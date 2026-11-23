# Vocabulary placement — psychometric challenge of the draft design (TASK-1073, review stage)

Written 2026-11-18 by an independent psychometric reviewer, for the synthesis stage. It covers
`placement/draft-design.md` (all 1,727 lines read) and the four research reports. Nothing was written to the wiki, the
codebase or the database. No database queries were run: every data figure below comes from files already exported to
the scratchpad, or from SQL the research stage quoted.

**Labels.** MEASURED means read from code (file:line), from the research stage's quoted SQL output, or computed exactly
from the read-only exports. ESTIMATE means simulation or arithmetic on stated inputs. INFERENCE means reasoning that was not
tested.

## Verdict

The core v1 measurement design holds up. It combines adaptive band allocation, a reading item asked only after a right
meaning, and ADR-051's estimator applied to the meaning outcome and to the pair outcome. I re-implemented the draft's exact
rules (warm-up, allocation, probes, the per-word precision exit from 40 items, the cap at 60, 95% intervals) on the
simulation stage's learner model. Results: count bias −1.1..+0.4% of the pool, 95% coverage 93–96% in every population,
and early stopping adds no bias. The pair estimator is unbiased for any skip behaviour, and nothing is double counted
(details under "Checked and upheld").

**What does not hold up** is everything built on top of the counts:
- **(M1, blocker)** The estimated exam-level range of §5.3 cannot produce its advertised output. Its 95% lower bound is 0
  for 100% of simulated learners, so the copy never says "about HSK k" or "HSK a–b".
- **(M2)** The level claims rest on a third of each level's words, and on the same exchangeability assumption that ADR-054
  rejected.
- **(M3, M4)** The zh reading item tests tones on only 11% of words, and nothing validates the guessing assumption of the
  reading step.
- **(M5)** The meaning estimate pools two instruments that do not measure the same thing.
- **(M6, M7)** Several statements over-claim, including the "I don't know" copy.
- **(M9)** A latent conflict: the v2 IRT plan would invalidate the report's estimator.

Ship the counts. Remove or redesign the level line (and soften the zh "with tones" claim) before the synthesis stage
files the spec.

## Method (what I re-ran)

- `placement/review_psy/psy_sim.py` imports the simulation stage's learner model and pools (`placement/sim/sim.py`,
  `pool.py`) unmodified. It re-implements the draft's v1 exactly:
  - §6 warm-up and allocation; §3 probes (0.25, at most 3);
  - §7 precision exit, checked after every completed word from 40 items, `SD ≤ 0.073·N` for both counts, cap 60 with a
    due reading still asked;
  - §5.1 estimator with z = 1.96 and ADR-051's `lo/hi` and label rules (`ADR-051…md:40-50`);
  - §5.3 level range: frame list items × band, cumulative `D`, the variance with the Bernoulli term, and the lower/upper
    rule.
- It also records the cap-60 snapshot of the same learners, to compare the early stop with a fixed length.
- Runs: 500 learners per population × 8 populations (`main.json`). Sensitivity runs at 300 per population: `partial=1`,
  `gamma_max=2.5`, `sig_eps=1.8`. Variants: `r_min_top=6/10` (forced items in the three most common bands) and
  `r_ja_full=1` (every non-kana ja word has a reading item).
- My reimplementation reproduces the simulation stage's point-placement accuracy: within one level for 79/78/84/85% against
  80/80/84/86% in [SIM Table 4]; zh by ability 100/74/60%, ja 100/96/59%, as [SIM §3.4].
- Outputs: `placement/review_psy/main_stop.md`, `variants.md`, `sens.md`. Helpers: `analyse.py`, `variants.py`,
  `variants2.py`, `coverage2.py`, `v5_effect.py`.
- Reproduce from the scratchpad root (Python 3.13, standard library only, about 5 s per run):
  `python3 -I placement/review_psy/psy_sim.py "$PWD" placement/review_psy/main.json 500`, then
  `python3 -I placement/review_psy/analyse.py placement/review_psy/main.json stop`.

## Findings

### M1 — BLOCKER — §5.3 level range (also prose l.102-103, l.131-133; ADR-058 decision 6; PQ2; TASK-1086)

**Problem.** The displayed exam-level range never takes the forms the copy promises. The rule is
`lower = max ℓ: S_j − 1.96·sd(S_j) ≥ 0.80 ∀ j ≤ ℓ`, and that bound needs `sd(S_1) ≲ 0.05–0.10`. HSK 1 and 2 and JLPT N5 and
N4 frame words sit in bands 4–7 (MEASURED, `sim/out/pool_stats.txt`), where adaptive allocation puts only 2–4 items, since
answers there agree. An all-correct band with n = 2 has a Jeffreys SD of 0.38, and with n = 4 an SD of 0.23 (ESTIMATE,
§5.1 formula). Simulation results (ESTIMATE, draft rules at the draft stop):

| pop | lower = 0 | lower = 0 when true placement ≥ 2 | copy "k" / "a–b" / "at most k" / "not yet" | point rule ±1, all / true ≥ 1 |
|---|---|---|---|---|
| zh·en-L1 | 100% | 100% (n = 404) | 0 / 0 / 56 / 44% | 79% / — |
| zh·ja-L1 | 100% | 100% (n = 394) | 0 / 0 / 57 / 43% | 78% / — |
| ja·en-L1 | 100% | 100% (n = 309) | 0 / 0 / 42 / 58% | 84% / — |
| ja·zh-L1 | 100% | 100% (n = 290) | 0 / 0 / 50 / 50% | 85% / — |
| zh pooled | | | | 51% among true ≥ 1 |
| ja pooled | | | | 56% among true ≥ 1 |

- **An advanced learner gets the ceiling copy.** For a zh learner who knows nearly everything, the estimate is
  `S_1 = 0.995` with `sd 0.162`, so `lower = 0`. The copy then reads "Up to HSK {upper} at most" (`main.json`).
- **The robustness checks fail as well.** The result holds in the `partial`, `gamma25` and `eps18` runs (`sens.md`). It
  also holds when 6 or 10 items are forced into each of the three most common bands: lower = 0 for 84–93% of learners
  with true placement ≥ 2, and the m+r half-width widens to ±21.8–24.0% of the pool. It holds with a monotone,
  frequency-ordered pooled lower bound too: a lower bound ≥ 1 for only 3–10% (`variants.md`).
- **The "about 4 learners in 5" figure measures something else.** It is the point rule `S_ℓ ≥ 0.80`, not the displayed
  range. It is carried by beginners: 58% of simulated zh learners and 67% of ja learners have a true placement of 0 and
  are placed trivially. For learners with true placement ≥ 1, the point rule is within one level for 51% (zh) and 56% (ja).
- **Under `gamma25`, even the one-sided ceiling fails.** It contains the truth for only 85–93% of learners.

**Correction.**
1. Remove the estimated level range from v1. This covers the result screen, the goal card, ADR-058 decision 6, PQ2,
   TASK-1086 and `result.level`. The goal card keeps ADR-054's measured buckets.
2. Delete "right within one level for about 4 learners in 5".
3. If the owner wants a level output, open a redesign task with an acceptance criterion on the displayed copy. Example: of
   learners whose true placement is ≥ 2, at least 50% get a lower bound ≥ 1, and the range contains the truth for at least
   90%. Candidates are level-targeted strata around a stated goal level (D3L), or a longer optional "level check".
4. Extend TASK-1087 (V0) to assert the distribution of displayed copy cases, not only the point rule.
5. The only statement this design supports today is a one-sided ceiling, "not yet most words of HSK {upper+1}". It
   contained the truth for 96–99% of learners in the base model, but it is weak (mean upper = true + 2 levels for zh
   intermediates) and fails S8 (85–93% under `gamma25`).

**Evidence.** `placement/review_psy/main_stop.md` (tables "Level range…" and "by true m+r placement"), `variants.md`,
`sens.md`. Draft §5.3 l.417-435. ESTIMATE.

### M2 — MAJOR — Exam-level claims rest on a third of each level and on the assumption ADR-054 rejected (§5.3, §8, ADR-058 decision 6)

**Problem.**
- **Coverage (MEASURED).** The check pool holds 32/33/33/29/32/22/9% of HSK 2025 levels 1/2/3/4/5/6/7–9, and 38/34/32/13/17%
  of JLPT N5–N1 ([SIM §2.1]). I also computed this from `kr/db_export/zh_vocab.tsv` and the live pool ids in
  `sim/data/anchor_pool_ids.json` (`coverage2.py`). The HSK 1–5 words that are in the dictionary but not in the pool
  outnumber the in-pool ones by 1.7–2.0 to 1 (for example, HSK 4: 604 against 298).
- **The in-pool words are more frequent (MEASURED).** Median Zipf, in pool vs in the dictionary but not the pool: HSK 3 5.16
  vs 4.78, HSK 4 5.08 vs 4.67, HSK 5 4.89 vs 4.52.
- **The frame-based share over-states the level.** I took each simulated learner's true band shares and reweighted to the
  whole level's band mix. Even if words within a band were exchangeable, the frame-based share over-states HSK ≤ 3–7 by
  +2.1 to +3.4 points on average (up to +7.5). That changes the learner's true placement for 299 of 2,000 zh learners
  (ESTIMATE).
- **Within-band exchangeability is false, so the real gap is larger.** ADR-051 F8 (`knowledge-report.tech.md:61`): frame
  lemmas appear in a test transcript 98.3% of the time, against 22.0% for non-frame lemmas of the same Zipf (INFERENCE).
- **The draft states a broader claim than it measures.** "Most words up to about HSK 3–4" (prose l.102-103, §8 l.546) is a
  claim about the exam level; what is measured is the frame subset.
- **ADR-054 already rejected the same estimate.** It rejected "Estimated coverage percentage in v1: its error is dominated
  by an untestable exchangeability assumption, so it cannot honestly carry a 95% label"
  (`ADR-054-exam-word-lists-in-storage.md:117-118`). The level range is that same §2.8a estimate with 95% bounds,
  thresholded at 80%. Calling it "coarser" does not remove the assumption.
- **V5 cannot test the frame-vs-non-frame part.** It only sees frame words.

**Correction.**
- Keep ADR-054's v1 stance; this is the same action as M1.
- If a level statement returns later:
  - name the subset in the copy ("of the 290 HSK 4 words the check draws from");
  - have ADR-058 explicitly revise ADR-054's rationale;
  - state that V5 tests only list vs non-list words within the frame, not frame vs non-frame words.
- The zh pool refresh (TASK-1063) changes the coverage, so any level claim must be re-validated after it.

**Evidence.** `coverage2.py` output (in this file); `ADR-054…md:25-33, 117-118`; `knowledge-report.tech.md:61, 369-385`.

### M3 — MAJOR — zh reading items test tone on only about 11% of words, so "knows the word" mixes two constructs (§2 rules 4 and 6, prose l.129-130, §8 l.534, §16 l.798, PQ3, PQ19, V6)

**Problem.** Rule 4 includes a tone-only foil only where one is cached: 433 of 3,969 zh anchors, 10.9%, against 519 of
30,929 foils overall (MEASURED, [AUD §2.4, A.6]). Every other served foil differs in its segments.
- **Most tone-ignorant learners are credited in full.** Take a learner who knows a word's syllables but none of its tones.
  On 89% of items they eliminate the foils and are scored right. On 11% they choose between two options. The estimator
  then credits them `1 − f + f/3 = 0.93` of a "known reading" (or 0.89 if they skip when torn), with f = 0.109 (ESTIMATE,
  §5.1 algebra). The stated construct ("Choose the pinyin (with tones)"; "a reading that is right except for its tone is a
  wrong reading") implies 0.
- **The guessing floor is also violated.** On the 11% of items, a segment-knower is at 1/2, not 1/4, so the reading step's
  r = 1/3 correction under-corrects (the `partial` mechanism).
- **The tone diagnostic is almost never observable.** "Pinyin right, tone not yet" (PQ19, V6) can only be seen on that 11%,
  at a rate of about f/2 = 5.5% of tone-unknown words. It therefore under-counts the state about 18-fold, and the count is
  not comparable across learners.
- **The literature says this state is common.** Advanced learners fail to reject tone-only mismatches even for words whose
  tones they identified ([LIT A8-50]).

**Correction.**
- In v1, make the zh reading estimand uniform: **exclude tone-only foils from scored reading items**.
- Word the copy and ADR-058 as "recognised the word's pinyin (tones not tested)", and drop "(with tones)".
- Measure tone separately with **unscored tone probes** on anchors that have a cached tone-only foil: a 2-option item (key
  vs tone-only foil) with its own 1/2 guess correction, scored pooled, at most 3 per test.
- Score tone per word only after PQ3 approves generated tone variants for every item.
- Re-word V6 accordingly.

**Evidence.** `research-audit.md:384, 394, 705-719`; draft l.270-280, 129-130, 534, 798; `research-literature.md:636-639`
(B4-17, A8-50).

### M4 — MAJOR — No validation covers the headline's key assumption: the reading-step guessing floor (§20, §5.1 "Known biases")

**Problem.**
- **What the headline rests on.** The m+r headline is unbiased only if a learner who knows a meaning but not the reading
  picks the right reading 1 time in 4 among the non-skipped answers. That is the 3:1 wrong:right ratio behind `prw/3`.
- **The real foils invite partial knowledge.** The foils are one sound away (ふね against ふく, やね, ふた; 知道 against
  zhī yào, zhì zào), so partial knowledge and character-based elimination are the expected case.
- **What happens when partial knowledge is present.** In the `partial` run my reimplementation gives m+r bias +4.0%
  (zh·ja) and +2.8% (ja·zh) of the pool, with coverage 92% (ESTIMATE, `sens.md`). Partial tone knowledge (M3) adds to it.
- **No V row measures it.** V3 checks only the meaning items. V4 measures reading after a missed meaning (a different
  term). V6 is descriptive.

**Correction.** Add a validation row, "reading credit", with this design:
1. Take a random sample of words credited m+r: about 3 per placement, or the first reading drill on those words.
2. Re-ask the reading later with a disjoint foil set (the cache holds up to 8 foils, so two disjoint sets of 3 exist),
   or record first-try accuracy in reading practice.
3. Estimate the false-credit rate and the empirical right:wrong ratio among unknown readings.
4. If the implied guess rate is above 0.25 + 0.05, replace r = 1/3 for readings with the estimated value, and record the
   change in an ADR revision.

Until then, label the m+r range "upper-side if readings can be partly guessed".

**Evidence.** `research-audit.md:384-389`; `research-simulation.md:437-442`; draft §20 l.876-886.

### M5 — MAJOR — The meaning sample A_m pools two non-equivalent instruments, contrary to ADR-051 (§5.1 l.355-358, §9, V1, TASK-1079)

**Problem.** A_m pools open-ended check meaning answers with placement meaning items, but the two items differ:
- **The check shows the reading.** Check items display the reading under the word: `calibration_build_items` returns
  `pronunciation` in definition mode (`migrations/calibration_distractor_cache_packed.sql:345-346`), and the page renders
  it (`static/js/pages/calibration.js:242-243`). The draft's own E3 confirms this, and I re-read it.
- **The check keeps the cross-CJK `headword；` prefix.** That prefix makes 13.3% (zh/ja) and 13.5% (ja/zh) of items
  answerable by string matching ([AUD §2.4]). TASK-1091, which would strip it, is blocked.
- **Placement items differ on both counts.** They hide the reading and strip the prefix.
- **The literature says this matters.** A reading shown with a meaning item changes what is measured and who scores
  higher ([LIT B4-15, A8-49]).
- **ADR-051 rejects this kind of pooling.** It rejects pooling "instruments of different difficulty"
  (`ADR-051…md:78`).

Consequences:
- **The meaning range moves with history.** On the result screen and in the report, it shifts with the learner's past mix
  of instruments.
- **The display guard is set off.** It binds whenever check answers sit in A_m (draft l.392-393).
- **V1 is confounded.** V1 compares a placement with the owner's 172 check answers, which all have the reading shown, so
  agreement or disagreement mixes the mode effect with error.

**Correction.**
- Store an instrument version on each response (`item_kind`, or a new `instrument` tag: reading shown or hidden, prefix
  stripped or not).
- The placement result uses placement items only. The report pools only same-instrument answers, or pools after a new task
  removes the reading line from the check's meaning items (together with TASK-1091), counting answers recorded after that
  date.
- Turn V1 into an explicit mode-effect check: the difference between the two instruments on disjoint words, with its SD.

**Evidence.** As cited; draft l.203, 355-358, 879.

### M6 — MAJOR — "I don't know" copy claims guess-neutrality that informed guessing contradicts (prose l.79-80, l.119-120; §5.2 l.410-413; §8 l.532-533)

**Problem.**
- **The neutrality result holds only for blind guesses.** "A guess does not change the result on average" and "guessing
  does not inflate it" are true under the know-or-guess model, where an unknown item is a blind 1-in-4 guess.
- **The literature says guesses are informed.** Real guesses are more often informed than not, and an IDK option
  suppresses partial knowledge (Zhang 2013, N = 150; Stoeckel et al. 2019, N = 200, where bilingual + IDK correlated
  r = .77 with meaning recall against .88–.91 for the other variants) ([LIT A2-13, A2-15]).
- **The instruction moves the result down.** Telling learners to choose IDK "to make the result more precise" lowers the
  expected result of a compliant learner relative to an otherwise identical guesser. That makes the result depend on
  test-taking style.
- **ADR-051 already treats skips as hiding knowledge.** It calls the figure lower-side if skips hide partial knowledge, and
  requires forced-choice probes (TASK-1061) to measure that before the range is used in marketing
  (`ADR-051…md:51-54`). A placement shown in onboarding is close to that use. The draft adds reading probes but no
  meaning probes after IDK.

**Correction.**
- Use neutral copy: "If you have no idea, choose I don't know. If you think you know, answer." Remove the "does not change
  the result on average" and "which is true" claims.
- Add unscored meaning forced-choice probes after IDK (TASK-1061 style, about 0.15 of IDKs, at most 3 per test) to measure
  hidden partial knowledge.
- Report each learner's skip share in validation (V8 already plans the distribution).

**Evidence.** `research-literature.md:116-134`; `ADR-051…md:51-54`; draft lines cited.

### M7 — MAJOR — Over-claims in prose, ADR naming and result copy

**Problem.** Each claim below says more than four-option recognition supports (the evidence after each is ESTIMATE unless
noted):
- **"Words they really know"** (l.99), and ADR-058's title "'knows the word'…". The headline is four-option recognition of
  rank-1 meaning plus reading. Elsewhere the draft's own copy rule says "recognised, never 'know' alone" (§16).
- **"The gap between the two is the words they recognise only through the characters"** (l.100-101). The gap is a
  difference of two estimates, possibly from different samples (M5), and is shown with no interval. For English-L1 learners
  it consists of words whose reading they never learned or forgot (5–12% of known words, [SIM §3]), not character
  transfer.
- **"Beginners usually finish early"** (l.95). At the draft's stop, beginners stop early 62–64% of the time with English
  as L1, but only 1–4% with Chinese or Japanese as L1. Overall early stops are 28% (en-L1) and 0–2% (cognate L1s), not the
  11% of §7 l.523, which used checkpoints and a 20-item minimum (`main_stop.md`).
- **"Probes make it uninformative"** (l.319-320). At the draft rates, P(meaning was right | a reading item appears) is
  85–92%.
- **"The placement result and My vocabulary always agree"** (l.149-150). The result is frozen (§14), while My vocabulary
  updates with later answers.
- **The per-word "meaning only" count is mostly guesses for a guessing beginner.** For a beginner who rarely skips
  (q = 0.3, K_m ≈ 0.05), about 17% of asked words land in "meaning only" by lucky meaning guesses (arithmetic:
  (0.05 + 0.95·0.175)·0.8).

**Correction.**
- Rename ADR-058 to "…meaning-and-reading recognition…". Use "recognised the meaning and the reading of about X–Y" without
  "really know".
- Describe the gap as "words whose meaning you recognised but not the reading", with no cause attributed, and give the gap
  its own interval: on the same placement sample, `Var(K_m − K_mr)` follows from the joint multinomial.
- State early-stop behaviour per L1. Drop "uninformative" and say the reading item's appearance usually signals a right
  meaning.
- Say "matches My vocabulary on the day it was taken".
- Label the per-word counts "your answers (guesses included)", or show them only above a minimum number of words.

**Evidence.** As cited.

### M8 — MINOR — The display guard binds often and points the wrong way (§5.1 l.392-393)

**Problem.**
- **It binds far more often than the draft says.** The draft says it binds "only when A_m contains open-ended check
  answers". On placement-only samples the guard's lower end binds in 25% of zh·en and 37% of ja·en placements, and the
  upper end in 16% and 29% (ESTIMATE, `main.json`).
- **The cause is ordinary precision.** The m+r estimate is more precise than the meaning estimate (a lucky guess must
  survive two items), so `lo_mr > lo_m` whenever the two counts are close.
- **Capping the lower end throws information away.** Capping `lo_mr` at `lo_m` widens the headline downward by 3.2–3.8% of
  the pool when it binds.

**Correction.** Use the logically valid direction. Because T_m ≥ T_mr, set `lo_m := max(lo_m, lo_mr)` and
`hi_mr := min(hi_mr, hi_m)`; meaning coverage stays 94% in simulation. Correct the "binds only when…" sentence.

**Evidence.** The guard computation in this file's run (`main.json`).

### M9 — MAJOR (v2, latent) — The v2 IRT plan breaks the report's design-based estimator and is under-identified as written (§5.4 l.437-478, ADR-057 decision 5, TASK-1093)

**Problem.**
1. **v2's item selection conflicts with v1's estimator.** v2 picks items by "0.2-Zipf bin … randomesque among the top 5
   words" (l.469-471). Within-band inclusion probabilities are then no longer uniform. Yet §9 feeds the same answers to
   `knowledge_estimate.estimate_range` (ADR-051's per-band SRS estimator) for both the result and the report, so switching
   to v2 selection would bias the report silently. v2's own gate does not check this.
2. **The model is not identified as written.** θ_u ~ N(μ0, 1.5²) with "μ0 = population mean", while
   b_w = β0 + …: μ0 and β0 trade off. The same holds for μφ(L1 group) against γ0, plus the per-group means of ε_w.
3. **One skip rate is assumed for both item kinds.** A single g_u = (1 − s_u)/4 serves both steps. The owner's own skip
   rates are 0.75 for meaning items and 0.95 for reading items ([SIM §2.2]).
4. **The gate has a loophole.** "… or ≥ 500 placements per language" can pass with an English-L1 majority while the
   cognate L1 groups (the owner's target case) have few learners. That leaves β3 and μφ(group) weakly estimated.

**Correction.**
- Keep v1's sampling (uniform within band) when v2 scores. If v2 must select items, compute the report's estimate with
  Horvitz–Thompson weights from the stored selection probabilities, or use the bins as strata with known N.
- Fix μ0 = 0 and γ-group means = 0, or the intercepts.
- Use separate g_m,u and g_r,u.
- Gate per (language, L1 group) on exposures and on V2/V3 within the group.

**Evidence.** Draft lines cited; ADR-051 decision 3.

### M10 — MINOR — V4 compares a raw right rate with 0.25 and ignores "I don't know" (§20 V4 l.882)

**Problem.**
- **The chance rate is lower when learners skip.** Under skipping, chance is (1 − q)/4, not 0.25.
- **V4 would miss knowledge the simulation contains.** In my run the probes' raw right rate is 18.7–23.6%, below 0.25, so
  V4 would report no reading-only knowledge. The guess-corrected rate `(r − w/3)/n` is 7.6–13.2%, which is the ω
  knowledge the model actually contains (ESTIMATE).
- **The stated bias bound needs heavy skipping.** The per-band bias is `(1 − K_m)·g_m·P(R | ¬M)`. For a non-skipper, a raw
  upper bound of 0.40 allows up to about 0.05·(1 − K_m), roughly 4.5% of a band for a beginner, not "≤ ~2%".

**Correction.** Estimate ω̂ = (r − w/3)/n with a Jeffreys-type interval. Compute the implied per-band bias with each
learner's ĝ_m, and gate on that.

**Evidence.** `main.json` probe tallies (computed in this review).

### M11 — MINOR — V5's threshold is uncalibrated and passes when underpowered (§20 V5 l.883, TASK-1090)

**Problem.**
- **The threshold sits at the base model's value.** On the observed scale (within band, within learner,
  Woolf-weighted), the list effect is 0.54 logit (zh) and 0.35 (ja) in the base learner model, the world where the draft
  deems band strata fine. It is 0.90 and 0.76 under `gamma25`, and 0.17 and 0.00 with no exam effect (ESTIMATE,
  `v5_effect.py`). The 0.5-logit threshold sits at the zh base value.
- **The rule passes when evidence is missing.** "CI includes 0 → keep" accepts an underpowered test.
- **The test uses a different outcome.** V5 tests meaning outcomes; the level line uses m+r.

**Correction.** This is moot for v1 if M1 is accepted. Before reuse: calibrate the decision by simulating V5 at the
planned n (30 placements) under base and `gamma25`, use an equivalence rule (keep only if the upper CI bound < the
threshold), and test pair outcomes.

### M12 — MINOR — V2 cannot detect under-coverage at 10 learners (§20 V2 l.880)

**Problem.** "≥ 8 of 10 within |z| ≤ 1.96" passes with probability 0.82 when the true coverage is 85%, and 0.53 when it is
75% (binomial arithmetic, ESTIMATE).

**Correction.** Always estimate the variance inflation √(mean z²) with its CI from every retest pair. Apply it whenever its
lower CI bound is above 1, not only when the 8-of-10 rule fails.

### M13 — MINOR — The ja simulation figures describe a different instrument from the launch design (E8, E13, E14; [SIM §2.1])

**Problem.**
- **The simulation's premise.** It treated every ja word without a stored reading as reading-exempt (MR = M): 2,069 of
  3,175 had reading items (`research-simulation.md:99-104`). That makes 757 non-kana words count as known on meaning
  alone.
- **The draft's premise.** It does not serve such words, and launches ja only at ≥ 90% readiness.
- **With every non-kana ja word given a reading item**, the simulated results change (ESTIMATE, `jafull.json`):
  - ja·zh learners' true m+r share falls from 45% to 38% of the pool;
  - reading items per test rise from 18.4 to 22.1 (zh-L1) and from 13.0 to 15.7 (en-L1);
  - the meaning 95% half-width widens from ±16.2% to ±17.2%;
  - m+r precision is unchanged.

**Correction.** Re-run E13/E14 for ja on post-refresh readiness. TASK-1087 fixtures must use the launch readiness flags,
not today's.

### M14 — MINOR — The readiness gate checks the ready share, not whether ready words are representative (§2 l.282-290, PQ13)

**Problem.**
- **Some frame words are never sampled.** Up to 10% of the frame overall, and 20% of a band, can never be sampled, yet
  they stay in the denominator N_b.
- **The excluded words are not random.** Rule 3 (same syllable/mora count) newly excludes words that lack enough same-length
  foils, plausibly long words and chengyu. Its effect is unmeasured (draft l.1726). The stale ja pool rows (841) are not
  known to be random either.
- **So the estimate carries a coverage bias** of (1 − r_b)·(K_ready − K_unready) per band (INFERENCE).

**Correction.** Make the gate also compare ready with not-ready words on Zipf within band, length and list level, and
record the result. Alternatively, report the m+r count over the ready sub-frame with its own denominator.

### M15 — MINOR — The D* rule can drop the placement's own answers (§5.1 l.351-361, §9)

**Problem.**
- **The definition language is the client's choice.** It is sent by the client (`routes/calibration.py:58-63`), so a
  learner can have check answers in one definition language and a placement in another.
- **The rule then drops the placement.** A_m and A_p keep answers "with D*" (the definition language with the most
  answers). So `knowledge_calibration_inputs` at `finish()` can return the old instrument's bands and `pairs = null` for
  the placement just taken.

**Correction.** The placement result is computed for its own session's D. The report's D* rule prefers the D of the latest
completed placement in the window, or shows per-D results. Add a test case for this.

### M16 — MINOR — The placement feeds a mis-specified ability fit while telling learners to skip (§11 l.604-615)

**Problem.**
- **The fit treats a skip as a wrong guess.** `_fit_points` scores a skip as wrong (`services/calibration_service.py:439-448`),
  and `_fit_ability` fixes the floor at 0.25 (`:43`; [AUD §1.7]).
- **For a heavy skipper the misfit is large.** It moves the curve by 0.4–0.8 Zipf (MEASURED on one learner, [AUD §1.7]).
- **The placement makes it worse.** It adds about 41 meaning items per session to this fit, explicitly encourages IDK
  (M6), and calls the guarded rating writer at `finish()`.

**Correction.**
- Gate the rating writer from placements on OQ33.
- Alternatively, fit placement meaning items with the skip-aware likelihood the draft already writes down in §5.4: g =
  (1 − ŝ)/4, with skip and wrong both ∝ (1 − K).

## Checked and upheld (no finding)

- **v1 identifiability and stability with very few users.** The design-based estimator needs no item parameters and works
  for n = 1 learner. With the eligibility amendment (n ≥ 2 per band after a completed placement), 95% coverage at the
  draft stop is 93–96% for both counts in all four populations, and 92–96% in the sensitivity runs. The draft's TASK-1087
  check therefore passes under the simulation model.
- **Local dependence.** Each estimator uses one outcome per word: meaning → A_m; pair → A_p, scored as one polytomous
  outcome. BKT, the pooled ability fit and the new-word queue take meaning items only, and probes are excluded everywhere.
  There is no double counting in v1. The v2 joint likelihood is algebraically correct (I re-derived both cells).
- **Pair estimator.** `E[pc − prw/3] = K_mr` holds even when the meaning and reading skip rates differ, and even when a
  reading skip depends on whether the meaning was known or guessed. It needs only the 1:3 right:wrong ratio among
  unknown readings (that is M4's assumption).
- **The stopping rule does not bias.** Checking after each word from 40 items gives the same bias and coverage as a fixed
  length of 60 (−1.1 vs −0.9% of the pool for meaning in en-L1 populations; coverage within one point).
- **Response-adaptive allocation.** Per-band bias of K_b is at most 0.024 in absolute value at every true share level
  (`main_stop.md`), so the theoretical small-sample bias of data-dependent n_h is negligible here.
- **Meaning-first conditional reading.** It is the right choice for the owner's target case. The cost to heritage
  learners is acknowledged.

## Limitations

- **Every simulation figure inherits the simulation stage's learner model.** Its cognate rates, π, ν, ω and τ range are
  assumptions anchored on one learner. My reimplementation reproduces that stage's numbers; it does not validate the
  model.
- **English was not simulated (no en pool export).** The M1 level finding does not apply to English, which has no level
  line.
- **No live database query was run.** The coverage figures use the exported `zh_vocab.tsv` and the research stage's
  read-only pool id export (`sim/data/anchor_pool_ids.json`).
- **The tone figures in M3 are algebra on the measured 10.9% foil share.** The share of zh learners' known words whose
  tones are uncertain is not measured.
