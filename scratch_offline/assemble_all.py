"""Assemble every reviewed run and capture the uploader's writes into one file.

    python3 scratch_offline/assemble_all.py [--lang ja] [--runs-glob GLOB ...] [--out DIR]

For each run with reviewed documents: `fat_seed_runner.py assemble`, then the
real `upload_exercises.py` (core, then exercises, --no-render) with its DB
writes captured by the offline shim instead of executed. The captured writes
of every run are concatenated into OUT/writes.jsonl for package_upload.py.
Runs already captured (RUN/upload_writes.jsonl) are reused; delete that file
and RUN/07_upload/ to re-assemble a run.
"""
import argparse
import glob
import json
import os
import subprocess

ENV = {'PYTHONIOENCODING': 'utf-8', 'PATH': '/usr/bin:/bin:/usr/local/bin'}
SNAP = 'scratch_offline/snap/writes.jsonl'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lang', default='ja')
    ap.add_argument('--runs-glob', nargs='*', default=None,
                    help='default: data/exercise_seeding/<lang>/wf/r* and .../wf2/r*')
    ap.add_argument('--out', default='', help='default: data/exercise_seeding/<lang>/payload_wf')
    args = ap.parse_args()
    base = f'data/exercise_seeding/{args.lang}'
    globs = args.runs_glob or [f'{base}/wf/r*', f'{base}/wf2/r*']
    out = args.out or f'{base}/payload_wf'
    os.makedirs(out, exist_ok=True)
    done, skipped = [], []
    runs = sorted(r for g in globs for r in glob.glob(g) if os.path.isdir(r))
    for run in runs:
        if not glob.glob(f'{run}/fat_seed/reviewed/*.json'):
            skipped.append((run, 'not reviewed'))
            continue
        if not os.path.exists(f'{run}/07_upload/batch_001.core.json'):
            r = subprocess.run(['python3', 'scratch_offline/run.py', 'scripts/fat_seed_runner.py', 'assemble', run],
                               capture_output=True, text=True, env=ENV)
            if not os.path.exists(f'{run}/07_upload/batch_001.core.json'):
                skipped.append((run, r.stderr.strip().splitlines()[-1:]))
                continue
        if os.path.exists(f'{run}/upload_writes.jsonl'):
            done.append(run)
            continue
        if os.path.exists(SNAP):
            os.remove(SNAP)
        for st in ('core', 'exercises'):
            subprocess.run(['python3', 'scratch_offline/run.py', 'scripts/upload_exercises.py', '--stage', st,
                            '--no-render', '--source-model', 'claude-code:fat-seed',
                            '--batch-file', f'{run}/07_upload/batch_001.{st}.batch.json',
                            '--answers-file', f'{run}/07_upload/batch_001.{st}.json'],
                           capture_output=True, text=True, env=ENV)
        if os.path.exists(SNAP):
            os.replace(SNAP, f'{run}/upload_writes.jsonl')
            done.append(run)
        else:
            skipped.append((run, 'no writes'))
    with open(f'{out}/writes.jsonl', 'w', encoding='utf-8') as fh:
        for run in done:
            fh.write(open(f'{run}/upload_writes.jsonl', encoding='utf-8').read())
    json.dump(skipped, open(f'{out}/skipped.json', 'w'), ensure_ascii=False, indent=1)
    print(len(done), 'runs assembled;', len(skipped), 'skipped')


if __name__ == '__main__':
    main()
