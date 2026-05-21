---
title: Study Plan Adaptation
type: algorithm
status: planned
tech_page: ./study-plan-adaptation.tech.md
last_updated: 2026-05-21
open_questions: []
---

# Study Plan Adaptation

## Purpose

The Study Plan adapter is the brain of the [[features/study-plans|Study Plans orchestrator]]. Once a week, it looks at a learner's measured behavior and rewrites the next week's targets — which skills get more tests, which less, and how much Practice time should split between maintenance and acquisition. Once a day, it solves a small optimization for *today's* concrete mix from those weekly targets.

The goal is **maximizing overall fluency**: the adapter pushes time toward weakness with value-weighting (rather than equal-ELO balancing), respects floor/ceiling guardrails so no skill is starved or dominates, and explores cold-start skills via bandit-style sampling instead of locking onto the first weakness it sees.

## Two Tiers

### Tier B — Weekly Adapter

Runs every Sunday at 23:00 UTC for every active `(user, language)`. Three jobs:

1. **Weakness signal.** For each test skill, combine four indicators into one number:
   - ELO gap (how far below the learner's mean is this skill?)
   - Accuracy trend (how far below 75% is the 28-day first-attempt accuracy?)
   - Ladder stagnation (what fraction of subscribed senses haven't moved in 14 days?)
   - FSRS lapse rate (lapses / reviews over the last 28 days)

   Default weights `(0.40, 0.25, 0.20, 0.15)`. Cold-start skills (fewer than 5 attempts) fall back to a neutral 0.50, with a wide bandit prior that ensures exploration. See [[decisions/ADR-010-value-weighted-thompson-skill-mix]] for why those four signals.

2. **Test count allocation.** Use value-weighted Thompson sampling to distribute the template's total weekly test count among skills:
   - Sample a Beta posterior over each skill's recent first-attempt accuracy.
   - Compute `bandit_score = value(s) · (1 − accuracy_sample)` — the worse the sample, the more this skill is weighted.
   - Allocate proportionally, then clamp each skill into `[⌈target · 0.5⌉, ⌈target · 1.5⌉]`, redistributing overflow.

   The bandit's randomness is seeded deterministically by `(user_id, week_start, skill_id)` so re-running the adapter with the same DB state always produces the same plan.

3. **Practice rebalancing.** Compute maintenance pressure (FSRS-due count, BKT decay) and acquisition pressure (stuck-word count, new-word rate) and rebalance the maintenance/acquisition split, clamped to `[0.15, 0.50]` / `[0.50, 0.85]`. Adjust total Practice minutes ±25% from the template based on global weakness, capped at the weekly time budget.

The output is one row per `(user, language, week_start)` in `weekly_plan_states`.

### Tier C — Daily Resolver

Runs lazily on the first session request per day. Reads:
- The current `weekly_plan_states` row (weekly targets, completed counts so far).
- The user's `weekday_shape` to compute `today_budget`.
- The last 3 days' skills (from `daily_test_loads`) for a spacing penalty.

Solves a small constrained optimization with ≤ 8 variables (test counts per skill + Practice minutes split into maintenance and acquisition):

- Maximize: `Σ count(s) · value(s) + α · maintenance_min + α · acquisition_min − γ · spacing_penalty`.
- Subject to: total minutes ≤ 1.5× today_budget (soft cap for catch-up days), each skill within its remaining weekly quota, Practice modes within their remaining weekly minutes, Practice total > 0.

The algorithm is greedy + local-swap: sort all candidates (test slots + 10-min Practice chunks) by value-per-minute, fill until cap, then try a swap pass. With at most 6 test skills and 2 Practice variables the problem is trivial; ILP fallback is reserved for future expansion.

The result writes test IDs (hydrated via the existing `get_recommended_tests` ELO matcher) to `daily_test_loads` and Practice minute targets to `daily_test_loads.daily_session_targets`.

## Why These Choices

### Value-weighted, not equal-balanced

A learner at listening 1100 / reading 1350 doesn't benefit equally from improving each by 50 ELO. The listening weakness is the larger fluency drag; the value formula `weakness · (1 − diminishing)` makes that quantitative. Diminishing returns kick in above ELO 1800 (full at 2400), recognizing that polishing a strong skill yields less per minute than fixing a weak one.

### Bandit, not pure greedy

Pure greedy on `value(s)` would lock onto the single weakest skill and starve the others until the ceiling forces a switch. Cold-start skills (no recent attempts) would never bubble up. Thompson sampling with a Beta posterior keeps exploration alive: a skill with low accuracy and few samples has a wide posterior, so it occasionally samples a high accuracy and gets less weight — and vice versa. With deterministic seeding the randomness is reproducible.

### Floor/ceiling, not unbounded

Without bounds, one bad week of listening could push the adapter to allocate 90% of tests there. Floor/ceiling at `⌈target · 0.5⌉` / `⌈target · 1.5⌉` keeps any single skill within a reasonable band. Languages with niche skills (pinyin, measure-word, pitch-accent) at `target = 1` get `floor = 1, ceiling = 2` — guaranteed weekly coverage, modest upside.

### Carry-over with decay

A learner who skips three days mid-week ends with 70% of weekly budget unfinished. The daily resolver's 1.5× cap means they can't binge-recover in one day; what doesn't get done bleeds 50% into next week's targets. So one missed week is forgiven; a chronically light user gradually has their plan right-sized.

### Weekly cadence, daily resolution

Adaptation at the weekly level prevents jitter (one bad listening test on Tuesday shouldn't flip the entire plan to listening). Resolution at the daily level adapts to real behavior (if Monday was 2× heavy, Tuesday gets pulled back). The 1.5× soft cap and the 50%-decay carry-over together keep both tiers honest.

## What the Adapter Does Not Do

- **Predict the future.** It looks at the last 28 days for signal, the last 3 days for spacing, and the last week for carry-over. It does not project ELO trajectories or estimate time-to-mastery.
- **Cross-language coupling.** Per [[decisions/ADR-011-per-language-independent-budgets]], plans are independent per language. The adapter for Chinese doesn't see Japanese.
- **Goal-driven biasing.** Goals are V2; the `goal_id` column is present but ignored in V1.
- **Notification timing / streak preservation.** Out of scope; those live above the plan layer.

## See Also

- [[algorithms/study-plan-adaptation.tech]] — Formulas, constants, pseudocode.
- [[features/study-plans]] — How the adapter fits into the learner UX.
- [[features/study-plans.tech]] — Full RPC + schema spec.
- [[decisions/ADR-008-study-plan-orchestration-layer]], [[decisions/ADR-009-two-budget-tests-vs-practice]], [[decisions/ADR-010-value-weighted-thompson-skill-mix]].
