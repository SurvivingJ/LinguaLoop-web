"""Build the tier-keyed question template seed (ADR-040, TASK-926).

Each tier row = its base row's template_text, unchanged, + a level block
appended at the end. Built in SQL from the live base row (``base || block``)
so the base's JSON output-format section stays byte-identical and the seed
never carries a stale copy of the base text.

Rows: the question types the tier mix uses at T1-T3
(migrations/fix_question_type_mix_t3_t5_t6.sql):

  T1  literal_detail, vocabulary_context
  T2  literal_detail, vocabulary_context, main_idea
  T3  literal_detail, vocabulary_context, main_idea, supporting_detail

x zh / en / ja = 27 rows, version 100 + tier, same model/provider as the base.

    python scripts/build_tier_question_templates.py > migrations/seed_tier_question_templates.sql

The level blocks are the reviewable content; they have not had a native
review pass yet (owed — see the log).
"""

from __future__ import annotations

import sys

TIER_TYPES = {
    1: ('literal_detail', 'vocabulary_context'),
    2: ('literal_detail', 'vocabulary_context', 'main_idea'),
    3: ('literal_detail', 'vocabulary_context', 'main_idea', 'supporting_detail'),
}
LANG_IDS = {'zh': 1, 'en': 2, 'ja': 3}

# --------------------------------------------------------------- ja

JA_BEGINNER = """【レベル別の要件（初級・T{tier}）— 上の難易度の指示より、こちらを優先すること】
・質問文・選択肢・解説は、ひらがなとカタカナで書くこと。漢字は、資料の本文に出てくる漢字だけ使ってよい。
・資料が分かち書き（ことばの間に空白）なら、質問文と選択肢も同じように分かち書きにすること。
・質問文は25字以内の短くやさしい文にすること。「文中の」「最も適切なもの」「選んでください」などのかたい言い方は使わないこと。例：「ロボットはどこでてつだいをしますか。」
・選択肢は15字以内の短い語句にし、四つとも同じ形（名詞なら名詞）にそろえること。
・正解は資料にはっきり書いてあることにすること。まちがいの選択肢も、資料の話題に関係のある、もっともらしいものにすること。"""

JA_T3 = """【レベル別の要件（T3）— 上の難易度の指示より、こちらを優先すること】
・質問文と選択肢は、やさしい日本語（JLPT N4〜N3 程度）で書くこと。資料にない難しい漢語や、「最も適切なもの」のようなかたい言い方は避けること。
・質問文は35字以内、選択肢は20字以内を目安にすること。
・四つの選択肢の長さと形をそろえ、正解だけが長くならないようにすること。"""

JA_TYPE = {
    (True, 'vocabulary_context'): "・語彙の問題では、資料に出てくる、子どもがよく使うことばを一つ選び、（ ）を付けて示すこと。四字熟語・ことわざ・慣用句は問わないこと。選択肢は、そのことばの意味を、ひらがなのやさしい言い方で説明したものにすること。例：質問「（てつだい）は、どういういみですか。」、選択肢「ひとをたすけること」。",
    (True, 'main_idea'): "・中心の内容を問う問題では、「このおはなしは、なにについてかいてありますか。」のような短い質問にすること。選択肢は短い一文にし、資料の文をそのまま長く写さないこと。",
    (False, 'vocabulary_context'): "・語彙の問題では、日常でよく使うことばや、文脈で意味が決まる基本的な語を問うこと。四字熟語やことわざは問わないこと。選択肢の説明には、問う語より難しいことばを使わないこと。",
    (False, 'main_idea'): "・選択肢は、資料の文をそのまま写さず、短く言い換えること。",
    (False, 'supporting_detail'): "・理由や例を問うときは、資料に書いてある理由そのものを短く言い換えて正解にすること。",
}
JA_END = "・出力は、上に示した JSON オブジェクトのみとすること。"

# --------------------------------------------------------------- zh

ZH_BEGINNER = """**难度级别要求（初级・T{tier}）——优先于上文的难度说明**
- 题干、选项和解释只用简单的字：文章中出现过的字，或 HSK 1–2 级常用字。
- 题干不超过 15 个字，用简单的口语问句，例如"小猫在哪里睡觉？"。不要用"下列""最恰当""根据文章"等书面说法。
- 每个选项不超过 8 个字，四个选项形式一致（都是名词，或都是短句）。
- 正确答案必须在文章中明确写出；错误选项要与文章话题有关、看起来合理。"""

ZH_T3 = """**难度级别要求（T3）——优先于上文的难度说明**
- 题干和选项用 HSK 3 级以内的常用词，避免文章中没有的书面语和成语。
- 题干不超过 20 个字，每个选项不超过 12 个字。
- 四个选项的长度和形式要相近，不要只让正确答案特别长。"""

ZH_TYPE = {
    (True, 'vocabulary_context'): '- 词汇题：选文章中一个常用词，用“”标出，不考成语或俗语。选项用比这个词更简单的话解释它的意思，例如“‘帮忙’是什么意思？”，选项“帮助别人”。',
    (True, 'main_idea'): '- 主旨题：题干如“这个故事主要讲了什么？”；每个选项是一句短话，不要照抄原文长句。',
    (False, 'vocabulary_context'): '- 词汇题：考常用词在上下文中的意思，不考成语或俗语；解释用的词不能比被考的词更难。',
    (False, 'main_idea'): '- 选项用自己的话简短概括，不要照抄原文。',
    (False, 'supporting_detail'): '- 问原因或例子时，正确答案是文章中写明的原因，用简短的话转述。',
}
ZH_END = "- 仅返回上面所示的 JSON 对象。"

# --------------------------------------------------------------- en

EN_BEGINNER = """**LEVEL REQUIREMENTS (beginner, T{tier}) — these override any difficulty guidance above**
- Write the question, choices and explanation in very simple English (CEFR A1-A2): short, common words. Words from the passage are fine.
- The question is at most 10 words, a plain direct question such as "Where does the cat sleep?" Do not use phrases like "according to the passage", "best expresses" or "primarily".
- Each choice is at most 6 words, and all four have the same form (all nouns, or all short phrases).
- The correct answer is stated plainly in the passage; wrong choices are about the same topic and look reasonable."""

EN_T3 = """**LEVEL REQUIREMENTS (T3) — these override any difficulty guidance above**
- Use clear, everyday English (CEFR B1). Avoid academic phrasing that is not in the passage.
- The question is at most 14 words; each choice at most 10 words.
- Keep all four choices similar in length and form; the correct answer must not be clearly the longest."""

EN_TYPE = {
    (True, 'vocabulary_context'): '- Vocabulary question: pick one common word from the passage and put it in quotation marks; do not test idioms. The choices explain its meaning with easier words, e.g. What does "help" mean here? -> "do something for someone".',
    (True, 'main_idea'): '- Main-idea question: ask something like "What is this story mostly about?"; each choice is one short sentence, not copied from the passage.',
    (False, 'vocabulary_context'): '- Vocabulary question: test a common word whose meaning depends on context; do not test idioms or rare words; each choice must use easier words than the target word.',
    (False, 'main_idea'): '- Summarise in your own short words; do not copy a sentence from the passage.',
    (False, 'supporting_detail'): '- For a reason or example question, the correct answer is the reason the passage gives, briefly paraphrased.',
}
EN_END = "- Return ONLY the JSON object shown above, no additional text."

BLOCKS = {
    'ja': (JA_BEGINNER, JA_T3, JA_TYPE, JA_END),
    'zh': (ZH_BEGINNER, ZH_T3, ZH_TYPE, ZH_END),
    'en': (EN_BEGINNER, EN_T3, EN_TYPE, EN_END),
}


def level_block(lang: str, tier: int, type_code: str) -> str:
    beginner, t3, per_type, end = BLOCKS[lang]
    is_beginner = tier <= 2
    head = (beginner if is_beginner else t3).replace('{tier}', str(tier))
    lines = [head]
    extra = per_type.get((is_beginner, type_code))
    if extra:
        lines.append(extra)
    lines.append(end)
    text = '\n'.join(lines)
    # Templates go through str.format: a stray brace would break rendering.
    assert '{' not in text and '}' not in text, (lang, tier, type_code)
    assert '$lvl$' not in text
    return text


def _q(text: str) -> str:
    assert '$lvl$' not in text
    return f"$lvl${text}$lvl$"


def build_sql() -> str:
    """Compact seed: each level text appears once; SQL assembles the blocks.

    block = replace(head, '{tier}', tier) [|| E'\\n' || type line] || E'\\n' || end line
    — the same string level_block() returns (checked by
    tests/test_tier_templates.py::test_seed_sql_matches_level_blocks).
    """
    heads, lines, ends, mix = [], [], [], []
    for lang, lang_id in LANG_IDS.items():
        beginner, t3, per_type, end = BLOCKS[lang]
        heads.append(f"    ({lang_id}, true,  {_q(beginner)})")
        heads.append(f"    ({lang_id}, false, {_q(t3)})")
        for (is_beg, t), line in per_type.items():
            lines.append(f"    ({lang_id}, {str(is_beg).lower()}, 'question_{t}', {_q(line)})")
        ends.append(f"    ({lang_id}, {_q(end)})")
    for tier, types in TIER_TYPES.items():
        for t in types:
            mix.append(f"    ({tier}, 'question_{t}')")
    j = ',\n'.join
    return f"""-- ADR-040 / TASK-926: tier-keyed question templates for T1-T3, zh/en/ja (27 rows).
-- GENERATED by scripts/build_tier_question_templates.py - edit the script, not this file.
-- Requires migrations/prompt_templates_tier_id.sql. Inert until TEST_GEN_TIER_TEMPLATES
-- enables a language. Each row = the active base row (tier_id IS NULL, highest version),
-- unchanged, || two newlines || a level block. Version = 100 + tier.
-- Data-only: no new objects. Idempotent (skips rows that already exist).

BEGIN;

WITH heads(language_id, beginner, head) AS (VALUES
{j(heads)}
), type_lines(language_id, beginner, task_name, line) AS (VALUES
{j(lines)}
), end_lines(language_id, line) AS (VALUES
{j(ends)}
), tier_mix(tier_id, task_name) AS (VALUES
{j(mix)}
), wanted AS (
    SELECT m.tier_id, m.task_name, h.language_id,
           replace(h.head, '{{tier}}', m.tier_id::text)
             || coalesce(E'\\n' || tl.line, '')
             || E'\\n' || e.line AS block
    FROM tier_mix m
    JOIN heads h ON h.beginner = (m.tier_id <= 2)
    JOIN end_lines e ON e.language_id = h.language_id
    LEFT JOIN type_lines tl ON tl.language_id = h.language_id
                           AND tl.beginner = (m.tier_id <= 2)
                           AND tl.task_name = m.task_name
)
INSERT INTO public.prompt_templates
    (task_name, template_text, version, is_active, description, language_id, model, provider, tier_id)
SELECT b.task_name,
       b.template_text || E'\\n\\n' || w.block,
       100 + w.tier_id, true,
       'ADR-040 T' || w.tier_id || ' level template (base v' || b.version || ' + level block)',
       b.language_id, b.model, b.provider, w.tier_id
FROM wanted w
JOIN LATERAL (
    SELECT * FROM public.prompt_templates p
    WHERE p.task_name = w.task_name AND p.language_id = w.language_id
      AND p.is_active AND p.tier_id IS NULL
    ORDER BY p.version DESC LIMIT 1
) b ON true
WHERE NOT EXISTS (
    SELECT 1 FROM public.prompt_templates x
    WHERE x.task_name = w.task_name AND x.language_id = w.language_id AND x.tier_id = w.tier_id
);

COMMIT;

-- Verify: expect T1 = 2, T2 = 3, T3 = 4 rows per language (27 total).
SELECT language_id, tier_id, count(*) FROM public.prompt_templates
WHERE tier_id IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2;
"""


if __name__ == '__main__':
    sys.stdout.write(build_sql())
