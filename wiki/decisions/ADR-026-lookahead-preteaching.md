---
title: "ADR-026: Pre-teach the vocabulary that blocks the next tests, from a pool, to Ring 2"
status: accepted
date: 2026-09-19
---

# ADR-026: Pre-teach the vocabulary that blocks the next tests

## Context

[[decisions/ADR-024-vocabulary-aware-test-selection]] made test selection read
vocabulary knowledge and prefer tests near a target unknown-word share `u*`. It
works, but it is a *search* strategy, and the search space is exhausted: on live
Japanese the least-unknown test available to our one real learner is still 27%
unknown, so the original 3–7% target was unreachable and even `u* = 0.15`
required settling.

The practice engine ([[features/practice-engine]], ADR-007) is meanwhile a
parallel activity with its own intake, unconnected to what the learner is about
to be tested on. Live, it is close to dormant: 15 `exercise_attempts` ever
against 54 `test_attempts`, and all 47 subscribed ladder words still in state
`new`.

The question this ADR settles: instead of searching harder for a test the
learner is ready for, can the practice engine **make** them ready — and if so,
which of the plausible designs?

A variant simulation over the live catalogue
([[evaluations/preteach-variants-2026-09-19]]) measured three axes: what to
target (one test / a pool / the catalogue), how deep to teach before the test
(Ring 1 / Ring 2 / mastery), and which words first (frequency / frontier /
least-known).

## Decision

**Adopt lookahead pre-teaching as `a2_cohort + b2_working + c3_greedy`, behind a
switch that ships off, and treat demand-first exercise generation as its
critical path.**

1. **Target a pool, not a test.** Each cycle derives a cohort of ~12 words from
   the vocabulary *shared* across the ten tests the recommender would serve
   next. Measured at ~1.7 words per test brought into band, against 17.8 for
   pinning a single test.
2. **Teach to Ring 2 cleared.** Recognition-only preview puts 36% of the ja
   catalogue in band; Ring 2 puts 98%; mastery adds nothing for 66% more time.
3. **Rank by pool demand, breaking ties least-known-first.** `greedy` won at
   every bounded budget; `frontier` remains a one-row switch, not a discard
   (see Consequences).
4. **The coupling is advisory.** Pre-teaching adds a tiebreak to
   `build_daily_session`'s hydration `ORDER BY`. It never withholds a test, never
   changes the budget solver, and never blocks a learner who asks for content
   directly.
5. **`preteach_enabled` ships at 0.** On today's inventory the feature would
   produce cohorts of one or two words.
6. **Re-point exercise generation from frequency-first to demand-first.** This is
   the decision that actually changes learner outcomes; items 1–5 are how the
   capacity gets used once it exists.

## Consequences

**Easier.** The unknown-word target becomes something the system can *reach*
rather than search for — the reason `u* = 0.15` was a settlement disappears.
Practice acquires a purpose the learner can feel: these words are for the tests
coming this week. The starved-nomination signal that already exists in
`practice_session_service` finally has somewhere to go.

**Harder.** The day now has a temporal structure it did not have. The ladder's
cross-session gate (first-attempt successes on ≥2 distinct calendar days) makes
three days the floor for a cohort — pre-teaching cannot be a same-session
feature, and a learner who studies once a week gets far less from it.

**Newly constrained.**
- `target_new_rate` (`daily_minutes // 6` per week, i.e. 5 words/week at 30
  min/day) is now inconsistent with a 12-word cohort on a 10-day deadline. One
  of the two numbers must move; this ADR does not decide which.
- **Evaluation is constrained more than anything else.** `p_known` is written
  *from* test results, so unknown share measured after an attempt is
  contaminated by that attempt. Measured: the as-of Spearman is −0.584, while
  recomputing from current `p_known` on the same 21 attempts gives +0.107 — the
  sign inverts. Every measurement of this feature must use snapshots taken at
  release. This is recorded in the schema as `unknown_at_open` /
  `unknown_at_close` rather than left to analyst discipline.

**Known to be unsettled.** `c3_greedy` won on arithmetic that charges every word
the same practice cost regardless of how well it is already known — an
assumption BKT contradicts. `c2_frontier` may be the better default in reality.
Shipping `greedy` as a tunable row rather than a constant is the whole mitigation.

## Alternatives Considered

- **`a1_commit` — pin one specific test and teach its vocabulary.** The obvious
  reading of "prepare the learner for the test". Rejected: ~10× more words per
  test brought into band, because nothing amortises, and it forces a commitment
  to a specific test days before the learner has earned it.
- **`a3_demand` — ignore upcoming tests, teach the highest-demand words
  catalogue-wide.** Rejected: needs 500 words to put 68% of ja in band, versus
  15 words for 90% of the pool. It is, however, exactly the right ranking for
  *generation* (see item 6), which is where it was adopted instead.
- **`b1_preview` — a cheap recognition-only "tomorrow's words" screen.**
  Rejected: 36% vs 98% in band. It is not a cheaper version of this feature, it
  is a version that does not work.
- **Withholding un-prepared tests (a hard gate).** Rejected for the same reason
  ADR-024 rejected a hard vocabulary filter: with zh currently at *zero*
  ladder-drillable blocking words per test, a locking design serves that learner
  nothing at all. A content shortage must degrade to today's behaviour, not to
  an empty app.
- **Raising `w_vocab` / turning on `combine_mode` instead.**
  [[evaluations/selection-three-arm-replay-2026-09-17]] already showed the
  vocabulary term is worth a lot (0.79 → 0.95 in-band) and the multiplicative
  combination worth nothing. But both operate on the same fixed catalogue.
  Selection redistributes what exists; pre-teaching changes what the learner
  brings to it. They are complements, and neither was rejected in favour of the
  other.

## Related Pages

- [[features/lookahead-preteaching]] / [[features/lookahead-preteaching.tech]]
- [[evaluations/preteach-variants-2026-09-19]]
- [[decisions/ADR-024-vocabulary-aware-test-selection]]
- [[decisions/ADR-007-merge-exercises-vocab-dojo]]
- [[decisions/ADR-005-momentum-bands]]
