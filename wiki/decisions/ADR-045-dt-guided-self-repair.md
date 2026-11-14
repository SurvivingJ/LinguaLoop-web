---
title: "ADR-045: Dual Translation feedback is guided self-repair (design option 2)"
status: accepted
date: 2026-11-14
---

# ADR-045: Dual Translation feedback is guided self-repair (design option 2)

Status: **accepted** (owner, 2026-11-14: "the guided process in mockup two is the way to go").
Built and integration-tested the same day ([[tasklist/dt-guided-self-repair.tasks]] TASK-952–969).
**Not live:** `migrations/dt_guided_self_repair.sql` is written but not applied (owner decision
pending, TASK-966) and the branch is not deployed (TASK-974). Until both happen every learner sees
today's result view — the submit hook detects the missing tables and steps aside.

## Context

The single-call grader ([[decisions/ADR-044-dt-single-call-generative-grader]]) gives, for each
error, the sentence it is in, a located learner span, the error type, a confidence, a local
correction and an L1 explanation, cheaply (~$0.0001, ~1.4 s per call). The old result screen showed
the full correction at once — diff, corrected forms and explanations — so the learner reads an
answer instead of retrieving one. Three feedback designs were drawn up in
[[evaluations/dt-decision-grading-2026-11-14]] (`wiki/design/dt-feedback/option-1-focused-correction`,
`option-2-guided-self-repair`, `option-3-pattern-coach`).

## Decision

After a DT submission whose grade came from the single-call grader, each flagged sentence becomes
one step in a full-screen pop-up: the learner edits their own sentence, may ask for help one rung at
a time (where → what kind → a clue → the answer), and each revision is re-checked. Sentences not
fixed unaided come back in daily practice. The key architectural decisions (detail in
[[features/dt-guided-self-repair.tech]] §12):

1. **The answer is withheld by the server, not hidden by the client.** While a repair session is
   open the submit response is redacted (scores and counts only); hints are rendered server-side;
   the reference sentence, corrected forms and explanations arrive only in the reveal (or the
   closing check) of their own sentence; the full contract is served by a separate endpoint after
   the pass is finished.
2. **The re-check is the single-call grader on one sentence pair** — same prompt, schema and
   decoder as grading, primary model only, 5 s timeout. "Fixed" = the target error is gone and no
   new major/critical error appeared; a valid alternative counts as repaired.
3. **Hints come from a versioned template file**, not from the model and not from the taxonomy
   row: Track D measured 0% leaks for templates against 9–40% for model-written hints, and hint copy
   must not bump the grading taxonomy. A leak filter guards the clue.
4. **One step per sentence, on its most serious error**; at most three hinted steps per pass;
   five or more flagged sentences (or any dimension at band 1) bypass the pass.
5. **Daily practice uses new tables with fixed intervals**, served as one `dt_repair` block in the
   existing daily-session queue; the FSRS-based `dt_card` remediation is left as it is.
6. **Separate blueprint and service package**, with a two-call hook in the submit route; the
   feature flag `DT_GUIDED_REPAIR` defaults on, and every grade that is not eligible (not a
   single-call grade, flag off, tables missing, any hook error) falls back to today's result view.
7. **Store offsets, not sentence copies**; successful re-checks are logged only in
   `dt_repair_event`.

Integration (WP-INT) added to the contract: per-step `l1` / `l2`, a whole-passage prompt fallback
on daily items, `back_later` on the calls that close a daily sitting (there is no daily "finish"),
`where: null` on closed steps, the reload-resume stash on the DT page, page pinning under the sheet,
and once-per-process detection of the missing tables.

## Consequences

- Easier: the learner retrieves before reading; every hint level, revision and outcome is recorded
  per sentence for later tuning; the grade itself never changes.
- Harder: a feedback screen now costs up to six extra model calls per sentence per sitting (capped
  per sitting, per day and by tokens); three new tables to retain (≈ 2.3 KB per graded submission;
  retention job needed at ~1,000 submissions/day); the frontend depends on a redacted/full contract
  pair and must never render the redacted one.
- Constrained: the flow only exists for single-call grades; hint templates must stay leak-free and
  within length limits; the zh/ja templates and UI strings are unreviewed (TASK-972); the re-check
  was not measured on real revisions (TASK-973); every threshold is a design default.

## Alternatives Considered

- **Option 1 — focused correction** (one error promoted to a "Fix this first" card with the original
  sentence, a one-line reason and an edit-and-check box; the rest collapsed): shows less than the
  grader knows on purpose; one repair per submission instead of one per flagged sentence.
- **Option 3 — pattern coach** (short per-translation feedback with the reference shown at once;
  the product is the cross-translation pattern profile on top of `dt_error_profile_entry` /
  `dt_card`): the answer is on screen immediately, and its patterns need per-type accuracy the
  grader has only shown on 30 seeded items per language. Not chosen by the owner; its pattern
  tracking can later be built on the per-sentence episodes option 2 records.
- **Hiding the answer in the client** (send the full contract, show it step by step): the answer
  would sit in devtools and in the `dt_feedback_view` localStorage stash.
- **Re-grading the whole passage on every check, or a new short "is it fixed?" prompt**: ×n cost and
  other sentences could change verdict; an unmeasured prompt and a yes/no model is the design the
  grading experiment rejected.
- **Model-written hints**: 9–40% leaked the answer in Track D.
- **Daily practice as a new `dt_card` type**: FSRS ratings do not express the hint-level rules, and
  the `card_type` CHECK would need a destructive change.
- **A third correction-style A/B arm**: a destructive constraint change and an A/B the owner did
  not ask for (open question on the prose page).

## Related Pages
- [[features/dt-guided-self-repair]] · [[features/dt-guided-self-repair.tech]]
- [[tasklist/dt-guided-self-repair.tasks]]
- [[decisions/ADR-044-dt-single-call-generative-grader]]
- [[evaluations/dt-decision-grading-2026-11-14]]
- [[features/dual-translation.tech]]
