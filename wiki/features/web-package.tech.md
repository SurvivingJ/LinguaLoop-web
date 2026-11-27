---
title: The Web Package — Technical Specification
type: feature-tech
status: complete
prose_page: ./web-package.md
last_updated: 2026-11-23
dependencies:
  - "Flask 3.0, Werkzeug (ProxyFix, HTTPException, RoutingException)"
  - "Flask-Limiter 4.1 / limits (rate limits)"
  - "APScheduler 3.11 (BackgroundScheduler, CronTrigger)"
  - "`utils/responses.py` (api_error envelope)"
  - "`middleware/auth.get_optional_user_id` (rate-limit key)"
  - "`templates/error.html` and one template per page"
breaking_change_risk: medium
open_questions:
  - "OPEN: CSP is report-only and allows 'unsafe-inline'; there is no report endpoint (no `report-uri`/`report-to` in the policy), so violations are visible only in the browser console. Decide the enforcement plan."
  - "OPEN: `init_rate_limits` wraps `app.view_functions` entries; a rate-limited view is therefore a wrapper, and anything that reads `app.view_functions[endpoint].__module__` sees `flask_limiter`/`functools` internals. Not a defect today; noted for tools that introspect routes."
  - "OPEN: the production log of the scheduled jobs was not read; the statement that the 04:20 sweep fails nightly rests on the code and on the live schema ([[overview/project.tech]])."
---

# The Web Package — Technical Specification

Verified 2026-11-23 against commit `0d345e98`. `web/` is six files, 504 lines: `__init__.py` (a docstring), `pages.py` (56 + 5 lines), `errors.py` (81), `security.py` (54), `rate_limits.py` (134), `scheduler.py` (173). Prose: [[features/web-package]]. The route list those pieces produce is in [[api/rpcs.tech]].

## Architecture Overview

`app.create_app(config_class=Config)` (`app.py`) is the only caller. In order:

| # | Step | Code |
|---|---|---|
| 1 | `config_class.validate()` — raises `RuntimeError` when `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (or the secret key) are missing | `config.py` |
| 2 | `Flask(__name__)`, `app.config.from_object`, `app.wsgi_app = ProxyFix(x_for=1, x_proto=1, x_host=1)`, `app.url_map.strict_slashes = False`, `app.secret_key`, `logging.basicConfig` | `app.py` |
| 3 | `_setup_cors(app)` — Flask-Cors on `/api/*` (methods GET, POST, PUT, DELETE, OPTIONS; headers Content-Type, Authorization, Accept; credentials; max-age 86400) and a `before_request` that answers `OPTIONS` itself | `app.py` |
| 4 | `init_security_headers(app)`, `init_request_size_limit(app)` | `web/security.py` |
| 5 | `init_static_assets(app)` — content-hash `?v=` on `url_for('static')`, one-year cache for versioned and `static/vendor/` files, Flask-Compress | `services/static_assets.py` |
| 6 | `_initialize_services(app)` — Supabase factory, `DimensionService` cache, `TestService` and `PracticeSessionService` singletons, OpenAI, R2, Stripe key, vocabulary pipeline | `app.py` |
| 7 | `init_scheduler(app)` unless `app.config['TESTING']` | `web/scheduler.py` |
| 8 | `_register_blueprints(app)` — 20 `register_blueprint` calls (the two `test_intros` and `word_list_import` blueprints carry their own URL prefix) | `app.py` |
| 9 | `register_error_handlers(app)` | `web/errors.py` |
| 10 | `_register_core_routes(app)` — `/api/health`, `/api/metadata` and the `_inline_metadata` context processor | `app.py` |
| 11 | `register_pages(app)` | `web/pages.py` |
| 12 | `init_rate_limits(app)` — **last**, because limits attach by endpoint name | `web/rate_limits.py` |

Order requirements: rate limits need every endpoint registered (step 12 after 8, 10, 11); security headers and the size limit are `after_request`/`before_request` hooks and may come early; the error handlers are app-wide and order-independent. `wsgi.py` does `app = create_app()`.

## Database Impact

None directly. The scheduler jobs read and write tables and call RPCs through their own services (listed in [[overview/project.tech]] and [[api/rpcs.tech]]). The rate limiter and the error handlers touch no table.

## API / RPC Surface

### `pages.register_pages(app)`

`PAGES` is a tuple of `(rule, endpoint, template)`; `LOGIN_REDIRECTS` is `(('/', 'index'), ('/logout', 'logout'))`. `register_pages` calls `app.add_url_rule(rule, endpoint, view)` for each: a redirect view (`redirect(url_for('login'))`, status 302) for the redirects, and a `_page_view(endpoint, template)` closure that returns `render_template(template)` and accepts the URL values (`slug`) without using them. The view's `__name__` is set to the endpoint. **Endpoint names are referenced by `url_for` in templates; do not rename them.** The 24 entries (23 plus the `/signup` alias of the login template) are tabulated in [[api/rpcs.tech]] (page routes). Pages carry no auth: the JavaScript calls the API with the stored token. `/placement` and `/knowledge` render even when their flags are off; the page reads its API's 404 and shows "not available".

### `errors.register_error_handlers(app)`

Two handlers:

- `HTTPException` handler `handle_http_exception(exc)`:
  - returns `exc` untouched when `exc.code is None`, when `exc.response is not None` (the exception already carries a response) or when it is a Werkzeug `RoutingException` (the strict-slash/redirect machinery);
  - for a request whose path starts with `/api/`, **or any 405**: `_json_error(exc)`;
  - else for 404: `redirect(url_for('login'))` (302);
  - else for `code >= 500`: `_error_page(code)`;
  - else returns `exc` (the default Werkzeug HTML for, say, a non-API 400).
- `Exception` handler `handle_unexpected_exception(exc)`: re-raises when `current_app.debug` (keeps the interactive debugger); otherwise takes the message from `g.api_error_message` (set by `@api_errors`) or "Internal server error", logs the exception with method, path and message, returns `api_error(message, 500, 'SERVER_ERROR')` for `/api/` and `_error_page(500)` otherwise.

`_API_ERRORS` maps status to `(error_code, message)`: 400 `BAD_REQUEST` (exception text), 401 `UNAUTHORIZED`, 402 `PAYMENT_REQUIRED`, 403 `FORBIDDEN`, 404 `NOT_FOUND` "Endpoint not found", 405 `METHOD_NOT_ALLOWED` "Method not allowed", 413 `PAYLOAD_TOO_LARGE` "Request body too large", 429 `RATE_LIMITED` "Too many requests. Please try again later.", 500 `SERVER_ERROR` "Internal server error", 503 `SERVICE_UNAVAILABLE`. `_json_error` builds `api_error(message or exc.description or exc.name, status, error_code)` and copies the `Allow` and `Retry-After` headers from the exception's own response (so a 405 keeps `Allow`, a 429 keeps `Retry-After`). `_error_page(status)` renders `error.html` with `status`; if rendering raises, it logs and returns the plain string "Something went wrong. Please try again in a moment." with the same status. Observed (Flask test client, 2026-11-23): `POST /api/payments/create-intent` → `404 {"error":"Endpoint not found","error_code":"NOT_FOUND","status":"error"}`; `GET /nope` → `302 /login`; `GET /api/nope` → JSON 404; `DELETE /api/auth/send-otp` → JSON 405; a 2 MiB body → JSON 413.

### `security`

- `init_security_headers(app)`: an `after_request` that sets (with `setdefault`, so a route's own header wins) `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin` on every response; `Strict-Transport-Security: max-age=31536000` when `request.is_secure` (true behind ProxyFix when the proxy sends `X-Forwarded-Proto: https`; no `includeSubDomains`, no `preload`); and, only when the response `Content-Type` starts with `text/html`, `Content-Security-Policy-Report-Only` with exactly:

  `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' data: https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self'; base-uri 'self'; frame-ancestors 'self'`

  **State: report-only, never enforced, with `'unsafe-inline'` for scripts and styles** (templates still contain inline `<script>`/`<style>`). There is no `Content-Security-Policy` header and no report endpoint, so a violation is a browser-console message only. Bootstrap, Font Awesome and Bootstrap Icons are self-hosted (`static/vendor/`); Google Fonts is the only third-party origin. `tests/test_platform_app.py` asserts the header equals `CSP_REPORT_ONLY` and that no enforcing header exists.
- `init_request_size_limit(app)`: a `before_request` that calls `abort(413)` when `app.config['MAX_CONTENT_LENGTH']` is set and `request.content_length` exceeds it (default 1 MiB, `MAX_CONTENT_LENGTH` env). Flask only enforces the limit when the body is first read, and a view that reads it inside a broad `except` would turn 413 into 500; this check runs first.

### `rate_limits.init_rate_limits(app)`

Creates one `flask_limiter.Limiter`: `key_func=user_or_ip`, `default_limits=[RATELIMIT_API_DEFAULT]` (`300 per minute`) with `default_limits_exempt_when=_outside_api` (pages are not limited), `storage_uri=RATELIMIT_STORAGE_URI` (`memory://`), `strategy='fixed-window'`, `headers_enabled=True`, `swallow_errors=True` and `in_memory_fallback_enabled=True` (a broken store must not take the site down). It is disabled when `RATELIMIT_ENABLED` is false, and also under `TESTING` unless `RATELIMIT_ENABLED_IN_TESTS` is set; `app.config['RATELIMIT_ENABLED']` is overwritten with the result because Flask-Limiter reads that key itself. `limiter.request_filter(...)` exempts the batch identity (`user_or_ip() == 'user:service-account'`). The limiter is stored in `app.extensions['rate_limiter']`.

Key functions: `client_ip()` = `ip:<get_remote_address()>`; `user_or_ip()` = `user:<id>` from `get_optional_user_id(request)` (cached per request in `g._rate_limit_user_id`, going through the auth middleware's validation cache so the route's own decorator reuses the result), else `client_ip()`; `email_or_ip()` = `email:<lowercased email, ≤ 254 chars>` from the JSON body, else the IP (so one address cannot be flooded from many IPs).

`ENDPOINT_LIMITS` (endpoint name → limits; every listed limit applies):

| Endpoint | Limits (key) |
|---|---|
| `auth.send_otp` | 5/min and 20/h (IP); 3/10 min and 10/day (email) |
| `auth.verify_otp` | 10/min and 60/h (IP); 10/10 min (email) |
| `auth.device_restore` | 30/min (IP) |
| `auth.refresh_token` | 60/min (IP) |
| `word_list_import.submit` | 5/h and 20/day (user) |
| `dual_translation.submit` | 10/min and 120/h (user) |
| `dt_repair.check` | 20/min and 300/h (user) |
| `dt_repair.hint` | 60/min (user) |
| `dt_repair.practice_due` | 30/min (user) |
| `knowledge.summary` | 30/min and 600/h (user) |
| `knowledge.prestudy_suggestion` | 30/min and 300/h (user) |
| `calibration.placement_start` | 10/day (user); a further cap of 3 starts per language per day is enforced in `services/calibration_placement.start()` |
| `calibration.placement_answer` | 120/min (user) |

For each entry the view in `app.view_functions` is replaced by `limiter.limit(limit, key_func=...)(view)` (one wrapper per limit); an unknown endpoint name logs a warning and is skipped. `EXEMPT_ENDPOINTS = ('health_check',)` are wrapped with `limiter.exempt`. When storage is `memory://` it logs once that counts are per worker process. **With two gunicorn workers a client can reach about twice each limit**; point `RATELIMIT_STORAGE_URI` at a `redis://` URI to share counts. Limits attach only after all routes exist, so a new rate-limited route needs only a new row in `ENDPOINT_LIMITS`.

### `scheduler`

`JOBS` is a tuple of `Job(id, target, cron, label, report=_log_summary, args=tuple)`: `target` is `'package.module:function'` imported when the job fires; `cron` holds `CronTrigger` fields (UTC); `report(logger, label, result)` logs the return value (`_log_skippable` logs `skipped (<reason>)` for `{'skipped': True, ...}`; `_log_slug_health` logs an ERROR naming dead model slugs); `args()` is called at fire time and returns the positional arguments (`_admin_client` supplies the service-role client to the three jobs that take one). `Job.when` renders "Sun 23:00 UTC" style strings. The ten jobs, their schedules and what each does are tabulated in [[overview/project.tech]]; the chain is `Sun 03:40 llm_calls_archive_weekly`, `03:50 dt_error_synthesis_nightly`, `04:00 irt_calibration_nightly`, `04:05 exercise_time_estimate_refresh`, `04:10 slug_health_nightly`, `04:15 generation_queue_drain_nightly`, `04:20 word_upload_watchlist_sweep_nightly`, `04:25 knowledge_snapshots_nightly`, `04:30 placement_close_stale_nightly`, `Sun 23:00 study_plan_weekly_recompute`.

`init_scheduler(app)`: returns at once (logging) when `DISABLE_SCHEDULER` is `1`/`true`/`yes` or APScheduler is not importable; takes a module lock; if a scheduler is already running in this process (`_running.running`) it attaches it as `app.scheduler` and warns instead of starting a second; otherwise builds `BackgroundScheduler(timezone='UTC')`, adds each job with `CronTrigger(**cron)`, `coalesce=True`, `max_instances=1`, `replace_existing=True`, starts it, sets `app.scheduler` and logs the job list. `_runner(job, logger)` returns the callable APScheduler fires: it sets the thread's database timeout to `Config.SUPABASE_JOB_TIMEOUT` (120 s, `SupabaseFactory.set_thread_timeout`), imports the target lazily, calls it with `job.args()` and reports the result; **any exception is logged ("<label> crashed") and swallowed**, so a failing job cannot stop the scheduler. Cross-worker safety is the job's own business (advisory lock or idempotent upsert); the scheduler itself runs in every worker (two schedulers under the `Procfile`).

## Component Specification (if UI)

Not applicable beyond `templates/error.html` (extends `base.html`; heading "Something went wrong", a link to the tests page).

## Key Architectural Decisions

1. **Wiring lives in `web/`, not in `app.py`.**
   - Rationale: `app.py` had grown pages, error handling, headers, limits and the scheduler inline; each is now a module with a table at the top and a `register_*`/`init_*` function.
   - Alternatives rejected: one `extensions.py` (mixes unrelated lifecycles); per-blueprint limits via decorators (every route file would need to know the limiter).
2. **Limits attach by endpoint name after registration.** Route modules stay unaware of them; the cost is the ordering requirement and the wrapper in `view_functions`.
3. **API errors are one envelope; a non-API 404 is a redirect to login.** Chosen so a stale bookmark lands somewhere usable; 405 stays JSON on pages because it always did.
4. **CSP report-only first.** Enforcing with `'unsafe-inline'` would add nothing; the policy is in place so the inline code can be removed against a known target.
5. **Jobs declared as data and imported lazily.** A job whose module fails to import crashes only itself at fire time, not the application at start-up.

## Security Considerations

Headers and the size limit above; the 413 check runs before any view; `ProxyFix(x_for=1, x_proto=1, x_host=1)` trusts exactly one proxy hop for the client IP (rate-limit key), `is_secure` and the host used by the origin check on cookie routes; the OPTIONS handler in `app.py` reflects an allowed origin only; the batch identity is exempt from rate limits (it is as trusted as the token). The unhandled-exception handler never returns the exception text to the client.

## Testing Strategy

`tests/test_platform_app.py` (factory wiring, headers, CSP equality, error handlers, 404 redirect, 413), `tests/test_platform_rate_limits.py` (key functions, per-endpoint limits, enabling in tests), `tests/test_platform_scheduler.py` (job table, `DISABLE_SCHEDULER`, crash isolation), `tests/test_core_routes.py`, `tests/test_route_helpers.py`. Edge cases to cover when changing the package: an endpoint named in `ENDPOINT_LIMITS` that no longer exists (warning, no crash); a template that fails to render in the error page; a body of exactly `MAX_CONTENT_LENGTH`; a 429 keeping `Retry-After`.

## Related Pages

- [[features/web-package]] — Prose page
- [[api/rpcs.tech]] — Route reference (pages, error envelope, rate-limit notes)
- [[overview/project.tech]] — Scheduler table, flags, gates
- [[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]] — static asset versioning and compression
- [[database/schema.tech]] — Tables the scheduled jobs touch
