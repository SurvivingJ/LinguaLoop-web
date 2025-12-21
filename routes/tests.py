# routes/tests.py
"""Test routes - handles test CRUD, generation, and submission."""

from flask import Blueprint, request, jsonify, current_app, make_response, g
from uuid import uuid4
from datetime import datetime, timezone
import traceback
import random
import logging

from ..config import Config
from ..middleware.auth import jwt_required as supabase_jwt_required
from ..services.test_service import (
    TestService, DimensionService, get_test_service,
    parse_language_id, LANGUAGE_ID_TO_NAME, VALID_LANGUAGE_IDS
)

logger = logging.getLogger(__name__)
tests_bp = Blueprint("tests", __name__)


# ============================================================================
# ROUTES
# ============================================================================

@tests_bp.route('/moderate', methods=['POST'])
@supabase_jwt_required
def moderate_content():
    """Check content using OpenAI moderation API via OpenAI service"""
    try:
        if not current_app.openai_service:
            return jsonify({
                "error": "OpenAI service not available",
                "status": "error"
            }), 500
        
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({
                "error": "No content provided",
                "status": "error"
            }), 400
        
        moderation_result = current_app.openai_service.moderate_content(content)

        if moderation_result.get('error'):
            logger.warning(f"Moderation service error: {moderation_result['error']}")

        is_safe = moderation_result['is_safe']

        if not is_safe:
            current_user_email = g.supabase_claims.get('email')
            test_service = get_test_service()
            test_service.record_flagged_input(
                current_user_email,
                content,
                moderation_result.get('flagged_categories', [])
            )

        return jsonify({
            "is_safe": is_safe,
            "flagged_categories": moderation_result.get('flagged_categories', []),
            "status": "success"
        }), 200

    except Exception as e:
        logger.error(f"Moderation endpoint error: {e}")
        return jsonify({
            "error": f"Moderation failed: {str(e)}",
            "status": "error"
        }), 500

@tests_bp.route('/random', methods=['GET'])
@supabase_jwt_required
def get_random_test():
    user_id = g.supabase_claims.get('sub')
    language_id_param = request.args.get('language_id')
    skill_type = request.args.get('skill_type', 'listening')

    # Parse and validate language_id
    language_id = parse_language_id(language_id_param)
    if not language_id:
        return jsonify({"error": "Invalid or missing language_id parameter"}), 400

    # Get language name for RPC
    language = LANGUAGE_ID_TO_NAME.get(language_id, 'chinese')

    result = current_app.supabase_service.rpc('get_random_test_for_user', {
        'p_user_id': user_id,
        'p_language': language,
        'p_skill_type': skill_type
    }).execute()
    
    candidates = result.data
    if not candidates:
        return jsonify({"error": "No tests available"}), 404
    
    random_test = random.choice(candidates)
    return jsonify({"test": random_test, "status": "success"})

@tests_bp.route('/generate_test', methods=['POST'])
@supabase_jwt_required
def generate_test():
    """Generate a new test and save to Supabase database"""
    try:
        current_user_id = g.supabase_claims.get('sub')
        current_user_email = g.supabase_claims.get('email')

        # Handle batch operations using service role key
        # Replace 'service-account' with a special UUID for batch-generated tests
        if current_user_id == 'service-account':
            # Use a well-known UUID for batch operations (00000000-0000-0000-0000-000000000001)
            current_user_id = '00000000-0000-0000-0000-000000000001'

        if not current_app.openai_service:
            return jsonify({
                "error": "AI service not available",
                "status": "error"
            }), 503

        if not current_app.supabase_service:
            return jsonify({
                "error": "Database service not connected",
                "status": "error"
            }), 503

        if request.method == 'OPTIONS':
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = ','.join(Config.CORS_ORIGINS)
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
            return response

        data = request.get_json()

        if not data:
            return jsonify({
                "error": "No JSON data provided",
                "status": "error"
            }), 400

        language = data.get('language')
        difficulty = data.get('difficulty')
        topic = data.get('topic')
        style = data.get('style', 'academic')
        tier = data.get('tier', 'free-tier')

        if not all([language, difficulty, topic]):
            return jsonify({
                "error": "Missing required fields: language, difficulty, topic",
                "status": "error"
            }), 400
        try:
            transcript = current_app.openai_service.generate_transcript(language, topic, difficulty, style)
        except Exception as e:
            current_app.logger.error(f"Transcript generation error: {e}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                "error": f"Failed to generate transcript: {str(e)}",
                "status": "error",
                "step": "transcript_generation"
            }), 500

        try:
            questions = current_app.openai_service.generate_questions(transcript, language, difficulty)
        except Exception as e:
            current_app.logger.error(f"Question generation error: {e}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                "error": f"Failed to generate questions: {str(e)}",
                "status": "error",
                "step": "question_generation"
            }), 500

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
            return jsonify({
                "error": f"Failed to save test: {str(e)}",
                "status": "error",
                "step": "database_save"
            }), 500
        audio_success = False
        audio_url = ""

        try:
            if current_app.openai_service and hasattr(current_app.openai_service, 'generate_audio'):
                audio_result = current_app.openai_service.generate_audio(transcript, slug)
                if audio_result:
                    audio_success = True
                    audio_url = f"https://pub-6397ec15ed7943bda657f81f246f7c4b.r2.dev/{slug}.mp3"
                    current_app.supabase_service.table('tests').update({
                        'audio_generated': True,
                        'audio_url': audio_url,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }).eq('id', test_id).execute()
        except Exception as e:
            current_app.logger.warning(f"Audio generation failed (non-critical): {e}")
        try:
            saved_test_result = current_app.supabase_service.table('tests').select(
                'id, slug, title, language_id, topic, difficulty, style, tier, '
                'audio_url, audio_generated, is_custom, is_featured, total_attempts, '
                'dim_languages(language_code, language_name)'
            ).eq('id', test_id).execute()

            ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
                'test_type_id, elo_rating, volatility, total_attempts, dim_test_types(type_code)'
            ).eq('test_id', test_id).execute()

            skill_ratings = {}
            flat_ratings = {}
            for rating in ratings_result.data:
                type_code = rating.get('dim_test_types', {}).get('type_code', 'unknown')
                skill_ratings[type_code] = {
                    'elo_rating': rating['elo_rating'],
                    'volatility': rating['volatility'],
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

                return jsonify({
                    "slug": slug,
                    "test_id": test_id,
                    "status": "success",
                    "message": "Test generated and saved successfully",
                    "audio_generated": audio_success,
                    "audio_url": audio_url if audio_success else None,
                    "test_summary": test_summary,
                })

        except Exception as e:
            current_app.logger.warning(f"Could not fetch complete test summary: {e}")
        response_data = {
            "slug": slug,
            "test_id": test_id,
            "status": "success",
            "message": "Test generated and saved to database successfully",
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
                "is_custom": False
            }
        }

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"UNEXPECTED ERROR in generate_test: {e}")
        current_app.logger.error(f"UNEXPECTED ERROR TYPE: {type(e).__name__}")
        current_app.logger.error(f"UNEXPECTED ERROR TRACEBACK: {traceback.format_exc()}")
        return jsonify({
            "error": f"Test generation failed: {str(e)}",
            "status": "error",
            "step": "unexpected_error",
            "error_type": type(e).__name__
        }), 500

@tests_bp.route('/custom_test', methods=['POST'])
@supabase_jwt_required
def custom_test():
    """Create a custom test with user-provided transcript and save to Supabase"""
    try:
        current_user_id = g.supabase_claims.get('sub')
        current_user_email = g.supabase_claims.get('email')

        # Handle batch operations using service role key
        # Replace 'service-account' with a special UUID for batch-generated tests
        if current_user_id == 'service-account':
            # Use a well-known UUID for batch operations (00000000-0000-0000-0000-000000000001)
            current_user_id = '00000000-0000-0000-0000-000000000001'

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided", "status": "error"}), 400

        if not current_app.openai_service:
            return jsonify({"error": "OpenAI service not available", "status": "error"}), 500

        if not current_app.supabase_service:
            return jsonify({"error": "Database service not connected", "status": "error"}), 500

        language = data.get('language')
        difficulty = data.get('difficulty')
        transcript = data.get('transcript', '').strip()

        if not (language and difficulty and transcript):
            return jsonify({
                "error": "Missing required fields: language, difficulty, and transcript", 
                "status": "error"
            }), 400

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
                    audio_url = f"https://pub-6397ec15ed7943bda657f81f246f7c4b.r2.dev/{slug}.mp3"

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
                'id, slug, title, language_id, topic, difficulty, style, tier, '
                'audio_url, audio_generated, is_custom, is_featured, total_attempts, '
                'dim_languages(language_code, language_name)'
            ).eq('id', test_id).execute()

            # Get the skill ratings with FK join to dim_test_types
            ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
                'test_type_id, elo_rating, volatility, total_attempts, dim_test_types(type_code)'
            ).eq('test_id', test_id).execute()

            # Transform ratings
            skill_ratings = {}
            flat_ratings = {}
            for rating in ratings_result.data:
                type_code = rating.get('dim_test_types', {}).get('type_code', 'unknown')
                skill_ratings[type_code] = {
                    'elo_rating': rating['elo_rating'],
                    'volatility': rating['volatility'],
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

                return jsonify({
                    "slug": slug,
                    "test_id": test_id,
                    "status": "success",
                    "message": "Custom test created and saved successfully",
                    "audio_generated": audio_success,
                    "audio_url": audio_url if audio_success else None,
                    "test_summary": test_summary,
                })
        except Exception as e:
            current_app.logger.warning(f"⚠️ Could not fetch complete test summary: {e}")

        # Fallback response
        return jsonify({
            "slug": slug,
            "test_id": test_id,
            "status": "success",
            "message": "Custom test created and saved to database successfully",
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
                "questions_count": len(questions)
            }
        })

    except Exception as e:
        current_app.logger.error(f"❌ Custom test error: {e}")
        current_app.logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e), "status": "error"}), 500




@tests_bp.route('/', methods=['GET'])
@supabase_jwt_required
def get_tests_with_ratings():
    """Get tests list with ELO ratings for filtering/preview."""
    try:
        language_id_param = request.args.get('language_id')
        difficulty = request.args.get('difficulty')
        limit = int(request.args.get('limit', 50))

        if not current_app.supabase_service:
            return jsonify({"error": "Database service not configured"}), 500

        query = current_app.supabase_service.table('tests').select(
            'id, slug, title, language_id, topic, difficulty, style, tier, '
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
                'test_id, test_type_id, elo_rating, volatility, total_attempts, dim_test_types(type_code)'
            ).in_('test_id', test_ids).execute()

            for rating in ratings_result.data:
                test_id = rating['test_id']
                type_code = rating.get('dim_test_types', {}).get('type_code', 'unknown')
                if test_id not in ratings_by_test:
                    ratings_by_test[test_id] = {}
                ratings_by_test[test_id][type_code] = {
                    'elo_rating': rating['elo_rating'],
                    'volatility': rating['volatility'],
                    'total_attempts': rating['total_attempts']
                }

        tests_with_ratings = []
        for test in tests_result.data:
            test_ratings = ratings_by_test.get(test['id'], {})
            test_with_ratings = {
                **test,
                'listening_rating': test_ratings.get('listening', {}).get('elo_rating', 1400),
                'reading_rating': test_ratings.get('reading', {}).get('elo_rating', 1400),
                'dictation_rating': test_ratings.get('dictation', {}).get('elo_rating', 1400),
                'skill_ratings': test_ratings
            }
            tests_with_ratings.append(test_with_ratings)

        return jsonify({
            "success": True,
            "tests": tests_with_ratings
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching tests: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@tests_bp.route('/<slug>', methods=['GET'])
#@supabase_jwt_required
def get_test(slug):
    """Get a test by slug in the shape expected by the Flutter app."""
    try:
        test_service = get_test_service()
        test_data = test_service.get_test_by_slug(slug)
        if not test_data:
            return jsonify({"error": "Test not found", "status": "not_found"}), 404

        test_data['audio_url'] = f"https://229f11834e90e4438de8d1a9ba872d0f.r2.cloudflarestorage.com/lingualoopaudio/{slug}.mp3"
        logger.debug(f"Returning test data for slug: {slug}")
        return jsonify({"test": test_data, "status": "success"})

    except Exception as e:
        current_app.logger.error(f"Error in get_test route: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500
        
@tests_bp.route('/<slug>/submit', methods=['POST'])
@supabase_jwt_required
def submit_test_attempt(slug):
    """Submit test answers and calculate ELO changes with idempotency support"""
    try:
        if not current_app.supabase_service:
            return jsonify({"error": "Database service not configured"}), 500

        current_user_id = g.supabase_claims.get('sub')
        if not current_user_id:
            return jsonify({"error": "User authentication failed"}), 401

        data = request.get_json() or {}
        responses = data.get('responses', [])
        test_mode = data.get('test_mode', 'reading').lower()

        if not responses:
            return jsonify({"error": "No responses provided"}), 400

        test_service = get_test_service()
        test_data = test_service.get_test_by_slug(slug)
        if not test_data:
            return jsonify({"error": f"Test not found: {slug}"}), 404

        questions = test_data.get('questions', [])
        if not questions:
            return jsonify({"error": "No questions found for this test"}), 404

        # Get test_type_id from the test_mode using DimensionService cache
        test_type_id = DimensionService.get_test_type_id(test_mode)
        if not test_type_id:
            logger.warning(f"Unknown test_mode '{test_mode}', defaulting to reading")
            test_type_id = DimensionService.get_test_type_id('reading') or 1

        response_map = {r['question_id']: r['selected_answer'] for r in responses}

        score = 0
        question_results = []

        for question in questions:
            selected = response_map.get(str(question['id']), '')
            correct = question.get('answer', '')
            is_correct = selected == correct

            if is_correct:
                score += 1

            question_results.append({
                'question_id': str(question['id']),
                'selected_answer': selected,
                'correct_answer': correct,
                'is_correct': is_correct
            })

        total_questions = len(questions)
        percentage = score / total_questions if total_questions > 0 else 0.0

        # Generate idempotency key to prevent duplicate submissions
        idempotency_key = str(uuid4())

        # Call database RPC for ELO calculation and attempt recording
        rpc_result = current_app.supabase_service.rpc('process_test_submission', {
            'p_user_id': current_user_id,
            'p_test_id': test_data['id'],
            'p_language_id': test_data['language_id'],
            'p_test_type_id': test_type_id,
            'p_score': score,
            'p_total_questions': total_questions,
            'p_was_free_test': True,
            'p_idempotency_key': idempotency_key
        }).execute()

        if not rpc_result.data or not rpc_result.data.get('success'):
            error_msg = rpc_result.data.get('error', 'Unknown error') if rpc_result.data else 'RPC failed'
            current_app.logger.error(f"ELO RPC failed: {error_msg}")
            return jsonify({"error": "Failed to process test submission"}), 500

        elo_results = rpc_result.data
        is_first_attempt = elo_results.get('is_first_attempt', True)

        # Update user stats (only on first attempt to avoid inflating counts)
        if is_first_attempt:
            user_data = current_app.supabase_service.table('users').select('total_tests_taken')\
                .eq('id', current_user_id).execute()

            current_tests_taken = 0
            if user_data.data and len(user_data.data) > 0:
                current_tests_taken = user_data.data[0].get('total_tests_taken', 0)

            current_app.supabase_service.table('users').update({
                'total_tests_taken': current_tests_taken + 1,
                'last_activity_at': datetime.now().isoformat()
            }).eq('id', current_user_id).execute()

        # Return comprehensive result
        return jsonify({
            'status': 'success',
            'result': {
                'score': score,
                'total_questions': total_questions,
                'percentage': percentage,
                'question_results': question_results,
                'is_first_attempt': is_first_attempt,
                'user_elo_change': {
                    'before': elo_results['user_elo_before'],
                    'after': elo_results['user_elo_after'],
                    'change': elo_results['user_elo_change']
                },
                'test_elo_change': {
                    'before': elo_results['test_elo_before'],
                    'after': elo_results['test_elo_after'],
                    'change': elo_results['test_elo_change']
                },
                'test_mode': test_mode,
                'language': test_data['language'],
                'attempt_id': str(elo_results.get('attempt_id')) if elo_results.get('attempt_id') else None
            }
        })

    except Exception as e:
        current_app.logger.error(f"Test submission error: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to submit test'}), 500




@tests_bp.route('/test/<slug>', methods=['GET'])
#@supabase_jwt_required
def get_test_with_ratings(slug):
    """Get test with ELO ratings for preview/taking."""
    try:
        if not current_app.supabase_service:
            return jsonify({"error": "Service not available"}), 503

        # Get test basic info with FK join to dim_languages
        test_result = current_app.supabase_service.table('tests').select(
            'id, slug, title, language_id, topic, difficulty, style, tier, transcript, '
            'audio_url, audio_generated, is_custom, is_featured, total_attempts, '
            'dim_languages(language_code, language_name)'
        ).eq('slug', slug).eq('is_active', True).execute()

        if not test_result.data:
            return jsonify({"error": "Test not found"}), 404

        test = test_result.data[0]
        test_id = test['id']

        # Add language info for backwards compatibility
        lang_info = test.pop('dim_languages', {}) or {}
        test['language'] = lang_info.get('language_code', 'unknown')
        test['language_name'] = lang_info.get('language_name', 'Unknown')

        # Get questions
        questions_result = current_app.supabase_service.table('questions').select(
            'id, question_id, question_text, question_type, choices, '
            'correct_answer, answer_explanation, points, audio_url'
        ).eq('test_id', test_id).execute()

        # Get ELO ratings with FK join to dim_test_types
        ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
            'test_type_id, elo_rating, volatility, total_attempts, dim_test_types(type_code)'
        ).eq('test_id', test_id).execute()

        # Transform ratings into a dictionary
        ratings = {
            rating.get('dim_test_types', {}).get('type_code', 'unknown'): {
                'elo_rating': rating['elo_rating'],
                'volatility': rating['volatility'],
                'total_attempts': rating['total_attempts']
            }
            for rating in ratings_result.data
        }
        
        # Build response
        response_data = {
            "test_data": test,
            "questions_data": questions_result.data,
            "skill_ratings": ratings
        }
        
        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error fetching test {slug}: {e}")
        return jsonify({"error": str(e)}), 500