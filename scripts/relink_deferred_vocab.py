#!/usr/bin/env python
"""Attach deferred vocabulary back to its test once the backfill has seeded it.

Closes the loop opened by TASK-744 / T2.3. When inline enrichment is capped
(``TEST_GEN_INLINE_ENRICHMENT_CAP``), the tail of a test's extracted vocabulary
is deferred: the ``dim_vocabulary`` rows are still created — that costs no LLM
call, and it is what ``scripts/backfill_senses.py`` selects on — but no sense is
generated inline and nothing is linked to the test. The deferred lemmas are
recorded in ``tests.vocab_sense_stats.deferred_lemmas``.

Without this script the deferral would be a permanent hole in the test's
vocabulary layer rather than a delay, which would make T2.3 a quality
regression dressed up as a throughput win. Run it after a backfill pass:

    python scripts/backfill_senses.py --language zh
    python scripts/relink_deferred_vocab.py --language zh

It makes no LLM calls. A lemma whose sense still does not exist is left in
``deferred_lemmas`` for the next run.

Usage:
    python scripts/relink_deferred_vocab.py [--language zh] [--limit 50]
                                            [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from services.supabase_factory import (  # noqa: E402
    SupabaseFactory, get_supabase_admin,
)

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger('relink_deferred_vocab')


def _language_id(db, language_code: str) -> int:
    resp = (
        db.table('dim_languages')
        .select('id')
        .eq('language_code', language_code)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise SystemExit(f'unknown language code: {language_code}')
    return resp.data[0]['id']


def _tests_with_deferrals(db, language_id: int | None, limit: int) -> list[dict]:
    query = (
        db.table('tests')
        .select('id, language_id, vocab_sense_ids, vocab_sense_stats')
        .not_.is_('vocab_sense_stats', 'null')
        .order('created_at', desc=True)
        .limit(limit * 20)
    )
    if language_id is not None:
        query = query.eq('language_id', language_id)

    out = []
    for row in (query.execute().data or []):
        stats = row.get('vocab_sense_stats') or {}
        if stats.get('deferred_lemmas'):
            out.append(row)
        if len(out) >= limit:
            break
    return out


def _senses_for_lemmas(
    db, lemmas: list[str], language_id: int,
) -> dict[str, int]:
    """lemma -> a sense id, for lemmas that now have one."""
    out: dict[str, int] = {}
    for start in range(0, len(lemmas), 100):
        chunk = lemmas[start:start + 100]
        resp = (
            db.table('dim_vocabulary')
            .select('id, lemma, dim_word_senses(id)')
            .eq('language_id', language_id)
            .in_('lemma', chunk)
            .execute()
        )
        for row in (resp.data or []):
            senses = row.get('dim_word_senses') or []
            if senses:
                out[row['lemma']] = senses[0]['id']
    return out


def relink(db, test_row: dict, dry_run: bool) -> tuple[int, int]:
    """Link whatever is now seeded. Returns (linked, still_deferred)."""
    stats = dict(test_row.get('vocab_sense_stats') or {})
    deferred = list(stats.get('deferred_lemmas') or [])
    language_id = test_row['language_id']

    found = _senses_for_lemmas(db, deferred, language_id)
    if not found:
        return 0, len(deferred)

    existing = list(test_row.get('vocab_sense_ids') or [])
    seen = set(existing)
    added: list[int] = []
    for sense_id in found.values():
        if sense_id not in seen:
            seen.add(sense_id)
            added.append(sense_id)

    remaining = [lemma for lemma in deferred if lemma not in found]
    stats['deferred_lemmas'] = remaining
    stats['senses_deferred'] = len(remaining)
    stats['unique_senses'] = len(existing) + len(added)
    # Re-derive completeness on the same rule _record_vocab_outcome uses.
    accounted = (
        stats['unique_senses']
        + int(stats.get('senses_skipped') or 0)
        + len(remaining)
    )
    stats['complete'] = accounted >= int(stats.get('words_attempted') or 0)
    if stats['complete']:
        stats.pop('shortfall_reason', None)

    if dry_run:
        logger.info(
            '[DRY RUN] test %s: would link %d sense(s), %d still deferred',
            test_row['id'], len(added), len(remaining),
        )
        return len(added), len(remaining)

    db.table('tests').update({
        'vocab_sense_ids': existing + added,
        'vocab_sense_stats': stats,
    }).eq('id', test_row['id']).execute()

    # NOTE: vocab_token_map and questions.sense_ids are deliberately NOT
    # rebuilt here. Both are derived from the passage and the question text by
    # orchestrator helpers that need a full TestGenerationOrchestrator, and
    # re-running them is a heavier, separately-scheduled job. The senses are
    # linked to the test, which is what the practice-engine supply gate and the
    # evidence queue read.
    logger.info(
        'test %s: linked %d sense(s), %d still deferred',
        test_row['id'], len(added), len(remaining),
    )
    return len(added), len(remaining)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language', help='language code, e.g. zh')
    parser.add_argument('--limit', type=int, default=50,
                        help='max tests to process (default 50)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    language_id = _language_id(db, args.language) if args.language else None

    tests = _tests_with_deferrals(db, language_id, args.limit)
    if not tests:
        logger.info('no tests with deferred vocabulary — nothing to do')
        return 0

    linked = deferred = 0
    for test_row in tests:
        try:
            n_linked, n_deferred = relink(db, test_row, args.dry_run)
        except Exception as exc:
            logger.error('test %s: relink failed: %s', test_row['id'], exc)
            continue
        linked += n_linked
        deferred += n_deferred

    logger.info(
        'Done: %d test(s), %d sense(s) linked, %d lemma(s) still awaiting '
        'a backfill pass', len(tests), linked, deferred,
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
