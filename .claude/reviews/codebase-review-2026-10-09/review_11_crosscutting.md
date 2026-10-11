# Review 11 - cross-cutting

Secret scan (git grep of tracked files for sk-, AKIA, ghp_, xox, whsec_, JWT, private-key and postgres-URL patterns): no hits. `.env` is gitignored (.gitignore:2) and untracked. No secret-looking filenames were deleted from history.

### [MEDIUM] No application-level rate limiting
- Category: security
- Location: app.py, routes/, middleware/ (only auth.py, local_only.py)
- Problem: No Flask-Limiter or equivalent. Login, signup, LLM-backed endpoints and RPC-submission routes are unthrottled.
- Evidence: grep for limiter / rate_limit / 429 in app.py, routes, middleware, utils found nothing. Not in requirements.txt.
- Fix: Add Flask-Limiter (per-IP and per-user) on /api/auth/* and LLM-cost endpoints.

### [MEDIUM] CSP is report-only; no HSTS / nosniff / X-Frame-Options headers
- Category: security
- Location: app.py:134-170
- Problem: Only `Content-Security-Policy-Report-Only` is set (with 'unsafe-inline' script-src), and only on text/html. No Strict-Transport-Security, X-Content-Type-Options, Referrer-Policy.
- Evidence: the only `after_request` hook is _apply_csp. grep for Strict-Transport|nosniff|X-Frame in app.py, routes, middleware, utils, config.py returns nothing.
- Fix: Add an after_request that sets HSTS (when request.is_secure), nosniff and Referrer-Policy; plan the move from report-only to enforced CSP.

### [MEDIUM] Flask session cookie flags never configured
- Category: security
- Location: app.py:69 (app.secret_key), config.py
- Problem: No SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE. The app's own cookies (routes/auth.py:28-81) are set correctly (httponly, Lax, secure=request.is_secure), but any use of flask.session gets Flask defaults (no Secure flag).
- Evidence: grep for SESSION_COOKIE|PERMANENT_SESSION in .py files returns nothing. Only ProxyFix is configured (app.py:63).
- Fix: Set SESSION_COOKIE_SECURE=True (env-gated), SESSION_COOKIE_SAMESITE='Lax', or confirm flask.session is unused.

### [MEDIUM] Committed junk and build artifacts the .gitignore doesn't cover
- Category: hygiene
- Location: .cache/components/Unihan.zip (8.3 MB) and cjk-decomp.txt; .playwright-mcp/*.log (6); supabase/.temp/* (8 files, includes project-ref and pooler-url); "C:tmppytest_out.txt" (mangled filename, tracked; the same file also sits in the repo root); bash.exe.stackdump and grep.exe.stackdump; data/eval/**/*.log (about 14); sandbox/exercise-lab/reports/measure_stdout.log.
- Problem: Generated or scratch files tracked. supabase/.temp reveals the Supabase project ref and pooler host. 0 .pyc / __pycache__ tracked (good). .gitignore has no entries for .cache, .playwright-mcp, supabase/.temp, *.stackdump or *.log.
- Evidence: `git ls-files` lists them. .gitignore greps for .cache, playwright-mcp, stackdump and .temp match only `.env`, `venv/`, `__pycache__/`, `logs/llm_usage/`, `playwright-report/`.
- Fix: `git rm --cached` them and add ignore rules. Replace the .cache/Unihan.zip dependency with a download script.

### [MEDIUM] twilio.txt still tracked (prior L-2)
- Category: security
- Location: twilio.txt (24 bytes)
- Problem: A bare token-shaped string (starts "PTQ9...") is committed in the Initial Commit (0f47bed6) and still tracked. It is probably a Twilio recovery code, and it stays in history even if removed now.
- Evidence: `git ls-files` includes twilio.txt, and `git log -- twilio.txt` shows the Initial Commit.
- Fix: Confirm the value is revoked or rotated, then `git rm` it. Purge it from history only if still live.

### [MEDIUM] Repo is very large and contains unrelated projects
- Category: hygiene
- Location: Portal/ (234 tracked files: FeastOptimiser, WorkoutDojo, MusicDojo), data/eval (671 files), Corpuses/haodoo.txt (2.3 MB), raw/cedict_ts.u8 (9.6 MB)
- Problem: Pack is 212 MiB (was 256 MB, so history was only partly slimmed since L-3). venv/ no longer tracked. Portal/ looks like separate apps with their own app.py/Procfile.
- Evidence: `git ls-files | cut -d/ -f1-2 | uniq -c`, `git count-objects -vH` size-pack 212.28 MiB.
- Fix: Move Portal/ to its own repo. Consider git-lfs or external storage for eval JSON and corpora.

### [MEDIUM] Unpinned dependencies (prior M-7), plus stale or phantom pins
- Category: dependencies
- Location: requirements.txt
- Problem: 14 lines are still unpinned or loosely pinned: wordfreq, spacy, bs4, langdetect, numpy, pypinyin, pyopenjtalk, fugashi, unidic-lite, mecab-python3, ipadic, jaconv, scipy>=1.10, APScheduler>=3.10. The rest is a flat `pip freeze` of 78 entries including transitives (anyio, h11, cffi...). jieba and lemminflect are imported (services/corpus/classifier.py:156-185 and others) but not declared. `transformers` is imported by a script and not declared. Declared but not imported anywhere: azure-cognitiveservices-speech (code imports azure.cognitiveservices at services/test_generation/agents/audio_synthesizer.py, so this one is used), flask-jwt-extended and python-decouple (no imports found, PLAUSIBLE unused), pytest-cov in the runtime file.
- Evidence: requirements.txt lines; import scan of git-tracked .py excluding Portal/archive/sandbox.
- Fix: Pin everything via pip-compile with a lockfile; split requirements-dev.txt; declare jieba/lemminflect or confirm they are optional.

### [MEDIUM] Dead and orphan modules
- Category: legacy/dead
- Location: see Evidence
- Problem: 206 modules scanned under services/utils/models/middleware (static import graph; dynamic registries may hide users, so PLAUSIBLE).
- Evidence: Zero importers (14): services/payment_service.py (PaymentService; routes/payments.py:46 only mentions it in a comment), services/corpus/run_corpus_processing.py, services/corpus/tasks.py, services/exercise_generation/run_exercise_generation.py, generators/{context_spectrum,jumbled_sentence,semantic,spot_incorrect,timed_speed_round}.py, vocabulary_ladder/deterministic/{classifier_match,counter_match,definition_match,readings,tone}.py. Test-only importers (8): dual_translation/metrics.py, exercise_generation/generators/{cloze,translation}.py, test_generation/stem_rotation.py, vocabulary_ladder/asset_generators/{particle_selection,syn_ant,word_family}.py, deterministic/jumbled.py. Another 11 are imported only by scripts/sandbox/data. Several of the zero-importer files may be CLI entry points or loaded through registries (no importlib/import_module use found in services/routes besides this).
- Fix: Verify the CLI entry points and registry loaders, then delete or archive the rest. payment_service.py is the most suspect, since the routes handle Stripe separately.

### [MEDIUM] Scattered config: 126 os.environ reads outside Config; many undocumented
- Category: maintainability
- Location: services/, routes/, utils/ (126 `os.environ.get|os.getenv` hits); config.py
- Problem: Config is not the single source. About 102 distinct env vars are read; 39+ are not mentioned in Project Knowledge, wiki or README (e.g. ADMIN_ALLOW_REMOTE, DEVICE_IP_HASH_SALT, CLAUDE_CLI_*, COUNTER_*, CLASSIFIER_*, TEST_GEN_*, TOPIC_*, LLM_DEFAULT_*, OLLAMA_*, SENSE_*, VOCAB_DOJO_SESSION_SIZE). There is no .env.example (`ls` finds none).
- Evidence: grep scan above.
- Fix: Add .env.example and one generated env reference; route reads through Config.

### [LOW] Multiple LLM and Supabase client wrappers
- Category: redundancy
- Location: services/llm_service.py:191 (OpenAI client cache); routes/word_list_import.py:184-189 (own OpenAI()); topic_generation/agents/{base,explorer,gatekeeper}.py and test_generation/agents/prose_writer.py:26 (each re-declare OPENROUTER_BASE_URL); services/jev_client.py:50, claude_cli_client.py, model_arena/pricing.py:28. Supabase: services/supabase_factory.py is canonical, but create_client( is also called in services/device_service.py, payment_service.py and corpus/run_corpus_processing.py.
- Problem: At least 5 independent OpenRouter base-URL definitions and 2 direct OpenAI() constructions bypass llm_service. Memory notes llm_service freezes OPENROUTER_API_KEY at import time, so the bypasses diverge.
- Evidence: greps above (5 create_client( hits).
- Fix: Route everything through llm_service / SupabaseFactory; one OPENROUTER_BASE_URL constant.

### [LOW] Duplicated LLM-JSON-cleanup helpers and tier maps
- Category: redundancy
- Location: services/llm_output_cleaner.py:97 clean_json_response; topic_generation/agents/explorer.py:207 _parse_json_response; vocabulary/phrase_detector.py:126 _clean_json. Tier/difficulty logic in 9 files: categorical_maps.py, dictation/cap.py, dual_translation/passage_builder.py, exercise_generation/difficulty.py, exercise_generation/transcript_miner.py, model_arena/arena_service.py, test_generation/agents/prose_writer.py, test_generation/difficulty_scorer.py, tier_classifier.py.
- Problem: At least 3 JSON-fence strippers. Difficulty-to-tier bands live in many modules (memory says 3 copies must stay in step), so drift risk.
- Evidence: grep for `def .*(extract_json|parse_json|clean_json)`, and `DIFFICULTY_TO_TIER|TIER_BANDS|def .*tier.*difficulty`. Not all 9 files necessarily contain bands, PLAUSIBLE.
- Fix: Use llm_output_cleaner everywhere. Centralise the tier map in one module imported by Python, with a test asserting the DB copy matches.

### [LOW] Logging setup split
- Category: maintainability
- Location: app.py:73 and one more logging.basicConfig site (2 total)
- Problem: Two basicConfig calls (app plus one other); the second is a no-op if the first has run.
- Evidence: grep count = 2.
- Fix: Keep one in app factory; scripts call a shared helper.

### [LOW] CORS preflight handler is hand-rolled alongside flask_cors, and permits `*` in a credentialed config (prior L-6)
- Category: security
- Location: app.py:104-125
- Problem: handle_preflight reflects the Origin if `"*" in CORS_ORIGINS` and falls back to CORS_ORIGINS[0] for any other origin. With supports_credentials=True a `*` setting would allow credentialed reflection. Defaults are localhost only (config.py:53-60). config.py:22 has no SECRET_KEY default and Config.validate() fails closed (good).
- Evidence: app.py:108-125, config.py:51-60.
- Fix: Drop the hand-rolled handler (flask_cors already answers OPTIONS) or reject `*` when credentials are on.

### [LOW] Other loose files in repo root / flask run host
- Category: hygiene
- Location: root; app.py:737
- Problem: Root holds generated_tests_20251209_*.csv, batch_errors_*.json, bug-wordquiz-backdrop.png, spot_check_semantic_class.csv, dim_*_rows files, *.md plans. app.run(host='0.0.0.0', debug=Config.DEBUG) is dev-only. DEBUG defaults to False, so this is acceptable.
- Fix: Move or ignore these root files.

### [LOW] Two parallel knowledge bases
- Category: maintainability
- Location: "Project Knowledge/" (80 md files, 13 folders, index last modified 2026-02-14) vs wiki/ (180 md files)
- Problem: Overlapping docs (e.g. Project Knowledge/11-Rules-and-Conventions/04-environment-variables.md). Project Knowledge appears stale relative to the wiki, and the project CLAUDE.md names only wiki/ as owned.
- Fix: Archive Project Knowledge or mark it deprecated.

## Prior-review status
- C-1 (admin_app 0.0.0.0 + debug): FIXED. middleware/local_only.py exists, admin_app.py binds loopback and uses Config.DEBUG (admin_app.py:7, 31).
- L-1 (build artifacts committed): STILL OPEN. .cache, .playwright-mcp, supabase/.temp, stackdump, logs and the mangled pytest_out file are all tracked.
- L-2 (twilio.txt): STILL OPEN. Tracked, from the Initial Commit.
- L-3 (venv in history, 256 MB): PARTIAL. venv/ is untracked and pack is now 212 MiB, but history was not rewritten (PLAUSIBLE).
- L-6 (CORS `*` reflection): STILL OPEN (see LOW finding above).
- M-6 (rate limiting): STILL OPEN.
- M-7 (14 unpinned deps): STILL OPEN (14 counted, same number).
