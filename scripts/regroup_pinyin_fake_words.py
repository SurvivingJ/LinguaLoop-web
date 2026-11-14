#!/usr/bin/env python3
"""Regroup pinyin payloads that still use retired fake words (2026-11-12).

tests.pinyin_payload (the tone game's per-character data) was built with plain
jieba, so 44 Chinese tests still group characters into the non-words retired by
scripts/retire_zh_fake_words.py (人用, 很强, 风一吹, ...). The pinyin builder now
uses the checked splitter (services/pinyin_service.segment_words).

Only the `word` (tone-group) field of a retired word's characters changes,
taken from a fresh build. Readings and tones are kept as stored: a dry run on
2026-11-12 found 1 reading of 112 that a fresh build would change, and it was
the stored one that was right (分得公平: 得 is neutral "de", a fresh build of
the lone 得 gives "dé").

Usage:
    python scripts/regroup_pinyin_fake_words.py            # dry run
    python scripts/regroup_pinyin_fake_words.py --apply    # writes a backup first
"""

import argparse
import copy
import datetime
import gzip
import json
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    from _common import admin_db, base_parser, bootstrap, paginate
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import admin_db, base_parser, bootstrap, paginate

bootstrap(log_format='%(message)s')


from services.pinyin_service import process_passage  # noqa: E402
from services.vocabulary import zh_segmenter  # noqa: E402

log = logging.getLogger('regroup_pinyin')
for noisy in ('httpx', 'jieba'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# The retired non-words and the two names kept whole (see retire_zh_fake_words).
FAKES = zh_segmenter.forced_splits()


def regroup(old: list[dict], fresh: list[dict]) -> tuple[list[dict], int]:
    """Return (new payload, characters regrouped).

    `fresh` must be a new build of the same text (same characters in order).
    """
    if [t['char'] for t in old] != [t['char'] for t in fresh]:
        raise ValueError('payload characters do not match the transcript')
    out = copy.deepcopy(old)
    regrouped = 0
    for tok, new in zip(out, fresh):
        if (tok.get('word') or '').strip() in FAKES:
            tok['word'] = new['word']
            regrouped += 1
    return out, regrouped


def main() -> int:
    ap = base_parser(__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args = ap.parse_args()
    db = admin_db()
    tests = []
    tests.extend(paginate(lambda: db.table('tests').select('id, slug, transcript, pinyin_payload').eq('language_id', 1)
                 .eq('is_active', True).not_.is_('pinyin_payload', 'null').order('id'), 100))
    plans, skipped = [], 0
    for t in tests:
        old = t['pinyin_payload'] or []
        if not any((tok.get('word') or '').strip() in FAKES for tok in old):
            continue
        text = ''.join(tok['char'] for tok in old)
        try:
            new, n_regrouped = regroup(old, process_passage(text))
        except ValueError as e:
            skipped += 1
            log.warning('%s: %s', t['slug'], e)
            continue
        if new != old:
            plans.append((t, new))
            log.info('%s: %d characters regrouped', t['slug'][:50], n_regrouped)
    log.info('%d tests to update, %d skipped', len(plans), skipped)
    if not args.apply or not plans:
        if not args.apply:
            log.info('dry run: nothing written (use --apply)')
        return 0
    out_dir = os.path.join(ROOT, 'data', 'zh_segmentation')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f'{datetime.date.today().isoformat()}_pinyin_regroup_backup.json.gz')
    n = 2
    while os.path.exists(path):  # never overwrite an earlier run's backup
        path = os.path.join(out_dir, f'{datetime.date.today().isoformat()}_pinyin_regroup_backup_{n}.json.gz')
        n += 1
    with gzip.open(path, 'wt', encoding='utf-8') as fh:
        json.dump([{'id': t['id'], 'pinyin_payload': t['pinyin_payload']} for t, _ in plans], fh, ensure_ascii=False)
    log.info('backup written: %s', path)
    for t, new in plans:
        db.table('tests').update({'pinyin_payload': new}).eq('id', t['id']).execute()
    log.info('applied: %d tests', len(plans))
    return 0


if __name__ == '__main__':
    sys.exit(main())
