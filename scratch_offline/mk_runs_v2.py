"""Regroup unauthored senses into 12-sense runs with each lemma's senses together.

Runs under wf/ whose words are all authored stay as they are (review only).
Unauthored wf/ runs are left on disk untouched and simply not used.
"""
import csv, glob, json, os, shutil
csv.field_size_limit(10**9)
SRC = 'data/exercise_seeding/ja/fatseed_all'
done_runs, done_ids = [], set()
for run in sorted(glob.glob('data/exercise_seeding/ja/wf/r*')):
    ids = [r['sense_id'] for r in csv.DictReader(open(f'{run}/senses.csv', encoding='utf-8'))]
    docs = [f'{run}/fat_seed/words/{i}.json' for i in ids]
    def ok(d):
        if not os.path.exists(d): return False
        j = json.load(open(d)); return 'variants' in j or 'skip' in j
    if all(ok(d) for d in docs):
        done_runs.append(run); done_ids.update(ids)
with open(f'{SRC}/senses.csv', encoding='utf-8', newline='') as fh:
    rd = csv.DictReader(fh); cols = rd.fieldnames; rows = list(rd)[144:]
rows = [r for r in rows if r['sense_id'] not in done_ids]
order, groups = [], {}
for r in rows:
    if r['lemma'] not in groups:
        order.append(r['lemma']); groups[r['lemma']] = []
    groups[r['lemma']].append(r)
chunks, cur = [], []
for lemma in order:
    g = groups[lemma]
    if cur and len(cur) + len(g) > 12:
        chunks.append(cur); cur = []
    cur += g
if cur: chunks.append(cur)
for i, chunk in enumerate(chunks):
    run = f'data/exercise_seeding/ja/wf2/r{i:04d}'
    os.makedirs(run, exist_ok=True)
    shutil.copy(f'{SRC}/prompts.json', run)
    with open(f'{run}/senses.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(chunk)
json.dump([os.path.basename(r) for r in done_runs], open('data/exercise_seeding/ja/wf/review_only.json', 'w'))
print(len(done_runs), 'authored runs kept;', len(rows), 'senses ->', len(chunks), 'new runs')
