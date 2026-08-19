-- Add an explicit "JSON" token to the zh + ja test_answer_entailment prompts.
--
-- WHY
-- ---
-- services/exercise_generation/judges/answer_entailment.py:79 calls the judge
-- with response_format='json_object'. services/llm_service.py:_make_one_call
-- forwards that as payload['response_format'] = {'type': 'json_object'} — and
-- several OpenRouter upstreams (Alibaba-hosted Qwen3.x, ByteDance Seed) hard
-- reject that request unless the literal token "json" appears somewhere in the
-- messages:
--
--   400 invalid_parameter_error: 'messages' must contain the word 'json' in
--   some form, to use 'response_format' of type 'json_object'
--
-- The EN template (id 149) says "valid JSON" and passes everywhere. The ZH
-- template said only 仅以如下格式返回 and the JA template only
-- 以下の形式のみで返してください — neither contains the token.
--
-- When that 400 fires it lands in answer_entailment.py's except branch, which
-- returns safe_accept() — confidence == THRESHOLD_ACCEPT. The judge therefore
-- degrades to a 100%-accept no-op while every dashboard still shows it running
-- and healthy. The nightly slug-health probe cannot catch it either: the model
-- resolves fine, only JSON mode fails.
--
-- MEASURED 2026-08-17 (raw templates, exactly what production sends today):
--
--   model                          zh    en    ja
--   qwen/qwen3.7-flash             400   ok    400
--   bytedance-seed/seed-2.0-mini   400   ok    400
--   deepseek/deepseek-v4-flash     ok    ok    ok
--   z-ai/glm-4.7-flash             ok    ok    ok
--   inclusionai/ling-3.0-flash     ok    ok    ok
--   deepseek/deepseek-chat  (live zh) ok
--   qwen/qwen-2.5-72b-instruct (live ja)     ok
--
-- So the current live routing does NOT 400 — the defect is latent, not active.
-- It arms itself the instant zh or ja is pointed at a Qwen3.x or Seed slug,
-- which is exactly what the entailment A/B is evaluating. This migration is a
-- hard prerequisite for promoting either of those families to zh/ja.
--
-- SCOPE
-- -----
-- Only test_answer_entailment is exposed. Audited all 161 active
-- prompt_templates rows on 2026-08-17: 20 lack a "json" token, but every other
-- one is called with response_format='json' or 'text', neither of which sets
-- the API parameter, so none of them can trigger this 400:
--   * dual_translation_tier1/2/3 — routing rows only; the prompt text lives in
--     services/dual_translation/prompts.py and is sent via
--     services/model_arena/llm_runner.call_model_with_usage, which sets no
--     response_format at all.
--   * prose_generation zh/ja — response_format='text'
--     (services/test_generation/agents/prose_writer.py:109).
--   * mystery_scene, title_generation, gatekeeper_check — not json_object.
-- No other judge is affected: the only two judges using json_object are
-- answer_entailment and distractor_plausibility, and the latter's templates
-- already contain the token.
--
-- The appended text is byte-identical to JSON_TOKEN_SUFFIX in
-- scripts/measure_entailment_ab.py, so what the A/B measured is what ships.
--
-- The suffix deliberately contains no { } characters: template_text is consumed
-- with str.format(passage, question, candidate) and any unescaped brace would
-- raise at format time.

BEGIN;

UPDATE prompt_templates
SET template_text = template_text || E'\n\n请仅输出 JSON。',
    version       = version + 1
WHERE task_name  = 'test_answer_entailment'
  AND language_id = 1
  AND is_active   = TRUE
  AND position('json' in lower(template_text)) = 0;

UPDATE prompt_templates
SET template_text = template_text || E'\n\nJSON のみを出力してください。',
    version       = version + 1
WHERE task_name  = 'test_answer_entailment'
  AND language_id = 3
  AND is_active   = TRUE
  AND position('json' in lower(template_text)) = 0;

-- Fail loudly rather than committing a half-applied fix.
DO $$
DECLARE
    missing INT;
BEGIN
    SELECT count(*) INTO missing
    FROM prompt_templates
    WHERE task_name = 'test_answer_entailment'
      AND is_active = TRUE
      AND position('json' in lower(template_text)) = 0;

    IF missing > 0 THEN
        RAISE EXCEPTION
            'test_answer_entailment still has % active row(s) without a json token',
            missing;
    END IF;
END $$;

COMMIT;

-- Verification (expect json_token = true for all three languages):
--
-- SELECT id, language_id, model, version,
--        position('json' in lower(template_text)) > 0 AS json_token
-- FROM prompt_templates
-- WHERE task_name = 'test_answer_entailment' AND is_active = TRUE
-- ORDER BY language_id;
