---
title: Test Tier Assignment
type: feature
status: complete
tech_page: test-tier-assignment.tech.md
last_updated: 2026-09-27
open_questions:
  - "OPEN: do the human-checked tiers agree with the two model readers used to calibrate ja and zh? (T5, and T3 in English, have almost no examples.)"
  - "OPEN: should a test whose assigned tier is two or more tiers from its target be flagged for review?"
---

# Test Tier Assignment

## Purpose
Every comprehension test has an age tier from T1 (a 4–5 year old) to T6 (an educated
professional). The tier decides which learners are offered the test, how its ELO starts, and
what mix of questions it carries. It is now measured from the finished passage rather than
inherited from the topic it was written for.

## User Story
A learner picking or being served a test needs its level to mean something. A "toddler-level"
test that reads like a policy paper, or a "professional" one that reads like a children's
story, wastes their time and distorts their rating.

## How It Works
1. A passage is written aimed at the topic's target tier.
2. An automatic classifier (jev, a fast structured-decision model) reads the finished passage
   in its own language and places it on the six-tier scale, using the same tier descriptions
   the writers use.
3. The classifier's raw answer is converted to a tier with a small per-language table. ja and
   zh use tables calibrated against passages labelled blind by two independent readers; English
   uses plain rounding because nothing beat it.
4. The assigned tier, not the target, decides the stored tier, the test's legacy difficulty
   number, its starting ELO, its question mix and whether the quality judges run.
5. The raw answer, its confidence and which table was used are stored with the test, so the
   tier can be audited or recomputed later without asking the classifier again.
6. New topics are also checked: a topic whose vocabulary assesses harder than the tier it was
   written for is rejected.

## Constraints & Edge Cases
- **A test's tier can differ from its topic's tier.** That is intended: the passage is what
  the learner reads.
- **No guessing.** If the classifier cannot be reached after retries, no test is written and
  the queue item is marked failed so it can be retried.
- **Existing tests were re-tiered once** (2026-09-26/27). Their ELO was not reset: it is
  empirical for the 54 tests with attempts, and not tier-anchored for the rest.
- **Dictation eligibility can change** for a test that moves down a tier (its transcript may
  exceed the lower tier's length cap).
- **Small calibration samples.** A new ja or zh test near a tier boundary can still land one
  tier off.

## Business Rules
- The tier of a stored test is always the tier assigned by the classifier from its passage.
- Tier, legacy difficulty and the tier bands stay in step (difficulty is derived from the tier
  and never the other way round).
- A calibration change is applied by re-deriving tiers from stored raw scores; it never
  silently rewrites past decisions without a recorded calibration label.

## Open Questions
- OPEN: human check of the calibration labels.
- OPEN: flag large target-versus-assigned gaps for review.

## Related Pages
- [[features/test-tier-assignment.tech]]
- [[decisions/ADR-029-jev-tier-assignment]]
- [[evaluations/jev-tier-calibration-2026-09-27]]
- [[evaluations/jev-judge-feasibility-2026-09-26]]
- [[algorithms/elo-ranking]]
