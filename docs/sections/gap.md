### B1. Observation from the reproduction

GOBI and GOBI\* make every decision from a **point forecast** of the next
interval: the monitored CPU/IPS of the previous interval (GOBI) plus a
persistence estimate of QoS (GOBI\*). The paper evaluates the policies only
under these implicitly-accurate inputs and never asks what happens when the
forecast is wrong. Our reproduction already gives a first data point:
GOBI\*, the variant that relies **more** on forecasts, performed **worse**
than GOBI once its forecaster was weaker than the paper's LSTM (54% vs 15%
SLO violations).

This is the same disconnect our Cutoff-1 proposal identified in the
literature. Predictor papers report forecast error (MAE/MAPE) in isolation,
and placement papers (LAVEA, IntelliScheduler, DRL schedulers, COSCO) assume
the forecast is reliable.

### B2. Gap experiment: controlled forecast-error injection

We corrupted what the schedulers observe (only during the decision window;
the simulator always runs on true values) along the three axes of the
proposal: noise σ ∈ {0.2, 0.4, 0.8}, bias b ∈ {−0.4, +0.4}, staleness
k ∈ {2, 4} intervals, and a combined condition (σ = 0.4, b = +0.4, k = 2).
Each condition ran 60 intervals on 50 hosts (seeds: see Part D).

⟨TABLE:error_grid.md⟩

![SLO vs forecast error](../results/figures/error_slo.png)
![Response time vs forecast error](../results/figures/error_resp.png)

### B3. Findings (gap evidence)

⟨GAP_FINDINGS⟩

### B4. Gap statement

> **The forecast-driven placement in COSCO (GOBI/GOBI\*) has no mechanism to
> account for error in the utilisation/QoS forecasts it optimises over.
> Its decision quality degrades under realistic noise, bias and staleness,
> and the forecast-heavier variant (GOBI\*) is the most fragile. No prior
> work in this line measures this sensitivity or makes the placement
> optimiser robust to it.**

**Why this gap is meaningful, not just interesting:** (i) it comes from an
observed failure in our reproduction (GOBI\* < GOBI), not from wanting to
try a new technique; (ii) monitoring in real edge–cloud deployments is
exactly this kind of noisy, biased (CPU steal, turbo) and stale (scrape
intervals, WAN to the cloud tier) data; (iii) it directly answers our
approved research question about a forecast-accuracy floor.

**Other gaps we observed but did not pursue** (candidates for the mentor
discussion): the frozen surrogate (no online adaptation); modality-blind
scheduling (images, audio and text reduced to resource vectors); no monetary
cost in the objective despite per-VM prices in Table 3; simulator-only
evaluation of the 50-host claims.
