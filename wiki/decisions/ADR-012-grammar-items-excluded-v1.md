---
title: "ADR-012: Grammar / Style / Collocation Items Without sense_id Excluded from V1 Practice Pool"
status: accepted
date: 2026-05-21
---

# ADR-012: Grammar / Style / Collocation Items Without sense_id Excluded from V1 Practice Pool

## Context

The Practice Engine merger ([[decisions/ADR-007-merge-exercises-vocab-dojo]]) introduces a unified score that ranks every candidate item. Two terms in that score — `ladder_priority` and `fsrs_urgency` — are computed *per sense*: they require `exercises.sense_id IS NOT NULL`.

Some exercise rows in the `exercises` table do not have a `sense_id`:
- `source_type = 'grammar'` — exercises about a grammatical pattern, not a specific word.
- `source_type = 'style'` — register/formality drills, often spanning many words.
- `source_type = 'collocation'` — some collocation exercises link to a *pair* of senses via a bridge table rather than a single `sense_id`.

V1 has three options:
1. **Include them, with fallback constants** for ladder/FSRS terms (e.g. `ladder_priority = 0.20` flat, `fsrs_urgency = 0.20` flat).
2. **Include them via an `exercises ↔ senses` bridge table** — route grammar items to Acquisition when they link to a ladder-active word.
3. **Exclude them entirely from V1.** Only rank items where `sense_id IS NOT NULL`.

The bridge table (option 2) is the right long-term answer but doesn't exist yet at production-data quality — `corpus-analysis` extracts collocations but the bridge to `exercises.id` is partial. Including grammar items with fallback constants (option 1) means the IRT + BKT terms drive scoring for those items; this is reasonable for grammar but means a learner can get grammar drills they have no interest in, ranked above word-anchored drills the ladder thought were prioritized.

## Decision

**V1 excludes** exercises with `sense_id IS NULL` from both Acquisition and Maintenance candidate pools. The unified-score SQL filters `WHERE e.sense_id IS NOT NULL` before ranking.

This affects roughly 20% of the current `exercises` table (rough estimate; auditable via `SELECT COUNT(*) FROM exercises WHERE sense_id IS NULL GROUP BY source_type`). Those items remain in the table but are unreachable via the merged Practice surface in V1. They remain reachable via direct admin tools and the (unmerged-yet) language-pack study UI.

V2 recovers them via the `exercises ↔ senses` bridge: a grammar exercise that the bridge says "exemplifies sense_id X" inherits the ladder_priority/fsrs_urgency of X for scoring purposes, with a small dampener to avoid over-recommending non-word-anchored items inside Acquisition mode.

## Consequences

- **Easier:** SQL stays simple — one `WHERE sense_id IS NOT NULL` predicate. No fallback constants, no bridge join, no debate over whether a grammar item should rank above a word-anchored one.
- **Easier:** Acquisition mode is strictly word-anchored, which matches the Dojo philosophy preserved by ADR-007.
- **Harder:** A real chunk of the content library is dark in V1 Practice. Acceptable for V1 because the library is large enough that word-anchored items already exceed the time learners spend.
- **Harder:** A learner who specifically wants grammar drills has no Practice entry to them in V1; they can still find them via the language-pack flow.
- **Constrained:** This decision is reversible: V2 can flip the predicate to include `sense_id IS NULL` items with fallback constants in a single migration + RPC update, without any data backfill.

## Alternatives Considered

1. **Include with fallback constants `ladder_priority = 0.20`, `fsrs_urgency = 0.20`.** Rejected for V1 — without the bridge, these items would dilute Maintenance and confuse Acquisition. Reconsider in V2 if telemetry shows learners actively miss them.

2. **Include only in Maintenance, exclude from Acquisition.** A compromise. Rejected — Maintenance ranking would then have two non-comparable item classes (sense-linked with full unified-score signals vs grammar with flat constants), making the score-breakdown debugging harder.

3. **Build the bridge table now as part of V1.** Rejected as scope creep — the bridge is a non-trivial corpus-analysis change with its own validation. V1 ships the orchestrator + merger; V2 expands the pool.

## Related Pages

- [[features/practice-engine.tech]] — Candidate-pool SQL with the `WHERE sense_id IS NOT NULL` predicate.
- [[algorithms/practice-unified-score.tech]] — Term definitions assume `sense_id IS NOT NULL`.
- [[decisions/ADR-007-merge-exercises-vocab-dojo]] — Parent decision that this constrains.
- [[features/corpus-analysis]] — Where the V2 bridge table will originate.
