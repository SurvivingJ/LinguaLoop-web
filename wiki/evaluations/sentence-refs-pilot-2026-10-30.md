---
title: "Sentence-reference pilot — two authoring arms, 30 tests per language (TASK-907)"
type: evaluation
status: complete
last_updated: 2026-10-30
---

# Sentence-reference pilot — two authoring arms, 30 tests per language

Implements TASK-907 of [[tasklist/test-sentence-references.tasks]] under
[[decisions/ADR-037-sentence-level-l1-references]]. All generation and review was done by Claude
subagents through the two new skills; no OpenRouter call was made. Spend: agent time only
(60 author turns, 30 reviewer turns, about 65–80k tokens each).

## Setup

- 30 active tests per language, stratified by difficulty from the live catalogue
  (`data/fixtures/sentence_refs/pilot_tests.json`; transcripts with a leading preamble excluded).
  L1 = English for Japanese and Chinese tests; L1 = Chinese for English tests.
- Two arms, same tests, independent author pools (Sonnet): `sentencewise` (translate one
  sentence at a time with the passage visible) and `aligned` (translate the passage as prose, then
  split into the aligned array).
- Deterministic checks (`sentence_ref_runner.py check`): 0 failures on 180 authored documents.
- Review (fresh context, blind to the arm): pack 01 of each run on Opus, packs 02–05 on Sonnet.
  Step 1 blind back-translation, step 2 judge against the gold, rewrite failures. Tightness =
  Tier 0 similarity (character-level for CJK, word-level for English) between the blind
  back-translation and the gold, computed by the runner.

## Results

| language | arm | sentences | blind for tightness | median tightness | p10 | entailment pass | rewritten | failed |
|---|---|---|---|---|---|---|---|---|
| ja | sentencewise | 119 | 114 (2 tests excluded) | **0.816** | 0.648 | 100% | 3.4% | 0 |
| ja | aligned | 119 | 119 | 0.812 | 0.608 | 100% | 6.7% | 0 |
| zh | sentencewise | 436 | 436 | **0.897** | 0.710 | 99.8% | 0.7% | 0.2% |
| zh | aligned | 436 | 436 | 0.894 | 0.715 | 100% | 0.7% | 0.2% |
| en | sentencewise | 481 | 339 (10 tests excluded) | 0.825 | 0.600 | 100% | 1.2% | 0 |
| en | aligned | 481 | 432 (4 tests excluded) | **0.840** | 0.593 | 100% | 1.0% | 0 |

Pooled share of sentences at or above a floor (both arms):

| language | n | ≥ 0.55 | ≥ 0.60 | p10 |
|---|---|---|---|---|
| ja | 238 | 95.0% | 94.1% | 0.64 |
| zh | 872 | 98.4% | 96.7% | 0.72 |
| en | 962 | 93.1% | 90.7% | 0.60 |

"Excluded" tests are those whose reviewer reported reading the gold before writing the blind
back-translation (16 of 180 test-reviews, all in the ja and en runs, listed in
`data/sentence_refs/pilot_2026-10-30/contaminated.json`). They are excluded from the tightness
statistics only; their entailment verdicts stand.

## Findings

1. **The two arms are indistinguishable on quality.** Median tightness differs by 0.004 (ja),
   0.003 (zh) and 0.015 (en); entailment pass is 99.8–100% in every arm. The decision rule
   (higher median unless entailment is more than 3 points lower) picks `sentencewise` for ja and
   zh and `aligned` for en, all inside noise. The one real difference is the **rewrite rate in
   Japanese: 3.4% sentencewise vs 6.7% aligned**, which is the reviewer catching drift introduced
   when a prose translation is split back into sentences.
2. **Reference quality is high in all three languages.** Of 2,072 sentence-reviews, 2,059 passed
   as authored, 11 were rewritten (word choice: "tea leaves" → "used tea leaves", "manual" →
   "physical labour", "anaerobic" rendered as "oxygen-starved"), and 2 failed because the gold
   itself is defective (zh test 4030db89 idx 0 contains the English word "saving" inside the
   Chinese; both arms flagged it independently).
3. **Low tightness is mostly a measurement artefact, not a bad reference.** The worst sentences
   are (a) very short English sentences where word-level similarity is unforgiving ("A bus is
   big" vs "Buses are big" = 0.29), (b) hiragana-only Japanese gold for children's tests where the
   reviewer back-translated in kanji (いしを つんで つくります vs 石を積み重ねて造ります = 0.36), and
   (c) lexical synonyms (外傷 vs けが, 待客之道 vs 招待客人的方式). Every one of them passed
   entailment with a reviewer note. Two fixes are filed as follow-ups: normalise kana/kanji before
   scoring, and skip the floor for sentences under 8 units.
4. **The blind step leaked in the harness, not in the reviewers.** The single-file review pack
   with a "do not read past this line" marker was read past by `sed` ranges in 5 of 30 reviews.
   Fixed the same day: `review-pack` now writes a blind file and a separate `.gold.md` file, the
   rules and the review skill say to open the gold file only after every back-translation is
   written, and `gold_seen_early` is a named note. The ja and zh runs are 2/60 and 0/60
   contaminated; the en runs 14/60, because the long English passages pushed the markers below
   the first `sed` window.
5. **Transcript defects surface for free.** Beyond the "saving" leak, reviewers noted a ja gold
   typo (入り方 for 入り口, test d5327ad9) and an oddly phrased ja gold (「主権」は私の番です,
   test 309431d5). These go to the transcript cleanup list (TASK-900 scope).
6. **Throughput.** Author turns took 25–60 s each for six tests; reviews 55–110 s. The full
   catalogue (305 tests, first L1 set) is about 51 author turns and 51 reviewer turns per arm,
   which is an afternoon of agent time, not days.

## Decision

- **Arm: `sentencewise` for every language.** It wins two of three languages, has the lowest
  Japanese rewrite rate, and its English deficit is inside noise on a sample that lost ten tests to
  contamination. One arm for all languages keeps the skill simple. Recorded in ADR-037.
- **Tightness floor, per language, from p10 rounded to 0.05: ja 0.65, zh 0.70, en 0.60.** Applied
  by the Produce window selector only for sentences of 8 or more units until the two scoring
  fixes above land; the floor is a preference, never a block, because entailment is the gate.
- **Full run (TASK-908) is unblocked.** Use the blind/gold split review packs; send pack 01 of
  each run plus every deterministic warning to Opus, the rest to Sonnet.
- The pilot's 2,072 reviewed references are assembled in each run's `upload.json` and can be
  uploaded with `--no-activate` once TASK-901 is applied live; the winning arm's rows are then
  activated by TASK-908.

## Open questions re-stated

- The tightness floor was set from p10; whether it predicts a learner's Produce experience is
  unmeasured until Produce has traffic (the `prestudy_sessions.produce` block records it).
- Second L1 set (ja for zh tests, zh for ja tests) not piloted; expect similar numbers but the
  kana/kanji artefact will not apply.
- Whether a transcript edit should retire or flag references: unchanged (retire by hash).

## Related Pages

- [[decisions/ADR-037-sentence-level-l1-references]]
- [[features/test-sentence-references]] / [[features/test-sentence-references.tech]]
- [[tasklist/test-sentence-references.tasks]]
- [[features/test-prestudy]] — the Produce stage these references serve
