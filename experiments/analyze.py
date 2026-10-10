"""Aggregate result JSONs into tables (markdown/CSV) and figures.

    python experiments/analyze.py reproduction
    python experiments/analyze.py gap ours
"""
import glob, json, os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'results', 'tables')
FIG = os.path.join(ROOT, 'results', 'figures')
METRICS = ['energy_per_interval_kWh', 'avg_response_time_s', 'p95_response_time_s', 'slo_violation_rate',
           'completed_tasks', 'total_migrations', 'avg_migration_time_s', 'avg_wait_time_intervals',
           'fairness_jain', 'avg_scheduling_time_s']
ORDER = ['GOBI*', 'GOBI', 'A3C', 'GA', 'DQLCM', 'POND', 'LR-MMT', 'MAD-MC',
         'GOBI+A', 'GOBI+B', 'R-GOBI']
COLORS = {'GOBI': '#4e79a7', 'GOBI*': '#76b7b2', 'LR-MMT': '#bab0ac',
          'GOBI+A': '#f28e2b', 'GOBI+B': '#59a14f', 'R-GOBI': '#e15759'}


def load(*suites):
    rows = []
    for s in suites:
        for f in glob.glob(os.path.join(ROOT, 'results', s, '*.json')):
            d = json.load(open(f)); d['suite'] = s; rows.append(d)
    df = pd.DataFrame(rows)
    for c in ('sigma', 'bias', 'staleness'):
        if c not in df: df[c] = 0.0
        df[c] = df[c].fillna(0.0)
    return df


def mean_ci(x):
    x = np.asarray(x, float)
    if len(x) < 2: return x.mean(), 0.0
    return x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def reproduction_table(df):
    g = df.groupby('scheduler')
    rows = []
    for name in [n for n in ORDER if n in g.groups]:
        sub = g.get_group(name); r = {'Scheduler': name, 'runs': len(sub)}
        for m in METRICS:
            mu, ci = mean_ci(sub[m]); r[m] = mu; r[m + '_ci'] = ci
        rows.append(r)
    t = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    t.to_csv(os.path.join(OUT, 'reproduction.csv'), index=False)
    fmt = lambda r, m, p=3: f"{r[m]:.{p}f} ± {r[m+'_ci']:.{p}f}"
    lines = ['| Scheduler | Energy/interval (kWh) | Avg resp. (s) | SLO viol. (%) | Completed | Migrations | Fairness | Sched. time (s) |',
             '|---|---|---|---|---|---|---|---|']
    for _, r in t.iterrows():
        lines.append(f"| {r.Scheduler} | {fmt(r,'energy_per_interval_kWh')} | {fmt(r,'avg_response_time_s',1)} | "
                     f"{100*r.slo_violation_rate:.2f} ± {100*r.slo_violation_rate_ci:.2f} | {fmt(r,'completed_tasks',1)} | "
                     f"{fmt(r,'total_migrations',1)} | {fmt(r,'fairness_jain')} | {fmt(r,'avg_scheduling_time_s')} |")
    open(os.path.join(OUT, 'reproduction.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    # Bar chart like Fig. 9
    fig, ax = plt.subplots(1, 4, figsize=(14, 3))
    for a, (m, lab) in zip(ax, [('energy_per_interval_kWh', 'Energy / interval (kWh)'),
                                ('avg_response_time_s', 'Avg response time (s)'),
                                ('slo_violation_rate', 'SLO violation rate'),
                                ('avg_scheduling_time_s', 'Scheduling time (s)')]):
        a.bar(t.Scheduler, t[m], yerr=t[m + '_ci'], color='#4e79a7', capsize=2)
        a.set_title(lab, fontsize=9); a.tick_params(axis='x', rotation=60, labelsize=7)
    fig.tight_layout(); os.makedirs(FIG, exist_ok=True)
    fig.savefig(os.path.join(FIG, 'reproduction_50hosts.png'), dpi=160)


def condition_label(r):
    if r.staleness: return f"stale k={int(r.staleness)}" if not (r.sigma or r.bias) else f"σ={r.sigma},b={r.bias},k={int(r.staleness)}"
    if r.bias and r.sigma: return f"σ={r.sigma},b={r.bias}"
    if r.bias: return f"bias {r.bias:+.1f}"
    return f"σ={r.sigma}"


def error_tables(df):
    df = df.copy(); df['condition'] = df.apply(condition_label, axis=1)
    os.makedirs(OUT, exist_ok=True); os.makedirs(FIG, exist_ok=True)
    agg = df.groupby(['scheduler', 'sigma', 'bias', 'staleness', 'condition']).agg(
        n=('seed', 'count'),
        resp=('avg_response_time_s', 'mean'), resp_sd=('avg_response_time_s', 'std'),
        p95=('p95_response_time_s', 'mean'),
        slo=('slo_violation_rate', 'mean'), slo_sd=('slo_violation_rate', 'std'),
        energy=('energy_per_interval_kWh', 'mean'),
        done=('completed_tasks', 'mean'), mig=('total_migrations', 'mean'),
        sched=('avg_scheduling_time_s', 'mean'), mape=('obs_mape_host_cpu', 'mean')).reset_index()
    agg.to_csv(os.path.join(OUT, 'error_grid.csv'), index=False)

    # Degradation relative to each scheduler's own zero-error run
    clean = agg[(agg.sigma == 0) & (agg.bias == 0) & (agg.staleness == 0)].set_index('scheduler')
    gobi_clean = clean.loc['GOBI'] if 'GOBI' in clean.index else None
    agg['resp_vs_clean_GOBI_%'] = 100 * (agg.resp / gobi_clean.resp - 1) if gobi_clean is not None else np.nan
    agg['energy_vs_clean_GOBI_%'] = 100 * (agg.energy / gobi_clean.energy - 1) if gobi_clean is not None else np.nan

    scheds = [s for s in ORDER if s in set(agg.scheduler)]
    conds = list(dict.fromkeys(agg.sort_values(['staleness', 'bias', 'sigma']).condition))
    lines = ['| Condition | obs. MAPE | ' + ' | '.join(scheds) + ' |', '|---|---|' + '---|' * len(scheds)]
    for c in conds:
        sub = agg[agg.condition == c].set_index('scheduler')
        mape = sub.mape.max()
        cells = []
        for s in scheds:
            if s in sub.index:
                r = sub.loc[s]; cells.append(f"{r.resp:.0f} s / {100*r.slo:.1f}% / {r.energy:.3f}")
            else: cells.append('—')
        lines.append(f"| {c} | {100*mape:.0f}% | " + ' | '.join(cells) + ' |')
    txt = 'Cells: avg response time / SLO violation rate / energy per interval (kWh), mean over seeds\n\n' + '\n'.join(lines)
    open(os.path.join(OUT, 'error_grid.md'), 'w', encoding='utf-8').write(txt + '\n')
    print(txt)

    # Figures: one panel per error axis
    axes_def = [('sigma', (agg.bias == 0) & (agg.staleness == 0), 'Noise σ (relative)'),
                ('bias', (agg.sigma == 0) & (agg.staleness == 0), 'Bias (relative)'),
                ('staleness', (agg.sigma == 0) & (agg.bias == 0), 'Staleness (intervals)')]
    for metric, lab in [('resp', 'Avg response time (s)'), ('slo', 'SLO violation rate'), ('energy', 'Energy / interval (kWh)')]:
        fig, axs = plt.subplots(1, 3, figsize=(13, 3.4))
        for a, (col, mask, xl) in zip(axs, axes_def):
            for s in scheds:
                sub = agg[mask & (agg.scheduler == s)].sort_values(col)
                if len(sub) < 2: continue
                a.plot(sub[col], sub[metric], marker='o', label=s, color=COLORS.get(s))
                if metric + '_sd' in sub:
                    a.fill_between(sub[col], sub[metric] - sub[metric + '_sd'], sub[metric] + sub[metric + '_sd'],
                                   color=COLORS.get(s), alpha=0.12)
            a.set_xlabel(xl); a.set_ylabel(lab); a.grid(alpha=0.3)
        axs[0].legend(fontsize=8)
        fig.tight_layout(); fig.savefig(os.path.join(FIG, f'error_{metric}.png'), dpi=160); plt.close(fig)
    return agg


if __name__ == '__main__' and sys.argv[1:2] not in (['final'], ['ci']):
    suites = sys.argv[1:] or ['reproduction']
    df = load(*suites)
    if suites == ['reproduction']: reproduction_table(df)
    else: error_tables(df)


# ------------------------------------------------------------ ablation / final
ABL = ['GOBI', 'GOBI+A', 'GOBI+B', 'R-GOBI']


def a3c_threshold():
    """Paper SLO: response time above the 95th percentile of A3C (Sec. 8.5)."""
    f = glob.glob(os.path.join(ROOT, 'results', 'reproduction', 'A3C_seed*.json'))
    return float(np.mean([json.load(open(x))['p95_response_time_s'] for x in f])) if f else None


def ablation(df):
    thr = a3c_threshold()
    df = df.copy(); df['condition'] = df.apply(condition_label, axis=1)
    if thr and 'response_times_s' in df:
        df['slo_paper'] = df.response_times_s.apply(
            lambda r: float(np.mean(np.array(r) > thr)) if isinstance(r, list) and len(r) else np.nan)
    df = df[df.scheduler.isin(ABL + ['GOBI*'])]
    clean = (df.sigma == 0) & (df.bias == 0) & (df.staleness == 0)
    g = df.groupby(['scheduler', 'condition', 'sigma', 'bias', 'staleness'])
    a = g.agg(resp=('avg_response_time_s', 'mean'), slo=('slo_violation_rate', 'mean'),
              slo_paper=('slo_paper', 'mean'), energy=('energy_per_interval_kWh', 'mean'),
              done=('completed_tasks', 'mean'), mig=('total_migrations', 'mean'),
              sched=('avg_scheduling_time_s', 'mean'), n=('seed', 'count')).reset_index()

    # Per condition: each variant vs GOBI under the same condition
    base = a[a.scheduler == 'GOBI'].set_index('condition')
    rows = []
    for _, r in a.iterrows():
        if r.condition not in base.index: continue
        b = base.loc[r.condition]
        rows.append({**r.to_dict(),
                     'resp_vs_GOBI_%': 100 * (r.resp / b.resp - 1),
                     'slo_pp_vs_GOBI': 100 * (r.slo - b.slo),
                     'energy_vs_GOBI_%': 100 * (r.energy / b.energy - 1),
                     'done_vs_GOBI_%': 100 * (r.done / b.done - 1)})
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(OUT, 'ablation_by_condition.csv'), index=False)

    # Summary: clean condition, mean over all error conditions, worst case
    summ = []
    for s in [x for x in ['GOBI*'] + ABL if x in set(t.scheduler)]:
        sub = t[t.scheduler == s]
        err = sub[~((sub.sigma == 0) & (sub.bias == 0) & (sub.staleness == 0))]
        cl = sub[(sub.sigma == 0) & (sub.bias == 0) & (sub.staleness == 0)]
        summ.append({'Scheduler': s,
                     'clean_resp': cl.resp.mean(), 'clean_slo': 100 * cl.slo.mean(), 'clean_energy': cl.energy.mean(),
                     'err_resp': err.resp.mean(), 'err_slo': 100 * err.slo.mean(),
                     'err_slo_paper': 100 * err.slo_paper.mean(), 'err_energy': err.energy.mean(),
                     'err_done': err.done.mean(), 'err_mig': err.mig.mean(),
                     'worst_slo': 100 * err.slo.max(), 'sched_time': sub.sched.mean(),
                     'resp_vs_GOBI_%': err['resp_vs_GOBI_%'].mean(), 'slo_pp_vs_GOBI': err.slo_pp_vs_GOBI.mean(),
                     'energy_vs_GOBI_%': err['energy_vs_GOBI_%'].mean(),
                     'wins_resp': f"{int((err['resp_vs_GOBI_%'] < 0).sum())}/{len(err)}"})
    S = pd.DataFrame(summ); S.to_csv(os.path.join(OUT, 'ablation_summary.csv'), index=False)
    lines = ['| Scheduler | Clean: resp (s) / SLO % / energy | Under error (mean of conditions): resp (s) | SLO % (code) | SLO % (paper def.) | Energy (kWh) | Completed | Migrations | Worst-case SLO % | Δresp vs GOBI | ΔSLO vs GOBI (pp) | Sched. time (s) |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for _, r in S.iterrows():
        lines.append(f"| {r.Scheduler} | {r.clean_resp:.0f} / {r.clean_slo:.1f} / {r.clean_energy:.3f} | {r.err_resp:.0f} | {r.err_slo:.1f} | "
                     f"{r.err_slo_paper:.1f} | {r.err_energy:.3f} | {r.err_done:.0f} | {r.err_mig:.0f} | {r.worst_slo:.1f} | "
                     f"{r['resp_vs_GOBI_%']:+.1f}% | {r.slo_pp_vs_GOBI:+.1f} | {r.sched_time:.2f} |")
    txt = f"A3C 95th-percentile threshold (paper SLO): {thr:.0f} s\n\n" + '\n'.join(lines) if thr else '\n'.join(lines)
    open(os.path.join(OUT, 'ablation_summary.md'), 'w', encoding='utf-8').write(txt + '\n')
    print(txt)

    # Per-condition table for the report
    piv = ['| Condition | ' + ' | '.join(s for s in ['GOBI*'] + ABL if s in set(t.scheduler)) + ' |']
    piv.append('|---|' + '---|' * (len(piv[0].split('|')) - 3))
    for c in list(dict.fromkeys(t.sort_values(['staleness', 'bias', 'sigma']).condition)):
        sub = t[t.condition == c].set_index('scheduler'); cells = []
        for s in [x for x in ['GOBI*'] + ABL if x in set(t.scheduler)]:
            cells.append(f"{sub.loc[s].resp:.0f} / {100*sub.loc[s].slo:.1f}%" if s in sub.index else '—')
        piv.append(f'| {c} | ' + ' | '.join(cells) + ' |')
    open(os.path.join(OUT, 'ablation_by_condition.md'), 'w', encoding='utf-8').write(
        'Cells: avg response time (s) / SLO violation rate (code definition)\n\n' + '\n'.join(piv) + '\n')
    print('\n'.join(piv))
    return t, S


if __name__ == '__main__' and sys.argv[1:2] == ['final']:
    t, S = ablation(load('gap', 'ours'))


# ------------------------------------------------------------ paired CI (Priority 3)
def paired_ci(df, a='GOBI', b='GOBI+B'):
    """Per condition: paired (same seed => same workload) difference b - a with 95% t-CI."""
    from scipy import stats
    df = df.copy(); df['condition'] = df.apply(condition_label, axis=1)
    rows = []
    order = ['σ=0.0', 'σ=0.8', 'bias +0.4', 'bias -0.4', 'stale k=2', 'stale k=4', 'σ=0.4,b=0.4,k=2']
    for c in order:
        sub = df[df.condition == c]
        A = sub[sub.scheduler == a].set_index('seed'); B = sub[sub.scheduler == b].set_index('seed')
        seeds = sorted(set(A.index) & set(B.index))
        if len(seeds) < 2: continue
        for m, scale, unit in (('slo_violation_rate', 100, 'pp'), ('avg_response_time_s', 1, 's')):
            d = scale * (B.loc[seeds, m].values - A.loc[seeds, m].values)
            half = stats.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d))
            p = stats.ttest_rel(B.loc[seeds, m].values, A.loc[seeds, m].values).pvalue if d.std() > 0 else 1.0
            rows.append({'condition': c, 'metric': m, 'n': len(seeds),
                         'a_mean': scale * A.loc[seeds, m].mean(), 'b_mean': scale * B.loc[seeds, m].mean(),
                         'a_sd': scale * A.loc[seeds, m].std(ddof=1), 'b_sd': scale * B.loc[seeds, m].std(ddof=1),
                         'diff': d.mean(), 'lo': d.mean() - half, 'hi': d.mean() + half, 'p': p,
                         'wins': int((d < 0).sum()), 'unit': unit})
    t = pd.DataFrame(rows); t.to_csv(os.path.join(OUT, 'paired_ci.csv'), index=False)
    out = []
    for m, lab in (('slo_violation_rate', 'SLO violation rate (%)'), ('avg_response_time_s', 'Average response time (s)')):
        s = t[t.metric == m]
        out += [f'**{lab}: {b} − {a}, paired by seed (negative = {b} better)**', '',
                f'| Condition | n seeds | {a} mean ± sd | {b} mean ± sd | Difference | 95% CI | p (paired t) | seeds where {b} better |',
                '|---|---|---|---|---|---|---|---|']
        p = 1 if m.startswith('slo') else 0
        for _, r in s.iterrows():
            sig = ' *' if r.hi < 0 or r.lo > 0 else ''
            out.append(f"| {r.condition} | {r.n} | {r.a_mean:.{p}f} ± {r.a_sd:.{p}f} | {r.b_mean:.{p}f} ± {r.b_sd:.{p}f} | "
                       f"{r['diff']:+.{p}f} {r.unit} | [{r.lo:+.{p}f}, {r.hi:+.{p}f}]{sig} | {r.p:.2f} | {r.wins}/{r.n} |")
        out.append('')
    # Pooled over the 6 error conditions (each seed-condition pair is one paired observation)
    for m, scale, unit in (('slo_violation_rate', 100, 'pp'), ('avg_response_time_s', 1, 's')):
        e = t[(t.metric == m) & (t.condition != 'σ=0.0')]
        if len(e):
            dd = []
            for c in e.condition:
                sub = df[df.condition == c]
                A = sub[sub.scheduler == a].set_index('seed')[m]; B = sub[sub.scheduler == b].set_index('seed')[m]
                ss = sorted(set(A.index) & set(B.index)); dd += list(scale * (B[ss].values - A[ss].values))
            dd = np.array(dd); half = stats.t.ppf(0.975, len(dd) - 1) * dd.std(ddof=1) / np.sqrt(len(dd))
            out.append(f"Pooled over all error conditions ({len(dd)} paired runs), {m}: "
                       f"{dd.mean():+.2f} {unit}, 95% CI [{dd.mean()-half:+.2f}, {dd.mean()+half:+.2f}], "
                       f"{b} better in {(dd < 0).sum()}/{len(dd)}")
    out.append('\n`*` = 95% CI excludes zero.')
    txt = '\n'.join(out)
    open(os.path.join(OUT, 'paired_ci.md'), 'w', encoding='utf-8').write(txt + '\n')
    print(txt)


if __name__ == '__main__' and sys.argv[1:2] == ['ci']:
    paired_ci(load('gap', 'ours'))
