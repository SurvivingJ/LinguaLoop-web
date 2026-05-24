---
title: "Code Review — 2026-05-24"
type: review
status: complete
last_updated: 2026-05-24
scope: "Main LinguaLoop / LinguaDojo backend (app.py, routes/, services/, middleware/, utils/, models/)."
prior_review: "2026-05-15 (see log.md entry of that date)"
---

# LinguaLoop / LinguaDojo Code Review — 2026-05-24

> **Status update (2026-05-24):** CR-03 and CR-04 are **PATCHED** as of commit `8989b0bf` (RED reproducers at `1bbf7e9a`). See the [[log]] entry of the same date for the full diff summary, the manual SQL verification checklist, and the list of sibling submission RPCs (`listening_lab_rpcs.sql`, `process_mystery_submission.sql`, etc.) that still carry the same `SQLERRM` leak pattern and need a follow-up sweep. CR-01 and CR-02 remain blockers for the next paid-tier release.

## Scope & Method

Read-only code review of the main backend, focused on **what has shipped since the 2026-05-15 audit**: the new `call_llm()` infrastructure (commits df85ebb4, 7d530fac), the batch test-generation pipeline rewrite, Study Plans rollout + destructive user-state wipe (f0afbf2d, [phase13 wipe migration](../../migrations/phase13_wipe_user_state_for_launch.sql)), the test-side K-factor decay (e1f35223, [phase14](../../migrations/phase14_test_kfactor_decay.sql)), and APScheduler cron jobs (82764d6b). Re-verified the high-traffic surfaces flagged in the prior audit to make sure they remained fixed.

**In scope:** `app.py`, `config.py`, `routes/`, `services/`, `middleware/`, `utils/`, `models/`, two recent SQL migrations.
**Out of scope:** `Portal/*`, `Corpuses/*`, frontend, SQL schema review at depth, vendored corpora.
**Tools:** no static analysis run — the project has no `pyproject.toml` / `ruff.toml` / `mypy.ini`. Review is by code reading + targeted grep. The 2026-05-15 audit covered tooling-class issues; this pass is bug-focused.

The single most material finding — **CR-01, the missing Stripe webhook** — is independently documented in [[api/rpcs.tech]] line 286 (*"Stripe webhook is currently NOT registered in `app.py`"*). Verified again here; still missing.

## Summary

| Severity   | Count | Notes                                                                                |
| ---------- | ----- | ------------------------------------------------------------------------------------ |
| CRITICAL   | 4     | Revenue loss, fail-open content moderation, double-spend race, error info leak       |
| HIGH       | 9     | Dead/broken service code, missing timeout, partial-init failure modes, asymmetric authz |
| MEDIUM     | 12    | Inconsistent error shapes, missing route validation, log-noise issues, silent defaults |
| LOW        | 6     | Dead code branches, micro-perf, naming consistency                                   |
| Redundancy | 5     | Four near-identical RPC wrappers, auth-decorator boilerplate, dual audio paths       |

Net merge guidance: **block release until CR-01 and CR-03 are addressed**. CR-02 and CR-04 are pre-existing risks acceptable for the next release window if explicitly tracked. The remaining HIGH items are tech debt, not crashes.

---

## CRITICAL

### CR-01 — Stripe webhook missing; paid token purchases never credit the user
- **Files:** [routes/payments.py](../../routes/payments.py) (only two routes: `/token-packages`, `/create-intent`), [services/payment_service.py:229-312](../../services/payment_service.py#L229-L312) (`handle_successful_payment` never called).
- **Evidence:** `Grep` for `stripe.+webhook|construct_event|payment_intent\.succeeded` across `services/` and `routes/` returns **zero hits**. The factory `get_payment_service` ([services/payment_service.py:405](../../services/payment_service.py#L405)) is also unreferenced anywhere outside the file itself.
- **Why it matters:** Users complete a Stripe checkout, money is captured, but no server-side handler runs `process_stripe_payment` to increment `user_tokens.purchased_tokens`. They paid and got nothing. The team already documented this gap in [[api/rpcs.tech]] line 286 — it remains unfixed.
- **Fix:**
  1. Add `@payments_bp.route('/webhook', methods=['POST'])` that verifies `Stripe-Signature` with `stripe.Webhook.construct_event` and the `STRIPE_WEBHOOK_SECRET` env var.
  2. Dispatch on `event['type'] == 'payment_intent.succeeded'`, extract `payment_intent.id`, then call the existing `process_stripe_payment(p_user_id, p_tokens_to_add, p_payment_intent_id, p_package_id, p_amount_cents)` RPC (idempotent server-side).
  3. Add Stripe webhook secret to [config.py](../../config.py) `validate()` checklist.
  4. Either delete `services/payment_service.py::handle_successful_payment` (now superseded by the RPC) or rewrite it as a thin caller for the RPC and use it from the new webhook handler.

### CR-02 — `services/payment_service.py::create_payment_intent` is broken — attribute access on dicts
- **File:** [services/payment_service.py:202-216](../../services/payment_service.py#L202-L216)
- **Evidence:**
  ```python
  package = self.TOKEN_PACKAGES[package_id]              # dict, from Config
  intent = stripe.PaymentIntent.create(
      amount=package.price_cents,                          # AttributeError
      ...
      'tokens': package.tokens,
      'type': 'token_purchase'
      },
      description=f"Purchase {package.tokens} tokens - {package.description}"
  )
  ```
  But [config.py:179-192](../../config.py#L179-L192) defines `TOKEN_PACKAGES` as a dict-of-dicts (`{'tokens': 10, 'price_cents': 199, ...}`). Attribute access on a `dict` raises `AttributeError`. Same bug in `get_token_packages` ([line 320-329](../../services/payment_service.py#L320-L329)).
- **Why it matters:** Any caller of `PaymentService.create_payment_intent` crashes. Currently nothing calls it (the live [routes/payments.py:40-55](../../routes/payments.py#L40-L55) re-implements the Stripe call with correct `package['price_cents']` dict access), so the bug is latent. It will bite the moment someone wires this service back in, and it indicates the whole `PaymentService` class is unexercised dead code worth deleting wholesale.
- **Fix:** Either (a) delete the class and reuse the dict-based code from `routes/payments.py`, or (b) keep it as the canonical service, switch all access to `package['price_cents']` / `package['tokens']` / etc., and route the new webhook handler through it.

### CR-03 — `AIService.moderate_content` fails OPEN on any moderation error
- **File:** [services/ai_service.py:292-300](../../services/ai_service.py#L292-L300)
- **Evidence:**
  ```python
  except Exception as e:
      error_msg = f"Content moderation error: {e}"
      logger.error(error_msg)
      return {
          'is_safe': True,                  # <-- fail OPEN
          'flagged_categories': [],
          ...
      }
  ```
  And [routes/tests.py:67-75](../../routes/tests.py#L67-L75) reads `is_safe` directly and only records flagged input when `not is_safe`.
- **Why it matters:** OpenAI moderation timeout, rate-limit, or any transient error silently passes ALL submitted content as safe. The flagged-input audit log (used to track abuse) is also bypassed in that case.
- **Fix:** Return `is_safe: False` (or raise) on error and let the route surface a 503/retry to the user. If a permissive default is intentional during outages, gate it behind an explicit `Config.MODERATION_FAIL_OPEN` flag with logging at WARNING level on every fallback.

### CR-04 — `process_test_submission` SQLERRM leaks DB internals; success/failure shape is misleading
- **File:** [migrations/phase14_test_kfactor_decay.sql:349-355](../../migrations/phase14_test_kfactor_decay.sql#L349-L355)
- **Evidence:**
  ```sql
  EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', SQLERRM,                -- raw Postgres error message
      'error_detail', SQLSTATE
    );
  ```
  The `_call_submission_rpc` helper in [routes/tests.py:683-701](../../routes/tests.py#L683-L701) forwards this JSONB straight to the client.
- **Why it matters:**
  1. `SQLERRM` can include table/column names, type info, RLS policy names — useful for an attacker probing the schema.
  2. The function rolls back inside the exception block, but the JSON still says `success: false` with an "error" message — the caller may treat the response as a recoverable application error and retry (re-running the temp-table create, the percentage math, etc.), wasting work. Worse, if the client surfaces "error" text verbatim, it shows DB internals to the user.
- **Fix:** Log `SQLERRM`/`SQLSTATE` to a backend logs table (or `RAISE WARNING`), but return a generic `{'success': false, 'error': 'submission_failed', 'error_code': '...'}` JSON to the client. Pattern can be reused across `process_dictation_submission`, `process_pinyin_submission`, `process_pitch_accent_submission`.

---

## HIGH

### HI-01 — Three auth decorators duplicate ~70 lines of identical exception handling
- **File:** [middleware/auth.py:41-206](../../middleware/auth.py#L41-L206)
- **Evidence:** `jwt_required`, `admin_required`, and `tier_required` each implement the same skeleton: extract token → `supabase.auth.get_user(token)` → catch `AuthApiError` / `AuthRetryableError` / `Exception` → return one of three JSON shapes with identical messages.
- **Why it matters:** Three places to fix any auth behavior change (logging, audit, status code adjustments). The 2026-05-15 audit hardened only `jwt_required`'s service-role check; `admin_required` and `tier_required` did NOT receive the same hardening because the bypass logic only lives in one decorator.
- **Fix:** Extract a `_authenticate(token) -> (user_or_None, error_response_or_None)` helper. Decorators become 5-line wrappers around it. Consolidates the service-role bypass too.

### HI-02 — Service-role JWT bypass is jwt_required-only; admin/tier endpoints silently fail with a service-role token
- **File:** [middleware/auth.py:58-72](../../middleware/auth.py#L58-L72) (bypass present), [108-154](../../middleware/auth.py#L108-L154), [157-206](../../middleware/auth.py#L157-L206) (bypass absent).
- **Why it matters:** Internal batch jobs that need admin-tier RPCs (e.g., the cron workers, the test generation orchestrator) cannot authenticate. They will hit `supabase.auth.get_user(<service_role_jwt>)` which the Supabase auth API rejects as malformed, and the decorator returns 401. Either intentional (write a separate batch-only endpoint) or surprising; either way, document it inline.
- **Fix:** Decide: add the same `hmac.compare_digest` bypass to `admin_required` / `tier_required`, or add an explicit `# Service-role tokens cannot reach this decorator; see jwt_required` comment so the asymmetry isn't lost.

### HI-03 — `services/payment_service.py::get_payment_service` rebuilds a Supabase client, bypassing the factory
- **File:** [services/payment_service.py:405-410](../../services/payment_service.py#L405-L410)
  ```python
  def get_payment_service(config) -> PaymentService:
      from supabase import create_client
      supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
      return PaymentService(supabase, config.STRIPE_SECRET_KEY)
  ```
- **Why it matters:** Repeats the exact anti-pattern fixed for `AuthService` in the 2026-05-15 audit (see [[log]] §2026-05-15). When `SupabaseFactory.initialize()` migrates auth/headers (e.g., adds a custom `x-client-info`), this client is left behind.
- **Fix:** `return PaymentService(get_supabase(), config.STRIPE_SECRET_KEY)` using the factory. Or — given CR-02 — delete the factory function along with the class.

### HI-04 — `r2_service.upload_from_url` is unbounded and SSRF-prone
- **File:** [services/r2_service.py:336-356](../../services/r2_service.py#L336-L356)
- **Evidence:** `response = requests.get(url, stream=True)` — no `timeout=`, no URL scheme/host validation.
- **Why it matters:** An operator or any caller that passes a user-controlled URL can hang the worker forever (no timeout) or hit internal services (no scheme allowlist). Even if currently admin-only, this is the kind of helper that grows callers.
- **Fix:**
  ```python
  if not url.startswith(('https://', 'http://')):
      raise ValueError("Only http(s) URLs are supported")
  response = requests.get(url, stream=True, timeout=30)
  ```
  Consider blocking RFC1918 hosts via a small `_is_safe_host(url)` helper.

### HI-05 — `orchestrator.run_batch` mutates the global `test_gen_config.dry_run` singleton
- **Files:** [services/test_generation/orchestrator.py:858-997](../../services/test_generation/orchestrator.py#L858-L997)
- **Evidence:** `run_batch` toggles a singleton config flag and restores it in `finally`. Two concurrent `run_batch` calls with different `dry_run` settings step on each other. This is not hypothetical — the CLI ([scripts/run_test_generation_cli.py](../../scripts/run_test_generation_cli.py)) and any future Flask-route trigger could overlap.
- **Why it matters:** Silent regression where one run accidentally writes to the DB because another run flipped the flag mid-execution.
- **Fix:** Pass `dry_run` through `_generate_test` (and downstream) as a parameter instead of reading from the singleton. The singleton stays for static defaults, but per-call overrides shouldn't mutate it.

### HI-06 — Orchestrator audio is uploaded BEFORE the test row is inserted; failure leaks an orphan MP3 in R2
- **File:** [services/test_generation/orchestrator.py:402-442](../../services/test_generation/orchestrator.py#L402-L442)
- **Evidence:** `test_id = uuid4()` → `audio_synthesizer.generate_and_upload(...)` (uploads `<test_id>.mp3` to R2) → `self.db.insert_test(test)` (which may fail). If insert fails, the test row is never persisted, but the MP3 stays in R2 indefinitely.
- **Why it matters:** Storage bloat and orphan-file accumulation. With many failed test generations over time, R2 fills with unreferenced audio. Also a minor cost issue.
- **Fix:** Insert the test row first (transcript only, `audio_url` left null), then upload audio, then UPDATE the row with `audio_url`. If the upload fails, the row stays but with a known-missing audio that a sweeper can retry.

### HI-07 — `routes/auth.py::send_otp` and three other handlers crash on missing JSON body
- **File:** [routes/auth.py:65](../../routes/auth.py#L65) (`data = request.get_json()` — no fallback), [routes/auth.py:79-80](../../routes/auth.py#L79-L80), [289-290](../../routes/auth.py#L289-L290), [333-334](../../routes/auth.py#L333-L334) (broad except, no `exc_info`).
- **Evidence:** `data.get('email', '')` on `None` raises `AttributeError`. Caught by the broad `except` at line 79, but the handler logs nothing and returns generic "Server error occurred", losing diagnostics.
- **Fix:** `data = request.get_json() or {}` (matches the pattern in `verify_otp`/`refresh_token`) and add `exc_info=True` to all auth-route logging for parity with `verify_otp` ([line 169](../../routes/auth.py#L169)).

### HI-08 — `app._initialize_services()` runs five independent try/except blocks and silently leaves the app in a half-initialized state
- **File:** [app.py:128-210](../../app.py#L128-L210)
- **Evidence:** Each try block on failure sets `app.supabase=None`, `app.openai_service=None`, `app.r2_service=None`, etc. The app boots and serves `/api/health` happily. But the first request that calls `current_app.supabase` or `current_app.openai_service` crashes with `AttributeError: 'NoneType' object has no attribute 'table'`. Worse, there's no overall startup-failed signal — the operator sees "LinguaDojo application initialized successfully" at line 93.
- **Why it matters:** Production deploys can silently start serving 500s without the orchestrator (Cloud Run, Heroku, fly.io) knowing the app is broken. `Config.validate()` covers the secret-missing case but not the "credentials present but Supabase unreachable" case.
- **Fix:** Decide per-service: REQUIRED (fail startup) vs OPTIONAL (boot with degraded health). For each required service, re-raise after logging. For optional services, ensure `/api/health` returns a `degraded` status (already partially wired via the `services:` dict at [app.py:502-509](../../app.py#L502-L509)) AND that the health-check endpoint returns non-200 when a required service is down.

### HI-09 — `llm_service._log_llm_call` chooses observability target by truthiness, silently writes via anon client when admin is None
- **File:** [services/llm_service.py:168-192](../../services/llm_service.py#L168-L192)
- **Evidence:** `client = get_supabase_admin() or get_supabase()`. If service-role init failed (per HI-08, easily possible), every LLM call falls through to the anon client, which is RLS-restricted. Most likely outcome: `llm_calls` inserts silently 0-row no-ops; the `logger.debug("llm_calls logging failed: %s", exc)` at line 192 hides the failure at DEBUG level.
- **Why it matters:** Loss of observability for every model call across the entire generation pipeline, with no operator-visible signal. The pipeline appears to run normally because the calling code only checks `parsed_ok`, not "did we log this?".
- **Fix:** If `get_supabase_admin()` returns None, log at WARNING once at startup and explicitly skip the call (don't try the anon client). Also bump line 192 from DEBUG to WARNING so log-target failures surface.

---

## MEDIUM

### ME-01 — Inconsistent error response shapes across blueprints
- **Files:** [routes/tests.py](../../routes/tests.py) (returns `{"error": ..., "status": "error"}` via raw `jsonify`), [routes/payments.py](../../routes/payments.py) (uses `utils.responses.bad_request` / `server_error`), [routes/auth.py](../../routes/auth.py) (returns `{"error": ...}` or `{"success": False, "message": ..., "user": None, "jwt_token": None}`).
- **Why it matters:** Clients have to handle multiple error shapes per endpoint. [utils/responses.py](../../utils/responses.py) defines the canonical helpers (`api_error`, `bad_request`, etc.); ~5 routes use them, ~15 don't.
- **Fix:** Pick one shape (recommend `utils.responses` since it's already defined) and migrate `routes/tests.py` first (largest payoff). New routes should fail review if they don't use the helpers.

### ME-02 — Pydantic schemas exist but only ~4 routes use them
- **Files:** [models/requests.py](../../models/requests.py) (`TestSubmissionRequest`, `PaymentIntentRequest`, `VocabularyExtractRequest`, `ErrorLogRequest`, `WordQuizRequest`) vs the ~30 routes that still parse `request.get_json()` ad-hoc.
- **Why it matters:** Routes that bypass Pydantic frequently crash on missing JSON (HI-07) or accept malformed payloads. The schemas are well-defined; the gap is adoption.
- **Fix:** Migrate one blueprint per release. `routes/tests.py` submit endpoints are the highest-value targets.

### ME-03 — `_award_daily_free_tokens` logs `tokens_added=DAILY_FREE_TOKENS` but never credits the balance
- **File:** [services/payment_service.py:367-385](../../services/payment_service.py#L367-L385)
- **Evidence:** The function updates `last_free_token_date` and writes a `token_transactions` row with `tokens_added=2`, but the actual "+2 free today" is computed at READ time inside `get_user_token_balance` (line 98). The DB never sees the +2 increment.
- **Why it matters:** Auditing `SUM(tokens_added) - SUM(tokens_consumed)` against the current `purchased_tokens` balance will be off by every free-token award. Confusing for any future reconciliation script and for the user-visible transaction history.
- **Fix:** Either (a) drop the misleading log row (free tokens are virtual), or (b) actually persist a free-token balance column and increment it, so the log reflects reality.

### ME-04 — `EXCEPTION WHEN OTHERS … catch all` pattern repeats throughout submission RPCs
- **Files:** [migrations/phase14_test_kfactor_decay.sql:349-355](../../migrations/phase14_test_kfactor_decay.sql#L349-L355); presumably mirrored in `process_dictation_submission.sql`, `process_pinyin_submission.sql`, `process_pitch_accent_submission.sql`.
- **Why it matters:** Same SQLERRM leak (CR-04) and same misleading `{success: false, error: ...}` shape. Fix once, sweep all.

### ME-05 — `/api/errors/log` uses service-role insert with no per-user rate limit
- **File:** [app.py:535-577](../../app.py#L535-L577)
- **Evidence:** `app.supabase_service.table('app_error_logs').insert(...)` — uses service-role to insert on behalf of any authenticated user. No per-user rate limit. A misbehaving (or malicious) client can spam `/api/errors/log` with up to ~2KB `error_message` payloads.
- **Fix:** Add a simple per-user rate limit (e.g., 60 inserts / 5 min via Flask-Limiter or a quick `user_id`-keyed counter), or move to the anon client and write an RLS policy that allows `INSERT WHERE user_id = auth.uid()`.

### ME-06 — `print()` calls in route handlers instead of `logger.*`
- **Files:** ~30 files in `routes/` per the recon grep; verified in `routes/study_plan.py`, `routes/practice.py`, `routes/users.py`.
- **Why it matters:** `print()` outputs go to stdout, get scraped into platform logs without level/structured context; not easy to filter or alert on.
- **Fix:** Sweep `print()` → `current_app.logger.info` (or appropriate level). Could be a single PR with a regex.

### ME-07 — Admin/tier role lookup makes a second round-trip on every request
- **File:** [middleware/auth.py:121-137](../../middleware/auth.py#L121-L137), [171-189](../../middleware/auth.py#L171-L189)
- **Evidence:** Each `admin_required` / `tier_required` request calls `supabase.auth.get_user(token)` (external HTTP) + a separate `supabase_admin.table('users').select('subscription_tier').eq(...).execute()` (DB hop). No caching per JWT.
- **Why it matters:** Two latency hops on every admin request, multiplied by the dashboard's ~10-20 requests on page load.
- **Fix:** Cache `subscription_tier` per JWT sub for ~60s in process memory (LRU). Or include `subscription_tier` as a Supabase JWT custom claim and read it from `user_response.user.user_metadata`.

### ME-08 — Token-balance read-modify-write race in `handle_successful_payment`
- **File:** [services/payment_service.py:278-290](../../services/payment_service.py#L278-L290)
- **Evidence:** SELECT `purchased_tokens` → compute `new_balance` → UPDATE. Two concurrent webhook deliveries for the SAME `payment_intent_id` are dedup'd by the idempotency check, but two concurrent intents for the same user can race.
- **Why it matters:** Currently latent because the entire flow is dead (CR-01). Will become live the moment the webhook is wired.
- **Fix:** Push the increment into a `process_stripe_payment` RPC that does `UPDATE user_tokens SET purchased_tokens = purchased_tokens + p_tokens` (atomic). The RPC is already referenced in [[api/rpcs.tech]] line 286/390.

### ME-09 — `raise Exception(...)` swallows original traceback chain
- **Files:** [services/ai_service.py:87-90](../../services/ai_service.py#L87-L90), [113-115](../../services/ai_service.py#L113-L115), [services/payment_service.py:107-109](../../services/payment_service.py#L107-L109), [184-186](../../services/payment_service.py#L184-L186), [225-227](../../services/payment_service.py#L225-L227), [310-312](../../services/payment_service.py#L310-L312), [353-355](../../services/payment_service.py#L353-L355) — and others.
- **Pattern:** `raise Exception(f"X failed: {e}")` — loses the original traceback chain; the caller sees a generic `Exception` and can't differentiate (e.g., transient network vs. schema violation).
- **Fix:** `raise RuntimeError("X failed") from e` preserves the chain and lets pyflakes / sentry stitch the original exception. Bare `raise Exception(...)` is also flagged by most linters.

### ME-10 — `Config.get_language_id` and `get_model_for_language` silently default on unknown input
- **File:** [config.py:247](../../config.py#L247) (falls back to English model), [config.py:272](../../config.py#L272) (falls back to Chinese ID 1).
- **Why it matters:** A typo like `lang='ko'` returns Chinese (ID 1) without complaint. Any downstream language-specific logic then writes wrong data with no audit trail.
- **Fix:** Raise `ValueError(f"Unknown language code: {code!r}")`. If a default truly is required at one call site, the caller should pass the fallback explicitly.

### ME-11 — `'jp'` vs ISO `'ja'` inconsistency in language codes
- **Files:** [config.py:86](../../config.py#L86) (`'jp'`), [services/llm_output_cleaner.py:43](../../services/llm_output_cleaner.py#L43) (`'ja': 'jp'` mapping), [services/test_generation/difficulty_scorer.py:47-54](../../services/test_generation/difficulty_scorer.py#L47-L54) (only `'jp'` in `_LANG_MAP`, not `'ja'`).
- **Why it matters:** Anyone passing the ISO-standard `'ja'` to `difficulty_scorer` triggers `ValueError`. Documentation, tests, and external integrations naturally use `'ja'`. The mismatch costs an hour of debugging every time someone new joins.
- **Fix:** Pick one (recommend keeping `'jp'` since it's pervasive) and have ALL public helpers accept both for one release before deprecating `'ja'`.

### ME-12 — `_validate_question_structure` in `services/ai_service.py` is dead code
- **File:** [services/ai_service.py:182-223](../../services/ai_service.py#L182-L223)
- **Evidence:** Defined on the LEGACY `AIService` class; not called from any sibling method, and no callers found in `Grep` of the codebase.
- **Why it matters:** 42 lines of dead branching logic. The fact that the LEGACY marker is at line 1 and major methods still live in this file makes it hard to tell what's safe to delete.
- **Fix:** Delete the method along with the eventual `AIService` retirement (see HI-03 / CR-02). Inventory the entire file: which methods (`generate_audio`, `moderate_content`, `generate_transcript`, `generate_questions`) are still called and which are vestigial.

---

## LOW

### LO-01 — `orchestrator._build_difficulty_schedule` has a dead `pass`-only branch
- **File:** [services/test_generation/orchestrator.py:1022-1028](../../services/test_generation/orchestrator.py#L1022-L1028)
- **Evidence:** The inner `if remainder > 0 and dist_from_mid <= remainder: pass` does nothing; the actual round-robin distribution happens in the next block (lines 1031-1038). The dead branch was probably leftover from an earlier draft.
- **Fix:** Delete the no-op `if`.

### LO-02 — `utils/question_validator.py` is barely used and overlaps `services/test_generation/agents/question_validator.py`
- **File:** [utils/question_validator.py](../../utils/question_validator.py) (99 lines)
- **Evidence:** Static-method class with `validate_question_format` and `check_semantic_overlap`. The richer validator lives at `services/test_generation/agents/question_validator.py`. The utils one uses uppercase keys (`"Question"`, `"Answer"`, `"Options"`) — a different schema from the production `MCQuestion` Pydantic model.
- **Fix:** Confirm no callers via `Grep "from utils.question_validator"` (probably none). If unused, delete. If used by a legacy script, mark `# DEPRECATED — use services.test_generation.agents.question_validator`.

### LO-03 — `_RE_BOLD_ITALIC` greedy-mis-strips innocuous single asterisks
- **File:** [services/llm_output_cleaner.py:49](../../services/llm_output_cleaner.py#L49)
- **Pattern:** `\*{1,2}(.+?)\*{1,2}` — matches `*foo*` correctly but also matches `*` literals in code-like text (`"3 * 4 = 12"` → `3 4 = 12`). Lazy `.+?` mitigates but doesn't eliminate.
- **Fix:** Require the closing marker count to match the opener (`\*\*(.+?)\*\*|\*(.+?)\*`) and don't apply if the text is detected as code (e.g., contains `=`, `function`, `def`, `>>>`).

### LO-04 — `check_semantic_overlap` whitespace-tokenizer fails for CJK
- **File:** [utils/question_validator.py:86-89](../../utils/question_validator.py#L86-L89)
- **Pattern:** `set(question.lower().split())` — Chinese/Japanese strings without spaces become single-token sets; Jaccard always degenerates to 0 or 1.
- **Fix:** If anyone uses this helper for non-EN, swap in `jieba.cut` / `fugashi` per language. Otherwise mark it EN-only in the docstring.

### LO-05 — `fugashi.Tagger` instantiated per call in `difficulty_scorer._tokenize_ja`
- **File:** [services/test_generation/difficulty_scorer.py:253-261](../../services/test_generation/difficulty_scorer.py#L253-L261)
- **Evidence:** Tagger initialization loads UniDic — non-trivial. Per-call cost adds up in batch generation runs.
- **Fix:** Module-level lazy-init `_TAGGER = None` + `_get_tagger()`.

### LO-06 — `R2Service.__init__` `getattr` fallback is dead code
- **File:** [services/r2_service.py:22-23](../../services/r2_service.py#L22-L23)
- **Evidence:** `getattr(config, 'R2_BUCKET_NAME', 'linguadojoaudio')` — `Config` always defines `R2_BUCKET_NAME` ([config.py:205](../../config.py#L205)), so the default path is unreachable.
- **Fix:** `config.R2_BUCKET_NAME` direct access; let it `AttributeError` early if someone passes a non-Config.

---

## Redundancies

### RD-01 — Four near-identical RPC wrappers in `routes/tests.py`
- **Files:** [routes/tests.py:677-786](../../routes/tests.py#L677-L786)
- **Locations:**
  - `_call_submission_rpc` (line 677) — `process_test_submission`
  - `_call_dictation_submission_rpc` (line 704) — `process_dictation_submission`
  - `_call_pinyin_submission_rpc` (line 736) — `process_pinyin_submission`
  - `_call_pitch_accent_submission_rpc` (line 762) — `process_pitch_accent_submission`
- **Common pattern:** `try client.rpc(NAME, params).execute()` → catch Exception → check `e.json()` / `e.args[0]` for a `success: True` payload (workaround for supabase-py raising on JSONB responses) → log + return jsonify error tuple.
- **Proposed consolidation:**
  ```python
  def _call_rpc(client, rpc_name, params, error_message):
      try:
          return client.rpc(rpc_name, params).execute().data
      except Exception as e:
          error_data = e.json() if hasattr(e, 'json') else (e.args[0] if e.args else {})
          if isinstance(error_data, dict) and error_data.get('success'):
              current_app.logger.info(
                  "%s succeeded (JSONB response): attempt_id=%s",
                  rpc_name, error_data.get('attempt_id'),
              )
              return error_data
          current_app.logger.error("%s failed: %s", rpc_name, error_data)
          return jsonify({"error": error_message}), 500
  ```
  The four call sites become 1-2 lines each. Total reduction ~80 → ~30 lines.
- **Bonus:** While at it, file an upstream issue against `supabase-py` for the JSONB-success-throws-exception quirk that necessitates the `e.json()` workaround.

### RD-02 — Auth-decorator boilerplate (HI-01 above)
- **Files:** [middleware/auth.py:41-206](../../middleware/auth.py#L41-L206)
- **Consolidation:** see HI-01.

### RD-03 — Audio generation has two paths: `ai_service.AIService.generate_audio` (legacy) and `test_generation/agents/audio_synthesizer.py`
- **Files:** [services/ai_service.py:225-250](../../services/ai_service.py#L225-L250) (legacy OpenAI TTS → R2), `services/test_generation/agents/audio_synthesizer.py` (newer pipeline; not read in this pass).
- **Why it matters:** Two divergent code paths for the same operation (TTS + R2 upload). Risk: one gets a fix the other doesn't.
- **Proposed consolidation:** Confirm `AIService.generate_audio` callers; migrate them to `AudioSynthesizer` or vice versa. Delete the loser.

### RD-04 — Service-initialization try/except blocks in `app._initialize_services`
- **File:** [app.py:128-210](../../app.py#L128-L210) — 5 nearly-identical try/except wrappers.
- **Consolidation:** Extract `_init_optional("service-name", init_callable, on_success_attr)` helper that handles the `try/except + log success/failure + assign None on failure` pattern. Reduces 80 lines → ~20.
  - This also pairs naturally with HI-08's fail-fast vs. fail-soft decision.

### RD-05 — Tenacity retry decorators duplicated in `llm_service.py` and `ai_service.py`
- **Files:** [services/llm_service.py:199-212](../../services/llm_service.py#L199-L212) (`@retry` on `call_llm`), [services/ai_service.py:19-26](../../services/ai_service.py#L19-L26) (`_retry_api` on `AIService.generate_audio`).
- **Why it matters:** Two slightly different retry policies (same parameters, different log loggers). Single source of truth would prevent drift.
- **Consolidation:** Move the `_retry_api` decorator into a shared `services.llm_retry` module imported by both, or — given AIService is LEGACY — delete `ai_service.py`'s copy as part of the AIService retirement (CR-02 / HI-03).

---

## Structural Observations

### ST-01 — Three live god modules; the recon "extra-large" claims were wrong
Actual line counts (sanity-checked via `Get-Content | Measure-Object -Line`):
- `routes/admin_local.py` — **1,282 lines** (largest; admin dashboard, many endpoints).
- `routes/tests.py` — **1,281 lines** (close second; submit handlers + RPC wrappers).
- `services/test_generation/orchestrator.py` — **1,072 lines** (recently rewritten; the `_generate_test` / `_generate_vocabulary` flow can plausibly split into a `TestPipeline` + a `VocabularyPipeline` class).
- `services/test_service.py` — **778 lines** (borderline; manageable but watch for growth).
- `middleware/auth.py` — **166 lines** (NOT 8,344 as the recon misreported).
- `utils/question_validator.py` — **99 lines** (NOT 3,645).
- `utils/responses.py` — **55 lines** (NOT 2,535).
- `models/requests.py` — **57 lines** (NOT 2,261).

Action: only `routes/admin_local.py` and `routes/tests.py` warrant active splitting plans (group routes by feature → sub-blueprints). The orchestrator's main bulk is `_generate_test` (~250 lines); extracting `TestPipeline` / `VocabularyPipeline` classes would localize concerns.

### ST-02 — `app.config.from_object(Config)` copies all secrets into Flask config
- **File:** [app.py:54](../../app.py#L54)
- **Why it matters:** Any future code that exposes Flask's config (debug toolbar, an inadvertent `/admin/config` page, an error template that includes app config) leaks `SUPABASE_SERVICE_ROLE_KEY`, `STRIPE_SECRET_KEY`, etc. Defense-in-depth: Flask only needs `SECRET_KEY` in `app.config`; everything else can stay on `Config` class attributes.
- **Fix:** `app.config.update(SECRET_KEY=Config.SECRET_KEY, DEBUG=Config.DEBUG, LISTENING_LAB_ENABLED=Config.LISTENING_LAB_ENABLED)` — only what Flask itself needs. Read everything else via `from config import Config` directly.

### ST-03 — Blueprints configured via attribute mutation
- **File:** [app.py:302-303](../../app.py#L302-L303), [routes/auth.py:13](../../routes/auth.py#L13) (comment: `auth_bp.auth_service and auth_bp.device_service are set there`).
- **Pattern:** Mutate module-level `auth_bp` after import to inject services. Works because blueprints are global; breaks when two app instances are created (tests), or when a route is imported before services are assigned.
- **Fix:** Read services from `current_app.auth_service` inside handlers (already attached at app init). This decouples blueprints from app construction order.

---

## Quick Wins

Order roughly by impact-per-effort. Items marked **(blocker)** must merge before the next paid-tier release.

1. **(blocker)** Wire the Stripe webhook handler — CR-01.
2. **(blocker)** Stop fail-open in `moderate_content` — CR-03 (single line change).
3. Replace `SQLERRM` in submission RPCs with a generic error code — CR-04 (4 SQL files).
4. Add `timeout=30` to `r2_service.upload_from_url` — HI-04 (single line).
5. Fix `routes/auth.py::send_otp` `get_json()`-without-fallback — HI-07 (single line).
6. Extract `_call_rpc` helper, collapse 4 wrappers in `routes/tests.py` — RD-01 (~50-line net delete).
7. Bump `llm_calls` logging failure from DEBUG to WARNING — HI-09 (single line).
8. Delete dead branch in `_build_difficulty_schedule` — LO-01 (single block).
9. Delete `services/payment_service.py::PaymentService` or rewire it through `SupabaseFactory` and the new webhook — CR-02 + HI-03 + RD-05.

---

## Out of Scope / Follow-up

- `Portal/*` subprojects (MathDojo, MusicDojo, FeastOptimiser, Library) — separate apps; recon flagged similar issues there (broad except, no input validation in MusicDojo routes, direct bracket access in FeastOptimiser).
- `Corpuses/verify_collocations.py` — recon flagged an N+1 update loop at lines 62-69; out of scope for this main-app review.
- SQL schema review at depth — restricted to two recent migrations here.
- Frontend JS/TS, templates, i18n bundles.
- Static analysis tool setup (ruff / mypy / bandit + `pyproject.toml`) — could be its own follow-up task (none currently configured).
- Detailed review of `services/test_generation/database_client.py` (~900 lines), `services/study_plan_service.py` (~625 lines), and `services/test_service.py` — sampled only via outgoing references from the orchestrator and middleware; warrant their own focused passes.
- The "JSONB-success-throws-exception" supabase-py quirk that motivates the `e.json()` workaround in RD-01 — worth filing upstream.
