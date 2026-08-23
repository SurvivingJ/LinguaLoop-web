"""TASK-733: remove CEFR from the test-gen / exercise-gen prompt families and
converge the ``cloze_distractor_generation`` distractor-tag enum across languages.

Fourteen ``prompt_templates`` rows. Every one is versioned, never overwritten:
the incumbent is deactivated and a new ``max(version)+1`` row is inserted, so a
rollback is a single ``is_active`` flip rather than a restore.

Why this file exists rather than a .sql migration
-------------------------------------------------
There is no psql/psycopg2 in this environment, so a .sql file is a record of
intent that nothing executes. This script is what actually writes, and — as with
``apply_prompt_rewrites.py`` — it never reports success from the absence of an
exception. Three things are checked before anything is written and again after:

1. **Substitution fired.** Each row carries ``must_go`` / ``must_have`` token
   lists. A ``must_go`` string still present in the incumbent but absent from the
   draft proves the rewrite targeted the live text; a ``must_go`` string that was
   never in the incumbent means the row drifted since it was audited, and we
   abort rather than write a no-op version bump.
2. **Parser contract intact.** ``str.format`` placeholders are extracted from the
   draft and compared against the set the caller actually supplies. A draft that
   invents a placeholder would raise ``KeyError`` at generation time, which for
   ``exercise_sentence_generation`` [ja] is exactly the live bug this task fixes.
3. **Line endings preserved.** Line endings are per-row, NOT uniform: ids 69,
   180 and 190 are LF-only while the other eleven are CRLF. The draft files on
   disk are LF; each row's incumbent convention is detected and reapplied.

Usage::

    python scripts/apply_task733_cefr_tier_rewrites.py --dry-run   # show the plan
    python scripts/apply_task733_cefr_tier_rewrites.py             # write, verify
    python scripts/apply_task733_cefr_tier_rewrites.py --verify    # verify only
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, 'data', 'eval', 'task733')

LANG_ID = {'zh': 1, 'en': 2, 'ja': 3}

# A CEFR band token, CJK-safe. Do NOT use \b: CJK codepoints are \w in Python,
# so \bCEFR\b never matches "CEFR等级" or "CEFRレベル".
CEFR_RE = re.compile(r'(?<![A-Za-z0-9])(?:CEFR|[ABC][12])(?![A-Za-z0-9])')

# Placeholders each caller actually supplies. A draft may use a subset; using
# anything outside the set is a KeyError at generation time.
CALLER_ARGS = {
    # services/test_generation/agents/prose_writer.py:81
    'prose_generation': {'topic_concept', 'keywords', 'complexity_tier',
                         'min_words', 'max_words', 'language', 'language_code',
                         'difficulty'},
    # services/test_generation/agents/title_generator.py:62
    'title_generation': {'prose', 'topic_concept', 'difficulty',
                         'complexity_tier', 'language', 'language_code'},
    # services/test_generation/agents/question_generator.py
    'question_vocabulary_context': {'prose', 'difficulty', 'language',
                                    'language_code', 'complexity_tier',
                                    'previous_questions', 'question_type'},
    # services/exercise_generation/transcript_miner.py:226
    #   template.format(count=..., **source_data), source_data from
    #   _load_source_data() at :239
    'exercise_sentence_generation': {'count', 'pattern_code', 'description',
                                     'example_sentence', 'complexity_tier'},
    'vocab_sentence_generation': {'count', 'word', 'definition',
                                  'complexity_tier'},
    'collocation_sentence_generation': {'count', 'collocation_text',
                                        'pos_pattern'},
    # services/exercise_generation/generators/cloze.py:_generate_distractors
    'cloze_distractor_generation': {'original_sentence', 'sentence_with_blank',
                                    'correct_answer', 'complexity_tier'},
}

# The five-dimension closed taxonomy — wiki/features/exercise-generation-prompts.md:570.
CLOZE_TAGS = ('semantic', 'collocational', 'aspectual', 'register', 'valency')

# (draft_file, task_name, lang, model, provider, must_go, must_have, description)
#
# model/provider carry the incumbent's values forward, except title_generation,
# whose three rows are NULL/NULL today. That is currently harmless — the
# orchestrator fetches the text via database_client.get_prompt_template (text
# only) and passes model_override=lang_config.question_model — but it is a trap
# for any future caller routed through prompt_service.get_template_config, which
# raises RuntimeError on a NULL model. We populate it with the model the path
# actually uses (question_literal_detail's, per _resolve_models) so the row is
# self-describing.
ROWS = [
    # ── TEST GENERATION ───────────────────────────────────────────────────
    ('prose_generation_en.txt', 'prose_generation', 'en',
     'google/gemini-3.5-flash-lite', 'openrouter',
     ['【A1-A2 (Beginner)】', '【B1-B2 (Intermediate)】', '【C1-C2 (Advanced)】',
      'Critical for A1/A2', 'A1-A2 Check'],
     ['【T1 — The Toddler (Age 4-5)】', '【T6 — The Educated Professional (Age 30+)】',
      'Critical for T1/T2', 'T1/T2 Check'],
     'v2 (TASK-733): three collapsed CEFR bands replaced by six single-tier '
     'sections keyed to T1-T6, matching the T-code the caller injects into '
     '{complexity_tier}. Band-conditional rules re-keyed to tiers.'),

    ('prose_generation_zh.txt', 'prose_generation', 'zh',
     'qwen/qwen3.7-plus', 'openrouter',
     ['【A1-A2 (初学者)】', '【B1-B2 (中级)】', '【C1-C2 (高级)】',
      '(A1/A2专用)', '检查 A1/A2 段落'],
     ['【T1 — 幼儿（4-5岁）】', '【T6 — 专业人士（30+岁）】', 'HSK', '(T1/T2 专用)'],
     'v2 (TASK-733): six single-tier sections keyed to T1-T6. HSK anchors kept '
     'and re-hung off tiers (T1=HSK1-2 … T6=HSK6+).'),

    ('prose_generation_ja.txt', 'prose_generation', 'ja',
     'qwen/qwen3.7-plus', 'openrouter',
     ['【A1-A2 (初心者)】', '【B1-B2 (中級)】', '【C1-C2 (上級)】',
      '指定レベルがA1-A2の場合', 'A1-A2の場合'],
     ['【T1 — 幼児（4-5歳）】', '【T6 — 社会人（30歳以上）】', 'JLPT',
      '指定レベルが T1 または T2 の場合'],
     'v2 (TASK-733): six single-tier sections keyed to T1-T6. JLPT anchors kept '
     'and re-hung off tiers (T1=N5 … T6=N1+).'),

    ('title_generation_en.txt', 'title_generation', 'en',
     'google/gemini-3.5-flash-lite', 'openrouter',
     ['CEFR LEVEL:', 'Difficulty 1-2 (A1)', 'Difficulty 8-9 (C2)'],
     ['COMPLEXITY TIER: {complexity_tier}', 'T1 (The Toddler, age 4-5)',
      'T6 (The Educated Professional, age 30+)', 'follow the tier'],
     'v2 (TASK-733): CEFR label removed; the difficulty->CEFR ladder re-keyed to '
     'T1-T6 using dim_complexity_tiers boundaries. {complexity_tier} is declared '
     'authoritative over {difficulty}, resolving the two competing scales. '
     'model/provider populated (were NULL).'),

    ('title_generation_zh.txt', 'title_generation', 'zh',
     'qwen/qwen3.7-plus', 'openrouter',
     ['CEFR级别：', '难度1-2（A1）', '难度8-9（C2）'],
     ['复杂度等级：{complexity_tier}', 'T1（幼儿，4-5岁）',
      'T6（专业人士，30岁以上）', '以等级为准'],
     'v2 (TASK-733): as the en row. Per-language character counts preserved '
     'verbatim (zh counts characters, not words). model/provider populated.'),

    ('title_generation_ja.txt', 'title_generation', 'ja',
     'qwen/qwen3.7-plus', 'openrouter',
     ['CEFRレベル：', '難易度1-2（A1）', '難易度8-9（C2）'],
     ['複雑度レベル：{complexity_tier}', 'T1（幼児、4-5歳）',
      'T6（社会人、30歳以上）', '必ず複雑度レベルを優先して'],
     'v2 (TASK-733): as the en row. Per-language character counts preserved '
     'verbatim. model/provider populated.'),

    ('question_vocabulary_context_en.txt', 'question_vocabulary_context', 'en',
     'google/gemini-3.5-flash-lite', 'openrouter',
     ['**Advanced Example (C2):**'],
     ['**Advanced Example (T6 — The Educated Professional):**'],
     'v3 (TASK-733): the one CEFR band label in the few-shot heading retitled to '
     'its tier. Body unchanged. zh/ja rows are already v3-clean and untouched.'),

    # ── EXERCISE GENERATION ───────────────────────────────────────────────
    ('exercise_sentence_generation_en.txt', 'exercise_sentence_generation', 'en',
     'google/gemini-3.5-flash-lite', 'openrouter',
     ['"cefr_level"'], ['"complexity_tier": "{complexity_tier}"'],
     'v2 (TASK-733): output field renamed cefr_level -> complexity_tier. The old '
     'name held a T-code and was read by nothing; the new name IS read, at '
     'generators/cloze.py:43, which until now always fell back to its "T3" default.'),

    ('exercise_sentence_generation_zh.txt', 'exercise_sentence_generation', 'zh',
     'qwen/qwen3.7-plus', 'openrouter',
     ['"cefr_level"'], ['"complexity_tier": "{complexity_tier}"'],
     'v2 (TASK-733): output field renamed cefr_level -> complexity_tier.'),

    ('exercise_sentence_generation_ja.txt', 'exercise_sentence_generation', 'ja',
     'qwen/qwen3.7-plus', 'openrouter',
     ['"cefr_level"', '[{"sentence"'],
     ['"complexity_tier": "{complexity_tier}"', '[{{"sentence"'],
     'v2 (TASK-733): output field renamed cefr_level -> complexity_tier, AND the '
     'single-braced JSON example doubled. The single braces were a live crash: '
     'template.format() raised KeyError \'"sentence"\' outside the try block at '
     'transcript_miner.py:226, so ja grammar sentence generation never ran.'),

    ('vocab_sentence_generation_zh.txt', 'vocab_sentence_generation', 'zh',
     'qwen/qwen3.7-plus', 'openrouter',
     ['"cefr_level"'], ['"complexity_tier": "{complexity_tier}"'],
     'v2 (TASK-733): output field renamed cefr_level -> complexity_tier. zh-only '
     'row; note the vocabulary source_type is retired at orchestrator.py:194.'),

    ('collocation_sentence_generation_zh.txt', 'collocation_sentence_generation', 'zh',
     'qwen/qwen3.7-plus', 'openrouter',
     ['"cefr_level": "B1"'], ['[{{"sentence": "..."}}]'],
     'v2 (TASK-733): the hardcoded "cefr_level": "B1" field DROPPED rather than '
     'swapped for a constant tier. This generator receives no complexity_tier '
     '(placeholders: collocation_text, count, pos_pattern) and corpus_collocations '
     'carries no level column, so there is no honest tier to emit. Nothing read '
     'the field; cloze.py:43 keeps its T3 default, so behaviour is unchanged.'),

    ('cloze_distractor_generation_zh.txt', 'cloze_distractor_generation', 'zh',
     'qwen/qwen3.7-plus', 'openrouter',
     ['form_error', 'learner_error'],
     list(CLOZE_TAGS) + ['{{"distractors"'],
     'v2 (TASK-733): full port of the en v2 doctrine — five-dimension closed tag '
     'taxonomy, substitution audit, and the >=2-distinct-dimensions rule. '
     'Replaces the semantic/form_error/learner_error set that '
     'exercise_generation_schema.sql:237 seeded and cloze_distractor_quality.sql '
     'later updated for English only.'),

    ('cloze_distractor_generation_ja.txt', 'cloze_distractor_generation', 'ja',
     'qwen/qwen3.7-plus', 'openrouter',
     ['form_error', 'learner_error', '語1'],
     list(CLOZE_TAGS) + ['{{"distractors"', '"word1"'],
     'v2 (TASK-733): full port of the en v2 doctrine, as the zh row. Example keys '
     'realigned 語1/語2/語3 -> word1/word2/word3 to match en/zh (the map is '
     'self-keyed at runtime, so this is cosmetic).'),
]


def md5(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def read_draft(filename: str) -> str:
    """Read a draft as LF-normalised text; EOL is reapplied per row later."""
    with open(os.path.join(DRAFTS, filename), encoding='utf-8', newline='') as handle:
        return handle.read().replace('\r\n', '\n')


def detect_eol(text: str) -> str:
    """Return the incumbent row's line-ending convention.

    Rows are not uniform: ids 69/180/190 are LF-only, the other eleven CRLF.
    A row with no newline at all defaults to LF (nothing to preserve).
    """
    return '\r\n' if '\r\n' in text else '\n'


def placeholders(text: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


def fetch(db, task: str, lang_id: int) -> list[dict]:
    return (db.table('prompt_templates')
              .select('id, version, is_active, template_text, model, provider')
              .eq('task_name', task)
              .eq('language_id', lang_id)
              .order('version')
              .execute().data)


def check_row(task, lang, draft_lf, incumbent, must_go, must_have,
              for_write: bool = True) -> list[str]:
    """Assertions on a draft. Returns a list of problems; empty means go.

    ``for_write`` gates the drift check only. Before writing, every ``must_go``
    token must still be present in the incumbent — that is what proves the
    rewrite targets the live text rather than silently bumping a version that
    already changed. After writing, the incumbent IS the new row, so those
    tokens are legitimately gone and the check must not run; --verify passes
    for_write=False. Every other assertion applies in both modes.
    """
    problems = []
    inc = incumbent['template_text']

    # 1. The substitution must actually fire against the LIVE text.
    for token in must_go:
        if for_write and token not in inc:
            problems.append(
                f'DRIFT: must_go token {token!r} is NOT in the live v'
                f'{incumbent["version"]} row — it changed since the audit; '
                f're-read the row before writing.')
        if token in draft_lf:
            problems.append(f'NO-OP: must_go token {token!r} survives in the draft.')
    for token in must_have:
        if token not in draft_lf:
            problems.append(f'MISSING: must_have token {token!r} absent from the draft.')

    # 2. No CEFR token may survive anywhere in the draft.
    leftover = CEFR_RE.findall(draft_lf)
    if leftover:
        problems.append(f'CEFR tokens survive in the draft: {sorted(set(leftover))}')
    if 'cefr' in draft_lf.lower():
        problems.append('the substring "cefr" survives in the draft (any case).')

    # 3. Parser contract: no placeholder the caller does not supply.
    allowed = CALLER_ARGS[task]
    used = placeholders(draft_lf)
    unknown = used - allowed
    if unknown:
        problems.append(
            f'placeholder(s) {sorted(unknown)} are not supplied by the caller '
            f'(allowed: {sorted(allowed)}) — this is a KeyError at generation time.')

    # 4. Brace balance: after formatting with dummy args the draft must not raise.
    try:
        draft_lf.format(**{k: f'<{k}>' for k in allowed})
    except Exception as exc:  # noqa: BLE001 - any format failure is fatal here
        problems.append(f'draft fails str.format(): {type(exc).__name__}: {exc}')

    # 5. Cloze rows must carry the full five-dimension closed set.
    if task == 'cloze_distractor_generation':
        for tag in CLOZE_TAGS:
            if f'"{tag}"' not in draft_lf:
                problems.append(f'cloze taxonomy incomplete: "{tag}" missing.')

    return problems


def plan(db, for_write: bool = True):
    """Build the plan, running every check. Aborts on any problem.

    When for_write is False (--verify) the target version is the row that is
    active NOW rather than max(version)+1, so verification reads back what was
    actually written instead of proposing a further bump.
    """
    jobs, problems = [], []
    for (fname, task, lang, model, provider, must_go, must_have, desc) in ROWS:
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

        draft_lf = read_draft(fname)
        row_problems = check_row(task, lang, draft_lf, incumbent, must_go,
                                 must_have, for_write=for_write)
        problems.extend(f'{task} [{lang}]: {p}' for p in row_problems)

        eol = detect_eol(incumbent['template_text'])
        body = draft_lf.replace('\n', eol) if eol == '\r\n' else draft_lf
        new_version = (max(r['version'] for r in rows) + 1) if for_write             else incumbent['version']

        jobs.append({
            'task': task, 'lang': lang, 'lang_id': lang_id,
            'incumbent_id': incumbent['id'], 'incumbent_version': incumbent['version'],
            'version': new_version, 'model': model, 'provider': provider,
            'body': body, 'description': desc,
            'eol': 'CRLF' if eol == '\r\n' else 'LF',
            'model_was': incumbent['model'],
        })
    return jobs, problems


def apply(db, jobs, dry_run: bool) -> None:
    for job in jobs:
        note = ''
        if job['model_was'] is None:
            note = f'  [model NULL -> {job["model"]}]'
        print(f'  {job["task"]:<32} {job["lang"]} '
              f'v{job["incumbent_version"]} -> v{job["version"]}  '
              f'{job["eol"]:<4} {len(job["body"]):>5} chars  '
              f'md5 {md5(job["body"])}{note}')
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
    print(f'\n{"task_name":<32} {"lg":<3} {"v":<4} {"active":<7} {"md5":<6} {"eol":<5} rows')
    print('-' * 82)
    for job in jobs:
        rows = fetch(db, job['task'], job['lang_id'])
        target = next((r for r in rows if r['version'] == job['version']), None)
        if target is None:
            print(f'{job["task"]:<32} {job["lang"]:<3} MISSING v{job["version"]}')
            problems += 1
            continue

        stored = target['template_text']
        matches = md5(stored) == md5(job['body'])
        eol_ok = detect_eol(stored) == ('\r\n' if job['eol'] == 'CRLF' else '\n')
        active_count = sum(1 for r in rows if r['is_active'])

        flags = ''
        if not matches:
            flags += ' MD5-MISMATCH'
            problems += 1
        if not target['is_active']:
            flags += ' NOT-ACTIVE'
            problems += 1
        # The invariant that matters: exactly one active row per (task, language).
        # Zero means get_template_config raises and the caller fails.
        if active_count != 1:
            flags += f' ACTIVE-ROWS={active_count}'
            problems += 1
        if not eol_ok:
            flags += ' EOL-CHANGED'
            problems += 1
        if not target['model'] or not target['provider']:
            flags += ' NULL-MODEL-OR-PROVIDER'
            problems += 1
        if CEFR_RE.search(stored) or 'cefr' in stored.lower():
            flags += ' CEFR-SURVIVES'
            problems += 1

        print(f'{job["task"]:<32} {job["lang"]:<3} v{job["version"]:<3} '
              f'{"yes":<7} {str(matches):<6} {job["eol"]:<5} '
              f'{len(rows)} version(s){flags}')
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true', help='show the plan, write nothing')
    parser.add_argument('--verify', action='store_true', help='verify only, write nothing')
    args = parser.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    jobs, problems = plan(db, for_write=not args.verify)
    if problems:
        print('PRE-FLIGHT FAILED — nothing written:\n')
        for p in problems:
            print(f'  ! {p}')
        return 1
    print(f'pre-flight OK for {len(jobs)} row(s)\n')

    if not args.verify:
        print('plan:' if args.dry_run else 'applying:')
        apply(db, jobs, args.dry_run)
        if args.dry_run:
            return 0

    problems = verify(db, jobs)
    print(f'\n{"OK - all rows verified" if not problems else f"{problems} PROBLEM(S)"}')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
