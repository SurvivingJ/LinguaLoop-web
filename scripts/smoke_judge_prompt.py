"""Prove a rewritten judge prompt still points the right way, before it goes live.

`rewrite_prompt_native.py` verifies *mechanics* — placeholders, literals, brace
doubling, no leaked Latin. It cannot verify *orientation*, and orientation is
where these two judges fail silently:

  * ``cloze.py:110`` — ``verdicts[d] = 'reject' if v == 'reject' else 'keep'``.
    Any other string, including a translated verdict word or a swapped one,
    falls through to ``keep``. Every distractor survives, no exception is
    raised, and the judge is an expensive no-op.
  * ``translation_uniqueness.py:13-26`` — the Likert scale is inverted relative
    to intuition (5 = clearly NOT an acceptable translation = ideal distractor).
    A prompt that flips it keeps precisely the also-correct options the judge
    exists to delete, and the item still looks well-formed.

Neither failure raises. Both silently degrade content. So each fixture below
pins an *expected* verdict, and the script fails if the judge disagrees.

Fixtures are deliberately unambiguous — a competent native speaker would not
hesitate on any of them. A disagreement means the prompt is wrong, not that the
fixture is hard.

Usage::

    python scripts/smoke_judge_prompt.py --task cloze_distractor_judge --lang zh \\
        --file data/eval/cloze_distractor_judge_zh.txt

    # test the live DB row instead of a candidate file
    python scripts/smoke_judge_prompt.py --task cloze_distractor_judge --lang zh --live

Every call is logged to `llm_calls` under `pipeline='diag'`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.llm_service import call_llm  # noqa: E402
from services.prompt_service import get_template_config  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402
from services.test_generation.schemas import likert_to_verdict  # noqa: E402

LANG_ID = {'zh': 1, 'ja': 3}

# Model used when testing a *file* (no DB row to read a model from). Matches the
# live rows' class of model so the test is representative.
FALLBACK_MODEL = {
    'cloze_distractor_judge': {'zh': 'deepseek/deepseek-chat',
                               'ja': 'qwen/qwen-2.5-72b-instruct'},
    'translation_uniqueness_judge': {'zh': 'qwen/qwen3.7-plus',
                                     'ja': 'google/gemini-3.5-flash-lite'},
}

# ---------------------------------------------------------------------------
# Fixtures — (render kwargs, [expected verdict per candidate])
# ---------------------------------------------------------------------------

CLOZE_FIXTURES = {
    'zh': [
        {
            'name': 'synonym must be rejected, nonsense kept',
            'args': {
                'sentence_with_blank': '他每天早上六点______床，从不赖床。',
                'correct_answer': '起',
                # 1: 'a synonym that also works -> reject
                # 2/3: clearly impossible in this slot -> keep
                'distractors': ['爬', '吃', '蓝色'],
            },
            'expect': ['reject', 'keep', 'keep'],
        },
        {
            'name': 'collocation violation kept',
            'args': {
                'sentence_with_blank': '我们下午三点______一个会，讨论明年的计划。',
                'correct_answer': '开',
                'distractors': ['举行', '做', '喝'],
            },
            'expect': ['reject', 'keep', 'keep'],
        },
    ],
    'ja': [
        {
            'name': 'acceptable alternative rejected, nonsense kept',
            'args': {
                'sentence_with_blank': '毎朝六時に______、決して寝坊しない。',
                'correct_answer': '起きて',
                'distractors': ['起床して', '食べて', '青くて'],
            },
            'expect': ['reject', 'keep', 'keep'],
        },
        {
            'name': 'particle/collocation violation kept',
            'args': {
                'sentence_with_blank': '午後三時に会議を______、来年の計画を話し合う。',
                'correct_answer': '開いて',
                'distractors': ['行って', '飲んで', '登って'],
            },
            'expect': ['reject', 'keep', 'keep'],
        },
    ],
}

TRANSLATION_FIXTURES = {
    'zh': [
        {
            'name': 'paraphrase is also-correct (low), meaning-change is ideal (high)',
            'args': {
                'tl_sentence': '他昨天把书还给图书馆了。',
                'correct_translation': 'He returned the book to the library yesterday.',
                'nl_language': 'English',
                # 1: same meaning, only article/number nuance -> also correct -> reject
                # 2: negation flipped -> ideal distractor -> accept
                # 3: different participants -> ideal distractor -> accept
                'candidates': [
                    'Yesterday he gave the book back to the library.',
                    'He did not return the book to the library yesterday.',
                    'The librarian returned the book to him yesterday.',
                ],
            },
            'expect': ['reject', 'accept', 'accept'],
        },
    ],
    'ja': [
        {
            'name': 'paraphrase is also-correct (low), meaning-change is ideal (high)',
            'args': {
                'tl_sentence': '彼は昨日、本を図書館に返しました。',
                'correct_translation': 'He returned the book to the library yesterday.',
                'nl_language': 'English',
                'candidates': [
                    'Yesterday he gave the book back to the library.',
                    'He did not return the book to the library yesterday.',
                    'The librarian returned the book to him yesterday.',
                ],
            },
            'expect': ['reject', 'accept', 'accept'],
        },
    ],
}


def _load_template(task: str, lang: str, path: str | None, live: bool) -> tuple[str, str]:
    if live:
        SupabaseFactory.initialize()
        cfg = get_template_config(get_supabase_admin(), task, LANG_ID[lang])
        return cfg['template'], cfg['model']
    with open(path, encoding='utf-8') as handle:
        return handle.read(), FALLBACK_MODEL[task][lang]


def _run_cloze(template: str, model: str, fixture: dict) -> list[str]:
    distractors = fixture['args']['distractors']
    numbered = '\n'.join(f'{i + 1}. {d}' for i, d in enumerate(distractors))
    prompt = template.format(
        sentence_with_blank=fixture['args']['sentence_with_blank'],
        correct_answer=fixture['args']['correct_answer'],
        distractors_numbered=numbered,
    )
    result = call_llm(prompt, model=model, temperature=0.0, response_format='json',
                      provider='openrouter', pipeline='diag',
                      task_name='cloze_distractor_judge_smoke', timeout=180)
    if not isinstance(result, dict):
        raise RuntimeError(f'non-dict response: {result!r}')

    # Mirror cloze.py:109-110 exactly, including its fallthrough.
    verdicts = []
    for idx in range(len(distractors)):
        entry = result.get(str(idx + 1)) or {}
        value = str(entry.get('verdict', 'keep')).strip().lower() if isinstance(entry, dict) else 'keep'
        verdicts.append('reject' if value == 'reject' else 'keep')
    return verdicts


def _run_translation(template: str, model: str, fixture: dict) -> list[str]:
    candidates = fixture['args']['candidates']
    numbered = '\n'.join(f'{i + 1}. {c}' for i, c in enumerate(candidates))
    prompt = template.format(
        tl_sentence=fixture['args']['tl_sentence'],
        correct_translation=fixture['args']['correct_translation'],
        nl_language=fixture['args']['nl_language'],
        candidates_numbered=numbered,
    )
    result = call_llm(prompt, model=model, temperature=0.0, response_format='json',
                      provider='openrouter', pipeline='diag',
                      task_name='translation_uniqueness_judge_smoke', timeout=180)
    if not isinstance(result, dict):
        raise RuntimeError(f'non-dict response: {result!r}')

    # Mirror translation_uniqueness.py:219-231.
    verdicts = []
    for idx in range(len(candidates)):
        entry = result.get(str(idx + 1))
        if not isinstance(entry, dict):
            verdicts.append('flag')
            continue
        try:
            verdicts.append(likert_to_verdict(float(entry.get('rating'))))
        except (TypeError, ValueError):
            verdicts.append('flag')
    return verdicts


RUNNERS = {
    'cloze_distractor_judge': (_run_cloze, CLOZE_FIXTURES),
    'translation_uniqueness_judge': (_run_translation, TRANSLATION_FIXTURES),
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--task', required=True, choices=sorted(RUNNERS))
    parser.add_argument('--lang', required=True, choices=sorted(LANG_ID))
    parser.add_argument('--file', help='candidate template file to test')
    parser.add_argument('--live', action='store_true',
                        help='test the active DB row instead of a file')
    args = parser.parse_args()

    if not args.live and not args.file:
        parser.error('pass --file or --live')

    template, model = _load_template(args.task, args.lang, args.file, args.live)
    if not args.live:
        SupabaseFactory.initialize()   # call_llm logs to llm_calls
    runner, fixtures = RUNNERS[args.task]

    print(f'{args.task} [{args.lang}] on {model}\n')
    failures = 0

    for fixture in fixtures[args.lang]:
        try:
            actual = runner(template, model, fixture)
        except Exception as exc:
            print(f'  FAIL {fixture["name"]}: {type(exc).__name__}: {exc}')
            failures += 1
            continue

        expected = fixture['expect']
        ok = actual == expected
        print(f'  {"OK  " if ok else "FAIL"} {fixture["name"]}')
        print(f'         expected: {expected}')
        print(f'         actual  : {actual}')
        if not ok:
            failures += 1
            # Name the consequence, not just the mismatch.
            if args.task == 'cloze_distractor_judge' and 'reject' in expected:
                print('         => an also-acceptable distractor was KEPT: the item '
                      'now has two correct answers.')
            if args.task == 'translation_uniqueness_judge':
                print('         => scale may be inverted; check the 5-vs-1 direction '
                      'in the prompt against translation_uniqueness.py:17-21.')

    total = len(fixtures[args.lang])
    print(f'\n{total - failures}/{total} fixtures passed')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
