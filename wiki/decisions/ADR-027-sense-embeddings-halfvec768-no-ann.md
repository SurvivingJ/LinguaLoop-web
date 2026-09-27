---
title: "ADR-027: Sense embeddings stored as halfvec(768) with no ANN index"
status: accepted
date: 2026-09-22
---

# ADR-027: Sense embeddings stored as halfvec(768) with no ANN index

## Context

The Supabase database had to come in under 400 MB. On 2026-09-21 it was 1,144 MB, and
`dim_word_senses` alone was 960 MB of that:

- ~466 MB of TOAST for 55,002 text-embedding-3-small vectors (float32, 1536-d, ~6 KB each).
- ~456 MB across seven partial HNSW indexes, one per (word language, definition language)
  pair. About a quarter of each index was page padding, because a 6 KB element fits only once
  per 8 KB page.

Everything else in the database was ~140–180 MB. Tidying columns, dropping dead tables and
archiving unused modules (2026-09-21/22) only reached 1,098 MB. The embeddings had to change.

The only consumers are `semantic_distractors()` (calibration foils; its results are cached in
`calibration_distractor_cache`, so it runs only on cache misses) and
`sense_similarity_to_lemmas()` (a brute-force band check with no index).
[[decisions/ADR-025-semantic-distractor-selection]] defines what they do.

## Decision

1. Store `dim_word_senses.embedding` as **halfvec(768)**: the first 768 dimensions,
   L2-normalised, stored in fp16. text-embedding-3-small is Matryoshka-trained, and OpenAI's
   `dimensions=768` is defined as exactly this truncate-and-normalise. Topic and passage
   embeddings are not affected and stay 1536-d.
2. **Drop the HNSW indexes.** `semantic_distractors()` now does an exact nearest-neighbour
   scan of one language pair.
3. Re-baseline the similarity thresholds by the measured shift: `dim_distractor_bands.cos_min`
   per pair (+0.010 to +0.019), `cos_max` +0.01, and `sense_neighbours.BAND_MIN` from 0.35 to
   0.365.
4. Every writer calls `scripts/backfill_sense_embeddings.py::sense_vector()`. The column
   rejects vectors of any other length.

Migration: `migrations/shrink_sense_embeddings_halfvec768.sql` (applied 2026-09-22).

## Consequences

- **Size.** The database went from 1,098 MB to **252 MB**, and `dim_word_senses` from 960 MB to
  113 MB. Each 1,000 new senses adds about 2 MB.
- **Quality.** Against the 1536-d vectors, cosine correlation is 0.980, top-10 neighbour overlap
  is 92% and top-100 overlap is 90%. About 1 in 10 calibration foils changed when the cache was
  rebuilt. The changes are concentrated in the mid-similarity band that foils are drawn from.
- **Latency.** The exact scan of en/en (10.8k rows) takes ~16 ms warm and ~0.7 s on a cold
  first read. The old HNSW path took ~1.1 s cold, because the indexes (442 MB) could not stay
  resident in 224 MB of shared_buffers. The exact scan also has no ANN recall loss.
- **Irreversible in SQL.** Dimensions 769–1536 are gone. To undo, re-embed at 1536-d
  (~$0.03, ~1.6M tokens) and recreate the indexes from
  `migrations/calibration_sense_word_language_and_partial_hnsw.sql`.
- **Constraints on future work.**
  - A writer that skips `sense_vector()` fails loudly, which is good. The exception is
    embed-on-create in `sense_generator`, which swallows the failure and leaves a NULL
    embedding until the next backfill.
  - Sense embeddings can no longer be compared with the 1536-d topic and passage embeddings.
  - If a language pair grows past roughly 100k senses, add an HNSW index on halfvec(768)
    (~2 KB/row).

## Alternatives Considered

- **halfvec(1536), lossless.** 100% neighbour overlap, but ~660 MB in total, which misses the
  target.
- **halfvec(768) and keep HNSW.** ~415 MB, which misses the target.
- **halfvec(512).** 87% top-100 overlap. Smaller than needed; 768 already meets the target
  with room to spare.
- **Supabase Pro ($25/month, 8 GB).** No quality loss. Rejected: the requirement was to shrink
  the database, not to pay for more space.
