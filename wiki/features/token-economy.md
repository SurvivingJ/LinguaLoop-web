---
title: Token Economy & Payments
type: feature
status: in-progress
tech_page: ./token-economy.tech.md
last_updated: 2026-11-23
open_questions:
  - "The token economy is not working end to end as of 2026-11-23 (see the status note below). Rebuild or retire? No decision is recorded in the wiki."
  - "Future subscription plans — what features will be gated? Translation practice, vocab tracking mentioned"
---

# Token Economy & Payments

> **Status note 2026-11-23:** the description below is the intended design, not today's behaviour. Learners do not receive the daily free tokens (the database function the app calls for it does not exist), the balance endpoint fails, and no purchase can complete: the payment-intent route was removed because nothing credited tokens after a payment. Only the token-package list is still served. Details: [[features/token-economy.tech]].


## Purpose

LinguaLoop uses a token-based economy to meter premium content. Free-tier users get a limited number of daily free tests; beyond that, tests consume tokens that can be purchased via Stripe.

## How It Works

1. New users start on the free tier with a daily free test allowance.
2. Free tests reset daily (`last_free_test_date` + `free_tests_used_today` on users table).
3. Once free tests are exhausted, each test costs tokens (amount set per subscription tier).
4. Users purchase token packages via Stripe checkout.
5. Token transactions are logged in a ledger (`token_transactions`) with full audit trail.
6. Tokens come in two pools: `purchased_tokens` and `bonus_tokens`.

## Business Rules

- Token balances cannot go negative (enforced by CHECK constraints).
- Stripe payments are idempotent (checked by `payment_intent_id`).
- Admin and moderator roles can view other users' balances.
- Token cost per test is tier-dependent via `get_test_token_cost()`.

## Related Pages

- [[features/token-economy.tech]] — Technical specification
- [[database/schema.tech]] — `user_tokens`, `token_transactions`, `dim_subscription_tiers`
