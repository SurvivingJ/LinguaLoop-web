# Review 08: scripts/, sandbox/, Corpuses/, prompts/, archive/, verify_prompts.py

Method: AST import/symbol/kwarg checker over all 131 scripts + sandbox + Corpuses (no execution); RPC/table names cross-checked against migrations/; reference counts across services/routes/tests/.claude/wiki.

### [HIGH] Corpuses/ingest_corpus.py is broken at import and targets dropped tables
- Category: legacy/dead
- Location: Corpuses/ingest_corpus.py:40,73
- Problem: Imports services.corpus.pack_service.CollocationPackService; that module no longer exists. The collocation_packs / pack_* tables were dropped in migrations/archive_unused_modules_2026_09_21.sql.
- Evidence: services/corpus has no pack_service.py; CollocationPackService appears only in this file; DROP TABLE public.collocation_packs / pack_collocations / pack_key_words in the migration.
- Fix: Archive, or strip the pack step if plain corpus ingestion is still wanted.

### [HIGH] scripts/apply_task734_en_prompt_fixes.py references deleted services
- Category: legacy/dead
- Location: scripts/apply_task734_en_prompt_fixes.py:169,358-362
- Problem: MYSTERY_ORCH points to services/mystery_generation/orchestrator.py (package removed with the 2026-09-21 module archive); the verify step opens it unconditionally -> FileNotFoundError. Prompts it writes (conversation_persona_design, mystery_plot) belong to dropped modules.
- Evidence: that path does not exist; open(MYSTERY_ORCH) at ~:359; zero inbound references. Comments in rewrite_prompt_native.py:16 and sweep_prompt_metalanguage.py:13 reference the same removed persona/scenario modules.
- Fix: Archive.

### [HIGH] build_classifier_dictionary.py wipes then inserts non-atomically, destructive by default
- Category: correctness
- Location: scripts/build_classifier_dictionary.py:556-560 (flag at 591)
- Problem: Default run (no --dry-run) deletes all zh rows in dim_classifier_noun_pairs and dim_classifiers via service-role, then inserts, as separate PostgREST calls with no transaction. A failed insert leaves the tables empty. Memory notes this also discards cedict-imported data needing re-import.
- Evidence: two delete().eq('language_id', ZH) calls then insert(); only opt-out is --dry-run (unsafe default).
- Fix: Require --apply, or do it in one SQL function/transaction; snapshot rows first.

### [MEDIUM] upload_tests_to_supabase.py + batch_generate_to_json.py + base_generator.py: legacy chain, stale schema, non-idempotent
- Category: legacy/dead
- Location: scripts/upload_tests_to_supabase.py:60-98; scripts/batch_generate_to_json.py:2; scripts/base_generator.py
- Problem: batch_generate_to_json.py self-declares "Superseded by run_test_generation_cli.py" and is the only importer of scripts/base_generator.py. The uploader writes a `language` text column to `tests`, whereas schema uses language_id (even the 2026-03 snapshot lacks `language`) -> likely fails (PLAUSIBLE). Plain insert per test then per question: re-run hits UNIQUE slug; mid-run failure leaves tests without questions.
- Evidence: archive/db_schema_live_2026-03-18.sql:520-532 tests columns; row dict at upload script :60-78; no references to the script anywhere.
- Fix: Archive all three plus root artifacts generated_tests_20251209_225642.*, batch_errors_20251209_225642.json.

### [MEDIUM] Silent truncation at PostgREST row cap in backfills
- Category: correctness
- Location: scripts/rederive_tiers.py:51 (.limit(2000)); scripts/backfill_zipf_scores.py:66-74; scripts/backfill_test_skill_ratings.py:59-76; scripts/backfill_topic_tiers.py:65,68 (.limit(10000))
- Problem: Selects without .range() pagination are capped by the project max-rows (default 1000), so limit(2000/10000) is a no-op and the script processes a partial set while reporting success. Same defect family as the fixed backfill_vocab bug. PLAUSIBLE: depends on Supabase max_rows setting. Other backfills (backfill_senses, backfill_vocab, rebuild_token_maps, backfill_gloss_definitions...) do paginate.
- Evidence: grep counts for range/page/offset per backfill script (0 for the four above).
- Fix: Shared fetch_all(query, page=1000) helper.

### [MEDIUM] Write-by-default scripts with inverted dry-run safety
- Category: correctness
- Location: scripts/backfill_token_maps.py (no flag at all); scripts/upload_tests_to_supabase.py; scripts/run_generation_batch.py:333; scripts/validate_effectiveness_view.py:202; scripts/fix_quarantined_senses.py:262; scripts/cleanup_classifier_data.py:240,266
- Problem: apply_*/fix_*/cleanup_*/build_classifier_* write live with the service-role key unless --dry-run is passed. backfill_token_maps.py and upload_tests_to_supabase.py have no dry-run/apply flag at all. Mitigations: apply_task733/735 etc. support --dry-run/--verify and verify-after-write; verify_calibration_state and calibration_estimator_bias use synthetic uuid users and clean up in finally; run_generation_batch deletes old exercises only after new rows exist (comment :332).
- Evidence: grep -L "dry.run|--apply|--commit" over apply_/fix_/backfill_/upload_/relink_/rebuild_/rederive_ returns only those two.
- Fix: Shared argparse helper with --apply (default dry-run).

### [MEDIUM] Boilerplate duplicated across ~120 scripts
- Category: redundancy
- Location: scripts/*.py (sys.path.insert in 119, argparse 116, get_supabase_admin/SupabaseFactory 105, load_dotenv() 81)
- Problem: Each script re-implements path hack + dotenv + admin client + paging + dry-run flag. Corpuses/ingest_corpus.py and upload_tests_to_supabase.py use raw create_client + manual env checks, bypassing services.supabase_factory (the only 2 uses of create_client). sandbox/live_probe/*.py hand-roll .env parsing and raw OpenRouter HTTP.
- Evidence: substring counts across scripts/*.py.
- Fix: scripts/_common.py (bootstrap(), admin_client(), fetch_all(), apply_flag()); routes/admin_local.py already imports scripts as a package, so sys.path hacks can go.

### [MEDIUM] Duplicate / finished experiment harnesses
- Category: legacy/dead
- Location: scripts/measure_judge_flag_rate.py, measure_entailment_ab.py, measure_selection_quality.py, shadow_entailment_window.py, calibrate_entailment_jev.py, smoke_entailment_jev.py, smoke_entailment_production_path.py, smoke_judge_prompt.py, run_exercise_gen_eval.py (75 KB), score_exercise_gen_run.py (50 KB), simulate_preteach_variants.py; tier set calibrate_tier_jev / fit_tier_thresholds / rederive_tiers / retier_tests_with_jev
- Problem: Overlapping entailment/judge/tier harnesses for experiments memory records as concluded (judge v3/v7, jev live 2026-09-27, selection simulation, preteach).
- Evidence: several have no inbound reference (table below).
- Fix: Move to scripts/archive/; keep one parameterised judge harness.

### [LOW] Task-numbered one-offs with zero inbound references
- Category: legacy/dead
- Location: apply_ja_prose_furigana_fix, apply_prompt_brand_mention_removal, backfill_dt_cloze_l1_context, backfill_pinyin_payload_punctuation_fix, backfill_vocab_reading, fix_ja_judge_brace_escaping, smoke_task733_prompts, smoke_test_generation_routing, verify_distribution, render_existing_assets, run_topic_import, generation_timing_report, import_character_components, json_to_csv, build_exercise_gen_reference_set
- Problem: No refs from code/tests/skills/wiki/settings. smoke_task733_prompts.py relies on dim_grammar_patterns (dropped in archive_unused_modules_2026_09_21.sql; its own comment at :14 says "empty") so only the stubbed path works.
- Fix: Archive after owner confirmation.

### [LOW] prompts/*.txt likely orphaned
- Category: legacy/dead
- Location: prompts/question_type1-3.txt, question_generation.txt, transcript_generation.txt
- Problem: Only string-referenced by services/ai_service.py, scripts/batch_generate_to_json.py and services/test_generation/schemas.py; live prompts come from the prompt_templates table. PLAUSIBLE (ai_service callers not fully traced).
- Fix: Verify then remove.

### [LOW] Tracked repo-root debris, possible credential file
- Category: security
- Location: twilio.txt, bash.exe.stackdump, batch_errors_20251209_225642.json, generated_tests_20251209_225642.json (all git-tracked); also untracked-or-not C:tmppytest_out.txt, grep.exe.stackdump
- Problem: twilio.txt (24 bytes, tracked) looks like a credential fragment (contents deliberately not read in full; PLAUSIBLE). Stackdumps and generated artifacts are noise.
- Fix: Inspect twilio.txt, rotate if live, git rm the rest, ignore *.stackdump.

### [LOW] Real test UUID in docstring
- Category: maintainability
- Location: scripts/upload_test_senses.py:35
- Problem: Prod test_id baked into usage example. No keys/JWTs/emails/DB URLs found in scripts, sandbox, Corpuses (greps for eyJ..., sk-..., sk-or-, supabase.co, @gmail, postgres:// all clean); .env is gitignored; service-role key is only read from env/Config and never printed (error messages print the variable name only); only subprocess use is git show in verify_mining_split.py:49 (list args, no shell).

### [LOW] sandbox/exercise-lab weight and duplication
- Category: maintainability
- Location: sandbox/exercise-lab/db/lab.sqlite (122 MB, gitignored), prototypes/fat_seed/*, live_probe/*.py
- Problem: prototypes/fat_seed overlaps scripts/fat_seed_runner.py; live_probe hand-rolls OpenRouter calls instead of services.llm_service; sandbox imports production modules (services.vocabulary_ladder.*, config) so it can break on refactor (currently all resolve).
- Fix: Mark experiment-only; archive live_probe once ADR-028 is closed.

### [LOW] v_sense_family_coverage view missing from migrations
- Category: maintainability
- Location: scripts/dedupe_legacy_vocab_exercises.py:66 (also services/vocabulary_ladder/queue_drain.py:65)
- Problem: Only table/view name used by scripts with no CREATE in migrations/ or supabase/ (live-DB-only DDL). Every .rpc() name and every other .table() name resolves to a migration.
- Fix: Add view DDL to migrations/.

### Health check (positive)
AST check over all scripts/sandbox: 0 syntax errors; 0 missing symbols in `from services|utils|config import X`; 0 invalid kwargs or excess positionals on calls to imported functions. Only import failures: the two BROKEN items above.

## Operational references
routes/admin_local.py imports run_generation_batch, backfill_vocab, backfill_token_maps, backfill_question_sense_ids, backfill_test_skill_ratings. services/tests import backfill_sense_embeddings, build_dt_gold_v6, dt_gold_seed_helper, dt_nightly_synthesis, rebuild_token_maps, upload_glosses. .claude/settings.json allow-lists exercise_stage_runner, export_exercise_worklist, upload_exercises; .claude/skills reference the batch-*/fat-seed/sense-linking scripts. No Procfile/GitHub workflow runs any script (Procfile = gunicorn; only frontend-tests.yml exists).

## Classification

| Class | Count | Files |
|---|---|---|
| KEEP | ~45 | run_generation_batch, backfill_vocab, backfill_token_maps, backfill_question_sense_ids, backfill_test_skill_ratings, backfill_sense_embeddings, backfill_senses, rebuild_token_maps, upload_glosses/senses/exercises/test_senses, export_*_worklist, export_tests_missing_senses, exercise_stage_runner, fat_seed_runner, sense_linking_common, sense_candidates, dt_nightly_synthesis, dt_gold_seed_helper, build_dt_gold_v6, build_dt_passages, run_content_build, run_test_generation(_cli), run_topic_generation, build_ja_mora_trie, build_calibration_distractor_cache, retier_tests_with_jev, batch_generate_furigana/pinyin/pitch_accent, provider_arg, run_ladder_from_existing, backfill_pronunciations/semantic_class/zipf_scores/topic_tiers/hant_mirrors, verify_prompts.py |
| ARCHIVE | ~38 | apply_* (9), author/stage/report/task721_blocks, audit_* (4), smoke_* (8), fix_ja_*, backfill_dt_cloze_l1_context, backfill_pinyin_payload_punctuation_fix, backfill_vocab_reading, dedupe_legacy_vocab_exercises, relink_deferred_vocab, rewrite_prompt_native, rewrite_vocab_context_prompt, sweep_prompt_metalanguage, simulate_preteach_variants, measure_selection_quality, calibration_estimator_bias, calibration_also_correct_report, generation_timing_report, verify_distribution, verify_mining_split, json_to_csv, render_existing_assets, run_topic_import, import_character_components, build_exercise_gen_reference_set |
| BROKEN | 3 (+1 partial) | Corpuses/ingest_corpus.py; scripts/apply_task734_en_prompt_fixes.py; scripts/upload_tests_to_supabase.py (PLAUSIBLE); smoke_task733_prompts.py partial |
| DUPLICATE | ~12 | base_generator.py + batch_generate_to_json.py (superseded); measure_judge_flag_rate / measure_entailment_ab / shadow_entailment_window; calibrate_tier_jev / fit_tier_thresholds / rederive_tiers / retier_tests_with_jev; smoke_entailment_jev / smoke_entailment_production_path; sandbox fat_seed vs fat_seed_runner; prompts/*.txt vs prompt_templates |
