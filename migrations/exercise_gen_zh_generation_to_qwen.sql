-- TASK-809: Move zh (and ja) vocabulary-ladder GENERATION prompts to the qwen
-- family, per ADR-028 Decision §2 ("zh and ja generation uses the qwen family
-- only; en generation may use any model").
--
-- Date: 2026-09-26 | Status: DRAFT, NOT APPLIED. Approved by user 2026-09-26
-- per wiki/tasklist/exercise-gen-cost.tasks.md TASK-809; still not run against
-- the live DB pending Phase 0 baseline (TASK-808) landing, per that task's
-- Depends On.
--
-- =============================================================================
-- IMPORTANT — 2026-09-26 VERIFICATION FINDING
-- =============================================================================
-- A live query against `prompt_templates` (project kpfqrjtfxmujzolwsvdq) found
-- that every zh/ja row in TASK-809's stated scope is ALREADY on
-- `qwen/qwen3.7-plus` and already `is_active = true`:
--
--   task_name                     | lang | version | model              | is_active
--   vocab_prompt1_core            | zh   | 2       | qwen/qwen3.7-plus  | true
--   vocab_prompt1_core            | ja   | 3       | qwen/qwen3.7-plus  | true
--   vocab_prompt2_exercises       | zh   | 4       | qwen/qwen3.7-plus  | true
--   vocab_prompt2_exercises       | ja   | 4       | qwen/qwen3.7-plus  | true
--   vocab_prompt3_transforms      | zh   | 2       | qwen/qwen3.7-plus  | true
--   vocab_prompt3_transforms      | ja   | 1       | qwen/qwen3.7-plus  | true
--   ladder_l4_morphology_generation           | zh, ja | qwen/qwen3.7-plus | true
--   ladder_l8_collocation_repair_generation    | zh, ja | qwen/qwen3.7-plus | true
--   ladder_syn_ant_generation                  | zh, ja | qwen/qwen3.7-plus | true
--   ladder_particle_selection_generation       | ja     | qwen/qwen3.7-plus | true
--
-- ADR-028's "Current model assignment" paragraph (dated 2026-09-24) describing
-- zh prompt2/prompt3 as `anthropic/claude-sonnet-5` and zh prompt1_core as
-- gemini is STALE as of this check. The rows' `updated_at` is 2026-08-17
-- 21:49:11 UTC across the board (a bulk change) — one day AFTER
-- `migrations/generator_model_routing_policy.sql` (dated 2026-08-16), which
-- explicitly *preserved* vocab_prompt2_exercises/vocab_prompt3_transforms/
-- ladder_l4_morphology_generation/ladder_syn_ant_generation as deliberate
-- claude-sonnet-5 exclusions. So a later, untracked change on 2026-08-17 is
-- what actually moved zh onto qwen for these three prompts — there is no
-- migration file in this repo recording that move. (En rows for the SAME
-- task_names are still on claude-sonnet-5 (`vocab_prompt2_exercises`,
-- `vocab_prompt3_transforms`, `ladder_l4_morphology_generation`,
-- `ladder_syn_ant_generation`, `ladder_word_family_generation`, updated_at
-- 2026-05-02..2026-08-10) or gemini (`vocab_prompt1_core`,
-- `ladder_l8_collocation_repair_generation`) — permitted, en generation may
-- use any model.)
--
-- All ten rows above were also confirmed (same query) to contain the literal
-- substring "JSON" in `template_text`, so the Qwen3.x
-- `response_format: json_object` landmine (400 if the prompt text does not
-- say "JSON") does not fire for any of them. No prompt-text patch is needed.
--
-- CONSEQUENCE: this migration is a NO-OP against the live DB today. It is
-- still filed, per TASK-809's deliverable, as (a) a durable historical record
-- that the state was checked and is correct, and (b) a generic, idempotent
-- guard that self-heals if a zh/ja generation row ever drifts back off qwen
-- (e.g. a future prompt-text edit that reactivates an older non-qwen version,
-- or a new ladder_*_generation task_name added without the model-family rule
-- applied). It is NOT a mechanical restatement of ADR-028's stale paragraph.
--
-- =============================================================================
-- WHAT THIS MIGRATION DOES
-- =============================================================================
-- For every ACTIVE prompt_templates row where:
--   * language_id IN (1 [zh], 3 [ja])
--   * task_name = 'vocab_prompt1_core' OR 'vocab_prompt2_exercises'
--     OR 'vocab_prompt3_transforms' OR task_name LIKE 'ladder_%_generation'
--   * model IS NOT NULL AND model NOT LIKE 'qwen/%'
-- ...insert a NEW version row (version = old max + 1) with the same
-- template_text (patched to insert the word "JSON" if missing — see the
-- `has_json` check below) and model = 'qwen/qwen3.7-plus', mark it active,
-- and deactivate the row(s) it supersedes. This is an explicit version bump,
-- NOT an UPDATE of the existing row and NOT an `ON CONFLICT DO NOTHING`
-- insert — per ADR-028's standing constraint ("Prompt migrations need
-- DO UPDATE / an explicit version bump ... a bare insert silently no-ops on a
-- corrected re-run") and per `get_template_config`/`get_template_text`
-- (services/prompt_service.py), which both select `is_active = true` and
-- `ORDER BY version DESC LIMIT 1` — so a new highest-version active row is
-- what actually changes what's served, and the old row is preserved as
-- history rather than overwritten.
--
-- Judges are explicitly OUT OF SCOPE (task_name NOT LIKE '%_judge' and not
-- matched by the patterns above in the first place) — ADR-028 open question
-- (a) leaves judges on their current models pending a separate operator
-- decision; this migration touches GENERATION only.
--
-- IDEMPOTENT: re-running this migration is safe. The `WHERE model NOT LIKE
-- 'qwen/%'` predicate on the source-row scan means a row already moved to
-- qwen by a previous run of this file (or by the 2026-08-17 change already
-- live) is not touched again, and no duplicate version is inserted.
--
-- =============================================================================
-- VERIFICATION (run manually before and after)
-- =============================================================================
-- Before:
--   SELECT task_name, language_id, version, model, is_active
--   FROM prompt_templates
--   WHERE language_id IN (1, 3)
--     AND (task_name IN ('vocab_prompt1_core','vocab_prompt2_exercises','vocab_prompt3_transforms')
--          OR task_name LIKE 'ladder_%_generation')
--     AND is_active = true
--   ORDER BY task_name, language_id;
--
-- After: same query — every model column should read 'qwen/qwen3.7-plus'.
-- Also confirm no row lost its "JSON" literal:
--   SELECT task_name, language_id, version
--   FROM prompt_templates
--   WHERE is_active = true AND language_id IN (1, 3)
--     AND (task_name IN ('vocab_prompt1_core','vocab_prompt2_exercises','vocab_prompt3_transforms')
--          OR task_name LIKE 'ladder_%_generation')
--     AND position('JSON' in template_text) = 0;
-- (expect 0 rows)
--
-- =============================================================================
-- ROLLBACK
-- =============================================================================
-- Each row this migration touches gets a NEW version, so rollback is:
--   UPDATE prompt_templates SET is_active = false, updated_at = now()
--     WHERE id IN (<the new row ids printed by the DO block's RAISE NOTICE>);
--   UPDATE prompt_templates SET is_active = true, updated_at = now()
--     WHERE id IN (<the superseded row ids — same list>);
-- Since this migration is a no-op today (no row currently qualifies), there is
-- nothing to roll back on first application. If a future re-run does insert
-- rows because of drift, the DO block below prints (via RAISE NOTICE) the
-- exact old-id -> new-id pairs it touched; capture that output at apply time
-- and keep it with this file for anyone who needs to revert.

BEGIN;

DO $$
DECLARE
    rec RECORD;
    new_version INTEGER;
    new_id INTEGER;
    patched_text TEXT;
    target_model CONSTANT TEXT := 'qwen/qwen3.7-plus';
BEGIN
    FOR rec IN
        SELECT id, task_name, language_id, version, template_text, provider, description
        FROM prompt_templates
        WHERE is_active = true
          AND language_id IN (1, 3)  -- zh, ja
          AND model IS NOT NULL
          AND model NOT LIKE 'qwen/%'
          AND (
              task_name IN ('vocab_prompt1_core', 'vocab_prompt2_exercises', 'vocab_prompt3_transforms')
              OR task_name LIKE 'ladder\_%\_generation' ESCAPE '\'
          )
    LOOP
        -- Landmine guard: Qwen3.x + response_format=json_object 400s unless
        -- the prompt text literally contains "JSON". Append a minimal,
        -- non-disruptive instruction line if it's missing, rather than
        -- silently shipping a prompt that will 400 on first use under qwen.
        IF position('JSON' in rec.template_text) = 0 THEN
            patched_text := rec.template_text
                || E'\n\nRespond with valid JSON only.';
            RAISE NOTICE 'TASK-809: % (lang %, v%) had no literal "JSON" in its '
                'template text — appended a minimal JSON instruction line.',
                rec.task_name, rec.language_id, rec.version;
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
             COALESCE(rec.description, '') || ' [TASK-809: model moved to qwen family, ' ||
                to_char(now(), 'YYYY-MM-DD') || ']',
             rec.language_id, target_model,
             COALESCE(rec.provider, 'openrouter'), now(), now())
        RETURNING id INTO new_id;

        RAISE NOTICE 'TASK-809: % (lang %) old row id=% (v%, model=deactivated) '
            '-> new row id=% (v%, model=%)',
            rec.task_name, rec.language_id, rec.id, rec.version,
            new_id, new_version, target_model;
    END LOOP;

    IF NOT FOUND THEN
        RAISE NOTICE 'TASK-809: no qualifying zh/ja generation rows found off '
            'the qwen family — live DB already satisfies ADR-028 Decision §2 '
            'for this scope (see header comment). No-op.';
    END IF;
END $$;

COMMIT;
