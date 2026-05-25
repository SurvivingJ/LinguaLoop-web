---
title: "ADR-014: Dedicated Batch-Service Credential, Scoped to `jwt_required` Only"
status: accepted
date: 2026-05-25
---

# ADR-014: Dedicated Batch-Service Credential, Scoped to `jwt_required` Only

## Context

[middleware/auth.py](../../middleware/auth.py) accepts `SUPABASE_SERVICE_ROLE_KEY` as a bearer token on protected routes and resolves it to a synthetic `service-account` identity. Per commit `7e074fd3` (HI-02, 2026-05-25), this bypass is **symmetric across all three decorators** — `jwt_required`, `admin_required`, and `tier_required`. The original asymmetric version (where only `jwt_required` honoured the bypass) caused batch jobs hitting admin/tier endpoints to silently 401, so HI-02 made it symmetric.

That fix solved the silent-401 bug but enlarged the blast radius of the credential. `SUPABASE_SERVICE_ROLE_KEY` now governs **three independent planes**:

1. **Postgres-direct RLS bypass** via `SupabaseFactory.get_service_client()` and every batch script that calls `create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)` (e.g. `scripts/seed_corpus_packs.py`, `Corpuses/ingest_corpus.py`, `services/corpus/run_corpus_processing.py`, `services/device_service.py:100`, `services/auth_service.py`).
2. **Admin Supabase client for in-process tier lookups** (`middleware/auth.py` `_user_has_tier`).
3. **HTTP identity bypass on every Flask route protected by any of the three auth decorators.**

One leak compromises all three. The open question in [[business-rules/auth-and-access]] (`2026-05-15`) flagged this; HI-02 has now made it more urgent rather than less.

Audit at the time of this ADR: **no batch script in the repository currently exercises plane 3** — every consumer uses the Supabase Python client directly, not the WebApp's HTTP API. The HTTP bypass is therefore a latent capability we want to retain (HTTP batch jobs are planned) but with a separated credential and a narrower scope.

### Design options considered

| Option | Description | Verdict |
|---|---|---|
| A. Status quo | Keep `SUPABASE_SERVICE_ROLE_KEY` as the HTTP bearer credential. | Rejected — couples three planes to one secret. |
| B. Remove the bypass entirely | Delete the bypass branch in `_authenticate`. | Rejected — pre-confirmed in this session that future HTTP batch jobs are planned. |
| C. **Separate shared-secret env var, scoped narrowly** | Add `BATCH_SERVICE_TOKEN`; bypass valid only on `jwt_required`; `admin_required` / `tier_required` no longer honour it. | **Selected.** |
| D. Signed JWT with aud/exp | Mint short-lived JWTs signed by a dedicated key. | Rejected — adds key-management, refresh, and clock handling the codebase doesn't have; out of proportion for the current threat. |
| E. `service_accounts` table with per-job tokens | DB-backed identities with scopes and revocation. | Deferred — heaviest option; revisit when there is more than one HTTP batch caller or a real revocation requirement. |

### Scope-limiting decision

The bypass will be honoured **only by `jwt_required`**. `admin_required` and `tier_required` will reject the batch token and require a real admin user. This deliberately **reverses** the symmetric design from HI-02 for the new credential — the silent-401 problem that HI-02 fixed is no longer relevant once the credential is purpose-built: it will be issued to and used by jobs that only need user-level identity. Anything administrative continues to require a real human admin session.

## Decision

1. Introduce a new env var **`BATCH_SERVICE_TOKEN`** (≥ 32-byte URL-safe random; e.g. `secrets.token_urlsafe(32)`). It is independent of `SUPABASE_SERVICE_ROLE_KEY` and lives only on hosts that run HTTP batch jobs.
2. `middleware/auth.py` `_authenticate` compares the bearer token against `BATCH_SERVICE_TOKEN` via `hmac.compare_digest`. The previous comparison against `SUPABASE_SERVICE_ROLE_KEY` is **removed**.
3. The successful comparison returns the same synthetic claims as today:
   ```python
   {'sub': 'service-account', 'email': 'batch-service@internal',
    'role': 'service_role', 'user': None}
   ```
4. Only `jwt_required` honours this identity. The `if claims['role'] == 'service_role': return f(...)` short-circuits in `admin_required` (`middleware/auth.py:135`) and `tier_required` (`middleware/auth.py:157`) are **deleted**. Service-account requests to admin/tier endpoints fall through to the normal tier check, which finds no `users` row for `sub='service-account'` and returns 403 — the desired outcome.
5. `Config.validate()` does **not** require `BATCH_SERVICE_TOKEN`. If unset, the bypass branch in `_authenticate` skips itself (treat as feature-off). This is a security-positive default: dev / local / CI environments need not carry the token.
6. The bypass continues to log `'Service-role bypass used on %s'` at INFO; rename to `'Batch-service bypass used on %s'` so log filters and SIEM alerts can distinguish HTTP service-identity use from direct Postgres service-role use.
7. **Out of scope for this ADR (and intentionally so):** plane 1 (Postgres-direct RLS bypass) and plane 2 (in-process admin client) continue to use `SUPABASE_SERVICE_ROLE_KEY`. Those planes are not exposed across the network and a separate credential there would just be a rename. The win here is decoupling **plane 3** from the other two.

### Migration sequence

1. Generate `BATCH_SERVICE_TOKEN` and add it to the deployment environment **and** to `.env.example` (placeholder + comment). Do not add it to any `.env` checked into VCS.
2. Land the `middleware/auth.py` change + tests in a single PR. The change is backwards-incompatible: any caller still sending the service-role key over HTTP starts getting 401s.
3. Grep `Corpuses/`, `scripts/`, and any external runbooks once more for HTTP callers; at the time of this ADR there are none in-repo. Communicate the cutover to whoever owns external batch infra if any exists outside this repo.
4. Resolve the open question in [[business-rules/auth-and-access]] frontmatter and update the prose paragraph on line 22.
5. Update [[api/rpcs]] line 69 (currently documents the `SUPABASE_SERVICE_ROLE_KEY` bypass).

### Test plan

- **Unit / route tests in `tests/test_middleware_auth_consolidation.py`:**
  - `BATCH_SERVICE_TOKEN` set + correct token on `jwt_required` route → 200, claims `sub='service-account'`.
  - `BATCH_SERVICE_TOKEN` set + correct token on `admin_required` route → **403** (was 200 before this ADR).
  - `BATCH_SERVICE_TOKEN` set + correct token on `tier_required` route → **403**.
  - Old `SUPABASE_SERVICE_ROLE_KEY` as bearer on any route → 401.
  - `BATCH_SERVICE_TOKEN` unset → all bearer-token paths fall through to Supabase JWT validation.
  - Off-by-one / near-miss token → 401, constant-time comparison preserved.
- **No regression** in the existing HI-01 / HI-02 reproducers; HI-02 is intentionally re-narrowed and that test must be updated to assert the new 403 behaviour with a comment referencing this ADR.

## Consequences

- **Easier:** A leak of `SUPABASE_SERVICE_ROLE_KEY` no longer grants HTTP service-account identity. A leak of `BATCH_SERVICE_TOKEN` no longer grants Postgres RLS bypass or the in-process admin client. The three planes can now be rotated independently.
- **Easier:** `admin_required` / `tier_required` HTTP routes are no longer reachable via any shared secret. Admin work requires a real authenticated admin session, which leaves audit-trail rows in standard auth logs rather than the synthetic `service-account` identity.
- **Easier:** Default-off posture — environments that don't run HTTP batch jobs simply omit `BATCH_SERVICE_TOKEN` and the bypass branch is inert.
- **Harder:** Reverses the HI-02 symmetric design. If a future batch job needs to hit an admin or tier endpoint, it must either (a) authenticate as a real admin user, or (b) call a Postgres RPC directly via the service-role client and skip Flask. Both are acceptable; the ADR makes this explicit so a future engineer doesn't re-symmetrise the bypass without thinking.
- **Constrained:** Per-job scoping, revocation, and rotation telemetry are deferred. The day there's a second HTTP batch caller or a real revocation requirement, revisit Option E (DB-backed `service_accounts`).

## Alternatives Considered

1. **Remove the HTTP bypass entirely (Option B).** Cleanest from a security perspective; rejected because the user confirmed HTTP batch jobs are on the roadmap. Re-introducing a credential after removing one is more disruptive than keeping a scoped one.
2. **Signed JWT (Option D).** Strongest cryptographic story (audience binding, expiry, no shared secret). Rejected as disproportionate — there is exactly one (future) consumer; symmetric shared-secret + `hmac.compare_digest` matches both the threat model and the codebase's existing secret-handling patterns ([[overview/project.tech]]).
3. **DB-backed `service_accounts` (Option E).** Best long-term answer if there are multiple HTTP batch identities with different scopes. Premature today; ADR-014 keeps the door open by isolating the change to `_authenticate` + one env var.
4. **Keep symmetric scoping (`admin_required` / `tier_required` still honoured).** Rejected because the whole purpose of separating the credential is to shrink the blast radius. A separate token that still passes admin/tier checks reduces the rotation problem but not the impact-of-leak problem.

## Related Pages

- [[business-rules/auth-and-access]] — Open question this ADR resolves (line 8 frontmatter, line 22 prose).
- [[api/rpcs]] — Documents the bearer-token bypass; needs update to reference `BATCH_SERVICE_TOKEN` not `SUPABASE_SERVICE_ROLE_KEY`.
- [[overview/project.tech]] — Env var inventory.
- [[reviews/code-review-2026-05-24]] — Original review that surfaced HI-01 / HI-02; HI-02's symmetric design is the prompt for ADR-014.
