"""
Immediate/recurring match sweep — word-list-import Step 4 (and, unmodified,
Step 5's future cron caller).

For each given `user_word_watchlist` row, finds an existing, active test
whose `tests.vocab_sense_ids` overlaps the row's `sense_id`, picks the one
closest in ELO to the user's current rating, and writes
`last_matched_test_id` / `last_matched_at` (+ resets `last_matched_surfaced_at`
on a genuinely NEW match) per the write contract documented in
migrations/word_upload_slot_scheduling.sql's header:

    "whenever a sweep sets last_matched_test_id to a NEW test_id ... it MUST
    reset last_matched_surfaced_at = NULL in the SAME UPDATE. Re-affirming
    the same test_id (no new match found) must leave last_matched_surfaced_at
    untouched."

Zero matches is an acceptable outcome (wiki/tasklist/word-list-import.plan.md)
— the row is left exactly as-is, no error.

ELO-closeness semantics are copied from the ALREADY-BUILT read side (the
`word_upload` slot block in migrations/word_upload_slot_scheduling.sql,
`build_daily_session`), not invented fresh here, so the two agree on what
"closest in ELO" means:

    JOIN test_skill_ratings tsr ON tsr.test_id = t.id
    JOIN dim_test_types dtt ON dtt.id = tsr.test_type_id AND dtt.is_active = true
    LEFT JOIN user_skill_ratings usr
           ON usr.user_id = wl.user_id
          AND usr.language_id = wl.language_id
          AND usr.test_type_id = tsr.test_type_id
    ...
    ORDER BY ABS(tsr.elo_rating - COALESCE(usr.elo_rating, 1200)) ASC

i.e. only ACTIVE-test-type skill rows count, and an unrated user skill
defaults to 1200 — replicated in Python below across a few round trips
(postgrest has no cross-table JOIN) rather than a single query.

This module is called from two places with no upload-specific assumptions:
Step 3's upload handler (immediate sweep, right after insert) and Step 5's
future recurring cron (a different, unrelated set of watchlist rows) — it
never reads `created_at` or anything else that would only make sense for a
freshly-inserted row.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_UNRATED_ELO_DEFAULT = 1200  # Same default get_recommended_tests / get_replay_tests /
                              # the word_upload slot block all use for an unrated skill.

# ---------------------------------------------------------------------------
# ELO-diff cutoff — a genuinely new judgment call, not mirrored from anywhere.
#
# Neither get_recommended_tests (migrations/task740_phase5b_topic_recency_
# exclusion.sql) nor get_replay_tests (migrations/get_replay_tests.sql) reject
# a candidate purely for being "too far away" in ELO — both ONLY sort by
# ABS(elo_diff) ASC among an already-curated candidate set (a fixed list of
# skill types, `rank_in_type <= 10`, or a caller-supplied `p_limit`). There is
# no equivalent pre-curated pool here: ANY active test whose vocab_sense_ids
# happens to contain the uploaded word's sense is a candidate, so "closest
# available" could still be a bad match if that happens to be the only test
# containing the sense (e.g. a beginner's sole matching test is an
# advanced-tier novel excerpt).
#
# dim_complexity_tiers (migrations/replace_cefr_with_age_tiers.sql) seeds 6
# tiers at initial_elo = 875 / 1175 / 1400 / 1550 / 1700 / 1925 — adjacent-tier
# gaps run 150-300 ELO points. 300 (the single largest adjacent-tier gap) is
# used here as an "at most about one tier away" cutoff: generous enough to
# rarely reject a genuinely reasonable match, while still refusing to ever
# surface the "closest of a bad bunch" when every candidate is wildly
# mismatched. Tunable — not a magic number buried inline.
# ---------------------------------------------------------------------------
ELO_MATCH_CUTOFF = 300


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_candidate_test_ids(db, sense_id: int, language_id: int) -> list:
    """Active tests whose vocab_sense_ids overlaps `sense_id`.

    Query construction mirrors scripts/audit_kana_fragments.py's
    `_reference_counts` helper (the one other Python/postgrest caller in this
    codebase that filters `tests.vocab_sense_ids` by array membership):

        db.table('tests').select('id', count='exact') \\
            .overlaps('vocab_sense_ids', [str(s) for s in sense_ids]).limit(1)

    — same `.overlaps(col, [str(sense_id)])` construction, itself modeled on
    the `tests_containing_sense` SQL RPC's
    `t.vocab_sense_ids @> ARRAY[p_sense_id]`
    (migrations/exercise_generation_schema.sql). The extra
    `.eq('language_id', language_id)` filter is not present in
    audit_kana_fragments.py, but mirrors tests_containing_sense's own
    belt-and-suspenders `JOIN dim_languages dl ON t.language = dl.code ...
    AND dl.id = p_language_id` — cheap, and correct defense in depth even
    though a sense_id should already be language-scoped by construction.
    """
    resp = (
        db.table('tests')
        .select('id')
        .overlaps('vocab_sense_ids', [str(sense_id)])
        .eq('is_active', True)
        .eq('language_id', language_id)
        .execute()
    )
    return [row['id'] for row in (resp.data or [])]


def _fetch_active_skill_rows(db, test_ids: list) -> list:
    """(test_id, test_type_id, elo_rating) triples for candidate tests,
    restricted to ACTIVE test types — mirrors the word_upload slot block's
    `JOIN dim_test_types dtt ON dtt.id = tsr.test_type_id AND dtt.is_active =
    true`. Two round trips (postgrest has no cross-table join)."""
    if not test_ids:
        return []

    tsr_resp = (
        db.table('test_skill_ratings')
        .select('test_id, test_type_id, elo_rating')
        .in_('test_id', test_ids)
        .execute()
    )
    rows = tsr_resp.data or []
    if not rows:
        return []

    type_ids = sorted({r['test_type_id'] for r in rows})
    active_resp = (
        db.table('dim_test_types')
        .select('id')
        .in_('id', type_ids)
        .eq('is_active', True)
        .execute()
    )
    active_type_ids = {r['id'] for r in (active_resp.data or [])}
    return [r for r in rows if r['test_type_id'] in active_type_ids]


def _fetch_user_elo_by_type(db, user_id: str, language_id: int, type_ids) -> dict:
    """{test_type_id: elo_rating} for the user's RATED skills only. A missing
    key means unrated -> caller applies the _UNRATED_ELO_DEFAULT (1200)
    COALESCE, exactly as the word_upload slot block's
    `COALESCE(usr.elo_rating, 1200)` does."""
    if not type_ids:
        return {}
    resp = (
        db.table('user_skill_ratings')
        .select('test_type_id, elo_rating')
        .eq('user_id', user_id)
        .eq('language_id', language_id)
        .in_('test_type_id', list(type_ids))
        .execute()
    )
    return {r['test_type_id']: r['elo_rating'] for r in (resp.data or [])}


def _find_closest_match(db, user_id: str, sense_id: int, language_id: int):
    """Return (test_id, elo_diff) for the ELO-closest eligible candidate, or
    (None, None) if there is no candidate at all, no candidate with an
    active-test-type skill rating, or the closest candidate still exceeds
    ELO_MATCH_CUTOFF.

    Ties (identical elo_diff across candidates) resolve to whichever
    candidate is encountered first in the DB's returned row order — this
    sweep makes no further claim about tie-breaking, since the plan does not
    specify one and both tied options are, by definition, equally
    ELO-appropriate.
    """
    test_ids = _fetch_candidate_test_ids(db, sense_id, language_id)
    if not test_ids:
        return None, None

    skill_rows = _fetch_active_skill_rows(db, test_ids)
    if not skill_rows:
        return None, None

    type_ids = {r['test_type_id'] for r in skill_rows}
    user_elo_by_type = _fetch_user_elo_by_type(db, user_id, language_id, type_ids)

    best_test_id = None
    best_diff = None
    for row in skill_rows:
        user_elo = user_elo_by_type.get(row['test_type_id'], _UNRATED_ELO_DEFAULT)
        diff = abs(row['elo_rating'] - user_elo)
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_test_id = row['test_id']

    if best_test_id is None or best_diff > ELO_MATCH_CUTOFF:
        return None, None
    return best_test_id, best_diff


def sweep_immediate_matches(watchlist_rows: list, db_client) -> dict:
    """For each given watchlist row, find an existing test whose
    vocab_sense_ids overlaps the row's sense_id at a level near the user's
    current ELO, and write last_matched_test_id/last_matched_at (+ reset
    last_matched_surfaced_at) if found. Returns a per-row match summary.

    Args:
        watchlist_rows: dicts shaped like `user_word_watchlist` rows, each
            requiring at least `id`, `sense_id`, `user_id`, `language_id`,
            and `last_matched_test_id` (may be None). Not assumed to be
            freshly inserted — callable unmodified by Step 5's recurring
            cron against any active watchlist row, regardless of age.
        db_client: Either a Supabase client directly (exposes `.table(...)`)
            or a duck-typed `TestDatabaseClient`-shaped wrapper exposing
            `.client` for the underlying Supabase client — matches the
            flexibility `services/word_list_import/upload_handler.py` and
            `services/vocabulary/word_resolver.py` already assume for their
            own `db_client` parameters.

    Returns:
        {
            'matched': int,      # rows that got a NEW last_matched_test_id
            'reaffirmed': int,   # rows whose existing match was re-confirmed
                                  # (same test_id written again; surfaced_at
                                  # left untouched)
            'no_match': int,     # rows left completely untouched
            'results': [
                {
                    'watchlist_id': ...,
                    'matched_test_id': int | None,
                    'elo_diff': int | None,
                    'changed': bool,  # True only for a genuinely new match
                },
                ...
            ],
        }
        One entry per input row, in input order.
    """
    db = db_client.client if hasattr(db_client, 'client') else db_client

    summary = {'matched': 0, 'reaffirmed': 0, 'no_match': 0, 'results': []}

    for row in watchlist_rows:
        watchlist_id = row['id']
        sense_id = row['sense_id']
        user_id = row['user_id']
        language_id = row['language_id']
        prior_test_id = row.get('last_matched_test_id')

        try:
            best_test_id, best_diff = _find_closest_match(
                db, user_id, sense_id, language_id,
            )
        except Exception as exc:
            logger.error(
                "Match sweep failed for watchlist row %s (sense %s, user %s): %s",
                watchlist_id, sense_id, user_id, exc,
            )
            summary['no_match'] += 1
            summary['results'].append({
                'watchlist_id': watchlist_id, 'matched_test_id': None,
                'elo_diff': None, 'changed': False, 'error': str(exc),
            })
            continue

        if best_test_id is None:
            # Zero matches is an acceptable outcome — leave the row as-is.
            summary['no_match'] += 1
            summary['results'].append({
                'watchlist_id': watchlist_id, 'matched_test_id': None,
                'elo_diff': None, 'changed': False,
            })
            continue

        is_new_match = best_test_id != prior_test_id
        update_payload = {
            'last_matched_test_id': best_test_id,
            'last_matched_at': _now_iso(),
        }
        if is_new_match:
            # Write contract (migrations/word_upload_slot_scheduling.sql
            # header): a NEW test_id MUST reset surfaced_at in the SAME
            # update. Re-affirming the same test_id must NOT touch it.
            update_payload['last_matched_surfaced_at'] = None

        db.table('user_word_watchlist').update(update_payload).eq(
            'id', watchlist_id,
        ).execute()

        summary['matched' if is_new_match else 'reaffirmed'] += 1
        summary['results'].append({
            'watchlist_id': watchlist_id, 'matched_test_id': best_test_id,
            'elo_diff': best_diff, 'changed': is_new_match,
        })

    return summary
