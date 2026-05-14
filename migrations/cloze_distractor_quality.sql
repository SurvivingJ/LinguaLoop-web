-- ============================================================================
-- Cloze distractor quality revamp.
-- Date: 2026-05-14
--
-- Three changes:
--   1. vocab_prompt2_exercises (English, v3 → v4): replace the L3 block with
--      an explicit per-distractor self-check requiring a failure-dimension
--      tag and a substitution audit. L1, L5, L6 preserved verbatim.
--   2. vocab_prompt2_exercises (Chinese, v1 → v2): mirror the same L3
--      strengthening for the Chinese template. L1, L5, L6 preserved verbatim.
--   3. cloze_distractor_generation (legacy, v1 → v2): strengthen the legacy
--      distractor prompt with the same self-check rules.
--   4. NEW task cloze_distractor_judge v1: a cheap-model verifier that rules
--      on whether each distractor could itself pass as a valid completion.
--
-- See wiki/features/exercise-generation-prompts.md for verbatim text.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. vocab_prompt2_exercises English: v3 → v4
-- ----------------------------------------------------------------------------
UPDATE public.prompt_templates
SET is_active = false
WHERE task_name = 'vocab_prompt2_exercises'
  AND language_id = 2
  AND version = 3;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider
)
VALUES (
    'vocab_prompt2_exercises',
    2,
    4,
    $PROMPT$Role: Expert computational linguist generating English vocabulary exercises.

Target word: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Tier: {complexity_tier}
Definition: {definition}
Primary collocate: {primary_collocate}

Base sentences:
{sentences_json}

Generate ONLY the exercise levels listed here: {active_levels_json}

Rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. For every option: "1" = option text, "2" = true/false (correct?), "3" = explanation.
4. Explanations must be short, clear, and pedagogical.
5. Treat the target word as a discrete whole word. Never confuse it with a longer word that merely contains its letters (e.g. for the target "new", do NOT use "knew", "renew", or "renewal" anywhere in Level 3, Level 5, or Level 6 sentences or distractors).

Level "1" (Listening Recognition):
- Scenario: the learner HEARS the target word spoken aloud (TTS) and must select which of 4 written options matches what they heard.
- Return 4 options. 1 correct = the target word as it would naturally be written. 3 distractors are PHONETICALLY confusable with the target by ear.
- Use a mix of at least two of these phonetic-distractor types:
  * Homophones / near-homophones (e.g. for "their": "there", "they're"; for "knew": "new", "gnu"; for "to": "too", "two")
  * Minimal pairs differing by one phoneme (e.g. for "ship": "sheep", "chip", "shop"; for "ride": "rode", "raid")
  * Same-stress same-syllable-count rhymes a learner could plausibly mishear (e.g. for "cat": "cap", "cab"; for "thing": "think", "thin")
- Hard rules for L1 distractors:
  * Each distractor MUST be a real English word.
  * Distractors MUST NOT be selected on visual/spelling similarity alone. "tough" and "though" look alike but sound completely different — they are NOT valid L1 distractors for each other.
  * Distractors MUST NOT be semantic synonyms of the target.
  * Distractors MUST NOT be the target word itself with a different inflection (e.g. "ran" is not a valid distractor for "run").
- L1 is the only level where homophones/near-homophones of the target are permitted as distractors.
- For each option, "3" (explanation) briefly states the phonetic relationship to the target — e.g. "homophone: same /ðeə/ sound, different spelling and meaning" or "minimal pair: differs only in /ɪ/ vs /iː/" or "rhymes with target but starts with a different consonant".

Level "3" (Cloze Completion):
- Use sentence at index {level_3_sentence_index}.
- Correct option = the target word as it appears in that sentence (its exact inflected form).
- 3 distractors: same POS as the target, grammatically valid in the slot, but contextually wrong.
- Do NOT use any homophone or near-homophone of the target as a distractor here.
- MANDATORY per-distractor self-check before emitting each distractor:
  (a) Failure dimension — tag each distractor with exactly one reason it fails in this sentence, chosen from:
        - "semantic"      : refers to a wrong class of referent / wrong concept
        - "collocational" : does not co-occur naturally with the surrounding lexis in this sentence
        - "aspectual"     : wrong lexical aspect / event structure (stative vs telic vs activity)
        - "register"      : wrong formality, domain, or social fit for this sentence
        - "valency"       : wrong argument structure (e.g. transitive vs intransitive, wrong preposition complement)
      Put the tag in the option's "3" (explanation) as a leading label, e.g. "semantic: ...".
  (b) Substitution audit — silently consider one common synonym of the target word and ask: if I swapped that synonym in for the target, would my distractor become a valid completion? If yes, REJECT this distractor and choose a different one. The distractor must be wrong for THIS sentence even under near-synonym variants of the target.
- Across the 3 distractors, at least TWO distinct failure dimensions must appear. No four near-identical "wrong-but-similar" options.
- Final pre-output check: silently re-read the sentence with each distractor in the blank. If any reads as natural, replace it before emitting.

Level "5" (Collocation Gap Fill) — only if included:
- Use sentence at index {level_5_sentence_index}.
- Correct option = the primary collocate.
- 3 distractors: semantically close but collocationally unnatural with the target word.

Level "6" (Semantic Discrimination):
- Use sentence at index {level_6_sentence_index} as the correct usage.
- Generate 3 new sentences using the target word that are grammatical but semantically or pragmatically inappropriate.
- Each new sentence MUST contain the target word as a whole word, never embedded in another word.

Output schema:
Top-level keys are level numbers as strings.
Each level value is an array of 4 option objects: [{"1": text, "2": bool, "3": explanation}, ...]
Exception: Level "6" value is {"1": correct_sentence_index, "2": array of 3 wrong sentence objects [{"1": text, "2": explanation}, ...]}$PROMPT$,
    true,
    'anthropic/claude-opus-4-7',
    'openrouter'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. vocab_prompt2_exercises Chinese: v1 → v2
-- ----------------------------------------------------------------------------
UPDATE public.prompt_templates
SET is_active = false
WHERE task_name = 'vocab_prompt2_exercises'
  AND language_id = 1
  AND version = 1;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider
)
VALUES (
    'vocab_prompt2_exercises',
    1,
    2,
    $PROMPT$角色：你是一位专业的计算语言学家，正在为汉语词汇学习者生成练习题。

目标词：{word}
词性：{pos}
语义类：{semantic_class}
学习者级别：{complexity_tier}
释义：{definition}
首要搭配词：{primary_collocate}

基础例句：
{sentences_json}

仅生成以下列出的练习级别：{active_levels_json}

通用规则：
1. 所有输出值必须使用简体中文，且不得夹杂英文。
2. 仅输出有效的 JSON，键使用数字字符串。
3. 每个选项格式："1" = 选项文本，"2" = 真 / 假（是否正确，使用 JSON 布尔值 true / false），"3" = 简短的教学解释（简体中文）。
4. 解释必须简短、清楚、具有教学价值。
5. 将目标词视为一个完整的词。在 L3、L5、L6 中，干扰项与备选句子中的目标字符必须承担与所锁定义项相同的句法 / 语义角色——禁止把目标字仅作为另一个词的字符片段使用（参见 prompt 1 规则 13）。

L1（听音辨字 — 听力练习）：
- 题目场景：学习者听到目标词的语音，从 4 个汉字 / 词选项中选出对应的写法。
- 返回 4 个选项。1 个正确 = 目标词；3 个为干扰项。
- 干扰项类型：声调混淆（同音节但声调不同）。
  - 单音节目标，例如 "妈"（mā）：干扰项为 "麻"（má）、"马"（mǎ）、"骂"（mà）。
  - 多音节目标，例如 "起来"（qǐ lái）：干扰项可改变其中一个音节的声调，例如 "起赖"（qǐ lài）、"齐来"（qí lái）等真实存在或合理的双音节组合；若找不到三个真实词，可使用与目标共享首音节但末音节声调不同的真实词。
- 干扰项必须是真实存在的汉字 / 词，且不得为目标词的同义词。
- 干扰项不得使用整体同音同调的纯同形异义字（这些属于纯听音无法区分的情形，不应在 L1 出现）。
- 解释要点：说明声调差异如何改变意义。

L3（语境填空）：
- 使用句子索引 {level_3_sentence_index} 的句子。
- 正确选项 = 目标词在该句中的形式（与该句出现的字符串完全一致）。
- 3 个干扰项：词性相同、语法上在该上下文中可填入但语义 / 语境不合适。
- 不得使用目标词的同音字 / 近音字（声调混淆留给 L1）。
- 干扰项必须满足规则 5 的义项 / 角色一致性。
- 强制性逐项自检（每个干扰项发出前都必须完成）：
  (a) 失效维度 — 给每个干扰项标注唯一一个在该句中失效的原因，从下列五类选其一：
        - "语义"   : 指向错误的指称类别 / 错误的概念
        - "搭配"   : 在该句上下文中与周围词语搭配不自然
        - "体貌"   : 词汇体 / 事件结构错误（如状态 vs 完成 vs 活动）
        - "语域"   : 正式度 / 领域 / 社会语用不合该句
        - "配价"   : 论元结构错误（如及物 vs 不及物、错介词补语）
      将该标签作为选项 "3"（解释）的前缀写出，例如："语义：……"。
  (b) 替换审计 — 在心中替换目标词为它的一个常见近义词，然后判断：用该近义词替换目标词后，这个干扰项是否会成为该句的合理答案？如果是，立即拒绝该干扰项并换一个。干扰项必须在目标词的近义变体下仍然在该句中错误。
- 3 个干扰项必须覆盖至少两个不同的失效维度，不能 4 个选项都是同一类"差不多但错了"。
- 最终自检：把每个干扰项填入空格逐句默读。若有任何一项读起来自然通顺，立刻替换。

L5（搭配填空）— 仅当包含时生成：
- 使用句子索引 {level_5_sentence_index} 的句子。
- 正确选项 = 首要搭配词（在该句中作为搭配出现）。
- 3 个干扰项：与正确搭配词词性相同、语义相近，但与目标词搭配时不自然或会改变义项。
- 解释要点：指出搭配词与目标词的固定关系。

L6（语义辨析）：
- 使用句子索引 {level_6_sentence_index} 的句子作为正确句子。
- 生成 3 个新的句子，每句都使用目标词，但语法上正确而语义 / 语用 / 搭配上不自然或错误。错误类型应从以下选取（每句尽量使用不同类别）：
  - 量词使用错误（针对名词类目标，例如 "一只书" 应为 "一本书"）；
  - 体标位置 / 选用错误（例如 "了 / 着 / 过" 用错位置或用错体）；
  - 语序错误（例如时间状语错位、"主题—评论" 结构破坏）；
  - 方向 / 结果补语误用（例如目标词为 "起来"，错误句使用 "起去"、"出来"、"下来" 替代但语义相反或不通）。
- 每个错误句必须包含目标词 {word}，并满足规则 5 的义项 / 角色一致性（即目标词字符仍在做该义项之事，错误是在其它结构层面）。
- 字段："1": 文本，"2": 解释（指出具体错误类型与原因）。

输出 schema：
顶层键为级别编号字符串。
L1 / L3 / L5 的值为 4 个选项对象数组：[{"1": 文本, "2": 真/假, "3": 解释}, ...]
L6 的值为：{"1": 正确句子索引, "2": [3 个错误句对象 {"1": 文本, "2": 解释}]}$PROMPT$,
    true,
    'qwen/qwen-max',
    'openrouter'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 3. cloze_distractor_generation (legacy): v1 → v2
-- ----------------------------------------------------------------------------
-- Note: prompt_templates.language_id is NOT NULL. The legacy loader
-- (base_generator.load_prompt_template) ignores language_id and picks the
-- highest-versioned row for the task_name, so a single English row covers
-- every caller. Tagged language_id = 2 for accuracy of the row metadata.
UPDATE public.prompt_templates
SET is_active = false
WHERE task_name = 'cloze_distractor_generation'
  AND version = 1;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider
)
VALUES (
    'cloze_distractor_generation',
    2,
    2,
    $PROMPT$Sentence: {original_sentence}
Blank: {sentence_with_blank}
Correct answer: {correct_answer}
Learner level: {complexity_tier}

Generate exactly 3 distractors that are wrong completions of this sentence.

Hard rules:
1. Each distractor must be the same part of speech as the correct answer.
2. Each distractor must be grammatically valid in the blank slot.
3. Each distractor must be contextually WRONG in this specific sentence.
4. Distractors must NOT be homophones, near-homophones, inflected variants of the correct answer, or substrings of it.

Mandatory per-distractor self-check before emitting each one:
(a) Failure dimension — assign exactly one reason it fails here, from:
    - "semantic"      : wrong referent class / wrong concept
    - "collocational" : does not co-occur naturally with the surrounding lexis
    - "aspectual"     : wrong lexical aspect / event structure
    - "register"      : wrong formality / domain / social fit
    - "valency"       : wrong argument structure / wrong complement
(b) Substitution audit — consider one common synonym of the correct answer and silently swap it in. If your distractor would become a valid completion under that synonym, REJECT the distractor and pick a different one. The distractor must be wrong for THIS sentence even under near-synonym variants.

Across the 3 distractors, at least TWO distinct failure dimensions must appear — no near-identical wrong-but-similar set.
Re-read the sentence with each distractor in the blank as a final check. If any reads naturally, replace it before emitting.

Return JSON:
{{"distractors": ["word1","word2","word3"], "distractor_tags": {{"word1":"semantic","word2":"collocational","word3":"valency"}}, "explanation": "Brief explanation of why the correct answer is right."}}

Put the correct answer first in any option lists — do NOT shuffle.$PROMPT$,
    true,
    'google/gemini-flash-1.5',
    'openrouter'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 4. NEW: cloze_distractor_judge v1
-- ----------------------------------------------------------------------------
-- Note: cloze_judge._load_template doesn't filter by language_id, so a
-- single row covers every caller. Tagged language_id = 2 to satisfy the
-- NOT NULL constraint; rules are language-agnostic.
INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'cloze_distractor_judge',
    2,
    1,
    $PROMPT$You are a strict cloze-test judge. A learner is shown a sentence with a blank and 4 options. Exactly ONE option is the intended correct answer; the other 3 must each be clearly wrong in this sentence. Your job is to rule on each candidate distractor and flag any that could in fact pass as a valid completion.

Sentence with blank: {sentence_with_blank}
Intended correct answer: {correct_answer}
Candidate distractors:
{distractors_numbered}

For EACH distractor, rule as follows:
- "keep"   = grammatical in the slot but CLEARLY semantically, collocationally, aspectually, register-wise, or valency-wise wrong in THIS sentence. The distractor would never be marked correct by a competent native speaker.
- "reject" = the distractor could itself be selected by a competent reader as a valid completion of this sentence (i.e. it is grammatically AND semantically acceptable, even if less idiomatic than the intended answer). Synonyms, near-synonyms, and contextually appropriate alternatives must all be REJECTed.

Be conservative: if you are unsure whether a distractor is acceptable in context, REJECT it. A good cloze test has zero ambiguous distractors.

Return JSON ONLY, keyed by the 1-based index of each distractor, with verdict and a short reason (<= 12 words):
{{"1": {{"verdict": "keep|reject", "reason": "..."}}, "2": {{"verdict": "keep|reject", "reason": "..."}}, "3": {{"verdict": "keep|reject", "reason": "..."}}}}

No prose outside the JSON. No markdown fences.$PROMPT$,
    true,
    'google/gemini-2.5-flash-lite',
    'openrouter',
    'Post-generation verifier that rejects cloze distractors which could pass as the correct answer in context.'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- Verification (run manually after migration)
-- ----------------------------------------------------------------------------
-- SELECT task_name, language_id, version, is_active, model
-- FROM public.prompt_templates
-- WHERE task_name IN ('vocab_prompt2_exercises','cloze_distractor_generation','cloze_distractor_judge')
-- ORDER BY task_name, language_id NULLS FIRST, version;
