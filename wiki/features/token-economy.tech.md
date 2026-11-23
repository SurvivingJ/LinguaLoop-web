---
title: Token Economy — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./token-economy.md
last_updated: 2026-11-23
dependencies:
  - "user_tokens table"
  - "token_transactions table"
  - "dim_subscription_tiers table"
  - "Stripe API"
  - "services/payment_service.py"
  - "routes/payments.py"
breaking_change_risk: medium
open_questions:
  - "Is the token economy meant to be revived? Today the daily free grant never happens (function missing), purchases cannot be fulfilled (no webhook route, no create-intent route) and GET /api/users/tokens fails. No decision is recorded on whether to rebuild (create grant_daily_free_tokens, add users.tokens / last_free_token_date or point the route at user_tokens, restore a signature-checked webhook) or retire the feature."
  - "can_use_free_test(uuid) is still live although this page says it was dropped 2026-05-15 (listed by pg_proc 2026-11-23). Unknown whether anything calls it."
---

> **Status update 2026-11-23: most of this page describes code that no longer runs.** Verified against the code tip and the live database the same day:
> - `POST /api/payments/create-intent` was **removed**. It created real Stripe PaymentIntents, no webhook route exists to credit tokens after payment, and nothing called it. `routes/payments.py` now registers only `GET /api/payments/token-packages` (returns `Config.TOKEN_PACKAGES`). There is no `POST /api/payments/webhook` and no `GET /api/payments/balance` route in the code. The comment in `routes/payments.py` says to restore create-intent only together with a webhook that checks the signature with `stripe.Webhook.construct_event` and calls `PaymentService.handle_successful_payment`.
> - `services/payment_service.py` still exists, is unused by any route and was left untouched.
> - **The daily free-token grant never happens.** The app calls the database function `grant_daily_free_tokens(p_user_id)` (`routes/users.py` `GET /api/users/tokens`, and `services/auth_service.py` on first login), but that function exists neither live nor in any migration (`migrations/security_function_grants_group_a.sql` records it as absent). `GET /api/users/tokens` therefore returns 500 (the RPC error is not caught; `@api_errors` turns it into a 500). Even with the function, the route then reads `users.tokens` and `users.last_free_token_date`, which do not exist live (the `users` table has `free_tests_used_today` and `last_free_test_date` only). In `auth_service.py` the failing call sits inside a try block that falls back to a zero balance.
> - Live token functions (2026-11-23): `add_tokens_atomic`, `can_use_free_test`, `get_daily_free_test_limit`, `get_test_token_cost`, `get_token_balance`, `process_stripe_payment`. Tables: `user_tokens`, `token_transactions`, `dim_subscription_tiers` (has `daily_free_tests`, `tokens_per_test`, `monthly_token_grant`).
>
> The sections below are the 2026-05 design and are kept as history, not as current behaviour.

# Token Economy — Technical Specification

## Database Impact

**Tables:** `user_tokens`, `token_transactions`, `dim_subscription_tiers`, `users`

**Key functions:**
- `get_token_balance(user_id)` → integer
- `get_test_token_cost(user_id)` → integer (tier-based)
- `get_daily_free_test_limit(user_id)` → integer
- `add_tokens_atomic(user_id, tokens, action, idempotency_key, ...)` → boolean
- `process_stripe_payment(user_id, tokens, payment_intent_id, package_id, amount_cents)` → boolean

> `can_use_free_test(user_id)` was dropped 2026-05-15 — see [[database/rpcs.tech]]. Daily-free logic now lives entirely in `PaymentService.get_user_token_balance` via the `last_free_token_date` comparison.

## API Surface

- ~~`POST /api/payments/create-intent`~~ **(removed 2026-11-23, see the status update above)** — created a Stripe PaymentIntent. **(2026-05-15 fix)** Reads the user id from `g.current_user_id` (set by `supabase_jwt_required`) and writes `metadata.user_id`, matching what the webhook handler reads. Previously wrote `metadata.user_email` while the webhook read `metadata.user_id` — every webhook delivery for an intent created by this route would have raised `KeyError`.
- `POST /api/payments/webhook` — Stripe webhook handler. **Not registered in the code (verified 2026-11-23).**
- `GET /api/payments/balance` — current token balance. **Not registered in the code (verified 2026-11-23).**
- `GET /api/payments/token-packages` — the only live payments route.
- `GET /api/users/tokens` — fails (see the status update).

## Webhook idempotency (2026-05-15) — design only; no webhook route exists as of 2026-11-23

`PaymentService.handle_successful_payment` now does an explicit idempotency check before crediting: it queries `token_transactions WHERE payment_intent_id = ? AND action = 'purchase' LIMIT 1` and short-circuits with `{'success': True, 'idempotent': True}` if a row exists. Stripe retries webhooks on 5xx, so without this check a duplicate delivery would have double-credited the user.

A small read-modify-write race still exists between the idempotency lookup and the credit update, but the duplicate-row check is the real safety net. A DB-side atomic increment (RPC) is the next planned improvement.

## Related Pages

- [[features/token-economy]] — Prose description
