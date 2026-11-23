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

**Founder pricing decisions (2026-11-17).** The first draft of this ADR had one paid solo tier (Pro, US$12 / US$99, A$17.99 / A$149) plus a 7-day Study Pass. The founder then decided on two solo tiers (Core and Pro) at lower prices, retired the Study Pass, and confirmed tutors as the first B2B buyers. This revision records those decisions. The figures are in [[business/pricing-plan]] §3 and §8, and their financial effect in [[business/business-case]] (revision v3).

## Decision

1. **Two solo subscription tiers, and both carry the whole study loop.** Credits never meter consuming pre-generated content: taking tests, the ladder, flashcards, sessions, prestudy, trainers, reports and audio.

   | Tier | Price | What it adds |
   |---|---|---|
   | **Core** | US$6 / US$49; A$8.99 / A$75 | The study loop (reading, listening, vocabulary): no daily test cap, full daily plan, Vocab Dojo, trainers, FSRS, BKT summary, dictionary imports, DT 5 a day. **No credit allowance.** |
   | **Pro** | US$10 / US$89; A$14.99 / A$129 | Plus **production** (DT 25 a day) and **personalisation** (300 credits a month for custom tests and new-word imports, rollover capped at 1×), and full per-word knowledge reports |

   Core and Pro differ only in DT volume, report detail and the credit allowance, so the line can be moved by changing entitlement values.
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
   - Core: 5 a day
   - Pro: 25 a day
   - Professional: 40 a day
   - school student: 20 a day
   - Free: 5 a week

   The existing token guardrail becomes a per-tier cost backstop.
4. **Credit packs are the PAYG route; there is no time pass.** The 7-day Study Pass (US$6.99 / A$9.99 or 500 credits) in the first draft is **retired**: at A$9.99 a week it would cost more than a month of Core (A$8.99), so Core is the cheap way into the full loop. Per-test pricing is not used. The translators' CT Exam Pass (A$79 for 3 months) is unaffected.
5. **Credit pools.**

   | Pool | Expiry rule |
   |---|---|
   | Allowance (Core none; Pro 300 a month; Professional 600) | Rolls over, capped at 1× |
   | Bonus | Expires after 12 months |
   | Purchased | Never expires |

   - Spend order is allowance, then bonus, then purchased.
   - The cost is shown before every action.
   - Actions of 20 credits or more need a confirmation.
   - A failed action refunds its credits automatically.
   - Auto top-up is opt-in only.
   - Credits are not transferable.
6. **Organisations (schools and tutors) hold a pooled credit balance** that teachers control. Students never see credits. **Tutors are the first organisation buyers** (founder decision D12): they launch at M13 (Jan 2028) at A$39 a month for 10 students then A$3 per student, before schools.
7. **The legacy `take_test` token cost is retired.** `tokens_per_test` is set to 0. Existing token balances convert 1:1 into purchased credits.

8. **The Core/Pro split is measured, not assumed** (D19, open). The model assumes 50% of payers choose Core and that adding Core lifts sign-up → paid by 1.33×. If, in the first 90 days, Core is over 60% of payers and conversion has not risen at least 33% over the Pro-only baseline, raise Core to US$7 / A$9.99 or move features up to Pro, for new subscribers only.

Prices, tiers and policies are in [[business/pricing-plan]]. The schema and Stripe mapping are in [[business/pricing-plan.tech]].

## Consequences

**Easier:**
- One clear promise: "your study loop is never metered", now from US$6 a month.
- A cheap entry tier sits beside the utility tools learners already pay for (Bunpro, renshuu, Readlang), and Pro sits below the content-tool band.
- Credits track real cost, so heavy custom generation pays for itself.
- Everything a learner generates becomes shared content, which further amortises its cost.
- Pricing pages and support become simpler than with per-test tokens.

**Harder:**
- A real credit ledger is needed: atomic multi-pool spends, idempotency, refunds and reconciliation against `llm_calls` costs.
- `llm_calls` cost logging for DT must be fixed before the D9 re-price.
- Purchased credits that never expire are a deferred-revenue liability. It is small at modelled volumes.
- Two tiers mean two sets of Stripe/MoR prices, plan-change handling (prorated allowance on upgrade) and a pricing page that must make the dividing line obvious.
- **Lower contribution per payer.** Blended contribution falls from A$11.57 (Pro only) to A$8.30, and LTV at 9% churn from A$129 to A$92. The v3 base case ends M36 at −A$12.4k (v2: +A$8.4k) and needs about A$50k of founder cash. The ladder only pays back if Core lifts conversion substantially.
- **Cannibalisation.** Some learners who would have bought Pro will take Core. At 70% Core the base case loses a further A$10.9k by M36.

**Constrained:**
- The free tier cannot be widened by giving away credits for tests. Free limits are entitlements (counts), not credits.
- Any future feature that adds a live LLM call per use must either declare a credit price or fit under a fair-use cap.
- Any future per-test charge would reverse this ADR.

**Risk accepted:**
- On the 2,500-credit pack spent entirely on the costliest new-word imports, margin falls to about 11%. Every later learner reuses those senses.
- The conversion uplift from Core is unmeasured. Without it, the v3 base case ends M36 at −A$32.4k. The D19 trigger is the mitigation.

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

**F. One paid solo tier (Pro only, US$12 / US$99).** The first draft of this ADR. Superseded by the founder on 2026-11-17.
- Higher contribution per payer (A$11.57) and a simpler build.
- But a single US$99 tier leaves nothing for learners who want the study loop without translation volume or custom content, and the founder judged the cheaper ladder more likely to convert.

**G. Keep the 7-day Study Pass as the PAYG route into the loop.** Rejected on 2026-11-17.
- At A$9.99 a week it is dearer than a month of Core. It would only be bought by mistake, and it adds a fourth consumer product to build and support.

**H. Schools before tutors.** Rejected (founder decision D12).
- Schools need ST4S, procurement and a A$22.5k build; tutors buy by card and reuse the same class layer.

## Related
- [[business/business-case]]
- [[business/pricing-plan]]
- [[business/pricing-plan.tech]]
- [[business/market-research]]
- [[features/token-economy]]
- [[decisions/ADR-044-dt-single-call-generative-grader]]
