#!/usr/bin/env python3
"""
Export lemmas that need the two-level sense treatment, as batch files to write.

Stage 1 of the in-session batch workflow
(.claude/skills/batch-sense-generation/SKILL.md). Selects the same worklist
``scripts/backfill_senses.py`` would — every lemma with no ``simple``-level sense
in its own language — and writes it as numbered JSON batches for Claude Code to
work through directly, instead of shelling out to `claude -p` per batch.

Each item carries everything needed to write a definition without a second
lookup: the lemma, its part of speech if known, and the existing ``standard``
definition when the word already has one. That last field matters — a word with a
standard sense but no simple sense is being *upgraded*, not defined from scratch,
and the new standard row overwrites the old one at the same rank. Handing the
generator the current wording is what keeps that from being a silent rewrite.

Words whose primary sense is ``source='manual'`` are excluded here rather than
rejected at upload, mirroring seed_word's guard: hand-written senses are never
overwritten by generated ones.

Usage:
    python scripts/export_sense_seed_worklist.py --language ja
    python scripts/export_sense_seed_worklist.py --language zh --batch-size 40 --limit 200

Options:
    --language CODE    Required. zh | en | ja
    --batch-size N     Lemmas per output file (default: 50)
    --limit N          Cap total lemmas (0 = all)
    --out-dir PATH     Default: data/sense_seeding/<language>
"""

import os
import sys
import json
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.vocabulary.sense_generator import POS_LEGENDS

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PAGE = 1000


def _paged(query_fn) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page = query_fn(offset).execute().data or []
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    return rows


def load_worklist(db, language_id: int) -> tuple[list[dict], int]:
    """Return ([{vocab_id, lemma, part_of_speech, existing_standard}, ...], already_seeded).

    Three reads and a set-difference rather than a NOT EXISTS per word: at a few
    thousand rows it is one round-trip per table and gives a deterministic,
    resumable worklist.
    """
    simple_rows = _paged(lambda o: db.table('dim_word_senses')
                         .select('vocab_id')
                         .eq('definition_language_id', language_id)
                         .eq('definition_level', 'simple')
                         .range(o, o + PAGE - 1))
    has_simple = {r['vocab_id'] for r in simple_rows}

    standard_rows = _paged(lambda o: db.table('dim_word_senses')
                           .select('vocab_id, definition, sense_rank, source')
                           .eq('definition_language_id', language_id)
                           .eq('definition_level', 'standard')
                           .order('sense_rank')
                           .range(o, o + PAGE - 1))
    primary_standard: dict[int, dict] = {}
    for row in standard_rows:
        primary_standard.setdefault(row['vocab_id'], row)

    vocab_rows = _paged(lambda o: db.table('dim_vocabulary')
                        .select('id, lemma, part_of_speech')
                        .eq('language_id', language_id)
                        .range(o, o + PAGE - 1))

    worklist = []
    manual_skipped = 0
    for row in vocab_rows:
        if row['id'] in has_simple:
            continue
        current = primary_standard.get(row['id'])
        if current and current.get('source') == 'manual':
            manual_skipped += 1
            continue
        worklist.append({
            'vocab_id': row['id'],
            'lemma': row['lemma'],
            'part_of_speech': row.get('part_of_speech'),
            'existing_standard': current.get('definition') if current else None,
        })

    if manual_skipped:
        logger.info("Excluded %d lemma(s) whose primary sense is source='manual'", manual_skipped)
    return worklist, len(has_simple)


def load_simple_register(db, language_code: str, language_id: int) -> str:
    """The child-register guide, read through SenseGenerator (ADR-003 source of truth)."""
    try:
        from services.test_generation.database_client import TestDatabaseClient
        from services.vocabulary.sense_generator import SenseGenerator
        gen = SenseGenerator(
            openai_client=None, db=db, db_client=TestDatabaseClient(),
            language_code=language_code, language_id=language_id, dry_run=True,
        )
        return gen._simple_register
    except Exception as exc:
        logger.warning("Could not load the simple register: %s", exc)
        return ''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language', required=True, choices=['zh', 'en', 'ja'])
    parser.add_argument('--batch-size', type=int, default=50)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--out-dir')
    args = parser.parse_args()

    language_id = Config.LANGUAGE_CODE_TO_ID[args.language]
    db = get_supabase_admin()

    worklist, already = load_worklist(db, language_id)
    logger.info("%s: %d lemma(s) need seeding (%d already have a simple level)",
                args.language, len(worklist), already)
    if args.limit:
        worklist = worklist[:args.limit]
        logger.info("  limited to %d", len(worklist))

    if not worklist:
        logger.info("Nothing to seed.")
        return 0

    out_dir = args.out_dir or os.path.join('data', 'sense_seeding', args.language)
    os.makedirs(out_dir, exist_ok=True)

    register = load_simple_register(db, args.language, language_id)
    legend = POS_LEGENDS.get(args.language, POS_LEGENDS['en'])

    batches = [worklist[i:i + args.batch_size]
               for i in range(0, len(worklist), args.batch_size)]
    for n, batch in enumerate(batches, start=1):
        path = os.path.join(out_dir, f"batch_{n:03d}.json")
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump({
                'language_code': args.language,
                'language_id': language_id,
                'batch': n,
                'of': len(batches),
                'simple_register': register,
                'pos_legend': legend,
                'items': batch,
            }, fh, ensure_ascii=False, indent=2)

    upgrades = sum(1 for w in worklist if w['existing_standard'])
    logger.info("Wrote %d batch file(s) of up to %d lemmas to %s",
                len(batches), args.batch_size, out_dir)
    logger.info("  %d new definitions, %d upgrades of an existing standard sense",
                len(worklist) - upgrades, upgrades)
    return 0


if __name__ == '__main__':
    sys.exit(main())
