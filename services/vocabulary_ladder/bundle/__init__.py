# services/vocabulary_ladder/bundle/__init__.py
"""ADR-028 Phase 2: call-collapse ("bundle") generation and judging.

TASK-814/815/816 — collapses the ~10-14 separate LLM calls/sense/variant that
`VocabAssetPipeline._generate_for_sense_impl` currently fans out
(`prompt2_exercises`, `prompt3_transforms`, the L4/L8 split generators, the
typed generators, and the 5-7 render-time judges) into one bundle-generation
call and one bundle-judge call per sense, covering BOTH variants A and B —
per ADR-028 Decision §4's ~4-5-call/sense target.

This package is standalone and NOT wired into the live pipeline yet. It is
built against the DRAFT prompt rows in
`migrations/exercise_gen_bundle_prompts_draft.sql` (`is_active = false`) and
gated end-to-end by `VOCAB_LADDER_BUNDLE_MODE` (see `flags.py`), which
defaults to `"off"` — importing this package has zero effect on production
behaviour until both the migration is applied with `is_active = true` AND the
wiring patch in
`wiki/tasklist/exercise-gen-cost.phase2-wiring.patch` is applied to
`asset_pipeline.py` / `exercise_renderer.py`.

Modules
-------
``flags``     — the `VOCAB_LADDER_BUNDLE_MODE` env var reader.
``mapping``   — pure functions mapping bundle LLM output onto the EXISTING
                word_assets asset shapes, by calling the EXISTING remap/
                validate functions unchanged.
``generator`` — `BundleGenerator`: one `vocab_bundle_generation` call per
                sense, with per-asset-family fallback to the existing
                per-generator calls on partial validation failure.
``judge``     — `BundleJudge`: one `ladder_bundle_judge` call per sense
                (zh/ja only — no bundle judge template exists for en yet),
                with per-axis fallback to the existing per-judge calls on
                partial/malformed output. Fail-closed: a total bundle-judge
                failure falls all the way back to calling every existing
                judge directly, never to a silent accept.
"""
