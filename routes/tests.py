# routes/tests.py
"""Test routes - handles test CRUD, generation, and submission."""

from flask import Blueprint, request, current_app, g
from functools import wraps
from uuid import uuid4
import traceback
import logging

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from services.ai_service import ModerationServiceError
from services import attempts
from services.attempt_timing import AttemptTimingError, clamp_time_taken, validate_counts
from services.concurrency import run_parallel
from services.day_boundary import local_day_start_utc, plan_timezone
from services.dual_translation.sentence_refs import LANG_ID as SENTENCE_L1_IDS
from services.dictation.cap import MAX_STORED_DIFF_ENTRIES
from services.test_service import (
    TestService, DimensionService, NoMatchingAttemptError, get_test_service,
    parse_language_id, VALID_LANGUAGE_IDS,
    find_active_test, find_active_test_by_slug, get_test_content, get_test_skill_ratings,
)
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from utils.responses import (
    api_success, api_error, bad_request, not_found, server_error,
    service_unavailable, unauthorized, forbidden,
)

logger = logging.getLogger(__name__)
tests_bp = Blueprint("tests", __name__)


# ============================================================================
# HELPERS
# ============================================================================

def normalize_audio_url(test_data):
    """Ensure test_data['audio_url'] is a full URL, falling back to slug-based CDN URL."""
    audio_url = test_data.get('audio_url', '')
    if audio_url:
        if not audio_url.startswith('http'):
            slug_part = audio_url.replace('.mp3', '')
            test_data['audio_url'] = Config.get_audio_url(slug_part)
    else:
        test_data['audio_url'] = Config.get_audio_url(test_data.get('slug', ''))
    return test_data


# ============================================================================
# ROUTES
# ============================================================================

@tests_bp.route('/moderate', methods=['POST'])
@supabase_jwt_required
def moderate_content():
    """Check content using OpenAI moderation API via OpenAI service"""
    try:
        if not current_app.openai_service:
            return server_error("OpenAI service not available")

        data = request.get_json(silent=True) or {}
        content = data.get('content', '').strip()

        if not content:
            return bad_request("No content provided")

        try:
            moderation_result = current_app.openai_service.moderate_content(content)
        except ModerationServiceError as e:
            # CR-03: moderation service unavailable. Fail closed by returning
            # 503 — DO NOT record a flagged_input audit row (would be a false
            # positive against the user).
            logger.error("Moderation service unavailable: %s", e)
            return service_unavailable("moderation_unavailable")

        is_safe = moderation_result['is_safe']

        if not is_safe:
            current_user_email = g.supabase_claims.get('email')
            test_service = get_test_service()
            test_service.record_flagged_input(
                current_user_email,
                content,
                moderation_result.get('flagged_categories', [])
            )

        return api_success(data={
            "is_safe": is_safe,
            "flagged_categories": moderation_result.get('flagged_categories', []),
        })

    except Exception as e:
        logger.error(f"Moderation endpoint error: {e}")
        return server_error(f"Moderation failed: {str(e)}")

@tests_bp.route('/random', methods=['GET'])
@supabase_jwt_required
def get_random_test():
    user_id = g.current_user_id
    language_id_param = request.args.get('language_id')

    # Parse and validate language_id
    language_id = parse_language_id(language_id_param)
    if not language_id:
        return bad_request("Invalid or missing language_id parameter")

    # Call the get_recommended_test RPC which handles ELO matching
    result = current_app.supabase_service.rpc('get_recommended_test', {
        'p_user_id': user_id,
        'p_language_id': language_id
    }).execute()

    test = result.data[0] if result.data else None
    if not test:
        return not_found("No tests available at your level")

    return api_success(data={"test": test})


@tests_bp.route('/recommended', methods=['GET'])
@supabase_jwt_required
def get_recommended_tests():
    """Get recommended tests based on user's ELO ratings."""
    user_id = g.current_user_id
    language_id_param = request.args.get('language_id')

    language_id = parse_language_id(language_id_param)
    if not language_id:
        return bad_request("Invalid or missing language_id")

    try:
        result = current_app.supabase_service.rpc('get_recommended_tests', {
            'p_user_id': user_id,
            'p_language_id': language_id
        }).execute()

        return api_success(data={"recommended_tests": result.data or []})
    except Exception as e:
        logger.error(f"Error fetching recommended tests: {e}")
        return server_error("Failed to fetch recommended tests")


@tests_bp.route('/daily-load', methods=['GET'])
@supabase_jwt_required
def get_daily_load():
    """Get or compute today's daily test load for the user."""
    user_id = g.current_user_id
    language_id_param = request.args.get('language_id')

    language_id = parse_language_id(language_id_param)
    if not language_id:
        return bad_request("Invalid or missing language_id")

    try:
        test_service = get_test_service()
        daily_load = test_service.get_or_create_daily_load(user_id, language_id)

        return api_success(data={"daily_load": daily_load})
    except Exception as e:
        logger.error(f"Error fetching daily load: {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to fetch daily load")


@tests_bp.route('/daily-load/complete', methods=['POST'])
@supabase_jwt_required
def complete_daily_load_test():
    """Mark a test as completed in today's daily load."""
    user_id = g.current_user_id
    data = request.get_json(silent=True) or {}

    if not data:
        return bad_request("Request body required")

    test_id = data.get('test_id')
    language_id = parse_language_id(data.get('language_id'))

    if not test_id or not language_id:
        return bad_request("test_id and language_id required")

    try:
        test_service = get_test_service()
        result = test_service.mark_daily_test_complete(user_id, language_id, test_id)
        return api_success(data=result)
    except NoMatchingAttemptError:
        return bad_request("No attempt recorded today for this test")
    except Exception as e:
        logger.error(f"Error marking daily test complete: {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to mark daily test complete")


@tests_bp.route('/', methods=['GET'])
@supabase_jwt_required
def get_tests_with_ratings():
    """Get tests list with ELO ratings for filtering/preview."""
    try:
        language_id_param = request.args.get('language_id')
        difficulty = request.args.get('difficulty')
        limit = request.args.get('limit', 50, type=int) or 50

        if not current_app.supabase_service:
            return server_error("Database service not configured")

        query = current_app.supabase_service.table('tests').select(
            'id, slug, title, language_id, topic_id, difficulty, style, tier, '
            'audio_url, audio_generated, is_custom, is_featured, total_attempts'
        ).eq('is_active', True)

        # Parse and validate language_id
        language_id = parse_language_id(language_id_param)
        if language_id:
            query = query.eq('language_id', language_id)
        if difficulty:
            query = query.eq('difficulty', int(difficulty))

        tests_result = query.limit(limit).execute()

        test_ids = [test['id'] for test in tests_result.data]

        ratings_by_test = {}
        if test_ids:
            ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
                'test_id, test_type_id, elo_rating, total_attempts, dim_test_types(type_code)'
            ).in_('test_id', test_ids).execute()

            for rating in ratings_result.data:
                test_id = rating['test_id']
                type_code = rating.get('dim_test_types', {}).get('type_code', 'unknown')
                if test_id not in ratings_by_test:
                    ratings_by_test[test_id] = {}
                ratings_by_test[test_id][type_code] = {
                    'elo_rating': rating['elo_rating'],
                    'total_attempts': rating['total_attempts']
                }

        tests_with_ratings = []
        for test in tests_result.data:
            test_ratings = ratings_by_test.get(test['id'], {})
            test_with_ratings = {
                **test,
                'listening_rating': test_ratings.get('listening', {}).get('elo_rating', Config.DEFAULT_ELO_RATING),
                'reading_rating': test_ratings.get('reading', {}).get('elo_rating', Config.DEFAULT_ELO_RATING),
                'dictation_rating': test_ratings.get('dictation', {}).get('elo_rating', Config.DEFAULT_ELO_RATING),
                'skill_ratings': test_ratings
            }
            tests_with_ratings.append(test_with_ratings)

        return api_success(data={"tests": tests_with_ratings})

    except Exception as e:
        current_app.logger.error(f"Error fetching tests: {e}", exc_info=True)
        return server_error("Failed to fetch tests")

def _public_cacheable(response):
    """Mark a response that carries no per-user data as briefly cacheable."""
    body, status = response
    body.headers['Cache-Control'] = 'private, max-age=60'
    return body, status


def _transcript_withheld_for(db, user_id, test):
    """Dictation withholding decided on the server: True while today's daily
    load schedules this test as dictation for this learner and the slot is not
    completed. A test has no type of its own (the same test is read, listened
    to and dictated), so the scheduled slot is what makes it a dictation."""
    if not user_id:
        return False
    return TestService(supabase_admin=db).has_pending_dictation_slot(
        user_id, test.get('language_id'), test['id'])


@tests_bp.route('/<slug>', methods=['GET'])
#@supabase_jwt_required
def get_test(slug):
    """Get a test by slug in the shape expected by the Flutter app."""
    try:
        test_service = get_test_service()
        test_data = test_service.get_test_by_slug(slug)
        if not test_data:
            return not_found("Test not found")

        normalize_audio_url(test_data)

        from middleware.auth import get_optional_user_id
        user_id = get_optional_user_id(request)
        if user_id and current_app.supabase_service and _transcript_withheld_for(
                current_app.supabase_service, user_id, test_data):
            test_data['transcript'] = ''

        logger.debug(f"Returning test data for slug: {slug}")
        response = api_success(data={"test": test_data})
        return response if user_id else _public_cacheable(response)

    except Exception as e:
        current_app.logger.error(f"Error in get_test route: {e}")
        return server_error("Failed to fetch test")


# Post-submission hooks. The logic lives in services.attempts; these names are
# kept because routes/classifier_drill.py and routes/counter_drill.py import
# _apply_timing_and_progress from here.
_normalize_timing = attempts.normalize_timing
_complete_daily_slot = attempts.complete_daily_slot
_apply_timing_and_progress = attempts.apply_timing_and_progress
_credit_attempt_window = attempts.credit_attempt_window
_update_vocabulary_tracking = attempts.track_vocabulary
_attach_explanations = attempts.attach_explanations
_build_submission_response = attempts.build_submission_response


# CR-04: the four submission RPCs return {success:false, error:SQLERRM,
# error_detail:SQLSTATE} when the underlying Postgres EXCEPTION block fires.
# These helpers must (a) log the raw payload server-side and (b) return a
# generic envelope to the client — never forwarding SQLERRM text or
# table/column hints that aid schema probing.

def _submission_failure_response(rpc_name, payload):
    """Log the upstream failure payload and return a client-safe envelope."""
    current_app.logger.error(
        "%s failed: %s", rpc_name, payload
    )
    return api_error("submission_failed", 500, error_code="submission_failed")


def _unwrap_rpc_response(rpc_name, response_data, on_success):
    """Inspect an RPC response and dispatch success/failure.

    ``on_success`` is invoked with the parsed dict when the payload is
    ``{success: True, ...}`` so the caller can record info-level logs with
    RPC-specific identifiers. Failures route through the generic envelope.
    """
    if isinstance(response_data, dict) and response_data.get('success'):
        on_success(response_data)
        return response_data
    # An RPC may signal an authz failure with a typed error_code rather than a
    # raised exception (which the RPC's WHEN OTHERS handler would otherwise mask
    # as a generic submission_failed). Surface it as a 403 so the client can
    # distinguish "not your test" from "server blew up".
    if isinstance(response_data, dict) and response_data.get('error_code') == 'unauthorized':
        current_app.logger.warning("%s rejected: unauthorized", rpc_name)
        return api_error("unauthorized", 403, error_code="unauthorized")
    return _submission_failure_response(rpc_name, response_data)


def _is_missing_function_error(exc) -> bool:
    """PostgREST's "no function matches these argument names" (PGRST202)."""
    text = str(exc)
    try:
        payload = exc.json() if hasattr(exc, 'json') else {}
    except Exception:
        payload = {}
    code = (payload or {}).get('code') if isinstance(payload, dict) else None
    return code == 'PGRST202' or 'PGRST202' in text or 'Could not find the function' in text


def _submit_rpc(client, rpc_name, user_id, test_id, language_id, test_type_id,
                idempotency_key, extra, optional_param=None):
    """Call one of the process_*_submission RPCs and handle JSONB response quirks.

    Returns the parsed RPC result dict on success, or a
    ``(jsonify_response, status_code)`` tuple on failure. Failure envelopes
    never include SQLERRM text — see CR-04.

    ``optional_param`` names a parameter in ``extra`` that an older database
    function may not have: when PostgREST reports the function missing, the
    call is repeated once without it.
    """
    def _on_success(data):
        current_app.logger.info(
            "%s succeeded: attempt_id=%s", rpc_name, data.get('attempt_id'),
        )

    params = {
        'p_user_id': user_id,
        'p_test_id': test_id,
        'p_language_id': language_id,
        'p_test_type_id': test_type_id,
        'p_was_free_test': True,
        'p_idempotency_key': str(idempotency_key) if idempotency_key else str(uuid4()),
        **extra,
    }
    try:
        response = client.rpc(rpc_name, params).execute()
    except Exception as e:
        if optional_param in params and _is_missing_function_error(e):
            current_app.logger.warning(
                "%s has no %s yet; submitting without it", rpc_name, optional_param)
            del extra[optional_param]
            return _submit_rpc(client, rpc_name, user_id, test_id, language_id, test_type_id,
                               params['p_idempotency_key'], extra)
        # supabase-py raises on JSONB responses; rescue the payload here so
        # we can dispatch both success and failure paths uniformly.
        error_data = e.json() if hasattr(e, 'json') else (e.args[0] if e.args else {})
        return _unwrap_rpc_response(rpc_name, error_data, _on_success)

    return _unwrap_rpc_response(rpc_name, response.data, _on_success)


def _call_submission_rpc(client, user_id, test_id, language_id, test_type_id, db_responses, furigana_used=False, idempotency_key=None, prestudied=False):
    extra = {'p_responses': db_responses, 'p_furigana_used': bool(furigana_used)}
    if prestudied:
        # Only sent when true, so a database without migrations/prestudy_elo_factor.sql
        # keeps working for every ordinary submission; if the function lacks the
        # parameter the attempt is graded at full K rather than failed.
        extra['p_prestudied'] = True
    return _submit_rpc(client, 'process_test_submission', user_id, test_id, language_id,
                       test_type_id, idempotency_key, extra, optional_param='p_prestudied')


def _call_dictation_submission_rpc(
    client, user_id, test_id, language_id, test_type_id,
    word_correct, word_total, replay_count, diff_payload, idempotency_key,
):
    return _submit_rpc(client, 'process_dictation_submission', user_id, test_id, language_id,
                       test_type_id, idempotency_key, {
                           'p_word_correct': int(word_correct),
                           'p_word_total': int(word_total),
                           'p_replay_count': int(replay_count),
                           'p_diff_payload': diff_payload,
                       })


def _call_pinyin_submission_rpc(client, user_id, test_id, language_id, test_type_id, correct_chars, total_chars, idempotency_key=None):
    return _submit_rpc(client, 'process_pinyin_submission', user_id, test_id, language_id,
                       test_type_id, idempotency_key, {
                           'p_correct_chars': int(correct_chars),
                           'p_total_chars': int(total_chars),
                       })


def _call_pitch_accent_submission_rpc(client, user_id, test_id, language_id, test_type_id, correct_units, total_units, furigana_used=False, idempotency_key=None):
    return _submit_rpc(client, 'process_pitch_accent_submission', user_id, test_id, language_id,
                       test_type_id, idempotency_key, {
                           'p_correct_units': int(correct_units),
                           'p_total_units': int(total_units),
                           'p_furigana_used': bool(furigana_used),
                       })


# ---------------------------------------------------------------------------
# Shared skeleton of the four submit handlers
# ---------------------------------------------------------------------------

def _submit_handler(log_label, failure_message):
    """Wrap a submit handler ``fn(slug, db, user_id, data)``: database check,
    JSON body, and the handler's error envelope."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(slug):
            try:
                db = current_app.supabase_service
                if not db:
                    return server_error("Database service not configured")
                return fn(slug, db, g.current_user_id, request.get_json() or {})
            except Exception as e:
                current_app.logger.error(f"{log_label} submission error: {e}")
                current_app.logger.error(f"Traceback: {traceback.format_exc()}")
                return server_error(failure_message)
        return wrapper
    return decorator


def _record_submission(rpc_result, db, data, user_id, language_id, test_id,
                       log_label, failure_message):
    """After a submission RPC: ``(error_response, pending)``.

    ``error_response`` is the response to return when the RPC failed, else
    None. On success the timing/progress and daily-slot hooks (best-effort)
    are started; the handler must ``attempts.join(pending)`` before answering.
    """
    if isinstance(rpc_result, tuple):
        return rpc_result, []
    # The wrappers already convert any {success:false} payload into the generic
    # envelope tuple, so this branch is a belt-and-suspenders guard. Do NOT
    # forward error_msg to the client — it may contain SQLERRM text (CR-04).
    if not rpc_result or not rpc_result.get('success'):
        error_msg = rpc_result.get('error', 'Unknown error') if rpc_result else 'RPC failed'
        error_detail = rpc_result.get('error_detail', '') if rpc_result else ''
        current_app.logger.error(f"{log_label} RPC failed: {error_msg} (detail: {error_detail})")
        return server_error(failure_message), []

    # Phase 13 — persist timing + bump Study Plan counter (best-effort).
    return None, [
        attempts.defer(_apply_timing_and_progress, db, rpc_result.get('attempt_id'), data,
                       user_id=user_id, language_id=language_id),
        attempts.defer(_complete_daily_slot, user_id=user_id, language_id=language_id,
                       test_id=test_id, db=db),
    ]


@tests_bp.route('/<slug>/submit', methods=['POST'])
@supabase_jwt_required
@_submit_handler('Test', 'Failed to submit test')
def submit_test_attempt(slug, db, current_user_id, data):
    """Submit test answers and calculate ELO changes with idempotency support"""
    responses = data.get('responses', [])
    test_mode = data.get('test_mode', 'reading').lower()
    furigana_used = bool(data.get('furigana_used', False))
    prestudied = data.get('prestudied') is True
    idempotency_key = data.get('idempotency_key') or str(uuid4())

    if not responses:
        return bad_request("No responses provided")

    try:
        _normalize_timing(data)
    except AttemptTimingError as e:
        return bad_request(str(e))

    # Lightweight test lookup (just id and language_id, no questions)
    test = find_active_test_by_slug(db, slug)
    if not test:
        return not_found(f"Test not found: {slug}")

    test_id = test['id']
    language_id = test['language_id']

    # Get test_type_id from the test_mode using DimensionService cache
    test_type_id = DimensionService.get_test_type_id(test_mode)
    if not test_type_id:
        logger.warning(f"Unknown test_mode '{test_mode}', defaulting to reading")
        test_type_id = DimensionService.get_test_type_id('reading') or 1

    # Transform responses: strip 'is_correct' field (DB will calculate).
    db_responses = [{"question_id": str(r['question_id']), "selected_answer": r['selected_answer']} for r in responses]

    # Test prestudy: the attempt is prestudied when a completed prime for
    # this test exists in the last 6 hours (server-verified). The client
    # flag only counts while prestudy_sessions does not exist yet.
    from services import prestudy as _prestudy

    def _verify_prestudy():
        try:
            return _prestudy.find_prestudy_for_attempt(db, current_user_id, test_id)
        except Exception as e:
            logger.warning("prestudy verification skipped: %s", e)
            return None, False

    # The questions (sense ids, explanations) are read once here, alongside
    # the prestudy check, and handed to everything after the RPC.
    (prestudy_session_id, verifiable), question_rows = run_parallel(
        _verify_prestudy, lambda: attempts.load_question_rows(db, test_id))
    if verifiable:
        prestudied = prestudy_session_id is not None

    # Call database RPC for validation, ELO calculation and attempt recording
    rpc_result = _call_submission_rpc(
        db, current_user_id,
        test_id, language_id, test_type_id, db_responses,
        furigana_used=furigana_used, idempotency_key=idempotency_key,
        prestudied=prestudied,
    )
    error, pending = _record_submission(
        rpc_result, db, data, current_user_id, language_id, test_id,
        'ELO', 'submission_failed')
    if error:
        return error

    current_app.logger.info(
        f"Test submitted: user={current_user_id}, test={test_id}, "
        f"attempt={rpc_result.get('attempt_id')}, "
        f"score={rpc_result.get('score', 0)}/{rpc_result.get('total_questions', 0)}"
    )
    try:
        if prestudied and prestudy_session_id:
            pending.append(attempts.defer(
                _prestudy.consume_session, db, prestudy_session_id, rpc_result.get('attempt_id')))

        # BKT vocabulary tracking
        word_quiz = _update_vocabulary_tracking(
            current_user_id, test_id, language_id, rpc_result,
            question_rows=question_rows, pending=pending)

        result = _build_submission_response(rpc_result, test_mode, word_quiz)
        _attach_explanations(result, question_rows)
        if prestudied:
            result['prestudied'] = True
    finally:
        attempts.join(pending)
    return api_success(data={'result': result})


def _submit_counted(slug, db, user_id, data, *, correct_key, total_key, mode,
                    language_id, wrong_language, type_missing, payload_column,
                    item_count, items, call_rpc, log_label, failure_message):
    """Pinyin / pitch-accent submit: the browser reports correct and total
    counts, which are checked against the test's real number of items."""
    time_taken = clamp_time_taken(data.get('time_taken', 0))
    idempotency_key = data.get('idempotency_key') or str(uuid4())

    try:
        correct, total = validate_counts(
            data.get(correct_key, 0), data.get(total_key, 0), correct_key, total_key)
        _normalize_timing(data)
    except AttemptTimingError as e:
        return bad_request(str(e))

    accuracy = correct / total

    test = find_active_test_by_slug(db, slug, f'id, language_id, {payload_column}')
    if not test:
        return not_found(f"Test not found: {slug}")

    test_id = test['id']
    if test['language_id'] != language_id:
        return bad_request(wrong_language)

    real_total = item_count(test.get(payload_column))
    if total > real_total:
        return bad_request(f"{total_key} exceeds the {real_total} {items} of this test")

    type_id = DimensionService.get_test_type_id(mode)
    if not type_id:
        return server_error(type_missing)

    rpc_result = call_rpc(db, user_id, test_id, language_id, type_id, correct, total,
                          idempotency_key=idempotency_key)
    error, pending = _record_submission(
        rpc_result, db, data, user_id, language_id, test_id, log_label, failure_message)
    if error:
        return error
    attempts.join(pending)

    return api_success(data={'result': {
        'accuracy': round(accuracy * 100, 1),
        correct_key: correct,
        total_key: total,
        'time_taken': time_taken,
        **attempts.elo_changes(rpc_result),
        'test_mode': mode,
        'attempt_id': attempts.attempt_id_str(rpc_result),
    }})


@tests_bp.route('/<slug>/submit-pinyin', methods=['POST'])
@supabase_jwt_required
@_submit_handler('Pinyin', 'Failed to submit pinyin test')
def submit_pinyin_attempt(slug, db, current_user_id, data):
    """Submit pinyin tone trainer results.

    Accepts accuracy-based scoring (correct_chars / total_chars) and delegates
    to process_pinyin_submission, which records the attempt and updates ELO
    without referencing the test's MC questions.
    """
    return _submit_counted(
        slug, db, current_user_id, data,
        correct_key='correct_chars', total_key='total_chars', mode='pinyin',
        language_id=1, wrong_language="Pinyin mode is only available for Chinese tests",
        type_missing="Pinyin test type not configured",
        payload_column='pinyin_payload', item_count=attempts.pinyin_item_count,
        items='characters',
        call_rpc=lambda *a, **k: _call_pinyin_submission_rpc(*a, **k),
        log_label='Pinyin', failure_message="Failed to process pinyin submission",
    )


@tests_bp.route('/<slug>/submit-pitch-accent', methods=['POST'])
@supabase_jwt_required
@_submit_handler('Pitch accent', 'Failed to submit pitch accent test')
def submit_pitch_accent_attempt(slug, db, current_user_id, data):
    """Submit pitch accent trainer results.

    Accepts accuracy-based scoring (correct_units / total_units, one unit per
    accent phrase) and delegates to process_pitch_accent_submission, which
    records the attempt and updates ELO without referencing the test's MC
    questions.
    """
    furigana_used = bool(data.get('furigana_used', False))
    return _submit_counted(
        slug, db, current_user_id, data,
        correct_key='correct_units', total_key='total_units', mode='pitch_accent',
        language_id=3, wrong_language="Pitch accent mode is only available for Japanese tests",
        type_missing="Pitch accent test type not configured",
        payload_column='pitch_payload', item_count=attempts.pitch_item_count,
        items='accent phrases',
        call_rpc=lambda *a, **k: _call_pitch_accent_submission_rpc(
            *a, furigana_used=furigana_used, **k),
        log_label='Pitch accent', failure_message="Failed to process pitch accent submission",
    )


@tests_bp.route('/<slug>/submit-dictation', methods=['POST'])
@supabase_jwt_required
@_submit_handler('Dictation', 'Failed to submit dictation')
def submit_dictation_attempt(slug, db, current_user_id, data):
    """Submit a dictation transcript for grading.

    Grades the typed transcript against the canonical one server-side via
    services.dictation.grader.grade_dictation, then calls
    process_dictation_submission to persist the attempt + update ELO, and
    finally fires per-word BKT updates for every transcript word that maps
    to a dim_word_senses row.
    """
    user_transcript = (data.get('user_transcript') or '').strip()
    replay_count = data.get('replay_count', 1)
    time_taken = clamp_time_taken(data.get('time_taken', 0))
    idempotency_key = data.get('idempotency_key') or str(uuid4())

    if not user_transcript:
        return bad_request("Empty user_transcript")

    try:
        _normalize_timing(data)
    except AttemptTimingError as e:
        return bad_request(str(e))

    try:
        replay_count = max(1, int(replay_count))
    except (TypeError, ValueError):
        replay_count = 1

    # Fetch canonical transcript + vocab metadata server-side
    test = find_active_test_by_slug(
        db, slug, 'id, language_id, transcript, vocab_sense_ids, vocab_token_map')
    if not test:
        return not_found(f"Test not found: {slug}")

    test_id = test['id']
    language_id = test['language_id']
    correct_transcript = (test.get('transcript') or '').strip()

    if not correct_transcript:
        return bad_request("Test has no transcript")

    # Server-side pathological-length guard (see plan §10)
    if len(user_transcript) > 10 * max(1, len(correct_transcript)):
        return bad_request("user_transcript exceeds 10x canonical length")

    dictation_type_id = DimensionService.get_test_type_id('dictation')
    if not dictation_type_id:
        return server_error("Dictation test type not configured")

    language_code = DimensionService.get_language_code(language_id) or ''

    # Grade
    from services.dictation import grade_dictation
    result = grade_dictation(correct_transcript, user_transcript, language_code)

    if result.word_total <= 0:
        return server_error("Canonical transcript produced no tokens")

    attempts.attach_dictation_senses(result.diff, test.get('vocab_token_map') or [])

    diff_payload = result.diff_payload()
    # Cap the STORED diff; the full diff is still returned to the client
    # for the current response.
    #
    # TASK-715: this was a flat 200 entries, chosen when every dictation
    # was capped at 80 words. With the per-tier cap a T6 passage can run to
    # 400 canonical tokens, so 200 would silently truncate the stored diff
    # mid-passage and a revisit would show a partial review — a truncation
    # surprise with no error anywhere. The ceiling now derives from the
    # largest tier cap, with headroom for 'insert' ops (extra user-side
    # tokens beyond the canonical count).
    diff_payload_stored = diff_payload[:MAX_STORED_DIFF_ENTRIES]

    rpc_result = _call_dictation_submission_rpc(
        db, current_user_id,
        test_id, language_id, dictation_type_id,
        result.word_correct, result.word_total, replay_count,
        diff_payload_stored, idempotency_key,
    )
    # See CR-04 — don't echo SQLERRM text into the client response.
    error, pending = _record_submission(
        rpc_result, db, data, current_user_id, language_id, test_id,
        'Dictation', 'submission_failed')
    if error:
        return error

    pending.append(attempts.defer(
        attempts.record_dictation_bkt, current_user_id, language_id, test_id, result.diff))
    attempts.join(pending)

    return api_success(data={'result': {
        'accuracy': round(result.accuracy * 100, 1),
        'word_correct': result.word_correct,
        'word_total': result.word_total,
        'replay_count': replay_count,
        'time_taken': time_taken,
        'diff': diff_payload,
        **attempts.elo_changes(rpc_result),
        'replay_factor': rpc_result.get('replay_factor'),
        'elo_reduction_factor': rpc_result.get('elo_reduction_factor'),
        'test_mode': 'dictation',
        'attempt_id': attempts.attempt_id_str(rpc_result),
    }})


@tests_bp.route('/test/<identifier>', methods=['GET'])
#@supabase_jwt_required
def get_test_with_ratings(identifier):
    """Get test with ELO ratings for preview/taking. Accepts slug or UUID."""
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")

        # This route is deliberately reachable without auth (public
        # preview/taking) -- personalize the definition language only
        # when a valid token happens to be present.
        from middleware.auth import get_optional_user_id
        from services.vocabulary.gloss_lookup import (
            apply_definition_language_preference, get_user_definition_language_id,
        )
        optional_user_id = get_optional_user_id(request)

        def _definition_language(test):
            if not optional_user_id or not any(s for _, s in (test.get('vocab_token_map') or [])):
                return None
            return get_user_definition_language_id(db, optional_user_id)

        # Static content comes from the in-process cache; ratings and the
        # per-user reads are fetched now, alongside whatever is not cached.
        found = get_test_content(db, identifier, also=(
            lambda test: get_test_skill_ratings(db, test['id']),
            lambda test: _transcript_withheld_for(db, optional_user_id, test),
            _definition_language,
        ))
        if not found:
            return not_found("Test not found")
        content, (ratings, dictation_pending, preferred_def_lang_id) = found
        test = content['test']

        # Add language info for backwards compatibility
        lang_info = test.pop('dim_languages', {}) or {}
        test['language'] = lang_info.get('language_code', 'unknown')
        test['language_name'] = lang_info.get('language_name', 'Unknown')

        # Withhold transcript pre-submit in dictation mode — the entire point
        # is that the learner types what they hear without seeing the text.
        # `?mode=dictation` asks for it; a pending dictation slot in today's
        # load enforces it whatever the caller asks for.
        mode = (request.args.get('mode') or '').lower()
        if mode == 'dictation' or dictation_pending:
            test.pop('transcript', None)
            test.pop('vocab_token_map', None)

        normalize_audio_url(test)

        # Pop pinyin payload (only present for Chinese tests)
        pinyin_payload = test.pop('pinyin_payload', None)
        # Pop pitch accent payload (only present for Japanese tests)
        pitch_payload = test.pop('pitch_payload', None)
        # Pop furigana payload (only present for Japanese tests)
        furigana_payload = test.pop('furigana_payload', None)

        # Load definitions for vocab token map sense IDs
        token_map = test.pop('vocab_token_map', None) or []
        definitions = {}
        sense_rows = content['senses'] if token_map else []
        if sense_rows:
            gloss_rows = []
            for sense in sense_rows:
                vocab = sense.get('dim_vocabulary') or {}
                gloss_rows.append({
                    'vocab_id': sense.get('vocab_id'),
                    'sense_rank': sense.get('sense_rank'),
                    'definition_level': sense.get('definition_level'),
                    'definition': sense.get('definition', ''),
                    'language_id': vocab.get('language_id'),
                })
            apply_definition_language_preference(db, gloss_rows, preferred_def_lang_id)

            for sense, gloss_row in zip(sense_rows, gloss_rows):
                vocab = sense.get('dim_vocabulary') or {}
                definitions[str(sense['id'])] = {
                    'word': vocab.get('lemma', ''),
                    'definition': gloss_row['definition'],
                    'definition_language_id': gloss_row['definition_language_id'],
                    'definition_is_gloss': gloss_row['definition_is_gloss'],
                    'part_of_speech': vocab.get('part_of_speech', ''),
                    'reading': sense.get('pronunciation')
                }

        # Build response
        response_data = {
            "test_data": test,
            "questions_data": content['questions'],
            "skill_ratings": ratings,
            "vocab_token_map": token_map,
            "definitions": definitions,
        }
        if pinyin_payload is not None:
            response_data["pinyin_payload"] = pinyin_payload
        if pitch_payload is not None:
            response_data["pitch_payload"] = pitch_payload
        if furigana_payload is not None:
            response_data["furigana_payload"] = furigana_payload

        response = api_success(data=response_data)
        return response if optional_user_id else _public_cacheable(response)

    except Exception as e:
        current_app.logger.error(f"Error fetching test {identifier}: {e}")
        return server_error("Failed to fetch test")


@tests_bp.route('/history', methods=['GET'])
@supabase_jwt_required
def get_test_history():
    """Get user's test attempt history with manual join"""
    try:
        user_id = g.current_user_id
        if not user_id:
            return unauthorized("User ID not found")

        history = attempts.list_test_history(
            current_app.supabase_service or current_app.supabase,
            current_app.supabase_service,
            user_id,
            language_id=request.args.get('language_id', type=int),
            test_type_id=request.args.get('test_type_id', type=int),
            limit=min(request.args.get('limit', 25, type=int) or 25, 100),
            offset=max(request.args.get('offset', 0, type=int) or 0, 0),
        )
        return api_success(data={'tests': history})

    except Exception as e:
        logger.error(f"Error getting test history: {e}")
        logger.error(traceback.format_exc())
        return server_error('Failed to get test history')

# ============================================================================
# TASK-909 — sentence spans + L1 references (ADR-037)
# ============================================================================

# Fallback L1 while users.native_language_id is unset for most rows — id 2 =
# English (config.py LANGUAGES); mirrors routes/dual_translation.py.
_DEFAULT_L1_LANGUAGE_ID = 2

_SENTENCE_COLUMNS = 'id, idx, l2_text, char_start, char_end, token_start, token_end, transcript_hash'


def _find_test_for_sentences(db, identifier):
    """Active test by slug, then by uuid; the columns the sentences endpoint needs."""
    return find_active_test(db, identifier, 'id, slug, language_id, transcript_hash')


def _resolve_sentence_l1(db, user_id, l1_code):
    """``?l1=<code>`` -> dim_languages id; absent -> users.native_language_id,
    else English. Unknown codes return None (400 at the route)."""
    if l1_code:
        return SENTENCE_L1_IDS.get(str(l1_code).lower())
    try:
        resp = db.table('users').select('native_language_id').eq('id', user_id).limit(1).execute()
        if resp.data and resp.data[0].get('native_language_id'):
            return int(resp.data[0]['native_language_id'])
    except Exception as e:  # best-effort; the default is always usable
        logger.warning("native_language_id lookup failed for %s: %s", user_id, e)
    return _DEFAULT_L1_LANGUAGE_ID


def _has_attempt_today(db, user_id, test_id, language_id):
    """True when the user has a ``test_attempts`` row for this test since the
    start of their local day (ADR-022) — the same check
    ``TestService.mark_daily_test_complete`` makes. This is the ``?mode=produce``
    withholding rule: before today's attempt is submitted the L2 text stays
    hidden, exactly as ``?mode=dictation`` hides the transcript."""
    day_start = local_day_start_utc(plan_timezone(db, user_id, language_id))
    resp = (
        db.table('test_attempts').select('id')
        .eq('user_id', user_id).eq('test_id', test_id)
        .gte('created_at', day_start.isoformat())
        .limit(1).execute()
    )
    return bool(resp.data)


def _load_sentence_rows(db, test_id):
    resp = (
        db.table('test_sentences').select(_SENTENCE_COLUMNS)
        .eq('test_id', test_id).order('idx').execute()
    )
    return resp.data or []


def _load_active_references(db, sentence_ids, l1_language_id):
    """``{sentence_id: {l1_text, tightness, review_verdict}}`` for the active
    reference of each sentence in this L1 (at most one active per pair)."""
    if not sentence_ids:
        return {}
    resp = (
        db.table('test_sentence_references')
        .select('sentence_id, l1_text, tightness, review_verdict')
        .in_('sentence_id', list(sentence_ids))
        .eq('l1_language_id', l1_language_id)
        .eq('is_active', True)
        .execute()
    )
    return {row['sentence_id']: row for row in (resp.data or [])}


def build_sentence_payload(rows, references, withhold_l2):
    """Shape the endpoint's ``sentences`` list from ``test_sentences`` rows and
    the active-reference map. ``l2_text`` is dropped when ``withhold_l2``."""
    out = []
    for row in rows:
        ref = references.get(row.get('id'))
        item = {
            'idx': row['idx'],
            'char_start': row['char_start'],
            'char_end': row['char_end'],
            'token_start': row.get('token_start'),
            'token_end': row.get('token_end'),
            'reference': (
                {'l1_text': ref['l1_text'], 'tightness': ref.get('tightness')} if ref else None
            ),
        }
        if not withhold_l2:
            item['l2_text'] = row['l2_text']
        out.append(item)
    return out


@tests_bp.route('/<identifier>/sentences', methods=['GET'])
@supabase_jwt_required
def get_test_sentences(identifier):
    """Sentence spans of a test with the learner's L1 references (TASK-909).

    ``?l1=<code>`` picks the reference language (default: the user's native
    language, else English). ``?mode=produce`` withholds ``l2_text`` until the
    user has submitted an attempt today — the Produce stage must not leak the
    passage before the test. 404 unknown test; 409 when the sentence rows were
    segmented from a different transcript than the one now stored (stale —
    the backfill script re-segments); an empty ``sentences`` list means the
    test has no rows yet (the client falls back to its own split).
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")

        test = _find_test_for_sentences(db, identifier)
        if not test:
            return not_found("Test not found")

        l1_language_id = _resolve_sentence_l1(db, g.current_user_id, request.args.get('l1'))
        if l1_language_id is None:
            return bad_request("Unknown l1 language code")

        rows = _load_sentence_rows(db, test['id'])
        stored_hash = test.get('transcript_hash')
        if rows and stored_hash and any(r.get('transcript_hash') != stored_hash for r in rows):
            return api_error(
                "Sentence rows are stale for this transcript", 409, error_code="SENTENCES_STALE",
            )

        mode = (request.args.get('mode') or '').lower()
        withhold = mode == 'produce' and not _has_attempt_today(
            db, g.current_user_id, test['id'], test.get('language_id'),
        )

        references = _load_active_references(db, [r['id'] for r in rows], l1_language_id)
        return api_success(data={
            'test_id': test['id'],
            'l1_language_id': l1_language_id,
            'l2_withheld': withhold,
            'sentences': build_sentence_payload(rows, references, withhold),
        })

    except Exception as e:
        logger.error("Error loading sentences for %s: %s", identifier, e)
        logger.error(traceback.format_exc())
        return server_error('Failed to load sentences')


# ============================================================================
# Test prestudy (wiki/features/test-prestudy.md)
# ============================================================================

_PRESTUDY_TEST_COLUMNS = (
    'id, slug, title, language_id, transcript, audio_url, difficulty, target_age_tier, '
    'vocab_sense_ids, vocab_token_map, furigana_payload, pinyin_payload'
)
_PRESTUDY_MAX_ANSWERS = 400
_PRESTUDY_MAX_EXERCISE_ANSWERS = 40


def _find_test_for_prestudy(db, identifier):
    """Active test by slug, then by uuid, with the columns prestudy needs."""
    return find_active_test(db, identifier, _PRESTUDY_TEST_COLUMNS)


@tests_bp.route('/<identifier>/prestudy', methods=['GET'])
@supabase_jwt_required
def get_test_prestudy(identifier):
    """Study material for one test: passage, word map, glosses in the learner's
    language, their knowledge of each word, and ladder exercises.

    ``?mode=followup`` (after an attempt) adds ``followup_sense_ids``: the
    senses behind the questions answered wrong on the latest attempt.

    Never returns the scored questions' text, choices or answers; only each
    question's linked senses, so the page can rank the words the test turns on.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")
        test = _find_test_for_prestudy(db, identifier)
        if not test:
            return not_found("Test not found")
        from services import prestudy
        from services.vocabulary.gloss_lookup import get_user_definition_language_id
        gloss_lang = get_user_definition_language_id(db, g.current_user_id)
        payload = prestudy.build_prestudy_payload(db, test, g.current_user_id, gloss_lang)
        if request.args.get('mode') == 'followup':
            attempt_id, senses = prestudy.wrong_question_senses(db, g.current_user_id, test['id'])
            if not attempt_id:
                return bad_request("Take the test before its follow-up")
            prime = prestudy.latest_prime_session(db, g.current_user_id, test['id'])
            payload['followup_sense_ids'] = senses
            payload['attempt_id'] = attempt_id
            payload['primed_sense_ids'] = (prime or {}).get('words_quizzed') or []
        return api_success(data=payload)
    except Exception as e:
        logger.error("Error loading prestudy for %s: %s", identifier, e)
        logger.error(traceback.format_exc())
        return server_error('Failed to load prestudy')


@tests_bp.route('/<identifier>/prestudy/session', methods=['POST'])
@supabase_jwt_required
def start_test_prestudy_session(identifier):
    """Open a prestudy_sessions row when the page loads.

    Body: {test_type, trigger, plan_mode, unknown_share, mode, session_block_id}.
    ``unknown_share`` is the snapshot at open and is never recomputed.
    Returns {session_id} (null until migrations/prestudy_workflow.sql is applied).
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")
        test = _find_test_for_prestudy(db, identifier)
        if not test:
            return not_found("Test not found")
        body = request.get_json(silent=True) or {}
        from services import prestudy
        load_date = None
        if body.get('session_block_id'):
            from services.day_boundary import plan_today_iso
            load_date = plan_today_iso(db, g.current_user_id, int(test['language_id']))
        session_id = prestudy.start_session(
            db, g.current_user_id, test,
            test_type=body.get('test_type') or 'reading', trigger=body.get('trigger') or 'opt_in',
            plan_mode=body.get('plan_mode'), unknown_share=body.get('unknown_share'),
            mode=body.get('mode') or 'prime', session_block_id=body.get('session_block_id'),
            load_date=load_date,
        )
        return api_success(data={'session_id': session_id})
    except Exception as e:
        logger.error("Error starting prestudy session for %s: %s", identifier, e)
        return server_error('Failed to start prestudy')


def _record_prestudy_exercises(db, user_id, exercise_answers, allowed):
    """Ladder exercises answered in the prime -> exercise_attempts (source
    prestudy) + exercise BKT. Only exercises of this test's senses count."""
    from services.practice_session_service import get_practice_session_service
    ids = []
    by_id = {}
    for a in exercise_answers[:_PRESTUDY_MAX_EXERCISE_ANSWERS]:
        if isinstance(a, dict) and isinstance(a.get('exercise_id'), str) and a['exercise_id'] not in by_id:
            by_id[a['exercise_id']] = a
            ids.append(a['exercise_id'])
    if not ids:
        return 0
    rows = db.table('exercises').select('id, exercise_type, word_sense_id, language_id') \
        .in_('id', ids).eq('is_active', True).execute().data or []
    svc = get_practice_session_service()
    recorded = 0
    for ex in rows:
        if ex.get('word_sense_id') not in allowed:
            continue
        a = by_id.get(str(ex['id'])) or {}
        try:
            svc.record_prestudy_exercise_attempt(
                user_id, ex, bool(a.get('correct')) and not a.get('idk'),
                user_response={'given': str(a.get('given') or '')[:500], 'idk': bool(a.get('idk'))},
            )
            recorded += 1
        except Exception as e:
            logger.warning("prestudy exercise %s not recorded: %s", ex.get('id'), e)
    return recorded


@tests_bp.route('/<identifier>/prestudy/evidence', methods=['POST'])
@supabase_jwt_required
def submit_test_prestudy_evidence(identifier):
    """Record a finished prime (or post-test follow-up) in one call.

    Body: {session_id?, mode?: 'prime'|'followup', answers: [{sense_id, correct,
    idk, stage}], exercise_answers?: [{exercise_id, correct, idk, given}],
    metrics?: {...}}.

    * Word answers: one word-test evidence point per sense (majority of its
      answers; "I don't know" counts as wrong). The prime writes with
      side_effects=False (no ladder admission, no new-word quota); the
      follow-up writes with side effects, so its senses enter Queue A1 as the
      post-test quiz's do.
    * Exercise answers: exercise_attempts tagged source=prestudy + exercise BKT.
    * Session: measurement record, minutes to the ledger (kind prestudy),
      next-day review rows, generation requests for primed words that have no
      exercises.
    Only senses of this test are accepted.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")
        test = _find_test_for_prestudy(db, identifier)
        if not test:
            return not_found("Test not found")
        body = request.get_json(silent=True) or {}
        answers = body.get('answers') or []
        exercise_answers = body.get('exercise_answers') or []
        if not isinstance(answers, list) or not isinstance(exercise_answers, list):
            return bad_request("answers and exercise_answers must be lists")
        if not answers and not exercise_answers and not body.get('session_id'):
            return bad_request("answers must be a non-empty list")
        if len(answers) > _PRESTUDY_MAX_ANSWERS:
            return bad_request(f"at most {_PRESTUDY_MAX_ANSWERS} answers")
        from services import prestudy
        user_id = g.current_user_id
        language_id = int(test['language_id'])
        allowed = prestudy.test_sense_ids(db, test)
        session = prestudy.get_session(db, user_id, body.get('session_id'))
        if session and session.get('test_id') != test['id']:
            session = None
        mode = 'followup' if (body.get('mode') == 'followup' or (session or {}).get('mode') == 'followup') else 'prime'

        rows = prestudy.evidence_rows(answers, allowed)
        updates = []
        if rows:
            updates = VocabularyKnowledgeService(db).update_from_word_tests_batch(
                user_id=user_id, language_id=language_id,
                results=rows, side_effects=(mode == 'followup'),
            ) or []
        n_ex = _record_prestudy_exercises(db, user_id, exercise_answers, allowed) if exercise_answers else 0

        out = {'updates': updates, 'recorded': len(rows), 'exercises_recorded': n_ex, 'session': None}
        if session and session.get('status') == 'open':
            reasons = prestudy.followups_from_answers(answers, allowed)
            if mode == 'followup':
                prime = prestudy.latest_prime_session(db, user_id, test['id'])
                reasons.update(prestudy.primed_missed((prime or {}).get('words_quizzed'), answers, allowed))
            metrics = body.get('metrics') if isinstance(body.get('metrics'), dict) else {}
            out['session'] = prestudy.complete_session(db, user_id, session, metrics, allowed, reasons)
            if mode == 'prime':
                # Primed words with no ladder exercises -> generation (reason prestudy)
                quizzed = [int(s) for s in (metrics.get('words_quizzed') or []) if str(s).isdigit()]
                quizzed = [s for s in quizzed if s in allowed]
                have = prestudy.senses_with_exercises(db, quizzed) if quizzed else set()
                out['generation_queued'] = prestudy.request_generation(
                    db, quizzed, language_id, {str(s): [True] for s in have})
        if mode == 'prime':
            # New-word drill (ADR-040): drilled words enter the ladder's intro
            # drill; a word that met session 1's target in the prime starts at
            # session 2. Words over today's quota come back as `overflow`.
            try:
                from services import intro_drill
                from services.practice_session_service import PracticeSessionService
                metrics = body.get('metrics') if isinstance(body.get('metrics'), dict) else {}
                drilled = [int(s) for s in (metrics.get('words_quizzed') or []) if str(s).isdigit() and int(s) in allowed]
                met = {int(s) for s in (metrics.get('met_sense_ids') or []) if str(s).isdigit()}
                out['intro'] = intro_drill.admit_prestudy(
                    PracticeSessionService(db), user_id, language_id, drilled, met)
            except Exception as e:
                logger.warning("prestudy intro admission failed for %s: %s", identifier, e)
        return api_success(data=out)
    except Exception as e:
        logger.error("Error recording prestudy evidence for %s: %s", identifier, e)
        logger.error(traceback.format_exc())
        return server_error('Failed to record prestudy answers')


@tests_bp.route('/<identifier>/prestudy/admit-overflow', methods=['POST'])
@supabase_jwt_required
def admit_prestudy_overflow(identifier):
    """'Add them all now': start the prime's over-quota words today.

    Body: {sense_ids: [...]}. Only words of this test that the prime queued in
    the last 6 hours qualify (services.intro_drill.overload).
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")
        test = _find_test_for_prestudy(db, identifier)
        if not test:
            return not_found("Test not found")
        body = request.get_json(silent=True) or {}
        ids = body.get('sense_ids')
        if not isinstance(ids, list) or not ids or len(ids) > 200:
            return bad_request("sense_ids must be a list of 1-200 ids")
        from services import prestudy, intro_drill
        allowed = prestudy.test_sense_ids(db, test)
        ids = [int(s) for s in ids if str(s).isdigit() and int(s) in allowed]
        done = intro_drill.overload(db, g.current_user_id, int(test['language_id']), ids)
        return api_success(data={'started': done})
    except Exception as e:
        logger.error("Error admitting prestudy overflow for %s: %s", identifier, e)
        return server_error('Failed to add words')


@tests_bp.route('/<identifier>/prestudy/produce', methods=['POST'])
@supabase_jwt_required
def start_test_prestudy_produce(identifier):
    """Produce: open a dual-translation passage on the window of this test with
    the most primed senses (tie-break: senses behind wrong questions, then
    shorter). Requires an attempt (DT's rule). Body: {l1_language_id?}.

    Returns the same object as POST /api/dual-translation/passage-from-sentences
    plus ``sentence_start``/``sentence_end``; 422 NO_WINDOW when no 2-4
    sentence window has usable references in the learner's language.
    """
    try:
        db = current_app.supabase_service
        if not db:
            return service_unavailable("Service not available")
        test = _find_test_for_prestudy(db, identifier)
        if not test:
            return not_found("Test not found")
        from services import prestudy
        from services.vocabulary.gloss_lookup import get_user_definition_language_id
        user_id = g.current_user_id
        body = request.get_json(silent=True) or {}
        try:
            l1 = int(body.get('l1_language_id') or get_user_definition_language_id(db, user_id) or 2)
        except (TypeError, ValueError):
            return bad_request("l1_language_id must be a language id")
        if l1 == int(test['language_id']):
            l1 = 2 if int(test['language_id']) != 2 else None
        if not l1:
            return api_error("No reference language for this test", 422, error_code="NO_WINDOW")
        attempt_id, wrong = prestudy.wrong_question_senses(db, user_id, test['id'])
        if not attempt_id:
            return forbidden("Take the test before Produce")
        prime = prestudy.latest_prime_session(db, user_id, test['id'])
        primed = [int(s) for s in ((prime or {}).get('words_quizzed') or [])]
        if not primed:
            # prime skipped or not recorded: target the words the client says
            # were unknown (still restricted to this test's senses below)
            primed = [int(s) for s in (body.get('fallback_sense_ids') or []) if str(s).isdigit()][:24]
        allowed = prestudy.test_sense_ids(db, test)
        primed = [s for s in primed if s in allowed][:24]
        window = prestudy.choose_produce_window(db, test, l1, primed, wrong)
        if not window:
            return api_error("No sentence window with references in your language", 422, error_code="NO_WINDOW")
        from routes.dual_translation import open_range_passage
        return open_range_passage(
            db, user_id, str(test['id']), window[0], window[1], l1, primed,
            extra={'sentence_start': window[0], 'sentence_end': window[1], 'test_id': test['id']},
        )
    except Exception as e:
        logger.error("Error starting Produce for %s: %s", identifier, e)
        logger.error(traceback.format_exc())
        return server_error('Failed to start Produce')
