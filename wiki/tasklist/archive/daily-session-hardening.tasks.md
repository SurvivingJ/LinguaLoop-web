---
title: "Daily Session Hardening — Task Breakdown"
feature: daily-session-hardening
prose_page: ../algorithms/daily-session-implementation-analysis.md
tech_page: ../algorithms/daily-session-implementation-analysis.tech.md
total_tasks: 17
done: 17
---

# Daily Session Hardening — Task Breakdown

Remediates findings F1–F16 from [[algorithms/daily-session-implementation-analysis.tech]].
Sequence: 700 → 701 → 702 (scheduling correctness) unblock everything user-visible;
703–706 are the algorithm-quality tier; the rest are independent.

---

## TASK-700: Fix weekly-plan seeding (lazy Tier B + cron target week)

**Status:** [x] Done (2026-07-19)
**Feature:** daily-session-hardening
**Type:** bug
**Complexity:** M
**Depends On:** none

**Description:**
The Sunday 23:00 UTC cron computes `_monday_of(date.today())` — the *outgoing*
week — so the upcoming week's `weekly_plan_states` row is never created and
`build_daily_session` returns `E_NOWEEK` every Monday, silently degrading all
plan users to the legacy 3-test load (F1). Fix all three legs: lazy compute,
cron target, and template-apply seeding.

**Acceptance Criteria:**
- [x] On `E_NOWEEK`, `get_or_create_daily_load` invokes `compute_weekly_plan(user, lang, monday_of(today))` once, then retries `build_daily_session`; falls back to legacy only if that also fails
- [x] Sunday cron computes the **upcoming** week (`_monday_of(today + 1)`) — or moves to Monday 00:05 UTC for the current week; either way a fresh Monday request finds a week row without lazy compute
- [x] `PUT /api/study-plan` template-only path triggers an immediate `compute_weekly_plan` for the current week after `apply_study_plan_template` succeeds
- [x] Regression test: freeze date to a Monday, apply template Sunday, assert first daily load is plan-driven (queue contains practice blocks)

**Implementation notes (2026-07-19):**
- Leg 1 keys the lazy compute off the `week_start` field the RPC returns in its
  `E_NOWEEK` payload (authoritative), falling back to `_monday_of(date.today())`
  only if absent/malformed. Guarded to the `E_NOWEEK` code, so it fires once per
  absent week, never per request; logs at INFO.
- Leg 2 kept the Sunday 23:00 UTC schedule and switched the target to
  `_monday_of(date.today() + timedelta(days=1))`.
- Leg 3 seeds the current week best-effort after `apply_study_plan_template`;
  a failure still returns the applied template (lazy path recovers it).
- Tests: `tests/test_weekly_plan_seeding.py` (4 cases, all legs). `pytest -k weekly_plan` green.

**Technical Notes:**
Lazy compute must be idempotent-safe (Tier B already UPSERTs deterministically)
and rate-guarded (only when the week row is absent, never on every request).
Log at INFO when lazy Tier B fires — it doubles as telemetry.

**Files to Create / Modify:**
- `services/test_service.py` — E_NOWEEK branch in `get_or_create_daily_load`
- `services/study_plan_service.py` — `_run_weekly_plan_recompute` week target
- `routes/study_plan.py` — post-template-apply recompute

**Verification:**
`pytest tests/ -k weekly_plan`; then live: apply a template on a fresh user and
GET `/api/study-session` — response must have `daily_session_targets`-driven
practice blocks the same day.

---

## TASK-701: Real practice timing → weekly minute counters advance

**Status:** [x] Done (2026-07-19; live verification closed 2026-08-07)
**Feature:** daily-session-hardening
**Type:** bug
**Complexity:** M
**Depends On:** none

**Description:**
`players/practice.js` posts `time_taken_ms: 0` on every attempt and
`record_attempt_with_updates` rounds per-attempt ms to whole minutes, so
`practice_completed_{maint,acq}_min` never move (F2): the resolver re-schedules
the full practice target daily and week-over-week carryover is wrong. FSRS also
receives 0 ms.

**Acceptance Criteria:**
- [x] Practice player measures render→submit elapsed ms per exercise and sends it
- [x] Server accumulates fractional minutes (seconds-granularity) instead of per-attempt `round(ms/60000)`; a 10-minute block of 25 s attempts credits ≈10 min, not 0
- [x] Absurd values are clamped (e.g. >5 min per attempt → `expected_seconds_p50` fallback); 0/missing ms credits the p50 estimate instead of nothing
- [x] Weekly state assertions: after a completed practice block, `practice_completed_*_min` > 0

**Technical Notes:**
Options: change `record_session_progress` to accept `p_delta_seconds int`, or
keep minutes but pass numeric. Prefer seconds with minutes as a derived read.
Same elapsed-ms fix applies to `vocab_dojo.html` if it shares the 0-ms
pattern — check while in there.

**Files to Create / Modify:**
- `static/js/session/players/practice.js` — per-exercise timer
- `services/practice_session_service.py` — accumulation + clamping
- `migrations/` — new `record_session_progress` revision (archive rules apply)

**Verification:**
Run a practice block in `/session`; `SELECT practice_completed_acq_min FROM weekly_plan_states` shows the elapsed minutes.

**Verification closed (2026-08-07, TASK-713 session):** no live browser session was available, so
the owed eyeball check was replaced with the sanctioned **rollback-only** DB equivalent on
`kpfqrjtfxmujzolwsvdq`, which exercises the same server path a real block would.
- **Setup:** no `weekly_plan_states` row existed for the current week (`2026-08-03`) — the latest
  was `2026-07-06` — and the RPC bails quietly (`RETURN true`) without one, which would have made a
  naive probe read as a false pass. Inside the transaction the `2026-07-06` row was moved to the
  current week with `practice_completed_acq_{sec,min}` zeroed.
- **Exercise:** 24 × `record_session_progress(p_kind => 'practice_acq', p_delta_seconds => 25)`
  with distinct `gen_random_uuid()` attempt ids — i.e. the AC's "10-minute block of 25 s attempts".
- **Result:** `before_sec=0, before_min=0 → after_sec=600, after_min=10`, `logged_attempts=24`,
  `practice_completed_acq_min > 0` **true**. Under the old `round(ms/60000)` behavior each 25 s
  attempt rounded to 0, so this is the exact regression the task was filed for.
- **Rollback proven clean:** post-transaction probe returns `current_week_rows = 0` and
  `original 2026-07-06 row = 1` — nothing persisted.
- **AC1** (player timer) verified by code: `state.renderedAt = performance.now()` at
  `static/js/session/players/practice.js:139`, elapsed computed at `:195` and posted as
  `time_taken_ms` at `:175`. **AC3** (clamping) verified in
  `PracticeSessionService._effective_practice_seconds` — `> PRACTICE_ATTEMPT_MAX_SECONDS`
  (5 min) or missing/zero/negative ms both fall back to the clamped `expected_seconds` p50
  estimate, never crediting nothing.

---

## TASK-702: Surface and reduce hydration shortfalls

**Status:** [x] Done (2026-07-19)
**Feature:** daily-session-hardening
**Type:** bug
**Complexity:** M
**Depends On:** none

**Description:**
Budgeted slots silently vanish when `get_recommended_tests` (top-3 per type,
never-attempted-only) can't fill them (F3). Three prior production incidents
(pinyin, pitch_accent, classifier_drill) were this failure class. Make
shortfalls visible and shrink their frequency.

**Acceptance Criteria:**
- [x] `build_daily_session` returns `requested_counts` and `hydrated_counts` per skill; `used_minutes` reflects hydrated (not budgeted) slots
- [x] `test_service` logs WARNING when hydrated < requested for any skill
- [x] `rank_in_type` cap raised (≥ max plausible per-day count per type, suggest 10) — raised to 10
- [x] Exhausted-pool fallback: nearest-ELO previously-attempted test older than N days enters with `slot_type='replay'` (N=7)

**Technical Notes:**
Keep the shortfall fields in `daily_session_targets` jsonb so no schema change
is needed. The replay fallback and TASK-704 retry slots share selection code —
implement together in the RPC.

**Files to Create / Modify:**
- `migrations/` — new `build_daily_session` + `get_recommended_tests` revisions
- `services/test_service.py` — shortfall WARNING

**Verification:**
SQL unit: user with 2 remaining reading tests and target 4 → response shows
`requested=4, hydrated=2` (+2 replay if pool allows); WARNING in app log.

**Completion notes (2026-07-19):**
- Migrations applied live (`kpfqrjtfxmujzolwsvdq`) and mirrored in repo:
  `task702_get_recommended_tests_rank_cap.sql` (cap 3→10),
  `get_replay_tests.sql` (new shared SRF, `p_min_age_days` default 7),
  `task702_build_daily_session.sql`. Superseded files archived
  (`add_pitch_accent_to_get_recommended_tests.sql`,
  `phase13_build_daily_session_classifier_drill.sql`).
- **`hydrated_counts` counts primary (never-attempted / sentinel) fill only** —
  a replay-covered slot is still reported as a shortfall so the WARNING fires and
  ops sees the pool ran dry. `replay_counts` tracks fallback fill separately.
  `used_minutes` = placed slots (new+replay) + practice; `budgeted_minutes` keeps
  the raw budget total.
- **Scope note re ADR-006:** the live `process_test_submission` does NOT
  implement the reduced-volatility retry/replay damping (phase14 dropped it; see
  `migrations/archive/README.md` CR-04 note). `slot_type='replay'` is emitted so
  the damping *can* key off it once re-landed, but no damping runs today. This
  affects **TASK-704**'s criterion "ELO update on retry uses the ADR-006 damped
  path" — that path must be re-landed in `process_test_submission` first.
- Verified live in rollback-only transactions: replay-available →
  `requested={reading:4}, hydrated={reading:2}, replay={reading:2}`,
  slots `[new,new,replay,replay]`, used=budgeted=24; replay-empty →
  `hydrated={reading:2}, replay={}`, 2 slots, **used=12 < budgeted=24**.
- Service WARNING covered by `tests/test_daily_load_shortfall.py` (5 tests).

---

## TASK-703: Interleave the session queue

**Status:** [x] Done (2026-07-19)
**Feature:** daily-session-hardening
**Type:** feature
**Complexity:** M
**Depends On:** TASK-701

**Description:**
Queue is currently all tests grouped by type, then two monolithic practice
blocks (F4). Interleave: round-robin across test types, split practice into
≤10-minute chunks placed between tests, deterministic per (user, load_date) so
resume order is stable.

**Acceptance Criteria:**
- [x] No two same-type tests adjacent when another type is available
- [x] Practice chunks appear mid-session (e.g. positions ⅓ and ⅔), not only at the end
- [x] Two GETs of `/api/study-session` return identical order (deterministic seed)
- [x] Resume behavior unchanged: `next_index` still points at first incomplete item

**Implementation (2026-07-19):**
Pure ordering layer added to `routes/study_session.py`:
`build_session_queue()` composes `_round_robin_tests()` (groups by `test_type`,
seeded group order via `_stable_seed(user_id, load_date)`, deque round-robin →
same-type never adjacent while another type has items) with
`_interleave_practice()` (spreads chunks at `((i+1)·T)//(P+1)` positions). Base
`_PRACTICE_BLOCKS` are expanded by `_build_practice_chunks()`/`_chunk_minutes()`
into `≤10`-min chunks with ids `practice_acq_1`, `practice_maint_1`, …
`complete-block` now validates against `_valid_practice_block_ids(targets)`.
FE unchanged (verified): `controller.js` renders dots off `q.kind`/`is_completed`;
`players/practice.js` forwards `item.minutes` to `/api/practice/session?minutes=`
(route validates 1..180 → small chunk values honored). Covered by
`tests/test_study_session_ordering.py` (20 tests, green).

**Technical Notes:**
Do the ordering in `routes/study_session.py` (Python, cheap to iterate) rather
than the RPC. Chunked practice needs block ids like `practice_acq_1` in
`_PRACTICE_BLOCKS` handling and `completed_blocks` (jsonb already supports it);
controller and practice player take `minutes` per chunk — verify
`/api/practice/session?minutes=` honors small values.

**Files to Create / Modify:**
- `routes/study_session.py` — ordering pass + chunked `_PRACTICE_BLOCKS`
- `static/js/session/controller.js` — no change expected; verify dots/progress
- `tests/` — ordering determinism + adjacency unit tests

**Verification:**
GET `/api/study-session` for a ZH plan user with 4+ tests: types alternate,
practice chunk mid-queue; refresh mid-session — same order, resumes correctly.

---

## TASK-704: Retry slots in the plan path (ADR-006)

**Status:** [x] Done (2026-07-19)
**Feature:** daily-session-hardening
**Type:** feature
**Complexity:** S
**Depends On:** TASK-702

**Description:**
`build_daily_session` emits only `slot_type='new'`; the reduced-volatility
retry mechanic ([[decisions/ADR-006-retry-slot-reduced-elo]]) only runs in the
legacy path (F5). Reserve up to one hydration slot for a <70% attempt older
than 24h.

**Acceptance Criteria:**
- [x] At most 1 retry slot per day per language, `slot_type='retry'`, `original_percentage` populated
- [x] Retry slot bypasses the never-attempted filter but respects the 24h cooldown
- [x] ELO update on retry uses the ADR-006 damped path (verify `process_test_submission` handles `slot_type`)

**Files to Create / Modify:**
- `migrations/task702_build_daily_session.sql` — retry-slot selection folded in
- `migrations/task704_process_test_submission_retry_elo.sql` — **new**; re-lands ADR-006 damping
- `tests/test_daily_load_retry_slot.py` — **new**; pins the retry-slot normalization contract

**Verification:**
Seed a 50% attempt 2 days old; next daily load contains that test with
`slot_type='retry'`; runner shows it and completes normally.

**Completion notes (2026-07-19):**
Scoped "Both A+B now" (user decision): criterion 3 required re-landing the ADR-006
damping the live `process_test_submission` had lost (phase14/CR-04 drift — see
[[process-test-submission-cr04-drift]]). Both applied live (`kpfqrjtfxmujzolwsvdq`)
and mirrored in repo.
- **Part A** `task702_build_daily_session.sql`: before hydration, select the single
  worst sub-70% latest attempt older than 24h (`DISTINCT ON (test_id)` → worst
  `percentage`, oldest first), stamp `slot_type='retry'` + `original_percentage`, and
  **free one budgeted `new` slot of that skill** (`skill_counts` decrement) so
  `used_minutes` stays ~constant (additive +1 only if the skill isn't budgeted today).
  Bypasses the never-attempted filter; 24h cooldown via `created_at < NOW() - INTERVAL '24 hours'`.
- **Part B** `task704_process_test_submission_retry_elo.sql` (**new** canonical definer
  of the 8-arg RPC; partG stays canonical for the QAR column drop): partG live body
  verbatim with the repeat branch rewritten — if the test is in today's
  `daily_test_loads` `slot_type='retry'` for this user+lang AND no reduced-ELO repeat
  recorded today (anti-grind), apply `factor = LEAST(1, GREATEST(0.20, days_since/60) + 0.25·improved)`
  in the live inline-ELO style (user K = 32·furigana·factor, test K = 16·factor), persist
  `elo_reduction_factor`. Off-slot / already-earned repeats keep the 0-ELO path.
- **Verified live (rollback-only)**: seeded a 50% attempt 2 days old for a plan user
  (cloned their weekly state into the current week) → daily load returned exactly one
  `retry` slot `{original_percentage:50.0}`, `requested.listening` 2→1, `used=22<budgeted=26`.
  Damping math (2-day, no improvement): factor **0.20**, user ELO **+2** (was 0), test −1;
  retry-slot detection subquery true. Txn aborted via `RAISE` — no persistence.
  `tests/test_daily_load_retry_slot.py` (3, green; ran directly — ~~pytest wrapper broken in-env~~).
  **Correction (2026-08-07):** the pytest wrapper is **not** broken. `python -m pytest` reports
  "No tests collected" because the suites `import` from `routes`/`services` and collection fails
  without the repo root on `sys.path`; the wrapper hides the `ModuleNotFoundError`. The correct
  invocation is `PYTHONPATH=. python -m pytest tests/ -q` — which runs the whole suite normally
  (verified: 20 passed for the ordering suite, 38 for `-k "daily_load or weekly_plan or
  study_session"`). See [[webapp-pytest-needs-pythonpath]].

---

## TASK-705: Make build_daily_session same-day-safe

**Status:** [x] Done (2026-07-20)
**Feature:** daily-session-hardening
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
`ON CONFLICT DO UPDATE SET completed_test_ids='[]'` wipes progress on any
same-day re-invocation (F6); today only caller-side checks prevent it.

**Acceptance Criteria:**
- [x] Second same-day call preserves `completed_test_ids` and `completed_blocks`
- [x] Already-completed test slots are retained in `test_ids`; only incomplete slots are re-resolved
- [x] SQL unit test covers the double-call scenario

**Files to Create / Modify:**
- `migrations/task702_build_daily_session.sql` — folded in: before rebuilding,
  carry over every slot already completed today (test_id ∈ prior
  `completed_test_ids`) into `chosen_tests` with `is_completed=true`, decrement
  its skill's budgeted count, and stop the `ON CONFLICT` branch resetting
  `completed_test_ids`. Added `NOT IN chosen_tests` guards to the retry pick and
  the get_recommended / classifier_drill hydration so a retained slot is never
  re-inserted. Items mirror rebuilt with per-slot `is_completed`.
- `tests/sql/test_task705_same_day_safe.sql` — new rollback-only double-call SQL test.

**Verification:**
Call the RPC twice with one completion in between; completion survives. Verified
live in a rollback-only transaction (2026-07-20): completed test + practice block
both survive the re-solve, completed slot kept exactly once, incomplete slot
re-resolved, items-mirror `is_completed` retained. **Live apply still owed** — the
CREATE OR REPLACE was blocked by the auto-mode classifier and must be applied by
the user (the rollback-txn verification did NOT persist the function).

---

## TASK-706: Advisory lock actually guards the weekly cron

**Status:** [x] Done (2026-07-20)
**Feature:** daily-session-hardening
**Type:** infra
**Complexity:** S
**Depends On:** none

**Description:**
`_try_advisory_lock`/`_release_advisory_lock` exist but are never called; the
lock RPCs they reference don't exist; every gunicorn worker runs the full
recompute (F7). Idempotent but N× DB load, and the docstrings lie.

**Acceptance Criteria:**
- [x] `pg_try_advisory_lock_for_study_plan` / unlock RPCs exist in `migrations/` (`study_plan_advisory_lock.sql`; applied live 2026-07-20)
- [x] `_run_weekly_plan_recompute` acquires the lock or **skips** (early-return `skipped:True` when not acquired; releases in `finally`)
- [x] Dead `irt_try_lock` reference removed (also dropped the unused `_ADVISORY_LOCK_KEY` constant; key now lives server-side in the RPC)

**Files to Create / Modify:**
- `migrations/study_plan_advisory_lock.sql` — the two lock functions (key `1467840848` = 0x577D7950 'StPP', distinct from the IRT key)
- `services/study_plan_service.py` — wire lock into the cron entry
- `tests/test_weekly_plan_seeding.py` — `TestWeeklyRecomputeAdvisoryLock` (skip-vs-run + release-in-finally)

**Verification:**
Two concurrent invocations: exactly one performs work (log inspection).
Done: live RPC probe returned `took_lock=true, held_in_pg_locks=1, released=true`
(correct key held); the second session gets `false` by `pg_try_advisory_lock`
semantics. Unit tests assert the loser skips (no `db.table` paging, no
`compute_weekly_plan`, no release) and the winner runs then releases. 6/6 pass.

---

## TASK-707: Legacy fallback correctness (type labels + ELO band)

**Status:** [x] Done (2026-07-20)
**Feature:** daily-session-hardening
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
Legacy `_compute_daily_load` fallback query ignores its computed ELO band
(dead `elo_min`/`elo_max`; `user_elo_after` never selected → always 1200) and
hardcodes `test_type='listening'`, mounting the wrong player and rating the
wrong skill (F9). Until TASK-700 lands this is the de-facto Monday path.

**Acceptance Criteria:**
- [x] Fallback picks carry the test's real type (via `test_skill_ratings` join)
- [x] ELO band applied to the fallback query, or the dead computation removed
- [x] Unit test: dictation-only pool → fallback items labeled `dictation`

**Files to Create / Modify:**
- `services/test_service.py` — `_compute_daily_load` step 4

**Verification:**
`pytest tests/ -k daily_load`; manual: user with exhausted recommendations gets
correctly-typed fallback tests in `/session`.

**Resolution (2026-07-20):**
Step 1 attempts query now selects `user_elo_after` (was omitted → band was dead,
always 1000–1400). Step 4 rewritten to read `test_skill_ratings` (not the bare
`tests` table): `select('test_id, elo_rating, dim_test_types(type_code),
tests!inner(id, is_active, language_id)')` scoped by `tests.language_id` +
`tests.is_active`, with the live `gte/lte` ELO band centred on the user's most
recent `user_elo_after`. Each pick carries its real `type_code` (fallback
`'listening'` only if the type embed is missing). New test
`tests/test_daily_load_fallback_type.py` (4 cases): dictation-only pool → items
labeled `dictation`; queries `test_skill_ratings` not `tests`; default band
[1000,1400] when unrated; band shifts to [1300,1700] for `user_elo_after=1500`
(proves the column is now read). `pytest tests/ -k daily_load` → 12 passed.

---

## TASK-708: /session discoverability (navbar + entry flow)

**Status:** [x] Done (2026-07-20)
**Feature:** daily-session-hardening
**Type:** feature
**Complexity:** S
**Depends On:** none

**Description:**
`/session` is reachable only via one button on `/tests` (F10). Add a navbar
entry (all 4 locales) and make it the primary post-language-selection CTA.

**Acceptance Criteria:**
- [x] Navbar link "Daily Session" with `data-i18n` key present in en/es/zh/ja JSON (all 4 — see the applyToDOM raw-key failure mode)
- [x] Active-state highlight when `request.endpoint == 'study_session_page'`
- [x] Language-selection / login landing surfaces the session CTA

**Files to Create / Modify:**
- `templates/base.html` — nav item
- `static/i18n/{en,es,zh,ja}.json` — `common.nav.daily_session`
- `templates/language_selection.html` — CTA (optional, confirm design)

**Verification:**
Each locale renders the label (no raw key strings); nav highlights on `/session`.

**Implementation notes (2026-07-20):**
- `common.nav.daily_session` added to all 4 locale JSONs (en "Daily Session",
  es "Sesión diaria", zh "每日训练", ja "デイリーセッション"), slotted
  alphabetically between `classifier_drill` and `exercises`.
- `templates/base.html`: "Daily Session" placed **first** in both the desktop
  `d-md-flex` nav and the mobile dropdown, with
  `{% if request.endpoint == 'study_session_page' %}active{% endif %}`.
- `templates/language_selection.html`: post-selection CTA design chosen by user
  = **primary → session, tests secondary**. Primary button relabelled
  (`lang_select.start_session`) and repointed to `study_session_page`; new muted
  secondary link `lang_select.browse_tests` → `tests`, disabled (pointer-events
  none / opacity .5) until a language is picked. Both persist `selectedLanguageId`
  before navigating. New keys `lang_select.start_session` +
  `lang_select.browse_tests` added to all 4 locales.
- Login landing: navbar entry now surfaces `/session` on every authenticated
  page including the post-login landing, so no separate login-page change made.

---

## TASK-709: Runner UX/a11y hardening

**Status:** [x] Done (2026-08-07)
**Feature:** daily-session-hardening
**Type:** feature
**Complexity:** S
**Depends On:** none

**Description:**
Error state is a dead end (no retry); progress dots lack ARIA; summary shows
only a count (F14).

**Acceptance Criteria:**
- [x] Error card has a Retry button re-invoking `loadSession()`
- [x] Progress region uses `aria-live="polite"`; dots have `aria-label` (type + state)
- [x] Summary lists per-item results (type, title, done/skipped); skipped items visually distinct

**Files to Create / Modify:**
- `static/js/session/controller.js`, `templates/study_session.html`
- `static/i18n/*.json` — new keys ×4 locales

**Verification:**
Kill the API mid-load → Retry recovers; screen reader announces progress;
summary distinguishes a skipped placeholder item.

**Implementation notes (2026-08-07):**
- **Retry (AC1).** `templates/study_session.html` — `#sessionError` gained a
  `#sessionErrorRetry` button (`data-i18n="session.retry"`). `controller.js`
  `showError()` binds it to the new `retryLoad()`, which hides the error card,
  re-shows `#sessionLoading`, and re-invokes `loadSession()`. `retryLoad()` wraps the
  call in its own try/catch so a *second* failure re-renders the still-retryable error
  card rather than throwing into an unhandled rejection and leaving a blank page.
- **Progress a11y (AC2).** `#sessionProgress` carries `aria-live="polite"` +
  `data-i18n-aria="session.progress_label"`; `#sessionDots` is `role="list"` and each
  dot is `role="listitem"` with an `aria-label` of `"{type} — {state}"` built from
  `itemTypeLabel()` (localized test type, or "Practice") and `dotStateLabel()`
  (Done / Skipped / In progress / Not started). `data-i18n-aria` was confirmed to be a
  real supported attribute in `static/js/i18n-manager.js:184-187`, not an invention.
- **Summary (AC3).** `showSummary()` now renders a `<ul class="session-results">` of
  per-item rows (icon + title + type + state) beneath the `done/total` count. Skipped
  rows are visually distinct three ways in `study_session.html` CSS — `opacity .65`,
  `line-through` on the title, and amber (`--warning`) icon/state vs green
  (`--success`) for done — so the distinction does not rely on colour alone.
- **Injection safety.** Item titles are server-supplied and were being interpolated into
  `innerHTML` (summary rows) and into an `aria-label` attribute (dots). Added
  `escapeHtml()` and routed every interpolated label through it.
- **i18n (the gotcha).** All 9 new keys — `session.retry`, `session.progress_label`,
  `session.dot_label`, `session.results_title`, `session.item_done`,
  `session.item_skipped`, `session.item_current`, `session.item_pending`,
  `session.practice_heading` — are present and genuinely localized in **all four**
  locales (verified by script, not by eye).
- **Latent bug found and fixed while verifying.** `itemTypeLabel()` resolves
  `T('test_list.' + tt)`, but **`test_list.pitch_accent` did not exist in any of the four
  locale files** — only `test_preview.pitch_accent` did. Every JA pitch-accent item would
  therefore have announced and displayed the raw key string `test_list.pitch_accent` in
  its dot `aria-label` and summary row. Added to all 4 locales, reusing each locale's
  existing `test_preview.pitch_accent` wording (en "Pitch Accent" / es "Acento tonal" /
  zh "日语音高" / ja "アクセント"). All four files re-validated with `json.load` (542 keys each).
  This is the same applyToDOM raw-key failure mode the task's own AC calls out — it was
  live for the *type* labels, not just the new keys.
- **Not covered:** no automated a11y test exists for this surface; the screen-reader
  announcement itself was verified structurally (ARIA attributes present and populated),
  not with an actual assistive-technology run.

---

## TASK-710: Consolidate the duplicated greedy pass

**Status:** [x] Done (2026-08-07, applied live kpfqrjtfxmujzolwsvdq)
**Feature:** daily-session-hardening
**Type:** refactor
**Complexity:** S
**Depends On:** TASK-702, TASK-704, TASK-705

**Description:**
`build_daily_session` runs the identical selection loop twice (totals, then a
"replay" for `skill_counts`) — any future edit must change both (F12). Merge
into one pass recording per-skill counts as it selects. Do this after the
functional revisions land so there's one final RPC file.

**Acceptance Criteria:**
- [x] Single selection loop; identical outputs on a fixture matrix (before/after diff)
- [x] Superseded RPC files moved to `migrations/archive/` per migrations/CLAUDE.md
- [x] Live DB verified via `pg_get_functiondef` post-apply (F13)

**Files to Create / Modify:**
- `migrations/` — final consolidated `build_daily_session`

**Verification:**
Fixture diff harness (see tech page Testing Strategy) shows identical
`test_ids` + targets across 20 seeded users.

**Resolution (2026-08-07):**
The second greedy loop (parallel `v_replay_used` / `v_replay_skills` accumulators
that only populated `pg_temp.skill_counts`) was removed; `skill_counts` is now
created before the single budget loop and the `INSERT … ON CONFLICT DO UPDATE`
runs inline in the test-kind branch. `task702_build_daily_session.sql` is the one
final RPC file (edited in place; header now `TASK-702/704/705/710`).
- **AC1 fixture matrix:** 20-scenario rollback-only harness on Supabase compared the
  old two-loop `g_old()` vs new one-loop `g_new()` over varied budgets, spacing-cost
  `CONTINUE`s, `pmv` ties and interleaved practice slots — **0 mismatches** on
  `used`/`objective`/`skills_today`/`counts`. Plus an end-to-end rollback smoke call
  on a cloned current-week plan (5 test_ids; single-pass counts drove hydration +
  shortfall correctly).
- **AC2 archiving:** no file to archive. The only other non-archived definer,
  `phase13_build_daily_session.sql`, is a multi-object file and the **sole repo
  record** of `test_time_estimate` + `week_start_for`, so migrations/CLAUDE.md
  rule #4 says keep it despite its stale `build_daily_session`. No new superseded
  file was created (edit-in-place).
- **AC3 live verify:** deployed via `apply_migration task710_build_daily_session_single_pass`;
  `pg_get_functiondef` confirms a single `FOR v_cand IN` loop, `v_replay_used` gone,
  and the 710 in-pass marker present. **Note:** this apply also landed TASK-705
  (was live-owed) since the repo file bundles it — done at the user's explicit
  direction (705+710 together). Resolves finding **F12** (and F13 drift-check).

---

## TASK-711: Document the plannable-type boundary

**Status:** [x] Done (2026-08-07) — decision taken by the user, ADR filed
**Feature:** daily-session-hardening
**Type:** docs
**Complexity:** XS
**Depends On:** none

**Description:**
No page states which surfaces are deliberately outside the daily planner
(listening_lab, mystery, dual_translation, flashcards) (F11). Decide intent per
surface, then record it in [[features/study-plans.tech]] + an ADR if any is to
join the planner. Also decide whether dictation's 80-word transcript cap should
scale with tier.

**Acceptance Criteria:**
- [x] Table in study-plans.tech: surface × in-planner? × rationale
- [x] Open question resolved in daily-session-implementation-analysis frontmatter

**Decision (2026-08-07, user):**
- **`flashcards` and `dual_translation` JOIN the planner**; **`listening_lab` and
  `mystery` stay deliberately outside** (long-form/exploratory — a minute budget
  fights their design).
- **Dictation's 80-word cap SCALES with tier.**
- Recorded in [[decisions/ADR-021-plannable-surface-boundary]] (accepted) with the
  full surface × in-planner? × rationale table, mirrored into
  [[features/study-plans.tech]].
- **Gotcha surfaced while writing it:** `test_time_estimate(p_skill text)` COALESCEs
  `dim_test_types.expected_minutes_p50` — **NULL for all 12 type codes** — onto
  hardcoded constants with a catch-all **`ELSE 5.0`**. A new plannable surface that
  isn't added to that CASE gets budgeted at 5 min/item **with no error**. Same silent
  -wrong-answer shape as F3. Called out in the ADR and in TASK-714's AC.
- Implementation filed as **TASK-714** (flashcards + DT as plannable surfaces) and
  **TASK-715** (tier-scaled dictation cap). This task covered the decision + docs only.

---

## TASK-712: Day-boundary timezone decision

**Status:** [x] Done (2026-08-07) — decision taken by the user, ADR filed
**Feature:** daily-session-hardening
**Type:** docs
**Complexity:** XS
**Depends On:** none

**Description:**
Daily loads roll over at UTC midnight = 07:00–09:00 for the ZH/JA audience;
`user_study_plans.timezone` is stored but unused (F15). Decide: keep UTC
(document it) or resolve `_today_iso()` through the plan timezone (touches
`daily_test_loads` uniqueness semantics — nontrivial).

**Acceptance Criteria:**
- [x] Decision recorded (ADR if switching); implementation task filed if needed

**Decision (2026-08-07, user): resolve through the plan timezone** — the expensive
option, chosen over keeping UTC and over the configurable-offset middle ground.
Recorded in [[decisions/ADR-022-local-day-boundary]] (accepted), which spells out the
four consequences that make this nontrivial: the `(user, language, load_date)`
uniqueness key becomes *per-user*-derived (a timezone edit can move `load_date`
backwards into an existing row, which TASK-705's same-day-safe path would treat as a
re-invocation); historical rows carry un-reinterpretable UTC semantics; the date is
currently derived independently in `routes/study_session.py` **and**
`services/test_service.py`, so it must collapse to one shared helper or the two will
produce different "today"s for the same request; and `weekly_plan_states.week_start_date`
is still UTC `date_trunc`, so the week edge needs the same treatment or an explicit
exemption. Implementation filed as **TASK-716**. This task covered the decision only —
**no code was changed**.

---

## TASK-713: Wiki truth reconciliation (Phase 13)

**Status:** [x] Done (2026-08-07)
**Feature:** daily-session-hardening
**Type:** docs
**Complexity:** S
**Depends On:** none

**Description:**
The wiki lags the shipped code (F16): study-plans.tasks TASK-201…220 all show
"Not Started" though live; master.md lacks the session-runner work;
pages-overview lacks `/session`; the runner's design plan lives outside the
repo.

**Acceptance Criteria:**
- [x] TASK-201…220 statuses audited against code and marked Done/adjusted
- [x] master.md summary counts recomputed
- [x] pages-overview gains `/session` row (route, template, APIs)
- [x] A `pages/study-session` page (or feature page) captures the runner design currently only in the out-of-repo plan file

**Verification:**
`lint` operation reports no stale-status contradictions for Phase 13 pages.

**Resolution (2026-08-07):**
- **AC1 — TASK-201…219 audited against the live DB, not just the code.** Probed
  `kpfqrjtfxmujzolwsvdq` directly: `test_attempts.started_at`/`duration_ms` (2 cols),
  `daily_test_loads.daily_session_targets`, `dim_test_types.expected_minutes_p50`,
  `dim_study_plan_templates` (9 seed rows), `dim_study_goals`, `user_study_plans`,
  `weekly_plan_states` all present; RPCs `apply_study_plan_template`,
  `record_session_progress` (8-arg), `build_daily_session` all present; Python/route/cron
  legs (`weakness`/`value`/`bandit_score`, both submit paths wired, `build_daily_session`
  wired into `get_or_create_daily_load`, `study_plan_weekly_recompute` in `app.py:301`,
  4 `/api/study-plan` endpoints, `templates/study_plan.html`,
  `phase13_wipe_user_state_for_launch.sql`, `Config.STUDY_PLAN_ENABLED` default `True`)
  all confirmed. All 19 flipped to Done. **One discrepancy found and recorded, not
  papered over:** TASK-210 is titled "RPC `compute_weekly_plan`" but no such database
  function exists (`pg_proc` → 0 rows); it is `StudyPlanService.compute_weekly_plan` in
  Python over two real RPCs (`compute_weekly_plan_load_signals`,
  `compute_weekly_plan_persist`). The task Description already said "Implement Python…",
  so only the title misled — an audit note now sits on TASK-210 so a future 0-row probe
  isn't misread as a missing object. TASK-220 was already Done (2026-07-14).
- **AC2 — counts recomputed.** The previous "Not Started 40" disagreed with master.md's
  own tables. Recounted from the `[ ]` rows: 23 (ExGen v2) + 5 (Evidence-First) + 0
  (Daily Session) = **28**; Blocked `[?]` = 5; added an **In Progress `[~]` = 1** row for
  TASK-629, which had no bucket at all. Done 102 → **104** (TASK-709, TASK-713). The
  TASK-201–219 flip deliberately did **not** move the Done total — the 2026-07-13 audit
  had already counted them.
- **AC3 — `/session` row added** to [[pages/pages-overview]] with route, template and both
  APIs. While there, three further contradictions were fixed: `/exercises` and
  `/vocab-dojo` were still listed as live pages although **TASK-220 retired both routes
  and deleted their templates** on 2026-07-14 (confirmed: neither `exercises.html` nor
  `vocab_dojo.html` exists) — both rows now marked RETIRED with their 302 targets; and
  seven live routes were missing entirely (`/study-plan`, `/test/<slug>/pitch-accent`,
  `/test/<slug>/dictation`, `/classifier-drill`, `/dual-translation`,
  `/dual-translation/profile`, `/listening-lab`), now added.
- **AC4 — [[pages/study-session]] + [[pages/study-session.tech]] created**, capturing the
  runner design that previously lived only in the out-of-repo plan file
  (`we-now-have-the-swirling-haven.md`): the queue-composition algorithm (`_stable_seed`
  sha256 → `_round_robin_tests` deque drain → `_build_practice_chunks` ≤10 min →
  `_interleave_practice` at `((i+1)·T)//(P+1)`), both endpoint contracts, the controller
  state machine + re-entrancy latch, the `res.ok` trap in `authFetch`, the a11y contract,
  and the 4 architectural decisions. Both registered in [[index]] (Pages: 95 → 97).

---

## TASK-714: Make `flashcards` and `dual_translation` plannable surfaces

**Status:** [x] Done — 2026-08-07, applied live
**Feature:** daily-session-hardening
**Type:** feature
**Complexity:** L
**Depends On:** TASK-711 (done — decision)

**Description:**
Implements [[decisions/ADR-021-plannable-surface-boundary]]. Bring FSRS flashcard
reviews and Dual Translation into the weekly/daily budget so the plan stops
under-counting real study time. Neither is a `dim_test_types` row today, and neither
resolves to an ELO-rated `tests` row, so this needs a plannable-*kind* concept rather
than two new type codes bolted onto the test path.

**Acceptance Criteria:**
- [x] `target_counts` (or a sibling structure) can express flashcards + DT budgets —
      both are ordinary `target_counts` keys; the resolver splits candidate rows into
      `kind='test'` vs `kind='surface'` so they compete for the same minutes but
      hydrate from their own pools. Seeded into all 9 templates
      (`task714_seed_surface_budgets.sql`): flashcards 7/wk, DT 2/3/4 by plan size
- [x] `build_daily_session` emits queue items for both, and `/api/study-session`
      returns them with a `kind` the runner's `player_registry` can mount —
      `daily_session_targets.surface_counts` drives `_build_surface_items`; new
      `players/flashcards.js` + `players/dual_translation.js` registered under
      `KIND_PLAYERS`
- [x] **Time estimates are seeded explicitly, not defaulted** — flashcards 7.0,
      dual_translation 12.0 in both `Config.TEST_TYPE_MINUTES` and the SQL
      `test_time_estimate` CASE. `tests/test_plannable_surfaces.py` asserts neither
      reaches `ELSE 5.0` *and* that the Python and SQL seeds match
- [x] Completion signal reaches `record_session_progress` for both — `p_kind='surface'`
      added; `POST /complete-block` calls it with a deterministic uuid5 so retries
      dedupe. Verified live: `completed_counts` → `{"flashcards":1,"dual_translation":1}`,
      second call returns `false` without double-counting
- [x] `listening_lab` and `mystery` remain **un**scheduled — pinned four ways in
      `tests/test_plannable_surfaces.py`: absent from `PLANNABLE_SURFACE_SKILLS`,
      from `Config.TEST_TYPE_MINUTES`, from the resolver's surface list, and from the
      template seed
- [x] Shortfall telemetry (TASK-702) covers the new kinds — surfaces join
      `requested_counts`/`hydrated_counts`, clamped to their real pools, so the
      existing `_log_hydration_shortfalls` WARNING fires unchanged. Verified live:
      5 flashcard blocks budgeted, 3 hydrated from 32 due cards → shortfall reported

**Technical Notes:**
`flashcards`/`dual_translation` are not in `dim_test_types`; `listening_lab` and
`mystery` *are* (modelling artefacts — see the ADR). Prefer widening the queue item
`kind` union (`test` | `practice` | …) over pretending these are tests. The runner
already dispatches on `item.kind` via `player_registry`, and both surfaces have
existing players/routes to reuse.

**Files to Create / Modify:**
- `migrations/` — new `build_daily_session` revision (archive rules apply)
- `routes/study_session.py` — queue composition for the new kinds
- `services/study_plan_service.py` — budget allocation
- `static/js/session/player_registry.js` + a DT/flashcards session player

**Verification:**
Seed a plan budgeting both; GET `/api/study-session` returns mountable items for each;
complete one of each and assert the weekly counters moved.

---

## TASK-715: Tier-scaled dictation transcript cap

**Status:** [x] Done — 2026-08-07, applied live
**Feature:** daily-session-hardening
**Type:** feature
**Complexity:** M
**Depends On:** TASK-711 (done — decision)

**Description:**
Implements the second decision in [[decisions/ADR-021-plannable-surface-boundary]]:
dictation's flat 80-word transcript cap scales with difficulty tier instead of staying
constant across all levels.

**Acceptance Criteria:**
- [x] Cap is a per-tier value, not a constant; generation respects it — new
      `public.dictation_max_words(difficulty)` (T1 80 · T2 120 · T3 160 · T4 220 ·
      T5 300 · T6 400) replaces the flat constant in `get_recommended_tests`,
      mirrored in `services/dictation/cap.py`. Generation respects it because
      `PASSAGE_WORD_RANGE`'s ceiling **is** the tier cap — dictation has no content
      of its own, it reuses the same `tests` rows
- [x] `test_time_estimate('dictation')` is **no longer a single scalar** — new 2-arg
      overload returns `2.0 + cap/20`: 6.0 at T1 (identical to the old scalar, so
      beginners see no change) rising to 22.0 at T6. The resolver uses the learner's
      *expected* tier when budgeting and the placed test's *actual* tier when
      accounting, so both ends are honest. Verified live across difficulty 1–9
- [x] Existing dictation tests are unaffected (no regeneration implied) — every
      per-tier cap is `>=` the old flat 80, so the eligible set only grows and
      nothing that qualifies today stops qualifying. A NULL/uncalibrated difficulty
      falls back to exactly 80. Pinned by test
- [x] Grader/tokenizer handle the longest tier without truncation surprises — found
      and fixed a real one: `routes/tests.py` capped the **stored** diff at 200
      entries, chosen when every dictation was ≤80 words. At T6's 400 canonical
      tokens that silently truncated mid-passage. Now derived from the largest tier
      cap with headroom for `insert` ops; a 400-token round-trip is asserted

**Technical Notes:**
See [[features/dictation.tech]] and [[decisions/ADR-003-age-tiers]] for the tier
vocabulary. The time-estimate change is the part that couples back into the planner —
do not ship the cap change without it.

**Files to Create / Modify:**
- `services/dictation/` — cap resolution
- generation prompts/config carrying `max_words`
- `migrations/` — `test_time_estimate` revision if the estimate becomes tier-aware

**Verification:**
Generate dictation tests at the lowest and highest tiers; assert transcript lengths
differ per the tier table and the budgeted minutes track actual elapsed time.

---

## TASK-716: Local-day boundary — resolve the daily load through the plan timezone

**Status:** [x] Done — 2026-08-07, applied live
**Feature:** daily-session-hardening
**Type:** bug
**Complexity:** L
**Depends On:** TASK-712 (done — decision)

**Description:**
Implements [[decisions/ADR-022-local-day-boundary]]. The daily load currently rolls
over at UTC midnight — 07:00–09:00 local for the ZH/JA audience — while
`user_study_plans.timezone` is stored and never read. Resolve "today" through the plan
timezone, falling back to UTC when unset.

**Acceptance Criteria:**
- [x] **One** shared helper derives the local date — new `services/day_boundary.py`.
      `routes/study_session.py::_today_iso()` now delegates to it and
      `services/test_service.py` calls it in both `get_or_create_daily_load` and
      `mark_daily_test_complete`. A third derivation was also removed:
      `StudyPlanService.build_daily_session` defaulted to `date.today()` (the
      *process* timezone). `tests/test_day_boundary.py` asserts both call sites
      reference the same function object, so a re-inlined `datetime.now(utc)` fails
      the build. SQL twin `public.plan_local_date` covers RPC bodies with no Python
      caller
- [x] An invalid / unknown timezone string **fails safe to UTC**, never raises —
      `resolve_zone` catches everything and returns UTC; SQL `resolve_plan_timezone`
      validates against `pg_timezone_names` and `plan_local_date` has an
      `EXCEPTION WHEN OTHERS` fallback. Parametrised over `None`, `''`, `'Not/AZone'`,
      `'es'` (a UI locale — the exact value V1 validation would have accepted),
      `'+09:00'`, and a non-string. Route validation now rejects new bad values
- [x] Defined policy for a backwards `load_date` move — **serve the existing row, do
      not re-solve.** `get_or_create_daily_load` already short-circuits on an existing
      row, so `build_daily_session` is never re-invoked and TASK-705's same-day-safe
      path is not exercised; nothing can disturb progress. A forward move simply
      starts a new date. The guard is the caller's existing-row check, which is now
      load-bearing rather than incidental — documented in both the migration header
      and at the call site
- [x] Explicit decision on `weekly_plan_states.week_start_date` — **moved it too.**
      Leaving it on UTC would create a new inconsistency at the week edge: verified
      live that at 2026-08-09 15:30 UTC a UTC+9 learner is already on Monday
      2026-08-10 (week `2026-08-10`) while UTC says week `2026-08-03`. Every
      completion in that 9-hour window would have credited a week the resolver was no
      longer reading — silent and self-cancelling. `record_session_progress` now
      derives its week from `plan_local_date`. Both anchors are Monday, so only
      *when* the week flips changed, never *which weekday*
- [x] Cutover position stated — **accept a one-time discontinuity; no backfill.**
      The timezone a learner was in when a historical row was written is recorded
      nowhere, so a backfill would have to guess it. At cutover an eastward learner
      may see one date already having a row (served as-is) or one date without one
      (freshly solved). Both are single-day effects on a day-scoped table. Written
      into the migration header, not left implicit
- [x] Tests: a UTC+9 learner at 22:00 local gets *their* date, not tomorrow's —
      `tests/test_day_boundary.py`, 30 cases. Also confirmed against the live DB:
      Tokyo → 2026-08-08, UTC → 2026-08-07 at the same instant, invalid zone → UTC

**Technical Notes:**
`daily_test_loads` uniqueness `(user_id, language_id, load_date)` is unchanged in shape
but its derivation becomes per-user. This is the riskiest part — the ADR's Consequences
section is the checklist.

**Files to Create / Modify:**
- `routes/study_session.py`, `services/test_service.py` — shared local-date helper
- `routes/study_plan.py` — tighten timezone validation to IANA zones
- `migrations/` — only if `week_start_date` semantics move

**Verification:**
Freeze the clock at 15:30 UTC and assert a UTC+9 plan resolves to the *next* local date
while a UTC plan resolves to the current one; assert an invalid timezone yields the UTC
date rather than an exception.
