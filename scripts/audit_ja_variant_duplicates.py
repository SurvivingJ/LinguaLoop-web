#!/usr/bin/env python3
"""
Audit ja dictionary rows that are spelling variants of one word (TASK-779 step 4).

Why
    売り上げ and 売上, アイディア and アイデア, 若し and 若い are one word each, but
    the dictionary holds two rows. Knowledge tracking, exercises and coverage all
    key on the row, so a learner who knows one spelling gets no credit for the
    other. The 36 spelling-variant links TASK-779 repointed were only the part
    visible from ja test transcripts; this reports the whole ja dictionary.

Method — read-only, no LLM
    Group rows by reading (dim_vocabulary.reading, else the tokenizer's reading
    for the lemma). Within a group, classify each pair:
      okurigana       same kanji, different kana (売り上げ / 売上)
      kana_variant    kana-only spellings differing by ー, ヴ, ィ… (アイディア / アイデア)
      classical       …し with a modern …い twin (若し / 若い)
      same_kanji_set  identical kanji, other differences (日溜まり / 日だまり)
      homophone       different kanji — DIFFERENT WORDS, never merge (橋 / 箸)
    Only the first four are merge candidates; homophones are reported separately
    so the count cannot be mistaken for a to-do list.

Usage:
    python scripts/audit_ja_variant_duplicates.py [--out report.json]
"""

import os
import sys
import re
import json
import argparse
import logging
from collections import defaultdict
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), '.env'))

from config import Config
from scripts.sense_linking_common import PAGE, get_processor

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

KANJI = re.compile(r'[一-鿿]')
KANA_ONLY = re.compile(r'^[ぁ-ゟァ-ヿー]+$')

# Katakana spellings of one loanword differ by the long mark, ヴ, and small kana:
# アイディア/アイデア, アクチュエーター/アクチュエータ, ヴォールト/ボールト. Their *readings*
# differ too, so a reading key alone never groups them — hence this second key.
_SMALL_TO_LARGE = str.maketrans('ァィゥェォャュョヵヶ', 'アイウエオヤユヨカケ')


def kana_key(lemma: str) -> str:
    if not KANA_ONLY.match(lemma):
        return ''
    k = ''.join(chr(ord(c) + 0x60) if 'ぁ' <= c <= 'ゖ' else c for c in lemma)
    return k.replace('ー', '').replace('ヴ', 'ブ').translate(_SMALL_TO_LARGE)


def kanji_set(lemma: str) -> frozenset:
    return frozenset(KANJI.findall(lemma))


def classify(a: str, b: str, pos_a=None, pos_b=None) -> str:
    """Spelling variants of one word, or two different words that sound alike.

    Part of speech is load-bearing: 取る/取り and 多く/多い share a reading and a
    kanji, but they are a verb and a noun, an adverb and an adjective — different
    dictionary entries, not two spellings of one.
    """
    ka, kb = kanji_set(a), kanji_set(b)
    if pos_a and pos_b and pos_a != pos_b:
        return 'different_pos'
    if KANA_ONLY.match(a) and KANA_ONLY.match(b):
        return 'kana_variant'
    if {a[-1], b[-1]} == {'し', 'い'} and ka == kb:
        return 'classical'
    if ka and ka == kb:
        return 'okurigana'
    # One spelling writes a morpheme in kana that the other writes in kanji
    # (錆びつく / 錆び付く): same word, one kanji set contained in the other.
    if ka and kb and (ka < kb or kb < ka):
        return 'okurigana'
    if ka and kb and ka != kb:
        return 'homophone'
    return 'mixed_script'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out')
    args = parser.parse_args()

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    language_id = Config.LANGUAGE_CODE_TO_ID['ja']

    rows, off = [], 0
    while True:
        page = (db.table('dim_vocabulary').select('id, lemma, reading, part_of_speech, frequency_rank')
                .eq('language_id', language_id).range(off, off + PAGE - 1).execute().data or [])
        rows += page
        if len(page) < PAGE:
            break
        off += PAGE
    logger.info("ja vocab rows: %d", len(rows))

    proc = get_processor('ja')
    by_reading = defaultdict(list)
    for r in rows:
        reading = r.get('reading') or proc.reading_for(r['lemma'])
        if reading:
            by_reading[f'r:{reading}'].append(r)
        kk = kana_key(r['lemma'])
        if kk:
            by_reading[f'k:{kk}'].append(r)

    # usage counts, so a pair can be ranked by how much it actually costs
    senses = defaultdict(int)
    off = 0
    while True:
        page = (db.table('dim_word_senses').select('id, vocab_id')
                .range(off, off + PAGE - 1).execute().data or [])
        for s in page:
            senses[s['vocab_id']] += 1
        if len(page) < PAGE:
            break
        off += PAGE

    pairs = defaultdict(list)
    seen_pairs = set()
    for reading, group in by_reading.items():
        if len(group) < 2:
            continue
        for a, b in combinations(sorted(group, key=lambda r: r['id']), 2):
            if (a['id'], b['id']) in seen_pairs:      # reachable under both keys
                continue
            seen_pairs.add((a['id'], b['id']))
            kind = classify(a['lemma'], b['lemma'],
                            a.get('part_of_speech'), b.get('part_of_speech'))
            pairs[kind].append({
                'reading': reading,
                'a': {'id': a['id'], 'lemma': a['lemma'], 'senses': senses.get(a['id'], 0)},
                'b': {'id': b['id'], 'lemma': b['lemma'], 'senses': senses.get(b['id'], 0)},
            })

    mergeable = ('okurigana', 'kana_variant', 'classical', 'same_kanji_set')
    logger.info("")
    logger.info("HEURISTIC OUTPUT — A REVIEW LIST, NOT A TO-DO LIST. Reading plus kanji "
                "plus part of speech does not separate one word's two spellings from two "
                "words that sound alike: 風邪/風 and こと/コート land in 'okurigana' and "
                "'kana_variant', while genuine variants (錆び付く/錆びつく, 生かす/活かす) "
                "land in 'different_pos' because the POS column disagrees with itself. "
                "Every pair needs a human or an LLM judge before any merge.")
    for kind in mergeable + ('mixed_script', 'different_pos', 'homophone'):
        got = pairs.get(kind, [])
        tag = 'review' if kind in mergeable else 'mostly distinct words'
        logger.info("%-15s %4d pair(s)  [%s]", kind, len(got), tag)
        for p in got[:8]:
            logger.info("    %s (%d senses) / %s (%d senses)",
                        p['a']['lemma'], p['a']['senses'], p['b']['lemma'], p['b']['senses'])

    total = sum(len(pairs.get(k, [])) for k in mergeable)
    logger.info("\n%d pair(s) in the review buckets, %d total pairs sharing a reading or "
                "kana key. Judge before merging.",
                total, sum(len(v) for v in pairs.values()))

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as fh:
            json.dump(pairs, fh, ensure_ascii=False, indent=1)
        logger.info("Full report: %s", args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
