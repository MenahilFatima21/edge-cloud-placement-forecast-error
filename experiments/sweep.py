"""Run a grid of (scheduler x forecast-error condition x seed) in parallel.

    python experiments/sweep.py --suite gap      # gap evidence (baselines under error)
    python experiments/sweep.py --suite ours     # proposed method + ablations, same grid

Each run writes one JSON to results/<suite>/. Existing files are skipped so the
sweep can be resumed.
"""
import argparse, itertools, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe')

# Forecast-error grid: one axis varied at a time, plus one combined condition
CONDITIONS = (
    [(s, 0.0, 0) for s in (0.0, 0.2, 0.4, 0.8)] +
    [(0.0, b, 0) for b in (-0.4, 0.4)] +
    [(0.0, 0.0, k) for k in (2, 4)] +
    [(0.4, 0.4, 2)]
)
SUITES = {
    'gap': ['GOBI', 'GOBI*'],
    'ours': ['R-GOBI', 'GOBI+A', 'GOBI+B'],
}
CLEAN = [(0.0, 0.0, 0)]


def job(args):
    sched, cond, seed, out, steps = args
    if cond is None:                        # plain reproduction run
        fn = os.path.join(out, f"{sched}_seed{seed}.json")
        if os.path.exists(fn): return 'skip'
        cmd = [PY, os.path.join(ROOT, 'experiments', 'run.py'), '--scheduler', sched,
               '--seed', str(seed), '--steps', str(steps), '--out', out]
        r = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, 'OMP_NUM_THREADS': '1', 'PYTHONIOENCODING': 'utf-8'})
        return 'ok' if r.returncode == 0 else f'FAIL {sched} repro {seed} ' + r.stderr[-800:]
    sigma, bias, k = cond
    tag = f"_s{sigma}_b{bias}_k{k}"
    fn = os.path.join(out, f"{sched.replace('*', 'star')}{tag}_seed{seed}.json")
    if os.path.exists(fn): return 'skip'
    env = {**os.environ, 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'PYTHONIOENCODING': 'utf-8'}
    cmd = [PY, os.path.join(ROOT, 'experiments', 'run.py'), '--scheduler', sched, '--seed', str(seed),
           '--steps', str(steps), '--sigma', str(sigma), '--bias', str(bias), '--staleness', str(k),
           '--out', out]
    cmd += ['--inject']   # uniform filenames, incl. the zero-error condition
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        return f'FAIL {sched} {tag} {seed}\n{r.stderr[-800:]}'
    return 'ok'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--suite', nargs='+', choices=list(SUITES) + ['repro'], required=True)
    ap.add_argument('--seeds', type=int, default=2)
    ap.add_argument('--steps', type=int, default=60)
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    jobs = []
    for seed in range(a.seeds):              # seed-major: a full first pass lands early
        for c in CONDITIONS:
            for suite in a.suite:
                if suite == 'repro': continue
                out = os.path.join(ROOT, 'results', suite); os.makedirs(out, exist_ok=True)
                jobs += [(s, c, seed, out, a.steps) for s in SUITES[suite]]
    if 'repro' in a.suite:                   # remaining paper baselines, clean, 100 intervals
        out = os.path.join(ROOT, 'results', 'reproduction')
        rep = [(s, None, seed, out, 100) for seed in range(3) for s in ('LR-MMT', 'MAD-MC', 'POND', 'DQLCM')]
        jobs = rep[:4] + jobs[:len(jobs)//2] + rep[4:] + jobs[len(jobs)//2:]
    done = 0
    with ThreadPoolExecutor(a.workers) as ex:
        for res in ex.map(job, jobs):
            done += 1
            if res.startswith('FAIL'): print(res, flush=True)
            print(f'{done}/{len(jobs)} {res[:4]}', flush=True)
    print('finished', len(jobs))
