"""HSK 2025 words: in the live check pool (zh, def en, has_embedding; ids from the sim's read-only SELECT) vs in the
dictionary export but not in the pool. Zipf medians and band-matched comparison. Untrusted list files only read."""
import json, os, sys, statistics as st, collections, csv
SCR = sys.argv[1]
sys.path.insert(0, os.path.join(SCR, 'placement', 'sim'))
import pool as P
ids = json.load(open(f'{SCR}/placement/sim/data/anchor_pool_ids.json'))
poolids = set(ids['1_def_en'])
lem = {}
for line in open(f'{SCR}/kr/db_export/zh_vocab.tsv', encoding='utf-8'):
    p = line.rstrip('\n').split('\t')
    if len(p) < 4 or not p[0].isdigit(): continue
    try: z = float(p[3])
    except ValueError: continue
    lem.setdefault(p[1], (int(p[0]), z))
print('dict lemmas', len(lem), 'pool ids', len(poolids), 'pool ids in export', sum(1 for v in lem.values() if v[0] in poolids))
tot_in = tot_out = 0
for lv in ['1', '2', '3', '4', '5', '6', '7-9']:
    seen = set(); inp, outp = [], []; miss = 0
    for line in open(f'{SCR}/kr/lists/krmanik_HSK-3.0/2025/HSK_Level_{lv}_words.txt', encoding='utf-8'):
        raw = line.strip()
        if not raw: continue
        forms = P.expand_zh(raw)
        if not forms or forms[0] in seen: continue
        seen.add(forms[0])
        hit = next((f for f in forms if f in lem), None)
        if hit is None: miss += 1; continue
        vid, z = lem[hit]
        (inp if vid in poolids else outp).append(z)
    # band-matched: share of out-of-pool words per band
    bin_ = lambda z: P.band_of(z)
    bi = collections.Counter(map(bin_, inp)); bo = collections.Counter(map(bin_, outp))
    print(f'HSK {lv}: list {len(seen)}; in pool {len(inp)} ({100*len(inp)/len(seen):.0f}%), median Zipf {st.median(inp):.2f}; '
          f'in dictionary not pool {len(outp)}, median Zipf {st.median(outp) if outp else float("nan"):.2f}; not in dictionary {miss}; '
          f'band mix in/out (b1..b7) {[bi[b] for b in range(1,8)]} / {[bo[b] for b in range(1,8)]}')
