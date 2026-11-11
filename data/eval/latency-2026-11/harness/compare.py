"""Before/after tables (markdown) for the SQL, HTTP and browser benchmarks."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from stats import summ
R = os.path.join(os.path.dirname(__file__), 'results')
SLUG = 'ja-d1-a-roman-child-s-wooden-toy-hor-20260823223156'
K = ('mean', 'median', 'p90', 'p95', 'p99', 'max')

def fmt(s): return ' | '.join(f"{s[k]:.0f}" if s[k] >= 10 else f"{s[k]:.1f}" for k in K)
def pct(a, b): return f"{(b - a) / a * 100:+.0f}%" if a else 'n/a'

def table(title, rows, extra_hdr=''):
    print(f"\n### {title}\n")
    print(f"| {extra_hdr or 'Item'} | run | n | mean | median | p90 | p95 | p99 | max | Δ median |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name, b, a, note in rows:
        sb, sa = summ(b), summ(a)
        print(f"| {name}{note} | before | {sb['n']} | {fmt(sb)} | |")
        print(f"| | after | {sa['n']} | {fmt(sa)} | **{pct(sb['median'], sa['median'])}** |")

def short(ep): return ep.split('?')[0].replace('/api/', '').replace(SLUG, '<slug>')

which = sys.argv[1:] or ['sql', 'http', 'browser']
if 'sql' in which and os.path.exists(f'{R}/sql_after.json'):
    b, a = json.load(open(f'{R}/sql_before.json')), json.load(open(f'{R}/sql_after.json'))
    table('SQL functions, server-side (ms per call)', [(f'`{k}`', b[k], a[k], '') for k in b if k in a], 'Function')
if 'http' in which and os.path.exists(f'{R}/http_after.json'):
    b, a = json.load(open(f'{R}/http_before.json')), json.load(open(f'{R}/http_after.json'))
    rows = []
    for ep in b:
        if ep in a:
            rows.append((f'`{short(ep)}`', [s['wall'] for s in b[ep]], [s['wall'] for s in a[ep]],
                         f" ({b[ep][-1]['calls']}→{a[ep][-1]['calls']} DB calls)"))
    table('HTTP endpoints, wall time (ms)', rows, 'Endpoint')
if 'browser' in which and os.path.exists(f'{R}/browser_after.json'):
    b, a = json.load(open(f'{R}/browser_before.json')), json.load(open(f'{R}/browser_after.json'))
    for mode in ('cold', 'warm'):
        rows = []
        for url in b:
            if url in a:
                rows.append((f'`{url.replace(SLUG, "<slug>")}`', [x['dataReady'] for x in b[url][mode]],
                             [x['dataReady'] for x in a[url][mode]], ''))
        table(f'Browser: navigation start → last API response ({mode} cache), ms', rows, 'Page')
    print('\n### Browser: bytes transferred and requests per load (median)\n')
    print('| Page | cold KB before | cold KB after | warm KB before | warm KB after | requests before | requests after | API calls before | API calls after |')
    print('|---|---|---|---|---|---|---|---|---|')
    med = lambda xs: sorted(xs)[len(xs) // 2]
    for url in b:
        if url not in a: continue
        f = lambda d, m, k: med([x[k] for x in d[url][m]])
        print(f"| `{url.replace(SLUG, '<slug>')}` | {f(b,'cold','transfer')/1024:.0f} | {f(a,'cold','transfer')/1024:.0f} | "
              f"{f(b,'warm','transfer')/1024:.0f} | {f(a,'warm','transfer')/1024:.0f} | {f(b,'cold','requests')} | {f(a,'cold','requests')} | "
              f"{len(b[url]['cold'][0]['apiCalls'])} | {len(a[url]['cold'][0]['apiCalls'])} |")
