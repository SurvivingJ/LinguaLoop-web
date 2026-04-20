---
title: ELO System — Implementation Analysis & Improvements
type: algorithm
status: in-progress
tech_page: ./elo-implementation-analysis.tech.md
last_updated: 2026-04-11
open_questions:
  - "Should volatility multiplier be integrated into process_test_submission or kept as a separate concern?"
  - "Is Glicko-2 worth the complexity over standard ELO for this use case?"
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

## Critical Finding: Volatility Intentionally Removed in V2

The most significant discrepancy between documentation and code has a historical explanation:

**V1 (`migrations/elo_functions.sql`)** correctly called both `calculate_elo_rating()` and `calculate_volatility_multiplier()`, with an asymmetric K-factor (32 for users, 16 for tests) and text-based columns (`language`, `skill_type`).

**V2 (`migrations/process_test_submission_v2.sql`)** — the current live version — rewrote the function to add server-side answer grading. In the process, volatility was **dropped** and the ELO calc was inlined with symmetric K=32 for both user and test. The helper functions were not deleted from the database, creating the appearance of dead code that was actually intentionally disconnected.

The current V2 behaviour:
- Hardcodes `k_factor = 32` for both user and test (V1 used 16 for tests)
- Does not apply any volatility multiplier
- Ignores whether the user is new (<10 tests) or returning (>90 days inactive)

The consequence: new users' ratings move at the same speed as established users, making initial calibration slower than what V1 designed for. Whether this was a deliberate simplification or an oversight during the V2 rewrite is unclear.

### Test ELO Seeding

A backfill script (`scripts/backfill_test_skill_ratings.py`) seeds initial test ELO from difficulty level using a `DIFFICULTY_ELO_MAP` (difficulty 1→ELO 800, difficulty 5→1400, difficulty 9→2000 in ~150 ELO steps). This gives new tests a reasonable starting ELO that skips the cold-start convergence problem.

## Other Discrepancies

| Wiki Says | Code Does | Impact |
|-----------|-----------|--------|
| Volatility amplifies K for new/returning users | Volatility functions exist but are never called | Slow calibration for new users |
| `get_recommended_test()` excludes previously attempted tests | It does NOT exclude them — random within radius | Users may see repeated tests |
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

## What Needs Improvement

### Priority 1: Wire Up Volatility (bug fix)

The volatility system was designed to accelerate calibration for new and returning users. It's implemented in SQL but disconnected from the submission path. Fix: replace the inlined ELO calculation in `process_test_submission()` with calls to the existing helper functions.

### Priority 2: Exclude Attempted Tests in Single Recommendation

`get_recommended_test()` doesn't exclude previously attempted tests, meaning users can be recommended tests they've already taken. `get_recommended_tests()` correctly excludes them. The single-recommendation function should be made consistent.

### Priority 3: Vocabulary-ELO Integration

`get_vocab_recommendations()` already combines ELO proximity with vocabulary coverage (target 3–7% unknown words). This is the most pedagogically sound recommendation strategy. Consider making it the primary recommendation method rather than pure ELO proximity.

### Priority 4: Adaptive K-Factor

The static K=32 is a reasonable starting point, but the system could benefit from:
- Higher K for tests with more questions (more reliable signal)
- Lower K for tests with few questions (noisy signal)
- Score-dependent K adjustment (extreme scores like 0% or 100% suggest mismatched difficulty)

### Priority 5: Rating Confidence / Glicko-2

Standard ELO doesn't express uncertainty. A user with 2 tests and a user with 200 tests at the same rating have very different reliability. Glicko-2 adds a rating deviation (RD) that widens with inactivity and narrows with activity — this would naturally handle the volatility concern and provide better recommendation confidence.

### Priority 6: Mystery ELO Unification

Mysteries have their own `mystery_skill_ratings` table and `process_mystery_submission` RPC with a separate ELO calculation. The user's test ELO and mystery ELO are independent. Consider whether a unified skill model (with type-specific offsets) would provide better difficulty matching.

## Quantitative Impact Assessment

| Improvement | Dev Effort | User Impact | Data Risk |
|-------------|-----------|-------------|-----------|
| Wire up volatility | XS (1h) | Medium — faster calibration for new users | Low |
| Exclude attempted in single rec | XS (30min) | Medium — no repeated tests | None |
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
