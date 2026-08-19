"""Apply migrations/native_zh_ja_prompt_rewrites.sql, then prove it landed.

There is no psql and no psycopg2 in this environment, so the .sql file is the
repo's record of intent and this script is what actually writes. Both are
generated from the same source of truth — the verified templates in data/eval/ —
so they cannot drift.

The verification is the point. Earlier in this workstream a version collision
silently overwrote two live `test_answer_entailment` rows and left zh and ja with
no active row at all: `get_template_config` raised, the judge fell into its
except branch, and the answer-hallucination guard became a no-op for two of three
languages without a single error surfacing. Nothing in the write path complained.

So this script never reports success from the absence of an exception. It reads
every row back and compares an md5 of the stored `template_text` against the file
on disk, and asserts the expected `is_active` state.

Usage::

    python scripts/apply_prompt_rewrites.py --dry-run   # show the plan
    python scripts/apply_prompt_rewrites.py             # write, then verify
    python scripts/apply_prompt_rewrites.py --verify    # verify only, no writes
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL = os.path.join(ROOT, 'data', 'eval')

LANG_ID = {'zh': 1, 'ja': 3}

# (task_name, lang, model, is_active, source_file, description)
#
# `is_active=False` rows are STAGED: v1 stays live and nothing changes at
# runtime. See the migration header for why the cloze rows are staged rather
# than promoted (smoke-tested as "different, not demonstrably better").
ROWS = [
    ('translation_uniqueness_judge', 'zh', 'qwen/qwen3.7-plus', True,
     'translation_uniqueness_judge_zh.txt',
     'v2: natively authored in Chinese (qwen3.8-max). Replaces an all-English row. '
     'Inverted 1-5 scale preserved and verified live by scripts/smoke_judge_prompt.py.'),
    ('translation_uniqueness_judge', 'ja', 'google/gemini-3.5-flash-lite', True,
     'translation_uniqueness_judge_ja.txt',
     'v2: natively authored in Japanese (qwen3.8-max). Replaces an all-English row. '
     'Inverted 1-5 scale preserved and verified live by scripts/smoke_judge_prompt.py.'),
    ('question_inference', 'zh', 'qwen/qwen3.7-plus', True,
     'question_inference_zh.txt',
     'v2: natively authored in Chinese (qwen3.8-max). Removes the English name '
     '"Martinez" from the few-shot passage and replaces the transplanted English '
     'scenario with a Chinese one.'),
    ('question_main_idea', 'ja', 'qwen/qwen3.7-plus', True,
     'question_main_idea_ja.txt',
     'v2: natively authored in Japanese (qwen3.8-max). Removes the English "vs" '
     'metalanguage and the translated English-context few-shot example.'),
    ('question_author_purpose', 'ja', 'qwen/qwen3.7-plus', True,
     'question_author_purpose_ja.txt',
     'v2: natively authored in Japanese (qwen3.8-max). Removes the English gloss '
     '"(Author Purpose/Tone)" and the "vs" metalanguage; uses 筆者 rather than 著者.'),
    ('cloze_distractor_judge', 'zh', 'deepseek/deepseek-chat', False,
     'cloze_distractor_judge_zh.txt',
     'v2 (INACTIVE): natively authored in Chinese (qwen3.8-max). Staged pending '
     'TASK-719 - the smoke test shows it changes verdict behaviour, not just language.'),
    ('cloze_distractor_judge', 'ja', 'qwen/qwen-2.5-72b-instruct', False,
     'cloze_distractor_judge_ja.txt',
     'v2 (INACTIVE): natively authored in Japanese (qwen3.8-max). Staged pending '
     'TASK-719 - see the zh note; ja shows no measurable change either way.'),
]

NEW_VERSION = 2


def read_body(filename: str) -> str:
    with open(os.path.join(EVAL, filename), encoding='utf-8') as handle:
        return handle.read()


def md5(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def apply(db, dry_run: bool) -> None:
    for task, lang, model, active, filename, description in ROWS:
        body = read_body(filename)
        lang_id = LANG_ID[lang]
        state = 'ACTIVE' if active else 'INACTIVE (staged)'
        print(f'  {task} [{lang}] -> v{NEW_VERSION} {state}  '
              f'{len(body)} chars  md5 {md5(body)}')
        if dry_run:
            continue

        # Deactivate the incumbent ONLY when the new row is going live. A staged
        # row must leave v1 serving traffic untouched.
        if active:
            (db.table('prompt_templates')
               .update({'is_active': False})
               .eq('task_name', task)
               .eq('language_id', lang_id)
               .neq('version', NEW_VERSION)
               .execute())

        (db.table('prompt_templates')
           .upsert({
               'task_name': task,
               'language_id': lang_id,
               'version': NEW_VERSION,
               'is_active': active,
               'model': model,
               'provider': 'openrouter',
               'template_text': body,
               'description': description,
           }, on_conflict='task_name,language_id,version')
           .execute())


def verify(db) -> int:
    """Read every touched row back. Returns the number of problems found."""
    problems = 0
    print(f'\n{"task_name":<32} {"lg":<3} {"v":<3} {"active":<7} {"md5 match":<10} rows')
    print('-' * 78)

    for task, lang, _model, active, filename, _description in ROWS:
        expected = md5(read_body(filename))
        lang_id = LANG_ID[lang]

        rows = (db.table('prompt_templates')
                  .select('version, is_active, template_text')
                  .eq('task_name', task)
                  .eq('language_id', lang_id)
                  .execute().data)

        target = next((r for r in rows if r['version'] == NEW_VERSION), None)
        if target is None:
            print(f'{task:<32} {lang:<3} -   MISSING v{NEW_VERSION}')
            problems += 1
            continue

        matches = md5(target['template_text']) == expected
        active_ok = bool(target['is_active']) == active

        # The invariant that actually matters: exactly one active row per
        # (task, language). Zero means get_template_config raises and the judge
        # silently fails open — the outage mode this script exists to catch.
        active_count = sum(1 for r in rows if r['is_active'])

        flag = ''
        if not matches:
            flag += ' MD5-MISMATCH'
            problems += 1
        if not active_ok:
            flag += f' EXPECTED-ACTIVE={active}'
            problems += 1
        if active_count != 1:
            flag += f' ACTIVE-ROWS={active_count}'
            problems += 1

        print(f'{task:<32} {lang:<3} {target["version"]:<3} '
              f'{str(bool(target["is_active"])):<7} {str(matches):<10} '
              f'{len(rows)} version(s){flag}')

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true', help='show the plan, write nothing')
    parser.add_argument('--verify', action='store_true', help='verify only, write nothing')
    args = parser.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    if not args.verify:
        print('plan:' if args.dry_run else 'applying:')
        apply(db, args.dry_run)
        if args.dry_run:
            return 0

    problems = verify(db)
    print(f'\n{"OK — all rows verified" if not problems else f"{problems} PROBLEM(S)"}')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
