-- TASK-812/813 harness deliverable — DRAFT, NOT APPLIED.
--
-- Moves en `vocab_prompt2_exercises`, `vocab_prompt3_transforms`, and any
-- en `ladder_*_generation` row currently on `anthropic/claude-sonnet-5` to
-- `qwen/qwen3.7-plus`, per the exercise-gen-cost.implementation-plan.md
-- Phase-1 smoke-run instruction ("for en add --model-override
-- vocab_prompt2_exercises:en=qwen/qwen3.7-plus --model-override
-- vocab_prompt3_transforms:en=qwen/qwen3.7-plus (plus any en
-- ladder_*_generation on sonnet)"). ADR-028 permits en generation to use any
-- model — this migration is NOT required by the ADR, it is the durable,
-- reviewable form of what the harness smoke run only ever does in-memory via
-- `scripts/run_exercise_gen_eval.py --model-override`. Filed so the operator
-- has a one-statement path to make that swap permanent AFTER the smoke run's
-- quality numbers are reviewed — this file must NOT be applied before that
-- review, and is not applied by this task.
--
-- Date: 2026-09-26 | Status: DRAFT, NOT APPLIED. Do not run against the live
-- DB without explicit operator/user approval of the Phase 1 smoke-run
-- results (phase1_smoke_en vs baseline_en, scored per TASK-807's protocol).
--
-- =============================================================================
-- LIVE STATE AT TIME OF WRITING (2026-09-26, read-only SELECT, no write made)
-- =============================================================================
-- SELECT task_name, language_id, version, model, provider, is_active,
--        position('JSON' in template_text) > 0 AS has_json
-- FROM prompt_templates
-- WHERE language_id = 2 AND is_active = true
--   AND (task_name IN ('vocab_prompt2_exercises', 'vocab_prompt3_transforms')
--        OR task_name LIKE 'ladder\_%\_generation' ESCAPE '\');
--
-- Returned (en, is_active=true):
--   vocab_prompt2_exercises          | v4 | anthropic/claude-sonnet-5 | openrouter | has_json=true
--   vocab_prompt3_transforms         | v2 | anthropic/claude-sonnet-5 | openrouter | has_json=true
--   ladder_l4_morphology_generation  | v1 | anthropic/claude-sonnet-5 | openrouter | has_json=true
--   ladder_word_family_generation    | v1 | anthropic/claude-sonnet-5 | openrouter | has_json=true
--   ladder_syn_ant_generation        | v1 | anthropic/claude-sonnet-5 | openrouter | has_json=true
--   ladder_l8_collocation_repair_generation | v1 | google/gemini-3.5-flash-lite | -- NOT sonnet, untouched
-- All five sonnet rows already contain the literal word "JSON" in
-- template_text, so the Qwen3.x `response_format: json_object` 400 landmine
-- (fires only when the prompt text does not say "JSON") does not apply to
-- any of them — no prompt-text patch is needed, matching TASK-809's zh/ja
-- finding for the same five task_names.
--
-- =============================================================================
-- WHAT THIS MIGRATION DOES
-- =============================================================================
-- For every ACTIVE prompt_templates row where:
--   * language_id = 2 (en)
--   * model = 'anthropic/claude-sonnet-5' exactly (not a broader "any non-qwen"
--     scan — unlike TASK-809's zh/ja migration, en is explicitly PERMITTED to
--     use any model per ADR-028, so this only targets the specific sonnet
--     rows the Phase 1 smoke run measured, not every en row)
--   * task_name IN ('vocab_prompt2_exercises', 'vocab_prompt3_transforms')
--     OR task_name LIKE 'ladder\_%\_generation'
-- ...insert a NEW version row (version = old max + 1) with the same
-- template_text (patched to insert a minimal "Respond with valid JSON only."
-- line if the literal word "JSON" is somehow missing — defensive, no row in
-- scope needs this today) and model = 'qwen/qwen3.7-plus', mark it active,
-- and deactivate the row(s) it supersedes. Explicit version bump via
-- DEACTIVATE + INSERT, not an UPDATE of the existing row and not an
-- `ON CONFLICT DO NOTHING` insert — same convention as
-- migrations/exercise_gen_zh_generation_to_qwen.sql (TASK-809) and the
-- standing ADR-028 constraint that a prompt migration must be a real version
-- bump, since `get_template_config`/`get_template_text`
-- (services/prompt_service.py) both select `is_active = true` ORDER BY
-- version DESC LIMIT 1.
--
-- Judges are out of scope (task_name pattern excludes '%_judge').
--
-- IDEMPOTENT: re-running is safe. The `model = 'anthropic/claude-sonnet-5'`
-- predicate on the source-row scan means a row already moved off sonnet by a
-- previous run of this file is not touched again.
--
-- =============================================================================
-- VERIFICATION (run manually before and after, if this is ever applied)
-- =============================================================================
-- Before:
--   SELECT task_name, version, model, is_active FROM prompt_templates
--   WHERE language_id = 2 AND is_active = true
--     AND (task_name IN ('vocab_prompt2_exercises', 'vocab_prompt3_transforms')
--          OR task_name LIKE 'ladder\_%\_generation' ESCAPE '\')
--   ORDER BY task_name;
--
-- After: same query — the five rows listed above should read
-- 'qwen/qwen3.7-plus'; any en row NOT on sonnet today (e.g.
-- ladder_l8_collocation_repair_generation, still gemini) is untouched.
--
-- =============================================================================
-- ROLLBACK
-- =============================================================================
-- Each row this migration touches gets a NEW version rather than being
-- overwritten, so rollback is a straight flip back:
--   UPDATE prompt_templates SET is_active = false, updated_at = now()
--     WHERE id IN (<the new qwen row ids printed by the DO block's RAISE NOTICE
--                   at apply time>);
--   UPDATE prompt_templates SET is_active = true, updated_at = now()
--     WHERE id IN (<the superseded sonnet row ids — same NOTICE output>);
-- Capture the DO block's NOTICE output (old id -> new id pairs) at apply time
-- and keep it alongside this file, exactly as TASK-809's migration documents.

BEGIN;

DO $$
DECLARE
    rec RECORD;
    new_version INTEGER;
    new_id INTEGER;
    patched_text TEXT;
    target_model CONSTANT TEXT := 'qwen/qwen3.7-plus';
    source_model CONSTANT TEXT := 'anthropic/claude-sonnet-5';
    touched_count INTEGER := 0;
BEGIN
    FOR rec IN
        SELECT id, task_name, language_id, version, template_text, provider, description
        FROM prompt_templates
        WHERE is_active = true
          AND language_id = 2  -- en
          AND model = source_model
          AND (
              task_name IN ('vocab_prompt2_exercises', 'vocab_prompt3_transforms')
              OR task_name LIKE 'ladder\_%\_generation' ESCAPE '\'
          )
    LOOP
        touched_count := touched_count + 1;

        -- Same defensive JSON-landmine guard as TASK-809's migration, even
        -- though every row in scope was confirmed to already contain "JSON"
        -- at the time this file was written — a template edited after that
        -- check should not silently reopen the 400 landmine on cutover.
        IF position('JSON' in rec.template_text) = 0 THEN
            patched_text := rec.template_text
                || E'\n\nRespond with valid JSON only.';
            RAISE NOTICE 'exercise_gen_en_p2_p3_off_sonnet: % (v%) had no '
                'literal "JSON" in its template text — appended a minimal '
                'JSON instruction line.', rec.task_name, rec.version;
        ELSE
            patched_text := rec.template_text;
        END IF;

        SELECT COALESCE(MAX(version), 0) + 1 INTO new_version
        FROM prompt_templates
        WHERE task_name = rec.task_name AND language_id = rec.language_id;

        UPDATE prompt_templates
           SET is_active = false, updated_at = now()
         WHERE id = rec.id;

        INSERT INTO prompt_templates
            (task_name, template_text, version, is_active, description,
             language_id, model, provider, created_at, updated_at)
        VALUES
            (rec.task_name, patched_text, new_version, true,
             COALESCE(rec.description, '') ||
                ' [exercise_gen_en_p2_p3_off_sonnet: model moved ' ||
                source_model || ' -> ' || target_model || ', ' ||
                to_char(now(), 'YYYY-MM-DD') || ']',
             rec.language_id, target_model,
             COALESCE(rec.provider, 'openrouter'), now(), now())
        RETURNING id INTO new_id;

        RAISE NOTICE 'exercise_gen_en_p2_p3_off_sonnet: % old row id=% (v%) '
            '-> new row id=% (v%, model=%)',
            rec.task_name, rec.id, rec.version, new_id, new_version, target_model;
    END LOOP;

    IF touched_count = 0 THEN
        RAISE NOTICE 'exercise_gen_en_p2_p3_off_sonnet: no qualifying en row '
            'on % found — either already moved, or none of the target '
            'task_names are on that model any more. No-op.', source_model;
    END IF;
END $$;

COMMIT;
