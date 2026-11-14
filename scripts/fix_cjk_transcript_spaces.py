#!/usr/bin/env python3
"""Remove stray spaces between Chinese characters in a test transcript (2026-11-12).

Some generated zh transcripts carry spaces inside sentences ("我们要 洗 手。 洗
手很重要。"). Spaces are not spoken, so the audio is unaffected; the text,
and everything derived from it, is rebuilt:
  - tests.transcript (spaces between CJK characters/punctuation removed)
  - tests.vocab_token_map, rebuilt with the sense-linking builder seeded from
    the test's own vocab_sense_ids (new links added to vocab_sense_ids)
  - tests.pinyin_payload (services/pinyin_service.process_passage)
  - tests.transcript_hash and test_sentences: rebuild afterwards with
    python scripts/build_test_sentences.py --apply --test-id <id>
A backup of every changed column is written first.

Usage:
    python scripts/fix_cjk_transcript_spaces.py SLUG            # dry run
    python scripts/fix_cjk_transcript_spaces.py SLUG --apply
"""

import argparse
import datetime
import json
import logging
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    from _common import admin_db, base_parser, bootstrap
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import admin_db, base_parser, bootstrap

bootstrap(log_format='%(message)s')


log = logging.getLogger('fix_cjk_spaces')
for noisy in ('httpx', 'jieba'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

_CJK = r'[　-〿一-鿿＀-￯]'
_SPACE_BETWEEN_CJK = re.compile(rf'(?<={_CJK})[ \t]+(?={_CJK})')


def clean(text: str) -> str:
    return _SPACE_BETWEEN_CJK.sub('', text or '')


def main() -> int:
    ap = base_parser(__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('slug')
    args = ap.parse_args()
    from services.pinyin_service import process_passage
    from scripts.sense_linking_common import VocabIndex, build_token_map_with_fallback, lemma_sense_lookup
    db = admin_db()
    rows = (db.table('tests').select('id, slug, language_id, transcript, vocab_token_map, vocab_sense_ids, pinyin_payload')
            .eq('slug', args.slug).execute().data or [])
    if not rows or rows[0]['language_id'] != 1:
        log.error('no Chinese test with slug %s', args.slug)
        return 1
    t = rows[0]
    new_text = clean(t['transcript'])
    if new_text == t['transcript']:
        log.info('nothing to fix')
        return 0
    index = VocabIndex(db, 1, 'zh')
    ids = list(t.get('vocab_sense_ids') or [])
    new_map, unmatched = build_token_map_with_fallback(
        db, 'zh', 1, new_text, lemma_sense_lookup(db, ids), resolve_vocab_id=lambda l: index.resolve(l)[0])
    assert ''.join(s for s, _ in new_map) == new_text
    new_ids = ids + list(dict.fromkeys(s for _, s in new_map if s and s not in ids))
    pinyin = process_passage(new_text)
    log.info('before: %s', t['transcript'])
    log.info('after:  %s', new_text)
    log.info('linked tokens %d -> %d; unmatched: %s; pinyin chars needing review: %d',
             sum(1 for _, s in t['vocab_token_map'] or [] if s), sum(1 for _, s in new_map if s),
             ', '.join(unmatched) or '-', sum(1 for p in pinyin if p.get('requires_review')))
    if not args.apply:
        log.info('dry run: nothing written (use --apply)')
        return 0
    out_dir = os.path.join(ROOT, 'data', 'transcript_fixes')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{datetime.date.today().isoformat()}_{t['slug']}.json")
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({k: t[k] for k in ('id', 'slug', 'transcript', 'vocab_token_map', 'vocab_sense_ids', 'pinyin_payload')},
                  fh, ensure_ascii=False)
    log.info('backup written: %s', path)
    db.table('tests').update({'transcript': new_text, 'vocab_token_map': new_map, 'vocab_sense_ids': new_ids,
                              'pinyin_payload': pinyin}).eq('id', t['id']).execute()
    log.info('applied; now run: python scripts/build_test_sentences.py --apply --test-id %s', t['id'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
