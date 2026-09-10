---
title: "Calibration — Task Breakdown"
feature: calibration
prose_page: ../features/calibration.md
tech_page: ../features/calibration.tech.md
total_tasks: 14
done: 13
last_updated: 2026-09-10
---

# Calibration — Task Breakdown

Phases 1-3 are complete and live as of 2026-09-08: the **distractor foundation**
(TASK-753 – TASK-756), the **engine and UI** (TASK-758 – TASK-761), and
**pronunciation mode + the corrected estimator** (TASK-762, TASK-764).

Phase 4 (TASK-757, TASK-766) added the dictionary screen and the handoff to test
selection. **TASK-765** (applying the Phase 4 migration) was verified live on
2026-09-10. One task remains: **TASK-763** needs real learner traffic that does not
exist yet.

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

**Still not fixed at source.** All 817 blocklist rows protect Calibration only.
Flashcards, practice and exercise generation still serve these rows. Per-flag JSON
files (`sense_mismatch_lang*.json`) were produced so an upstream repair has
something to work from — that repair is deliberately NOT automated here, because
rewriting a definition is a content decision, not a screening one.

**Files:** `scripts/screen_sense_definition_mismatch.py`

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
