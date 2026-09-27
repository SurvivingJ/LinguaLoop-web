-- Phase 0 cost instrumentation for the vocabulary-ladder pipeline.
--
-- llm_calls already has cost_usd / latency_ms / language_code (populated by
-- services/llm_service.py's call_llm -> _log_llm_call), but nothing records
-- WHERE the tokens/cost went at a finer grain: how many tokens, how much of
-- the prompt was cache-served, which sense a call was generating for, which
-- generation batch it belonged to, or whether it was the primary attempt vs.
-- a retry/repair/salvage turn. Without that, cost cannot be broken down by
-- sense, by call kind, or joined back to word_assets — which is the entire
-- point of Phase 0 ("we cannot optimise cost because nothing records it").
--
-- Purely additive: every new column is nullable (or has a default), so
-- existing rows and any in-flight code that inserts without them are
-- unaffected. services/llm_service.py's writer degrades gracefully if this
-- migration has not been applied yet (retries the insert without these
-- columns and logs one warning) — see _insert_llm_call_row.
--
-- Columns
-- -------
--   prompt_tokens         usage.prompt_tokens from the provider response.
--   completion_tokens     usage.completion_tokens from the provider response.
--   cached_tokens         usage.prompt_tokens_details.cached_tokens — the
--                         portion of the prompt served from a provider-side
--                         cache (0 or NULL when the provider doesn't report
--                         caching for that call).
--   reasoning_tokens      usage.completion_tokens_details.reasoning_tokens —
--                         already extracted by _extract_usage_tokens but
--                         previously logged to the CSV sink only, never to
--                         this table.
--   sense_id              dim_word_senses.id this call was generating/judging
--                         for. Type matches dim_word_senses.id (int4). No FK:
--                         a sense can be deleted (or the dictionary can be
--                         rebuilt) without llm_calls history becoming invalid
--                         or blocking the delete; this is an observability
--                         tag, not a referential relationship.
--   call_role             what kind of call this was within one generation
--                         attempt. CHECK-constrained to the five roles
--                         services/llm_service.py and its callers actually
--                         emit today (see CALL_ROLE_* constants there):
--                           primary      - the normal/first-attempt call.
--                           retry        - an automatic same-prompt retry
--                                          after a call or shape failure
--                                          (e.g. a generator's 2nd of 2
--                                          attempts).
--                           json_repair  - llm_service's own one-shot
--                                          malformed-JSON repair turn.
--                           repair       - a targeted repair call given
--                                          specific validation errors (P1's
--                                          repair()/repair_sentences(), and
--                                          llm_service's schema-validation
--                                          repair turn).
--                           salvage      - prompt3_transforms' text-mode
--                                          salvage attempt after strict JSON
--                                          parsing fails twice.
--   generation_batch_id   word_assets.generation_batch_id for the batch this
--                         call belongs to. Type matches word_assets'
--                         generation_batch_id (uuid). No FK for the same
--                         reason as sense_id — batches are ephemeral
--                         identifiers, not a table with its own rows.
--
-- RLS / grants
-- ------------
-- llm_calls currently has RLS disabled (relrowsecurity = false) and anon,
-- authenticated and service_role all already hold INSERT/SELECT on it — so no
-- new grants or policies are needed for these columns; they inherit the
-- table's existing (lack of) row-level restrictions. If RLS is ever enabled
-- on this table, remember these columns carry no additional sensitivity
-- beyond what's already stored (sense_id/generation_batch_id are internal
-- identifiers, not user data).
--
-- Indexes
-- -------
--   sense_id, created_at — the two axes cost analysis actually filters by
--   ("what did sense N cost across all its calls" / "what did we spend since
--   time T", the latter already the access pattern in
--   scripts/run_generation_batch.py's spend_since()). created_at had no index
--   before this migration.

BEGIN;

ALTER TABLE llm_calls
    ADD COLUMN IF NOT EXISTS prompt_tokens        integer,
    ADD COLUMN IF NOT EXISTS completion_tokens     integer,
    ADD COLUMN IF NOT EXISTS cached_tokens          integer,
    ADD COLUMN IF NOT EXISTS reasoning_tokens        integer,
    ADD COLUMN IF NOT EXISTS sense_id                 integer,
    ADD COLUMN IF NOT EXISTS call_role                 text,
    ADD COLUMN IF NOT EXISTS generation_batch_id        uuid;

-- Guarded so re-running this migration (e.g. after a partial apply) does not
-- error on a constraint that already exists.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'llm_calls_call_role_check'
    ) THEN
        ALTER TABLE llm_calls
            ADD CONSTRAINT llm_calls_call_role_check
            CHECK (call_role IS NULL OR call_role IN (
                'primary', 'retry', 'json_repair', 'repair', 'salvage'
            ));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_llm_calls_sense_id ON llm_calls (sense_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_created_at ON llm_calls (created_at);

COMMIT;

-- Verification (run after apply):
--   SELECT column_name, data_type FROM information_schema.columns
--   WHERE table_name = 'llm_calls'
--   AND column_name IN ('prompt_tokens', 'completion_tokens', 'cached_tokens',
--                        'reasoning_tokens', 'sense_id', 'call_role',
--                        'generation_batch_id');
