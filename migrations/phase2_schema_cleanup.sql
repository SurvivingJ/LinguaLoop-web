-- ============================================================================
-- Phase 2: Schema Cleanup — Fix Types, FKs, Constraints
-- Date: 2026-04-12
--
-- 2.1 Fix user_pack_selections.user_id text -> uuid
-- 2.2 Fix get_packs_with_user_selection RPC parameter type
-- 2.3 Fix user_reports FK: auth.users -> public.users
-- 2.4 Add FK to app_error_logs.user_id
-- 2.5 Rename legacy PK: dim_cefr_levels_pkey -> dim_complexity_tiers_pkey
-- 2.6 Fix user_exercise_sessions.language_id type + add FK
-- ============================================================================


-- ============================================================================
-- 2.1 Fix user_pack_selections.user_id: text -> uuid with proper FK
-- ============================================================================
-- Current table has user_id as text with no FK constraint. Recreate with
-- uuid type, FK to users, composite PK, and RLS.

-- Step 1: Create replacement table
CREATE TABLE IF NOT EXISTS public.user_pack_selections_new (
    user_id     uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    pack_id     bigint NOT NULL REFERENCES public.collocation_packs(id) ON DELETE CASCADE,
    created_at  timestamptz DEFAULT now(),
    PRIMARY KEY (user_id, pack_id)
);

-- Step 2: Migrate valid data (only rows where user_id is a valid UUID)
INSERT INTO public.user_pack_selections_new (user_id, pack_id, created_at)
SELECT user_id::uuid, pack_id, created_at
FROM public.user_pack_selections
WHERE user_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
ON CONFLICT DO NOTHING;

-- Step 3: Swap tables
DROP TABLE IF EXISTS public.user_pack_selections;
ALTER TABLE public.user_pack_selections_new RENAME TO user_pack_selections;

-- Step 4: Enable RLS
ALTER TABLE public.user_pack_selections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own pack selections"
    ON public.user_pack_selections
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role full access on pack selections"
    ON public.user_pack_selections
    FOR ALL
    USING (auth.role() = 'service_role');


-- ============================================================================
-- 2.2 Fix get_packs_with_user_selection RPC: p_user_id text -> uuid
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_packs_with_user_selection(
    p_language_id integer,
    p_user_id uuid
)
RETURNS TABLE(
    id bigint,
    pack_name text,
    description text,
    pack_type text,
    tags text[],
    total_items integer,
    difficulty_range text,
    is_selected boolean
)
LANGUAGE sql
STABLE
AS $function$
    SELECT
        cp.id,
        cp.pack_name,
        cp.description,
        cp.pack_type,
        cp.tags,
        cp.total_items,
        cp.difficulty_range,
        (ups.user_id IS NOT NULL) AS is_selected
    FROM collocation_packs cp
    LEFT JOIN user_pack_selections ups
        ON ups.pack_id = cp.id
       AND ups.user_id = p_user_id
    WHERE cp.language_id = p_language_id
      AND cp.is_public = TRUE
    ORDER BY cp.pack_name;
$function$;

-- Drop old signature with text parameter
DROP FUNCTION IF EXISTS public.get_packs_with_user_selection(integer, text);


-- ============================================================================
-- 2.3 Fix user_reports FK: auth.users.id -> public.users.id
-- ============================================================================
-- Aligns with the public mirror pattern used everywhere else.

ALTER TABLE public.user_reports
    DROP CONSTRAINT IF EXISTS user_reports_user_id_fkey;

ALTER TABLE public.user_reports
    ADD CONSTRAINT user_reports_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.users(id);


-- ============================================================================
-- 2.4 Add FK to app_error_logs.user_id
-- ============================================================================
-- Clean orphaned rows first, then add FK with ON DELETE SET NULL
-- so user deletion preserves error log history.

DELETE FROM public.app_error_logs
WHERE user_id IS NOT NULL
  AND user_id NOT IN (SELECT id FROM public.users);

ALTER TABLE public.app_error_logs
    ADD CONSTRAINT app_error_logs_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.users(id)
    ON DELETE SET NULL;


-- ============================================================================
-- 2.5 Rename legacy PK/sequence from dim_cefr_levels -> dim_complexity_tiers
-- ============================================================================
-- Table was renamed but PK constraint and sequence retain the old name.

ALTER INDEX IF EXISTS dim_cefr_levels_pkey RENAME TO dim_complexity_tiers_pkey;
ALTER SEQUENCE IF EXISTS dim_cefr_levels_id_seq RENAME TO dim_complexity_tiers_id_seq;


-- ============================================================================
-- 2.6 Fix user_exercise_sessions.language_id: integer -> smallint + add FK
-- ============================================================================
-- dim_languages.id is smallint; this table uses integer with no FK.

ALTER TABLE public.user_exercise_sessions
    ALTER COLUMN language_id TYPE smallint;

ALTER TABLE public.user_exercise_sessions
    ADD CONSTRAINT user_exercise_sessions_language_id_fkey
    FOREIGN KEY (language_id) REFERENCES public.dim_languages(id);
