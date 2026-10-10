# Forecast-Error-Robust Task Placement in Edge–Cloud Systems: Reproducing COSCO/GOBI and Closing Its Forecast-Accuracy Gap

**Group G23 · Section A · Cloud Computing (Dr. Basharat Hussain)**
Menahil Fatima (23I-0813), Primary Researcher · Sarah Suhail (23I-0557), Co-Researcher
Research area: Edge–Cloud Intelligence (Approved Direction 4)
Code: `G23-cloud-research/` (to be pushed to https://github.com/MenahilFatima21/edge-cloud-placement-forecast-error)

> **How this connects to our Cutoff-1 proposal.** The proposal asked whether
> there is a *latency-forecast-accuracy floor* in edge–cloud placement. LAVEA
> (2017), our original anchor, has no public code, so it cannot be reproduced.
> We therefore anchored the same research question on **COSCO/GOBI** (IEEE TPDS
> 2022). It is a forecast-driven edge–cloud placement system with official code,
> public traces and a CPU-only simulator. The error-injection study from the
> proposal (Sec. 7.3) is now the **evidence for the research gap**. Our new
> contribution is a placement method that is **robust to forecast error**
> (R-GOBI).

---

## Part A — Reproduction (Steps 1–6)

### A1. Selected paper

| Item | Value |
|---|---|
| Title | COSCO: Container Orchestration Using Co-Simulation and Gradient Based Optimization for Fog Computing Environments |
| Authors | Shreshth Tuli, Shivananda R. Poojara, Satish N. Srirama, Giuliano Casale, Nicholas R. Jennings |
| Venue / Year | IEEE Transactions on Parallel and Distributed Systems, vol. 33, no. 1, pp. 101–116, 2022 (IEEE "Code Reviewed" badge) |
| Paper | https://ieeexplore.ieee.org/document/9448450 · preprint https://arxiv.org/abs/2104.14392 |
| Code | https://github.com/imperial-qore/COSCO (commit `d2c073c`, 28 Mar 2023) |
| Data / traces | BitBrain GWA-T-12; DeFog; Zenodo https://doi.org/10.5281/zenodo.4897944 |

### A2. Reproducibility check (Step 2)

| Resource | Available? | Notes |
|---|---|---|
| Official repository | ✅ | BSD-3 licence |
| Source code (simulator, schedulers, framework) | ✅ | Python |
| Experiment / training scripts | ✅ / partial | `main.py` runs one scheduler for 100 intervals. No script loops over baselines or seeds (we wrote `experiments/run.py` and `sweep.py`). `scheduler/BaGTI/train.py` retrains surrogates |
| Datasets | ✅ | BitBrain is auto-downloaded. Surrogate training CSVs and pre-trained checkpoints ship in the repo |
| Configuration | ✅ | Constants are hard-coded at the top of `main.py` |
| Libraries | ⚠️ | Pinned to Python 3.7/3.8, numpy 1.19, torch 1.7.1 (2020-era) |
| Hardware | ✅ | Simulator is CPU-only. Paper used an i7-10700K, 64 GB RAM, GTX 1060 |
| Install instructions | ⚠️ | `install.py` also installs InfluxDB, Vagrant, VirtualBox and Ansible, and copies SSH keys. That is only needed for the physical testbed, so we skipped it |
| Instructions to reproduce results | ⚠️ | The README says to "modify line 106 of main.py" per scheduler. There is no seed control and no result-aggregation script |

### A3. Problem, approach and architecture (Step 4)

**Problem.** Fog/edge–cloud brokers must decide every scheduling interval
(Δ = 300 s) which host runs each containerised IoT task, and whether to migrate
running tasks. Workloads are volatile and hosts are heterogeneous: edge hosts
are close (3 ms) but weak, cloud hosts are far (76 ms) but strong. Heuristics
(LR-MMT, MAD-MC) are fast but don't adapt. RL (A3C, DQLCM) and evolutionary
methods (GA) adapt but are slow, and slow decisions inflate response time and
SLO violations.

**Why it matters.** Response-time-sensitive IoT applications (healthcare,
smart cities, video analytics) need both low latency and low energy. A
scheduler that is too slow or too naive hurts both.

**Proposed solution.**
* **GOBI** trains a feed-forward neural surrogate *f(U, D) → (energy, response
  time)*. *U* is the monitored state of the last interval (host CPU %, container
  IPS) and *D* is the placement as one-hot rows. At decision time GOBI fixes
  the network weights and runs **gradient descent on the input *D*** (AdamW,
  lr 0.8, cosine annealing, ≤200 iterations, re-projected to one-hot after each
  step). The objective is 0.8·energy + 0.2·response time.
* **GOBI\*** adds a *co-simulation*: GOBI's tentative decision is simulated one
  interval ahead, and the predicted (energy, response time) are fed as two
  extra input columns to a second surrogate.
* **COSCO** is the framework that runs the same scheduler code on a
  discrete-event simulator or on a real Azure/Vagrant testbed.

**Architecture.** IoT layer → gateway → **Fog Broker** (resource monitor,
scheduler = GOBI/GOBI\*, container orchestrator, coupled simulator) → hosts
(edge layer: Azure B2s/B4ms in London; cloud layer: B4ms/B8ms in Virginia).
Surrogate: input 50×52 (GOBI) or 50×54 (GOBI\*) → Linear(128)+Softplus →
Linear(128)+Softplus → Linear(64)+Tanhshrink → Linear(2)+Sigmoid.

**Cloud computing component.** The cloud is part of the decision space: the
broker places containers across an edge tier and a remote cloud tier with
different latency, capacity, price ($/hr per VM type, Table 3) and power
models (SPEC). Live migration between tiers is supported (CRIU in the
framework). The physical experiments ran on 10 Azure VMs in two regions.

**Multimodal component.** The DeFog workloads are YOLO (images), PocketSphinx
(speech audio) and Aeneas (text–audio alignment). The scheduler never sees the
media itself. Each modality reaches it only through its resource profile
(IPS, RAM, disk, network).

**Baselines.** LR-MMT, MAD-MC (heuristics); GA (evolutionary, same
surrogate); A3C, DQLCM (deep RL); POND (max-weight).

**Metrics.** Average energy per interval, average response time, SLO-violation
fraction, Jain fairness, average migration time, scheduling time, wait time.

**Experimental settings and hyperparameters.** 100 intervals × 300 s, 5 runs
averaged. 50 simulated hosts (60% edge). New tasks per interval: λ = 5 (paper
says Poisson; the code uses N(5, 1.5)). Surrogate trained on 2,000 intervals of
a random scheduler (AdamW, lr 1e-5, 80/20 split). Energy/latency weights
0.8/0.2.

**Assumptions made by the paper.** A central broker. Allocation time
negligible. No intra-layer network latency. **The monitored utilisation of
the previous interval is an accurate input for the next interval's decision**
(GOBI). For GOBI\*, the LSTM utilisation predictors are assumed accurate.

**Limitations acknowledged.** GOBI\* is more than 2× slower than GOBI. The
surrogate must be differentiable (no ReLU). Workflows/serverless are future
work. The authors do **not** discuss the effect of monitoring or forecast
error on decisions.

**Missing or unclear implementation details** (found while reproducing):
1. The paper (Sec. 8.2) says GOBI\* uses **LSTM utilisation predictors**. The
   released code has no LSTM: GOBI\* feeds `runSimulationGOBI()`, which
   returns the simulated energy plus the **mean of the last 5 intervals'**
   response time (a persistence forecast).
2. The paper says GOBI adapts through "neural model update in each iteration".
   The released GOBI uses a **frozen** checkpoint with no online training.
3. **SLO definition.** The paper uses "response time > 95th percentile of A3C
   for that application". The code uses a per-task deadline
   (creation + N(20, 3) intervals).
4. Arrivals are Poisson in the paper but Gaussian in the code.
5. The GA baseline seeds its population from **random rows of the training
   set**, not from the current system state.

### A4. Datasets (Step 3)

See `docs/DATASETS.md` for the full documentation. In summary:

| Dataset | Source | Size | Modality | Use |
|---|---|---|---|---|
| BitBrain GWA-T-12 (`rnd`, 2013-09) | TU Delft GWA | 500 VMs × ~8,333 samples (5-min), 477 MB | Multivariate resource time series | Simulated workload (reproduced) |
| DeFog (YOLO / PocketSphinx / Aeneas) | qub-blesson/DeFog | 1,500 / 320 / 1,500 requests | Image / audio / text+audio | Physical testbed (not reproduced) |
| GOBI training set | repo + Zenodo | 1,999 intervals × 152 cols | Tabular | Pre-trained surrogate |

### A5. Environment

| Item | Paper | Ours |
|---|---|---|
| CPU | Intel i7-10700K | 12 logical cores (laptop) |
| RAM | 64 GB | 7.7 GB |
| GPU | GTX 1060 | none (CPU only) |
| OS | Windows 10 Pro | Windows 11 Home 10.0.26200 |
| Python | 3.7/3.8 | 3.12.2 (venv) |
| PyTorch | 1.7.1+cpu | 2.14.1+cpu |
| numpy / pandas / scipy | 1.19.2 / 1.1.2 / 1.5.2 | 2.5.3 / 3.0.6 / 1.18.1 |
| Cloud resources | 10 Azure VMs (London + Virginia) | none: simulator only |

**Important configuration (unchanged from `main.py`):** HOSTS = 50,
CONTAINERS = 50, NEW_CONTAINERS = 5 (σ = 1.5), INTERVAL_TIME = 300 s,
TOTAL_POWER = 1000, ROUTER_BW = 10000, NUM_SIM_STEPS = 100, datacenter
`AzureFog(50)`, workload `BWGD2`, surrogate checkpoint
`energy_latency_50_Trained.ckpt`.

### A6. Results: original vs reproduced (Step 5)

⟨REPRO_TABLE⟩

⟨REPRO_DIFF⟩

### A7. Problems encountered and deviations (Step 6)

**Installation problems.**
* `install.py` assumes Linux/WSL with sudo, InfluxDB, Vagrant, VirtualBox and
  Ansible. It even copies SSH keys into `~/.ssh`. We did not run it and
  installed only the Python dependencies.
* Python 3.7/3.8 and torch 1.7.1 wheels are no longer installable on
  Python 3.12. We used current versions and added three compatibility shims
  in our runner (not in the authors' code): `np.float/np.int/np.bool` aliases,
  and `torch.load(weights_only=False)` because torch ≥2.6 changed the default.
* The laptop's C: drive was full (0 bytes free). Setup was blocked until
  space was freed.

**Code problems.**
* `scheduler/BaGTI/src/ga.py`: `chromosome != []` on a numpy array raises in
  numpy ≥ 1.25. We patched it to `len(chromosome) > 0` (one line, tracked by
  `git diff` in `baseline_COSCO/`).
* The workload reads BitBrain CSVs with a regex separator (`';\t'`), which
  forces pandas' pure-Python parser. That was ~85% of runtime: 500 files at
  start-up plus one per new task, so ~24 min per run under parallel load. We
  added a parsed-trace pickle cache (`experiments/trace_cache.py`) and
  **verified identical metrics** with and without it.
* `main.py` has no seed control. Our runner seeds `random`, `numpy` and
  `torch`.

**Missing resources.** No LSTM predictor code for GOBI\* (see A3). No
aggregation or plotting script for the paper's figures. The paper reports
50-host results only as bar charts (Fig. 9), so most "original" values below
are read from the text or from the charts.

**Computational limitations.** 7.7 GB RAM and no GPU. Each 100-interval run
took about 21–24 min of wall time before our trace cache (2–4 min after).
Within the deadline we completed 5 seeds for GOBI/GOBI\*/GA, 4 for A3C, 2 for
MAD-MC and 1 each for LR-MMT and POND. DQLCM did not complete and one POND
seed crashed (error output was empty, not investigated). The forecast-error
sweeps used 2 seeds × 60 intervals per condition.

**Deviations from the original experiment.**
1. Simulation only (50 hosts, BitBrain). The 10-VM Azure DeFog testbed (Fig. 8)
   was not reproduced: it needs paid Azure VMs in two regions plus Linux tooling.
2. Modern library versions (above).
3. SLO is reported with the code's deadline definition and additionally with
   the paper's definition (95th percentile of A3C), computed from per-task
   response times.

---

## Part B — Research Gap (Step 7)

⟨GAP_SECTION⟩

---

## Part C — Proposed Method: R-GOBI (Step 9) — Methodology

⟨METHOD_SECTION⟩

---

## Part D — Evaluation (Steps 10–12)

⟨EVAL_SECTION⟩

---

## Part E — Discussion

⟨DISCUSSION⟩

---

## Reproducing everything

```bash
python -m venv .venv
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python -m pip install numpy pandas scipy matplotlib seaborn scikit-learn tqdm joblib wget scienceplots
git clone https://github.com/imperial-qore/COSCO baseline_COSCO        # then apply the 1-line ga.py patch
.venv/Scripts/python experiments/run.py --scheduler GOBI --seed 0       # one reproduction run
.venv/Scripts/python experiments/sweep.py --suite repro gap ours         # all experiments
.venv/Scripts/python experiments/analyze.py reproduction
.venv/Scripts/python experiments/analyze.py gap ours
```
