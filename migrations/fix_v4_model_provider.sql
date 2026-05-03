-- ============================================================================
-- Backfill model + provider on vocab_prompt1_core v4
-- Date: 2026-05-03
--
-- restrict_l5_and_lock_l8_sentence.sql inserted v4 without populating the
-- model/provider columns, so prompt_service.get_template_config raises:
--   "prompt_templates row for 'vocab_prompt1_core'/lang=2 v4 has no model
--    configured."
--
-- Match the model+provider that v3 was running with so the swap is
-- behaviorally identical from the LLM-call side. Idempotent: only updates
-- when the columns are still NULL.
--
-- (Note: the model/provider columns are not defined in any tracked
-- migration in this repo — they were added directly in Supabase. Future
-- prompt-template inserts must remember to set them.)
-- ============================================================================

UPDATE public.prompt_templates
SET model = 'google/gemini-2.5-flash-lite',
    provider = 'openrouter'
WHERE task_name = 'vocab_prompt1_core'
  AND language_id = 2
  AND version = 4
  AND (model IS NULL OR provider IS NULL);

-- Verification (run manually):
-- SELECT version, is_active, model, provider
-- FROM public.prompt_templates
-- WHERE task_name = 'vocab_prompt1_core' AND language_id = 2
-- ORDER BY version;
