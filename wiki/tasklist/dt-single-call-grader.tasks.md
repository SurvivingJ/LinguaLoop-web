---
title: "DT Single-Call Grader (ADR-044) — Task Breakdown"
feature: dt-single-call-grader
prose_page: ../features/dual-translation.md
tech_page: ../features/dual-translation.tech.md
total_tasks: 7
done: 0
---

# DT Single-Call Grader (ADR-044) — Task Breakdown

Rollout of the single-call generative DT grader ([[decisions/ADR-044-dt-single-call-generative-grader]]).
The grader, its tests, the migration file and the eval-harness option were built on 2026-11-14
(not numbered as tasks; see `wiki/log.md`). Spec: [[features/dual-translation.tech]] "Single-call
grader (ADR-044)". Evidence: [[evaluations/dt-decision-grading-2026-11-14]].

Drafted 2026-11-14 and **not yet reviewed by the owner** (CLAUDE.md §5d). Tasks that depend on an
open decision are `[?]`.

State today: `DT_SINGLE_CALL_GRADER` off, `DT_GRADING_ASSET_COLUMNS` off,
`migrations/dt_grading_assets.sql` not applied, taxonomy v6 not live
([[tasklist/dt-taxonomy-v6.tasks]] TASK-853 blocked).

---

## TASK-935: Apply `dt_grading_assets.sql` and turn on `DT_GRADING_ASSET_COLUMNS`

**Status:** [ ] Not Started (LIVE-DB, developer applies)
**Feature:** dt-single-call-grader
**Type:** infra
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Apply the additive migration that adds five nullable columns to `dt_error_instance` and creates
`dt_grading_call`, then export `DT_GRADING_ASSET_COLUMNS=true`. The order matters: with the flag on
and the migration missing, PostgREST rejects the error insert and every graded submission fails.
The migration is safe to apply on its own, before any flag changes.

**Acceptance Criteria:**
- [ ] `migrations/dt_grading_assets.sql` applied live; the five `VALIDATE CONSTRAINT` statements succeeded
- [ ] `dt_grading_call` has RLS enabled, no policies, and no grants to `anon` / `authenticated`
- [ ] `tests/sql/check_function_acls.sql` result sets still empty
- [ ] `DT_GRADING_ASSET_COLUMNS=true` set in the app environment only after the above
- [ ] One DT submission graded after the change returns 200 and its `dt_error_instance` rows insert

**Technical Notes:**
Idempotent (ADD COLUMN IF NOT EXISTS, CREATE TABLE IF NOT EXISTS, drop-then-add CHECKs). The
`dt_v5_snapshot_*` tables do not gain the new columns; the TASK-852 rewrite names its columns
explicitly. With the v2 grader still live the new columns stay NULL and no `dt_grading_call` rows
are written; that is expected.

**Files to Create / Modify:**
- none (apply `migrations/dt_grading_assets.sql`; set the env var)

**Verification:**
`SELECT column_name FROM information_schema.columns WHERE table_name = 'dt_error_instance' AND column_name IN ('sentence_index','model_severity','model_note','span_source','correction_source');` returns five rows. `SELECT relrowsecurity FROM pg_class WHERE relname = 'dt_grading_call';` returns `t`.

---

## TASK-936: Shadow run of the single-call grader on real submissions

**Status:** [?] Blocked — needs taxonomy v6 live (TASK-853) or an owner decision to shadow under a pinned v6 taxonomy while v5 stays live; and TASK-935
**Feature:** dt-single-call-grader
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-935, TASK-853

**Description:**
Run the single-call grader next to the live grader on every real submission without showing its
result, and store it for comparison. This is the step the experiment report asks for before
enabling the grader: every number so far comes from seeded errors or model-written paraphrases.
The storage question that blocked a shadow run since September is answered by `dt_grading_call`
(`role = 'shadow'`, decoded grade in `result`); the writer does not exist yet.

**Acceptance Criteria:**
- [ ] A config switch (default off) makes the submit path run the single-call grader after the live grade is persisted, off the response path (the learner's response time does not change)
- [ ] One `dt_grading_call` row per shadow call with `role = 'shadow'` and `result` = `{scores, overall_band, errors[]}`
- [ ] A shadow failure never affects the live grade or the response
- [ ] A script reports, per language: band agreement between shadow and live, errors found by one and not the other, share of clean submissions flagged, share of errors with `correction_source = reference_sentence`, fallback rate, cost
- [ ] Optionally the same for `deepseek/deepseek-v4.1-flash` as a second shadow model
- [ ] Results filed under `wiki/evaluations/`

**Technical Notes:**
`single_call_grader.grade` needs the Tier 0 result, rubric and taxonomy; call it through
`grade_submission(single_call=True)` on a worker thread or from a small job reading recent
`dt_submission` rows. Real submissions have no gold: the report compares two graders, so sample
disagreements for manual reading. Decide here whether the "free translations are expected"
paragraph is needed (open question in the evaluation page).

**Files to Create / Modify:**
- `routes/dual_translation.py` or a new `scripts/dt_shadow_grade.py` — shadow writer
- `config.py` — shadow switch
- `scripts/` — comparison report
- `tests/` — shadow writer tests

**Verification:**
With the switch on in staging, submit one reproduction: the response is unchanged, `dt_grade` holds the live grade, and `dt_grading_call` holds one `shadow` row for the submission.

---

## TASK-937: Enable `DT_SINGLE_CALL_GRADER` in production

**Status:** [?] Blocked — needs the shadow-run result (TASK-936), taxonomy v6 live (TASK-853), and owner decisions on: naturalness/range staying unscored, the free-translation paragraph, and whether learners may see single-call grades before native review (TASK-938)
**Feature:** dt-single-call-grader
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-936, TASK-853, TASK-941

**Description:**
Flip the flag so the single-call flow grades live submissions, with the v2 flow as its fallback.
Before the v6 cutover the flag has no effect (every call falls back with "taxonomy mismatch").

**Acceptance Criteria:**
- [ ] Owner sign-off on the shadow report recorded in ADR-044
- [ ] `DT_SINGLE_CALL_GRADER=true` exported; first live grades show `grader_trace.tier = "single_call"`
- [ ] The DT result page renders a three-dimension grade correctly at every age tier (naturalness and range absent)
- [ ] Fallback rate (`grader_trace.single_call.used = false`) and cost checked after one day from `dt_grade` / `dt_grading_call`
- [ ] Rollback documented: unset the flag; no data change needed

**Technical Notes:**
`source` and `confidence` on single-call errors are fixed defaults; check nothing downstream
(nightly synthesis, cards, UI chips) treats them as judgements. The UI shows a `source` chip when
the field is present.

**Files to Create / Modify:**
- none expected (env var); `static/js/dual_translation.js` only if the source chip must be hidden

**Verification:**
`SELECT grader_trace->>'tier', count(*) FROM dt_grade WHERE created_at > now() - interval '1 day' GROUP BY 1;` shows `single_call` rows.

---

## TASK-938: Native-speaker review of single-call explanations and hint templates

**Status:** [?] Blocked — no reviewer named (open question in [[evaluations/dt-decision-grading-2026-11-14]])
**Feature:** dt-single-call-grader
**Type:** docs
**Complexity:** M (3-8h)
**Depends On:** TASK-936 (for a sample of real output)

**Description:**
A native speaker of each L2 (and a fluent reader of each L1 used in templates) reviews a sample of
what learners would see or might later see: the template explanations rendered on single-call
errors, the model's short notes (`model_note`), and the hint templates drafted for the guided
self-repair design. All of it is AI-drafted and unreviewed.

**Acceptance Criteria:**
- [ ] At least 50 errors per L2 sampled from shadow or gold output, each judged: error real? type right? template text correct and clear? model note correct?
- [ ] Rate of wrong or misleading texts reported per L2 and per error type
- [ ] A decision recorded on whether `model_note` may be shown to learners, and in which language
- [ ] Template fixes filed as taxonomy string changes

**Technical Notes:**
Sample from `dt_grading_call.response` (model notes) joined to `dt_error_instance` (rendered
explanation). Track D's finding: LLM judges cannot count hallucinations (κ = 0.08), so this must be
a human read.

**Files to Create / Modify:**
- `wiki/evaluations/` — review results

**Verification:**
The review page exists and ADR-044 links to it.

---

## TASK-939: Guided self-repair UI for DT feedback (design option 2)

**Status:** [?] Blocked — the option 2 spec is being revised against the single-call grader's output and is not final; hint templates are unreviewed (TASK-938)
**Feature:** dt-single-call-grader
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-935, TASK-937

**Description:**
Build the feedback flow the owner chose ([[design/dt-feedback/option-2-guided-self-repair/SPEC]]):
mark which sentences have a problem, let the learner revise, give help one step at a time (where,
what kind, a clue, the answer), re-check each revision with the cheap grader, and end with the
reference sentence on screen. To be decomposed into its own tasks once the spec is final.

**Acceptance Criteria:**
- [ ] Spec finalised against the single-call contract: "where" uses `sentence_index` and the model span, not the character diff
- [ ] New tables for repair episodes (hint level reached, revisions and their re-check results, outcome) designed and migrated
- [ ] A re-check endpoint grades one revised sentence and logs the call
- [ ] Task breakdown written and reviewed by the owner

**Technical Notes:**
The grader already returns what the first two hint levels need (sentence, span, type). The clue
level needs the reviewed templates. Interaction tables were deliberately left out of
`dt_grading_assets.sql`; see the "Still needed" list in [[features/dual-translation.tech]].

**Files to Create / Modify:**
- to be defined by the task breakdown

**Verification:**
To be defined by the task breakdown.

---

## TASK-940: Re-use a learner's own erroneous sentences in daily practice

**Status:** [?] Blocked — depends on the option 2 spec's daily-practice view being final, and on whether this replaces or sits beside the existing DT error cards ([[features/dual-translation-remediation.tech]])
**Feature:** dt-single-call-grader
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-935, TASK-939

**Description:**
Schedule sentences a learner got wrong for re-translation in the daily session. `sentence_index`
on `dt_error_instance` identifies the sentence; the reference sentence comes from the passage.

**Acceptance Criteria:**
- [ ] Decision recorded: relation to `dt_card` / `dt_error_profile_entry` (replace, feed, or coexist)
- [ ] A store or view of due sentences per learner: submission, sentence index, reference sentence, error types, last attempt, next due
- [ ] A daily-session block serves them and re-checks answers with the single-call grader
- [ ] Study time credited through the existing ledger

**Technical Notes:**
Whether retrying one's own sentence transfers to new sentences is an open question in the design
specs; plan a way to measure it.

**Files to Create / Modify:**
- to be defined after the decision

**Verification:**
To be defined after the decision.

---

## TASK-941: Keep whole-sentence corrections out of cloze cards and profile synthesis

**Status:** [ ] Not Started
**Feature:** dt-single-call-grader
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-935

**Description:**
A single-call error whose correction is the whole reference sentence
(`correction_source = 'reference_sentence'`) would produce a cloze card that blanks an entire
sentence. Make card generation skip those rows, and check that the nightly synthesis does not
treat the default `source` / `confidence` values of single-call errors as signal.

**Acceptance Criteria:**
- [ ] `services/dual_translation/cards.py` does not build a cloze card from a `reference_sentence` row (test)
- [ ] `scripts/dt_nightly_synthesis.py` reads the new column only when `DT_GRADING_ASSET_COLUMNS` is on
- [ ] No behaviour change for rows where the column is NULL (v1/v2 grades)

**Technical Notes:**
On the gold set 1 of 70 errors had a whole-sentence correction; on real, freer translations the
share will be higher (measure it in TASK-936).

**Files to Create / Modify:**
- `services/dual_translation/cards.py` — skip rule
- `scripts/dt_nightly_synthesis.py` — select the column behind the flag
- `tests/test_dual_translation_cards.py` — test

**Verification:**
`pytest tests/test_dual_translation_cards.py -q` passes with the new test.
