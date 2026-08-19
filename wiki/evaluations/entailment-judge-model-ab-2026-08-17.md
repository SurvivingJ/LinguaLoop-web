---
title: Answer-Entailment Judge — Cross-Model A/B (gold-labelled)
type: evaluation
status: complete
last_updated: 2026-08-17
harness: scripts/measure_entailment_ab.py
sample: data/eval/entailment_sample_150.json
results: data/eval/entailment_ab_2026-08-17.json
---

# Answer-Entailment Judge — Cross-Model A/B

## What this settles

TASK-718 hit a wall: two judge models produced reject sets that barely
overlapped, so no *rate* could be called correct and no arm could be promoted.
Entailment is the one judge where gold labels are free, so this run scores
against labels instead of measuring a rate:

* a question's **correct answer** → entailed → judge should score HIGH (label 1)
* a question's **distractors** → not entailed → judge should score LOW (label 0)

150 frozen questions (50 zh / 50 en / 50 ja), 1 positive + 2 distractors each =
450 labelled items per arm, 6 arms, 2700 judge calls. Total spend **$0.71**.

### Scope — what this judge does, and does not, do

`test_answer_entailment` is the **answer-hallucination guard**. It is called from
`services/test_generation/agents/question_generator.py:500` as
`judge_answer_entailment(passage, question_text, answer)` and verifies that the
passage actually supports the proposed **correct answer**. It can only flag or
drop a generated question.

It is **not** the distractor judge and it has **no role in prose selection or
generation**. Three distinct `prompt_templates` rows are easily conflated:

| job | task_name | model (zh/ja) | in this A/B? |
|---|---|---|---|
| writes the passage | `prose_generation` | `qwen/qwen3.7-plus` | no |
| checks the answer isn't hallucinated | `test_answer_entailment` | this evaluation | **yes** |
| judges distractors | `cloze_distractor_judge` | `gemini-3.1-flash-lite` | no — TASK-718 |

### The negative class is a proxy — read FR and FA differently

This harness feeds **distractors** to the judge as label-0 items. That is a
measurement device to manufacture free gold labels; **production never sends this
judge a distractor.** Consequently the two error rates do not have equal standing:

* **False-reject maps directly to production** — a genuine correct answer scored
  low, i.e. a good question binned and its generation spend wasted. Load-bearing.
* **False-accept is measured on a proxy population.** It stands in for "a
  hallucinated answer slips through", using distractors as the stand-in. Real
  hallucinated answers may be easier or harder to detect than distractors.

So the ja incumbent's 8% false-accept should be read as *"worst of seven arms on
identical inputs"* — a valid ranking — and **not** as "8% of shipped answers are
hallucinated". Cross-arm comparisons hold; the absolute magnitude does not
transfer to production.

### Label caveat — quote this with every number

The labels are **structural, not human-adjudicated**. A distractor that genuinely
*is* entailed by the passage is a content bug in the distractor set, but it is
charged here to the judge as a false accept. A "correct" answer the passage does
not actually support is a generator bug charged as a false reject. Both are real
defects worth finding, but they mean **every AUC below is a lower bound, not a
point estimate**. Differences of ~0.01 AUC are not separable at n=50/language.

## Discrimination (ROC AUC — threshold-free)

| arm | model | zh | en | ja |
|---|---|---|---|---|
| **live** | zh=deepseek-chat / en=gemini-3.5-flash-lite / ja=qwen-2.5-72b | 0.999 | 0.974 | 0.932 |
| q37f | qwen/qwen3.7-flash | **1.000** | 0.995 | 0.941 |
| **dsv4f** | deepseek/deepseek-v4-flash | **1.000** | 0.985 | 0.953 |
| **ling3** | inclusionai/ling-3.0-flash | 0.999 | **0.996** | 0.955 |
| seed2m | bytedance-seed/seed-2.0-mini | 0.987 | 0.977 | **0.961** |
| glm47 | z-ai/glm-4.7-flash | 0.979 ⚠ | 0.806 ⚠ | 0.972 ⚠ |

⚠ glm47 numbers are computed on a **biased 53% subset** — see Disqualified.

zh is saturated: every usable arm is ≥0.987. **ja is where the incumbent is
weakest** (0.932) and where every challenger beats it.

## Errors at the live thresholds (accept ≥ 0.8, reject < 0.6)

False-reject = drops a good question (wasted generation spend).
False-accept = ships a hallucinated answer to a learner (**the worse failure**).

| arm | zh FR | zh FA | en FR | en FA | ja FR | ja FA |
|---|---|---|---|---|---|---|
| live | 2% | 1% | 6% | 1% | 10% | **8%** |
| q37f | 4% | **0%** | 10% | 1% | 10% | 4% |
| dsv4f | **0%** | **0%** | 4% | 2% | 8% | 4% |
| ling3 | 4% | **0%** | **0%** | 3% | 12% | 3% |
| seed2m | 6% | 1% | **0%** | 7% | 6% | **2%** |
| glm47 | 0% | 3% | 4% | **31%** | 3% | 7% |

95% Wilson CIs overlap heavily at n=50 positives / 100 negatives per language —
treat within-language ordering as suggestive, not proven.

## Score-distribution sanity check

Distinct confidence values emitted (a judge that emits 3 magic numbers cannot be
re-tuned later, however good its AUC looks today):

| arm | zh | en | ja |
|---|---|---|---|
| live | 6 | 5 | **4** ⚠ |
| q37f | 8 | 7 | 7 |
| **dsv4f** | **12** | **10** | **12** |
| **ling3** | 8 | **11** | **15** |
| seed2m | 5 | **4** ⚠ | 7 |
| glm47 | 6 | 6 | 9 |

The incumbent **ja** model is effectively a 3-value classifier
(0.0 ×61, 0.85 ×52, 0.5 ×36, 1.0 ×1) — it cannot be threshold-tuned at all.
`seed2m` on **en** is nearly as collapsed (0.0 ×93, 1.0 ×32, 0.85 ×24, 0.9 ×1),
which is why its good ja error rates do not earn it a promotion.

## JSON robustness (repair turns / primary calls)

Every repair is an extra billed call and a latency hit:

| arm | repair rate |
|---|---|
| q37f | **0%** |
| dsv4f | 1.3% |
| seed2m | 2.9% |
| ling3 | 7.7% |
| **live en (gemini-3.5-flash-lite)** | **32%** ⚠ |
| glm47 | >100% |

The incumbent EN model needs a JSON repair turn on roughly a third of calls.
That is a previously unmeasured cost and reliability tax.

## Cost — measured, not list-price

Read back from `llm_calls` (OpenRouter usage accounting), including repair turns.
Every arm judged the identical 450-item workload, so per-call is comparable.

| arm | $/call | vs incumbent | @150/mo (today) | @10k/mo | @100k/mo |
|---|---|---|---|---|---|
| **dsv4f** | 0.0000977 | **2.74× cheaper** | $0.015 | $0.98 | $9.77 |
| ling3 | 0.0001569 | 1.71× cheaper | $0.024 | $1.57 | $15.69 |
| q37f | 0.0002118 | 1.26× cheaper | $0.032 | $2.12 | $21.18 |
| live (blended) | 0.0002677 | 1.00× | $0.040 | $2.68 | $26.77 |
| glm47 | 0.0002984 | 0.90× | $0.045 | $2.98 | $29.84 |
| seed2m | 0.0004703 | **0.57× (dearer)** | $0.071 | $4.70 | $47.03 |

Per-language incumbent cost: zh (deepseek-chat) $0.000183, ja (qwen-2.5-72b)
$0.000225, en (gemini-3.5-flash-lite) $0.000366 — EN prompts are ~3× zh and ~7× ja
in length, so EN dominates absolute spend.

### The headline 5–10× cost reduction does not exist

List prices predicted it; measured cost refutes it. **Best real saving is 2.74×**,
and `seed-2.0-mini` is *1.75× more expensive* than the incumbent despite a
headline input price 3.6× lower. Output-token volume (reasoning traces), not
per-token price, dominates this workload. Any future model comparison here must
be settled on measured $/call.

### Cost is not the deciding factor at current volume

Production has run **783 entailment calls all-time** (first 2026-06-02, 150 in
the last 30 days). The best-case monthly saving today is **$0.025**. The
promotion case therefore rests entirely on **quality**; the cost table only
matters if entailment volume grows ~1000×.

## Disqualified

* **z-ai/glm-4.7-flash** — returned `RuntimeError: LLM returned empty content`
  on **210/450 (47%)** of calls. In production every one of those lands in
  `answer_entailment.py`'s except branch → `safe_accept()` → a silent
  100%-accept no-op. Its EN false-accept rate of 31% on the surviving subset is
  the second reason. **Do not use.**
* **qwen/qwen3.5-flash-02-23** — returns a bare float instead of an object on
  zh/ja; fails `AnswerEntailmentVerdict` validation. Dropped at pre-flight.
* **stepfun/step-3.5-flash** — SiliconFlow upstream: `"Json mode is not
  supported for this model"` on all three languages. Dropped at pre-flight.

## Japanese is not Chinese

Worth stating because the hypothesis going in was that Chinese-trained models
would carry ja. They do beat the incumbent — but the incumbent *is* a Qwen model,
and the ja ranking (seed2m 0.961 > ling3 0.955 > dsv4f 0.953 > q37f 0.941) does
not track "Chinese-trained" in any clean way. ja was decided by the per-language
table, not by provenance. Swallow / Nejumi rankings were not used as evidence;
neither Qwen nor DeepSeek published benchmarks for these specific flash SKUs.

## Recommendations

| lang | incumbent | recommend | AUC | error change | call |
|---|---|---|---|---|---|
| **zh** | deepseek-chat | **deepseek/deepseek-v4-flash** | 0.999 → 1.000 | FR 2%→0%, FA 1%→0% | **promote (low-stakes)** |
| **en** | gemini-3.5-flash-lite | **inclusionai/ling-3.0-flash** | 0.974 → **0.996** | FR 6%→0%, FA 1%→3% | **promote** |
| **ja** | qwen-2.5-72b | **deepseek/deepseek-v4-flash** | 0.932 → **0.953** | FR 10%→8%, FA **8%→4%** | **promote** |

**zh — promote, but the win is marginal.** Both models are at ceiling. dsv4f is
weakly dominant (equal-or-better on AUC, FR, FA), doubles the usable score scale
(6→12 values), and is 1.9× cheaper. Justified as consolidation, not as a fix.

**en — promote, strongest case in the set.** AUC 0.974→0.996, false rejects
eliminated (3/50→0/50), score scale 5→11 values, 2.3× cheaper, and it retires
the incumbent's 32% JSON-repair rate. The one regression is false-accept 1%→3%
(3/100, CI [1%,8%]) — accepted because en false-accepts are the *lowest*-risk cell
in the matrix (en AUC is 0.996, so the accepted items sit near the boundary) and
because best-achievable balanced accuracy rises 0.965→0.985.

**ja — promote, clearest quality gain.** The incumbent is a 2024 model with a
collapsed 4-value scale, the worst AUC in the matrix (0.932) and an **8%
false-accept rate** — the single worst product-risk number measured. dsv4f halves
false-accepts to 4%, lifts AUC to 0.953, and gives 12 distinct values instead of 4.
`seed2m` scores better on ja at the live thresholds (FR 6%, FA 2%, AUC 0.961) and
is the honest runner-up, but it costs **4.8×** more than dsv4f, collapses to 4
values on en, and needs the JSON-token migration. Their ja CIs overlap, so the
tie is broken on cost, scale, and operational simplicity.

**Net effect:** zh+ja on `deepseek/deepseek-v4-flash`, en on
`inclusionai/ling-3.0-flash`. Two slugs instead of three, both Chinese-trained,
both verified to work against the **raw** un-suffixed templates — so this
promotion set does **not** depend on the JSON-token migration.

## Prerequisite that is *not* triggered by this set

`migrations/entailment_json_token_zh_ja.sql` adds a "json" token to the zh + ja
templates. Measured 2026-08-17: `qwen/qwen3.7-flash` and
`bytedance-seed/seed-2.0-mini` return **HTTP 400** on the raw zh/ja templates
(`'messages' must contain the word 'json'`), which degrades to `safe_accept()` —
a silent no-op. The recommended models (dsv4f, ling3) do **not** 400, so the
migration is not a blocker here. Land it anyway as defence-in-depth: it is the
only thing standing between a future Qwen/Seed re-route and a silently disabled
judge. See [[entailment-json-object-landmine]] in agent memory.

## Addendum — `google/gemini-3.7-flash` (7th arm, run 2026-08-17)

Tested on request, same frozen 450 items, after the JSON-token migration landed
(prompts unchanged — the migration appends the byte-identical string the harness
was already appending, so all seven arms remain comparable).

| lang | AUC | FR | FA | distinct | bal-acc @live | best |
|---|---|---|---|---|---|---|
| zh | **1.000** | 6% | **0%** | 11 | 0.950 | 0.995 |
| en | 0.988 | 8% | 1% | 8 | 0.945 | 0.970 |
| ja | 0.925 | 16% | 2% | 14 | 0.880 | 0.920 |

**450/450 calls succeeded, 0 errors, 0 JSON repairs** — tied best-in-matrix for
reliability, and a big improvement on the incumbent's 32% repair rate.

**Do not promote.** Three reasons:

1. **It loses to `ling-3.0-flash` on en on every axis that matters** — AUC 0.988
   vs 0.996, false-reject 8% vs 0%, scale 8 vs 11 values, bal-acc 0.945 vs 0.960.
2. **At the live thresholds it is worse than the incumbent it would replace**
   (bal-acc 0.945 vs 0.965), because its false-reject rate doubles (3/50 → 4/50).
   Its AUC gain is real but unrealisable without re-tuning the cut points.
3. **It is the most expensive arm measured: $0.0007541/call** — 2.1× dearer than
   `gemini-3.5-flash-lite` and **4.8× dearer than `ling-3.0-flash`**, despite a
   list price that predicted the opposite. Second confirmation that this
   workload's cost is driven by output-token volume, not headline price.

Behaviourally it is a **harsh, confident** judge: it parks 63–66% of all items at
exactly 0.0 and has the highest false-reject rate of any arm on all three
languages, paired with the lowest false-accepts. If false-accepts ever become the
binding product constraint it is worth revisiting — with re-tuned thresholds.

It is also **not** a ja upgrade: AUC 0.925 is *below* the incumbent's 0.932.

## Follow-ups

* Gold set is structural only. Human-adjudicating even 30 items per language
  would convert every AUC here from a lower bound into an estimate, and is the
  cheapest available increase in confidence.
* This measures confidence-scale behaviour. TASK-723 replaces that with a 1–5
  Likert scale; re-run this harness after that lands, since the thresholds and
  the distribution table both become meaningless under a new scale.
* `dsv4f` at threshold 0.7 (zh) / 0.5 (ja) beats the live 0.8/0.6 cut points —
  worth a separate threshold-tuning pass now that a model with 12 usable values
  is in place.

## Related

- [[api/rpcs.tech]] — judge call surface
- [[tasklist/distractor-judge-calibration.tasks]] — TASK-723 Likert unification
- `scripts/measure_judge_flag_rate.py` — the rate-only predecessor (TASK-718)
