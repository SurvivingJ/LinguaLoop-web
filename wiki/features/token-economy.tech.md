---
title: Token Economy — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./token-economy.md
last_updated: 2026-05-16
dependencies:
  - "user_tokens table"
  - "token_transactions table"
  - "dim_subscription_tiers table"
  - "Stripe API"
  - "services/payment_service.py"
  - "routes/payments.py"
breaking_change_risk: medium
---

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

- `POST /api/payments/create-intent` — create Stripe PaymentIntent. **(2026-05-15 fix)** Reads the user id from `g.current_user_id` (set by `supabase_jwt_required`) and writes `metadata.user_id`, matching what the webhook handler reads. Previously wrote `metadata.user_email` while the webhook read `metadata.user_id` — every webhook delivery for an intent created by this route would have raised `KeyError`.
- `POST /api/payments/webhook` — Stripe webhook handler.
- `GET /api/payments/balance` — current token balance.

## Webhook idempotency (2026-05-15)

`PaymentService.handle_successful_payment` now does an explicit idempotency check before crediting: it queries `token_transactions WHERE payment_intent_id = ? AND action = 'purchase' LIMIT 1` and short-circuits with `{'success': True, 'idempotent': True}` if a row exists. Stripe retries webhooks on 5xx, so without this check a duplicate delivery would have double-credited the user.

A small read-modify-write race still exists between the idempotency lookup and the credit update, but the duplicate-row check is the real safety net. A DB-side atomic increment (RPC) is the next planned improvement.

## Related Pages

- [[features/token-economy]] — Prose description
