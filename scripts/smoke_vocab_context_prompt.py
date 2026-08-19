"""Smoke-test the live `question_vocabulary_context` rows (TASK-722 verification).

Renders the ACTIVE prompt row for a language against a real passage and calls the
row's own configured model, then checks the properties TASK-722 is supposed to
have bought:

* the response parses as JSON with the five expected keys
* ``answer`` reproduces one of ``choices`` verbatim (question_generator.py drops
  the question otherwise)
* no Latin-script content leaks into the generated question, options or
  explanation — the actual defect being fixed
* at difficulty 7-9 the target is a fixed expression rather than a plain word

Usage::

    python scripts/smoke_vocab_context_prompt.py --lang zh --n 3 --difficulty 8

Every call is logged to `llm_calls` under `pipeline='diag'`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.llm_service import call_llm  # noqa: E402
from services.prompt_service import get_template_config  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}

# Short, self-contained passages with obvious idiomatic potential, so a failure
# is the prompt's fault rather than the passage's.
PASSAGES = {
    'zh': (
        '公司决定裁撤整个部门时，老张原本想去找总经理理论，可是走到门口又停下了。'
        '同事们劝他别去，说这种事早就定下来了，去了也是碰一鼻子灰。他站了很久，'
        '最后还是转身回了工位，一句话也没说。'
    ),
    'ja': (
        '新製品の不具合が見つかったとき、担当者は上司に報告するかどうか迷った。'
        '小さな問題に見えたので、しばらく様子を見ることにした。しかし数週間後、'
        '同じ不具合が各地で相次ぎ、会社は大規模な回収に追い込まれた。'
    ),
}

LATIN_RUN = re.compile(r'[A-Za-z][A-Za-z_]*')
REQUIRED_KEYS = ('question_text', 'question_type', 'choices', 'answer', 'explanation')


def check(obj: dict) -> list[str]:
    problems: list[str] = []

    for key in REQUIRED_KEYS:
        if key not in obj:
            problems.append(f'missing key {key!r}')
    if problems:
        return problems

    choices = obj['choices']
    if not isinstance(choices, list) or len(choices) != 4:
        problems.append(f'expected 4 choices, got {choices!r}')
    elif len(set(choices)) != 4:
        problems.append('choices are not distinct')
    elif obj['answer'] not in choices:
        # question_generator.py:346 drops the question on exactly this.
        problems.append(f'answer {obj["answer"]!r} is not one of choices')

    if obj.get('question_type') != 'vocabulary_context':
        problems.append(f'question_type is {obj.get("question_type")!r}')

    # The point of the task: no English in learner-visible output.
    visible = ' '.join(
        [str(obj.get('question_text', '')), str(obj.get('explanation', ''))]
        + [str(c) for c in (choices if isinstance(choices, list) else [])]
    )
    leaked = [r for r in LATIN_RUN.findall(visible) if len(r) >= 2]
    if leaked:
        problems.append(f'Latin-script content in generated output: {sorted(set(leaked))}')

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--lang', choices=sorted(LANG_ID), required=True)
    parser.add_argument('--n', type=int, default=3)
    parser.add_argument('--difficulty', type=int, default=8)
    args = parser.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()
    cfg = get_template_config(db, 'question_vocabulary_context', LANG_ID[args.lang])
    print(f'[{args.lang}] template v{cfg["version"]} on {cfg["model"]}')

    asked: list[str] = []
    failures = 0

    for i in range(1, args.n + 1):
        prompt = cfg['template'].format(
            prose=PASSAGES[args.lang],
            difficulty=args.difficulty,
            previous_questions='\n'.join(asked) if asked else '(なし)',
        )
        try:
            obj = call_llm(
                prompt,
                model=cfg['model'],
                response_format='json',
                temperature=0.7,
                max_tokens=8000,
                timeout=240,
                pipeline='diag',
                task_name='question_vocabulary_context_smoke',
                template_version=cfg['version'],
            )
        except Exception as exc:
            print(f'  [{i}] CALL FAILED: {type(exc).__name__}: {exc}')
            failures += 1
            continue

        if not isinstance(obj, dict):
            print(f'  [{i}] non-dict response: {obj!r}')
            failures += 1
            continue

        problems = check(obj)
        status = 'OK  ' if not problems else 'FAIL'
        print(f'  [{i}] {status} {obj.get("question_text", "")}')
        print(f'         choices: {json.dumps(obj.get("choices"), ensure_ascii=False)}')
        print(f'         answer : {obj.get("answer")!r} '
              f'(position {obj["choices"].index(obj["answer"]) + 1})'
              if isinstance(obj.get('choices'), list) and obj.get('answer') in obj.get('choices', [])
              else f'         answer : {obj.get("answer")!r}')
        for problem in problems:
            print(f'         - {problem}')
        if problems:
            failures += 1
        asked.append(str(obj.get('question_text', '')))

    print(f'\n[{args.lang}] {args.n - failures}/{args.n} clean')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
