#!/usr/bin/env python3
"""
Rebuild tests.vocab_token_map where it has drifted from the dictionary (TASK-779).

Why this exists
    task778_ja_loanword_lemma_cleanup.sql deleted every sense it judged
    unreferenced. Its reference check unioned vocab_sense_ids, questions,
    mysteries and the calibration tables — but not vocab_token_map, which is
    jsonb. Live on 2026-09-15 that left 198 token-map entries across 47 ja tests
    pointing at deleted senses (シャツ, デザイン, メンバー, …). The reader renders
    those tokens as clickable and then has no definition to show, and a
    per-occurrence coverage term (TASK-780) would read them as unresolvable.

What it does
    For each target test, rebuilds the map with the same builder the
    sense-linking workflow uses (sense_linking_common.build_token_map_with_fallback),
    seeded from the test's own vocab_sense_ids. It writes vocab_token_map ONLY —
    never vocab_sense_ids, never dim_word_senses.

Safety
    A rebuild is refused, not written, when:
      - the new map does not concatenate back to the transcript exactly (the
        reader relies on that) and is not text-identical to the current map
        either — 6 live ja maps already lose the transcript's newlines, because
        the ja processor drops them; that pre-existing defect is not this
        script's to fix, but a rebuild must not make it worse;
      - it would unlink a token that currently resolves to a live sense;
      - it still contains a sense id that does not exist.
    --allow-loss overrides only the second rule, for a reviewed run.

Targets
    Default: tests whose map references a deleted sense, or that have linked
    senses but no map at all. --all considers every active test in the language;
    an unchanged rebuild is never written.

Not fixed here
    en maps and en vocab_sense_ids disagree by design, not by drift: 330 linked
    senses are multi-word lemmas ("take off") that a per-token map cannot carry,
    and ~325 map tokens are fallback links to words the linker did not extract.
    A rebuild does not change either.

Usage:
    python scripts/rebuild_token_maps.py --language ja --dry-run
    python scripts/rebuild_token_maps.py --language ja
    python scripts/rebuild_token_maps.py --test-id <uuid-or-slug> --dry-run
"""

import os
import sys
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from scripts.sense_linking_common import (
    PAGE,
    VocabIndex,
    build_token_map_with_fallback,
    fetch_test,
    language_code_for,
    lemma_sense_lookup,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ pure logic

def map_sense_ids(token_map) -> set[int]:
    """Distinct non-zero sense ids in a token map, tolerating malformed entries."""
    out: set[int] = set()
    for entry in token_map or []:
        if isinstance(entry, (list, tuple)) and len(entry) > 1:
            sid = entry[1]
            if isinstance(sid, int) and sid > 0:
                out.add(sid)
    return out


def _linked_tokens(token_map, live: set[int]) -> int:
    return sum(1 for e in token_map or []
               if isinstance(e, (list, tuple)) and len(e) > 1 and e[1] in live)


def assess_rebuild(old_map, new_map, transcript: str, live_sense_ids: set[int],
                   allow_loss: bool = False) -> dict:
    """Compare a test's current map with its rebuild and decide whether to write.

    `live_sense_ids` must contain every sense id referenced by either map that
    still exists in dim_word_senses; anything absent from it is treated as deleted.

    verdict is 'unchanged', 'write', or 'refuse:<reason>'.
    """
    old_ids = map_sense_ids(old_map)
    new_ids = map_sense_ids(new_map)
    report = {
        'dangling_before': len(old_ids - live_sense_ids),
        'dangling_after': len(new_ids - live_sense_ids),
        'live_links_before': _linked_tokens(old_map, live_sense_ids),
        'live_links_after': _linked_tokens(new_map, live_sense_ids),
        'tokens_before': len(old_map or []),
        'tokens_after': len(new_map or []),
    }

    rebuilt_text = ''.join(str(e[0]) for e in new_map or [])
    old_text = ''.join(str(e[0]) for e in old_map or []
                       if isinstance(e, (list, tuple)) and e)
    # The ja processor drops newlines, so some live maps already fall short of
    # the transcript. A rebuild that reproduces the current map's text exactly is
    # no worse than today; anything else is a regression.
    report['text_faithful'] = rebuilt_text == (transcript or '')
    if not report['text_faithful'] and not (old_map and rebuilt_text == old_text):
        report['verdict'] = 'refuse:transcript_mismatch'
    elif report['dangling_after']:
        report['verdict'] = 'refuse:dangling_after'
    elif report['live_links_after'] < report['live_links_before'] and not allow_loss:
        report['verdict'] = 'refuse:would_unlink'
    elif [list(e) for e in old_map or []] == [list(e) for e in new_map or []]:
        report['verdict'] = 'unchanged'
    else:
        report['verdict'] = 'write'
    return report


def is_default_target(test: dict, live_sense_ids: set[int]) -> bool:
    """A map pointing at a deleted sense, or linked senses with no map at all."""
    token_map = test.get('vocab_token_map') or []
    if not token_map:
        return bool(test.get('vocab_sense_ids'))
    return bool(map_sense_ids(token_map) - live_sense_ids)


# ------------------------------------------------------------------- DB access

def fetch_tests(db, language_id: int) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page = (db.table('tests')
                .select('id, slug, language_id, transcript, vocab_sense_ids, vocab_token_map')
                .eq('language_id', language_id)
                .eq('is_active', True)
                .order('id')
                .range(offset, offset + PAGE - 1)
                .execute().data or [])
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    return rows


def existing_sense_ids(db, sense_ids) -> set[int]:
    ids = sorted(set(sense_ids))
    found: set[int] = set()
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        resp = db.table('dim_word_senses').select('id').in_('id', chunk).execute()
        found.update(r['id'] for r in (resp.data or []))
    return found


# ------------------------------------------------------------------------ main

def run(db, tests: list[dict], language_code: str, language_id: int,
        consider_all: bool, dry_run: bool, allow_loss: bool) -> int:
    referenced = set()
    for t in tests:
        referenced |= map_sense_ids(t.get('vocab_token_map'))
    live = existing_sense_ids(db, referenced)

    targets = [t for t in tests
               if (t.get('transcript') or '').strip()
               and (consider_all or is_default_target(t, live))]
    logger.info("%d active %s test(s); %d targeted (%s)", len(tests), language_code,
                len(targets), 'all' if consider_all else 'dangling or missing map')
    if not targets:
        return 0

    index = VocabIndex(db, language_id, language_code)
    tally: dict[str, int] = {}
    refused = 0

    for test in targets:
        seed = lemma_sense_lookup(db, test.get('vocab_sense_ids') or [])
        new_map, unmatched = build_token_map_with_fallback(
            db, language_code, language_id, test['transcript'], seed,
            resolve_vocab_id=lambda lemma: index.resolve(lemma)[0],
        )
        # New maps only draw on senses that exist now; add them to the live set
        # so a fresh link is not misread as dangling.
        live |= existing_sense_ids(db, map_sense_ids(new_map) - live)

        report = assess_rebuild(test.get('vocab_token_map'), new_map,
                                test['transcript'], live, allow_loss=allow_loss)
        verdict = report['verdict']
        tally[verdict] = tally.get(verdict, 0) + 1

        logger.info(
            "%s %s: %s | dangling %d->%d | linked tokens %d->%d | tokens %d->%d | %d unmatched",
            '[DRY RUN]' if dry_run else '', test.get('slug'), verdict,
            report['dangling_before'], report['dangling_after'],
            report['live_links_before'], report['live_links_after'],
            report['tokens_before'], report['tokens_after'], len(unmatched),
        )

        if verdict.startswith('refuse'):
            refused += 1
        elif verdict == 'write' and not dry_run:
            db.table('tests').update({'vocab_token_map': new_map}) \
                .eq('id', test['id']).execute()

    logger.info("Summary (%s): %s", 'dry run' if dry_run else 'applied',
                ', '.join(f"{k}={v}" for k, v in sorted(tally.items())))
    return 1 if refused else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language', choices=['zh', 'en', 'ja'])
    parser.add_argument('--test-id', help='tests.id (uuid) or tests.slug')
    parser.add_argument('--all', action='store_true',
                        help='Consider every active test, not just drifted ones')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--allow-loss', action='store_true',
                        help='Write even if a currently-working link would be lost')
    args = parser.parse_args()

    if not (args.language or args.test_id):
        parser.error("Pass --language or --test-id")

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()

    if args.test_id:
        test = fetch_test(db, args.test_id)
        language_id = test['language_id']
        return run(db, [test], language_code_for(language_id), language_id,
                   consider_all=True, dry_run=args.dry_run, allow_loss=args.allow_loss)

    language_id = Config.LANGUAGE_CODE_TO_ID[args.language]
    return run(db, fetch_tests(db, language_id), args.language, language_id,
               consider_all=args.all, dry_run=args.dry_run, allow_loss=args.allow_loss)


if __name__ == '__main__':
    sys.exit(main())
