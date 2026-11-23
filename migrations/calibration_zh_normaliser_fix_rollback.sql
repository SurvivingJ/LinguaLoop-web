-- Rollback of calibration_zh_normaliser_fix.sql (TASK-1074).
-- Restores the live bodies as of 2026-11-19 (pg_get_functiondef, read-only), with no
-- SET search_path, as they were. zh readings without a numbered part go back to
-- normalising to their diacritics with syllable count 0 (E7).

CREATE OR REPLACE FUNCTION public.calibration_normalise_pronunciation(p_pronunciation text, p_language_id smallint)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    SELECT CASE
        WHEN p_pronunciation IS NULL OR btrim(p_pronunciation) = '' THEN NULL
        WHEN p_language_id = 1 THEN
            -- Chinese is stored as 'yìng yòng (ying4 yong4)'. The parenthesised
            -- numbered form is the stable one and is what
            -- services/vocabulary_ladder/deterministic/lexicon.py:266 treats as
            -- canonical, so it wins when present. Tone digits are KEPT: tone is
            -- part of the identity of a reading, and a tone-only difference is
            -- exactly the minimal pair this mode exists to test.
            lower(regexp_replace(
                coalesce(substring(p_pronunciation from '\(([^)]*)\)'), p_pronunciation),
                '\s+', '', 'g'))
        WHEN p_language_id = 3 THEN
            -- Japanese readings are already kana. Loanwords carry a latin gloss
            -- suffix ('いんく-ink'), which is not part of the reading.
            lower(regexp_replace(
                regexp_replace(normalize(p_pronunciation, NFC), '-.*$', ''),
                '\s+', '', 'g'))
        ELSE
            lower(regexp_replace(p_pronunciation, '\s+', '', 'g'))
    END;
$function$;

COMMENT ON FUNCTION public.calibration_normalise_pronunciation(text, smallint) IS
  'Canonical comparison form of a pronunciation, per language. zh prefers the parenthesised numbered pinyin and KEEPS tone digits (a tone-only difference is a legitimate minimal pair, not noise); ja strips the latin gloss suffix off loanword readings. Used by pronunciation_distractors() both to measure edit distance and to reject homophones, which would otherwise be a second correct answer.';

REVOKE ALL ON FUNCTION public.calibration_normalise_pronunciation(text, smallint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_normalise_pronunciation(text, smallint) TO service_role;


CREATE OR REPLACE FUNCTION public.calibration_syllable_count(p_normalised text, p_language_id smallint)
 RETURNS integer
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    SELECT CASE
        WHEN p_normalised IS NULL OR p_normalised = '' THEN 0
        -- zh normalised form is numbered pinyin ('ying4yong4'): exactly one tone
        -- digit per syllable, so counting digits counts syllables.
        WHEN p_language_id = 1 THEN
            coalesce(length(regexp_replace(p_normalised, '[^1-5]', '', 'g')), 0)
        -- ja is kana; small kana (ゃゅょっぁぃぅぇぉ) do not start a mora, and the
        -- long-vowel mark does, so this is a mora count rather than a char count.
        WHEN p_language_id = 3 THEN
            greatest(length(regexp_replace(
                p_normalised, '[ゃゅょャュョぁぃぅぇぉァィゥェォ]', '', 'g')), 0)
        ELSE length(p_normalised)
    END;
$function$;

COMMENT ON FUNCTION public.calibration_syllable_count(text, smallint) IS
  'Syllables (zh) or morae (ja) in a normalised pronunciation. pronunciation_distractors() prefers candidates with the SAME count: a reading of a different length is visibly a different shape, so it is a weak distractor however close the edit distance says it is.';

REVOKE ALL ON FUNCTION public.calibration_syllable_count(text, smallint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_syllable_count(text, smallint) TO service_role;
