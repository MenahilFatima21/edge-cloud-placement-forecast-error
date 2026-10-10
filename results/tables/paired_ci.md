**SLO violation rate (%): GOBI+B − GOBI, paired by seed (negative = GOBI+B better)**

| Condition | n seeds | GOBI mean ± sd | GOBI+B mean ± sd | Difference | 95% CI | p (paired t) | seeds where GOBI+B better |
|---|---|---|---|---|---|---|---|
| σ=0.0 | 5 | 11.6 ± 4.5 | 11.3 ± 3.9 | -0.3 pp | [-4.2, +3.6] | 0.84 | 2/5 |
| σ=0.8 | 5 | 10.6 ± 3.1 | 11.2 ± 5.6 | +0.5 pp | [-6.8, +7.8] | 0.85 | 2/5 |
| bias +0.4 | 5 | 10.5 ± 2.2 | 9.2 ± 3.4 | -1.4 pp | [-4.1, +1.4] | 0.24 | 4/5 |
| bias -0.4 | 5 | 10.6 ± 4.7 | 10.1 ± 2.9 | -0.6 pp | [-4.2, +3.1] | 0.68 | 3/5 |
| stale k=2 | 5 | 11.1 ± 3.6 | 10.1 ± 3.3 | -1.1 pp | [-4.9, +2.8] | 0.49 | 3/5 |
| stale k=4 | 5 | 11.7 ± 6.2 | 10.0 ± 4.9 | -1.7 pp | [-5.4, +2.0] | 0.27 | 4/5 |
| σ=0.4,b=0.4,k=2 | 5 | 11.0 ± 2.9 | 9.1 ± 3.5 | -1.9 pp | [-6.0, +2.2] | 0.26 | 4/5 |

**Average response time (s): GOBI+B − GOBI, paired by seed (negative = GOBI+B better)**

| Condition | n seeds | GOBI mean ± sd | GOBI+B mean ± sd | Difference | 95% CI | p (paired t) | seeds where GOBI+B better |
|---|---|---|---|---|---|---|---|
| σ=0.0 | 5 | 2290 ± 207 | 2236 ± 103 | -54 s | [-238, +130] | 0.46 | 4/5 |
| σ=0.8 | 5 | 2254 ± 142 | 2268 ± 224 | +14 s | [-276, +303] | 0.90 | 2/5 |
| bias +0.4 | 5 | 2288 ± 128 | 2218 ± 155 | -70 s | [-257, +117] | 0.36 | 4/5 |
| bias -0.4 | 5 | 2179 ± 141 | 2208 ± 119 | +30 s | [-73, +132] | 0.47 | 3/5 |
| stale k=2 | 5 | 2233 ± 110 | 2247 ± 177 | +14 s | [-149, +178] | 0.82 | 4/5 |
| stale k=4 | 5 | 2226 ± 205 | 2291 ± 191 | +65 s | [-13, +144] | 0.08 | 1/5 |
| σ=0.4,b=0.4,k=2 | 5 | 2277 ± 98 | 2236 ± 202 | -40 s | [-188, +107] | 0.49 | 4/5 |

Pooled over all error conditions (30 paired runs), slo_violation_rate: -1.01 pp, 95% CI [-2.27, +0.25], GOBI+B better in 20/30
Pooled over all error conditions (30 paired runs), avg_response_time_s: +2.05 s, 95% CI [-48.77, +52.87], GOBI+B better in 18/30

`*` = 95% CI excludes zero.
