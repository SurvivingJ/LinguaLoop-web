"""Summarise raw simulation output into markdown tables. Standard library only.
Usage: python3 -I summarize.py RAW_JSON OUT_MD [RAW_JSON2 ...]
Later raw files are merged into the first by learner key; a design present in both is taken from the later file and the
earlier copy is kept under the name + 'i' (used for the first, superseded m+r model of D2-D4).
All figures are ESTIMATES from simulation."""
import json
import math
import sys
from collections import defaultdict

RAW, OUT = sys.argv[1], sys.argv[2]
D = json.load(open(RAW))
META, ROWS = D['meta'], D['rows']
for extra in sys.argv[3:]:
    E = json.load(open(extra))
    idx = {(r['lang'], r['prof'], r['skip'], r['idx']): r for r in E['rows']}
    for r in ROWS:
        e = idx.get((r['lang'], r['prof'], r['skip'], r['idx']))
        if not e:
            continue
        assert e['T_m'] == r['T_m'] and e['T_mr'] == r['T_mr'], 'learners differ between runs'
        for d, v in e['res'].items():
            if d in r['res']:
                r['res'][d + 'i'] = r['res'][d]
            r['res'][d] = v
    META['seconds'] = f"{META['seconds']} + {E['meta']['seconds']}"
READING = {'D2', 'D3', 'D4', 'D3S', 'D3L', 'D2i', 'D3i', 'D4i'}
POPNAME = {('zh', 'E'): 'zh, English L1', ('zh', 'J'): 'zh, Japanese L1 (cognates)',
           ('ja', 'E'): 'ja, English L1', ('ja', 'Z'): 'ja, Chinese L1 (cognates)'}
DESC = {'D0': 'fixed 10/band, meaning (today)', 'D1': 'IRT adaptive, meaning', 'D1S': 'adaptive bands, meaning',
        'D1L': 'adaptive exam levels, meaning', 'D2': 'IRT, meaning+reading every word',
        'D3': 'IRT, reading after correct meaning', 'D4': 'IRT, reading on half the words',
        'D3S': 'adaptive bands, reading after correct meaning', 'D3L': 'adaptive exam levels, reading after correct meaning',
        'D2i': 'D2 with first m+r model (superseded)', 'D3i': 'D3 with first m+r model (superseded)',
        'D4i': 'D4 with first m+r model (superseded)'}


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return float('nan')
    k = (len(xs) - 1) * q
    f = math.floor(k)
    c = min(len(xs) - 1, f + 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def mean(xs):
    return sum(xs) / len(xs) if xs else float('nan')


def snap_at(snaps, n):
    for s in snaps:
        if s['n'] >= n:
            return s
    return snaps[-1]


def snap_stop(snaps, h, N, cap, mn, reading):
    for s in snaps:
        if s['n'] < mn:
            continue
        if s['n'] >= cap:
            return s
        if s['hw'] <= h * N and (not reading or s['rhw'] <= h * N):
            return s
    return snaps[-1]


def metrics(pairs, design):
    """pairs: list of (row, snapshot)."""
    out = {}
    N = pairs[0][0]['N']
    reading = design in READING
    out['n'] = mean([s['n'] for r, s in pairs])
    out['n_lo'], out['n_hi'] = pct([s['n'] for r, s in pairs], .05), pct([s['n'] for r, s in pairs], .95)
    out['n_r'] = mean([s['n_r'] for r, s in pairs])
    out['min_b'] = mean([s['tb'] for r, s in pairs]) / 60
    out['min_m'] = mean([s['tm'] for r, s in pairs]) / 60
    out['min_m_hi'] = pct([s['tm'] for r, s in pairs], .95) / 60
    e = [(s['Tm'] - r['T_m']) / N * 100 for r, s in pairs]
    out['bias_m'] = mean(e)
    out['mae_m'] = mean([abs(x) for x in e])
    out['e5_m'], out['e95_m'] = pct(e, .05), pct(e, .95)
    out['mae_m_w'] = mean([abs(s['Tm'] - r['T_m']) for r, s in pairs])
    out['cov_m'] = mean([1.0 if s['lo'] <= r['T_m'] <= s['hi'] else 0.0 for r, s in pairs]) * 100
    out['hw_m'] = mean([s['hw'] for r, s in pairs]) / N * 100
    out['pl_m_exact'] = mean([1.0 if s['pm'] == r['pm'] else 0.0 for r, s in pairs]) * 100
    out['pl_m_1'] = mean([1.0 if abs(s['pm'] - r['pm']) <= 1 else 0.0 for r, s in pairs]) * 100
    out['lem'] = mean([s['lem'] for r, s in pairs]) * 100
    if reading:
        e2 = [(s['Tr'] - r['T_mr']) / N * 100 for r, s in pairs]
        out['bias_r'] = mean(e2)
        out['mae_r'] = mean([abs(x) for x in e2])
        out['e5_r'], out['e95_r'] = pct(e2, .05), pct(e2, .95)
        out['cov_r'] = mean([1.0 if s['rlo'] <= r['T_mr'] <= s['rhi'] else 0.0 for r, s in pairs]) * 100
        out['hw_r'] = mean([s['rhw'] for r, s in pairs]) / N * 100
        out['pl_r_exact'] = mean([1.0 if s['pr'] == r['pr'] else 0.0 for r, s in pairs]) * 100
        out['pl_r_1'] = mean([1.0 if abs(s['pr'] - r['pr']) <= 1 else 0.0 for r, s in pairs]) * 100
        out['ler'] = mean([s['ler'] for r, s in pairs]) * 100
        out['over_word'] = mean([1.0 if s['rlo'] > r['T_mr'] else 0.0 for r, s in pairs]) * 100
        out['overplace'] = mean([1.0 if s['pr'] > r['pr'] else 0.0 for r, s in pairs]) * 100
        rep = [(s['Tr'] - r['T_mr']) / N * 100 for r, s in pairs]
    else:
        # meaning-only designs: what they report as "known words" is the meaning count
        rep = [(s['Tm'] - r['T_mr']) / N * 100 for r, s in pairs]
        out['over_word'] = mean([1.0 if s['lo'] > r['T_mr'] else 0.0 for r, s in pairs]) * 100
        out['overplace'] = mean([1.0 if s['pm'] > r['pr'] else 0.0 for r, s in pairs]) * 100
        out['pl_r_exact'] = mean([1.0 if s['pm'] == r['pr'] else 0.0 for r, s in pairs]) * 100
        out['pl_r_1'] = mean([1.0 if abs(s['pm'] - r['pr']) <= 1 else 0.0 for r, s in pairs]) * 100
        out['cov_r'] = mean([1.0 if s['lo'] <= r['T_mr'] <= s['hi'] else 0.0 for r, s in pairs]) * 100
    out['rep_vs_mr'] = mean(rep)
    cr = sum(s['cr'] for r, s in pairs)
    out['cred'] = cr / len(pairs)
    out['cred_nmr'] = 100 * sum(s['cr_nmr'] for r, s in pairs) / cr if cr else float('nan')
    out['cred_nm'] = 100 * sum(s['cr_nm'] for r, s in pairs) / cr if cr else float('nan')
    return out


def f1(x):
    return '—' if x is None or (isinstance(x, float) and math.isnan(x)) else f'{x:.1f}'


def f0(x):
    return '—' if x is None or (isinstance(x, float) and math.isnan(x)) else f'{x:.0f}'


pops = []
for r in ROWS:
    k = (r['lang'], r['prof'], r['skip'])
    if k not in pops:
        pops.append(k)
designs = [d for d in DESC if d in ROWS[0]['res']]
by_pop = defaultdict(list)
for r in ROWS:
    by_pop[(r['lang'], r['prof'], r['skip'])].append(r)

L = []
L.append(f"# Simulation tables — run `{RAW.split('/')[-1]}`\n")
L.append(f"Learners per population: {META['n_learners']}. Config: `{json.dumps(META['cfg'])}`. Runtime {META['seconds']} s.\n")
L.append('All numbers are ESTIMATES from simulation. Errors are in % of the check pool (N words). '
         'Intervals are 90%. "e5..e95" is the 90% range of the error across learners.\n')

# population truth
L.append('## Populations (truth)\n')
L.append('| population | skip | N | mean known by meaning (% of N) | mean known by meaning+reading (%) | meaning-only words (% of known) | true placement by meaning: share at 0 / at max | by meaning+reading: 0 / max |')
L.append('|---|---|---|---|---|---|---|---|')
for k in pops:
    rs = by_pop[k]
    N = rs[0]['N']
    nlev = len(META['pool'][k[0]]['NL']) - 1
    tm, tr = mean([r['T_m'] for r in rs]), mean([r['T_mr'] for r in rs])
    L.append(f"| {POPNAME[(k[0], k[1])]} | {k[2]} | {N} | {100 * tm / N:.1f} | {100 * tr / N:.1f} | {100 * (tm - tr) / tm:.1f} | "
             f"{100 * mean([r['pm'] == 0 for r in rs]):.0f}% / {100 * mean([r['pm'] == nlev for r in rs]):.0f}% | "
             f"{100 * mean([r['pr'] == 0 for r in rs]):.0f}% / {100 * mean([r['pr'] == nlev for r in rs]):.0f}% |")
L.append('')

# budget table
BUDGET = {'D0': 70, 'D1': 40, 'D1S': 40, 'D1L': 40, 'D2': 60, 'D3': 60, 'D4': 60, 'D3S': 60, 'D3L': 60,
          'D2i': 60, 'D3i': 60, 'D4i': 60}
SUMMARY = {}


def budget_tables(title, pick):
    L.append(f'## {title}\n')
    for k in pops:
        rs = by_pop[k]
        L.append(f"### {POPNAME[(k[0], k[1])]}, skip-if-unknown {k[2]}\n")
        L.append('| design | items (reading) | min brief / measured | meaning: bias, MAE, e5..e95 | cover / half-width | '
                 'm+r: bias, MAE, e5..e95 | cover / half-width | place m exact/±1 | place m+r exact/±1 | '
                 '"known" interval above true m+r | credited words not known m+r / not known at all |')
        L.append('|---|---|---|---|---|---|---|---|---|---|---|')
        for d in designs:
            pairs = [(r, pick(r, d)) for r in rs]
            m = metrics(pairs, d)
            SUMMARY[(title, k, d)] = m
            rd = d in READING
            mr = (f"{f1(m['bias_r'])}, {f1(m['mae_r'])}, {f1(m['e5_r'])}..{f1(m['e95_r'])}" if rd else
                  f"(reports meaning) {f1(m['rep_vs_mr'])}")
            mrc = f"{f0(m['cov_r'])} / {f1(m['hw_r'])}" if rd else f"{f0(m['cov_r'])} / —"
            L.append(f"| {d} {DESC[d]} | {f0(m['n'])} ({f0(m['n_r'])}) | {f1(m['min_b'])} / {f1(m['min_m'])} | "
                     f"{f1(m['bias_m'])}, {f1(m['mae_m'])}, {f1(m['e5_m'])}..{f1(m['e95_m'])} | {f0(m['cov_m'])} / {f1(m['hw_m'])} | "
                     f"{mr} | {mrc} | {f0(m['pl_m_exact'])} / {f0(m['pl_m_1'])} | {f0(m['pl_r_exact'])} / {f0(m['pl_r_1'])} | "
                     f"{f0(m['over_word'])}% | {f1(m['cred_nmr'])}% / {f1(m['cred_nm'])}% |")
        L.append('')


budget_tables('At a fixed budget (D0 70, meaning-only 40, with readings 60 items)',
              lambda r, d: snap_at(r['res'][d], BUDGET[d]))

# precision vs items
L.append('## Precision vs number of items (fixed-length snapshots)\n')
L.append('Mean 90% half-width and MAE of the meaning count (and of the meaning+reading count for reading designs), '
         '% of N, averaged over all populations of the language; coverage in brackets.\n')
for lang in ('zh', 'ja'):
    L.append(f'### {lang}\n')
    NS = [20, 30, 40, 50, 60, 70, 90]
    L.append('| design | ' + ' | '.join(f'n={n}' for n in NS) + ' |')
    L.append('|---|' + '---|' * len(NS))
    for d in designs:
        cells = []
        for n in NS:
            pairs = [(r, snap_at(r['res'][d], n)) for k in pops if k[0] == lang for r in by_pop[k]]
            if pairs[0][1]['n'] < n - 2 and pairs[0][1] is pairs[0][0]['res'][d][-1]:
                cells.append('—')
                continue
            m = metrics(pairs, d)
            c = f"m ±{f1(m['hw_m'])} MAE {f1(m['mae_m'])} ({f0(m['cov_m'])}%)"
            if d in READING:
                c += f"; m+r ±{f1(m['hw_r'])} MAE {f1(m['mae_r'])} ({f0(m['cov_r'])}%)"
            cells.append(c)
        L.append(f'| {d} | ' + ' | '.join(cells) + ' |')
    L.append('')

# stopping rules
L.append('## Stopping rules (applied to the snapshots; stop at the first checkpoint where every reported 90% half-width '
         '<= h x N, after a minimum, else at the cap)\n')
RULES = [(0.10, 20, 40, 60), (0.12, 20, 40, 60), (0.08, 20, 60, 90), (0.10, 20, 60, 90)]
for h, mn, cap_m, cap_r in RULES:
    L.append(f'### h = {h}, min {mn}, cap {cap_m} (meaning-only) / {cap_r} (with readings)\n')
    L.append('| population | design | items mean (5..95%) | stopped before cap | minutes measured mean / 95th | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |')
    L.append('|---|---|---|---|---|---|---|---|')
    for k in pops:
        for d in designs:
            if d == 'D0':
                continue
            rd = d in READING
            cap = cap_r if rd else cap_m
            rs = by_pop[k]
            N = rs[0]['N']
            pairs = [(r, snap_stop(r['res'][d], h, N, cap, mn, rd)) for r in rs]
            m = metrics(pairs, d)
            early = mean([1.0 if s['n'] < cap else 0.0 for r, s in pairs]) * 100
            SUMMARY[(f'stop{h}_{cap_m}_{cap_r}', k, d)] = dict(m, early=early)
            L.append(f"| {POPNAME[(k[0], k[1])]} s={k[2]} | {d} | {f0(m['n'])} ({f0(m['n_lo'])}..{f0(m['n_hi'])}) | {f0(early)}% | "
                     f"{f1(m['min_m'])} / {f1(m['min_m_hi'])} | {f1(m['mae_m'])} / {f0(m['cov_m'])}% | "
                     f"{(f1(m['mae_r']) + ' / ' + f0(m['cov_r']) + '%') if rd else '—'} | {f0(m['pl_r_1'])} |")
    L.append('')

# ability breakdown at budget
L.append('## By ability (budget snapshot), all populations of a language pooled\n')
L.append('Ability groups by the learner\'s study frontier tau (Zipf at 50% known): beginner tau >= 5.5, '
         'intermediate 4.0-5.5, advanced < 4.0.\n')
L.append('| lang | design | group | n learners | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |')
L.append('|---|---|---|---|---|---|---|')
for lang in ('zh', 'ja'):
    for d in ('D0', 'D1', 'D1S', 'D3', 'D3S', 'D3L'):
        if d not in designs:
            continue
        for gname, lo, hi in (('beginner', 5.5, 99), ('intermediate', 4.0, 5.5), ('advanced', -99, 4.0)):
            rs = [r for k in pops if k[0] == lang for r in by_pop[k] if lo <= r['tau'] < hi]
            if not rs:
                continue
            m = metrics([(r, snap_at(r['res'][d], BUDGET[d])) for r in rs], d)
            rd = d in READING
            L.append(f"| {lang} | {d} | {gname} | {len(rs)} | {f1(m['mae_m'])} / {f0(m['cov_m'])}% | "
                     f"{(f1(m['mae_r']) + ' / ' + f0(m['cov_r']) + '%') if rd else '—'} | {f0(m['pl_r_1'])} |")
L.append('')

open(OUT, 'w', encoding='utf-8').write('\n'.join(L))
json.dump({'|'.join(map(str, [a, b[0], b[1], b[2], c])): v for (a, b, c), v in SUMMARY.items()},
          open(OUT.replace('.md', '.json'), 'w'), indent=0)
print('wrote', OUT)
