---
title: LinguaDojo Pricing Plan — Technical Specification
type: overview
status: planned
prose_page: ./pricing-plan.md
last_updated: 2026-11-17
dependencies:
  - "user_tokens, token_transactions (existing; extended)"
  - "dim_subscription_tiers (existing; re-seeded)"
  - "users.subscription_tier_id, users.organization_id, tests.organization_id (existing columns; org FKs dropped 2026-09-22)"
  - "organizations, organization_members (dropped 2026-09-22; to be re-created)"
  - "services/payment_service.py, routes/payments.py, middleware/auth.py (tier_required), routes/tests/submit.py, routes/dual_translation.py"
  - "llm_calls (cost logging; must be fixed for DT)"
  - "Stripe API (PaymentIntents, Checkout, Billing, Invoicing, Tax); merchant of record (Paddle or Stripe Managed Payments, TBD)"
breaking_change_risk: high
open_questions:
  - "ANSWERED 2026-11-17 (D4): **Stripe everywhere** (Stripe Billing + Stripe Tax). No merchant of record. Consequence: the founder registers for tax where required — AU GST, EU VAT via the non-Union OSS scheme and UK VAT from the first consumer sale there; US sales tax only once a state's economic-nexus threshold is reached (Stripe Tax monitors thresholds). Only the Stripe webhook family is built; the MoR webhook route below is not built."
  - "OPEN: Is TASK-875 (revoke client writes on users; drop the users_update_own / users_admin_all policies) applied in production? schema.tech.md says the users table policies still let a user raise their own subscription_tier_id. BLOCKER for billing."
  - "OPEN: What does max_tier='tier1' do when the ADR-044 single-call grader is active? The DT_DAILY_TOKEN_BUDGET guardrail (routes/dual_translation.py:208) degrades rather than blocks, and it was written for the v1 cascade."
  - "OPEN: Can the DT grader route be pinned to zero-data-retention providers on OpenRouter (provider routing flags), and is gpt-6-luna available that way?"
  - "OPEN: Which LMS export formats should the gradebook support at school launch (CSV only, or also Compass, SEQTA or Canvas)?"
  - "OPEN: Where is the school tenant data hosted (Supabase region of project kpfqrjtfxmujzolwsvdq; Railway region)? Needed for the AU-residency statement."
  - "OPEN (D19): If the Core trigger fires (Core > 60% of payers without a 33% conversion uplift), it changes plan_prices (a new price_version for core) or moves entitlement values from core to pro for new subscribers only. Grandfathered Core subscribers then need per-subscription entitlements (see §2, grandfathering note)."
---

# LinguaDojo Pricing Plan — Technical Specification

This page specifies how [[business/pricing-plan]] is implemented on the existing scaffolding. The decision is recorded in [[decisions/ADR-047-credits-and-subscription-model]]. Current schema is in [[database/schema.tech]]. The legacy design is in [[features/token-economy.tech]]. Roles are in [[business-rules/auth-and-access]].

## Architecture Overview

```
                ┌────────────── Billing providers ──────────────┐
                │ MoR (Paddle / Stripe MP, TBD)   Stripe (AU)   │
                │  consumer subs + packs           tutors, packs │
                │                                  school invoices│
                └───────┬───────────────────────────┬───────────┘
                        │ webhooks (signed)         │
                        ▼                           ▼
            /api/billing/mor-webhook     /api/payments/webhook
                        │                           │
                        └──────► billing_events (idempotency) ◄──┘
                                       │
                 ┌─────────────────────┼──────────────────────┐
                 ▼                     ▼                      ▼
          subscriptions        credit ledger RPCs       organizations / seats
       (plan, status,      (grant / spend / refund;       (licence, census,
        price_version)      3 pools; org pool)             pooled credits)
                 │                     │                      │
                 └──────────► get_entitlements(user) ◄────────┘
                                       │
         routes: tests/submit, daily session, prestudy, DT submit,
         word-list import, generate_test, trainers, reports
```

**Principles:**
1. **Webhooks are the only writers of subscription state.** The client never sets a tier. `users.subscription_tier_id` is a denormalised cache that only the webhook and service code write.
2. **One entitlement check.** Every gated route calls `get_entitlements(user_id)` (cached for the request, see [[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]]). The decorator `tier_required` in `middleware/auth.py:364` is kept for admin-only routes but is not used for product gating. Tiers change; entitlement keys do not.
3. **Credits are spent atomically in the database.** Spending happens in an RPC with a row lock and an idempotency key. It is never a read-modify-write in Python. The current `PaymentService.consume_tokens` does read-modify-write and must be retired.
4. **Every credit debit links to its cost.** Each debit stores the `llm_calls` id(s) it paid for, so the actual cost per action can be compared with the credits charged (decision D9).

## Current state (verified 2026-11-17)

| Item | State | Evidence |
|---|---|---|
| Tests charged | **Never.** Every submission is recorded as free. | `routes/tests/submit.py:103` `'p_was_free_test': True` |
| Payment routes | `GET /api/payments/token-packages` and `POST /api/payments/create-intent` only. **No webhook route.** [[features/token-economy.tech]] lists `POST /api/payments/webhook`, which is stale. | `routes/payments.py:18,24` |
| Payment crediting | `PaymentService.handle_successful_payment` exists. It retrieves the intent, reads `metadata.user_id`, `package_id` and `tokens`, and has a duplicate-row idempotency check. Nothing calls it. | `services/payment_service.py:229–` |
| Stripe config | `STRIPE_SECRET_KEY` only. No webhook signing secret, no price IDs. | `config.py:401` |
| Token packs | `config.py` has `starter_10` A$1.99, `popular_50` A$7.99 and `premium_200` A$19.99. Token costs are `take_test=1`, `generate_test=5`, with `DAILY_FREE_TOKENS=2`. These conflict with the DB tier seed. | `config.py:377–395` |
| Tier seed (prod) | Free: 1 free test a day, 10 tokens per test. Premium: 3 a day, 100 tokens a month, 8 per test. Enterprise: 10 a day, 500 a month, 5 per test. Admin. [[business-rules/auth-and-access]] says Free = 2 a day, which is a contradiction. | cost research, prod SELECT |
| Tier gating | `tier_required` exists and is used by no product route. | `middleware/auth.py:364` |
| Orgs | `organizations` and `organization_members` were dropped on 2026-09-22. `is_org_member` and `get_org_role` were also dropped. The columns `users.organization_id` and `tests.organization_id` **remain, without FKs**. | `migrations/archive_unused_modules_2026_09_21.sql:58–64` |
| DT guardrail | `DT_DAILY_TOKEN_BUDGET=20000` tokens a day. At or over budget, the cascade is called with `max_tier='tier1'`; it does not block. At about 2–3k tokens per ADR-044 call, it trips after about 7–10 submissions. | `config.py:159`, `routes/dual_translation.py:208,786` |
| DT cost logging | Production `llm_calls` rows for `dt_single_call_grade` have NULL `cost_usd` and 0 tokens. Most calls went to `:free` models. | cost research |
| Client writes | `user_tokens` and `token_transactions` have client writes revoked (TASK-875). The `users` table update policies may still allow a user to change `subscription_tier_id`. | [[database/schema.tech]] §2, security posture |

## Database Impact

All changes are additive migrations except the re-seed of `dim_subscription_tiers`. The existing table names (`user_tokens`, `token_transactions`) are kept to avoid breaking callers. The UI calls them "credits".

### 1. `dim_subscription_tiers`: re-seed

**Rows (`tier_code`):**

| Group | Tier codes |
|---|---|
| Solo | `free`, `core`, `pro`, `pro_lifetime`, `professional`, `exam_pass` |
| Schools and tutors | `school_student`, `teacher_free`, `teacher_class`, `teacher_dept`, `tutor` |
| Staff | `admin` |

**Changes to existing tiers:**
- Mark the legacy `premium` and `enterprise` rows `is_active=false`. They have no users; verify before migrating.

**Columns:**

| Column | Change |
|---|---|
| `daily_free_tests` | Keep. 1 for `free`. No cap (NULL meaning unlimited) for paid tiers, `core` included. **This needs a column-semantics change:** the column is `NOT NULL CHECK >= 0`, so either use a large sentinel or move the value into `tier_entitlements`. Recommended: move it. |
| `monthly_token_grant` | Keep it as the monthly credit allowance. Values: 0 `core`, 300 `pro`, 150 `pro_lifetime`, 600 `professional`, 0 elsewhere. |
| `tokens_per_test` | Set to 0 on every row, then deprecate. Drop it in a later migration once `get_test_token_cost` has no callers. |
| `can_generate_tests`, `can_create_custom_tests`, `max_custom_tests`, `can_access_analytics` | Superseded by `tier_entitlements`. Keep them readable and stop writing them. |
| `allowance_rollover_cap` (new) | `integer NOT NULL DEFAULT 0`. 0 for `core` (no allowance), 300 for `pro`, 600 for `professional`, 0 for `pro_lifetime`. The maximum balance is grant + cap. |

### 2. New `tier_entitlements`

| Column | Type | Notes |
|---|---|---|
| `tier_id` | smallint | FK → `dim_subscription_tiers.id` |
| `entitlement_key` | text | See the key list below |
| `int_limit` | integer NULL | NULL = unlimited |
| `enabled` | boolean NOT NULL DEFAULT true | |
| PK | (`tier_id`, `entitlement_key`) | |

**Entitlement keys and launch values:**

| key | free | core | pro / pro_lifetime | professional | school_student | tutor seat (student) |
|---|---|---|---|---|---|---|
| `tests_new_per_day` | 1 (2 for grandfathered users, via `user_entitlement_overrides`) | NULL | NULL | NULL | NULL | NULL (assigned and matched) |
| `session_minutes_per_day` | 10 | NULL | NULL | NULL | NULL | 20 |
| `new_words_per_day` | 5 | NULL | NULL | NULL | NULL | 10 |
| `prestudy_per_week` | 1 | NULL | NULL | NULL | NULL | 3 |
| `dt_free_per_week` | 5 | — | — | — | — | — |
| `dt_per_day` | — | **5** | 25 | 40 | 20 | 10 |
| `dt_tokens_per_day` | 20000 | 20000 | 75000 | 120000 | 60000 | 30000 |
| `word_import_dictionary` | false | true | true | true | via teacher | via tutor |
| `trainer_level_max` | 2 | NULL | NULL | NULL | NULL | NULL |
| `bkt_report_detail` | `summary` (stored as 0) | **`summary` (0)** | full (1) | full | full | full |
| `domain_packs` | false | false | false | true | false | false |
| `pd_log_export` | false | false | false | true | false | false |
| `custom_test_generation` | true (credits) | true (credits; purchased only, no allowance) | true (credits) | true (credits) | false | false |

- **Core vs Pro differ in exactly three places:** `dt_per_day` (5 vs 25), `bkt_report_detail` (summary vs full) and `monthly_token_grant` (0 vs 300, on `dim_subscription_tiers`). Keep it that way so the D19 trigger can move a feature by changing one value.
- `dt_tokens_per_day` for `core` is set to the free tier's 20000 rather than 5 × 3,000 = 15000, so the backstop never bites before the count cap does (5 grades at up to 4k tokens each).
- **Grandfathering under D19.** If a Core feature is later moved up to Pro, existing Core subscribers keep it. Implement this as a new tier row (`core_v2`) for new subscribers, not by editing the `core` row, so `subscriptions.price_version` and the tier both identify what a subscriber bought.

**New `user_entitlement_overrides`** (`user_id`, `entitlement_key`, `int_limit`, `enabled`, `reason`, `expires_at`). Uses: grandfathering the 18 existing users (`tests_new_per_day=2`), goodwill grants and trials. (The 7-day Study Pass, which also used overrides, was retired on 2026-11-17.)

### 3. New `plan_prices` (single source of truth for prices)

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `plan_code` | text | `core`, `pro`, `pro_founding`, `pro_student`, `pro_lifetime`, `professional`, `professional_launch`, `exam_pass`, `pack_500`, `pack_1100`, `pack_2500`, `tutor_base`, `tutor_seat`, `school_class`, `school_dept_seat`, `school_senior_seat`, `org_pool_5000` |
| `currency` | char(3) | `USD`, `AUD`, `EUR`, `GBP` |
| `interval` | text | `month`, `year`, `one_time`, `seat_year` |
| `amount_minor` | integer | Tax-inclusive for consumer plans. Ex-GST for `school_*` and `org_pool_*`. |
| `tax_inclusive` | boolean | |
| `credits` | integer NULL | For packs (500 / 1,100 / 2,500) and `exam_pass` (1,000) |
| `price_version` | integer | Bumped on every price change. Existing subscribers keep theirs. |
| `provider` | text | `stripe` or `mor` |
| `provider_price_id` | text | Stripe `price_…` or the MoR price id. Set when provisioned. |
| `active` | boolean | |
| UNIQUE | (`plan_code`, `currency`, `interval`, `price_version`) | |

`config.TOKEN_PACKAGES` and `PaymentService.TOKEN_PACKAGES` are removed. `GET /api/payments/token-packages` reads `plan_prices` instead.

**Launch seed for solo subscriptions (`price_version = 1`, prices decided 2026-11-17).** Amounts are in minor units and tax-inclusive. The earlier single-tier draft (Pro US$12 / US$99, A$17.99 / A$149) was never provisioned, so it has no `price_version`.

| `plan_code` | `interval` | USD | AUD | EUR | GBP |
|---|---|---|---|---|---|
| `core` | `month` | 600 | 899 | 599 | 499 |
| `core` | `year` | 4900 | 7500 | 4900 | 4200 |
| `pro` | `month` | 1000 | 1499 | 999 | 849 |
| `pro` | `year` | 8900 | 12900 | 8900 | 7500 |
| `pro_founding` | `year` | 6900 | 9900 | — | — |
| `pro_student` | `year` | 5900 | 8900 | — | — |
| `pro_lifetime` | `one_time` | 29900 | 44900 | — | — |

- EUR and GBP amounts are derived, not founder-set; confirm them before provisioning.
- Founding, student and lifetime are sold in USD and AUD only at launch (unchanged from the earlier draft).

### 4. New `subscriptions`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `owner_user_id` | uuid NULL | FK `users`. Set this or `owner_org_id`, never both (CHECK). |
| `owner_org_id` | uuid NULL | FK `organizations` |
| `plan_code` | text | |
| `price_version` | integer | |
| `provider` | text | `stripe`, `mor` or `manual` (school invoices paid by bank transfer) |
| `provider_customer_id` | text | |
| `provider_subscription_id` | text UNIQUE NULL | |
| `status` | text | `trialing`, `active`, `past_due`, `canceled`, `expired`, `lifetime` |
| `current_period_start` | timestamptz | |
| `current_period_end` | timestamptz | |
| `cancel_at` | timestamptz NULL | |
| `is_founding` | boolean DEFAULT false | Locked rate while the subscription is continuous |
| `seats` | integer NULL | Org plans |
| `created_at`, `updated_at` | timestamptz | |

**The user's effective tier** is the highest active entitlement among:
- their own subscription;
- an active org seat (a `school_student` or tutor-student membership in an org with an active subscription);
- an override;
- otherwise `free`.

`users.subscription_tier_id` is updated by the webhook handler as a cache.

### 5. Credit ledger: `user_tokens` (extended)

**New columns:**

| Column | Type | Meaning |
|---|---|---|
| `allowance_tokens` | integer NOT NULL DEFAULT 0, CHECK >= 0 | Allowance pool |
| `allowance_period_end` | timestamptz NULL | When the allowance next resets |
| `purchased_tokens` | existing | Purchased pool. Never expires. |
| `bonus_tokens` | existing | Bonus pool. Kept as a cached sum of unexpired `credit_grants` rows. |

**New `credit_grants` table.** It tracks expiry for each bonus grant.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | |
| `user_id` | uuid NULL | Set this or `org_id` |
| `org_id` | uuid NULL | |
| `pool` | text | `bonus` |
| `amount` | integer | |
| `remaining` | integer | |
| `reason` | text | |
| `expires_at` | timestamptz | |
| `created_at` | timestamptz | |

**Spend order is allowance, then bonus (oldest expiring first), then purchased.**

### 6. `token_transactions` (extended)

| New column | Type | Notes |
|---|---|---|
| `pool` | text | `allowance`, `bonus`, `purchased` or `org`. One row per pool touched. |
| `org_id` | uuid NULL | Debits against the org pool |
| `idempotency_key` | text | UNIQUE (`user_id`, `idempotency_key`) |
| `llm_call_ids` | bigint[] NULL | Links the debit to `llm_calls` rows (type to match the `llm_calls` PK; verify) |
| `actual_cost_usd` | numeric(10,6) NULL | Filled after the call completes |
| `provider_event_id` | text NULL | The webhook event that caused a credit |

**New `action` values:**
- **Spends:** `dt_grade_overcap`, `custom_test`, `ref_set`, `sense_import`, `deep_regrade`, `mock_grade`. (`study_pass` is not added: the pass was retired before launch.)
- **Grants and adjustments:** `allowance_grant`, `allowance_expire`, `bonus_grant`, `bonus_expire`, `purchase`, `refund`, `chargeback`, `legacy_conversion`.
- **Legacy:** keep `take_test` and `generate_test` for history only.

### 7. Organizations (re-create for G1a/G1)

**Starting point.** Restore the shape from `archive/db_backups/stage1-unused-tables-2026-09-21.zip`, then re-add the FKs from `users.organization_id` and `tests.organization_id`. First run `SELECT count(*) … WHERE organization_id IS NOT NULL` on both tables; the expected result is 0.

**New columns on `organizations`:**

| Column | Purpose |
|---|---|
| `org_type` | `school`, `tutor` or `community_school` |
| `abn` | |
| `invoice_email` | |
| `po_number` | |
| `seat_limit` | |
| `census_count` | |
| `census_date` | |
| `licence_start` | |
| `licence_end` | |
| `token_pool` | Pooled credits, CHECK >= 0 |
| `state` | `VIC`, `NSW`, `QLD`, `SA`, `WA`, `TAS`, `ACT` or `NT` |
| `sector` | `government`, `catholic` or `independent` |

**`organization_members`** columns are `organization_id`, `user_id`, `role` (`student`, `teacher`, `admin` or `owner`) and `joined_at`. Add `left_at` so a seat is freed without losing the student's history.

**Recreate the functions:** `is_org_member(user_id, org_id)` and `get_org_role(user_id, org_id)`.

**Later (school build):**
- `classes` (id, org_id, name, year_level, language_id, join_code UNIQUE)
- `class_members`
- `assignments` (id, class_id, kind (`test`, `word_list`, `dt_passage`), ref_id, due_at)
- `assignment_results`

These are specified in a future `features/classes-and-assignments` page, which does not exist yet.

**RLS:**
- Teachers read results only for members of their own classes.
- Students read only their own results.
- Org admins manage members.
- A student can never see the org pool balance.

### 8. Billing idempotency: new `billing_events`

| Column | Notes |
|---|---|
| `provider` | |
| `event_id` | UNIQUE (`provider`, `event_id`) |
| `type` | |
| `payload` | jsonb |
| `received_at` | |
| `processed_at` | |
| `error` | |

**Handling rules:**
1. Insert the event first. A duplicate returns 200 at once.
2. Process the event.
3. Set `processed_at`.

## API / RPC Surface

### RPCs (SECURITY DEFINER; callable by `service_role` only unless stated)

#### `get_entitlements(p_user_id uuid): jsonb`
- **Purpose:** Return the user's effective tier and entitlement map.
- **Returns:** `{tier_code, source: 'own'|'org'|'override'|'free', limits: {key: int|null}, flags: {key: bool}, credits: {allowance, bonus, purchased, total, allowance_period_end}}`
- **Auth:** the user may call it for themselves (`auth.uid() = p_user_id`). Admins may call it for anyone.
- **Errors:** `user_not_found`.
- **Side effects:** none.

#### `spend_credits(p_user_id uuid, p_amount int, p_action text, p_idempotency_key text, p_test_id uuid default null, p_org_id uuid default null): jsonb`
- **Purpose:** Debit credits atomically.
  - With `p_org_id`, it debits the org pool.
  - Otherwise it debits allowance, then bonus, then purchased.
- **Returns:** `{ok: true, spent_by_pool: {...}, balance_after}` or `{ok: false, error: 'insufficient_credits', balance}`.
- **Errors:** `insufficient_credits`, `invalid_amount` (≤0), `org_not_member`, `duplicate` (returns the original result; not an error to the caller).
- **Auth:** service code only. Routes call it after `get_entitlements`.
- **Side effects:**
  - Locks the `user_tokens` row with `SELECT … FOR UPDATE`.
  - Writes one `token_transactions` row per pool touched.

#### `refund_credits(p_transaction_group_key text, p_reason text): jsonb`
- **Purpose:** Reverse a spend into the same pools it came from.
- **Called when:** an LLM call fails, a generation fails, or support issues a goodwill refund.
- **Bonus pool:** credits go back to the original grant, or a new 12-month grant if that one has expired.

#### `grant_credits(p_user_id uuid, p_amount int, p_pool text, p_reason text, p_idempotency_key text, p_expires_at timestamptz default null): jsonb`
- **Purpose:** Add credits, as purchased (packs), bonus or allowance.
- **Replaces** `add_tokens_atomic` for new code. Keep the old RPC until callers move.
- **Packs:** `process_stripe_payment` is re-implemented as a thin wrapper over `grant_credits(..., 'purchased', ...)`.

#### `reset_allowance(p_user_id uuid, p_period_end timestamptz): jsonb`
- **Purpose:** Called on `invoice.paid` (monthly) or monthly from the scheduler (annual and lifetime). A no-op for tiers whose `monthly_token_grant` is 0 (`core`, `free`), apart from zeroing any leftover allowance after a Pro → Core downgrade.
- **Calculation:** new allowance = min(remaining + grant, grant + rollover_cap).
- **Logs** `allowance_expire` for the excess and `allowance_grant` for the new grant.
- **Idempotency key:** `allowance:<user>:<period_end>`.

#### `expire_bonus_credits(): int`
- **Purpose:** Nightly APScheduler job. Expires `credit_grants` rows past `expires_at` and logs `bonus_expire`.

#### Retire
- `get_test_token_cost`: return 0, then drop once there are no callers.
- `PaymentService.consume_tokens`, `can_perform_action` and `_award_daily_free_tokens`: replace with the entitlement and ledger calls above.
- Keep `get_daily_free_test_limit`, re-implemented as a read of `tests_new_per_day`.

### HTTP routes

**Billing and credits:**

| Route | Purpose | Auth |
|---|---|---|
| `POST /api/payments/webhook` | Stripe webhook. Verifies the `Stripe-Signature` header against new config `STRIPE_WEBHOOK_SECRET`; returns 400 if it fails. Records the event in `billing_events`, then dispatches it (see the event table). | Stripe signature only (no JWT) |
| `POST /api/billing/mor-webhook` | MoR webhook (Paddle: `Paddle-Signature`, HMAC; verify the scheme for the provider chosen) | Signature only |
| `POST /api/billing/checkout` | Body `{plan_code, currency}`. Creates a Stripe Checkout Session or MoR checkout for the `plan_prices` row. Sets `client_reference_id`/metadata to `user_id` and `price_version`. Returns `{url}`. | `jwt_required` |
| `GET /api/billing/portal` | Stripe Billing Portal session URL, or the MoR customer portal. This is the one-click cancellation path (unfair trading practices law, 1 Jul 2027). | `jwt_required` |
| `GET /api/billing/entitlements` | Proxies `get_entitlements` for the UI | `jwt_required` |
| `POST /api/credits/quote` | Body `{action, params}`. Returns `{credits, requires_confirm: credits >= 20}`. The UI shows this before every metered action. | `jwt_required` |
| `POST /api/payments/create-intent` | Kept for packs on Stripe. Change it to read `plan_prices` and write `metadata.user_id`, `plan_code`, `credits` and `price_version`. | `jwt_required` |

**Orgs:**

| Route | Purpose | Auth |
|---|---|---|
| `POST /api/orgs` | Create an org | `jwt_required`, then the creator becomes owner |
| `POST /api/orgs/{id}/quote` | Create the quote PDF | owner or admin |
| `POST /api/orgs/{id}/members/join` | Join with a class code | `jwt_required` |
| `GET /api/orgs/{id}/seats` | Seat usage | owner or admin |

### Stripe / MoR event handling

| Event | Action |
|---|---|
| `checkout.session.completed` (mode `subscription`) | Upsert `subscriptions` (status from the subscription object). Set the user tier cache. If the plan has an allowance, call `reset_allowance`. |
| `checkout.session.completed` (mode `payment`) / `payment_intent.succeeded` | Pack: `grant_credits(purchased)`. Exam Pass: apply `exam_pass` (90 days + 1,000 purchased credits). Use `payment_intent.id` as the idempotency key. Lifetime: create a `subscriptions` row with `status='lifetime'`. |
| `customer.subscription.updated` | Sync status, period, `cancel_at` and plan changes. Upgrades are prorated by the provider. A downgrade applies at period end. **Core → Pro upgrade:** grant the allowance prorated to the share of the period left, `floor(300 × days_left / days_in_period)`, with idempotency key `allowance_upgrade:<subscription>:<period_end>`; the full 300 comes with the next `invoice.paid`. **Pro → Core at period end:** zero the allowance (log `allowance_expire`); keep bonus and purchased credits. |
| `customer.subscription.deleted` | Set `status=canceled`. Zero the allowance (log `allowance_expire`). Keep purchased and bonus credits. Tier cache → `free`. |
| `invoice.paid` | Extend the period. Reset the allowance (monthly). For school invoices with `provider='manual'`, ops marks them paid in the admin UI, which applies the same transition. |
| `invoice.payment_failed` | `status=past_due`. Entitlements are kept for a 7-day grace period (dunning e-mails come from the provider), then downgrade to free. |
| `charge.refunded` | Pack: `spend_credits`/claw back the unused purchased credits, up to the balance. Log `refund`. Subscription refund (14-day policy): cancel immediately. |
| `charge.dispute.created` | Freeze spend on purchased credits. Alert the admin. |
| `invoice.finalized` / `invoice.sent` (Stripe Invoicing, schools) | Record the invoice id on the org. No entitlement change until it is paid, unless the org is in its pilot or grace window. |
| Paddle equivalents | `transaction.completed`, `subscription.created`, `subscription.updated`, `subscription.canceled`, `adjustment.created` (refunds). **Verify the names against Paddle's docs before G0.** |

**Stripe objects to provision (one per `plan_prices` row):**
- **Products:** Core, Pro, Pro Lifetime, Professional, Exam Pass, Credit Pack 500/1,100/2,500, Tutor, School Class, School Department seat, Senior add-on seat, Org Credit Pool 5,000. **No Study Pass product** (retired 2026-11-17).
- **Prices:** use `lookup_key = <plan_code>_<currency>_<interval>_v<price_version>`. Solo subscriptions at launch: `core_<USD|AUD|EUR|GBP>_<month|year>_v1` and `pro_<USD|AUD|EUR|GBP>_<month|year>_v1` (8 prices each; amounts in the `plan_prices` launch seed above), plus `pro_founding_<USD|AUD>_year_v1`, `pro_student_<USD|AUD>_year_v1` and `pro_lifetime_<USD|AUD>_one_time_v1`.
- **Core and Pro are separate Products** (not two prices on one product), so the Billing Portal can offer Core ↔ Pro switches as plan changes with proration.
- **Stripe Tax:** turn on for AU GST on Stripe-billed consumer and tutor sales if Stripe is used rather than an MoR.
- **School invoices:** quantity = seats. Use invoice custom fields for the PO number and ABN.

### Entitlement checks per route

| Route / feature | Check | On deny |
|---|---|---|
| Test start or submit (`routes/tests/submit.py`) | The test is new for the user today and `tests_new_per_day` is reached → deny. Remove `'p_was_free_test': True`. Pass `p_was_free_test = (tier == 'free')` for analytics only. | 402 `{error: 'daily_test_limit', upgrade: true}` |
| Daily session build ([[features/session-modules]], [[decisions/ADR-043-one-call-daily-session]]) | Clamp the budget to `session_minutes_per_day` and the new-word quota to `new_words_per_day` | Clamp silently; show an upsell banner |
| Prestudy start ([[features/test-prestudy]]) | Count this week's prestudy sessions against `prestudy_per_week` | 402 |
| DT submit (`routes/dual_translation.py`) | Free: count this week's submissions against `dt_free_per_week`. Paid: count today's against `dt_per_day` (5 Core, 25 Pro, 40 Professional, 20 school student, 10 tutor seat). Over → `spend_credits(1, 'dt_grade_overcap')`, or 402 if the balance is short. Keep the token guardrail as a **cost backstop**: compare against `dt_tokens_per_day` instead of the global `Config.DT_DAILY_TOKEN_BUDGET`. | 402 `{error: 'dt_cap', credits_required: 1}` |
| Deep re-grade | `spend_credits(8, 'deep_regrade')` before calling the v2 grader. Refund on failure. | 402 |
| Custom test (`generate_test`) | `custom_test_generation`, then `spend_credits(10)`, plus 30 if references are requested. Refund on pipeline failure. | 402 / 403 |
| Word-list import ([[tasklist/word-list-import.plan]]) | `word_import_dictionary` for dictionary words. Each sense not yet in the dictionary costs `spend_credits(8, 'sense_import')`. The existing `batch_limits` daily caps stay. | 402 / 403 |
| Trainers (pinyin, pitch accent, measure words) | `trainer_level_max` | Lock the higher levels in the UI |
| Knowledge reports | `bkt_report_detail` (summary for `free` and `core`; full for `pro` and above) | Show the summary only, with a Pro upsell on the per-word view |
| Credit allowance | `monthly_token_grant` on the tier (0 Core, 300 Pro, 150 Lifetime, 600 Professional) | Core users see only purchased and bonus credits; credit actions quote the cost and offer a pack or Pro |
| Professional features | `domain_packs`, `pd_log_export` | 403 |

**Error code.** 402 Payment Required is used only for "credits or plan needed", so the client can show one paywall component.

## Component Specification (UI)

### `CreditCostChip`
- **Purpose:** shows "N credits" next to every metered action.
- **Props:**
  - `action: string`
  - `params: object`
- **Data:** `POST /api/credits/quote`, cached for each action and params.

### `ConfirmSpendDialog`
- **When it opens:** for any action costing 20 credits or more.
- **Content:**
  - the balance before and after the spend;
  - no pre-ticked options.

### `PaywallPanel`
- **Input:** the 402 payload.
- **What it offers:** Core or Pro (a Pro trial if eligible), or a credit pack. On a `dt_cap` 402 from a Core user, lead with Pro (25 a day). Prices come from `GET /api/payments/token-packages` (now backed by `plan_prices`).

### `BillingSettings`
- **Shows:**
  - the plan;
  - the renewal date;
  - one balance, with an allowance / owned split;
  - a link to the portal for cancellation;
  - the transaction history from `get_user_transaction_history`.

### Pricing page
- **Content:**
  - Core and Pro side by side, monthly and annual, with the dividing line stated (Core = study loop; Pro = + translation volume and personal content);
  - prices by currency (detected, with a manual switch);
  - GST/VAT-inclusive labels;
  - the founding counter;
  - the lifetime seats remaining.

## Key Architectural Decisions

1. **Decision: entitlement keys in a table, not tier booleans in code.**
   - **Rationale:** Tiers will change (Core was added on 2026-11-17; Professional, PPP, school variants and the D19 trigger may follow). Routes depend on stable keys. This also gives overrides for grandfathering and passes.
   - **Alternatives rejected:**
     - `tier_required([...])` on routes. Brittle: every new tier means editing routes.
     - More boolean columns on `dim_subscription_tiers`. These do not scale.
2. **Decision: keep the `user_tokens` / `token_transactions` names and extend them.**
   - **Rationale:** Avoids breaking existing RPCs and history. The UI label "credits" is cosmetic.
   - **Alternatives rejected:** a new `credit_*` schema. It needs a backfill and dual-write period for 18 users' worth of value, so it is not worth it.
3. **Decision: webhook-driven state with a `billing_events` idempotency table.**
   - **Rationale:** Providers retry, so duplicate delivery must be harmless. The existing duplicate check is a read-then-write race (see [[features/token-economy.tech]]).
   - **Alternatives rejected:** client-side success callbacks. These can be forged and are lost if the tab closes.
4. **Decision: the DT fair-use cap is count-based; the token budget becomes a per-tier backstop.**
   - **Rationale:** At 2–3k tokens per grade, a 20k-token budget cannot deliver an advertised 25 a day. Learners understand counts, not tokens.
   - **Alternatives rejected:** advertising a token budget.
5. **Decision (superseded 2026-11-17 by D4 = Stripe everywhere): a single merchant of record for global consumers, and Stripe for AU B2B.** Kept for the record; `POST /api/billing/mor-webhook` and `provider='mor'` are not built.
   - **Rationale:** EU/UK VAT applies from the first sale to consumers in those markets. An MoR removes the registrations. AU schools need ABN tax invoices and bank transfer.
   - **Alternatives rejected:** Stripe + Stripe Tax everywhere. That means the founder registers for VAT in the EU and UK.

## Security Considerations
- **Blocker before G0.** Confirm that clients cannot write `users.subscription_tier_id` (TASK-875 status). Otherwise a user can grant themselves Pro.
- **Webhook signatures.**
  - Verify the signature on every webhook, with a 5-minute timestamp tolerance (Stripe default).
  - Reject unsigned requests.
  - Never trust `metadata.tokens`. Look up credits from `plan_prices` by `plan_code` + `price_version`.
- **Who calls the credit RPCs.**
  - `spend_credits` and `grant_credits` are not callable by `anon` or `authenticated`. Service code calls them after authenticating the user.
  - `ADR-014` batch-service tokens must not be honoured on billing routes.
- **Rate limits.**
  - Limit `/api/credits/quote` and `/api/billing/checkout` per user.
  - Card-testing defence: rely on the provider's Radar or equivalent.
- **Privacy.**
  - Store no card data; use only provider-hosted checkout.
  - Grade DT on zero-data-retention providers only.
  - Record the processor list in the privacy policy (APP 8).
  - School tenant data is hosted in an AU region before the first school is signed (open question).
- **Minors.** Accounts aged 13–15 get the under-18 defaults (no marketing, minimal analytics). Org members under 18 are created by teachers via class codes and are never offered consumer checkout.

## Testing Strategy

### Unit tests
- **`spend_credits`:**
  - the spend order across pools;
  - an insufficient balance;
  - a duplicate idempotency key returns the first result;
  - concurrent spends (two transactions) never go negative.
- **`reset_allowance`:** the rollover cap (300 + 300 left → 600; 300 + 450 left → 600, logging 150 expired). For `core` it grants nothing.
- **Core vs Pro entitlements:** a Core user's 6th DT grade of the day costs 1 credit (Pro: the 26th); a Core user gets the summary report only.
- **Plan changes:** Core → Pro mid-period grants the prorated allowance once (replaying the webhook grants nothing more); Pro → Core at period end zeroes the allowance and keeps purchased credits.
- **`get_entitlements`:** precedence across own subscription, org seat, override and free.

### Webhook tests
- Replay fixtures from the Stripe CLI (`stripe trigger …`) for every event in the table.
- Deliver each twice and assert a single effect.
- Out-of-order delivery: `updated` arrives before `created`.

### Route tests
- Each gated route returns 402 or a clamp at the limit and passes when under it.
- A failed DT grade refunds its credit.
- Test submit no longer hardcodes free.

### Reconciliation (nightly)
- The sum of `token_transactions` per user must equal the `user_tokens` pools.
- `llm_calls.cost_usd` linked through `llm_call_ids`, compared with the credits charged by action. This report drives the D9 re-price.

### Manual check (staging)
1. Buy a pack in Stripe test mode.
2. Subscribe and cancel through the portal.
3. Refund within 14 days.
4. Confirm the balances and tiers at each step.

## Migration and rollout order
1. TASK-875 verification. Add `billing_events`, `plan_prices`, `subscriptions` and `tier_entitlements`, and re-seed the tiers.
2. Ledger columns and RPCs. Convert legacy balances 1:1 into `purchased_tokens` (`legacy_conversion`). Add grandfather overrides for the existing users.
3. Webhook route, checkout and portal.
4. Entitlement checks route by route, behind config flag `ENTITLEMENTS_ENFORCED`. This follows the ADR-013 rollout pattern.
5. Pricing page and paywall UI.
6. **Later (G1a/G1):** re-create organizations, then add classes, assignments and invoicing.

## Related Pages
- [[business/pricing-plan]] — Prose counterpart
- [[business/business-case]] — Why these prices
- [[decisions/ADR-047-credits-and-subscription-model]] — Decision record
- [[database/schema.tech]] — Current schema
- [[features/token-economy.tech]] — Legacy design (partly stale: lists a webhook route that does not exist)
- [[business-rules/auth-and-access]] — Roles (the Free = 2 tests a day row conflicts with the production seed)
- [[decisions/ADR-044-dt-single-call-generative-grader]] — DT cost basis
- [[decisions/ADR-014-batch-service-credential]] — Batch token scope
