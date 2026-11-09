---
title: Test Quality Checks — Calibration (2026-11-09)
type: evaluation
status: complete
last_updated: 2026-11-09
---

# Test Quality Checks — Calibration (2026-11-09)

TASK-920 for [[features/test-quality-checks]]. Question: on the live library, how often is each
deterministic check right, and which may reject questions during generation?

## Method
1. Full audit of 304 active tests (zh 125, en 121, ja 58; 1,420 questions) with every check
   forced to `flag`: `scripts/audit_test_quality.py` — 545 findings on the first pass.
2. Sample ≤ 20 findings per check × language (seed 920): 242 findings
   (`data/test_quality/calibration_2026-11-09/pack_*.json`).
3. Three fresh-context Claude reviewers, one per language, labelled each finding *real* or
   *false alarm* against a written definition per check (`labels_*.json`).
4. Thresholds retuned from the false-alarm patterns; `scripts/score_quality_calibration.py`
   re-runs the current rules on every labelled finding and reports precision now and real hits
   lost (`scores.md`).
5. Rule: `reject` needs ≥ 10 labelled findings and precision ≥ 0.9; otherwise `flag`.

## Results (all languages)

| language | check | labelled | real | precision (as sampled) | still fires | precision now | real lost |
|---|---|---|---|---|---|---|---|
| all | `absolute_distractors` | 27 | 25 | 0.93 | 27 | 0.93 | 0 |
| all | `answer_copies_passage` | 17 | 14 | 0.82 | 13 | 1.00 | 1 |
| all | `answer_length_outlier` | 60 | 30 | 0.50 | 24 | 0.88 | 9 |
| all | `choice_label_prefix` | 4 | 4 | 1.00 | 4 | 1.00 | 0 |
| all | `duplicate_answer` | 25 | 24 | 0.96 | 25 | 0.96 | 0 |
| all | `duplicate_stem` | 3 | 3 | 1.00 | 3 | 1.00 | 0 |
| all | `duplicate_vocab_target` | 9 | 5 | 0.56 | 3 | 1.00 | 2 |
| all | `foreign_script` | 3 | 2 | 0.67 | 2 | 1.00 | 0 |
| all | `latin_in_cjk` | 14 | 14 | 1.00 | 14 | 1.00 | 0 |
| all | `missing_title` | 1 | 1 | 1.00 | 1 | 1.00 | 0 |
| all | `script_above_level` | 12 | 12 | 1.00 | 12 | 1.00 | 0 |
| all | `too_few_questions` | 7 | 3 | 0.43 | 1 | 1.00 | 2 |
| all | `type_mix` | 60 | 42 | 0.70 | 60 | 0.70 | 0 |

Per-language rows are in `scores.md`. Notable: `type_mix` precision is ja 0.90, en 0.85,
zh 0.35 — Chinese author's-purpose pairs more often split attitude from technique.

## What changed
| check | change | why |
|---|---|---|
| `answer_length_outlier` | characters in every language; answer ≥ 1.4 × the longest distractor and ≥ 4 chars longer; the "1.3 × mean" branch removed | ja 16/20 false alarms came from the mean branch; en word counts flagged answers one word longer |
| `answer_copies_passage` | CJK minimum 15 characters (was 10); skipped at T1–T2 | 10-character runs were ordinary phrases; at T1–T2 recognising the passage's words is the skill |
| `duplicate_vocab_target` | target = shortest quoted span, not the first | zh stems quote the sentence, then the word |
| `type_mix` | "no detail question" only up to T4 | zh false alarms at T5–T6 were deliberate higher-order mixes |
| `too_few_questions` | T3+ only | 3 questions on a short T2 passage is fine |
| `foreign_script` | 昇 allowlisted for zh | 毕昇 |

Tried and reverted: firing on two author's-purpose questions only when their answers overlap.
Bigram overlap was 0.0–0.6 on both real and false pairs, and it dropped 28 real hits.

## Decision — `CHECK_MODES`
- **reject:** `absolute_distractors` (0.93, n = 27), `answer_copies_passage` (1.00 of 13 still firing),
  `duplicate_answer` (0.96, n = 25), `latin_in_cjk` (1.00, n = 14), `script_above_level` (1.00, n = 12).
- **flag:** `answer_length_outlier` (0.88), `type_mix` (0.70), and the checks with < 10 labels
  (`choice_label_prefix`, `duplicate_stem`, `duplicate_vocab_target`, `foreign_script`,
  `too_few_questions`, `missing_title`), all of which were 100 % precise on their few labels.

## Caveats
- The copy and length thresholds were tuned on the same labels they are scored on, so "precision
  now" is in-sample. TASK-924 measures behaviour on fresh generations.
- The labels come from model reviewers, not people.
- **Coverage is low.** Against the [[evaluations/ja-test-review-2026-11-09]] gold set (241 questions
  after excluding the fixed and deleted ones), only 19 of the 78 flawed questions get a
  question-level finding, and 9 of 163 "ok" questions do. The earlier estimate that ~45 of the 79
  minor problems were in reach was optimistic: most of the review's minor issues (unsupported keys,
  partly defensible distractors, subtle duplicates) need a reader. This is the case for the blind
  answerer and the authoring/review skill.

## After calibration
Re-audit with calibrated rules: 325 findings (zh 133, en 121, ja 71); 133 tests have at least one
finding classed `regenerate_question` in `data/test_quality/remediation_2026-11-09.csv`.
