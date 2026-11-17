---
title: "Billing, Credits and Plans — Task Breakdown"
feature: billing
prose_page: ../business/pricing-plan.md
tech_page: ../business/pricing-plan.tech.md
total_tasks: 25
done: 0
---

# Billing, Credits and Plans — Task Breakdown

Draft for founder review (2026-11-17). **Planning only: no code has been changed.** The tasks
implement [[business/pricing-plan]] (Free / Core / Pro, PAYG credit packs) as specified in
[[business/pricing-plan.tech]] and [[decisions/ADR-047-credits-and-subscription-model]].

The code map behind these tasks was taken on 2026-11-17 by two read-only passes over the repo.
Each task's file:line references come from that map, so check them before editing.

## Phases

| Phase | Gate | Tasks |
|---|---|---|
| **G0a: foundations** (no user-visible change) | none | TASK-976 – TASK-982 |
| **G0b: payments** | D4 (provider) for consumer checkout | TASK-983 – TASK-986 |
| **G0c: enforcement** (behind `ENTITLEMENTS_ENFORCED`) | G0a done | TASK-987 – TASK-992 |
| **G0d: product surfaces Pro needs** | founder scope decisions | TASK-993 – TASK-995 |
| **G0e: launch** | all of the above | TASK-996 – TASK-997 |
| **G1a: tutors (month 13)** | G0 live + gate metric | TASK-998 – TASK-1000 |

Schools (G1) and translators (G2) are not broken down yet. They need the `classes-and-assignments`
feature spec first.

## Things the code map changed

1. **TASK-875 is applied.** `users_update_own` and the related policies were dropped live on
   2026-11-11 ([[tasklist/security-hardening.tasks]]), so clients cannot raise their own
   `subscription_tier_id`. The billing blocker in [[business/pricing-plan.tech]] is resolved.
   `database/schema.tech.md:460` is stale (TASK-976 fixes the docs).
2. **There are two balance stores.**
   - `PaymentService` uses `user_tokens`. It is never constructed, and nothing calls it.
   - The live `GET /api/users/tokens` reads **`users.tokens`** after calling the RPC
     `grant_daily_free_tokens` (`routes/users.py:28-50`).
   - TASK-977 settles this before any ledger work.
3. **Pro's selling points mostly don't exist yet.**
   - Pro differs from Core by DT 25/day (exists), the full per-word knowledge report
     (**no report exists at all**) and 300 credits a month.
   - Of the credit actions, only new-word import (an import route exists) and DT over the cap
     are buildable now. User custom tests and deep re-grade have no route.
   - Without TASK-993/994, Pro at launch is "Core + more DT + credits for word imports". See the
     founder questions at the end.
4. **Tests have no "start" route.** `GET /api/tests/<slug>` works without login. The daily-test
   limit therefore needs a logged-in pre-check on the test page plus a backstop at submit
   (TASK-987).
5. **The DT token budget never blocks.** It only drops the grader to tier 1. DT cost logging
   writes NULL `cost_usd` for `:free` models, by design (TASK-992).

---

## TASK-976: Docs reconciliation before billing work

**Status:** [ ] Not Started
**Feature:** billing
**Type:** docs
**Complexity:** XS
**Depends On:** none

**Description:**
Correct the stale statements found during planning so later tasks start from accurate docs.

**Acceptance Criteria:**
- [ ] `wiki/database/schema.tech.md:460`: the `users` RLS note says TASK-875 was applied 2026-11-11 and the update policies were dropped.
- [ ] `wiki/business/pricing-plan.tech.md`: the TASK-875 open question and the "Blocker before G0" bullet are marked ANSWERED.
- [ ] The same page says word-list `batch_limits` are in-code limits (`services/word_list_import/batch_limits.py`), not a table.
- [ ] `wiki/features/token-economy.tech.md`: the non-existent `POST /api/payments/webhook` is marked "planned (TASK-983)".
- [ ] `wiki/business-rules/auth-and-access.md`: Free = 1 test/day (production seed).

**Files to Create / Modify:** the four wiki pages above.

**Verification:** `grep -n "not yet applied" wiki/database/schema.tech.md` no longer matches the users row.

---

## TASK-977: Settle the balance store (`users.tokens` vs `user_tokens`)

**Status:** [ ] Not Started
**Feature:** billing
**Type:** refactor
**Complexity:** S
**Depends On:** TASK-976

**Description:**
Production has two token balances: `users.tokens`, which is live via `/api/users/tokens` and
`grant_daily_free_tokens`, and `user_tokens`, which is dead code in `PaymentService`. The new
ledger extends `user_tokens` (tech spec, Key Decision 2), so `users.tokens` must be
read-migrated and retired.

**Acceptance Criteria:**
- [ ] A read-only SQL audit is recorded in the task log:
  - the count of users with `users.tokens > 0`;
  - the sum of `users.tokens`;
  - the count of `user_tokens` rows and the sum of `purchased_tokens` and `bonus_tokens`;
  - what `grant_daily_free_tokens` writes.
- [ ] A decision is recorded on the wiki page, with the default: daily free tokens are **discontinued**, because the free tier is now count-based. Any `users.tokens` balance from purchases (expected 0) converts 1:1 into `user_tokens.purchased_tokens` in TASK-979. Free daily grants are not converted.
- [ ] `GET /api/users/tokens` is listed for replacement by `GET /api/billing/entitlements` (TASK-980). The route keeps working until TASK-997.

**Technical Notes:** read with the Supabase MCP `execute_sql` (SELECT only). Do not change data in this task.

**Files to Create / Modify:**
- `wiki/business/pricing-plan.tech.md` — "Current state" table gains a `users.tokens` row and the decision

**Verification:** the audit numbers and the decision appear on the wiki page.

---

## TASK-978: Migration — plans, prices, subscriptions, entitlements (LIVE-DB, approval)

**Status:** [ ] Not Started
**Feature:** billing
**Type:** infra
**Complexity:** M
**Depends On:** TASK-977

**Description:**
Create the billing catalogue and subscription state from tech spec §1–4 and §8.

**Acceptance Criteria:**
- [ ] New tables, with RLS enabled:
  - `billing_events` (UNIQUE `provider, event_id`)
  - `plan_prices` (UNIQUE `plan_code, currency, interval, price_version`)
  - `subscriptions` (CHECK exactly one of `owner_user_id` / `owner_org_id`; `owner_org_id` stays nullable without an FK until TASK-998)
  - `tier_entitlements` (PK `tier_id, entitlement_key`)
  - `user_entitlement_overrides`
- [ ] `dim_subscription_tiers`:
  - Gains `allowance_rollover_cap`.
  - Rows `free`, `core`, `pro`, `pro_lifetime` and `admin` exist with `monthly_token_grant` 0/0/300/150/0.
  - `premium` and `enterprise` are `is_active=false`, after a SELECT shows they have no users.
  - `tokens_per_test` is 0 on every row.
  - The other tiers in the spec (`professional`, `exam_pass`, school, tutor) are **not** seeded yet; they belong to G1/G2.
- [ ] `tier_entitlements` is seeded for `free`, `core`, `pro` and `pro_lifetime` exactly as in the spec table. Core and Pro differ only in `dt_per_day` (5 vs 25), `bkt_report_detail` (0 vs 1) and `monthly_token_grant`.
- [ ] `plan_prices` seed, `price_version=1`:
  - Core and Pro, month and year, in USD/AUD/EUR/GBP;
  - `pro_founding`, `pro_student` and `pro_lifetime` in USD/AUD;
  - packs 500/1,100/2,500 in USD/AUD.
  - Amounts come from the spec's launch seed, with `provider_price_id` NULL.
- [ ] The users with history get `user_entitlement_overrides(tests_new_per_day=2, reason='grandfathered_2026')`. The count is taken from the live query; the business case says 18.
- [ ] All functions and grants follow `migrations/CLAUDE.md`. `tests/test_migration_security_lint.py` passes.
- [ ] The migration is idempotent.

**Technical Notes:**
- No client grants on any of these tables. `plan_prices` is read by the server and exposed through routes.
- Keep the old boolean tier columns readable; nothing writes them.
- EUR/GBP amounts are derived and need founder confirmation before TASK-984 provisions them in Stripe. Seeding them as data is fine.

**Files to Create / Modify:**
- `migrations/billing_core.sql` — new
- `tests/sql/test_billing_core.sql` — seed and constraint checks
- `wiki/database/schema.tech.md` — new tables; tier rows
- `wiki/api/rpcs.tech.md` — none yet (RPCs are added in TASK-979)

**Verification:** `pytest tests/test_migration_security_lint.py -q` passes. Applying twice to a scratch database is a no-op. `SELECT tier_code, entitlement_key, int_limit FROM tier_entitlements JOIN dim_subscription_tiers ...` matches the spec table.

---

## TASK-979: Migration — credit ledger and RPCs (LIVE-DB, approval)

**Status:** [ ] Not Started
**Feature:** billing
**Type:** infra
**Complexity:** L
**Depends On:** TASK-978

**Description:**
Extend `user_tokens` and `token_transactions` into the three-pool ledger (allowance, then bonus,
then purchased). Add the atomic credit RPCs from tech spec §5–6 and "RPCs". This replaces the
read-modify-write in `PaymentService.consume_tokens`.

**Acceptance Criteria:**
- [ ] `user_tokens` gains `allowance_tokens` (CHECK ≥ 0) and `allowance_period_end`.
- [ ] A new `credit_grants` table exists.
- [ ] `token_transactions` gains `pool`, `org_id`, `idempotency_key` (UNIQUE `user_id, idempotency_key`), `llm_call_ids` (type matched to the `llm_calls` PK; check it) and `actual_cost_usd`.
- [ ] The `action` CHECK allows the new values. `study_pass` is not included.
- [ ] New RPCs:
  - `spend_credits` locks the `user_tokens` row with `SELECT ... FOR UPDATE`, spends in pool order, and writes one transaction row per pool.
  - On a duplicate idempotency key, `spend_credits` returns the original result.
  - `refund_credits`, `grant_credits`, `reset_allowance` (rollover cap = grant + cap; a no-op for grant 0) and `expire_bonus_credits`.
  - All are SECURITY DEFINER, `service_role` only.
- [ ] Legacy conversion: any purchased balance found in TASK-977 is granted as `purchased` with action `legacy_conversion`.
- [ ] `get_test_token_cost` returns 0. Callers are unchanged; the RPC is dropped later.
- [ ] SQL tests cover:
  - pool order;
  - insufficient balance;
  - duplicate key;
  - rollover (300 + 300 → 600; 300 + 450 → 600 with 150 expired);
  - Core grant 0;
  - refund back into the original pools;
  - two concurrent spends never take the balance negative. Run the concurrency check with two psql sessions and record it in the task log.

**Technical Notes:**
- Re-implement `process_stripe_payment` as a thin wrapper over `grant_credits` or drop it; it has no callers (`migrations/security_function_grants_group_a.sql`).
- Keep `add_tokens_atomic` until TASK-982 has removed the old code paths.

**Files to Create / Modify:**
- `migrations/billing_ledger.sql` — new
- `tests/sql/test_billing_ledger.sql` — new
- `wiki/api/rpcs.tech.md` — the five RPCs
- `wiki/database/schema.tech.md` — ledger columns

**Verification:** the SQL tests pass on a scratch database. A concurrent-spend run leaves `sum(token_transactions)` equal to the pools.

---

## TASK-980: Entitlements service, flag and endpoint

**Status:** [ ] Not Started
**Feature:** billing
**Type:** feature
**Complexity:** M
**Depends On:** TASK-979

**Description:**
One server-side function that every gated route calls. It returns the effective tier, the
limits, the flags and the credit balances. It is request-cached like the ADR-042 helpers.
Enforcement stays off until the flag is set.

**Acceptance Criteria:**
- [ ] SQL RPC `get_entitlements(p_user_id)` follows the spec. Precedence: own active subscription (including `trialing`, and `past_due` within 7 days), then override, then free. The org source is stubbed until TASK-998.
- [ ] `services/billing/entitlements.py`:
  - `get_entitlements(user_id)` wraps the RPC with `services/request_cache.memo`.
  - Helpers: `limit(key)`, `flag(key)`, `usage_today(key)` and `usage_this_week(key)`.
  - `invalidate()` is called after any spend or grant.
- [ ] `Config.ENTITLEMENTS_ENFORCED` defaults to False, using the flag pattern at `config.py:136+`. When False, every check logs what it *would* have denied (`entitlement_shadow_deny`) and allows the action.
- [ ] `GET /api/billing/entitlements` (`jwt_required`) is on a new blueprint `billing_bp` at `/api/billing`, registered in `app.py:_register_blueprints`.
- [ ] One 402 helper, `payment_required(error, **extra)`, returns `{error, upgrade: true, ...}` for every gate.
- [ ] Unit tests cover precedence and the cache (one RPC call per request).

**Files to Create / Modify:**
- `services/billing/__init__.py`, `services/billing/entitlements.py` — new
- `routes/billing.py` — new blueprint
- `app.py` — import and register
- `config.py` — `ENTITLEMENTS_ENFORCED`
- `migrations/billing_ledger.sql` or a new `migrations/billing_entitlements_rpc.sql` — the RPC
- `tests/test_billing_entitlements.py` — new, using `tests/conftest.py:mock_supabase`

**Verification:** `pytest tests/test_billing_entitlements.py -q`. With the flag off, hitting a gated route over its limit returns 200 and logs `entitlement_shadow_deny`.

---

## TASK-981: Credits service and quote endpoint

**Status:** [ ] Not Started
**Feature:** billing
**Type:** feature
**Complexity:** S
**Depends On:** TASK-980

**Description:**
A Python wrapper over the ledger RPCs, plus the credit price list as data, so every metered action
quotes and spends the same way.

**Acceptance Criteria:**
- [ ] `services/billing/credits.py`:
  - `CREDIT_COSTS = {dt_grade_overcap: 1, sense_import: 8, custom_test: 10, ref_set: 30, deep_regrade: 8, mock_grade: 25}`.
  - `quote(action, params)`.
  - `spend(user_id, action, amount, idempotency_key, llm_call_ids=None)`.
  - `refund(group_key, reason)`.
  - `attach_cost(transaction_key, llm_call_ids, cost_usd)`.
- [ ] `POST /api/credits/quote` returns `{credits, requires_confirm: credits >= 20, balance}` and is rate-limited in `web/rate_limits.py:ENDPOINT_LIMITS`.
- [ ] Idempotency keys are deterministic per action, e.g. `dt:<submission_id>` and `sense:<batch_id>:<sense_key>`.

**Files to Create / Modify:**
- `services/billing/credits.py` — new
- `routes/billing.py` — the quote route (or a `credits_bp` at `/api/credits`)
- `web/rate_limits.py` — limits
- `tests/test_billing_credits.py` — new

**Verification:** `pytest tests/test_billing_credits.py -q`.

---

## TASK-982: Retire the dead token code

**Status:** [ ] Not Started
**Feature:** billing
**Type:** refactor
**Complexity:** S
**Depends On:** TASK-981

**Description:**
Remove the legacy token path, which is unused and buggy (`package.price_cents` attribute access on
dicts), so nothing can reach it by accident.

**Acceptance Criteria:**
- [ ] `services/payment_service.py` is deleted: it has no callers. Its `get_user_transaction_history` logic moves to `services/billing/credits.py`.
- [ ] `Config.TOKEN_COSTS`, `DAILY_FREE_TOKENS` and `TOKEN_PACKAGES` (`config.py:377-397`) are removed.
- [ ] `/api/config` (`app.py:277-289`) returns `credit_costs` from `CREDIT_COSTS` instead of `token_costs`.
- [ ] `GET /api/payments/token-packages` reads active `plan_prices` (packs and plans) for the requested currency.
- [ ] `grep -rn "TOKEN_PACKAGES\|PaymentService\|daily_free_tokens" --include=*.py --include=*.js` returns nothing outside `archive/` and migrations.

**Files to Create / Modify:**
- `services/payment_service.py` — delete
- `config.py`, `app.py`, `routes/payments.py` — as above
- `static/js/**` — any reader of `token_costs`. None is expected; confirm with grep.

**Verification:** the grep above, plus `pytest -q` passes.

---

## TASK-983: Stripe webhook route with idempotency and event dispatch

**Status:** [ ] Not Started
**Feature:** billing
**Type:** feature
**Complexity:** L
**Depends On:** TASK-981

**Description:**
`POST /api/payments/webhook` verifies the `Stripe-Signature`, records the event in `billing_events`
(a duplicate returns 200 at once) and dispatches it. This is the only writer of subscription state
and `users.subscription_tier_id`. Stripe is needed whatever D4 decides, because AU tutors and
packs go through Stripe.

**Acceptance Criteria:**
- [ ] `Config.STRIPE_WEBHOOK_SECRET` exists. Missing in production means the route returns 503, not 200.
- [ ] The raw body is read with `request.get_data()`; no hook parses it. The route has no JWT and no rate-limit bucket shared with users.
- [ ] Handlers for every event in tech spec "Stripe / MoR event handling":
  - `checkout.session.completed` (subscription / payment)
  - `payment_intent.succeeded`
  - `customer.subscription.updated`, including the prorated Core→Pro allowance and Pro→Core zeroing
  - `customer.subscription.deleted`
  - `invoice.paid`
  - `invoice.payment_failed` (7-day grace)
  - `charge.refunded`
  - `charge.dispute.created`
- [ ] Credits are looked up from `plan_prices` by `plan_code` + `price_version`. `metadata.tokens` is never trusted.
- [ ] Out-of-order delivery is handled: `updated` before `created` upserts by `provider_subscription_id`.
- [ ] Errors set `billing_events.error` and return 500, so Stripe retries.
- [ ] Tests: each event fixture delivered twice gives one effect; a bad signature returns 400.

**Files to Create / Modify:**
- `routes/payments.py` — webhook route
- `services/billing/stripe_events.py` — new dispatcher
- `config.py` — `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`
- `tests/fixtures/stripe/*.json` — event fixtures (captured with `stripe trigger` in test mode)
- `tests/test_billing_stripe_webhook.py` — new

**Verification:** `pytest tests/test_billing_stripe_webhook.py -q`. Then `stripe listen --forward-to localhost:5000/api/payments/webhook` with `stripe trigger checkout.session.completed` in test mode.

---

## TASK-984: Stripe provisioning, checkout and portal

**Status:** [ ] Not Started
**Feature:** billing
**Type:** feature
**Complexity:** M
**Depends On:** TASK-983

**Description:**
Create the Stripe Products and Prices from `plan_prices`, then the checkout and customer-portal
routes.

**Acceptance Criteria:**
- [ ] `scripts/provision_stripe_prices.py` is idempotent by `lookup_key = <plan_code>_<currency>_<interval>_v<price_version>`.
  - Core and Pro are separate Products.
  - It writes `provider_price_id` back to `plan_prices`.
  - It defaults to `--dry-run` and needs `--live` for live mode.
- [ ] `POST /api/billing/checkout {plan_code, currency, interval}` creates a Checkout Session.
  - Mode `subscription` or `payment`.
  - `client_reference_id=user_id`, with metadata `plan_code` and `price_version`.
  - The founding and lifetime seat counters are enforced server-side.
  - It returns `{url}`.
- [ ] `POST /api/payments/create-intent` reads `plan_prices` and sets metadata `{user_id, plan_code, credits, price_version}`, or is removed in favour of Checkout mode `payment`. Pick one and record it.
- [ ] `GET /api/billing/portal` returns a Billing Portal session URL, with Core ↔ Pro switching and cancellation enabled in the portal config.
- [ ] Stripe Tax is on for AU GST.

**Technical Notes:** if D4 picks a merchant of record for global consumers, this task still ships Stripe for AU and packs. TASK-985 adds the MoR path, and `plan_prices.provider` selects it per row.

**Files to Create / Modify:**
- `scripts/provision_stripe_prices.py` — new
- `routes/billing.py` — checkout and portal
- `routes/payments.py` — create-intent change
- `tests/test_billing_checkout.py` — new

**Verification:** in Stripe test mode, `python scripts/provision_stripe_prices.py --test` creates 8 + 6 + 6 prices. A second run creates 0. Checkout then completes and the webhook sets the user to `core`.

---

## TASK-985: Merchant-of-record adapter (consumer checkout outside AU)

**Status:** [?] Blocked — needs **D4** (Paddle vs Stripe Managed Payments vs Stripe + own VAT)
**Feature:** billing
**Type:** feature
**Complexity:** L
**Depends On:** TASK-983, D4

**Description:**
If D4 picks a merchant of record, add its webhook (`POST /api/billing/mor-webhook`), signature
check, event mapping into the same `services/billing` handlers, and checkout.

**Acceptance Criteria:** (to be finalised after D4)
- [ ] The provider's events map onto the same subscription and credit transitions as Stripe. The event names are verified against the provider's docs.
- [ ] `plan_prices.provider='mor'` rows route checkout to the MoR.
- [ ] The duplicate and out-of-order tests from TASK-983 are repeated for the MoR.

**Verification:** to be defined after D4.

---

## TASK-986: Scheduled billing jobs and nightly reconciliation

**Status:** [ ] Not Started
**Feature:** billing
**Type:** infra
**Complexity:** S
**Depends On:** TASK-983

**Description:**
Add jobs to `web/scheduler.py:JOBS` for bonus expiry, monthly allowance resets on annual and
lifetime plans (monthly plans reset on `invoice.paid`), grace-period downgrades, and a
reconciliation report.

**Acceptance Criteria:**
- [ ] Each job has `id`, a `module:function` target and a UTC cron, placed outside the 03:50–04:20 slot already used:
  - `billing_expire_bonus`
  - `billing_reset_annual_allowances` (users whose `allowance_period_end <= now()` on a yearly or lifetime plan)
  - `billing_grace_downgrade` (`past_due` older than 7 days → free)
  - `billing_reconcile`
- [ ] `billing_reconcile` writes a report row or a log line:
  - users where the transaction sum ≠ the pools (must be 0);
  - per action, credits charged vs `llm_calls.cost_usd` linked by `llm_call_ids` (the D9 data).
- [ ] Every job is idempotent if run twice.

**Files to Create / Modify:**
- `web/scheduler.py` — four jobs
- `services/billing/jobs.py` — new
- `tests/test_billing_jobs.py` — new

**Verification:** `pytest tests/test_billing_jobs.py -q`. Running each job twice by hand leaves the same state.

---

## TASK-987: Daily new-test limit (Free 1/day) — page pre-check and submit backstop

**Status:** [ ] Not Started
**Feature:** billing
**Type:** feature
**Complexity:** M
**Depends On:** TASK-980

**Description:**
Free users may start one *new* test a day (2 if grandfathered); retakes are unlimited. Paid
tiers have no cap. There is no test-start route, and `GET /api/tests/<slug>` works without login.
So the check happens on the logged-in test page load, with a backstop at submit.

**Acceptance Criteria:**
- [ ] `usage_today('tests_new_per_day')` counts distinct `test_id` in `test_attempts`:
  - for this user since local midnight (`services/day_boundary.plan_today_iso`);
  - only tests with no earlier attempt by the user, across all test types (`is_first_attempt` is per test *type*, so it cannot be used directly);
  - excluding drill sentinel tests.
- [ ] The test page (or a new `GET /api/tests/<slug>/access`, `jwt_required`) returns `{allowed, reason, limit, used}`. The front end shows `PaywallPanel` (TASK-995) before the learner starts.
- [ ] Submit backstop in `routes/tests/submit.py:_submit_rpc` (:81): over the limit and enforced → 402 `daily_test_limit`.
- [ ] The hardcoded `'p_was_free_test': True` at `submit.py:103` and `services/drill_service.py:183` becomes `p_was_free_test = (tier == 'free')`, for analytics only.
- [ ] Drills (classifier and counter) are not counted.
- [ ] Tests cover:
  - Free first new test allowed, second denied;
  - a retake allowed;
  - a grandfathered user gets 2;
  - Core unlimited;
  - flag off allows and logs.

**Files to Create / Modify:**
- `routes/tests/submit.py`, `routes/tests/catalog.py` (or a new access route), `services/drill_service.py`
- `services/billing/entitlements.py` — usage counter
- the test page JS that loads the test — the pre-check call
- `tests/test_billing_test_limit.py` — new

**Verification:** `pytest tests/test_billing_test_limit.py -q`. Manually, as a free user with the flag on, the second new test of the day shows the paywall before it starts.

---

## TASK-988: Daily session and prestudy clamps for Free

**Status:** [ ] Not Started
**Feature:** billing
**Type:** feature
**Complexity:** M
**Depends On:** TASK-980

**Description:**
Free gets 10 session minutes a day, 5 new words a day and 1 prestudy a week. Paid tiers have no
cap. Session clamps are silent and show a banner. Prestudy over the cap returns 402.

**Acceptance Criteria:**
- [ ] Effective `daily_minutes = min(plan value, session_minutes_per_day)` and `new_words_per_day = min(plan value, entitlement)`.
  - Applied where the plan is read for building: `services/study_plan_service.py:compute_weekly_plan` (~755) and the inputs to the `build_daily_session` RPC (`study_plan_service.py:969-988`).
  - The user's stored plan values are **not** overwritten, so upgrading restores them at once.
- [ ] `GET /api/study-session` (`routes/study_session.py:101`) returns `clamped: {minutes, new_words}` when a clamp applied. The UI shows an upsell banner.
- [ ] `start_test_prestudy_session` (`routes/tests/prestudy.py:69`) counts this week's `prestudy_sessions` rows for the user and returns 402 `prestudy_limit` over `prestudy_per_week`.
- [ ] Prestudy *Produce* (`prestudy.py:238`) uses DT grading, so it goes through the DT cap in TASK-989 as well.
- [ ] Tests cover each clamp, no clamp on Core, and upgrade restoring the plan values.

**Files to Create / Modify:**
- `services/study_plan_service.py`, `routes/study_session.py`, `routes/tests/prestudy.py`
- the session UI JS — the banner
- `tests/test_billing_session_clamps.py` — new (use `tests/_study_plan_fakes.py:FakeDb`)

**Verification:** `pytest tests/test_billing_session_clamps.py -q`. With the flag on, a free user's session has at most 10 minutes and 5 new words.

---

## TASK-989: Dual-translation caps, over-cap credits and refunds

**Status:** [ ] Not Started
**Feature:** billing
**Type:** feature
**Complexity:** M
**Depends On:** TASK-981

**Description:**
DT is count-capped per tier: Free 5 a week, Core 5 a day, Pro 25 a day. Over the cap costs 1
credit, refunded if the grade fails. The global token budget becomes a per-tier cost backstop.

**Acceptance Criteria:**
- [ ] `routes/dual_translation.py:162 submit`:
  - Count successful grades from `dt_grade` rows: Free since the start of the week, paid since local midnight. `dt_submission` rows are created when a passage is served, so they cannot be counted.
  - Under the cap → grade.
  - Over the cap → `credits.spend(1, 'dt_grade_overcap', key='dt:<submission_id>')`. A short balance returns 402 `dt_cap` with `credits_required: 1`.
- [ ] A cached grade (early return at :191) is never charged.
- [ ] A refund is issued when the grade fails:
  - an exception (the 500 path at :296);
  - `overall_band is None` (:245);
  - a provisional result: refund only if the product decision says so; default is no refund, because a grade was shown.
- [ ] The token guardrail at :208 / `_tokens_used_today` (:786) compares against `dt_tokens_per_day` for the tier instead of `Config.DT_DAILY_TOKEN_BUDGET`. Behaviour is unchanged (drop to tier 1, never block).
- [ ] Guided-repair re-checks (`routes/dt_repair.py:100`) are **not** counted against the cap. They are part of the same submission.
- [ ] The prestudy Produce path is counted the same way.
- [ ] Tests cover:
  - Core's 6th grade costs 1 credit and Pro's 26th;
  - Free's 6th this week costs 1;
  - a refund on exception;
  - a cached grade free;
  - a replay with the same submission charges once.

**Files to Create / Modify:**
- `routes/dual_translation.py`, `routes/tests/prestudy.py` (Produce)
- `services/dual_translation/repair/budget.py` — per-tier budget
- `tests/test_billing_dt_caps.py` — new

**Verification:** `pytest tests/test_billing_dt_caps.py -q`. Manually, as a Core test user with the flag on, the 6th DT submission shows "1 credit" and debits once.

---

## TASK-990: Word-list import — dictionary gate and per-new-sense credits

**Status:** [ ] Not Started
**Feature:** billing
**Type:** feature
**Complexity:** M
**Depends On:** TASK-981

**Description:**
Importing dictionary words is included for Core and Pro (`word_import_dictionary`); Free cannot
import. Each sense *not* in the dictionary costs 8 credits, quoted before submit and refunded if
its generation fails.

**Acceptance Criteria:**
- [ ] `POST /api/word-list/submit` (`routes/word_list_import.py:220`) returns 403 `upgrade` for Free when enforced.
- [ ] Before queueing, the route resolves which submitted words have no sense yet, quotes `8 × n_new`, and needs `confirm=true` when the quote is 20 or more. It then spends with key `import:<batch_id>`.
- [ ] `_run_upload_in_background` refunds the credits for senses that failed generation, as partial refunds keyed per sense.
- [ ] The existing in-code limits stay (`batch_limits.py`: 5 batches a day, 50 words per submit, 429).
- [ ] Each debit links the generation's `llm_calls` ids through `attach_cost` (D9 data).
- [ ] Tests cover:
  - Free 403;
  - a Core all-dictionary list costs 0;
  - 3 new senses cost 24;
  - one failure refunds 8;
  - a short balance returns 402.

**Files to Create / Modify:**
- `routes/word_list_import.py`, the background job module in `services/word_list_import/`
- the word-list page JS — quote and confirm
- `tests/test_billing_word_import.py` — new

**Verification:** `pytest tests/test_billing_word_import.py -q`.

---

## TASK-991: Trainer level cap for Free

**Status:** [?] Blocked — needs a founder decision on whether it is worth building (see questions)
**Feature:** billing
**Type:** feature
**Complexity:** S
**Depends On:** TASK-980

**Description:**
The plan gives Free only "taster levels" of the trainers. Pinyin and pitch accent are per-test
pages, not levelled trainers. The classifier and counter drills carry an item `level`
(`drill_service.py:68-95`) but have no level selector. A cap would filter items at
`DrillService.get_session` (`drill_service.py:134`) to `level <= trainer_level_max`.

**Acceptance Criteria:** (if kept)
- [ ] Free drill sessions only serve items with `level <= 2`. Paid tiers are unfiltered.
- [ ] Pinyin and pitch-accent pages follow the test limit (TASK-987) and get no separate cap.

**Verification:** `pytest tests/test_drills*.py -q` plus a new free-tier case.

---

## TASK-992: Fix DT cost logging (prerequisite for the D9 re-price data)

**Status:** [ ] Not Started
**Feature:** billing
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
Production `llm_calls` rows for `dt_single_call_grade` have NULL `cost_usd` and 0 tokens. Without
these, the reconciliation report (TASK-986) cannot compare credits with cost.

**Acceptance Criteria:**
- [ ] Find out which of these causes the 0 tokens: the instrumentation columns being missing live (which triggers the column-stripping retry in `services/llm_service.py:583-613`), or the provider omitting usage. Record the answer.
- [ ] Tokens are always logged when the provider returns `usage`.
- [ ] When `usage.cost` is missing, write `cost_usd` NULL as now (no estimates) **and** set a new `cost_estimated_usd` from the model price table. The reconciliation report then uses the measured cost where present and the estimate otherwise, and labels which is which.
- [ ] The v1/v2 path (`grader_cascade.py:911,1722`, `call_model_with_usage`) logs through `_log_llm_call` too.

**Files to Create / Modify:**
- `services/llm_service.py`, `services/dual_translation/single_call_grader.py`, `services/dual_translation/grader_cascade.py`
- a migration, if `cost_estimated_usd` is added: `migrations/llm_calls_cost_estimate.sql`
- `tests/test_llm_cost_logging.py` — new or extended

**Verification:** after one DT grade on staging, `SELECT prompt_tokens, completion_tokens, cost_usd, cost_estimated_usd FROM llm_calls WHERE task='dt_single_call_grade' ORDER BY created_at DESC LIMIT 1` shows non-zero tokens and one of the costs.

---

## TASK-993: Knowledge report — summary (Free/Core) and full per-word view (Pro)

**Status:** [?] Blocked — needs a feature spec; the founder must confirm it is in launch scope
**Feature:** billing
**Type:** feature
**Complexity:** L
**Depends On:** TASK-980

**Description:**
`bkt_report_detail` is one of only three differences between Core and Pro, but **no knowledge
report exists**. `VocabularyKnowledgeService` has no read or summary method. The nearest surfaces
are the profile ELO and history, `/api/flashcards/stats` and the DT error profile. Write a feature
spec first (`features/knowledge-report.md` + `.tech.md`), then build:
- a summary: words known by band, recent growth, weak families;
- a full per-word table: `p_known`, last seen, ladder level, filter and sort.

**Acceptance Criteria:** (to be finalised in the spec)
- [ ] `GET /api/knowledge/summary` is available to all tiers. `GET /api/knowledge/words` is Pro only (402 otherwise).
- [ ] A page linked from the profile shows the summary to Free and Core, with a Pro upsell on the per-word view.

**Verification:** to be defined in the spec.

---

## TASK-994: User custom tests (10 credits, +30 for an L1 reference set)

**Status:** [?] Blocked — needs a feature spec; the founder must confirm it is in launch scope
**Feature:** billing
**Type:** feature
**Complexity:** XL
**Depends On:** TASK-981

**Description:**
The plan's main credit sink is "custom test from your own topic or word list". **No user-facing
generation route exists.** `services/test_generation/orchestrator.py` runs only from scripts and
the batch pipeline.

A spec has to settle:
- input limits;
- moderation before a test joins the shared catalogue (the amortisation argument depends on it);
- running the pipeline async with progress;
- refunds on fail-closed judging ([[tasklist/test-gen-fail-closed-judging.tasks]]);
- the reference-set add-on.

**Acceptance Criteria:** (to be finalised in the spec)
- [ ] `POST /api/tests/custom` quotes, spends 10 credits (+30 for references), queues generation, refunds on failure, and links `llm_call_ids`.

**Verification:** to be defined in the spec.

---

## TASK-995: Billing UI — pricing page, paywall, credit chips, billing settings

**Status:** [ ] Not Started
**Feature:** billing
**Type:** feature
**Complexity:** L
**Depends On:** TASK-984, TASK-981

**Description:**
Build the front-end pieces in tech spec "Component Specification". There is no billing UI today.

**Acceptance Criteria:**
- [ ] `/pricing` page (route in `web/pages.py`, new template):
  - Core and Pro side by side, monthly and annual;
  - the dividing line stated;
  - currency detected with a manual switch;
  - GST/VAT-inclusive labels;
  - the founding counter;
  - lifetime seats remaining.
  - Prices come from `GET /api/payments/token-packages` (backed by `plan_prices`).
- [ ] A global 402 handler in `window.authFetch` (`static/js/pages/base.js:179`) or `static/js/utils.js:apiRequest` opens `PaywallPanel` with the payload. On a Core `dt_cap`, it leads with Pro.
- [ ] `CreditCostChip` sits beside metered actions (DT over the cap, word import). `ConfirmSpendDialog` opens for 20 credits or more, showing the balance before and after, with nothing pre-ticked.
- [ ] A billing section on `templates/profile.html` / `static/js/pages/profile.js`:
  - the plan and renewal date;
  - one balance with an allowance / owned split;
  - a portal link (cancellation);
  - transaction history.
- [ ] CSP (`web/security.py:10-19`) allows the Stripe Checkout redirect. Checkout is hosted, so no Stripe.js is needed unless TASK-984 keeps PaymentIntents.
- [ ] i18n strings are added to all four locales.
- [ ] Vitest covers the 402 handler and the chip/confirm logic. A Playwright smoke test covers `/pricing` at 390 px and desktop.

**Files to Create / Modify:**
- `templates/pricing.html`, `static/js/pages/pricing.js`, `static/js/components/paywall.js`, `static/js/components/credit-chip.js` — new
- `static/js/pages/base.js` or `static/js/utils.js`, `templates/profile.html`, `static/js/pages/profile.js`, `web/pages.py`, `web/security.py`, the i18n locale files
- `tests/unit/billing-paywall.test.js`, `tests/e2e/pricing.spec.js` — new

**Verification:** `npx vitest run tests/unit/billing-paywall.test.js` and `npx playwright test tests/e2e/pricing.spec.js --trace off`.

---

## TASK-996: Trial and lifecycle emails (21-day Pro trial, no card)

**Status:** [?] Blocked — needs **D17** (age policy). The trial shape is decided (D5).
**Feature:** billing
**Type:** feature
**Complexity:** M
**Depends On:** TASK-980, TASK-986

**Description:**
After placement, start a no-card Pro trial as a `subscriptions` row with `provider='manual'` and
`status='trialing'`, plus a 21-day `current_period_end`. Email 3 days before the end. Re-offer a
14-day trial at day 45 to users who did not convert. Age handling follows D17, with no marketing
email to under-18s.

**Acceptance Criteria:**
- [ ] Placement completion starts the trial once per user, keyed by idempotency.
- [ ] Day-18 reminder and day-45 re-offer jobs are added to `web/scheduler.py` and sent through the existing SMTP path.
- [ ] Trial end → free (or Core/Pro if the user checked out). Allowance credits granted during the trial lapse.
- [ ] Signup stores date of birth (or an age band) per D17, with under-18 defaults applied.

**Verification:** a unit test with frozen time over days 0, 18, 21 and 45.

---

## TASK-997: Staging end-to-end and rollout (LIVE, owner)

**Status:** [ ] Not Started
**Feature:** billing
**Type:** test
**Complexity:** M
**Depends On:** TASK-978 – TASK-990, TASK-995 (and TASK-993/994 if in launch scope)

**Description:**
Run the manual staging check from the tech spec, then turn enforcement on in production. The owner
applies the migrations and flips the flag.

**Acceptance Criteria:**
- [ ] In Stripe test mode, all of these pass with balances and tiers checked at each step:
  - buy a pack;
  - subscribe to Core;
  - upgrade to Pro (prorated allowance once);
  - downgrade at period end;
  - cancel in the portal;
  - refund within 14 days;
  - a failed renewal → `past_due` → downgrade after 7 days.
- [ ] Shadow mode (flag off) runs at least 7 days in production. The `entitlement_shadow_deny` logs are reviewed for false denials.
- [ ] Migrations TASK-978/979 are applied live by the owner. The provisioning script runs with `--live`. The webhook endpoint is registered in the Stripe dashboard with `STRIPE_WEBHOOK_SECRET` set.
- [ ] `ENTITLEMENTS_ENFORCED=true`. After the first nightly run, the reconciliation report shows 0 ledger mismatches.
- [ ] `GET /api/users/tokens` and `grant_daily_free_tokens` are retired (TASK-977 decision).

**Verification:** the checklist above, recorded in `wiki/log.md`.

---

## TASK-998: Re-create organizations for tutors (LIVE-DB, approval)

**Status:** [?] Blocked — G1a gate (month 13) and the `classes-and-assignments` feature spec
**Feature:** billing
**Type:** infra
**Complexity:** M
**Depends On:** TASK-997

**Description:**
Restore `organizations` and `organization_members` from `archive/db_backups/stage1-unused-tables-2026-09-21.zip`.
Add `org_type` (`tutor` first), seats and `left_at`. Re-add the FKs from `users.organization_id` and
`tests.organization_id` after confirming both are all NULL. Recreate `is_org_member` and
`get_org_role`. Add the org source to `get_entitlements` (a tutor-student seat gets the
`tutor_student` tier: DT 10 a day, 20 minutes, 10 new words).

**Acceptance Criteria:** (to be finalised with the spec) the tech spec §7 columns, RLS rules and
entitlement precedence tests.

---

## TASK-999: Tutor billing — base plus per-seat subscription

**Status:** [?] Blocked — after TASK-998
**Feature:** billing
**Type:** feature
**Complexity:** M
**Depends On:** TASK-998, TASK-984

**Description:**
A Stripe subscription with two prices: `tutor_base` (A$39 a month, 10 seats) and `tutor_seat`
(A$3 per extra student, quantity-based). Seat count is synced when students join or leave.
Webhook mapping goes to `owner_org_id`.

---

## TASK-1000: Tutor workspace — invite students, assign tests and word lists, see results

**Status:** [?] Blocked — needs the `classes-and-assignments` feature spec
**Feature:** billing
**Type:** feature
**Complexity:** XL
**Depends On:** TASK-998

**Description:**
The tutor-facing product: join codes, a student list, assigning a test, word list or DT passage
with a due date, and a results view. The same tables (`classes`, `assignments`,
`assignment_results`) later serve schools, so the spec should be written for both.

---

## Founder questions raised by this plan

| # | Question | Why it matters | Default if unanswered |
|---|---|---|---|
| Q1 | Are the knowledge report (TASK-993) and user custom tests (TASK-994) in launch scope? | Without them, Pro differs from Core only by DT volume (25 vs 5 a day) and 300 credits that can only be spent on new-word imports and DT over the cap. Pro at A$14.99 may be hard to sell. | Build the knowledge report (L) before launch. Launch custom tests after, and say so on the pricing page. |
| Q2 | D4: which payment provider handles global consumers? | Decides whether TASK-985 exists and which webhook family is primary. | Launch on Stripe only, with Stripe Tax for AU. Accept registering for EU/UK VAT later, or use Stripe Managed Payments if it is eligible. |
| Q3 | Keep the trainer level cap for Free (TASK-991)? | The trainers aren't levelled products today, so this cap means little to users. | Drop it. Free is already limited by tests and session minutes. |
| Q4 | Refund over-cap DT credits on a *provisional* grade? | A provisional grade is shown but incomplete. | No refund on provisional grades; refund on an error or no band. |
| Q5 | Daily free tokens (`users.tokens`): retire? | They no longer have a purpose under count-based limits. | Retire (TASK-977/997). |
