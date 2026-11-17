-- Rollback for migrations/task998_classifier_drill_levels.sql. Not applied;
-- kept for an operator who needs to undo it.
--
-- 1. update_classifier_mastery: the exact live definition captured on
--    2026-11-17 with
--      SELECT pg_get_functiondef('public.update_classifier_mastery(uuid,smallint,boolean)'::regprocedure);
--    before task998 replaced it (proconfig search_path=public, pg_temp;
--    ACL {postgres=X, service_role=X}; SECURITY DEFINER; VOLATILE).
-- 2. get_classifier_drill_session_v2 is a new function: dropped. The original
--    get_classifier_drill_session(uuid, smallint, integer) was never changed.
--    services/drill_service.py falls back to it when v2 is missing.
-- 3. user_classifier_mastery.level_attempts is a new nullable column: dropped
--    AFTER the function that writes it is restored.
-- Rows written to user_classifier_mastery while task998 was live are kept
-- (they are valid under the old rule).

CREATE OR REPLACE FUNCTION public.update_classifier_mastery(p_user_id uuid, p_classifier_id smallint, p_is_correct boolean)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_row     user_classifier_mastery;
    v_alpha   numeric := 0.3;
    v_old_level smallint;
    v_promoted boolean := false;
    v_demoted  boolean := false;
BEGIN
    -- Upsert (lazy creation)
    INSERT INTO user_classifier_mastery (user_id, classifier_id)
    VALUES (p_user_id, p_classifier_id)
    ON CONFLICT (user_id, classifier_id) DO NOTHING;

    SELECT * INTO v_row FROM user_classifier_mastery
    WHERE user_id = p_user_id AND classifier_id = p_classifier_id;

    v_old_level := v_row.current_level;

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

    -- Promotion: attempts >= 5 AND ewma >= 0.80 AND level < 4
    IF v_row.attempts >= 5 AND v_row.ewma_accuracy >= 0.80 AND v_row.current_level < 4 THEN
        v_row.current_level := v_row.current_level + 1;
        v_row.promoted_at := now();
        v_promoted := true;
    END IF;

    -- Demotion: 3 wrong-in-a-row AND level > 1
    IF v_row.last_wrong_streak >= 3 AND v_row.current_level > 1 THEN
        v_row.current_level := v_row.current_level - 1;
        v_row.last_wrong_streak := 0;  -- reset after demotion
        v_demoted := true;
    END IF;

    UPDATE user_classifier_mastery
       SET attempts          = v_row.attempts,
           correct           = v_row.correct,
           ewma_accuracy     = v_row.ewma_accuracy,
           current_level     = v_row.current_level,
           last_wrong_streak = v_row.last_wrong_streak,
           promoted_at       = v_row.promoted_at,
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
        'demoted',  v_demoted
    );
END;
$function$;

REVOKE ALL ON FUNCTION public.update_classifier_mastery(uuid, smallint, boolean)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_classifier_mastery(uuid, smallint, boolean) TO service_role;

DROP FUNCTION IF EXISTS public.get_classifier_drill_session_v2(uuid, smallint, integer);

ALTER TABLE public.user_classifier_mastery DROP COLUMN IF EXISTS level_attempts;
