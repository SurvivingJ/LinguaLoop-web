#!/usr/bin/env python3
"""
Batch Test Generation Script - JSON Output

Generates tests locally using AI services and saves to JSON file.
No database connection required. Upload to Supabase separately.

Requirements:
    pip install openai python-dotenv boto3

Usage:
    python scripts/batch_generate_to_json.py

Environment Variables:
    - USE_OPENROUTER=true (recommended)
    - OPENROUTER_API_KEY=your_key
    - Or: OPENAI_API_KEY=your_key
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Dict
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from services.prompt_service import PromptService
from utils.question_validator import QuestionValidator

# Topic-Difficulty pairings
TOPIC_DIFFICULTY_CONFIGS = {
    'english': {
        'beginner': [
            ('Daily routines', 1),
            ('Family members', 1),
            ('Basic greetings', 2),
            ('Weather descriptions', 2),
            ('Food and drinks', 3),
            ('Simple shopping', 3),
            ('Colors and numbers', 1),
            ('Transportation basics', 2),
            ('Asking directions', 3)
        ],
        'intermediate': [
            ('Travel planning', 4),
            ('Work and careers', 5),
            ('Health and fitness', 4),
            ('Technology use', 5),
            ('Environmental issues', 6),
            ('Social customs', 6),
            ('Education systems', 4),
            ('Media and news', 5),
            ('Cultural events', 6)
        ],
        'advanced': [
            ('Economic trends', 7),
            ('Political systems', 8),
            ('Scientific research', 7),
            ('Philosophy and ethics', 9),
            ('Global diplomacy', 8),
            ('Art history', 7),
            ('Legal frameworks', 8),
            ('Advanced technology', 9),
            ('Academic discourse', 9)
        ]
    },
    'chinese': {
        'beginner': [
            ('Self introduction', 1),
            ('Family structure', 1),
            ('Daily activities', 2),
            ('Food ordering', 2),
            ('Shopping basics', 3),
            ('Time and dates', 1),
            ('Locations', 2),
            ('Hobbies', 3),
            ('Weather talk', 2)
        ],
        'intermediate': [
            ('Chinese New Year', 4),
            ('Tea culture', 5),
            ('Modern cities', 4),
            ('Family values', 5),
            ('Traditional medicine', 6),
            ('Education system', 6),
            ('Work culture', 4),
            ('Food culture', 5),
            ('Social media', 6)
        ],
        'advanced': [
            ('Economic reform', 7),
            ('Ancient philosophy', 8),
            ('Technology innovation', 7),
            ('Cultural revolution', 9),
            ('Belt and Road', 8),
            ('Classical literature', 7),
            ('Modern governance', 8),
            ('Scientific achievements', 9),
            ('Historical dynasties', 9)
        ]
    },
    'japanese': {
        'beginner': [
            ('Greetings', 1),
            ('Family terms', 1),
            ('Daily life', 2),
            ('Food basics', 2),
            ('Numbers and counting', 3),
            ('Train travel', 1),
            ('School life', 2),
            ('Seasons', 3),
            ('Simple requests', 2)
        ],
        'intermediate': [
            ('Cherry blossoms', 4),
            ('Anime culture', 5),
            ('Tea ceremony', 4),
            ('Martial arts', 5),
            ('Traditional crafts', 6),
            ('Japanese cuisine', 6),
            ('Work etiquette', 4),
            ('Festival traditions', 5),
            ('Modern fashion', 6)
        ],
        'advanced': [
            ('Buddhism influence', 7),
            ('Corporate culture', 8),
            ('Technology innovation', 7),
            ('Post-war reconstruction', 9),
            ('Constitutional monarchy', 8),
            ('Classical poetry', 7),
            ('Economic miracle', 8),
            ('Architectural evolution', 9),
            ('Geopolitical role', 9)
        ]
    }
}

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


class LocalTestGenerator:
    """Generates tests locally without API calls to Flask backend"""

    def __init__(self):
        self.prompt_service = PromptService()
        self.client = None
        self.use_openrouter = False
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
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

    def generate_transcript(self, language: str, topic: str, difficulty: int, style: str) -> str:
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

    def generate_questions(self, transcript: str, language: str, difficulty: int) -> List[Dict]:
        """Generate questions for transcript"""
        question_types = self._get_question_type_distribution(difficulty)
        questions = []
        previous_questions = []

        for q_type in question_types:
            question = self._generate_single_question(
                transcript, language, q_type, previous_questions
            )
            questions.append(question)
            previous_questions.append(question["question"])

        return questions

    def _get_question_type_distribution(self, difficulty: int) -> List[int]:
        """Get question type distribution based on difficulty"""
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
            raise Exception(f"Model returned None content")

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
            return content[start_idx:end_idx+1]

        # Extract JSON array
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            return content[start_idx:end_idx+1]

        return content

    def generate_test(self, config: Dict) -> Dict:
        """Generate a complete test and return as dict"""
        language = config['language']
        difficulty = config['difficulty']
        topic = config['topic']
        style = config.get('style', 'conversational')

        # Generate transcript
        transcript = self.generate_transcript(language, topic, difficulty, style)

        # Generate questions
        questions = self.generate_questions(transcript, language, difficulty)

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
            'gen_user': None,  # Will be set when uploading to Supabase
            'questions': questions,
            'created_at': now,
            'updated_at': now
        }

    def generate_test_configs(self, count: int = 250) -> List[Dict]:
        """Generate balanced test configurations"""
        configs = []
        TARGETS = {'english': 83, 'chinese': 83, 'japanese': 84}

        for language, target in TARGETS.items():
            per_level = target // 3
            remainder = target % 3

            level_targets = {
                'beginner': per_level + (1 if remainder > 0 else 0),
                'intermediate': per_level + (1 if remainder > 1 else 0),
                'advanced': per_level
            }

            for level in ['beginner', 'intermediate', 'advanced']:
                topic_pairs = TOPIC_DIFFICULTY_CONFIGS[language][level]
                c = 0
                while c < level_targets[level]:
                    pair = topic_pairs[c % len(topic_pairs)]
                    configs.append({
                        'language': language,
                        'difficulty': pair[1],
                        'topic': pair[0],
                        'style': 'conversational'
                    })
                    c += 1

        return configs[:count]

    def run(self, configs: List[Dict], delay: float = 2.0, start_from: int = 0):
        """Run batch generation and save to JSON"""
        print("\n" + "="*70)
        print("  LinguaLoop Batch Test Generation (JSON Output)")
        print("="*70)
        print(f"  Total tests: {len(configs)}")
        print(f"  Starting from: {start_from}")
        print(f"  Delay: {delay}s between requests")
        print("="*70 + "\n")

        self.stats['start_time'] = datetime.now()

        for i, config in enumerate(configs[start_from:], start=start_from + 1):
            self.stats['total'] += 1

            lang_emoji = {'english': 'EN', 'chinese': 'CN', 'japanese': 'JP'}
            emoji = lang_emoji.get(config['language'], '??')

            print(f"[{i}/{len(configs)}] {emoji} {config['language'].title()} D{config['difficulty']} - {config['topic']}")

            try:
                test = self.generate_test(config)
                self.generated_tests.append(test)
                self.stats['success'] += 1
                print(f"  OK - {test['slug'][:8]}...")
            except Exception as e:
                self.stats['failed'] += 1
                self.stats['errors'].append({
                    'config': config,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                print(f"  FAILED: {e}")

            # Progress summary
            if i % 10 == 0:
                rate = (self.stats['success'] / self.stats['total']) * 100
                print(f"\n  Progress: {self.stats['success']}/{self.stats['total']} ({rate:.1f}%)\n")

            # Rate limit
            #if i < len(configs):
            #    time.sleep(delay)

        self.stats['end_time'] = datetime.now()
        self._save_results()
        self._print_stats()

    def _save_results(self):
        """Save generated tests to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save tests
        output_file = f"generated_tests_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.generated_tests, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(self.generated_tests)} tests to: {output_file}")

        # Save errors if any
        if self.stats['errors']:
            error_file = f"batch_errors_{timestamp}.json"
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats['errors'], f, indent=2, ensure_ascii=False)
            print(f"Saved errors to: {error_file}")

    def _print_stats(self):
        """Print final statistics"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        mins = int(duration // 60)
        secs = int(duration % 60)

        print("\n" + "="*70)
        print("  BATCH COMPLETE")
        print("="*70)
        print(f"  Total: {self.stats['total']}")
        print(f"  Success: {self.stats['success']}")
        print(f"  Failed: {self.stats['failed']}")
        print(f"  Duration: {mins}m {secs}s")
        print("="*70 + "\n")


def main():
    print("\nInitializing local test generator...\n")

    generator = LocalTestGenerator()

    try:
        generator.initialize_ai_client()
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nSet one of these environment variables:")
        print("  USE_OPENROUTER=true")
        print("  OPENROUTER_API_KEY=your_key")
        print("Or:")
        print("  OPENAI_API_KEY=your_key")
        sys.exit(1)

    # Generate configs
    test_count = int(os.getenv('TEST_COUNT', '250'))
    configs = generator.generate_test_configs(test_count)

    print(f"Generated {len(configs)} test configurations")
    print(f"  English: {len([c for c in configs if c['language'] == 'english'])}")
    print(f"  Chinese: {len([c for c in configs if c['language'] == 'chinese'])}")
    print(f"  Japanese: {len([c for c in configs if c['language'] == 'japanese'])}")

    start_from = int(os.getenv('START_FROM', '0'))
    if start_from > 0:
        print(f"\nResuming from test #{start_from}")

    input("\nPress ENTER to start (Ctrl+C to cancel)...")
    generator.run(configs, delay=2.0, start_from=start_from)


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
