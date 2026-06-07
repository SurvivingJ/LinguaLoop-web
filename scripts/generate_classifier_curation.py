#!/usr/bin/env python3
"""
Classifier Curation Generator (offline, LLM-assisted)

For each target measure word, asks qwen (via OpenRouter) for common nouns that
idiomatically take it + an example phrase, judges each pairing, filters, and
writes a per-classifier JSON file to data/classifier_curation/<hanzi>.json for
HUMAN REVIEW. It never touches the DB or the curated dictionary directly — the
review + merge step does that.

Targets come from one of:
  --classifiers 束,锅,群        explicit list
  --underserved N               every classifier with < N distinct nouns (DB)
  --smoke                       a single quick classifier (束) for a smoke test

Flags:
  --classify                    also run the classify step (group/tier/label),
                                e.g. for measure words being promoted out of
                                'general'. Result stored in the JSON's
                                "classifier" block for review.
  --count N                     nouns to request per classifier (default config)
  --limit N                     cap number of classifiers processed

Usage:
    python scripts/generate_classifier_curation.py --smoke
    python scripts/generate_classifier_curation.py --underserved 10 --classify
    python scripts/generate_classifier_curation.py --classifiers 束,锅,串 --count 16
"""

import os
import re
import sys
import json
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

from services.classifier_curation.config import (
    LANGUAGE_ID_ZH, OUTPUT_DIR, TARGET_NOUNS, JUDGE_ACCEPT_THRESHOLD,
)
from services.classifier_curation.generator import classify_classifier, generate_nouns
from services.classifier_curation.judge import judge_nouns

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_HANZI_RE = re.compile(r'^[一-鿿]{1,6}$')
GE = '个'


def _fetch_underserved(db, threshold: int) -> list[tuple[str, str]]:
    """Return (hanzi, semantic_label) for classifiers with < threshold nouns."""
    cls = (
        db.table('dim_classifiers')
          .select('id, hanzi, semantic_label')
          .eq('language_id', LANGUAGE_ID_ZH)
          .execute()
    ).data or []
    # Count distinct nouns per classifier_id via paginated pair scan.
    counts: dict[int, set] = {}
    offset = 0
    while True:
        chunk = (
            db.table('dim_classifier_noun_pairs')
              .select('lemma_text, classifier_id')
              .eq('language_id', LANGUAGE_ID_ZH)
              .range(offset, offset + 999)
              .execute()
        ).data or []
        if not chunk:
            break
        for r in chunk:
            counts.setdefault(r['classifier_id'], set()).add(r['lemma_text'])
        if len(chunk) < 1000:
            break
        offset += 1000
    out = []
    for c in cls:
        if c['hanzi'] == GE:
            continue
        n = len(counts.get(c['id'], set()))
        if n < threshold:
            out.append((c['hanzi'], c.get('semantic_label') or ''))
    return out


def _existing_vocab(db, nouns: list[str]) -> set[str]:
    """Return the subset of nouns present in dim_vocabulary (lang zh)."""
    found: set[str] = set()
    for i in range(0, len(nouns), 200):
        batch = nouns[i:i + 200]
        rows = (
            db.table('dim_vocabulary')
              .select('lemma')
              .eq('language_id', LANGUAGE_ID_ZH)
              .in_('lemma', batch)
              .execute()
        ).data or []
        found.update(r['lemma'] for r in rows)
    return found


def process_classifier(db, hanzi: str, semantic_label: str,
                       do_classify: bool, count: int) -> dict:
    """Generate + judge + filter nouns for one classifier; return a review dict."""
    classifier_block = {'hanzi': hanzi, 'semantic_label': semantic_label}
    if do_classify:
        try:
            meta = classify_classifier(hanzi, hint=semantic_label)
            classifier_block = meta.model_dump()
            semantic_label = meta.semantic_label or semantic_label
        except Exception as exc:
            logger.warning("classify failed for %s: %s", hanzi, exc)

    raw = generate_nouns(hanzi, semantic_label=semantic_label, n=count).nouns

    # Deterministic filters: valid Chinese, length, not 个, not the classifier,
    # dedup (first occurrence wins).
    seen: set[str] = set()
    candidates = []
    for ne in raw:
        noun = (ne.noun or '').strip()
        if not _HANZI_RE.match(noun) or noun in (GE, hanzi) or noun in seen:
            continue
        seen.add(noun)
        candidates.append(ne)

    ratings = judge_nouns(hanzi, [c.noun for c in candidates], semantic_label)
    vocab = _existing_vocab(db, [c.noun for c in candidates]) if candidates else set()

    nouns_out = []
    for ne, rating in zip(candidates, ratings):
        nouns_out.append({
            'noun': ne.noun,
            'pinyin': ne.pinyin,
            'gloss': ne.gloss,
            'example_sentence': ne.example_sentence,
            'ge_also_acceptable': ne.ge_also_acceptable,
            'judge_rating': rating,
            'accepted': rating >= JUDGE_ACCEPT_THRESHOLD,
            'in_vocab': ne.noun in vocab,
        })

    accepted = sum(1 for n in nouns_out if n['accepted'])
    logger.info("%s: %d generated -> %d candidates -> %d accepted (>=%d)",
                hanzi, len(raw), len(candidates), accepted, JUDGE_ACCEPT_THRESHOLD)
    return {'classifier': classifier_block, 'nouns': nouns_out}


def run(targets: list[tuple[str, str]], do_classify: bool, count: int, limit: int):
    db = get_supabase_admin()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if limit:
        targets = targets[:limit]
    logger.info("Processing %d classifier(s) -> %s", len(targets), OUTPUT_DIR)
    for hanzi, label in targets:
        try:
            result = process_classifier(db, hanzi, label, do_classify, count)
        except Exception as exc:
            logger.error("Failed on %s: %s", hanzi, exc)
            continue
        path = os.path.join(OUTPUT_DIR, f"{hanzi}.json")
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        logger.info("Wrote %s", path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="LLM-assisted classifier noun curation")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument('--classifiers', help='Comma-separated hanzi list')
    src.add_argument('--underserved', type=int, metavar='N',
                     help='Process every classifier with < N distinct nouns')
    src.add_argument('--smoke', action='store_true', help='Single-classifier smoke test (束)')
    parser.add_argument('--classify', action='store_true',
                        help='Also run the classify step (group/tier/label)')
    parser.add_argument('--count', type=int, default=TARGET_NOUNS,
                        help=f'Nouns to request per classifier (default {TARGET_NOUNS})')
    parser.add_argument('--limit', type=int, default=0, help='Cap classifiers processed')
    args = parser.parse_args()

    _db = get_supabase_admin()
    if args.smoke:
        _targets = [('束', 'bundles / bouquets / beams')]
    elif args.classifiers:
        _targets = [(h.strip(), '') for h in args.classifiers.split(',') if h.strip()]
    else:
        _targets = _fetch_underserved(_db, args.underserved)

    run(_targets, do_classify=args.classify, count=args.count, limit=args.limit)
