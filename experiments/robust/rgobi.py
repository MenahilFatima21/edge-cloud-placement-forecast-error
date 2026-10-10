"""R-GOBI: forecast-error-robust GOBI (G23 proposed method).

GOBI optimises a neural surrogate f(state, D) at a single point estimate of
the state -- the monitored host CPU / container IPS from the last interval --
and trusts it fully. R-GOBI adds two components (toggled for ablation):

  A  Uncertainty-aware objective. Keep an online buffer of relative forecast
     residuals r = true/forecast - 1 (revealed by delayed ground truth).
     Bootstrap K residual matrices, build K plausible states
     x_k = x_hat * (1 + r_k) and minimise  mean_k f(x_k, D) + kappa * std_k f(x_k, D).
     Distribution-free (empirical residuals), so it covers whatever error the
     telemetry really has instead of assuming a Gaussian.

  B  Online forecast calibration. A pooled online ridge regressor maps the
     observed history [o_t, o_{t-1}, o_{t-2}, fleet-mean(o_t), 1] to the true
     value. Trained on delayed ground truth with exponential forgetting, it
     learns to undo bias, extrapolate across staleness and shrink noise.
     Falls back to the raw observation until it has enough samples.

Assumption: exact utilisation becomes available after a delay
(staleness + 1 intervals), e.g. from metering / billing logs, while the
real-time monitoring feed used for decisions is noisy, biased or stale.
"""
import numpy as np
import torch
from collections import defaultdict, deque

from scheduler.Scheduler import Scheduler
from scheduler.BaGTI.src.models import *          # noqa: F401,F403 (surrogate classes)
from scheduler.BaGTI.src.constants import Coeff_Energy, Coeff_Latency
from scheduler.BaGTI.src.opt import opt
from scheduler.BaGTI.train import load_model
from scheduler.BaGTI.src.utils import load_energy_latency_data


class OnlineRidge:
    """Recursive ridge regression with exponential forgetting."""

    def __init__(self, dim, lam=1.0, forget=0.995, min_samples=40):
        self.A = lam * np.eye(dim); self.b = np.zeros(dim)
        self.lam, self.forget, self.n, self.min_samples = lam, forget, 0, min_samples
        self.w = None

    def update(self, X, y):
        f = self.forget ** len(y)
        self.A = f * self.A + X.T @ X + (1 - f) * self.lam * np.eye(len(self.b))
        self.b = f * self.b + X.T @ y
        self.n += len(y)
        self.w = np.linalg.solve(self.A, self.b)

    def predict(self, X, fallback):
        if self.w is None or self.n < self.min_samples: return fallback
        return np.clip(X @ self.w, 0.0, None)


class _RiskSurrogate(torch.nn.Module):
    """Wraps the GOBI surrogate: mean + kappa*std over K bootstrapped states."""

    def __init__(self, base, mult, kappa):
        super().__init__()
        self.base, self.kappa = base, kappa
        self.register_buffer('mult', mult)          # (K, M, 2): multipliers for cpu cols
        self.name = base.name

    def forward(self, x):
        K = self.mult.shape[0]
        cpu = x[:, :2].unsqueeze(0) * self.mult      # (K, M, 2)
        alloc = x[:, 2:].unsqueeze(0).expand(K, -1, -1)
        out = self.base.find(torch.cat([cpu, alloc], dim=2).reshape(K, -1))
        z = Coeff_Energy * out[:, 0] + Coeff_Latency * out[:, 1]
        return z.mean() + self.kappa * z.std()


class RGOBIScheduler(Scheduler):
    def __init__(self, hosts, use_A=True, use_B=True, K=16, kappa=1.0, buffer=600):
        super().__init__()
        dt = 'energy_latency_' + str(hosts)
        self.data_type, self.hosts = dt, hosts
        self.model = eval(dt + '()')
        self.model, _, _, _ = load_model(dt, self.model, dt)
        for p in self.model.parameters(): p.requires_grad = False
        _, _, self.max_container_ips = load_energy_latency_data(hosts)
        self.use_A, self.use_B, self.K, self.kappa = use_A, use_B, K, kappa
        self.telemetry = None                       # set by ForecastError.attach
        self.rng = np.random.default_rng(0)
        # Calibration (component B)
        self.ridge_h, self.ridge_c = OnlineRidge(5), OnlineRidge(5)
        self.hist_h = defaultdict(lambda: deque(maxlen=3))
        self.hist_c = defaultdict(lambda: deque(maxlen=3))
        self.pending = deque()                      # (t, kind, key, features, raw_obs, forecast)
        # Residuals (component A)
        self.res_h, self.res_c = deque(maxlen=buffer), deque(maxlen=buffer)

    # ---------------------------------------------------------- calibration
    def _features(self, hist, fleet_mean):
        h = list(hist); h = [h[0]] * (3 - len(h)) + h  # left-pad with oldest
        return np.array([h[-1], h[-2], h[-3], fleet_mean, 1.0])

    def _forecast(self):
        t = self.env.interval
        cpu_obs = np.array([h.getCPU() / 100 for h in self.env.hostlist])
        ips_obs = {c.creationID: c.getApparentIPS() / self.max_container_ips
                   for c in self.env.containerlist if c}
        for i, v in enumerate(cpu_obs): self.hist_h[i].append(v)
        for k, v in ips_obs.items(): self.hist_c[k].append(v)
        mh = cpu_obs.mean(); mc = np.mean(list(ips_obs.values())) if ips_obs else 0.0

        Xh = np.stack([self._features(self.hist_h[i], mh) for i in range(self.hosts)])
        cpu_hat = self.ridge_h.predict(Xh, cpu_obs) if self.use_B else cpu_obs
        cont_hat = {}
        for k, v in ips_obs.items():
            x = self._features(self.hist_c[k], mc)
            cont_hat[k] = float(self.ridge_c.predict(x[None], np.array([v]))[0]) if self.use_B else v
            self.pending.append((t, 'c', k, x, cont_hat[k]))
        for i in range(self.hosts):
            self.pending.append((t, 'h', i, Xh[i], cpu_hat[i]))
        return cpu_hat, cont_hat

    def _ingest_feedback(self):
        """Use ground truth that has become available (delayed) to train B and fill A's buffers."""
        if self.telemetry is None: return
        ready_before = self.env.interval - self.telemetry.feedback_delay
        Xh, yh, Xc, yc = [], [], [], []
        while self.pending and self.pending[0][0] <= ready_before:
            t, kind, key, x, fc = self.pending.popleft()
            true = self.telemetry.truth(t, kind, key)
            if true is None: continue
            true = true / 100 if kind == 'h' else true / self.max_container_ips
            (Xh if kind == 'h' else Xc).append(x); (yh if kind == 'h' else yc).append(true)
            if fc > 1e-3 and true > 1e-3:
                (self.res_h if kind == 'h' else self.res_c).append(np.clip(true / fc - 1, -0.9, 3.0))
        if Xh: self.ridge_h.update(np.array(Xh), np.array(yh))
        if Xc: self.ridge_c.update(np.array(Xc), np.array(yc))

    # ---------------------------------------------------------- decision
    def run(self):
        self._ingest_feedback()
        cpu_hat, cont_hat = self._forecast()
        cpuC = np.array([cont_hat.get(c.creationID, 0.0) if c else 0.0 for c in self.env.containerlist])
        state = np.stack([cpu_hat, cpuC], axis=1)
        alloc, prev = [], {}
        for c in self.env.containerlist:
            one = [0] * self.hosts
            if c: prev[c.id] = c.getHostID()
            if c and c.getHostID() != -1: one[c.getHostID()] = 1
            else: one[np.random.randint(0, self.hosts)] = 1
            alloc.append(one)
        init = torch.tensor(np.concatenate((state, alloc), axis=1), dtype=torch.float, requires_grad=True)

        model = self.model
        if self.use_A and len(self.res_h) >= 30:
            M = state.shape[0]
            rh = np.array(self.res_h); rc = np.array(self.res_c) if len(self.res_c) >= 30 else rh
            mult = np.stack([1 + self.rng.choice(rh, size=(self.K, M)),
                             1 + self.rng.choice(rc, size=(self.K, M))], axis=2)
            model = _RiskSurrogate(self.model, torch.tensor(mult, dtype=torch.float), self.kappa)

        result, _, _ = opt(init, model, [], self.data_type)
        decision = []
        for cid in prev:
            one = result[cid, -self.hosts:].tolist()
            h = one.index(max(one))
            if prev[cid] != h: decision.append((cid, h))
        return decision

    def selection(self):
        return []

    def placement(self, containerIDs):
        return self.run()
