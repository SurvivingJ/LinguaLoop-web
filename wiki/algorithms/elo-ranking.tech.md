---
title: ELO Ranking — Technical Specification
type: algorithm-tech
status: complete
prose_page: ./elo-ranking.md
last_updated: 2026-05-15
dependencies:
  - "calculate_elo_rating() function"
  - "calculate_volatility_multiplier() function"
  - "process_test_submission() function"
  - "get_recommended_test() / get_recommended_tests() functions"
  - "user_skill_ratings table"
  - "test_skill_ratings table"
  - "daily_test_loads table (retry-slot eligibility lookup)"
breaking_change_risk: medium
---

# ELO Ranking — Technical Specification

## Formula

Implemented in `calculate_elo_rating()` plpgsql function:

```
expected_score = 1.0 / (1.0 + 10^((opposing_rating - current_rating) / 400.0))
adjusted_k = k_factor * volatility_multiplier
new_rating = current_rating + (adjusted_k * (actual_score - expected_score))
result = clamp(400, 3000, round(new_rating))
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `k_factor` | 32 | Standard ELO K-factor. Higher = more volatile. |
| `volatility_multiplier` | 1.0 | Amplifier for new/returning users |
| `actual_score` | 0.0-1.0 | Percentage correct (score / total_questions) |

### Volatility Multiplier

`calculate_volatility_multiplier(attempts, last_date, base_volatility)`:

```
multiplier = base_volatility  (default 1.0)
if attempts < 10:  multiplier += 0.5
if last_date > 90 days ago:  multiplier += 0.5
```

Maximum effective K = 32 * 2.0 = 64 for a new user who hasn't tested in 90+ days.

## Data Flow

```
User submits test
  → process_test_submission()
    → calculate percentage: score / total_questions
    → fetch user_skill_ratings for (user, language, test_type)
    → fetch test_skill_ratings for (test, test_type)
    → calculate_volatility_multiplier for user (re-enabled in Phase 3)
    → BRANCH on attempt history:
        - First attempt:  full K (status quo)
        - Repeat + retry-slot eligible: reduced K (factor < 1.0)
        - Repeat + not eligible:        skip ELO update entirely (factor = 0)
    → new_user_elo = calculate_elo_rating(user_elo, test_elo, percentage, 32, volatility × factor)
    → new_test_elo = calculate_elo_rating(test_elo, user_elo, 1-percentage, 16, 1.0 × factor)
    → UPSERT user_skill_ratings (if factor > 0)
    → UPSERT test_skill_ratings (if factor > 0)
    → INSERT test_attempts with elo_before/elo_after snapshots + elo_reduction_factor
```

### Asymmetric K-Factors (Phase 3 fix)

User K=32, Test K=16. Tests move at half the rate of users because each test is taken by many users — with symmetric K, test ratings would be overly volatile. Test volatility is always 1.0 (tests don't get "rusty").

### Retry-Slot Reduced-Volatility Factor (2026-05-15)

Implemented in [migrations/process_test_submission_reduced_repeats.sql](../../migrations/process_test_submission_reduced_repeats.sql). A repeat attempt earns reduced ELO iff all of:

1. `is_first_attempt = false` (counted from `test_attempts`).
2. The test currently appears in today's `daily_test_loads.test_ids` for this user and language with `slot_type = 'retry'` (JSONB element scan via `jsonb_array_elements`).
3. The user has no prior `test_attempts` row today for this `(user, test)` with `elo_reduction_factor IS NOT NULL` (anti-grind: once per day).

When eligible, the factor is:

```
days_since   = (NOW() - MAX(prior.created_at)) / 86400s
base         = LEAST(1.0, GREATEST(0.20, days_since / 60.0))
prev_best    = MAX(score / total_questions * 100) over all prior (user, test) attempts
bonus        = 0.25 if (current_percentage - prev_best) >= 15 else 0
factor       = LEAST(1.0, base + bonus)
```

Applied symmetrically:

```
user_k_effective = 32 × calculate_volatility_multiplier(...) × factor
test_k_effective = 16 × factor   (test side still skips the volatility helper)
```

Notable factor values:
- Same-day retry, no improvement: factor ≈ 0.20.
- 30 days later: factor ≈ 0.50.
- 60+ days later: factor = 1.0 (effectively a fresh first attempt).
- Same-day retry with 50% → 80% breakthrough: factor ≈ 0.45 (0.20 + 0.25).

The applied factor is persisted to `test_attempts.elo_reduction_factor` (numeric, nullable). NULL means no factor was applied (first attempt at full K, or non-eligible repeat at 0 K). The submission response (`_build_submission_response` in [routes/tests.py](../../routes/tests.py)) and `/api/tests/history` both surface this column to the client.

## Test Recommendation Algorithm

### `get_recommended_test(user_id, language_id)`

Expanding-radius single-test selection:
1. Get user's listening and reading ELO
2. For each radius in [50, 100, 250, 500, 10000]:
   - Find an active test within ±radius of user's ELO for either type
   - If found, return it (random selection within radius)
3. **Phase 3 fix:** Excludes previously attempted tests via `NOT EXISTS (SELECT 1 FROM test_attempts WHERE user_id = ... AND test_id = t.id)`

### `get_recommended_tests(user_id, language)`

Ranked multi-test recommendation:
1. Get user's ELO per test type
2. Find all active tests, ranked by ELO proximity
3. Partition by test type, take top 3 per type
4. Deduplicate across types
5. Exclude previously attempted tests
6. Respect tier access (free users only see free-tier tests)
7. Return sorted by ELO proximity

## Tables

### `user_skill_ratings`
- Unique: `(user_id, language_id, test_type_id)`
- `elo_rating` default 1200, CHECK [400, 3000]
- `tests_taken` counter

### `test_skill_ratings`
- Unique: `(test_id, test_type_id)`
- `elo_rating` default 1400, CHECK [400, 3000]
- `total_attempts` counter

### `test_attempts.elo_reduction_factor` (added 2026-05-15)
- `numeric NULL` — populated only when reduced-volatility ELO fired on a repeat attempt; NULL otherwise.
- Used by the profile history badge and as the once-per-day anti-grind sentinel.

## Related Pages

- [[algorithms/elo-ranking]] — Prose description
- [[algorithms/elo-implementation-analysis]] — Implementation history and audit
- [[decisions/ADR-006-retry-slot-reduced-elo]] — Why reduced-volatility on retry-slot repeats
- [[features/comprehension-tests.tech]] — Test submission flow
- [[database/schema.tech]] — Table DDL
