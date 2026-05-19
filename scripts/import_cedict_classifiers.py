#!/usr/bin/env python3
"""
CC-CEDICT Classifier Importer

Downloads (if missing) and parses cedict_ts.u8, the public Mandarin-English
dictionary maintained by MDBG (CC-BY-SA 3.0), and inserts every
noun-classifier annotation as a row in dim_classifier_noun_pairs with
source='cedict'.

CC-CEDICT encodes classifiers inline in the gloss as:
    /CL:X[pin1]/    or    /CL:X[pin1],Y[pin2]/

We walk every entry that has at least one CL: tag, look up each classifier
in dim_classifiers (creating a Tier-4 'general' row if it's new), and
upsert a (lemma_text, classifier_id) pair.

The curated build script (build_classifier_dictionary.py) takes precedence:
this importer skips any (lemma, classifier) pair that already has a
source='curated' row.

Usage:
    python scripts/import_cedict_classifiers.py             # full import
    python scripts/import_cedict_classifiers.py --dry-run   # parse only
    python scripts/import_cedict_classifiers.py --limit 500 # first 500 hits
"""

import os
import sys
import re
import gzip
import urllib.request
import argparse
import logging
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LANGUAGE_ID_ZH = 1
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, 'raw')
CEDICT_PATH = os.path.join(RAW_DIR, 'cedict_ts.u8')
CEDICT_GZ_URL = 'https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz'


# A line in CC-CEDICT looks like:
#   simplified  traditional  [pin1 yin1]  /def1/def2/CL:X[pin],Y[pin]/
# where the simplified hanzi is the first token.
LINE_RE = re.compile(
    r'^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/\s*$'
)

# CL: tag — possibly multiple comma-separated classifiers.
CL_TAG_RE = re.compile(r'CL:([^/]+?)(?=/|$)')

# Each CL entry: traditional|simplified[pinyin] or traditional[pinyin].
# Group 1: traditional. Group 2: simplified (None when both forms identical).
# Group 3: pinyin.
CL_ENTRY_RE = re.compile(
    r'([一-鿿]+)(?:\|([一-鿿]+))?\[([^\]]+)\]'
)


def _ensure_cedict_file():
    """Download cedict_ts.u8 to raw/ if not present."""
    if os.path.exists(CEDICT_PATH):
        return
    os.makedirs(RAW_DIR, exist_ok=True)
    gz_path = CEDICT_PATH + '.gz'
    logger.info(f"Downloading CC-CEDICT from {CEDICT_GZ_URL}...")
    urllib.request.urlretrieve(CEDICT_GZ_URL, gz_path)
    logger.info(f"Decompressing to {CEDICT_PATH}")
    with gzip.open(gz_path, 'rb') as gz_in, open(CEDICT_PATH, 'wb') as out:
        out.write(gz_in.read())
    os.remove(gz_path)
    logger.info("CC-CEDICT ready.")


def parse_cedict():
    """Yield (simplified, traditional, pinyin, [(cl_hanzi, cl_pinyin), ...]).

    CC-CEDICT line format is: TRADITIONAL SIMPLIFIED [pinyin] /defs/
    Inside CL: tags, entries take the form  X|Y[pin]  where X is TRADITIONAL
    and Y is SIMPLIFIED, or just X[pin] when both forms are identical.
    We always prefer the simplified form for the trainer.
    """
    with open(CEDICT_PATH, 'r', encoding='utf-8') as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            m = LINE_RE.match(line)
            if not m:
                continue
            traditional, simplified, pinyin, defs = m.groups()
            cl_tags = CL_TAG_RE.findall(defs)
            if not cl_tags:
                continue
            classifiers = []
            for tag in cl_tags:
                for cl_match in CL_ENTRY_RE.finditer(tag):
                    trad_form = cl_match.group(1)
                    simp_form = cl_match.group(2) if cl_match.group(2) else trad_form
                    cl_pinyin = cl_match.group(3)
                    # Real classifiers are single characters. CC-CEDICT
                    # occasionally tags multi-char phrases (e.g.
                    # 三点钟 / 五分钟 / 香烟) — those aren't measure words
                    # the learner picks between, so skip them.
                    if len(simp_form) != 1:
                        continue
                    classifiers.append((simp_form, cl_pinyin))
            if classifiers:
                yield (simplified, traditional, pinyin, classifiers)


def _load_existing_state(db):
    """Return (classifier_by_hanzi, curated_pairs, all_pairs, fallback_group_id)."""
    grp = (
        db.table('dim_classifier_distractor_groups')
          .select('id, label')
          .eq('language_id', LANGUAGE_ID_ZH)
          .execute()
    )
    group_id_map = {r['label']: r['id'] for r in grp.data or []}
    fallback = group_id_map.get('general')
    if not fallback:
        raise RuntimeError("'general' group not found; run build_classifier_dictionary.py first")

    cls = (
        db.table('dim_classifiers')
          .select('id, hanzi, distractor_group_id, difficulty_tier')
          .eq('language_id', LANGUAGE_ID_ZH)
          .execute()
    )
    classifier_by_hanzi = {r['hanzi']: r for r in cls.data or []}

    # Pull existing pairs in chunks (range pagination)
    curated, cedict, both = set(), set(), set()
    offset = 0
    while True:
        chunk = (
            db.table('dim_classifier_noun_pairs')
              .select('lemma_text, classifier_id, source')
              .eq('language_id', LANGUAGE_ID_ZH)
              .range(offset, offset + 999)
              .execute()
        )
        rows = chunk.data or []
        if not rows:
            break
        for r in rows:
            key = (r['lemma_text'], r['classifier_id'])
            both.add(key)
            if r['source'] == 'curated':
                curated.add(key)
            elif r['source'] == 'cedict':
                cedict.add(key)
        if len(rows) < 1000:
            break
        offset += 1000

    return classifier_by_hanzi, curated, both, fallback


def _create_new_classifier(db, hanzi, pinyin_raw, fallback_group_id, frequency_rank):
    """Insert a CC-CEDICT-only classifier as Tier 4, general group."""
    # Normalize CC-CEDICT pinyin (numeric tones, no diacritics) to lowercase.
    pinyin = pinyin_raw.strip().lower().replace(' ', '')
    # pinyin_display: keep numeric form; we don't auto-add diacritics for these
    # rare/long-tail classifiers. Curated classifiers carry proper diacritics.
    resp = (
        db.table('dim_classifiers')
          .insert({
              'language_id': LANGUAGE_ID_ZH,
              'hanzi': hanzi,
              'pinyin': pinyin,
              'pinyin_display': pinyin,
              'semantic_label': '(imported)',
              'example_nouns': [],
              'frequency_rank': frequency_rank,
              'distractor_group_id': fallback_group_id,
              'difficulty_tier': 4,
          })
          .execute()
    )
    return resp.data[0] if resp.data else None


def run(dry_run: bool = False, limit: int = 0):
    _ensure_cedict_file()
    db = get_supabase_admin()

    classifier_by_hanzi, curated_keys, existing_keys, fallback_group_id = _load_existing_state(db)
    logger.info(
        f"Loaded {len(classifier_by_hanzi)} existing classifiers, "
        f"{len(curated_keys)} curated pairs, {len(existing_keys)} total pairs"
    )

    # First pass: count CL: tag occurrences per classifier hanzi to feed
    # frequency_rank for any new classifiers.
    classifier_counts = defaultdict(int)
    for simplified, _, _, classifiers in parse_cedict():
        for cl_hanzi, _ in classifiers:
            classifier_counts[cl_hanzi] += 1

    # Backfill frequency_rank starting after the highest existing rank
    max_existing_rank = max(
        (c.get('frequency_rank') or 0 for c in classifier_by_hanzi.values()),
        default=0,
    )

    new_classifiers_created = 0
    pairs_to_insert = []
    skipped_curated = 0
    skipped_existing = 0
    total_parsed = 0

    # Sort new classifiers by descending CC-CEDICT frequency so the highest-
    # frequency newcomers get the lowest frequency_rank (after existing core).
    seen_new = set()
    for cl_hanzi, _ in sorted(
        ((h, classifier_counts[h]) for h in classifier_counts),
        key=lambda x: -x[1],
    ):
        if cl_hanzi in classifier_by_hanzi or cl_hanzi in seen_new:
            continue
        seen_new.add(cl_hanzi)

    # Second pass: build pair rows.
    for simplified, _, _, classifiers in parse_cedict():
        # Skip entries that are themselves single CJK characters that look
        # like proper nouns or have non-noun glosses. CC-CEDICT only marks
        # CL: on nouns, so the presence of CL: itself is the noun signal.
        if not simplified or len(simplified) > 6:
            continue

        for cl_hanzi, cl_pinyin in classifiers:
            total_parsed += 1

            # Lazily create unknown classifiers (Tier 4, general group)
            if cl_hanzi not in classifier_by_hanzi:
                if dry_run:
                    classifier_by_hanzi[cl_hanzi] = {'id': -1, 'hanzi': cl_hanzi}
                else:
                    max_existing_rank += 1
                    created = _create_new_classifier(
                        db, cl_hanzi, cl_pinyin, fallback_group_id, max_existing_rank
                    )
                    if not created:
                        continue
                    classifier_by_hanzi[cl_hanzi] = created
                    new_classifiers_created += 1

            cls_id = classifier_by_hanzi[cl_hanzi]['id']
            key = (simplified, cls_id)
            if key in curated_keys:
                skipped_curated += 1
                continue
            if key in existing_keys:
                skipped_existing += 1
                continue

            pairs_to_insert.append({
                'language_id':     LANGUAGE_ID_ZH,
                'noun_sense_id':   None,
                'lemma_text':      simplified,
                'classifier_id':   cls_id,
                'is_primary':      True,  # CC-CEDICT lists in order of frequency
                'frequency_score': 1.0,
                'source':          'cedict',
            })
            existing_keys.add(key)  # avoid duplicates in this batch

            if limit and len(pairs_to_insert) >= limit:
                break
        if limit and len(pairs_to_insert) >= limit:
            break

    logger.info(
        f"Parsed: {total_parsed} CL: occurrences | new classifiers: {new_classifiers_created} | "
        f"new pairs: {len(pairs_to_insert)} | skipped (curated): {skipped_curated} | "
        f"skipped (already-imported): {skipped_existing}"
    )

    if dry_run:
        for p in pairs_to_insert[:10]:
            logger.info(f"  preview: {p}")
        logger.info("Dry-run complete; no rows written")
        return

    if not pairs_to_insert:
        logger.info("Nothing to insert.")
        return

    # Insert in 500-row chunks
    for i in range(0, len(pairs_to_insert), 500):
        chunk = pairs_to_insert[i:i + 500]
        db.table('dim_classifier_noun_pairs').insert(chunk).execute()
    logger.info(f"Inserted {len(pairs_to_insert)} new noun-classifier pairs from CC-CEDICT")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Import CC-CEDICT classifier annotations")
    parser.add_argument('--dry-run', action='store_true', help='Parse only, no DB writes')
    parser.add_argument('--limit', type=int, default=0, help='Cap inserts (0 = unlimited)')
    args = parser.parse_args()
    run(dry_run=args.dry_run, limit=args.limit)
