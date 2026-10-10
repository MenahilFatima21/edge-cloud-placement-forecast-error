### D1. Evaluation protocol

* **Same system, data and metrics as the reproduction:** COSCO simulator,
  50 hosts (AzureFog: 60% edge in London, 40% cloud in Virginia), BitBrain
  workload, authors' surrogate checkpoint, and the paper's metrics (energy,
  response time, SLO violations, migrations, scheduling time).
* **Conditions:** the 9 forecast-error conditions of Part B (1 clean + 8 with
  error), 60 intervals each. ⟨SEEDS⟩
* **Systems (ablation, Step 11):** GOBI (original) · GOBI + A
  (uncertainty-aware objective) · GOBI + B (online forecast calibration) ·
  **R-GOBI** (A + B). GOBI\* is included as the paper's forecast-driven
  reference.
* **SLO** is reported with the code's per-task deadline (main metric) and
  with the paper's definition (> 95th percentile of A3C response time =
  6,104 s).

### D2. Ablation results — summary over error conditions

⟨TABLE:ablation_summary.md⟩

Δ columns are the mean, over the 8 error conditions, of each variant's change
relative to GOBI under the *same* condition (negative = better).

### D3. Results per condition

⟨TABLE:ablation_by_condition.md⟩

### D4. Interpretation

⟨EVAL_FINDINGS⟩

### D5. Final comparison (Step 12)

⟨FINAL_TABLE⟩

### D6. Runtime and resource usage

| Item | Value |
|---|---|
| Hardware for all runs | Windows 11 laptop, 12 logical cores, 7.7 GB RAM, no GPU (no paid cloud resources) |
| Wall time per 100-interval reproduction run | ≈ 21–24 min before the trace cache (10 runs in parallel), ≈ 2–4 min after |
| Wall time per 60-interval sweep run | ≈ 2–3 min (7 in parallel) |
| Total experiment compute | ≈ ⟨NRUNS⟩ simulator runs, ≈ 4.5 h wall-clock on one laptop |
| Memory per run | ≈ 300–350 MB |
| Extra storage | BitBrain 477 MB + parsed cache 360 MB |
| R-GOBI overhead | Component A: K = 16 scenario forward/backward passes, batched; Component B: one 5×5 solve per update. Scheduling time in D2 |
| Model retraining needed | none (R-GOBI reuses the authors' checkpoint) |

Scheduling times were measured while 7–10 simulations shared the CPU, so
they are noisy (± several hundred %). Compare them within a table, not with
the paper's absolute numbers.

### D7. Uncertainty: 5 seeds and paired 95% confidence intervals (GOBI vs GOBI + B)

The ablation identified Component B as the useful contribution, so we added
seeds 2–4 for **GOBI and GOBI + B only**, giving **⟨NSEEDS⟩ seeds** on 7
conditions: clean, σ = 0.8, bias ±0.4, staleness k = 2 and 4, and the
combined condition. These were chosen *after* the 2-seed ablation. They
cover every error type, and they deliberately include the two conditions
where B had looked worse (clean, bias −0.4). Seeds 0–1 informed this
choice, so the fresh evidence is seeds 2–4. We therefore also report the
result on seeds 2–4 alone. Each seed fixes the workload (task
arrivals and traces), so the two schedulers face identical workloads and
the comparison is **paired by seed**. For each condition we report the
mean per-seed difference (GOBI + B − GOBI) with a 95% Student-t CI, a paired
t-test p-value (exploratory, no multiple-comparison correction) and the
number of seeds where GOBI + B was better.

⟨TABLE:paired_ci.md⟩

⟨CI_FINDINGS⟩
