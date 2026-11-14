"""Test catalogue: moderation, recommendations, daily load, lists, opening a
test and attempt history."""

from flask import request, current_app, g
import logging

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from routes.common import get_db
from services import attempts
from services.ai_service import ModerationServiceError
from services.test_service import (
    TestService, NoMatchingAttemptError, get_test_service, parse_language_id,
    get_test_content, get_test_skill_ratings, list_tests_with_ratings,
)
from utils.responses import (
    api_errors, api_success, bad_request, not_found, server_error,
    service_unavailable, unauthorized,
)
from utils.validation import json_body

from .blueprint import tests_bp

logger = logging.getLogger("routes.tests")


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


@tests_bp.route('/moderate', methods=['POST'])
@supabase_jwt_required
def moderate_content():
    """Check content using OpenAI moderation API via OpenAI service"""
    try:
        if not current_app.openai_service:
            return server_error("OpenAI service not available")

        data = json_body(silent=True)
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
    result = get_db().rpc('get_recommended_test', {
        'p_user_id': user_id,
        'p_language_id': language_id
    }).execute()

    test = result.data[0] if result.data else None
    if not test:
        return not_found("No tests available at your level")

    return api_success(data={"test": test})


@tests_bp.route('/recommended', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to fetch recommended tests")
def get_recommended_tests():
    """Get recommended tests based on user's ELO ratings."""
    user_id = g.current_user_id
    language_id_param = request.args.get('language_id')

    language_id = parse_language_id(language_id_param)
    if not language_id:
        return bad_request("Invalid or missing language_id")

    result = get_db().rpc('get_recommended_tests', {
        'p_user_id': user_id,
        'p_language_id': language_id
    }).execute()

    return api_success(data={"recommended_tests": result.data or []})


@tests_bp.route('/daily-load', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to fetch daily load")
def get_daily_load():
    """Get or compute today's daily test load for the user."""
    user_id = g.current_user_id
    language_id_param = request.args.get('language_id')

    language_id = parse_language_id(language_id_param)
    if not language_id:
        return bad_request("Invalid or missing language_id")

    test_service = get_test_service()
    daily_load = test_service.get_or_create_daily_load(user_id, language_id)

    return api_success(data={"daily_load": daily_load})


@tests_bp.route('/daily-load/complete', methods=['POST'])
@supabase_jwt_required
@api_errors("Failed to mark daily test complete")
def complete_daily_load_test():
    """Mark a test as completed in today's daily load."""
    user_id = g.current_user_id
    data = json_body(silent=True)

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


@tests_bp.route('/', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to fetch tests")
def get_tests_with_ratings():
    """Get tests list with ELO ratings for filtering/preview."""
    language_id_param = request.args.get('language_id')
    difficulty = request.args.get('difficulty')
    limit = request.args.get('limit', 50, type=int) or 50

    tests_with_ratings = list_tests_with_ratings(
        get_db(),
        language_id=parse_language_id(language_id_param),
        difficulty=difficulty, limit=limit,
    )

    return api_success(data={"tests": tests_with_ratings})

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
@api_errors("Failed to fetch test")
def get_test(slug):
    """Get a test by slug in the shape expected by the Flutter app."""
    test_service = get_test_service()
    test_data = test_service.get_test_by_slug(slug)
    if not test_data:
        return not_found("Test not found")

    normalize_audio_url(test_data)

    from middleware.auth import get_optional_user_id
    user_id = get_optional_user_id(request)
    if user_id and _transcript_withheld_for(
            get_db(), user_id, test_data):
        test_data['transcript'] = ''

    logger.debug(f"Returning test data for slug: {slug}")
    response = api_success(data={"test": test_data})
    return response if user_id else _public_cacheable(response)


@tests_bp.route('/test/<identifier>', methods=['GET'])
#@supabase_jwt_required
@api_errors("Failed to fetch test")
def get_test_with_ratings(identifier):
    """Get test with ELO ratings for preview/taking. Accepts slug or UUID."""
    db = get_db()

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


@tests_bp.route('/history', methods=['GET'])
@supabase_jwt_required
@api_errors('Failed to get test history')
def get_test_history():
    """Get user's test attempt history with manual join"""
    user_id = g.current_user_id
    if not user_id:
        return unauthorized("User ID not found")

    history = attempts.list_test_history(
        get_db(),
        get_db(),
        user_id,
        language_id=request.args.get('language_id', type=int),
        test_type_id=request.args.get('test_type_id', type=int),
        limit=min(request.args.get('limit', 25, type=int) or 25, 100),
        offset=max(request.args.get('offset', 0, type=int) or 0, 0),
    )
    return api_success(data={'tests': history})
