---
title: ELO Ranking System
type: algorithm
status: in-progress
tech_page: ./elo-ranking.tech.md
last_updated: 2026-04-10
open_questions:
  - "Test recommendation algorithm needs refinement beyond expanding-radius random selection"
---

# ELO Ranking System

## Purpose

LinguaLoop uses a dual-ELO system where both users and tests have ELO ratings. This creates a self-correcting difficulty matching system: as users improve, they face harder tests. As tests are taken by many users, their difficulty rating adjusts to reflect actual difficulty.

## How It Works

### The Core Idea

ELO was originally designed for chess — rating two players against each other. LinguaLoop adapts this: the "players" are a learner and a test. When a learner takes a test, the result is treated like a match:

- **Learner wins** (high score) → learner's ELO rises, test's ELO falls
- **Learner loses** (low score) → learner's ELO falls, test's ELO rises

The amount of change depends on how surprising the result was. If a high-ELO learner aces an easy test, nothing much changes. If a low-ELO learner aces a hard test, both ratings shift significantly.

### Dual ELO

- **User Skill Ratings** — per language, per test type (reading, listening). Start at 1200.
- **Test Skill Ratings** — per test, per test type. Start at 1400.

### Volatility

New users and returning users (>90 days since last test) have a volatility multiplier that amplifies ELO changes. This lets the system calibrate faster when data is sparse.

- Fewer than 10 tests taken → +0.5 volatility
- More than 90 days since last test → +0.5 volatility

### Test Matching

Tests are recommended based on ELO proximity. The system uses an expanding-radius search:
1. Look for tests within ±50 ELO of the user → if found, pick randomly
2. Expand to ±100, then ±250, then ±500, then ±10000
3. Exclude previously attempted tests
4. Respect tier access (free vs. premium)

## Constraints & Edge Cases

- All ELO ratings clamped to [400, 3000].
- Default K-factor: 32 (standard chess value).
- Score is fractional (0.0 to 1.0): percentage correct, not binary win/loss.
- First attempt is distinguished from re-attempts for analytics.

## Business Rules

- ELO updates are atomic within test submission (single DB transaction).
- A user has separate ELO ratings for reading and listening in each language.
- Tests also have per-type ELO ratings.

## Related Pages

- [[algorithms/elo-ranking.tech]] — Formula, parameters, implementation
- [[features/comprehension-tests]] — Where ELO is applied
- [[features/vocabulary-knowledge]] — BKT and ELO work together
