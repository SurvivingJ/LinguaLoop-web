#!/usr/bin/env python3
"""
Backfill ``dim_word_senses.embedding`` (TASK-521).

Usage::

    python -m scripts.backfill_sense_embeddings --all-languages --dry-run
    python -m scripts.backfill_sense_embeddings --language 2
    python -m scripts.backfill_sense_embeddings --all-languages --batch 256

What gets embedded, and why it matters
--------------------------------------
The embedded text is ``"{lemma}: {definition}"``, not the definition alone.
Definitions in this corpus are frequently short and generic ("a kind of tool",
"一种化学物质"), and several unrelated senses collapse onto nearly the same
vector when embedded bare. Prefixing the lemma keeps distinct senses distinct,
which is exactly the property the mid-band neighbour query depends on.

Idempotent: senses that already carry an embedding are skipped, so an
interrupted run resumes and a re-run after adding senses pays only for the new
ones. ``--force`` re-embeds everything, which is right only after a model
change.

Cost is reported. text-embedding-3-small is cheap — about $0.02 per million
tokens, so a full 22k-sense backfill is a few cents — but the number is printed
rather than assumed.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('backfill_embeddings')

_PAGE = 1000
_USD_PER_MILLION_TOKENS = 0.02          # text-embedding-3-small


def build_text(lemma: str | None, definition: str | None) -> str:
    """The string that gets embedded.

    Defined once so the batch backfill and the embed-on-create hook can never
    disagree — a corpus half-embedded one way and half the other would produce
    silently wrong neighbours with nothing to indicate it.
    """
    lemma = (lemma or '').strip()
    definition = (definition or '').strip()
    if lemma and definition:
        return f'{lemma}: {definition}'
    return lemma or definition


def fetch_pending(db, language_id: int | None, force: bool) -> list[dict]:
    """Senses needing an embedding, paired with their lemma."""
    out: list[dict] = []
    offset = 0
    while True:
        query = (
            db.table('dim_word_senses')
            .select('id, definition, dim_vocabulary!inner(lemma, language_id)')
            .range(offset, offset + _PAGE - 1)
        )
        if language_id is not None:
            query = query.eq('dim_vocabulary.language_id', language_id)
        if not force:
            query = query.is_('embedding', 'null')
        rows = query.execute().data or []
        for row in rows:
            vocab = row.get('dim_vocabulary') or {}
            text = build_text(vocab.get('lemma'), row.get('definition'))
            if text:
                out.append({'id': row['id'], 'text': text})
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    return out


def embed_and_store(db, embedder, rows: list[dict], batch_size: int) -> dict:
    """Embed in batches and write each vector back."""
    stats = {'embedded': 0, 'failed': 0, 'api_calls': 0, 'tokens_est': 0}
    for start in range(0, len(rows), batch_size):
        window = rows[start:start + batch_size]
        try:
            vectors = embedder.embed_batch([r['text'] for r in window])
        except Exception as exc:
            logger.error('embedding call failed for %d rows: %s', len(window), exc)
            stats['failed'] += len(window)
            continue

        stats['api_calls'] += 1
        # Rough token estimate for the cost line: this wrapper does not surface
        # API usage, and a 4-chars-per-token heuristic is close enough to catch
        # an order-of-magnitude surprise.
        stats['tokens_est'] += sum(len(r['text']) for r in window) // 4

        for row, vector in zip(window, vectors):
            if not vector:
                stats['failed'] += 1
                continue
            try:
                db.table('dim_word_senses').update(
                    {'embedding': vector}).eq('id', row['id']).execute()
                stats['embedded'] += 1
            except Exception as exc:
                logger.error('failed to store embedding for sense %s: %s',
                             row['id'], exc)
                stats['failed'] += 1

        logger.info('  %d/%d embedded', stats['embedded'], len(rows))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description='Backfill sense embeddings')
    parser.add_argument('--language', type=int, choices=[1, 2, 3])
    parser.add_argument('--all-languages', action='store_true')
    parser.add_argument('--batch', type=int, default=256,
                        help='texts per embedding API call (default 256)')
    parser.add_argument('--limit', type=int, default=None,
                        help='stop after this many senses')
    parser.add_argument('--force', action='store_true',
                        help='re-embed senses that already have a vector')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if not args.language and not args.all_languages:
        parser.error('pass --language or --all-languages')

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        stream=sys.stdout)
    for noisy in ('httpx', 'httpcore', 'openai', 'urllib3'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    languages = [1, 2, 3] if args.all_languages else [args.language]
    total = {'embedded': 0, 'failed': 0, 'api_calls': 0, 'tokens_est': 0}

    for language_id in languages:
        rows = fetch_pending(db, language_id, args.force)
        if args.limit:
            rows = rows[:args.limit]
        logger.info('language %s: %d senses to embed', language_id, len(rows))
        if not rows:
            continue
        if args.dry_run:
            for row in rows[:5]:
                logger.info('  [dry-run] sense %s -> %r', row['id'], row['text'][:80])
            continue

        from services.topic_generation.agents.embedder import EmbeddingService
        stats = embed_and_store(db, EmbeddingService(), rows, args.batch)
        logger.info('language %s: %s', language_id, stats)
        for key in total:
            total[key] += stats[key]

    if not args.dry_run:
        logger.info('total: %s (~$%.4f)', total,
                    total['tokens_est'] / 1_000_000 * _USD_PER_MILLION_TOKENS)


if __name__ == '__main__':
    main()
