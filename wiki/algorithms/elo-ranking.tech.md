---
title: ELO Ranking — Technical Specification
type: algorithm-tech
status: complete
prose_page: ./elo-ranking.md
last_updated: 2026-04-15
dependencies:
  - "calculate_elo_rating() function"
  - "calculate_volatility_multiplier() function"
  - "process_test_submission() function"
  - "get_recommended_test() / get_recommended_tests() functions"
  - "user_skill_ratings table"
  - "test_skill_ratings table"
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
    → new_user_elo = calculate_elo_rating(user_elo, test_elo, percentage, 32, volatility)
    → new_test_elo = calculate_elo_rating(test_elo, user_elo, 1-percentage, 16, 1.0)
    → UPSERT user_skill_ratings
    → UPSERT test_skill_ratings
    → INSERT test_attempts with elo_before/elo_after snapshots
```

### Asymmetric K-Factors (Phase 3 fix)

User K=32, Test K=16. Tests move at half the rate of users because each test is taken by many users — with symmetric K, test ratings would be overly volatile. Test volatility is always 1.0 (tests don't get "rusty").

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

## Related Pages

- [[algorithms/elo-ranking]] — Prose description
- [[features/comprehension-tests.tech]] — Test submission flow
- [[database/schema.tech]] — Table DDL
