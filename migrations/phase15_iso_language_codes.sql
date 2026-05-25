-- ME-11: Switch dim_languages.language_code from app-convention to ISO 639-1.
-- 'jp' -> 'ja', 'cn' -> 'zh'. Idempotent.
--
-- All FK references in the DB are to dim_languages.language_id (the integer
-- PK), so this only touches the human-readable code column. Verify before
-- running: SELECT language_id, language_code FROM public.dim_languages;

BEGIN;

UPDATE public.dim_languages
   SET language_code = 'zh'
 WHERE language_code = 'cn';

UPDATE public.dim_languages
   SET language_code = 'ja'
 WHERE language_code = 'jp';

-- Verify
DO $$
DECLARE
    bad_count int;
BEGIN
    SELECT count(*) INTO bad_count
      FROM public.dim_languages
     WHERE language_code IN ('cn', 'jp');
    IF bad_count > 0 THEN
        RAISE EXCEPTION 'Migration incomplete: % rows still have legacy codes', bad_count;
    END IF;
END $$;

COMMIT;
