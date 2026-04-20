---
title: Token Economy — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./token-economy.md
last_updated: 2026-04-10
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
- `can_use_free_test(user_id)` → boolean
- `add_tokens_atomic(user_id, tokens, action, idempotency_key, ...)` → boolean
- `process_stripe_payment(user_id, tokens, payment_intent_id, package_id, amount_cents)` → boolean

## API Surface

- `POST /api/payments/create-checkout` — create Stripe checkout session
- `POST /api/payments/webhook` — Stripe webhook handler
- `GET /api/payments/balance` — current token balance

## Related Pages

- [[features/token-economy]] — Prose description
