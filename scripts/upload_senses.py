#!/usr/bin/env python3
"""
Write a batch of generated two-level senses to dim_word_senses.

Stage 3 of the in-session batch workflow
(.claude/skills/batch-sense-generation/SKILL.md). Takes the definitions Claude
Code wrote for one exported batch and applies them through
``SenseGenerator._write_two_levels`` — the same write path
``scripts/backfill_senses.py`` uses.

Delegating that call is the whole point of this script. A sense is not one
INSERT: it is a paired simple+standard row at a shared sense_rank, a POS
write-back to dim_vocabulary, an is_validated language check, a source_ref, and
an embedding for both levels. Hand-rolling those inserts here would make this a
second writer of dim_word_senses, free to drift from the first.

Rank follows seed_word exactly: the word's existing primary sense_rank when it
has one — so the new standard row *replaces* the old wording at that rank and the
missing simple row joins it — and rank 1 for a brand-new word. Words whose
primary sense is source='manual' are refused, never overwritten.

Validation is fail-closed. A vocab_id that is not in the batch, a definition
missing either level, or a part_of_speech outside the language's legend aborts
the run before anything is written.

Usage:
    python scripts/upload_senses.py --batch-file data/sense_seeding/ja/batch_001.json \\
        --senses-file data/sense_seeding/ja/batch_001.senses.json --dry-run
    python scripts/upload_senses.py --batch-file ... --senses-file ...

Senses file format — a list, or an object with a "senses" list:
    [
      {"vocab_id": 12345, "part_of_speech": 1, "confidence": 0.95,
       "simple": "<child-register definition>",
       "standard": "<standard definition>",
       "example": "<one short sentence using the word>"},
      {"vocab_id": 12346, "skip": true, "reason": "proper noun"}
    ]

Options:
    --batch-file PATH    The exported batch this answers (defines the legal vocab_ids).
    --senses-file PATH   Generated definitions to apply.
    --dry-run            Report what would be written, write nothing.
    --skip-invalid       Drop invalid items and continue instead of aborting.
    --source-model NAME  Recorded in source_ref (default: claude-code:batch-sense-generation)
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
from services.vocabulary.sense_generator import POS_LEGENDS, SenseGenerator
from scripts.sense_linking_common import fetch_standard_senses

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_SOURCE_MODEL = 'claude-code:batch-sense-generation'


class SenseUploadError(Exception):
    """A batch that cannot be applied safely."""


def load_senses(path: str) -> list[dict]:
    with open(path, encoding='utf-8') as fh:
        payload = json.load(fh)
    if isinstance(payload, dict):
        payload = payload.get('senses') or payload.get('items') or []
    if not isinstance(payload, list):
        raise SenseUploadError("Senses file must be a list, or an object with a 'senses' list")
    return payload


def validate(senses: list[dict], batch: dict) -> tuple[list[dict], list[dict], list[str]]:
    """Split into (writable, skipped, errors).

    The batch file is the authority on which vocab_ids are in play. An id that
    was never exported is a transcription slip at best and a write to an
    unrelated word at worst, so it is rejected rather than looked up.
    """
    legal = {item['vocab_id']: item for item in batch['items']}
    legend = POS_LEGENDS.get(batch['language_code'], POS_LEGENDS['en'])

    writable: list[dict] = []
    skipped: list[dict] = []
    errors: list[str] = []
    seen: set[int] = set()

    for i, s in enumerate(senses):
        vocab_id = s.get('vocab_id')
        label = s.get('lemma') or f'vocab_id={vocab_id}' or f'#{i}'

        if not isinstance(vocab_id, int) or vocab_id not in legal:
            errors.append(f"{label}: vocab_id {vocab_id!r} is not in this batch")
            continue
        if vocab_id in seen:
            errors.append(f"{label}: vocab_id {vocab_id} appears twice")
            continue
        seen.add(vocab_id)

        if s.get('skip'):
            skipped.append({**s, 'lemma': legal[vocab_id]['lemma']})
            continue

        simple = str(s.get('simple') or '').strip()
        standard = str(s.get('standard') or '').strip()
        if not standard:
            errors.append(f"{label}: no `standard` definition")
            continue
        if not simple:
            errors.append(
                f"{label}: no `simple` definition — both levels are required, a "
                "standard-only row is the drift the two-level treatment prevents"
            )
            continue

        pos = s.get('part_of_speech')
        if pos is not None and (not isinstance(pos, int) or pos not in legend):
            errors.append(
                f"{label}: part_of_speech {pos!r} is not a code in this "
                f"language's legend {sorted(legend)}"
            )
            continue

        writable.append({**s, 'lemma': legal[vocab_id]['lemma']})

    missing = set(legal) - seen
    if missing:
        errors.append(
            f"{len(missing)} lemma(s) in the batch got no answer: "
            + ', '.join(legal[v]['lemma'] for v in list(missing)[:10])
            + ('…' if len(missing) > 10 else '')
        )

    return writable, skipped, errors


def apply(db, batch: dict, writable: list[dict], args) -> dict:
    language_code = batch['language_code']
    language_id = batch['language_id']

    # SenseGenerator is used only for _write_two_levels, which makes no LLM call.
    # The model name is passed so source_ref records where these came from.
    from services.test_generation.database_client import TestDatabaseClient
    gen = SenseGenerator(
        openai_client=None, db=db, db_client=TestDatabaseClient(),
        language_code=language_code, language_id=language_id,
        model=args.source_model, dry_run=args.dry_run,
    )

    existing_by_vocab = fetch_standard_senses(
        db, [s['vocab_id'] for s in writable], language_id
    )

    stats = {'written': 0, 'failed': 0, 'refused_manual': 0}
    for s in writable:
        vocab_id = s['vocab_id']
        existing = existing_by_vocab.get(vocab_id) or []

        if any(e.get('source') == 'manual' for e in existing):
            logger.warning("  %s: primary sense is source='manual', refusing to overwrite",
                           s['lemma'])
            stats['refused_manual'] += 1
            continue

        # seed_word's rule: overwrite the existing primary rank so the refreshed
        # standard and the new simple land together; rank 1 for a new word.
        rank = existing[0]['sense_rank'] if existing else 1

        sense_id = gen._write_two_levels(vocab_id, s['lemma'], {
            'simple': str(s['simple']).strip(),
            'standard': str(s['standard']).strip(),
            'example': str(s.get('example') or '').strip(),
            'pos_code': s.get('part_of_speech'),
            'confidence': s.get('confidence'),
            'skip': False,
        }, rank)

        if sense_id is None:
            logger.error("  %s: write failed", s['lemma'])
            stats['failed'] += 1
        else:
            stats['written'] += 1

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--batch-file', required=True)
    parser.add_argument('--senses-file', required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-invalid', action='store_true')
    parser.add_argument('--source-model', default=DEFAULT_SOURCE_MODEL)
    args = parser.parse_args()

    with open(args.batch_file, encoding='utf-8') as fh:
        batch = json.load(fh)

    try:
        senses = load_senses(args.senses_file)
        writable, skipped, errors = validate(senses, batch)

        if errors:
            for e in errors:
                logger.error("  invalid — %s", e)
            if not args.skip_invalid:
                raise SenseUploadError(
                    f"{len(errors)} problem(s); nothing written. Fix them, or "
                    "re-run with --skip-invalid to drop them."
                )
            logger.warning("--skip-invalid: continuing with %d item(s)", len(writable))

        db = get_supabase_admin()
        stats = apply(db, batch, writable, args)
    except SenseUploadError as e:
        logger.error(str(e))
        return 1

    prefix = '[DRY RUN] ' if args.dry_run else ''
    logger.info(
        "%sbatch %s/%s: %d written, %d skipped by the generator, "
        "%d refused (manual), %d failed",
        prefix, batch.get('batch'), batch.get('of'),
        stats['written'], len(skipped), stats['refused_manual'], stats['failed'],
    )
    for s in skipped:
        logger.info("  skipped %s: %s", s['lemma'], s.get('reason') or '(no reason given)')

    return 0 if stats['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
