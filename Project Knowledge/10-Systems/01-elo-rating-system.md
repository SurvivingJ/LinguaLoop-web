# ELO Rating System

## Overview

Adapted from chess ELO for adaptive test difficulty matching. Both users and tests have ELO ratings. After each test attempt, both ratings are updated based on the user's performance relative to the expected outcome.

## Starting Values

- **Users**: 1200 (all skills, all languages)
- **Tests**: Varies by CEFR level (from `dim_cefr_levels`):

| CEFR Level | Difficulty | Initial ELO |
|------------|-----------|-------------|
| A1 | 1-2 | 875 |
| A2 | 3-4 | 1175 |
| B1 | 5 | 1400 |
| B2 | 6 | 1550 |
| C1 | 7 | 1700 |
| C2 | 8-9 | 1925 |

## ELO Formula

```
Expected Score = 1 / (1 + 10^((opponent_elo - player_elo) / 400))
New ELO = Current ELO + K * Volatility * (Actual Score - Expected Score)
```

- **K-factor**: 32 (user), 16 (test in v1), 32 (both in v2)
- **Actual score**: percentage correct (0.0-1.0)
- **For test**: actual score is inverted (1 - user_percentage)
- **ELO clamped**: 400-3000

## Volatility

- **Base**: 1.0
- **+0.5** if < 10 attempts (new player/test)
- **+0.5** if > 90 days since last attempt (returning player)
- Only used in v1 (`calculate_volatility_multiplier`). v2 uses fixed K=32.

## Key Rules

- Only first attempts change ELO (retakes don't affect ratings)
- Idempotency key prevents duplicate submissions
- User ELO is per-language per-skill (`user_skill_ratings` table)
- Test ELO is per-skill (`test_skill_ratings` table)
- Recommendation: tests within +/-200 ELO of user

## Database Functions

- **`process_test_submission`** (v2): Validates answers, calculates ELO, creates attempt record atomically
- **`calculate_elo_rating`**: Pure ELO calculation
- **`calculate_volatility_multiplier`**: Volatility based on experience

## Related Tables

| Table | Key Columns | Purpose |
|-------|------------|---------|
| `user_skill_ratings` | user_id, language_id, test_type_id, elo_rating, tests_taken | Tracks user ELO per language per skill |
| `test_skill_ratings` | test_id, test_type_id, elo_rating, total_attempts | Tracks test ELO per skill |
| `test_attempts` | Records before/after ELO for both user and test | Audit trail of ELO changes |

## Related Documents

- [06-cefr-difficulty-mapping.md](06-cefr-difficulty-mapping.md) - CEFR levels and initial ELO values
- [05-language-support.md](05-language-support.md) - Per-language skill ratings
- [02-token-economy.md](02-token-economy.md) - Token cost for taking tests
