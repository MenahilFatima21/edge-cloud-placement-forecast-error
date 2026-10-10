### C1. Problem definition

At the start of interval *I_t*, GOBI observes the monitored state
**Û**<sub>t</sub> = [ĉ<sub>h</sub>, ŝ<sub>j</sub>]: host CPU utilisation ĉ<sub>h</sub> ∈ [0, 1] for
each host *h* and container throughput ŝ<sub>j</sub> (IPS, normalised) for each
container slot *j*. It then solves

  D\* = argmin<sub>D</sub> f<sub>θ</sub>(Û<sub>t</sub>, D),

where *f<sub>θ</sub>* is the frozen neural surrogate and *D* the one-hot placement.
The decision is only as good as **Û**<sub>t</sub>. In practice **Û**<sub>t</sub> is a
*forecast* of the true state **U**<sub>t</sub> that the tasks will experience, and it
is wrong in three ways:

| Error type | Model used in this study | Real-world cause |
|---|---|---|
| Noise | Û = U·(1 + ε), ε ~ N(0, σ²) | sampling jitter, short monitoring windows, noisy predictors |
| Bias | Û = U·(1 + b) | mis-calibrated predictors, CPU-steal/turbo effects, wrong capacity metadata |
| Staleness | Û<sub>t</sub> = U<sub>t−k</sub> | monitoring/aggregation delay, scrape intervals, WAN to the cloud tier |

**Goal:** a placement policy whose energy, response time and SLO violations
degrade gracefully as σ, |b| and k grow, with little loss when the forecast
is accurate and little extra scheduling time.

### C2. Design rationale

GOBI fails under forecast error for two separate reasons, and each component
of R-GOBI targets one of them:

1. **It optimises a point estimate.** Gradient descent on f(Û, D) happily
   exploits small, spurious differences between hosts that exist only in the
   noisy forecast, and it migrates containers to chase them. → **Component A**
   optimises a *risk-aware* objective over the distribution of plausible true
   states.
2. **It cannot correct systematic error.** Bias and staleness shift the input
   in a consistent direction that more samples cannot average out. →
   **Component B** learns an online correction of the forecast from delayed
   ground truth.

### C3. Component A — Uncertainty-aware surrogate objective

*Residual buffer.* After each interval, the exact utilisation of interval *t*
becomes available after a delay of *d = k + 1* intervals (metering logs; see
C5). For every host and container we store the relative residual

  r = U / Ũ − 1 (clipped to [−0.9, 3]),

where Ũ is the forecast actually used at decision time. We keep a FIFO buffer
of the last 600 host residuals and 600 container residuals.

*Bootstrap scenarios.* At decision time we draw *K* = 16 scenario matrices by
sampling residuals with replacement, independently per row:

  U<sup>(k)</sup> = Ũ ⊙ (1 + R<sup>(k)</sup>), k = 1..K.

The empirical residual distribution is used directly, so no Gaussian
assumption is made. It captures heavy tails and skew in BitBrain and any
residual bias left after Component B.

*Risk-aware objective.* GOBI's objective is replaced with

  J(D) = mean<sub>k</sub> f<sub>θ</sub>(U<sup>(k)</sup>, D) + κ · std<sub>k</sub> f<sub>θ</sub>(U<sup>(k)</sup>, D), κ = 1.

The K scenarios run through the surrogate as one batch of size K, and J is
optimised with **GOBI's own optimiser** (AdamW, lr 0.8, cosine annealing,
one-hot projection, same stopping rule). Only the objective changes. The
std term penalises placements whose quality depends on the forecast being
exactly right. This is a mean–variance (sample-average-approximation)
formulation of robust optimisation. A is switched on once ≥ 30 residuals
have been collected; before that R-GOBI behaves exactly like GOBI.

### C4. Component B — Online forecast calibration

For each host *h* (and each container, with a separate model) we build the
feature vector from the observed history:

  x<sub>t</sub> = [Û<sub>t</sub>, Û<sub>t−1</sub>, Û<sub>t−2</sub>, mean<sub>h'</sub> Û<sub>t</sub>(h'), 1].

A single **pooled online ridge regressor** (shared across hosts, so it learns
fast) predicts the true value: Ũ<sub>t</sub> = max(0, w<sup>⊤</sup>x<sub>t</sub>). The weights are
updated by recursive least squares with exponential forgetting (λ = 0.995,
ridge α = 1) whenever delayed ground truth arrives. With these features the
model can:

* **remove bias**, since a scale on Û<sub>t</sub> undoes multiplicative bias;
* **compensate staleness**, since the lagged terms let it extrapolate the trend
  across k intervals;
* **shrink noise**, since it blends Û<sub>t</sub> with history and the fleet mean,
  the optimal linear denoiser under noise.

Until 40 labelled samples exist, Ũ = Û (identity fallback). The forgetting
factor lets the corrector track non-stationary error.

### C5. Assumptions

* **Delayed exact telemetry.** The real-time feed used for decisions may be
  noisy, biased or stale, but exact per-interval utilisation becomes
  available later (e.g., cgroup accounting or billing/metering logs). We
  model this delay as *k* + 1 intervals, so R-GOBI never sees ground truth
  earlier than the stale feed would.
* The surrogate f<sub>θ</sub> is the authors' **pre-trained checkpoint, unchanged**.
  R-GOBI needs no retraining and no access to the simulator.

### C6. Algorithm (per scheduling interval)

```
Input: observed state Û_t, residual buffers B_h, B_c, ridge models R_h, R_c
1  for each delayed ground-truth record (t', U_t') now available:
2      update R_h / R_c with (x_t', U_t')                       # Component B
3      push U_t' / Ũ_t' − 1 into B_h / B_c                      # Component A
4  Ũ_t ← R(x_t) if B enabled and trained else Û_t
5  if A enabled and |B_h| ≥ 30:
6      draw K residual matrices from B_h, B_c;  U^(k) = Ũ_t ⊙ (1 + R^(k))
7      J(D) = mean_k f(U^(k), D) + κ·std_k f(U^(k), D)
8  else J(D) = f(Ũ_t, D)
9  D* ← GOBI-optimiser(J, init = current allocation)
10 return migrations/placements in D* that differ from current allocation
```

### C7. Integration with the original system

R-GOBI is a drop-in `Scheduler` subclass (`experiments/robust/rgobi.py`) using
the same interfaces (`placement`, `selection`, `filter_placement`), the same
surrogate checkpoint and the same optimiser function `opt()` from the
authors' code. The original GOBI, GOBI\* and all baselines stay unchanged and
selectable (`--scheduler GOBI`). The forecast-error layer
(`experiments/forecast_error.py`) corrupts only what *any* scheduler observes
during its decision window. Execution, energy and SLA accounting always use
true values, so differences in QoS come only from decision quality.

### C8. Complexity

GOBI costs one forward/backward pass per optimiser iteration. A batches
K = 16 scenarios into one pass, so the extra cost is a larger matrix
multiply (input 2,600 → 128), which is small next to the simulator. B costs
one 5×5 linear solve per update. Scheduling-time overhead is reported in the
evaluation.
