---
title: "ADR-032: Session module exclusion — redistribute in Tier B, filter in Tier C"
status: accepted
date: 2026-10-12
---

# ADR-032: Session module exclusion — redistribute in Tier B, filter in Tier C

## Context

Learners want to switch daily-session modules (listening, reading, dictation, pinyin, pitch
accent, flashcards, dual translation, vocabulary practice) on and off from their settings. An
excluded module should be left out of the planned daily session only. It must stay usable
everywhere else in the app.

The developer settled four choices on 2026-10-12:

1. **Keep the daily length.** The minutes an excluded module would have used go to the modules
   that remain. The session does not get shorter.
2. **Per-language scope.** This matches [[decisions/ADR-011-per-language-independent-budgets]].
3. **Every module is toggleable**, with at least one left on.
4. **Immediate effect**, including today's not-yet-completed slots.

The daily session is planned in two tiers ([[features/study-plans.tech]]). **Tier B**
(`compute_weekly_plan`, Python) turns the template's `weekly_test_counts` and
`practice_total_minutes` into weekly targets. **Tier C** (`build_daily_session`, SQL) turns the
weekly targets into today's slots. It splits today's budget between the test/surface side and the
practice side in proportion to each side's outstanding weekly minutes (TASK-732).

## Decision

1. Store the setting as `user_study_plans.excluded_modules text[] NOT NULL DEFAULT '{}'`. A CHECK
   constrains it to the known module vocabulary. The route enforces the per-language
   "offered by the template" and "≥1 kept" rules.
2. **Tier B owns redistribution.** Before allocation, `apply_module_exclusions` removes the
   excluded modules from the template. It then multiplies every remaining *scalable* module
   (test counts and practice minutes) by one common factor
   `k = (M_total − M_fixed) / M_scalable`, using largest-remainder integer rounding. Template
   total minutes and the relative mix of the kept modules are both preserved. `flashcards` is
   fixed (not scaled). The rest of the Tier B pipeline (bandit, ±50% bounds, carry-over,
   `daily_minutes·7` clamp) runs unchanged on the adjusted template.
3. **Tier C filters as defence in depth.** `build_daily_session` drops excluded keys from
   `target_counts` and practice candidates, and keeps retry and word_upload off excluded test
   types. A weekly state computed before the change, or a failed recompute, therefore still never
   schedules an excluded module.
4. **Immediate effect** comes from a settings-save hook. It recomputes the learner-local current
   week and then re-runs `build_daily_session` for today if today's row exists. TASK-705
   re-entrancy retains completed slots.
5. An empty `excluded_modules` short-circuits `apply_module_exclusions` to the identity, so
   existing plans behave byte-identically.

## Consequences

- **Easier:** no new tables, RPCs or queue kinds. All the existing Tier B math applies unchanged,
  and the session runner needs only a speed-round gate.
- **Easier:** a stale weekly state can never leak an excluded module into a session, because the
  Tier C filter reads the plan row directly.
- **Harder:** the module vocabulary now lives in three places that must agree: the SQL CHECK,
  `ALL_MODULES` in Python, and the i18n labels. A unit test pins the first two.
- **Constrained:** the "every skill ≥1 slot/week" coverage floor no longer holds universally. It
  holds for *included* modules only.
- **New exercise of an old path:** before this change, no Python code re-ran `build_daily_session`
  on a date that already had a row. TASK-705's same-day re-entrancy now has a production caller
  and needs an SQL-level test.
- **Edge:** if only `flashcards` remains, nothing can absorb the freed time and the session is
  shorter. This is accepted and surfaced in the UI.

## Alternatives Considered

- **Tier C filter only.** Dropping excluded skills only at daily resolution is simple, but the
  TASK-732 split then hands the freed minutes to the *other side*. Excluding listening would grow
  practice and leave reading untouched. That breaks choice 1 and distorts the test/practice ratio.
- **Tier B only.** This gives correct redistribution but no protection against a weekly state
  computed before the change, or a failed recompute. Retry and word_upload also live only in
  Tier C. Rejected as fragile.
- **Proportional-by-side redistribution** (freed test minutes go only to tests, freed practice
  minutes only to tests). This is asymmetric, and when every test module is excluded there is
  nowhere for the test minutes to go. One common factor across all scalable modules handles every
  combination.
- **Scale flashcards too.** Rejected. Flashcards is one block a day sized by due cards, so 8/week
  would double-book a day and add no review.
- **Apply from tomorrow.** Simpler, but the learner would keep seeing the module they just
  excluded. The developer chose immediate effect.
