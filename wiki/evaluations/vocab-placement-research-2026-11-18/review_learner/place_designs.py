"""m+r placement within one level by TRUE level, per design, at the budget snapshot (read-only). Usage: python3 -I place_designs.py <raw_main.json> <raw_main_rho.json>"""
import json, sys
from collections import defaultdict
acc = defaultdict(list)
for path in sys.argv[1:]:
    d = json.load(open(path))
    for r in d['rows']:
        for des, sn in r['res'].items():
            if des not in ('D3S', 'D3L', 'D3', 'D0', 'D1S'):
                continue
            s = next((x for x in sn if x['n'] >= (70 if des == 'D0' else 40 if des == 'D1S' else 60)), sn[-1])
            est = s.get('pr', s['pm'])
            acc[(r['lang'], des, r['pr'])].append(est - r['pr'])
print('lang design | within one level for true m+r level 2, 3, 4, 5, 6 (n) ; meaning-only designs use their meaning placement')
for lang in ('zh', 'ja'):
    for des in ('D0', 'D1S', 'D3', 'D3S', 'D3L'):
        cells = []
        for lv in range(2, 7 if lang == 'zh' else 5):
            e = acc.get((lang, des, lv), [])
            if e:
                cells.append(f'L{lv} {100*sum(abs(x)<=1 for x in e)/len(e):.0f}% ({len(e)})')
        print(lang, des, ' | '.join(cells))
