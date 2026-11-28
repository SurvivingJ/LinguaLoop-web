-- =============================================================================
-- word_upload_queue.sql  (ADR-069, wiki/features/word-upload-queue.md)
-- =============================================================================
-- Purpose: give the word-list upload a durable work queue. A learner's
-- uploaded words are stored here as raw text; the operator builds every
-- missing asset offline (senses, glosses, embeddings, pronunciation, ladder
-- core + exercises, exercise audio) with the authoring skills, and
-- scripts/word_upload_queue.py moves each word to `done` once all of its
-- assets exist, inserting the learner's user_word_watchlist row at that point.
--
-- Until now POST /api/word-list/submit ran the whole LLM pipeline inside the
-- web process (routes/word_list_import.py, worker-pool thread). That path is
-- kept behind WORD_LIST_INLINE_GENERATION=true; the queue is the default.
--
-- Row lifecycle (status):
--   pending   raw word stored; not yet resolved to a dim_vocabulary row
--   building  resolved (vocab_id set; sense_id set once a native standard
--             sense exists); `missing` lists the assets still to build
--   done      every asset exists; user_word_watchlist row written
--   failed    cannot be built (untokenisable, manual-only sense, operator
--             rejected); `detail.reason` says why
--   cancelled withdrawn (operator)
--
-- `missing` holds asset keys from services/word_list_import/queue.py
-- ASSET_KEYS: vocab, sense, embedding, pronunciation, gloss, core,
-- exercises, audio.
--
-- One row per (user, language, word): a learner re-submitting a word does
-- not queue it twice. Two learners uploading the same word get one row each;
-- the operator script de-duplicates by vocab/sense when it exports work.
--
-- THIS FILE IS ADDITIVE ONLY: one new table, its indexes, RLS. Nothing
-- existing is altered and no row is written. Empty table: 32 kB with its
-- indexes; about 250-400 bytes per row (raw word, a short `missing` array,
-- a small `detail`). The 50-word / 5-batch-per-day cap bounds growth at
-- 250 rows per learner per day.
--
-- FK targets (live, checked 2026-11-28 via information_schema):
--   public.users(id) uuid, dim_languages(id) smallint,
--   dim_vocabulary(id) integer, dim_word_senses(id) integer.
--   user_id cascades like user_word_watchlist; reference-data FKs carry no
--   ON DELETE clause, matching user_word_watchlist_schema.sql.
--
-- Access: service role only (RLS on, no policy, no client grant). Every
-- reader and writer is Flask (supabase admin) or an operator script.
--
-- VERIFY BEFORE:
--   SELECT to_regclass('public.word_upload_queue');            -- NULL
--   SELECT pg_database_size(current_database()) < 480 * 1024 * 1024;  -- true
-- VERIFY AFTER:
--   SELECT relrowsecurity FROM pg_class WHERE oid = 'public.word_upload_queue'::regclass;  -- true
--   SELECT count(*) FROM pg_policies WHERE tablename = 'word_upload_queue';                -- 0
--   SELECT has_table_privilege('authenticated', 'public.word_upload_queue', 'SELECT');     -- false
--
-- Rollback: word_upload_queue_rollback.sql (DROP TABLE; queued words are lost,
-- watchlist rows already written stay).
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.word_upload_queue (
    id                bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id           uuid        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    upload_batch_id   uuid        NOT NULL,
    language_id       smallint    NOT NULL REFERENCES public.dim_languages(id),
    raw_word          text        NOT NULL CHECK (char_length(raw_word) BETWEEN 1 AND 40),
    gloss_language_id smallint    REFERENCES public.dim_languages(id),
    vocab_id          integer     REFERENCES public.dim_vocabulary(id),
    sense_id          integer     REFERENCES public.dim_word_senses(id),
    status            text        NOT NULL DEFAULT 'pending'
                                  CHECK (status IN ('pending', 'building', 'done', 'failed', 'cancelled')),
    missing           text[]      NOT NULL DEFAULT '{}',
    detail            jsonb,
    requested_at      timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    completed_at      timestamptz,
    CONSTRAINT word_upload_queue_user_lang_word_key UNIQUE (user_id, language_id, raw_word),
    CONSTRAINT word_upload_queue_gloss_not_own CHECK (gloss_language_id IS DISTINCT FROM language_id)
);

COMMENT ON TABLE public.word_upload_queue IS
  'Word-list upload work queue (ADR-069). One row per (user, language, raw word). '
  'Built offline by scripts/word_upload_queue.py; done rows have a user_word_watchlist row.';
COMMENT ON COLUMN public.word_upload_queue.gloss_language_id IS
  'Language the cross-language gloss is written in: the uploader''s native language '
  '(English when unset), NULL when that is the word''s own language.';
COMMENT ON COLUMN public.word_upload_queue.missing IS
  'Asset keys still to build (services/word_list_import/queue.py ASSET_KEYS); empty when done.';

-- Operator work list: open rows of one language, oldest first.
CREATE INDEX IF NOT EXISTS idx_word_upload_queue_status_lang_requested
    ON public.word_upload_queue (status, language_id, requested_at);
-- Learner's own queue on GET /api/word-list/watchlist and the daily batch cap.
CREATE INDEX IF NOT EXISTS idx_word_upload_queue_user_requested
    ON public.word_upload_queue (user_id, requested_at DESC);

ALTER TABLE public.word_upload_queue ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.word_upload_queue FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.word_upload_queue TO service_role;

COMMIT;
