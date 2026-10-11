# Review 02 - services/ top-level modules

Slice: services/*.py (not subdirectories). Read-only review, 2026-10-09. Supabase client behaviour verified against venv/Lib/site-packages/supabase/_sync/client.py (supabase==2.6.0, requirements.txt:52).
Prior review (.claude/reviews/codebase-review-2026-09-08.md): only M-6 (no app-level rate limiting) touches this slice - STILL OPEN (grep for Limiter/flask_limiter in app.py, routes, utils, config.py returns nothing).

---

### [HIGH] Shared "admin" Supabase singleton takes on the last-logged-in user's JWT
- Category: security / correctness
- Location: services/auth_service.py:51,108,293,323 (with services/supabase_factory.py:45, app.py:187-188)
- Problem: AuthService runs `sign_in_with_otp`, `verify_otp`, `refresh_session` and `mint_session_for_user` on the process-wide service-role client from `get_supabase_admin()`. supabase-py registers `_listen_to_auth_events`, which on SIGNED_IN / TOKEN_REFRESHED / SIGNED_OUT replaces `options.headers["Authorization"]` with the user's access token and rebuilds postgrest. Every later `get_supabase_admin()` caller (about 500 call sites, e.g. test_intro_service, test_service, llm_service._log_llm_call) then runs as that user under RLS, not as service_role, until the token expires or the next login. The same client is also `app.supabase_service` and is used by DeviceService.
- Evidence: venv/.../supabase/_sync/client.py:293-304 sets `self.options.headers["Authorization"] = _create_auth_header(access_token)` with the session token; `AuthService.__init__` takes `get_supabase_admin()` (auth_service.py:25) and calls `verify_otp` on it (auth_service.py:108). The comments at auth_service.py:153-159 and :236-239 already document RLS silently zeroing rows on the anon client, but the admin client has the mirror-image problem.
- Fix: Do auth-flow calls on a throw-away client (`create_client(url, anon_key)` per call, or a dedicated auth-only client). Never call `verify_otp` / `refresh_session` / `sign_in_*` on the shared service-role client. Assert `Authorization` is still the service key in a startup test.

### [MEDIUM] PaymentService is dead, broken, and the Stripe flow has no crediting path
- Category: legacy/dead / correctness
- Location: services/payment_service.py:1-409; routes/payments.py:24-64
- Problem: No code instantiates `PaymentService` / `get_payment_service` / `handle_successful_payment` / `consume_tokens` (grep over repo excluding venv: only a comment in routes/payments.py:45). There is no Stripe webhook route and no `construct_event` / `payment_intent.succeeded` handling anywhere, so a successful `/api/payments/create-intent` payment never credits tokens. The class would not work if wired: it reads `package.price_cents` / `package.tokens` as attributes while `Config.TOKEN_PACKAGES` values are dicts (config.py:288-300), so `create_payment_intent` / `get_token_packages` raise AttributeError (swallowed into 'Failed to create payment intent').
- Evidence: payment_service.py:208,215,222-223,324-327 attribute access vs config.py:289 dict literal; `grep -rn "handle_successful_payment"` finds no caller. The frontend does not call `/api/payments/*` either (no JS match), so this is latent, not live.
- Fix: Either delete payment_service.py and keep routes/payments.py as the single stub, or finish it: add a signature-verified webhook (`stripe.Webhook.construct_event` with STRIPE_WEBHOOK_SECRET), call a DB-side atomic credit RPC, and drop the duplicate token ledger.

### [MEDIUM] payment_service token logic is wrong even if it were revived (free tokens unlimited, first-call-of-day shows 0)
- Category: correctness
- Location: services/payment_service.py:91-105, 156-167, 274-290
- Problem: (a) `consume_tokens` computes `free_tokens_available` but only decrements `purchased_tokens`; free tokens are never recorded as spent, so DAILY_FREE_TOKENS is re-granted on every call (unlimited free usage). (b) `free_tokens_today` is derived from `last_free_date` read before `_award_daily_free_tokens` ran, so the first request of each day reports 0 free tokens. (c) Credit is read-modify-write (noted in a comment at :274-277) with a non-atomic idempotency pre-check. (d) The user's token system actually lives in RPCs (`get_token_balance`, `grant_daily_free_tokens`, auth_service.py:171,195), so this is a second, divergent ledger.
- Evidence: lines above. Parallel implementation of the same concept.
- Fix: Delete, or replace with the RPC-backed ledger and an atomic `credit_tokens(payment_intent_id, ...)` RPC with a unique constraint on payment_intent_id.

### [MEDIUM] call_llm treats ClaudeCliError as a malformed-JSON error: bypasses retry ladder and multiplies subprocess calls
- Category: correctness
- Location: services/llm_service.py:1082 (`except (json.JSONDecodeError, RuntimeError)`), services/claude_cli_client.py:109, services/llm_service.py:822-865,1654-1720
- Problem: `ClaudeCliError` subclasses `RuntimeError`. A CLI timeout (default 600 s), non-zero exit or API error raised inside `_make_one_call` is caught by call_llm's `except (JSONDecodeError, RuntimeError)`, which routes it to `_repair_malformed_json` (a second CLI call, with a "your previous reply was not valid JSON: Claude CLI timed out" prompt). When the repair also fails it `raise error`, re-raising the ClaudeCliError out of the tenacity-wrapped function, which is in `_retryable_types()`, so tenacity retries the whole thing up to 3 times: up to 6 subprocess calls (up to ~60 minutes at the 600 s timeout) per logical call, and the "repair" turn is nonsense for a transport failure.
- Evidence: `class ClaudeCliError(RuntimeError)`; llm_service.py:1082 catches RuntimeError generically; `_retryable_types()` adds ClaudeCliError at :842-857.
- Fix: Catch ClaudeCliError before the generic RuntimeError clause and re-raise it directly (or give empty-content a dedicated exception type instead of bare RuntimeError).

### [MEDIUM] Failed LLM calls (API errors, exhausted retries, timeouts) are never written to llm_calls
- Category: correctness / maintainability
- Location: services/llm_service.py:1065-1100 (call_llm), :1269-1380 (_make_one_call)
- Problem: `_log_llm_call` is only invoked after a successful `_make_one_call` return (or in repair paths). A 4xx/5xx, timeout or exhausted tenacity retry raises with no row and no cost hook, so spend on failed/billed-but-errored requests and failure rates are invisible in the ledger the project relies on for budget ceilings.
- Evidence: no try/except/finally around `_make_one_call` in call_llm other than the JSON/RuntimeError branch that does not log the primary failure; only `_repair_malformed_json` logs its own failure.
- Fix: Wrap the primary call in try/except that logs `parsed_ok=False, error=str(exc)` (latency known) then re-raises.

### [MEDIUM] Trusted-device token rotation is check-then-act (race) and can false-positive "theft"
- Category: security / correctness
- Location: services/device_service.py:150-216
- Problem: `restore_from_token` SELECTs the row, then INSERTs the next generation and only afterwards marks the presented row 'rotated' (three separate requests, no conditional update). Two concurrent restores with the same cookie (two tabs, a retry after a lost response) both pass the `revoked_at` check and both mint a new valid chain; the loser's later request carrying the now-rotated token trips reuse detection and revokes every device of the user. Also if `_get_user_email` fails (line 219-222) the old token is already rotated and the new one is never returned: the user is locked out.
- Evidence: lines 150-157 read, 212 insert, 216 `_mark_revoked(row['id'], ...)` with `.eq('id', row_id)` and no `revoked_at IS NULL` guard.
- Fix: Do the rotation in one SQL RPC (UPDATE ... SET revoked_at, revoked_reason='rotated' WHERE id=$1 AND revoked_at IS NULL RETURNING ...; insert new row only if a row was updated), and look up the email before rotating. Consider a short grace window for the immediately-previous token.

### [MEDIUM] Drill submissions are client-scored with no cap and an unbounded per-item RPC loop
- Category: security / correctness
- Location: services/classifier_drill_service.py:93-160, services/counter_drill_service.py:107-144 (route validation at routes/classifier_drill.py:73-97)
- Problem: `correct_items` / `total_items` come straight from the client and are fed to `process_*_drill_submission` (ELO update). The route only checks `0 <= correct <= total` and total > 0 - no upper bound and no tie to a server-issued session, so a client can claim e.g. 1,000,000/1,000,000 correct. `item_results` is an unbounded list and each entry triggers one `update_classifier_mastery` RPC (N+1 round trips, ~65 ms each per project notes), so a large list is both an abuse vector and a latency problem.
- Evidence: classifier_drill_service.py:142-156 loop with no length cap; routes check at classifier_drill.py:76-79.
- Fix: Cap `total_items` to the served session size (`count` <= 50) and cap/dedupe `item_results`; ideally issue a session token in `get_session` and grade server-side; batch mastery updates into one RPC.

### [MEDIUM] Practice attempt recording: client-asserted correctness, TOCTOU first-attempt detection, lost-update counters
- Category: correctness / security
- Location: services/practice_session_service.py:450-593
- Problem: `is_correct` is taken from the client and drives BKT, FSRS and weekly progress. First-attempt detection (SELECT exercise_attempts ... then INSERT) is a check-then-act, so a double-submit records two "first" attempts and double-applies BKT. `attempt_count`/`correct_count` on `exercises` are read-modify-write (lines 536-539), losing concurrent updates. The `.single().execute().data` lookup at :487-495 raises on zero rows in supabase-py rather than returning None, so the `if not exercise: return {'error': 'Exercise not found'}` branch is effectively unreachable (a bad id becomes a generic 500).
- Evidence: lines 487-495, 505-513, 536-539.
- Fix: Move attempt insert + first-attempt flag + counter increments into one RPC (INSERT ... ON CONFLICT, `attempt_count = attempt_count + 1`); use `.maybe_single()`; grade server-side where the answer key is available.

### [MEDIUM] Unbounded history reads silently truncated at PostgREST's 1000-row cap
- Category: correctness
- Location: services/test_service.py:480-488 (`_compute_daily_load`), :771-775 (`get_user_elo_summary`)
- Problem: Both pull a user's entire `test_attempts` history with no limit/pagination. PostgREST returns at most 1000 rows by default, so after 1000 attempts `latest_by_test` misses old tests (they get re-recommended as "new") and `tests_taken` in the ELO summary stops growing / reports wrong counts. Each daily-load computation also transfers the full history.
- Evidence: queries end in `.order('created_at', desc=True).execute()` with no `.limit()`/`.range()`.
- Fix: Aggregate in SQL (RPC / view: latest attempt per test, count per (language,type)), or paginate.

### [LOW] mark_daily_test_complete accepts any test_id and uses read-modify-write on an array
- Category: correctness
- Location: services/test_service.py:719-745
- Problem: `test_id` is not checked against the day's `test_ids`, so any id can be appended to `completed_test_ids` (inflating `completed`, and `all_complete` becomes true early). Concurrent completions can overwrite each other. `.single()` raises when no row exists, making the `if not record.data` branch dead.
- Fix: Validate membership against `test_ids[*].test_id`; use an RPC with `array_append` + `NOT (x = ANY(arr))`.

### [LOW] Dead AIService surface: only `moderate_content` is used
- Category: legacy/dead
- Location: services/ai_service.py:1-326
- Problem: File header says LEGACY. Callers exist only for `moderate_content` (routes/tests.py:62) and `ModerationServiceError`. `generate_transcript`, `generate_questions`, `_generate_single_question`, `_validate_question_structure`, `get_starting_elo`, `generate_audio`, `reload_prompts`, `get_available_prompts`, `get_prompt_preview` have no callers (scripts/batch_generate_to_json.py defines its own `_generate_*`; scripts/run_test_generation.py only monkeypatches names). It also builds its own boto3 R2 client (:55-63, a third R2 client alongside services/r2_service.py and test_generation's audio synthesizer) and reads `/prompts/*.txt` via PromptService, keeping the file-prompt loader alive.
- Evidence: grep for `.generate_transcript(`, `.generate_questions(`, `._validate_question_structure(`, `.get_starting_elo(`, `.reload_prompts(`, `.get_prompt_preview(` outside ai_service.py and tests: none.
- Fix: Reduce to a small `ModerationService` (OpenAI moderations call only) and delete the rest plus prompts/*.txt and `PromptService`.

### [LOW] Dead R2Service methods and an SSRF-shaped helper
- Category: legacy/dead / security
- Location: services/r2_service.py:128-195,224-264,285-388 (notably :325-356 `upload_from_url`)
- Problem: `download_audio`, `delete_audio`, `file_exists`, `list_audio_files`, `get_file_info`, `upload_from_url`, `get_bucket_stats` have no callers (the other `delete_audio` in test_generation/agents/audio_synthesizer.py:343 is separate). `upload_from_url` does `requests.get(url, stream=True)` with no timeout, no scheme/host allow-list and loads the whole body (`response.content`) - an SSRF / memory-exhaustion primitive if it were ever wired to user input. `Key=filename` is used unsanitised everywhere (no `..`/slash validation, though S3 keys are not path-traversal-prone). `_initialize_client` performs a live `list_objects_v2` at construction (blocking network call at app startup) and swallows failure, leaving `r2_client=None` so every upload logs and returns False silently.
- Evidence: grep for each method shows no call sites; r2_service.py:340 `requests.get(url, stream=True)`.
- Fix: Delete unused methods; keep `upload_audio` + `get_audio_url`. If URL fetch is needed, add timeout, size cap, https + host allow-list.

### [LOW] app.py and ServiceFactory each construct their own R2Service / AI service
- Category: redundancy
- Location: services/service_factory.py:14-55, app.py:210,217,241
- Problem: `ServiceFactory` provides lazy `r2_service`, `prompt_service`, `openai_service`, yet app.py also builds `R2Service(Config)` directly (app.py:217) and a separate `PromptService()` (app.py:233) whose result (`app.prompt_service`) is never read (grep for `app.prompt_service` / `current_app.prompt_service`: none). `ServiceFactory.openai_service` is misnamed (can be OpenRouter) and the only ServiceFactory consumer is app.py:18. supabase_factory vs service_factory are different concerns but the naming overlaps.
- Fix: Pick one construction path; delete `app.prompt_service`.

### [LOW] Five-plus prompt loaders; file-based PromptService is legacy
- Category: redundancy / maintainability
- Location: services/prompt_service.py:8-96 (DB loaders) and :99-158 (file loader); other loaders in services/test_generation/database_client.py:193,463,565 and in many modules that read `prompt_templates` directly (judges/base.py, vocabulary/pipeline.py, vocabulary_ladder/asset_pipeline.py, topic_generation/database_client.py, ...)
- Problem: `get_template_config` / `get_template_text` filter `is_active=True`, ordering by version; other loaders (per the known project fact) ignore `is_active`, so deactivating a row is not a reliable kill switch. The file-based `PromptService` (reads `prompts/*.txt`, used only by dead AIService paths and scripts/batch_generate_to_json.py) is a separate mechanism.
- Fix: Route all DB prompt reads through prompt_service helpers; delete the file loader with AIService.

### [LOW] Dead / legacy methods in test_service and practice_session_service
- Category: legacy/dead
- Location: services/test_service.py:70-120 (`get_tests`), :200-209 (`update_audio`), :215-278 (`record_attempt`); services/practice_session_service.py:1289-1352 (`get_or_create_daily_session`)
- Problem: No non-test callers (`record_attempt` hit in routes/vocab_dojo.py is `LadderService.record_attempt`, a different class). `TestService.record_attempt` inserts through the anon client with hard-coded `user_elo_before/after=1200`, a `test_mode` column the rest of the code replaced with `test_type_id`, and trusts client `is_correct`: stale and misleading. `get_or_create_daily_session` uses `date.today()` (server-local date, contradicting ADR-022 elsewhere) and is unused; `mark_exercise_complete` is a documented no-op still routed from routes/exercises.py:166.
- Fix: Remove after confirming no external scripts use them; drop the "backwards compatibility" re-exports at test_service.py:19-26 if unused.

### [LOW] Claude CLI subprocess inherits the full environment (service-role key, Stripe key, etc.)
- Category: security
- Location: services/claude_cli_client.py:174-183
- Problem: `_child_env` only removes ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN; everything else (SUPABASE_SERVICE_ROLE_KEY, STRIPE_SECRET_KEY, R2 keys, OPENROUTER_API_KEY) is passed to `claude -p`. Tools and MCP are disabled, but user-level hooks/plugins still load in the child and see the secrets. Also, the system prompt (including any caller `system` message) goes on argv (`--system-prompt`, :331), subject to the ~32k Windows command-line limit.
- Evidence: `env = dict(os.environ)` then pop of two vars.
- Fix: Build a minimal allow-list env (PATH, HOME/USERPROFILE, APPDATA, SystemRoot, proxy vars); pass long system prompts via a file/stdin.

### [LOW] llm_service logs full prompts and raw responses to an unbounded daily CSV and to llm_calls.raw_response
- Category: security / maintainability
- Location: services/llm_service.py:530-570 (`_log_llm_call_csv`), :776-808
- Problem: Every call writes `input_text` and `output_text` in full to logs/llm_usage/llm_calls_YYYY-MM-DD.csv (no rotation/retention) and `raw_response` to the DB. Pipelines that include user-submitted text (dual-translation answers, test-gen topics from users) land in plaintext on disk. The CSV `provider` column logs the argument (often None) instead of the resolved provider.
- Fix: Make full-text CSV logging opt-in (env flag) or truncate; add retention; log resolved provider.

### [LOW] Superseded "frozen key" trap still described in comments; module constants remain
- Category: legacy/dead
- Location: services/llm_service.py:65,134-139; services/jev_client.py:26-29
- Problem: `_resolve_provider` already re-reads `OPENROUTER_API_KEY` at call time (the known "freezes at import" issue is fixed in this file; the module constant is only a fallback). jev_client's docstring still claims llm_service freezes the key. Other modules that copy `llm_service.OPENROUTER_API_KEY` at import time are outside this slice and should be checked.
- Fix: Update docstring; delete the module-level constant or alias it to a function.

### [LOW] llm_service accumulated experiment scaffolding: dead modes, kill-switch envs, duplicated constants
- Category: maintainability / legacy
- Location: services/llm_service.py:76 vs services/claude_cli_client.py:75 (duplicate `CLAUDE_CLI_BASE_URL`); :335-520 (reasoning modes `on/off/low/budget`); :991-1004 (`LLM_AB_NO_PRICE_ROUTING`, `LLM_AB_NO_DISABLE_REASONING`); :67-80 (`OLLAMA_MODELS` with only a 'default' key)
- Problem: ~190 lines of comment-driven flag logic where the rollback modes `off`/`low`/`on` are experiment leftovers and the `LLM_AB_*` switches are marked "diagnostic-only ... remove once confirmed"; `OLLAMA_MODELS` is only read in `_resolve_model`. `_log_llm_call(...)` is called with ~25 repeated kwargs in 4+ places (lines 1103-1280), a recurring drift risk. `get_client` mutates `_clients` without a lock (benign duplicate-client race).
- Fix: Collapse call_llm's logging into a helper taking the `_CallResult`; delete the A/B kill switches and unused modes once ADR-028 is closed; import `CLAUDE_CLI_BASE_URL` from one place.

### [LOW] task_runner: root-logger handler captures all threads, prune can delete running tasks, unsynchronised dict
- Category: correctness / security
- Location: services/task_runner.py:46-96
- Problem: `QueueLogHandler` is attached to the root logger for the life of each task, so it captures log lines from every thread (including unrelated web requests: emails, user ids) and these are streamed by the admin SSE endpoint. `_prune_old_tasks` deletes tasks older than 3600 s regardless of status; a still-running task then hits `KeyError` at `TASKS[task_id][...]` in `target()` (and again inside the `except`, killing the thread with a stack trace). `TASKS` is mutated/iterated from many threads with no lock (`RuntimeError: dictionary changed size`).
- Fix: Filter the handler by thread (`record.thread == threading.get_ident()` or a `threading.local` check); only prune non-running tasks; add a lock.

### [LOW] model_health: advisory lock via PostgREST is session-scoped over pooled HTTP connections; probe failure reports ok=True
- Category: correctness
- Location: services/model_health.py:223-248, :57-137
- Problem: `pg_try_advisory_lock` / `pg_advisory_unlock` via two separate PostgREST RPC calls may land on different backend connections, so the lock is not reliably held or released (PLAUSIBLE; same pattern as the study-plan lock noted in project memory). A failed `/models` fetch or unreadable prompt_templates yields `ok: True, error: ...` by design, so dashboards that check only `ok` read healthy. Only prompt_templates rows are probed - code defaults (`LLM_DEFAULT_MODEL`, `SENSE_MODEL_*`, llm_service.py:83-91) can rot unseen (the file's own comment acknowledges this for LLM_DEFAULT_MODEL).
- Fix: Use `pg_try_advisory_xact_lock` inside a single RPC that does the work, or a lock table with TTL; surface `error` as a distinct status; add the code-default slugs to the probe.

### [LOW] Auth service: user enumeration, raw exception text to clients, PII in logs, no OTP attempt limiting, logout does not revoke
- Category: security
- Location: services/auth_service.py:64-84,105,120,137-143,247-262; routes/auth.py:116-136
- Problem: `send_otp(is_registration=False)` returns `USER_NOT_FOUND` / "No account found" (account enumeration), and the generic branch returns `f'Failed to send OTP: {str(e)}'` (internal/provider error text) to the client via routes/auth.py:130. Emails are logged at INFO (:105,:120). `verify_otp` has no local attempt limiting (M-6, still open). `logout` calls `self.supabase.auth.sign_out()` on the shared anon client, which holds no user session, so it does not revoke the user's refresh token server-side (only the cookie is cleared by the route).
- Fix: Return a uniform response for send-otp; map errors to fixed messages; hash/mask emails in logs; add flask-limiter on send-otp/verify-otp; revoke via `admin.sign_out(jwt)` or by deleting the refresh session.

### [LOW] device_service: IP-hash salt can degrade to empty, own admin-client fallback duplicates the factory
- Category: security / redundancy
- Location: services/device_service.py:43-47, 96-101
- Problem: `_hash_ip` uses `Config.DEVICE_IP_HASH_SALT or Config.SECRET_KEY or ''`; with no salt configured the stored hash is a plain SHA-256 of the IPv4 address (trivially reversible). `DeviceService.__init__` falls back to `create_client(os.getenv(...), os.getenv(...))` with possibly-None args, a second client-construction path beside SupabaseFactory (only app.py:188 uses it, always passing the factory client).
- Fix: Fail startup if no salt/secret; remove the fallback client.

### [LOW] Duplicated sentinel-test lookup modules (classifier vs counter drill)
- Category: redundancy
- Location: services/classifier_drill_service.py:17-48,93-160; services/counter_drill_service.py:30-61,107-144
- Problem: `_fetch_sentinel_test_id`, the `_sentinel_id_cache`, the submit RPC wrapper and the exception-payload workaround (`e.json()` / `e.args[0]` treated as success) are copy-pasted; any fix (e.g. the unbounded loop above) must be made twice. `.single()` at :40 raises rather than returning None, so the "sentinel not found" log is unreachable.
- Fix: Extract a shared `drill_common` helper parameterised by RPC names and sentinel slugs.

### [LOW] Type-unstable DimensionService.get_all_test_types and never-refreshed caches
- Category: maintainability / correctness
- Location: services/dimension_service.py:108-140, class-level caches :32-36
- Problem: `get_all_test_types` returns a list of dicts when metadata is cached but a `(code_to_id, id_to_code)` tuple on the fallback path; callers such as test_service.get_user_elo_summary iterate it as a list of dicts. Caches are class-level mutable dicts populated once at startup and never invalidated (new languages/test types need a restart); `initialize` swallows all errors leaving empty caches with only an ERROR log.
- Fix: Return a single type; add TTL/refresh or an explicit reload hook.

### [LOW] clean_json_response picks the wrong span when prose contains brackets before the JSON
- Category: correctness
- Location: services/llm_output_cleaner.py:97-146
- Problem: When both `[...]` and `{...}` exist, whichever delimiter appears first wins. A preamble such as `Note [see below]: {"a": 1}` yields `[see below]`, which then fails `json.loads` and triggers a paid repair turn. `text.replace('```', '', 1)` also mangles content containing backticks.
- Fix: Try `json.JSONDecoder().raw_decode` at each candidate start and take the first that parses.

### [LOW] jev_client holds the global concurrency semaphore while sleeping on backoff
- Category: correctness
- Location: services/jev_client.py:119-170
- Problem: The `with _semaphore:` block contains the retry loop and `_sleep(...)` (up to 20-30 s per wait, 4 retries), so rate-limited calls hold a slot while idle and starve other judge threads. Failed calls (non-2xx after retries) are also not logged to llm_calls.
- Fix: Release the semaphore during sleeps; log failures.

### [LOW] timing.stage uses wall clock and an unsynchronised shared dict
- Category: correctness
- Location: services/timing.py:34-43
- Problem: `time.time()` is not monotonic (clock adjustments produce negative/odd durations) and `bucket[name] = bucket.get(name, 0.0) + ...` races when the same bucket is used from the pipeline's thread pool.
- Fix: Use `time.perf_counter()`; guard with a lock or per-thread buckets.

---
Verified-clean / no issue found in slice: pitch_accent_service, furigana_service, pinyin_service (no security-relevant findings on a scan; not read line by line), batch_prompting (bounded recursion, correct halving; only `validate()` exceptions are uncaught at batch_prompting.py:~190), categorical_maps/tier_classifier (DIFFICULTY_TO_TIER is one of three copies: categorical_maps.py:273, services/dictation/cap.py:27, transcript_miner.py:126 - pinned by tests/test_difficulty_to_tier_matches_db.py).
No subprocess shell injection in claude_cli_client (argv list, shell=False, prompt via stdin). No Stripe webhook exists, so no signature-verification bug to report - the absence is the finding above.
