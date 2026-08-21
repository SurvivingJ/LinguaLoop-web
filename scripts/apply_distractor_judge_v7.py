"""Stage the two-axis (v7) `test_distractor_plausibility` rows, then prove it landed.

TASK-719 splits the judge's single 1-5 rating onto two axes (topical **fit** and
**confusability** with the correct answer); TASK-720 redefines band 3 on both as
"the judge is not confident" and records which axis fired. The Python side ships
with the code. This script writes the prompt rows those bands live in.

**The rows are written INACTIVE.** Nothing changes at runtime until someone flips
`is_active`, and that decision is deliberately not this script's to make:

* the adjudicated distractor gold set (TASK-726) does not exist yet, so no reject
  signal in this workstream is validated in absolute terms — TASK-718 measured two
  judge models whose reject sets were **disjoint**;
* the two prior prompt interventions in this workstream (TASK-717's v5, TASK-721's
  generator spec) were both measured and both stayed staged. Measure first is the
  house rule here, not caution for its own sake.

Deploying the code ahead of the rows is safe, and that is a property worth
stating rather than assuming. A v4/v6 row returns one rating per distractor; the
schema reads it as `fit`, whose bands are identical to v4's, and the absent
`confusability` contributes nothing. Verdicts are unchanged until v7 is active.
`tests/test_distractor_two_axis.py::test_fit_reproduces_the_v4_scale_exactly`
pins that. This is the opposite of the entailment cutover (TASK-723), where the
two scales inverted at 1 and the code needed a version gate.

Version 7 in **all three** languages, even though en and ja have no v6. Uniform
numbering is worth a gap: `measure_judge_flag_rate.py` takes one integer per arm,
and the live set is already zh v6 / en v4 / ja v4, which no integer can express.

Usage::

    python scripts/apply_distractor_judge_v7.py --dry-run   # show the plan
    python scripts/apply_distractor_judge_v7.py             # write, then verify
    python scripts/apply_distractor_judge_v7.py --verify     # verify only
    python scripts/apply_distractor_judge_v7.py --emit-sql migrations/x.sql
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

TASK = 'test_distractor_plausibility'
NEW_VERSION = 7
LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}

# (lang, model, source_file, description)
#
# The model is the one each language's ACTIVE row runs today, carried forward
# unchanged. v7 is a prompt change and must be measurable as one: varying the
# model at the same time is what made the TASK-718 numbers hard to compare
# against the analysis page's.
ROWS = [
    ('zh', 'google/gemini-3.5-flash-lite', 'distractor_judge_v7_zh.txt',
     'v7 (INACTIVE, TASK-719/720): two axes — topical fit and confusability with '
     'the correct answer — rated separately, three-element arrays [fit, '
     'confusability, reason]. Band 3 on either axis now means "not confident" and '
     'routes to human review. Natively authored in Chinese (qwen3.8-max). Staged '
     'pending the TASK-726 gold set.'),
    ('en', 'google/gemini-3.5-flash-lite', 'distractor_judge_v7_en.txt',
     'v7 (INACTIVE, TASK-719/720): two axes — topical fit and confusability with '
     'the correct answer — rated separately, three-element arrays [fit, '
     'confusability, reason]. Band 3 on either axis now means "not confident" and '
     'routes to human review. Staged pending the TASK-726 gold set.'),
    ('ja', 'google/gemini-3.5-flash-lite', 'distractor_judge_v7_ja.txt',
     'v7 (INACTIVE, TASK-719/720): two axes — topical fit and confusability with '
     'the correct answer — rated separately, three-element arrays [fit, '
     'confusability, reason]. Band 3 on either axis now means "not confident" and '
     'routes to human review. Natively authored in Japanese (qwen3.8-max). Staged '
     'pending the TASK-726 gold set.'),
]


def read_body(filename: str) -> str:
    with open(os.path.join(EVAL, filename), encoding='utf-8') as handle:
        return handle.read()


def md5(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def _render_check(body: str) -> None:
    """Render the row exactly as the judge will. A KeyError here is an outage.

    `judge_distractor_plausibility` calls `.format(passage, question, answer,
    numbered, type_code, keywords)` with six positional args. A row missing a
    slot, or carrying a stray single brace, raises inside the judge's try block
    and every distractor in the batch is safe-accepted — silently.
    """
    body.format('(passage)', '(question)', '(answer)', '1. A\n2. B\n3. C',
                'vocabulary_context', '(subject)')
    for i in range(6):
        if body.count('{%d}' % i) != 1:
            raise ValueError(f'slot {{{i}}} appears {body.count("{%d}" % i)}x, expected 1')


def apply(db, dry_run: bool) -> None:
    for lang, model, filename, description in ROWS:
        body = read_body(filename)
        _render_check(body)
        print(f'  {TASK} [{lang}] -> v{NEW_VERSION} INACTIVE (staged)  '
              f'{len(body)} chars  md5 {md5(body)}  {model}')
        if dry_run:
            continue

        # No deactivation pass: the incumbent row must keep serving. Writing a
        # staged row that silently unseats the live one is the failure that left
        # zh and ja with no active entailment row at all (TASK-723).
        (db.table('prompt_templates')
           .upsert({
               'task_name': TASK,
               'language_id': LANG_ID[lang],
               'version': NEW_VERSION,
               'is_active': False,
               'model': model,
               'provider': 'openrouter',
               'template_text': body,
               'description': description,
           }, on_conflict='task_name,language_id,version')
           .execute())


def verify(db) -> int:
    """Read every touched row back. Returns the number of problems found."""
    problems = 0
    print(f'\n{"lang":<6} {"v":<3} {"active":<7} {"md5 match":<10} '
          f'{"live row":<10} rows')
    print('-' * 62)

    for lang, _model, filename, _description in ROWS:
        expected = md5(read_body(filename))
        rows = (db.table('prompt_templates')
                  .select('version, is_active, template_text')
                  .eq('task_name', TASK)
                  .eq('language_id', LANG_ID[lang])
                  .execute().data)

        target = next((r for r in rows if r['version'] == NEW_VERSION), None)
        if target is None:
            print(f'{lang:<6} -   MISSING v{NEW_VERSION}')
            problems += 1
            continue

        matches = md5(target['template_text']) == expected
        active = [r['version'] for r in rows if r['is_active']]

        flag = ''
        if not matches:
            flag += ' MD5-MISMATCH'
            problems += 1
        if target['is_active']:
            flag += ' V7-IS-ACTIVE(should be staged)'
            problems += 1
        # Exactly one active row per language, and it must not be v7. Zero means
        # get_template_config raises and the judge falls open on every call.
        if len(active) != 1:
            flag += f' ACTIVE-ROWS={len(active)}'
            problems += 1

        print(f'{lang:<6} {target["version"]:<3} '
              f'{str(bool(target["is_active"])):<7} {str(matches):<10} '
              f'{("v" + str(active[0])) if len(active) == 1 else "?":<10} '
              f'{len(rows)} version(s){flag}')

    return problems


_SQL_HEADER = """\
-- test_distractor_plausibility v7 — the two-axis judge rubric (TASK-719/720)
--
-- Generated by scripts/apply_distractor_judge_v7.py --emit-sql. There is no psql
-- in this environment, so that script is what actually writes; this file is the
-- repo's record of intent and both come from the same source of truth
-- (data/eval/distractor_judge_v7_{zh,en,ja}.txt), so they cannot drift.
--
-- WHAT CHANGES
--   The judge returned ONE 1-5 rating per distractor that was answering two
--   unrelated questions at once — is this option about the right subject, and
--   would a learner confuse it with the correct answer. Those come apart in both
--   directions, so a single integer could not say which failure it had seen.
--   v7 asks for both ratings, as [fit, confusability, reason], and the verdict
--   arithmetic moves into schemas.axes_to_verdict where the cut points are named
--   constants instead of prose in three languages.
--
--   Band 3 on BOTH axes now means "the judge is not confident" and routes to
--   generation_review_queue, replacing the narrow "essentially a paraphrase of
--   the correct answer" definition that no model ever applied as written.
--
-- THESE ROWS ARE INACTIVE ON PURPOSE.
--   The adjudicated gold set (TASK-726) does not exist yet, so no reject signal
--   here is validated in absolute terms. Both prior prompt interventions in this
--   workstream (TASK-717 v5, TASK-721) were measured and both stayed staged.
--   To activate, after measuring:
--
--     UPDATE prompt_templates SET is_active = (version = 7), updated_at = now()
--      WHERE task_name = 'test_distractor_plausibility'
--        AND language_id IN (1, 2, 3);
--
--   The code needs no coordinated deploy: a v4/v6 row's single rating is read as
--   `fit`, whose bands are identical to v4's, so verdicts are unchanged until the
--   flip. Unlike entailment v3 (TASK-723) the two scales do not invert.
--
-- VERSION 7 IN ALL THREE LANGUAGES, and en/ja therefore skip 6. Per-task version
-- numbering is not aligned across languages here — live is zh v6, en v4, ja v4 —
-- and measure_judge_flag_rate.py takes one integer per arm, so a uniform number
-- is what lets a single arm span the three languages.
"""


def emit_sql(path: str) -> None:
    parts = [_SQL_HEADER]
    for lang, model, filename, description in ROWS:
        body = read_body(filename)
        _render_check(body)
        parts.append(
            f"\n-- {lang} (language_id={LANG_ID[lang]}) — {len(body)} chars, "
            f"md5 {md5(body)}\n"
            "INSERT INTO prompt_templates\n"
            "    (task_name, language_id, version, is_active, model, provider,\n"
            "     template_text, description)\n"
            "VALUES (\n"
            f"    '{TASK}', {LANG_ID[lang]}, {NEW_VERSION}, false,\n"
            f"    '{model}', 'openrouter',\n"
            f"    {_lit(body)},\n"
            f"    {_lit(description)}\n"
            ")\n"
            "ON CONFLICT (task_name, language_id, version) DO UPDATE SET\n"
            "    is_active     = EXCLUDED.is_active,\n"
            "    model         = EXCLUDED.model,\n"
            "    provider      = EXCLUDED.provider,\n"
            "    template_text = EXCLUDED.template_text,\n"
            "    description   = EXCLUDED.description,\n"
            "    updated_at    = now();\n"
        )
    parts.append(
        "\n-- Verification: three staged rows, and the live row per language\n"
        "-- unchanged (zh v6, en v4, ja v4).\n"
        "SELECT language_id, version, is_active, length(template_text) AS len,\n"
        "       md5(template_text) AS md5\n"
        "  FROM prompt_templates\n"
        f" WHERE task_name = '{TASK}'\n"
        " ORDER BY language_id, version;\n"
    )
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(''.join(parts))
    print(f'wrote {path}')


def _lit(text: str) -> str:
    """Dollar-quote a body. The prompts contain quotes, braces and newlines."""
    tag = '$prompt$'
    if tag in text:
        raise ValueError('body contains the dollar-quote tag')
    return f'{tag}{text}{tag}'


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true',
                        help='show the plan, write nothing')
    parser.add_argument('--verify', action='store_true',
                        help='verify only, write nothing')
    parser.add_argument('--emit-sql', metavar='PATH',
                        help='write the migration file and exit')
    args = parser.parse_args()

    if args.emit_sql:
        emit_sql(args.emit_sql)
        return 0

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
