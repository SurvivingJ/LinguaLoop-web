-- TASK-821 (ADR-029, recalibration): per-language score thresholds for jev tiers.
--
-- 1. tests.age_tier_calibration — which score->tier mapping produced
--    target_age_tier ('default' = round half up; 'ja-2026-09-27' = fitted ja
--    thresholds). age_tier_score stays jev's RAW score, so any tier can be
--    re-derived under a different mapping without another call.
-- 2. tests_tier_backup_20260927_v1 — the state after the first (uncalibrated)
--    jev pass and before this recalibration, so it can be reversed:
--
--      UPDATE tests t
--         SET target_age_tier = b.target_age_tier, difficulty = b.difficulty,
--             age_tier_calibration = b.age_tier_calibration
--        FROM tests_tier_backup_20260927_v1 b WHERE b.test_id = t.id;
--
-- 3. apply_jev_retier now also writes age_tier_calibration ('default' if the
--    payload row has none).

ALTER TABLE tests ADD COLUMN IF NOT EXISTS age_tier_calibration text;

UPDATE tests SET age_tier_calibration = 'default'
 WHERE age_tier_score IS NOT NULL AND age_tier_calibration IS NULL;

CREATE TABLE IF NOT EXISTS tests_tier_backup_20260927_v1 (
    test_id              uuid PRIMARY KEY,
    target_age_tier      smallint,
    difficulty           integer,
    age_tier_calibration text,
    backed_up_at         timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE tests_tier_backup_20260927_v1 ENABLE ROW LEVEL SECURITY;

INSERT INTO tests_tier_backup_20260927_v1
    (test_id, target_age_tier, difficulty, age_tier_calibration)
SELECT t.id, t.target_age_tier, t.difficulty, t.age_tier_calibration
  FROM tests t
 WHERE t.is_active
   AND NOT EXISTS (SELECT 1 FROM tests_tier_backup_20260927_v1);

CREATE OR REPLACE FUNCTION public.apply_jev_retier(p_rows jsonb)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_expected integer := jsonb_array_length(p_rows);
    v_updated  integer;
BEGIN
    WITH v AS (
        SELECT (r->>'id')::uuid            AS id,
               (r->>'new_tier')::smallint  AS tier,
               (r->>'score')::real         AS score,
               (r->>'confidence')::real    AS conf,
               r->'probabilities'          AS probs,
               r->>'model'                 AS model,
               COALESCE(r->>'calibration', 'default') AS calibration
          FROM jsonb_array_elements(p_rows) AS r
    ), applied AS (
        UPDATE tests t
           SET difficulty = CASE WHEN t.target_age_tier IS DISTINCT FROM v.tier
                                 THEN c.difficulty_min ELSE t.difficulty END,
               target_age_tier        = v.tier,
               age_tier_score         = v.score,
               age_tier_confidence    = v.conf,
               age_tier_probabilities = v.probs,
               age_tier_model         = v.model,
               age_tier_calibration   = v.calibration,
               age_tier_assessed_at   = now()
          FROM v
          JOIN dim_complexity_tiers c ON c.id = v.tier
         WHERE t.id = v.id AND t.is_active
        RETURNING 1
    )
    SELECT count(*) INTO v_updated FROM applied;

    IF v_updated <> v_expected THEN
        RAISE EXCEPTION 'apply_jev_retier: expected % rows, updated % — rolled back',
            v_expected, v_updated;
    END IF;
    RETURN v_updated;
END;
$$;

REVOKE ALL ON FUNCTION public.apply_jev_retier(jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.apply_jev_retier(jsonb) TO service_role;
