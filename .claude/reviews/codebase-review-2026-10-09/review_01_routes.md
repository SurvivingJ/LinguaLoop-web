# Review 01 - app.py / wsgi.py / config.py / routes / middleware / utils / models

Method: AST audit of every `@route` and its decorators (all auth-less routes enumerated), full read of every routes/*.py except the bulk of admin_local.py (skimmed: entry, guard, run/* handlers, upload paths), middleware/*, utils/*, models/*, app.py, config.py; frontend usage cross-checked by scanning static/ + templates/ for each URL; library behaviour checked in venv (supabase 2.6.0 / gotrue).

Auth coverage summary: every non-admin route in the production blueprint set has `jwt_required`/`admin_required` EXCEPT, deliberately: `/api/auth/send-otp|verify-otp|refresh-token|device-restore`, `/api/payments/token-packages`, `/api/tests/<slug>` (tests.py:249, auth decorator commented out), `/api/tests/test/<identifier>` (tests.py:1012, commented out), `/api/health`, `/api/config`, `/api/metadata`, and HTML page routes. `admin_local_bp` (36 routes) and `model_arena_bp` (3) have no auth, loopback-only (gitignored admin_app.py). No IDOR found: every user-owned read/write filters on `g.current_user_id`, and DT submission/card routes re-check ownership (dual_translation.py:176, :321).

---

### [HIGH] Shared service-role Supabase client is re-authenticated as the last user who logged in
- Category: security / correctness
- Location: services/auth_service.py:51, :108, :293, :323 (called from routes/auth.py:131,:156,:263,:312); services/supabase_factory.py:41-45
- Problem: `AuthService` runs `sign_in_with_otp`/`verify_otp`/`refresh_session` on the process-wide service-role client (`get_supabase_admin()`). In supabase-py 2.6.0 the client subscribes to auth events and, on `SIGNED_IN`/`TOKEN_REFRESHED`, overwrites `options.headers['Authorization']` with the user's access token and resets postgrest. After any login/refresh, every later "admin" query on that worker runs with that user's JWT (RLS applies, wrong identity) until its token expires, after which PostgREST rejects with expired-JWT. `mint_session_for_user` (device-restore) does the same.
- Evidence: venv/Lib/site-packages/supabase/_sync/client.py:92 `self.auth.on_auth_state_change(self._listen_to_auth_events)` and :293-304 (`access_token = session.access_token ... self.options.headers["Authorization"] = ...`); gotrue_client.py:573 `verify_otp` -> `_notify_all_subscribers("SIGNED_IN")`. Factory returns one shared `_service_client`. Mechanism confirmed from library source; runtime symptoms not exercised.
- Fix: do all auth-flow calls (send/verify OTP, refresh, generate_link/verify_otp) on a throwaway `create_client(url, key)` per call (or a dedicated auth-only client), never the shared service-role singleton; or construct the service client with `ClientOptions(auto_refresh_token=False, persist_session=False)` and reset the header after auth calls.

### [HIGH] Any logged-in user can trigger unbounded expensive LLM generation (word-list import)
- Category: security (cost / DoS)
- Location: routes/word_list_import.py:213-249
- Problem: `/api/word-list/submit` is `@jwt_required` only; each call spawns an unbounded daemon thread (no per-user in-flight cap, no rate limit, no token cost) that runs the 3-prompt ladder LLM pipeline (~5.5 min and real $ per new sense). 50 words/request, unlimited requests, per-word string length unchecked.
- Evidence: line 237-242 `threading.Thread(...daemon=True).start()`; only limit is `MAX_WORDS_PER_SUBMIT = 50` (line 95); no limiter exists anywhere (grep for limiter/rate_limit in app/routes/middleware: 0 hits; flask-limiter not in requirements).
- Fix: per-user concurrency cap (e.g. reject if a batch is already running / cap rows in user_word_watchlist per day), max word length, and a global worker pool/queue instead of thread-per-request; gate behind token cost or tier.

### [HIGH] Unauthenticated loopback-only admin is open to browser-driven CSRF / DNS rebinding, and the loopback guard is bypassable via X-Forwarded-For
- Category: security
- Location: middleware/local_only.py:76-83; routes/admin_local.py:540,559,611,620,629,643,658,672,693,702,711,720 (`request.get_json(force=True)`); routes/model_arena.py:58; app.py:72 (ProxyFix); admin_app.py:20-21
- Problem: (a) No CSRF/Origin/Host check on destructive or spend-incurring POSTs (`/admin/api/vocab/word/<id>/wipe` takes no body at all). Any web page the operator visits can fire a no-cors POST at http://127.0.0.1:<port>/admin/...; `get_json(force=True)` even accepts `text/plain` simple requests, and a rebinding hostname defeats the loopback check. (b) `create_app()` installs `ProxyFix(x_for=1)`, so `request.remote_addr` is taken from `X-Forwarded-For`; any off-box client can send `X-Forwarded-For: 127.0.0.1` and pass `is_loopback` if the admin app is ever bound wider (ADMIN_HOST / ADMIN_ALLOW_REMOTE container case).
- Evidence: local_only.py uses `request.remote_addr` only; app.py:72 `ProxyFix(app.wsgi_app, x_for=1, ...)` wraps every `create_app()`, including admin_app.py's.
- Fix: in `enforce_loopback` also require `Host` in {localhost,127.0.0.1,[::1]} and reject cross-site requests (require a custom header such as `X-Admin-Token`/same-origin `Origin`, drop `force=True`); read `request.environ['REMOTE_ADDR']` before ProxyFix (or skip ProxyFix in admin_app). Prior C-1 fix is otherwise in place.

### [MEDIUM] Production app imports app.py at module level AND wsgi.py builds a second app -> two schedulers/service stacks per gunicorn worker
- Category: correctness
- Location: app.py:735; wsgi.py:6-9; Procfile (`gunicorn wsgi:app --workers 2`)
- Problem: `from app import create_app` executes app.py's module-level `app = create_app()` (line 735), then wsgi.py calls `create_app()` again. Each call re-initialises Supabase factory, registers blueprints on a fresh Flask object and starts its own `BackgroundScheduler` (`_initialize_scheduler`), so every worker runs 2 schedulers with 7 cron jobs each (only advisory locks prevent double work; `auth_bp.auth_service` etc. are overwritten by whichever app registered last).
- Evidence: app.py:735 `app = create_app()`; wsgi.py:6 `from app import create_app` / :9 `app = create_app()`; blueprint-level attributes `auth_bp.auth_service/device_service` set per call (app.py:~323).
- Fix: guard app.py's module-level instantiation (`if __name__ == '__main__'`) or have wsgi.py do `from app import app`.

### [MEDIUM] Public, unauthenticated test endpoints return the answer key
- Category: security
- Location: routes/tests.py:249-265 (+ services/test_service.py:154-158), routes/tests.py:1012-1073 (select list line ~1048: `answer, answer_explanation`)
- Problem: `GET /api/tests/<slug>` and `GET /api/tests/test/<identifier>` have their `@supabase_jwt_required` commented out and return every question's correct `answer`. Anyone (no account) can scrape all answers; a logged-in user can read answers before submitting and farm ELO (graded server-side but trivially passable).
- Evidence: `#@supabase_jwt_required` at tests.py:250 and :1013; `'answer': q.get('correct_answer', '')` in get_test_by_slug.
- Fix: strip `answer`/`answer_explanation` from the pre-submit payload (return them from the submit RPC response, which already returns `question_results`); keep the public route to non-answer fields.

### [MEDIUM] Client-asserted scores/outcomes accepted without server verification (ELO and mastery inflation)
- Category: security (integrity)
- Location: routes/tests.py:647-735 (pinyin), :740-830 (pitch accent); routes/classifier_drill.py:54-137; routes/counter_drill.py (same); routes/vocab_dojo.py:256-290 (`passed`), :330-370 (`score`,`passed`); routes/study_session.py:454; routes/tests.py:161 (`daily-load/complete`)
- Problem: the server records `correct_chars/total_chars`, `correct_units/total_units`, `correct_items/total_items`, gate `passed=true`, stress-test `passed/score` exactly as the client claims. The RPCs only check `0 <= correct <= total`, not that `total` matches the test or that a session was issued, so `{correct:1,total:1}` repeated with fresh idempotency keys yields perfect accuracy and ELO gains; `passed:true` graduates any sense. `complete-block` and `daily-load/complete` also let a client mark any block/test_id done (test_id not checked against today's `test_ids`, services/test_service.py:714-746).
- Evidence: tests.py:660-668 / :763; migrations/process_pinyin_submission.sql:53-57 (range check only); vocab_dojo.py:274-281.
- Fix: bind totals to server-known values (pinyin/pitch payload length, issued drill session size), verify gate/stress results server-side from stored attempts, validate test_id/block_id membership.

### [MEDIUM] SSRF in corpus URL ingest (admin/moderator), error text echoed
- Category: security
- Location: routes/corpus.py:36-62; services/corpus/ingestion.py:60
- Problem: `source_type=url` fetches any URL with `httpx.get(follow_redirects=True)` - no scheme/host allow-list or private-range block (cloud metadata, internal services) - and returns `str(exc)` with 502, giving a response oracle. `admin_required` also admits `moderator` tier.
- Evidence: ingestion.py:60-66; corpus.py:62 `return api_error(str(exc), 502)`.
- Fix: allow only http(s), resolve and reject private/link-local/loopback IPs (re-check after redirects), cap response size, return a generic error; restrict to `admin` tier.

### [MEDIUM] No rate limiting anywhere; OTP endpoints enumerate users and can be abused (prior finding still open)
- Category: security
- Location: routes/auth.py:117-137, :140-237; services/auth_service.py:68-73
- Problem: `/send-otp` and `/verify-otp` are unauthenticated with no per-IP/email throttle (only Supabase's own limits); `send_otp` with `is_registration=false` returns `USER_NOT_FOUND`/"No account found", which enumerates registered emails. Same absence applies to LLM-backed endpoints (`/api/dual-translation/<id>/submit` - `reproduction` has no length cap, routes/dual_translation.py:158-160; `/api/vocabulary/extract` - `text` has no max_length, models/requests.py:24-26, app.py:691).
- Evidence: grep for limiter in app.py/routes/middleware = 0; requirements.txt has no flask-limiter.
- Fix: add Flask-Limiter (storage-backed) with strict budgets on auth routes and LLM-calling routes; return a uniform response from send-otp; cap `reproduction`/`text` lengths (Config.MAX_INPUT_LENGTH already exists and is unused for these).

### [MEDIUM] Payments blueprint is half-built: creates Stripe PaymentIntents but nothing ever fulfils them
- Category: legacy/dead + correctness
- Location: routes/payments.py:26-64; services/payment_service.py:229 (`handle_successful_payment`, no caller)
- Problem: `create-intent` charges users via PaymentIntent (metadata user_id/tokens), but there is no webhook route and no caller of `handle_successful_payment`, so a successful payment credits nothing; also no FE references `/api/payments/*`, `token-packages`, or `/api/users/tokens`. If ever wired, the webhook will need `stripe.Webhook.construct_event` signature verification (none exists today).
- Evidence: grep for `webhook|construct_event|handle_successful_payment` in non-test .py: only the def and a comment; static/templates scan for `payments`: 0 hits.
- Fix: either remove the blueprint until a verified webhook exists, or add `POST /api/payments/webhook` with signature verification + idempotent fulfilment.

### [MEDIUM] Concurrent read-modify-write on JSON arrays loses updates
- Category: correctness
- Location: routes/study_session.py:513-530 (`completed_blocks`), services/test_service.py:732-739 (`completed_test_ids`)
- Problem: both handlers read an array, append in Python and write it back. Two near-simultaneous completions (two tabs / retry) overwrite each other; `_record_surface_progress` fires only for the "newly_completed" branch, so a lost write can double-credit later or lose credit.
- Fix: do the append in SQL (`array_append ... WHERE NOT block = ANY`) via an RPC, or use an optimistic `updated_at` check.

### [LOW] Server exceptions echoed to clients
- Category: security (info disclosure)
- Location: routes/tests.py:88 (`f"Moderation failed: {str(e)}"`); routes/model_arena.py:40,92; routes/corpus.py:62,111; routes/vocab_admin.py:80; services/auth_service.py:136 (`Verification failed: {str(e)}`, returned by routes/auth.py:231)
- Problem: raw exception text (upstream URLs, Supabase/PostgREST messages) reaches clients, including unauthenticated callers of verify-otp.
- Fix: log server-side, return a generic message/code.

### [LOW] Unbounded / non-int pagination params can raise 500 or fetch huge ranges
- Category: correctness
- Location: routes/tests.py:191 (`limit` no cap), :1171-1172; routes/exercises.py:32-33 (`min(None,100)` TypeError on non-int limit; negative values); routes/classifier_drill.py:41 and routes/counter_drill.py (`min(request.args.get('count',20,type=int),40)` with non-int -> `min(None,40)` TypeError); routes/vocab_admin.py:177; tests.py:200 `int(difficulty)` ValueError
- Fix: shared helper `int_arg(name, default, lo, hi)` that clamps and tolerates bad input.

### [LOW] `.single()` followed by "not found" branch is unreachable (500 instead of 404)
- Category: correctness
- Location: routes/flashcards.py:129-139 (`card_resp ... .single()` then `if not card_resp.data`), routes/tests.py:600-606,682-690 (same pattern for slug lookups), routes/vocab_admin.py preview
- Problem: postgrest `.single()` raises on 0 rows, so a missing card/test hits the generic `except` and returns 500 "Failed to submit review" instead of the intended 404.
- Fix: use `.limit(1)` / `maybe_single()` and test `.data`.

### [LOW] CORS: duplicate preflight handler, reflective origin with credentials when `*` configured, PATCH not allow-listed
- Category: security / redundancy
- Location: app.py:101-143
- Problem: flask-cors already answers preflights; the hand-rolled `before_request` repeats it for every path (not just /api/*), echoes any Origin when `"*"` is in CORS_ORIGINS together with `Allow-Credentials: true`, and both lists omit `PATCH` though users.py uses PATCH (cross-origin PATCH preflight fails; same-origin unaffected). Default config is localhost-only, so only misconfiguration exposes it (unchanged from prior review).
- Fix: delete the manual handler; reject `*` when credentials are on; add PATCH.

### [LOW] Unauthenticated admin HTML page route and health detail
- Category: security
- Location: app.py:636 (`/admin/vocab-preview`), app.py:650-665 (`/api/health`)
- Problem: the preview page shell is served without auth (its data calls are admin-gated, so only the template leaks); `/api/health` publicly reveals which backends (openai/r2/stripe/vocab) are configured.
- Fix: minimal public `{status:ok}`; serve admin pages only behind admin auth or drop.

### [LOW] Redirect handlers interpolate raw query string
- Category: security
- Location: routes/exercises.py:147-150, routes/vocab_dojo.py:26-29
- Problem: `language_id` is concatenated unescaped into the redirect URL (`...&language_id={language_id}`), allowing parameter injection (e.g. `1&debug=1`). Target stays same-origin `/api/practice/session`, so not an open redirect.
- Fix: `type=int` parse or `urlencode`.

### [LOW] Naive "today" in plan routes ignores the user's stored timezone
- Category: correctness
- Location: routes/study_plan.py:111,224,347 (`_monday_of(date.today())`), routes/flashcards.py:49,115,... (`date.today()`)
- Problem: study_session uses `plan_today_iso(db, user, lang)` (ADR-022) but study_plan/flashcards use server-local date; near midnight the week/due boundary disagrees with the daily load.
- Fix: reuse `services.day_boundary` in these routes.

### [LOW] `isinstance(x, int)` accepts booleans
- Category: correctness
- Location: routes/study_plan.py:164,208,300; routes/classifier_drill.py / counter_drill.py (`language_id`, `total_items`); routes/calibration.py:161,166
- Fix: exclude `bool` in a shared int-validator.

---

## Redundancy

### [MEDIUM] classifier_drill.py and counter_drill.py are ~82% identical
- Category: redundancy
- Location: routes/classifier_drill.py vs routes/counter_drill.py (both ~135 lines; difflib ratio 0.82 after name normalisation)
- Fix: one drill blueprint factory parameterised by (test_type code, language id, service module, copy).

### [MEDIUM] Vocab admin endpoints duplicated in admin_local.py and vocab_admin.py
- Category: redundancy
- Location: routes/admin_local.py:376 (list words), :459 (preview), :540 (wipe), :559 (remove level) vs routes/vocab_admin.py:168, :309, :263, :284
- Problem: same logic implemented twice (one authenticated, one loopback-only), so fixes diverge.
- Fix: move to a shared service function; admin_local keeps thin wrappers (or just calls the vocab_admin handlers).

### [LOW] Four overlapping "submit attempt" endpoints
- Category: redundancy
- Location: routes/exercises.py:180 (`/api/exercises/attempt`), routes/practice.py:92, routes/vocab_dojo.py:34, routes/vocabulary.py:18 + two duplicate "profile" endpoints (routes/auth.py:358 vs routes/users.py:64)
- Fix: keep practice/attempt, delete the superseded ones once dead-code removal below is done.

### [LOW] Test-submission RPC wrappers copy-pasted four times
- Category: redundancy
- Location: routes/tests.py:312-415 (`_call_submission_rpc`, `_call_dictation_...`, `_call_pinyin_...`, `_call_pitch_accent_...`) and the four `lookup test by slug` blocks (:600, :682, :765, :866) and four `user_elo_change/test_elo_change` response literals
- Fix: one `_call_rpc(name, params)` + `_lookup_test(slug)` + `_elo_envelope(rpc_result)`.

### [LOW] Duplicate question validator + dead helpers
- Category: redundancy / legacy
- Location: utils/question_validator.py (only imported by scripts/batch_generate_to_json.py; a second copy lives at services/test_generation/agents/question_validator.py); utils/validation.py:`sanitize_input` (0 callers)

---

## Legacy / dead code

### [MEDIUM] Routes with no frontend caller (static/ + templates/ scan; 0 hits)
- Category: legacy/dead
- Location: all of routes/exercises.py (`/api/exercises/`, `/session` redirect, `/session/complete`, `/attempt`, `/types`; TASK-220 retired the page); routes/vocab_dojo.py (all 7 routes - only comments in static/js/session/players/practice.js:8,91 mention it; gate/stress batteries never requested); routes/corpus.py (3 routes, superseded by admin_local); routes/payments.py (2); `/api/users/tokens` (users.py:33), `/api/users/profile` (users.py:64), `/api/tests/moderate` (tests.py:49), `/api/flashcards/stats|skip|page` (flashcards.py:23,196,245), `/api/calibration/ability` (calibration.py:184 - only /end used), `/api/vocabulary/extract` (app.py:691), `/api/errors/log` (app.py:713), `/api/tests/<slug>` (tests.py:249, "Flutter app" shape - PLAUSIBLE dead).
- Problem: ~35 live, authenticated attack surface routes that nothing calls; some (vocab_dojo gate/result, exercises/attempt, extract) carry the client-trust and cost issues above.
- Fix: delete, or at minimum remove from `_register_blueprints` until needed. Verify against any external client (Flutter) before removing.

### [LOW] Broken link: `/flashcards/page` does not exist
- Category: correctness / legacy
- Location: static/js/session/players/flashcards.js:92 links `/flashcards/page`; the real page is `/flashcards` (app.py:600). `/api/flashcards/page` (flashcards.py:23) is an HTML route behind a Bearer-token decorator, so a browser navigation can never reach it. The 404 handler (app.py:~395) redirects non-API 404s to `/login`, hiding the break.
- Fix: link `/flashcards`; delete flashcards.py:23.

### [LOW] Dead config, imports and models
- Category: legacy/dead
- Location: config.py: `AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_S3_BUCKET` (0 users), `EXERCISE_SLOT_DISTRIBUTION`, `EXERCISE_COOLDOWN_DAYS`, `SUPABASE_BATCH_CHUNK_SIZE`, `VOCAB_DOJO_SESSION_SIZE` (referenced only in config.py), `DEFAULT_AI_MODEL`/`AI_MODELS` are "legacy fallback" per their own comment, `get_language_name` unused; models/requests.py `TestSubmissionRequest`, `TestSubmissionResponse` (never imported); middleware/auth.py `tier_required` (no callers); unused imports: routes/corpus.py `g, jwt_required`; routes/exercises.py `datetime, timezone`; routes/study_plan.py `current_app`; routes/tests.py `jsonify, TestService, VALID_LANGUAGE_IDS`; routes/vocab_admin.py `render_template`; utils/question_validator.py `json, Optional`.
- Fix: delete; add pyflakes/ruff to the lint gate (pyflakes is not installed in the venv).

### [LOW] Misc maintainability
- Category: maintainability
- Location: routes/tests.py:6-7 module is 1236 lines mixing helpers, 4 submit flows and listing; app.py:`/api/config` uses `hasattr(Config,'TOKEN_COSTS')` for attributes that always exist; routes/auth.py:179,293 re-`import logging` inside functions; `_client_ip()` in auth.py duplicates `request.remote_addr`; app.py:735 comment-less module-level `app = create_app()` plus `app.run(host='0.0.0.0')` under `__main__`.
- Fix: split tests.py (listing / submissions / helpers).

---

## Prior-review status (.claude/reviews/codebase-review-2026-09-08.md, items in this slice)
- C-1 admin_app.py 0.0.0.0 + debug=True + 42 unauthenticated routes: FIXED as described (middleware/local_only.py enforced on both blueprints, admin_app binds 127.0.0.1 and takes debug from Config). Residual risks are new findings above (CSRF/rebinding, X-Forwarded-For via ProxyFix).
- Rate limiting on OTP routes (review line ~236): STILL OPEN - no limiter exists anywhere.
- CORS wildcard-with-credentials reflection (review line ~295, app.py:126-129): STILL OPEN (only exploitable if `*` is configured; default list is localhost).
- CSP report-only / 'unsafe-inline' (review line ~206, app.py:141): STILL OPEN (report-only by design).
- Auth middleware consolidation praised in the review (middleware/auth.py, ADR-014 batch token): confirmed good - `admin_required`/`tier_required` ignore the service identity; token cache stores successes only and respects JWT exp.
- Other prior items (H-1/H-2 tests/ESLint, H-3/M-1 JS escaping, M-5 word quiz batching) are outside this slice and were not re-checked.
