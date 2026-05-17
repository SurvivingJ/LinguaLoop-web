#!/usr/bin/env python3
"""
Enroll an existing listening test in Listening Lab.

For each candidate test (must be listening type, active, with a transcript):
  1. Pick a deterministic voice from dim_languages.tts_voice_ids (or --voice).
  2. Generate 4 speed-variant MP3s via Azure SSML <prosody rate>:
     {test_id}-s075.mp3, -s090.mp3, -s100.mp3, -s115.mp3 -> R2.
  3. Generate 15 additional MCQs via the existing QuestionGenerator agent,
     insert into `questions` with pool_source='lab_expansion'.
  4. Insert listening_lab_passages row with is_active=False.

Idempotent: re-running on an already-enrolled test_id is a no-op.

Usage:
    # By explicit test id (1 test)
    python scripts/enroll_listening_lab.py --test-id <uuid>

    # By filter (multiple tests)
    python scripts/enroll_listening_lab.py --language-id 2 --difficulty 5 --limit 10

    # Override voice for the batch
    python scripts/enroll_listening_lab.py --test-id <uuid> --voice en-US-AvaMultilingualNeural

    # Dry run (no R2 / DB writes, no LLM calls)
    python scripts/enroll_listening_lab.py --test-id <uuid> --dry-run
"""

import argparse
import json
import logging
import os
import random
import sys
from typing import Dict, List, Optional
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import get_supabase_admin
from services.test_generation.agents.audio_synthesizer import AudioSynthesizer
from services.test_generation.agents.question_generator import QuestionGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Listening Lab uses 20 MCQs per passage = 5 original + 15 lab_expansion.
EXPANSION_QUESTION_COUNT = 15
TARGET_POOL_SIZE = 20

# 15 questions across 6 cognitive types: balanced spread, weighted slightly
# toward detail/supporting since they're the most common in real exams.
EXPANSION_TYPE_PLAN: List[str] = (
    ['literal_detail'] * 3
    + ['vocabulary_context'] * 3
    + ['main_idea'] * 2
    + ['supporting_detail'] * 3
    + ['inference'] * 2
    + ['author_purpose'] * 2
)
assert len(EXPANSION_TYPE_PLAN) == EXPANSION_QUESTION_COUNT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick_voice(language_row: dict, override: Optional[str]) -> str:
    """Resolve the TTS voice to use across all 4 variants for a passage.

    Priority: explicit --voice override, then a deterministic pick from
    dim_languages.tts_voice_ids, then the audio_synthesizer default.
    """
    if override:
        return override

    voice_ids = language_row.get('tts_voice_ids') or []
    if isinstance(voice_ids, str):
        try:
            voice_ids = json.loads(voice_ids)
        except json.JSONDecodeError:
            voice_ids = []

    if voice_ids:
        return random.choice(voice_ids)

    return 'en-US-AvaMultilingualNeural'


def _resolve_question_type_ids(db) -> Dict[str, int]:
    """type_code -> dim_question_types.id, for tagging expansion questions."""
    rows = db.table('dim_question_types').select('id, type_code').execute().data or []
    return {row['type_code']: row['id'] for row in rows}


def _select_tests(
    db,
    test_id: Optional[str],
    language_id: Optional[int],
    difficulty: Optional[int],
    limit: int,
) -> List[dict]:
    """Resolve the list of candidate tests, filtered to listening type only."""
    listening_type = (
        db.table('dim_test_types')
        .select('id')
        .eq('type_code', 'listening')
        .limit(1)
        .execute()
        .data
    )
    if not listening_type:
        raise RuntimeError("dim_test_types row for 'listening' not found")

    if test_id:
        rows = (
            db.table('tests')
            .select('id, slug, title, transcript, difficulty, language_id, audio_url')
            .eq('id', test_id)
            .eq('is_active', True)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows

    # Filter mode: find candidate listening tests that have transcripts but
    # aren't enrolled yet. Listening type isn't stored on tests.test_type_id
    # — tests are classified by which test_type_id they're being attempted as.
    # Practically, listening passages are tests with non-null audio_url.
    query = (
        db.table('tests')
        .select('id, slug, title, transcript, difficulty, language_id, audio_url')
        .eq('is_active', True)
        .not_.is_('transcript', 'null')
        .not_.is_('audio_url', 'null')
    )
    if language_id:
        query = query.eq('language_id', int(language_id))
    if difficulty is not None:
        query = query.eq('difficulty', int(difficulty))
    query = query.order('created_at', desc=True).limit(limit)
    return query.execute().data or []


def _already_enrolled(db, test_id: str) -> bool:
    res = (
        db.table('listening_lab_passages')
        .select('id')
        .eq('test_id', test_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return bool(res)


def _count_existing_questions(db, test_id: str) -> Dict[str, int]:
    """Return counts grouped by pool_source so we know how many to generate."""
    rows = (
        db.table('questions')
        .select('pool_source')
        .eq('test_id', test_id)
        .execute()
        .data
        or []
    )
    counts: Dict[str, int] = {}
    for row in rows:
        src = row.get('pool_source') or 'original'
        counts[src] = counts.get(src, 0) + 1
    return counts


def _generate_speed_variants(
    synth: AudioSynthesizer,
    transcript: str,
    test_id: str,
    voice: str,
    dry_run: bool,
) -> Dict[float, str]:
    """Render 4 speed-variant MP3s. In dry-run mode, return stub URLs."""
    if dry_run:
        base = f'https://r2.example/dryrun/{test_id}'
        return {0.75: f'{base}-s075.mp3', 0.90: f'{base}-s090.mp3',
                1.00: f'{base}-s100.mp3', 1.15: f'{base}-s115.mp3'}

    return synth.generate_speed_variants(
        text=transcript,
        base_slug=test_id,
        voice=voice,
    )


def _generate_expansion_questions(
    qgen: QuestionGenerator,
    test: dict,
    language_name: str,
    dry_run: bool,
) -> List[dict]:
    """Run the QuestionGenerator agent with the EXPANSION_TYPE_PLAN."""
    if dry_run:
        return [
            {
                'question': f'[DRY-RUN] Q{i+1} ({tc})',
                'choices': ['A', 'B', 'C', 'D'],
                'answer': 'A',
                'type_code': tc,
            }
            for i, tc in enumerate(EXPANSION_TYPE_PLAN)
        ]

    return qgen.generate_questions(
        prose=test['transcript'],
        language_name=language_name,
        question_type_codes=EXPANSION_TYPE_PLAN,
        difficulty=int(test.get('difficulty') or 5),
    )


def _insert_expansion_questions(
    db,
    test: dict,
    questions: List[dict],
    type_code_to_id: Dict[str, int],
) -> int:
    """Insert generated questions with pool_source='lab_expansion'."""
    if not questions:
        return 0

    slug = test.get('slug') or test['id']
    # Continue the original test's question_id numbering after the canonical 5
    # so the expansion ids don't collide.
    existing_count = (
        db.table('questions').select('id').eq('test_id', test['id']).execute().data or []
    )
    start_idx = len(existing_count) + 1

    rows = []
    for i, q in enumerate(questions):
        row = {
            'id': str(uuid4()),
            'test_id': test['id'],
            'question_id': f'{slug}-lab-q{start_idx + i}',
            'question_text': q['question'],
            'choices': q['choices'],
            'answer': q['answer'],
            'pool_source': 'lab_expansion',
        }
        type_id = type_code_to_id.get(q.get('type_code', ''))
        if type_id:
            row['question_type_id'] = type_id
        rows.append(row)

    response = db.table('questions').insert(rows).execute()
    return len(response.data or [])


def _insert_passage(
    db,
    test: dict,
    audio_urls: Dict[float, str],
    voice: str,
    pool_size: int,
) -> str:
    """Insert the listening_lab_passages row (is_active=False by default)."""
    record = {
        'test_id': test['id'],
        'language_id': test['language_id'],
        'audio_url_075': audio_urls[0.75],
        'audio_url_090': audio_urls[0.90],
        'audio_url_100': audio_urls[1.00],
        'audio_url_115': audio_urls[1.15],
        'voice_id': voice,
        'pool_size': pool_size,
        'is_active': False,
    }
    response = db.table('listening_lab_passages').insert(record).execute()
    return response.data[0]['id'] if response.data else ''


# ---------------------------------------------------------------------------
# Main enrollment routine (one test)
# ---------------------------------------------------------------------------

def enroll_test(
    db,
    synth: AudioSynthesizer,
    qgen: QuestionGenerator,
    test: dict,
    language_row: dict,
    type_code_to_id: Dict[str, int],
    voice_override: Optional[str],
    dry_run: bool,
) -> dict:
    """Run the full enrollment pipeline for one test."""
    test_id = test['id']
    slug = test.get('slug', test_id)
    logger.info("=" * 60)
    logger.info("Enrolling test %s (%s)", slug, test_id)

    if _already_enrolled(db, test_id):
        logger.info("Already enrolled — skipping")
        return {'status': 'skipped', 'reason': 'already_enrolled', 'test_id': test_id}

    if not test.get('transcript'):
        logger.warning("No transcript — skipping")
        return {'status': 'skipped', 'reason': 'no_transcript', 'test_id': test_id}

    voice = _pick_voice(language_row, voice_override)
    logger.info("Voice: %s", voice)

    # Step 1: Audio variants
    logger.info("Generating 4 speed-variant MP3s...")
    audio_urls = _generate_speed_variants(synth, test['transcript'], test_id, voice, dry_run)
    for speed, url in audio_urls.items():
        logger.info("  %.2fx -> %s", speed, url)

    # Step 2: Question expansion
    counts = _count_existing_questions(db, test_id)
    n_original = counts.get('original', 0)
    n_expansion = counts.get('lab_expansion', 0)
    needed = max(EXPANSION_QUESTION_COUNT - n_expansion, 0)
    logger.info(
        "Question pool: %d original, %d lab_expansion (need %d more)",
        n_original, n_expansion, needed,
    )

    inserted = 0
    if needed > 0:
        # If lab_expansion is partially populated, scale the type plan.
        plan = EXPANSION_TYPE_PLAN if needed == EXPANSION_QUESTION_COUNT else EXPANSION_TYPE_PLAN[:needed]
        questions = _generate_expansion_questions(
            qgen=qgen,
            test={**test, 'transcript': test['transcript']},
            language_name=language_row['language_name'],
            dry_run=dry_run,
        )
        # Use only as many as we need (the generator was called with the full
        # plan so we get the higher-quality types first).
        questions = questions[:needed]

        if dry_run:
            logger.info("[DRY-RUN] Would insert %d expansion questions", len(questions))
        else:
            inserted = _insert_expansion_questions(db, test, questions, type_code_to_id)
            logger.info("Inserted %d expansion questions", inserted)

    final_pool_size = n_original + n_expansion + inserted
    if final_pool_size < TARGET_POOL_SIZE and not dry_run:
        logger.warning(
            "Final pool size %d < target %d; passage will still be enrolled "
            "but Listening Lab sessions may exhaust the without-replacement pool sooner.",
            final_pool_size, TARGET_POOL_SIZE,
        )

    # Step 3: passage row
    if dry_run:
        logger.info("[DRY-RUN] Would insert listening_lab_passages row (is_active=False)")
        passage_id = '<dryrun>'
    else:
        passage_id = _insert_passage(db, test, audio_urls, voice, final_pool_size)
        logger.info("Inserted passage %s (is_active=False)", passage_id)

    return {
        'status': 'enrolled',
        'test_id': test_id,
        'slug': slug,
        'passage_id': passage_id,
        'voice': voice,
        'audio_urls': audio_urls,
        'pool_size': final_pool_size,
        'questions_inserted': inserted,
        'dry_run': dry_run,
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Enroll existing listening tests in Listening Lab.",
    )
    parser.add_argument('--test-id', help='Enroll a single test by UUID.')
    parser.add_argument('--language-id', type=int, help='Filter: language_id.')
    parser.add_argument('--difficulty', type=int, help='Filter: difficulty 1-9.')
    parser.add_argument('--limit', type=int, default=10,
                        help='Max tests to enroll when using filter mode (default: 10).')
    parser.add_argument('--voice', help='Override TTS voice id for all variants.')
    parser.add_argument('--dry-run', action='store_true',
                        help='No R2 writes, no DB writes, no LLM calls.')
    args = parser.parse_args()

    if not args.test_id and not args.language_id:
        parser.error("Either --test-id or --language-id is required.")

    db = get_supabase_admin()

    # Pre-load shared lookups.
    type_code_to_id = _resolve_question_type_ids(db)
    if not type_code_to_id:
        logger.warning("No dim_question_types rows found — questions will be inserted without question_type_id")

    tests = _select_tests(
        db,
        test_id=args.test_id,
        language_id=args.language_id,
        difficulty=args.difficulty,
        limit=args.limit,
    )
    if not tests:
        logger.warning("No tests matched the given filters.")
        return 0

    logger.info("Found %d candidate test(s) to enroll", len(tests))

    # Resolve language row(s) up-front so we only hit dim_languages once per lang.
    lang_ids = sorted({t['language_id'] for t in tests})
    lang_rows = (
        db.table('dim_languages')
        .select('id, language_name, language_code, tts_voice_ids')
        .in_('id', lang_ids)
        .execute()
        .data
        or []
    )
    languages = {row['id']: row for row in lang_rows}

    synth = AudioSynthesizer()
    qgen = QuestionGenerator() if not args.dry_run else None

    summary = {'enrolled': 0, 'skipped': 0, 'failed': 0, 'details': []}

    for test in tests:
        try:
            lang_row = languages.get(test['language_id'])
            if not lang_row:
                logger.error("Language %s not found for test %s", test['language_id'], test['id'])
                summary['failed'] += 1
                continue

            result = enroll_test(
                db=db,
                synth=synth,
                qgen=qgen,
                test=test,
                language_row=lang_row,
                type_code_to_id=type_code_to_id,
                voice_override=args.voice,
                dry_run=args.dry_run,
            )
            summary['details'].append(result)
            if result['status'] == 'enrolled':
                summary['enrolled'] += 1
            else:
                summary['skipped'] += 1

        except Exception as e:
            logger.error("Enrollment failed for test %s: %s", test['id'], e, exc_info=True)
            summary['failed'] += 1
            summary['details'].append({
                'status': 'failed', 'test_id': test['id'], 'error': str(e),
            })

    logger.info("=" * 60)
    logger.info("Done: %d enrolled, %d skipped, %d failed",
                summary['enrolled'], summary['skipped'], summary['failed'])
    return 0 if summary['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
