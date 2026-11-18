---
title: "Free OpenRouter models as the Dual Translation single-call grader — Evaluation"
type: evaluation
status: complete
last_updated: 2026-11-18
open_questions:
  - "ANSWERED (2026-11-18): withhold medium-confidence errors for unvalidated models — shipped and measured live (§6)."
  - "ANSWERED (2026-11-18): no model fallback by default; a failed grade offers the learner a retry (§6)."
  - "OPEN: English understandability bands got worse with the filter (QWK .70 -> .45 on the same items). Accept, or keep medium errors for band scoring only?"
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

## 6. Shipped configuration, measured live (2026-11-18)

Built and pushed (not deployed): for models outside `VALIDATED_MODELS` only `high` errors are shown and
scored (`dropped.not_high_confidence`); their prompt adds `JOINED_SENTENCES_PARAGRAPH` (variant
`v2_guard2`); `DT_SINGLE_CALL_FALLBACK_MODEL` defaults to blank; the learner gets "Try again" when no model
graded the translation. Run with Particle, no fallback (prefix `fq_`, all 9 runs, 211 free calls).

9 calls hit OpenRouter's free per-minute limit (429 `free-models-per-min`, 20/min) because the runs are
back to back; those items fell to the refused paid flow. Rows marked "excl." drop those 9 items from both
sides.

| Setup | Gold P / R (TP/FP/FN) | Clean flagged | Heavy: rephrasings flagged · P / R | Moderate · P / R |
|---|---|---|---|---|
| Paid gpt-6-luna | .97 / .91 (73/2/7) | 0/30 | 2 · .94 / .85 | 0 · .97 / .80 |
| Particle, old setup | .95 / .88 (70/4/10) | 1/30 | 21 · .50 / .88 | 14 · .69 / .92 |
| **Particle, new setup** | .95 / .79 (63/3/17) | 0/30 | **0** · 1.0 / .82 | **0** · 1.0 / .67 |
| Particle, new setup, excl. | .95 / .81 (63/3/15) | 0/30 | 0 · 1.0 / .82 | 0 of 83 · 1.0 / .85 |
| Paid, same items excl. | .97 / .91 (71/2/7) | 0/30 | 2 · .94 / .85 | 0 of 83 · .97 / .82 |

Gold QWK accuracy / fidelity / understandability (excl.): en .82 / .76 / .45 (old .82 / .82 / .70; paid
1.0 / .83 / .69), zh .75 / .92 / .94 (old .75 / .84 / .74), ja .85 / .84 / .76 (old .85 / .89 / .79).
Overall-band QWK .74 (old .74, paid .81).

Joined-sentence spot checks (2 runs each, Particle, new prompt): correct joins in ja, zh and en raised no
flag; a joined sentence with a wrong verb (家にいきます) and a wrong te-form (広いで) were still flagged
(critical / major). The 2026-11-18 learner sentence went from "conjugation, major" (3/3) to "word_choice,
minor" in 2 of 4 runs and major in 2 (one still said the で left the sentence unfinished).

**Reading.** The filter removes every false flag on correct rephrasings in the stress set, as simulated,
at a recall cost (gold .88 -> .81). Bands improve for Chinese and drop for English understandability,
because medium errors that were real no longer lower the band.

## Related Pages

- [[evaluations/dt-decision-grading-2026-11-14]] — the paid sign-off and the stress set
- [[decisions/ADR-044-dt-single-call-generative-grader]]
- [[features/dual-translation.tech]]
