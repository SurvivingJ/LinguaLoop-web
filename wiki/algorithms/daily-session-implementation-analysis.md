---
title: Daily Session Implementation Analysis
type: algorithm
status: complete
tech_page: daily-session-implementation-analysis.tech.md
last_updated: 2026-07-05
open_questions:
  - "Should listening_lab / mystery / dual_translation / flashcards ever be plannable session items, or stay standalone surfaces? (Needs a product decision before TASK-711.)"
  - "Should the session day boundary follow user_study_plans.timezone instead of UTC?"
---

# Daily Session Implementation Analysis

## Purpose
Audit (2026-07-05) of the daily training pipeline: Tier B weekly planner → Tier C
resolver (`build_daily_session`) → `/session` single-page runner. Answers four
questions: is the HTML ready, does the algorithm cover all test types, will it
schedule properly, and will it interleave?

## Verdicts at a Glance

| Question | Verdict |
|---|---|
| HTML ready to serve? | **Mostly yes.** Route, template, controller, 6 players, i18n in all 4 locales all ship. Gaps: no navbar entry, no error-retry, weak a11y, no timing capture. |
| Covers all test types? | **Covers the 6 plannable types** (reading, listening, dictation, pinyin, pitch_accent, classifier_drill-via-sentinel). listening_lab, mystery, dual_translation, flashcards are outside the planner — partly by design, undocumented. |
| Will it schedule properly? | **No — three compounding faults.** The Sunday cron seeds the *outgoing* week, so plan-driven days silently fall back to legacy every Monday; practice minutes never advance (0 ms attempts), so practice is re-scheduled at full target daily; slot hydration shortfalls are silently dropped. |
| Will it interleave? | **No.** Tests are emitted grouped by type (`ORDER BY skill, test_id`) and practice is always appended last. The resolver's γ-spacing term is cross-**day** variety, not within-session interleaving. |

## How It Works Today
1. Sundays 23:00 UTC, a cron recomputes every user's weekly plan (target test
   counts per skill + practice minutes) via Thompson-sampled skill values.
2. On the first request each day, `build_daily_session` greedily fills the
   day's minute budget from remaining weekly targets, writes `daily_test_loads`,
   and the `/session` page runs the queue: all tests (grouped by type), then up
   to two practice blocks (acquisition, maintenance).
3. Submissions feed progress counters back into the weekly state so later days
   schedule less of what's already done.

## Critical Deficiencies
1. **The week is never seeded on time.** The Sunday-night cron computes the
   Monday of the week that is *ending*, not the week about to start. Nothing
   else creates the new week's state (applying a template doesn't; there is no
   lazy compute on `E_NOWEEK`). Result: every Monday the plan path declines and
   users silently get the legacy 3-test load all week, unless they press
   "Recompute this week now" in Study Plan settings.
2. **Practice progress is invisible.** The session practice player reports
   `time_taken_ms: 0` for every attempt, and per-attempt rounding to whole
   minutes discards short attempts anyway. Weekly practice-completed counters
   stay at zero, so the resolver re-schedules the full practice target every
   day and the next week's carryover assumes no practice happened.
3. **Budgeted slots vanish silently.** Slot hydration depends on
   `get_recommended_tests`, which returns at most 3 candidates per type and
   excludes every previously-attempted test. Thin or exhausted pools mean
   budgeted slots are dropped with no telemetry, while `used_minutes` still
   reports them as scheduled.

## High-Priority Improvements
- **Interleave the queue**: round-robin test types and sandwich practice blocks
  between tests (split the two monolithic blocks into ≤10-minute chunks).
- **Restore retry slots** under the plan path — [[decisions/ADR-006-retry-slot-reduced-elo]]
  mechanics are unused when a plan exists (`slot_type` is always `'new'`).
- **Protect completions**: `build_daily_session`'s upsert resets
  `completed_test_ids` to `[]`; any same-day re-invocation wipes progress.
- **Fix the legacy fallback** (it's now the de-facto Monday path): its ELO
  range filter is dead code and fallback picks are mislabeled `listening`,
  which mounts the wrong player and rates the wrong skill.

## Constraints & Edge Cases Confirmed Working
- Resume/re-entrancy: server-authoritative `next_index`, double-submit latch,
  one silent retry on persistence, failure toast (M2/M3 hardening).
- Classifier drill rides a per-language sentinel test row and completes through
  the standard daily-load path; ZH-only by data, degrades cleanly elsewhere.
- All 4 locale files carry the full `session.*` key set (23 keys each).
- Time-estimate refresh RPC filters `time_taken_ms > 0`, so zero-ms attempts do
  not corrupt p50 estimates (they just contribute nothing).

## Related Pages
- [[algorithms/daily-session-implementation-analysis.tech]] — evidence, file/line, fix sketches
- [[tasklist/daily-session-hardening.tasks]] — TASK-700+ remediation breakdown
- [[features/study-plans.tech]] — Tier B/C spec this audits against
- [[algorithms/study-plan-adaptation.tech]] — weakness/bandit/resolver formulas
