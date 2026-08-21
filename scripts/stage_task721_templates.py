"""Materialise the TASK-721 before/after template bodies onto disk.

`before/` is the live active body of each of the 18 `question_*` rows, plus one
mandatory repair (below). `after/` is `before/` with a distractor-construction
block spliced in at a named anchor. Both are written as files so
`generate_question_sample.py --templates <dir>` can measure either arm without
activating anything, and so the migration and the measurement are generated from
one source of truth and cannot drift.

THE REPAIR -- a live defect found while establishing the baseline
----------------------------------------------------------------
Four active rows contain no case-insensitive `json` token:

    question_vocabulary_context [zh] v2
    question_vocabulary_context [ja] v2
    question_main_idea          [ja] v2
    question_author_purpose     [ja] v2

All four are TASK-722 / TASK-724 native rewrites, and all four lost the token to
the "English metalanguage" sweep. They are all on `qwen/qwen3.7-plus`, which
OpenRouter routes to Alibaba, and Alibaba hard-rejects `response_format=
json_object` when the prompt does not contain the literal word:

    400 invalid_parameter_error: 'messages' must contain the word 'json' in
    some form, to use 'response_format' of type 'json_object'

So those four rows currently fail EVERY generation attempt in production, and
they fail loudly at the call site rather than degrading. The 2026-08-17 note
recorded this failure mode as latent on Qwen3.x; it is not latent, and it is not
confined to the entailment judge.

`JSON` here is machine contract, not leakage -- exactly the category
`rewrite_prompt_native.allowed_latin` already whitelists. The repair is a
single-token insertion into the existing output sentence, listed literally below
so it is reviewable.

The repair is applied to BOTH arms. It has to be: without it there is no
before-arm output for those four cells at all, and a before/after that also
carries a bug fix cannot attribute its own result.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, '.env'))

from services.prompt_service import get_template_config  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

from task721_blocks import ANCHORS, BLOCKS, FAMILY  # noqa: E402

OUT = os.path.join(ROOT, 'data', 'eval', 'task721')
LF, CRLF = chr(10), chr(13) + chr(10)
LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}
TYPES = ('literal_detail', 'supporting_detail', 'main_idea',
         'inference', 'author_purpose', 'vocabulary_context')

# (task, lang) -> (exact substring to find, its replacement). One token each.
JSON_REPAIR: dict[tuple[str, str], tuple[str, str]] = {
    ('question_vocabulary_context', 'zh'): (
        '最终只输出一个对象，', '最终只输出一个 JSON 对象，'),
    ('question_vocabulary_context', 'ja'): (
        '出力は、次のオブジェクトのみとすること。',
        '出力は、次の JSON オブジェクトのみとすること。'),
    ('question_main_idea', 'ja'): (
        '次のオブジェクトだけを出力すること。',
        '次の JSON オブジェクトだけを出力すること。'),
    ('question_author_purpose', 'ja'): (
        '最終的な出力は、次の形式のみとしてください。',
        '最終的な出力は、次の JSON 形式のみとしてください。'),
}


def _apply_once(text: str, old: str, new: str, what: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'[error] {what}: anchor occurs {n}x, expected exactly 1')
    return text.replace(old, new)


def build(db, only: str = 'both') -> list[dict]:
    rows = []
    for tc in TYPES:
        task = f'question_{tc}'
        for lang, lid in LANG_ID.items():
            live = get_template_config(db, task, lid)['template']

            before = live
            repair = JSON_REPAIR.get((task, lang))
            if repair:
                old, new = repair
                # Idempotent: once the repair is applied live (as a hotfix), the
                # source string is gone and the target is already present. Both
                # states are correct; anything else means the row moved under us.
                if new in before and old not in before:
                    pass
                else:
                    before = _apply_once(before, old, new,
                                         f'{task}[{lang}] json repair')
            elif 'json' not in before.lower():
                raise SystemExit(
                    f'[error] {task}[{lang}] has no json token and no repair '
                    f'entry -- it will 400 on a json_object call')

            anchor = ANCHORS[(task, lang)]
            if only == 'before':
                # Still assert the anchor is usable, so a bad anchor is caught
                # now rather than after an authoring run has been paid for.
                _apply_once(before, anchor, anchor, f'{task}[{lang}] block anchor')
                after = ''
            else:
                block = BLOCKS[(FAMILY[tc], lang)][tc]
                # Match the row's own line endings so a spliced row does not end
                # up half CRLF, half LF. See the ANCHORS note.
                if CRLF in before:
                    block = block.replace(CRLF, LF).replace(LF, CRLF)
                after = _apply_once(before, anchor, block + anchor,
                                    f'{task}[{lang}] block anchor')

            rows.append({
                'task': task, 'lang': lang, 'type_code': tc,
                'before': before, 'after': after,
                'repaired': bool(repair),
            })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true',
                    help='validate only, write nothing')
    ap.add_argument('--only', default='both', choices=('before', 'both'),
                    help="'before' skips the blocks (usable pre-authoring)")
    args = ap.parse_args()

    SupabaseFactory.initialize()
    rows = build(get_supabase_admin(), args.only)

    arms = ('before',) if args.only == 'before' else ('before', 'after')
    for arm in arms:
        os.makedirs(os.path.join(OUT, arm), exist_ok=True)

    print(f'{"task":34} {"lang":4} {"before":>7} {"after":>7} {"delta":>6}  repaired')
    for r in rows:
        b, a = r['before'], r['after'] or r['before']
        # str.format must still render, and the three placeholders must survive.
        for ph in ('{prose}', '{difficulty}', '{previous_questions}'):
            if a.count(ph) != b.count(ph) or ph not in a:
                raise SystemExit(f'[error] {r["task"]}[{r["lang"]}] lost {ph}')
        try:
            a.format(prose='x', difficulty=7, previous_questions='y', language='z')
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f'[error] {r["task"]}[{r["lang"]}] render: {exc}')
        for lit in ('"question_text"', '"question_type"', '"choices"',
                    '"answer"', '"explanation"', f'"{r["type_code"]}"'):
            if lit not in a:
                raise SystemExit(f'[error] {r["task"]}[{r["lang"]}] lost {lit}')
        if 'json' not in a.lower():
            raise SystemExit(f'[error] {r["task"]}[{r["lang"]}] after-body has no '
                             f'json token')

        print(f'{r["task"]:34} {r["lang"]:4} {len(b):7} {len(a):7} '
              f'{len(a) - len(b):+6}  {"yes" if r["repaired"] else ""}')

        if not args.check:
            for arm in arms:
                p = os.path.join(OUT, arm, f'{r["task"]}_{r["lang"]}.txt')
                with open(p, 'w', encoding='utf-8', newline='') as fh:
                    fh.write(r[arm])

    if not args.check:
        print(f'\nwrote {len(rows) * len(arms)} files under {OUT}')
        if 'after' in arms:
            for r in rows:
                h = hashlib.md5(r['after'].encode()).hexdigest()
                print(f'  after {r["task"]:34} {r["lang"]:4} md5 {h}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
