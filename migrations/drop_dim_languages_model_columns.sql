-- ============================================================================
-- Drop redundant model columns from dim_languages and the dead
-- language_model_config table.
-- Date: 2026-05-04
--
-- Apply only AFTER:
--   1. promote_prompt_templates_model_columns.sql has been applied (so
--      every active prompt_templates row has model + provider populated).
--   2. The accompanying code refactor has been deployed: every reader of
--      dim_languages.*_model has been switched to read prompt_templates.model
--      via services.prompt_service.get_template_config. Sites that were
--      migrated:
--        - services/conversation_generation/database_client.py::get_conversation_model
--        - services/mystery_generation/orchestrator.py (per-task lookups)
--        - services/exercise_generation/orchestrator.py::_load_models
--        - services/test_generation/database_client.py::_resolve_models (used
--          by both get_language_config and get_language_config_by_code)
--        - services/vocabulary/pipeline.py (phrase detection model)
--      Scripts and orchestrators that read lang_config.prose_model /
--      .question_model still work transparently because LanguageConfig now
--      sources those fields from prompt_templates.
--
-- This migration permanently removes the redundant columns. Reapplying it
-- against a database that has already had them dropped is a no-op
-- (`IF EXISTS` clauses).
--
-- The dead `language_model_config` table (created by phase4_schema_evolution.sql
-- as a one-time copy of these columns but never read by any application code)
-- is dropped at the same time.
-- ============================================================================

BEGIN;

ALTER TABLE public.dim_languages
  DROP COLUMN IF EXISTS prose_model,
  DROP COLUMN IF EXISTS question_model,
  DROP COLUMN IF EXISTS exercise_model,
  DROP COLUMN IF EXISTS exercise_sentence_model,
  DROP COLUMN IF EXISTS conversation_model,
  DROP COLUMN IF EXISTS vocab_prompt1_model,
  DROP COLUMN IF EXISTS vocab_prompt2_model,
  DROP COLUMN IF EXISTS vocab_prompt3_model;

DROP TABLE IF EXISTS public.language_model_config;

-- Verification (run manually):
-- \d public.dim_languages   -- confirm none of the eight *_model columns appear
-- \d public.language_model_config  -- should error: relation does not exist

COMMIT;
