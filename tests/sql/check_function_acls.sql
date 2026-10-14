-- =============================================================================
-- check_function_acls.sql  (TASK-881)  READ-ONLY catalog check. SELECT only.
-- =============================================================================
-- Run against live/staging:   psql "$DATABASE_URL" -f tests/sql/check_function_acls.sql
-- Every result set should be EMPTY (0 rows). Any row is a violation. It reads only
-- pg_catalog; it never calls a function and never reads user data.
--
-- Allowlist (functions that legitimately stay executable by anon/authenticated): edit the
-- VALUES list in check 1 and 2. Adding an entry needs an ADR (see migrations/CLAUDE.md).
-- Currently: is_admin, is_moderator (used inside RLS policies).
-- =============================================================================

-- 1. SECURITY DEFINER functions in public executable by anon/authenticated (outside allowlist)
SELECT 'definer_executable_by_client' AS check_name,
       p.oid::regprocedure::text      AS object,
       r.rolname                      AS role
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname = 'public'
CROSS JOIN (SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')) r
WHERE p.prosecdef
  AND p.prokind IN ('f', 'p')
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e')
  AND p.proname NOT IN (SELECT a FROM (VALUES ('is_admin'), ('is_moderator')) v(a))
  AND has_function_privilege(r.rolname, p.oid, 'EXECUTE')
ORDER BY 2, 3;

-- 2. SECURITY DEFINER functions in public without a pinned search_path
SELECT 'definer_without_search_path' AS check_name,
       p.oid::regprocedure::text     AS object
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname = 'public'
WHERE p.prosecdef
  AND p.prokind IN ('f', 'p')
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e')
  AND NOT EXISTS (SELECT 1 FROM unnest(coalesce(p.proconfig, '{}')) c WHERE c LIKE 'search_path=%')
ORDER BY 2;

-- 3. Public tables with row level security OFF
SELECT 'table_rls_off' AS check_name,
       c.oid::regclass::text AS object
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
WHERE c.relkind IN ('r', 'p')
  AND NOT c.relrowsecurity
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype = 'e')
ORDER BY 2;

-- 4. Client write privileges on the account / ledger tables (TASK-875)
SELECT 'client_write_on_account_table' AS check_name,
       c.oid::regclass::text           AS object,
       r.rolname || ':' || pr.priv     AS role_privilege
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
CROSS JOIN (SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')) r
CROSS JOIN (VALUES ('INSERT'), ('UPDATE'), ('DELETE'), ('TRUNCATE'), ('REFERENCES'), ('TRIGGER')) pr(priv)
WHERE c.relname IN ('users', 'user_tokens', 'token_transactions')
  AND c.relkind IN ('r', 'p')
  AND has_table_privilege(r.rolname, c.oid, pr.priv)
ORDER BY 2, 3;

-- 5. anon holding any privilege on a public table (anon should have none)
SELECT 'anon_table_privilege' AS check_name,
       c.oid::regclass::text  AS object,
       pr.priv                AS privilege
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
CROSS JOIN (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'), ('TRUNCATE'),
                   ('REFERENCES'), ('TRIGGER')) pr(priv)
WHERE c.relkind IN ('r', 'p')
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype = 'e')
  AND has_table_privilege('anon', c.oid, pr.priv)
ORDER BY 2, 3;
