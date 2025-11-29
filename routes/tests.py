# routes/tests.py

from flask import Flask, request, jsonify, redirect, Response, make_response, g  # Added 'g'
from flask_cors import CORS, cross_origin
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import uuid4
import os
import json
import time
from datetime import datetime, timezone
import stripe
from supabase import create_client, Client
import requests
import logging
import sys
import traceback
from flask import Blueprint, request, jsonify, current_app
from ..config import Config
from ..services.openai_service import OpenAIService
from ..services.service_factory import ServiceFactory
from ..services.r2_service import R2Service
from ..services.prompt_service import PromptService
from ..utils.auth import supabase_jwt_required
from ..services.elo_service import EloService
from ..services.database_service import DatabaseService

tests_bp = Blueprint("tests", __name__)


# =============================================================================
# DATABASE HELPER FUNCTIONS
# =============================================================================

def save_test_to_database(supabase_service_client, test_data):
    """Save generated test data using service role client (bypasses RLS)."""
    if not supabase_service_client:
        raise Exception("Supabase service client not initialized")
    
    print(f"TEST DATA: {test_data}", flush=True)
    
    try:
        # IMPORTANT: Still validate user authentication first
        if not hasattr(g, 'supabase_claims') or not g.supabase_claims.get('sub'):
            raise Exception("User not authenticated")
        
        # Build tests row using only fields that exist in the actual schema
        tests_row = {
            "slug": test_data["slug"],  # required
            "language": test_data["language"],  # required
            "topic": test_data.get("topic", ""),
            "difficulty": int(test_data.get("difficulty", 1)),
            "style": test_data.get("style", ""),
            "tier": test_data.get("tier", "free"),
            "title": test_data.get("title") or test_data.get("topic") or f"{test_data['language'].capitalize()} Test",
            "transcript": test_data.get("transcript", ""),
            "audio_url": test_data.get("audio_url", ""),
            "total_attempts": test_data.get("total_attempts", 0),
            "is_active": test_data.get("is_active", True),
            "is_featured": test_data.get("is_featured", False),
            "is_custom": test_data.get("is_custom", False),
            "generation_model": test_data.get("generation_model", "gpt-4"),
            "audio_generated": test_data.get("audio_generated", False),
            "gen_user": test_data.get("gen_user", ""),  # UUID from validated JWT
        }

        print(f"🔧 Inserting test record with service role client: {tests_row}")
        
        # Use service role client - bypasses RLS
        test_result = supabase_service_client.table('tests').insert(tests_row).execute()
        
        if not test_result.data:
            raise Exception("No data returned from test insert")
        
        test_id = test_result.data[0]['id']
        print(f"✅ Test inserted with ID: {test_id}")
        
        # Build questions rows using only fields that exist in the actual schema
        question_rows = []
        for i, q in enumerate(test_data.get('questions', []), start=1):
            # Ensure choices and correct_answer are properly formatted for JSONB
            choices = q.get('choices', [])
            if isinstance(choices, str):
                try:
                    choices = json.loads(choices)
                except json.JSONDecodeError:
                    choices = [choices]  # Convert single string to array
            
            correct_answer = q.get('answer', '')
            
            question_row = {
                'test_id': test_id,
                'question_id': q.get('id') or str(uuid4()),
                'question_text': q.get('question', ''),
                'question_type': q.get('question_type', 'multiple_choice'),  # default type
                'choices': choices,  # JSONB field
                'correct_answer': correct_answer,  # JSONB field
                'answer_explanation': q.get('explanation', ''),
                'points': q.get('points', 1),  # default 1 point per question
                'audio_url': q.get('audio_url', ''),
            }
            question_rows.append(question_row)
        
        if question_rows:
            print(f"🔧 Inserting {len(question_rows)} questions with service role client")
            
            # Use service role client for questions too
            questions_result = supabase_service_client.table('questions').insert(question_rows).execute()
            print(f"✅ Questions inserted successfully")
        else:
            print("⚠️ No questions to insert")
        
        initial_elo = 1400  # Starting ELO
        skill_ratings = [
            {
                'test_id': test_id,
                'skill_type': 'listening',
                'elo_rating': initial_elo,
                'volatility': 1.0,
                'total_attempts': 0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            },
            {
                'test_id': test_id,
                'skill_type': 'reading',
                'elo_rating': initial_elo,
                'volatility': 1.0,
                'total_attempts': 0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            },
            {
                'test_id': test_id,
                'skill_type': 'dictation',
                'elo_rating': initial_elo,
                'volatility': 1.0,
                'total_attempts': 0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
        ]
        
        # Insert skill ratings
        print(f"🔧 Inserting {len(skill_ratings)} skill ratings")
        ratings_result = supabase_service_client.table('test_skill_ratings').insert(skill_ratings).execute()
        print(f"✅ Skill ratings inserted successfully")

        print(f"✅ Saved test to database: {test_data['slug']} ({test_id})")
        return test_id
        
    except Exception as e:
        print(f"❌ Error saving test to database: {e}", flush=True)
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise


def get_tests_from_database(supabase, test_type='reading', limit=20, language=None, difficulty=None):
    """Fetch tests list with optional filters; order by ELO of requested test type."""
    if not supabase:
        return []
    
    try:
        # Select only fields the FE may need in lists
        query = supabase.table('tests').select(
            'id, slug, language, topic, difficulty, '
            'listening_rating, reading_rating, dictation_rating, created_at'
        )
        
        if language:
            query = query.eq('language', language)
        if difficulty is not None:
            query = query.eq('difficulty', str(int(difficulty)))
        
        # Map test type to sort column
        type_key = (test_type or 'reading').lower()
        order_col = 'reading_rating'
        if type_key in ('listening', 'reading', 'dictation'):
            order_col = f'{type_key}_rating'
        
        query = query.order(order_col, desc=True).limit(limit)
        result = query.execute()
        data = result.data or []
        
        # Normalize difficulty to int for FE
        for t in data:
            try:
                if t.get('difficulty') is not None:
                    t['difficulty'] = int(t['difficulty'])
            except Exception:
                pass
        
        return data
        
    except Exception as e:
        print(f"Error fetching tests from database: {e}")
        return []

def get_test_by_slug(supabase, slug):
    """Get a single test by slug with its questions, formatted for the Flutter app."""
    if not supabase:
        return None
    
    try:
        print(f"🔍 Getting test by slug: {slug}", flush=True)
        
        # Get test record
        t_res = supabase.table('tests').select('*').eq('slug', slug).limit(1).execute()
        if not t_res.data:
            print(f"❌ No test found for slug: {slug}", flush=True)
            return None
        
        t = t_res.data[0]
        print(f"✅ Found test: {t['id']}", flush=True)
        
        # Get questions for this test
        q_res = (
            supabase.table('questions')
            .select('*')
            .eq('test_id', t['id'])
            .execute()
        )
        
        q_rows = q_res.data or []
        print(f"✅ Found {len(q_rows)} questions", flush=True)
        
        def _parse_choices(raw):
            if isinstance(raw, list):
                return raw
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                    return parsed if isinstance(parsed, list) else [raw]
                except Exception:
                    return [raw]
            return []
        
        questions = []
        for q in q_rows:
            questions.append({
                'id': q['id'],
                'question': q['question_text'],
                'choices': _parse_choices(q.get('choices')),
                'answer': q.get('correct_answer', ''),
            })
        
        # Normalize difficulty to int
        difficulty_value = t.get('difficulty', 1)
        try:
            difficulty_value = int(difficulty_value)
        except Exception:
            difficulty_value = 1
        
        formatted = {
            'id': t['id'],
            'slug': t['slug'],
            'language': t.get('language'),
            'topic': t.get('topic') or '',
            'title': t.get('topic') or f"{t.get('language','').capitalize()} Test (Level {difficulty_value})",
            'difficulty': difficulty_value,
            'transcript': t.get('transcript') or '',
            'questions': questions,  # ← THIS IS CRUCIAL
            'created_at': t.get('created_at'),
        }
        
        print(f"✅ Returning test with {len(questions)} questions")
        return formatted
        
    except Exception as e:
        print(f"❌ Error fetching test by slug: {e}", flush=True)
        print(f"❌ Full traceback: {traceback.format_exc()}", flush=True)
        return None

def record_test_attempt(supabase, user_id, test_id, responses, test_mode, time_taken=None):
    """Record a user's test attempt and individual responses"""
    if not supabase:
        raise Exception("Supabase client not initialized")
    
    try:
        # Calculate score
        total_questions = len(responses)
        correct_count = sum(1 for r in responses if r['is_correct'])
        
        # TODO: Get user ELO before attempt (implement ELO system)
        user_elo_before = 1200  # Default starting ELO
        user_elo_after = 1200   # Will be calculated by ELO function
        
        # Insert test attempt
        attempt_record = {
            'user_id': user_id,
            'test_id': test_id,
            'score': correct_count,
            'total_questions': total_questions,
            'test_mode': test_mode,
            'time_taken_seconds': time_taken,
            'user_elo_before': user_elo_before,
            'user_elo_after': user_elo_after
        }
        
        attempt_result = supabase.table('test_attempts').insert(attempt_record).execute()
        attempt_id = attempt_result.data[0]['id']
        
        # Insert individual responses
        responses_to_insert = []
        for response in responses:
            response_record = {
                'attempt_id': attempt_id,
                'question_id': response['question_id'],
                'selected_answer': response['selected_answer'],
                'is_correct': response['is_correct'],
                'response_time_ms': response.get('response_time_ms')
            }
            responses_to_insert.append(response_record)
        
        if responses_to_insert:
            supabase.table('attempt_responses').insert(responses_to_insert).execute()
        
        return {
            'attempt_id': attempt_id,
            'score': correct_count,
            'total_questions': total_questions,
            'percentage': (correct_count / total_questions) * 100
        }
        
    except Exception as e:
        print(f"❌ Error recording test attempt: {e}")
        raise e

def record_flagged_input(supabase, user_email, content, flagged_categories=None):
    """Record flagged input for analytics with category information"""
    if not supabase:
        return
    
    try:
        import hashlib
        record = {
            'user_email': user_email,
            'content_hash': hashlib.sha256(content.encode()).hexdigest()[:32],
            'flagged_at': datetime.now(timezone.utc).isoformat(),
            'content_type': 'test_generation',
            'flagged_categories': json.dumps(flagged_categories or []),
            'content_length': len(content),
        }
        
        supabase.table('flagged_inputs').insert(record).execute()
        print(f"📊 Recorded flagged input: {flagged_categories}")
    except Exception as e:
        print(f"❌ Failed to record flagged input: {e}")

@tests_bp.route('/moderate', methods=['POST'])
@supabase_jwt_required
def moderate_content():
    print("Authorization header:", request.headers.get("Authorization"), flush=True)
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
        
        # Use OpenAI service for moderation
        moderation_result = current_app.openai_service.moderate_content(content)
        
        # Handle service errors
        if moderation_result.get('error'):
            print(f"⚠️ Moderation service error: {moderation_result['error']}")
            # Continue with fail-safe response
        
        is_safe = moderation_result['is_safe']
        
        # Record flagged content for analytics
        if not is_safe:
            current_user_email = g.supabase_claims.get('email')
            record_flagged_input(
                current_app.supabase,
                current_user_email,
                content,
                moderation_result.get('flagged_categories', [])
            )
            print(f"🚨 Flagged content from {current_user_email}: {moderation_result['flagged_categories']}")
        
        return jsonify({
            "is_safe": is_safe,
            "flagged_categories": moderation_result.get('flagged_categories', []),
            "status": "success"
        }), 200
        
    except Exception as e:
        print(f"❌ Moderation endpoint error: {e}")
        return jsonify({
            "error": f"Moderation failed: {str(e)}",
            "status": "error"
        }), 500
    

@tests_bp.route('/generate_test', methods=['POST'])
@supabase_jwt_required
def generate_test():
    """Generate a new test and save to Supabase database - ENHANCED DEBUG VERSION"""
    try:
        current_app.logger.info("🔧 STEP 1: Generate test request received")
        
        # Get current user from Supabase JWT claims (stored by your custom decorator)
        current_user_id = g.supabase_claims.get('sub')  # 'sub' is typically the user ID
        current_user_email = g.supabase_claims.get('email')  # Email if you need it
        current_app.logger.info(f"🔧 STEP 1: Current user ID: {current_user_id}, Email: {current_user_email}")
        
        # Validate services
        if not current_app.openai_service:
            current_app.logger.error("❌ STEP 1 FAILED: OpenAI service not available")
            return jsonify({
                "error": "AI service not available",
                "status": "error"
            }), 503
            
        current_app.logger.info("🔧 STEP 1 SUCCESS: OpenAI service available")
            
        if not current_app.supabase_service:
            current_app.logger.error("❌ STEP 1 FAILED: Database service not connected")
            return jsonify({
                "error": "Database service not connected",
                "status": "error"
            }), 503
            
        current_app.logger.info("🔧 STEP 1 SUCCESS: Database service connected")
        
        if request.method == 'OPTIONS':
            current_app.logger.info("🔧 STEP 1: Handling OPTIONS preflight")
            response = make_response()
            response.headers['Access-Control-Allow-Origin'] = ','.join(Config.CORS_ORIGINS)
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
            return response
        
        # Get and validate request data
        current_app.logger.info("🔧 STEP 2: Parsing request data")
        data = request.get_json()
        
        if not data:
            current_app.logger.error("❌ STEP 2 FAILED: No JSON data provided")
            return jsonify({
                "error": "No JSON data provided",
                "status": "error"
            }), 400
            
        current_app.logger.info(f"🔧 STEP 2 SUCCESS: Request data received: {data}")
        
        # Validate required fields
        current_app.logger.info("🔧 STEP 3: Validating required fields")
        language = data.get('language')
        difficulty = data.get('difficulty')
        topic = data.get('topic')
        style = data.get('style', 'academic')
        tier = data.get('tier', 'free-tier')  # Default to free-tier
        
        current_app.logger.info(f"🔧 STEP 3: Parsed fields - Language: {language}, Difficulty: {difficulty}, Topic: {topic}, Style: {style}")
        
        if not all([language, difficulty, topic]):
            current_app.logger.error(f"❌ STEP 3 FAILED: Missing required fields - Language: {language}, Difficulty: {difficulty}, Topic: {topic}")
            return jsonify({
                "error": "Missing required fields: language, difficulty, topic",
                "status": "error"
            }), 400
            
        current_app.logger.info(f"✅ STEP 3 SUCCESS: All required fields present")
        
        # Generate transcript
        current_app.logger.info("🔧 STEP 4: Starting OpenAI transcript generation")
        try:
            transcript = current_app.openai_service.generate_transcript(language, topic, difficulty, style)
            current_app.logger.info(f"✅ STEP 4 SUCCESS: Transcript generated ({len(transcript)} chars)")
        except Exception as e:
            current_app.logger.error(f"❌ STEP 4 FAILED: Transcript generation error: {e}")
            current_app.logger.error(f"❌ STEP 4 TRACEBACK: {traceback.format_exc()}")
            return jsonify({
                "error": f"Failed to generate transcript: {str(e)}",
                "status": "error",
                "step": "transcript_generation"
            }), 500
        
        # Generate questions
        current_app.logger.info("🔧 STEP 5: Starting question generation")
        try:
            questions = current_app.openai_service.generate_questions(transcript, language, difficulty)
            current_app.logger.info(f"✅ STEP 5 SUCCESS: Generated {len(questions)} questions")
        except Exception as e:
            current_app.logger.error(f"❌ STEP 5 FAILED: Question generation error: {e}")
            current_app.logger.error(f"❌ STEP 5 TRACEBACK: {traceback.format_exc()}")
            return jsonify({
                "error": f"Failed to generate questions: {str(e)}",
                "status": "error",
                "step": "question_generation"
            }), 500
        
        # Create test data structure
        current_app.logger.info("🔧 STEP 6: Creating test data structure")
        slug = str(uuid4())
        
        # Generate a meaningful title
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
            'audio_url': '',  # Will be updated after audio generation
            'total_attempts': 0,
            'is_active': True,
            'is_featured': data.get('is_featured', False),
            'is_custom': False,  # This is a generated test, not custom
            'generation_model': data.get('generation_model', 'gpt-4'),
            'audio_generated': False,  # Will be updated after audio generation
            'gen_user': current_user_id,  # User who generated the test (use Supabase user ID)
            'questions': questions,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        current_app.logger.info(f"✅ STEP 6 SUCCESS: Test data structure created with slug: {slug}")
        
        # Save to database using service role client
        current_app.logger.info("🔧 STEP 7: Saving test to database")
        try:
            test_id = save_test_to_database(current_app.supabase_service, test_data)
            current_app.logger.info(f"✅ STEP 7 SUCCESS: Test saved to database with ID: {test_id}")
        except Exception as e:
            current_app.logger.error(f"❌ STEP 7 FAILED: Database save error: {e}")
            current_app.logger.error(f"❌ STEP 7 TRACEBACK: {traceback.format_exc()}")
            return jsonify({
                "error": f"Failed to save test: {str(e)}",
                "status": "error",
                "step": "database_save"
            }), 500
        
        # Generate audio (optional)
        current_app.logger.info("🔧 STEP 8: Starting audio generation (optional)")
        audio_success = False
        audio_url = ""
        
        try:
            if current_app.openai_service and hasattr(current_app.openai_service, 'generate_audio'):
                audio_result = current_app.openai_service.generate_audio(transcript, slug)
                if audio_result:
                    audio_success = True
                    audio_url = f"https://pub-6397ec15ed7943bda657f81f246f7c4b.r2.dev/{slug}.mp3"  # Or whatever URL structure you use
                    
                    # Update the test record with audio information using service role client
                    current_app.supabase_service.table('tests').update({
                        'audio_generated': True,
                        'audio_url': audio_url,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }).eq('id', test_id).execute()
                    
                current_app.logger.info(f"✅ STEP 8: Audio generation result: {audio_success}")
            else:
                current_app.logger.info("🔧 STEP 8: Audio generation not available or not implemented")
        except Exception as e:
            current_app.logger.warning(f"⚠️ STEP 8: Audio generation failed (non-critical): {e}")
        
        # Fetch complete test summary with ELO ratings for response
        current_app.logger.info("🔧 STEP 9: Fetching complete test summary")
        try:
            # Get the saved test with all fields for frontend
            saved_test_result = current_app.supabase_service.table('tests').select(
                'id, slug, title, language, topic, difficulty, style, tier, '
                'audio_url, audio_generated, is_custom, is_featured, total_attempts'
            ).eq('id', test_id).execute()
            
            # Get the skill ratings
            ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
                'skill_type, elo_rating, volatility, total_attempts'
            ).eq('test_id', test_id).execute()
            
            # Transform ratings
            skill_ratings = {}
            flat_ratings = {}
            for rating in ratings_result.data:
                skill_type = rating['skill_type']
                skill_ratings[skill_type] = {
                    'elo_rating': rating['elo_rating'],
                    'volatility': rating['volatility'],
                    'total_attempts': rating['total_attempts']
                }
                flat_ratings[f'{skill_type}_rating'] = rating['elo_rating']
            
            if saved_test_result.data:
                test_summary = {
                    **saved_test_result.data[0],
                    'skill_ratings': skill_ratings,
                    **flat_ratings,  # Add flat ratings for compatibility
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
            else:
                # Fallback if we can't fetch the saved test
                current_app.logger.warning("⚠️ Could not fetch saved test, using fallback response")
                
        except Exception as e:
            current_app.logger.warning(f"⚠️ Could not fetch complete test summary: {e}")
        
        # Fallback response
        current_app.logger.info("🔧 STEP 9: Preparing fallback response")
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
        
        current_app.logger.info(f"✅ STEP 9 SUCCESS: Returning successful response for test {slug}")
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"❌ UNEXPECTED ERROR in generate_test: {e}")
        current_app.logger.error(f"❌ UNEXPECTED ERROR TYPE: {type(e).__name__}")
        current_app.logger.error(f"❌ UNEXPECTED ERROR TRACEBACK: {traceback.format_exc()}")
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
        # Get current user from Supabase JWT claims
        current_user_id = g.supabase_claims.get('sub')
        current_user_email = g.supabase_claims.get('email')
        current_app.logger.info(f"🔧 Custom test request from user ID: {current_user_id}, Email: {current_user_email}")
        
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
        tier = data.get('tier', 'premium-tier')  # Custom tests might be premium feature

        # Generate questions using OpenAI service
        current_app.logger.info("🔧 Generating questions for custom test")
        questions = current_app.openai_service.generate_questions(transcript, language, difficulty)
        current_app.logger.info(f"✅ Generated {len(questions)} questions for custom test")

        slug = str(uuid4())
        
        # Generate a meaningful title
        title = data.get('title') or f"Custom {language.capitalize()}: {topic}"

        # Prepare test data structure matching the database schema
        test_data = {
            'slug': slug,
            'language': language,
            'topic': topic,
            'difficulty': difficulty,
            'style': style,
            'tier': tier,
            'title': title,
            'transcript': transcript,
            'audio_url': '',  # Will be updated after audio generation
            'total_attempts': 0,
            'is_active': True,
            'is_featured': data.get('is_featured', False),
            'is_custom': True,  # This is a custom test
            'generation_model': data.get('generation_model', 'gpt-4'),
            'audio_generated': False,  # Will be updated after audio generation
            'gen_user': current_user_id,  # User who created the custom test (use Supabase user ID)
            'questions': questions,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }

        # Save test to Supabase database using service role client
        current_app.logger.info("🔧 Saving custom test to database")
        test_id = save_test_to_database(current_app.supabase_service, test_data)
        current_app.logger.info(f"✅ Custom test saved with ID: {test_id}")

        # Generate audio using service (optional)
        audio_success = False
        audio_url = ""
        
        try:
            if current_app.openai_service and hasattr(current_app.openai_service, 'generate_audio'):
                current_app.logger.info("🔧 Generating audio for custom test")
                audio_result = current_app.openai_service.generate_audio(transcript, slug)
                
                if audio_result:
                    audio_success = True
                    audio_url = f"https://pub-6397ec15ed7943bda657f81f246f7c4b.r2.dev/{slug}.mp3"
                    
                    # Update the test record with audio information using service role client
                    current_app.supabase_service.table('tests').update({
                        'audio_generated': True,
                        'audio_url': audio_url,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }).eq('id', test_id).execute()
                    
                current_app.logger.info(f"✅ Audio generation result: {audio_success}")
        except Exception as e:
            current_app.logger.warning(f"⚠️ Audio generation failed (non-critical): {e}")

        # Fetch complete test summary with ELO ratings for response
        try:
            # Get the saved test with all fields for frontend
            saved_test_result = current_app.supabase_service.table('tests').select(
                'id, slug, title, language, topic, difficulty, style, tier, '
                'audio_url, audio_generated, is_custom, is_featured, total_attempts'
            ).eq('id', test_id).execute()
            
            # Get the skill ratings
            ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
                'skill_type, elo_rating, volatility, total_attempts'
            ).eq('test_id', test_id).execute()
            
            # Transform ratings
            skill_ratings = {}
            flat_ratings = {}
            for rating in ratings_result.data:
                skill_type = rating['skill_type']
                skill_ratings[skill_type] = {
                    'elo_rating': rating['elo_rating'],
                    'volatility': rating['volatility'],
                    'total_attempts': rating['total_attempts']
                }
                flat_ratings[f'{skill_type}_rating'] = rating['elo_rating']
            
            if saved_test_result.data:
                test_summary = {
                    **saved_test_result.data[0],
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
        # Get query parameters
        language = request.args.get('language')
        difficulty = request.args.get('difficulty')
        limit = int(request.args.get('limit', 50))
        
        # Build query
        query = current_app.supabase_service.table('tests').select(
            'id, slug, title, language, topic, difficulty, style, tier, '
            'audio_url, audio_generated, is_custom, is_featured, total_attempts'
        ).eq('is_active', True)
        
        if language:
            query = query.eq('language', language)
        if difficulty:
            query = query.eq('difficulty', int(difficulty))
            
        tests_result = query.limit(limit).execute()
        
        # Get ELO ratings for all tests
        test_ids = [test['id'] for test in tests_result.data]
        if test_ids:
            ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
                'test_id, skill_type, elo_rating, volatility, total_attempts'
            ).in_('test_id', test_ids).execute()
            
            # Group ratings by test_id
            ratings_by_test = {}
            for rating in ratings_result.data:
                test_id = rating['test_id']
                if test_id not in ratings_by_test:
                    ratings_by_test[test_id] = {}
                ratings_by_test[test_id][rating['skill_type']] = {
                    'elo_rating': rating['elo_rating'],
                    'volatility': rating['volatility'],
                    'total_attempts': rating['total_attempts']
                }
        
        # Combine test data with ratings
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
        current_app.logger.error(f"❌ Error fetching tests: {e}")
        return jsonify({"error": str(e)}), 500

@tests_bp.route('/<slug>', methods=['GET'])
#@supabase_jwt_required
def get_test(slug):
    """Get a test by slug in the shape expected by the Flutter app."""
    try:
        if not current_app.supabase:
            return jsonify({"error": "Database not connected", "status": "error"}), 500
        
        test_data = get_test_by_slug(current_app.supabase, slug)
        if not test_data:
            return jsonify({"error": "Test not found", "status": "not_found"}), 404
        
        # Provide audio URL for listening/dictation
        test_data['audio_url'] = f"https://229f11834e90e4438de8d1a9ba872d0f.r2.cloudflarestorage.com/lingualoopaudio/{slug}.mp3"
        print(test_data, flush=True)
        return jsonify({"test": test_data, "status": "success"})
        
    except Exception as e:
        current_app.logger.error(f"❌ Error in get_test route: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500
        
@tests_bp.route('/<slug>/submit', methods=['POST'])
@supabase_jwt_required  # Your custom decorator that populates g.supabase_claims
def submit_test_attempt(slug):
    """Submit test answers and calculate ELO changes - Supabase Auth Version"""
    try:
        if not current_app.supabase:
            return jsonify({"error": "Database not connected"}), 500

        # Initialize ELO service with service role client to bypass RLS
        elo_service = EloService(current_app.supabase_service or current_app.supabase)
        
        # Get user info from Supabase claims (set by @supabase_jwt_required)
        current_user_id = g.supabase_claims.get('sub')
        current_user_email = g.supabase_claims.get('email')
        
        if not current_user_id:
            return jsonify({"error": "User authentication failed"}), 401
        
        current_app.logger.info(f"Test submission from user: {current_user_email} ({current_user_id})")
        
        # Parse request
        data = request.get_json() or {}
        responses = data.get('responses', [])
        test_mode = data.get('test_mode', 'reading').lower()
        time_taken = data.get('time_taken_seconds', 0)
        
        if not responses:
            return jsonify({"error": "No responses provided"}), 400
        
        # Get test with questions using existing helper function
        test_data = get_test_by_slug(current_app.supabase, slug)
        if not test_data:
            return jsonify({"error": f"Test not found. DATA: {test_data} || SLUG: {slug} || SUPABASE: {current_app.supabase}"}), 404
        
        questions = test_data.get('questions', [])
        if not questions:
            return jsonify({"error": "No questions found for this test"}), 404
        
        # Calculate score and question results
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
        
        # Calculate ELO changes
        elo_results = elo_service.process_test_submission(
            user_id=current_user_id,  # Use Supabase user ID
            test_id=test_data['id'],
            language=test_data['language'],
            skill_type=test_mode,
            questions_data=questions,
            responses=question_results,
            percentage=percentage
        )
        
        # Record test attempt in your schema
        attempt_data = {
            'user_id': current_user_id,  # Use Supabase user ID
            'test_id': test_data['id'],
            'score': score,
            'total_questions': total_questions,
            # 'percentage' is a generated column - don't insert
            # 'elo_change' is a generated column - don't insert
            'test_mode': test_mode,
            'language': test_data['language'],
            'user_elo_before': elo_results['user_elo_before'],
            'test_elo_before': elo_results['test_elo_before'],
            'user_elo_after': elo_results['user_elo_after'],
            'test_elo_after': elo_results['test_elo_after'],
            'was_free_test': True,
            'tokens_consumed': 0
        }
        
        # ALWAYS use service role client for test attempts - bypasses RLS
        if not current_app.supabase_service:
            current_app.logger.error("❌ Service role client not available")
            return jsonify({"error": "Database service not configured properly"}), 500

        try:
            attempt_result = current_app.supabase_service.table('test_attempts').insert(attempt_data).execute()
            attempt_id = attempt_result.data[0]['id'] if attempt_result.data else None
        except Exception as e:
            current_app.logger.error(f"❌ Failed to insert test attempt: {e}")
            current_app.logger.error(f"❌ Attempt data: {attempt_data}")
            if '42501' in str(e):  # RLS policy violation code
                current_app.logger.error("❌ RLS POLICY VIOLATION - using wrong client or policy misconfigured")
            raise

        # Update user stats - get current value first, then increment
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
                'attempt_id': str(attempt_id) if attempt_id else None
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
        
        # Get test basic info
        test_result = current_app.supabase_service.table('tests').select(
            'id, slug, title, language, topic, difficulty, style, tier, transcript, '
            'audio_url, audio_generated, is_custom, is_featured, total_attempts'
        ).eq('slug', slug).eq('is_active', True).execute()
        
        if not test_result.data:
            return jsonify({"error": "Test not found"}), 404
            
        test = test_result.data[0]
        test_id = test['id']
        
        # Get questions
        questions_result = current_app.supabase_service.table('questions').select(
            'id, question_id, question_text, question_type, choices, '
            'correct_answer, answer_explanation, points, audio_url'
        ).eq('test_id', test_id).execute()
        
        # Get ELO ratings
        ratings_result = current_app.supabase_service.table('test_skill_ratings').select(
            'skill_type, elo_rating, volatility, total_attempts'
        ).eq('test_id', test_id).execute()
        
        # Transform ratings into a dictionary
        ratings = {
            rating['skill_type']: {
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
        current_app.logger.error(f"❌ Error fetching test {slug}: {e}")
        return jsonify({"error": str(e)}), 500