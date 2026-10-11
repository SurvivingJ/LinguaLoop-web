# Whole-Codebase Review — LinguaLoop WebApp — 2026-10-09

Method: 11 parallel Sonnet reviewers, one per slice, read-only. The orchestrating session then
verified the top findings directly. Two CRITICAL findings come from **read-only live catalog
queries** against the production Supabase project (`kpfqrjtfxmujzolwsvdq`). They are not
inferences from migration files.

Per-slice detail with full evidence and fix notes: `.claude/reviews/codebase-review-2026-10-09/review_NN_*.md`

| Slice | File | Findings |
|---|---|---|
| Routes, app, middleware, utils, models | review_01_routes.md | 27 |
| Top-level services | review_02_services_core.md | 27 |
| vocabulary_ladder | review_03_vocab_ladder.md | 17 |
| exercise / test / topic generation | review_04_generation.md | 22 |
| DT, vocabulary, corpus, IRT, word-list import, curation | review_05_services_other.md | 18 |
| Frontend JS + templates | review_06_frontend.md | 13 (1 refuted, below) |
| SQL migrations | review_07_migrations.md | 13 |
| scripts / sandbox / Corpuses | review_08_scripts.md | 16 |
| tests | review_09_tests.md | 9 |
| Portal/ | review_10_portal.md | 16 |
| Cross-cutting (secrets, deps, dead modules) | review_11_crosscutting.md | 15 |

About 180 distinct findings after de-duplication.

**Test suite:** 3241 passed, 1 failed, 2 skipped (pytest, e2e excluded). Vitest: 129 passed.
The failing test is stale: `tests/test_prompt_split_l4_l8.py::test_unregistered_prompt_version_is_refused_not_guessed`.

**Refuted during verification:** the frontend reviewer reported routes rendering templates that do
not exist (recipes, planner, workouts…). Every `render_template` name in `routes/` and `app.py` has a
file in `templates/`. Those names came from `Portal/`. The finding is dropped.

---

## CRITICAL (verified live)

### C-1. 32 public tables have RLS disabled, and `anon` has full SELECT/INSERT/UPDATE/DELETE on them
Live `pg_class.relrowsecurity = false` and `has_table_privilege('anon', …)` are true for all four
verbs. The affected tables are:

`prompt_templates`, `dt_submission`, `dt_grade`, `dt_card`, `dt_card_review`, `dt_error_instance`,
`dt_error_profile_entry`, `dt_passage`, `dt_passage_reference`, `dt_rubric_version`,
`dt_taxonomy_version`, `user_classifier_mastery`, `exercises`, `word_assets`, `llm_calls`,
`generation_queue`, `generation_review_queue`, `generation_stage_timings`, `production_queue`,
`test_generation_config`, `test_generation_runs`, `topic_generation_runs`, `topics`, `categories`,
`corpus_sources`, `corpus_collocations`, `corpus_style_profiles`, `dim_classifiers`,
`dim_classifier_noun_pairs`, `dim_classifier_distractor_groups`,
`question_type_distributions_by_tier`, `script_conversion_overrides`.

- **Impact:** anyone holding the project's anon key can read every learner's DT submissions,
  grades and mastery. They can also rewrite `prompt_templates`, which steers every generation
  pipeline, and delete `exercises` and `word_assets`. `llm_calls` contains full prompts and
  responses. The anon key is a public-by-design credential. The GitHub repo
  `SurvivingJ/LinguaLoop-web` is publicly reachable, and tracked `supabase/.temp` holds the project
  ref and pooler URL. The app does not currently ship the anon key to browsers. That is the only
  thing standing between this and open exploitation.
- **Fix:** `ALTER TABLE … ENABLE ROW LEVEL SECURITY` on all 32 tables. Add owner-scoped policies on
  user tables (`dt_submission`, `dt_grade`, `dt_card*`, `dt_error_*`, `user_classifier_mastery`).
  Add read-only policies on content tables only where the browser genuinely needs them. Run
  `REVOKE ALL … FROM anon` on internal tables (`prompt_templates`, `llm_calls`, `*_queue`,
  `*_runs`, `*_config`). The backend uses the service role, so RLS does not break it. Also see H-1.

### C-2. `process_stripe_payment` lets any caller mint unlimited tokens for any user
Live definition: `SECURITY DEFINER`, no `SET search_path`, no `auth.uid()` check. `anon` and
`authenticated` both hold EXECUTE. It takes `p_user_id` and `p_tokens_to_add` straight from the
caller. Its only idempotency key is a caller-chosen `p_payment_intent_id`.

- **Fix:** `REVOKE EXECUTE ON FUNCTION process_stripe_payment(...) FROM PUBLIC, anon, authenticated;`
  and add `SET search_path = public, pg_temp`. Payments are not wired up (see M-PAY), so nothing
  legitimate calls it today.

### C-3. 23 more SECURITY DEFINER RPCs take `p_user_id`, are anon-executable and never check `auth.uid()` (verified live)
Live query: these are `prosecdef`, `has_function_privilege('anon', …, 'EXECUTE')`, with no
`auth.uid()` in the body:

- **Writes:** `apply_study_plan_template`, `build_daily_session`, `compute_weekly_plan_persist`,
  `record_session_progress`, `update_classifier_mastery`, `calibration_build_items`,
  `calibration_record_answer`, `calibration_discard_unanswered`.
- **Reads of another user's state:** `compute_weekly_plan_load_signals`, `get_recommended_test(s)`,
  `get_replay_tests`, `get_vocab_recommendations`, `get_word_quiz_candidates`,
  `get_classifier_drill_session`, `get_counter_drill_session`, `get_daily_free_test_limit`,
  `get_test_token_cost`, `max_unlocked_tier`, `plan_local_date`, `is_admin`, `is_moderator`.
- `get_classifier_drill_session`, `max_unlocked_tier` and `update_classifier_mastery` also lack
  `SET search_path`.
- Advisory-lock RPCs (`pg_try_advisory_lock_for_*`) and `irt_apply_calibration` are
  anon-executable per the migration reviewer. These were not re-queried live.
- **Fix:** one migration that `REVOKE EXECUTE … FROM PUBLIC, anon, authenticated` on every
  internal RPC that only the Flask backend calls with the service role. For any RPC the
  browser-facing JWT path really calls, add `IF p_user_id IS DISTINCT FROM auth.uid() AND
  auth.role() <> 'service_role' THEN RAISE …`.
  Also flip the default: `ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;`

---

## HIGH

### Security
- **H-1. The shared service-role client gets re-authenticated as the last user to log in.**
  `services/auth_service.py:51,108,293,323` runs `verify_otp` and `refresh_session` on the singleton
  from `get_supabase_admin()`. supabase-py's `_listen_to_auth_events` (`supabase/_sync/client.py:293-304`)
  swaps that client's `Authorization` header to the user's JWT on SIGNED_IN and TOKEN_REFRESHED.
  After any login, about 500 "admin" call sites run as that user under RLS. That produces silent
  empty reads, failed writes and cross-user `auth.uid()` attribution. **Fix:** use a separate,
  throwaway client (or `create_client(..., ClientOptions(persist_session=False, auto_refresh_token=False))`)
  for all GoTrue operations, and never call `.auth.*` on the service singleton. *Verified.*
- **H-2. Unbounded, unthrottled LLM spend from any logged-in user.** `routes/word_list_import.py:211-213`
  spawns a thread per request with no per-word cap, quota or rate limit. Its results land in
  global shared dimension tables. `routes/dual_translation.py:164` has no length cap on
  `reproduction`. Failed grades are never counted against the budget gate, and Tier-0 difflib is
  quadratic.
- **H-3. Loopback-only admin has no CSRF or Host check.** `middleware/local_only.py:76`. It accepts
  `get_json(force=True)` and a no-body wipe POST, so a malicious web page can drive it from the
  developer's browser. ProxyFix trusts `X-Forwarded-For`, so binding wider would let a remote
  caller spoof 127.0.0.1.

### Correctness (silent failure)
- **H-4. Judges fail open on production regen paths.** The nightly drain, admin regen and top-up
  (`services/vocabulary_ladder/queue_drain.py:238-330`, `routes/vocab_admin.py:62-85`,
  `routes/admin_local.py:1424`) run without `batch_mode()`. They then *replace live exercises*
  with unjudged ones. Same for `run_vocabulary_batch` and `run_collocation_batch`
  (`services/exercise_generation/run_exercise_generation.py:12`).
- **H-5. Swallowed persistence errors report success.** These include
  `asset_pipeline._store_asset` (`asset_pipeline.py:1098-1165`), exercise-gen `_batch_insert`
  (`orchestrator.py:238`) and the test-gen orchestrator. That orchestrator marks a queue item
  *completed* with 0 tests on exception and never retries it (`test_generation/orchestrator.py:440`).
- **H-6. The guard against overwriting a valid asset fails open** when its SELECT errors
  (`asset_pipeline.py:1117-1142`).
- **H-7. Queue claims have no lease or reaper.** This affects the test-gen queue
  (`test_generation/database_client.py:178`) and the ladder queue (`queue_drain.py:175-207`).
  A crash or `JudgeUnavailable` strands rows in 'processing'/'running' forever. This matches the
  memory note that `generation_queue` has been jammed since 2026-08-21.
- **H-8. `scripts/build_classifier_dictionary.py:556-560` deletes all zh classifier rows and then
  inserts them**, with no transaction. It writes by default.

### Broken legacy (crashes if run)
- **H-9.** `Corpuses/ingest_corpus.py:40,73` imports the missing `services.corpus.pack_service`
  and writes dropped `pack_*` tables. `scripts/apply_task734_en_prompt_fixes.py:169,358` opens the
  deleted `services/mystery_generation/orchestrator.py`.
  `services/exercise_generation/run_exercise_generation.py:136` calls an undefined
  `run_grammar_batch`, which raises NameError.

### Portal (separate apps, publicly deployed)
- **H-10.** `Portal/Library/app.py:20-200` exposes write and delete APIs with no auth.
  `/api/proxy-image` (`:211-224`) is an open SSRF and content proxy.

---

## MEDIUM

### Security
1. Client-asserted scores and `passed` flags are trusted. This inflates ELO and mastery
   (`routes/tests.py:647,740`, `classifier_drill`, `counter_drill`, `vocab_dojo.py:256,330`,
   `practice_session_service.py:450-593`). Drill `item_results` is unbounded, with one RPC per item.
2. Unauthenticated public test endpoints return the answer key (`routes/tests.py:249,1012`).
   The auth decorators there are commented out.
3. Generated `question.explanation` goes unescaped into innerHTML (`templates/test.html:667`,
   `static/js/session/players/reading_listening.js:311`). The access JWT sits in localStorage
   (`base.html:74,140,556`), so this XSS can steal sessions.
4. SSRF in admin corpus URL ingest (`routes/corpus.py:36`, `services/corpus/ingestion.py:60`).
   Redirects are followed, there is no host allow-list and no size cap.
5. Still no application rate limiting anywhere (prior M-6). OTP verification has no attempt
   limit. `USER_NOT_FOUND` enables user enumeration.
6. CSP is report-only with `'unsafe-inline'`. There is no HSTS, nosniff or Referrer-Policy
   (`app.py:134-170`). `SESSION_COOKIE_*` flags are never set.
7. Trusted-device rotation is check-then-act (`device_service.py:150-216`). A concurrent replay
   revokes all of a user's devices. The IP-hash salt can be empty.
8. Stale `process_test_submission` overloads (7-arg and legacy) remain GRANTed to `authenticated`.
   The REVOKE covers only the 8-arg signature. The canonical definition is
   `migrations/sec_submission_rpcs_auth_gate.sql:47`, which supersedes the partG and task704 files.
9. `twilio.txt` is still tracked with a token-shaped value since the initial commit (prior L-2).
   Confirm it is revoked, then remove it.

### Correctness
10. **M-PAY.** Payments are half-built. `routes/payments.py:26` creates Stripe PaymentIntents, but
    no webhook or fulfilment exists. `services/payment_service.py` has zero importers. It would
    raise AttributeError if wired, and it keeps a second token ledger whose free tokens never
    decrement. Either finish it or delete it, together with `process_stripe_payment` (C-2).
11. `create_app()` runs twice per gunicorn worker (`app.py:735` plus `wsgi.py:9`). That starts two
    schedulers and two service stacks.
12. LLM path: `ClaudeCliError` subclasses `RuntimeError`, so CLI timeouts are treated as bad JSON
    and repaired, then retried. That allows up to 6×600s per call (`llm_service.py:1082`). Failed
    calls are never logged to `llm_calls` or the cost hooks (`llm_service.py:1065-1380`).
13. The PostgREST 1000-row cap silently truncates reads. This affects `test_service.py:480-488,771-775`
    (attempt history), `scripts/dt_nightly_synthesis.py:77`, `irt/calibrator.py:127` (`.range()`
    without ORDER BY) and `scripts/rederive_tiers.py:51` and siblings.
14. The IRT nightly seed is read from the column the posterior is written to, so shrinkage
    compounds nightly (`irt/calibrator.py:151,309`).
15. The corpus sweep inserts a new `corpus_sources` row every run, duplicating sources
    (`corpus/run_corpus_processing.py:36`).
16. Regen deletes old exercises and then inserts a partial render, non-atomically
    (`queue_drain.py:296-321`). `render_all` re-runs hit the unique index and return `[]` with
    HTTP success.
17. `_update_vocabulary_metadata` can NULL the shared `dim_vocabulary.semantic_class` and
    `part_of_speech` (`asset_pipeline.py:1181-1190`).
18. A `JudgeUnavailable` abort doesn't cancel queued futures, so spend continues
    (`test_generation/orchestrator.py:1794`). Judge `template.format()` sits outside every try
    block. Three judges hard-code `provider='openrouter'`. Judge `_cfg_cache` never expires.
19. Test-gen and topic-gen silently fall back to English prompts for zh/ja when the template row is
    missing (`test_generation/database_client.py:711`, `topic_generation/database_client.py:553`).
    The gatekeeper turns an LLM outage into silent mass rejection (`gatekeeper.py:75`).
20. `knowledge_service.py:41-67` returns `[]` after the BKT RPC has already committed, so an
    outage looks like "nothing updated".
21. Read-modify-write on array columns loses concurrent updates (`routes/study_session.py:513`,
    `test_service.py:732`).
22. Nine `session.speed_*` i18n keys are missing from all 4 locales, so speed round shows raw key
    strings (`players/speed_round.js:82-299`).
23. The word-list upload never calls `sweep_immediate_matches`, so words that match existing tests
    never match (PLAUSIBLE intent gap).

### Redundancy
24. Judge scaffolding is duplicated across about 10 files in `exercise_generation/judges/`. Ladder
    retry/repair scaffolding is copied 4 ways. `_LANG_ID_TO_CODE` is defined 7 times.
25. There are multiple LLM clients bypassing `llm_service`, which loses retry and `llm_calls`
    logging: the topic `BaseAgent` (`topic_generation/agents/base.py:60`), the DT grader through
    `model_arena.llm_runner`, `routes/word_list_import.py:184`, and `prose_writer.py:26`.
26. Prompt loaders diverge in 3+ ways: raise, English fallback, or None, with differing
    `is_active` handling.
27. `escapeHtml`/`esc` is defined 27 times (prior H-3 was 31). 8 variants don't escape quotes.
28. Test templates are still near-forks of the session players (prior M-2). There are 8,256 inline
    JS lines outside lint and tests (prior M-3).
29. `classifier_drill` and `counter_drill` are about 82% identical across route, service and
    curation packages.
30. Vocab list/preview/wipe logic is duplicated between `admin_local.py:376-559` and
    `vocab_admin.py:168-309`.
31. In scripts, there are 119 `sys.path.insert`, 105 `get_supabase_admin` and 81 `load_dotenv`
    copies, with no shared bootstrap or `fetch_all` pager.
32. 35 test files hand-roll their own Supabase fake (prior M-4 was 27).

### Legacy / dead
33. 14 modules have zero importers, including `payment_service.py`, and 8 are imported only by
    tests (static import graph).
34. About 35 authenticated routes have no frontend caller: `routes/exercises.py`, `vocab_dojo.py`,
    `corpus.py`, `payments.py`, `users/tokens`, `users/profile`, `tests/moderate`, flashcards
    stats/skip/page, and others. `flashcards.js:92` links to a non-existent `/flashcards/page`.
35. DT v1 grading body is about 220 lines and dead since V2 defaulted on
    (`grader_cascade.py:160-312`). On env rollback it fails open to MAX_BAND.
36. The bundle experiment is about 1.6k lines. It is default-off, failed blind review, and its
    shadow mode still pays for the call. The `LADDER_QWEN_REASONING` off/low constants are carried
    in 6 modules after failing review.
37. About 770 lines of retired exercise generators remain (cloze, context_spectrum,
    jumbled_sentence, semantic, spot_incorrect, timed_speed_round, translation).
38. In migrations, ~13 functions and tables have no code references (`can_use_free_test`,
    `get_token_balance`, `bkt_phase*`, `dim_block`, `dim_library`, `user_vocabulary`, …). Many
    functions are redefined across files with differing arg counts, which leaves stale overloads.
    Dead-module files carry `USING(true)` policies.
39. Migrations have no ordering scheme. Lexical replay drops modules before creating them, and
    about 130 of 237 files have no BEGIN, so the directory cannot rebuild the database.
40. In scripts, there are about 38 ARCHIVE candidates, about 12 DUPLICATE harnesses
    (`measure_*`, `smoke_entailment_*`, `calibrate_*`/`fit_tier_*`/`retier_*`), and 3 BROKEN.
    See review_08.

### Hygiene / dependencies
41. Tracked generated or scratch files with no ignore rules: `.cache/`, `.playwright-mcp/`,
    `supabase/.temp/`, `bash.exe.stackdump`, `C:tmppytest_out.txt`, `batch_errors_*.json`,
    `generated_tests_*.json`, and Portal runtime data (`james_stats.json`, `*.csv.lock`).
42. `requirements.txt` has 14 unpinned lines (prior M-7). `jieba` and `lemminflect` are imported
    but undeclared. `flask-jwt-extended` and `python-decouple` look unused. `pytest-cov` is in the
    runtime requirements.
43. About 100 env vars are read across 126 sites, 39+ of them undocumented, and there is no
    `.env.example`.
44. `Portal/` is five independent Flask apps with no coupling to the WebApp. The reviewer
    recommends splitting it out with `git filter-repo --subdirectory-filter Portal`. Portal also
    has its own MEDIUM issues (open CORS `*`, DEBUG and SECRET_KEY dev defaults, `str(e)` to
    clients, unescaped `cover_url`). See review_10.

---

## LOW (abridged — full list in the slice files)

- Raw exception text is returned to clients in about 8 places across routes and services.
- `/api/health` leaks which backends are configured.
- `limit`/`count` params are not validated, so `min(None, n)` causes a 500.
- `isinstance(x, int)` accepts bool.
- `.single()` makes the 404 branches unreachable.
- Server-local `date.today()` ignores the user timezone in `study_plan.py:111` and `flashcards.py:49`.
- The hand-rolled CORS preflight reflects Origin when `*` is configured (prior L-6, default is safe).
- The `claude` CLI subprocess inherits the full environment, including the service-role and Stripe keys.
- Full prompts go to an unbounded daily CSV.
- `task_runner` has a root-logger handler and an unlocked TASKS dict. Pruning can delete running tasks.
- Advisory locks over PostgREST may release on a different pooled connection, and all lock helpers
  fail open.
- `phonetic_trie/trie.py:205` uses `pickle.load` on an artifact file.
- `word_assets.prompt_version` is hard-coded to `'v1'`.
- The Python exercise-type set and the SQL unique-index list are hand-synced with no test.
- Learner DT text is concatenated into the grading prompt unfenced, which allows self-grade
  injection.
- Dead config: `AWS_*`, `EXERCISE_SLOT_DISTRIBUTION`, `EXERCISE_COOLDOWN_DAYS`, and others.
  Unused `TestSubmission*` models, unused `tier_required` decorator, about 10 unused imports.
- Dead functions: about 18 in generation, about 15 in `vocabulary_ladder/config.py`, 7 in
  `r2_service`, most of `ai_service`, and `test_service.get_tests`/`update_audio`/`record_attempt`.
- `jev_client` docstring still describes the OpenRouter key import-freeze, which is fixed in
  `llm_service`.
- Production classes named `Test*` cause pytest collection warnings.
- `tests/__pycache__` has orphan bytecode.
- 4 tests use `time.sleep` for thread interleaving.
- `Project Knowledge/` duplicates `wiki/` and was last touched 2026-02-14.
- Backup tables from task819/task821 sit in `public` with no RLS.
- CDN scripts are loaded without SRI in `admin_dashboard.html` and `language_selection.html`.

---

## Prior review (2026-09-08) status

| Item | Status |
|---|---|
| C-1 admin app 0.0.0.0 + debug | FIXED (residual: H-3 above) |
| H-1 suite red | Mostly fixed. 1 stale failure remains |
| H-2 session runtime never linted | Open (deferred by decision) |
| H-3 escapeHtml ×31 | Open, now ×27 |
| M-1 admin attribute injection | FIXED |
| M-2 template forks | Open |
| M-3 inline JS | Open (8,256 lines) |
| M-4 hand-rolled Supabase fakes | Open, worse (27 → 35) |
| M-6 no rate limiting | Open |
| M-7 unpinned deps | Open |
| L-1 build artifacts tracked | Open |
| L-2 twilio.txt | Open |
| L-3 venv in history | Partial (pack 212 MiB, history not rewritten) |
| L-4 Portal in repo | Open |
| L-6 CORS `*` reflection | Open (default config safe) |

## Suggested order

1. **Today:** C-2 (revoke `process_stripe_payment`), C-1 (enable RLS and revoke anon on 32
   tables) and C-3 (revoke anon/authenticated EXECUTE on internal RPCs). These are one migration
   and need no app code change, because the backend uses the service role.
2. H-1 (separate GoTrue client). This is a small change with a large blast radius.
3. H-2 and Security #5 (rate limits and length caps on LLM-spending endpoints).
4. H-4 to H-7 (fail-closed regen, surface persistence errors, queue leases).
5. Decide on payments: finish them or delete them (M-PAY).
6. Dead-code sweep (items 33–40) and the Portal split.
