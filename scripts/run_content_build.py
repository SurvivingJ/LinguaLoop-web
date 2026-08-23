#!/usr/bin/env python3
"""Build a batch of tests plus the word assets and ladder exercises for the
vocabulary those tests actually introduce.

Three pipelines have to run in order, and only the first two are joined by an
existing entry point:

    tests   TestGenerationOrchestrator.run_batch  -> tests.vocab_sense_ids
    senses  (this script)                         -> rank + cap the fan-out
    ladder  VocabAssetPipeline.generate_for_sense -> word_assets
            LadderExerciseRenderer.render_all     -> exercises (word_asset_id)

Why the cap exists
------------------
``tests.vocab_sense_ids`` averages 80-113 senses per test, and 100 existing
English tests reference 5,821 *distinct* senses. The ladder runs ~5.5 min per
sense (TASK-515), so "assets for everything these tests touch" is several
hundred hours. The fan-out must be ranked and capped, and the ranking is by how
many of the newly generated tests a sense appears in — a sense carried by
twelve tests earns its assets ahead of one carried by a single test.

Ordering and failure design
---------------------------
* **Canary before the long run.** One sense goes through the full ladder before
  a single test is generated. ja has never produced a ``word_assets`` row, so
  the first honest evidence that the path works end to end for this language is
  a sense that survives it. Five minutes here beats discovering a missing
  prompt row five hours in. The canary also *measures* per-sense wall clock, so
  the ETA printed before the main run is observed rather than assumed.
* **Fail-closed judging.** Both long phases run inside ``batch_mode()``. A
  judge that cannot resolve its template or model raises ``JudgeUnavailable``
  and abandons the phase instead of silently ``safe_accept``-ing everything —
  two total outages came from exactly that (TASK-510).
* **Checkpoint every sense.** The state file is rewritten after each sense, so
  ``--resume`` never redoes finished work. This matters more than usual here:
  ``render_all`` does a plain insert with **no de-duplication**, so re-running a
  rendered sense duplicates its exercise rows.
* **Preflight is per-language.** Required prompt rows are derived from the
  types actually enabled for this language in ``EXERCISE_TYPE_REGISTRY`` — e.g.
  ``ladder_word_family_generation`` has no ja row because ``word_family`` is
  registered ``(2,)``, English only. Demanding it for ja would be a false alarm.

Usage::

    # look before leaping — no LLM calls, no writes
    python scripts/run_content_build.py --language ja --phases preflight

    # prove the ladder works for this language on one real sense (~5 min)
    python scripts/run_content_build.py --language ja --phases preflight,canary

    # the full build
    python scripts/run_content_build.py --language ja --tests 100 \
        --max-senses 150 --sense-workers 3 --yes

    # pick up after an interruption
    python scripts/run_content_build.py --resume ja-20260822-140301 --yes
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, 'data', 'content_builds')

LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}
LANG_NAME = {'zh': 'Chinese', 'en': 'English', 'ja': 'Japanese'}

# The three prompts every ladder sense needs, whatever the language.
CORE_LADDER_TASKS = (
    'vocab_prompt1_core',
    'vocab_prompt2_exercises',
    'vocab_prompt3_transforms',
)

# Levels that left the P3 monolith and carry their own prompt row.
SPLIT_LEVEL_TASKS = {
    4: 'ladder_l4_morphology_generation',
    8: 'ladder_l8_collocation_repair_generation',
}

# Type-registered LLM generators that own a prompt row, keyed by registry type.
TYPE_PROMPT_TASKS = {
    'synonym_antonym_match': 'ladder_syn_ant_generation',
    'word_family': 'ladder_word_family_generation',
    'particle_selection': 'ladder_particle_selection_generation',
}

logger = logging.getLogger('content_build')


# ── state ──────────────────────────────────────────────────────────────────

def state_path(run_id: str) -> str:
    return os.path.join(STATE_DIR, f'{run_id}.json')


def load_state(run_id: str) -> dict:
    with open(state_path(run_id), encoding='utf-8') as fh:
        return json.load(fh)


def save_state(state: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = state_path(state['run_id']) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, state_path(state['run_id']))


def new_state(args) -> dict:
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    return {
        'run_id': f'{args.language}-{stamp}',
        'language': args.language,
        'language_id': LANG_ID[args.language],
        'started': datetime.now(timezone.utc).isoformat(),
        'config': {
            'tests': args.tests, 'test_type': args.test_type,
            'difficulty': args.difficulty, 'max_senses': args.max_senses,
            'sense_workers': args.sense_workers,
            'canary_senses': args.canary_senses,
        },
        'phases_done': [],
        'tests': {'generated': 0, 'failed': 0, 'test_ids': []},
        'canary': {},
        'senses': {'selected': [], 'done': {}, 'failed': {}},
    }


# ── helpers ────────────────────────────────────────────────────────────────

def enabled_types(language_id: int) -> set[str]:
    """Registry types enabled for this language."""
    from services.vocabulary_ladder.config import _CAPABILITY_SPEC
    out = set()
    for row in _CAPABILITY_SPEC:
        type_name, langs, enabled = row[0], row[1], row[-1]
        if enabled and language_id in langs:
            out.add(type_name)
    return out


def senses_without_assets(db, sense_ids: list[int]) -> list[int]:
    """Subset of sense_ids that have no word_assets row yet."""
    have: set[int] = set()
    for i in range(0, len(sense_ids), 300):
        chunk = sense_ids[i:i + 300]
        rows = (db.table('word_assets').select('sense_id')
                  .in_('sense_id', chunk).execute().data or [])
        have.update(r['sense_id'] for r in rows)
    return [s for s in sense_ids if s not in have]


def sense_ids_for_tests(db, test_ids: list[str]) -> Counter:
    """Count how many of these tests each sense appears in."""
    counts: Counter = Counter()
    for i in range(0, len(test_ids), 100):
        chunk = test_ids[i:i + 100]
        rows = (db.table('tests').select('id, vocab_sense_ids')
                  .in_('id', chunk).execute().data or [])
        for r in rows:
            for sid in set(r.get('vocab_sense_ids') or []):
                counts[sid] += 1
    return counts


def spend_since(db, since_iso: str) -> tuple[int, float, int]:
    """(calls, usd, rows_with_null_cost) logged since a timestamp."""
    try:
        rows = (db.table('llm_calls').select('cost_usd')
                  .gte('created_at', since_iso).limit(50000).execute().data or [])
    except Exception as exc:                                  # table/col drift
        logger.debug('spend query failed: %s', exc)
        return (0, 0.0, 0)
    nulls = sum(1 for r in rows if r.get('cost_usd') is None)
    total = sum(float(r['cost_usd']) for r in rows if r.get('cost_usd') is not None)
    return (len(rows), total, nulls)


def fmt_hms(seconds: float) -> str:
    s = int(seconds)
    return f'{s // 3600}h{(s % 3600) // 60:02d}m{s % 60:02d}s'


# ── phases ─────────────────────────────────────────────────────────────────

def phase_preflight(db, state: dict) -> list[str]:
    """Return a list of blocking problems (empty means go)."""
    lang, lid = state['language'], state['language_id']
    cfg = state['config']
    problems: list[str] = []

    print(f'\n── preflight: {LANG_NAME[lang]} (language_id={lid}) ' + '─' * 26)

    # 1. Queue supply. run_batch cycles items when count exceeds supply, so a
    #    short queue is not fatal — but it silently narrows topic variety.
    from services.test_generation.database_client import TestDatabaseClient
    pending_id = TestDatabaseClient()._get_status_id('pending')
    q = (db.table('production_queue').select('id', count='exact')
           .eq('status_id', pending_id).eq('language_id', lid).execute())
    pending = q.count or 0
    if pending == 0:
        problems.append(f'no pending production_queue items for {lang} — '
                        f'run_batch would return immediately')
    elif pending < cfg['tests']:
        print(f'  WARN  queue supply {pending} < {cfg["tests"]} tests — topics '
              f'will be cycled ({cfg["tests"] / pending:.1f} tests per topic)')
    else:
        print(f'  OK    queue supply: {pending} pending items')

    # 2. Ladder prompt rows, restricted to what this language actually runs.
    types = enabled_types(lid)
    required = set(CORE_LADDER_TASKS) | set(SPLIT_LEVEL_TASKS.values())
    for type_name, task in TYPE_PROMPT_TASKS.items():
        if type_name in types:
            required.add(task)
        else:
            print(f'  SKIP  {task} not required ({type_name} not enabled for {lang})')

    rows = (db.table('prompt_templates')
              .select('task_name, version, model, provider')
              .eq('language_id', lid).eq('is_active', True)
              .in_('task_name', sorted(required)).execute().data or [])
    found = {r['task_name']: r for r in rows}
    for task in sorted(required):
        r = found.get(task)
        if r is None:
            problems.append(f'no active {lang} prompt_templates row for {task!r}')
        elif not r.get('model') or not r.get('provider'):
            problems.append(f'{task} [{lang}] v{r["version"]} has NULL '
                            f'model/provider — prompt_service raises on this')
        else:
            print(f'  OK    {task} v{r["version"]} ({r["model"]})')

    # 3. Candidate senses for the canary and, later, a sanity bound on fan-out.
    existing = (db.table('tests').select('vocab_sense_ids')
                  .eq('language_id', lid).limit(500).execute().data or [])
    pool: set[int] = set()
    for r in existing:
        pool.update(r.get('vocab_sense_ids') or [])
    if not pool:
        problems.append(f'no existing {lang} test carries vocab_sense_ids — '
                        f'cannot pick a canary sense')
    else:
        free = senses_without_assets(db, sorted(pool))
        print(f'  OK    canary pool: {len(free)} {lang} senses without assets '
              f'(of {len(pool)} referenced)')
        state['canary_pool'] = free[:50]

    # 4. Credentials the long phases assume.
    if not os.getenv('OPENROUTER_API_KEY'):
        problems.append('OPENROUTER_API_KEY not set (llm_service freezes it at '
                        'import time — exporting it later will not help)')
    else:
        print('  OK    OPENROUTER_API_KEY present')

    return problems


def _ladder_one(db, sense_id: int, language_id: int) -> dict:
    """Assets then render for one sense. Never renders half-built assets."""
    from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
    from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer
    from services.test_generation.agents.audio_synthesizer import AudioSynthesizer

    t0 = time.time()
    pipeline = VocabAssetPipeline(db)
    result = pipeline.generate_for_sense(sense_id, language_id)
    status = result.get('status')
    # TASK-737: generate_for_sense now reports a per-stage breakdown (see
    # services/timing.py) — carried through so phase_canary can print where
    # the 5.5 min/sense baseline actually goes, not just the total.
    stage_seconds = result.get('stage_seconds') or {}
    if status == 'failed':
        return {'status': 'failed', 'exercises': 0, 'seconds': time.time() - t0,
                'errors': result.get('errors', []), 'stage_seconds': stage_seconds}

    renderer = LadderExerciseRenderer(db, audio_synthesizer=AudioSynthesizer())
    exercise_ids = renderer.render_all(sense_id, language_id)
    return {'status': status, 'exercises': len(exercise_ids),
            'seconds': time.time() - t0, 'errors': result.get('errors', []),
            'stage_seconds': stage_seconds}


def phase_canary(db, state: dict) -> bool:
    """Run N senses through the full ladder before committing to the batch.

    One sense proves the path resolves; two or three tell you whether a level
    yielding nothing is a property of that sense or of the language. Canary
    senses are recorded in ``senses['done']`` like any other, so they count in
    the final tally and are never rebuilt by the ladder phase.
    """
    from services.exercise_generation.judges.base import batch_mode

    pool = [s for s in (state.get('canary_pool') or [])
            if str(s) not in state['senses']['done']]
    n = state['config'].get('canary_senses', 1)
    if len(pool) < n:
        print(f'  FAIL  only {len(pool)} canary senses available, need {n}')
        return False
    picks = pool[:n]

    print(f'\n── canary: {n} sense(s) through the full ladder ' + '─' * 22)
    runs = []
    for sense_id in picks:
        since = datetime.now(timezone.utc).isoformat()
        with batch_mode():
            out = _ladder_one(db, sense_id, state['language_id'])
        calls, usd, nulls = spend_since(db, since)
        out.update(sense_id=sense_id, calls=calls, usd=usd)
        runs.append(out)

        if out['status'] != 'failed':
            state['senses']['done'][str(sense_id)] = out
        else:
            state['senses']['failed'][str(sense_id)] = out
        state['canary'] = runs
        save_state(state)

        print(f'  sense {sense_id}: status={out["status"]}  '
              f'exercises={out["exercises"]}  {fmt_hms(out["seconds"])}  '
              f'{calls} calls  ${usd:.4f}'
              + (f'  ({nulls} null-cost)' if nulls else ''))
        stages = out.get('stage_seconds') or {}
        if stages:
            breakdown = '  '.join(
                f'{name}={secs:.1f}s'
                for name, secs in sorted(stages.items(), key=lambda kv: -kv[1])
            )
            print(f'    stages: {breakdown}')
        if out.get('errors'):
            print(f'    errors: {out["errors"][:3]}')

    ok = [r for r in runs if r['status'] != 'failed' and r['exercises'] > 0]
    if not ok:
        print('  FAIL  no canary sense produced exercises — not committing to '
              'the full run')
        return False

    mean = sum(r['seconds'] for r in ok) / len(ok)
    mean_usd = sum(r['usd'] for r in ok) / len(ok)
    state['canary_mean_seconds'] = mean
    state['canary_mean_usd'] = mean_usd
    save_state(state)
    print(f'  OK    {len(ok)}/{len(runs)} senses produced exercises  '
          f'(mean {fmt_hms(mean)}/sense, ${mean_usd:.4f}/sense)')
    return True


def phase_tests(db, state: dict) -> None:
    from services.test_generation.orchestrator import (
        TestGenerationOrchestrator, BatchConfig,
    )
    lang, lid, cfg = state['language'], state['language_id'], state['config']

    print(f'\n── tests: {cfg["tests"]} × {LANG_NAME[lang]} {cfg["test_type"]} '
          + '─' * 20)

    before = {r['id'] for r in (db.table('tests').select('id')
                                 .eq('language_id', lid).limit(10000)
                                 .execute().data or [])}
    since = datetime.now(timezone.utc).isoformat()
    t0 = time.time()

    orchestrator = TestGenerationOrchestrator()
    metrics = orchestrator.run_batch(BatchConfig(
        language_code=lang,
        count=cfg['tests'],
        test_type=cfg['test_type'],
        difficulty=cfg['difficulty'],
    ))

    after = {r['id'] for r in (db.table('tests').select('id')
                                .eq('language_id', lid).limit(10000)
                                .execute().data or [])}
    new_ids = sorted(after - before)
    calls, usd, nulls = spend_since(db, since)

    state['tests'] = {
        'generated': metrics.tests_generated,
        'failed': metrics.tests_failed,
        'test_ids': new_ids,
        'seconds': time.time() - t0,
        'calls': calls, 'usd': usd,
    }
    save_state(state)
    print(f'  generated={metrics.tests_generated}  failed={metrics.tests_failed}  '
          f'new rows={len(new_ids)}  {fmt_hms(time.time() - t0)}  ${usd:.4f}')


def phase_select(db, state: dict) -> None:
    """Rank the new tests' senses by test-frequency, drop any that already
    have assets, and cap at max_senses."""
    test_ids = state['tests']['test_ids']
    if not test_ids:
        raise RuntimeError('no test ids recorded — run the tests phase first')

    counts = sense_ids_for_tests(db, test_ids)
    free = senses_without_assets(db, [s for s, _ in counts.most_common()])
    freeset = set(free)
    ranked = [s for s, _ in counts.most_common() if s in freeset]
    cap = state['config']['max_senses']
    selected = ranked[:cap]

    state['senses']['selected'] = selected
    state['senses']['candidates'] = len(ranked)
    save_state(state)

    print(f'\n── select: {len(counts)} distinct senses across {len(test_ids)} '
          f'tests ' + '─' * 12)
    print(f'  {len(ranked)} lack assets; taking top {len(selected)} by test '
          f'frequency (cap {cap})')
    if selected:
        top = counts[selected[0]]
        cut = counts[selected[-1]]
        print(f'  frequency range of the selection: {top} tests -> {cut} tests')
    if len(ranked) > cap:
        print(f'  NOTE  {len(ranked) - cap} senses left unbuilt — re-run with a '
              f'higher --max-senses to extend')


def phase_ladder(db, state: dict) -> None:
    from concurrent.futures import as_completed
    from services.exercise_generation.judges.base import (
        batch_mode, BatchModeThreadPoolExecutor,
    )

    selected = state['senses']['selected']
    done = state['senses']['done']
    todo = [s for s in selected if str(s) not in done]
    workers = state['config']['sense_workers']

    print(f'\n── ladder: {len(todo)} senses × {workers} workers ' + '─' * 26)
    if not todo:
        print('  nothing to do'); return

    per_sense = state.get('canary_mean_seconds')
    if per_sense:
        eta = len(todo) * per_sense / max(workers, 1)
        print(f'  ETA {fmt_hms(eta)} at the canary\'s {fmt_hms(per_sense)}/sense')

    since = datetime.now(timezone.utc).isoformat()
    t0 = time.time()
    lid = state['language_id']
    completed = 0

    # batch_mode outside the pool: BatchModeThreadPoolExecutor snapshots the
    # submitting thread's flag per submit, so workers inherit fail-closed.
    with batch_mode():
        with BatchModeThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_ladder_one, db, sid, lid): sid for sid in todo}
            for fut in as_completed(futures):
                sid = futures[fut]
                completed += 1
                try:
                    out = fut.result()
                except Exception as exc:
                    state['senses']['failed'][str(sid)] = {'error': str(exc)}
                    logger.error('sense %d raised: %s', sid, exc)
                else:
                    if out['status'] == 'failed':
                        state['senses']['failed'][str(sid)] = out
                    else:
                        state['senses']['done'][str(sid)] = out
                save_state(state)                       # checkpoint every sense
                rate = (time.time() - t0) / completed
                remain = (len(todo) - completed) * rate
                print(f'  [{completed}/{len(todo)}] sense {sid}: '
                      f'{state["senses"]["done"].get(str(sid), {}).get("exercises", 0)} ex  '
                      f'({fmt_hms(remain)} left)')

    calls, usd, nulls = spend_since(db, since)
    state['senses']['calls'] = calls
    state['senses']['usd'] = usd
    save_state(state)
    print(f'  ladder done in {fmt_hms(time.time() - t0)}  {calls} calls  ${usd:.4f}')


def report(state: dict) -> None:
    t = state['tests']
    s = state['senses']
    n_done, n_fail = len(s['done']), len(s['failed'])
    exercises = sum(v.get('exercises', 0) for v in s['done'].values())
    # 'canary' is a list of per-sense runs; its spend is already inside
    # senses['done']/['failed'], so count it from there and never twice.
    canary_usd = sum((r.get('usd') or 0) for r in (state.get('canary') or []))
    usd = (t.get('usd', 0) or 0) + (s.get('usd', 0) or 0) + canary_usd

    print('\n' + '═' * 62)
    print(f'  run {state["run_id"]}  ({LANG_NAME[state["language"]]})')
    print('═' * 62)
    print(f'  tests generated     {t.get("generated", 0)} '
          f'(failed {t.get("failed", 0)})')
    print(f'  senses built        {n_done} (failed {n_fail}) '
          f'of {len(s["selected"])} selected')
    print(f'  ladder exercises    {exercises}')
    print(f'  word_assets         {n_done} senses now carry assets')
    print(f'  total spend         ${usd:.2f}')
    print(f'  state file          {state_path(state["run_id"])}')
    if s['failed']:
        print(f'\n  failed senses (re-run with --resume {state["run_id"]}):')
        for sid, v in list(s['failed'].items())[:10]:
            print(f'    {sid}: {v.get("errors") or v.get("error")}')
    print('═' * 62)


# ── main ───────────────────────────────────────────────────────────────────

ALL_PHASES = ('preflight', 'canary', 'tests', 'select', 'ladder')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--language', choices=sorted(LANG_ID), help='zh | en | ja')
    ap.add_argument('--tests', type=int, default=100)
    ap.add_argument('--test-type', default='listening',
                    choices=['listening', 'reading'])
    ap.add_argument('--difficulty', type=int, default=None,
                    help='fix all tests at 1-9 (default: balanced [1,3,6,9])')
    ap.add_argument('--max-senses', type=int, default=150,
                    help='cap on senses given assets + ladder exercises')
    ap.add_argument('--sense-workers', type=int, default=3,
                    help='senses in flight; each already fans out to 8 threads')
    ap.add_argument('--canary-senses', type=int, default=1,
                    help='senses to prove end-to-end before the batch')
    ap.add_argument('--phases', default=','.join(ALL_PHASES),
                    help=f'comma-separated subset of {",".join(ALL_PHASES)}')
    ap.add_argument('--resume', metavar='RUN_ID',
                    help='continue a previous run from its state file')
    ap.add_argument('--yes', action='store_true',
                    help='skip the confirmation before the long phases')
    args = ap.parse_args()

    logging.basicConfig(
        level=os.getenv('BUILD_LOG_LEVEL', 'INFO').upper(),
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )
    for noisy in ('httpx', 'httpcore', 'openai', 'urllib3'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if not args.resume and not args.language:
        ap.error('--language is required unless --resume is given')

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    if args.resume:
        state = load_state(args.resume)
        print(f'Resuming {state["run_id"]} '
              f'(phases done: {state["phases_done"] or "none"})')
    else:
        state = new_state(args)
        save_state(state)
        print(f'New run {state["run_id"]}')

    phases = [p.strip() for p in args.phases.split(',') if p.strip()]
    bad = [p for p in phases if p not in ALL_PHASES]
    if bad:
        ap.error(f'unknown phase(s): {bad}')

    if 'preflight' in phases:
        problems = phase_preflight(db, state)
        save_state(state)
        if problems:
            print('\nABORT — preflight found blocking problems:')
            for p in problems:
                print(f'  ! {p}')
            return 1
        print('  preflight clean')
        state['phases_done'].append('preflight')
        save_state(state)

    if 'canary' in phases:
        if not phase_canary(db, state):
            return 1
        state['phases_done'].append('canary')
        save_state(state)

    long_phases = [p for p in phases if p in ('tests', 'ladder')]
    if long_phases and not args.yes:
        cfg = state['config']
        per = state.get('canary_mean_seconds')
        est = ''
        if per and 'ladder' in long_phases:
            est = (f'  ladder ~{fmt_hms(cfg["max_senses"] * per / cfg["sense_workers"])}'
                   f' at the observed {fmt_hms(per)}/sense')
        print(f'\nAbout to run: {long_phases}\n'
              f'  {cfg["tests"]} tests (~2.9 min each => ~'
              f'{fmt_hms(cfg["tests"] * 174)})\n{est}')
        if input('Proceed? [y/N] ').strip().lower() != 'y':
            print('Aborted.'); return 1

    if 'tests' in phases:
        phase_tests(db, state)
        state['phases_done'].append('tests')
        save_state(state)

    if 'select' in phases:
        phase_select(db, state)
        state['phases_done'].append('select')
        save_state(state)

    if 'ladder' in phases:
        phase_ladder(db, state)
        state['phases_done'].append('ladder')
        save_state(state)

    report(state)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
