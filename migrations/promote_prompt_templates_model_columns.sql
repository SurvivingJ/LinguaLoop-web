-- ============================================================================
-- Promote prompt_templates.model + .provider to first-class tracked columns
-- and backfill them on every active row.
-- Date: 2026-05-03
--
-- Today the model/provider columns exist in Supabase (added directly via the
-- dashboard) but are not tracked in any source migration. Several rows have
-- NULL values, which causes services/prompt_service.get_template_config to
-- raise at runtime. This migration formalises the schema and backfills all
-- active rows so prompt_templates becomes the single source of truth for
-- "which model handles this task". The follow-up migration
-- drop_dim_languages_model_columns.sql removes the now-redundant columns
-- from dim_languages once code paths have been migrated.
--
-- Backfill mapping is documented in the wiki (features/exercise-generation-
-- prompts.md) and was derived from dim_languages._model column seed values.
-- Mystery tasks were assigned per a product decision: plot/scene get Sonnet
-- (creative writing), question/clue/deduction get Flash Lite (structural).
--
-- Idempotent: every UPDATE has a `WHERE model IS NULL OR provider IS NULL`
-- guard so re-running the migration after manual edits is a no-op.
-- ============================================================================

BEGIN;

-- ──────────────────────────────────────────────────────────────────────────
-- 1. Schema: add columns formally if not already present
-- ──────────────────────────────────────────────────────────────────────────

ALTER TABLE public.prompt_templates
  ADD COLUMN IF NOT EXISTS model    text,
  ADD COLUMN IF NOT EXISTS provider text DEFAULT 'openrouter';

-- ──────────────────────────────────────────────────────────────────────────
-- 2. Backfill — Vocab ladder pipeline (English only — CN/JP rows missing)
-- ──────────────────────────────────────────────────────────────────────────

UPDATE public.prompt_templates
SET model = 'google/gemini-2.5-flash-lite', provider = 'openrouter'
WHERE task_name = 'vocab_prompt1_core'
  AND is_active = true
  AND (model IS NULL OR provider IS NULL);

UPDATE public.prompt_templates
SET model = 'anthropic/claude-sonnet-4-6', provider = 'openrouter'
WHERE task_name IN ('vocab_prompt2_exercises', 'vocab_prompt3_transforms')
  AND is_active = true
  AND (model IS NULL OR provider IS NULL);

-- ──────────────────────────────────────────────────────────────────────────
-- 3. Backfill — Test generation (prose + 6 comprehension question types)
-- ──────────────────────────────────────────────────────────────────────────

UPDATE public.prompt_templates
SET model = 'google/gemini-2.5-flash-lite', provider = 'openrouter'
WHERE task_name IN (
    'prose_generation',
    'question_literal_detail',
    'question_vocabulary_context',
    'question_main_idea',
    'question_supporting_detail',
    'question_inference',
    'question_author_purpose'
  )
  AND is_active = true
  AND (model IS NULL OR provider IS NULL);

-- ──────────────────────────────────────────────────────────────────────────
-- 4. Backfill — Conversation generation pipeline
-- ──────────────────────────────────────────────────────────────────────────

UPDATE public.prompt_templates
SET model = 'google/gemini-2.0-flash-001', provider = 'openrouter'
WHERE task_name IN (
    'conversation_generation',
    'conversation_analysis',
    'conversation_persona_design',
    'conversation_scenario_plan',
    'scenario_batch_generation'
  )
  AND is_active = true
  AND (model IS NULL OR provider IS NULL);

-- ──────────────────────────────────────────────────────────────────────────
-- 5. Backfill — Legacy exercise generation (12 task types)
-- ──────────────────────────────────────────────────────────────────────────

UPDATE public.prompt_templates
SET model = 'google/gemini-flash-1.5', provider = 'openrouter'
WHERE task_name IN (
    'exercise_sentence_generation',
    'vocab_sentence_generation',
    'collocation_sentence_generation',
    'cloze_distractor_generation',
    'tl_nl_translation_generation',
    'nl_tl_translation_generation',
    'spot_incorrect_generation',
    'semantic_discrimination_generation',
    'odd_one_out_generation',
    'collocation_gap_fill_generation',
    'collocation_repair_generation',
    'odd_collocation_out_generation'
  )
  AND is_active = true
  AND (model IS NULL OR provider IS NULL);

-- ──────────────────────────────────────────────────────────────────────────
-- 6. Backfill — Mystery generation (split per product decision)
-- ──────────────────────────────────────────────────────────────────────────

-- Creative-writing tasks → Sonnet
UPDATE public.prompt_templates
SET model = 'anthropic/claude-sonnet-4-6', provider = 'openrouter'
WHERE task_name IN ('mystery_plot', 'mystery_scene')
  AND is_active = true
  AND (model IS NULL OR provider IS NULL);

-- Structural tasks → Flash Lite
UPDATE public.prompt_templates
SET model = 'google/gemini-2.5-flash-lite', provider = 'openrouter'
WHERE task_name IN ('mystery_question', 'mystery_clue', 'mystery_deduction')
  AND is_active = true
  AND (model IS NULL OR provider IS NULL);

-- ──────────────────────────────────────────────────────────────────────────
-- 7. Backfill — Vocab phrase detection (NLP classification)
-- ──────────────────────────────────────────────────────────────────────────

UPDATE public.prompt_templates
SET model = 'google/gemini-2.5-flash-lite', provider = 'openrouter'
WHERE task_name = 'vocab_phrase_detection'
  AND is_active = true
  AND (model IS NULL OR provider IS NULL);

-- ──────────────────────────────────────────────────────────────────────────
-- 8. Verification (run manually after migration)
-- ──────────────────────────────────────────────────────────────────────────
-- SELECT task_name, language_id, version, is_active, model, provider
-- FROM public.prompt_templates
-- WHERE is_active = true
-- ORDER BY task_name, language_id;
--
-- Every active row should have non-null model + provider. Rows that the
-- code never queries (deactivated history) keep their NULLs by design.

COMMIT;
