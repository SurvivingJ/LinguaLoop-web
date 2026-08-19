-- ============================================================================
-- Japanese counter drill (助数詞) — tables + session RPC
-- Date: 2026-08-11
-- Task: TASK-530 (exercise-generation-v2)
--
-- Clones the Chinese measure-word drill's architecture
-- (migrations/add_classifier_drill_mode.sql, add_classifier_groups.sql) for
-- Japanese counters. The two drills stay separate objects rather than one
-- parameterised drill: the distractor logic is the same shape but the
-- linguistic content is not, and the general-counter exclusions differ.
--
-- The three tables were created live on 2026-08-08 without a repo record;
-- their DDL below is written IF NOT EXISTS and matches the live definition, so
-- applying this file is a no-op for them (migrations/CLAUDE.md: migrations/
-- must reflect the current definition of every object). The RPC is new.
--
-- WHAT IS DELIBERATELY NOT HERE
-- -----------------------------
-- No 个-equivalent hard-coded exclusion. Chinese 个 is excluded from its drill
-- because it is the universal fallback classifier — testing it teaches
-- nothing. Japanese 個 is not the same case: it is one counter among several
-- for small objects and is genuinely wrong for most nouns, so it stays in the
-- pool. つ (the native-series general counter) is the closer analogue, and it
-- is handled through its distractor group's 'general' label rather than by
-- hard-coding a character the way the classifier RPC does.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.dim_counter_distractor_groups (
    id          smallint PRIMARY KEY,
    label       text NOT NULL UNIQUE,
    description text
);

CREATE TABLE IF NOT EXISTS public.dim_counters (
    id                  smallint PRIMARY KEY,
    language_id         smallint NOT NULL,
    counter             text     NOT NULL,
    reading             text,
    semantic_label      text,
    example_nouns       text[]   NOT NULL DEFAULT '{}'::text[],
    -- Euphonic change is the whole difficulty of Japanese counters:
    -- 一本 is いっぽん, 三本 さんぼん, 六本 ろっぽん. Stored per numeral so the
    -- drill can show or test them without re-deriving the sandhi rules.
    numeral_readings    jsonb,
    frequency_rank      integer,
    distractor_group_id smallint REFERENCES public.dim_counter_distractor_groups(id),
    difficulty_tier     smallint,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.dim_counter_noun_pairs (
    id              bigserial PRIMARY KEY,
    language_id     smallint NOT NULL,
    lemma_text      text     NOT NULL,
    noun_sense_id   integer,
    counter_id      smallint NOT NULL REFERENCES public.dim_counters(id),
    -- A noun may take several counters (うさぎ: 羽 traditional, 匹 colloquial).
    -- is_primary marks the one taught first; the drill accepts them all.
    is_primary      boolean  NOT NULL DEFAULT false,
    frequency_score real     NOT NULL DEFAULT 1.0,
    source          text     NOT NULL DEFAULT 'curated',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_counter_noun_pairs_lang_lemma
    ON public.dim_counter_noun_pairs (language_id, lemma_text);
CREATE INDEX IF NOT EXISTS idx_counter_noun_pairs_counter
    ON public.dim_counter_noun_pairs (counter_id);
CREATE INDEX IF NOT EXISTS idx_counters_lang_group
    ON public.dim_counters (language_id, distractor_group_id);

-- One (lemma, counter) fact per language: the build script upserts on it.
CREATE UNIQUE INDEX IF NOT EXISTS uq_counter_noun_pairs_lemma_counter
    ON public.dim_counter_noun_pairs (language_id, lemma_text, counter_id);

COMMIT;


-- ----------------------------------------------------------------------------
-- get_counter_drill_session
-- ----------------------------------------------------------------------------
-- Mirrors get_classifier_drill_session's semantics exactly, so the two drills
-- behave identically from the learner's side:
--
--   * one row per NOUN, not per pair — a noun with two acceptable counters
--     appears once, with both marked correct (multi-acceptable support);
--   * ALWAYS three distractors, topped up from the easy tiers when the noun's
--     own semantic group cannot supply them, because a two-option "multiple
--     choice" is a different exercise;
--   * distractors drawn from the answer's semantic group first, since a foil
--     from an unrelated group (枚 for a cat) is rejected on sight and tests
--     nothing.
--
-- p_user_id is accepted for signature parity with the classifier drill (and
-- for future per-user weighting); the current selection is user-independent.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.get_counter_drill_session(
    p_user_id     uuid,
    p_language_id smallint,
    p_count       integer DEFAULT 20
)
RETURNS TABLE(
    out_pair_id                 bigint,
    out_noun_lemma              text,
    out_noun_sense_id           integer,
    out_noun_gloss              text,
    out_noun_pronunciation      text,
    out_correct_counter_ids     smallint[],
    out_correct_counter_text    text[],
    out_correct_counter_reading text[],
    out_distractor_ids          smallint[],
    out_distractor_text         text[],
    out_distractor_reading      text[],
    out_numeral_readings        jsonb,
    out_semantic_label          text,
    out_distractor_group_label  text,
    out_difficulty_tier         smallint
)
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path = public
AS $function$
BEGIN
    RETURN QUERY
    WITH
    picked_lemmas AS (
        -- One row per noun. is_primary first, then a frequency-weighted
        -- random so common nouns lead without the set ever being fixed.
        SELECT DISTINCT ON (p.lemma_text)
            p.id            AS pair_id,
            p.lemma_text,
            p.noun_sense_id,
            p.counter_id    AS answer_counter_id,
            p.frequency_score
        FROM dim_counter_noun_pairs p
        WHERE p.language_id = p_language_id
        ORDER BY p.lemma_text, p.is_primary DESC, random() * p.frequency_score DESC
    ),
    sampled AS (
        SELECT * FROM picked_lemmas
        ORDER BY random()
        LIMIT GREATEST(p_count, 1)
    ),
    expanded AS (
        SELECT
            s.pair_id,
            s.lemma_text    AS lemma,
            s.noun_sense_id AS sense_id,
            s.answer_counter_id,
            ARRAY(
                SELECT p2.counter_id
                FROM dim_counter_noun_pairs p2
                WHERE p2.language_id = p_language_id
                  AND p2.lemma_text  = s.lemma_text
                ORDER BY p2.is_primary DESC, p2.frequency_score DESC
            )::smallint[] AS correct_ids
        FROM sampled s
    ),
    enriched AS (
        SELECT
            e.pair_id,
            e.lemma,
            e.sense_id,
            e.correct_ids,
            (SELECT ws.definition FROM dim_word_senses ws
              WHERE ws.id = e.sense_id LIMIT 1) AS gloss,
            (SELECT ws.pronunciation FROM dim_word_senses ws
              WHERE ws.id = e.sense_id LIMIT 1) AS pronunciation,
            c.distractor_group_id,
            c.semantic_label,
            c.difficulty_tier,
            c.numeral_readings,
            grp.label AS group_label
        FROM expanded e
        JOIN dim_counters c ON c.id = e.answer_counter_id
        JOIN dim_counter_distractor_groups grp ON grp.id = c.distractor_group_id
    ),
    with_distractors AS (
        SELECT
            en.*,
            -- 'general' is the つ/個-class catch-all group. Foils drawn from it
            -- are acceptable for almost any noun, so the group is skipped and
            -- the top-up below supplies real alternatives instead.
            CASE WHEN en.group_label = 'general' THEN
                ARRAY[]::smallint[]
            ELSE
                ARRAY(
                    SELECT d.id
                    FROM dim_counters d
                    WHERE d.language_id         = p_language_id
                      AND d.distractor_group_id = en.distractor_group_id
                      AND d.id <> ALL(en.correct_ids)
                    ORDER BY d.difficulty_tier ASC, random()
                    LIMIT 3
                )::smallint[]
            END AS distractor_ids
        FROM enriched en
    ),
    topped_up AS (
        SELECT
            wd.*,
            CASE
                WHEN COALESCE(array_length(wd.distractor_ids, 1), 0) < 3
                THEN (wd.distractor_ids || ARRAY(
                    SELECT d2.id
                    FROM dim_counters d2
                    WHERE d2.language_id      = p_language_id
                      AND d2.difficulty_tier <= 2
                      AND d2.id <> ALL(wd.correct_ids)
                      AND d2.id <> ALL(COALESCE(wd.distractor_ids, ARRAY[]::smallint[]))
                    ORDER BY random()
                    LIMIT (3 - COALESCE(array_length(wd.distractor_ids, 1), 0))
                ))::smallint[]
                ELSE wd.distractor_ids
            END AS final_distractor_ids
        FROM with_distractors wd
    )
    SELECT
        tu.pair_id,
        tu.lemma,
        tu.sense_id,
        tu.gloss,
        tu.pronunciation,
        tu.correct_ids,
        ARRAY(SELECT c.counter FROM dim_counters c
               WHERE c.id = ANY(tu.correct_ids)
               ORDER BY array_position(tu.correct_ids, c.id))::text[],
        ARRAY(SELECT c.reading FROM dim_counters c
               WHERE c.id = ANY(tu.correct_ids)
               ORDER BY array_position(tu.correct_ids, c.id))::text[],
        tu.final_distractor_ids,
        ARRAY(SELECT c.counter FROM dim_counters c
               WHERE c.id = ANY(tu.final_distractor_ids)
               ORDER BY array_position(tu.final_distractor_ids, c.id))::text[],
        ARRAY(SELECT c.reading FROM dim_counters c
               WHERE c.id = ANY(tu.final_distractor_ids)
               ORDER BY array_position(tu.final_distractor_ids, c.id))::text[],
        tu.numeral_readings,
        tu.semantic_label,
        tu.group_label,
        tu.difficulty_tier
    FROM topped_up tu
    ORDER BY random();
END;
$function$;


-- ----------------------------------------------------------------------------
-- Verification
-- ----------------------------------------------------------------------------
-- SELECT count(*) FROM public.dim_counters;              -- expect >= 40
-- SELECT count(*) FROM public.dim_counter_noun_pairs;    -- expect >= 300
--
-- Every returned row must carry exactly three distractors and at least one
-- correct answer — the two invariants the drill UI depends on:
-- SELECT count(*) AS bad_rows
--   FROM get_counter_drill_session(NULL::uuid, 3::smallint, 300)
--  WHERE cardinality(out_distractor_ids) <> 3
--     OR cardinality(out_correct_counter_ids) < 1;
--
-- No distractor may also be a correct answer:
-- SELECT count(*) FROM get_counter_drill_session(NULL::uuid, 3::smallint, 300)
--  WHERE out_distractor_ids && out_correct_counter_ids;
