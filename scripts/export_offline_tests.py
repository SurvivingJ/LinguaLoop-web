#!/usr/bin/env python3
"""Generate comprehension tests offline into a compressed bundle (no DB writes).

Runs the normal test-generation path (prose, tier, title, judged questions,
furigana and pitch payloads) with ``dry_run=True`` and an export sink, so each
finished test becomes one JSON record instead of database rows. Audio and
vocabulary linking are left for upload time (``scripts/upload_offline_tests.py``),
because they write to R2 and to the dictionary.

Slots are (topic, target tier) pairs over every ``production_queue`` topic
of the language (any status). Every slot also gets a writing angle, because the
claude-cli transport has no sampling control: the same topic and tier would
otherwise produce the same passage as a live test written from that topic.

Meant to run with every LLM call on headless Claude and nothing written to the
database:

    LLM_FORCE_PROVIDER=claude_cli LLM_CALLS_DB_LOG=0 \\
      python -m scripts.export_offline_tests --language ja --count 500 \\
        --tiers 1,2,3,4 --shards 4 --shard 0 --out data/offline_tests/ja-2026-11-27

Run one process per shard (``--shard 0`` .. ``--shard N-1``). Each appends to
``<out>/shards/shard_<k>.jsonl`` and skips slots already there, so a stopped
shard resumes where it left off. Then ``--assemble`` writes
``<out>/tests.jsonl.xz`` and ``<out>/manifest.json``.

Without ``--provider claude-cli`` and ``LLM_FORCE_PROVIDER=claude_cli`` the
calls go to the configured providers (OpenRouter by default).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import lzma
import os
import sys
import threading
from datetime import datetime, timezone
from uuid import UUID

try:
    from _common import bootstrap
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import bootstrap

bootstrap(log_level=None)

logger = logging.getLogger('export_offline_tests')

#: Appended to the prose prompt, one per slot (rotated). English is fine: the
#: prose templates already carry English instructions around the topic.
ANGLES = (
    'an everyday scene: one person dealing with this in their daily life',
    'a short news-style report about something that happened recently',
    'a plain explanation of how it works, step by step',
    'one person giving an opinion with two clear reasons',
    'a comparison of two options or two ways of doing it',
    'a short look at how it started and how it changed over time',
    'advice for a beginner who wants to try it',
    'a description of a place or an event connected to it',
)

LANG_IDS = {'zh': 1, 'en': 2, 'ja': 3}


def angle_instruction(angle: str, note: str = '') -> str:
    text = (
        f'\n\nWrite this passage as {angle}. Keep to the topic, the level and '
        'the length given above.'
    )
    if note:
        text += f'\n{note.strip()}'
    return text


def slot_key(topic_id: str, tier: int, variant: int = 0) -> str:
    return f'{topic_id}:T{tier}' + (f':v{variant}' if variant else '')


def build_slots(topic_ids: list[str], tiers: list[int], count: int,
                exclude: frozenset = frozenset(), angle_offset: int = 0,
                variant: int = 0) -> list[dict]:
    """(topic, tier, angle) slots, broad before deep.

    Topic i takes the tiers in an order rotated by i, and slots are ranked by
    (round, topic): every topic gets its first tier before any topic gets a
    second, so a run of ``count`` slots covers as many topics as it can and
    keeps the tiers balanced. Angles rotate per slot.

    ``exclude`` drops slot keys already built (e.g. in an earlier bundle), and
    ``angle_offset`` shifts the angle rotation, so a second bundle over the
    same topics does not repeat a (topic, tier, angle) prompt. ``variant`` > 0
    makes keys ``<topic>:T<tier>:v<variant>``: a further test for a (topic, tier)
    pair that is already used, written from a different angle (pair it with
    a new ``angle_offset``).
    """
    ranked = []
    for t_idx, topic_id in enumerate(topic_ids):
        rotated = tiers[t_idx % len(tiers):] + tiers[:t_idx % len(tiers)]
        for rnd, tier in enumerate(rotated):
            angle = ANGLES[(t_idx + tier + angle_offset) % len(ANGLES)]
            if slot_key(topic_id, tier, variant) in exclude:
                continue
            ranked.append(((rnd, t_idx), {
                'topic_id': topic_id, 'tier': tier, 'angle': angle,
                'key': slot_key(topic_id, tier, variant),
            }))
    ranked.sort(key=lambda p: p[0])
    return [slot for _, slot in ranked[:count]]


def shard_slots(slots: list[dict], shards: int, shard: int) -> list[dict]:
    return [s for i, s in enumerate(slots) if i % shards == shard]


def read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _paged(query_fn) -> list[dict]:
    rows, start = [], 0
    while True:
        page = query_fn().range(start, start + 999).execute().data or []
        rows.extend(page)
        if len(page) < 1000:
            return rows
        start += 1000


def queue_topic_ids(db, language_id: int) -> list[str]:
    """Every topic queued for the language (any status), fewest existing tests
    in that language first, then oldest queue row first. Read-only."""
    rows = _paged(lambda: db.client.table('production_queue')
                  .select('topic_id, created_at, id').eq('language_id', language_id)
                  .order('created_at').order('id'))
    tests = _paged(lambda: db.client.table('tests').select('topic_id')
                   .eq('language_id', language_id).order('id'))
    live = {}
    for t in tests:
        live[t['topic_id']] = live.get(t['topic_id'], 0) + 1
    order, seen = [], set()
    for r in rows:
        if r['topic_id'] not in seen:
            seen.add(r['topic_id'])
            order.append(r['topic_id'])
    position = {tid: i for i, tid in enumerate(order)}
    return sorted(order, key=lambda tid: (live.get(tid, 0), position[tid]))


def load_prior_bundles(paths) -> list[dict]:
    """Records of earlier bundles (``--exclude-bundle DIR``), for their slot
    keys and passage hashes."""
    out = []
    for path in paths or []:
        with lzma.open(os.path.join(path, 'tests.jsonl.xz'), 'rt', encoding='utf-8') as f:
            out.extend(json.loads(line) for line in f if line.strip())
    return out


def run_shard(args) -> int:
    from services.supabase_factory import SupabaseFactory
    from services.test_generation.orchestrator import TestGenerationOrchestrator
    from services.exercise_generation.judges.base import (
        BatchModeThreadPoolExecutor, JudgeUnavailable, batch_mode,
    )

    SupabaseFactory.initialize()
    orch = TestGenerationOrchestrator()
    lang_config = orch.db.get_language_config_by_code(args.language)
    if not lang_config:
        raise SystemExit(f'unknown language {args.language!r}')

    topic_ids = queue_topic_ids(orch.db, lang_config.id)
    tiers = [int(t) for t in args.tiers.split(',')]
    prior = load_prior_bundles(args.exclude_bundle)
    slots = build_slots(topic_ids, tiers, args.count,
                        exclude=frozenset(r['slot_key'] for r in prior),
                        angle_offset=args.angle_offset, variant=args.variant)
    mine = shard_slots(slots, args.shards, args.shard)

    shard_dir = os.path.join(args.out, 'shards')
    os.makedirs(shard_dir, exist_ok=True)
    out_path = os.path.join(shard_dir, f'shard_{args.shard}.jsonl')
    fail_path = os.path.join(shard_dir, f'shard_{args.shard}.failures.jsonl')
    done = {r['slot_key'] for r in read_jsonl(out_path)}
    hashes = {r.get('passage_hash') for r in read_jsonl(out_path)} | {
        r.get('passage_hash') for r in prior}
    todo = [s for s in mine if s['key'] not in done]
    logger.info(
        'shard %d/%d: %d topics, %d slots total, %d mine, %d done, %d to do',
        args.shard, args.shards, len(topic_ids), len(slots), len(mine),
        len(mine) - len(todo), len(todo),
    )

    lock = threading.Lock()
    counts = {'saved': 0, 'failed': 0, 'duplicate': 0}

    def write(path, obj):
        with lock, open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + '\n')
            f.flush()

    def one(slot):
        topic = orch.db.get_topic(UUID(slot['topic_id']))
        if not topic:
            write(fail_path, {**slot, 'error': 'topic missing'})
            counts['failed'] += 1
            return
        category_name = orch.db.get_category_name(topic.category_id)
        captured = []
        try:
            ok = orch._generate_test(
                topic=topic, lang_config=lang_config, category_name=category_name,
                tier_id=slot['tier'], test_type=args.type, dry_run=True,
                prose_extra_instruction=angle_instruction(slot['angle'], args.prose_note),
                export_sink=captured.append,
            )
        except JudgeUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 -- one slot never stops the shard
            write(fail_path, {**slot, 'error': f'{type(exc).__name__}: {exc}'[:500]})
            counts['failed'] += 1
            logger.warning('slot %s failed: %s', slot['key'], exc)
            return
        if not ok or not captured:
            write(fail_path, {**slot, 'error': 'skipped (duplicate or no record)'})
            counts['failed'] += 1
            return
        record = captured[0]
        with lock:
            if record.get('passage_hash') in hashes:
                counts['duplicate'] += 1
                dup = True
            else:
                hashes.add(record.get('passage_hash'))
                dup = False
        if dup:
            write(fail_path, {**slot, 'error': 'duplicate passage within bundle'})
            return
        # Slugs are topic + difficulty + second: two slots of one topic can
        # collide, so the bundle makes each unique with the test id.
        record['slug'] = f"{record['slug']}-{record['test_id'][:8]}"
        record['slot_key'] = slot['key']
        record['slot_angle'] = slot['angle']
        write(out_path, record)
        counts['saved'] += 1
        logger.info('saved %s (%s, seeded ELO %s) [%d saved, %d failed]',
                    record['slug'], slot['key'], record.get('seeded_elo'),
                    counts['saved'], counts['failed'])

    with batch_mode():
        with BatchModeThreadPoolExecutor(max_workers=args.workers) as pool:
            for future in [pool.submit(one, s) for s in todo]:
                future.result()

    logger.info('shard %d finished: %s', args.shard, counts)
    return 0


def assemble(args) -> int:
    shard_dir = os.path.join(args.out, 'shards')
    records, failures = [], []
    for name in sorted(os.listdir(shard_dir)):
        path = os.path.join(shard_dir, name)
        if name.endswith('.failures.jsonl'):
            failures.extend(read_jsonl(path))
        elif name.endswith('.jsonl'):
            records.extend(read_jsonl(path))
    by_key = {}
    for r in records:
        by_key.setdefault(r['slot_key'], r)   # first record per slot wins
    records = sorted(by_key.values(), key=lambda r: r['slot_key'])
    seen, unique = set(), []
    for r in records:
        if r.get('passage_hash') in seen:
            continue
        seen.add(r.get('passage_hash'))
        unique.append(r)

    payload = ''.join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in unique
    ).encode('utf-8')
    xz_path = os.path.join(args.out, 'tests.jsonl.xz')
    with lzma.open(xz_path, 'wb', preset=9) as f:
        f.write(payload)

    tiers, elos, models = {}, [], {}
    for r in unique:
        tiers[str(r['tier_id'])] = tiers.get(str(r['tier_id']), 0) + 1
        if r.get('seeded_elo') is not None:
            elos.append(r['seeded_elo'])
        models[r.get('generation_model')] = models.get(r.get('generation_model'), 0) + 1
    elos.sort()
    manifest = {
        'format': 'lingualoop-offline-tests',
        'record_version': unique[0]['record_version'] if unique else None,
        'language': args.language,
        'built_at': datetime.now(timezone.utc).isoformat(),
        'tests': len(unique),
        'questions': sum(len(r['questions']) for r in unique),
        'topics': len({r['topic_id'] for r in unique}),
        'assigned_tiers': dict(sorted(tiers.items())),
        'seeded_elo': {
            'min': elos[0] if elos else None,
            'median': elos[len(elos) // 2] if elos else None,
            'max': elos[-1] if elos else None,
        },
        'generation_models': models,
        'failed_slots': len({f['key'] for f in failures} - set(by_key)),
        'file': 'tests.jsonl.xz',
        'sha256': hashlib.sha256(open(xz_path, 'rb').read()).hexdigest(),
        'uncompressed_bytes': len(payload),
        'compressed_bytes': os.path.getsize(xz_path),
        'not_included': ['audio (made at upload)', 'vocabulary linking (made at upload)',
                         'passage_embedding (no OpenAI key at build time)'],
    }
    with open(os.path.join(args.out, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--language', required=True, choices=sorted(LANG_IDS))
    p.add_argument('--out', required=True, help='bundle directory')
    p.add_argument('--count', type=int, default=500)
    p.add_argument('--tiers', default='1,2,3,4')
    p.add_argument('--type', default='listening', choices=['listening', 'reading'])
    p.add_argument('--shards', type=int, default=1)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--exclude-bundle', action='append', default=[],
                   help='earlier bundle dir whose slots and passages to skip (repeatable)')
    p.add_argument('--prose-note', default='',
                   help='extra instruction appended to every prose prompt (e.g. a target exam level)')
    p.add_argument('--variant', type=int, default=0,
                   help='N > 0: extra slots <topic>:T<tier>:vN for pairs already used')
    p.add_argument('--angle-offset', type=int, default=0,
                   help='shift the angle rotation (use a new value per bundle over the same topics)')
    p.add_argument('--assemble', action='store_true',
                   help='merge the shard files into tests.jsonl.xz + manifest.json')
    from scripts.provider_arg import add_provider_arg, apply_provider
    add_provider_arg(p)
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, stream=sys.stdout,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    for noisy in ('httpx', 'httpcore', 'urllib3'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if args.assemble:
        return assemble(args)
    if not 0 <= args.shard < args.shards:
        p.error('--shard must be in [0, --shards)')
    apply_provider(args.provider)
    return run_shard(args)


if __name__ == '__main__':
    sys.exit(main())
