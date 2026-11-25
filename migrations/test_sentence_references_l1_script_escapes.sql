-- ============================================================================
-- test_sentence_references_l1_script_escapes.sql - restore the intended Han
-- range in the L1-script check (finding F-05)
-- Date: 2026-11-23   Review: pkg8. NOT APPLIED.
--
-- WHAT: CREATE OR REPLACE public.test_sentence_references_check_l1_script(),
-- the BEFORE INSERT/UPDATE trigger function behind trigger
-- test_sentence_references_check_l1_script on test_sentence_references. Same
-- definition as migrations/test_sentence_references_schema.sql intends, with
-- every non-ASCII code point written as a regex escape (\uXXXX / \UXXXXXXXX),
-- so this file is pure ASCII and no Unicode normalisation can alter it.
-- Ranges: Han U+4E00-9FFF, U+3400-4DBF, U+F900-FAFF, U+20000-2A6DF;
-- kana U+3040-309F, U+30A0-30FF, U+31F0-31FF, U+FF66-FF9F.
--
-- WHY: the live Han range starts at U+8C48 instead of U+F900 (the repo's
-- literal U+F900 CJK compatibility ideograph was NFC-normalised to its
-- canonical equivalent U+8C48 when applied). [U+8C48-U+FAFF] spans Hangul
-- syllables (U+AC00-D7A3), Yi (U+A000-A4CF) and more, so the live trigger
-- rejects an L1 reference containing Korean or Yi text for a zh/ja test
-- (live: U&'\D55C\AD6D\C5B4' (Korean) matches the live range = true).
--
-- WHAT A LEARNER OR THE APP WOULD NOTICE: storing a sentence reference whose
-- l1_text contains Hangul, Yi or other characters in U+A000-U+F8FF stops failing
-- with check_violation. Rejection of real Han / kana text is unchanged
-- (U+8C48 itself is still inside U+4E00-9FFF). Existing rows are not re-checked;
-- the change only narrows what is rejected, so nothing can start failing.
--
-- PRECONDITIONS: standard_conforming_strings = on (live: on), so '\u4E00'
-- reaches the regex engine as an escape. Checked read-only 2026-11-23:
-- U+4E00 and U+F900 and U+20000 match the new Han class; U&'\D55C\AD6D\C5B4' (Korean), Yi and ASCII
-- do not; the new kana class matches hiragana, katakana and half-width kana.
--
-- VERIFY BEFORE / AFTER (read-only). Lists the code points of the live ranges
-- and the body hash. Before: han_cps contains 8c48, rejects_hangul = true,
-- body_md5 = fd8764eacc672a6d6b993a80082275ec. After: han_cps and kana_cps are
-- NULL (no literal non-ASCII left), v_han is the escaped string, rejects_hangul
-- = false, body_md5 = 878716b974eab653b9167a2e01263079, definer = false, search_path {public, pg_temp},
-- anon_x = auth_x = false.
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g')) AS body_md5,
--          substring(p.prosrc from 'v_han\s+constant text := ''([^'']*)''') AS v_han,
--          (SELECT string_agg(to_hex(ascii(ch)), ' ') FROM regexp_split_to_table(
--              substring(p.prosrc from 'v_han\s+constant text := ''([^'']*)'''), '') ch
--            WHERE ascii(ch) > 127) AS han_cps,
--          (SELECT string_agg(to_hex(ascii(ch)), ' ') FROM regexp_split_to_table(
--              substring(p.prosrc from 'v_kana\s+constant text := ''([^'']*)'''), '') ch
--            WHERE ascii(ch) > 127) AS kana_cps,
--          U&'\D55C\AD6D\C5B4' ~ substring(p.prosrc from 'v_han\s+constant text := ''([^'']*)''') AS rejects_hangul,
--          p.prosecdef AS definer, p.proconfig AS search_path,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x
--     FROM pg_proc p WHERE p.oid = 'public.test_sentence_references_check_l1_script()'::regprocedure;
--
-- ROLLBACK: none recommended (the live body is the defect). To restore it
-- byte for byte, save `SELECT pg_get_functiondef('public.test_sentence_references_check_l1_script()'::regprocedure);`
-- before applying and re-run that output.
--
-- Live attributes reproduced: SECURITY INVOKER, search_path public, pg_temp,
-- owner postgres, EXECUTE service_role only. The trigger is not touched.
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.test_sentence_references_check_l1_script()
RETURNS trigger LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    v_l2_code  text;
    -- Regex escapes, not literal characters: the apply path NFC-normalised a
    -- literal U+F900 to U+8C48 (finding F-05). Keep this file ASCII-only here.
    v_han      constant text := '[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF\U00020000-\U0002A6DF]';
    v_kana     constant text := '[\u3040-\u309F\u30A0-\u30FF\u31F0-\u31FF\uFF66-\uFF9F]';
    v_pattern  text;
BEGIN
    SELECT l.language_code INTO v_l2_code
      FROM public.test_sentences s
      JOIN public.tests t ON t.id = s.test_id
      JOIN public.dim_languages l ON l.id = t.language_id
     WHERE s.id = NEW.sentence_id;

    IF v_l2_code IS NULL THEN
        RAISE EXCEPTION 'test_sentence_references: sentence % has no test / language', NEW.sentence_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    v_pattern := CASE v_l2_code
        WHEN 'zh' THEN v_han
        WHEN 'ja' THEN v_han || '|' || v_kana
        ELSE NULL
    END;

    IF v_pattern IS NOT NULL AND NEW.l1_text ~ v_pattern THEN
        RAISE EXCEPTION 'test_sentence_references: l1_text contains the L2 (%) script: %',
            v_l2_code, left(NEW.l1_text, 80)
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

ALTER FUNCTION public.test_sentence_references_check_l1_script() OWNER TO postgres;
REVOKE ALL ON FUNCTION public.test_sentence_references_check_l1_script() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.test_sentence_references_check_l1_script() TO service_role;

COMMIT;
