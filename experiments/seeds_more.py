"""Priority 2: extra seeds (2-4) for GOBI vs GOBI+B on pre-selected error conditions."""
import os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep import job, ROOT

CONDS = [(0.0, 0.0, 0), (0.8, 0.0, 0), (0.0, 0.4, 0), (0.0, -0.4, 0),
         (0.0, 0.0, 2), (0.0, 0.0, 4), (0.4, 0.4, 2)]
jobs = []
for seed in (2, 3, 4):
    for c in CONDS:
        for s, suite in (('GOBI', 'gap'), ('GOBI+B', 'ours')):
            jobs.append((s, c, seed, os.path.join(ROOT, 'results', suite), 60))
with ThreadPoolExecutor(7) as ex:
    for i, r in enumerate(ex.map(job, jobs), 1):
        print(f'{i}/{len(jobs)} {r[:200]}', flush=True)
print('finished')
