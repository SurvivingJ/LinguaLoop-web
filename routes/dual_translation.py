# routes/dual_translation.py
"""Dual Translation routes (TASK-607, +TASK-614) — serve + grade L1->L2
reproductions, plus the spaced-remediation card queue.

Endpoints:
  GET  /api/dual-translation/next               — serve the next passage
                                                    (interleaved with due
                                                    error cards, TASK-614)
  POST /api/dual-translation/<id>/submit        — grade a reproduction
  GET  /api/dual-translation/profile            — error-profile dashboard
  GET  /api/dual-translation/cards/due          — due error-remediation cards
  POST /api/dual-translation/cards/<id>/review  — grade a card review

This module owns the dt_submission/dt_grade/dt_error_instance persistence;
the actual grading is delegated wholesale to
``services.dual_translation.grader_cascade.grade_submission`` (TASK-606),
which is a pure function of (gold, reproduction, config) and never touches
the DB itself. Card generation (``dt_card`` rows from promoted
``dt_error_profile_entry`` clusters) is delegated to
``services.dual_translation.cards.generate_cards_for_queued_entries``
(TASK-614); FSRS scheduling reuses ``services.vocabulary.fsrs`` as-is —
error cards are NOT sense-linked, so they get their own ``dt_card`` table
rather than living in ``user_flashcards``.

dt_* tables have no RLS yet (TASK-602 notes: "ownership enforcement ... is
called out in the tech spec as an application-layer" concern) — every
submission/card read here re-checks ``user_id`` by hand before returning
anything.

L1 resolution: no table recorded a learner's native language before this
task (``user_languages`` is the L2 *study*-language enrollment table, not
an L1 designation). ``users.native_language_id`` was added alongside this
task (see migrations/add_users_native_language.sql) specifically so
``GET /next`` has somewhere real to read it from; it is nullable and
defaults to English until an onboarding UI sets it.
"""

import logging
import os
import random
from datetime import date, datetime, time as dtime, timezone
from typing import Optional

from flask import Blueprint, request, g, current_app

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from services.dimension_service import DimensionService
from services.dual_translation import cards as dt_cards
from services.dual_translation.grader_cascade import grade_submission, get_active_rubric
from services.vocabulary.fsrs import AGAIN, CardState, schedule_review
from utils.responses import (
    ApiResponse, api_success, api_error, bad_request, not_found, forbidden, server_error,
)

logger = logging.getLogger(__name__)
dual_translation_bp = Blueprint("dual_translation", __name__)

# TASK-614: roughly 1-in-N GET /next calls serves a due error card instead of
# a passage. Not a strict counter — a counter driven off dt_submission rows
# would get stuck re-triggering every subsequent call once the ratio is hit,
# since serving a card doesn't itself create a dt_submission row to advance
# past the threshold. A per-call probability self-corrects instead. Read
# straight from the environment (not Config) to match the other DT_* nightly
# tunables' convention (services/dual_translation/synthesis.py knobs).
DT_ERROR_CARD_INTERLEAVE_EVERY = max(1, int(os.environ.get('DT_ERROR_CARD_INTERLEAVE_EVERY', '4')))

# Fallback L1 while users.native_language_id is still unset for most rows
# (no onboarding UI captures it yet) — id 2 = English (config.py LANGUAGES).
DEFAULT_L1_LANGUAGE_ID = 2

# ADR-018: naturalness is de-emphasized everywhere and hidden outright in the
# rubric "feed-up" at the lowest age tiers, to avoid demotivation.
_NATURALNESS_HIDDEN_AGE_TIERS = (1, 2)


# ============================================================================
# GET /next
# ============================================================================

@dual_translation_bp.route('/next', methods=['GET'])
@supabase_jwt_required
def get_next() -> ApiResponse:
    """Serve the next dual-translation passage for the authenticated user.

    Selection: only dt_passage rows whose source_ref_id is a test the user
    has already completed (so content is inherently at-level), with an L1
    reference available for the user's resolved L1. Creates the
    dt_submission row up front (reproduction filled in later, at submit).
    """
    try:
        db = current_app.supabase_service
        if not db:
            return server_error("Database service not configured")

        user_id = g.current_user_id

        # TASK-614: interleave due error-remediation cards into the passage
        # stream so remediation happens in the flow of normal practice.
        if _should_serve_error_card():
            error_card = _next_due_error_card(db, user_id)
            if error_card:
                return api_success({'type': 'error_card', **error_card})

        l1_language_id = _resolve_l1_language_id(db, user_id)

        passage = _select_next_passage(db, user_id, l1_language_id)
        if not passage:
            return not_found("No dual-translation passage available yet")

        # TASK-617: assign + stamp the correction-style A/B arm at serve time.
        # Stamping it onto dt_submission (rather than only recomputing from
        # user_id later) keeps the experiment analyzable even if the config
        # mode or bucketing changes — the row records exactly what was shown.
        correction_style = Config.resolve_correction_style(user_id)

        submission_resp = db.table('dt_submission').insert({
            'user_id': user_id,
            'passage_id': passage['passage_id'],
            'l1_language_id': l1_language_id,
            'reproduction': '',
            'correction_style': correction_style,
        }).execute()
        if not submission_resp.data:
            return server_error("Failed to create submission")

        submission_id = submission_resp.data[0]['id']
        l2_code = DimensionService.get_language_code(passage['l2_language_id'])

        return api_success({
            'type': 'passage',
            'submission_id': submission_id,
            'l1_text': passage['l1_text'],
            'age_tier': passage['age_tier'],
            'rubric_descriptors': _rubric_descriptors_for(db, passage['age_tier'], l2_code),
            'correction_style': correction_style,
        })

    except Exception as e:
        logger.error("Error fetching next dual-translation passage: %s", e)
        return server_error("Failed to fetch next passage")


# ============================================================================
# POST /<submission_id>/submit
# ============================================================================

@dual_translation_bp.route('/<int:submission_id>/submit', methods=['POST'])
@supabase_jwt_required
def submit(submission_id: int) -> ApiResponse:
    """Grade a reproduction against its passage gold.

    Body: {reproduction: str, idempotency_key: str (optional)}.
    Idempotent: if this submission already has a persisted dt_grade, that
    grade is returned as-is rather than re-grading (dt_grade.submission_id
    is UNIQUE — a submission can only ever be graded once).
    """
    try:
        db = current_app.supabase_service
        if not db:
            return server_error("Database service not configured")

        data = request.get_json() or {}
        reproduction = data.get('reproduction')
        idempotency_key = data.get('idempotency_key')

        if not reproduction or not isinstance(reproduction, str):
            return bad_request("reproduction required")

        submission_row = _get_submission(db, submission_id)
        if not submission_row:
            return not_found("Submission not found")

        if submission_row['user_id'] != g.current_user_id:
            return forbidden("This submission does not belong to you")

        cached = _cached_grade(db, submission_id)
        if cached is not None:
            return api_success(cached)

        passage = _get_passage(db, submission_row['passage_id'])
        if not passage:
            return server_error("Passage for this submission no longer exists")

        if passage['status'] != 'active':
            return api_error("This passage has been retired", 400, error_code="PASSAGE_RETIRED")

        # TASK-601: budget gate. At/over the per-user/day token budget, cap
        # the cascade to Tier 0+1 rather than skip grading — grade_submission
        # never hard-fails on this, it just fails Tier 2's dimensions open.
        max_tier = 'tier1' if _tokens_used_today(db, g.current_user_id) >= Config.DT_DAILY_TOKEN_BUDGET else 'tier2'

        contract = grade_submission(
            db,
            passage_id=passage['id'],
            gold_l2=passage['l2_text'],
            reproduction=reproduction,
            l2_language_id=passage['l2_language_id'],
            l1_language_id=submission_row['l1_language_id'],
            age_tier=passage['age_tier'],
            max_tier=max_tier,
        )

        # TASK-628: a v2 grade with no scores (both the Detector and the Verifier
        # failed) is provisional and carries no evidence. Persisting it would poison
        # the idempotency cache — dt_grade.submission_id is UNIQUE, so _cached_grade
        # would then serve that empty grade forever (the TASK-633/ADR-019 hazard).
        # Skip persistence so the learner's retry re-grades; the provisional contract
        # still returns, and the UI shows the "grading incomplete — retry" notice.
        if contract.get('overall_band') is None:
            return api_success(contract)

        _persist_grade(db, submission_id, reproduction, idempotency_key, contract)

        # TASK-610: systematic errors are synthesised OFF the hot path by the
        # nightly job (scripts/dt_nightly_synthesis.py), which reads these
        # dt_error_instance rows directly and clusters/promotes them into
        # dt_error_profile_entry — there is no submit-time enqueue step.

        return api_success(contract)

    except Exception as e:
        logger.error("Error submitting dual-translation reproduction %s: %s", submission_id, e)
        return server_error("Failed to submit reproduction")


# ============================================================================
# GET /profile
# ============================================================================

@dual_translation_bp.route('/profile', methods=['GET'])
@supabase_jwt_required
def get_profile() -> ApiResponse:
    """Error-profile dashboard (TASK-611).

    Returns this user's ``dt_error_profile_entry`` rows — one per subtype
    cluster the TASK-610 nightly synthesis has produced — ranked by
    ``severity_rank`` (frequency × severity) with each row's trend snapshot.
    Self-regulation surface: the UI is expected to gamify the *shrinking
    profile* (counts trending down, subtypes reaching ``resolved``), never
    the raw score.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return server_error("Database service not configured")

        entries = _fetch_profile_entries(db, g.current_user_id)
        return api_success({'entries': entries})

    except Exception as e:
        logger.error("Error fetching error profile for %s: %s", g.current_user_id, e)
        return server_error("Failed to fetch error profile")


# ============================================================================
# GET /cards/due
# ============================================================================

@dual_translation_bp.route('/cards/due', methods=['GET'])
@supabase_jwt_required
def get_due_cards() -> ApiResponse:
    """Due error-remediation cards for the authenticated user (TASK-614).

    Lazily materialises ``dt_card`` rows for any newly-``queued``
    ``dt_error_profile_entry`` clusters first (pipeline steps 5-6 —
    [[features/dual-translation-remediation.tech]] §Pipeline), then returns
    the due queue interleaved by subtype so a review session never presents
    a long run of the same subtype back-to-back.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return server_error("Database service not configured")

        user_id = g.current_user_id
        dt_cards.generate_cards_for_queued_entries(db, user_id)

        due = _fetch_due_cards(db, user_id)
        interleaved = dt_cards.interleave_by_subtype(due)

        return api_success({'cards': interleaved, 'total': len(interleaved)})

    except Exception as e:
        logger.error("Error fetching due dual-translation cards for %s: %s", g.current_user_id, e)
        return server_error("Failed to fetch due cards")


# ============================================================================
# POST /cards/<card_id>/review
# ============================================================================

@dual_translation_bp.route('/cards/<int:card_id>/review', methods=['POST'])
@supabase_jwt_required
def submit_card_review(card_id: int) -> ApiResponse:
    """Grade a review of one error-remediation card (TASK-614).

    Body: ``{rating: 1-4, was_correct: bool (optional)}``. ``rating`` drives
    the FSRS state update via the reused ``services.vocabulary.fsrs``
    scheduler (mirrors ``routes/flashcards.py``'s ``submit_review``, minus
    the BKT update — error cards are subtype-keyed, not sense-linked).
    ``was_correct`` defaults to ``rating != AGAIN`` when the client doesn't
    pass an explicit value; it is logged separately from ``rating`` because
    it drives the recurrence-reduction dashboard metric, not scheduling.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return server_error("Database service not configured")

        data = request.get_json() or {}
        rating = data.get('rating')
        if rating not in (1, 2, 3, 4):
            return bad_request("valid rating (1-4) required")

        card_row = _get_card(db, card_id)
        if not card_row:
            return not_found("Card not found")
        if card_row['user_id'] != g.current_user_id:
            return forbidden("This card does not belong to you")

        new_card = _apply_card_review(card_row, rating)

        db.table('dt_card').update({
            'stability': new_card.stability,
            'difficulty': new_card.difficulty,
            'due_date': new_card.due_date.isoformat() if new_card.due_date else None,
            'last_review': datetime.now(timezone.utc).isoformat(),
            'reps': new_card.reps,
            'lapses': new_card.lapses,
            'state': new_card.state,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', card_id).execute()

        was_correct = data.get('was_correct')
        if was_correct is None:
            was_correct = rating != AGAIN
        db.table('dt_card_review').insert({
            'card_id': card_id,
            'rating': rating,
            'was_correct': was_correct,
        }).execute()

        return api_success({
            'next_due': new_card.due_date.isoformat() if new_card.due_date else None,
            'new_state': new_card.state,
            'stability': round(new_card.stability, 2) if new_card.stability else None,
        })

    except Exception as e:
        logger.error("Error submitting review for dual-translation card %s: %s", card_id, e)
        return server_error("Failed to submit card review")


# ============================================================================
# HELPERS — each is a boundary tests can monkeypatch independently
# ============================================================================

def _resolve_l1_language_id(db, user_id: str) -> int:
    """The learner's L1, from users.native_language_id. Falls back to
    English: no onboarding UI sets this column yet, so most rows are NULL."""
    resp = db.table('users').select('native_language_id').eq('id', user_id).limit(1).execute()
    if resp.data and resp.data[0].get('native_language_id'):
        return resp.data[0]['native_language_id']
    return DEFAULT_L1_LANGUAGE_ID


def _select_next_passage(db, user_id: str, l1_language_id: int) -> Optional[dict]:
    """First active, test_transcript-sourced passage from a test the user has
    completed that also has an L1 reference for l1_language_id."""
    attempts_resp = db.table('test_attempts').select('test_id').eq('user_id', user_id).execute()
    test_ids = list({str(row['test_id']) for row in (attempts_resp.data or [])})
    if not test_ids:
        return None

    passages_resp = (
        db.table('dt_passage')
        .select('id, l2_text, age_tier, l2_language_id')
        .eq('source_kind', 'test_transcript')
        .eq('status', 'active')
        .in_('source_ref_id', test_ids)
        .execute()
    )
    candidates = passages_resp.data or []

    for passage in candidates:
        ref_resp = (
            db.table('dt_passage_reference')
            .select('l1_text')
            .eq('passage_id', passage['id'])
            .eq('l1_language_id', l1_language_id)
            .limit(1)
            .execute()
        )
        if ref_resp.data:
            return {
                'passage_id': passage['id'],
                'l1_text': ref_resp.data[0]['l1_text'],
                'age_tier': passage['age_tier'],
                'l2_language_id': passage['l2_language_id'],
            }
    return None


def _rubric_descriptors_for(db, age_tier: int, l2_code: Optional[str]) -> dict:
    """Band descriptors for the active rubric at this age tier, in this L2 —
    the "feed-up" shown before reveal. Never blocks /next: a missing active
    rubric (TASK-604 not seeded) degrades to an empty dict, not an error."""
    try:
        rubric_cfg = get_active_rubric(db)
    except RuntimeError:
        return {}

    tier_cfg = (rubric_cfg.get('band_descriptors') or {}).get(str(age_tier), {})
    descriptors = {
        dim: bands[l2_code]
        for dim, bands in tier_cfg.items()
        if l2_code and l2_code in bands
    }
    if age_tier in _NATURALNESS_HIDDEN_AGE_TIERS:
        descriptors.pop('naturalness', None)
    return descriptors


def _tokens_used_today(db, user_id: str) -> int:
    """Sum of dt_grade.grader_trace token counts (in+out) across this user's
    submissions created since UTC midnight — the per-user/day budget window
    for the TASK-601 guardrail. Two-step (submissions then grades) rather
    than a join: the Supabase query-builder chain used everywhere else in
    this file has no join primitive."""
    start_of_day = datetime.combine(datetime.now(timezone.utc).date(), dtime.min, tzinfo=timezone.utc)
    submissions_resp = (
        db.table('dt_submission')
        .select('id')
        .eq('user_id', user_id)
        .gte('created_at', start_of_day.isoformat())
        .execute()
    )
    submission_ids = [row['id'] for row in (submissions_resp.data or [])]
    if not submission_ids:
        return 0

    grades_resp = (
        db.table('dt_grade')
        .select('grader_trace')
        .in_('submission_id', submission_ids)
        .execute()
    )
    total = 0
    for row in (grades_resp.data or []):
        tokens = (row.get('grader_trace') or {}).get('tokens') or {}
        total += int(tokens.get('in', 0) or 0) + int(tokens.get('out', 0) or 0)
    return total


def _get_submission(db, submission_id: int) -> Optional[dict]:
    resp = (
        db.table('dt_submission')
        .select('id, user_id, passage_id, l1_language_id')
        .eq('id', submission_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def _get_passage(db, passage_id: int) -> Optional[dict]:
    resp = (
        db.table('dt_passage')
        .select('id, l2_text, l2_language_id, age_tier, status')
        .eq('id', passage_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def _cached_grade(db, submission_id: int) -> Optional[dict]:
    """If submission_id already has a persisted dt_grade, reconstruct the
    §2.2 contract from it instead of letting the caller re-grade (dt_grade.
    submission_id is UNIQUE — a second grade attempt would otherwise hit an
    integrity error)."""
    grade_resp = (
        db.table('dt_grade')
        .select('scores, overall_band, diff, grader_trace')
        .eq('submission_id', submission_id)
        .limit(1)
        .execute()
    )
    if not grade_resp.data:
        return None

    grade = grade_resp.data[0]
    errors_resp = (
        db.table('dt_error_instance')
        .select(
            'span_reproduction, span_reference, category, subtype, source, '
            'severity, learner_form, corrected_form, explanation, confidence, is_mistake'
        )
        .eq('submission_id', submission_id)
        .execute()
    )
    return {
        'scores': grade['scores'],
        'overall_band': grade['overall_band'],
        'diff': grade['diff'],
        'errors': errors_resp.data or [],
        'grader_trace': grade['grader_trace'],
        # TASK-628: surface the persisted provisional flag so a cached provisional
        # grade (a single-tier failure that still had evidence) keeps showing the
        # retry notice. Absent on v1/tier0 grader_trace -> defaults False.
        'provisional': (grade['grader_trace'] or {}).get('provisional', False),
    }


# The dt_error_instance columns a cascade error dict may carry into the insert.
# The insert is column-whitelisted (not `{**error}`) because the v2 contract's
# errors now also carry response-only fields that are NOT columns — e.g.
# `explanation_parts` (TASK-630 §6c: the concatenated `explanation` string is
# persisted, its {rule, application} breakdown is returned but not stored). Mirrors
# the select list `_cached_grade` reads back.
_ERROR_INSERT_COLUMNS = (
    'span_reproduction', 'span_reference', 'category', 'subtype', 'source',
    'severity', 'learner_form', 'corrected_form', 'explanation', 'confidence',
    'is_mistake',
)


def _persist_grade(
    db, submission_id: int, reproduction: str, idempotency_key: Optional[str], contract: dict,
) -> None:
    """Write the reproduction text back onto dt_submission (it was created
    with a '' placeholder at /next time) plus N dt_error_instance rows and one
    dt_grade row from the cascade's contract.

    Ordering is load-bearing (TASK-633). ``_cached_grade`` keys entirely off
    the dt_grade row (submission_id is UNIQUE — never re-graded once present),
    so the dt_grade insert is deliberately LAST: the error rows must have
    landed before a cache-satisfying grade can exist. Were the grade written
    first and the error insert then failed (an un-migrated severity CHECK, a
    transient error), the cache would serve that submission forever with
    ``errors: []`` — silent, permanent loss of all evidence, violating the
    evidence-first invariant (ADR-019). Writing the grade last means a failed
    error insert leaves no grade behind, so the retry re-grades cleanly.
    dt_error_instance FKs dt_submission, not dt_grade, so nothing requires the
    reverse order."""
    db.table('dt_submission').update({
        'reproduction': reproduction,
        'idempotency_key': idempotency_key,
    }).eq('id', submission_id).execute()

    if contract['errors']:
        rows = [
            {**{k: error[k] for k in _ERROR_INSERT_COLUMNS if k in error},
             'submission_id': submission_id}
            for error in contract['errors']
        ]
        db.table('dt_error_instance').insert(rows).execute()

    db.table('dt_grade').insert({
        'submission_id': submission_id,
        'scores': contract['scores'],
        'overall_band': contract['overall_band'],
        'diff': contract['diff'],
        'grader_trace': contract['grader_trace'],
    }).execute()


def _fetch_profile_entries(db, user_id: str) -> list:
    """This user's ``dt_error_profile_entry`` rows, ranked by ``severity_rank``
    descending (frequency × severity — see services/dual_translation/synthesis.py).
    Language ids are resolved to codes here so the dashboard never has to."""
    resp = (
        db.table('dt_error_profile_entry')
        .select(
            'l1_language_id, l2_language_id, subtype, count, severity_rank, '
            'trend, remediation_status'
        )
        .eq('user_id', user_id)
        .order('severity_rank', desc=True)
        .execute()
    )
    return [
        {
            'subtype': row['subtype'],
            'l1_language': DimensionService.get_language_code(row['l1_language_id']),
            'l2_language': DimensionService.get_language_code(row['l2_language_id']),
            'count': row['count'],
            'severity_rank': row['severity_rank'],
            'remediation_status': row['remediation_status'],
            'trend': row.get('trend'),
        }
        for row in (resp.data or [])
    ]


# ============================================================================
# TASK-614 — error-card interleaving, due queue, FSRS review
# ============================================================================

def _should_serve_error_card() -> bool:
    """~1-in-``DT_ERROR_CARD_INTERLEAVE_EVERY`` GET /next calls serve a due
    error card instead of a passage."""
    return random.random() < (1.0 / DT_ERROR_CARD_INTERLEAVE_EVERY)


def _next_due_error_card(db, user_id: str) -> Optional[dict]:
    """One due error card (subtype-interleaved), materialising cards for any
    newly-``queued`` profile entries first. ``None`` if nothing is due."""
    dt_cards.generate_cards_for_queued_entries(db, user_id)
    due = _fetch_due_cards(db, user_id)
    if not due:
        return None
    return dt_cards.interleave_by_subtype(due)[0]


def _fetch_due_cards(db, user_id: str) -> list:
    """This user's due ``dt_card`` rows (``due_date`` today-or-earlier, or
    never-yet-reviewed ``new`` cards), oldest-due first. Not yet interleaved
    by subtype — callers run this through ``dt_cards.interleave_by_subtype``."""
    today = date.today().isoformat()
    resp = (
        db.table('dt_card')
        .select('id, card_type, subtype, prompt_payload, state, due_date')
        .eq('user_id', user_id)
        .or_(f'due_date.lte.{today},state.eq.new')
        .order('due_date')
        .execute()
    )
    return [
        {
            'card_id': row['id'],
            'card_type': row['card_type'],
            'subtype': row['subtype'],
            'prompt_payload': row['prompt_payload'],
            'state': row.get('state'),
            'due_date': row.get('due_date'),
        }
        for row in (resp.data or [])
    ]


def _get_card(db, card_id: int) -> Optional[dict]:
    resp = (
        db.table('dt_card')
        .select('id, user_id, stability, difficulty, due_date, last_review, reps, lapses, state')
        .eq('id', card_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def _apply_card_review(card_row: dict, rating: int) -> CardState:
    """Build the pre-review ``CardState`` from a ``dt_card`` row and run it
    through the reused FSRS scheduler (``services.vocabulary.fsrs``) — same
    reconstruction as ``routes/flashcards.py``'s ``submit_review``."""
    last_review = None
    if card_row.get('last_review'):
        last_review = datetime.fromisoformat(card_row['last_review'].replace('Z', '+00:00')).date()

    card = CardState(
        stability=card_row.get('stability') or 0,
        difficulty=card_row.get('difficulty') or 0.3,
        due_date=date.fromisoformat(card_row['due_date']) if card_row.get('due_date') else None,
        last_review=last_review,
        reps=card_row.get('reps') or 0,
        lapses=card_row.get('lapses') or 0,
        state=card_row.get('state') or 'new',
    )
    return schedule_review(card, rating)
