---
title: "ADR-001: Dual ELO Rating System"
status: accepted
date: 2026-04-10
---

# ADR-001: Dual ELO Rating System

## Context

LinguaLoop needs to match learners with appropriately difficult tests. A static difficulty rating (1-9) is too coarse — the same test might be easy for one learner and hard for another. We need a system that adapts to actual usage data.

## Decision

Implement a dual-ELO system where both users and tests have ELO ratings. When a user takes a test, the result is treated as a "match" between the user's skill and the test's difficulty. Both ratings update according to the standard ELO formula with a K-factor of 32 and configurable volatility.

User ratings are tracked per-language and per-test-type (reading, listening). Tests also have per-type ratings.

## Consequences

- **Easier:** Automatic difficulty calibration — no manual difficulty tagging needed beyond the initial seed rating.
- **Easier:** Test recommendations improve automatically as more data accumulates.
- **Harder:** New tests start at a fixed ELO (1400) and need several attempts before their rating is accurate.
- **Harder:** Users who only take easy/hard tests may have inaccurate ELO until they test across the spectrum.
- **Constrained:** ELO assumes each test is an independent event. It doesn't account for vocabulary overlap between tests.

## Alternatives Considered

1. **Static difficulty only** — simpler but doesn't adapt. Rejected because difficulty perception varies by learner.
2. **IRT (Item Response Theory)** — more sophisticated. Deferred as a future enhancement (IRT parameters are already stored on exercises for future use).
3. **Glicko-2** — better handling of uncertainty. Rejected for complexity; current volatility multiplier provides a simpler approximation.
