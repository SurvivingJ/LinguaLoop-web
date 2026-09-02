#!/usr/bin/env python3
"""
Apply sense decisions to the database and link a test to its vocabulary.

Stage 4 of the sense-linking workflow (.claude/skills/test-sense-linking/SKILL.md).
The only stage that writes. Takes the select-or-create decisions stage 3 made and:

    1. creates dim_vocabulary rows for genuinely new lemmas
    2. writes new senses through SenseGenerator._write_two_levels
    3. writes tests.vocab_sense_ids / vocab_sense_stats / vocab_token_map

Step 2 delegates on purpose. A new sense is not one INSERT — it is a paired
simple+standard row at a shared sense_rank, a POS write-back to dim_vocabulary,
an is_validated language check, a source_ref, and an embedding for both levels
(without which the distractor mid-cosine band degrades silently for exactly the
newest words). Re-implementing that here would make this the second writer of
dim_word_senses, free to drift from the first. It calls the real one instead.

Validation is fail-closed. A sense_id that doesn't exist, isn't standard-level,
is in the wrong definition language, or belongs to a different word aborts the
run before anything is written. This repo has had guardrails that were silently
inert for months; a link to a hallucinated sense_id is exactly the kind of error
that surfaces later as a wrong definition in a learner's face, so it stops here.

Usage:
    # dry run first — always
    python scripts/upload_test_senses.py --decisions-file data/sense_linking/<slug>.decisions.json --dry-run
    python scripts/upload_test_senses.py --decisions-file data/sense_linking/<slug>.decisions.json

    # No LLM needed: rebuild vocab_sense_ids from a token map that already has them
    python scripts/upload_test_senses.py --from-token-map --language en --dry-run

Decisions file format:
    {
      "test_id": "03f1ba3e-316b-45f2-b0c2-4bec27bc38ed",
      "decisions": [
        {"term": "<known word>", "vocab_id": 4412, "action": "select", "sense_id": 8812},
        {"term": "<new word>", "vocab_id": null, "lemma": "<new word>", "action": "create",
         "simple": "...", "standard": "...", "example": "...",
         "part_of_speech": 1, "confidence": 0.9},
        {"term": "<a name>", "action": "skip", "reason": "proper noun"}
      ]
    }

Options:
    --decisions-file PATH  Stage 3 output to apply.
    --from-token-map       Ignore decisions; rebuild vocab_sense_ids from each
                           test's existing vocab_token_map. Needs --test-id or --language.
    --test-id REF          Restrict --from-token-map to one test (uuid or slug).
    --language CODE        Restrict --from-token-map to one language.
    --dry-run              Report what would change, write nothing.
    --force                Overwrite vocab_sense_ids on a test that already has them.
    --skip-invalid         Drop invalid decisions and continue instead of aborting.
    --source-model NAME    Recorded in dim_word_senses.source_ref for created senses
                           (default: claude-code:test-sense-linking)
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
from services.vocabulary.sense_generator import POS_LEGENDS, SenseGenerator
from services.vocabulary.frequency_service import compute_zipf_for_vocab_item
from scripts.sense_linking_common import (
    PAGE,
    VocabIndex,
    _looks_like_uuid,
    build_token_map_with_fallback,
    fetch_standard_senses,
    fetch_test,
    language_code_for,
)

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_SOURCE_MODEL = 'claude-code:test-sense-linking'
VALID_ACTIONS = {'select', 'create', 'skip'}


class DecisionError(Exception):
    """A decision that cannot be applied safely."""


# --------------------------------------------------------------------- validate

def validate_decisions(db, decisions: list[dict], language_id: int) -> tuple[list[dict], list[str]]:
    """Split decisions into applicable ones and a list of rejection reasons.

    Every `select` sense_id is verified against the database in one batched read:
    it must exist, be standard-level, be in this test's definition language, and
    belong to the vocab_id the decision claims. An id that passes all four is one
    the renderer can safely show.
    """
    errors: list[str] = []
    applicable: list[dict] = []

    select_ids = [d.get('sense_id') for d in decisions
                  if d.get('action') == 'select' and isinstance(d.get('sense_id'), int)]

    verified: dict[int, dict] = {}
    for i in range(0, len(select_ids), 500):
        chunk = select_ids[i:i + 500]
        resp = db.table('dim_word_senses') \
            .select('id, vocab_id, definition_level, definition_language_id') \
            .in_('id', chunk) \
            .execute()
        for row in (resp.data or []):
            verified[row['id']] = row

    for idx, d in enumerate(decisions):
        term = d.get('term') or d.get('lemma') or f'#{idx}'
        action = d.get('action')

        if action not in VALID_ACTIONS:
            errors.append(f"{term}: unknown action {action!r}")
            continue
        if action == 'skip':
            continue

        if action == 'select':
            sense_id = d.get('sense_id')
            if not isinstance(sense_id, int):
                errors.append(f"{term}: select without an integer sense_id")
                continue
            row = verified.get(sense_id)
            if row is None:
                errors.append(f"{term}: sense_id {sense_id} does not exist")
                continue
            if row['definition_level'] != 'standard':
                errors.append(
                    f"{term}: sense_id {sense_id} is {row['definition_level']}-level; "
                    "only standard senses are linkable"
                )
                continue
            if row['definition_language_id'] != language_id:
                errors.append(
                    f"{term}: sense_id {sense_id} is in language "
                    f"{row['definition_language_id']}, test is {language_id}"
                )
                continue
            claimed = d.get('vocab_id')
            if isinstance(claimed, int) and claimed != row['vocab_id']:
                errors.append(
                    f"{term}: sense_id {sense_id} belongs to vocab {row['vocab_id']}, "
                    f"decision claims vocab {claimed}"
                )
                continue
            applicable.append({**d, 'vocab_id': row['vocab_id']})
            continue

        # action == 'create'
        if not (d.get('lemma') or d.get('term')):
            errors.append(f"{term}: create without a lemma")
            continue
        if not str(d.get('standard') or '').strip():
            errors.append(f"{term}: create without a `standard` definition")
            continue
        if not str(d.get('simple') or '').strip():
            errors.append(
                f"{term}: create without a `simple` definition — both levels are "
                "required, a standard-only sense is the drift the two-level "
                "backfill exists to prevent"
            )
            continue
        applicable.append(d)

    return applicable, errors


# ----------------------------------------------------------------------- apply

def get_or_create_vocab(db, index: VocabIndex, lemma: str, language_id: int,
                        language_code: str, pos_code, dry_run: bool) -> int | None:
    """Return the vocab_id for `lemma`, inserting a dim_vocabulary row if needed."""
    vocab_id, canonical, _tier = index.resolve(lemma)
    if vocab_id:
        return vocab_id

    lemma = canonical or lemma
    pos_name = POS_LEGENDS.get(language_code, POS_LEGENDS['en']).get(pos_code) \
        if isinstance(pos_code, int) else None

    row = {'lemma': lemma, 'language_id': language_id}
    if pos_name and pos_name != 'other':
        row['part_of_speech'] = pos_name
    zipf = compute_zipf_for_vocab_item({'lemma': lemma}, language_code)
    if zipf is not None:
        row['frequency_rank'] = zipf

    if dry_run:
        logger.info("  [DRY RUN] would create dim_vocabulary row for %r", lemma)
        return None

    try:
        resp = db.table('dim_vocabulary').insert(row).execute()
        vocab_id = resp.data[0]['id']
    except Exception:
        # Raced or already present under a spelling the index missed.
        lookup = db.table('dim_vocabulary').select('id') \
            .eq('lemma', lemma).eq('language_id', language_id).limit(1).execute()
        if not lookup.data:
            raise
        vocab_id = lookup.data[0]['id']

    index.by_lemma[lemma] = vocab_id
    index.by_casefold.setdefault(lemma.casefold(), vocab_id)
    return vocab_id


def apply_decisions(db, sheet: dict, args) -> dict:
    """Apply one test's decisions. Returns a stats dict."""
    test_id = sheet['test_id']
    test = fetch_test(db, test_id)
    language_id = test['language_id']
    language_code = language_code_for(language_id)
    transcript = test.get('transcript') or ''

    if test.get('vocab_sense_ids') and not args.force:
        raise DecisionError(
            f"test {test_id} already has {len(test['vocab_sense_ids'])} linked senses; "
            "pass --force to overwrite"
        )

    decisions = sheet.get('decisions') or []
    applicable, errors = validate_decisions(db, decisions, language_id)

    if errors:
        for e in errors:
            logger.error("  invalid decision — %s", e)
        if not args.skip_invalid:
            raise DecisionError(
                f"{len(errors)} invalid decision(s); nothing written. "
                "Fix them, or re-run with --skip-invalid to drop them."
            )
        logger.warning("--skip-invalid: dropping %d decision(s)", len(errors))

    index = VocabIndex(db, language_id, language_code)

    # SenseGenerator is used only for _write_two_levels, which makes no LLM call.
    # The model name is passed so created senses carry honest provenance in
    # source_ref — these definitions came from the skill, not from SENSE_MODEL_DEFAULT.
    sense_gen = SenseGenerator(
        openai_client=None,
        db=db,
        db_client=_prompt_db_client(),
        language_code=language_code,
        language_id=language_id,
        model=args.source_model,
        dry_run=args.dry_run,
    )

    lemma_to_sense: dict[str, int] = {}
    sense_ids: list[int] = []
    vocab_ids: list[int] = []
    stats = {'selected': 0, 'created': 0, 'skipped': len(decisions) - len(applicable),
             'failed': 0}

    creates = [d for d in applicable if d.get('action') == 'create']
    create_vocab_ids = [d['vocab_id'] for d in creates if isinstance(d.get('vocab_id'), int)]
    existing_ranks = fetch_standard_senses(db, create_vocab_ids, language_id)

    for d in applicable:
        lemma = d.get('lemma') or d.get('term')

        if d['action'] == 'select':
            sense_id = d['sense_id']
            stats['selected'] += 1
        else:
            vocab_id = d.get('vocab_id')
            if not isinstance(vocab_id, int):
                vocab_id = get_or_create_vocab(
                    db, index, lemma, language_id, language_code,
                    d.get('part_of_speech'), args.dry_run,
                )
            if vocab_id is None:  # dry-run, vocab row not really created
                logger.info("  [DRY RUN] would create sense for %r", lemma)
                stats['created'] += 1
                continue

            existing = existing_ranks.get(vocab_id) or fetch_standard_senses(
                db, [vocab_id], language_id).get(vocab_id, [])
            next_rank = max((s.get('sense_rank') or 0 for s in existing), default=0) + 1

            fields = {
                'simple': str(d['simple']).strip(),
                'standard': str(d['standard']).strip(),
                'example': str(d.get('example') or '').strip(),
                'pos_code': d.get('part_of_speech'),
                'confidence': d.get('confidence'),
                'skip': False,
            }
            sense_id = sense_gen._write_two_levels(vocab_id, lemma, fields, next_rank)
            if sense_id is None:
                logger.error("  failed to write sense for %r", lemma)
                stats['failed'] += 1
                continue
            stats['created'] += 1
            d['vocab_id'] = vocab_id

        if sense_id and sense_id > 0:
            if sense_id not in sense_ids:
                sense_ids.append(sense_id)
            if lemma:
                lemma_to_sense.setdefault(lemma, sense_id)
                lemma_to_sense.setdefault(lemma.casefold(), sense_id)
        if isinstance(d.get('vocab_id'), int):
            vocab_ids.append(d['vocab_id'])

    # A dry run never really writes the new senses, so a test whose decisions are
    # mostly `create` legitimately reaches here with nothing linked yet. Only the
    # live path treats an empty result as a refusal to blank the test.
    if not sense_ids and not (args.dry_run and stats['created']):
        raise DecisionError(f"test {test_id}: no senses resolved, refusing to blank the test")

    token_map, unmatched = _build_extended_token_map(
        db, index, language_code, language_id, transcript, lemma_to_sense
    )

    vocab_stats = {
        'unique_senses': len(sense_ids),
        'unique_vocab': len(set(vocab_ids)),
        'phrases': sum(1 for d in applicable
                       if (d.get('lemma') or d.get('term') or '').strip().count(' ') > 0),
        'single_words': sum(1 for d in applicable
                            if (d.get('lemma') or d.get('term') or '').strip().count(' ') == 0),
    }

    linked_tokens = sum(1 for t in token_map if t[1])
    if args.dry_run:
        logger.info(
            "[DRY RUN] test %s: %d senses (%d selected, %d created), "
            "%d/%d tokens linked, %d lemmas unmatched",
            test_id, len(sense_ids), stats['selected'], stats['created'],
            linked_tokens, len(token_map), len(unmatched),
        )
    else:
        db.table('tests').update({
            'vocab_sense_ids': sense_ids,
            'vocab_sense_stats': vocab_stats,
            'vocab_token_map': token_map,
        }).eq('id', test_id).execute()
        logger.info(
            "test %s: linked %d senses (%d selected, %d created), %d/%d tokens linked",
            test_id, len(sense_ids), stats['selected'], stats['created'],
            linked_tokens, len(token_map),
        )

    if unmatched:
        logger.info("  unmatched content lemmas (render as plain text): %s",
                    ', '.join(unmatched[:15]) + ('…' if len(unmatched) > 15 else ''))

    stats['sense_ids'] = len(sense_ids)
    stats['tokens_linked'] = linked_tokens
    return stats


def _build_extended_token_map(db, index: VocabIndex, language_code: str,
                              language_id: int, transcript: str,
                              lemma_to_sense: dict[str, int]):
    """Token map from the decisions, then extended with already-known senses.

    The decisions only cover the terms stage 3 judged teachable. Every *other*
    content word in the transcript that already has a sense in the dictionary can
    still be linked for free, and leaving those at 0 makes them unclickable in the
    reader for no reason.
    """
    return build_token_map_with_fallback(
        db, language_code, language_id, transcript, lemma_to_sense,
        resolve_vocab_id=lambda lemma: index.resolve(lemma)[0],
    )


def _prompt_db_client():
    """TestDatabaseClient, needed by SenseGenerator's constructor.

    _write_two_levels never reaches for a prompt, but __init__ reads the simple
    register out of dim_complexity_tiers through this client.
    """
    from services.test_generation.database_client import TestDatabaseClient
    return TestDatabaseClient()


# ------------------------------------------------------------- token-map rebuild

def rebuild_from_token_map(db, args) -> int:
    """Derive vocab_sense_ids from an existing vocab_token_map. No LLM, no writes
    to dim_word_senses.

    A test generated before the sense_ids column was populated can still carry a
    fully linked token map. Its distinct non-zero sense ids *are* its vocabulary
    list — recovering them costs one query.
    """
    language_id = Config.LANGUAGE_CODE_TO_ID.get(args.language) if args.language else None

    rows: list[dict] = []
    offset = 0
    while True:
        q = db.table('tests').select('id, slug, vocab_sense_ids, vocab_token_map').order('id')
        if args.test_id:
            # --test-id takes a slug as readily as a uuid; Postgres rejects a slug
            # compared against a uuid column outright, so pick the column here
            # rather than letting a 22P02 surface as an opaque APIError.
            q = q.eq('id' if _looks_like_uuid(args.test_id) else 'slug', args.test_id)
        if language_id is not None:
            q = q.eq('language_id', language_id)
        page = (q.range(offset, offset + PAGE - 1).execute().data or [])
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE

    updated = 0
    for test in rows:
        if (test.get('vocab_sense_ids') or []) and not args.force:
            continue
        token_map = test.get('vocab_token_map') or []
        sense_ids: list[int] = []
        for token in token_map:
            if isinstance(token, (list, tuple)) and len(token) > 1:
                sid = token[1]
                if isinstance(sid, int) and sid > 0 and sid not in sense_ids:
                    sense_ids.append(sid)
        if not sense_ids:
            continue

        if args.dry_run:
            logger.info("[DRY RUN] test %s (%s): would link %d senses from token map",
                        test['id'], test.get('slug'), len(sense_ids))
        else:
            db.table('tests').update({
                'vocab_sense_ids': sense_ids,
                'vocab_sense_stats': {'unique_senses': len(sense_ids),
                                      'source': 'token_map_rebuild'},
            }).eq('id', test['id']).execute()
            logger.info("test %s (%s): linked %d senses from token map",
                        test['id'], test.get('slug'), len(sense_ids))
        updated += 1

    logger.info("%s %d test(s) from existing token maps",
                'Would update' if args.dry_run else 'Updated', updated)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--decisions-file')
    parser.add_argument('--from-token-map', action='store_true')
    parser.add_argument('--test-id', help='tests.id (uuid) or tests.slug')
    parser.add_argument('--language', choices=['zh', 'en', 'ja'])
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--skip-invalid', action='store_true')
    parser.add_argument('--source-model', default=DEFAULT_SOURCE_MODEL)
    args = parser.parse_args()

    db = get_supabase_admin()

    if args.from_token_map:
        if not (args.test_id or args.language):
            parser.error("--from-token-map needs --test-id or --language")
        return rebuild_from_token_map(db, args)

    if not args.decisions_file:
        parser.error("Pass --decisions-file PATH (or --from-token-map)")

    with open(args.decisions_file, encoding='utf-8') as fh:
        sheet = json.load(fh)
    if not sheet.get('test_id'):
        parser.error("Decisions file has no test_id")

    try:
        apply_decisions(db, sheet, args)
    except DecisionError as e:
        logger.error(str(e))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
