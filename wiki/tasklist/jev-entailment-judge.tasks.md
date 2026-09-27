---
title: "jev Answer-Entailment Judge — Task Breakdown"
feature: answer-entailment-judge
prose_page: ../features/answer-entailment-judge.md
tech_page: ../features/answer-entailment-judge.tech.md
total_tasks: 6
done: 5
---

# jev Answer-Entailment Judge — Task Breakdown

Decision: [[decisions/ADR-030-jev-entailment-judge-backend]] · Evidence:
[[evaluations/jev-entailment-calibration-2026-09-26]]. Numbers TASK-830–835 were chosen
clear of the 819–829 range in case parallel jev work (tier re-assignment) files tasks of
its own.

**State 2026-09-27:** built, tested, live-smoke-tested, shadow-tested and adjudicated (model
labels). **The default is now `jev`** (TASK-835, done at the operator's explicit instruction);
`ENTAILMENT_JUDGE_BACKEND=llm` rolls back. Evidence:
[[evaluations/jev-entailment-shadow-and-adjudication-2026-09-27]].

---

## TASK-830: `services/jev_client.py` — Decisions API client

**Status:** [x] Done (2026-09-26)
**Feature:** answer-entailment-judge
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:** Client for `POST /api/alpha/decisions`, which `call_llm` cannot reach.
Retries 429 / transient 402 / 5xx / network errors, fails fast on other 4xx and on a
permanent 402, caps concurrency, reads the API key at call time, and logs every call to
`llm_calls` with `cost_usd` from `usage.cost`.

**Acceptance Criteria:**
- [x] Retry matrix covered by mocked-HTTP tests (429 + Retry-After, transient vs permanent 402, 5xx exhaustion, network, other 4xx).
- [x] `cost_usd` reaches the `llm_calls` row non-NULL — unit test **and** live: 7/7 raw rows non-NULL (`scripts/smoke_entailment_jev.py`).
- [x] Missing `usage.cost` stores NULL and warns; a logging failure never breaks the call.

**Files:** `services/jev_client.py`, `tests/test_jev_entailment.py`

---

## TASK-831: jev backend + `ENTAILMENT_JUDGE_BACKEND` flag

**Status:** [x] Done (2026-09-26)
**Feature:** answer-entailment-judge
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-830, TASK-832

**Description:** `llm` | `jev` | `shadow` dispatcher in `judge_answer_entailment`. jev
outcomes carry `confidence=None` + `probability`; a jev failure falls back to the LLM judge;
`shadow` returns the LLM verdict and logs jev's under `judge_answer_entailment_shadow`.
`JudgeOutcome` gains `probability` / `backend`; `_apply_judges` logs and stores them.

**Acceptance Criteria:**
- [x] Default is `llm` and never touches jev; unknown values mean `llm` with a warning.
- [x] Fail-closed preserved: jev error → LLM; both down → `JudgeUnavailable` in `batch_mode()`, accept when serving.
- [x] Shadow cannot change the outcome or raise, including in a batch.
- [x] Prompts entirely in zh / ja / en.
- [x] 80 new tests + 115 existing judge/fail-closed tests green.

**Files:** `services/exercise_generation/judges/answer_entailment.py`,
`answer_entailment_jev.py`, `base.py`, `services/test_generation/agents/question_generator.py`

---

## TASK-832: Calibrate accept / flag / reject cutoffs

**Status:** [x] Done (2026-09-26)
**Feature:** answer-entailment-judge
**Type:** test
**Complexity:** M
**Depends On:** none

**Description:** Chose `(reject < 0.30, accept ≥ 0.60)` from a sweep over 1,050 structurally
labelled items, and compared jev to the live judge item by item. See the evaluation page.

**Acceptance Criteria:**
- [x] Per-language confusion matrices and every disagreement with its text (`calibration_report.md`).
- [x] Spend under the $1 cap ($0.19).

**Files:** `scripts/calibrate_entailment_jev.py`, `scripts/build_entailment_prod_sample.py`,
`data/eval/jev_entailment_calibration_2026-09-26/`

---

## TASK-833: Shadow window — evidence for the switch-over

**Status:** [x] Done (2026-09-27) — with two gaps, below
**Feature:** answer-entailment-judge
**Type:** infra
**Complexity:** S (operator time, wall clock)
**Depends On:** TASK-831

**Description:** Set `ENTAILMENT_JUDGE_BACKEND=shadow` where test generation runs and let a
normal generation window pass (target ≥ 300 judged questions per language). Read the
comparison query in [[features/answer-entailment-judge.tech]]. Also measure whether questions
regenerated after a **jev** reject (synthesised reason) pass more or less often than after an
LLM reject — shadow can't show that directly, so sample it with a short `jev` run on a
throwaway batch.

**Acceptance Criteria:**
- [x] Live-vs-jev verdict cross-tab per language over the window (216 comparisons, 0 jev failures).
- [x] Every disagreement read (8 of 216; jev the stricter side on all, never accepted what live rejected).
- [x] Shadow spend and latency recorded: jev p50 296 ms / p95 375 ms vs live 1,336 / 7,233 ms; ≈ $0.00004/call.
- [ ] **Gap:** target was ≥ 300 judged questions per language; achieved 70–76 — the $1 cap binds on generation cost (~90% of the $0.70 window spend), not judge cost.
- [ ] **Gap:** regeneration after a jev reject vs an LLM reject was **not measured** — only 6 of 216 candidates were rejected, so it would need thousands of questions. Bounded by `question_regen_attempts`.

**Verification:** `scripts/shadow_entailment_window.py --backend shadow`; results in
`data/eval/entailment_shadow_window_2026-09-27/`. Note the harness lost `test_id` (thread-local
across the generator's pool); fixed to store the passage.

---

## TASK-834: Human-adjudicated entailment gold sample

**Status:** [~] In Progress — model-adjudicated part done 2026-09-27; **human confirmation owed**
**Feature:** answer-entailment-judge
**Type:** test
**Complexity:** M
**Depends On:** none

**Description:** The current gold is structural (answer = 1, distractor = 0), which cannot
tell "jev right, distractor valid" from "jev wrong". Hand-label a few hundred real items,
weighted toward the categories where the two judges disagree: ja "meaning of X in the
passage", inference questions, and the ~83 disagreements already in `calibration_report.md`.
Re-score both judges and re-check the cutoffs.

**Acceptance Criteria:**
- [x] 300 items labelled, 100 per language, two independent blind labellers on 297 (κ = 0.887) plus a tiebreak — **but the labellers are Claude models (Sonnet, Opus), not humans.**
- [x] Both judges' false-accept / false-reject reported against those labels (jev 1 confident error, live 27 on a disagreement-weighted pool; both 0 on 214 agreeing items).
- [x] Cutoffs confirmed unchanged: `(0.30, 0.60)`.
- [ ] **Owed:** a human labels `data/eval/entailment_adjudication_2026-09-27/human_review_sheet.csv` (22 items: adjudicators split, or the model label contradicts jev's confident verdict), ideally with a second human on a subset.

---

## TASK-835: Switch the default to `jev`

**Status:** [x] Done (2026-09-27) — flipped at the operator's explicit instruction ("flip default
now"). An earlier in-session attempt, before that instruction, was reverted after the permission guard
refused it ("Feature Flag Writes"). Evidence:
[[evaluations/jev-entailment-shadow-and-adjudication-2026-09-27]].
**Feature:** answer-entailment-judge
**Type:** infra
**Complexity:** XS
**Depends On:** TASK-833, TASK-834

**Description:** `answer_entailment.DEFAULT_BACKEND` changed `'llm'` → `'jev'`. The LLM judge stays
as the automatic fallback when jev cannot answer, and as the rollback. `tests/conftest.py` pins the
rest of the suite to `llm` so older judge tests cannot reach the network.

**Accepted risks at the time of the flip:** no human labels yet (TASK-834); 216 rather than ~900 shadow
comparisons; the regeneration effect of the synthesised reject reason is unmeasured; ja flags ~6% of
items in the window (review load, not blocked questions); one OpenRouter credit limit funds both backends.

**Acceptance Criteria:**
- [x] Operator approval recorded (this log entry, 2026-09-27).
- [x] `_backend()` returns `jev` with the variable unset; no `.env`/deploy file overrides it (checked).
- [x] `scripts/smoke_entailment_jev.py` passes; full suite green except one unrelated test.
- [x] Rollback is one env var (`ENTAILMENT_JUDGE_BACKEND=llm`).

**Watch after the flip:** `judge_answer_entailment` verdict rows now have `judge_confidence` NULL
by design (jev rows); `generation_review_queue` entries for entailment carry `probability` and
`backend='jev'`; the LLM fallback fires only if jev errors (look for "falling back to the LLM judge"
warnings).

**Acceptance Criteria:**
- [ ] User approval recorded in the log.
- [ ] `scripts/smoke_entailment_jev.py` passes against production config.
- [ ] Rollback is one env var (`ENTAILMENT_JUDGE_BACKEND=llm`).
