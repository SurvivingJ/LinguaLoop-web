---
title: API — Technical Specification
type: api-tech
status: complete
prose_page: ./rpcs.md
last_updated: 2026-05-13 (vocab browser mirror added to admin_local)
dependencies:
  - "Flask Blueprints (15 in `routes/`)"
  - "Supabase JWT middleware (`middleware/auth.py`)"
  - "Supabase Python client (REST + RPC)"
  - "Stripe SDK (payments)"
breaking_change_risk: medium
---

# API — Technical Specification

> **Planned additions (2026-05-21) — Study Plans + Practice Engine merger.** Full route specs in [[features/practice-engine.tech]] and [[features/study-plans.tech]].
>
> **New blueprints / routes:**
> - `routes/practice.py` (new blueprint)
>   - `GET /api/practice/session?mode=acquisition|maintenance|auto&minutes=N&language_id=L&debug=0|1` → `get_practice_session` jsonb.
>   - `POST /api/practice/attempt` body `{ exercise_id, user_response, is_correct, time_taken_ms, session_mode, language_id, sense_id?, ladder_level? }` → attempt record + BKT/FSRS/ladder updates + `record_session_progress` call.
> - `routes/settings.py` (extended)
>   - `GET /api/study-plan?language_id=L` → `user_study_plans` row + current `weekly_plan_states` row.
>   - `PUT /api/study-plan` body `{ language_id, daily_minutes?, weekday_shape?, skill_weight_overrides?, template_id? }` → updated row.
>   - `POST /api/study-plan/recompute` body `{ language_id }` → result of `compute_weekly_plan(user, lang, this_week_monday)`.
>   - `GET /api/study-plan/templates?language_id=L` → array of `dim_study_plan_templates` for the language.
>
> **Deprecated / wrapped routes (kept one release):**
> - `GET /api/exercises/session` — now wraps `get_practice_session('auto', ...)`. Logs `[DEPRECATED]` once per session.
> - `GET /api/vocab-dojo/session` — wraps `get_practice_session('acquisition', ...)`. Gate / stress-test endpoints unchanged.
>
> **Modified:**
> - `POST /api/tests/<slug>/submit` (and dictation/pinyin/pitch variants) — accepts new `started_at`, `finished_at` ISO timestamps; server computes `duration_ms`. Existing fields unchanged.
>
> **New cron registrations:** `study_plan_weekly_recompute` (Sun 23:00 UTC) and `exercise_time_estimate_refresh` (04:05 UTC) join `irt_calibration_nightly` in [app.py:201](../../app.py#L201). Same APScheduler block; same advisory-lock pattern.

This is the canonical endpoint reference. Every route is enumerated with its decorator (auth requirement), accepted body / query params, the success response shape, and the underlying RPC or service call. Use the table on each blueprint to navigate; use the per-handler subsections when wiring frontend or third-party code.

## Application Entry Points

The Flask factory `create_app()` lives in [app.py:44](../../app.py#L44) and registers the **production** blueprint set. The local admin variant [admin_app.py](../../admin_app.py) wraps `create_app()` and additionally mounts the admin pipeline + Model Arena blueprints — so admin endpoints exist **only** when running `python admin_app.py` (or equivalent on Railway). The production deployment does not expose `/admin/*`.

| Variant | Blueprints | Url-prefixes | Use |
|---------|-----------|--------------|-----|
| `app.py` (production) | auth, tests, reports, vocabulary, flashcards, exercises, corpus, users, payments, mystery, conversations, vocab_dojo, vocab_admin | `/api/*`, `/api/admin/vocab/*` | Railway production |
| `admin_app.py` (local) | All of the above, plus `admin_local_bp` (`/admin`) and `model_arena_bp` (`/admin/arena`) | adds `/admin/*` | Operator/admin tooling |

The Flask app boots an APScheduler `BackgroundScheduler` ([app.py:201](../../app.py#L201)) inside every worker. Right now a single cron job is registered: `irt_calibration_nightly @ 04:00 UTC` which calls [`services.irt.calibrator.calibrate_all_active_languages()`](../../services/irt/calibrator.py). Cross-worker safety comes from a Postgres advisory lock (`irt_try_lock`); duplicate fires across gunicorn workers exit cleanly. Disable for tests via `DISABLE_SCHEDULER=true`.

## Authentication

All decorators live in [middleware/auth.py](../../middleware/auth.py). Token extraction is `Authorization: Bearer <jwt>`; `g.current_user_id` (and aliases `g.user_id`, `g.current_user`, `g.supabase_claims`) is populated server-side and never trusted from the client.

| Decorator | Behaviour | Failure |
|-----------|-----------|---------|
| `@jwt_required` (alias `@supabase_jwt_required`) | Validates Supabase JWT via `auth.get_user(token)`. **Service-role bypass:** if `token == SUPABASE_SERVICE_ROLE_KEY`, the request runs as `g.current_user_id='service-account'` — used by internal batch jobs. | 401 Token missing / Invalid / 503 Auth service down |
| `@admin_required` | JWT + reads `users.subscription_tier` via the service client, requires `'admin'` or `'moderator'`. | 403 Admin access required |
| `@tier_required([tiers])` | JWT + checks `users.subscription_tier` against the supplied list. | 403 Requires X access |
| _no decorator_ | Public route. Used for `/api/auth/send-otp`, `/api/auth/verify-otp`, `/api/auth/refresh-token`, `/api/payments/token-packages`, `/api/health`, `/api/config`, `/api/metadata`, and the unauthenticated `/api/tests/<slug>` reads. | — |

Response helpers ([utils/responses.py](../../utils/responses.py)): `api_success(payload, status_code=200)`, `bad_request(msg)` → 400, `not_found(msg)` → 404, `server_error(msg)` → 500, `service_unavailable(msg)` → 503. All return `(jsonify(...), status_code)`.

---

## Core Routes — `app.py`

Defined inline in `_register_core_routes()` ([app.py:400](../../app.py#L400)) and `_register_web_routes()` ([app.py:301](../../app.py#L301)).

### Public APIs

| Method | Path | Auth | Purpose | Response |
|---|---|---|---|---|
| GET | `/api/health` | none | Service liveness probe | `{status, timestamp, version: "2.2.0", services: {openai, supabase, auth, r2, stripe, vocabulary}}` |
| GET | `/api/config` | none | Public feature flags | `{features: {...}, token_costs, daily_free_tokens}` |
| GET | `/api/metadata` | none | Cached dimension data | `{languages[], test_types[], status: 'success'}` |
| POST | `/api/vocabulary/extract` | `@jwt_required` | LLM-based vocab extraction from arbitrary text | `{vocabulary: {...}}`. Body: `VocabularyExtractRequest = {text, language_code}`. Delegates to `VocabularyExtractionPipeline.extract()`. |
| POST | `/api/errors/log` | `@jwt_required` | Frontend error reporting | 201. Body: `ErrorLogRequest = {error_type, error_message, url?, metadata?}`. Inserts to `app_error_logs` with the authenticated `user_id`. |

### Web pages (HTML, server-rendered)

| Path | Template | Notes |
|---|---|---|
| `/` | (302 → `/login`) | |
| `/login`, `/signup` | `login.html` | OTP flow; same template |
| `/welcome` | `onboarding.html` | First-time user flow |
| `/language-selection` | `language_selection.html` | |
| `/tests` | `test_list.html` | Calls `/api/tests/recommended` |
| `/test/<slug>` | `test.html` | MC reading/listening test |
| `/test/<slug>/preview` | `test_preview.html` | Pre-start metadata |
| `/test/<slug>/pinyin` | `test_pinyin.html` | Pinyin tone trainer (Chinese only) |
| `/profile` | `profile.html` | ELO, tokens, history |
| `/flashcards` | `flashcards.html` | FSRS review |
| `/exercises` | `exercises.html` | Daily mixed-session UI |
| `/mysteries` | `mystery_list.html` | |
| `/mystery/<slug>` | `mystery.html` | 5-scene murder mystery flow |
| `/conversations` | `conversation_list.html` | |
| `/conversation/<id>` | `conversation_reader.html` | Render generated dialogue |
| `/vocab-dojo` | `vocab_dojo.html` | Ladder + gates + stress test UI |
| `/admin/vocab-preview` | `admin_vocab_preview.html` | Per-word exercise spot-check |
| `/logout` | (302 → `/login`) | Frontend clears tokens |

---

## `/api/auth` — [routes/auth.py](../../routes/auth.py)

OTP-based passwordless auth. Calls into `auth_bp.auth_service` (an [`AuthService`](../../services/auth_service.py) instance bound by `app.py` at startup).

| Method | Path | Auth | Body | Notes |
|---|---|---|---|---|
| POST | `/send-otp` | none | `{email, is_registration?}` | Sends 6-digit OTP via Supabase Auth. Returns `{success, message}`. |
| POST | `/verify-otp` | none | `{email, otp_code}` | Verifies OTP and returns `{success, user: {id, email, emailVerified, subscriptionTier, tokenBalance, totalTestsTaken, totalTestsGenerated}, jwt_token, refresh_token}`. |
| POST | `/refresh-token` | none | `{refresh_token}` | Refreshes the Supabase session; returns `{success, jwt_token, refresh_token}`. 401 on invalid token. |
| GET | `/profile` | `@jwt_required` | — | Returns `{success, profile}` from `AuthService.get_user_profile(user_id)`. 404 if user row missing. |
| POST | `/logout` | `@jwt_required` | — | Calls `AuthService.logout(user_id)`. |

---

## `/api/tests` — [routes/tests.py](../../routes/tests.py)

The comprehension-test surface: list, fetch, submit, generate. Most non-trivial logic delegates to [TestService](../../services/test_service.py) and the `process_test_submission` Postgres RPC.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/` | `@jwt_required` | Filterable test list with ELO ratings joined |
| GET | `/random` | `@jwt_required` | One ELO-matched test (`get_recommended_test` RPC) |
| GET | `/recommended` | `@jwt_required` | Curated list (`get_recommended_tests` RPC) |
| GET | `/daily-load` | `@jwt_required` | Today's pre-computed daily test set |
| POST | `/daily-load/complete` | `@jwt_required` | Mark a test complete in the daily load |
| GET | `/<slug>` | none ⚠ | Public test data (no JWT) — slug → test row |
| GET | `/test/<identifier>` | none ⚠ | Test + questions + ratings (slug or UUID) |
| GET | `/history` | `@jwt_required` | Paged user attempt history |
| POST | `/moderate` | `@jwt_required` | OpenAI content moderation passthrough |
| POST | `/generate_test` | `@jwt_required` | Trigger custom test generation pipeline (token-charged) |
| POST | `/custom_test` | `@jwt_required` | Variant of generate_test with user-supplied transcript |
| POST | `/<slug>/submit` | `@jwt_required` | MC test submission — full grading + ELO + BKT pipeline |
| POST | `/<slug>/submit-pinyin` | `@jwt_required` | Pinyin tone trainer submission |

### POST `/<slug>/submit` — submission contract

**Body:** `{responses: [{question_id, selected_answer}, ...], test_mode: 'reading'|'listening'|'dictation'}`

**Server flow:**
1. Resolve test by slug → test_id, language_id. 404 if not active.
2. Map `test_mode` → `test_type_id` via `DimensionService.get_test_type_id()`.
3. Call `process_test_submission(p_user_id, p_test_id, p_language_id, p_test_type_id, p_responses, p_was_free_test, p_idempotency_key)` — atomic. Validates answers server-side, records `test_attempts`, updates `user_skill_ratings` + `test_skill_ratings` (volatility-multiplied ELO via `calculate_elo_rating`).
4. Pass `question_results` to `VocabularyKnowledgeService.update_from_comprehension()` → calls `bkt_update_comprehension` per sense.
5. Run `apply_contextual_inference()` — dampened BKT bump for transcript senses not directly tested.
6. Build a 5-word word-quiz from question senses via `build_quiz_with_distractors()` (calls `get_word_quiz_candidates` + `get_distractors` RPCs).

**Response:** `{status, result: {score, total_questions, percentage, question_results, is_first_attempt, user_elo_change: {before, after, change}, test_elo_change: {...}, test_mode, attempt_id, word_quiz?: {candidates, attempt_id}}}`.

### POST `/<slug>/submit-pinyin` — Chinese-only

Body: `{correct_chars, total_chars, time_taken}`. Language must be `language_id=1` else 400. Synthesises a single response from `accuracy = correct_chars/total_chars`, then re-uses `process_test_submission` with `test_type_id=DimensionService.get_test_type_id('pinyin')`. Response: `{result: {accuracy, correct_chars, total_chars, time_taken, user_elo_change, test_elo_change, test_mode: 'pinyin', attempt_id}}`.

*Calls RPCs:* `process_test_submission`, `get_recommended_test`, `get_recommended_tests`, `bkt_update_comprehension`, `bkt_contextual_inference`, `get_word_quiz_candidates`, `get_distractors`.

---

## `/api/exercises` — [routes/exercises.py](../../routes/exercises.py)

The **daily mixed-session** surface — fundamentally different from `/api/vocab-dojo` (per-word ladder). As of Phase 9 the canonical builder is the SQL RPC `get_exercise_session(p_user_id, p_language_id, p_session_size, p_user_theta?)` ([migrations/phase9_get_exercise_session.sql](../../migrations/phase9_get_exercise_session.sql)); Python's role is to call the RPC, append up to 3 virtual jumbled-sentence picks from test transcripts, cache to `user_exercise_sessions`, and enrich for the frontend.

| Method | Path | Auth | Query / Body | Purpose |
|---|---|---|---|---|
| GET | `/` | `@jwt_required` | `language_id (req), exercise_type?, source_type?, complexity_tier?, limit≤100, offset` | Filterable exercise browse (used by admin/preview tools, not the daily session). Lazily joins `dim_word_senses` + `dim_vocabulary` for vocab exercises and runs `prepare_jumbled_content` for jumbled_sentence rows. |
| GET | `/session` | `@jwt_required` | `language_id` (req) | Cached daily mixed session via `ExerciseSessionService.get_or_create_daily_session()`. Returns `{session: {load_date, exercises[], progress, session_size}}`. |
| POST | `/session/complete` | `@jwt_required` | `{exercise_id, language_id}` | Marks the exercise complete in `user_exercise_sessions.completed_ids`. |
| POST | `/attempt` | `@jwt_required` | `{exercise_id, user_response?, is_correct, time_taken_ms?}` | Records `exercise_attempts` row, increments `exercises.attempt_count` / `correct_count`, runs BKT (gated by **server-derived** `is_first_attempt` — checks `exercise_attempts` for prior rows under `(user_id, exercise_id)`) and FSRS via `_update_fsrs_for_exercise`. Virtual exercises (`exercise_id.startswith('virtual-')`) short-circuit to a no-op success. |
| GET | `/types` | `@jwt_required` | `language_id` | Distinct `exercise_type` values for a language. |

*Calls RPCs:* `get_exercise_session`, `get_session_senses`, `get_word_quiz_candidates`, `bkt_update_exercise`, `bkt_apply_lapse_penalty`, `update_vocabulary_from_word_test`.

---

## `/api/vocab-dojo` — [routes/vocab_dojo.py](../../routes/vocab_dojo.py)

Per-word vocabulary ladder. Backed by [Phase 8 momentum bands](../../migrations/phase8_momentum_bands.sql) and [Phase 10 advancement/demotion](../../migrations/phase10_ladder_advancement_demotion.sql).

| Method | Path | Auth | Query / Body | Notes |
|---|---|---|---|---|
| GET | `/session` | `@jwt_required` | `language_id (req), count≤50 (default 20)` | Calls `_ensure_ladder_rows` (lazy-inits `user_word_ladder` for newly-uploaded senses) then `get_ladder_session(p_user_id, p_language_id, p_count)`. Adds `ladder_name` / `family` per row and runs `prepare_jumbled_content` for jumbled sentences. |
| POST | `/attempt` | `@jwt_required` | `{exercise_id, sense_id, is_correct, is_first_attempt, time_taken_ms?, language_id?, exercise_type?, ladder_level?, exercise_context?}` | `LadderService.record_attempt()` → `ladder_record_attempt` RPC (atomic family-BKT update, momentum-band scheduling, ring advance/demote per Phase 10, FSRS lapse path). |
| GET | `/word/<sense_id>/exercises` | `@jwt_required` | `language_id (req)` | Returns `{word, exercises[], assets[]}` — full per-sense rendering for the dojo word page. |
| POST | `/gate` | `@jwt_required` | `{sense_id, language_id, gate_name: 'gate_a'\|'gate_b'}` | `LadderService.assemble_gate()` — assembles a 3-exercise battery. |
| POST | `/gate/result` | `@jwt_required` | `{sense_id, gate_name, passed}` | If passed → `ladder_pass_gate` RPC; if failed → return-only (`{passed:false, word_state:'active'}`). |
| POST | `/stress-test` | `@jwt_required` | `{sense_id, language_id}` | Assembles the 8-exercise pre-mastery battery. |
| POST | `/stress-test/result` | `@jwt_required` | `{sense_id, language_id, score (0-1), passed}` | If passed → `ladder_graduate` (FSRS handoff); if failed → `{word_state:'relearning', stress_test_score, passed:false}`. |

*Calls RPCs:* `get_ladder_session`, `ladder_record_attempt`, `ladder_pass_gate`, `ladder_graduate`, `ladder_compute_p_known`, `fsrs_schedule_review`, `bkt_apply_lapse_penalty`.

---

## `/api/flashcards` — [routes/flashcards.py](../../routes/flashcards.py)

| Method | Path | Auth | Query / Body | Notes |
|---|---|---|---|---|
| GET | `/page` | `@jwt_required` | — | Renders `flashcards.html` (same template as `/flashcards` page route). |
| GET | `/due` | `@jwt_required` | `language_id (req)` | All cards with `due_date ≤ today` OR `state='new'`. Returns `{cards: [{card_id, sense_id, lemma, definition, pronunciation, example_sentence, audio_url, state, reps, due_date}], total}`. |
| POST | `/review` | `@jwt_required` | `{card_id, rating: 1\|2\|3\|4}` | Rating: 1=again, 2=hard, 3=good, 4=easy. Calls `services.vocabulary.fsrs.schedule_review(CardState, rating)` then updates `user_flashcards`. Treats rating≥3 as correct and calls `VocabularyKnowledgeService.update_from_word_test` (BKT). Returns `{next_due, new_state, stability}`. |
| GET | `/stats` | `@jwt_required` | `language_id (req)` | `{stats: {total_cards, due_today, by_state}}`. |
| POST | `/skip` | `@jwt_required` | `{card_id}` | Hard-deletes the row. |

*Note:* No `bkt_*` RPC used here directly — `VocabularyKnowledgeService.update_from_word_test` orchestrates the BKT update server-side.

---

## `/api/vocabulary` — [routes/vocabulary.py](../../routes/vocabulary.py)

| Method | Path | Auth | Body | Notes |
|---|---|---|---|---|
| POST | `/word-quiz` | `@jwt_required` | `WordQuizRequest = {attempt_id, language_id, results: [{sense_id, is_correct, response_time_ms?}, ...]}` | Post-test word quiz submission. Calls `VocabularyKnowledgeService.record_word_quiz_results()` which inserts `word_quiz_results` rows and calls `update_vocabulary_from_word_test` per sense. Returns `{updates: [{sense_id, p_known_before, p_known_after, status}]}`. |

The `/api/vocabulary/extract` endpoint lives on `app.py` core, not this blueprint.

---

## `/api/corpus` — [routes/corpus.py](../../routes/corpus.py)

Mixed user + admin surface.

| Method | Path | Auth | Body / Query | Notes |
|---|---|---|---|---|
| POST | `/ingest` | **`@admin_required`** | `{source_type: 'url'\|'text', language_id, tags?, url? (url), text? (text), title? (text), analyze_style?}` | Triggers `CorpusIngestionService.ingest_url()` or `.ingest_text()` — fetches, normalises, tokenises, extracts collocations, optionally runs the style pipeline. Returns `{corpus_source_id}`. |
| GET | `/packs` | `@jwt_required` | `language_id` | `CollocationPackService.get_packs_for_user()` — calls `get_packs_with_user_selection(p_language_id, p_user_id)` RPC. |
| POST | `/packs/<pack_id>/select` | `@jwt_required` | — | Idempotent upsert into `user_pack_selections`. |
| POST | `/style-analyze` | **`@admin_required`** | `{corpus_source_id, language_id}` | Re-runs `CorpusIngestionService._run_style_pipeline()` for an existing source. Returns `{style_profile_id}`. |
| GET | `/style-profile/<source_id>` | **`@admin_required`** | — | Reads from `corpus_style_profiles`. |
| POST | `/style-packs` | **`@admin_required`** | `{corpus_source_id, pack_name, description?, language_id}` | `StylePackService.create_pack_from_profile()`. |
| GET | `/style-packs` | `@jwt_required` | `language_id` | List packs. |
| GET | `/style-packs/<pack_id>/items` | `@jwt_required` | — | Items in a pack. |

---

## `/api/mystery` — [routes/mystery.py](../../routes/mystery.py)

Five-scene comprehension series. All `@jwt_required`.

| Method | Path | Query / Body | Notes |
|---|---|---|---|
| GET | `/` | `language_id (req), difficulty?, limit?` | List active mysteries. |
| GET | `/recommended` | `language_id (req)` | ELO-matched: `get_recommended_mysteries(p_user_id, p_language_id)` RPC. |
| GET | `/<slug>` | `mode? ('reading'\|'listening')` | Returns `{mystery, progress}`. Auto-creates `mystery_progress` row on first access. |
| GET | `/<slug>/scene/<n>` | — | 1-5 only. Returns `{scene, progress}`. Enforces progression: `scene_number ≤ progress.current_scene`. In listening mode, scene transcript is hidden (`transcript_locked: true`) until questions are answered correctly. |
| POST | `/<slug>/scene/<n>/submit` | `{responses: [{question_id, selected_answer}]}` | `MysteryService.submit_scene()` — must answer all correctly to unlock the clue. Updates `mystery_progress.scene_responses` JSONB. |
| POST | `/<slug>/submit` | `{responses}` | Finale: `MysteryService.submit_finale()` → `process_mystery_submission` RPC (ELO + scoring). Then `_update_mystery_vocabulary` runs BKT on target_vocab_ids using the score ratio. |

*Calls RPCs:* `get_recommended_mysteries`, `process_mystery_submission`.

---

## `/api/conversations` — [routes/conversations.py](../../routes/conversations.py)

| Method | Path | Auth | Query | Notes |
|---|---|---|---|---|
| GET | `/` | `@jwt_required` | `language_id (req), complexity_tier?, limit, offset` | List active conversations with nested scenario + persona_pair joins. |
| GET | `/<conversation_id>` | `@jwt_required` | — | Full conversation with `turns` and persona metadata. Adds `speaker_name` to each turn by joining `turns[*].persona_id` → persona name. |

Read-only — generation lives in `services/conversation_generation/` and is triggered via the admin dashboard.

---

## `/api/users` — [routes/users.py](../../routes/users.py)

All `@jwt_required`.

| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/elo` | — | `TestService.get_user_elo_summary()` — per-language/test-type ELO across all `user_skill_ratings` rows. |
| GET | `/tokens` | — | Calls `grant_daily_free_tokens(p_user_id)` RPC atomically (server-side date check, no replay), then reads `users.tokens`. Returns `{total_tokens, free_tokens_today, last_free_token_date}`. |
| GET | `/profile` | — | Selects `id, email, display_name, email_verified, total_tests_taken, total_tests_generated, last_activity_at, subscription_tier_id, created_at, last_login`. |
| PATCH | `/preferences` | `{session_size?}` | Validates `MIN_EXERCISE_SESSION_SIZE ≤ size ≤ MAX_EXERCISE_SESSION_SIZE`, then merges into `users.exercise_preferences` JSONB. |

*Note:* `grant_daily_free_tokens` is invoked here but does not appear in the public-schema RPC catalogue dump as of 2026-05-12 — verify before relying on it (may live in `auth.*` schema or be unapplied).

---

## `/api/payments` — [routes/payments.py](../../routes/payments.py)

| Method | Path | Auth | Body | Notes |
|---|---|---|---|---|
| GET | `/token-packages` | none | — | Returns `Config.TOKEN_PACKAGES` (static, defined in `config.py`). |
| POST | `/create-intent` | `@jwt_required` | `PaymentIntentRequest = {package_id}` | Creates a Stripe `PaymentIntent` with amount from `Config.TOKEN_PACKAGES[package_id]`. Metadata: `{user_email, package_id, tokens}`. Returns `{client_secret, amount, tokens}`. 500 if Stripe key missing; 400 if package_id unknown. |

*Stripe webhook is currently NOT registered in `app.py` — token grants from real payments go through `process_stripe_payment(p_user_id, p_tokens_to_add, p_payment_intent_id, p_package_id, p_amount_cents)` RPC but the webhook handler that calls it is missing from this blueprint. Verify before claiming the payment flow is end-to-end.*

---

## `/api/reports` — [routes/reports.py](../../routes/reports.py)

| Method | Path | Auth | Body | Notes |
|---|---|---|---|---|
| POST | `/submit` | `@jwt_required` | `{report_category, description (≥10 chars), current_page?, test_id?, test_type?, user_agent?, screen_resolution?}` | Inserts into `user_reports`. `report_category` must be one of: `test_answer_incorrect`, `test_load_error`, `website_crash`, `improvement_idea`, `audio_quality`, `other`. Returns `{report_id}` with 201. |

---

## `/api/admin/vocab` — [routes/vocab_admin.py](../../routes/vocab_admin.py)

All routes guarded by `@admin_required` (requires `users.subscription_tier IN ('admin','moderator')`). The blueprint is registered in **production** ([app.py:262](../../app.py#L262)), so the decorator is the only access boundary.

> *The local admin dashboard's Vocab Browser tab does not hit these directly — it uses the auth-free local mirror at `/admin/api/vocab/*` (see the **Vocab browser mirror** section under admin_local.py below). The production-facing routes here are still hit by [templates/admin_vocab_preview.html](../../templates/admin_vocab_preview.html) (at `/admin/vocab-preview`), which uses `authFetch` to send the operator's admin JWT.*

| Method | Path | Auth | Body / Query | Notes |
|---|---|---|---|---|
| POST | `/upload-words` | `@admin_required` | `{language_id, words: [{lemma, definition?, pos?, complexity_tier?}, ...]}` | Three-step pipeline: (1) upsert `dim_vocabulary` + `dim_word_senses`, (2) `VocabAssetPipeline.generate_batch()` to fill `word_assets`, (3) `LadderExerciseRenderer.render_all()` to materialise `exercises` rows. Returns `{senses_processed, assets_generated, exercises_rendered, ...}`. |
| POST | `/generate-assets` | `@admin_required` | `{language_id, sense_ids[], force?}` | Asset pipeline only. `force=true` regenerates even if `word_assets` row exists. |
| POST | `/render-exercises` | `@admin_required` | `{language_id, sense_ids[]}` | Exercise rendering from existing `word_assets` rows. |
| GET | `/words` | `@admin_required` | `language_id (req), limit≤200, offset` | Paged word list with `has_prompt1/2/3`, `exercise_count`, `levels[]` per sense. |
| POST | `/word/<sense_id>/wipe` | `@admin_required` | — | Hard-deletes all `exercises` + `word_assets` for the sense (used before regenerate). |
| DELETE | `/word/<sense_id>/level/<level>` | `@admin_required` | — | Soft-deletes (`is_active=false`) ladder-level exercises. |
| GET | `/word/<sense_id>/preview` | `@admin_required` | `language_id (req)` | Returns `{word, assets, exercises, ladder_levels}` for the admin preview UI. |

---

## Admin Pipeline — [routes/admin_local.py](../../routes/admin_local.py) (only mounted by `admin_app.py`)

Url-prefix `/admin`. ⚠ No auth decorators — relies on being a local-only app. Single-page dashboard at `/admin` with **10 tabs**, each backed by a `_do_*` function dispatched into a daemon thread via [`services.task_runner.run_in_thread`](../../services/task_runner.py). Tabs stream progress via Server-Sent Events; stop button POSTs to `/admin/api/task-stop/<task_id>` to set a `threading.Event` consumed by `is_task_stopped()`.

### Dashboard infrastructure

| Method | Path | Notes |
|---|---|---|
| GET | `/` | Renders `admin_dashboard.html`. |
| GET | `/api/task-status/<task_id>` | SSE stream — yields one event per log line until the task completes. |
| POST | `/api/task-stop/<task_id>` | Sets the stop event. |

### Reference data lookups (GETs used to populate dropdowns)

| Path | Returns |
|---|---|
| `/api/languages` | `dim_languages` active rows |
| `/api/grammar-patterns` | `dim_grammar_patterns` filtered by language |
| `/api/word-senses` | `dim_word_senses` joined with vocab, filterable |
| `/api/collocations` | `corpus_collocations` filtered by language |
| `/api/corpus-sources` | `corpus_sources` rows |
| `/api/topics` | `topics` rows |
| `/api/categories` | `categories` rows |
| `/api/queue-counts` | Counts across `production_queue` by status |
| `/api/conversation-domains` | `conversation_domains` rows |

### Vocab browser mirror

Local-only duplicates of the dashboard-relevant routes in [routes/vocab_admin.py](../../routes/vocab_admin.py). Handler bodies are copied verbatim; the only differences are URL prefix (`/admin/api/vocab/*` vs `/api/admin/vocab/*`) and the absence of `@admin_required` (auth is provided by deployment posture on admin_local_bp). Added 2026-05-13 so the dashboard's Vocab Browser tab works after the production routes were gated. **Keep in lockstep with vocab_admin.py.**

| Method | Path | Body / Query | Mirrors |
|---|---|---|---|
| GET | `/api/vocab/words` | `language_id (req), limit≤200, offset` | `vocab_admin.list_words` |
| GET | `/api/vocab/word/<sense_id>/preview` | `language_id (req)` | `vocab_admin.preview_word` |
| POST | `/api/vocab/word/<sense_id>/wipe` | — | `vocab_admin.wipe_word` |
| DELETE | `/api/vocab/word/<sense_id>/level/<level>` | — | `vocab_admin.remove_level` |

### Pipeline runners (POST, all return `{task_id}` immediately)

| Path | Runner | Body | Purpose |
|---|---|---|---|
| `/api/run/corpus-ingest` | `_do_corpus_ingest` | `{source_type, language_id, url?, text?, title?, tags?, analyze_style?}` | URL/text → ingest + collocation extraction (+ optional style pipeline). |
| `/api/run/topic-generation` | `_do_topic_generation` / `_do_custom_topic_insert` | `{category_id?, language_id?, mode: 'auto'\|'manual', topics?}` | Auto-generate via `TopicGenerationOrchestrator` or insert hand-written topics. |
| `/api/run/test-generation` | `_do_test_generation` | `{language_ids[], count=20, test_type='listening', difficulty?, dry_run?}` | Drains `production_queue` via `TestGenerationOrchestrator`. |
| `/api/run/exercise-generation` | `_do_exercise_generation` | `{language_id, source: 'grammar'\|'vocabulary'\|'collocation', limit?, ids?}` | Calls `run_grammar_batch` / `run_vocabulary_batch` / `run_collocation_batch`. |
| `/api/run/style-analysis` | `_do_style_analysis` | `{language_id, source: 'existing'\|'new', ...}` | `CorpusIngestionService._run_style_pipeline`. |
| `/api/run/conversation-generation` | `_do_conversation_generation` | `{language_id, domain_id?, limit?}` | `ConversationBatchProcessor`. |
| `/api/run/mystery-generation` | `_do_mystery_generation` | `{language_id, count?, difficulty?, archetype?}` | `MysteryGenerationOrchestrator`. |
| `/api/run/pinyin-backfill` | `_do_pinyin_backfill` | `{test_ids?, all?, resolve_polyphones?}` | Recomputes `tests.pinyin_payload` via `pinyin_service.process_passage()`. |
| `/api/run/full-pipeline` | `_do_full_pipeline` | `{language_id}` | Sequential idempotent backfill chain: vocab → token maps → question sense ids → test skill ratings → exercises → collocations. |
| `/api/run/vocab-generate` | `_do_vocab_generate` | `{language_id, sense_ids[]}` | Asset pipeline + L1 audio synthesis + exercise rendering for selected senses. |
| `/api/run/l1-audio-backfill` | `_do_l1_audio_backfill` | `{language_id}` | Per [2026-05-12 ship entry](../log.md) — iterates active L1 exercises and regenerates `audio_url` via `AudioSynthesizer + audio_voice.pick_voice`. |
| `/api/run/irt-calibration` | `_do_irt_calibration` | `{language_id?, min_attempts?}` | Per [Phase 11](../../migrations/phase11_irt_selection.sql) — 2PL MLE fit of `irt_difficulty` / `irt_discrimination` for items with ≥ `min_attempts` (default 20) first-attempt rows. Omit `language_id` to sweep every active language under the `irt_try_lock` advisory lock. |

### Model Arena — [routes/model_arena.py](../../routes/model_arena.py)

Url-prefix `/admin/arena` (mounted by `admin_app.py`). ⚠ No auth decorators.

| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/api/models` | query `?refresh=1` to force re-fetch | OpenRouter model catalogue, cached 1h. Returns `{models: [{id, name, context_length, prompt_cost, completion_cost}]}`. |
| POST | `/api/run/arena` | `{contestant_models: [2-5 ids], judge_model, language_id, language_name?, language_code?, generation_types: ['prose'\|'questions'], num_trials: 1-50}` | Spawns `_do_arena_run` via `run_in_thread`. Returns `{task_id}` 202. |
| GET | `/api/arena-results/<task_id>` | — | In-process result, falls back to `data/arena_runs/<task_id>.json`. |

---

## RPC Call Site Map

Every Supabase RPC currently invoked from Python, with its caller. See [database/rpcs.tech.md](../database/rpcs.tech.md) for the full RPC signatures.

| RPC | Called from | Note |
|---|---|---|
| `process_test_submission` | `routes/tests.py: _call_submission_rpc` | DEFINER. Atomic test grading + ELO + token charge + idempotency. |
| `process_mystery_submission` | `services/mystery_service.py` | DEFINER. Mystery finale grading. |
| `process_stripe_payment` | (intended for webhook — handler missing) | DEFINER. Atomic token grant. |
| `add_tokens_atomic` | `services/payment_service.py` | DEFINER. Generic token credit with idempotency. |
| `can_use_free_test` | `services/test_service.py` | DEFINER. Per-user daily limit check. |
| `get_token_balance` | `services/payment_service.py` | DEFINER. |
| `get_recommended_test` | `routes/tests.py:get_random_test` | DEFINER. Single ELO-matched test. Excludes attempted tests (V3, 2026-05-08). |
| `get_recommended_tests` | `routes/tests.py:get_recommended_tests` | DEFINER. Curated list of up to 9 ELO-matched tests (3 per type: listening/reading/dictation). Signature: `(p_user_id uuid, p_language_id smallint)`. |
| `get_recommended_mysteries` | `routes/mystery.py:get_recommended` | DEFINER. |
| `get_packs_with_user_selection` | `services/corpus/pack_service.py` | INVOKER. |
| `get_vocab_recommendations` | `services/test_service.py` | DEFINER. Vocab-aware test matching. |
| `get_ladder_session` | `routes/vocab_dojo.py:get_dojo_session` | INVOKER. Phase 8. |
| `ladder_record_attempt` | `services/vocabulary_ladder/ladder_service.py` | INVOKER. Phase 8 + Phase 10. |
| `ladder_pass_gate` | `LadderService.pass_gate` | INVOKER. |
| `ladder_graduate` | `LadderService.graduate` | INVOKER. FSRS handoff. |
| `ladder_compute_p_known` | (helper, inlined into other RPCs) | IMMUTABLE. |
| `fsrs_schedule_review` | Pure-SQL FSRS scheduler used inside `ladder_*` and `services/vocabulary/fsrs.py` mirror | STABLE. |
| `get_exercise_session` | `services/exercise_session_service.py:_compute_session` | INVOKER. Phase 9 + Phase 11. Two overloads: 3-arg legacy and 4-arg with `p_user_theta`. |
| `get_session_senses` | Inlined into `get_exercise_session` CTE | INVOKER. |
| `bkt_update_comprehension` | `VocabularyKnowledgeService.update_from_comprehension` | IMMUTABLE. |
| `bkt_update_word_test` | `VocabularyKnowledgeService.update_from_word_test` | IMMUTABLE. |
| `bkt_update_exercise` | `VocabularyKnowledgeService.update_from_exercise` | IMMUTABLE. |
| `bkt_apply_decay` | Inlined; both 3-arg flat-half-life and 4-arg FSRS-stability variants exist. | IMMUTABLE. |
| `bkt_apply_lapse_penalty` | `services/vocabulary_ladder/ladder_service.py:_update_fsrs` | VOLATILE. |
| `bkt_contextual_inference` | `VocabularyKnowledgeService.apply_contextual_inference` | VOLATILE. |
| `bkt_infer_from_frequency` | `VocabularyKnowledgeService._trigger_frequency_inference` | VOLATILE. |
| `bkt_phase` / `bkt_phase_thresholds` | Read by `VocabularyKnowledgeService.get_phase_thresholds` | IMMUTABLE. |
| `get_word_quiz_candidates` | `VocabularyKnowledgeService.build_quiz_with_distractors` | DEFINER. |
| `get_distractors` | Same | DEFINER. |
| `update_vocabulary_from_test` | (RPC, also exposed as trigger name) | VOLATILE. |
| `update_vocabulary_from_word_test` | `VocabularyKnowledgeService` (2 overloads, 4-arg legacy and 5-arg with exercise_type) | VOLATILE. |
| `match_topics` | `services/topic_generation/database_client.py` | DEFINER. Embedding-similarity dedup. |
| `tests_containing_sense` | `services/vocabulary/...` | STABLE. |
| `batch_lookup_lemmas` | `services/vocabulary/pipeline.py` | DEFINER, STABLE. |
| `get_top_collocations_for_sources` | `services/corpus/pack_service.py` | STABLE. |
| `irt_apply_calibration` | `services/irt/calibrator.py:apply_results` | DEFINER. |
| `irt_compute_user_theta` | `services/irt/calibrator.compute_user_theta_for_selection` + `services/exercise_session_service._compute_session` | STABLE. |
| `irt_try_lock` / `irt_release_lock` | `services/irt/calibrator.calibrate_all_active_languages` | DEFINER. Postgres advisory lock pair `(8901234567890123)` for nightly job. |
| `get_model_for_task` | `services/prompt_service.get_template_config` (indirectly) | STABLE. |
| `get_prompt_template` | `services/prompt_service` | STABLE. |
| `is_admin` / `is_moderator` / `is_org_member` / `get_org_role` | RLS policy expressions | DEFINER, STABLE. |
| `anonymize_user_data` | (offline ops, not in route code yet) | DEFINER. |
| `sync_exercise_history` | Trigger on `exercise_attempts` INSERT | — |
| `handle_new_user` | Trigger on `auth.users` insert | — |
| `create_user_dependencies` | Trigger on `public.users` INSERT | Initialises dependent rows. |
| `update_user_vocab_stats` | Defined but no INSERT trigger currently bound to it | Verify before relying. |

Non-application RPCs (`vector_*`, `halfvec_*`, `sparsevec_*`, `_int*`, `g_int*`, `gtrgm_*`, `gin_*`, `hnsw_*`, `ivfflat_*`, etc.) come from `pgvector`, `pg_trgm`, and `intarray` and are not called by application code directly.

## Cross-cutting middleware

- [`middleware/auth.py`](../../middleware/auth.py) — JWT extraction + Supabase verification, with a service-role bypass for batch jobs. Also exposes class-based `AuthMiddleware(supabase_client)` for legacy callers; new code should use the module-level decorators.
- [`models/requests.py`](../../models/requests.py) — Pydantic request schemas (`VocabularyExtractRequest`, `ErrorLogRequest`, `PaymentIntentRequest`, `WordQuizRequest`). Validation errors → `bad_request(e.errors()[0]['msg'])`.
- [`utils/responses.py`](../../utils/responses.py) — JSON response shape helpers (see Authentication section).
- [`utils/validation.py`](../../utils/validation.py) — `validate_email` and other shared validators.

## Related Pages

- [[api/rpcs]] — Prose overview of the API design philosophy
- [[overview/project.tech]] — Architecture, deployment, scheduler, full directory tree
- [[database/rpcs.tech]] — Full Postgres RPC catalogue with SQL definitions
- [[database/schema.tech]] — Tables, columns, FKs, indexes, triggers, policies
- [[features/vocab-dojo.tech]] — `/api/vocab-dojo` deep dive
- [[features/exercises.tech]] — `/api/exercises` (daily mixed session) deep dive
- [[features/comprehension-tests.tech]] — `/api/tests` deep dive
- [[features/mysteries.tech]] — `/api/mystery` deep dive
- [[features/model-arena.tech]] — `/admin/arena/*` deep dive
