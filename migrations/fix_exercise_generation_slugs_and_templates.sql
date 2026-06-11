-- ============================================================================
-- Exercise-generation pipeline: model-slug rot + missing/inactive templates
-- Date: 2026-06-09
--
-- Source: wiki/evaluations/exercise-pipeline-eval-2026-06-09.md (CRITICAL #1, #2).
--
-- The legacy services/exercise_generation pipeline (still live via the admin
-- "generate exercises" path and conversation_generation) was dead on arrival:
--   1. Every generation row pointed at google/gemini-flash-1.5, which is
--      404-delisted on OpenRouter (zero llm_calls in 21+ days). Same failure
--      class as the qwen/qwen-max rot, but on this pipeline.
--   2. orchestrator._load_models() fast-failed before any generation because
--      EN(2) had no exercise_sentence_generation row and ZH(1)
--      cloze_distractor_generation was inactive.
--
-- Live-probed replacement slugs (OpenRouter /models, 2026-06-09):
--   google/gemini-3.5-flash  -> LIVE   (English, language_id=2)
--   qwen/qwen3.7-plus        -> LIVE   (Chinese=1, Japanese=3)
--   google/gemini-flash-1.5  -> MISSING (confirmed delisted)
--
-- Idempotent throughout: slug sweep keys on the dead slug; inserts guard with
-- NOT EXISTS; the activate is a no-op if already active.
--
-- NOTE: prompt-text-only rows (cloze_target_selection,
-- semantic_discrimination_from_context, context_spectrum_generation) keep
-- model=NULL on purpose — they do not drive model selection (generators use the
-- shared exercise model resolved from cloze_distractor_generation). The
-- language-aware get_template_text() loader does not require model/provider.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Sweep the dead slug everywhere, language-appropriately.
-- ---------------------------------------------------------------------------
UPDATE public.prompt_templates
SET model = CASE language_id
              WHEN 2 THEN 'google/gemini-3.5-flash'   -- English
              ELSE        'qwen/qwen3.7-plus'          -- Chinese (1), Japanese (3)
            END,
    provider = 'openrouter',
    updated_at = now()
WHERE model = 'google/gemini-flash-1.5';

-- ---------------------------------------------------------------------------
-- 2. Activate the ZH(1) cloze_distractor_generation row so _load_models can
--    resolve the Chinese exercise model. (Only v1 exists for ZH.)
-- ---------------------------------------------------------------------------
UPDATE public.prompt_templates
SET is_active = true,
    updated_at = now()
WHERE task_name = 'cloze_distractor_generation'
  AND language_id = 1
  AND is_active = false;

-- ---------------------------------------------------------------------------
-- 3. Seed EN(2) exercise_sentence_generation (was entirely missing).
--    Required by _load_models for EVERY English source_type (it resolves the
--    sentence model here) and used as the grammar-source sentence prompt.
-- ---------------------------------------------------------------------------
INSERT INTO public.prompt_templates
    (task_name, language_id, version, is_active, model, provider, template_text, description)
SELECT
    'exercise_sentence_generation', 2, 1, true,
    'google/gemini-3.5-flash', 'openrouter',
    E'Generate {count} natural {complexity_tier}-level sentences in the target language that demonstrate the following:\nPattern: {pattern_code}\nDescription: {description}\nExample: {example_sentence}\n\nReturn a JSON array of objects: [{{"sentence": "...", "cefr_level": "{complexity_tier}"}}]\nDo not include translations. Sentences must be grammatically correct and contextually natural.',
    'EN grammar/sentence generation prompt; seeded 2026-06-09 to unblock _load_models (eval CRITICAL #2).'
WHERE NOT EXISTS (
    SELECT 1 FROM public.prompt_templates
    WHERE task_name = 'exercise_sentence_generation' AND language_id = 2
);

-- ---------------------------------------------------------------------------
-- 4. Seed JA(3) tl_nl / nl_tl translation prompts so Japanese learners get
--    real translation exercises (cross-language; not skipped). Cloned from the
--    ZH(1) prompts (ids 41/42), localised to Japanese, on qwen/qwen3.7-plus.
--    EN is intentionally NOT seeded: tl_nl/nl_tl are runtime-skipped when
--    target language == native language (English-target learners).
-- ---------------------------------------------------------------------------
INSERT INTO public.prompt_templates
    (task_name, language_id, version, is_active, model, provider, template_text, description)
SELECT
    'tl_nl_translation_generation', 3, 1, true,
    'qwen/qwen3.7-plus', 'openrouter',
    E'文（目標言語）：{tl_sentence}\n母語：{nl_language}\n\n生成してください：\n1. 正確な {nl_language} の翻訳を1つ。\n2. もっともらしいが誤った {nl_language} の翻訳を2つ（同じ主題、異なる時制・相・意味）。\n\nJSONで返してください：\n{{"correct_nl": "...", "wrong_options": ["...", "..."]}}\n\n正しい翻訳を最初に置いてください——順序を変えないでください。',
    'JA tl_nl translation prompt; seeded 2026-06-09 (eval HIGH #3, JA translations).'
WHERE NOT EXISTS (
    SELECT 1 FROM public.prompt_templates
    WHERE task_name = 'tl_nl_translation_generation' AND language_id = 3
);

INSERT INTO public.prompt_templates
    (task_name, language_id, version, is_active, model, provider, template_text, description)
SELECT
    'nl_tl_translation_generation', 3, 1, true,
    'qwen/qwen3.7-plus', 'openrouter',
    E'目標言語の文：{tl_sentence}\n母語（{nl_language}）に翻訳し、産出練習の採点基準を提供してください。\n\nJSONで返してください：\n{{"nl_sentence": "...", "grading_notes": "重要な要件：例えば現在完了進行形を使用する必要がある、継続期間の標識が必要。", "acceptable_variants": ["...", "..."]}}',
    'JA nl_tl translation prompt; seeded 2026-06-09 (eval HIGH #3, JA translations).'
WHERE NOT EXISTS (
    SELECT 1 FROM public.prompt_templates
    WHERE task_name = 'nl_tl_translation_generation' AND language_id = 3
);

-- ---------------------------------------------------------------------------
-- Verification (run manually):
--   SELECT task_name, language_id, version, is_active, model
--   FROM public.prompt_templates
--   WHERE task_name IN ('cloze_distractor_generation','exercise_sentence_generation',
--     'tl_nl_translation_generation','nl_tl_translation_generation',
--     'semantic_discrimination_generation','vocab_sentence_generation','odd_one_out_generation')
--   ORDER BY task_name, language_id, version;
--   -- Expect: no remaining 'google/gemini-flash-1.5'; EN/ZH active rows present.
-- ============================================================================
