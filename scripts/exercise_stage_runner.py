#!/usr/bin/env python3
"""Stage runner for CSV exercise authoring (TASK-797).

Drives the staged chain from wiki/features/csv-exercise-authoring.tech.md over
a run directory that `export_exercise_worklist.py --format csv` created:

    prepare RUN --stage K      write stageK/round_NN/call_*.prompt.md (item_N envelopes)
    collect RUN --stage K      read call_*.response.json, validate, merge into 0K_*.json
    bridge  RUN                stage 2b: level plan + P2/P3/L4/L8/typed prompts
    assemble RUN               stage 7: 07_upload/batch_001.{core,exercises}[.batch].json
    status  RUN                where every sense stands

Order: prepare 1 → collect 1 → prepare 2 → collect 2 → bridge →
prepare/collect 3, 4, 5 → prepare 6 → collect 6 → assemble → upload_exercises.py.

Stages 1, 3, 4, 5 are answered by the batch-exercise-authoring skill; stages
2 and 6 by batch-exercise-judging, in a context that has never seen the
authoring. No step here writes to the database: prepare 2/6 and bridge read it
(the P1 judge prompt, the renderer's judges, collocate grounding, the live
capability gates); upload_exercises.py is the only writer.

Nothing is re-implemented. Validation is upload_exercises.prepare_core /
prepare_exercises; the level plan and exercise prompts are
export_exercise_worklist.build_exercise_item; judge prompts are captured from
the real judge functions and the real LadderExerciseRenderer with call_llm
swapped for a recorder, so they are exactly what would be sent live.
"""

import os
import sys
import csv
import copy
import json
import argparse
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling scripts

from services.vocabulary_ladder import stage_runner as sr

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('stage_runner')
for noisy in ('httpx', 'httpcore'):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Run-dir readers
# ---------------------------------------------------------------------------

def read_senses(run_dir: str) -> list[dict]:
    with open(os.path.join(run_dir, 'senses.csv'), encoding='utf-8', newline='') as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r['sense_id'] = int(r['sense_id'])
        r['corpus_sentences'] = json.loads(r['corpus_sentences'] or '[]')
    return rows


def read_prompts(run_dir: str) -> dict:
    return sr.read_json(os.path.join(run_dir, 'prompts.json'))


def only(units, senses: set[int] | None):
    return [u for u in units if not senses or u.sense_id in senses]


def db_and_language(run_dir: str):
    """Deferred: importing these initialises Supabase."""
    import export_exercise_worklist as eew  # noqa: F401 — initialises the factory
    from services.supabase_factory import get_supabase_admin
    prompts = read_prompts(run_dir)
    return get_supabase_admin(), prompts['language_id'], prompts


# ---------------------------------------------------------------------------
# Stage 1 — core (author)
# ---------------------------------------------------------------------------

def units_stage1(run_dir: str) -> tuple[list[sr.Unit], dict]:
    return [sr.Unit(unit_id=str(r['sense_id']), sense_id=r['sense_id'],
                    body=r['p1_prompt'], meta={'lemma': r['lemma']})
            for r in read_senses(run_dir)], {}


# ---------------------------------------------------------------------------
# Stage 2 — judge core (judge)
# ---------------------------------------------------------------------------

P1_JUDGE_GUIDANCE = """\
The artifact is a vocab_prompt1_core answer (numeric keys: "8" is the sentence
list, each {"1": text, "2": target word as it appears, ...}). Rewrite only a
sentence a judge would rate 2 or below. Constraints the uploader enforces:
the target word must appear verbatim in the sentence text; a mined corpus
sentence that is rewritten stops counting as mined; the sentence count and
order must not change; POS must stay in pos_set {pos_set}."""


def units_stage2(run_dir: str) -> tuple[list[sr.Unit], dict]:
    from services.vocabulary_ladder.asset_generators.prompt1_core import CoreAssetGenerator
    from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline

    db, language_id, prompts = db_and_language(run_dir)
    senses = {r['sense_id']: r for r in read_senses(run_dir)}
    core = sr.stage_output(run_dir, 1)['units']
    p1_gen = CoreAssetGenerator(db, language_id)
    pipeline = VocabAssetPipeline(db)
    guidance = P1_JUDGE_GUIDANCE.replace(
        '{pos_set}', ', '.join(prompts['validation']['pos_set']))

    units, blocked = [], {}
    for uid, res in core.items():
        if res['status'] != sr.STATUS_OK:
            continue
        sid = res['sense_id']
        content = p1_gen._remap_output(copy.deepcopy(res['answer']))
        if content is None:
            blocked[uid] = {'sense_id': sid, 'reason': 'P1 key remapping failed'}
            continue
        p1_gen._tag_sentence_sources(content, senses[sid]['corpus_sentences'])
        with sr.capture_llm_calls() as captured:
            pipeline._judge_p1_sentences(content, language_id, p1_gen, sid)
        units.append(sr.Unit(
            unit_id=uid, sense_id=sid, original=res['answer'],
            body=sr.judge_body(f"Sense {sid} ({senses[sid]['lemma']}) — P1 core",
                               captured, res['answer'], guidance)))
    return units, blocked


# ---------------------------------------------------------------------------
# Stage 2b — bridge (deterministic, DB read)
# ---------------------------------------------------------------------------

def check_prompt_pins(db, language_id: int, pinned: dict) -> None:
    """Refuse to continue if a prompt moved since stage 0 was exported."""
    from services.prompt_service import get_template_config
    moved = []
    for task, info in pinned.items():
        if 'version' not in info:
            continue
        try:
            live = get_template_config(db, task, language_id)['version']
        except Exception:
            continue
        if live != info['version']:
            moved.append(f'{task}: exported v{info["version"]}, live v{live}')
    if moved:
        raise sr.StageError('prompt_templates changed since export — re-export '
                            'the run: ' + '; '.join(moved))


def bridge(run_dir: str) -> dict:
    import export_exercise_worklist as eew
    import upload_exercises as ux
    from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
    from services.vocabulary_ladder.asset_generators.prompt2_exercises import ExerciseAssetGenerator
    from services.vocabulary_ladder.asset_generators.prompt3_transforms import TransformAssetGenerator

    db, language_id, prompts = db_and_language(run_dir)
    check_prompt_pins(db, language_id, prompts['prompts'])
    judged = sr.require_judged(run_dir, 2)['units']
    stage1 = sr.stage_output(run_dir, 1)['units']
    senses = read_senses(run_dir)

    dropped: dict[str, str] = {}
    core_items: dict[str, dict] = {}
    answers: dict[int, dict] = {}
    for r in senses:
        sid, key = r['sense_id'], str(r['sense_id'])
        s1 = stage1.get(key)
        if not s1:
            dropped[key] = 'stage 1: not answered'
            continue
        if s1['status'] == sr.STATUS_SKIP:
            dropped[key] = f'stage 1: skipped — {s1.get("reason")}'
            continue
        if s1['status'] != sr.STATUS_OK:
            dropped[key] = f'stage 1: {s1.get("reason")}'
            continue
        j = judged.get(key)
        if not j or j['status'] != sr.STATUS_OK:
            dropped[key] = f'stage 2: {(j or {}).get("reason") or "not judged"}'
            continue
        if j['verdict'] == 'reject':
            dropped[key] = f'stage 2 judge rejected: {j.get("notes")}'
            continue
        core_items[key] = {'sense_id': sid, 'lemma': r['lemma'],
                           'corpus_sentences': r['corpus_sentences'],
                           'tests_referencing': int(r['blocks_n_tests'] or 0)}
        answers[sid] = {'sense_id': sid, 'answer': j['answer']}

    # The uploader's own prepare step: remap, sentence_source, tier screen,
    # collocate grounding (pinned onto the content), VocabAssetValidator.
    ready, failed = ux.prepare_core(
        db, {'language_id': language_id,
             'items': [core_items[str(s)] for s in answers]}, answers)
    for row in failed:
        key = str(row['sense_id'])
        dropped[key] = 'core validation: ' + '; '.join(row['errors'])
        core_items.pop(key, None)

    pipeline = VocabAssetPipeline(db)
    p2_gen = ExerciseAssetGenerator(db, language_id)
    p3_gen = TransformAssetGenerator(db, language_id)
    split_gens = {lv: cls(db, language_id) for lv, cls in eew.SPLIT_GENERATORS.items()}

    items, contents, warnings = [], {}, {}
    for row in ready:
        sid, key = row['sense_id'], str(row['sense_id'])
        item = eew.build_exercise_item(
            pipeline, p2_gen, p3_gen, split_gens, sid, language_id, row['content'],
            core_items[key]['tests_referencing'], include_typed=True)
        if item is None:
            dropped[key] = 'bridge: no LLM-authored level is active for this sense'
            core_items.pop(key, None)
            continue
        items.append(item)
        contents[key] = row['content']
        warnings[key] = row['warnings']

    plan = {
        'language': prompts['language'], 'language_id': language_id,
        'all_sense_ids': [r['sense_id'] for r in senses],
        'core_header': {k: v for k, v in eew.core_header(db, language_id).items()
                        if k != 'prompts'},
        'exercise_header': {k: v for k, v in eew.exercise_header(db, language_id).items()
                            if k != 'prompts'},
        'core_items': core_items,
        'core_contents': contents,
        'core_warnings': warnings,
        'exercise_items': items,
        'dropped': dropped,
    }
    sr.write_json(os.path.join(run_dir, sr.PLAN_FILE), plan)
    write_plan_csv(run_dir, plan)
    logger.info('bridge: %d sense(s) planned, %d dropped', len(items), len(dropped))
    for key, why in dropped.items():
        logger.info('    dropped %s: %s', key, why)
    return plan


def write_plan_csv(run_dir: str, plan: dict) -> None:
    cols = ['sense_id', 'lemma', 'pos', 'semantic_class', 'active_levels',
            'p3_expected_levels', 'primary_collocate', 'collocate_grade',
            'typed_types', 'n_mined_kept', 'warnings']
    with open(os.path.join(run_dir, sr.PLAN_CSV), 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for item in plan['exercise_items']:
            key = str(item['sense_id'])
            content = plan['core_contents'][key]
            grade = (content.get('collocate_grounding') or {}).get('status')
            w.writerow({
                'sense_id': item['sense_id'],
                'lemma': plan['core_items'][key]['lemma'],
                'pos': content.get('pos'),
                'semantic_class': item['semantic_class'],
                'active_levels': json.dumps(item['active_levels']),
                'p3_expected_levels': json.dumps(item['p3_expected_levels']),
                'primary_collocate': content.get('primary_collocate') or '',
                'collocate_grade': grade or '',
                'typed_types': json.dumps(sorted(item['variants']['A'].get('typed') or {})),
                'n_mined_kept': sum(1 for s in content.get('sentences') or []
                                    if s.get('sentence_source') == 'mined'),
                'warnings': json.dumps(plan['core_warnings'][key], ensure_ascii=False),
            })


# ---------------------------------------------------------------------------
# Stages 3-5 — exercises / transforms / split + typed (author)
# ---------------------------------------------------------------------------

def plan_units(run_dir: str, stage: int) -> tuple[list[sr.Unit], dict]:
    plan = sr.read_json(os.path.join(run_dir, sr.PLAN_FILE))
    units = []
    for item in plan['exercise_items']:
        sid = item['sense_id']
        for v, variant in item['variants'].items():
            for part in sr.variant_parts(variant):
                if stage == 3 and part != 'p2' or stage == 4 and part != 'p3' \
                        or stage == 5 and part in ('p2', 'p3'):
                    continue
                if part.startswith('typed:'):
                    prompt = variant['typed'][part.split(':', 1)[1]]['prompt']
                else:
                    prompt = variant[part]['prompt']
                units.append(sr.Unit(unit_id=sr.unit_id(sid, v, part), sense_id=sid,
                                     variant=v, part=part, body=prompt,
                                     meta={'lemma': item.get('lemma')}))
    return units, {}


# ---------------------------------------------------------------------------
# Stage 6 — judge items (judge)
# ---------------------------------------------------------------------------

ITEM_JUDGE_GUIDANCE = """\
The artifact holds one sense's hand-authored exercise answers for variants A
and B, in each prompt's own numeric contract (p2 = vocab_prompt2_exercises,
p3 = vocab_prompt3_transforms, l4/l8 = split prompts, typed = typed LLM
types). The judge prompts above are exactly what the live renderer would send
for these items. Rewrite any option, distractor or sentence a judge would rate
2 or below; keep every structural rule: exactly 4 options with exactly one
correct (L1 may carry 4-8), a non-empty explanation per option, L6 has 3 wrong
sentences, L7's incorrect and corrected sentences differ. Do not add or remove
levels. Core sentences for reference:
{sentences}"""


def units_stage6(run_dir: str) -> tuple[list[sr.Unit], dict]:
    import upload_exercises as ux
    from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer

    db, language_id, _ = db_and_language(run_dir)
    plan = sr.read_json(os.path.join(run_dir, sr.PLAN_FILE))
    stage_units = {s: sr.stage_output(run_dir, s)['units'] for s in (3, 4, 5)}

    class InMemoryRenderer(LadderExerciseRenderer):
        """The real renderer over assets that are not stored yet."""
        def __init__(self, db, assets):
            super().__init__(db)
            self._assets = assets

        def _load_assets(self, sense_id):
            return copy.deepcopy(self._assets)

        def _load_asset_ids(self, sense_id):
            return {k: None for k in self._assets}

    units, blocked = [], {}
    for item in plan['exercise_items']:
        sid, key = item['sense_id'], str(item['sense_id'])
        entry, missing = sr.exercise_answer_for(sid, item, stage_units)
        if missing:
            blocked[key] = {'sense_id': sid,
                            'reason': 'missing upstream answer: ' + '; '.join(missing)}
            continue
        ready, failed = ux.prepare_exercises(
            db, {'language_id': language_id, 'items': [item]}, {sid: entry})
        if failed:
            blocked[key] = {'sense_id': sid,
                            'reason': 'exercise validation: ' + '; '.join(failed[0]['errors'])}
            continue
        core = plan['core_contents'][key]
        assets = {'prompt1_core': core, **ready[0]['assets']}
        with sr.capture_llm_calls() as captured:
            InMemoryRenderer(db, assets).build_rows(sid, language_id)
        artifact = {v: entry[v] for v in item['variants']}
        sentences = '\n'.join(f'  [{i}] {s.get("text", "")}'
                              for i, s in enumerate(core.get('sentences') or []))
        units.append(sr.Unit(
            unit_id=key, sense_id=sid, original=artifact,
            body=sr.judge_body(f'Sense {sid} ({plan["core_items"][key]["lemma"]}) — exercise items',
                               captured, artifact,
                               ITEM_JUDGE_GUIDANCE.replace('{sentences}', sentences))))
    return units, blocked


# ---------------------------------------------------------------------------
# Stage 8 — the renderer's judges (subagent), then render with replay
# ---------------------------------------------------------------------------

def assembled_sense_ids(run_dir: str) -> list[int]:
    path = os.path.join(run_dir, sr.UPLOAD_DIR, 'batch_001.exercises.json')
    return [a['sense_id'] for a in sr.read_json(path)]


def stored_render_answers(run_dir: str) -> dict:
    units = sr.stage_output(run_dir, sr.RENDER_JUDGE_STAGE)['units']
    return {uid: u['answer'] for uid, u in units.items() if u.get('status') == sr.STATUS_OK}


def seed_for_sense(sense_id: int) -> None:
    """Make the renderer's random choices repeatable per sense.

    l1_lookup.build_candidates shuffles and truncates the phonetic-trie
    candidates, so an unseeded capture and an unseeded render ask the L1
    judge about different words and a stored answer never matches. Seeding
    both identically makes the render ask exactly what the subagent answered.
    """
    import random
    random.seed(f'csv-authoring:{sense_id}')


def units_stage8(run_dir: str) -> tuple[list[sr.Unit], dict]:
    """Every judge request the real renderer makes for the stored assets.

    Requests that already have a subagent answer are left out, so a second
    round only asks what the first did not cover (e.g. a request that only
    appears once an earlier verdict is known).
    """
    from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer

    db, language_id, _ = db_and_language(run_dir)
    answered = stored_render_answers(run_dir)
    renderer = LadderExerciseRenderer(db)
    requests: dict[str, dict] = {}
    for sid in assembled_sense_ids(run_dir):
        # Replay what is already answered so later requests (which can depend
        # on earlier verdicts) are the ones actually reached.
        seed_for_sense(sid)
        with sr.replay_llm_calls(answered) as misses:
            renderer.build_rows(sid, language_id)
        for m in misses:
            req = requests.setdefault(m['key'], {**m, 'sense_ids': []})
            if sid not in req['sense_ids']:
                req['sense_ids'].append(sid)
    units = [sr.Unit(unit_id=key, sense_id=req['sense_ids'][0],
                     body=sr.render_judge_body(req['task_name'], req['template_version'],
                                               req['prompt'], req['sense_ids']),
                     meta={'task_name': req['task_name'], 'sense_ids': req['sense_ids']})
             for key, req in requests.items()]
    if not units:
        raise sr.StageError('stage 8: every renderer judge request already has an '
                            'answer — run `render`')
    return units, {}


def cmd_render(args) -> int:
    """Build exercise rows with every judge answered from stage 8. No API calls.

    A sense is inserted only if every judge request it made was answered; a
    miss means `prepare --stage 8` again. A sense that already has exercise
    rows is refused — render has no de-duplication.
    """
    from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer

    db, language_id, _ = db_and_language(args.run_dir)
    answers = stored_render_answers(args.run_dir)
    renderer = LadderExerciseRenderer(db)
    senses = ([int(s) for s in args.senses.split(',')] if args.senses
              else assembled_sense_ids(args.run_dir))
    total, blocked = 0, 0
    for sid in senses:
        existing = (db.table('exercises').select('id', count='exact')
                      .eq('word_sense_id', sid).limit(1).execute().count or 0)
        if existing:
            logger.error('sense %s already has %d exercise row(s) — refusing to '
                         'render twice (clear them first)', sid, existing)
            blocked += 1
            continue
        seed_for_sense(sid)
        with sr.replay_llm_calls(answers) as misses:
            rows = renderer.build_rows(sid, language_id)
        if misses:
            logger.error('sense %s: %d judge request(s) have no subagent answer — '
                         'nothing inserted; run prepare --stage 8', sid, len(misses))
            blocked += 1
            continue
        if not rows:
            logger.warning('sense %s: rendered 0 rows — check the core asset', sid)
            continue
        linked = sum(1 for r in rows if r.get('word_asset_id'))
        logger.info('sense %s: %d rows (%d with word_asset_id)%s', sid, len(rows), linked,
                    '' if not args.dry_run else ' [dry run]')
        if not args.dry_run:
            db.table('exercises').insert(rows).execute()
        total += len(rows)
    logger.info('%s %d rows; %d sense(s) blocked', 'would insert' if args.dry_run
                else 'inserted', total, blocked)
    return 1 if blocked else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

UNIT_BUILDERS = {
    1: units_stage1,
    2: units_stage2,
    3: lambda d: plan_units(d, 3),
    4: lambda d: plan_units(d, 4),
    5: lambda d: plan_units(d, 5),
    6: units_stage6,
    8: units_stage8,
}


def cmd_prepare(args) -> int:
    if args.stage in (3, 4, 5, 6) and not os.path.exists(os.path.join(args.run_dir, sr.PLAN_FILE)):
        raise sr.StageError('run `bridge` first — stages 3-6 need the level plan')
    units, blocked = UNIT_BUILDERS[args.stage](args.run_dir)
    senses = {int(s) for s in args.senses.split(',')} if args.senses else None
    units = only(units, senses)
    blocked = {k: v for k, v in blocked.items() if not senses or v['sense_id'] in senses}
    round_dir = sr.next_round_dir(args.run_dir, args.stage)
    manifest = sr.write_calls(round_dir, args.stage, units,
                              args.width or sr.DEFAULT_WIDTH[args.stage], blocked=blocked)
    role = ('batch-exercise-judging'
            if args.stage in sr.JUDGE_STAGES or args.stage == sr.RENDER_JUDGE_STAGE
            else 'batch-exercise-authoring')
    logger.info('stage %d: %d unit(s) in %d call(s) -> %s  [%s]',
                args.stage, len(units), len(manifest['calls']), round_dir, role)
    for uid, info in blocked.items():
        logger.warning('    blocked %s: %s', uid, info['reason'])
    return 0


def cmd_collect(args) -> int:
    round_dir = sr.latest_round_dir(args.run_dir, args.stage)
    results = sr.collect_round(round_dir, args.stage)
    merged = sr.merge_results(sr.stage_output(args.run_dir, args.stage), results, args.stage)
    sr.write_json(os.path.join(args.run_dir, sr.STAGE_FILES[args.stage]), merged)
    counts = {}
    for r in results.values():
        counts[r['status']] = counts.get(r['status'], 0) + 1
    logger.info('stage %d collected from %s: %s', args.stage,
                os.path.basename(round_dir), counts)
    for uid, r in results.items():
        if r['status'] == sr.STATUS_FAILED:
            logger.warning('    %s failed: %s', uid, r.get('reason'))
    if args.stage in sr.JUDGE_STAGES:
        verdicts = {}
        for r in merged['units'].values():
            if r['status'] == sr.STATUS_OK:
                verdicts[r['verdict']] = verdicts.get(r['verdict'], 0) + 1
        logger.info('verdicts: %s', verdicts)
        if merged['rubber_stamp']:
            logger.error('RUBBER STAMP: every judged item is changed:false. The run '
                         'cannot proceed past stage %d until the judging skill is '
                         're-run in a fresh context.', args.stage)
            return 1
    return 0


def cmd_bridge(args) -> int:
    bridge(args.run_dir)
    return 0


def cmd_assemble(args) -> int:
    out = sr.assemble(args.run_dir)
    logger.info('assembled %d sense(s); %d dropped', out['kept'], len(out['dropped']))
    for key, why in out['dropped'].items():
        logger.info('    dropped %s: %s', key, why)
    f = out['files']
    logger.info('next:\n  python scripts/upload_exercises.py --stage core --batch-file %s '
                '--answers-file %s --dry-run\n  python scripts/upload_exercises.py '
                '--stage exercises --batch-file %s --answers-file %s --dry-run',
                f['core_batch'], f['core_answers'], f['exercises_batch'],
                f['exercises_answers'])
    return 0


def cmd_status(args) -> int:
    for stage, name in sr.STAGE_FILES.items():
        path = os.path.join(args.run_dir, name)
        if not os.path.exists(path):
            print(f'stage {stage}: not collected')
            continue
        out = sr.read_json(path)
        counts = {}
        for r in out['units'].values():
            counts[r['status']] = counts.get(r['status'], 0) + 1
        extra = '  RUBBER STAMP' if out.get('rubber_stamp') else ''
        print(f'stage {stage}: {counts}{extra}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('run_dir')
    p.add_argument('--stage', type=int, required=True, choices=sorted(UNIT_BUILDERS))
    p.add_argument('--width', type=int, help='items per call (default: per stage)')
    p.add_argument('--senses', help='comma-separated sense ids (re-run a subset)')
    p.set_defaults(fn=cmd_prepare)
    c = sub.add_parser('collect')
    c.add_argument('run_dir')
    c.add_argument('--stage', type=int, required=True, choices=sorted(UNIT_BUILDERS))
    c.set_defaults(fn=cmd_collect)
    for name, fn in (('bridge', cmd_bridge), ('assemble', cmd_assemble), ('status', cmd_status)):
        s = sub.add_parser(name)
        s.add_argument('run_dir')
        s.set_defaults(fn=fn)
    r = sub.add_parser('render', help='insert exercise rows, judges replayed from stage 8')
    r.add_argument('run_dir')
    r.add_argument('--senses')
    r.add_argument('--dry-run', action='store_true')
    r.set_defaults(fn=cmd_render)
    args = parser.parse_args()
    try:
        return args.fn(args)
    except sr.StageError as exc:
        logger.error('%s', exc)
        return 1


if __name__ == '__main__':
    sys.exit(main())
