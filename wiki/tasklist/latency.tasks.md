---
title: "Latency — Task Breakdown"
feature: latency
prose_page: ../evaluations/latency-2026-11-11.md
tech_page: ../decisions/ADR-042-request-scoped-caching-and-static-asset-caching.md
total_tasks: 10
done: 8
---

# Latency — Task Breakdown

Source: the 2026-11-11 latency audit and fix pass ([[evaluations/latency-2026-11-11]],
[[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]]). The developer asked for
every suggested fix **except** raising gunicorn concurrency (hobby-tier Railway instance).

---

## TASK-925: Stop `resolve_plan_timezone` scanning `pg_timezone_names`

**Status:** [x] Done (applied live by the developer 2026-11-11, verified)
**Feature:** latency
**Type:** refactor
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
`pg_timezone_names` reads the tz database from disk on each call (~55 ms warm, ~300–500 ms
cold), and it sat inside every plan-local-date helper. Snapshot the names into `public.tz_names`
and look them up by primary key, falling back to the scan only for an unknown name. Same
migration: drop the four duplicate indexes, index the foreign keys whose parents are deleted,
and wrap `auth.uid()` / `auth.role()` in RLS policies in a scalar sub-select.

**Acceptance Criteria:**
- [x] `resolve_plan_timezone` returns the same value as before for every name in `pg_timezone_names`, for `''`, NULL and garbage.
- [x] Every `plan_local_date` caller loses its ~55 ms floor (measured in the evaluation).
- [x] Policy digest after unwrapping equals the pre-migration digest `9de38a5b2b08aef7f7062e70060c543a` (106 policies; digest of `tablename|policyname|cmd|roles|permissive|qual|with_check` ordered by table, policy — unwrap `( SELECT auth.x() AS x)` → `auth.x()` before hashing).
- [x] Advisor: `duplicate_index` and `auth_rls_initplan` findings gone.

**Files to Create / Modify:**
- `migrations/latency_2026_11_db.sql` — the migration (idempotent).
- `migrations/latency_2026_11_db_rollback.sql` — exact rollback (not applied).

**Verification:** `SELECT public.resolve_plan_timezone('Asia/Tokyo')` under `EXPLAIN ANALYZE`
is < 1 ms; rerun the advisor.

---

## TASK-926: Per-request cache for the `user_study_plans` row

**Status:** [x] Done 2026-11-11
**Feature:** latency
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
`services/request_cache.py` (GET/HEAD-only memo on `flask.g`) and
`day_boundary.plan_row()`; every request-path read of the plan row goes through it.

**Acceptance Criteria:**
- [x] One `user_study_plans` read per GET for study-session, practice/session and study-plan.
- [x] PUT/POST never served from cache; failures not cached; callers get copies.
- [x] `GET /api/study-plan` response shape unchanged.

**Files:** `services/request_cache.py`, `services/day_boundary.py`, `services/test_service.py`,
`services/practice_session_service.py`, `services/prestudy.py`, `services/study_plan_service.py`,
`routes/study_plan.py`, `tests/test_latency_caching.py`, `tests/test_session_modules_routes.py`.

---

## TASK-927: Memoise the new-word state; cache the `dim_test_types` minutes map

**Status:** [x] Done 2026-11-11
**Feature:** latency
**Type:** refactor
**Complexity:** S (1-3h)
**Depends On:** TASK-926

**Description:**
`PracticeSessionService.new_word_state` computed once per GET (it ran up to three times),
invalidated by every `user_word_ladder` writer and by a same-request `rebuild_today`.
`_test_time_estimate` reads one `{type_code: p50}` map per client, cached 10 minutes.

**Acceptance Criteria:**
- [x] `review_governor_state` and `ladder_new_word_state` called once per study-session / practice GET.
- [x] `dim_test_types` read once per `/api/study-plan` (was 6–7×).
- [x] A ladder insert inside the request forces a recount (unit test).

---

## TASK-928: Compress responses and long-cache content-hashed static files

**Status:** [x] Done 2026-11-11 (measured)
**Feature:** latency
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
`services/static_assets.py`: `?v=<sha1[:10]>` on every `url_for('static')`, one-year
`Cache-Control` for versioned requests only, Flask-Compress (gzip for pages/JSON, br/zstd for
streamed static files), versioned i18n URLs via `window.LINGUA_I18N_VERSIONS`.
`requirements.txt` gains `Flask-Compress==1.26`.

**Acceptance Criteria:**
- [x] Warm page loads serve every versioned static file from the browser cache (measured: 0 → all).
- [x] A changed file gets a new URL; unversioned requests still revalidate.

---

## TASK-929: Remove start-up waterfalls in the browser

**Status:** [x] Done 2026-11-11 (measured; walkthrough 16/16)
**Feature:** latency
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-928

**Description:**
Embed `/api/metadata` in every page; load both i18n files in parallel from script start;
session page imports players on demand and preloads today's; prestudy fetches its data in
parallel with i18n; test page reuses the preview's `/api/tests/test/<slug>` payload;
`authFetch` waits for the head-script renewal and shares one renewal across 401s;
`test-intro.js` only on test/drill pages; session-page classic scripts deferred.

**Acceptance Criteria:**
- [x] No page awaits `/api/metadata` before its first API call.
- [x] vitest `player-registry.test.js`: spinner → real mount, destroy-before-load cancels.
- [x] Browser walkthrough with the test account: 16/16 checks; same-data screenshots 19/22 identical (calibration = random word; profile = pre-existing highlight bug, fixed). Found and fixed an i18n render race (`LinguaMetadata.load()` now waits for translations).

---

## TASK-930: Assemble the daily session in one RPC

**Status:** [x] Done 2026-11-11 — option B live: study-session 14 → 6 DB calls, median 3.8 → 1.6 s (−58%); bundles identical to the per-table reads on live data (ADR-043). Option A deferred ([[decisions/ADR-043-one-call-daily-session]])
**Feature:** latency
**Type:** refactor
**Complexity:** L (1-2d)
**Depends On:** TASK-926

**Description:**
`GET /api/study-session` still makes ~14 sequential round trips (daily load, enrichment,
intake, speed-round check, prestudy planning, governor). Moving the read side into one SQL
function would cut it to 2–3. Needs a design pass: intake writes, prestudy planning lives in
Python (`services/prestudy.py`).

**Verification:** HTTP harness from [[evaluations/latency-2026-11-11]]: ≤ 4 DB calls (option A); option B target 6. After applying the migration: `python scripts/check_session_merges_parity.py` exits 0, and the harness shows `study-session` at 6 calls.

---

## TASK-931: Keep content-generation batch jobs off learners' hours

**Status:** [ ] Not Started
**Feature:** latency
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
`pg_stat_statements` shows batch work dominating DB time (embedding updates 13,700 s total,
calibration distractor chunks up to 22 s each) on a small instance (`shared_buffers` 224 MB).
User-facing worst cases (3–7 s) likely coincide. Schedule/throttle these runs off-peak, or
raise the compute size only while they run. Operational — the developer's call.

---

## TASK-932: Consolidate multiple permissive RLS policies

**Status:** [x] Done 2026-11-11 — applied live by the developer (self-verifying probes passed): 22 tables now have one policy per command (49 policies); only `tests` keeps overlapping SELECT policies (different role lists, skipped by design); advisor `multiple_permissive_policies` → 6 findings, all on `tests`. Follow-up `migrations/rls_tests_single_select_policy.sql` (written 2026-11-11, self-verifying, tested locally; developer applies) merges the three `tests` SELECT policies into `tests_select TO authenticated USING (is_active IS TRUE OR is_moderator(auth.uid()))`, which clears the last findings. Rollback: `migrations/rls_consolidate_permissive_policies_rollback.sql`
**Feature:** latency
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-925

**Description:**
Advisor `multiple_permissive_policies` (372 findings): e.g. `users` has six SELECT policies for
`authenticated`. Merging them is a security-sensitive redesign; the app reads through the
service role (ADR-034), so the latency impact today is small. Needs review before any change.

---

## TASK-933: Trim render-blocking fonts and CSS in `base.html`

**Status:** [x] Done 2026-11-11 — first paint −58 to −62% on every logged-in page (phone network, cold), CLS unchanged, walkthrough 16/16 ([[evaluations/first-paint-2026-11-11]])
**Feature:** latency
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
`base.html` blocks first paint on Google Fonts (5 families incl. Noto Sans SC/JP), Bootstrap
CSS and all of Font Awesome. Options: load CJK families only for the matching study language,
subset Font Awesome, self-host with long caching (TASK-928's mechanism). The base scripts
cannot simply be deferred: page inline scripts call `LinguaMetadata` / `authFetch` while
parsing.

---

## TASK-934: Stop late-loading sections from pushing the page down (CLS)

**Status:** [ ] Not Started — needs a layout decision
**Feature:** latency
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Pre-existing layout shift measured 2026-11-11 ([[evaluations/first-paint-2026-11-11]]): on
`/tests` (CLS ≈ 0.29) "Today's Test Load" (`#dailyLoadSection`, `display:none` until
`/api/tests/daily-load` returns) is inserted above "Recommended for You" and pushes everything
down; `/test/<slug>` (≈ 0.35) and `/study-plan` (≈ 0.16) have similar late insertions.
Options: reserve the section's space with a skeleton while loading; render it below the fold;
or load the daily load with the page. Google's "good" threshold is CLS ≤ 0.1.

**Acceptance Criteria:**
- [ ] CLS ≤ 0.1 on `/tests`, `/test/<slug>`, `/study-plan` in `harness/paint_bench.js`.
- [ ] Same-data screenshots unchanged once loading has finished.
