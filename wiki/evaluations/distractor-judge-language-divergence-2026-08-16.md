---
title: "Distractor Judge — ZH/JA Language Divergence Analysis (2026-08-16)"
type: evaluation
status: complete
date: 2026-08-16
harness: scripts/measure_judge_flag_rate.py (150 questions / 450 distractors, 50 per language)
prompt_version: test_distractor_plausibility v4 (live)
judge_models: all three languages google/gemini-3.1-flash-lite — zh/ja moved off qwen/qwen3.6-flash by TASK-718 (§11)
open_questions:
  - "ANSWERED (§11): the zh gap is judge-driven. Under a common judge, zh rejects at 2% vs en 4% and ja 6% — the cleanest of the three, not the worst."
  - "OPEN: no judge's reject signal is validated in absolute terms. The two models' reject sets are near-disjoint, so a gold set is still owed (TASK-719/720)."
---

# Distractor Judge — ZH/JA Language Divergence Analysis (2026-08-16)

Follow-up to the v4 Likert migration. The v4 measurement showed a flag channel that only ever
fires in English and a zh reject rate 7× the English one. This page establishes **why**, from the
prompt text and the 450-distractor sample, and separates the three independent causes.

**Headline: the zh reject rate is mostly a judge artefact, not weaker zh content.** But a real
zh/ja content defect exists in the generator prompts, independently of the judge.

---

## 1. Measured distribution

n = 50 questions per language, 3 distractors each. Re-derived from the surviving
`flag_rate_results.json` / `flag_rate_sample.json` sample.

| lang | 1 | 2 | 3 | 4 | 5 | reject (question-level) |
|------|---|---|---|---|---|---|
| zh | 0 | 24 | **0** | 42 | 84 | 15/50 = **30%** |
| en | 0 | 2 | 4 | 68 | 76 | 2/50 = **4%** |
| ja | 0 | 6 | **0** | 57 | 87 | 6/50 = **12%** |

Two facts not previously recorded:

1. **Every zh and ja reject is a rating of 2. Not one rating of 1 exists in 450 distractors.**
   Band 1 is "also arguably a correct answer" — the oversharp-distractor case this judge was built
   to catch, per its own module docstring. It has caught **zero**. The judge is currently doing
   topical screening only, not the job it exists for.
2. **`qwen3.6-flash` uses {5, 4, 2}; `gemini-3.1-flash-lite` uses {5, 4, 3, 2}.** Band 2 on qwen is
   therefore a catch-all for "anything that is not a clean accept", which is the entire mechanism
   behind the missing middle in zh/ja.

### Rejects by question type

| type | zh | en | ja |
|------|----|----|----|
| `vocabulary_context` | **8/16 (50%)** | 0/12 | 1/13 |
| `author_purpose` | 3/7 | 0/8 | 0/9 |
| `literal_detail` | 2/10 | 0/11 | 2/12 |
| `inference` | 1/10 | 2/9 | 2/9 |
| `main_idea` | 1/3 | 0/8 | 0/5 |
| `supporting_detail` | 0/4 | 0/2 | 1/2 |

**Excluding `vocabulary_context`: zh 21%, ja 14%, en 5%.** Roughly half the zh excess is a single
question type where the rubric is structurally misapplied.

---

## 2. Cause A — the judge prompt is NOT the source of the divergence

All three v4 templates were diffed. They are faithful translations of one another: same
"READ THIS FIRST" corrective paragraph, same 5-point anchors, same worked example, same
`{{"1": [rating, reason]}}` output contract. **The zh and ja prompts each contain a worked
band-3 example and the model still never emits a 3.**

Prompt drift is ruled out. The missing middle is model behaviour.

---

## 3. Cause B — the scale conflates two orthogonal axes

The five bands do not measure one quantity:

- Bands **5 / 4 / 2** measure *topical distance from the passage*.
- Bands **3 / 1** measure *confusability with the correct answer*.

A model must collapse a two-dimensional judgment into a single integer. `gemini-3.1-flash-lite`
spreads across both axes; `qwen3.6-flash` commits to the topical axis and slides to 2 for anything
it will not accept.

Bands 3 and 1 also **overlap semantically**: band 3 is "essentially a paraphrase of the correct
answer" and band 1 is "also arguably a correct answer". A near-paraphrase of the answer *is*
arguably correct. The boundary is a judgment of degree, which is exactly what a small model
collapses.

**Even the English band-3 flags do not match the rubric.** All four:

| correct answer | flagged distractor | is it a paraphrase of the answer? |
|---|---|---|
| Drag | "Push up" | No — it paraphrases *Lift*, a different option |
| Arrows | "Triangles" | Shape-adjacent at best |
| To remain in one's residence | "To play games using a computer" | No — arguably band 2 |
| Leading or at the forefront of | "Observing from a detached perspective" | No — near-opposite |

`gemini` is using band 3 as a generic "unsure" band. That is arguably what a review queue *wants*,
but it is not what the rubric says, so **the entire review queue rests on a signal no model applies
as written**.

---

## 4. Cause C — the rubric is ill-posed for half the question types

The band-2 test asks "does this belong to the same subject as the passage". That is sound for
`literal_detail`, `supporting_detail` and `inference`, where distractors are same-domain facts. It
is a **category error** for:

- **`vocabulary_context`** — distractors are competing *word senses*. They should relate to the
  target word, not the passage topic.
- **`author_purpose` / `main_idea`** — distractors are competing *authorial intents*, not topics.
  "Same subject as the passage" is not a well-formed question about an intent.

Worked example from the sample (zh, `vocabulary_context`): an aviation passage asks what 跑 means.
Correct answer 移动. Distractors 跳跃 / 滑倒 / 休息 — three well-formed competing senses — were all
scored **2, "belongs to a different subject"**. They are supposed to.

### The spec/implementation gap

`services/exercise_generation/judges/distractor_plausibility.py:89-93` states that `type_code`
exists so "the type lets the judge treat a vocabulary distractor (an alternate word sense)
differently from a literal-detail distractor (a same-domain fact)".

**The prompt body never implements this.** It renders `题目类型：{4}` and gives no type-conditional
rule anywhere in any of the three languages. The behaviour is specified in a docstring and was
never written into the prompt.

### The domain slot is dead in production

`judge_distractor_plausibility(..., keywords=...)` fills prompt slot `{5}`
(`本文章的学科／领域（关键词）：{5}`). **The sole caller —
`services/test_generation/agents/question_generator.py:480` — never passes it**, so it always
renders the fallback "(infer the subject from the passage above)".

Band 2 *is* a domain-membership test, and the judge is being asked to invent the domain boundary
itself. A model that infers narrowly rejects; one that infers broadly accepts. This is precisely
the qwen/gemini split.

---

## 5. Are the zh rejects real? Mostly not

All 7 non-`vocabulary_context` zh rejects were read individually. Roughly 6 are **false rejects of
the exact type the prompt's own corrective paragraph warns against**:

| passage subject | rejected distractor (rated 2 = "different subject") | assessment |
|---|---|---|
| fast fashion & water/environment | 解释如何通过回收旧衣服解决环境污染 | False — same subject; a *further* option scored 4 |
| printing press & book access | 因为人们不想读书 | False — passage is about books and reading |
| SaaS AI-compliance governance | 呼吁政府加强对AI企业的监管力度 | False — passage is about AI regulation |
| home composting | 强调家庭堆肥的技术优越性 | False — names the passage's own topic |
| home composting (inference) | 帮助他们掌握微生物学的专业知识 | Probably false — composting passages discuss microbes |
| virtual worlds / "code-woven universe" | 强调虚拟世界的技术复杂性 | False — same subject |
| biodegradable plastic & bacteria | 金属颗粒 | **Defensible** — metal is a different material domain |

The scoring is not merely harsh, it is **incoherent**: in several cases a topically nearer option
scored 2 while a further one scored 4 or 5. A consistent pattern in the false rejects is that the
option is topically right but *rhetorically* wrong (for `author_purpose`, "an intent the author
did not have"), and qwen — having no band for "wrong but well-formed" — reaches for 2.

**Conclusion:** ~6 of 7 non-vocab zh rejects and most of the 8 vocab rejects are judge artefacts.
The zh generator is not producing 30%-bad distractors. TASK-718 settles the residual.

---

## 6. The real zh/ja content defect (independent of the judge)

Found while diffing the generator prompts. It does not show up in the reject numbers but should be
fixed regardless.

**The zh and ja `question_vocabulary_context` generator prompts are literal translations that kept
the English lexical targets.** The zh prompt instructs the model with the examples `'bright'`,
`'pick up'`, and `'turn a blind eye'`, and its few-shot passages are Chinese with English idioms
embedded:

> 段落：「风暴过后，社区居民团结起来，共同'pick up the pieces'，重建失去的一切。」

The ja version glosses the English into the Japanese passage:
「事態を収拾し（pick up the pieces）、失われたものを再建した。」

So a Chinese vocabulary-question generator is few-shotted on **English phrasal verbs**, a category
that does not exist in Chinese. The natural analogue (成语 / 惯用语 for zh; 慣用句 / 四字熟語 for
ja) is never mentioned. The advanced-level rule "MUST ask about an idiom, phrase, or multi-word
expression, NOT a single word" is transplanted unchanged from English, where it means something
different.

Latin-run counts confirm the contamination is specific to this type: `question_vocabulary_context`
has 19–20 Latin runs in zh/ja vs 9–14 for the other five types (those are JSON keys, which are
expected).

**Separately: no generator prompt in any language contains a single line of distractor guidance.**
All 6 types × 3 languages describe only how to build the *question*. The elaborate distractor
rubric exists only on the judge side; the generator has never been told any of it. This is the
root asymmetry — content is being filtered against a specification it was never given.

This is the same class of defect as [[tasklist/ladder-numeric-keys.tasks]] (English field names
pulling ZH/JA generation toward English), one layer up: English *content* rather than English keys.

---

## 7. Reject routing — confirmed

**Rejects do not queue.** `question_generator.py:498-508` returns `(None, rejection)`; the question
is dropped and the record goes to `last_rejections`, a regen-feedback diagnostic.
`orchestrator.py:66` writes `generation_review_queue` rows **solely** from `_judge_flags`, i.e.
band 3 only.

Therefore the human review load is **2.7%, not 18%** — and because zh/ja never produce a 3, they
contribute exactly zero queue entries. The queue is an English-only channel in practice.

---

## 8. Caveat on these numbers

The measurement harness passed `question_type_id` (a bare integer) into prompt slot `{4}`, so the
judge saw `题目类型：2` where production sends the string `vocabulary_context`. Since the prompt
carries no type-conditional rule, the effect is likely small — but **the measured zh reject rate is
probably a mild over-estimate of production**. Any re-measurement (TASK-717) must pass the string.

---

## 10. TASK-717 outcome — the fix was measured and did not work

Added 2026-08-16, after §1–§9. **Both hypotheses in §4 were tested and both are wrong.** v5 was
built, applied, measured and rolled back the same day; v4 is live again.

Four arms, the same frozen 150-question sample, identical content, models unchanged
(zh/ja `qwen3.6-flash`, en `gemini-3.1-flash-lite`). 600 judge calls, **$1.48**.

| arm | prompt | slot `{4}` | slot `{5}` | what it isolates |
|-----|--------|-----------|-----------|------------------|
| B | v4 | type_code string | — | corrected baseline |
| D | v4 | type_code string | subject | the caller fix alone |
| C | v5 | type_code string | — | the type-conditional rubric alone |
| A | v5 | type_code string | subject | both (what was briefly live) |

### Question-level rejects

| lang | §1 published | B | D | C | A |
|------|----|----|----|----|----|
| zh | 15/50 (30%) | 18/50 (36%) | 18/50 (36%) | 17/50 (34%) | 15/50 (30%) |
| en | 2/50 (4%) | 2/50 (4%) | 2/50 (4%) | **5/50 (10%)** | **4/50 (8%)** |
| ja | 6/50 (12%) | 6/50 (12%) | **8/50 (16%)** | 4/50 (8%) | **11/50 (22%)** |

### Rejects by type — `B>D>C>A`

| type | zh | en | ja |
|------|----|----|----|
| `vocabulary_context` | **9>9>9>9** /16 | 0>0>**5**>**4** /12 | 2>1>1>2 /13 |
| `author_purpose` | 2>1>1>2 /7 | 0>0>0>0 /8 | 1>0>0>**3** /9 |
| `inference` | 5>3>5>3 /10 | 1>2>0>0 /9 | 1>2>1>**3** /9 |
| `literal_detail` | 2>2>1>0 /10 | 1>0>0>0 /11 | 1>**3**>1>2 /12 |
| `main_idea` | 0>2>0>1 /3 | 0>0>0>0 /8 | 0>0>0>0 /5 |
| `supporting_detail` | 0>1>1>0 /4 | 0>0>0>0 /2 | 1>2>1>1 /2 |

Band-2 distractor counts attribute the two harms independently — en tracks the rubric block
(1, 2 → 9, 9), ja tracks the subject line (7, 4 → 11, 13), each in two arms:

| band 2 | B | D | C | A |
|--------|---|---|---|---|
| zh | 29 | 26 | 27 | 25 |
| en | 1 | 2 | **9** | **9** |
| ja | 7 | **11** | 4 | **13** |

### Findings

1. **zh `vocabulary_context` is 9/16 in all four arms.** Completely invariant to the type
   string, the type-conditional rubric and the subject line. §4 called this a rubric
   mis-specification; it is not — it is model behaviour, consistent with facts 1–2 in the
   tasklist preamble (`qwen3.6-flash` collapses to {5, 4, 2} regardless of instruction).
   **This makes [[tasklist/distractor-judge-calibration.tasks]] TASK-718 the load-bearing task,
   not TASK-717.**
2. **The type-conditional rubric backfired in English**, creating 5 `vocabulary_context`
   rejects where v4 had 0. The zh/en/ja bullet closed with "2 is reserved for an option that
   is not a possible meaning of the expression at all" — intended to *narrow* band 2, it
   instead named a condition under which band 2 applies to vocabulary questions, and gemini
   began applying it. Naming a reject condition increases its use even inside a sentence that
   restricts it.
3. **§4's domain-slot argument is backwards.** Supplying an authoritative subject line was
   expected to loosen the off-topic band. It tightened it: "concept + five keywords" (en median
   128 chars) is a *narrower* membership test than one inferred from a whole passage. ja rose in
   both arms containing it; zh and en did not move.
4. **§8's caveat is also backwards.** Passing the `type_code` string instead of the integer did
   not expose the published baseline as an over-estimate — zh went 15 → 18. The
   integer-vs-string difference is noise, and §1's numbers stand as written.

### What shipped

The caller plumbing (`keywords=` reaching the template) is correct and stays, with a
mutation-verified regression test. It is gated behind `JUDGE_SUBJECT_KEYWORDS`, **default off**,
so production sits at arm B — the pre-task baseline. The off-state is pinned by tests precisely
so it cannot decay back into the silent dead-parameter bug this task set out to fix. The v5 rows
remain in `prompt_templates` with `is_active = false` for TASK-718 to re-test under a different
model.

---

## 11. TASK-718 outcome — it is the judge, and the model swap fixes it

Added 2026-08-16, after §10. **Verdict: judge-driven.** The zh reject rate is an artefact of
`qwen3.6-flash` scoring Chinese. Content contribution is indistinguishable from zero.

Harness promoted out of the scratchpad to `scripts/measure_judge_flag_rate.py` (`--judge-model`,
multi-arm, `--report-only`). Same frozen 150-question sample as §1 and §10 — identical content in
every arm, so the only variables are prompt version and judge model. Subject line **off** (slot
`{5}` renders the fallback), matching production's `JUDGE_SUBJECT_KEYWORDS` default. 600 calls,
11 min, **$1.11**.

The design is wider than the task asked for, deliberately. The brief specified v5 only, but v5 is
reverted and **v4 is live**, so a model decision measured on v5 could not be applied to the `model`
column without extrapolation. Running the full 2×2×3 factorial also puts **qwen on English** — the
crossover cell the original design omitted, and the one that separates "this model is harsh" from
"this model is harsh *at Chinese*".

### Question-level rejects

| lang | v4·qwen | v4·gemini | v5·qwen | v5·gemini |
|------|---------|-----------|---------|-----------|
| zh | **16/50 (32%)** | **1/50 (2%)** | 16/50 (32%) | 2/50 (4%) |
| en | 5/50 (10%) | 2/50 (4%) | 6/50 (12%) | 5/50 (10%) |
| ja | 4/50 (8%) | 3/50 (6%) | 8/50 (16%) | 3/50 (6%) |

Read the columns, not the rows. Under a **common judge (gemini)** the three languages sit at
zh 2%, en 4%, ja 6% — **zh is the cleanest of the three, not the worst.** Under the other common
judge (qwen) they sit at zh 32%, en 10%, ja 8%. So qwen is mildly harsher everywhere *and*
catastrophically harsher on Chinese specifically. The published headline was zh 30% against
en 4%, a 26pp gap; under a single judge that gap is **−2pp**. Essentially 100% of it was the judge.

### Rating distribution — the middle band returns

Distractor level, n = 150 per cell.

| arm | lang | 1 | 2 | 3 | 4 | 5 | bands used |
|-----|------|---|---|---|---|---|---|
| v4·qwen | zh | 0 | 25 | **0** | 37 | 88 | {5,4,2} |
| v4·qwen | en | 0 | 10 | **0** | 44 | 96 | {5,4,2} |
| v4·qwen | ja | 0 | 4 | 1 | 52 | 93 | {5,4,3,2} |
| v4·gemini | zh | 0 | 1 | **1** | 62 | 86 | {5,4,3,2} |
| v4·gemini | en | **1** | 1 | 5 | 63 | 80 | {5,4,3,2,1} |
| v4·gemini | ja | 0 | 3 | **2** | 78 | 67 | {5,4,3,2} |
| v5·qwen | zh | 0 | 26 | 0 | 32 | 92 | {5,4,2} |
| v5·qwen | en | 0 | 8 | 0 | 39 | 103 | {5,4,2} |
| v5·qwen | ja | **1** | 7 | 0 | 46 | 96 | {5,4,2,1} |
| v5·gemini | zh | 0 | 5 | 0 | 48 | 95 | {5,4,2} |
| v5·gemini | en | **1** | 10 | 1 | 36 | 102 | {5,4,3,2,1} |
| v5·gemini | ja | 0 | 3 | 2 | 65 | 80 | {5,4,3,2} |

**gemini produces a middle band in zh and ja on the live v4 prompt** (1 and 2 respectively). Thin,
but the review queue stops being English-only for free — which weakens much of TASK-719/720's
motivation, exactly as the task's technical note predicted.

**Band 1 fired for the first time.** §1 fact 1 recorded zero band-1 ratings in 450 distractors;
across these 1,800 there are three (gemini·en on both prompts, qwen·ja on v5). Still vanishingly
rare, so the "band 1 has never caught the case it exists for" finding stands in substance.

### The decisive table — the two judges disagree almost completely

Distractor-level cross-tab on v4, rows = qwen's rating, columns = gemini's:

| zh | g=1 | g=2 | g=3 | g=4 | g=5 |
|----|-----|-----|-----|-----|-----|
| **q=2** (qwen rejects) | 0 | **0** | **0** | **19** | **6** |
| q=4 | 0 | 0 | 0 | 16 | 21 |
| q=5 | 0 | 1 | 1 | 27 | 59 |

**Every one of the 25 zh distractors qwen rejected was rated 4 or 5 by gemini** — six of them at the
very top of the scale. Not one landed in gemini's own reject or review band.

Question-level, the reject *sets* are disjoint:

| v4 | both | qwen only | gemini only | neither |
|----|------|-----------|-------------|---------|
| zh | **0** | 16 | 1 | 33 |
| en | **0** | 5 | 2 | 43 |
| ja | 1 | 3 | 2 | 44 |

Across 150 questions the two judges agree on **one** reject. Exact rating agreement is 50–56%, but
that is carried entirely by the accept mass; on the class that actually gates content, agreement is
approximately zero.

### Per-type — the load-bearing bucket moves with the model and nothing else

Rejects, `v4·qwen > v4·gemini > v5·qwen > v5·gemini`:

| type | zh | en | ja |
|------|----|----|----|
| `vocabulary_context` | **9>1>11>2** /16 | 1>1>2>**5** /12 | 1>1>1>1 /13 |
| `inference` | 4>0>4>0 /10 | 2>0>2>0 /9 | 1>1>3>1 /9 |
| `literal_detail` | 1>0>1>0 /10 | 1>0>1>0 /11 | 1>1>3>1 /12 |
| `author_purpose` | 1>0>0>0 /7 | 0>1>0>0 /8 | 0>0>0>0 /9 |
| `main_idea` | 1>0>0>0 /3 | 1>0>1>0 /8 | 0>0>0>0 /5 |
| `supporting_detail` | 0>0>0>0 /4 | 0>0>0>0 /2 | 1>0>1>0 /2 |

zh `vocabulary_context` held at **9/16 across all four TASK-717 prompt configurations** and is
**1/16** the moment the model changes. §10 finding 1 was right that this is model behaviour; this
run shows it is also *fixable* by changing the model.

### Harness validation

Cells whose configuration matches a previous run reproduce it:

- en·gemini·v4 → 2/50, matching §1 (2/50) and §10 arm B (2/50).
- en·gemini·v5 `vocabulary_context` → 5/12, matching §10 arm C (5/12) exactly.
- zh·qwen·v4 → 16/50, against §1's 15/50 and arm B's 18/50 — run-to-run spread of 15–18 at
  temperature 0, which bounds the noise on every number here at roughly ±3 questions.

### v5 is still dead

v5 is neutral-to-harmful under **both** models (en 2→5 under gemini; ja 4→8 under qwen), so §10's
revert stands and the rows stay inactive. Their `model` column was updated with v4's anyway, so
activating v5 later cannot silently restore qwen.

### Decision applied

`migrations/distractor_judge_model_zh_ja_gemini.sql` — zh and ja (v4 live + v5 retained) moved to
`google/gemini-3.1-flash-lite`. **Applied live 2026-08-16**; all three active rows now share one
judge model. Secondary benefit: gemini is **6.7× cheaper** ($0.00047/call vs $0.00313 over 300 calls
each), so the judge's per-call cost on zh/ja drops ~85%.

### Limitations — read before treating 2% as the true rate

1. **This proves qwen's zh rejects are not reproducible; it does not prove gemini's acceptances are
   correct.** With inter-judge agreement on rejects near zero, neither model's reject signal is
   validated in absolute terms. The corroboration for "the rejects were false" is the manual read in
   §5, not this experiment.
2. **gemini did not reproduce the one zh reject §5 judged defensible** (金属颗粒 for a
   biodegradable-plastic passage). Its single zh reject is a different item — a `vocabulary_context`
   distractor 发出声音 for 用力, which is a reasonable call. So the swap plausibly trades some recall
   for a large precision gain, and the size of that trade is unmeasured.
3. A gold set remains owed. That is the real prerequisite for TASK-719/720, and it is now the
   binding constraint rather than the two-axis redesign.

---

## 9. Related pages

- [[tasklist/distractor-judge-calibration.tasks]] — TASK-717–722, the fix breakdown
- [[evaluations/exercise-pipeline-eval-2026-06-09]] — earlier judge-layer eval; "cloze judge ships
  rejected distractors anyway" is a sibling of the reject-routing finding in §7
- [[tasklist/ladder-numeric-keys.tasks]] — the English-contamination fix one layer down
- [[features/comprehension-tests.tech]] — the pipeline this judge gates
- [[reviews/exercise-generation-audit-2026-06-07]] — prior finding of English-centric validation
