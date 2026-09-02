#!/usr/bin/env python3
"""Backfill ``l1_context`` onto stale ``dt_card`` cloze rows (TASK-740 follow-up).

Context: ``build_cloze_card`` (services/dual_translation/cards.py) did not
accept or store ``l1_context`` until commit ede24bd4. ``dt_card`` rows are
generated once and never rebuilt (``generate_cards_for_queued_entries`` skips
a profile entry that already has a card), so cloze cards materialised before
that commit are permanently missing the field the frontend
(``static/js/dt-error-card.js::promptHTML``) needs to show the L1 reference —
the cloze card renders with no English translation of the blanked sentence.

This is a one-time, idempotent repair: for every ``dt_card`` with
``card_type = 'cloze'`` whose ``prompt_payload`` lacks the ``l1_context`` key,
re-derive the error + source texts exactly as ``generate_cards_for_queued_entries``
would and merge in the ``l1_context`` that ``build_cloze_card`` would have
written, leaving ``prompt``/``answer`` (and everything else already reviewed
against it) untouched.

Usage:
    python scripts/backfill_dt_cloze_l1_context.py [--dry-run] [--user UUID]
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.dual_translation import cards as dt_cards

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('backfill_dt_cloze_l1_context')


def _find_stale_cloze_cards(db, user_id: str | None) -> list[dict]:
    """dt_card rows with card_type='cloze' and no 'l1_context' key in
    prompt_payload. PostgREST has no JSON "has key" filter usable server-side
    across all supabase-py versions, so the emptiness check is done here
    rather than pushed into the query."""
    q = (
        db.table('dt_card')
        .select('id, user_id, origin_error_id, prompt_payload')
        .eq('card_type', dt_cards.CARD_TYPE_CLOZE)
    )
    if user_id:
        q = q.eq('user_id', user_id)
    rows = q.execute().data or []
    return [r for r in rows if 'l1_context' not in (r.get('prompt_payload') or {})]


def _error_row(db, error_id: int) -> dict | None:
    resp = (
        db.table('dt_error_instance')
        .select('id, submission_id, span_reference, corrected_form')
        .eq('id', error_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help="Report what would change; write nothing.")
    parser.add_argument('--user', dest='user_id', default=None, help="Limit to one user_id (uuid).")
    args = parser.parse_args()

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()

    stale = _find_stale_cloze_cards(db, args.user_id)
    if not stale:
        logger.info("No stale cloze cards found (l1_context already present on every row).")
        return 0

    logger.info("Found %d stale cloze card(s).", len(stale))

    updated = 0
    skipped = 0
    for row in stale:
        card_id = row['id']
        error_id = row.get('origin_error_id')
        if error_id is None:
            logger.warning("card_id=%s has no origin_error_id — cannot re-derive, skipping.", card_id)
            skipped += 1
            continue

        error = _error_row(db, error_id)
        if error is None:
            logger.warning("card_id=%s origin_error_id=%s no longer exists — skipping.", card_id, error_id)
            skipped += 1
            continue

        gold_l2, l1_text = dt_cards._source_texts(db, error['submission_id'])
        if gold_l2 is None:
            logger.warning("card_id=%s submission_id=%s has no source passage — skipping.",
                            card_id, error['submission_id'])
            skipped += 1
            continue
        if not l1_text:
            logger.warning("card_id=%s has no L1 reference available (l1_text empty) — skipping.", card_id)
            skipped += 1
            continue

        rebuilt = dt_cards.build_cloze_card(
            {'span_reference': error['span_reference'], 'corrected_form': error['corrected_form']},
            gold_l2,
            l1_text,
        )
        new_l1_context = rebuilt['l1_context']
        if not new_l1_context:
            logger.warning("card_id=%s rebuilt l1_context is empty — skipping.", card_id)
            skipped += 1
            continue

        merged_payload = dict(row['prompt_payload'] or {})
        merged_payload['l1_context'] = new_l1_context

        logger.info("card_id=%s -> l1_context=%r", card_id, new_l1_context[:80])
        if not args.dry_run:
            db.table('dt_card').update({'prompt_payload': merged_payload}).eq('id', card_id).execute()
        updated += 1

    logger.info("%s%d updated, %d skipped.", "[dry-run] " if args.dry_run else "", updated, skipped)
    return 0


if __name__ == '__main__':
    sys.exit(main())
