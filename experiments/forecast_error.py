"""Controllable forecast-error injection for COSCO schedulers.

GOBI (and GOBI*, LR-MMT, MAD-MC) decide placements from the *monitored*
state: host CPU utilisation (Host.getCPU) and container IPS
(Container.getApparentIPS). That last-interval reading is the scheduler's
forecast of the next interval. This module corrupts what the scheduler sees
-- only inside the decision window -- along three independent axes from the
G23 proposal (Sec. 7.3):

  sigma     : multiplicative Gaussian noise, obs = true * (1 + N(0, sigma))
  bias      : systematic over/under-estimation, obs = true * (1 + bias)
  staleness : obs = the value measured `staleness` intervals ago

The simulator itself (execution, energy, SLA accounting) always uses the true
values, so any QoS change is caused purely by worse decisions.
"""
import numpy as np
from collections import defaultdict, deque


class ForecastError:
    def __init__(self, sigma=0.0, bias=0.0, staleness=0, seed=0):
        self.sigma, self.bias, self.staleness = float(sigma), float(bias), int(staleness)
        self.rng = np.random.default_rng(10_000 + seed)
        self.host_hist = defaultdict(lambda: deque(maxlen=self.staleness + 1))
        self.cont_hist = defaultdict(lambda: deque(maxlen=self.staleness + 1))
        self.obs_err = []          # relative error of observed vs true host CPU
        self._patched = []
        self.env = None
        self.truth_log = {}        # interval -> {('h', host_id) | ('c', creation_id): true value}

    @property
    def feedback_delay(self):
        # Exact utilisation (metering logs) arrives after the interval, and no
        # earlier than the stale monitoring feed would have shown it.
        return self.staleness + 1

    def truth(self, t, kind, key):
        return self.truth_log.get(t, {}).get((kind, key))

    @property
    def active(self):
        return self.sigma > 0 or self.bias != 0 or self.staleness > 0

    def attach(self, env, schedulers):
        self.env = env
        for s in schedulers:
            if hasattr(s, 'telemetry'): s.telemetry = self

    def describe(self):
        return {'sigma': self.sigma, 'bias': self.bias, 'staleness': self.staleness,
                'obs_mape_host_cpu': float(np.mean(self.obs_err)) if self.obs_err else 0.0}

    # ------------------------------------------------------------------ core
    def _corrupt(self, value, hist):
        hist.append(value)
        v = hist[0] if self.staleness > 0 else value   # oldest kept = k intervals ago
        if self.sigma > 0: v = v * (1.0 + self.rng.normal(0.0, self.sigma))
        v = v * (1.0 + self.bias)
        return max(0.0, v)

    def before_decision(self, env):
        """Freeze corrupted observations and patch the getters the schedulers read."""
        log = self.truth_log.setdefault(env.interval, {})
        for h in env.hostlist: log[('h', h.id)] = h.getCPU()
        for c in env.containerlist:
            if c: log[('c', c.creationID)] = c.getApparentIPS()
        self.truth_log.pop(env.interval - 20, None)
        if not self.active: return
        # Keys are creation ids so staleness follows a container across slots
        for h in env.hostlist:
            true = h.getCPU()
            obs = min(100.0, self._corrupt(true, self.host_hist[h.id]))
            if true > 1e-6: self.obs_err.append(abs(obs - true) / true)
            self._patch(h, 'getCPU', obs)
        for c in env.containerlist:
            if not c: continue
            true = c.getApparentIPS()
            obs = self._corrupt(true, self.cont_hist[c.creationID])
            self._patch(c, 'getApparentIPS', obs)

    def _patch(self, obj, name, value):
        obj.__dict__[name] = (lambda v=value: v)
        self._patched.append((obj, name))

    def after_decision(self, env):
        for obj, name in self._patched:
            obj.__dict__.pop(name, None)
        self._patched = []

    def record(self, env, stats):
        pass
