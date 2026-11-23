-- Rollback of calibration_zh_tones.sql (TASK-1092). Drops the zh tone inventory, the
-- character-reading table and their functions. Run only while no deployed function
-- calls calibration_zh_tone_variants() (the placement item builder, TASK-1077); a
-- dependent plpgsql body would fail at call time.

DROP FUNCTION IF EXISTS public.calibration_zh_tone_variants(text, integer);
DROP FUNCTION IF EXISTS public.calibration_refresh_zh_tone_inventory();
DROP FUNCTION IF EXISTS public.calibration_zh_mark_syllable(text, integer);
DROP FUNCTION IF EXISTS public.calibration_zh_parse_pinyin(text);
DROP TABLE IF EXISTS public.calibration_zh_tone_inventory;
DROP TABLE IF EXISTS public.calibration_zh_char_readings;
