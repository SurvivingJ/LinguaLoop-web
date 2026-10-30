"""Split fatseed_all/senses.csv into 6-sense RUN dirs (rows [start:end])."""
import csv, os, shutil, sys
csv.field_size_limit(10**9)
SRC = 'data/exercise_seeding/ja/fatseed_all'
start, end = int(sys.argv[1]), int(sys.argv[2])
with open(f'{SRC}/senses.csv', encoding='utf-8', newline='') as fh:
    rd = csv.DictReader(fh); cols = rd.fieldnames; rows = list(rd)[start:end]
for i in range(0, len(rows), 6):
    run = f'data/exercise_seeding/ja/wf/r{start + i:05d}'
    if os.path.exists(f'{run}/fat_seed/briefs/core_01.md'):
        continue
    os.makedirs(run, exist_ok=True)
    shutil.copy(f'{SRC}/prompts.json', run)
    with open(f'{run}/senses.csv', 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows[i:i + 6])
    print(run, flush=True)
