# Datasets (Step 3)

The base paper (COSCO, Tuli et al., IEEE TPDS 2022) uses three data sources. The
simulation experiments we reproduce use #1 and #3. #2 needs the physical
Azure testbed and is documented here only for completeness.

## 1. BitBrain VM utilisation traces (GWA-T-12) — *used*

| Field | Value |
|---|---|
| Source | Grid Workloads Archive, TU Delft — http://gwa.ewi.tudelft.nl/datasets/gwa-t-12-bitbrains (mirror used by the COSCO code: `rnd.zip`, auto-downloaded) |
| Owner / licence | Bitbrains (managed hosting for banks, insurers and credit operators), released for research |
| Subset | `rnd` — 500 VMs, month 2013-09 (the COSCO loader deletes 2013-07 and 2013-08) |
| Samples | 500 CSV files × ~8,333 rows each (5-minute samples, ~29 days) ≈ 4.2 M rows, 477 MB on disk |
| Modality | Multivariate time series (tabular) |
| Columns | timestamp, CPU cores, CPU capacity provisioned [MHz], CPU usage [MHz] and [%], memory provisioned / used [KB], disk read/write [KB/s], network rx/tx [KB/s] |
| Characteristics | Real enterprise workloads, highly non-stationary and bursty. Good for testing schedulers under volatility |
| Split | No train/test split. Traces are *sampled* to create tasks: VMs whose CPU at row 10 is between 500 and 3,000 MIPS are eligible (`BitbrainWorkload2.py`), and each new task picks one eligible VM uniformly at random |
| Preprocessing (code) | MHz → MIPS by ×(2054/1200) (Pentium-III Dhrystone ratio); memory KB/4000; network KB/s/1000; disk read KB/s/4000, write /12000 |
| Arrivals | Number of new tasks per 300-s interval ~ N(5, 1.5) rounded, min 1 (the paper says Poisson(λ=5); the code uses a Gaussian; see the reproduction report) |
| SLA | Each task gets a deadline of N(20, 3) intervals after creation. A violation is when the task finishes after its deadline |

## 2. DeFog benchmark applications — *documented, not run*

| Field | Value |
|---|---|
| Source | https://github.com/qub-blesson/DeFog ; Docker images `shreshthtuli/yolo`, `shreshthtuli/pocketsphinx`, `shreshthtuli/aeneas` |
| Modality | **Multimodal**: YOLO (image object detection, 1,500 requests with unique images), PocketSphinx (speech-to-text audio, 320 requests), Aeneas (text–audio forced alignment, 1,500 requests) |
| Use in paper | The physical 10-VM Azure experiments (Fig. 8). The mix is p_y = p_p = p_a = 0.33, plus "dominant" runs where one app is 0.8 |
| Why not reproduced | Needs 10 Azure VMs in 2 regions, Vagrant, Ansible, InfluxDB and CRIU (Linux). This machine has Windows, no Azure budget and limited disk |

## 3. GOBI surrogate training set — *used (pre-trained checkpoint)*

| Field | Value |
|---|---|
| Source | Shipped in the repo: `scheduler/BaGTI/datasets/energy_latency_50_scheduling.csv`; full traces on Zenodo, https://doi.org/10.5281/zenodo.4897944 (CC BY 4.0) |
| Samples | 1,999 rows (one per scheduling interval of a random scheduler on the 50-host simulator) |
| Features | 50 host CPU % + 50 container IPS + 50 container→host allocation indices + [energy, avg response time] targets |
| Preprocessing | CPU/100; IPS / max container IPS; allocations one-hot (50×50); energy min-max normalised; response time / max |
| Split | Random 80 / 20 train / validation (`train.py`) |
| Use | Surrogate f for GOBI (input 50×52 → 2 outputs, combined 0.8·energy + 0.2·latency) |

## How the modalities are combined

In COSCO every application, whether an image, audio or text job or a BitBrain trace,
is reduced to the same resource-demand vector (IPS, RAM, disk and network time
series). The scheduler never sees pixels or audio. The modality only shapes
the resource profile (YOLO: memory, bandwidth and compute heavy; PocketSphinx:
compute heavy; Aeneas: bandwidth heavy). This is a limitation of the base
paper and is discussed in the gap analysis.
