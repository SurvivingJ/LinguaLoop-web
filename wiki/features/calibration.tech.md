---
title: Calibration — Technical Specification
type: feature-tech
status: in-progress
prose_page: calibration.md
last_updated: 2026-09-08
dependencies:
  - "table: dim_word_senses (+ new column word_language_id, embedding)"
  - "table: dim_vocabulary (lemma, language_id, frequency_rank)"
  - "table: dim_distractor_bands (new)"
  - "RPC: semantic_distractors (new)"
  - "function: shared_prefix_len (new)"
  - "extension: vector 0.8.0 (HNSW)"
  - "script: scripts/backfill_sense_embeddings.py"
  - "script: scripts/dump_calibration_distractors.py (new)"
  - "script: scripts/calibration_estimator_bias.py (new)"
  - "tables: calibration_sessions / _responses / _response_options / _anchor_blocklist (new)"
  - "RPCs: calibration_next_anchor, calibration_ability, calibration_zipf_band, calibration_band_midpoint (new)"
  - "routes/calibration.py, services/calibration_service.py, templates/calibration.html (new)"
breaking_change_risk: low
---

# Calibration — Technical Specification

**Phases 1-4 are COMPLETE** — distractor foundation, session engine + UI,
pronunciation mode + the corrected estimator, and the handoff to test selection.
Phases 1-3 are applied live; Phase 4's migration is written and **not yet applied**
(the session that wrote it had no DDL path), and everything downstream fails closed
until it is. TASK-763 remains open and needs real learner traffic.

## Architecture Overview

```
   templates/calibration.html            <-- Phase 2, LIVE
        |  POST /api/calibration/{start,answer,end}, GET /{next,ability}
        v
   routes/calibration.py -> services/calibration_service.py
        |                             |
        |                             +--> calibration_next_anchor()   (stratified anchor)
        |                             +--> calibration_ability()        (the Zipf curve)
        |  anchor sense id, word lang, definition lang
        v
   semantic_distractors()            <-- Phase 1, LIVE
        |
        +-- dim_distractor_bands     (measured cosine floor/ceiling per language pair)
        |
        +-- idx_dws_emb_w<N>_d<N>    (7 partial HNSW cosine indexes)
                |
                v
           dim_word_senses.embedding  vector(1536), text-embedding-3-small
```

The embedded text is **`"{lemma}: {definition}"`**, not the definition alone. This is
deliberate (see the docstring in `scripts/backfill_sense_embeddings.py`): short generic
definitions collapse onto one vector when embedded bare. **Do not change this recipe or
re-embed with definition-only.** It is also the direct cause of the sibling-exclusion
requirement below.

## Database Impact

### `dim_word_senses.word_language_id smallint NOT NULL` (new)

The word's language, copied from `dim_vocabulary.language_id`. Exists so both language
predicates sit on the same table as the vector being ordered — a predicate on a *joined* table
cannot be pushed into an HNSW index scan, which is exactly what made `nearest_senses()` time
out.

Derived, never supplied:

| object | timing | behaviour |
|---|---|---|
| `set_sense_word_language()` / `trg_dim_word_senses_word_language` | `BEFORE INSERT OR UPDATE OF vocab_id` | Overwrites the caller's value from `dim_vocabulary`; raises `23503` if `vocab_id` resolves to no row. |
| `propagate_vocab_language_to_senses()` / `trg_dim_vocabulary_language_propagate` | `AFTER UPDATE OF language_id` on `dim_vocabulary` | Propagates a relabel. Only fires when `language_id` is in the UPDATE's column list. |

Both are `SECURITY DEFINER` — RLS is enabled on both tables, and a plain trigger would read
zero rows under a restricted role and fail closed on every insert.

### Indexes

Dropped: `idx_dim_word_senses_embedding` (482 MB, `idx_scan = 0` against a
`pg_stat_database.stats_reset` of NULL — it never served a scan in its lifetime).

Created: seven partial HNSW cosine indexes, one per existing (word, definition) language pair.

| index | pair | rows | size |
|---|---|---|---|
| `idx_dws_emb_w1_d1` | zh/zh | 8,214 | 64 MB |
| `idx_dws_emb_w1_d2` | zh/en | 7,828 | 61 MB |
| `idx_dws_emb_w1_d3` | zh/ja | 7,828 | 61 MB |
| `idx_dws_emb_w2_d2` | en/en | 10,774 | 84 MB |
| `idx_dws_emb_w3_d1` | ja/zh | 7,126 | 56 MB |
| `idx_dws_emb_w3_d2` | ja/en | 7,126 | 56 MB |
| `idx_dws_emb_w3_d3` | ja/ja | 7,126 | 56 MB |

438 MB total, replacing 482 MB. Predicates are disjoint, so a write touches exactly one.
Each predicate is `word_language_id = X AND definition_language_id = Y AND embedding IS NOT NULL`
and **a query must repeat all three** or the partial index will not match.

Also created: `idx_dim_word_senses_wl_dl_level (word_language_id, definition_language_id, definition_level)`.

### `dim_distractor_bands` (new)

Primary key `(word_language_id, definition_language_id)`; `cos_min`, `cos_max`, plus the
provenance of `cos_min` (`unrelated_median`, `unrelated_p95`, `pct_above_0_35`, `measured_on`,
`notes`). RLS on, `SELECT` to `authenticated` and `service_role`.

`cos_min` is the p95 of that pair's measured unrelated-pair distribution. Values in
[[decisions/ADR-025-semantic-distractor-selection]].

## API / RPC Surface

### `semantic_distractors(p_sense_id integer, p_word_language_id smallint, p_definition_language_id smallint, p_count integer = 3, p_cos_min real = NULL, p_cos_max real = NULL, p_freq_band real = 1.0, p_definition_level text = 'standard', p_pool integer = 100, p_exclude_stem_variants boolean = true) RETURNS SETOF record`

- **Purpose:** k semantically near, difficulty-matched distractor senses for one anchor sense.
- **Arguments:**
  - `p_sense_id` — the anchor (the correct answer's sense).
  - `p_word_language_id`, `p_definition_language_id` — both required; together they select the
    partial index.
  - `p_cos_min` / `p_cos_max` — **parameters, not constants.** `NULL` falls back to
    `dim_distractor_bands`, then to a last-resort 0.40 / 0.75.
  - `p_freq_band` — half-width in **Zipf points** of the tier-0 frequency band.
  - `p_pool` — index fetch depth, clamped to `[p_count*10, 200]`.
  - `p_exclude_stem_variants` — the morphological-variant guard.
- **Returns:** `out_sense_id, out_vocab_id, out_lemma, out_definition, out_similarity,
  out_frequency, out_frequency_delta, out_freq_tier`.
- **Errors:** `42501 Authentication required` unless `auth.role()` is `authenticated` or
  `service_role`. Returns **zero rows** (does not raise) when the anchor is missing or
  unembedded — the caller's fallback is `get_distractors()`.
- **Auth:** `SECURITY DEFINER`, `search_path` pinned, granted to `authenticated`/`service_role`,
  revoked from `anon`.
- **Side effects:** none. `STABLE`, read-only.

#### The five filters, in order of how badly they break the item if removed

1. **`vocab_id` sibling exclusion.** Because the lemma is inside the embedded text, a word's
   own rows are its nearest neighbours. Without this the three "distractors" for 基本 are three
   more definitions of 基本 — all correct.
2. **Per-pair cosine floor** from `dim_distractor_bands`.
3. **Frequency tiering** on `dim_vocabulary.frequency_rank`, which is a **Zipf score**
   (0.25–6.56, *higher = more common*), **not a rank** — see
   `services/vocabulary_ladder/deterministic/lexicon.py:266`. Tier 0 = within `p_freq_band`,
   tier 1 = within 2x or frequency unknown, tier 2 = beyond. Ordering is `freq_tier, similarity
   DESC`, so **the frequency band relaxes before the cosine floor ever does**. NULL frequency
   (8.5% of `dim_vocabulary`) is tier 1, never Zipf 0 — that would read as "maximally rare".
4. **`definition_level = 'standard'`.** At `'simple'`, cross-language glosses often restate the
   lemma verbatim (ja/zh 508/3,563 = 14.3%; zh/ja 461/3,914 = 11.8%). At `'standard'` the count
   is zero across all seven pairs, so this removes the "option identical to the prompt" defect
   by construction.
5. **Stem-variant guard** (`shared_prefix_len >= 4` and `>= 60%` of the shorter lemma).
   Morphological variants are *different* `vocab_id` rows, so they survive filter 1, and their
   definitions are frequently mutually correct. Self-limiting to alphabetic scripts: CJK lemmas
   of 1–3 characters never reach a 4-character shared prefix.

Then `DISTINCT ON (vocab_id)` (one option per word) and `DISTINCT ON (lower(definition))`
(one option per text).

#### Two settings that are load-bearing and easy to delete by accident

- **`SET plan_cache_mode TO 'force_custom_plan'`** — a partial index is only usable when the
  planner can *prove* the query predicate implies the index predicate, which it cannot do when
  the language ids are plan parameters. plpgsql switches to a generic plan after ~5 executions;
  without this, **call six** silently falls back to a sequential scan and the 57014 timeout
  returns.
- **`set_config('hnsw.ef_search', v_pool, true)` in the body** — `ef_search` must be at least
  the scan's LIMIT or recall collapses silently. It is set in the body because the declarative
  `SET hnsw.ef_search` clause is rejected on Supabase with
  `42501: permission denied to set parameter`.

## Performance

Warm, ja anchor 41404, `EXPLAIN (ANALYZE, BUFFERS)`:

| design | pool / ef_search | time | buffers |
|---|---|---|---|
| per-word-language index (rejected) | 400 / 400 | 3,947 ms | hit 4473, read 3701 |
| **per-language-pair index (shipped)** | 100 / 100 | **19 ms** | hit 2274, **read 0** |

HNSW recall was verified rather than assumed: against an exact brute-force scan of the same
21,378 ja vectors, recall@100 was **100/100** on every probed anchor.

## Operational Notes

- **Index builds are serial-only on this instance.** `max_parallel_maintenance_workers > 0`
  fails with `53100: could not resize shared memory segment ... No space left on device` at
  both 1 GB and 256 MB `maintenance_work_mem` — /dev/shm is too small. Use
  `SET max_parallel_maintenance_workers = 0; SET maintenance_work_mem = '512MB';`
  (~36–40 s per index).
- **Drop the big HNSW index before any full-table UPDATE on `dim_word_senses`.** An UPDATE
  writes a new heap tuple into *every* index; with the 482 MB graph present the
  `word_language_id` backfill timed out and rolled back. Without it, the same UPDATE took
  seconds.
- The RPC cannot be smoke-tested from a bare SQL console — `auth.role()` is NULL there and it
  raises 42501. Use the service-role client.

## Testing Strategy

**The mechanical checks are necessary but not sufficient.** The failure that matters — foils
that are not *tempting* — passes every assertion. `scripts/dump_calibration_distractors.py`
samples N items per language pair, counts the mechanical failures, and writes the items out to
be **read**.

Result over 1,400 items (200 x 7 pairs), 2026-09-08:

| check | result |
|---|---|
| sibling leaks | 0 |
| definition == own lemma | 0 |
| definition == anchor lemma | 0 |
| definition == anchor definition | 0 |
| duplicate options within an item | 0 |
| short items (< 3 foils) | 1 of 1,400 |
| stem-variant foils | 0 (was 68/600 in en/en before filter 5) |
| mean cosine per pair | 0.595 – 0.632 |
| floors bind exactly | ja/en min 0.360 vs floor 0.36; en/en 0.345 vs 0.34; ja/ja 0.442 vs 0.44 |

Regression tests worth adding in Phase 2: the sibling exclusion; that call #6 is still fast
(guards `force_custom_plan`); that a missing `dim_distractor_bands` row falls back rather than
returning nothing.

## Phase 2 — the engine (COMPLETE, applied live 2026-09-08)

### What Calibration outputs, and why it is that

**A Zipf knowledge curve, not a score.** Every anchor carries a Zipf score, so
bucketing answers by frequency band gives known-share as a function of word
frequency; the interesting number is where that curve *crosses* a threshold.

This is deliberately the same statistic
[[decisions/ADR-024-vocabulary-aware-test-selection]] §1.2 was blocked on:
`ability_zipf`, "the Zipf at which known-share crosses 1 - u* (85%)". The wiki log
records that this definition alone swings the derived ELO by **430 points**, so it
has to be measured rather than assumed. Calibration is the instrument that
measures it. **Read the bias section below before wiring it into anything.**

### Anchors are stratified, not random

`calibration_next_anchor()` serves the Zipf band with the fewest items answered so
far in this session (random tie-break). Locating a crossing needs points on *both*
sides of it; uniform random sampling piles items wherever the dictionary is dense
and can leave a band empty, which makes the crossing uninterpolatable. Verified: a
90-item run produced band counts 13/13/12/13/13/13/13.

### Schema

| table | purpose |
|---|---|
| `calibration_sessions` | one run; language pair, counters, `ended_at` |
| `calibration_responses` | one row per item **served** (`is_correct IS NULL` = served but abandoned — kept, because dropping abandoned items biases the curve upward) |
| `calibration_response_options` | **one row per option rendered**, with its cosine and frequency tier |
| `calibration_anchor_blocklist` | senses that must never be a prompt (TASK-757) |

Storing every option, not just the chosen one, is what makes the also-correct
analysis in ADR-025 / TASK-763 possible at all: a distractor that strong learners
pick as often as the key *is* a second right answer, and that is invisible if the
un-chosen options were discarded at write time.

### Calibration does not write back to ELO or study planning

Unlike `classifier_drill`, no route here calls `_apply_timing_and_progress` or any
`process_*_submission` RPC, and there is no sentinel test row. A measurement that
silently moved the thing it measures would be a feedback loop, not a calibration.
Feeding `ability_zipf` into test selection is TASK-748's (the ranking) and
TASK-747's (the guarded rating writer), each with its own guards.

### API

| endpoint | notes |
|---|---|
| `POST /api/calibration/start` | `{word_language_id, definition_language_id}` |
| `GET /api/calibration/next` | `item: null` + `exhausted: true` when the pair runs out |
| `POST /api/calibration/answer` | `position` may be `null` (skip → recorded incorrect) |
| `GET /api/calibration/ability` | the curve so far |
| `POST /api/calibration/end` | closes the session, returns the final report |

Ownership is checked in `calibration_service.get_session()` rather than left to
RLS, because the Flask layer uses the service role and therefore bypasses RLS. A
session belonging to another user returns **404, not 403**, so it is
indistinguishable from one that does not exist. The correct answer is never sent
to the client with the item — only in the response to an answer.

### MEASURED BIAS — read before trusting `ability_zipf_85`

`scripts/calibration_estimator_bias.py` runs simulated learners whose true ability
is known (correct above a threshold, guessing at 0.25 below), so any deviation is
the estimator's own error. 84 items per trial, ja/en, 2026-09-08:

| true | `z85` | err | `z50` | err |
|---|---|---|---|---|
| 3.30 | 3.450 | **+0.15** | 3.000 | −0.30 |
| 3.80 | 3.950 | **+0.15** | 3.375 | −0.42 |
| 4.30 | 4.600 | **+0.30** | 4.250 | −0.05 |
| 4.80 | 5.100 | **+0.30** | 4.750 | −0.05 |
| 5.30 | 5.621 | **+0.32** | 5.321 | +0.02 |

**`ability_zipf_85` is biased high in every trial, by +0.15 to +0.32 Zipf
(mean ≈ +0.24).** That is systematic, not noise.

The cause is **discretization, not guessing**. For a step learner the 0.25 guess
floor cancels out of the crossing exactly (observed share jumps 0.25 → 1.0 at the
threshold, passing through both 0.85 and the guess-corrected 0.8875 at the same
point). What does not cancel is linear interpolation between the midpoints of
0.5-wide bands: a step falling *inside* a band is smeared into a partial average,
and interpolating up to a high target lands late. `ability_zipf_50` is not
systematically biased but is noisier, a mid-curve target being more sensitive to
per-band sampling noise.

**Consequence for ADR-024.** Given that work's 430-point sensitivity to this
statistic, a +0.24 Zipf offset is material and must not be fed into an ELO mapping
uncorrected. TASK-764 replaces the piecewise-linear interpolation with a
guess-floor-aware logistic fit (`services/irt/` already exists), which removes the
discretization error rather than papering over it with a constant.

### Verified end to end

A 90-item simulated run: 0 build failures, no anchor served twice, exactly 4
options recorded per item (90/90), the blocklisted sense never served, every
answer recording a chosen option, and near-uniform band coverage.

## Phase 3 — pronunciation mode and the corrected estimator (COMPLETE)

### TASK-764: the estimator was wrong, and is now fixed and re-validated

The +0.24 Zipf bias above was **real and is gone**. `calibration_ability()` still
returns the per-band curve (that is the evidence the UI shows), but the crossings
are now computed in `calibration_service._fit_ability()` by maximum likelihood on
the **raw responses**, with the 1-in-4 guess floor as a **fixed** parameter:

    p(z) = 0.25 + 0.75 * sigmoid(slope * (z - midpoint))

Two things changed. Nothing is discretized into 0.5-wide bands any more — the old
bias was a discretization artifact, a step in ability falling *inside* a band being
smeared into a partial average. And "85%" now means 85% of words genuinely known
rather than 85% of items answered right, which differ substantially near the bottom
of the curve where a struggling learner sits.

Coarse-to-fine grid search rather than gradient descent: the surface is
two-dimensional and well behaved, a grid cannot diverge or settle in a local
optimum the way an unbounded Newton step can, and it costs under a millisecond.

**Re-validated, and the residual is explained rather than waved through:**

| learner | mean err85 | reading |
|---|---|---|
| step (adversarial) | **+0.084** | was +0.24; an infinitely sharp step cannot be represented by a finite-slope logistic, so this is **model mismatch, not estimator bias** |
| logistic (realistic, live, 120 items) | **+0.029** | model correctly specified — essentially unbiased |

**Precision, not bias, is now the binding constraint.** 60 simulated learners per row:

| items | bias | sd | p90 \|err\| |
|---|---|---|---|
| 20 | −0.118 | 0.631 | 0.95 |
| 40 | −0.053 | 0.416 | 0.57 |
| 60 | −0.035 | 0.270 | 0.43 |
| 84 | −0.040 | 0.238 | 0.39 |
| 120 | −0.044 | 0.157 | 0.26 |
| 200 | −0.002 | 0.156 | 0.26 |
| 300 | −0.051 | 0.109 | 0.20 |

That table is now the source for `expected_sd()` and for the confidence labels,
which were previously guessed from an item count and are now read off measured
precision. The API returns **`ability_zipf_85_sd`**, and the UI renders
`4.31 ± 0.24` rather than a bare number — at 60 items the standard error is still
±0.27 Zipf, and a two-decimal figure reads far more precise than the measurement is.
**For ADR-024, propagate `ability_zipf_85_sd`; do not treat the point estimate as
exact.**

**Three degenerate cases now return `None` instead of a confident-looking number**
(found by testing, not by reasoning — a simulated session of random answers
produced `ability_zipf_85 = 8.43`, a Zipf no word in the corpus reaches):

1. slope below 0.35 — a curve that flat locates nothing;
2. a crossing outside the **observed** Zipf range — that is extrapolation past the
   edge of the evidence, not measurement;
3. failing a likelihood-ratio test against the null model of one constant accuracy
   (gain < 3.0, ~chi-square at 2 df, p=0.05) — a two-parameter curve can always be
   bent through noise.

### TASK-762: pronunciation mode

A **different distractor problem**, so a different picker —
`pronunciation_distractors()`, nearest OTHER readings by edit distance
(`fuzzystrmatch`) over a per-language normalised form. Full rationale in
`migrations/calibration_pronunciation_mode.sql`. The four decisions that matter:

1. **Homophones excluded outright.** Identical reading = second correct answer;
   张 and 章 are both zhang1. The counterpart of the `vocab_id` sibling exclusion.
2. **Tone kept.** zh compares numbered pinyin, so `bǎ fēng`/`bā fēng` are one edit
   apart. Note this *differs from L1*, where tone-only pairs are invalid because
   TTS renders one of them; here the learner reads the options, so tone is testable.
3. **Distance cap scales with length.** A fixed 3-edit cap left 13% of zh items
   with zero options, all four-syllable words. `max(3, ceil(len*0.45))` took zh from
   19 empty / 25 short (of 150) to **0 empty / 2 short**.
4. **Same syllable count preferred** (not required) — a different-length reading is
   a different shape on the page and is discardable without knowing the word.

Also fixed by reading the output: the ja latin gloss suffix was leaking into the
rendered option (`いおん-Ion`), which made one option visibly a different shape — a
format tell. Hence `calibration_display_pronunciation()`, separate from the
comparison form.

**English is refused, not degraded.** Readings exist on only the native row, and
en has **21 of 6,555** senses (0.3%) versus zh 4,217 and ja 2,385. The route rejects
it and the UI disables the toggle. In pronunciation mode the session's definition
language is **ignored** — honouring it would select an empty set, because every
cross-language gloss row has `pronunciation` NULL.

Verified over 150 sampled items per language: 0 sibling leaks, 0 format tells, 0
duplicate options; zh 0 empty / 2 short, ja 4 empty / 7 short. Examples:
`政治 せいじ` vs せいふ/だいじ/せいぶ; `国际 guó jì` vs luó jí/gū jì/guó jí.

## Phase 4 — the handoff to test selection (COMPLETE, applied live — TASK-765)

### What connects to what

`user_calibration_state` is not a new invention: it is the **input contract**
[[features/vocabulary-aware-test-selection]] §1.1 already specifies, described
there as "built in parallel; this feature consumes it". Calibration writes it,
selection reads it, and neither calls the other. That boundary is the whole design
— it means selection can start consuming the measurement without Calibration
knowing anything about ELO, and it is why this phase touches neither
`get_recommended_tests` nor `process_test_submission`.

| written by Calibration | read by selection |
|---|---|
| `ability_zipf` | the ELO anchor (§1.2) and the untested-sense prior (§3.2) |
| `ability_se` | gate G3 — skip the rating write above 0.75 |
| `band_accuracies` | per-type offset evidence and diagnostics |
| `items_answered` | gate — skip below 20 |
| `last_run_at` | staleness gate |

### The contract was the risk, and it is satisfied

§1.2 is emphatic that `ability_zipf` MUST be the Zipf at which known-share crosses
85% — not a 50% crossover. On live data those map **431 ELO points apart**
(verified: `calibration_zipf_to_elo(5.00) = 1250`, `(3.85) = 1681`), and the wrong
end sends a learner who knows 17% of T4 vocabulary to T5 content.

Calibration's `ability_zipf_85` is that construct, and TASK-764 is what makes it
so: fitting `p(z) = 0.25 + 0.75·σ(a(z−b))` with the guess floor **fixed** means 85%
denotes *words genuinely known*, not *items answered correctly*. Those diverge most
at the bottom of the curve — exactly where a struggling learner sits — so removing
the guess floor is part of meeting the contract, not a refinement of it.

### Pooling, because precision is the constraint

`pooled_ability()` fits across **all** of a user's sessions in one language and
mode rather than reporting the last one. Precision is what binds this estimate
(sd 0.63 at 20 answers, 0.27 at 60, 0.16 at 120), pooling is what buys it, and
vocabulary knowledge does not decay over a few sessions so there is no reason to
prefer the most recent run. Modes are pooled **separately, never averaged**:
definition mode measures vocabulary, pronunciation mode measures reading, and
selection wants the former.

### The map lives in SQL and nowhere else

`calibration_zipf_to_elo(numeric)` interpolates the age-tier ladder, clamped to
[875, 1925]. Its ELO anchors are read from `dim_complexity_tiers` **at call time**
rather than written as literals, so the two halves cannot drift —
[[two-difficulty-to-tier-maps]] records that three copies already have to be kept
in step and this adds no fourth. The only Python copy is the fixture in
`scripts/verify_calibration_state.py` that asserts agreement with the SQL.

### Deliberately NOT shipped: the rating write

ADR-024 §4 puts the `user_skill_ratings` write behind hard guards, and §5 requires
every decision **including every skip and its reason** to be appended to
`user_skill_rating_adjustments`. That table did not exist when Phase 4 shipped; it
is TASK-746, built together with the guarded writer it audits (TASK-747). Shipping
the writer without its audit trail would be an unaudited automated write to live
user ratings — the precise thing those guards exist to prevent. So Phase 4 ships
the measurement and stops at the boundary.

### Applied live (TASK-765)

`migrations/calibration_user_state_and_zipf_to_elo.sql` is live. Verified
2026-09-10: `user_calibration_state` exists with PK `(user_id, language_id, mode)`
(0 rows — no calibration run has been completed yet), and
`calibration_zipf_to_elo` is STABLE and round-trips every anchor plus
`5.0 → 1250`, `3.85 → 1681`, and the clamps `7.0 → 875` / `1.0 → 1925`.
`python -m scripts.verify_calibration_state --self-test` passes both checks. It was
applied outside the migration history (no `schema_migrations` row), so the exact
timestamp is not recorded. Consumers still fail closed if the table is ever absent.

## TASK-757 — the dictionary screen (RUN)

Two defects, found to be different problems needing different detectors.

**1. Definitions that do not define the headword** — semantic, so it needs a model.
The embeddings cannot see it (every sense is embedded as `"{lemma}: {definition}"`,
so the lemma is *inside* the vector and a mis-keyed definition still sits near its
own headword), and no string rule can either.

All three languages swept, 14,400 senses, `google/gemini-3.5-flash-lite`,
757 calls, **$1.33 total**, 0 failed batches:

| language | senses | flagged | rate | self-reference FPs suppressed |
|---|---|---|---|---|
| en | 6,555 | 318 | **4.85%** | 117 |
| ja | 3,563 | 154 | **4.32%** | 4 |
| zh | 4,282 | 121 | **2.83%** | 6 |

zh being the cleanest is consistent with [[distractor-judge-v3-likert]], which found
the same thing once model artefacts were controlled for: under a common judge zh is
the cleanest of the three, not the worst.

The guard matters more than the model here. The first pass ran at ~55% precision,
flagging `associate` for "defining" *associate (noun)* and `tending` for *tend* —
inflections and part-of-speech readings of the headword, which is not the defect.
Tightening the prompt removed most at source and a post-filter on the model's own
`actually_defines` field caught the rest, taking a hand-checked sample to 5/5.
The guard compares **whole normalised strings, not leading tokens**: a first-token
version suppressed `hand` → "hand in hand", which is precisely the true positive
the screen exists to find.

Representative true positives:

- **en** — `work` defined as *agriculture*; `vast` as *various*; `long` → *long ago*,
  `high` → *high pitch*, `morning` → *morning cuppa* (the `hand in hand` pattern);
  and sense 14178, `land`, whose stored definition is the string *"The word 'land'
  does not appear in the provided target sentence"* — a generation error persisted
  as dictionary content.
- **ja** — `図書` (books) carrying the definition of 図書館 (library); `例えば`
  ("for example") defined as 印刷機 (printing press); `因る` → に因る.
- **zh** — `先河` → 开先河, the same phrase pattern; `解释权` (right of
  interpretation) defined as 决定权 (right of decision).

The pattern generalises: the `hand in hand` shape recurs in all three languages, so
this was never an English-specific defect.

**2. Malformed lemmas** — orthographic, so it needs no model at all. Found while
rate-checking Japanese: **90 ja lemmas (270 senses)** are MeCab morpheme sequences
stored as a headword — `作る れる ます`, `びっくり 為る ます た`, `ゲーム を 為る`.
The definitions are fine; the *prompt word* is garbage. The rule is exact rather
than heuristic, because Japanese and Chinese orthography do not use spaces: a space
in a zh/ja lemma cannot be part of the word. Measured zh **0**, ja **90**. English
is excluded — multi-word English lemmas are ordinary, not artifacts.

**Contained, still not fixed at source.** All 817 flags are written to
`calibration_anchor_blocklist`, which keeps them out of Calibration only. The
dictionary is still wrong for flashcards, practice and exercise generation. The
per-flag records are in `data/calibration/sense_mismatch_{en,ja,zh}.json` — each
carries the lemma, the stored definition, and what the screen judged it actually
defines — so an upstream repair has something to work from. That repair is
deliberately not automated here: rewriting a definition is a content decision, not
a screening one.

## Still open

- **TASK-763** — needs real learner traffic.
  `scripts/calibration_also_correct_report.py` is written and reports honestly that
  there is no data yet.
- Downstream, in [[tasklist/vocabulary-aware-test-selection.tasks]]: **TASK-746**
  builds `user_skill_rating_adjustments`, **TASK-747** the guarded rating writer,
  and **TASK-748** has selection consume `user_calibration_state`
  (`mode = 'definition'` only), with no change needed here.

## Related Pages

- [[features/calibration]] — prose counterpart
- [[decisions/ADR-025-semantic-distractor-selection]]
- [[tasklist/calibration.tasks]]
- [[database/schema.tech]], [[api/rpcs.tech]]
