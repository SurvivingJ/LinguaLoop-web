---
title: "ADR-038: Calibration distractor cache stores one packed row per anchor"
status: accepted
date: 2026-10-30
---

# ADR-038: Calibration distractor cache stores one packed row per anchor

## Context

Vocabulary storage phase 2 (phase 1: [[decisions/ADR-037-one-sense-vector-native-standard-512]]).
The project is on Supabase Free (500 MB) and the content target is 10k zh + 10k ja words with
full ladders.

`calibration_distractor_cache` (TASK-773) stored **one row per option**: 211,692 rows
(162,613 definition + 49,079 pronunciation) in 46 MB, about 133 B of heap plus 60 B of index per
row. At target scale it would reach ~110 MB.

Most of each row could be derived from `sense_id`. Checked on all 211,692 live rows on
2026-10-29, with 0 mismatches:

- `option_text` is `dim_word_senses.definition` in definition mode, or
  `calibration_display_pronunciation(pronunciation, word_language_id)` in pronunciation mode;
- `vocab_id` is `dim_word_senses.vocab_id`;
- `frequency` is `dim_vocabulary.frequency_rank`;
- `word_language_id` / `definition_language_id` are the anchor row's own languages;
- each anchor's ranks ran contiguously from 0.

Removing the cache altogether was not an option: `pronunciation_distractors()` costs ~180 ms
per call, and `calibration_build_items()` builds 20 items per request (TASK-770).

## Decision

1. Store **one row per `(anchor_sense_id, mode)`**. The ranked options are kept as arrays:
   `sense_ids integer[]`, `similarities real[]` (definition mode only; NULL in pronunciation
   mode) and `freq_tiers smallint[]` (edit distance in pronunciation mode).
2. `calibration_cached_options(mode, anchor)` expands a packed row back to the old shape
   (`rank, sense_id, vocab_id, option_text, similarity, frequency, freq_tier`). It joins the
   option text and frequency live.
3. `calibration_fill_distractor_cache()` now writes the packed row, and
   `calibration_build_items()` reads through the helper. Neither function changes in any other
   way. `calibration_cache_distractors_chunk()` and `calibration_distractor_cache_coverage()`
   are unchanged, because they only test EXISTS on `(mode, anchor_sense_id)`.
4. The existing contents were carried over, so no rebuild was needed.

Migration: `migrations/calibration_distractor_cache_packed.sql`, applied 2026-10-30 in the
Supabase SQL Editor. A second run of the same script failed on `_packed` and rolled back, which
was harmless.

## Consequences

- **Size.** 46 MB → **7 MB**, 33,599 rows, all 211,692 options intact. Projected ~18 MB at
  target scale.
- **Fresher options.** Definitions and readings are read at serve time, so a corrected
  definition or reading reaches learners at once instead of waiting for a cache rebuild. On
  2026-10-30, 263 cached pronunciation options already pointed at readings another job had
  corrected that day (e.g. `bù fèn` → `bù fen`). Before this change they would have kept
  showing the old text. A re-check found no foil that had become a homophone of its anchor.
- **What can still go stale.** The *choice* of foils still can: similarity and edit distance
  are fixed when an anchor is filled. Rebuilding stays the right step after a bulk change to
  definitions, embeddings or readings.
- **Serving cost.** Each anchor costs one primary-key lookup plus a join over ≤ 8 senses.
  Expanding the whole cache (211,692 options) runs in well under a second.

## Alternatives Considered

- **Keep one row per option but drop the derivable columns.** About 92 B per row → ~48 MB at
  target. Rejected: the packed form is ~6× smaller still.
- **No cache.** Rejected because of pronunciation-mode latency (above). The definition path
  alone would now be fast enough (~10–15 ms per anchor with exact scans, ADR-037).
