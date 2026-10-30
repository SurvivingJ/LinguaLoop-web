"""Run the tool-free fat-seed pipeline (author -> patch review) over many runs.

    python3 scratch_offline/nt_pipeline.py [--lang ja] [--runs-dir DIR]
        [--cheatsheet PATH] [--workers 4] [--limit N] [--from r0020]

Picks the run directories under --runs-dir (default
data/exercise_seeding/<lang>/wf2, built by nt_make_runs.py) in order, skipping
any whose every sense is already reviewed or skipped. Each run: nt_author.py
(resumes from existing docs), then nt_review.py in place, both with the
production configuration below. Logs go to RUN/fat_seed/nt_pipeline.log; a
one-line status per run is printed so a monitor can follow it.
"""
import argparse
import csv
import glob
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHEATSHEETS = os.path.join(REPO, '.claude/skills/fat-seed-authoring/cheatsheets')

# Production configuration = the optimisation campaign's quality finalist
# (opt/REPORT.md, arm c_final3_100) with a Sonnet core: the production queue
# puts the senses of one lemma in the same run and Haiku confuses them in the
# core sentences (fatal share 0.26 vs 0.06 with a Sonnet core on the same
# runs; opt/ctrl_hybrid). Sonnet/low writes the core only; Haiku/medium does
# the audits, the variants and the patch review; no level_1 (the renderer
# builds it from the phonetic trie). Lints: only the rules that paid for
# themselves (A/B overlap, level_7 twin, ps_slot, l7_target_absent,
# l7_multi_span); the rest are demoted.
# The cheat sheet (--cheatsheet, default cheatsheets/<lang>.md) is appended.
AUTHOR_ARGS = ['--model', 'haiku', '--effort', 'medium', '--core-model', 'sonnet', '--core-effort', 'low',
               '--skip-l1', '--core-audit', '--variant-audit', '--l6-audit']
REVIEW_ARGS = ['--model', 'haiku', '--effort', 'medium']
LINT_ENV = {'FAT_SEED_LINT_ALL_BLOCKS': '1',
            'FAT_SEED_LINT_SKIP': 'l3_generic_expl,l6_shared_expl,l6_copied_expl,l7_edit_far'}


def n_senses(run):
    return sum(1 for _ in csv.DictReader(open(os.path.join(run, 'senses.csv'), encoding='utf-8')))


def reviewed(run):
    """Senses that are finished: reviewed, or skipped by the author (no review record)."""
    done = len(glob.glob(os.path.join(run, 'fat_seed', 'review', '*.json')))
    for f in glob.glob(os.path.join(run, 'fat_seed', 'words', '*.json')):
        try:
            if json.load(open(f)).get('skip') and not os.path.exists(
                    os.path.join(run, 'fat_seed', 'review', os.path.basename(f))):
                done += 1
        except (json.JSONDecodeError, OSError):
            pass
    return done


def process(run, args):
    rel = os.path.relpath(run, REPO)
    os.makedirs(os.path.join(run, 'fat_seed'), exist_ok=True)  # a fresh run has no fat_seed/ yet
    log = open(os.path.join(run, 'fat_seed', 'nt_pipeline.log'), 'a')
    env = dict(os.environ, NT_LANG=args.lang, **LINT_ENV)
    review_args = list(REVIEW_ARGS)
    if glob.glob(os.path.join(run, 'fat_seed', 'reviewed', '*.json')):
        review_args.append('--resume')  # a relaunch must not re-review (re-pay) finished senses
    for script, extra in (('nt_author.py', [rel, *AUTHOR_ARGS, '--cheatsheet', args.cheatsheet]),
                          ('nt_review.py', [rel, rel, *review_args])):
        p = subprocess.run([sys.executable, f'scratch_offline/{script}', *extra],
                           cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
        if p.returncode != 0:
            return rel, f'{script} exited {p.returncode}'
    tail = open(os.path.join(run, 'fat_seed', 'nt_pipeline.log')).read().strip().splitlines()[-1:]
    return rel, (tail[0] if tail else 'done')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--from', dest='start', default='r0000')
    ap.add_argument('--lang', default='ja', help='ja | zh | en (sets NT_LANG for the scripts)')
    ap.add_argument('--runs-dir', default='', help='default data/exercise_seeding/<lang>/wf2')
    ap.add_argument('--cheatsheet', default='', help='default cheatsheets/<lang>.md in the skill')
    args = ap.parse_args()
    runs_dir = args.runs_dir or os.path.join(REPO, 'data/exercise_seeding', args.lang, 'wf2')
    args.cheatsheet = args.cheatsheet or os.path.join(CHEATSHEETS, f'{args.lang}.md')
    if not os.path.exists(args.cheatsheet):
        raise SystemExit(f'no cheat sheet for {args.lang}: write {args.cheatsheet} first '
                         '(see .claude/skills/fat-seed-authoring/cheatsheets/README.md)')
    runs = [r for r in sorted(glob.glob(os.path.join(runs_dir, 'r*')))
            if os.path.basename(r) >= args.start and reviewed(r) < n_senses(r)]
    if args.limit:
        runs = runs[:args.limit]
    print(f'{len(runs)} runs queued', flush=True)
    with ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(process, r, args): r for r in runs}
        for f in as_completed(futs):
            try:
                rel, status = f.result()
            except Exception as e:  # keep the pool going
                rel, status = os.path.relpath(futs[f], REPO), f'crashed: {e}'
            print(f'RUN {rel}: {status}', flush=True)
    print('PIPELINE DONE', flush=True)


if __name__ == '__main__':
    main()
