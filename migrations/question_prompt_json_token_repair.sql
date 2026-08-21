-- Restore the literal `JSON` token to four live question_* rows.
-- Date: 2026-08-19
-- Applied live by scripts/apply_json_token_repair.py (there is no psql here);
-- this file is the reviewable record and is byte-for-byte re-derivable.
--
-- THE OUTAGE
-- ----------
-- These four active rows contained no case-insensitive `json` token:
--
--   question_vocabulary_context [zh] v2 -> v3
--   question_vocabulary_context [ja] v2 -> v3
--   question_main_idea          [ja] v2 -> v3
--   question_author_purpose     [ja] v2 -> v3
--
-- All four are TASK-722 / TASK-724 native rewrites and all four lost the token
-- to migrations/zh_ja_prompt_metalanguage_sweep.sql. All four run on
-- `qwen/qwen3.7-plus`, which OpenRouter routes to Alibaba, and Alibaba refuses
-- `response_format=json_object` unless the prompt contains the word:
--
--   400 invalid_parameter_error: 'messages' must contain the word 'json' in
--   some form, to use 'response_format' of type 'json_object'
--
-- services/test_generation/agents/question_generator.py always passes
-- response_format='json_object', so EVERY generation attempt for these four
-- (question type x language) pairs failed. Measured 2026-08-19: 4 of 4 such
-- cells failed in an 18-cell pilot; with the token restored, 179 of 180 cells
-- succeeded across a 3-language run.
--
-- The 2026-08-17 note recorded this failure mode as LATENT and specific to
-- test_answer_entailment. It is neither: it was live, and it was in the
-- generators.
--
-- WHY THIS IS NOT A REVERSION OF TASK-724
-- ---------------------------------------
-- `JSON` here is machine contract, not English leakage -- the same category
-- scripts/rewrite_prompt_native.py already whitelists in `allowed_latin`
-- alongside the JSON key names and the question_type enum. The sweep was right
-- about "markdown" and "schema" and wrong about this one token. Nothing else
-- changes: one word, inserted into each row's existing output sentence.
--
-- VERSION NUMBERS: all four incumbents were at v2, so all four targets are v3.
-- Derived, not assumed -- see the max(version) read in the apply script.
--
-- IDEMPOTENT: replace() over already-substituted text is a no-op, and the
-- source rows are DEACTIVATED rather than modified, so v3 stays re-derivable.

BEGIN;

-- question_vocabulary_context [zh] v2 -> v3   md5 393955fe65e00688fc8ca981db9ca96c
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider, template_text,
   description)
SELECT task_name, language_id, 3, true, model, provider,
       replace(template_text, '最终只输出一个对象，', '最终只输出一个 JSON 对象，'),
       'v3: restores the literal JSON token lost to the TASK-724 metalanguage '
       'sweep. Without it Alibaba 400s every response_format=json_object call '
       'and this row cannot generate at all. Body = v2 verbatim + one word.'
  FROM public.prompt_templates
 WHERE task_name = 'question_vocabulary_context' AND language_id = 1 AND version = 2
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active = EXCLUDED.is_active, template_text = EXCLUDED.template_text,
       description = EXCLUDED.description, updated_at = now();

-- question_vocabulary_context [ja] v2 -> v3   md5 864a0571b103df4a4a9d41d9ce76d0fb
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider, template_text,
   description)
SELECT task_name, language_id, 3, true, model, provider,
       replace(template_text,
               '出力は、次のオブジェクトのみとすること。',
               '出力は、次の JSON オブジェクトのみとすること。'),
       'v3: restores the literal JSON token lost to the TASK-724 metalanguage '
       'sweep. Without it Alibaba 400s every response_format=json_object call '
       'and this row cannot generate at all. Body = v2 verbatim + one word.'
  FROM public.prompt_templates
 WHERE task_name = 'question_vocabulary_context' AND language_id = 3 AND version = 2
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active = EXCLUDED.is_active, template_text = EXCLUDED.template_text,
       description = EXCLUDED.description, updated_at = now();

-- question_main_idea [ja] v2 -> v3            md5 f9cbe9f1d9b76a690a40ebe563406b57
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider, template_text,
   description)
SELECT task_name, language_id, 3, true, model, provider,
       replace(template_text,
               '次のオブジェクトだけを出力すること。',
               '次の JSON オブジェクトだけを出力すること。'),
       'v3: restores the literal JSON token lost to the TASK-724 metalanguage '
       'sweep. Without it Alibaba 400s every response_format=json_object call '
       'and this row cannot generate at all. Body = v2 verbatim + one word.'
  FROM public.prompt_templates
 WHERE task_name = 'question_main_idea' AND language_id = 3 AND version = 2
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active = EXCLUDED.is_active, template_text = EXCLUDED.template_text,
       description = EXCLUDED.description, updated_at = now();

-- question_author_purpose [ja] v2 -> v3       md5 35301e017625a38d1bfd119e6edafcb8
INSERT INTO public.prompt_templates
  (task_name, language_id, version, is_active, model, provider, template_text,
   description)
SELECT task_name, language_id, 3, true, model, provider,
       replace(template_text,
               '最終的な出力は、次の形式のみとしてください。',
               '最終的な出力は、次の JSON 形式のみとしてください。'),
       'v3: restores the literal JSON token lost to the TASK-724 metalanguage '
       'sweep. Without it Alibaba 400s every response_format=json_object call '
       'and this row cannot generate at all. Body = v2 verbatim + one word.'
  FROM public.prompt_templates
 WHERE task_name = 'question_author_purpose' AND language_id = 3 AND version = 2
ON CONFLICT (task_name, language_id, version) DO UPDATE
   SET is_active = EXCLUDED.is_active, template_text = EXCLUDED.template_text,
       description = EXCLUDED.description, updated_at = now();

-- Retire the incumbents. Exactly one active row per (task_name, language_id)
-- must survive -- zero makes get_template_config raise and kills generation for
-- that question type outright.
UPDATE public.prompt_templates SET is_active = false, updated_at = now()
 WHERE version <> 3
   AND ((task_name = 'question_vocabulary_context' AND language_id IN (1, 3))
     OR (task_name = 'question_main_idea'          AND language_id = 3)
     OR (task_name = 'question_author_purpose'     AND language_id = 3));

COMMIT;

-- Verification (run manually):
-- SELECT task_name, language_id, version, is_active,
--        template_text ILIKE '%json%' AS has_json_token
--   FROM public.prompt_templates
--  WHERE task_name LIKE 'question\_%' AND is_active
--  ORDER BY task_name, language_id;
-- Expect has_json_token = true for all 18.
