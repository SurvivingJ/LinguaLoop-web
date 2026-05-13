-- migrations/trusted_devices.sql
-- Backs the "Remember this device for 6 months" feature on the login page.
-- One row per (device, generation) — the device is a chain of rows that share
-- a stable device_id and differ in token_hash. Rotation inserts a new row and
-- marks the previous row revoked with reason 'rotated'. Reuse of a 'rotated'
-- token at any point in the chain is evidence of theft: the application
-- revokes every active row for that user (reuse detection — OAuth 2.0 BCP).
--
-- Storage model:
--   * token_hash holds sha256(opaque random token); the raw token is never
--     persisted — it lives only in an HttpOnly cookie on the device.
--   * device_id is stable across rotations so the future settings UI can show
--     "Chrome on Windows — last used 2 days ago" as a single entry.
--   * generation is a human-readable counter that grows monotonically inside
--     a chain (not a security mechanism on its own).
--   * expires_at on a fresh row is now() + 180 days; the chain slides forward
--     on every successful rotation.
--
-- All access is server-side via the service-role Supabase client. RLS is
-- enabled with a service-role policy + admin SELECT for audit. No own-data
-- policy is needed: the user's JS never reads this table.
--
-- Idempotent: safe to re-apply.

-- ===========================================================================
-- 1. Table
-- ===========================================================================
CREATE TABLE IF NOT EXISTS public.trusted_devices (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id       uuid NOT NULL,
    user_id         uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash      bytea NOT NULL,
    generation      int  NOT NULL DEFAULT 1,
    device_label    text,
    user_agent      text,
    ip_hash         bytea,
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_used_at    timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    revoked_at      timestamptz,
    revoked_reason  text
);

-- ===========================================================================
-- 2. Indexes
-- ===========================================================================
-- Hot path: every /api/auth/device-restore call hashes the incoming cookie
-- and looks up by hash. We need to find both active rows (rotate them) AND
-- revoked-with-reason='rotated' rows (reuse detection), so the index is
-- full-table. With 48 bytes of entropy in each token, hash collisions are
-- essentially impossible, so we can make it UNIQUE.
CREATE UNIQUE INDEX IF NOT EXISTS trusted_devices_token_hash_idx
    ON public.trusted_devices (token_hash);

-- Used by the future settings UI (list a user's active devices) and by
-- revoke_all_for_user during reuse-detection cleanup.
CREATE INDEX IF NOT EXISTS trusted_devices_user_active_idx
    ON public.trusted_devices (user_id)
    WHERE revoked_at IS NULL;

-- Used by the settings UI to collapse a chain into a single entry.
CREATE INDEX IF NOT EXISTS trusted_devices_device_id_idx
    ON public.trusted_devices (device_id);

-- ===========================================================================
-- 3. RLS
-- ===========================================================================
ALTER TABLE public.trusted_devices ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS td_service_role ON public.trusted_devices;
CREATE POLICY td_service_role ON public.trusted_devices
  FOR ALL
  USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS td_admin_view ON public.trusted_devices;
CREATE POLICY td_admin_view ON public.trusted_devices
  FOR SELECT
  USING (is_admin(auth.uid()));

-- ===========================================================================
-- Verification queries (run after apply)
-- ===========================================================================
-- 1) Table + columns:
--    \d public.trusted_devices
--
-- 2) RLS enabled:
--    SELECT relname, relrowsecurity FROM pg_class
--    WHERE relname = 'trusted_devices';
--    Expected: relrowsecurity = t
--
-- 3) Policy set:
--    SELECT policyname FROM pg_policies
--    WHERE schemaname = 'public' AND tablename = 'trusted_devices'
--    ORDER BY policyname;
--    Expected: td_admin_view, td_service_role
