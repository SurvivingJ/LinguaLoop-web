#!/usr/bin/env python3
"""
Counter Curation Generator (offline, LLM-assisted) — TASK-530.

The Japanese sibling of generate_classifier_curation.py. For each target
counter, asks qwen (via OpenRouter) for common nouns that idiomatically take it
+ an example phrase, judges each pairing, filters, and writes a per-counter JSON
file to data/counter_curation/<counter>.json for HUMAN REVIEW. It never touches
the DB or the curated dictionary directly — the review + merge step does that.

Targets come from one of:
  --counters 皿,枚,冊          explicit list
  --underserved N              every counter with < N distinct nouns (DB)
  --smoke                      a single quick counter (皿) for a smoke test

Flags:
  --classify                   also run the classify step (group/tier/label +
                               the is_real_counter / counts_nouns gates)
  --count N                    nouns to request per counter (default config)
  --limit N                    cap number of counters processed
  --ceiling USD                abort before the next counter once spend since
                               the run started exceeds this
  --report                     print the sign-off report over existing JSON and
                               exit without calling any model

Usage:
    PYTHONPATH=. python scripts/generate_counter_curation.py --smoke
    PYTHONPATH=. python scripts/generate_counter_curation.py --underserved 10 --classify --ceiling 5.00
    PYTHONPATH=. python scripts/generate_counter_curation.py --report
"""

import argparse
import glob
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

from services.counter_curation.config import (
    APPROVED_FILE, JUDGE_ACCEPT_THRESHOLD, LANGUAGE_ID_JA, OUTPUT_DIR,
    TARGET_NOUNS,
)
from services.counter_curation.generator import classify_counter, generate_nouns
from services.counter_curation.judge import judge_nouns

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Kanji, hiragana, katakana, the long vowel mark, and the ヶ in 一ヶ月.
_JA_RE = re.compile(r'^[一-鿿぀-ゟ゠-ヿーヶ]{1,8}$')

# Universal counters. A noun whose only counter is one of these teaches nothing
# in a counter drill, and using them as foils produces items with more than one
# defensible answer.
UNIVERSAL = {'つ', '個'}

# Below this share of nouns surviving the judge, the counter's list is more
# likely incoherent than merely strict — surfaced in the sign-off report.
_INCOHERENT_ACCEPT_RATE = 0.5


def _fetch_underserved(db, threshold: int) -> list[tuple[str, str]]:
    """Return (counter, semantic_label) for counters with < threshold nouns."""
    counters = (
        db.table('dim_counters')
          .select('id, counter, semantic_label')
          .eq('language_id', LANGUAGE_ID_JA)
          .execute()
    ).data or []

    counts: dict[int, set] = {}
    offset = 0
    while True:
        chunk = (
            db.table('dim_counter_noun_pairs')
              .select('lemma_text, counter_id')
              .eq('language_id', LANGUAGE_ID_JA)
              .range(offset, offset + 999)
              .execute()
        ).data or []
        if not chunk:
            break
        for row in chunk:
            counts.setdefault(row['counter_id'], set()).add(row['lemma_text'])
        if len(chunk) < 1000:
            break
        offset += 1000

    out = []
    for c in counters:
        if c['counter'] in UNIVERSAL:
            continue
        if len(counts.get(c['id'], set())) < threshold:
            out.append((c['counter'], c.get('semantic_label') or ''))
    return out


def _existing_vocab(db, nouns: list[str]) -> set[str]:
    """Return the subset of nouns present in dim_vocabulary (lang ja)."""
    found: set[str] = set()
    for i in range(0, len(nouns), 200):
        batch = nouns[i:i + 200]
        rows = (
            db.table('dim_vocabulary')
              .select('lemma')
              .eq('language_id', LANGUAGE_ID_JA)
              .in_('lemma', batch)
              .execute()
        ).data or []
        found.update(r['lemma'] for r in rows)
    return found


def _spend_since(db, since_iso: str) -> float:
    """Actual USD spent since a timestamp, from llm_calls.cost_usd."""
    try:
        rows = (
            db.table('llm_calls')
              .select('cost_usd')
              .gte('created_at', since_iso)
              .not_.is_('cost_usd', 'null')
              .execute()
        ).data or []
        return round(sum(float(r['cost_usd'] or 0) for r in rows), 4)
    except Exception as exc:
        logger.warning("cost query failed: %s", exc)
        return 0.0


def process_counter(db, counter: str, semantic_label: str,
                    do_classify: bool, count: int) -> dict:
    """Generate + judge + filter nouns for one counter; return a review dict."""
    counter_block = {'counter': counter, 'semantic_label': semantic_label}

    if do_classify:
        try:
            meta = classify_counter(counter, hint=semantic_label)
            counter_block = meta.model_dump()
            semantic_label = meta.semantic_label or semantic_label

            # Both gates end the counter here rather than generating a list.
            # A counter that counts no noun is a legitimate outcome; inventing
            # nouns for it is the specific defect this exists to prevent.
            if not meta.is_real_counter:
                logger.warning("%s: model says this is not a real counter", counter)
                return {'counter': counter_block, 'nouns': [],
                        'skipped_reason': 'not_a_counter'}
            if not meta.counts_nouns:
                logger.info("%s: counts no showable noun (%s) — no list requested",
                            counter, meta.semantic_label)
                return {'counter': counter_block, 'nouns': [],
                        'skipped_reason': 'counts_no_nouns'}
        except Exception as exc:
            logger.warning("classify failed for %s: %s", counter, exc)

    raw = generate_nouns(counter, semantic_label=semantic_label, n=count).nouns

    # Deterministic filters: valid Japanese, length, not universal, not the
    # counter itself, dedup (first occurrence wins).
    seen: set[str] = set()
    candidates = []
    for entry in raw:
        noun = (entry.noun or '').strip()
        if not _JA_RE.match(noun) or noun in UNIVERSAL or noun == counter:
            continue
        if noun in seen:
            continue
        seen.add(noun)
        candidates.append(entry)

    ratings = judge_nouns(counter, [c.noun for c in candidates], semantic_label)
    vocab = _existing_vocab(db, [c.noun for c in candidates]) if candidates else set()

    nouns_out = []
    for entry, rating in zip(candidates, ratings):
        alternates = [a for a in (entry.also_acceptable_counters or [])
                      if a and a != counter and a not in UNIVERSAL]
        nouns_out.append({
            'noun': entry.noun,
            'reading': entry.reading,
            'gloss': entry.gloss,
            'example_phrase': entry.example_phrase,
            'also_acceptable_counters': alternates,
            'judge_rating': rating,
            'accepted': rating >= JUDGE_ACCEPT_THRESHOLD,
            'in_vocab': entry.noun in vocab,
        })

    accepted = sum(1 for n in nouns_out if n['accepted'])
    logger.info("%s: %d generated -> %d candidates -> %d accepted (>=%d)",
                counter, len(raw), len(candidates), accepted,
                JUDGE_ACCEPT_THRESHOLD)
    return {'counter': counter_block, 'nouns': nouns_out}


def run(targets, do_classify: bool, count: int, limit: int,
        ceiling: float | None) -> None:
    db = get_supabase_admin()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if limit:
        targets = targets[:limit]
    started = datetime.now(timezone.utc).isoformat()
    logger.info("Processing %d counter(s) -> %s", len(targets), OUTPUT_DIR)

    for index, (counter, label) in enumerate(targets):
        # Checked before each counter rather than after, so the ceiling stops
        # the next spend instead of reporting an overrun already incurred.
        if ceiling and index:
            spent = _spend_since(db, started)
            if spent >= ceiling:
                logger.error(
                    "ABORT: spent $%.4f of the $%.2f ceiling after %d counter(s); "
                    "stopping before %s", spent, ceiling, index, counter)
                break

        try:
            result = process_counter(db, counter, label, do_classify, count)
        except Exception as exc:
            logger.error("Failed on %s: %s", counter, exc)
            continue

        path = os.path.join(OUTPUT_DIR, f"{counter}.json")
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        logger.info("Wrote %s", path)

    logger.info("run spend: $%.4f", _spend_since(db, started))


# ---------------------------------------------------------------------------
# Sign-off report
# ---------------------------------------------------------------------------

def report() -> dict:
    """Summarise the review JSON for human sign-off.

    Deliberately a summary and not a dump. The reviewer needs the cases where
    the pipeline is least trustworthy — borderline ratings, incoherent lists,
    multi-acceptable nouns — not 500 rows of 皿/カレー that nobody will read
    carefully by row 40.
    """
    files = sorted(
        f for f in glob.glob(os.path.join(OUTPUT_DIR, '*.json'))
        if os.path.basename(f) != os.path.basename(APPROVED_FILE)
    )

    summary = {
        'files': len(files),
        'counters_with_nouns': 0,
        'total_rows': 0,
        'accepted_rows': 0,
        'not_a_counter': [],
        'counts_no_nouns': [],
        'below_ten_accepted': [],
        'incoherent': [],
        'uncertain': [],
        'multi_acceptable': [],
        'not_in_vocab': 0,
    }

    for path in files:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        block = data.get('counter', {})
        counter = block.get('counter') or os.path.basename(path)[:-5]
        nouns = data.get('nouns', [])
        reason = data.get('skipped_reason')

        if reason == 'not_a_counter':
            summary['not_a_counter'].append(counter)
            continue
        if reason == 'counts_no_nouns':
            summary['counts_no_nouns'].append(
                f"{counter} ({block.get('semantic_label', '')})")
            continue

        accepted = [n for n in nouns if n.get('accepted')]
        summary['counters_with_nouns'] += 1
        summary['total_rows'] += len(nouns)
        summary['accepted_rows'] += len(accepted)
        summary['not_in_vocab'] += sum(1 for n in accepted if not n.get('in_vocab'))

        if len(accepted) < 10:
            summary['below_ten_accepted'].append(f"{counter}={len(accepted)}")

        rate = len(accepted) / len(nouns) if nouns else 0.0
        if nouns and rate < _INCOHERENT_ACCEPT_RATE:
            summary['incoherent'].append(
                f"{counter}: only {len(accepted)}/{len(nouns)} survived the judge")

        # Rating 3 is the model saying "marginal" — the band where a human
        # actually changes the outcome.
        for n in nouns:
            if n.get('judge_rating') == 3:
                summary['uncertain'].append(f"{counter}/{n['noun']}")
            for alt in n.get('also_acceptable_counters') or []:
                summary['multi_acceptable'].append(f"{n['noun']}: {counter} + {alt}")

    return summary


def print_report(summary: dict) -> None:
    print('=' * 68)
    print('COUNTER CURATION — SIGN-OFF REPORT')
    print('=' * 68)
    print(f"review files:            {summary['files']}")
    print(f"counters with noun lists {summary['counters_with_nouns']}")
    print(f"rows generated:          {summary['total_rows']}")
    print(f"rows accepted (>=4):     {summary['accepted_rows']}")
    print(f"accepted not in vocab:   {summary['not_in_vocab']}")
    print()

    def _section(title: str, items: list, note: str = '') -> None:
        print(f"{title} ({len(items)})" + (f" — {note}" if note else ''))
        if not items:
            print('  none')
        for item in items:
            print(f"  - {item}")
        print()

    _section('NOT A REAL COUNTER', summary['not_a_counter'],
             'drop these from the dictionary')
    _section('COUNTS NO SHOWABLE NOUN', summary['counts_no_nouns'],
             'keep as foils, expect no nouns')
    _section('SEMANTICALLY INCOHERENT LISTS', summary['incoherent'],
             'judge rejected most of the list')
    _section('BELOW THE 10-NOUN BAR', summary['below_ten_accepted'])
    _section('MODEL UNCERTAIN (rating 3)', summary['uncertain'])
    _section('MULTI-ACCEPTABLE COUNTERS', summary['multi_acceptable'],
             'each must be merged as a secondary pair or the drill marks a '
             'correct answer wrong')
    print('=' * 68)
    print('Nothing has been merged. Run merge_counter_curation.py after sign-off.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="LLM-assisted Japanese counter noun curation")
    src = parser.add_mutually_exclusive_group()
    src.add_argument('--counters', help='Comma-separated counter list')
    src.add_argument('--underserved', type=int, metavar='N',
                     help='Process every counter with < N distinct nouns')
    src.add_argument('--smoke', action='store_true',
                     help='Single-counter smoke test (皿)')
    parser.add_argument('--classify', action='store_true',
                        help='Also run the classify step (group/tier/label)')
    parser.add_argument('--count', type=int, default=TARGET_NOUNS,
                        help=f'Nouns to request per counter (default {TARGET_NOUNS})')
    parser.add_argument('--limit', type=int, default=0, help='Cap counters processed')
    parser.add_argument('--ceiling', type=float, default=None,
                        help='Abort once spend since run start exceeds this USD')
    parser.add_argument('--report', action='store_true',
                        help='Print the sign-off report and exit (no model calls)')
    args = parser.parse_args()

    if args.report:
        print_report(report())
        sys.exit(0)

    if not (args.counters or args.underserved or args.smoke):
        parser.error('pass --counters, --underserved, --smoke or --report')

    _db = get_supabase_admin()
    if args.smoke:
        _targets = [('皿', 'plates of food')]
    elif args.counters:
        _targets = [(c.strip(), '') for c in args.counters.split(',') if c.strip()]
    else:
        _targets = _fetch_underserved(_db, args.underserved)

    run(_targets, do_classify=args.classify, count=args.count,
        limit=args.limit, ceiling=args.ceiling)
