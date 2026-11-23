---
title: ELO System — Implementation Analysis & Improvements
type: algorithm
status: in-progress
tech_page: ./elo-implementation-analysis.tech.md
last_updated: 2026-11-23
open_questions:
  - "Is Glicko-2 worth the complexity over standard ELO for this use case?"
  - "OPEN: apply the two pending migrations (skill_ratings_natural_key_unique.sql, then skill_ratings_writers_on_conflict.sql) so a first-ever simultaneous submission cannot create duplicate rating rows? Checked live 2026-11-23: neither is applied, no duplicates exist."
  - "Should mystery ELO and test ELO share a unified skill rating model?"
---

# ELO System — Implementation Analysis & Improvements

## Purpose

This page analyses the current ELO implementation as it exists in the codebase (not as designed in the spec), identifies discrepancies between documentation and code, and proposes concrete improvements ordered by impact and feasibility.

## Current State Summary

The ELO system has three layers:

1. **Pure math** — `calculate_elo_rating()` and `calculate_volatility_multiplier()` exist as plpgsql functions and are correct.
2. **Test submission** — `process_test_submission()` handles grading, ELO updates, and attempt recording in a single atomic transaction.
3. **Recommendation** — `get_recommended_test()` (single) and `get_recommended_tests()` (multi) select tests by ELO proximity. `get_vocab_recommendations()` adds vocabulary-aware filtering.

## Volatility: Removed in V2, Restored in V3 (2026-05-08)

The most significant discrepancy between documentation and code has a historical explanation:

**V1 (`migrations/elo_functions.sql`)** correctly called both `calculate_elo_rating()` and `calculate_volatility_multiplier()`, with an asymmetric K-factor (32 for users, 16 for tests) and text-based columns (`language`, `skill_type`).

**V2 (`migrations/archive/process_test_submission_v2.sql`)** rewrote the function to add server-side answer grading. In the process, volatility was **dropped** and the ELO calc was inlined with symmetric K=32 for both user and test. The helper functions were not deleted from the database, creating the appearance of dead code that was actually intentionally disconnected.

**V3 (`migrations/wire_volatility_and_exclude_attempted.sql`)** restores volatility on the user side (multiplier applied to K=32 when user has <10 tests or is >90 days inactive) and reintroduces the asymmetric K-factor for tests (K=16, no volatility — tests don't go rusty). The inlined math is replaced with calls to the existing `calculate_volatility_multiplier()` and `calculate_elo_rating()` helpers.

### Test ELO Seeding

A test gets its initial rating when it is generated. The generation pipeline starts from the midpoint ELO of the topic's age tier (`dim_complexity_tiers.initial_elo`) and nudges it up or down by a small lexical-complexity score of the passage (`seed_test_elo` in `services/test_generation/difficulty_scorer.py`); if the scorer fails, the tier midpoint is used. The orchestrator then writes one `test_skill_ratings` row per applicable test type (`insert_test_skill_ratings` in `services/test_generation/database_client.py`). Checked live 2026-11-23: all 488 active tests have rating rows, so no backfill is needed. The older scripts/backfill_test_skill_ratings.py (which mapped difficulty 1 to 9 onto ELO 800 to 2000) has been **deleted**: it was obsolete, and because the tables have no uniqueness on the natural key it could have inserted duplicate rows. Sentinel tests used by the drill trainers (such as the measure-word drill) get their rating row from the submission function on first use (test ELO 1400). Users start at 1200 on their first submission per language and test type.

### Known limitation: duplicate rating rows on a simultaneous first submission

`user_skill_ratings` and `test_skill_ratings` have only a surrogate primary key (`id`). Nothing in the database makes `(user_id, language_id, test_type_id)` or `(test_id, test_type_id)` unique. `process_test_submission` now reads these rows with `FOR UPDATE`, which serialises submissions that find an existing row, but a lock cannot cover a row that does not exist yet, so two simultaneous first-ever submissions can each insert one. Checked live 2026-11-23: no duplicates exist. Two migrations that close this are written and **pending** (not applied): `migrations/skill_ratings_natural_key_unique.sql` (unique indexes) and `migrations/skill_ratings_writers_on_conflict.sql` (the submission functions use `ON CONFLICT`); they must be applied in that order. See [[algorithms/elo-implementation-analysis.tech]].

## Other Discrepancies

| Wiki Says | Code Does | Impact |
|-----------|-----------|--------|
| Tests start at 1400, users at 1200 | Correct in code | 200-point gap creates initial difficulty bias |
| Level 10 capstone exists | Not implemented | No productive assessment pathway |
| `user_word_progress` table tracks promotion/demotion counters | Actual table is `user_word_ladder` with simpler schema | Promotion/demotion logic simplified |

## What Works Well

1. **Atomic transactions**: `process_test_submission()` wraps grading + ELO + attempt recording + user_languages update in a single function. No partial state.
2. **Idempotency**: UUID-based duplicate detection prevents double-counting.
3. **First-attempt gating**: Only first attempts per test+type combo update ELO. Retakes don't inflate ratings.
4. **ELO snapshots**: `test_attempts` stores `user_elo_before/after` and `test_elo_before/after` on every attempt — full audit trail.
5. **Dual ELO**: User and test ratings move symmetrically, creating a self-correcting system.
6. **Rating bounds**: [400, 3000] prevents runaway ratings.

## Recently Fixed (2026-05-08)

`migrations/wire_volatility_and_exclude_attempted.sql` closes the two highest-priority gaps:

- **Volatility wired back into `process_test_submission`** — user-side K=32 is now multiplied by `calculate_volatility_multiplier(tests_taken, last_test_date)` (1.0 baseline → 1.5 for new users → 2.0 for new and inactive users). Test-side K=16 with no volatility, restoring V1's asymmetric design.
- **`get_recommended_test` excludes attempted tests** — the expanding-radius loop now carries a `NOT EXISTS` against `test_attempts`, matching the behaviour of `get_recommended_tests()`. If the user has exhausted every test in the language, the function returns nothing and the `/api/tests/random` route serves its existing 404.

## Recently Fixed (2026-05-15)

`migrations/archive/process_test_submission_reduced_repeats.sql` closes the **zero-ELO-on-retry** pedagogical gap:

- **Retry-slot reduced-volatility repeats** — when the daily-load retry slot resurfaces a sub-70% test, retaking it now grants ELO at a time-decay factor `clamp(0.20, days_since_last/60, 1.0)` plus a `+0.25` improvement bonus if the user gains 15+ percentage points over their prior best. Applied symmetrically to user (K=32 × volatility × factor) and test (K=16 × factor). Off-recommendation repeats keep their status-quo 0 ELO. Anti-grind: at most one reduced-ELO submission per `(user, test)` per day, enforced via `test_attempts.elo_reduction_factor IS NOT NULL` sentinel. See [[decisions/ADR-006-retry-slot-reduced-elo]].

## What Needs Improvement

### Priority 1: Vocabulary-ELO Integration

`get_vocab_recommendations()` already combines ELO proximity with vocabulary coverage (target 3–7% unknown words). This is the most pedagogically sound recommendation strategy. Consider making it the primary recommendation method rather than pure ELO proximity.

### Priority 2: Adaptive K-Factor

The static K=32 is a reasonable starting point, but the system could benefit from:
- Higher K for tests with more questions (more reliable signal)
- Lower K for tests with few questions (noisy signal)
- Score-dependent K adjustment (extreme scores like 0% or 100% suggest mismatched difficulty)

### Priority 3: Rating Confidence / Glicko-2

Standard ELO doesn't express uncertainty. A user with 2 tests and a user with 200 tests at the same rating have very different reliability. Glicko-2 adds a rating deviation (RD) that widens with inactivity and narrows with activity — this would naturally handle the volatility concern and provide better recommendation confidence.

### Priority 4: Mystery ELO Unification

Mysteries have their own `mystery_skill_ratings` table and `process_mystery_submission` RPC with a separate ELO calculation. The user's test ELO and mystery ELO are independent. Consider whether a unified skill model (with type-specific offsets) would provide better difficulty matching.

## Quantitative Impact Assessment

| Improvement | Dev Effort | User Impact | Data Risk |
|-------------|-----------|-------------|-----------|
| Vocab-ELO integration as primary | S (2–4h) | High — better pedagogical targeting | Low |
| Adaptive K-factor | M (4–8h) | Medium — more accurate ratings | Low |
| Glicko-2 migration | L (1–2d) | High — proper uncertainty modeling | Medium (schema change) |
| Mystery ELO unification | M (4–8h) | Low — improves mystery matching | Medium |

## Related Pages

- [[algorithms/elo-implementation-analysis.tech]] — Technical details with code references
- [[algorithms/elo-ranking]] — Original ELO system design
- [[algorithms/elo-ranking.tech]] — Original ELO technical specification
- [[database/rpcs.tech]] — Full RPC definitions
- [[features/comprehension-tests]] — Test submission flow
- [[decisions/ADR-001-dual-elo]] — Dual ELO decision record
