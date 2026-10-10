**What was successfully reproduced?** The full COSCO simulation pipeline
(50 hosts, BitBrain, surrogate-based GOBI and GOBI\*, plus GA, A3C, POND,
LR-MMT and MAD-MC) runs end to end on a CPU-only laptop with modern
libraries after one numpy-compatibility patch. The **efficiency** claims
reproduce: GOBI decides about 10× faster than GA, GOBI\* costs about 2× GOBI,
and GA migrates the most.

**What could not be reproduced?** (i) The paper's **QoS ranking**: in our
runs GOBI/GOBI\* do not beat GA and the heuristics on response time or SLO,
and GOBI\* is worse than GOBI. (ii) The **physical Azure testbed** with DeFog
(Fig. 8), which needs paid VMs in two regions. (iii) DQLCM within our compute
budget.

**Why were there differences?** Mainly because the released code differs
from the paper (no LSTM forecasters in GOBI\*, no online surrogate update),
a different SLO definition, new library versions and unseeded volatility
(details in A6).

**What research gap was identified?** COSCO's forecast-driven placement
assumes its forecasts are accurate. Under controlled noise, bias and
staleness its decisions degrade, and the more forecast-dependent GOBI\*
degrades most.

**How does the proposed improvement address the gap?** R-GOBI (i) learns to
correct biased, stale or noisy telemetry online from delayed ground truth
(B), and (ii) optimises a risk-aware objective over bootstrapped forecast
residuals instead of a point estimate (A). It plugs into GOBI without
retraining.

**What evidence shows the improvement works?** ⟨EVIDENCE⟩

**Remaining limitations.**
1. **Statistical power.** The ablation used 2 seeds × 60 intervals. Adding
   seeds 2–4 for GOBI vs GOBI + B (D7) removed the apparent gain: pooled
   SLO −1.0 pp, CI [−2.3, +0.3], and on fresh seeds −0.45 pp, CI [−2.3, +1.4]. The workload
   is volatile (GOBI's SLO CI is ±3.9 pp over 5 seeds × 100 intervals), so
   differences of 1–2 pp are within noise. More seeds and longer runs are
   needed before making strong claims.
2. **Simulation only.** No physical edge/cloud testbed and no DeFog
   (image/audio/text) workloads, so the multimodal aspect is untested.
3. **Synthetic error model.** Multiplicative Gaussian noise, constant bias and
   fixed staleness. Real monitoring error is correlated across hosts and
   time. Positive bias on host CPU is partly masked because many hosts sit at
   100% utilisation and observations are clipped.
4. **Delayed-truth assumption.** Component B needs exact utilisation to
   arrive later (metering/billing logs). Without it, B cannot learn.
5. **Component A as designed increases migrations.** The variance penalty
   is computed per decision, so successive decisions disagree. A
   migration-aware penalty (charging migration cost against the uncertainty
   margin) is the obvious next step.
6. **Surrogate shift.** Both GOBI and R-GOBI use the authors' frozen
   surrogate. Combining B with online surrogate fine-tuning is future work.
7. Scheduling times were measured under heavy CPU contention.

**Next steps (for the mentor discussion).** (a) More seeds and 100-interval
runs for the 4 ablation systems. (b) A migration-aware version of
Component A. (c) Evaluate on Azure2017/2019 traces (already supported by
COSCO) for cross-dataset generalisation. (d) Optionally, a small real
deployment (2 edge VMs + 1 cloud VM) using the DeFog containers to test the
multimodal workloads.
