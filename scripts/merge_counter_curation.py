#!/usr/bin/env python3
"""
Counter Curation Merger (offline) — TASK-530.

Consolidates the per-counter review JSON written by generate_counter_curation.py
into a single approved_curation.json that build_counter_dictionary.py loads and
merges into its curated dictionary.

Policy (mirrors merge_classifier_curation.py):
  * Counters ALREADY in the curated COUNTERS list keep their hand-set
    group / tier / label / numeral readings — only their accepted nouns are
    folded in. The hand-written euphonic readings (一本 いっぽん) are the part a
    model is least reliable on, so they are never overwritten.
  * Counters NOT yet curated contribute a full meta block AND their nouns.
    These are the rows a human should eyeball, since the group/tier came from
    the model.

Only nouns with "accepted": true (judge rating >= threshold) are merged.
Counters the classify step marked not_a_counter or counts_no_nouns contribute
nothing and are reported, not silently dropped.

Usage:
    PYTHONPATH=. python scripts/merge_counter_curation.py            # merge all *.json
    PYTHONPATH=. python scripts/merge_counter_curation.py --dry-run  # report only
"""

import argparse
import glob
import json
import logging
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.counter_curation.config import APPROVED_FILE, OUTPUT_DIR
from scripts.build_counter_dictionary import COUNTERS, PAIRS, SECONDARY

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

#: Counters whose 2026-08-12 curated list is rejected at human sign-off.
#: Excluded from BOTH their own noun list and other counters' alternates — an
#: alternate pointing at a counter we refuse to teach is still a drill answer.
#:
#: The first five were rejected on the judge's own numbers: the model proposed
#: nouns and its judge then threw most of them out, which means the counter's
#: real coverage is too small to drill rather than that the pass went wrong.
#:
#: 列 is a different and more interesting case. It counts *rows* of things, so
#: "nouns that take 列" is really "nouns that can be arranged in a row" —
#: 車, 学生, 本, 花, 建物 all qualify, and none of them is *taught* with 列.
#: Same shape as 階 counting storeys: the counted thing is an arrangement, not
#: the noun. The classify step's counts_nouns gate caught 階 and six others but
#: not this one, and it was the single largest source of multi-acceptable pairs
#: (列+台, 列+両, 列+冊, 列+本, 列+棟 …), each of which would have made an
#: ordinary item accept two answers.
EXCLUDED_COUNTERS: dict[str, str] = {
    '筋': 'judge accepted 0/19 — nothing usable',
    '編': 'judge accepted 2/20 — incoherent list',
    '項': 'judge accepted 3/19 — incoherent list',
    '片': 'judge accepted 7/20 — incoherent list',
    '組': 'judge accepted 9/20 — incoherent list',
    '列': 'counts rows, not nouns — foil-only, same class as 階',
}


def _curated_nouns() -> set[str]:
    """Every noun the in-file curated tables already cover."""
    nouns = {noun for nouns_ in PAIRS.values() for noun in nouns_}
    nouns |= set(SECONDARY)
    return nouns


def merge(dry_run: bool = False) -> dict:
    existing_counters = {row[1] for row in COUNTERS}  # counter is tuple index 1
    already_curated = _curated_nouns()

    files = sorted(
        f for f in glob.glob(os.path.join(OUTPUT_DIR, '*.json'))
        if os.path.basename(f) != os.path.basename(APPROVED_FILE)
    )
    logger.info("Merging %d review file(s) from %s", len(files), OUTPUT_DIR)

    counters_out: list[dict] = []
    seen_new: set[str] = set()
    noun_ratings: dict[str, list[tuple[str, int]]] = defaultdict(list)
    declined: list[str] = []

    for path in files:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        block = data.get('counter', {})
        counter = block.get('counter')
        if not counter:
            logger.warning("skipping %s: no counter", path)
            continue

        reason = data.get('skipped_reason')
        if reason:
            declined.append(f"{counter} ({reason})")
            continue

        if counter in EXCLUDED_COUNTERS:
            declined.append(f"{counter} (sign-off: {EXCLUDED_COUNTERS[counter]})")
            continue

        accepted = [n for n in data.get('nouns', []) if n.get('accepted')]
        if not accepted:
            logger.warning("%s: no accepted nouns", counter)

        # New counter → contribute a meta block (group/tier from the LLM).
        if counter not in existing_counters and counter not in seen_new:
            if block.get('group') and block.get('difficulty_tier'):
                seen_new.add(counter)
                counters_out.append({
                    'counter': counter,
                    'reading': block.get('reading', ''),
                    'group': block['group'],
                    'semantic_label': block.get('semantic_label', ''),
                    'example_nouns': [n['noun'] for n in accepted[:5]],
                    'difficulty_tier': int(block['difficulty_tier']),
                })
            else:
                logger.warning("%s: new counter missing group/tier; run with --classify",
                               counter)

        for n in accepted:
            noun_ratings[n['noun']].append((counter, int(n.get('judge_rating', 0))))
            # An alternate the model flagged is only recorded when it is a
            # counter we actually know about — otherwise the pair insert would
            # reference a counter that does not exist. It is recorded at a lower
            # rating than the primary so ordering puts the primary first.
            for alt in n.get('also_acceptable_counters') or []:
                if alt in EXCLUDED_COUNTERS:
                    continue
                if alt in existing_counters or alt in seen_new:
                    noun_ratings[n['noun']].append((alt, 0))

    # noun -> counters ordered by judge rating (best first = primary candidate)
    noun_counters: dict[str, list[str]] = {}
    for noun, pairs in noun_ratings.items():
        ordered = [c for c, _ in sorted(pairs, key=lambda x: -x[1])]
        seen: set[str] = set()
        noun_counters[noun] = [c for c in ordered if not (c in seen or seen.add(c))]

    out = {'counters': counters_out, 'noun_counters': noun_counters}

    new_nouns = sum(1 for n in noun_counters if n not in already_curated)
    logger.info(
        "Merged: %d new counter(s), %d noun(s) (%d new, %d already curated)",
        len(counters_out), len(noun_counters), new_nouns,
        len(noun_counters) - new_nouns,
    )
    for item in declined:
        logger.info("declined by classify: %s", item)

    if dry_run:
        logger.info("Dry-run; not writing %s", APPROVED_FILE)
        return out

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(APPROVED_FILE, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    logger.info("Wrote %s", APPROVED_FILE)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Consolidate counter curation review JSON")
    parser.add_argument('--dry-run', action='store_true',
                        help='Report only, do not write')
    args = parser.parse_args()
    merge(dry_run=args.dry_run)
