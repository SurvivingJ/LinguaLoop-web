---
title: Chinese tagger trial — Stanza vs jieba
type: evaluation
status: complete
last_updated: 2026-11-12
open_questions:
  - "OPEN: validate jieba's guessed (HMM) words against a free dictionary (CC-CEDICT, CC BY-SA 4.0) before they become vocabulary? Needs the dictionary download (mdbg.net) and the developer's go-ahead."
  - "OPEN: of the 108 dictionary words that exist only because of jieba's guessing, which fakes to retire (and what happens to senses/tests linked to them)?"
---

# Chinese tagger trial — Stanza vs jieba

## Question
Would Stanza (Stanford, Apache 2.0 code; Chinese model trained on UD
Chinese-GSDSimp, CC BY-SA 4.0 — the only strong tagger found free for
commercial use; HanLP 2.x models are CC BY-NC-SA, LTP needs a paid licence)
give better Chinese word splitting and part of speech than jieba, which today
creates vocabulary and tags it? Prompted by jieba tagging 宗教改革
(Reformation) "nr" (person name) and creating the non-word 人用.

## Method
Read-only. All 125 active Chinese tests (53,238 characters). jieba
`posseg` (as `services/vocabulary/processors/chinese.py`) vs Stanza 1.15
`zh-hans` tokenize+pos, CPU. Tags compared after `services/vocabulary/pos.py`
`normalize_pos` (Stanza xpos NNB → measure_word). The one-off trial script
(`scripts/eval_zh_taggers_stanza_vs_jieba.py`, commit dad0f0e) and Stanza
itself were removed afterwards at the developer's request, and the
Hugging Face hosts added for the 419 MB model download were taken back out of
the environment's network allowlist.

## Results
| | jieba | Stanza |
|---|---|---|
| Speed (CPU) | 32,839 chars/s | 1,458 chars/s (≈22× slower) |
| Tokens | 32,247 | 35,132 (finer splitting) |
| Segmentation agreement (F1) | 0.825 | |
| POS agreement on identically split words | 65.9% | |

**Segmentation: Stanza is worse for a learner dictionary.** It over-splits
everyday words learners should meet whole — T恤 → T|恤, 微生物 → 微|生物,
成为 → 成|为, 看起来 → 看|起来, 有时候 → 有|时候, 泰迪熊 → 泰迪|熊,
供应链 → 供应|链, 咖啡豆 → 咖啡|豆, 一个 → 一|个 — and invents its own
non-words: 熊穿, 笔来, 人要, 升水, 去学, 可作, and 发展中国家 → …中国|家. It
also produced 人用 (3×) and never produced 宗教改革 (it splits it).

**Part of speech: the disagreements are mostly convention, not error.**
Stanza uses Universal Dependencies conventions that suit parsing, not
learners: 的 = SCONJ (909×), 是/要/会/可以 = AUX, 了/着 = AUX, 也/就 = SCONJ,
中/下 (localisers) = ADP, 这/该 = DET, 如果/虽然/因为 = ADP. Real errors exist
on both sides (jieba: 吸管 v, 变脏 n, 高昂 nr; Stanza: 一定 ADJ).

**Where jieba's problems come from (the useful finding).**
1. *Fake words* come from jieba's HMM guessing of unknown words: 301 distinct
   tokens across the corpus exist only with HMM on; **108 are in
   dim_vocabulary** (list: `data/zh_segmentation/2026-11-12_hmm_only_vocab.csv`).
   About half are fakes (人用, 会用, 人会, 水用, 要用, 很强, 更快, 帮花, 风一吹,
   厨余会, 酸丁二酯) and half are real modern words missing from jieba's
   dictionary (播客, 共情, 问责, 赋能, 厨余, 水培, 厌氧, 时区, 古腾堡). With HMM
   off, the fakes split correctly (很多人用 → 很多|人|用) but the real ones are
   lost too.
2. *Wrong tags* such as 宗教改革 nr and 高昂 nr are entries in jieba's own
   dictionary (HMM on or off makes no difference).

## Conclusion
Do not adopt Stanza: slower, worse splitting for learners, and a tagset that
fits learners less well. Keep jieba and fix its two failure modes
deterministically:
- validate HMM-guessed words against a free dictionary (CC-CEDICT) before
  they become vocabulary — keeps 播客/共情, drops 人用/很强;
- override jieba's dictionary tags with our own standardised tags via a jieba
  user dictionary built from vetted dim_vocabulary rows (after
  `migrations/standardise_part_of_speech.sql`), so 宗教改革 → noun.

## Related
- `services/vocabulary/processors/chinese.py`, `services/vocabulary/word_resolver.py` (word creation)
- `migrations/standardise_part_of_speech.sql`, `services/vocabulary/pos.py`
