"""Seeded, scriptable runner for the COSCO simulator (50-host BitBrain setup).

Mirrors the simulation loop in baseline_COSCO/main.py (initalizeEnvironment /
stepSimulation) but adds: CLI scheduler selection, fixed seeds, forecast-error
injection hooks (used later by the gap study) and a JSON summary of the
metrics reported in the COSCO paper (Sec. 8.5).

Usage:
    python experiments/run.py --scheduler GOBI --seed 0 --steps 100
"""
import argparse, json, os, sys, random, time
from contextlib import redirect_stdout
import io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'baseline_COSCO')

# ---------------------------------------------------------------- compat shims
# The released code targets numpy 1.19 / torch 1.7. We run numpy 2.x / torch 2.x.
import numpy as np
if not hasattr(np, 'float'): np.float = float
if not hasattr(np, 'int'): np.int = int
if not hasattr(np, 'bool'): np.bool = bool
import torch
_torch_load = torch.load
torch.load = lambda *a, **k: _torch_load(*a, **{**k, 'weights_only': False})

sys.path.insert(0, os.path.join(ROOT, 'experiments'))
import trace_cache
trace_cache.install()

CALLER_CWD = os.getcwd()
os.chdir(BASE)
sys.path.insert(0, BASE)

from simulator.Simulator import Simulator
from simulator.environment.AzureFog import AzureFog
from simulator.workload.BitbrainWorkload2 import BWGD2
from stats.Stats import Stats

# Paper constants for the simulated environment (main.py, Sec. 8.1)
HOSTS = 50
CONTAINERS = HOSTS
TOTAL_POWER = 1000
ROUTER_BW = 10000
INTERVAL_TIME = 300
NEW_CONTAINERS = 5


BASELINES = ['GOBI', 'GOBI*', 'GA', 'A3C', 'DQLCM', 'POND', 'LR-MMT', 'MAD-MC', 'Random']


def make_scheduler(name, hosts):
    dt = 'energy_latency_' + str(hosts)
    if name == 'GOBI':
        from scheduler.GOBI import GOBIScheduler; return GOBIScheduler(dt)
    if name == 'GOBI*':
        from scheduler.GOBI2 import GOBI2Scheduler; return GOBI2Scheduler(dt)
    if name == 'GA':
        from scheduler.GA import GAScheduler; return GAScheduler(dt)
    if name == 'A3C':
        from scheduler.DRL import DRLScheduler; return DRLScheduler(dt)
    if name == 'DQLCM':
        from scheduler.DQL import DQLScheduler; return DQLScheduler(dt)
    if name == 'POND':
        from scheduler.POND import PONDScheduler; return PONDScheduler(dt)
    if name == 'LR-MMT':
        from scheduler.LR_MMT_Random import LRMMTRScheduler; return LRMMTRScheduler()
    if name == 'MAD-MC':
        from scheduler.MAD_MC_Random import MADMCRScheduler; return MADMCRScheduler()
    if name == 'Random':
        from scheduler.Random_Random_Random import RandomScheduler; return RandomScheduler()
    # Our methods are registered by experiments/robust (imported lazily)
    from robust.registry import make as make_ours
    return make_ours(name, hosts)


def seed_all(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)


def summarise(stats, sched_times, wall):
    m = stats.metrics[1:]  # interval 0 is the initial allocation
    resp, wait, mig = [], [], []
    viol = done = 0
    for d in m:
        resp += d['responsetime']; wait += d['waittime']; mig += d['migrationtime']
        viol += d['slaviolations']; done += len(d['responsetime'])
    resp = np.array(resp, dtype=float)
    fairness = (resp.sum() ** 2) / (len(resp) * (resp ** 2).sum()) if len(resp) else 0
    return {
        'intervals': len(m),
        'energy_total_kWh': float(sum(d['energytotalinterval'] for d in m) / 3.6e6),
        'energy_per_interval_kWh': float(np.mean([d['energytotalinterval'] for d in m]) / 3.6e6),
        # Container.totalExecTime + totalMigrationTime are already in seconds
        'avg_response_time_s': float(resp.mean()) if len(resp) else 0.0,
        'p95_response_time_s': float(np.percentile(resp, 95)) if len(resp) else 0.0,
        'slo_violation_rate': float(viol / done) if done else 0.0,
        'completed_tasks': int(done),
        'avg_migration_time_s': float(np.mean(mig)) if mig else 0.0,
        'total_migrations': int(sum(d['nummigrations'] for d in m)),
        'avg_wait_time_intervals': float(np.mean(wait)) if wait else 0.0,
        'fairness_jain': float(fairness),
        'avg_scheduling_time_s': float(np.mean(sched_times)),
        'wall_clock_s': float(wall),
        # Per-task values so the paper's SLO (95th pct of A3C) can be computed post hoc
        'response_times_s': [round(float(x), 2) for x in resp],
    }


def run(scheduler_name, seed, steps, perturb=None, quiet=True):
    seed_all(seed)
    datacenter = AzureFog(HOSTS)
    workload = BWGD2(NEW_CONTAINERS, 1.5)
    scheduler = make_scheduler(scheduler_name, HOSTS)
    hostlist = datacenter.generateHosts()
    env = Simulator(TOTAL_POWER, ROUTER_BW, scheduler, CONTAINERS, INTERVAL_TIME, hostlist)
    stats = Stats(env, workload, datacenter, scheduler)
    if perturb is not None:
        perturb.attach(env, [scheduler, stats.simulated_scheduler])

    sink = io.StringIO()
    sched_times = []
    t0 = time.time()
    with redirect_stdout(sink if quiet else sys.stdout):
        new = workload.generateNewContainers(env.interval)
        deployed = env.addContainersInit(new)
        s = time.time(); decision = scheduler.placement(deployed); sched_times.append(time.time() - s)
        migrations = env.allocateInit(decision)
        workload.updateDeployedContainers(env.getCreationIDs(migrations, deployed))
        stats.saveStats(deployed, migrations, [], deployed, decision, sched_times[-1])
        for step in range(steps):
            new = workload.generateNewContainers(env.interval)
            deployed, destroyed = env.addContainers(new)
            if perturb is not None: perturb.before_decision(env)
            s = time.time()
            selected = scheduler.selection()
            decision = scheduler.filter_placement(scheduler.placement(selected + deployed))
            sched_times.append(time.time() - s)
            if perturb is not None: perturb.after_decision(env)
            migrations = env.simulationStep(decision)
            workload.updateDeployedContainers(env.getCreationIDs(migrations, deployed))
            stats.saveStats(deployed, migrations, destroyed, selected, decision, sched_times[-1])
            if perturb is not None: perturb.record(env, stats)
    out = summarise(stats, sched_times, time.time() - t0)
    out.update({'scheduler': scheduler_name, 'seed': seed, 'steps': steps})
    if perturb is not None: out.update(perturb.describe())
    return out, stats


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--scheduler', default='GOBI')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--steps', type=int, default=100)
    ap.add_argument('--out', default=os.path.join(ROOT, 'results', 'reproduction'))
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--sigma', type=float, default=0.0, help='forecast noise (relative std)')
    ap.add_argument('--bias', type=float, default=0.0, help='forecast bias (relative)')
    ap.add_argument('--staleness', type=int, default=0, help='forecast age in intervals')
    ap.add_argument('--inject', action='store_true', help='attach the error layer even at zero error')
    a = ap.parse_args()
    perturb = None
    if a.inject or a.sigma or a.bias or a.staleness or a.scheduler not in BASELINES:
        from forecast_error import ForecastError
        perturb = ForecastError(a.sigma, a.bias, a.staleness, seed=a.seed)
    res, _ = run(a.scheduler, a.seed, a.steps, perturb=perturb, quiet=not a.verbose)
    a.out = os.path.join(CALLER_CWD, a.out)   # relative to where the user ran us
    os.makedirs(a.out, exist_ok=True)
    tag = f"_s{a.sigma}_b{a.bias}_k{a.staleness}" if perturb is not None else ''
    fn = os.path.join(a.out, f"{a.scheduler.replace('*', 'star')}{tag}_seed{a.seed}.json")
    json.dump(res, open(fn, 'w'), indent=2)
    print(json.dumps(res, indent=2))
