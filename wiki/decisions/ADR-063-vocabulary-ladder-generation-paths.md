---
title: "ADR-063: Vocabulary-ladder generation: one bulk path and one top-up path"
status: proposed
date: 2026-11-23
---

# ADR-063: Vocabulary-ladder generation: one bulk path and one top-up path

> **PROPOSAL for the owner's decision. Nothing here is decided or built.** It would supersede the "fat-seed as the sole method" rejection in [[decisions/ADR-028-exercise-gen-cost-under-1c]] (accepted 2026-09-24). Evidence below was read from the live database and the code on 2026-11-23.

## Context

Exercise assets for the vocabulary ladder (see [[algorithms/vocabulary-ladder.tech]], [[features/exercises.tech]]) can be produced by several pipelines that grew side by side:

1. **Hosted generation (default).** `services/vocabulary_ladder/ladder_service.py` and `asset_pipeline.py` call hosted models through OpenRouter. Driven in bulk by `scripts/run_generation_batch.py` (623 lines), `run_content_build.py` (659) and `run_ladder_from_existing.py` (181); driven per sense by the nightly generation-queue drain (`services/vocabulary_ladder/queue_drain.py`, job `generation_queue_drain_nightly`, 04:15).
2. **Bundle mode** (`services/vocabulary_ladder/bundle/`, flag `VOCAB_LADDER_BUNDLE_MODE`, off by default). **Deleted 2026-11-23** (1,618 lines plus four test files of 827 lines in total; untouched since 2026-10-11, failed the quality comparison in every language, see [[evaluations/exercise-gen-phase2-2026-10]]). Leftovers: `migrations/exercise_gen_bundle_prompts_draft.sql` (never applied; no `vocab_bundle_generation` or `ladder_bundle_judge` row exists in `prompt_templates`) and comments in `services/llm_service.py`.
3. **Staged CSV runner** (`scripts/exercise_stage_runner.py`, 605 lines, with `export_exercise_worklist.py` and `upload_exercises.py`; skills `batch-exercise-authoring` (192 lines) and `batch-exercise-judging` (110)). The agent answers the live prompts stage by stage. See [[features/csv-exercise-authoring.tech]].
4. **Fat-seed** (`scripts/fat_seed_runner.py` 657 lines, `services/vocabulary_ladder/fat_seed.py` 606, `scratch_offline/` 13 files, 3,355 lines; skills `fat-seed-authoring` (229) and `fat-seed-review` (100)). One JSON document per sense written by headless `claude -p` calls, uploaded as a SQL package, then rendered with stage 8 and `render` of the staged runner.
5. The older **`batch-exercise-generation` skill** (328 lines), which exports senses with no exercises plus the live prompts and uploads through `upload_exercises.py`.

**Evidence (live, SELECT only, 2026-11-23).** `word_assets.model_used`, distinct senses:

| Tag | Senses | Note |
|-----|--------|------|
| `claude-code:fat-seed` | 10,793 | zh 7,757, ja 3,036 |
| `claude-code:batch-exercise-generation` | 108 | all ja; shared by the staged runner (it is `upload_exercises.py`'s default tag) and the batch skill, so their output cannot be told apart |
| `per-type (see prompt_templates)` | 55 | hosted |
| hosted named models (qwen, gemini, claude) | 57 | hosted; the per-model sense counts sum to 81 because a sense can carry several models |
| all hosted tags together | 65 | distinct senses (the 57 and the 55 overlap); summing per-tag counts gives about 136, which double-counts |

Of 10,958 senses that have any asset, fat-seed wrote 10,793 (98.5%). (The dictionary holds 73,003 senses; most have no exercises.) Hosted models wrote 65 distinct senses (0.6%).

`generation_queue` (the nightly drain's queue): 4 done, 103 failed, 7 running. The 7 `running` rows were all requested 2026-08-21 04:15 and have no completion time, 94 days before the check: they are stuck, not in progress. Of the 103 failures, 83 are `Prompt 1 generation failed` (43 from `prestudy`, 40 from `evidence_queue`); the newest failure is 2026-11-17. So the path this ADR names as the top-up path is, today, mostly failing; the cause was not investigated.

**Code facts about the fat-seed tooling.** `scratch_offline/` is excluded from ruff (`pyproject.toml`), has no tests, and its stand-in for the database (`scratch_offline/offline_db.py`) returns an empty list for a table it has no snapshot of, logging `MISSING <table>` to a file instead of raising, so a new uploader query silently reads nothing. `tests/test_fat_seed.py` covers `services/vocabulary_ladder/fat_seed.py` (329 lines) only.

**Relation to ADR-028.** ADR-028 rejected "fat-seed subagent path as the sole generation method" because it was unmeasured at scale (n=6) and one comparison found a defect class (compound-word anchoring) that the staged chain's separate P1 sentence judge catches. Since then fat-seed produced 10,793 senses and gained its own review step (`fat-seed-review`, judging against the live judge rules). This ADR would reverse that part of ADR-028 for **bulk** work; ADR-028's cost target for hosted generation and its model rules stay in force for the top-up path. The attribution eval ADR-028 planned (bundle mode versus the reasoning setting changed at the same time) was never run, and the deletion of bundle mode forecloses it.

## Decision (proposed)

1. **Fat-seed is the bulk path** for building assets for many senses or a new language.
2. **The nightly queue drain (hosted generation, `queue_drain.py` through `ladder_service`) is the only top-up path** for individual new senses. Hosted bulk scripts remain only as drivers of that same code.
3. **Retire stages 1-6 of the staged runner** (the unit builders and `bridge`/`assemble`, about 280 of 605 lines: lines 82-364 of `scripts/exercise_stage_runner.py`) and the two skills `batch-exercise-authoring` and `batch-exercise-generation`. **Keep stage 8, `render` and `batch-exercise-judging`**, which fat-seed uses after upload (`fat-seed-authoring` step 7).
4. **Give each path its own `model_used` tag** (for example `claude-code:fat-seed`, `claude-code:staged-csv` if any staged use survives, `hosted:<model>`), so provenance is readable.
5. **Move `scratch_offline/` into a tested, linted package** (for example `tools/fat_seed/`): include it in ruff; add a test that runs `package_upload.py` on a small fixture and one that runs the uploader through the offline database on a fixture snapshot; make the offline database raise on an unknown table.
6. Fix or retire the nightly drain before relying on it: clear the 7 stuck `running` rows and find why Prompt 1 generation fails.

## Consequences

- **Deletable if accepted** (line counts re-measured 2026-11-23 with `wc -l`): about 280 lines of staged-runner stages 1-6; two skills (192 + 328 = 520 lines); their share of `tests/test_csv_exercise_authoring.py` (315 lines, to be split, not all removed). Bundle mode (1,618 + 827 test lines) is already gone.
- Easier: one place to look for each job; provenance by tag; the fat-seed pipeline gets tests and lint.
- Harder: a small batch of senses that needs the judge in the loop (the staged path's strength) has no dedicated route; it would go through the hosted drain or a small fat-seed run followed by `fat-seed-review`.
- Constrained: stage 8 and `render` become part of the fat-seed contract and need to stay compatible with `fat_seed_runner.py`.

## Risks

- Losing the staged path's judge-in-the-loop for small batches (see above).
- The top-up path is currently failing (83 Prompt 1 failures, 7 stuck rows); making it the only top-up path before fixing it would leave new senses without exercises.
- Tag changes affect any query or report that filters `word_assets.model_used`; existing rows keep their old tags.
- Fat-seed rests on headless Claude subscription calls, logged at $0 in `llm_calls` (ADR-028 open question c), so its cost is invisible.

## Alternatives Considered

- **Keep all paths.** No migration work, but four ways to do one job, ambiguous provenance and an untested production orchestrator.
- **Make the staged runner authoritative.** It has the judge-in-the-loop and shares the live prompts, but it produced at most 108 senses against 10,793 for fat-seed, and it was the slower route for bulk work.
- **Make hosted generation authoritative for bulk.** Cost and quality were the point of ADR-028 and the Phase 2 evaluations; the target of under $0.01 per sense was not met at non-inferior quality, and it produced a small share of the content.

## Open questions

- Why does Prompt 1 generation fail for `prestudy` and `evidence_queue` requests (not investigated)?
- Does the owner accept that fat-seed output (reviewed by `fat-seed-review`) is good enough for bulk, given that ADR-028's concern about compound-word anchoring was never re-measured on the 10,793 senses?
- The earlier working figure of "roughly 136 hosted senses" sums per-tag counts; the distinct count is 65 (checked 2026-11-23).

## Related Pages

- [[decisions/ADR-028-exercise-gen-cost-under-1c]]
- [[algorithms/vocabulary-ladder.tech]]
- [[features/csv-exercise-authoring.tech]]
- [[features/exercise-generation-prompts]]
- [[evaluations/exercise-gen-phase2-2026-10]]
