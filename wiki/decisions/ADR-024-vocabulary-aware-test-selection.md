---
title: "ADR-024: Vocabulary ranks test candidates; difficulty stays ELO-mediated"
status: proposed
date: 2026-09-08
---

# ADR-024: Vocabulary ranks test candidates; difficulty stays ELO-mediated

## Context

Test selection (`get_recommended_tests`) ranks candidates solely by
`ABS(test_elo - user_elo)`. It never filters on `tests.difficulty`, never reads
`tests.vocab_sense_ids`, and never consults `user_vocabulary_knowledge`. The
reported symptom is "Japanese tests are too hard".

A live audit on 2026-09-08 (27 Japanese attempts, 21 first attempts) found the
symptom real but the cause compound:

1. **Test ELO is test-type-blind.** 48 of 60 Japanese tests carry an identical
   ELO across all 8 test types, because TASK-732 seeded from prose complexity,
   which cannot know whether the task is reading, dictation or pitch accent.

2. **The rating system compresses ability roughly 5×.** Inverting the Elo
   expectation per attempt, this learner's true ability spans **448 points**
   (pitch accent ~1091, dictation ~1539) while the system has them in an
   **88-point** band (1182-1270). Reading, listening and dictation are all
   *under*-rated; only pitch accent is over-rated. So Japanese is mostly too
   *easy* — but pitch accent, with 6 of 7 attempts below 50%, dominates how it
   feels.

3. **ELO cannot close the gap even in principle.** Multiple-choice scores have a
   chance floor. The Elo equilibrium gap is `400·log₁₀(1/s − 1)`, which at a 25%
   floor is **−191 points**: a learner who knows nothing still settles ~190
   below the pool and no further. With Japanese difficulty-1 tests rated ~1240,
   the learner is pinned near 1050-1240 whatever they do — and each attempt
   moves them only 2-10 points anyway.

Meanwhile the signal ELO lacks is already stored and ignored. Share of a test's
senses this learner knows: **73% at difficulty 1, 17% at difficulty 6, 9% at
difficulty 9.**

Two facts constrain any fix:

- `vocab_sense_ids` coverage is ja 59/59, en 100/121, zh 98/125 — so **17-22% of
  English and Chinese tests have no vocabulary link at all.**
- At difficulty 9, only **10.3%** of a test's senses have any
  `user_vocabulary_knowledge` row. The other 90% are *untested*, not *unknown*.

## Decision

**1. Vocabulary coverage becomes a ranking term, never a filter.**
Candidates are scored on distance from a target unknown-word rate and combined
with the ELO distance:

```
score = w_elo·|test_elo − user_elo|/400 + w_vocab·|unknown(t) − u*|/u_tol
```

A test with no usable vocabulary link receives the **median penalty of its
candidate cohort** — "no opinion" — rather than 0 (which would make unlinked
tests always win) or `+∞` (which would silently empty the pool for a fifth of
the catalogue).

**2. Untested senses get a frequency prior, not a zero.**
`P_known(s)` is the BKT `p_known` where a row exists, else
`σ(1.5·(zipf(s) − ability_zipf))`. Without this the term is degenerate — 90% of
difficulty-9 senses would read as unknown and every unseen test would score
identically at the bottom, getting worse as the catalogue grows.

**3. Difficulty and tier do NOT become a filter.** Ranking stays ELO- and
vocabulary-mediated. The single exception is a safety rail: when a calibration
row exists, exclude candidates more than 2 tiers above the learner's calibrated
tier. That is an eligibility guard against the pathological case (an
840-character difficulty-9 dictation on day one), not a selection mechanism, and
it excludes nothing when calibration is absent.

**4. Calibration seeds ratings under hard guards; it never overrules history.**
Below 5 attempts it writes the mapped ELO directly. Above 5 it writes only on a
disagreement wider than 200 points, and then moves by at most
`min(0.25·diff, 150)`, at most once per week, never within an hour of a test
attempt, clamped to the ladder's [875, 1925]. Every decision — including every
skip and its reason — is appended to `user_skill_rating_adjustments`.

**5. `process_test_submission` is not modified.** The two writers of
`user_skill_ratings.elo_rating` are separated by temporal guards rather than by
editing a function whose live body has already drifted from the repo.

## Consequences

**Easier**
- Selection uses measured vocabulary instead of a rating that cannot express the
  gap. The 73/17/9% gradient is far cleaner than the ELO ranges.
- Cold start is solved without making the learner grind through mismatched tests.
- `vocab_weight = 0` reproduces today's ranking exactly, so rollback is a
  one-row `UPDATE`, not a migration.
- Every rating write becomes auditable — today's are not.

**Harder**
- `get_recommended_tests` gains CTEs over `unnest(vocab_sense_ids)`,
  `user_vocabulary_knowledge` and `dim_vocabulary`. Cheap at ≤125 tests per
  language; needs a materialised view past ~10k.
- Two rating writers now exist. The guards are the contract; if either side
  changes, the guards must be re-verified.
- The target `u* = 0.15` is an interim. The 3-7% the dropped
  `get_vocab_recommendations` aimed at is **unreachable** against live content —
  the best available is 27% unknown at difficulty 1 — so the constant is a
  tunable row, revisited as coverage improves.

**Constrained**
- Vocabulary may never remove the last candidate from a pool. Pool count per type
  is a shipped regression metric (M5).
- `frequency_rank` is a **Zipf score, higher = more common**. Reading it as a
  rank inverts every ordering that touches it.
- No fourth copy of the tier→ELO bands: the anchor table lives in SQL only,
  derived from `dim_complexity_tiers` at call time.

**Known limit, stated up front**
- Better selection cannot fix pitch accent on its own, because the type-blind
  test ELO is a *content seeding* defect. Expect the primary metric to move for
  reading, listening and dictation first, and for pitch accent only after a
  per-type ELO reseed. If pitch accent does not move, that is the predicted
  result, not a failed rollout.

## Alternatives Considered

**Hard filter on unknown-word rate (the dropped RPC's shape).** Rejected: it
empties the candidate pool for the 17-22% of en/zh tests with no vocabulary
link, and the 3-7% band it targeted is unreachable against live content.

**Filter on `tests.difficulty` directly.** Rejected: it recreates the cold-start
trap one level up — you need the learner's difficulty level, which is the
unknown. And the label does not separate the content: live Japanese ELO ranges
overlap heavily (d1 1112-1430, d6 1330-1545), so filtering on the label would
discard measured signal in favour of an authoring guess.

**Raise the ELO K-factor so ratings converge faster.** Rejected: it cannot work.
The chance floor caps the reachable gap at ~190 points regardless of K; a larger
K only adds variance to a fixed point that is in the wrong place.

**Rebuild selection on IRT, retiring ELO.** Rejected as disproportionate now —
21 first attempts from one learner is not an IRT dataset. The vocabulary term is
a step toward it and the audit table accumulates exactly what a later fit needs.

**Reuse `get_vocab_recommendations`.** Not possible — dropped at
`migrations/drop_unused_rpcs.sql:24`, and it depended on the legacy
`user_vocabulary.known_sense_ids` array. The *idea* is reused; the
implementation is rebuilt on `user_vocabulary_knowledge`.

**Add `p_vocab_weight` as a defaulted function parameter.** Rejected: the repo
already carries `get_recommended_tests_drop_ambiguous_overload.sql` cleaning up
exactly this. A settings row also allows rollback without re-applying a
migration.

## Amendment — 2026-09-10 (implementation, TASK-744–752)

Implemented and applied live, with `selection_tuning.vocab_weight = 0`, i.e.
**switched off**; turning it on is an operator decision after the shadow window.
Three points differ from the text above:

1. **Decision 2, the prior is 0.85 at `ability_zipf`, not 0.5:**
   `σ(1.5·(zipf − ability_zipf) + ln(0.85/0.15))`. `ability_zipf` is the 85%
   crossing, so the original form mis-stated the contract it depends on.
2. **Decision 2, the no-calibration fallback** is the Zipf at which the
   learner's own `user_vocabulary_knowledge` known-share crosses 85%, not a
   median of known senses; neutral when not identifiable.
3. **Decision 3, the tier ceiling demotes, it does not exclude.** An
   over-ceiling candidate ranks after every within-ceiling one. Exclusion would
   break the Constrained clause below ("vocabulary may never remove the last
   candidate from a pool") whenever fewer than 10 within-ceiling candidates
   exist.

Details: [[features/vocabulary-aware-test-selection.tech]] §3.2 and §4,
[[tasklist/vocabulary-aware-test-selection.tasks]].

## Related

- [[features/vocabulary-aware-test-selection]] · [[features/vocabulary-aware-test-selection.tech]]
- [[decisions/ADR-001-dual-elo]] — the rating system this supplements
- [[decisions/ADR-002-bkt-per-sense]] — origin of `p_known`
- [[decisions/ADR-003-age-tiers]] — the tier ladder reused for the ELO map
- [[decisions/ADR-006-retry-slot-reduced-elo]] — the other damped ELO writer
