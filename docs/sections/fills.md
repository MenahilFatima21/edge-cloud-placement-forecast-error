
@@GAP_FINDINGS
Observation error achieved (host-CPU MAPE): σ = 0.2 → ≈ 8%, σ = 0.4 → ≈ 17%,
σ = 0.8 → ≈ 29%, staleness k = 2 → ≈ 25%, k = 4 → ≈ 40%, bias −0.4 → 40%,
combined → ≈ 33%. Bias +0.4 shows only ≈ 2% because many hosts are at 100%
CPU and observations are clipped there; the container-IPS inputs are still
biased.

1. **GOBI\*, the forecast-heavy variant, is the most fragile.** Its SLO
   violations are 22.6% with clean inputs and rise to 26.0% (σ = 0.2) and
   23.5% (bias −0.4). It is worse than GOBI in **every** condition (+18%
   response time, +11.6 pp SLO on average). Adding a forecast to the
   surrogate input *hurts* when the forecast is a weak one.
2. **GOBI degrades gradually, not sharply.** Clean: 2,098 s / 7.7% SLO. Worst
   case (σ = 0.8): 2,251 s (+7.3%) / 10.4% (+2.7 pp, +35% relative).
   Combined error: 2,183 s / 8.3%. Mean over the 8 error conditions:
   2,132 s (+1.6%) / 8.2%.
3. **Answer to our Cutoff-1 question ("is there a forecast-accuracy
   floor?").** For GOBI on this workload we see **no sharp threshold** up to
   ~40% observation MAPE. QoS degrades smoothly, and below roughly
   15–20% MAPE the change is smaller than the seed-to-seed variation
   (±3.9 pp SLO). In other words, the floor is *high*: making the forecaster
   more accurate than ~15–20% MAPE buys little for GOBI. Robustness to
   **systematic** error (bias, staleness) matters more than raw accuracy.
4. **The direction of bias matters.** Over-estimation (+0.4) makes GOBI\*
   more conservative and actually lowers its SLO violations (11.8%), while
   under-estimation (−0.4) does the opposite. A single "forecast accuracy"
   number (MAE/MAPE) cannot predict placement quality, which is exactly the
   disconnect in the literature.

@@SEEDS
2 seeds (0, 1) per (system, condition): 9 conditions × 5 systems × 2 seeds = 90 runs, all completed.

@@EVAL_FINDINGS
*Exploratory (2 seeds). The 5-seed check in D7 does **not** confirm these
gains.* **Component B (online forecast calibration) looked responsible for
the improvement.** Across the 8 error conditions GOBI + B lowers response time
by 1.3% and SLO violations by 1.1 pp on average vs GOBI, with the best
worst-case SLO (9.9% vs 10.4%) and no extra migrations (313 vs 318). Its gains
concentrate where its design says they should, on **systematic or large
error**. Over the 5 conditions with bias +0.4, staleness, the combined
error or σ = 0.8, GOBI + B averages 2,068 s / 6.1% SLO vs GOBI's
2,164 s / 8.5% (**−4.4% response time, −2.4 pp SLO, −28% relative**). With
clean or mildly noisy inputs (σ ≤ 0.4) and under-estimation bias (−0.4), B
is neutral to slightly worse, because there is little systematic error to
remove and early in a run the corrector has few samples. *(This 5-condition
grouping was chosen after seeing the results and is reported as such; the
all-condition mean above is the pre-specified comparison.)*

**Component A (uncertainty-aware objective) does not help as designed.** It
helps in some conditions (clean: 5.2% vs 7.7% SLO; bias −0.4: 3.5% vs 7.3%)
but adds +23% migrations (391 vs 318) and +2.1% response time on average. The
bootstrap redraws a new scenario set every interval, so successive decisions
disagree and containers are moved back and forth. Migration cost isn't in the
surrogate's objective, so A cannot see this cost.

**R-GOBI (A + B)** inherits A's instability. Its average SLO equals GOBI's
(−0.0 pp) and response time is +1.2%. It is the best system at σ = 0.2
(6.6% SLO) and staleness k = 4 (5.6%) but the worst on the combined
condition (10.6%). **We therefore do not claim that the full R-GOBI improves
on GOBI.** The ablation shows that **B is the useful contribution and A
needs a migration-aware redesign**, which is exactly why Step 11 asks for an
ablation.

**Statistical caution.** With 2 seeds × 60 intervals, effects of 1–2 pp are
inside the seed-to-seed variation. The direction of B's effect is consistent
(it wins on SLO in 5 of 8 error conditions, including all systematic-error
ones), but more seeds are needed before claiming significance.

**Cost.** None of the variants changes energy (0.398–0.404 kWh/interval,
< 1.5% spread). Scheduling time rises from GOBI's 0.45 s to 1.1–4.0 s, but
these were measured with 7 simulations sharing the CPU and are dominated by
contention. All variants stay far below GA (13 s) and a 300-s interval.

@@FINAL_TABLE
| System / metric (BitBrain, 50 simulated hosts; error rows = 2-seed exploratory, see D7 for 5-seed CIs) | Original paper (GOBI) | Reproduced baseline (GOBI) | Proposed R-GOBI (A+B) | Best ablation: GOBI + B |
|---|---|---|---|---|
| Dataset 1: BitBrain (simulation) | ✓ | ✓ | ✓ | ✓ |
| Dataset 2: DeFog on 10 Azure VMs | ✓ (Fig. 8) | ✗ not reproduced | ✗ | ✗ |
| Avg response time, accurate forecasts | 17.98% below GA (no absolute value given) | 2,472 s @100 int. (17.7% *above* GA); 2,098 s @60 int. | 2,149 s | 2,131 s |
| SLO violations, accurate forecasts | 1.1% | 15.3% @100 int.; 7.7% @60 int. | 7.1% | 7.7% |
| Avg response time under forecast error (mean of 8 conditions) | not studied | 2,132 s | 2,156 s (+1.2%) | **2,101 s (−1.3%)** |
| SLO violations under forecast error, code definition | not studied | 8.2% | 8.2% (±0.0 pp) | **7.1% (−1.1 pp)** |
| SLO under error, paper definition (> A3C p95 = 6,104 s) | not studied | 2.5% | 2.6% | **2.4%** |
| Worst-case SLO across error conditions | not studied | 10.4% | 10.6% | **9.9%** |
| SLO under systematic / large error (5 conditions, post hoc) | not studied | 8.5% | 8.6% | **6.1%** |
| Energy per interval | ≈ A3C | 0.398 kWh | 0.398 kWh | 0.399 kWh |
| Migrations per 60 intervals (under error) | — | 318 | 314 | 313 |
| Scheduling time per decision | 2.65 s (physical) | 0.45–1.24 s | 1.14 s | 3.15 s (CPU contention) |
| Runtime per experiment | 8 h 20 min (physical) | 2–4 min (sim, with cache) | 2–4 min | 2–4 min |
| Resource usage | i7-10700K, 64 GB, GTX 1060, 10 Azure VMs | laptop CPU, 7.7 GB RAM, no GPU, no cloud spend | same + 600-residual buffer | same + 2 × 5×5 ridge models |

@@EVIDENCE
**Updated after the 5-seed check (D7): the evidence does not show a
statistically significant improvement.** The text below describes the
2-seed exploratory ablation. (1) A controlled ablation (GOBI, +A, +B, +A+B) on the same simulator,
workload, checkpoint and 9 error conditions × 2 seeds. (2) GOBI + B is the
only variant that is better than GOBI on average response time (−1.3%),
SLO (−1.1 pp) and worst-case SLO without more migrations, and its gains are
largest under bias, staleness and high noise (−2.4 pp SLO), which are the
error types it was designed to correct. (3) The same ablation shows that
Component A, and therefore the full R-GOBI, does **not** improve on GOBI:
a negative result we report rather than hide. The evidence is directionally
consistent but not yet statistically conclusive (2 seeds).

@@NRUNS
135 (reproduction 23 + sweep 90 + smoke/validation ~22)

@@NSEEDS
up to 5 (exact n per condition in the table)

@@CI_FINDINGS
**Result: with 5 seeds the improvement from Component B is not
statistically supported.**

* **No single condition shows a significant difference.** Every 95% CI
  includes zero, for both SLO and response time.
* **Pooled over the 6 error conditions (30 paired runs):** SLO −1.0 pp,
  95% CI [−2.3, +0.3], GOBI + B better in 20/30. Response time +2 s,
  CI [−49, +53].
* **On the fresh seeds 2–4 alone (18 paired runs, not used to choose the
  conditions):** SLO −0.45 pp, 95% CI [−2.3, +1.4], better in only 9/18.
  Response time +49 s, CI [−12, +110].
* **The largest 2-seed effect (σ = 0.8: −4.3 pp) disappears** with 5 seeds
  (+0.5 pp). It was seed noise.
* **Some direction remains under systematic error,** but it isn't
  significant. GOBI + B was better on SLO in 4/5 seeds for bias +0.4
  (−1.4 pp), staleness k = 4 (−1.7 pp) and the combined condition
  (−1.9 pp). Its effect on response time is nil.
* **Seed variance is large.** GOBI's SLO sd across seeds is 2–6 pp, larger
  than any effect we measured. Detecting a 1 pp effect at this variance
  would need roughly 30 or more seeds per condition.

**What this means for the claims in D2–D5:** treat those 2-seed numbers,
and especially the post-hoc "systematic/large error" grouping, as
**exploratory**. The defensible conclusion is that **neither R-GOBI nor its
components significantly improve on GOBI under forecast error on this
workload.** GOBI itself is fairly robust (Part B: no sharp
forecast-accuracy floor up to ~40% MAPE). This explains why there was little
room for improvement.
