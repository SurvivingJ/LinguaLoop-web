---
title: Authentication & Access Control
type: business-rule
status: in-progress
last_updated: 2026-05-15
open_questions:
  - "Global admin role — currently determined by subscription tier is_admin flag. Should there be a separate admin table?"
  - "Service-role bypass in middleware/auth.py uses the same SUPABASE_SERVICE_ROLE_KEY the backend itself uses. A leak grants full DB access. Replace with a dedicated batch-service credential."
---

# Authentication & Access Control

## Startup invariants (2026-05-15)

- `Config.validate()` at app boot raises `RuntimeError` if any of `SECRET_KEY`, `JWT_SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY` is unset. The previous placeholder defaults (`'temp-secret-change-in-production'`, `'jwt-secret-change-in-production'`) were removed so a misconfigured `.env` can no longer boot the app in an insecure state.
- `SupabaseFactory.initialize()` runs once in `create_app()` and is the only construction site for Supabase clients. `AuthService` now pulls the admin client from this factory instead of calling `create_client(...)` itself.

## User Authentication

- Authentication via Supabase Auth (email/password).
- JWTs issued by Supabase, validated by Flask middleware ([`middleware/auth.py`](../../middleware/auth.py)). Only standalone decorators (`jwt_required`, `admin_required`, `tier_required`) — the class-based `AuthMiddleware` was removed 2026-05-15 (had no callers).
- The `jwt_required` decorator also accepts the raw `SUPABASE_SERVICE_ROLE_KEY` as a bearer token, used for internal batch jobs. The comparison uses `hmac.compare_digest` (constant-time, 2026-05-15) and every bypass call logs `'Service-role bypass used on %s'`. **Open question above** flags the deeper risk.
- New users automatically get a `users` row + `user_tokens` row via `handle_new_user()` trigger.
- Soft-delete via `deleted_at` / `anonymized_at` timestamps (GDPR compliance via `anonymize_user_data()`).

## Roles

### Individual Roles (via `dim_subscription_tiers`)

| Tier | Daily Free Tests | Can Generate | Is Admin | Is Moderator |
|------|-----------------|-------------|----------|-------------|
| Free | 2 | No | No | No |
| Premium | (TBD) | (TBD) | No | No |
| Enterprise | (TBD) | (TBD) | No | No |
| Admin | Unlimited | Yes | Yes | Yes |

### Organization Roles (via `organization_members`)

| Role | Permissions |
|------|------------|
| Student | Access org content |
| Teacher | Manage students |
| Admin | Manage org settings |
| Owner | Full org control |

## Access Control Functions

- `is_admin(user_id)` — checks subscription tier `is_admin` flag
- `is_moderator(user_id)` — checks `is_moderator OR is_admin`
- `is_org_member(user_id, org_id)` — org membership check
- `get_org_role(user_id, org_id)` — returns org role

## Invariants

- A user cannot submit a test for another user (enforced in `process_test_submission`).
- Token balance operations check `auth.uid()` matches target user (admin exempt).
- RLS policies on Supabase enforce row-level access.
- Content creation is system-only; no user-facing content authoring.

## Related Pages

- [[features/token-economy]] — Token access rules
- [[database/schema.tech]] — Auth functions
