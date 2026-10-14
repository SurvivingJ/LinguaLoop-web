---
title: "Security Hardening — Task Breakdown"
feature: security-hardening
prose_page: ../features/security-hardening.md
tech_page: ../features/security-hardening.tech.md
total_tasks: 10
done: 2
---

# Security Hardening — Task Breakdown

Implements the remediation plan from the 2026-10-14 swarm security audit (findings S1..S17, see
[[features/security-hardening.tech]]) under [[decisions/ADR-034-no-client-db-writes]]. Nothing has been applied live
and no migration file exists yet; every status below is Not Started except TASK-884 (Deferred).

**Developer decisions (2026-10-14), binding on every task here:**
1. DROP policy `users_admin_all`. Admin operations go through Flask with the service role.
2. NO admin session rotation, even if the audit finds unexpected admins (the audit is still run and reported).
3. `users`: FULL REVOKE of client write privileges. No column allowlist.
4. `vw_exercise_type_effectiveness`: REVOKE `authenticated` SELECT. Admin reads go through Flask with the service role.
   Verified in code 2026-10-14: the only reference outside the migration is `scripts/validate_effectiveness_view.py:164`,
   which uses `get_supabase_admin()`; no route, service, template or static file reads the view.
5. TASK-884 (rate limiting) is NOT implemented. Filed as a potential future improvement, status Deferred, plan notes kept.
6. In-function `auth.uid()` checks are added only for functions that must stay EXECUTE-able by `authenticated` after
   hardening (`is_admin`, `is_moderator` and any allowlisted exception). `service_role`-only functions need none.

**Sequencing.** 875 (users, tokens, reports) -> 876 (RLS-off tables) -> 877 (functions) -> 878 (audit) -> 879 (views) ->
880 (progress tables and default privileges) -> 881 (regression guard) -> 882 and 883 (routes) -> 884 (deferred).
Every task marked LIVE-DB requires explicit user approval before any `apply_migration` or DDL ("requires user approval to apply live").

**Cross-cutting rules**
- Revoke from `PUBLIC`, `anon` and `authenticated` together. A revoke from `anon` alone does nothing, because `anon`
  inherits EXECUTE through the `PUBLIC` grant (`=X`).
- Every migration follows `migrations/CLAUDE.md`: idempotent and re-runnable, header comment stating purpose and
  "requires user approval to apply live", `NOT VALID` + `VALIDATE` where constraints are involved. Function revokes loop over
  `pg_proc` / `regprocedure`, so every overload is covered (live 8-arg and pending 10-arg `record_session_progress`,
  `plan_local_date`, `plan_local_day_start`).
- `service_role` bypasses RLS and keeps its own grants, so Flask is unaffected. This holds only if each service really uses the
  service key, which is a pre-flight check in each task.
- Audit queries are read-only SELECTs on catalogs and aggregates. Never select user data rows. Never auto-fix rows.

---

## TASK-875: Close the self-escalation and balance-forgery holes on `users`, `user_tokens` and `user_reports`

**Status:** [x] Done (repo) — awaiting live apply approval
**Repo status:** migrations/security_lock_users_tokens_reports.sql + migrations/audits/security_users_tokens_audit.sql + tests/sql/test_security_lock_users_tokens.sql. Counts-only audit run live read-only: 0 mismatches. SQL not executed (no local Postgres). Apply-order: independent.
**Feature:** security-hardening
**Type:** bug
**Complexity:** M (3-8h)
**Depends On:** none
**Approval:** LIVE-DB, requires user approval to apply.

**Description:** Covers S1, S4 and S9, the three critical or high paths that need only an anon key plus a normal login. A
user can PATCH their own `subscription_tier_id` to an admin tier and gain admin rights. A user can write their own
`purchased_tokens`. Anyone can read all `user_reports` via a `USING (true)` policy. Remove all client write access on
`users`, `user_tokens` and `token_transactions` (full revoke, no column allowlist) and the over-broad policy. Flask uses
`service_role`, so nothing legitimate breaks.

**Acceptance Criteria:**
- [ ] As `authenticated`, `UPDATE users SET subscription_tier_id=...` fails with permission denied.
- [ ] As `anon` and `authenticated`, INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER on `users`, `user_tokens` and `token_transactions` are revoked. No column-level UPDATE grant is added (decision 3).
- [ ] `user_tokens` and `users` keep own-row SELECT only, so "Users can view own tokens" still works.
- [ ] The policy "Admin can view all reports" is dropped. `anon` has no grants on `user_reports`, and `authenticated` keeps INSERT and own-row SELECT.
- [ ] Policies `users_update_own`, `Users can update own profile` and `Users update own profile` are dropped, as are `System can update tokens` and `tokens_own_data` (ALL). A separate own-row SELECT policy exists on `user_tokens`.
- [ ] Policy `users_admin_all` (ALL) is DROPPED (decision 1). The migration comment records that admin operations go through Flask with the service role.
- [ ] The read-only audit queries below were run before applying and their result was reported to the user. No admin session rotation is performed whatever they show (decision 2).

**Technical Notes:**
- Pre-flight, confirm live (read-only):
  - No SECURITY INVOKER function or trigger writes `users` or `user_tokens` as the caller. Check `pg_proc WHERE prosecdef=false` for bodies referencing these tables, and `pg_trigger`.
  - `grant_daily_free_tokens` and the other token RPCs are SECURITY DEFINER or run under `service_role`.
  - `tests/conftest.py`, which was the only client-side hit, does not rely on a user-JWT PATCH on `users`.
  - Because `users_admin_all` is dropped: confirm no browser or admin page issues Supabase calls with an admin user JWT. All admin pages must reach `users` through Flask with the service client (grep `static/` and `templates/` for `supabase` client use).
- Audit (read-only SELECT, aggregates and counts only): join `users` to `dim_subscription_tiers` where `is_admin` or a non-default tier is set, and compare `user_tokens.purchased_tokens` with `SUM(token_transactions)` per user. Report counts to the user. Do not auto-fix any rows and do not rotate sessions.

**Files to Create / Modify:**
- `migrations/security_lock_users_tokens_reports.sql` (new)
- `wiki/database/schema.tech.md` (update grants and policies for `users`, `user_tokens`, `token_transactions`, `user_reports`)

**Verification:** In a transaction, run `SET LOCAL ROLE authenticated; SET LOCAL request.jwt.claims = '{"sub":"<uuid>"}'; UPDATE users SET subscription_tier_id = ...`. Expect "permission denied". Repeat for `user_tokens`. As `anon`, `SELECT * FROM user_reports` expects permission denied. Smoke-test login, the token display, the report submit routes and an admin page through Flask.

---

## TASK-876: Enable RLS and revoke client access on the 32 unprotected tables

**Status:** [x] Done (repo) — awaiting live apply approval
**Repo status:** migrations/security_enable_rls_unprotected_tables.sql. Asserts exactly 32 tables at apply time. NOTE: the 5 analytics views are NOT security_invoker live, so this file alone does NOT close client access to them; apply security_views_invoker.sql (TASK-879) immediately after.
**Feature:** security-hardening
**Type:** bug
**Complexity:** S (1-3h)
**Depends On:** none
**Approval:** LIVE-DB, requires user approval to apply.

**Description:** Covers S2. Thirty-two public tables have RLS off and full DML plus TRUNCATE for `anon` and `authenticated`.
This includes `prompt_templates`, `llm_calls`, `exercises`, `word_assets`, `user_classifier_mastery`, and the `dt_*`,
`generation_*`, `corpus_*` and `dim_classifier*` tables. Enable RLS on all of them and revoke all privileges from the client
roles. No policies are needed, because only `service_role` accesses them.

**Acceptance Criteria:**
- [ ] `relrowsecurity = true` for all 32 tables.
- [ ] `has_table_privilege('anon'|'authenticated', t, any privilege)` is false for all 32.
- [ ] `service_role` still has its grants, and `postgres` is unchanged. Do not use FORCE RLS.
- [ ] The full test suite and the generation pipeline smoke test pass with the service key.

**Technical Notes:**
- Use `ALTER TABLE public.<t> ENABLE ROW LEVEL SECURITY; REVOKE ALL ON public.<t> FROM PUBLIC, anon, authenticated;` for each table. Derive the list from `pg_class` at apply time (`relrowsecurity=false AND relkind='r'` in `public`) rather than hardcoding. Assert that the result equals the expected 32, and fail the migration if it is not.
- Sequences: also `REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated`, with a pre-check of `pg_class` ACLs for sequences. Safe because there is no direct client insert.
- Pre-flight: grep `scripts/`, `tests/` and `services/` for any `create_client(` that uses an anon key against these tables. Confirm that `topic_generation` and `test_generation` DB clients use the service key.
- Some of these tables may be read by SECURITY INVOKER views or by user-facing code that uses the anon client (see TASK-883 about `TestService`). Check that none of the 32 is among them.

**Files to Create / Modify:**
- `migrations/security_enable_rls_unprotected_tables.sql` (new)
- `wiki/database/schema.tech.md` (RLS column and grants)

**Verification:** Run `SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND relkind='r' AND NOT relrowsecurity;` and expect no rows. As `anon`, `SELECT 1 FROM prompt_templates LIMIT 1` should return permission denied. Then run the generation pipeline once with the service key.

---

## TASK-877: Function-grant hardening migration (REVOKE/GRANT per function plus pinned search_path)

**Status:** [x] Done (repo) — awaiting live apply approval
**Repo status:** migrations/security_function_grants_group_a.sql (apply alone first), security_function_grants_group_b.sql, security_function_auth_checks.sql (is_admin/is_moderator only; decision 6). Re-run group B after the session-budget migrations are applied to sweep the pending-branch functions. Function default privileges are revoked database-wide for postgres (see group B warning).
**Feature:** security-hardening
**Type:** bug
**Complexity:** L (1-2d)
**Depends On:** none. Coordinate with the pending branch (`claude/session-budget-settings`). If it has merged, this task runs after it. If not, this migration is a superset and the pending REVOKEs become no-ops.
**Approval:** LIVE-DB, requires user approval to apply. Stage the groups below as separate applies so a failure is easy to roll back.

**Description:** Covers S3, S5, S6, S7, S8, S13 and S17. Every SECURITY DEFINER function that takes a user id or mutates
shared state must be executable only by `service_role`. Today the live ACL is `{=X, anon=X, authenticated=X, service_role=X}`,
so anon can call them. The migration revokes by exact signature using the caller map, and pins `search_path` where it is
missing. Per decision 6, `service_role`-only functions get NO in-function `auth.uid()` check; such a check is added only to
functions that remain EXECUTE-able by `authenticated` (`is_admin`, `is_moderator`, plus any allowlisted exception, each of
which takes no caller-supplied user id).

**Acceptance Criteria:**
- [ ] No function in the groups below is executable by `PUBLIC`, `anon` or `authenticated`. `service_role` and `postgres` retain EXECUTE.
- [ ] Functions without a pinned search_path (`process_stripe_payment`, `update_classifier_mastery`, `get_classifier_drill_session`, `max_unlocked_tier`, `batch_lookup_lemmas`, `process_classifier_drill_submission`, `process_pinyin_submission`, `process_pitch_accent_submission`) have `proconfig` containing `search_path=public, pg_temp`.
- [ ] `is_admin` and `is_moderator` remain executable by `authenticated`, because RLS policies evaluate them as the caller. Any function left executable by `authenticated` is on a written allowlist and, if it accepts a user id, checks `auth.uid()` inside the body.
- [ ] `handle_new_user` and the trigger functions keep working. Only their RPC exposure is trimmed.
- [ ] The Flask integration tests pass: study plan, practice session, calibration, classifier drill, IRT calibrator and token flow.
- [ ] `ALTER DEFAULT PRIVILEGES` stops future functions from being granted to the client roles (applied in TASK-880).

**Function groups** (order of application):

| Group | Functions | Source |
|---|---|---|
| A: critical | `process_stripe_payment(uuid,integer,text,text,integer)` | S3 |
| B: write RPCs | every overload of `record_session_progress` (8-arg live, 10-arg pending), `apply_attempt_timing_and_progress`, `compute_weekly_plan_persist`, `apply_study_plan_template`, `build_daily_session`, `compute_weekly_plan_load_signals`, `plan_local_date`, `plan_local_day_start`, `update_classifier_mastery`, `irt_apply_calibration`, `irt_try_lock`, `irt_release_lock`, `calibration_*` (all six), `process_*_submission` x3, `add_tokens_atomic`, `anonymize_user_data` | S5, S6, S7, S17 |
| C: read and pipeline RPCs | the S8 list (14 functions), the S13 list (`pg_try_advisory_lock_for_*`, `pg_advisory_unlock_for_*`, `refresh_*`, `match_topics*`, `get_distractors` and similar) | S8, S13 |

**Technical Notes:**
- Use a `DO` block that iterates `pg_proc` by `proname` (not by hand-typed signature), so every overload is revoked. It emits `REVOKE ALL ON FUNCTION <oid::regprocedure> FROM PUBLIC, anon, authenticated; GRANT EXECUTE ON FUNCTION <oid::regprocedure> TO service_role;`. For the `pg_try_advisory_lock_for_*` family use `LIKE`. Raise an exception if an expected name matches zero functions, so a rename cannot slip through silently. The loop runs `ALTER FUNCTION ... SET search_path = public, pg_temp` for the unpinned list. Do not change the three `irt_*` functions, which already have `search_path=public`.
- Pre-flight caller verification (read-only, before applying):
  1. Confirm each calling service's DB client uses the service key. Services to check: `services/classifier_drill_service.py:148`, `services/irt/calibrator.py`, `calibration_service.py:186/259/304/471`, `study_plan_service.py:638/813/858/959/974/1083/1098`, `study_session.py:737`, `practice_session_service.py:703`, `tests.py:288`, `study_plan.py:487` and `queue_drain.py`. Pay particular attention to the two with a Medium-low risk rating, the classifier drill and the IRT calibrator.
  2. Look for SECURITY INVOKER functions or triggers that call `plan_local_date`, `plan_local_day_start` or the other revoked functions. A caller running as `authenticated` or `anon` would then fail with permission denied. Query `pg_proc.prosrc` for these names.
  3. Check that no RLS policy or column default calls any function in the groups above. Policies evaluate functions as the invoking role.
- `calibration_next_anchor` (singular) is not SECURITY DEFINER. Review its grant separately and revoke it too if only `service_role` calls it.
- S7 (calibration functions trust `p_user_id`): the revoke removes the exposure. No `auth.uid()` check is added inside these `service_role`-only functions (decision 6).
- Apply Group A first and alone, since it is the critical one and has no callers. Then B, then C. After each, re-read `proacl` and confirm the `PUBLIC` entry (`=X`) is gone.

**Files to Create / Modify:**
- `migrations/security_function_grants_hardening.sql` (new; the DO-block loop and the search_path pins)
- `wiki/api/rpcs.tech.md` (add an "Execute grant" column per RPC)
- `wiki/database/schema.tech.md`

**Verification:** Run `SELECT proname, oid::regprocedure, proacl, proconfig FROM pg_proc WHERE pronamespace='public'::regnamespace AND prosecdef AND (has_function_privilege('anon',oid,'EXECUTE') OR has_function_privilege('authenticated',oid,'EXECUTE'));` Expect only the allowlist (`is_admin`, `is_moderator` and anything policy-required). Run a full session-end flow in staging through Flask, then confirm `POST /rest/v1/rpc/process_stripe_payment` with the anon key returns 401/403.

---

## TASK-878: Rule out tampering before debugging the study-plan minutes

**Status:** [ ] Not Started
**Feature:** security-hardening
**Type:** bug (investigation)
**Complexity:** S (1-3h)
**Depends On:** TASK-877 applied, so the evidence stops changing.
**Approval:** read-only live queries only; needs a project id for the Supabase tool.

**Description:** The follow-up item is that this week's recorded minutes on the study plan page are inaccurate. The 8-arg
`record_session_progress` and `apply_attempt_timing_and_progress` were anon-callable, and S15 shows the durations are
client-claimed with no upper bound. Before treating the discrepancy as a logic bug, find out whether the data was tampered
with, then hand off to the minutes fix.

**Acceptance Criteria:**
- [ ] Report the number of `test_attempts` this week with implausible duration (for example over a stated cap or `finished_at < started_at`) and `weekly_plan_states` rows whose minutes are not reconcilable with attempts.
- [ ] State a clear conclusion: tampering, client-claimed durations, or a genuine logic bug.
- [ ] If the cause is logic, open a separate task for the minutes bug. This plan does not fix it.

**Technical Notes:** Compare `weekly_plan_states` minutes with `SUM` of attempt durations per user and week, using `plan_local_date` boundaries. Check that timezone week boundaries match between `plan_local_date` and the page. Do not select user rows beyond aggregates and counts. Anything that needs user rows goes to the user.

**Files to Create / Modify:** none. The result is reported to the user.

**Verification:** The written conclusion, backed by the aggregate queries.

---

## TASK-879: Analytics views, run as invoker and drop client grants

**Status:** [x] Done (repo) — awaiting live apply approval
**Repo status:** migrations/security_views_invoker.sql (8 views: security_invoker=true, client grants revoked, service_role SELECT). Decision 4 verified in code: only reader of vw_exercise_type_effectiveness is scripts/validate_effectiveness_view.py (service role). tests/sql/test_security_progress_tables.sql covers it.
**Feature:** security-hardening
**Type:** bug
**Complexity:** M (3-8h)
**Depends On:** TASK-876
**Approval:** LIVE-DB, requires user approval to apply.

**Description:** Covers S11. Eight views run as owner and are granted to `anon` and `authenticated` with write grants.
`vw_distractor_error_analysis` is per-user (`user_id`, error pattern) and is the real leak, so it goes first. The others are
aggregates and lower sensitivity. Decision 4: `vw_exercise_type_effectiveness` loses its `authenticated` SELECT as well
(its admin reader is Flask with the service role; verified in code, see top of this file).

**Acceptance Criteria:**
- [ ] Write grants (INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER) are revoked on all eight views from both client roles.
- [ ] `vw_distractor_error_analysis` has no `anon` or `authenticated` SELECT.
- [ ] `vw_exercise_type_effectiveness` has no `anon` or `authenticated` SELECT (the grant at `migrations/task534_exercise_type_effectiveness.sql:119` is revoked, decision 4). `scripts/validate_effectiveness_view.py` still works because it uses `get_supabase_admin()`.
- [ ] `ALTER VIEW ... SET (security_invoker = true)` is applied to all eight.
- [ ] `v_sense_family_coverage` still works for `queue_drain.py` via `service_role`.
- [ ] The other aggregate views are either service_role-only too, or each retained client SELECT is justified in the migration comment after callers are checked (none was found in the repo).

**Technical Notes:** Read the definitions of `corpus_statistics`, `v_ladder_judge_reject_rates` and `v_sense_family_coverage`, which were not inspected, before deciding which to lock fully. `security_invoker = true` on a view over RLS tables returns only the caller's rows to any non-service reader, so aggregates would become per-user for `authenticated`. Aggregates that must stay readable by `authenticated` would need a definer-style aggregate function or to stay as-is; the default is service_role-only. Re-run the live check of `relacl` and `reloptions` before applying (not confirmed live for S11).

**Files to Create / Modify:**
- `migrations/security_analytics_views_lockdown.sql` (new)
- `wiki/database/schema.tech.md`

**Verification:** Run `SELECT relname, reloptions, relacl FROM pg_class WHERE relname IN (...)`. As `anon`, `SELECT * FROM vw_distractor_error_analysis` returns permission denied. As `authenticated`, `SELECT * FROM vw_exercise_type_effectiveness` returns permission denied. Run the vocabulary ladder queue drain once and `scripts/validate_effectiveness_view.py` once.

---

## TASK-880: Lock down client-writable progress tables and the default privileges

**Status:** [x] Done (repo) — awaiting live apply approval
**Repo status:** migrations/security_lock_progress_tables.sql (12 tables + default privileges for tables and sequences). tests/sql/test_security_progress_tables.sql. attempt_responses is a similar client-writable table not in the plan list; consider adding.
**Feature:** security-hardening
**Type:** bug
**Complexity:** M (3-8h)
**Depends On:** TASK-875, TASK-877
**Approval:** LIVE-DB, requires user approval to apply.

**Description:** Covers S10 and S12. Progress tables allow own-row writes from `authenticated`, which lets a user forge ELO,
attempts and ladder state. `test_attempts` has an insert policy that contradicts `attempts_no_manual_insert`. Separately, the
schema grants everything to `anon` by default, so protection rests on RLS alone. Fix the progress tables first, then trim
blanket grants and default privileges.

**Acceptance Criteria:**
- [ ] On `user_skill_ratings`, `test_attempts`, `exercise_attempts`, `question_attempt_results`, `user_vocabulary_knowledge`, `user_word_ladder`, `daily_test_loads`, `user_flashcards`, `calibration_sessions`, `calibration_responses`, `weekly_plan_states` and `user_study_plans`: own-row SELECT policy only, write policies dropped (including the contradictory `test_attempts` insert policy), and INSERT/UPDATE/DELETE/TRUNCATE revoked from `anon` and `authenticated`.
- [ ] `anon` has no table, sequence or function privileges in `public` (S12), except any explicitly allowlisted object.
- [ ] `authenticated` holds no TRUNCATE, TRIGGER or REFERENCES anywhere in `public`.
- [ ] `ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES, SEQUENCES, FUNCTIONS FROM anon, authenticated, PUBLIC`, for both the `postgres` and `supabase_admin` roles. Confirm in `pg_default_acl` live.
- [ ] Existing own-row SELECT paths and the Flask flows are unaffected.

**Technical Notes:** Verified policy lists for S5 tables were not read, so read the actual policy names with `pg_policies` first. The blanket `REVOKE ... FROM anon` over all tables is wide, so run it after TASK-876 and TASK-879, and re-run the Flask smoke tests. `is_admin()` and `is_moderator()` must still work for `authenticated`; they read `users` through a SECURITY DEFINER function, so they are unaffected by table revokes.

**Files to Create / Modify:**
- `migrations/security_progress_tables_and_default_privileges.sql` (new)
- `wiki/database/schema.tech.md`
- `wiki/business-rules/data-write-paths.md` (new; states that clients never write the DB directly, see [[decisions/ADR-034-no-client-db-writes]])

**Verification:** Query `pg_policies` and `information_schema.role_table_grants` for the listed tables, and `pg_default_acl`. Run an end-to-end practice session and a study plan load in staging.

---

## TASK-881: Regression guard for ACLs and RLS, plus a migrations/CLAUDE.md rule

**Status:** [x] Done
**Repo status:** tests/test_migration_security_lint.py (static lint, 9 tests), tests/sql/check_function_acls.sql (read-only catalog check, not yet run live), migrations/CLAUDE.md rule. Not built: pytest catalog test gated on SUPABASE_DB_URL and function_acl_allowlist.txt (SQL script substituted). Pending lint exemptions: session_module_exclusions*.sql (historic CREATE OR REPLACE without REVOKE; group B sweeps them).
**Feature:** security-hardening
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-875, TASK-876, TASK-877 (the checks need the clean state to pass)
**Approval:** none (repo-only). The live check can be read-only.

**Description:** Pin the fixed state so it cannot recur. Two layers: a static test over `migrations/*.sql` that runs in CI
without a database, and a catalog test that runs against a live or staging database when credentials are present.

**Acceptance Criteria:**
- [x] Static test: every `CREATE [OR REPLACE] FUNCTION` that is `SECURITY DEFINER` in a migration is followed, in the same file or a later one, by a `REVOKE ... FROM PUBLIC` (or `anon`) for that function, or the function is in `tests/sql/function_acl_allowlist.txt` with a reason. It fails with the file and function name.
- [x] Static test: every `CREATE TABLE public.*` has `ENABLE ROW LEVEL SECURITY`.
- [ ] Catalog test (skipped when `SUPABASE_DB_URL` is absent):
  - No SECURITY DEFINER function in `public` is executable by `anon` or `authenticated` unless allowlisted. The allowlist must include `is_admin` and `is_moderator`.
  - Every `public` table has `relrowsecurity = true`.
  - `anon` has no table privileges, and `authenticated` has no write privileges on `users`, `user_tokens` or `token_transactions`.
  - No `public` function that takes a user id parameter lacks `search_path` in `proconfig`.
- [x] `migrations/CLAUDE.md` gains a rule: every new function must end with `REVOKE ALL ... FROM PUBLIC, anon, authenticated; GRANT EXECUTE ... TO service_role;` and `SET search_path = public, pg_temp`. Every new table must `ENABLE ROW LEVEL SECURITY` and revoke client grants. Any client-visible exception needs an allowlist entry plus an ADR.
- [x] The test fails when run against the pre-fix state. Prove it by running against a temporary copy that restores the old grants, or by inspecting the failing output once.

**Technical Notes:** Follow existing patterns in `tests/sql/` for how SQL checks are invoked. Do not call functions in the catalog test, only inspect `pg_proc`, `pg_class` and `pg_policies`. Make the allowlist a plain file so adding an exception shows up in code review.

**Files to Create / Modify:**
- `tests/test_migration_security_lint.py` (new, static)
- `tests/sql/test_function_acls.py` (new, catalog)
- `tests/sql/function_acl_allowlist.txt` (new)
- `migrations/CLAUDE.md` (add the rule)

**Verification:** `pytest tests/test_migration_security_lint.py tests/sql/test_function_acls.py -q` passes. Temporarily add an unrevoked SECURITY DEFINER function in a scratch migration and confirm the static test fails, then remove it.

---

## TASK-882: Route-level hardening for pre-submit answer keys and client-trusted results

**Status:** [x] Done (repo) — awaiting live apply approval
**Repo status:** Code done and tested (tests/test_security_route_hardening.py, services/attempt_timing.py, battery_token.py); migrations/security_questions_tests_policies.sql awaits live apply (deploy the Flask change first). RESIDUAL, not done: DB-side duration cap (security_duration_caps.sql not written); bounds/clamps in routes/classifier_drill.py, routes/counter_drill.py, study_session complete-block, study_plan, practice_session_service; gate/stress per-item is_correct is still client-reported and the battery token is replayable within 1h (a forged pass is still possible with all items marked correct; real fix is server-side grading per type).
**Feature:** security-hardening
**Type:** bug
**Complexity:** L (1-2d)
**Depends On:** TASK-876, TASK-880. Do it before the minutes fix ships, since S15 feeds those numbers.
**Approval:** none for the code. The `questions_read` / `tests_*` policy changes (S14 part 2) and the duration-cap migration are LIVE-DB and need user approval to apply.

**Description:** Covers S14 and S15. The test fetch routes return `answer` and `answer_explanation` before submit. Several
submit and result endpoints trust client-supplied scores, counts and durations. The minutes issue is a likely beneficiary, so
cap credited durations server-side.

**Acceptance Criteria:**
- [x] `GET /api/tests/test/<identifier>` and `GET /api/tests/<slug>` no longer return `answer` or `answer_explanation`. They are returned in the submit response. Update the frontend that consumed them.
- [ ] `TestService` reads of `tests` / `questions` and the `flagged_inputs` insert move to the admin client. Then `questions_read` and `tests_public_read` are tightened to tier-aware access, and `tests_user_create` is removed or replaced with a service path.
- [ ] `apply_attempt_timing_and_progress` and the practice/complete-block/daily-load routes cap credited duration (state the cap as a named constant, justified from test length) and reject `finished_at < started_at` and future timestamps.
- [x] `daily-load/complete` verifies a matching `test_attempts` row.
- [ ] `vocab-dojo/gate/result` derives pass/fail from a server-issued battery (the most severe item). `classifier-drill/submit`, `counter-drill/submit`, `submit-pinyin`, `submit-pitch-accent` and `stress-test/result` bound their inputs (`correct <= total`, sane `time_taken_ms`).
- [x] Unit tests cover each rejection path.

**Technical Notes:** Split into three PRs: answer keys, duration caps, then result validation, so each can be reverted alone. The duration cap changes the RPC body, so it needs a migration plus the revoke from TASK-877 re-applied (the pending-branch 10-arg `record_session_progress` is the obvious place).

**Files to Create / Modify:**
- `routes/tests.py`, `services/test_service.py`, frontend consumers of the answer fields
- `routes/study_session.py`, `routes/study_plan.py`, `services/practice_session_service.py`
- `routes/vocab_dojo*.py`, `services/classifier_drill_service.py`
- `migrations/security_duration_caps.sql` (new)
- `tests/` for each validation

**Verification:** Fetch a test with curl and confirm no answer fields. Submit with an out-of-range duration and expect a 400. Complete a normal session and confirm minutes are still credited.

---

## TASK-883: Small route and code cleanups

**Status:** [x] Done
**Repo status:** routes/users.py fails closed (500) without the service client; dead get_payment_service() factory removed (PaymentService class kept; developer may delete the module). 3 new tests in tests/test_users.py.
**Feature:** security-hardening
**Type:** refactor
**Complexity:** S (1-3h)
**Depends On:** TASK-877
**Approval:** none.

**Description:** Covers the code-side items of S17: remove the anon-client fallback at `routes/users.py:39` (fail closed if
the service key is missing), and delete the dead `payment_service` anon-client factory. A future Stripe webhook must use the
service key server-side.

**Acceptance Criteria:**
- [x] `routes/users.py` raises or returns 500 if the service client is unavailable, and never falls back to anon.
- [x] The dead payment factory is removed, with a grep confirming no references.
- [x] Tests pass.

**Files to Create / Modify:** `routes/users.py`, `services/payment_service.py`.

**Verification:** `pytest -q`, plus `grep -rn "payment_service" .` shows no live references.

---

## TASK-884: Rate limiting on LLM and auth endpoints (potential future improvement)

**Status:** Deferred (developer decision 2026-10-14: do NOT implement now; filed as a potential future improvement)
**Feature:** security-hardening
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** none (lowest priority)
**Approval:** none for code. A shared store (for example Redis) is an infrastructure decision, so ask before adding one.

**Description:** Covers S16. There is no limiter anywhere, and Gunicorn runs 2 workers, so in-memory limits would be
per-worker. When picked up: add `flask-limiter` keyed on user id and IP for `/api/tests/moderate`, `/api/vocabulary/extract`,
`/api/word-list/submit`, `/api/reports/submit`, `/api/dual-translation/*` and the OTP endpoints. Add input size caps and a
concurrent-batch limit for word-list submit (one daemon thread per submit today). The exposure meanwhile is cost and abuse
of LLM endpoints, not data disclosure; the data-exposure findings are closed by TASK-875 to TASK-882.

**Acceptance Criteria (for when it is un-deferred):**
- [ ] Limits are configured by constant per route, with a 429 and `Retry-After`.
- [ ] Content-size caps apply before the call to OpenAI moderation.
- [ ] Word-list submit allows at most N concurrent batches per user.
- [ ] A test confirms the 429 behavior.

**Open question `[?]`:** which shared store, and what limits suit normal use. Must be answered before the task can leave Deferred.

**Files to Create / Modify:** `app.py` (limiter init), the listed route files, `requirements.txt`.

**Verification:** Hit a limited route N+1 times and expect a 429.

---

## Accepted risk list (explicit, with reasons)

| Item | Decision | Reason |
|---|---|---|
| S7 in-function `auth.uid()` check | Not added to `service_role`-only functions (decision 6) | The revoke removes the exposure. A check is added only to functions that stay EXECUTE-able by `authenticated`. Revisit if a user-JWT RPC caller is ever added. |
| FORCE RLS on the 32 tables | Not done | It would bind the owner role and could break migrations or scripts connecting as `postgres`. |
| `add_tokens_atomic` stub returning true | Accepted | No exploit. Revoked in TASK-877 Group B anyway. |
| Trigger functions callable via RPC | Accepted | Not invokable via RPC. Only the grant trim in TASK-877 applies. |
| Aggregate analytics views (S11, non-per-user) | Lower priority | Low sensitivity. Handled in TASK-879 after `vw_distractor_error_analysis`. |
| Own-data-only forgery that remains after TASK-880 (S10) | Residual | Server-side routes remain client-trusted until TASK-882 completes. |
| Admin session rotation after S1 | Not done (decision 2) | Developer decision. The TASK-875 audit still reports unexpected admins; remediation of rows is the user's call. |
| No rate limiting (S16) | Deferred (decision 5) | TASK-884 is a potential future improvement. |

## Caveats

- Live grants and `reloptions` for the S3, S6, S11 and S13 objects were not confirmed live by the audit (it fell back to the repo), so TASK-877 and TASK-879 each start with a read-only catalog check.
- The S5 object list should drop `weekly_plan_states`, `user_study_plans`, `daily_test_loads` and `test_attempts` as function targets. They have RLS on. Their direct table path is handled in TASK-880 after the policies are read.
- Any migration here needs user approval to apply live. None has been written or applied.
