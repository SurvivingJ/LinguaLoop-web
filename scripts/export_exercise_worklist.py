#!/usr/bin/env python3
"""Export the vocabulary-ladder asset worklist for senses that have no exercises.

Two stages, because the ladder's prompts form a dependency chain: Prompt 2 and
Prompt 3 are both rendered *from* Prompt 1's output, so the core asset has to
exist before the exercise prompts can be built at all.

    --stage core       Senses with no exercises and no valid prompt1_core.
                       Emits the live `vocab_prompt1_core` prompt, already
                       seeded with the sense's mined corpus sentences.

    --stage exercises  Senses that now have a valid prompt1_core but still no
                       exercises. Emits the live `vocab_prompt2_exercises` and
                       `vocab_prompt3_transforms` prompts — plus the split L4 /
                       L8 prompts where their capability rows fire — once for
                       variant A and once for variant B.

Every prompt written into a batch file is rendered by the *real* generator
object against the live `prompt_templates` row, so what you answer is
byte-identical to what the production model would be sent, at the same
template version. Nothing here paraphrases a prompt.

Selection is ranked by how many active tests reference the sense — the same
ranking scripts/run_ladder_from_existing.py uses, reusing its helpers.

Usage:
    python scripts/export_exercise_worklist.py --language ja --stage core --limit 24
    python scripts/export_exercise_worklist.py --language ja --stage exercises

Options:
    --language CODE         Required. zh | en | ja
    --stage STAGE           Required. core | exercises
    --batch-size N          Senses per output file (default: 8 — one ladder
                             sense is roughly ten gloss items of writing)
    --limit N               Cap senses exported after filtering (0 = all)
    --include-unreferenced  Extend the pool past test-referenced senses (always
                             ranked first) to senses no active test uses
    --overwrite             Include senses that already have exercises
    --regenerate-core       stage=core: also re-export senses that already have
                             a valid prompt1_core, rebuilding it against the
                             current prompt version. Without this, a stale core
                             is invisible to stage=core forever.
    --sense-ids A,B,C       Export exactly these senses, bypassing the pool
    --out-dir PATH          Default: data/exercise_seeding/<lang>
"""

import os
import sys
import json
import argparse
import logging
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling scripts

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

from services.prompt_service import get_template_config
from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
from services.vocabulary_ladder.asset_generators._renderer import render_template
from services.vocabulary_ladder.asset_generators.prompt1_core import (
    CoreAssetGenerator, TASK_NAME as P1_TASK,
)
from services.vocabulary_ladder.asset_generators.prompt2_exercises import (
    ExerciseAssetGenerator, TASK_NAME as P2_TASK,
)
from services.vocabulary_ladder.asset_generators.prompt3_transforms import (
    TransformAssetGenerator, TASK_NAME as P3_TASK,
)
from services.vocabulary_ladder.asset_generators.l4_morphology import MorphologySlotGenerator
from services.vocabulary_ladder.asset_generators.l8_repair import CollocationRepairGenerator
from services.vocabulary_ladder.config import (
    LADDER_LEVELS, PROMPT2_LEVELS, PROMPT3_MONOLITH_LEVELS, SPLIT_LEVEL_TASKS,
    SENTENCE_ASSIGNMENTS_A, SENTENCE_ASSIGNMENTS_B,
    L7_CORRECT_INDICES_A, L7_CORRECT_INDICES_B,
    PROMPT1_KEY_MAP, SENTENCE_KEY_MAP, MORPH_FORM_KEY_MAP, OPTION_KEY_MAP,
    active_levels_for_context, normalize_semantic_class,
    prompt3_levels_for_context, get_validation_profile, get_sentence_target,
)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}
DEFAULT_BATCH_SIZE = 8

# Split-level generator classes, keyed by the level they own. Instantiated per
# language in main() so each carries its own prompt_templates row.
SPLIT_GENERATORS = {4: MorphologySlotGenerator, 8: CollocationRepairGenerator}


# ---------------------------------------------------------------------------
# Pool construction
# ---------------------------------------------------------------------------

def all_senses_for_language(db, language_id: int) -> list[int]:
    """Every dim_word_senses id whose word belongs to this language.

    Two hops: dim_word_senses has no language_id, so vocab is resolved first
    (the same shape run_exercise_generation.run_vocabulary_batch uses).
    """
    vocab_ids: list[int] = []
    offset = 0
    while True:
        page = (db.table('dim_vocabulary').select('id')
                  .eq('language_id', language_id)
                  .range(offset, offset + 999).execute().data or [])
        vocab_ids.extend(r['id'] for r in page)
        if len(page) < 1000:
            break
        offset += 1000

    sense_ids: list[int] = []
    for i in range(0, len(vocab_ids), 400):
        chunk = vocab_ids[i:i + 400]
        rows = (db.table('dim_word_senses').select('id')
                  .in_('vocab_id', chunk).execute().data or [])
        sense_ids.extend(r['id'] for r in rows)
    return sense_ids


def senses_with_exercises(db, sense_ids: list[int]) -> set[int]:
    """Subset that already has at least one row in `exercises`."""
    have: set[int] = set()
    for i in range(0, len(sense_ids), 300):
        chunk = sense_ids[i:i + 300]
        rows = (db.table('exercises').select('word_sense_id')
                  .in_('word_sense_id', chunk).execute().data or [])
        have.update(r['word_sense_id'] for r in rows if r.get('word_sense_id'))
    return have


def valid_core_assets(db, sense_ids: list[int]) -> dict[int, dict]:
    """sense_id -> prompt1_core content, for valid core assets only.

    An invalid core is deliberately excluded: rendering P2/P3 prompts from a
    core that failed validation is how half-built assets reach learners.
    """
    found: dict[int, dict] = {}
    for i in range(0, len(sense_ids), 200):
        chunk = sense_ids[i:i + 200]
        rows = (db.table('word_assets').select('sense_id, content')
                  .eq('asset_type', 'prompt1_core').eq('is_valid', True)
                  .in_('sense_id', chunk).execute().data or [])
        for r in rows:
            if isinstance(r.get('content'), dict):
                found[r['sense_id']] = r['content']
    return found


def rank_by_test_frequency(db, language_id: int) -> Counter:
    """How many active tests reference each sense. Reuses run_content_build."""
    import run_content_build as rcb  # sibling script, as run_ladder_from_existing does

    test_ids = [r['id'] for r in (
        db.table('tests').select('id')
          .eq('language_id', language_id).eq('is_active', True)
          .limit(2000).execute().data or []
    )]
    counts = rcb.sense_ids_for_tests(db, test_ids)
    logger.info("%d distinct senses referenced across %d active tests",
                len(counts), len(test_ids))
    return counts


def build_pool(db, language_id: int, counts: Counter, args) -> list[int]:
    """Senses to export, best first.

    Test-referenced senses come first, ordered by reference count; senses no
    active test uses are appended only when --include-unreferenced is given.
    """
    every = all_senses_for_language(db, language_id)
    logger.info("%d senses total for this language", len(every))

    with_ex = set() if args.overwrite else senses_with_exercises(db, every)
    logger.info("%d senses already have exercises%s",
                len(with_ex), " (ignored: --overwrite)" if args.overwrite else "")

    # TASK-767: a quarantined sense's dictionary row is known to be wrong, and
    # the exercises trigger would retire anything written for it.
    from services.vocabulary.sense_quarantine import quarantined_sense_ids
    quarantined = quarantined_sense_ids(db, every)
    if quarantined:
        logger.info("%d senses skipped as quarantined", len(quarantined))

    candidates = [s for s in every if s not in with_ex and s not in quarantined]
    candidate_set = set(candidates)

    ranked = [s for s, _ in counts.most_common() if s in candidate_set]
    logger.info("%d of them are referenced by at least one active test", len(ranked))

    if args.include_unreferenced:
        seen = set(ranked)
        ranked += [s for s in candidates if s not in seen]
        logger.info("--include-unreferenced: pool extended to %d", len(ranked))
    elif not ranked:
        logger.warning(
            "No candidate sense is referenced by an active test. Re-run with "
            "--include-unreferenced to seed senses no test uses yet.")

    return ranked


# ---------------------------------------------------------------------------
# Per-sense item builders
# ---------------------------------------------------------------------------

def build_core_item(pipeline, p1_gen, sense_id: int, language_id: int,
                    test_refs: int) -> dict | None:
    """One `stage=core` item: the filled vocab_prompt1_core prompt."""
    word = p1_gen._load_word_data(sense_id)
    if not word or not word.get('lemma'):
        logger.warning("sense %s: no word data — skipped", sense_id)
        return None

    corpus = pipeline._fetch_corpus_sentences(sense_id, language_id)
    needed = max(0, Config.VOCAB_SENTENCES_PER_WORD - len(corpus))

    prompt = p1_gen._build_prompt(
        word['lemma'], word.get('definition', ''),
        word.get('complexity_tier', 'T3'), corpus, needed, sense_id=sense_id,
    )
    return {
        'sense_id': sense_id,
        'lemma': word['lemma'],
        'existing_definition': word.get('definition', ''),
        'complexity_tier': word.get('complexity_tier', 'T3'),
        'tests_referencing': test_refs,
        # Kept so upload can tag sentence_source exactly as the pipeline does:
        # a sentence counts as 'mined' only if it comes back unchanged.
        'corpus_sentences': corpus,
        'sentences_needed': needed,
        'prompt': prompt,
    }


def build_exercise_item(pipeline, p2_gen, p3_gen, split_gens,
                        sense_id: int, language_id: int, core: dict,
                        test_refs: int) -> dict | None:
    """One `stage=exercises` item: the filled P2/P3 (+L4/L8) prompts, per variant.

    The level derivation mirrors VocabAssetPipeline._generate_for_sense_impl
    steps 2-3 exactly — matrix gating, the capability-requirements narrowing,
    and the L5 PMI gate — because the validator on upload is held to the same
    level list. Deriving it differently here would read back as "Missing
    level_N" on an otherwise-good asset.
    """
    semantic_class = normalize_semantic_class(core.get('semantic_class'))
    capability_context = pipeline._capability_context(core)
    active_levels = active_levels_for_context(
        semantic_class, language_id, capability_context,
    )
    if 5 in active_levels and not pipeline._collocation_is_fixed(core, language_id):
        active_levels = [lv for lv in active_levels if lv != 5]

    p3_expected = prompt3_levels_for_context(
        active_levels, semantic_class, language_id, capability_context,
    )
    split_levels = [lv for lv in p3_expected if lv in SPLIT_LEVEL_TASKS]

    p2_active = sorted(lv for lv in active_levels if lv in PROMPT2_LEVELS)
    p3_active = sorted(lv for lv in p3_expected if lv in PROMPT3_MONOLITH_LEVELS)

    if not p2_active and not p3_active and not split_levels:
        logger.info("sense %s: no LLM-authored levels active — skipped", sense_id)
        return None

    sentences = core.get('sentences') or []
    variants: dict[str, dict] = {}
    for key, assignments, l7_idx in (
        ('A', SENTENCE_ASSIGNMENTS_A, L7_CORRECT_INDICES_A),
        ('B', SENTENCE_ASSIGNMENTS_B, L7_CORRECT_INDICES_B),
    ):
        variant: dict = {
            'sentence_assignments': {str(k): v for k, v in assignments.items()},
        }

        if p2_active:
            variant['p2'] = {
                'levels': p2_active,
                # used_distractors is [] for both variants, matching the
                # pipeline: it submits each variant without threading the
                # other's distractors through.
                'prompt': p2_gen._build_prompt(core, p2_active, assignments, []),
            }
        if p3_active:
            variant['p3'] = {
                'levels': p3_active,
                'l7_correct_indices': l7_idx,
                'prompt': p3_gen._build_prompt(core, p3_active, assignments, l7_idx, []),
            }
        for level in split_levels:
            gen = split_gens[level]
            idx = gen._sentence_index(core, assignments)
            if idx is None:
                # The generator would clean-skip this level for this sense too.
                continue
            variant[f'l{level}'] = {
                'level': level,
                'type_code': gen.TYPE_CODE,
                'prompt_version': gen.prompt_version,
                'sentence_index': idx,
                'prompt': render_template(
                    gen.cfg['template'], **gen._prompt_vars(core, idx, []),
                ),
            }
        variants[key] = variant

    return {
        'sense_id': sense_id,
        'lemma': get_sentence_target(sentences[0]) if sentences else '',
        'tests_referencing': test_refs,
        'semantic_class': semantic_class,
        'active_levels': active_levels,
        'p2_levels': p2_active,
        'p3_expected_levels': p3_expected,
        'level_names': {str(lv): LADDER_LEVELS[lv]['name']
                        for lv in active_levels if lv in LADDER_LEVELS},
        'variants': variants,
    }


# ---------------------------------------------------------------------------
# Batch headers
# ---------------------------------------------------------------------------

def core_header(db, language_id: int) -> dict:
    cfg = get_template_config(db, P1_TASK, language_id)
    profile = get_validation_profile(language_id)
    return {
        'prompts': {P1_TASK: {'version': cfg['version'],
                              'model_of_record': cfg['model'],
                              'provider': cfg['provider']}},
        'answer_contract': {
            'top_level': PROMPT1_KEY_MAP,
            'sentences': SENTENCE_KEY_MAP,
            'morphological_forms': MORPH_FORM_KEY_MAP,
        },
        'validation': {
            'sentences_required': Config.VOCAB_SENTENCES_PER_WORD,
            'pos_set': sorted(profile.pos_set),
            'semantic_class_set': sorted(profile.semantic_class_set),
            'min_morphological_forms': profile.min_morphological_forms,
            'ipa_required': profile.ipa_required,
        },
    }


def exercise_header(db, language_id: int) -> dict:
    prompts = {}
    for task in (P2_TASK, P3_TASK, *SPLIT_LEVEL_TASKS.values()):
        try:
            cfg = get_template_config(db, task, language_id)
            prompts[task] = {'version': cfg['version'],
                             'model_of_record': cfg['model'],
                             'provider': cfg['provider']}
        except Exception as exc:
            prompts[task] = {'error': str(exc)}
    return {
        'prompts': prompts,
        'answer_contract': {
            'p2_p3_options': OPTION_KEY_MAP,
            'note': ('P2/P3 use the 1-based option numbering above; the split '
                     'L4/L8 prompts use their own 0-based contract '
                     '(0=options, 9=error escape) and are schema-gated on '
                     'upload against their prompt_version.'),
        },
    }


# ---------------------------------------------------------------------------

def write_batches(items: list[dict], header: dict, out_dir: str,
                  batch_size: int, stage: str, language: str,
                  language_id: int) -> int:
    os.makedirs(out_dir, exist_ok=True)
    written = 0
    for i in range(0, len(items), batch_size):
        written += 1
        chunk = items[i:i + batch_size]
        path = os.path.join(out_dir, f'batch_{written:03d}.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump({
                'stage': stage,
                'language': language,
                'language_id': language_id,
                'batch': written,
                'count': len(chunk),
                **header,
                'items': chunk,
            }, fh, ensure_ascii=False, indent=2)
        logger.info("wrote %s (%d senses)", path, len(chunk))
    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language', required=True, choices=['zh', 'en', 'ja'])
    parser.add_argument('--stage', required=True, choices=['core', 'exercises'])
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--include-unreferenced', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--regenerate-core', action='store_true',
                        help='stage=core: also re-export senses that already '
                             'have a valid prompt1_core, to rebuild it against '
                             'the current prompt version')
    parser.add_argument('--sense-ids',
                        help='comma-separated sense ids to export, bypassing '
                             'the ranked pool entirely')
    parser.add_argument('--out-dir')
    args = parser.parse_args()

    db = get_supabase_admin()
    language_id = LANG_ID[args.language]

    counts = rank_by_test_frequency(db, language_id)

    if args.sense_ids:
        pool = [int(s) for s in args.sense_ids.split(',') if s.strip()]
        logger.info("--sense-ids: exporting %d named sense(s), pool filters "
                    "bypassed", len(pool))
    else:
        pool = build_pool(db, language_id, counts, args)
    if not pool:
        logger.info("Nothing to export.")
        return 0

    cores = valid_core_assets(db, pool)
    if args.stage == 'core':
        if args.regenerate_core or args.sense_ids:
            # Re-authoring an existing core is the only way to fix an asset
            # generated under an older prompt version: validation runs at write
            # time, so a stale core sits in word_assets unchallenged forever.
            selected = list(pool)
            logger.info("%d sense(s) selected; %d of them already have a valid "
                        "prompt1_core and will be rebuilt",
                        len(selected), sum(1 for s in selected if s in cores))
        else:
            selected = [s for s in pool if s not in cores]
            logger.info("%d senses have a valid prompt1_core already (they "
                        "belong to --stage exercises, or pass "
                        "--regenerate-core to rebuild them); %d need one",
                        len(pool) - len(selected), len(selected))
    else:
        selected = [s for s in pool if s in cores]
        logger.info("%d of the pool have a valid prompt1_core and can be "
                    "exercised now; %d still need --stage core first",
                    len(selected), len(pool) - len(selected))

    if not selected:
        logger.info("Nothing to export for stage=%s.", args.stage)
        return 0

    if args.limit:
        selected = selected[:args.limit]
    logger.info("Exporting %d senses (stage=%s)", len(selected), args.stage)

    pipeline = VocabAssetPipeline(db)
    items: list[dict] = []

    if args.stage == 'core':
        p1_gen = CoreAssetGenerator(db, language_id)
        header = core_header(db, language_id)
        for n, sense_id in enumerate(selected, 1):
            logger.info("[%d/%d] core prompt for sense %s", n, len(selected), sense_id)
            item = build_core_item(pipeline, p1_gen, sense_id, language_id,
                                   counts.get(sense_id, 0))
            if item:
                items.append(item)
    else:
        p2_gen = ExerciseAssetGenerator(db, language_id)
        p3_gen = TransformAssetGenerator(db, language_id)
        split_gens = {lv: cls(db, language_id) for lv, cls in SPLIT_GENERATORS.items()}
        header = exercise_header(db, language_id)
        for n, sense_id in enumerate(selected, 1):
            logger.info("[%d/%d] exercise prompts for sense %s", n, len(selected), sense_id)
            try:
                item = build_exercise_item(
                    pipeline, p2_gen, p3_gen, split_gens,
                    sense_id, language_id, cores[sense_id], counts.get(sense_id, 0),
                )
            except Exception as exc:
                logger.error("sense %s: prompt build failed: %s", sense_id, exc)
                continue
            if item:
                items.append(item)

    if not items:
        logger.warning("No items built — nothing written.")
        return 1

    out_dir = args.out_dir or os.path.join(ROOT, 'data', 'exercise_seeding', args.language)
    n = write_batches(items, header, out_dir, args.batch_size,
                      args.stage, args.language, language_id)
    logger.info("Done: %d senses across %d batch file(s) in %s",
                len(items), n, out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
