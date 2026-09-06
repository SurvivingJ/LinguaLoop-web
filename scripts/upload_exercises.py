#!/usr/bin/env python3
"""Write hand-authored ladder assets back through the real asset write path.

The companion to scripts/export_exercise_worklist.py. Answers are the *raw
numeric-keyed JSON the exported prompt asks for* — exactly what the production
model would return — so this script does the same remapping, the same
deterministic post-processing and the same validation the pipeline does, and
then stores through `word_assets`.

    --stage core       Remaps via PROMPT1_KEY_MAP, derives `sentence_source`,
                       screens the sentences against the tier gate, grades the
                       collocate, validates with VocabAssetValidator, and
                       upserts `prompt1_core`. Also writes POS / semantic_class
                       / phonetics back to dim_vocabulary and dim_word_senses,
                       as VocabAssetPipeline does.

    --stage exercises  Remaps P2 and P3, schema-gates and remaps the split
                       L4 / L8 fragments, merges the P3 family into one
                       `prompt3_transforms_<variant>` asset (the shape the
                       renderer reads), validates each, upserts them, then
                       renders `exercises` rows via LadderExerciseRenderer.

Validation is fail-closed for the whole batch: nothing is written if any sense
fails, so a batch is never half-applied. --skip-invalid drops the offending
senses and continues — for senses you have decided to abandon, not for an
error you have not read.

No LLM calls are made by this script. The judges the automated pipeline runs
are deliberately not invoked: in this workflow you are the quality step.

Usage:
    python scripts/upload_exercises.py --stage core \\
        --batch-file data/exercise_seeding/ja/batch_001.json \\
        --answers-file data/exercise_seeding/ja/batch_001.core.json --dry-run

    python scripts/upload_exercises.py --stage exercises \\
        --batch-file data/exercise_seeding/ja/batch_001.json \\
        --answers-file data/exercise_seeding/ja/batch_001.exercises.json
"""

import os
import sys
import json
import uuid
import argparse
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

from services.exercise_generation.schemas import (
    SchemaError, error_escape, validate_ladder_output,
)
from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
from services.vocabulary_ladder.asset_generators.prompt1_core import CoreAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt2_exercises import ExerciseAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt3_transforms import TransformAssetGenerator
from services.vocabulary_ladder.asset_generators.l4_morphology import MorphologySlotGenerator
from services.vocabulary_ladder.asset_generators.l8_repair import CollocationRepairGenerator
from services.vocabulary_ladder.collocation_grounding import (
    GROUNDING_ASSERTED, ground_core_asset,
)
from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer
from services.vocabulary_ladder.tier_gate import screen_sentences, tier_for_lemma
from services.vocabulary_ladder.validators import VocabAssetValidator

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_SOURCE_MODEL = 'claude-code:batch-exercise-generation'
SPLIT_GENERATORS = {4: MorphologySlotGenerator, 8: CollocationRepairGenerator}


class UploadError(Exception):
    """A batch-level problem that must stop the run before any write."""


def load_json(path: str):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def index_answers(answers, batch: dict, stage: str) -> dict[int, dict]:
    """Answers keyed by sense_id, with the every-item rule enforced.

    A dropped sense looks identical to a sense you decided against, so silence
    is rejected rather than skipped — the same rule upload_senses and
    upload_glosses apply.
    """
    if not isinstance(answers, list):
        raise UploadError("answers file must be a JSON array")

    expected = {it['sense_id'] for it in batch['items']}
    seen: dict[int, dict] = {}

    for entry in answers:
        if not isinstance(entry, dict):
            raise UploadError(f"answer entry is not an object: {entry!r}")
        sid = entry.get('sense_id')
        if sid is None:
            raise UploadError(f"answer entry has no sense_id: {entry!r}")
        if sid not in expected:
            raise UploadError(
                f"sense_id {sid} is not in this batch — never invent a "
                f"sense_id, a plausible wrong one writes assets onto an "
                f"unrelated word")
        if sid in seen:
            raise UploadError(f"duplicate answer for sense_id {sid}")
        seen[sid] = entry

    missing = sorted(expected - set(seen))
    if missing:
        raise UploadError(
            f"{len(missing)} sense(s) left unanswered: {missing[:10]}"
            f"{' …' if len(missing) > 10 else ''}. Every item needs an answer "
            f"or an explicit skip.")

    if batch.get('stage') != stage:
        raise UploadError(
            f"batch file is stage={batch.get('stage')!r} but --stage {stage} "
            f"was given")
    return seen


# ---------------------------------------------------------------------------
# Stage: core
# ---------------------------------------------------------------------------

def prepare_core(db, batch: dict, answers: dict[int, dict]) -> tuple[list[dict], list[dict]]:
    """Remap, post-process and validate every core answer. No writes."""
    language_id = batch['language_id']
    validator = VocabAssetValidator()
    p1_gen = CoreAssetGenerator(db, language_id)

    ready: list[dict] = []
    failed: list[dict] = []

    for item in batch['items']:
        sid = item['sense_id']
        entry = answers[sid]

        if entry.get('skip'):
            logger.info("sense %s (%s): skipped — %s", sid, item.get('lemma'),
                        entry.get('reason') or 'no reason given')
            continue

        raw = entry.get('answer')
        if not isinstance(raw, dict):
            failed.append({'sense_id': sid, 'errors': [
                "no 'answer' object (give the raw numeric-keyed JSON the "
                "prompt asks for, or set skip:true)"]})
            continue

        content = p1_gen._remap_output(raw)
        if content is None:
            failed.append({'sense_id': sid, 'errors': ['key remapping failed']})
            continue

        # Same derivation the generator does: a lightly-rewritten mined
        # sentence has, for provenance purposes, been generated.
        p1_gen._tag_sentence_sources(content, item.get('corpus_sentences') or [])

        valid, errors, warnings = validator.validate_prompt1(content, language_id)

        # Deterministic screens the pipeline also runs. Reported, never
        # repaired here — repair is an LLM call, and in this workflow a
        # misfit sentence is something you rewrite yourself.
        lemma = item.get('lemma') or ''
        tier = tier_for_lemma(lemma, language_id)
        for i, verdict in enumerate(
            screen_sentences(content.get('sentences') or [], language_id, tier, lemma)
        ):
            if not verdict.passed:
                warnings.append(f"sentence {i} above tier {tier}: {verdict.reason}")

        grounding = ground_core_asset(content, language_id, db)
        if grounding.status == GROUNDING_ASSERTED:
            warnings.append(
                f"collocate {content.get('primary_collocate')!r} is "
                f"llm_asserted — {grounding.reason}")

        if not valid:
            failed.append({'sense_id': sid, 'errors': errors})
            continue

        ready.append({'sense_id': sid, 'lemma': lemma, 'content': content,
                      'warnings': warnings})

    return ready, failed


def apply_core(db, batch: dict, ready: list[dict], args) -> dict:
    language_id = batch['language_id']
    pipeline = VocabAssetPipeline(db)
    batch_id = str(uuid.uuid4())
    written = 0

    for row in ready:
        sid, content = row['sense_id'], row['content']
        n_sent = len(content.get('sentences') or [])
        logger.info("sense %s (%s): %s / %s, %d sentences%s",
                    sid, row['lemma'], content.get('pos'),
                    content.get('semantic_class'), n_sent,
                    f", {len(row['warnings'])} warning(s)" if row['warnings'] else '')
        for w in row['warnings']:
            logger.info("    warning: %s", w)

        if args.dry_run:
            continue

        pipeline._store_asset(
            sid, language_id, 'prompt1_core', content,
            args.source_model, batch_id,
            validation_warnings=row['warnings'] or None,
        )
        pipeline._update_vocabulary_metadata(sid, content)
        written += 1

    return {'batch_id': batch_id, 'written': written}


# ---------------------------------------------------------------------------
# Stage: exercises
# ---------------------------------------------------------------------------

def _remap_split(gen, raw, level: int, sentence_index: int,
                 prompt_version: int, errors: list[str]) -> dict:
    """Schema-gate one L4/L8 answer and remap it, or record why it was dropped.

    Returns {} for a clean skip (the model's own error escape, or a payload the
    gate refuses) so the rest of the P3 family still lands — the split levels
    exist precisely so one level's failure does not cost the others.
    """
    try:
        schema_errors = validate_ladder_output(gen.TYPE_CODE, int(prompt_version), raw)
    except SchemaError as exc:
        errors.append(f"L{level}: {exc}")
        return {}
    if schema_errors:
        errors.append(f"L{level} schema: {'; '.join(schema_errors[:4])}")
        return {}

    declined = error_escape(raw)
    if declined:
        logger.info("    L%d declined in the answer: %s", level, declined)
        return {}

    return {f'level_{level}': gen._remap(raw, sentence_index)}


def prepare_exercises(db, batch: dict, answers: dict[int, dict]) -> tuple[list[dict], list[dict]]:
    """Remap and validate every exercise answer, both variants. No writes."""
    language_id = batch['language_id']
    validator = VocabAssetValidator()
    p2_gen = ExerciseAssetGenerator(db, language_id)
    p3_gen = TransformAssetGenerator(db, language_id)
    split_gens = {lv: cls(db, language_id) for lv, cls in SPLIT_GENERATORS.items()}

    ready: list[dict] = []
    failed: list[dict] = []

    for item in batch['items']:
        sid = item['sense_id']
        entry = answers[sid]

        if entry.get('skip'):
            logger.info("sense %s (%s): skipped — %s", sid, item.get('lemma'),
                        entry.get('reason') or 'no reason given')
            continue

        active_levels = item['active_levels']
        p3_expected = item['p3_expected_levels']
        errors: list[str] = []
        assets: dict[str, dict] = {}

        for variant_key, variant in item['variants'].items():
            answer = entry.get(variant_key)
            if not isinstance(answer, dict):
                errors.append(f"variant {variant_key}: missing answer object")
                continue

            assignments = {int(k): v for k, v in variant['sentence_assignments'].items()}

            if 'p2' in variant:
                raw_p2 = answer.get('p2')
                if not isinstance(raw_p2, dict):
                    errors.append(f"[{variant_key}] missing p2 answer")
                else:
                    p2_asset = p2_gen._remap_output(
                        raw_p2, variant['p2']['levels'], assignments)
                    ok, errs = validator.validate_prompt2(p2_asset, active_levels)
                    if not ok:
                        errors.extend(f"[{variant_key}] {e}" for e in errs)
                    assets[f'prompt2_exercises_{variant_key}'] = p2_asset

            # The P3 family: the monolith's level_7 plus the split fragments,
            # merged into ONE asset. The renderer and validator read the
            # pre-split shape, so the split stays invisible downstream.
            p3_asset: dict | None = None
            if 'p3' in variant:
                raw_p3 = answer.get('p3')
                if not isinstance(raw_p3, dict):
                    errors.append(f"[{variant_key}] missing p3 answer")
                else:
                    p3_asset = p3_gen._remap_output(raw_p3, variant['p3']['levels'])

            for level in (4, 8):
                spec = variant.get(f'l{level}')
                if not spec:
                    continue
                raw_split = answer.get(f'l{level}')
                if not isinstance(raw_split, dict):
                    errors.append(f"[{variant_key}] missing l{level} answer")
                    continue
                split_errors: list[str] = []
                fragment = _remap_split(
                    split_gens[level], raw_split, level,
                    spec['sentence_index'], spec['prompt_version'], split_errors)
                errors.extend(f"[{variant_key}] {e}" for e in split_errors)
                if fragment:
                    p3_asset = {**(p3_asset or {}), **fragment}

            if p3_asset is not None:
                ok, errs = validator.validate_prompt3(p3_asset, p3_expected)
                if not ok:
                    errors.extend(f"[{variant_key}] {e}" for e in errs)
                assets[f'prompt3_transforms_{variant_key}'] = p3_asset

        if errors:
            failed.append({'sense_id': sid, 'errors': errors})
            continue
        if not assets:
            failed.append({'sense_id': sid,
                           'errors': ['no assets produced from the answer']})
            continue

        ready.append({'sense_id': sid, 'lemma': item.get('lemma'),
                      'assets': assets, 'active_levels': active_levels})

    return ready, failed


def apply_exercises(db, batch: dict, ready: list[dict], args) -> dict:
    language_id = batch['language_id']
    pipeline = VocabAssetPipeline(db)
    renderer = LadderExerciseRenderer(db)
    batch_id = str(uuid.uuid4())
    written = rendered = 0

    for row in ready:
        sid = row['sense_id']
        logger.info("sense %s (%s): %s", sid, row['lemma'],
                    ', '.join(sorted(row['assets'])))
        for asset_type, content in sorted(row['assets'].items()):
            logger.info("    %s: %s", asset_type, ', '.join(sorted(content)) or '(empty)')

        if args.dry_run:
            continue

        for asset_type, content in row['assets'].items():
            pipeline._store_asset(sid, language_id, asset_type, content,
                                  args.source_model, batch_id)
            written += 1

        if args.no_render:
            continue
        ids = renderer.render_all(sid, language_id)
        rendered += len(ids)
        if not ids:
            logger.warning("    rendered 0 exercises — check the core asset")
        else:
            logger.info("    rendered %d exercises", len(ids))

    return {'batch_id': batch_id, 'written': written, 'rendered': rendered}


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--stage', required=True, choices=['core', 'exercises'])
    parser.add_argument('--batch-file', required=True)
    parser.add_argument('--answers-file', required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-invalid', action='store_true')
    parser.add_argument('--no-render', action='store_true',
                        help='stage=exercises: store assets without rendering '
                             'exercise rows')
    parser.add_argument('--source-model', default=DEFAULT_SOURCE_MODEL)
    args = parser.parse_args()

    db = get_supabase_admin()
    batch = load_json(args.batch_file)

    try:
        answers = index_answers(load_json(args.answers_file), batch, args.stage)
    except UploadError as exc:
        logger.error("Batch rejected: %s", exc)
        return 1

    prepare = prepare_core if args.stage == 'core' else prepare_exercises
    ready, failed = prepare(db, batch, answers)

    if failed:
        logger.error("%d sense(s) failed validation:", len(failed))
        for row in failed:
            logger.error("  sense %s:", row['sense_id'])
            for err in row['errors']:
                logger.error("      %s", err)
        if not args.skip_invalid:
            logger.error("Nothing written. Fix the answers file and re-run, or "
                         "pass --skip-invalid to abandon these senses.")
            return 1
        logger.warning("--skip-invalid: continuing with %d valid sense(s)", len(ready))

    if not ready:
        logger.info("Nothing to write.")
        return 0

    apply_fn = apply_core if args.stage == 'core' else apply_exercises
    summary = apply_fn(db, batch, ready, args)

    if args.dry_run:
        logger.info("DRY RUN — %d sense(s) would be written. Nothing changed.",
                    len(ready))
    else:
        logger.info("Wrote %d asset(s) for %d sense(s) (batch %s)%s",
                    summary['written'], len(ready), summary['batch_id'],
                    f", rendered {summary['rendered']} exercises"
                    if 'rendered' in summary else '')
    return 0


if __name__ == '__main__':
    sys.exit(main())
