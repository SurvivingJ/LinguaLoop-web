-- TASK-820 (ADR-029): apply a jev re-tier as ONE atomic statement.
--
-- apply_jev_retier(p_rows) takes the array scripts/retier_tests_with_jev.py
-- saves in data/eval/jev_retier_<date>/results.json and updates every named
-- active test: target_age_tier, the age_tier_* audit columns, and
-- difficulty — rewritten only where the tier changed, to the bottom of the new
-- tier's dim_complexity_tiers band (what test generation writes). ELO is
-- deliberately untouched (ADR-029).
--
-- Raises — rolling the whole call back — unless exactly jsonb_array_length
-- rows were updated, so a partial re-tier cannot be committed.
--
-- Reverse with the UPDATE documented in task819_jev_tier_assignment.sql.

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
               r->>'model'                 AS model
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
