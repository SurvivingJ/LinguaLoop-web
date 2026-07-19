---
title: Daily Session Implementation Analysis — Technical Evidence
type: algorithm-tech
status: complete
prose_page: daily-session-implementation-analysis.md
last_updated: 2026-07-05
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

### F1 (C) — Sunday cron seeds the outgoing week; new week starts unplanned
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

### F2 (C) — Practice completed-minutes never advance
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

### F3 (H) — Silent hydration shortfall
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

### F4 (H) — No within-session interleaving
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

### F5 (H) — ADR-006 retry slots absent from the plan path
- RPC line 268: every hydrated slot is `'slot_type','new'`. Legacy
  `_compute_daily_load` (test_service.py:566-618) still builds retry slots, but
  under a plan the reduced-volatility retry mechanic never fires.
- **Fix sketch:** reserve up to 1 slot in hydration for a sub-70% attempt older
  than 24 h (reuse legacy criteria) with `slot_type='retry'`.

### F6 (H) — Same-day re-invocation wipes completions
- RPC lines 292-295: `ON CONFLICT ... DO UPDATE SET completed_test_ids = '[]'`.
  Only caller-side existence checks (test_service.py:469-477) prevent a
  mid-day reset today; any future direct call (admin tool, recompute-triggered
  rebuild, race between two first-requests) clobbers progress.
- **Fix sketch:** preserve `completed_test_ids` on conflict and drop only
  not-yet-completed slots from the rebuilt `test_ids`; or make the RPC a no-op
  when a row for `p_date` already exists unless `p_force`.

### F7 (M) — Weekly recompute unguarded across gunicorn workers
- `_try_advisory_lock` / `_release_advisory_lock` (study_plan_service.py:508-529)
  are **never called**; `_run_weekly_plan_recompute` has no lock despite its
  docstring and `app.py:262-264` claiming advisory-lock safety. The helper also
  references a bogus `irt_try_lock` RPC and swallows the result; the
  study-plan lock RPCs don't exist in `migrations/`.
- **Fix sketch:** create the two lock RPCs, wire the lock into
  `_run_weekly_plan_recompute`, and fix the fallback to *skip* (not run) when
  the lock RPC exists but isn't acquired.

### F8 (M) — daily_test_load_items is dead dual bookkeeping
- Written and deleted by the RPC (lines 298-303), RLS'd
  (enable_rls_on_user_owned_tables.sql), but no Python reads or updates it;
  completions live solely in `daily_test_loads.completed_test_ids` jsonb
  (`mark_daily_test_complete`, test_service.py:783-812).
- **Fix sketch:** either make it authoritative (flip `is_completed` there;
  derive jsonb) or drop the table + RPC writes. Decide, then document in
  [[database/schema.tech]].

### F9 (M) — Legacy fallback defects (now the de-facto Monday path per F1)
- `test_service.py:656-673`: `elo_min`/`elo_max` computed but never applied to
  the fallback query (dead code); `user_elo_after` is not in the selected
  columns (line 569) so `user_elo` is always 1200.
- Line 680: fallback picks hardcode `'test_type': 'listening'` — wrong player
  mounts for non-listening tests and ELO posts to the wrong skill.
- **Fix sketch:** select the test's real primary type (join test_skill_ratings)
  and apply the ELO band filter or delete the pretense.

### F10 (M) — Discoverability
- `/session` (app.py:452-455) is reachable only from a button on
  `templates/test_list.html:20`. No navbar entry (`base.html` nav lists
  language/tests/dojo/drill/lab), no `pages-overview` row, no post-login or
  onboarding routing to it.

### F11 (M) — Type-coverage boundary undocumented
- Plannable universe = get_recommended_tests target_types (listening, reading,
  dictation, pinyin, pitch_accent) + classifier_drill sentinel. `dim_test_types`
  also contains `listening_lab` and `mystery`; dual_translation (ADR-017
  standalone) and FSRS flashcards live outside the planner. No wiki page states
  which surfaces are deliberately un-planned; template `target_counts` are the
  only implicit registry. Dictation's 80-word transcript cap can starve
  dictation slots for long-transcript corpora.

### F12 (L) — Duplicated greedy pass
- The RPC runs the identical selection loop twice (once for totals, lines
  152-185; a "replay" for `skill_counts`, lines 193-227). Any future edit must
  change both or totals ≠ hydration. Consolidate into one pass that records
  per-skill counts as it selects.

### F13 (L) — Migration/live drift risk on build_daily_session
- Two non-archived files define pieces of the pipeline:
  `phase13_build_daily_session.sql` (also holds `test_time_estimate`,
  `week_start_for`) and `phase13_build_daily_session_classifier_drill.sql`
  (canonical for the function). Precedent (`process_test_submission` CR-04
  drift) says verify the live definition via `pg_get_functiondef` before
  trusting repo SQL.

### F14 (L) — Runner UX/a11y hardening
- `controller.js` error state has no retry button (dead-end on transient
  failure); progress dots expose only `title` (no `aria-label`/`aria-live`);
  summary screen shows count only (no per-item recap); skipped placeholder
  items are indistinguishable from completed in the summary.

### F15 (L) — UTC day boundary ignores plan timezone
- `routes/study_session.py:57` and `test_service.py:466` use UTC dates;
  `user_study_plans.timezone` is stored (routes/study_plan.py:247-251) but
  unused. Evening users in UTC+8/+9 (the ZH/JA audience) get day rollover at
  07:00–08:00 local — acceptable, but decide and document.

### F16 (L) — Wiki hygiene
- [[tasklist/study-plans.tasks]] shows TASK-201…220 all "Not Started" while the
  code is live; `tasklist/master.md` has no Phase-13/session-runner section;
  [[pages/pages-overview]] lacks `/session`; the runner's design doc is an
  out-of-repo plan file (`~/.claude/plans/we-now-have-the-swirling-haven.md`)
  referenced from code comments.

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
