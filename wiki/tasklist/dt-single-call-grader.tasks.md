---
title: "DT Single-Call Grader (ADR-044) — Task Breakdown"
feature: dt-single-call-grader
prose_page: ../features/dual-translation.md
tech_page: ../features/dual-translation.tech.md
total_tasks: 7
done: 0
in_progress: 1
---

# DT Single-Call Grader (ADR-044) — Task Breakdown

Rollout of the single-call generative DT grader ([[decisions/ADR-044-dt-single-call-generative-grader]]).
The grader, its tests, the migration file and the eval-harness option were built on 2026-11-14
(not numbered as tasks; see `wiki/log.md`). Spec: [[features/dual-translation.tech]] "Single-call
grader (ADR-044)". Evidence: [[evaluations/dt-decision-grading-2026-11-14]].

Drafted 2026-11-14 and **not yet reviewed by the owner** (CLAUDE.md §5d). Tasks that depend on an
open decision are `[?]`.

State on 2026-11-14 after the owner-review revision (prompt v2): `DT_SINGLE_CALL_GRADER` and
`DT_GRADING_ASSET_COLUMNS` **default to on** in `config.py` (owner approval; env vars override).
`migrations/dt_grading_assets.sql` is final and **not applied**. The active taxonomy and rubric are
version 6 (read live 2026-11-14), so the grader goes live when this code is deployed. No real
submission has been graded by it yet. Not deployed, not committed by the agent that made the change.

---

## TASK-935: Apply `dt_grading_assets.sql` and turn on `DT_GRADING_ASSET_COLUMNS`

**Status:** [ ] Not Started (LIVE-DB, developer applies) — the file is final; apply before or with the deploy of the default-on config
**Feature:** dt-single-call-grader
**Type:** infra
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Apply the additive migration that adds seven nullable columns to `dt_error_instance`
(`sentence_index`, `model_severity`, `model_note`, `span_source`, `correction_source`,
`confidence_label`, `explanation_source`) and creates `dt_grading_call`. `DT_GRADING_ASSET_COLUMNS`
now defaults to on, so no env var is needed. The order is no longer fatal: with the migration
missing, the app retries the insert without the new columns, logs one error per process and still
saves the grade — but the per-error grader fields and the call rows are lost for those submissions,
and a reloaded grade shows the template explanation only.

**Acceptance Criteria:**
- [ ] `migrations/dt_grading_assets.sql` applied live; the seven `VALIDATE CONSTRAINT` statements succeeded
- [ ] `dt_grading_call` has RLS enabled, no policies, and no grants to `anon` / `authenticated`
- [ ] `tests/sql/check_function_acls.sql` result sets still empty
- [ ] No "DT grading-asset columns unavailable" error in the app log after the deploy
- [ ] One DT submission graded after the change returns 200, its `dt_error_instance` rows carry `span_source`, and one `dt_grading_call` row exists for it

**Technical Notes:**
Idempotent and without any destructive statement (ADD COLUMN IF NOT EXISTS, CREATE TABLE / INDEX IF
NOT EXISTS, each CHECK added only if absent). The file was revised on 2026-11-14 before it was ever
applied; nothing needs migrating from an earlier version. Because no CHECK is dropped and re-added,
a later change to an allowed value set (for example a new `span_source`) needs a new migration. The
`dt_v5_snapshot_*` tables do not gain the new columns; the TASK-852 rewrite names its columns
explicitly. If the app was already running without the migration, it probes the columns again
within 10 minutes of the apply; no restart is needed.

**Files to Create / Modify:**
- none (apply `migrations/dt_grading_assets.sql`)

**Verification:**
`SELECT column_name FROM information_schema.columns WHERE table_name = 'dt_error_instance' AND column_name IN ('sentence_index','model_severity','model_note','span_source','correction_source','confidence_label','explanation_source');` returns seven rows. `SELECT relrowsecurity FROM pg_class WHERE relname = 'dt_grading_call';` returns `t`.

---

## TASK-936: Shadow run of the single-call grader on real submissions

**Status:** [?] Blocked — owner decision needed. The grader was turned on by default on 2026-11-14 without this run, and taxonomy v6 is live, so the task as written (single-call shadows the live grader) no longer fits. Decide: (a) run the previous Detector/Verifier grader as the shadow on a sample of live submissions (about $0.03–0.05 each), (b) replace this with a manual read of the first N live single-call grades, or (c) drop it
**Feature:** dt-single-call-grader
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-935

**Description:**
*(Written before the grader was turned on; see Status.)* Run the single-call grader next to the live grader on every real submission without showing its
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

**Status:** [~] In Progress — repo side done 2026-11-14 (config defaults flipped on owner approval, prompt v2 re-validated on gold and the stress set); deploy and the live checks below remain
**Feature:** dt-single-call-grader
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-935

**Description:**
Make the single-call flow grade live submissions, with the v2 flow as its fallback. The owner
approved this on 2026-11-14 without the shadow run (TASK-936). `config.py` now defaults
`DT_SINGLE_CALL_GRADER` and `DT_GRADING_ASSET_COLUMNS` to true. The active taxonomy is v6, so the
grader is live as soon as this code is deployed. What remains is the deploy and checking the first
live grades.

**Acceptance Criteria:**
- [x] Owner approval recorded in ADR-044 (2026-11-14)
- [x] `config.py` defaults on; env vars still override (test)
- [x] Prompt v2 measured on v6 gold (two runs) and the Track E stress set ([[evaluations/dt-decision-grading-2026-11-14]] §9.1)
- [ ] Deployed; first live grades show `grader_trace.tier = "single_call"`
- [ ] The DT result page renders a five-dimension grade, and a grade with naturalness or range absent, at every age tier
- [ ] The Application-layer explanation renders under the template text for a fresh and a reloaded grade
- [ ] A zero-width `span_reproduction` (dropped word, `span_source = diff_hunk`) renders acceptably
- [ ] Fallback rate (`grader_trace.single_call.used = false`), share of `span_source = sentence`, share of withheld low-confidence entries and cost checked after one day from `dt_grade` / `dt_grading_call`
- [ ] Rollback documented: export `DT_SINGLE_CALL_GRADER=false`; no data change needed

**Technical Notes:**
`source` and `confidence` on single-call errors are now model judgments (`confidence` is one of
0.9 / 0.6 / 0.3). The UI shows a `source` chip when the field is present; `source` is unvalidated.
Nothing in the UI uses `confidence` yet. Cloze cards can still be built from whole-sentence
corrections until TASK-941 is done; none occurred in 223 measured errors.

**Files to Create / Modify:**
- `config.py` — done
- `static/js/dual_translation.js` — only if the zero-width span or the source chip needs handling

**Verification:**
`SELECT grader_trace->>'tier', count(*) FROM dt_grade WHERE created_at > now() - interval '1 day' GROUP BY 1;` shows `single_call` rows.

---

## TASK-938: Native-speaker review of single-call explanations and hint templates

**Status:** [?] Blocked — no reviewer named (open question in [[evaluations/dt-decision-grading-2026-11-14]]). More pressing since 2026-11-14: the grading model's own L1 explanation is now shown to learners
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
(`correction_source = 'reference_sentence'`), or whose span is the whole learner sentence
(`span_source = 'sentence'`), would produce a cloze card that blanks an entire sentence. Make card
generation skip those rows. Also decide what a card does with a zero-width learner span
(`span_source = 'diff_hunk'`, dropped word), and check how the nightly synthesis reads `source`
and `confidence`, which for single-call errors are model judgments on a three-step scale
(0.9 / 0.6 / 0.3). The grader is on by default since 2026-11-14, so this guard should land before
or soon after the deploy.

**Acceptance Criteria:**
- [ ] `services/dual_translation/cards.py` does not build a cloze card from a `reference_sentence` row (test)
- [ ] `scripts/dt_nightly_synthesis.py` reads the new column only when `DT_GRADING_ASSET_COLUMNS` is on
- [ ] No behaviour change for rows where the column is NULL (v1/v2 grades)

**Technical Notes:**
With prompt v1, 1 of 71 gold errors had a whole-sentence correction. With prompt v2, 0 of 223
measured errors (gold and stress set) had a whole-sentence span or correction. Real submissions
have not been measured.

**Files to Create / Modify:**
- `services/dual_translation/cards.py` — skip rule
- `scripts/dt_nightly_synthesis.py` — select the column behind the flag
- `tests/test_dual_translation_cards.py` — test

**Verification:**
`pytest tests/test_dual_translation_cards.py -q` passes with the new test.
