---
title: Answer-Entailment Judge — Technical Specification
type: feature-tech
status: complete
prose_page: answer-entailment-judge.md
last_updated: 2026-09-27
dependencies:
  - "services/exercise_generation/judges/answer_entailment.py"
  - "services/exercise_generation/judges/answer_entailment_jev.py"
  - "services/jev_client.py"
  - "services/exercise_generation/judges/base.py (JudgeOutcome, batch_mode, safe_accept)"
  - "services/test_generation/agents/question_generator.py (_apply_judges)"
  - "prompt_templates task_name='test_answer_entailment' (v3+, LLM backend only)"
  - "llm_calls"
breaking_change_risk: medium
---

# Answer-Entailment Judge — Technical Specification

Prose: [[features/answer-entailment-judge]] · Decision: [[decisions/ADR-030-jev-entailment-judge-backend]]
· Tasks: [[tasklist/jev-entailment-judge.tasks]]

## Architecture Overview

```
question_generator._apply_judges
        │  judge_answer_entailment(db, passage, question_text, answer, language_id) -> JudgeOutcome
        ▼
answer_entailment.judge_answer_entailment   ── reads ENTAILMENT_JUDGE_BACKEND per call
   ├─ 'llm'    → _judge_llm  (Likert v3 prompt via call_llm; rollback + jev fallback)
   ├─ 'jev'    → _judge_jev  (DEFAULT since 2026-09-27)  (answer_entailment_jev.evaluate → jev_client.call_jev)
   │              └─ any Exception → falls through to _judge_llm
   └─ 'shadow' → _judge_llm (returned) + _shadow_jev (logged, never raises)
```

Callers see one contract: `JudgeOutcome(verdict, confidence, reason, probability, backend)`.
`verdict` ∈ accept / flag / reject on every backend. Reject regenerates the question
(reason fed back as avoid-context); flag keeps it and queues it in
`generation_review_queue`; accept passes.

## Backends

| | `llm` (rollback / fallback) | `jev` (default) |
|---|---|---|
| Model | per-language `prompt_templates` row (zh deepseek-chat, en/ja gemini-3.5-flash-lite as of 2026-09-26) | `typesafe/jev-1.13` |
| Endpoint | chat completions via `call_llm` | `POST https://openrouter.ai/api/alpha/decisions` |
| Raw score | 1-5 Likert rating | P(yes), 0-1 (`noul`) |
| Verdict | `likert_to_verdict`: 5,4 accept · 3 flag · 2,1 reject | `probability_to_verdict`: p<0.30 reject · p≥0.60 accept · else flag |
| `outcome.confidence` | the rating (float) | `None` |
| `outcome.probability` | `None` | P(yes) |
| Reason | model's explanation, in the content language | synthesised sentence with P(yes), in the content language |
| Cost | ~$0.0002–0.0003/call | ~$0.00004/call |

**Cutoffs** live in `answer_entailment_jev.CUTOFFS[language_id] = (reject_below, accept_at)`,
currently `(0.30, 0.60)` for zh / en / ja. Derivation:
[[evaluations/jev-entailment-calibration-2026-09-26]]. Retune by editing the dict; no other
logic depends on the values.

## Configuration

| Variable | Values | Default | Notes |
|---|---|---|---|
| `ENTAILMENT_JUDGE_BACKEND` | `llm` \| `jev` \| `shadow` | `jev` (`DEFAULT_BACKEND`, since 2026-09-27) | Case/whitespace tolerant; unset or blank means the default; an unrecognised value logs a warning and means `llm` (never the default). Read on every call, so flipping needs no restart. **Rollback: `ENTAILMENT_JUDGE_BACKEND=llm`.** |
| `JEV_MAX_CONCURRENCY` | int | `8` | Process-wide cap on in-flight jev requests. Read at import. |
| `OPENROUTER_API_KEY` | key | — | jev client reads it **at call time** (unlike `llm_service`, which freezes it at import). Scripts still `load_dotenv()` first. |

## Fail-open / fail-closed contract (unchanged in kind)

- **Serving:** a judge that cannot run returns `safe_accept()` — never blocks a learner.
- **`batch_mode()`** (wrapped around `run()`/`run_batch()` only): the same outage raises
  `JudgeUnavailable`; the judge-path handlers re-raise it.
- **jev backend:** a jev failure is *not* an outage by itself — the LLM judge runs. Only when
  the LLM judge also cannot run does `safe_accept()` fire (abort in batch, accept when
  serving). A response without a usable `noul` in [0, 1] counts as a jev failure, not an
  item-level gap: this is the hallucinated-answer guard, so a jev that answered nothing did not run.
- **shadow:** the LLM path keeps its own contract; jev failures are logged and swallowed,
  even in a batch.
- `accept_item` (missing single rating) is only reachable on the LLM backend.
- There is **no d≤2 skip inside this judge**; the difficulty gate is the caller's
  (`run_judges = difficulty > 2` in `_generate_test`).

## `services/jev_client.py`

`call_jev(state, questions, *, model='typesafe/jev-1.13', pipeline, task_name, language_code,
template_version, max_retries=4, timeout=30, log=True) -> JevResult`; every failure is
`JevError`.

- Retries: network errors, 429 (honours `Retry-After`, capped 30 s), 5xx, and 402 **only**
  when `limit_source == 'openrouter_in_flight_budget'`. Other 4xx and a permanent 402
  (credits / key limit exhausted) fail immediately.
- Logs one `llm_calls` row per call, best-effort: `provider='TypeSafe'`, `cost_usd` from
  `usage.cost`, `raw_response` = the `answers` JSON. A response with no `usage.cost` logs a
  warning and stores NULL rather than 0.
- Wire format: `state` holds the passage / question / candidate; `questions.entailed` is one
  `noul` with native-language `instructions` and `criteria.true/false`
  (`answer_entailment_jev.RUBRIC`). jev returns no text.

## Telemetry

| Row | `task_name` | `model` | `judge_verdict` | `judge_confidence` | `cost_usd` |
|---|---|---|---|---|---|
| LLM raw round-trip | `judge_answer_entailment` | chat model | NULL | NULL | per call |
| LLM verdict summary | `judge_answer_entailment` | chat model | set | rating 1-5 | NULL |
| jev raw round-trip | `judge_answer_entailment` | `typesafe/jev-1.13-<date>` | NULL | NULL | `usage.cost` |
| jev verdict summary | `judge_answer_entailment` | `typesafe/jev-1.13-<date>` | set | **NULL** | NULL |
| shadow raw round-trip | `judge_answer_entailment_shadow` | jev | NULL | NULL | `usage.cost` |
| shadow verdict | `judge_answer_entailment_shadow` | jev | set | NULL | NULL |

Shadow `raw_response` on the verdict row: `{"p_yes", "jev_verdict", "live_verdict",
"live_rating"}` — one row holds both verdicts.
The task_name is the `judge_` label, **not** the `prompt_templates` key
(`test_answer_entailment`) — see [[evaluations/entailment-likert-v3-rollout-2026-08-19]].

Shadow comparison:

```sql
SELECT language_code,
       raw_response::json->>'live_verdict' AS live,
       judge_verdict                        AS jev,
       count(*)
FROM llm_calls
WHERE task_name = 'judge_answer_entailment_shadow' AND judge_verdict IS NOT NULL
GROUP BY 1,2,3 ORDER BY 1,2,3;
```

Only rows with `judge_verdict IS NOT NULL` carry the `raw_response` above; the raw
round-trip rows hold jev's `answers` JSON instead.

## Review-queue payload

`_judge_flags['answer_entailment'] = {confidence, probability, backend, reason}` →
`generation_review_queue.judge_scores` (jsonb). Pre-2026-09-26 rows have only
`{confidence, reason}`. Rejection records gained `probability` and `backend` too.

## Measurement hook

`answer_entailment.shadow_observer` (default `None`): called as `observer(passage, question_text,
answer, language_id, live_outcome, jev_verdict)` after every successful shadow evaluation; a raising
observer is logged and ignored. Used by `scripts/shadow_entailment_window.py` to keep the text of each
comparison (`llm_calls` stores verdicts only).

## Evidence

[[evaluations/jev-entailment-calibration-2026-09-26]] (cutoffs, structural gold) ·
[[evaluations/jev-entailment-shadow-and-adjudication-2026-09-27]] (shadow window, model-adjudicated
gold). Measured latency: jev p50 296 ms / p95 375 ms; live judge p50 1,336 / p95 7,233 ms (zh p50 3.2 s).

## Testing

`tests/conftest.py` pins `ENTAILMENT_JUDGE_BACKEND=llm` for the whole suite (the default is jev, which
makes a real HTTP call). `tests/test_jev_entailment.py` (81 tests): client wire format + retry matrix + `cost_usd`
non-NULL; boundary mapping in all three languages; prompts entirely in-language; flag
switching; shadow can't alter or raise; jev-failure → LLM fallback; double failure aborts a
batch / fails open when serving; `_apply_judges` shape. Existing suites still green:
`tests/test_generation`, `tests/test_test_gen_fail_closed.py`,
`tests/test_distractor_two_axis.py`, `tests/test_judge_subject_keywords.py`.

Run: `PYTHONPATH=. pytest tests/test_jev_entailment.py`. Live wiring check (production
pipeline, <1¢): `PYTHONPATH=. python scripts/smoke_entailment_jev.py`.

## Open questions

- Human confirmation of the 22-item `human_review_sheet.csv` (TASK-834). Model adjudicators
  agree with each other (κ 0.887) but are both Claude models.
- Does the synthesised reject reason degrade regeneration? Unmeasured: the shadow window had only
  6 rejects in 216.
- The shared OpenRouter account funds both backends; a 402 outage takes both.
