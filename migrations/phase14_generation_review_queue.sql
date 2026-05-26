-- ============================================================================
-- Phase 14 — Generation Quality — generation_review_queue table
-- Date: 2026-05-26
--
-- Centralized review queue for human-in-the-loop triage of LLM-generated
-- artifacts that land in the flag tier (judge confidence 0.6–0.8).
--
-- Populated by:
--   * LLM judges (answer_entailment, distractor_plausibility) — Wave 2
--   * Cross-corpus dedup (pg_trgm stem match / sentence dedup) — later waves
--   * Selection-rate flagger (distractors picked >35%) — Phase 3
--
-- Artifact kinds: test_question | exercise
-- Status lifecycle: pending → approved | rejected | edited
--
-- The admin UI to drain the queue is deferred to a later wave.
-- Until then, ops teams inspect via SQL, e.g.:
--   SELECT flag_reasons, COUNT(*) FROM generation_review_queue
--   WHERE status = 'pending' GROUP BY 1;
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.generation_review_queue (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_kind text        NOT NULL,
    artifact_id   uuid        NOT NULL,
    flag_reasons  text[]      NOT NULL DEFAULT '{}',
    judge_scores  jsonb,
    status        text        NOT NULL DEFAULT 'pending',
    reviewer_id   uuid,
    reviewed_at   timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT chk_artifact_kind CHECK (artifact_kind IN ('test_question', 'exercise')),
    CONSTRAINT chk_status        CHECK (status IN ('pending', 'approved', 'rejected', 'edited'))
);

COMMENT ON TABLE public.generation_review_queue IS
    'Human-in-the-loop review queue for LLM-generated artifacts flagged by '
    'judges (confidence 0.6–0.8), cross-corpus dedup, or selection-rate '
    'monitoring. One row per flagged event; rows are append-only until '
    'reviewed. Admin UI ships in a later wave.';

COMMENT ON COLUMN public.generation_review_queue.artifact_kind IS
    'Discriminator for the artifact table: test_question | exercise. '
    'No hard FK because the target table varies by kind.';
COMMENT ON COLUMN public.generation_review_queue.artifact_id IS
    'PK of the flagged artifact in its own table. '
    'For test_question: questions table id. '
    'For exercise: exercises.id.';
COMMENT ON COLUMN public.generation_review_queue.flag_reasons IS
    'Machine-readable reason codes, e.g. answer_entailment_low, '
    'distractor_plausibility_low, stem_dedup, sentence_dedup, '
    'selection_rate_high.';
COMMENT ON COLUMN public.generation_review_queue.judge_scores IS
    'Per-judge confidence vector, e.g. '
    '{"answer_entailment": 0.72, "distractor_plausibility": [0.9, 0.65, 0.88]}. '
    'Populated at insert time; aids the reviewer in understanding the flag.';
COMMENT ON COLUMN public.generation_review_queue.status IS
    'pending: awaiting reviewer action. '
    'approved: reviewer approved; source artifact is_published flipped true. '
    'rejected: reviewer rejected; source artifact hidden or deleted. '
    'edited: reviewer edited inline and then approved.';
COMMENT ON COLUMN public.generation_review_queue.reviewer_id IS
    'auth.users.id of the reviewer who closed this item. NULL while pending.';

-- ---------------------------------------------------------------------------
-- Indexes — tuned for the queue drain query (inbox view) and flag monitoring.
-- ---------------------------------------------------------------------------

-- Primary inbox view: pending items by kind, newest-first
CREATE INDEX IF NOT EXISTS idx_review_queue_status_kind_created
    ON public.generation_review_queue (status, artifact_kind, created_at DESC);

-- Fast lookup: "which queue rows exist for this artifact?"
CREATE INDEX IF NOT EXISTS idx_review_queue_artifact_pending
    ON public.generation_review_queue (artifact_id)
    WHERE status = 'pending';

COMMIT;
