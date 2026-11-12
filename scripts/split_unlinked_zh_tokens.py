#!/usr/bin/env python3
"""Make unlinked Chinese compounds clickable in existing word maps (2026-11-12).

jieba's dictionary holds many compounds and phrases our dictionary has no entry
for (器官移植, 外科医生, 书桌上, 记录下来, 闪烁着); in tests.vocab_token_map they
are tokens with sense 0, so the reader shows them as plain text. New maps
split them at build time (services/vocabulary/zh_segmenter.split_unlinked, used
by scripts/sense_linking_common.py and the test-generation orchestrator); this
applies the same step to the maps already stored.

Only tokens with sense 0 change: each is split into dictionary words, and is
replaced only when a content-word piece gets a link. Every linked token keeps
its sense; the map still concatenates to the transcript. New links are added
to tests.vocab_sense_ids. Sentence token spans then need refreshing:
    python scripts/build_test_sentences.py --resegment --apply

Usage:
    python scripts/split_unlinked_zh_tokens.py            # dry run
    python scripts/split_unlinked_zh_tokens.py --apply    # writes a backup first
"""

import argparse
import datetime
import gzip
import json
import logging
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(ROOT, '.env'))

from scripts.sense_linking_common import VocabIndex, split_unlinked_zh  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger('split_unlinked_zh')
for noisy in ('httpx', 'jieba', 'scripts.sense_linking_common'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

ZH = 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    tests, start = [], 0
    while True:
        chunk = (db.table('tests').select('id, slug, transcript, vocab_token_map, vocab_sense_ids')
                 .eq('language_id', ZH).eq('is_active', True).order('id')
                 .range(start, start + 99).execute().data or [])
        tests += chunk
        if len(chunk) < 100:
            break
        start += 100
    index = VocabIndex(db, ZH, 'zh')
    plans, pieces = [], Counter()
    for t in tests:
        old = t.get('vocab_token_map') or []
        if not old:
            continue
        new = split_unlinked_zh(db, ZH, old, {}, lambda lemma: index.resolve(lemma)[0])
        if new == [list(e) for e in old]:
            continue
        assert ''.join(s for s, _ in new) == ''.join(s for s, _ in old), t['slug']
        before = sum(1 for _, s in old if s)
        after = sum(1 for _, s in new if s)
        for s, sid in new:
            if sid and s.strip() not in {x.strip() for x, y in old if y}:
                pieces[s.strip()] += 1
        ids = list(t.get('vocab_sense_ids') or [])
        added = [sid for _, sid in new if sid and sid not in ids]
        plans.append((t, new, ids + list(dict.fromkeys(added))))
        log.info('%s: linked tokens %d -> %d', t['slug'][:50], before, after)
    log.info('%d tests to update; most common new links: %s', len(plans),
             ', '.join(f'{w}×{n}' for w, n in pieces.most_common(25)))
    if not args.apply or not plans:
        if not args.apply:
            log.info('dry run: nothing written (use --apply)')
        return 0
    out_dir = os.path.join(ROOT, 'data', 'zh_segmentation')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f'{datetime.date.today().isoformat()}_split_unlinked_backup.json.gz')
    n = 2
    while os.path.exists(path):  # never overwrite an earlier run's backup
        path = os.path.join(out_dir, f'{datetime.date.today().isoformat()}_split_unlinked_backup_{n}.json.gz')
        n += 1
    with gzip.open(path, 'wt', encoding='utf-8') as fh:
        json.dump([{'id': t['id'], 'vocab_token_map': t['vocab_token_map'],
                    'vocab_sense_ids': t['vocab_sense_ids']} for t, _, _ in plans], fh, ensure_ascii=False)
    log.info('backup written: %s', path)
    for t, new, ids in plans:
        db.table('tests').update({'vocab_token_map': new, 'vocab_sense_ids': ids}).eq('id', t['id']).execute()
    log.info('applied: %d tests', len(plans))
    return 0


if __name__ == '__main__':
    sys.exit(main())
