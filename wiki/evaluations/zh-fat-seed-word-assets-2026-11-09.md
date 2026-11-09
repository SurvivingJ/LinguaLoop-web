---
title: zh word assets — fat-seed pipeline tuning and full run
type: evaluation
status: complete
last_updated: 2026-11-09
open_questions:
  - "OPEN: the upload package (data/exercise_seeding/zh/upload/) is not applied yet. The developer applies it; exercises are then rendered (stage-8 judge + render)."
  - "OPEN: 1,851 rejected and 805 skipped senses are dictionary-data problems (duplicate sibling senses, bound characters, proper nouns, segmentation artifacts). See data/exercise_seeding/zh/issues/."
  - "OPEN: level_6 'wrong' sentences that are actually correct remain the largest defect class after the Opus second review."
---

# zh word assets — fat-seed pipeline tuning and full run

## Purpose
Record how the Chinese word assets (ladder exercises for ~19k senses) were produced, which configuration was
chosen and why, and the measured quality, so later languages and re-runs start from evidence.

## Summary
- **Scope:** every zh sense without a `prompt1_core` asset: 19,233 senses (both `simple` and `standard`
  definition levels, as for ja).
- **Result:** 16,361 senses packaged as 114,527 `word_assets` rows (7 asset types) plus 32,722 UPDATEs to
  `dim_vocabulary` / `dim_word_senses`. 805 senses were skipped by the author, 1,851 rejected by a reviewer and
  about 235 failed the final check.
- **Pipeline:** tool-free fat-seed (`scratch_offline/nt_pipeline.py`) with Sonnet/low core, Haiku audits and
  variants, Haiku/high patch review, then a second review by **Opus/low** over every passing sense.
- **Cost:** about $745 first pass + $868 Opus second review + ~$150 experiments and ~$80 judging.
  About $0.10 per packaged sense, pipeline and second review only.
- **Quality (frozen judge, Opus/medium, rubric 3):** first pass 6.67 mean, 0.166 fatal share (986 senses sampled).
  The Opus second review added +0.78 to +0.96 points per sense on paired samples and cut the fatal share to
  roughly 0.04–0.15 depending on the run range.

## Configuration search (gold sets)
Two 100-sense gold sets (`gold100`, held-out `gold100b`, no shared lemmas) were judged by Opus/medium, rubric 3.
Differences under ~0.55 points are noise.

| arm | score gold / held-out | fatal share | $/sense |
|---|---|---|---|
| ja production config on zh | 6.90 / — | 0.20 | 0.037 |
| Sonnet author + Opus/medium review (baseline) | 8.42 / 8.35 | 0.04–0.05 | 0.141–0.147 |
| new zh sheet + Haiku review effort high (adopted) | 7.29 / 7.17 | 0.09–0.10 | 0.044 |
| Haiku variants + Opus/medium review | 8.25 / 7.94 | 0.08–0.09 | 0.10–0.11 |
| Sonnet review instead of Opus | 8.41 / 7.53 | 0.06 / 0.15 | 0.11 |

Findings:
- The reviewer decides quality. A Sonnet reviewer tied on gold100 and failed on the held-out set.
- Haiku review effort high adds ~+0.4 for $0.003/sense.
- The longer cheat sheet (v2 proposal) did not help; the short sheet `zh_q3` cut level_7 losses and raised
  level_1 coverage. Its tone rule now matches the live L1 judge (tone changes on any syllable are allowed).
- Arm log: `data/exercise_seeding/zh/opt/ARMS.txt`; sheets in `opt/cheatsheets/`.

## Full run
- 1,603 runs of ≤12 senses, 24 workers, ~37 runs/hour. Interrupted by two container restarts and one user pause;
  every relaunch resumed from disk with no lost work.
- 19 runs failed on a Haiku repair reply that was invalid JSON twice; all were completed on relaunch.
- Quality fell in later runs: runs from about r0600 have no mined corpus sentences, so every sentence is generated
  (fatal share 0.15 early vs 0.20 late). The gold sets had 30% mined senses and did not cover this.

## Opus/low second review
A paired pilot on 306 judged late senses: 6.41 → 7.37 (+0.96 ± 0.25), fatal 0.203 → 0.111, $0.052/sense.
Applied in three batches over all 16,842 passing senses:

| runs | senses | paired judge sample | fatal share before → after | cost |
|---|---|---|---|---|
| r0000–r0400 | 4,512 | +0.78 ± 0.38 (105) | 0.124 → 0.038 | $235 |
| r0401–r0900 | 5,233 | +0.85 ± 0.36 (101) | 0.109 → 0.059 | $271 |
| r0901–r1602 | 7,097 | +0.90 ± 0.56 (62) | 0.177 → 0.145 | $362 |

The second review also rejected 353 senses the Haiku reviewer had passed.

## Defect classes that remain
- level_6: "wrong" sentences that are correct uses (无需: 乘客无需系安全带).
- level_3: distractors that also fit the blank (陌生 / 拥挤 with 一个人).
- level_7: planted errors natives accept (争辩过三个小时).
- core: sentences in another sense (强暴 read as rape; 微博 the post, not the platform).
- One cross-contaminated block in the sample (首相 carried 开幕's antonym block). A code check that every block
  belongs to its own headword would catch it.

## Artifacts
- Package: `data/exercise_seeding/zh/upload/` (chunks, gzipped all-in-one SQL and CSV, `verify.sql`, README).
- Issues: `data/exercise_seeding/zh/issues/`.
- Records: `data/exercise_seeding/zh/archive/` (JSON documents, tar.gz split into parts under 50 MB).
- Code: `.claude/skills/fat-seed-authoring/cheatsheets/zh.md`, `scratch_offline/nt_pipeline.py`
  (`REVIEW_ARGS_BY_LANG`).

## Related Pages
- [[tasklist/master]]
- [[evaluations/exercise-gen-phase2-2026-10]]
