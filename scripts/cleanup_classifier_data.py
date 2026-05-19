#!/usr/bin/env python3
"""
Classifier Data Cleanup

One-off maintenance pass that fixes two issues in the measure-word trainer
tables that accumulated from the CC-CEDICT import:

  1. Traditional Han characters were imported into dim_classifiers.hanzi,
     dim_classifier_noun_pairs.lemma_text, dim_classifier_example_sentences.*
     when CC-CEDICT entries had no simplified counterpart in the CL: tag.
     Convert every Han string to its simplified form using zhconv.

  2. dim_classifiers.pinyin_display still holds the raw numeric pinyin
     (e.g. "han4") for CC-CEDICT-imported rows. Convert each one to the
     proper diacritic form ("hàn") following standard pinyin orthography.

Run this once after import_cedict_classifiers.py. Idempotent — safe to re-run.

Usage:
    python scripts/cleanup_classifier_data.py            # apply
    python scripts/cleanup_classifier_data.py --dry-run  # preview only
"""

import os
import re
import sys
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import zhconv
from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LANGUAGE_ID_ZH = 1


# ============================================================================
# PINYIN: numeric -> diacritic
# ============================================================================
# Precomposed vowel-with-tone table. Index = tone (1-5; 5 = neutral / bare).
TONE_MARKS = {
    'a': [None, 'ā', 'á', 'ǎ', 'à', 'a'],
    'e': [None, 'ē', 'é', 'ě', 'è', 'e'],
    'i': [None, 'ī', 'í', 'ǐ', 'ì', 'i'],
    'o': [None, 'ō', 'ó', 'ǒ', 'ò', 'o'],
    'u': [None, 'ū', 'ú', 'ǔ', 'ù', 'u'],
    'ü': [None, 'ǖ', 'ǘ', 'ǚ', 'ǜ', 'ü'],
}

SYLLABLE_RE = re.compile(r'^([a-zü:]+?)([1-5])?$')


def to_diacritic(numeric_pinyin: str) -> str:
    """Convert a single-syllable numeric pinyin like 'han4' to 'hàn'.

    Handles 'u:' or 'v' as ü. Returns the input unchanged when it doesn't
    match the expected pattern or has an out-of-range tone.
    """
    if not numeric_pinyin:
        return numeric_pinyin
    s = numeric_pinyin.strip().lower()
    m = SYLLABLE_RE.match(s)
    if not m:
        return numeric_pinyin
    syl = m.group(1).replace('u:', 'ü').replace('v', 'ü')
    tone = int(m.group(2) or '5')
    if tone < 1 or tone > 5:
        return syl
    if tone == 5:
        return syl   # neutral tone — bare syllable

    # Pinyin orthography for tone placement:
    #   - If 'a' or 'e' is present, mark it.
    #   - Else if the diphthong 'ou' is present, mark the 'o'.
    #   - Else mark the LAST vowel in the syllable.
    idx = None
    if 'a' in syl:
        idx = syl.index('a')
    elif 'e' in syl:
        idx = syl.index('e')
    elif 'ou' in syl:
        idx = syl.index('ou')
    else:
        last = -1
        for i, ch in enumerate(syl):
            if ch in 'iouü':
                last = i
        if last >= 0:
            idx = last

    if idx is None:
        return syl
    vowel = syl[idx]
    if vowel not in TONE_MARKS:
        return syl
    marked = TONE_MARKS[vowel][tone]
    return syl[:idx] + marked + syl[idx + 1:]


# ============================================================================
# TRAD -> SIMP
# ============================================================================
def to_simp(text: str) -> str:
    if not text:
        return text
    return zhconv.convert(text, 'zh-cn')


# ============================================================================
# CLEANUP STEPS
# ============================================================================

def _fetch_all(db, table, columns, language_id=None, chunk=1000):
    """Paginated read of a table; returns a list of rows."""
    rows = []
    offset = 0
    while True:
        q = db.table(table).select(columns)
        if language_id is not None:
            q = q.eq('language_id', language_id)
        resp = q.range(offset, offset + chunk - 1).execute()
        batch = resp.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < chunk:
            break
        offset += chunk
    return rows


def fix_classifiers(db, dry_run: bool) -> int:
    """Convert hanzi to simplified and rebuild pinyin_display."""
    rows = _fetch_all(db, 'dim_classifiers',
                      'id, hanzi, pinyin, pinyin_display, distractor_group_id, '
                      'difficulty_tier, example_nouns, semantic_label, frequency_rank',
                      LANGUAGE_ID_ZH)
    logger.info(f"dim_classifiers: {len(rows)} rows to inspect")

    updates = 0
    merges = 0

    # Build hanzi -> id map BEFORE renames so we can detect collisions.
    by_hanzi = {r['hanzi']: r for r in rows}

    for r in rows:
        new_hanzi  = to_simp(r['hanzi'])
        new_pin    = to_diacritic(r['pinyin'] or '')
        new_examples = [to_simp(x) for x in (r['example_nouns'] or [])]

        hanzi_changed   = new_hanzi != r['hanzi']
        pin_changed     = new_pin   != r['pinyin_display']
        examples_changed = new_examples != (r['example_nouns'] or [])

        if not (hanzi_changed or pin_changed or examples_changed):
            continue

        if hanzi_changed:
            # If the simplified form already exists in dim_classifiers as a
            # DIFFERENT row, we need to merge: redirect this row's pairs to
            # the existing row and delete this row.
            existing = by_hanzi.get(new_hanzi)
            if existing and existing['id'] != r['id']:
                logger.info(f"  MERGE {r['hanzi']}(id={r['id']}) -> {new_hanzi}(id={existing['id']})")
                if not dry_run:
                    _merge_classifier(db, r['id'], existing['id'])
                merges += 1
                continue

        patch = {}
        if hanzi_changed:    patch['hanzi'] = new_hanzi
        if pin_changed:      patch['pinyin_display'] = new_pin
        if examples_changed: patch['example_nouns']  = new_examples

        logger.info(f"  UPDATE id={r['id']}: {patch}")
        if not dry_run:
            db.table('dim_classifiers').update(patch).eq('id', r['id']).execute()
        if hanzi_changed:
            # Update local index so subsequent rows in this pass see the
            # post-rename state.
            by_hanzi.pop(r['hanzi'], None)
            by_hanzi[new_hanzi] = {**r, **patch}
        updates += 1

    logger.info(f"dim_classifiers: {updates} row updates, {merges} merges into existing simplified rows")
    return updates + merges


def _merge_classifier(db, src_id, dst_id):
    """Move all noun pairs from src classifier to dst; delete src."""
    # Insert pairs that don't already exist under dst
    src_pairs = (
        db.table('dim_classifier_noun_pairs')
          .select('id, lemma_text, classifier_id, is_primary, frequency_score, source, noun_sense_id, language_id')
          .eq('classifier_id', src_id)
          .execute()
    ).data or []

    dst_existing = {
        r['lemma_text'] for r in (
            db.table('dim_classifier_noun_pairs')
              .select('lemma_text')
              .eq('classifier_id', dst_id)
              .execute()
        ).data or []
    }
    for p in src_pairs:
        if p['lemma_text'] in dst_existing:
            continue
        new_row = {k: p[k] for k in ('language_id','noun_sense_id','lemma_text','is_primary','frequency_score','source')}
        new_row['classifier_id'] = dst_id
        db.table('dim_classifier_noun_pairs').insert(new_row).execute()
        dst_existing.add(p['lemma_text'])

    # Examples table
    db.table('dim_classifier_example_sentences') \
      .update({'classifier_id': dst_id}) \
      .eq('classifier_id', src_id) \
      .execute()

    db.table('dim_classifier_noun_pairs').delete().eq('classifier_id', src_id).execute()
    db.table('dim_classifiers').delete().eq('id', src_id).execute()


def fix_noun_pairs(db, dry_run: bool) -> int:
    """Convert lemma_text to simplified across dim_classifier_noun_pairs."""
    rows = _fetch_all(db, 'dim_classifier_noun_pairs', 'id, lemma_text, classifier_id', LANGUAGE_ID_ZH)
    logger.info(f"dim_classifier_noun_pairs: {len(rows)} rows to inspect")

    # Group by (classifier_id, lemma_text) to detect duplicates post-conversion.
    target_keys = set()  # (classifier_id, new_lemma)
    plans = []  # (row_id, classifier_id, old_lemma, new_lemma)
    for r in rows:
        new_lemma = to_simp(r['lemma_text'])
        if new_lemma == r['lemma_text']:
            target_keys.add((r['classifier_id'], r['lemma_text']))
            continue
        plans.append((r['id'], r['classifier_id'], r['lemma_text'], new_lemma))

    updates = 0
    deletes = 0
    for row_id, cid, old, new in plans:
        key = (cid, new)
        if key in target_keys:
            logger.info(f"  DELETE duplicate after trad->simp: id={row_id} ({old} -> {new}) for classifier {cid}")
            if not dry_run:
                db.table('dim_classifier_noun_pairs').delete().eq('id', row_id).execute()
            deletes += 1
        else:
            logger.info(f"  UPDATE id={row_id}: lemma_text {old!r} -> {new!r}")
            if not dry_run:
                db.table('dim_classifier_noun_pairs').update({'lemma_text': new}).eq('id', row_id).execute()
            target_keys.add(key)
            updates += 1

    logger.info(f"dim_classifier_noun_pairs: {updates} updates, {deletes} duplicate deletes")
    return updates + deletes


def fix_example_sentences(db, dry_run: bool) -> int:
    """Convert sentence / blanked_sentence / noun_lemma to simplified."""
    rows = _fetch_all(db, 'dim_classifier_example_sentences',
                      'id, sentence, blanked_sentence, noun_lemma', LANGUAGE_ID_ZH)
    logger.info(f"dim_classifier_example_sentences: {len(rows)} rows to inspect")

    updates = 0
    for r in rows:
        new_sentence = to_simp(r['sentence'] or '')
        new_blanked  = to_simp(r['blanked_sentence'] or '')
        new_lemma    = to_simp(r['noun_lemma'] or '')
        if new_sentence == r['sentence'] and new_blanked == r['blanked_sentence'] and new_lemma == r['noun_lemma']:
            continue
        patch = {}
        if new_sentence != r['sentence']:     patch['sentence'] = new_sentence
        if new_blanked  != r['blanked_sentence']: patch['blanked_sentence'] = new_blanked
        if new_lemma    != r['noun_lemma']:   patch['noun_lemma'] = new_lemma
        logger.info(f"  UPDATE example id={r['id']}: {patch}")
        if not dry_run:
            db.table('dim_classifier_example_sentences').update(patch).eq('id', r['id']).execute()
        updates += 1

    logger.info(f"dim_classifier_example_sentences: {updates} row updates")
    return updates


def main(dry_run: bool):
    db = get_supabase_admin()
    logger.info("=" * 60)
    logger.info("Classifier data cleanup" + ("  (DRY-RUN)" if dry_run else ""))
    logger.info("=" * 60)

    fix_classifiers(db, dry_run)
    fix_noun_pairs(db, dry_run)
    fix_example_sentences(db, dry_run)

    logger.info("Done.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    args = parser.parse_args()
    main(dry_run=args.dry_run)
