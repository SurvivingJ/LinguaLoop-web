---
title: "Latency — Task Breakdown"
feature: latency
prose_page: ../evaluations/latency-2026-11-11.md
tech_page: ../decisions/ADR-042-request-scoped-caching-and-static-asset-caching.md
total_tasks: 9
done: 2
---

# Latency — Task Breakdown

Source: the 2026-11-11 latency audit and fix pass ([[evaluations/latency-2026-11-11]],
[[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]]). The developer asked for
every suggested fix **except** raising gunicorn concurrency (hobby-tier Railway instance).

---

## TASK-925: Stop `resolve_plan_timezone` scanning `pg_timezone_names`

**Status:** [~] Done (repo), awaiting live apply — the Supabase confirmation prompt timed out unanswered on 2026-11-11; nothing was applied
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
- [ ] `resolve_plan_timezone` returns the same value as before for every name in `pg_timezone_names`, for `''`, NULL and garbage.
- [ ] Every `plan_local_date` caller loses its ~55 ms floor (measured in the evaluation).
- [ ] Policy digest after unwrapping equals the pre-migration digest `9de38a5b2b08aef7f7062e70060c543a` (106 policies; digest of `tablename|policyname|cmd|roles|permissive|qual|with_check` ordered by table, policy — unwrap `( SELECT auth.x() AS x)` → `auth.x()` before hashing).
- [ ] Advisor: `duplicate_index` and `auth_rls_initplan` findings gone.

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

**Status:** [~] Done (repo) 2026-11-11 — after-measurement pending
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
- [ ] Warm page loads transfer only the HTML and API responses (after-measurement pending).
- [x] A changed file gets a new URL; unversioned requests still revalidate.

---

## TASK-929: Remove start-up waterfalls in the browser

**Status:** [~] Done (repo) 2026-11-11 — after-measurement and browser walkthrough pending
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
- [ ] Browser walkthrough with the test account shows no visual or functional change (pending).

---

## TASK-930: Assemble the daily session in one RPC

**Status:** [ ] Not Started
**Feature:** latency
**Type:** refactor
**Complexity:** L (1-2d)
**Depends On:** TASK-926

**Description:**
`GET /api/study-session` still makes ~14 sequential round trips (daily load, enrichment,
intake, speed-round check, prestudy planning, governor). Moving the read side into one SQL
function would cut it to 2–3. Needs a design pass: intake writes, prestudy planning lives in
Python (`services/prestudy.py`).

**Verification:** HTTP harness from [[evaluations/latency-2026-11-11]]: ≤ 4 DB calls.

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

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
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
