#!/usr/bin/env python3
"""TASK-768 — repair quarantined dictionary rows and release them.

``calibration_anchor_blocklist`` quarantines senses whose definition does not
define the headword (TASK-757 screen). TASK-767 made that quarantine bind every
exercise consumer. This script is the other half: it writes a corrected
definition onto each flagged sense *in place* and takes it off the list.

In place, not merged into a sibling sense. The dictionary keeps one sense per
test context (``accessible`` has six), and ``tests.vocab_sense_ids`` points at
these exact rows, so rewriting keeps every test link valid while making what
the learner sees correct. Each rewrite defines what the headword means *in the
sense's example sentence* — ``carbon`` from "carbon footprint" becomes carbon
as in carbon emissions, not the compound.

Fixes file (JSON list), one entry per sense::

    {"sense_id": 16222, "action": "rewrite", "confidence": 0.9,
     "definition": "carbon dioxide and other carbon-based gases ...",
     "simple": "..."}                      # only when a paired simple row exists
    {"sense_id": 10281, "action": "rewrite", "definition": "...",
     "example": "..."}                     # when the example uses another word
    {"sense_id": 17214, "action": "false_positive", "reason": "..."}
    {"sense_id": 12345, "action": "keep", "reason": "..."}   # leave quarantined
    {"sense_id": 36791, "action": "gloss",                 # already-rewritten sense
     "glosses": {"1": {"simple": "河", "standard": "..."},
                 "2": {"simple": "a river", "standard": "..."}}}

What a write does:
  * ``rewrite``         — definition replaced, embedding nulled (re-embed with
                          ``python -m scripts.backfill_sense_embeddings``), old
                          text appended to ``validation_notes``, blocklist row
                          removed. ``simple`` rewrites the paired simple row at
                          the same (vocab_id, sense_rank).
  * ``false_positive``  — definition untouched, blocklist row removed.
  * ``keep``            — nothing written; the sense stays quarantined.
  * ``gloss``           — replaces the cross-language gloss rows (same vocab_id +
                          sense_rank, other definition language) of a sense this
                          task already rewrote; they were translated from the bad
                          definition. Each (language, level) must match one row.

Retired exercises are NOT reactivated (TASK-767): they were built from the bad
definition and must be regenerated.

Fail-closed validation: every id must be on the blocklist, appear once, and a
rewrite must carry a non-empty definition. Nothing is written if any entry fails.

Usage::

    PYTHONIOENCODING=utf-8 python -m scripts.fix_quarantined_senses \
        --fixes data/calibration/quarantine_fixes/en_001.json --dry-run
    PYTHONIOENCODING=utf-8 python -m scripts.fix_quarantined_senses \
        --fixes data/calibration/quarantine_fixes/en_001.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

ACTIONS = {'rewrite', 'false_positive', 'keep', 'gloss'}
TAG = 'TASK-768'
REWRITTEN_MARK = f'{TAG}] definition rewritten'


def validate(fixes: list, blocked: set[int], rows: dict[int, dict]) -> list[str]:
    errors, seen = [], set()
    for i, f in enumerate(fixes):
        sid = f.get('sense_id')
        where = f'entry {i} (sense {sid})'
        if not isinstance(sid, int):
            errors.append(f'{where}: sense_id must be an integer')
            continue
        if sid in seen:
            errors.append(f'{where}: duplicate')
        seen.add(sid)
        action = f.get('action')
        if action == 'gloss':
            # Glosses are repaired only for senses this task already rewrote
            # (they are off the blocklist by then). Anything else is out of scope.
            row = rows.get(sid)
            if not row or REWRITTEN_MARK not in (row.get('validation_notes') or ''):
                errors.append(f'{where}: gloss only allowed on a {TAG}-rewritten sense')
                continue
            glosses = f.get('glosses') or {}
            if not glosses:
                errors.append(f'{where}: gloss needs a glosses object')
            for lang, levels in glosses.items():
                if not lang.isdigit() or int(lang) == row['definition_language_id']:
                    errors.append(f'{where}: gloss language {lang!r} must be another language id')
                if not all((levels or {}).get(k, '').strip() for k in ('simple', 'standard')):
                    errors.append(f'{where}: gloss {lang} needs simple and standard')
            continue
        if sid not in blocked:
            errors.append(f'{where}: not on calibration_anchor_blocklist')
        if action not in ACTIONS:
            errors.append(f'{where}: action must be one of {sorted(ACTIONS)}')
        if action == 'rewrite' and not (f.get('definition') or '').strip():
            errors.append(f'{where}: rewrite needs a definition')
        if action in ('false_positive', 'keep') and not (f.get('reason') or '').strip():
            errors.append(f'{where}: {action} needs a reason')
    return errors


def _note(existing: str | None, text: str) -> str:
    stamp = datetime.now(timezone.utc).date().isoformat()
    line = f'[{stamp} {TAG}] {text}'
    return f'{existing}\n{line}' if existing else line


def _write_glosses(db, row: dict, lemma: str, glosses: dict, dry_run: bool) -> int:
    """Replace the cross-language glosses paired with a rewritten sense.

    Cross-language glosses (source='llm_gloss') sit at the same vocab_id +
    sense_rank in another definition language, and were translated from the
    bad definition — 川 glossed "a peel", 説明 "a yawn". Each target row must
    match exactly one (language, level); anything else is reported, not written.
    """
    written = 0
    for lang, levels in glosses.items():
        for level in ('standard', 'simple'):
            text = levels[level].strip()
            match = (db.table('dim_word_senses')
                       .select('id, definition, validation_notes')
                       .eq('vocab_id', row['vocab_id'])
                       .eq('sense_rank', row['sense_rank'])
                       .eq('definition_language_id', int(lang))
                       .eq('definition_level', level)
                       .execute().data or [])
            if len(match) != 1:
                print(f'  !! [{row["id"]}] {lemma}: {len(match)} {lang}/{level} '
                      f'gloss rows match; writing none')
                continue
            g = match[0]
            print(f'  gloss  [{row["id"]}] {lemma} {lang}/{level}: '
                  f'{g["definition"][:40]!r} -> {text!r}')
            if dry_run:
                continue
            db.table('dim_word_senses').update({
                'definition': text,
                'embedding': None,
                'validation_notes': _note(
                    g.get('validation_notes'),
                    f'gloss rewritten with sense {row["id"]} '
                    f'(was: {g["definition"]!r})'),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }).eq('id', g['id']).execute()
            written += 1
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixes', required=True)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    with open(args.fixes, encoding='utf-8') as fh:
        fixes = json.load(fh)

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    ids = [f['sense_id'] for f in fixes if isinstance(f.get('sense_id'), int)]
    blocked = {r['sense_id'] for r in (
        db.table('calibration_anchor_blocklist').select('sense_id')
          .in_('sense_id', ids).execute().data or [])}

    rows = {r['id']: r for r in (
        db.table('dim_word_senses')
          .select('id, vocab_id, sense_rank, definition_language_id, definition, '
                  'example_sentence, validation_notes, '
                  'dim_vocabulary!inner(lemma)')
          .in_('id', ids).execute().data or [])}

    errors = validate(fixes, blocked, rows)
    if errors:
        print('Validation failed — nothing written:')
        for e in errors:
            print('  ' + e)
        sys.exit(1)

    counts = {'rewrite': 0, 'simple': 0, 'false_positive': 0, 'keep': 0,
              'gloss': 0, 'gloss_rows': 0}
    for f in fixes:
        sid, action = f['sense_id'], f['action']
        row = rows[sid]
        lemma = row['dim_vocabulary']['lemma']
        counts[action] += 1

        if action == 'gloss':
            counts['gloss_rows'] += _write_glosses(db, row, lemma, f['glosses'],
                                                   args.dry_run)
            continue

        if action == 'keep':
            print(f'  keep   [{sid}] {lemma}: {f["reason"]}')
            continue

        if action == 'false_positive':
            print(f'  ok     [{sid}] {lemma}: {row["definition"][:70]}')
        else:
            print(f'  fix    [{sid}] {lemma}\n'
                  f'           was: {row["definition"][:100]}\n'
                  f'           now: {f["definition"]}')
        if args.dry_run:
            continue

        if action == 'rewrite':
            note = f'definition rewritten (was: {row["definition"]!r})'
            update = {
                'definition': f['definition'].strip(),
                'embedding': None,
                'gen_confidence': f.get('confidence'),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
            if (f.get('example') or '').strip():
                # The screen also caught rows whose example sentence belongs to
                # the other word (定义 exemplified with 道理) — replace it too.
                update['example_sentence'] = f['example'].strip()
                note += f'; example rewritten (was: {row.get("example_sentence")!r})'
            update['validation_notes'] = _note(row.get('validation_notes'), note)
            db.table('dim_word_senses').update(update).eq('id', sid).execute()

            if (f.get('simple') or '').strip():
                # definition_language_id is load-bearing: cross-language glosses
                # (TASK cross-language-glosses) share vocab_id + sense_rank + level,
                # and without it a Chinese simple text overwrote the en/ja glosses
                # of the same word on the first run.
                pair = (db.table('dim_word_senses')
                          .select('id, definition, validation_notes')
                          .eq('vocab_id', row['vocab_id'])
                          .eq('sense_rank', row['sense_rank'])
                          .eq('definition_level', 'simple')
                          .eq('definition_language_id', row['definition_language_id'])
                          .execute().data or [])
                if len(pair) > 1:
                    print(f'  !! [{sid}] {len(pair)} simple rows match; writing none')
                    pair = []
                for p in pair:
                    db.table('dim_word_senses').update({
                        'definition': f['simple'].strip(),
                        'embedding': None,
                        'validation_notes': _note(
                            p.get('validation_notes'),
                            f'simple rewritten with sense {sid} '
                            f'(was: {p["definition"]!r})'),
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                    }).eq('id', p['id']).execute()
                    counts['simple'] += 1

        db.table('calibration_anchor_blocklist').delete().eq('sense_id', sid).execute()

    print(f'\n{counts}' + ('  (dry run — nothing written)' if args.dry_run else ''))
    if not args.dry_run and counts['rewrite']:
        print('Next: python -m scripts.backfill_sense_embeddings --language <id>')


if __name__ == '__main__':
    main()
