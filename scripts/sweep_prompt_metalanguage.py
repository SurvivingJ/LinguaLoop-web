"""Replace leftover English *metalanguage* in zh/ja prompt rows. No LLM involved.

These are the residue after the native rewrites: single English words describing
output *format* inside prompts that are otherwise fully in the target language —
"不要使用 markdown 代码块", "输出 schema：", "IPA フィールド".

WHAT THIS DELIBERATELY DOES NOT TOUCH
-------------------------------------
Everything else `audit_prompt_latin.py` still reports is load-bearing or
legitimate, and was checked in context before being excluded:

  * parser enums and constants — `no_relation`, `corpus_validated`,
    `llm_asserted`, the 27 persona archetypes, `form_error`, `estimated_tier`,
    `sentence_index`, `subject_verb_agreement`, `antonym`/`synonym`, and the
    `plain/polite/honorific/humble/formal/casual` register list that must match
    the injected `{register}` value
  * `{word}`, `{pos}`, `{semantic_class}` … — these are str.format placeholders.
    A token regex matches *inside* the braces, which is why the audit appears to
    report `word` as leaked in a dozen rows. It is not.
  * `clean` in ladder_p1_sentence_judge [zh] — an emitted output value
    (`或写"clean"`, and `"reason": "clean"` in its own example), not prose.
  * proper nouns — HSK, JLPT, CEFR, ASCII, LinguaLoop, and the pinyin examples
    ("qǐ lái" vs "qi3 lai2") that are the entire point of their instruction
  * the six `dual_translation_tier*` rows, which are not prompts: they read
    "Model-routing row only; no prompt text" and are never sent to a model
  * `cloze_distractor_judge` v1 — being replaced wholesale by the staged v2

Each substitution is asserted to fire. A rule that matches nothing means the row
drifted and the assumption behind the edit no longer holds, so the run fails
rather than writing a no-op version bump.

Usage::

    python scripts/sweep_prompt_metalanguage.py --dry-run
    python scripts/sweep_prompt_metalanguage.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

LANG_ID = {'zh': 1, 'ja': 3}

# Ordered per language: longer, more specific phrases first so the generic
# fallback only catches what the specific rules missed.
SUBSTITUTIONS = {
    'zh': [
        ('markdown 代码块', '代码块'),
        ('markdown。', '代码块。'),
        ('输出 schema：', '输出结构：'),
        ('下游 prompt', '下游提示词'),
        ('prompt 1 规则', '提示词 1 规则'),
        ('mǎ vs mā', 'mǎ 与 mā'),
        ('状态 vs 完成 vs 活动', '状态／完成／活动'),
        ('字段 IPA 中的国际音标符号', '国际音标字段中的音标符号'),
    ],
    'ja': [
        ('markdown コードフェンス', 'コードフェンス'),
        ('説明・markdown は', '説明・コードフェンスは'),
        ('IPA フィールドの音声記号', '国際音声記号フィールドの音声記号'),
    ],
}

# Rows to sweep, and which substitutions must fire in each. Naming the expected
# rules is what turns "the edit ran" into "the edit did what I meant".
TARGETS: list[tuple[str, str, tuple[str, ...]]] = [
    ('ladder_collocation_judge', 'zh', ('markdown 代码块',)),
    ('ladder_l1_distractor_judge', 'zh', ('markdown 代码块', 'mǎ vs mā')),
    ('ladder_l4_morphology_generation', 'zh', ('markdown 代码块',)),
    ('ladder_l4_morphology_generation', 'ja', ('markdown コードフェンス',)),
    ('ladder_l8_collocation_repair_generation', 'zh', ('markdown 代码块',)),
    ('ladder_l8_collocation_repair_generation', 'ja', ('markdown コードフェンス',)),
    ('ladder_p1_sentence_judge', 'zh', ('markdown 代码块',)),
    ('ladder_particle_judge', 'ja', ('markdown コードフェンス',)),
    ('ladder_particle_selection_generation', 'ja', ('markdown コードフェンス',)),
    ('ladder_relation_judge', 'zh', ('markdown 代码块',)),
    ('ladder_relation_judge', 'ja', ('markdown コードフェンス',)),
    ('ladder_sentence_validity_judge', 'zh', ('markdown 代码块',)),
    ('ladder_syn_ant_generation', 'zh', ('markdown 代码块',)),
    ('ladder_syn_ant_generation', 'ja', ('markdown コードフェンス',)),
    ('semantic_class_classification', 'zh', ('markdown。',)),
    ('semantic_class_classification', 'ja', ('説明・markdown は',)),
    ('test_distractor_plausibility', 'zh', ('markdown 代码块',)),
    ('vocab_prompt1_core', 'zh', ('输出 schema：', '下游 prompt',
                                  '字段 IPA 中的国际音标符号')),
    ('vocab_prompt1_core', 'ja', ('IPA フィールドの音声記号',)),
    ('vocab_prompt2_exercises', 'zh', ('输出 schema：', 'prompt 1 规则',
                                       '状态 vs 完成 vs 活动')),
    ('vocab_prompt3_transforms', 'zh', ('输出 schema：', 'prompt 1 规则')),
]

PLACEHOLDER = re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')
JSON_KEY = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:')


def rewrite(text: str, lang: str) -> tuple[str, list[str]]:
    fired: list[str] = []
    for needle, replacement in SUBSTITUTIONS[lang]:
        if needle in text:
            text = text.replace(needle, replacement)
            fired.append(needle)
    return text, fired


def contract_intact(before: str, after: str) -> list[str]:
    """A metalanguage edit must not disturb anything the parser reads."""
    problems = []
    if sorted(PLACEHOLDER.findall(before)) != sorted(PLACEHOLDER.findall(after)):
        problems.append('placeholder set changed')
    if sorted(JSON_KEY.findall(before)) != sorted(JSON_KEY.findall(after)):
        problems.append('JSON key set changed')
    if before.count('{{') != after.count('{{') or before.count('}}') != after.count('}}'):
        problems.append('brace doubling changed')
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    problems = 0
    changed = 0

    for task, lang, expected_rules in TARGETS:
        lang_id = LANG_ID[lang]
        rows = (db.table('prompt_templates')
                  .select('id, version, is_active, template_text')
                  .eq('task_name', task).eq('language_id', lang_id)
                  .eq('is_active', True).execute().data)
        if len(rows) != 1:
            print(f'FAIL {task} [{lang}]: expected 1 active row, found {len(rows)}')
            problems += 1
            continue

        row = rows[0]
        before = row['template_text'] or ''
        after, fired = rewrite(before, lang)

        missing = [rule for rule in expected_rules if rule not in fired]
        if missing:
            # The row is not what this edit was written against. Refuse it.
            print(f'FAIL {task} [{lang}]: expected rule(s) did not fire: {missing}')
            problems += 1
            continue

        breaks = contract_intact(before, after)
        if breaks:
            print(f'FAIL {task} [{lang}]: {"; ".join(breaks)}')
            problems += 1
            continue

        if after == before:
            print(f'skip {task} [{lang}]: already clean')
            continue

        new_version = max(r['version'] for r in
                          db.table('prompt_templates').select('version')
                            .eq('task_name', task).eq('language_id', lang_id)
                            .execute().data) + 1

        print(f'{"would bump" if args.dry_run else "bump"} {task} [{lang}] '
              f'v{row["version"]} -> v{new_version}  rules: {", ".join(fired)}')
        changed += 1

        if args.dry_run:
            continue

        source = (db.table('prompt_templates').select('*')
                    .eq('id', row['id']).execute().data[0])
        db.table('prompt_templates').update({'is_active': False}).eq('id', row['id']).execute()
        db.table('prompt_templates').insert({
            'task_name': task,
            'language_id': lang_id,
            'version': new_version,
            'is_active': True,
            'model': source['model'],
            'provider': source.get('provider') or 'openrouter',
            'template_text': after,
            'description': (f'v{new_version}: English format metalanguage replaced with '
                            f'target-language wording ({", ".join(fired)}). '
                            f'No contract token touched.'),
        }).execute()

    print(f'\n{changed} row(s) {"would change" if args.dry_run else "changed"}, '
          f'{problems} problem(s)')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
