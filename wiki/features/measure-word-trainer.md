---
title: Measure Word Trainer
type: feature
status: complete
tech_page: ./measure-word-trainer.tech.md
last_updated: 2026-06-07
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

A learner navigates to `/classifier-drill` (or meets the drill inside `/session`). The page
shows `一 ___ 猫` with the pinyin and gloss, and four buttons holding the correct classifier
and three plausible distractors from the same semantic group. Press **1–4** or click to
answer. Wrong → a feedback modal shows the canonical `一只猫`, the semantic-group reason
("animals are counted with 只 — small/medium"), and the learner's answer. A round is 20
items; finish a round to see accuracy, time, and ELO change. Hit "Next round" to keep going.

A header toggle switches between **Choose** (MC mode) and **Type** (text input mode). Type
mode accepts any of the multiple acceptable classifiers for that noun — `狗` accepts both
`只` and `条`.

## 个 is never trained

个 (gè) is the universal *catch-all* classifier: when in doubt a speaker can fall back to
个. Drilling it teaches nothing, and offering it as a wrong option lets the learner default
to it instead of learning the specific measure word. So the trainer **never shows 个** — not
as the answer, not as a distractor. Nouns whose only sensible classifier is 个 (苹果, 问题 …)
are simply left out of the drill; the focus is entirely on the specific measure words.

## How It Works

1. A session RPC samples up to 20 noun-classifier pairs from a curated dictionary, weighting
   by frequency, and always picking a *specific* (non-个) classifier as the item's answer.
2. For each picked noun the RPC returns: the noun's lemma, pinyin and gloss, *all* acceptable
   (non-个) classifier IDs (CC-CEDICT-style multi-valid), and three distractor classifiers.
   Distractors come from the answer's own semantic group, preferring common classifiers; when
   the answer is a general-purpose classifier, distractors are drawn from a pool of common
   specific classifiers instead — never 个.
3. The learner answers each item; the client tallies correct count and submits the batch
   result at end-of-round to `process_classifier_drill_submission`, which writes a
   `test_attempts` row against a hidden sentinel test and updates the user's `classifier_drill`
   ELO with the same K=32 formula used by the pinyin and pitch-accent trainers.

## Dictionary Source

The seed dictionary is hand-curated and ships embedded in
`scripts/build_classifier_dictionary.py` — **75 classifiers across 16 semantic groups**,
~870 curated noun-classifier pairs. The CC-CEDICT long tail (`CL:X[pin]` annotations from
`cedict_ts.u8`) is then layered on via `scripts/import_cedict_classifiers.py`, adding ~1.8k
more pairs (`source = 'cedict'`), for ~2.6k pairs total. Re-running the build script **wipes
and reinserts** the dictionary, so the script (plus the curation merge file) is the source of
truth; the CC-CEDICT import must be re-run after every build.

Coverage of the rarer measure words was expanded with an **offline LLM authoring pipeline**
(`services/classifier_curation/`, qwen via OpenRouter): the model proposes nouns + example
phrases, a judge scores them, and a human reviews the JSON before it is merged into the
curated dictionary. CC-CEDICT alone was exhausted as a source — it annotates almost no nouns
for classifiers like 束/锅/串 — so authored content is what gives every measure word enough
variety to drill. The serving path itself uses **no LLM** and is fully deterministic.

## Distractor Strategy

Each classifier belongs to one of 16 distractor groups, e.g. *animals* (只, 头, 匹, 群),
*long_thin* (条, 根, 支, 把), *vehicles* (辆, 架, 艘, 列), *containers* (杯, 瓶, 碗, 盒, 包, 袋),
plus newer buckets *abstract* (种, 项, 份, 门), *small_round* (颗/粒), *strands* (股), *sections*
(段, 节). Distractors are drawn from the correct answer's own group so the wrong choices are
always plausible — the learner cannot reject 头 just because it looks weird; they have to know
that 牛 takes 头, not 只. General-purpose answers (台, 颗 …) draw distractors from a pool of
common specific classifiers, so they are still confusable rather than random.

## Constraints & Edge Cases

- **Multi-acceptable nouns.** 狗 accepts both 只 and 条. The RPC returns all acceptable
  (non-个) IDs; the client accepts any in Type mode and highlights all of them after a miss.
- **Always three distractors.** Earlier the 个 fallback could leave an item with only two
  distractors; now distractors top up from a common-classifier core pool, so every MC item has
  a full set of four options.
- **Anti-repetition between rounds is not implemented.** A user playing back-to-back rounds can
  see the same noun twice — Phase 2 would add a `user_classifier_history` log.
- **Repeats earn no ELO.** Same first-attempt-only rule as pinyin/pitch-accent
  ([[algorithms/elo-ranking.tech]]).
- **Rare classifiers stay small.** A few genuinely sparse measure words (列 trains, 瓣 cloves)
  have only a handful of nouns even after curation; that is acceptable (there is no minimum-noun
  gate).

## Business Rules

- Chinese only (`language_id = 1`) in v1. Japanese counters (助数詞) are out of scope.
- Sentinel test row `slug = '__classifier_drill_zh'` is `is_active = false` so it never appears
  in test listings or recommendations; it only anchors `test_attempts` and `test_skill_ratings`.
- The route handler rejects any `language_id` other than 1.

## Interaction with the Cloze Pipeline

Cloze L6/L7 prompts continue to surface `量词错误` distractors as one of four grammatical-error
categories — this trainer is additive, not a replacement. Cloze drills measure words in passage
context; this trainer drills the bare noun-classifier pairing for recall.

## Open Questions

None.

## Related Pages

- [[features/measure-word-trainer.tech]] — full technical specification
- [[features/pinyin-trainer]] — sibling Chinese trainer (per-test, not infinite)
- [[features/pitch-accent-trainer]] — sibling Japanese trainer
- [[features/vocab-dojo]] — the closest infinite-trainer pattern (BKT-driven)
- [[algorithms/elo-ranking]] — ELO formula shared by the trainer
