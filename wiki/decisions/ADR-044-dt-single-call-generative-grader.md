---
title: "ADR-044: Dual Translation is graded by one structured generative call; decision models are not used for DT feedback"
status: accepted
date: 2026-11-14
---

# ADR-044: Dual Translation is graded by one structured generative call; decision models are not used for DT feedback

Status: **accepted** (owner instruction 2026-11-14: "Build out the gpt-6-luna grader for dual
translation"). **Built, flag-gated, default OFF.** Live grading is unchanged until
`DT_SINGLE_CALL_GRADER=true` is exported, and that waits for a shadow run on real submissions
([[tasklist/dt-single-call-grader.tasks]] TASK-936, TASK-937).

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
   a list of errors: sentence number, the offending learner text, a taxonomy-v6 type, a severity and
   a short note. Everything else is Python: span validation, the reference-side fragment, the
   template explanation ([[decisions/ADR-015-eager-error-explanations]]) and the bands
   (`services/dual_translation/scoring.py`, unchanged).
2. **The prompt is frozen.** It is the Track B "span + explanation" variant, ported byte-for-byte
   (`services/dual_translation/single_call_prompts.py`, `PROMPT_VERSION`). A test pins it against
   the experiment harness. Any wording change is a new prompt version and needs its own
   measurement.
3. **Severity rule per model and language**, as frozen in the experiment: for gpt-6-luna the
   taxonomy default severity of the predicted type for en (unless the model said critical), the
   model's own severity for zh and ja. For the fallback model: default for en and ja, model's own
   for zh.
4. **Fallback chain:** primary model → `deepseek/deepseek-v4.1-flash` once
   (`DT_SINGLE_CALL_FALLBACK_MODEL`) → the configured existing flow (v2 Detector/Verifier, or v1).
   A failure never awards full marks. `grader_trace.single_call` records which path graded.
5. **Decision models (jev and the others tested) are not used for DT error feedback.** This
   supersedes the routing and shadow recommendations of
   [[evaluations/jev-dt-tuning-2026-09-27]] for this purpose. jev stays in use where
   [[decisions/ADR-029-jev-tier-assignment]] and [[decisions/ADR-030-jev-entailment-judge-backend]]
   put it.
6. **Only accuracy, fidelity and understandability are scored.** Naturalness and range could not be
   validated, so the single-call grade leaves them out of `scores` and computes `overall_band` over
   the three. It does not default them to band 4.
7. **Grading assets are stored as structured JSON, not prompts**
   (`migrations/dt_grading_assets.sql`, config `DT_GRADING_ASSET_COLUMNS`): five per-error columns
   on `dt_error_instance` (including `sentence_index`) and a `dt_grading_call` table with one row
   per model call. About 1–2 KB per graded submission.

## Consequences

- **Cost and latency.** About $0.00005 and 1.0–1.4 s per submission, against $0.025–0.05 and up to
  minutes for the live grader.
- **Requires taxonomy v6 as the loaded taxonomy.** The frozen type list is v6's. v6 is not live
  yet ([[tasklist/dt-taxonomy-v6.tasks]] TASK-853 is blocked). Under any other taxonomy the single
  call is skipped and the configured flow grades; the trace says "taxonomy mismatch". Turning the
  flag on before the v6 cutover therefore changes nothing.
- **English prompt, slugs not indices.** This departs from the L2-only, numeric-index rule the
  other DT prompts follow ([[decisions/ADR-015-eager-error-explanations]] context,
  `services/dual_translation/prompts.py`). It is what was measured. The learner still never sees
  model prose as the eager explanation.
- **Fields the model is not asked for are filled with fixed defaults:** `source = intralingual`,
  `confidence = 0.5`. The trace names them as defaults. Anything that reads `source` or `confidence`
  as a judgement must not do so for single-call grades.
- **`corrected_form` is derived, not model-given.** The learner sentence is aligned with its
  reference sentence and the learner span carried across. When there is nothing local to show (a
  free rewrite, or the span is a whole sentence) the correction is the whole reference sentence and
  `correction_source = reference_sentence`. Cloze cards must skip those rows (TASK-941).
- **No positive-evidence highlights and no Application layer by default.** `highlights` is empty.
  `explanation_parts.application` is null unless `DT_SINGLE_CALL_EXPLAINER` adds the v2 Explainer
  call. The model's note is kept in `explanation_parts.model_note`, separate and unreviewed.
- **The daily token budget does not degrade this flow.** It is cheaper than the tier-1-only grade
  the budget falls back to. Its tokens still count toward the budget.
- **Run-to-run variance is real.** The production path reproduces the experiment exactly when fed
  the experiment's recorded responses, but live re-runs gave zh accuracy QWK .59 and .66 against
  the reported .74 ([[evaluations/dt-decision-grading-2026-11-14]] "Production-path check").

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
- **Ask the model for the corrected form and the reference span.** Would change the validated
  prompt. Deferred to a future prompt version with its own measurement.
- **Store prompts and raw responses for every call.** Rejected on size: the prompt is about 5 KB
  and identical per language; it is reproducible from the prompt version and the stored texts.

## Related Pages
- [[features/dual-translation.tech]] — "Single-call grader (ADR-044)" section: flow, config, contract, persistence
- [[evaluations/dt-decision-grading-2026-11-14]] — the experiment and the production-path check
- [[tasklist/dt-single-call-grader.tasks]] — migration, shadow run, enablement, review, self-repair UI
- [[decisions/ADR-019-evidence-first-scoring]] · [[decisions/ADR-031-dt-taxonomy-v6-merge]] · [[decisions/ADR-013-global-feature-flag-rollout]]
- [[design/dt-feedback/option-2-guided-self-repair/SPEC]] — the feedback design the owner chose
