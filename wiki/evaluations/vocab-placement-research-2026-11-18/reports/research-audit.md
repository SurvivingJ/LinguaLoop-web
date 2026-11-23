# Vocabulary placement test: code and data audit of the existing vocabulary check (Calibration)

Research stage, TASK-1073. Written 2026-11-18. Read-only work: no application code was written and nothing was
written to the live database (Supabase `kpfqrjtfxmujzolwsvdq`; SELECT only). Users are referred to by the first 8
characters of their id.

Labels: **MEASURED** = read from code or from a query shown here; **ESTIMATE** = a number derived from measured
inputs with stated assumptions; **INFERENCE** = a reasoned conclusion that has not been tested.

Live function bodies were read with `SELECT pg_get_functiondef(oid)` / `prosrc` from `pg_proc` (queries in §A).
Where the live body matches a migration file, the file:line is cited. "live" means the body as read on 2026-11-18.

---

## 0. Summary for the designers

1. **Selection today is not adaptive.** `calibration_next_anchors` serves the least-served Zipf band of the
   current session, random within band, from `calibration_anchor_pool`. It excludes anchors served in this
   session only, so anchors repeat across sessions and retakes. Any sense rank can be served. (MEASURED)
2. **Readings mode** builds wrong options by Levenshtein distance over a normalised reading (zh: numbered pinyin
   with tone digits; ja: kana), excluding homophones, preferring the same syllable or mora count, from a cached
   pool of 8 sampled at random down to 3 at serve time. The learner sees tone-marked pinyin (no numbers) or kana.
   (MEASURED) **The zh normaliser is now broken for 82% of zh readings.** 6,621 of 8,110 live zh readings no
   longer carry the `(ying4 yong4)` numbered suffix, so they normalise to a diacritic string with a syllable count
   of 0. The existing cache predates this (built September 2026) and still renders correctly. Any new fill,
   including the planned zh pool refresh (TASK-1063), would rank foils with a broken length and syllable test.
   (MEASURED + INFERENCE)
3. **Definition items show the reading under the word.** `calibration_build_items` returns `pronunciation` in
   definition mode and the page renders it. In a paired design, a meaning item shown before the reading item for
   the same word gives the reading away. (MEASURED)
4. **For a paired meaning-and-reading design, the item bank is ready for Chinese but not yet for Japanese.**
   Rank-1 lemmas with both distractor sets cached: zh 3,482 of 3,623 (96%); ja 2,185 of 3,175 (69%), and only
   50% in band 1. The ja gap is mostly a **stale pool**: 841 ja native rows in the pool have no reading although
   `dim_word_senses` now has one. Japanese also has 214 katakana-only lemmas in the reading pool; their reading
   is a mechanical transliteration (5 of 5 answered right in the live data). (MEASURED)
5. **The shared-character problem the owner raised is visible in the item bank.** All 3,682 zh/ja keys
   (Chinese word, Japanese definition) begin with a Japanese headword followed by `；`. In 11.8% that headword
   is the Chinese lemma character for character. At least 13% of zh/ja and ja/zh anchors can be answered by
   finding the prompt string inside the key, because no cached foil contains it. Meaning items alone cannot
   separate "knows the word" from "reads the characters" for these learners. (MEASURED)
6. **Live data is tiny.** There are 344 answered items from 3 users. 110fb390 looks automated (median latency
   364 ms; 25 one-item sessions lasting 0–2 s). Usable data comes from one learner, de6fd05b (ja): 178 meaning
   and 99 reading answers. Median latency is 3.4 s (meaning) and 3.6 s (reading); wall-clock time is 6–8 s per
   item including the reveal. The learner skips rather than guesses: 43% / 40% skips against 10% / 1% wrong
   picks. **Only 6 words were answered in both modes**: 3 both right, 1 meaning only, 1 reading only, 1 neither.
   That is too few to estimate anything. (MEASURED)
7. **Sessions almost never end.** 74 of 79 sessions have no `ended_at`; 1,005 of 1,349 response rows (74.5%)
   are prefetched items that were never answered. Publishing to `user_calibration_state`, the BKT write and the
   rating write all run only at `/end`. de6fd05b's 178 meaning answers have never reached
   `user_calibration_state` or BKT. A placement test needs a server-side end. (MEASURED)
8. **BKT:** at `/end`, definition mode only, each answered anchor sense goes through
   `update_vocabulary_from_word_tests_batch`. The prior is a Zipf step function, the update uses slip 0.05 and
   guess 0.25, then transit 0.05 is applied, and a skip counts as wrong. It writes to the **anchor sense row**:
   for ja/en that is the English-gloss row of the Japanese word. (MEASURED)
9. **The ability estimate** is a per-learner maximum-likelihood fit of `p = 0.25 + 0.75·σ(a(z − b))` over Zipf,
   with a skip counted as a wrong answer. Its SE is a lookup by answer count from a simulation, not the
   learner's own uncertainty. Reproducing it on de6fd05b's pronunciation answers gives z85 = 5.52 (stored: 5.49).
   A skip-aware likelihood moves the midpoint 0.4–0.8 Zipf lower for the same data. (MEASURED / ESTIMATE)
10. **`services/irt/` is a nightly 2PL item calibrator for `exercises`.** It has no guessing parameter, no
    person-ability estimation, no item selection and no stopping rule. It has calibrated 0 of 144,374 exercises
    ever. It cannot be reused as a CAT engine; its only reusable part is the bounded L-BFGS-B fitting pattern.
    (MEASURED)
11. **Size:** database 513,535,123 B (513.5 MB decimal, 490 MiB); calibration tables ≈ 18.6 MB. A 40-item
    placement costs about 20–35 KB of rows (ESTIMATE). Mixing meaning and reading items in one session, a new
    `placement` mode, per-user retake exclusion and the zh normaliser fix all need migrations (§5).

---

## 1. How the check works today

### 1.1 Item choice — `calibration_next_anchors` (live; `migrations/task772_calibration_anchor_pool.sql:186-257`)

- Called by `calibration_build_items` with `v_slack = LEAST(CEIL(count·1.4)+3, 50)` candidates
  (`migrations/calibration_distractor_cache_packed.sql:256`). (MEASURED)
- Candidate set (`task772:226-240`): rows of `calibration_anchor_pool` for (word language, definition language).
  In pronunciation mode the definition language is replaced by the word language, because readings exist only on
  native rows (`task772`, comment above `v_def_lang`). Also required: `has_pronunciation` or `has_embedding` by
  mode (`task772:234`), **not already served in this session** (`task772:236`, `served` CTE filters
  `cr.session_id = p_session_id`), and not in `calibration_anchor_blocklist` (applied live). (MEASURED)
- Ordering (`task772:245-254`): `row_number() OVER (PARTITION BY zipf_band ORDER BY random())` plus the band's load
  so far in this session, then `random()`. This is a round-robin over the least-served bands. **There is no
  adaptivity**: the learner's answers never influence which band or word comes next. (MEASURED)
- **Sense rank is not filtered.** Any `sense_rank` in the pool can be served; ADR-051 measured 38% rank > 1 in
  en/en. For de6fd05b's ja answers only 2 of 178 were rank > 1 (§3.6). (MEASURED)
- **Exclusion is per session, not per user.** Anchors repeat across sessions: de6fd05b answered 178 meaning items
  on 174 distinct lemmas (§3.1). A retake can show the same words, and a wrong answer or skip reveals the key
  (`static/js/pages/calibration.js:355-381`). (MEASURED)
- Bands (`calibration_zipf_band`, live; `migrations/calibration_sessions_and_ability.sql:98-116`): 1 `< 3.0`,
  2 `[3.0,3.5)`, … 6 `[5.5…)` → **band 1 and band 7 are open-ended**, not 0.5 wide (band 1 reached Zipf 1.10 in
  de6fd05b's data). Band midpoints 2.75 … 5.75 (`:118-125`). (MEASURED)
- Client: first fetch 3 items, then batches of 12 whenever the queue drops to 6
  (`static/js/pages/calibration.js:41-43`); the server clamps a batch to 25 (`services/calibration_service.py:48`,
  `calibration_build_items` `LEAST(...,25)`). (MEASURED)

### 1.2 Building an item — `calibration_build_items` (live; `calibration_distractor_cache_packed.sql:227-368`)

- Key text = the anchor's definition (definition mode) or displayed reading (pronunciation mode).
  Anchors whose key is empty are skipped. (MEASURED)
- Options come from the packed cache via `calibration_cached_options(mode, anchor)` (live; packed `:119-150`),
  which joins `option_text` live from `dim_word_senses`. Any cached option whose text equals the key is removed
  (`:275, :285, :304`). If fewer than 3 remain, the builder fills the cache on demand, at most 4 fills per
  request (`p_max_fill`). If 3 options still cannot be found, the anchor is skipped. (MEASURED)
- Definition mode serves foils by cached rank (deterministic, the first 3). Pronunciation mode samples 3 of up to
  8 at random (`:305-307`). Positions are shuffled (`:324`). (MEASURED)
- **The item payload includes `pronunciation` in definition mode** (`:345-346`: `CASE WHEN v_need_pron THEN NULL
  ELSE v_anchor.out_pronunciation END`), and the page renders it under the word
  (`static/js/pages/calibration.js:243-244`). A zh meaning item therefore shows the pinyin, and a ja meaning item
  shows the kana. (MEASURED)
- `exhausted` = no candidate anchors at all (`:365`). (MEASURED)

### 1.3 Readings mode — how wrong readings are built

`pronunciation_distractors(p_sense_id, p_word_language_id, p_count=3, p_max_distance=3, p_max_ratio=0.45)`
(live; `migrations/calibration_pronunciation_mode.sql:165-270`), called with `p_count = 8` by the cache filler
(`calibration_distractor_cache_packed.sql:186`):

| step | live behaviour | cite |
|---|---|---|
| comparison form | zh: the parenthesised **numbered pinyin with tone digits** if present, else the raw string; whitespace removed, lower-cased. ja: NFC kana with the latin loanword suffix (`-Ion`) stripped | `calibration_normalise_pronunciation`, `calibration_pronunciation_mode.sql:86-112` (`:99`) |
| distance cap | `GREATEST(3, ceil(len·0.45))` | `:212` |
| candidates | other `vocab_id`s, same word language, `definition_level='standard'`, with a reading, length within the cap; **no LIMIT** (whole space searched) | `:220-230` (`:227`) |
| homophones | distance 0 excluded outright (张/章 = zhang1) | `:242` |
| per word / per reading | one candidate per `vocab_id`, then per distinct normalised reading | `:244-257` |
| ranking | same syllable/mora count first, then relative distance, then frequency closeness, then `random()` | `:265-268` |
| syllable count | zh: number of tone digits `[1-5]`; ja: kana minus small kana | `calibration_syllable_count`, `:137-160` (`:151`) |
| display | zh: diacritic pinyin only, parenthesised numbers stripped ("showing the numbered form … gives away tone"); ja: kana with latin suffix stripped | `calibration_display_pronunciation`, `:114-135` |

So: **zh options are tone-marked pinyin (diacritics, no tone numbers); ja options are hiragana.** Tone is kept, so
tone-only minimal pairs are valid foils (MEASURED, §2.4: 519 of 30,929 cached zh foils, on 10.9% of anchors).

**Defect: the zh comparison form has drifted.** `dim_word_senses.pronunciation` for zh standard native rows is now
mostly diacritic-only (`yuán xíng`), not `yuán xíng (yuan2 xing2)` (§2.3):

```sql
WITH z AS (SELECT s.pronunciation, calibration_normalise_pronunciation(s.pronunciation, 1::smallint) norm
           FROM dim_word_senses s
           WHERE s.word_language_id=1 AND s.definition_language_id=1 AND s.definition_level='standard'
             AND s.pronunciation IS NOT NULL AND btrim(s.pronunciation)<>'')
SELECT (pronunciation ~ '\(') has_numbered_suffix, count(*) n,
       count(*) FILTER (WHERE calibration_syllable_count(norm,1::smallint)=0) syllable_count_zero,
       min(norm), max(norm) FROM z GROUP BY 1;
```
| has_numbered_suffix | n | syllable_count_zero | min(norm) | max(norm) |
|---|---|---|---|---|
| false | 6,621 | **6,621** | a | zǔzhuāng |
| true | 1,489 | 0 | a1la1bi3 | zuo4zai4 |

MEASURED: for 6,621 of 8,110 zh readings the normaliser returns a diacritic string, and the syllable count is
0. INFERENCE: a new cache fill would compare numbered and diacritic strings against each other (large, meaningless
distances) and would rank every candidate as "same syllable count" (0 = 0). This loses the shape guard that
TASK-762 measured as necessary. The pronunciation cache was built in September 2026 (§2.2), before the format
change, and renders the live text correctly, so existing items are fine. **Fix the normaliser, for example by
deriving tone digits from the diacritics, before any zh pronunciation refill** (TASK-1063, or a new paired bank).

### 1.4 What is stored per response

Live columns (`information_schema.columns`, §A.3):

- `calibration_sessions`: id, user_id, word_language_id, definition_language_id, started_at, **ended_at**,
  items_served, items_answered, items_correct, **mode** (CHECK `definition|pronunciation`), bkt_applied_at.
- `calibration_responses` (one per item **served**): id, session_id, user_id, anchor_sense_id, anchor_vocab_id,
  anchor_zipf, zipf_band, chosen_sense_id, is_correct, latency_ms, served_at, answered_at. **No mode, item kind,
  `skip_allowed` or sense rank per response**: mode is inferred from the session.
- `calibration_response_options` (one per option rendered, 4 per item): response_id, sense_id, vocab_id, is_key,
  position, similarity (definition mode), frequency, freq_tier (edit distance in pronunciation mode),
  was_chosen.

Grading, `calibration_record_answer` (live; `migrations/task769_calibration_record_answer.sql:69-169`):
checks ownership, session and that the item is not already answered. `is_correct = COALESCE(chosen_is_key, false)`
(`:138`), so **a skip (`position` NULL) is stored as `chosen_sense_id NULL, is_correct false`**. It sets
`latency_ms` and `answered_at` (`:144-145`), marks `was_chosen` and bumps the session counters. Latency is measured
on the client from render to click (`static/js/pages/calibration.js:273, 339`). (MEASURED)

### 1.5 How sessions end

- Only by `POST /api/calibration/end` (`routes/calibration.py:189-200`), which the page calls from Finish.
  `end_session` (`services/calibration_service.py:731-773`) discards unanswered prefetched rows
  (`calibration_discard_unanswered`), sets `ended_at`, computes the session report and publishes pooled ability
  to `user_calibration_state` (`:569-609`). In definition mode it also writes BKT (`:642-728`) and calls the
  guarded rating writer (`:612-639`). (MEASURED)
- There is **no stopping rule** and no server-side timeout or end. (MEASURED)
- Live consequence (§3.1): **74 of 79 sessions have `ended_at` NULL**, and 1,005 of 1,349 response rows (74.5%)
  are served-but-unanswered prefetch leftovers. de6fd05b's 9 ja definition sessions (178 answers) were never
  ended, so they have **no `user_calibration_state` definition row and `bkt_applied_at` is NULL on all of
  them**. The learner's only state row is from the one ended pronunciation session. (MEASURED)
- Wiki contradiction: `wiki/features/calibration.md:122-126` and `calibration.tech.md:260-266` say Calibration
  does not write ELO. The code calls `apply_calibration_to_skill_ratings` at `/end`
  (`services/calibration_service.py:766-772`, `routes/calibration.py:14-17`), gated by G1–G6
  (`migrations/task747_apply_calibration_to_skill_ratings.sql:16-22`: definition state row, ≥ 20 items,
  SE ≤ 0.75, ≤ 90 days old, no test in the last hour, ≤ 1 adjustment per 7 days). (MEASURED)

### 1.6 What is written to BKT, and the update rule

`apply_calibration_to_vocabulary` (`services/calibration_service.py:642-728`):

- Definition mode only (`:671-673`). The session is claimed once through
  `UPDATE … SET bkt_applied_at = now() WHERE bkt_applied_at IS NULL` (`:679-688`).
- Rows with `answered_at` and `is_correct` set (a skip is included as wrong; never-answered items are ignored,
  `:690-700`, per ADR-033 revision (c) item 4) are sent as `{sense_id: anchor_sense_id, is_correct}` to
  `update_vocabulary_from_word_tests_batch` with `side_effects=False` (`:704-708`). (MEASURED)
- Live RPC body (§A.2): duplicates within the batch are merged with `bool_or`. Prior when there is no row: Zipf
  ≥ 6 → 0.85, ≥ 5 → 0.65, ≥ 4 → 0.35, ≥ 3 → 0.15, else 0.05, NULL → 0.10. Then `bkt_update_word_test`:
  `bkt_update(p, correct, slip 0.05, guess 0.25)`, followed by `p + (1 − p)·0.05` transit, clamped to
  [0.02, 0.98]. The row is upserted, `evidence_count`, `word_test_correct` and `word_test_wrong` are incremented,
  and `user_marked_unknown` is preserved. (MEASURED)
- **The sense written is the anchor sense row.** For ja/en that is the ja word's English-gloss row, not its
  native row; ADR-047 problem 3 records that one meaning is spread across several sense rows. Pronunciation
  answers are never written. (MEASURED / INFERENCE on the consequence)
- One correct answer from the 0.35 prior gives `bkt_update` = 0.35·0.95 / (0.35·0.95 + 0.65·0.25) = 0.672, and
  with transit 0.688. One wrong answer gives 0.35·0.05 / (0.35·0.05 + 0.65·0.75) = 0.035, and with transit
  0.083. (ESTIMATE, arithmetic from the live constants.)

### 1.7 The ability estimate

- `calibration_ability(session)` (live; `calibration_sessions_and_ability.sql:343-…`): per-band n, correct and
  `known_share = correct/n` for one session, plus an old band-interpolation crossing and confidence. The service
  **overrides** the crossings and the confidence (`services/calibration_service.py:451-506`). (MEASURED)
- `_fit_ability` (`calibration_service.py:340-436`): maximum likelihood over raw (anchor_zipf, correct) pairs with
  `p(z) = 0.25 + 0.75·σ(a·(z − b))`, guess fixed at 0.25 (`:43`, `:315-337`). It uses a coarse-to-fine grid over
  slope (log-spaced 0.5–26) and midpoint. It returns `z85 = b + ln(0.85/0.15)/a` and `z50 = b`. It returns None
  if there are fewer than 12 answers, all answers are the same, the Zipf span is under 0.5, the slope is under
  0.35, the likelihood-ratio gain over a constant-accuracy model is under 3.0, or the crossing lies outside the
  observed Zipf range (`:363-436`). **A skip is a wrong answer here** (`_fit_points`, `:439-448`). (MEASURED)
- **SE** = `expected_sd(n)`, a lookup by answer count from 60 simulated learners per row (`:58-99`; 0.63 at
  20, 0.27 at 60, 0.16 at 120). It is not this learner's posterior SD, and it assumes stratified (non-adaptive)
  sampling. Confidence: SD > 0.40 low, > 0.20 medium, else good (`:495-505`). (MEASURED)
- `pooled_ability` (`:509-566`) fits across all of a user's sessions for one **word language** and mode. It does
  not filter by definition language (`:526-532`), whereas ADR-051 uses one definition language per estimate.
  `write_calibration_state` upserts `user_calibration_state` with PK (user, language, mode) (`:569-609`).
  (MEASURED)
- Check against live data (script `placement/scripts/skip_fit.py`, run with `python3 -I` on the scratchpad
  exports): de6fd05b pronunciation (99 answers) gives slope 1.88, midpoint 4.60, **z85 5.52**, against the stored
  `user_calibration_state.ability_zipf = 5.49` (the 0.03 gap is grid resolution). With a **skip-aware**
  likelihood (known → right; not known → skip with probability s, otherwise a 1-in-4 guess), the same data gives
  midpoint 3.80 and z85 5.94; definition data gives midpoint 5.04 → 4.64 and z85 5.79 → 6.15. ESTIMATE, one
  learner: **how skips enter the likelihood moves the curve by 0.4–0.8 Zipf**. This learner skips about 4 times as
  often as they pick wrong, so the "skip = wrong guess" assumption (75% wrong when not known) is badly
  mis-specified for them. ADR-051's estimator already treats a skip as "not known", so the two outputs disagree
  (ADR-051 Consequences, OQ33).

---

## 2. Item bank readiness for a paired meaning-and-reading design

Pairing has to happen at the **word (vocab_id)** level. A ja/en meaning anchor is the English-gloss sense row,
while the ja reading anchor is the native ja/ja row of the same `vocab_id` (§1.1). "Ready" means the anchor is in
the pool, not blocklisted, and has a cache row with ≥ 3 options. Meaning anchors are restricted to rank-1 senses,
matching ADR-051's frame and TASK-1062.

### 2.1 Both-ready lemmas by pair and band (MEASURED)

```sql
WITH pool AS (
  SELECT p.*, s.sense_rank,
         EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id=p.sense_id) AS blocked
  FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id=p.sense_id),
defr AS (
  SELECT p.word_language_id w, p.definition_language_id d, p.vocab_id, p.zipf_band,
         bool_or(coalesce(cardinality(c.sense_ids),0) >= 3) AS def_ready
  FROM pool p LEFT JOIN calibration_distractor_cache c ON c.mode='definition' AND c.anchor_sense_id=p.sense_id
  WHERE p.has_embedding AND NOT p.blocked AND p.sense_rank=1 GROUP BY 1,2,3,4),
pronr AS (
  SELECT p.word_language_id w, p.vocab_id,
         bool_or(coalesce(cardinality(c.sense_ids),0) >= 3) AS pron_ready, bool_or(true) AS pron_in_pool
  FROM pool p LEFT JOIN calibration_distractor_cache c ON c.mode='pronunciation' AND c.anchor_sense_id=p.sense_id
  WHERE p.has_pronunciation AND NOT p.blocked AND p.definition_language_id=p.word_language_id GROUP BY 1,2)
SELECT d.w, d.d, d.zipf_band band, count(*) lemmas_rank1,
  count(*) FILTER (WHERE d.def_ready) def_ready, count(*) FILTER (WHERE r.pron_in_pool) pron_in_pool,
  count(*) FILTER (WHERE r.pron_ready) pron_ready, count(*) FILTER (WHERE d.def_ready AND r.pron_ready) both_ready
FROM defr d LEFT JOIN pronr r ON r.w=d.w AND r.vocab_id=d.vocab_id
WHERE d.w IN (1,3) GROUP BY ROLLUP ((d.w, d.d), d.zipf_band) ORDER BY d.w, d.d, band NULLS LAST;
```

zh (zh/en; zh/ja is identical, zh/zh differs by a few lemmas):

| band | Zipf | rank-1 lemmas | meaning ready | reading in pool | reading ready | **both ready** | % |
|---|---|---|---|---|---|---|---|
| 1 | < 3.0 | 303 | 300 | 293 | 278 | **276** | 91% |
| 2 | 3.0–3.5 | 617 | 613 | 607 | 591 | **587** | 95% |
| 3 | 3.5–4.0 | 742 | 738 | 729 | 716 | **712** | 96% |
| 4 | 4.0–4.5 | 691 | 687 | 674 | 672 | **670** | 97% |
| 5 | 4.5–5.0 | 664 | 658 | 653 | 653 | **647** | 97% |
| 6 | 5.0–5.5 | 435 | 433 | 424 | 424 | **422** | 97% |
| 7 | ≥ 5.5 | 171 | 170 | 171 | 169 | **168** | 98% |
| all | | 3,623 | 3,599 | 3,551 | 3,503 | **3,482** | 96% |

zh/zh: 3,643 rank-1 lemmas, 3,499 both ready.

ja (ja/en; ja/zh is identical, ja/ja has 3,158 lemmas and 2,186 both ready):

| band | rank-1 lemmas | meaning ready | reading in pool | reading ready | **both ready** | % |
|---|---|---|---|---|---|---|
| 1 | 577 | 554 | 330 | 306 | **289** | 50% |
| 2 | 425 | 419 | 254 | 250 | **248** | 58% |
| 3 | 621 | 618 | 419 | 415 | **414** | 67% |
| 4 | 655 | 653 | 491 | 491 | **490** | 75% |
| 5 | 537 | 536 | 438 | 436 | **436** | 81% |
| 6 | 283 | 280 | 242 | 242 | **240** | 85% |
| 7 | 77 | 76 | 69 | 69 | **68** | 88% |
| all | 3,175 | 3,136 | 2,243 | 2,209 | **2,185** | 69% |

English: no reading mode (pool en/en has 12 rows with a reading, out of 6,110). (MEASURED)

INFERENCE: a 40-item test that touches about 6 words per band needs only tens of words per band, so raw supply
is not the constraint even in ja band 7 (68). Exposure control and disjoint retakes are what consume the bank.
With 68–169 words in the top band, a few disjoint retakes are possible; dozens are not.

### 2.2 Why Japanese reading coverage is low: mostly a stale pool (MEASURED)

```sql
-- ja rank-1 lemmas not in the reading pool, by reason (band rollup; totals shown)
... (query in §A.4) ...
```
| band | lemmas | in reading pool | hiragana-only (excluded by design) | no reading stored | **other** | katakana-only in reading pool |
|---|---|---|---|---|---|---|
| 1 | 577 | 333 | 6 | 26 | **212** | 136 |
| 2 | 425 | 255 | 2 | 11 | **157** | 48 |
| 3 | 621 | 420 | 4 | 8 | **189** | 26 |
| 4 | 655 | 491 | 2 | 12 | **150** | 4 |
| 5–7 | 897 | 752 | 11 | 14 | **120** | 0 |
| all | 3,175 | 2,251 | 25 | 71 | **828** | 214 |

```sql
SELECT s.word_language_id w,
  count(*) FILTER (WHERE (p.pronunciation IS NULL OR btrim(p.pronunciation)='')
                   AND s.pronunciation IS NOT NULL AND btrim(s.pronunciation)<>'') pool_null_live_has,
  count(*) FILTER (WHERE p.pronunciation IS NOT NULL AND s.pronunciation IS DISTINCT FROM p.pronunciation) pool_differs_live,
  count(*) pool_native_rows
FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id=p.sense_id
WHERE p.definition_language_id=p.word_language_id GROUP BY 1;
```
| w | pool reading NULL, live has one | pool reading differs from live | pool native rows |
|---|---|---|---|
| zh | 60 | 2,506 (numbered suffix dropped, §1.3) | 4,048 |
| en | 0 | 0 | 6,110 |
| ja | **841** | 31 | 3,278 |

So most of the "other" 828 are words whose reading was written after the last pool refresh. **A pool refresh
followed by a pronunciation cache fill would lift ja to roughly 90%** (ESTIMATE: (2,251 + ~800) / 3,175). The
pool is derived and goes stale silently (`calibration.tech.md:665-681`). In pronunciation mode the **key** text
comes from the pool (`calibration_next_anchors` returns `r.pronunciation` from the pool, `task772:250`), while the
foils are read live. For the 2,506 zh rows that differ, the displayed form is identical (the numbered suffix is
stripped for display), so there is no visible tell today. (MEASURED)

**Katakana-only lemmas** (テレビ etc.) are in the reading pool: 214 ja rank-1 lemmas, 136 of them in band 1. The
refresh excludes only hiragana-only lemmas (`migrations/sense_vectors_native_standard_512.sql:394, 411`). The
reading of a katakana word is a mechanical transliteration into hiragana; live, de6fd05b answered 5 of 5 such
reading items correctly (§3.6). These items should be excluded from reading items. (MEASURED / INFERENCE)

Cache state (MEASURED):

| mode | word lang | built (month) | anchors | avg cached options | < 3 options |
|---|---|---|---|---|---|
| definition | zh | 2026-10 | 11,388 | 5.95 | 58 |
| definition | en | 2026-10 | 6,110 | 6.00 | 1 |
| definition | ja | 2026-10 | 9,807 | 5.93 | 92 |
| pronunciation | zh | **2026-09** | 3,969 | 7.79 | 42 |
| pronunciation | ja | **2026-09** | 2,322 | 7.82 | 35 |

`calibration_distractor_cache_misses`: definition 202 anchors (last attempt 2026-10-29), pronunciation 116 (last
2026-09-23), with an average of about 1.1 options found.

### 2.3 Pronunciation formats in `dim_word_senses.pronunciation` (MEASURED)

```sql
SELECT s.word_language_id w, s.definition_level lvl, ... (full query §A.5)
```
| w | level | native rows | with reading | zh diacritic + (numbered) | zh diacritic only | zh no tone mark | ja hiragana only | ja katakana only | ja romaji only | ja contains kanji |
|---|---|---|---|---|---|---|---|---|---|---|
| zh | simple | 12,788 | 3,867 | 3,867 | 0 | 0 | | | | |
| zh | **standard** | 13,137 | 8,110 | 1,489 | **6,612** | 9 | | | | |
| ja | simple | 3,491 | 2,379 | | | | 2,336 | 3 | 19 | 1 |
| ja | **standard** | 3,491 | 3,399 | | | | **3,383** | 1 | 6 | 1 |

Cross-language gloss rows carry no reading (0 in every group).
- **zh:** tone **marks** (diacritics), e.g. `yuán xíng`. Only 1,489 standard rows still have the `(yuan2 xing2)`
  numbered form. Tone numbers never appear alone. Neutral tone is unmarked (`bēi zi`). 9 rows have no tone mark
  at all.
- **ja:** **hiragana**, never romaji except for 6 data errors (+19 on simple rows), with 1 kanji-containing
  error. The latin loanword suffix (`-Ion`) is gone from current data (0 rows), though the display function
  still strips it.

Sample rendered reading items (key; cached foils with edit distance), MEASURED:
- zh 知道 `zhī dào`: zhí dào [1] | zhī yào [1] | zhì zào [2] | zhǐ dǎo [2] | chí dào [2] … (tone-only foil `zhí dào`)
- zh 机械 `jī xiè`: jī liè [1] | jī qì [2] | jī dì [2] …
- zh 降解塑料 `jiàng jiě sù liào` (4 syllables): jīng jì fù dān [9] | **jiàng jiě [8]** | jiàn guo miàn [9] … (a
  2-syllable prefix of the key and several 3-syllable foils: a shape tell on long words)
- ja 船 `ふね`: ふく | やね | ふた | つね … ; 革新 `かくしん`: そくしん | かくさん | かんしん …

### 2.4 Quality signals relevant to the paired design (MEASURED)

| measure | zh | ja | query |
|---|---|---|---|
| cached reading foils that differ from the key **only in tone** | 519 of 30,929 (1.7%); 433 of 3,969 anchors (10.9%) have one | n/a | §A.6 |
| cached reading foils with a different syllable count (split on spaces) | 2,473 of 30,929 (8.0%) | — | §A.6 |
| rank-1 **meaning keys containing the prompt lemma**: zh/zh, zh/ja, ja/zh, ja/ja, zh/en, ja/en | 19.5%, **16.9%** (zh/ja), 0.0% (zh/en) | 21.6% (ja/zh), 10.6% (ja/ja), 1.0% (ja/en) | §A.7 |
| …of which **no** cached foil contains the lemma (answerable by string matching) | zh/zh 449 (12.1%), **zh/ja 488 (13.3%)** | **ja/zh 440 (13.5%)**, ja/ja 210 (6.4%) | §A.7 |
| zh/ja keys starting with a `headword；` prefix / prefix identical to the zh lemma | 3,682 of 3,682 / **435 (11.8%)** | ja/zh: 700 / 95 (2.9%) | §A.7 |

Example (zh/ja, MEASURED): 林地 → key `林地；たくさんの木が生えている場所`, foils `林区；…`, `植樹する；…`, `植生；…`.
The learner matches 林地 to 林地 without knowing the word. ADR-025's check "definition == own lemma: 0" tested
identical text, not containment. INFERENCE: for Japanese-L1 learners of Chinese (and the reverse), meaning items
in the cross-CJK pairs measure character recognition. The reading item is the part of a paired design that can
show whether they know the Chinese word, which is what the owner asked for. Meaning items for these pairs also
need the `headword；` prefix removed, or the zh/en or ja/en key used instead.

---

## 3. Live response data (anonymised, MEASURED)

### 3.1 Volume

```sql
SELECT s.mode, s.word_language_id w, s.definition_language_id d, count(DISTINCT s.user_id) users,
  count(DISTINCT s.id) sessions, count(r.id) served_rows, count(r.id) FILTER (WHERE r.is_correct IS NOT NULL) answered,
  count(r.id) FILTER (WHERE r.is_correct) correct,
  count(r.id) FILTER (WHERE r.is_correct IS NOT NULL AND r.chosen_sense_id IS NULL) skips, ...
FROM calibration_sessions s LEFT JOIN calibration_responses r ON r.session_id=s.id
GROUP BY ROLLUP ((s.mode, s.word_language_id, s.definition_language_id));
```
| mode | pair | users | sessions | served rows | answered | correct | skips | first / last answer |
|---|---|---|---|---|---|---|---|---|
| definition | zh/zh | 1 | 1 | 15 | 0 | — | — | — |
| definition | zh/en | 1 | 43 | 639 | 39 | 11 | 14 | 2026-11-16 / 11-17 |
| definition | en/en | 1 | 1 | 15 | 0 | — | — | — |
| definition | ja/en | 2 | 29 | 543 | 206 | 93 | 76 | 2026-09-13 / 11-16 |
| pronunciation | ja (def lang en, ignored) | 1 | 5 | 137 | 99 | 58 | 40 | 2026-09-13 / 09-21 |
| **all** | | **3** | **79** | **1,349** | **344** | **162** | **130** | |

No zh reading answers exist. Per user:

| user | mode | pair | sessions | ended | answered | served-unanswered | distinct lemmas | BKT applied |
|---|---|---|---|---|---|---|---|---|
| 110fb390 | definition | zh/zh | 1 | 0 | 0 | 15 | 0 | 0 |
| 110fb390 | definition | zh/en | 43 | 1 | 39 | 600 | 38 | 1 |
| 110fb390 | definition | ja/en | 20 | 3 | 28 | 234 | 28 | 3 |
| 26142069 | definition | en/en | 1 | 0 | 0 | 15 | 0 | 0 |
| de6fd05b | definition | ja/en | 9 | **0** | 178 | 103 | 174 | **0** |
| de6fd05b | pronunciation | ja | 5 | 1 | 99 | 38 | 97 | 0 |

`user_calibration_state`: 110fb390 zh definition (13 answers, ability NULL), 110fb390 ja definition (22, NULL),
de6fd05b ja **pronunciation** (99 answers, ability_zipf 5.49, se 0.207). There is no definition row for de6fd05b.

**110fb390 is very likely an automated or test account**: median latency 364 ms on zh meaning items (four
definitions to read), 25 zh sessions with 1–9 answers each lasting 0–47 s (most 0–2 s), and chance-level
accuracy with a guess-corrected K ≈ 0 or below in most bands (§3.2). ADR-047 flags the test account the same
way. **The only usable data is de6fd05b's**, and the scratchpad export `mock/data/real_events.json` `cal` (178
definition + 99 pronunciation, ja/en) matches it exactly. INFERENCE: validation statistics for a placement test
cannot come from live data yet.

### 3.2 Accuracy by band and mode (n / correct / skips / wrong picks; K = c/n − w/(3n))

de6fd05b, ja:

| band | meaning n | right | skip | wrong | % right | K | reading n | right | skip | wrong | % right | K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 27 | 7 | 17 | 3 | 26 | 0.22 | 13 | 6 | 7 | 0 | 46 | 0.46 |
| 2 | 24 | 6 | 16 | 2 | 25 | 0.22 | 13 | 4 | 8 | 1 | 31 | 0.28 |
| 3 | 26 | 9 | 14 | 3 | 35 | 0.31 | 15 | 5 | 10 | 0 | 33 | 0.33 |
| 4 | 24 | 9 | 12 | 3 | 38 | 0.33 | 14 | 6 | 8 | 0 | 43 | 0.43 |
| 5 | 25 | 13 | 9 | 3 | 52 | 0.48 | 14 | 11 | 3 | 0 | 79 | 0.79 |
| 6 | 26 | 16 | 8 | 2 | 62 | 0.59 | 15 | 13 | 2 | 0 | 87 | 0.87 |
| 7 | 26 | 24 | 0 | 2 | 92 | 0.90 | 15 | 13 | 2 | 0 | 87 | 0.87 |
| all | 178 | 84 | 76 | 18 | 47 | | 99 | 58 | 40 | 1 | 59 | |

110fb390 (zh/en, 39 answers): 14–50% right per band with n = 4–7, and band 7 at 14%. ja/en (28 answers): 0
skips, 25% right overall. Consistent with random clicking.

Observations (INFERENCE, n = 1 learner): the learner rarely guesses. Wrong picks are 10% of meaning answers and
1% of reading answers, so the guess correction barely changes K for them; their skip behaviour drives the
estimate (§1.7). Reading accuracy is above meaning accuracy in bands 1 and 4–6, on different words, which is
plausible for an English-L1 learner who reads kanji compounds without knowing their English meaning. That would
be the "reading only" cell of the paired table.

### 3.3 Latency (ms, client-measured render → click)

| mode | user | outcome | n | p50 | p90 |
|---|---|---|---|---|---|
| definition | de6fd05b | all | 178 | **3,406** | **10,006** |
| | | correct | 84 | 3,340 | 11,557 |
| | | skip | 76 | 3,240 | 9,042 |
| | | wrong | 18 | 4,390 | 6,424 |
| pronunciation | de6fd05b | all | 99 | **3,615** | **7,388** |
| | | correct | 58 | 3,133 | 6,290 |
| | | skip | 40 | 4,970 | 14,682 |
| definition | 110fb390 | zh / ja | 39 / 28 | 364 / 902 | 832 / 2,246 |
| definition | all users | | 245 | 2,744 | 7,847 |

Wall clock per item, including reveal and the learner-paced "Next word" after a wrong answer or skip
(first served → last answered, de6fd05b): 99 items / 635 s = **6.4 s**, 35 / 209 s = 6.0 s, 62 reading / 485 s
= **7.8 s**. ESTIMATE: **a 3-minute test ≈ 25–30 items and a 5-minute test ≈ 40–50 items** at this learner's
pace. A paired design spends two items on each word it tests both ways.

### 3.4 Items per session

| user | mode | sessions with answers | answered per session | median |
|---|---|---|---|---|
| de6fd05b | definition | 8 | 99, 35, 18, 13, 8, 3, 1, 1 | 10.5 |
| de6fd05b | pronunciation | 5 | 62, 22, 8, 6, 1 | 8 |
| 110fb390 | definition zh | 25 | 9, 4, 2, 2, 2, then 1 ×20 | 1 |

### 3.5 Skip rates

de6fd05b: meaning 76/178 = **43%**, reading 40/99 = **40%** (band 1–3 skips 53–67%; band 7 0–13%).
110fb390: zh 14/39 = 36%, ja 0/28 = 0%. All users: 130/344 = 38%.

### 3.6 Same word answered in both modes (meaning vs reading agreement)

```sql
WITH a AS (SELECT s.user_id, s.mode, r.anchor_vocab_id vid, r.zipf_band band, r.is_correct,
                  (r.chosen_sense_id IS NULL) skipped, r.answered_at,
                  row_number() OVER (PARTITION BY s.user_id, s.mode, r.anchor_vocab_id ORDER BY r.answered_at DESC) rn
           FROM calibration_responses r JOIN calibration_sessions s ON s.id=r.session_id WHERE r.is_correct IS NOT NULL),
d AS (SELECT * FROM a WHERE mode='definition' AND rn=1), p AS (SELECT * FROM a WHERE mode='pronunciation' AND rn=1)
SELECT left(d.user_id::text,8) uid, count(*) paired_words,
  count(*) FILTER (WHERE d.is_correct AND p.is_correct) both_right, count(*) FILTER (WHERE d.is_correct AND NOT p.is_correct) meaning_only,
  count(*) FILTER (WHERE NOT d.is_correct AND p.is_correct) reading_only, count(*) FILTER (WHERE NOT d.is_correct AND NOT p.is_correct) neither,
  count(*) FILTER (WHERE p.answered_at < d.answered_at) reading_answered_first
FROM d JOIN p ON p.user_id=d.user_id AND p.vid=d.vid GROUP BY 1;
```
| user | paired words | both right | meaning only | reading only | neither | reading answered first |
|---|---|---|---|---|---|---|
| de6fd05b (ja) | **6** | 3 | 1 | 1 | 1 | 6 |

The words: 実る (band 1: both skipped), どう (7: both right; a hiragana-only lemma served in September, before the
pool excluded such lemmas from reading mode), 人間 (7: meaning right, reading skipped), 話 (7: **meaning wrong**,
reading right; the learner picked the foil "to say; to speak" (similarity 0.613) for the key "talk; a story",
an also-correct risk, ADR-025), 車 and 関係 (7: both right). The readings were answered 2026-09-13 to 09-18 and
the meanings on 2026-10-17. **n = 6 supports no conclusion**; it only shows that all four cells occur.

Other per-learner facts: katakana-only lemmas, reading items 5/5 right; meaning items 12/15 right (80%, against
47% overall: English loanwords are easy meaning items for an English speaker). Rank > 1 senses: 2 of 178 meaning
items.

---

## 4. `services/irt/` — what it can do

`services/irt/calibrator.py` (364 lines; `services/irt/__init__.py` is empty), MEASURED:

- **Model:** 2PL `P = σ(a(θ − b))` per **exercise** (the `exercises` table, vocabulary-ladder items), **no
  guessing parameter** (`:9`, `:55-60`).
- **Person ability:** not estimated. θ is fixed as the logit of the user's raw first-attempt accuracy in the
  language, clipped to [0.05, 0.95] (`:166-181`). This is not a joint or marginal maximum-likelihood fit.
- **Item fit:** L-BFGS-B with an analytic gradient, bounds a ∈ [0.3, 3], b ∈ [−3, 3] (`:40-41`, `:72-110`). The
  SE of b comes from the expected-information Hessian (`:95-108`; the `(y − p)·0.0` term on `:101` is a no-op).
  Prior: shrinkage toward the tier-seeded `irt_difficulty` with pseudocount 10 (`:36`, `:113-115`). At least 20
  first attempts per exercise (`:47`).
- **Data:** `user_exercise_history` first attempts (`:122-141`). Writes through `irt_apply_calibration`
  (`:188-202`). Nightly at 04:00 UTC via `web/scheduler.py:76-78`, guarded by an advisory lock (`:209-229`).
- **Live:** `SELECT count(*) FROM exercises WHERE irt_calibrated_at IS NOT NULL` → **0 of 144,374**; there is
  no `last_calibrated`. The job has never produced a fit.
- **Missing for a CAT:** a person-ability estimator (MLE, EAP or MAP with a prior), test information, item
  selection, a stopping rule, exposure control, a guessing floor, a skip model, and any connection to calibration
  anchors.

INFERENCE on fit with a 2PL/3PL CAT: the module is **not** a basis for a placement CAT. With 3 users, no
per-item
calibration of anchors is possible for a long time (the module itself requires 20 attempts per item). The model
that fits is the one Calibration already uses: an **explanatory IRT model** where item difficulty is a function of
Zipf (plus item kind, meaning or reading, and a language-pair or L1 term for CJK cognates), with a fixed guessing
floor of 0.25 and a person parameter. That is `_fit_ability` (`calibration_service.py:315-337`) re-expressed with
θ as the person parameter and `b_i = β0 + β1·zipf_i (+ kind, pair terms)`. A CAT then needs EAP over θ with a
prior (for example from the stated exam level or ADR-047's default ability), selection of the next anchor's band
near the current θ by maximum information (with some spread so the slope stays identifiable), and a stop when the
posterior SD falls below a target. The reusable parts are the bounded optimiser pattern (`fit_2pl`) and the
guess-floored likelihood and grid (`_log_likelihood`, `_fit_ability`); EAP over a 1-D θ grid needs nothing beyond
`math`. The population constants (β1 slope, kind and pair offsets) would have to start from simulation and
ADR-024/047 constants and be refitted later on pooled data, for example via `scipy` (already a dependency,
`calibrator.py:28`).

---

## 5. Constraints for a new design

### 5.1 Sizes (MEASURED)

```sql
SELECT c.relname, pg_total_relation_size(c.oid) total_b, ... ; SELECT pg_database_size(current_database());
```
| relation | rows | total | heap | indexes |
|---|---|---|---|---|
| **database** | | **513,535,123 B** (513.5 MB decimal; `pg_size_pretty` 490 MB = MiB) | | |
| dim_word_senses | ~72,259 | 54 MB | 45 MB | 9.6 MB |
| calibration_anchor_pool | 27,356 | 9.6 MiB | 7.3 MiB | 2.3 MiB |
| calibration_distractor_cache | 33,599 | 6.9 MiB | 5.6 MiB | 1.2 MiB |
| dim_vocabulary | ~20,613 | 5.6 MiB | | |
| calibration_response_options | 5,396 | 696 KiB | 368 KiB | 296 KiB |
| calibration_responses | 1,349 | 432 KiB | 200 KiB | 200 KiB |
| calibration_anchor_blocklist | ~648 | 272 KiB | | |
| calibration_distractor_cache_misses | ~297 | 112 KiB | | |
| calibration_sessions | 79 | 88 KiB | | |
| user_calibration_state | 3 | 48 KiB | | |
| **calibration total** | | **≈ 18.6 MB** | | |

Average tuple sizes (`pg_column_size`): response 100 B, option 56 B, pool 133 B, packed cache 169 B. Indexes:
responses have a pkey, `(anchor_sense_id)` and `(session_id, served_at)`; options have a pkey
`(response_id, sense_id)` and a partial index on chosen distractors.

ESTIMATE, storage per answered item at scale: a response is ≈ 100 B tuple + ~30 B overhead + 3 index entries
≈ 60 B, about 190 B. Four options are ≈ 4 × (56 + ~30 + ~25) ≈ 440 B. That is about **0.6 KB per item**, with
the current small tables measuring 0.86 KB because of page overhead. **A 40-item placement is ≈ 25–35 KB; 1,000
placements ≈ 25–35 MB.** The prefetch leftovers (74.5% of response rows today) multiply this unless a placement
ends server-side and discards them, or prefetches less. The per-option table is 4 rows per item; a packed layout
(as ADR-039 did for the cache) or storing only the chosen and key option ids would cut it by roughly 3×.

The cap: the Free plan limit is 500 MB. Measured 513.5 MB (decimal) / 490 MiB on 2026-11-18, the same as the
2026-11-17 figure in the brief. I could not verify from here whether Supabase counts the cap in MB or MiB.
TASK-1063's pool refresh is estimated at ≈ 5–7 MB (knowledge-report.tasks.md:971). A ja pool refresh adds only
reading flags on existing rows plus about 840 pronunciation cache rows (≈ 840 × ~200 B ≈ 0.2 MB, ESTIMATE).

### 5.2 What would need a migration (INFERENCE from the live schema and code)

| need | why | objects |
|---|---|---|
| A **placement** session kind or **mixed-mode** sessions | `calibration_sessions.mode` and `user_calibration_state.mode` are CHECK-constrained to `definition|pronunciation`; a session has one mode; responses carry no mode, so `pooled_ability`, `write_calibration_state`, `apply_calibration_to_vocabulary` and `calibration_ability` would mis-pool a session that mixes meaning and reading items | CHECK constraints `calibration_sessions_mode_chk`, `user_calibration_state_mode_chk`; add `calibration_responses.item_kind` (or `mode`), or link two sessions per placement |
| **Adaptive selection** | `calibration_next_anchors` has no ability input; the band is chosen by session load | new function (target band or Zipf window, rank-1 only, paired word) — overlaps TASK-1062 |
| **Pairing by word** | meaning and reading anchors are different sense rows of one `vocab_id`; exclusion is by `anchor_sense_id` | selection keyed on `vocab_id`; exclusion on `anchor_vocab_id` |
| **Disjoint retakes** | exclusion is per session | per-user exclusion window (`calibration_responses` by `user_id, anchor_vocab_id`; index exists only on `anchor_sense_id`) |
| **Hide the reading on meaning items when paired** | `calibration_build_items` returns `pronunciation` in definition mode (`packed:345`) | function change (or a client flag) |
| **Server-side end / stop** | publishing, BKT and rating writes run only at `/end`; 74 of 79 sessions never ended | service and route change; the stopping rule decides the end |
| **zh normaliser** | 6,621 of 8,110 readings normalise to diacritics with syllable count 0 | `calibration_normalise_pronunciation`, `calibration_syllable_count` (derive tone digits from diacritics), then refill the zh pronunciation cache |
| **Exclude katakana-only lemmas from reading items** | trivial transliteration (214 ja lemmas) | `calibration_refresh_anchor_pool` predicate |
| **Pool refresh** | ja readings stale (841 rows); zh pool stale (TASK-1063) | data only (`scripts/build_calibration_distractor_cache.py --refresh-pool`, then fill) |
| **Cross-CJK meaning keys** | `headword；` prefix identical to the lemma (zh/ja 11.8%); ≥ 13% answerable by string match | display-time strip of the prefix, or exclude or flag such anchors for those pairs |
| **Skip-aware evidence and evidence kind** | a skip is stored as wrong; placement evidence must be its own kind (TASK-1065) and never "rated known" | `skip_allowed` / `skip_kind` (TASK-1061); evidence-kind counters (TASK-1065) |
| Optional: **lighter per-item storage** | 4 option rows per item | packed options column, or chosen and key only |

No migration is needed to **read** what exists: the pool, cache and `calibration_cached_options` already support
both item kinds for zh and ja.

---

## Appendix A — queries and raw outputs not shown inline

### A.1 Function inventory (live)
```sql
SELECT p.proname, pg_get_function_identity_arguments(p.oid), length(p.prosrc), p.prosecdef, p.provolatile
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public' AND (p.proname ILIKE '%calibration%' OR p.proname ILIKE '%distractor%'
  OR p.proname ILIKE 'bkt_update%' OR p.proname='update_vocabulary_from_word_tests_batch' OR p.proname ILIKE '%pronunciation%');
```
29 functions, including `calibration_build_items` (5,133 chars, SECURITY DEFINER, volatile), `calibration_next_anchors`
(2,523, definer, stable), `calibration_record_answer` (2,689), `calibration_ability` (3,127), `pronunciation_distractors`
(4,018), `semantic_distractors` (5,088), `apply_calibration_to_skill_ratings` (6,187), `update_vocabulary_from_word_tests_batch`
(2,862, invoker), `bkt_update_word_test` (255, immutable), `irt_apply_calibration` (302).

### A.2 Bodies read
`SELECT pg_get_functiondef(oid)` / `prosrc` for: calibration_build_items, calibration_next_anchors, calibration_next_anchor,
calibration_record_answer, calibration_ability, calibration_cached_options, calibration_zipf_band, calibration_band_midpoint,
calibration_discard_unanswered, pronunciation_distractors, calibration_normalise_pronunciation,
calibration_display_pronunciation, calibration_syllable_count, calibration_fill_distractor_cache,
calibration_refresh_anchor_pool, update_vocabulary_from_word_tests_batch, bkt_update_word_test, bkt_update.
Key live lines are quoted in §1. The live bodies match the cited migration files on every line quoted.

`bkt_update(p, correct, slip, guess)`: obs_knows = correct ? 1−slip : slip; obs_not = correct ? guess : 1−guess;
returns clamp(obs_knows·p / (obs_knows·p + obs_not·(1−p)), 0.02, 0.98).
`bkt_update_word_test(p, correct)`: `bkt_update(p, correct, 0.05, 0.25)`, then `p + (1−p)·0.05`, clamped to [0.02, 0.98].

### A.3 Columns
```sql
SELECT table_name, string_agg(column_name||' '||data_type||CASE WHEN is_nullable='NO' THEN ' NN' ELSE '' END, ', ' ORDER BY ordinal_position)
FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('calibration_sessions','calibration_responses',
 'calibration_response_options','calibration_anchor_pool','calibration_distractor_cache','calibration_distractor_cache_misses',
 'calibration_anchor_blocklist','user_calibration_state') GROUP BY table_name;
```
Output summarised in §1.4. Pool: word_language_id, definition_language_id, sense_id, vocab_id, lemma, definition,
pronunciation, zipf, zipf_band, has_embedding, has_pronunciation. Cache: anchor_sense_id, mode, sense_ids[],
similarities[], freq_tiers[], built_at. Constraints: §5.2 (query on `pg_constraint`).

### A.4 ja reading-pool reasons
```sql
WITH r1 AS (SELECT DISTINCT ON (p.vocab_id) p.vocab_id, p.lemma, p.zipf_band FROM calibration_anchor_pool p
            JOIN dim_word_senses s ON s.id=p.sense_id
            WHERE p.word_language_id=3 AND p.definition_language_id=2 AND p.has_embedding AND s.sense_rank=1
              AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id=p.sense_id)),
nat AS (SELECT vocab_id, bool_or(pronunciation IS NOT NULL AND btrim(pronunciation)<>'') has_any_pron FROM dim_word_senses
        WHERE word_language_id=3 AND definition_language_id=3 AND definition_level='standard' GROUP BY 1),
pp AS (SELECT DISTINCT vocab_id FROM calibration_anchor_pool WHERE word_language_id=3 AND definition_language_id=3 AND has_pronunciation)
SELECT r1.zipf_band, count(*), count(*) FILTER (WHERE pp.vocab_id IS NOT NULL),
  count(*) FILTER (WHERE pp.vocab_id IS NULL AND r1.lemma ~ '^[ぁ-ゟー]+$'),
  count(*) FILTER (WHERE pp.vocab_id IS NULL AND r1.lemma !~ '^[ぁ-ゟー]+$' AND NOT coalesce(nat.has_any_pron,false)),
  count(*) FILTER (WHERE pp.vocab_id IS NULL AND r1.lemma !~ '^[ぁ-ゟー]+$' AND coalesce(nat.has_any_pron,false)),
  count(*) FILTER (WHERE pp.vocab_id IS NOT NULL AND r1.lemma ~ '^[ァ-ヿー・]+$')
FROM r1 LEFT JOIN pp USING (vocab_id) LEFT JOIN nat USING (vocab_id) GROUP BY ROLLUP (r1.zipf_band);
```
Native ja standard rows with a reading (non-hiragana lemma, Zipf known): 3,333; not in the pool at all: 157 (created
2026-06-15 … 2026-11-12); in the pool with `has_pronunciation = false`: 837.

### A.5 Pronunciation formats
```sql
SELECT s.word_language_id, s.definition_level,
  count(*) FILTER (WHERE s.definition_language_id=s.word_language_id) native_rows,
  count(*) FILTER (WHERE s.definition_language_id=s.word_language_id AND s.pronunciation IS NOT NULL AND btrim(s.pronunciation)<>'') native_with_pron,
  count(*) FILTER (WHERE s.definition_language_id<>s.word_language_id AND s.pronunciation IS NOT NULL) gloss_rows_with_pron,
  count(*) FILTER (WHERE s.word_language_id=1 AND s.pronunciation ~ '\([a-zü:]+[1-5]') zh_diacritic_plus_numbered,
  count(*) FILTER (WHERE s.word_language_id=1 AND s.pronunciation !~ '\(' AND s.pronunciation ~ '[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]') zh_diacritic_only,
  count(*) FILTER (WHERE s.word_language_id=1 AND s.pronunciation !~ '\(' AND s.pronunciation ~ '^[a-zü: ]*[1-5]') zh_numbered_only,
  count(*) FILTER (WHERE s.word_language_id=1 AND s.pronunciation IS NOT NULL AND s.pronunciation !~ '[1-5āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]') zh_no_tone,
  count(*) FILTER (WHERE s.word_language_id=3 AND s.pronunciation ~ '^[ぁ-ゟー]+$') ja_hiragana_only, ... katakana, latin suffix, romaji, kanji
FROM dim_word_senses s WHERE s.word_language_id IN (1,3) GROUP BY 1,2;
```
Output in §2.3.

### A.6 zh tone-only and syllable-mismatch foils
```sql
WITH k AS (SELECT c.anchor_sense_id, calibration_display_pronunciation(s.pronunciation,1::smallint) key_disp
           FROM calibration_distractor_cache c JOIN dim_word_senses s ON s.id=c.anchor_sense_id
           WHERE c.mode='pronunciation' AND s.word_language_id=1),
o AS (SELECT k.anchor_sense_id, k.key_disp, x.option_text FROM k CROSS JOIN LATERAL calibration_cached_options('pronunciation', k.anchor_sense_id) x),
t AS (SELECT *, translate(lower(key_disp),'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü','aaaaeeeeiiiioooouuuuvvvvv') kt,
               translate(lower(option_text),'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü','aaaaeeeeiiiioooouuuuvvvvv') ot FROM o)
SELECT count(DISTINCT anchor_sense_id), count(*), count(*) FILTER (WHERE kt=ot),
       count(DISTINCT anchor_sense_id) FILTER (WHERE kt=ot),
       count(*) FILTER (WHERE array_length(string_to_array(key_disp,' '),1) <> array_length(string_to_array(option_text,' '),1))
FROM t;
-- 3,969 | 30,929 | 519 | 433 | 2,473
```

### A.7 Prompt-in-key (shared characters)
```sql
SELECT p.word_language_id, p.definition_language_id, count(*),
  count(*) FILTER (WHERE strpos(p.definition, p.lemma) > 0),
  count(*) FILTER (WHERE length(p.lemma)>=2 AND strpos(p.definition, p.lemma) > 0)
FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id=p.sense_id
WHERE s.sense_rank=1 AND p.has_embedding AND p.word_language_id IN (1,3) GROUP BY 1,2;
```
| w/d | rank-1 anchors | key contains lemma | % | multi-char lemma |
|---|---|---|---|---|
| zh/zh | 3,721 | 727 | 19.5 | 614 |
| zh/en | 3,682 | 0 | 0.0 | 0 |
| zh/ja | 3,682 | 622 | 16.9 | 531 |
| ja/zh | 3,263 | 705 | 21.6 | 545 |
| ja/en | 3,263 | 32 | 1.0 | 26 |
| ja/ja | 3,263 | 347 | 10.6 | 240 |

Then, among those, anchors where none of the 6 cached definition foils contains the lemma (so none of the 3 served can):
zh/zh 449, zh/ja 488, ja/zh 440, ja/ja 210 (query: the same set, with
`(SELECT count(*) FROM calibration_cached_options('definition', sense_id) o WHERE strpos(o.option_text, lemma) > 0) = 0`).
Headword-prefix query: `split_part(replace(definition,';','；'),'；',1) = lemma` → zh/ja 435 of 3,682 (11.8%);
ja/zh 95 of 3,263 (2.9%); `definition ~ '^[^；;—]{1,12}[；;]'` → zh/ja 3,682, ja/zh 700, zh/zh 117, ja/ja 0.

### A.8 Not verified
- Whether the Supabase Free cap is counted in MB (10^6) or MiB.
- The live `semantic_distractors` and `apply_calibration_to_skill_ratings` bodies were not re-read line by line (only
  inventoried); their behaviour is cited from the migrations and wiki.
- `pronunciation_distractors` cannot be executed from the SQL console (`auth.role()` is NULL → 42501), so the claim
  that a new zh fill degrades is inferred from the normaliser output, not from a test fill.
- The skip-aware refit (§1.7) uses a coarse grid over the skip propensity s ∈ {0.5 … 0.95}; the pronunciation optimum
  sits at the grid edge (0.95). It is illustrative, not an estimator proposal.
