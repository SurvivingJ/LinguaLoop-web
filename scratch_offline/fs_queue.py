"""Print the next N pending jobs: review for authored-unreviewed runs first, then author."""
import glob, json, os, sys, csv
n = int(sys.argv[1])
def authored(run):
    ids = [r['sense_id'] for r in csv.DictReader(open(f'{run}/senses.csv', encoding='utf-8'))]
    for i in ids:
        p = f'{run}/fat_seed/words/{i}.json'
        if not os.path.exists(p): return False
        j = json.load(open(p))
        if 'variants' not in j and 'skip' not in j: return False
    return True
reviewed = lambda run: os.path.isdir(f'{run}/fat_seed/reviewed') and os.listdir(f'{run}/fat_seed/reviewed')
runs = [f'data/exercise_seeding/ja/wf/{r}' for r in json.load(open('data/exercise_seeding/ja/wf/review_only.json'))]
runs += sorted(glob.glob('data/exercise_seeding/ja/wf2/r*'))
inflight = set(open('scratch_offline/inflight.txt').read().split()) if os.path.exists('scratch_offline/inflight.txt') else set()
out = []
for r in runs:
    if r in inflight or reviewed(r): continue
    out.append(('review' if authored(r) else 'author', r))
    if len(out) >= n: break
for k, r in out: print(k, r)
