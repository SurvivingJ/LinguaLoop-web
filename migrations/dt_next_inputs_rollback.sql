-- Rollback for migrations/dt_next_inputs.sql. Not applied; kept for an operator
-- who needs to undo it.
--
-- dt_next_inputs.sql creates one NEW function and changes nothing else (verified
-- 2026-11-17 before writing it: `select proname from pg_proc join pg_namespace n
-- on n.oid = pronamespace where n.nspname = 'public' and proname like 'dt%'`
-- returned no rows, so there is no previous definition to restore).
--
-- After the drop, GET /api/dual-translation/next keeps working: the route
-- detects the missing function (PGRST202 / 42883), logs it once and uses the
-- per-table reads (routes/dual_translation.py `_next_inputs`).

DROP FUNCTION IF EXISTS public.dt_next_inputs(uuid, integer, integer);
