---
title: "ADR-064: Claude-only test generation and offline test bundles"
status: accepted
date: 2026-11-27
---

# ADR-064: Claude-only test generation and offline test bundles

## Context
On 2026-11-27 the owner asked for Japanese tests to be generated with headless Claude only,
using neither the OpenRouter key nor the Anthropic API. The first run used `--provider claude-cli`,
which moved only the writer. The judges pin `provider='openrouter'`, answer entailment and
passage tiering go to jev (OpenRouter's Decisions API), and phrase detection calls a fixed
OpenRouter client directly. Those calls exhausted the key and stopped the run (HTTP 402).

The owner then asked for 500 more Japanese tests, stored compressed in the repository to be
loaded later. The database was at 492 MB of the 500 MB Free cap.

## Decision
1. `LLM_FORCE_PROVIDER=claude_cli` routes every model call of a run to headless Claude:
   `call_llm`, `get_client(provider)`, both judges, entailment (LLM backend), passage tiering,
   and phrase detection. `call_jev` refuses.
2. Under it, passages are tiered by Claude against jev's six tier descriptions. The tier is
   stored with `age_tier_calibration = 'claude-uncalibrated'` (the owner chose this over
   keeping jev or storing the target tier).
3. Offline runs write no database rows: `LLM_CALLS_DB_LOG=0` covers `llm_calls` and
   `generation_stage_timings`, and `dry_run` with an export sink replaces the save.
4. Bundles are `tests.jsonl.xz` plus `manifest.json` under `data/offline_tests/<lang>-<date>/`.
   They hold everything except audio and vocabulary linking, which are made at upload
   through the same `_persist_test` path a live run uses (owner's choice over committing MP3s).
5. Passages are varied with a writing angle per (topic, tier) slot, because `claude -p` has no
   sampling control.

## Consequences
- A generation run can be fully subscription-billed and leave the database untouched until upload.
- Claude judging Claude's own questions is a weaker check than an independent judge model;
  judge pass rates under claude-cli are not comparable with the Gemini/jev baselines.
- Seeded ELOs of Claude-tiered tests are uncalibrated. In the 2026-11-27 runs Claude rated
  passages higher than jev (a tier-3 target came back T5), so tier-2 targets landed near ELO 1260.
- Uploading 500 tests needs database headroom first (roughly 45 KB per test with vocabulary).

## Alternatives Considered
- **Keep jev for tiering only:** calibrated, but needs OpenRouter credit, which the owner ruled out.
- **Store the target tier unchecked:** violates ADR-029; the pilots showed passages land a tier off.
- **Commit MP3s:** ~0.5 MB each, ~300 MB of binary history for 500 tests.
- **Write straight to the database:** no headroom (492 / 500 MB) and the owner wanted to add them later.
