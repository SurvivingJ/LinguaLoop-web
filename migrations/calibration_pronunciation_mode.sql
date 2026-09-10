-- Calibration Phase 3 — pronunciation mode.
-- =============================================================================
-- PROBLEM
--   The definition mode asks "what does this word mean?". The pronunciation mode
--   asks "how is this word read?", and that is a DIFFERENT DISTRACTOR PROBLEM,
--   not a display variant of the same one. semantic_distractors() is useless
--   here: two readings that mean unrelated things can be one keystroke apart, and
--   two readings of near-identical meaning can be nothing alike. What makes a
--   reading a good foil is that it is confusable to eye and ear.
--
-- FIX
--   pronunciation_distractors(): the nearest OTHER readings by edit distance over
--   a per-language normalised form, preferring the same syllable count and a
--   similar frequency, and rejecting exact homophones outright.
--
-- FOUR THINGS THAT MAKE OR BREAK THIS
--
--   1. HOMOPHONES ARE EXCLUDED, NOT RANKED LOW.
--      A word with the identical reading is a SECOND CORRECT ANSWER. 张 and 章 are
--      both zhang1; offering both makes the item unanswerable. Distance 0 is
--      dropped, which is the pronunciation-mode counterpart of the vocab_id
--      sibling exclusion in ADR-025.
--
--   2. TONE IS PART OF THE READING, AND IS KEPT.
--      zh is stored as 'yìng yòng (ying4 yong4)'. The parenthesised numbered form
--      is canonical (lexicon.py:266) and its tone digits are retained for
--      comparison, so bǎ fēng and bā fēng are one edit apart — a tone minimal pair,
--      which is precisely the thing worth testing. Note this differs from the L1
--      listening exercise, where tone-only pairs are INVALID because TTS renders
--      one of them; here the learner reads the options, so tone is visible and
--      testable.
--
--   3. THE DISTANCE CAP SCALES WITH LENGTH.
--      Confusability is relative. A fixed 3-edit cap left 13% of zh items with
--      ZERO options, all of them four-syllable words: 'pin2fu4cha1ju4' is 14
--      characters and has no neighbour within 3 edits. Scaling to
--      max(3, ceil(len * 0.45)) took zh from 19 empty and 25 short (of 150) to
--      0 empty and 2 short, without touching the short readings, which keep the
--      strict absolute limit because the larger of the two caps wins.
--
--   4. SAME SYLLABLE COUNT IS PREFERRED.
--      A reading with a different number of syllables is a different SHAPE on the
--      page and can be discarded without knowing the word. Preferred rather than
--      required, so a rare word with no same-length neighbour still gets options
--      instead of none.
--
-- WHERE THIS MODE DOES NOT WORK, AND WHY IT IS REFUSED RATHER THAN DEGRADED
--   Readings are stored on only a fraction of senses, and only on the NATIVE row:
--
--       word/def   senses   with a reading
--       zh/zh       4,282    4,217
--       zh/en       3,914        0
--       zh/ja       3,914        0
--       en/en       6,555       21     <-- 0.3%
--       ja/zh       3,563        0
--       ja/en       3,563        0
--       ja/ja       3,563    2,385
--
--   Two consequences, both load-bearing:
--     * The session's definition language is IGNORED in this mode and the native
--       row is used instead. Honouring it would select a set that is empty by
--       construction, and the mode would appear broken rather than unavailable.
--     * ENGLISH IS REFUSED. 21 usable senses cannot support a calibration run, so
--       the route rejects it and the UI disables the toggle. A disabled control
--       reads as a limitation; a control that silently produces nothing reads as
--       a bug.
--
-- SAFETY
--   - Additive: three new functions, one new column with a default, one index.
--     `mode` defaults to 'definition', so existing sessions are unaffected.
--   - Requires the fuzzystrmatch extension (levenshtein), installed into the
--     `extensions` schema. Additive and standard; pg_trgm was already present.
--   - calibration_next_anchor() gains a p_mode parameter with a default, and the
--     old 3-argument signature is dropped so no caller can silently get the old
--     behaviour from an overload.
--
-- APPLIED LIVE: 2026-09-08
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS fuzzystrmatch WITH SCHEMA extensions;


-- -----------------------------------------------------------------------------
-- 1. Normalisation. Two forms, deliberately: one to COMPARE with, one to SHOW.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calibration_normalise_pronunciation(
    p_pronunciation text,
    p_language_id   smallint
)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $function$
    SELECT CASE
        WHEN p_pronunciation IS NULL OR btrim(p_pronunciation) = '' THEN NULL
        WHEN p_language_id = 1 THEN
            lower(regexp_replace(
                coalesce(substring(p_pronunciation from '\(([^)]*)\)'), p_pronunciation),
                '\s+', '', 'g'))
        WHEN p_language_id = 3 THEN
            lower(regexp_replace(
                regexp_replace(normalize(p_pronunciation, NFC), '-.*$', ''),
                '\s+', '', 'g'))
        ELSE
            lower(regexp_replace(p_pronunciation, '\s+', '', 'g'))
    END;
$function$;

COMMENT ON FUNCTION public.calibration_normalise_pronunciation(text, smallint) IS
  'Canonical comparison form of a pronunciation, per language. zh prefers the parenthesised numbered pinyin and KEEPS tone digits (a tone-only difference is a legitimate minimal pair, not noise); ja strips the latin gloss suffix off loanword readings. Used by pronunciation_distractors() both to measure edit distance and to reject homophones, which would otherwise be a second correct answer.';


CREATE OR REPLACE FUNCTION public.calibration_display_pronunciation(
    p_pronunciation text,
    p_language_id   smallint
)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $function$
    SELECT CASE
        WHEN p_pronunciation IS NULL OR btrim(p_pronunciation) = '' THEN NULL
        WHEN p_language_id = 1 THEN
            btrim(regexp_replace(p_pronunciation, '\s*\([^)]*\)\s*', '', 'g'))
        WHEN p_language_id = 3 THEN
            btrim(regexp_replace(normalize(p_pronunciation, NFC), '-.*$', ''))
        ELSE btrim(p_pronunciation)
    END;
$function$;

COMMENT ON FUNCTION public.calibration_display_pronunciation(text, smallint) IS
  'What a pronunciation option should LOOK like. Distinct from calibration_normalise_pronunciation, which is the comparison key: zh keeps tone digits for comparison but shows only the diacritic form, because displaying the numbered form would hand the learner the tone the item is testing. ja drops the latin gloss suffix, which otherwise made one option visibly a different shape from the others - a format tell usable without knowing the word.';


CREATE OR REPLACE FUNCTION public.calibration_syllable_count(
    p_normalised text,
    p_language_id smallint
)
RETURNS integer
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $function$
    SELECT CASE
        WHEN p_normalised IS NULL OR p_normalised = '' THEN 0
        -- zh normalised form is numbered pinyin: exactly one tone digit per
        -- syllable, so counting digits counts syllables.
        WHEN p_language_id = 1 THEN
            coalesce(length(regexp_replace(p_normalised, '[^1-5]', '', 'g')), 0)
        -- ja is kana; small kana do not start a mora, so this is a mora count
        -- rather than a character count.
        WHEN p_language_id = 3 THEN
            greatest(length(regexp_replace(
                p_normalised, '[ゃゅょャュョぁぃぅぇぉァィゥェォ]', '', 'g')), 0)
        ELSE length(p_normalised)
    END;
$function$;


-- -----------------------------------------------------------------------------
-- 2. The picker
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.pronunciation_distractors(
    p_sense_id         integer,
    p_word_language_id smallint,
    p_count            integer DEFAULT 3,
    p_max_distance     integer DEFAULT 3,
    p_max_ratio        real    DEFAULT 0.45
)
RETURNS TABLE(
    out_sense_id      integer,
    out_vocab_id      integer,
    out_lemma         text,
    out_pronunciation text,
    out_distance      integer,
    out_frequency     real
)
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path TO 'public', 'extensions', 'pg_temp'
AS $function$
DECLARE
    v_vocab_id integer;
    v_norm     text;
    v_zipf     real;
    v_len      integer;
    v_max      integer;
    v_syl      integer;
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    SELECT s.vocab_id,
           calibration_normalise_pronunciation(s.pronunciation, p_word_language_id),
           v.frequency_rank
      INTO v_vocab_id, v_norm, v_zipf
      FROM dim_word_senses s
      JOIN dim_vocabulary v ON v.id = s.vocab_id
     WHERE s.id = p_sense_id;

    IF v_norm IS NULL THEN
        RETURN;
    END IF;
    v_len := length(v_norm);
    v_syl := calibration_syllable_count(v_norm, p_word_language_id);

    -- Scales with length; see point 3 in the header. Whichever cap is larger wins,
    -- so short readings keep the strict absolute limit.
    v_max := GREATEST(p_max_distance, ceil(v_len * p_max_ratio)::integer);

    RETURN QUERY
    WITH candidates AS (
        -- No LIMIT on purpose: only ~2.4k (ja) to 4.2k (zh) senses carry a reading,
        -- and the length prefilter cuts that further, so the whole space is
        -- searched. An arbitrary LIMIT before ORDER BY would silently discard the
        -- nearest neighbours, which are the only ones worth having.
        SELECT s.id, s.vocab_id, v.lemma, s.pronunciation, v.frequency_rank,
               calibration_normalise_pronunciation(s.pronunciation, p_word_language_id) AS norm
          FROM dim_word_senses s
          JOIN dim_vocabulary v ON v.id = s.vocab_id
         WHERE s.word_language_id = p_word_language_id
           AND s.definition_level = 'standard'
           AND s.pronunciation IS NOT NULL
           AND s.vocab_id <> v_vocab_id
           -- Edit distance is at least the length difference, so this excludes
           -- hopeless candidates before the expensive comparison.
           AND length(calibration_normalise_pronunciation(s.pronunciation, p_word_language_id))
               BETWEEN v_len - v_max AND v_len + v_max
    ),
    scored AS (
        SELECT c.*,
               extensions.levenshtein(c.norm, v_norm) AS dist,
               (calibration_syllable_count(c.norm, p_word_language_id) <> v_syl)::int AS syl_mismatch
          FROM candidates c
         WHERE c.norm IS NOT NULL
           -- LOAD-BEARING: a true homophone is a SECOND CORRECT ANSWER, not a
           -- distractor. 张 and 章 are both zhang1; showing both makes the item
           -- unanswerable. Distance 0 is excluded outright rather than ranked low.
           AND c.norm <> v_norm
    ),
    per_word AS (
        SELECT DISTINCT ON (s.vocab_id) s.*
          FROM scored s
         WHERE s.dist <= v_max
         ORDER BY s.vocab_id, s.syl_mismatch, s.dist,
                  abs(coalesce(s.frequency_rank, 0) - coalesce(v_zipf, 0))
    ),
    per_reading AS (
        -- Two different words can share a reading that differs from the anchor's.
        -- Showing it twice wastes an option slot and looks like a bug.
        SELECT DISTINCT ON (w.norm) w.*
          FROM per_word w
         ORDER BY w.norm, w.syl_mismatch, w.dist,
                  abs(coalesce(w.frequency_rank, 0) - coalesce(v_zipf, 0))
    )
    SELECT r.id, r.vocab_id, r.lemma,
           calibration_display_pronunciation(r.pronunciation, p_word_language_id),
           r.dist, r.frequency_rank
      FROM per_reading r
     -- Same syllable count FIRST (see point 4), then nearest relative to length,
     -- then frequency-matched.
     ORDER BY r.syl_mismatch,
              r.dist::real / GREATEST(v_len, 1),
              abs(coalesce(r.frequency_rank, 0) - coalesce(v_zipf, 0)), random()
     LIMIT GREATEST(p_count, 1);
END;
$function$;

REVOKE EXECUTE ON FUNCTION public.pronunciation_distractors(integer, smallint, integer, integer, real) FROM anon;
GRANT EXECUTE ON FUNCTION public.pronunciation_distractors(integer, smallint, integer, integer, real)
    TO authenticated, service_role;

CREATE INDEX IF NOT EXISTS idx_dim_word_senses_pronunciation_lookup
    ON public.dim_word_senses (word_language_id, definition_level)
    WHERE pronunciation IS NOT NULL;


-- -----------------------------------------------------------------------------
-- 3. Sessions carry a mode, and anchor selection respects it
-- -----------------------------------------------------------------------------
ALTER TABLE public.calibration_sessions
  ADD COLUMN IF NOT EXISTS mode text NOT NULL DEFAULT 'definition';

DO $do$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.calibration_sessions'::regclass
          AND conname = 'calibration_sessions_mode_chk'
    ) THEN
        ALTER TABLE public.calibration_sessions
          ADD CONSTRAINT calibration_sessions_mode_chk
          CHECK (mode IN ('definition', 'pronunciation'));
    END IF;
END
$do$;

COMMENT ON COLUMN public.calibration_sessions.mode IS
  'definition = four meanings, one right (semantic_distractors). pronunciation = four readings, one right (pronunciation_distractors). Different distractor problems entirely: semantic nearness vs audio/orthographic confusability. In pronunciation mode definition_language_id is IGNORED, because readings live only on the native (word language = definition language) sense row.';

CREATE OR REPLACE FUNCTION public.calibration_next_anchor(
    p_session_id             uuid,
    p_word_language_id       smallint,
    p_definition_language_id smallint,
    p_mode                   text DEFAULT 'definition'
)
RETURNS TABLE(
    out_sense_id      integer,
    out_vocab_id      integer,
    out_lemma         text,
    out_definition    text,
    out_pronunciation text,
    out_zipf          real,
    out_zipf_band     smallint
)
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_target_band smallint;
    v_def_lang    smallint;
    v_need_pron   boolean := (p_mode = 'pronunciation');
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    -- Readings are stored ONLY on the native row: every cross-language gloss row
    -- has pronunciation NULL (verified 2026-09-08 — zh/en, zh/ja, ja/zh, ja/en all
    -- have exactly 0). So in pronunciation mode the session's definition language
    -- is irrelevant and would select an empty set if honoured.
    v_def_lang := CASE WHEN v_need_pron THEN p_word_language_id
                       ELSE p_definition_language_id END;

    SELECT b.band INTO v_target_band
    FROM (SELECT generate_series(1, 7)::smallint AS band) b
    LEFT JOIN (
        SELECT zipf_band, count(*) AS served
        FROM calibration_responses
        WHERE session_id = p_session_id
        GROUP BY zipf_band
    ) r ON r.zipf_band = b.band
    WHERE EXISTS (
        SELECT 1
        FROM dim_word_senses s
        JOIN dim_vocabulary v ON v.id = s.vocab_id
        WHERE s.word_language_id       = p_word_language_id
          AND s.definition_language_id = v_def_lang
          AND s.definition_level = 'standard'
          AND (NOT v_need_pron OR (s.pronunciation IS NOT NULL AND btrim(s.pronunciation) <> ''))
          AND (v_need_pron OR s.embedding IS NOT NULL)
          AND v.frequency_rank IS NOT NULL
          AND calibration_zipf_band(v.frequency_rank) = b.band
          AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl WHERE bl.sense_id = s.id)
          AND NOT EXISTS (SELECT 1 FROM calibration_responses cr
                           WHERE cr.session_id = p_session_id AND cr.anchor_sense_id = s.id)
    )
    ORDER BY coalesce(r.served, 0), random()
    LIMIT 1;

    IF v_target_band IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT s.id, s.vocab_id, v.lemma, s.definition,
           calibration_display_pronunciation(s.pronunciation, p_word_language_id),
           v.frequency_rank, calibration_zipf_band(v.frequency_rank)
      FROM dim_word_senses s
      JOIN dim_vocabulary v ON v.id = s.vocab_id
     WHERE s.word_language_id       = p_word_language_id
       AND s.definition_language_id = v_def_lang
       AND s.definition_level = 'standard'
       AND (NOT v_need_pron OR (s.pronunciation IS NOT NULL AND btrim(s.pronunciation) <> ''))
       AND (v_need_pron OR s.embedding IS NOT NULL)
       AND v.frequency_rank IS NOT NULL
       AND calibration_zipf_band(v.frequency_rank) = v_target_band
       AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl WHERE bl.sense_id = s.id)
       AND NOT EXISTS (SELECT 1 FROM calibration_responses cr
                        WHERE cr.session_id = p_session_id AND cr.anchor_sense_id = s.id)
     ORDER BY random()
     LIMIT 1;
END;
$function$;

-- The 3-argument signature is DROPPED, not left as an overload: an overload would
-- let a stale caller keep the old definition-only behaviour silently.
DROP FUNCTION IF EXISTS public.calibration_next_anchor(uuid, smallint, smallint);

GRANT EXECUTE ON FUNCTION public.calibration_next_anchor(uuid, smallint, smallint, text)
    TO authenticated, service_role;


-- =============================================================================
-- Verification
-- =============================================================================
-- Sampled 150 items per language and READ them (the harness is ad hoc; the
-- semantic equivalent is scripts/dump_calibration_distractors.py). 2026-09-08:
--
--   zh  items=150  short=2  empty=0  sibling leaks=0  format tells=0  duplicates=0
--   ja  items=150  short=7  empty=4  sibling leaks=0  format tells=0  duplicates=0
--
-- Examples worth keeping, because they are what "confusable" should look like:
--   政治 せいじ   vs せいふ / だいじ / せいぶ
--   旋律 せんりつ vs だんぜつ / せいりつ / そんりつ
--   国际 guó jì  vs luó jí / gū jì / guó jí        <- tone minimal pairs
--   提案 tí àn   vs tí wèn / dá àn  / tú àn
--
-- No returned reading may equal the anchor's (the homophone rule):
--   SELECT count(*) FROM pronunciation_distractors(36371, 3::smallint, 10) d
--    WHERE calibration_normalise_pronunciation(d.out_pronunciation, 3::smallint)
--        = calibration_normalise_pronunciation(
--            (SELECT pronunciation FROM dim_word_senses WHERE id = 36371), 3::smallint);
--   -- expect 0
--
-- English is refused rather than degraded — it has 21 usable senses:
--   SELECT count(*) FROM dim_word_senses
--    WHERE word_language_id = 2 AND definition_level = 'standard'
--      AND pronunciation IS NOT NULL;      -- 21, hence the route-level refusal
-- =============================================================================
