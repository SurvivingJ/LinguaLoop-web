"""Assemble every reviewed wf/ run, capture uploader writes, build one payload."""
import glob, json, os, subprocess
ENV = {'PYTHONIOENCODING': 'utf-8', 'PATH': '/usr/bin:/bin:/usr/local/bin'}
OUT = 'data/exercise_seeding/ja/payload_wf'
os.makedirs(OUT, exist_ok=True)
SNAP = 'scratch_offline/snap/writes.jsonl'
done, skipped = [], []
for run in sorted(glob.glob('data/exercise_seeding/ja/wf/r*') + glob.glob('data/exercise_seeding/ja/wf2/r*')):
    if not glob.glob(f'{run}/fat_seed/reviewed/*.json'):
        skipped.append((run, 'not reviewed')); continue
    if not os.path.exists(f'{run}/07_upload/batch_001.core.json'):
        r = subprocess.run(['python3', 'scratch_offline/run.py', 'scripts/fat_seed_runner.py', 'assemble', run],
                           capture_output=True, text=True, env=ENV)
        if not os.path.exists(f'{run}/07_upload/batch_001.core.json'):
            skipped.append((run, r.stderr.strip().splitlines()[-1:] )); continue
    if os.path.exists(f'{run}/upload_writes.jsonl'):
        done.append(run); continue
    if os.path.exists(SNAP): os.remove(SNAP)
    for st in ('core', 'exercises'):
        subprocess.run(['python3', 'scratch_offline/run.py', 'scripts/upload_exercises.py', '--stage', st,
                        '--no-render', '--source-model', 'claude-code:fat-seed',
                        '--batch-file', f'{run}/07_upload/batch_001.{st}.batch.json',
                        '--answers-file', f'{run}/07_upload/batch_001.{st}.json'],
                       capture_output=True, text=True, env=ENV)
    if os.path.exists(SNAP):
        os.replace(SNAP, f'{run}/upload_writes.jsonl'); done.append(run)
    else:
        skipped.append((run, 'no writes'))
with open(f'{OUT}/writes.jsonl', 'w', encoding='utf-8') as fh:
    for run in done:
        fh.write(open(f'{run}/upload_writes.jsonl', encoding='utf-8').read())
json.dump(skipped, open(f'{OUT}/skipped.json', 'w'), ensure_ascii=False, indent=1)
print(len(done), 'runs assembled;', len(skipped), 'skipped')
