**Setup.** 50 simulated hosts, BitBrain workload, 100 intervals, the authors'
pre-trained surrogate checkpoints. Mean ± 95% CI over seeds: GOBI, GOBI\*, GA
(5 seeds), A3C (4), MAD-MC (2), LR-MMT and POND (1). DQLCM did not finish
within our compute budget, and one POND seed crashed (see A7).

**Full reproduced table (Fig. 9 equivalent):**

⟨TABLE:reproduction.md⟩

![Reproduced 50-host comparison](../results/figures/reproduction_50hosts.png)

**Original vs reproduced.** The paper reports its 50-host results as bar
charts (Fig. 9) plus the numbers quoted in its text, so we compare the
quantitative claims:

| Claim (50-host simulation unless noted) | Original paper | Reproduced | Difference | Reproduced? |
|---|---|---|---|---|
| GOBI SLO violations | 1.1% | 15.3% ± 3.9% | +14.2 pp | ✗ |
| GOBI\* SLO violations | 0% | 54.0% ± 8.7% | +54.0 pp | ✗ |
| GA SLO violations | 0.2% | 4.3% ± 1.1% | +4.1 pp | ✗ (ordering GA < GOBI also flips) |
| GOBI response time vs GA | −17.98% | **+17.7%** (2472 s vs 2101 s) | 35.7 pp | ✗ |
| GOBI\* response time vs GA | −20.87% | **+35.4%** (2844 s vs 2101 s) | 56.3 pp | ✗ |
| GOBI\* energy vs A3C | −9.39% | +1.3% (0.382 vs 0.377 kWh) | 10.7 pp | ✗ |
| GOBI energy vs A3C | "very close" | +8.0% (0.407 vs 0.377 kWh) | — | ~ |
| GOBI scheduling time (Table 4, physical) | 2.65 s | 1.24 s (sim) | −1.41 s | ✓ (same order of magnitude) |
| GOBI\* / GOBI scheduling-time ratio | 2.2× | 1.85× | −0.35× | ✓ |
| GOBI far faster than GA (gradient vs gradient-free) | yes (Fig. 9g) | 1.24 s vs 13.07 s (−90%) | — | ✓ |
| GA has the most migrations | yes | 2,436 vs ≤ 1,969 for others | — | ✓ |
| GOBI/GOBI\* are the fairest schedulers | yes | no (0.634/0.649 vs 0.737 POND) | — | ✗ |

**Summary.** The *efficiency* claims reproduce: GOBI is about 10× faster to
decide than GA, and GOBI\* costs about 2× GOBI. The *QoS-superiority* claims
(GOBI/GOBI\* best response time and SLO) do **not** reproduce with the
released code. In our runs the simple heuristics MAD-MC and LR-MMT have the
lowest response time (≈1,921 s), followed by GA (2,101 s) and GOBI (2,472 s).
GOBI\* and A3C are worst on SLO.

**Possible explanations, in order of how likely we think they are:**
1. **GOBI\* in the released code is not the GOBI\* in the paper.** The paper's
   LSTM utilisation predictors are absent. GOBI\* feeds the surrogate a
   persistence estimate (mean response time of the last 5 intervals), so its
   extra inputs are a weak forecast. This alone can explain GOBI\* < GOBI, and
   it motivates our research gap.
2. **No online model update.** The paper says GOBI adapts through per-interval
   model updates. The released GOBI uses a frozen checkpoint trained on
   random-scheduler data. Under GOBI's own placements the state distribution
   shifts away from that training data, so the surrogate is less accurate
   than in the paper.
3. **Different SLO definition.** The paper's percentile-based SLO (95th pct of
   A3C) is much looser than the code's per-task deadline. With the paper's
   definition, our A3C threshold is 6,104 s, and the GOBI violation rate in
   the sweep runs drops to about 2.5%, much closer to the paper's 1.1% (Part D).
4. **Library versions.** numpy 1.19 → 2.5 and torch 1.7 → 2.14 change RNG
   streams and floating-point kernels. The optimiser's one-hot projection is
   discontinuous, so small numeric differences can change decisions.
5. **Randomness.** The paper's runs are unseeded and the workload is volatile:
   our GOBI SLO 95% CI is ±3.9 pp over 5 seeds.
6. **Workload generation.** The paper states Poisson(λ = 5) arrivals; the code
   uses N(5, 1.5).
7. **Unreleased code version.** The repository's last commit (2023) postdates
   the paper (2021). Results in the paper may come from an earlier version.
8. **Hardware / OS** (Windows 11 laptop vs i7-10700K desktop). This affects
   scheduling *time* only, not decisions.
