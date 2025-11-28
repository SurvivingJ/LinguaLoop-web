from openai import OpenAI
import os
import json
from datetime import datetime, timezone
from uuid import uuid4
from typing import Protocol, List, Dict
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Import your PromptService
from .prompt_service import PromptService
from ..utils.question_validator import QuestionValidator

class OpenAIService:
    def __init__(self, openai_client, config, prompt_service=None):
        self.client = openai_client
        self.r2_client = self._create_r2_client(config)
        self.r2_bucket = 'lingualoopaudio'
        
        # Initialize PromptService
        self.prompt_service = prompt_service if prompt_service else PromptService()
    
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
        """Generate listening comprehension transcript using OpenAI with detailed debugging"""
        try:
            print(f"🔧 TRANSCRIPT GENERATION STARTED")
            print(f"🔧   Parameters received:")
            print(f"🔧     Language: '{language}' (type: {type(language)})")
            print(f"🔧     Topic: '{topic}' (type: {type(topic)})")
            print(f"🔧     Difficulty: '{difficulty}' (type: {type(difficulty)})")
            print(f"🔧     Style: '{style}' (type: {type(style)})")
            
            # Validate and sanitize inputs
            safe_language = language or "english"
            safe_topic = topic or "any suitable topic"
            safe_difficulty = difficulty or 1
            safe_style = style or "natural conversation"
            
            print(f"🔧   Sanitized parameters:")
            print(f"🔧     Safe Language: '{safe_language}'")
            print(f"🔧     Safe Topic: '{safe_topic}'")
            print(f"🔧     Safe Difficulty: '{safe_difficulty}'")
            print(f"🔧     Safe Style: '{safe_style}'")
            
            print(f"🔧   Calling prompt_service.format_prompt...")
            
            prompt = self.prompt_service.format_prompt(
                'transcript_generation',
                language=safe_language,
                difficulty=safe_difficulty,
                topic=safe_topic,
                style=safe_style
            )
            
            print(f"🔧   Prompt formatted successfully")
            print(f"🔧   Prompt length: {len(prompt)} characters")
            print(f"🔧   Prompt preview (first 300 chars):")
            print(f"🔧   {'-' * 60}")
            print(f"🔧   {prompt[:300]}...")
            print(f"🔧   {'-' * 60}")
            
            print(f"🔧   Making OpenAI API call...")
            print(f"🔧     Model: gpt-4")
            print(f"🔧     Temperature: 0.7")
            print(f"🔧     Message type: user")
            
            response = self.client.chat.completions.create(
                model="gpt-5-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=1
            )
            
            print(f"🔧   OpenAI API response received")
            print(f"🔧     Response type: {type(response)}")
            print(f"🔧     Choices available: {len(response.choices) if response.choices else 0}")
            
            if not response.choices:
                raise Exception("No choices returned from OpenAI API")
            
            raw_content = response.choices[0].message.content
            print(f"🔧   Raw response content:")
            print(f"🔧     Content type: {type(raw_content)}")
            print(f"🔧     Content length: {len(raw_content) if raw_content else 0}")
            print(f"🔧     Content is None: {raw_content is None}")
            
            if raw_content is None:
                raise Exception("OpenAI returned None content")
            
            transcript = raw_content.strip()
            print(f"🔧   Content after strip():")
            print(f"🔧     Final length: {len(transcript)}")
            print(f"🔧     First 200 chars: '{transcript[:200]}'")
            print(f"🔧     Last 100 chars: '...{transcript[-100:] if len(transcript) > 100 else transcript}'")
            
            # Check if response looks like JSON (from your template)
            if transcript.startswith('{') and transcript.endswith('}'):
                print(f"🔧   Response appears to be JSON format")
                try:
                    import json
                    transcript_data = json.loads(transcript)
                    if isinstance(transcript_data, dict) and 'transcript' in transcript_data:
                        actual_transcript = transcript_data['transcript']
                        print(f"🔧   Extracted transcript from JSON:")
                        print(f"🔧     Extracted length: {len(actual_transcript)}")
                        print(f"🔧     Word count: {transcript_data.get('word_count', 'not provided')}")
                        print(f"🔧     Duration: {transcript_data.get('estimated_duration_seconds', 'not provided')} seconds")
                        transcript = actual_transcript
                    else:
                        print(f"🔧   JSON format but no 'transcript' key found")
                        print(f"🔧   Available keys: {list(transcript_data.keys()) if isinstance(transcript_data, dict) else 'not a dict'}")
                except json.JSONDecodeError as json_error:
                    print(f"🔧   Failed to parse as JSON: {json_error}")
                    print(f"🔧   Using raw response as transcript")
            else:
                print(f"🔧   Response appears to be plain text format")
            
            print(f"✅ TRANSCRIPT GENERATION COMPLETED SUCCESSFULLY")
            print(f"✅   Final transcript length: {len(transcript)} characters")
            print(f"✅   Character breakdown:")
            print(f"✅     Alphanumeric: {sum(c.isalnum() for c in transcript)}")
            print(f"✅     Spaces: {transcript.count(' ')}")
            print(f"✅     Punctuation: {sum(not c.isalnum() and not c.isspace() for c in transcript)}")
            
            return transcript
            
        except Exception as e:
            print(f"❌ TRANSCRIPT GENERATION FAILED")
            print(f"❌   Error type: {type(e).__name__}")
            print(f"❌   Error message: {str(e)}")
            print(f"❌   Error details:")
            
            # Try to get more error context
            import traceback
            error_traceback = traceback.format_exc()
            print(f"❌   Full traceback:")
            for line in error_traceback.split('\n'):
                if line.strip():
                    print(f"❌     {line}")
            
            # Re-raise with more context
            error_msg = f"Transcript generation failed: {e}"
            print(f"❌   Raising exception: {error_msg}")
            raise Exception(error_msg)

    
    def generate_questions(self, transcript, language, difficulty):
        """Generate questions using new multi-call approach"""
        try:
            print(f"🔧 Starting question generation: {language}, difficulty {difficulty}")
            
            # Determine question type distribution
            question_types = self._get_question_type_distribution(difficulty)
            print(f"🔧 Question distribution: {question_types}")
            
            generated_questions = []
            previous_questions = []
            
            # Generate each question individually  
            for i, question_type in enumerate(question_types, 1):
                print(f"🔧 Generating question {i}/5 (Type {question_type})")
                
                question = self._generate_single_question(
                    transcript=transcript,
                    language=language,
                    question_type=question_type,
                    previous_questions=previous_questions
                )
                
                generated_questions.append(question)
                previous_questions.append(question["question"])
                
                print(f"✅ Question {i} generated successfully")
            
            print(f"✅ All 5 questions generated successfully")
            return generated_questions
            
        except Exception as e:
            print(f"❌ Question generation failed: {e}", flush=True)
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
        return distributions.get(difficulty, [2, 2, 2, 2, 2])  # Default to Type 2

    def _generate_single_question(self, transcript: str, language: str, 
                                question_type: int, previous_questions: List[str]) -> Dict:
        """Generate a single question of specified type"""
        
        # Format previous questions for deduplication
        previous_text = "; ".join(previous_questions) if previous_questions else "None"
        
        # Get appropriate prompt template
        prompt = self.prompt_service.format_prompt(
            f'question_type{question_type}',
            language=language,
            transcript=transcript,
            previous_questions=previous_text
        )
        
        # Make API call with timeout
        response = self.client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            timeout=30  # Shorter timeout per question
        )
        
        if not response.choices:
            raise Exception("No response from OpenAI")
            
        content = response.choices[0].message.content.strip()
        
        # Parse and validate JSON
        try:
            question_data = json.loads(content)
            validated_question = QuestionValidator.validate_question_format(question_data)
            
            # Check for semantic overlap
            if QuestionValidator.check_semantic_overlap(
                validated_question["Question"], 
                previous_questions
            ):
                print(f"⚠️ Potential semantic overlap detected, but proceeding")
            
            # Add UUID and metadata
            return {
                'id': str(uuid4()),
                'question': validated_question["Question"],
                'choices': validated_question["Options"], 
                'answer': validated_question["Answer"]
            }
            
        except json.JSONDecodeError as e:
            print(e, flush=True)
            raise Exception(f"Invalid JSON response: {e}")
        except ValueError as e:
            print(e, flush=True)
            raise Exception(f"Question validation failed: {e}")




    
    def _clean_json_response(self, content):
        """Clean AI response that might be wrapped in markdown code blocks"""
        # Remove markdown code blocks
        if content.startswith('```'):
            content = content.replace('```json', '', 1)
        if content.startswith('```'):
            content = content.replace('```', '', 1)
        if content.endswith('```'):
            content = content.rsplit('```', 1)[0]
        
        # Remove any leading/trailing whitespace
        content = content.strip()
        
        # Sometimes AI adds extra text before or after JSON
        # Try to extract just the JSON part
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_part = content[start_idx:end_idx+1]
            print(f"🔧 Extracted JSON part: {json_part[:200]}...")
            return json_part
        
        # If no array found, try object
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_part = content[start_idx:end_idx+1]
            print(f"🔧 Extracted JSON object: {json_part[:200]}...")
            return json_part
        
        print(f"🔧 No JSON cleaning needed")
        return content
    
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
        
        # Validate choices
        if not isinstance(validated['choices'], list) or len(validated['choices']) != 4:
            print(f"⚠️ Invalid choices for question {question_id}, using defaults")
            validated['choices'] = ['Option A', 'Option B', 'Option C', 'Option D']
        
        # Validate answer
        if validated['answer'] not in validated['choices']:
            print(f"⚠️ Answer '{validated['answer']}' not in choices for question {question_id}")
            validated['answer'] = validated['choices'][0]
        
        # Validate question text
        if not validated['question'] or validated['question'] == '[Missing question text]':
            raise ValueError(f"Question {question_id} has no valid question text")
        
        return validated
    
    def generate_audio(self, text, slug):
        """Generate TTS audio and upload directly to R2"""
        try:
            print(f"🔧 Generating audio for {slug} ({len(text)} chars)")
            
            # Generate audio with OpenAI
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="mp3",
                speed=1.0
            )
            
            # Upload directly to R2 - no local save
            self.r2_client.put_object(
                Bucket=self.r2_bucket,
                Key=f'{slug}.mp3',
                Body=response.content,
                ContentType='audio/mpeg',
                CacheControl='public, max-age=31536000'
            )
            
            print(f"✅ Uploaded {slug}.mp3 to R2")
            return True
            
        except Exception as e:
            error_msg = f"Audio upload failed for {slug}: {e}"
            print(f"❌ {error_msg}")
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
            
            print(f"🔧 Moderating content ({len(content)} chars)")
            
            # Call OpenAI moderation API
            response = self.client.moderations.create(input=content.strip())
            
            # Extract results
            result = response.results[0]
            is_flagged = result.flagged
            
            # Get flagged categories
            flagged_categories = []
            if is_flagged:
                for category, flagged in result.categories.__dict__.items():
                    if flagged:
                        flagged_categories.append(category)
            
            # Get category scores for debugging
            category_scores = result.category_scores.__dict__
            
            print(f"✅ Content moderation complete - Safe: {not is_flagged}")
            
            return {
                'is_safe': not is_flagged,
                'flagged_categories': flagged_categories,
                'category_scores': category_scores,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Content moderation error: {e}"
            print(f"❌ {error_msg}")
            return {
                'is_safe': True,  # Fail-safe: allow content if moderation fails
                'flagged_categories': [],
                'category_scores': {},
                'error': str(e)
            }

    # Utility methods for prompt management
    def reload_prompts(self):
        """Reload prompt templates from files (useful for development)"""
        if hasattr(self.prompt_service, '_prompt_cache'):
            self.prompt_service._prompt_cache.clear()
            print("🔄 Prompt cache cleared - templates will reload on next use")
        else:
            print("🔄 Prompt service doesn't support cache clearing")
    
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