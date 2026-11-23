-- =============================================================================
-- TASK-1075 (vocab-placement rule 3b): Japanese wrong readings must fit the kana visible in the word.
-- 91 of 488 ja kanji+kana reading anchors (19%) were answerable by kana matching alone (tech §0 E10).
-- Signature unchanged. Supersedes the definition in calibration_pronunciation_mode.sql (a multi-object
-- file, kept per migrations/CLAUDE.md). Existing cache rows are not changed: TASK-1075 deletes and refills
-- the ja anchors with fewer than 3 consistent cached foils. Owner-applied.
-- Rollback: pronunciation_distractors_ja_kana_pattern_rollback.sql.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.pronunciation_distractors(p_sense_id integer, p_word_language_id smallint, p_count integer DEFAULT 3, p_max_distance integer DEFAULT 3, p_max_ratio real DEFAULT 0.45)
 RETURNS TABLE(out_sense_id integer, out_vocab_id integer, out_lemma text, out_pronunciation text, out_distance integer, out_frequency real)
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
    v_lemma    text;
    v_kana_re  text;      -- TASK-1075 rule 3b: the anchor's visible-kana pattern (ja only)
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    SELECT s.vocab_id,
           calibration_normalise_pronunciation(s.pronunciation, p_word_language_id),
           v.frequency_rank,
           v.lemma
      INTO v_vocab_id, v_norm, v_zipf, v_lemma
      FROM dim_word_senses s
      JOIN dim_vocabulary v ON v.id = s.vocab_id
     WHERE s.id = p_sense_id;

    IF v_norm IS NULL THEN
        RETURN;
    END IF;
    v_len := length(v_norm);
    v_syl := calibration_syllable_count(v_norm, p_word_language_id);

    -- The distance cap SCALES WITH LENGTH, and that is not a convenience.
    -- Confusability is relative: 'sui4' against 'hui4' differs by a quarter of the
    -- string and is a genuine minimal pair, while 'pin2fu4cha1ju4' (14 chars) has
    -- no neighbour at all within 3 edits — a fixed cap left 13% of zh items with
    -- ZERO options, concentrated entirely in the four-syllable words. Whichever
    -- cap is larger wins, so short readings keep the strict absolute limit.
    v_max := GREATEST(p_max_distance, ceil(v_len * p_max_ratio)::integer);

    -- TASK-1075 (vocab-placement rule 3b, E10): a wrong reading that contradicts the kana already visible in
    -- the word (考え かんがえ vs かんがい) is answerable by matching the kana, not by knowing the word. For a
    -- Japanese lemma that contains hiragana, keep only candidates whose reading fits the lemma's visible-kana
    -- pattern: every non-hiragana run of the lemma becomes '.+'. The kana are literal (no regex metacharacters).
    IF p_word_language_id = 3 AND v_lemma ~ '[ぁ-ゟ]' THEN
        v_kana_re := '^' || regexp_replace(v_lemma, '[^ぁ-ゟー]+', '.+', 'g') || '$';
    END IF;

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
           AND (v_kana_re IS NULL OR c.norm ~ v_kana_re)
    ),
    per_word AS (
        SELECT DISTINCT ON (s.vocab_id) s.*
          FROM scored s
         WHERE s.dist <= v_max
         ORDER BY s.vocab_id, s.syl_mismatch, s.dist,
                  abs(coalesce(s.frequency_rank, 0) - coalesce(v_zipf, 0))
    ),
    per_reading AS (
        SELECT DISTINCT ON (w.norm) w.*
          FROM per_word w
         ORDER BY w.norm, w.syl_mismatch, w.dist,
                  abs(coalesce(w.frequency_rank, 0) - coalesce(v_zipf, 0))
    )
    SELECT r.id, r.vocab_id, r.lemma,
           calibration_display_pronunciation(r.pronunciation, p_word_language_id),
           r.dist, r.frequency_rank
      FROM per_reading r
     -- Same syllable count FIRST: a reading with a different number of syllables
     -- is a different shape on the page and is discardable without knowing the
     -- word. Only then nearest relative to length, then frequency-matched. A
     -- preference, not a filter, so a rare word with no same-length neighbour
     -- still gets options rather than none.
     ORDER BY r.syl_mismatch,
              r.dist::real / GREATEST(v_len, 1),
              abs(coalesce(r.frequency_rank, 0) - coalesce(v_zipf, 0)), random()
     LIMIT GREATEST(p_count, 1);
END;
$function$;

-- Live ACL on 2026-11-19 is service_role only (security migrations); kept.
REVOKE ALL ON FUNCTION public.pronunciation_distractors(integer, smallint, integer, integer, real) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.pronunciation_distractors(integer, smallint, integer, integer, real) TO service_role;
