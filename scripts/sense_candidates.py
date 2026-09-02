#!/usr/bin/env python3
"""
Resolve extracted terms against the sense dictionary and emit a decision sheet.

Stage 2 of the sense-linking workflow (.claude/skills/test-sense-linking/SKILL.md).
Takes the terms an LLM pulled out of one transcript and, for each, answers the
only two questions stage 3 needs: does this word already exist in
dim_vocabulary, and if so what senses does it already have?

This script never calls an LLM and never writes. It is deliberately the boring
half of the loop — every judgement is deferred to stage 3 and every write to
stage 4, so a bad decision can be re-made by re-running stage 3 against the same
candidate file.

Why this exists rather than letting the LLM query directly: the term an LLM
reads off a transcript is a surface form, and dim_vocabulary is keyed by the
tokenizer's lemma. Matching those is a mechanical job with a right answer
(see VocabIndex.resolve), and getting it wrong doesn't fail loudly — it creates
a duplicate vocabulary row that quietly splits a word's senses in two.

Usage:
    python scripts/sense_candidates.py --test-id 412 \\
        --terms-file data/sense_linking/412.terms.json \\
        --output data/sense_linking/412.candidates.json

    echo '["fabric","tail"]' | python scripts/sense_candidates.py --test-id <slug> --terms-stdin

Terms file format (UTF-8) — either shape is accepted:
    ["term one", "term two"]
    [{"term": "term one"}, {"term": "term two", "note": "appears twice"}]

Options:
    --test-id REF      Required. tests.id (uuid) or tests.slug. The slug is
                       usually what you want — it is what the stage 1 CSV and the
                       candidate filenames use.
    --terms-file PATH  JSON file of extracted terms.
    --terms-stdin      Read the terms JSON from stdin instead.
    --output PATH      Where to write the candidate sheet
                       (default: data/sense_linking/<slug>.candidates.json)
"""

import os
import sys
import json
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.vocabulary.sense_generator import POS_LEGENDS, find_sentence
from scripts.sense_linking_common import (
    VocabIndex,
    fetch_standard_senses,
    fetch_test,
    language_code_for,
)

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join('data', 'sense_linking')


def load_simple_register(db, language_code: str, language_id: int) -> str:
    """The child-register guide a `simple` definition must be written to.

    Read through SenseGenerator rather than re-querying dim_complexity_tiers here,
    so the register stage 3 writes against is byte-identical to the one the
    hosted sense pipeline uses (ADR-003, single source of truth). Best-effort:
    a candidate sheet without it is still usable, just less well calibrated.
    """
    try:
        from services.test_generation.database_client import TestDatabaseClient
        from services.vocabulary.sense_generator import SenseGenerator
        gen = SenseGenerator(
            openai_client=None, db=db, db_client=TestDatabaseClient(),
            language_code=language_code, language_id=language_id, dry_run=True,
        )
        return gen._simple_register
    except Exception as exc:
        logger.warning("Could not load the simple register: %s", exc)
        return ''


def load_terms(args) -> list[dict]:
    """Normalise either accepted terms shape into [{term, note}, ...].

    Duplicates are collapsed on the way through: a transcript mentioning a word
    five times should produce one decision, not five, and stage 4 links one
    sense_id per word regardless.
    """
    if args.terms_stdin:
        raw = json.load(sys.stdin)
    elif args.terms_file:
        with open(args.terms_file, encoding='utf-8') as fh:
            raw = json.load(fh)
    else:
        raise SystemExit("Pass --terms-file PATH or --terms-stdin")

    if not isinstance(raw, list):
        raise SystemExit("Terms JSON must be a list")

    seen: set[str] = set()
    terms: list[dict] = []
    for entry in raw:
        if isinstance(entry, str):
            term, note = entry.strip(), None
        elif isinstance(entry, dict):
            term, note = str(entry.get('term', '')).strip(), entry.get('note')
        else:
            logger.warning("Ignoring unrecognised term entry: %r", entry)
            continue
        if not term or term in seen:
            continue
        seen.add(term)
        terms.append({'term': term, 'note': note})
    return terms


def build_sheet(db, test_ref: str, terms: list[dict]) -> dict:
    test = fetch_test(db, test_ref)
    language_id = test['language_id']
    language_code = language_code_for(language_id)
    transcript = test.get('transcript') or ''

    if test.get('vocab_sense_ids'):
        logger.warning(
            "test %s already has %d linked senses — stage 4 will refuse to "
            "overwrite them without --force",
            test['id'], len(test['vocab_sense_ids']),
        )

    index = VocabIndex(db, language_id, language_code)

    resolved = []
    for entry in terms:
        vocab_id, lemma, tier = index.resolve(entry['term'])
        resolved.append({**entry, 'vocab_id': vocab_id, 'lemma': lemma, 'match': tier})

    senses_by_vocab = fetch_standard_senses(
        db, [r['vocab_id'] for r in resolved if r['vocab_id']], language_id
    )

    items = []
    for r in resolved:
        candidates = [
            {
                'sense_id': s['id'],
                'sense_rank': s['sense_rank'],
                'definition': s.get('definition'),
                'example_sentence': s.get('example_sentence'),
                'source': s.get('source'),
            }
            for s in senses_by_vocab.get(r['vocab_id'], [])
        ] if r['vocab_id'] else []

        # A term the tokenizer never produced from this transcript is usually an
        # LLM paraphrase of what the text said. Flagged, not dropped — stage 3
        # decides, because a legitimate multi-word phrase also fails this test.
        in_transcript = bool(r['term'] and r['term'] in transcript)
        if not in_transcript and r['lemma']:
            in_transcript = r['lemma'] in transcript

        items.append({
            'term': r['term'],
            'note': r.get('note'),
            'lemma': r['lemma'],
            'vocab_id': r['vocab_id'],
            'match': r['match'],
            'in_transcript': in_transcript,
            'sentence': find_sentence(transcript, r['lemma'] or r['term']),
            'candidates': candidates,
        })

    return {
        'test_id': test['id'],
        'slug': test.get('slug'),
        'language_code': language_code,
        'language_id': language_id,
        'difficulty': test.get('difficulty'),
        'transcript': transcript,
        'pos_legend': POS_LEGENDS.get(language_code, POS_LEGENDS['en']),
        'simple_register': load_simple_register(db, language_code, language_id),
        'items': items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--test-id', required=True,
                        help='tests.id (uuid) or tests.slug')
    parser.add_argument('--terms-file')
    parser.add_argument('--terms-stdin', action='store_true')
    parser.add_argument('--output', '-o')
    args = parser.parse_args()

    terms = load_terms(args)
    if not terms:
        logger.error("No usable terms supplied")
        return 1

    db = get_supabase_admin()
    sheet = build_sheet(db, args.test_id, terms)

    output = args.output or os.path.join(
        OUTPUT_DIR, f"{sheet['slug'] or sheet['test_id']}.candidates.json")
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    with open(output, 'w', encoding='utf-8') as fh:
        json.dump(sheet, fh, ensure_ascii=False, indent=2)

    known = sum(1 for i in sheet['items'] if i['vocab_id'])
    with_senses = sum(1 for i in sheet['items'] if i['candidates'])
    fuzzy = sum(1 for i in sheet['items'] if i['match'] not in ('exact', 'none'))
    absent = sum(1 for i in sheet['items'] if not i['in_transcript'])

    logger.info("Wrote %s", output)
    logger.info("  %d terms | %d in dim_vocabulary | %d with existing senses",
                len(sheet['items']), known, with_senses)
    if fuzzy:
        logger.info("  %d matched below `exact` — check the `match` field before trusting them", fuzzy)
    if absent:
        logger.warning("  %d terms do not appear in the transcript", absent)
    return 0


if __name__ == '__main__':
    sys.exit(main())
