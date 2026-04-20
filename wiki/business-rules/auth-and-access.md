---
title: Authentication & Access Control
type: business-rule
status: in-progress
last_updated: 2026-04-10
open_questions:
  - "Global admin role — currently determined by subscription tier is_admin flag. Should there be a separate admin table?"
---

# Authentication & Access Control

## User Authentication

- Authentication via Supabase Auth (email/password).
- JWTs issued by Supabase, validated by Flask middleware (`middleware/auth.py`).
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
