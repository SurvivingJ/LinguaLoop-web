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
from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline, mine_sentences
from services.vocabulary_ladder.asset_generators import typed_llm
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
        # Same-language senses only: a cross-language gloss shares the vocab_id
        # and would otherwise be exported (and exercised) as a second sense.
        rows = (db.table('dim_word_senses').select('id')
                  .in_('vocab_id', chunk)
                  .eq('definition_language_id', language_id)
                  .execute().data or [])
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

def fetch_sense_test_rows(db, sense_ids: list[int], language_id: int,
                          chunk_size: int = 50) -> dict[int, list[dict]]:
    """``tests_containing_sense`` for many senses in a few queries.

    Same predicate as the RPC (active tests of this language whose
    ``vocab_sense_ids`` contain the sense) and the same columns, so the rows
    can go straight into ``mine_sentences``. Each sense's rows keep the order
    the query returned them in; scripts/verify_mining_split.py checks that
    this order matches the per-sense RPC, because mining stops at the cap.
    """
    wanted = set(sense_ids)
    by_sense: dict[int, list[dict]] = {s: [] for s in sense_ids}
    seen_tests: set = set()
    for i in range(0, len(sense_ids), chunk_size):
        chunk = sense_ids[i:i + chunk_size]
        offset = 0
        while True:
            page = (db.table('tests')
                      .select('id, transcript, difficulty, vocab_token_map, vocab_sense_ids')
                      .eq('language_id', language_id).eq('is_active', True)
                      .overlaps('vocab_sense_ids', [str(s) for s in chunk])
                      .range(offset, offset + 999).execute().data or [])
            for row in page:
                if row['id'] in seen_tests:
                    continue  # already assigned by an earlier chunk
                seen_tests.add(row['id'])
                hit = {'id': row['id'], 'transcript': row.get('transcript'),
                       'difficulty': row.get('difficulty'),
                       'vocab_token_map': row.get('vocab_token_map')}
                for sid in (row.get('vocab_sense_ids') or []):
                    if sid in wanted:
                        by_sense[sid].append(hit)
            if len(page) < 1000:
                break
            offset += 1000
    return by_sense


def build_core_item(pipeline, p1_gen, sense_id: int, language_id: int,
                    test_refs: int, test_rows: list[dict] | None = None) -> dict | None:
    """One `stage=core` item: the filled vocab_prompt1_core prompt.

    ``test_rows`` (from :func:`fetch_sense_test_rows`) skips the per-sense
    RPC; the mining itself is the pipeline's own ``mine_sentences`` either way.
    """
    word = p1_gen._load_word_data(sense_id)
    if not word or not word.get('lemma'):
        logger.warning("sense %s: no word data — skipped", sense_id)
        return None

    if test_rows is None:
        corpus = pipeline._fetch_corpus_sentences(sense_id, language_id)
    else:
        corpus = mine_sentences(test_rows, word['lemma'].strip(), sense_id, language_id)
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


def typed_generators_for(db, language_id: int, semantic_class: str | None,
                         capability_context: dict) -> dict:
    """type_code -> typed LLM generator, for the types this word gets.

    ``typed_llm.applicable_types`` is the same matrix walk the pipeline's
    ``generate_all`` does, so the set here is the set the pipeline would run.
    """
    return {
        cap['type_code']: typed_llm.generator_class(cap['type_code'])(db, language_id)
        for cap in typed_llm.applicable_types(language_id, semantic_class,
                                              capability_context)
    }


def build_exercise_item(pipeline, p2_gen, p3_gen, split_gens,
                        sense_id: int, language_id: int, core: dict,
                        test_refs: int, include_typed: bool = False) -> dict | None:
    """One `stage=exercises` item: the filled P2/P3 (+L4/L8) prompts, per variant.

    The level derivation mirrors VocabAssetPipeline._generate_for_sense_impl
    steps 2-3 exactly — matrix gating, the capability-requirements narrowing,
    and the L5 PMI gate — because the validator on upload is held to the same
    level list. Deriving it differently here would read back as "Missing
    level_N" on an otherwise-good asset.

    ``include_typed`` adds a ``typed`` block per variant: the typed LLM prompts
    (syn/ant, word family, particle selection) the pipeline's
    ``typed_llm.generate_all`` would run, stored on upload as ``llm_types_<v>``.
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

    typed_gens = (typed_generators_for(pipeline.db, language_id, semantic_class,
                                       capability_context)
                  if include_typed else {})

    if not p2_active and not p3_active and not split_levels and not typed_gens:
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
        if include_typed:
            # Always present, even empty: upload stores an empty llm_types_<v>
            # asset, which the renderer reads as "no applicable types" rather
            # than "never generated" (the pipeline does the same).
            typed: dict = {}
            for type_code, gen in typed_gens.items():
                idx = gen._sentence_index(core, assignments)
                if idx is None:
                    continue  # generate() would clean-skip this type too
                typed[type_code] = {
                    'type_code': type_code,
                    'task_name': gen.TASK_NAME,
                    'prompt_version': gen.prompt_version,
                    'sentence_index': idx,
                    'prompt': render_template(
                        gen.cfg['template'], **gen._prompt_vars(core, idx, []),
                    ),
                }
            variant['typed'] = typed
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


def typed_task_names() -> list[str]:
    return sorted(typed_llm.generator_class(t).TASK_NAME
                  for t in typed_llm.registered_types())


def exercise_header(db, language_id: int) -> dict:
    prompts = {}
    for task in (P2_TASK, P3_TASK, *SPLIT_LEVEL_TASKS.values(), *typed_task_names()):
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


# ---------------------------------------------------------------------------
# --format csv: stage 0 of CSV exercise authoring (TASK-796)
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    'sense_id', 'lemma', 'reading', 'part_of_speech', 'definition',
    'zipf', 'level_tag', 'semantic_class', 'complexity_tier', 'blocks_n_tests',
    'surface_tokens', 'corpus_sentences', 'n_mined', 'sentences_needed',
    'sentences_required', 'pos_set', 'semantic_class_enum', 'prompt_version',
    'p1_prompt',
]


def judge_task_names() -> list[str]:
    """prompt_templates names of the ladder judges, read off the judge modules
    so a renamed template cannot leave a stale copy here."""
    from services.exercise_generation.judges import (
        collocation, l1_distractor, p1_sentences, particle, relation,
        sentence_validity,
    )
    return [p1_sentences._PT_NAME, sentence_validity._PT_NAME,
            l1_distractor._PT_NAME, collocation._PT_NAME,
            relation._RELATION_PT, relation._FAMILY_PT, particle._PT_NAME]


def prompts_manifest(db, language_id: int) -> dict:
    """Every prompt the staged chain uses, version-pinned, template included."""
    tasks = [P1_TASK, P2_TASK, P3_TASK, *SPLIT_LEVEL_TASKS.values(),
             *typed_task_names(), *judge_task_names()]
    manifest: dict = {}
    for task in tasks:
        try:
            cfg = get_template_config(db, task, language_id)
            manifest[task] = {'version': cfg['version'], 'model_of_record': cfg['model'],
                              'provider': cfg['provider'], 'template': cfg['template']}
        except Exception as exc:
            manifest[task] = {'error': str(exc)}
    return manifest


def vocab_extras(db, sense_ids: list[int], language_id: int) -> dict[int, dict]:
    """reading / zipf / semantic_class etc. for each sense, same-language rows only."""
    out: dict[int, dict] = {}
    for i in range(0, len(sense_ids), 200):
        rows = (db.table('dim_word_senses')
                  .select('id, dim_vocabulary(reading, part_of_speech, frequency_rank, '
                          'level_tag, semantic_class)')
                  .in_('id', sense_ids[i:i + 200])
                  .eq('definition_language_id', language_id)
                  .execute().data or [])
        for r in rows:
            out[r['id']] = r.get('dim_vocabulary') or {}
    return out


def build_csv_rows(db, pipeline, p1_gen, selected: list[int], language_id: int,
                   counts: Counter, header: dict) -> list[dict]:
    test_rows = fetch_sense_test_rows(db, selected, language_id)
    extras = vocab_extras(db, selected, language_id)
    validation = header['validation']
    p1_version = header['prompts'][P1_TASK]['version']
    as_json = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731

    rows: list[dict] = []
    for n, sid in enumerate(selected, 1):
        logger.info("[%d/%d] csv row for sense %s", n, len(selected), sid)
        if sid not in extras:
            logger.warning("sense %s: not a same-language sense — skipped", sid)
            continue
        item = build_core_item(pipeline, p1_gen, sid, language_id,
                               counts.get(sid, 0), test_rows=test_rows.get(sid, []))
        if not item:
            continue
        surface: list[str] = []
        for row in test_rows.get(sid, []):
            for tok in VocabAssetPipeline._sense_surface_tokens(
                    row.get('vocab_token_map'), sid):
                if tok not in surface:
                    surface.append(tok)
        vx = extras[sid]
        rows.append({
            'sense_id': sid,
            'lemma': item['lemma'],
            'reading': vx.get('reading') or '',
            'part_of_speech': vx.get('part_of_speech') or '',
            'definition': item['existing_definition'],
            'zipf': vx.get('frequency_rank'),
            'level_tag': vx.get('level_tag') or '',
            'semantic_class': vx.get('semantic_class') or '',
            'complexity_tier': item['complexity_tier'],
            'blocks_n_tests': item['tests_referencing'],
            'surface_tokens': as_json(surface),
            'corpus_sentences': as_json(item['corpus_sentences']),
            'n_mined': len(item['corpus_sentences']),
            'sentences_needed': item['sentences_needed'],
            'sentences_required': validation['sentences_required'],
            'pos_set': as_json(validation['pos_set']),
            'semantic_class_enum': as_json(validation['semantic_class_set']),
            'prompt_version': p1_version,
            'p1_prompt': item['prompt'],
        })
    return rows


def write_csv_run(rows: list[dict], header: dict, manifest: dict, out_dir: str,
                  language: str, language_id: int) -> str:
    import csv
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'senses.csv')
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with open(os.path.join(out_dir, 'prompts.json'), 'w', encoding='utf-8') as fh:
        json.dump({'language': language, 'language_id': language_id,
                   'answer_contract': header['answer_contract'],
                   'validation': header['validation'],
                   'prompts': manifest}, fh, ensure_ascii=False, indent=2)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language', required=True, choices=['zh', 'en', 'ja'])
    parser.add_argument('--stage', choices=['core', 'exercises'],
                        help='required unless --format csv (which is stage 0 '
                             'of CSV authoring and selects like --stage core)')
    parser.add_argument('--format', choices=['json', 'csv'], default='json',
                        help='csv: write senses.csv + prompts.json for the '
                             'staged CSV authoring chain '
                             '(scripts/exercise_stage_runner.py)')
    parser.add_argument('--include-typed', action='store_true',
                        help='stage=exercises: also export the typed LLM '
                             'prompts (syn/ant, word family, particle)')
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
    if args.format == 'csv':
        if args.stage == 'exercises':
            parser.error('--format csv is stage 0 of CSV authoring; the '
                         'exercise prompts are rendered later by the stage '
                         'runner\'s bridge step')
        args.stage = 'core'
    elif not args.stage:
        parser.error('--stage is required')

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

    if args.format == 'csv':
        from datetime import datetime
        p1_gen = CoreAssetGenerator(db, language_id)
        header = core_header(db, language_id)
        rows = build_csv_rows(db, pipeline, p1_gen, selected, language_id,
                              counts, header)
        if not rows:
            logger.warning("No rows built — nothing written.")
            return 1
        out_dir = args.out_dir or os.path.join(
            ROOT, 'data', 'exercise_seeding', args.language,
            f"run_{datetime.now():%Y%m%d_%H%M%S}")
        path = write_csv_run(rows, header, prompts_manifest(db, language_id),
                             out_dir, args.language, language_id)
        logger.info("Done: %d senses -> %s (+ prompts.json). Next: "
                    "python scripts/exercise_stage_runner.py prepare %s --stage 1",
                    len(rows), path, out_dir)
        return 0

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
                    include_typed=args.include_typed,
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
