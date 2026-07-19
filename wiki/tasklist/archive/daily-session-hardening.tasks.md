---
title: "Daily Session Hardening — Task Breakdown"
feature: daily-session-hardening
prose_page: ../algorithms/daily-session-implementation-analysis.md
tech_page: ../algorithms/daily-session-implementation-analysis.tech.md
total_tasks: 14
done: 1
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

**Status:** [x] Done (2026-07-19) — code + `phase18_practice_time_seconds.sql` applied to live (8-arg RPC + `_sec` columns verified, backfill clean); `/session` block run to eyeball `practice_completed_acq_min > 0` still owed
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
- [ ] Practice player measures render→submit elapsed ms per exercise and sends it
- [ ] Server accumulates fractional minutes (seconds-granularity) instead of per-attempt `round(ms/60000)`; a 10-minute block of 25 s attempts credits ≈10 min, not 0
- [ ] Absurd values are clamped (e.g. >5 min per attempt → `expected_seconds_p50` fallback); 0/missing ms credits the p50 estimate instead of nothing
- [ ] Weekly state assertions: after a completed practice block, `practice_completed_*_min` > 0

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

**Status:** [ ] Not Started
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
- [ ] No two same-type tests adjacent when another type is available
- [ ] Practice chunks appear mid-session (e.g. positions ⅓ and ⅔), not only at the end
- [ ] Two GETs of `/api/study-session` return identical order (deterministic seed)
- [ ] Resume behavior unchanged: `next_index` still points at first incomplete item

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

**Status:** [ ] Not Started
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
- [ ] At most 1 retry slot per day per language, `slot_type='retry'`, `original_percentage` populated
- [ ] Retry slot bypasses the never-attempted filter but respects the 24h cooldown
- [ ] ELO update on retry uses the ADR-006 damped path (verify `process_test_submission` handles `slot_type`)

**Files to Create / Modify:**
- `migrations/` — `build_daily_session` revision (fold into TASK-702's revision)

**Verification:**
Seed a 50% attempt 2 days old; next daily load contains that test with
`slot_type='retry'`; runner shows it and completes normally.

---

## TASK-705: Make build_daily_session same-day-safe

**Status:** [ ] Not Started
**Feature:** daily-session-hardening
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
`ON CONFLICT DO UPDATE SET completed_test_ids='[]'` wipes progress on any
same-day re-invocation (F6); today only caller-side checks prevent it.

**Acceptance Criteria:**
- [ ] Second same-day call preserves `completed_test_ids` and `completed_blocks`
- [ ] Already-completed test slots are retained in `test_ids`; only incomplete slots are re-resolved
- [ ] SQL unit test covers the double-call scenario

**Files to Create / Modify:**
- `migrations/` — fold into the TASK-702 `build_daily_session` revision

**Verification:**
Call the RPC twice with one completion in between; completion survives.

---

## TASK-706: Advisory lock actually guards the weekly cron

**Status:** [ ] Not Started
**Feature:** daily-session-hardening
**Type:** infra
**Complexity:** S
**Depends On:** none

**Description:**
`_try_advisory_lock`/`_release_advisory_lock` exist but are never called; the
lock RPCs they reference don't exist; every gunicorn worker runs the full
recompute (F7). Idempotent but N× DB load, and the docstrings lie.

**Acceptance Criteria:**
- [ ] `pg_try_advisory_lock_for_study_plan` / unlock RPCs exist in `migrations/`
- [ ] `_run_weekly_plan_recompute` acquires the lock or **skips** (current fallback runs anyway)
- [ ] Dead `irt_try_lock` reference removed

**Files to Create / Modify:**
- `migrations/study_plan_advisory_lock.sql` — the two lock functions
- `services/study_plan_service.py` — wire lock into the cron entry

**Verification:**
Two concurrent invocations: exactly one performs work (log inspection).

---

## TASK-707: Legacy fallback correctness (type labels + ELO band)

**Status:** [ ] Not Started
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
- [ ] Fallback picks carry the test's real type (via `test_skill_ratings` join)
- [ ] ELO band applied to the fallback query, or the dead computation removed
- [ ] Unit test: dictation-only pool → fallback items labeled `dictation`

**Files to Create / Modify:**
- `services/test_service.py` — `_compute_daily_load` step 4

**Verification:**
`pytest tests/ -k daily_load`; manual: user with exhausted recommendations gets
correctly-typed fallback tests in `/session`.

---

## TASK-708: /session discoverability (navbar + entry flow)

**Status:** [ ] Not Started
**Feature:** daily-session-hardening
**Type:** feature
**Complexity:** S
**Depends On:** none

**Description:**
`/session` is reachable only via one button on `/tests` (F10). Add a navbar
entry (all 4 locales) and make it the primary post-language-selection CTA.

**Acceptance Criteria:**
- [ ] Navbar link "Daily Session" with `data-i18n` key present in en/es/zh/ja JSON (all 4 — see the applyToDOM raw-key failure mode)
- [ ] Active-state highlight when `request.endpoint == 'study_session_page'`
- [ ] Language-selection / login landing surfaces the session CTA

**Files to Create / Modify:**
- `templates/base.html` — nav item
- `static/i18n/{en,es,zh,ja}.json` — `common.nav.daily_session`
- `templates/language_selection.html` — CTA (optional, confirm design)

**Verification:**
Each locale renders the label (no raw key strings); nav highlights on `/session`.

---

## TASK-709: Runner UX/a11y hardening

**Status:** [ ] Not Started
**Feature:** daily-session-hardening
**Type:** feature
**Complexity:** S
**Depends On:** none

**Description:**
Error state is a dead end (no retry); progress dots lack ARIA; summary shows
only a count (F14).

**Acceptance Criteria:**
- [ ] Error card has a Retry button re-invoking `loadSession()`
- [ ] Progress region uses `aria-live="polite"`; dots have `aria-label` (type + state)
- [ ] Summary lists per-item results (type, title, done/skipped); skipped items visually distinct

**Files to Create / Modify:**
- `static/js/session/controller.js`, `templates/study_session.html`
- `static/i18n/*.json` — new keys ×4 locales

**Verification:**
Kill the API mid-load → Retry recovers; screen reader announces progress;
summary distinguishes a skipped placeholder item.

---

## TASK-710: Consolidate the duplicated greedy pass

**Status:** [ ] Not Started
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
- [ ] Single selection loop; identical outputs on a fixture matrix (before/after diff)
- [ ] Superseded RPC files moved to `migrations/archive/` per migrations/CLAUDE.md
- [ ] Live DB verified via `pg_get_functiondef` post-apply (F13)

**Files to Create / Modify:**
- `migrations/` — final consolidated `build_daily_session`

**Verification:**
Fixture diff harness (see tech page Testing Strategy) shows identical
`test_ids` + targets across 20 seeded users.

---

## TASK-711: Document the plannable-type boundary

**Status:** [?] Blocked — needs product decision
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
- [ ] Table in study-plans.tech: surface × in-planner? × rationale
- [ ] Open question resolved in daily-session-implementation-analysis frontmatter

---

## TASK-712: Day-boundary timezone decision

**Status:** [?] Blocked — needs product decision
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
- [ ] Decision recorded (ADR if switching); implementation task filed if needed

---

## TASK-713: Wiki truth reconciliation (Phase 13)

**Status:** [ ] Not Started
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
- [ ] TASK-201…220 statuses audited against code and marked Done/adjusted
- [ ] master.md summary counts recomputed
- [ ] pages-overview gains `/session` row (route, template, APIs)
- [ ] A `pages/study-session` page (or feature page) captures the runner design currently only in the out-of-repo plan file

**Verification:**
`lint` operation reports no stale-status contradictions for Phase 13 pages.
