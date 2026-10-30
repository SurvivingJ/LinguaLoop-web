"""Split an exported worklist into run directories for nt_pipeline.py.

    python3 scratch_offline/nt_make_runs.py EXPORT_DIR RUNS_DIR [--size 12]

EXPORT_DIR is the output of `scripts/export_exercise_worklist.py --format csv`
(senses.csv + prompts.json). Senses are packed into runs of at most --size,
with every sense of a lemma in the same run: the reviewer and the core audit
see the siblings together. Senses that already have a review record (or a
skip document) in an existing run under RUNS_DIR are left out, so the script
can be re-run after a new export; new runs are numbered after the highest
existing one.
"""
import argparse
import csv
import glob
import json
import os
import shutil

csv.field_size_limit(10 ** 9)


def finished(runs_dir):
    done = set()
    for run in glob.glob(os.path.join(runs_dir, 'r*')):
        done |= {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(run, 'fat_seed', 'review', '*.json'))}
        for f in glob.glob(os.path.join(run, 'fat_seed', 'words', '*.json')):
            try:
                if json.load(open(f, encoding='utf-8')).get('skip'):
                    done.add(os.path.basename(f)[:-5])
            except (json.JSONDecodeError, OSError):
                pass
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('export_dir')
    ap.add_argument('runs_dir')
    ap.add_argument('--size', type=int, default=12)
    args = ap.parse_args()
    with open(os.path.join(args.export_dir, 'senses.csv'), encoding='utf-8', newline='') as fh:
        rd = csv.DictReader(fh)
        cols, rows = rd.fieldnames, list(rd)
    done = finished(args.runs_dir)
    todo = [r for r in rows if r['sense_id'] not in done]
    groups = {}
    for r in todo:  # keep the export's ranking order within and across lemmas
        groups.setdefault(r['lemma'], []).append(r)
    runs = []
    for g in groups.values():
        for run in runs:
            if len(run) + len(g) <= args.size:
                run.extend(g)
                break
        else:
            runs.append(list(g))
    os.makedirs(args.runs_dir, exist_ok=True)
    existing = [int(os.path.basename(d)[1:]) for d in glob.glob(os.path.join(args.runs_dir, 'r[0-9]*'))
                if os.path.basename(d)[1:].isdigit()]
    nxt = max(existing, default=-1) + 1
    for i, run in enumerate(runs):
        d = os.path.join(args.runs_dir, f'r{nxt + i:04d}')
        os.makedirs(d)
        shutil.copy(os.path.join(args.export_dir, 'prompts.json'), d)
        with open(os.path.join(d, 'senses.csv'), 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(run)
    print(f'{len(rows)} exported, {len(rows) - len(todo)} already finished, '
          f'{len(todo)} senses in {len(runs)} new runs '
          f'(r{nxt:04d}..r{nxt + len(runs) - 1:04d}) under {args.runs_dir}')


if __name__ == '__main__':
    main()
