-- =============================================================================
-- calibration_placement_rpcs.sql  (TASK-1077, vocabulary placement SQL; ADR-057, ADR-060)
-- =============================================================================
-- The five functions of wiki/features/vocab-placement.tech.md §14 plus the helpers
-- they share. Python (services/calibration_placement.py, TASK-1080) chooses the
-- band and the random draws; SQL picks the word, builds the item, grades and
-- returns the tallies, in ONE round trip per answer.
--
--   calibration_placement_ready_counts(L, D)                 launch gate (tech §2)
--   calibration_placement_next_item(user, session, band, exclude_days)
--   calibration_placement_answer(user, session, response, position, latency,
--                                next_band, draws)
--   calibration_placement_close(user, session, reason)
--   calibration_placement_close_stale(user | NULL, older_than)
--
-- Item rules (tech §2): rank-1 senses only; no reading on meaning items; reading
-- foils with the key's DISPLAY syllable (zh) or mora (ja) count; ja foils match the
-- lemma's visible kana (3b); zh reading items are two tone pairs K, K', F, F' (rule
-- 4, ADR-060) with K' and F' from calibration_zh_tone_variants (TASK-1092,
-- migrations/calibration_zh_tones.sql); cross-CJK definitions lose their leading
-- equivalent word and anchors still answerable by matching are not served (rule 5).
--
-- Behaviour beyond the letter of tech §14 (each is reported with the task):
--   * next_item re-sends the session's pending unanswered item instead of drawing a
--     second one (tech §14 "used ... on resume"; at most one pending row per
--     session). The re-sent payload carries "resent": true.
--   * recheck probes (tech §3): at the start of a session (no rows yet) next_item
--     serves a recheck when the learner has an eligible credited reading, and after
--     a recheck answer, a second one, before any scored item; budget 2.
--   * rule 5 strips a second, dash-ended equivalent ("迅速；急速 —— …"): 226 ja/zh
--     keys have this double prefix (live, 2026-11-19).
--   * meaning options: the first 3 cached foils whose stripped text differs from the
--     stripped key and from each other (the check compares raw text only).
--   * zh F and F' (and ja foils) never equal any reading of the prompt lemma.
--   * sound_pair probe rows have instrument NULL (no instrument value fits them).
--
-- Never sent to a client: key_position, option_sense_ids, option_roles, the key's
-- sense id, the reading on a meaning item. Reveals show the key only after the word
-- is complete. Probe decisions use p_draws only (no random() for probes).
--
-- Errors: P0002 = session not found (missing, another user's, or not a placement;
-- Flask maps it to 404). 22023 = session closed, already answered, invalid
-- position / band / draws / reason, or a response not in this session.
--
-- Security: every function SET search_path; REVOKE ALL FROM PUBLIC, anon,
-- authenticated; GRANT EXECUTE TO service_role. The four writers are SECURITY
-- DEFINER and check that p_user_id owns the session.
--
-- REQUIRES: calibration_placement.sql (TASK-1076) and calibration_zh_tones.sql
-- (TASK-1092) applied first; this file refuses to run otherwise.
-- Idempotent (CREATE OR REPLACE). REQUIRES USER APPROVAL TO APPLY LIVE.
-- Rollback: migrations/calibration_placement_rpcs_rollback.sql.
-- Read-only checks after apply: tests/sql/check_calibration_placement.sql and
-- scripts/verify_placement_rpcs.py (owner-run, test account).
-- =============================================================================

BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'public' AND table_name = 'calibration_responses'
                    AND column_name = 'option_roles') THEN
    RAISE EXCEPTION 'apply migrations/calibration_placement.sql (TASK-1076) first';
  END IF;
  IF to_regprocedure('public.calibration_zh_tone_variants(text,integer)') IS NULL THEN
    RAISE EXCEPTION 'apply migrations/calibration_zh_tones.sql (TASK-1092) first';
  END IF;
END $$;

-- =============================================================================
-- Pure helpers (IMMUTABLE)
-- =============================================================================

-- Rule 5: strip the leading equivalent word of a cross-CJK definition (zh/ja, ja/zh).
-- Pass 1 is tech §2's regex; pass 2 removes a second, dash-ended equivalent left by a
-- double prefix ("迅速；急速 —— 速度非常快" -> "速度非常快"). Other pairs: btrim only
-- (an English "to go; to leave" must not lose its first gloss).
CREATE OR REPLACE FUNCTION public.calibration_placement_strip_definition(
    p_text text, p_word_language_id smallint, p_definition_language_id smallint)
RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE
SET search_path = public, pg_temp
AS $$
    SELECT CASE
        WHEN p_text IS NULL THEN NULL
        WHEN (p_word_language_id, p_definition_language_id) IN ((1, 3), (3, 1)) THEN
            btrim(regexp_replace(
                regexp_replace(p_text, '^\s*[^；;—]{1,12}\s*(；|;|——|—)\s*', ''),
                '^\s*[^；;—]{1,12}\s*(——|—)\s*', ''))
        ELSE btrim(p_text)
    END;
$$;

-- Reading-exempt words: ja kana-only lemmas and every en word (tech §2 table).
CREATE OR REPLACE FUNCTION public.calibration_placement_reading_exempt(
    p_lemma text, p_word_language_id smallint)
RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE
SET search_path = public, pg_temp
AS $$
    SELECT CASE
        WHEN p_word_language_id = 1 THEN false
        WHEN p_word_language_id = 3 THEN coalesce(p_lemma ~ '^[ぁ-ゟァ-ヿー・]+$', false)
        ELSE true
    END;
$$;

-- Rule 3 length on the DISPLAY form: zh = space-separated syllables; ja = kana minus
-- small kana (ゃゅょぁぃぅぇぉっ and katakana equivalents, as tech §2 lists them).
CREATE OR REPLACE FUNCTION public.calibration_placement_units(
    p_text text, p_word_language_id smallint)
RETURNS integer
LANGUAGE sql IMMUTABLE PARALLEL SAFE
SET search_path = public, pg_temp
AS $$
    SELECT CASE
        WHEN p_text IS NULL OR btrim(p_text) = '' THEN 0
        WHEN p_word_language_id = 1 THEN cardinality(regexp_split_to_array(btrim(p_text), '\s+'))
        WHEN p_word_language_id = 3 THEN
            char_length(regexp_replace(btrim(p_text), '[ゃゅょぁぃぅぇぉっャュョァィゥェォッ]', '', 'g'))
        ELSE char_length(btrim(p_text))
    END;
$$;

-- Rule 4: the diacritic-stripped pinyin (F must differ from K here).
CREATE OR REPLACE FUNCTION public.calibration_placement_toneless(p_text text)
RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE
SET search_path = public, pg_temp
AS $$
    SELECT translate(lower(normalize(p_text, NFC)),
                     'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü', 'aaaaeeeeiiiioooouuuuvvvvv');
$$;

-- Rule 3b: the lemma's visible-kana pattern (考え -> ^.+え$).
CREATE OR REPLACE FUNCTION public.calibration_placement_kana_pattern(p_lemma text)
RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE
SET search_path = public, pg_temp
AS $$
    SELECT '^' || regexp_replace(p_lemma, '[^ぁ-ゟー]+', '.+', 'g') || '$';
$$;

-- A reading the item may use as a key: zh tone-marked pinyin syllables with at least
-- one mark (the 9-10 unmarked function words are not reading-ready); ja kana only
-- (rows with romaji or kanji are data errors, tech §2).
CREATE OR REPLACE FUNCTION public.calibration_placement_well_formed_reading(
    p_text text, p_word_language_id smallint)
RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE
SET search_path = public, pg_temp
AS $$
    SELECT CASE
        WHEN p_text IS NULL THEN false
        WHEN p_word_language_id = 1 THEN
            p_text ~ '^[a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]+( [a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]+)*$'
            AND p_text ~ '[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]'
        WHEN p_word_language_id = 3 THEN p_text ~ '^[ぁ-ゟァ-ヿー・]+$'
        ELSE false
    END;
$$;

-- ja special-mora / voicing skeleton (research Q3): NFD, drop dakuten, handakuten,
-- っ, ん, ー, う, い. Equal skeletons + different strings = a sound_pair candidate.
CREATE OR REPLACE FUNCTION public.calibration_placement_mora_skeleton(p_text text)
RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE
SET search_path = public, pg_temp
AS $$
    SELECT regexp_replace(normalize(p_text, NFD), U&'[\3099\309Aっんーうい]', '', 'g');
$$;

-- A deterministic uniform in [0, 1) from one injected draw and a tag, so one u_seed
-- drives every choice of an item without calling random().
CREATE OR REPLACE FUNCTION public.calibration_placement_unit(p_seed double precision, p_tag text)
RETURNS double precision
LANGUAGE sql IMMUTABLE PARALLEL SAFE
SET search_path = public, pg_temp
AS $$
    SELECT (('x' || substr(md5(coalesce(p_seed, 0)::text || '|' || p_tag), 1, 13))::bit(52)::bigint)::double precision
           / 4503599627370496.0;
$$;

-- =============================================================================
-- Item parts (STABLE)
-- =============================================================================

-- Meaning item (tech §2 rules 1, 2, 5): key + the first 3 cached definition foils,
-- all stripped, canonical order (key first). status: ok | no_key | few_foils | rule5.
CREATE OR REPLACE FUNCTION public.calibration_placement_meaning_parts(
    p_anchor_sense_id integer, p_word_language_id smallint, p_definition_language_id smallint,
    p_lemma text, p_key text,
    OUT status text, OUT sense_ids integer[], OUT texts text[])
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    WITH k AS (
        SELECT calibration_placement_strip_definition(p_key, p_word_language_id,
                                                      p_definition_language_id) AS kt
    ),
    f AS (
        SELECT DISTINCT ON (x.t) o.sense_id, x.t, o.rank
          FROM calibration_cached_options('definition', p_anchor_sense_id) o
         CROSS JOIN LATERAL (SELECT calibration_placement_strip_definition(
                                 o.option_text, p_word_language_id, p_definition_language_id) AS t) x
         CROSS JOIN k
         WHERE x.t <> '' AND x.t IS DISTINCT FROM k.kt AND o.sense_id <> p_anchor_sense_id
         ORDER BY x.t, o.rank
    ),
    f3 AS (SELECT * FROM f ORDER BY rank, sense_id LIMIT 3),
    agg AS (
        SELECT count(*) AS n,
               array_agg(sense_id ORDER BY rank, sense_id) AS ids,
               array_agg(t ORDER BY rank, sense_id) AS ts,
               coalesce(bool_or(strpos(t, p_lemma) > 0), false) AS foil_has_lemma
          FROM f3
    ),
    st AS (
        SELECT CASE
                   WHEN coalesce(k.kt, '') = '' THEN 'no_key'
                   WHEN agg.n < 3 THEN 'few_foils'
                   WHEN (p_word_language_id, p_definition_language_id) IN ((1, 3), (3, 1))
                        AND char_length(p_lemma) >= 2 AND strpos(k.kt, p_lemma) > 0
                        AND NOT agg.foil_has_lemma THEN 'rule5'
                   ELSE 'ok'
               END AS s, k.kt, agg.ids, agg.ts
          FROM k, agg
    )
    SELECT st.s,
           CASE WHEN st.s = 'ok' THEN ARRAY[p_anchor_sense_id] || st.ids END,
           CASE WHEN st.s = 'ok' THEN ARRAY[st.kt] || st.ts END
      FROM st;
$$;

-- The reading key: the word's native rank-1 standard row (definition language = word
-- language), in the pool with has_pronunciation, not blocklisted, well-formed.
CREATE OR REPLACE FUNCTION public.calibration_placement_reading_key(
    p_vocab_id integer, p_word_language_id smallint,
    OUT sense_id integer, OUT reading text)
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    SELECT s.id, calibration_display_pronunciation(s.pronunciation, p_word_language_id)
      FROM dim_word_senses s
      JOIN calibration_anchor_pool p
        ON p.word_language_id = p_word_language_id
       AND p.definition_language_id = p_word_language_id
       AND p.sense_id = s.id
     WHERE s.vocab_id = p_vocab_id
       AND s.definition_language_id = p_word_language_id
       AND s.definition_level = 'standard'
       AND s.sense_rank = 1
       AND p.has_pronunciation
       AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = s.id)
       AND calibration_placement_well_formed_reading(
               calibration_display_pronunciation(s.pronunciation, p_word_language_id), p_word_language_id)
     ORDER BY s.id
     LIMIT 1;
$$;

-- Every display reading of the lemma (polyphones): never offered as a wrong option.
CREATE OR REPLACE FUNCTION public.calibration_placement_own_readings(
    p_vocab_id integer, p_word_language_id smallint)
RETURNS text[]
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    SELECT coalesce(array_agg(DISTINCT d), '{}')
      FROM (SELECT calibration_display_pronunciation(s.pronunciation, p_word_language_id) AS d
              FROM dim_word_senses s
             WHERE s.vocab_id = p_vocab_id
               AND s.definition_language_id = p_word_language_id
               AND s.pronunciation IS NOT NULL) x
     WHERE d IS NOT NULL;
$$;

-- Reading item options in canonical order, or NULL when the word is not reading-ready.
--   ja: key + 3 cached foils with the key's mora count, kana only, matching the
--       lemma's visible kana (rules 3, 3b), chosen by p_seed;
--   zh: K, K' (a variant of K), F (a cached foil with K's syllable count whose
--       toneless form differs from K's), F' (a variant of F not in {K, K'}); the
--       first F in p_seed order that has a variant wins (rule 4).
-- p_exclude_*: a recheck's earlier options (tech §3: foils disjoint from the first
-- serving). Readiness does not depend on p_seed.
CREATE OR REPLACE FUNCTION public.calibration_placement_reading_parts(
    p_native_sense_id integer, p_vocab_id integer, p_word_language_id smallint,
    p_lemma text, p_key text, p_seed double precision,
    p_exclude_sense_ids integer[] DEFAULT '{}', p_exclude_texts text[] DEFAULT '{}')
RETURNS jsonb
LANGUAGE plpgsql STABLE
SET search_path = public, pg_temp
AS $$
DECLARE
    v_units    integer := calibration_placement_units(p_key, p_word_language_id);
    v_own      text[]  := calibration_placement_own_readings(p_vocab_id, p_word_language_id);
    v_ex_ids   integer[] := coalesce(p_exclude_sense_ids, '{}');
    v_ex_texts text[]  := coalesce(p_exclude_texts, '{}');
    v_kv       text[];
    v_kt       text;
    v_fv       text[];
    v_ids      integer[];
    v_texts    text[];
    v_fvocab   integer[];
    i          integer;
BEGIN
    IF p_native_sense_id IS NULL OR p_key IS NULL OR v_units = 0 THEN
        RETURN NULL;
    END IF;

    IF p_word_language_id = 1 THEN
        -- Segmental foil candidates first (cheap): no candidate, no item, and no call to
        -- the variant generator (2-7 ms a call).
        SELECT array_agg(d.sense_id ORDER BY calibration_placement_unit(p_seed, 'f:' || d.sense_id), d.sense_id),
               array_agg(d.vocab_id ORDER BY calibration_placement_unit(p_seed, 'f:' || d.sense_id), d.sense_id),
               array_agg(d.option_text ORDER BY calibration_placement_unit(p_seed, 'f:' || d.sense_id), d.sense_id)
          INTO v_ids, v_fvocab, v_texts
          FROM (SELECT DISTINCT ON (o.option_text) o.sense_id, o.vocab_id, o.option_text
                  FROM calibration_cached_options('pronunciation', p_native_sense_id) o
                 WHERE o.option_text IS NOT NULL
                   AND o.sense_id <> p_native_sense_id
                   AND o.option_text <> p_key
                   AND calibration_placement_units(o.option_text, 1::smallint) = v_units
                   AND calibration_placement_toneless(o.option_text)
                       <> calibration_placement_toneless(p_key)
                   AND o.option_text <> ALL (v_own)
                   AND o.sense_id <> ALL (v_ex_ids)
                   AND o.option_text <> ALL (v_ex_texts)
                 ORDER BY o.option_text, o.sense_id) d;
        IF coalesce(cardinality(v_ids), 0) = 0 THEN
            RETURN NULL;
        END IF;

        SELECT array_agg(v ORDER BY v) INTO v_kv
          FROM unnest(calibration_zh_tone_variants(p_key, p_vocab_id)) AS v
         WHERE v IS NOT NULL AND v <> p_key
           AND v <> ALL (v_own) AND v <> ALL (v_ex_texts)
           AND calibration_placement_units(v, 1::smallint) = v_units;
        IF coalesce(cardinality(v_kv), 0) = 0 THEN
            RETURN NULL;
        END IF;
        v_kt := v_kv[1 + floor(calibration_placement_unit(p_seed, 'kt') * cardinality(v_kv))::integer];

        FOR i IN 1..cardinality(v_ids) LOOP
            SELECT array_agg(v ORDER BY v) INTO v_fv
              FROM unnest(calibration_zh_tone_variants(v_texts[i], v_fvocab[i])) AS v
             WHERE v IS NOT NULL AND v <> v_texts[i] AND v <> p_key AND v <> v_kt
               AND v <> ALL (v_own) AND v <> ALL (v_ex_texts)
               AND calibration_placement_units(v, 1::smallint) = v_units;
            IF coalesce(cardinality(v_fv), 0) > 0 THEN
                RETURN jsonb_build_object(
                    'sense_ids', jsonb_build_array(p_native_sense_id, NULL, v_ids[i], NULL),
                    'texts', jsonb_build_array(
                        p_key, v_kt, v_texts[i],
                        v_fv[1 + floor(calibration_placement_unit(p_seed, 'ft') * cardinality(v_fv))::integer]),
                    'roles', jsonb_build_array('K', 'KT', 'F', 'FT'));
            END IF;
        END LOOP;
        RETURN NULL;
    END IF;

    IF p_word_language_id = 3 THEN
        SELECT array_agg(z.sense_id ORDER BY z.u, z.sense_id), array_agg(z.option_text ORDER BY z.u, z.sense_id)
          INTO v_ids, v_texts
          FROM (SELECT d.sense_id, d.option_text,
                       calibration_placement_unit(p_seed, 'f:' || d.sense_id) AS u
                  FROM (SELECT DISTINCT ON (o.option_text) o.sense_id, o.option_text
                          FROM calibration_cached_options('pronunciation', p_native_sense_id) o
                         WHERE o.option_text IS NOT NULL
                           AND o.sense_id <> p_native_sense_id
                           AND o.option_text <> p_key
                           AND o.option_text ~ '^[ぁ-ゟァ-ヿー・]+$'
                           AND calibration_placement_units(o.option_text, 3::smallint) = v_units
                           AND o.option_text ~ calibration_placement_kana_pattern(p_lemma)
                           AND o.option_text <> ALL (v_own)
                           AND o.sense_id <> ALL (v_ex_ids)
                           AND o.option_text <> ALL (v_ex_texts)
                         ORDER BY o.option_text, o.sense_id) d
                 ORDER BY 3, 1
                 LIMIT 3) z;
        IF coalesce(cardinality(v_ids), 0) < 3 THEN
            RETURN NULL;
        END IF;
        RETURN jsonb_build_object('sense_ids', to_jsonb(ARRAY[p_native_sense_id] || v_ids),
                                  'texts', to_jsonb(ARRAY[p_key] || v_texts),
                                  'roles', NULL);
    END IF;

    RETURN NULL;
END;
$$;

-- Foil counts for the gate's exclusion columns: n_rule3 = foils passing rule 3 (zh:
-- also toneless-different from K); n_rule3b = also matching the visible kana (ja).
CREATE OR REPLACE FUNCTION public.calibration_placement_reading_foil_counts(
    p_native_sense_id integer, p_vocab_id integer, p_word_language_id smallint,
    p_lemma text, p_key text,
    OUT n_rule3 integer, OUT n_rule3b integer)
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    WITH own AS (SELECT calibration_placement_own_readings(p_vocab_id, p_word_language_id) AS r),
    o AS (
        SELECT DISTINCT o.option_text AS t
          FROM calibration_cached_options('pronunciation', p_native_sense_id) o, own
         WHERE o.option_text IS NOT NULL AND o.sense_id <> p_native_sense_id
           AND o.option_text <> p_key AND o.option_text <> ALL (own.r)
           AND calibration_placement_units(o.option_text, p_word_language_id)
               = calibration_placement_units(p_key, p_word_language_id)
           AND CASE WHEN p_word_language_id = 1
                    THEN calibration_placement_toneless(o.option_text) <> calibration_placement_toneless(p_key)
                    ELSE o.option_text ~ '^[ぁ-ゟァ-ヿー・]+$' END
    )
    SELECT count(*)::integer,
           (count(*) FILTER (WHERE p_word_language_id <> 3
                                OR o.t ~ calibration_placement_kana_pattern(p_lemma)))::integer
      FROM o;
$$;

-- Is the word reading-ready (tech §2)?
CREATE OR REPLACE FUNCTION public.calibration_placement_reading_ready(
    p_vocab_id integer, p_word_language_id smallint, p_lemma text)
RETURNS boolean
LANGUAGE plpgsql STABLE
SET search_path = public, pg_temp
AS $$
DECLARE
    k record;
BEGIN
    SELECT * INTO k FROM calibration_placement_reading_key(p_vocab_id, p_word_language_id);
    IF k.sense_id IS NULL THEN
        RETURN false;
    END IF;
    RETURN calibration_placement_reading_parts(k.sense_id, p_vocab_id, p_word_language_id,
                                               p_lemma, k.reading, 0.5) IS NOT NULL;
END;
$$;

-- Candidate lemmas for a draw: rank-1 frame rows of (L, D) (pool row, has_embedding,
-- not blocklisted), not served in this session, not answered by the user in any
-- calibration session in the last p_exclude_days days. p_band NULL = every band.
CREATE OR REPLACE FUNCTION public.calibration_placement_candidates(
    p_user_id uuid, p_session_id uuid, p_word_language_id smallint,
    p_definition_language_id smallint, p_band smallint, p_exclude_days integer)
RETURNS TABLE (sense_id integer, vocab_id integer, lemma text, definition text,
               zipf real, zipf_band smallint)
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    SELECT p.sense_id, p.vocab_id, p.lemma, s.definition, p.zipf, p.zipf_band
      FROM calibration_anchor_pool p
      JOIN dim_word_senses s ON s.id = p.sense_id AND s.sense_rank = 1
     WHERE p.word_language_id = p_word_language_id
       AND p.definition_language_id = p_definition_language_id
       AND p.has_embedding
       AND (p_band IS NULL OR p.zipf_band = p_band)
       AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = p.sense_id)
       AND NOT EXISTS (SELECT 1 FROM calibration_responses r
                        WHERE r.session_id = p_session_id AND r.anchor_vocab_id = p.vocab_id)
       AND NOT EXISTS (SELECT 1 FROM calibration_responses r
                        WHERE r.user_id = p_user_id
                          AND r.anchor_vocab_id = p.vocab_id
                          AND r.answered_at IS NOT NULL
                          AND r.answered_at > now() - make_interval(days => greatest(coalesce(p_exclude_days, 180), 0)));
$$;

-- Does band p_band still have a placement-ready word for this learner? (warm-up test)
CREATE OR REPLACE FUNCTION public.calibration_placement_band_has_word(
    p_user_id uuid, p_session_id uuid, p_word_language_id smallint,
    p_definition_language_id smallint, p_band smallint, p_exclude_days integer DEFAULT 180)
RETURNS boolean
LANGUAGE plpgsql STABLE
SET search_path = public, pg_temp
AS $$
DECLARE
    c record;
BEGIN
    FOR c IN
        SELECT * FROM calibration_placement_candidates(p_user_id, p_session_id, p_word_language_id,
                                                       p_definition_language_id, p_band, p_exclude_days)
         ORDER BY vocab_id
    LOOP
        IF (calibration_placement_meaning_parts(c.sense_id, p_word_language_id, p_definition_language_id,
                                                c.lemma, c.definition)).status = 'ok'
           AND (calibration_placement_reading_exempt(c.lemma, p_word_language_id)
                OR calibration_placement_reading_ready(c.vocab_id, p_word_language_id, c.lemma)) THEN
            RETURN true;
        END IF;
    END LOOP;
    RETURN false;
END;
$$;

-- Draw a placement-ready word uniformly at random within the band (tech §6.3):
-- candidates in random order, the first ready one wins. p_nearest: if the band has
-- none, the nearest band with one (ties -> the commoner band), then any.
CREATE OR REPLACE FUNCTION public.calibration_placement_draw(
    p_user_id uuid, p_session_id uuid, p_word_language_id smallint,
    p_definition_language_id smallint, p_band smallint, p_nearest boolean, p_exclude_days integer)
RETURNS TABLE (anchor_sense_id integer, vocab_id integer, lemma text, zipf real,
               zipf_band smallint, sense_ids integer[], texts text[])
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
DECLARE
    c record;
    m record;
BEGIN
    FOR c IN
        SELECT * FROM calibration_placement_candidates(
                   p_user_id, p_session_id, p_word_language_id, p_definition_language_id,
                   CASE WHEN p_nearest THEN NULL ELSE p_band END, p_exclude_days) x
         ORDER BY abs(x.zipf_band - p_band), x.zipf_band DESC, random()
    LOOP
        SELECT * INTO m FROM calibration_placement_meaning_parts(
            c.sense_id, p_word_language_id, p_definition_language_id, c.lemma, c.definition);
        CONTINUE WHEN m.status <> 'ok';
        CONTINUE WHEN NOT calibration_placement_reading_exempt(c.lemma, p_word_language_id)
                  AND NOT calibration_placement_reading_ready(c.vocab_id, p_word_language_id, c.lemma);
        anchor_sense_id := c.sense_id;
        vocab_id        := c.vocab_id;
        lemma           := c.lemma;
        zipf            := c.zipf;
        zipf_band       := c.zipf_band;
        sense_ids       := m.sense_ids;
        texts           := m.texts;
        RETURN NEXT;
        RETURN;
    END LOOP;
END;
$$;

-- =============================================================================
-- Rows, payloads, reveal, tallies
-- =============================================================================

-- Insert one item row with its options shuffled by p_seed and return the client
-- payload (no key, no sense ids, no roles). p_key_index is the key's 1-based index in
-- the canonical arrays; p_avoid_order (forced_guess) forces a new order.
CREATE OR REPLACE FUNCTION public.calibration_placement_insert_item(
    p_session_id uuid, p_user_id uuid, p_anchor_sense_id integer, p_vocab_id integer,
    p_lemma text, p_zipf real, p_band smallint,
    p_item_kind text, p_probe_kind text, p_instrument text, p_pair_response_id bigint,
    p_sense_ids integer[], p_texts text[], p_roles text[], p_key_index integer,
    p_store_texts boolean, p_seed double precision, p_avoid_order integer[] DEFAULT NULL)
RETURNS jsonb
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
DECLARE
    v_n    integer := cardinality(p_texts);
    v_perm integer[];
    v_id   bigint;
BEGIN
    SELECT array_agg(i ORDER BY calibration_placement_unit(p_seed, 'pos:' || i), i)
      INTO v_perm FROM generate_series(1, v_n) AS i;
    IF p_avoid_order IS NOT NULL
       AND (SELECT array_agg(p_sense_ids[t.i] ORDER BY t.o)
              FROM unnest(v_perm) WITH ORDINALITY AS t(i, o)) IS NOT DISTINCT FROM p_avoid_order THEN
        SELECT array_agg(t.i ORDER BY t.o DESC) INTO v_perm
          FROM unnest(v_perm) WITH ORDINALITY AS t(i, o);
    END IF;

    INSERT INTO calibration_responses (
        session_id, user_id, anchor_sense_id, anchor_vocab_id, anchor_zipf, zipf_band, served_at,
        item_kind, probe_kind, instrument, pair_response_id,
        option_sense_ids, key_position, option_roles, option_texts)
    VALUES (
        p_session_id, p_user_id, p_anchor_sense_id, p_vocab_id, p_zipf, p_band, clock_timestamp(),
        p_item_kind, p_probe_kind, p_instrument, p_pair_response_id,
        (SELECT array_agg(p_sense_ids[t.i] ORDER BY t.o) FROM unnest(v_perm) WITH ORDINALITY AS t(i, o)),
        (array_position(v_perm, p_key_index) - 1)::smallint,
        CASE WHEN p_roles IS NOT NULL THEN
            (SELECT array_agg(p_roles[t.i] ORDER BY t.o) FROM unnest(v_perm) WITH ORDINALITY AS t(i, o)) END,
        CASE WHEN p_store_texts THEN
            (SELECT array_agg(p_texts[t.i] ORDER BY t.o) FROM unnest(v_perm) WITH ORDINALITY AS t(i, o)) END)
    RETURNING id INTO v_id;

    UPDATE calibration_sessions SET items_served = items_served + 1 WHERE id = p_session_id;

    RETURN jsonb_build_object(
        'response_id', v_id,
        'vocab_id',    p_vocab_id,
        'lemma',       p_lemma,
        'band',        p_band,
        'kind',        p_item_kind,
        'probe_kind',  p_probe_kind,
        'options',     (SELECT jsonb_agg(p_texts[t.i] ORDER BY t.o)
                          FROM unnest(v_perm) WITH ORDINALITY AS t(i, o)),
        'idk_allowed', p_probe_kind IS DISTINCT FROM 'forced_guess');
END;
$$;

-- The displayed option texts of a stored row, in display order (zh reading rows store
-- them; meaning rows are rebuilt from the sense ids with rule 5; ja reading and
-- sound_pair rows from the senses' display readings).
CREATE OR REPLACE FUNCTION public.calibration_placement_option_texts(p_response_id bigint)
RETURNS text[]
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    SELECT CASE
        WHEN r.option_texts IS NOT NULL THEN r.option_texts
        ELSE (SELECT array_agg(CASE WHEN r.item_kind = 'meaning'
                                    THEN calibration_placement_strip_definition(
                                             s.definition, cs.word_language_id, cs.definition_language_id)
                                    ELSE calibration_display_pronunciation(s.pronunciation, cs.word_language_id)
                               END ORDER BY u.o)
                FROM unnest(r.option_sense_ids) WITH ORDINALITY AS u(sid, o)
                LEFT JOIN dim_word_senses s ON s.id = u.sid)
    END
      FROM calibration_responses r
      JOIN calibration_sessions cs ON cs.id = r.session_id
     WHERE r.id = p_response_id;
$$;

-- The client payload of a stored row (used to re-send the pending item).
CREATE OR REPLACE FUNCTION public.calibration_placement_item_payload(p_response_id bigint)
RETURNS jsonb
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    SELECT jsonb_build_object(
               'response_id', r.id,
               'vocab_id',    r.anchor_vocab_id,
               'lemma',       v.lemma,
               'band',        r.zipf_band,
               'kind',        r.item_kind,
               'probe_kind',  r.probe_kind,
               'options',     to_jsonb(calibration_placement_option_texts(r.id)),
               'idk_allowed', r.probe_kind IS DISTINCT FROM 'forced_guess')
      FROM calibration_responses r
      JOIN dim_vocabulary v ON v.id = r.anchor_vocab_id
     WHERE r.id = p_response_id;
$$;

-- The reveal reading: the native rank-1 standard reading (zh, ja); NULL for en.
CREATE OR REPLACE FUNCTION public.calibration_placement_reveal_reading(
    p_vocab_id integer, p_word_language_id smallint)
RETURNS text
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    SELECT CASE WHEN p_word_language_id IN (1, 3) THEN (
        SELECT calibration_display_pronunciation(s.pronunciation, p_word_language_id)
          FROM dim_word_senses s
         WHERE s.vocab_id = p_vocab_id
           AND s.definition_language_id = p_word_language_id
           AND s.definition_level = 'standard'
           AND s.pronunciation IS NOT NULL
         ORDER BY s.sense_rank, s.id
         LIMIT 1) END;
$$;

-- The combined reveal of one word: its root row (scored meaning item, or a recheck)
-- and every row whose pair_response_id is the root (reading item, probes).
CREATE OR REPLACE FUNCTION public.calibration_placement_reveal(p_root_id bigint)
RETURNS jsonb
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    WITH root AS (
        SELECT r.*, cs.word_language_id AS l, cs.definition_language_id AS d
          FROM calibration_responses r
          JOIN calibration_sessions cs ON cs.id = r.session_id
         WHERE r.id = p_root_id
    ),
    parts AS (
        SELECT r.id, r.item_kind, r.probe_kind, r.is_correct, r.chosen_position, r.key_position,
               r.option_roles, calibration_placement_option_texts(r.id) AS texts
          FROM calibration_responses r, root
         WHERE r.session_id = root.session_id
           AND (r.id = root.id OR r.pair_response_id = root.id)
    )
    SELECT jsonb_build_object(
               'lemma',   v.lemma,
               'reading', calibration_placement_reveal_reading(root.anchor_vocab_id, root.l),
               'meaning', (SELECT calibration_placement_strip_definition(s.definition, root.l, root.d)
                             FROM dim_word_senses s
                            WHERE s.vocab_id = root.anchor_vocab_id
                              AND s.definition_language_id = root.d
                              AND s.definition_level = 'standard'
                              AND s.sense_rank = 1
                            ORDER BY s.id LIMIT 1),
               'parts',   (SELECT jsonb_agg(jsonb_build_object(
                               'kind',           p.item_kind,
                               'probe_kind',     p.probe_kind,
                               'chosen_text',    CASE WHEN p.chosen_position IS NOT NULL
                                                      THEN p.texts[p.chosen_position + 1] END,
                               'key_text',       p.texts[p.key_position + 1],
                               'is_correct',     p.is_correct,
                               'tone_only_miss', coalesce(p.option_roles[p.chosen_position + 1] = 'KT', false))
                               ORDER BY p.id)
                             FROM parts p))
      FROM root
      JOIN dim_vocabulary v ON v.id = root.anchor_vocab_id;
$$;

-- This session's tallies (tech §5.1, §6, §7):
--   m  = [[n, c, w] x 7]        scored meaning items: answered, right, answered wrong
--   mr = ja [[n', pc, prw] x 7] | zh [[n', pc, pkt, pf] x 7] | en null
--        n' = pair-sample words: meaning answered and, when a reading was due
--        (reading-ready word, meaning right), the reading answered.
--   scored, probes (answered), active_ms (sum of min(gap, 60 s); the first gap from
--   started_at), median_latency_ms, warmup_done (2 meaning items in every band that
--   still has a placement-ready word for this learner).
CREATE OR REPLACE FUNCTION public.calibration_placement_tallies(p_session_id uuid)
RETURNS jsonb
LANGUAGE plpgsql STABLE
SET search_path = public, pg_temp
AS $$
DECLARE
    v_s       calibration_sessions%ROWTYPE;
    v_m       jsonb;
    v_mr      jsonb;
    v_n       integer[];
    v_scored  integer;
    v_probes  integer;
    v_active  bigint;
    v_median  integer;
    v_warm    boolean := true;
    v_band    integer;
BEGIN
    SELECT * INTO v_s FROM calibration_sessions WHERE id = p_session_id;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    WITH r AS (
        SELECT * FROM calibration_responses WHERE session_id = p_session_id
    ),
    m AS (
        SELECT r.id, r.zipf_band AS b, r.is_correct AS mc, (r.chosen_position IS NULL) AS m_idk,
               calibration_placement_reading_exempt(v.lemma, v_s.word_language_id) AS ex
          FROM r JOIN dim_vocabulary v ON v.id = r.anchor_vocab_id
         WHERE r.item_kind = 'meaning' AND r.probe_kind IS NULL AND r.answered_at IS NOT NULL
    ),
    p AS (
        SELECT m.*, (rd.answered_at IS NOT NULL) AS r_ans, coalesce(rd.is_correct, false) AS rc,
               (rd.answered_at IS NOT NULL AND rd.chosen_position IS NULL) AS r_idk,
               rd.option_roles[rd.chosen_position + 1] AS role
          FROM m
          LEFT JOIN r rd ON rd.pair_response_id = m.id AND rd.item_kind = 'reading' AND rd.probe_kind IS NULL
    ),
    ps AS (SELECT * FROM p WHERE ex OR NOT mc OR r_ans),
    bands AS (SELECT g AS b FROM generate_series(1, 7) g),
    mb AS (
        SELECT bands.b, count(m.id)::integer AS n,
               jsonb_build_array(count(m.id),
                                 count(m.id) FILTER (WHERE m.mc),
                                 count(m.id) FILTER (WHERE NOT m.mc AND NOT m.m_idk)) AS x
          FROM bands LEFT JOIN m ON m.b = bands.b GROUP BY bands.b
    ),
    pb AS (
        SELECT bands.b,
               CASE WHEN v_s.word_language_id = 1 THEN
                   jsonb_build_array(count(ps.id),
                                     count(ps.id) FILTER (WHERE ps.mc AND ps.role = 'K'),
                                     count(ps.id) FILTER (WHERE ps.mc AND ps.role = 'KT'),
                                     count(ps.id) FILTER (WHERE ps.mc AND ps.role IN ('F', 'FT')))
               ELSE
                   jsonb_build_array(count(ps.id),
                                     count(ps.id) FILTER (WHERE ps.mc AND (ps.ex OR ps.rc)),
                                     count(ps.id) FILTER (WHERE (ps.ex AND NOT ps.mc AND NOT ps.m_idk)
                                                             OR (NOT ps.ex AND ps.mc AND ps.r_ans
                                                                 AND NOT ps.rc AND NOT ps.r_idk)))
               END AS x
          FROM bands LEFT JOIN ps ON ps.b = bands.b GROUP BY bands.b
    )
    SELECT (SELECT jsonb_agg(mb.x ORDER BY mb.b) FROM mb),
           CASE WHEN v_s.word_language_id IN (1, 3) THEN (SELECT jsonb_agg(pb.x ORDER BY pb.b) FROM pb) END,
           (SELECT array_agg(mb.n ORDER BY mb.b) FROM mb),
           (SELECT count(*) FROM r WHERE r.probe_kind IS NULL AND r.answered_at IS NOT NULL),
           (SELECT count(*) FROM r WHERE r.probe_kind IS NOT NULL AND r.answered_at IS NOT NULL),
           (SELECT coalesce(sum(least(greatest(extract(epoch FROM (a.answered_at - a.prev)), 0) * 1000, 60000)), 0)
              FROM (SELECT r.answered_at,
                           coalesce(lag(r.answered_at) OVER (ORDER BY r.answered_at, r.id), v_s.started_at) AS prev
                      FROM r WHERE r.answered_at IS NOT NULL) a),
           (SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY r.latency_ms))
              FROM r WHERE r.answered_at IS NOT NULL AND r.latency_ms IS NOT NULL)
      INTO v_m, v_mr, v_n, v_scored, v_probes, v_active, v_median;

    FOR v_band IN 1..7 LOOP
        IF v_n[v_band] < 2 AND calibration_placement_band_has_word(
               v_s.user_id, v_s.id, v_s.word_language_id, v_s.definition_language_id, v_band::smallint, 180) THEN
            v_warm := false;
            EXIT;
        END IF;
    END LOOP;

    RETURN jsonb_build_object(
        'm',                 v_m,
        'mr',                v_mr,
        'scored',            v_scored,
        'probes',            v_probes,
        'active_ms',         v_active,
        'median_latency_ms', v_median,
        'warmup_done',       v_warm);
END;
$$;

-- =============================================================================
-- Item builders (VOLATILE; called by the writers below)
-- =============================================================================

-- A reading item (scored, reading_after_miss or recheck) for one word; NULL if the
-- word is not reading-ready (or, for a recheck, no disjoint item can be built).
CREATE OR REPLACE FUNCTION public.calibration_placement_build_reading(
    p_session_id uuid, p_user_id uuid, p_word_language_id smallint,
    p_vocab_id integer, p_lemma text, p_zipf real, p_band smallint,
    p_pair_response_id bigint, p_probe_kind text, p_seed double precision,
    p_exclude_sense_ids integer[] DEFAULT '{}', p_exclude_texts text[] DEFAULT '{}')
RETURNS jsonb
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
DECLARE
    k     record;
    v_p   jsonb;
BEGIN
    SELECT * INTO k FROM calibration_placement_reading_key(p_vocab_id, p_word_language_id);
    IF k.sense_id IS NULL THEN
        RETURN NULL;
    END IF;
    v_p := calibration_placement_reading_parts(k.sense_id, p_vocab_id, p_word_language_id, p_lemma,
                                               k.reading, p_seed, p_exclude_sense_ids, p_exclude_texts);
    IF v_p IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN calibration_placement_insert_item(
        p_session_id, p_user_id, k.sense_id, p_vocab_id, p_lemma, p_zipf, p_band,
        'reading', p_probe_kind,
        CASE WHEN p_word_language_id = 1 THEN 'reading_tone_v1' ELSE 'reading_v1' END,
        p_pair_response_id,
        ARRAY(SELECT (x)::integer FROM jsonb_array_elements_text(v_p -> 'sense_ids') WITH ORDINALITY AS e(x, o) ORDER BY o),
        ARRAY(SELECT x FROM jsonb_array_elements_text(v_p -> 'texts') WITH ORDINALITY AS e(x, o) ORDER BY o),
        CASE WHEN jsonb_typeof(v_p -> 'roles') = 'array' THEN
            ARRAY(SELECT x FROM jsonb_array_elements_text(v_p -> 'roles') WITH ORDINALITY AS e(x, o) ORDER BY o) END,
        1, p_word_language_id = 1, p_seed);
END;
$$;

-- A new scored meaning item in p_band (p_nearest: fall back to the nearest band).
CREATE OR REPLACE FUNCTION public.calibration_placement_build_meaning(
    p_session_id uuid, p_user_id uuid, p_word_language_id smallint,
    p_definition_language_id smallint, p_band smallint, p_nearest boolean,
    p_exclude_days integer, p_seed double precision)
RETURNS jsonb
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
DECLARE
    c record;
BEGIN
    SELECT * INTO c FROM calibration_placement_draw(p_user_id, p_session_id, p_word_language_id,
                                                    p_definition_language_id, p_band, p_nearest, p_exclude_days);
    IF NOT FOUND OR c.anchor_sense_id IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN calibration_placement_insert_item(
        p_session_id, p_user_id, c.anchor_sense_id, c.vocab_id, c.lemma, c.zipf, c.zipf_band,
        'meaning', NULL, 'meaning_bare_v1', NULL, c.sense_ids, c.texts, NULL, 1, false, p_seed);
END;
$$;

-- A recheck probe (tech §3): a word whose meaning and reading this learner got right
-- in an earlier placement answered 7-180 days ago, never rechecked before, rebuilt
-- with foils disjoint from that first serving.
CREATE OR REPLACE FUNCTION public.calibration_placement_build_recheck(
    p_session_id uuid, p_user_id uuid, p_word_language_id smallint, p_seed double precision)
RETURNS jsonb
LANGUAGE plpgsql VOLATILE
SET search_path = public, pg_temp
AS $$
DECLARE
    c     record;
    v_key integer;
    v_out jsonb;
BEGIN
    IF p_word_language_id NOT IN (1, 3) THEN
        RETURN NULL;
    END IF;
    FOR c IN
        SELECT rr.id, rr.anchor_vocab_id, rr.anchor_zipf, rr.zipf_band, rr.option_sense_ids,
               rr.option_texts, rr.key_position, v.lemma
          FROM calibration_responses rr
          JOIN calibration_sessions ss ON ss.id = rr.session_id
                                      AND ss.mode = 'placement'
                                      AND ss.word_language_id = p_word_language_id
          JOIN calibration_responses mm ON mm.id = rr.pair_response_id AND mm.is_correct
          JOIN dim_vocabulary v ON v.id = rr.anchor_vocab_id
         WHERE rr.user_id = p_user_id
           AND rr.session_id <> p_session_id
           AND rr.item_kind = 'reading' AND rr.probe_kind IS NULL AND rr.is_correct
           AND rr.answered_at IS NOT NULL
           AND rr.answered_at <= now() - interval '7 days'
           AND rr.answered_at >  now() - interval '180 days'
           AND NOT EXISTS (SELECT 1 FROM calibration_responses q
                            WHERE q.user_id = p_user_id AND q.anchor_vocab_id = rr.anchor_vocab_id
                              AND q.answered_at IS NOT NULL AND q.probe_kind = 'recheck')
           AND NOT EXISTS (SELECT 1 FROM calibration_responses q
                            WHERE q.session_id = p_session_id AND q.anchor_vocab_id = rr.anchor_vocab_id)
         ORDER BY random()
    LOOP
        v_key := c.option_sense_ids[c.key_position + 1];
        v_out := calibration_placement_build_reading(
            p_session_id, p_user_id, p_word_language_id, c.anchor_vocab_id, c.lemma,
            c.anchor_zipf, c.zipf_band, NULL, 'recheck', p_seed,
            ARRAY(SELECT x FROM unnest(c.option_sense_ids) x WHERE x IS NOT NULL AND x <> v_key),
            ARRAY(SELECT t FROM unnest(coalesce(c.option_texts, '{}')) WITH ORDINALITY AS u(t, o)
                   WHERE u.o <> c.key_position + 1));
        IF v_out IS NOT NULL THEN
            RETURN v_out;
        END IF;
    END LOOP;
    RETURN NULL;
END;
$$;

-- =============================================================================
-- calibration_placement_ready_counts  (launch gate and monitoring; tech §2, §14)
-- =============================================================================
CREATE OR REPLACE FUNCTION public.calibration_placement_ready_counts(
    p_word_language_id smallint, p_definition_language_id smallint)
RETURNS jsonb
LANGUAGE sql STABLE
SET search_path = public, pg_temp
AS $$
    WITH fr AS (
        SELECT DISTINCT ON (p.vocab_id) p.sense_id, p.vocab_id, p.lemma, s.definition, p.zipf, p.zipf_band
          FROM calibration_anchor_pool p
          JOIN dim_word_senses s ON s.id = p.sense_id AND s.sense_rank = 1
         WHERE p.word_language_id = p_word_language_id
           AND p.definition_language_id = p_definition_language_id
           AND p.has_embedding
           AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = p.sense_id)
         ORDER BY p.vocab_id, p.sense_id
    ),
    st AS (
        SELECT fr.*, mp.status AS m_status,
               calibration_placement_reading_exempt(fr.lemma, p_word_language_id) AS ex,
               rk.sense_id AS rk_sense, rk.reading AS rk_reading
          FROM fr
         CROSS JOIN LATERAL calibration_placement_meaning_parts(
                   fr.sense_id, p_word_language_id, p_definition_language_id, fr.lemma, fr.definition) mp
          LEFT JOIN LATERAL calibration_placement_reading_key(fr.vocab_id, p_word_language_id) rk ON true
    ),
    st2 AS MATERIALIZED (   -- evaluate reading_parts once per lemma (it is referenced twice below)
        SELECT st.*,
               (NOT st.ex AND st.rk_sense IS NOT NULL
                AND calibration_placement_reading_parts(st.rk_sense, st.vocab_id, p_word_language_id,
                                                        st.lemma, st.rk_reading, 0.5) IS NOT NULL) AS rr,
               fc.n_rule3, fc.n_rule3b
          FROM st
          LEFT JOIN LATERAL calibration_placement_reading_foil_counts(
                   st.rk_sense, st.vocab_id, p_word_language_id, st.lemma, st.rk_reading) fc
            ON NOT st.ex AND st.rk_sense IS NOT NULL
    ),
    f AS (
        SELECT st2.*, (m_status = 'ok') AS mok, (m_status = 'ok' AND (ex OR rr)) AS ready
          FROM st2
    ),
    bands AS (SELECT g::smallint AS b FROM generate_series(1, 7) g),
    per AS (
        SELECT bands.b,
               jsonb_build_object(
                   'band',               bands.b,
                   'frame_n',            count(f.vocab_id),
                   'ready_n',            count(f.vocab_id) FILTER (WHERE f.ready),
                   'meaning_ready_n',    count(f.vocab_id) FILTER (WHERE f.mok),
                   'reading_ready_n',    count(f.vocab_id) FILTER (WHERE f.rr),
                   'exempt_n',           count(f.vocab_id) FILTER (WHERE f.ex),
                   'excluded_rule5_n',   count(f.vocab_id) FILTER (WHERE f.m_status = 'rule5'),
                   'excluded_rule3b_n',  count(f.vocab_id) FILTER (WHERE p_word_language_id = 3 AND NOT f.ex
                                                                    AND f.n_rule3 >= 3 AND f.n_rule3b < 3),
                   'excluded_tone_n',    count(f.vocab_id) FILTER (WHERE p_word_language_id = 1 AND NOT f.ex
                                                                    AND f.n_rule3 >= 1 AND NOT f.rr),
                   'ready_mean_zipf',    round(avg(f.zipf) FILTER (WHERE f.ready)::numeric, 3),
                   'unready_mean_zipf',  round(avg(f.zipf) FILTER (WHERE NOT f.ready)::numeric, 3),
                   'ready_share_len3',   round(avg((char_length(f.lemma) >= 3)::integer)
                                               FILTER (WHERE f.ready)::numeric, 3),
                   'unready_share_len3', round(avg((char_length(f.lemma) >= 3)::integer)
                                               FILTER (WHERE NOT f.ready)::numeric, 3)) AS x
          FROM bands LEFT JOIN f ON f.zipf_band = bands.b
         GROUP BY bands.b
    )
    SELECT jsonb_build_object(
               'word_language_id',       p_word_language_id,
               'definition_language_id', p_definition_language_id,
               'frame',                  (SELECT count(*) FROM f),
               'ready',                  (SELECT count(*) FILTER (WHERE ready) FROM f),
               'bands',                  (SELECT jsonb_agg(per.x ORDER BY per.b) FROM per));
$$;

-- =============================================================================
-- calibration_placement_next_item  (tech §14)
-- =============================================================================
-- Draws and builds a meaning item in p_band (no fallback band: {exhausted: true} when
-- the band has no word left). Also: re-sends the pending item if one exists, and at
-- the very start of a session serves a recheck probe when one is eligible.
CREATE OR REPLACE FUNCTION public.calibration_placement_next_item(
    p_user_id uuid, p_session_id uuid, p_band smallint, p_exclude_days integer DEFAULT 180)
RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_s       calibration_sessions%ROWTYPE;
    v_pending bigint;
    v_out     jsonb;
BEGIN
    SELECT * INTO v_s FROM calibration_sessions
     WHERE id = p_session_id AND user_id = p_user_id AND mode = 'placement'
       FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'placement session not found' USING ERRCODE = 'P0002';
    END IF;
    IF v_s.ended_at IS NOT NULL THEN
        RAISE EXCEPTION 'placement session is closed' USING ERRCODE = '22023';
    END IF;
    IF p_band IS NULL OR p_band NOT BETWEEN 1 AND 7 THEN
        RAISE EXCEPTION 'invalid band %', p_band USING ERRCODE = '22023';
    END IF;
    IF p_exclude_days IS NOT NULL AND p_exclude_days < 0 THEN
        RAISE EXCEPTION 'invalid exclude_days %', p_exclude_days USING ERRCODE = '22023';
    END IF;

    SELECT id INTO v_pending FROM calibration_responses
     WHERE session_id = p_session_id AND answered_at IS NULL
     ORDER BY id DESC LIMIT 1;
    IF v_pending IS NOT NULL THEN
        RETURN calibration_placement_item_payload(v_pending) || jsonb_build_object('resent', true);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM calibration_responses WHERE session_id = p_session_id) THEN
        v_out := calibration_placement_build_recheck(p_session_id, p_user_id, v_s.word_language_id, random());
        IF v_out IS NOT NULL THEN
            RETURN v_out;
        END IF;
    END IF;

    v_out := calibration_placement_build_meaning(p_session_id, p_user_id, v_s.word_language_id,
                                                 v_s.definition_language_id, p_band, false,
                                                 coalesce(p_exclude_days, 180), random());
    IF v_out IS NULL THEN
        RETURN jsonb_build_object('exhausted', true);
    END IF;
    RETURN v_out;
END;
$$;

-- =============================================================================
-- calibration_placement_answer  (tech §14)
-- =============================================================================
CREATE OR REPLACE FUNCTION public.calibration_placement_answer(
    p_user_id uuid, p_session_id uuid, p_response_id bigint, p_position smallint,
    p_latency_ms integer, p_next_band smallint, p_draws jsonb)
RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_s         calibration_sessions%ROWTYPE;
    v_r         calibration_responses%ROWTYPE;
    v_l         smallint;
    v_d         smallint;
    v_u_probe   double precision := 1.0;     -- no draw -> no probe
    v_u_seed    double precision;
    v_correct   boolean;
    v_role      text;
    v_lemma     text;
    v_exempt    boolean;
    v_root      bigint;
    v_probes    integer;
    v_fg        integer;
    v_ram       integer;
    v_sp        integer;
    v_rc        integer;
    v_scored_rows integer;
    v_next      jsonb;
    v_reveal    jsonb;
    v_exhausted boolean := false;
    v_texts     text[];
    v_k         record;
    v_foil      record;
BEGIN
    SELECT * INTO v_s FROM calibration_sessions
     WHERE id = p_session_id AND user_id = p_user_id AND mode = 'placement'
       FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'placement session not found' USING ERRCODE = 'P0002';
    END IF;
    IF v_s.ended_at IS NOT NULL THEN
        RAISE EXCEPTION 'placement session is closed' USING ERRCODE = '22023';
    END IF;
    IF p_next_band IS NOT NULL AND p_next_band NOT BETWEEN 1 AND 7 THEN
        RAISE EXCEPTION 'invalid next band %', p_next_band USING ERRCODE = '22023';
    END IF;
    IF p_draws IS NOT NULL AND jsonb_typeof(p_draws) <> 'object' THEN
        RAISE EXCEPTION 'invalid draws' USING ERRCODE = '22023';
    END IF;
    IF p_draws ? 'u_probe' AND jsonb_typeof(p_draws -> 'u_probe') <> 'null' THEN
        IF jsonb_typeof(p_draws -> 'u_probe') <> 'number' THEN
            RAISE EXCEPTION 'invalid draws' USING ERRCODE = '22023';
        END IF;
        v_u_probe := (p_draws ->> 'u_probe')::double precision;
    END IF;
    IF p_draws ? 'u_seed' AND jsonb_typeof(p_draws -> 'u_seed') <> 'null' THEN
        IF jsonb_typeof(p_draws -> 'u_seed') <> 'number' THEN
            RAISE EXCEPTION 'invalid draws' USING ERRCODE = '22023';
        END IF;
        v_u_seed := (p_draws ->> 'u_seed')::double precision;
    ELSE
        v_u_seed := random();
    END IF;
    IF v_u_probe < 0 OR v_u_probe > 1 OR v_u_seed < 0 OR v_u_seed > 1 THEN
        RAISE EXCEPTION 'invalid draws' USING ERRCODE = '22023';
    END IF;

    SELECT * INTO v_r FROM calibration_responses
     WHERE id = p_response_id AND session_id = p_session_id AND user_id = p_user_id
       FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'response % is not in this session', p_response_id USING ERRCODE = '22023';
    END IF;
    IF v_r.answered_at IS NOT NULL THEN
        RAISE EXCEPTION 'response % already answered', p_response_id USING ERRCODE = '22023';
    END IF;
    IF p_position IS NOT NULL
       AND (p_position < 0 OR p_position >= coalesce(cardinality(v_r.option_sense_ids), 0)) THEN
        RAISE EXCEPTION 'invalid position %', p_position USING ERRCODE = '22023';
    END IF;

    -- Grade --------------------------------------------------------------------
    v_correct := (p_position IS NOT NULL AND p_position = v_r.key_position);
    v_role    := CASE WHEN p_position IS NOT NULL THEN v_r.option_roles[p_position + 1] END;

    UPDATE calibration_responses
       SET chosen_position = p_position,
           chosen_sense_id = CASE WHEN p_position IS NOT NULL THEN v_r.option_sense_ids[p_position + 1] END,
           is_correct      = v_correct,
           latency_ms      = CASE WHEN p_latency_ms IS NOT NULL
                                  THEN least(greatest(p_latency_ms, 0), 600000) END,
           answered_at     = clock_timestamp()
     WHERE id = p_response_id;

    UPDATE calibration_sessions
       SET items_answered = items_answered + 1,
           items_correct  = items_correct + CASE WHEN v_correct THEN 1 ELSE 0 END
     WHERE id = p_session_id;

    -- What comes next ----------------------------------------------------------
    v_l := v_s.word_language_id;
    v_d := v_s.definition_language_id;
    SELECT lemma INTO v_lemma FROM dim_vocabulary WHERE id = v_r.anchor_vocab_id;
    v_exempt := calibration_placement_reading_exempt(v_lemma, v_l);
    v_root   := coalesce(v_r.pair_response_id, v_r.id);

    SELECT count(*) FILTER (WHERE probe_kind IS NOT NULL),
           count(*) FILTER (WHERE probe_kind = 'forced_guess'),
           count(*) FILTER (WHERE probe_kind = 'reading_after_miss'),
           count(*) FILTER (WHERE probe_kind = 'sound_pair'),
           count(*) FILTER (WHERE probe_kind = 'recheck'),
           count(*) FILTER (WHERE probe_kind IS NULL)
      INTO v_probes, v_fg, v_ram, v_sp, v_rc, v_scored_rows
      FROM calibration_responses WHERE session_id = p_session_id;

    IF v_r.probe_kind IS NULL AND v_r.item_kind = 'meaning' THEN
        IF v_correct AND NOT v_exempt THEN
            -- 1. right meaning on a reading-ready word: the scored reading item
            v_next := calibration_placement_build_reading(
                p_session_id, p_user_id, v_l, v_r.anchor_vocab_id, v_lemma, v_r.anchor_zipf,
                v_r.zipf_band, v_r.id, NULL, v_u_seed);
        ELSIF p_position IS NULL AND v_u_probe < 0.15 AND v_probes < 4 AND v_fg < 2 THEN
            -- 2. IDK: forced_guess (same options, new order, no IDK)
            v_texts := calibration_placement_option_texts(v_r.id);
            v_next := calibration_placement_insert_item(
                p_session_id, p_user_id, v_r.anchor_sense_id, v_r.anchor_vocab_id, v_lemma,
                v_r.anchor_zipf, v_r.zipf_band, 'meaning', 'forced_guess', 'meaning_bare_v1', v_r.id,
                v_r.option_sense_ids, v_texts, NULL, v_r.key_position + 1, false, v_u_seed,
                v_r.option_sense_ids);
        ELSIF NOT v_correct AND NOT v_exempt AND v_u_probe < 0.25 AND v_probes < 4 AND v_ram < 2 THEN
            -- 3. wrong or IDK on a reading-ready word: reading_after_miss
            v_next := calibration_placement_build_reading(
                p_session_id, p_user_id, v_l, v_r.anchor_vocab_id, v_lemma, v_r.anchor_zipf,
                v_r.zipf_band, v_r.id, 'reading_after_miss', v_u_seed);
        END IF;
    ELSIF v_r.probe_kind IS NULL AND v_r.item_kind = 'reading' THEN
        IF v_l = 3 AND v_correct AND v_u_probe < 0.5 AND v_probes < 4 AND v_sp < 2 THEN
            -- 4. ja: sound_pair (key and a cached special-mora / voicing foil)
            SELECT * INTO v_k FROM calibration_placement_reading_key(v_r.anchor_vocab_id, v_l);
            IF v_k.sense_id IS NOT NULL THEN
                SELECT o.sense_id, o.option_text INTO v_foil
                  FROM calibration_cached_options('pronunciation', v_k.sense_id) o
                 WHERE o.option_text IS NOT NULL AND o.option_text <> v_k.reading
                   AND o.sense_id <> v_k.sense_id
                   AND calibration_placement_mora_skeleton(o.option_text)
                       = calibration_placement_mora_skeleton(v_k.reading)
                 ORDER BY calibration_placement_unit(v_u_seed, 'sp:' || o.sense_id), o.sense_id
                 LIMIT 1;
                IF v_foil.sense_id IS NOT NULL THEN
                    v_next := calibration_placement_insert_item(
                        p_session_id, p_user_id, v_k.sense_id, v_r.anchor_vocab_id, v_lemma,
                        v_r.anchor_zipf, v_r.zipf_band, 'sound_pair', 'sound_pair', NULL, v_root,
                        ARRAY[v_k.sense_id, v_foil.sense_id], ARRAY[v_k.reading, v_foil.option_text],
                        NULL, 1, false, v_u_seed);
                END IF;
            END IF;
        END IF;
    END IF;

    IF v_next IS NULL THEN
        -- 5. the word is complete
        v_reveal := calibration_placement_reveal(v_root);
        IF p_next_band IS NOT NULL THEN
            IF v_r.probe_kind = 'recheck' AND v_scored_rows = 0 AND v_rc < 2 AND v_probes < 4 THEN
                v_next := calibration_placement_build_recheck(p_session_id, p_user_id, v_l, v_u_seed);
            END IF;
            IF v_next IS NULL THEN
                v_next := calibration_placement_build_meaning(p_session_id, p_user_id, v_l, v_d,
                                                              p_next_band, true, 180, v_u_seed);
                v_exhausted := (v_next IS NULL);
            END IF;
        END IF;
    END IF;

    RETURN jsonb_build_object(
        'answer',    jsonb_build_object('is_correct', v_correct,
                                        'skipped',    p_position IS NULL,
                                        'kind',       v_r.item_kind,
                                        'probe_kind', v_r.probe_kind,
                                        'role',       v_role),
        'reveal',    v_reveal,
        'next_item', v_next,
        'exhausted', v_exhausted,
        'tallies',   calibration_placement_tallies(p_session_id));
END;
$$;

-- =============================================================================
-- calibration_placement_close  (tech §14)
-- =============================================================================
CREATE OR REPLACE FUNCTION public.calibration_placement_close(
    p_user_id uuid, p_session_id uuid, p_reason text)
RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_s       calibration_sessions%ROWTYPE;
    v_deleted integer;
BEGIN
    SELECT * INTO v_s FROM calibration_sessions
     WHERE id = p_session_id AND user_id = p_user_id AND mode = 'placement'
       FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'placement session not found' USING ERRCODE = 'P0002';
    END IF;

    IF v_s.ended_at IS NOT NULL THEN
        RETURN calibration_placement_tallies(p_session_id)
               || jsonb_build_object('session_id', v_s.id, 'stop_reason', v_s.stop_reason,
                                     'ended_at', v_s.ended_at, 'already_closed', true, 'deleted', 0);
    END IF;

    IF p_reason IS NULL
       OR p_reason NOT IN ('precision', 'cap', 'time', 'exhausted', 'learner', 'abandoned') THEN
        RAISE EXCEPTION 'invalid stop reason %', p_reason USING ERRCODE = '22023';
    END IF;

    DELETE FROM calibration_responses
     WHERE session_id = p_session_id AND answered_at IS NULL;
    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    UPDATE calibration_sessions
       SET ended_at     = now(),
           stop_reason  = p_reason,
           items_served = greatest(items_served - v_deleted, items_answered)
     WHERE id = p_session_id
    RETURNING * INTO v_s;

    RETURN calibration_placement_tallies(p_session_id)
           || jsonb_build_object('session_id', v_s.id, 'stop_reason', v_s.stop_reason,
                                 'ended_at', v_s.ended_at, 'already_closed', false, 'deleted', v_deleted);
END;
$$;

-- =============================================================================
-- calibration_placement_close_stale  (tech §14; nightly with p_user_id NULL)
-- =============================================================================
-- Closes open placements whose last activity (start, last serve, last answer) is older
-- than p_older_than, with stop_reason 'abandoned' and ended_at = that last activity.
-- Returns their ids; the caller runs finish() on each.
CREATE OR REPLACE FUNCTION public.calibration_placement_close_stale(
    p_user_id uuid, p_older_than interval DEFAULT '24 hours')
RETURNS uuid[]
LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    c         record;
    v_ids     uuid[] := '{}';
    v_deleted integer;
BEGIN
    IF p_older_than IS NULL OR p_older_than < interval '0' THEN
        RAISE EXCEPTION 'invalid interval %', p_older_than USING ERRCODE = '22023';
    END IF;

    FOR c IN
        SELECT cs.id,
               greatest(cs.started_at, max(r.served_at), max(r.answered_at)) AS last_at
          FROM calibration_sessions cs
          LEFT JOIN calibration_responses r ON r.session_id = cs.id
         WHERE cs.mode = 'placement' AND cs.ended_at IS NULL
           AND (p_user_id IS NULL OR cs.user_id = p_user_id)
         GROUP BY cs.id, cs.started_at
        HAVING greatest(cs.started_at, max(r.served_at), max(r.answered_at)) < now() - p_older_than
         ORDER BY cs.started_at, cs.id
    LOOP
        PERFORM 1 FROM calibration_sessions
          WHERE id = c.id AND ended_at IS NULL
            FOR UPDATE SKIP LOCKED;
        CONTINUE WHEN NOT FOUND;

        DELETE FROM calibration_responses WHERE session_id = c.id AND answered_at IS NULL;
        GET DIAGNOSTICS v_deleted = ROW_COUNT;

        UPDATE calibration_sessions
           SET ended_at     = c.last_at,
               stop_reason  = 'abandoned',
               items_served = greatest(items_served - v_deleted, items_answered)
         WHERE id = c.id;
        v_ids := v_ids || c.id;
    END LOOP;
    RETURN v_ids;
END;
$$;

-- =============================================================================
-- Lock-down: service role only (migrations/CLAUDE.md, TASK-881)
-- =============================================================================
REVOKE ALL ON FUNCTION public.calibration_placement_strip_definition(text, smallint, smallint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_reading_exempt(text, smallint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_units(text, smallint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_toneless(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_kana_pattern(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_well_formed_reading(text, smallint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_mora_skeleton(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_unit(double precision, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_meaning_parts(integer, smallint, smallint, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_reading_key(integer, smallint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_own_readings(integer, smallint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_reading_parts(integer, integer, smallint, text, text, double precision, integer[], text[]) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_reading_foil_counts(integer, integer, smallint, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_reading_ready(integer, smallint, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_candidates(uuid, uuid, smallint, smallint, smallint, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_band_has_word(uuid, uuid, smallint, smallint, smallint, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_draw(uuid, uuid, smallint, smallint, smallint, boolean, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_insert_item(uuid, uuid, integer, integer, text, real, smallint, text, text, text, bigint, integer[], text[], text[], integer, boolean, double precision, integer[]) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_option_texts(bigint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_item_payload(bigint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_reveal_reading(integer, smallint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_reveal(bigint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_tallies(uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_build_reading(uuid, uuid, smallint, integer, text, real, smallint, bigint, text, double precision, integer[], text[]) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_build_meaning(uuid, uuid, smallint, smallint, smallint, boolean, integer, double precision) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_build_recheck(uuid, uuid, smallint, double precision) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_ready_counts(smallint, smallint) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_next_item(uuid, uuid, smallint, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_answer(uuid, uuid, bigint, smallint, integer, smallint, jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_close(uuid, uuid, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.calibration_placement_close_stale(uuid, interval) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.calibration_placement_strip_definition(text, smallint, smallint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_reading_exempt(text, smallint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_units(text, smallint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_toneless(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_kana_pattern(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_well_formed_reading(text, smallint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_mora_skeleton(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_unit(double precision, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_meaning_parts(integer, smallint, smallint, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_reading_key(integer, smallint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_own_readings(integer, smallint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_reading_parts(integer, integer, smallint, text, text, double precision, integer[], text[]) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_reading_foil_counts(integer, integer, smallint, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_reading_ready(integer, smallint, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_candidates(uuid, uuid, smallint, smallint, smallint, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_band_has_word(uuid, uuid, smallint, smallint, smallint, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_draw(uuid, uuid, smallint, smallint, smallint, boolean, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_insert_item(uuid, uuid, integer, integer, text, real, smallint, text, text, text, bigint, integer[], text[], text[], integer, boolean, double precision, integer[]) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_option_texts(bigint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_item_payload(bigint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_reveal_reading(integer, smallint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_reveal(bigint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_tallies(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_build_reading(uuid, uuid, smallint, integer, text, real, smallint, bigint, text, double precision, integer[], text[]) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_build_meaning(uuid, uuid, smallint, smallint, smallint, boolean, integer, double precision) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_build_recheck(uuid, uuid, smallint, double precision) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_ready_counts(smallint, smallint) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_next_item(uuid, uuid, smallint, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_answer(uuid, uuid, bigint, smallint, integer, smallint, jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_close(uuid, uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.calibration_placement_close_stale(uuid, interval) TO service_role;

COMMIT;
