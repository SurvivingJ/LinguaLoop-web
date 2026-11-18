---
title: Vocabulary placement — research, simulation and review record (2026-11-18)
type: evaluation
status: complete
last_updated: 2026-11-18
---

# Vocabulary placement — research, simulation and review record (2026-11-18)

This is the evidence behind [[features/vocab-placement]], [[features/vocab-placement.tech]],
[[decisions/ADR-057-adaptive-placement-with-conditional-reading]],
[[decisions/ADR-058-meaning-and-reading-recognition-pair-estimator]] and
[[decisions/ADR-059-placement-evidence-kind]]. It was produced by TASK-1073 (knowledge-report task list)
as a staged workflow on 2026-11-18:
1. four research stages: literature, products, code/data audit, simulation;
2. a design draft;
3. two independent reviews: psychometric (M1–M16) and learner-side (L1–L13);
4. synthesis.

No application code was written. The live database (Supabase `kpfqrjtfxmujzolwsvdq`) was read with
SELECT only. Users are named by the first 8 characters of their id.

**Labels.** MEASURED = read from code (file:line), a quoted read-only query, or a cited study.
ESTIMATE = simulation or arithmetic on stated inputs; simulation figures hold only for the learner model
of §4.2. INFERENCE = reasoning that was not tested.

**Owner decisions (fixed):**
1. Build on the adaptive vocabulary check.
2. No fake words, pseudowords or Yes/No self-report.
3. For Chinese and Japanese, test both the meaning and the reading of words; English is tested on
   meaning only.

**Working files.** Archived next to this page in
[`vocab-placement-research-2026-11-18/`](vocab-placement-research-2026-11-18/) (about 0.8 MB):
- `reports/`: the full research and review reports — `research-literature.md`, `research-products.md`,
  `research-audit.md`, `research-simulation.md`, `review-psychometrics.md`, `review-learner.md`.
  The draft design is not archived; §6 below records what each review finding changed in it.
- `sim/`: simulation scripts (`sim.py`, `pool.py`, `summarize.py`, `condense.py`, `fit_owner.py`,
  `run_sens.sh`), with the summary tables in `sim/out/` (`tables_*.md`, `condensed_*.md`, `pool_stats.txt`,
  `fit_owner.txt`).
- `review_psy/`: the psychometric review's re-runs (`psy_sim.py`, `analyse.py`, `variants.py`,
  `variants2.py`, `coverage2.py`, `v5_effect.py`; outputs `main_stop.md`, `sens.md`, `variants*.md`,
  `*.txt`). `review_learner/`: the learner review's re-runs (`learner_view.py`, `level_by_true.py`,
  `labels.py`, `short_cover.py`, `early_exit.py`, `floor_exit.py`, `compare_floor.py`, `place_by_len.py`,
  `place_designs.py`; outputs `*_out.txt`).
- `synth/`: synthesis re-runs (`len50.py` → `len50_out.txt`, `stop50.py` → `stop50_out.txt`).
- `scripts/skip_fit.py`, `info_calc.py`: the skip-rate fit and the 3PL information table.

**Not archived:** the raw per-learner outputs (`raw_*.json`, about 400 MB) and the inputs the scripts read
from the session scratchpad: `mock/data/dict.json` (word, Zipf and gloss export), `sim/data/anchor_pool_ids.json`
(live `calibration_anchor_pool` ids), the HSK 3.0 2025 and JLPT list files (ADR-054 sources) and the owner's
own answer export (`real_events.json`, personal data). All scripts are standard-library Python 3 run with
`python3 -I`. They hard-code the original scratchpad paths, so re-running them means re-creating those exports
with read-only SELECTs (`reports/research-simulation.md` lists the SQL) and editing the path constant.

---

## 1. Summary

- **The core design is sound.** Adaptive band-stratified selection, a reading item only after a right
  meaning, and ADR-051's estimator applied to the meaning outcome and to the meaning-and-reading pair
  (design "D3S") were unbiased (−1.1..+0.4% of the pool) with 95% coverage of 93–96% in every simulated
  population. The psychometric reviewer re-implemented the draft independently (ESTIMATE).
- **Precision is the binding limit.** A placement gives about ±14–17% of the check's pool at 95% after
  50 scored items (about 6 minutes at the measured pace). Results are usually labelled "Rough" (ESTIMATE).
- **Meaning-only tests mislabel cognate learners.** A meaning-only test over-states Japanese-L1 learners
  of Chinese by about 1,000 words (+27–30% of the pool). The conditional reading removes this (ESTIMATE).
- **The draft's exam-level estimate failed.** Its 95% lower bound was 0 for every simulated learner, and
  the point rule was within one level for only 3–41% of true HSK 2–5 learners. It was removed from v1
  (ESTIMATE).
- **The item bank has measurable flaws that favour cognate learners.** zh tones are tested on only 11%
  of items. 19% of ja kanji+kana reading items are solvable from visible kana. 10.8% of ja/zh meaning
  items are answerable by string matching after the draft's prefix strip (MEASURED).
- **The practice hand-off was broken for the target case.** Words with the meaning recognised but not
  the reading would not reach practice (MEASURED in code).

---

## 2. Annotated bibliography

Access: [OA] open copy, [PW] paywall (abstract free), [?] unclear. **Every source was checked through
search-engine abstracts and snippets only**: WebFetch could not reach publisher hosts in this session.
Numbers quoted from secondary summaries are marked "reported". Full texts should be checked before an
ADR cites a paper-specific figure.

### 2.1 Vocabulary size and levels tests

| # | Source | Finding | Use in the design |
|---|---|---|---|
| 1 | Nation & Beglar (2007), *The Language Teacher* 31(7) [?] | VST: four-option meaning recognition sampled by 1,000-word bands; raw score × constant | Closest template; guessing inflates a raw-score size |
| 2 | Beglar (2010), *Language Testing* 27(1) [PW] | Reported: 5 items per band give adequate whole-test reliability | Whole-test ≠ per-band precision |
| 3 | Webb, Sasao & Ballance (2017), *ITL* 168(1) [OA, host unreachable] | Updated VLT, 1K–5K levels; mastery per level (format from memory, unverified) | Per-level mastery needs many items per level |
| 4 | Stoeckel, McLean & Nation (2021), *SSLA* 43(1) [PW] | Meaning-recognition formats over-estimate (guessing, strategies) | Label the result "recognised" |
| 5 | Gyllstad, McLean & Stewart (2021), *Language Testing* 38(4) [PW] | Individual band estimates need ≥ 30 items per band | Per-level output cannot be measured directly in minutes |
| 6 | Gyllstad, Vilkaitė & Schmitt (2015), *ITL* 166(2) [OA record] | MC over-estimated size against an interview | Supports recognition labelling |
| 7 | McLean, Stewart & Batty (2020), *Language Testing* 37(3) [OA], N = 103 | Meaning recall predicts reading best; recognition weaker | Validate against later behaviour (V3) |
| 8 | Kremmel & Schmitt (2016), *LAQ* 13(4) [PW] | All formats carry error; MC defensible (figures unverified) | MC acceptable |
| 9 | Hashimoto (2021), *LAQ*; BYU thesis [OA], N = 403 | Rasch difficulty vs frequency r = 0.50 (0.31 when banded) | Frequency is a weak difficulty prior (v2 σ_δ wide) |
| 10 | Brysbaert et al. (2019), *BRM* 51 [OA] | Word prevalence predicts beyond frequency | Learn per-word difficulty from answers (v2) |
| 11 | Laufer & Ravenhorst-Kalovski (2010), *RFL* 22(1) [OA] | 4–5k / 8k families for 95% / 98% coverage (contested) | Background only |
| 12 | Gonzalez-Fernandez & Webb (2024), *SSLA* [OA preprint] | Secondary meanings as hard as new words | Rank-1 sense only |

### 2.2 Guessing, "I don't know", score correction

| # | Source | Finding | Use |
|---|---|---|---|
| 13 | Zhang (2013), *TESOL Quarterly* [PW], N = 150 | IDK reduced guessing but suppressed partial knowledge | Neutral IDK copy; `forced_guess` probes (V8) |
| 14 | Stoeckel, Bennett & McLean (2016), *TESOL Quarterly* 50(4) [?] | Learners use IDK differently, weakening validity | Store skip share; v2 per-person skip |
| 15 | Stoeckel et al. (2019), *System* 87 [PW], N = 200 | Bilingual + IDK r = .77 vs .88–.91 for other variants; guesses more often informed | Our format is bilingual + IDK: no neutrality claim (PSY M6) |
| 16 | Stewart (2014), *LAQ* 11; Stewart & White (2011), *TESOL Q* 45(2) [PW] | MC inflates size; VLT ~16–17/99 (reported), mostly for low scorers | Guess correction matters most for beginners |
| 17 | Holster & Lake (2016); Stewart, McLean & Kramer (2017), *LAQ* [PW] | Rasch fit does not detect guessing | Model the floor explicitly |
| 18 | Elgort (2013), *Language Testing* 30(2) [PW], N = 121 | Bilingual VST easier; cognates easier, less so at higher frequency | L1 × cognate term in v2 |

### 2.3 Computerised adaptive testing

| # | Source | Finding | Use |
|---|---|---|---|
| 19 | Linacre (2006), *RMT* 20(2) [OA] | Information P(1−P); targeting and SE | Stopping arithmetic |
| 20 | Babcock & Weiss (2012), *JCAT* [OA] | SE-threshold rule most studied (thresholds unverified) | Precision exit |
| 21 | Choi, Grady & Dodd (2010/11), *EPM* 70 [?] | Predicted SE reduction stop | Not used in v1 (cap is the real stop) |
| 22 | Bock & Mislevy (1982), *APM* 6 [PW] | EAP finite for all-correct/all-wrong patterns | v2 uses EAP |
| 23 | Georgiadou et al. (2007), *JTLA* 5 [OA]; Kingsbury & Zara (1989) | Randomesque exposure control | Not needed: uniform within-band draws |
| 24 | Mislevy & Wu (1996), ETS RR-96-30 [OA]; Lord (1974) | Omits scored wrong bias ability down | Skip-aware likelihood (§11, OQ33) |
| 25 | Han (2012), *PARE* [OA] | 3PL with c fixed at 1/k performs well; free c needs thousands | Floor fixed at 1/4 (1/2 for sound pairs) |

### 2.4 Item calibration with few users

| # | Source | Finding | Use |
|---|---|---|---|
| 26 | McCarthy et al. (2021), *EMNLP* [OA] | Feature-predicted difficulty works with ~500 takers, ~6 exposures per item | v2 gate (≥ 6 exposures) |
| 27 | Settles, LaFlair & Hagiwara (2020), *TACL* 8 [OA] | Difficulty from features instead of piloting | v2 item features |
| 28 | Pelánek (2016), *Computers & Education* [OA]; Pankiewicz (2020) | Elo beats proportion correct at small n | Possible online update |
| 29 | König, Spoden & Frey (2020), *APM* [OA] | Hierarchical 2PL priors; N ≈ 50 under limits | Shrinkage to features |
| 30 | Mislevy (1988), *APM* 12; De Boeck & Wilson (2004) [PW] | Explanatory IRT / LLTM | The form of v2 |

### 2.5 Dimensions of word knowledge; two items on one word

| # | Source | Finding | Use |
|---|---|---|---|
| 31 | Nation (2001/2013/2022), *Learning Vocabulary in Another Language* [PW] | Form, meaning, use × receptive/productive | Meaning and reading = two components |
| 32 | Henriksen (1999), *SSLA* 21(2) [PW] | Partial → precise knowledge | Close distractors push toward precise |
| 33 | Laufer & Goldstein (2004), *Language Learning* 54(3); Aviad-Levitzky et al. (2019), *LAQ* 16(3), N = 453 | CATSS: conditional multi-modality design; a word passed is not re-tested | Precedent for "reading only after a right meaning" |
| 34 | Webb (2005, 2007), *SSLA*, *Applied Linguistics* [PW] | Aspects develop at different rates | Two dimensions |
| 35 | González-Fernández & Schmitt (2020), *Applied Linguistics* 41(4) [OA], N = 144 | Components correlated but separable | Two correlated abilities in v2 |
| 36 | Milton & Hopkins (2006), *CMLR* 63(1) [?] | Aural and written sizes diverge | Form needs its own measure |
| 37 | Wainer, Bradlow & Wang (2007), *Testlet Response Theory* [PW] | Ignoring testlets overstates precision; score the bundle polytomously | Pair = one polytomous item |
| 38 | Tutz (1990), *BJMSP* 43; Hemker et al. (2001), *Psychometrika* 66 [OA] | Sequential (steps) model | Exactly the conditional pair |
| 39 | Bifactor / MIRT tutorial [OA]; mixed vocabulary evidence | Whether two scales are needed is empirical | Test on our data (v2) |

### 2.6 Japanese

| # | Source | Finding | Use |
|---|---|---|---|
| 40 | Imai, Akagi & Nakasono (2009), J-CAT [OA] | Operational Japanese CAT; distractors from learner errors | Error-based reading foils (PQ3) |
| 41 | Kano, TTBJ kanji diagnostic [OA] | Kanji meaning and reading as separate subtests | Separate dimensions |
| 42 | *New JLPT Guidebook* (2009) [OA] | 漢字読み item type (choose the kana reading) | Our ja reading item is exam-congruent |
| 43 | NINJAL SPOT paper (2024) [OA] | SPOT measures processing, not size | Not a model |
| 44 | Rothville (2024), *JER* 11(2) [OA] | Japanese VLT to 5,000 words, KR-21 = .98 | Closest Japanese levels test |
| 45 | Yamato, Tamaoka & Kayamoto (2016), KAKEN [OA] | Lexical test for non-kanji learners (details unverified) | Background |
| 46 | Matsunaga (1999), *Sekai no Nihongo Kyouiku* 9 [OA] | Chinese-L1 learners understood kanji text without Japanese readings | The owner's target case |
| 47 | Hu (2012); Tokuhiro; Hong Kong study [OA] | Chinese-L1 reading errors: vowel length, voicing, っ, ん | ja `sound_pair` probes; PQ3 |
| 48 | Zhao (2025), *IJAL* [PW]; *Applied Psycholinguistics* [PW] | Chinese-L1 learners lean on kanji form | Meaning via characters |

### 2.7 Chinese

| # | Source | Finding | Use |
|---|---|---|---|
| 49 | Zhang, Lin, Zhang & Choi (2017/2019), *LLJ* 47(3) [OA record] | Showing pinyin changes what a meaning item measures; heritage learners gain | No reading on meaning items; instruments not pooled (PSY M5) |
| 50 | Pelzl et al. (2019, 2021), *SSLA* [PW] | Advanced learners fail to reject tone-only mismatches | Tone is a separate sub-skill (PSY M3) |
| 51 | Japanese learners' tone difficulty, *Frontiers* (2024) [OA] | T3 > T2 > T1 = T4; T2/T3 confusion | `sound_pair` probe targets |
| 52 | Li (2026), *IJAL* [PW], N = 72 | Chinese phonological size test; gains and attrition | Retakes, re-placement |
| 53 | Qi (2025/2026), *IJAL* [PW] | Chinese VLT keyed to HSK 3.0 levels 4–6 | Level-keyed tests exist |
| 54 | CVPT [?], N = 170 / 354 | 100-item IRT test | Background |
| 55 | Zhou et al. (2019), BEA @ ACL [OA] | 3PL CAT with generated items (length reduction unverified) | Closest technical precedent |
| 56 | Chen & Hsu (2019), TOCFL-CAT [abstract] | > 30% fewer items for equal precision | Expected adaptivity gain |
| 57 | BLCU thesis (2012) [CNKI PW], N = 60 | Definition test; accuracy falls with frequency | Background |
| 58 | EdUHK (2025), *IJCLE* 17 [OA] | School multistage test | Simpler alternative (not chosen) |

### 2.8 Cross-language effects

| # | Source | Finding | Use |
|---|---|---|---|
| 59 | Matsushita et al. (2020), JKVC, *JJLT* 177 [OA abstract] | ~half of frequent Japanese words Sino-Japanese; ~70% isographic with Chinese | Cognate flag for v2 |
| 60 | Yu; Nagoya University; ANLP 2022 databases | Cross-CJK compound and homograph lists (availability unverified) | Possible cognate source |
| 61 | Machida (2001), *System* 29 [PW] | Meaning transfers through characters; non-Chinese learners pronounce kanji better | The asymmetry the pair exposes |
| 62 | Aichi University and others [OA] | ja-L1 errors on same-form near-synonyms | Close meaning distractors matter |
| 63 | Daulton (2008); Rogers, Webb & Nakata (2015) [PW/OA] | Loanword cognates easier (reverse direction) | Katakana words meaning-only |
| 64 | Jordan (2012); *Applied Linguistics Review* (2018) | Frequency predicts facility less well for cognates | Frequency × cognate interaction |

### 2.9 Reporting uncertainty

| # | Source | Finding | Use |
|---|---|---|---|
| 65 | van der Bles et al. (2020), *PNAS* 117(14) [OA] | Numeric ranges barely reduce trust; verbal hedges do | Show ranges, not hedges |
| 66 | Kay et al. (2016), *CHI* [OA] | Quantile dotplots work on mobile | Band/dot strip on the result |
| 67 | Zwick, Zapata-Rivera & Hegarty (2014), *Educational Assessment* 19(2) [PW]; Zenisky & Hambleton | Misconceptions about error are common; show bands | "How this works" text |

Excluded by owner decision (listed for completeness): LexTALE-type pseudoword tests for Chinese
(LEXTALE_CH, LexCHI, LexCH) and Japanese (LexJP), DET Yes/No items, and Meara checklists.

---

## 3. Product comparison

All web claims come from search extracts; no product page was opened. "M" = meaning, "R" = reading.

| Product | Lang | Placement | Length | M and R | Afterwards | Retakes / uncertainty |
|---|---|---|---|---|---|---|
| WaniKani | ja | none; no level skip | — | separate typed prompts, both required; kana-only vocab M only | starts at level 1 | reset down only |
| KameSame | ja | "placement test" lesson mode | self-paced | recall prompts | items burned | lessons only |
| Bunpro | ja | none for vocab; mark known | — | context-sentence vocab reviews | per-deck progress; JLPT mocks (2025) | bulk marking broken (users) |
| Renshuu | ja | "I know this" sets mastery, still quizzed later | — | separate facets per reading | mastery per term | flags can be undone |
| jpdb | ja | none; deck-state override | — | one self-graded card | coverage %; blacklist changes the denominator | self-report, loose |
| Migaku | ja, zh | none (own help page) | — | not tested | known-word count ("a proxy") | Known never auto-demoted |
| Kanshudo | ja | inferred mastery | — | per item | mastery level mapped to JLPT | revised by use |
| Hack Chinese | zh | questionnaire → "assumed known", spot-checked daily | ≤ 30 checks/day | self-graded; pinyin/tone then definition | separate "assumed known, unchecked" bar segment | intervals boosted when confirmed |
| Skritter | zh, ja | none; mark as learned | — | separate parts: writing, tone, reading, definition | per-part scheduling | tone prompts often switched off |
| Pleco | zh | none | — | separate test types and scorefiles; MC pinyin always matches syllable count | per-test scores | — |
| HelloChinese | zh | placement exists (no detail) | ? | ? | course level, not HSK | manual override by email |
| LingoDeer | ja, zh | unit "Test Out" | per unit | mixed | unit unlocked | retry |
| Duolingo | all | adaptive placement; partial credit added after over-placement | ~5–10 min | mixed | starting unit | "Jump here" |
| Duolingo English Test | en | adaptive Yes/No pseudowords (rejected format) | 15–18 items, 5 s each | M only | score report | feature-based difficulty, exposure control |
| Busuu | many | adaptive | "5 minutes" | mixed | "just a suggestion" | any time |
| LingQ | many | none | — | not tested | known-word thresholds | — |
| Anki | any | none | — | user's choice | deck stats | — |
| GoEast (web) | zh | 3PL IRT, Bayesian | ~20 items | M | size, HSK level, word list; no interval | — |
| HSKLord (web) | zh | adaptive, includes character→pinyin | 20 items | mixed into one score | highest level ≥ 60% | states its limits |
| GyanMirai (web) | ja | even sampling N5–N1 | ? | M | size; ~60% = core words | — |
| martindbp (blog) | zh | logistic model, self-reported HSK prior, entropy sampling | ? | M | P(known) per word | model-based |

Lessons adopted (INFERENCE):
- Score meaning and reading separately and report the joint "both" figure (WaniKani, Skritter, Pleco).
- Hide the other part during each prompt and reveal together (Skritter).
- Same syllable count in pinyin MC (Pleco).
- Seed placed words as "assumed known, to be checked" (Hack Chinese, Renshuu), never as permanently
  known (Migaku).
- Say plainly the result is an estimate and easy to redo (Busuu, Duolingo).
- Avoid threshold level verdicts (HSKLord's "≥ 60%"); our simulation confirms they mislead (E23).

No source measured any product's placement accuracy against later outcomes.

---

## 4. Code and data audit — measured facts

Read-only queries are quoted in full in `research-audit.md` (Appendix A) and `review-learner.md` §4.

| Area | Fact | Source |
|---|---|---|
| Selection | Round-robin over the least-served band, random within band; per-session exclusion only; any sense rank | `migrations/task772_calibration_anchor_pool.sql:186-257` |
| Item build | Meaning items carry `pronunciation`, rendered under the word | `migrations/calibration_distractor_cache_packed.sql:345-346`; `static/js/pages/calibration.js:243-244` |
| Reading foils | Levenshtein over a normalised reading; homophones excluded; same count preferred; 8 cached, 3 sampled; tone-marked pinyin / hiragana displayed | `migrations/calibration_pronunciation_mode.sql:86-270` |
| zh normaliser | 6,621 of 8,110 zh standard readings lack `(numbered)` → syllable count 0 | query in audit §1.3 |
| Storage per response | `chosen_sense_id NULL, is_correct false` for a skip; mode per session only | `migrations/task769_calibration_record_answer.sql:138` |
| Ending | Only `/end`; 74 of 79 sessions never ended; 1,005 of 1,349 rows unanswered prefetch | `routes/calibration.py:189-200`; `services/calibration_service.py:731-773` |
| Rating writer | Called at `/end` (wiki says it is not) | `services/calibration_service.py:764-772`; `wiki/features/calibration.md:122-126` |
| BKT | Definition mode only; Zipf step prior; slip 0.05, guess 0.25, transit 0.05; written on the anchor (gloss) row | `services/calibration_service.py:642-728`; live `bkt_update_word_test` |
| Ability fit | MLE of 0.25 + 0.75·σ(a(z − b)); a skip is a wrong answer; SE from a lookup; skip-aware refit moves it 0.4–0.8 Zipf for de6fd05b | `services/calibration_service.py:41-43, 340-448`; audit §1.7 |
| Readiness (paired) | zh 3,482 of 3,623 (96%; band 1 91%); ja 2,185 of 3,175 (69%; band 1 50%) | audit §2.1 |
| ja stale pool | 841 pool rows without a reading that `dim_word_senses` now has; 214 katakana-only lemmas in the reading pool | audit §2.2 |
| zh tone-only foils | 433 of 3,969 anchors (10.9%); 519 of 30,929 foils; 2,473 foils with another syllable count (8.0%) | audit A.6 |
| ja special-mora foils | 298 of 17,592 foils; 267 of 2,230 anchors (12.0%); ~4.3% of served items | review-learner Q3 |
| ja okurigana | 488 of 2,243 kanji+kana anchors; 55% of their foils eliminable; 199 with < 3 consistent; 91 (19%) fully solvable | review-learner Q2 |
| Cross-CJK keys | zh/ja: 3,623 of 3,623 `；` prefix. ja/zh: 693 `；`, 2,478 `——` (453 = lemma). After a `；`-only strip: zh/ja 1 residual; ja/zh 470 contain the lemma, 343 (10.8%) answerable by matching | review-learner Q4, Q5 (the audit's A.7 missed the `——` form) |
| Homograph foils | 0 zh, 0 ja reading foils share the anchor's lemma | review-learner Q8 |
| Live answers | 344 answers from 3 users; 110fb390 likely automated (median 364 ms); de6fd05b ja: 178 meaning (47% right, 43% skip, 10% wrong) and 99 reading (59/40/1); 6 words in both modes (3 both, 1 meaning only, 1 reading only, 1 neither) | audit §3 |
| Pace | de6fd05b gap between answers (≤ 60 s): meaning 6.57 s (median 5.03), reading 7.50 s (median 5.39); latency medians 3.4 / 3.6 s | review-learner Q1; audit §3.3 |
| Practice hand-off | A2 admits wrong/skipped only (`new_word_admission.py:648-655`); veto (`:660-673`); A1 thresholds (`constants.py:37-38`); supply gate on the exact sense (`:762-811`); intro-drill bypass (`:498-505`); ledger reads mode `definition` only (`:566-600`) | code read 2026-11-18 |
| Exercise supply | Gloss anchor sense with ≥ 3 active exercises: 0 (zh 3,623, ja 3,175); any sense: zh 3,386, ja 2,935; reading drill on some sense: 3,161 / 2,582; `dim_vocabulary.reading` empty for 3,682 zh pool words | review-learner Q6, Q7 |
| Intro drill | `reading = dim_vocabulary.reading or pronunciation` (`services/prestudy.py:185`); zh reading dropped without a numbered part (`services/intro_drill.py:238-251`) | code read 2026-11-18 |
| IRT module | 2PL exercise calibrator, no floor, no person estimate; 0 of 144,374 exercises calibrated | `services/irt/calibrator.py`; audit §4 |
| Size | Database 513,535,123 B; calibration tables ≈ 18.6 MB; response tuple ≈ 100 B | audit §5.1 |
| List coverage | Pool holds HSK 2025 L1 95/300, L2 67/202, L3 164/506, L4 290/1,015, L5 495/1,631, L6 372/1,809, L7–9 481/5,605; JLPT N5 274/718, N4 229/668, N3 686/2,140, N2 244/1,905, N1 460/2,699; unlisted 46% (zh) and 40% (ja) of pool words. In-pool vs dictionary-only median Zipf: HSK 3 5.16 vs 4.78, HSK 4 5.08 vs 4.67, HSK 5 4.89 vs 4.52 | `sim/out/pool_stats.txt`; `review_psy/coverage2.txt` |

---

## 5. Simulation

### 5.1 Designs

All designs used the check's four-option items and "I don't know". Design-based designs use the ADR-051
estimator per stratum; model-based designs use a grid posterior over a Zipf knowledge curve with a
cognate floor and a guess rate (1 − q̂)/4.

| id | items | reading items | estimator |
|---|---|---|---|
| D0 | fixed, 10 per band (today's check) | none | design-based |
| D1 | adaptive (IRT) | none | model-based |
| D1S | adaptive band-stratified | none | design-based |
| D1L | adaptive exam-level-stratified | none | design-based |
| D2 | adaptive (IRT) | after every meaning item | model-based |
| D3 | adaptive (IRT) | only after a right meaning | model-based |
| D4 | adaptive (IRT) | every second word | model-based |
| **D3S** | adaptive band-stratified | only after a right meaning | design-based (meaning and pair) |
| D3L | adaptive level-stratified | only after a right meaning | design-based |

### 5.2 Learner model (assumption; partly anchored on real data)

- **Word pools.** Real pools, subsampled to the frame sizes: zh 3,623 = [303, 617, 742, 691, 664, 435,
  171]; ja 3,175 = [577, 425, 621, 655, 537, 283, 77]. Reading items: zh 3,560, ja 2,069. The ja figure
  treats every word without a stored reading as exempt (see 5.6).
- **Per word.** Zipf; a difficulty residual ε ~ N(0, 1.2); an exam-level residual; a cognate flag per
  L1. Cognate rates are 0.55/0.30 for zh with ja-L1 and 0.65/0.45/0.20 for ja with zh-L1; katakana
  words are cognates for en-L1 at 0.80.
- **Per learner.**
  - study frontier τ ~ U(2.5, 7.0) Zipf;
  - slope ~ lognormal(1.6, 0.2);
  - exam orientation γ ~ U(0, 1);
  - skip-if-unknown s ~ N(0.3 or 0.7, 0.1);
  - cognate transfer κ, reading retention π, cognate reading ν, compositional reading ω, by profile.
- **Responses.** A known item is answered right; an unknown item is skipped with probability s,
  otherwise guessed at 1/4. The `partial` run lets a meaning-known, reading-unknown learner guess the
  reading at 0.40.
- **Real anchors (n = 1).** The owner's answers give a slope of 1.05 per Zipf point (0.70–1.55),
  skip-if-unknown 0.75 for meaning and 0.95 for reading (`sim/fit_owner.py`).
- **Scale.** 500 learners × 8 populations, all designs on the same learners. Sensitivity runs:
  `eps06`, `eps18`, `partial`, `gamma25` (exam orientation U(0, 2.5)), 300 per population.

### 5.3 Main results (research stage; 90% intervals; budget snapshot: D0 70 items, meaning-only 40, reading designs 60)

**Length and time** (simulation latency model, which later proved optimistic; see 5.5):

| design | items | reading | min (brief 6 s / 5 s) | min (measured latencies, mean / p95) |
|---|---|---|---|---|
| D0 | 70 | 0 | 7.0 | 6.0 / 6.2 |
| D1 / D1S / D1L | 40 | 0 | 4.0 | 3.4 / 3.5–3.6 |
| D2 | 60 | 30 | 5.5 | 5.4 / 6.0 |
| D3 / D3S | 60 | 19 | 5.7 | 5.1 / 5.6 |
| D4 | 60 | 20 | 5.7 | 5.3 / 5.8 |

**Words known by meaning** (MAE / 90% coverage / half-width, % of pool):

| design | zh·en-L1 | zh·ja-L1 | ja·en-L1 | ja·zh-L1 | bias range |
|---|---|---|---|---|---|
| D0 | 5.2 / 90% / ±10.4 | 5.0 / 91% / ±10.9 | 5.2 / 90% / ±10.9 | 5.4 / 89% / ±11.1 | −0.6..0.5 |
| D1 | 5.4 / 90% / ±11.0 | 5.7 / 91% / ±11.6 | 5.2 / 91% / ±10.8 | 5.4 / 91% / ±11.7 | −2.7..2.0 |
| D1S | 6.4 / 88% / ±12.7 | 6.6 / 89% / ±13.5 | 7.1 / 86% / ±13.1 | 6.7 / 89% / ±13.6 | −1.3..1.4 |
| D3S | 6.2 / 90% / ±12.6 | 7.0 / 90% / ±14.3 | 6.0 / 89% / ±12.2 | 6.7 / 87% / ±13.4 | −1.0..0.5 |

**Words known by meaning and reading.** Meaning-only rows show their over-statement against the m+r
truth and their coverage of it:

| design | zh·en-L1 | zh·ja-L1 | ja·en-L1 | ja·zh-L1 | bias range |
|---|---|---|---|---|---|
| D0 (meaning) | +4.4 / 80% | **+28.6 / 4%** | +2.1 / 88% | **+15.9 / 30%** | |
| D1S (meaning) | +3.6 / 86% | **+29.7 / 8%** | +1.2 / 86% | **+15.9 / 41%** | |
| D2 | 5.1 / 96% / ±11.7 | 5.4 / 94% / ±12.3 | 5.4 / 91% / ±11.5 | 5.0 / 94% / ±12.1 | −4.0..1.3 |
| D3 | 4.2 / 96% / ±10.5 | 5.2 / 94% / ±11.5 | 5.6 / 85% / ±10.1 | 5.1 / 93% / ±11.3 | −4.4..2.0 |
| **D3S** | 5.2 / 91% / ±10.9 | 6.2 / 90% / ±12.8 | 5.4 / 90% / ±11.3 | 6.5 / 88% / ±12.9 | **−0.6..0.9** |
| D3L | 7.1 / 92% / ±15.7 | 9.1 / 90% / ±18.0 | 7.1 / 84% / ±13.4 | 8.1 / 87% / ±15.4 | −1.9..0.1 |

**Mislabelling**, as m+r over-statement / intervals wholly above the truth / credited words not known
with the reading:

| design | zh·ja-L1 | ja·zh-L1 |
|---|---|---|
| D0 | +28.6 / 96% / 46% | +15.9 / 70% / 28% |
| D1S | +29.7 / 92% / 49% | +15.9 / 59% / 31% |
| D4 | +0.9 / 5% / 39% | +1.2 / 7% / 24% |
| D3S | +0.1 / 4% / 12% | +0.2 / 6% / 9% |

Lucky guesses among credited words for D3S: 2–12%, depending on skip rate and L1.

**First model vs ρ model** (lesson, ESTIMATE). D3i fitted "meaning and reading" as its own curve:
bias −2.6..+8.7%, coverage 78–91%. D3 multiplies by ρ = P(reading | meaning): −4.4..+2.0%, 85–96%.

**Sensitivity.**
- `eps06` and `eps18`: conclusions unchanged.
- `partial`: m+r bias +2.4..+3.8% for cognate learners; coverage 85–90%.
- `gamma25`: band-based level placement collapses (zh 36–46% within one level), while level strata keep
  88–92%.

### 5.4 Review re-runs (psychometric reviewer, `review_psy/`; draft rules: exit from 40, cap 60, 95% intervals)

| population | items | early stop (beginners / int. / adv.) | meaning bias / MAE / cover95 | m+r bias / MAE / cover95 | draft guard binds |
|---|---|---|---|---|---|
| zh·en-L1 | 56.6 | 28% (64 / 18 / 0) | −1.1 / 6.7 / 94% | +0.3 / 5.3 / 96% | 31% |
| zh·ja-L1 | 60.4 | 0% (1 / 0 / 0) | −0.2 / 7.2 / 95% | −0.2 / 6.3 / 96% | 0% |
| ja·en-L1 | 56.9 | 28% (62 / 22 / 2) | −1.1 / 6.6 / 94% | −0.4 / 5.9 / 94% | 44% |
| ja·zh-L1 | 60.2 | 2% (4 / 1 / 2) | +0.1 / 6.8 / 94% | +0.3 / 6.7 / 93% | 3% |

**Draft level range (95% bounds, 80% threshold), m+r, by true placement** (all populations of a
language pooled):

| true level | zh n | zh range contains truth | zh point ±1 | ja n | ja contains | ja point ±1 |
|---|---|---|---|---|---|---|
| 0 | 1,159 | 100% | 99% | 1,342 | 100% | 99% |
| 1 | 43 | 60% | 93% | 59 | 81% | 97% |
| 2 | 102 | 83% | **3%** | 157 | 90% | **26%** |
| 3 | 77 | 86% | **12%** | 81 | 95% | **35%** |
| 4 | 92 | 98% | **21%** | 97 | 99% | **44%** |
| 5 | 90 | 97% | **39%** | 264 | 100% | 76% |
| 6 | 141 | 99% | 57% | | | |
| 7 | 296 | 100% | 82% | | | |

The lower bound was 0 for 100% of learners at every true level, so the displayed copy was always "up to
HSK k at most" or "not yet most HSK 1 words".

The learner-side reviewer, using the 60-item snapshot of the research run, got within-one-level shares of
6 / 14 / 24 / 41 / 60% for HSK 2–6, with 49–82% placed two or more levels too low. For N4–N1 the shares
were 21 / 36 / 48 / 82%. Neither more items (40 → 90) nor forcing ≥ 5 items into bands 4–7 helped, and
with the exam effect switched off (`gamma_max = 0`) zh HSK 2–5 still reached only 12–38%
(`review_learner/level_by_true_out.txt`, `place_by_len_out.txt`, `compare_floor_out.txt`,
`place_gamma0_out.txt`).

**Other review figures:**
- **Per-band bias of K_b** was ≤ 0.024 at every true share level, so response-adaptive allocation does not
  bias.
- **Probes after a missed meaning:** raw right 18.7–23.6%; guess-corrected 7.6–13.2% (`main_stop.md`,
  "Probes").
- **`partial` run:** m+r bias +4.0% (zh·ja) and +2.8% (ja·zh), coverage 92% (`sens.md`).
- **ja with every non-kana word given a reading item** (`jafull.json`): ja·zh true m+r 45% → 38%; reading
  items 18.4 → 22.1 (zh-L1) and 13.0 → 15.7 (en-L1); meaning 95% half-width ±16.2% → ±17.2%.
- **List effect on the observed scale** (`v5_effect.txt`): 0.54 logit (zh) and 0.35 (ja) in the base
  model; 0.90 / 0.76 under `gamma25`; 0.17 / 0.00 with no exam effect.
- **Headline labels for a placement alone** (`labels_out.txt`): zh true level 0 → "Fewer than" 84%; zh
  true HSK 1–2 → 24–29%; otherwise "Rough", 1,095–1,213 words wide (zh) or 964–1,001 (ja).
- **Short tests** (`short_cover_out.txt`, 90%): at 20 items zh 92% / 95%, ja 90% / 92% (meaning / m+r),
  half-widths ±23.8–26.5%; at 40 items 87–93%, ±14.6–16.6%.

### 5.5 Synthesis re-runs (`synth/len50.py`, `synth/stop50.py` on `sim/out/raw_main.json`)

These settle the length decision (LRN L4), at de6fd05b's measured pace (6.57 s per meaning item,
7.50 s per reading item) and with D3S snapshots:

| lang / L1 | items | meaning / reading items | 90% half-width meaning / m+r (% pool) | MAE m / m+r | 90% cover m / m+r | minutes mean / p95 |
|---|---|---|---|---|---|---|
| zh (all) | 40 | 26.2 / 14.1 | ±16.9 / ±15.0 | 8.2 / 6.9 | 90% / 92% | 4.6 / 4.8 |
| zh (all) | **50** | 32.8 / 17.5 | **±14.9 / ±13.2** | 7.3 / 6.2 | 90% / 92% | **5.8 / 5.9** |
| zh (all) | 60 | 39.3 / 21.0 | ±13.5 / ±11.9 | 6.6 / 5.7 | 90% / 91% | 6.9 / 7.1 |
| ja (all) | 40 | 29.1 / 11.1 | ±16.1 / ±15.2 | 8.2 / 7.5 | 88% / 89% | 4.6 / 4.7 |
| ja (all) | **50** | 36.5 / 13.7 | **±14.2 / ±13.4** | 7.2 / 6.6 | 88% / 88% | **5.7 / 5.9** |
| ja (all) | 60 | 44.0 / 16.3 | ±12.8 / ±12.1 | 6.4 / 6.0 | 88% / 89% | 6.9 / 7.0 |

Cap 50 with the precision exit from 40 (checked at the 40 and 45 snapshots):

| population | early stop | items | minutes |
|---|---|---|---|
| zh·en-L1 | 16% (beginners 43%, intermediate 4%, advanced 0%) | 49.0 | 5.6 |
| zh·ja-L1 | 0% | 50.4 | 5.8 |
| ja·en-L1 | 16% (beginners 41%, intermediate 6%, advanced 0%) | 48.9 | 5.5 |
| ja·zh-L1 | 0% (beginners 1%) | 50.3 | 5.8 |

English-L1 zh beginners answer 22% of meaning items right, guesses included.

### 5.6 Limitations

- **The learner model is an assumption.** Cognate rates, κ, π, ν, ω, the τ distribution and the
  exam-level effect are invented, informed by the literature and one learner. Results are most
  trustworthy as comparisons between designs.
- **English was not simulated** (no en pool export). en length and precision are inferred from D1S.
- **The research run's ja figures treat words without a stored reading as exempt.** The launch design
  does not (see the `jafull` numbers); V0 must use the launch readiness flags.
- **Distractor quality is not modelled.** A guess is right 1 in 4.
- **Item flaws are not modelled.** These include the tone-only and okurigana tells and the cross-CJK
  prefix.
- **The draft's displayed level range was simulated only by the reviewer**, not by the research stage.

---

## 6. What each finding changed in the design

The reviews challenged the draft (2026-11-18, `draft-design.md`). Decisions by the synthesis stage:

| ID | Severity | Finding (short) | Decision | Change in the spec |
|---|---|---|---|---|
| M1 | blocker | 95% level-range lower bound always 0; "4 in 5" is the point rule carried by beginners | accepted | Level range removed from v1 (tech §5.3); PQ2 default "none"; TASK-1090 redesign with gates on displayed copy; V0 records copy/label distributions |
| M2 | major | Level shares rest on frame words (9–38% of levels), more frequent than the rest; the assumption ADR-054 rejected | accepted | ADR-054 stance kept; any later claim names the subset, revises ADR-054, re-validates after TASK-1063 |
| M3 | major | Tone-only foils on 10.9% of zh anchors; tone-ignorant learners credited ≈ 0.93; tone count unobservable | accepted | Scored zh items exclude tone-only foils; "tones not tested" copy; unscored 2-option `sound_pair` probes (V6); per-word tone line dropped |
| M4 | major | Nothing validates the reading-step 1:3 ratio; partial run +2.8..+4.0% | accepted | V9 `recheck` probes (disjoint foils, ≥ 7 days later; lower-bound caveat because the reveal teaches); "may be a little high" in the method note; ADR revision trigger at implied guess > 0.30 |
| M5 | major | Meaning sample pools two instruments (reading shown and prefix kept vs not) | accepted | `instrument` column; pooling within instrument and D; the placement's own result from its own items; TASK-1091 converts the check; V1 becomes a mode-effect estimate |
| M6 | major | IDK copy claims neutrality; IDK suppresses partial knowledge | accepted | Neutral copy; `forced_guess` probes (p 0.15, ≤ 2 per test within a shared budget of 4); `skip_share` stored |
| M7 | major | Over-claims ("really know", gap cause, beginners finish early, probes uninformative, "always agree", guessed per-word counts) | accepted | Recognition wording; gap with its own interval and no cause; per-L1 early-stop facts; reading item "usually/always signals a right meaning"; "matches My vocabulary on the day taken"; "guesses included" |
| M8 | minor | Display guard binds often and points the wrong way | accepted | `lo_m := max(lo_m, lo_mr)`, `hi_mr := min(hi_mr, hi_m)` |
| M9 | major (v2) | v2 selection breaks the design-based estimator; unidentified; one skip rate; gate loophole | accepted | v2 scores only, selection stays uniform; μ0 and group means fixed at 0; separate g_m, g_r; gate per (language, L1 group) |
| M10 | minor | V4 compares a raw rate with 0.25 under skipping | accepted | V4 uses ω̂ = (r − w/3)/n and the implied per-learner bias |
| M11 | minor | V5 threshold uncalibrated; underpowered pass; wrong outcome | accepted | V5 kept only as input to TASK-1090, with a simulated decision rule, an equivalence test and pair outcomes |
| M12 | minor | V2's 8-of-10 rule cannot detect under-coverage | accepted | Variance inflation √(mean z²) with a CI from every pair, applied when its lower bound > 1 |
| M13 | minor | ja simulation treated words without readings as exempt | accepted | E29 figures quoted; V0 fixtures from launch readiness flags |
| M14 | minor | Readiness gate checks share, not representativeness | accepted | Gate compares ready vs not-ready lemmas on Zipf, length and list share per band |
| M15 | minor | D* rule can drop the placement's own answers | accepted | The placement result uses its session's D; the report prefers the latest placement's D; test case |
| M16 | minor | Placement feeds a skip-as-wrong ability fit and the rating writer | accepted | No pooled-ability or rating write from placements until OQ33 (TASK-1083 blocked) |
| L1 | blocker | Level line wrong for mid-level learners (3–41% within one level for HSK 2–5) | accepted | Same as M1; per-true-level gate (≥ 70% for levels 1–6 zh, 1–4 ja) on displayed copy for any later level output; goal-level share with a range offered under PQ2/TASK-1090 |
| L2 | major | Headline is a pool count, often "Fewer than" or ~1,100 words wide | accepted | Result leads with this test's word groups and actions; range second as a band; lo = 0 phrasing; gap line only when clearly above 0 |
| L3 | major | End now and abandoned sessions get no result | accepted | Eligibility (c): warm-up + ≥ 20 scored items; abandoned results frozen and shown once; resume 24 h; unit cases at 20/30/45 |
| L4 | major | "About 5 minutes" is 6.6–7.0 at the real pace; a round trip per tap | partly accepted | Cap 50 + 7-minute active-time cap, "about 6 minutes" (5.5–5.8 measured-pace ESTIMATE); "about N minutes left"; one SQL round trip per answer with lagged allocation. **Rejected**: pre-sending both branches, because choosing between them reveals the key |
| L5 | major | Beginners face ~50 items, mostly IDK; "finish early" false | accepted | Onboarding "studied before?" gate; warm-up commonest band first; claim deleted; "Stop here and see your result" |
| L6 | major | Meaning-only words pushed out of practice; drill cannot show zh pinyin | accepted | Pair-based evidence; A2r reading-gap queue; native-sense admission; TASK-1082 intro-drill fix as a zh launch dependency; "Practise these readings" for all tiers |
| L7 | major | Launch allowed with the evidence hook off while copy promises practice | accepted | Evidence (TASK-1081) and, for zh, TASK-1082 are hard launch dependencies (TASK-1088); PQ5 launch-blocking |
| L8 | major | Strip misses ja/zh `headword ——`: 343 items answerable | accepted | Rule 5 covers `；`, `;`, `——`, `—`; measured residual ≤ 1%; residual anchors not meaning-ready |
| L9 | major | Tone/special-mora errors rarely tested; okurigana tell (19%) | accepted except point 2 (partly) | Rule 3b kana consistency (+ filler fix in TASK-1075); "Choose the pinyin (tones are not tested)"; PQ3 asked before launch. Point 2 (force-include special-mora foils in scored items) **partly accepted**: measured by `sound_pair` probes instead, keeping the scored construct uniform, consistent with M3 |
| L10 | major | Retake headline pools 180 days, showing progress at half size | accepted | Retake block: this vs previous placement with the ADR-053 verdict, then combined |
| L11 | minor | Probes unlabelled and misleading; "uninformative" false | accepted | Probes labelled "Extra question — not scored"; claim deleted |
| L12 | minor | Guessing instruction not true for informed guesses | accepted | Same as M6 |
| L13 | minor | Goal path unchanged after a placement | accepted | TASK-1094: "answered in a placement, not yet checked" segment and hero copy |

**Not verified** (carried into the spec as INFERENCE or open questions):
- literature figures (abstracts only);
- the JLPT 漢字読み near-miss distractor style;
- English length and precision;
- the effect of rules 3, 3b, 4 and 5 on readiness (measured by `calibration_placement_ready_counts`
  after TASK-1077);
- whether the Supabase cap is 500 MB or 500 MiB;
- the intro-drill path for placement-admitted words, traced in code but not executed.

## Related Pages
- [[features/vocab-placement]] · [[features/vocab-placement.tech]]
- [[decisions/ADR-057-adaptive-placement-with-conditional-reading]] · [[decisions/ADR-058-meaning-and-reading-recognition-pair-estimator]] · [[decisions/ADR-059-placement-evidence-kind]]
- [[decisions/ADR-051-vocabulary-size-from-calibration-frame]] · [[decisions/ADR-054-exam-word-lists-in-storage]]
- [[features/calibration]] · [[features/knowledge-report]]
- [[tasklist/vocab-placement.tasks]]
