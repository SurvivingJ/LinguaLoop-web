---
title: "jev vs live answer-entailment judge — cutoff calibration (2026-09-26)"
type: evaluation
status: complete
last_updated: 2026-09-26
---

# jev vs live answer-entailment judge — cutoff calibration

Follow-up to [[evaluations/jev-judge-feasibility-2026-09-26]] §3.2. That page showed
`typesafe/jev-1.13` separates entailed answers from distractors almost perfectly
(AUC 1.000 zh / 0.9996 en / 0.969 ja). This run does the part the feasibility study left
open: choose accept / flag / reject cutoffs from data, and lay jev next to the live judge
item by item. Outcome: [[decisions/ADR-030-jev-entailment-judge-backend]].

## Method

Two item sets, structural gold (a question's stated answer = positive, each of its
distractors = negative). **Not human-adjudicated** — every number is bounded by that
(see Caveats).

| Set | Source | Items | Live verdicts |
|---|---|---|---|
| `eval` | `data/eval/entailment_sample_150.json`, replayed with the seed-718 shuffle (2 negatives) | 450 | reused from `entailment_v3_2026-08-19.json` (zh, en) and `entailment_v3_ja_models_2026-08-19.json` (ja, gemini) |
| `prod` | 50 most-recent production questions per language, excluding the `eval` qids (`scripts/build_entailment_prod_sample.py`) | 600 | fresh run of the live judge, `scripts/measure_entailment_ab.py --arms live=` |

Live judge models at the time: zh `deepseek/deepseek-chat`, en and ja
`google/gemini-3.5-flash-lite`. jev: one `noul` question per item, native-language prompt.
Every jev call returned a usable `noul`. **Spend: $0.19** (live $0.150, jev $0.037, smoke
tests <$0.001) of the $1 cap.

Script: `scripts/calibrate_entailment_jev.py` (`run`, `report`). Data:
`data/eval/jev_entailment_calibration_2026-09-26/` — `jev_vs_live.json` (every item, both
verdicts) and `calibration_report.md` (all 83 disagreements with text).

## Score shape → cutoffs

jev's P(yes) is bimodal. Distractors sit almost entirely under 0.35 (zh/en 98th percentile
0.22–0.34; ja is heavier-tailed, 0.53). Stated answers are mostly above 0.7. The entailment
scores do **not** skew high — only the grammar rubric did — so 0.5 was not used, but the
correct cutoffs turned out low, not high.

- **Reject below 0.30.** False-rejects of real answers are flat across 0.30–0.40 in all three
  languages; 0.30 keeps the flag band narrowest. Above 0.40 ja false-rejects climb (5/100 at
  0.40, 9/100 at 0.50).
- **Accept at 0.60.** Lowest accept cutoff that takes zh false-accepts to zero. Raising it to
  0.70/0.80 only widens the flag band (ja 17 → 24 flags at 0.70).
- No per-language difference is supported by the data, so all three share `(0.30, 0.60)`.
  The values live in a per-language dict (`answer_entailment_jev.CUTOFFS`).

## Confusion matrices at (reject < 0.30, accept ≥ 0.60)

350 items per language: 100 answers, 250 distractors.

| Lang | Gold | jev A / F / R | live A / F / R |
|---|---|---|---|
| zh | answer | 97 / 3 / 0 | 100 / 0 / 0 |
| zh | distractor | 0 / 3 / 247 | **16** / 24 / 210 |
| en | answer | 94 / 4 / 2 | 95 / 1 / 4 |
| en | distractor | 1 / 5 / 244 | 3 / 1 / 246 |
| ja | answer | 89 / 7 / 4 | 90 / 3 / 7 |
| ja | distractor | 4 / 10 / 236 | **12** / 4 / 234 |

Live (rows) × jev (columns), all items:

| Lang | live accept → A/F/R | live flag → A/F/R | live reject → A/F/R | disagreements |
|---|---|---|---|---|
| zh | 97 / 5 / 14 | 0 / 1 / 23 | 0 / 0 / 210 | 42 |
| en | 93 / 3 / 2 | 0 / 1 / 1 | 2 / 5 / 243 | 13 |
| ja | 88 / 11 / 3 | 2 / 1 / 4 | 3 / 5 / 233 | 28 |

Both sets agree: zh 0 false-reject / 0 false-accept in each; en `eval` 0/0, `prod` 2/1;
ja `eval` 4/2, `prod` 0/2. Flag band (kept + queued for review): 1.7% zh, 2.6% en, 4.9% ja
of items.

## What the disagreements are

- **zh — the live judge is the one making errors.** All 14 items where live accepts a
  distractor and jev rejects it are real live errors, several contradicted by live's own
  reason. Passage: "公司每周检查数据"; live accepts the answer 每天 ("daily") with a reason
  stating the answer is weekly. Distractor 洗手 for "什么东西会让人生病？" was rated 5 with
  the reason "细菌会让人生病"; jev gave both 0.02.
- **ja "meaning of X in the passage" items** account for most of the ja `prod` flags and
  false-accepts (文中の「X」の意味…). Several distractors there are defensible synonyms
  (e.g. 「浮上している」→「表面に浮かび上がってきている」: jev 0.72, live 5). Those are
  **gold-label errors, not judge errors**, so the ja false-accept figure is an over-count.
- **Both judges reject some gold "answers"** — 減った (passage says the opposite), a
  "turn a blind eye" question whose phrase is not in the passage, 「コーヒーが牛乳や雑誌を
  販売している」. Correct catches of generator defects, charged to the judges by structural gold.
- **Real jev misses are few and one-directional.** en answer "Telling people what is in the
  data": jev 0.27 (reject), live 5. en distractor "It can do what you want": jev 0.62
  (accept), live reject. Elsewhere jev under-scores terse or inferential *correct* answers
  into the flag band (0.40–0.51) — safe, because flag keeps the question.

## Caveats

1. **Structural gold**, not human-adjudicated. It flatters jev on zh/ja wherever live's
   "false accepts" are actually valid distractors, and it charges both judges for
   generator defects. AUC-style numbers are lower bounds; the cutoffs are defensible, not
   proven optimal. A hand-labelled sample (TASK-834) is the fix.
2. The reasons quoted above are the **live** judge's; jev returns no text. On a jev reject
   the generator's regenerate feedback is a synthesised sentence with the probability, not a
   diagnosis.
3. `prod` is 50 questions/language from the most recent tests — recent-tests skew, and
   question type mix was not controlled.

## Related

[[evaluations/jev-judge-feasibility-2026-09-26]] ·
[[evaluations/entailment-likert-v3-rollout-2026-08-19]] ·
[[evaluations/entailment-judge-model-ab-2026-08-17]] ·
[[features/answer-entailment-judge.tech]] · [[tasklist/jev-entailment-judge.tasks]]
