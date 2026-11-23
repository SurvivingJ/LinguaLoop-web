---
title: Token Economy — Technical Specification
type: feature-tech
status: deprecated
prose_page: ./token-economy.md
last_updated: 2026-11-23
dependencies:
  - "user_tokens table"
  - "token_transactions table"
  - "dim_subscription_tiers table"
  - "Stripe API"
breaking_change_risk: medium
open_questions: []
---

> **Retired 2026-11-23 by owner decision; proposed as a future implementation.** Removed from the code on 2026-11-23 (TASK-1210, commit on branch `review/retire-token-economy`): `GET /api/users/tokens`, `routes/payments.py` (`GET /api/payments/token-packages`) and its blueprint registration, `services/payment_service.py`, `Config.TOKEN_COSTS`, `DAILY_FREE_TOKENS`, `TOKEN_PACKAGES`, `STRIPE_SECRET_KEY`, the `stripe` pin in `requirements.txt`, both `grant_daily_free_tokens` calls in `services/auth_service.py` and `routes/users.py`, the `token_balance` / `tokenBalance` field of the login and profile payloads (no reader in `static/js` or `templates/`), and the token fields of `GET /api/config` and the `stripe` flag of `GET /api/health`. Nothing was changed in the database.
>
> **Kept, because the live submission RPCs need them:** `get_test_token_cost` (called by `process_test_submission`, `process_dictation_submission`, `process_pinyin_submission`, `process_pitch_accent_submission`, `process_classifier_drill_submission`), `test_attempts.tokens_consumed` / `was_free_test`, and the `p_was_free_test` argument. Every caller (`routes/tests/submit.py`, `services/drill_service.py`) passes `True`, so the recorded cost is always 0, the RPCs never read `user_tokens`, never debit and never block. Learners are not charged or blocked before or after the retirement.
>
> **Live objects left in place (verified 2026-11-23):** functions `add_tokens_atomic` (a stub that only checks authorisation and returns true), `can_use_free_test`, `get_daily_free_test_limit`, `get_test_token_cost`, `get_token_balance`, `process_stripe_payment`; tables `user_tokens` (18 rows), `token_transactions` (0 rows); `dim_subscription_tiers.tokens_per_test`, `daily_free_tests`, `monthly_token_grant`; `users.free_tests_used_today`, `last_free_test_date`, `total_free_tests_used`. No Python code calls the token functions now except through the five submission RPCs. Drop candidates for a later, separate migration: `add_tokens_atomic`, `get_token_balance`, `process_stripe_payment`, `can_use_free_test`, `get_daily_free_test_limit`, `user_tokens`, `token_transactions` (check [[business/pricing-plan.tech]] first: it may reuse them).
>
> The sections below are the 2026-05 design, kept as history.

## If rebuilt

Relation to the newer design: [[decisions/ADR-047-credits-and-subscription-model]] (hybrid subscription plus credits; founder answer 2026-11-17 retires daily free tokens) and [[tasklist/billing.tasks]] (TASK-982 to TASK-1000). A rebuild should start from that design, not from this page. A working token version would need:

1. **The grant function.** `grant_daily_free_tokens(p_user_id uuid)` created by a migration that follows `migrations/CLAUDE.md` (`SECURITY DEFINER`, `SET search_path`, `REVOKE` from PUBLIC/anon/authenticated, `GRANT` to `service_role`). It never existed live or in any migration.
2. **The balance columns.** The old route read `users.tokens` and `users.last_free_token_date`, which do not exist live. Either add them or read `user_tokens` (`purchased_tokens`, `bonus_tokens`) and keep one source of truth.
3. **A verified Stripe webhook.** A route that checks the signature with `stripe.Webhook.construct_event`, then credits through one RPC. `POST /api/payments/create-intent` must not return before the webhook exists.
4. **An idempotency constraint.** A unique index on `token_transactions.payment_intent_id` (today only a read-then-insert check; there is no constraint) so a retried webhook cannot double-credit.
5. **Atomic balance updates.** One database function that locks the `user_tokens` row, checks the balance and writes the ledger row together (`add_tokens_atomic` is a stub today; `process_stripe_payment` is the only function that credits), instead of the read-modify-write the old `PaymentService` did.
6. **A decision on what a token pays for**, and a way for the submission RPCs to actually charge it (they record a cost but never debit).

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

- [[decisions/ADR-047-credits-and-subscription-model]] — the newer credits and subscription design
- [[features/token-economy]] — Prose description
