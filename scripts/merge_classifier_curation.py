#!/usr/bin/env python3
"""
Classifier Curation Merger (offline)

Consolidates the per-classifier review JSON written by
generate_classifier_curation.py into a single approved_curation.json that
build_classifier_dictionary.py loads and merges into its curated dictionary.

Policy (per design decision):
  * Classifiers ALREADY in the curated CLASSIFIERS list keep their hand-set
    group / tier / label — only their accepted nouns are folded in.
  * Classifiers NOT yet curated (promoted / new measure words) contribute a
    full classifier meta block (group / tier / label from the LLM classify
    step) AND their nouns. These are the rows a human should eyeball in
    approved_curation.json before the rebuild, since the group/tier came from
    the model.

Only nouns with "accepted": true (judge rating >= threshold) are merged.

Usage:
    python scripts/merge_classifier_curation.py            # merge all *.json
    python scripts/merge_classifier_curation.py --dry-run  # report only
"""

import os
import sys
import json
import glob
import argparse
import logging
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.classifier_curation.config import OUTPUT_DIR, APPROVED_FILE
from scripts.build_classifier_dictionary import CLASSIFIERS, NOUN_CLASSIFIERS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def merge(dry_run: bool = False) -> dict:
    existing_hanzi = {row[0] for row in CLASSIFIERS}  # hanzi is tuple index 0

    files = sorted(
        f for f in glob.glob(os.path.join(OUTPUT_DIR, '*.json'))
        if os.path.basename(f) != os.path.basename(APPROVED_FILE)
    )
    logger.info("Merging %d review file(s) from %s", len(files), OUTPUT_DIR)

    classifiers_out: list[dict] = []
    seen_new: set[str] = set()
    noun_ratings: dict[str, list[tuple[str, int]]] = defaultdict(list)

    for path in files:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        cb = data.get('classifier', {})
        hanzi = cb.get('hanzi')
        if not hanzi:
            logger.warning("skipping %s: no classifier hanzi", path)
            continue

        accepted = [n for n in data.get('nouns', []) if n.get('accepted')]
        if not accepted:
            logger.warning("%s: no accepted nouns", hanzi)

        # Promoted/new classifier → contribute a meta block (group/tier from LLM).
        if hanzi not in existing_hanzi and hanzi not in seen_new:
            if cb.get('group') and cb.get('difficulty_tier'):
                seen_new.add(hanzi)
                classifiers_out.append({
                    'hanzi': hanzi,
                    'pinyin': cb.get('pinyin', ''),
                    'pinyin_display': (cb.get('pinyin_display') or cb.get('pinyin', '')).replace(' ', ''),
                    'group': cb['group'],
                    'semantic_label': cb.get('semantic_label', ''),
                    'example_nouns': [n['noun'] for n in accepted[:3]],
                    'difficulty_tier': int(cb['difficulty_tier']),
                })
            else:
                logger.warning("%s: new classifier missing group/tier; run with --classify", hanzi)

        for n in accepted:
            noun_ratings[n['noun']].append((hanzi, int(n.get('judge_rating', 0))))

    # noun -> classifiers ordered by judge rating (best first = primary candidate)
    noun_classifiers: dict[str, list[str]] = {}
    for noun, pairs in noun_ratings.items():
        ordered = [h for h, _ in sorted(pairs, key=lambda x: -x[1])]
        # dedupe preserving order
        seen: set[str] = set()
        noun_classifiers[noun] = [h for h in ordered if not (h in seen or seen.add(h))]

    out = {'classifiers': classifiers_out, 'noun_classifiers': noun_classifiers}

    logger.info(
        "Merged: %d new classifier(s), %d noun(s) (%d already in curated NOUN_CLASSIFIERS)",
        len(classifiers_out), len(noun_classifiers),
        sum(1 for n in noun_classifiers if n in NOUN_CLASSIFIERS),
    )

    if dry_run:
        logger.info("Dry-run; not writing %s", APPROVED_FILE)
        return out

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(APPROVED_FILE, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    logger.info("Wrote %s", APPROVED_FILE)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Consolidate classifier curation review JSON")
    parser.add_argument('--dry-run', action='store_true', help='Report only, do not write')
    args = parser.parse_args()
    merge(dry_run=args.dry_run)
