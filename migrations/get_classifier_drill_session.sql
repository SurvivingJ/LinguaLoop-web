-- ============================================================================
-- get_classifier_drill_session.sql
--
-- Builds a session batch of N items for the Measure Word Drill trainer.
-- Each item: a noun lemma, the noun's pronunciation/gloss, the set of
-- acceptable classifier IDs (CC-CEDICT-style multi-valid), and 3 distractor
-- classifier IDs drawn from the same semantic distractor group.
--
-- Weighting (v1, frequency-only): pairs with higher frequency_score and
-- primary status are sampled more often. Per-user mastery weighting is
-- deferred to Phase 2.
-- ============================================================================

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
    out_distractor_group_label text
) LANGUAGE plpgsql STABLE SECURITY DEFINER AS $$
BEGIN
    RETURN QUERY
    WITH
    -- 1. Pick N distinct noun lemmas, weighted by frequency_score
    picked_lemmas AS (
        SELECT DISTINCT ON (lemma_text)
            id, lemma_text, noun_sense_id, classifier_id, frequency_score
        FROM dim_classifier_noun_pairs
        WHERE language_id = p_language_id
          AND is_primary = true
        ORDER BY lemma_text, random() * frequency_score DESC
    ),
    sampled AS (
        SELECT * FROM picked_lemmas
        ORDER BY random()
        LIMIT GREATEST(p_count, 1)
    ),
    -- 2. For each sampled noun, gather ALL acceptable classifier IDs
    --    (CC-CEDICT-style; e.g. 狗 accepts both 只 and 条).
    expanded AS (
        SELECT
            s.id                                       AS pair_id,
            s.lemma_text                               AS lemma,
            s.noun_sense_id                            AS sense_id,
            s.classifier_id                            AS primary_classifier_id,
            ARRAY(
                SELECT p2.classifier_id
                FROM dim_classifier_noun_pairs p2
                WHERE p2.language_id = p_language_id
                  AND p2.lemma_text = s.lemma_text
                ORDER BY p2.is_primary DESC, p2.frequency_score DESC
            )::smallint[] AS correct_ids
        FROM sampled s
    ),
    -- 3. Look up noun gloss + pronunciation from dim_word_senses
    enriched AS (
        SELECT
            e.pair_id,
            e.lemma,
            e.sense_id,
            e.primary_classifier_id,
            e.correct_ids,
            COALESCE(
                (SELECT ws.definition
                 FROM dim_word_senses ws
                 WHERE ws.id = e.sense_id
                 LIMIT 1),
                NULL
            ) AS gloss,
            COALESCE(
                (SELECT ws.pronunciation
                 FROM dim_word_senses ws
                 WHERE ws.id = e.sense_id
                 LIMIT 1),
                NULL
            ) AS pronunciation,
            c.distractor_group_id,
            c.semantic_label,
            grp.label AS group_label
        FROM expanded e
        JOIN dim_classifiers c ON c.id = e.primary_classifier_id
        JOIN dim_classifier_distractor_groups grp ON grp.id = c.distractor_group_id
    ),
    -- 4. For each item, pull 3 distractor classifiers from the same group
    --    that are NOT acceptable answers for this noun.
    with_distractors AS (
        SELECT
            en.*,
            ARRAY(
                SELECT d.id
                FROM dim_classifiers d
                WHERE d.language_id = p_language_id
                  AND d.distractor_group_id = en.distractor_group_id
                  AND d.id <> ALL(en.correct_ids)
                ORDER BY random()
                LIMIT 3
            )::smallint[] AS distractor_ids
        FROM enriched en
    ),
    -- 5. If a group has < 3 alternatives, top up from 'general' fallback
    topped_up AS (
        SELECT
            wd.*,
            CASE
                WHEN array_length(wd.distractor_ids, 1) IS NULL
                  OR array_length(wd.distractor_ids, 1) < 3
                THEN (wd.distractor_ids || ARRAY(
                    SELECT d2.id
                    FROM dim_classifiers d2
                    JOIN dim_classifier_distractor_groups g2 ON g2.id = d2.distractor_group_id
                    WHERE d2.language_id = p_language_id
                      AND g2.label = 'general'
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
        tu.group_label
    FROM topped_up tu
    ORDER BY random();
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_classifier_drill_session(uuid, smallint, integer) TO authenticated;
