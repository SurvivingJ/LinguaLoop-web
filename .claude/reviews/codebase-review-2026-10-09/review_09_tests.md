# Review 09 - tests/
Pytest (tests/, e2e ignored): 1 failed, 3241 passed, 2 skipped, 10 warnings in 167s. Vitest: 129 passed (3 files).
FAILED: tests/test_prompt_split_l4_l8.py::test_unregistered_prompt_version_is_refused_not_guessed
Prior H-1 (suite red): partially still open - 1 stale failure. Prior M-4 (hand-rolled Supabase fakes): still open; recount 35 test files define own Fake/Mock/Stub classes or fake-client helpers (grep list), vs 27 before.

### [MEDIUM] Stale test fails: asserts morphology_slot v2 unregistered
- Category: legacy/dead
- Location: tests/test_prompt_split_l4_l8.py:289-294
- Problem: Test expects ladder_schema('morphology_slot', 2) to raise, but PROMPT_VERSIONS was widened to {1, 2}.
- Evidence: services/exercise_generation/schemas/ladder_l4_morphology.py:54 `frozenset({1, 2})`; test message "known versions: [1]".
- Fix: Use a genuinely unregistered version (e.g. 99) and derive the expected list from PROMPT_VERSIONS.

### [MEDIUM] Many hand-rolled Supabase fakes (M-4 still open)
- Category: redundancy
- Location: 35 files incl. tests/test_sweep_cron.py, test_word_resolver.py, test_dual_translation_routes.py, test_speed_round.py, test_match_sweep.py, test_ladder_topup.py, test_model_health.py (plus conftest.py)
- Problem: each file defines its own Fake/Stub client with different chain-method coverage; drift hides behaviour changes.
- Evidence: grep for `class (Fake|Mock|Stub|_Fake)` finds 35 files.
- Fix: Extract one chainable FakeSupabase (table/select/eq/rpc recording) into conftest or tests/helpers.

### [MEDIUM] Riskiest untested modules (no test imports them)
- Category: test-coverage
- Location: services/payment_service.py, routes/payments.py, services/auth_service.py (only incidentally via conftest/route tests), services/r2_service.py, services/device_service.py, routes/practice.py, routes/exercises.py, routes/vocab_admin.py, routes/vocab_dojo.py, routes/admin_local.py (60KB), routes/corpus.py, routes/classifier_drill.py, routes/counter_drill.py, services/furigana_service.py, services/pitch_accent_service.py, services/task_runner.py
- Problem: payments and auth_service have zero direct tests; admin_local and practice routes untested.
- Evidence: grep of tests/ for `services.<mod>` / `routes.<mod>` returns 0 files for each (test_auth.py/test_users.py/test_flashcards.py only test routes via client with MagicMock).
- Fix: Prioritise payment_service/routes/payments (Stripe webhook verification), auth_service, routes/practice, admin_local auth gating.

### [LOW] Orphaned __pycache__ for deleted tests
- Category: legacy/dead
- Location: tests/__pycache__/ (test_listening_lab_routes, test_listening_lab_service, test_csp_tmp, test_phase1_verify_tmp)
- Problem: bytecode of removed tests (listening lab feature removed); harmless clutter, check .gitignore covers it.
- Fix: Delete pycache.

### [LOW] Conditional skips depend on env
- Category: test-quality
- Location: tests/test_ladder_validation_profiles.py:80, tests/test_provider_routing_and_reasoning.py:629 (SUPABASE_URL needed - live DB read), tests/test_dual_translation_gold_seed_helper.py:72,94 (TASK-627 pending - likely stale, rubric v6 is live), tests/test_matrix_gated_planning.py:87,172 (skip if ZH L4 capability appears)
- Problem: the 2 skipped now are env-gated live-DB tests; they are unmarked integration tests that silently skip in CI. TASK-627 skips are probably dead since rubric v5/v6 live.
- Fix: Mark with a custom `integration` marker; delete TASK-627 skips or make them hard asserts.

### [LOW] Real time.sleep in tests
- Category: test-quality
- Location: tests/test_dual_translation_grader_cascade.py:378, tests/test_generation_batch_workers.py:103, tests/test_jev_client.py:110, tests/test_word_list_import_routes.py:168
- Problem: 10-50ms sleeps used to provoke thread interleaving; small but potentially flaky on loaded CI.
- Fix: Use threading.Barrier/Event.

### [LOW] Pytest collection warnings
- Category: test-quality
- Location: tests importing TestService / TestGenerationOrchestrator / TestDatabaseClient / TestGenConfig
- Problem: production classes named Test* are collected and warn.
- Fix: set `__test__ = False` on those classes or alias on import.

### [LOW] E2E specs not covered by any marker/config; one live-data note
- Category: test-quality
- Location: tests/e2e/*.spec.js
- Problem: e2e writes real data (memory: calibration-e2e-writes-real-data); not run here. No JS-vs-Python separation config found in pytest.ini (no "e2e" entries); they are JS so pytest ignores them naturally.
- Fix: none needed beyond documentation.

### [INFO] Not found
- No xfail marks; no network-hitting unmarked tests found in the passing run; test_auth.py:PROTECTED_ENDPOINTS 401 checks are meaningful. SQL tests (tests/sql/*.sql, 6 files) are manual and not wired into pytest (PLAUSIBLE untested in CI).
