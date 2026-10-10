# G23 — Forecast-Error-Robust Edge–Cloud Placement (COSCO/GOBI → R-GOBI)

Cloud Computing research project, Group G23 (Menahil Fatima 23I-0813, Sarah Suhail 23I-0557).

* **Base paper:** Tuli et al., *COSCO: Container Orchestration using Co-Simulation and Gradient Based
  Optimization for Fog Computing Environments*, IEEE TPDS 33(1), 2022 —
  code https://github.com/imperial-qore/COSCO
* **Gap:** GOBI/GOBI\* optimise placements over a point forecast of host/container utilisation
  and have no mechanism for forecast noise, bias or staleness.
* **Proposed:** R-GOBI = GOBI + (A) uncertainty-aware objective over bootstrapped forecast residuals
  + (B) online forecast calibration from delayed ground truth.

**Report:** [`docs/REPORT_FINAL.md`](docs/REPORT_FINAL.md) (datasets: [`docs/DATASETS.md`](docs/DATASETS.md))

## Layout

| Path | Contents |
|---|---|
| `baseline_COSCO/` | Authors' code (commit d2c073c) + 1-line numpy fix (`docs/baseline_patch.diff`) |
| `experiments/run.py` | Seeded runner for one scheduler/condition → JSON metrics |
| `experiments/forecast_error.py` | Controllable forecast-error injection (noise / bias / staleness) |
| `experiments/robust/` | **R-GOBI** and ablation variants (`GOBI+A`, `GOBI+B`, `R-GOBI`) |
| `experiments/trace_cache.py` | Parsed BitBrain cache (same data, ~8× faster runs) |
| `experiments/sweep.py` | Parallel experiment grid |
| `experiments/analyze.py` | Tables (`results/tables/`) and figures (`results/figures/`) |
| `results/{reproduction,gap,ours}/` | One JSON per run |
| `papers/` | Base paper PDF + extracted text |

## Run

```bash
python -m venv .venv
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python -m pip install numpy pandas scipy matplotlib seaborn scikit-learn tqdm joblib wget scienceplots
git clone https://github.com/imperial-qore/COSCO baseline_COSCO && (cd baseline_COSCO && git apply ../docs/baseline_patch.diff)

.venv/Scripts/python experiments/run.py --scheduler GOBI --seed 0                          # reproduction run
.venv/Scripts/python experiments/run.py --scheduler R-GOBI --sigma 0.4 --bias 0.4 --staleness 2
.venv/Scripts/python experiments/sweep.py --suite repro gap ours                            # everything
.venv/Scripts/python experiments/analyze.py reproduction && .venv/Scripts/python experiments/analyze.py gap ours
.venv/Scripts/python experiments/analyze.py final && python docs/build_report.py
```
