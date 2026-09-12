# Edge-Cloud Placement Under Forecast Error

## Overview
This project studies how errors in latency/workload forecasting affect the 
quality of edge-cloud task placement decisions, using an IoT video-analytics 
workload as the test case.

## Research Question
How does latency-forecast error affect the cost and SLA performance of 
edge-cloud task placement in an IoT video-analytics workload?

## Approach
1. An existing edge-cloud task placement algorithm is used as the baseline system.
2. The algorithm is first run with accurate (ground-truth) latency predictions.
3. Controlled noise (5%, 10%, 20%, 30% error) is injected into the predictions.
4. The algorithm is re-run under each noise level.
5. Cost, SLA violations, and placement quality are compared across error levels.

## Repository Structure
- `/src` — simulation and noise-injection code
- `/config` — placement algorithm settings, workload parameters, error levels
- `/data` — workload trace / dataset (or scripts to generate/download it)
- `/results` — output CSVs and generated graphs

## How to Reproduce
1. Install dependencies: `pip install -r requirements.txt`
2. Run baseline (perfect prediction): `python src/run_baseline.py`
3. Run with noisy predictions: `python src/run_noisy.py --error 10`
4. Generate plots: `python src/plot_results.py`

## Authors
- [Your Name] — [Roll Number]
- [Co-Researcher Name] — [Roll Number]

## Course
Cloud Computing — 100-Day Research Assignment, Fall 2026

## License
MIT License (see LICENSE file)

## Reproducibility
Reproducibility: The code and reproducibility materials for this study are 
publicly available at: https://github.com/MenahilFatima21/edge-cloud-placement-forecast-error
