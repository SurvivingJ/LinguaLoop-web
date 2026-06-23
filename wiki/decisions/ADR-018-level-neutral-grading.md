---
title: "ADR-018: Level-Neutral Grading (difficulty controlled at selection)"
status: accepted
date: 2026-06-23
---

# ADR-018: Level-Neutral Grading (difficulty controlled at selection)

## Context
Dual Translation grades a reproduction against a fixed gold L2 reference. We must decide whether
the grade should be **level-dependent** (expectations relaxed for lower age tiers) or
**level-neutral** (measured against the gold at face value). A key fact resolved on 2026-06-23:
passages are served only from tests the learner has **already completed** (reading/listening/
dictation), so the content is inherently at the learner's level — difficulty is controlled at
*selection time*, not at grading time.

## Decision
Grade **level-neutral**: rubric bands are scored against the gold at face value, and error
detection + explanation are identical at every tier (an omitted particle is an error for a
beginner and an advanced learner alike, and the explanation of *why* is never softened). The
**only** level-dependent behaviour is the `naturalness` dimension: de-emphasized at all tiers and
**hidden entirely at the lowest age tiers (1–2)** to avoid demotivation (Munro & Derwing; report).

## Consequences
- **Honest signal:** the grade reflects real performance against the standard; no per-tier leniency
  to calibrate or game.
- **Simpler pipeline:** no tier-conditional scoring logic except the `naturalness` visibility gate.
- **Relies on selection:** correctness depends on the selection rule actually serving at-level
  (completed-test) content — if that breaks, beginners could face out-of-level passages. The
  selection rule is therefore part of this decision's contract.
- **Band descriptors per age tier still exist** (they shape the model's calibration few-shots), but
  they describe the *content* level, not a grading curve.

## Alternatives Considered
1. **Level-dependent (lenient) grading.** Relax expectations for lower tiers. Rejected: difficulty
   is already controlled at selection, so a second leniency layer would double-count and obscure
   the true signal.
2. **Fully level-neutral including naturalness.** Rejected: over-penalising nativeness at beginner
   tiers demotivates without improving communication (the report's core caution).
