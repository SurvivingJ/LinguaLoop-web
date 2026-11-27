---
title: Offline test bundles — Technical Specification
type: feature-tech
status: in-progress
prose_page: offline-test-bundles.md
last_updated: 2026-11-27
dependencies:
  - "services/test_generation/orchestrator.py (_generate_test, _export_record, _persist_test, persist_exported_test)"
  - "scripts/export_offline_tests.py"
  - "scripts/upload_offline_tests.py"
  - "services/llm_service.py (forced_provider, db_call_logging_enabled)"
  - "tables: tests, questions, test_skill_ratings, generation_review_queue, production_queue (read), topics (read)"
breaking_change_risk: low
---

# Offline test bundles — Technical Specification

## Architecture Overview

```
export_offline_tests --shard k  (×N processes, each a BatchModeThreadPoolExecutor of --workers)
   └─ TestGenerationOrchestrator._generate_test(dry_run=True,
         prose_extra_instruction=<angle>, export_sink=list.append)
         translate → prose → tier → dedup (read) → title → questions+judges → validator
         → _export_record(...)  (furigana + pitch computed here)
   └─ <out>/shards/shard_k.jsonl   (append; resumable by slot_key)
export_offline_tests --assemble
   └─ <out>/tests.jsonl.xz  +  <out>/manifest.json        ← committed
upload_offline_tests --bundle <out> [--apply]
   └─ skip checks → optional embedding + near-dup → persist_exported_test(record)
         └─ _persist_test: audio → insert_test → questions → review queue
            → skill ratings → script payloads → _generate_vocabulary
```

A live run calls `_persist_test` with the same record built by `_export_record`, so the
live save path and the upload path are the same code.

## Environment for a Claude-only, database-silent run

| Variable | Value | Effect |
|---|---|---|
| `--provider claude-cli` | flag | process default provider; concurrency capped by `scripts/provider_arg.py` |
| `LLM_FORCE_PROVIDER` | `claude_cli` | overrides providers pinned by callers (judges pin `openrouter`); entailment judge uses its LLM backend; `call_jev` raises `JevError`; `tier_classifier.classify_passage` asks Claude; `ProseWriter.client` (phrase detection) is the forced client |
| `LLM_CALLS_DB_LOG` | `0` | no `llm_calls` rows (calls or judge verdicts) and no `generation_stage_timings` rows; `logs/llm_usage/*.csv` still written |
| `OPENROUTER_API_KEY` | dummy value | belt and braces: a path that still reaches OpenRouter fails with 401 instead of spending |
| `OPENAI_API_KEY` | dummy value | the test-gen config requires one; the embedding call then fails and dedup degrades to exact-hash only (`dedup.py`) |

Database reads still happen (topics, prompt templates, tier configs, question distributions,
exact-hash dedup against `tests`). Verified on the 4-slot pilot: row counts of `llm_calls`,
`tests`, `questions`, `generation_stage_timings`, `dim_word_senses`, `generation_review_queue`
unchanged.

## Slot plan (`build_slots`)
- Topics: every `production_queue` topic of the language, any status, ordered by number of
  live tests in that language (ascending), then by queue row age (`queue_topic_ids`).
- Topic *i* takes the tiers rotated by *i*; slots are ranked `(round, topic)` so every topic
  gets one tier before any gets a second. For ja on 2026-11-27: 165 topics × tiers 1–4,
  500 slots = 125 per tier, every topic used 3 times (5 topics 4 times).
- Angle: `ANGLES[(topic_index + tier) % 8]`, appended to the prose prompt through
  `generate_prose(extra_instruction=...)`. The dedup retry keeps the angle and adds the nudge.
- Shard *k* of *N* takes slots with `index % N == k`.
- Slug: the generated slug plus `-<first 8 hex of test_id>`. Without it, two slots of one topic
  at the same difficulty in the same second produce the same slug (seen in the pilot).

## Record format (`EXPORT_RECORD_VERSION = 1`)
One JSON object per line, keys sorted, UTF-8, xz preset 9:

`record_version, test_id, slug, language_id, language_code, language_name, topic_id,
topic_concept_english, category_name, target_tier_id, tier_id, legacy_difficulty,
transcript, title, initial_elo, seeded_elo, age_tier_score, age_tier_confidence,
age_tier_probabilities, age_tier_model, age_tier_calibration, passage_hash,
generation_model, test_type, voice, tts_speed, prose_extra_instruction, questions[],
pinyin_payload, pitch_payload, furigana_payload, created_at, slot_key, slot_angle`

`questions[]` holds the validator-accepted, judge-passed questions in mix order: `question,
choices, answer, correct_answer_index, type_code, distractor_types, _judge_flags` (choices
already shuffled). `persist_exported_test` refuses any other `record_version`.

`manifest.json`: `format, record_version, language, built_at, tests, questions, topics,
assigned_tiers, seeded_elo{min,median,max}, generation_models, failed_slots, file, sha256,
uncompressed_bytes, compressed_bytes, not_included`.

## API / RPC Surface

### `TestGenerationOrchestrator.persist_exported_test(record: dict, *, passage_embedding=None) -> None`
- **Purpose:** save one bundle record through the live save path.
- **Errors:** `ValueError` for an unknown `record_version` or language; anything the save
  path raises (audio, insert) propagates.
- **Side effects:** R2 upload (listening), rows in `tests`, `questions`,
  `generation_review_queue` (judge-flagged questions), `test_skill_ratings`; vocabulary
  extraction and sense creation (LLM calls).

### `scripts/upload_offline_tests.py --bundle DIR [--apply] [--limit N] [--tiers 2,3] [--min-elo E] [--max-elo E] [--provider ...]`
- Dry run by default. Skips: id already in `tests`; topic missing; same `passage_hash` on the
  same topic. With a working `OPENAI_API_KEY` it embeds the passage, stores it and applies
  the live near-dup threshold. Exit 1 if any record failed.

## Key Architectural Decisions
1. **Decision:** bundle text only; audio and vocabulary at upload. See [[decisions/ADR-064-claude-only-offline-test-generation]].
2. **Decision:** one shared `_persist_test` for live and upload.
   - **Rationale:** a second save path would drift (payloads, review queue, ratings).
   - **Alternatives rejected:** an upload script with its own inserts.
3. **Decision:** vary passages with an angle per slot, not a seed.
   - **Rationale:** `claude -p` ignores temperature and seed; the same prompt returns the same passage.

## Security Considerations
The bundle holds generated content only: no user data, no keys. The upload uses the service
role, like every generation script.

## Testing Strategy
`tests/test_offline_test_bundle.py`: slot plan (broad before deep, tier balance, shard
partition), assembly (dedup by slot and passage hash, manifest, xz round trip), upload
selection, record → `_persist_test` field mapping, record-version guard,
`LLM_CALLS_DB_LOG=0` skipping the DB but not the CSV. `tests/test_force_provider_claude_cli.py`
covers `LLM_FORCE_PROVIDER`.

## Bundles

| Bundle | Built | Tests | Notes |
|---|---|---|---|
| `data/offline_tests/ja-2026-11-27/` | 2026-11-27 | see manifest | ja listening, tiers 1–4, headless Claude only, not uploaded |
