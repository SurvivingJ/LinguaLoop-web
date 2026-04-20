-- ============================================================================
-- Phase 1: Quick Wins — Zero Risk, Independent Migrations
-- Date: 2026-04-12
--
-- 1.1 Remove duplicate trigger on test_attempts
-- 1.2 Drop dead RPC: process_test_submission-old
-- 1.3 Drop broken RPC: migrate_test_json
-- 1.4 Drop empty users_backup table
-- 1.5 Fix get_prompt_template (references non-existent language_code column)
-- ============================================================================


-- ============================================================================
-- 1.1 Remove duplicate trigger on test_attempts
-- ============================================================================
-- Currently three COUNT(*) scans fire on every test_attempts INSERT:
--   - trigger_update_skill_attempts (runs update_skill_attempts_count)
--   - update_skill_attempts_count_trigger (DUPLICATE — runs same function)
--   - trigger_update_test_attempts (runs update_test_attempts_count)
-- Dropping the duplicate halves the trigger overhead.

DROP TRIGGER IF EXISTS update_skill_attempts_count_trigger ON public.test_attempts;


-- ============================================================================
-- 1.2 Drop dead RPC: process_test_submission-old
-- ============================================================================
-- Exact duplicate of process_test_submission. Never called by app code.
-- Hyphenated name requires quoting.

DROP FUNCTION IF EXISTS public."process_test_submission-old"(
    uuid, uuid, smallint, smallint, jsonb, boolean, uuid
);


-- ============================================================================
-- 1.3 Drop broken RPC: migrate_test_json
-- ============================================================================
-- References non-existent tables (test_questions, test_catalog).
-- Cannot execute and has been broken since schema V2.

DROP FUNCTION IF EXISTS public.migrate_test_json(jsonb);


-- ============================================================================
-- 1.4 Drop empty users_backup table
-- ============================================================================
-- Empty table with no PK, outdated column set (has native_language,
-- target_languages, timezone which the live users table lacks).

DROP TABLE IF EXISTS public.users_backup;


-- ============================================================================
-- 1.5 Fix get_prompt_template
-- ============================================================================
-- Current version references language_code column which does not exist on
-- prompt_templates (the table has language_id integer). Rewrite to use
-- language_id with fallback to language_id=2 (English default).

CREATE OR REPLACE FUNCTION public.get_prompt_template(
    p_task_name character varying,
    p_language_id integer DEFAULT 2
)
RETURNS text
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    result_text TEXT;
BEGIN
    -- Try language-specific first
    SELECT template_text INTO result_text
    FROM prompt_templates
    WHERE task_name = p_task_name
      AND language_id = p_language_id
      AND is_active = true
    ORDER BY version DESC
    LIMIT 1;

    -- Fall back to English (language_id=2) if not found
    IF result_text IS NULL AND p_language_id != 2 THEN
        SELECT template_text INTO result_text
        FROM prompt_templates
        WHERE task_name = p_task_name
          AND language_id = 2
          AND is_active = true
        ORDER BY version DESC
        LIMIT 1;
    END IF;

    RETURN result_text;
END;
$function$;

-- Drop the old signature with language_code text parameter to avoid ambiguity
DROP FUNCTION IF EXISTS public.get_prompt_template(character varying, character varying);
