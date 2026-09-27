-- ============================================================================
-- Archive unused modules and drop their tables (2026-09-21)
-- ============================================================================
--
-- Every table/row removed here was first exported (rows as JSONL + CSV, DDL as
-- schema.sql, row counts verified against an exact count) into:
--   archive/db_backups/stage1-unused-tables-2026-09-21.zip
--   archive/modules/{language-packs,listening-lab,grammar-patterns,
--                    conversations,mysteries}-2026-09-21.zip
--   archive/db_backups/llm-calls-log-2026-09-21.zip
-- Each zip also carries the module's code, docs and a RESTORE.md.
--
-- NOT archived (still live): the corpus tables (corpus_sources,
-- corpus_collocations, corpus_style_profiles) — the vocabulary ladder's
-- collocation grounding (services/vocabulary_ladder/collocation_grounding.py)
-- reads corpus_collocations. user_exercise_sessions is also kept (daily
-- practice-session cache). The 10 source_type='collocation' exercises stay with
-- the corpus pipeline that produced them.
--
-- Kept columns: user_study_plans.goal_id (read by routes/study_plan.py) and
-- tests/users.organization_id (tests_public_read policy reads it). Only their
-- FK constraints to the dropped tables are removed.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Guards: fail the whole migration if state moved since the export.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF (SELECT count(*) FROM exercises WHERE source_type = 'conversation') <> 7352 THEN
    RAISE EXCEPTION 'conversation exercise count changed since export';
  END IF;
  IF EXISTS (SELECT 1 FROM exercise_attempts a JOIN exercises e ON e.id = a.exercise_id
              WHERE e.source_type = 'conversation')
     OR EXISTS (SELECT 1 FROM user_exercise_history h JOIN exercises e ON e.id = h.exercise_id
              WHERE e.source_type = 'conversation') THEN
    RAISE EXCEPTION 'conversation exercises have attempts/history — not dead';
  END IF;
  IF EXISTS (SELECT 1 FROM exercises WHERE grammar_pattern_id IS NOT NULL OR style_pack_item_id IS NOT NULL) THEN
    RAISE EXCEPTION 'exercises reference grammar patterns / style pack items';
  END IF;
  IF (SELECT count(*) FROM conversations) <> 261 OR (SELECT count(*) FROM persona_pairs) <> 22951
     OR (SELECT count(*) FROM mysteries) <> 1 OR (SELECT count(*) FROM question_type_distributions) <> 9 THEN
    RAISE EXCEPTION 'archived table row counts changed since export';
  END IF;
  IF EXISTS (SELECT 1 FROM user_study_plans WHERE goal_id IS NOT NULL)
     OR EXISTS (SELECT 1 FROM tests WHERE organization_id IS NOT NULL)
     OR EXISTS (SELECT 1 FROM users WHERE organization_id IS NOT NULL) THEN
    RAISE EXCEPTION 'goal_id / organization_id now populated';
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. Stage 1 — unused tables
-- ---------------------------------------------------------------------------
ALTER TABLE public.user_study_plans DROP CONSTRAINT IF EXISTS user_study_plans_goal_id_fkey;
ALTER TABLE public.tests            DROP CONSTRAINT IF EXISTS tests_organization_id_fkey;
ALTER TABLE public.users            DROP CONSTRAINT IF EXISTS users_organization_id_fkey;
DROP FUNCTION IF EXISTS public.is_org_member(uuid, uuid);
DROP FUNCTION IF EXISTS public.get_org_role(uuid, uuid);
DROP TABLE public.organization_members;
DROP TABLE public.organizations;
DROP TABLE public.flagged_content;
DROP TABLE public.question_type_distributions;
DROP TABLE public.vocabulary_review_queue;
DROP TABLE public.dim_classifier_example_sentences;
DROP TABLE public.dim_study_goals;

-- ---------------------------------------------------------------------------
-- exercises.chk_source_fk names three of the columns dropped below. DROP COLUMN
-- would silently remove the whole CHECK, so drop it explicitly here and
-- rebuild it on the surviving source columns after section 5.
-- ---------------------------------------------------------------------------
ALTER TABLE public.exercises DROP CONSTRAINT chk_source_fk;

-- ---------------------------------------------------------------------------
-- 2. Language packs
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_packs_with_user_selection(integer, uuid);
ALTER TABLE public.exercises DROP COLUMN style_pack_item_id;          -- FK + idx_exercises_style_item go with it
DROP TABLE public.pack_collocations;
DROP TABLE public.pack_key_words;
DROP TABLE public.pack_style_items;
DROP TABLE public.user_pack_selections;
DROP TABLE public.style_pack_items;
DROP TABLE public.collocation_packs;

-- ---------------------------------------------------------------------------
-- 3. Listening lab (dim_test_types row 'listening_lab' is kept: ratings rows
--    may reference it and the study planner's UNPLANNED_TEST_TYPES names it)
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.start_listening_lab_session(uuid, uuid);
DROP FUNCTION IF EXISTS public.submit_listening_lab_tier(uuid, uuid, smallint, jsonb, uuid);
DROP FUNCTION IF EXISTS public.get_listening_lab_recommendations(uuid, integer);
DROP TABLE public.listening_lab_sessions;
DROP TABLE public.listening_lab_passages;

-- ---------------------------------------------------------------------------
-- 4. Grammar patterns
-- ---------------------------------------------------------------------------
ALTER TABLE public.exercises DROP COLUMN grammar_pattern_id;          -- FK + idx_exercises_grammar go with it
DROP TABLE public.dim_grammar_patterns;

-- ---------------------------------------------------------------------------
-- 5. Conversations (incl. the 7,352 unservable conversation-sourced exercises
--    and the conversation-generation prompt templates)
-- ---------------------------------------------------------------------------
DELETE FROM public.exercises WHERE source_type = 'conversation';
ALTER TABLE public.exercises DROP COLUMN conversation_id;             -- FK + idx_exercises_conversation go with it
DROP TABLE public.conversation_generation_queue;
DROP TABLE public.conversations;
DROP TABLE public.scenarios;
DROP TABLE public.persona_pairs;
DROP TABLE public.personas;
DROP TABLE public.conversation_domains;
DELETE FROM public.prompt_templates
 WHERE task_name IN ('conversation_analysis', 'conversation_generation', 'conversation_persona_design',
                     'conversation_scenario_plan', 'scenario_batch_generation');

-- Rebuild the "every exercise has a source" guarantee on what remains
-- (verified 2026-09-21: 0 of the 6,224 surviving rows violate it).
ALTER TABLE public.exercises ADD CONSTRAINT chk_source_fk
  CHECK (((word_sense_id IS NOT NULL)::integer + (corpus_collocation_id IS NOT NULL)::integer) >= 1);

-- ---------------------------------------------------------------------------
-- 6. Mysteries (dim_test_types row 'mystery' kept, as for listening_lab)
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.process_mystery_submission(uuid, uuid, smallint, smallint, jsonb, uuid);
DROP FUNCTION IF EXISTS public.get_recommended_mysteries(uuid, integer);
DROP TABLE public.mystery_attempts;
DROP TABLE public.mystery_progress;
DROP TABLE public.mystery_skill_ratings;
DROP TABLE public.mystery_questions;
DROP TABLE public.mystery_scenes;
DROP TABLE public.mysteries;
DELETE FROM public.prompt_templates
 WHERE task_name IN ('mystery_clue', 'mystery_deduction', 'mystery_plot', 'mystery_question', 'mystery_scene');

-- ---------------------------------------------------------------------------
-- 7. llm_calls log moved to archive/db_backups/llm-calls-log-2026-09-21.zip.
--    Export's newest row: 2026-09-21 21:24:04.168011+00. Rows from the 10
--    minutes before that (and anything written since) are put back, so a row
--    committed during the export window cannot be lost; the overlap is
--    duplicated in the archive, which is harmless. TRUNCATE (not DELETE)
--    so the space is returned immediately.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _llm_keep ON COMMIT DROP AS
  SELECT * FROM public.llm_calls WHERE created_at > timestamptz '2026-09-21 21:14:04.168011+00';
TRUNCATE public.llm_calls;
INSERT INTO public.llm_calls SELECT * FROM _llm_keep;

-- ---------------------------------------------------------------------------
-- 8. Remove the temporary export helper created for this archive.
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.tmp_archive_ddl(text[], text[]);

COMMIT;
