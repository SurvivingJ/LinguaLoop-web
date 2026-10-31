---
title: "ADR-038: One sense vector per meaning, on the native standard row, halfvec(512)"
status: accepted
date: 2026-10-29
---

# ADR-038: One sense vector per meaning, on the native standard row, halfvec(512)

Supersedes the storage half of [[decisions/ADR-027-sense-embeddings-halfvec768-no-ann]]
(the "no ANN index, exact scan" half still holds).

## Context

The project is on Supabase Free, which caps the database at 500 MB. The content target is
10,000 zh + 10,000 ja words, each with full vocabulary ladders (variants A and B), and more
languages later. On 2026-10-28 the database was 270 MB:

- `dim_word_senses` was 113 MB, and its `embedding` column alone 85 MB (55,002 halfvec(768)
  vectors, 1,544 B each). The rows were just under the TOAST threshold, so vectors stayed
  inline and only 4 rows fit on an 8 KB page.
- **One meaning was embedded up to six times**: native simple + native standard, and two
  cross-language glosses (e.g. zh word with en and ja definitions) at two levels each. At
  10k + 10k words that is ~131k rows, ~270 MB for this table alone.
- The `simple` vectors did no work. `semantic_distractors()` ordered its candidate pool by
  vector *before* filtering on `definition_level`, so `simple` rows only took pool slots and
  were then thrown away. `calibration_refresh_anchor_pool()` only reads `standard` rows.
- Cross-language gloss vectors embedded `"{lemma}: {gloss}"`, where a simple ja gloss averages
  3 characters. The native definition says more about the meaning.

Every gloss and simple row has exactly one "twin": the native standard row with the same
`(vocab_id, sense_rank)` (verified live 2026-10-28 for all 26,158 simple rows and all 14,614
non-native standard rows).

## Decision

1. **A sense has one vector**, stored on its native standard row
   (`definition_level = 'standard' AND definition_language_id = word_language_id`). Every other
   row of the sense reads it through `public.sense_embedding(sense_id)`.
2. The rule is a **CHECK constraint**, `dim_word_senses_embedding_native_standard_chk`, so a
   writer cannot regress it. Writers use `scripts/backfill_sense_embeddings.py::is_embedded_row`.
3. **Truncate to halfvec(512)** and re-normalise (text-embedding-3-small is Matryoshka-trained,
   so this equals the API's `dimensions=512`).
4. `semantic_distractors()` scans the **word language's native standard vectors**, then joins
   each neighbour to the row the learner reads (requested definition language and level).
5. Cross-language pairs now score native-definition vectors, so their `dim_distractor_bands`
   rows take the native pair's band. All bands shift by the measured 768→512 shift.

Migration: `migrations/sense_vectors_native_standard_512.sql` (applied 2026-10-29 via the
Supabase SQL Editor; the MCP `apply_migration` approval prompt never reached the developer).

## Consequences

- **Size.** `dim_word_senses` 113 → **33 MB**; database 270 → **193 MB**. Vectors: 55,002 →
  14,230. Projected at 10k zh + 10k ja words: ~75 MB for the table.
- **Quality.**
  - 512-d vs 768-d: correlation 0.983–0.988; top-20 neighbour overlap 90–92%.
  - p95 shift of unrelated pairs: zh +0.016, en +0.016, ja +0.012.
  - New bands: zh pairs `cos_min` 0.445, ja pairs 0.463, en/en 0.366; `cos_max` 0.77 for all.
  - `sense_neighbours.BAND_MIN` 0.365 → 0.377; `BAND_MAX` unchanged.
  - Spot checks after the rebuild looked right, e.g. 支柱 → 支撑 / 支点 / 框架.
  - The full 100-slot pool now goes to the requested level, so more candidates survive the filters.
- **Cache.** `calibration_distractor_cache` (definition mode) was dropped and rebuilt on the new
  vectors: 162,613 rows, ~10–15 ms per anchor. 7–10 anchors per pair came up short and are
  recorded as misses, as before.
- **Irreversible in SQL.** Dimensions 513–768 and the non-native vectors are gone. Undo means
  re-embedding at a higher dimension (cents) with the old writer code.
- **Constraints on future work.**
  - A new language needs no extra vectors for its glosses: only its own words' native standard
    rows are embedded.
  - Any new reader of sense vectors must go through `sense_embedding()` (or join to the twin);
    `dim_word_senses.embedding` is NULL on 3 of every 4 rows by design.
  - Similarities for a cross-language pair are now the native pair's similarities. A band
    re-measurement for a cross pair must use native vectors.

## Alternatives Considered

- **Keep 768-d, only drop simple + gloss vectors.** ~22 MB more at today's size, ~35 MB more at
  target. Rejected: the 512-d quality loss is small (90–92% overlap) and the developer accepted it.
- **Move vectors to a side table.** Fixes the page-packing waste, but once 3 of 4 rows carry no
  vector the main table packs well anyway, and every reader would have to change.
- **Supabase Pro.** Rejected by the developer: the project stays on Free.
- **Inline compression (`toast_tuple_target` + lz4).** Measured: no effect. PG only toasts rows
  larger than ~2 KB; these rows are smaller, and halfvec does not compress.
