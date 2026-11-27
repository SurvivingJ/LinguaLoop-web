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

## Follow-up the same day: model choice and the pilot

The OpenRouter key had $0.22 left, so the owner chose their Anthropic key. 20 random ja items
needing an explanation (12 spot, 8 pick), effort medium, standard price, all answers valid:

| Model | In / out tokens | Per item | 17,256 items | Batched (50%) | Time |
|---|---|---|---|---|---|
| Claude Opus 5.5 | 730 / 722 | $0.0174 | ~$300 | ~$150 | 7.0 s |
| Claude Sonnet 5.5 | 726 / 460 | $0.0061 | ~$105 | ~$52 | 3.7 s |
| Claude Haiku 5.5 | 726 / 1,075 | $0.0006 | ~$10.50 | ~$5.30 | 5.2 s |

Owner chose Sonnet 5.5. Pilot through the Message Batches API: 20 senses, 38 items, all 38
returned within 2 minutes, 37 usable (one answer appended a corrected second JSON — the parser
now takes the last valid one), 20 files written, $0.1239 (estimate $0.12); the serving path
attached all 37 from the files with the model disabled. Storage reads of cold files took up to
~2 s, so the serving read budget was raised to the hydration's 3 s.

## Full Japanese run, 2026-11-27

`scripts/prewrite_explanations_anthropic_batch.py --apply`, Claude Sonnet 5.5, effort medium,
Message Batches on the owner's key.

| | |
|---|---|
| ja senses with spot / pick items | 5,963 (20 had pilot files; 7 more had only items whose own notes already cover every sentence) |
| Items written | **17,218**: 11,638 spot (every one with its reviewed corrected sentence), 5,580 pick |
| Items not needing a model | 5,429 pick items whose own English notes explain every sentence |
| Batches | 4 (5,000 / 5,000 / 5,000 / 2,218), created 01:16 UTC; 3 failed items re-sent in one retry batch; collected 01:29 (~13 min) |
| Usable answers | **17,218 / 17,218** |
| Files written | **5,936** (0 senses held back at prepare or collect) |
| Tokens | 12,464,465 in / 8,127,642 out |
| Cost | **$53.10** (estimate $52.17; with the pilot $53.23) |
| Storage after | `explanations/ja/`: 5,956 files, 30 MB; bucket `exercise-content` 195 MB of 1 GB |
| Database after | 487,017,619 B (464 MiB). Each Storage file also has a `storage.objects` row (~0.5 KB): ~3 MB for these 5,956 |

### Serving check (model calls disabled; `call_llm` patched to raise)

Items served through `exercise_explanations.prefetch` + `prepare_items`, as the session request
does, after content hydration:

| Sample | Attached | Source |
|---|---|---|
| 400 random items the batch wrote | **400 / 400** | 274 spot + 126 pick from files |
| 400 random active ja items (200 spot, 200 pick, paged past the 1,000-row API cap) | **400 / 400** | 200 spot from files; pick 106 from files, 94 from their own notes |

0 model calls. Every attached item had one entry per sentence; file entries had a meaning and
an explanation for each.

**Cold reads at the live 3 s budget** (files not yet read by anyone; this container, like the
Railway app, is far from the Sydney Storage origin, ~1–1.8 s per cold GET; 6 file readers):

| Explainable items per request (≈ distinct senses) | Attached at serve time | Missed, then found by the background job's file re-read |
|---|---|---|
| 8 | 192 / 200 (median read 2.15 s) | 8 / 8 |
| 20 | 138 / 200 (median 3.00 s, the budget) | 62 / 62 |

A miss costs no model call: the background job re-reads the file before generating, and the
renderer's explanation request waits on that job. Real ja sittings in the last 30 days held
~9.8 explainable items over **4.6 senses** on average (max 16), so one round of reads usually
suffices; a file once read is cached in the process (8 MB LRU) and warm at the CDN. If cold
misses show in production, raise `explanation_files._WORKERS` together with the shared
HTTP client's connection limit (`concurrency + 4` = 20, shared with the content reader's 16).
