"""Drop the "LinguaLoop" brand mention from every active prompt_templates row.

User directive (2026-08-23): "For all prompts, drop the mention of 'Lingualoop'
- it is unecessary and leaks language." The mention is dead weight in every
row that carries it: it tells the model nothing about the task, and in the
zh/ja rows it is a bare English brand name sitting inside otherwise fully
target-language instructions -- the same class of defect flagged elsewhere in
this codebase as language leakage (see wiki/log.md 2026-08-11..21 sweeps).

Six active rows matched (checked via `template_text ~* 'lingualoop'` against
every active row in `prompt_templates`; zero rows matched 'linguadojo' or any
other brand spelling, so this is the complete live set):

    prose_generation               en (351) zh (352) ja (353)
    semantic_class_classification  en (195) zh (267) ja (268)

Each edit removes only the brand clause and leaves everything else --
including every {placeholder} and every JSON example -- byte-identical. Rows
are versioned, never overwritten: the incumbent is deactivated and a new
max(version)+1 row is inserted, so rollback is one is_active flip.

Two renderer engines are in play and only one of them treats braces as
syntax:

    prose_generation               str.format() at
                                    services/test_generation/agents/prose_writer.py:81
                                    -- supplied kwargs: topic_concept, keywords,
                                    complexity_tier, min_words, max_words,
                                    language, language_code, difficulty.
    semantic_class_classification  a single literal .replace('{batch}', ...) at
                                    scripts/backfill_semantic_class.py:155 --
                                    every other brace (including the JSON
                                    example in the prompt body) is inert.

Neither edit touches a brace, a placeholder, or the JSON example region, so
this script's checks are narrower than the CEFR/L1 rewrite scripts it follows
the pattern of (apply_task733_cefr_tier_rewrites.py,
apply_task735_ja_l1_fixes.py): confirm the brand clause is removed, confirm
nothing else changed, confirm no 'lingualoop' spelling survives anywhere in
the new text.

Usage::

    python scripts/apply_prompt_brand_mention_removal.py --dry-run
    python scripts/apply_prompt_brand_mention_removal.py
    python scripts/apply_prompt_brand_mention_removal.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}
LINGUALOOP_RE = re.compile(r'lingualoop', re.IGNORECASE)

# (task_name, lang, old_clause, new_clause, description)
#
# old_clause must appear in the live row EXACTLY ONCE and is replaced verbatim
# by new_clause -- nothing else in the row is touched.
ROWS = [
    ('prose_generation', 'zh',
     '你是由 "LinguaLoop" 开发的专业中文教学内容生成引擎。',
     '你是专业中文教学内容生成引擎。',
     'v3: drop the "LinguaLoop" brand mention (unnecessary, and a bare English '
     'brand name inside an otherwise fully Chinese instruction). No other '
     'change; T1-T6 structure from v2 (TASK-733) untouched.'),

    ('prose_generation', 'en',
     'You are the content generation engine for "LinguaLoop," an app for '
     'English language learners.',
     'You are the content generation engine for English language learners.',
     'v3: drop the "LinguaLoop" brand mention (unnecessary). No other change; '
     'T1-T6 structure from v2 (TASK-733) untouched.'),

    ('prose_generation', 'ja',
     'あなたは「LinguaLoop」という言語学習アプリのコンテンツ生成エンジンです。',
     'あなたは言語学習アプリのコンテンツ生成エンジンです。',
     'v3: drop the "LinguaLoop" brand mention (unnecessary, and a bare English '
     'brand name inside an otherwise fully Japanese instruction). No other '
     'change; T1-T6 structure from v2 (TASK-733) untouched.'),

    ('semantic_class_classification', 'zh',
     '你是 LinguaLoop 词汇系统的语言分类器。',
     '你是词汇系统的语言分类器。',
     'v4: drop the "LinguaLoop" brand mention (unnecessary, and a bare English '
     'brand name inside an otherwise fully Chinese instruction). No contract '
     'token touched.'),

    ('semantic_class_classification', 'en',
     'You are a linguistic classifier for the LinguaLoop vocabulary system.',
     'You are a linguistic classifier for the vocabulary system.',
     'v3: drop the "LinguaLoop" brand mention (unnecessary). No contract token '
     'touched.'),

    ('semantic_class_classification', 'ja',
     'あなたは LinguaLoop 語彙システムの言語分類器です。',
     'あなたは語彙システムの言語分類器です。',
     'v4: drop the "LinguaLoop" brand mention (unnecessary, and a bare English '
     'brand name inside an otherwise fully Japanese instruction). No contract '
     'token touched.'),
]

# Model/provider carried forward unchanged from the incumbent row (fetched
# live, not hardcoded) -- this script only edits template_text.


def md5(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def fetch(db, task: str, lang_id: int) -> list[dict]:
    return (db.table('prompt_templates')
              .select('id, version, is_active, template_text, model, provider')
              .eq('task_name', task)
              .eq('language_id', lang_id)
              .order('version')
              .execute().data)


def check_row(old_clause: str, new_clause: str, incumbent_text: str,
              new_text: str) -> list[str]:
    problems = []

    occurrences = incumbent_text.count(old_clause)
    if occurrences == 0:
        problems.append(f'old_clause not found in the live row (drifted?): '
                        f'{old_clause[:60]!r}')
    elif occurrences > 1:
        problems.append(f'old_clause appears {occurrences} times, expected 1 -- '
                        f'a blind replace would be ambiguous: {old_clause[:60]!r}')

    if new_clause not in new_text:
        problems.append('new_clause missing from the rewritten text.')

    if LINGUALOOP_RE.search(new_text):
        problems.append('"lingualoop" (any case) still present after rewrite.')

    # Everything outside the one clause must be untouched.
    expected = incumbent_text.replace(old_clause, new_clause, 1)
    if expected != new_text:
        problems.append('rewrite changed more than the target clause -- '
                        'diff outside old_clause/new_clause.')

    return problems


def plan(db, for_write: bool = True):
    jobs, problems = [], []
    for (task, lang, old_clause, new_clause, desc) in ROWS:
        lang_id = LANG_ID[lang]
        rows = fetch(db, task, lang_id)
        if not rows:
            problems.append(f'{task} [{lang}]: no rows at all.')
            continue
        active = [r for r in rows if r['is_active']]
        if len(active) != 1:
            problems.append(f'{task} [{lang}]: {len(active)} active rows, expected 1.')
            continue
        incumbent = active[0]
        incumbent_text = incumbent['template_text']

        target_version = incumbent['version'] if not for_write else \
            (max(r['version'] for r in rows) + 1)

        if for_write:
            new_text = incumbent_text.replace(old_clause, new_clause, 1)
            problems.extend(
                f'{task} [{lang}]: {p}' for p in
                check_row(old_clause, new_clause, incumbent_text, new_text))
        else:
            # --verify reads back what was written; the clause is legitimately
            # gone from the now-live row, so just confirm no brand mention
            # survives and the new_clause is present.
            new_text = incumbent_text
            if LINGUALOOP_RE.search(new_text):
                problems.append(f'{task} [{lang}]: "lingualoop" still present '
                                f'in the live row.')
            if new_clause not in new_text:
                problems.append(f'{task} [{lang}]: new_clause not found in the '
                                f'live row.')

        jobs.append({
            'task': task, 'lang': lang, 'lang_id': lang_id,
            'incumbent_id': incumbent['id'],
            'incumbent_version': incumbent['version'],
            'version': target_version,
            'model': incumbent['model'], 'provider': incumbent['provider'],
            'body': new_text, 'description': desc,
        })
    return jobs, problems


def apply(db, jobs, dry_run: bool) -> None:
    for job in jobs:
        print(f'  {job["task"]:<28} {job["lang"]} '
              f'v{job["incumbent_version"]} -> v{job["version"]}  '
              f'{len(job["body"]):>5} chars  md5 {md5(job["body"])}')
        if dry_run:
            continue

        (db.table('prompt_templates')
           .update({'is_active': False})
           .eq('task_name', job['task'])
           .eq('language_id', job['lang_id'])
           .execute())

        (db.table('prompt_templates')
           .upsert({
               'task_name': job['task'],
               'language_id': job['lang_id'],
               'version': job['version'],
               'is_active': True,
               'model': job['model'],
               'provider': job['provider'],
               'template_text': job['body'],
               'description': job['description'],
           }, on_conflict='task_name,language_id,version')
           .execute())


def verify(db, jobs) -> int:
    problems = 0
    print(f'\n{"task_name":<28} {"lg":<3} {"v":<4} {"active":<7} {"md5":<6} rows')
    print('-' * 70)
    for job in jobs:
        rows = fetch(db, job['task'], job['lang_id'])
        target = next((r for r in rows if r['version'] == job['version']), None)
        if target is None:
            print(f'{job["task"]:<28} {job["lang"]:<3} MISSING v{job["version"]}')
            problems += 1
            continue

        stored = target['template_text']
        matches = md5(stored) == md5(job['body'])
        active_count = sum(1 for r in rows if r['is_active'])
        has_brand = bool(LINGUALOOP_RE.search(stored))

        flags = []
        if not matches:
            flags.append('MD5-MISMATCH')
        if not target['is_active']:
            flags.append('NOT-ACTIVE')
        if active_count != 1:
            flags.append(f'{active_count}-ACTIVE')
        if has_brand:
            flags.append('BRAND-STILL-PRESENT')
        if not target['model'] or not target['provider']:
            flags.append('NULL-MODEL')
        problems += len(flags)

        print(f'{job["task"]:<28} {job["lang"]:<3} v{job["version"]:<3} '
              f'{str(target["is_active"]):<7} '
              f'{"ok" if matches else "BAD":<6} {len(rows)}  {" ".join(flags)}')
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true',
                        help='show the plan, write nothing')
    parser.add_argument('--verify', action='store_true',
                        help='verify only, write nothing')
    args = parser.parse_args()

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    jobs, problems = plan(db, for_write=not args.verify)
    if problems:
        print('PRE-FLIGHT FAILED -- nothing written:\n')
        for p in problems:
            print(f'  ! {p}')
        return 1

    print(f'\n-- plan ({len(jobs)} rows) ' + '-' * 40)
    if not args.verify:
        apply(db, jobs, dry_run=args.dry_run)
    if args.dry_run:
        print('\ndry run -- nothing written.')
        return 0

    failures = verify(db, jobs)
    if failures:
        print(f'\nVERIFY FAILED: {failures} problem(s).')
        return 1
    print('\nverified: every row stored byte-for-byte, exactly one active per task, '
          'no brand mention survives.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
