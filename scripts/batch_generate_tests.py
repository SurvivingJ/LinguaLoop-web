#!/usr/bin/env python3
"""
Batch Test Generation Script for LinguaLoop

Generates 250 tests across English, Chinese, and Japanese using language-specific
AI models via OpenRouter. Designed for efficient cost-effective batch generation.

Test distribution with balanced difficulty levels:
- 83 English (28 beginner, 28 intermediate, 27 advanced)
- 83 Chinese (28 beginner, 28 intermediate, 27 advanced)
- 84 Japanese (28 beginner, 28 intermediate, 28 advanced)
Total: 250 tests with balanced difficulty distribution

Requirements:
    - pip install requests python-dotenv

Usage:
    1. Set environment variables:
       - BATCH_AUTH_TOKEN: JWT token from authenticated user session
       - API_BASE_URL: Base URL of API (default: http://localhost:5000)

    2. Run: python scripts/batch_generate_tests.py
"""

import os
import sys
import requests
import json
import time
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')
BATCH_AUTH_TOKEN = os.getenv('BATCH_AUTH_TOKEN')

# Topic-Difficulty pairings with balanced distribution across skill levels
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


class BatchTestGenerator:
    """Manages batch test generation with progress tracking and error recovery"""

    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }

    def set_auth_token(self, token: str):
        """Set JWT authentication token for API requests"""
        self.token = token
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
        print(f"✓ Authentication token configured")

    def generate_test(self, config: Dict) -> bool:
        """
        Generate a single test via API

        Args:
            config: Test configuration with language, difficulty, topic, style

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                'language': config['language'],
                'difficulty': config['difficulty'],
                'topic': config['topic'],
                'style': config.get('style', 'conversational'),
                'tier': config.get('tier', 'free-tier')
            }

            response = self.session.post(
                f'{API_BASE_URL}/api/tests/generate_test',
                json=payload,
                timeout=120  # 2 minutes for generation
            )

            if response.status_code == 200:
                data = response.json()
                slug = data.get('slug', 'unknown')
                audio = '🔊' if data.get('audio_generated') else '🔇'
                print(f"  ✓ Test created: {slug} {audio}")
                return True
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                print(f"  ✗ Failed: {error_msg}")
                self.stats['errors'].append({
                    'config': config,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                })
                return False

        except requests.exceptions.Timeout:
            error_msg = "Request timeout (>120s)"
            print(f"  ✗ Timeout: {config['topic']}")
            self.stats['errors'].append({
                'config': config,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
            return False

        except Exception as e:
            error_msg = str(e)
            print(f"  ✗ Exception: {error_msg}")
            self.stats['errors'].append({
                'config': config,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
            return False

    def generate_test_configs(self) -> List[Dict]:
        """
        Generate 250 balanced test configurations with even difficulty distribution

        Distribution per language:
        - Beginner (D1-3): ~28 tests
        - Intermediate (D4-6): ~28 tests
        - Advanced (D7-9): ~27-28 tests

        Returns:
            List of 250 test configuration dictionaries
        """
        configs = []

        # Target: 83 English, 83 Chinese, 84 Japanese
        TARGETS = {'english': 83, 'chinese': 83, 'japanese': 84}

        for language, target in TARGETS.items():
            # Calculate per-level distribution
            per_level = target // 3  # Base: 27 per level
            remainder = target % 3

            # Distribute remainder across levels
            level_targets = {
                'beginner': per_level + (1 if remainder > 0 else 0),
                'intermediate': per_level + (1 if remainder > 1 else 0),
                'advanced': per_level
            }

            # Generate tests for each difficulty level
            for level in ['beginner', 'intermediate', 'advanced']:
                topic_difficulty_pairs = TOPIC_DIFFICULTY_CONFIGS[language][level]
                count = 0

                while count < level_targets[level]:
                    # Cycle through topic-difficulty pairs
                    pair = topic_difficulty_pairs[count % len(topic_difficulty_pairs)]

                    configs.append({
                        'language': language,
                        'difficulty': pair[1],  # difficulty from tuple
                        'topic': pair[0],        # topic from tuple
                        'style': 'conversational'
                    })

                    count += 1

        return configs

    def run(self, configs: List[Dict], delay: float = 2.0, start_from: int = 0):
        """
        Execute batch generation

        Args:
            configs: List of test configurations
            delay: Delay between requests in seconds (default: 2.0)
            start_from: Index to start from (for resuming failed batches)
        """
        print("\n" + "="*70)
        print("  LinguaLoop Batch Test Generation")
        print("="*70)
        print(f"  Total tests: {len(configs)}")
        print(f"  Starting from index: {start_from}")
        print(f"  API: {API_BASE_URL}")
        print(f"  Delay: {delay}s between requests")
        print("="*70 + "\n")

        if not self.token:
            print("❌ ERROR: No authentication token set!")
            print("   Please set BATCH_AUTH_TOKEN environment variable")
            return

        self.stats['start_time'] = datetime.now()

        for i, config in enumerate(configs[start_from:], start=start_from + 1):
            self.stats['total'] += 1

            lang_emoji = {'english': '🇬🇧', 'chinese': '🇨🇳', 'japanese': '🇯🇵'}
            emoji = lang_emoji.get(config['language'], '🌐')

            print(f"[{i}/{len(configs)}] {emoji} {config['language'].title()} D{config['difficulty']} - {config['topic']}")

            if self.generate_test(config):
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1

            # Progress summary every 10 tests
            if i % 10 == 0:
                success_rate = (self.stats['success'] / self.stats['total']) * 100
                print(f"\n  📊 Progress: {self.stats['success']}/{self.stats['total']} "
                      f"({success_rate:.1f}% success)\n")

            # Rate limiting delay (skip on last test)
            if i < len(configs):
                time.sleep(delay)

        self.stats['end_time'] = datetime.now()
        self._print_final_stats()
        self._save_error_log()

    def _print_final_stats(self):
        """Print final batch generation statistics"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        print("\n" + "="*70)
        print("  BATCH GENERATION COMPLETE")
        print("="*70)
        print(f"  Total tests:      {self.stats['total']}")
        print(f"  ✓ Successful:     {self.stats['success']}")
        print(f"  ✗ Failed:         {self.stats['failed']}")
        print(f"  Success rate:     {(self.stats['success']/self.stats['total']*100):.1f}%")
        print(f"  Duration:         {minutes}m {seconds}s")
        print(f"  Avg time/test:    {duration/self.stats['total']:.1f}s")
        print("="*70 + "\n")

        if self.stats['failed'] > 0:
            print(f"⚠️  {self.stats['failed']} tests failed. Check error_log.json for details.")

    def _save_error_log(self):
        """Save error log to JSON file if there were failures"""
        if self.stats['errors']:
            log_file = f"batch_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'summary': {
                        'total_errors': len(self.stats['errors']),
                        'timestamp': datetime.now().isoformat()
                    },
                    'errors': self.stats['errors']
                }, f, indent=2, ensure_ascii=False)
            print(f"📄 Error log saved: {log_file}")


def main():
    """Main execution function"""
    print("\n🚀 Initializing batch test generator...\n")

    # Validate required environment variables
    if not BATCH_AUTH_TOKEN:
        print("❌ ERROR: BATCH_AUTH_TOKEN environment variable not set!")
        print("\nTo obtain a JWT token:")
        print("1. Login to your LinguaLoop account via the web app")
        print("2. Open browser DevTools > Network tab")
        print("3. Look for the /verify-otp request")
        print("4. Copy the 'jwt_token' from the response")
        print("5. Set environment variable: export BATCH_AUTH_TOKEN='your_token_here'")
        print("\nAlternatively, you can pass it directly:")
        print("  BATCH_AUTH_TOKEN='your_token' python scripts/batch_generate_tests.py\n")
        sys.exit(1)

    # Initialize generator
    generator = BatchTestGenerator()
    generator.set_auth_token(BATCH_AUTH_TOKEN)

    # Generate test configurations
    print("📋 Generating test configurations...")
    test_configs = generator.generate_test_configs()

    print(f"✓ Created {len(test_configs)} test configurations")
    print(f"  - English: {len([c for c in test_configs if c['language'] == 'english'])}")
    print(f"  - Chinese: {len([c for c in test_configs if c['language'] == 'chinese'])}")
    print(f"  - Japanese: {len([c for c in test_configs if c['language'] == 'japanese'])}")

    # Print difficulty distribution
    beginner_count = len([c for c in test_configs if c['difficulty'] in [1, 2, 3]])
    intermediate_count = len([c for c in test_configs if c['difficulty'] in [4, 5, 6]])
    advanced_count = len([c for c in test_configs if c['difficulty'] in [7, 8, 9]])

    print(f"\n📊 Difficulty distribution:")
    print(f"  - Beginner (D1-3): {beginner_count}")
    print(f"  - Intermediate (D4-6): {intermediate_count}")
    print(f"  - Advanced (D7-9): {advanced_count}")

    # Check if user wants to resume from specific index
    start_from = int(os.getenv('START_FROM', '0'))
    if start_from > 0:
        print(f"\n⏩ Resuming from test #{start_from}")

    # Start batch generation
    input("\nPress ENTER to start batch generation (or Ctrl+C to cancel)...")
    generator.run(test_configs, delay=2.0, start_from=start_from)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Batch generation interrupted by user")
        print("To resume, set START_FROM environment variable to the last completed test number")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
