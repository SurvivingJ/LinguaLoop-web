---
title: Storage cost of pre-writing exercise explanations — 2026-11-27
type: evaluation
status: complete
last_updated: 2026-11-27
---

# Storage cost of pre-writing exercise explanations — 2026-11-27

Owner: "Estimate the storage cost of pre writing all explanations." Context:
[[decisions/ADR-064-exercise-explanations-generated-once-and-cached]].

## Measured inputs

- **Payload size** (three live ja spot items, prompt v2, `pg_column_size(...::jsonb)`): 1,472 /
  1,536 / 1,684 bytes, mean ~1.56 KB. Rows (~1.66 KB with header and line pointer) are below
  the ~2 KB TOAST threshold, so they are stored inline and uncompressed: 4–5 per 8 KB page,
  **~1.9 KB per item on disk** plus ~40 B of primary-key index.
- **Items that need a model-written explanation** (English learners): every spot item, and the
  pick-the-sentence items whose stored notes do not already cover every sentence in English
  (ja 113/200 sampled = 56.5%; zh 47/150 = 31%).

| Language | Spot | Pick needing one | Rows | Database size |
|---|---|---|---|---|
| ja | 11,676 | ~6,240 of 11,042 | ~17,900 | **~35 MB** |
| zh | 14,856 | ~4,560 of 14,725 | ~19,400 | **~38 MB** |

Each further learner language multiplies the rows.

- **Database**: 473.3 MB on 2026-11-27 (`pg_database_size`). Free plan cap 500 MB → 26.7 MB
  left; the seeding runbook works to a 475 MB line → 1.7 MB left.
- **Storage**: bucket `exercise-content` 160 MB (14,606 files, mean 11.5 KB) +
  `llm-logs-archive` 6 MB = 166 MB of the Free plan's 1 GB.

## Options

| Where | Format | ja | ja + zh | Fits the Free plan? |
|---|---|---|---|---|
| table, as built | full JSON | ~35 MB | ~73 MB | No — DB ~508 MB with ja alone |
| table | lean JSON (no sentence text, compact arrays: 988 B mean) | ~22 MB | ~45 MB | ja only just under 500 MB; far over 475 MB |
| table | lean + forced compression (`toast_tuple_target`, zlib ~714 B as a guide) | ~15 MB | ~31 MB | ja under 500 MB; over 475 MB |
| Storage files (one per sense and learner language, beside the content files) | full JSON | ~27 MB | ~57 MB | Yes — 166 → ~225 MB of 1 GB; database unchanged |
| table, lazy (current) | full JSON | ~5 MB a year per daily learner | — | Yes for now |

Storage files would also load with the exercise content (one parallel GET per sense, cached),
instead of a table read. Model cost to pre-write is separate: ~$0.00025 per item
(deepseek-v4.1-flash, measured), ~$4.5 for ja, ~$4.9 for zh.

## Recommendation

Keep the lazy table for live use. If everything is to be written ahead, write it to Storage
files, not the table; or upgrade the plan, which removes the database constraint.
