"""Generate a fresh question sample from a chosen set of `question_*` templates.

TASK-721. `measure_judge_flag_rate.py` judges a sample; it does not generate one.
This script is the missing half: it produces a sample JSON in exactly the shape
that harness consumes (`qid, lang, passage, question, answer, distractors,
type_code`), so the two compose:

    python scripts/generate_question_sample.py --arm before --templates live \
        --out data/eval/task721_before.json
    python scripts/measure_judge_flag_rate.py --sample data/eval/task721_before.json \
        --langs zh --arms "live=6:"        # zh judge is v6
    python scripts/measure_judge_flag_rate.py --sample data/eval/task721_before.json \
        --langs en,ja --arms "live=4:"     # en/ja judge is v4

WHY A VERSION OVERRIDE INSTEAD OF ACTIVATING ROWS
-------------------------------------------------
`prompt_service.get_template_config` filters `is_active = true` and has no
version argument, so there is no way to ask the DB for "v3 of question_main_idea"
while v1 stays live. But `QuestionGenerator.generate_question` already accepts a
`prompt_template=` string, and the orchestrator is its only production caller.
So `--templates <dir>` reads the staged prompt bodies off disk and passes them
in directly. Measuring an inactive prompt therefore never requires activating it
-- which is the whole point, because activating 18 rows to find out whether they
help is the mistake TASK-717 spent a day undoing.

EXPERIMENTAL DESIGN
-------------------
* Passages are drawn from `data/eval/entailment_sample_150.json` -- the same
  frozen material the rest of this workstream measured on. Both arms see the
  SAME passages in the SAME order, so the arms differ only in prompt text.
* Difficulty cycles 4 / 6 / 8 across passages (identically in both arms) so the
  three `vocabulary_context` difficulty tiers are all exercised. A fixed
  difficulty would measure one third of that prompt.
* Six question types per passage, generated in a fixed order with
  `previous_questions` accumulating -- as `generate_questions` does in
  production.
* ONE SHOT PER CELL. Production retries a failed question with an
  `avoid_context` block appended, which mutates the prompt under measurement.
  Regeneration is therefore disabled here and failures are counted instead.
* `pipeline='diag'` so this spend does not contaminate per-pipeline production
  cost reporting.

MODEL. Never overridden. Production resolves the question model from
`prompt_templates.model` of `question_literal_detail` for that language
(`database_client._resolve_models`), and this script resolves it the same way.
TASK-717 froze the model during a prompt A/B for a reason: a run that varies
both is uninterpretable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, '.env'))

from services.llm_service import call_llm  # noqa: E402
from services.prompt_service import get_template_config  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402
from services.test_generation.config import get_test_gen_config  # noqa: E402
from services.test_generation.schemas import MCQuestion  # noqa: E402

LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}
LANG_NAME = {1: 'zh', 2: 'en', 3: 'ja'}
# `language_name` as dim_languages spells it -- the value the orchestrator feeds
# the optional {language} placeholder.
LANG_FULL = {1: 'Chinese', 2: 'English', 3: 'Japanese'}

TYPES = (
    'literal_detail',
    'supporting_detail',
    'main_idea',
    'inference',
    'author_purpose',
    'vocabulary_context',
)

DIFFICULTIES = (4, 6, 8)

SAMPLE_SRC = os.path.join(ROOT, 'data', 'eval', 'entailment_sample_150.json')

# Passages outside this band are excluded: a 54-character passage cannot carry
# six distinct questions, and a 6k one triples the token bill for no more signal.
MIN_CHARS, MAX_CHARS = 200, 2500

_print_lock = Lock()
_done = [0]


# --------------------------------------------------------------------- inputs


def load_passages(
    langs: list[int], n: int, exclude: set[str] | None = None
) -> dict[int, list[str]]:
    """Distinct passages per language, deterministic order.

    Sorted by (length, text) rather than shuffled: reproducible without a seed
    argument, and stable if the source file is ever re-serialised.

    `exclude` drops passages already used by an earlier sample, which is what
    makes a top-up run additive: without it, re-running with a different `n`
    re-picks overlapping passages and the merged sample carries twelve
    questions off one passage instead of six.
    """
    with open(SAMPLE_SRC, encoding='utf-8') as fh:
        rows = json.load(fh)

    exclude = exclude or set()
    out: dict[int, list[str]] = {}
    for lang in langs:
        seen: dict[str, None] = {}
        for r in rows:
            if r['lang'] != lang:
                continue
            p = (r.get('passage') or '').strip()
            if MIN_CHARS <= len(p) <= MAX_CHARS and p not in exclude:
                seen[p] = None
        ordered = sorted(seen, key=lambda p: (len(p), p))
        if len(ordered) < n:
            raise SystemExit(
                f'[error] only {len(ordered)} usable passages for '
                f'{LANG_NAME[lang]}, asked for {n}'
            )
        # Spread the pick across the length range instead of taking the n
        # shortest, which would bias every arm toward thin passages.
        step = len(ordered) / n
        out[lang] = [ordered[int(i * step)] for i in range(n)]
    return out


def load_templates(db, langs: list[int], source: str) -> dict[tuple[int, str], str]:
    """Template body per (language_id, type_code).

    `source == 'live'` reads the active row; anything else is a directory of
    `question_<type>_<lang>.txt` files -- the staged bodies.
    """
    tpl: dict[tuple[int, str], str] = {}
    for lang in langs:
        for tc in TYPES:
            task = f'question_{tc}'
            if source == 'live':
                tpl[(lang, tc)] = get_template_config(db, task, lang)['template']
            else:
                path = os.path.join(source, f'{task}_{LANG_NAME[lang]}.txt')
                if not os.path.exists(path):
                    raise SystemExit(f'[error] missing staged template {path}')
                # newline='' — read the staged bytes as staged. Nine rows are
                # CRLF in the table; universal-newline translation would measure
                # a body that differs from the one the migration lands.
                with open(path, encoding='utf-8', newline='') as fh:
                    tpl[(lang, tc)] = fh.read()
    return tpl


def resolve_models(db, langs: list[int]) -> dict[int, str]:
    """Same representative task production uses -- see _resolve_models."""
    return {
        lang: get_template_config(db, 'question_literal_detail', lang)['model']
        for lang in langs
    }


# ------------------------------------------------------------------ generation


def _generate_one(prompt: str, model: str, tc: str, total: int) -> MCQuestion | None:
    try:
        q = call_llm(
            prompt,
            model=model,
            temperature=get_test_gen_config().question_temperature,
            response_format='json_object',
            schema=MCQuestion,
            timeout=60,
            pipeline='diag',
            task_name=f'task721_question_{tc}',
        )
    except Exception as exc:  # noqa: BLE001 -- one bad cell must not lose the run
        with _print_lock:
            print(f'  [fail] {tc}: {type(exc).__name__}: {exc}', flush=True)
        q = None
    with _print_lock:
        _done[0] += 1
        if _done[0] % 10 == 0 or _done[0] == total:
            print(f'  [{_done[0]}/{total}]', flush=True)
    return q


def _run_passage(job) -> list[dict]:
    """All six types for one passage, sequentially, accumulating history.

    Sequential within a passage is not an optimisation choice -- it is what
    `previous_questions` means. Parallelism happens across passages.
    """
    lang, passage, difficulty, tpl, model, total = job
    previous: list[str] = []
    rows: list[dict] = []
    for tc in TYPES:
        prompt = tpl[(lang, tc)].format(
            prose=passage,
            difficulty=difficulty,
            previous_questions='; '.join(previous) if previous else 'None',
            language=LANG_FULL[lang],
        )
        q = _generate_one(prompt, model, tc, total)
        if q is None:
            continue
        previous.append(q.question_text)
        rows.append({
            'qid': str(uuid.uuid4()),
            'lang': lang,
            'passage': passage,
            'question': q.question_text,
            'answer': q.answer,
            'distractors': [c for c in q.choices if c != q.answer],
            'type_code': tc,
            'difficulty': difficulty,
            'answer_index': q.correct_answer_index,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--arm', default='before', help='label recorded in the output')
    ap.add_argument('--templates', default='live',
                    help="'live' (active rows) or a directory of staged bodies")
    ap.add_argument('--passages', type=int, default=8, help='passages per language')
    ap.add_argument('--langs', default='zh,en,ja')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--exclude-passages', action='append', default=[],
                    help='sample JSON whose passages this run must not reuse '
                         '(repeatable) — for topping an existing sample up')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    langs = [LANG_ID[n.strip()] for n in args.langs.split(',') if n.strip()]

    exclude: set[str] = set()
    for path in args.exclude_passages:
        with open(path, encoding='utf-8') as fh:
            exclude |= {(r.get('passage') or '').strip() for r in json.load(fh)}
    if exclude:
        print(f'excluding {len(exclude)} passages already sampled')

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    passages = load_passages(langs, args.passages, exclude)
    tpl = load_templates(db, langs, args.templates)
    models = resolve_models(db, langs)

    print(f'arm {args.arm}: templates={args.templates}')
    for lang in langs:
        print(f'  {LANG_NAME[lang]}: {len(passages[lang])} passages, '
              f'model={models[lang]}')

    total = sum(len(passages[lang]) for lang in langs) * len(TYPES)
    jobs = [
        (lang, p, DIFFICULTIES[i % len(DIFFICULTIES)], tpl, models[lang], total)
        for lang in langs
        for i, p in enumerate(passages[lang])
    ]

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        rows = [r for batch in ex.map(_run_passage, jobs) for r in batch]
    elapsed = time.time() - t0

    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)

    got = Counter(LANG_NAME[r['lang']] for r in rows)
    print(f'\ngenerated {len(rows)}/{total} questions {dict(got)}')
    print(f'wall clock: {elapsed / 60:.1f} min -> {args.out}')
    if len(rows) < total:
        print(f'[warn] {total - len(rows)} cells failed and are absent from the '
              f'sample; per-arm denominators differ -- report rates, not counts')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
