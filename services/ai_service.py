from openai import OpenAI, APIConnectionError, RateLimitError, APITimeoutError
import json
import logging
import traceback
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Dict
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from services.prompt_service import PromptService
from services.llm_service import call_llm as llm_call
from utils.question_validator import QuestionValidator

_RETRYABLE_ERRORS = (APIConnectionError, RateLimitError, APITimeoutError, ConnectionError, TimeoutError)
_retry_api = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(_RETRYABLE_ERRORS),
    before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
    reraise=True,
)

logger = logging.getLogger(__name__)

class AIService:
    """AI generation service supporting OpenAI and OpenRouter"""

    def __init__(self, openai_client, config, prompt_service=None, use_openrouter=False):
        self.client = openai_client
        self.config = config
        self.r2_client = self._create_r2_client(config)
        self.r2_bucket = config.R2_BUCKET_NAME

        # Initialize PromptService
        self.prompt_service = prompt_service if prompt_service else PromptService()

        # OpenRouter configuration - use Config as source of truth
        self.use_openrouter = use_openrouter
    
    def _create_r2_client(self, config):
        """Create Cloudflare R2 client using boto3"""
        return boto3.client(
            's3',
            endpoint_url=f'https://{config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
            aws_access_key_id=config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
            region_name='auto'
        )

    def generate_transcript(self, language, topic, difficulty, style):
        """Generate listening comprehension transcript using language-specific models"""
        try:
            safe_language = language or "english"
            safe_topic = topic or "any suitable topic"
            safe_difficulty = difficulty or 1
            safe_style = style or "natural conversation"

            prompt = self.prompt_service.format_prompt(
                'transcript_generation',
                language=safe_language,
                difficulty=safe_difficulty,
                topic=safe_topic,
                style=safe_style
            )

            transcript = llm_call(
                prompt,
                language=safe_language,
                temperature=1.0,
                response_format='text',
            )

            transcript = transcript.strip()

            # Handle JSON-wrapped responses (some models return {"transcript": "..."})
            if transcript.startswith('{') and transcript.endswith('}'):
                try:
                    transcript_data = json.loads(transcript)
                    if isinstance(transcript_data, dict) and 'transcript' in transcript_data:
                        transcript = transcript_data['transcript']
                except json.JSONDecodeError:
                    pass  # Use raw content if JSON parsing fails

            return transcript

        except Exception as e:
            logger.error(f"Transcript generation failed: {e}")
            logger.debug(traceback.format_exc())
            raise Exception(f"Transcript generation failed: {e}")

    
    def generate_questions(self, transcript, language, difficulty):
        """Generate questions using multi-call approach"""
        try:
            question_types = self._get_question_type_distribution(difficulty)
            generated_questions = []
            previous_questions = []

            for i, question_type in enumerate(question_types, 1):
                question = self._generate_single_question(
                    transcript=transcript,
                    language=language,
                    question_type=question_type,
                    previous_questions=previous_questions
                )

                generated_questions.append(question)
                previous_questions.append(question["question"])

            return generated_questions

        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            raise Exception(f"Question generation failed: {str(e)}")

    def _get_question_type_distribution(self, difficulty: int) -> List[int]:
        """Return list of question types based on difficulty"""
        distributions = {
            1: [1, 1, 1, 1, 1],
            2: [1, 1, 1, 1, 1],
            3: [1, 1, 1, 2, 2],
            4: [1, 1, 1, 2, 2],
            5: [1, 2, 2, 2, 3],
            6: [1, 2, 2, 2, 3],
            7: [2, 2, 2, 2, 3],
            8: [2, 2, 2, 3, 3],
            9: [2, 2, 3, 3, 3]
        }
        return distributions.get(difficulty, [2, 2, 2, 2, 2])

    def _generate_single_question(self, transcript: str, language: str,
                                question_type: int, previous_questions: List[str]) -> Dict:
        """Generate a single question of specified type using language-specific model"""

        previous_text = "; ".join(previous_questions) if previous_questions else "None"

        prompt = self.prompt_service.format_prompt(
            f'question_type{question_type}',
            language=language,
            transcript=transcript,
            previous_questions=previous_text
        )

        try:
            question_data = llm_call(
                prompt,
                language=language,
                temperature=1.0,
                response_format='json',
                timeout=30,
            )

            logger.debug(f"Question Type {question_type}, Language: {language}")

            validated_question = QuestionValidator.validate_question_format(question_data)
            QuestionValidator.check_semantic_overlap(validated_question["Question"], previous_questions)

            logger.debug(f"Question generated successfully for type {question_type}")
            return {
                'id': str(uuid4()),
                'question': validated_question["Question"],
                'choices': validated_question["Options"],
                'answer': validated_question["Answer"]
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e}")
            raise Exception(f"Invalid JSON response: {e}")
        except ValueError as e:
            logger.error(f"Validation Error: {e}")
            raise Exception(f"Question validation failed: {e}")




    
    def _validate_question_structure(self, question, question_id, starting_elo, timestamp):
        """Validate and fix question structure"""
        if not isinstance(question, dict):
            raise ValueError(f"Expected question to be dict, got {type(question)}")

        validated = {
            'id': question.get('id', question_id),
            'question': question.get('question', '[Missing question text]'),
            'choices': question.get('choices', ['Option A', 'Option B', 'Option C', 'Option D']),
            'answer': question.get('answer', 'Option A'),
            'ratings': {
                'listening': {
                    'rating': starting_elo,
                    'volatility': 1.0,
                    'attempts': 0,
                    'last_attempt': timestamp
                },
                'reading': {
                    'rating': starting_elo,
                    'volatility': 1.0,
                    'attempts': 0,
                    'last_attempt': timestamp
                },
                'dictation': {
                    'rating': starting_elo,
                    'volatility': 1.0,
                    'attempts': 0,
                    'last_attempt': timestamp
                }
            }
        }

        if not isinstance(validated['choices'], list) or len(validated['choices']) != 4:
            validated['choices'] = ['Option A', 'Option B', 'Option C', 'Option D']

        if validated['answer'] not in validated['choices']:
            validated['answer'] = validated['choices'][0]

        if not validated['question'] or validated['question'] == '[Missing question text]':
            raise ValueError(f"Question {question_id} has no valid question text")

        return validated
    
    @_retry_api
    def generate_audio(self, text, slug):
        """Generate TTS audio and upload directly to R2"""
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="mp3",
                speed=1.0
            )

            self.r2_client.put_object(
                Bucket=self.r2_bucket,
                Key=f'{slug}.mp3',
                Body=response.content,
                ContentType='audio/mpeg',
                CacheControl='public, max-age=31536000'
            )

            return True

        except Exception as e:
            error_msg = f"Audio upload failed for {slug}: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
    def get_starting_elo(self, difficulty):
        """Get starting ELO rating based on difficulty level"""
        difficulty_to_elo = {
            "1": 800, "2": 950, "3": 1100,
            "4": 1250, "5": 1400, "6": 1550,
            "7": 1700, "8": 1850, "9": 2000
        }
        return difficulty_to_elo.get(str(difficulty), 1400)

    def moderate_content(self, content):
        """Check content safety using OpenAI's moderation API"""
        try:
            if not content or not content.strip():
                return {
                    'is_safe': False,
                    'flagged_categories': ['empty_content'],
                    'category_scores': {},
                    'error': 'No content provided'
                }

            response = self.client.moderations.create(input=content.strip())

            result = response.results[0]
            is_flagged = result.flagged

            flagged_categories = []
            if is_flagged:
                for category, flagged in result.categories.__dict__.items():
                    if flagged:
                        flagged_categories.append(category)

            category_scores = result.category_scores.__dict__

            return {
                'is_safe': not is_flagged,
                'flagged_categories': flagged_categories,
                'category_scores': category_scores,
                'error': None
            }

        except Exception as e:
            error_msg = f"Content moderation error: {e}"
            logger.error(error_msg)
            return {
                'is_safe': True,
                'flagged_categories': [],
                'category_scores': {},
                'error': str(e)
            }

    def reload_prompts(self):
        """Reload prompt templates from files"""
        if hasattr(self.prompt_service, '_prompt_cache'):
            self.prompt_service._prompt_cache.clear()
    
    def get_available_prompts(self):
        """Get list of available prompt templates"""
        return self.prompt_service.get_available_prompts()
    
    def get_prompt_preview(self, prompt_name: str, max_length: int = 200):
        """Get a preview of a prompt template for debugging"""
        try:
            prompt_content = self.prompt_service.load_prompt(prompt_name)
            if len(prompt_content) > max_length:
                return prompt_content[:max_length] + "..."
            return prompt_content
        except Exception as e:
            return f"Error loading prompt: {e}"