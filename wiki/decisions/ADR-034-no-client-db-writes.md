---
title: "ADR-034: No direct client database writes"
status: accepted
date: 2026-10-14
---

# ADR-034: No direct client database writes

## Context
The 2026-10-14 security audit ([[features/security-hardening.tech]]) found that the `anon` and `authenticated` Postgres roles
(reachable from any browser with the public anon key through PostgREST) could update their own `users.subscription_tier_id`
and `user_tokens.purchased_tokens`, write 32 tables that had RLS off, and EXECUTE SECURITY DEFINER functions such as
`process_stripe_payment` and the progress and calibration write RPCs. The app has no legitimate direct browser-to-database
write path: every write already goes through Flask, which uses the service role.

## Decision
1. Browser and user-JWT roles (`anon`, `authenticated`) get no direct table writes (INSERT, UPDATE, DELETE, TRUNCATE,
   REFERENCES, TRIGGER) and no EXECUTE on privileged or user-id-taking functions. All writes go through Flask with the service role.
2. Row-level security is enabled on every table in the public schema. Browser roles keep at most own-row SELECT where a
   browser read is legitimate.
3. Revokes are always applied to `PUBLIC`, `anon` and `authenticated` together. Default privileges for new objects in `public`
   are revoked for the same roles.
4. Admin operations also run through Flask with the service role; there is no admin-JWT write policy (`users_admin_all` is dropped).
5. `users` has a full revoke of client writes, with no column allowlist.
6. Functions that must stay EXECUTE-able by `authenticated` (currently `is_admin`, `is_moderator`) are listed on an allowlist
   file and, if they accept a user id, check `auth.uid()` in the body. `service_role`-only functions need no such check.
7. Any exception needs an allowlist entry in `tests/sql/function_acl_allowlist.txt` plus an ADR.

## Consequences
Easier: the attack surface of the public API shrinks to own-row reads; reasoning about security reduces to the Flask routes;
new objects are closed by default. Harder: any future feature that wants a browser-direct write (for example a realtime or
offline client) needs an ADR and an allowlist entry; every new function and table migration must carry its REVOKE and
RLS statements (enforced by TASK-881). Constrained: all services must use the service key, and Flask routes become the sole
place where authorisation and input validation can live (hence TASK-882).

## Alternatives Considered
- Column-level UPDATE allowlist on `users`: rejected (developer decision 2026-10-14); there is no browser caller, so a full revoke is simpler and safer.
- In-function `auth.uid()` checks on every function while leaving EXECUTE open: rejected as the primary defence; it relies on every body being correct, and the audit found many that trust a caller-supplied user id. Used only for functions that must stay client-callable.
- Keeping `users_admin_all` for admin JWTs: rejected; it is a privileged write path reachable by anyone who can obtain the admin tier.
- Per-table RLS policies as the only control: rejected; the schema default grants everything to `anon`, so protection would rest on RLS alone.

## Residual (recorded 2026-10-14)
Vocab-dojo gate and stress-test results use a signed battery token that closes forging a bare `passed` flag, but per-item `is_correct` stays client-reported and the token is replayable for 1 hour. Not closed: needs server-side grading per exercise type (and optionally single-use tokens).
