-- TASK-1074: zh reading normaliser and syllable count for readings with no numbered part.
-- =============================================================================
-- PROBLEM (wiki/features/vocab-placement.tech.md §0 E7)
--   zh readings used to be stored as 'yìng yòng (ying4 yong4)', and
--   calibration_normalise_pronunciation() took the parenthesised numbered part as
--   the comparison form. 6,621 of 8,110 zh standard native readings no longer
--   carry it ('yuán xíng'). For those the function returned the diacritic string
--   ('yuánxíng') and calibration_syllable_count() counted its tone digits: 0. Any
--   zh pronunciation cache fill (pronunciation_distractors(), TASK-1063 or a
--   refill) would rank foils with a broken length and syllable test.
--
-- FIX
--   calibration_normalise_pronunciation(p, 1), when p has no '(…)' part: numbered
--   pinyin derived from the tone marks, per space-separated token —
--     * lower case, NFD; for each tone mark (U+0304 ā, U+0301 á, U+030C ǎ, U+0300 à
--       -> 1..4) the mark is removed and the digit goes after the rest of its
--       syllable (following vowels, then n / ng / g unless a vowel follows, then an
--       er-hua r unless a vowel follows), so one token holding two syllables still
--       splits ('yíhuìr' -> 'yi2huir4');
--     * NFC (ü stays ü: the stored numbered parts write 'lü4', and the comparison
--       form must match them, or 绿 'lǜ (lü4)' and 律 'lǜ' would differ by one edit);
--     * a token that still ends in a letter is unmarked: tone 5 ('bēi zi' -> 'bei1zi5');
--     * separators (whitespace, ', -, ·) removed.
--   A reading WITH a '(…)' part normalises exactly as before (same expression).
--   ja and other languages: unchanged.
--
--   calibration_syllable_count(n, 1): unchanged when n has a tone digit; a zh value
--   with no digit at all is normalised first, so a diacritic or unmarked reading
--   counts its syllables instead of 0 ('ma' -> 1, 'yuánxíng' -> 2).
--
--   Python mirror: services/placement_tones.to_numbered (TASK-1082); the same
--   fixtures are tested on both sides:
--     'yuán xíng' -> 'yuan2xing2'   'bēi zi' -> 'bei1zi5'
--     'lǜ shī'    -> 'lü4shi1'      'nǚ ér'  -> 'nü3er2'
--
-- SAFETY
--   - Same signatures, same volatility (IMMUTABLE PARALLEL SAFE). Both functions now
--     SET search_path (migrations/CLAUDE.md); calibration_syllable_count() calls
--     the normaliser schema-qualified.
--   - Only caller: pronunciation_distractors() (live pg_proc search, 2026-11-19); no
--     index, generated column, constraint or view uses either function, so nothing
--     stored needs rebuilding. Cached foils are NOT refilled here (TASK-1063).
--   - Checked on the local harness over all 11,977 native zh readings: the 5,356 rows
--     with a numbered part normalise and count byte-identically; every one of the 8,110
--     standard rows normalises to ^([a-zü]+[1-5])+$.
--   - Rollback: calibration_zh_normaliser_fix_rollback.sql (the previous live bodies).
--
-- VERIFY (read-only, after apply)
--   SELECT (pronunciation ~ '\(') AS has_numbered_part,
--          count(*) AS readings,
--          count(*) FILTER (WHERE calibration_syllable_count(
--              calibration_normalise_pronunciation(pronunciation, 1::smallint), 1::smallint) = 0)
--            AS syllable_count_zero,
--          count(*) FILTER (WHERE calibration_normalise_pronunciation(pronunciation, 1::smallint)
--              !~ '^([a-zü]+[1-5])+$') AS not_numbered
--     FROM dim_word_senses
--    WHERE word_language_id = 1 AND definition_language_id = 1
--      AND definition_level = 'standard' AND pronunciation IS NOT NULL
--    GROUP BY 1;
--   -- expect syllable_count_zero = 0 and not_numbered = 0 in both rows.
--   SELECT calibration_normalise_pronunciation(r, 1::smallint)
--     FROM unnest(ARRAY['yuán xíng', 'bēi zi', 'lǜ shī', 'nǚ ér']) r;
--   -- expect yuan2xing2, bei1zi5, lü4shi1, nü3er2
-- =============================================================================

CREATE OR REPLACE FUNCTION public.calibration_normalise_pronunciation(
    p_pronunciation text,
    p_language_id   smallint
)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
SET search_path = public, pg_temp
AS $function$
    SELECT CASE
        WHEN p_pronunciation IS NULL OR btrim(p_pronunciation) = '' THEN NULL
        WHEN p_language_id = 1
         AND substring(p_pronunciation from '\(([^)]*)\)') IS NOT NULL THEN
            -- Chinese stored as 'yìng yòng (ying4 yong4)': the parenthesised
            -- numbered form wins, exactly as before this migration. Tone digits are
            -- KEPT: a tone-only difference is the minimal pair this mode tests.
            lower(regexp_replace(
                substring(p_pronunciation from '\(([^)]*)\)'),
                '\s+', '', 'g'))
        WHEN p_language_id = 1 THEN
            -- Chinese stored as tone-marked pinyin only ('yuán xíng', TASK-1074):
            -- numbered form from the marks. Mirror: services/placement_tones.to_numbered.
            regexp_replace(
                regexp_replace(
                    normalize(
                        regexp_replace(regexp_replace(regexp_replace(regexp_replace(
                            normalize(lower(p_pronunciation), NFD),
                            '\u0304((?:[aeiou]\u0308?)*(?:(?:ng|n|g)(?![aeiou]))?(?:r(?![aeiou]))?)', '\11', 'g'),
                            '\u0301((?:[aeiou]\u0308?)*(?:(?:ng|n|g)(?![aeiou]))?(?:r(?![aeiou]))?)', '\12', 'g'),
                            '\u030c((?:[aeiou]\u0308?)*(?:(?:ng|n|g)(?![aeiou]))?(?:r(?![aeiou]))?)', '\13', 'g'),
                            '\u0300((?:[aeiou]\u0308?)*(?:(?:ng|n|g)(?![aeiou]))?(?:r(?![aeiou]))?)', '\14', 'g'),
                        NFC),
                    -- a syllable left without a digit has no mark: neutral tone
                    '([a-zü])(?=[\s''·-]|$)', '\15', 'g'),
                '[\s''·-]+', '', 'g')
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
  'Canonical comparison form of a pronunciation, per language. zh: the parenthesised numbered pinyin when present, else numbered pinyin derived from the tone marks (tone 5 when unmarked, ü kept; TASK-1074); tone digits are KEPT (a tone-only difference is a legitimate minimal pair, not noise). ja strips the latin gloss suffix off loanword readings. Used by pronunciation_distractors() both to measure edit distance and to reject homophones, which would otherwise be a second correct answer.';

REVOKE ALL ON FUNCTION public.calibration_normalise_pronunciation(text, smallint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_normalise_pronunciation(text, smallint) TO service_role;


CREATE OR REPLACE FUNCTION public.calibration_syllable_count(
    p_normalised  text,
    p_language_id smallint
)
RETURNS integer
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
SET search_path = public, pg_temp
AS $function$
    SELECT CASE
        WHEN p_normalised IS NULL OR p_normalised = '' THEN 0
        -- zh normalised form is numbered pinyin ('ying4yong4'): exactly one tone
        -- digit per syllable, so counting digits counts syllables. A value with no
        -- digit at all (tone marks only, or unmarked) is normalised first (TASK-1074).
        WHEN p_language_id = 1 THEN
            coalesce(length(regexp_replace(
                CASE WHEN p_normalised ~ '[1-5]' THEN p_normalised
                     ELSE public.calibration_normalise_pronunciation(p_normalised, 1::smallint)
                END,
                '[^1-5]', '', 'g')), 0)
        -- ja is kana; small kana (ゃゅょっぁぃぅぇぉ) do not start a mora, and the
        -- long-vowel mark does, so this is a mora count rather than a char count.
        WHEN p_language_id = 3 THEN
            greatest(length(regexp_replace(
                p_normalised, '[ゃゅょャュョぁぃぅぇぉァィゥェォ]', '', 'g')), 0)
        ELSE length(p_normalised)
    END;
$function$;

COMMENT ON FUNCTION public.calibration_syllable_count(text, smallint) IS
  'Syllables (zh) or morae (ja) in a normalised pronunciation. zh counts tone digits; a zh value with no digit is normalised first (TASK-1074). pronunciation_distractors() prefers candidates with the SAME count: a reading of a different length is visibly a different shape, so it is a weak distractor however close the edit distance says it is.';

REVOKE ALL ON FUNCTION public.calibration_syllable_count(text, smallint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_syllable_count(text, smallint) TO service_role;
