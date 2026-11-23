-- =============================================================================
-- calibration_placement.sql  (TASK-1076, vocabulary placement schema; ADR-057, ADR-060)
-- =============================================================================
-- Purpose: a placement is a session mode of the vocabulary check
-- (wiki/features/vocab-placement.tech.md §13). This file only extends the two
-- calibration tables; the functions are in calibration_placement_rpcs.sql
-- (TASK-1077) and knowledge_calibration_inputs.sql (TASK-1079).
--
-- calibration_sessions
--   mode            CHECK admits 'placement'
--   stop_reason     precision | cap | time | exhausted | learner | abandoned
--   result          frozen result JSON (<= 2 KB, written by services/calibration_placement.py)
-- calibration_responses (placement rows always set item_kind and, except sound_pair
-- probes, instrument; item_kind NULL marks a legacy check row)
--   item_kind        meaning | reading | sound_pair
--   probe_kind       recheck | reading_after_miss | forced_guess | sound_pair (NULL = scored)
--   instrument       meaning_bare_v1 | reading_v1 (ja) | reading_tone_v1 (zh)
--   pair_response_id the word's scored meaning row (reading item and probes of that word)
--   option_sense_ids option sense ids in display order (NULL entries for zh K' and F')
--   key_position     0..3 (0..1 for sound_pair); never sent with an item
--   option_roles     zh reading items: K, KT, F, FT in display order; never sent
--   option_texts     zh reading items: the four displayed pinyin strings
--   chosen_position  0..3, NULL for "I don't know"
-- + partial index (user_id, anchor_vocab_id) WHERE answered_at IS NOT NULL (180-day
--   exclusion, tech §12) and a partial index on pair_response_id (the self-FK's
--   ON DELETE CASCADE and the word grouping read it).
--
-- Answer keys: calibration_responses has RLS on and no client privilege
-- (security_calibration_answer_keys.sql); nothing here grants anything.
--
-- Locking: every ADD COLUMN is nullable with no default (catalog-only, no rewrite:
-- pg_class.relfilenode is unchanged). Constraints are added NOT VALID in the first
-- transaction and validated afterwards under SHARE UPDATE EXCLUSIVE
-- (migrations/CLAUDE.md). Both tables are small (73 sessions, 1,259 responses on
-- 2026-11-19).
--
-- Idempotent and re-runnable. DDL only; no row is touched.
-- REQUIRES USER APPROVAL TO APPLY LIVE. Apply before calibration_placement_rpcs.sql.
-- Rollback: migrations/calibration_placement_rollback.sql (after the RPC rollback).
--
-- Read-only checks after apply:
--   SELECT table_name, column_name, data_type, is_nullable
--     FROM information_schema.columns
--    WHERE table_schema = 'public'
--      AND table_name IN ('calibration_sessions', 'calibration_responses')
--    ORDER BY table_name, ordinal_position;
--   SELECT conname, convalidated, pg_get_constraintdef(oid) FROM pg_constraint
--    WHERE conrelid IN ('public.calibration_sessions'::regclass,
--                       'public.calibration_responses'::regclass) ORDER BY 1;
--   SELECT indexrelid::regclass, pg_relation_size(indexrelid) FROM pg_index
--    WHERE indrelid = 'public.calibration_responses'::regclass;
--   SELECT relname, relfilenode FROM pg_class
--    WHERE relname IN ('calibration_sessions', 'calibration_responses');
--     -- before: 179439 / 179461 (read 2026-11-19); must be unchanged
-- =============================================================================

BEGIN;

-- The new key columns (key_position, option_roles, option_sense_ids) are hidden only
-- because calibration_responses has no client privilege. Refuse if that ever changed.
DO $$
BEGIN
  IF has_table_privilege('anon', 'public.calibration_responses', 'SELECT')
     OR has_table_privilege('authenticated', 'public.calibration_responses', 'SELECT') THEN
    RAISE EXCEPTION 'a client role can read calibration_responses; apply security_calibration_answer_keys.sql first';
  END IF;
END $$;

-- calibration_sessions --------------------------------------------------------
ALTER TABLE public.calibration_sessions DROP CONSTRAINT IF EXISTS calibration_sessions_mode_chk;
ALTER TABLE public.calibration_sessions ADD CONSTRAINT calibration_sessions_mode_chk
  CHECK (mode IN ('definition', 'pronunciation', 'placement')) NOT VALID;

ALTER TABLE public.calibration_sessions
  ADD COLUMN IF NOT EXISTS stop_reason text NULL,
  ADD COLUMN IF NOT EXISTS result      jsonb NULL;

ALTER TABLE public.calibration_sessions DROP CONSTRAINT IF EXISTS calibration_sessions_stop_reason_chk;
ALTER TABLE public.calibration_sessions ADD CONSTRAINT calibration_sessions_stop_reason_chk
  CHECK (stop_reason IS NULL OR stop_reason IN ('precision', 'cap', 'time', 'exhausted', 'learner', 'abandoned'))
  NOT VALID;

-- calibration_responses -------------------------------------------------------
ALTER TABLE public.calibration_responses
  ADD COLUMN IF NOT EXISTS item_kind        text NULL,
  ADD COLUMN IF NOT EXISTS probe_kind       text NULL,
  ADD COLUMN IF NOT EXISTS instrument       text NULL,
  ADD COLUMN IF NOT EXISTS pair_response_id bigint NULL,
  ADD COLUMN IF NOT EXISTS option_sense_ids integer[] NULL,
  ADD COLUMN IF NOT EXISTS key_position     smallint NULL,
  ADD COLUMN IF NOT EXISTS option_roles     text[] NULL,
  ADD COLUMN IF NOT EXISTS option_texts     text[] NULL,
  ADD COLUMN IF NOT EXISTS chosen_position  smallint NULL,
  -- PQ23 (2026-11-23): set on scored meaning rows when served; true = the word is asked the meaning
  -- question only (en, ja kana-only, or no reading item can be built). NULL on older rows and on
  -- reading/probe rows: readers fall back to calibration_placement_reading_exempt(lemma).
  ADD COLUMN IF NOT EXISTS reading_exempt   boolean NULL;

ALTER TABLE public.calibration_responses DROP CONSTRAINT IF EXISTS calibration_responses_item_kind_chk;
ALTER TABLE public.calibration_responses ADD CONSTRAINT calibration_responses_item_kind_chk
  CHECK (item_kind IS NULL OR item_kind IN ('meaning', 'reading', 'sound_pair')) NOT VALID;

ALTER TABLE public.calibration_responses DROP CONSTRAINT IF EXISTS calibration_responses_probe_kind_chk;
ALTER TABLE public.calibration_responses ADD CONSTRAINT calibration_responses_probe_kind_chk
  CHECK (probe_kind IS NULL OR probe_kind IN ('recheck', 'reading_after_miss', 'forced_guess', 'sound_pair')) NOT VALID;

ALTER TABLE public.calibration_responses DROP CONSTRAINT IF EXISTS calibration_responses_instrument_chk;
ALTER TABLE public.calibration_responses ADD CONSTRAINT calibration_responses_instrument_chk
  CHECK (instrument IS NULL OR instrument IN ('meaning_bare_v1', 'reading_v1', 'reading_tone_v1')) NOT VALID;

ALTER TABLE public.calibration_responses DROP CONSTRAINT IF EXISTS calibration_responses_pair_response_id_fkey;
ALTER TABLE public.calibration_responses ADD CONSTRAINT calibration_responses_pair_response_id_fkey
  FOREIGN KEY (pair_response_id) REFERENCES public.calibration_responses(id) ON DELETE CASCADE NOT VALID;

COMMENT ON COLUMN public.calibration_sessions.stop_reason IS
  'Placement only: why the session ended (precision, cap, time, exhausted, learner, abandoned).';
COMMENT ON COLUMN public.calibration_sessions.result IS
  'Placement only: the frozen result JSON (tech §8, <= 2 KB).';
COMMENT ON COLUMN public.calibration_responses.item_kind IS
  'meaning | reading | sound_pair; NULL = legacy check row (its kind is the session mode).';
COMMENT ON COLUMN public.calibration_responses.key_position IS
  'Placement: 0-based display position of the key. Answer key: never sent to a client.';
COMMENT ON COLUMN public.calibration_responses.option_roles IS
  'zh placement reading items: K, KT, F, FT in display order. Answer key: never sent to a client.';

COMMIT;

-- Validation outside the exclusive-lock window (SHARE UPDATE EXCLUSIVE; reads and
-- writes continue). All existing rows have NULL in the new columns.
ALTER TABLE public.calibration_sessions  VALIDATE CONSTRAINT calibration_sessions_mode_chk;
ALTER TABLE public.calibration_sessions  VALIDATE CONSTRAINT calibration_sessions_stop_reason_chk;
ALTER TABLE public.calibration_responses VALIDATE CONSTRAINT calibration_responses_item_kind_chk;
ALTER TABLE public.calibration_responses VALIDATE CONSTRAINT calibration_responses_probe_kind_chk;
ALTER TABLE public.calibration_responses VALIDATE CONSTRAINT calibration_responses_instrument_chk;
ALTER TABLE public.calibration_responses VALIDATE CONSTRAINT calibration_responses_pair_response_id_fkey;

-- 180-day exclusion: "has this user answered this lemma recently" (tech §12).
CREATE INDEX IF NOT EXISTS idx_calibration_responses_user_vocab_answered
  ON public.calibration_responses (user_id, anchor_vocab_id) WHERE answered_at IS NOT NULL;

-- The self-FK's ON DELETE CASCADE and the per-word grouping read pair_response_id.
CREATE INDEX IF NOT EXISTS idx_calibration_responses_pair
  ON public.calibration_responses (pair_response_id) WHERE pair_response_id IS NOT NULL;
