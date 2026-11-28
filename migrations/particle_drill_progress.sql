-- Particle drill: the learner's ladder state, one JSON row per user and drill.
--
-- NOT APPLIED. The drill works without it (state stays in the browser's
-- localStorage); applying it adds the cross-device copy written by
-- PUT /api/particle-drill/progress (services/particle_drill/progress.py).
--
-- Size: one row per learner, a few KB each (the route rejects a state over
-- 256 KB). No content table: the exercises ship as files (ADR-067).
--
-- VERIFY BEFORE:  SELECT to_regclass('public.user_drill_progress');   -- NULL
-- VERIFY AFTER:   SELECT relrowsecurity FROM pg_class WHERE oid = 'public.user_drill_progress'::regclass;  -- t
--                 SELECT count(*) FROM pg_policies WHERE tablename = 'user_drill_progress';                -- 0
--                 SELECT has_table_privilege('anon', 'public.user_drill_progress', 'SELECT'),
--                        has_table_privilege('authenticated', 'public.user_drill_progress', 'SELECT');     -- f, f
-- ROLLBACK:       DROP TABLE IF EXISTS public.user_drill_progress;

BEGIN;

CREATE TABLE IF NOT EXISTS public.user_drill_progress (
    user_id    uuid        NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    drill      text        NOT NULL CHECK (drill ~ '^[a-z0-9_]{1,40}$'),
    state      jsonb       NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, drill),
    CONSTRAINT user_drill_progress_state_size CHECK (pg_column_size(state) <= 300000)
);

-- Flask reads and writes with the service role. RLS on and no policy: no
-- client role can see or change a row through PostgREST.
ALTER TABLE public.user_drill_progress ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.user_drill_progress FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_drill_progress TO service_role;

COMMENT ON TABLE public.user_drill_progress IS
    'Client-side drill state (particle drill ladder), one JSON document per user and drill.';

COMMIT;
