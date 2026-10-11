# Review 03 - services/vocabulary_ladder/ (read-only)

Note: the grep tool in this environment was filtered by rtk, so findings are from direct file reads plus a repo-wide def/constant reference count (count==1 means definition only, tests and scripts included).

### [HIGH] Nightly drain, admin and top-up regen run judges fail-OPEN, then replace live exercises
- Category: correctness
- Location: services/vocabulary_ladder/queue_drain.py:238-330 (_regenerate), routes/vocab_admin.py:62-85, routes/admin_local.py:1424
- Problem: Judges only fail closed inside `batch_mode()`. Only scripts/run_generation_batch.py:302 enters it. The queue-drain path (nightly cron, vocab_dojo, practice top-up), vocab_admin and admin_local call the pipeline and renderer without it. A dead model slug (the documented prompt-template slug rot) makes every judge call `safe_accept`, so unjudged content is stored. `_regenerate` then deletes the learner's existing exercises and inserts the unjudged ones.
- Evidence: `judges/base.py:297-305` `safe_accept` raises JudgeUnavailable only in batch_mode. `grep batch_mode` over services/vocabulary_ladder, routes, app.py and practice_session_service finds nothing. `asset_pipeline.py:505-510` itself says only code running in batch mode is fail-closed.
- Fix: Wrap `_regenerate` and the admin render paths in `batch_mode()` (use BatchModeThreadPoolExecutor, which pipeline already does). Treat JudgeUnavailable as "release the row and stop the drain".

### [HIGH] Asset store failures are swallowed, so the pipeline reports status "success" without persisting
- Category: correctness
- Location: services/vocabulary_ladder/asset_pipeline.py:1098-1165 (_store_asset), :233/277/300/531/596/622, :640-645
- Problem: `_store_asset` catches every exception, logs, and returns None. Callers do not check. `result['status']` is 'success' whenever `result['errors']` is empty. A failed upsert (CHECK violation, RLS, network) gives status 'success' while the DB lacks the asset. The renderer then reads `_load_assets` and builds from stale or missing content. This is the same class as the earlier asset_type CHECK defect, which would show here as log lines only.
- Evidence: `except Exception as e: logger.error(...)` at :1163-1165 with no raise and no return value. :640 `if not result['errors']: status='success'`.
- Fix: Return a bool or raise from `_store_asset` and append to `result['errors']` on failure, so status becomes 'partial'/'failed'.

### [HIGH] Valid-asset protection guard fails open
- Category: correctness
- Location: services/vocabulary_ladder/asset_pipeline.py:1117-1142
- Problem: The "never overwrite a valid asset with an invalid one" check sits in a try block. If the SELECT raises, the code logs and falls through to the upsert. The invalid row then overwrites the good one that is still serving exercises. A transient DB error removes the guard.
- Evidence: `except Exception as e: logger.error("Failed to check existing ...")` is followed by an unconditional upsert at :1155.
- Fix: On check failure, return without writing (fail closed), or re-raise.

### [MEDIUM] Unscoped/scoped regen deletes old exercises, then inserts a partial render; the "non-destructive" ordering is not atomic
- Category: correctness
- Location: services/vocabulary_ladder/queue_drain.py:296-321; services/vocabulary_ladder/exercise_renderer.py:344-346
- Problem: (a) `build_rows` swallows a per-level render exception with `logger.error` and does not record a Skip, so that level is silently absent from `new_rows`. (b) `_regenerate` deletes every ladder exercise for the sense (or the scoped levels) and inserts whatever rendered. A level whose render raised loses its existing exercises. The post-check `coverage_gaps` then marks the row failed, but the old rows are already gone. (c) If the `insert` raises after `delete.execute()`, the sense has no exercises, which contradicts the docstring "old exercises are deleted only after the new render". There is no transaction.
- Evidence: `exercise_renderer.py:344` logs only. `queue_drain.py:312` `delete_query.execute()` is followed by `:313` `insert(new_rows)`, both outside any RPC.
- Fix: Do swap in one RPC/transaction. Append a Skip on render exceptions, and refuse to delete a level that has no replacement row.

### [MEDIUM] vocab_admin render path is non-idempotent, and failures return [] silently
- Category: correctness
- Location: routes/vocab_admin.py:76 and :153 calling services/vocabulary_ladder/exercise_renderer.py:56-75 (render_all)
- Problem: `render_all` does a plain multi-row insert with no dedup. Re-running a sense hits `uq_exercises_context_free_variant` (migrations/task743...:106), so the whole batch insert fails. `render_all` catches this and returns `[]`, so the route's `try/except` never fires and it reports `exercises_rendered: 0` with HTTP success. vocab_admin:68-85 also renders every sense even when the pipeline result for it was 'failed'.
- Evidence: `exercise_renderer.py:72-74` `except Exception ... return []`. The docstring admits "no de-duplication".
- Fix: Route admin through the `_regenerate`-style build_rows + replace logic (or delete first), and surface the insert error.

### [MEDIUM] Queue claim has no lease; lock fails open; crashes strand rows as 'running'
- Category: correctness
- Location: services/vocabulary_ladder/queue_drain.py:175-207, :380-411
- Problem: `_claim_batch` is a read followed by a per-row update with no atomic claim. Rows marked 'running' have no lease or timestamp reclaim, so any crash or exception between claim and `_finish` leaves rows permanently 'running'. `_open_queue_sense_ids` treats 'running' as open, so `enqueue` and `enqueue_coverage_gaps` skip those senses forever. This matches the known "queue jammed since 2026-08-21 with no lease". `_try_lock` returns True when the RPC is missing or errors (fail-open mutex). A session-level advisory lock taken through PostgREST may be unlocked on a different pooled connection (PLAUSIBLE leak).
- Evidence: `_claim_batch` has no `started_at`/stale-running reclaim. `_try_lock` `except: return True` at :401-403. `_release_lock` swallows with `pass` at :409.
- Fix: Add `claimed_at` and reclaim 'running' rows older than N minutes at the start of each drain. Use a single claim RPC with SKIP LOCKED. Fail closed when the lock RPC errors.

### [MEDIUM] _update_vocabulary_metadata can null out dim_vocabulary.semantic_class / part_of_speech
- Category: correctness
- Location: services/vocabulary_ladder/asset_pipeline.py:1181-1190
- Problem: The update is unconditional. `normalize_semantic_class` returns None for unrecognised labels (config.py:905-917), so a bad P1 label writes NULL over an existing class. `pos` is likewise overwritten with None. `dim_vocabulary` is per lemma and shared across senses, so one sense's P1 clobbers the others. LLM-provided `morphological_forms` and `pronunciation` are also written to dim_word_senses without schema checks here.
- Evidence: the `update({'semantic_class': normalize_semantic_class(...), 'part_of_speech': core_asset.get('pos')})` dict has no None filter.
- Fix: Only include keys with non-None validated values, and do not overwrite a ratified class.

### [MEDIUM] Entire bundle/ package (~1.6k lines) is a flagged-off, unapplied experiment
- Category: legacy/dead
- Location: services/vocabulary_ladder/bundle/ (generator.py 575, judge.py 688, mapping.py 250, flags.py 69); hooks at asset_pipeline.py:47-48, 405-440 and exercise_renderer.py:27-30, 225-250, 637+
- Problem: `VOCAB_LADDER_BUNDLE_MODE` defaults to 'off'. The prompt rows exist only in `migrations/exercise_gen_bundle_prompts_draft.sql` ("DRAFT - NOT APPLIED"). Project memory records that the bundle failed blind review (ADR-028). Shadow mode runs the bundle call alongside the legacy path, pays for both, and discards the result: the code comment admits shadow output is only logged "and should be persisted ... by whoever wires TASK-807". `bundle/judge.py` re-implements the six per-judge filters with fallbacks to `filter_distractors` and similar, so it is a parallel judge implementation. It also uses `str.format` templates, while the generators use `render_template`.
- Evidence: `asset_pipeline.py:408-440`. `bundle/flags.py` default MODE_OFF. Tests test_bundle_*.py are the only other consumers.
- Fix: Delete the package, the flag and the renderer hooks, or move to a branch/archive. If kept, remove the shadow mode that pays for the call and drops the result.

### [MEDIUM] LADDER_QWEN_REASONING modes 'off'/'low' are rejected options still carried in 6 modules
- Category: legacy/dead
- Location: services/llm_service.py:487-520; asset_generators/prompt1_core.py:60-88, prompt2_exercises.py:43-58, prompt3_transforms.py:47-72, bundle/generator.py:62-95, bundle/judge.py:77-92, exercise_generation/judges/particle.py:71
- Problem: Each module keeps a pair of token-cap constants (right-sized vs `_REASONING_SAFE`) selected by `mode != 'off'`. 'off' (and 'low') failed blind review per llm_service's own comment (zh major-defect 31.6% vs 7.0%), and production is 'budget'. The 'off' caps are only reachable by setting an env var that is known to ship worse content. The `!= 'off'` check also silently treats 'low', 'budget' and 'on' identically.
- Evidence: llm_service.py comment block at :460-472; `_LADDER_QWEN_REASONING_DEFAULT = 'budget'`.
- Fix: Collapse to one cap helper (single source in llm_service) and drop the 'off' branch constants.

### [MEDIUM] Copy-pasted retry/repair/call scaffolding in P1, P2, P3, split base and bundle
- Category: redundancy
- Location: asset_generators/prompt2_exercises.py:143-285, prompt3_transforms.py:195-340, prompt1_core.py:265-310, _split_base.py:164-260
- Problem: P2 and P3 `_call_with_retry` / `_repair_missing_levels` are near-identical (same two-attempt loop, `missing = [lv for lv in ... if str(lv) not in raw]`, same call_llm kwargs, same scoped repair), differing only in labels. P1 and `_split_base` have their own variants with different attempt counts. When one is fixed (for example the attempt-1 partial result is discarded rather than merged) the others drift. `_LANG_ID_TO_CODE = {1:'zh',2:'en',3:'ja'}` is defined 7 times (prompt1_core:94, prompt2:63, prompt3:76, _split_base:65, asset_pipeline:54, bundle/generator:53, bundle/judge:62).
- Evidence: the files above, read side by side.
- Fix: Extract a shared `call_with_retry(missing_fn, ...)` helper and one language-code mapping in config.

### [LOW] Dead progression code in config.py duplicates the SQL RPC logic
- Category: legacy/dead
- Location: services/vocabulary_ladder/config.py:56-57 (DATABASE_LEVELS, LOCAL_LEVELS), :108 ACTIVE_FAMILIES, :193 MAX_WORD_APPEARANCES_PER_SESSION, :273/:286 MAINTENANCE_FAMILY_WEIGHTS and SESSION_PRIORITY_WEIGHTS, :298 WORD_STATES, plus functions :1011 next_active_level, :1038 get_ring_for_level, :1066 compute_p_known_overall, :1075 get_momentum_band, :1083 compute_word_state; also prev_active_level, get_levels_for_ring and DEFAULT_FAMILY_CONFIDENCE
- Problem: Each has a repo-wide reference count of 1 (the definition only; tests, scripts, routes included). ladder_service.py states progression logic is "handled atomically in SQL", so these Python mirrors can drift from the RPC and are never executed.
- Evidence: the reference-count sweep over all *.py. A grep of `.py/.js/.md` for the names finds only config.py and wiki/algorithms/vocabulary-ladder.tech.md.
- Fix: Delete them, or keep one canonical copy and a test pinning it to the RPC.

### [LOW] Other zero-reference definitions
- Category: legacy/dead
- Location: services/vocabulary_ladder/fat_seed.py:43 (P2_OPTION_LEVELS), services/vocabulary_ladder/stage_runner.py:55 (AUTHOR_STAGES)
- Problem: Constants with only their definition (count 1).
- Evidence: reference-count sweep. The `deterministic/readings.py` `build_*` functions also show count 1 but are `@register`-decorated, so they are NOT dead.
- Fix: Delete.

### [LOW] Parallel fat-seed implementation in sandbox/
- Category: redundancy
- Location: sandbox/exercise-lab/prototypes/fat_seed/ (seed_schema.py 544, render.py 460, plus 5 more files, about 2.2k lines) versus services/vocabulary_ladder/fat_seed.py
- Problem: A second schema/renderer for the same fat-seed idea, with imports into `l1_lookup`/`validators`. The sandbox's `render_all_for_seed` re-implements row building that `exercise_renderer` owns. Memory says the real fat-seed path has had no real run and its quality is unmeasured, so which copy is canonical is unclear. PLAUSIBLE that the sandbox copy is obsolete.
- Evidence: sandbox/.../pipeline.py:40 imports its own `render_all_for_seed`.
- Fix: Decide on one, delete or archive the other.

### [LOW] word_assets.prompt_version hard-coded 'v1'
- Category: correctness
- Location: services/vocabulary_ladder/asset_pipeline.py:1148
- Problem: Every stored asset records `prompt_version: 'v1'` although the templates have versions (`cfg.get('version')` is passed to call_llm elsewhere). Provenance and regression analysis cannot tell which prompt produced an asset.
- Evidence: the row dict at :1143-1153.
- Fix: Thread the template version through to `_store_asset`.

### [LOW] Index/code mirror lists must be hand-synced
- Category: maintainability
- Location: services/vocabulary_ladder/exercise_renderer.py:~203 (_CONTEXT_FREE_UNIQUE_TYPES) versus migrations/task743_context_free_exercise_caps.sql:106-117
- Problem: The Python frozenset must exactly mirror the SQL index's type array. The code comment itself warns that drift "silently reopens this bug". Nothing enforces it; no test was found that parses the migration.
- Fix: Add a test that parses the migration and asserts equality, or derive both from one constant.

### [LOW] Pickle load of the trie artifact
- Category: security
- Location: services/vocabulary_ladder/phonetic_trie/trie.py:205-215
- Problem: `pickle.load` on a file path. It is safe if the artifact stays under build-time control, and the isinstance check runs after deserialisation, so it does not protect against a malicious file. Local-only trust assumption (PLAUSIBLE risk, no remote path found in the slice).
- Fix: Document the trust boundary or use a data format (json/msgpack) for the trie.

### [LOW] _judge_p1_sentences fails open on verdict-length mismatch
- Category: correctness
- Location: services/vocabulary_ladder/asset_pipeline.py:~822-826
- Problem: When the judge returns a different count than the sentences, the function returns `([], False)` and the asset is stored unjudged with no warning recorded. The docstring declares it intentional, but no warning is persisted, so the unjudged asset is indistinguishable from a judged one.
- Fix: Append a warning such as "P1 judge skipped: length mismatch" to `validation_warnings`.

## Not found / checked clean
- No commented-out code blocks in the package.
- No HTML rendering or escaping in this package. LLM output reaches exercises.content as JSON, and frontend escaping is outside this slice (not verified).
- Language-specific branches: zh=1, en=2, ja=3 are consistently handled in the places read. `exercise_renderer.py:1401` (hant mirror, language_id != 1) is correct.
- cost_usd/budget guardrails live in llm_service and scripts, not this slice, so they were not audited here.
