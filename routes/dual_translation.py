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

import hashlib
import logging
import time
import os
import random
from datetime import date, datetime, time as dtime, timezone
from typing import Optional

from flask import Blueprint, request, g, current_app

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from services.dimension_service import DimensionService
from services.dual_translation import cards as dt_cards
from services.dual_translation import primed_token
from services.dual_translation import output_sanitizer
from services.dual_translation import provider_errors
from services.dual_translation.grader_cascade import grade_submission, get_active_rubric
from services.dual_translation.repair import budget as repair_budget
from services.dual_translation.repair import hooks as repair_hooks
from services.dual_translation.passage_builder import (
    MAX_WINDOW, SOURCE_KIND, DEFAULT_STATUS, difficulty_to_age_tier, join_sentences,
)
from services.dual_translation.sentence_refs import LANG_CODE as _LANG_CODE
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from services.study_time import clamp_active_ms, credit_study_time, parse_client_event_id
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

# GET /next 404 error codes: the learner has no eligible content in this
# language at all (take a test first) vs. has had every eligible passage graded.
NO_PASSAGES = 'NO_PASSAGES'
ALL_DONE = 'ALL_DONE'

# GET /next sentence-window fallback: at most this many attempted tests are
# examined per call (two small reads each), which bounds the call's latency for
# a learner with many attempted tests whose sentences have no references.
MAX_WINDOW_TESTS_PER_CALL = 40

# Weekly minutes: one error-card review is credited at most this long
# (task AC: DT card 120 s; the submit path allows 900 s).
DT_CARD_REVIEW_MAX_SECONDS = 120

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

    Query:
      ``language_id`` — the learner's selected study language (the L2 the
        passage is in). Validated against Config.VALID_LANGUAGE_IDS (400
        otherwise). When absent (an older cached client), the language of the
        learner's most recent test attempt is used.
      ``reserve=1`` — TASK-989: when nothing new is left, serve an already
        graded passage again (least recently graded first). The repeat is
        recorded as a repeat at submit (``_repeat_of``) and kept out of the
        error profile, the guided-repair queue and target-word evidence.
      ``test_id`` — only passages of this test (the test preview page's
        "Translate a passage from this test").

    Selection (``_choose_next``, 2026-11-17): only passages that already have a
    reviewed reference in the learner's L1 (no live generation), never one the
    learner has had graded (except with ``reserve``):

      1. a legacy whole passage of a test the learner attempted, never served;
      2. a new sentence window of a test the learner attempted;
      3. a legacy passage of a test the learner has NOT attempted, nearest the
         learner's level first (``from_untaken_test`` in the answer — the client
         says so, because the passage shows part of that test);
      4. a new sentence window of such a test, nearest level first;
      5. a passage served before but never graded, least recently served first;
      6. with ``reserve``: a graded passage, least recently graded first.

    404 ``ALL_DONE`` when nothing is left and the learner has had a passage
    graded in this language (the client then offers ``reserve``);
    ``NO_PASSAGES`` when nothing is eligible at all.

    TASK-990: the reads come from one database call (``dt_next_inputs``) with a
    per-table fallback. TASK-991: a passage the learner was served and never
    started reuses that open submission instead of inserting a new empty row.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return server_error("Database service not configured")

        user_id = g.current_user_id

        raw_language = request.args.get('language_id')
        if raw_language not in (None, ''):
            try:
                l2_language_id = int(raw_language)
            except (TypeError, ValueError):
                return bad_request("language_id must be an integer")
            if l2_language_id not in Config.VALID_LANGUAGE_IDS:
                return bad_request("language_id is not a supported study language")
        else:
            l2_language_id = None
        reserve = request.args.get('reserve') in ('1', 'true')
        only_test = (request.args.get('test_id') or '').strip() or None
        if only_test is not None and not _looks_like_uuid(only_test):
            return bad_request("test_id must be a test id")

        # TASK-614: interleave due error-remediation cards into the passage
        # stream. Only when the study language is known (TASK-991: a card of
        # another language is never served), and never on an explicit
        # reserve / single-test request.
        wants_card = not reserve and only_test is None and _should_serve_error_card()
        if wants_card and l2_language_id is not None:
            error_card = _next_due_error_card(db, user_id, l2_language_id)
            if error_card:
                return api_success({'type': 'error_card', **error_card})
            wants_card = False

        inputs = _next_inputs(db, user_id, l2_language_id)
        l2_language_id = inputs.l2
        if l2_language_id is None:
            return api_error(
                "No dual-translation passage yet - choose a study language first", 404,
                error_code=NO_PASSAGES,
            )
        if wants_card:
            error_card = _next_due_error_card(db, user_id, l2_language_id)
            if error_card:
                return api_success({'type': 'error_card', **error_card})

        choice = _choose_next(db, user_id, inputs.l1, l2_language_id, None,
                              reserve=reserve, test_id=only_test, inputs=inputs)
        if choice['kind'] == 'none':
            if choice.get('all_done'):
                return api_error(
                    "You have translated every passage available to you in this language",
                    404, error_code=ALL_DONE,
                )
            return api_error(
                "No dual-translation passage available yet", 404, error_code=NO_PASSAGES,
            )
        return _serve_choice(db, user_id, inputs, choice)

    except Exception as e:
        logger.error("Error fetching next dual-translation passage: %s", e, exc_info=True)
        return server_error("Failed to fetch next passage")


@dual_translation_bp.route('/test-available', methods=['GET'])
@supabase_jwt_required
def get_test_available() -> ApiResponse:
    """Can the learner translate a passage from this test right now?

    Query: ``test_id`` or ``slug`` (the preview page knows only the slug).
    ``{available, test_id, l1_language_id}``. Same rule
    as the prestudy Produce stage (``services.prestudy.produce_available``: a
    2-4 sentence window whose references in the learner's L1 all exist and clear
    the tightness floor), with the dual-translation L1 (``users.native_language_id``,
    English when unset). Never fails: any read error answers ``available: false``.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return server_error("Database service not configured")
        test_id = (request.args.get('test_id') or '').strip()
        slug = (request.args.get('slug') or '').strip()
        if test_id:
            if not _looks_like_uuid(test_id):
                return bad_request("test_id must be a test id")
            test = _get_test_for_passage(db, test_id)
        elif slug and len(slug) <= 200:
            rows = (
                db.table('tests').select('id, language_id, difficulty, transcript_hash')
                .eq('slug', slug).eq('is_active', True).limit(1).execute()
            ).data or []
            test = rows[0] if rows else None
        else:
            return bad_request("test_id or slug required")
        if not test:
            return not_found("Test not found")
        l1 = _resolve_l1_language_id(db, g.current_user_id)
        out = {'available': False, 'test_id': str(test['id']), 'l1_language_id': l1}
        if int(l1) != int(test['language_id']):
            from services import prestudy
            out['available'] = prestudy.produce_available(db, test, int(l1))
        return api_success(out)
    except Exception as e:
        logger.warning("dual-translation test availability failed: %s", e)
        return api_success({'available': False})


def _looks_like_uuid(value: str) -> bool:
    import uuid as _uuid
    try:
        _uuid.UUID(str(value))
        return True
    except (TypeError, ValueError, AttributeError):
        return False


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

        # silent: a malformed body is a 400 below, not an exception -> 500.
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        reproduction = data.get('reproduction')
        idempotency_key = data.get('idempotency_key')
        primed = data.get('primed_token')

        if not reproduction or not isinstance(reproduction, str):
            return bad_request("reproduction required")
        # Invisible/control characters out before grading, so the stored text,
        # the spans and the graded text are the same string (NUL would also fail
        # the dt_submission write). Markup is kept: it is the learner's text.
        reproduction = output_sanitizer.clean_learner_text(reproduction)
        if not reproduction:
            return bad_request("reproduction required")
        if len(reproduction) > output_sanitizer.MAX_REPRODUCTION_CHARS:
            return api_error(
                f"Your translation is longer than {output_sanitizer.MAX_REPRODUCTION_CHARS} characters",
                400, error_code="REPRODUCTION_TOO_LONG",
            )

        submission_row = _get_submission(db, submission_id)
        if not submission_row:
            return not_found("Submission not found")

        if submission_row['user_id'] != g.current_user_id:
            return forbidden("This submission does not belong to you")

        cached = _cached_grade(db, submission_id)
        if cached is not None:
            if cached.get('repeat_of'):
                return api_success(cached)  # a repeat never has a repair session
            # Guided self-repair: the existing session (redacted while open), or
            # one created now if grading succeeded but the session was not.
            return api_success(repair_hooks.for_cached(db, g.current_user_id, submission_id, cached))

        passage = _get_passage(db, submission_row['passage_id'])
        if not passage:
            return server_error("Passage for this submission no longer exists")

        if passage['status'] != 'active':
            return api_error("This passage has been retired", 400, error_code="PASSAGE_RETIRED")

        # TASK-989: a passage this learner already had graded (re-served on
        # request) is graded and shown as usual but recorded as a repeat.
        repeat_of = _repeat_of(db, g.current_user_id, submission_row)

        # TASK-601: budget gate. At/over the per-user/day token budget, cap
        # the cascade to Tier 0+1 rather than skip grading — grade_submission
        # never hard-fails on this, it just fails Tier 2's dimensions open.
        max_tier = 'tier1' if _tokens_used_today(db, g.current_user_id) >= Config.DT_DAILY_TOKEN_BUDGET else 'tier2'

        # TASK-910: the prestudy Produce stage echoes the signed primed-sense
        # token issued by /passage-from-sentences; its senses become the
        # grader's target words. A bad token is a 400, never a silent drop —
        # the per-word rows are the whole point of that stage.
        target_ctx = None
        if primed is not None:
            try:
                target_ids = primed_token.load(primed, g.current_user_id, passage['id'])
            except primed_token.PrimedTokenError as e:
                return bad_request(str(e))
            if target_ids:
                target_ctx = _target_word_context(db, passage, target_ids)

        with provider_errors.capture() as grading_calls:
            contract = grade_submission(
                db,
                passage_id=passage['id'],
                gold_l2=passage['l2_text'],
                reproduction=reproduction,
                l2_language_id=passage['l2_language_id'],
                l1_language_id=submission_row['l1_language_id'],
                age_tier=passage['age_tier'],
                max_tier=max_tier,
                **(target_ctx or {}),
            )

        # The grading provider refused every call (key limit / no credits /
        # bad key / daily quota) and no model answered: nothing graded this
        # submission and an immediate retry would be refused the same way. Say
        # so with a stable code instead of returning an empty provisional grade
        # (whose UI invites a retry), and save nothing — the submission stays
        # ungraded, so a later submit grades it normally.
        if grading_calls.refused_without_answer():
            logger.error(
                "DT grading unavailable: provider refused every grading call "
                "(user=%s submission=%s passage=%s l2=%s max_tier=%s): %s",
                g.current_user_id, submission_id, passage['id'], passage['l2_language_id'],
                max_tier, grading_calls.summary(),
            )
            return api_error(
                "Grading is temporarily unavailable. Your translation was not graded; "
                "please try again later.",
                503, error_code=provider_errors.ERROR_CODE,
            )

        # ADR-044: the single-call grader's per-model-call records are storage
        # material, not part of the response contract — take them off before the
        # contract is returned or persisted.
        grading_assets = contract.pop('grading_assets', None)

        # TASK-628: a v2 grade with no scores (both the Detector and the Verifier
        # failed) is provisional and carries no evidence. Persisting it would poison
        # the idempotency cache — dt_grade.submission_id is UNIQUE, so _cached_grade
        # would then serve that empty grade forever (the TASK-633/ADR-019 hazard).
        # Skip persistence so the learner's retry re-grades; the provisional contract
        # still returns, and the UI shows the "grading incomplete — retry" notice.
        if contract.get('overall_band') is None:
            return api_success(contract)

        # A grade that is not well-formed (a band outside 1-4, a malformed span)
        # is never stored half-valid: it is answered as provisional, unsaved,
        # exactly like a grade with no scores, so a retry grades it again.
        problems = output_sanitizer.contract_problems(contract)
        if problems:
            logger.error("DT grade for submission %s not stored, malformed: %s", submission_id, problems[:5])
            contract = output_sanitizer.sanitize_contract(contract)
            contract['provisional'] = True
            return api_success(contract)

        # D (2026-11-17): every model-derived string is plain text with a
        # documented cap and no NUL/control characters before it is stored or
        # returned, whatever model produced it.
        contract = output_sanitizer.sanitize_contract(contract)
        grading_assets = output_sanitizer.sanitize_assets(grading_assets)

        if repeat_of:
            _persist_grade(db, submission_id, reproduction, idempotency_key, contract,
                           repeat_of=repeat_of)
        else:
            _persist_grade(db, submission_id, reproduction, idempotency_key, contract)
        _persist_grading_assets(db, submission_id, grading_assets)

        if repeat_of:
            # A repeat's errors are kept on dt_grade only (see _persist_grade): no
            # dt_error_instance rows (error profile / recurrence trends / cards),
            # no guided-repair session or queue items, no target-word BKT evidence.
            contract['repeat_of'] = _public_repeat(repeat_of)
            response = contract
        else:
            # Guided self-repair (wiki/features/dt-guided-self-repair.tech.md 3.3): the
            # response to send. Never raises; not eligible / any failure -> `contract`
            # itself. The side effects below keep reading the unredacted `contract`.
            response = repair_hooks.after_grade(
                db, user_id=g.current_user_id, submission_row=submission_row, passage=passage,
                contract=contract, reproduction=reproduction,
            )

        # TASK-910: one production-evidence row per primed sense. Not part of
        # _persist_grade (whose ordering contract is about dt_grade caching);
        # best-effort, like the dictation BKT write.
        if contract.get('target_words') and not repeat_of:
            _record_target_word_evidence(
                db, g.current_user_id, passage['l2_language_id'], submission_id,
                contract['target_words'],
            )
            # Test prestudy: store the Produce result on the prime session and
            # send omitted primed words to next-day review. Best-effort.
            if passage.get('source_ref_id'):
                from services import prestudy
                prestudy.record_produce(
                    db, g.current_user_id, str(passage['source_ref_id']),
                    passage['l2_language_id'], submission_id, contract['target_words'],
                )

        # Weekly minutes: credit once, on the first persisted grading only
        # (the cached path above returns early). Best-effort, clamped to 900 s.
        credit_study_time(
            db, g.current_user_id, passage['l2_language_id'], 'dual_translation',
            clamp_active_ms('dual_translation', data.get('active_ms')),
            'dt_submission', submission_id,
        )

        # TASK-610: systematic errors are synthesised OFF the hot path by the
        # nightly job (scripts/dt_nightly_synthesis.py), which reads these
        # dt_error_instance rows directly and clusters/promotes them into
        # dt_error_profile_entry — there is no submit-time enqueue step.

        return api_success(response)

    except Exception as e:
        logger.error("Error submitting dual-translation reproduction %s: %s", submission_id, e)
        return server_error("Failed to submit reproduction")


# ============================================================================
# POST /passage-from-sentences  (TASK-909, ADR-037)
# ============================================================================

@dual_translation_bp.route('/passage-from-sentences', methods=['POST'])
@supabase_jwt_required
def passage_from_sentences() -> ApiResponse:
    """Find or create the ``dt_passage`` for a sentence range of a test and
    open a submission on it — the prestudy Produce stage's entry point.

    Body: ``{test_id, sentence_start, sentence_end, l1_language_id,
    primed_sense_ids[]}`` (indices inclusive, into ``test_sentences.idx``).

    * 403 when the user has no attempt on the test (DT's existing rule:
      passages come only from attempted tests);
    * 422 when any sentence in the range lacks an active ``pass``/``rewritten``
      reference in that L1 (``missing_idx`` names them so the client can fall
      back to the best fully covered window), or the range has no sentence
      rows;
    * 409 when the sentence rows are stale for the stored transcript.

    The passage is keyed by ``(source_ref_id, sentence_start, sentence_end)``
    (partial unique index) so the same range always yields the same
    ``passage_id``; ``l2_text`` is never returned. The primed senses are not
    stored: they come back signed as ``primed_token``, which the client echoes
    on ``POST /<submission_id>/submit`` (see services/dual_translation/primed_token.py).

    Deviation from the tech page's "dt_passage insert, nothing else": a
    ``dt_submission`` row is created too (as ``GET /next`` does), because the
    existing submit route grades a submission, not a passage — without it the
    client could not submit the reproduction.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return server_error("Database service not configured")
        user_id = g.current_user_id

        data = request.get_json(silent=True) or {}
        test_id = data.get('test_id')
        try:
            start = int(data.get('sentence_start'))
            end = int(data.get('sentence_end'))
            l1_language_id = int(data.get('l1_language_id'))
        except (TypeError, ValueError):
            return bad_request("test_id, sentence_start, sentence_end and l1_language_id required")
        if not test_id or not isinstance(test_id, str):
            return bad_request("test_id required")
        n_sentences = end - start + 1
        if start < 0 or n_sentences < 1 or n_sentences > MAX_WINDOW:
            return bad_request(f"sentence range must cover 1-{MAX_WINDOW} sentences")
        primed_ids = data.get('primed_sense_ids') or []
        if not isinstance(primed_ids, list):
            return bad_request("primed_sense_ids must be a list")

        return open_range_passage(db, user_id, test_id, start, end, l1_language_id, primed_ids)

    except Exception as e:
        logger.error("Error building passage from sentences: %s", e)
        return server_error("Failed to build passage")


def open_range_passage(db, user_id: str, test_id: str, start: int, end: int, l1_language_id: int,
                       primed_ids: list, extra: Optional[dict] = None) -> ApiResponse:
    """Core of POST /passage-from-sentences, shared with the prestudy Produce
    route (POST /api/tests/<id>/prestudy/produce), which picks the window
    itself. ``extra`` keys are merged into the success payload."""
    n_sentences = end - start + 1
    if not _user_has_attempted(db, user_id, test_id):
        return forbidden("Dual translation passages come only from tests you have attempted")

    test = _get_test_for_passage(db, test_id)
    if not test:
        return not_found("Test not found")
    if l1_language_id == int(test['language_id']):
        return bad_request("l1_language_id must differ from the test's language")

    sentences = _get_sentence_range(db, test_id, start, end)
    if len(sentences) != n_sentences:
        return api_error(
            "No sentence rows for this range", 422, error_code="SENTENCES_MISSING",
        )
    stored_hash = test.get('transcript_hash')
    if stored_hash and any(sr.get('transcript_hash') != stored_hash for sr in sentences):
        return api_error(
            "Sentence rows are stale for this transcript", 409, error_code="SENTENCES_STALE",
        )

    refs = _get_usable_references(db, [sr['id'] for sr in sentences], l1_language_id)
    missing = [sr['idx'] for sr in sentences if sr['id'] not in refs]
    if missing:
        return api_error(
            "A sentence in this range has no reference in that language", 422,
            error_code="REFERENCE_MISSING", details={'missing_idx': missing},
        )

    l2_code = _LANG_CODE.get(int(test['language_id']), 'en')
    l1_code = _LANG_CODE.get(l1_language_id, 'en')
    passage = _find_or_create_range_passage(
        db, test, start, end,
        l2_text=join_sentences([sr['l2_text'] for sr in sentences], l2_code),
    )
    if not passage:
        return server_error("Failed to create passage")
    if passage.get('status') not in (None, 'active'):
        # TASK-991: an existing window passage that was retired is never opened
        # (submit would answer PASSAGE_RETIRED after the learner wrote it).
        return api_error("This passage has been retired", 409, error_code="PASSAGE_RETIRED")
    l1_text = join_sentences([refs[sr['id']]['l1_text'] for sr in sentences], l1_code)

    correction_style = Config.resolve_correction_style(user_id)
    submission_resp = db.table('dt_submission').insert({
        'user_id': user_id,
        'passage_id': passage['id'],
        'l1_language_id': l1_language_id,
        'reproduction': '',
        'correction_style': correction_style,
    }).execute()
    if not submission_resp.data:
        return server_error("Failed to create submission")

    return api_success({
        **(extra or {}),
        'passage_id': passage['id'],
        'l1_text': l1_text,
        'n_sentences': n_sentences,
        'submission_id': submission_resp.data[0]['id'],
        'age_tier': passage['age_tier'],
        'rubric_descriptors': _rubric_descriptors_for(db, passage['age_tier'], l2_code),
        'correction_style': correction_style,
        'primed_token': primed_token.issue(user_id, passage['id'], primed_ids),
    })


def _user_has_attempted(db, user_id: str, test_id: str) -> bool:
    resp = (
        db.table('test_attempts').select('id')
        .eq('user_id', user_id).eq('test_id', test_id).limit(1).execute()
    )
    return bool(resp.data)


def _get_test_for_passage(db, test_id: str) -> Optional[dict]:
    resp = (
        db.table('tests').select('id, language_id, difficulty, transcript_hash')
        .eq('id', test_id).eq('is_active', True).limit(1).execute()
    )
    return resp.data[0] if resp.data else None


def _get_sentence_range(db, test_id: str, start: int, end: int) -> list:
    resp = (
        db.table('test_sentences')
        .select('id, idx, l2_text, token_start, token_end, transcript_hash')
        .eq('test_id', test_id).gte('idx', start).lte('idx', end).order('idx').execute()
    )
    return resp.data or []


_USABLE_VERDICTS = ('pass', 'rewritten')


def _get_usable_references(db, sentence_ids: list, l1_language_id: int) -> dict:
    """``{sentence_id: row}`` for active references with a usable review verdict."""
    if not sentence_ids:
        return {}
    resp = (
        db.table('test_sentence_references')
        .select('sentence_id, l1_text, tightness, review_verdict')
        .in_('sentence_id', sentence_ids)
        .eq('l1_language_id', l1_language_id)
        .eq('is_active', True)
        .in_('review_verdict', list(_USABLE_VERDICTS))
        .execute()
    )
    return {
        row['sentence_id']: row for row in (resp.data or [])
        if row.get('review_verdict') in _USABLE_VERDICTS
    }


def _find_or_create_range_passage(db, test: dict, start: int, end: int, *, l2_text: str,
                                  known_absent: bool = False) -> Optional[dict]:
    """The ``dt_passage`` for (test, start, end): existing row, else inserted.
    A lost race on the partial unique index re-reads the winner's row.
    ``known_absent``: the caller just read that no such row exists (GET /next's
    read bundle), so the select is skipped."""
    if not known_absent:
        existing = _select_range_passage(db, str(test['id']), start, end)
        if existing:
            return existing
    payload = {
        'l2_language_id': test['language_id'],
        'source_kind': SOURCE_KIND,
        'source_ref_id': str(test['id']),
        'l2_text': l2_text,
        'age_tier': difficulty_to_age_tier(test.get('difficulty')),
        'register': None,
        'status': DEFAULT_STATUS,
        'sentence_start': start,
        'sentence_end': end,
    }
    try:
        resp = db.table('dt_passage').insert(payload).execute()
        if resp.data:
            return resp.data[0]
    except Exception as e:
        logger.info("dt_passage range insert lost a race or failed (%s); re-reading", e)
    return _select_range_passage(db, str(test['id']), start, end)


def _select_range_passage(db, source_ref_id: str, start: int, end: int) -> Optional[dict]:
    resp = (
        db.table('dt_passage').select('id, age_tier, l2_language_id, status')
        .eq('source_ref_id', source_ref_id)
        .eq('sentence_start', start).eq('sentence_end', end)
        .limit(1).execute()
    )
    return resp.data[0] if resp.data else None


# ============================================================================
# TASK-910 — target words (per-word production evidence)
# ============================================================================

def _target_word_context(db, passage: dict, target_ids: list) -> dict:
    """The ``grade_submission`` kwargs for target-word classification: the
    token-map slice covering the passage's sentence range and the senses'
    lemmas. A passage without range columns (a pre-ADR-037 window) gets the
    whole test's token map — surfaces are then located in the gold by text."""
    token_map: list = []
    lemmas: dict = {}
    try:
        test_resp = (
            db.table('tests').select('vocab_token_map')
            .eq('id', passage.get('source_ref_id')).limit(1).execute()
        )
        full_map = (test_resp.data[0].get('vocab_token_map') if test_resp.data else None) or []
        start, end = passage.get('sentence_start'), passage.get('sentence_end')
        if full_map and start is not None and end is not None:
            rows = _get_sentence_range(db, passage['source_ref_id'], int(start), int(end))
            spans = [r for r in rows if r.get('token_start') is not None and r.get('token_end') is not None]
            if spans and len(spans) == len(rows):
                token_map = full_map[int(spans[0]['token_start']):int(spans[-1]['token_end'])]
            else:
                token_map = full_map
        else:
            token_map = full_map
        sense_resp = (
            db.table('dim_word_senses').select('id, dim_vocabulary(lemma)')
            .in_('id', [int(t) for t in target_ids]).execute()
        )
        for row in (sense_resp.data or []):
            lemma = (row.get('dim_vocabulary') or {}).get('lemma')
            if lemma:
                lemmas[int(row['id'])] = lemma
    except Exception as e:
        logger.warning("target-word context lookup failed (non-fatal): %s", e)
    return {
        'target_sense_ids': [int(t) for t in target_ids],
        'target_token_map': token_map,
        'target_lemmas': lemmas,
    }


def _record_target_word_evidence(db, user_id: str, language_id: int, submission_id: int, rows: list) -> None:
    """One ``user_vocabulary_knowledge`` evidence point per primed sense via
    the batch BKT RPC with ``side_effects=False`` (no flashcard creation, no
    ladder seeding, no frequency inference): Produce is evidence, never
    admission ([[features/test-prestudy]]). Never raises.

    TODO(TASK-910): no exercise_attempts row is written. exercise_attempts has
    no `source` column and `exercise_id` is the only link to an exercise
    (migrations/create_all_tables.sql); a write path for non-exercise sources
    (`source = 'prestudy_produce'`) does not exist yet. Add the column + a
    nullable-exercise insert path, then record one row per sense here.
    Omitted senses go to next-day review through ``prestudy.record_produce``
    (called by the submit route after this).
    """
    results = [
        {'sense_id': int(r['sense_id']), 'is_correct': bool(r.get('is_correct'))}
        for r in (rows or []) if r.get('sense_id')
    ]
    if not results:
        return
    try:
        updated = VocabularyKnowledgeService(db).update_from_word_tests_batch(
            user_id=user_id, language_id=language_id, results=results, side_effects=False,
        )
        logger.info(
            "DT target words: user=%s submission=%s %d senses -> %d BKT rows",
            user_id, submission_id, len(results), len(updated or []),
        )
    except Exception as e:
        logger.warning("DT target-word evidence write failed (non-fatal): %s", e)


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

        _credit_card_review_time(db, card_row, data)

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


def _read_all_pages(make_query) -> list:
    """Every row of a select, read page by page. PostgREST caps one response
    at ``_POSTGREST_ROW_CAP`` rows, so an unpaged read of a table that grows
    per learner (dt_submission gains a row on every GET /next) silently
    truncates. ``make_query()`` must return a fresh, totally ordered select."""
    rows: list = []
    start = 0
    while True:
        page = make_query().range(start, start + _POSTGREST_ROW_CAP - 1).execute().data or []
        rows += page
        if len(page) < _POSTGREST_ROW_CAP:
            return rows
        start += _POSTGREST_ROW_CAP


def _attempted_tests(db, user_id: str) -> list:
    """This user's test attempts as ``[{test_id, language_id, created_at}]``,
    most recent first (one row per attempt; a test can repeat)."""
    return _read_all_pages(lambda: (
        db.table('test_attempts').select('id, test_id, language_id, created_at')
        .eq('user_id', user_id).order('created_at', desc=True).order('id', desc=True)
    ))


def _latest_attempt_language(attempts: list) -> Optional[int]:
    """GET /next with no ``language_id``: the study language of the learner's
    most recent test attempt, or None when they have none."""
    for row in attempts:
        if row.get('language_id'):
            return int(row['language_id'])
    return None


def _rotation_key(user_id: str, item, salt: int) -> str:
    """Deterministic-but-varied order: a stable hash of (user, item, salt). The
    salt is the number of passages this learner has been served, so the order
    is reproducible for a given state and changes after every serve."""
    return hashlib.sha256(f"{user_id}|{item}|{salt}".encode('utf-8')).hexdigest()


def _served_history(db, user_id: str, l1_language_id: Optional[int] = None) -> dict:
    """``{passage_id: {last_served, graded, last_graded_at, band, open_id}}``
    over all of this user's dt_submission rows (a passage served twice keeps its
    latest serve). ``open_id``: the newest submission on the passage with no
    grade and no reproduction yet (in ``l1_language_id`` when given) — GET /next
    reuses it instead of inserting another empty row (TASK-991)."""
    subs = _read_all_pages(lambda: (
        db.table('dt_submission').select('id, passage_id, created_at, reproduction, l1_language_id')
        .eq('user_id', user_id).order('id')
    ))
    grades: dict = {}
    sub_ids = [row['id'] for row in subs]
    for i in range(0, len(sub_ids), 200):
        part = sub_ids[i:i + 200]
        rows = (
            db.table('dt_grade').select('submission_id, created_at, overall_band')
            .in_('submission_id', part).execute()
        ).data or []
        for r in rows:
            grades[r['submission_id']] = r
    history: dict = {}
    for row in subs:
        pid = row['passage_id']
        entry = history.setdefault(pid, {'last_served': '', 'graded': False, 'last_graded_at': None,
                                         'band': None, 'open_id': None})
        served = str(row.get('created_at') or '')
        if served > entry['last_served']:
            entry['last_served'] = served
        grade = grades.get(row['id'])
        if grade is not None:
            entry['graded'] = True
            at = str(grade.get('created_at') or '')
            if entry['last_graded_at'] is None or at >= entry['last_graded_at']:
                entry['last_graded_at'] = at
                entry['band'] = grade.get('overall_band')
        elif not (row.get('reproduction') or '') and (
                l1_language_id is None or row.get('l1_language_id') in (None, l1_language_id)):
            if entry['open_id'] is None or row['id'] > entry['open_id']:
                entry['open_id'] = row['id']
    return history


def _legacy_reference(db, passage_id: int, l1_language_id: int) -> Optional[str]:
    resp = (
        db.table('dt_passage_reference').select('l1_text')
        .eq('passage_id', passage_id).eq('l1_language_id', l1_language_id)
        .limit(1).execute()
    )
    return resp.data[0]['l1_text'] if resp.data else None


def _served_passage(passage: dict, l1_text: str) -> dict:
    return {
        'passage_id': passage['id'],
        'l1_text': l1_text,
        'age_tier': passage['age_tier'],
        'l2_language_id': passage['l2_language_id'],
    }


def _choose_next(db, user_id: str, l1_language_id: int, l2_language_id: int,
                 attempts: Optional[list], *, reserve: bool = False,
                 test_id: Optional[str] = None, inputs: Optional['_NextInputs'] = None) -> dict:
    """Pick what GET /next serves. Returns one of

    * ``{'kind': 'passage', 'passage': {passage_id, l1_text, age_tier, l2_language_id}}``
      — an existing passage with an L1 reference (legacy, or a served window);
    * ``{'kind': 'range', 'test_id', 'start', 'end'}`` — a sentence window to
      open (``_serve_choice``; ``open_range_passage`` for other callers);
    * ``{'kind': 'none', 'all_done': bool}`` — nothing eligible; ``all_done``
      when the learner has had a passage of this language graded.

    A passage or window from a test the learner has not attempted also carries
    ``'untaken': True``; a re-served graded passage (``reserve``) carries
    ``'repeat_of': {'graded_at', 'band'}``. The order is in get_next's docstring.

    ``inputs`` is the read bundle (``_next_inputs``); without it the per-table
    reads are used, starting from ``attempts`` (test_attempts rows).
    """
    if inputs is None:
        inputs = _TableInputs(db, user_id, l1_language_id, l2_language_id, attempts)
    if l1_language_id == l2_language_id:
        return {'kind': 'none', 'all_done': False}
    l2 = int(l2_language_id)
    history = inputs.history
    salt = inputs.salt
    only = str(test_id) if test_id else None

    def in_scope(test) -> bool:
        return only is None or str(test) == only

    # Served windows (graded or not) and retired range passages are never part
    # of a new window.
    blocked = _served_ranges(list(inputs.passages.values()))

    # 1 / 3. Legacy whole passages never served, attempted tests first.
    legacy = [p for p in inputs.legacy_passages()
              if int(p.get('l2_language_id') or l2) == l2 and in_scope(p.get('source_ref_id'))]
    unseen = [p for p in legacy if p['id'] not in history]
    taken_legacy = sorted(
        (p for p in unseen if str(p.get('source_ref_id')) in inputs.attempted),
        key=lambda p: _rotation_key(user_id, p['id'], salt),
    )
    for passage in taken_legacy:
        l1_text = inputs.legacy_text(passage)
        if l1_text:
            return {'kind': 'passage', 'passage': _served_passage(passage, l1_text)}

    # 2. A new window of an attempted test (ADR-037 sentence references).
    taken_tests = inputs.taken_tests(only)
    window = _first_window(inputs, taken_tests, l2, blocked)
    if window:
        return {'kind': 'range', **window}

    # 3. Legacy passages of tests not attempted yet, nearest the learner's level.
    level = inputs.level_order()
    untaken_legacy = sorted(
        (p for p in unseen if str(p.get('source_ref_id')) not in inputs.attempted),
        key=lambda p: (*level(p.get('source_ref_id')), _rotation_key(user_id, p['id'], salt)),
    )
    for passage in untaken_legacy:
        l1_text = inputs.legacy_text(passage)
        if l1_text:
            return {'kind': 'passage', 'passage': _served_passage(passage, l1_text), 'untaken': True}

    # 4. A new window of a test not attempted yet, nearest the learner's level.
    untaken_tests = inputs.untaken_tests(only)
    window = _first_window(inputs, untaken_tests, l2, blocked)
    if window:
        return {'kind': 'range', **window, 'untaken': True}

    # 5. Served before, never graded: least recently served first.
    ungraded = [pid for pid, h in history.items() if not h['graded']]
    ungraded.sort(key=lambda pid: history[pid]['last_served'])
    hit = _first_servable(inputs, ungraded, l2, in_scope)
    if hit:
        return hit[0]

    graded = [pid for pid, h in history.items() if h['graded']
              and int((inputs.passages.get(pid) or {}).get('l2_language_id') or 0) == l2
              and in_scope((inputs.passages.get(pid) or {}).get('source_ref_id'))]

    # 6. TASK-989: re-serve on request, least recently graded first.
    if reserve and graded:
        graded.sort(key=lambda pid: (history[pid].get('last_graded_at') or '', pid))
        hit = _first_servable(inputs, graded, l2, in_scope)
        if hit:
            choice, pid = hit
            choice['repeat_of'] = {'graded_at': history[pid].get('last_graded_at'),
                                   'band': history[pid].get('band')}
            return choice

    # "All done" only when the learner has had a passage of THIS language
    # graded; graded work in another language says nothing about this one,
    # which then simply has nothing eligible (NO_PASSAGES).
    return {'kind': 'none', 'all_done': bool(graded)}


def _first_window(inputs: '_NextInputs', tests: list, l2: int, blocked: dict) -> Optional[dict]:
    """The first fresh window over ``tests`` (in order), reading their
    materials a batch at a time and stopping at the first batch with one."""
    for i in range(0, len(tests), _WINDOW_TEST_BATCH):
        batch = tests[i:i + _WINDOW_TEST_BATCH]
        materials = inputs.materials(batch)
        window = _next_sentence_window(batch, materials, l2, _merge_ranges(blocked, inputs.retired_ranges()))
        if window:
            return window
    return None


def _merge_ranges(a: dict, b: dict) -> dict:
    out = {k: set(v) for k, v in a.items()}
    for k, v in b.items():
        out.setdefault(k, set()).update(v)
    return out


def _first_servable(inputs: '_NextInputs', passage_ids: list, l2: int, in_scope) -> Optional[tuple]:
    """The first of ``passage_ids`` (already ordered) that can be served again:
    active, in this language and scope, and either a legacy passage with an L1
    reference or a window whose sentences all still have usable references.
    Returns ``(choice, passage_id)``."""
    for pid in passage_ids:
        passage = inputs.passages.get(pid)
        if not passage or passage.get('status') != 'active':
            continue
        if int(passage.get('l2_language_id') or 0) != l2 or not in_scope(passage.get('source_ref_id')):
            continue
        untaken = str(passage.get('source_ref_id')) not in inputs.attempted
        if passage.get('sentence_start') is not None and passage.get('sentence_end') is not None:
            test = inputs.test_meta(passage.get('source_ref_id'))
            if not test:
                continue
            materials = inputs.materials([test])
            if _range_still_servable(passage, materials):
                out = {'kind': 'range', 'test_id': str(passage['source_ref_id']),
                       'start': int(passage['sentence_start']), 'end': int(passage['sentence_end'])}
                if untaken:
                    out['untaken'] = True
                return out, pid
            continue
        l1_text = inputs.legacy_text(passage)
        if l1_text:
            out = {'kind': 'passage', 'passage': _served_passage(passage, l1_text)}
            if untaken:
                out['untaken'] = True
            return out, pid
    return None


# ----------------------------------------------------------------------------
# GET /next read bundle (TASK-990)
# ----------------------------------------------------------------------------

# How long the per-table reads are used without retrying the bundle after it
# was found missing (migrations/dt_next_inputs.sql not applied) or failing.
_NEXT_INPUTS_RETRY_S = 600
_next_inputs_state = {'unavailable_until': 0.0, 'logged': False}


class _NextInputs:
    """Everything ``_choose_next`` reads, behind one interface. Two sources:
    ``_RpcInputs`` (one call to ``dt_next_inputs``) and ``_TableInputs`` (the
    per-table reads, used before that migration is applied, when it fails, and
    by the unit tests' filtering fake DB).

    Attributes: ``l1``, ``l2`` (resolved), ``salt`` (passages ever served),
    ``attempted`` (set of attempted test ids, as str), ``history``
    (``{passage_id: {last_served, graded, last_graded_at, band, open_id}}``)
    and ``passages`` (``{passage_id: dt_passage row without text}`` for every
    served passage)."""

    source = 'none'
    # Tests examined per call (None: all). The per-table path caps it to bound
    # its reads; the bundle has every candidate's materials already.
    max_tests: Optional[int] = None
    l1: int
    l2: Optional[int]
    salt: int
    attempted: set
    history: dict
    passages: dict

    # -- overridden ---------------------------------------------------------
    def legacy_passages(self) -> list:
        raise NotImplementedError

    def legacy_text(self, passage: dict) -> Optional[str]:
        raise NotImplementedError

    def candidate_tests(self, attempted: bool) -> list:
        """Active tests in l2 (``{id, language_id, transcript_hash, difficulty,
        elo}``) that were (not) attempted, unordered."""
        raise NotImplementedError

    def materials(self, tests: list) -> dict:
        raise NotImplementedError

    def range_passage(self, test_id: str, start: int, end: int) -> Optional[dict]:
        raise NotImplementedError

    def window_texts(self, db, sentence_ids: list) -> dict:
        """``{sentence_id: (l2_text, l1_text)}``."""
        return _read_window_texts(db, sentence_ids, self.l1)

    # -- shared -------------------------------------------------------------
    def taken_tests(self, only: Optional[str] = None) -> list:
        """Attempted candidate tests (only ``only`` when given), in rotation
        order, capped at ``max_tests``."""
        tests = sorted((t for t in self.candidate_tests(True) if only is None or str(t['id']) == only),
                       key=lambda t: _rotation_key(self.user_id, t['id'], self.salt))
        return tests[:self.max_tests] if self.max_tests else tests

    def untaken_tests(self, only: Optional[str] = None) -> list:
        """Not-attempted candidate tests (only ``only`` when given), nearest the
        learner's level first (ELO distance; unrated last), then rotation
        order; capped at ``max_tests``."""
        level = self.level_order()
        tests = sorted((t for t in self.candidate_tests(False) if only is None or str(t['id']) == only),
                       key=lambda t: (*level(t['id']), _rotation_key(self.user_id, t['id'], self.salt)))
        return tests[:self.max_tests] if self.max_tests else tests

    def level_order(self):
        """``test_id -> (unrated, elo distance)``: a sort key, nearest first."""
        elo = {str(t['id']): t.get('elo') for t in self.candidate_tests(False)}

        def key(test_id):
            d = elo.get(str(test_id))
            return (d is None, float(d) if d is not None else 0.0)
        return key

    def test_meta(self, test_id) -> Optional[dict]:
        for t in self.candidate_tests(True) + self.candidate_tests(False):
            if str(t['id']) == str(test_id):
                return t
        return None

    def retired_ranges(self) -> dict:
        """``{test_id: set(idx)}`` of known range passages that are not active."""
        return _served_ranges([p for p in self._known_ranges().values() if p.get('status') != 'active'])

    def _known_ranges(self) -> dict:
        return {}


class _RpcInputs(_NextInputs):
    source = 'rpc'

    def __init__(self, user_id: str, data: dict):
        self.user_id = user_id
        self.l1 = int(data.get('l1') or DEFAULT_L1_LANGUAGE_ID)
        self.l2 = int(data['l2']) if data.get('l2') is not None else None
        self.salt = int(data.get('salt') or 0)
        self.attempted = {str(t) for t in (data.get('attempted') or [])}
        self.history, self.passages = {}, {}
        for h in data.get('history') or []:
            pid = h['p']
            self.history[pid] = {
                'last_served': str(h.get('ls') or ''), 'graded': bool(h.get('g')),
                'last_graded_at': h.get('lg'), 'band': h.get('b'), 'open_id': h.get('o'),
            }
            self.passages[pid] = {
                'id': pid, 'age_tier': h.get('a'), 'l2_language_id': h.get('l2'),
                'status': h.get('st'), 'source_ref_id': h.get('t'),
                'sentence_start': h.get('s'), 'sentence_end': h.get('e'),
            }
        self._legacy = [
            {'id': r['id'], 'age_tier': r.get('a'), 'l2_language_id': self.l2,
             'source_ref_id': r.get('t'), 'sentence_start': None, 'status': 'active',
             'l1_text': r.get('x')}
            for r in (data.get('legacy') or [])
        ]
        self._legacy_by_id = {p['id']: p for p in self._legacy}
        self._tests = {True: [], False: []}
        self._materials: dict = {}
        for t in data.get('tests') or []:
            meta = {'id': str(t['id']), 'language_id': self.l2, 'transcript_hash': t.get('h'),
                    'difficulty': t.get('d'), 'elo': t.get('elo')}
            self._tests[bool(t.get('at'))].append(meta)
            self._materials[meta['id']] = _materials_from_rows(meta['id'], t.get('rows') or [])
        self._ranges = {
            (str(r['t']), int(r['s']), int(r['e'])): {
                'id': r['id'], 'age_tier': r.get('a'), 'l2_language_id': self.l2,
                'status': r.get('st'), 'source_ref_id': str(r['t']),
                'sentence_start': r['s'], 'sentence_end': r['e'],
            }
            for r in (data.get('ranges') or [])
        }
        self._texts = {int(x[0]): (x[1], x[2]) for x in (data.get('texts') or [])}

    def legacy_passages(self) -> list:
        return self._legacy

    def legacy_text(self, passage: dict) -> Optional[str]:
        hit = self._legacy_by_id.get(passage['id'])
        return hit.get('l1_text') if hit else None

    def candidate_tests(self, attempted: bool) -> list:
        return self._tests[bool(attempted)]

    def materials(self, tests: list) -> dict:
        return {str(t['id']): self._materials[str(t['id'])]
                for t in tests if str(t['id']) in self._materials}

    def range_passage(self, test_id: str, start: int, end: int) -> Optional[dict]:
        return self._ranges.get((str(test_id), int(start), int(end)))

    def window_texts(self, db, sentence_ids: list) -> dict:
        if all(int(i) in self._texts for i in sentence_ids):
            return {int(i): self._texts[int(i)] for i in sentence_ids}
        return super().window_texts(db, sentence_ids)

    def _known_ranges(self) -> dict:
        return self._ranges


def _materials_from_rows(test_id: str, rows: list) -> tuple:
    """``dt_next_inputs`` sentence rows -> the ``_window_materials`` tuple
    ``(rows, refs_ok, tightness)``. A stale row (``fresh`` false) and a gap
    in idx stay in the list as window breakers, exactly as there."""
    out_rows, refs_ok, tightness = [], set(), {}
    for sid, idx, fresh, ref_ok, tight, chars in rows:
        idx = int(idx)
        out_rows.append({'id': sid, 'test_id': test_id, 'idx': idx,
                         'char_start': 0, 'char_end': int(chars or 0)})
        if fresh and ref_ok:
            refs_ok.add(idx)
            if tight is not None:
                tightness[idx] = float(tight)
    present = {r['idx'] for r in out_rows}
    if present:
        out_rows += [{'id': None, 'test_id': test_id, 'idx': i, 'l2_text': ''}
                     for i in range(min(present), max(present) + 1) if i not in present]
    out_rows.sort(key=lambda r: r['idx'])
    return out_rows, refs_ok, tightness


class _TableInputs(_NextInputs):
    """The per-table reads (the pre-TASK-990 path), lazily: tests not
    attempted, their ratings and materials are only read when the attempted
    tests have nothing left."""
    source = 'tables'
    max_tests = MAX_WINDOW_TESTS_PER_CALL

    def __init__(self, db, user_id: str, l1: Optional[int], l2: Optional[int],
                 attempts: Optional[list] = None):
        self.db, self.user_id = db, user_id
        attempts = _attempted_tests(db, user_id) if attempts is None else attempts
        self.l2 = int(l2) if l2 is not None else _latest_attempt_language(attempts)
        self.l1 = int(l1) if l1 is not None else _resolve_l1_language_id(db, user_id)
        self.attempted = {str(r['test_id']) for r in attempts if r.get('test_id')}
        self.history = _served_history(db, user_id, self.l1)
        self.salt = len(self.history)
        self.passages = {p['id']: p for p in _passages_by_id(db, list(self.history))}
        self._legacy = None
        self._tests: dict = {}
        self._materials: dict = {}
        self._ranges: dict = {}
        self._ranges_read: set = set()

    def legacy_passages(self) -> list:
        if self._legacy is None:
            rows = (
                self.db.table('dt_passage')
                .select('id, age_tier, l2_language_id, source_ref_id, sentence_start, status')
                .eq('source_kind', 'test_transcript')
                .eq('status', 'active')
                .eq('l2_language_id', self.l2)
                .execute()
            ).data or []
            self._legacy = [p for p in rows if p.get('sentence_start') is None]
        return self._legacy

    def legacy_text(self, passage: dict) -> Optional[str]:
        return _legacy_reference(self.db, passage['id'], self.l1)

    def candidate_tests(self, attempted: bool) -> list:
        key = bool(attempted)
        if key not in self._tests:
            if key:
                ids = sorted(self.attempted)
                tests = []
                for i in range(0, len(ids), 100):
                    tests += (
                        self.db.table('tests').select('id, language_id, difficulty, transcript_hash')
                        .in_('id', ids[i:i + 100]).eq('is_active', True).execute()
                    ).data or []
            else:
                tests = _read_all_pages(lambda: (
                    self.db.table('tests').select('id, language_id, difficulty, transcript_hash')
                    .eq('language_id', self.l2).eq('is_active', True).order('id')
                ))
                tests = [t for t in tests if str(t['id']) not in self.attempted]
                with_refs = _tests_with_references(self.db, self.l1)
                if with_refs is not None:
                    tests = [t for t in tests if str(t['id']) in with_refs]
                _attach_elo(self.db, self.user_id, self.l2, tests)
            self._tests[key] = [
                {**t, 'id': str(t['id'])} for t in tests
                if int(t.get('language_id') or 0) == int(self.l2)
            ]
        return self._tests[key]

    def materials(self, tests: list) -> dict:
        missing = [t for t in tests if str(t['id']) not in self._materials]
        if missing:
            self._materials.update(_window_materials(self.db, missing, self.l1))
            for t in missing:
                self._materials.setdefault(str(t['id']), ([], set(), {}))
            self._read_ranges([str(t['id']) for t in missing])
        return {str(t['id']): self._materials[str(t['id'])] for t in tests}

    def _read_ranges(self, test_ids: list) -> None:
        rows = (
            self.db.table('dt_passage')
            .select('id, age_tier, l2_language_id, status, source_ref_id, sentence_start, sentence_end')
            .in_('source_ref_id', test_ids).execute()
        ).data or []
        self._ranges_read.update(test_ids)
        for p in rows:
            if p.get('sentence_start') is not None and p.get('sentence_end') is not None:
                self._ranges[(str(p['source_ref_id']), int(p['sentence_start']), int(p['sentence_end']))] = p

    def range_passage(self, test_id: str, start: int, end: int) -> Optional[dict]:
        key = (str(test_id), int(start), int(end))
        if key not in self._ranges and str(test_id) not in self._ranges_read:
            hit = _select_range_passage(self.db, str(test_id), int(start), int(end))
            if hit:
                self._ranges[key] = hit
        return self._ranges.get(key)

    def _known_ranges(self) -> dict:
        return self._ranges


def _tests_with_references(db, l1: int) -> Optional[set]:
    """Ids of tests with at least one usable sentence reference in ``l1`` (the
    per-table path's filter for tests not attempted, which are otherwise every
    active test of the language). None when the embedded read is unavailable
    (no filter then)."""
    try:
        rows = _read_all_pages(lambda: (
            db.table('test_sentence_references').select('id, test_sentences(test_id)')
            .eq('l1_language_id', l1).eq('is_active', True)
            .in_('review_verdict', list(_USABLE_VERDICTS)).order('id')
        ))
    except Exception as e:
        logger.info("DT reference test lookup unavailable (%s); not filtering", e)
        return None
    out = set()
    for r in rows:
        emb = r.get('test_sentences')
        if isinstance(emb, list):
            emb = emb[0] if emb else None
        if not isinstance(emb, dict) or not emb.get('test_id'):
            return None
        out.add(str(emb['test_id']))
    return out


def _attach_elo(db, user_id: str, l2: int, tests: list) -> None:
    """``t['elo']`` = the get_recommended_tests distance: min over test types of
    |test ELO - learner ELO (1200 when unrated)|; None when the test is unrated."""
    try:
        mine = {
            int(r['test_type_id']): r.get('elo_rating')
            for r in (db.table('user_skill_ratings').select('test_type_id, elo_rating')
                      .eq('user_id', user_id).eq('language_id', l2).execute()).data or []
        }
        ids = [str(t['id']) for t in tests]
        best: dict = {}
        for i in range(0, len(ids), 200):
            for r in (db.table('test_skill_ratings').select('test_id, test_type_id, elo_rating')
                      .in_('test_id', ids[i:i + 200]).execute()).data or []:
                if r.get('elo_rating') is None:
                    continue
                d = abs(int(r['elo_rating']) - int(mine.get(int(r['test_type_id'])) or 1200))
                tid = str(r['test_id'])
                best[tid] = min(best.get(tid, d), d)
        for t in tests:
            t['elo'] = best.get(str(t['id']))
    except Exception as e:  # ordering only: never block serving
        logger.info("DT level ordering unavailable (%s); rotation order only", e)
        for t in tests:
            t.setdefault('elo', None)


def _next_inputs(db, user_id: str, l2_language_id: Optional[int]) -> _NextInputs:
    """The read bundle for GET /next: one ``dt_next_inputs`` call, or the
    per-table reads while that function is missing or failing (logged once per
    process, retried after ``_NEXT_INPUTS_RETRY_S``)."""
    if time.monotonic() >= _next_inputs_state['unavailable_until'] and hasattr(db, 'rpc'):
        try:
            data = db.rpc('dt_next_inputs', {
                'p_user_id': user_id, 'p_l2': l2_language_id, 'p_l1': None,
            }).execute().data
            if isinstance(data, list):  # some client versions wrap a scalar
                data = data[0] if data else None
            if isinstance(data, dict) and 'history' in data:
                return _RpcInputs(user_id, data)
            raise ValueError(f"unexpected dt_next_inputs answer: {type(data).__name__}")
        except Exception as e:
            _next_inputs_state['unavailable_until'] = time.monotonic() + _NEXT_INPUTS_RETRY_S
            if not _next_inputs_state['logged']:
                _next_inputs_state['logged'] = True
                logger.warning(
                    "dt_next_inputs unavailable (%s); GET /next uses the per-table reads. "
                    "Is migrations/dt_next_inputs.sql applied? Logged once per process.", e)
    return _TableInputs(db, user_id, None, l2_language_id)


def _read_window_texts(db, sentence_ids: list, l1_language_id: int) -> dict:
    """``{sentence_id: (l2_text, l1_text)}`` for a window's sentences: one read
    (the reference with its sentence embedded); a second read only when the
    embedding is unavailable."""
    ids = [int(i) for i in sentence_ids]
    rows = (
        db.table('test_sentence_references')
        .select('sentence_id, l1_text, test_sentences(l2_text)')
        .in_('sentence_id', ids)
        .eq('l1_language_id', l1_language_id)
        .eq('is_active', True)
        .in_('review_verdict', list(_USABLE_VERDICTS))
        .execute()
    ).data or []
    out = {}
    for r in rows:
        embedded = r.get('test_sentences')
        if isinstance(embedded, list):
            embedded = embedded[0] if embedded else None
        out[int(r['sentence_id'])] = ((embedded or {}).get('l2_text'), r.get('l1_text'))
    if any(v[0] is None for v in out.values()):
        l2 = {
            int(r['id']): r.get('l2_text') for r in (
                db.table('test_sentences').select('id, l2_text').in_('id', ids).execute()
            ).data or []
        }
        out = {k: (l2.get(k), v[1]) for k, v in out.items()}
    return out


def _serve_choice(db, user_id: str, inputs: _NextInputs, choice: dict) -> ApiResponse:
    """Open the chosen passage: find or create its dt_passage (a window), then
    reuse the learner's open submission on it (served, never started, same L1)
    or create one (TASK-991: skipping a passage no longer leaves one empty
    dt_submission row per GET /next). Common path: 1-2 writes."""
    l1 = inputs.l1
    extra = {'type': 'passage'}
    if choice.get('untaken'):
        extra['from_untaken_test'] = True
    if choice.get('repeat_of'):
        extra['repeat_of'] = choice['repeat_of']

    if choice['kind'] == 'passage':
        passage = choice['passage']
        l2_code = DimensionService.get_language_code(passage['l2_language_id'])
        submission_id = _open_or_create_submission(db, user_id, inputs, passage['passage_id'], l1)
        if submission_id is None:
            return server_error("Failed to create submission")
        return api_success({
            **extra,
            'source': 'passage',
            'passage_id': passage['passage_id'],
            'submission_id': submission_id,
            'l1_text': passage['l1_text'],
            'age_tier': passage['age_tier'],
            'rubric_descriptors': _rubric_descriptors_for(db, passage['age_tier'], l2_code),
            'correction_style': Config.resolve_correction_style(user_id),
        })

    test = inputs.test_meta(choice['test_id'])
    start, end = int(choice['start']), int(choice['end'])
    rows = {int(r['idx']): r for r in inputs.materials([test])[str(test['id'])][0]} if test else {}
    ids = [rows[i]['id'] for i in range(start, end + 1) if i in rows and rows[i].get('id')]
    if not test or len(ids) != end - start + 1:
        logger.warning("DT /next window %s %s-%s lost its sentence rows; nothing served", choice['test_id'], start, end)
        return api_error("No dual-translation passage available yet", 404, error_code=NO_PASSAGES)

    texts = inputs.window_texts(db, ids)
    if any(int(i) not in texts or not texts[int(i)][1] for i in ids):
        return api_error("No dual-translation passage available yet", 404, error_code=NO_PASSAGES)
    l2_code = _LANG_CODE.get(int(inputs.l2), 'en')
    l1_code = _LANG_CODE.get(int(l1), 'en')

    passage = inputs.range_passage(test['id'], start, end)
    if passage is None:
        passage = _find_or_create_range_passage(
            db, {**test, 'language_id': inputs.l2}, start, end,
            l2_text=join_sentences([texts[int(i)][0] or '' for i in ids], l2_code),
            known_absent=True,  # range_passage() just looked it up
        )
    if not passage:
        return server_error("Failed to create passage")
    if passage.get('status') not in (None, 'active'):
        # TASK-991: never open a retired window (submit would refuse it).
        return api_error("No dual-translation passage available yet", 404, error_code=NO_PASSAGES)

    submission_id = _open_or_create_submission(db, user_id, inputs, passage['id'], l1)
    if submission_id is None:
        return server_error("Failed to create submission")
    age_tier = passage.get('age_tier') or difficulty_to_age_tier(test.get('difficulty'))
    return api_success({
        **extra,
        'source': 'sentence_refs',
        'passage_id': passage['id'],
        'l1_text': join_sentences([texts[int(i)][1] for i in ids], l1_code),
        'n_sentences': end - start + 1,
        'submission_id': submission_id,
        'age_tier': age_tier,
        'rubric_descriptors': _rubric_descriptors_for(db, age_tier, l2_code),
        'correction_style': Config.resolve_correction_style(user_id),
        'primed_token': primed_token.issue(user_id, passage['id'], []),
    })


def _open_or_create_submission(db, user_id: str, inputs: _NextInputs, passage_id: int,
                               l1_language_id: int) -> Optional[int]:
    open_id = (inputs.history.get(passage_id) or {}).get('open_id')
    if open_id:
        return int(open_id)
    resp = db.table('dt_submission').insert({
        'user_id': user_id,
        'passage_id': passage_id,
        'l1_language_id': l1_language_id,
        'reproduction': '',
        'correction_style': Config.resolve_correction_style(user_id),
    }).execute()
    return resp.data[0]['id'] if resp.data else None


def _passages_by_id(db, passage_ids: list) -> list:
    """dt_passage rows (no text) for these ids, read in chunks."""
    rows: list = []
    for i in range(0, len(passage_ids), 200):
        part = passage_ids[i:i + 200]
        rows += (
            db.table('dt_passage')
            .select('id, age_tier, l2_language_id, status, source_ref_id, sentence_start, sentence_end')
            .in_('id', part).execute()
        ).data or []
    return rows


def _served_ranges(served_passages: list) -> dict:
    """``{test_id: set(sentence idx)}`` covered by sentence-window passages this
    learner has been served (graded or not): new windows avoid them."""
    out: dict = {}
    for p in served_passages:
        start, end = p.get('sentence_start'), p.get('sentence_end')
        if start is None or end is None or not p.get('source_ref_id'):
            continue
        out.setdefault(str(p['source_ref_id']), set()).update(range(int(start), int(end) + 1))
    return out


# Tests per test_sentences read in the sentence-window search. Transcripts are
# a few dozen sentences, so a batch stays well under PostgREST's 1000-row cap;
# a batch that comes back with exactly the cap is re-read test by test.
_WINDOW_TEST_BATCH = 10
_POSTGREST_ROW_CAP = 1000


def _window_materials(db, tests: list, l1_language_id: int) -> dict:
    """``{test_id: (rows, refs_ok, tightness)}`` for the sentence-window
    selector, read in batches (a few queries for any number of tests): each
    test's sentence rows in index order (rows stale for the stored transcript,
    and placeholders for missing indices, are kept as window breakers but never
    count as referenced, as open_range_passage would refuse them), the indices
    with an active ``pass``/``rewritten`` reference in ``l1_language_id`` and
    their tightness."""
    out: dict = {}
    for i in range(0, len(tests), _WINDOW_TEST_BATCH):
        batch = tests[i:i + _WINDOW_TEST_BATCH]
        rows = (
            db.table('test_sentences')
            .select('id, test_id, idx, l2_text, token_start, token_end, transcript_hash')
            .in_('test_id', [str(t['id']) for t in batch]).order('idx').execute()
        ).data or []
        if len(rows) >= _POSTGREST_ROW_CAP:
            rows = []
            for t in batch:
                rows += (
                    db.table('test_sentences')
                    .select('id, test_id, idx, l2_text, token_start, token_end, transcript_hash')
                    .eq('test_id', str(t['id'])).order('idx').execute()
                ).data or []
        by_test: dict = {}
        for r in rows:
            by_test.setdefault(str(r['test_id']), []).append(r)
        by_id: dict = {}
        for t in batch:
            test_rows = by_test.get(str(t['id']), [])
            stored_hash = t.get('transcript_hash')
            # Stale rows (and placeholders for missing indices) stay in the
            # list but never get a usable reference: select_window_for_primed
            # walks list positions, so dropping a row would let a window
            # straddle it and name a range open_range_passage then refuses
            # (409 SENTENCES_STALE / 422 SENTENCES_MISSING). Same rule as
            # services.prestudy.choose_produce_window.
            for r in test_rows:
                if not stored_hash or r.get('transcript_hash') == stored_hash:
                    by_id[r['id']] = r
            present = {int(r['idx']) for r in test_rows}
            if present:
                test_rows = test_rows + [
                    {'id': None, 'test_id': str(t['id']), 'idx': i, 'l2_text': ''}
                    for i in range(min(present), max(present) + 1) if i not in present
                ]
            test_rows.sort(key=lambda r: int(r['idx']))
            out[str(t['id'])] = (test_rows, set(), {})
        ids = list(by_id)
        for j in range(0, len(ids), 200):
            refs = _get_usable_references(db, ids[j:j + 200], l1_language_id)
            for sentence_id, ref in refs.items():
                row = by_id.get(sentence_id)
                if not row:
                    continue
                _, refs_ok, tightness = out[str(row['test_id'])]
                refs_ok.add(int(row['idx']))
                if ref.get('tightness') is not None:
                    tightness[int(row['idx'])] = float(ref['tightness'])
    return out


def _tightness_floor(l2_language_id: int) -> float:
    """The Produce stage's per-language reference-tightness floor (the same
    quality bar for every sentence-window passage)."""
    from services.prestudy import PRODUCE_TIGHTNESS_FLOOR
    return PRODUCE_TIGHTNESS_FLOOR.get(int(l2_language_id), 0.6)


def _next_sentence_window(tests: list, materials: dict, l2_language_id: int,
                          served_ranges: dict) -> Optional[dict]:
    """The first fresh 2-4 sentence window over ``tests`` (already in rotation
    order): every sentence has a usable L1 reference, the mean tightness clears
    the language floor, and no sentence belongs to a window this learner was
    already served. Window choice is ``select_window_for_primed`` with no
    primed words (the shortest eligible window, then the earliest)."""
    from services.dual_translation.passage_builder import select_window_for_primed

    floor = _tightness_floor(l2_language_id)
    for test in tests:
        rows, refs_ok, tightness = materials.get(str(test['id']), ([], set(), {}))
        if not rows:
            continue
        free = refs_ok - served_ranges.get(str(test['id']), set())
        window = select_window_for_primed(rows, [], [], free, tightness, floor)
        if window:
            return {'test_id': str(test['id']), 'start': int(window[0]), 'end': int(window[1])}
    return None


def _range_still_servable(passage: dict, materials: dict) -> bool:
    """A served-but-ungraded window passage can be re-opened only while its
    test is an eligible active test (present in ``materials``) and every
    sentence still has a usable reference."""
    material = materials.get(str(passage['source_ref_id']))
    if not material:
        return False
    rows, refs_ok, _ = material
    want = set(range(int(passage['sentence_start']), int(passage['sentence_end']) + 1))
    have = {int(r['idx']) for r in rows}
    return want <= have and want <= refs_ok


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
    """Today's (UTC) DT token spend for the TASK-601 guardrail: grades
    (dt_grade.grader_trace tokens of today's submissions) plus guided-repair
    re-checks (dt_repair_event), so first grades see re-check spend. The logic
    lives in services.dual_translation.repair.budget; re-check tokens read as 0
    when the repair tables are missing."""
    return repair_budget.grade_tokens_today(db, user_id) + repair_budget.recheck_tokens_today(db, user_id)


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
        .select('id, l2_text, l2_language_id, age_tier, status, source_ref_id, sentence_start, sentence_end')
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
    repeat = (grade.get('grader_trace') or {}).get('repeat')
    if isinstance(repeat, dict):
        errors = [dict(e) for e in (repeat.get('errors') or [])]
        for row in errors:
            if row.get('explanation_source') == 'model' and row.get('model_note'):
                row['explanation_parts'] = {'rule': row.get('explanation') or '',
                                            'application': row['model_note']}
    else:
        errors = _read_error_rows(db, submission_id)
    out = {
        'scores': grade['scores'],
        'overall_band': grade['overall_band'],
        'diff': grade['diff'],
        'errors': errors,
        'grader_trace': ({k: v for k, v in grade['grader_trace'].items() if k != 'repeat'}
                         if isinstance(repeat, dict) else grade['grader_trace']),
        # TASK-628: surface the persisted provisional flag so a cached provisional
        # grade (a single-tier failure that still had evidence) keeps showing the
        # retry notice. Absent on v1/tier0 grader_trace -> defaults False.
        'provisional': (grade['grader_trace'] or {}).get('provisional', False),
    }
    if isinstance(repeat, dict):
        out['repeat_of'] = _public_repeat(repeat)
    return out


def _read_error_rows(db, submission_id: int) -> list:
    """The stored dt_error_instance rows of one submission, in the contract shape.

    ADR-044: a single-call grade shows the model's own explanation as the
    Application layer (`explanation_parts.application`), which is stored in
    `model_note` with `explanation_source = 'model'`, while `explanation` stays
    the Rule template. Rebuild `explanation_parts` for those rows so a reloaded
    grade shows the learner the same two layers as the fresh one. Reading the
    grading-asset columns degrades like writing them does (see
    `_asset_columns_usable`): if the select fails with them, it is retried
    without them and the grade is still served."""
    def _select(columns):
        return (
            db.table('dt_error_instance')
            .select(', '.join(columns))
            .eq('submission_id', submission_id)
            .execute()
        ).data or []

    columns = _error_columns()
    if not _names_asset_columns(columns):
        return _select(columns)
    try:
        rows = _select(columns)
    except Exception as e:
        _asset_columns_failed('read dt_error_instance', e)
        return _select(_error_columns(with_assets=False))
    for row in rows:
        if row.get('explanation_source') == 'model' and row.get('model_note'):
            row['explanation_parts'] = {
                'rule': row.get('explanation') or '', 'application': row['model_note'],
            }
    return rows


# The dt_error_instance columns a cascade error dict may carry into the insert.
# The insert is column-whitelisted (not `{**error}`) because the v2 contract's
# errors now also carry response-only fields that are NOT columns — e.g.
# `explanation_parts` (TASK-630 §6c: the concatenated `explanation` string is
# persisted, its {rule, application} breakdown is returned but not stored). Mirrors
# the select list `_cached_grade` reads back.
_ERROR_INSERT_COLUMNS = (
    'span_reproduction', 'span_reference', 'category', 'subtype', 'source',
    'severity', 'learner_form', 'corrected_form', 'explanation', 'confidence',
    'is_mistake', 'taxonomy_version', 'explanation_variant',
    'sentence_index', 'model_severity', 'model_note', 'span_source', 'correction_source',
    'confidence_label', 'explanation_source',
)

# TASK-842: columns added by migrations/dt_taxonomy_v6_columns.sql. Read and
# written only while Config.DT_TAXONOMY_COLUMNS is on — before that migration is
# applied, PostgREST rejects any insert/select naming them.
_TAXONOMY_ERROR_COLUMNS = ('taxonomy_version', 'explanation_variant')


# ADR-044: columns added by migrations/dt_grading_assets.sql (per-error grader
# fields the single-call flow emits). Read and written only while
# Config.DT_GRADING_ASSET_COLUMNS is on (the default since 2026-11-14) AND they
# have not just been found missing (`_asset_columns_usable`). Errors from the
# v1/v2 flows simply do not carry these keys (`_error_row` copies only what is
# present), so their rows keep NULLs.
_GRADING_ASSET_ERROR_COLUMNS = (
    'sentence_index', 'model_severity', 'model_note', 'span_source', 'correction_source',
    'confidence_label', 'explanation_source',
)

# Graceful degradation for DT_GRADING_ASSET_COLUMNS=True on a database where
# migrations/dt_grading_assets.sql is missing (or half-applied): PostgREST
# rejects an insert/select naming a column that does not exist, and that must
# never cost a learner their grade. When a statement that names the asset
# columns fails, it is retried once WITHOUT them; if that works the columns are
# treated as unavailable for _ASSET_COLUMN_RETRY_S (so every later submission
# skips the doomed first attempt), the problem is logged ONCE per process, and
# the grade is saved with the columns the table does have. After the pause the
# columns are probed again, so applying the migration needs no restart.
_ASSET_COLUMN_RETRY_S = 600
_asset_columns_state = {'unavailable_until': 0.0, 'logged': False}


def _asset_columns_usable() -> bool:
    return (Config.DT_GRADING_ASSET_COLUMNS
            and time.monotonic() >= _asset_columns_state['unavailable_until'])


def _asset_columns_failed(what: str, error: Exception) -> None:
    """Record that a statement naming the grading-asset columns failed."""
    _asset_columns_state['unavailable_until'] = time.monotonic() + _ASSET_COLUMN_RETRY_S
    if not _asset_columns_state['logged']:
        _asset_columns_state['logged'] = True
        logger.error(
            "DT grading-asset columns unavailable (%s failed: %s). Is "
            "migrations/dt_grading_assets.sql applied? Grades are still saved, without "
            "the per-error grader fields and without dt_grading_call rows; retrying every "
            "%d s. Logged once per process.", what, error, _ASSET_COLUMN_RETRY_S,
        )


def _names_asset_columns(columns: tuple) -> bool:
    return any(c in _GRADING_ASSET_ERROR_COLUMNS for c in columns)


# The dt_grading_call columns a grading-asset record may carry into the insert
# (services.dual_translation.single_call_grader._asset_record).
_GRADING_CALL_COLUMNS = (
    'flow', 'role', 'model_slug', 'provider', 'prompt_version', 'prompt_variant',
    'severity_rule', 'l2_code', 'status', 'error', 'finish_reason', 'tokens_in',
    'tokens_out', 'cached_tokens', 'reasoning_tokens', 'cost_usd', 'latency_ms',
    'taxonomy_version', 'rubric_version', 'response', 'errors_raw', 'errors_kept',
    'dropped', 'result', 'raw_response', 'raw_truncated',
)


def _error_columns(with_assets: bool = True) -> tuple:
    """The dt_error_instance columns to insert and to read back right now.
    `with_assets=False` leaves the grading-asset columns out regardless of the
    flag (the degraded retry)."""
    skip: tuple = ()
    if not Config.DT_TAXONOMY_COLUMNS:
        skip += _TAXONOMY_ERROR_COLUMNS
    if not (with_assets and _asset_columns_usable()):
        skip += _GRADING_ASSET_ERROR_COLUMNS
    return tuple(c for c in _ERROR_INSERT_COLUMNS if c not in skip)


def _error_row(error: dict, submission_id: int, columns: tuple) -> dict:
    row = {k: error[k] for k in columns if k in error}
    # dt_error_instance_explanation_variant_check ties the variant to
    # word_choice. A variant left on a re-typed error would fail the whole
    # insert (and, by design, leave the submission ungraded) — drop it instead.
    if row.get('explanation_variant') is not None and row.get('subtype') != 'word_choice':
        row['explanation_variant'] = None
    row['submission_id'] = submission_id
    return row


def _persist_grade(
    db, submission_id: int, reproduction: str, idempotency_key: Optional[str], contract: dict,
    repeat_of: Optional[dict] = None,
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
    reverse order.

    TASK-989: for a repeat (``repeat_of``: the learner's earlier grade of the same
    passage) the error rows are NOT written to dt_error_instance — every
    aggregate built on that table (nightly error synthesis and its recurrence
    trend, error cards, guided-repair items) would otherwise count one passage's
    errors twice, and a second try after seeing the gold measures recall of the
    correction, not the learner's level. They are kept, column-whitelisted, in
    ``grader_trace.repeat`` with the earlier grade, so the cached grade still
    shows them."""
    db.table('dt_submission').update({
        'reproduction': reproduction,
        'idempotency_key': idempotency_key,
    }).eq('id', submission_id).execute()

    trace = contract['grader_trace']
    if repeat_of:
        columns = _error_columns(with_assets=True)
        trace = {**(trace or {}), 'repeat': {
            **_public_repeat(repeat_of),
            'errors': [{k: v for k, v in _error_row(e, submission_id, columns).items()
                        if k != 'submission_id'} for e in (contract['errors'] or [])],
        }}
    elif contract['errors']:
        columns = _error_columns()
        rows = [_error_row(error, submission_id, columns) for error in contract['errors']]
        if not _names_asset_columns(columns):
            db.table('dt_error_instance').insert(rows).execute()
        else:
            # ADR-044: the grading-asset columns are extras. If the insert fails
            # with them, retry without them; only a failure of the plain insert
            # (the pre-ADR-044 statement) propagates and leaves the submission
            # ungraded, exactly as before.
            try:
                db.table('dt_error_instance').insert(rows).execute()
            except Exception as e:
                plain = _error_columns(with_assets=False)
                rows = [_error_row(error, submission_id, plain) for error in contract['errors']]
                db.table('dt_error_instance').insert(rows).execute()
                _asset_columns_failed('insert into dt_error_instance', e)

    db.table('dt_grade').insert({
        'submission_id': submission_id,
        'scores': contract['scores'],
        'overall_band': contract['overall_band'],
        'diff': contract['diff'],
        'grader_trace': trace,
    }).execute()


def _repeat_of(db, user_id: str, submission_row: dict) -> Optional[dict]:
    """The learner's latest earlier grade of this submission's passage
    (``{of_submission_id, graded_at, band}``), or None when this is the first
    graded attempt. Two reads; a read failure counts as not a repeat (the grade
    is then aggregated like any other, which is the pre-TASK-989 behaviour)."""
    try:
        others = [
            r['id'] for r in (
                db.table('dt_submission').select('id')
                .eq('user_id', user_id).eq('passage_id', submission_row['passage_id'])
                .execute()
            ).data or []
            if r.get('id') != submission_row['id']
        ]
        if not others:
            return None
        grades = (
            db.table('dt_grade').select('submission_id, created_at, overall_band')
            .in_('submission_id', others[-500:]).execute()
        ).data or []
    except Exception as e:
        logger.warning("DT repeat check failed (treated as first attempt): %s", e)
        return None
    if not grades:
        return None
    latest = max(grades, key=lambda r: (str(r.get('created_at') or ''), r['submission_id']))
    return {'of_submission_id': latest['submission_id'], 'graded_at': latest.get('created_at'),
            'band': latest.get('overall_band')}


def _public_repeat(repeat_of: dict) -> dict:
    return {k: repeat_of.get(k) for k in ('of_submission_id', 'graded_at', 'band')}


def _persist_grading_assets(db, submission_id: int, assets: Optional[list]) -> None:
    """Write the grader's per-model-call records to dt_grading_call (ADR-044).

    Best-effort and deliberately AFTER ``_persist_grade``: these rows are design
    and audit material, never something a learner's grade may depend on, so a
    failure here is logged and swallowed. A no-op when the grade carried no
    records (v1/v2/tier0 grades), while Config.DT_GRADING_ASSET_COLUMNS is off, or
    while the asset columns were just found missing (`_asset_columns_usable`) —
    the grader_trace stored on dt_grade still names the model, prompt version,
    usage and cost."""
    if not assets or not _asset_columns_usable():
        return
    try:
        rows = []
        for asset in assets:
            row = {k: asset[k] for k in _GRADING_CALL_COLUMNS if k in asset}
            row['submission_id'] = submission_id
            rows.append(row)
        db.table('dt_grading_call').insert(rows).execute()
    except Exception as e:
        logger.warning("Could not store grading assets for submission %s: %s", submission_id, e)
        if _looks_like_missing_relation(e):
            _asset_columns_failed('insert into dt_grading_call', e)


def _looks_like_missing_relation(error: Exception) -> bool:
    """True for PostgREST/Postgres "no such table / column" errors (PGRST204,
    PGRST205, 42P01, 42703) — as opposed to a transient failure."""
    text = f"{getattr(error, 'code', '')} {error}"
    return any(code in text for code in ('PGRST204', 'PGRST205', '42P01', '42703'))


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


def _next_due_error_card(db, user_id: str, l2_language_id: Optional[int] = None) -> Optional[dict]:
    """One due error card (subtype-interleaved), materialising cards for any
    newly-``queued`` profile entries first. ``None`` if nothing is due. With
    ``l2_language_id`` only cards whose profile entry is in that study language
    qualify (GET /next serves one language)."""
    dt_cards.generate_cards_for_queued_entries(db, user_id)
    due = _fetch_due_cards(db, user_id)
    if due and l2_language_id is not None:
        allowed = _card_ids_for_language(db, user_id, l2_language_id)
        due = [c for c in due if c['card_id'] in allowed]
    if not due:
        return None
    return dt_cards.interleave_by_subtype(due)[0]


def _card_ids_for_language(db, user_id: str, l2_language_id: int) -> set:
    """Ids of this user's dt_card rows whose profile entry is in ``l2_language_id``."""
    entries = (
        db.table('dt_error_profile_entry').select('id')
        .eq('user_id', user_id).eq('l2_language_id', l2_language_id).execute()
    ).data or []
    entry_ids = [e['id'] for e in entries]
    if not entry_ids:
        return set()
    cards = (
        db.table('dt_card').select('id')
        .eq('user_id', user_id).in_('profile_entry_id', entry_ids).execute()
    ).data or []
    return {c['id'] for c in cards}


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


def _credit_card_review_time(db, card_row: dict, data: dict) -> None:
    """Weekly minutes: credit an error-card review (kind dual_translation).

    Needs a valid ``client_event_id`` and ``active_ms > 0``. The card has no
    language column, so the language is the profile entry's L2; a card with no
    resolvable language earns nothing. Never raises.
    """
    try:
        event_id = parse_client_event_id(data.get('client_event_id'))
        seconds = clamp_active_ms('dual_translation', data.get('active_ms'))
        # Per-card reviews are short; cap at the flashcard-style 120 s.
        seconds = min(seconds, DT_CARD_REVIEW_MAX_SECONDS)
        if not event_id or seconds <= 0 or not card_row.get('profile_entry_id'):
            return
        resp = (
            db.table('dt_error_profile_entry')
            .select('l2_language_id')
            .eq('id', card_row['profile_entry_id'])
            .limit(1)
            .execute()
        )
        if not resp.data or not resp.data[0].get('l2_language_id'):
            return
        credit_study_time(
            db, card_row['user_id'], resp.data[0]['l2_language_id'],
            'dual_translation', seconds, 'dt_card_review', event_id,
        )
    except Exception as e:
        logger.warning("dt card review credit skipped (non-fatal): %s", e)


def _get_card(db, card_id: int) -> Optional[dict]:
    resp = (
        db.table('dt_card')
        .select('id, user_id, profile_entry_id, stability, difficulty, due_date, last_review, reps, lapses, state')
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
