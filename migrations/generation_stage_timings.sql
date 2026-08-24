-- ============================================================================
-- generation_stage_timings — wall-clock stage observability
-- Date: 2026-08-23
--
-- services/timing.py's `stage()` context manager has been timing pipeline
-- stages (prose, questions, audio, vocab_senses_llm, p1_generate, p1_judge,
-- ...) since TASK-737, but only ever logged the resulting dict to stdout —
-- never persisted, never split by language. llm_calls (phase14_llm_calls.sql)
-- covers the LLM-round-trip portion of that time; this table covers the rest
-- of the wall clock a stage spans (DB writes, audio synthesis, tokenization,
-- non-LLM validation, etc.) so the two together answer "where did the wall
-- clock go" completely, not just "where did the LLM spend go".
--
-- One row per (stage, artifact) — NOT one row per LLM call inside that stage;
-- llm_calls already has call-level granularity. A stage's duration_ms may
-- therefore overlap with the sum of the llm_calls rows made during it — do
-- not add the two totals together (see scripts/generation_timing_report.py).
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.generation_stage_timings (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline      text        NOT NULL,
    stage_name    text        NOT NULL,
    language_code text,
    artifact_id   uuid,
    run_id        uuid,
    duration_ms   integer     NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.generation_stage_timings IS
    'Wall-clock duration of one named pipeline stage for one artifact. '
    'Written best-effort from services.timing.log_stage_seconds at the end '
    'of a test/sense/asset build, once per stage name — not per LLM call '
    '(see services.llm_service / llm_calls for call-level timing). '
    'Append-only, for analytics via scripts/generation_timing_report.py.';

COMMENT ON COLUMN public.generation_stage_timings.pipeline IS
    'Which pipeline: test_gen, vocab_ladder, vocab_senses, vocab_glosses.';
COMMENT ON COLUMN public.generation_stage_timings.stage_name IS
    'Stage label as passed to services.timing.stage(), e.g. prose, '
    'questions, audio, vocab_senses_llm, p1_generate, p1_judge.';
COMMENT ON COLUMN public.generation_stage_timings.language_code IS
    'Study-language code (zh | en | ja) the artifact was generated in. '
    'Free-text, not an FK — same convention as llm_calls.language_code.';
COMMENT ON COLUMN public.generation_stage_timings.artifact_id IS
    'Pipeline-dependent reference: tests.id for test_gen, '
    'dim_word_senses.id for vocab_ladder/vocab_senses. Not a hard FK — '
    'the target table varies by pipeline (same convention as llm_calls).';
COMMENT ON COLUMN public.generation_stage_timings.run_id IS
    'Groups every stage row from one batch invocation (one '
    'orchestrator.run()/run_batch() call, one asset_pipeline batch_id) so a '
    'whole run''s wall clock can be summed without a time-window guess.';

CREATE INDEX IF NOT EXISTS idx_gen_stage_timings_pipeline_stage_created
    ON public.generation_stage_timings (pipeline, stage_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_gen_stage_timings_language
    ON public.generation_stage_timings (language_code)
    WHERE language_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_gen_stage_timings_run
    ON public.generation_stage_timings (run_id)
    WHERE run_id IS NOT NULL;

COMMIT;
