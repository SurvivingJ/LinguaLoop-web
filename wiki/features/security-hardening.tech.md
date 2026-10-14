---
title: Security Hardening — Technical Specification
type: feature-tech
status: planned
prose_page: ./security-hardening.md
last_updated: 2026-10-14
dependencies:
  - "tables: users, user_tokens, token_transactions, user_reports and the 32 RLS-off tables (see TASK-876)"
  - "progress tables: user_skill_ratings, test_attempts, exercise_attempts, question_attempt_results, user_vocabulary_knowledge, user_word_ladder, daily_test_loads, user_flashcards, calibration_sessions, calibration_responses, weekly_plan_states, user_study_plans"
  - "views: eight analytics views incl. vw_distractor_error_analysis, vw_exercise_type_effectiveness, v_sense_family_coverage, corpus_statistics, v_ladder_judge_reject_rates"
  - "functions: process_stripe_payment, record_session_progress (all overloads), calibration_*, process_*_submission, irt_*, S8 and S13 lists"
  - "package (deferred): flask-limiter"
breaking_change_risk: high
open_questions:
  - "OPEN: findings of the read-only live audits (admin tiers, purchased_tokens vs token_transactions, duration outliers). Not run yet."
  - "OPEN: live grants and reloptions for the S3, S6, S11 and S13 objects were not confirmed live by the audit."
  - "OPEN: shared store and limits for rate limiting (TASK-884, Deferred)."
---

# Security Hardening — Technical Specification

Authoritative task list: [[tasklist/security-hardening.tasks]]. Principle: [[decisions/ADR-034-no-client-db-writes]].
Nothing described here is applied live. Every task marked LIVE-DB in the table below requires the user's explicit approval
before any `apply_migration` or DDL ("requires user approval to apply live").

## Architecture Overview

Threat model: an attacker holds the public anon key (shipped to every browser) and optionally an ordinary learner login. They
call PostgREST (`/rest/v1/<table>`, `/rest/v1/rpc/<fn>`) directly, bypassing Flask. Anything the `anon` or `authenticated`
Postgres roles can do is therefore attacker-reachable. Flask connects with `service_role` (BYPASSRLS, own grants), so removing
client-role privileges does not affect it provided each service really uses the service key (a pre-flight check per task).

Target state: `anon` and `authenticated` have no table writes, no privileged function EXECUTE, and only own-row SELECT on
tables the browser legitimately reads. `PUBLIC` is revoked wherever `anon` is, because `anon` inherits EXECUTE through the `=X`
PUBLIC grant. RLS is on for every public table. `ALTER DEFAULT PRIVILEGES` keeps new objects closed (TASK-880), and a static
plus a catalog test keep it that way (TASK-881).

## Findings

Severity follows the audit grouping: S1 to S9 were the 9 high/critical findings, all of which survived adversarial
verification (0 refuted); S10 to S17 were the 8 medium/low findings, not adversarially verified. The remediation plan
states the S-numbers only in task descriptions, so the one-line wording and the critical-vs-high split in this table are
reconstructed from those task descriptions; the audit report holds the original evidence and should win on any difference.

| ID | Finding | Severity | Task |
|----|---------|----------|------|
| S1 | A user can PATCH their own `users.subscription_tier_id` to an admin tier and gain admin rights (policies `users_update_own`, `Users can update own profile`, `Users update own profile`; `users_admin_all` ALL is an admin-JWT write path) | Critical | TASK-875 |
| S2 | 32 public tables have RLS off and full DML + TRUNCATE for `anon` and `authenticated` (`prompt_templates`, `llm_calls`, `exercises`, `word_assets`, `user_classifier_mastery`, `dt_*`, `generation_*`, `corpus_*`, `dim_classifier*`) | Critical | TASK-876 |
| S3 | `process_stripe_payment(uuid,integer,text,text,integer)` is SECURITY DEFINER with ACL `{=X, anon=X, authenticated=X, service_role=X}` and no pinned search_path: anonymous payment forgery | Critical | TASK-877 Group A |
| S4 | A user can write their own `user_tokens.purchased_tokens` (policies `System can update tokens`, `tokens_own_data` ALL) | High | TASK-875 |
| S5 | Client-callable write RPCs and own-row write policies on progress state (forge ELO, attempts, ladder) | High | TASK-877 B, TASK-880 |
| S6 | Anon-callable write RPCs: all overloads of `record_session_progress`, `apply_attempt_timing_and_progress`, `compute_weekly_plan_persist`, `apply_study_plan_template`, `build_daily_session`, `update_classifier_mastery`, `process_*_submission` | High | TASK-877 B |
| S7 | `calibration_*` and `irt_*` functions trust a caller-supplied `p_user_id` | High | TASK-877 B |
| S8 | 14 read RPCs that take a user id leak other users' data when called with an arbitrary id | High | TASK-877 C |
| S9 | `user_reports` policy "Admin can view all reports" is `USING (true)`: every report is readable | High | TASK-875 |
| S10 | Progress tables allow own-row writes from `authenticated`; `test_attempts` insert policy contradicts `attempts_no_manual_insert` | Medium | TASK-880 |
| S11 | Eight analytics views run as owner, granted to `anon`/`authenticated` with write grants; `vw_distractor_error_analysis` is per-user | Medium | TASK-879 |
| S12 | Schema default privileges grant everything to `anon`; protection rests on RLS alone | Medium | TASK-880 |
| S13 | Pipeline RPCs exposed (`pg_try_advisory_lock_for_*`, `pg_advisory_unlock_for_*`, `refresh_*`, `match_topics*`, `get_distractors`) | Medium | TASK-877 C |
| S14 | Test fetch routes return `answer` and `answer_explanation` before submit; `questions_read` / `tests_public_read` / `tests_user_create` too permissive | Medium | TASK-882 |
| S15 | Submit/result endpoints trust client-supplied scores, counts and durations (`vocab-dojo/gate/result`, `classifier-drill/submit`, `counter-drill/submit`, `submit-pinyin`, `submit-pitch-accent`, `stress-test/result`, `daily-load/complete`) | Medium | TASK-882 |
| S16 | No rate limiting anywhere; Gunicorn runs 2 workers; unbounded LLM spend and OTP abuse | Low | TASK-884 (Deferred) |
| S17 | Cleanups: anon-client fallback `routes/users.py:39`, dead `payment_service` anon factory, `anonymize_user_data`, `add_tokens_atomic` stub, unpinned search_path | Low | TASK-877, TASK-883 |

## Approach and approval requirement

| Task | Scope | Findings | Live DB? |
|------|-------|----------|----------|
| TASK-875 | Full revoke on `users`/`user_tokens`/`token_transactions`; drop write policies and `users_admin_all`; drop open `user_reports` policy; read-only audit, no row fixes, no session rotation | S1, S4, S9 | LIVE-DB, requires user approval to apply |
| TASK-876 | `ENABLE RLS` + `REVOKE ALL` on the 32 tables (list derived from `pg_class`, asserted = 32; no FORCE RLS) | S2 | LIVE-DB, requires user approval to apply |
| TASK-877 | Per-function REVOKE (PUBLIC, anon, authenticated) + GRANT service_role by `pg_proc` loop; pin `search_path = public, pg_temp`; Groups A, B, C applied separately | S3, S5-S8, S13, S17 | LIVE-DB, requires user approval to apply |
| TASK-878 | Aggregate-only read-only queries for tampering before the minutes bug is debugged | S6, S15 | Read-only SELECTs; no approval for DDL (none) |
| TASK-879 | Views: revoke writes, revoke `anon`/`authenticated` SELECT on `vw_distractor_error_analysis` and `vw_exercise_type_effectiveness`, `security_invoker = true` | S11 | LIVE-DB, requires user approval to apply |
| TASK-880 | Progress tables own-row SELECT only; revoke `anon` everywhere; default privileges for `postgres` and `supabase_admin` | S10, S12 | LIVE-DB, requires user approval to apply |
| TASK-881 | Static migration lint, catalog test, `migrations/CLAUDE.md` rule | prevention | Repo-only (catalog test read-only) |
| TASK-882 | Strip answer keys from fetch routes; server-side duration caps and input bounds; tighten `questions_read`, `tests_*` policies | S14, S15 | Code: no. Policy and duration-cap migrations: LIVE-DB, requires user approval to apply |
| TASK-883 | Remove anon fallback, delete dead payment factory | S17 | No |
| TASK-884 | Rate limiting | S16 | Deferred, not implemented |

### Developer decisions (2026-10-14)
1. `users_admin_all` is dropped; admin operations run in Flask with the service role.
2. No admin session rotation.
3. `users`: full revoke of client write privileges, no column allowlist.
4. `vw_exercise_type_effectiveness`: `authenticated` SELECT revoked. Verified in code: the only non-migration reader is `scripts/validate_effectiveness_view.py` via `get_supabase_admin()`; no route, template or static code reads it.
5. TASK-884 is not implemented; filed as a potential future improvement (Deferred).
6. In-function `auth.uid()` checks only for functions that remain EXECUTE-able by `authenticated` (`is_admin`, `is_moderator`, allowlisted exceptions); `service_role`-only functions need none.

## Database Impact
Reads/writes: see [[database/schema.tech]] "Security posture" section for the target grants. New migrations (all idempotent, per
`migrations/CLAUDE.md`): `security_lock_users_tokens_reports.sql`, `security_enable_rls_unprotected_tables.sql`,
`security_function_grants_hardening.sql`, `security_analytics_views_lockdown.sql`,
`security_progress_tables_and_default_privileges.sql`, `security_duration_caps.sql`. None exists yet.

## API / RPC Surface
No new RPCs. Execute grants of existing RPCs change: [[api/rpcs.tech]] gains an "Execute grant" column (TASK-877). Allowlist
of functions that stay executable by `authenticated`: `is_admin`, `is_moderator`, plus anything proven policy-required.
Route changes (TASK-882): test fetch routes drop `answer`/`answer_explanation`; submit responses carry them; several result
endpoints validate inputs and cap durations by a named constant.

## Key Architectural Decisions
1. **Decision:** Browser roles get no table writes or privileged EXECUTE; all writes go through Flask with the service role.
   - **Rationale:** the app has no direct browser caller; see [[decisions/ADR-034-no-client-db-writes]].
   - **Alternatives rejected:** column allowlists and per-function `auth.uid()` checks as the primary defence.
2. **Decision:** Revoke from PUBLIC, anon and authenticated together, looping over `pg_proc` so all overloads are covered.
   - **Rationale:** a revoke from anon alone is a no-op because of the PUBLIC `=X` grant.
3. **Decision:** No FORCE RLS on the 32 tables.
   - **Rationale:** it would bind the owner role and could break migrations and scripts running as `postgres`.

## Security Considerations
Residual after TASK-880: own-data forgery via client-trusted server routes until TASK-882 is complete. Without TASK-884 the
LLM-backed endpoints remain open to cost abuse. Tampering that already happened is not undone by these migrations; TASK-875 and
TASK-878 report, they do not repair.

## Testing Strategy
Per-task verification is in [[tasklist/security-hardening.tasks]]: role-switched transactions asserting "permission denied",
catalog queries for `relrowsecurity`, `proacl`, `proconfig`, `pg_policies`, `pg_default_acl`; Flask integration smoke tests
(study plan, practice session, calibration, classifier drill, IRT calibrator, token flow, generation pipeline, queue drain);
and TASK-881's static and catalog regression tests, proven to fail on the pre-fix state.
