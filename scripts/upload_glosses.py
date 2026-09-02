#!/usr/bin/env python3
"""
Write a batch of cross-language glosses to dim_word_senses.

Stage 3 of the in-session workflow
(.claude/skills/cross-language-glosses/SKILL.md). Takes the glosses Claude
Code wrote for one exported batch (scripts/export_gloss_worklist.py) and
writes them as additional dim_word_senses rows: same vocab_id and sense_rank
as the source sense, but definition_language_id set to the TARGET language
and source='llm_gloss'.

This cannot go through SenseGenerator._write_two_levels (see upload_senses.py)
-- that method hardcodes definition_language_id to the generator's own
language_id, i.e. the WORD's language. A gloss row needs it set to the target
language instead, so the two simple+standard rows per (vocab_id, sense_rank,
target language) are upserted directly here, on the same
`vocab_id,definition_language_id,definition_level,sense_rank` key
SenseGenerator and backfill_gloss_definitions.py both use. This is additive
only -- it never updates or deletes the source sense_id, so nothing that
already references it (word_assets, exercises, user_word_ladder, ...) is
touched.

Validation is fail-closed, matching upload_senses.py: reject a (vocab_id,
sense_rank) not in the batch, a duplicate, a target language not requested
for that item, a missing `simple` or `standard` for a required target, a
gloss that looks like it's in the wrong language, a gloss shaped like a
sentence instead of an equivalent (see check_gloss_shape), a gloss that still
contains the source word itself, or any batch item left unanswered.

Usage:
    python scripts/upload_glosses.py --batch-file data/gloss_seeding/en_to_zh-ja/batch_001.json \\
        --glosses-file data/gloss_seeding/en_to_zh-ja/batch_001.glosses.json --dry-run
    python scripts/upload_glosses.py --batch-file ... --glosses-file ...

Glosses file format -- a list, or an object with a "glosses" list:
    [
      {"vocab_id": 4412, "sense_rank": 1,
       "glosses": {
         "zh": {"simple": "...", "standard": "..."},
         "ja": {"simple": "...", "standard": "..."}
       }},
      {"vocab_id": 4413, "sense_rank": 1, "skip": true, "reason": "proper noun"}
    ]

Options:
    --batch-file PATH    The exported batch this answers (defines legal keys).
    --glosses-file PATH  Generated glosses to apply.
    --dry-run            Report what would be written, write nothing.
    --skip-invalid       Drop invalid items and continue instead of aborting.
    --source-model NAME  Recorded in source_ref (default: claude-code:cross-language-glosses)
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
from services.vocabulary.language_detection import check_text_language

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_SOURCE_MODEL = 'claude-code:cross-language-glosses'
LEVELS = ('simple', 'standard')

# A `simple` gloss is a single best equivalent (緊張 -> "tension"); a `standard`
# gloss is a short equivalent set plus a clarifier only where the mapping is
# lossy (緊張 -> "tension; nervousness; strain -- being keyed up or on edge").
# Neither is a sentence-length definition -- that prose-instead-of-equivalent
# shape is exactly what made the old hosted prompt unusable (see
# services/vocabulary/gloss_generator.py). MAX_STANDARD_CHARS sits between the
# longest legitimate clarifier measured in that investigation (気's "no single
# English equivalent; covers mood, attention and intention", 90 chars) and the
# actual bloated-prose regression it needs to catch (the real ja->en output
# for 緊張, 142 chars) -- loose enough for a real clarifier, tight enough that
# a prompt regression back to prose fails this gate instead of shipping.
MAX_SIMPLE_CHARS = 60
MAX_STANDARD_CHARS = 120


class GlossUploadError(Exception):
    """A batch that cannot be applied safely."""


def check_gloss_shape(simple: str, standard: str) -> str | None:
    """Return a validation error string, or None if the pair is shaped right.

    Enforces the target format's two invariants: `simple` is the short single
    equivalent, and `standard` is longer (equivalent set + optional nuance)
    but still not a paragraph.
    """
    if len(simple) > MAX_SIMPLE_CHARS:
        return (f"`simple` is {len(simple)} chars (max {MAX_SIMPLE_CHARS}) -- "
                "should be the single best equivalent, not a sentence")
    if len(standard) > MAX_STANDARD_CHARS:
        return (f"`standard` is {len(standard)} chars (max {MAX_STANDARD_CHARS}) -- "
                "should be an equivalent set plus a short clarifier, not a paragraph")
    if len(standard) <= len(simple):
        return "`standard` must be longer than `simple` (equivalent set + nuance vs. one word)"
    return None


def load_glosses(path: str) -> list[dict]:
    with open(path, encoding='utf-8') as fh:
        payload = json.load(fh)
    if isinstance(payload, dict):
        payload = payload.get('glosses') or payload.get('items') or []
    if not isinstance(payload, list):
        raise GlossUploadError("Glosses file must be a list, or an object with a 'glosses' list")
    return payload


def validate(glosses: list[dict], batch: dict) -> tuple[list[dict], list[dict], list[str]]:
    """Split into (writable, skipped, errors).

    The batch file is the authority on which (vocab_id, sense_rank) keys are
    in play, and on which target languages each one still needs -- an id that
    was never exported, or a language nobody asked for, is rejected rather
    than looked up.
    """
    legal = {(item['vocab_id'], item['sense_rank']): item for item in batch['items']}
    source_lang = batch.get('source_language_code')

    writable: list[dict] = []
    skipped: list[dict] = []
    errors: list[str] = []
    seen: set[tuple[int, int]] = set()

    for i, g in enumerate(glosses):
        vocab_id = g.get('vocab_id')
        sense_rank = g.get('sense_rank')
        key = (vocab_id, sense_rank)
        label = f"vocab_id={vocab_id} rank={sense_rank}" if vocab_id is not None else f"#{i}"

        if key not in legal:
            errors.append(f"{label}: not in this batch")
            continue
        if key in seen:
            errors.append(f"{label}: appears twice")
            continue
        seen.add(key)
        item = legal[key]
        label = f"{item['lemma']} ({label})"

        if g.get('skip'):
            skipped.append({**g, 'lemma': item['lemma']})
            continue

        payload = g.get('glosses')
        if not isinstance(payload, dict) or not payload:
            errors.append(f"{label}: no `glosses` object")
            continue

        required = set(item['target_languages'])
        provided = set(payload.keys())

        unknown = provided - required
        if unknown:
            errors.append(
                f"{label}: target language(s) {sorted(unknown)} not requested for "
                f"this item (needs: {sorted(required)})")
            continue

        missing_required = required - provided
        if missing_required:
            errors.append(f"{label}: missing gloss for required target(s) {sorted(missing_required)}")
            continue

        item_errors = []
        for lang, texts in payload.items():
            if not isinstance(texts, dict):
                item_errors.append(f"{label} [{lang}]: not an object")
                continue
            simple = str(texts.get('simple') or '').strip()
            standard = str(texts.get('standard') or '').strip()
            if not simple or not standard:
                item_errors.append(
                    f"{label} [{lang}]: needs both `simple` and `standard` -- "
                    "a standard-only gloss is the drift the two-level treatment prevents")
                continue

            shape_error = check_gloss_shape(simple, standard)
            if shape_error:
                item_errors.append(f"{label} [{lang}]: {shape_error}")
                continue

            # ja and zh share a writing system, so for that pair alone an
            # identical (or overlapping) string in the gloss is often the
            # objectively correct answer, not laziness -- a Japanese "十" and
            # its Chinese gloss are the same character, and always will be.
            # Arabic numerals are shared even more widely -- "10" belongs in
            # an English gloss of the lemma "10" exactly as written. Only
            # check word-leak where neither of those applies, i.e. where a
            # verbatim survival of the source word is a real signal something
            # didn't get translated.
            lemma = item['lemma']
            shares_script = {source_lang, lang} <= {'zh', 'ja'} or lemma.strip().isdigit()
            if lemma and not shares_script and (lemma in simple or lemma in standard):
                item_errors.append(
                    f"{label} [{lang}]: gloss contains the source word {lemma!r} itself")
                continue

            for level, text in (('simple', simple), ('standard', standard)):
                ok, reason = check_text_language(text, lang)
                if not ok:
                    item_errors.append(
                        f"{label} [{lang}] {level}: failed {lang} language check ({reason})")

        if item_errors:
            errors.extend(item_errors)
            continue

        writable.append({
            'vocab_id': vocab_id,
            'sense_rank': sense_rank,
            'lemma': item['lemma'],
            'glosses': {lang: {'simple': str(texts['simple']).strip(),
                               'standard': str(texts['standard']).strip()}
                       for lang, texts in payload.items()},
        })

    missing = set(legal) - seen
    if missing:
        errors.append(
            f"{len(missing)} sense(s) in the batch got no answer: "
            + ', '.join(legal[k]['lemma'] for k in list(missing)[:10])
            + ('…' if len(missing) > 10 else '')
        )

    return writable, skipped, errors


def apply(db, batch: dict, writable: list[dict], args) -> dict:
    target_ids = batch['target_language_ids']
    source_ref = f'{args.source_model} v1'

    stats = {'written': 0, 'failed': 0, 'rows_written': 0}
    for entry in writable:
        rows = []
        for lang, texts in entry['glosses'].items():
            for level in LEVELS:
                rows.append({
                    'vocab_id': entry['vocab_id'],
                    'definition_language_id': target_ids[lang],
                    'definition_level': level,
                    'definition': texts[level],
                    'sense_rank': entry['sense_rank'],
                    'source': 'llm_gloss',
                    'source_ref': source_ref,
                })

        if args.dry_run:
            for lang, texts in entry['glosses'].items():
                logger.info(
                    "  [DRY RUN] %s (rank=%s, ->%s): simple=%r standard=%r",
                    entry['lemma'], entry['sense_rank'], lang,
                    texts['simple'][:80], texts['standard'][:80],
                )
            stats['written'] += 1
            stats['rows_written'] += len(rows)
            continue

        try:
            db.table('dim_word_senses') \
                .upsert(rows, on_conflict='vocab_id,definition_language_id,definition_level,sense_rank') \
                .execute()
            stats['written'] += 1
            stats['rows_written'] += len(rows)
        except Exception as e:
            logger.error("  %s: write failed: %s", entry['lemma'], e)
            stats['failed'] += 1

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--batch-file', required=True)
    parser.add_argument('--glosses-file', required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-invalid', action='store_true')
    parser.add_argument('--source-model', default=DEFAULT_SOURCE_MODEL)
    args = parser.parse_args()

    with open(args.batch_file, encoding='utf-8') as fh:
        batch = json.load(fh)

    try:
        glosses = load_glosses(args.glosses_file)
        writable, skipped, errors = validate(glosses, batch)

        if errors:
            for e in errors:
                logger.error("  invalid — %s", e)
            if not args.skip_invalid:
                raise GlossUploadError(
                    f"{len(errors)} problem(s); nothing written. Fix them, or "
                    "re-run with --skip-invalid to drop them."
                )
            logger.warning("--skip-invalid: continuing with %d item(s)", len(writable))

        db = get_supabase_admin()
        stats = apply(db, batch, writable, args)
    except GlossUploadError as e:
        logger.error(str(e))
        return 1

    prefix = '[DRY RUN] ' if args.dry_run else ''
    logger.info(
        "%sbatch %s/%s: %d sense(s) written (%d rows), %d skipped, %d failed",
        prefix, batch.get('batch'), batch.get('of'),
        stats['written'], stats['rows_written'], len(skipped), stats['failed'],
    )
    for s in skipped:
        logger.info("  skipped %s: %s", s['lemma'], s.get('reason') or '(no reason given)')

    return 0 if stats['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
