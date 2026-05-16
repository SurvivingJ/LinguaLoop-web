---
title: "ADR-006: Reduced-Volatility ELO on Daily-Load Retry-Slot Repeats"
status: accepted
date: 2026-05-15
---

# ADR-006: Reduced-Volatility ELO on Daily-Load Retry-Slot Repeats

## Context

Before this change, the test submission RPC (`process_test_submission`) skipped the entire ELO update block whenever `is_first_attempt = false`. The dashboard's daily-load *retry slot* surfaces previously-attempted tests the user scored below 70% on (24h cooldown), but retaking one of these tests produced **zero ELO movement** — the user felt unrewarded for the effort, and the system gave up a real (if attenuated) re-assessment signal.

`get_recommended_tests` itself still excludes all previously-attempted tests, so the retry slot is the *only* path where a learner is asked to repeat a test as part of their normal flow. This is the surface where reduced-but-nonzero ELO is most pedagogically defensible: the system is explicitly inviting the repeat, the user scored badly, and a delta in performance — over time, or in absolute terms — is informative.

## Decision

When a user submits a repeat attempt and the test appears in today's `daily_test_loads.test_ids` with `slot_type = 'retry'` for that user and language, apply ELO updates at a reduced factor:

```
days_since   = (NOW() − MAX(prior.created_at)) / 86400 seconds
base         = clamp(0.20, days_since / 60.0, 1.0)
prev_best    = MAX( score / total_questions × 100 )  over all prior (user, test) attempts
bonus        = 0.25 if (current_percentage − prev_best) ≥ 15 else 0
factor       = LEAST(1.0, base + bonus)

user K_eff   = 32 × calculate_volatility_multiplier(...) × factor
test K_eff   = 16 × factor   -- test side still skips the volatility helper
```

The factor floor of 0.20 ensures any retry-slot attempt earns a token reward; the 60-day ceiling makes long-gap repeats count as fresh assessments. The +0.25 improvement bonus rewards genuine learning over memorisation.

Three eligibility conditions, all server-side (no client flag):

1. `is_first_attempt = false`.
2. Test is in today's retry slot for this user+language (JSONB element scan against `daily_test_loads`).
3. No prior `test_attempts` row today for this `(user, test)` already has `elo_reduction_factor IS NOT NULL` — anti-grind: at most one reduced-ELO submission per test per day.

The applied factor is persisted to `test_attempts.elo_reduction_factor` (numeric, nullable). NULL means no factor was applied (first attempt at full K, or non-eligible repeat at zero K).

Off-recommendation repeats — direct slug navigation, history page replays, manual retries of tests not currently in the retry slot — keep the status-quo zero-ELO behaviour.

## Consequences

- **Easier:** The dashboard's retry-slot effort registers as real ELO motion, which is motivational and pedagogically honest.
- **Easier:** Long-gap repeats (60+ days) are treated as fresh assessments, which is statistically appropriate when memorisation contamination is low.
- **Easier:** Grinding is structurally bounded — anti-grind sentinel + 24h cooldown on the retry slot means at most one reduced-ELO repeat per test per day.
- **Harder:** Slightly more complex ELO calculation; the factor depends on three SQL lookups (retry-slot EXISTS, anti-grind EXISTS, prior-attempt MAX), all on indexed columns.
- **Harder:** Users may not understand why two repeats of the same test yield different ELO changes; a UI badge (`Review · 0.45× ELO`) helps but doesn't eliminate the surface.
- **Constrained:** Day boundary is UTC-aligned via `CURRENT_DATE` and `created_at::date`, consistent with how `daily_test_loads.load_date` is written. A user near a UTC midnight may see edge-case timing.

## Alternatives Considered

1. **Flat 0.5× K on all repeats** (Option A in the planning doc). Trivial to ship — one migration, no Python/JS — and uniform. Rejected because it does not distinguish a thoughtful 60-day-later revisit from a 5-minute memorisation grind, and it grants ELO to off-recommendation replays we want to keep at zero.

2. **Slot-typed buckets** (Option C). Retry slot = flat 0.5× K, everything else = 0. Rejected because the discrete bucket is coarser than a time-decay function: a same-day grind earns the same 0.5× as a thoughtful one-month revisit, which inflates ratings disproportionately for short-gap repeats.

3. **Broadening `get_recommended_tests` to include attempted tests** (a variant of Option D's scope). Rejected for this round to keep the change narrow; the daily-load retry slot is already the system's pedagogical "review" surface, and expanding the recommender opens UX questions (how often, what mix, what badging) that are better treated as a follow-up.

4. **Glicko-2 / RD-based uncertainty** (deferred from ADR-001). The right long-term answer for "how confident are we in this rating?", but materially more complex than this change needs.

## Related Pages

- [[algorithms/elo-ranking.tech]] — Updated data-flow and factor sections.
- [[algorithms/elo-implementation-analysis]] — "Recently Fixed (2026-05-15)" entry.
- [[features/comprehension-tests.tech]] — Submission flow interaction with retry slot.
- [[decisions/ADR-001-dual-elo]] — Foundational dual-ELO decision this builds on.
