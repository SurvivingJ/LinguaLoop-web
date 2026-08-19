---
title: Daily Session Implementation Analysis — Technical Evidence
type: algorithm-tech
status: complete
prose_page: daily-session-implementation-analysis.md
last_updated: 2026-08-07
dependencies:
  - "build_daily_session RPC (migrations/phase13_build_daily_session_classifier_drill.sql — canonical)"
  - "get_recommended_tests RPC (migrations/add_pitch_accent_to_get_recommended_tests.sql — canonical)"
  - "services/study_plan_service.py, services/test_service.py, routes/study_session.py"
  - "static/js/session/* , templates/study_session.html"
breaking_change_risk: low
---

# Daily Session Implementation Analysis — Technical Evidence

Findings F1–F16, each with evidence and a fix sketch. Severity: C=critical,
H=high, M=medium, L=low. Remediation tasks: [[tasklist/daily-session-hardening.tasks]].

## Architecture Map (as-built)

```
Sun 23:00 UTC cron (app.py:309-316)
  └─ _run_weekly_plan_recompute (study_plan_service.py:532)   [Tier B]
       └─ compute_weekly_plan → weekly_plan_states (target_counts, skill_values,
          practice targets; Thompson bandit + weakness signal in Python)

First request of day: GET /api/study-session (routes/study_session.py:74)
  └─ test_service.get_or_create_daily_load (test_service.py:450)
       ├─ plan path: build_daily_session RPC (phase13_..._classifier_drill.sql)
       │    greedy fill by per-minute value; hydrate via get_recommended_tests;
       │    UPSERT daily_test_loads (+ daily_test_load_items)
       └─ fallback: legacy _compute_daily_load (3 tests, retry slots)

Runner: /session (app.py:452) → study_session.html → controller.js
  └─ player_registry.js → players/{reading_listening,dictation,pinyin,
     pitch_accent,classifier_drill,practice}.js (+ placeholder fallback)

Feedback: submit handlers → apply_attempt_timing_and_progress →
  record_session_progress → weekly_plan_states.completed_counts / practice_*_min
```

## Findings

### F1 (C) — Sunday cron seeds the outgoing week; new week starts unplanned — ✅ RESOLVED (TASK-700, 2026-07-19)
- `study_plan_service.py:542` — `week_start = _monday_of(date.today())`; fired
  Sun 23:00 UTC (`app.py:311`), when `_monday_of(today)` is the Monday **6 days
  ago**. The upcoming week's `weekly_plan_states` row is never created.
- `build_daily_session` returns `E_NOWEEK` (RPC lines 81-88) → `test_service.py:498-504`
  logs and falls back to legacy — silent for the user, all week.
- `apply_study_plan_template` (phase13_apply_study_plan_template.sql) inserts
  only `user_study_plans`; `templates/study_plan.html:324-336` applyTemplate
  does not call `/api/study-plan/recompute`. Cold-start users have no week row
  until the (mistargeted) cron or a manual button press.
- **Fix sketch:** (a) cron computes `_monday_of(today + 1 day)` (or runs Mon
  00:05 for the current week); (b) lazy Tier B: on `E_NOWEEK`,
  `get_or_create_daily_load` calls `compute_weekly_plan(user, lang, this_monday)`
  once, then retries the resolver; (c) template-apply route triggers an
  immediate recompute. (b) alone heals both cold-start and cron drift.

### F2 (C) — Practice completed-minutes never advance — ✅ RESOLVED (TASK-701, 2026-07-19; live-verified 2026-08-07)
- `static/js/session/players/practice.js:162` — every attempt posts
  `time_taken_ms: 0`.
- `practice_session_service.py:262` — `minutes = max(0, round(ms/60_000))`
  per attempt; even genuine 20–40 s attempts round to 0.
- Consequence: `weekly_plan_states.practice_completed_{maint,acq}_min` stay 0 →
  resolver candidate generation (RPC lines 134-150) sees full remaining target
  daily; Tier B carryover (`study_plan_service.py:420-423`) is also wrong.
  `_update_fsrs_for_exercise` receives 0 ms too.
- **Fix sketch:** capture per-exercise elapsed ms in the player (render→submit
  timestamps); server-side, credit fractional minutes accumulated in seconds
  (switch the RPC delta to seconds or numeric minutes), or credit
  `dim_exercise_types.expected_seconds_p50` when client ms is 0/absurd.

### F3 (H) — Silent hydration shortfall — ✅ RESOLVED (TASK-702, 2026-07-19)
- `get_recommended_tests` caps candidates: `WHERE rank_in_type <= 3`
  (add_pitch_accent migration line 96) and excludes all previously-attempted
  tests (`NOT EXISTS test_attempts`, lines 79-84). Dictation excludes
  transcripts > 80 words.
- `build_daily_session` hydration (`LIMIT v_test.count`, RPC line 259) silently
  under-fills when count > available; `used_minutes` / `objective_value`
  still count the dropped slots. Non-ZH `classifier_drill` slots drop by design
  but indistinguishably from bugs. Two prior incidents (pinyin, pitch_accent,
  classifier_drill hydration) were this same failure class.
- **Fix sketch:** raise the rank cap to `<= 10` (or parameterize); have the RPC
  return `requested_counts` vs `hydrated_counts` per skill and log/emit a
  shortfall warning in `test_service`; add an exhausted-pool fallback (nearest
  ELO among attempted tests older than N days, `slot_type='replay'`).

### F4 (H) — No within-session interleaving — ✅ RESOLVED (TASK-703, 2026-07-19)
- RPC line 270: `jsonb_agg(... ORDER BY skill, test_id)` groups same-type
  tests consecutively; `routes/study_session.py:102-126` appends the two
  practice blocks after all tests. The γ-spacing term (RPC lines 159-171)
  penalizes skills attempted in the prior 3 **days** — it never reorders today.
- **Fix sketch:** ordering pass in `routes/study_session.py` (cheapest place):
  round-robin across test types, insert practice chunks at ⅓ and ⅔ positions;
  deterministic seed = (user, load_date) so resume order is stable. Split
  `practice_{acq,maint}` into ≤10-min chunks (`practice_acq_1`, …) — the
  `completed_blocks` jsonb already supports arbitrary block ids, but
  `_PRACTICE_BLOCKS` and the runner need chunk-id awareness.

### F5 (H) — ADR-006 retry slots absent from the plan path — ✅ RESOLVED (TASK-704, 2026-07-19)
- RPC line 268: every hydrated slot is `'slot_type','new'`. Legacy
  `_compute_daily_load` (test_service.py:566-618) still builds retry slots, but
  under a plan the reduced-volatility retry mechanic never fires.
- **Fix sketch:** reserve up to 1 slot in hydration for a sub-70% attempt older
  than 24 h (reuse legacy criteria) with `slot_type='retry'`.

### F6 (H) — Same-day re-invocation wipes completions — ✅ RESOLVED (TASK-705, built 2026-07-20, applied live 2026-08-07)
- RPC lines 292-295: `ON CONFLICT ... DO UPDATE SET completed_test_ids = '[]'`.
  Only caller-side existence checks (test_service.py:469-477) prevent a
  mid-day reset today; any future direct call (admin tool, recompute-triggered
  rebuild, race between two first-requests) clobbers progress.
- **Fix sketch:** preserve `completed_test_ids` on conflict and drop only
  not-yet-completed slots from the rebuilt `test_ids`; or make the RPC a no-op
  when a row for `p_date` already exists unless `p_force`.

### F7 (M) — Weekly recompute unguarded across gunicorn workers — **RESOLVED (TASK-706, 2026-07-20)**
- ~~`_try_advisory_lock` / `_release_advisory_lock` (study_plan_service.py:508-529)
  are **never called**; `_run_weekly_plan_recompute` has no lock despite its
  docstring and `app.py:262-264` claiming advisory-lock safety. The helper also
  references a bogus `irt_try_lock` RPC and swallows the result; the
  study-plan lock RPCs don't exist in `migrations/`.~~
- **Fixed:** `migrations/study_plan_advisory_lock.sql` adds
  `pg_try_advisory_lock_for_study_plan` / `pg_advisory_unlock_for_study_plan`
  (key `1467840848`, applied live). `_run_weekly_plan_recompute` now acquires
  the lock and **early-returns `skipped:True`** if another worker holds it,
  releasing in a `finally`. The dead `irt_try_lock` call and the unused
  `_ADVISORY_LOCK_KEY` constant are gone. Regression:
  `tests/test_weekly_plan_seeding.py::TestWeeklyRecomputeAdvisoryLock`.

### F8 (M) — daily_test_load_items is dead dual bookkeeping — ⚠️ STILL OPEN, no task filed (confirmed 2026-08-07)
- Written and deleted by the RPC (lines 298-303), RLS'd
  (enable_rls_on_user_owned_tables.sql), but no Python reads or updates it;
  completions live solely in `daily_test_loads.completed_test_ids` jsonb
  (`mark_daily_test_complete`, test_service.py:783-812).
- **Fix sketch:** either make it authoritative (flip `is_completed` there;
  derive jsonb) or drop the table + RPC writes. Decide, then document in
  [[database/schema.tech]].

### F9 (M) — Legacy fallback defects (now the de-facto Monday path per F1) — ✅ RESOLVED (TASK-707, 2026-07-20)
- `test_service.py:656-673`: `elo_min`/`elo_max` computed but never applied to
  the fallback query (dead code); `user_elo_after` is not in the selected
  columns (line 569) so `user_elo` is always 1200.
- Line 680: fallback picks hardcode `'test_type': 'listening'` — wrong player
  mounts for non-listening tests and ELO posts to the wrong skill.
- **Fix sketch:** select the test's real primary type (join test_skill_ratings)
  and apply the ELO band filter or delete the pretense.

### F10 (M) — Discoverability — ✅ RESOLVED (TASK-708, 2026-07-20)
- `/session` (app.py:452-455) is reachable only from a button on
  `templates/test_list.html:20`. No navbar entry (`base.html` nav lists
  language/tests/dojo/drill/lab), no `pages-overview` row, no post-login or
  onboarding routing to it.

### F11 (M) — Type-coverage boundary undocumented — ✅ RESOLVED (TASK-711 decision + TASK-714/715 implementation, 2026-08-07)
- Plannable universe = get_recommended_tests target_types (listening, reading,
  dictation, pinyin, pitch_accent) + classifier_drill sentinel. `dim_test_types`
  also contains `listening_lab` and `mystery`; dual_translation (ADR-017
  standalone) and FSRS flashcards live outside the planner. No wiki page states
  which surfaces are deliberately un-planned; template `target_counts` are the
  only implicit registry. Dictation's 80-word transcript cap can starve
  dictation slots for long-transcript corpora.
- **Resolved by product decision (user, 2026-08-07) →
  [[decisions/ADR-021-plannable-surface-boundary]]:** `flashcards` and
  `dual_translation` **join** the planner (implementation TASK-714);
  `listening_lab` and `mystery` are **deliberately outside** — their
  `dim_test_types` rows are a modelling artefact, not scheduling intent.
  Dictation's 80-word cap **scales with tier** (TASK-715). The canonical
  surface × in-planner? × rationale table now lives in
  [[features/study-plans.tech]]. Surfaced while writing it:
  `test_time_estimate` ends in a catch-all `ELSE 5.0`, so any new plannable
  surface not added to that CASE is silently budgeted at 5 min/item.
- **Implemented 2026-08-07 (TASK-714 + TASK-715), applied live.** Both new
  surfaces ride a queue `kind='surface'` rather than new type codes: budgeted by
  the same greedy loop (so they *compete* for minutes rather than adding to
  them), hydrated from their own pools, reported through the TASK-702 shortfall
  maps, and completed via `record_session_progress(p_kind='surface')` with a
  deterministic uuid5. `listening_lab`/`mystery` exclusion is now pinned four
  ways by `tests/test_plannable_surfaces.py`, and the `ELSE 5.0` trap is pinned
  by a test asserting both new surfaces resolve elsewhere *and* that the Python
  and SQL seeds agree. Dictation's cap is per-tier (80→400) with a matching
  tier-aware time estimate (6.0→22.0 min).
- **Two latent defects surfaced during implementation**, both fixed: the stored
  dictation diff was capped at 200 entries (chosen when every passage was ≤80
  words — it would have truncated a T6 attempt mid-passage with no error), and
  `get_word_count_range` fed the prose prompt
  `dim_complexity_tiers.word_count_max`, which is a **vocabulary size** (up to
  25000), not a passage length. The generator was being told to write
  "600-25000 words" at T6 — the reason live EN difficulty-9 transcripts average
  ~777 words. New T5/T6 passages will be materially shorter; existing rows are
  untouched.

### F12 (L) — Duplicated greedy pass — ✅ RESOLVED (TASK-710, 2026-08-07)
- The RPC runs the identical selection loop twice (once for totals, lines
  152-185; a "replay" for `skill_counts`, lines 193-227). Any future edit must
  change both or totals ≠ hydration. Consolidate into one pass that records
  per-skill counts as it selects.
- **Resolved:** the second loop was removed and `skill_counts` is now populated
  in-pass by the single budget loop (`task702_build_daily_session.sql`, applied
  live). Proven output-identical on a 20-scenario rollback-only fixture matrix
  (`g_old` two-loop vs `g_new` one-loop, 0 mismatches) plus an end-to-end rollback
  smoke call. See [[tasklist/daily-session-hardening.tasks]] TASK-710.

### F13 (L) — Migration/live drift risk on build_daily_session — 🟡 MITIGATED, not eliminated (TASK-710, 2026-08-07)
- Two non-archived files define pieces of the pipeline:
  `phase13_build_daily_session.sql` (also holds `test_time_estimate`,
  `week_start_for`) and `phase13_build_daily_session_classifier_drill.sql`
  (canonical for the function). Precedent (`process_test_submission` CR-04
  drift) says verify the live definition via `pg_get_functiondef` before
  trusting repo SQL.

### F14 (L) — Runner UX/a11y hardening — ✅ RESOLVED (TASK-709, 2026-08-07)
- `controller.js` error state has no retry button (dead-end on transient
  failure); progress dots expose only `title` (no `aria-label`/`aria-live`);
  summary screen shows count only (no per-item recap); skipped placeholder
  items are indistinguishable from completed in the summary.
- **Resolved:** `#sessionErrorRetry` → `retryLoad()` (self-guarding, so a second
  failure re-renders the retryable card); `#sessionProgress` gained
  `aria-live="polite"` + `data-i18n-aria`, `#sessionDots` is `role="list"` with a
  per-dot `aria-label` of `"{type} — {state}"`; `showSummary()` renders per-item
  rows with skipped styled by opacity + line-through + amber (not colour alone).
  `escapeHtml()` added — server-supplied titles now flow into both `innerHTML`
  and an attribute context. A latent i18n bug surfaced during verification:
  `test_list.pitch_accent` was missing from **all four** locales, so JA
  pitch-accent items would have announced the raw key; added everywhere.

### F15 (L) — UTC day boundary ignores plan timezone — ✅ RESOLVED (TASK-712 decision + TASK-716 implementation, 2026-08-07)
- `routes/study_session.py:57` and `test_service.py:466` use UTC dates;
  `user_study_plans.timezone` is stored (routes/study_plan.py:247-251) but
  unused. Evening users in UTC+8/+9 (the ZH/JA audience) get day rollover at
  07:00–08:00 local — acceptable, but decide and document.
- **Resolved by product decision (user, 2026-08-07) →
  [[decisions/ADR-022-local-day-boundary]]:** resolve the day boundary **through
  `user_study_plans.timezone`** (UTC fallback when unset) rather than keeping UTC
  or adding a fixed rollover offset. Implementation TASK-716. The ADR records the
  four things that make this the expensive option: `daily_test_loads` uniqueness
  becomes per-user-derived (a timezone edit can move `load_date` backwards onto an
  existing row, which TASK-705's same-day-safe path reads as a re-invocation);
  historical rows keep UTC semantics; the date is currently derived independently
  in two modules and must collapse to one helper; and `week_start_date` is still
  UTC `date_trunc`, so the week edge needs the same treatment or an explicit
  exemption. Invalid timezone strings must fail safe to UTC (cf. ADR-020).
- **Implemented 2026-08-07 (TASK-716), applied live.** All four ADR concerns
  answered:
  1. *One derivation.* `services/day_boundary.py` (+ SQL twin
     `public.plan_local_date`) replaced **three** independent computations, not
     the two the finding named — `build_daily_session`'s `date.today()` default
     was a third, using the *process* timezone.
     `tests/test_day_boundary.py` asserts the route and the service reference
     the same function object, so a re-inlined `datetime.now(utc)` fails.
  2. *Backwards timezone move.* Policy: **serve the existing row, never
     re-solve.** `get_or_create_daily_load`'s existing-row short-circuit means
     TASK-705's same-day-safe path is not reached, so nothing can disturb
     progress. That check is now load-bearing rather than incidental.
  3. *Week edge.* `week_start_date` **moved too**. Verified live that at
     2026-08-09 15:30 UTC a UTC+9 learner is already on Monday 2026-08-10 while
     UTC reports week 2026-08-03 — leaving it would have credited every
     completion in that 9-hour window to a week the resolver no longer read.
     Both anchors are Monday, so only *when* the week flips changed.
  4. *Historical rows.* **No backfill** — the zone a row was written under is
     recorded nowhere, so a backfill would guess. A one-time single-day
     discontinuity at cutover is accepted explicitly.
  Fail-safe holds at every layer: `resolve_zone` (Python), and
  `resolve_plan_timezone` + an `EXCEPTION WHEN OTHERS` in `plan_local_date`
  (SQL). `PUT /api/study-plan` now rejects non-IANA values so no *new* garbage
  is stored.

### F16 (L) — Wiki hygiene — ✅ RESOLVED (TASK-713, 2026-08-07)
- [[tasklist/study-plans.tasks]] shows TASK-201…220 all "Not Started" while the
  code is live; `tasklist/master.md` has no Phase-13/session-runner section;
  [[pages/pages-overview]] lacks `/session`; the runner's design doc is an
  out-of-repo plan file (`~/.claude/plans/we-now-have-the-swirling-haven.md`)
  referenced from code comments.
- **Resolved:** TASK-201–219 flipped to Done after a live-DB probe of every
  table/column/RPC/route leg (TASK-220 was already closed); an audit note records
  that TASK-210's "RPC" title is a misnomer — `compute_weekly_plan` is Python over
  `compute_weekly_plan_load_signals` + `_persist`, with no DB function of that
  name. master.md counts recomputed (Not Started 40 → 28; the old figure disagreed
  with its own tables) and an In-Progress bucket added for TASK-629.
  [[pages/pages-overview]] gained `/session` plus seven other missing live routes,
  and `/exercises` + `/vocab-dojo` — still listed as live despite TASK-220 deleting
  their routes and templates — are now marked RETIRED. The runner design is now
  in-repo at [[pages/study-session]] + [[pages/study-session.tech]], so the
  out-of-repo plan file is no longer load-bearing.

## Testing Strategy (for the remediation work)
- **Unit (SQL):** build_daily_session with (a) no week row, (b) exhausted test
  pool, (c) count > 3 per skill, (d) second same-day call — assert shortfall
  fields, preserved completions.
- **Unit (Python):** get_or_create_daily_load lazy-Tier-B path; legacy fallback
  type labeling; interleave ordering determinism across two calls.
- **E2E (Playwright):** Monday-morning simulation — apply template → first
  /session request → assert plan-driven queue (not legacy 3-test), interleaved
  order, practice minutes advancing after a block.

## Related Pages
- [[algorithms/daily-session-implementation-analysis]] — prose verdicts
- [[tasklist/daily-session-hardening.tasks]] — remediation tasks TASK-700+
- [[features/study-plans.tech]], [[algorithms/study-plan-adaptation.tech]]
- [[decisions/ADR-006-retry-slot-reduced-elo]], [[decisions/ADR-013-global-feature-flag-rollout]]
