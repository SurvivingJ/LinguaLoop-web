---
title: "ADR-025: Semantic distractor selection for Calibration"
status: accepted
date: 2026-09-08
---

# ADR-025: Semantic distractor selection for Calibration

## Context

Calibration is a standalone mode (nav item, infinite MCQ, outside session planning) that
shows a word and four definitions — or four pronunciations — to measure how much vocabulary a
learner actually knows.

The measurement only works if the three wrong options are hard. The existing picker,
`get_distractors()`, selects them with `ORDER BY random()`. Random foils make an item
answerable by elimination from world knowledge alone: a learner who has never seen the word
still scores, because two of the three options are about unrelated subject matter. The item
then measures test-taking, not vocabulary.

`dim_word_senses.embedding` (vector(1536), text-embedding-3-small) already existed and gave us
a semantic-distance signal. Three things stood between it and a usable picker.

1. **A third of the corpus was not embedded.** ja/en — the pair an English speaker studying
   Japanese sees, i.e. the primary use case — was at **0 of 7,126**.
2. **The only neighbour-search function, `nearest_senses()`, timed out on every call**
   (Postgres 57014) and had zero callers.
3. **There was no per-language notion of "semantically near"**, and the one constant in the
   codebase (`BAND_MIN = 0.35`) means very different things in different language pairs.

## Decision

### 1. The word's language is denormalised onto `dim_word_senses`

`nearest_senses()` was slow for a structural reason, not a tuning reason: it filtered
`dim_vocabulary.language_id` inside the lateral that also ordered by `embedding <=> anchor`.
An HNSW index can only serve a clean `ORDER BY embedding <=> <const> LIMIT k`; a predicate on
a *joined* table cannot be pushed into the index scan, so the planner abandoned HNSW and
sequentially scanned ~56,000 vectors per call.

We add `dim_word_senses.word_language_id`, so both language predicates sit on the same table
as the vector. It is a **derived** column, not merely a backfilled one: a
`BEFORE INSERT OR UPDATE OF vocab_id` trigger overwrites whatever the caller supplies, so a
sense cannot be created without it and cannot carry a wrong value.

### 2. Seven partial HNSW indexes, keyed on BOTH languages

The intended design was three indexes (one per word language), leaving definition language as
a post-index filter costing a known ~3x over-fetch. **Measurement rejected it.** On ja,
warm cache:

| design | pool / ef_search | time | buffers |
|---|---|---|---|
| 3 indexes (per word language) | 400 / 400 | **3,947 ms** | hit 4473, **read 3701** |
| 7 indexes (per language pair) | 100 / 100 | **19 ms** | hit 2274, read 0 |

~200x, because HNSW cost grows superlinearly in `ef_search` and the larger working set stops
fitting in `shared_buffers`. The over-fetch was not a constant factor on a cheap operation; it
was the dominant cost. The seven predicates are disjoint, so they partition the same rows:
438 MB total versus the 482 MB single global index they replace, and a write still touches
exactly one index.

### 3. `nearest_senses()` is dropped, not repaired

It timed out on every call and had zero callers. Its use case is served by the new function.
Repairing it would leave a second, subtly different neighbour searcher with no callers —
which is how it rotted the first time. Its definition is preserved in
`migrations/dim_word_senses_embedding.sql`.

### 4. A new RPC, `semantic_distractors()`, with the band as parameters

Not an overload of `get_distractors()` (still live, still correct for flashcards) and not of
`nearest_senses()`. It:

- excludes the anchor's **`vocab_id` siblings**, not just the anchor row;
- takes floor and ceiling as **parameters**, defaulting from a measured table;
- treats **frequency as a soft key and cosine as the hard one**, so the frequency band relaxes
  before the cosine floor ever does;
- restricts to `definition_level = 'standard'`;
- drops **morphological variants** of the anchor lemma.

### 5. Per-language-pair cosine floors live in `dim_distractor_bands`

A single 0.35 floor is seven different thresholds wearing one number — it admits 4.0% of
random unrelated pairs in en/en but 21.0% in ja/ja. Each pair's floor is the **p95 of its own
measured unrelated distribution**, so "above the floor" means the same thing everywhere. A
table, not constants, because the floors are empirical and keeping the measurement beside the
number is the only way a reader can tell a tuned value from a guess.

| word/def | floor | median | % above 0.35 |
|---|---|---|---|
| en/en | 0.34 | 0.200 | 4.0% |
| ja/en | **0.36** | **0.218** | **5.8%** |
| ja/zh | 0.38 | 0.240 | 7.7% |
| zh/ja | 0.39 | 0.244 | 9.7% |
| zh/en | 0.40 | 0.255 | 12.7% |
| zh/zh | 0.41 | 0.240 | 12.4% |
| ja/ja | 0.44 | 0.275 | 21.0% |

ja/en was measured **after** the backfill; it could not be measured before, because the pair
had no embeddings at all.

## Consequences

**Easier.** Distractor selection is a single indexed RPC at ~20 ms. Re-tuning a band is an
`UPDATE`, not a redeploy. The pronunciation mode of Calibration can reuse the same function.

**Harder / constrained.**

- `dim_word_senses` carries a denormalised column. Justified because a word's language is
  fixed at creation (`dim_vocabulary` is keyed `(language_id, lemma)`; the same lemma in
  another language is a different row), and enforced by trigger so it cannot drift.
- Seven HNSW indexes must be rebuilt if the embedding model changes.
- Index builds are serial-only on this instance: `max_parallel_maintenance_workers > 0` fails
  with `53100: could not resize shared memory segment` because /dev/shm is too small.

**The limit we are accepting, explicitly.** Cosine cannot separate "unrelated" from
"duplicate". Same-word pairs have a median similarity of only 0.73–0.76 and 88–94% fall below
0.88; meanwhile the unrelated distribution's top (p99 0.43–0.56) overlaps the same-word
distribution's bottom (p5 0.33–0.57). No threshold exists. So:

- exact exclusions (`vocab_id` siblings, stem variants) do the duplicate-catching work;
- the 0.75 ceiling is **provisional** and currently binds on only ~0.2% of returned foils;
- **different-word synonyms from an unrelated stem will get through** — 因子 against 要因,
  適正 against 妥当 at cosine 0.736. 12–21% of returned foils sit at cosine ≥ 0.70, the band
  where this risk lives. Catching them requires response data: an option that strong learners
  pick as often as the key *is* a second right answer, and no embedding geometry reveals that
  in advance. This is the first thing Calibration's own logs should be used for.

## Alternatives Considered

**Repair `nearest_senses()` instead of adding a function.** Rejected — see decision 3.

**Three indexes with a definition-language post-filter.** Rejected on measurement (decision 2).
This was the intended design and it was ~200x slower.

**Six or fourteen indexes (adding `definition_level`).** Rejected. `definition_level` is a
caller-overridable parameter, and a ~2x post-filter leaves ~50 candidates for 3 slots at
pool 100 — comfortably enough, with zero starvation observed over 1,400 sampled items.

**A single global cosine floor.** Rejected on measurement (decision 5).

**Re-embedding definitions without the lemma prefix.** Rejected, and deliberately not
attempted. The `"{lemma}: {definition}"` recipe is load-bearing: short generic definitions
collapse onto one vector when embedded bare. It is also precisely *why* the `vocab_id` sibling
exclusion is necessary — the lemma being inside the text makes a word's own rows its nearest
neighbours.

**Screening also-correct answers with an LLM judge at selection time.** Rejected for Phase 1:
it puts a model call on an interactive path that currently costs ~20 ms. Revisit only if
response data shows the problem is material.

## Related

- [[features/calibration]] — what Calibration is
- [[features/calibration.tech]] — the technical specification
- [[tasklist/calibration.tasks]] — task breakdown
- `migrations/calibration_sense_word_language_and_partial_hnsw.sql`
- `migrations/calibration_semantic_distractors.sql`
- `scripts/dump_calibration_distractors.py` — the sampling harness
