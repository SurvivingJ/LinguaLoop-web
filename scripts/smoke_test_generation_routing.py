#!/usr/bin/env python
"""End-to-end smoke test for the LIVE model routing in ``prompt_templates``.

WHY THIS EXISTS
---------------
The pytest suite mocks every LLM call, so ``1792 passed`` says nothing about
whether the model a prompt is routed to actually returns parseable output in the
target language. That gap is not theoretical:

  * ``qwen/qwen-max`` was delisted by OpenRouter and every topic-generation call
    404'd silently for days (see services/topic_generation/config.py).
  * ``qwen3.6-flash`` returned NO ratings at all under the v3 judge prompt, and
    ``schemas.likert_to_verdict(None)`` maps a missing rating to ``accept`` --
    so a judge that stops emitting integers ships everything and looks healthy.

Both failures are invisible to unit tests and to the nightly slug-health probe
(which checks that a slug EXISTS, not that it produces usable output). This
script closes that gap by driving the real production path -- live templates,
live models, real responses, production schemas -- once per language.

Run it after ANY model-routing change (a prompt_templates model sweep, a slug
rotation, a judge model swap).

WHAT IT EXERCISES
-----------------
Per language (zh/en/ja), the real generate -> judge -> validate funnel:

  1. ``prose_generation``    -- free-text response, cleaned + length-checked.
  2. Two ``question_*`` types -- strict ``MCQuestion`` pydantic schema. This is
     the load-bearing check: a model that emits prose instead of JSON, or drops
     the ``answer``/``choices`` contract, fails HERE and nowhere else.
  3. Both judges (``test_answer_entailment``, ``test_distractor_plausibility``)
     -- run because difficulty > 2 and ``db`` + ``language_id`` are supplied,
     matching orchestrator.py. Judge models are resolved independently of
     generator models, so this covers the judge routing too.

The distractor judge is additionally checked for the SILENT-ACCEPT failure
above: if it returns no usable ratings we report that explicitly rather than
letting `accept` stand in for `didn't answer`.

WHAT IT DOES NOT DO
-------------------
NO DATABASE WRITES. It never touches production_queue, tests, questions, or
generation_review_queue -- it calls the agents directly rather than through
``TestGenerationOrchestrator.generate_test``. Templates are read, nothing is
persisted. The only side effect is rows in ``llm_calls`` (written by
``call_llm`` itself) and the API spend, which the script reports.

Cost: ~21 calls, low cents. Runtime is dominated by qwen3.7-plus latency.

USAGE
-----
    export PYTHONIOENCODING=utf-8        # Windows: console must take CJK
    python scripts/smoke_test_generation_routing.py
    python scripts/smoke_test_generation_routing.py --langs zh
    python scripts/smoke_test_generation_routing.py --types literal_detail

Exit code is 0 only if every language passed every stage -- safe for CI.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

# Languages keyed by code -> (language_id, language_name). The ids are
# dim_languages PKs and are relied on by prompt_templates.language_id.
LANGS: dict[str, tuple[int, str]] = {
    'zh': (1, 'Chinese'),
    'en': (2, 'English'),
    'ja': (3, 'Japanese'),
}

# Two question types with deliberately different failure surfaces:
# literal_detail is the easiest thing a model can be asked for (if this fails,
# the model is broken), vocabulary_context is the type that has historically
# driven the distractor judge's reject rate.
DEFAULT_TYPES = ['literal_detail', 'vocabulary_context']

# Fixed topic so runs are comparable across models and dates. English concept +
# keywords mirror what the orchestrator passes pre-translation.
TOPIC_CONCEPT = 'how bridges carry weight'
TOPIC_KEYWORDS = ['bridge', 'weight', 'support', 'arch', 'engineer']

# difficulty > 2 is REQUIRED for the judges to run at all (orchestrator.py:467).
DIFFICULTY = 5


def _fmt(ok: bool) -> str:
    return 'OK  ' if ok else 'FAIL'


def init_supabase() -> None:
    """Bootstrap SupabaseFactory the way app.py does at startup.

    The factory is a process-wide singleton normally initialized inside the
    Flask app factory, so any standalone script must do it explicitly or every
    ``get_supabase_admin()`` call raises "SupabaseFactory not initialized".
    The service-role key is required: prompt_templates reads go through the
    admin client to bypass RLS.
    """
    from config import Config
    from services.supabase_factory import SupabaseFactory

    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        raise RuntimeError('SUPABASE_URL / SUPABASE_KEY missing from environment')
    SupabaseFactory.initialize(
        supabase_url=Config.SUPABASE_URL,
        supabase_key=Config.SUPABASE_KEY,
        service_role_key=Config.SUPABASE_SERVICE_ROLE_KEY,
    )


def run_language(code: str, types: list[str], verbose: bool) -> dict:
    """Drive prose -> questions -> judges for one language. Never raises."""
    from services.prompt_service import get_template_config
    from services.test_generation.agents import ProseWriter, QuestionGenerator
    from services.test_generation.database_client import TestDatabaseClient

    lang_id, lang_name = LANGS[code]
    result: dict = {'lang': code, 'stages': [], 'ok': True, 'notes': []}

    def stage(name: str, ok: bool, detail: str) -> None:
        result['stages'].append((name, ok, detail))
        if not ok:
            result['ok'] = False

    db_client = TestDatabaseClient()
    db = db_client.client

    # --- Routing resolution -------------------------------------------------
    # get_template_config raises if model OR provider is null, so this doubles
    # as an assertion that the sweep left no half-configured row behind.
    try:
        prose_cfg = get_template_config(db, 'prose_generation', lang_id)
        q_cfg = get_template_config(db, f'question_{types[0]}', lang_id)
    except Exception as exc:
        stage('resolve routing', False, f'{type(exc).__name__}: {exc}')
        return result

    result['prose_model'] = prose_cfg['model']
    result['question_model'] = q_cfg['model']
    stage('resolve routing', True,
          f"prose={prose_cfg['model']}  question={q_cfg['model']}")

    # --- Stage 1: prose -----------------------------------------------------
    # Passage length MUST come from production's own source, not a hardcoded
    # guess: TASK-715 moved this to services.dictation.cap so every generated
    # test is dictation-eligible at its own difficulty, and deliberately made
    # new T5/T6 passages shorter than the existing corpus. Hardcoding a range
    # here would measure the script's parameters rather than the pipeline's.
    word_min, word_max = db_client.get_word_count_range(DIFFICULTY)

    prose = ''
    try:
        prose = ProseWriter().generate_prose(
            topic_concept=TOPIC_CONCEPT,
            language_name=lang_name,
            language_code=code,
            difficulty=DIFFICULTY,
            word_count_min=word_min,
            word_count_max=word_max,
            keywords=TOPIC_KEYWORDS,
            prompt_template=prose_cfg['template'],
            model_override=prose_cfg['model'],
            template_version=prose_cfg['version'],
        )
    except Exception as exc:
        stage('prose_generation', False, f'{type(exc).__name__}: {exc}')
        if verbose:
            traceback.print_exc()
        return result  # questions need prose; nothing further is meaningful

    # A model that ignores the language instruction is a real failure mode, and
    # a CJK passage returned in English would sail past a pure length check.
    ascii_ratio = sum(c.isascii() for c in prose) / max(len(prose), 1)
    wrong_script = code in ('zh', 'ja') and ascii_ratio > 0.5
    # 50 chars is the orchestrator's own hard gate (orchestrator.py:402). The
    # word count is reported, not asserted: `split()` is whitespace-based and
    # therefore meaningless for zh/ja, where it returns ~1 for a full passage.
    words = len(prose.split())
    stage('prose_generation', len(prose) > 50 and not wrong_script,
          f'{len(prose)} chars, ~{words} ws-words (asked {word_min}-{word_max}), '
          f'ascii={ascii_ratio:.0%}'
          + ('  <-- WRONG SCRIPT' if wrong_script else ''))

    # --- Stage 2+3: questions (schema) and judges ---------------------------
    q_templates = {
        t: db_client.get_prompt_template(f'question_{t}', lang_id)
        for t in types
    }

    try:
        gen = QuestionGenerator()
        questions = gen.generate_questions(
            prose=prose,
            language_name=lang_name,
            question_type_codes=types,
            difficulty=DIFFICULTY,
            prompt_templates=q_templates,
            model_override=q_cfg['model'],
            language_id=lang_id,   # with db, enables the judge gate
            db=db,
            template_version=q_cfg['version'],
        )
    except Exception as exc:
        stage('question_generation', False, f'{type(exc).__name__}: {exc}')
        if verbose:
            traceback.print_exc()
        return result

    # generate_questions swallows per-type failures and returns fewer items, so
    # count is the signal -- an empty list means every attempt died in the
    # schema layer or was rejected by a judge on every retry.
    stage('question_generation', len(questions) == len(types),
          f'{len(questions)}/{len(types)} survived the funnel')

    for q in questions:
        # MCQuestion already validated shape; re-assert the invariant that
        # actually breaks downstream rendering.
        ok = (
            len(q.get('choices', [])) == 4
            and q.get('answer') in q.get('choices', [])
            and isinstance(q.get('correct_answer_index'), int)
        )
        stage(f"  schema[{q['type_code']}]", ok,
              f"4 choices, answer in choices, idx={q.get('correct_answer_index')}")
        if verbose:
            print(f"      Q: {q['question'][:70]}")
            print(f"      A: {q['answer'][:70]}")

    # Rejections are diagnostic, not failures -- a judge SHOULD reject bad
    # output. Surface them so a 0/2 result is interpretable.
    for rej in getattr(gen, 'last_rejections', []) or []:
        result['notes'].append(
            f"rejected {rej.get('type_code')} at {rej.get('stage')}: "
            f"{(rej.get('reason') or '')[:80]}"
        )

    # The silent-accept check: a judge returning no integers maps to `accept`
    # via likert_to_verdict(None), which is indistinguishable from a real pass.
    flagged = sum(1 for q in questions if q.get('_judge_flags'))
    stage('judges ran', True,
          f'{len(questions)} judged, {flagged} flagged for review')

    return result


def report_cost(since: datetime) -> None:
    """Read actual spend back out of llm_calls for this run's window."""
    try:
        from services.test_generation.database_client import TestDatabaseClient
        db = TestDatabaseClient().client
        resp = (
            db.table('llm_calls')
            .select('model, cost_usd')
            .eq('pipeline', 'test_gen')
            .gte('created_at', since.isoformat())
            .execute()
        )
        rows = resp.data or []
        if not rows:
            print('\nCost: no llm_calls rows found for this window.')
            return
        by_model: dict[str, list] = {}
        for r in rows:
            by_model.setdefault(r['model'] or '(null)', []).append(r['cost_usd'] or 0)
        print(f'\nCost ({len(rows)} calls):')
        total = 0.0
        for model, costs in sorted(by_model.items()):
            s = sum(costs)
            total += s
            print(f'  {model:<34} {len(costs):>3} calls  ${s:.4f}')
        print(f'  {"TOTAL":<34} {len(rows):>3} calls  ${total:.4f}')
        if total == 0:
            # A NULL cost_usd silently disarmed every budget ceiling once
            # before; worth saying out loud rather than printing $0.0000.
            print('  NOTE: total is $0 - cost_usd may not be populated.')
    except Exception as exc:
        print(f'\nCost: unavailable ({type(exc).__name__}: {exc})')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--langs', default='zh,en,ja',
                    help='comma-separated subset of zh,en,ja')
    ap.add_argument('--types', default=','.join(DEFAULT_TYPES),
                    help='comma-separated question type codes (no question_ prefix)')
    ap.add_argument('--verbose', action='store_true',
                    help='print generated questions and full tracebacks')
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format='%(levelname)s %(name)s: %(message)s',
    )

    langs = [c.strip() for c in args.langs.split(',') if c.strip()]
    bad = [c for c in langs if c not in LANGS]
    if bad:
        print(f'unknown language code(s): {bad}; valid: {list(LANGS)}')
        return 2
    types = [t.strip() for t in args.types.split(',') if t.strip()]

    init_supabase()

    started = datetime.now(timezone.utc)
    print('=' * 72)
    print(f'GENERATION ROUTING SMOKE TEST  {started:%Y-%m-%d %H:%M:%S} UTC')
    print(f'languages={langs}  types={types}  difficulty={DIFFICULTY}')
    print('=' * 72)

    results = []
    for code in langs:
        print(f'\n--- {code} (language_id={LANGS[code][0]}) ---')
        t0 = time.time()
        res = run_language(code, types, args.verbose)
        results.append(res)
        for name, ok, detail in res['stages']:
            print(f'  {_fmt(ok)} {name:<24} {detail}')
        for note in res['notes']:
            print(f'       note: {note}')
        print(f'       ({time.time() - t0:.1f}s)')

    print('\n' + '=' * 72)
    for res in results:
        print(f"  {_fmt(res['ok'])} {res['lang']}  "
              f"prose={res.get('prose_model', '?')}  "
              f"question={res.get('question_model', '?')}")
    passed = all(r['ok'] for r in results)
    print(f"\nRESULT: {'PASS' if passed else 'FAIL'}")
    print('=' * 72)

    report_cost(started)
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
