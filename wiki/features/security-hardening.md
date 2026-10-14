---
title: Security Hardening (database and API access)
type: feature
status: planned
tech_page: ./security-hardening.tech.md
last_updated: 2026-10-14
open_questions:
  - "OPEN: TASK-884 (rate limiting) is deferred. Which shared store (for example Redis) and which per-route limits suit normal use must be answered before it can start."
  - "OPEN: what the TASK-875 audit and the TASK-878 tampering check actually find in live data. Nothing has been queried or fixed yet."
  - "ANSWERED 2026-10-14: admin operations go through the server with the service role; the admin policy on the users table is dropped."
  - "ANSWERED 2026-10-14: no admin session rotation, even if the audit finds unexpected admins."
  - "ANSWERED 2026-10-14: the users table loses all client write rights (no per-column allowlist)."
  - "ANSWERED 2026-10-14: the exercise-type effectiveness view is no longer readable by logged-in users; the admin page reads it through the server."
---

# Security Hardening (database and API access)

## Purpose
A 2026-10-14 security audit found that the public database API let any logged-in (and in some cases anonymous) caller
change data they should never touch. This feature closes those holes and keeps them closed.

## User Story
As a learner I can trust that my progress, tokens and reports are mine and cannot be altered or read by someone else, and as
the developer I can trust that nobody can promote themselves to admin, mint tokens, or read the answers before submitting a test.

## How It Works
The app has a browser, a Flask server and a Supabase database. The audit showed the browser-facing database door was
open far wider than the app ever uses. Everything the app does for a user already goes through the Flask server, which holds a
privileged key. So the fix is to shut the browser-facing door:

1. People can no longer edit their own account row (tier, token balance) or read everyone's reports.
2. Thirty-two internal tables that had no protection at all are locked down.
3. Internal database functions (payments, progress writing, calibration, pipeline helpers) can only be called by the server.
4. Analytics views stop exposing per-learner data.
5. Progress tables become read-only for the browser.
6. A test and a written rule stop new tables or functions from being left open by mistake.
7. The server stops sending test answers before the learner submits, and stops trusting scores and durations sent by the browser.

Each database step is a migration that is written, reviewed and applied only when the developer approves it.

## Constraints & Edge Cases
- The server keeps working because it uses the privileged service key. Each step starts with a read-only check that every caller really does.
- Study-plan minutes that look wrong this week are checked for tampering first (TASK-878) before being treated as a logic bug.
- Rate limiting of AI-backed endpoints is a known gap. It is parked as a future improvement (TASK-884) and is not part of this work.

## Business Rules
- Browsers never write the database directly. See [[decisions/ADR-034-no-client-db-writes]].
- Every table in the public schema has row-level security turned on.
- Every sensitive function is callable only by the server, unless it is on a written exception list.
- Anything that changes the live database needs the developer's explicit approval.

## Open Questions
- OPEN: shared store and limits for rate limiting (TASK-884, deferred).
- OPEN: findings of the live audit queries (admins, token balances, tampered durations).

## Related Pages
- [[features/security-hardening.tech]]
- [[tasklist/security-hardening.tasks]]
- [[decisions/ADR-034-no-client-db-writes]]
- [[business-rules/auth-and-access]]
- [[database/schema.tech]]
