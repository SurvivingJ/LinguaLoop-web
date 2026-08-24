-- ============================================================================
-- llm_calls — add language_code for per-language timing/cost breakdowns
-- Date: 2026-08-23
--
-- llm_calls (phase14_llm_calls.sql) already carries pipeline/task_name/
-- latency_ms/cost_usd per LLM round-trip, but nothing says which STUDY
-- language the call was for — so "which language is the bottleneck" could
-- only be answered by joining back to the artifact table per pipeline (and
-- not at all for calls made before the artifact row exists). Logging the
-- code directly at call time is simpler and pipeline-uniform.
--
-- Nullable and additive: existing rows and existing call_llm() callers that
-- don't pass language_code are unaffected.
-- ============================================================================

BEGIN;

ALTER TABLE public.llm_calls
    ADD COLUMN IF NOT EXISTS language_code text;

COMMENT ON COLUMN public.llm_calls.language_code IS
    'ISO-ish study-language code (zh | en | ja) the call was made for, when '
    'the caller knows it. Free-text, not an FK to dim_languages (same '
    'looseness as artifact_id) — set from services.llm_service.call_llm''s '
    'language_code kwarg. NULL for pipelines that have not been wired yet.';

CREATE INDEX IF NOT EXISTS idx_llm_calls_language_pipeline_created
    ON public.llm_calls (language_code, pipeline, task_name, created_at DESC);

COMMIT;
