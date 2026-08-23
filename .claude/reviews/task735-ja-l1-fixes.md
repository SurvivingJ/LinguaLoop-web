# TASK-735 — ja L1: fabrication, judge strictness, and the P1 write-off

**Date:** 2026-08-22
**Baseline:** canary run `ja-20260822-232552` (senses 34997 昔, 34999 一, 35001 機械)
**Status:** two of three defects fixed and measured; the third is a verdict, not a change.

---

## Summary

| # | Defect as briefed | Verdict | Action |
|---|---|---|---|
| 1 | ja L1 generator fabricates words | **Confirmed**, and the mechanism was orthographic | `vocab_prompt2_exercises` [ja] v1 → v4. Fabrication now 0/7 candidates. |
| 2 | P1 judge threshold too strict for ja | **Not a judge defect.** The threshold is right. | No change. The 33% is a sense-pool problem — see below. |
| 3 | L1 judge over-strict on true minimal pairs | **Confirmed** | `ladder_l1_distractor_judge` [ja] v2 → v3. 5 correct flips, 0 false keeps. |

Plus one structural fix the measurement forced: L1 now over-generates, because
`_render_phonetic` drops the whole variant below 3 surviving distractors, so
exactly-3 distractors demanded a 100% hit rate from the model.

---

## Baseline: how 17 rejects became 0 exercises

Six `judge_ladder_l1_distractor` calls on 2026-08-22, 18 distractors, **17 rejected**.
[exercise_renderer.py:504](../../services/vocabulary_ladder/exercise_renderer.py#L504)
returns `None` for the entire variant when `len(kept) < 3`, so the ja ladder
produced zero L1 exercises rather than weakened ones. The all-or-nothing gate is
what turns a distractor-quality problem into a total loss.

---

## Defect 1 — the generator fabricated words

Sense 34997 (昔/むかし) variant B emitted `向こうし` and `無蚊地`. Neither is a
word; the model's own explanation claimed 無蚊地 was "an existing word (a place
name etc.)". Variant A, which happened to answer in kana, invented nothing.

**The mechanism is orthographic, not lexical.** The incumbent prompt said
nothing about how to *write* an option. Having committed to a kanji surface for
variant B, the model composed kanji until the reading fitted. The one
anti-fabrication clause it did carry — `ディストラクターはすべて実在する語で…` —
was a passive aside among eight bullets, and it did not hold.

Fixed across three prompt versions, each measured:

- **v2** — attestation gate (dictionary headword; state reading and meaning
  before writing the explanation; no coined compounds, naming the two observed
  fabrications), an orthography rule (never manufacture a spelling to match the
  target's script), and a one-mora contrast rule.
  → *Measured: 0 fabrications, but only 2 of 3 distractors survived per variant.*
- **v3** — over-generate to 6 options.
  → *Measured: 機械 renders; 昔 regressed to inventing `無蚊`, `むかけ`, `むかっ` —
  demanding 5 distractors for a word with few neighbours forces invention.*
- **v4** — an explicit mora-substitution search procedure, and permission to
  return 3 distractors when only 3 real words exist ("padding the count by
  coining a word is the single worst failure").
  → *Measured: 0 fabrications across both senses.*

Final generated sets — every one a real word:

```
昔    向き  迎え  百足  可笑し
機械  理解  議会  期待
```

## Defect 3 — the judge's closed keep-list

v2 listed exactly four admissible contrast types (長短母音, 清濁, 促音撥音,
高低アクセント). An ordinary one-mora minimal pair is not among them, so
むかし/むかえ — as clean a minimal pair as Japanese offers — was killed with
`最小対立の条件を満たさず`. The judge was correct by its own rules; the rules were
wrong. The **en** row (id 173) never had this problem: its taxonomy is open
("a homophone / near-homophone, a minimal pair differing by one phoneme, or a
same-stress rhyme").

v2 was also self-contradictory on pitch accent — it listed accent-only pairs as
`keep` *and* as `reject`. The model resolved that by killing 機会/機械. The
generator meanwhile *preferred* accent-only pairs. **The judge is the one that
was right**: L1 audio is a single TTS rendering, so an accent-only contrast is
undecidable for the learner. Both rows now forbid it.

**Controlled A/B**, identical inputs, same model, temp 0 (`--judge`):

| sense | distractor | v2 | v3 | |
|---|---|---|---|---|
| 34997 A | むかえ | reject | **keep** | flipped — correct |
| 34997 A | むこう / むし | reject | reject | correct both |
| 34997 B | 向こうし / 無蚊地 | reject | reject | fabrications, correct |
| 35001 A | 機会 | reject | reject | accent-only, correct |
| 35001 A | 気体 / 帰還 | reject | **keep** | flipped — correct |
| 35001 B | 気体 / 機関 | reject | **keep** | flipped — correct |
| 35001 B | 気配 | reject | reject | two morae, correct |

**v2 kept 0/12. v3 kept 5/12. Zero false keeps.** Every reject that should have
stood, stood.

Note the A/B also proves the ordering in the brief was right: with the judge
fixed but the generator untouched, **0 of 4 variants still render**. The
generator was the binding constraint.

## The structural fix over-generation was needed for

The generator emitted exactly 3 distractors and the renderer needed all 3 —
a 100% hit rate per item. That is not a rate an LLM holds. L1 now returns 4–6
options; the renderer still keeps `kept[:3]`, so the learner sees 4 either way.

This required [validators.py](../../services/vocabulary_ladder/validators.py)
to stop pinning every option level at exactly 4 — the renderer reads only
`is_valid=True` assets, so an over-generated L1 would have invalidated L3, L5
and L6 along with it. `OPTION_COUNTS = {1: (4, 8)}` relaxes **L1 only**; L3/L5/L8
stay pinned, because their distractors are *not* individually judged and a fifth
option there would reach the learner as a fifth option. The band is wider than
the prompt asks (4–6) so a model that overshoots by one does not invalidate the
whole P2 asset. Regression test:
[tests/test_l1_option_overgeneration.py](../../tests/test_l1_option_overgeneration.py).

## Defect 2 — the P1 threshold is right; the sense pool is not

`P1_MIN_ACCEPTABLE_SENTENCES = 6` did not misfire. Reading the actual verdicts:

- **34999 (一/いち) — blocked, correctly.** All 10 sentences rated 2, with
  reasons `対象語が全単語で現れない`, `対象語：接頭辞として使用`,
  `義項：別義、文字断片`. 一 is a bound numeral: it occurs as 一つ, 一番, 一人,
  一日 — essentially never as a free-standing word. The judge's whole-word check
  is doing exactly its job.
- **35001 (機械) — not blocked.** Two sentences rated 2, repaired, re-judged to
  3 and 5. The `reject` in `llm_calls` is the worst-verdict log line, not a block.

**Loosening the threshold would admit sentences where the target is a character
fragment, poisoning every level L3–L9 that inherits them.** Do not do it.

The real defect is upstream: bound morphemes are in the ja sense pool, and
`phase_select` ranks by test frequency — which puts them at the *top* of the
selection. In the first 20 of the canary pool:

| sense | lemma | why it will fail P1 |
|---|---|---|
| 34999 | 一 | bound numeral (confirmed blocked) |
| 35009 | 様 | its own definition says `接尾語`, "used like お客様" |
| 35035 | 度 | its own definition cites 一度/二度/強度/速度 |

~15% of the pool, not 33% — the canary's 1-in-3 is small-sample noise around
that floor. At ~$0.02 and ~7 minutes per sense, 150 senses implies roughly
20 wasted senses, ~$0.45 and ~2.5 hours.

`part_of_speech` cannot gate this — 一, 度 and 人 are all `名詞`. The tractable
signal is the definition text (`接尾語` / `接頭語` / 助数詞 markers). **Not
implemented here** — it is a sense-pool change, outside the three briefed
defects, and worth its own decision.

*(Incidental: `dim_vocabulary` has 2 ja rows whose `part_of_speech` is the
Simplified Chinese `名词` rather than `名詞` — 昔 and 機械. Harmless today,
since nothing gates on it.)*

---

## Where it stands

| metric | before | after |
|---|---|---|
| fabricated distractors | 2 of 6 generated (33%) | **0 of 7** |
| judge keeps on the recorded sets | 0/12 | 5/12, no false keeps |
| variants that would render | 0/4 | 1/2 |

Not yet the ~100% the 300-exercise target needs. Both remaining rejects are
generator-side and both are the *last* candidates emitted — the model finds 2–3
good ones and then pads (`向き` is genuinely 2 morae from むかし; `可笑し` is a
classical form). The judge called both correctly.

**Recommended next step: re-measure before tuning further.** n=2 senses over
three prompt rounds is well into over-fitting territory —
`python scripts/smoke_task735_ja_l1.py --gen` after widening `SENSES` to ~10
gives an honest hit rate for roughly $0.20. If padding is confirmed as the
dominant residual, the fix is in the prompt's ordering (require the search
procedure to terminate before the count is considered), not in the judge.

## Live changes

| what | change | rollback |
|---|---|---|
| `prompt_templates` id 184 | `vocab_prompt2_exercises` [ja] v1 → v4 | flip `is_active` to v1 |
| `prompt_templates` id 370 | `ladder_l1_distractor_judge` [ja] v2 → v3 | flip `is_active` to v2 |
| `services/vocabulary_ladder/validators.py` | `OPTION_COUNTS`, L1 → 4–8 | revert |

Full suite: **1965 passed, 2 skipped**.

Applier: `scripts/apply_task735_ja_l1_fixes.py` (`--dry-run` / `--verify`).
Harness: `scripts/smoke_task735_ja_l1.py` (`--judge` / `--gen`).
Drafts: `data/eval/task735/`.
