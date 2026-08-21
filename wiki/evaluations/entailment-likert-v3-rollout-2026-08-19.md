---
title: Answer-Entailment Likert v3 — Post-Rollout Band Usage and Gold Re-Measurement
type: evaluation
status: complete
date: 2026-08-19
task: TASK-723
harness: scripts/measure_entailment_ab.py
sample: data/eval/entailment_sample_150.json
results:
  - data/eval/entailment_v3_2026-08-19.json
  - data/eval/entailment_v3_ja_models_2026-08-19.json
spend_usd: 0.2135
---

# Answer-Entailment Likert v3 — Post-Rollout Band Usage and Gold Re-Measurement

Closes the two open measurement items on [[tasklist/distractor-judge-calibration]] TASK-723:
the gold-set re-measurement of v3, and per-language post-rollout band usage.

---

## 0. Cutover state (verified before measuring)

| Move | State |
|---|---|
| Deploy code | Done — committed, not just working tree. `git diff HEAD` clean for `services/`. `answer_entailment._is_pre_likert` present and gating. |
| Activate v3 | Done — zh/en/ja v3 all `is_active = true`, all six rows share `updated_at` 2026-08-19 10:11:32Z (one transaction). |
| Restart | **Moot, not skipped.** No app process exists. The only running Python processes were VS Code isort LSP servers; no listener on any of 3000/5000/5001/8000/8080/8888. |

`_cfg_cache` is process-lifetime and never invalidated, so a process that had judged before
10:11:32Z would still hold v1/v2 and would `safe_accept()` everything via `_is_pre_likert` — the
answer-hallucination guard silently off. **That did not happen, because there is no such process.**
The next app start loads v3 cleanly.

### The "no telemetry" premise was a query artefact

The task brief recorded zero `llm_calls` rows for `test_answer_entailment` and inferred the live
judge might not log at all. It logs fine. `test_answer_entailment` is the **`prompt_templates`
key**; the **`llm_calls` label is `judge_answer_entailment`** (the `judge_` prefix is set at
`answer_entailment.py:75`). Under the correct label there are 784 production rows,
`pipeline='test_gen'`, spanning 2026-06-02 → 2026-08-16.

**No telemetry gap exists and no task is needed for one.** The real fact is narrower and still
worth stating: every production row is `template_version = 1`, and the newest is 2026-08-16
21:15:04Z — before the v3 activation. So no v3 traffic had ever run. That is why band usage had to
be measured on the harness rather than on production traffic.

---

## 0b. Production-path smoke — the gap the A/B harness could not close

`measure_entailment_ab.py` calls `call_llm` directly with `AnswerEntailmentVerdict`, so it
**bypasses the production wrapper entirely**: no `_load_cfg`, no `_is_pre_likert`, no
`likert_to_verdict`, no `log_judge_verdict`. Everything in §2–§5 therefore validates the *prompt and
the model*, not the *plumbing* — and `llm_calls` held zero rows at `template_version = 3`, so the
two had never run together against the live row.

`scripts/smoke_entailment_production_path.py` closes that. It calls `judge_answer_entailment`
exactly as `question_generator.py:500` does, on blunt fixtures (one clearly-supported answer, one
clearly-unrelated answer per language) where a disagreement means broken wiring, not a hard item.

**6/6 pass, all three languages.**

| lang | live row | supported answer | unrelated answer |
|---|---|---|---|
| zh | v3, `deepseek/deepseek-chat` | accept, rating 5 | reject, rating 1 |
| en | v3, `google/gemini-3.5-flash-lite` | accept, rating 5 | reject, rating 1 |
| ja | v3, `google/gemini-3.5-flash-lite` | accept, rating 5 | reject, rating 1 |

What this proves that the A/B could not:

1. **The version gate does not fire.** `_is_pre_likert` passes on all three live rows, so the judge
   is genuinely judging rather than degrading to `safe_accept()` — the answer-hallucination-guard-off
   failure mode. The smoke treats a missing rating as a failure even on the *accept* fixture,
   because a dead judge and a healthy accept are otherwise indistinguishable.
2. **ja picked up the model swap.** The process started fresh, so `_cfg_cache` loaded ja on
   `google/gemini-3.5-flash-lite` — §4 applied and readable through the production loader.
3. **Telemetry lands.** First-ever `template_version = 3` rows in `llm_calls`,
   `pipeline='test_gen'`.
4. **`judge_confidence` now carries the Likert rating, and the two scales no longer collide.**

   | model | verdict | `judge_confidence` |
   |---|---|---|
   | deepseek-chat / gemini-3.5-flash-lite | accept | **5** |
   | deepseek-chat / gemini-3.5-flash-lite | reject | **1** |

   No `0.8` probability constant appears. This is the collision `null_legacy_judge_confidence.sql`
   erased 888 rows to clear, verified closed on the live path rather than assumed from the code.

**Cost note:** these calls log under the **production** pipeline (`test_gen`), not `diag` — that is
what makes them a production-path proof. 7 calls, $0.00105, visible in production cost reporting.

---

## 1. Are the zh/ja v3 prompts genuinely band-anchored?

**Yes. All three are faithful translations of each other.** This was worth checking: the bodies are
402 (zh) / 1101 (en) / 494 (ja) characters, and en is 2.7× zh, which looks like an abbreviated
paraphrase in two of three languages.

It is not. The length gap is entirely CJK character density. Each of the three carries, in full:

- the single-axis restriction ("rate the strength of textual support only, not how well written,
  how difficult or how interesting the question is");
- all five band definitions, individually anchored;
- the tie-break rule ("choose the highest rating whose description is fully true; if between two,
  choose the lower");
- the JSON output contract with a worked example.

The bands are mutually exclusive on one axis, as designed: 4-vs-3 turns on *uniqueness*, 2-vs-1 on
*absence vs contradiction*. `scripts/audit_prompt_latin.py --task test_answer_entailment
--all-versions` returns **CLEAN** for zh v2/v3 and ja v2/v3, CJK ratio 0.971 / 0.979, zero leaks.

The literal `JSON` token survives in both zh and ja v3, so the Alibaba/Qwen `json_object` 400 that
`entailment_json_token_zh_ja.sql` fixed has not been reintroduced.

---

## 2. Gold-set re-measurement — it was never blocked

The brief carried the gold set forward as a blocker shared with TASK-719/720. **For entailment that
is not true, and the harness's own docstring says so.** Entailment gold labels are *structural and
free*: a question's correct answer is entailed by its passage by construction (label 1), and its
distractors are not (label 0). No human adjudication is required.

The blocker is real for TASK-719/720, which judge *distractor plausibility* — "is this distractor
confusable" has no structural label and does need adjudication. The two cases were being treated as
one. They are separable, and the entailment half ran today.

**Label caveat, which bounds every number below.** The labels are structural, not human-adjudicated.
A distractor that genuinely *is* entailed is a content bug charged here to the judge as a false
accept; a "correct" answer the passage does not support is a generator bug charged as a false
reject. AUC is therefore a **lower bound** on judge quality, not a point estimate.

### Live arm, v3 prompt, each language on its configured model

150 questions (50/language), 1 positive + 2 negatives each = 450 judge calls.

| lang | model | n+ | n− | AUC | mean+ | mean− | gap |
|---|---|---|---|---|---|---|---|
| zh | `deepseek/deepseek-chat` | 50 | 100 | **0.990** | 4.66 | 1.60 | 3.06 |
| en | `google/gemini-3.5-flash-lite` | 50 | 100 | **0.982** | 4.48 | 1.32 | 3.16 |
| ja | `qwen/qwen-2.5-72b-instruct` | 50 | 100 | **0.870** | 3.96 | 2.40 | 1.56 |
| **ALL** | | 150 | 300 | **0.957** | | | |

---

## 3. Band usage, measured (not assumed)

Full 1–5 distribution, v3 prompt, 150 ratings per language. `pos` should sit high, `neg` low.

**zh — `deepseek/deepseek-chat`**

| band | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| all | 57 | 30 | 10 | 19 | 34 |
| pct | 38.0% | 20.0% | 6.7% | 12.7% | 22.7% |
| pos (50) | 0 | 0 | 0 | 17 | 33 |
| neg (100) | 57 | 30 | 10 | 2 | 1 |

**en — `google/gemini-3.5-flash-lite`**

| band | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| all | 76 | 23 | 1 | 19 | 31 |
| pct | 50.7% | 15.3% | 0.7% | 12.7% | 20.7% |
| pos (50) | 0 | 3 | 0 | 17 | 30 |
| neg (100) | 76 | 20 | 1 | 2 | 1 |

**ja — `qwen/qwen-2.5-72b-instruct`** (as measured; since replaced — §4)

| band | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| all | 33 | 17 | 37 | 55 | 8 |
| pct | 22.0% | 11.3% | 24.7% | 36.7% | 5.3% |
| pos (50) | 1 | 0 | 4 | 40 | 5 |
| neg (100) | 32 | 17 | 33 | 15 | 3 |

**All five bands fire in all three languages. Zero unparsed responses in 450 calls.**

This is the first time any judge in this family has achieved that. The contrast with the distractor
judge is the point of the exercise: TASK-717 §2 established that zh/ja v4 distractor prompts each
contained a worked band-3 example and `qwen3.6-flash` still emitted **zero** 3s across 150
distractors, and band 1 fired 3 times in 1,800 ratings across two models. Here band 3 fires 10 / 1 /
37 and band 1 fires 57 / 76 / 33.

The lesson from TASK-717 still stands and is not contradicted: anchoring bands does not *make* a
small model use them. What changed here is that the entailment question is genuinely one axis, so
the anchors describe distinctions the model can actually make. The distractor judge's bands still
conflate two axes, which is why TASK-719 remains necessary.

**Caveat on band 3 as a review channel.** Band-3 volume is not evidence of useful review signal. In
zh and en every band-3 was a *negative* (10/10 and 1/1) — the band is catching under-determined
distractors, which is what it is for. In ja under qwen, 33 of 37 were negatives but the band was
absorbing items the other two languages resolved to 1 or 2, i.e. indecision, not nuance.

---

## 4. ja was the model, not the language

ja was the clear outlier: AUC 0.870 against 0.990/0.982, false-accept 18/100, and a 24.7% band-3
review load. Holding the v3 prompt fixed and varying **only** the model (TASK-717's discipline),
on the same 150-question sample:

| ja arm | AUC | false-accept | false-reject | band-3 load | bal-acc @live thr |
|---|---|---|---|---|---|
| `qwen/qwen-2.5-72b-instruct` (was live) | 0.870 | 18/100 (18%) | 1/50 (2%) | 24.7% | 0.695 |
| **`google/gemini-3.5-flash-lite`** | **0.940** | **2/100 (2%)** | 5/50 (10%) | 2.7% | **0.915** |
| `deepseek/deepseek-chat` | 0.798 | 33/100 (33%) | 4/50 (8%) | 4.0% | 0.760 |

Pairwise on disagreements: gemini right 34, deepseek right 2, both wrong 4.

Since zh and en score 0.99/0.98 on the *same* prompt, and the ja prompt audits CLEAN with all five
bands anchored, the deficit is neither the ja prompt nor ja content. **It is the model** — the same
conclusion TASK-718 reached about qwen for the distractor judge. This entailment row was the one
active judge row the 2026-08-16 sweep (`consolidate_gemini_on_3_5_flash_lite.sql`) could not reach,
because that sweep moved *gemini* rows and this row was on qwen.

**Applied live 2026-08-19** — `migrations/entailment_ja_v3_onto_gemini_3_5_flash_lite.sql`. Only the
`model` column changed; ja v3 body length 494 and md5 `df168c48f2b9b92ea53715438788b680` verified
unchanged on readback.

The trade is 18% → 2% false-accept for 2% → 10% false-reject. This judge is the answer-hallucination
guard: a false accept ships an unsupported answer to a learner, a false reject regenerates a
question. The trade runs in the direction the guard exists for. Under the structural-label caveat,
part of that 10% is generator defect rather than judge error.

Post-swap ja band usage (all five bands still used, review load now proportionate):

| band | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| all | 82 | 18 | 4 | 16 | 30 |
| pos (50) | 4 | 1 | 1 | 15 | 29 |
| neg (100) | 78 | 17 | 3 | 1 | 1 |

---

## 5. Threshold check

Best single threshold swept over observed scores lands on **4.0 for every language and every model
arm tested** — identical to the deployed `LIKERT_ACCEPT`. The live cut points are in the right
place; no retune is indicated.

| arm | best thr | bal-acc @best | bal-acc @live |
|---|---|---|---|
| zh deepseek-chat | 4.0 | 0.985 | 0.935 |
| en gemini-3.5-flash-lite | 4.0 | 0.955 | 0.950 |
| ja qwen-2.5-72b | 4.0 | 0.860 | 0.695 |
| ja gemini-3.5-flash-lite | 4.0 | 0.930 | 0.915 |

---

## 6. Spend

All diagnostic, `pipeline='diag'`, so production cost reporting is uncontaminated.

| run | calls | USD |
|---|---|---|
| live arm, zh+en+ja, v3 | 448 | 0.1238 |
| ja model A/B (gemini, deepseek) | 300 | 0.0897 |
| **total** | **748** | **0.2135** |

Against a $3.00 budget — **$2.79 unspent**.

---

## Related Pages

- [[tasklist/distractor-judge-calibration]] — TASK-723
- [[evaluations/entailment-judge-model-ab-2026-08-17]] — prior float-scale A/B on the same sample
- [[evaluations/distractor-judge-language-divergence-2026-08-16]] — the two-axis band problem this
  judge avoids and the distractor judge still has
