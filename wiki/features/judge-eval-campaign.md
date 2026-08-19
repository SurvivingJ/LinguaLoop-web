---
title: Judge Evaluation Campaign System
type: feature
status: planned
tech_page: judge-eval-campaign.tech.md
last_updated: 2026-08-17
open_questions:
  - "OPEN: Dataset size — 1000 labelled items (~334 questions) or 1000 questions (3x the call budget)? Recommendation: 1000 items."
  - "OPEN: Candidate count — 200 models as originally requested, or ~40 well-chosen candidates plus human adjudication of ~100 gold items? Recommendation: 40 + adjudication."
  - "OPEN: Sequencing — build before or after TASK-723's 1-5 Likert migration? Likert invalidates the threshold and score-distribution metrics. Recommendation: after."
---

# Judge Evaluation Campaign System

## Purpose

Turn the one-off answer-entailment A/B (run manually on 2026-08-17, 7 arms) into a
repeatable system that can screen many candidate models for a judge role and
present the outcome as a report a human can act on.

**Status: deferred 2026-08-17.** The design is recorded here so it can be picked
up without re-deriving it. Nothing has been built.

## Why this was wanted

Choosing a judge model is currently a manual, expensive, memory-bound exercise.
The 2026-08-17 run ([[evaluations/entailment-judge-model-ab-2026-08-17]]) proved
the *method* works — gold-labelled scoring separates good judges from bad ones,
and it caught three models that fail in ways no benchmark table would reveal. But
it took a full session to run seven models, and the knowledge of which models are
broken lives in a session transcript rather than in the repo.

The ask was to scale that to ~200 models with a consistent dataset and an HTML
report.

## How it would work

A learner never sees any of this; the audience is whoever is choosing a model.

1. **A frozen gold dataset.** One committed file of passages, questions, correct
   answers and distractors, stratified across the three languages and across
   question types. Frozen means content-hashed and versioned: two runs a month
   apart score identical inputs, so any difference is the model's doing and not
   the sample's. A slice is held back and never used during screening.

2. **A cheap gate before any spending.** Each candidate gets a handful of probe
   calls first, checking it can be reached, will honour JSON mode, returns the
   expected shape, and is not silently failing. Models that fail are recorded in
   a cache so future runs skip them — the system remembers what is broken.

3. **A funnel, not a flat sweep.** Survivors are screened on a small slice of the
   dataset, which is enough to reject weak models but not to separate strong ones.
   Only the leaders are then run on the full dataset. This is what makes ~200
   candidates affordable in hours rather than days.

4. **A report.** A single self-contained HTML page: a leaderboard, per-language
   accuracy and error rates with confidence intervals, whether each model uses
   enough of the confidence scale to be re-tunable later, measured cost per call,
   and what died at which stage of the funnel and why.

The operator can either name the models to test or let the system pick them from
OpenRouter's catalogue within price and context limits.

## Constraints & Edge Cases

* **A flat sweep is not executable.** 200 candidates × 1000 items is 200,000
  calls — roughly 35 hours at the concurrency the existing harness uses. The
  funnel cuts this to about 4.5 hours and ~$13.
* **List prices do not predict cost.** Measured spend on 2026-08-17 diverged from
  list-price expectations by up to 4.8×, because output-token volume dominates
  this workload. Only measured cost counts.
* **Some models fail invisibly.** One candidate returned empty content on 47% of
  calls; in production every one of those would have become a silent
  accept-everything no-op. Live probing is the only way to find this.
* **Long runs must survive interruption.** A multi-hour campaign has to
  checkpoint and resume, or one crash wastes the whole spend.
* **Rate limits are real.** A per-model concurrency cap is needed; a single global
  pool trips per-provider limits.

## Business Rules

* No campaign may spend without first printing a projected cost, and a budget
  ceiling must **fail closed** when cost data is missing rather than treating it
  as zero. A missing-cost value silently disarmed every budget ceiling in this
  repo before 2026-08-12.
* The frozen dataset is never regenerated in place. A new sample is a new version.
* The held-out slice is only ever used to confirm the final two or three
  candidates, never during screening.

## Open Questions

See frontmatter. All three are genuine decisions with material cost consequences,
and all three are unresolved.

## Why it was deferred

Two reasons, both recorded on 2026-08-17:

1. **More candidates would not have changed the answer.** On zh the top four
   models sat within 0.01 AUC of each other, all ≥0.987. That language is
   saturated; screening 200 models measures a ceiling more precisely rather than
   raising it. The binding constraint is **label quality**, not candidate count —
   the labels are structural rather than human-checked, so every accuracy figure
   is a lower bound. Human-adjudicating a hundred items would buy more confidence
   than two hundred more models.
2. **TASK-723 would invalidate part of it.** Moving all judges to a 1–5 Likert
   scale retires the threshold logic and the score-distribution check, which are
   two of the six proposed metric components. Building first means reworking them.

## Related Pages

- [[features/judge-eval-campaign.tech]] — technical specification
- [[evaluations/entailment-judge-model-ab-2026-08-17]] — the manual run this generalises
- [[tasklist/distractor-judge-calibration.tasks]] — TASK-723 Likert unification, the sequencing dependency
- [[features/comprehension-tests]] — the pipeline the entailment judge guards
