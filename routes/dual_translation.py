# routes/dual_translation.py
"""Dual Translation routes (TASK-607) — serve + grade L1->L2 reproductions.

Two endpoints:
  GET  /api/dual-translation/next             — serve the next passage
  POST /api/dual-translation/<id>/submit      — grade a reproduction

This module owns the dt_submission/dt_grade/dt_error_instance persistence;
the actual grading is delegated wholesale to
``services.dual_translation.grader_cascade.grade_submission`` (TASK-606),
which is a pure function of (gold, reproduction, config) and never touches
the DB itself.

dt_* tables have no RLS yet (TASK-602 notes: "ownership enforcement ... is
called out in the tech spec as an application-layer" concern) — every
submission read here re-checks ``user_id`` by hand before returning anything.

L1 resolution: no table recorded a learner's native language before this
task (``user_languages`` is the L2 *study*-language enrollment table, not
an L1 designation). ``users.native_language_id`` was added alongside this
task (see migrations/add_users_native_language.sql) specifically so
``GET /next`` has somewhere real to read it from; it is nullable and
defaults to English until an onboarding UI sets it.
"""

import logging
from typing import Optional

from flask import Blueprint, request, g, current_app

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from services.dimension_service import DimensionService
from services.dual_translation.grader_cascade import grade_submission, get_active_rubric
from utils.responses import (
    ApiResponse, api_success, api_error, bad_request, not_found, forbidden, server_error,
)

logger = logging.getLogger(__name__)
dual_translation_bp = Blueprint("dual_translation", __name__)

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

        # TODO(TASK-601): budget gate. Pass max_tier='tier1' when the user is
        # over their per-day token budget; no-op for now — always grades at
        # full tier2 since the budget config/check doesn't exist yet.
        contract = grade_submission(
            db,
            passage_id=passage['id'],
            gold_l2=passage['l2_text'],
            reproduction=reproduction,
            l2_language_id=passage['l2_language_id'],
            l1_language_id=submission_row['l1_language_id'],
            age_tier=passage['age_tier'],
        )

        _persist_grade(db, submission_id, reproduction, idempotency_key, contract)

        # TODO(TASK-610): enqueue systematic errors here for the error-profile
        # clustering/promotion job. dt_error_profile_entry doesn't exist yet
        # (TASK-609), so there is nothing to enqueue into — this is just the
        # marker for where that hook belongs once it does.

        return api_success(contract)

    except Exception as e:
        logger.error("Error submitting dual-translation reproduction %s: %s", submission_id, e)
        return server_error("Failed to submit reproduction")


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
    }


def _persist_grade(
    db, submission_id: int, reproduction: str, idempotency_key: Optional[str], contract: dict,
) -> None:
    """Write the reproduction text back onto dt_submission (it was created
    with a '' placeholder at /next time) plus one dt_grade row and N
    dt_error_instance rows from the cascade's contract."""
    db.table('dt_submission').update({
        'reproduction': reproduction,
        'idempotency_key': idempotency_key,
    }).eq('id', submission_id).execute()

    db.table('dt_grade').insert({
        'submission_id': submission_id,
        'scores': contract['scores'],
        'overall_band': contract['overall_band'],
        'diff': contract['diff'],
        'grader_trace': contract['grader_trace'],
    }).execute()

    if contract['errors']:
        rows = [{**error, 'submission_id': submission_id} for error in contract['errors']]
        db.table('dt_error_instance').insert(rows).execute()
