-- TASK-1092: zh tone variants for placement reading items (ADR-060).
-- =============================================================================
-- WHAT
--   A zh placement reading item shows four tone-marked pinyin strings: the key K,
--   a tone variant K′ of K, a cached segmental foil F and a tone variant F′ of F
--   (wiki/features/vocab-placement.tech.md §2 rule 4). A tone variant is the same
--   syllables with a different tone combination in which every syllable+tone
--   exists in Mandarin, i.e. occurs in at least one zh dictionary reading. This
--   file adds what the item builder (TASK-1077) needs for that:
--
--   * calibration_zh_tone_inventory: toneless syllable -> the full tones (1-4) it
--     carries anywhere in the native zh readings of dim_word_senses (≈ 382 rows,
--     ≈ 15 KB). A syllable only ever seen neutral is listed with no tones.
--   * calibration_refresh_zh_tone_inventory(): rebuilds it; returns the row count.
--     Run it with every zh pool refresh (TASK-1063) and after any zh sense backfill.
--   * calibration_zh_tone_variants(p_pronunciation, p_vocab_id): every valid tone
--     variant of a reading, in display (tone-marked) form, at most 16.
--   * two helpers both of the above use, so the parse and the re-marking exist once:
--     calibration_zh_parse_pinyin(text) and calibration_zh_mark_syllable(text, int).
--
-- THE RULE (ADR-060; Python reference services/placement_tones.variants, which
-- must return the same list for every pool reading: scripts/verify_zh_tone_variants.py)
--   * Parse the display form (calibration_display_pronunciation: the '(…)' numbered
--     part is dropped; the zh normaliser is not used). Tokens are split on
--     whitespace, ', - and ·. A token is a syllable when, in NFD and lower case, it
--     has at most one tone mark (U+0304, U+0301, U+030C, U+0300 -> tones 1-4; none
--     -> 5) and its letters are [a-z] with at most one ü (base keeps ü as 'u:').
--     Any other token (e.g. 'yíhuìr', two marks) is kept as written.
--   * Only full tones change, and only to full tones the inventory lists for the
--     base (the syllable's own tone always counts). A neutral syllable keeps its
--     tone and no syllable becomes neutral (optional neutral tones would make such
--     a variant arguably correct).
--   * No change on a syllable written 一 or 不, aligned by position when the
--     lemma's character count equals the syllable count.
--   * A combination whose only changes are tone 3 -> 2 before an (original) tone-3
--     syllable is a sandhi realisation and is excluded; so is the original.
--   * A variant never equals any reading of the same lemma (polyphones: 长 cháng
--     never yields zhǎng), compared on syllables and tones.
--   * Changed syllables are re-marked: the mark goes on a, else e, else the o of
--     "ou", else the last vowel (ü included); unchanged tokens and separators keep
--     their text. Cap 16, in the order md5(tone digits) then the digits: a fixed
--     pseudo-random order, so the 16 kept are a uniform-looking sample of all valid
--     variants. The item builder draws one uniformly (u_seed).
--
-- MEASURED (2026-11-19)
--   Local Postgres copy (live function bodies, all 11,977 native zh readings, a pool
--   sample): inventory 381 bases, 2.47 full tones per base (the research counted 382:
--   it also listed 'yihuir', a two-syllable token this parse keeps as a non-syllable);
--   scripts/verify_zh_tone_variants.py --all-readings: 10,390 readings, 94,712
--   variants, 0 mismatches with the Python reference, 0 unattested syllable+tone.
--   Live pool (read-only export, Python reference): 3,620 of 3,656 keys (99.0%) have
--   ≥ 1 variant, band 7 94.8%, bands 1-6 ≥ 98.4% (with the pool rows' own readings:
--   3,622, 99.1%, as tones/tone_cover_out.txt). Typical call 2-7 ms; the longest
--   reading (9 syllables, 62k combinations) about 0.3 s.
--
-- SECURITY
--   Table: RLS on, no policy, no client privilege. Functions: SET search_path,
--   EXECUTE for service_role only. The refresh is SECURITY DEFINER (it writes the
--   table); the rest are SECURITY INVOKER.
--
-- SIZE: ≈ 382 rows, ≈ 15 KB (tech §13).
--
-- VERIFY (read-only, after apply)
--   SELECT count(*), round(avg(cardinality(tones)), 2) FROM calibration_zh_tone_inventory;
--   -- ≈ 382 rows, ≈ 2.47 tones per base
--   SELECT calibration_zh_tone_variants('hěn hǎo', v.id) FROM dim_vocabulary v
--    WHERE v.lemma = '很好' AND v.language_id = 1;   -- never 'hén hǎo'
--   python scripts/verify_zh_tone_variants.py           -- 0 mismatches, coverage per band
--
-- ROLLBACK: calibration_zh_tones_rollback.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.calibration_zh_tone_inventory (
    base     text PRIMARY KEY,               -- toneless syllable, lower case, ü as 'u:'
    tones    smallint[] NOT NULL
             CHECK (tones <@ ARRAY[1, 2, 3, 4]::smallint[]),   -- attested full tones
    built_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.calibration_zh_tone_inventory ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.calibration_zh_tone_inventory FROM PUBLIC, anon, authenticated;

COMMENT ON TABLE public.calibration_zh_tone_inventory IS
  'TASK-1092 / ADR-060: toneless pinyin syllable (ü as u:) -> the full tones 1-4 it carries in native zh dim_word_senses readings. A tone variant may only use a syllable+tone listed here. Rebuilt by calibration_refresh_zh_tone_inventory().';


-- -----------------------------------------------------------------------------
-- Helpers
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_zh_parse_pinyin(p_pronunciation text)
RETURNS TABLE(ord integer, token text, is_sep boolean, base text, tone smallint)
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
SET search_path = public, pg_temp
AS $function$
    -- The display form split into tokens and separators, in order. For a token:
    -- base = toneless letters (ü as 'u:') and tone 1-4 / 5 when it is one pinyin
    -- syllable; base NULL and tone 0 otherwise. Separators: base NULL, tone NULL.
    -- Mirror: services/placement_tones.segments / parse_syllable.
    SELECT t.ord::integer,
           t.tok,
           t.sep,
           CASE WHEN t.ok THEN t.bare END,
           CASE WHEN t.sep THEN NULL
                WHEN NOT t.ok THEN 0
                WHEN t.marks = '' THEN 5
                WHEN t.marks = chr(772) THEN 1   -- U+0304 macron
                WHEN t.marks = chr(769) THEN 2   -- U+0301 acute
                WHEN t.marks = chr(780) THEN 3   -- U+030C caron
                ELSE 4                           -- U+0300 grave
           END::smallint
      FROM (
        SELECT m.ord, m.tok, m.sep, m.marks, m.bare,
               (NOT m.sep AND length(m.marks) <= 1 AND m.bare <> ''
                AND m.bare ~ '^[a-z]*(u:)?[a-z]*$') AS ok
          FROM (
            SELECT x.ord,
                   x.r[1] AS tok,
                   x.r[1] ~ '^[\s''·-]+$' AS sep,
                   regexp_replace(normalize(lower(x.r[1]), NFD), '[^\u0300\u0301\u0304\u030c]', '', 'g') AS marks,
                   regexp_replace(regexp_replace(normalize(lower(x.r[1]), NFD),
                       '[\u0300\u0301\u0304\u030c]', '', 'g'), '\u0308', ':', 'g') AS bare
              FROM regexp_matches(
                       normalize(public.calibration_display_pronunciation(p_pronunciation, 1::smallint), NFC),
                       '[\s''·-]+|[^\s''·-]+', 'g') WITH ORDINALITY AS x(r, ord)
          ) m
      ) t;
$function$;

COMMENT ON FUNCTION public.calibration_zh_parse_pinyin(text) IS
  'TASK-1092: a zh reading''s display form as (ord, token, is_sep, base, tone). base: toneless syllable, ü as u:; tone 1-4 from the mark, 5 unmarked; base NULL and tone 0 for a token that is not one pinyin syllable. Mirror: services/placement_tones.';

REVOKE ALL ON FUNCTION public.calibration_zh_parse_pinyin(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_zh_parse_pinyin(text) TO service_role;


CREATE OR REPLACE FUNCTION public.calibration_zh_mark_syllable(p_base text, p_tone integer)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
SET search_path = public, pg_temp
AS $function$
    -- Toneless base (ü as 'u:') + tone -> tone-marked syllable, NFC. The mark goes
    -- on a, else e, else the o of "ou", else the last vowel (ü included); with no
    -- vowel (m, n, ng) on the first m or n. Tone 5 / 0 / NULL: no mark.
    -- Mirror: services/placement_tones.mark_syllable.
    SELECT CASE
               WHEN p_tone IS NULL OR p_tone NOT BETWEEN 1 AND 4 OR i.pos IS NULL THEN l.letters
               ELSE normalize(left(l.letters, i.pos)
                              || chr((ARRAY[772, 769, 780, 768])[p_tone])
                              || substr(l.letters, i.pos + 1), NFC)
           END
      FROM (SELECT replace(p_base, 'u:', 'ü') AS letters) l
     CROSS JOIN LATERAL (
        SELECT CASE
                   WHEN strpos(l.letters, 'a') > 0 THEN strpos(l.letters, 'a')
                   WHEN strpos(l.letters, 'e') > 0 THEN strpos(l.letters, 'e')
                   WHEN strpos(l.letters, 'ou') > 0 THEN strpos(l.letters, 'ou')
                   WHEN l.letters ~ '[iouü]' THEN length(substring(l.letters from '^(.*[iouü])'))
                   WHEN l.letters ~ '[mn]' THEN length(substring(l.letters from '^([^mn]*[mn])'))
               END AS pos
     ) i;
$function$;

COMMENT ON FUNCTION public.calibration_zh_mark_syllable(text, integer) IS
  'TASK-1092: toneless pinyin syllable (ü as u:) + tone 1-4 -> tone-marked syllable (a, else e, else o of ou, else the last vowel). Mirror: services/placement_tones.mark_syllable.';

REVOKE ALL ON FUNCTION public.calibration_zh_mark_syllable(text, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_zh_mark_syllable(text, integer) TO service_role;


-- -----------------------------------------------------------------------------
-- Inventory refresh
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_refresh_zh_tone_inventory()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $function$
DECLARE
    v_rows integer;
BEGIN
    -- One rebuild at a time (a second caller waits, then rebuilds again). Readers
    -- see the previous rows until this transaction commits.
    PERFORM pg_advisory_xact_lock(hashtext('calibration_refresh_zh_tone_inventory'));

    -- `WHERE true`: Supabase's pg_safeupdate rejects an unqualified DELETE issued
    -- through PostgREST (as in calibration_refresh_anchor_pool, TASK-778).
    DELETE FROM calibration_zh_tone_inventory WHERE true;

    INSERT INTO calibration_zh_tone_inventory (base, tones, built_at)
    SELECT p.base,
           coalesce(array_agg(DISTINCT p.tone ORDER BY p.tone)
                        FILTER (WHERE p.tone BETWEEN 1 AND 4),
                    ARRAY[]::smallint[]),
           now()
      FROM dim_word_senses s
     CROSS JOIN LATERAL calibration_zh_parse_pinyin(s.pronunciation) p
     WHERE s.word_language_id = 1
       AND s.definition_language_id = 1
       AND s.pronunciation IS NOT NULL
       AND p.base IS NOT NULL
     GROUP BY p.base;

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RETURN v_rows;
END;
$function$;

COMMENT ON FUNCTION public.calibration_refresh_zh_tone_inventory() IS
  'TASK-1092: rebuild calibration_zh_tone_inventory from the native zh readings of dim_word_senses (all levels and ranks); returns the row count. Idempotent. Run with every zh pool refresh (TASK-1063) and after a zh sense backfill.';

REVOKE ALL ON FUNCTION public.calibration_refresh_zh_tone_inventory() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_refresh_zh_tone_inventory() TO service_role;


-- -----------------------------------------------------------------------------
-- Tone variants
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_zh_tone_variants(
    p_pronunciation text,
    p_vocab_id      integer
)
RETURNS text[]
LANGUAGE sql
STABLE
PARALLEL SAFE
SET search_path = public, pg_temp
AS $function$
WITH RECURSIVE
seg AS (
    SELECT p.ord, p.token, p.is_sep, p.base, p.tone
      FROM calibration_zh_parse_pinyin(p_pronunciation) p
),
syl AS (                      -- the tokens, numbered 1..n
    SELECT row_number() OVER (ORDER BY seg.ord)::integer AS k,
           seg.ord, seg.token, seg.base, seg.tone
      FROM seg
     WHERE NOT seg.is_sep
),
hdr AS (
    SELECT count(*)::integer AS n,
           array_agg(syl.tone ORDER BY syl.k) AS orig,
           string_agg(coalesce(syl.base, '?' || lower(syl.token)), ' ' ORDER BY syl.k) AS frame,
           (SELECT v.lemma FROM dim_vocabulary v WHERE v.id = p_vocab_id) AS lemma
      FROM syl
),
opt AS (
    -- every syllable may keep its own tone ...
    SELECT syl.k, syl.tone AS t
      FROM syl
    UNION
    -- ... and a full-tone syllable not written 一/不 may take any other full tone
    -- attested for its base
    SELECT syl.k, a.t
      FROM syl
     CROSS JOIN hdr
      JOIN calibration_zh_tone_inventory inv ON inv.base = syl.base
     CROSS JOIN LATERAL unnest(inv.tones) AS a(t)
     WHERE syl.tone BETWEEN 1 AND 4
       AND a.t BETWEEN 1 AND 4
       AND NOT coalesce(char_length(hdr.lemma) = hdr.n
                        AND substr(hdr.lemma, syl.k, 1) IN ('一', '不'), false)
),
combo AS (
    -- real_change: some syllable changed in a way that is not 3 -> 2 before an
    -- original tone 3 (a combination with only such changes is a sandhi form)
    SELECT 0 AS k, ARRAY[]::smallint[] AS tones, false AS real_change
    UNION ALL
    SELECT c.k + 1,
           c.tones || o.t,
           c.real_change
           OR (o.t <> h.orig[c.k + 1]
               AND NOT (h.orig[c.k + 1] = 3 AND o.t = 2
                        AND c.k + 1 < h.n AND h.orig[c.k + 2] = 3))
      FROM combo c
     CROSS JOIN hdr h
      JOIN opt o ON o.k = c.k + 1
),
own AS (                      -- tone sequences of this lemma's readings on the same syllables
    SELECT o.tones
      FROM dim_word_senses s
     CROSS JOIN LATERAL (
        SELECT string_agg(coalesce(p.base, '?' || lower(p.token)), ' ' ORDER BY p.ord) AS frame,
               array_agg(p.tone ORDER BY p.ord) AS tones
          FROM calibration_zh_parse_pinyin(s.pronunciation) p
         WHERE NOT p.is_sep
     ) o
     WHERE s.vocab_id = p_vocab_id
       AND s.pronunciation IS NOT NULL
       AND o.frame = (SELECT hdr.frame FROM hdr)
),
pick AS (
    SELECT c.tones,
           row_number() OVER (ORDER BY md5(array_to_string(c.tones, '')),
                                       array_to_string(c.tones, '') COLLATE "C") AS rk
      FROM combo c
     CROSS JOIN hdr h
     WHERE h.n > 0
       AND c.k = h.n
       AND c.real_change
       AND NOT EXISTS (SELECT 1 FROM own WHERE own.tones = c.tones)
     ORDER BY rk
     LIMIT 16
)
SELECT coalesce(array_agg(r.txt ORDER BY r.rk), ARRAY[]::text[])
  FROM (
    SELECT pick.rk,
           normalize(string_agg(
               CASE WHEN seg.is_sep OR pick.tones[syl.k] = syl.tone THEN seg.token
                    ELSE calibration_zh_mark_syllable(syl.base, pick.tones[syl.k])
               END, '' ORDER BY seg.ord), NFC) AS txt
      FROM pick
     CROSS JOIN seg
      LEFT JOIN syl ON syl.ord = seg.ord
     GROUP BY pick.rk
  ) r;
$function$;

COMMENT ON FUNCTION public.calibration_zh_tone_variants(text, integer) IS
  'TASK-1092 / ADR-060 rule 4: every valid tone variant of a zh reading in display form (same syllables, other attested full tones; neutral and 一/不 syllables kept; 3->2-before-3-only sandhi forms and readings of p_vocab_id excluded), at most 16, ordered by md5 of the tone digits. Must equal services/placement_tones.variants (scripts/verify_zh_tone_variants.py).';

REVOKE ALL ON FUNCTION public.calibration_zh_tone_variants(text, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.calibration_zh_tone_variants(text, integer) TO service_role;


-- -----------------------------------------------------------------------------
-- First fill
-- -----------------------------------------------------------------------------
SELECT public.calibration_refresh_zh_tone_inventory();
