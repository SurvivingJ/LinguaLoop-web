#!/usr/bin/env python3
"""
Cross-language gloss backfill.

For every existing dim_word_senses definition in --source-language, writes an
additional dim_word_senses row per --gloss-language: same vocab_id/sense_rank/
definition_level, but definition_language_id set to the gloss language and
definition = an LLM translation of the source definition (services/vocabulary/
gloss_generator.py). source='llm_gloss' on every row written here.

This is additive only -- it never updates or deletes an existing sense_id, so
nothing that already references a sense (word_assets, exercises,
user_word_ladder, ...) is touched.

Resumable: (vocab_id, sense_rank, definition_level) pairs that already have a
gloss row for a given target language are skipped without an LLM call.

Usage:
    python scripts/backfill_gloss_definitions.py --source-language ja --gloss-languages en,zh --dry-run
    python scripts/backfill_gloss_definitions.py --source-language ja --gloss-languages en,zh --limit 50
    python scripts/backfill_gloss_definitions.py --source-language ja --gloss-languages en,zh --concurrency 8

Options:
    --source-language CODE   Required. Word's own language: zh | en | ja
    --gloss-languages LIST   Comma-separated target languages (default: en,zh)
    --levels LIST            Comma-separated definition_level values to cover
                              (default: simple,standard)
    --model NAME             OpenRouter model slug (default: openrouter/auto-beta)
    --limit N                Cap source rows processed, before language fan-out (0 = all)
    --concurrency N          In-flight LLM calls (default: 5)
    --dry-run                Translate + log, write nothing
"""

import os
import sys
import argparse
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.vocabulary.gloss_generator import translate_definition
from services.vocabulary.sense_generator import retry_transient_db_call

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PAGE = 1000
DEFAULT_MODEL = 'openrouter/auto-beta'


def _load_source_senses(db, source_language_id: int, levels: list[str]) -> list[dict]:
    """Native definitions for the source language, at the requested levels.

    Filters on dim_word_senses.definition_language_id (the row's OWN
    language) -- not derived from the vocab join -- so a future gloss row
    can never accidentally be picked up as a "source" definition to
    translate again. dim_vocabulary.language_id is checked too, as a cheap
    belt-and-suspenders assertion against the current one-native-row-per-word
    invariant.
    """
    rows: list[dict] = []
    offset = 0
    while True:
        page = (
            db.table('dim_word_senses')
            .select(
                'id, vocab_id, definition, example_sentence, sense_rank, '
                'definition_level, dim_vocabulary(lemma, language_id)'
            )
            .eq('definition_language_id', source_language_id)
            .in_('definition_level', levels)
            .range(offset, offset + PAGE - 1)
            .execute()
        ).data or []
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE

    out = []
    for r in rows:
        vocab = r.get('dim_vocabulary') or {}
        if vocab.get('language_id') != source_language_id:
            continue  # paranoia: shouldn't happen given the query above
        out.append({
            'sense_id': r['id'],
            'vocab_id': r['vocab_id'],
            'lemma': vocab.get('lemma', ''),
            'definition': r.get('definition', '') or '',
            'example_sentence': r.get('example_sentence') or '',
            'sense_rank': r['sense_rank'],
            'definition_level': r['definition_level'],
        })
    return out


def _load_existing_glosses(db, gloss_language_id: int) -> set[tuple[int, int, str]]:
    """(vocab_id, sense_rank, definition_level) already glossed in this language."""
    existing: set[tuple[int, int, str]] = set()
    offset = 0
    while True:
        page = (
            db.table('dim_word_senses')
            .select('vocab_id, sense_rank, definition_level')
            .eq('definition_language_id', gloss_language_id)
            .eq('source', 'llm_gloss')
            .range(offset, offset + PAGE - 1)
            .execute()
        ).data or []
        existing.update(
            (r['vocab_id'], r['sense_rank'], r['definition_level']) for r in page
        )
        if len(page) < PAGE:
            break
        offset += PAGE
    return existing


def run(source_language: str, gloss_languages: list[str], levels: list[str],
        model: str, limit: int, concurrency: int, dry_run: bool):
    source_id = Config.LANGUAGE_CODE_TO_ID.get(source_language)
    if not source_id:
        raise ValueError(f"Unknown source language: {source_language!r}")

    gloss_ids = {}
    for code in gloss_languages:
        lid = Config.LANGUAGE_CODE_TO_ID.get(code)
        if not lid:
            raise ValueError(f"Unknown gloss language: {code!r}")
        if lid == source_id:
            raise ValueError(f"Gloss language {code!r} is the same as source language")
        gloss_ids[code] = lid

    db = get_supabase_admin()

    source_rows = _load_source_senses(db, source_id, levels)
    if limit:
        source_rows = source_rows[:limit]
    logger.info(
        f"{source_language}: {len(source_rows)} source definitions "
        f"(levels={levels}) -> gloss languages {gloss_languages} | "
        f"model={model} | concurrency={concurrency} | dry_run={dry_run}"
    )
    if not source_rows:
        logger.info("Nothing to do.")
        return

    # (gloss_lang_code, vocab_id, sense_rank, definition_level) already done.
    existing_by_lang = {
        code: _load_existing_glosses(db, lid) for code, lid in gloss_ids.items()
    }

    tasks = []
    for row in source_rows:
        key = (row['vocab_id'], row['sense_rank'], row['definition_level'])
        for code, lid in gloss_ids.items():
            if key not in existing_by_lang[code]:
                tasks.append((row, code, lid))

    already = (len(source_rows) * len(gloss_ids)) - len(tasks)
    logger.info(f"{len(tasks)} gloss rows to generate ({already} already exist)")
    if not tasks:
        logger.info("Nothing to do.")
        return

    stats = {'written': 0, 'translate_failed': 0, 'write_failed': 0}
    lock = threading.Lock()

    def bump(key):
        with lock:
            stats[key] += 1

    @retry_transient_db_call
    def _write(write_row):
        db.table('dim_word_senses') \
            .upsert(write_row, on_conflict='vocab_id,definition_language_id,definition_level,sense_rank') \
            .execute()

    def work(task):
        row, gloss_code, gloss_id = task
        translated = translate_definition(
            lemma=row['lemma'],
            source_lang_code=source_language,
            target_lang_code=gloss_code,
            definition=row['definition'],
            example_sentence=row['example_sentence'],
            model=model,
        )
        if not translated:
            bump('translate_failed')
            return

        if dry_run:
            logger.info(
                f"  [DRY RUN] {row['lemma']} ({row['definition_level']}, "
                f"{source_language}->{gloss_code}): {translated[:80]}"
            )
            bump('written')
            return

        write_row = {
            'vocab_id': row['vocab_id'],
            'definition_language_id': gloss_id,
            'definition_level': row['definition_level'],
            'definition': translated,
            'sense_rank': row['sense_rank'],
            'source': 'llm_gloss',
            'source_ref': f'{model} v1',
        }
        try:
            _write(write_row)
            bump('written')
        except Exception as e:
            logger.error(f"  Write failed for {row['lemma']} ({gloss_code}): {e}")
            bump('write_failed')

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futures = [ex.submit(work, t) for t in tasks]
        for fut in as_completed(futures):
            fut.result()
            done += 1
            if done % 200 == 0:
                logger.info(f"  ...{done}/{len(tasks)} processed")

    logger.info(
        f"Done. processed={done} written={stats['written']} "
        f"translate_failed={stats['translate_failed']} "
        f"write_failed={stats['write_failed']}"
    )
    if dry_run:
        logger.info("Dry-run: no rows were written.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Backfill cross-language gloss definitions")
    parser.add_argument('--source-language', required=True, help='Word\'s own language: zh, en, ja')
    parser.add_argument('--gloss-languages', default='en,zh', help='Comma-separated target languages')
    parser.add_argument('--levels', default='simple,standard', help='Comma-separated definition_level values')
    parser.add_argument('--model', default=DEFAULT_MODEL, help='OpenRouter model slug')
    parser.add_argument('--limit', type=int, default=0, help='Cap source rows (0 = all)')
    parser.add_argument('--concurrency', type=int, default=5, help='In-flight LLM calls')
    parser.add_argument('--dry-run', action='store_true', help='Translate + log, write nothing')
    args = parser.parse_args()

    run(
        source_language=args.source_language,
        gloss_languages=[c.strip() for c in args.gloss_languages.split(',') if c.strip()],
        levels=[c.strip() for c in args.levels.split(',') if c.strip()],
        model=args.model,
        limit=args.limit,
        concurrency=args.concurrency,
        dry_run=args.dry_run,
    )
