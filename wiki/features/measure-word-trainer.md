---
title: Measure Word Trainer
type: feature
status: complete
tech_page: ./measure-word-trainer.tech.md
last_updated: 2026-05-17
open_questions: []
---

# Measure Word Trainer

## Purpose

Chinese requires a *classifier* (量词) between a numeral or demonstrative and a noun:
一**只**猫 (one cat), 一**条**狗 (one dog), 一**辆**车 (one car). The right classifier
depends on the noun's shape, animacy, social register, or sometimes pure idiom. Picking
the wrong one is one of the most common grammatical errors for L2 Chinese learners and was
already called out as the L6/L7 error category `量词使用错误` in the cloze distractor prompts
([[features/exercise-generation-prompts]]).

This trainer promotes that practice surface to its own first-class drill, served as an
*infinite* session (Vocab Dojo style) rather than per-test.

## User Story

A learner navigates to `/classifier-drill`. The page shows `一 ___ 猫` with the
pinyin and gloss, and four buttons holding the correct classifier and three plausible
distractors from the same semantic group (other animal classifiers, in this case). Press
**1–4** or click to answer. Wrong → a feedback modal shows the canonical `一只猫`, the
semantic-group reason ("animals are counted with 只 — small/medium"), and the learner's
answer. A round is 20 items; finish a round to see accuracy, time, and ELO change. Hit
"Next round" to keep going indefinitely.

A header toggle switches between **Choose** (MC mode) and **Type** (text input mode).
Type mode accepts any of the multiple acceptable classifiers for that noun — `狗` accepts
both `只` and `条`.

## How It Works

1. A session RPC samples up to 20 noun-classifier pairs from a curated dictionary,
   weighting by frequency and acceptable-classifier breadth.
2. For each picked noun the RPC returns: the noun's lemma, pinyin and gloss, *all*
   acceptable classifier IDs (CC-CEDICT-style multi-valid), and three distractor classifier
   IDs drawn from the same semantic group with the noun's acceptable answers excluded. If
   the group has fewer than three alternatives, the topup pulls from the general (`个`)
   fallback group.
3. The learner answers each item; the client tallies correct count and submits the
   batch result at end-of-round to `process_classifier_drill_submission`, which writes a
   `test_attempts` row against a hidden sentinel test and updates the user's
   `classifier_drill` ELO with the same K=32 formula used by the pinyin and pitch-accent
   trainers.

## Dictionary Source

The seed dictionary is hand-curated and ships embedded in
`scripts/build_classifier_dictionary.py`. 40 classifiers across 12 semantic groups,
269 noun-classifier pairs (~ 207 distinct nouns), covering HSK 1–4 vocabulary and high-
frequency content from existing Chinese tests. Re-running the build script wipes and
reinserts the dictionary, so changes to the script are the source of truth. No LLM is
used at any point in the pipeline.

A future expansion path documented in the script: parse `CL:X[pin]` annotations from
CC-CEDICT's `cedict_ts.u8` to add long-tail nouns; the table schema and pipeline are
designed for this and the `source` column distinguishes `'curated'` from `'cedict'`.

## Distractor Strategy

Each classifier belongs to one of 12 distractor groups, e.g. *animals* (只, 头, 匹, 群),
*long_thin* (条, 根, 支, 把), *vehicles* (辆, 架, 艘, 列), *containers* (杯, 瓶, 碗, 盒, 包, 袋).
Distractors are drawn from the correct answer's own group so the wrong choices are always
plausible — the learner cannot reject 头 just because it looks weird; they have to know
that 牛 takes 头, not 只.

## Constraints & Edge Cases

- **Multi-acceptable nouns.** 狗 accepts both 只 and 条; 朋友 accepts both 个 and 位. The
  RPC returns all acceptable IDs and the client accepts any of them in Type mode and
  highlights all of them in feedback after a miss.
- **Small distractor groups.** A few groups have only 3 classifiers (e.g. *events*: 场, 次,
  顿). When the noun's acceptable answers include 个 (very common) the topup from the
  *general* group is blocked and the item may render with only 2 distractors. Acceptable
  for v1; tracked as a refinement.
- **Anti-repetition between rounds is not implemented.** A user playing back-to-back
  rounds can see the same noun twice — Phase 2 would add a `user_classifier_history`
  log.
- **Repeats earn no ELO.** Same first-attempt-only rule as pinyin/pitch-accent
  ([[algorithms/elo-ranking.tech]]).

## Business Rules

- Chinese only (`language_id = 1`) in v1. Japanese counters (助数詞) require their own
  pipeline because of morphophonological alternation and are out of scope.
- Sentinel test row `slug = '__classifier_drill_zh'` is `is_active = false` so it never
  appears in test listings or recommendations. It exists solely to anchor `test_attempts`
  and `test_skill_ratings` rows.
- The route handler rejects any `language_id` other than 1.

## Interaction with the Cloze Pipeline

Cloze L6/L7 prompts continue to surface `量词错误` distractors as one of four
grammatical-error categories — this trainer is additive, not a replacement. The two
surfaces complement each other: cloze drills measure words in passage context; this
trainer drills the bare noun-classifier pairing for recall.

## Open Questions

None.

## Related Pages

- [[features/measure-word-trainer.tech]] — full technical specification
- [[features/pinyin-trainer]] — sibling Chinese trainer (per-test, not infinite)
- [[features/pitch-accent-trainer]] — sibling Japanese trainer
- [[features/vocab-dojo]] — the closest infinite-trainer pattern (BKT-driven)
- [[algorithms/elo-ranking]] — ELO formula shared by the trainer
