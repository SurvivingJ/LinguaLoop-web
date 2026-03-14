#!/usr/bin/env python3
"""
Validate and fix word sense definitions and example sentences.

Definitions should be in the SAME language as the word (Chinese definitions
for Chinese words, etc.). Example sentences should also be in the target language.
Uses LLM to regenerate bad entries when --fix is specified.

Usage:
    python scripts/validate_sense_languages.py --language cn [--limit 100] [--fix] [--dry-run]

Options:
    --language CODE   Required. Language code: cn, en, jp
    --limit N         Process at most N senses (default: all)
    --fix             Actually update bad entries via LLM (default: report only)
    --dry-run         Show what would be fixed without writing to DB
"""

import sys
import os
import argparse
import logging
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.vocabulary.language_detection import check_text_language

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TARGET_LANGUAGES = {
    'cn': 'Chinese',
    'en': 'English',
    'jp': 'Japanese',
}


def get_openai_client():
    """Initialize OpenAI client (direct or via OpenRouter)."""
    from openai import OpenAI

    if Config.USE_OPENROUTER and Config.OPENROUTER_API_KEY:
        return OpenAI(
            api_key=Config.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
    elif Config.OPENAI_API_KEY:
        return OpenAI(api_key=Config.OPENAI_API_KEY)
    else:
        raise RuntimeError("OpenAI or OpenRouter API key required")


def regenerate_definition(client, lemma: str, language_name: str,
                          example_sentence: str, model: str) -> str | None:
    """Generate a new definition in the target language for a word."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    f"Provide a concise definition in {language_name} for the "
                    f"{language_name} word \"{lemma}\". "
                    f"The definition must be written entirely in {language_name}. "
                    f"Context sentence: \"{example_sentence[:300]}\"\n\n"
                    f"Reply with ONLY a JSON object: {{\"definition\": \"...\"}}"
                )
            }],
            temperature=0.0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        return data.get('definition', '').strip() or None
    except Exception as e:
        logger.error(f"Definition regeneration failed for '{lemma}': {e}")
        return None


def regenerate_example_sentence(client, lemma: str, language_name: str,
                                model: str) -> str | None:
    """Generate a new example sentence in the target language."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    f"Write a simple example sentence in {language_name} using the word \"{lemma}\". "
                    f"The sentence should be natural and demonstrate the word's meaning. "
                    f"Reply with ONLY a JSON object: {{\"sentence\": \"...\"}}"
                )
            }],
            temperature=0.3,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        return data.get('sentence', '').strip() or None
    except Exception as e:
        logger.error(f"Example sentence regeneration failed for '{lemma}': {e}")
        return None


def run_validation(language_code: str, limit: int = 0, fix: bool = False,
                   dry_run: bool = False):
    db = get_supabase_admin()
    language_id = Config.LANGUAGE_CODE_TO_ID.get(language_code)
    if not language_id:
        raise ValueError(f"Unknown language code: {language_code}")

    target_language = TARGET_LANGUAGES[language_code]

    # Get model for this language
    from services.test_generation.database_client import TestDatabaseClient
    db_client = TestDatabaseClient()
    lang_config = db_client.get_language_config_by_code(language_code)
    model = lang_config.prose_model if lang_config else 'gpt-4o-mini'

    logger.info(f"Validating senses for {language_code} (id={language_id})")
    logger.info(f"  Target language: {target_language}")
    logger.info(f"  Definitions should be in: {target_language}")
    logger.info(f"  Example sentences should be in: {target_language}")
    logger.info(f"  Model: {model}")
    logger.info(f"  Fix: {fix}, Dry run: {dry_run}")

    # Fetch all senses for this language
    query = db.table('dim_word_senses') \
        .select('id, vocab_id, definition, example_sentence, sense_rank, '
                'dim_vocabulary(lemma, language_id)') \
        .order('id')

    if limit:
        query = query.limit(limit)

    response = query.execute()
    all_senses = response.data or []

    # Filter to senses whose vocab belongs to this language
    senses = [
        s for s in all_senses
        if s.get('dim_vocabulary', {}).get('language_id') == language_id
    ]

    logger.info(f"Found {len(senses)} senses for language {language_code}")

    if not senses:
        logger.info("Nothing to validate!")
        return

    client = get_openai_client() if fix else None

    stats = {
        'total': len(senses),
        'definition_ok': 0,
        'definition_bad': 0,
        'definition_empty': 0,
        'definition_fixed': 0,
        'example_ok': 0,
        'example_bad': 0,
        'example_empty': 0,
        'example_fixed': 0,
        'errors': 0,
    }

    bad_definitions = []
    bad_examples = []

    for i, sense in enumerate(senses):
        sense_id = sense['id']
        lemma = sense.get('dim_vocabulary', {}).get('lemma', '?')
        definition = sense.get('definition', '') or ''
        example = sense.get('example_sentence', '') or ''

        # Check definition language — should be in the target language
        def_is_bad = False
        if not definition.strip():
            stats['definition_empty'] += 1
            def_is_bad = True
        else:
            is_correct, reason = check_text_language(definition, language_code)
            if not is_correct:
                def_is_bad = True

        # Check example sentence language — should also be in the target language
        example_is_bad = False
        if not example.strip():
            stats['example_empty'] += 1
            example_is_bad = True
        else:
            is_correct, reason = check_text_language(example, language_code)
            if not is_correct:
                example_is_bad = True

        if def_is_bad and definition.strip():
            stats['definition_bad'] += 1
            bad_definitions.append((sense_id, lemma, definition[:80]))
            logger.warning(
                f"  [{i+1}/{len(senses)}] BAD DEFINITION (not in {target_language}): "
                f"sense={sense_id}, lemma=\"{lemma}\", def=\"{definition[:60]}...\""
            )
        else:
            stats['definition_ok'] += 1

        if example_is_bad and example.strip():
            stats['example_bad'] += 1
            bad_examples.append((sense_id, lemma, example[:80]))
            logger.warning(
                f"  [{i+1}/{len(senses)}] BAD EXAMPLE (not in {target_language}): "
                f"sense={sense_id}, lemma=\"{lemma}\", example=\"{example[:60]}...\""
            )
        else:
            stats['example_ok'] += 1

    logger.info("=" * 60)
    logger.info("Validation Report")
    logger.info(f"  Total senses:       {stats['total']}")
    logger.info(f"  Definitions OK:     {stats['definition_ok']}")
    logger.info(f"  Definitions bad:    {stats['definition_bad']} (not in {target_language})")
    logger.info(f"  Definitions empty:  {stats['definition_empty']}")
    logger.info(f"  Examples OK:        {stats['example_ok']}")
    logger.info(f"  Examples bad:       {stats['example_bad']} (not in {target_language})")
    logger.info(f"  Examples empty:     {stats['example_empty']}")
    logger.info("=" * 60)

    if not fix:
        if bad_definitions or bad_examples:
            logger.info("Run with --fix to regenerate bad entries via LLM")
        return

    # Fix bad entries
    logger.info(f"Fixing {len(bad_definitions)} definitions and {len(bad_examples)} examples...")

    if not client:
        client = get_openai_client()

    for sense_id, lemma, _ in bad_definitions:
        # Get the current example sentence for context
        sense_row = next((s for s in senses if s['id'] == sense_id), None)
        example = (sense_row.get('example_sentence', '') or '') if sense_row else ''

        new_def = regenerate_definition(client, lemma, target_language, example, model)
        if new_def:
            # Verify the regenerated definition is in the right language
            is_correct, reason = check_text_language(new_def, language_code)
            if not is_correct:
                logger.warning(
                    f"  Regenerated definition for '{lemma}' still not in "
                    f"{target_language}: \"{new_def[:60]}...\" ({reason})"
                )
                stats['errors'] += 1
                continue

            if dry_run:
                logger.info(f"  [DRY RUN] Would fix definition for '{lemma}': \"{new_def[:60]}...\"")
            else:
                try:
                    db.table('dim_word_senses') \
                        .update({'definition': new_def}) \
                        .eq('id', sense_id) \
                        .execute()
                    stats['definition_fixed'] += 1
                    logger.info(f"  Fixed definition for '{lemma}' (sense={sense_id})")
                except Exception as e:
                    logger.error(f"  Failed to update definition for '{lemma}': {e}")
                    stats['errors'] += 1
        else:
            stats['errors'] += 1

    for sense_id, lemma, _ in bad_examples:
        new_example = regenerate_example_sentence(client, lemma, target_language, model)
        if new_example:
            # Verify the regenerated example is in the right language
            is_correct, reason = check_text_language(new_example, language_code)
            if not is_correct:
                logger.warning(
                    f"  Regenerated example for '{lemma}' still not in "
                    f"{target_language}: \"{new_example[:60]}...\" ({reason})"
                )
                stats['errors'] += 1
                continue

            if dry_run:
                logger.info(f"  [DRY RUN] Would fix example for '{lemma}': \"{new_example[:60]}...\"")
            else:
                try:
                    db.table('dim_word_senses') \
                        .update({'example_sentence': new_example}) \
                        .eq('id', sense_id) \
                        .execute()
                    stats['example_fixed'] += 1
                    logger.info(f"  Fixed example for '{lemma}' (sense={sense_id})")
                except Exception as e:
                    logger.error(f"  Failed to update example for '{lemma}': {e}")
                    stats['errors'] += 1
        else:
            stats['errors'] += 1

    logger.info("=" * 60)
    logger.info("Fix Complete")
    logger.info(f"  Definitions fixed:  {stats['definition_fixed']}")
    logger.info(f"  Examples fixed:     {stats['example_fixed']}")
    logger.info(f"  Errors:             {stats['errors']}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Validate and fix word sense definitions/examples language'
    )
    parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],
                        help='Language code to validate')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max number of senses to process (0=all)')
    parser.add_argument('--fix', action='store_true',
                        help='Regenerate bad entries via LLM')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be fixed without writing to DB')

    args = parser.parse_args()

    SupabaseFactory.initialize()
    run_validation(
        language_code=args.language,
        limit=args.limit,
        fix=args.fix,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    main()
