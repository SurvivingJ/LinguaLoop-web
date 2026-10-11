# Review 07 - migrations/ (read-only; live DB state NOT visible, so grant/RLS findings are "per repo")

Method: scripted scan of all 237 top-level migrations + 22 archive files for CREATE FUNCTION / SECURITY DEFINER / REVOKE / GRANT / RLS / policies / dynamic SQL, then manual reads of hits. supabase/ is an empty directory; tests/sql has 6 hand-run test scripts; check_prompts.sql is a 2-query SQL-editor scratch file.

### [HIGH] SECURITY DEFINER write/read RPCs taking p_user_id have no REVOKE and no auth check
- Category: security
- Location: migrations/phase13_apply_study_plan_template.sql:18; task716_local_day_boundary.sql:155 (record_session_progress); phase13_compute_weekly_plan_helpers.sql:57,246; phase13_apply_attempt_timing_and_progress.sql:42; word_upload_slot_scheduling.sql:116 (build_daily_session); get_replay_tests.sql:28; get_classifier_drill_session.sql:35,199; counter_drill.sql:100; word_quiz_retake_fallback.sql:7; wire_volatility_and_exclude_attempted.sql:314; task748_get_recommended_tests_vocab_aware.sql:435 (get_recommended_tests)
- Problem: Only the six process_*_submission RPCs (sec_submission_rpcs_auth_gate.sql:437-451) and the TASK-744+ calibration/selection functions get REVOKE FROM PUBLIC/anon. All the above are SECURITY DEFINER, accept an arbitrary p_user_id, never compare it to auth.uid(), and have no REVOKE anywhere in the repo, so Postgres' default EXECUTE-to-PUBLIC (plus Supabase default privileges) applies. Any anon/authenticated PostgREST caller can read any user's daily session/recommendations and write another user's study plan (apply_study_plan_template UPSERTs user_study_plans for p_user_id; record_session_progress and compute_weekly_plan_persist mutate progress).
- Evidence: apply_study_plan_template body (lines 18-57) does `INSERT INTO user_study_plans ... p_user_id ... ON CONFLICT DO UPDATE` with no auth gate; grep of all migrations finds no REVOKE for these names. The same hole was already found and fixed for submissions (sec_submission_rpcs_auth_gate.sql header) - this is the unfinished remainder. Live grants unknown (could have been revoked out-of-band).
- Fix: One migration: REVOKE ALL ... FROM PUBLIC, anon, authenticated + GRANT TO service_role for every p_user_id RPC the Flask backend calls with the service client (or add `p_user_id = auth.uid() OR auth.role()='service_role'` gates).

### [HIGH] Advisory-lock and cron-support RPCs, plus IRT calibration writer, callable by anon
- Category: security
- Location: migrations/study_plan_advisory_lock.sql:26,35; dt_synthesis_advisory_lock.sql:35,44; task510_model_health_advisory_lock.sql:28,37; task517_queue_drain_advisory_lock.sql:39,48; word_upload_sweep_advisory_lock.sql:76,85; add_irt_calibration_metadata.sql:45,74,83 (irt_apply_calibration/irt_try_lock/irt_release_lock); phase13_refresh_practice_time_estimates.sql:27
- Problem: SECURITY DEFINER with no REVOKE. An anonymous caller can take (or release) the global advisory locks, which makes the cron jobs "acquire-or-skip" and silently starve; irt_apply_calibration lets any caller overwrite exercise difficulty/discrimination parameters.
- Evidence: bodies contain no auth check; no REVOKE/GRANT for these names in any migration (the TASK-773 calibration RPCs do `REVOKE ALL ... FROM public`, showing the pattern was known).
- Fix: REVOKE from PUBLIC/anon/authenticated, GRANT to service_role.

### [HIGH] Large set of tables never get ENABLE ROW LEVEL SECURITY anywhere in the repo
- Category: security
- Location: create_all_tables.sql (test_attempts:540, user_tokens:378, token_transactions:658, user_reports:572, user_vocabulary:394, test_skill_ratings:562, user_skill_ratings:406, user_languages:368, tests:430, questions:524, exercises:498, ...); dual_translation_groundwork.sql:53-221 and dt_cards.sql:34,126, dt_error_profile.sql:32 (all dt_* tables incl. dt_submission/dt_grade user text); phase14_llm_calls.sql:22; vocabulary_ladder_schema.sql:22 (word_assets); generation_queue.sql:12
- Problem: Scripted scan finds no `ENABLE ROW LEVEL SECURITY` for these (enable_rls_on_user_owned_tables.sql covers only 7 tables, phase6 covers users + a few dims). User-owned data (attempts, tokens, DT submissions) would be readable/writable by anon key holders if RLS is off live. PLAUSIBLE only: RLS may have been enabled through the Supabase dashboard, which these files cannot show; but the repo is not the source of truth for it.
- Evidence: enable_rls_on_user_owned_tables.sql:1-8 itself documents a prior audit finding of exactly this class.
- Fix: Add an idempotent migration enabling RLS (+ own-data/service-role policies) on every public table, and a test that queries pg_class.relrowsecurity.

### [MEDIUM] Stale process_test_submission overloads still defined in non-archived files (replay can resurrect an unrevoked 7-arg overload)
- Category: redundancy / security
- Location: migrations/listening_lab_rpcs.sql:37 (7-arg, `GRANT ... TO authenticated` at :360), wire_volatility_and_exclude_attempted.sql:29, phase3_rpc_fixes.sql:26, elo_functions.sql:56 (text-signature, GRANT :213), partF_question_attempt_results.sql:100, partG_qar_drop_response_time.sql:45; canonical = sec_submission_rpcs_auth_gate.sql:47 (8-arg)
- Problem: Adding p_furigana_used created a new signature; the drop of the 7-arg/legacy overloads lives only in archive/process_test_submission_v2.sql:15-22. Nothing in sec_submission drops them, and the REVOKE at :437 targets only the 8-arg signature. If the 7-arg overload exists/reappears (listening_lab_rpcs.sql sorts alphabetically after the archive file and says "SUPERSEDED" in a comment but still executes CREATE OR REPLACE), it is SECURITY DEFINER, GRANTed to authenticated and lacks the new gate. Note: memory says partG is canonical; the repo now says sec_submission_rpcs_auth_gate.sql is (it supersedes partG), and archive README agrees.
- Evidence: listening_lab_rpcs.sql:34-45 "SUPERSEDED ... live definition is phase14_test_kfactor_decay.sql" (a file now in archive/ - stale pointer); no DROP FUNCTION process_test_submission outside archive.
- Fix: Add `DROP FUNCTION IF EXISTS` for the 7-arg and text-signature overloads to a live migration; delete the stale function bodies from listening_lab_rpcs/phase3/wire_volatility/elo_functions/partF/partG (move to archive).

### [MEDIUM] No migration ordering mechanism; lexical order replays dropped-module DDL after the DROP
- Category: maintainability / correctness
- Location: migrations/ (names like add_*.sql, phase*.sql, task7xx_*.sql, partF/partG); archive_unused_modules_2026_09_21.sql vs mystery_mode_tables.sql, mystery_prompt_templates.sql, process_mystery_submission.sql, listening_lab_schema.sql, listening_lab_rpcs.sql, conversation_generation_tables.sql, corpus_analysis_tables.sql (partly), scenario_generation_prompts.sql
- Problem: Files have no timestamp/sequence prefix and ~130 of 237 lack BEGIN/COMMIT. A fresh build (alphabetical) would run archive_unused_modules (which DROPs tables/functions and has row-count guards that RAISE) before the files that create those objects, and before create_all_tables. The directory cannot be replayed to rebuild the DB; it is documentation of history only.
- Evidence: archive_unused_modules_2026_09_21.sql:61-133 drops the mystery, listening-lab, conversation, pack tables and RPCs; their creating migrations are still top-level and not archived.
- Fix: Adopt a numeric/timestamp prefix (or Supabase CLI migrations), and move the creator files for dropped modules into archive/ with README rows.

### [MEDIUM] Dead-module migrations remain top-level with permissive policies (USING true, no TO role)
- Category: legacy/dead (and security if ever replayed)
- Location: migrations/mystery_mode_tables.sql:176-212; listening_lab_schema.sql:128-132; calibration_sessions_and_ability.sql:232 (read-only, fine)
- Problem: `FOR INSERT WITH CHECK (true)`, `FOR UPDATE USING (true)`, and `FOR ALL USING (true)` on mystery_skill_ratings are not scoped `TO service_role`, so they apply to anon/authenticated (service_role bypasses RLS anyway, so these are pure holes). The tables were later dropped (archive_unused_modules_2026_09_21.sql:97-133), so live risk is nil; the files are misleading if reused as templates or replayed.
- Evidence: mystery_mode_tables.sql:206 `CREATE POLICY "service_manage_mystery_ratings" ON mystery_skill_ratings FOR ALL USING (true);`
- Fix: Archive the files; never copy the "service_*" USING(true) pattern.

### [MEDIUM] Duplicate canonical definitions across non-archived files (violates migrations/CLAUDE.md rule)
- Category: redundancy
- Location: bkt_apply_decay/bkt_effective_p_known/bkt_update_* in phase5_algorithm_fixes.sql:25-221 vs phase7_bkt_improvements.sql:24-191 (and bkt_vocabulary_tracking.sql:126-137; bkt_apply_decay has 3 vs 4 args = two overloads); ladder_record_attempt phase8_momentum_bands.sql:386 vs phase10_ladder_advancement_demotion.sql:58; get_practice_session phase12_get_practice_session.sql:91 vs get_practice_session_language_scope.sql:27; get_word_quiz_candidates in 3 files (bkt_vocabulary_tracking:339, phase6:229, word_quiz_retake_fallback:7); get_distractors in 3 files (bkt_vocabulary_tracking:409, phase3:503, get_distractors_definition_language_param:16); semantic_distractors in 3 files (calibration_semantic_distractors:227, calibration_distractor_headword_guard:101, shrink_sense_embeddings_halfvec768:125 - latest, keeps guard); build_daily_session phase13_build_daily_session.sql:68 vs word_upload_slot_scheduling.sql:116 (latest; phase13 kept as sole record of week_start_for per README); get_recommended_tests task740_phase5b:23 vs task748:435 (latest; task780 only redefines recommended_tests_ranked); apply_jev_retier task820:15 vs task821:39; test_time_estimate has 1-arg and 2-arg overloads (phase13:32, task715:97,128); update_vocabulary_from_word_test bkt_vocabulary_tracking:264 (4 args) vs phase5:93 (5 args) = leftover overload; get_recommended_test (singular, legacy) phase3:317 vs wire_volatility:314
- Problem: Canonical file is only discoverable by newest-name guesswork; several differ by arg count, i.e. both overloads can be live and callable (cf. the real incident in get_recommended_tests_drop_ambiguous_overload.sql). Canonical picks: process_test_submission -> sec_submission_rpcs_auth_gate.sql; get_recommended_tests -> task748 (3-arg; the task780 file does not redefine it); build_daily_session -> word_upload_slot_scheduling.sql.
- Fix: For each arg-count-changing pair, add explicit DROP FUNCTION IF EXISTS for the old signature and archive the superseded single-purpose file; add a CI check listing functions defined in >1 live file.

### [MEDIUM] Stale/unused functions left live (no code references)
- Category: legacy/dead
- Location: migrations/bkt_vocabulary_tracking.sql (bkt_phase, bkt_phase_thresholds, bkt_status), phase3_rpc_fixes.sql:391,431,475 (can_use_free_test, get_token_balance, update_test_attempts_count; SD, no search_path on :475), phase8_momentum_bands.sql (ladder_get_ring/ladder_ring_families), exercise_scheduling.sql (user_exercise_sessions table and sync_exercise_history), calibration_sessions_and_ability.sql (calibration_next_anchor, superseded by calibration_next_anchors in task772)
- Problem: grep of services/ routes/ scripts/ static/ templates/ tests/ shows zero references (can_use_free_test/get_model_for_task are even in a DROP list in drop_unused_rpcs.sql but are redefined again later, so confirm live state). Tables with zero code refs: dim_block, dim_cefr_levels, dim_library, dim_prog_language, dim_question_template, dim_variable_pool, user_vocabulary, user_pack_selections_new, calibration_distractor_cache_misses (maybe only via RPC), dim_practice_modes.
- Evidence: scripted word-boundary grep over code roots; PLAUSIBLE where only referenced from other SQL.
- Fix: Confirm against live pg_proc/pg_class and add a drop migration.

### [LOW] Leftover backup tables in public schema with no RLS
- Category: legacy/dead / security
- Location: migrations/task819_jev_tier_assignment.sql:33 (tests_tier_backup_20260926), task821_tier_calibration.sql (tests_tier_backup_20260927_v1)
- Problem: Snapshot tables in the PostgREST-exposed schema, no RLS statement, no code references. Low sensitivity (test ids/tiers) but exposed and permanent.
- Fix: Drop after retention window or ENABLE RLS with no policies.

### [LOW] Non-idempotent migrations (fail on re-run)
- Category: correctness
- Location: 40 CREATE POLICY without matching DROP POLICY IF EXISTS (e.g. exercise_scheduling.sql, dim_character_components.sql:69, listening_lab_schema.sql, mystery_mode_tables.sql, task741_pack_key_words_bridge.sql:52); 20 CREATE INDEX without IF NOT EXISTS (add_sense_levels_and_source.sql, replace_cefr_with_age_tiers.sql, test_generation_tables.sql, mystery/listening); user_word_watchlist_schema.sql:23 CREATE TABLE without IF NOT EXISTS
- Problem: Re-running errors at the first duplicate. Mixed with idempotent files, so "safe to re-apply" cannot be assumed. Also several data-fix files (cleanup_corrupt_pinyin_attempts.sql, delete_confirmed_kana_fragment_vocab.sql, cleanup_cross_language_test_skill_ratings.sql, dedupe_categories_and_topics.sql, task732_ja_skill_rating_elo_reseed.sql, phase13_wipe_user_state_for_launch.sql) are one-off data mutations living beside schema; phase13_wipe_user_state_for_launch.sql is destructive if replayed.
- Fix: Move one-off data fixes to a data-fixes/ folder (or archive); require IF NOT EXISTS / DROP POLICY IF EXISTS in new files.

### [LOW] Submission RPC bodies still carry NULL-permissive auth gate (defence in depth)
- Category: security
- Location: process_dictation_submission.sql, process_pinyin_submission.sql, process_pitch_accent_submission.sql, process_classifier_drill_submission.sql (stated in sec_submission_rpcs_auth_gate.sql:24-25); several lack SET search_path (process_classifier_drill_submission.sql:14, process_pinyin_submission.sql:12, process_pitch_accent_submission.sql:19; also get_classifier_drill_session.sql:35, resolve_plan_timezone task716:64)
- Problem: Safe only while the REVOKE (sec_submission:437-451) holds; a CREATE OR REPLACE never changes ACL, but a DROP+CREATE would reopen it. Missing search_path on SECURITY DEFINER functions permits search-path hijack if a caller can create objects in a schema ahead of public (low risk on Supabase).
- Fix: Add `IF auth.role()<>'service_role' AND p_user_id IS DISTINCT FROM auth.uid()` and `SET search_path = public, pg_temp` to each.

### [LOW] Stale GRANT TO authenticated lines in superseded files
- Category: maintainability
- Location: elo_functions.sql:213-215, listening_lab_rpcs.sql:360, process_*_submission.sql (GRANT ... TO authenticated, e.g. process_pinyin_submission.sql:297)
- Problem: Reading a single file suggests authenticated may call submission RPCs; the contradicting REVOKE is in a later file. Replaying in a different order can re-grant.
- Fix: Annotate/remove after consolidating.

### [LOW] Stale cross-references and scratch files
- Category: maintainability
- Location: listening_lab_rpcs.sql:34 (points at archive/phase14_test_kfactor_decay.sql), check_prompts.sql (SQL-editor scratch, hardcoded prompt names), supabase/ (empty dir), migrations/archive/ (22 files, README table is accurate and consistent with CLAUDE.md rules)
- Problem: Dead pointers; empty supabase/ means no CLI migration config.
- Fix: Delete check_prompts.sql or move to scripts/; fix the pointer.

### Not found / checked clean
- Dynamic SQL: only dt_rewrite_history_v6.sql (format with %1$s from catalog column lists; REVOKEd from PUBLIC/anon/authenticated at :520-529) and fix_daily_test_loads_user_id_fk.sql:38 (format %I). No injection risk.
- Hot-RPC index coverage was not exhaustively verified (needs live EXPLAIN); not reported.
