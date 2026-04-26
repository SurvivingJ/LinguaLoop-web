#!/usr/bin/env python3
"""
Backfill sense_ids on the questions table (Phase 7 compatible).

For each test with vocab_sense_ids, assigns per-question sense_ids by
matching vocabulary lemmas against each question's text + choices + answer.
Only vocabulary that appears in a question's content is assigned to it.

This mirrors the logic in orchestrator._match_question_senses() — questions
about inference (where no vocab directly appears) fall back to all sense_ids.

Usage:
    python scripts/backfill_question_sense_ids.py --language cn [--limit 10] [--force]

Options:
    --language CODE   Required. Language code: cn, en, jp
    --limit N         Process at most N tests (default: all)
    --force           Overwrite existing sense_ids on questions
    --dry-run         Preview changes without writing to DB
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def build_sense_lookup(db, sense_ids: list[int]) -> dict[str, int]:
    """Reverse-lookup: sense_ids → vocab_id → lemma → {lemma: sense_id}.

    Mirrors orchestrator._build_sense_lookup().
    """
    if not sense_ids:
        return {}

    sense_to_vocab: dict[int, int] = {}
    for i in range(0, len(sense_ids), 500):
        chunk = sense_ids[i:i + 500]
        result = db.table('dim_word_senses') \
            .select('id, vocab_id') \
            .in_('id', chunk) \
            .execute()
        for row in (result.data or []):
            sense_to_vocab[row['id']] = row['vocab_id']

    vocab_ids = list(set(sense_to_vocab.values()))
    vocab_to_lemma: dict[int, str] = {}
    for i in range(0, len(vocab_ids), 500):
        chunk = vocab_ids[i:i + 500]
        result = db.table('dim_vocabulary') \
            .select('id, lemma') \
            .in_('id', chunk) \
            .execute()
        for row in (result.data or []):
            vocab_to_lemma[row['id']] = row['lemma']

    lemma_to_sense: dict[str, int] = {}
    for sense_id, vocab_id in sense_to_vocab.items():
        lemma = vocab_to_lemma.get(vocab_id)
        if lemma and lemma not in lemma_to_sense:
            lemma_to_sense[lemma] = sense_id

    return lemma_to_sense


def match_question_senses(
    question: dict,
    lemma_to_sense: dict[str, int],
    all_sense_ids: list[int],
) -> list[int]:
    """Determine which sense_ids are relevant to a specific question.

    Matches vocabulary lemmas against the question text + answer choices.
    Falls back to all_sense_ids if no matches found (inference questions).

    Mirrors orchestrator._match_question_senses().
    """
    text_parts = [question.get('question_text', '')]
    choices = question.get('choices') or []
    if isinstance(choices, list):
        text_parts.extend(
            c if isinstance(c, str) else str(c) for c in choices
        )
    answer = question.get('answer', '')
    if answer:
        text_parts.append(answer if isinstance(answer, str) else str(answer))
    searchable = ' '.join(text_parts).lower()

    matched_senses = []
    for lemma, sense_id in lemma_to_sense.items():
        if lemma.lower() in searchable:
            matched_senses.append(sense_id)

    if not matched_senses:
        return all_sense_ids

    return matched_senses


def run_backfill(language_code: str, limit: int = 0, force: bool = False,
                 dry_run: bool = False):
    db = get_supabase_admin()
    language_id = Config.LANGUAGE_CODE_TO_ID.get(language_code)
    if not language_id:
        raise ValueError(f"Unknown language code: {language_code}")

    # Fetch tests with vocab_sense_ids
    query = db.table('tests') \
        .select('id, slug, vocab_sense_ids') \
        .eq('language_id', language_id) \
        .eq('is_active', True) \
        .not_.is_('vocab_sense_ids', 'null') \
        .order('created_at')

    if limit:
        query = query.limit(limit)

    tests = (query.execute()).data or []
    logger.info(f"Found {len(tests)} tests with vocab_sense_ids for {language_code}")

    stats = {'tests': 0, 'questions_updated': 0, 'skipped': 0, 'fallback': 0}

    for i, test in enumerate(tests):
        test_id = test['id']
        slug = test['slug']
        sense_ids = test.get('vocab_sense_ids') or []

        if not sense_ids:
            logger.warning(f"Skipping {slug}: empty vocab_sense_ids")
            stats['skipped'] += 1
            continue

        # Build lemma → sense_id lookup for this test
        lemma_to_sense = build_sense_lookup(db, sense_ids)
        if not lemma_to_sense:
            logger.warning(f"Skipping {slug}: could not resolve any lemmas from sense_ids")
            stats['skipped'] += 1
            continue

        # Fetch questions for this test
        questions = (
            db.table('questions')
            .select('id, question_text, choices, answer, sense_ids')
            .eq('test_id', test_id)
            .execute()
        ).data or []

        if not questions:
            logger.warning(f"Skipping {slug}: no questions found")
            stats['skipped'] += 1
            continue

        # Match per-question sense_ids
        updated = 0
        for q in questions:
            if not force and q.get('sense_ids') and len(q['sense_ids']) > 0:
                continue

            q_senses = match_question_senses(q, lemma_to_sense, sense_ids)
            is_fallback = len(q_senses) == len(sense_ids)

            if is_fallback:
                stats['fallback'] += 1

            if dry_run:
                logger.info(
                    f"  [DRY RUN] Question {q['id'][:8]}…: "
                    f"{len(q_senses)} senses"
                    f"{' (fallback — no direct matches)' if is_fallback else ''}"
                )
            else:
                db.table('questions') \
                    .update({'sense_ids': q_senses}) \
                    .eq('id', q['id']) \
                    .execute()
            updated += 1

        stats['questions_updated'] += updated
        stats['tests'] += 1
        logger.info(
            f"[{i+1}/{len(tests)}] {slug}: "
            f"{len(lemma_to_sense)} lemmas, "
            f"{updated}/{len(questions)} questions updated"
        )

    logger.info("=" * 60)
    logger.info("Backfill Complete")
    logger.info(f"  Tests processed:    {stats['tests']}")
    logger.info(f"  Tests skipped:      {stats['skipped']}")
    logger.info(f"  Questions updated:  {stats['questions_updated']}")
    logger.info(f"  Fallback (all ids): {stats['fallback']}")
    logger.info("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Backfill per-question sense_ids (Phase 7 compatible)'
    )
    parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],
                        help='Language code to process')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max number of tests to process (0=all)')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite existing sense_ids')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing to DB')

    args = parser.parse_args()

    if args.dry_run:
        logger.info("Running in DRY RUN mode — no changes will be made")

    SupabaseFactory.initialize()
    run_backfill(
        language_code=args.language,
        limit=args.limit,
        force=args.force,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    main()
