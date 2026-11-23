"""Condense summarize.py JSON into the report's headline tables. Usage: python3 -I condense.py TABLES_JSON [mode]
mode 'main' (default) or 'sens' (one compact table). All numbers are ESTIMATES from simulation."""
import json
import sys

S = json.load(open(sys.argv[1]))
MODE = sys.argv[2] if len(sys.argv) > 2 else 'main'
BUD = 'At a fixed budget (D0 70, meaning-only 40, with readings 60 items)'
PROF = [('zh', 'E'), ('zh', 'J'), ('ja', 'E'), ('ja', 'Z')]
PN = {('zh', 'E'): 'zh·en-L1', ('zh', 'J'): 'zh·ja-L1', ('ja', 'E'): 'ja·en-L1', ('ja', 'Z'): 'ja·zh-L1'}
READ = {'D2', 'D3', 'D4', 'D3S', 'D3L', 'D2i', 'D3i', 'D4i'}


def get(title, lang, prof, skip, d):
    return S.get(f'{title}|{lang}|{prof}|{skip}|{d}')


def avg(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def f(x, nd=1):
    return '—' if x is None else f'{x:.{nd}f}'


designs = []
for k in S:
    d = k.split('|')[-1]
    if d not in designs:
        designs.append(d)
skips = sorted({k.split('|')[3] for k in S})


def row_metric(title, d, key, profs=PROF, skp=None):
    out = []
    for p in profs:
        ms = [get(title, p[0], p[1], s, d) for s in (skp or skips)]
        out.append(avg([m.get(key) if m else None for m in ms]))
    return out


if MODE == 'main':
    print('#### Table 1. Length and time (budget snapshot; mean over all populations)\n')
    print('| design | items | of which reading | minutes, brief (6 s / 5 s) | minutes, measured latencies (mean / 95th pct) |')
    print('|---|---|---|---|---|')
    for d in designs:
        g = lambda key: avg(row_metric(BUD, d, key))
        print(f"| {d} | {f(g('n'), 0)} | {f(g('n_r'), 0)} | {f(g('min_b'))} | {f(g('min_m'))} / {f(g('min_m_hi'))} |")
    for title, key_mae, key_cov, key_hw, key_bias, lab in (
            ('Table 2. Words known by MEANING in the pool', 'mae_m', 'cov_m', 'hw_m', 'bias_m', 'meaning'),
            ('Table 3. Words known by MEANING AND READING ("knows the word")', 'mae_r', 'cov_r', 'hw_r', 'bias_r', 'm+r')):
        print(f'\n#### {title} — budget snapshot; MAE / 90% coverage / mean 90% half-width, % of the pool; '
              'both skip settings averaged\n')
        print('| design | ' + ' | '.join(PN[p] for p in PROF) + ' | bias range |')
        print('|---|' + '---|' * (len(PROF) + 1))
        for d in designs:
            if lab == 'm+r' and d not in READ:
                cells = []
                for p in PROF:
                    ms = [get(BUD, p[0], p[1], s, d) for s in skips]
                    v = avg([m['rep_vs_mr'] for m in ms])
                    cells.append(f"reports meaning: {'+' if v >= 0 else ''}{f(v)} / {f(avg([m['cov_r'] for m in ms]), 0)}%")
                print(f'| {d} | ' + ' | '.join(cells) + ' | |')
                continue
            cells, biases = [], []
            for p in PROF:
                ms = [get(BUD, p[0], p[1], s, d) for s in skips]
                cells.append(f"{f(avg([m[key_mae] for m in ms]))} / {f(avg([m[key_cov] for m in ms]), 0)}% / ±{f(avg([m[key_hw] for m in ms]))}")
                biases += [m[key_bias] for m in ms]
            print(f'| {d} | ' + ' | '.join(cells) + f' | {f(min(biases))}..{f(max(biases))} |')
    print('\n#### Table 4. Exam placement (HSK 2025 for zh, JLPT for ja): exact / within one level, "knows the word" '
          '(meaning-only designs: their meaning placement vs the true "knows the word" placement); in brackets the '
          'same for meaning placement vs true meaning placement\n')
    print('| design | ' + ' | '.join(PN[p] for p in PROF) + ' |')
    print('|---|' + '---|' * len(PROF))
    for d in designs:
        cells = []
        for p in PROF:
            ms = [get(BUD, p[0], p[1], s, d) for s in skips]
            cells.append(f"{f(avg([m['pl_r_exact'] for m in ms]), 0)} / {f(avg([m['pl_r_1'] for m in ms]), 0)} "
                         f"({f(avg([m['pl_m_exact'] for m in ms]), 0)} / {f(avg([m['pl_m_1'] for m in ms]), 0)})")
        print(f'| {d} | ' + ' | '.join(cells) + ' |')
    print('\n#### Table 4b. Mean absolute error of the cumulative per-level known share (percentage points), '
          'meaning / "knows the word"\n')
    print('| design | ' + ' | '.join(PN[p] for p in PROF) + ' |')
    print('|---|' + '---|' * len(PROF))
    for d in designs:
        cells = []
        for p in PROF:
            ms = [get(BUD, p[0], p[1], s, d) for s in skips]
            cells.append(f"{f(avg([m['lem'] for m in ms]))} / {f(avg([m['ler'] for m in ms])) if d in READ else '—'}")
        print(f'| {d} | ' + ' | '.join(cells) + ' |')
    print('\n#### Table 5. Mislabelling "knows the word" (budget snapshot, both skip settings averaged)\n')
    print('Columns per population: reported known-words count minus true "knows the word" count (% of pool) · '
          'learners whose whole reported interval lies above their true count · learners placed above their true '
          '"knows the word" level · credited words the learner does not know by meaning and reading.\n')
    print('| design | ' + ' | '.join(PN[p] for p in PROF) + ' |')
    print('|---|' + '---|' * len(PROF))
    for d in designs:
        cells = []
        for p in PROF:
            ms = [get(BUD, p[0], p[1], s, d) for s in skips]
            cells.append(f"{'+' if avg([m['rep_vs_mr'] for m in ms]) >= 0 else ''}{f(avg([m['rep_vs_mr'] for m in ms]))} · "
                         f"{f(avg([m['over_word'] for m in ms]), 0)}% · {f(avg([m['overplace'] for m in ms]), 0)}% · "
                         f"{f(avg([m['cred_nmr'] for m in ms]), 0)}%")
        print(f'| {d} | ' + ' | '.join(cells) + ' |')
    print('\n#### Table 5b. Credited words that are lucky guesses (not known even by meaning), by skip setting\n')
    print('| design | ' + ' | '.join(f'{PN[p]} s=0.3 / 0.7' for p in PROF) + ' |')
    print('|---|' + '---|' * len(PROF))
    for d in designs:
        cells = []
        for p in PROF:
            a = get(BUD, p[0], p[1], '0.3', d)
            b = get(BUD, p[0], p[1], '0.7', d)
            cells.append(f"{f(a['cred_nm'], 0) if a else '—'}% / {f(b['cred_nm'], 0) if b else '—'}%")
        print(f'| {d} | ' + ' | '.join(cells) + ' |')
else:
    title = BUD
    profs = sorted({(k.split('|')[1], k.split('|')[2]) for k in S if k.startswith(BUD)})
    print('| design | population | items | meaning MAE / cover / ±hw | m+r MAE / cover / ±hw | place m+r exact / ±1 | credited not m+r |')
    print('|---|---|---|---|---|---|---|')
    for d in designs:
        for p in profs:
            ms = [get(BUD, p[0], p[1], s, d) for s in skips]
            ms = [m for m in ms if m]
            if not ms:
                continue
            g = lambda key: avg([m.get(key) for m in ms])
            mr = (f"{f(g('mae_r'))} / {f(g('cov_r'), 0)}% / ±{f(g('hw_r'))}" if d in READ else
                  f"reports meaning +{f(g('rep_vs_mr'))}")
            print(f"| {d} | {PN.get(p, p)} | {f(g('n'), 0)} | {f(g('mae_m'))} / {f(g('cov_m'), 0)}% / ±{f(g('hw_m'))} | {mr} | "
                  f"{f(g('pl_r_exact'), 0)} / {f(g('pl_r_1'), 0)} | {f(g('cred_nmr'), 0)}% |")
