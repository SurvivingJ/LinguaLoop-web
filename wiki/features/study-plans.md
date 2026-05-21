---
title: Study Plans
type: feature
status: planned
tech_page: ./study-plans.tech.md
last_updated: 2026-05-21
open_questions:
  - "Should the settings page surface a 'total time across languages' warning above a threshold, or just display the tally silently?"
  - "What's the right copy for explaining the 30:70 maintenance-vs-acquisition split to learners who notice it in the UI?"
---

# Study Plans

## Purpose

Study Plans is the orchestrator that answers "what should I do today?" for each learner. It allocates time across two budgets — Tests and Practice — per language, adapts the mix weekly to the learner's measured weaknesses, and resolves a concrete daily session that respects their time intent and weekday rhythm. See [[decisions/ADR-008-study-plan-orchestration-layer]] for the rationale.

## User Story

A learner signs up, picks Chinese, and chooses "30 minutes a day" in onboarding. The system creates their plan from the default Chinese 30-min template — 6 reading tests, 5 listening, 2 dictation, 1 pinyin, 1 measure-word per week, plus 90 minutes of Practice. The first week is balanced because the system has no data yet; cold-start exploration ensures every skill gets a fair try.

Two weeks in, the system has noticed: their listening accuracy is 58%, their reading is 71%. The Sunday-night recompute shifts the next week's mix — listening jumps from 5 to 9, reading dips from 6 to 4 (each bounded by floor/ceiling). Practice stays at 90 minutes but the maintenance share creeps up because the learner is starting to accumulate FSRS-due flashcards.

On Monday, they open the app at lunch and see today's session: 2 listenings, 1 reading, 1 dictation, 1 pinyin, and 15 minutes of Practice. Total ≈ 32 minutes. They do half, and Tuesday's resolver re-balances around what was completed.

If they skip a few days, Sunday's recompute notices and adds a 50%-decayed catch-up to the next week's targets — they won't be punished for one bad week, but chronic skippers don't accumulate forever.

## How It Works

### Per-language plans

A learner has one Study Plan row per language they're studying. Each row carries:
- `daily_minutes` — how much time they want to commit per day to this language.
- `weekday_shape` — 7 weights summing to 7 (default uniform; can be tilted toward weekends).
- `skill_weight_overrides` — optional per-skill multipliers (e.g. "give me extra listening").
- `template_id` — the bucket the plan was built from (30 / 45 / 60 min).

Multi-language users (e.g. CN + JP) have two independent plans. The settings UI displays a total-across-languages tally but does not cap it — see [[decisions/ADR-011-per-language-independent-budgets]].

### Two budgets

- **Tests** — comprehension tests (reading, listening, dictation) and language-specific trainers (pinyin, measure-word, pitch-accent). ELO-scored. Allocated as counts per skill per week.
- **Practice** — everything in the [[features/practice-engine|Practice Engine]]. Allocated as minutes per week, internally split between Maintenance (FSRS-due / decayed reviews) and Acquisition (ladder-active new learning).

See [[decisions/ADR-009-two-budget-tests-vs-practice]] for why two budgets and not three.

### Two tiers of adaptation

- **Weekly** (cron, Sundays at 23:00 UTC): The system recomputes the next week's test counts and Practice minutes based on a composite weakness signal — ELO gaps, accuracy trends, ladder stagnation, FSRS lapse rate. It also rebalances Maintenance vs Acquisition based on retention pressure (FSRS due count, BKT decay) vs learning pressure (stuck words, new-word rate).
- **Daily** (lazy, first session of the day): A daily resolver takes the weekly targets, considers what's already been done this week and what skills appeared in the last 3 days, and solves a small optimization for today's concrete mix. Output: which tests appear in today's `daily_test_loads`, and how many Practice minutes go to Maintenance vs Acquisition.

### Adaptation philosophy

The system maximizes overall fluency, not equal-ELO balance. A learner who's at ELO 1100 listening / 1350 reading will get more listening, because the *value* of fixing the weak skill outweighs the value of polishing the strong one. ELO 1800+ skills hit diminishing returns (the `diminishing` term in `value(s)`); past that, allocation tapers.

The Tier B allocator uses Thompson sampling over a Beta posterior of recent first-attempt accuracy ([[decisions/ADR-010-value-weighted-thompson-skill-mix]]). This balances exploitation (drill what's weak) with exploration (try cold-start skills). The sampling is deterministic (seeded by `user_id || week_start || skill_id`), so the same inputs always produce the same plan.

### Carry-over

If a learner skips days mid-week, the daily resolver caps single-day work at 1.5× the notional (so they can't binge a 6-day week into one day, which would induce fatigue and erode learning). What stays unfinished decays 50% into the next week's targets — so a chronically light week nudges next week up, but a single missed week doesn't double-stack.

## Templates

Templates are the starting points the adapter shifts from. Each `(language, daily_minutes)` cell defines weekly test counts per skill, total Practice minutes, and a 30:70 base Maintenance/Acquisition split.

### Chinese
| Daily | Reading | Listening | Dictation | Pinyin | Measure word | Practice |
|---|---|---|---|---|---|---|
| 30 min | 6 | 5 | 2 | 1 | 1 | 90 min |
| 45 min | 8 | 7 | 3 | 2 | 1 | 135 min |
| 60 min | 10 | 9 | 4 | 2 | 2 | 180 min |

### Japanese
| Daily | Reading | Listening | Dictation | Pitch accent | Practice |
|---|---|---|---|---|---|
| 30 min | 6 | 6 | 2 | 1 | 95 min |
| 45 min | 8 | 8 | 3 | 2 | 140 min |
| 60 min | 11 | 10 | 4 | 3 | 185 min |

### English
| Daily | Reading | Listening | Dictation | Practice |
|---|---|---|---|---|
| 30 min | 7 | 6 | 2 | 100 min |
| 45 min | 10 | 8 | 3 | 150 min |
| 60 min | 13 | 11 | 4 | 200 min |

### Bounds
- Test counts per skill bounded `[⌈target · 0.5⌉, ⌈target · 1.5⌉]` — the adapter can shift but not zero a skill or let one dominate.
- Maintenance share bounded `[0.15, 0.50]`; Acquisition share `[0.50, 0.85]`.
- Practice minutes can flex ±25% from template based on the global weakness signal, capped at `daily_minutes · 7`.

## Constraints & Edge Cases

- **Cold start** (new user, no attempt history): all weakness signals fall back to neutral (`weakness = 0.50`); the Beta(2,2) bandit prior stays wide, naturally exploring. Plus the per-skill floor of 1/week guarantees coverage of every supported skill.
- **No selected packs** (user studying a language but hasn't added a pack): Practice Acquisition has nothing to anchor on; falls through to Maintenance; if also empty, returns a "select a pack" nudge.
- **Multi-language user** (e.g. studying CN and JP): two independent plans; cron iterates both; settings page shows a per-language tab and a total-across-languages tally.
- **Multiple sessions per day**: the daily resolver runs once per day per language; subsequent session requests read the resolved targets from `daily_test_loads.daily_session_targets`.
- **Mid-week template change**: editing `daily_minutes` updates the row immediately, but the in-flight `weekly_plan_states` row is not recomputed unless the learner explicitly triggers a manual recompute. Sunday's cron will pick up the change.
- **Skipped weekly recompute** (cron failed, user newly created mid-week): Tier C falls back to running with template defaults (no carry-over). Logged for monitoring.
- **Timezones in V1**: all weekly recomputes use UTC. A user in NZ/JP gets their fresh plan during their Monday morning; an Americas user gets it Sunday evening local. V2 supports per-user TZ via the `user_study_plans.timezone` column already present.

## Business Rules

- Practice sessions remain free of token cost (unchanged from existing Vocab Dojo / Exercises).
- Tests still consume tokens / free-tier limits per existing logic — the plan respects `get_daily_free_test_limit` when filling test slots.
- A learner can edit `daily_minutes`, `weekday_shape`, and `skill_weight_overrides` at any time. Changes apply to the next Sunday's recompute and the next daily resolve.
- The `goal_id` column is present but ignored in V1 — see [[decisions/ADR-008-study-plan-orchestration-layer]] for the V2 plan.

## Onboarding

A new user picks a language and a daily-minutes bucket (default 30; choices: 15 / 30 / 45 / 60 / 90 / 120). The system calls `apply_study_plan_template(user, language, default_template_for_30min)` to create their plan. Sunday's cron picks them up; their first daily session post-Monday is plan-driven.

Existing users at the time of rollout get default plans via a one-shot backfill (default 30 min/day, uniform weekday). Their in-flight Monday daily test load is preserved; plan-driven loads start the next day.

## Worked Example

A learner is 4 weeks into a Chinese plan at 45 min/day, uniform weekday. Their listening ELO is 1100 (weak), reading is 1350 (mid), dictation is 1280, pinyin is 1450, measure-word is 1380. The Sunday recompute notices listening accuracy is 58%, ladder stagnation across 32% of subscribed senses, FSRS lapse rate 18%.

Tier B computes weakness scores: listening at 0.54, dictation at 0.17, reading at 0.10, pinyin and measure-word ≈ 0.09. After Beta-sampled accuracy weighting and floor/ceiling clamping, the next week's test counts become: reading=4, listening=11, dictation=4, pinyin=1, measure-word=1 (total 21).

Practice rebalancing: maintenance pressure 0.45, acquisition pressure 0.57 → maintenance share 44%, acquisition 56%. Practice minutes flex down to 115 from the template's 135 (global weakness 0.20 is below 0.50, so the flex factor is 0.85).

Monday morning, the daily resolver computes today_budget = 226/7 ≈ 32 minutes. After greedy filling and a local-swap pass, today's plan: 3 listenings, 1 reading, 1 dictation, 1 measure-word, 1 pinyin, 10 minutes Practice Acquisition — total ≈ 45 minutes (close to the 1.5× day cap).

Full numerical traceback in [[features/study-plans.tech]] under "Worked Example."

## Related Pages

- [[features/study-plans.tech]] — Full technical specification.
- [[algorithms/study-plan-adaptation]] — Plain-English adaptation philosophy.
- [[algorithms/study-plan-adaptation.tech]] — Formulas and pseudocode.
- [[features/practice-engine]] — The Practice surface this orchestrator allocates against.
- [[features/comprehension-tests]] — The Tests budget content.
- [[decisions/ADR-008-study-plan-orchestration-layer]] — Why an orchestrator.
- [[decisions/ADR-009-two-budget-tests-vs-practice]] — Why two budgets.
- [[decisions/ADR-010-value-weighted-thompson-skill-mix]] — Tier B algorithm.
- [[decisions/ADR-011-per-language-independent-budgets]] — Per-language model.
- [[decisions/ADR-013-global-feature-flag-rollout]] — Rollout / rollback mechanism.
