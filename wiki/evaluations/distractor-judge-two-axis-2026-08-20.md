---
title: "Distractor judge v7 — two axes, and what the split actually shows"
type: evaluation
status: complete
last_updated: 2026-08-20
tasks:
  - TASK-719
  - TASK-720
open_questions:
  - "Is a 22-47% question-level review rate worth paying for? It is 10-25x today's and the gold set cannot arbitrate it."
  - "Should CONFUSABILITY_INERT_MAX be 0 rather than 1? It contributes ~25% of the queue volume and is the one cut point v4 had no opinion about."
---

# Distractor judge v7 — two axes, and what the split actually shows

Executes [[tasklist/distractor-judge-calibration]] TASK-719 (split the rating onto two
axes) and TASK-720 (redefine the review band as judge uncertainty, and record which axis
triggered it).

**Headline: the split works, and it costs more than expected.** Both axes fire in all three
languages, the review band goes from ~0 to a real signal everywhere, and the queue is now
attributable to an axis. But the review rate lands at **22-47% of questions** against
today's 0-3%, and the also-correct failure the whole exercise was meant to expose fires
**once in 537 distractors**. The v7 rows are therefore staged `is_active = false`, the same
disposition TASK-717's v5 and TASK-721 reached.

---

## What was built

| Layer | Change |
|---|---|
| `services/test_generation/schemas.py` | `fit` / `confusability` fields on `DistractorPlausibilityVerdict`; `fit_to_verdict`, `confusability_to_verdict`, `axes_to_verdict`; cut points as named constants |
| `services/exercise_generation/judges/base.py` | `JudgeOutcome.axes` and `.flag_axes` — optional, so the eight single-axis judges are untouched |
| `services/exercise_generation/judges/distractor_plausibility.py` | verdict comes from the pair; per-axis missing-rating handling |
| `services/test_generation/orchestrator.py` | `_flag_reasons` — queue rows read `distractor_plausibility:confusability` |
| `migrations/distractor_plausibility_prompt_v7_two_axis.sql` | v7 rows, zh/en/ja, **inactive** |
| `scripts/apply_distractor_judge_v7.py` | writes and verifies them; `--emit-sql` generates the migration from the same source |
| `tests/test_distractor_two_axis.py` | 26 tests |

### The bands

```
fit            5 clearly the passage's subject · 4 plausibly within it
               3 NOT CONFIDENT → review
               2 clearly a different subject   · 1 not a coherent option

confusability  5 also correct / indistinguishable from the answer  → reject
               4 strongly tempting but definitely wrong  (the target)
               3 NOT CONFIDENT → review
               2 mildly tempting               · 1 inert → review
```

`confusability` is not monotone in quality — both ends are defects and 4 is the goal. That
is the property a single ordinal cannot carry, and the reason the arithmetic moved into
Python.

### The compatibility property, stated because it is load-bearing

`fit`'s bands are **identical** to the v4 single-axis bands. A v4/v6 row returns one rating,
it lands in `fit`, `confusability` is `None`, and a `None` axis contributes 'accept'. So the
deployed code returns byte-identical verdicts against the rows live today, and the code
could ship without a coordinated prompt cutover. This is the opposite of entailment v3
(TASK-723), where the two scales inverted at `1` and 77% of historical responses would have
flipped meaning. `test_fit_reproduces_the_v4_scale_exactly` asserts it rather than trusting
the prose. The live-arm columns below are the empirical check: they are the same numbers the
single-axis code produced.

---

## Measurement

Same frozen sample as TASK-721 (`data/eval/task721_before.json`): 179 questions, 537
distractors, zh 59 / en 60 / ja 60, stratified over the six question types. Same judge model
in every cell (`google/gemini-3.5-flash-lite`) — v7 is a prompt change and is measured as
one. Slot `{5}` renders its fallback, as production does. 358 calls, 1.4 min, **$0.2738**.

```
python scripts/measure_judge_flag_rate.py --sample data/eval/task721_before.json \
    --arms "live=live:,v7=7:" --out data/eval/distractor_two_axis_2026-08-20.json
```

`live` resolves per language (zh v6, en v4, ja v4). v7 is uniform, which is why it was
numbered 7 in all three despite en and ja having no v6.

### 1. Verdicts, question level

| lang | live rejects | v7 rejects | live flagged | v7 flagged |
|---|---|---|---|---|
| zh | 2 / 59 | **7 / 59** | 1 / 59 | **28 / 59** |
| en | 1 / 60 | **3 / 60** | 2 / 60 | **13 / 60** |
| ja | 2 / 60 | **1 / 60** | 0 / 60 | **17 / 60** |

Rejects move a little and not in one direction (zh up, ja down); on n=60 per language none of
that is separable from noise. The flag column is the real change, and it is an order of
magnitude.

### 2. The fit axis loses its middle band — and most of band 4

| arm | lang | 1 | 2 | 3 | 4 | 5 | unrated |
|---|---|---|---|---|---|---|---|
| live | zh | 0 | 2 | 1 | 47 | 127 | 0 |
| live | en | 0 | 1 | 2 | 33 | 144 | 0 |
| live | ja | 0 | 2 | 0 | 65 | 113 | 0 |
| v7 | zh | 0 | 7 | **0** | 2 | 168 | 0 |
| v7 | en | 0 | 4 | **0** | 10 | 163 | 3 |
| v7 | ja | 0 | 1 | **0** | 2 | 177 | 0 |

Not the direction anyone predicted. Splitting the axes made the model **more** decisive about
subject membership, not less: band 4 collapses (47→2, 33→10, 65→2) and band 3 stops firing
entirely. Read together with §3 this is coherent rather than alarming — under v4 the single
integer had to absorb hesitation about *both* questions, and once confusability has its own
column, "is this the right subject?" turns out to be a question this model finds easy. It is
also a warning: **the fit axis alone is now a near-binary signal**, so anyone tempted to
retire confusability and keep fit would be keeping the half that carries almost no
information.

### 3. The confusability axis carries the whole middle

| arm | lang | 1 | 2 | 3 | 4 | 5 | unrated |
|---|---|---|---|---|---|---|---|
| v7 | zh | 14 | 79 | 23 | 60 | **1** | 0 |
| v7 | en | 8 | 77 | 9 | 83 | 0 | 3 |
| v7 | ja | 4 | 58 | 14 | 104 | 0 | 0 |

All five bands in zh; four of five in en and ja. Under `live` this table is entirely
`unrated`, which is the correct reading — that prompt never asked.

**Band 5 (also correct) fired once in 537 distractors.** That is the failure TASK-719's
acceptance criterion named as having fired *zero* times on the single-axis scale, so the
criterion is met: it is detectable, and it is detected on the axis built for it. But be
honest about the size. TASK-718 saw the old band 1 fire 3 times in 1,800 ratings (0.17%);
this is 1 in 537 (0.19%). **The two rates are the same.** The revised TASK-719 status note
guessed that band 1's target failure "may simply be rare rather than undetectable", and that
is what the data says. The axis split did not uncover a hidden reservoir of also-correct
distractors — it made a rare event *legible* and gave it somewhere unambiguous to live.

### 4. Review load by axis — TASK-720's sizing

Distractor level, `flag` verdicts only:

| arm | lang | items | flagged | via fit | via confusability | flag % |
|---|---|---|---|---|---|---|
| live | zh | 177 | 1 | 1 | — | 0.6% |
| live | en | 180 | 2 | 2 | — | 1.1% |
| live | ja | 180 | 0 | 0 | — | 0.0% |
| v7 | zh | 177 | 31 | **0** | **31** | 17.5% |
| v7 | en | 180 | 13 | **0** | **13** | 7.2% |
| v7 | ja | 180 | 17 | **0** | **17** | 9.4% |

Every single v7 flag is a confusability flag. Recording the axis was TASK-720's deliverable
and it earned its keep immediately: the queue is not "the judge was unsure", it is "the judge
could not tell how tempting this option would be", every time, in all three languages. That
is a specific, answerable question to hand a reviewer.

Decomposed by cause:

| lang | unsure (band 3) | inert (band ≤1) | total |
|---|---|---|---|
| zh | 23 | 8 | 31 |
| en | 9 | 4 | 13 |
| ja | 14 | 3 | 17 |

~75% is genuine uncertainty, ~25% is the new inert rule. `CONFUSABILITY_INERT_MAX` is a named
constant precisely so that quarter can be dropped (set it to 0) without touching a prompt in
three languages.

**Question-level queue volume, which is the unit a reviewer works in:**

| lang | live | v7 |
|---|---|---|
| zh | 1 / 59 (1.7%) | **28 / 59 (47%)** |
| en | 2 / 60 (3.3%) | **13 / 60 (22%)** |
| ja | 0 / 60 (0.0%) | **17 / 60 (28%)** |

This is the number that decides the task. Roughly one question in three would arrive in
`generation_review_queue`. TASK-720's criterion was "queue volume is sized and recorded
before rollout, so review time can be budgeted" — it is sized, and the budget is not small.

---

## Why the rows are staged

1. **Nothing here is gold-validated.** TASK-726's adjudicated set does not exist. TASK-718
   measured two judge models whose reject sets were disjoint, so no reject signal in this
   workstream has ground truth behind it. A 47% zh review rate could be an honest judge
   admitting it cannot tell, or a prompt that made a confident model timid. The measurement
   above cannot distinguish those, and no measurement without labels can.
2. **The house rule.** TASK-717's v5 and TASK-721's generator spec were both authored,
   measured and left staged. Two for two; this is three.
3. **Nothing forces the decision.** The code is live-safe against the current rows (see the
   compatibility property above), so staging costs nothing and buys the gold set time.

**To activate**, after the gold set exists:

```sql
UPDATE prompt_templates SET is_active = (version = 7), updated_at = now()
 WHERE task_name = 'test_distractor_plausibility' AND language_id IN (1, 2, 3);
```

There is no code deploy to coordinate and no process restart to sequence — `_cfg_cache` is
process-lifetime, so a running process would need a restart to see the flip, but the verdict
semantics are identical either side of it.

---

## Loose ends

* **3 unrated distractors in en v7** (one question). The model returned a well-formed reply
  for the other two and nothing for the third; `accept_item` handled it, as designed. 3/537
  is below the noise floor of anything measured here but worth watching if v7 goes live.
* **The ja prompt needed one hand repair.** `qwen3.8-max` wrote the output-format section in
  fluent Japanese and rendered `JSON` as ジェイソンオブジェクト — a katakana transliteration.
  `rewrite_prompt_native.py`'s `required_literals` check caught it on all three attempts and
  refused to certify the row. Repaired by substituting the literal token back
  (`JSON オブジェクト`); nothing else in the body was touched. The contract check is the only
  reason this did not ship: `response_format='json_object'` needs the token, and the failure
  would have been a silently degraded judge, not an error.
* **`classify()` and `THRESHOLD_*` still survive** with one caller (`judges/cloze.py`).
  TASK-723's last open criterion — "one verdict mapper, not two" — was blocked on this task
  settling the axis split. It is settled; `axes_to_verdict` is the template cloze converts
  onto. That conversion is not in TASK-719/720's scope and remains owed.

## Related pages

- [[tasklist/distractor-judge-calibration]] — TASK-719, TASK-720, TASK-726
- [[evaluations/distractor-judge-language-divergence-2026-08-16]] — the §3 analysis that
  identified the two-axis conflation, and TASK-718's model A/B
- [[evaluations/distractor-gold-frame-2026-08-19]] — the frame this is waiting on
- [[evaluations/entailment-likert-v3-rollout-2026-08-19]] — the single-axis judge that did
  cut over, and why it was the easy case
