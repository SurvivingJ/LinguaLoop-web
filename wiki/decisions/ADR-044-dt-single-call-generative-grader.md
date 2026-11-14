---
title: "ADR-044: Dual Translation is graded by one structured generative call; decision models are not used for DT feedback"
status: accepted
date: 2026-11-14
---

# ADR-044: Dual Translation is graded by one structured generative call; decision models are not used for DT feedback

Status: **accepted** (owner instruction 2026-11-14: "Build out the gpt-6-luna grader for dual
translation"). **Revised the same day after owner review** (prompt v2, see "Revision" below), and
**turned on by default** on owner approval: `DT_SINGLE_CALL_GRADER` and `DT_GRADING_ASSET_COLUMNS`
default to true in `config.py` (env vars still override). Taxonomy v6 was activated in production
on 2026-11-14 ([[decisions/ADR-031-dt-taxonomy-v6-merge]], TASK-853) and
`migrations/dt_grading_assets.sql` was applied the same day (TASK-935), so deploying this code makes the
single-call grader the live DT grader. Outstanding: restart all web workers (taxonomy cached with no TTL) and deploy
([[tasklist/dt-single-call-grader.tasks]] TASK-937).

## Context

[[evaluations/dt-decision-grading-2026-11-14]] compared three ways of grading a Dual Translation
(DT) submission cheaply: decision models (jev and others) asked narrow questions per sentence,
cascades that route between a decision model and an LLM, and a cheap generative LLM asked once for
a structured error list.

- On the v6 gold set one cheap LLM call per item matched or beat the live Detector/Verifier grader
  ([[decisions/ADR-019-evidence-first-scoring]]) at about 1/500 of its cost, and beat jev on recall.
- On free (paraphrased) translations the decision-model pipelines flagged 31–76% of correct
  rephrased sentences. `openai/gpt-6-luna` flagged 1 of 152 and no clean item.
- The character diff stops locating the error once the learner rephrases (a small local edit for 12
  of 40 errors at heavy paraphrase); the LLM's own span stayed on the error.

The owner also asked that grading output be kept for later design work, within a size limit.

## Decision

1. **One call per submission.** A submission that Tier 0 does not resolve is graded by a single
   strict-JSON-schema call to `openai/gpt-6-luna` (config `DT_SINGLE_CALL_MODEL`). The model returns
   a list of errors and two band judgments (items 6–9). Everything else is Python: span location,
   the template explanation ([[decisions/ADR-015-eager-error-explanations]]) and the three derived
   bands (`services/dual_translation/scoring.py`, unchanged).
2. **The prompt is versioned and measured.** `services/dual_translation/single_call_prompts.py`,
   `PROMPT_VERSION`. Any wording change is a new prompt version and needs its own measurement. The
   current prompt is v2 (`dt-single-call/v2-quotes-5dim/2026-11-14`); v1 was the Track B prompt
   ported byte-for-byte.
3. **Severity rule per model and language**, as frozen in the experiment: for gpt-6-luna the
   taxonomy default severity of the predicted type for en (unless the model said critical), the
   model's own severity for zh and ja. For the fallback model: default for en and ja, model's own
   for zh. The rule was fitted on prompt v1 and kept for v2 without refitting.
4. **Fallback chain:** primary model → `deepseek/deepseek-v4.1-flash` once
   (`DT_SINGLE_CALL_FALLBACK_MODEL`) → the configured existing flow (v2 Detector/Verifier, or v1).
   A failure never awards full marks. `grader_trace.single_call` records which path graded.
5. **Decision models (jev and the others tested) are not used for DT error feedback.** This
   supersedes the routing and shadow recommendations of
   [[evaluations/jev-dt-tuning-2026-09-27]] for this purpose. jev stays in use where
   [[decisions/ADR-029-jev-tier-assignment]] and [[decisions/ADR-030-jev-entailment-judge-backend]]
   put it.
6. **All five rubric dimensions are scored** (revised; v1 scored three). Accuracy, fidelity and
   understandability are derived from the error list. Naturalness and range are judged by the model
   in the same call, the way the v2 Verifier judges them: the rubric band descriptors for the
   passage's age tier are in the prompt, and a judgment counts only with a band 1–4 and a verbatim
   evidence quote found in the learner text. A judgment that fails is left out and the overall band
   renormalises; it is never defaulted to 4. One extra rule: a naturalness band below 4 whose
   evidence is only a listed accuracy/fidelity error is discarded, because that error is already
   scored. **These two dimensions are not validated to the standard of the other three** — the gold
   set has range = 4 on every item and naturalness = 3 on 7 of 91.
7. **Confidence and source come from the model** (revised; v1 used fixed 0.5 and `intralingual`).
   Confidence is high / medium / low, stored as 0.9 / 0.6 / 0.3 with the label in
   `confidence_label`. Source is the model's interlingual / intralingual call, made knowing the
   learner's L1; the taxonomy carries no default source to derive it from. An entry the model marks
   `low` is withheld from the grade (counted and listed in the trace) unless
   `DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE` is on.
8. **The model's explanation is shown to the learner** (revised; v1 stored it unseen). It is asked
   for in the learner's L1 and goes into `explanation_parts.application`, the field the results UI
   already renders under the template text, after the Explainer's own guards (≤ 240 characters, one
   paragraph, no score-like digits, quotes the learner or corrected form) plus a wrong-language
   check. A rejected explanation leaves the template alone. `explanation` itself stays the eager
   template text (ADR-015). Each error records `explanation_source` (model / template / explainer).
9. **Spans come from verbatim quotes, located by a ladder** (revised). The model returns the
   sentence number, an exact quote of the learner fragment and the reference fragment it should have
   been. The learner quote is located by: exact match in the named sentence → normalised match
   (width, kana, case, punctuation) → exact or normalised match in another sentence → bounded fuzzy
   match inside the named sentence → the diff hunk of that sentence that overlaps the quote → the
   whole sentence as a last resort. The path is stored as `span_source` and counted in the trace.
   The reference quote, located the same way, is the `corrected_form` (`correction_source =
   model_quote`); sentence alignment and the whole reference sentence are the fallbacks.
10. **The error-type list is hardcoded and exhaustive.** `TYPE_DEFINITIONS` lists every subtype
    taxonomy v6 allows per L2, each with a definition. A test fails if the list and
    `migrations/dt_taxonomy_v6_seed.sql` diverge. At run time a loaded taxonomy whose list differs in
    either direction is not graded with this prompt (the configured flow grades instead). A type
    outside the list from the model is mapped through the taxonomy's legacy aliases if possible,
    otherwise dropped; both are counted and logged.
11. **Grading assets are stored as structured JSON, not prompts**
    (`migrations/dt_grading_assets.sql`, config `DT_GRADING_ASSET_COLUMNS`): seven per-error columns
    on `dt_error_instance` and a `dt_grading_call` table with one row per model call. About 1.5–3 KB
    per graded submission. If the migration is missing the grade is still saved without them.

## Consequences

- **Cost and latency.** About $0.00010 and 1.5–1.7 s per submission with prompt v2 (v1: $0.00005,
  1.0–1.4 s), against $0.025–0.05 and up to minutes for the Detector/Verifier grader.
- **Requires taxonomy v6 as the loaded taxonomy.** It is, as of the 2026-11-14 cutover (v6 inserted and
  activated in production that day; v5 kept, inactive; the subtype lists equal the hardcoded ones; workers still need a
  restart to pick it up). (A mid-day revision of this ADR said the active taxonomy was already v6 "when read"; that
  does not agree with the cutover record, where v5 was active until the activation, and is unreconciled.) Under any other taxonomy the
  single call is skipped and the configured flow grades; the trace says "taxonomy mismatch".
- **English prompt, slugs not indices.** This departs from the L2-only, numeric-index rule the
  other DT prompts follow (`services/dual_translation/prompts.py`). The learner's L1 is named in the
  user message and in the response schema; the rubric band descriptors are quoted in the L2.
- **Learners now see unreviewed model prose.** The explanation shown as the Application layer is
  the grading model's own sentence. On gold and the stress set 96% passed the guards; nobody has
  checked them for correctness (TASK-938).
- **Naturalness is close to a constant 4.** With the double-count guard the grader scored
  naturalness on 238 of 285 measured items and found 1 of the 13 gold naturalness-3 cases among
  them. It no longer drags the overall band down for grammar errors, and it adds almost no
  information. Range was 4 on 278 of 279.
- **Low-confidence errors are withheld.** In the measured runs every `low` entry was a false alarm,
  so this protects correct answers. It also means the grader's own doubts are invisible until a UI
  with an "unsure" state turns `DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE` on.
- **`medium` is the only "unsure" signal left in the grade**, and it is weak: precision .85 against
  .99 for `high`, on 20 medium errors.
- **`source` is an unvalidated model judgment.** There are no gold labels for it.
- **The lower rungs of the span ladder have not been exercised by a real model.** gpt-6-luna quoted
  verbatim on all 223 measured errors. The normalised, fuzzy and diff-hunk paths are unit-tested
  only.
- **Whole-sentence spans and corrections can still occur** (`span_source = sentence`,
  `correction_source = reference_sentence`). Cloze cards must skip those rows; that guard is not
  built (TASK-941).
- **No positive-evidence highlights.** `highlights` is empty.
- **The daily token budget does not degrade this flow.** It is cheaper than the tier-1-only grade
  the budget falls back to. Its tokens still count toward the budget.
- **Run-to-run variance is real.** At temperature 0 the same prompt gave Chinese accuracy QWK .59
  and .68 on two gold runs ([[evaluations/dt-decision-grading-2026-11-14]] §9.1).
- **The default is on without a shadow run.** The owner approved this on the gold and stress-set
  numbers. Those are seeded and synthetic data; no real submission has been graded by this flow.
- **Unit tests pin both flags off** (`tests/conftest.py`), because the older DT tests exercise the
  v1/v2 flows without naming one and would otherwise make paid calls.

## Revision 2026-11-14 (prompt v2)

Owner feedback on the first build and what was done:

| Feedback | Change | Measured |
|---|---|---|
| "the three dimensions is not enough" | Decision 6 | range 278/279 exact; naturalness 221/238 exact where scored, 47 left out |
| "fixed error doesnt make sense" (fixed confidence and source) | Decision 7 | high .99 precision, medium .85; low withheld |
| "show model explanation" | Decision 8 | shown for 214 of 223 errors |
| "fix unlocatable spans" | Decision 9 | whole-sentence fallback 0 of 223 (v1: 1 of 71 on gold) |
| "error-type list can be hardcoded, just needs to be exhaustive" | Decision 10 | drift test added |
| turn the grader on | config defaults flipped; missing-migration fallback added | — |

Detection against prompt v1: gold QWK inside v1's run-to-run range on every cell; heavy-paraphrase
precision / recall .94 / .85 against .91 / .72; no clean item flagged on gold or on either stress
level. Full tables: [[evaluations/dt-decision-grading-2026-11-14]] §9.1.

## Alternatives Considered

- **Keep the Detector/Verifier flow (v2).** It stays as the fallback and as the live grader until
  the flag flips. It costs about 500 times more and was not more accurate on gold.
- **Diff-focused jev, or a jev cascade.** Rejected: collapses on rephrased translations, costs more
  per sentence than a flash-class LLM call, and cannot write explanations.
- **`deepseek/deepseek-v4.1-flash` as primary.** Cheaper and equal on near-copy gold, but its
  precision fell from .96 to .60 on heavy paraphrase. Kept as the fallback model.
- **Add the "free translations are expected" paragraph now.** Not adopted: it lowers recall on
  near-verbatim answers (.88 → .80). Available as `DT_SINGLE_CALL_FREE_TRANSLATION`, default off;
  to be decided after the shadow run.
- **Ask the model for the corrected form and the reference span.** Deferred in v1; adopted in
  prompt v2 (Decision 9).
- **Derive naturalness from the error list** (band 3 if any naturalness-type error, else 4), as
  Track B's proxy did. Rejected: the owner asked for the existing contract's judged dimensions, and
  the proxy is not a judgment. In practice the guarded model judgment behaves much like it.
- **Keep low-confidence errors and show them as unsure.** Not possible yet: the results UI has no
  unsure state, so they would appear as plain errors on correct answers. Available behind
  `DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE`.
- **A numeric confidence (0–1).** Rejected for a three-level label: cheap models cluster numeric
  self-reports, and the UI needs a state, not a number.
- **Store prompts and raw responses for every call.** Rejected on size: the prompt is about 5 KB
  and identical per language; it is reproducible from the prompt version and the stored texts.

## Related Pages
- [[features/dual-translation.tech]] — "Single-call grader (ADR-044)" section: flow, config, contract, persistence
- [[evaluations/dt-decision-grading-2026-11-14]] — the experiment and the production-path check
- [[tasklist/dt-single-call-grader.tasks]] — migration, shadow run, deploy check, review, self-repair UI
- [[decisions/ADR-019-evidence-first-scoring]] · [[decisions/ADR-031-dt-taxonomy-v6-merge]] · [[decisions/ADR-013-global-feature-flag-rollout]]
- [[design/dt-feedback/option-2-guided-self-repair/SPEC]] — the feedback design the owner chose
