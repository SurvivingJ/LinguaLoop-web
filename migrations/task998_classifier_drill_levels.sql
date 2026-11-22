-- Measure-word drill: per-item levels, reverse and cloze payloads, and level
-- progression that does not skip levels. 2026-11-17 (TASK-998).
--
-- ROOT CAUSE (verified 2026-11-17 against the live catalog and git history):
--   The 2026-05-19 "Measure Word Trainer v2" change applied a v5
--   get_classifier_drill_session to the live database that returned
--   out_level, out_classifier_id_primary, out_reverse_noun_options and
--   out_cloze_* and restricted the pool by max_unlocked_tier(). That
--   definition was never committed to migrations/ (live migration history:
--   20260519082733 .. 20260519084411 get_classifier_drill_session_v2..v5_cloze).
--   On 2026-06-06 (live migration 20260606152415
--   classifier_drill_exclude_ge_and_improve_distractors) the repo file
--   migrations/get_classifier_drill_session.sql (still the v1 shape) was
--   extended with the 个 exclusion and re-applied with DROP + CREATE, which
--   replaced the live v5 with a 13-column function. Since then:
--     * every item has level NULL, so Auto mode only ever shows level 1;
--     * classifier_id_primary is NULL, so the player never adds an answer to
--       item_results and update_classifier_mastery is never called
--       (observed before the services/drill_service.py v1 fallback: no
--       user_classifier_mastery row older than 2026-11-17 02:02 UTC; a
--       20-item round on the real app on 2026-11-17 wrote a test_attempts row
--       and made no update_classifier_mastery call);
--     * the cloze table it read (dim_classifier_example_sentences) was dropped
--       on 2026-09-21 (archive_unused_modules_2026_09_21.sql).
--   The live and repo definitions of get_classifier_drill_session are the same
--   (13 columns); there is no newer unapplied definition in the repo.
--
-- WHAT THIS FILE DOES (backward compatible with the code deployed from main):
--   1. ADD COLUMN user_classifier_mastery.level_attempts integer (nullable, no
--      default: a catalog-only change, no table rewrite; the table has 44 rows,
--      all the test account's, measured 2026-11-17 before applying).
--   2. CREATE OR REPLACE update_classifier_mastery, SAME signature and return
--      type (jsonb). Promotion now needs 5 answers AT THE CURRENT LEVEL
--      (level_attempts) with EWMA >= 0.80, and level_attempts restarts at 0 on
--      every promotion or demotion. Before, once attempts >= 5 and EWMA >= 0.80,
--      each further correct answer promoted again, so a learner went
--      Choose -> Type -> Reverse -> Fill in on three consecutive correct answers
--      and never practised Type or Reverse. The returned jsonb gains the key
--      level_attempts; every existing key is unchanged. The row is now read
--      FOR UPDATE so two concurrent submits cannot lose an update.
--   3. NEW function get_classifier_drill_session_v2 (same arguments as the
--      existing get_classifier_drill_session, which is left untouched for the
--      deployed main code). It returns the 13 v1 columns, then:
--        out_level                 level to DRAW this item at (1 Choose,
--                                  2 Type, 3 Reverse, 4 Fill in): the learner's
--                                  level for the answer classifier, lowered to
--                                  what the content supports (4 needs a cloze
--                                  sentence, 3 needs three reverse nouns)
--        out_mastery_level         the learner's stored level (1 when none)
--        out_classifier_id_primary the answer classifier (= correct ids[0]);
--                                  mastery is recorded against it
--        out_reverse_noun_options  3 nouns that do NOT take the answer
--                                  classifier (wrong options of Reverse)
--        out_cloze_sentence        a sentence with <numeral><classifier><noun>
--        out_cloze_blanked         the same sentence with the classifier
--                                  replaced by ___ (NULL when unusable)
--        out_max_tier              max_unlocked_tier() for the learner
--      Changes against v1 beyond the added columns:
--        * the pool is restricted to classifiers with difficulty_tier <=
--          max_unlocked_tier(user) (the 2026-05-19 design: a new learner works
--          on the 11 tier-1 classifiers, the next tier unlocks when 80% of a
--          tier is at level 2+). This is what makes promotion reachable: with
--          ~150 classifiers in the pool a classifier came up about once per
--          10 rounds;
--        * the answer classifier is listed first in out_correct_classifier_ids
--          so the Choose/Type answer, the Reverse prompt, the cloze blank and
--          the mastery row all name the same classifier;
--        * lemmas are sampled with weight 1/sqrt(nouns of their answer
--          classifier), so each unlocked classifier comes up about equally
--          often instead of in proportion to its noun count;
--        * for a classifier at level 4 the lemma's pair that has a cloze
--          sentence is preferred, and such lemmas weigh 1.5x, so Fill in
--          actually comes up;
--        * a lemma with no linked sense falls back to the lemma's first
--          monolingual sense in dim_word_senses for gloss and pronunciation
--          (lemmas with a pronunciation: 132 -> 523 of 1,573 measured
--          2026-11-17).
--      STABLE SECURITY DEFINER, search_path pinned, EXECUTE for service_role
--      only (as get_classifier_drill_session).
--
-- Cloze sentences are stored in the existing, all-NULL column
-- dim_classifier_noun_pairs.example_sentence by the separate data fill
-- migrations/task998_classifier_cloze_sentences_fill.sql. Without that fill
-- this function still works; no item reaches level 4 and level-4 classifiers
-- are drawn as Reverse.
--
-- Rollback: migrations/task998_classifier_drill_levels_rollback.sql (restores
-- the exact previous update_classifier_mastery captured with
-- pg_get_functiondef on 2026-11-17, drops the new function and column).
-- Tests: tests/sql/test_task998_classifier_drill_levels.sql (rollback-only),
--        tests/test_classifier_drill_levels.py (no database).

-- ---------------------------------------------------------------------------
-- 1. Answers at the current level
-- ---------------------------------------------------------------------------
ALTER TABLE public.user_classifier_mastery
    ADD COLUMN IF NOT EXISTS level_attempts integer;

COMMENT ON COLUMN public.user_classifier_mastery.level_attempts IS
    'Answers since current_level last changed (TASK-998). NULL on rows written '
    'before the column existed: treated as attempts.';

-- ---------------------------------------------------------------------------
-- 2. update_classifier_mastery: promote one level per 5 answers at that level
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_classifier_mastery(
    p_user_id uuid,
    p_classifier_id smallint,
    p_is_correct boolean
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $function$
DECLARE
    v_row        user_classifier_mastery;
    v_alpha      numeric := 0.3;
    v_old_level  smallint;
    v_level_n    integer;
    v_promoted   boolean := false;
    v_demoted    boolean := false;
BEGIN
    -- Upsert (lazy creation)
    INSERT INTO user_classifier_mastery (user_id, classifier_id, level_attempts)
    VALUES (p_user_id, p_classifier_id, 0)
    ON CONFLICT (user_id, classifier_id) DO NOTHING;

    SELECT * INTO v_row FROM user_classifier_mastery
    WHERE user_id = p_user_id AND classifier_id = p_classifier_id
    FOR UPDATE;

    v_old_level := v_row.current_level;
    -- Rows written before level_attempts existed: every attempt so far counts
    -- as an attempt at the current level (the old rule's view).
    v_level_n := COALESCE(v_row.level_attempts, v_row.attempts) + 1;

    -- Update counters
    v_row.attempts := v_row.attempts + 1;
    IF p_is_correct THEN
        v_row.correct := v_row.correct + 1;
        v_row.last_wrong_streak := 0;
    ELSE
        v_row.last_wrong_streak := v_row.last_wrong_streak + 1;
    END IF;

    -- EWMA update; seed from raw accuracy on first attempt
    IF v_row.attempts = 1 THEN
        v_row.ewma_accuracy := CASE WHEN p_is_correct THEN 1.0 ELSE 0.0 END;
    ELSE
        v_row.ewma_accuracy := v_alpha * (CASE WHEN p_is_correct THEN 1.0 ELSE 0.0 END)
                             + (1 - v_alpha) * v_row.ewma_accuracy;
    END IF;

    -- Promotion: 5 answers at this level AND ewma >= 0.80 AND level < 4
    IF v_level_n >= 5 AND v_row.ewma_accuracy >= 0.80 AND v_row.current_level < 4 THEN
        v_row.current_level := v_row.current_level + 1;
        v_row.promoted_at := now();
        v_promoted := true;
        v_level_n := 0;
    END IF;

    -- Demotion: 3 wrong-in-a-row AND level > 1
    IF v_row.last_wrong_streak >= 3 AND v_row.current_level > 1 THEN
        v_row.current_level := v_row.current_level - 1;
        v_row.last_wrong_streak := 0;  -- reset after demotion
        v_demoted := true;
        v_level_n := 0;
    END IF;

    UPDATE user_classifier_mastery
       SET attempts          = v_row.attempts,
           correct           = v_row.correct,
           ewma_accuracy     = v_row.ewma_accuracy,
           current_level     = v_row.current_level,
           last_wrong_streak = v_row.last_wrong_streak,
           promoted_at       = v_row.promoted_at,
           level_attempts    = v_level_n,
           last_attempted_at = now(),
           updated_at        = now()
     WHERE user_id = p_user_id AND classifier_id = p_classifier_id;

    RETURN jsonb_build_object(
        'classifier_id', p_classifier_id,
        'attempts', v_row.attempts,
        'correct',  v_row.correct,
        'ewma_accuracy', v_row.ewma_accuracy,
        'current_level', v_row.current_level,
        'old_level',     v_old_level,
        'promoted', v_promoted,
        'demoted',  v_demoted,
        'level_attempts', v_level_n
    );
END;
$function$;

REVOKE ALL ON FUNCTION public.update_classifier_mastery(uuid, smallint, boolean)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_classifier_mastery(uuid, smallint, boolean) TO service_role;

-- ---------------------------------------------------------------------------
-- 3. get_classifier_drill_session_v2
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.get_classifier_drill_session_v2(
    p_user_id     uuid,
    p_language_id smallint,
    p_count       integer DEFAULT 20
) RETURNS TABLE (
    out_pair_id                  integer,
    out_noun_lemma               text,
    out_noun_sense_id            integer,
    out_noun_gloss               text,
    out_noun_pronunciation       text,
    out_correct_classifier_ids   smallint[],
    out_correct_classifier_hanzi text[],
    out_distractor_ids           smallint[],
    out_distractor_hanzi         text[],
    out_distractor_pinyin        text[],
    out_semantic_label           text,
    out_distractor_group_label   text,
    out_difficulty_tier          smallint,
    out_level                    smallint,
    out_mastery_level            smallint,
    out_classifier_id_primary    smallint,
    out_reverse_noun_options     text[],
    out_cloze_sentence           text,
    out_cloze_blanked            text,
    out_max_tier                 smallint
) LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_ge_id smallint;
    v_tier  smallint;
BEGIN
    -- 个 by hanzi: the dictionary build regenerates serial ids.
    SELECT id INTO v_ge_id
    FROM dim_classifiers
    WHERE language_id = p_language_id AND hanzi = '个'
    LIMIT 1;

    v_tier := COALESCE(max_unlocked_tier(p_user_id, p_language_id), 1);

    RETURN QUERY
    WITH
    mastery AS (
        SELECT m.classifier_id, m.current_level
        FROM user_classifier_mastery m
        WHERE m.user_id = p_user_id
    ),
    -- 1. Every servable pair: not 个, classifier within the unlocked tiers.
    --    cloze_blanked is usable only when the classifier occurs once in the
    --    sentence (else the blank is given away) and is followed by the noun.
    candidates AS (
        SELECT
            p.id              AS pair_id,
            p.lemma_text,
            p.noun_sense_id,
            p.classifier_id,
            p.is_primary,
            p.frequency_score,
            COALESCE(ms.current_level, 1)::smallint AS mastery_level,
            CASE WHEN p.example_sentence IS NOT NULL THEN p.example_sentence END AS cloze_sentence,
            CASE
                WHEN p.example_sentence IS NOT NULL
                 AND char_length(c.hanzi) = 1
                 AND char_length(p.example_sentence)
                     - char_length(replace(p.example_sentence, c.hanzi, '')) = 1
                 AND strpos(p.example_sentence, c.hanzi || p.lemma_text) > 0
                THEN replace(p.example_sentence, c.hanzi || p.lemma_text, '___' || p.lemma_text)
            END AS cloze_blanked
        FROM dim_classifier_noun_pairs p
        JOIN dim_classifiers c ON c.id = p.classifier_id
        LEFT JOIN mastery ms ON ms.classifier_id = p.classifier_id
        WHERE p.language_id = p_language_id
          AND p.classifier_id IS DISTINCT FROM v_ge_id
          AND COALESCE(c.difficulty_tier, 4) <= v_tier
    ),
    -- 2. One answer pair per lemma: a level-4 classifier's pair with a usable
    --    cloze sentence first, then primary, then frequency-weighted random.
    picked_lemmas AS (
        SELECT DISTINCT ON (cd.lemma_text)
            cd.*,
            (cd.mastery_level >= 4 AND cd.cloze_blanked IS NOT NULL) AS cloze_ready
        FROM candidates cd
        ORDER BY cd.lemma_text,
                 (cd.mastery_level >= 4 AND cd.cloze_blanked IS NOT NULL) DESC,
                 cd.is_primary DESC,
                 random() * cd.frequency_score DESC
    ),
    -- Weighted sampling without replacement (key = -ln(u) / w, smallest
    -- first). w = 1 / sqrt(nouns of the answer classifier) evens out how
    -- often each classifier comes up (只 has ~90 nouns, 杯 ~17), so every
    -- classifier gets the answers it needs to move up a level; x1.5 for a
    -- level-4 classifier's noun that has a cloze sentence.
    weighted AS (
        SELECT pl.*,
               count(*) OVER (PARTITION BY pl.classifier_id) AS n_cls
        FROM picked_lemmas pl
    ),
    sampled AS (
        SELECT * FROM weighted w
        ORDER BY -ln(1.0 - random())
                 * sqrt(w.n_cls::double precision)
                 / (CASE WHEN w.cloze_ready THEN 1.5 ELSE 1.0 END)
        LIMIT GREATEST(p_count, 1)
    ),
    -- 3. All acceptable classifiers for the noun except 个, the answer first.
    expanded AS (
        SELECT
            s.*,
            ARRAY(
                SELECT p2.classifier_id
                FROM dim_classifier_noun_pairs p2
                WHERE p2.language_id = p_language_id
                  AND p2.lemma_text = s.lemma_text
                  AND p2.classifier_id IS DISTINCT FROM v_ge_id
                ORDER BY (p2.classifier_id = s.classifier_id) DESC,
                         p2.is_primary DESC, p2.frequency_score DESC, p2.classifier_id
            )::smallint[] AS correct_ids
        FROM sampled s
    ),
    -- 4. Gloss and pronunciation: the linked sense, else the lemma's first
    --    monolingual sense that has a pronunciation.
    enriched AS (
        SELECT
            e.*,
            COALESCE(ls.id, fb.id)                       AS sense_id_out,
            COALESCE(ls.definition, fb.definition)       AS gloss,
            COALESCE(NULLIF(ls.pronunciation, ''), fb.pronunciation) AS pronunciation,
            c.distractor_group_id,
            c.semantic_label,
            c.difficulty_tier,
            grp.label AS group_label
        FROM expanded e
        JOIN dim_classifiers c ON c.id = e.classifier_id
        JOIN dim_classifier_distractor_groups grp ON grp.id = c.distractor_group_id
        LEFT JOIN LATERAL (
            SELECT ws.id, ws.definition, ws.pronunciation
            FROM dim_word_senses ws
            WHERE ws.id = e.noun_sense_id
        ) ls ON true
        LEFT JOIN LATERAL (
            SELECT ws.id, ws.definition, ws.pronunciation
            FROM dim_vocabulary v
            JOIN dim_word_senses ws ON ws.vocab_id = v.id
            WHERE (ls.id IS NULL OR COALESCE(ls.pronunciation, '') = '')
              AND v.language_id = p_language_id
              AND v.lemma = e.lemma_text
              AND ws.definition_language_id = p_language_id
              AND COALESCE(ws.pronunciation, '') <> ''
            ORDER BY ws.sense_rank NULLS LAST, ws.definition_level NULLS LAST, ws.id
            LIMIT 1
        ) fb ON true
    ),
    -- 5. Same-group distractors for specific groups (as v1).
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
    -- 6. Top up to 3 from the core pool (tier <= 2, never 个) (as v1).
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
    ),
    -- 7. Reverse: 3 common curated nouns that take none of the noun's
    --    classifiers and, for a specific group, no classifier of the answer's
    --    group (so a wrong option is not secretly right).
    with_reverse AS (
        SELECT
            tu.*,
            ARRAY(
                SELECT q.lemma_text
                FROM (
                    SELECT DISTINCT p3.lemma_text
                    FROM dim_classifier_noun_pairs p3
                    JOIN dim_classifiers c3 ON c3.id = p3.classifier_id
                    WHERE p3.language_id = p_language_id
                      AND p3.source = 'curated'
                      AND p3.lemma_text <> tu.lemma_text
                      AND p3.classifier_id IS DISTINCT FROM v_ge_id
                      AND COALESCE(c3.difficulty_tier, 4) <= 2
                      AND NOT EXISTS (
                          SELECT 1
                          FROM dim_classifier_noun_pairs p4
                          JOIN dim_classifiers c4 ON c4.id = p4.classifier_id
                          WHERE p4.language_id = p_language_id
                            AND p4.lemma_text = p3.lemma_text
                            AND (p4.classifier_id = ANY(tu.correct_ids)
                                 OR (tu.group_label <> 'general'
                                     AND c4.distractor_group_id = tu.distractor_group_id))
                      )
                ) q
                ORDER BY random()
                LIMIT 3
            )::text[] AS reverse_nouns
        FROM topped_up tu
    )
    SELECT
        wr.pair_id              AS pair_id,
        wr.lemma_text           AS noun_lemma,
        wr.sense_id_out         AS noun_sense_id,
        wr.gloss                AS noun_gloss,
        wr.pronunciation        AS noun_pronunciation,
        wr.correct_ids          AS correct_classifier_ids,
        ARRAY(
            SELECT c.hanzi FROM dim_classifiers c
            WHERE c.id = ANY(wr.correct_ids)
            ORDER BY array_position(wr.correct_ids, c.id)
        )::text[]               AS correct_classifier_hanzi,
        wr.final_distractor_ids AS distractor_ids,
        ARRAY(
            SELECT c.hanzi FROM dim_classifiers c
            WHERE c.id = ANY(wr.final_distractor_ids)
            ORDER BY array_position(wr.final_distractor_ids, c.id)
        )::text[]               AS distractor_hanzi,
        ARRAY(
            SELECT c.pinyin_display FROM dim_classifiers c
            WHERE c.id = ANY(wr.final_distractor_ids)
            ORDER BY array_position(wr.final_distractor_ids, c.id)
        )::text[]               AS distractor_pinyin,
        wr.semantic_label       AS semantic_label,
        wr.group_label          AS distractor_group_label,
        wr.difficulty_tier      AS difficulty_tier,
        (CASE
            WHEN wr.mastery_level >= 4 AND wr.cloze_blanked IS NOT NULL THEN 4
            WHEN wr.mastery_level >= 3 AND COALESCE(array_length(wr.reverse_nouns, 1), 0) = 3 THEN 3
            WHEN wr.mastery_level >= 2 THEN 2
            ELSE 1
        END)::smallint          AS level,
        wr.mastery_level        AS mastery_level,
        wr.classifier_id        AS classifier_id_primary,
        wr.reverse_nouns        AS reverse_noun_options,
        wr.cloze_sentence       AS cloze_sentence,
        wr.cloze_blanked        AS cloze_blanked,
        v_tier                  AS max_tier
    FROM with_reverse wr
    ORDER BY random();
END;
$$;

REVOKE ALL ON FUNCTION public.get_classifier_drill_session_v2(uuid, smallint, integer)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_classifier_drill_session_v2(uuid, smallint, integer) TO service_role;
