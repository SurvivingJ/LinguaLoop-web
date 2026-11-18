---
title: "Free OpenRouter models as the Dual Translation single-call grader — Evaluation"
type: evaluation
status: complete
last_updated: 2026-11-18
open_questions:
  - "OPEN: Withhold medium-confidence errors for unvalidated (free) models? Simulated only on error lists (§4); scores were not recomputed, so a real run is needed before shipping."
  - "OPEN: What should the fallback model be? Nemotron false-flags rephrasings heavily; Baidu Ernie fails 38% of calls at the 1,400-token budget (a larger budget for it is untested)."
  - "OPEN: Fund the key and return to the validated pair (openai/gpt-6-luna, deepseek/deepseek-v4.1-flash, ADR-044)?"
  - "OPEN: Prompt change for joined sentences (て/で connective) — the 2026-11-18 learner case was a high-confidence flag that the confidence filter would not remove."
---

# Free OpenRouter models as the DT single-call grader

**Date:** 2026-11-18 · **Spend:** $0 (free models; 805 calls of the key's 1,000/day free quota) ·
**No DB writes; no production setting changed.**
**Runs:** `data/eval/dt_decision_2026-11-14/prod_check/v2/` prefixes `fp_` (Particle), `fn_` (Nemotron),
`fe_` (Baidu Ernie, default reasoning), `fl_` (Baidu Ernie, low reasoning effort); baseline `e_` (paid
`openai/gpt-6-luna`, the prompt-v2 sign-off in [[evaluations/dt-decision-grading-2026-11-14]] §9.1).
Scored with that directory's `score.py`.

## 1. Why

Since 2026-11-16 the single-call grader runs on free models (`config.py`: primary
`particle-ai/particle-1:free`, fallback `nvidia/nemotron-3.5-super-vl:free`) because the OpenRouter key hit
its $10 limit. They were never measured. On 2026-11-18 a learner's correct Japanese rephrasing
(この服は私の一番好きで、熊の絵が好きです for この服はわたしのお気に入りです。くまの絵がすきです。) got a
high-confidence "conjugation, major" error on 一番好きで (the で is the connective form of です; nothing
is mis-conjugated), identically in 3 of 3 re-runs. The developer asked whether to use the Baidu model for
free grading.

## 2. Method

`scripts/run_dt_grading_eval.py --single-call --fixture-set v6` with the v6 taxonomy and rubric seed files,
one model per run (`DT_SINGLE_CALL_FALLBACK_MODEL` blank, so a failed call is visible as a fall-through to the
configured flow, whose paid models the capped key refuses). Same items as the paid sign-off: the v6 gold set (31
en / 30 zh / 30 ja; the scorer pools the 90 that score.py matches) and the Track E stress set's heavy (53) and moderate (60) levels,
which measure false flags on correct rephrased sentences. One run each.

## 3. Results

Gold = pooled precision / recall on error spans (TP / FP / FN), clean items flagged. Stress = correct
rephrased sentences flagged (of 152 heavy, 93 moderate), precision / recall.

| Model | Gold P / R | Gold clean flagged | Heavy: rephrasings flagged · P / R | Moderate: rephrasings flagged · P / R | Calls failed | p50 latency |
|---|---|---|---|---|---|---|
| gpt-6-luna (paid, sign-off) | .97 / .91 (73/2/7) | 0/30 | 2 · .94 / .85 | 0 · .97 / .80 | 0/287 | 1.7 s |
| **Particle** (current primary) | .95 / .88 (70/4/10) | 1/30 | **21** · .50 / .88 | **14** · .69 / .92 | 0/200 | 1.5 s |
| **Nemotron** (current fallback) | .94 / .84 (67/4/13) | 1/30 | **46** (6 major) · .21 / .78 | **31** · .31 / .78 | 0/200 | 1.4 s |
| Baidu Ernie, default effort | 1.0 / .46 (37/0/43) | 0/30 | — | — | **73/200** | 3.5 s |
| Baidu Ernie, low effort | 1.0 / .50 (40/0/40) | 0/30 | 3 · .82 / .35 | 3 · .88 / .47 | **76/200** | 6.3 s |

- **Baidu Ernie (`baidu/ernie-5.5-flash-preview:free`)** cannot disable reasoning (400 "Reasoning is
  mandatory for this endpoint"). It spends ~660 reasoning tokens (p50; p90 ~1,100) and, on 38% of calls,
  the whole 1,400-token budget, returning no answer (`finish_reason: length`). `reasoning.effort: low` is
  accepted and ignored. Its low recall is partly those failures (each falls to the refused paid flow and
  contributes no errors); on answered calls it is cautious (few false flags) but still misses errors.
- **Particle** finds as many errors as the paid model on gold but false-flags rephrasings (mostly as
  `minor`).
- **Nemotron** false-flags rephrasings 2–3× more than Particle, including major ones.

## 4. Confidence filter (simulated)

The grader already withholds `low`-confidence errors. On the stress set Particle's false flags are almost
all `medium` (heavy 34 of 35, moderate 19 of 20) and its true positives almost all `high` (precision of
`high` flags .97–.98, of `medium` .08–.17). Keeping only `high` errors in the saved runs:

| Model | Gold P / R | Gold clean flagged | Heavy: rephrasings flagged · P / R | Moderate: rephrasings flagged · P / R |
|---|---|---|---|---|
| gpt-6-luna, high only | .98 / .79 | 0/30 | 1 · .97 / .82 | 0 · 1.0 / .76 |
| **Particle, high only** | .95 / .79 (63/3/17) | 0/30 | **0** · 1.0 / .82 | **0** · 1.0 / .86 |
| Nemotron, high only | .96 / .82 | 1/30 | 22 (6 major) · .38 / .72 | 17 · .56 / .71 |

Caveat: the simulation removes errors from the stored lists only. Bands and the overall band are computed
in Python from the error list, and those were **not** recomputed, so only the span metrics above are
measured. The learner's 2026-11-18 flag was `high`, so this filter would not have removed it.

## 5. Conclusion

- Do not switch to Baidu Ernie at the current budget: too many empty answers, slower, lower recall.
- Particle plus a "high confidence only" rule for unvalidated models removes every false flag on correct
  rephrasings in the stress set at a recall cost on gold (.88 → .79).
- Nemotron should not stay as the fallback.
- The validated paid pair remains the best grader measured (gold .97 / .91, 0–2 rephrasing flags).

## Related Pages

- [[evaluations/dt-decision-grading-2026-11-14]] — the paid sign-off and the stress set
- [[decisions/ADR-044-dt-single-call-generative-grader]]
- [[features/dual-translation.tech]]
