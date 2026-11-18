"""Summarise psy_sim.py output. Usage: python3 -I analyse.py RUN.json [stop|cap]"""
import json
import sys
from collections import defaultdict, Counter

D = json.load(open(sys.argv[1]))
KEY = sys.argv[2] if len(sys.argv) > 2 else 'stop'
rows = D['rows']
POPS = [('zh', 'E'), ('zh', 'J'), ('ja', 'E'), ('ja', 'Z')]
NAMES = {('zh', 'E'): 'zh·en-L1', ('zh', 'J'): 'zh·ja-L1', ('ja', 'E'): 'ja·en-L1', ('ja', 'Z'): 'ja·zh-L1'}


def grp(t):
    return 'beginner' if t >= 5.5 else ('intermediate' if t >= 4.0 else 'advanced')


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float('nan')


def pc(x):
    return f'{100 * x:.0f}%'


print(f'# {sys.argv[1]} [{KEY}] extra={D["extra"]} n/pop={D["npp"]}\n')
print('## Length, stop, counts (95% intervals, ADR-051 rules)')
print('| pop | items | early stop | early stop: beg / int / adv | m bias / MAE / cover95 | m+r bias / MAE / cover95 | guard binds (lo or hi) |')
print('|---|---|---|---|---|---|---|')
for p in POPS:
    rs = [r for r in rows if (r['lang'], r['prof']) == p]
    N = rs[0]['N']
    s = [r[KEY] for r in rs]
    early = [x['reason'] == 'precision' for x in s]
    eg = {g: mean(x['reason'] == 'precision' for r, x in zip(rs, s) if grp(r['tau']) == g) for g in ('beginner', 'intermediate', 'advanced')}
    out = [NAMES[p], f"{mean(x['items'] for x in s):.1f}", pc(mean(early)),
           ' / '.join(pc(eg[g]) for g in ('beginner', 'intermediate', 'advanced'))]
    for k in ('m', 'mr'):
        b = mean((x[k]['T'] - x[k]['truth']) / N for x in s)
        mae = mean(abs(x[k]['T'] - x[k]['truth']) / N for x in s)
        cov = mean(x[k]['cover'] for x in s)
        out.append(f'{100 * b:+.1f} / {100 * mae:.1f} / {pc(cov)}')
    out.append(pc(mean(x['guard_lo'] or x['guard_hi'] for x in s)))
    print('| ' + ' | '.join(out) + ' |')

print('\n## ADR-051 labels a placement alone receives (m+r headline / meaning)')
print('| pop | m+r labels | meaning labels |')
print('|---|---|---|')
for p in POPS:
    s = [r[KEY] for r in rows if (r['lang'], r['prof']) == p]
    out = [NAMES[p]]
    for k in ('mr', 'm'):
        c = Counter(x[k]['label'] for x in s)
        out.append(', '.join(f'{lab} {pc(c[lab] / len(s))}' for lab in ('good', 'medium', 'rough', 'fewer_than', 'too_uncertain') if c[lab]))
    print('| ' + ' | '.join(out) + ' |')

print('\n## Level range of draft §5.3 (95% bounds, 80% threshold), m+r; truth = placement over pool list words')
print('| pop | point ±1 (sim metric) | range contains truth | lower = 0 | lower=0 among true place ≥ 2 | upper = 0 | lower = upper | mean width (levels) | copy: "k" / "a–b" / "at most k" / "not yet" |')
print('|---|---|---|---|---|---|---|---|---|')
for p in POPS:
    s = [r[KEY]['mr'] for r in rows if (r['lang'], r['prof']) == p]
    pt = mean(abs(x['point'] - x['place_true']) <= 1 for x in s)
    cont = mean(x['lower'] <= x['place_true'] <= x['upper'] for x in s)
    l0 = mean(x['lower'] == 0 for x in s)
    hi_true = [x for x in s if x['place_true'] >= 2]
    l0b = mean(x['lower'] == 0 for x in hi_true)
    u0 = mean(x['upper'] == 0 for x in s)
    eq = mean(x['lower'] == x['upper'] for x in s)
    wid = mean(x['upper'] - x['lower'] for x in s)
    cases = Counter()
    for x in s:
        if x['upper'] == 0:
            cases['not yet'] += 1
        elif x['lower'] == 0:
            cases['at most'] += 1
        elif x['lower'] == x['upper']:
            cases['k'] += 1
        else:
            cases['a-b'] += 1
    cs = ' / '.join(pc(cases[c] / len(s)) for c in ('k', 'a-b', 'at most', 'not yet'))
    print(f'| {NAMES[p]} | {pc(pt)} | {pc(cont)} | {pc(l0)} | {pc(l0b)} (n={len(hi_true)}) | {pc(u0)} | {pc(eq)} | {wid:.2f} | {cs} |')

print('\n## Level range by true m+r placement (all pops of a language pooled)')
for lang in ('zh', 'ja'):
    s = [r[KEY]['mr'] for r in rows if r['lang'] == lang]
    byt = defaultdict(list)
    for x in s:
        byt[x['place_true']].append(x)
    print(f'\n{lang}: true place -> n, mean lower, mean upper, share lower=0, share range contains truth, share point ±1')
    for t in sorted(byt):
        xs = byt[t]
        print(f'  {t}: n={len(xs)}, lower {mean(x["lower"] for x in xs):.2f}, upper {mean(x["upper"] for x in xs):.2f}, '
              f'lower=0 {pc(mean(x["lower"] == 0 for x in xs))}, contains {pc(mean(x["lower"] <= t <= x["upper"] for x in xs))}, '
              f'point±1 {pc(mean(abs(x["point"] - t) <= 1 for x in xs))}')

print('\n## Per-band bias of K_b (estimate minus the learner\'s true band share), by true share; m+r and meaning')
for lang in ('zh', 'ja'):
    for k, ti, ei in (('m', 1, 2), ('mr', 4, 5)):
        bins = defaultdict(list)
        nn = defaultdict(list)
        for r in rows:
            if r['lang'] != lang:
                continue
            for b in r[KEY]['bands']:
                t = b[ti]
                key = min(4, int(t * 5))
                bins[key].append(b[ei] - t)
                nn[key].append(b[3])
        print(f'{lang} {k}: ' + '; '.join(f'true {kk / 5:.1f}-{(kk + 1) / 5:.1f}: bias {mean(bins[kk]):+.3f} (n_b mean {mean(nn[kk]):.1f}, N={len(bins[kk])})' for kk in sorted(bins)))

print('\n## Probes')
for p in POPS:
    s = [r[KEY]['probes'] for r in rows if (r['lang'], r['prof']) == p]
    n = sum(x['probes'] for x in s)
    print(f"{NAMES[p]}: probes/test {mean(x['probes'] for x in s):.2f}; pooled right {sum(x['probe_r'] for x in s)}, wrong {sum(x['probe_w'] for x in s)}, skip {sum(x['probe_s'] for x in s)} of {n}")
