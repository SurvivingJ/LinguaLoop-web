-- generation_queue — async work queue for the vocabulary-ladder generation pipeline.
-- Source of truth: wiki/features/exercise-generation-v2.md §6.5 (DDL verbatim).
-- TASK-511 (Exercise Generation v2, Phase 0).
--
-- Per-sense generation requests with a status lifecycle. `reason` records why the
-- sense was enqueued: 'pack' | 'subscribe_topup' | 'coverage_gap' | 'regen'.
-- UNIQUE (sense_id, reason) makes re-enqueuing a (sense, reason) pair a no-op
-- (see the ON CONFLICT producers in the pipeline) rather than an error.
--
-- Forward-only and idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS generation_queue (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sense_id      integer NOT NULL REFERENCES dim_word_senses(id),
    language_id   smallint NOT NULL,
    reason        text NOT NULL,                       -- 'pack'|'subscribe_topup'|'coverage_gap'|'regen'
    status        text NOT NULL DEFAULT 'pending',     -- pending|running|done|failed
    detail        jsonb,
    requested_at  timestamptz NOT NULL DEFAULT now(),
    completed_at  timestamptz,
    UNIQUE (sense_id, reason)
);

-- Worker dequeue path: oldest pending first.
CREATE INDEX IF NOT EXISTS idx_generation_queue_status_requested_at
    ON generation_queue (status, requested_at);
