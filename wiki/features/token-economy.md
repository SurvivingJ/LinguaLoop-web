---
title: Token Economy & Payments
type: feature
status: deprecated
tech_page: ./token-economy.tech.md
last_updated: 2026-11-23
open_questions:
  - "If the token economy is rebuilt: what does a token pay for, and how does it relate to the credits and subscription model in ADR-047 (credits-and-subscription-model)? See 'If rebuilt' below."
---

# Token Economy & Payments

> **Retired 2026-11-23 by owner decision; proposed as a future implementation.** The application side was removed on 2026-11-23 (TASK-1210): the daily free-token grant, the balance endpoint, the token-package list and the payment service. Learners were never charged or blocked by tokens (every test submission is recorded as a free test), so nothing a learner can do changed. The text below is the original design, kept as history. Details: [[features/token-economy.tech]]. The monetisation plan that is actually being designed is [[decisions/ADR-047-credits-and-subscription-model]] and [[tasklist/billing.tasks]].

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

## If rebuilt

A working version would need a daily free-token grant that exists in the database, a place to keep each learner's balance that the app actually reads, a payment webhook that checks Stripe's signature and cannot credit the same payment twice, and balance changes that cannot race. It would also need to be reconciled with the credits and subscription model in [[decisions/ADR-047-credits-and-subscription-model]] (founder answer 2026-11-17: daily free tokens are retired). Technical list: [[features/token-economy.tech]].

## Related Pages

- [[decisions/ADR-047-credits-and-subscription-model]] — the newer credits and subscription design

- [[features/token-economy.tech]] — Technical specification
- [[database/schema.tech]] — `user_tokens`, `token_transactions`, `dim_subscription_tiers`
