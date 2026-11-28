#!/usr/bin/env python3
"""Load an offline test bundle (``scripts/export_offline_tests.py``) into the database.

Reads ``<bundle>/tests.jsonl.xz`` and saves each record through the same path
a live generation run uses (``TestGenerationOrchestrator.persist_exported_test``):
audio (Azure TTS -> R2), the test row, questions, review-queue rows for
judge-flagged questions, skill ratings, furigana/pitch payloads, then
vocabulary linking.

Dry run by default: it reports what it would load and why it would skip a
record. ``--apply`` writes.

A record is skipped when its test id is already in ``tests``, its topic no
longer exists, or a test with the same passage hash already exists for that
topic. With a working ``OPENAI_API_KEY`` the passage is embedded, stored in
``passage_embedding`` and checked against near-duplicates like a live run;
without one the near-duplicate check is skipped and the column stays NULL.

    python -m scripts.upload_offline_tests --bundle data/offline_tests/ja-2026-11-27
    LLM_FORCE_PROVIDER=claude_cli AZURE_TTS_TRANSPORT=rest \\
      python -m scripts.upload_offline_tests --bundle ... --provider claude-cli --apply --limit 50

Mind the database size before a large upload: on 2026-11-27 a live test plus
its vocabulary linking cost roughly 45 KB including llm_calls rows
(``LLM_CALLS_DB_LOG=0`` keeps call logs out of the database).
"""

from __future__ import annotations

import argparse
import json
import logging
import lzma
import os
import sys
from uuid import UUID

try:
    from _common import bootstrap
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import bootstrap

bootstrap(log_level=None)

logger = logging.getLogger('upload_offline_tests')


def load_bundle(bundle: str) -> tuple[dict, list[dict]]:
    with open(os.path.join(bundle, 'manifest.json'), encoding='utf-8') as f:
        manifest = json.load(f)
    path = os.path.join(bundle, manifest.get('file', 'tests.jsonl.xz'))
    with lzma.open(path, 'rt', encoding='utf-8') as f:
        records = [json.loads(line) for line in f if line.strip()]
    return manifest, records


def _elo(r: dict):
    return r.get('seeded_elo') or r.get('initial_elo')


def select(records: list[dict], *, tiers=None, min_elo=None, max_elo=None, limit=None,
           near_elo=None, one_per_topic=False):
    """Filter, then (``near_elo``) order by closeness to that ELO, then
    (``one_per_topic``) keep the first record per topic, then cap at ``limit``."""
    out = []
    for r in records:
        if tiers and r.get('tier_id') not in tiers:
            continue
        elo = _elo(r)
        if min_elo is not None and (elo is None or elo < min_elo):
            continue
        if max_elo is not None and (elo is None or elo > max_elo):
            continue
        out.append(r)
    if near_elo is not None:
        out.sort(key=lambda r: (abs((_elo(r) or 0) - near_elo), r.get('slot_key', '')))
    if one_per_topic:
        seen, unique = set(), []
        for r in out:
            if r['topic_id'] not in seen:
                seen.add(r['topic_id'])
                unique.append(r)
        out = unique
    return out[:limit] if limit else out


def skip_reason(db, record: dict) -> str | None:
    if db.client.table('tests').select('id').eq('id', record['test_id']).limit(1).execute().data:
        return 'already loaded (test id exists)'
    if not db.get_topic(UUID(record['topic_id'])):
        return 'topic no longer exists'
    if record.get('passage_hash'):
        dup = (
            db.client.table('tests').select('id')
            .eq('topic_id', record['topic_id'])
            .eq('passage_hash', record['passage_hash']).limit(1).execute().data
        )
        if dup:
            return f"same passage already live (test {dup[0]['id']})"
    return None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--bundle', required=True)
    p.add_argument('--apply', action='store_true', help='write (default: dry run)')
    p.add_argument('--limit', type=int)
    p.add_argument('--tiers', help='comma list of assigned tiers to load, e.g. 2,3')
    p.add_argument('--min-elo', type=int)
    p.add_argument('--max-elo', type=int)
    p.add_argument('--near-elo', type=int, help='take the records closest to this ELO first')
    p.add_argument('--one-per-topic', action='store_true', help='at most one record per topic')
    from scripts.provider_arg import add_provider_arg, apply_provider
    add_provider_arg(p)
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, stream=sys.stdout,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    for noisy in ('httpx', 'httpcore', 'urllib3'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    manifest, records = load_bundle(args.bundle)
    tiers = {int(t) for t in args.tiers.split(',')} if args.tiers else None
    chosen = select(records, tiers=tiers, min_elo=args.min_elo,
                    max_elo=args.max_elo, limit=args.limit,
                    near_elo=args.near_elo, one_per_topic=args.one_per_topic)
    logger.info('bundle: %d records (%s); selected %d; %s',
                len(records), manifest.get('language'), len(chosen),
                'APPLY' if args.apply else 'dry run')

    apply_provider(args.provider)
    from services.supabase_factory import SupabaseFactory
    from services.test_generation.orchestrator import TestGenerationOrchestrator
    from services.test_generation.dedup import PassageDedupChecker
    SupabaseFactory.initialize()
    orch = TestGenerationOrchestrator()
    dedup = PassageDedupChecker(orch.db)

    loaded = skipped = failed = 0
    for i, record in enumerate(chosen, 1):
        reason = skip_reason(orch.db, record)
        embedding = None
        if reason is None and os.environ.get('OPENAI_API_KEY'):
            try:
                embedding = dedup.embedding_service.embed_single(record['transcript'])
                near = dedup.check_near_duplicate(
                    UUID(record['topic_id']), record['tier_id'], embedding)
                if near.is_duplicate:
                    reason = f'near-duplicate of test {near.matched_test_id} ({near.similarity})'
            except Exception as exc:  # noqa: BLE001 -- degrade like a live run
                logger.warning('embedding failed for %s, near-dup check skipped: %s',
                               record['slug'], exc)
                embedding = None
        if reason:
            skipped += 1
            logger.info('[%d/%d] skip %s: %s', i, len(chosen), record['slug'], reason)
            continue
        if not args.apply:
            loaded += 1
            logger.info('[%d/%d] would load %s (tier %s, ELO %s, %d questions)',
                        i, len(chosen), record['slug'], record['tier_id'],
                        record.get('seeded_elo'), len(record['questions']))
            continue
        try:
            orch.persist_exported_test(record, passage_embedding=embedding)
            loaded += 1
            logger.info('[%d/%d] loaded %s', i, len(chosen), record['slug'])
        except Exception as exc:  # noqa: BLE001 -- report and continue
            failed += 1
            logger.error('[%d/%d] failed %s: %s', i, len(chosen), record['slug'], exc)

    logger.info('%s: %d loaded, %d skipped, %d failed',
                'applied' if args.apply else 'dry run', loaded, skipped, failed)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
