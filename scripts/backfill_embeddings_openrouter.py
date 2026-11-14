#!/usr/bin/env python3
"""
Backfill missing embeddings via OpenRouter (openai/text-embedding-3-small).

Usage::

    python -m scripts.backfill_embeddings_openrouter --dry-run
    python -m scripts.backfill_embeddings_openrouter --only senses tests topics
    python -m scripts.backfill_embeddings_openrouter --limit 50 --only tests

Same model and vector space as the direct-OpenAI path (OpenRouter routes
``openai/text-embedding-3-small``, 1536-d), so the output is interchangeable
with existing vectors. Nothing here uses a different model on purpose: mixing
embedding spaces in one column makes cosine similarity meaningless.

Fills only rows whose vector is NULL:
  * dim_word_senses.embedding   native standard rows, text via build_text(),
                                truncated to 512-d with sense_vector() (ADR-038)
  * tests.passage_embedding     text = transcript, full 1536-d
  * topics.embedding            text = construct_semantic_signature-style string,
                                full 1536-d; also writes topics.semantic_signature

Idempotent and resumable: re-running only touches rows still NULL.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

try:
    from _common import admin_db, bootstrap
except ImportError:
    from scripts._common import admin_db, bootstrap

bootstrap(log_level=None)

from scripts.backfill_sense_embeddings import build_text, sense_vector  # noqa: E402

logger = logging.getLogger('backfill_openrouter')

MODEL = os.getenv('OPENROUTER_EMBEDDING_MODEL', 'openai/text-embedding-3-small')
BASE_URL = 'https://openrouter.ai/api/v1'
_PAGE = 1000
_MAX_CHARS = 8000


def get_embedder():
    from openai import OpenAI
    key = os.getenv('OPENROUTER_API_KEY')
    if not key:
        raise SystemExit('OPENROUTER_API_KEY is not set')
    return OpenAI(base_url=BASE_URL, api_key=key)


def embed_texts(client, texts: list[str], retries: int = 4) -> list[list[float]]:
    cleaned = [t.replace('\n', ' ').strip()[:_MAX_CHARS] for t in texts]
    for attempt in range(retries):
        try:
            resp = client.embeddings.create(model=MODEL, input=cleaned)
            data = sorted(resp.data, key=lambda d: d.index)
            if len(data) != len(texts):
                raise RuntimeError(f'got {len(data)} vectors for {len(texts)} texts')
            return [d.embedding for d in data]
        except Exception as exc:
            if attempt == retries - 1:
                raise
            wait = 2 ** (attempt + 1)
            logger.warning('embed call failed (%s); retrying in %ss', exc, wait)
            time.sleep(wait)
    return []


def pending_senses_native(db) -> list[dict]:
    """Native standard rows only: the CHECK constraint rejects any other row."""
    out, offset = [], 0
    while True:
        rows = (db.table('dim_word_senses')
                .select('id, definition, word_language_id, definition_language_id, '
                        'dim_vocabulary!inner(lemma)')
                .eq('definition_level', 'standard')
                .is_('embedding', 'null')
                .order('id').range(offset, offset + _PAGE - 1).execute().data or [])
        out.extend(r for r in rows
                   if r['definition_language_id'] == r['word_language_id'])
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    result = []
    for r in out:
        text = build_text((r.get('dim_vocabulary') or {}).get('lemma'), r.get('definition'))
        if text:
            result.append({'id': r['id'], 'text': text})
    return result


def pending_tests(db) -> list[dict]:
    out, offset = [], 0
    while True:
        rows = (db.table('tests').select('id, transcript')
                .is_('passage_embedding', 'null')
                .order('id').range(offset, offset + _PAGE - 1).execute().data or [])
        out.extend({'id': r['id'], 'text': r['transcript']}
                   for r in rows if (r.get('transcript') or '').strip())
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    return out


def pending_topics(db) -> list[dict]:
    lenses = {r['id']: r['display_name'] for r in
              db.table('dim_lens').select('id, display_name').execute().data or []}
    cats = {r['id']: r['name'] for r in
            db.table('categories').select('id, name').execute().data or []}
    rows = (db.table('topics')
            .select('id, category_id, concept_english, lens_id, keywords')
            .is_('embedding', 'null').order('id').execute().data or [])
    out = []
    for r in rows:
        kws = ', '.join((r.get('keywords') or [])[:5])
        sig = f"{cats.get(r['category_id'], '')}: {r['concept_english']} [{lenses.get(r['lens_id'], '')}]"
        if kws:
            sig += f' ({kws})'
        out.append({'id': r['id'], 'text': sig, 'signature': sig})
    return out


TARGETS = {
    'senses': ('dim_word_senses', 'embedding', pending_senses_native,
               lambda r, v: {'embedding': sense_vector(v)}),
    'tests': ('tests', 'passage_embedding', pending_tests,
              lambda r, v: {'passage_embedding': v}),
    'topics': ('topics', 'embedding', pending_topics,
               lambda r, v: {'embedding': v, 'semantic_signature': r['signature']}),
}


def run(db, client, name: str, batch: int, limit: int | None, dry: bool) -> dict:
    table, _col, fetch, payload = TARGETS[name]
    rows = fetch(db)
    if limit:
        rows = rows[:limit]
    logger.info('%s: %d rows to embed', name, len(rows))
    stats = {'embedded': 0, 'failed': 0, 'tokens_est': 0}
    if dry or not rows:
        for r in rows[:3]:
            logger.info('  [dry-run] %s -> %r', r['id'], r['text'][:80])
        return stats
    for i in range(0, len(rows), batch):
        window = rows[i:i + batch]
        try:
            vectors = embed_texts(client, [r['text'] for r in window])
        except Exception as exc:
            logger.error('%s: batch at %d failed: %s', name, i, exc)
            stats['failed'] += len(window)
            continue
        stats['tokens_est'] += sum(len(r['text']) for r in window) // 4
        for r, v in zip(window, vectors):
            try:
                db.table(table).update(payload(r, v)).eq('id', r['id']).execute()
                stats['embedded'] += 1
            except Exception as exc:
                logger.error('%s: store failed for %s: %s', name, r['id'], exc)
                stats['failed'] += 1
        logger.info('  %s: %d/%d', name, stats['embedded'], len(rows))
    return stats


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    p.add_argument('--only', nargs='+', choices=list(TARGETS), default=list(TARGETS))
    p.add_argument('--batch', type=int, default=64)
    p.add_argument('--limit', type=int)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        stream=sys.stdout)
    for noisy in ('httpx', 'httpcore', 'openai', 'urllib3'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    db = admin_db()
    client = None if args.dry_run else get_embedder()
    total = {'embedded': 0, 'failed': 0, 'tokens_est': 0}
    for name in args.only:
        s = run(db, client, name, args.batch, args.limit, args.dry_run)
        for k in total:
            total[k] += s[k]
    logger.info('total: %s (~$%.4f at $0.02/M tokens)', total,
                total['tokens_est'] / 1e6 * 0.02)


if __name__ == '__main__':
    main()
