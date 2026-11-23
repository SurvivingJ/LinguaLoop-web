# Vocabulary placement test: simulating candidate adaptive designs

**TASK-1073, research stage (simulation).** 2026-11-18. Written by the simulation agent, for the synthesis stage.
No application code was written, and no database writes were made: the only database access was six read-only SELECT queries (§7).

**Labels.** Every result from the simulation is an **ESTIMATE**: it holds only for the learner model in §2.2, which
is an assumption. **MEASURED** marks facts read from the live database, the exports or the code, with file:line or the
SQL. **INFERENCE** marks my reasoning. 500 synthetic learners per population (8 populations, 4,000 learners), each
taking all 9 designs (common random numbers). Sensitivity runs used 300 learners per population.

**Owner decisions taken as fixed:** (1) build on the adaptive check, using the existing four-option items with a stopping rule;
(2) no fake words and no Yes/No self-report; (3) zh and ja test both meaning and reading; English tests meaning only.

## 0. Findings in brief

1. **Precision is the binding limit, not test length** (ESTIMATE). In 3–6 minutes, a vocabulary count from the
   check's four-option items is good to roughly **±10–13% of the check pool** (90% interval half-width). That is about
   ±360–470 of 3,623 zh words, or ±320–410 of 3,175 ja words. Today's fixed check (D0, 70 items) gives ±10.4–11.1%.
   No design reached ±6% within 90 items. An SE-based stopping rule ends the test early mainly for beginners: with
   h = 10% of the pool and a cap of 40 items, 15% of D1 learners stop early. The **cap is the real stopping rule**.
2. **Adaptivity saves about 40% of the items** (ESTIMATE). IRT-style adaptive meaning items (D1) at 40 items match
   D0 at 70: ±10.8–11.7% half-width, MAE 5.2–5.7% of the pool, 90–91% coverage. That is about 3.4 minutes with
   measured latencies, against 6.0. Adaptive stratified sampling (D1S), which keeps today's estimator, matches D0 at
   about 50 items. Gains are modest because knowledge falls off slowly with frequency. The owner's own answers show a
   slope of 1.05 per Zipf point (MEASURED, n = 1), so no band is safely known or unknown. The four-option guessing
   floor also limits what each item tells us.
3. **Ask the reading only after a correct meaning answer (D3/D3S)** (ESTIMATE). This is the cheapest way to measure
   "knows the word" (meaning and reading). In 60 items, about 41 are meaning and 19 are reading, about 5.1 minutes
   measured. The meaning-and-reading count has MAE 4.2–6.5% of the pool and 85–96% coverage. Asking the reading for
   every word (D2) spends about 60% more reading items for no gain. A reading answer after a wrong meaning answer says
   nothing about "knows the word" (derivation in §6). Asking it on a fixed half of the words (D4) still credits
   13–39% of the words it marks known wrongly.
4. **Meaning-only designs badly mislabel cognate learners** (ESTIMATE). Take Japanese-L1 learners of Chinese: any
   meaning-only design reports **+27–30% of the pool (about 1,000 words) more "known words"** than they know with the
   reading. With D0, D1 or D1S, 91–96% of them get an interval wholly above their true count, and 46–53% of the words
   those designs would credit lack the reading (73% and 35% for the level-stratified D1L). For Chinese-L1 learners of Japanese, the overstatement is +14–17%, and 44–70% of them get
   an interval wholly above their true count. The conditional reading item cuts this to near-zero bias:
   3–6% of learners get an interval above their true count, and 9–13% of credited words lack the reading. Those
   remaining credits are mostly guesses on both items.
   If a learner who knows the meaning can half-guess the reading (`partial` run), the bias returns to +2–4%.
5. **Exam-level placement is coarse whatever the design** (ESTIMATE). Exam-level placement is right within one
   HSK/JLPT level for 59–87% of learners and exact for 47–78%, depending on design and population (D3S: 80–86% and
   69–78%). The per-level known share has an MAE of 6–13 percentage points. For advanced learners the IRT design
   places only 32–33% within one level, against 60–64% for the
   band-stratified design and 66–70% for the level-stratified one.
6. **Frequency bands vs exam levels as strata depends on an unknown** (ESTIMATE). The unknown is how much exam level
   predicts knowledge beyond frequency. In the base model, band strata plus the §2.8a level mapping (D3S) give the
   best balance: unbiased counts and 80–86% within one level. Level strata (D3L) widen count intervals by 20–45%
   and overplace 13–19% of learners. If exam level matters more (`gamma25` run), band-based placement collapses
   (zh: 36–46% within one level, level-share MAE 17–20 points), while level strata keep 88–92%. This is the knowledge-report
   S8 concern ("list words are not exchangeable with frame words"), and it can be measured from early answers (§5).
7. **Design-based or model-based scoring?** (ESTIMATE). The design-based D3S (ADR-051 estimator applied to meaning
   and to the meaning-reading pair) is **unbiased in every population**: bias −0.6..+0.9% of the pool, coverage
   88–91%. The model-based D3 has slightly lower error but biases up to −4.4% of the pool (85% coverage for
   English-L1 learners of Japanese), from a curve that is misspecified. D3 also places levels worse. Both hold up when
   word-difficulty noise varies from 0.6 to 1.8 logits.
8. **The pool covers only about a third of each low exam level** (MEASURED). The check pool holds 95 of 300 HSK 1
   words, 67 of 202 HSK 2, 290 of 1,015 HSK 4, 274 of 718 JLPT N5 and 244 of 1,905 N2. 46% (zh) and 40% (ja) of pool
   words are on no list. Only **65% of ja pool words have a usable reading item** (2,069 of 3,175), against 98% for zh.
9. **Timing** (MEASURED latencies, small n). Meaning items are answered faster than the brief's 6 s and reading items
   match its 5 s: ja meaning items take a mean 4.2 s (median 3.1 s), ja reading items 5.0 s (median 3.6 s). With the post-answer pause, 40
   meaning items take about 3.4 minutes and 60 mixed items about 5.1 minutes.
10. **Model "knows the word" as meaning × P(reading | meaning)** (ESTIMATE, a lesson from this run). My first
    version (D2i–D4i) fitted "knows meaning and reading" as its own curve. It overstated the count by up to +8.7% of
    the pool for English-L1 learners of Chinese and had 78–86% coverage for Japanese-L1 learners of Chinese. Modelling the
    conditional curve ρ(z) = P(reading | meaning) fixed both (§3.7).

**What the simulation favours** (INFERENCE; for the synthesis stage to decide):
- **zh and ja: D3S.** Adaptive stratified sampling over the 7 Zipf bands, 2 per band to start, then Neyman-style
  allocation. The reading item comes only after a correct meaning answer. Score with the existing ADR-051 estimator
  on both the meaning outcome and the pair outcome. Cap at 60 items (about 5 minutes), with an early exit once both
  90% half-widths are at most 12% of the pool after 40 items.
- **English: D1S or D1 at 40 meaning items** (about 3.4 minutes).
- **Upgrade to the IRT scoring (D3 with ρ) once item difficulties have been calibrated** from responses. It is
  worth about 10–20% lower error for the counts, but not for placement.
- **Show exam levels as a range** (for example "HSK 3–4"), never as a single level.
- **Decide between band and level strata** once first-user data shows whether list words differ from same-band words.

## 1. Question and scope

The brief asked for a simulation of synthetic learners taking candidate placement designs over the real word pools
(zh, ja). Designs: D0, today's fixed check; D1, adaptive with meaning only; D2, both items for every word; D3, the
reading only after a correct meaning answer; D4, the reading on a fixed share of words. Selection by exam level was to
be compared with selection by frequency band. Metrics: items and minutes; error and interval coverage for words known
by meaning, for words known by meaning AND reading, and for HSK/JLPT placement; and how often a design mislabels a
cognate learner as knowing a word when they know only its meaning. Each of D1 and D3 was built two ways, IRT-style
(model-based) and stratified (design-based, keeping ADR-051's estimator), because that choice matters as much as the
item format. English was not simulated: it is meaning-only and would behave like D1 or D1S.

## 2. Method

### 2.1 Word pool (MEASURED inputs)

- **Words.** The check's definition-mode pool, read-only from the live database (`calibration_anchor_pool`, definition
  language 2, `has_embedding`): 3,682 zh and 3,263 ja distinct `vocab_id`s (SQL in §7). Zipf per word from
  `mock/data/dict.json` (it contains every zh pool id and 3,237 of the 3,263 ja ids). Subsampled per Zipf band to the
  frame sizes N_b of ADR-051 (fixed seed): **zh 3,623 = [303, 617, 742, 691, 664, 435, 171]**, **ja 3,175 =
  [577, 425, 621, 655, 537, 283, 77]** (bands 1..7, rarest to most common, `build_data.py:22-25`).
- **Reading items.** A word has a reading item when the live pool has a pronunciation row for it
  (`has_pronunciation`: zh 3,656 ids, ja 2,339 ids) and, for ja, it is not kana-only. The pool already excludes
  hiragana-only headwords from pronunciation mode (`migrations/task772_calibration_anchor_pool.sql:151-155`); the
  simulation also excludes katakana-only words (325 in the ja pool) because their reading is a script conversion
  (INFERENCE). Result: **zh 3,560 of 3,623 words (98%)**, **ja 2,069 of 3,175 (65%)** have a reading item. For words
  without one, "knows the word" = "knows the meaning".
- **Exam levels.** HSK 3.0 2025 (`krmanik_HSK-3.0/2025/HSK_Level_*_words.txt`, same expansion rule as
  `build_data.py:103-114`) and JLPT N5–N1 (`jamsinclair_open-anki-jlpt-decks/n5..n1.csv`), matched by lemma (ja: also
  reading + shared kanji, as `build_data.py:136-150`); a word takes its lowest level; unmatched list entries are not in
  the pool. Pool words per level:

  | list | L1 | L2 | L3 | L4 | L5 | L6 | L7 (7–9) | not on the list |
  |---|---|---|---|---|---|---|---|---|
  | HSK (zh pool) | 95 of 300 | 67 of 202 | 164 of 506 | 290 of 1,015 | 495 of 1,631 | 372 of 1,809 | 481 of 5,605 | 1,659 |
  | JLPT (ja pool) | N5 274 of 718 | N4 229 of 668 | N3 686 of 2,140 | N2 244 of 1,905 | N1 460 of 2,699 | | | 1,282 |

  MEASURED (`out/pool_stats.txt`): **the check pool holds only about a third of each HSK 1–5 level and of JLPT N5–N3**
  (and 9–18% of HSK 7–9, N2, N1); 46% (zh) and 40% (ja) of pool words are on no list. Level placement from the check
  pool therefore rests on samples of 67–495 words per level.

### 2.2 Learner model (ASSUMPTIONS, partly anchored on real data)

Per word w: Zipf z_w; a shared word difficulty residual ε_w ~ N(0, σ_ε = 1.2 logits) (fixed across learners); a
standardised exam-level residual ℓ_w (the word's level minus the level its Zipf predicts, linear fit over the pool;
unlisted = top level + 1); a cognate flag c_w for the learner's L1 (drawn once per word):
zh for ja-L1 0.55 (multi-character) / 0.30 (single); ja for zh-L1 0.65 (all-kanji compounds) / 0.45 (other kanji
words) / 0.20 (katakana); ja for en-L1 0.80 on katakana-only words (loanwords); otherwise 0.

Per learner: study frontier τ ~ U(2.5, 7.0) Zipf (the Zipf at which half of words are learned; 7.0 = near-beginner,
2.5 = knows most of the pool); slope a ~ lognormal(median 1.6, sd 0.2) per Zipf; exam-orientation γ ~ U(0, 1);
skip-if-unknown propensity s ~ N(s_pop, 0.1) with s_pop ∈ {0.3, 0.7}; cognate transfer κ, reading retention π, cognate
reading ν, compositional reading ω (ranges per profile below).

Generative knowledge per word (each draw independent):

    F_w (learned through study)  ~ Bernoulli( σ( a·(z_w − τ) − ε_w − γ·ℓ_w ) )
    C_w (meaning via L1 cognate) ~ Bernoulli( κ·c_w )            [only if not F_w]
    M_w (knows the meaning)      = F_w or C_w
    R_w (knows the reading)      = no reading item:  M_w
                                   F_w:              Bernoulli( π + (1 − π)·σ(a·(z_w − τ) − 1) )
                                   C_w only:         Bernoulli( ν )
                                   neither:          Bernoulli( ω·σ(a·(z_w − τ) + 1.5) )   (reads it from its characters)
    "knows the word" MR_w        = M_w and R_w

| profile | κ (cognate meaning) | π (reading of a learned word, at the frontier) | ν (reading of a cognate-only word) | ω (reading from characters) |
|---|---|---|---|---|
| zh, English L1 | 0 | 0.60–0.90 (tones) | — | 0.10–0.40 |
| zh, Japanese L1 | 0.60–0.95 | 0.60–0.90 | 0.03–0.15 | 0.10–0.40 |
| ja, English L1 | 0.50–0.85 (katakana loanwords) | 0.75–0.95 | — | 0.05–0.30 |
| ja, Chinese L1 | 0.60–0.95 | 0.70–0.95 | 0.10–0.35 (on'yomi) | 0.05–0.30 |

Responses: a known item is answered correctly; an unknown item is skipped ("I don't know") with probability s,
otherwise guessed (correct with probability 0.25). Meaning and reading items behave the same way.
Sensitivity run `partial`: a learner who knows the meaning but not the reading skips half as often and guesses the
reading right 40% of the time (partial knowledge eliminates an option).

**Anchors in real data (MEASURED, n = 1 learner, so weak):** fitting the same response model to the owner's own check
answers (`mock/data/real_events.json`, key `cal`, ja with English definitions; script `sim/fit_owner.py`, output
`out/fit_owner.txt`) gives, for meanings (178 answers), a knowledge slope of **1.05 per Zipf point** (90% profile
interval 0.70–1.55), 50%-known Zipf 4.60 and **skip-if-unknown 0.75**; for readings (99 answers) slope 0.80
(0.50–1.20), 50%-known Zipf 3.80, skip 0.95. The base learner model has a marginal (population-of-words) slope of about
1.23 per Zipf (r between word difficulty and Zipf ≈ 0.73–0.76); the `eps18` sensitivity run (σ_ε = 1.8) has 1.03
(r ≈ 0.60–0.63), closer to the owner's slope and to the literature's r ≈ 0.5 between frequency and item facility
(research-literature.md, A1). The skip setting 0.7 matches the owner; 0.3 is the pessimistic case for guessing.

### 2.3 Designs

All designs use the check's existing four-option items and "I don't know". "Reading" = the existing Readings mode item
for the same word (four pronunciations, one sound apart). Two estimator families are compared:

- **Design-based (stratified):** the ADR-051 estimator, unchanged: per stratum K = c/n − (1/3)·w/n (skip = not known),
  Jeffreys-smoothed multinomial variance with the finite-population factor, T = Σ N_h K_h. Per-level shares by
  knowledge-report.tech.md §2.8a (`est_L = Σ_b D_{L,b} K_b`) when the strata are Zipf bands, directly when the strata
  are exam levels. For "knows the word" the same estimator is applied to the pair outcome: K_mr = (both right − right
  then reading wrong ÷ 3)/n — unbiased because a reading guess after a meaning guess is as likely as after a known
  meaning (derivation in §6).
- **Model-based (IRT-style):** per learner, a grid posterior over a knowledge curve in Zipf,
  P(known | z) = f + (1 − f)·σ(s·(z − m)), with a floor f for cognates (47 × 4 × 5 grid; prior m ~ N(4.8, 1.4),
  s lognormal(1.15, 0.35), f prior by the learner's L1: mostly 0 for English L1, flat for ja/zh L1). Guessing rate
  g = (1 − q̂)/4 with q̂ the learner's running skip share among unknowns. For readings, a second curve
  ρ(z) = P(reading known | meaning known), so P(knows the word | z) = P(known | z)·ρ(z) can never exceed the meaning
  curve; it is updated only by reading answers that follow a correct meaning answer (likelihood conditions on the
  meaning answer; §6; grid 25 × 3 × 5 × 2 over location, slope, floor 0–0.8 and ceiling 0.85/1, with an L1-informed
  floor prior). Counts T = Σ_words P(known | z_w) over the whole pool, variance = posterior variance +
  Bernoulli variance. Item choice: the 0.2-Zipf bin whose answer most reduces the relative posterior variance of the
  reported count(s) (Bayes-linear, Cov(T, P_z)² / Var(y)); a random unused word from that bin.

| id | items chosen | reading items | estimator |
|---|---|---|---|
| D0 | fixed: 10 per band, band round-robin (today's check, meaning only) | none | design-based |
| D1 | adaptive (IRT) | none | model-based |
| D1S | adaptive stratified: 2 per band, then the band whose next item most reduces Var(T) | none | design-based |
| D1L | as D1S with exam levels + "not on the list" as strata; allocation also targets levels whose share is near 80% | none | design-based |
| D2 | adaptive (IRT) | after every meaning item | model-based |
| D3 | adaptive (IRT) | only after a correct meaning answer | model-based |
| D4 | adaptive (IRT) | on every second word, whatever the meaning answer | model-based |
| D3S | adaptive stratified by band (as D1S) | only after a correct meaning answer | design-based |
| D3L | adaptive stratified by exam level (as D1L) | only after a correct meaning answer | design-based |

Each design runs to a cap (70 items meaning-only, 90 with readings) and its estimates are recorded at item counts
15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90. A snapshot equals a fixed-length test of that length (the item choice
never depends on the cap), and stopping rules are evaluated on the snapshots (stop at the first checkpoint where every
reported 90% half-width ≤ h × N, after a minimum of 20 items, else at the cap).

### 2.4 Time per item

Brief default: 6 s per meaning item, 5 s per reading item. **Measured alternative (MEASURED, small n):** live
`calibration_responses.latency_ms` (render to tap, `static/js/pages/calibration.js:273,339`), ja, capped at 30 s:
meaning items mean 4.59 s correct / 3.05 s wrong / 4.34 s skip (206 answers, 2 users; median 3.1 s), reading items
3.59 s correct / 7.12 s skip (99 answers, 1 user; median 3.6 s). zh answers (39, one user, median 0.36 s) look like
test clicking and were not used. To these the model adds the 0.45 s auto-advance after a correct answer
(`calibration.js:47,379`) and an ASSUMED 1.5 s to read the key and tap on after a wrong answer or skip (that wait is
not measured; `calibration.js:380-386`).

### 2.5 Metrics

Per learner (truth = the simulated learner's actual known words in the pool): error of the meaning count and of the
"knows the word" count as % of the pool (bias, mean absolute error, 5th–95th percentile range), coverage of the 90%
interval and its half-width; exam placement = number of leading levels whose cumulative known share is ≥ 80% (the
report's "next level" rule, knowledge-report.tech.md §2.8 P13), exact and ±1; and three mislabelling measures:
(1) share of learners whose reported "known words" interval lies wholly above their true "knows the word" count,
(2) share placed above their true "knows the word" level, (3) of the words a design credits as known (all items for
that word answered right), the share the learner does not know by meaning AND reading, and the share not known at all
(lucky guesses). Meaning-only designs report the meaning count as "known words", so (1)–(3) measure what they would
claim if used for "knows the word".

## 3. Results (main run, base learner model; all ESTIMATE)

Populations, truth (from `out/tables_main.md`): English-L1 learners know 37–41% of the pool by meaning, and 5–12% of
those words lack the reading. Japanese-L1 learners of zh know 62–64% by meaning, but **44–47% of those words lack the
pinyin**, because the realised cognate share is 54% of zh pool words. Chinese-L1 learners of ja know 60–61% by
meaning, of which **25–27% lack the reading** (cognate share 52%). Katakana loanwords make 8% of ja pool words
cognates for English speakers. The study frontier is uniform over Zipf 2.5–7.0, so many learners are beginners: 32–63%
have true meaning placement 0, meaning below 80% of HSK 1 / N5 known.

"Budget snapshot" means D0 at 70 items, the meaning-only designs at 40, and the reading designs at 60 items in total.

### 3.1 Length and time

#### Table 1. Length and time (budget snapshot; mean over all populations)

| design | items | of which reading | minutes, brief (6 s / 5 s) | minutes, measured latencies (mean / 95th pct) |
|---|---|---|---|---|
| D0 | 70 | 0 | 7.0 | 6.0 / 6.2 |
| D1 | 40 | 0 | 4.0 | 3.4 / 3.6 |
| D1S | 40 | 0 | 4.0 | 3.4 / 3.6 |
| D1L | 40 | 0 | 4.0 | 3.4 / 3.5 |
| D2 | 60 | 30 | 5.5 | 5.4 / 6.0 |
| D3 | 60 | 19 | 5.7 | 5.1 / 5.6 |
| D4 | 60 | 20 | 5.7 | 5.3 / 5.8 |
| D3S | 60 | 19 | 5.7 | 5.1 / 5.6 |
| D3L | 60 | 21 | 5.7 | 5.1 / 5.5 |

### 3.2 Words known by meaning

#### Table 2. Words known by MEANING in the pool — budget snapshot; MAE / 90% coverage / mean 90% half-width, % of the pool; both skip settings averaged

| design | zh·en-L1 | zh·ja-L1 | ja·en-L1 | ja·zh-L1 | bias range |
|---|---|---|---|---|---|
| D0 | 5.2 / 90% / ±10.4 | 5.0 / 91% / ±10.9 | 5.2 / 90% / ±10.9 | 5.4 / 89% / ±11.1 | -0.6..0.5 |
| D1 | 5.4 / 90% / ±11.0 | 5.7 / 91% / ±11.6 | 5.2 / 91% / ±10.8 | 5.4 / 91% / ±11.7 | -2.7..2.0 |
| D1S | 6.4 / 88% / ±12.7 | 6.6 / 89% / ±13.5 | 7.1 / 86% / ±13.1 | 6.7 / 89% / ±13.6 | -1.3..1.4 |
| D1L | 9.1 / 89% / ±17.2 | 9.9 / 87% / ±19.0 | 8.5 / 85% / ±15.1 | 8.7 / 83% / ±16.3 | -2.0..-0.3 |
| D2 | 6.0 / 93% / ±12.5 | 6.6 / 90% / ±13.4 | 5.2 / 94% / ±12.2 | 6.0 / 92% / ±13.3 | -3.4..2.5 |
| D3 | 5.0 / 92% / ±11.0 | 6.0 / 91% / ±12.3 | 5.3 / 89% / ±10.4 | 5.5 / 90% / ±11.6 | -3.0..2.1 |
| D4 | 5.1 / 92% / ±11.0 | 5.9 / 90% / ±11.7 | 5.0 / 91% / ±10.8 | 5.6 / 89% / ±11.7 | -2.6..2.5 |
| D3S | 6.2 / 90% / ±12.6 | 7.0 / 90% / ±14.3 | 6.0 / 89% / ±12.2 | 6.7 / 87% / ±13.4 | -1.0..0.5 |
| D3L | 9.5 / 88% / ±18.1 | 10.7 / 87% / ±20.8 | 7.9 / 85% / ±14.5 | 8.8 / 86% / ±16.3 | -2.5..-0.1 |

Precision against test length (mean 90% half-width, % of the pool; zh / ja; coverage stays at 84–95% throughout):

| design (count reported) | 20 items | 30 | 40 | 60 | 70 | 90 |
|---|---|---|---|---|---|---|
| D0 meaning | ±20.7 / 21.2 | ±16.6 / 17.1 | ±14.3 / 14.7 | ±11.6 / 11.9 | ±10.7 / 11.0 | — |
| D1 meaning | ±15.0 / 15.0 | ±12.7 / 12.7 | ±11.3 / 11.3 | ±9.4 / 9.5 | ±8.8 / 8.8 | — |
| D1S meaning | ±19.4 / 19.7 | ±15.3 / 15.6 | ±13.1 / 13.3 | ±10.5 / 10.7 | ±9.7 / 9.9 | — |
| D1L meaning | ±28.4 / 23.5 | ±21.8 / 18.5 | ±18.1 / 15.7 | ±14.0 / 12.4 | ±12.8 / 11.4 | — |
| D2 meaning+reading | — | ±15.7 / 15.4 | ±14.1 / 13.8 | ±12.0 / 11.8 | ±11.2 / 11.1 | ±10.1 / 10.0 |
| D3 meaning+reading | — | ±14.6 / 14.1 | ±13.0 / 12.6 | ±11.0 / 10.7 | ±10.3 / 10.0 | ±9.2 / 9.0 |
| D4 meaning+reading | — | ±15.9 / 14.7 | ±14.2 / 13.1 | ±12.3 / 11.2 | ±11.5 / 10.5 | ±10.5 / 9.5 |
| D3S meaning+reading | — | ±18.0 / 18.0 | ±15.0 / 15.2 | ±11.9 / 12.1 | ±10.9 / 11.1 | ±9.5 / 9.7 |
| D3L meaning+reading | — | ±25.7 / 21.8 | ±22.1 / 18.2 | ±16.8 / 14.4 | ±15.1 / 13.2 | ±12.9 / 11.4 |

Read across: D1 at 40 items ≈ D0 at 70. D1S at 40 ≈ D0 at about 50. D3S trails D3 by about 1 point at 60 items and
nearly catches up by 90; its 2-per-band warm-up costs precision early on.

### 3.3 Words known by meaning AND reading ("knows the word")

#### Table 3. Words known by MEANING AND READING ("knows the word") — budget snapshot; MAE / 90% coverage / mean 90% half-width, % of the pool; both skip settings averaged

Meaning-only rows show what they would claim: their meaning count minus the true meaning+reading count (% of the
pool), and how often their interval contains the true meaning+reading count.

| design | zh·en-L1 | zh·ja-L1 | ja·en-L1 | ja·zh-L1 | bias range |
|---|---|---|---|---|---|
| D0 | reports meaning: +4.4 / 80% | reports meaning: +28.6 / 4% | reports meaning: +2.1 / 88% | reports meaning: +15.9 / 30% | |
| D1 | reports meaning: +6.1 / 78% | reports meaning: +27.1 / 9% | reports meaning: -0.4 / 92% | reports meaning: +16.6 / 31% | |
| D1S | reports meaning: +3.6 / 86% | reports meaning: +29.7 / 8% | reports meaning: +1.2 / 86% | reports meaning: +15.9 / 41% | |
| D1L | reports meaning: +2.8 / 89% | reports meaning: +27.7 / 27% | reports meaning: +0.2 / 86% | reports meaning: +14.2 / 56% | |
| D2 | 5.1 / 96% / ±11.7 | 5.4 / 94% / ±12.3 | 5.4 / 91% / ±11.5 | 5.0 / 94% / ±12.1 | -4.0..1.3 |
| D3 | 4.2 / 96% / ±10.5 | 5.2 / 94% / ±11.5 | 5.6 / 85% / ±10.1 | 5.1 / 93% / ±11.3 | -4.4..2.0 |
| D4 | 4.8 / 94% / ±11.1 | 6.5 / 92% / ±13.6 | 5.7 / 86% / ±10.6 | 5.5 / 91% / ±11.9 | -4.5..1.8 |
| D3S | 5.2 / 91% / ±10.9 | 6.2 / 90% / ±12.8 | 5.4 / 90% / ±11.3 | 6.5 / 88% / ±12.9 | -0.6..0.9 |
| D3L | 7.1 / 92% / ±15.7 | 9.1 / 90% / ±18.0 | 7.1 / 84% / ±13.4 | 8.1 / 87% / ±15.4 | -1.9..0.1 |

D2 asks 30 reading items in 60 and D3 asks 19, yet D3 is as precise or better. Under the model, reading answers after
a wrong or skipped meaning answer are uninformative (§6), so D2 spends about 11 items on them. D4 is close to D3 on
the count, but see Table 5 for what it credits.

### 3.4 Exam placement

Placement is the number of leading levels whose cumulative known share is at least 80% (HSK 1–6 and 7–9; JLPT N5–N1).

#### Table 4. Exam placement (HSK 2025 for zh, JLPT for ja): exact / within one level, "knows the word" (meaning-only designs: their meaning placement vs the true "knows the word" placement); in brackets the same for meaning placement vs true meaning placement

| design | zh·en-L1 | zh·ja-L1 | ja·en-L1 | ja·zh-L1 |
|---|---|---|---|---|
| D0 | 74 / 85 (63 / 72) | 66 / 76 (63 / 72) | 78 / 86 (74 / 80) | 76 / 83 (76 / 84) |
| D1 | 71 / 78 (58 / 66) | 68 / 78 (58 / 67) | 73 / 80 (69 / 75) | 77 / 84 (72 / 78) |
| D1S | 71 / 81 (64 / 73) | 59 / 69 (61 / 70) | 76 / 86 (74 / 82) | 70 / 78 (73 / 82) |
| D1L | 59 / 75 (64 / 84) | 47 / 59 (62 / 77) | 70 / 86 (73 / 87) | 63 / 75 (70 / 84) |
| D2 | 63 / 69 (57 / 66) | 64 / 70 (57 / 65) | 70 / 73 (68 / 75) | 73 / 78 (71 / 77) |
| D3 | 64 / 69 (58 / 65) | 64 / 69 (58 / 64) | 69 / 74 (70 / 76) | 73 / 78 (75 / 81) |
| D4 | 62 / 68 (59 / 67) | 64 / 68 (57 / 65) | 69 / 73 (70 / 75) | 73 / 78 (71 / 78) |
| D3S | 69 / 80 (62 / 71) | 72 / 80 (60 / 70) | 77 / 84 (75 / 82) | 78 / 86 (75 / 83) |
| D3L | 67 / 82 (63 / 84) | 63 / 78 (60 / 76) | 74 / 87 (72 / 88) | 75 / 87 (69 / 82) |

#### Table 4b. Mean absolute error of the cumulative per-level known share (percentage points), meaning / "knows the word"

| design | zh·en-L1 | zh·ja-L1 | ja·en-L1 | ja·zh-L1 |
|---|---|---|---|---|
| D0 | 10.8 / — | 7.8 / — | 8.8 / — | 6.3 / — |
| D1 | 12.7 / — | 8.7 / — | 10.1 / — | 7.6 / — |
| D1S | 11.7 / — | 9.1 / — | 9.5 / — | 7.6 / — |
| D1L | 9.3 / — | 9.3 / — | 9.7 / — | 10.2 / — |
| D2 | 12.5 / 12.1 | 9.5 / 12.8 | 9.7 / 10.5 | 8.0 / 9.0 |
| D3 | 12.2 / 11.6 | 8.9 / 12.4 | 10.1 / 10.9 | 7.1 / 8.5 |
| D4 | 12.1 / 12.1 | 9.1 / 13.1 | 10.0 / 11.2 | 7.5 / 9.2 |
| D3S | 11.6 / 10.2 | 9.2 / 10.7 | 9.2 / 8.4 | 7.5 / 7.7 |
| D3L | 9.6 / 9.3 | 9.7 / 9.9 | 9.3 / 9.0 | 10.3 / 9.5 |

By ability, within-one-level placement for "knows the word", all populations of a language pooled
(from `out/tables_main.md`; beginners are trivially placed at 0):

| design | zh beginner / intermediate / advanced | ja beginner / intermediate / advanced |
|---|---|---|
| D0 (meaning vs m+r truth) | 99 / 66 / 74 | 100 / 90 / 63 |
| D1 | 99 / 68 / 65 | 100 / 92 / 53 |
| D3 | 100 / 72 / **32** | 100 / 96 / **33** |
| D3S | 100 / 74 / 64 | 100 / 96 / 60 |
| D3L | 99 / 75 / 66 | 100 / 92 / 70 |

INFERENCE: the IRT model is a smooth Zipf-only curve fitted with items near the learner's edge. It mispredicts the
share known of common, low-level words, which is exactly what placement for advanced learners depends on. Both
stratified designs sample every band or level.

### 3.5 Mislabelling "knows the word"

#### Table 5. Mislabelling "knows the word" (budget snapshot, both skip settings averaged)

Columns per population: reported known-words count minus true "knows the word" count (% of pool) · learners whose whole reported interval lies above their true count · learners placed above their true "knows the word" level · credited words the learner does not know by meaning and reading.

| design | zh·en-L1 | zh·ja-L1 | ja·en-L1 | ja·zh-L1 |
|---|---|---|---|---|
| D0 | +4.4 · 19% · 8% · 25% | +28.6 · 96% · 28% · 46% | +2.1 · 9% · 4% · 17% | +15.9 · 70% · 19% · 28% |
| D1 | +6.1 · 22% · 4% · 27% | +27.1 · 91% · 22% · 53% | -0.4 · 3% · 3% · 20% | +16.6 · 69% · 13% · 35% |
| D1S | +3.6 · 12% · 14% · 27% | +29.7 · 92% · 34% · 49% | +1.2 · 9% · 8% · 19% | +15.9 · 59% · 26% · 31% |
| D1L | +2.8 · 9% · 35% · 19% | +27.7 · 73% · 51% · 35% | +0.2 · 7% · 22% · 16% | +14.2 · 44% · 34% · 28% |
| D2 | +0.2 · 1% · 0% · 6% | +0.1 · 3% · 1% · 12% | -3.7 · 0% · 0% · 5% | +0.8 · 4% · 1% · 10% |
| D3 | +0.4 · 2% · 0% · 7% | +0.1 · 3% · 0% · 13% | -4.2 · 0% · 0% · 8% | +1.2 · 5% · 1% · 9% |
| D4 | -0.1 · 2% · 0% · 18% | +0.9 · 5% · 0% · 39% | -4.4 · 0% · 0% · 13% | +1.2 · 7% · 1% · 24% |
| D3S | +0.5 · 4% · 8% · 8% | +0.1 · 4% · 6% · 12% | +0.0 · 4% · 5% · 9% | +0.2 · 6% · 6% · 9% |
| D3L | -0.2 · 3% · 17% · 5% | -0.4 · 3% · 19% · 7% | -1.3 · 4% · 13% · 7% | -1.2 · 5% · 13% · 8% |

#### Table 5b. Credited words that are lucky guesses (not known even by meaning), by skip setting

| design | zh·en-L1 s=0.3 / 0.7 | zh·ja-L1 s=0.3 / 0.7 | ja·en-L1 s=0.3 / 0.7 | ja·zh-L1 s=0.3 / 0.7 |
|---|---|---|---|---|
| D0 | 20% / 10% | 8% / 4% | 17% / 8% | 9% / 4% |
| D1 | 19% / 9% | 10% / 5% | 18% / 10% | 10% / 5% |
| D1S | 22% / 10% | 9% / 4% | 20% / 10% | 10% / 4% |
| D1L | 13% / 6% | 6% / 3% | 15% / 8% | 9% / 4% |
| D2 | 6% / 2% | 4% / 2% | 6% / 2% | 3% / 1% |
| D3 | 8% / 2% | 4% / 2% | 10% / 4% | 6% / 2% |
| D4 | 13% / 6% | 7% / 4% | 13% / 6% | 8% / 3% |
| D3S | 9% / 3% | 4% / 2% | 12% / 5% | 8% / 3% |
| D3L | 5% / 2% | 3% / 1% | 9% / 4% | 6% / 2% |

Credited lucky guesses depend mostly on how often learners use "I don't know". For English-L1 learners with skip-if-unknown 0.3,
13–22% of the words a meaning-only design credits are not known at all; with the conditional reading (D3, D3S) the
figure is 8–12%.

### 3.6 Stopping rules

The rule: stop at the first checkpoint, after at least 20 items, where every reported 90% half-width is at most
h × pool size; otherwise stop at the cap. The table shows mean items per population (share stopped before the cap);
the right-hand columns pool all populations.

| rule | design | zh·en | zh·ja | ja·en | ja·zh | mean items | stopped early | minutes (measured) | meaning MAE / cover | m+r MAE / cover | place m+r ±1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| h 10%, cap 40 / 60 | D1 | 38 (16%) | 39 (13%) | 38 (19%) | 39 (12%) | 38 | 15% | 3.3 | 5.5 / 91% | — | 80 |
| | D1S | 40 (2%) | 40 (0%) | 40 (1%) | 40 (0%) | 40 | 1% | 3.4 | 6.7 / 88% | — | 78 |
| | D3 | 57 (15%) | 60 (0%) | 55 (21%) | 60 (1%) | 58 | 9% | 5.0 | 5.5 / 91% | 5.0 / 93% | 73 |
| | D3S | 59 (7%) | 60 (0%) | 59 (7%) | 60 (0%) | 60 | 4% | 5.1 | 6.5 / 89% | 5.9 / 90% | 83 |
| h 12%, cap 40 / 60 | D1 | 34 (52%) | 35 (42%) | 34 (56%) | 35 (41%) | 35 | 48% | 3.0 | 5.6 / 91% | — | 79 |
| | D1S | 39 (16%) | 40 (1%) | 39 (9%) | 40 (0%) | 40 | 7% | 3.4 | 6.8 / 88% | — | 78 |
| | D3 | 52 (37%) | 60 (2%) | 48 (53%) | 58 (21%) | 54 | 28% | 4.6 | 5.5 / 91% | 5.1 / 93% | 73 |
| | D3S | 56 (22%) | 60 (0%) | 56 (21%) | 60 (0%) | 58 | 11% | 5.0 | 6.6 / 89% | 5.9 / 90% | 83 |
| h 10%, cap 60 / 90 | D1 | 51 (45%) | 53 (35%) | 50 (48%) | 53 (35%) | 52 | 41% | 4.4 | 4.9 / 91% | — | 80 |
| | D3 | 77 (43%) | 90 (3%) | 72 (60%) | 86 (24%) | 81 | 33% | 6.9 | 4.7 / 91% | 4.4 / 92% | 74 |
| | D3S | 83 (28%) | 90 (0%) | 83 (30%) | 90 (3%) | 87 | 15% | 7.4 | 5.4 / 88% | 4.9 / 89% | 84 |

Stopping early costs no coverage: the half-width is honest, so stopping on it does not bias anything. But cognate
learners almost never stop early. They know many words, and a large count carries a large uncertainty in words.
INFERENCE: a rule on relative precision, or on how certain the placement is, would stop them sooner; neither was
simulated. Full tables, including h = 8%, are in `out/tables_main.md`.

### 3.7 First vs second model for "knows the word" (D2i–D4i vs D2–D4)

My first model-based version fitted P(meaning and reading | z) as an independent curve, updated only by reading
answers. When reading answers were few, that curve fell back to its prior and could exceed the meaning curve:

| design | m+r MAE / coverage, zh·en | zh·ja | ja·en | ja·zh | bias range |
|---|---|---|---|---|---|
| D3i (first) | 12.2 / 90% | 6.3 / 78% | 7.2 / 91% | 5.2 / 85% | −2.6..+8.7 |
| D3 (ρ model) | 4.2 / 96% | 5.2 / 94% | 5.6 / 85% | 5.1 / 93% | −4.4..+2.0 |

Lesson for the spec (INFERENCE): never estimate "knows the word" on its own. Estimate P(reading | meaning) and
multiply. The design-based pair estimator does this implicitly, because a reading item exists only after a correct
meaning answer.

## 4. Sensitivity (ESTIMATE; 300 learners per population; budget snapshot)

**Word-difficulty noise σ_ε = 0.6 and 1.8** (frequency explains more or less of difficulty; σ_ε = 1.8 matches the
owner's slope best). The conclusions do not change. Compared with the main run at skip 0.7, MAE moves by at most about
±0.7 points and coverage stays 85–97%. At σ_ε = 1.8: D1 meaning MAE 5.0–5.5 with 89–95% coverage at 40 items; D3 meaning+reading MAE 4.4–5.1 with
90–97% coverage; D3S 5.1–6.5 with 87–92%. Tables: `out/tables_eps06.md`, `out/tables_eps18.md`.

**Partial reading knowledge** (a learner who knows the meaning but not the reading skips half as often and guesses
the reading right 40% of the time). The meaning-and-reading count is now biased up for cognate learners: +2.4..+3.8%
of the pool for D2, D3 and D3S. Credited words that lack the reading rise to 11–21% (zh·ja-L1: 20–21%). Coverage
falls to 85–90%. English-L1 learners are barely affected. INFERENCE: reading distractors one sound apart limit this;
the size of the effect is unknown until real data shows how often a correct meaning answer is followed by a correct
reading for words whose reading the learner later fails. Table: `out/tables_partial.md`.

**Exam level matters more beyond frequency** (`gamma25`: exam-orientation γ ~ U(0, 2.5) instead of U(0, 1)). Counts
are unaffected. Placement from Zipf bands collapses:

| design | zh·en: place m exact / ±1, level-share MAE | ja·en: place m exact / ±1, level-share MAE | place m+r ±1 zh / ja |
|---|---|---|---|
| D0 | 34 / 43, 17.4 pts | 55 / 66, 15.0 pts | 67 / 75 (meaning vs m+r) |
| D1 | 29 / 36, 20.2 | 48 / 59, 16.3 | 60 / 68 |
| D1S | 38 / 46, 17.1 | 55 / 67, 15.0 | 69 / 76 |
| D1L (level strata) | 57 / **88**, 7.7 | 72 / **92**, 8.3 | 65 / 87 |
| D3 | — | — | 52 / 64 |
| D3S | — | — | 62 / 74 |
| D3L (level strata) | — | — | **80 / 91** |

With level strata, D3L still overplaces 18–23% of learners on "knows the word" in this run. Tables:
`out/tables_gamma25.md`.

## 5. Conclusions for the synthesis stage

All from simulation (ESTIMATE) unless marked.

1. **Length and time.** For zh and ja, about 60 items (about 41 meaning and 19 reading) take about 5.1 minutes
   measured, or 5.7 minutes at the brief's 6 s / 5 s. English, meaning only: 40 items, about 3.4 minutes. Precision
   at those lengths is about ±10–13% of the check pool, about ±330–470 words. The report should show a range, never a
   single number. That matches ADR-051's honesty rules.
2. **Stopping rule.** Use a cap (60 zh/ja, 40 en) with an early exit when every reported 90% half-width is at most
   12% of the pool, after at least 40 items (zh/ja) or 20 (en). The early exit mostly serves beginners. A ±6% target
   is out of reach in under 90 items.
3. **Reading.** Ask it only after a correct meaning answer, and only on words with a real reading item. Hiragana-only
   words are already excluded (`task772_calibration_anchor_pool.sql:151-155`). INFERENCE: exclude katakana-only
   words too, since their reading is a script conversion. For ja this leaves 65% of the pool with reading items.
4. **Scoring.** The design-based D3S needs no new statistics: it is ADR-051 applied to meaning and to the pair. It
   is unbiased and honestly covered in every population tried, and it is robust to the curve's shape (cognate
   floors, loanwords). The model-based D3 is worth about 10–20% lower error for the counts, but it biased up to
   −4.4% and placed advanced learners badly. Treat it as a later upgrade, once item difficulties can be fitted from
   real responses.
5. **Cognate learners.** A meaning-only test overstates "knows the word" by about 1,000 words for Japanese-L1
   learners of Chinese, and for most of them the whole interval sits above the truth. Reading is not optional for
   these learners. INFERENCE: the report should show meaning-known and word-known side by side, because the gap is
   itself useful ("you recognise 2,300 words' meanings; you can also read about 1,200 of them").
6. **Exam placement.** Report a level range or per-level shares with their uncertainty. Within one level is the best
   honest claim (80–86% in the base model for D3S). Before choosing band or level strata, measure from first-user
   data whether list words of a band are known more often than non-list words of the same band (S8). If they are,
   use level strata (D3L), or add the level as a covariate.
7. **Seeding practice.** Seed practice only with words answered right on every item asked. Even then, 7–13% of seeded
   words are not known as words (mostly guesses), up to 21% with partial reading knowledge, so store them as placement evidence
   (TASK-1065) and never as "rated known".

## 6. Derivations used by the scoring

Notation for one word in one stratum: K_m = P(knows meaning), K_mr = P(knows meaning and reading), q = P(skip | not
known), g = (1 − q)/4 = P(correct guess | not known) for either item type.

**Pair estimator for "knows the word" (design-based, D3S/D3L).** The reading item is shown only after a correct
meaning answer. With pc = "meaning right and reading right" and prw = "meaning right and reading answered wrong (not
skipped)":

    P(pc)  = K_mr + (K_m − K_mr)·g + (1 − K_m)·g·g
    P(prw) = 3g·[ (K_m − K_mr) + (1 − K_m)·g ]
    ⇒ E[pc − prw/3] = K_mr        (for every q)

For a word with no reading item, the pair outcome is the meaning outcome (pc = right, prw = wrong), and
E[c − w/3] = K_m = K_mr. So K̂_mr = (pc − prw/3)/n per stratum is the ADR-051 estimator applied to pairs, with the same
variance formula. It assumes a learner who does not know a reading guesses it as often as one who does not know the
meaning; the `partial` sensitivity run breaks that assumption on purpose. If the learner can read a word whose meaning
they do not know (ω > 0), the estimator is biased up by P(not M)·g·P(R | not M), at most a few points (§4).

**Reading likelihood after a correct meaning answer (model-based, D2–D4).** With K_m from the meaning curve (posterior
mean, frozen when the item is answered), ρ = P(reading | meaning) and base = K_m + (1 − K_m)·g:

    P(meaning right, reading right) = K_m·ρ·(1 − g) + g·base
    P(meaning right, reading not right) ∝ base − K_m·ρ

A reading answer after a wrong or skipped meaning answer carries no information about ρ under this model (D2 asks
those reading items anyway; D4 asks half of them).

**Meaning likelihood.** P(right) = g + (1 − g)·K(z), P(not right) ∝ (1 − g)·(1 − K(z)); skip and wrong differ only by
factors that do not depend on the curve, so q enters only through g (plug-in q̂ = (skips + ½)/(skips + 4/3·wrongs + 1)).

## 7. Queries run (read-only SELECTs on project kpfqrjtfxmujzolwsvdq, 2026-11-18)

1. Latency by mode/language/outcome (MEASURED latencies in §2.4):

       SELECT s.mode, s.word_language_id,
         CASE WHEN r.is_correct THEN 'correct' WHEN r.chosen_sense_id IS NULL THEN 'skip' ELSE 'wrong' END AS outcome,
         count(*) n, round(avg(least(r.latency_ms, 30000))) AS mean_capped30s,
         percentile_cont(0.5) within group (order by r.latency_ms) AS p50,
         sum(CASE WHEN r.latency_ms > 30000 THEN 1 ELSE 0 END) AS over30s,
         left(min(r.user_id::text),8) AS u_min, left(max(r.user_id::text),8) AS u_max,
         min(r.answered_at)::date d0, max(r.answered_at)::date d1
       FROM calibration_responses r JOIN calibration_sessions s ON s.id = r.session_id
       WHERE r.is_correct IS NOT NULL GROUP BY 1,2,3 ORDER BY 1,2,3;

   Output (ja = 3, zh = 1): definition/ja correct 93 answers mean 4,586 ms (median 3,113), skip 76 mean 4,335
   (3,240), wrong 37 mean 3,047 (2,512); pronunciation/ja correct 58 mean 3,591 (3,133), skip 40 mean 7,120 (4,970;
   2 over 30 s), wrong 1 3,705; definition/zh correct 11 mean 3,067 (median 436; 1 over 30 s), skip 14 mean 364,
   wrong 14 mean 386. Users: de6fd05b (ja, both modes), 110fb390 (zh, and 2 days of ja).

2. Pool membership (§2.1): `SELECT word_language_id, 'def_en', string_agg(DISTINCT vocab_id::text, ',') FROM
   calibration_anchor_pool WHERE word_language_id IN (1,3) AND definition_language_id = 2 AND has_embedding GROUP BY 1
   UNION ALL SELECT word_language_id, 'pron', string_agg(DISTINCT vocab_id::text, ',') FROM calibration_anchor_pool
   WHERE word_language_id IN (1,3) AND has_pronunciation GROUP BY 1;` → zh 3,682 / ja 3,263 definition-mode ids,
   zh 3,656 / ja 2,339 pronunciation ids (saved to `placement/sim/data/anchor_pool_ids.json`).

3. Pool counts by band: `SELECT word_language_id, definition_language_id, zipf_band, count(DISTINCT vocab_id) FILTER
   (WHERE has_embedding), count(DISTINCT vocab_id) FILTER (WHERE has_pronunciation) FROM calibration_anchor_pool WHERE
   word_language_id IN (1,3) AND definition_language_id = 2 GROUP BY 1,2,3;` → zh [316, 629, 756, 703, 672, 435, 171],
   ja [607, 437, 633, 665, 552, 288, 81] distinct lemmas per band (all senses; the frame N_b counts rank-1 lemmas).
   Pronunciation rows sit under the word's own language as definition language (zh 1/1, ja 3/3), not under English.

4. Latency percentiles: `SELECT s.mode, s.word_language_id, count(*), count(r.latency_ms), percentile_cont(0.25 / 0.5 /
   0.75 / 0.9) WITHIN GROUP (ORDER BY r.latency_ms), count(DISTINCT r.user_id) FROM calibration_responses r JOIN
   calibration_sessions s ON s.id = r.session_id WHERE r.is_correct IS NOT NULL GROUP BY 1,2;` → definition/ja 206
   answers, p25/p50/p75/p90 = 2,151 / 3,110 / 4,800 / 8,869 ms, 2 users; pronunciation/ja 99 answers, 2,572 / 3,615 /
   5,931 / 7,388 ms, 1 user; definition/zh 39 answers, p50 364 ms, 1 user.
5. Columns of `calibration_anchor_pool` from `information_schema.columns` (to write queries 2–3).
6. Distinct lemmas per (word language, definition language): zh 3,721 / 3,682 / 3,682 with an embedding for definition
   languages 1 / 2 / 3, and 3,656 with a pronunciation (under definition language 1); ja 3,263 for every definition
   language, and 2,339 with a pronunciation (under definition language 3).

## 8. Limitations and what I could not verify

- **The learner model is an assumption.** The cognate shares, κ, π, ν and ω, the τ distribution and the exam-level
  effect are invented, informed by the literature notes in `placement/research-literature.md` (cognate share: about
  half of frequent Japanese words are Sino-Japanese, about 70% of those isographic with Chinese, A9) and by one real
  learner's answers. Results are most trustworthy as comparisons between designs, least as absolute error levels.
- **The real-data anchor is n = 1.** The slope 1.05 per Zipf point and skip rate 0.75 come from the owner's own
  answers (178 meaning and 99 reading answers, ja). Reading latencies come from one user; zh latencies looked like
  test clicking and were not used. The wait after a wrong answer, before tapping on, is ASSUMED to be 1.5 s.
- **Distractor quality is not modelled.** A guess is assumed correct 25% of the time. Semantically close
  distractors (ADR-025) could make it lower; arguably-correct distractors could make it higher.
- **Pool.** dict.json is a read-only export: it misses 26 of 3,263 ja pool ids, and the frame subsample is random
  within each band (fixed seed). Exam-level matches use the same string rules as the report mock-ups. JLPT matching
  by reading may misassign homographs. Not verified against the live `dim_vocabulary`.
- **Not simulated:** retakes with disjoint items; exposure control beyond random choice within a bin; item
  difficulty recalibration; stopping on placement certainty; English (meaning only, which behaves like D1/D1S on its
  own pool of 3,754 words); learners who switch skip behaviour mid-test.
- **Research audit.** `placement/research-audit.md` did not exist when this ran, so latencies came from the
  live database (§2.4).
- **Runtime:** main run 747 s, rho rerun 1,417 s, sensitivity runs 91–287 s each, on 4 CPUs.

## 9. Files (all under the scratchpad's `placement/sim/`)

- `pool.py`: pool, reading-item and exam-level loader. `sim.py`: learner model, designs and scoring.
  `summarize.py`, `condense.py`: tables. `fit_owner.py`: real-data slope and skip fit. `run_sens.sh`: sensitivity
  runs. `data/anchor_pool_ids.json`: read-only pool ids.
- `out/tables_main.md` and `.json`: every population and design, every budget, stopping rule and ability group (main
  run merged with the rho rerun). `out/condensed_main.md`: the tables above. `out/tables_{eps06,eps18,partial,gamma25}.md`:
  sensitivity runs. `out/raw_*.json`: per-learner snapshots. `out/pool_stats.txt`, `out/fit_owner.txt`.
- Reproduce: `python3 -I sim.py SCRATCH OUT 500 main`, then `... 500 main_rho designs=D2,D3,D4`, then
  `python3 -I summarize.py OUT/raw_main.json OUT/tables_main.md OUT/raw_main_rho.json`.
