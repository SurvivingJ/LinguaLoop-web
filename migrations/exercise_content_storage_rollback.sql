-- =============================================================================
-- exercise_content_storage_rollback.sql — undo migrations/exercise_content_storage.sql
-- Date: 2026-11-17   Task: TASK-1016   Spec: wiki/decisions/ADR-049-exercise-content-in-storage.md
--
-- STATUS: NOT applied. Run only to undo exercise_content_storage.sql.
--
-- Valid ONLY before EXERCISE_CONTENT_WRITE=dual was ever set in any environment. Once a dual
-- write has committed, rows carry content versions whose files exist only in Storage, and
-- dropping content_version loses the link between a row and its file. The guard below refuses
-- when any row has content_version <> 0.
--
-- Order: roll back migrations/exercise_content_session_rpcs.sql FIRST
-- (exercise_content_session_rpcs_rollback.sql); its get_practice_session /
-- get_review_ahead_items read exercises.content_version. The guard below refuses while the
-- 6-argument session functions exist.
--
-- Drops the three write-side functions, the version sequence and both columns
-- (content_version, dedupe_key: catalog-only drops). It never deletes bucket objects: the
-- bucket row exercise-content and any files in it are left in place (delete them from the
-- Storage dashboard if wanted; Storage refuses to drop a non-empty bucket).
-- Renumbered 2026-11-17 when merged with main: ADR-047 -> ADR-049 and TASK-976..999 ->
-- TASK-1008..1031 (main already used those ids). Function bodies and COMMENT strings keep
-- the old ids: they are (or will be) the live text, md5-compared against the database.
-- =============================================================================

BEGIN;

DO $guard$
BEGIN
    IF to_regprocedure('public.get_practice_session(uuid, smallint, text, smallint, numeric, boolean)') IS NOT NULL
       OR to_regprocedure('public.get_review_ahead_items(uuid, smallint, integer, integer, integer[], boolean)') IS NOT NULL THEN
        RAISE EXCEPTION 'exercise_content_storage rollback: run exercise_content_session_rpcs_rollback.sql first';
    END IF;
    -- Nested IF: the inner query is planned only when the column exists.
    IF EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'exercises'
                  AND column_name = 'content_version') THEN
        IF EXISTS (SELECT 1 FROM public.exercises WHERE content_version <> 0) THEN
            RAISE EXCEPTION 'exercise_content_storage rollback: rows with content_version <> 0 exist '
                            '(dual writes happened); this rollback is no longer valid';
        END IF;
    END IF;
END
$guard$;

DROP FUNCTION IF EXISTS public.exercise_content_commit(integer, integer, uuid[], integer, uuid[], jsonb, jsonb);
DROP FUNCTION IF EXISTS public.exercise_content_begin(integer);
DROP FUNCTION IF EXISTS public.exercise_content_live_versions(integer);

DROP SEQUENCE IF EXISTS public.exercise_content_version_seq;

ALTER TABLE public.exercises
    DROP COLUMN IF EXISTS dedupe_key,
    DROP COLUMN IF EXISTS content_version;

-- The bucket row and its objects are deliberately kept (see header).

NOTIFY pgrst, 'reload schema';

COMMIT;
