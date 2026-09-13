---
title: "Calibration — Task Breakdown"
feature: calibration
prose_page: ../features/calibration.md
tech_page: ../features/calibration.tech.md
total_tasks: 26
done: 23
last_updated: 2026-09-14
---

# Calibration — Task Breakdown

Phases 1-3 are complete and live as of 2026-09-08: the **distractor foundation**
(TASK-753 – TASK-756), the **engine and UI** (TASK-758 – TASK-761), and
**pronunciation mode + the corrected estimator** (TASK-762, TASK-764).

Phase 4 (TASK-757, TASK-766) added the dictionary screen and the handoff to test
selection. **TASK-765** (applying the Phase 4 migration) was verified live on
2026-09-10.

Phase 5 (TASK-769 – TASK-775, 2026-09-13) is **latency**. The run was measured at
2.9 s per item correct and 3.7 s wrong, and essentially none of it was computation:
eight round trips to grade a click, seven to serve a word, on a link whose median
round trip is ~65 ms, plus two RPCs that between them cost ~1.5 s because the
instance cannot hold the HNSW indexes they read. The fix is one round trip per
action, items precomputed and prefetched, and — separately — a learner who decides
for themselves when to leave a wrong answer.

One task remains: **TASK-763** needs real learner traffic that does not exist yet.

2026-09-14: **TASK-776** (drop synonym foils that share a head gloss — found via 先生/教師)
is written but awaits live apply + cache rebuild. **TASK-777** (offline LLM synonym judge) is
parked as an open question.

---

## TASK-753: Backfill the missing sense embeddings

**Status:** [x] Done — 2026-09-08
**Feature:** calibration
**Type:** infra
**Complexity:** S
**Depends On:** none

**Description:**
`dim_word_senses.embedding` covered five of seven word/definition language combinations.
**ja/en was 0 of 7,126** — the combination an English speaker studying Japanese sees, i.e. the
primary Calibration use case — and zh/en and zh/ja were at 70%.

**Root cause (established before re-running, as required):** not a filter or pagination bug.
`fetch_pending()` was verified against ground truth and returns all 7,546 pending ja rows with
zero skips. The gap is an **operator-gated step that was never run**: the
`cross-language-glosses` skill writes gloss rows with *no* embed-on-write (unlike
`SenseGenerator._write_two_levels`), and its Stage 4 re-embed is a separate manual command. The
ja/zh glosses were uploaded 2026-09-03 and Stage 4 was run (94%); the ja/en glosses were
uploaded 2026-09-04 and it never was (0%).

**Acceptance Criteria:**
- [x] Cause identified and shown not to be a filter/pagination defect
- [x] ja/en confirmed to go 0 → 7,126
- [x] All seven combinations at 100%, zero unembedded senses
- [x] Actual cost reported

**Outcome:** 12,168 embedded in the first pass at **$0.0025**; 87 transient failures
(`PGRST002` schema-cache invalidation caused by concurrently applying DDL, plus one timeout and
one connection reset) closed by an idempotent re-run at ~$0.0000. **Final: 56,022 / 56,022.**

---

## TASK-754: Make filtered vector search index-backed

**Status:** [x] Done — 2026-09-08
**Feature:** calibration
**Type:** infra
**Complexity:** M
**Depends On:** TASK-753

**Description:**
Add `dim_word_senses.word_language_id` (derived by trigger), replace the unused global HNSW
index with partial indexes keyed on both languages, and retire the broken `nearest_senses()`.

**Acceptance Criteria:**
- [x] `word_language_id` backfilled, `NOT NULL`, 0 disagreements with `dim_vocabulary`
- [x] Derive trigger makes it impossible to insert a sense without it or with a wrong value
- [x] Filtered vector query plans as an index scan, not a sequential scan
- [x] `nearest_senses()` timeout gone (function dropped; 0 rows in `pg_proc`)

**Notes:** The intended three-index design (one per word language) was **rejected on
measurement** — 3,947 ms versus 19 ms for seven pair-keyed indexes. See
[[decisions/ADR-025-semantic-distractor-selection]]. Two operational traps found and recorded:
the full-table backfill must run *after* dropping the 482 MB HNSW index (it timed out
otherwise), and parallel index builds fail on this instance for lack of /dev/shm.

**Files:** `migrations/calibration_sense_word_language_and_partial_hnsw.sql`

---

## TASK-755: The semantic distractor RPC

**Status:** [x] Done — 2026-09-08
**Feature:** calibration
**Type:** feature
**Complexity:** M
**Depends On:** TASK-754

**Description:**
`semantic_distractors()` plus `dim_distractor_bands` (measured per-pair cosine floors) and
`shared_prefix_len()`.

**Acceptance Criteria:**
- [x] Excludes the anchor's `vocab_id` siblings, not just the anchor row
- [x] Floor and ceiling are **parameters**, defaulting from a measured table
- [x] Frequency read as a **Zipf score**, and the frequency band relaxes before the cosine floor
- [x] Returns sense id, lemma, definition, similarity and frequency
- [x] ja/en band measured and recorded (0.36 floor; could not be measured before TASK-753)

**Files:** `migrations/calibration_semantic_distractors.sql`

---

## TASK-756: Sample and read real items

**Status:** [x] Done — 2026-09-08
**Feature:** calibration
**Type:** test
**Complexity:** S
**Depends On:** TASK-755

**Description:**
Dump ~200 items per language pair and **read them**. The failure that matters — foils that are
not tempting — passes every mechanical assertion, so this step is a human read, not a test.

**Acceptance Criteria:**
- [x] 1,400 items dumped across all seven pairs and read
- [x] Mechanical failure modes counted: 0 sibling leaks, 0 lemma-repeats, 0 duplicate options,
      1 short item in 1,400
- [x] "Is the definition just the lemma repeated?" quantified and designed out

**Outcome:** Found a defect that reasoning had missed — **11.3% of en/en foils were
morphological variants of the anchor** (precision/precise, trade/trading, culture/cultural).
They are separate `vocab_id` rows, so the sibling exclusion never saw them, and their
definitions are frequently also-correct. Added the stem guard (filter 5); 68/600 → 0/600 with
no increase in short items. Also confirmed the lemma-repeat problem is confined to
`definition_level = 'simple'` (ja/zh 14.3%, zh/ja 11.8%, standard 0.0%), which is why the RPC
filters to `'standard'`.

**Files:** `scripts/dump_calibration_distractors.py`

---

## TASK-757: Fix dictionary entries whose definition does not define the lemma

**Status:** [x] Screened and contained — 2026-09-09. The dictionary itself is still
unrepaired at source; see the note at the end.
**Feature:** calibration
**Type:** bug
**Complexity:** M
**Depends On:** none

**Description:**
Surfaced by TASK-756. Some `dim_word_senses` rows are keyed to a multiword idiom but stored
under the bare lemma — sense 14968 is lemma `hand` defined as "Closely connected or associated
with something else", which defines *hand in hand*. The picker behaves correctly and the item
is still broken, because the key does not define the prompt. This is a dictionary defect, not a
distractor defect, and it will corrupt any Calibration measurement built on those rows.

**Acceptance Criteria:**
- [x] Quantify how many senses have this shape, per language
- [x] Decide per case: exclude from Calibration (blocklist); source repair deferred
- [x] Calibration anchor selection skips any that remain

**Outcome — two defects, not one, needing different detectors.**

*Definitions that do not define the headword* are semantic, so they need a model:
the embeddings cannot see it (the lemma is inside every vector) and no string rule
can. All three languages swept, 14,400 senses, `google/gemini-3.5-flash-lite`,
757 calls, **$1.33**, 0 failed batches:

| language | senses | flagged | rate | self-reference FPs suppressed |
|---|---|---|---|---|
| en | 6,555 | 318 | 4.85% | 117 |
| ja | 3,563 | 154 | 4.32% | 4 |
| zh | 4,282 | 121 | 2.83% | 6 |

The guard did more work than the model. The first pass ran at ~55% precision,
flagging `associate` for "defining" *associate (noun)* and `tending` for *tend* —
inflections of the headword, not the defect. It compares whole normalised strings,
**not leading tokens**: a first-token version suppressed `hand` → "hand in hand",
the exact true positive being hunted. Hand-checked sample after the fix: 5/5.

Real finds, and the pattern is not English-specific: `work` defined as
*agriculture*; `vast` as *various*; ja `図書` (books) carrying 図書館's (library)
definition; ja `例えば` defined as 印刷機; zh `先河` → 开先河. Sense 14178 `land`
holds the string *"The word 'land' does not appear in the provided target
sentence"* — a generation error persisted as dictionary content.

*Malformed lemmas* are orthographic and need no model: **90 ja lemmas (270 senses)**
are MeCab morpheme sequences (`作る れる ます`, `ゲーム を 為る`). The rule is exact,
not heuristic — zh/ja do not use spaces, so a space in the lemma cannot be part of
the word. Measured zh 0, ja 90; English excluded, since multi-word English lemmas
are ordinary.

**Superseded 2026-09-11 — see TASK-767 and TASK-768.** The blocklist originally
protected Calibration only; TASK-767 made it bind every exercise consumer, and
TASK-768 repaired 430 of the flagged definitions at source, cutting the list from
817 to 355.

**Files:** `scripts/screen_sense_definition_mismatch.py`

---

## TASK-767: Make the sense blocklist bind exercise generation and practice

**Status:** [x] Done — applied live 2026-09-11
**Feature:** calibration
**Type:** bug
**Complexity:** S
**Depends On:** TASK-757

**Description:**
`calibration_anchor_blocklist` was read only by the two Calibration picker RPCs, so on
2026-09-11 225 active exercises across 27 blocklisted senses were still being served,
each built on a known-bad definition. Every serving path already filters
`exercises.is_active`, so the quarantine is enforced at the table rather than in each
reader: an exercise on a blocklisted sense is never active.

**Acceptance Criteria:**
- [x] No active exercise on a blocklisted sense (backfilled: 225 retired)
- [x] Any insert/update of an exercise for a blocklisted sense lands inactive
- [x] Blocklisting a sense retires its live exercises immediately
- [x] `generation_queue` drops quarantined senses (else the ladder supply gate and
      the nightly coverage sweep re-queue them forever and burn LLM spend)
- [x] The ladder asset pipeline and the exercise worklist exporter skip quarantined
      senses before any LLM call

**Technical Notes:**
Three triggers plus `is_sense_quarantined(int)`. Trigger 1 *demotes* rather than
raises, because generators insert many senses per statement. Un-blocklisting does
**not** reactivate: retired exercises were written from the bad definition and must
be regenerated. Python guard fails open (the triggers still hold) — worst case is
wasted spend, never a bad item served. The table keeps its Calibration name; renaming
would break two RPCs and the screen script for a cosmetic gain.

**Files:**
- `migrations/task767_sense_quarantine_guards.sql` — triggers, helper, backfill
- `services/vocabulary/sense_quarantine.py` — `quarantined_sense_ids()` / `is_quarantined()`
- `services/vocabulary_ladder/asset_pipeline.py` — skip before Prompt 1
- `services/vocabulary_ladder/queue_drain.py` — treat a quarantined skip as failure
- `scripts/export_exercise_worklist.py` — exclude from the pool
- `tests/test_sense_quarantine.py` — 6 tests

**Verification:** live, in rolled-back transactions: reactivating a quarantined
sense's exercises leaves them inactive; a queue insert for one writes 0 rows;
blocklisting a healthy sense retires its exercises. 169 ladder/pipeline tests pass.

---

## TASK-768: Repair the blocklisted dictionary rows at source

**Status:** [x] Done — 2026-09-11 (355 rows deliberately left quarantined)
**Feature:** calibration
**Type:** bug
**Complexity:** L
**Depends On:** TASK-767

**Description:**
Every one of the 547 definition-mismatch flags was read by hand and given one of
three verdicts. Rewrites are **in place**, not merges into a sibling sense: the
dictionary keeps one sense per test context and `tests.vocab_sense_ids` points at
these exact rows, so rewriting keeps every test link valid. Each rewrite defines
what the headword means in its example sentence (`carbon` from "carbon footprint"
becomes carbon as in carbon emissions).

| verdict | zh | en | ja | total |
|---|---|---|---|---|
| rewrite (definition, + simple row / example where wrong) | 85 | 277 | 68 | 430 |
| false positive (definition was fine; unblocked) | 8 | 9 | 15 | 32 |
| keep quarantined (headword itself is broken) | 28 | 32 | 25 | 85 |

Plus 208 cross-language gloss rows (52 senses × en/zh/ja × 2 levels) that had been
translated *from* the bad definition — 川 glossed "a peel", 説明 "a yawn",
例えば "a printing press".

**What "keep" means.** The headword, not the definition, is wrong: zh segmentation
fragments (进大, 下降时, 坐在, 人会), lemmatizer-stripped English phrases (`tell
story`, `help us`, `call export`), ja reading-only or mis-annotated lemmas (リツ,
`クラム-clam` carrying *crumb*), symbols (`15`, `C`, `*`) and definitions invented
to fit a non-word (斯塔 as NATO, 三一 as a bird). Rewriting cannot fix these; the
fix is upstream in tokenisation / test-sense-linking. With the 270 ja MeCab
morpheme-sequence lemmas, **355 senses stay quarantined**.

**Every change is reversible.** The old text of each rewritten row is appended to
`validation_notes` (`[date TASK-768] ... (was: '...')`); 733 rows carry it.

**Incident, fixed in the same session:** the first zh run's paired-simple lookup did
not filter `definition_language_id`, so it overwrote 22 en/ja gloss rows with Chinese
text. All 22 were restored exactly from `validation_notes`, and the lookup now filters
by language and refuses to write when more than one row matches.

**Open follow-ups (not done):**
- 181 exercises on 24 rewritten senses stay retired and will **not** regenerate by
  themselves — none are ladder-backed, so `v_sense_family_coverage` never shows them.
  `export_exercise_worklist.senses_with_exercises` counts inactive rows, so the worklist
  would also skip these senses; regenerating them needs that check narrowed to active rows.
- The 355 kept rows need upstream repair (re-segment / re-link the tests that use them).

**Files:**
- `scripts/fix_quarantined_senses.py` — validated uploader (rewrite / false_positive / keep / gloss)
- `data/calibration/quarantine_fixes/*.json` — every per-sense decision, with reasons

**Verification:** blocklist 817 → 355 (zh 28, en 32, ja 295); 0 TASK-768 rows without
an embedding (755 re-embedded); 0 active exercises on quarantined senses; 0 refusal-text
definitions left in `dim_word_senses`.

---

## TASK-758: Calibration item builder

**Status:** [x] Done — 2026-09-08
**Feature:** calibration
**Type:** feature
**Complexity:** M
**Depends On:** TASK-755, TASK-757

**Description:**
Given a study language and a definition language, pick an anchor sense, call
`semantic_distractors()`, shuffle the four options, and return a renderable item. Falls back to
`get_distractors()` when the RPC returns fewer than three foils.

**Acceptance Criteria:**
- [x] Anchor selection avoids repeats within a run (verified over a 90-item run)
- [x] Option order is shuffled; the key is not positionally predictable
- [x] Short-foil fallback implemented (`get_distractors()`), logged at WARNING —
      it is a real quality drop, not a silent equivalent
- [x] Similarity/frequency of every foil persisted

**Notes:** anchors are stratified across Zipf bands rather than random — see
TASK-760. If neither picker can fill four options the anchor is skipped rather than
rendered short, because a 3-option item would silently change the guess rate the
ability curve is built on.

**Files:** `services/calibration_service.py`, `migrations/calibration_sessions_and_ability.sql`

---

## TASK-759: Response logging

**Status:** [x] Done — 2026-09-08
**Feature:** calibration
**Type:** feature
**Complexity:** S
**Depends On:** TASK-758

**Description:**
Persist every item and answer with the chosen option, its cosine and its frequency tier. This
is the data that ADR-025 says is the **only** way to catch different-word synonyms that are
secretly also-correct, so the schema must record enough to find them.

**Acceptance Criteria:**
- [x] Every option shown is recorded, not only the chosen one (verified: 4 rows per
      item, 90/90)
- [x] Cosine and frequency tier stored per option
- [x] A query can rank options by pick rate — the also-correct signal, with a
      partial index on `(sense_id) WHERE was_chosen AND NOT is_key`

**Files:** `calibration_response_options`

---

## TASK-760: Ability estimate and stopping rule

**Status:** [x] Done — 2026-09-08
**Feature:** calibration
**Type:** feature
**Complexity:** L
**Depends On:** TASK-759

**Description:**
Turn a stream of answers into an ability estimate. The two blocking product
questions were decided rather than deferred:

- **No stopping rule.** The run is infinite and the learner ends it. Instead of
  enforcing sufficiency, the result *reports* it: a `confidence` label
  (`none`/`low`/`medium`/`good`) from the answer count and how many bands have
  enough data.
- **No writeback.** Calibration writes only its own tables. Feeding `ability_zipf`
  into selection is TASK-747's and TASK-748's call, under ADR-024's guards.

**Output is a Zipf knowledge curve**, not a score — deliberately the statistic
the ADR-024 §1.2 contract names. To locate a crossing you need points on both
sides, so `calibration_next_anchor()` stratifies across bands (verified
13/13/12/13/13/13/13 over 90 items) rather than sampling randomly.

**Acceptance Criteria:**
- [x] Per-band known-share returned alongside the headline figure
- [x] `ability_zipf_85` and `ability_zipf_50` interpolated, NULL when the curve
      never crosses — an honest "not measured" rather than an extrapolation
- [x] Thin bands (n < 3) excluded from interpolation so one lucky guess cannot
      move the estimate
- [x] **Estimator validated against known ground truth** — which is how the bias in
      TASK-764 was found

---

## TASK-761: Calibration UI and nav entry

**Status:** [x] Done — 2026-09-08
**Feature:** calibration
**Type:** feature
**Complexity:** M
**Depends On:** TASK-758

**Description:**
Nav item, item view, immediate advance on answer, and a results panel that shows
the knowledge curve beside the headline figure — deliberately, so a number from six
answers cannot be mistaken for a number from eighty.

**Done:** `templates/calibration.html` (+ `routes/calibration.py` wired in `app.py`
at `/calibration` and `/api/calibration/*`), nav entry in `base.html`, and 17 i18n
keys added to **all four** `static/i18n/*.json` — verified programmatically, since
`applyToDOM` clobbers defaults and a missing key renders the raw key string.
Number keys 1-4 answer, for speed over a long run.

---

## TASK-762: Pronunciation mode

**Status:** [x] Done — 2026-09-08
**Feature:** calibration
**Type:** feature
**Complexity:** M
**Depends On:** TASK-758

**Description:**
The four-readings variant. A **different distractor problem** — audio and
orthographic confusability, not semantic similarity — so it uses a new picker,
`pronunciation_distractors()`, built on edit distance over a per-language
normalised reading (`fuzzystrmatch`).

**Acceptance Criteria:**
- [x] Homophones excluded outright (identical reading = second correct answer)
- [x] Tone retained for zh, so tone-only minimal pairs are produced
- [x] Same syllable count preferred, so options share a shape
- [x] Sampled 150 items per language and **read them**
- [x] English refused rather than degraded

**Outcome:** 0 sibling leaks, 0 format tells, 0 duplicate options across 300 items.
Three defects found by reading the output rather than by reasoning:

1. A fixed 3-edit cap left **13% of zh items with zero options**, all four-syllable
   words — `pin2fu4cha1ju4` is 14 characters and has no neighbour within 3 edits.
   Scaling the cap to `max(3, ceil(len*0.45))` took zh to **0 empty / 2 short**.
2. The ja latin gloss suffix leaked into the rendered option (`いおん-Ion`), making
   one option visibly a different shape — a format tell usable without knowing the
   word. Fixed with a display form separate from the comparison form.
3. Readings exist **only on the native row**; every cross-language gloss row has
   `pronunciation` NULL. Pronunciation mode therefore ignores the session's
   definition language, which would otherwise select an empty set.

**English is refused**, not degraded: 21 of 6,555 senses carry a reading (0.3%)
against zh 4,217 and ja 2,385.

**Files:** `migrations/calibration_pronunciation_mode.sql`,
`services/calibration_service.py`, `routes/calibration.py`,
`templates/calibration.html`

---

## TASK-764: Replace the linear interpolation with a guess-aware logistic fit

**Status:** [x] Done — 2026-09-08
**Feature:** calibration
**Type:** bug
**Complexity:** M
**Depends On:** TASK-760

**Description:**
`ability_zipf_85` is **systematically biased high**. Measured against simulated
learners whose true ability is known (`scripts/calibration_estimator_bias.py`,
84 items per trial, ja/en, 2026-09-08):

| true | z85 | err | z50 | err |
|---|---|---|---|---|
| 3.30 | 3.450 | +0.15 | 3.000 | -0.30 |
| 3.80 | 3.950 | +0.15 | 3.375 | -0.42 |
| 4.30 | 4.600 | +0.30 | 4.250 | -0.05 |
| 4.80 | 5.100 | +0.30 | 4.750 | -0.05 |
| 5.30 | 5.621 | +0.32 | 5.321 | +0.02 |

Positive in every trial, mean approximately **+0.24 Zipf**. The cause is
discretization, not guessing: for a step learner the 0.25 guess floor cancels out of
the crossing exactly, but linear interpolation between the midpoints of 0.5-wide
bands cannot resolve a step *inside* a band, and interpolating up to a high target
lands late.

This matters because the wiki log records that `ability_zipf`'s definition alone
swings the derived ELO by **430 points**, so a +0.24 offset is material.
**`ability_zipf_85` must not be wired into test selection until this is fixed.**

**Acceptance Criteria:**
- [x] Logistic fit with the 0.25 guess floor fixed, on RAW responses (no binning)
- [x] Mean |error| below 0.10 Zipf: **+0.084** against an adversarial step learner,
      **+0.029** against a realistic one on live data
- [x] `scripts/calibration_estimator_bias.py` re-run, extended with `--learner`,
      and its docstring tables updated
- [x] Did NOT subtract a constant

**Outcome.** The residual +0.084 on the step learner is **model mismatch, not
estimator bias** — an infinitely sharp step cannot be represented by a
finite-slope logistic. Against a correctly specified learner the fit is unbiased
(−0.028 over 15 offline trials, +0.029 live at 120 items).

**Precision replaced bias as the binding constraint**, and that is the more useful
finding: measured sd is 0.63 at 20 answers, 0.27 at 60, 0.16 at 120, 0.11 at 300.
The confidence labels were previously guessed from an item count and are now read
off that table, the API returns `ability_zipf_85_sd`, and the UI shows `± sd`.

**Three degenerate cases now return None** — found by testing, not reasoning, after
a random-answer session produced `ability_zipf_85 = 8.43` (no word reaches Zipf
6.56): a near-flat slope, a crossing outside the observed range, and failing a
likelihood-ratio test against a constant-accuracy null model.

`services/irt/` was **not** reused — it solves a different problem (item
calibration across a population) where this needs a two-parameter fit for one
session, and a dependency would have bought nothing.

---

## TASK-766: Publish pooled ability to test selection

**Status:** [x] Done — 2026-09-09 (migration applied live, TASK-765)
**Feature:** calibration
**Type:** feature
**Complexity:** M
**Depends On:** TASK-760, TASK-764

**Description:**
Connect the measurement to its consumer. `user_calibration_state` is the input
contract [[features/vocabulary-aware-test-selection]] §1.1 already specifies —
Calibration writes it, selection reads it, neither calls the other.

**Acceptance Criteria:**
- [x] Ability pooled across ALL sessions per (user, language, mode), not last-run
- [x] Modes stored separately, never averaged
- [x] `ability_se` published so consumers can propagate uncertainty
- [x] `calibration_zipf_to_elo()` in SQL only, ELO anchors read from
      `dim_complexity_tiers` at call time so no fourth copy of the ladder exists
- [x] Contract verified: 5.00 → 1250, 3.85 → 1681, a 431-point swing
- [x] Fails closed when the migration is unapplied

**Notes.** Pooling is not cosmetic — precision is what binds this estimate (sd 0.63
at 20 answers, 0.27 at 60, 0.16 at 120) and pooling is what buys it.

Deliberately **not** shipped: the `user_skill_ratings` write. ADR-024 §4 guards it
and §5 requires every decision, including every skip, to be audited to
`user_skill_rating_adjustments` — a table that did not exist then and belongs with
the writer it audits (TASK-746 builds the table, TASK-747 the writer). Shipping the writer without its audit trail would be an
unaudited automated write to live user ratings.

**Files:** `migrations/calibration_user_state_and_zipf_to_elo.sql`,
`services/calibration_service.py`, `scripts/verify_calibration_state.py`

---

## TASK-765: Apply the Phase 4 migration

**Status:** [x] Done — verified live 2026-09-10
**Feature:** calibration
**Type:** infra
**Complexity:** XS
**Depends On:** TASK-766

**Outcome (2026-09-10).** Live on project `kpfqrjtfxmujzolwsvdq`:
`user_calibration_state` exists with PK `(user_id, language_id, mode)` and its
mode/se CHECKs (0 rows; `calibration_sessions` also 0 rows).
`calibration_zipf_to_elo` is STABLE and returns 6.25→875, 5.25→1175, 5.0→1250,
4.5→1400, 4.2→1550, 3.85→1681, 3.8→1700, 3.25→1925, clamping 7.0→875 and
1.0→1925. `--self-test`: map PASS (61 probe points, 0 mismatches), state handoff
PASS. The migration has no `supabase_migrations.schema_migrations` row, so it was
applied outside the migration history and its exact timestamp is not recorded.
The migration header's `APPLIED LIVE` line now carries this verification.

**Description:**
Apply `migrations/calibration_user_state_and_zipf_to_elo.sql`. It was written in a
session with no DDL path (the Supabase MCP connection dropped and `DATABASE_URL`
points at a local dev database), so it is the one manual step.

Everything downstream already fails closed: `write_calibration_state()` logs a
warning naming this file and returns `None`, and a learner still gets their result.

**Verification:**
```
PYTHONIOENCODING=utf-8 python -m scripts.verify_calibration_state --self-test
```
Expect the anchor ladder to round-trip (875/1175/1400/1550/1700/1925), `5.00 → 1250`,
`3.85 → 1681`, clamping outside the ladder, 61 probe points agreeing with the
reference implementation, and a synthetic learner's state row landing with an
`ability_zipf` near their true ability.

---

## TASK-763: Re-tune the cosine ceiling from response data

**Status:** [?] Blocked — needs real learner traffic (harness ready)
**Feature:** calibration
**Type:** refactor
**Complexity:** S
**Depends On:** TASK-759

**Description:**
The 0.75 ceiling is provisional and binds on only ~0.2% of returned foils. ADR-025 records why
no cosine threshold can separate "unrelated" from "duplicate". Once real answers exist, set the
ceiling — or replace it with an explicit also-correct blocklist — from pick-rate evidence.
Updating a band is an `UPDATE` to `dim_distractor_bands`, not a redeploy.

**Ready now:** `scripts/calibration_also_correct_report.py` ranks distractors by how
often *strong* learners picked them over the key — the discriminating statistic,
since a weak learner picking one is evidence of nothing. It currently reports,
correctly, that no responses exist. It cannot be run on simulated answers: the whole
signal is which wrong option a *person* found tempting.

---

## TASK-769: Grade a calibration answer in one round trip

**Status:** [x] Done — applied live 2026-09-13
**Feature:** calibration
**Type:** refactor
**Complexity:** S
**Depends On:** TASK-759

**Description:**
Clicking an option took ~570 ms to reveal correct/incorrect, and almost none of it was
computation. `record_answer()` made eight sequential Supabase calls — a session read, a
response read, an options read, three writes and `calibration_ability(fit=False)` — on a link
whose median round trip is ~65 ms. Collapse all of it into one RPC that also returns the two
running counts the header renders, so the estimator is not called on the reveal path at all.

**Acceptance Criteria:**
- [x] `calibration_record_answer()` performs every check the Python did, in the same order,
      with the same outcomes: unknown item, wrong session, already answered, no such option,
      no recorded options.
- [x] A skip (`position` NULL) is still graded incorrect, never dropped.
- [x] Session counters are incremented in SQL (`items_answered + 1`), not read-modify-written
      from a Python copy, so two tabs cannot lose an update.
- [x] Invariant failures return `{"error": ...}` **before any write** and surface as the same
      `CalibrationError` -> 400 the route always produced.
- [x] `/answer` makes exactly one Supabase call (pinned by `tests/test_calibration_fast_path.py`).

**Technical Notes:**
`/answer` no longer loads the session first: the RPC proves ownership *and* session membership
before writing, so the read proved nothing new. A wrong session id is therefore a 400
("item does not belong to this session") rather than a 404 — the same amount of information,
since neither answer reveals whether the session exists.

**Files to Create / Modify:**
- `migrations/task769_calibration_record_answer.sql` — the RPC
- `services/calibration_service.py` — `record_answer()` rewritten
- `routes/calibration.py` — drops `_load_session` and the `ability(fit=False)` call

**Verification:**
Measured 2026-09-13: 8 calls -> 2 (auth + RPC), ~570 ms -> ~130 ms; with TASK-774, ~70 ms.

---

## TASK-772: Materialise a narrow calibration anchor pool

**Status:** [x] Done — applied live 2026-09-13
**Feature:** calibration
**Type:** refactor
**Complexity:** M
**Depends On:** TASK-758

**Description:**
`calibration_next_anchor()` measured 202-565 ms per item because it scanned
`dim_word_senses JOIN dim_vocabulary` twice — once inside a correlated EXISTS evaluated per
Zipf band, once to pick the row — and `dim_word_senses` is 56,022 rows carrying a
`vector(1536)`. Materialise the eligible anchors into a narrow table and select from that.

**Acceptance Criteria:**
- [x] `calibration_anchor_pool` holds one row per eligible (word lang, def lang, sense);
      27,326 rows built, and the per-pair counts match the old query exactly
      (zh/zh 4048, zh/en 3682, zh/ja 3682, en/en 6110, ja/* 3268).
- [x] The **blocklist is not baked in** — `calibration_anchor_blocklist` is still applied live,
      so a TASK-767/768 edit takes effect without a rebuild.
- [x] One table serves both modes via `has_embedding` / `has_pronunciation`.
- [x] Pronunciation is stored raw and rendered by `calibration_display_pronunciation()` at read
      time, so a display fix needs no data rebuild.
- [x] `calibration_next_anchors(..., p_count)` picks N anchors round-robin over the least-served
      bands in one pass; at `p_count = 1` it reduces exactly to the old behaviour.
- [x] `calibration_next_anchor()` keeps its signature and delegates.
- [x] `calibration_refresh_anchor_pool()` rebuilds with `DELETE` (not `TRUNCATE`, which would
      take an ACCESS EXCLUSIVE lock and block a live run).

**Technical Notes:**
The pool is a **cache**. Refresh it after any job that writes senses, embeddings,
pronunciations or frequency ranks — it goes stale silently, and a stale pool cannot corrupt a
measurement but will fail to offer newly-eligible words.

**Files to Create / Modify:**
- `migrations/task772_calibration_anchor_pool.sql`

**Verification:**
20 anchors in **15.6 ms** (was 202-565 ms for one).

---

## TASK-773: Cache the distractor sets

**Status:** [x] Done — applied live 2026-09-13; bulk build run same day
**Feature:** calibration
**Type:** infra
**Complexity:** M
**Depends On:** TASK-772

**Description:**
`semantic_distractors()` measured 1064-1252 ms **cold** and 17 ms warm, and cold is the normal
case: `shared_buffers` is 224 MB and the seven HNSW indexes on `dim_word_senses` total 442 MB,
so the working set cannot stay resident. Precompute the distractor sets into a table.

**Acceptance Criteria:**
- [x] Caching the semantic picker is **free, not a trade-off**: `semantic_distractors()`
      contains no `random()` and its final `ORDER BY (freq_tier, similarity DESC)` is fully
      determined by the data, so the cache returns the identical foils. Verified byte-for-byte
      against a live call for sense 41543.
- [x] Pronunciation is cached as a **pool of 8 and sampled at serve time**, because
      `pronunciation_distractors()` *does* contain `random()` and freezing three foils would
      remove variety the live picker has.
- [x] The cache self-fills on a miss, so a newly-eligible sense is never unserveable.
- [x] The bulk filler works **one language pair at a time** so that pair's partial HNSW index
      stays resident; measured effect 451 -> 86 -> 62 ms/anchor across the first three chunks.
- [x] An anchor that cannot be filled is left uncached, not marked bad — that verdict is the
      blocklist's job and a human judgement.
- [x] `calibration_distractor_cache_coverage()` reports cached-vs-total per pair and mode.

**Technical Notes:**
Derived data. Re-run the builder after any change to definitions, embeddings or the sense
inventory, or a corrected definition keeps being served as a stale foil.

**Files to Create / Modify:**
- `migrations/task773_calibration_distractor_cache.sql`
- `scripts/build_calibration_distractor_cache.py`

**Verification:**
```
PYTHONPATH=. python scripts/build_calibration_distractor_cache.py --coverage
PYTHONPATH=. python scripts/build_calibration_distractor_cache.py --refresh-pool
```
Full build ~30 min for ~27k anchors at ~65 ms each.

---

## TASK-770: Build calibration items in batches

**Status:** [x] Done — applied live 2026-09-13
**Feature:** calibration
**Type:** feature
**Complexity:** M
**Depends On:** TASK-772, TASK-773

**Description:**
`/next` cost ~1.8-2.1 s per item and sat between every answer and the next word. After
TASK-772/773 removed the two slow RPCs, six round trips per item remained. Move the whole item
build — anchor selection, distractor lookup, both inserts, the option shuffle, the served
counter — into one SQL function that can produce up to 25 items per call.

**Acceptance Criteria:**
- [x] `calibration_build_items()` returns items **without** the key; the client still learns
      which option was right only by submitting one.
- [x] The option shuffle is one `MATERIALIZED` CTE feeding both the stored rows and the returned
      JSON, so positions cannot disagree. Verified against the stored rows of a built item.
- [x] Anchors are over-fetched ~1.4x; an anchor that cannot supply three real foils is skipped,
      not padded with random ones.
- [x] Cold-cache fills are capped per call (`p_max_fill`, default 4) so a batch cannot become a
      22-second request.
- [x] `exhausted` is true only when the language pair has no unseen anchors — an empty batch is
      reported by `built = 0` instead.
- [x] `calibration_discard_unanswered()` removes prefetched-but-unreached items at `/end` and
      corrects `items_served`.

**Technical Notes:**
This retires the `get_distractors()` random-foil fallback **for calibration**. It existed
because a singular builder had no second chance; a batch builder always has one, so definition
mode now agrees with pronunciation mode — an item is built from real foils or it is not built.
Measured rate at which this bites: ~1 anchor in 1,400.

**Files to Create / Modify:**
- `migrations/task770_calibration_build_items.sql`
- `services/calibration_service.py` — `build_items()`, `next_item()` wrapper, `discard_unanswered()`
- `routes/calibration.py` — `/next?count=`

**Verification:**
20 items in **348 ms**, 0 skipped, 0 filled, against a warm cache (measured 2026-09-13).
Previously 20 x ~1.9 s = ~38 s.

---

## TASK-771: Prefetch items into a client-side queue

**Status:** [x] Done — 2026-09-13
**Feature:** calibration
**Type:** feature
**Complexity:** S
**Depends On:** TASK-770

**Description:**
Render from a queue rather than fetching on demand, so answering an item is never followed by
waiting for the next one. Fetch a small first batch — the only one the learner waits on — and
top up in the background while they answer.

**Acceptance Criteria:**
- [x] First paint asks for 3 items; top-ups of 12 fire when the queue falls to 6 or fewer.
- [x] A top-up started for a session that has since been replaced (restart, mode switch) does
      not enqueue its items.
- [x] Concurrent top-ups collapse into the in-flight request rather than starting a second.
- [x] A drained queue shows the exhausted state only when the server said exhausted; otherwise
      it waits for the in-flight fetch.
- [x] Queued-but-unanswered items are dropped on `finish()`, matching the server-side discard.

**Files to Create / Modify:**
- `templates/calibration.html` — `state.queue`, `topUp()`, `showNext()`, `waitForItem()`

---

## TASK-774: Stop revalidating every token over the network

**Status:** [x] Done — 2026-09-13
**Feature:** calibration (app-wide effect)
**Type:** refactor
**Complexity:** S
**Depends On:** none

**Description:**
`_authenticate` called `auth.get_user(token)` — a network call to GoTrue — on **every**
authenticated request in the application, so every endpoint paid a fixed ~65-150 ms toll before
its handler started. Cache successful validations in-process.

**Acceptance Criteria:**
- [x] A repeated token does not go to the network.
- [x] A **rejection is never cached**, so a bad token is re-checked every time.
- [x] An entry never outlives the token's own `exp` — the expiry is `min(now + TTL, exp)`, read
      unverified, which is safe because that value can only *shorten* a lifetime.
- [x] `AUTH_CACHE_TTL_SECONDS=0` disables the cache and restores the previous behaviour.
- [x] Raw bearer tokens are never used as keys (SHA-256).

**Technical Notes:**
The residual risk is the intended one and is what the TTL bounds: a session revoked
server-side keeps working for at most the TTL (default 60 s). `clear_auth_cache()` drops
everything for an operator who does not want to wait it out.

**Files to Create / Modify:**
- `middleware/auth.py`
- `tests/test_auth_token_cache.py`

---

## TASK-775: Let the learner move on from a wrong answer themselves

**Status:** [x] Done — 2026-09-13
**Feature:** calibration
**Type:** feature
**Complexity:** XS
**Depends On:** TASK-771

**Description:**
A wrong answer used to be replaced automatically after 1,300 ms. That is the one moment in a run
where there is something to read — which option was right, and how near the one they picked was
— and a timer decides for the learner how long that takes. Show a **Next word** button instead
and wait. A correct answer has nothing to study, so it still advances by itself.

**Acceptance Criteria:**
- [x] A wrong answer, and a skip, reveal the key and show a Next button; nothing advances until
      the learner acts.
- [x] "I don't know" is hidden while an answer is revealed — it can no longer mean anything.
- [x] A correct answer advances after 450 ms, and a key press skips that pause.
- [x] Enter / Space / Right arrow advance from a revealed answer. The button is never focused,
      so one Space cannot both activate it natively and fire the handler.
- [x] Timer, button and key all go through one `advance()` guarded by `awaitingAdvance`, so two
      of them firing together cannot consume two items.
- [x] `calibration.next` and `calibration.next_hint` exist in all four locale files
      (see [[i18n]] — a missing key renders as the raw key string).

**Files to Create / Modify:**
- `templates/calibration.html`
- `static/i18n/{en,zh,ja,es}.json`

---

## TASK-773b: Stop the bulk distractor builder retrying a short anchor forever

**Status:** [x] Done — applied live 2026-09-13
**Feature:** calibration
**Type:** bug
**Complexity:** XS
**Depends On:** TASK-773

**Description:**
Found by running the TASK-773 build. `calibration_cache_distractors_chunk` selects anchors with
no cache rows, and the driving script loops until a chunk processes zero. An anchor whose picker
legitimately returns fewer than three usable foils ends its attempt with no cache rows — so the
next chunk selects it again, and again. ja/ja pronunciation stalled at 2,339 of 2,352 with
thirteen anchors cycling indefinitely.

**Why the obvious fix was wrong:**
Stopping the script when a chunk fills nothing would have ended the build early: the selector is
`ORDER BY sense_id LIMIT n`, so a few short anchors at the front of that order would have hidden
the thousands behind them.

**Acceptance Criteria:**
- [x] `calibration_distractor_cache_misses` records the anchor and how many rows came back; the
      selector excludes it.
- [x] The ledger records an **attempt, not a verdict**. "This anchor is bad" stays with
      `calibration_anchor_blocklist`, which is a human judgement (TASK-767/768).
- [x] **Nothing at serve time reads it.** `calibration_build_items` still self-fills on a miss,
      so a listed anchor is not barred from being served — only from being bulk-retried.
- [x] `calibration_clear_distractor_cache_misses()` forgets them, for after a dictionary change:
      an anchor that was short yesterday may have gained near neighbours since.
- [x] The script keeps a second line of defence — it stops if the remaining count repeats — so a
      future selector bug cannot spin forever either.

**Files to Create / Modify:**
- `migrations/task773b_calibration_distractor_cache_misses.sql`
- `scripts/build_calibration_distractor_cache.py` — `_remaining()` stall guard

**Verification:**
Re-running the pair that hung now reports `already complete` and exits 0; the 13 anchors are
recorded with `rows_found = 0`.

---

## TASK-776: Drop foils that share a head gloss with the right answer

**Status:** [~] In Progress — migration written 2026-09-14, **not yet applied live**; cache not rebuilt
**Feature:** calibration
**Type:** bug
**Complexity:** S
**Depends On:** TASK-773

**Description:**
A ja/en item for 先生 offered 教師 "teacher; an instructor at a school" as a *wrong* answer beside
先生 "a teacher — a person who teaches…". Both are correct. The pair scored cosine 0.71, under
the 0.75 ceiling, and `semantic_distractors()` ranks by similarity DESC, so a synonym just under
the ceiling is ranked **first**, not merely admitted. The sibling and stem-variant guards compare
lemmas and cannot see it. An also-correct foil marks a learner who knows the word as wrong, which
biases the ability estimate down.

Fix: a new guard (6) in `semantic_distractors()` rejecting any candidate whose head glosses (text
before the first em dash, split on ; ； ：, lightly normalised by `definition_head_glosses()`)
overlap the anchor's. Rejected candidates are replaced by the next nearest, as with every other
guard.

**Measured before the fix** (cache, top-3 served foils, anchors affected): ja/en 680 / 3,268 ·
ja/zh 395 / 3,267 · zh/en 293 / 3,680 · zh/ja 122 / 3,681 · en/en 18 / 6,110 · zh/zh 5 / 4,041 ·
ja/ja 0. First-gloss-only matching caught roughly half as many in ja/en (354); a hand-read sample
of 85 any-overlap matches was overwhelmingly true synonyms, loosest being cross-POS pairs
(to plant / plant) that give the answer away anyway.

**Acceptance Criteria:**
- [x] `definition_head_glosses(text) → text[]` exists, IMMUTABLE, returns `{}` for NULL/prose.
- [x] Guard applied after the index scan; signature unchanged, so no DROP / re-GRANT.
- [ ] Migration applied live.
- [ ] Affected anchors' definition-mode cache rows deleted and refilled (the cache is an exact
      copy of the function's output — without the rebuild nothing a learner sees changes).
- [ ] The no-overlap verification query in the migration returns 0.
- [ ] Anchor 43399 (先生, ja/en) no longer caches sense 56314 (教師).
- [ ] Short anchors (fewer than 3 foils after the guard) counted and reported.

**Technical Notes:**
Only anchors with a match in their cached rows need rebuilding: the guard only removes rows, and
any row it would remove from an anchor's top 6 is already in the cache to be checked, so
unmatched anchors are provably unchanged. Rebuild one language pair at a time (TASK-773
decision 4). `calibration_distractor_cache_misses` should be cleared for the rebuilt anchors so
the bulk builder retries them. Paraphrased synonyms are out of scope — see TASK-777.

**Files to Create / Modify:**
- `migrations/calibration_distractor_headword_guard.sql` — new; canonical for `semantic_distractors()`
- `migrations/calibration_semantic_distractors.sql` — kept (sole record of `dim_distractor_bands`,
  `shared_prefix_len`); pointer comment added

**Verification:**
1. Apply the migration.
2. Run the DELETE in the migration's *Rebuild* block, then
   `python -m scripts.build_calibration_distractor_cache --mode definition --word-language 3 --definition-language 2`
   (repeat per affected pair: 3/2, 3/1, 1/2, 1/3, 2/2, 1/1).
3. Run both verification queries at the bottom of the migration; expect 0 and 0.

---

## TASK-777: Offline LLM synonym judge over the distractor cache

**Status:** [?] Open question — paused 2026-09-14 by decision; do not start
**Feature:** calibration
**Type:** feature
**Complexity:** M
**Depends On:** TASK-776

**Description:**
TASK-776 only catches synonyms that *state* the same gloss. Paraphrased synonyms ("instructor"
vs "teacher") still pass the cosine ceiling and are still ranked first. Because the cache is
precomputed and stores 6 foils per anchor while serving 3, a one-off judge pass ("could this
option also correctly define the prompt word?") would cost nothing at serve time and has slack
to drop rejects.

**Open questions (answer before this becomes a task):**
- Is the headword guard alone enough? Measure after TASK-776 with a hand-read sample of the
  highest-similarity surviving foils before spending on a judge.
- Which model, and how is it validated? The distractor-judge history (TASK-718) showed two judges
  producing disjoint reject sets with no gold set to arbitrate — a judge here needs its own small
  gold set or it is unvalidated.
- What happens to an anchor that drops below 3 foils: refill deeper from the pool (needs a
  larger `p_count` than 6), or leave it short and skipped?
- Does a rejection live in the cache only (lost on rebuild) or in a durable table that
  `semantic_distractors()` / the filler consults?

---
