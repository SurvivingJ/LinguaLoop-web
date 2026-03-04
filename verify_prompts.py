#!/usr/bin/env python3
"""
Verify that prompt templates exist in database.
Run with: python verify_prompts.py
"""
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from services.supabase_factory import get_supabase_admin

def main():
    client = get_supabase_admin()

    print("=" * 60)
    print("Checking prompt_templates table...")
    print("=" * 60)

    # Check for test generation prompts
    test_prompts = [
        'prose_generation',
        'question_literal_detail',
        'question_vocabulary_context',
        'question_main_idea',
        'question_supporting_detail',
        'question_inference',
        'question_author_purpose'
    ]

    for task_name in test_prompts:
        response = client.table('prompt_templates') \
            .select('task_name, language_id, is_active, created_at') \
            .eq('task_name', task_name) \
            .eq('is_active', True) \
            .execute()

        if response.data:
            print(f"✓ {task_name:35} - Found ({len(response.data)} rows)")
        else:
            print(f"✗ {task_name:35} - NOT FOUND")

    print("\n" + "=" * 60)
    print("Fetching sample prompt to verify format...")
    print("=" * 60)

    # Get one question prompt to check format
    response = client.table('prompt_templates') \
        .select('template_text') \
        .eq('task_name', 'question_literal_detail') \
        .eq('language_id', 2) \
        .eq('is_active', True) \
        .limit(1) \
        .execute()

    if response.data:
        template = response.data[0]['template_text']
        print("\nSample: question_literal_detail template:")
        print("-" * 60)
        # Show first 500 chars
        print(template[:500])
        print("...")

        # Check for correct field names
        if '{prose}' in template:
            print("\n✓ Uses {prose} placeholder")
        else:
            print("\n✗ Missing {prose} placeholder")

        if '"Question":' in template:
            print("✓ Uses 'Question' field in JSON")
        else:
            print("✗ Missing 'Question' field in JSON")

        if '"Options":' in template:
            print("✓ Uses 'Options' field in JSON")
        else:
            print("✗ Missing 'Options' field in JSON")
    else:
        print("\n✗ No template found - MIGRATION NOT RUN!")
        print("\nAction Required:")
        print("  1. Go to Supabase SQL Editor")
        print("  2. Copy content from: migrations/test_generation_tables.sql")
        print("  3. Run the SQL")

    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
