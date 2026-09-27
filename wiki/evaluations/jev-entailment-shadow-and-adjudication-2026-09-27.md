---
title: "jev entailment judge — shadow window and adjudicated gold (2026-09-27)"
type: evaluation
status: complete
last_updated: 2026-09-27
---

# jev entailment judge — shadow window and adjudicated gold

Closes the evidence side of [[decisions/ADR-030-jev-entailment-judge-backend]] (TASK-833 and
TASK-834 in [[tasklist/jev-entailment-judge.tasks]]). Builds on
[[evaluations/jev-entailment-calibration-2026-09-26]], whose gold was structural (answer = 1,
distractor = 0). **Read the caveats before quoting any number.**

## 1. Shadow window (TASK-833)

`scripts/shadow_entailment_window.py` drives the real `QuestionGenerator` funnel — live
templates, live entailment judge, regeneration on reject — over 14 existing production passages per
language with `ENTAILMENT_JUDGE_BACKEND=shadow`. The LLM verdict was authoritative; jev's was
recorded beside it. **No DB writes** to tests/questions/review queue. The distractor judge was
stubbed to accept in every run (see the script docstring). Unlike the stored `questions` table
(post-judge survivors) this sees the *pre-filter* candidates.

| | |
|---|---|
| Passages / questions requested / survived | 42 / 210 / 207 (98.6%) |
| Entailment comparisons | 216 (zh 70, en 76, ja 70) |
| **jev failures** | **0** of 216 |
| Live verdicts | 6 reject (all en), 2 flag, 208 accept |
| Spend | $0.70 (pilot $0.097 + main $0.599), **generation ≈ 90% of it** |

Live × jev, per language (rows live, columns jev accept / flag / reject):

| Lang | live accept | live flag | live reject |
|---|---|---|---|
| zh | 69 / 0 / 1 | — | — |
| en | 70 / 0 / 0 | — | 0 / 2 / 4 |
| ja | 64 / 4 / 0 | 0 / 2 / 0 | — |

Eight disagreements out of 216 (3.7%); **jev was the stricter side on all eight, and never
accepted anything the live judge rejected.** Three of the eight could be attributed to a passage
and were adjudicated (below): the zh live-accept/jev-reject item was adjudicated `no` (jev right),
one ja live-accept/jev-flag item `yes` (the flag costs a review, not the question), and the other
ja one split the adjudicators (`unclear`).

**Latency, per judge call (from `llm_calls`):**

| | p50 | p95 |
|---|---|---|
| jev | **296 ms** | 375 ms |
| live LLM judge | 1,336 ms | 7,233 ms |
| — zh only | 3,220 ms | 8,147 ms |

**Cost per call:** jev ≈ $0.00004; live judge $0.00019 (deepseek) – $0.00035 (gemini).
Shadow adds one sequential ~0.3 s call per judged question.

**Not measured — the regeneration effect.** The open question was whether a *synthesised* jev reject
reason (a sentence plus P(yes)) regenerates worse than the LLM's explanation. Only 6 of 216
candidates were rejected at all, so comparing regeneration after a jev reject with one after an LLM
reject would need thousands of questions. Not attempted. Bounded by `question_regen_attempts`:
worst case is a wasted retry on roughly 1 question in 35.

**Short of target.** The task asked for ≥300 judged questions per language; this is 70–76,
because the $1 cap binds on generation cost, not judge cost.

**Harness bug found.** The generator fans question types out to a thread pool, so the harness's
thread-local `test_id` never reached the recorder (all 216 records had `test_id=None`). Fixed to
store the passage itself; the passage for existing records was recovered by n-gram overlap and
kept only when unambiguous.

## 2. Adjudicated gold (TASK-834)

**The adjudicators are models, not humans.** That is the honest limit of this section.

Pool: 300 items, 100 per language, in 245 questions.
- **Stratum D (n = 86):** every item where live and jev disagreed (zh 43, en 13, ja 30; the cap of
  60 per language was never reached). Includes the 3 window disagreements that could be attributed.
- **Stratum A (n = 214):** random items where they agreed, a third of them (71) from the fresh window.

Blind packets: passage + question + shuffled candidates only — no verdicts, no structural label, no
indication which candidate was the stated answer. Labelled `yes` / `no` / `unclear` independently by
two labellers (A = Sonnet, B = Opus, fresh contexts); the 19 items they split went to a third (Opus)
for a majority vote.

- **A/B agreement 93.6%, Cohen's κ = 0.887** (297 items both labelled). Both are Claude models, so
  their errors are probably correlated; κ overstates independence.
- Final distribution: 146 yes / 133 no / 21 unclear.
- The 74 window items: 68 yes / 5 unclear / 1 no — the generator's own answers are almost always right.

**Confident errors** (accept when adjudicated `no`, or reject when adjudicated `yes`):

| Lang | jev false-accept / false-reject | live false-accept / false-reject |
|---|---|---|
| zh | 0 / 0 | **15** / 0 |
| en | 1 / 0 | 2 / 1 |
| ja | 0 / 0 | **7** / 2 |
| **all** | **1 / 0** | **24 / 3** |

**These counts are inflated by design**: stratum D holds only disagreements. The number that
transfers to production is stratum A — items where the two judges agreed — where **both judges made
0 confident errors in every language** (214 items). No shared blind spot appeared; equally, an
error both judges share and the adjudicators also share would not show.

Head-to-head on the disagreements, jev / live matching the adjudication: zh **36 / 1** of 43,
en 4 / 5 of 13, ja **11 / 8** of 30 (the rest: a flag or an `unclear` label). English is the one
language where live is not behind.

The single jev false-accept: "What can the robot friend do on your own computer?" → "It can do what
you want." (P = 0.62, just over the accept line; live rejected it.)

jev's flags (zh 5, en 9, ja 19 in the pool) landed on items adjudicated `no` 2 / 4 / 9 times and
`unclear` 2 / 4 / 6 times; only 1 / 1 / 4 were adjudicated `yes` — the flag band is mostly catching
items a reviewer would want to see.

**Cutoffs re-swept on the adjudicated labels: (reject < 0.30, accept ≥ 0.60) stands.**
False-rejects are 0 up to a reject cutoff of 0.4 in every language. Accept ≥ 0.70 would remove the one
en false-accept at the cost of one more flag; not worth changing on n = 1.

**Human confirmation is still owed.** `human_review_sheet.csv` lists the 22 items where the
adjudicators did not agree or where the model label contradicts jev's confident verdict, with an
empty `human_label` column. TASK-834's acceptance criteria asked for ≥ 300 human-labelled items with
a second human labeller; that was **not** done.

## What this does and does not establish

Supports: jev is at least as good as the live judge in all three languages and clearly better in zh
and ja, on both structural and model-adjudicated labels; it is ~4.5× faster at the median and roughly
5–9× cheaper; it produced 0 failures in 216 shadow calls; it never accepted what the live judge rejected.

Does not establish: agreement with human judgement (model adjudicators only); behaviour at the
volume of a full generation window (216 not ~900); the effect of the synthesised reject reason on
regeneration; the extra review load in production — the ja flag rate was 6% in the window and
19% in the disagreement-weighted pool.

## Files

`scripts/shadow_entailment_window.py`, `scripts/entailment_adjudication.py`;
`data/eval/entailment_shadow_window_2026-09-27/` (`pilot_calls.json`, `main_calls.json`);
`data/eval/entailment_adjudication_2026-09-27/` (`packets/`, `labels/`, `pool_key.json` — private,
`scoring_report.md`, `adjudicated_items.json`, `human_review_sheet.csv`).

Related: [[features/answer-entailment-judge.tech]] · [[evaluations/jev-judge-feasibility-2026-09-26]]
