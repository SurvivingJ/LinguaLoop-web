---
title: The Tests Route Package — Technical Specification
type: feature-tech
status: complete
prose_page: ./routes-tests-package.md
last_updated: 2026-11-23
dependencies:
  - "tables: tests, questions, test_attempts, test_skill_ratings, user_skill_ratings, daily_test_loads, dim_word_senses, test_sentences, test_sentence_references, prestudy_sessions, exercises, exercise_attempts, flagged_inputs, users"
  - "RPCs: process_test_submission, process_dictation_submission, process_pinyin_submission, process_pitch_accent_submission, get_recommended_test, get_recommended_tests, apply_attempt_timing_and_progress, credit_study_time, update_vocabulary_from_word_tests_batch"
  - "services: attempts, attempt_timing, concurrency, test_service, prestudy, intro_drill, dictation, vocabulary.knowledge_service, day_boundary, pinyin_format"
  - "middleware.auth (jwt_required, get_optional_user_id)"
breaking_change_risk: medium
open_questions:
  - "OPEN: `find_active_test_by_slug` (`services/test_service.py`) ends in `.single().execute()`. postgrest-py 0.16.11 (the pinned version) raises `APIError` for the 406/PGRST116 that PostgREST returns for zero rows, so for an unknown or inactive slug the submit handlers most likely never reach `if not test: return not_found(...)` and answer `500` (message from `@api_errors`). Not run against the live API. Confirm, then catch the error or use `.limit(1)`."
  - "OPEN: `routes/tests/submit.py` comments say the name `_apply_timing_and_progress` is kept for the earlier per-drill route modules, which no longer exist (the single caller is `routes/drills.py`). Comment is stale."
  - "OPEN: `GET /api/tests/` (`catalog.get_tests_with_ratings`) and `GET /api/tests/random`'s `skill_type` parameter have no effect on or caller in the app; see [[api/rpcs.tech]]."
---

# The Tests Route Package — Technical Specification

Verified 2026-11-23 against commit `0d345e98`. Package `routes/tests/`: six files, 1,353 lines (`__init__.py` 48, `blueprint.py` 5, `catalog.py` 308, `prestudy.py` 334, `sentences.py` 154, `submit.py` 504). 20 routes on one blueprint (`POST /moderate` was removed 2026-11-23, TASK-1221). The route table with auth and clients is in [[api/rpcs.tech]]; this page is the module map and the submit flow. Prose: [[features/routes-tests-package]].

## Architecture Overview

```
app.py ── from routes.tests import tests_bp ── register_blueprint(url_prefix='/api/tests')
routes/tests/__init__.py   imports blueprint, then catalog, submit, sentences, prestudy (registering their routes)
        │
        ├─ blueprint.py   tests_bp = Blueprint("tests", "routes.tests")
        ├─ catalog.py     list / open / recommend / daily load / history
        ├─ submit.py      4 submit routes + submission RPC wrappers
        ├─ sentences.py   GET /<identifier>/sentences
        └─ prestudy.py    7 prestudy routes
                 │
                 ▼
   services/test_service.py   services/attempts.py   services/prestudy.py   services/dictation/
```

The blueprint name `tests` (and so every endpoint name `tests.<function>`) and every URL are unchanged by the split; `web/rate_limits.py` names no `tests.*` endpoint. `routes/tests/__init__.py` re-exports names that other modules and tests import with `from routes.tests import ...`; keep them importable: `tests_bp`, `DimensionService`, `TestService`, `get_test_service`, `normalize_audio_url`, `_apply_timing_and_progress`, `_attach_explanations`, `_build_submission_response`, `_call_dictation_submission_rpc`, `_call_pinyin_submission_rpc`, `_call_pitch_accent_submission_rpc`, `_call_submission_rpc`, `_complete_daily_slot`, `_credit_attempt_window`, `_is_missing_function_error`, `_normalize_timing`, `_submission_failure_response`, `_unwrap_rpc_response`, `_update_vocabulary_tracking`, `_has_attempt_today`, `_load_active_references`, `_load_sentence_rows`, `_resolve_sentence_l1`, `build_sentence_payload`, `_PRESTUDY_MAX_ANSWERS`, `_PRESTUDY_MAX_EXERCISE_ANSWERS`. The only production importer is `routes/drills.py` (`_apply_timing_and_progress`, imported lazily because of a circular import).

### Where the old single-file tests route module went

Commit `6797632b` (2026-11-14) split the 1,361-line single file with no behaviour change. Afterwards the bookkeeping that is not about HTTP moved on to the service layer:

| Old responsibility (in the single file) | Now |
|---|---|
| `normalize_audio_url`, random/recommended, daily load, list, open by slug, open by id, history | `catalog.py` |
| The catalogue query for the list | `services/test_service.list_tests_with_ratings` (moved in the same commit) |
| Static test content with a short cache; ratings | `services/test_service.get_test_content` (TTL 120 s, `TEST_CONTENT_TTL_SECONDS`), `get_test_skill_ratings` |
| Submission RPC wrappers and the four submit handlers | `submit.py` |
| Post-submission hooks (timing, daily slot, study-time credit, BKT tracking, explanations, response shape, ELO blocks, dictation helpers, pinyin/pitch item counts, history query) | `services/attempts.py`; `submit.py` keeps the old private names as aliases (`_normalize_timing = attempts.normalize_timing`, etc.) |
| Sentences endpoint and helpers | `sentences.py` |
| Prestudy routes and helpers | `prestudy.py` (the logic is in `services/prestudy.py`) |

## Database Impact

Reads: `tests`, `questions`, `dim_word_senses` (through the cached content), `test_skill_ratings`, `user_skill_ratings`, `daily_test_loads`, `test_attempts`, `test_sentences`, `test_sentence_references`, `users` (`native_language_id`), `prestudy_sessions`. Writes: only through RPCs and services — the four `process_*_submission` RPCs (attempts, ratings, `question_attempt_results`, idempotency), `apply_attempt_timing_and_progress` (duration, plan counter), `credit_study_time` (ledger), BKT/flashcard/ladder writes in `VocabularyKnowledgeService`, `flagged_inputs` (moderation), `prestudy_sessions`, `exercise_attempts` (prestudy exercises). No route here writes a table directly except those services. See [[database/schema.tech]] and [[database/rpcs.tech]].

## API / RPC Surface

### `catalog.py` (308 lines)

- `normalize_audio_url(test_data)`: an `audio_url` without `http` becomes `Config.get_audio_url(<slug part>)`; empty falls back to the slug-based CDN URL.
- `GET /` `get_tests_with_ratings` (JWT): `list_tests_with_ratings(db, language_id?, difficulty?, limit=50)`.
- `GET /<slug>` `get_test` (optional auth): `get_test_service().get_test_by_slug`; `404` unknown; with a valid token and `TestService.has_pending_dictation_slot` the `transcript` is `''`; without a token the response is `Cache-Control: private, max-age=60` (`_public_cacheable`).
- `GET /test/<identifier>` `get_test_with_ratings` (optional auth): slug or UUID; `get_test_content(db, identifier, also=(ratings, dictation_pending, definition-language))` runs the per-user reads concurrently with whatever the content cache lacks; `?mode=dictation` or a pending dictation slot removes `transcript` and `vocab_token_map`; builds `definitions` per sense with the learner's definition language (`apply_definition_language_preference`), Chinese readings as tone-marked pinyin (`display_pronunciation`); response `{test_data, questions_data, skill_ratings, vocab_token_map, definitions, pinyin_payload?, pitch_payload?, furigana_payload?}`.
- `GET /random`, `GET /recommended`: RPCs `get_recommended_test` and `get_recommended_tests(p_user_id, p_language_id)`; `language_id` via `parse_language_id` (`400` invalid); random answers `404` when empty. Recommended returns `{recommended_tests}`.
- `GET /daily-load`, `POST /daily-load/complete`: `get_or_create_daily_load(user_id, language_id)`; `mark_daily_test_complete(user_id, language_id, test_id)` (`400 No attempt recorded today for this test` on `NoMatchingAttemptError`).
- `GET /history`: `attempts.list_test_history(db, db, user_id, language_id?, test_type_id?, limit ≤ 100 (25), offset ≥ 0)` → `{tests: [...]}`.
- `POST /moderate` was removed 2026-11-23 (TASK-1221; no caller). `AIService.moderate_content`, `ModerationServiceError`, `TestService.record_flagged_input` and the `tests.moderate_content` rate limit went with it; `AIService` remains only as the holder of the shared OpenAI-compatible client.

### `submit.py` (504 lines)

See "Submit flow" below. Helpers: `_submission_failure_response(rpc_name, payload)` (logs the raw payload, returns the generic `500 {error: "submission_failed", error_code: "submission_failed"}`; CR-04: never forward `SQLERRM`), `_unwrap_rpc_response(rpc_name, data, on_success)` (success dict → `on_success`; `error_code == 'unauthorized'` → `403 unauthorized`; else the generic failure), `_is_missing_function_error(exc)` (PGRST202 or "Could not find the function"), `_submit_rpc(client, rpc_name, user_id, test_id, language_id, test_type_id, idempotency_key, extra, optional_param=None)`, the four `_call_*_rpc` wrappers, `_submit_handler(failure_message)` (decorator: `@api_errors`, then calls `fn(slug, get_db(), g.current_user_id, json_body())`), `_record_submission(...)`, `_submit_counted(...)`.

### `sentences.py` (154 lines)

`GET /<identifier>/sentences` (JWT): `_find_test_for_sentences` (active test by slug then UUID: `id, slug, language_id, transcript_hash`), `_resolve_sentence_l1(db, user_id, l1_code)` (`?l1=` via `SENTENCE_L1_IDS`; unknown code → `400`; absent → `users.native_language_id`, else English id 2), `_load_sentence_rows` (`test_sentences` ordered by `idx`), stale check (`409 SENTENCES_STALE` when a row's `transcript_hash` differs from the test's), `?mode=produce` withholds `l2_text` unless `_has_attempt_today` (a `test_attempts` row since the learner's local day start, ADR-022), `_load_active_references` (`test_sentence_references` active rows for the L1), `build_sentence_payload(rows, references, withhold_l2)`. Response `{test_id, l1_language_id, l2_withheld, sentences: [{idx, char_start, char_end, token_start, token_end, reference: {l1_text, tightness} | null, l2_text?}]}`; an empty list means no rows yet.

### `prestudy.py` (334 lines)

Constants `_PRESTUDY_MAX_ANSWERS = 400`, `_PRESTUDY_MAX_EXERCISE_ANSWERS = 40`; `_find_test_for_prestudy(db, identifier)` reads `_PRESTUDY_TEST_COLUMNS`. Routes (all JWT): `GET /<id>/prestudy` (`prestudy.build_prestudy_payload`; `?mode=followup` adds `followup_sense_ids`, `attempt_id`, `primed_sense_ids`, `400` before an attempt); `GET /<id>/prestudy/exercises?sense_ids=` (1–`MAX_ON_DEMAND_SENSES`); `POST /<id>/prestudy/session` (`prestudy.start_session`; returns `{session_id}`, null until the workflow migration is applied); `POST /<id>/prestudy/evidence` (word answers → `update_from_word_tests_batch` with `side_effects` only in follow-up mode; exercise answers → `_record_prestudy_exercises` → `PracticeSessionService.record_prestudy_exercise_attempt`; session close, generation requests, `intro_drill.admit_prestudy`); `POST /<id>/prestudy/admit-overflow` (`intro_drill.overload`); `POST /<id>/prestudy/produce` (`resolve_produce_l1`, `wrong_question_senses`, `choose_produce_window`, then `routes.dual_translation.open_range_passage`; `422 NO_WINDOW`, `403` without an attempt); `GET /<id>/prestudy/produce-available`. Behaviour of each is specified in [[features/test-prestudy.tech]].

## Submit flow (end to end)

Entry: `POST /api/tests/<slug>/submit` → `@supabase_jwt_required` → `@_submit_handler('Failed to submit test')` → `submit_test_attempt(slug, db, current_user_id, data)`.

1. **Parse.** `responses` (empty → `400 No responses provided`), `test_mode` (default `reading`, lower-cased), `furigana_used`, `prestudied = (data['prestudied'] is True)`, `idempotency_key` (given or a new uuid4).
2. **Timing.** `_normalize_timing(data)` = `attempts.normalize_timing`: validates and clamps `started_at`/`finished_at` (`validate_attempt_window`; window capped at `MAX_CREDITED_ATTEMPT_SECONDS` = 20 min by moving the start forward); a forged window is `400` and **nothing is recorded**.
3. **Test lookup.** `find_active_test_by_slug(db, slug)` → `id, language_id` (see the open question about the unknown-slug case). `test_type_id` from `DimensionService.get_test_type_id(test_mode)`; an unknown mode falls back to `reading` (id 1).
4. **Responses are stripped** to `{question_id, selected_answer}`; the database calculates correctness.
5. **Prestudy check and question read, concurrently** (`run_parallel`): `prestudy.find_prestudy_for_attempt(db, user, test)` (a completed prime within the last 6 hours; the client flag only counts while `prestudy_sessions` does not exist) and `attempts.load_question_rows(db, test_id)` (`id, sense_ids, answer_explanation`). A failed verification is logged and treated as "not verifiable".
6. **RPC** `process_test_submission(p_user_id, p_test_id, p_language_id, p_test_type_id, p_was_free_test=true, p_idempotency_key, p_responses, p_furigana_used[, p_prestudied=true])` through `_submit_rpc`. `p_prestudied` is sent only when true and dropped (one retry) if PostgREST reports the function lacks it. supabase-py raises on a JSONB `success:false`; the exception payload is rescued and routed through `_unwrap_rpc_response`. In one transaction the RPC validates answers server-side, writes the attempt (idempotent on the key), the per-question results and moves `user_skill_ratings` and `test_skill_ratings`. Failure → generic `500 submission_failed`; unauthorised → `403`.
7. **Bookkeeping, started in parallel** (`_record_submission` returns the futures): `attempts.defer(_apply_timing_and_progress, ...)` (RPC `apply_attempt_timing_and_progress` writes the duration and bumps the study-plan counter, then `credit_attempt_window` writes the study-time ledger) and `attempts.defer(_complete_daily_slot, ...)` (marks today's daily-load slot for this test done). Both are best-effort. `attempts.defer` uses a 16-thread pool (`attempt-*`).
8. **Prestudy consumption** (if prestudied and a session id): `prestudy.consume_session` deferred.
9. **Vocabulary tracking** `attempts.track_vocabulary(...)`: `update_from_comprehension` (RPC `update_vocabulary_from_test` per sense, no side effects yet) concurrently with the learner's definition language; then either all side effects in order (when a word crosses the known threshold) or flashcards and ladder seeding deferred in parallel; contextual inference deferred (`bkt_contextual_inference`); then `build_quiz_with_distractors` (`get_word_quiz_candidates`, `get_quiz_distractors` with `get_distractors` fallback) up to 5 words → `word_quiz {candidates, attempt_id}`. Any failure is logged and returns no quiz.
10. **Response** `attempts.build_submission_response` + `attach_explanations` (explanations revealed only now) → `{status, result: {score, total_questions, percentage, question_results, is_first_attempt, user_elo_change, test_elo_change, elo_reduction_factor, test_mode, attempt_id, word_quiz?, prestudied?}}`.
11. **`finally: attempts.join(pending)`** — waits for every deferred task; a raising task is logged and never re-raised.

**Other modes.** Pinyin and pitch-accent go through `_submit_counted`: `clamp_time_taken`, `validate_counts(correct, total)`, `normalize_timing`; `find_active_test_by_slug(db, slug, 'id, language_id, <payload column>')`; `language_id` must be 1 (pinyin) or 3 (pitch accent), else `400`; `total` may not exceed the real item count of `pinyin_payload` / `pitch_payload` (`attempts.pinyin_item_count`, `pitch_item_count`); RPCs `process_pinyin_submission(p_correct_chars, p_total_chars)` and `process_pitch_accent_submission(p_correct_units, p_total_units, p_furigana_used)`; response `{accuracy, <correct_key>, <total_key>, time_taken, user_elo_change, test_elo_change, test_mode, attempt_id}`. Dictation: `user_transcript` (empty → `400`; > 10× the canonical length → `400`), the canonical transcript read server-side, `grade_dictation(correct, typed, language_code)`, `attach_dictation_senses`, the diff stored capped at `MAX_STORED_DIFF_ENTRIES` (twice the largest tier word cap; the full diff is still returned), RPC `process_dictation_submission(p_word_correct, p_word_total, p_replay_count, p_diff_payload)`, deferred `record_dictation_bkt`; response adds `word_correct`, `word_total`, `replay_count`, `diff`, `replay_factor`, `elo_reduction_factor`.

## Component Specification (if UI)

Not applicable; the callers are `static/js/session/players/*.js` (submit), `static/js/pages/test-list.js`, `test-preview.js`, `profile.js`, `static/js/prestudy/*.js`, `sentences.js`.

## Key Architectural Decisions

1. **One blueprint, four modules by topic.** Rationale: the 1,361-line file mixed four concerns; endpoint names and URLs stay; alternatives rejected: separate blueprints (would change endpoint names used in rate limits and `url_for`).
2. **Everything that is not HTTP moved to `services/attempts.py`**, which never reads `g`, `request` or `current_app` and takes the client explicitly, so it can run on a worker thread.
3. **Grading is in the database.** The route never decides correctness; it forwards the learner's choices and reads the RPC result (idempotency, ELO and attempt are one transaction).
4. **Best-effort bookkeeping overlaps the response.** The learner's result never depends on the timing, daily-slot, flashcard, ladder or contextual-inference writes.
5. **Generic failure envelopes** (CR-04): no SQL error text reaches the client.

## Security Considerations

All writes require a valid token; `g.current_user_id` only. Opening a test is public by design (`GET /<slug>`, `GET /test/<identifier>`) and personalises only when a valid token is present; the transcript of a pending dictation is withheld on the server, not by the client. `question_results` expose the correct answer only in the submission response. Counted submissions are checked against the real item count; time windows are validated; dictation length is bounded.

## Testing Strategy

Existing tests: `test_tests_routes_refactor.py` (split and re-exports), `test_submission_rpc_error_envelope.py`, `test_sentence_endpoints.py`, `test_prestudy*.py`, `test_daily_slot_on_submit.py`, `test_study_time_tests_route.py`, `test_classifier_drill_progress.py`, `test_pinyin_display_surfaces.py`, `test_security_route_hardening.py`. Edge cases to keep covered: missing `p_prestudied` function (retry without it); `success:false` payload rescued from an exception; idempotent double submit; forged `started_at`; pinyin total above the real count; unknown slug (see open question); dictation 10× length; deferred task raising.

## Related Pages

- [[features/routes-tests-package]] — Prose page
- [[api/rpcs.tech]] — Route table (auth, RPCs, clients)
- [[features/comprehension-tests.tech]] — Test engine and ratings
- [[features/test-prestudy.tech]] — Prestudy behaviour
- [[features/dictation.tech]], [[features/pinyin-trainer.tech]], [[features/pitch-accent-trainer.tech]] — Mode-specific grading
- [[algorithms/elo-ranking.tech]] — The rating update inside the RPC
- [[database/rpcs.tech]] — RPC definitions
- [[database/schema.tech]] — Tables
