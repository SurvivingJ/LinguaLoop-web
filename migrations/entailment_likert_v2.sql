-- Answer-entailment judge -> 1-5 Likert (TASK-723), zh/en/ja.
--
-- WHY: `llm_calls.judge_confidence` is one `real` column holding two scales that
-- INVERT. `judge_answer_entailment` and `cloze_distractor_judge` wrote a 0.0-1.0
-- probability classified by judges/base.py:classify (>=0.8 accept, >=0.6 flag,
-- else reject); `judge_distractor_plausibility` and the `judge_ladder_*` family
-- write a 1-5 Likert mapped by schemas.likert_to_verdict (5/4 accept, 3 flag,
-- 2/1 reject). A stored 1.0 therefore means "maximum confidence, accept" on one
-- scale and "worst rating, reject" on the other. Nothing in the codebase could
-- tell them apart, which is why migrations/null_legacy_judge_confidence.sql had
-- to erase 888 rows outright rather than reinterpret them.
--
-- Entailment converts first because it is the easy case: "does the passage
-- support this answer" is naturally ONE axis, so its bands can be made mutually
-- exclusive without the two-axis redesign TASK-719 owes the distractor judge.
-- `cloze_distractor_judge` is deliberately NOT converted here -- it has the same
-- topical-distance-vs-confusability conflation, and cloning today's bands would
-- bake that in. It waits for TASK-719.
--
-- THE BANDS are a single axis (strength of textual support) and are mutually
-- exclusive rather than separated by degree -- the property TASK-723 requires
-- and the current distractor bands lack:
--   5  stated explicitly; a sentence can be pointed at
--   4  not stated, but the only conclusion the passage's information allows
--   3  partly supported, but the passage equally permits a different answer
--   2  unsupported; merely on the same topic
--   1  contradicted by the passage, or unrelated to it
-- Note 4 vs 3 is uniqueness (sole conclusion vs one of several), not strength,
-- and 2 vs 1 is absence-of-support vs active contradiction. No band is
-- reachable by "a bit less than" its neighbour.
--
-- SHAPE is unchanged: numeric keys, so the ZH/JA bodies stay free of English
-- field names -- {"1": <rating>, "2": "<reason>"}. Only the meaning of key "1"
-- changes, from a float to an integer, which is exactly what
-- schemas.AnswerEntailmentVerdict._reject_legacy_float_scale detects: if this
-- migration is NOT applied but the v2 code is deployed, the judge raises rather
-- than rounding 0.85 to 1 and inverting every verdict.
--
-- MODELS ARE DELIBERATELY UNCHANGED. wiki/evaluations/entailment-judge-model-ab-
-- 2026-08-17.md recommends promoting zh+ja to deepseek/deepseek-v4-flash and en
-- to inclusionai/ling-3.0-flash. That promotion is a SEPARATE change: its AUC
-- numbers were measured on the 0.0-1.0 scale, and moving the scale and the model
-- in one step makes the re-measurement uninterpretable -- the same discipline
-- TASK-717 applied when it froze the model during the prompt A/B. Convert the
-- scale, re-measure on the gold set, then promote.
--
-- ############################################################################
-- v2 ROWS LAND **INACTIVE**. THIS MIGRATION DOES NOT CHANGE LIVE BEHAVIOUR.
-- ############################################################################
--
-- The prompt and the code are COUPLED and must cut over together. Activating v2
-- while the deployed code still expects a float would make every entailment call
-- fail schema validation, fall into the judge's except branch, and return
-- safe_accept() -- i.e. the answer-hallucination guard would silently become a
-- no-op across all three languages, which is precisely the class of silent
-- outage TASK-510's batch mode exists to prevent. The reverse order is caught
-- loudly by _reject_legacy_float_scale, but this order is not, because a v1
-- float is a *valid* input to v1 code.
--
-- CUTOVER, in this order:
--   1. apply this migration          (v2 rows exist, inactive; nothing changes)
--   2. measure v3 on the gold set    (scripts/measure_entailment_ab.py
--                                     --template-version 3)
--   3. deploy the new code           (schemas.py, answer_entailment.py)
--   4. activate:
--        UPDATE prompt_templates SET is_active = (version = 3), updated_at = now()
--         WHERE task_name = 'test_answer_entailment';
--
-- Reversible at step 4:
--        UPDATE prompt_templates
--           SET is_active = (version = CASE language_id WHEN 2 THEN 1 ELSE 2 END)
--         WHERE task_name = 'test_answer_entailment';
--
-- ############################################################################
-- VERSION NUMBERS ARE NOT ALIGNED ACROSS LANGUAGES ON THIS TASK. READ THIS.
-- ############################################################################
--
-- Before this migration the live rows were: en v1, zh v2, ja v2 -- NOT v1
-- everywhere. `migrations/entailment_json_token_zh_ja.sql` appended the "json"
-- token to zh and ja with `SET ... version = version + 1`, an in-place UPDATE,
-- so those two rows *became* v2 and no v1 row survives for them.
--
-- Writing these Likert rows at version 2 therefore does NOT create new rows: it
-- collides with the live zh/ja rows on (task_name, language_id, version) and the
-- ON CONFLICT branch overwrites them. Doing that during this task destroyed both
-- live templates and deactivated them, leaving zh and ja with no active
-- entailment row -- i.e. get_template_config raises, the judge safe_accepts, and
-- the answer-hallucination guard is silently off for two of three languages.
-- Recovered from phase14_judge_prompt_seeds.sql plus the suffix above, verified
-- by restored lengths 208 (zh) and 267 (ja).
--
-- Hence v3 for all three languages: it is free on every language and it realigns
-- the numbering so the step-4 activation is a single predicate. Always SELECT
-- the existing versions for a task before choosing a version number.

BEGIN;

-- zh (language_id=1)
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'test_answer_entailment', 1, 3, FALSE,
    'deepseek/deepseek-chat', 'openrouter',
    '你是一位阅读理解题目质量评判员。

文章：
{0}

题目：
{1}

候选正确答案：
{2}

请判断文章对该候选答案的支持强度，从 1 到 5 中选择一个整数。

只评判一个维度：文章对该答案的支持强度。不要评判题目写得好不好、难不难、有没有意思。

5 = 文章明确写出了该答案，可以指出具体语句。
4 = 文章没有直接写出，但根据文中信息只能得出该答案。
3 = 文章提供了部分依据，但同样允许另一个不同的答案，该答案并非唯一。
2 = 文章没有提供依据，该答案只是与文章主题相关。
1 = 文章与该答案矛盾，或该答案与文章内容无关。

选择描述完全成立的最高等级。若在两个等级之间犹豫，取较低的一个。

仅返回如下格式的 JSON，其中键 "1" 是 1 到 5 的整数评级，键 "2" 是理由：
{{"1": 4, "2": "文章第二段写道……"}}

请仅输出 JSON，不要使用代码块。',
    'v2 (TASK-723): 1-5 Likert on a single support-strength axis, replacing the 0.0-1.0 confidence. Bands are mutually exclusive (4 vs 3 is uniqueness, 2 vs 1 is absence vs contradiction).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = FALSE,   -- see the cutover note at the top
       description   = EXCLUDED.description,
       updated_at    = now();

-- en (language_id=2)
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'test_answer_entailment', 2, 3, FALSE,
    'google/gemini-3.5-flash-lite', 'openrouter',
    'You are a reading comprehension quality judge.

Passage:
{0}

Question:
{1}

Proposed correct answer:
{2}

How strongly does the passage support the proposed answer? Choose one integer from 1 to 5.

Rate ONE thing only: the strength of textual support. Do not rate how well written, how difficult, or how interesting the question is.

5 = The passage states the answer explicitly. You can point to the sentence.
4 = The passage does not state it, but it is the only conclusion the passage''s information allows.
3 = The passage partly supports it, but equally permits a different answer. The answer is not uniquely determined.
2 = The passage does not support it. The answer is merely on the same topic.
1 = The passage contradicts the answer, or the answer is unrelated to the passage.

Choose the highest rating whose description is fully true. If you are between two ratings, choose the lower one.

Respond ONLY with JSON in exactly this format, where key "1" is the integer rating 1-5 and key "2" is your reason:
{{"1": 4, "2": "Paragraph 2 states that ..."}}

Return JSON only, with no code block.',
    'v2 (TASK-723): 1-5 Likert on a single support-strength axis, replacing the 0.0-1.0 confidence. Bands are mutually exclusive (4 vs 3 is uniqueness, 2 vs 1 is absence vs contradiction).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = FALSE,   -- see the cutover note at the top
       description   = EXCLUDED.description,
       updated_at    = now();

-- ja (language_id=3)
INSERT INTO prompt_templates
    (task_name, language_id, version, is_active, model, provider,
     template_text, description)
VALUES (
    'test_answer_entailment', 3, 3, FALSE,
    'qwen/qwen-2.5-72b-instruct', 'openrouter',
    'あなたは読解問題の品質評価者です。

文章：
{0}

設問：
{1}

正解候補：
{2}

文章がこの正解候補をどの程度裏づけているか、1から5までの整数で1つ選んでください。

評価する軸は1つだけです。文章による裏づけの強さのみを評価し、設問の出来・難易度・面白さは評価しないでください。

5 = 文章に明記されている。該当する一文を指し示せる。
4 = 明記はされていないが、文章の情報から導ける結論はこれ以外にない。
3 = 部分的には裏づけられるが、別の答えも同じように成り立つ。答えが一つに定まらない。
2 = 文章は裏づけていない。話題が同じというだけである。
1 = 文章がこの答えと矛盾する、または答えが文章と無関係である。

説明が完全に当てはまる最も高い評価を選んでください。二つの評価で迷う場合は低いほうを選んでください。

次の形式のJSONのみを返してください。キー "1" は1から5の整数評価、キー "2" は理由です：
{{"1": 4, "2": "第2段落に……と書かれている"}}

JSONのみを出力し、コードブロックは使わないでください。',
    'v2 (TASK-723): 1-5 Likert on a single support-strength axis, replacing the 0.0-1.0 confidence. Bands are mutually exclusive (4 vs 3 is uniqueness, 2 vs 1 is absence vs contradiction).'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET template_text = EXCLUDED.template_text,
       model         = EXCLUDED.model,
       provider      = EXCLUDED.provider,
       is_active     = FALSE,   -- see the cutover note at the top
       description   = EXCLUDED.description,
       updated_at    = now();

COMMIT;
