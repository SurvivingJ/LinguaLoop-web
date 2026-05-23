-- ============================================================================
-- Phase 14 — Generation Quality — llm_calls observability table
-- Date: 2026-05-23
--
-- One row per LLM call across every pipeline (test gen, vocab ladder, corpus,
-- conversation gen, mystery, etc.). Wired from services/llm_service.py so
-- every call site logs automatically.
--
-- Purpose:
--   * Per-task parse / schema success rates → catch regressions on prompt
--     edits or model swaps.
--   * Per-task latency + cost rollups for spend monitoring.
--   * Judge verdict distribution per task → tune confidence thresholds.
--   * Link rows to the artifact they produced (exercise_id, test_id, etc.)
--     so quality outcomes can be traced back to the call that made them.
--
-- See wiki/features/llm-infrastructure-improvements.tech.md (forthcoming).
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.llm_calls (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline         text        NOT NULL,
    task_name        text        NOT NULL,
    template_version integer,
    model            text        NOT NULL,
    temperature      real,
    seed             integer,
    prompt_hash      bytea,
    raw_response     text,
    parsed_ok        boolean,
    schema_ok        boolean,
    judge_verdict    text,
    judge_confidence real,
    latency_ms       integer,
    cost_usd         numeric(10,6),
    artifact_id      uuid,
    created_at       timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.llm_calls IS
    'Observability table for every LLM call across every pipeline. Wired '
    'automatically from services.llm_service.call_llm. One row per call; '
    'rows are append-only and intended for analytics, not for retry logic.';

COMMENT ON COLUMN public.llm_calls.pipeline IS
    'Which pipeline issued the call: test_gen, vocab_ladder, corpus, '
    'conversation_gen, mystery, topic_gen, etc. Free-text but conventionally '
    'snake_case.';
COMMENT ON COLUMN public.llm_calls.task_name IS
    'Specific task within the pipeline. Matches prompt_templates.task_name '
    'when the call uses a templated prompt (e.g. test_question_generator, '
    'vocab_prompt2_exercises, cloze_distractor_judge).';
COMMENT ON COLUMN public.llm_calls.template_version IS
    'Active version of prompt_templates row used for this call, when '
    'applicable.';
COMMENT ON COLUMN public.llm_calls.prompt_hash IS
    'SHA-256 of the rendered prompt content. Lets repeated identical prompts '
    'be grouped without storing full prompt text.';
COMMENT ON COLUMN public.llm_calls.raw_response IS
    'Full text returned by the model before any cleaning or parsing. May be '
    'large; safe to truncate or null out in long-term archival.';
COMMENT ON COLUMN public.llm_calls.parsed_ok IS
    'True if the response cleaner + json.loads succeeded.';
COMMENT ON COLUMN public.llm_calls.schema_ok IS
    'True if Pydantic schema validation succeeded (including after a repair '
    'retry). NULL when no schema was supplied.';
COMMENT ON COLUMN public.llm_calls.judge_verdict IS
    'For judge calls only: accept | flag | reject | error. NULL otherwise.';
COMMENT ON COLUMN public.llm_calls.judge_confidence IS
    'For judge calls only: confidence value reported by the judge (0.0-1.0).';
COMMENT ON COLUMN public.llm_calls.artifact_id IS
    'Pipeline-dependent foreign reference: exercises.id for vocab ladder, '
    'tests.id for test gen, etc. Not a hard FK because the target table '
    'varies by pipeline.';

-- ---------------------------------------------------------------------------
-- Indexes — tuned for the dashboard queries the plan calls out:
--   * Per-task success rate over time
--   * Recent parse / schema failures across all tasks
--   * Lookups by artifact (which calls produced this exercise?)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_llm_calls_task_created
    ON public.llm_calls (task_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_calls_parsed_schema_created
    ON public.llm_calls (parsed_ok, schema_ok, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_calls_pipeline_created
    ON public.llm_calls (pipeline, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_calls_artifact
    ON public.llm_calls (artifact_id)
    WHERE artifact_id IS NOT NULL;

COMMIT;
