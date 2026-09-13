-- TASK-773b — the bulk distractor builder must not retry a short anchor forever.
-- =============================================================================
-- BUG, found while running the TASK-773 build on 2026-09-13
--   `calibration_cache_distractors_chunk` selects anchors that have NO cache
--   rows, and the driving script loops until a chunk processes zero anchors.
--   An anchor whose picker legitimately returns fewer than three usable foils
--   ends the attempt with no cache rows — so it is selected again by the very
--   next chunk, and again, forever. ja/ja pronunciation stalled at 2,339 of
--   2,352 with thirteen such anchors cycling indefinitely.
--
--   Stopping the script when a chunk fills nothing would have been wrong: the
--   selector is `ORDER BY sense_id LIMIT n`, so a handful of short anchors at
--   the front of that order would end the build before the thousands behind
--   them were ever reached.
--
-- DECISION — RECORD THE ATTEMPT, NOT A VERDICT
--   `calibration_distractor_cache_misses` records that an anchor was tried and
--   how many rows came back. That is a fact about a build run, and it is
--   deliberately NOT the same statement as "this anchor is bad" — that verdict
--   belongs to `calibration_anchor_blocklist` and is a human judgement
--   (TASK-767/768, and decision 5 of TASK-773).
--
--   The consequence of that distinction is what makes the table safe: nothing
--   at SERVE time reads it. `calibration_build_items` still consults the cache
--   itself and still self-fills on a miss, so an anchor listed here is not
--   barred from being served — it is only skipped by the BULK builder, which
--   has already learnt it has nothing to gain from retrying it.
--
--   The ledger is therefore derived data about derived data: clear it whenever
--   the dictionary changes, because an anchor that was short yesterday may have
--   acquired near neighbours since.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.calibration_distractor_cache_misses (
    mode            text     NOT NULL
        CHECK (mode IN ('definition', 'pronunciation')),
    anchor_sense_id integer  NOT NULL,
    rows_found      smallint NOT NULL,
    attempted_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (mode, anchor_sense_id)
);

COMMENT ON TABLE public.calibration_distractor_cache_misses IS
'TASK-773b. Anchors the bulk builder tried and could not fill with three foils.
A record of an ATTEMPT, not a verdict — the blocklist is where "this anchor is
bad" is said. Read only by the bulk builder, never at serve time. Clear it when
the dictionary changes.';

ALTER TABLE public.calibration_distractor_cache_misses ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.calibration_distractor_cache_misses FROM anon, authenticated;
GRANT SELECT ON TABLE public.calibration_distractor_cache_misses TO service_role;


CREATE OR REPLACE FUNCTION public.calibration_cache_distractors_chunk(
    p_word_language_id       smallint,
    p_definition_language_id smallint,
    p_mode                   text    DEFAULT 'definition',
    p_batch                  integer DEFAULT 25
)
RETURNS TABLE(anchors_processed integer, anchors_filled integer, anchors_short integer)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
SET statement_timeout TO '600s'
AS $function$
DECLARE
    v_anchor    record;
    v_rows      integer;
    v_processed integer := 0;
    v_filled    integer := 0;
    v_short     integer := 0;
    v_batch     integer := LEAST(GREATEST(COALESCE(p_batch, 25), 1), 200);
BEGIN
    IF auth.role() <> 'service_role' THEN
        RAISE EXCEPTION 'service_role required' USING ERRCODE = '42501';
    END IF;

    FOR v_anchor IN
        SELECT p.sense_id
          FROM calibration_anchor_pool p
         WHERE p.word_language_id       = p_word_language_id
           AND p.definition_language_id = p_definition_language_id
           AND (CASE WHEN p_mode = 'pronunciation' THEN p.has_pronunciation
                     ELSE p.has_embedding END)
           AND NOT EXISTS (SELECT 1 FROM calibration_distractor_cache c
                            WHERE c.mode = p_mode
                              AND c.anchor_sense_id = p.sense_id)
           -- TASK-773b: and not one we have already tried and failed to fill,
           -- which is what made this loop non-terminating.
           AND NOT EXISTS (SELECT 1 FROM calibration_distractor_cache_misses m
                            WHERE m.mode = p_mode
                              AND m.anchor_sense_id = p.sense_id)
         ORDER BY p.sense_id
         LIMIT v_batch
    LOOP
        v_rows := calibration_fill_distractor_cache(
            v_anchor.sense_id, p_word_language_id, p_definition_language_id, p_mode);
        v_processed := v_processed + 1;

        IF v_rows >= 3 THEN
            v_filled := v_filled + 1;
        ELSE
            v_short := v_short + 1;
            INSERT INTO calibration_distractor_cache_misses (
                mode, anchor_sense_id, rows_found)
            VALUES (p_mode, v_anchor.sense_id, LEAST(v_rows, 32767)::smallint)
            ON CONFLICT (mode, anchor_sense_id)
            DO UPDATE SET rows_found = EXCLUDED.rows_found,
                          attempted_at = now();
        END IF;
    END LOOP;

    RETURN QUERY SELECT v_processed, v_filled, v_short;
END;
$function$;

COMMENT ON FUNCTION public.calibration_cache_distractors_chunk(smallint, smallint, text, integer) IS
'TASK-773/773b. Fills the distractor cache for up to p_batch not-yet-tried anchors
of one language pair and mode. Resumable and TERMINATING — call repeatedly until
anchors_processed is 0. An anchor that cannot be filled is recorded in
calibration_distractor_cache_misses so it is not retried; that ledger is cleared
by calibration_clear_distractor_cache_misses() when the dictionary changes.';


-- Clearing the ledger is a separate, explicit act: an anchor that was short
-- yesterday may have gained near neighbours since, and only the caller knows
-- whether the dictionary has moved.
CREATE OR REPLACE FUNCTION public.calibration_clear_distractor_cache_misses(
    p_mode text DEFAULT NULL
)
RETURNS integer
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_deleted integer;
BEGIN
    IF auth.role() <> 'service_role' THEN
        RAISE EXCEPTION 'service_role required' USING ERRCODE = '42501';
    END IF;

    DELETE FROM calibration_distractor_cache_misses m
     WHERE p_mode IS NULL OR m.mode = p_mode;
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$function$;

COMMENT ON FUNCTION public.calibration_clear_distractor_cache_misses(text) IS
'TASK-773b. Forgets which anchors the bulk builder could not fill, so the next
build retries them. Run after the dictionary changes.';

REVOKE ALL ON FUNCTION public.calibration_clear_distractor_cache_misses(text) FROM public;
GRANT EXECUTE ON FUNCTION public.calibration_clear_distractor_cache_misses(text) TO service_role;
