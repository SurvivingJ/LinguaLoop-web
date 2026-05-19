#!/usr/bin/env python3
"""
Classifier Example Sentence Miner

Scans every Chinese tests.transcript for sentences containing a
[number][classifier][noun] pattern and inserts them into
dim_classifier_example_sentences. Used by the cloze-in-sentence trainer
level (level 4) so the user fills the blank with the correct classifier
in real-passage context.

The miner is conservative: only sentences <= 80 characters are kept (to
suit the SPA UI), and only matches against classifiers + nouns that
already exist in dim_classifier_noun_pairs (curated or cedict).

Usage:
    python scripts/mine_classifier_sentences.py [--dry-run]
"""

import os
import sys
import re
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LANGUAGE_ID_ZH = 1
MAX_SENTENCE_LEN = 80

# Splitter on Chinese sentence-ending punctuation.
SENT_SPLIT_RE = re.compile(r'[。！？!?]')

# Chinese numerals + measure modifiers that can precede a classifier.
# Includes 一-十, 百千, 这/那/几/多/某, and standard arabic digits.
NUMERAL_CLASS = '[一二三四五六七八九十百千两这那几多某半另每好0-9]'


def _load_classifier_pairs(db):
    """Return (classifier_by_id, lemmas_by_classifier_id, pair_index)."""
    cls = (
        db.table('dim_classifiers')
          .select('id, hanzi')
          .eq('language_id', LANGUAGE_ID_ZH)
          .execute()
    )
    cls_by_id = {r['id']: r['hanzi'] for r in cls.data or []}
    hanzi_to_id = {r['hanzi']: r['id'] for r in cls.data or []}

    # Pull all pairs paginated
    pair_index = {}      # noun_lemma -> set of classifier_id
    classifier_lemmas = {}  # classifier_id -> set of lemmas
    offset = 0
    while True:
        chunk = (
            db.table('dim_classifier_noun_pairs')
              .select('lemma_text, classifier_id')
              .eq('language_id', LANGUAGE_ID_ZH)
              .range(offset, offset + 999)
              .execute()
        )
        rows = chunk.data or []
        if not rows:
            break
        for r in rows:
            lemma = r['lemma_text']
            cid = r['classifier_id']
            pair_index.setdefault(lemma, set()).add(cid)
            classifier_lemmas.setdefault(cid, set()).add(lemma)
        if len(rows) < 1000:
            break
        offset += 1000
    return cls_by_id, hanzi_to_id, pair_index, classifier_lemmas


def _split_sentences(transcript):
    if not transcript:
        return []
    parts = SENT_SPLIT_RE.split(transcript)
    sentences = []
    for p in parts:
        p = p.strip()
        if 2 < len(p) <= MAX_SENTENCE_LEN:
            sentences.append(p)
    return sentences


def _scan_sentence(sentence, classifier_hanzi_set, hanzi_to_id, pair_index):
    """Yield (classifier_hanzi, classifier_id, noun_lemma, blanked_sentence)
    for each [numeral][classifier][noun] hit in this sentence.

    Looks 1-3 characters ahead of the classifier for a noun that has a
    known pair with this classifier.
    """
    out = []
    n = len(sentence)
    for i, ch in enumerate(sentence):
        if ch not in classifier_hanzi_set:
            continue
        # Numeral precedes the classifier?
        if i == 0:
            continue
        if not re.match(NUMERAL_CLASS, sentence[i - 1]):
            continue
        # Try noun candidates of length 1, 2, 3 following the classifier
        cid = hanzi_to_id.get(ch)
        if not cid:
            continue
        for noun_len in (3, 2, 1):
            if i + 1 + noun_len > n:
                continue
            candidate = sentence[i + 1:i + 1 + noun_len]
            # Require all hanzi
            if not all('一' <= c <= '鿿' for c in candidate):
                continue
            if cid in pair_index.get(candidate, set()):
                blanked = sentence[:i] + '___' + sentence[i + 1:]
                out.append((ch, cid, candidate, blanked))
                break  # Take the longest noun match; don't double-emit
    return out


def run(dry_run: bool = False):
    db = get_supabase_admin()

    cls_by_id, hanzi_to_id, pair_index, _ = _load_classifier_pairs(db)
    classifier_hanzi_set = set(hanzi_to_id.keys())
    logger.info(f"Loaded {len(classifier_hanzi_set)} classifiers, {len(pair_index)} unique noun lemmas")

    # Fetch Chinese test transcripts paginated
    tests_seen = 0
    sentences_seen = 0
    hits = []
    offset = 0
    while True:
        chunk = (
            db.table('tests')
              .select('id, transcript')
              .eq('language_id', LANGUAGE_ID_ZH)
              .eq('is_active', True)
              .not_.is_('transcript', 'null')
              .range(offset, offset + 99)
              .execute()
        )
        rows = chunk.data or []
        if not rows:
            break
        for t in rows:
            tests_seen += 1
            sentences = _split_sentences(t.get('transcript') or '')
            sentences_seen += len(sentences)
            for s in sentences:
                for cl_hanzi, cid, noun, blanked in _scan_sentence(
                    s, classifier_hanzi_set, hanzi_to_id, pair_index
                ):
                    hits.append({
                        'language_id':     LANGUAGE_ID_ZH,
                        'classifier_id':   cid,
                        'noun_lemma':      noun,
                        'sentence':        s,
                        'blanked_sentence': blanked,
                        'source_test_id':  t['id'],
                    })
        if len(rows) < 100:
            break
        offset += 100

    logger.info(f"Scanned {tests_seen} tests, {sentences_seen} sentences. Hits: {len(hits)}")

    if dry_run:
        for h in hits[:15]:
            logger.info(f"  {h['blanked_sentence']}    -- classifier={cls_by_id[h['classifier_id']]} noun={h['noun_lemma']}")
        logger.info("Dry-run; no rows written.")
        return

    if not hits:
        logger.info("Nothing to insert.")
        return

    # Wipe and rebuild (cheap)
    db.table('dim_classifier_example_sentences').delete().eq('language_id', LANGUAGE_ID_ZH).execute()

    # Dedupe in-memory (classifier_id, sentence) to honor UNIQUE constraint
    seen = set()
    deduped = []
    for h in hits:
        key = (h['classifier_id'], h['sentence'])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(h)

    for i in range(0, len(deduped), 500):
        chunk = deduped[i:i + 500]
        db.table('dim_classifier_example_sentences').insert(chunk).execute()
    logger.info(f"Inserted {len(deduped)} example sentences across {len(set(h['classifier_id'] for h in deduped))} classifiers")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Mine [num][classifier][noun] sentences from Chinese test transcripts")
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    args = parser.parse_args()
    run(dry_run=args.dry_run)
