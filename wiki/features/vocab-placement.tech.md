---
title: Vocabulary placement — Technical Specification
type: feature-tech
status: planned
prose_page: ./vocab-placement.md
last_updated: 2026-11-18
dependencies:
  - "tables (extended): calibration_sessions, calibration_responses, user_vocabulary_knowledge"
  - "tables (read): calibration_anchor_pool, calibration_distractor_cache, calibration_anchor_blocklist, dim_word_senses, dim_vocabulary, exercises"
  - "NEW SQL functions: calibration_placement_ready_counts, calibration_placement_next_item, calibration_placement_answer, calibration_placement_close, calibration_placement_close_stale, knowledge_calibration_inputs, update_vocabulary_from_placement_batch"
  - "NEW table (zh tones, TASK-1092): calibration_zh_tone_inventory; NEW SQL: calibration_zh_tone_variants, calibration_refresh_zh_tone_inventory"
  - "CHANGED SQL functions: calibration_normalise_pronunciation and calibration_syllable_count (zh), calibration_refresh_anchor_pool (katakana-only lemmas), pronunciation_distractors (ja visible-kana filter)"
  - "NEW code: services/placement_design.py, services/calibration_placement.py, templates/placement.html, static/js/pages/placement.js"
  - "CHANGED code: routes/calibration.py, services/practice/new_word_admission.py, services/intro_drill.py, services/vocabulary/knowledge_estimate.py (created by TASK-1035), web/pages.py, web/rate_limits.py, web/scheduler.py, templates/onboarding.html, static/js/pages/onboarding.js, static/css/redesign/trainers.css, static/i18n/{en,es,ja,zh}.json"
  - "Knowledge Report tasks: TASK-1034 (frame bands), TASK-1035 (estimator module), TASK-1036 (summary RPC), TASK-1039/1040 (summary route and page), TASK-1044 (words RPC)"
  - "Exam lists in Storage (ADR-054) — only for validation V5 and the representativeness check; no level output in v1"
breaking_change_risk: medium
---

# Vocabulary placement — Technical Specification

> **Risk is medium.** The migrations extend live tables on the only Supabase project (there is no
> staging). Four live calibration functions change: the zh normaliser, the pool refresh predicate,
> the ja foil filter, and the check's item builder later (TASK-1091, owner-gated). One practice read
> path changes (new-word admission). Every change is additive or a bug fix, and the open-ended check
> keeps working unchanged until TASK-1091.

**Labels.** MEASURED = read from code (file:line), the live database (read-only SQL quoted in
[[evaluations/vocab-placement-research-2026-11-18]]) or a cited study. ESTIMATE = arithmetic or
simulation on stated inputs; every simulation figure holds only for the research stage's learner
model. INFERENCE = reasoning not tested. DECISION = a design choice; each contestable one is a
question in §22 with its default.

**Design in one paragraph.** A placement is a session of the vocabulary check
([[features/calibration]]) in a new mode, `placement`. It adapts **which frequency band** the next
word comes from to the answers so far: two words per band first, commonest first, then the band
whose next answer most narrows the result. Within a band the word is drawn uniformly at random. For
Chinese and Japanese each word is a **pair**. The meaning item shows the characters only. Only if the
meaning is right does the reading item for the same word follow. For Chinese it shows the right
pinyin, a wrong tone combination of it, another word's pinyin with the same syllable count, and a
wrong tone combination of that, using only syllable+tone pairs that exist in Mandarin (owner,
PQ3), so tones are scored. For Japanese it shows kana readings consistent with the word's visible
kana. One reveal follows the whole word. The test stops at 60 scored items for zh/ja (owner, PQ10)
or 40 for en, after 9 minutes of answering, or earlier once both ranges are narrow enough. Scoring
uses ADR-051's estimator on the meaning answers and a pair estimator on the meaning-and-reading
answers (for zh: right tones minus wrong tones on the same syllables), with answers pooled only with
the same kind of item. The result leads with this test's own words, then the meaning-and-reading
range, then the gaps ("pinyin, not the tones" for zh; "meaning, not the reading") when they are
clearly above zero. There is **no exam-level estimate** (owner, PQ2: not for now). Answers reach practice as their own evidence kind, written per word pair; words with the
meaning but not the reading go to reading practice. Up to 4 labelled, unscored questions per test
check the scoring's assumptions. A model-based (IRT) scoring is specified as a gated later upgrade.

---

## 0. Evidence base

Source tags: **[AUD]** code and data audit, **[SIM]** design simulation, **[LIT]** literature,
**[PROD]** product survey, **[PSY]** psychometric review, **[LRN]** learner-side review, **[SYN]**
synthesis-stage re-runs. All are filed in [[evaluations/vocab-placement-research-2026-11-18]].

| # | Fact | Label / source |
|---|---|---|
| E1 | Today's check is not adaptive. `calibration_next_anchors` serves the least-served Zipf band of the session, random within band, excluding only anchors served in this session (words repeat across sessions), and serves any sense rank. | MEASURED [AUD §1.1] (`migrations/task772_calibration_anchor_pool.sql:186-257`) |
| E2 | A skip is stored `chosen_sense_id NULL, is_correct false` (`migrations/task769_calibration_record_answer.sql:138`). Mode is stored per session only (CHECK `definition|pronunciation`). | MEASURED [AUD §1.4] |
| E3 | Meaning items show the reading under the word: `calibration_build_items` returns `pronunciation` in definition mode (`migrations/calibration_distractor_cache_packed.sql:345-346`), rendered at `static/js/pages/calibration.js:243-244`. | MEASURED |
| E4 | Sessions end only through `POST /api/calibration/end` (`routes/calibration.py:189-200`) → `end_session` (`services/calibration_service.py:731-773`). 74 of 79 live sessions never ended; 1,005 of 1,349 response rows (74.5%) are unanswered prefetch. | MEASURED [AUD §1.5] |
| E5 | The check calls the guarded rating writer at `/end` (`services/calibration_service.py:764-772`), contradicting `wiki/features/calibration.md:122-126`. | MEASURED |
| E6 | Reading foils come from Levenshtein distance over a normalised reading, with homophones excluded and the same syllable or mora count **preferred**. 8 are cached and 3 sampled at serve time. zh: 433 of 3,969 anchors (10.9%) have a cached tone-only foil (519 of 30,929 foils, 1.7%); 2,473 foils (8.0%) differ in syllable count. | MEASURED [AUD §1.3, §2.4, A.6] |
| E7 | **zh normaliser defect.** 6,621 of 8,110 zh standard readings lack the numbered suffix, so `calibration_normalise_pronunciation` returns diacritics with syllable count 0. Any new zh foil fill would rank foils with a broken length test. | MEASURED + INFERENCE [AUD §1.3] |
| E8 | Paired readiness today (rank-1 lemma, ≥ 3 cached options in both modes): zh 3,482 of 3,623 (96%; band 1 91%); ja 2,185 of 3,175 (69%; band 1 50%). ja: 841 pool rows lack a reading that `dim_word_senses` now has (stale pool); 214 katakana-only lemmas are in the reading pool. | MEASURED [AUD §2.1, §2.2] |
| E9 | Cross-CJK definitions. All 3,623 zh/ja rank-1 keys start `headword；`. Of 3,175 ja/zh keys, 693 start `headword；` and **2,478 start `headword ——`**, 453 of them with the Japanese lemma itself. After a strip of the `；` form only, zh/ja has 1 residual key containing the prompt; ja/zh has 470 keys still containing the lemma, **343 (10.8%) answerable by string matching**. | MEASURED [LRN Q4, Q5]; [AUD §2.4] missed the `——` form |
| E10 | ja okurigana tell: 488 of 2,243 ja reading anchors are kanji+kana. On average 55% of their cached foils contradict the visible kana; 199 have fewer than 3 consistent foils; 91 (19%) can be answered by kana matching alone (考え かんがえ vs かんがい, かんけい …). | MEASURED [LRN Q2] |
| E11 | ja special-mora and voicing foils (vowel length, っ, ん, dakuten; generous detector): 298 of 17,592 cached foils, on 267 of 2,230 anchors (12.0%); about 4.3% of served items contain one. | MEASURED [LRN Q3] |
| E12 | Live data: 344 answers from 3 users. 110fb390 looks automated (median latency 364 ms). Usable data is de6fd05b (ja): 178 meaning answers (47% right, 43% skip, 10% wrong) and 99 reading answers (59% / 40% / 1%). Only 6 words were answered in both modes. | MEASURED [AUD §3] |
| E13 | Pace of the only real learner (de6fd05b; gap between consecutive answers ≤ 60 s, which includes reading the reveal): **6.57 s per meaning item** (median 5.03 s), **7.50 s per reading item** (median 5.39 s). Render-to-tap latency medians are 3.4 s and 3.6 s. That learner is the developer; newcomers are probably slower (INFERENCE). | MEASURED [LRN Q1], [AUD §3.3] |
| E14 | The owner's own answers (n = 1, ja/en): knowledge slope 1.05 per Zipf point (90% interval 0.70–1.55). Skip-if-unknown 0.75 for meaning items, 0.95 for reading items. | MEASURED [SIM §2.2] |
| E15 | Practice hand-off today. Queue A2 admits only calibration answers that were wrong or skipped (`services/practice/new_word_admission.py:648-655`) and vetoes `known`/`probably_known` rows (`:660-673`). A1 needs ≥ 2 evidence or `p_known ≤ 0.40` (`services/practice/constants.py:37-38`). The supply gate counts exercises on the exact sense id (`new_word_admission.py:762-811`); words enter through the intro-drill bypass (`:498-505`). The ledger reads `mode = 'definition'` sessions only (`:566-600`). | MEASURED (read 2026-11-18) |
| E16 | Exercise supply. The calibration anchor (English-gloss) sense has ≥ 3 active exercises for **0** of 3,623 zh and 0 of 3,175 ja pool words. Some sense of the same word has ≥ 3 for zh 3,386 and ja 2,935, and a reading drill for zh 3,161 and ja 2,582. `dim_vocabulary.reading` is empty for all 3,682 zh pool words. | MEASURED [LRN Q6, Q7] |
| E17 | The intro drill reads `reading = dim_vocabulary.reading or sense.pronunciation` (`services/prestudy.py:185`), and `intro_drill._reading` returns None for zh unless the reading has a numbered `(…)` part (`services/intro_drill.py:238-251`). Most zh native readings no longer have one (E7), so the drill's reading formats (`read_typed`, stage 1 for cjk, `:47-48`) are dropped for those words. | MEASURED (code) + INFERENCE (not executed end to end) |
| E18 | `services/irt/calibrator.py` is a 2PL exercise calibrator with no guessing floor, person estimation, selection or stopping rule. It has calibrated 0 of 144,374 exercises. | MEASURED [AUD §4] |
| E19 | Storage: database 513,535,123 B; calibration tables ≈ 18.6 MB; a response tuple averages 100 B. | MEASURED [AUD §5.1] |
| E20 | Design D3S (adaptive band allocation, conditional reading, ADR-051 estimator on meaning and on pairs) reimplemented at the draft rules: count bias −1.1..+0.4% of the pool; **95% coverage 93–96%** in every population; stopping early adds no bias; per-band bias of K_b ≤ 0.024. | ESTIMATE [PSY], [SIM §3] |
| E21 | Meaning-only results over-state "meaning and reading" for Japanese-L1 learners of Chinese by **+27–30% of the pool (~1,000 words)**, with 91–96% of their intervals wholly above the truth. For Chinese-L1 learners of Japanese the over-statement is +14–17%. The conditional reading cuts the share of intervals above the truth to 3–6%. | ESTIMATE [SIM §3.5] |
| E22 | Length (D3S, measured pace E13). **50 scored items**: 5.7–5.8 min mean; 90% half-width m+r ±13.2–13.4% and meaning ±14.2–14.9% of the pool. **60 items**: 6.9–7.0 min; ±11.9–12.1% and ±12.8–13.5%. Early stop with a cap of 50 (exit from 40): English-L1 beginners 41–43% at ~46.5 items; cognate-L1 learners 0–1%. | ESTIMATE [SYN `len50.py`, `stop50.py`] |
| E23 | **Exam-level estimate fails.** The 95% lower bound of the draft level range was 0 for 100% of simulated learners. The point rule was within one level for zh true HSK 2/3/4/5/6: 3–6 / 12–14 / 21–24 / 39–41 / 57–60%, mostly two or more levels too low; for ja true N4/N3/N2/N1: 21–26 / 35–36 / 44–48 / 76–82%. The pooled "80–86%" came from the 58% (zh) and 67% (ja) of learners whose true level is 0. More items (40 → 90) and forcing items into bands 4–7 do not help. | ESTIMATE [PSY M1], [LRN L1] |
| E24 | The pool holds 22–33% of HSK 2025 levels 1–6, 9% of 7–9 and 13–38% of JLPT levels. In-pool level words are more frequent than dictionary-only ones (HSK 4 median Zipf 5.08 vs 4.67). The frame band mix over-states HSK ≤ 3–7 shares by +2.1..+3.4 points on average. | MEASURED + ESTIMATE [PSY M2], [SIM §2.1] |
| E25 | Headline labels for a placement alone: zh learners with true level 0 get "Fewer than" 84% of the time, true HSK 1–2 24–29%; everyone else gets "Rough", about 1,100–1,200 words wide (zh) or 1,000 (ja). | ESTIMATE [LRN L2] |
| E26 | Partial reading knowledge (meaning known, reading half-guessable) biases m+r up by +2.4..+4.0% of the pool for cognate learners, with coverage 85–92%. | ESTIMATE [SIM §4], [PSY M4] |
| E27 | Short tests stay honest: D3S 90% coverage at 20 items is 92% / 95% (zh, meaning / m+r) and 90% / 92% (ja), with half-widths ±24–27%. | ESTIMATE [LRN L3] |
| E28 | Reading probes after a missed meaning: raw right rate 18.7–23.6% (below 0.25 because of skips); guess-corrected (r − w/3)/n 7.6–13.2%. | ESTIMATE [PSY M10] |
| E29 | With every non-kana ja word given a reading item (the launch design), ja·zh true m+r share falls from 45% to 38% of the pool. Reading items per 60-item test rise 18.4 → 22.1 (zh-L1) and 13.0 → 15.7 (en-L1), and the meaning 95% half-width widens ±16.2% → ±17.2%. | ESTIMATE [PSY M13] |
| E31 | **Length at the owner's 60** (cap 60, precision exit from 40 checked at 40/45/50, D3S, pace E13): zh·en 56.7 items, 22% stop early (beginners 56%), 6.5 min (p95 7.1); zh·ja 60.4, 0%, 7.0 (7.1); ja·en 56.8, 21% (beginners 52%), 6.4 (7.0); ja·zh 60.2, 0%, 6.9 (7.0). 95% half-widths meaning / m+r (syllables-only reading items): zh·en ±15.5 / ±13.4%, zh·ja ±17.0 / ±15.3%, ja·en ±15.0 / ±13.8%, ja·zh ±16.0 / ±15.3% of the pool. 90% coverage 87–92%. | ESTIMATE [SYN `stop60.py`] |
| E32 | **zh tone variants under the owner's rule** (a syllable+tone counts as existing if it occurs in any zh dictionary reading; only full tones 1–4 change; no change on 一/不; a 3→2 change before a tone-3 syllable alone is a sandhi form and excluded; never equal to a reading of the same lemma): 382 syllable bases with on average 2.47 attested full tones. Of 3,656 pool readings, **3,622 (99.1%) have ≥ 1 valid variant**, 96.5% ≥ 2, 89.0% ≥ 3; band 7 94.8% / 70.3% (≥ 1 / ≥ 3), bands 1–6 98.6–99.8% ≥ 1. 7,754 of 7,855 zh dictionary readings (98.7%) have one (proxy for segmental foils). | MEASURED (read-only SELECT 2026-11-18; `tones/tone_cover.py`) |
| E33 | **Scored-tone item simulation** (item K, K′, F, F′ of rule 4; tone known given reading known with p = θ + (1 − θ)·σ(a(z − τ) − 1.5), θ ~ U(0.5, 0.95), ASSUMPTION; 4 × 300 zh learners; cap 60): the full-reading estimator (pc − pkt)/n′ has bias +0.6..+0.7% of the pool; with pseudo-count 0.25 per category its 95% coverage is 96–97% (0.5, ADR-051's value: 98–99%, too wide; 0.1: 93–94%). 95% half-width ±15.2% (zh·en) / ±17.5% (zh·ja) of the pool, ≈ ±550 / ±630 words; 56.4 / 60.4 items; 29% / 0% stop early; 6.4 / 7.0 min. The ADR-058 pair estimator (prw/3) on the same items over-states by +1.9..+3.3%, because it credits a third of the words whose syllables are known without their tones. The syllables estimator (pc + pkt − pf)/n′ has bias −0.1%, coverage 96%. Sensitivity: weaker tone knowledge (θ ~ U(0.3, 0.8)) stays unbiased (+0.6%); partial tone memory (65% right tone when the syllables are known) biases +2.1..+2.4% with coverage 95–96%. | ESTIMATE [SYN `tones/tone_sim.py`] |
| E34 | **V0 on the production code** (TASK-1087, `tests/test_placement_coverage.py`, 5 populations × 2 IDK levels × 600 synthetic learners, a reduced port of the research model with the E33 tone state): 95% coverage 0.92–0.97 for meaning and meaning-and-reading, bias within ±1.3% of the pool, gap ranges 0.95–0.99; zh/ja 55–60 scored items and 6.2–7.0 min, en 38.5 items / 4.2 min; End now at 20/30 items ≥ 0.88. The meaning estimate runs about −1% for English-L1 learners whether or not the precision exit is used: response-adaptive allocation, the same −1.1% the psychometric review found. The ja·en reading gap reads −2.6% (no V0 threshold on gap bias). | ESTIMATE |
| E30 | Literature: four-option meaning tests measure recognition and over-estimate usable knowledge. Meaning and reading of kanji/hanzi words are separable dimensions. Showing a reading in a meaning item changes what it measures. A sequential (steps) model fits "reading only after a right meaning". The guessing floor must be fixed at small n. An IDK option suppresses partial knowledge, and IDK use differs between learners (bilingual + IDK r = .77 vs .88–.91, N = 200). | MEASURED in other populations [LIT B1–B5, A2-13, A2-15]; abstracts only |

## 1. Architecture Overview

```
/placement?lang=zh  (templates/placement.html + static/js/pages/placement.js; .cal-page styles)
  │ authFetch
  ▼
routes/calibration.py  (calibration_bp, /api/calibration/placement/*)
  POST /placement/start  ─► calibration_placement.start()
  │     ├─ calibration_placement_close_stale(user, '24 hours')      [SQL; finish() each closed session]
  │     ├─ resume an open placement for (L, D) younger than 24 h, or INSERT calibration_sessions (mode 'placement')
  │     └─ first item: calibration_placement_next_item(band 7)       [SQL]
  POST /placement/answer ─► calibration_placement.answer()
  │     ├─ next_band = placement_design.next_band(tallies returned by the previous call)   [pure Python]
  │     ├─ draws = rng() for the probe rules                                                [pure Python]
  │     ├─ calibration_placement_answer(...)  → grade + per-band tallies + next item      [SQL, ONE round trip]
  │     └─ placement_design.should_stop(tallies) → finish(reason) when a word is complete  [pure Python]
  POST /placement/end    ─► finish('learner') if eligible, else {not_enough}
  GET  /placement/result ─► frozen calibration_sessions.result
  GET  /placement/latest ─► latest frozen result for the language (shows an abandoned session's result once)
finish(reason):
  ├─ calibration_placement_close(session, reason)  (deletes the one pending unanswered row; ended_at; stop_reason)
  ├─ knowledge_calibration_inputs(user, L, D=session D, p_session_id)       → this placement's tallies
  ├─ knowledge_calibration_inputs(user, L, D=session D, instrument rule)    → combined tallies (same instrument)
  ├─ knowledge_estimate: estimate_range ×{m, mr}, gap_range, guard, labels, eligibility   [pure Python]
  ├─ previous placement for (L, D) → ADR-053 comparison
  ├─ UPDATE calibration_sessions SET result = {...} (frozen, ≤ 2 KB)
  ├─ evidence write (ADR-059): update_vocabulary_from_placement_batch(pair outcomes)        [SQL]
  └─ (no pooled-ability or rating write until OQ33 — §11)
Knowledge Report: knowledge_report_summary embeds knowledge_calibration_inputs (report rule, §9).
```

**DECISION (ADR-057):** the placement is a **session mode of the vocabulary check**, not a new
feature stack. It uses the same pool, distractor cache and tables (extended) and the same estimator
as the report. Allocation, stopping and statistics run in pure Python on per-band tallies (≤ 7 × 6
integers). Word choice, item building and grading run in SQL, in **one round trip per answer**
(TASK-774 measured 53–108 ms per Supabase round trip from the host, [[evaluations/latency-2026-11-11]]).

## 2. Item formats and item rules

| language | meaning item | reading item | reading-exempt words |
|---|---|---|---|
| **zh** | the word in characters only (no pinyin line); four definitions in the definition language D from the definition cache (first 3 cached foils, as the check); "I don't know" | the same word; four **tone-marked pinyin** strings (`calibration_display_pronunciation`) under rule 4: the key K from the word's native rank-1 row, a tone variant K′ of K, one cached segmental foil F (rule 3) and a tone variant F′ of F; "I don't know"; prompt "Choose the pinyin" | none. The 9 zh rows with no tone mark at all [AUD §2.3] are not reading-ready |
| **ja** | the word as written (kanji, kanji+kana or kana), no reading line | the same word; four **hiragana** readings (key from the native rank-1 row, 3 sampled foils under rules 3 and 3b); prompt "Choose the reading" | **kana-only lemmas** (`^[ぁ-ゟァ-ヿー・]+$`): their written form is their reading. Rows whose reading contains romaji or kanji (7 data errors [AUD §2.3]) are not reading-ready |
| **en** | the word; four definitions in D | none | all |

**Placement item rules (DECISION, ADR-057):**
1. **Rank-1 sense only**, one item per lemma (as TASK-1062 proposes for the check).
2. **No reading on meaning items** (fixes E3 for this mode).
3. **Same syllable (zh) or mora (ja) count** for all 3 served reading foils, counted on the
   **display** form: zh = number of space-separated syllables; ja = kana count minus small kana
   (ゃゅょぁぃぅぇぉ and katakana equivalents; っ is a mora and counts — corrected 2026-11-19, the first version dropped it, so きって counted 2). This does not use the broken zh normaliser (E7). Pleco does
   the same [PROD P3].
   - **3b (ja).** Every served foil must match the lemma's visible-kana pattern
     `'^' || regexp_replace(lemma, '[^ぁ-ゟー]+', '.+', 'g') || '$'` (E10).
4. **zh: two tone pairs (owner, PQ3, 2026-11-18; ADR-060).** The four options are K (the key), K′ (a
   tone variant of K), F (a cached segmental foil) and F′ (a tone variant of F), shuffled. Every
   reading item has the same shape, so the two options that share the key's syllables never point to
   the key (each syllable set appears twice).
   - **Tone variant** of a reading = the same syllables with a different tone combination, where
     every syllable+tone pair **exists in Mandarin**: it occurs in at least one zh dictionary reading
     (`calibration_zh_tone_inventory`, built from native zh rows of `dim_word_senses`). Only full tones
     1–4 change; a neutral-tone syllable keeps its tone and no syllable becomes neutral (optional
     neutral tones make such variants arguably correct). No change on a syllable written 一 or 不. A
     variant that only turns a tone 3 into tone 2 before another tone 3 is a sandhi realisation and is
     excluded. A variant never equals any reading of the same lemma (polyphones). Drawn uniformly
     from the valid variants by `calibration_zh_tone_variants` (§14).
   - **F** is drawn from the anchor's cached pronunciation foils with the key's display syllable count
     (rule 3) whose diacritic-stripped form
     (`translate(lower(x), 'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü', 'aaaaeeeeiiiioooouuuuvvvvv')`) differs from the
     key's, and that have a valid variant F′ ∉ {K, K′}.
   - The construct is **"recognises the pinyin with its tones"**. Choosing K′ means "the syllables
     but not the tones" and feeds the tone gap (§5.1).
5. **Cross-CJK definitions (zh/ja, ja/zh): strip the leading equivalent word** from all four options
   at display time: `regexp_replace(text, '^\s*[^；;—]{1,12}\s*(；|;|——|—)\s*', '')` (E9). An anchor
   for these pairs whose stripped key still contains the prompt lemma (length ≥ 2) while none of
   its 3 served foils does is **not meaning-ready** for that pair (LRN L8).
6. **Every meaning option is a real word's definition; every reading option is a real word's
   reading, or (zh only) a wrong tone combination of one under rule 4.** No made-up syllables, no
   made-up words. ja long-vowel / っ / ん / voicing variants are not used as scored foils (PQ3 was
   answered for tones only); ja special morae are measured only by the unscored `sound_pair` probe.

**Readiness, per (L, D) and lemma:**
- *meaning-ready*: the rank-1 sense is in the frame F(L, D) (ADR-051: pool row, `has_embedding`,
  not blocklisted) with ≥ 3 cached definition foils, and rule 5 does not exclude it.
- *reading-ready* (zh; ja non-kana): the native rank-1 row (definition language = L,
  `definition_level = 'standard'`, `has_pronunciation`, not blocklisted, well-formed reading) has
  - ja: ≥ 3 cached pronunciation foils that pass rules 3 and 3b;
  - zh: ≥ 1 valid tone variant of the key and ≥ 1 cached segmental foil that passes rule 4 (with its
    own variant). Measured: 99.1% of pool keys have a variant (band 7: 94.8%) (E32).
- *placement-ready* = meaning-ready ∧ (reading-exempt ∨ reading-ready). Only placement-ready lemmas
  are served; the denominator stays the full frame F(L, D) (§5.1).

**Launch gate per (L, D) (DECISION, PSY M14):**
1. ≥ 90% of the frame placement-ready overall and ≥ 80% in every band.
2. **Representativeness**, in every band where ≥ 5% of the frame is not ready, comparing ready and
   not-ready lemmas:
   - |mean Zipf difference| ≤ 0.10;
   - difference in the share of lemmas with ≥ 3 characters ≤ 10 points;
   - difference in the share of lemmas on an exam list (ADR-054 file) ≤ 10 points.
3. The output of `calibration_placement_ready_counts` is recorded in `wiki/log.md`. A failing
   language stays off.

The uncorrected coverage bias per band is (1 − r_b)·(K_ready − K_unready), where r_b is the ready
share (INFERENCE). Point 2 bounds it indirectly.

Today: zh passes point 1 on the paired criterion (96%; band 1 91%; to be re-measured with rules 3–5
and the tone rule, which removes about 1% of keys, E32).
ja fails (69%; band 1 50%) until TASK-1075. Rule 3b alone removes about 199 ja anchors unless
the refill applies the kana filter (ESTIMATE: (2,185 + ~800 − 199)/3,175 ≈ 88% without it).

## 3. Pairing, sequencing and probes

**DECISION (ADR-057): meaning first; the reading only after a right meaning; one combined reveal.**

```
word w (zh/ja, reading-ready):
  meaning ──► right ─────────────► reading (scored) ──► [sound_pair probe? ja] ──► combined reveal
          ├─► IDK ──► [forced_guess probe?] ───────────────────────────────────► combined reveal (reading shown)
          └─► wrong ─► [reading_after_miss probe?] ────────────────────────────► combined reveal (reading shown)
word w (reading-exempt, or en): meaning ──► [forced_guess probe after IDK?] ──► reveal
```

Why (ESTIMATE [SIM §3.3, §6]; INFERENCE [LIT B4-14]):
- A reading answer after a missed meaning carries no information about meaning-and-reading
  recognition under the know-or-guess model. Asking the reading for every word (D2) spent 30 of 60
  items on readings for no gain over asking it only after a right meaning (D3/D3S: 19 of 60).
- Asking it on a fixed half of the words (D4) still credited 13–39% of the words it marked known
  without the learner knowing the reading.
- The pair is one polytomous item (0 = meaning not recognised, 1 = meaning only, 2 = both; the Tutz
  sequential model [LIT A6-38]). This removes the local-dependence problem of two items on one word
  [LIT A6-37], and a guessed "2" has probability 1/16.
- Meaning first observes the owner's target case directly: meaning through shared characters but not
  the reading ([LIT A7-46, A9-61], [PROD L1]). Cost: heritage learners who know sounds but not
  characters are under-measured on reading; `reading_after_miss` probes measure how much.
- **No feedback between the items of a word** [LIT B4-15]. Because a scored reading item follows only
  a right meaning, its appearance tells the learner the meaning was right. The meaning answer is
  already locked, so this is harmless (INFERENCE). Probes are labelled, so they do not blur this signal.

**Unscored probes (DECISION, PQ4, default on).** Each probe is shown with the label "Extra question
— not scored". Probes are never used by any estimate, BKT write or queue. At most one probe per
word, **at most 4 per placement**, at most 2 per kind. Probes do not count toward the scored-item cap
but do count toward active time.

| kind | when (draw with probability p, while budget remains) | item | measures (§20) |
|---|---|---|---|
| `recheck` | the first 1–2 items of a session: words the learner had credited meaning-and-reading in a placement ≥ 7 days earlier, whose anchor has ≥ 6 qualifying cached foils (ja) or ≥ 2 qualifying segmental foils and ≥ 2 key variants (zh) | the reading item with 3 foils disjoint from the first serving (`option_sense_ids`) | V9: false credit on readings |
| `reading_after_miss` | after a wrong or IDK meaning on a reading-ready word, p = 0.25 | the scored-format reading item | V4: reading without meaning (ω) |
| `forced_guess` | after IDK on a meaning item, p = 0.15 | the same 4 options in a new order, no IDK button, "Your best guess" | V8: partial knowledge hidden by IDK |
| `sound_pair` (ja only) | after meaning ✓ and reading ✓, when the anchor has a cached special-mora/voicing variant (E11), p = 0.5 | 2 options: the key and that foil | V6: special morae given the kana skeleton. zh tones are scored in the reading item itself (rule 4), so zh has no `sound_pair` probe |

Cost (ESTIMATE): at most 4 × ~7 s ≈ 0.5 min. The scored precision is unchanged because probes sit
outside the cap.

## 4. What the result claims

**DECISION (ADR-058).** The zh/ja headline is **meaning-and-reading recognition**: the rank-1
meaning and the reading of a word are both recognised in four-option items. For zh the reading
means the pinyin **with its tones** (rule 4). For reading-exempt words (ja kana-only, all en) it is
meaning recognition. Copy says "recognised", never "know" on its own.

Per-word groups of **this test's** answers. These are raw outcomes with guesses included, under the
heading "Your answers (guesses included)":

| group | rule | shown as |
|---|---|---|
| `both` | meaning right ∧ (reading right ∨ reading-exempt) | "Meaning and reading" (en: "Recognised") |
| `tones_not_yet` (zh) | meaning right ∧ reading = K′ (right syllables, wrong tones) | "Meaning and pinyin, not the tones" |
| `meaning_only` | meaning right ∧ reading-ready ∧ reading wrong (zh: F or F′) or IDK | "Meaning, not the reading" |
| `not_yet` | meaning wrong or IDK | "Not yet recognised" |

Probe answers never move a word between groups. ESTIMATE (PSY M7): for a guessing beginner (IDK
rate 0.3 when unknown, K_m ≈ 0.05), about 17% of asked words land in `meaning_only` by a lucky
meaning guess. That is why the heading says "guesses included" and the estimates (§5) never use
these raw counts.

## 5. Scoring model

### 5.1 v1: design-based (ADR-051 extended) — DECISION (ADR-058)

Notation: learner u, word language L, definition language D, frequency band b = 1…7
(`calibration_zipf_band`), frame size N_b (ADR-051, `knowledge_frame_bands()`), N = Σ N_b.
G = 1/4, r = G/(1 − G) = 1/3.

**Instruments (PSY M5).** Every response stores `instrument` (§13). Answers are pooled only within
one instrument and one D:
- `meaning_bare_v1`: meaning item, characters only, cross-CJK prefix stripped (placement meaning
  items; check meaning items after TASK-1091);
- `reading_v1`: ja reading item under rules 3 and 3b;
- `reading_tone_v1`: zh reading item under rule 4 (two tone pairs);
- NULL: legacy items (check definition mode with the reading shown and the prefix kept; legacy
  Readings mode).

**Samples.** All exclude probes (`probe_kind IS NOT NULL`) and take rank-1 anchors only.
- *This placement* (the result screen's first range): this session's scored items.
- *Combined* (the retake line, and My vocabulary): the latest scored answer per `anchor_vocab_id`
  within 180 days with D and instrument `meaning_bare_v1`, across placements and bare-instrument
  check sessions. Pairs come from placements only.

**Meaning counts** per band: n_b, c_b (right), s_b (IDK), w_b = n_b − c_b − s_b.
**Pair counts** per band: n'_b (pair-sample words: meaning items whose due reading item was answered,
plus exempt words) and

| word | counts as `pc` | counts as `prw` (ja) | counts as `pkt` (zh) | counts as `pf` (zh) | otherwise |
|---|---|---|---|---|---|
| reading-ready | meaning right ∧ reading right (zh: K) | meaning right ∧ reading answered wrong (not IDK) | meaning right ∧ reading K′ | meaning right ∧ reading F or F′ | n'_b only |
| reading-exempt | meaning right | meaning answered wrong (not IDK) | — | — | n'_b only |

**Estimators.** Meaning (all languages) and ja meaning-and-reading use ADR-051's form (x ∈ {m, mr};
for m: (x1, x2, n) = (c_b, w_b, n_b); for ja mr: (pc_b, prw_b, n'_b)):

    K_x,b  = x1/n − r·x2/n                                  (no clamp)
    p̃1 = (x1 + 0.5)/(n + 1.5),  p̃2 = (x2 + 0.5)/(n + 1.5)
    Var_x,b = [p̃1(1 − p̃1) + r²·p̃2(1 − p̃2) + 2r·p̃1·p̃2] / n · max(0, 1 − n/N_b)
    T_x = Σ_b N_b·K_x,b,   SD_x = sqrt(Σ_b N_b²·Var_x,b)
    lo, hi, rel', labels, rounding, one-sided "Fewer than": exactly ADR-051 rule 3–4 (z = 1.96)

**zh meaning-and-reading (with tones) — DECISION (ADR-060).** Per word y = +1 for `pc`, −1 for `pkt`,
0 otherwise (IDK, F, F′, meaning not right); exempt words do not occur in zh. Right tones are counted
against wrong tones **on the same syllables**:

    K_mr,b = (pc_b − pkt_b)/n'_b                            (no clamp)
    p̃+ = (pc_b + 0.25)/(n'_b + 0.75),  p̃− = (pkt_b + 0.25)/(n'_b + 0.75)
    Var_mr,b = [p̃+ + p̃− − (p̃+ − p̃−)²] / n'_b · max(0, 1 − n'_b/N_b)
    T_mr, SD_mr, lo, hi, labels: as above

The pseudo-count 0.25 per category (not ADR-051's 0.5) gave 96–97% coverage of 95% intervals in
simulation; 0.5 gave 98–99%, about 2 points of the pool wider than needed (E33). The ADR-051/058 form
`pc − prw/3` is **not** used for zh: on these items it credits a third of the words whose syllables
are known without their tones (+1.9..+3.3% of the pool, E33).

**Gaps** (PSY M7). Computed on the pair sample of one placement session (this placement), never
across instruments. Per word x, by gap:

| outcome | reading gap, ja: meaning not reading | reading gap, zh: meaning not pinyin | tone gap, zh: pinyin not tones |
|---|---|---|---|
| reading-ready, meaning right, reading right (zh: K) | 0 | 0 | 0 |
| zh: meaning right, reading K′ | — | 0 | 2 |
| reading-ready, meaning right, reading answered wrong (zh: F or F′) | 4/3 | 2 | −1 |
| reading-ready, meaning right, reading IDK | 1 | 1 | 0 |
| reading-ready, meaning answered wrong | −1/3 | −1/3 | 0 |
| anything else (meaning IDK; exempt words) | 0 | 0 | 0 |

    D̂_b = mean of x over the band's pair-sample words
          ja reading gap = K_m,b − K_mr,b;  zh reading gap = K_m,b − K_syl,b;  zh tone gap = K_syl,b − K_mr,b
          with K_syl,b = (pc_b + pkt_b − pf_b)/n'_b (meaning and pinyin, tones aside; guess rate 1/2)
    p̃_k = (count_k + 0.5)/(n'_b + 0.5·k_n),  k over the column's distinct x values, k_n their number
    Var_D,b = [Σ_k p̃_k·x_k² − (Σ_k p̃_k·x_k)²] / n'_b · max(0, 1 − n'_b/N_b)
    G = Σ_b N_b·D̂_b,  SD_G = sqrt(Σ_b N_b²·Var_D,b),  lo_G = G − 1.96·SD_G,  hi_G = min(N, G + 1.96·SD_G)

For zh, K_m = K_mr + tone gap + reading gap on the same sample. Each gap line is shown only when its
lo_G ≥ max(0.01·N, the rounding step); ends are rounded outward as in ADR-051. The gaps' coverage was
not simulated with the zh items (V0 measures it).

**Why the estimators are unbiased** (derivations [SIM §6]; INFERENCE under the know-or-guess
model). Let K_m = P(meaning recognised), K_mr = P(meaning and reading recognised), q = P(IDK | not
known) and g = (1 − q)/4:

    E[c − w/3]   = K_m                         for every q
    P(pc)  = K_mr + (K_m − K_mr)·g + (1 − K_m)·g²
    P(prw) = 3g·[(K_m − K_mr) + (1 − K_m)·g]
    ⇒ E[pc − prw/3] = K_mr                     for every q, also when reading and meaning skip rates differ [PSY]

zh (ADR-060): a word whose meaning is recognised (or guessed right) is in one of three reading
states: full reading R (always K), syllables only S (K or K′, ½ each), none (IDK with probability q,
else each of K, K′, F, F′ with ¼). Then P(K) − P(K′) = P(R), whatever q, so E[pc − pkt] counts words
with the meaning and the full reading. Guessed meanings contribute 0 for the same reason. And
P(K) + P(K′) − P(F or F′) = P(R) + P(S) gives K_syl.

**Known biases (stated in the method note, measured in §20):**
- (i) **Partly guessable readings.** ja: if a learner who recognises the meaning but not the reading
  can eliminate foils, the 1:3 right:wrong ratio behind `prw/3` fails. m+r is then biased up by
  +2.4..+4.0% of the pool for cognate learners (E26). zh: segmental partial knowledge cancels in
  pc − pkt, but **partial tone memory** does not: if learners who know the syllables pick the right
  tones 65% of the time, the zh count is +2.1..+2.4% high (E33). The method note says the
  meaning-and-reading range "may be a little high if readings can be partly guessed" until V9
  measures it.
- (ii) **Reading without meaning (ω).** Bias (1 − K_m)·g_m·P(R | ¬M) per band (V4).
- (iii) **IDK hiding partial knowledge** makes both ranges lower-side (ADR-051 rule 5; V8).
- (iv) **Tone variants are not real words' readings** in most cases. A learner could reject a
  variant because it "sounds wrong" without knowing the word. This is knowledge of the word's sound
  pattern, close to what the item claims (INFERENCE); V9 rechecks bound it.
- (v) **Readiness coverage** (§2 gate).

**Display guard (DECISION, PSY M8).** In truth T_m ≥ T_mr, so before rounding set
`lo_m := max(lo_m, lo_mr)` and `hi_mr := min(hi_mr, hi_m)`. In simulation, meaning coverage stays at
94%. The draft's opposite cap discarded information: on placement-only samples it bound in 25–37%
of placements and widened the headline by 3.2–3.8% of the pool.

**Eligibility (amends ADR-051 rule 1; DECISION, ADR-058).** An estimate is eligible when:
- (a) every band has n ≥ 10 (ADR-051 unchanged); **or**
- (b) the sample contains a placement with `stop_reason ∈ {precision, cap, time, exhausted}` and every
  band has n ≥ 2 (the warm-up guarantees it); **or**
- (c) for a placement's own result with `stop_reason ∈ {learner, abandoned}`: the warm-up is complete
  (2 meaning items in every band that has a ready word) and ≥ 20 scored items were answered. The
  result then adds "You ended early, so the range is wider" (E27; LRN L3).

**Labels are unchanged** (ADR-051 rule 4: Good ≥ 30 and Medium ≥ 20 answers in every band), so a
placement alone yields "Rough" or "Fewer than" (PQ9; E25).

### 5.2 "I don't know" and the guessing floor

- The guessing floor is fixed at G = 1/4 for four options (zh: 1/4 for the full reading, 1/2 for the
  syllables) and 1/2 for `sound_pair` probes. It is never estimated per item (that needs thousands of examinees [LIT A3-25]).
- "I don't know" = not known. Under **blind** guessing the expectation of `c − w/3` does not depend on
  the IDK rate; only the precision does. Real guesses are often informed, and an IDK option
  suppresses partial knowledge [LIT A2-13, A2-15]. Learners who use IDK more therefore score a little
  lower than learners who guess on the same knowledge (PSY M6). The copy makes **no neutrality
  claim** and says only: "If you have no idea, choose I don't know. If you think you know it,
  answer." `forced_guess` probes measure the hidden knowledge, and each learner's IDK share is
  stored in `result.skip_share` (V8).

### 5.3 Exam levels — none (owner, PQ2, 2026-11-18: "not at the moment"; ADR-058)

The draft's level range (cumulative frame-share ≥ 80% with 95% bounds) is **removed** from v1: the
result screen, the goal card, the result JSON and the tasks.
- **It cannot produce its promised output** (E23). The bound is computed at placement sample sizes,
  where common bands get 2–4 items and an all-correct band has a Jeffreys SD of 0.23–0.38. The lower
  bound was 0 for every simulated learner, so the copy could only ever read "Up to HSK k at most"
  or "Not yet most HSK 1 words".
- **The point rule misplaces mid-level learners** (3–41% within one level for true HSK 2–5),
  usually downward, and more items do not fix it.
- **It claims the whole level from about a third of it** (E24), on the within-band exchangeability
  assumption that ADR-054 rejected for a v1 percentage. Frame lemmas appear in a test transcript
  98.3% of the time against 22.0% for non-frame lemmas of the same Zipf (ADR-051 context).

The goal path keeps ADR-054's measured buckets. Any later level output (TASK-1090) must:
1. state the subset in its copy ("of the 290 HSK 4 words the check draws from");
2. explicitly revise ADR-054's rationale in a new ADR;
3. pass V0 gates **on the displayed copy**: within one level for ≥ 70% of simulated learners at every
   true level 1–6 (zh) and 1–4 (ja), range containment ≥ 90%, and ≥ 50% of true-level-≥ 2 learners
   with a lower bound ≥ 1;
4. state that V5 tests list against non-list words inside the frame only;
5. be re-validated after the zh pool refresh (TASK-1063).

Candidates: level strata around a stated goal level (D3L), a longer optional "level check", or the
goal level's own share with a range (S_ℓ ± 1.96·sd, named subset) (LRN L1 point 4).

### 5.4 v2: model-based IRT scoring (later; shadow first) — DECISION (ADR-057)

Not shown to learners until the gate below passes. It is computed into `result.irt_shadow` when
`PLACEMENT_IRT_SHADOW` is on.

**Meaning step** (learner u, word w, the learner's L1 group):

    b_w   = β0 + β1·(5 − z_w) + β2·λ_w + β3·c_w + β4·k_w + δ_w,      δ_w ~ N(0, σ_δ²)
    K_uw  = σ(θ_u − b_w),   θ_u ~ N(0, 1.5²)                        (μ0 fixed at 0: identifies β0)
    P(right) = K + (1 − K)·g_m,u ;  P(wrong) = (1 − K)(1 − s_m,u)·3/4 ;  P(IDK) = (1 − K)·s_m,u ;  g_m,u = (1 − s_m,u)/4

**Reading step** (only after a right meaning, reading-ready words):

    ρ_uw = σ(φ_u − r_w),   r_w = γ0 + γ1·(5 − z_w) + γ3·c_w + ε_w,   φ_u ~ N(0, 1²) per L1 group   (group means fixed at 0: identifies γ0 per group)
    P(m right, r right)     = K·ρ·(1 − g_r,u) + g_r,u·[K + (1 − K)·g_m,u]
    P(m right, r not right) = (1 − g_r,u)·[K + (1 − K)·g_m,u − K·ρ]

Notes:
- z_w is Zipf. λ_w is the exam-level residual (the word's lowest list level minus the level its Zipf
  predicts, by a linear fit over the pool; 0 if on no list). c_w is the isographic-cognate flag for
  ja-L1 learners of zh and zh-L1 learners of ja. k_w is the katakana-loanword flag for en-L1
  learners of ja.
- **Separate skip propensities** s_m,u and s_r,u: the owner's are 0.75 and 0.95 (E14). Plug-in
  ŝ = (IDK + 0.5)/(IDK + (4/3)·wrong + 1) per item kind.
- Starting values: β1 = 1.05 per Zipf point (E14, n = 1); σ_δ = 1.2 logits; the other β and γ
  N(0, 1), refitted from pooled data.
- "Meaning and reading" is never modelled as its own curve: P(both) = K·ρ ≤ K. The first simulated
  version did otherwise and over-stated counts by up to +8.7% of the pool [SIM §3.7].
- Posterior: EAP on a grid (θ 61 × φ 21; pure Python). Counts T_m = Σ_{w∈F} E[K_uw] and
  T_mr = Σ_w E[K_uw·ρ_uw] (ρ = 1 if exempt).
- Item calibration: nightly MAP of δ_w and ε_w per (vocab_id, item kind, L1 group), shrunk to the
  feature prediction with pseudocount 10 (pattern of `services/irt/calibrator.py:36, 113-115`; bounded
  L-BFGS-B `:72-110`), stored in a small table `calibration_item_params` (exposed items only).

**Selection stays v1's.** Uniform within band, so the report's design-based estimator stays valid
(PSY M9). Any switch to model-targeted selection needs its own ADR, stored per-item selection
probabilities, and Horvitz–Thompson weights in the report estimator.

**Gate to show v2 instead of v1**, per (language, L1 group): ≥ 6 exposures for ≥ 80% of frame words
in that group [LIT A4-26]; v2 beats v1 on V2 (retest) and V3 (predictive calibration) **within the
group**, with 90% coverage ≥ 0.88. The draft's "or ≥ 500 placements per language" is dropped: it could
pass on an English-L1 majority with few cognate learners.

## 6. Adaptive item selection — DECISION (ADR-057)

Strata are the 7 Zipf bands of `calibration_zipf_band` (band 1 < 3.0 and band 7 ≥ 5.5 are open-ended).
1. **Warm-up:** 2 meaning items per band. The first pass goes from the commonest band to the rarest
   (7 → 1), so a beginner starts with common words (LRN L5). The second pass uses a random band order.
2. **Allocation** (Neyman-style, response-dependent [SIM §2.3]). The next word's band is computed
   from the tallies returned by the **previous** answer call, so the server can build the next item in
   the same round trip as grading the current answer:

       h* = argmax_h [ Δ_m(h) + Δ_mr(h) ]            (en: Δ_m only)
       Δ_x(h) = N_h² · v_x,h · (1/n_h − 1/(n_h + 1)) / Var(T_x)
       v_x,h  = p̃1(1 − p̃1) + p̃2(1 − p̃2)/9 + (2/3)·p̃1·p̃2       (Jeffreys, §5.1, this session's tallies)
       zh mr:  v_mr,h = p̃+ + p̃− − (p̃+ − p̃−)²                     (§5.1, pseudo-count 0.25)

   over bands with a placement-ready word left; ties broken at random. The one-answer lag does not
   affect validity (INFERENCE): the selection still depends only on observed answers and stays uniform
   within band. Its efficiency cost was not simulated and is expected to be negligible.
3. **Word:** uniform at random among placement-ready lemmas of band h* for (L, D) that the learner
   has **not answered in any calibration session in the last 180 days** and that were not served in
   this session. Uniform draws keep the ADR-051 estimator valid and spread exposure.
4. **Pair:** after a right meaning on a reading-ready word, the next item is that word's scored
   reading item. Probes follow §3.
5. **Exhausted band:** skipped by the allocation. When every band is exhausted the test stops
   (`exhausted`).

## 7. Stopping rule and expected length — DECISION (ADR-057; owner, PQ10: "about 60")

Scored items = meaning items + scored reading items. Active time = Σ over answers of min(gap since
the previous answer, 60 s).

| | zh, ja | en |
|---|---|---|
| warm-up | 2 meaning items per band | 2 per band |
| precision exit (checked when a word completes, from the earliest stop on) | from 40 scored items: SD_m ≤ 0.073·N **and** SD_mr ≤ 0.073·N on this session's tallies (90% half-width ≤ 12% of the pool) | from 20: SD_m ≤ 0.073·N |
| cap | no new word once scored items ≥ 60 (a due reading item is still asked: at most 61) | 40 (not changed by PQ10; see PQ10) |
| time cap | no new word once active time ≥ 9 min | same |
| other ends | `exhausted`; `learner` ("Stop here and see your result"; eligible per §5.1 (c)); `abandoned` (closed after 24 h) | same |

A word is never left with a pending scored reading item. At a stop, the pre-built next meaning row
is deleted by `calibration_placement_close`.

Expected at cap 60 (ESTIMATE, measured pace E13; probes add ≤ ~0.5 min). zh rows are from the
scored-tone simulation (E33), ja rows from the cap-60 re-run (E31):

| population | scored items mean | stopped early | minutes mean (p95) | 95% half-width, meaning / m+r (% of pool; words) |
|---|---|---|---|---|
| zh, English L1 (tones scored) | 56.4 | 29% (mostly beginners) | 6.4 (7.1) | ±15.6 / ±15.2 (≈ ±565 / ±550) |
| zh, Japanese L1 (tones scored) | 60.4 | 0% | 7.0 (7.1) | ±17.1 / ±17.5 (≈ ±620 / ±630) |
| ja, English L1 | 56.8 | 21% (beginners 52%) | 6.4 (7.0) | ±15.0 / ±13.8 (≈ ±475 / ±440) |
| ja, Chinese L1 | 60.2 | 0% | 6.9 (7.0) | ±16.0 / ±15.3 (≈ ±510 / ±485) |
| en (not simulated) | 40 | — | ≈ 4.4 (INFERENCE: 40 × 6.57 s) | ≈ ±15–16 meaning (INFERENCE from D1S at 40 items, ±12.7–13.6% at 90%) |

The 9-minute time cap sits about 2 minutes above the simulated p95, so it binds only for learners
much slower than E13 (newcomers probably are, INFERENCE). The 50-item figures this replaces are in
E22. For ja, a launch design that gives every non-kana word a reading item widens the meaning
half-width by about 1 point (E29). Copy: "about 7 minutes" (zh, ja), "about 5 minutes" (en). Scoring
tones widens the zh m+r range by about 2 points of the pool against syllables-only items (E31 vs
E33); that is the cost of the stronger claim.

INFERENCE: an absolute-width rule rarely stops cognate learners early, because large counts carry
large absolute SDs. A ±6% target is out of reach under 90 items [SIM §0.1]. The cap is the real
stopping rule.

## 8. What the learner sees

**Before** (onboarding entry only, PQ7): "Have you studied {language} before?" with "Yes", "Only a
few words" and "No". "Yes" opens the placement, which the learner can still skip. The other two
answers skip it and **store nothing**. The other entry points (§15) offer the placement whenever the
learner has no placement for that language, so it is offered again later without any new state.
Elsewhere the placement starts directly.

**During** (`templates/placement.html`):
- **Intro:** the time ("about 7 minutes"; en "about 5 minutes"), "If you have no idea, choose I don't know. If you think you
  know it, answer.", and Start.
- **Item card:** the word without a reading; "Choose the meaning", "Choose the pinyin" or "Choose the
  reading"; 4 options; "I don't know"; keys 1–4 and 0. Probes carry the badge "Extra question — not
  scored"; `forced_guess` hides "I don't know" and says "Your best guess"; `sound_pair` (ja) shows 2
  options.
- **Combined reveal:** the word, its reading and meaning, ✓/✗ per question, and the chosen wrong
  option. All ✓ auto-advances after 450 ms (as the check); otherwise "Next word".
- **Progress:** "about N minutes left", computed from the remaining scored items × the session's
  mean seconds per item, capped by the time cap.
- **"Stop here and see your result"**, visible once eligibility (c) holds. Before that, "End now"
  asks for confirmation and says "Not enough answers yet for a result — answer {k} more, or leave and
  come back within 24 hours".

**Result** (`result` JSON, frozen; blocks in this order):

| block | zh / ja | en |
|---|---|---|
| 1. Your answers (guesses included) | "Of the {n} words you were asked: {both} meaning and reading · [zh: {tones_not_yet} meaning and pinyin, not the tones ·] {meaning_only} meaning, not the reading · {not_yet} not yet recognised". Each group is tappable and lists its words; actions "Practise these readings" (tones_not_yet, meaning_only) and "Learn these" (not_yet) | "{both} recognised · {not_yet} not yet recognised" |
| 2. Range | "Across the {N} {language} words the check draws from, you recognised the meaning and the reading of about {lo_mr}–{hi_mr}" + label + band strip (dot strip, [LIT A10-66]); lo = 0 → "Most of the check's words are still new to you (fewer than {hi} of {N})" | "…you recognised the meaning of about {lo_m}–{hi_m}" |
| 3. Gaps (each only when its lo_G ≥ threshold, §5.1) | zh: "You also recognised the meaning and the pinyin, but not the tones, of about {lo_T}–{hi_T} more." Then (zh, ja): "You also recognised the meaning, but not the reading, of about {lo_G}–{hi_G} more." | — |
| 4. Retake (when a previous eligible placement for (L, D) exists and the frame size changed by ≤ 1%) | "This placement: {lo}–{hi} · Previous ({date}): {lo}–{hi} · {clearly up / clearly down / not clearly different}" (ADR-053 rule on the m+r headline (en: meaning): clearly changed when \|Δ\| ≥ 1.96·sqrt(SD_prev² + SD_now²)), then "Combined with your earlier answers: {lo}–{hi}" | same, meaning |
| 5. Next steps | "Practise these readings" · "Learn these" · "Start today's session" · "Narrow your range: continue the vocabulary check" | last three |
| 6. How this works | recognition among four; guesses are subtracted on average; IDK counts as not known; why a range; for zh, the reading includes the tones (two options share the right syllables, only one has the right tones); "the meaning-and-reading range may be a little high if readings can be partly guessed"; the count is of the check's word pool; the result matches My vocabulary on the day taken | same, without readings |
| flags | ended early: "You ended early, so the range is wider." Fast: "You answered very quickly; this result may not reflect what you know." | same |

On a first placement with no other same-instrument answers, the combined range equals this placement's
range and is not repeated. The "Practise these readings" and "Learn these" actions start today's session
(`/session`). Those words were admitted by the evidence write (§10) and appear within the learner's daily
new-word budget. The button text is followed by "(up to {k} today)" when the group exceeds the remaining
budget.

`result` (jsonb, ≤ 2 KB):
```json
{"version": 1, "word_language_id": 1, "definition_language_id": 2, "instrument": "meaning_bare_v1",
 "stop_reason": "cap", "ended_early": false, "fast": false, "skip_share": 0.41,
 "items": {"scored": 60, "meaning": 39, "reading": 21, "probes": 3}, "active_seconds": 408,
 "words": {"asked": 39, "both": 12, "tones_not_yet": 3, "meaning_only": 4, "not_yet": 20},
 "frame_n": 3623,
 "this": {"m": {"lo": 900, "hi": 1700, "label": "rough"}, "mr": {"lo": 500, "hi": 1100, "label": "rough"},
          "tone_gap": {"lo": 60, "hi": 420}, "gap": {"lo": 120, "hi": 650} },
 "combined": null,
 "previous": null,
 "seen": false}
```
`gap` and `tone_gap` are null when below the threshold; `tone_gap` and `words.tones_not_yet` exist for
zh only; `mr` and `gap` are null for en; `combined` is null when it
equals `this`; `previous` holds `{session_id, ended_at, mr|m: {lo, hi}, verdict}`.

**Goal-path report** ([[features/knowledge-report]], TASK-1072): the hero shows the same ranges in the
same order. The goal card has **no level line**; its ring and level path keep ADR-054's measured
buckets. TASK-1094 adds a segment "answered in a placement, not yet checked" to the level bars (Hack
Chinese's assumed-known segment [PROD H5], LRN L13), for every tier. It also changes the demo's hero
copy "After about 70 answers you get a range" for the placement path.

## 9. Feeding the Knowledge Report — extends ADR-051, does not replace it (ADR-058)

- **One estimator, shared inputs.** A new STABLE SQL function `knowledge_calibration_inputs` (§14)
  returns D, the instrument, meaning bands, pair bands, gap bands, all-time counts and dates.
  `knowledge_report_summary` (TASK-1036) embeds it instead of computing its own calibration block, and
  `finish()` calls it. Both then call `knowledge_estimate`, so the combined range on the result screen
  and the report's hero agree on the day the placement is taken.
- **Report D and instrument rule (PSY M5, M15).** If the 180-day window holds a placement for L with
  an eligible result, the report uses **that latest placement's D** and instrument `meaning_bare_v1`.
  Its meaning bands come from all scored `meaning_bare_v1` answers with that D, from placements and
  converted check sessions, and its pair bands from placements. Otherwise ADR-051 rule 1 is unchanged
  (legacy check answers, D = the definition language with the most answers). Consequence: a learner with
  many legacy check answers, such as de6fd05b (Medium, 850–1,400), sees the report switch to the
  placement's instrument (usually Rough) until the check moves to the bare instrument (TASK-1091).
- **Changes to report tech §2.6:**
  - the instrument and D rule above;
  - a second range (`estimate_mr`) for zh/ja from pair bands;
  - the gap line;
  - the display guard and the eligibility amendment of §5.1;
  - the hero copy order of §8;
  - snapshots (ADR-053) store pair and gap bands next to the meaning bands (zh pairs are
    [n', pc, pkt, pf]: 7 × 4 integers) and the instrument.
- **Changes to report §2.4:** a new evidence state between `checked` and `not_checked`,
  `placement_only` ("Placement answer only"), with the rule
  `placement_correct + placement_wrong > 0 AND checks_correct + checks_wrong = 0`. The Pro row lead is
  "Placement ✓ meaning ✓ reading ✗ · 3 Nov" (from the ledger). The rated-known rule is unchanged, so
  placement evidence alone can never satisfy it (ADR-059).
- **Changes to report §2.8/§2.8a:** none. There is no placement level line (owner, PQ2), and OQ34 is
  unchanged.
- **Growth (ADR-053):** retakes are disjoint, so the "clearly changed" comparison of consecutive
  placements is valid; the retake result screen shows it directly (§8 block 4).

## 10. Writing to the knowledge model — evidence kind (ADR-059, accepted; owner approved PQ5 2026-11-18)

Written once per session at `finish()`, including sessions closed as `abandoned`, through
`update_vocabulary_from_placement_batch(p_user_id, p_items jsonb)`. The session is claimed through
`bkt_applied_at`, as `services/calibration_service.py:679-688` does.

| word outcome (scored items only) | BKT write | counters | practice admission |
|---|---|---|---|
| reading-ready: meaning ✓, reading ✓ | correct | `placement_correct` +1 | none (probably known; normal review) |
| reading-ready: meaning ✓, reading ✗ (zh: K′, F or F′) or IDK | **none** | none | **A2r** (reading gap; for zh K′ this is a tone gap) |
| meaning ✗ or IDK (any word) | wrong | `placement_wrong` +1 | **A2** (as a missed check answer) |
| exempt (ja kana-only, en): meaning ✓ | correct | `placement_correct` +1 | none |
| probes | never | never | never |

- **BKT update** = the check's (`bkt_update_word_test`: slip 0.05, guess 0.25, transit 0.05; Zipf step
  prior; duplicate merge with `bool_or`). It is written on the **anchor sense row**, as the check
  writes (ADR-047 problem 3 unchanged; PQ21). It never increments `word_test_correct` or
  `word_test_wrong`, so placement answers can never make a word "rated known after a direct check".
- **Admission maps to the native rank-1 sense** (PQ21, LRN L6). For A2 and A2r the anchor sense is
  mapped to the native rank-1 sense of the same `vocab_id` (definition language = L,
  `definition_level = 'standard'`, `sense_rank = 1`) **before** the status veto and the supply gate.
  Exercises live on that row (E16); the gloss row has none.
- **Ledger read.** `new_word_admission._calibration_ledger` (`services/practice/new_word_admission.py:566-600`)
  is extended to sessions with `mode = 'placement'` and `bkt_applied_at` set:
  - **A2** takes scored meaning items with `is_correct = false`;
  - **A2r** takes scored meaning items with `is_correct = true` on reading-ready words whose paired
    scored reading item is not correct.
  Both use the same age limit (`CALIBRATION_EVIDENCE_MAX_AGE_DAYS`, 90), the same veto and the same
  daily budget (ADR-033). A2r candidates are ranked with A2, alternating when both exist.
- **Reading practice.** A2r words enter through the new-word path. Its intro drill opens with the
  reading formats for cjk (`read_typed`, `services/intro_drill.py:47-48`). The zh reading for those
  words exists only on the native row, in diacritic form, so **TASK-1082 is a zh launch dependency**:
  it fixes `intro_drill._reading` to derive the numbered form from diacritics (E17).
- **Never inferred:** no evidence is written for words the learner was not asked (ADR-051 rejects
  extrapolating rows).
- **Fast-flagged sessions** still write evidence (the learner's own data) but are excluded from
  validation.

## 11. Test selection and ELO

- **v1: placements do not feed `pooled_ability` and do not call the guarded rating writer** (PSY M16,
  PQ19). `_fit_points` scores a skip as a wrong 1-in-4 guess (`services/calibration_service.py:439-448`,
  floor `:41-43`). For a heavy skipper that moves the curve 0.4–0.8 Zipf (MEASURED on one learner
  [AUD §1.7]). The placement encourages IDK and adds about 39–46 meaning items per session at cap 60.
- After the report's OQ33 is answered (TASK-1083):
  - either placement meaning items enter the fit through a **skip-aware likelihood**
    (`P(right) = K + (1 − K)·(1 − ŝ)/4`, with IDK and wrong both ∝ 1 − K), and `write_calibration_state`
    and `apply_calibration_to_ratings` (G1–G6, `:612-639`) run at `finish()` for sessions that are not
    flagged fast;
  - or placements stay out of the fit.
- INFERENCE: response-adaptive selection does not bias a likelihood fit, because selection depends only
  on observed answers. The `expected_sd` lookup (`:79-99`) assumes non-adaptive sampling; TASK-1087
  measures its error on placement-shaped samples.

## 12. Retakes and item exposure

- **Disjoint retakes:** a placement never serves a scored lemma the learner answered in any
  calibration session (check or placement, any item kind) in the last 180 days (= ADR-051's window).
  Index `(user_id, anchor_vocab_id) WHERE answered_at IS NOT NULL`. `recheck` probes are the only
  exception, and they are unscored.
- **Supply:** a placement uses about 2–10 lemmas per band at cap 60. The smallest placement-ready bands
  are ja band 7 (68 today) and zh band 7 (168) [AUD §2.1], so at least about 6 disjoint retakes fit in
  the smallest band. A band the learner has exhausted is skipped; its finite-population factor goes to 0.
- **Pooling:** the combined line pools same-instrument answers (latest per lemma, 180 days), so each
  retake narrows the combined range. The retake screen leads with this placement against the previous
  one (§8).
- **Exposure:** uniform within-band draws spread exposure; nothing more is needed for v1 (no security
  stake).
- **Rate:** at most 3 placement starts per (user, language) per day (PQ8).

## 13. Database Impact

One migration, `migrations/calibration_placement.sql` (+ rollback), owner-applied. All additive.

```sql
-- calibration_sessions
ALTER TABLE public.calibration_sessions DROP CONSTRAINT calibration_sessions_mode_chk;
ALTER TABLE public.calibration_sessions ADD CONSTRAINT calibration_sessions_mode_chk
  CHECK (mode IN ('definition', 'pronunciation', 'placement')) NOT VALID;
ALTER TABLE public.calibration_sessions VALIDATE CONSTRAINT calibration_sessions_mode_chk;
ALTER TABLE public.calibration_sessions
  ADD COLUMN IF NOT EXISTS stop_reason text NULL
    CHECK (stop_reason IS NULL OR stop_reason IN ('precision','cap','time','exhausted','learner','abandoned')),
  ADD COLUMN IF NOT EXISTS result jsonb NULL;            -- frozen result (≤ 2 KB)

-- calibration_responses
ALTER TABLE public.calibration_responses
  ADD COLUMN IF NOT EXISTS item_kind text NULL
    CHECK (item_kind IS NULL OR item_kind IN ('meaning','reading','sound_pair')),
  ADD COLUMN IF NOT EXISTS probe_kind text NULL
    CHECK (probe_kind IS NULL OR probe_kind IN ('recheck','reading_after_miss','forced_guess','sound_pair')),
  ADD COLUMN IF NOT EXISTS instrument text NULL
    CHECK (instrument IS NULL OR instrument IN ('meaning_bare_v1','reading_v1','reading_tone_v1')),
  ADD COLUMN IF NOT EXISTS pair_response_id bigint NULL
    REFERENCES public.calibration_responses(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS option_sense_ids integer[] NULL,   -- placement: option sense ids in display order
  ADD COLUMN IF NOT EXISTS key_position smallint NULL,        -- placement: 0..3 (0..1 for sound_pair); never sent with the item
  ADD COLUMN IF NOT EXISTS option_roles text[] NULL,          -- zh reading items: {'K','KT','F','FT'} in display order; never sent
  ADD COLUMN IF NOT EXISTS option_texts text[] NULL,          -- zh reading items: the 4 displayed pinyin strings (K′, F′ have no sense id)
  ADD COLUMN IF NOT EXISTS chosen_position smallint NULL;     -- placement: 0..3, NULL for IDK (a generated option has no chosen_sense_id)
CREATE INDEX IF NOT EXISTS idx_calibration_responses_user_vocab_answered
  ON public.calibration_responses (user_id, anchor_vocab_id) WHERE answered_at IS NOT NULL;

-- zh tone inventory (TASK-1092, ADR-060): syllable → tones that occur in zh dictionary readings
CREATE TABLE IF NOT EXISTS public.calibration_zh_tone_inventory (
  base  text PRIMARY KEY,                 -- toneless syllable, lower case, ü as 'u:' (≈ 382 rows, ≈ 15 KB)
  tones smallint[] NOT NULL,              -- attested full tones 1..4
  built_at timestamptz NOT NULL DEFAULT now());
REVOKE ALL ON public.calibration_zh_tone_inventory FROM PUBLIC, anon, authenticated;

-- user_vocabulary_knowledge (TASK-1081, ADR-059; separate migration)
ALTER TABLE public.user_vocabulary_knowledge
  ADD COLUMN IF NOT EXISTS placement_correct smallint NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS placement_wrong   smallint NOT NULL DEFAULT 0;
```

- `item_kind NULL` marks a legacy row, whose kind is the session's mode. Placement rows always set
  `item_kind` and `instrument` (probes: `instrument` of their format, plus `probe_kind`).
- **No option rows for placement items.** `calibration_response_options` keeps serving the check.
  The option sense ids are packed in `option_sense_ids` (NULL entries for K′ and F′); `key_position`,
  `option_roles`, `option_texts` and the array sit on a table with no client privilege
  (`migrations/security_calibration_answer_keys.sql`). The chosen role of a zh reading answer is
  `option_roles[chosen_position + 1]`.
- `calibration_anchor_pool` is not altered; readiness is computed at serve time from the pool and the
  packed cache (PK lookups).
- `user_calibration_state` is unchanged (placements do not write it in v1, §11).

**Byte budget** (ESTIMATE from [AUD §5.1]'s measured tuple sizes):

| item | bytes |
|---|---|
| placement response row (≈ 100 B tuple + ~24 B ids array + kinds + overhead + 4 index entries) | ≈ 0.25 KB (zh reading rows ≈ 0.35 KB with texts and roles) |
| one placement: ≤ 61 scored + ≤ 4 probe rows + session row with `result` | ≈ 18 + 2 = **≈ 20 KB** |
| new BKT rows for a new learner (≤ 46 meaning items × ≈ 0.2 KB) | ≈ 9 KB |
| **per placement, all-in** | **≈ 25–30 KB** → 100 placements ≈ 3 MB; 1,000 ≈ 30 MB |
| zh tone inventory | ≈ 15 KB |
| new index on today's 1,349 response rows | < 0.1 MB |
| ja pool refresh + ~840 pronunciation cache rows (TASK-1075) | ≈ 0.2 MB [AUD §5.1] |
| UVK counter columns (fast default; ~1.1k rows) | ≈ 0 |

The database is 513.5 MB against a 500 MB-or-MiB Free cap (report OQ13). Placement growth is small and
per use; ADR-049's content drop is the planned relief (PQ15). The check's prefetch waste does not
occur: at most one pending unanswered row exists per open placement, deleted at close.

## 14. API / RPC Surface

All new functions: `SET search_path = public, pg_temp`; `SECURITY DEFINER` where they write;
`REVOKE ALL … FROM PUBLIC, anon, authenticated; GRANT EXECUTE … TO service_role` in the same file
(`migrations/CLAUDE.md`, lint `tests/test_migration_security_lint.py`). Every function that takes a
session checks that `p_user_id` owns it.

### `calibration_placement_ready_counts(p_word_language_id smallint, p_definition_language_id smallint): jsonb`
- **Purpose:** the launch gate (§2) and monitoring.
- **Returns:** `{"frame": N, "ready": n, "bands": [{band, frame_n, ready_n, meaning_ready_n, reading_ready_n, exempt_n, excluded_rule5_n, excluded_rule3b_n, excluded_tone_n, ready_mean_zipf, unready_mean_zipf, ready_share_len3, unready_share_len3}×7]}`. List-level shares are added by the Python gate script from the ADR-054 file.
- **Errors:** none (empty bands for an unknown pair). STABLE, read-only.

### `calibration_placement_next_item(p_user_id uuid, p_session_id uuid, p_band smallint, p_exclude_days integer DEFAULT 180): jsonb`
- **Purpose:** draw and build a meaning item in band `p_band`. It is used for the first item and on resume.
- **Behaviour:** random placement-ready lemma of band `p_band` for the session's (L, D), rank-1
  anchor, not answered by the user in the last `p_exclude_days` days, not served in this session.
  Options are the key plus the first 3 cached definition foils, rule 5 applied, shuffled. Inserts one
  `calibration_responses` row (`item_kind 'meaning'`, `instrument 'meaning_bare_v1'`,
  `option_sense_ids`, `key_position`, `zipf_band`, `anchor_zipf`) and bumps `items_served`.
- **Returns:** `{response_id, vocab_id, lemma, band, kind: 'meaning', probe_kind: null, options: [4 texts], idk_allowed: true}`.
  It never contains the key or a reading. When the band has no word left: `{exhausted: true}`.
- **Errors:** `P0002` session not found (wrong user or session, mapped to 404); `22023` session closed. VOLATILE.

### `calibration_placement_answer(p_user_id uuid, p_session_id uuid, p_response_id bigint, p_position smallint, p_latency_ms integer, p_next_band smallint, p_draws jsonb): jsonb`
- **Purpose:** grade one answer and, in the same call, build the item that follows.
- **Grading:** checks ownership, that the item is not already answered, and that
  `p_position IS NULL OR 0..3` (0..1 for `sound_pair`). Latency is clamped to 0..600,000. Sets
  `chosen_sense_id` (NULL for IDK), `is_correct`, `latency_ms`, `answered_at`, and bumps the session
  counters.
- **What comes next.** `p_draws = {u_probe, u_seed}` are uniform draws from the injected RNG.
  `p_next_band` is NULL when Python has decided that no new word may start (cap or time). The branches:
  1. Answered meaning item (scored), right, reading-ready → build the scored reading item (`pair_response_id`):
     ja rules 3 and 3b, `instrument 'reading_v1'`; zh rule 4 (K, K′, F, F′ shuffled with `u_seed`;
     `option_roles`, `option_texts`), `instrument 'reading_tone_v1'`.
  2. Scored meaning IDK, `u_probe < 0.15`, budget left → `forced_guess` probe (same options, new order,
     `idk_allowed: false`).
  3. Scored meaning wrong or IDK on a reading-ready word, `u_probe < 0.25`, budget left →
     `reading_after_miss` probe.
  4. ja: scored reading right, the anchor has a special-mora/voicing foil, `u_probe < 0.5`, budget
     left → `sound_pair` probe. (zh has no `sound_pair` probe; tones are in the scored item.)
  5. Otherwise the word is complete: return `reveal` and, if `p_next_band` is not NULL, build the next
     meaning item in that band (if the band is exhausted, the nearest band with words left, then any;
     `exhausted: true` if none).
  At most one probe per word; budget ≤ 4 per session and ≤ 2 per kind (counted from the session's rows).
- **Returns:** `{answer: {is_correct, skipped, kind, probe_kind, role}, reveal: {lemma, reading, meaning, parts: [{kind, probe_kind, chosen_text, key_text, is_correct, tone_only_miss}]} | null, next_item: {...as next_item} | null, exhausted: bool, tallies: {m: [ [n,c,w] ×7 ], mr: [ [n,pc,prw] ×7 ] (ja) | [ [n,pc,pkt,pf] ×7 ] (zh), scored, probes, active_ms, median_latency_ms, warmup_done}}`. `role` and `tone_only_miss` (chosen K′) are returned only after the answer is graded.
- **Errors:** `22023` already answered, invalid position, or a response not in this session; `P0002`. VOLATILE.

### `calibration_placement_close(p_user_id uuid, p_session_id uuid, p_reason text): jsonb`
- Deletes the session's unanswered row (at most one), sets `ended_at` and `stop_reason`, and returns
  the final tallies. Idempotent: a closed session returns its stored values.

### `calibration_placement_close_stale(p_user_id uuid, p_older_than interval DEFAULT '24 hours'): uuid[]`
- Closes the user's open placements whose last activity is older than the interval, with reason
  `abandoned`, and returns their ids. The Python caller runs `finish()` on each: the result is frozen if
  eligible (§5.1 (c)) and the evidence is written. The nightly job (§21) calls it for all users with
  `p_user_id = NULL` (service role only).

### `knowledge_calibration_inputs(p_user_id uuid, p_language_id smallint, p_as_of timestamptz DEFAULT now(), p_window_days integer DEFAULT 180, p_definition_language_id smallint DEFAULT NULL, p_session_id uuid DEFAULT NULL): jsonb`
- **Purpose:** the calibration block of report §2.6, extended by §5.1 and §9.
- **Behaviour:** with `p_session_id`, counts only that session's scored items. Otherwise it applies the
  report D and instrument rule (§9); `p_definition_language_id`, when given, overrides D.
- **Returns:** `{definition_language_id, instrument, bands: [ [n,s,c] ×7 ], pairs: [ [n',pc,prw] ×7 ] (ja) | [ [n',pc,pkt,pf] ×7 ] (zh) | null, gap: [ [n',a43,b1,cm13] ×7 ] (ja) | [ [n',f,idk,cm13,kt] ×7 ] (zh) | null, alltime_n: [7], first_at, last_at, placement_eligible: bool, stop_reasons: [...], rated_known_in_frame}`.
- STABLE, `SECURITY INVOKER`, service role only. `knowledge_report_summary` embeds it (TASK-1036 adjusted).

### `update_vocabulary_from_placement_batch(p_user_id uuid, p_items jsonb): jsonb`
- Like `update_vocabulary_from_word_tests_batch` (`migrations/bkt_word_test_batch.sql`), but it
  increments `placement_correct` and `placement_wrong`, not `word_test_*`. `p_items` = `[{sense_id, is_correct}]`
  for the rows of §10 that write. Returns `{updated, inserted}`.

### `calibration_zh_tone_variants(p_pronunciation text, p_vocab_id integer): text[]` (TASK-1092, ADR-060)
- **Purpose:** every valid tone variant of a zh reading under rule 4, in display (diacritic) form.
- **Behaviour:** parse the display syllables (tone from the mark, 5 if none); for each syllable with a
  full tone, the alternatives are the other full tones listed for its base in
  `calibration_zh_tone_inventory`; keep tone 5 and syllables written 一 or 不 (aligned with the lemma's
  characters when the counts match) unchanged; form every combination except the original; drop
  combinations whose only changes are 3→2 before a tone-3 syllable, and any equal to a reading of
  `p_vocab_id` in `dim_word_senses`; re-mark with the standard rule (a or e takes the mark; in ou the o;
  otherwise the last vowel; ü kept). Capped at 16 variants.
- **Returns:** text[] (empty when none). STABLE. Must match the reference implementation
  (`wiki/evaluations/vocab-placement-research-2026-11-18/tones/tone_cover.py`) on every pool reading.

### `calibration_refresh_zh_tone_inventory(): integer` (TASK-1092)
- Rebuilds the inventory from native zh `dim_word_senses` readings; returns the row count. Run with the
  zh pool refresh (TASK-1063) and after any zh sense backfill. SECURITY DEFINER, service role only.

### Changed SQL (bug fixes, LIVE-DB)
- `calibration_normalise_pronunciation` and `calibration_syllable_count` (zh): derive numbered pinyin
  from diacritics when no `(…)` suffix exists (tone 1–4 from the mark, 5 for unmarked syllables), so
  length and syllable count work on all 8,110 zh readings (E7). This is a prerequisite for TASK-1063 and
  any zh refill (TASK-1074).
- `calibration_refresh_anchor_pool`: also exclude katakana-only lemmas (`^[ァ-ヿー・]+$`) from
  `has_pronunciation` (E8; TASK-1075).
- `pronunciation_distractors` (ja): candidates must match the anchor lemma's visible-kana pattern
  (rule 3b), so refills produce consistent foils (TASK-1075).

### Flask routes (`routes/calibration.py`, `calibration_bp`)

Decorators as on the existing routes: `@supabase_jwt_required`, `@api_errors(...)`, ownership 404 through
the RPC. No feature switch (owner, 2026-11-23; the earlier `PLACEMENT_ENABLED_LANGS` flag was removed): always on
for zh, en and ja (`calibration_placement.PLACEMENT_LANGUAGES`); any other language id answers 400/404.

| endpoint | body / query | response |
|---|---|---|
| `POST /api/calibration/placement/start` | `{word_language_id, definition_language_id}` (validated against `_SUPPORTED_LANGUAGE_IDS`, D as the check's start, `routes/calibration.py:56-63`) | 201 `{session_id, item, progress: {scored: 0, cap, minutes_left}, resumed: bool}`. An open placement for the pair younger than 24 h is resumed, and its pending item is re-sent. 429 over the daily limit |
| `POST /api/calibration/placement/answer` | `{session_id, response_id, position: int\|null, latency_ms?: int}` | 200 `{answer, reveal\|null, next_item\|null, done: bool, result\|null, can_stop: bool, progress}` |
| `POST /api/calibration/placement/end` | `{session_id}` | 200 `{result}` (`stop_reason` `learner`), or 200 `{not_enough: true, needed: k}` (the session stays open) |
| `GET /api/calibration/placement/result` | `session_id` | 200 `{result}` (frozen) |
| `GET /api/calibration/placement/latest` | `word_language_id` | 200 `{result\|null, unseen: bool}`; marks the result seen |

`services/calibration_placement.py`: `start`, `answer`, `end`, `finish(session, reason)`, `result`,
`latest`, `close_stale_for(user_id | None)`.

`services/placement_design.py` (pure, no I/O):
- `CONFIG` (version 1): warm-up 2; earliest stop 40/20; cap 60/40; time cap 540 s; `SD_RATIO = 0.12/1.645`;
  zh pair pseudo-count 0.25; probe p = {forced_guess 0.15, reading_after_miss 0.25, sound_pair 0.5 (ja)}; probe budget 4 per session and
  2 per kind; recheck delay 7 days; exclude 180 d; fast median 800 ms over ≥ 10 answers; resume 24 h.
- `warmup_order(rng)`, `next_band(tallies, frame, rng)`, `should_stop(tallies, frame, config) -> reason|None`,
  `eligible(tallies, stop_reason)`, `word_groups(rows)`, `minutes_left(tallies, config)`.

`services/vocabulary/knowledge_estimate.py` (TASK-1035) gains `pair_counts(...)`,
`estimate_range_pairs(...)` (ja: same formula, second input), `estimate_range_tone_pairs(...)` (zh: §5.1,
ADR-060), `gap_range(...)` (ja gap, zh reading gap, zh tone gap), `apply_guard(m, mr)`, the eligibility
amendment, and `compare(prev, now)` (the ADR-053 rule).

Rate limits (`web/rate_limits.py`, `ENDPOINT_LIMITS`, key `user_or_ip`):
- `'calibration.placement_start': (('10 per day', user_or_ip),)`;
- `'calibration.placement_answer': (('120 per minute', user_or_ip),)`.

The per-language cap of 3 starts per day (PQ8) is enforced in `calibration_placement.start()` by
counting the user's placement sessions for the pair since midnight UTC (429 `RATE_LIMITED`).

## 15. Component Specification (UI)

### `templates/placement.html` (registered in `web/pages.py` next to `('/calibration', …)`, `:23`)
- Task-mode page (Back header) that reuses `.cal-page` styles (`static/css/redesign/trainers.css`). New
  classes only: `.plc-reveal`, `.plc-probe-badge`, `.plc-progress`, `.plc-result`, `.plc-groups`, `.plc-band`.

### `static/js/pages/placement.js` (classic IIFE, like `static/js/pages/calibration.js`)
- **State:** `sessionId, lang, defLang, item, pendingWord` (the word's parts held until its reveal),
  `progress`, `result`, `canStop`, `awaitingAdvance` (one `advance()` guard, as TASK-775).
- **Effects:**
  - key handler 1–4 / 0 (IDK, hidden on `forced_guess`) / Enter (Next);
  - no reading line on meaning items;
  - the probe badge whenever `item.probe_kind` is set;
  - the word's `lang` attribute set for fonts;
  - latency measured from render to click (`performance.now()`);
  - the tapped option is highlighted immediately while the request is in flight.
- **Queries:**
  - `authFetch` POST start, answer and end; GET result and latest;
  - on load, `latest` shows an unseen abandoned result first;
  - on 404 (flag off) the page shows "not available";
  - on a network error the same answer is retried once (the RPC rejects a double answer, so a retry is
    safe).
- **Result:** the blocks of §8. Word groups expand in place; the actions link to `/session`; the band
  strip is drawn as inline SVG with a dot per 5% of the pool.

### Onboarding gate (TASK-1085)
Built 2026-11-27 (PQ7 answered). The study language is chosen on `/language-selection`, the page after
`/welcome`, so the gate lives there:
- `static/js/pages/onboarding.js`: "Get Started" sets `sessionStorage['ld_onboarding'] = '1'` (per tab).
- `templates/language_selection.html`: `#langGate` (hidden card under the three languages; a `.ld-seg`
  radiogroup of `[data-studied="yes|few|no"]`; `#langGateHint`) and `#placement-btn` (hidden link, first
  in the dock).
- `static/js/pages/language-selection.js` (`renderGate`): only when the mark is set and a language is
  selected, the card shows "Have you studied {language} before?" (`onboarding.studied_before`, language
  name from `lang_select.name_*`). "Yes" shows `#placement-btn` ("Take the placement test",
  `onboarding.placement_cta`, href `/placement?lang=<id>`) as the main action, the hint
  (`onboarding.placement_hint` with `{time}` = `placement.intro_time_en` for English, else
  `placement.intro_time_cjk`), turns "Start Daily Session" into a ghost button (the skip) and hides
  "Browse tests". "Only a few words" and "No" restore the page. Answering is optional: "Start Daily
  Session" is enabled as soon as a language is chosen.
- **Nothing is stored or sent**: the answer lives in a variable. Leaving the page by any of the three
  actions saves `selectedLanguageId` as before and removes the mark, so a later visit to the page (or a
  returning learner on a new device, who comes from `/login`) never sees the gate.
- Test: `tests/unit/language-selection-gate.test.js` (5 cases).

### Entry points (TASK-1085)
Built 2026-11-27 (all but onboarding); each is a plain link to `/placement`, which opens on the study language, and each is always shown (also after a placement, so it doubles as the retake entry):
- Onboarding (above).
- The report's empty state and its "not enough answers" estimate state → "Take the 7-minute placement" (`knowledge.state.empty_placement`; `templates/knowledge.html`, `static/js/pages/knowledge.js`), the primary button ahead of the vocabulary check.
- The calibration page: "Short placement instead" (`calibration.placement_instead`; a quiet link under the mode toggle in `templates/calibration.html`).
- A Me-hub row "Vocabulary placement" under My vocabulary (`#mePlacementRow`, `placement.title` / `me.placement_sub`; `templates/profile.html`).

## 16. i18n

Flat keys in `static/i18n/{en,es,ja,zh}.json`, all four locales in the same task, with the parity test
(`tests/test_i18n_locale_files.py`):
- **Page and intro:** `placement.title`, `.intro_time_cjk` ("about 7 minutes"), `.intro_time_en` ("about 5
  minutes"), `.intro_idk_hint`, `.start`.
- **Items:** `.choose_meaning`, `.choose_pinyin` ("Choose the pinyin"),
  `.choose_reading_ja`, `.idk`, `.best_guess`, `.probe_badge` ("Extra question — not scored"),
  `.sound_pair_prompt` (ja), `.next`.
- **Ending:** `.stop_here`, `.end_confirm`, `.not_enough`, `.minutes_left`, `.reveal_meaning`, `.reveal_reading`.
- **Result:** `.answers_heading` ("Your answers (guesses included)"), `.group_both`, `.group_tones_not_yet`, `.group_meaning_only`,
  `.group_not_yet`, `.group_recognised_en`, `.practise_readings`, `.learn_these`, `.up_to_today`,
  `.result_mr`, `.result_m`, `.result_m_en`, `.result_fewer`, `.result_tone_gap`, `.result_gap`, `.retake_this`,
  `.retake_previous`, `.retake_up`, `.retake_down`, `.retake_same`, `.retake_combined`,
  `.ended_early`, `.fast_flag`.
- **Next steps and method:** `.next_session`, `.next_check`, `.how_title`, `.how_body_cjk`,
  `.how_body_en`, `.unavailable`.
- **Onboarding gate:** `onboarding.studied_before`, `.studied_yes`, `.studied_few`, `.studied_no`.
- **Labels:** `.label_low|medium|good` reuse the report's keys.

Copy rules:
- "recognised", never "know" alone;
- no exam level (PQ2);
- no praise, pass/fail or readiness;
- no neutrality claim about guessing;
- numbers formatted by locale;
- the name per PQ12 needs native review (es, ja, zh).

## 17. Key Architectural Decisions

1. **Decision:** adaptive band allocation + conditional reading + design-based scoring (D3S) for v1,
   with IRT scoring as a gated, shadow-first upgrade that keeps v1's selection (ADR-057).
   - **Rationale:** unbiased with honest 95% coverage in every simulated population; no item
     calibration or priors needed with 3 users (E18, E20).
   - **Alternatives rejected:** IRT targeting now (D1/D3: bias up to −4.4% of the pool, advanced
     learners within one level only 32–33%, uncalibrated items); reading on every word (D2) or half
     the words (D4); level strata (D3L: 20–45% wider counts).
2. **Decision:** the zh/ja headline is meaning-and-reading recognition from a pair estimator (ja
   ADR-058; zh with tones, ADR-060). Answers pool only within one instrument and D. There is no
   exam-level estimate (ADR-058; owner, PQ2).
   - **Rationale:** E21 (cognate over-statement), PSY M5 (instrument mix), E23 (level estimate fails).
   - **Alternatives rejected:** meaning headline; pooling legacy check answers; the threshold level
     range.
3. **Decision:** placement evidence is its own kind, written per word pair. Meaning-only words go to
   reading practice, and placement evidence is never rated known on its own (ADR-059).
   - **Rationale:** LRN L6 (the target case was pushed out of practice), [SIM §5.7] (7–13% of all-right
     words are not known as words).
4. **Decision:** extend the calibration tables (mode `placement`, item and probe kinds, instrument,
   packed options); no new tables in v1 (ADR-057).
   - **Alternatives rejected:** a `placement_*` table family (duplicates the ledger the report and the
     planner read); option rows (≈ 2× bytes).
5. **Decision:** one SQL round trip per answer (grade + build next), with the next band computed from
   the previous call's tallies.
   - **Rationale:** the check's client prefetch leaves unanswered rows (E4).
   - **Alternatives rejected:** sending both possible next items to the client (LRN L4), because
     choosing between them reveals whether the tapped option was the key.
6. **Decision (owner, PQ3; ADR-060, superseding ADR-057 decision 4):** zh reading items score tones
   with two tone pairs (K, K′, F, F′) built only from syllable+tone pairs that exist in Mandarin, and
   the full reading is estimated as right tones minus wrong tones on the same syllables. ja special
   morae stay in unscored 2-option probes.
   - **Rationale:** the owner wants pronunciation, tones included, to separate real from partial
     knowledge; valid variants exist for 99.1% of pool words (E32); the estimator is unbiased with
     96–97% coverage (E33); one pair per syllable set removes the "two similar options" cue.
   - **Alternatives rejected:** syllables only (the earlier default; tones untested); one tone
     variant with two segmental foils (the key is always one of the only two options that share
     syllables); three tone variants (gives the syllables away and cannot be built for 11% of words,
     E32); the ADR-058 `prw/3` correction on these items (+1.9..+3.3% bias, E33).
7. **Decision:** cap 60 (zh/ja; owner, PQ10) / 40 (en) plus a 9-minute active-time cap, copy "about 7 /
   5 minutes" (E31, E33).

## 18. Security Considerations

- **Answer keys:** an item payload never contains the key or, on meaning items, the reading.
  `key_position` and `option_sense_ids` live on `calibration_responses`, which has no client privilege
  (`migrations/security_calibration_answer_keys.sql`). All reads and writes go through the service role.
- **Ownership:** every RPC checks `p_user_id` against the session. A foreign session cannot be told
  apart from a missing one (404), as in the check (`routes/calibration.py:38-47`).
- **Input validation:**
  - language ids from `_SUPPORTED_LANGUAGE_IDS`;
  - `position` int 0–3 (0–1 for a sound pair) or null;
  - generated zh options are built server-side from the inventory; the client only ever sends a position;
  - `latency_ms` int, clamped;
  - `response_id` int;
  - `p_draws` and `p_next_band` produced server-side only, never taken from the client;
  - existing JSON body size limits.
- **Function lockdown:** `SET search_path` and REVOKE/GRANT per `migrations/CLAUDE.md`. The static lint
  `tests/test_migration_security_lint.py` and `tests/sql/check_function_acls.sql` must pass.
- **Rate limits** (§14). **Answer harvesting:** reveals show keys after wrong answers. The only stake is
  the learner's own result, limited by the daily start cap and the 180-day exclusion.
- **Automated accounts:** a session whose median latency is < 800 ms over ≥ 10 answers is flagged
  `fast`. Its result says so, and validation excludes it (110fb390-like, E12).
- **Privacy:** results contain only the learner's own data. Logs and validation queries refer to users
  by the first 8 characters of the id.

## 19. Testing Strategy

- **Unit, pure Python** (`tests/test_placement_design.py`, `tests/test_knowledge_estimate.py`):
  - the warm-up's first pass is 7 → 1 and covers every band twice;
  - allocation picks the band with the largest Δ (hand-computed fixture) from the previous call's
    tallies;
  - exhausted bands are skipped;
  - stop reasons at 40/60/61, at 540 s active time, and for en at 20/40;
  - a pending reading item blocks stopping;
  - probe budget and per-kind caps, with at most one probe per word;
  - the pair-counting table of §5.1: ready vs exempt, IDK vs wrong, probes excluded, abandoned pair
    excluded;
  - the gap x-mapping and variance against a hand computation, and G = T_m − T_mr on identical samples;
  - `estimate_range_pairs` reproduces ADR-051 on identical inputs;
  - zh: `estimate_range_tone_pairs` on hand-computed fixtures (K/K′/F/F′/IDK counts), the 0.25
    pseudo-count, and K_m = K_mr + tone gap + reading gap on one sample;
  - the tone-variant reference: 买 mǎi has no 一/不 change and excludes its own readings; 很好 hěn hǎo
    excludes hén hǎo (sandhi); 东西 dōng xi keeps xi neutral; 一样 yí yàng never changes yí;
  - the M8 guard direction;
  - eligibility (a), (b) and (c), with **End now at 20, 30 and 45 scored items returning a result**
    and at 19 returning `not_enough`;
  - word groups;
  - the ADR-053 comparison verdicts;
  - the rule-5 regex on `行李 —— …`, `林地；…`, `x; …` and a 13-character prefix (not stripped);
  - the rule-3b pattern on 考え against かんがえ, かんがい, かかえ.
- **Simulation (slow, `tests/test_placement_coverage.py`, TASK-1087):** the production allocation and
  estimator on the [SIM] learner model. Assertions in §20 V0.
- **SQL (read-only checks after apply; static migration tests):**
  - `next_item` and `answer` never return a lemma answered in 180 days, a non-ready lemma, a key, or a
    reading on a meaning item;
  - reading foils share the key's display syllable or mora count; no kana-inconsistent foil (ja);
  - zh reading items have exactly the roles K, KT, F, FT; KT and FT are tone variants of K and F under
    rule 4 (every syllable+tone in the inventory, no sandhi-only variant, no reading of the same lemma);
    F is not a tone variant of K; `calibration_zh_tone_variants` matches the reference implementation
    on every pool reading;
  - the rule-5 residual is ≤ 1% for zh/ja and ja/zh (§2, query Q4 of the research record);
  - answering twice and answering a foreign session are rejected;
  - `close` leaves no unanswered placement rows;
  - the lint and ACL checks pass.
- **Integration (`tests/test_placement_routes.py`, Supabase fake):**
  - a scripted learner runs start → answers → done for zh, ja and en;
  - the result is frozen;
  - the evidence batch is called once (claimed by `bkt_applied_at`);
  - a missed meaning becomes an A2 candidate, and a meaning ✓ reading ✗ word becomes an A2r candidate
    mapped to the native rank-1 sense;
  - an abandoned session closed by `close_stale` gets a frozen result when eligible.
- **Latency:** `/answer` server time p50 ≤ 250 ms and p95 ≤ 600 ms over 50 calls against production with
  a test account. Record every run, because host jitter is large ([[evaluations/latency-2026-11-11]]).
- **UI:**
  - vitest (`tests/unit/placement.test.js`): the reveal state machine (parts held, auto-advance only
    when all ✓, one advance per click), the probe badge, IDK hidden on `forced_guess`, result rendering
    (zh, ja, en; gap shown or hidden; retake block);
  - Playwright smoke at 390 px in both themes;
  - i18n parity.

## 20. Validation plan (small n)

Exclusions everywhere: 110fb390 and `fast` sessions. All analyses use read-only SQL plus pure Python,
and results are filed under `wiki/evaluations/`.

| # | when | n needed | question | method | pass / action |
|---|---|---|---|---|---|
| V0 | before launch (TASK-1087) | synthetic | does the production code behave as simulated? | production `placement_design` + `knowledge_estimate` on the [SIM] model with the zh tone state of E33, launch readiness fixtures (PSY M13), zh·en, zh·ja, ja·en, ja·zh, en·en, IDK 0.3/0.7 | 95% coverage ≥ 0.90 for m, m+r, the reading gap and the zh tone gap; \|bias\| ≤ 1.5% of the pool; mean scored items 55–61 (zh/ja); End-now coverage at 20/30 items ≥ 0.88; the label distribution and early-stop share per L1 recorded and compared with E22/E25; `expected_sd` error recorded |
| V1 | first week | the owner (de6fd05b, ja) | **mode effect**: bare meaning items vs the legacy check (reading shown) on disjoint words | Δ = T_place,m − T_check (172 legacy answers) with SD = √(SD₁² + SD₂²); real minutes per item | descriptive: report Δ and its 95% CI; a CI excluding 0 is evidence that the instruments differ (expected); minutes ≤ 8 |
| V2 | weeks 1–6 | every retest pair (10–30 per language) | test–retest on disjoint words within 7 days | z = (T₂ − T₁)/√(SD₁² + SD₂²); variance inflation κ = √(mean z²) with a 95% CI (χ² on the pairs) | whenever the CI's lower bound > 1, widen all intervals by κ and record it (PSY M12) |
| V3 | after ≥ 200 later first-try outcomes on placement-tested words | pooled | do credited words predict later practice? | first-try accuracy of meaning-right vs meaning-missed words; calibration by band | difference ≥ 20 points; credited-but-wrong later near the simulated 7–13% |
| V4 | ≥ 60 pooled `reading_after_miss` probes | pooled | reading without meaning (ω) | ω̂ = (r − w/3)/n (zh: (K − K′)/n) with a Jeffreys-type interval; per learner, the implied per-band bias (1 − K̂_m,b)·ĝ_m·ω̂ with ĝ_m = (1 − ŝ_m)/4 | implied bias ≤ 2% of the pool for ≥ 90% of learners → keep; else an ω-correction ADR (PSY M10) |
| V5 | ≥ 30 placements per language | pooled | S8 inside the frame: are list words recognised more than same-band non-list words? | logistic regression of **pair** outcomes on band dummies + on-list (+ level), learner random intercept; decision rule calibrated by simulating V5 at n = 30 under the base and `gamma25` models; equivalence rule (keep only if the upper CI bound < the calibrated threshold) | input to TASK-1090 only (no level output in v1) (PSY M11) |
| V6 | ja: ≥ 50 pooled `sound_pair` probes; zh: ≥ 30 placements | pooled | ja: given the kana skeleton, are special morae recognised? zh: how large is the tone gap, and is K′ chosen more often than F′ by learners who miss F (a sign that variants are rejected by sound pattern, rule-4 bias iv)? | ja (c − w)/n (guess 1/2) with a Jeffreys-type interval; zh the tone gap of §5.1 pooled, and the K′:F′ ratio among non-K answers | descriptive; a K′:F′ ratio far from the model's (S-learners pick K′, guessers pick both equally) triggers an ADR-060 review |
| V7 | when a goal or level is stated | ≥ 15 | does the m+r count rise with the stated level? | Spearman (stated level, T_mr) | descriptive only, never a gate |
| V8 | ≥ 30 placements; ≥ 60 `forced_guess` probes | pooled | IDK use and the knowledge it hides | distribution of `result.skip_share` vs T; hidden knowledge (c − w/3)/n over forced-guess probes with an interval | descriptive; if hidden knowledge > 0.15, strengthen the "lower-side" copy and revisit ADR-051 rule 5 with TASK-1061 |
| V9 | ≥ 100 pooled `recheck` probes | pooled | **reading credit**: are m+r-credited readings recognised again ≥ 7 days later with disjoint foils? | false-credit rate = 1 − (c − w/3)/n on rechecks (zh: 1 − (K − K′)/n, which also measures partial tone memory, E33); implied guess rate among unknown readings | if the implied guess rate > 0.30, replace r = 1/3 for readings via an ADR-058 revision; until then the method note keeps "may be a little high". Caveat: the reveal teaches the reading, so the false-credit rate is a lower bound (INFERENCE) (PSY M4) |
| V10 | ≥ 30 placements | pooled | real length | active minutes p50/p95 per language and L1; share stopped early | copy changes if p50 is more than 1 minute off "about 7 / 5 minutes"; the time cap moves if more than 10% of placements end on it |

## 21. Rollout

1. Bug fixes and data: TASK-1074 (zh normaliser), TASK-1075 (ja pool and foils), TASK-1082 (intro-drill
   pinyin). All are independent of the feature.
2. Migration (TASK-1076) and SQL functions (TASK-1077, TASK-1079) applied by the owner, followed by
   read-only checks.
3. Code behind an empty `PLACEMENT_ENABLED_LANGS`; V0 harness green (TASK-1087).
4. PQ3 (zh tones scored) and PQ5 (evidence) were answered by the owner on 2026-11-18; zh launches with
   TASK-1092. Enable zh and en (PQ6, PQ14); ja after its readiness gate passes (PQ13). The nightly `calibration_placement_close_stale` job is added to `web/scheduler.py`.
5. V1 by the owner, then V2–V10 as data arrives (TASK-1089).
6. A level output only through TASK-1090; v2 IRT only after its gate (TASK-1093).

## 22. Open questions

| # | Question | Why it matters | Default |
|---|---|---|---|
| PQ1 | For zh/ja, which range leads: "meaning and reading" or "meaning"? | A meaning headline over-states cognate learners by ~1,000 zh words (E21). | **Meaning and reading first**; the gap line when clearly above 0. |
| PQ2 | **ANSWERED (owner, 2026-11-18): "No, not at the moment."** | The threshold level line failed (E23); a level claim rests on about a third of each level (E24). | **None.** TASK-1090 stays parked until the owner asks for a level output. |
| PQ3 | **ANSWERED for zh (owner, 2026-11-18): "Yes, but only the existing tones, just wrong combos."** Read as: tone variants are allowed as wrong options when every syllable+tone pair exists in Mandarin and only the combination is wrong. ja long-vowel / っ / ん / voicing variants were not asked about and stay unscored. | Real-reading foils test tone on 11% of zh items (E6); valid variants exist for 99.1% of pool words (E32). | **zh: scored tones, rule 4 (ADR-060, TASK-1092, a zh launch item). ja: no.** |
| PQ4 | Unscored, labelled probes (≤ 4 per test)? | They test the scoring's assumptions (V4, V6, V8, V9), which no live data covers; cost ≤ ~0.5 min. | **Yes.** |
| PQ5 | **ANSWERED (owner, 2026-11-18): approved.** Placement evidence is its own kind, written per pair; meaning-only words go to reading practice; never rated known alone. | Without it the target case is pushed out of practice (LRN L6), and the result's copy would be untrue (LRN L7). | **Yes** (ADR-059 accepted); the open-ended check's kind is decided in TASK-1065. |
| PQ6 | Offer the placement to English learners at launch? | en is meaning-only, 40 items, ~4.4 min; not simulated. | **Yes**, once V0 includes an en population. |
| PQ7 | Offer it in onboarding, with the "studied before?" gate? | Beginners face ~50–60 items, most IDK (LRN L5); a first experience. | **Offered after the gate, skippable**; always on offer on the report and the Me row while the learner has no placement. **ANSWERED (owner, 2026-11-27): build it** — built as the default. |
| PQ8 | Retake policy | Disjoint words need supply (ja band 7: 68 ready words). | **Any time, ≤ 3 starts per language per day, no word within 180 days**; retake compared with the previous placement. |
| PQ9 | Keep ADR-051's per-band minima for Medium/Good? | A placement alone is "Rough" or "Fewer than" (E25). | **Keep**; revisit after V2. |
| PQ10 | **ANSWERED for zh/ja (owner, 2026-11-18): "About 60."** English was not part of the question and stays at 40 (meaning only, ≈ 4.4 min) unless the owner says otherwise. | 60 items ≈ 6.4–7.0 min (E31, E33). | **60 (zh/ja) / 40 (en), 9-minute active-time cap**, "about 7 / 5 minutes". |
| PQ11 | Make the check's meaning items the bare instrument (no reading line, prefix stripped)? | Otherwise check and placement answers cannot be pooled (PSY M5); ≥ 10.8–13.3% of cross-CJK items are answerable by string matching. | **Yes** (TASK-1091). |
| PQ12 | Name and translations | UI copy in four locales. | "Vocabulary placement" / "Prueba de nivel de vocabulario" / "語彙レベルチェック" / "词汇水平测试", **native review**. |
| PQ13 | Japanese waits for the ja pool refresh, the kana-consistent refill and the readiness gate? | 69% readiness today, 50% in band 1 (E8); rule 3b removes ~199 more. | **Yes, wait** (TASK-1075). |
| PQ14 | Chinese launches on today's pool (3,623 of 12,790 lemmas)? | The zh refresh (TASK-1063, ≈ 5–7 MB) changes the denominator later. | **Yes**; the retake block and growth card announce a pool change. |
| PQ15 | Proceed at the database cap question (report OQ13)? | ≈ 20–25 KB per placement. | **Yes**; reassess at 1,000 placements. |
| PQ16 | Exclude 110fb390 from all validation (report OQ6)? | It looks automated. | **Yes.** |
| PQ17 | Use the learner's stated exam level as a prior? | A wrong self-report biases a model; v1 needs no prior. | **Not in v1**; v2 only, shown in "How this works". |
| PQ18 | Does the placement replace the open-ended check in navigation? | The check narrows the range and keeps Readings mode. | **No**; linked as "Narrow your range". |
| PQ19 | May a placement move the learner's test level (ELO)? | The ability fit scores IDK as a wrong guess (PSY M16). | **Not until OQ33**; then via a skip-aware likelihood (TASK-1083). |
| PQ20 | "Practise these readings" for every tier? | It is the owner's target case. | **Yes**, all tiers, in v1. |
| PQ21 | Which sense row placement BKT writes, and which row admission uses | ADR-047 problem 3: one meaning has several rows; exercises live on the native row (E16). | **BKT on the anchor row (as the check); admission on the native rank-1 row.** |
| PQ22 | Seed a reviewed heteronym list for single-character zh lemmas? | 14 real readings (强 qiǎng, 数 shǔ, 可 kè, …) are not attested by any dictionary word, so they can appear as wrong tone options (§23). | **Yes, before the zh launch** (TASK-1096). |
| PQ23 | Long words with no buildable reading item drop out of the placement (gate fails on the length check). | Fixed length rule vs per-word meaning-only. | **Per-word meaning-only** (owner 2026-11-23; §23b). |

## 23. Build notes (2026-11-19) — where the code differs from or fills gaps in this page

Built on `claude/beautiful-planck-0fftk4`; nothing applied live. Apply order: [[tasklist/report-and-placement-apply-runbook]].
- **Answer round trip (§1, §14).** The previous call's tallies live in a process-local cache; with several gunicorn
  workers a request can find it cold. The service then sends `p_next_band = NULL`, computes the band from the
  returned tallies and builds the next item with `calibration_placement_next_item`: one extra round trip, on a
  cache miss only.
- **`next_item` re-sends a pending item** (`"resent": true`) instead of drawing a second one; this is how resume
  works. `recheck` probes are served at session start. `close` returns the tallies merged with
  `session_id, stop_reason, ended_at, already_closed, deleted`; `close_stale` sets `ended_at` to the session's
  last activity. When the requested band is empty, the item comes from the nearest band (ties → the commoner).
- **Probe draw.** The branches share one `u_probe`: after IDK on a reading-ready word, `forced_guess` fires at
  0.15 and `reading_after_miss` at 0.10 (not 0.25). V4's sample-size estimate must use 0.10.
- **`update_vocabulary_from_placement_batch(p_user_id, p_language_id, p_items)`** takes the language (needed for
  inserted rows), unlike §14's two-argument signature.
- **Gap guard (new).** Neither end of the reading gap or the tone gap may exceed the meaning range's upper end
  (`knowledge_estimate.cap_gap`). Driving the service against the real SQL showed why: a learner who consistently
  picks the same wrong tones (K′ every time) is outside the ADR-060 model; (pc − pkt) goes below zero and the raw
  tone gap doubles. The per-word group ("meaning and pinyin, not the tones") is right for such a learner.
- **Combined line** is shown only when the inputs are the placement instrument: for an abandoned first placement
  the inputs are read before its result is frozen and fall back to legacy rows.
- **Pinyin.** Numbered pinyin keeps ü (`lü4`), as the stored numbered parts do (rule-4 text said v). A token with
  two marks (`yíhuìr`) is two syllables. The tone inventory has 381 syllables (not 382). A second table,
  `calibration_zh_char_readings` (2,379 rows), stops a single-character lemma getting a tone variant that its
  character has anywhere in the dictionary: 15 of 48 polyphone cases fixed; the 33 left (14 real readings) are
  TASK-1096.
- **Mora count (rule 3) corrected:** っ/ッ is a mora and is counted (きって = 3); only ゃゅょぁぃぅぇぉ and their
  katakana forms are not.
- **Rule 5.** A second pass strips a dash-ended equivalent (226 ja/zh keys look like `X；Y —— …`). The residual before
  exclusion is 1/3,623 (zh/ja) and 50/3,175 = 1.57% (ja/zh, above the 1% criterion; mostly genuine shared words such
  as 心理 in 心理学); after exclusion 0. zh/zh (16 keys) and ja/en (17) keep a lemma-containing prefix: rule 5 only
  covers cross-CJK pairs.
- **`calibration_placement_ready_counts` for zh takes about 30 s** (two variant calls per lemma), over PostgREST's 8 s
  timeout: the gate runs through psql (`scripts/placement_readiness_gate.py --psql`) or the SQL editor.
- **Result payloads** also carry `word_lists` (group → words) on `/answer` (done), `/end`, `/result` and `/latest`.
  The page's intro says "If you think you recognise it, answer" (copy rule: never "know" alone).
- **`knowledge_calibration_inputs` choices:** an eligible placement is one ended in the window, not abandoned unless
  its result is frozen; `placement_eligible` is eligibility rule (b)'s precondition; the gap uses the combined
  placement pair sample; dates fall back to all-time answers when the window is empty. `sound_pair` rows have
  `instrument` NULL.
- **Japanese readiness (TASK-1075).** `calibration_refresh_anchor_pool(p_word_language_id)` and the kana-pattern
  filter in `pronunciation_distractors` are built from the live definitions. On the local sample the old picker had
  138 of 218 foils inconsistent with the visible kana, the new one 0 of 1,827. Live (read-only): 277 of 567 ja
  kanji+kana anchors have fewer than 3 consistent cached foils (estimate was ≈ 199).
- **Prestudy** shared the E17 gap: `prestudy._load_senses` now appends the numbered part to tone-marked-only zh
  readings, so the prestudy page and the intro drill both get it.

---

### 23b. Meaning-only words (PQ23, owner 2026-11-23; applied live the same day)

The live gates failed on the length check: words of ≥ 3 characters often have no cached wrong reading with the same
syllable / mora count (rule 3) or, in ja, consistent with the visible kana (rule 3b), so they were never drawn.
Live counts by shape (zh 1:2): 1 char 247/263 reading-ready, 2 chars 2,501/2,522, 3 chars 440/470, 4 chars 220/290,
5+ 0/4; ja 3:2: 2-kanji words ≥ 99%, 3+ character words with kana endings 192/470, 5+ mora readings mostly not.
A fixed length rule would have dropped ≈ 850 working reading items, so the owner chose the per-word rule:

- **A word whose reading item cannot be built is asked the meaning question only** (like en words and ja kana-only
  lemmas). `calibration_responses.reading_exempt` (boolean, NULL on older rows and on reading/probe rows) is set on
  each scored meaning row when it is served: `calibration_placement_reading_exempt(lemma) OR NOT
  calibration_placement_reading_ready(vocab, L, lemma)`.
- `calibration_placement_draw` and `_band_has_word` need only a meaning-ready word; `_build_meaning` writes the flag.
- `_answer`, `_tallies`, `knowledge_calibration_inputs` and `services/calibration_placement._word_outcomes` read the
  stored flag, falling back to the lemma rule when it is NULL.
- zh pair tallies `[n', pc, pkt, pf]`: a meaning-only word answered right counts in `pc` (combined-correct), as ja
  kana-only words already did in `[n', pc, prw]`; answered wrong it counts in `n'` only.
- `calibration_placement_ready_counts`: `ready` = meaning-ready (every such word can be served); new
  `meaning_only_n` per band. The launch gate is unchanged.
- Consequence: the reading half of the estimate rests on the words that do have reading items, which under-represents
  long words; the meaning half covers the whole frame.

Result on live (2026-11-23): ja (3, 2) 3,194 / 3,241 ready (98.5%), PASS, every band ≥ 95% (≈ 330 words meaning-only).

## Appendix A — Review outcomes

Two independent reviews challenged the 2026-11-18 draft: a psychometric review (M1–M16) and a
learner-side review (L1–L13). Full findings, evidence and dispositions are in
[[evaluations/vocab-placement-research-2026-11-18]] §6. In short:

| finding | decision | what changed |
|---|---|---|
| M1, L1 (blockers) | accepted | Exam-level range removed from v1 (§5.3); PQ2 default "none"; TASK-1090 redesign with per-level gates on displayed copy |
| M2 | accepted | ADR-054's v1 stance kept; conditions for any later level claim (§5.3) |
| M3, L9 | accepted (L9 point 2 partly); zh part superseded by the owner's PQ3 answer | ja kana-consistent foils (rule 3b); ja `sound_pair` probes. zh: tones now scored with two tone pairs (rule 4, ADR-060), which also answers M3's 10.9% tone coverage |
| M4 | accepted | V9 reading-credit rechecks; "may be a little high" in the method note |
| M5, M15 | accepted | `instrument` per response; pool within instrument and D; report D rule; V1 as a mode-effect estimate; TASK-1091 widened |
| M6, L12 | accepted | Neutral IDK copy; `forced_guess` probes; skip share stored |
| M7 | accepted | "recognition" wording; gap with its own interval; per-L1 early-stop facts; "guesses included"; "matches My vocabulary on the day taken" |
| M8 | accepted | Guard direction reversed (§5.1) |
| M9 | accepted | v2 keeps v1 selection; identification fixed; separate skip rates; per-group gate |
| M10, M11, M12 | accepted | V4, V5, V2 rewritten |
| M13 | accepted | ja figures flagged (E29); V0 fixtures from launch readiness |
| M14 | accepted | Representativeness added to the launch gate |
| M16 | accepted | No pooled-ability or rating write until OQ33 (TASK-1083) |
| L2 | accepted | Result leads with this test's word groups; range second; "Fewer than" phrased for beginners; gap shown only when clear |
| L3 | accepted | Result after End now (warm-up + 20 items) and for abandoned sessions; resume 24 h |
| L4 | partly accepted; length superseded by the owner's PQ10 answer | Cap 60 + 9-minute time cap, "about 7 minutes"; minutes-left progress; one round trip per answer; pre-sending both branches rejected (it leaks the key) |
| L5 | accepted | "Studied before?" gate; commonest band first; claim deleted |
| L6, L7 | accepted | Pair-based evidence; A2r reading-gap queue; native-sense admission; intro-drill pinyin fix; evidence is a launch dependency |
| L8 | accepted | Rule 5 covers `——`/`—`; measured ≤ 1% residual; residual anchors excluded |
| L10 | accepted | Retake result shows this vs previous with the ADR-053 verdict, then combined |
| L11 | accepted | Probes labelled; "uninformative" claim deleted |
| L13 | accepted | TASK-1094: placement segment in the goal-path bars; hero copy |

## Related Pages
- [[features/vocab-placement]] — prose counterpart
- [[features/calibration]], [[features/calibration.tech]] — the check this extends
- [[features/knowledge-report]], [[features/knowledge-report.tech]] §2.4, §2.6, §6.1 — the report sections this changes
- [[decisions/ADR-057-adaptive-placement-with-conditional-reading]], [[decisions/ADR-058-meaning-and-reading-recognition-pair-estimator]], [[decisions/ADR-059-placement-evidence-kind]], [[decisions/ADR-060-zh-placement-scores-tones]]
- [[decisions/ADR-051-vocabulary-size-from-calibration-frame]], [[decisions/ADR-053-daily-knowledge-snapshots]], [[decisions/ADR-054-exam-word-lists-in-storage]], [[decisions/ADR-033-budget-scope-and-new-word-budget]], [[decisions/ADR-047-basic-word-knowledge-prior]], [[decisions/ADR-025-semantic-distractor-selection]], [[decisions/ADR-039-packed-calibration-distractor-cache]]
- [[evaluations/vocab-placement-research-2026-11-18]] — research record
- [[database/schema.tech]], [[api/rpcs.tech]]
- [[tasklist/vocab-placement.tasks]]
