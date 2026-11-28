#!/usr/bin/env python3
"""Backfill ``tests.passage_embedding`` for tests that have none.

The passage embedding feeds the near-duplicate check of test generation
(``services/test_generation/dedup.py``, ``match_test_passages``). Tests
generated or uploaded without an embedding key are invisible to it.

Dry run unless ``--apply``. Uses ``EmbeddingService`` (text-embedding-3-small,
1536-d), so ``EMBEDDINGS_PROVIDER=openrouter`` routes it through OpenRouter.

    python -m scripts.backfill_passage_embeddings
    EMBEDDINGS_PROVIDER=openrouter python -m scripts.backfill_passage_embeddings --apply
"""

from __future__ import annotations

import argparse
import logging
import sys

try:
    from _common import admin_db, bootstrap
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import admin_db, bootstrap

bootstrap(log_level=None)

logger = logging.getLogger('backfill_passage_embeddings')


def fetch_missing(db, language_id: int | None) -> list[dict]:
    rows, start = [], 0
    while True:
        q = (db.table('tests').select('id, transcript, language_id')
             .is_('passage_embedding', 'null').order('id'))
        if language_id:
            q = q.eq('language_id', language_id)
        page = q.range(start, start + 999).execute().data or []
        rows.extend(r for r in page if (r.get('transcript') or '').strip())
        if len(page) < 1000:
            return rows
        start += 1000


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    from services import language_registry
    p.add_argument('--language', type=int, choices=language_registry.ids())
    p.add_argument('--batch', type=int, default=100)
    p.add_argument('--apply', action='store_true', help='write (default: dry run)')
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='%(asctime)s %(levelname)s %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)

    db = admin_db()
    rows = fetch_missing(db, args.language)
    logger.info('%d tests without a passage embedding', len(rows))
    if not args.apply:
        for r in rows[:5]:
            logger.info('  [dry-run] %s (lang %s): %s', r['id'], r['language_id'], r['transcript'][:60])
        return 0

    from services.topic_generation.agents.embedder import EmbeddingService
    embedder = EmbeddingService()
    done = failed = 0
    for i in range(0, len(rows), args.batch):
        window = rows[i:i + args.batch]
        vectors = embedder.embed_batch([r['transcript'] for r in window])
        for r, v in zip(window, vectors):
            try:
                db.table('tests').update({'passage_embedding': v}).eq('id', r['id']).execute()
                done += 1
            except Exception as exc:  # noqa: BLE001 -- report and continue
                failed += 1
                logger.error('update failed for %s: %s', r['id'], exc)
        logger.info('  %d/%d embedded', done, len(rows))
    logger.info('done: %d embedded, %d failed, %d api calls (model %s)',
                done, failed, embedder.api_call_count, embedder.model)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
