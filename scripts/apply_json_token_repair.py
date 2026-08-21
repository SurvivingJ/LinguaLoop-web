"""Hotfix: restore the literal `JSON` token to four live `question_*` rows.

THE OUTAGE
----------
These four active rows contain no case-insensitive `json` token:

    question_vocabulary_context [zh] v2
    question_vocabulary_context [ja] v2
    question_main_idea          [ja] v2
    question_author_purpose     [ja] v2

All four are TASK-722 / TASK-724 native rewrites, and all four lost the token to
the English-metalanguage sweep. All four run on `qwen/qwen3.7-plus`, which
OpenRouter routes to Alibaba, and Alibaba refuses `response_format=json_object`
unless the prompt contains the word:

    400 invalid_parameter_error: 'messages' must contain the word 'json' in
    some form, to use 'response_format' of type 'json_object'

`question_generator.generate_question` always passes
`response_format='json_object'`, so every generation attempt for these four
(question type x language) pairs fails. Measured 2026-08-19: 4/4 cells failed in
a 18-cell pilot; after this repair, 179/180 succeeded.

WHY THIS IS NOT A REVERSION OF TASK-724
---------------------------------------
`JSON` here is machine contract, not English leakage -- the same category
`rewrite_prompt_native.allowed_latin` already whitelists alongside the JSON key
names and the `question_type` enum. The sweep was right about
"markdown"/"schema" and wrong about this one token. Nothing else in those rows
changes: the repair is a single word inserted into the existing output sentence,
listed literally below.

SEPARATE FROM TASK-721 ON PURPOSE. The TASK-721 rows carry this repair too, but
they land INACTIVE pending a measurement. A live outage should not wait on that.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, '.env'))

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

from stage_task721_templates import JSON_REPAIR  # noqa: E402

LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}
DESCRIPTION = (
    'v{v}: restores the literal JSON token lost to the TASK-724 metalanguage '
    'sweep. Without it Alibaba 400s every response_format=json_object call and '
    'this row cannot generate at all. Body = v{p} verbatim + one word.'
)


def md5(t: str) -> str:
    return hashlib.md5(t.encode('utf-8')).hexdigest()


def plan(db) -> list[dict]:
    out = []
    for (task, lang), (old, new) in JSON_REPAIR.items():
        lid = LANG_ID[lang]
        rows = (db.table('prompt_templates')
                  .select('version, is_active, model, provider, template_text')
                  .eq('task_name', task).eq('language_id', lid).execute().data)
        live = [r for r in rows if r['is_active']]
        if len(live) != 1:
            raise SystemExit(f'[error] {task}[{lang}] has {len(live)} active rows')
        body = live[0]['template_text']
        if new in body and old not in body:
            print(f'  {task} [{lang}] already repaired — skipping')
            continue
        if body.count(old) != 1:
            raise SystemExit(
                f'[error] {task}[{lang}] repair anchor occurs '
                f'{body.count(old)}x, expected 1')
        out.append({
            'task': task, 'lang': lang, 'lang_id': lid,
            'prev': live[0]['version'],
            'version': max(r['version'] for r in rows) + 1,
            'model': live[0]['model'], 'provider': live[0]['provider'],
            'body': body.replace(old, new),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()
    rows = plan(db)
    if not rows:
        print('nothing to do')
        return 0

    for r in rows:
        print(f'  {r["task"]:32} [{r["lang"]}] v{r["prev"]} -> v{r["version"]} '
              f'ACTIVE  {len(r["body"])} chars  md5 {md5(r["body"])}')
        if args.dry_run:
            continue
        (db.table('prompt_templates')
           .upsert({
               'task_name': r['task'], 'language_id': r['lang_id'],
               'version': r['version'], 'is_active': True,
               'model': r['model'], 'provider': r['provider'],
               'template_text': r['body'],
               'description': DESCRIPTION.format(v=r['version'], p=r['prev']),
           }, on_conflict='task_name,language_id,version').execute())
        (db.table('prompt_templates')
           .update({'is_active': False})
           .eq('task_name', r['task']).eq('language_id', r['lang_id'])
           .neq('version', r['version']).execute())
    if args.dry_run:
        return 0

    problems = 0
    print(f'\n{"task":<32} {"lg":<3} {"v":<3} {"active":<7} {"md5":<7} active_rows')
    for r in rows:
        got = (db.table('prompt_templates')
                 .select('version, is_active, template_text')
                 .eq('task_name', r['task']).eq('language_id', r['lang_id'])
                 .execute().data)
        t = next((g for g in got if g['version'] == r['version']), None)
        if t is None:
            print(f'{r["task"]:<32} {r["lang"]:<3} MISSING')
            problems += 1
            continue
        ok_md5 = md5(t['template_text']) == md5(r['body'])
        n_active = sum(1 for g in got if g['is_active'])
        has_json = 'json' in t['template_text'].lower()
        flag = ''
        if not ok_md5:
            flag += ' MD5-MISMATCH'; problems += 1
        if not t['is_active']:
            flag += ' NOT-ACTIVE'; problems += 1
        if n_active != 1:
            flag += f' ACTIVE-ROWS={n_active}'; problems += 1
        if not has_json:
            flag += ' STILL-NO-JSON-TOKEN'; problems += 1
        print(f'{r["task"]:<32} {r["lang"]:<3} {t["version"]:<3} '
              f'{str(bool(t["is_active"])):<7} {str(ok_md5):<7} {n_active}{flag}')

    print(f'\n{"OK" if not problems else f"{problems} PROBLEM(S)"}')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
