---
title: "ADR-030: jev as a flag-gated backend for the answer-entailment judge (default stays llm)"
status: accepted
date: 2026-09-26
---

# ADR-030: jev as a flag-gated backend for the answer-entailment judge

## Context

The answer-entailment judge ([[features/answer-entailment-judge.tech]]) guards test
generation against hallucinated correct answers. It is a chat-model call that returns a
1-5 Likert rating ([[evaluations/entailment-likert-v3-rollout-2026-08-19]]), costs roughly
$0.0002–0.0003 per call (measured 2026-09-26: $0.000177 zh, $0.000289 en/ja).

[[evaluations/jev-judge-feasibility-2026-09-26]] found `typesafe/jev-1.13` — OpenRouter's
non-chat "decision model" behind `POST /api/alpha/decisions` — separates entailed answers
from distractors near-perfectly at $0.042/M input tokens, $0 output, ~0.5 s.
[[evaluations/jev-entailment-calibration-2026-09-26]] then chose cutoffs and compared it to
the live judge on 1,050 items. On zh the live judge is the weaker of the two.

The evidence is strong but **not conclusive**: gold labels are structural, not
human-adjudicated, and jev returns no reasoning text.

## Decision

1. Add jev as a second backend, selected by `ENTAILMENT_JUDGE_BACKEND` = `llm` | `jev` |
   `shadow`, read on every call. Originally **default `llm`**, with the switch a separate,
   explicitly-approved step (TASK-835) — **done 2026-09-27, default is now `jev`; see the update below.**
2. Map jev's P(yes) onto the existing accept / flag / reject contract with per-language
   cutoffs **reject < 0.30, accept ≥ 0.60** (flag between), held in
   `answer_entailment_jev.CUTOFFS`. Downstream code (`_apply_judges`, the review queue,
   the orchestrator) is unchanged.
3. **jev outcomes never write a probability into the 1-5 `judge_confidence` column.**
   `JudgeOutcome.confidence` is `None`; the score travels in a new
   `JudgeOutcome.probability` field and in the review-queue payload
   (`{confidence, probability, backend, reason}`).
4. **Fallback:** if jev cannot answer (any error after retries, or no usable `noul`), the
   LLM judge runs. Only if that also fails does `safe_accept()` apply — which still raises
   `JudgeUnavailable` inside `batch_mode()` and fails open when serving. A jev outage
   therefore cannot weaken fail-closed batch judging.
5. **Shadow mode** returns the LLM verdict and logs jev's beside it under
   `task_name='judge_answer_entailment_shadow'`. It can neither change the outcome nor
   raise, including in a batch.
6. jev prompts are written entirely in the content language (zh/ja/en).
7. jev is called through a new `services/jev_client.py`, not `call_llm`: it retries 429 /
   transient 402 / 5xx, caps concurrency, and logs every call to `llm_calls` with
   `cost_usd` from `usage.cost`.

## Consequences

- Cheaper (~$0.00004/call vs ~$0.0002–0.0003) once switched. jev's own latency measured
  p50 ≈ 0.53 s; the live judge's per-call latency was not compared.
- Two scales no longer share a column: jev rows have `judge_confidence` NULL by design.
  Queries that assume every `judge_answer_entailment` verdict row has a rating must
  filter on `model`.
- A jev reject carries a **synthesised** reason, not a diagnosis. That reason is fed back
  to the question generator as "avoid" context, so regeneration feedback is weaker than
  the LLM judge's explanation. Worth measuring during the shadow window (does the
  regenerated question pass more or less often?).
- The shared OpenRouter account funds both backends: a credit-limit outage (402) takes
  out jev *and* its LLM fallback. The feasibility study hit exactly this.
- Shadow mode adds one sequential jev call (~0.5 s) per judged question.

## Update 2026-09-27 — evidence in

[[evaluations/jev-entailment-shadow-and-adjudication-2026-09-27]]: a 216-comparison shadow window
(0 jev failures; jev stricter on all 8 disagreements, never accepted what live rejected; p50
296 ms vs 1,336 ms) and 300 items labelled by two blind **model** adjudicators (κ 0.887). Against
those labels jev is at least as good as the live judge in all three languages and much better on
zh; the cutoffs stand. Open at the time: (1) the adjudicators are not human, (2) the regeneration effect of the
synthesised reject reason is unmeasured.

## Update 2026-09-27 (later) — default flipped

**Status: accepted; the default is now `jev`** (TASK-835), changed at the operator's explicit
instruction ("flip default now") with the two open items above accepted as risks. An earlier in-session
flip, made before that instruction, was reverted after the permission guard refused it. Decision 1 above
("default `llm`") is superseded; everything else stands. Rollback: `ENTAILMENT_JUDGE_BACKEND=llm`.

## Alternatives Considered

- **Replace the LLM judge outright.** Rejected until human-adjudicated gold exists: the
  structural gold cannot distinguish "jev right, distractor valid" from "jev wrong".
- **Threshold at 0.5.** Rejected: the score distribution is bimodal with negatives under
  0.35; 0.5 sits inside the gap and buys nothing, while 0.30/0.60 keeps a flag band that
  routes the ambiguous middle to review.
- **Map the probability onto a synthetic 1-5 rating** so `judge_confidence` stays populated.
  Rejected: fabricates a rating nobody made — the lesson of the v3 Likert cutover.
- **Fail closed on a jev outage** (no LLM fallback). Rejected on instruction: the LLM judge
  is retained precisely as the fallback.
