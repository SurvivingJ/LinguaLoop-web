---
title: "ADR-047: Hybrid subscription + credits monetisation model"
status: proposed
date: 2026-11-17
---

# ADR-047: Hybrid subscription + credits monetisation model

## Context

**What the founder asked for.** LinguaDojo is bootstrapped. The founder asked for two monetisation mechanisms: a pay-as-you-go credits system and a subscription. Deciding what credits pay for was left to us.

**The scaffolding today** ([[features/token-economy]], [[business/pricing-plan.tech]]):
- It is a token economy in which taking a test costs 1 token and generating one costs 5. It is not live: `routes/tests/submit.py` hardcodes `p_was_free_test=True`.
- There is a Stripe PaymentIntent route but no webhook.
- The tier seed conflicts with `config.py`.
- `tier_required` exists but no route uses it.
- The `organizations` tables were dropped on 2026-09-22.

**What things cost.** These figures come from the measured cost research summarised in [[business/market-research]] §1.
- Serving pre-generated content costs A$0 per use: tests, Vocab Dojo, FSRS, BKT, sessions and audio.
- Live-LLM actions have a real but small marginal cost:
  - custom tests: A$0.02–0.23
  - importing a word not yet in the dictionary: A$0.015–0.075
  - a DT grade: about A$0.0003
  - a v2 deep re-grade: A$0.04–0.07
- The largest per-transaction cost is the A$0.30 card fee.

**What the market does.** In-category and AI vendors are converging on a subscription with a credit allowance plus top-ups (Mandarin Temple, ElevenLabs, LingQ Premium Plus). Users complain about credits that expire, opaque burn and auto-recharge.

## Decision

1. **The subscription (Pro) carries the whole study loop.** Credits never meter consuming pre-generated content: taking tests, the ladder, flashcards, sessions, prestudy, trainers, reports and audio.
2. **Credits meter only actions that make a live LLM call at the moment of use.**

   | Action | Credits |
   |---|---|
   | Custom test | 10 |
   | L1 reference set | +30 |
   | Importing a word sense not yet in the dictionary | 8 |
   | DT beyond the fair-use cap | 1 |
   | Deep re-grade | 8 |
   | Mock-passage grading | 25 |

3. **DT is included under a count-based daily fair-use cap**, not metered per use:
   - Pro: 25 a day
   - Professional: 40 a day
   - school student: 20 a day
   - Free: 5 a week

   The existing token guardrail becomes a per-tier cost backstop.
4. **The PAYG route for non-subscribers into the core loop is a 7-day Study Pass**, sold for US$6.99 / A$9.99 or 500 credits. Per-test pricing is not used.
5. **Credit pools.**

   | Pool | Expiry rule |
   |---|---|
   | Allowance (Pro 300 a month; Professional 600) | Rolls over, capped at 1× |
   | Bonus | Expires after 12 months |
   | Purchased | Never expires |

   - Spend order is allowance, then bonus, then purchased.
   - The cost is shown before every action.
   - Actions of 20 credits or more need a confirmation.
   - A failed action refunds its credits automatically.
   - Auto top-up is opt-in only.
   - Credits are not transferable.
6. **Organisations (schools and tutors) hold a pooled credit balance** that teachers control. Students never see credits.
7. **The legacy `take_test` token cost is retired.** `tokens_per_test` is set to 0. Existing token balances convert 1:1 into purchased credits.

Prices, tiers and policies are in [[business/pricing-plan]]. The schema and Stripe mapping are in [[business/pricing-plan.tech]].

## Consequences

**Easier:**
- One clear promise: "your study loop is never metered".
- Credits track real cost, so heavy custom generation pays for itself.
- Everything a learner generates becomes shared content, which further amortises its cost.
- Pricing pages and support become simpler than with per-test tokens.

**Harder:**
- A real credit ledger is needed: atomic multi-pool spends, idempotency, refunds and reconciliation against `llm_calls` costs.
- `llm_calls` cost logging for DT must be fixed before the D9 re-price.
- Purchased credits that never expire are a deferred-revenue liability. It is small at modelled volumes.

**Constrained:**
- The free tier cannot be widened by giving away credits for tests. Free limits are entitlements (counts), not credits.
- Any future feature that adds a live LLM call per use must either declare a credit price or fit under a fair-use cap.
- Any future per-test charge would reverse this ADR.

**Risk accepted:**
- On the 2,500-credit pack spent entirely on the costliest new-word imports, margin falls to about 11%. Every later learner reuses those senses.

## Alternatives Considered

**A. Keep per-test tokens (the current design).** Rejected.
- It meters zero-cost actions and so recovers no cost.
- It puts a counter on the core loop that serious learners resent.
- At small charge sizes the A$0.30 card fee takes about 12%.

**B. Subscription only (no credits).** Rejected.
- It breaks the founder's PAYG requirement.
- It leaves custom generation and imports either unprofitable at heavy use or unavailable.

**C. Credits only (no subscription).** Rejected.
- Recurring revenue is what lets a bootstrapped business plan.
- The research shows credit-only consumer products draw the most complaints about burn rate and expiry.

**D. Meter DT per submission.** Rejected.
- A grade costs about A$0.0003, so metering it would cost more in friction than it recovers.
- Competitors (LingQ Premium Plus, Langua) use caps.

**E. Purchased credits expire after 12 or 24 months of inactivity.** Rejected.
- Forfeiting purchased value risks being an unfair term in a standard-form consumer contract.
- Expiry is also the single most common credit complaint.

## Related
- [[business/business-case]]
- [[business/pricing-plan]]
- [[business/pricing-plan.tech]]
- [[business/market-research]]
- [[features/token-economy]]
- [[decisions/ADR-044-dt-single-call-generative-grader]]
