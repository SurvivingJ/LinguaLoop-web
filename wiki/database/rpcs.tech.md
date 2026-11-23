---
title: "RPC & Functions — Technical Specification"
type: api-tech
status: complete
prose_page: ../api/rpcs.md
last_updated: 2026-11-23
dependencies:
  - "All tables in schema.tech.md"
  - "migrations/phase8_momentum_bands.sql — vocabulary ladder RPCs"
  - "migrations/phase9_get_exercise_session.sql — daily-session RPC"
  - "migrations/add_irt_calibration_metadata.sql — IRT persistence + lock RPCs"
  - "migrations/phase11_irt_selection.sql — IRT-aware get_exercise_session"
  - "migrations/restore_get_distractors_auth_check.sql — re-adds auth.role() guard on get_distractors (2026-05-15)"
  - "migrations/add_test_attempts_idempotency_index.sql — partial index for process_test_submission idempotency lookup (2026-05-15)"
  - "migrations/drop_unused_rpcs.sql — drops 4 dead RPCs (2026-05-15; three of them are live, see Live Function Reference)"
  - "migrations/PENDING-2026-11-23.md — function changes written but not applied"
open_questions:
  - "Calls whose function name is built at run time (for example a name held in a variable) may be missing from the 'called by the application' count; the grep covered `.rpc(` literals, the `call_bundle` / `optional_rpc` helpers, the drill session config and `services/calibration_placement.py`."
  - "process_classifier_drill_submission and process_test_submission still return SQLERRM in their error reply; the 2026-11-23 change note said the four non-test submission RPCs send a generic reply with the message logged only: true live for pinyin, pitch accent and dictation, not for the classifier drill. Decide whether to make the classifier drill match."
  - "grant_daily_free_tokens is called by routes/users.py and services/auth_service.py but exists neither live nor in any migration; the balance route and signup welcome grant cannot work as written. Owner decision needed (create the function, or change the callers)."
  - "can_use_free_test, get_model_for_task and get_prompt_template were documented as dropped on 2026-05-15 but are live; get_model_for_task fails when called (it reads the dropped table language_model_config). Drop them, or confirm they are kept on purpose."
  - "Argument default values are shown as '=d' in the live reference; the value is in the canonical migration file, not repeated here."
breaking_change_risk: high
---

# RPC & Functions — Technical Specification

> **Historical note (2026-05-21) — Study Plans + Practice Engine merger; every RPC listed here is now live (see the Live Function Reference below).** Full signatures and bodies are spec'd in [[features/practice-engine.tech]] and [[features/study-plans.tech]]; this note enumerates what's coming so the catalog stays current.
>
> **New RPCs:**
> - `get_practice_session(p_user_id uuid, p_language_id smallint, p_mode text='auto', p_target_minutes smallint=15, p_user_theta numeric=NULL) RETURNS jsonb` — unified Practice surface. Mode dispatch (`acquisition`|`maintenance`|`auto`), candidate-pool composition, unified-score ranking, mid-session fall-through. Errors: `language_not_active`, `invalid_mode`, `target_minutes_out_of_range`. See [[features/practice-engine.tech#rpc-get_practice_session]].
> - `practice_unified_score(p_a, p_b, p_theta, p_p_known, p_due_date, p_stability, p_today, p_ladder_priority, p_alpha, p_beta, p_gamma, p_delta) RETURNS numeric` — `IMMUTABLE` SQL helper. See [[algorithms/practice-unified-score.tech]].
> - `ladder_compute_priority(p_current_ring int, p_word_state text, p_family_confidence jsonb, p_review_due_at timestamptz, p_last_exercised_family text) RETURNS numeric` — `IMMUTABLE` standalone form of the get_ladder_session priority formula. Used by get_practice_session and (potential) future surfaces.
> - `apply_study_plan_template(p_user_id uuid, p_language_id smallint, p_template_id smallint) RETURNS user_study_plans` — onboarding hook (UPSERT).
> - `compute_weekly_plan_load_signals(p_user_id, p_language_id, p_week_start) RETURNS jsonb` — Tier B Python adapter pulls every needed signal in one round-trip.
> - `compute_weekly_plan_persist(p_user_id, p_language_id, p_week_start, p_computed jsonb) RETURNS jsonb` — atomic UPSERT of Python-computed Tier B output; preserves `completed_counts`/`practice_completed_*_min`/`session_progress_log`.
> - `build_daily_session(p_user_id uuid, p_language_id smallint, p_date date=CURRENT_DATE) RETURNS jsonb` — Tier C resolver in PL/pgSQL; greedy + spacing-penalty fill; writes `daily_test_loads` + `daily_session_targets`. Returns `code=E_NOPLAN` or `E_NOWEEK` jsonb on missing prerequisites. **TASK-702:** hydrates budgeted slots from `get_recommended_tests` (`slot_type='new'`) then tops up shortfalls from `get_replay_tests` (`slot_type='replay'`); returns per-skill `requested_counts` / `hydrated_counts` (primary fill only) / `replay_counts`; `used_minutes` reflects placed slots (+ `budgeted_minutes` for the raw budget). Canonical: `task702_build_daily_session.sql`.
> - `record_session_progress(p_user_id, p_language_id, p_attempt_id uuid, p_kind text, p_skill text, p_delta_count int DEFAULT 0, p_delta_minutes int DEFAULT 0, p_delta_seconds int DEFAULT 0) RETURNS boolean` — idempotent counter update keyed by `attempt_id`. Practice accrues `p_delta_seconds` into `practice_completed_*_sec`; the `*_min` columns are re-derived as `ROUND(sec/60)` (TASK-701, `phase18_practice_time_seconds.sql`). Test path uses `p_delta_count`/`p_delta_minutes`.
> - `apply_attempt_timing_and_progress(p_attempt_id uuid, p_started_at timestamptz, p_finished_at timestamptz) RETURNS jsonb` — post-submission hook called by `routes/tests.py` to persist `started_at`/`duration_ms` on `test_attempts` and invoke `record_session_progress(..., 'test', ...)` atomically. NULL-timestamp-tolerant.
> - `refresh_practice_time_estimates() RETURNS jsonb` — nightly job that refreshes `dim_exercise_types.expected_seconds_p50` (from `exercise_attempts.time_taken_ms`) and `dim_test_types.expected_minutes_p50` (from `test_attempts.duration_ms`) from observed P50s over the last 30 days, requiring ≥30 samples per type.
> - `test_time_estimate(p_skill text) RETURNS numeric` — `STABLE` helper. Prefers `dim_test_types.expected_minutes_p50` when set; else falls back to a hard-coded seed matching `Config.TEST_TYPE_MINUTES`.
> - `week_start_for(p_date date) RETURNS date` — `IMMUTABLE` helper returning the Monday of `p_date`'s ISO week.
>
> **Tier B implementation note:** The full `compute_weekly_plan` function lives in **Python** (`services/study_plan_service.py::StudyPlanService.compute_weekly_plan`) — see ADR-010 + R3.2 (deterministic Beta sampling). The two SQL helpers above (`_load_signals`, `_persist`) are the database surface; the Python orchestrator runs the bandit + value math between them.
>
> **Submission RPCs (`process_test_submission` + variants): unchanged.** Body-of-RPC modification was deferred in favor of the `apply_attempt_timing_and_progress` hook called by the route handler after the submission returns. Timing has no influence on ELO calculation so isolating it as a hook avoids duplicating ~250 lines × 4 RPCs.
>
> **Deprecation wrappers — REMOVED 2026-07-14 (TASK-220):**
> - `get_exercise_session`, `get_ladder_session` — **dropped** by `migrations/phase17_drop_deprecation_wrappers.sql` (now in `migrations/archive/`). The drop did not take effect live; ADR-049 dropped them on 2026-11-17 and they were checked absent on 2026-11-19 (TASK-1031). They had been thin wrappers delegating to `get_practice_session('auto', size·0.6 min)` and `get_practice_session('acquisition', count·0.5 min)`. `/api/exercises/session` and `/api/vocab-dojo/session` now 302 to `/api/practice/session`; the standalone pages were retired. The full-spec sections for both RPCs below are retained as historical record only.
>
> **Cron:**
> - New job `study_plan_weekly_recompute` — Sundays at 23:00 UTC; iterates `user_study_plans`, calls `compute_weekly_plan` per row under an advisory lock (same pattern as `irt_calibration_nightly`).
> - New job `exercise_time_estimate_refresh` — 04:05 UTC daily; refreshes `dim_exercise_types.expected_seconds_p50` and `dim_test_types.expected_minutes_p50` from observed P50s (≥ 30 samples required).

## Live Function Reference (verified against the live database, 2026-11-23)

This section is the authoritative, current reference. Every row was generated from `pg_proc` of project `kpfqrjtfxmujzolwsvdq` (schema `public`, functions owned by the application, i.e. not extension members) on 2026-11-23; the per-function sections further down are the older DDL-level notes and are kept for history, with their status corrected in place where it was wrong. Where a per-function section below and this section disagree, this section wins.

**Totals (live):** 214 functions: 85 SECURITY DEFINER, 129 SECURITY INVOKER; 4 names are overloaded (`bkt_apply_decay`, `bkt_effective_p_known`, `update_vocabulary_from_word_test`, `test_time_estimate`). 94 distinct names are called by the application (directly by name from `routes/`, `services/`, `scripts/`, or through the helpers `call_bundle`, `optional_rpc`, the drill session config in `services/drill_service.py`, and `services/calibration_placement.py`), 72 more are called only by those functions, and 44 are neither (94 + 72 + 44 = 210 names; 214 rows because of the 4 overloads) (triggers, helpers for the app-less admin tasks, history). Counts of "called by the app" come from a grep of `.rpc(` and dynamic names in the repo at HEAD, so a name built at run time that the grep could not see may be missing (see `open_questions`).

**Who may execute (`has_function_privilege`, all 214 checked):** `service_role` can execute every function; `anon` and `authenticated` can execute only `is_admin(uuid)` and `is_moderator(uuid)` (RLS helpers; they answer only for the caller's own JWT subject). Everything else is service-role only, so the Flask backend must use the service key to call them (the per-user JWT cannot). Default privileges on new functions still grant EXECUTE to `anon`/`authenticated` (see `pg_default_acl`), so every new function needs an explicit REVOKE in its migration.

**Security column legend:** `D` = SECURITY DEFINER with `search_path = public, pg_temp` (every DEFINER function pins a search path); `I` = SECURITY INVOKER. Exceptions to the standard search path: `search_path = public` for `apply_calibration_to_skill_ratings`, `get_counter_drill_session`, `get_recommended_tests`, `get_replay_tests`, `irt_apply_calibration`, `irt_release_lock`, `irt_try_lock`, the eight `pg_try_advisory_lock_for_*`/`pg_advisory_unlock_for_*` functions, `recommended_tests_ranked`, `selection_vocab_ability`, `trg_blocklist_retire_exercises`, and (INVOKER) `is_sense_quarantined`, `trg_exercises_sense_quarantine`, `trg_generation_queue_sense_quarantine`; `public, extensions, pg_temp` for `pronunciation_distractors`; `public, pg_temp` plus `plan_cache_mode = force_custom_plan` for `semantic_distractors`; `public, pg_temp` plus `statement_timeout = 600s` for `calibration_cache_distractors_chunk`. INVOKER functions without a letter suffix have no pinned path (62 functions), those marked `I*` have `search_path = public, pg_temp`.

**Reads / writes** are a static scan of each function body (`INSERT INTO`, `UPDATE`, `DELETE FROM` = write; `FROM`, `JOIN` = read); a table reached only through a called function is not listed. **File** is the newest non-archive file in `migrations/` that defines the function; for the six functions with a pending replacement (see "Pending function changes" below) the file that matches the live body is named, not the pending file. Argument defaults are written `=d` (the value is in the file). `†` marks files the page could not tie to the live body byte for byte (the file is the latest definition by git history, not proven identical).

### Application contract that changed on 2026-11-23

**`record_exercise_attempt` is the only path that records a practice attempt.** `services/practice/attempt_recording.py` makes one `rpc('record_exercise_attempt')` call per answer; the old Python per-step path (separate inserts and updates for the attempt, counters, BKT, ladder, study time, plan progress) and the `PRACTICE_ATTEMPT_RPC_ENABLED` flag are gone (`tests/test_practice_attempt_recording.py::test_the_retired_env_flag_is_ignored` asserts the env variable is ignored).

- Signature: `record_exercise_attempt(p_user_id uuid, p_exercise_id uuid, p_is_correct boolean, p_user_response jsonb=d, p_time_taken_ms integer=d, p_language_id smallint=d, p_credit_seconds integer=d, p_plan_kind text=d, p_is_tail boolean=d, p_exercise_context text=d) RETURNS jsonb`. SECURITY INVOKER, `search_path = public, pg_temp`, VOLATILE, EXECUTE service_role only. File `migrations/record_exercise_attempt.sql`.
- One transaction, in this order: (1) read the exercise's type, sense and language (returns `{"error":"exercise_not_found"}` if missing); (2) `pg_advisory_xact_lock(hashtextextended(user_id || ':' || exercise_id, 0))`, which serialises concurrent answers to the same exercise by the same learner so the first-attempt decision cannot race; (3) `is_first_attempt` = no earlier `exercise_attempts` row for (user, exercise); (4) insert the `exercise_attempts` row; (5) bump `exercises.attempt_count` and `correct_count`; (6) complete open `prestudy_followups` for the sense; (7) on a first attempt with a sense: `update_vocabulary_from_word_test(..., exercise_type)` (BKT), then `bkt_infer_from_frequency` when p_known crosses 0.90 upward, then store `p_known_before/after` on the attempt row; (8) `ladder_apply_progress` (context limited to `standard`, `gate`, `stress_test`); (9) `credit_study_time(... 'practice' ...)` when `p_credit_seconds > 0`; (10) `record_session_progress` when `p_plan_kind` is `practice_acq` or `practice_maint`; (11) read back the learner's `user_flashcards` row. Steps 6 to 10 each run in their own exception block: a failure is appended to the returned `warnings` array (`step`, `error`) and does not roll back the attempt.
- Returns `jsonb`: `attempt_id`, `is_first_attempt`, `exercise_type`, `sense_id`, `language_id`, `bkt_update`, `ladder`, `flashcard` (id, stability, difficulty, due_date, last_review, reps, lapses, state), `warnings`.
- **Still in Python after the RPC returns:** the FSRS scheduling write (`_apply_fsrs_review` updates `user_flashcards` using `services/vocabulary/fsrs.py`, working on the `flashcard` row the RPC returned), and, when FSRS reports a lapse, the BKT lapse penalty (`rpc('bkt_apply_lapse_penalty')`), plus the new-word-drill restart and the response shaping. These are not in the transaction: an FSRS or lapse failure is logged and does not undo the attempt.

### The six functions changed live on 2026-11-23 (what the live bodies do)

Read from `pg_proc.prosrc` on 2026-11-23. Common to the five submission RPCs (`process_test_submission`, `process_pinyin_submission`, `process_pitch_accent_submission`, `process_dictation_submission`, `process_classifier_drill_submission`; all SECURITY DEFINER, VOLATILE, service_role only):

- **Caller check.** First statement: if `p_user_id IS NULL`, or (`auth.uid()` is distinct from `p_user_id` and `auth.role()` is not `service_role`), return `{"success": false, "error_code": "unauthorized"}` (RETURN, not RAISE, so the catch-all handler cannot flatten it). A missing user is therefore rejected, where the old `p_user_id != auth.uid()` test passed when `auth.uid()` was NULL (see `migrations/sec_submission_rpcs_auth_gate.sql`).
- **Error reply, per function (these differ):** `process_pinyin_submission`, `process_pitch_accent_submission`, `process_dictation_submission`: the catch-all handler logs `RAISE WARNING '<fn> failed: % (SQLSTATE=%)', SQLERRM, SQLSTATE` and returns only `{"success": false, "error_code": "submission_failed", "sqlstate": <code>}`: the Postgres message goes to the log, not to the client. `process_test_submission` and `process_classifier_drill_submission`: the handler returns `{"success": false, "error": SQLERRM, "error_detail": SQLSTATE}`, i.e. the Postgres message is still in the reply (no log line). The change description given to this page said all four non-test functions send a generic reply; the live classifier body does not, see `open_questions`.
- **Idempotency:** if `p_idempotency_key` matches an existing attempt of the user, the stored result is returned with `cached: true` and nothing is written.
- Writes: `test_attempts`, `user_skill_ratings` (get-or-create, then update), `test_skill_ratings`, `user_languages` (`ON CONFLICT (user_id, language_id)` upsert). The rating rows are still created with a plain `INSERT` after a failed lookup; the `ON CONFLICT` writers are pending (see below).

`process_test_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_was_free_test boolean=d, p_idempotency_key uuid=d, p_furigana_used boolean=d, p_prestudied boolean=d) RETURNS jsonb` (file `migrations/process_test_submission_set_based_grading.sql`):
- Rejects an empty `p_responses` (`RAISE EXCEPTION 'No responses provided'`, caught by the handler above).
- **Row locks:** `SELECT ... FROM user_skill_ratings ... FOR UPDATE` on the learner's rating row (two submissions by one learner for the same language and test type now run one after the other; a learner's very first submission has no row to lock) and `FOR UPDATE` on the `test_skill_ratings` row (concurrent first attempts by different learners no longer overwrite each other's test-ELO change).
- **Set-based grading in one query:** a `resp` CTE de-duplicates the payload (`DISTINCT ON question_id`, first entry wins), a `graded` CTE joins every `questions` row of the test (numbered by `created_at`) to it with a LEFT JOIN (unanswered counts as `''` and is wrong), and a single `SELECT COUNT(*), COUNT(*) FILTER (WHERE is_correct), jsonb_agg(...)` yields total, score and the per-question result array. No temp table, no per-question lookup.
- ELO: first attempt moves both ratings (user K = 32, x0.5 furigana dampener when `p_furigana_used`, x0.5 when `p_prestudied`; test K = 48 below 20 attempts, 24 below 50, else 16, x0.5 when prestudied; clamped 400..3000); a repeat moves ratings only in today's retry slot (`daily_test_loads`, reduced-volatility factor, once per day), otherwise ELO is unchanged. `elo_reduction_factor` records the prestudy or retry factor. Per-question outcomes are written to `question_attempt_results` inside a nested block whose failure only logs a warning.
- Returns `success`, `attempt_id`, `attempt_number`, `is_first_attempt`, the ELO before/after/change pairs, `elo_reduction_factor`, `tokens_cost`, `score`, `total_questions`, `percentage`, `question_results`, `message`. (The older section below lacks `p_furigana_used` and `p_prestudied`.)

`get_quiz_distractors(p_sense_id integer, p_language_id smallint, p_count integer=d, p_definition_language_id smallint=d) RETURNS TABLE(definition text, lemma text)` (SECURITY DEFINER, VOLATILE, file `migrations/get_quiz_distractors_sample_ids_first.sql`): rejects any caller whose `auth.role()` is not `authenticated` or `service_role` (42501). **Ids first:** a `cand` CTE (MATERIALIZED) selects only ids for every eligible sense (same language, definition language = `p_definition_language_id` or the word language, rank-1 `standard`-level definition that is not null, a different headword) together with a `random()` value and a same-part-of-speech flag (the asked word's class, computed once from the distinct tags so `pos_class` is not called per row); `picked` keeps one row per headword (its smallest random number), same class first, capped at `LEAST(p_count, 10)`; only then are definitions and lemmas fetched for the picked senses. The old version sampled over rows that carried the definition text.

### Functions removed or never created

- **Absent live (checked 2026-11-23):** `is_org_member`, `get_org_role` (organizations dropped 2026-09-22), `get_recommended_mysteries`, `process_mystery_submission` (mystery mode dropped 2026-09-22), `get_packs_with_user_selection` (packs dropped 2026-09-22), `get_ladder_session`, `get_exercise_session` (dropped 2026-11-17, ADR-049). Their per-function sections below are history only.
- **Documented as dropped but live:** `can_use_free_test(uuid)`, `get_model_for_task(smallint)`, `get_prompt_template(varchar, integer)`: the 2026-05-15 drop (`migrations/drop_unused_rpcs.sql`) did not take effect for these three (or was reverted); they exist, are INVOKER, service-role only, and have no caller in the application (the Python method `get_prompt_template` in `services/vocabulary/*` is unrelated).
- **`grant_daily_free_tokens` does not exist** (not in the live database, not in any migration; only the grant migrations `migrations/security_function_grants_group_a.sql` and `_group_b.sql` mention it, to say so). The application calls it in `routes/users.py` (`GET` token balance, line 37) and `services/auth_service.py` (welcome tokens on signup, line 219). Both calls fail at runtime against the live database; `routes/users.py` then reads `users.tokens` and `users.last_free_token_date`, columns that also do not exist on live `users`. Needs an owner decision (see follow-ups in the batch report and `open_questions`).
- **Never created (called but absent):** `pg_try_advisory_lock_for_word_upload_sweep`, `pg_advisory_unlock_for_word_upload_sweep` (called by `services/word_list_import/sweep_cron.py`; pending, see below) and `exercise_content_sweep` (the name is only a directory in `scripts/sweep_exercise_content.py`; not an RPC).

### Functions the application calls (94 names)

Sec: D/I as in the legend. "File" paths are in `migrations/`.

| Function (arguments) | Returns | Sec | Purpose | Reads / Writes | File |
|---|---|---|---|---|---|
| `apply_attempt_timing_and_progress(p_attempt_id uuid, p_started_at timestamptz=d, p_finished_at timestamptz=d)` | jsonb | D | Post-submit hook: stores `started_at`/`duration_ms` on the attempt and credits weekly-plan progress | R `dim_test_types`, `test_attempts` / W `test_attempts` | `phase13_apply_attempt_timing_and_progress` |
| `apply_calibration_to_skill_ratings(p_user_id uuid, p_language_id smallint)` | jsonb | D | Only path by which placement moves `user_skill_ratings` (seed or correct ELO from ability) | R `user_calibration_state`, `test_attempts`, `user_skill_ratings`, `test_skill_ratings`, `tests`, `dim_test_types` / W `user_skill_ratings`, `user_skill_rating_adjustments` | `task747_apply_calibration_to_skill_ratings` |
| `apply_jev_retier(p_rows jsonb)` | integer | I | Applies a JEV tier re-assignment to `tests` | R `dim_complexity_tiers` / W `tests` | `task821_tier_calibration` |
| `apply_study_plan_template(p_user_id uuid, p_language_id smallint, p_template_id smallint)` | user_study_plans | D | Idempotent upsert of a plan from a template (copies daily minutes, keeps user edits) | R `dim_study_plan_templates` / W `user_study_plans` | `phase13_apply_study_plan_template` |
| `bkt_apply_lapse_penalty(p_user_id uuid, p_sense_id integer)` | void | I | Lowers p_known after an FSRS lapse | W `user_vocabulary_knowledge` | `phase7_bkt_improvements` |
| `bkt_contextual_inference(p_user_id uuid, p_language_id smallint, p_contextual_sense_ids integer[], p_score_ratio numeric)` | integer | I | Moves p_known of senses seen in a test by the score ratio | R/W `user_vocabulary_knowledge` | `phase7_bkt_improvements` |
| `bkt_infer_from_frequency(p_user_id uuid, p_language_id smallint, p_known_sense_id integer, p_new_p_known numeric)` | integer | I | Raises p_known of more frequent words when a rarer word is known | R/W `user_vocabulary_knowledge` | `phase7_bkt_improvements` |
| `build_daily_session(p_user_id uuid, p_language_id smallint, p_date date=d)` | jsonb | D | Builds and stores the day's test slots (daily load) | R plan, tests, attempts, sentence refs, DT tables / W `daily_test_loads`, `daily_test_load_items`, `user_word_watchlist` | `word_upload_slot_scheduling` |
| `calibration_ability(p_session_id uuid, p_min_band_n integer=d)` | jsonb | D | Pooled ability estimate of a session | R `calibration_responses` | `calibration_sessions_and_ability` |
| `calibration_build_items(p_session_id uuid, p_user_id uuid, p_word_language_id smallint, p_definition_language_id smallint, p_mode text=d, p_count integer=d, p_max_fill integer=d)` | jsonb | D | Builds up to `p_count` placement items (anchors, cached distractors) in one round trip | W `calibration_responses`, `calibration_response_options`, `calibration_sessions` | `calibration_distractor_cache_packed` |
| `calibration_cache_distractors_chunk(p_word_language_id smallint, p_definition_language_id smallint, p_mode text=d, p_batch integer=d)` | TABLE(anchors_processed, anchors_filled, anchors_short) | D | Fills the distractor cache for a batch of untried anchors | R pool, cache, misses / W `calibration_distractor_cache_misses` (+ cache via helper) | `task773b_calibration_distractor_cache_misses` |
| `calibration_discard_unanswered(p_session_id uuid, p_user_id uuid)` | integer | D | Deletes served-but-unanswered items and fixes `items_served` | W `calibration_responses`, `calibration_response_options`, `calibration_sessions` | `task770_calibration_build_items` |
| `calibration_distractor_cache_coverage()` | TABLE | D | Cached vs total anchors per language pair and mode | R pool, cache | `task773_calibration_distractor_cache` |
| `calibration_placement_answer(p_user_id uuid, p_session_id uuid, p_response_id bigint, p_position smallint, p_latency_ms integer, p_next_band smallint, p_draws jsonb)` | jsonb | D | Grades one placement answer and returns the next item in one round trip | R/W `calibration_responses`, `calibration_sessions` | `calibration_placement_rpcs` |
| `calibration_placement_close(p_user_id uuid, p_session_id uuid, p_reason text)` | jsonb | D | Closes a placement session and builds its result | R/W `calibration_responses`, `calibration_sessions` | `calibration_placement_rpcs` |
| `calibration_placement_close_stale(p_user_id uuid, p_older_than interval=d)` | uuid[] | D | Closes the learner's abandoned placement sessions (nightly job) | R/W same | `calibration_placement_rpcs` |
| `calibration_placement_meaning_parts(p_anchor_sense_id integer, p_word_language_id smallint, p_definition_language_id smallint, p_lemma text, p_key text, OUT status text, OUT sense_ids integer[], OUT texts text[])` | record | I* | Option set for a meaning item | (helpers only) | `calibration_placement_rpcs` |
| `calibration_placement_next_item(p_user_id uuid, p_session_id uuid, p_band smallint, p_exclude_days integer=d)` | jsonb | D | Picks and inserts the next placement item | R `calibration_responses`, `calibration_sessions` | `calibration_placement_rpcs` |
| `calibration_placement_reading_ready(p_vocab_id integer, p_word_language_id smallint, p_lemma text)` | boolean | I* | Whether a reading item can be built for the word | none | `calibration_placement_rpcs` |
| `calibration_placement_ready_counts(p_word_language_id smallint, p_definition_language_id smallint)` | jsonb | I* | Counts of placement-ready words per band | R pool, blocklist, `dim_word_senses` | `calibration_placement_rpcs` |
| `calibration_placement_reveal_reading(p_vocab_id integer, p_word_language_id smallint)` | text | I* | The word's reading, shown after a miss | R `dim_word_senses` | `calibration_placement_rpcs` |
| `calibration_record_answer(p_response_id bigint, p_user_id uuid, p_session_id uuid, p_position integer=d, p_latency_ms integer=d)` | jsonb | D | Grades one (non-placement) calibration answer, returns running counts | R/W `calibration_responses`, `calibration_response_options`, `calibration_sessions` | `task769_calibration_record_answer` |
| `calibration_refresh_anchor_pool(p_word_language_id smallint=d)` | integer | D | Rebuilds `calibration_anchor_pool` | R/W `calibration_anchor_pool`; R vocab, senses | `calibration_pool_refresh_language_and_katakana` |
| `calibration_zh_tone_variants(p_pronunciation text, p_vocab_id integer)` | text[] | I* | Valid tone variants of a Chinese reading | R `calibration_zh_char_readings`, `calibration_zh_tone_inventory` | `calibration_zh_tones` |
| `calibration_zipf_to_elo(p_ability_zipf numeric)` | integer | I* | Maps ability (Zipf) to the age-tier ELO ladder | R `dim_complexity_tiers` | `calibration_user_state_and_zipf_to_elo` |
| `compute_weekly_plan_load_signals(p_user_id uuid, p_language_id smallint, p_week_start date)` | jsonb | D | Inputs for the weekly plan in one call | R attempts, ratings, vocab, flashcards, ladder, `weekly_plan_states` | `phase13_compute_weekly_plan_helpers` |
| `compute_weekly_plan_persist(p_user_id uuid, p_language_id smallint, p_week_start date, p_computed jsonb)` | jsonb | D | Atomic upsert of the computed week (keeps progress counters) | W `weekly_plan_states` | `session_module_exclusions` |
| `credit_study_time(p_user_id uuid, p_language_id smallint, p_kind text, p_seconds integer, p_source_table text, p_source_id text)` | boolean | D | Credits measured seconds to the learner-local week once per source row (ADR-035) | W `study_time_ledger` | `prestudy_workflow` |
| `dt_next_inputs(p_user_id uuid, p_l2 integer, p_l1 integer)` | jsonb | I* | Read bundle for the dual-translation `/next` route | R `dt_grade`, `dt_passage`, `dt_submission`, `test_*`, ratings, `users` | `dt_next_inputs` |
| `exercise_content_begin(p_sense_id integer)` | jsonb | I* | Step 1 of the Storage content write: current version and ids (ADR-049) | R `exercises` | `exercise_content_storage` |
| `exercise_content_commit(p_sense_id integer, p_expected_version integer, p_expected_ids uuid[], p_new_version integer, p_delete_ids uuid[]=d, p_insert_rows jsonb=d, p_update_contents jsonb=d)` | jsonb | I* | Compare-and-swap commit of one sense's exercise rows | R/W `exercises` | `exercise_content_drop_column` |
| `exercise_content_live_versions(p_language_id integer)` | jsonb | I* | `{sense_id: [versions]}` of active rows, for the sweep | R `exercises` | `exercise_content_storage` |
| `get_active_languages()` | TABLE | D | Active languages | R `dim_languages` | `phase6_security_hardening` |
| `get_classifier_drill_session(p_user_id uuid, p_language_id smallint, p_count integer=d)` | TABLE | D | Classifier drill items (v1, fallback) | R classifier tables, senses | `get_classifier_drill_session` |
| `get_classifier_drill_session_v2(p_user_id uuid, p_language_id smallint, p_count integer=d)` | TABLE | D | Classifier drill items by mastery level | R classifier tables, `user_classifier_mastery`, vocab | `task998_classifier_drill_levels` |
| `get_counter_drill_session(p_user_id uuid, p_language_id smallint, p_count integer=d)` | TABLE | D | Counter drill items (ja) | R counter tables, senses | `counter_drill` |
| `get_distractors(p_sense_id integer, p_language_id smallint, p_count integer=d, p_definition_language_id smallint=d)` | TABLE | D | Exercise distractor definitions | R vocab, senses | `phase3_rpc_fixes` |
| `get_next_category()` | TABLE | D | Next topic category to generate for | R `categories`, `dim_status` | `phase6_security_hardening` |
| `get_practice_session(p_user_id uuid, p_language_id smallint, p_mode text=d, p_target_minutes smallint=d, p_user_theta numeric=d, p_include_content boolean=d)` | jsonb | I* | Unified Practice session builder (mode, time budget, score) | R exercises, history, flashcards, knowledge, ladder, modes | `exercise_content_drop_column` |
| `get_quiz_distractors(...)` | TABLE | D | See "The six functions changed" | R vocab, senses | `get_quiz_distractors_sample_ids_first` |
| `get_recommended_test(p_user_id uuid, p_language_id integer)` | SETOF tests | D | Single recommended test (older route) | R tests, ratings, attempts | `wire_volatility_and_exclude_attempted` |
| `get_recommended_tests(p_user_id uuid, p_language_id smallint, p_topic_recency_days smallint=d)` | TABLE | D | Ranked recommended tests | R tests, ratings, `selection_tuning`, tiers | `dictation_cap_cjk_word_count` |
| `get_review_ahead_items(p_user_id uuid, p_language_id smallint, p_limit integer=d, p_exclude_recent_minutes integer=d, p_exclude_sense_ids integer[]=d, p_include_content boolean=d)` | jsonb | I* | Review-ahead items for extra rounds | R exercises, attempts, flashcards, knowledge | `exercise_content_drop_column` |
| `get_token_balance(p_user_id uuid)` | integer | D | Token balance (purchased + bonus) | R `user_tokens` | `phase3_rpc_fixes` |
| `get_weekly_study_seconds(p_user_id uuid, p_language_id smallint, p_week_start date)` | jsonb | D | Ledger seconds per kind for a week | R `study_time_ledger` | `prestudy_workflow` |
| `get_word_quiz_candidates(p_user_id uuid, p_sense_ids integer[], p_language_id smallint, p_max_words integer=d)` | TABLE | D | Words for the post-test word quiz | R vocab, senses, knowledge | `archive/word_quiz_retake_fallback` (live; archived) |
| `intro_commit_word(p_user_id uuid, p_sense_id integer, p_stage smallint, p_attempts jsonb, p_update jsonb)` | boolean | I* | Commits a new-word-drill stage (attempts + ladder row) | R/W `user_word_ladder`, W `exercise_attempts` | `intro_commit_word` |
| `irt_apply_calibration(p_exercise_id uuid, p_discrimination numeric, p_difficulty numeric, p_se_difficulty numeric, p_n_attempts integer)` | void | D | Stores IRT parameters on an exercise | W `exercises` | `add_irt_calibration_metadata` |
| `irt_release_lock()`, `irt_try_lock()` | boolean | D | Advisory lock around the nightly IRT job | none | `add_irt_calibration_metadata` |
| `knowledge_active_pairs(p_since timestamptz)` | jsonb | I* | (learner, language) pairs active since a time, for the nightly snapshot job | R calibration, knowledge | `knowledge_report_foundation` |
| `knowledge_calibration_inputs(p_user_id uuid, p_language_id smallint, p_as_of timestamptz=d, p_window_days integer=d, p_definition_language_id smallint=d, p_session_id uuid=d)` | jsonb | I* | Estimator inputs from placement and calibration | R calibration, pool, blocklist, knowledge | `knowledge_calibration_inputs` |
| `knowledge_frame_bands()` | jsonb | I* | Frame sizes per language and Zipf band | R pool, blocklist, senses | `knowledge_report_foundation` |
| `knowledge_report_summary(p_user_id uuid, p_language_id smallint, p_as_of timestamptz=d, p_window_days integer=d, p_cal_since timestamptz[]=d)` | jsonb | I* | Knowledge Report summary aggregates | R calibration, vocab, attempts, knowledge, watchlist, word quiz | `knowledge_report_summary` |
| `knowledge_report_words(p_user_id uuid, p_language_id smallint, p_definition_language_id smallint, p_filters jsonb=d, p_sort text=d, p_cursor jsonb=d, p_limit integer=d, p_as_of timestamptz=d)` | jsonb | I* | One keyset page of the report's word table | R vocab, senses, exercises, ladder, watchlist, flashcards, knowledge | `knowledge_report_words` |
| `knowledge_snapshots_prune(p_keep_daily_days integer=d)` | integer | I* | Deletes old snapshots (retention) | R/W `user_knowledge_snapshots` | `knowledge_report_foundation` |
| `ladder_graduate(p_user_id uuid, p_sense_id integer, p_stress_test_score real, p_language_id smallint)` | jsonb | I | Graduates a word to review and creates its flashcard | W `user_flashcards`, `user_word_ladder` | `phase8_momentum_bands` |
| `ladder_new_word_state(p_user_id uuid, p_language_id smallint, p_day_start timestamptz)` | jsonb | D | Unstarted / started-today words for the new-word quota | R vocab, senses, attempts, exercises, ladder | `new_word_drill` |
| `ladder_pass_gate(p_user_id uuid, p_sense_id integer, p_gate_name text)` | jsonb | I | Marks a ladder gate passed | R/W `user_word_ladder` | `phase8_momentum_bands` |
| `ladder_record_attempt(p_user_id uuid, p_sense_id integer, p_exercise_id uuid, p_is_correct boolean, p_is_first_attempt boolean, p_time_taken_ms integer=d, p_language_id smallint=d, p_exercise_type text=d, p_ladder_level integer=d, p_exercise_context text=d)` | jsonb | I | Ladder attempt write (family BKT, momentum bands); used by the ladder service, not by Practice | R/W attempts, flashcards, knowledge, ladder | `phase8_momentum_bands` |
| `match_test_passages_by_topic_tier(p_topic_id uuid, p_tier_id smallint, query_embedding vector, match_threshold double precision=d, match_count integer=d)` | TABLE | D | Nearest existing passages for dedup | R `tests` | `task740_phase5_question_passage_dedup` |
| `match_topics(query_category integer, query_embedding vector, match_threshold double precision=d, match_count integer=d)`, `match_topics_global(query_embedding vector, match_threshold double precision=d, match_count integer=d)` | TABLE | D | Topic similarity search | R `topics` | `phase6_security_hardening`, `task740_collapse_difficulty_to_tier_schema` |
| `pg_try_advisory_lock_for_dt_synthesis()` / `pg_advisory_unlock_for_dt_synthesis()` and the same pairs for `model_health`, `queue_drain`, `study_plan` | boolean | D | Session-level advisory locks so the nightly jobs run once (eight functions) | none | `dt_synthesis_advisory_lock`, `task510_model_health_advisory_lock`, `task517_queue_drain_advisory_lock`, `study_plan_advisory_lock` |
| `prestudy_plan_inputs(p_user_id uuid, p_language_id smallint, p_test_ids uuid[])` | jsonb | I* | Prestudy inputs bundle (called via `call_bundle`) | R tests, knowledge, ability | `latency_2026_11_session_merges` |
| `new_word_state_inputs(p_user_id uuid, p_language_id smallint, p_date date, p_day_start timestamptz, p_with_governor boolean)` | jsonb | I* | New-word state bundle (called via `call_bundle`) | R ladder, plan, ... | `latency_2026_11_session_merges` |
| `process_classifier_drill_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_correct_items integer, p_total_items integer, p_was_free_test boolean=d, p_idempotency_key uuid=d)` | jsonb | D | Records a classifier-drill session and moves ELO on the first attempt | see "changed" section | `process_classifier_drill_submission` |
| `process_dictation_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_word_correct integer, p_word_total integer, p_replay_count smallint, p_diff_payload jsonb, p_was_free_test boolean=d, p_idempotency_key uuid=d)` | jsonb | D | Records a dictation attempt (replay penalty, retry slot) | R also `daily_test_loads` | `process_dictation_submission` |
| `process_pinyin_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_correct_chars integer, p_total_chars integer, p_was_free_test boolean=d, p_idempotency_key uuid=d)` | jsonb | D | Records a pinyin attempt | see "changed" section | `process_pinyin_submission` |
| `process_pitch_accent_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_correct_units integer, p_total_units integer, p_was_free_test boolean=d, p_idempotency_key uuid=d, p_furigana_used boolean=d)` | jsonb | D | Records a pitch-accent attempt | see "changed" section | `process_pitch_accent_submission` |
| `process_test_submission(...)` | jsonb | D | See "The six functions changed" | W `question_attempt_results` too | `process_test_submission_set_based_grading` |
| `recommended_tests_ranked(p_user_id uuid, p_language_id smallint, p_topic_recency_days smallint, p_vocab_weight numeric, p_as_of timestamptz=d)` | TABLE | D | Every eligible test with its score decomposition (vocab-aware ranker) | R tests, ratings, vocab, `selection_tuning` | `dictation_cap_cjk_word_count` |
| `record_exercise_attempt(...)` | jsonb | I* | See "Application contract that changed" | W attempts, `exercises`, `prestudy_followups` | `record_exercise_attempt` |
| `record_session_progress(p_user_id uuid, p_language_id smallint, p_attempt_id uuid, p_kind text, p_skill text, p_delta_count integer=d, p_delta_minutes integer=d, p_delta_seconds integer=d, p_sense_id bigint=d, p_is_tail boolean=d)` | boolean | D | Idempotently credits one completion to the current week | R/W `weekly_plan_states` | `task716_local_day_boundary` |
| `refresh_new_word_minutes()` | jsonb | D | Nightly estimate of minutes per new word | W `dim_languages` | `new_word_minutes_estimate` |
| `refresh_practice_time_estimates()` | jsonb | D | Nightly p50 seconds/minutes per exercise and test type | W `dim_exercise_types`, `dim_test_types` | `phase13_refresh_practice_time_estimates` |
| `review_governor_state(p_user_id uuid, p_language_id smallint, p_date date)` | jsonb | D | Review backlog and governor level (normal, reduced, paused) | R plan, flashcards, ladder, vocab | `new_word_drill_governor` |
| `selection_vocab_ability(p_user_id uuid, p_language_id smallint, p_as_of timestamptz=d)` | TABLE | D | Ability (Zipf) behind the untested-sense prior | R `user_calibration_state`, knowledge, vocab | `task748_get_recommended_tests_vocab_aware` |
| `semantic_distractors(p_sense_id integer, p_word_language_id smallint, p_definition_language_id smallint, p_count integer=d, p_cos_min real=d, p_cos_max real=d, p_freq_band real=d, p_definition_level text=d, p_pool integer=d, p_exclude_stem_variants boolean=d)` | TABLE | D | Embedding-neighbour distractors inside a cosine band | R `dim_distractor_bands`, vocab, senses | `sense_vectors_native_standard_512` |
| `sense_similarity_to_lemmas(p_sense_id integer, p_language_id smallint, p_lemmas text[])` | TABLE | D | Similarity of a sense to a list of lemmas | R vocab, senses | `sense_vectors_native_standard_512` |
| `set_new_words_shortfall(p_user_id uuid, p_language_id smallint, p_date date, p_shortfall integer, p_checked_e integer=d)` | boolean | D | Records how many new words the day could not fill | W `daily_test_loads` | `session_module_exclusions_build_daily_session` |
| `tests_containing_sense(p_sense_id integer, p_language_id integer)` | TABLE | I | Tests whose transcript includes a sense | R `tests`, `dim_languages` | `exercise_generation_schema` |
| `update_classifier_mastery(p_user_id uuid, p_classifier_id smallint, p_is_correct boolean)` | jsonb | D | Updates classifier mastery and promotes after 5 answers at a level | R/W `user_classifier_mastery` | `task998_classifier_drill_levels` |
| `update_vocabulary_from_placement_batch(p_user_id uuid, p_language_id smallint, p_items jsonb)` | TABLE | I* | Writes placement evidence to BKT (own evidence kind) | R/W `user_vocabulary_knowledge` | `baseline_update_vocabulary_from_placement_batch` |
| `update_vocabulary_from_test(p_user_id uuid, p_language_id smallint, p_question_results jsonb)` | TABLE | I | BKT update from a comprehension test's per-question results | R `questions`; W `user_vocabulary_knowledge` | `bkt_vocabulary_tracking` |
| `update_vocabulary_from_word_test(p_user_id uuid, p_sense_id integer, p_is_correct boolean, p_language_id smallint, p_exercise_type text=d)` | TABLE | I | BKT update from one word-test or exercise answer (5-argument form; the 4-argument overload is pending removal) | R/W `user_vocabulary_knowledge` | `phase5_algorithm_fixes` |
| `update_vocabulary_from_word_tests_batch(p_user_id uuid, p_language_id smallint, p_results jsonb)` | TABLE | I | Batch form of the word-test BKT update | R/W `user_vocabulary_knowledge` | `bkt_word_test_batch` |

### Functions called only by other functions (72)

Same legend. Not callable usefully from the client (service-role only).

| Function (arguments) | Returns | Sec | Purpose | Called by / reads, writes | File |
|---|---|---|---|---|---|
| `bkt_apply_decay(p_known numeric, p_last_evidence_at timestamptz, p_half_life_days numeric=d)` | numeric | I | Time decay of p_known, half-life form | pure | `phase7_bkt_improvements` |
| `bkt_apply_decay(p_known numeric, p_last_evidence_at timestamptz, p_stability real=d, p_evidence_count integer=d)` | numeric | I | Decay using FSRS stability when known (the form documented below) | pure | `phase7_bkt_improvements` |
| `bkt_effective_p_known(p_known numeric, p_last_evidence_at timestamptz)` | numeric | I | p_known after decay, default parameters | pure | `phase7_bkt_improvements` |
| `bkt_effective_p_known(p_known numeric, p_last_evidence_at timestamptz, p_stability real=d, p_evidence_count integer=d)` | numeric | I | p_known after decay with stability (the form documented below) | pure | `phase7_bkt_improvements` |
| `bkt_status(p_known numeric)` | text | I | Status label from p_known | pure | `bkt_vocabulary_tracking` |
| `bkt_update(p_current numeric, p_correct boolean, p_slip numeric=d, p_guess numeric=d)`, `bkt_update_comprehension(p_current, p_correct)`, `bkt_update_exercise(p_current, p_correct, p_exercise_type text)`, `bkt_update_word_test(p_current, p_correct)` | numeric | I | One Bayesian update step with per-source slip/guess | pure | `bkt_vocabulary_tracking`, `phase7_bkt_improvements` |
| `calculate_elo_rating(current_rating integer, opposing_rating integer, actual_score numeric, k_factor integer=d, volatility_multiplier numeric=d)`, `calculate_volatility_multiplier(attempts integer, last_date date=d, base_volatility numeric=d)` | integer / numeric | I | ELO and volatility helpers (used by the dictation RPC) | pure | `elo_functions` |
| `calibration_band_midpoint(p_band smallint)`, `calibration_zipf_band(p_zipf real)` | real / smallint | I | Zipf band helpers | pure | `calibration_sessions_and_ability` |
| `calibration_cached_options(p_mode text, p_anchor_sense_id integer)` | TABLE | I* | Cached foils for an anchor, ranked | R cache, vocab, senses | `calibration_distractor_cache_packed` |
| `calibration_display_pronunciation(p_pronunciation text, p_language_id smallint)`, `calibration_normalise_pronunciation(p_pronunciation text, p_language_id smallint)`, `calibration_syllable_count(p_normalised text, p_language_id smallint)` | text / integer | I / I* | Pronunciation display, comparison form, syllable or mora count | pure | `calibration_pronunciation_mode`, `calibration_zh_normaliser_fix` |
| `calibration_fill_distractor_cache(p_anchor_sense_id integer, p_word_language_id smallint, p_definition_language_id smallint, p_mode text=d)` | integer | D | Fills the cache for one anchor | R/W `calibration_distractor_cache` | `calibration_distractor_cache_packed` |
| `calibration_next_anchors(p_session_id uuid, p_word_language_id smallint, p_definition_language_id smallint, p_mode text=d, p_count integer=d)` | TABLE | D | Unserved anchors for a session, round-robin by band | R pool, blocklist, responses | `task772_calibration_anchor_pool` |
| `calibration_placement_*` helpers (19): `band_has_word`, `build_meaning`, `build_reading`, `build_recheck`, `candidates`, `draw`, `insert_item`, `item_payload`, `kana_pattern`, `mora_skeleton`, `option_texts`, `own_readings`, `reading_exempt`, `reading_foil_counts`, `reading_key`, `reading_parts`, `reveal`, `strip_definition`, `tallies`, `toneless`, `unit`, `units`, `well_formed_reading` | jsonb / text / TABLE / boolean | I* (`build_meaning`, `build_reading`, `build_recheck`, `draw`, `insert_item` are VOLATILE) | Item building, readiness, tallies for placement; `build_meaning` and `insert_item` write `calibration_responses` (and `insert_item` `calibration_sessions`) | called by `calibration_placement_next_item`, `_answer`, `_close` | `calibration_placement_rpcs` |
| `calibration_zh_mark_syllable(p_base text, p_tone integer)`, `calibration_zh_parse_pinyin(p_pronunciation text)` | text / TABLE | I* | Pinyin tone-mark helpers | pure | `calibration_zh_tones` |
| `definition_head_glosses(p_definition text)`, `shared_prefix_len(a text, b text)` | text[] / integer | I | Distractor headword guard helpers | pure | `calibration_distractor_headword_guard`, `calibration_semantic_distractors` |
| `dictation_max_words(p_difficulty integer)`, `transcript_word_count(p_text text)` | integer | I | Dictation transcript length cap | R `dim_complexity_tiers` | `task715_test_time_estimate_tiered`, `dictation_cap_cjk_word_count` |
| `fsrs_schedule_review(p_stability real, p_difficulty real, p_last_review date, p_reps integer, p_lapses integer, p_state text, p_rating integer, p_review_date date=d)` | jsonb | I | SQL FSRS step (the Python scheduler is the one in use) | pure | `phase8_momentum_bands` |
| `get_replay_tests(p_user_id uuid, p_language_id smallint, p_test_type text, p_min_age_days integer=d, p_exclude uuid[]=d, p_limit integer=d)` | TABLE | D | Tests the learner may replay | R tests, ratings, attempts | `get_replay_tests` |
| `get_test_token_cost(p_user_id uuid)` | integer | D | Token cost of a test for the user's tier | R `dim_subscription_tiers`, `users` | `baseline_get_test_token_cost` |
| `irt_compute_user_theta(p_user_id uuid, p_language_id smallint)` | numeric | I | Ability from exercise history | R `user_exercise_history` | `add_irt_calibration_metadata` |
| `is_admin(p_user_id uuid)`, `is_moderator(p_user_id uuid)` | boolean | D | RLS helpers; the only functions `anon` and `authenticated` may execute | R `users`, `dim_subscription_tiers` | `security_function_auth_checks` |
| `ladder_apply_progress(p_user_id uuid, p_sense_id integer, p_exercise_id uuid, p_is_correct boolean, p_is_first_attempt boolean, p_exercise_context text=d)` | jsonb | I* | Ladder progress write used by `record_exercise_attempt` | R `exercises`; R/W `user_word_ladder` | `ladder_apply_progress` |
| `ladder_compute_p_known(p_fc jsonb)`, `ladder_compute_priority(...)`, `ladder_get_family(p_level integer)`, `ladder_ring_families(p_ring integer, p_active_levels integer[])` | numeric / text / text[] | I | Ladder helpers | pure | `phase8_momentum_bands`, `phase12_get_practice_session` |
| `max_unlocked_tier(p_user_id uuid, p_language_id smallint)` | smallint | D | Highest classifier tier the learner has unlocked | R `dim_classifiers`, `user_classifier_mastery` | `baseline_max_unlocked_tier` |
| `new_word_minutes(p_language_id smallint)`, `new_words_effective(p_quota integer, p_level text)`, `new_words_for_day(p_new_words_per_day integer, p_weight numeric)` | numeric / integer | I | New-word budget arithmetic | R `dim_languages` (first) | `session_module_exclusions`, `review_governor` |
| `plan_local_date(p_user_id uuid, p_language_id smallint, p_at timestamptz=d)`, `plan_local_day_start(p_user_id uuid, p_language_id smallint)`, `resolve_plan_timezone(p_tz text)`, `week_start_for(p_date date)` | date / timestamptz / text | D / I | Learner-local day boundary (ADR-022) | R `user_study_plans`, `tz_names` | `task716_local_day_boundary`, `new_words_completed_accrual`, `latency_2026_11_db`, `phase13_build_daily_session` |
| `pos_class(p_pos text)` | text | I* | Part-of-speech class used for same-class distractors | pure | `get_quiz_distractors` |
| `practice_unified_score(p_a numeric, p_b numeric, p_theta numeric, p_p_known numeric, p_due_date date, p_stability real, p_today date, p_ladder_priority numeric, p_alpha numeric, p_beta numeric, p_gamma numeric, p_delta numeric)` | numeric | I | Practice ranking score | pure | `phase12_practice_unified_score` |
| `pronunciation_distractors(p_sense_id integer, p_word_language_id smallint, p_count integer=d, p_max_distance integer=d, p_max_ratio real=d)` | TABLE | D | Reading distractors by edit distance | R vocab, senses | `pronunciation_distractors_ja_kana_pattern` |
| `review_governor_level(p_backlog_min numeric, p_threshold_min numeric)`, `review_item_seconds(p_user_id uuid, p_language_id smallint)` | text / numeric | I / D | Governor level and per-item review time | R attempts, vocab | `review_governor` |
| `sense_embedding(p_sense_id integer)` | halfvec | I* | A sense's 512-d vector | R `dim_word_senses` | `sense_vectors_native_standard_512` |
| `test_time_estimate(p_skill text)`, `test_time_estimate(p_skill text, p_difficulty integer)` | numeric | I | Expected minutes per test slot | R `dim_test_types` | `task715_test_time_estimate_tiered` |

### Live functions the application does not call (44 names)

Service-role only unless stated. Trigger functions are attached as listed in the Triggers section of [[database/schema.tech]].

| Function | Returns | Canonical file | Purpose |
|---|---|---|---|
| `add_tokens_atomic(p_user_id, p_tokens_to_add integer, p_action, p_idempotency_key text, p_payment_intent_id=d, p_package_id=d)` | boolean (D) | `baseline_add_tokens_atomic` | Idempotent token credit (payments) |
| `anonymize_user_data(p_user_id uuid)` | void (D) | `baseline_anonymize_user_data` | GDPR anonymisation of a user row |
| `batch_lookup_lemmas(p_lemmas text[], p_language_id integer)` | TABLE (D) | `baseline_batch_lookup_lemmas` | Bulk lemma to vocab id lookup |
| `bkt_phase(p_known numeric)`, `bkt_phase_thresholds()` | text / TABLE | `phase5_algorithm_fixes` | BKT phase label and its thresholds |
| `calibration_clear_distractor_cache_misses(p_mode text=d)` | integer (D) | `task773b_calibration_distractor_cache_misses` | Forget miss markers so the builder retries |
| `calibration_next_anchor(p_session_id, p_word_language_id, p_definition_language_id, p_mode=d)` | TABLE | `task772_calibration_anchor_pool` | One-anchor wrapper of `calibration_next_anchors` |
| `calibration_refresh_zh_tone_inventory()` | integer (D) | `calibration_zh_tones` | Rebuilds `calibration_zh_tone_inventory` and `calibration_zh_char_readings` |
| `can_use_free_test(p_user_id uuid)` | boolean (D) | `phase3_rpc_fixes` | Free-test eligibility (live, no caller) |
| `create_user_dependencies()` | trigger | `baseline_create_user_dependencies` | After insert on `users`: creates token and language rows |
| `exercise_type_phase_weight(p_exercise_type text, p_phase text)`, `tier_to_phase(p_tier text)`, `tier_window_for_p_known(p_avg numeric)` | numeric / text / text[] | `phase9_get_exercise_session` | Helpers of the removed `get_exercise_session`, still live |
| `get_daily_free_test_limit(p_user_id uuid)` | integer (D) | `baseline_get_daily_free_test_limit` | Daily free tests of the user's tier |
| `get_model_for_task(p_task_key text, p_language_id smallint)` | text | `phase4_schema_evolution` | Live though documented dropped; its body reads `language_model_config`, a table that no longer exists, so any call fails (verified 2026-11-23) |
| `get_prompt_template(p_task_name varchar, p_language_id integer=d)` | text | `phase1_quick_wins` | Prompt lookup (live, no caller) |
| `get_quiz_distractors_batch(p_sense_ids integer[], p_language_id smallint, p_count integer=d, p_definition_language_ids smallint[]=d)` | TABLE (D) | `archive/get_quiz_distractors_batch` | Batch form; no SQL or app caller; drop pending |
| `get_session_senses(p_user_id, p_language_id, p_due_limit=d, p_learning_limit=d, p_new_limit=d)` | TABLE | `phase7_bkt_improvements` | Senses for an old session builder |
| `get_top_collocations_for_sources(p_source_ids integer[], p_min_pmi double precision, p_top_n integer)` | TABLE | `corpus_rpcs` | Top collocations per corpus source |
| `get_vocab_recommendations(p_user_id, p_language_id integer, p_target_unknown_min=d, p_target_unknown_max=d, p_limit=d)` | TABLE (D) | `phase6_security_hardening` | Vocabulary recommendations |
| `handle_new_user()` | trigger (D) | `baseline_handle_new_user` | Auth trigger that creates the `users` profile |
| `is_sense_quarantined(p_sense_id integer)` | boolean | `task767_sense_quarantine_guards` | True when a sense is on `calibration_anchor_blocklist` |
| `ladder_get_ring(p_level integer)` | integer | `phase8_momentum_bands` | Ring of a ladder level |
| `normalize_pos(p_tag text)`, `pos_tag_lookup(t text)` | text | `standardise_part_of_speech` | Part-of-speech normalisation |
| `process_stripe_payment(p_user_id, p_tokens_to_add, p_payment_intent_id, p_package_id, p_amount_cents)` | boolean (D) | `baseline_process_stripe_payment` | Credits tokens for a Stripe payment |
| `propagate_vocab_language_to_senses()`, `set_sense_word_language()` | trigger (D) | `calibration_sense_word_language_and_partial_hnsw` | Keep `dim_word_senses.word_language_id` in step with the vocabulary |
| `purge_old_log_rows(p_llm_raw_response_days=d, p_stage_timings_days=d, p_error_logs_days=d, p_batch_limit=d, p_dry_run=d)` | jsonb | `log_retention_purge` | Retention for `llm_calls.raw_response`, `generation_stage_timings`, `app_error_logs` |
| `selection_tuning_touch()`, `touch_user_study_plans_updated_at()`, `update_updated_at_column()` | trigger | `task744_selection_tuning_table`, `phase13_user_study_plans`, `baseline_update_updated_at_column` | `updated_at` maintenance |
| `semdisc_note_is_vague(n text)` | boolean | `baseline_semdisc_note_is_vague` | Judge-note helper |
| `sync_exercise_history()` | trigger | `phase4_schema_evolution` | Copies `exercise_attempts` to `user_exercise_history` |
| `test_sentence_references_check_l1_script()`, `test_sentences_check_l2_text()` | trigger | `test_sentence_references_schema` | Reference-table guards (L1 script check has a wrong range, fix pending) |
| `trg_blocklist_retire_exercises()`, `trg_exercises_sense_quarantine()`, `trg_generation_queue_sense_quarantine()` | trigger | `task767_sense_quarantine_guards` | Quarantine guards |
| `trg_dim_vocabulary_normalize_pos()` | trigger | `standardise_part_of_speech` | Normalises POS on write |
| `update_skill_attempts_count()`, `update_test_attempts_count()` | trigger | `phase3_rpc_fixes` | O(1) attempt counters |
| `update_user_vocab_stats()` | trigger | `baseline_update_user_vocab_stats` | Vocabulary stats on `users`; no trigger uses it (verified 2026-11-23), so it is dead |
| `usra_refuse_update()` | trigger | `task746_user_skill_rating_adjustments` | Blocks UPDATE on the append-only adjustments table |

### Pending function changes (migrations written, NOT applied; verified against live 2026-11-23)

Apply sheet: `migrations/PENDING-2026-11-23.md` (order, pre/post checks, rollbacks). Each row was re-checked against live on 2026-11-23: the pre-check hash in the sheet equals the live body's hash (`md5` of the body without comments and whitespace), so none of these has been applied.

| # | File | Effect when applied | Live today |
|---|---|---|---|
| 1 | `drop_update_vocabulary_from_word_test_4arg.sql` | Drops the 4-argument overload | Both overloads exist (`(uuid,integer,boolean,smallint)` and the 5-argument form) |
| 2 | `test_sentence_references_l1_script_escapes.sql` | L1-script trigger with escaped code points, Han range from U+F900 | Live trigger function hash `fd8764ea...`: the range starts at U+8C48 (wrongly rejects some Hangul / Yi) |
| 3 | `prestudy_plan_inputs_definition_mode.sql` | Adds `ucs.mode = 'definition'` to the ability lookup | Live body has no such filter |
| 4 | `skill_ratings_natural_key_unique.sql` | Unique indexes `(user_id, language_id, test_type_id)` on `user_skill_ratings` and `(test_id, test_type_id)` on `test_skill_ratings` | Only `id` primary keys and non-unique indexes exist |
| 5 | `skill_ratings_writers_on_conflict.sql` | The five submission RPCs and `apply_calibration_to_skill_ratings` use `ON CONFLICT` on those keys; must follow #4 | Plain `INSERT` after a failed lookup (as read above); hashes unchanged |
| 6 | `drop_get_quiz_distractors_batch.sql` | Drops `get_quiz_distractors_batch` (after the code that removed `QUIZ_DISTRACTORS_BATCH` is deployed) | Function exists |
| 7 | `data_fix_dt_cards_cross_language_20261123.sql` | One-off: deletes `dt_card` 11 and 12 and re-queues profile entry 10 | Both cards exist |
| 8 | `word_quiz_retake_fallback_hardened.sql` | `get_word_quiz_candidates` tier-2 fill (decision required) | Live hash `7670f2d5...` equals the sheet's pre-check |
| 9 | `word_upload_sweep_advisory_lock_hardened.sql` | Creates `word_upload_sweep_state` and the two sweep advisory-lock functions (decision required: watermark seed) | `to_regclass('public.word_upload_sweep_state')` is NULL; neither lock function exists; `services/word_list_import/sweep_cron.py` therefore errors at its 04:20 UTC run |

---

## Overview (2026-05 snapshot; superseded by the Live Function Reference above)

| Metric | Value |
|--------|-------|
| Total application functions | 214 live on 2026-11-23 (the 61 below is the 2026-05 count; see Live Function Reference) |
| SECURITY DEFINER | 25 |
| SECURITY INVOKER | 36 |
| Trigger functions | 6 |
| Pure/IMMUTABLE functions | 16 |
| STABLE functions | 13 |
| Extension functions (not documented here) | 199 (pgvector, intarray, pg_trgm) |

### Categories at a Glance

| Category | Count | Functions |
|----------|-------|-----------|
| Auth & User Management | 7 | `is_admin`, `is_moderator`, `is_org_member` (ABSENT live), `get_org_role` (ABSENT live), `handle_new_user`, `create_user_dependencies`, `anonymize_user_data` |
| Token Economy | 4 | `add_tokens_atomic`, `get_token_balance`, `get_test_token_cost`, `get_daily_free_test_limit` (`can_use_free_test` is LIVE although documented dropped 2026-05-15; no callers) |
| Payment Processing | 1 | `process_stripe_payment` |
| ELO / Skill Rating | 3 | `calculate_elo_rating`, `calculate_volatility_multiplier`, `update_skill_attempts_count` |
| Test & Content | 6 | `get_recommended_test`, `get_recommended_tests`, `get_replay_tests`, `process_test_submission`, `update_test_attempts_count`, `tests_containing_sense` |
| Vocabulary & Knowledge (BKT) | 13 | `bkt_update`, `bkt_status`, `bkt_update_comprehension`, `bkt_update_word_test`, `bkt_update_exercise`, `bkt_apply_decay`, `bkt_effective_p_known`, `bkt_phase`, `bkt_phase_thresholds`, `update_vocabulary_from_test`, `update_vocabulary_from_word_test`, `get_word_quiz_candidates`, `update_user_vocab_stats` (`get_vocab_recommendations` dropped 2026-05-15 — no callers) |
| Vocabulary Lookup | 2 | `batch_lookup_lemmas`, `get_distractors` |
| Mystery System | 2 | `get_recommended_mysteries`, `process_mystery_submission` (both ABSENT live: mystery mode dropped 2026-09-22) |
| Packs & Content Discovery | 2 | `get_packs_with_user_selection` (ABSENT live), `get_active_languages` |
| Model Config | 1 | (`get_model_for_task` is LIVE although documented dropped 2026-05-15 — no callers, and it fails when called; model selection is in Python via `services/prompt_service.py`) |
| Corpus & Collocations | 1 | `get_top_collocations_for_sources` |
| Category / Topic Matching | 2 | `get_next_category`, `match_topics` |
| Prompt Templates | 1 | (`get_prompt_template` is LIVE although documented dropped 2026-05-15 — no callers; the Python method of the same name on `conversation_generation/database_client.py` is unrelated and remains) |
| Utility / Triggers | 2 | `update_updated_at_column`, `sync_exercise_history` |
| Vocabulary Ladder (Phase 8) | 9 | `ladder_get_family`, `ladder_get_ring`, `ladder_ring_families`, `ladder_compute_p_known`, `fsrs_schedule_review`, `ladder_record_attempt`, `ladder_pass_gate`, `ladder_graduate`, `get_ladder_session` |
| Exercise Session (Phase 9 + 11) | 4 | `exercise_type_phase_weight`, `tier_window_for_p_known`, `tier_to_phase`, `get_exercise_session` (Phase 11 adds the `p_user_theta` parameter and Gaussian IRT weight) |
| IRT Calibration (Phase 11) | 4 | `irt_apply_calibration`, `irt_compute_user_theta`, `irt_try_lock`, `irt_release_lock` |

---

## Auth & User Management

---

### `is_admin(p_user_id uuid): boolean`

- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Checks whether a user has admin privileges by joining the `users` table to `dim_subscription_tiers`. Returns `false` if the user is deleted or not found.

```sql
CREATE OR REPLACE FUNCTION public.is_admin(p_user_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT COALESCE(dst.is_admin, false)
  FROM users u
  JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
  WHERE u.id = p_user_id AND u.deleted_at IS NULL;
$function$
```

- **Key behaviors:** Returns NULL (falsy) if user not found; explicitly excludes soft-deleted users.

---

### `is_moderator(p_user_id uuid): boolean`

- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Checks whether a user has moderator OR admin privileges. Admins are always treated as moderators.

```sql
CREATE OR REPLACE FUNCTION public.is_moderator(p_user_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT COALESCE(dst.is_moderator OR dst.is_admin, false)
  FROM users u
  JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
  WHERE u.id = p_user_id AND u.deleted_at IS NULL;
$function$
```

- **Key behaviors:** Admin implies moderator. Soft-deleted users excluded.

---

### `is_org_member(p_user_id uuid, p_org_id uuid): boolean`

> **ABSENT LIVE (checked 2026-11-23): this function no longer exists in the database. The section is kept as history.**

> **ARCHIVED 2026-09-21.** Never called; dropped with organizations. Code and DDL are in `archive/db_backups/stage1-unused-tables-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). Kept for history.


- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Checks whether a user belongs to a specific organization by querying `organization_members`.

```sql
CREATE OR REPLACE FUNCTION public.is_org_member(p_user_id uuid, p_org_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT EXISTS (
    SELECT 1 FROM organization_members
    WHERE user_id = p_user_id AND organization_id = p_org_id
  );
$function$
```

---

### `get_org_role(p_user_id uuid, p_org_id uuid): text`

> **ABSENT LIVE (checked 2026-11-23): this function no longer exists in the database. The section is kept as history.**

> **ARCHIVED 2026-09-21.** Never called; dropped with organizations. Code and DDL are in `archive/db_backups/stage1-unused-tables-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). Kept for history.


- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Returns the role string (e.g. `'admin'`, `'member'`) for a user within an organization. Returns NULL if not a member.

```sql
CREATE OR REPLACE FUNCTION public.get_org_role(p_user_id uuid, p_org_id uuid)
 RETURNS text
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT role FROM organization_members
  WHERE user_id = p_user_id AND organization_id = p_org_id;
$function$
```

---

### `handle_new_user(): trigger`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Trigger function fired on `auth.users` INSERT. Creates a corresponding row in `public.users` with the free subscription tier. Auto-creates the free tier in `dim_subscription_tiers` if it does not exist. Uses `ON CONFLICT` for idempotency. Catches all exceptions to avoid blocking auth user creation.

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_free_tier_id integer;
BEGIN
    -- Get the ID of the 'free' subscription tier
    SELECT id INTO v_free_tier_id
    FROM dim_subscription_tiers
    WHERE tier_code = 'free'
    LIMIT 1;
    
    -- If free tier doesn't exist, create it
    IF v_free_tier_id IS NULL THEN
        INSERT INTO dim_subscription_tiers (
            tier_code,
            display_name,
            can_generate_tests,
            can_create_custom_tests,
            daily_free_tests
        )
        VALUES ('free', 'Free', false, false, 2)
        RETURNING id INTO v_free_tier_id;
        
        RAISE LOG 'Created free tier with ID: %', v_free_tier_id;
    END IF;
    
    -- Insert into public.users with correct column name
    INSERT INTO public.users (
        id, 
        email, 
        subscription_tier_id,
        email_verified, 
        created_at,
        last_login,
        total_tests_taken,
        total_tests_generated
    )
    VALUES (
        NEW.id,
        NEW.email,
        v_free_tier_id,
        COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
        NOW(),
        NOW(),
        0,
        0
    )
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        email_verified = COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
        last_login = NOW();
    
    RAISE LOG 'User profile created successfully for: % (tier_id: %)', NEW.email, v_free_tier_id;
    
    RETURN NEW;
    
EXCEPTION WHEN OTHERS THEN
    -- Log the full error for debugging
    RAISE WARNING 'Failed to create user profile for %: % (SQLSTATE: %)', 
        NEW.email, SQLERRM, SQLSTATE;
    -- Still return NEW so auth user creation doesn't fail
    RETURN NEW;
END;
$function$
```

- **Side effects:** Creates user row, potentially creates free tier row. Never fails (exception swallowed to protect auth flow).
- **Tables written:** `users`, possibly `dim_subscription_tiers`.

---

### `create_user_dependencies(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Trigger function that creates a `user_tokens` row with zero purchased tokens when a new user is created. Uses `ON CONFLICT` for idempotency.

```sql
CREATE OR REPLACE FUNCTION public.create_user_dependencies()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    INSERT INTO user_tokens (user_id, purchased_tokens)
    VALUES (NEW.id, 0)
    ON CONFLICT (user_id) DO NOTHING;
    
    RETURN NEW;
END;
$function$
```

- **Tables written:** `user_tokens`.

---

### `anonymize_user_data(p_user_id uuid): void`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Soft-deletes and anonymizes a user by replacing their email and display name with generic placeholders and setting `deleted_at` and `anonymized_at` timestamps. Only the user themselves or an admin can invoke this.

```sql
CREATE OR REPLACE FUNCTION public.anonymize_user_data(p_user_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  -- Verify caller owns this user_id OR is admin
  IF p_user_id != auth.uid() AND NOT is_admin(auth.uid()) THEN
    RAISE EXCEPTION 'Unauthorized: Cannot anonymize another user';
  END IF;
  
  -- Soft delete and anonymize
  UPDATE users
  SET 
    email = 'deleted-' || id || '@lingualoop.local',
    display_name = 'Deleted User',
    deleted_at = NOW(),
    anonymized_at = NOW()
  WHERE id = p_user_id;
  
  RAISE NOTICE 'User % anonymized successfully', p_user_id;
END;
$function$
```

- **Auth:** Caller must be the user or an admin.
- **Side effects:** Irreversibly overwrites PII fields.

---

## Token Economy

---

### `add_tokens_atomic(p_user_id uuid, p_tokens_to_add integer, p_action text, p_idempotency_key text, p_payment_intent_id text DEFAULT NULL, p_package_id text DEFAULT NULL): boolean`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Adds tokens to a user's balance atomically. Currently a stub that validates authorization only (Phase 3 TODO). Only the user themselves or an admin/moderator can call this.

```sql
CREATE OR REPLACE FUNCTION public.add_tokens_atomic(p_user_id uuid, p_tokens_to_add integer, p_action text, p_idempotency_key text, p_payment_intent_id text DEFAULT NULL::text, p_package_id text DEFAULT NULL::text)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  -- SECURITY: Allow only self-service OR admin/moderator role
  IF p_user_id != auth.uid() THEN
    IF NOT (is_admin(auth.uid()) OR is_moderator(auth.uid())) THEN
      RAISE EXCEPTION 'Unauthorized: Cannot add tokens for another user';
    END IF;
  END IF;
  
  -- TODO: Token addition logic will be implemented in Phase 3
  -- For now, just validate authorization
  
  RETURN true;
END;
$function$
```

- **Auth:** Self or admin/moderator.
- **Note:** Stub implementation -- always returns true.

---

### `get_token_balance(p_user_id uuid): integer`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Returns a user's current token balance (purchased + bonus). Only the user themselves or an admin/moderator can view the balance. Implemented in Phase 3 (was stub returning 0).

```sql
CREATE OR REPLACE FUNCTION public.get_token_balance(p_user_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_balance integer;
BEGIN
    IF p_user_id != auth.uid() THEN
        IF NOT (is_admin(auth.uid()) OR is_moderator(auth.uid())) THEN
            RAISE EXCEPTION 'Unauthorized: Cannot view another user''s token balance';
        END IF;
    END IF;

    SELECT COALESCE(purchased_tokens + bonus_tokens, 0)
    INTO v_balance
    FROM user_tokens
    WHERE user_id = p_user_id;

    RETURN COALESCE(v_balance, 0);
END;
$function$
```

- **Tables read:** `user_tokens`.

---

### `get_test_token_cost(p_user_id uuid): integer`

- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Returns the per-test token cost for a user based on their subscription tier. Defaults to 10 tokens if not configured.

```sql
CREATE OR REPLACE FUNCTION public.get_test_token_cost(p_user_id uuid)
 RETURNS integer
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT COALESCE(dst.tokens_per_test, 10)
  FROM users u
  JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
  WHERE u.id = p_user_id AND u.deleted_at IS NULL;
$function$
```

---

### `get_daily_free_test_limit(p_user_id uuid): integer`

- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Returns the daily free test limit for a user based on their subscription tier. Returns 0 if the user is deleted or has no tier.

```sql
CREATE OR REPLACE FUNCTION public.get_daily_free_test_limit(p_user_id uuid)
 RETURNS integer
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT COALESCE(dst.daily_free_tests, 0)
  FROM users u
  JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
  WHERE u.id = p_user_id AND u.deleted_at IS NULL;
$function$
```

---

### `can_use_free_test(p_user_id uuid): boolean`

> **LIVE on 2026-11-23 (this section previously said DROPPED 2026-05-15).** `migrations/drop_unused_rpcs.sql` did not remove it (or it was restored); no application caller.

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Checks whether a user can take a free test today. Properly enforces daily count (Phase 3 — was stub returning `daily_limit > 0`). Reads `free_tests_used_today` and `last_free_test_date` from users table; resets counter if last date is not today.

```sql
CREATE OR REPLACE FUNCTION public.can_use_free_test(p_user_id uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_daily_limit integer;
    v_used_today integer;
    v_last_free_date date;
BEGIN
    IF p_user_id != auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized: Cannot check free test status for another user';
    END IF;

    v_daily_limit := get_daily_free_test_limit(p_user_id);

    SELECT free_tests_used_today, last_free_test_date
    INTO v_used_today, v_last_free_date
    FROM users
    WHERE id = p_user_id AND deleted_at IS NULL;

    IF v_last_free_date IS NULL OR v_last_free_date < CURRENT_DATE THEN
        v_used_today := 0;
    END IF;

    RETURN COALESCE(v_used_today, 0) < v_daily_limit;
END;
$function$
```

- **Auth:** Caller must be the user (strict self-only).
- **Tables read:** `users`, `dim_subscription_tiers` (via `get_daily_free_test_limit`).

---

## Payment Processing

---

### `process_stripe_payment(p_user_id uuid, p_tokens_to_add integer, p_payment_intent_id text, p_package_id text, p_amount_cents integer): boolean`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Processes a Stripe payment by adding purchased tokens to a user's balance and recording the transaction. Uses `payment_intent_id` as an idempotency key (Stripe's built-in deduplication). Acquires a row-level lock on `user_tokens` to prevent race conditions.

```sql
CREATE OR REPLACE FUNCTION public.process_stripe_payment(p_user_id uuid, p_tokens_to_add integer, p_payment_intent_id text, p_package_id text, p_amount_cents integer)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    current_balance INTEGER;
    token_record RECORD;
BEGIN
    -- 1. Use payment_intent_id as idempotency key (Stripe's built-in deduplication)
    SELECT * INTO token_record FROM token_transactions WHERE payment_intent_id = p_payment_intent_id;
    IF FOUND THEN
        RETURN TRUE; -- Stripe payment already processed
    END IF;

    -- 2. Row-level lock
    SELECT * INTO token_record FROM user_tokens WHERE user_id = p_user_id FOR UPDATE;

    current_balance := token_record.purchased_tokens + token_record.bonus_tokens;

    -- 3. Add purchased tokens
    UPDATE user_tokens SET 
        purchased_tokens = purchased_tokens + p_tokens_to_add,
        total_tokens_purchased = total_tokens_purchased + p_tokens_to_add
    WHERE user_id = p_user_id;

    -- 4. Record transaction with Stripe details
    INSERT INTO token_transactions (
        user_id, tokens_added, action, idempotency_key,
        payment_intent_id, package_id, token_balance_after, 
        created_at
    ) VALUES (
        p_user_id, p_tokens_to_add, 'stripe_payment', p_payment_intent_id,
        p_payment_intent_id, p_package_id, current_balance + p_tokens_to_add,
        NOW()
    );

    RETURN TRUE;
END;
$function$
```

- **Side effects:** Updates `user_tokens`, inserts into `token_transactions`.
- **Concurrency:** Uses `FOR UPDATE` row-level locking.
- **Idempotency:** Checks `token_transactions.payment_intent_id` before processing.

---

## ELO / Skill Rating

---

### `calculate_elo_rating(current_rating integer, opposing_rating integer, actual_score numeric, k_factor integer DEFAULT 32, volatility_multiplier numeric DEFAULT 1.0): integer`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** Pure ELO calculation function. Computes a new rating given the current rating, opposing rating, and actual score (0.0 to 1.0). Supports adjustable K-factor and volatility multiplier. Clamps result between 400 and 3000.

```sql
CREATE OR REPLACE FUNCTION public.calculate_elo_rating(current_rating integer, opposing_rating integer, actual_score numeric, k_factor integer DEFAULT 32, volatility_multiplier numeric DEFAULT 1.0)
 RETURNS integer
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    expected_score NUMERIC;
    adjusted_k NUMERIC;
    new_rating NUMERIC;
BEGIN
    expected_score := 1.0 / (1.0 + POWER(10, (opposing_rating - current_rating) / 400.0));
    adjusted_k := k_factor * volatility_multiplier;
    new_rating := current_rating + (adjusted_k * (actual_score - expected_score));

    -- Clamp between 400 and 3000
    RETURN GREATEST(400, LEAST(3000, ROUND(new_rating)::INTEGER));
END;
$function$
```

- **Key behaviors:** Standard ELO formula. Rating floor 400, ceiling 3000.

---

### `calculate_volatility_multiplier(attempts integer, last_date date DEFAULT NULL, base_volatility numeric DEFAULT 1.0): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** Calculates a volatility multiplier for ELO adjustments. Increases volatility for users with few attempts (<10) and for users who have been inactive for >90 days.

```sql
CREATE OR REPLACE FUNCTION public.calculate_volatility_multiplier(attempts integer, last_date date DEFAULT NULL::date, base_volatility numeric DEFAULT 1.0)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    multiplier NUMERIC := base_volatility;
BEGIN
    -- Low attempts = higher volatility
    IF attempts < 10 THEN
        multiplier := multiplier + 0.5;
    END IF;

    -- Long time since last attempt = higher volatility
    IF last_date IS NOT NULL AND (CURRENT_DATE - last_date) > 90 THEN
        multiplier := multiplier + 0.5;
    END IF;

    RETURN multiplier;
END;
$function$
```

- **Key behaviors:** Base 1.0 + 0.5 for low attempts + 0.5 for inactivity. Max possible: 2.0.

---

### `update_skill_attempts_count(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Trigger function that increments `total_attempts` in `test_skill_ratings` after a new test attempt. Phase 3 fix: uses O(1) increment instead of COUNT(*) scan.

```sql
CREATE OR REPLACE FUNCTION public.update_skill_attempts_count()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    UPDATE test_skill_ratings
    SET total_attempts = total_attempts + 1,
        updated_at = NOW()
    WHERE test_id = NEW.test_id
      AND test_type_id = NEW.test_type_id;
    RETURN NEW;
END;
$function$
```

- **Tables written:** `test_skill_ratings`.
- **Phase 3 fix:** Was `COUNT(*)` scan, now O(1) increment. Duplicate trigger `update_skill_attempts_count_trigger` was removed in Phase 1.

---

## Test & Content

---

### `get_recommended_test(p_user_id uuid, p_language_id integer): SETOF tests`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Returns a single recommended test for a user by expanding ELO radius search. Tries radii of 50, 100, 250, 500, and 10000 around the user's listening and reading ELO ratings until a match is found. Returns a random test within the matching radius. **Phase 3 fix:** Now excludes tests the user has already attempted via `NOT EXISTS` on `test_attempts`. Also adds `SET search_path`.

```sql
CREATE OR REPLACE FUNCTION public.get_recommended_test(
    p_user_id uuid,
    p_language_id integer
)
 RETURNS SETOF tests
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_listening_type_id SMALLINT;
    v_reading_type_id SMALLINT;
    v_user_listening_elo INT := 1200;
    v_user_reading_elo INT := 1200;
    v_radius INT;
    v_radii INT[] := ARRAY[50, 100, 250, 500, 10000];
    v_test_found tests%ROWTYPE;
BEGIN
    SELECT id INTO v_listening_type_id FROM dim_test_types WHERE type_code = 'listening';
    SELECT id INTO v_reading_type_id FROM dim_test_types WHERE type_code = 'reading';

    SELECT
        MAX(CASE WHEN test_type_id = v_listening_type_id THEN elo_rating END),
        MAX(CASE WHEN test_type_id = v_reading_type_id THEN elo_rating END)
    INTO v_user_listening_elo, v_user_reading_elo
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id;

    IF v_user_listening_elo IS NULL THEN v_user_listening_elo := 1200; END IF;
    IF v_user_reading_elo IS NULL THEN v_user_reading_elo := 1200; END IF;

    FOREACH v_radius IN ARRAY v_radii
    LOOP
        SELECT t.*
        INTO v_test_found
        FROM tests t
        JOIN test_skill_ratings tsr ON t.id = tsr.test_id
        WHERE t.language_id = p_language_id
          AND t.is_active = TRUE
          AND tsr.test_type_id IN (v_listening_type_id, v_reading_type_id)
          AND (
              (tsr.test_type_id = v_listening_type_id
               AND tsr.elo_rating BETWEEN (v_user_listening_elo - v_radius)
                                       AND (v_user_listening_elo + v_radius))
              OR
              (tsr.test_type_id = v_reading_type_id
               AND tsr.elo_rating BETWEEN (v_user_reading_elo - v_radius)
                                       AND (v_user_reading_elo + v_radius))
          )
          -- FIX (Phase 3): Exclude already-attempted tests
          AND NOT EXISTS (
              SELECT 1 FROM test_attempts ta
              WHERE ta.user_id = p_user_id AND ta.test_id = t.id
          )
        ORDER BY random()
        LIMIT 1;

        IF v_test_found.id IS NOT NULL THEN
            RETURN NEXT v_test_found;
            RETURN;
        END IF;
    END LOOP;
END;
$function$
```

- **Key behaviors:** Expanding radius search (50 -> 10000). Default ELO 1200. Returns 0 or 1 row. **Phase 3: Now excludes already-attempted tests.**

---

### `get_replay_tests(p_user_id uuid, p_language_id smallint, p_test_type text, p_min_age_days int=7, p_exclude uuid[]='{}', p_limit int=10): TABLE(...)`

- **Security:** DEFINER · **Language:** plpgsql · **Added:** 2026-07-19 (TASK-702), [migrations/get_replay_tests.sql](../../migrations/get_replay_tests.sql)
- **Description:** Exhausted-pool fallback / shared selection code for `build_daily_session`'s replay slots (and, later, TASK-704 retry slots). The **inverse** of `get_recommended_tests`: returns the nearest-ELO tests of one `p_test_type` that the user **has** attempted, but whose most-recent attempt is **older than `p_min_age_days`** (default 7), excluding `p_exclude` and honouring the same premium/tier gating. Ordered by `|test_elo − user_elo|` asc, then oldest-attempt first. Returns nothing for an unknown/inactive `p_test_type`.
- **Returns:** `TABLE(test_id uuid, test_type text, elo_rating integer, elo_diff integer, last_attempt_at timestamptz)`
- **Callers stamp `slot_type='replay'`** on the result. As of TASK-704 (2026-07-19) the live `process_test_submission` **does** implement ADR-006 reduced-volatility damping — but it fires **only on `slot_type='retry'`, not `'replay'`** (the retry slot is the intended ADR-006 review surface). So replay repeats still move ELO like any other repeat; only the daily-load retry slot is damped.

### `get_recommended_tests(p_user_id uuid, p_language_id smallint): TABLE(...)`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Returns multiple recommended tests for a user by language id. Checks subscription tier for premium access. Excludes tests the user has already attempted **for that same test type**. Returns up to **10** tests per test type (listening, reading, dictation, pinyin, pitch_accent), deduplicated by `(test_id, test_type)`, sorted by ELO proximity.
- **Migration history:**
  - 2026-05-13 — signature changed from `(uuid, text)` to `(uuid, smallint)` via [migrations/fix_get_recommended_tests_signature.sql](../../migrations/archive/fix_get_recommended_tests_signature.sql).
  - 2026-05-17 — [migrations/update_get_recommended_tests_for_dictation.sql](../../migrations/archive/update_get_recommended_tests_for_dictation.sql): the `NOT EXISTS test_attempts` exclusion key changed from `(user_id, test_id)` to `(user_id, test_id, test_type_id)` so a user who took the listening version of a test still sees the dictation lane; added an 80-word transcript cap on the dictation lane specifically; CTE filter now requires `dim_test_types.is_active = true`.
  - 2026-06 — pinyin then pitch_accent added to `target_types` (now the full slug-based set the study planner can schedule).
  - 2026-07-19 (TASK-702) — per-type candidate cap raised **3 → 10** (`rank_in_type <= 10`) via [migrations/task702_get_recommended_tests_rank_cap.sql](../../migrations/task702_get_recommended_tests_rank_cap.sql), so `build_daily_session` can hydrate heavy-weekday budgets before falling back to replay slots. Canonical file is now `task702_get_recommended_tests_rank_cap.sql`.

**Returns:** `TABLE(test_id uuid, slug text, test_type text, title text, difficulty_level integer, elo_rating integer, elo_diff integer, tier text)`

```sql
CREATE OR REPLACE FUNCTION public.get_recommended_tests(
  p_user_id     uuid,
  p_language_id smallint
)
 RETURNS TABLE(test_id uuid, slug text, test_type text, title text, difficulty_level integer, elo_rating integer, elo_diff integer, tier text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
  v_user_tier_code TEXT;
  v_is_premium     BOOLEAN;
BEGIN
  -- 1. Determine User Access Level
  SELECT st.tier_code INTO v_user_tier_code
  FROM users u
  JOIN dim_subscription_tiers st ON u.subscription_tier_id = st.id
  WHERE u.id = p_user_id;

  v_is_premium := (v_user_tier_code NOT ILIKE '%free%');

  -- 2. Execute Recommendation Logic (unique test_ids only)
  RETURN QUERY
  WITH target_types AS (
    SELECT id AS type_id, type_code
    FROM dim_test_types
    WHERE type_code IN ('listening', 'reading', 'dictation')
  ),
  user_stats AS (
    SELECT
      tt.type_id,
      tt.type_code,
      COALESCE(usr.elo_rating, 1200) as current_elo
    FROM target_types tt
    LEFT JOIN user_skill_ratings usr
      ON usr.user_id = p_user_id
      AND usr.language_id = p_language_id
      AND usr.test_type_id = tt.type_id
  ),
  all_candidates AS (
    SELECT
      t.id AS c_test_id,
      t.slug::text AS c_slug,
      us.type_code::text AS c_test_type,
      t.title::text AS c_title,
      t.difficulty AS c_difficulty_level,
      tsr.elo_rating AS c_elo_rating,
      ABS(tsr.elo_rating - us.current_elo) AS c_elo_diff,
      t.tier::text AS c_tier,
      ROW_NUMBER() OVER (
        PARTITION BY us.type_code
        ORDER BY ABS(tsr.elo_rating - us.current_elo) ASC
      ) AS rank_in_type
    FROM user_stats us
    JOIN test_skill_ratings tsr ON tsr.test_type_id = us.type_id
    JOIN tests t ON t.id = tsr.test_id
    WHERE t.language_id = p_language_id
      AND t.is_active = true
      AND (
        t.tier = 'free-tier'
        OR (t.tier != 'free-tier' AND v_is_premium)
      )
      AND NOT EXISTS (
        SELECT 1
        FROM test_attempts ta
        WHERE ta.user_id = p_user_id
          AND ta.test_id = t.id
      )
  ),
  deduplicated AS (
    SELECT DISTINCT ON (c_test_id)
      c_test_id, c_slug, c_test_type, c_title,
      c_difficulty_level, c_elo_rating, c_elo_diff, c_tier
    FROM all_candidates
    WHERE rank_in_type <= 10   -- TASK-702: raised from 3
    ORDER BY c_test_id, c_elo_diff ASC
  )
  SELECT
    d.c_test_id, d.c_slug, d.c_test_type, d.c_title,
    d.c_difficulty_level, d.c_elo_rating, d.c_elo_diff, d.c_tier
  FROM deduplicated d
  ORDER BY d.c_elo_diff ASC;

END;
$function$
```

- **Key behaviors:** Free-tier users only see `free-tier` tests. Already-attempted tests are excluded. Top 3 per test type, deduplicated.
- **Tables read:** `users`, `dim_subscription_tiers`, `dim_test_types`, `user_skill_ratings`, `test_skill_ratings`, `tests`, `test_attempts`.

---

### `process_test_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_was_free_test boolean DEFAULT true, p_idempotency_key uuid DEFAULT NULL, p_furigana_used boolean DEFAULT false, p_prestudied boolean DEFAULT false): jsonb`

> **Live signature has two more arguments than the first line of the older text below (`p_furigana_used`, `p_prestudied`); the body below predates set-based grading and the row locks: see the Live Function Reference.**

- **Security:** DEFINER
- **Language:** plpgsql
- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** The primary test submission handler. Validates answers server-side against the `questions` table, calculates score, updates ELO ratings, records the attempt, and updates user language activity. Supports idempotency via UUID key. As of 2026-05-15, repeat attempts no longer skip ELO updates unconditionally — when a repeat is launched from today's daily-load *retry slot*, it earns reduced-volatility ELO via a time-decay factor. See [[decisions/ADR-006-retry-slot-reduced-elo]] and [migrations/process_test_submission_reduced_repeats.sql](../../migrations/process_test_submission_reduced_repeats.sql).

The live function body is maintained in [migrations/task704_process_test_submission_retry_elo.sql](../../migrations/task704_process_test_submission_retry_elo.sql) (canonical as of TASK-704, 2026-07-19; supersedes the archived `process_test_submission_reduced_repeats.sql` V4) — refer there for the canonical SQL. NB the **live signature is 8-arg**: it also takes `p_furigana_used boolean DEFAULT false` (furigana dampener 0.5× on user K), which the heading above omits. The re-landed damping applies in the live inline-ELO style (logistic expected score), not the archived `calculate_elo_rating`/volatility-helper style. High-level outline:

```text
-- 1. Auth + input validation (unchanged)
-- 2. Server-side answer grading via TEMP TABLE join on questions
-- 3. Idempotency: return cached row on matching idempotency_key
-- 4. Compute percentage, attempt_number, is_first_attempt
-- 5. Get-or-create user_skill_ratings (default 1200) and test_skill_ratings (default 1400)
-- 6. v_user_volatility := calculate_volatility_multiplier(tests_taken, last_test_date, 1.0)
-- 7. ELO branch:
--    IF v_is_first_attempt THEN
--      user K=32 * volatility,  test K=16 * 1.0  (status quo)
--    ELSE
--      v_is_retry_slot := EXISTS in daily_test_loads.test_ids for today
--                         where slot_type='retry' AND test_id matches
--      v_already_earned_today := EXISTS in test_attempts today
--                                 where elo_reduction_factor IS NOT NULL
--      IF v_is_retry_slot AND NOT v_already_earned_today THEN
--        days_since := EXTRACT(EPOCH FROM (NOW() - MAX(prior.created_at))) / 86400
--        base       := LEAST(1.0, GREATEST(0.20, days_since / 60.0))
--        prev_best  := MAX( score / total_questions * 100 )
--        bonus      := 0.25 IF (v_percentage - prev_best) >= 15 ELSE 0
--        v_factor   := LEAST(1.0, base + bonus)
--        user K=32 * volatility * v_factor,  test K=16 * v_factor
--        record v_factor into test_attempts.elo_reduction_factor
--      ELSE
--        skip ELO updates (status-quo zero-ELO repeat)
--      END IF
--    END IF
-- 8. UPDATE user_skill_ratings + test_skill_ratings (only when ELO actually moved)
-- 9. INSERT test_attempts (always, with elo_reduction_factor populated only on eligible repeats)
-- 10. UPSERT user_languages
-- 11. Return JSONB: { success, attempt_id, is_first_attempt, user_elo_before/after/change,
--                     test_elo_before/after/change, elo_reduction_factor, score,
--                     total_questions, percentage, question_results, message }
-- EXCEPTION WHEN OTHERS THEN return { success: false, error, error_detail }
```

- **Auth:** Caller must be the user (`auth.uid()` check).
- **Side effects:** Creates/updates `user_skill_ratings`, `test_skill_ratings`, inserts `test_attempts` (with optional `elo_reduction_factor`), upserts `user_languages`.
- **Key behaviors:**
  - ELO change on first attempts is unchanged (K=32 × volatility for users, K=16 for tests).
  - Repeat attempts now branch on retry-slot eligibility instead of always skipping. Eligible repeats apply a continuous time-decay factor `clamp(0.20, days_since_last/60, 1.0)` plus a `+0.25` improvement bonus, composed into the volatility argument passed to `calculate_elo_rating`. Non-eligible repeats still produce no ELO movement.
  - Anti-grind: at most one reduced-ELO submission per `(user, test)` per UTC day, gated by `test_attempts.elo_reduction_factor IS NOT NULL` sentinel.
  - **Phase 3 (2026-05-08):** Volatility multiplier re-enabled via `calculate_volatility_multiplier()`. Asymmetric K-factors retained.
  - Catches all exceptions and returns error JSON.
- **Idempotency:** Returns cached result if `idempotency_key` matches existing attempt.
- **Migration history:**
  - V1 → [migrations/elo_functions.sql](../../migrations/elo_functions.sql) (text-keyed schema, original)
  - V2 → `migrations/process_test_submission_v2.sql` (added server-side grading; inlined ELO; volatility dropped — DROPPED)
  - V3 → [migrations/wire_volatility_and_exclude_attempted.sql](../../migrations/wire_volatility_and_exclude_attempted.sql) (helpers re-wired, asymmetric K restored)
  - V4 → [migrations/process_test_submission_reduced_repeats.sql](../../migrations/process_test_submission_reduced_repeats.sql) (retry-slot reduced-volatility repeats, `elo_reduction_factor` column)

---

> **`process_test_submission-old` — DROPPED** (Phase 1). Was a duplicate of `process_test_submission`.

> **`migrate_test_json` — DROPPED** (Phase 1). Referenced non-existent tables (`test_questions`, `test_catalog`). Was broken since schema V2.

---

### `process_pinyin_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_correct_chars integer, p_total_chars integer, p_was_free_test boolean DEFAULT true, p_idempotency_key uuid DEFAULT NULL): jsonb`

- **Security:** DEFINER
- **Language:** plpgsql
- **Migration:** `migrations/process_pinyin_submission.sql` (2026-05-15)
- **Description:** Accuracy-based test submission for the Pinyin Tone Trainer. The pinyin trainer does not use MC questions, so `process_test_submission`'s question-validation loop cannot grade pinyin attempts (every synthetic-response submission scored 0/N_mc). This RPC takes pre-counted `correct_chars` / `total_chars` directly and records the attempt with truthful score/total/percentage. ELO update reuses the same K=32 formula as `process_test_submission`.
- **Arguments:**
  - `p_correct_chars` — characters answered without ever needing a retry (`max(0, total_chars - error_count)`)
  - `p_total_chars` — playable characters in the test
  - other args mirror `process_test_submission`
- **Validates:** `auth.uid()` matches `p_user_id`; `p_total_chars > 0`; `0 <= p_correct_chars <= p_total_chars`.
- **Side effects:** inserts `test_attempts` row; get-or-creates and updates `user_skill_ratings` + `test_skill_ratings`; upserts `user_languages.last_test_date / total_tests_taken`.
- **Returns:** JSONB envelope identical in shape to `process_test_submission` (`success`, `attempt_id`, `user_elo_before/after/change`, `test_elo_before/after/change`, `score`, `total_questions`, `percentage`, ...).

---

> **Cleanup migration (2026-05-15):** `migrations/cleanup_corrupt_pinyin_attempts.sql` deleted all `test_attempts` rows for the pinyin type (test_type_id = 11) that were produced by the broken synthetic-response path, recomputed `tests.total_attempts` for affected tests, and reset pinyin `user_skill_ratings` to ELO 1200 / `test_skill_ratings` to ELO 1400.

---

### `process_pitch_accent_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_correct_units integer, p_total_units integer, p_was_free_test boolean DEFAULT true, p_idempotency_key uuid DEFAULT NULL): jsonb`

- **Security:** DEFINER
- **Language:** plpgsql
- **Migration:** [migrations/process_pitch_accent_submission.sql](../../migrations/process_pitch_accent_submission.sql) (2026-05-17)
- **Description:** Accuracy-based test submission for the Japanese Pitch Accent Trainer. Mirrors `process_pinyin_submission` (parameter rename only) — accepts pre-counted `correct_units` / `total_units` (one unit per accent-phrase word), records the attempt, updates ELO via the same K=32 first-attempt-only formula. The pitch trainer does not use MC questions, so `process_test_submission` cannot grade pitch attempts.
- **Arguments:**
  - `p_correct_units` — accent-phrase words guessed without ever needing a retry (`max(0, total_units - error_count)`)
  - `p_total_units` — playable accent-phrase words in the test
  - other args mirror `process_test_submission`
- **Validates:** `auth.uid()` matches `p_user_id`; `p_total_units > 0`; `0 <= p_correct_units <= p_total_units`.
- **Side effects:** inserts `test_attempts` row; get-or-creates and updates `user_skill_ratings` + `test_skill_ratings`; upserts `user_languages.last_test_date / total_tests_taken`.
- **Returns:** JSONB envelope identical in shape to `process_pinyin_submission` (`success`, `attempt_id`, `user_elo_before/after/change`, `test_elo_before/after/change`, `score`, `total_questions`, `percentage`, ...).

---

### `process_dictation_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_word_correct integer, p_word_total integer, p_replay_count smallint, p_diff_payload jsonb, p_was_free_test boolean DEFAULT true, p_idempotency_key uuid DEFAULT NULL): jsonb`

- **Security:** DEFINER
- **Language:** plpgsql
- **Migration:** [migrations/process_dictation_submission.sql](../../migrations/process_dictation_submission.sql) (2026-05-17)
- **Description:** Word-accuracy submission for dictation mode. Tokenization, alignment, and Levenshtein fuzzy matching happen in Python ([services/dictation/grader.py](../../services/dictation/grader.py)); this RPC trusts the count inputs and performs validation, idempotency, ELO arithmetic, and writes only. Pure-SQL Levenshtein over JSONB token arrays was rejected as fragile and harder to test.
- **Arguments:**
  - `p_word_correct` / `p_word_total` — word-level counts produced by the grader after normalization + alignment.
  - `p_replay_count` — number of times the audio was played (≥ 1; 1 = no penalty).
  - `p_diff_payload` — per-token opcodes for the result-screen inline diff (capped at 200 entries client-side).
  - other args mirror `process_test_submission`.
- **Validates:** `auth.uid()` matches `p_user_id`; `p_word_total > 0`; `0 ≤ p_word_correct ≤ p_word_total`; `p_replay_count ≥ 1`.
- **ELO update:** composes `v_replay_factor = GREATEST(0.5, 1.0 - 0.10 * GREATEST(0, p_replay_count - 1))` into the K factor on first attempts AND retry-slot repeats (multiplicative composition with the retry-decay factor per [[decisions/ADR-006-retry-slot-reduced-elo]]). Persisted to `test_attempts.elo_reduction_factor` so the existing badge renderer in `profile.html` works unchanged.
- **Side effects:** inserts `test_attempts` row (populating `score`, `total_questions`, `replay_count`, `dictation_word_correct`, `dictation_word_total`, `dictation_diff`, `elo_reduction_factor`); get-or-creates and updates `user_skill_ratings` + `test_skill_ratings`; upserts `user_languages`.
- **Returns:** JSONB envelope shape identical to `process_pinyin_submission` plus `replay_count`, `replay_factor`, and the `diff` payload.

---

### `update_vocabulary_from_word_tests_batch(p_user_id uuid, p_language_id smallint, p_results jsonb): TABLE`

- **Security:** INVOKER
- **Language:** plpgsql
- **Migration:** [migrations/bkt_word_test_batch.sql](../../migrations/bkt_word_test_batch.sql) (2026-05-19)
- **Description:** Batched per-sense word-test BKT update. Mirrors the existing batched `update_vocabulary_from_test` (comprehension) but for direct sense-level word-test evidence using the stronger `bkt_update_word_test` slip/guess parameters (slip=0.05). Built for dictation (50-100 evidence points per submission) and any future bulk-evidence flows.
- **Arguments:**
  - `p_results` — JSONB array of `{"sense_id": int, "is_correct": bool}` entries. Duplicates allowed; the function dedupes via `bool_or` (credit as correct if any occurrence was correct).
- **Returns:** `TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)` — one row per unique sense after dedup.
- **Why dedup**: BKT assumes independent samples. Repeated occurrences of the same word in one transcript aren't independent; they should produce one evidence point. This is also a correctness fix vs the prior per-word loop, which compounded `word_test_correct`/`word_test_wrong` for repeated tokens.
- **Performance:** single set-based `INSERT ... ON CONFLICT` over the deduped input. Replaces what was previously N sequential calls to `update_vocabulary_from_word_test` from the dictation submit handler — the root cause of the 2026-05-19 "Content-Length exceeds Body" worker-timeout truncation.
- **Side effects:** upserts `user_vocabulary_knowledge` rows; increments `evidence_count`, `word_test_correct`, `word_test_wrong`. The Python service caller ([VocabularyKnowledgeService.update_from_word_tests_batch](../../services/vocabulary/knowledge_service.py)) additionally runs `_auto_create_flashcards` and `_trigger_frequency_inference` once over the batch result.

---

### `update_test_attempts_count(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Trigger function that increments `total_attempts` on the `tests` table. Phase 3 fix: O(1) increment instead of COUNT(*).

```sql
CREATE OR REPLACE FUNCTION public.update_test_attempts_count()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    UPDATE public.tests
    SET total_attempts = total_attempts + 1
    WHERE id = NEW.test_id;
    RETURN NEW;
END;
$function$
```

- **Tables written:** `tests`.

---

### `tests_containing_sense(p_sense_id integer, p_language_id integer): TABLE(id uuid, transcript text, difficulty numeric, vocab_token_map jsonb)`

- **Security:** INVOKER
- **Language:** SQL (STABLE)
- **Description:** Returns all active tests in a given language that contain a specific vocabulary sense ID, using the `vocab_sense_ids` integer array with the `@>` (contains) operator.

```sql
CREATE OR REPLACE FUNCTION public.tests_containing_sense(p_sense_id integer, p_language_id integer)
 RETURNS TABLE(id uuid, transcript text, difficulty numeric, vocab_token_map jsonb)
 LANGUAGE sql
 STABLE
AS $function$
    SELECT t.id, t.transcript, t.difficulty, t.vocab_token_map
    FROM tests t
    JOIN dim_languages dl ON dl.id = p_language_id
    WHERE t.vocab_sense_ids @> ARRAY[p_sense_id]
      AND t.language_id = p_language_id
      AND t.is_active = TRUE;
$function$
```

---

## Vocabulary & Knowledge (BKT)

---

### `bkt_update(p_current numeric, p_correct boolean, p_slip numeric DEFAULT 0.10, p_guess numeric DEFAULT 0.25): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** Core Bayesian Knowledge Tracing (BKT) update function. Given a current knowledge probability, whether the answer was correct, and slip/guess parameters, returns the updated probability of knowledge. Clamps output between 0.02 and 0.98.

```sql
CREATE OR REPLACE FUNCTION public.bkt_update(p_current numeric, p_correct boolean, p_slip numeric DEFAULT 0.10, p_guess numeric DEFAULT 0.25)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    p_obs_knows NUMERIC;
    p_obs_not_knows NUMERIC;
BEGIN
    IF p_correct THEN
        p_obs_knows := 1 - p_slip;
        p_obs_not_knows := p_guess;
    ELSE
        p_obs_knows := p_slip;
        p_obs_not_knows := 1 - p_guess;
    END IF;

    RETURN GREATEST(0.02, LEAST(0.98,
        (p_obs_knows * p_current) /
        (p_obs_knows * p_current + p_obs_not_knows * (1 - p_current))
    ));
END;
$function$
```

- **Key behaviors:** Pure function. Floor 0.02, ceiling 0.98. Default slip=0.10, guess=0.25.

---

### `bkt_status(p_known numeric): text`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** Maps a BKT knowledge probability to a human-readable status string. Thresholds: <0.20 = unknown, <0.50 = encountered, <0.75 = learning, <0.90 = probably_known, >=0.90 = known.

```sql
CREATE OR REPLACE FUNCTION public.bkt_status(p_known numeric)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    RETURN CASE
        WHEN p_known < 0.20 THEN 'unknown'
        WHEN p_known < 0.50 THEN 'encountered'
        WHEN p_known < 0.75 THEN 'learning'
        WHEN p_known < 0.90 THEN 'probably_known'
        ELSE 'known'
    END;
END;
$function$
```

---

### `bkt_update_comprehension(p_current numeric, p_correct boolean): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** BKT update wrapper for comprehension test evidence. Uses slip=0.10, guess=0.25 (standard parameters for multiple-choice comprehension questions). **(Phase 7)** Now includes transit credit P(T)=0.02 after posterior update.

```sql
CREATE OR REPLACE FUNCTION public.bkt_update_comprehension(p_current numeric, p_correct boolean)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    RETURN bkt_update(p_current, p_correct, 0.10, 0.25);
END;
$function$
```

---

### `bkt_update_word_test(p_current numeric, p_correct boolean): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** BKT update wrapper for word test evidence. Uses slip=0.05, guess=0.25 (lower slip because word tests are more direct assessments of knowledge). **(Phase 7)** Now includes transit credit P(T)=0.05 after posterior update.

```sql
CREATE OR REPLACE FUNCTION public.bkt_update_word_test(p_current numeric, p_correct boolean)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    RETURN bkt_update(p_current, p_correct, 0.05, 0.25);
END;
$function$
```

---

### `bkt_update_exercise(p_current numeric, p_correct boolean, p_exercise_type text): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** **(Phase 5, Phase 7 transit)** Exercise-type-specific BKT update. Four tiers based on cognitive demand: Recognition (high guess 0.25, low slip 0.05, transit 0.05), Recall (low guess 0.10, moderate slip 0.10, transit 0.08), Nuanced (moderate guess 0.20, higher slip 0.15, transit 0.08), Production (very low guess 0.05, highest slip 0.20, transit 0.10). Falls back to default (slip=0.05, guess=0.25, transit 0.05) for unknown types.

```sql
-- See migrations/phase5_algorithm_fixes.sql for full definition
-- Routes to bkt_update() with exercise-type-specific slip/guess parameters
```

- **Tier mapping:**
  - Recognition: phonetic_recognition, definition_match, text_flashcard, listening_flashcard, cloze_completion
  - Recall: morphology_slot, jumbled_sentence, tl_nl_translation, nl_tl_translation, spot_incorrect_*
  - Nuanced: semantic_discrimination, collocation_gap_fill, collocation_repair, odd_one_out, odd_collocation_out
  - Production: verb_noun_match, context_spectrum, timed_speed_round, style_imitation, free_production, sentence_writing

---

### `bkt_apply_decay(p_known numeric, p_last_evidence_at timestamptz, p_stability real DEFAULT NULL, p_evidence_count integer DEFAULT 0): numeric`

> **Overloaded live:** the heading shows one of two live signatures; the other is listed in the Live Function Reference.

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** **(Phase 7, supersedes Phase 5)** FSRS stability-informed temporal decay. Two-path model:
  - **Path A:** If `p_stability > 0`, uses `retrievability = exp(-days / stability)` (FSRS-backed)
  - **Path B:** Fallback to evidence-count-scaled half-life: `30 * (1 + 0.5 * ln(1 + evidence_count))`
  - Floor: 0.10. No decay within 1 day.

---

### `bkt_effective_p_known(p_known numeric, p_last_evidence_at timestamptz, p_stability real DEFAULT NULL, p_evidence_count integer DEFAULT 0): numeric`

> **Overloaded live:** the heading shows one of two live signatures; the other is listed in the Live Function Reference.

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** **(Phase 7)** Convenience wrapper calling `bkt_apply_decay` with all parameters. Used by `get_session_senses()` and any query needing decay-applied p_known.

---

### `get_session_senses(p_user_id uuid, p_language_id smallint, p_due_limit integer DEFAULT 30, p_learning_limit integer DEFAULT 30, p_new_limit integer DEFAULT 30): TABLE(out_sense_id integer, out_effective_p_known numeric, out_bucket text, out_entropy numeric)`

- **Security:** INVOKER
- **Language:** plpgsql (STABLE)
- **Description:** **(Phase 7)** Unified session-building RPC that returns all candidate senses with decay-applied effective p_known and bucket labels. Replaces three separate Python fetch methods. LEFT JOINs `user_flashcards` for FSRS stability. Returns three buckets:
  - `'due'`: FSRS due flashcards (state in review/relearning, due_date <= today)
  - `'learning'`: Uncertainty zone (effective 0.25–0.75), sorted by entropy DESC
  - `'new'`: Low effective p_known (< 0.30), status encountered/unknown

---

### `bkt_apply_lapse_penalty(p_user_id uuid, p_sense_id integer): void`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** **(Phase 7)** Applies 20% p_known penalty when FSRS records a lapse. `p_known *= 0.80`, clamped to floor 0.10. Preserves `user_marked_unknown` status. Called from Python after FSRS `schedule_review()` detects `new_card.lapses > old_card.lapses`.

---

### `bkt_infer_from_frequency(p_user_id uuid, p_language_id smallint, p_known_sense_id integer, p_new_p_known numeric): integer`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** **(Phase 7)** Frequency-tier inference. When a rare word reaches "known" (p_known ≥ 0.90), boosts common words with `evidence_count < 3` and `frequency_rank > known_word_rank + 1.0` to their frequency-based prior floor. Returns count of words boosted. Only raises p_known floors, never lowers.

---

### `bkt_contextual_inference(p_user_id uuid, p_language_id smallint, p_contextual_sense_ids integer[], p_score_ratio numeric): integer`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** **(Phase 7)** Sentence-level contextual inference. Applies dampened positive BKT update to vocabulary in test transcript that was NOT directly tested by any question. Dampening = 0.30 × score_ratio. Only fires when score ≥ 50%. Positive-only (never lowers p_known). Preserves `user_marked_unknown` status. Returns count of senses updated.

---

### `bkt_phase(p_known numeric): text`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** **(Phase 5)** Canonical phase thresholds — single source of truth. Returns 'A' (<0.30), 'B' (<0.55), 'C' (<0.80), 'D' (>=0.80). Python should import from config or call this function rather than hardcoding thresholds.

---

### `bkt_phase_thresholds(): TABLE(phase text, min_p_known numeric, max_p_known numeric)`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** **(Phase 5)** Exposes phase thresholds as a table for Python to query. Returns 4 rows: A(0.00-0.30), B(0.30-0.55), C(0.55-0.80), D(0.80-1.00).

---

### `update_vocabulary_from_test(p_user_id uuid, p_language_id smallint, p_question_results jsonb): TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Bulk updates vocabulary knowledge for a user after a comprehension test. Extracts sense IDs from each question's `sense_ids` array, deduplicates (using `bool_or` for correctness), computes BKT updates, and upserts into `user_vocabulary_knowledge`. Computes initial priors from word frequency rank when no prior knowledge exists. Preserves `user_marked_unknown` status.

```sql
CREATE OR REPLACE FUNCTION public.update_vocabulary_from_test(p_user_id uuid, p_language_id smallint, p_question_results jsonb)
 RETURNS TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)
 LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    WITH question_senses AS (
        SELECT
            unnest(q.sense_ids) AS sense_id,
            (qr->>'is_correct')::boolean AS is_correct
        FROM jsonb_array_elements(p_question_results) qr
        JOIN questions q ON q.id = (qr->>'question_id')::uuid
        WHERE q.sense_ids IS NOT NULL
          AND array_length(q.sense_ids, 1) > 0
    ),
    deduped AS (
        SELECT qs.sense_id, bool_or(qs.is_correct) AS is_correct
        FROM question_senses qs
        GROUP BY qs.sense_id
    ),
    current_state AS (
        SELECT
            d.sense_id,
            d.is_correct,
            COALESCE(
                uvk.p_known,
                CASE
                    WHEN dv.frequency_rank IS NULL THEN 0.10
                    WHEN dv.frequency_rank >= 6.0 THEN 0.85
                    WHEN dv.frequency_rank >= 5.0 THEN 0.65
                    WHEN dv.frequency_rank >= 4.0 THEN 0.35
                    WHEN dv.frequency_rank >= 3.0 THEN 0.15
                    ELSE 0.05
                END
            ) AS p_current
        FROM deduped d
        JOIN dim_word_senses dws ON dws.id = d.sense_id
        JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
        LEFT JOIN user_vocabulary_knowledge uvk
            ON uvk.user_id = p_user_id AND uvk.sense_id = d.sense_id
    ),
    updated AS (
        SELECT
            cs.sense_id,
            cs.p_current AS p_before,
            bkt_update_comprehension(cs.p_current, cs.is_correct) AS p_after,
            cs.is_correct
        FROM current_state cs
    ),
    upserted AS (
        INSERT INTO user_vocabulary_knowledge
            (user_id, sense_id, language_id, p_known, status,
             evidence_count, comprehension_correct, comprehension_wrong,
             last_evidence_at, updated_at)
        SELECT
            p_user_id, u.sense_id, p_language_id,
            u.p_after, bkt_status(u.p_after),
            1,
            CASE WHEN u.is_correct THEN 1 ELSE 0 END,
            CASE WHEN u.is_correct THEN 0 ELSE 1 END,
            NOW(), NOW()
        FROM updated u
        ON CONFLICT (user_id, sense_id) DO UPDATE SET
            p_known = EXCLUDED.p_known,
            status = CASE
                WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
                THEN 'user_marked_unknown'
                ELSE EXCLUDED.status
            END,
            evidence_count = user_vocabulary_knowledge.evidence_count + 1,
            comprehension_correct = user_vocabulary_knowledge.comprehension_correct + EXCLUDED.comprehension_correct,
            comprehension_wrong = user_vocabulary_knowledge.comprehension_wrong + EXCLUDED.comprehension_wrong,
            last_evidence_at = NOW(),
            updated_at = NOW()
        RETURNING sense_id, p_known, status
    )
    SELECT
        upserted.sense_id,
        COALESCE(u.p_before, 0.10),
        upserted.p_known,
        upserted.status
    FROM upserted
    LEFT JOIN updated u ON u.sense_id = upserted.sense_id;
END;
$function$
```

- **Key behaviors:** Frequency-rank-based priors for new words. `user_marked_unknown` status is never overwritten by BKT. Uses `bool_or` dedup (if a sense appears in multiple questions, one correct answer counts as correct).
- **Tables written:** `user_vocabulary_knowledge`.

---

### `update_vocabulary_from_word_test(p_user_id uuid, p_sense_id integer, p_is_correct boolean, p_language_id smallint, p_exercise_type text DEFAULT NULL): TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Updates vocabulary knowledge for a single word after a word quiz or exercise. **Phase 5:** Added optional `p_exercise_type` parameter. When provided, routes to `bkt_update_exercise()` (exercise-type-specific slip/guess); when NULL, falls back to `bkt_update_word_test()`. Computes frequency-based priors for new words. Preserves `user_marked_unknown` status.

```sql
CREATE OR REPLACE FUNCTION public.update_vocabulary_from_word_test(p_user_id uuid, p_sense_id integer, p_is_correct boolean, p_language_id smallint)
 RETURNS TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_p_current NUMERIC;
    v_p_new NUMERIC;
    v_status TEXT;
BEGIN
    -- Get current p_known or compute prior
    SELECT COALESCE(uvk.p_known,
        CASE
            WHEN dv.frequency_rank IS NULL THEN 0.10
            WHEN dv.frequency_rank >= 6.0 THEN 0.85
            WHEN dv.frequency_rank >= 5.0 THEN 0.65
            WHEN dv.frequency_rank >= 4.0 THEN 0.35
            WHEN dv.frequency_rank >= 3.0 THEN 0.15
            ELSE 0.05
        END
    ) INTO v_p_current
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    LEFT JOIN user_vocabulary_knowledge uvk
        ON uvk.user_id = p_user_id AND uvk.sense_id = p_sense_id
    WHERE dws.id = p_sense_id;

    IF v_p_current IS NULL THEN
        v_p_current := 0.10;
    END IF;

    v_p_new := bkt_update_word_test(v_p_current, p_is_correct);
    v_status := bkt_status(v_p_new);

    INSERT INTO user_vocabulary_knowledge
        (user_id, sense_id, language_id, p_known, status,
         evidence_count, word_test_correct, word_test_wrong,
         last_evidence_at, updated_at)
    VALUES (
        p_user_id, p_sense_id, p_language_id,
        v_p_new, v_status,
        1,
        CASE WHEN p_is_correct THEN 1 ELSE 0 END,
        CASE WHEN p_is_correct THEN 0 ELSE 1 END,
        NOW(), NOW()
    )
    ON CONFLICT (user_id, sense_id) DO UPDATE SET
        p_known = EXCLUDED.p_known,
        status = CASE
            WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
            THEN 'user_marked_unknown'
            ELSE EXCLUDED.status
        END,
        evidence_count = user_vocabulary_knowledge.evidence_count + 1,
        word_test_correct = user_vocabulary_knowledge.word_test_correct + EXCLUDED.word_test_correct,
        word_test_wrong = user_vocabulary_knowledge.word_test_wrong + EXCLUDED.word_test_wrong,
        last_evidence_at = NOW(),
        updated_at = NOW();

    RETURN QUERY SELECT p_sense_id, v_p_current, v_p_new, v_status;
END;
$function$
```

- **Tables written:** `user_vocabulary_knowledge`.

---

### `get_vocab_recommendations(p_user_id uuid, p_language_id integer, p_target_unknown_min double precision DEFAULT 0.03, p_target_unknown_max double precision DEFAULT 0.07, p_limit integer DEFAULT 10): TABLE(id uuid, title text, slug text, unknown_pct float, unknown_count integer)`

> **DROPPED 2026-05-15** by `migrations/drop_unused_rpcs.sql`. Zero Python and SQL callers verified before drop. Recommendation logic lives in `get_recommended_test` / `get_recommended_tests`. Reference retained for history.

- **Security:** DEFINER — **Phase 6 fix:** Added `SET search_path TO 'public', 'pg_temp'`. Also: return type changed (column `test_id` → `id`, `double precision` → `float`), default `p_limit` changed from 20 → 10, old signature explicitly dropped first.
- **Language:** plpgsql
- **Description:** Recommends tests for vocabulary acquisition by finding tests where the percentage of unknown words falls within a target range (default 3-7%). Uses the user's known sense IDs and ELO rating (within +/-200) to filter. Sorts by proximity to the 5% ideal unknown ratio.

```sql
DROP FUNCTION IF EXISTS public.get_vocab_recommendations(uuid, integer, double precision, double precision, integer);

CREATE OR REPLACE FUNCTION public.get_vocab_recommendations(
    p_user_id uuid,
    p_language_id integer,
    p_target_unknown_min double precision DEFAULT 0.03,
    p_target_unknown_max double precision DEFAULT 0.07,
    p_limit integer DEFAULT 10
)
RETURNS TABLE(
    id uuid,
    title text,
    slug text,
    unknown_pct float,
    unknown_count integer
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_known_sense_ids integer[];
    v_user_elo int;
BEGIN
    SELECT known_sense_ids INTO v_known_sense_ids
    FROM user_vocabulary
    WHERE user_id = p_user_id AND language_id = p_language_id;

    SELECT elo_rating INTO v_user_elo
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id
    LIMIT 1;

    IF v_known_sense_ids IS NULL THEN v_known_sense_ids := '{}'; END IF;
    IF v_user_elo IS NULL THEN v_user_elo := 1200; END IF;

    RETURN QUERY
    SELECT
        t.id,
        t.title,
        t.slug,
        (CARDINALITY(t.vocab_sense_ids) - CARDINALITY(t.vocab_sense_ids & v_known_sense_ids))::float
          / NULLIF(CARDINALITY(t.vocab_sense_ids), 0) as u_pct,
        (CARDINALITY(t.vocab_sense_ids) - CARDINALITY(t.vocab_sense_ids & v_known_sense_ids)) as u_count
    FROM public.tests t
    LEFT JOIN public.test_skill_ratings tsr ON tsr.test_id = t.id
    WHERE
        t.language_id = p_language_id
        AND t.is_active = true
        AND (tsr.elo_rating BETWEEN (v_user_elo - 200) AND (v_user_elo + 200) OR tsr.elo_rating IS NULL)
        AND CARDINALITY(t.vocab_sense_ids) > 0
    HAVING
        (CARDINALITY(t.vocab_sense_ids) - CARDINALITY(t.vocab_sense_ids & v_known_sense_ids))::float
          / NULLIF(CARDINALITY(t.vocab_sense_ids), 0)
        BETWEEN p_target_unknown_min AND p_target_unknown_max
    ORDER BY ABS(u_pct - 0.05)
    LIMIT p_limit;
END;
$function$
```

- **Key behaviors:** Uses intarray `&` operator for set intersection. Targets i+1 comprehensible input (3-7% unknown words). Old signature must be explicitly dropped first because return type (OUT parameter names) changed.
- **Tables read:** `user_vocabulary`, `user_skill_ratings`, `tests`, `test_skill_ratings`.

---

### `get_word_quiz_candidates(p_user_id uuid, p_sense_ids integer[], p_language_id smallint, p_max_words integer DEFAULT 5): TABLE(...)`

- **Security:** DEFINER (STABLE) — **Phase 6 fix:** Changed from INVOKER to SECURITY DEFINER with `SET search_path TO 'public', 'pg_temp'` because this function reads RLS-protected `user_vocabulary_knowledge`, `dim_word_senses`, and `dim_vocabulary` tables.
- **Language:** plpgsql
- **Description:** Selects word quiz candidates from a set of sense IDs, targeting words the user is actively learning (p_known between 0.25 and 0.75). Scores candidates by knowledge uncertainty weighted by inverse log frequency rank. Excludes words marked as `user_marked_unknown`.

**Returns:** `TABLE(out_sense_id integer, out_lemma text, out_definition text, out_pronunciation text, out_p_known numeric, out_score numeric)`

```sql
CREATE OR REPLACE FUNCTION public.get_word_quiz_candidates(
    p_user_id uuid,
    p_sense_ids integer[],
    p_language_id smallint,
    p_max_words integer DEFAULT 5
)
 RETURNS TABLE(out_sense_id integer, out_lemma text, out_definition text, out_pronunciation text, out_p_known numeric, out_score numeric)
 LANGUAGE plpgsql
 STABLE
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        uvk.sense_id,
        dv.lemma,
        dws.definition,
        dws.pronunciation,
        uvk.p_known,
        (uvk.p_known * (1 - uvk.p_known) *
         (1.0 / GREATEST(1.0, ln(GREATEST(1.0, COALESCE(dv.frequency_rank, 1.0)::numeric))))
        ) AS score
    FROM user_vocabulary_knowledge uvk
    JOIN dim_word_senses dws ON dws.id = uvk.sense_id
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE uvk.user_id = p_user_id
      AND uvk.sense_id = ANY(p_sense_ids)
      AND uvk.p_known BETWEEN 0.25 AND 0.75
      AND uvk.status != 'user_marked_unknown'
    ORDER BY score DESC
    LIMIT p_max_words;
END;
$function$
```

- **Key behaviors:** Score formula: `p_known * (1 - p_known) * (1 / ln(frequency_rank))`. Targets maximum uncertainty words weighted toward high-frequency.

---

### `update_user_vocab_stats(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Trigger function that recalculates `total_senses_tracked` by counting keys in the `sense_learning_stats` JSONB column before each row update.

```sql
CREATE OR REPLACE FUNCTION public.update_user_vocab_stats()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.total_senses_tracked := (
    SELECT COUNT(*) FROM jsonb_object_keys(NEW.sense_learning_stats)
  );
  RETURN NEW;
END;
$function$
```

---

## Vocabulary Lookup

---

### `batch_lookup_lemmas(p_lemmas text[], p_language_id integer): TABLE(lemma text, vocab_id integer)`

- **Security:** DEFINER (STABLE)
- **Language:** plpgsql
- **Description:** Bulk lookup of vocabulary IDs by lemma strings for a given language. Used during test ingestion/creation to resolve lemma text to vocabulary table IDs.

```sql
CREATE OR REPLACE FUNCTION public.batch_lookup_lemmas(p_lemmas text[], p_language_id integer)
 RETURNS TABLE(lemma text, vocab_id integer)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
AS $function$
BEGIN
  RETURN QUERY
  SELECT v.lemma, v.id
  FROM dim_vocabulary v
  WHERE v.language_id = p_language_id
    AND v.lemma = ANY(p_lemmas);
END;
$function$
```

---

### `get_distractors(p_sense_id integer, p_language_id smallint, p_count integer DEFAULT 3): TABLE(out_definition text)`

- **Security:** DEFINER
- **Language:** plpgsql (STABLE)
- **Description:** Returns random distractor definitions for a word quiz. Selects definitions from the same language that are NOT from the same vocabulary item as the target sense, restricted to primary senses (`sense_rank = 1`).

**Auth-check history:**
- Phase 3 (2026-04-12): added `IF auth.uid() IS NULL THEN RAISE` and made the function SECURITY DEFINER.
- `get_distractors_drop_auth_check.sql` (2026-05-03): removed the check because `auth.uid()` returns NULL under the service-role JWT, breaking the admin vocab pipeline. Side effect: any anon caller could enumerate `dim_word_senses.definition`.
- `restore_get_distractors_auth_check.sql` (2026-05-15): re-added a guard keyed on `auth.role()` so service-role calls still pass while anon is blocked; also `REVOKE EXECUTE ... FROM anon; GRANT EXECUTE ... TO authenticated, service_role` for defense in depth.

```sql
CREATE OR REPLACE FUNCTION public.get_distractors(p_sense_id integer, p_language_id smallint, p_count integer DEFAULT 3)
 RETURNS TABLE(out_definition text)
 LANGUAGE plpgsql
 STABLE
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    IF auth.role() NOT IN ('authenticated', 'service_role') THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;

    RETURN QUERY
    SELECT dws.definition
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE dv.language_id = p_language_id
      AND dws.id != p_sense_id
      AND dws.vocab_id != (SELECT vocab_id FROM dim_word_senses WHERE id = p_sense_id)
      AND dws.sense_rank = 1
    ORDER BY random()
    LIMIT p_count;
END;
$function$
```

- **Key behaviors:** Random selection. Excludes all senses from the same vocab item. Role-based guard accepts both authenticated user JWTs and the service-role JWT (used by the admin vocab pipeline).

---

## Mystery System

> **ARCHIVED 2026-09-21.** Both RPCs are dropped by the migration. Code and DDL are in `archive/modules/mysteries-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). Kept for history.


---

### `get_recommended_mysteries(p_user_id uuid, p_language_id integer): SETOF jsonb`

> **ABSENT LIVE (checked 2026-11-23): this function no longer exists in the database. The section is kept as history.**

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Returns up to 10 recommended mystery games for a user, matched by ELO proximity (within 200 points). Returns JSONB objects with mystery metadata, both ELO ratings, and the ELO gap.

```sql
CREATE OR REPLACE FUNCTION public.get_recommended_mysteries(p_user_id uuid, p_language_id integer)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    v_user_elo integer;
    v_mystery_type_id integer;
BEGIN
    -- Get mystery test_type_id
    SELECT id INTO v_mystery_type_id
    FROM dim_test_types WHERE type_code = 'mystery';

    -- Get user's mystery ELO (default 1200 if no rating)
    SELECT COALESCE(
        (SELECT elo_rating FROM user_skill_ratings
         WHERE user_id = p_user_id
           AND language_id = p_language_id
           AND test_type_id = v_mystery_type_id),
        1200
    ) INTO v_user_elo;

    -- Return matching mysteries
    RETURN QUERY
    SELECT jsonb_build_object(
        'id', m.id,
        'slug', m.slug,
        'title', m.title,
        'premise', m.premise,
        'difficulty', m.difficulty,
        'language_id', m.language_id,
        'suspects', m.suspects,
        'total_attempts', m.total_attempts,
        'mystery_elo', COALESCE(msr.elo_rating, 1400),
        'user_elo', v_user_elo,
        'elo_gap', ABS(COALESCE(msr.elo_rating, 1400) - v_user_elo)
    )
    FROM mysteries m
    LEFT JOIN mystery_skill_ratings msr ON msr.mystery_id = m.id
    WHERE m.language_id = p_language_id
      AND m.is_active = true
      AND ABS(COALESCE(msr.elo_rating, 1400) - v_user_elo) <= 200
    ORDER BY ABS(COALESCE(msr.elo_rating, 1400) - v_user_elo) ASC
    LIMIT 10;
END;
$function$
```

- **Key behaviors:** Default mystery ELO 1400. User default 1200. Max 200 ELO gap. Up to 10 results.

---

### `process_mystery_submission(p_user_id uuid, p_mystery_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_idempotency_key uuid DEFAULT NULL): jsonb`

> **ABSENT LIVE (checked 2026-11-23): this function no longer exists in the database. The section is kept as history.**

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** The mystery submission handler -- analogous to `process_test_submission` but for mystery games. Validates answers against `mystery_questions` (across all scenes), calculates score, updates ELO for both user and mystery (first attempt only), records the attempt, and updates user language activity. Supports idempotency.

```sql
CREATE OR REPLACE FUNCTION public.process_mystery_submission(p_user_id uuid, p_mystery_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_idempotency_key uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    v_user_elo integer;
    v_mystery_elo integer;
    v_user_tests_taken integer;
    v_mystery_attempts integer;
    v_new_user_elo integer;
    v_new_mystery_elo integer;
    v_attempt_id uuid;
    v_attempt_number integer;
    v_is_first_attempt boolean;
    v_existing_attempt record;
    v_score integer := 0;
    v_total_questions integer := 0;
    v_question_results jsonb := '[]'::jsonb;
    v_question_record record;
    v_user_answer text;
    v_correct_answer text;
    v_is_correct boolean;
    v_percentage numeric;
    v_percentage_decimal numeric;
BEGIN
    -- ========================================================================
    -- SECURITY VALIDATION
    -- ========================================================================

    IF p_user_id != auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized: Cannot submit mystery for another user';
    END IF;

    -- ========================================================================
    -- INPUT VALIDATION
    -- ========================================================================

    IF p_responses IS NULL OR jsonb_array_length(p_responses) = 0 THEN
        RAISE EXCEPTION 'No responses provided';
    END IF;

    -- ========================================================================
    -- ANSWER VALIDATION
    -- ========================================================================

    CREATE TEMP TABLE temp_mystery_responses ON COMMIT DROP AS
    SELECT
        (elem->>'question_id')::UUID as question_id,
        elem->>'selected_answer' as selected_answer
    FROM jsonb_array_elements(p_responses) as elem;

    -- Validate each question across all scenes of this mystery
    FOR v_question_record IN (
        SELECT mq.id, mq.answer
        FROM mystery_questions mq
        JOIN mystery_scenes ms ON ms.id = mq.scene_id
        WHERE ms.mystery_id = p_mystery_id
        ORDER BY ms.scene_number, mq.created_at
    ) LOOP
        SELECT selected_answer INTO v_user_answer
        FROM temp_mystery_responses
        WHERE question_id = v_question_record.id;

        v_user_answer := COALESCE(v_user_answer, '');
        v_correct_answer := v_question_record.answer #>> '{}';
        v_is_correct := (v_user_answer = v_correct_answer);

        IF v_is_correct THEN
            v_score := v_score + 1;
        END IF;

        v_question_results := v_question_results || jsonb_build_object(
            'question_id', v_question_record.id::TEXT,
            'selected_answer', v_user_answer,
            'correct_answer', v_correct_answer,
            'is_correct', v_is_correct
        );

        v_total_questions := v_total_questions + 1;
    END LOOP;

    DROP TABLE IF EXISTS temp_mystery_responses;

    IF v_total_questions = 0 THEN
        RAISE EXCEPTION 'No questions found for this mystery';
    END IF;

    -- ========================================================================
    -- IDEMPOTENCY CHECK
    -- ========================================================================

    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_attempt
        FROM mystery_attempts
        WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key;

        IF FOUND THEN
            RETURN jsonb_build_object(
                'success', true,
                'attempt_id', v_existing_attempt.id,
                'cached', true,
                'user_elo_change', COALESCE(
                    v_existing_attempt.user_elo_after - v_existing_attempt.user_elo_before, 0
                ),
                'message', 'Duplicate submission detected - returning cached result'
            );
        END IF;
    END IF;

    -- ========================================================================
    -- CALCULATE PERCENTAGE
    -- ========================================================================

    v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
    v_percentage_decimal := v_percentage / 100.0;

    -- ========================================================================
    -- DETERMINE ATTEMPT NUMBER
    -- ========================================================================

    SELECT COUNT(*) INTO v_attempt_number
    FROM mystery_attempts
    WHERE user_id = p_user_id AND mystery_id = p_mystery_id;

    v_attempt_number := v_attempt_number + 1;
    v_is_first_attempt := (v_attempt_number = 1);

    -- ========================================================================
    -- GET OR CREATE USER ELO RATING
    -- ========================================================================

    SELECT elo_rating, tests_taken
    INTO v_user_elo, v_user_tests_taken
    FROM user_skill_ratings
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND test_type_id = p_test_type_id;

    IF NOT FOUND THEN
        v_user_elo := 1200;
        v_user_tests_taken := 0;

        INSERT INTO user_skill_ratings (
            user_id, language_id, test_type_id, elo_rating, tests_taken
        ) VALUES (
            p_user_id, p_language_id, p_test_type_id, v_user_elo, 0
        );
    END IF;

    -- ========================================================================
    -- GET OR CREATE MYSTERY ELO RATING
    -- ========================================================================

    SELECT elo_rating, total_attempts
    INTO v_mystery_elo, v_mystery_attempts
    FROM mystery_skill_ratings
    WHERE mystery_id = p_mystery_id;

    IF NOT FOUND THEN
        v_mystery_elo := 1400;
        v_mystery_attempts := 0;

        INSERT INTO mystery_skill_ratings (mystery_id, elo_rating, total_attempts)
        VALUES (p_mystery_id, v_mystery_elo, 0);
    END IF;

    -- ========================================================================
    -- CALCULATE ELO CHANGES (ONLY FOR FIRST ATTEMPTS)
    -- ========================================================================

    IF v_is_first_attempt THEN
        DECLARE
            expected_user_score numeric;
            k_factor integer := 32;
        BEGIN
            expected_user_score := 1.0 / (1.0 + POWER(10, (v_mystery_elo - v_user_elo) / 400.0));

            v_new_user_elo := ROUND(v_user_elo + k_factor * (v_percentage_decimal - expected_user_score));
            v_new_mystery_elo := ROUND(v_mystery_elo + k_factor * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));

            v_new_user_elo := GREATEST(400, LEAST(3000, v_new_user_elo));
            v_new_mystery_elo := GREATEST(400, LEAST(3000, v_new_mystery_elo));
        END;

        UPDATE user_skill_ratings
        SET elo_rating = v_new_user_elo,
            tests_taken = tests_taken + 1,
            last_test_date = CURRENT_DATE,
            updated_at = NOW()
        WHERE user_id = p_user_id
          AND language_id = p_language_id
          AND test_type_id = p_test_type_id;

        UPDATE mystery_skill_ratings
        SET elo_rating = v_new_mystery_elo,
            total_attempts = total_attempts + 1,
            updated_at = NOW()
        WHERE mystery_id = p_mystery_id;

        UPDATE mysteries
        SET total_attempts = total_attempts + 1,
            updated_at = NOW()
        WHERE id = p_mystery_id;
    ELSE
        v_new_user_elo := v_user_elo;
        v_new_mystery_elo := v_mystery_elo;
    END IF;

    -- ========================================================================
    -- INSERT ATTEMPT RECORD
    -- ========================================================================

    INSERT INTO mystery_attempts (
        user_id, mystery_id, score, total_questions,
        user_elo_before, user_elo_after,
        mystery_elo_before, mystery_elo_after,
        language_id, test_type_id,
        attempt_number, is_first_attempt,
        idempotency_key
    ) VALUES (
        p_user_id, p_mystery_id, v_score, v_total_questions,
        v_user_elo, v_new_user_elo,
        v_mystery_elo, v_new_mystery_elo,
        p_language_id, p_test_type_id,
        v_attempt_number, v_is_first_attempt,
        p_idempotency_key
    )
    RETURNING id INTO v_attempt_id;

    -- ========================================================================
    -- UPDATE USER_LANGUAGES
    -- ========================================================================

    INSERT INTO user_languages (
        user_id, language_id, total_tests_taken, last_test_date
    ) VALUES (
        p_user_id, p_language_id, 1, CURRENT_DATE
    )
    ON CONFLICT (user_id, language_id)
    DO UPDATE SET
        total_tests_taken = user_languages.total_tests_taken + 1,
        last_test_date = CURRENT_DATE,
        updated_at = NOW();

    -- ========================================================================
    -- RETURN RESULT
    -- ========================================================================

    RETURN jsonb_build_object(
        'success', true,
        'attempt_id', v_attempt_id,
        'attempt_number', v_attempt_number,
        'is_first_attempt', v_is_first_attempt,
        'user_elo_before', v_user_elo,
        'user_elo_after', v_new_user_elo,
        'user_elo_change', v_new_user_elo - v_user_elo,
        'mystery_elo_before', v_mystery_elo,
        'mystery_elo_after', v_new_mystery_elo,
        'score', v_score,
        'total_questions', v_total_questions,
        'percentage', v_percentage,
        'question_results', v_question_results,
        'message', CASE
            WHEN v_is_first_attempt THEN 'First attempt - ELO updated'
            ELSE 'Retake - ELO unchanged'
        END
    );

EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', SQLSTATE
    );
END;
$function$
```

- **Auth:** Caller must be the user.
- **Side effects:** Creates/updates `user_skill_ratings`, `mystery_skill_ratings`, `mysteries`, inserts `mystery_attempts`, upserts `user_languages`.
- **Key behaviors:** Questions span multiple scenes via `mystery_scenes` join. Uses `ON COMMIT DROP` temp table. ELO only updates on first attempt.

---

## Packs & Content Discovery

---

### `get_packs_with_user_selection(p_language_id integer, p_user_id uuid): TABLE(...)`

> **ABSENT LIVE (checked 2026-11-23): this function no longer exists in the database. The section is kept as history.**

> **ARCHIVED 2026-09-21.** Dropped with the language-packs archive. Code and DDL are in `archive/modules/language-packs-2026-09-21.zip`; dropped by `migrations/archive_unused_modules_2026_09_21.sql` (applied 2026-09-22). Kept for history.


- **Security:** INVOKER
- **Language:** SQL (STABLE)
- **Description:** Returns all public collocation packs for a language with a boolean flag indicating whether the user has selected each pack. Used to render the pack selection UI. **Phase 2:** `p_user_id` changed from `text` to `uuid` to match the rebuilt `user_pack_selections` table.

**Returns:** `TABLE(id bigint, pack_name text, description text, pack_type text, tags text[], total_items integer, difficulty_range text, is_selected boolean)`

```sql
CREATE OR REPLACE FUNCTION public.get_packs_with_user_selection(p_language_id integer, p_user_id uuid)
 RETURNS TABLE(id bigint, pack_name text, description text, pack_type text, tags text[], total_items integer, difficulty_range text, is_selected boolean)
 LANGUAGE sql
 STABLE
AS $function$
    SELECT
        cp.id,
        cp.pack_name,
        cp.description,
        cp.pack_type,
        cp.tags,
        cp.total_items,
        cp.difficulty_range,
        (ups.user_id IS NOT NULL) AS is_selected
    FROM collocation_packs cp
    LEFT JOIN user_pack_selections ups
        ON ups.pack_id = cp.id
       AND ups.user_id = p_user_id
    WHERE cp.language_id = p_language_id
      AND cp.is_public = TRUE
    ORDER BY cp.pack_name;
$function$
```

- **Phase 2:** Old signature with `text` parameter dropped.

---

### `get_active_languages(): TABLE(id integer, language_code text, language_name text, native_name text)`

- **Security:** DEFINER (Phase 6 — was INVOKER. Needs DEFINER to read RLS-protected dim_languages.)
- **Language:** plpgsql (STABLE)
- **Description:** Returns all active languages from `dim_languages`, ordered by display order. Falls back to `language_name` if `native_name` is NULL.

```sql
CREATE OR REPLACE FUNCTION public.get_active_languages()
 RETURNS TABLE(id integer, language_code text, language_name text, native_name text)
 LANGUAGE plpgsql
 STABLE
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        dl.id::INTEGER,
        dl.language_code::TEXT,
        dl.language_name::TEXT,
        COALESCE(dl.native_name, dl.language_name)::TEXT AS native_name
    FROM dim_languages dl
    WHERE dl.is_active = true
    ORDER BY dl.display_order;
END;
$function$
```

---

## Corpus & Collocations

---

### `get_top_collocations_for_sources(p_source_ids integer[], p_min_pmi double precision, p_top_n integer): TABLE(...)`

- **Security:** INVOKER
- **Language:** SQL (STABLE)
- **Description:** Returns the top N collocations (by PMI score) from a set of corpus sources, deduplicated by collocation text (keeping the highest-PMI representative).

**Returns:** `TABLE(id bigint, collocation_text text, n_gram_size integer, pmi_score double precision, log_likelihood double precision, t_score double precision, collocation_type text, pos_pattern text, language_id integer)`

```sql
CREATE OR REPLACE FUNCTION public.get_top_collocations_for_sources(p_source_ids integer[], p_min_pmi double precision, p_top_n integer)
 RETURNS TABLE(id bigint, collocation_text text, n_gram_size integer, pmi_score double precision, log_likelihood double precision, t_score double precision, collocation_type text, pos_pattern text, language_id integer)
 LANGUAGE sql
 STABLE
AS $function$
    -- Subquery: pick the highest-PMI representative for each collocation_text,
    -- then re-sort globally by PMI and apply LIMIT for correct top-N.
    SELECT sub.id, sub.collocation_text, sub.n_gram_size, sub.pmi_score,
           sub.log_likelihood, sub.t_score, sub.collocation_type,
           sub.pos_pattern, sub.language_id
    FROM (
        SELECT DISTINCT ON (cc.collocation_text)
            cc.id,
            cc.collocation_text,
            cc.n_gram_size,
            cc.pmi_score,
            cc.log_likelihood,
            cc.t_score,
            cc.collocation_type,
            cc.pos_pattern,
            cc.language_id
        FROM corpus_collocations cc
        WHERE cc.corpus_source_id = ANY(p_source_ids)
          AND cc.pmi_score >= p_min_pmi
        ORDER BY cc.collocation_text, cc.pmi_score DESC
    ) sub
    ORDER BY sub.pmi_score DESC
    LIMIT p_top_n;
$function$
```

- **Key behaviors:** Two-phase deduplication: `DISTINCT ON` per collocation_text, then global sort + limit.

---

## Category / Topic Matching

---

### `get_next_category(): TABLE(id integer, name text, status_id integer, target_language_id integer, last_used_at timestamp with time zone, cooldown_days integer)`

- **Security:** DEFINER (Phase 6 — was INVOKER. Needs DEFINER to read RLS-protected dim_status.)
- **Language:** plpgsql
- **Description:** Returns the next available universal category (no specific target language) that is active and has either never been used or has passed its cooldown period. Returns at most 1 row, ordered by least recently used.

```sql
CREATE OR REPLACE FUNCTION public.get_next_category()
 RETURNS TABLE(id integer, name text, status_id integer, target_language_id integer, last_used_at timestamp with time zone, cooldown_days integer)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.name::TEXT,
        c.status_id,
        c.target_language_id,
        c.last_used_at,
        c.cooldown_days
    FROM categories c
    JOIN dim_status s ON c.status_id = s.id
    WHERE s.status_code = 'active'
      AND c.target_language_id IS NULL  -- Only universal categories
      AND (
          c.last_used_at IS NULL
          OR c.last_used_at < NOW() - (c.cooldown_days || ' days')::INTERVAL
      )
    ORDER BY c.last_used_at NULLS FIRST
    LIMIT 1;
END;
$function$
```

---

### `match_topics(query_category integer, query_embedding vector, match_threshold double precision DEFAULT 0.85, match_count integer DEFAULT 5): TABLE(id uuid, concept_english text, similarity double precision)`

- **Security:** DEFINER (Phase 6 — was INVOKER. Good practice for DEFINER + search_path.)
- **Language:** plpgsql
- **Description:** Performs cosine similarity search over topic embeddings within a given category using pgvector. Returns topics exceeding the similarity threshold, sorted by similarity descending.

```sql
CREATE OR REPLACE FUNCTION public.match_topics(query_category integer, query_embedding vector, match_threshold double precision DEFAULT 0.85, match_count integer DEFAULT 5)
 RETURNS TABLE(id uuid, concept_english text, similarity double precision)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.concept_english,
        (1 - (t.embedding <=> query_embedding))::FLOAT AS similarity
    FROM topics t
    WHERE t.category_id = query_category
      AND t.embedding IS NOT NULL
      AND (1 - (t.embedding <=> query_embedding)) > match_threshold
    ORDER BY t.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$
```

- **Key behaviors:** Uses pgvector cosine distance operator (`<=>`). Converts to similarity (1 - distance). Default threshold 0.85.

---

## Model Config

---

### `get_model_for_task(p_task_key text, p_language_id smallint): text`

> **LIVE on 2026-11-23 (this section previously said DROPPED 2026-05-15).** `migrations/drop_unused_rpcs.sql` did not remove it (or it was restored); no application caller. Its body reads `language_model_config`, which no longer exists, so a call fails.

- **Security:** INVOKER (STABLE)
- **Language:** plpgsql
- **Description:** Looks up the active LLM model name for a given task key and language from the `language_model_config` table. Returns NULL if no active config exists. **Phase 4 addition** — part of the normalization that replaces growing model columns on `dim_languages`.

```sql
CREATE OR REPLACE FUNCTION public.get_model_for_task(
    p_task_key text,
    p_language_id smallint
)
RETURNS text
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    v_model text;
BEGIN
    SELECT model_name INTO v_model
    FROM language_model_config
    WHERE task_key = p_task_key
      AND language_id = p_language_id
      AND is_active = true
    LIMIT 1;

    RETURN v_model;
END;
$function$
```

- **Key behaviors:** Simple key-value lookup. Returns NULL (not error) when no config found — callers must handle fallback. Only returns active configs.
- **Tables read:** `language_model_config`.

---

## Prompt Templates

---

### `get_prompt_template(p_task_name character varying, p_language_id integer DEFAULT 2): text`

> **LIVE on 2026-11-23 (this section previously said DROPPED 2026-05-15).** `migrations/drop_unused_rpcs.sql` did not remove it (or it was restored); no application caller.

- **Security:** INVOKER
- **Language:** plpgsql (STABLE)
- **Description:** Retrieves the latest active prompt template for a given task, with language-specific override support. **Phase 1 fix:** Now uses `language_id` (integer) instead of `language_code` (text), since `prompt_templates` has `language_id` not `language_code`. Falls back to language_id=2 (English default). Old signature with text parameter dropped.

```sql
CREATE OR REPLACE FUNCTION public.get_prompt_template(
    p_task_name character varying,
    p_language_id integer DEFAULT 2
)
RETURNS text
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    result_text TEXT;
BEGIN
    -- Try language-specific first
    SELECT template_text INTO result_text
    FROM prompt_templates
    WHERE task_name = p_task_name
      AND language_id = p_language_id
      AND is_active = true
    ORDER BY version DESC
    LIMIT 1;

    -- Fall back to English (language_id=2) if not found
    IF result_text IS NULL AND p_language_id != 2 THEN
        SELECT template_text INTO result_text
        FROM prompt_templates
        WHERE task_name = p_task_name
          AND language_id = 2
          AND is_active = true
        ORDER BY version DESC
        LIMIT 1;
    END IF;

    RETURN result_text;
END;
$function$
```

- **Key behaviors:** Language-specific -> English (language_id=2) fallback. Versioned (latest version wins). Only active templates. Old signature with `language_code text` parameter explicitly dropped.

---

## Utility / Triggers

---

### `update_updated_at_column(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Generic trigger function that sets the `updated_at` column to `NOW()` on every row update. Attached to multiple tables throughout the schema.

```sql
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$function$
```

---

### `sync_exercise_history(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Trigger function that auto-populates `user_exercise_history` on every `exercise_attempts` INSERT. Copies user_id, exercise_id, sense_id, exercise_type, is_correct, is_first_attempt, and looks up language_id from the exercises table. **Phase 4 addition** — enables the anti-repetition table without changing existing INSERT paths. Silently catches errors (RAISE WARNING) so the main insert is never blocked.

```sql
CREATE OR REPLACE FUNCTION public.sync_exercise_history()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    INSERT INTO public.user_exercise_history (
        user_id, language_id, exercise_id, sense_id,
        exercise_type, is_correct, is_first_attempt, session_date
    )
    SELECT
        NEW.user_id,
        e.language_id,
        NEW.exercise_id,
        NEW.sense_id,
        NEW.exercise_type,
        NEW.is_correct,
        COALESCE(NEW.is_first_attempt, true),
        CURRENT_DATE
    FROM exercises e
    WHERE e.id = NEW.exercise_id;

    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'sync_exercise_history failed: %', SQLERRM;
    RETURN NEW;
END;
$function$
```

- **Trigger:** `trigger_sync_exercise_history` AFTER INSERT ON `exercise_attempts` FOR EACH ROW.
- **Key behaviors:** Joins exercises table for language_id. Defaults is_first_attempt to true. Session_date = CURRENT_DATE. Exception handler ensures main insert always succeeds.

---

## Vocabulary Ladder (Phase 8 Momentum Bands)

The vocabulary ladder progression engine lives entirely inside these RPCs. All schema mutations to `user_word_ladder` (family confidence, ring, gates, word_state, FSRS handoff) go through them. Source: [migrations/phase8_momentum_bands.sql](../../migrations/phase8_momentum_bands.sql). Design rationale: [[decisions/ADR-005-momentum-bands]].

---

### `ladder_get_family(p_level integer): text`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** Maps ladder level (1–9) to cognitive family. Pure function.

```sql
SELECT CASE p_level
    WHEN 1 THEN 'form_recognition'
    WHEN 2 THEN 'form_recognition'
    WHEN 3 THEN 'meaning_recall'
    WHEN 4 THEN 'form_production'
    WHEN 5 THEN 'collocation'
    WHEN 6 THEN 'semantic_discrimination'
    WHEN 7 THEN 'semantic_discrimination'
    WHEN 8 THEN 'collocation'
    WHEN 9 THEN 'form_production'
END;
```

---

### `ladder_get_ring(p_level integer): integer`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** Maps ladder level (1–9) to ring number (1–4). Pure.

```sql
SELECT CASE
    WHEN p_level BETWEEN 1 AND 2 THEN 1
    WHEN p_level BETWEEN 3 AND 5 THEN 2
    WHEN p_level BETWEEN 6 AND 7 THEN 3
    WHEN p_level BETWEEN 8 AND 9 THEN 4
END;
```

---

### `ladder_ring_families(p_ring integer, p_active_levels integer[]): text[]`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** Returns the cognitive families required to clear a given ring, computed from the word's active_levels. Concrete nouns (whose active_levels exclude 5 and 8) get a smaller required set for R2 and R4.

| Ring | Required if active | Family |
|------|--------------------|--------|
| 1 | L1 or L2 active | form_recognition |
| 2 | L3 active | meaning_recall |
| 2 | L4 active | form_production |
| 2 | L5 active | collocation |
| 3 | L6 or L7 active | semantic_discrimination |
| 4 | L8 active | collocation |
| 4 | L9 active | form_production |

---

### `ladder_compute_p_known(p_fc jsonb): numeric`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** Weighted aggregate of family confidences. Mirrors `services/vocabulary_ladder/config.py::compute_p_known_overall`.

```
p_known = 0.12·form_recognition + 0.18·meaning_recall + 0.20·form_production
        + 0.16·collocation + 0.16·semantic_discrimination + 0.18·contextual_use
```

Rounds to 4 decimals.

---

### `fsrs_schedule_review(p_stability real, p_difficulty real, p_last_review date, p_reps integer, p_lapses integer, p_state text, p_rating integer, p_review_date date DEFAULT CURRENT_DATE): jsonb`

- **Security:** INVOKER
- **Language:** plpgsql (STABLE)
- **Description:** Port of FSRS-4.5 to PostgreSQL ([services/vocabulary/fsrs.py](../../services/vocabulary/fsrs.py)). Used by `ladder_record_attempt` on the lapse path. Encodes the 17 default FSRS weights inline. Returns `jsonb` with `stability, difficulty, due_date, state, reps, lapses`.
- **States:** `new | learning | review | relearning`.
- **Ratings:** `1=again, 2=hard, 3=good, 4=easy`.
- **Constants:** `retention=0.9`, `max_interval=365` days.

---

### `ladder_record_attempt(p_user_id uuid, p_sense_id integer, p_exercise_id uuid, p_is_correct boolean, p_is_first_attempt boolean, p_time_taken_ms integer DEFAULT NULL, p_language_id smallint DEFAULT NULL, p_exercise_type text DEFAULT NULL, p_ladder_level integer DEFAULT NULL, p_exercise_context text DEFAULT 'standard'): jsonb`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Atomic write path for one exercise attempt. Locks `user_word_ladder` `FOR UPDATE`, updates family confidence, evaluates ring clearing / gate transitions / lapse path / **cross-session advancement gate / ring demotion**, writes all progression-state columns, UPSERTs `user_vocabulary_knowledge`, and (on lapse) updates `user_flashcards` + applies BKT lapse penalty. Redefined by [migrations/phase10_ladder_advancement_demotion.sql](../../migrations/phase10_ladder_advancement_demotion.sql) to layer cross-session validation and demotion onto Phase 8.
- **`p_exercise_context`:** `'standard' | 'gate' | 'stress_test'` — controls family BKT learn/slip rates (standard: 0.15/0.12, gate: 0.18/0.10, stress_test: 0.20/0.12).
- **Cross-session advancement gate (Phase 10):** A ring clears only if (a) every required family is ≥ its confidence threshold AND (b) every required family has first-attempt successes on ≥ 2 distinct calendar days, tracked in `family_success_dates` (JSONB, trimmed to the most recent 2 dates per family).
- **Ring demotion (Phase 10):** A first-attempt failure on a family that's required by the current ring demotes the word by one ring when `consecutive_failures ≥ 3`. R1 is the floor — no further demotion. Only the gate guarding exit from the dropped-into ring resets (gate_a on demote→R2, gate_b on demote→R3); other gates survive. `family_success_dates` for the demoted-into-ring required families is cleared; the learner must re-establish cross-session stability.
- **Returns JSONB:**
  ```
  is_correct boolean
  family text                                   -- which family this attempt updated
  family_confidence jsonb                       -- full new family_confidence map
  family_success_sessions jsonb                 -- per-family count of distinct cross-session
                                                --   successes (capped at 2 by storage trim).
                                                --   New in Phase 10.
  p_known_overall numeric                       -- weighted aggregate
  current_ring integer                          -- after this attempt (may be demoted)
  word_state text                               -- after this attempt
  review_due_at timestamptz                     -- next scheduled review
  requeue boolean                               -- = NOT correct AND is_first_attempt
  gate_pending text|null                        -- 'gate_a' | 'gate_b' | null
  stress_test_ready boolean                     -- true if all active families ≥ 0.72
  bkt_p_known numeric                           -- new overall BKT (separate from family)
  is_lapse boolean                              -- true if mastered word just failed
  demoted boolean                               -- true if this attempt triggered a ring drop.
                                                --   New in Phase 10.
  ```
- **Side effects:**
  - `INSERT exercise_attempts` (Phase 4 trigger fans out to `user_exercise_history`).
  - `UPDATE user_word_ladder` (all Phase 8 columns + Phase 10 `family_success_dates` + Phase 4 counters: `total_attempts`, `first_try_success_count`, `first_try_failure_count`, `consecutive_failures`, `last_success_session_date`, `last_exercised_family`). On demotion, `consecutive_failures` resets to 0.
  - `UPSERT user_vocabulary_knowledge` via `bkt_update_exercise`.
  - **Lapse path** (mastered + failed): extra 30% confidence penalty; `word_state := 'relearning'`; if a `user_flashcards` row exists, call `fsrs_schedule_review` with rating=1 and UPDATE; call `bkt_apply_lapse_penalty`.
- **Auto-init:** If no `user_word_ladder` row exists for (user, sense), INSERT a default row with semantic-class-derived `active_levels` (`{1,2,3,4,6,7,9}` for concrete nouns, else `{1,2,3,4,5,6,7,8,9}`), `current_ring=1`, `word_state='new'`.

---

### `ladder_pass_gate(p_user_id uuid, p_sense_id integer, p_gate_name text): jsonb`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Marks a threshold gate as passed and advances the ring. Called from Python after the gate battery has been evaluated client-side (`/api/vocab-dojo/gate/result` with `passed=true`). Gate **failure** doesn't have a dedicated RPC — failed batteries call `ladder_record_attempt` per item with `exercise_context='gate'` instead.
- **`p_gate_name`:** `'gate_a'` (unlocks R3) or `'gate_b'` (unlocks R4).
- **Returns JSONB:** `{ gate, passed: true, new_ring, word_state, p_known_overall }`.
- **Side effects:** `gates_passed[name] := true`; `current_ring := 3|4`; `word_state` recomputed (becomes `'pre_mastery'` if R4+gate_b+p_known≥0.88, else `'active'`); `review_due_at := tomorrow`.

---

### `ladder_graduate(p_user_id uuid, p_sense_id integer, p_stress_test_score real, p_language_id smallint): jsonb`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Graduation handoff from the ladder to FSRS-4.5. Called after a passing stress test (`/api/vocab-dojo/stress-test/result` with `passed=true`).
- **FSRS seeding from acquisition trace:**
  ```
  stress_bonus    = 1.0 if score ≥ 0.90 else 0.5 if ≥ 0.80 else 0.0
  stability       = clamp(7 + 21·p_known + 6·stress_bonus, 7, 34)
  family_stddev   = stddev_pop of the 5 active family confidences
  variance_penalty= min(1.5, family_stddev · 4)
  difficulty      = clamp(8 − 5·p_known + variance_penalty, 2, 8.5)
  first_due       = today + round(0.6 · stability)
  ```
- **Returns JSONB:** `{ word_state: 'mastered', stress_test_score, fsrs_stability, fsrs_difficulty, fsrs_due_date, p_known_overall }`.
- **Side effects:** `word_state := 'mastered'`, `stress_test_score := score`, `review_due_at := NULL` (FSRS owns scheduling from here); UPSERTs `user_flashcards` with `state='review'`, `reps≥1`, `lapses=0`.

---

### `get_ladder_session(p_user_id uuid, p_language_id smallint, p_count integer DEFAULT 20): TABLE(...)`

> **ABSENT LIVE (checked 2026-11-23); dropped 2026-11-17 by ADR-049.**

- **Security:** INVOKER
- **Language:** plpgsql (STABLE)
- **Description:** The Vocab Dojo session builder. Single SQL function: scores candidate words by priority, picks top N, picks one exercise per word preferring target-family + unseen variant + not-seen-today.
- **Priority:**
  ```
  0.35·overdue_score + 0.25·weakness_score + 0.20·gate_urgency
  + 0.10·novelty_score + 0.10·relapse_score
  ```
  - `overdue_score`: `LEAST(7, days_overdue) / 7`
  - `weakness_score`: ring-threshold − min(family confidences), floor 0; thresholds 0.50 / 0.50 / 0.65 / 0.72 by ring
  - `gate_urgency`: 1 if `word_state='gated'`
  - `novelty_score`: 0.5 if `last_exercised_family IS NULL`
  - `relapse_score`: 1 if `word_state='relearning'`
- **Anti-repetition:** correlated CTE against `user_exercise_history` for today's `session_date` — seen-today exercises are *deprioritised*, not eliminated (so users with a single exercise per word still get content).
- **Variant alternation:** prefers `exercises.tags->>'variant'` not equal to the last seen exercise for this sense.
- **Returns TABLE** (15 columns, all prefixed `out_`):
  ```
  out_sense_id, out_exercise_id, out_exercise_type, out_content,
  out_ladder_level, out_family, out_p_known, out_word_state,
  out_lemma, out_definition, out_pronunciation, out_variant,
  out_is_gate (= word_state='gated'),
  out_is_stress_test (= word_state='pre_mastery'),
  out_priority
  ```
- **Used by:** `/api/vocab-dojo/session` ([routes/vocab_dojo.py:14-70](../../routes/vocab_dojo.py#L14-L70)).

---

## Exercise Session (Phase 9 Daily Mixed Session)

The daily mixed exercise session is built by a single SQL RPC `get_exercise_session` plus three immutable helper functions. Source: [migrations/phase9_get_exercise_session.sql](../../migrations/phase9_get_exercise_session.sql). Replaces the Python 6-bucket builder; ladder content is delegated to `get_ladder_session` (Phase 8) internally.

---

### `exercise_type_phase_weight(p_exercise_type text, p_phase text): numeric`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** Per-(exercise_type, phase) weight used by `get_exercise_session` to rank candidate exercises within a sense. Mirrors `services/exercise_session_service.py::_get_eligible_types_weighted` and the `PHASE_MAP` registry in `services/exercise_generation/config.py`.
- **Rule:**
  - Phase A: 100% of weight on A types (3 types, 1/3 each).
  - Phase B: 70% on B types (7 types, 0.10 each) + 30% on A types (3 types, 0.10 each).
  - Phase C: 70% on C types (7 types) + 30% on B types (7 types).
  - Phase D: 70% on D types (4 types, 0.175 each) + 30% on C types (7 types).
  - Any unrecognised type: 0.001 (still selectable as last-resort fallback).

---

### `tier_window_for_p_known(p_avg numeric): text[]`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** Maps a user's average vocabulary `p_known` to the complexity-tier window used to pick supplementary grammar/collocation exercises. Mirrors the heuristic in `services/exercise_session_service.py::_get_supplementary_exercises`.

| Average p_known | Tier window |
|---|---|
| < 0.20 | [T1, T2] |
| < 0.40 | [T2, T3] |
| < 0.60 | [T3, T4] |
| < 0.80 | [T4, T5] |
| ≥ 0.80 | [T5, T6] |

---

### `tier_to_phase(p_tier text): text`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** Maps a complexity tier (T1–T6) to a phase letter (A/B/C/D). Used to label supplementary exercises in the session output. Mirrors `services/conversation_generation/categorical_maps.py::TIER_TO_PHASE`.

```
T1, T2 → A    T3 → B    T4 → C    T5, T6 → D
```

---

### `get_exercise_session(p_user_id uuid, p_language_id smallint, p_session_size integer DEFAULT 20, p_user_theta numeric DEFAULT 0.0): TABLE(...)`

> **ABSENT LIVE (checked 2026-11-23); dropped 2026-11-17 by ADR-049.**

- **Security:** INVOKER
- **Language:** plpgsql (STABLE)
- **Description:** Daily mixed-session builder. Single SQL function returning up to `p_session_size` candidate exercises across due / learning / new / ladder / supplementary slots. Anti-repetition via the indexed `user_exercise_history` table (7-day window). Ladder content delegated to `get_ladder_session` (cap 5). Virtual jumbled-sentence picks are NOT produced here — they depend on language-specific tokenisation and are appended by the Python caller.
- **Phase 11 IRT term:** `sense_candidates.type_weight` is multiplied by `EXP(-0.5 · ((irt_difficulty − p_user_theta)/σ)²)` (σ=1.0 logit) when `irt_n_attempts ≥ 20`, else 1.0. Source: [migrations/phase11_irt_selection.sql](../../migrations/phase11_irt_selection.sql). The Python wrapper computes `p_user_theta` via `irt_compute_user_theta` and passes it in.
- **Slot distribution** (40/40/20 from session_size):
  - `due_slots := ROUND(p_session_size * 0.40)`
  - `learning_slots := ROUND(p_session_size * 0.40)`
  - `new_slots := p_session_size − due − learning`
  - `ladder_cap := LEAST(5, p_session_size)`
  - Supplementary fills the remaining gap.
- **CTE pipeline:**
  1. `recent_seen` — DISTINCT `exercise_id` from `user_exercise_history` (last 7 days).
  2. `raw_senses` — `get_session_senses(user, lang, due*3, learning*3, new*3)` returns due / learning / new candidates with BKT-decay applied.
  3. `new_fallback` — `user_flashcards.state='new'` for senses missing from `raw_senses`.
  4. `senses_deduped` — collapses duplicates across buckets (prefer due > learning > new).
  5. `ladder_picks` — `get_ladder_session(user, lang, ladder_cap)`; priority bumped by +1.0 to anchor above vocab.
  6. `sense_candidates` — JOIN `exercises` for each deduped sense, attach `exercise_type_phase_weight`, exclude `recent_seen` and ladder picks.
  7. `ranked_sense_picks` — `ROW_NUMBER() OVER (PARTITION BY sense_id ORDER BY type_weight DESC, RANDOM())`.
  8. `vocab_picks_capped` — of `sense_rn = 1`, `ROW_NUMBER() OVER (PARTITION BY bucket ORDER BY type_weight DESC, RANDOM())`; keep `bucket_rn ≤ slot_allocation`.
  9. `vocab_picks` — map bucket → slot_type; priority = bucket-anchor (0.9 / 0.6 / 0.3) + 0.1 × type_weight.
  10. `supplementary_picks` — `exercises WHERE word_sense_id IS NULL AND complexity_tier = ANY(tier_window_for_p_known(avg))`; cap = `session_size − ladder − vocab`.
  11. Final UNION ALL → `ORDER BY priority DESC, RANDOM() LIMIT p_session_size`.
- **Returns TABLE** (8 columns, all prefixed `out_`):
  ```
  out_exercise_id    uuid
  out_sense_id       integer       -- NULL for supplementary picks
  out_exercise_type  text
  out_content        jsonb
  out_complexity_tier text
  out_phase          text          -- 'A'|'B'|'C'|'D'
  out_slot_type      text          -- 'due_review'|'active_learning'|'new_word'|'ladder'|'supplementary'
  out_priority       numeric
  ```
- **Used by:** `/api/exercises/session` via `ExerciseSessionService.get_or_create_daily_session()` ([services/exercise_session_service.py](../../services/exercise_session_service.py)).
- **Performance:** one round-trip per session build (vs the prior ~40 per-sense queries). Indexed lookups on `user_exercise_history(user_id, language_id, session_date, exercise_id)`, `exercises(word_sense_id, language_id)`, `exercises(complexity_tier)`.

---

## IRT Calibration (Phase 11)

Source: [migrations/add_irt_calibration_metadata.sql](../../migrations/add_irt_calibration_metadata.sql). Three small RPCs supporting the nightly 2PL fit (see [services/irt/calibrator.py](../../services/irt/calibrator.py)) plus an advisory-lock pair for cross-worker exclusion.

### `irt_apply_calibration(p_exercise_id uuid, p_discrimination numeric, p_difficulty numeric, p_se_difficulty numeric, p_n_attempts integer): void`

- **Security:** DEFINER
- **Language:** sql
- **Description:** Persists one fitted exercise in a single round-trip. Updates `irt_discrimination`, `irt_difficulty`, `irt_se_difficulty`, `irt_n_attempts`, and stamps `irt_calibrated_at = now()` server-side.
- **Used by:** `services/irt/calibrator.py::_persist_calibration`.

### `irt_compute_user_theta(p_user_id uuid, p_language_id smallint): numeric`

- **Security:** INVOKER
- **Language:** sql (STABLE)
- **Description:** Returns the logit of the user's clipped first-attempt accuracy in `user_exercise_history` for the given language. Clip range `[0.05, 0.95]` so 0% / 100% users don't produce ±infinity. Returns `0.0` for users with no first-attempt history.
- **Used by:** `services/exercise_session_service.py::_compute_session` to compute `p_user_theta` for `get_exercise_session`. Also used by the Python calibrator for consistency.

### `irt_try_lock(): boolean`, `irt_release_lock(): boolean`

- **Security:** DEFINER
- **Language:** sql
- **Description:** Wrappers around `pg_try_advisory_lock(8901234567890123)` / `pg_advisory_unlock(8901234567890123)` so the supabase python client can call them by name. Used by `calibrate_all_active_languages` to ensure only one gunicorn worker runs the nightly sweep even though APScheduler starts in every process.

### `pg_try_advisory_lock_for_study_plan(): boolean`, `pg_advisory_unlock_for_study_plan(): boolean`

- **Security:** DEFINER
- **Language:** sql
- **Source:** `migrations/study_plan_advisory_lock.sql` (applied live 2026-07-20, TASK-706)
- **Description:** Wrappers around `pg_try_advisory_lock(1467840848)` / `pg_advisory_unlock(1467840848)` (key `0x577D7950` = ASCII 'StPP', distinct from the IRT key) so the supabase python client can call them by name. Used by `_run_weekly_plan_recompute` (Sunday 23:00 UTC cron) so only the gunicorn worker that takes the session-level lock runs the sweep; the rest early-return `skipped:True`. The recompute is idempotent, so the lock only saves N× DB load rather than guarding correctness.

---

## Tier Assignment (ADR-029)

### `apply_jev_retier(p_rows jsonb): integer`

- **Purpose:** atomically apply a jev re-tier to active tests.
- **Arguments:** `p_rows` — array of `{id, new_tier, score, confidence, probabilities, model,
  calibration}` (`calibration` defaults to `'default'`).
- **Returns:** number of rows updated.
- **Behaviour:** sets `target_age_tier`, `age_tier_score/confidence/probabilities/model/
  calibration/assessed_at`; sets `difficulty` to `dim_complexity_tiers.difficulty_min` of the new
  tier **only where the tier changed**. Touches active tests only; never ELO.
- **Errors:** raises (rolling back the whole call) unless exactly `jsonb_array_length(p_rows)`
  rows update.
- **Auth:** `service_role` only (EXECUTE revoked from PUBLIC, anon, authenticated).
- **Callers:** `scripts/retier_tests_with_jev.py --apply`, `scripts/rederive_tiers.py --apply`.
- **Migrations:** `task820_apply_jev_retier.sql`, replaced by `task821_tier_calibration.sql`
  (adds the calibration label). See [[features/test-tier-assignment.tech]].

---

## Security Summary

The following table lists 48 application functions and their security model as of 2026-05 (stale: 214 functions are live, 85 SECURITY DEFINER; see the Live Function Reference for the current security column and execute privileges):

| # | Function | Security | Auth Check |
|---|----------|----------|------------|
| 1 | `add_tokens_atomic` | DEFINER | Self or admin/moderator |
| 2 | `anonymize_user_data` | DEFINER | Self or admin |
| 3 | `batch_lookup_lemmas` | DEFINER | None (STABLE) |
| 4 | `bkt_apply_decay` | INVOKER | None (IMMUTABLE) |
| 5 | `bkt_effective_p_known` | INVOKER | None (STABLE) |
| 6 | `bkt_phase` | INVOKER | None (IMMUTABLE) |
| 7 | `bkt_phase_thresholds` | INVOKER | None (IMMUTABLE) |
| 8 | `bkt_status` | INVOKER | None (IMMUTABLE) |
| 9 | `bkt_update` | INVOKER | None (IMMUTABLE) |
| 10 | `bkt_update_comprehension` | INVOKER | None (IMMUTABLE) |
| 11 | `bkt_update_exercise` | INVOKER | None (IMMUTABLE) |
| 12 | `bkt_update_word_test` | INVOKER | None (IMMUTABLE) |
| 13 | `calculate_elo_rating` | INVOKER | None (IMMUTABLE) |
| 14 | `calculate_volatility_multiplier` | INVOKER | None (IMMUTABLE) |
| 15 | `can_use_free_test` | DEFINER | Self only |
| 16 | `create_user_dependencies` | INVOKER | Trigger (no direct call) |
| 17 | `get_active_languages` | DEFINER | None (Phase 6: INVOKER→DEFINER) |
| 18 | `get_daily_free_test_limit` | DEFINER | None (called internally) |
| 19 | `get_distractors` | DEFINER | `auth.uid()` required (Phase 3: INVOKER→DEFINER) |
| 20 | `get_model_for_task` | INVOKER | None (STABLE) |
| 21 | `get_next_category` | DEFINER | None (Phase 6: INVOKER→DEFINER) |
| 22 | `get_org_role` | DEFINER | None (STABLE) |
| 23 | `get_packs_with_user_selection` | INVOKER | None (STABLE) |
| 24 | `get_prompt_template` | INVOKER | None (STABLE) |
| 25 | `get_recommended_mysteries` | DEFINER | None |
| 26 | `get_recommended_test` | DEFINER | None |
| 27 | `get_recommended_tests` | DEFINER | None |
| 28 | `get_test_token_cost` | DEFINER | None (called internally) |
| 29 | `get_token_balance` | DEFINER | Self or admin/moderator |
| 30 | `get_top_collocations_for_sources` | INVOKER | None (STABLE) |
| 31 | `get_vocab_recommendations` | DEFINER | None (Phase 6: search_path hardened) |
| 32 | `get_word_quiz_candidates` | DEFINER | None (Phase 6: INVOKER→DEFINER) |
| 33 | `handle_new_user` | DEFINER | Trigger (no direct call) |
| 34 | `is_admin` | DEFINER | None (STABLE) |
| 35 | `is_moderator` | DEFINER | None (STABLE) |
| 36 | `is_org_member` | DEFINER | None (STABLE) |
| 37 | `match_topics` | DEFINER | None (Phase 6: INVOKER→DEFINER) |
| 38 | `process_mystery_submission` | DEFINER | Self only (`auth.uid()`) |
| 39 | `process_stripe_payment` | DEFINER | None (server-side only) |
| 40 | `process_test_submission` | DEFINER | Self only (`auth.uid()`) |
| 41 | `sync_exercise_history` | INVOKER | Trigger (no direct call) |
| 42 | `tests_containing_sense` | INVOKER | None (STABLE) |
| 43 | `update_skill_attempts_count` | INVOKER | Trigger (no direct call) |
| 44 | `update_test_attempts_count` | INVOKER | Trigger (no direct call) |
| 45 | `update_updated_at_column` | INVOKER | Trigger (no direct call) |
| 46 | `update_user_vocab_stats` | INVOKER | Trigger (no direct call) |
| 47 | `update_vocabulary_from_test` | INVOKER | None |
| 48 | `update_vocabulary_from_word_test` | INVOKER | None |

### SECURITY DEFINER Functions (24 total)

These functions execute with the **privileges of the function owner** (typically the database admin), bypassing RLS. They require careful review:

| Function | Reason for DEFINER |
|----------|-------------------|
| `add_tokens_atomic` | Cross-table token operations |
| `anonymize_user_data` | Needs write access to user PII fields |
| `batch_lookup_lemmas` | Reads dimension tables without RLS overhead |
| `can_use_free_test` | Reads subscription tier data |
| `get_active_languages` | Reads RLS-protected dim_languages (Phase 6, +search_path) |
| `get_daily_free_test_limit` | Reads subscription tier data |
| `get_distractors` | Reads RLS-protected dim tables, requires auth (Phase 3, +search_path) |
| `get_next_category` | Reads categories + dim_status (Phase 6, +search_path) |
| `get_org_role` | Reads organization membership |
| `get_recommended_mysteries` | Reads across mystery + skill rating tables |
| `get_recommended_test` | Reads across test + skill rating tables |
| `get_recommended_tests` | Reads across test + skill rating + subscription tables |
| `get_test_token_cost` | Reads subscription tier data |
| `get_token_balance` | Reads token balance (sensitive) |
| `get_vocab_recommendations` | Reads user vocabulary + test data (Phase 6, +search_path) |
| `get_word_quiz_candidates` | Reads RLS-protected vocabulary knowledge tables (Phase 6, +search_path) |
| `handle_new_user` | Creates user rows (auth trigger) |
| `is_admin` | Reads subscription tier admin flag |
| `is_moderator` | Reads subscription tier moderator flag |
| `is_org_member` | Reads organization membership |
| `match_topics` | Reads topics table (Phase 6, +search_path) |
| `process_mystery_submission` | Multi-table transactional write |
| `process_stripe_payment` | Financial transaction with row locking |
| `process_test_submission` | Multi-table transactional write |
| `apply_jev_retier` | Bulk tier update; service-role only, all-or-nothing |
