---
title: "ADR-010: Value-Weighted Thompson Sampling for Weekly Test-Skill Allocation"
status: accepted
date: 2026-05-21
---

# ADR-010: Value-Weighted Thompson Sampling for Weekly Test-Skill Allocation

## Context

Tier B of the Study Plan orchestrator ([[decisions/ADR-008-study-plan-orchestration-layer]]) must allocate a weekly *count of tests per skill* across ~5 comprehension test skills (reading, listening, dictation + 1–2 language-specific trainers). The allocation should:

- Push more time toward skills the learner is genuinely weak at (value-weighted).
- Explore untested skills, not just exploit known weak ones (cold-start handling).
- Stay deterministic enough to reason about ("why did I get 11 listenings this week?") and idempotent (re-running Tier B with the same inputs produces the same plan).
- Honor floor/ceiling constraints from the template (no skill goes to zero; no skill dominates).

Several algorithms were evaluated:

- **Pure greedy on `value(s)`.** Allocates everything to the single weakest skill until the ceiling is hit, then moves to the next. No exploration; cold-start skills with no data never bubble up.
- **Pure heuristic priority score.** Same problem — no exploration, miscalibrates when the priority weights are wrong.
- **Multi-armed bandit (Thompson sampling).** Each skill modeled as a Beta-distributed arm over first-attempt accuracy. Each recompute samples once per arm; the sample uncertainty handles exploration naturally.
- **Multi-objective evolutionary (NSGA-II).** Overkill for ≤ 8 variables.
- **Reinforcement learning (DQN/PPO).** Opaque, data-hungry, hard to debug. Disqualifying for a small N-of-skills allocation problem with strong domain priors.

## Decision

Use **value-weighted Thompson sampling**, capped to template floor/ceiling, with water-fill redistribution of overflow:

```python
alpha = 2 + first_attempt_correct_28d(s)
beta  = 2 + first_attempt_wrong_28d(s)
seed  = hash(user_id || week_start || skill_id)       # determinism
acc_sample = numpy.random.default_rng(seed).beta(alpha, beta)
bandit_score(s) = value(s) · (1 - acc_sample)
```

Allocate the template's total weekly test count proportional to `bandit_score`, clamp each skill to `[floor, ceiling]`, redistribute overflow to highest-scoring unsaturated skills.

Where:
- `value(s) = weakness(s) · (1 - diminishing(s))` with `diminishing(s) = clamp01((elo(s) - 1800) / 600)`.
- `weakness(s) = 0.40·elo_gap + 0.25·accuracy_trend + 0.20·ladder_stagnation + 0.15·fsrs_lapse_rate`.
- Cold start (skill has < 5 first-attempt attempts in 28d): `weakness(s) = 0.50`; bandit prior `Beta(2, 2)` stays wide → high sample variance → high chance of being sampled.
- Per-skill user overrides: `weakness_adjusted(s) = weakness(s) · skill_weight_overrides[s]` (default 1.0; range 0.5–2.0).

`Beta(2, 2)` prior chosen over `Beta(1, 1)` (flat) so cold-start exploration is mildly informative around 0.5 rather than completely uniform. One sample per skill per recompute keeps Tier B cheap (≤ 8 RNG draws per user per week). Deterministic seed makes `compute_weekly_plan` idempotent: same inputs on the same week-start produce the same plan, so re-runs (manual triggers, replays, idempotent UPSERTs) don't shuffle the learner's expectations.

See [[algorithms/study-plan-adaptation.tech]] for the full allocation algorithm including water-fill.

## Consequences

- **Easier:** Cold-start skills get explored without manual intervention. A new user gets a balanced first week even with zero attempt history.
- **Easier:** Deterministic seed makes the plan debuggable and idempotent. Re-running Tier B with the same DB state always produces the same `target_counts`.
- **Easier:** The `(1 - acc_sample)` weighting means high-accuracy skills (the user already does well) get less allocation than low-accuracy skills, even if `value(s)` is similar — a useful secondary signal.
- **Harder:** Bandit math is less immediately readable than a pure greedy formula. Mitigated by the worked example in [[features/study-plans.tech#worked-example]] and the deterministic seed (a developer can reproduce any week's allocation).
- **Constrained:** Single-sample Thompson is noisier than 100-sample-median. For ≤ 8 arms with strong template floors/ceilings, the noise is bounded and the cost saving is meaningful.
- **Constrained:** The diminishing-returns cap at ELO 1800 (full at 2400) is language-agnostic. If telemetry shows the cap is too low for English (where users plateau higher) or too high for Pinyin (where 1800 already means mastery), the V2 spec adds a per-language `diminishing_elo_anchor` to `dim_languages`.

## Alternatives Considered

1. **Pure greedy on value.** Rejected — no exploration; cold-start skills starve.

2. **Beta(1, 1) flat prior with 100-sample median.** Rejected — costlier and not obviously better than the chosen approach given that cold-start fallback handling (`weakness = 0.50` when n < 5) and the floor=1/week template constraint together backstop exploration.

3. **Non-deterministic random sampling each run.** Rejected — loses idempotency; a learner's plan would shift week-to-week even with stable inputs. Bad for trust and debugging.

4. **UCB1 (Upper Confidence Bound).** Could substitute for Thompson. Rejected — UCB is sharper for fixed time horizons; Thompson handles non-stationary weakness signals more gracefully (the underlying distribution changes as the user learns).

5. **Per-template tuning of the four weakness weights `(w_elo, w_acc, w_lad, w_fsrs)`.** Rejected for V1; one set of defaults `(0.40, 0.25, 0.20, 0.15)` across all templates keeps the spec simple. Per-template overrides can be added to `dim_study_plan_templates` if telemetry shows the defaults misfit a language.

## Related Pages

- [[algorithms/study-plan-adaptation]] — Plain-English description.
- [[algorithms/study-plan-adaptation.tech]] — Full algorithm including water-fill.
- [[features/study-plans.tech]] — Tier B context and worked example.
- [[decisions/ADR-008-study-plan-orchestration-layer]] — The layer that calls this allocator.
