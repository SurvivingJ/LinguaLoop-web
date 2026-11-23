-- =============================================================================
-- calibration_placement_rpcs_rollback.sql  (TASK-1077) — reverses calibration_placement_rpcs.sql.
-- Drops every placement function (public API and helpers). Apply BEFORE
-- calibration_placement_rollback.sql. Does not touch calibration_zh_tone_variants
-- (TASK-1092) or any row. REQUIRES USER APPROVAL TO APPLY LIVE.
-- =============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.calibration_placement_close_stale(uuid, interval);
DROP FUNCTION IF EXISTS public.calibration_placement_close(uuid, uuid, text);
DROP FUNCTION IF EXISTS public.calibration_placement_answer(uuid, uuid, bigint, smallint, integer, smallint, jsonb);
DROP FUNCTION IF EXISTS public.calibration_placement_next_item(uuid, uuid, smallint, integer);
DROP FUNCTION IF EXISTS public.calibration_placement_ready_counts(smallint, smallint);
DROP FUNCTION IF EXISTS public.calibration_placement_build_recheck(uuid, uuid, smallint, double precision);
DROP FUNCTION IF EXISTS public.calibration_placement_build_meaning(uuid, uuid, smallint, smallint, smallint, boolean, integer, double precision);
DROP FUNCTION IF EXISTS public.calibration_placement_build_reading(uuid, uuid, smallint, integer, text, real, smallint, bigint, text, double precision, integer[], text[]);
DROP FUNCTION IF EXISTS public.calibration_placement_tallies(uuid);
DROP FUNCTION IF EXISTS public.calibration_placement_reveal(bigint);
DROP FUNCTION IF EXISTS public.calibration_placement_reveal_reading(integer, smallint);
DROP FUNCTION IF EXISTS public.calibration_placement_item_payload(bigint);
DROP FUNCTION IF EXISTS public.calibration_placement_option_texts(bigint);
DROP FUNCTION IF EXISTS public.calibration_placement_insert_item(uuid, uuid, integer, integer, text, real, smallint, text, text, text, bigint, integer[], text[], text[], integer, boolean, double precision, integer[]);
DROP FUNCTION IF EXISTS public.calibration_placement_draw(uuid, uuid, smallint, smallint, smallint, boolean, integer);
DROP FUNCTION IF EXISTS public.calibration_placement_band_has_word(uuid, uuid, smallint, smallint, smallint, integer);
DROP FUNCTION IF EXISTS public.calibration_placement_candidates(uuid, uuid, smallint, smallint, smallint, integer);
DROP FUNCTION IF EXISTS public.calibration_placement_reading_ready(integer, smallint, text);
DROP FUNCTION IF EXISTS public.calibration_placement_reading_foil_counts(integer, integer, smallint, text, text);
DROP FUNCTION IF EXISTS public.calibration_placement_reading_parts(integer, integer, smallint, text, text, double precision, integer[], text[]);
DROP FUNCTION IF EXISTS public.calibration_placement_own_readings(integer, smallint);
DROP FUNCTION IF EXISTS public.calibration_placement_reading_key(integer, smallint);
DROP FUNCTION IF EXISTS public.calibration_placement_meaning_parts(integer, smallint, smallint, text, text);
DROP FUNCTION IF EXISTS public.calibration_placement_unit(double precision, text);
DROP FUNCTION IF EXISTS public.calibration_placement_mora_skeleton(text);
DROP FUNCTION IF EXISTS public.calibration_placement_well_formed_reading(text, smallint);
DROP FUNCTION IF EXISTS public.calibration_placement_kana_pattern(text);
DROP FUNCTION IF EXISTS public.calibration_placement_toneless(text);
DROP FUNCTION IF EXISTS public.calibration_placement_units(text, smallint);
DROP FUNCTION IF EXISTS public.calibration_placement_reading_exempt(text, smallint);
DROP FUNCTION IF EXISTS public.calibration_placement_strip_definition(text, smallint, smallint);

COMMIT;
