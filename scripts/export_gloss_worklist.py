#!/usr/bin/env python3
"""
Export the cross-language gloss worklist, as batch files for Claude Code to
write in-session.

Stage 1 of the in-session workflow
(.claude/skills/cross-language-glosses/SKILL.md). A "gloss" here is a
dim_word_senses row whose definition_language_id differs from the word's own
dim_vocabulary.language_id -- e.g. an English definition of a Japanese word,
written for a learner reading their L1. See services/vocabulary/gloss_generator.py
for why these are no longer written by a hosted translate-a-definition prompt.

Selection is a *complete source pair*: a (vocab_id, sense_rank) that has both a
`simple` and a `standard` definition in --source-language. A standard-only sense
(source has a standard row but no simple counterpart -- true for a real slice of
`en`) is excluded and counted separately rather than glossed from a half pair,
matching the export-worklist convention in export_sense_seed_worklist.py of
never silently half-writing a two-level concept.

One batch item per (vocab_id, sense_rank), carrying every --target-languages
code that still needs a gloss for that sense -- so a sense is answered once, in
one pass, and every target language's simple+standard rows are written together
and stay consistent with each other. Without --overwrite, a (vocab_id,
sense_rank) whose requested targets are ALL already glossed (both levels, in
every requested target language) is skipped entirely: that is what makes the
job resumable across sessions. A sense with only SOME targets already glossed
(e.g. a run that covered zh but was interrupted before ja) is still exported,
but its `target_languages` field lists only the ones still missing -- so a
resumed run does not re-answer a language that already has a good gloss.

Usage:
    python scripts/export_gloss_worklist.py --source-language en --target-languages zh,ja
    python scripts/export_gloss_worklist.py --source-language en --target-languages zh,ja --limit 40 --batch-size 40
    python scripts/export_gloss_worklist.py --source-language ja --target-languages en --overwrite

Options:
    --source-language CODE     Required. The word's own language: zh | en | ja
    --target-languages LIST    Required. Comma-separated languages to write
                                definitions IN: zh | en | ja (must not include
                                --source-language)
    --overwrite                Re-export senses that already have a gloss row
                                for a requested target, instead of skipping them
    --batch-size N              Senses per output file (default: 40)
    --limit N                  Cap total senses exported, after filtering (0 = all)
    --out-dir PATH              Default: data/gloss_seeding/<source>_to_<targets>
"""

import os
import sys
import json
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PAGE = 1000
LEVELS = ('simple', 'standard')


def _paged(query_fn) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page = query_fn(offset).execute().data or []
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    return rows


def load_complete_source_pairs(db, source_id: int) -> tuple[list[dict], int]:
    """Every (vocab_id, sense_rank) with both levels defined in the source
    language. Returns (pairs, standard_only_count).

    Filters on dim_word_senses.definition_language_id (the row's OWN
    language), not a join through dim_vocabulary -- so a gloss row written by
    an earlier run (definition_language_id = some OTHER language) can never
    be picked up here as a second "source" definition. dim_vocabulary.language_id
    is checked too, as a cheap assertion against the one-native-row-per-word
    invariant (mirrors backfill_gloss_definitions.py's old _load_source_senses).
    """
    rows = _paged(lambda o: db.table('dim_word_senses')
                  .select('vocab_id, sense_rank, definition_level, definition, '
                          'example_sentence, dim_vocabulary(lemma, language_id)')
                  .eq('definition_language_id', source_id)
                  .in_('definition_level', LEVELS)
                  .range(o, o + PAGE - 1))

    by_key: dict[tuple[int, int], dict] = {}
    for r in rows:
        vocab = r.get('dim_vocabulary') or {}
        if vocab.get('language_id') != source_id:
            continue  # paranoia: shouldn't happen given the filter above
        key = (r['vocab_id'], r['sense_rank'])
        entry = by_key.setdefault(key, {
            'vocab_id': r['vocab_id'],
            'sense_rank': r['sense_rank'],
            'lemma': vocab.get('lemma', ''),
            'example_sentence': '',
        })
        level = r['definition_level']
        entry[level] = r.get('definition', '') or ''
        # Either level's example sentence will do; prefer standard's if both exist.
        example = r.get('example_sentence') or ''
        if example and (level == 'standard' or not entry['example_sentence']):
            entry['example_sentence'] = example

    complete = [e for e in by_key.values() if e.get('simple') and e.get('standard')]
    standard_only = sum(1 for e in by_key.values() if e.get('standard') and not e.get('simple'))
    complete.sort(key=lambda e: (e['vocab_id'], e['sense_rank']))
    return complete, standard_only


def load_glossed_targets(db, target_id: int) -> set[tuple[int, int]]:
    """(vocab_id, sense_rank) pairs that already have BOTH levels glossed in
    this target language. A pair with only one level present does not count
    as done -- it still needs the missing level written."""
    rows = _paged(lambda o: db.table('dim_word_senses')
                  .select('vocab_id, sense_rank, definition_level')
                  .eq('definition_language_id', target_id)
                  .eq('source', 'llm_gloss')
                  .range(o, o + PAGE - 1))
    levels_by_key: dict[tuple[int, int], set[str]] = {}
    for r in rows:
        key = (r['vocab_id'], r['sense_rank'])
        levels_by_key.setdefault(key, set()).add(r['definition_level'])
    return {key for key, levels in levels_by_key.items() if set(LEVELS) <= levels}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source-language', required=True, choices=['zh', 'en', 'ja'])
    parser.add_argument('--target-languages', required=True,
                        help='Comma-separated: zh | en | ja (must exclude --source-language)')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--batch-size', type=int, default=40)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--out-dir')
    args = parser.parse_args()

    targets = [c.strip() for c in args.target_languages.split(',') if c.strip()]
    if not targets:
        logger.error("--target-languages must name at least one language")
        return 1
    if args.source_language in targets:
        logger.error("--target-languages must not include the source language (%s)",
                     args.source_language)
        return 1
    for code in targets:
        if code not in ('zh', 'en', 'ja'):
            logger.error("Unknown target language %r", code)
            return 1

    source_id = Config.LANGUAGE_CODE_TO_ID[args.source_language]
    target_ids = {code: Config.LANGUAGE_CODE_TO_ID[code] for code in targets}
    db = get_supabase_admin()

    pairs, standard_only = load_complete_source_pairs(db, source_id)
    logger.info("%s: %d complete sense pair(s) (simple+standard both present)",
                args.source_language, len(pairs))
    if standard_only:
        logger.info(
            "  excluded %d standard-only sense(s) (no simple counterpart in %s) -- "
            "not glossed from a half pair", standard_only, args.source_language)

    glossed_by_target = {
        code: (set() if args.overwrite else load_glossed_targets(db, tid))
        for code, tid in target_ids.items()
    }

    items = []
    already_done = 0
    for pair in pairs:
        key = (pair['vocab_id'], pair['sense_rank'])
        missing = [code for code in targets if key not in glossed_by_target[code]]
        if not missing:
            already_done += 1
            continue
        items.append({
            'vocab_id': pair['vocab_id'],
            'sense_rank': pair['sense_rank'],
            'lemma': pair['lemma'],
            'source_simple': pair['simple'],
            'source_standard': pair['standard'],
            'example_sentence': pair['example_sentence'],
            'target_languages': missing,
        })

    logger.info("  %d already fully glossed for %s (skipped)", already_done, targets)
    if args.limit:
        items = items[:args.limit]
        logger.info("  limited to %d", len(items))

    if not items:
        logger.info("Nothing to gloss.")
        return 0

    out_dir = args.out_dir or os.path.join(
        'data', 'gloss_seeding', f"{args.source_language}_to_{'-'.join(targets)}")
    os.makedirs(out_dir, exist_ok=True)

    batches = [items[i:i + args.batch_size] for i in range(0, len(items), args.batch_size)]
    for n, batch in enumerate(batches, start=1):
        path = os.path.join(out_dir, f"batch_{n:03d}.json")
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump({
                'source_language_code': args.source_language,
                'source_language_id': source_id,
                'target_languages': targets,
                'target_language_ids': target_ids,
                'batch': n,
                'of': len(batches),
                'items': batch,
            }, fh, ensure_ascii=False, indent=2)

    logger.info("Wrote %d batch file(s) of up to %d senses to %s",
                len(batches), args.batch_size, out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
