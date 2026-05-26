-- ============================================================================
-- Phase 14 — Generation Quality — Judge prompt_templates seed rows
-- Date: 2026-05-26
--
-- Seeds 6 rows: 2 judge tasks × 3 languages (zh=1, en=2, ja=3).
-- Each row carries its own model + provider so the per-language model lives
-- on the prompt row — no Config.AI_MODELS change needed (agents call
-- get_template_config(task_name, language_id) to retrieve the pair).
--
-- Per-language model defaults (tunable via UPDATE — no code change needed):
--   zh (1): deepseek/deepseek-chat
--   en (2): google/gemini-2.5-flash-lite
--   ja (3): qwen/qwen-2.5-72b-instruct
--
-- Prompt language policy
-- ----------------------
-- Non-English (ZH, JA) prompts are authored entirely in the target language
-- with zero ASCII-letter words (verified by the spot-check below).
-- All prompts use positional format placeholders {0}, {1}, {2}[, {3}] so
-- the Python judge code calls template.format(passage, question, answer[,
-- distractors_numbered]) regardless of language.
-- The JSON example in each prompt uses numeric keys "1"/"2" only — no
-- English field names appear in the prompt body.
-- The Pydantic schemas (AnswerEntailmentVerdict, DistractorPlausibilityVerdict
-- in services/test_generation/schemas.py) normalise {"1":…,"2":…} → named
-- fields at parse time.
--
-- Post-seed ASCII spot-check (result must be 0 rows):
--   SELECT task_name, language_id, regexp_matches(template_text,'[A-Za-z]+','g')
--   FROM prompt_templates
--   WHERE task_name IN ('test_answer_entailment','test_distractor_plausibility')
--     AND language_id IN (1, 3);
--
-- Idempotency: each INSERT is guarded by WHERE NOT EXISTS on
-- (task_name, language_id, version=1).
-- ============================================================================

BEGIN;

-- ============================================================
-- test_answer_entailment — English (language_id = 2)
-- ============================================================
INSERT INTO public.prompt_templates
    (task_name, language_id, template_text, version, is_active, description, model, provider)
SELECT
    'test_answer_entailment',
    2,
    $$You are a reading comprehension quality judge.

Passage:
{0}

Question:
{1}

Proposed correct answer:
{2}

Does the passage actually support the proposed answer? Rate your confidence from 0.0 to 1.0:
- 1.0 = the passage clearly and directly supports this answer
- 0.5 = the answer is ambiguous or only partially supported by the passage
- 0.0 = the passage does not support this answer, or the answer is factually wrong

Respond ONLY with valid JSON in exactly this format:
{{"1": 0.85, "2": "The passage explicitly states in paragraph 2 that..."}}$$,
    1,
    true,
    'Answer entailment judge (English): does the passage support the correct answer? Returns {"1": confidence, "2": reason}.',
    'google/gemini-2.5-flash-lite',
    'openrouter'
WHERE NOT EXISTS (
    SELECT 1 FROM public.prompt_templates
    WHERE task_name = 'test_answer_entailment' AND language_id = 2 AND version = 1
);

-- ============================================================
-- test_answer_entailment — Chinese / 中文 (language_id = 1)
-- Zero ASCII-letter words; {0}{1}{2} are positional-only (digits, no letters)
-- ============================================================
INSERT INTO public.prompt_templates
    (task_name, language_id, template_text, version, is_active, description, model, provider)
SELECT
    'test_answer_entailment',
    1,
    $$你是一位阅读理解题目质量评判员。

文章：
{0}

题目：
{1}

候选正确答案：
{2}

文章是否真正支持该候选答案？请给出0.0到1.0之间的置信度：
- 1.0 = 文章明确直接支持该答案
- 0.5 = 答案仅有部分依据，或存在歧义
- 0.0 = 文章不支持该答案，或答案与文章内容矛盾

仅以如下格式返回：
{{"1": 0.85, "2": "文章第二段明确写道……"}}$$,
    1,
    true,
    '答案蕴含判断（中文）：文章是否支持正确答案？返回 {"1": 置信度, "2": 理由}。',
    'deepseek/deepseek-chat',
    'openrouter'
WHERE NOT EXISTS (
    SELECT 1 FROM public.prompt_templates
    WHERE task_name = 'test_answer_entailment' AND language_id = 1 AND version = 1
);

-- ============================================================
-- test_answer_entailment — Japanese / 日本語 (language_id = 3)
-- Zero ASCII-letter words; {0}{1}{2} are positional-only (digits, no letters)
-- ============================================================
INSERT INTO public.prompt_templates
    (task_name, language_id, template_text, version, is_active, description, model, provider)
SELECT
    'test_answer_entailment',
    3,
    $$あなたは読解問題の品質評価員です。

文章：
{0}

問題：
{1}

候補正解：
{2}

この文章は候補正解を本当に支持していますか？0.0から1.0の確信度で評価してください：
- 1.0 = 文章が明確かつ直接的にこの解答を支持している
- 0.5 = 解答は一部しか根拠がないか、曖昧である
- 0.0 = 文章がこの解答を支持していない、または内容と矛盾している

以下の形式のみで返してください：
{{"1": 0.85, "2": "文章の第2段落に明確に記されている……"}}$$,
    1,
    true,
    '回答含意判定（日本語）：文章は正解を支持しているか？{"1": 確信度, "2": 理由} を返す。',
    'qwen/qwen-2.5-72b-instruct',
    'openrouter'
WHERE NOT EXISTS (
    SELECT 1 FROM public.prompt_templates
    WHERE task_name = 'test_answer_entailment' AND language_id = 3 AND version = 1
);

-- ============================================================
-- test_distractor_plausibility — English (language_id = 2)
-- ============================================================
INSERT INTO public.prompt_templates
    (task_name, language_id, template_text, version, is_active, description, model, provider)
SELECT
    'test_distractor_plausibility',
    2,
    $$You are a reading comprehension question quality judge.

Passage:
{0}

Question:
{1}

Correct answer:
{2}

Distractors to evaluate:
{3}

For each distractor, rate how well it functions as a plausible-but-clearly-wrong option (0.0 to 1.0):
- 1.0 = excellent: plausible enough to mislead careless readers, but clearly wrong given the passage
- 0.5 = weak: somewhat plausible but too obvious, or too similar to the correct answer
- 0.0 = invalid: could also be a correct answer, or so absurd no learner would pick it

Respond ONLY with valid JSON in exactly this format (one entry per distractor, in the same order as listed):
{{"1": [0.9, 0.4, 0.85], "2": ["Plausible but the passage rules it out in paragraph 1.", "Too obviously wrong.", "Tempting but contradicted by the final sentence."]}}$$,
    1,
    true,
    'Distractor plausibility judge (English): are distractors plausible-but-wrong? Returns {"1": [conf,...], "2": [reason,...]}.',
    'google/gemini-2.5-flash-lite',
    'openrouter'
WHERE NOT EXISTS (
    SELECT 1 FROM public.prompt_templates
    WHERE task_name = 'test_distractor_plausibility' AND language_id = 2 AND version = 1
);

-- ============================================================
-- test_distractor_plausibility — Chinese / 中文 (language_id = 1)
-- Zero ASCII-letter words; {0}{1}{2}{3} are positional-only (digits, no letters)
-- ============================================================
INSERT INTO public.prompt_templates
    (task_name, language_id, template_text, version, is_active, description, model, provider)
SELECT
    'test_distractor_plausibility',
    1,
    $$你是一位阅读理解题目质量评判员。

文章：
{0}

题目：
{1}

正确答案：
{2}

待评估干扰项：
{3}

对每个干扰项，评估其"貌似合理但明显错误"的效果（0.0到1.0）：
- 1.0 = 优质干扰项：足以误导粗心读者，但结合文章内容明显错误
- 0.5 = 较弱干扰项：有一定迷惑性，但过于明显，或与正确答案过于接近
- 0.0 = 无效干扰项：可能也是正确答案，或荒谬到学习者不会选择

仅以如下格式返回（每个干扰项一条，顺序与上述列表一致）：
{{"1": [0.9, 0.4, 0.85], "2": ["有迷惑性，但文章第一段已排除。", "过于明显错误。", "有吸引力，但与文章结尾矛盾。"]}}$$,
    1,
    true,
    '干扰项合理性判断（中文）：干扰项是否貌似合理但明显错误？返回 {"1": [置信度,...], "2": [理由,...]}。',
    'deepseek/deepseek-chat',
    'openrouter'
WHERE NOT EXISTS (
    SELECT 1 FROM public.prompt_templates
    WHERE task_name = 'test_distractor_plausibility' AND language_id = 1 AND version = 1
);

-- ============================================================
-- test_distractor_plausibility — Japanese / 日本語 (language_id = 3)
-- Zero ASCII-letter words; {0}{1}{2}{3} are positional-only (digits, no letters)
-- ============================================================
INSERT INTO public.prompt_templates
    (task_name, language_id, template_text, version, is_active, description, model, provider)
SELECT
    'test_distractor_plausibility',
    3,
    $$あなたは読解問題の品質評価員です。

文章：
{0}

問題：
{1}

正解：
{2}

評価する誤答選択肢：
{3}

各誤答選択肢について、「もっともらしいが明らかに誤り」という観点で評価してください（0.0〜1.0）：
- 1.0 = 優良：不注意な読者をひきつけるが、文章を読めば明らかに誤り
- 0.5 = 弱い：やや説得力があるが、わかりやすすぎるか正解に近すぎる
- 0.0 = 無効：正解になり得るか、学習者が絶対に選ばないほど不合理

以下の形式のみで返してください（誤答の順番どおりに）：
{{"1": [0.9, 0.4, 0.85], "2": ["第1段落で否定されているがもっともらしい。", "明らかに誤りすぎる。", "魅力的だが最終文で否定されている。"]}}$$,
    1,
    true,
    '誤答妥当性判定（日本語）：誤答はもっともらしいが明らかに誤りか？{"1": [確信度,...], "2": [理由,...]} を返す。',
    'qwen/qwen-2.5-72b-instruct',
    'openrouter'
WHERE NOT EXISTS (
    SELECT 1 FROM public.prompt_templates
    WHERE task_name = 'test_distractor_plausibility' AND language_id = 3 AND version = 1
);

COMMIT;
