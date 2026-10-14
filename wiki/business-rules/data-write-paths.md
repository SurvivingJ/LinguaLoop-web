---
title: Data Write Paths
type: business-rule
status: in-progress
tech_page: ../features/security-hardening.tech.md
last_updated: 2026-10-14
open_questions:
  - "Should attempt_responses be added to the TASK-880 client-write revoke list?"
---

# Data Write Paths

## Purpose
States who may write which data in LinguaLoop after the security hardening (ADR-034): the browser never writes the database or calls an RPC directly.

## How It Works
- All writes and all RPC calls go through Flask using the service-role client. The browser talks only to Flask.
- Client roles (anon, authenticated) hold no write privileges on any public table. Own-row reads are kept where a table has an own-row SELECT policy.
- Admin operations also go through Flask with the service role; there is no admin-JWT write policy on users.
- The only functions callable by client roles are is_admin and is_moderator, used by RLS policies, and they answer only for the caller's own id.
- Future tables and functions get no automatic client grants; migrations must grant explicitly (see migrations/CLAUDE.md).

## Constraints & Edge Cases
- A missing service-role key makes the affected routes return 500; there is no anon fallback.
- Gate and stress-test results are scored server-side from a signed battery token, but per-item correctness is still client-reported (residual).

## Related Pages
- [[features/security-hardening.tech]]
- [[decisions/ADR-034-no-client-db-writes]]
- [[database/schema.tech]]
