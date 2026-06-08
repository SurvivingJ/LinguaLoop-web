-- ============================================================================
-- phase16_ladder_judge_reject_rates.sql
-- Vocabulary-ladder judge-as-data observability (Phase 4.3 / TASK-414).
-- Date: 2026-06-08
--
-- Read-only view v_ladder_judge_reject_rates: one row per
-- (language_id, ladder_level, prompt_version, judge_key) carrying the number of
-- exercises judged, the count of rejected candidate items, and the resulting
-- reject_rate. Lets prompt regressions surface (rising reject rate for a new
-- prompt_version) before learners ever see the degraded exercises.
--
-- Spec: wiki/tasklist/ladder-judge-layer.tasks.md (TASK-414, decision 5) and
-- wiki/reviews/exercise-generation-audit-2026-06-07.md (B3.6).
--
-- ----------------------------------------------------------------------------
-- Data sources
--
-- 1. Per-exercise judge sidecars (exercise_renderer.build_rows, decision 5).
--    Each judged renderer writes exercises.tags['<judge>_judge'] with integer
--    'rejected' and 'kept' members. The four keys:
--      cloze_judge              (L3, filter shape: rejected/kept distractors)
--      l1_distractor_judge      (L1, filter shape)
--      collocation_judge        (L5 filter + L8 verdict; L8 meta has kept=1)
--      sentence_validity_judge  (L6 filter + L7 verdict; L7 meta has kept=1)
--    prompt_version comes from word_assets.prompt_version via
--    exercises.word_asset_id -> word_assets.id.
--
-- 2. P1 sentence-corpus judge sidecar (asset_pipeline._judge_p1_sentences,
--    decision 4). P1 verdicts are NOT exercise tags — they live in
--    word_assets.validation_warnings (text[]) on the prompt1_core asset, one
--    string per non-accept sentence:
--      'P1 sentence[<i>] rejected (rating <r>): <reason>'
--      'P1 sentence[<i>] flagged  (rating <r>): <reason>'
--    Accepted sentences leave no marker, so an all-accept asset is
--    indistinguishable from an un-judged one. The P1 row is therefore computed
--    only over prompt1_core assets that carry at least one 'P1 sentence[' marker
--    (i.e. were judged and had >=1 flag/reject); its reject_rate is the rejected
--    fraction across those assets' sentence corpora. ladder_level is NULL and
--    judge_key is 'p1_sentence_judge'.
--
-- Columns: exercises_n (rows judged), rejected_n (items dropped), kept_n
-- (items kept), items_n (rejected_n + kept_n), reject_rate (rejected_n/items_n,
-- 4 dp). Pure SQL, no writes — safe to query on the live DB.
-- ============================================================================

CREATE OR REPLACE VIEW public.v_ladder_judge_reject_rates AS
WITH exercise_judges AS (
    SELECT
        e.language_id,
        e.ladder_level,
        wa.prompt_version,
        j.judge_key,
        COALESCE(NULLIF(e.tags -> j.judge_key ->> 'rejected', '')::int, 0) AS rejected,
        COALESCE(NULLIF(e.tags -> j.judge_key ->> 'kept',     '')::int, 0) AS kept
    FROM public.exercises e
    JOIN public.word_assets wa ON wa.id = e.word_asset_id
    CROSS JOIN LATERAL (
        VALUES ('cloze_judge'),
               ('l1_distractor_judge'),
               ('collocation_judge'),
               ('sentence_validity_judge')
    ) AS j(judge_key)
    WHERE e.tags ? j.judge_key
),
exercise_agg AS (
    SELECT
        language_id,
        ladder_level,
        prompt_version,
        judge_key,
        count(*)                  AS exercises_n,
        sum(rejected)             AS rejected_n,
        sum(kept)                 AS kept_n,
        sum(rejected + kept)      AS items_n
    FROM exercise_judges
    GROUP BY language_id, ladder_level, prompt_version, judge_key
),
p1_assets AS (
    SELECT
        wa.language_id,
        wa.prompt_version,
        COALESCE(jsonb_array_length(wa.content -> 'sentences'), 0) AS sent_n,
        (SELECT count(*) FROM unnest(wa.validation_warnings) w
            WHERE w LIKE 'P1 sentence[%] rejected%')               AS rejected_sent_n
    FROM public.word_assets wa
    WHERE wa.asset_type = 'prompt1_core'
      AND wa.validation_warnings IS NOT NULL
      AND EXISTS (
          SELECT 1 FROM unnest(wa.validation_warnings) w
          WHERE w LIKE 'P1 sentence[%'
      )
),
p1_agg AS (
    SELECT
        language_id,
        NULL::int            AS ladder_level,
        prompt_version,
        'p1_sentence_judge'  AS judge_key,
        count(*)             AS exercises_n,
        sum(rejected_sent_n) AS rejected_n,
        sum(sent_n - rejected_sent_n) AS kept_n,
        sum(sent_n)          AS items_n
    FROM p1_assets
    GROUP BY language_id, prompt_version
)
SELECT
    language_id,
    ladder_level,
    prompt_version,
    judge_key,
    exercises_n,
    rejected_n,
    kept_n,
    items_n,
    round(rejected_n::numeric / NULLIF(items_n, 0), 4) AS reject_rate
FROM exercise_agg
UNION ALL
SELECT
    language_id,
    ladder_level,
    prompt_version,
    judge_key,
    exercises_n,
    rejected_n,
    kept_n,
    items_n,
    round(rejected_n::numeric / NULLIF(items_n, 0), 4) AS reject_rate
FROM p1_agg;

COMMENT ON VIEW public.v_ladder_judge_reject_rates IS
    'Phase 4.3 judge-as-data: per (language_id, ladder_level, prompt_version, judge_key) '
    'reject rates from exercises.tags.<judge>_judge plus the P1 validation_warnings '
    'sidecar. Read-only. See migrations/phase16_ladder_judge_reject_rates.sql.';

-- ----------------------------------------------------------------------------
-- Verification (run manually after a render batch)
-- ----------------------------------------------------------------------------
-- SELECT * FROM public.v_ladder_judge_reject_rates ORDER BY reject_rate DESC;
