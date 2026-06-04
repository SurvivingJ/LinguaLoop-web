#!/usr/bin/env python3
"""
Two-level sense dictionary backfill.

Seeds dim_word_senses with both definition levels (simple + standard) for every
lemma in dim_vocabulary, one cheap hosted-LLM call per word
(services/vocabulary/sense_generator.py :: SenseGenerator.seed_word). The
standard row of words already seeded by the old single-level pipeline is
refreshed and a `simple` row is added alongside it at the same sense_rank.

Resumable: words that already have a `simple` row are skipped (no LLM call), so
a killed run can be restarted and re-running to completion creates 0 new rows.
source='manual' senses are never overwritten.

Concurrent: hosted APIs parallelise well; each worker thread owns its own
SenseGenerator (the cache/stats are per-instance), and stats are aggregated at
the end.

Usage:
    python scripts/backfill_senses.py --language zh
    python scripts/backfill_senses.py --language ja --limit 100 --dry-run
    python scripts/backfill_senses.py --language en --model deepseek/deepseek-v4-flash --concurrency 8

Options:
    --language CODE    Required. zh | en | ja
    --model NAME       Sense model override (default: SENSE_MODEL_DEFAULT, DeepSeek V4 Flash)
    --limit N          Process at most N lemmas (0 = all)
    --concurrency N    In-flight LLM calls (default: 5)
    --delay SECS       Per-word delay inside each worker (default: 0.0)
    --dry-run          Generate + log, write nothing
"""

import os
import sys
import time
import argparse
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.llm_service import SENSE_MODEL_DEFAULT
from services.vocabulary.sense_generator import SenseGenerator

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PAGE = 1000


def _load_worklist(db, language_id: int):
    """Return [(vocab_id, lemma), ...] for lemmas lacking a `simple` sense row.

    Loads all vocab for the language and the set of vocab_ids that already have
    a simple-level sense, then subtracts — cheap at a few thousand rows and gives
    a deterministic, resumable worklist without a NOT EXISTS round-trip per word.
    """
    seeded: set[int] = set()
    offset = 0
    while True:
        rows = (db.table('dim_word_senses')
                .select('vocab_id')
                .eq('definition_language_id', language_id)
                .eq('definition_level', 'simple')
                .range(offset, offset + PAGE - 1)
                .execute()).data or []
        seeded.update(r['vocab_id'] for r in rows)
        if len(rows) < PAGE:
            break
        offset += PAGE

    worklist = []
    offset = 0
    while True:
        rows = (db.table('dim_vocabulary')
                .select('id, lemma')
                .eq('language_id', language_id)
                .range(offset, offset + PAGE - 1)
                .execute()).data or []
        for r in rows:
            if r['id'] not in seeded:
                worklist.append((r['id'], r['lemma']))
        if len(rows) < PAGE:
            break
        offset += PAGE

    return worklist, len(seeded)


class _GeneratorPool:
    """One SenseGenerator per worker thread (cache/stats are per-instance)."""

    def __init__(self, db, db_client, language_code, language_id, model, dry_run):
        self._args = (db, db_client, language_code, language_id, model, dry_run)
        self._local = threading.local()
        self._all: list[SenseGenerator] = []
        self._lock = threading.Lock()

    def get(self) -> SenseGenerator:
        gen = getattr(self._local, 'gen', None)
        if gen is None:
            db, db_client, code, lid, model, dry_run = self._args
            gen = SenseGenerator(
                openai_client=None, db=db, db_client=db_client,
                language_code=code, language_id=lid, model=model,
                prefer_existing=True, dry_run=dry_run,
            )
            self._local.gen = gen
            with self._lock:
                self._all.append(gen)
        return gen

    def aggregate_stats(self) -> dict:
        totals: dict[str, int] = {}
        for gen in self._all:
            for k, v in gen.stats.items():
                totals[k] = totals.get(k, 0) + v
        return totals


def run(language_code: str, model: str, limit: int, concurrency: int,
        delay: float, dry_run: bool):
    language_id = Config.LANGUAGE_CODE_TO_ID.get(language_code)
    if not language_id:
        raise ValueError(f"Unknown language code: {language_code!r} (use zh, en, ja)")

    from services.test_generation.database_client import TestDatabaseClient
    db = get_supabase_admin()
    db_client = TestDatabaseClient()

    worklist, already = _load_worklist(db, language_id)
    if limit:
        worklist = worklist[:limit]
    logger.info(
        f"{language_code}: {len(worklist)} lemmas to seed "
        f"({already} already have a simple level) | model={model} | "
        f"concurrency={concurrency} | dry_run={dry_run}"
    )
    if not worklist:
        logger.info("Nothing to do.")
        return

    pool = _GeneratorPool(db, db_client, language_code, language_id, model, dry_run)
    done = 0
    failed = 0

    def work(item):
        vocab_id, lemma = item
        if delay:
            time.sleep(delay)
        gen = pool.get()
        try:
            gen.seed_word(vocab_id=vocab_id, lemma=lemma, sentence="")
            return True
        except Exception as e:
            logger.error(f"  {lemma} (vocab {vocab_id}) failed: {e}")
            return False

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futures = [ex.submit(work, item) for item in worklist]
        for fut in as_completed(futures):
            done += 1
            if not fut.result():
                failed += 1
            if done % 100 == 0:
                logger.info(f"  ...{done}/{len(worklist)} processed")

    stats = pool.aggregate_stats()
    logger.info(
        f"Done. processed={done} worker_errors={failed} | "
        f"senses_created={stats.get('senses_created', 0)} "
        f"reused={stats.get('senses_reused', 0)} "
        f"skipped={stats.get('senses_skipped', 0)} "
        f"failed={stats.get('senses_failed', 0)} "
        f"rows_written={stats.get('rows_written', 0)} "
        f"fallback_used={stats.get('fallback_used', 0)}"
    )
    if dry_run:
        logger.info("Dry-run: no rows were written.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Backfill two-level word senses")
    parser.add_argument('--language', required=True, help='Language code: zh, en, ja')
    parser.add_argument('--model', default=SENSE_MODEL_DEFAULT, help='Sense model slug')
    parser.add_argument('--limit', type=int, default=0, help='Cap lemmas (0 = all)')
    parser.add_argument('--concurrency', type=int, default=5, help='In-flight LLM calls')
    parser.add_argument('--delay', type=float, default=0.0, help='Per-word delay (s)')
    parser.add_argument('--dry-run', action='store_true', help='Generate + log, write nothing')
    args = parser.parse_args()
    run(args.language, args.model, args.limit, args.concurrency, args.delay, args.dry_run)
