#!/usr/bin/env python
"""Backfill topic tiers and thin-tier test coverage (plan §3, T3.3 / T3.4).

Two related gaps, both measured live on 2026-08-31.

T3.4 — 43 of 183 topics carry no ``target_age_tier``. They come from the import
path, which has no tier concept at all, so nothing ever stamped them. Untiered
topics are invisible to the tier-keyed question distribution and to the
tier-scaled novelty threshold. ``--stamp-tiers`` walks them through the
TierFitJudge, asking each tier independently, ascending, and stamps the lowest
tier whose reader can actually reach the topic's distinctive vocabulary.

T3.3 — tests cluster at tiers 1/2/4/6 (71/61/92/80) while T3 and T5 have **one
test each**, a legacy artefact of ``target_difficulties = [1,3,6,9]``. The
important part, which the plan's framing did not have: **topics at T3 and T5
are not scarce** — there are 26 and 23 of them, as many as any other tier. The
shortfall is entirely in the *test* queue, so no topic fan-out is needed. Fan-out
was the risky half of the design and this measurement removes the reason for it
altogether. ``--queue-tiers 3,5`` enqueues the topics that already exist.

This script never generates tests. Enqueuing is cheap and reversible; running a
generation batch costs money and hours, so the run command is printed for a
human to execute.

Usage:
    python scripts/backfill_topic_tiers.py --report
    python scripts/backfill_topic_tiers.py --stamp-tiers [--limit 10] [--dry-run]
    python scripts/backfill_topic_tiers.py --queue-tiers 3,5 [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from services.supabase_factory import (  # noqa: E402
    SupabaseFactory, get_supabase_admin,
)
from services.topic_generation.agents import TierFitJudge  # noqa: E402
from services.topic_generation.agents.tier_fit_judge import (  # noqa: E402
    TIER_READERS,
)

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger('backfill_topic_tiers')

ALL_TIERS = tuple(sorted(TIER_READERS))


# ----------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------

def report(db) -> None:
    topics = (
        db.table('topics').select('id, target_age_tier').limit(10000).execute()
    ).data or []
    tests = (
        db.table('tests').select('id, target_age_tier').limit(10000).execute()
    ).data or []

    topic_counts = Counter(t.get('target_age_tier') for t in topics)
    test_counts = Counter(t.get('target_age_tier') for t in tests)

    print('tier   topics   tests')
    print('----   ------   -----')
    for tier in ALL_TIERS:
        print(f'T{tier}     {topic_counts.get(tier, 0):6d}  {test_counts.get(tier, 0):6d}')
    print(f'none   {topic_counts.get(None, 0):6d}  {test_counts.get(None, 0):6d}')
    print()
    thin = [t for t in ALL_TIERS if test_counts.get(t, 0) < 5
            and topic_counts.get(t, 0) >= 5]
    if thin:
        print(
            'Thin tiers with topics already available (T3.3): '
            + ', '.join(f'T{t}' for t in thin)
        )
        print(
            '  -> these need TESTS, not topics. Run with '
            f'--queue-tiers {",".join(str(t) for t in thin)}'
        )
    if topic_counts.get(None):
        print(
            f'Untiered topics (T3.4): {topic_counts[None]} '
            '-> run with --stamp-tiers'
        )


# ----------------------------------------------------------------------
# T3.4 — stamp a tier on untiered topics
# ----------------------------------------------------------------------

def stamp_tiers(db, limit: int, dry_run: bool) -> None:
    resp = (
        db.table('topics')
        .select('id, concept_english, distinctive_vocabulary')
        .is_('target_age_tier', 'null')
        .limit(limit)
        .execute()
    )
    topics = resp.data or []
    if not topics:
        logger.info('no untiered topics — nothing to stamp')
        return

    judge = TierFitJudge()
    stamped = skipped = 0

    for topic in topics:
        concept = topic.get('concept_english') or ''
        tier, verdicts = judge.best_tier(
            concept=concept,
            distinctive_vocabulary=topic.get('distinctive_vocabulary'),
            candidate_tiers=ALL_TIERS,
        )
        if tier is None:
            unjudged = sum(1 for _, v in verdicts if not v.judged)
            logger.warning(
                'no tier fits %r (%d of %d verdicts were fail-open, so the '
                'topic is left untiered rather than guessed)',
                concept[:50], unjudged, len(verdicts),
            )
            skipped += 1
            continue

        if dry_run:
            logger.info('[DRY RUN] %r -> T%s', concept[:50], tier)
            stamped += 1
            continue

        try:
            db.table('topics').update(
                {'target_age_tier': tier}
            ).eq('id', topic['id']).execute()
        except Exception as exc:
            logger.error('could not stamp %s: %s', topic['id'], exc)
            skipped += 1
            continue
        logger.info('%r -> T%s', concept[:50], tier)
        stamped += 1

    logger.info('Stamped %d topic(s); %d left untiered', stamped, skipped)


# ----------------------------------------------------------------------
# T3.3 — enqueue existing topics at the thin tiers
# ----------------------------------------------------------------------

def queue_tiers(db, tiers: list[int], dry_run: bool) -> None:
    languages = (
        db.table('dim_languages').select('id, language_code')
        .eq('is_active', True).execute()
    ).data or []
    if not languages:
        logger.error('no active languages — nothing to queue')
        return

    status = (
        db.table('dim_status').select('id, status_code')
        .eq('status_code', 'pending').limit(1).execute()
    ).data
    if not status:
        logger.error("no 'pending' row in dim_status — cannot queue")
        return
    pending_id = status[0]['id']

    topics = (
        db.table('topics').select('id, concept_english, target_age_tier')
        .in_('target_age_tier', tiers).limit(10000).execute()
    ).data or []
    if not topics:
        logger.info('no topics at tier(s) %s', tiers)
        return

    # Idempotent: never re-queue a (topic, language) pair that is already
    # sitting in the queue. Re-running this must be safe.
    existing = (
        db.table('production_queue').select('topic_id, language_id')
        .in_('topic_id', [t['id'] for t in topics]).limit(10000).execute()
    ).data or []
    already = {(row['topic_id'], row['language_id']) for row in existing}

    rows = [
        {
            'topic_id': topic['id'],
            'language_id': language['id'],
            'status_id': pending_id,
        }
        for topic in topics
        for language in languages
        if (topic['id'], language['id']) not in already
    ]

    if not rows:
        logger.info(
            'all %d topic(s) at tier(s) %s are already queued for every active '
            'language — nothing to add', len(topics), tiers,
        )
        return

    if dry_run:
        logger.info(
            '[DRY RUN] would queue %d topic-language pair(s) across tier(s) %s',
            len(rows), tiers,
        )
    else:
        db.table('production_queue').insert(rows).execute()
        logger.info(
            'Queued %d topic-language pair(s) across tier(s) %s',
            len(rows), tiers,
        )

    print()
    print('Queued only. To actually generate, run one batch per tier — the')
    print('batch tier is a CLI flag, not a property of the queue row:')
    for tier in tiers:
        for language in languages:
            print(
                f"  python scripts/run_test_generation_cli.py "
                f"--language {language['language_code']} --tier {tier} "
                f"--count <n>"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='store_true',
                        help='print per-tier topic and test coverage')
    parser.add_argument('--stamp-tiers', action='store_true',
                        help='T3.4: stamp a tier on untiered topics')
    parser.add_argument('--queue-tiers',
                        help='T3.3: comma-separated tiers to enqueue, e.g. 3,5')
    parser.add_argument('--limit', type=int, default=50,
                        help='max topics to stamp (default 50)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if not (args.report or args.stamp_tiers or args.queue_tiers):
        parser.error('nothing to do: pass --report, --stamp-tiers or --queue-tiers')

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()

    if args.report:
        report(db)
    if args.stamp_tiers:
        stamp_tiers(db, args.limit, args.dry_run)
    if args.queue_tiers:
        tiers = [int(t) for t in args.queue_tiers.split(',') if t.strip()]
        bad = [t for t in tiers if t not in ALL_TIERS]
        if bad:
            parser.error(f'unknown tier(s): {bad}')
        queue_tiers(db, tiers, args.dry_run)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
