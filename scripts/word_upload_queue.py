#!/usr/bin/env python3
"""Work the word-upload queue: learners' uploaded words -> every asset -> watchlist.

ADR-069 / wiki/features/word-upload-queue.tech.md. Learners' words wait in
``word_upload_queue``; this script is the operator's side. It never calls an
LLM itself. It writes the worklists the authoring skills already answer, and
after each upload it re-checks the queue and finishes every word whose
assets are now all present (writing the learner's watchlist row and running
the test-match sweep).

    status   [--language L]                  counts by language and status
    list     [--language L] [--status S]     the rows, with what each is missing
    advance  [--language L] [--create-vocab] resolve + re-check + finish (no LLM)
    export   --language L [--out-dir RUN]    advance --create-vocab, then write the
                                             worklists for the next missing stage of
                                             every open word, and RUN/plan.md saying
                                             what to run
    requeue  --ids 1,2                       failed/cancelled -> pending
    fail     --ids 1,2 --reason TEXT         mark rows failed (junk, offensive, not a word)

advance, export, requeue and fail are dry runs unless --apply (scripts convention,
TASK-1218): a dry run reads the queue, prints what would change and writes nothing.

The loop, per language::

    python scripts/word_upload_queue.py export --language ja --apply
    # follow RUN/plan.md: answer each worklist with its skill, upload, run
    # the deterministic backfills it lists
    python scripts/word_upload_queue.py export --language ja --apply   # next stage
    ...until plan.md says nothing is left; `advance` finishes the words.

Stage order (a later stage needs the earlier one's output):

    vocab -> sense -> {embedding, pronunciation, gloss, core} -> exercises -> audio

``export`` only writes a worklist for a word once the stages before it are
done, so running it again after each upload always hands out the next step.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

try:
    from _common import ROOT, ApplyArgumentParser, add_apply_flags, admin_db, bootstrap
except ImportError:  # imported as scripts.word_upload_queue
    from scripts._common import ROOT, ApplyArgumentParser, add_apply_flags, admin_db, bootstrap

bootstrap()

from services import language_registry  # noqa: E402
from services.word_list_import import queue as q  # noqa: E402

#: Assets that need an earlier stage's output before they can be built.
NEEDS_SENSE = (q.ASSET_EMBEDDING, q.ASSET_PRONUNCIATION, q.ASSET_GLOSS, q.ASSET_CORE)


def _ids(text: str) -> list[int]:
    return [int(v) for v in (text or '').split(',') if v.strip()]


def _language_id(code: str | None) -> int | None:
    return language_registry.id_of(code) if code else None


def _db_client():
    try:
        from services.test_generation.database_client import TestDatabaseClient
        return TestDatabaseClient()
    except Exception as exc:  # the match sweep is optional
        print(f'(no TestDatabaseClient, match sweep skipped: {exc})')
        return None


# ---------------------------------------------------------------------------
# status / list
# ---------------------------------------------------------------------------

def cmd_status(db, args) -> int:
    rows = q.load_open_rows(db, language_id=_language_id(args.language),
                            statuses=[q.STATUS_PENDING, q.STATUS_BUILDING,
                                      q.STATUS_DONE, q.STATUS_FAILED])
    counts = Counter((language_registry.code_of(r['language_id']), r['status']) for r in rows)
    missing = Counter(m for r in rows if r['status'] in q.OPEN_STATUSES
                      for m in (r.get('missing') or []))
    if not rows:
        print('Queue is empty.')
        return 0
    print(f"{'lang':<6}{'pending':>9}{'building':>10}{'done':>7}{'failed':>8}")
    for code in sorted({c for c, _ in counts}):
        print(f"{code:<6}" + ''.join(
            f'{counts[(code, s)]:>{w}}' for s, w in
            ((q.STATUS_PENDING, 9), (q.STATUS_BUILDING, 10), (q.STATUS_DONE, 7),
             (q.STATUS_FAILED, 8))))
    if missing:
        print('\nOpen words missing each asset:')
        for key in q.ASSET_KEYS:
            if missing[key]:
                print(f'  {key:<14}{missing[key]}')
    return 0


def cmd_list(db, args) -> int:
    statuses = [args.status] if args.status else None
    rows = q.load_open_rows(db, language_id=_language_id(args.language), statuses=statuses)
    for r in rows:
        lemma = (r.get('detail') or {}).get('lemma') or ''
        reason = (r.get('detail') or {}).get('reason') or ''
        print(f"{r['id']:>6}  {language_registry.code_of(r['language_id'])}  "
              f"{r['status']:<9} {r['raw_word']:<16} {lemma:<16} "
              f"vocab={r.get('vocab_id') or '-'} sense={r.get('sense_id') or '-'} "
              f"missing={','.join(r.get('missing') or []) or '-'} {reason}")
    print(f'{len(rows)} row(s)')
    return 0


# ---------------------------------------------------------------------------
# advance
# ---------------------------------------------------------------------------

def preview(db, language_id: int | None) -> dict:
    """Dry run of advance: what the queue would do now, with no write."""
    rows = q.load_open_rows(db, language_id=language_id)
    checks = q.check_assets(db, [r for r in rows if r.get('status') == q.STATUS_BUILDING])
    finish = [r['id'] for r in rows if (c := checks.get(r['id'])) and c['sense_id']
              and not c['missing']]
    for r in rows:
        if r['id'] in checks:
            r['sense_id'] = checks[r['id']]['sense_id']
            r['missing'] = checks[r['id']]['missing']
    return {'rows': rows, 'would_finish': finish,
            'pending_to_resolve': [r['id'] for r in rows if r['status'] == q.STATUS_PENDING]}


def cmd_advance(db, args) -> int:
    if args.dry_run:
        p = preview(db, _language_id(args.language))
        print(f"(dry run) {len(p['rows'])} open row(s); would finish {p['would_finish'] or 'none'}; "
              f"would resolve {len(p['pending_to_resolve'])} pending row(s). Re-run with --apply.")
        return 0
    summary = q.advance(db, language_id=_language_id(args.language),
                        create_vocab=args.create_vocab,
                        db_client=None if args.no_sweep else _db_client(),
                        sweep=not args.no_sweep)
    print(json.dumps(summary, indent=2))
    return 0


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def stage_groups(rows: list[dict]) -> dict[str, list[dict]]:
    """Which open rows are ready for which stage now (see module docstring)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r['status'] != q.STATUS_BUILDING:
            continue
        missing = set(r.get('missing') or [])
        if q.ASSET_SENSE in missing or not r.get('sense_id'):
            groups[q.ASSET_SENSE].append(r)
            continue
        for key in NEEDS_SENSE:
            if key in missing:
                groups[key].append(r)
        if q.ASSET_CORE not in missing and q.ASSET_EXERCISES in missing:
            groups[q.ASSET_EXERCISES].append(r)
        elif q.ASSET_EXERCISES not in missing and q.ASSET_AUDIO in missing:
            groups[q.ASSET_AUDIO].append(r)
    return groups


def _run(cmd: list[str]) -> bool:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run([sys.executable] + cmd[1:], cwd=ROOT).returncode == 0


def _uniq(values) -> list[int]:
    return sorted({v for v in values if v})


def build_plan(code: str, language_id: int, groups: dict, out_dir: str) -> tuple[list, list[str]]:
    """(exporter commands to run now, plan.md lines)."""
    py = 'python'
    commands: list[list[str]] = []
    lines = [f'# Word-upload queue — {code} — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC', '',
             f'Run directory: `{out_dir}`. Work top to bottom; when done, run',
             f'`python scripts/word_upload_queue.py export --language {code} --apply` again for the next stage.',
             '']
    step = 0

    def section(title: str, body: list[str]) -> None:
        nonlocal step
        step += 1
        lines.extend([f'## {step}. {title}', ''] + body + [''])

    if groups.get(q.ASSET_SENSE):
        vocab_ids = _uniq(r['vocab_id'] for r in groups[q.ASSET_SENSE])
        sense_dir = os.path.join(out_dir, 'senses')
        commands.append([py, 'scripts/export_sense_seed_worklist.py', '--language', code,
                         '--vocab-ids', ','.join(map(str, vocab_ids)), '--out-dir', sense_dir])
        section(f'Senses — {len(vocab_ids)} word(s)  (skill: batch-sense-generation)', [
            f'Worklist: `{sense_dir}/batch_*.json` (written by this export). Write each',
            '`batch_NNN.senses.json` per the skill, then for each batch:', '',
            '```',
            f'python scripts/upload_senses.py --batch-file {sense_dir}/batch_001.json \\',
            f'    --senses-file {sense_dir}/batch_001.senses.json',
            '```',
            'A word that should not be in the dictionary at all (not a real word, offensive):',
            '`python scripts/word_upload_queue.py fail --ids <queue ids> --reason "..." --apply`.',
            'Queue ids: ' + ', '.join(str(r['id']) for r in groups[q.ASSET_SENSE]),
        ])

    if groups.get(q.ASSET_EMBEDDING):
        section(f'Embeddings — {len(groups[q.ASSET_EMBEDDING])} sense(s)  (deterministic)', [
            '```',
            f'python -m scripts.backfill_sense_embeddings --language {language_id} --apply',
            '```'])

    if groups.get(q.ASSET_PRONUNCIATION):
        section(f'Pronunciation — {len(groups[q.ASSET_PRONUNCIATION])} sense(s)  (deterministic, no LLM)', [
            '```',
            f'python scripts/backfill_pronunciations.py --language {code} --apply',
            '```'])

    by_target: dict[int, list[dict]] = defaultdict(list)
    for r in groups.get(q.ASSET_GLOSS, []):
        by_target[r['gloss_language_id']].append(r)
    for target_id, rows in sorted(by_target.items()):
        target = language_registry.code_of(target_id)
        vocab_ids = _uniq(r['vocab_id'] for r in rows)
        gloss_dir = os.path.join(out_dir, f'glosses_{target}')
        commands.append([py, 'scripts/export_gloss_worklist.py', '--source-language', code,
                         '--target-languages', target, '--vocab-ids',
                         ','.join(map(str, vocab_ids)), '--out-dir', gloss_dir])
        section(f'Glosses {code} -> {target} — {len(vocab_ids)} word(s)  (skill: cross-language-glosses)', [
            f'Worklist: `{gloss_dir}/batch_*.json`. Write `batch_NNN.glosses.json`, then:', '',
            '```',
            f'python scripts/upload_glosses.py --batch-file {gloss_dir}/batch_001.json \\',
            f'    --glosses-file {gloss_dir}/batch_001.glosses.json',
            '```'])

    for stage, key in (('core', q.ASSET_CORE), ('exercises', q.ASSET_EXERCISES)):
        rows = groups.get(key)
        if not rows:
            continue
        sense_ids = _uniq(r['sense_id'] for r in rows)
        ex_dir = os.path.join(out_dir, f'exercises_{stage}')
        commands.append([py, 'scripts/export_exercise_worklist.py', '--language', code,
                         '--stage', stage, '--sense-ids', ','.join(map(str, sense_ids)),
                         '--out-dir', ex_dir])
        section(f'Ladder {stage} — {len(sense_ids)} sense(s)  (skill: batch-exercise-generation)', [
            f'Worklist: `{ex_dir}/batch_*.json`. Answer each per the skill\'s stage '
            f'{"2" if stage == "core" else "5"}, then:', '',
            '```',
            f'python scripts/upload_exercises.py --stage {stage} --batch-file {ex_dir}/batch_001.json \\',
            f'    --answers-file {ex_dir}/batch_001.answers.json',
            '```',
            'For a large slice use fat-seed-authoring instead: re-export with `--format csv` '
            'and the same `--sense-ids`.'])

    if groups.get(q.ASSET_AUDIO):
        section(f'Exercise audio — {len(groups[q.ASSET_AUDIO])} sense(s)  (TTS, spends Azure quota)', [
            '```',
            f'python scripts/backfill_exercise_audio.py --language {code}',
            '```',
            'Language-wide and capped per run (AUDIO_BACKFILL_CAP); run again if the queue still shows `audio`.'])

    if step == 0:
        lines.append('Nothing to build: every open word is either finished or waiting on a '
                     'dictionary row (see `list --status pending`).')
    lines += ['## Finish', '', '```',
              f'python scripts/word_upload_queue.py advance --language {code} --apply',
              f'python scripts/word_upload_queue.py status --language {code}', '```']
    return commands, lines


def cmd_export(db, args) -> int:
    code = args.language
    language_id = _language_id(code)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    out_dir = args.out_dir or os.path.join('data', 'word_upload_queue', f'{code}-{stamp}')

    if args.dry_run:
        # Nothing written: the plan for the queue as it stands (no vocab rows
        # created, so words not yet in the dictionary are not shown).
        rows = preview(db, language_id)['rows']
        commands, lines = build_plan(code, language_id, stage_groups(rows), out_dir)
        print('(dry run) would run:')
        for cmd in commands:
            print('  ' + ' '.join(cmd))
        print('\n'.join(lines))
        print('\n(dry run) nothing written. Re-run with --apply.')
        return 0

    summary = q.advance(db, language_id=language_id, create_vocab=not args.no_create_vocab,
                        db_client=_db_client(), sweep=True)
    print('advance:', json.dumps(summary))

    rows = q.load_open_rows(db, language_id=language_id)
    groups = stage_groups(rows)
    os.makedirs(os.path.join(ROOT, out_dir), exist_ok=True)

    commands, lines = build_plan(code, language_id, groups, out_dir)
    ok = all(_run(cmd) for cmd in commands)

    with open(os.path.join(ROOT, out_dir, 'plan.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    with open(os.path.join(ROOT, out_dir, 'queue.json'), 'w', encoding='utf-8') as fh:
        json.dump({'language': code, 'exported_at': stamp,
                   'stages': {k: [r['id'] for r in v] for k, v in groups.items()},
                   'rows': rows}, fh, ensure_ascii=False, indent=2, default=str)
    print(f'\nWrote {out_dir}/plan.md')
    print('\n'.join(lines))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# requeue / fail
# ---------------------------------------------------------------------------

def _set_status(db, ids: list[int], status: str, reason: str | None, from_statuses,
                dry_run: bool = False) -> int:
    rows = q.load_open_rows(db, ids=ids, statuses=from_statuses)
    if dry_run:
        for r in rows:
            print(f"  (dry run) {r['id']} {r['raw_word']}: {r['status']} -> {status}")
        print(f'(dry run) {len(rows)} row(s) would change. Re-run with --apply.')
        return 0
    for r in rows:
        detail = dict(r.get('detail') or {})
        if reason:
            detail['reason'] = reason
        else:
            detail.pop('reason', None)
        fields = {'status': status, 'detail': detail}
        if status == q.STATUS_PENDING:
            fields.update(vocab_id=None, sense_id=None, missing=[])
        q._write(db, r, **fields)
    print(f'{len(rows)} row(s) -> {status}')
    return 0


def cmd_requeue(db, args) -> int:
    return _set_status(db, _ids(args.ids), q.STATUS_PENDING, None,
                       [q.STATUS_FAILED, q.STATUS_CANCELLED], getattr(args, 'dry_run', False))


def cmd_fail(db, args) -> int:
    return _set_status(db, _ids(args.ids), q.STATUS_FAILED, args.reason,
                       list(q.OPEN_STATUSES), getattr(args, 'dry_run', False))


def main(argv=None) -> int:
    ap = ApplyArgumentParser(description=__doc__.split('\n')[0],
                             formatter_class=argparse.RawDescriptionHelpFormatter,
                             epilog=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    codes = language_registry.codes()

    p = sub.add_parser('status')
    p.add_argument('--language', choices=codes)
    p = sub.add_parser('list')
    p.add_argument('--language', choices=codes)
    p.add_argument('--status', choices=[q.STATUS_PENDING, q.STATUS_BUILDING, q.STATUS_DONE,
                                        q.STATUS_FAILED, q.STATUS_CANCELLED])
    p = sub.add_parser('advance')
    p.add_argument('--language', choices=codes)
    p.add_argument('--create-vocab', action='store_true',
                   help='create dim_vocabulary rows for words not in the dictionary')
    p.add_argument('--no-sweep', action='store_true', help='skip the test-match sweep')
    add_apply_flags(p)
    p = sub.add_parser('export')
    p.add_argument('--language', choices=codes, required=True)
    p.add_argument('--out-dir', help='default data/word_upload_queue/<lang>-<timestamp>')
    p.add_argument('--no-create-vocab', action='store_true',
                   help='leave words with no dictionary row pending')
    add_apply_flags(p, apply_help='advance the queue, run the exporters and write RUN/ '
                                  '(default: dry run, print the plan only)')
    p = sub.add_parser('requeue')
    p.add_argument('--ids', required=True)
    add_apply_flags(p)
    p = sub.add_parser('fail')
    p.add_argument('--ids', required=True)
    p.add_argument('--reason', required=True)
    add_apply_flags(p)

    args = ap.parse_args(argv)
    db = admin_db()
    return {'status': cmd_status, 'list': cmd_list, 'advance': cmd_advance,
            'export': cmd_export, 'requeue': cmd_requeue, 'fail': cmd_fail}[args.cmd](db, args)


if __name__ == '__main__':
    sys.exit(main())
