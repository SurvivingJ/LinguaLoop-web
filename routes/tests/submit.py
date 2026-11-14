"""Submitting a test attempt: comprehension, pinyin, pitch accent, dictation."""

from flask import request, current_app, g
from functools import wraps
from uuid import uuid4
import traceback
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from services import attempts
from services.attempt_timing import AttemptTimingError, clamp_time_taken, validate_counts
from services.concurrency import run_parallel
from services.dictation.cap import MAX_STORED_DIFF_ENTRIES
from services.test_service import DimensionService, find_active_test_by_slug
from utils.responses import api_success, api_error, bad_request, not_found, server_error

from .blueprint import tests_bp

logger = logging.getLogger("routes.tests")


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
