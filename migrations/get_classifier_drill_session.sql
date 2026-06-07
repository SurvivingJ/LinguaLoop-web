-- ============================================================================
-- get_classifier_drill_session.sql
--
-- Builds a session batch of N items for the Measure Word Drill trainer.
-- Each item: a noun lemma, the noun's pronunciation/gloss, the set of
-- acceptable classifier IDs (CC-CEDICT-style multi-valid), and 3 distractor
-- classifier IDs.
--
-- 个 (gè) is the CATCH-ALL classifier and is never trained: it is excluded as
-- both a correct answer and a distractor. Nouns whose ONLY acceptable
-- classifier is 个 are dropped from the pool entirely (nothing specific to
-- teach). The "answer classifier" used for distractor grouping is therefore
-- always a SPECIFIC classifier, never 个.
--
-- Distractor selection:
--   * Specific-group answers draw same-group peers, preferring common
--     (low difficulty_tier) classifiers, topped up from a core common pool.
--   * 'general'-group answers (台, 颗, 份, 道…) skip the polluted general
--     bucket and draw all distractors from the core common pool — real,
--     confusable classifiers (只/条/张/本…), the contrast the learner needs.
--
-- 个 is referenced BY HANZI (not a hard-coded id): build_classifier_dictionary.py
-- wipes and re-inserts classifiers, regenerating serial ids, so the id of 个 is
-- not stable across rebuilds.
--
-- Weighting (v1, frequency-only): pairs with higher frequency_score and
-- primary status are sampled more often. Per-user mastery weighting is
-- deferred to Phase 2.
-- ============================================================================

-- Return type gained out_difficulty_tier, so the old signature must be dropped
-- before CREATE (CREATE OR REPLACE cannot change a function's return type).
DROP FUNCTION IF EXISTS public.get_classifier_drill_session(uuid, smallint, integer);

CREATE OR REPLACE FUNCTION public.get_classifier_drill_session(
    p_user_id     uuid,
    p_language_id smallint,
    p_count       integer DEFAULT 20
) RETURNS TABLE (
    out_pair_id                integer,
    out_noun_lemma             text,
    out_noun_sense_id          integer,
    out_noun_gloss             text,
    out_noun_pronunciation     text,
    out_correct_classifier_ids smallint[],
    out_correct_classifier_hanzi text[],
    out_distractor_ids         smallint[],
    out_distractor_hanzi       text[],
    out_distractor_pinyin      text[],
    out_semantic_label         text,
    out_distractor_group_label text,
    out_difficulty_tier        smallint
) LANGUAGE plpgsql STABLE SECURITY DEFINER AS $$
DECLARE
    v_ge_id smallint;
BEGIN
    -- Resolve 个 by hanzi (may be NULL if absent; IS DISTINCT FROM handles that).
    SELECT id INTO v_ge_id
    FROM dim_classifiers
    WHERE language_id = p_language_id AND hanzi = '个'
    LIMIT 1;

    RETURN QUERY
    WITH
    -- 1. Pick N distinct noun lemmas, weighted by frequency_score. The
    --    representative "answer classifier" is the best NON-个 pair for the
    --    lemma (primary first, then frequency). Lemmas whose only acceptable
    --    classifier is 个 have no non-个 pair and drop out here.
    picked_lemmas AS (
        SELECT DISTINCT ON (p.lemma_text)
            p.id            AS pair_id,
            p.lemma_text,
            p.noun_sense_id,
            p.classifier_id AS answer_classifier_id,
            p.frequency_score
        FROM dim_classifier_noun_pairs p
        WHERE p.language_id = p_language_id
          AND p.classifier_id IS DISTINCT FROM v_ge_id
        ORDER BY p.lemma_text, p.is_primary DESC, random() * p.frequency_score DESC
    ),
    sampled AS (
        SELECT * FROM picked_lemmas
        ORDER BY random()
        LIMIT GREATEST(p_count, 1)
    ),
    -- 2. Gather ALL acceptable classifier IDs for the noun, EXCLUDING 个.
    expanded AS (
        SELECT
            s.pair_id,
            s.lemma_text            AS lemma,
            s.noun_sense_id         AS sense_id,
            s.answer_classifier_id,
            ARRAY(
                SELECT p2.classifier_id
                FROM dim_classifier_noun_pairs p2
                WHERE p2.language_id = p_language_id
                  AND p2.lemma_text = s.lemma_text
                  AND p2.classifier_id IS DISTINCT FROM v_ge_id
                ORDER BY p2.is_primary DESC, p2.frequency_score DESC
            )::smallint[] AS correct_ids
        FROM sampled s
    ),
    -- 3. Noun gloss + pronunciation, plus the answer classifier's group/tier.
    enriched AS (
        SELECT
            e.pair_id,
            e.lemma,
            e.sense_id,
            e.answer_classifier_id,
            e.correct_ids,
            (SELECT ws.definition
               FROM dim_word_senses ws WHERE ws.id = e.sense_id LIMIT 1) AS gloss,
            (SELECT ws.pronunciation
               FROM dim_word_senses ws WHERE ws.id = e.sense_id LIMIT 1) AS pronunciation,
            c.distractor_group_id,
            c.semantic_label,
            c.difficulty_tier,
            grp.label AS group_label
        FROM expanded e
        JOIN dim_classifiers c ON c.id = e.answer_classifier_id
        JOIN dim_classifier_distractor_groups grp ON grp.id = c.distractor_group_id
    ),
    -- 4. Same-group distractors for SPECIFIC groups (prefer common classifiers,
    --    exclude 个 and the correct answers). 'general'-group answers skip the
    --    polluted bucket and are filled entirely from the core pool in step 5.
    with_distractors AS (
        SELECT
            en.*,
            CASE WHEN en.group_label = 'general' THEN
                ARRAY[]::smallint[]
            ELSE
                ARRAY(
                    SELECT d.id
                    FROM dim_classifiers d
                    WHERE d.language_id = p_language_id
                      AND d.distractor_group_id = en.distractor_group_id
                      AND d.id IS DISTINCT FROM v_ge_id
                      AND d.id <> ALL(en.correct_ids)
                    ORDER BY d.difficulty_tier ASC, random()
                    LIMIT 3
                )::smallint[]
            END AS distractor_ids
        FROM enriched en
    ),
    -- 5. Top up to 3 from the CORE COMMON POOL (tier <= 2, never 个), excluding
    --    correct answers and already-chosen distractors.
    topped_up AS (
        SELECT
            wd.*,
            CASE
                WHEN array_length(wd.distractor_ids, 1) IS NULL
                  OR array_length(wd.distractor_ids, 1) < 3
                THEN (wd.distractor_ids || ARRAY(
                    SELECT d2.id
                    FROM dim_classifiers d2
                    WHERE d2.language_id = p_language_id
                      AND d2.difficulty_tier <= 2
                      AND d2.id IS DISTINCT FROM v_ge_id
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
        ARRAY(
            SELECT c.hanzi FROM dim_classifiers c
            WHERE c.id = ANY(tu.correct_ids)
            ORDER BY array_position(tu.correct_ids, c.id)
        )::text[] AS correct_hanzi,
        tu.final_distractor_ids,
        ARRAY(
            SELECT c.hanzi FROM dim_classifiers c
            WHERE c.id = ANY(tu.final_distractor_ids)
            ORDER BY array_position(tu.final_distractor_ids, c.id)
        )::text[] AS distractor_hanzi,
        ARRAY(
            SELECT c.pinyin_display FROM dim_classifiers c
            WHERE c.id = ANY(tu.final_distractor_ids)
            ORDER BY array_position(tu.final_distractor_ids, c.id)
        )::text[] AS distractor_pinyin,
        tu.semantic_label,
        tu.group_label,
        tu.difficulty_tier
    FROM topped_up tu
    ORDER BY random();
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_classifier_drill_session(uuid, smallint, integer) TO authenticated;
