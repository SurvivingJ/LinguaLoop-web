#!/usr/bin/env python3
"""
Convert Generated Tests JSON to CSV files for Supabase Import

Splits the JSON data into two CSV files matching the database schema:
- tests.csv (for tests table)
- questions.csv (for questions table)

Usage:
    python scripts/json_to_csv.py generated_tests_XXXXXX.json

Note: gen_user column will be empty - fill it in manually before importing.
"""

import os
import sys
import json
import csv
from datetime import datetime, timezone
from uuid import uuid4


def convert_to_csv(json_file: str):
    """Convert JSON tests to CSV files for Supabase import"""

    # Load tests from JSON
    print(f"Loading tests from {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        tests = json.load(f)

    print(f"Found {len(tests)} tests")

    # Prepare data for CSVs
    tests_rows = []
    questions_rows = []

    now = datetime.now(timezone.utc).isoformat()

    for test in tests:
        # Generate a UUID for this test (will be used as test_id in questions)
        test_id = str(uuid4())

        # Build test row matching db schema
        test_row = {
            'id': test_id,
            'gen_user': '',  # Fill in manually before importing
            'slug': test['slug'],
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
            'created_at': test.get('created_at', now),
            'updated_at': now
        }
        tests_rows.append(test_row)

        # Build question rows
        for q in test.get('questions', []):
            question_row = {
                'id': str(uuid4()),
                'test_id': test_id,
                'question_id': q.get('id', str(uuid4())),
                'question_text': q['question'],
                'question_type': 'multiple_choice',
                'choices': json.dumps(q['choices']),  # JSONB as JSON string
                'correct_answer': json.dumps(q['answer']),  # JSONB as JSON string
                'answer_explanation': '',
                'points': 1,
                'audio_url': '',
                'created_at': now,
                'updated_at': now
            }
            questions_rows.append(question_row)

    # Generate output filenames
    base_name = os.path.splitext(json_file)[0]
    tests_csv = f"{base_name}_tests.csv"
    questions_csv = f"{base_name}_questions.csv"

    # Write tests CSV
    tests_fields = [
        'id', 'gen_user', 'slug', 'language', 'topic', 'difficulty', 'style',
        'tier', 'title', 'transcript', 'audio_url', 'total_attempts',
        'is_active', 'is_featured', 'is_custom', 'generation_model',
        'audio_generated', 'created_at', 'updated_at'
    ]

    with open(tests_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=tests_fields)
        writer.writeheader()
        writer.writerows(tests_rows)

    print(f"Wrote {len(tests_rows)} tests to: {tests_csv}")

    # Write questions CSV
    questions_fields = [
        'id', 'test_id', 'question_id', 'question_text', 'question_type',
        'choices', 'correct_answer', 'answer_explanation', 'points',
        'audio_url', 'created_at', 'updated_at'
    ]

    with open(questions_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=questions_fields)
        writer.writeheader()
        writer.writerows(questions_rows)

    print(f"Wrote {len(questions_rows)} questions to: {questions_csv}")

    print("\n" + "="*60)
    print("CSV files ready for Supabase import")
    print("="*60)
    print("\nBefore importing:")
    print("  - Open the tests CSV and fill in the 'gen_user' column")
    print("    with your Supabase user UUID")
    print("\nImport order (important due to foreign keys):")
    print(f"  1. First import: {tests_csv}")
    print(f"  2. Then import:  {questions_csv}")
    print("\nIn Supabase Dashboard:")
    print("  Table Editor > Select table > Import > Upload CSV")


def main():
    if len(sys.argv) < 2:
        print("Usage: python json_to_csv.py <json_file>")
        print("\nExample:")
        print("  python scripts/json_to_csv.py generated_tests_20251209.json")
        sys.exit(1)

    json_file = sys.argv[1]
    if not os.path.exists(json_file):
        print(f"ERROR: File not found: {json_file}")
        sys.exit(1)

    convert_to_csv(json_file)


if __name__ == '__main__':
    main()
