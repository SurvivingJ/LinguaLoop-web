#!/usr/bin/env python3
"""Fat-seed exercise authoring: one JSON per word, one review pass, then upload.

The cheap/fast sibling of the staged CSV chain (exercise_stage_runner.py). It
works on the same run directory that

    python scripts/export_exercise_worklist.py --language ja --format csv --limit 8 --out-dir RUN

creates (senses.csv + prompts.json), and writes everything of its own under
RUN/fat_seed/. Its upload files land in RUN/07_upload/, the same place the
staged chain puts them, so stage 8 (`exercise_stage_runner.py prepare/collect
--stage 8`) and `render` run on a fat-seed run unchanged.

    brief        RUN   rules_core.md + briefs/core_NN.md   (fat-seed-authoring, phase 1)
    plan         RUN   plans/<sid>.json from each authored core (reads the DB);
                       --source reviewed writes plans_reviewed/ instead
    check        RUN   translate + validate words/ (or --source reviewed) exactly as upload would
    review-pack  RUN   rules_judges.md + review_packs/review_NN.md  (fat-seed-review)
    assemble     RUN   reviewed/ -> 07_upload/batch_001.{core,exercises}[.batch].json
    status       RUN

Order: brief -> author cores -> plan -> author variants -> check (fix until
clean) -> review-pack -> review (fresh context) -> assemble -> upload_exercises.py
--no-render -> stage 8 -> render.

Nothing is re-implemented. Translation is services/vocabulary_ladder/fat_seed.py;
validation is upload_exercises.prepare_core / prepare_exercises; the level plan
is export_exercise_worklist.build_exercise_item. No step writes the database
and no step calls a model.
"""

import os
import sys
import glob
import json
import argparse
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling scripts

from services.vocabulary_ladder import fat_seed as fs
from services.vocabulary_ladder import stage_runner as sr
from services.vocabulary_ladder.config import get_sentence_target as fs_target
from exercise_stage_runner import read_senses, read_prompts

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fat_seed')
for noisy in ('httpx', 'httpcore'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

SUBDIR = 'fat_seed'
SOURCE_MODEL = 'claude-code:fat-seed'
DEFAULT_WIDTH = {'brief': 6, 'review': 6}

CORE_TASKS = ('vocab_prompt1_core',)
EXERCISE_TASKS = ('vocab_prompt2_exercises', 'vocab_prompt3_transforms',
                  'ladder_l4_morphology_generation',
                  'ladder_l8_collocation_repair_generation',
                  'ladder_syn_ant_generation', 'ladder_word_family_generation',
                  'ladder_particle_selection_generation')
JUDGE_TASKS = ('ladder_p1_sentence_judge', 'ladder_sentence_validity_judge',
               'ladder_l1_distractor_judge', 'ladder_collocation_judge',
               'ladder_relation_judge', 'ladder_word_family_judge',
               'ladder_particle_judge')

# Prompt variables worth showing the author of a typed block: the ones code
# decides (the relation to test, the particle spans) rather than the author.
TYPED_GIVEN_KEYS = ('relation', 'stem', 'target_word', 'particle_spans_json',
                    'morphological_forms_json')

EXERCISE_NAMES = {
    'level_1': 'phonetic_recognition', 'level_3': 'cloze_completion',
    'level_4': 'morphology_slot', 'level_5': 'collocation_gap_fill',
    'level_6': 'semantic_discrimination', 'level_7': 'spot_incorrect_sentence',
    'level_8': 'collocation_repair',
}


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def fdir(run_dir: str, *parts: str) -> str:
    return os.path.join(run_dir, SUBDIR, *parts)


def word_path(run_dir: str, source: str, sid: int) -> str:
    return fdir(run_dir, source, f'{sid}.json')


def load_doc(run_dir: str, source: str, sid: int) -> dict | None:
    path = word_path(run_dir, source, sid)
    if not os.path.exists(path):
        return None
    try:
        doc = sr.read_json(path)
    except json.JSONDecodeError as exc:
        return {'_parse_error': f'{path}: {exc}'}
    return doc if isinstance(doc, dict) else {'_parse_error': f'{path}: not an object'}


def selected(run_dir: str, senses_arg: str | None) -> list[dict]:
    rows = read_senses(run_dir)
    if senses_arg:
        want = {int(s) for s in senses_arg.split(',')}
        rows = [r for r in rows if r['sense_id'] in want]
    return rows


def db_and_language(run_dir: str):
    """Deferred: importing these initialises Supabase."""
    import export_exercise_worklist as eew  # noqa: F401 — initialises the factory
    from services.supabase_factory import get_supabase_admin
    return get_supabase_admin(), read_prompts(run_dir)['language_id']


# ---------------------------------------------------------------------------
# Rules files (the live prompt texts, once per run)
# ---------------------------------------------------------------------------

RULES_PREAMBLE = """\
# {title}

These are the **live production prompts** ({language}), reproduced for their
RULES: learner-tier limits, sense pinning, part-of-speech tokens, collocation
tests, distractor requirements. Follow every rule.

**Ignore each prompt's output-schema section, its numeric keys ("1", "2", "0",
"9" …) and its `{{placeholders}}`.** You write the named-field JSON described
in your brief; code translates it into these contracts.

"""


def write_rules(run_dir: str, name: str, title: str, tasks: tuple[str, ...]) -> str:
    prompts = read_prompts(run_dir)
    parts = [RULES_PREAMBLE.format(title=title, language=prompts['language'])]
    for task in tasks:
        spec = prompts['prompts'].get(task) or {}
        if not spec.get('template'):
            continue  # no row for this language (e.g. word_family outside en)
        parts.append(f'## {task} (version {spec.get("version")})\n\n'
                     f'```text\n{spec["template"].strip()}\n```\n')
    path = fdir(run_dir, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(parts))
    return path


# ---------------------------------------------------------------------------
# brief — phase 1 (core) briefs
# ---------------------------------------------------------------------------

CORE_BRIEF_HEAD = """\
# Fat-seed brief {batch:02d} — core ({language})

Run directory: `{run_dir}`

Read `{rules}` first: the live P1 rules for {language}. For every sense below,
write `{words_dir}/<sense_id>.json`:

```json
{{"sense_id": 123, "lemma": "…",
  "core": {{
    "pos": "…", "semantic_class": "…", "definition": "…",
    "primary_collocate": null, "pronunciation": "…", "ipa": "…",
    "syllable_count": 2, "register": "…", "sense_fingerprint": "…",
    "morphological_forms": [{{"form": "…", "label": "…"}}],
    "sentences": [{{"text": "…", "target_word": "…", "complexity_tier": "T3", "furigana": "…"}}]
  }}}}
```

or `{{"sense_id": 123, "lemma": "…", "skip": "reason"}}` for proper nouns,
symbols and fragments. Do NOT write `variants` yet. That comes after `plan`.

Non-negotiable (upload rejects otherwise):
- exactly {required} sentences; every `target_word` appears verbatim in its `text`
- the mined sentences listed below come first, **byte-for-byte unchanged**
- `pos` from the POS set listed per sense; `semantic_class` from the enum. It decides the level plan.
- `primary_collocate` is null unless it passes the fixed-collocation test in the rules
- `furigana` is ja only; omit it for zh/en

"""


def cmd_brief(args) -> int:
    rows = selected(args.run_dir, args.senses)
    if not args.force:
        rows = [r for r in rows
                if load_doc(args.run_dir, 'words', r['sense_id']) is None]
    if not rows:
        logger.info('brief: every selected sense already has words/<sid>.json '
                    '(--force to re-brief)')
        return 0
    prompts = read_prompts(args.run_dir)
    rules = write_rules(args.run_dir, 'rules_core.md', 'Core rules', CORE_TASKS)
    os.makedirs(fdir(args.run_dir, 'words'), exist_ok=True)
    width = args.width or DEFAULT_WIDTH['brief']
    index: dict[str, list[int]] = {}
    for n, i in enumerate(range(0, len(rows), width), 1):
        chunk = rows[i:i + width]
        body = [CORE_BRIEF_HEAD.format(
            batch=n, language=prompts['language'], run_dir=args.run_dir,
            rules=rules, words_dir=fdir(args.run_dir, 'words'),
            required=chunk[0]['sentences_required'])]
        for r in chunk:
            mined = [s.get('text', '') if isinstance(s, dict) else str(s)
                     for s in r['corpus_sentences']]
            body.append(
                f"## sense {r['sense_id']}: {r['lemma']}\n\n"
                f"- reading: {r['reading'] or '(none)'}\n"
                f"- dictionary POS hint: {r['part_of_speech'] or '(none)'}. "
                f"The enum below wins over this hint.\n"
                f"- existing definition: {r['definition'] or '(none)'}\n"
                f"- learner tier: {r['complexity_tier']}\n"
                f"- surface forms seen in tests: {r['surface_tokens']}\n"
                f"- POS set: {r['pos_set']}\n"
                f"- semantic_class enum: {r['semantic_class_enum']}\n"
                f"- mined sentences ({len(mined)}, keep verbatim, put first):\n"
                + ''.join(f'  {k}. {t}\n' for k, t in enumerate(mined))
                + f"- sentences to write yourself: {r['sentences_needed']}\n")
        path = fdir(args.run_dir, 'briefs', f'core_{n:02d}.md')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(body))
        index[os.path.basename(path)] = [r['sense_id'] for r in chunk]
        logger.info('wrote %s (%d senses)', path, len(chunk))
    sr.write_json(fdir(args.run_dir, 'briefs', 'index.json'), index)
    return 0


# ---------------------------------------------------------------------------
# The shared translate-and-validate pass
# ---------------------------------------------------------------------------

class _Ctx:
    """DB handles and generators, built once per command."""

    def __init__(self, run_dir: str):
        import export_exercise_worklist as eew
        import upload_exercises as ux
        from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
        from services.vocabulary_ladder.asset_generators.prompt2_exercises import ExerciseAssetGenerator
        from services.vocabulary_ladder.asset_generators.prompt3_transforms import TransformAssetGenerator

        self.eew, self.ux = eew, ux
        self.db, self.language_id = db_and_language(run_dir)
        self.pipeline = VocabAssetPipeline(self.db)
        self.p2 = ExerciseAssetGenerator(self.db, self.language_id)
        self.p3 = TransformAssetGenerator(self.db, self.language_id)
        self.split = {lv: cls(self.db, self.language_id)
                      for lv, cls in eew.SPLIT_GENERATORS.items()}


def core_item_for(row: dict) -> dict:
    return {'sense_id': row['sense_id'], 'lemma': row['lemma'],
            'corpus_sentences': row['corpus_sentences'],
            'tests_referencing': int(row['blocks_n_tests'] or 0)}


def evaluate_core(ctx: _Ctx, row: dict, doc: dict) -> dict:
    """Core → upload's prepare_core → level plan. The exercise half comes later."""
    sid = row['sense_id']
    try:
        raw = fs.core_to_raw(doc.get('core'))
    except fs.FatSeedError as exc:
        return {'status': 'failed', 'errors': [f'core: {exc}']}
    ready, failed = ctx.ux.prepare_core(
        ctx.db, {'language_id': ctx.language_id, 'items': [core_item_for(row)]},
        {sid: {'sense_id': sid, 'answer': raw}})
    if failed:
        return {'status': 'failed', 'errors': [f'core: {e}' for e in failed[0]['errors']]}
    content = ready[0]['content']
    item = ctx.eew.build_exercise_item(
        ctx.pipeline, ctx.p2, ctx.p3, ctx.split, sid, ctx.language_id, content,
        core_item_for(row)['tests_referencing'], include_typed=True)
    if item is None:
        return {'status': 'failed',
                'errors': ['plan: no LLM-authored level is active for this sense']}
    return {'status': 'ok', 'core_answer': raw, 'content': content, 'item': item,
            'warnings': ready[0]['warnings']}


def evaluate(ctx: _Ctx, row: dict, doc: dict | None) -> dict:
    """Everything upload would do to one document, without writing."""
    if doc is None:
        return {'status': 'missing', 'errors': ['no document']}
    if doc.get('_parse_error'):
        return {'status': 'failed', 'errors': [doc['_parse_error']]}
    if doc.get('sense_id') != row['sense_id']:
        return {'status': 'failed',
                'errors': [f"sense_id in file is {doc.get('sense_id')!r}"]}
    if doc.get('skip'):
        return {'status': 'skipped', 'errors': [], 'reason': doc['skip']}
    res = evaluate_core(ctx, row, doc)
    if res['status'] != 'ok':
        return res
    entry, errors, surplus = fs.exercise_answer(doc, res['item'])
    res['surplus'] = surplus
    if errors:
        return {**res, 'status': 'failed', 'errors': errors}
    _, failed = ctx.ux.prepare_exercises(
        ctx.db, {'language_id': ctx.language_id, 'items': [res['item']]},
        {row['sense_id']: entry})
    if failed:
        return {**res, 'status': 'failed', 'errors': failed[0]['errors']}
    return {**res, 'entry': entry, 'errors': []}


# ---------------------------------------------------------------------------
# plan — phase 2 inputs
# ---------------------------------------------------------------------------

def block_descriptors(ctx: _Ctx, item: dict, content: dict, headword: str) -> dict:
    """What each required block must be about, per variant.

    ``headword`` is dim_vocabulary.lemma: L1 names the dictionary form, never
    the inflected target of sentence 0 (TASK-803).
    """
    sentences = content.get('sentences') or []
    collocate = content.get('primary_collocate') or None

    def sent(i):
        if i is None or not (0 <= i < len(sentences)):
            return None
        return {'sentence_index': i, 'sentence': sentences[i].get('text', ''),
                'target_word': fs_target(sentences[i])}

    semantic_class = item['semantic_class']
    typed_gens = ctx.eew.typed_generators_for(
        ctx.db, ctx.language_id, semantic_class, ctx.pipeline._capability_context(content))

    out: dict = {}
    for v, vp in item['variants'].items():
        a = {int(k): val for k, val in vp['sentence_assignments'].items()}
        blocks: dict = {}
        for lv in (vp.get('p2') or {}).get('levels', []):
            name = f'level_{lv}'
            d = {'exercise': EXERCISE_NAMES[name]}
            if lv == 1:
                d['correct'] = headword
                d['options'] = '4-8 (over-generate; a judge filters distractors)'
            elif lv == 6:
                d.update({'correct_sentence_index': a.get(6),
                          'sentence': (sent(a.get(6)) or {}).get('sentence')})
            else:
                d.update(sent(a.get(lv)) or {})
                d['correct'] = collocate if lv == 5 else d.get('target_word')
                d['options'] = 'exactly 4, exactly 1 correct'
            blocks[name] = d
        if 7 in (vp.get('p3') or {}).get('levels', []):
            blocks['level_7'] = {'exercise': EXERCISE_NAMES['level_7'],
                                 'correct_sentence_indices': vp['p3']['l7_correct_indices']}
        for lv in (4, 8):
            spec = vp.get(f'l{lv}')
            if not spec:
                continue
            d = {'exercise': EXERCISE_NAMES[f'level_{lv}'], **(sent(spec['sentence_index']) or {}),
                 'options': 'exactly 4, exactly 1 correct',
                 'may_decline_with': fs.ESCAPE_TOKENS[f'level_{lv}']}
            d['correct'] = d.get('target_word') if lv == 4 else collocate
            blocks[f'level_{lv}'] = d
        for code, spec in sorted((vp.get('typed') or {}).items()):
            gen = typed_gens.get(code)
            given = {}
            if gen is not None:
                pv = gen._prompt_vars(content, spec['sentence_index'], [])
                given = {k: pv[k] for k in TYPED_GIVEN_KEYS if pv.get(k) not in (None, '', '[]')}
            blocks[code] = {'exercise': code, **(sent(spec['sentence_index']) or {}),
                            'given': given, 'options': 'exactly 4, exactly 1 correct',
                            'may_decline_with': fs.ESCAPE_TOKENS[code]}
        out[v] = blocks
    return out


def cmd_plan(args) -> int:
    ctx = _Ctx(args.run_dir)
    write_rules(args.run_dir, 'rules_exercises.md', 'Exercise rules', EXERCISE_TASKS)
    # A reviewer who changes the core (semantic_class, collocate, morphology)
    # changes the plan; its plans go beside the authored ones, not over them.
    plans = 'plans' if args.source == 'words' else 'plans_reviewed'
    os.makedirs(fdir(args.run_dir, plans), exist_ok=True)
    bad = 0
    for row in selected(args.run_dir, args.senses):
        sid = row['sense_id']
        doc = load_doc(args.run_dir, args.source, sid)
        if doc is None or doc.get('skip') or doc.get('_parse_error'):
            continue
        res = evaluate_core(ctx, row, doc)
        path = fdir(args.run_dir, plans, f'{sid}.json')
        if res['status'] != 'ok':
            sr.write_json(path, {'sense_id': sid, 'ok': False, 'errors': res['errors']})
            logger.warning('sense %s (%s): core not plannable', sid, row['lemma'])
            for e in res['errors']:
                logger.warning('    %s', e)
            bad += 1
            continue
        item, content = res['item'], res['content']
        sr.write_json(path, {
            'sense_id': sid, 'ok': True, 'lemma': row['lemma'],
            'semantic_class': item['semantic_class'],
            'active_levels': item['active_levels'],
            'collocate_grade': (content.get('collocate_grounding') or {}).get('status'),
            'core_warnings': res['warnings'],
            # [index, text, target_word, 'mined' | 'generated']: mined
            # sentences are corpus-attested and must stay byte-identical.
            'sentences': [[i, s.get('text', ''), fs_target(s), s.get('sentence_source')]
                          for i, s in enumerate(content.get('sentences') or [])],
            'blocks': block_descriptors(ctx, item, content, row['lemma']),
        })
        logger.info('sense %s (%s): %s — A needs %s', sid, row['lemma'],
                    item['semantic_class'], ', '.join(fs.expected_blocks(item['variants']['A'])))
        for w in res['warnings']:
            logger.info('    warning: %s', w)
    return 1 if bad else 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def cmd_check(args) -> int:
    ctx = _Ctx(args.run_dir)
    report, counts = {}, {}
    for row in selected(args.run_dir, args.senses):
        sid = row['sense_id']
        res = evaluate(ctx, row, load_doc(args.run_dir, args.source, sid))
        counts[res['status']] = counts.get(res['status'], 0) + 1
        report[str(sid)] = {k: res.get(k) for k in ('status', 'errors', 'surplus', 'warnings', 'reason')}
        tag = f"sense {sid} ({row['lemma']}): {res['status']}"
        if res['status'] == 'failed':
            logger.error(tag)
            for e in res['errors']:
                logger.error('    %s', e)
        else:
            logger.info(tag)
        for s in res.get('surplus') or []:
            logger.warning('    surplus block dropped (not in plan): %s', s)
    sr.write_json(fdir(args.run_dir, f'check.{args.source}.json'), report)
    logger.info('check (%s): %s', args.source, counts)
    return 1 if counts.get('failed') or counts.get('missing') else 0


# ---------------------------------------------------------------------------
# review-pack
# ---------------------------------------------------------------------------

REVIEW_HEAD = """\
# Fat-seed review {batch:02d} ({language})

Run directory: `{run_dir}`

Read `{rules}`: the live judge prompts. Apply their standards to every item.
Then for each sense below:

1. Read `{words}/<sid>.json` (the authored document) and `{plans}/<sid>.json`
   (which blocks are required, and the sentence each one is anchored to).
2. Write `{reviewed}/<sid>.json`: the full corrected document, same shape.
   Copy it unchanged only if nothing needed fixing.
3. Write `{review}/<sid>.json`:
   `{{"sense_id": <sid>, "verdict": "accept"|"rewrite"|"reject",
      "issues": [{{"path": "variants.A.level_3.options[2]", "problem": "…", "fix": "…"}}],
      "notes": "…"}}`

`reject` drops the sense from the upload. Use it only when the core itself is
unusable (wrong sense, broken sentences), not for a fixable distractor.

"""


def cmd_review_pack(args) -> int:
    prompts = read_prompts(args.run_dir)
    rows = [r for r in selected(args.run_dir, args.senses)
            if (d := load_doc(args.run_dir, 'words', r['sense_id'])) is not None
            and not d.get('skip') and not d.get('_parse_error')]
    if not rows:
        logger.error('review-pack: no authored documents to review')
        return 1
    rules = write_rules(args.run_dir, 'rules_judges.md', 'Judge rules', JUDGE_TASKS)
    for sub in ('reviewed', 'review', 'review_packs'):
        os.makedirs(fdir(args.run_dir, sub), exist_ok=True)
    width = args.width or DEFAULT_WIDTH['review']
    index = {}
    for n, i in enumerate(range(0, len(rows), width), 1):
        chunk = rows[i:i + width]
        body = [REVIEW_HEAD.format(
            batch=n, language=prompts['language'], run_dir=args.run_dir, rules=rules,
            words=fdir(args.run_dir, 'words'), plans=fdir(args.run_dir, 'plans'),
            reviewed=fdir(args.run_dir, 'reviewed'), review=fdir(args.run_dir, 'review'))]
        body += [f"- sense {r['sense_id']}: {r['lemma']}" for r in chunk]
        path = fdir(args.run_dir, 'review_packs', f'review_{n:02d}.md')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(body) + '\n')
        index[os.path.basename(path)] = [r['sense_id'] for r in chunk]
        logger.info('wrote %s (%d senses)', path, len(chunk))
    sr.write_json(fdir(args.run_dir, 'review_packs', 'index.json'), index)
    return 0


# ---------------------------------------------------------------------------
# assemble
# ---------------------------------------------------------------------------

def cmd_assemble(args) -> int:
    ctx = _Ctx(args.run_dir)
    rows = read_senses(args.run_dir)
    dropped: dict[str, str] = {}
    summary: dict[str, dict] = {}
    core_items, core_answers, ex_items, ex_answers = [], [], [], []

    for row in rows:
        sid, key = row['sense_id'], str(row['sense_id'])
        authored = load_doc(args.run_dir, 'words', sid)
        if authored is None:
            dropped[key] = 'not authored'
            continue
        if authored.get('skip'):
            dropped[key] = f"skipped by author: {authored['skip']}"
            continue
        record_path = fdir(args.run_dir, 'review', f'{sid}.json')
        reviewed = load_doc(args.run_dir, 'reviewed', sid)
        if not os.path.exists(record_path) or reviewed is None:
            dropped[key] = 'not reviewed'
            continue
        record = sr.read_json(record_path)
        verdict = record.get('verdict')
        paths = fs.changed_paths(authored, reviewed)
        summary[key] = {'verdict': verdict, 'changed': paths,
                        'issues': len(record.get('issues') or [])}
        if verdict not in sr.VERDICTS:
            dropped[key] = f'review verdict {verdict!r} is not one of {sr.VERDICTS}'
            continue
        if verdict == 'reject':
            dropped[key] = f"review rejected: {record.get('notes') or 'no notes'}"
            continue
        if verdict == 'rewrite' and not paths:
            dropped[key] = 'review says rewrite but reviewed/ is identical to words/'
            continue
        res = evaluate(ctx, row, reviewed)
        if res['status'] != 'ok':
            dropped[key] = 'reviewed document fails upload validation: ' + '; '.join(res['errors'])
            continue
        core_items.append(core_item_for(row))
        core_answers.append({'sense_id': sid, 'answer': res['core_answer']})
        ex_items.append(res['item'])
        ex_answers.append(res['entry'])

    if summary and not any(s['changed'] for s in summary.values()):
        logger.error('RUBBER STAMP: the review changed nothing in %d document(s). '
                     'Re-run fat-seed-review in a fresh context; do not assemble.',
                     len(summary))
        sr.write_json(fdir(args.run_dir, 'review_summary.json'), summary)
        return 1

    out_dir = os.path.join(args.run_dir, sr.UPLOAD_DIR)
    header = {'language': read_prompts(args.run_dir)['language'],
              'language_id': ctx.language_id, 'batch': 1}
    core_header = {k: v for k, v in ctx.eew.core_header(ctx.db, ctx.language_id).items()
                   if k != 'prompts'}
    ex_header = {k: v for k, v in ctx.eew.exercise_header(ctx.db, ctx.language_id).items()
                 if k != 'prompts'}
    files = {n: os.path.join(out_dir, n) for n in (
        'batch_001.core.batch.json', 'batch_001.core.json',
        'batch_001.exercises.batch.json', 'batch_001.exercises.json', 'dropped.json')}
    sr.write_json(files['batch_001.core.batch.json'],
                  {**header, 'stage': 'core', 'count': len(core_items), **core_header,
                   'items': core_items})
    sr.write_json(files['batch_001.core.json'], core_answers)
    sr.write_json(files['batch_001.exercises.batch.json'],
                  {**header, 'stage': 'exercises', 'count': len(ex_items), **ex_header,
                   'items': ex_items})
    sr.write_json(files['batch_001.exercises.json'], ex_answers)
    sr.write_json(files['dropped.json'], dropped)
    sr.write_json(fdir(args.run_dir, 'review_summary.json'), summary)

    verdicts = {}
    for s in summary.values():
        verdicts[s['verdict']] = verdicts.get(s['verdict'], 0) + 1
    logger.info('assembled %d sense(s); %d dropped; review verdicts %s',
                len(ex_items), len(dropped), verdicts)
    for key, why in dropped.items():
        logger.info('    dropped %s: %s', key, why)
    c, cb = files['batch_001.core.json'], files['batch_001.core.batch.json']
    e, eb = files['batch_001.exercises.json'], files['batch_001.exercises.batch.json']
    logger.info('next (dry run first, then without --dry-run):\n'
                '  python scripts/upload_exercises.py --stage core --source-model %s '
                '--batch-file %s --answers-file %s --dry-run\n'
                '  python scripts/upload_exercises.py --stage exercises --no-render '
                '--source-model %s --batch-file %s --answers-file %s --dry-run',
                SOURCE_MODEL, cb, c, SOURCE_MODEL, eb, e)
    return 0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status(args) -> int:
    rows = read_senses(args.run_dir)
    def count(sub):
        return len(glob.glob(fdir(args.run_dir, sub, '*.json')))
    words = [load_doc(args.run_dir, 'words', r['sense_id']) for r in rows]
    authored = [d for d in words if d]
    skipped = sum(1 for d in authored if d.get('skip'))
    with_variants = sum(1 for d in authored if isinstance(d.get('variants'), dict))
    print(f'senses: {len(rows)}   authored: {len(authored)} ({skipped} skipped, '
          f'{with_variants} with variants)')
    print(f'plans: {count("plans")}   reviewed: {count("reviewed")}   '
          f'review records: {count("review")}')
    for source in ('words', 'reviewed'):
        path = fdir(args.run_dir, f'check.{source}.json')
        if os.path.exists(path):
            rep = sr.read_json(path)
            tally = {}
            for r in rep.values():
                tally[r['status']] = tally.get(r['status'], 0) + 1
            print(f'last check ({source}): {tally}')
    up = os.path.join(args.run_dir, sr.UPLOAD_DIR, 'batch_001.exercises.json')
    print(f'assembled: {"yes" if os.path.exists(up) else "no"}')
    return 0


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('brief', 'plan', 'check', 'review-pack', 'assemble', 'status'):
        p = sub.add_parser(name)
        p.add_argument('run_dir')
        if name in ('brief', 'plan', 'check', 'review-pack'):
            p.add_argument('--senses', help='comma-separated sense ids')
        if name in ('brief', 'review-pack'):
            p.add_argument('--width', type=int, help='senses per brief/pack')
        if name == 'brief':
            p.add_argument('--force', action='store_true',
                           help='re-brief senses that already have a document')
        if name in ('check', 'plan'):
            p.add_argument('--source', choices=('words', 'reviewed'), default='words')
    args = parser.parse_args()
    handler = {'brief': cmd_brief, 'plan': cmd_plan, 'check': cmd_check,
               'review-pack': cmd_review_pack, 'assemble': cmd_assemble,
               'status': cmd_status}[args.cmd]
    try:
        return handler(args)
    except sr.StageError as exc:
        logger.error('%s', exc)
        return 1


if __name__ == '__main__':
    sys.exit(main())
