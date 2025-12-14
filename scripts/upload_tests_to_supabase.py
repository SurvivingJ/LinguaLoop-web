#!/usr/bin/env python3
"""
Upload Generated Tests to Supabase

Uploads tests from JSON file to Supabase database.

Usage:
    python scripts/upload_tests_to_supabase.py generated_tests_XXXXXX.json

Environment Variables:
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY
    - GEN_USER_ID (UUID of user to attribute tests to)
"""

import os
import sys
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
GEN_USER_ID = os.getenv('GEN_USER_ID')


def upload_tests(json_file: str, user_id: str):
    """Upload tests from JSON to Supabase"""
    from supabase import create_client

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    if not user_id:
        print("ERROR: Set GEN_USER_ID to attribute tests to a user")
        print("  You can find your user ID in Supabase > Authentication > Users")
        sys.exit(1)

    # Load tests from JSON
    print(f"Loading tests from {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        tests = json.load(f)

    print(f"Found {len(tests)} tests to upload")

    # Connect to Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    success = 0
    failed = 0
    errors = []

    for i, test in enumerate(tests, 1):
        try:
            # Prepare test row (without questions)
            test_row = {
                'slug': test['slug'],
                'gen_user': user_id,
                'language': test['language'],
                'topic': test['topic'],
                'difficulty': test['difficulty'],
                'style': test.get('style', 'conversational'),
                'tier': test.get('tier', 'free-tier'),
                'title': test.get('title', test['topic']),
                'transcript': test['transcript'],
                'audio_url': test.get('audio_url', ''),
                'total_attempts': 0,
                'is_active': True,
                'is_featured': False,
                'is_custom': False,
                'generation_model': test.get('generation_model', 'unknown'),
                'audio_generated': test.get('audio_generated', False),
                'created_at': test.get('created_at', datetime.now(timezone.utc).isoformat()),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            # Insert test
            result = supabase.table('tests').insert(test_row).execute()
            test_id = result.data[0]['id']

            # Insert questions
            questions = test.get('questions', [])
            for q in questions:
                question_row = {
                    'test_id': test_id,
                    'question_id': q.get('id', str(__import__('uuid').uuid4())),
                    'question_text': q['question'],
                    'question_type': 'multiple_choice',
                    'choices': q['choices'],
                    'correct_answer': q['answer'],
                    'points': 1
                }
                supabase.table('questions').insert(question_row).execute()

            success += 1
            print(f"[{i}/{len(tests)}] OK - {test['language']} D{test['difficulty']} - {test['topic'][:30]}")

        except Exception as e:
            failed += 1
            errors.append({'test': test['slug'], 'error': str(e)})
            print(f"[{i}/{len(tests)}] FAILED - {test['topic'][:30]}: {e}")

    print("\n" + "="*60)
    print(f"Upload complete: {success} success, {failed} failed")
    print("="*60)

    if errors:
        error_file = f"upload_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(error_file, 'w') as f:
            json.dump(errors, f, indent=2)
        print(f"Errors saved to: {error_file}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_tests_to_supabase.py <json_file>")
        print("\nExample:")
        print("  python scripts/upload_tests_to_supabase.py generated_tests_20251209.json")
        print("\nRequired environment variables:")
        print("  SUPABASE_URL")
        print("  SUPABASE_SERVICE_ROLE_KEY")
        print("  GEN_USER_ID (your user UUID from Supabase)")
        sys.exit(1)

    json_file = sys.argv[1]
    if not os.path.exists(json_file):
        print(f"ERROR: File not found: {json_file}")
        sys.exit(1)

    user_id = GEN_USER_ID
    if not user_id:
        print("GEN_USER_ID not set.")
        user_id = input("Enter your Supabase user UUID: ").strip()
        if not user_id:
            print("ERROR: User ID required")
            sys.exit(1)

    upload_tests(json_file, user_id)


if __name__ == '__main__':
    main()
