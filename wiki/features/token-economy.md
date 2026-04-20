---
title: Token Economy & Payments
type: feature
status: in-progress
tech_page: ./token-economy.tech.md
last_updated: 2026-04-10
open_questions:
  - "Future subscription plans — what features will be gated? Translation practice, vocab tracking mentioned"
---

# Token Economy & Payments

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
