#!/usr/bin/env python3
"""
Audit existing kana-only dim_vocabulary rows (Japanese) for the
segmentation-fragment defect: a UniDic sub-word piece (often a
sokuon-truncated syllable from a compound, or a verb stem) that got
registered as if it were a standalone word, carrying the definition of the
longer word it was actually cut from.

Read-only / report-only — this script never deletes or modifies rows. It
runs the classify_kana_lemma judge (services/vocabulary/kana_homophone_judge.py)
over every kana-only Japanese dim_vocabulary lemma, and additionally
reports how many live rows reference each one (tests.vocab_sense_ids,
questions.sense_ids, word_assets.sense_id, user_vocabulary_knowledge,
user_flashcards, vocabulary_review_queue) so a human can weigh "is this
safe to delete" alongside "is this a real word".

Usage:
    python scripts/audit_kana_fragments.py [--limit N]
"""

import sys
import os
import re
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.vocabulary.kana_homophone_judge import classify_kana_lemma

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LANGUAGE_ID_JA = 3
_KANA_ONLY = re.compile(r'^[ぁ-ゟー]+$')  # hiragana + ー only


def _reference_counts(db, sense_ids: list[int]) -> dict:
    if not sense_ids:
        return {'tests': 0, 'questions': 0, 'word_assets': 0,
                'user_knowledge': 0, 'flashcards': 0, 'review_queue': 0}

    def count(table, col, op='overlap'):
        try:
            if op == 'overlap':
                resp = db.table(table).select('id', count='exact') \
                    .overlaps(col, [str(s) for s in sense_ids]).limit(1).execute()
            else:
                resp = db.table(table).select('id', count='exact') \
                    .in_(col, sense_ids).limit(1).execute()
            return resp.count or 0
        except Exception as e:
            logger.warning("Reference count failed for %s.%s: %s", table, col, e)
            return -1

    return {
        'tests': count('tests', 'vocab_sense_ids'),
        'questions': count('questions', 'sense_ids'),
        'word_assets': count('word_assets', 'sense_id', op='in'),
        'user_knowledge': count('user_vocabulary_knowledge', 'sense_id', op='in'),
        'flashcards': count('user_flashcards', 'sense_id', op='in'),
        'review_queue': count('vocabulary_review_queue', 'sense_id', op='in'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = db.table('dim_vocabulary') \
            .select('id, lemma, part_of_speech') \
            .eq('language_id', LANGUAGE_ID_JA) \
            .range(offset, offset + page_size - 1) \
            .execute()
        page = resp.data or []
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    kana_rows = [r for r in all_rows if r.get('lemma') and _KANA_ONLY.match(r['lemma'])]
    if args.limit:
        kana_rows = kana_rows[:args.limit]

    print(f"# {len(kana_rows)} kana-only Japanese dim_vocabulary rows to audit "
          f"(of {len(all_rows)} total ja rows)\n")

    fragments = []
    legit = []
    unclassified = []

    for row in kana_rows:
        senses_resp = db.table('dim_word_senses') \
            .select('id, definition, sense_rank') \
            .eq('vocab_id', row['id']) \
            .order('sense_rank') \
            .execute()
        senses = senses_resp.data or []
        definitions = [s['definition'] for s in senses if s.get('definition')]
        sense_ids = [s['id'] for s in senses]

        verdict = classify_kana_lemma(
            db,
            lemma=row['lemma'],
            pos=row.get('part_of_speech'),
            definitions=definitions,
            language_id=LANGUAGE_ID_JA,
        )

        refs = _reference_counts(db, sense_ids)
        total_refs = sum(v for v in refs.values() if v > 0)

        record = {
            'vocab_id': row['id'],
            'lemma': row['lemma'],
            'pos': row.get('part_of_speech'),
            'sense_ids': sense_ids,
            'refs': refs,
            'total_refs': total_refs,
            'verdict': verdict,
        }

        if not verdict.get('ok'):
            unclassified.append(record)
        elif verdict.get('is_fragment'):
            fragments.append(record)
        else:
            legit.append(record)

    def fmt(record):
        v = record['verdict']
        refs = record['refs']
        ref_str = ', '.join(f"{k}={v}" for k, v in refs.items() if v != 0) or 'none'
        line = (f"  vocab_id={record['vocab_id']:<8} lemma={record['lemma']!r:<12} "
                f"pos={record['pos']!r:<8} refs=[{ref_str}]")
        if v.get('ok'):
            src = v.get('likely_source_word')
            if src:
                line += f"  -> likely fragment of {src!r}"
            line += f"  ({v.get('reason', '')[:80]})"
        return line

    print(f"## FRAGMENTS ({len(fragments)}) — likely safe to delete if refs=none\n")
    for r in sorted(fragments, key=lambda r: -r['total_refs']):
        print(fmt(r))

    print(f"\n## LEGITIMATE WORDS ({len(legit)}) — leave alone\n")
    for r in legit:
        print(fmt(r))

    if unclassified:
        print(f"\n## UNCLASSIFIED / judge failed ({len(unclassified)}) — needs manual review\n")
        for r in unclassified:
            print(fmt(r))

    referenced_fragments = [r for r in fragments if r['total_refs'] > 0]
    if referenced_fragments:
        print(f"\n## WARNING: {len(referenced_fragments)} fragment(s) ARE referenced by live "
              f"content — do not delete without checking what breaks:\n")
        for r in referenced_fragments:
            print(fmt(r))


if __name__ == '__main__':
    main()
