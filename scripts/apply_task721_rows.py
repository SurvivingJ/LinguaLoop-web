"""Land the 18 TASK-721 `question_*` rows as new INACTIVE versions, then prove it.

Same shape and the same reasoning as `apply_prompt_rewrites.py`: there is no
psql and no psycopg2 here, so `migrations/task721_question_distractor_spec.sql`
is the repo's record of intent and this script is what actually writes. Both are
generated from `data/eval/task721/after/`, so they cannot drift.

STAGED, NOT PROMOTED. Every row lands `is_active = false` and the incumbent is
left serving traffic. TASK-717 activated a prompt version before it was measured
and had to be reverted; the v5 rows are still sitting inactive as the reminder.
Activation is a separate, deliberate step (`--activate`) and is only justified by
the before/after comparison.

VERSION NUMBERS ARE NOT UNIFORM and are never assumed: the target is
`max(version) + 1` per (task_name, language_id), read from the table at write
time. Six of the eighteen incumbents are at v2, the rest at v1. Assuming v1 is
how two live `test_answer_entailment` rows were destroyed earlier in this
workstream.

The upsert is ON CONFLICT (task_name, language_id, version) DO UPDATE, so a
re-run overwrites the same row rather than colliding.
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

from task721_blocks import FAMILY  # noqa: E402

AFTER = os.path.join(ROOT, 'data', 'eval', 'task721', 'after')
LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}

DESCRIPTION = (
    'TASK-721 v{v} (STAGED, inactive): adds a distractor-construction block '
    'inverted from the live test_distractor_plausibility rubric ({family} '
    'family), plus the json-token repair that unbroke json_object calls on '
    'Alibaba. Body = the incumbent verbatim + one spliced block.'
)


def md5(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def read_after(task: str, lang: str) -> str:
    path = os.path.join(AFTER, f'{task}_{lang}.txt')
    if not os.path.exists(path):
        raise SystemExit(f'[error] missing {path} — run stage_task721_templates.py')
    # newline='' — no universal-newline translation. Nine of the eighteen rows
    # are CRLF in the table; reading them back as LF would make the stored body
    # differ from "incumbent + one block" by every line ending, and quietly
    # convert nine rows' line endings as a side effect of this task.
    with open(path, encoding='utf-8', newline='') as fh:
        return fh.read()


def plan(db, applied: bool = False) -> list[dict]:
    """One entry per row: incumbent version, target version, body, model.

    `applied=True` targets `max(version)` rather than `max(version) + 1` — after
    a successful apply the staged row IS the max, so recomputing the write
    target would look one version past what was written and report all 18 rows
    missing.
    """
    out = []
    for tc in FAMILY:
        task = f'question_{tc}'
        for lang, lid in LANG_ID.items():
            rows = (db.table('prompt_templates')
                      .select('version, is_active, model, provider')
                      .eq('task_name', task)
                      .eq('language_id', lid)
                      .execute().data)
            if not rows:
                raise SystemExit(f'[error] no rows at all for {task}[{lang}]')
            live = [r for r in rows if r['is_active']]
            if len(live) != 1:
                raise SystemExit(
                    f'[error] {task}[{lang}] has {len(live)} active rows, '
                    f'expected exactly 1 — refusing to guess')
            out.append({
                'task': task, 'lang': lang, 'lang_id': lid, 'type_code': tc,
                'incumbent': live[0]['version'],
                # max over ALL versions, active or not: inactive history still
                # occupies version numbers.
                'version': max(r['version'] for r in rows) + (0 if applied else 1),
                # Never changed. Mixing a prompt change with a model change
                # makes the before/after uninterpretable (TASK-717).
                'model': live[0]['model'],
                'provider': live[0]['provider'],
                'body': read_after(task, lang),
            })
    return out


def apply(db, rows: list[dict], dry_run: bool) -> None:
    for r in rows:
        print(f'  {r["task"]:34} [{r["lang"]}] v{r["incumbent"]} -> v{r["version"]} '
              f'INACTIVE  {len(r["body"]):5} chars  md5 {md5(r["body"])}  '
              f'{r["model"]}')
        if dry_run:
            continue
        (db.table('prompt_templates')
           .upsert({
               'task_name': r['task'],
               'language_id': r['lang_id'],
               'version': r['version'],
               'is_active': False,
               'model': r['model'],
               'provider': r['provider'],
               'template_text': r['body'],
               'description': DESCRIPTION.format(v=r['version'],
                                                 family=FAMILY[r['type_code']]),
           }, on_conflict='task_name,language_id,version')
           .execute())


def activate(db, rows: list[dict]) -> None:
    """Promote the staged versions. Deactivate-then-activate, per (task, lang)."""
    for r in rows:
        (db.table('prompt_templates')
           .update({'is_active': False})
           .eq('task_name', r['task'])
           .eq('language_id', r['lang_id'])
           .neq('version', r['version'])
           .execute())
        (db.table('prompt_templates')
           .update({'is_active': True})
           .eq('task_name', r['task'])
           .eq('language_id', r['lang_id'])
           .eq('version', r['version'])
           .execute())
        print(f'  activated {r["task"]:34} [{r["lang"]}] v{r["version"]}')


def verify(db, rows: list[dict], expect_active: bool) -> int:
    problems = 0
    print(f'\n{"task_name":<32} {"lg":<3} {"v":<3} {"active":<7} {"md5":<7} rows')
    print('-' * 76)
    for r in rows:
        got = (db.table('prompt_templates')
                 .select('version, is_active, template_text')
                 .eq('task_name', r['task'])
                 .eq('language_id', r['lang_id'])
                 .execute().data)
        target = next((g for g in got if g['version'] == r['version']), None)
        if target is None:
            print(f'{r["task"]:<32} {r["lang"]:<3} -   MISSING v{r["version"]}')
            problems += 1
            continue

        matches = md5(target['template_text']) == md5(r['body'])
        active_ok = bool(target['is_active']) == expect_active
        # The invariant that matters: exactly one active row per (task, lang).
        # Zero means get_template_config raises and generation dies for that
        # question type in that language.
        active_count = sum(1 for g in got if g['is_active'])

        flag = ''
        if not matches:
            flag += ' MD5-MISMATCH'
            problems += 1
        if not active_ok:
            flag += f' EXPECTED-ACTIVE={expect_active}'
            problems += 1
        if active_count != 1:
            flag += f' ACTIVE-ROWS={active_count}'
            problems += 1

        print(f'{r["task"]:<32} {r["lang"]:<3} {target["version"]:<3} '
              f'{str(bool(target["is_active"])):<7} {str(matches):<7} '
              f'{len(got)} version(s){flag}')
    return problems


def emit_sql(rows: list[dict], path: str) -> None:
    def lit(s: str) -> str:
        return "$tpl$" + s + "$tpl$"

    parts = [
        '-- TASK-721: give the 18 question_* generator prompts a distractor',
        '-- specification. STAGED INACTIVE -- see scripts/apply_task721_rows.py.',
        '--',
        '-- Each new body is the incumbent verbatim plus one spliced block, so the',
        '-- diff is attributable to exactly one change. Version numbers are per-row',
        '-- max(version)+1 and are NOT uniform.',
        '--',
        '-- NOTE: four bodies also carry a single-token `JSON` repair. Without it',
        '-- those rows 400 on Alibaba under response_format=json_object and cannot',
        '-- generate at all. See the header of scripts/stage_task721_templates.py.',
        '',
        'BEGIN;',
        '',
    ]
    for r in rows:
        desc = DESCRIPTION.format(v=r['version'], family=FAMILY[r['type_code']])
        parts += [
            f'-- {r["task"]} [{r["lang"]}] v{r["incumbent"]} -> v{r["version"]}  '
            f'md5 {md5(r["body"])}',
            'INSERT INTO public.prompt_templates',
            '  (task_name, language_id, version, is_active, model, provider,',
            '   template_text, description)',
            f'VALUES (\'{r["task"]}\', {r["lang_id"]}, {r["version"]}, false,',
            f'        \'{r["model"]}\', \'{r["provider"]}\',',
            f'        {lit(r["body"])},',
            f'        {lit(desc)})',
            'ON CONFLICT (task_name, language_id, version) DO UPDATE',
            '   SET is_active     = EXCLUDED.is_active,',
            '       model         = EXCLUDED.model,',
            '       provider      = EXCLUDED.provider,',
            '       template_text = EXCLUDED.template_text,',
            '       description   = EXCLUDED.description,',
            '       updated_at    = now();',
            '',
        ]
    parts += ['COMMIT;', '']
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(parts))
    print(f'wrote {path}')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--activate', action='store_true',
                    help='promote the staged versions (only after measuring)')
    ap.add_argument('--emit-sql',
                    default=os.path.join(ROOT, 'migrations',
                                         'task721_question_distractor_spec.sql'))
    args = ap.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()
    rows = plan(db, applied=args.verify or args.activate)

    if args.activate:
        activate(db, rows)
        problems = verify(db, rows, expect_active=True)
    elif args.verify:
        problems = verify(db, rows, expect_active=False)
    else:
        print('plan:' if args.dry_run else 'applying:')
        apply(db, rows, args.dry_run)
        if args.dry_run:
            return 0
        emit_sql(rows, args.emit_sql)
        problems = verify(db, rows, expect_active=False)

    print(f'\n{"OK" if not problems else f"{problems} PROBLEM(S)"}')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
