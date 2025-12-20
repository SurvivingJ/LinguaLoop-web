#!/usr/bin/env python3
"""
Batch Test Generation Script - API Mode

Generates tests via Flask API. Requires running backend and JWT token.

Usage:
    1. Set BATCH_AUTH_TOKEN environment variable
    2. Run: python scripts/batch_generate_tests.py
"""

import os
import sys
import requests
from typing import Dict
from dotenv import load_dotenv

from base_generator import BaseTestGenerator

load_dotenv()

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')
BATCH_AUTH_TOKEN = os.getenv('BATCH_AUTH_TOKEN')


class APITestGenerator(BaseTestGenerator):
    """Generates tests via Flask API"""

    def __init__(self):
        super().__init__(name="LinguaLoop Batch Test Generation (API)")
        self.session = requests.Session()
        self.token = None

    def set_auth_token(self, token: str):
        """Set JWT authentication token"""
        self.token = token
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
        print("Authentication token configured")

    def generate_test(self, config: Dict) -> bool:
        """Generate a single test via API"""
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
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                slug = data.get('slug', 'unknown')
                audio = 'audio' if data.get('audio_generated') else 'no-audio'
                print(f"  OK - {slug[:8]}... ({audio})")
                return True
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                print(f"  FAILED: {error_msg}")
                self.record_error(config, error_msg)
                return False

        except requests.exceptions.Timeout:
            error_msg = "Request timeout (>120s)"
            print(f"  FAILED: {error_msg}")
            self.record_error(config, error_msg)
            return False

        except Exception as e:
            error_msg = str(e)
            print(f"  FAILED: {error_msg}")
            self.record_error(config, error_msg)
            return False

    def _print_header(self, configs, delay, start_from):
        """Override to add API URL info"""
        super()._print_header(configs, delay, start_from)
        print(f"  API: {API_BASE_URL}")
        print("=" * 70 + "\n")


def main():
    print("\nInitializing API test generator...\n")

    if not BATCH_AUTH_TOKEN:
        print("ERROR: BATCH_AUTH_TOKEN not set!")
        print("\nTo obtain a JWT token:")
        print("1. Login to LinguaLoop via the web app")
        print("2. Open browser DevTools > Network tab")
        print("3. Look for the /verify-otp request")
        print("4. Copy the 'jwt_token' from the response")
        print("5. Set: export BATCH_AUTH_TOKEN='your_token'\n")
        sys.exit(1)

    generator = APITestGenerator()
    generator.set_auth_token(BATCH_AUTH_TOKEN)

    # Generate configs
    test_count = int(os.getenv('TEST_COUNT', '250'))
    configs = generator.generate_test_configs(test_count)
    generator.print_config_summary(configs)

    # Check for resume
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
