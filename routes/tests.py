# routes/tests.py
"""Test routes - handles test CRUD, generation, and submission."""

from flask import Blueprint, request, jsonify, current_app, make_response, g
from uuid import uuid4
from datetime import datetime, timezone
import traceback
import logging

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from services.ai_service import ModerationServiceError
from services.test_service import (
    TestService, DimensionService, get_test_service,
    parse_language_id, VALID_LANGUAGE_IDS
)
from services.vocabulary.knowledge_service import VocabularyKnowledgeService
from utils.responses import (
    api_success, api_error, bad_request, not_found, server_error,
    service_unavailable, unauthorized,
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
    except Exception as e:
        logger.error(f"Error marking daily test complete: {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to mark daily test complete")


@tests_bp.route('/generate_test', methods=['POST'])
@supabase_jwt_required
def generate_test():
    """Generate a new test and save to Supabase database"""
    try:
        current_user_id = g.current_user_id
        current_user_email = g.supabase_claims.get('email')

        # Handle batch operations using service role key
        # Replace 'service-account' with a special UUID for batch-generated tests
        if current_user_id == 'service-account':
            # Use a well-known UUID for batch operations (00000000-0000-0000-0000-000000000001)
            current_user_id = '00000000-0000-0000-0000-000000000001'

        if not current_app.openai_service:
            return service_unavailable("AI service not available")

        if not current_app.supabase_service:
            return service_unavailable("Database service not connected")

        if request.method == 'OPTIONS':
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = ','.join(Config.CORS_ORIGINS)
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
            return response

        data = request.get_json(silent=True) or {}

        if not data:
            return bad_request("No JSON data provided")

        language = data.get('language')
        difficulty = data.get('difficulty')
        topic = data.get('topic')
        style = data.get('style', 'academic')
        tier = data.get('tier', 'free-tier')

        if not all([language, difficulty, topic]):
            return bad_request("Missing required fields: language, difficulty, topic")
        try:
            transcript = current_app.openai_service.generate_transcript(language, topic, difficulty, style)
        except Exception as e:
            current_app.logger.error(f"Transcript generation error: {e}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            return api_error(
                f"Failed to generate transcript: {str(e)}",
                500,
                details={"step": "transcript_generation"},
            )

        try:
            questions = current_app.openai_service.generate_questions(transcript, language, difficulty)
        except Exception as e:
            current_app.logger.error(f"Question generation error: {e}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            return api_error(
                f"Failed to generate questions: {str(e)}",
                500,
                details={"step": "question_generation"},
            )

        slug = str(uuid4())
        title = data.get('title') or f"{topic}"
        
        test_data = {
            'slug': slug,
            'language': language,
            'topic': topic,
            'difficulty': difficulty,
            'style': style,
            'tier': tier,
            'title': title,
            'transcript': transcript,
            'audio_url': '',
            'total_attempts': 0,
            'is_active': True,
            'is_featured': data.get('is_featured', False),
            'is_custom': False,
            'generation_model': data.get('generation_model', 'gpt-4'),
            'audio_generated': False,
            'gen_user': current_user_id,
            'questions': questions,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }

        try:
            test_service = get_test_service()
            test_id = test_service.save_test(test_data, current_user_id)
        except Exception as e:
            current_app.logger.error(f"Database save error: {e}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            return api_error(
                f"Failed to save test: {str(e)}",
                500,
                details={"step": "database_save"},
            )
        audio_success = False
        audio_url = ""

        try:
            if current_app.openai_service and hasattr(current_app.openai_service, 'generate_audio'):
                audio_result = current_app.openai_service.generate_audio(transcript, slug)
                if audio_result:
                    audio_success = True
                    audio_url = current_app.r2_service.get_audio_url(slug)
                    current_app.supabase_service.table('tests').update({
                        'audio_generated': True,
                        'audio_url': audio_url,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }).eq('id', test_id).execute()
        except Exception as e:
            current_app.logger.warning(f"Audio generation failed (non-critical): {e}")
        try:
            saved_test_result = current_app.supabase_service.table('tests').select(
                'id, slug, title, language_id, topic_id, difficulty, style, tier, '
                'audio_url, audio_generated, is_custom, is_featured, total_attempts, '
                'dim_languages(language_code, language_name)'
            ).eq('id', test_id).execute()

            ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
                'test_type_id, elo_rating, total_attempts, dim_test_types(type_code)'
            ).eq('test_id', test_id).execute()

            skill_ratings = {}
            flat_ratings = {}
            for rating in ratings_result.data:
                type_code = rating.get('dim_test_types', {}).get('type_code', 'unknown')
                skill_ratings[type_code] = {
                    'elo_rating': rating['elo_rating'],
                    'total_attempts': rating['total_attempts']
                }
                flat_ratings[f'{type_code}_rating'] = rating['elo_rating']

            if saved_test_result.data:
                test_data = saved_test_result.data[0]
                # Add language name for backwards compatibility
                lang_info = test_data.pop('dim_languages', {}) or {}
                test_data['language'] = lang_info.get('language_code', 'unknown')
                test_data['language_name'] = lang_info.get('language_name', 'Unknown')

                test_summary = {
                    **test_data,
                    'skill_ratings': skill_ratings,
                    **flat_ratings,
                }

                return api_success(
                    data={
                        "slug": slug,
                        "test_id": test_id,
                        "audio_generated": audio_success,
                        "audio_url": audio_url if audio_success else None,
                        "test_summary": test_summary,
                    },
                    message="Test generated and saved successfully",
                )

        except Exception as e:
            current_app.logger.warning(f"Could not fetch complete test summary: {e}")
        return api_success(
            data={
                "slug": slug,
                "test_id": test_id,
                "audio_generated": audio_success,
                "audio_url": audio_url if audio_success else None,
                "test_data": {
                    "language": language,
                    "difficulty": difficulty,
                    "topic": topic,
                    "style": style,
                    "tier": tier,
                    "title": title,
                    "questions_count": len(questions),
                    "is_custom": False,
                },
            },
            message="Test generated and saved to database successfully",
        )

    except Exception as e:
        current_app.logger.error(f"UNEXPECTED ERROR in generate_test: {e}")
        current_app.logger.error(f"UNEXPECTED ERROR TYPE: {type(e).__name__}")
        current_app.logger.error(f"UNEXPECTED ERROR TRACEBACK: {traceback.format_exc()}")
        return api_error(
            f"Test generation failed: {str(e)}",
            500,
            details={"step": "unexpected_error", "error_type": type(e).__name__},
        )

@tests_bp.route('/custom_test', methods=['POST'])
@supabase_jwt_required
def custom_test():
    """Create a custom test with user-provided transcript and save to Supabase"""
    try:
        current_user_id = g.current_user_id
        current_user_email = g.supabase_claims.get('email')

        # Handle batch operations using service role key
        # Replace 'service-account' with a special UUID for batch-generated tests
        if current_user_id == 'service-account':
            # Use a well-known UUID for batch operations (00000000-0000-0000-0000-000000000001)
            current_user_id = '00000000-0000-0000-0000-000000000001'

        data = request.get_json(silent=True) or {}
        if not data:
            return bad_request("No JSON data provided")

        if not current_app.openai_service:
            return server_error("OpenAI service not available")

        if not current_app.supabase_service:
            return server_error("Database service not connected")

        language = data.get('language')
        difficulty = data.get('difficulty')
        transcript = data.get('transcript', '').strip()

        if not (language and difficulty and transcript):
            return bad_request("Missing required fields: language, difficulty, and transcript")

        topic = data.get('topic', 'Custom Topic').strip()
        style = data.get('style', 'custom')
        tier = data.get('tier', 'premium-tier')

        questions = current_app.openai_service.generate_questions(transcript, language, difficulty)

        slug = str(uuid4())
        title = data.get('title') or f"Custom {language.capitalize()}: {topic}"
        test_data = {
            'slug': slug,
            'language': language,
            'topic': topic,
            'difficulty': difficulty,
            'style': style,
            'tier': tier,
            'title': title,
            'transcript': transcript,
            'audio_url': '',
            'total_attempts': 0,
            'is_active': True,
            'is_featured': data.get('is_featured', False),
            'is_custom': True,
            'generation_model': data.get('generation_model', 'gpt-4'),
            'audio_generated': False,
            'gen_user': current_user_id,
            'questions': questions,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }

        test_service = get_test_service()
        test_id = test_service.save_test(test_data, current_user_id)
        audio_success = False
        audio_url = ""

        try:
            if current_app.openai_service and hasattr(current_app.openai_service, 'generate_audio'):
                audio_result = current_app.openai_service.generate_audio(transcript, slug)

                if audio_result:
                    audio_success = True
                    audio_url = current_app.r2_service.get_audio_url(slug)

                    current_app.supabase_service.table('tests').update({
                        'audio_generated': True,
                        'audio_url': audio_url,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }).eq('id', test_id).execute()
        except Exception as e:
            current_app.logger.warning(f"Audio generation failed (non-critical): {e}")
        try:
            # Get the saved test with all fields for frontend
            saved_test_result = current_app.supabase_service.table('tests').select(
                'id, slug, title, language_id, topic_id, difficulty, style, tier, '
                'audio_url, audio_generated, is_custom, is_featured, total_attempts, '
                'dim_languages(language_code, language_name)'
            ).eq('id', test_id).execute()

            # Get the skill ratings with FK join to dim_test_types
            ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
                'test_type_id, elo_rating, total_attempts, dim_test_types(type_code)'
            ).eq('test_id', test_id).execute()

            # Transform ratings
            skill_ratings = {}
            flat_ratings = {}
            for rating in ratings_result.data:
                type_code = rating.get('dim_test_types', {}).get('type_code', 'unknown')
                skill_ratings[type_code] = {
                    'elo_rating': rating['elo_rating'],
                    'total_attempts': rating['total_attempts']
                }
                flat_ratings[f'{type_code}_rating'] = rating['elo_rating']

            if saved_test_result.data:
                test_data = saved_test_result.data[0]
                # Add language name for backwards compatibility
                lang_info = test_data.pop('dim_languages', {}) or {}
                test_data['language'] = lang_info.get('language_code', 'unknown')
                test_data['language_name'] = lang_info.get('language_name', 'Unknown')

                test_summary = {
                    **test_data,
                    'skill_ratings': skill_ratings,
                    **flat_ratings,  # Add flat ratings for compatibility
                }

                return api_success(
                    data={
                        "slug": slug,
                        "test_id": test_id,
                        "audio_generated": audio_success,
                        "audio_url": audio_url if audio_success else None,
                        "test_summary": test_summary,
                    },
                    message="Custom test created and saved successfully",
                )
        except Exception as e:
            current_app.logger.warning(f"⚠️ Could not fetch complete test summary: {e}")

        # Fallback response
        return api_success(
            data={
                "slug": slug,
                "test_id": test_id,
                "audio_generated": audio_success,
                "audio_url": audio_url if audio_success else None,
                "test_data": {
                    "language": language,
                    "difficulty": difficulty,
                    "topic": topic,
                    "style": style,
                    "tier": tier,
                    "title": title,
                    "custom": True,
                    "is_custom": True,
                    "questions_count": len(questions),
                },
            },
            message="Custom test created and saved to database successfully",
        )

    except Exception as e:
        current_app.logger.error(f"Custom test error: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return server_error("Failed to create custom test")




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

        logger.debug(f"Returning test data for slug: {slug}")
        return api_success(data={"test": test_data})

    except Exception as e:
        current_app.logger.error(f"Error in get_test route: {e}")
        return server_error("Failed to fetch test")
        
def _apply_timing_and_progress(client, attempt_id, request_body):
    """Post-submission hook — persist timing + bump Study Plan counter.

    Phase 13. Best-effort: failures are logged but never bubble up to the
    learner, who has already received their submission result. Both
    timestamps are optional; missing timestamps mean the FE didn't capture
    them (older clients) and we skip the duration UPDATE while still
    incrementing the test counter.

    Args:
        client: Supabase service client.
        attempt_id: UUID returned by the submission RPC.
        request_body: the request JSON dict (we read started_at /
            finished_at from it).

    See migrations/phase13_apply_attempt_timing_and_progress.sql.
    """
    if not attempt_id:
        return
    started_at  = request_body.get('started_at')   # ISO timestamp or None
    finished_at = request_body.get('finished_at')
    try:
        client.rpc('apply_attempt_timing_and_progress', {
            'p_attempt_id':  str(attempt_id),
            'p_started_at':  started_at,
            'p_finished_at': finished_at,
        }).execute()
    except Exception as e:
        # Non-fatal — timing capture and Study Plan counters are best-effort.
        current_app.logger.warning(
            f"apply_attempt_timing_and_progress failed (non-fatal) for "
            f"attempt={attempt_id}: {e}"
        )


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
    return _submission_failure_response(rpc_name, response_data)


def _call_submission_rpc(client, user_id, test_id, language_id, test_type_id, db_responses, furigana_used=False):
    """Call the process_test_submission RPC and handle JSONB response quirks.

    Returns the parsed RPC result dict on success, or a
    ``(jsonify_response, status_code)`` tuple on failure. Failure envelopes
    never include SQLERRM text — see CR-04.
    """
    def _on_success(data):
        current_app.logger.info(
            "process_test_submission succeeded: attempt_id=%s",
            data.get('attempt_id'),
        )

    try:
        response = client.rpc('process_test_submission', {
            'p_user_id': user_id,
            'p_test_id': test_id,
            'p_language_id': language_id,
            'p_test_type_id': test_type_id,
            'p_responses': db_responses,
            'p_was_free_test': True,
            'p_idempotency_key': str(uuid4()),
            'p_furigana_used': bool(furigana_used),
        }).execute()
    except Exception as e:
        # supabase-py raises on JSONB responses; rescue the payload here so
        # we can dispatch both success and failure paths uniformly.
        error_data = e.json() if hasattr(e, 'json') else (e.args[0] if e.args else {})
        return _unwrap_rpc_response('process_test_submission', error_data, _on_success)

    return _unwrap_rpc_response('process_test_submission', response.data, _on_success)


def _call_dictation_submission_rpc(
    client, user_id, test_id, language_id, test_type_id,
    word_correct, word_total, replay_count, diff_payload, idempotency_key,
):
    """Call the process_dictation_submission RPC. See _call_submission_rpc
    for the CR-04 envelope contract."""
    def _on_success(data):
        current_app.logger.info(
            "process_dictation_submission succeeded: attempt_id=%s",
            data.get('attempt_id'),
        )

    try:
        response = client.rpc('process_dictation_submission', {
            'p_user_id': user_id,
            'p_test_id': test_id,
            'p_language_id': language_id,
            'p_test_type_id': test_type_id,
            'p_word_correct': int(word_correct),
            'p_word_total': int(word_total),
            'p_replay_count': int(replay_count),
            'p_diff_payload': diff_payload,
            'p_was_free_test': True,
            'p_idempotency_key': str(idempotency_key) if idempotency_key else str(uuid4()),
        }).execute()
    except Exception as e:
        error_data = e.json() if hasattr(e, 'json') else (e.args[0] if e.args else {})
        return _unwrap_rpc_response('process_dictation_submission', error_data, _on_success)

    return _unwrap_rpc_response('process_dictation_submission', response.data, _on_success)


def _call_pinyin_submission_rpc(client, user_id, test_id, language_id, test_type_id, correct_chars, total_chars):
    """Call the process_pinyin_submission RPC. See _call_submission_rpc
    for the CR-04 envelope contract."""
    def _on_success(data):
        current_app.logger.info(
            "process_pinyin_submission succeeded: attempt_id=%s",
            data.get('attempt_id'),
        )

    try:
        response = client.rpc('process_pinyin_submission', {
            'p_user_id': user_id,
            'p_test_id': test_id,
            'p_language_id': language_id,
            'p_test_type_id': test_type_id,
            'p_correct_chars': int(correct_chars),
            'p_total_chars': int(total_chars),
            'p_was_free_test': True,
            'p_idempotency_key': str(uuid4()),
        }).execute()
    except Exception as e:
        error_data = e.json() if hasattr(e, 'json') else (e.args[0] if e.args else {})
        return _unwrap_rpc_response('process_pinyin_submission', error_data, _on_success)

    return _unwrap_rpc_response('process_pinyin_submission', response.data, _on_success)


def _call_pitch_accent_submission_rpc(client, user_id, test_id, language_id, test_type_id, correct_units, total_units, furigana_used=False):
    """Call the process_pitch_accent_submission RPC. See _call_submission_rpc
    for the CR-04 envelope contract."""
    def _on_success(data):
        current_app.logger.info(
            "process_pitch_accent_submission succeeded: attempt_id=%s",
            data.get('attempt_id'),
        )

    try:
        response = client.rpc('process_pitch_accent_submission', {
            'p_user_id': user_id,
            'p_test_id': test_id,
            'p_language_id': language_id,
            'p_test_type_id': test_type_id,
            'p_correct_units': int(correct_units),
            'p_total_units': int(total_units),
            'p_was_free_test': True,
            'p_idempotency_key': str(uuid4()),
            'p_furigana_used': bool(furigana_used),
        }).execute()
    except Exception as e:
        error_data = e.json() if hasattr(e, 'json') else (e.args[0] if e.args else {})
        return _unwrap_rpc_response('process_pitch_accent_submission', error_data, _on_success)

    return _unwrap_rpc_response('process_pitch_accent_submission', response.data, _on_success)


def _update_vocabulary_tracking(user_id, test_id, language_id, rpc_result):
    """Run BKT vocabulary tracking and build a word quiz from question results.

    Returns a word_quiz dict or None. Failures are logged but never raised.
    """
    try:
        question_results_raw = rpc_result.get('question_results', [])
        current_app.logger.info(f"BKT: {len(question_results_raw)} question results from RPC")

        if not question_results_raw:
            return None

        bkt_question_results = [
            {'question_id': str(qr['question_id']), 'is_correct': qr.get('is_correct', False)}
            for qr in question_results_raw
            if qr.get('question_id')
        ]
        current_app.logger.info(f"BKT: {len(bkt_question_results)} valid question results")

        if not bkt_question_results:
            return None

        knowledge_svc = VocabularyKnowledgeService()
        vocab_updates = knowledge_svc.update_from_comprehension(
            user_id=user_id, language_id=language_id, question_results=bkt_question_results,
        )
        current_app.logger.info(f"BKT: {len(vocab_updates)} vocab updates returned")

        # Contextual inference: dampened update for transcript words not directly tested
        score = rpc_result.get('score', 0)
        total = rpc_result.get('total_questions', 1) or 1
        score_ratio = score / total
        contextual_count = knowledge_svc.apply_contextual_inference(
            user_id=user_id, language_id=language_id,
            test_id=str(test_id),
            question_results=bkt_question_results,
            score_ratio=score_ratio,
        )
        if contextual_count:
            current_app.logger.info(f"BKT: {contextual_count} contextual senses boosted")

        # Collect all sense_ids from questions for quiz candidate selection
        all_sense_ids = set()
        questions_resp = knowledge_svc.db.table('questions') \
            .select('sense_ids').eq('test_id', str(test_id)).execute()
        for q in (questions_resp.data or []):
            if q.get('sense_ids'):
                all_sense_ids.update(q['sense_ids'])

        current_app.logger.info(f"BKT: {len(all_sense_ids)} unique sense_ids from questions")

        if not all_sense_ids:
            current_app.logger.warning("BKT: No sense_ids on questions — run backfill_question_sense_ids.py")
            return None

        quiz_candidates = knowledge_svc.build_quiz_with_distractors(
            user_id=user_id, sense_ids=list(all_sense_ids),
            language_id=language_id, max_words=5,
        )
        current_app.logger.info(f"BKT: {len(quiz_candidates)} quiz candidates with distractors")

        if quiz_candidates:
            attempt_id = rpc_result.get('attempt_id')
            return {
                'candidates': quiz_candidates,
                'attempt_id': str(attempt_id) if attempt_id else None,
            }
        return None

    except Exception as e:
        current_app.logger.error(f"BKT/word quiz failed (non-fatal): {e}\n{traceback.format_exc()}")
        return None


def _build_submission_response(rpc_result, test_mode, word_quiz):
    """Construct the API response dict from RPC results and optional word quiz."""
    attempt_id = rpc_result.get('attempt_id')
    result = {
        'score': rpc_result.get('score'),
        'total_questions': rpc_result.get('total_questions'),
        'percentage': rpc_result.get('percentage'),
        'question_results': rpc_result.get('question_results', []),
        'is_first_attempt': rpc_result.get('is_first_attempt', True),
        'user_elo_change': {
            'before': rpc_result.get('user_elo_before'),
            'after': rpc_result.get('user_elo_after'),
            'change': rpc_result.get('user_elo_change', 0)
        },
        'test_elo_change': {
            'before': rpc_result.get('test_elo_before'),
            'after': rpc_result.get('test_elo_after'),
            'change': rpc_result.get('test_elo_change', 0)
        },
        'elo_reduction_factor': rpc_result.get('elo_reduction_factor'),
        'test_mode': test_mode,
        'attempt_id': str(attempt_id) if attempt_id else None,
    }
    if word_quiz:
        result['word_quiz'] = word_quiz
    return result


@tests_bp.route('/<slug>/submit', methods=['POST'])
@supabase_jwt_required
def submit_test_attempt(slug):
    """Submit test answers and calculate ELO changes with idempotency support"""
    try:
        if not current_app.supabase_service:
            return server_error("Database service not configured")

        current_user_id = g.current_user_id

        data = request.get_json() or {}
        responses = data.get('responses', [])
        test_mode = data.get('test_mode', 'reading').lower()
        furigana_used = bool(data.get('furigana_used', False))

        if not responses:
            return bad_request("No responses provided")

        # Lightweight test lookup (just id and language_id, no questions)
        test_lookup = current_app.supabase_service.table('tests')\
            .select('id, language_id')\
            .eq('slug', slug)\
            .eq('is_active', True)\
            .single()\
            .execute()

        if not test_lookup.data:
            return not_found(f"Test not found: {slug}")

        test_id = test_lookup.data['id']
        language_id = test_lookup.data['language_id']

        # Get test_type_id from the test_mode using DimensionService cache
        test_type_id = DimensionService.get_test_type_id(test_mode)
        if not test_type_id:
            logger.warning(f"Unknown test_mode '{test_mode}', defaulting to reading")
            test_type_id = DimensionService.get_test_type_id('reading') or 1

        # Transform responses: strip 'is_correct' field (DB will calculate)
        db_responses = [
            {"question_id": str(r['question_id']), "selected_answer": r['selected_answer']}
            for r in responses
        ]

        # Call database RPC for validation, ELO calculation and attempt recording
        rpc_result = _call_submission_rpc(
            current_app.supabase_service, current_user_id,
            test_id, language_id, test_type_id, db_responses,
            furigana_used=furigana_used,
        )
        if isinstance(rpc_result, tuple):
            return rpc_result  # Error response

        # Validate the result. The wrapper above already converts any
        # {success:false} payload into the generic envelope tuple, so this
        # branch is a belt-and-suspenders guard. Do NOT forward error_msg
        # to the client — it may contain SQLERRM text (CR-04).
        if not rpc_result or not rpc_result.get('success'):
            error_msg = rpc_result.get('error', 'Unknown error') if rpc_result else 'RPC failed'
            error_detail = rpc_result.get('error_detail', '') if rpc_result else ''
            current_app.logger.error(f"ELO RPC failed: {error_msg} (detail: {error_detail})")
            return server_error("submission_failed")

        current_app.logger.info(
            f"Test submitted: user={current_user_id}, test={test_id}, "
            f"attempt={rpc_result.get('attempt_id')}, "
            f"score={rpc_result.get('score', 0)}/{rpc_result.get('total_questions', 0)}"
        )

        # Phase 13 — persist timing + bump Study Plan counter (best-effort).
        _apply_timing_and_progress(
            current_app.supabase_service, rpc_result.get('attempt_id'), data,
        )

        # BKT vocabulary tracking
        word_quiz = _update_vocabulary_tracking(current_user_id, test_id, language_id, rpc_result)

        result = _build_submission_response(rpc_result, test_mode, word_quiz)
        return api_success(data={'result': result})

    except Exception as e:
        current_app.logger.error(f"Test submission error: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return server_error('Failed to submit test')


@tests_bp.route('/<slug>/submit-pinyin', methods=['POST'])
@supabase_jwt_required
def submit_pinyin_attempt(slug):
    """Submit pinyin tone trainer results.

    Accepts accuracy-based scoring (correct_chars / total_chars) and delegates
    to process_pinyin_submission, which records the attempt and updates ELO
    without referencing the test's MC questions.
    """
    try:
        if not current_app.supabase_service:
            return server_error("Database service not configured")

        current_user_id = g.current_user_id
        data = request.get_json() or {}

        correct_chars = data.get('correct_chars', 0)
        total_chars = data.get('total_chars', 0)
        time_taken = data.get('time_taken', 0)

        if total_chars <= 0:
            return bad_request("Invalid total_chars")

        accuracy = correct_chars / total_chars

        # Look up test
        test_lookup = current_app.supabase_service.table('tests') \
            .select('id, language_id') \
            .eq('slug', slug) \
            .eq('is_active', True) \
            .single() \
            .execute()

        if not test_lookup.data:
            return not_found(f"Test not found: {slug}")

        test_id = test_lookup.data['id']
        language_id = test_lookup.data['language_id']

        if language_id != 1:
            return bad_request("Pinyin mode is only available for Chinese tests")

        pinyin_type_id = DimensionService.get_test_type_id('pinyin')
        if not pinyin_type_id:
            return server_error("Pinyin test type not configured")

        rpc_result = _call_pinyin_submission_rpc(
            current_app.supabase_service, current_user_id,
            test_id, language_id, pinyin_type_id,
            correct_chars, total_chars,
        )
        if isinstance(rpc_result, tuple):
            return rpc_result

        if not rpc_result or not rpc_result.get('success'):
            error_msg = rpc_result.get('error', 'Unknown error') if rpc_result else 'RPC failed'
            current_app.logger.error(f"Pinyin RPC failed: {error_msg}")
            return server_error("Failed to process pinyin submission")

        # Phase 13 — persist timing + bump Study Plan counter (best-effort).
        _apply_timing_and_progress(
            current_app.supabase_service, rpc_result.get('attempt_id'), data,
        )

        result = {
            'accuracy': round(accuracy * 100, 1),
            'correct_chars': correct_chars,
            'total_chars': total_chars,
            'time_taken': time_taken,
            'user_elo_change': {
                'before': rpc_result.get('user_elo_before'),
                'after': rpc_result.get('user_elo_after'),
                'change': rpc_result.get('user_elo_change', 0)
            },
            'test_elo_change': {
                'before': rpc_result.get('test_elo_before'),
                'after': rpc_result.get('test_elo_after'),
                'change': rpc_result.get('test_elo_change', 0)
            },
            'test_mode': 'pinyin',
            'attempt_id': str(rpc_result.get('attempt_id')) if rpc_result.get('attempt_id') else None,
        }

        return api_success(data={'result': result})

    except Exception as e:
        current_app.logger.error(f"Pinyin submission error: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return server_error('Failed to submit pinyin test')


@tests_bp.route('/<slug>/submit-pitch-accent', methods=['POST'])
@supabase_jwt_required
def submit_pitch_accent_attempt(slug):
    """Submit pitch accent trainer results.

    Accepts accuracy-based scoring (correct_units / total_units, one unit per
    accent phrase) and delegates to process_pitch_accent_submission, which
    records the attempt and updates ELO without referencing the test's MC
    questions.
    """
    try:
        if not current_app.supabase_service:
            return server_error("Database service not configured")

        current_user_id = g.current_user_id
        data = request.get_json() or {}

        correct_units = data.get('correct_units', 0)
        total_units = data.get('total_units', 0)
        time_taken = data.get('time_taken', 0)
        furigana_used = bool(data.get('furigana_used', False))

        if total_units <= 0:
            return bad_request("Invalid total_units")

        accuracy = correct_units / total_units

        test_lookup = current_app.supabase_service.table('tests') \
            .select('id, language_id') \
            .eq('slug', slug) \
            .eq('is_active', True) \
            .single() \
            .execute()

        if not test_lookup.data:
            return not_found(f"Test not found: {slug}")

        test_id = test_lookup.data['id']
        language_id = test_lookup.data['language_id']

        if language_id != 3:
            return bad_request("Pitch accent mode is only available for Japanese tests")

        pitch_type_id = DimensionService.get_test_type_id('pitch_accent')
        if not pitch_type_id:
            return server_error("Pitch accent test type not configured")

        rpc_result = _call_pitch_accent_submission_rpc(
            current_app.supabase_service, current_user_id,
            test_id, language_id, pitch_type_id,
            correct_units, total_units,
            furigana_used=furigana_used,
        )
        if isinstance(rpc_result, tuple):
            return rpc_result

        if not rpc_result or not rpc_result.get('success'):
            error_msg = rpc_result.get('error', 'Unknown error') if rpc_result else 'RPC failed'
            current_app.logger.error(f"Pitch accent RPC failed: {error_msg}")
            return server_error("Failed to process pitch accent submission")

        # Phase 13 — persist timing + bump Study Plan counter (best-effort).
        _apply_timing_and_progress(
            current_app.supabase_service, rpc_result.get('attempt_id'), data,
        )

        result = {
            'accuracy': round(accuracy * 100, 1),
            'correct_units': correct_units,
            'total_units': total_units,
            'time_taken': time_taken,
            'user_elo_change': {
                'before': rpc_result.get('user_elo_before'),
                'after': rpc_result.get('user_elo_after'),
                'change': rpc_result.get('user_elo_change', 0)
            },
            'test_elo_change': {
                'before': rpc_result.get('test_elo_before'),
                'after': rpc_result.get('test_elo_after'),
                'change': rpc_result.get('test_elo_change', 0)
            },
            'test_mode': 'pitch_accent',
            'attempt_id': str(rpc_result.get('attempt_id')) if rpc_result.get('attempt_id') else None,
        }

        return api_success(data={'result': result})

    except Exception as e:
        current_app.logger.error(f"Pitch accent submission error: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return server_error('Failed to submit pitch accent test')


@tests_bp.route('/<slug>/submit-dictation', methods=['POST'])
@supabase_jwt_required
def submit_dictation_attempt(slug):
    """Submit a dictation transcript for grading.

    Grades the typed transcript against the canonical one server-side via
    services.dictation.grader.grade_dictation, then calls
    process_dictation_submission to persist the attempt + update ELO, and
    finally fires per-word BKT updates for every transcript word that maps
    to a dim_word_senses row.
    """
    try:
        if not current_app.supabase_service:
            return server_error("Database service not configured")

        current_user_id = g.current_user_id
        data = request.get_json() or {}

        user_transcript = (data.get('user_transcript') or '').strip()
        replay_count = data.get('replay_count', 1)
        time_taken = data.get('time_taken', 0)
        idempotency_key = data.get('idempotency_key') or str(uuid4())

        if not user_transcript:
            return bad_request("Empty user_transcript")

        try:
            replay_count = max(1, int(replay_count))
        except (TypeError, ValueError):
            replay_count = 1

        # Fetch canonical transcript + vocab metadata server-side
        test_lookup = current_app.supabase_service.table('tests') \
            .select('id, language_id, transcript, vocab_sense_ids, vocab_token_map') \
            .eq('slug', slug) \
            .eq('is_active', True) \
            .single() \
            .execute()

        if not test_lookup.data:
            return not_found(f"Test not found: {slug}")

        test = test_lookup.data
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

        # Map canonical tokens → sense_ids via vocab_token_map.
        # Token map is a list of (surface_form, sense_id) pairs aligned to
        # the test's tokenization. We do a lemma-agnostic surface match
        # (post-normalization) on the canonical token strings.
        token_map = test.get('vocab_token_map') or []
        if token_map:
            # Build a lookup from normalized surface → sense_id.
            from services.dictation.tokenizer import normalize as _norm
            surface_to_sense = {}
            for entry in token_map:
                if not entry or len(entry) < 2:
                    continue
                surface, sense_id = entry[0], entry[1]
                if not sense_id:
                    continue
                key = _norm(str(surface))
                # First mapping wins (avoid overwriting with later duplicates)
                surface_to_sense.setdefault(key, sense_id)

            for d in result.diff:
                if d.correct:
                    d.sense_id = surface_to_sense.get(d.correct)

        diff_payload = result.diff_payload()
        # Cap stored diff at 200 entries (per plan); but full diff still
        # returned to client for the current response.
        diff_payload_stored = diff_payload[:200]

        rpc_result = _call_dictation_submission_rpc(
            current_app.supabase_service, current_user_id,
            test_id, language_id, dictation_type_id,
            result.word_correct, result.word_total, replay_count,
            diff_payload_stored, idempotency_key,
        )
        if isinstance(rpc_result, tuple):
            return rpc_result

        if not rpc_result or not rpc_result.get('success'):
            # See CR-04 — don't echo SQLERRM text into the client response.
            error_msg = rpc_result.get('error', 'Unknown error') if rpc_result else 'RPC failed'
            current_app.logger.error(f"Dictation RPC failed: {error_msg}")
            return server_error("submission_failed")

        # Phase 13 — persist timing + bump Study Plan counter (best-effort).
        _apply_timing_and_progress(
            current_app.supabase_service, rpc_result.get('attempt_id'), data,
        )

        # Per-word BKT updates — single batched RPC instead of N round-trips.
        # 'insert' ops (extra user words) have no canonical sense_id and are
        # excluded; 'equal' / 'replace' / 'delete' all carry canonical-side
        # sense_ids when the token maps to a dim_word_senses row.
        try:
            word_results = [
                {'sense_id': d.sense_id, 'is_correct': bool(d.is_correct)}
                for d in result.diff
                if d.sense_id and d.op in ('equal', 'replace', 'delete')
            ]
            if word_results:
                knowledge_svc = VocabularyKnowledgeService()
                bkt_rows = knowledge_svc.update_from_word_tests_batch(
                    user_id=current_user_id,
                    language_id=language_id,
                    results=word_results,
                )
                current_app.logger.info(
                    f"Dictation BKT: user={current_user_id} test={test_id} "
                    f"{len(word_results)} inputs → {len(bkt_rows)} senses updated (batched)"
                )
        except Exception as e:
            current_app.logger.error(f"Dictation BKT update failed (non-fatal): {e}")

        response = {
            'accuracy': round(result.accuracy * 100, 1),
            'word_correct': result.word_correct,
            'word_total': result.word_total,
            'replay_count': replay_count,
            'time_taken': time_taken,
            'diff': diff_payload,
            'user_elo_change': {
                'before': rpc_result.get('user_elo_before'),
                'after': rpc_result.get('user_elo_after'),
                'change': rpc_result.get('user_elo_change', 0),
            },
            'test_elo_change': {
                'before': rpc_result.get('test_elo_before'),
                'after': rpc_result.get('test_elo_after'),
                'change': rpc_result.get('test_elo_change', 0),
            },
            'replay_factor': rpc_result.get('replay_factor'),
            'elo_reduction_factor': rpc_result.get('elo_reduction_factor'),
            'test_mode': 'dictation',
            'attempt_id': str(rpc_result.get('attempt_id')) if rpc_result.get('attempt_id') else None,
        }

        return api_success(data={'result': response})

    except Exception as e:
        current_app.logger.error(f"Dictation submission error: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return server_error('Failed to submit dictation')


@tests_bp.route('/test/<identifier>', methods=['GET'])
#@supabase_jwt_required
def get_test_with_ratings(identifier):
    """Get test with ELO ratings for preview/taking. Accepts slug or UUID."""
    try:
        if not current_app.supabase_service:
            return service_unavailable("Service not available")

        select_columns = (
            'id, slug, title, language_id, topic_id, difficulty, style, tier, transcript, '
            'audio_url, audio_generated, is_custom, is_featured, total_attempts, '
            'vocab_token_map, pinyin_payload, pitch_payload, furigana_payload, '
            'dim_languages(language_code, language_name)'
        )

        # Try lookup by slug first
        test_result = current_app.supabase_service.table('tests').select(
            select_columns
        ).eq('slug', identifier).eq('is_active', True).execute()

        # If not found by slug, try by id (UUID)
        if not test_result.data:
            test_result = current_app.supabase_service.table('tests').select(
                select_columns
            ).eq('id', identifier).eq('is_active', True).execute()

        if not test_result.data:
            return not_found("Test not found")

        test = test_result.data[0]
        test_id = test['id']

        # Add language info for backwards compatibility
        lang_info = test.pop('dim_languages', {}) or {}
        test['language'] = lang_info.get('language_code', 'unknown')
        test['language_name'] = lang_info.get('language_name', 'Unknown')

        # Withhold transcript pre-submit in dictation mode — the entire point
        # is that the learner types what they hear without seeing the text.
        mode = (request.args.get('mode') or '').lower()
        if mode == 'dictation':
            test.pop('transcript', None)
            test.pop('vocab_token_map', None)

        normalize_audio_url(test)

        # Get questions
        questions_result = current_app.supabase_service.table('questions').select(
            'id, question_id, question_text, question_type_id, choices, '
            'answer, answer_explanation, points, audio_url'
        ).eq('test_id', test_id).execute()

        # Get ELO ratings with FK join to dim_test_types
        ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
            'test_type_id, elo_rating, total_attempts, dim_test_types(type_code)'
        ).eq('test_id', test_id).execute()

        # Transform ratings into a dictionary
        ratings = {
            rating.get('dim_test_types', {}).get('type_code', 'unknown'): {
                'elo_rating': rating['elo_rating'],
                'total_attempts': rating['total_attempts']
            }
            for rating in ratings_result.data
        }
        
        # Pop pinyin payload (only present for Chinese tests)
        pinyin_payload = test.pop('pinyin_payload', None)
        # Pop pitch accent payload (only present for Japanese tests)
        pitch_payload = test.pop('pitch_payload', None)
        # Pop furigana payload (only present for Japanese tests)
        furigana_payload = test.pop('furigana_payload', None)

        # Load definitions for vocab token map sense IDs
        token_map = test.pop('vocab_token_map', None) or []
        definitions = {}
        if token_map:
            sense_ids = list(set(s for _, s in token_map if s))
            if sense_ids:
                senses_result = current_app.supabase_service.table('dim_word_senses').select(
                    'id, definition, pronunciation, '
                    'dim_vocabulary(lemma, part_of_speech)'
                ).in_('id', sense_ids).execute()
                for sense in (senses_result.data or []):
                    vocab = sense.get('dim_vocabulary') or {}
                    definitions[str(sense['id'])] = {
                        'word': vocab.get('lemma', ''),
                        'definition': sense.get('definition', ''),
                        'part_of_speech': vocab.get('part_of_speech', ''),
                        'reading': sense.get('pronunciation')
                    }

        # Build response
        response_data = {
            "test_data": test,
            "questions_data": questions_result.data,
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

        return api_success(data=response_data)

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

        language_id = request.args.get('language_id', type=int)
        test_type_id = request.args.get('test_type_id', type=int)
        limit = min(request.args.get('limit', 25, type=int) or 25, 100)
        offset = max(request.args.get('offset', 0, type=int) or 0, 0)

        client = current_app.supabase_service or current_app.supabase

        query = client.table('test_attempts')\
            .select('id, test_id, score, total_questions, percentage, user_elo_after, created_at, test_type_id, elo_reduction_factor')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)

        if language_id:
            query = query.eq('language_id', language_id)
        if test_type_id:
            query = query.eq('test_type_id', test_type_id)

        attempts_result = query.execute()
        attempts = attempts_result.data or []

        if not attempts:
            return api_success(data={'tests': []})

        test_ids = list(set(a['test_id'] for a in attempts))

        tests_map = {}
        if test_ids and current_app.supabase_service:
            tests_result = current_app.supabase_service.table('tests')\
                .select('id, title, slug')\
                .in_('id', test_ids)\
                .execute()
            for t in tests_result.data or []:
                tests_map[t['id']] = t

        type_map = {}
        try:
            types_res = client.table('dim_test_types').select('id, type_name').execute()
            for t in types_res.data or []:
                type_map[t['id']] = t['type_name']
        except Exception as e:
            logger.debug(f"dim_test_types lookup skipped: {e}")

        history = []
        for attempt in attempts:
            test_id = attempt['test_id']
            test_detail = tests_map.get(test_id, {})
            type_name = type_map.get(attempt['test_type_id'], 'Unknown')

            history.append({
                'id': attempt['id'],
                'test_id': test_id,
                'test_title': test_detail.get('title', 'Unknown Test'),
                'test_slug': test_detail.get('slug', ''),
                'test_type': type_name,
                'test_type_id': attempt['test_type_id'],
                'score': attempt['score'],
                'total_questions': attempt['total_questions'],
                'percentage': attempt['percentage'],
                'user_elo_after': attempt['user_elo_after'],
                'elo_reduction_factor': attempt.get('elo_reduction_factor'),
                'created_at': attempt['created_at']
            })

        return api_success(data={'tests': history})

    except Exception as e:
        logger.error(f"Error getting test history: {e}")
        logger.error(traceback.format_exc())
        return server_error('Failed to get test history')