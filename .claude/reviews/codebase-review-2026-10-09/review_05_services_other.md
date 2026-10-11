# Review 05 - services/dual_translation, vocabulary, corpus, model_arena, word_list_import, dictation, irt, classifier_curation, counter_curation

Read-only review. Findings verified against code unless marked PLAUSIBLE. Not exhaustively read: vocabulary/sense_generator.py, knowledge_service.py beyond the excerpts, dual_translation/prompts.py, passage_builder.py, corpus analyzers/style_analyzer.

### [HIGH] DT submit has no length cap on the learner's reproduction (LLM cost + O(n^2) diff)
- Category: security
- Location: routes/dual_translation.py:164-168 -> services/dual_translation/grader_cascade.py:92 -> services/dual_translation/prompts.py:449
- Problem: `reproduction` is only checked for non-empty `str`. It goes unbounded into Tier-0 `grade_dictation` (difflib `SequenceMatcher(autojunk=False)`, quadratic), into the Detector/Verifier/Explainer user prompts, and into the DB. The daily token budget (`_tokens_used_today`, routes/dual_translation.py:425) is checked before the call, so one huge submission overshoots it. Grades with `overall_band is None` are not persisted (:205-211), so they never count against the budget and can be retried unlimited times. No `MAX_CONTENT_LENGTH` is set in app.py/config.py. The dictation route has a "10x canonical" guard (routes/tests.py:884); DT has no equivalent.
- Evidence: no `len(reproduction)` check anywhere in routes/dual_translation.py. `tier0.py` reuses `grade_dictation`.
- Fix: Reject `len(reproduction) > ~3x len(gold)` (or a hard char cap) before grading. Count failed/provisional grades toward the budget. Set `MAX_CONTENT_LENGTH`.

### [HIGH] Word-list upload lets any authenticated user trigger unbounded LLM sense + exercise generation from arbitrary strings
- Category: security
- Location: routes/word_list_import.py:211-247, services/word_list_import/upload_handler.py:199-239
- Problem: `/api/word-list/submit` (`@jwt_required` only) accepts up to 50 non-empty strings of any length. There is no per-word length cap, no dedupe/strip, no per-user or global rate limit, and no concurrency limit (one daemon thread per request). Each unknown word runs `resolve_or_create_sense` (LLM sense generation, with the user string in the prompt) and then `VocabAssetPipeline.generate_for_sense` plus `render_all`, which are multi-LLM-call, minutes-long and paid. The user string also goes into the prompt (injection surface) and into `dim_vocabulary` / `dim_word_senses`, which are global shared tables, so garbage or adversarial lemmas become permanent shared content. The in-code comment only justifies 50 on wall-clock grounds.
- Evidence: the only validators are `isinstance(w,str) and w.strip()` and `len(words) > 50`. Threads are started with no registry or limit.
- Fix: Per-word max length (about 40 chars) plus script/charset validation for the language. Per-user daily quota and one in-flight batch per user. Consider a quarantine or approval state for newly created senses.

### [MEDIUM] IRT nightly calibration re-uses its own output as the "seed" prior, so shrinkage compounds every night (non-idempotent)
- Category: correctness
- Location: services/irt/calibrator.py:151-166 (`_load_exercise_seeds`), :309-313, :220-231
- Problem: `b_seed` is read from `exercises.irt_difficulty`, and `irt_apply_calibration` writes the shrunk posterior back into that same column. After the first run the "tier seed" is the previous posterior, so each night `apply_prior` pulls b toward an already-fitted value. The prior is re-counted every night, so with no new data the result is a moving fixed point and the original tier seed is lost. The docstring says the seed is the "tier-seeded `b_seed`".
- Evidence: the select is `exercises.irt_difficulty`, and the module docstring says the RPC UPDATEs `exercises.irt_difficulty`.
- Fix: Keep an immutable `irt_seed_difficulty` column (or derive the seed from tier) and shrink toward that.

### [MEDIUM] IRT first-attempt paging has no ORDER BY
- Category: correctness
- Location: services/irt/calibrator.py:127-143
- Problem: `.range(offset, ...)` pagination over `user_exercise_history` with no `.order(...)`. Postgres gives no stable order across pages, especially with concurrent writes, so rows can be skipped or duplicated. Duplicates inflate n and skew theta and fits. The nightly run is silent about it.
- Evidence: the query chain is `.select().eq().eq().range()` with no `.order`.
- Fix: Add `.order('id')` (or a stable key), or use a keyset cursor.

### [MEDIUM] Nightly DT synthesis fetches `dt_error_instance` with no pagination (PostgREST row cap silently truncates)
- Category: correctness
- Location: scripts/dt_nightly_synthesis.py:77-96 (called from services via app.py:374)
- Problem: The 2xW-day `dt_error_instance` query ends in a bare `.execute()`. Supabase caps responses (default 1000 rows), so once volume exceeds the cap the synthesis silently counts only part of the window. Profile rows and promotion thresholds are then wrong, and nothing logs it. `fetch_existing_status` also uses `_fetch_in_chunks` with chunk=500 user ids; a chunk with more than 1000 profile entries is truncated the same way. This is the kind of volume-dependent bug that appears only after launch.
- Evidence: no `.range(` or `max_rows` handling anywhere in the file.
- Fix: Page with `.range()` and a stable `.order('id')`, and warn when `len(page) == limit`.

### [MEDIUM] Admin-pipeline `sweep_unprocessed_sources` re-creates duplicate rows and never marks the original processed
- Category: correctness
- Location: services/corpus/run_corpus_processing.py:36-52 with services/corpus/ingestion.py:251-290
- Problem: The sweep finds `processed_at IS NULL` rows and calls `_run_pipeline(raw_text=...)`. `_run_pipeline` step 1 always INSERTs a NEW `corpus_sources` row and marks that one processed. The original stays `processed_at NULL`, so every run duplicates the source and its collocations, indefinitely. The module has no non-test importer and no scheduler reference, so it is effectively a latent footgun script.
- Evidence: ingestion.py:~287 `self.db.table('corpus_sources').insert({...})` unconditionally.
- Fix: Add a `source_id=` parameter to `_run_pipeline` that updates the existing row, or delete the script.

### [MEDIUM] Word-list uploads never run the "immediate" match sweep, so words matching existing tests never match
- Category: correctness
- Location: services/word_list_import/upload_handler.py (docstring "Does NOT run the match sweep"), routes/word_list_import.py:211-247, services/word_list_import/sweep_cron.py (watermark on `tests.created_at`)
- Problem: `sweep_immediate_matches` is called only from `sweep_cron`. Neither the upload handler nor the route calls it. The cron fetches only tests created after the watermark, so a freshly uploaded word whose matching tests already exist is never matched until a new test with that sense is generated. PLAUSIBLE intent gap: the Step-4 "immediate sweep after insert" described in the docs appears unwired. grep confirms no other caller.
- Evidence: `grep sweep_immediate_matches` returns only match_sweep.py (def) and sweep_cron.py.
- Fix: Call `sweep_immediate_matches` on the inserted rows at the end of `process_word_list_upload`, or backfill candidates for new watchlist rows in the cron.

### [MEDIUM] v1 DT grading path is dead but still ~220 lines of live-looking code, with stale "default OFF" comments
- Category: legacy/dead
- Location: services/dual_translation/grader_cascade.py:160-312 (v1 tier1/tier2 body), `_call_tier` :613, `_merge_scores` :675, `_safe_float` :689, `CONFIDENCE_ESCALATION_THRESHOLD`/`LARGE_DIFF_RATIO` consts; config.py:156-158; v1 prompt builders in prompts.py
- Problem: `Config.DT_FRAMEWORK_V2` defaults to `'True'` (since 2026-07-19), so the v1 body is reachable only via env rollback or `framework_v2=False` in tests. Comments still say "Gated by Config.DT_FRAMEWORK_V2 (default OFF)" and "The v1 tier1/tier2 body stays the shipping path until the flag flips" (grader_cascade.py:160-163). v1's fail-open default of `MAX_BAND` per dimension (:254/:287) is the full-marks leniency v2 was built to remove, so a stray env rollback silently re-enables it.
- Evidence: `_call_tier`, `_merge_scores`, `_safe_float` have no other callers (grep). `config.py:158` default `'True'`.
- Fix: Decide whether the rollback is still wanted. If not, delete the v1 branch and helpers (plus their tests). Either way, correct the stale comments.

### [MEDIUM] `update_from_test` conflates "RPC failed" with "nothing to update" and discards successful results when a post-step fails
- Category: correctness
- Location: services/vocabulary/knowledge_service.py:41-67
- Problem: One broad `try/except Exception -> return []` wraps the BKT RPC and then `_auto_create_flashcards`, `_seed_ladder_for_new_words` and `_trigger_frequency_inference`. A failure in any follow-on step (after the BKT write has already committed) returns `[]`, so callers see "no senses updated" while the DB was updated. Other methods (:359, :482, :526) follow the same pattern: errors are logged and the caller cannot distinguish failure from an empty result. The learner's knowledge model silently stops updating on RPC outage.
- Evidence: knowledge_service.py:41-67; the post-steps run inside the same `try`.
- Fix: Separate the RPC try from the post-steps (each fail-soft individually), and surface RPC failure to the caller (raise or return a sentinel).

### [MEDIUM] Production DT grader depends on `services.model_arena` (a local-only admin tool)
- Category: maintainability
- Location: services/dual_translation/{grader_cascade,explainer,passage_builder,router,prompts}.py import `services.model_arena.llm_runner.call_model_with_usage` / `models`
- Problem: The user-facing grading hot path depends on a package belonging to the local-only admin "arena" (`routes/model_arena.py`, `middleware/local_only`). `call_model_with_usage` bypasses `services.llm_service.call_llm` (its own retry, logging and `llm_calls` accounting): it calls the client directly, with no retry or `llm_calls` logging. Cost tracking for DT is hand-rolled via `grader_trace.tokens`. Two LLM-call paths to maintain.
- Evidence: model_arena/llm_runner.py:11-54 uses `get_client(...).chat.completions.create` directly.
- Fix: Move `call_model_with_usage` into `services/llm_service` (or `services/llm_usage.py`) and have both DT and the arena import it; log to `llm_calls` there.

### [LOW] Learner text is concatenated unfenced into judge/grader prompts (self-grade manipulation)
- Category: security
- Location: services/dual_translation/prompts.py:433-453 (`build_user_prompt`), explainer.py
- Problem: `reproduction` is interpolated as `"{label}: {text}"` lines with no delimiter or escaping, so a learner can write instructions such as "ignore the above, score 6" into their answer. Impact is bounded because the grade is the learner's own, but it feeds ELO/profile data and dt_error rows. Verifier/arbiter mitigations exist (evidence-span requirement) but there is no explicit fencing or "treat as data" instruction in the user prompt.
- Evidence: prompts.py:449 `lines = [f"{ref_label}: {gold_l2}", f"{learner_label}: {reproduction}"]`.
- Fix: Wrap in tagged blocks (`<learner_text>...</learner_text>`, stripping the tag from input) and state in the system prompt that its contents are data.

### [LOW] Card generation is check-then-insert, so concurrent `GET /next` can create duplicate cards
- Category: correctness
- Location: services/dual_translation/cards.py:400-466
- Problem: The function reads `queued` entries, checks existing `dt_card` rows, then inserts cards and flips status in separate statements. It is called on every `/next` and `/cards/due`. Two concurrent requests (double tab, prefetch) both see "no cards" and both insert. PLAUSIBLE: depends on whether `dt_card(profile_entry_id, ...)` has a unique constraint (not verified).
- Evidence: cards.py:424-464, no upsert or claim-by-update.
- Fix: Claim with `UPDATE ... SET remediation_status='drilling' WHERE status='queued' RETURNING` first, or add a unique constraint and use upsert.

### [LOW] Advisory locks taken through PostgREST RPC are session-scoped on pooled connections (PLAUSIBLE) and fail open
- Category: correctness
- Location: services/irt/calibrator.py:196-221, scripts/dt_nightly_synthesis.py:290-315, same pattern in sweep_cron
- Problem: `pg_try_advisory_lock` via `db.rpc` runs on a pooled backend, and the unlock may run on another backend, leaving the lock held on the first (or releasing nothing). All three helpers also return True when the RPC errors ("run unguarded"). So the mutex is best-effort and may skip jobs after a leak or double-run when the RPC is missing. Memory notes say the study-plan variant was made "real"; I did not verify these use `xact`/same-connection semantics.
- Evidence: the helpers call separate `rpc('..._lock')` / `rpc('..._unlock')`.
- Fix: Use a lease row (`UPDATE ... WHERE locked_until < now() RETURNING`) or a transaction-level lock inside a single RPC that runs the job.

### [LOW] `ingest_url` fetches an arbitrary admin-supplied URL with redirects (SSRF-capable)
- Category: security
- Location: services/corpus/ingestion.py:60-65, routes/corpus.py:43-49
- Problem: `httpx.get(url, follow_redirects=True)` with no scheme/host allow-list or private-IP block. Admin-only (`@admin_required`), so exposure is limited to a compromised admin or token, but it can reach cloud metadata or internal services. The fetched body size is also unbounded.
- Evidence: no URL validation before `httpx.get`.
- Fix: Allow only http(s); resolve and block private/link-local ranges; cap the response size.

### [LOW] classifier_curation and counter_curation are near-verbatim copies of one another
- Category: redundancy
- Location: services/classifier_curation/{judge,generator,schemas,config}.py vs services/counter_curation/*.py
- Problem: `judge.py` is identical after renaming `classifier`/`counter`. `generator` differs by about 78 diff lines, `schemas` by 49 and `config` by 24, mostly naming. Both judges are fail-open by design (documented). Per memory these were one-off curation runs (CC-CEDICT exhausted for coverage), so the packages are probably archivable.
- Evidence: a rename-normalised diff of judge.py yields 0 differing lines.
- Fix: Merge into one parameterised `curation` package, or move both to scripts/archive.

### [LOW] Orphan / test-only modules and functions
- Category: legacy/dead
- Location: services/corpus/tasks.py (`run_ingestion_async`, 0 callers anywhere), services/dual_translation/metrics.py (no non-test importer; `compute_recurrence_metrics` only tested), services/dual_translation/word_choice_variant.py `resolve_variant`, services/dual_translation/eval_metrics.py `span_detection_f1`, services/irt/calibrator.py `compute_user_theta_for_selection` (0 callers; the duplicate of `irt_compute_user_theta` RPC logic), services/vocabulary/config.py `supported_languages`, services/vocabulary/gloss_generator.py `build_gloss_prompt` (test only)
- Problem: No production callers found (repo-wide scan of .py excluding venv/data/static/sandbox).
- Evidence: scan output; the `metrics.py` and `compute_recurrence_metrics` tests are the only references. `resolve_variant` is listed because it had no non-test reference in the scan; not verified whether `word_choice_variant` is used another way.
- Fix: Delete or wire in. For `metrics.py`, confirm whether TASK-615 instrumentation is meant to be live.

### [LOW] 2PL standard-error code carries a no-op term and the SE ignores the prior shrinkage
- Category: correctness
- Location: services/irt/calibrator.py:104-106, 311-313
- Problem: `h_ab = ... + (((y - p)) * 1.0).sum() * 0.0` is a dead zero-term (the observed-information cross term is arguably wrongly dropped). `se_b` is computed for the unshrunk `b_fit` but persisted alongside the shrunk `b_post`, so the stored SE misdescribes the stored difficulty. Theta is per-user accuracy over the same items being calibrated (circular), and is clipped to [0.05, 0.95] only. Design-level, not a crash.
- Evidence: line 106 literal; `_persist_calibration(db, eid, a, b_post, se_b, n)`.
- Fix: Remove the dead term and either shrink SE with the prior or document the semantics.

### [LOW] Tokeniser/edit-distance helpers duplicated across dictation and dual_translation
- Category: redundancy
- Location: services/dictation/grader.py:72-100 (`_levenshtein` pure-python), services/dual_translation/tier0.py (re-normalises on top of dictation's normalize; docstring notes "doubly-normalized")
- Problem: Tier 0 deliberately layers its own NFKC/kata2hira fold over dictation's normalize/tokenise, then maps tokens back to raw text in `_RawTokenLocator` (grader_cascade.py:781). Two normalisation layers plus a locator exist only to undo the first. `rapidfuzz` / `Levenshtein` are installed in the venv, so the hand-rolled Levenshtein is replaceable. The dictation fuzzy match (len>=4, distance<=1) is also applied to CJK tokens, where it rarely triggers.
- Evidence: see the cited files.
- Fix: Give Tier 0 a single normalisation entry point that records offsets, and drop the pure-python Levenshtein if the dependency is declared in requirements.
