#!/usr/bin/env python3
"""
Batch Test Generation Script - JSON Output

Generates tests locally using AI services and saves to JSON file.
No database connection required. Upload to Supabase separately.

Usage:
    USE_OPENROUTER=true OPENROUTER_API_KEY=key python scripts/batch_generate_to_json.py
"""

import os
import sys
import json
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Dict
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from base_generator import BaseTestGenerator
from services.prompt_service import PromptService
from utils.question_validator import QuestionValidator

# Language-specific model configuration for OpenRouter
MODEL_CONFIG = {
    'english': {
        'transcript': 'google/gemini-2.0-flash-001',
        'questions': 'google/gemini-2.0-flash-001'
    },
    'chinese': {
        'transcript': 'deepseek/deepseek-chat',
        'questions': 'deepseek/deepseek-chat'
    },
    'japanese': {
        'transcript': 'qwen/qwen-2.5-72b-instruct',
        'questions': 'qwen/qwen-2.5-72b-instruct'
    }
}


class LocalTestGenerator(BaseTestGenerator):
    """Generates tests locally using AI services"""

    def __init__(self):
        super().__init__(name="LinguaDojo Batch Test Generation (JSON)")
        self.prompt_service = PromptService()
        self.client = None
        self.use_openrouter = False
        self.generated_tests = []

    def initialize_ai_client(self):
        """Initialize OpenAI/OpenRouter client"""
        from openai import OpenAI

        use_openrouter = os.getenv('USE_OPENROUTER', 'false').lower() == 'true'
        openrouter_key = os.getenv('OPENROUTER_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')

        if use_openrouter and openrouter_key:
            self.client = OpenAI(
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1"
            )
            self.use_openrouter = True
            print("Using OpenRouter API")
        elif openai_key:
            self.client = OpenAI(api_key=openai_key)
            self.use_openrouter = False
            print("Using OpenAI API")
        else:
            raise ValueError("No API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY")

    def _get_model(self, language: str, task: str) -> str:
        """Get model for language and task"""
        if not self.use_openrouter:
            return "gpt-4o-mini"

        lang_key = language.lower()
        config = MODEL_CONFIG.get(lang_key, MODEL_CONFIG['english'])
        return config.get(task, 'google/gemini-2.0-flash-001')

    def generate_test(self, config: Dict) -> bool:
        """Generate a single test and store it"""
        try:
            test = self._create_test(config)
            self.generated_tests.append(test)
            print(f"  OK - {test['slug'][:8]}...")
            return True
        except Exception as e:
            print(f"  FAILED: {e}")
            self.record_error(config, str(e))
            return False

    def _create_test(self, config: Dict) -> Dict:
        """Create a complete test object"""
        language = config['language']
        difficulty = config['difficulty']
        topic = config['topic']
        style = config.get('style', 'conversational')

        # Generate transcript
        transcript = self._generate_transcript(language, topic, difficulty, style)

        # Generate questions
        questions = self._generate_questions(transcript, language, difficulty)

        # Build test object
        slug = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        return {
            'slug': slug,
            'language': language,
            'topic': topic,
            'difficulty': difficulty,
            'style': style,
            'tier': config.get('tier', 'free-tier'),
            'title': topic,
            'transcript': transcript,
            'audio_url': '',
            'total_attempts': 0,
            'is_active': True,
            'is_featured': False,
            'is_custom': False,
            'generation_model': self._get_model(language, 'transcript'),
            'audio_generated': False,
            'gen_user': None,
            'questions': questions,
            'created_at': now,
            'updated_at': now
        }

    def _generate_transcript(self, language: str, topic: str, difficulty: int, style: str) -> str:
        """Generate transcript using AI"""
        prompt = self.prompt_service.format_prompt(
            'transcript_generation',
            language=language,
            difficulty=difficulty,
            topic=topic,
            style=style
        )

        model = self._get_model(language, 'transcript')
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=1
        )

        raw_content = response.choices[0].message.content
        if raw_content is None:
            raise Exception("API returned None content")

        transcript = raw_content.strip()

        # Handle JSON-wrapped responses
        if transcript.startswith('{') and transcript.endswith('}'):
            try:
                data = json.loads(transcript)
                if isinstance(data, dict) and 'transcript' in data:
                    transcript = data['transcript']
            except json.JSONDecodeError:
                pass

        return transcript

    def _generate_questions(self, transcript: str, language: str, difficulty: int) -> List[Dict]:
        """Generate questions for transcript"""
        distributions = {
            1: [1, 1, 1, 1, 1], 2: [1, 1, 1, 1, 1], 3: [1, 1, 1, 2, 2],
            4: [1, 1, 1, 2, 2], 5: [1, 2, 2, 2, 3], 6: [1, 2, 2, 2, 3],
            7: [2, 2, 2, 2, 3], 8: [2, 2, 2, 3, 3], 9: [2, 2, 3, 3, 3]
        }
        question_types = distributions.get(difficulty, [2, 2, 2, 2, 2])

        questions = []
        previous_questions = []

        for q_type in question_types:
            question = self._generate_single_question(transcript, language, q_type, previous_questions)
            questions.append(question)
            previous_questions.append(question["question"])

        return questions

    def _generate_single_question(self, transcript: str, language: str,
                                   question_type: int, previous_questions: List[str]) -> Dict:
        """Generate a single question"""
        previous_text = "; ".join(previous_questions) if previous_questions else "None"

        prompt = self.prompt_service.format_prompt(
            f'question_type{question_type}',
            language=language,
            transcript=transcript,
            previous_questions=previous_text
        )

        model = self._get_model(language, 'questions')
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            timeout=30
        )

        raw_content = response.choices[0].message.content
        if raw_content is None:
            raise Exception("Model returned None content")

        content = self._clean_json_response(raw_content.strip())
        question_data = json.loads(content)
        validated = QuestionValidator.validate_question_format(question_data)

        return {
            'id': str(uuid4()),
            'question': validated["Question"],
            'choices': validated["Options"],
            'answer': validated["Answer"]
        }

    def _clean_json_response(self, content: str) -> str:
        """Clean markdown/extra text from JSON response"""
        if content.startswith('```'):
            content = content.replace('```json', '', 1).replace('```', '', 1)
        if content.endswith('```'):
            content = content.rsplit('```', 1)[0]
        content = content.strip()

        # Extract JSON object
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            return content[start_idx:end_idx + 1]

        # Extract JSON array
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            return content[start_idx:end_idx + 1]

        return content

    def run(self, configs, delay=2.0, start_from=0):
        """Override to save results after run"""
        super().run(configs, delay=delay, start_from=start_from)
        self._save_results()

    def _save_results(self):
        """Save generated tests to JSON file"""
        if not self.generated_tests:
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"generated_tests_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.generated_tests, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(self.generated_tests)} tests to: {output_file}")


def main():
    print("\nInitializing local test generator...\n")

    generator = LocalTestGenerator()

    try:
        generator.initialize_ai_client()
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nSet one of these environment variables:")
        print("  USE_OPENROUTER=true OPENROUTER_API_KEY=your_key")
        print("Or:")
        print("  OPENAI_API_KEY=your_key")
        sys.exit(1)

    # Generate configs
    test_count = int(os.getenv('TEST_COUNT', '250'))
    configs = generator.generate_test_configs(test_count)
    generator.print_config_summary(configs)

    # Check for resume
    start_from = int(os.getenv('START_FROM', '0'))
    if start_from > 0:
        print(f"\nResuming from test #{start_from}")

    input("\nPress ENTER to start (Ctrl+C to cancel)...")
    generator.run(configs, delay=0, start_from=start_from)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        print("Set START_FROM env var to resume")
        sys.exit(0)
    except Exception as e:
        print(f"\nFATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
