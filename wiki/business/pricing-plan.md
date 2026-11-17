---
title: LinguaDojo Pricing Plan
type: overview
status: planned
tech_page: ./pricing-plan.tech.md
last_updated: 2026-11-17
open_questions:
  - "OPEN (D4): Merchant of record for global consumer sales: Paddle (5% + 50¢; separate terms under US$10, unverified), Stripe Managed Payments (about +3.5%; AU eligibility unconfirmed), or Stripe + Stripe Tax with own EU/UK VAT registration? Core monthly (US$6) and Pro monthly (US$10) now sit at or below Paddle's US$10 small-ticket line, so these terms matter more than before."
  - "OPEN (D19): Core/Pro mix and conversion uplift. The model assumes 50% of payers on Core and a 1.33× lift in sign-up → paid from adding Core. Measure both in the first 90 days after launch; if Core is over 60% of payers and conversion has not risen at least 33% over the Pro-only baseline, raise Core to US$7 / A$9.99 or move features up to Pro."
  - "OPEN (D9): Re-price new-word import once DT/import cost logging works. 8 credits now; drop to 5 if the measured mean live cost per new sense is under A$0.04 over 30 days."
  - "OPEN (D15): Professional at A$219/yr (A$179 launch) or lower, given the PD-log caps (D.4 20 points per cycle, B.6 10 points per activity)?"
  - "OPEN: Final Children's Online Privacy Code text (due 10 Dec 2026). The age policy below (16+ self-serve, 13–15 with under-18 defaults, no under-13 solo accounts) may need to change."
  - "OPEN: Can the DT primary grader (openai/gpt-6-luna via OpenRouter) and its fallback be pinned to zero-data-retention providers? If not, which model replaces them?"
  - "OPEN: GST registration timing (D13). The recommended default is to register now."
---

# LinguaDojo Pricing Plan

## Conventions
- **Exchange rate:** 1 USD = A$1.47.
- **Consumer prices** in AUD include GST. EUR and GBP prices include VAT.
- **School prices** are quoted ex-GST, and GST is added on the tax invoice.
- **E** marks an estimate.

## Related pages
- Business case and numbers: [[business/business-case]]
- Implementation: [[business/pricing-plan.tech]]
- Decision record: [[decisions/ADR-047-credits-and-subscription-model]]
- Sources: [[business/market-research]]

## Purpose
Turn LinguaDojo's study tools into revenue through two mechanisms:
- **A subscription** in two solo tiers: **Core** for the study loop, and **Pro** for the study loop plus production practice and personalisation.
- **Pay-as-you-go credits** for the few actions that cost real money each time they run.

## User story
"I am preparing for HSK 5. I want one affordable subscription that gives me all the matched tests, my daily plan and my vocabulary review. If I start writing a lot of translations, I'll move up to Pro. I don't want to count tokens every time I take a test. If I want something made just for me, such as a test built from my textbook's word list, I'm happy to pay a few cents for it, and I want to see the price before I click."

---

## 1. What credits pay for (recommendation)

**Rule: credits meter only actions that make a live LLM call when they are used.** Content generated in batch is shared by every user and is never metered.

For people who don't subscribe, **credit packs** are the PAYG route. There is no longer a time-boxed pass into the study loop: the solo **7-day Study Pass was retired on 2026-11-17**. At A$9.99 for 7 days it would have cost more than a whole month of Core (A$8.99), so Core is now the cheap way into the full loop.

| Option | Verdict | Why |
|---|---|---|
| A. Meter only actions with real marginal cost | **Adopt** | Tests, the ladder, FSRS, BKT, sessions and audio cost A$0.00 per use. Custom tests cost A$0.02–0.23 each; importing a new word costs A$0.015–0.075. |
| B. Meter all usage past a free allowance (today's `take_test` = 1 token) | Reject | It charges for actions that cost us nothing, so it recovers no cost. It nickel-and-dimes the core loop. On small charges the A$0.30 card fee eats about 12%. It is also not even switched on (`submit.py` hardcodes `p_was_free_test=True`). |
| C. A plus a time-boxed pass for non-subscribers (7-day Study Pass) | **Retired 2026-11-17** (was adopted) | It met the PAYG requirement without per-test pricing, but at A$9.99 a week it is dearer than a month of Core (A$8.99). Credit packs remain the PAYG route. |

**Why dual-translation (DT) is capped, not metered**
- One DT grade costs about A$0.0003.
- Metering every submission would cost more in friction than it recovers.
- So DT is included up to a daily fair-use cap: 5 a day on Core, 25 on Pro.
- Credits apply only beyond the cap, or after a free user's weekly tasters.

### Credit design rules
1. Show the credit cost before every action. Actions of 20 credits or more need a one-tap confirmation, with no pre-ticked upsell.
2. If a generation fails, refund its credits automatically.
3. Auto top-up is off by default, opt-in only, and has a monthly ceiling the user sets.
4. Purchased credits **never expire**.
5. Credits cannot be transferred or gifted at launch. This keeps them outside the gift-card rules.
6. One balance is shown to the user. A tooltip splits it into "monthly allowance, renews on <date>" and "credits you own".

### 1.1 Credit price list

The nominal value of a credit is about A$0.015 / US$0.01 at the smallest pack.

| Action | Credits | Retail value (A$) | Cost to serve (A$) | Notes |
|---|---|---|---|---|
| Custom test from your own topic or word list (no L1 references) | 10 | 0.10–0.15 | 0.02–0.05 | Once moderated, the test joins the shared catalogue, so its cost is amortised |
| Add an L1 reference set to a custom test (enables DT and Produce) | +30 | 0.30–0.45 | ~0.18 (E) | |
| Import a word that is **not** in the 73k-sense dictionary (definition + ladder) | **8** per new sense | 0.10–0.12 | 0.015–0.075 | Dictionary words are free. The new sense becomes shared content. Re-price to 5 if the measured mean cost is under A$0.04 (D9) |
| DT submission beyond the fair-use cap, or for a non-subscriber after the free tasters | 1 | ~0.015 | 0.0003–0.001 | |
| Deep re-grade of a DT answer (v2 Detector/Verifier) | 8 | 0.08–0.12 | 0.04–0.07 | |
| Mock-passage grading (Professional and Exam Pass) | 25 | 0.25–0.38 | ~0.05–0.10 (E) | |

**Never metered:** taking any pre-generated test, placement, Vocab Dojo, FSRS flashcards, daily sessions, prestudy, the pinyin, pitch and measure-word trainers, analytics, and audio.

**Retired (2026-11-17): 7-day Study Pass** (was 500 credits or US$6.99 / A$9.99). A pass priced above a month of Core would only ever be bought by mistake, and keeping it would mean a fourth consumer product to build, explain and support. Non-subscribers who want the full loop for a short spell take the 21-day trial or one month of Core and cancel.

---

## 2. Free tier and trial

| | Free |
|---|---|
| Placement / vocabulary-size calibration | Full |
| ELO-matched tests | **1 new test a day.** Retakes are unlimited. The 18 existing users keep 2 a day (grandfathered) |
| Daily session / study plan | 10 minutes a day, 5 new words a day |
| Vocab Dojo ladder and new-word drill | Inside the capped session |
| FSRS flashcards | Full |
| Test prestudy | 1 a week |
| Trainers (pinyin tones, pitch accent, measure words) | Taster levels |
| BKT knowledge report | Summary |
| DT grading and guided self-repair | 5 a week, then 1 credit each |
| Credits | Can buy packs; no allowance |

**Trial (D5)**
- 21-day Pro trial with no card, starting after placement. At the end the learner chooses Core or Pro, or drops to Free.
- RevenueCat: trials of 17 days or longer convert 42.5%, against 25.5% for shorter ones.
- Re-offer a 14-day trial at day 45. Adapty: 23.5% of education trials start after day 31.
- Remind the user 3 days before the trial ends. Nothing is charged, because no card was taken.

**Age policy (provisional until the Children's Online Privacy Code is final)**
- **16 and over:** self-serve.
- **13–15:** allowed, with under-18 defaults: no marketing email, no public profile, minimal analytics and no third-party analytics sharing.
- **Under 13:** no solo accounts. Students reach the product only through a school or tutor.
- Primary schools are excluded at launch.

---

## 3. Solo subscription (global)

### 3.1 Tiers at launch (D2, decided 2026-11-17: two paid solo tiers)

| | Core | Pro |
|---|---|---|
| Matched tests | No daily cap. Catalogue size per band is shown in the UI. We do not promise "unlimited" until each band has at least 200 tests. | Same |
| Daily session / study plan | Full budget, custom quotas, extra rounds | Same |
| Vocab Dojo ladder, new-word drill, prestudy, trainers | Full | Full |
| FSRS flashcards | Full | Full |
| BKT knowledge reports | **Summary** | Full, per word sense |
| Word-list import (dictionary words) | Included | Included |
| DT grading and self-repair | **Fair use: 5 a day**, then 1 credit each | **Fair use: 25 a day**, then 1 credit each |
| Monthly credit allowance | **None** | **300 credits** (about 30 custom tests, or 37 new words), rollover capped at 1× |
| Credit packs | Can buy at the standard price | Can buy at the standard price |

**The dividing line.** Core is the **study loop**: reading, listening and vocabulary. Pro adds **production** (DT volume: 25 graded translations a day instead of 5) and **personalisation** (custom tests and new-word imports, paid from the monthly credit allowance). A Core subscriber can still make a custom test or import a new word by buying a pack; Pro simply includes the credits.

### 3.2 Prices (D3, decided 2026-11-17)

| | Core monthly | Core annual | Pro monthly | Pro annual |
|---|---|---|---|---|
| USD (default for the rest of the world) | **US$6** | **US$49** (32% off 12× monthly) | **US$10** | **US$89** (26% off) |
| AUD (GST included) | **A$8.99** | **A$75** (30% off: A$8.99 × 12 = A$107.88) | **A$14.99** | **A$129** (28% off: A$14.99 × 12 = A$179.88) |
| EUR / GBP (VAT included; **derived**, not set by the founder) | €5.99 / £4.99 | €49 / £42 (32% / 30% off) | €9.99 / £8.49 | €89 / £75 (26% off) |

- EUR/GBP prices are derived from the USD prices at the same ratios as the earlier draft (€ ≈ US$ at charm points; £ ≈ 0.85 × €). Confirm before provisioning.
- These replace the earlier draft of US$12 / US$99 (A$17.99 / A$149) for a single Pro tier, which was never sold.
- Pro costs A$6 a month (A$54 a year on annual) more than Core.

**Positioning**
- **Core** (US$6 / US$49) sits in the utility price band, beside Bunpro (US$5 a month, ~US$50 a year), renshuu (US$49.99 a year) and Readlang (US$6 / US$48). It offers far more than an SRS at that price: matched tests, the daily plan, knowledge tracking and a taste of graded translation.
- **Pro** (US$89 a year) now sits at the bottom of the "content and immersion" band, just under Satori (US$89.99) and below Migaku US$96, Skritter US$99.99 and LingQ US$119.99.
- Both are below the AI-tutor band: Duolingo Max ~US$168, Speak US$164.99.
- The pitch is that LinguaDojo replaces the **reading, listening and vocabulary** parts of a learner's stack (Core), with translation practice and personal content on top (Pro).
- Do **not** claim it replaces WaniKani or Bunpro.

**Regional / PPP pricing (D8)**
- Off at launch.
- After 3 months of data, add a −40% zone keyed to the card's billing country for lower-middle-income markets. Much of the JLPT and HSK volume is in Asia.
- Have the price table ready before launch so the zone can be switched on quickly.

### 3.3 Credit packs (anyone can buy)

| Pack | USD | AUD (GST included) | Bonus | Effective A$ per credit |
|---|---|---|---|---|
| 500 | US$4.99 | A$7.49 | — | 0.0150 |
| 1,100 | US$9.99 | A$14.99 | +10% | 0.0136 |
| **2,500** | US$19.99 | A$29.99 | **+25%** | 0.0120 |

- There is no pack below A$7.49. Below that, the A$0.30 fee takes more than 6%.
- If the merchant of record's terms under US$10 are poor (D4), sell packs through Stripe directly, or drop the 500 pack and start at US$9.99.
- Packs carry no extra bonus for subscribers. Pro's allowance already covers that, Core is priced without credits, and dropping the bonus keeps worst-case pack margins above zero.
- Packs are the only PAYG product for solo learners now that the Study Pass is retired.

### 3.4 Credit pools, expiry and rollover (D10)

| Pool | Source | Expiry | Spent |
|---|---|---|---|
| Allowance | Monthly subscription grant (Pro 300, Professional 600, Lifetime 150; **Core has none**) | Rolls over, capped at 1× the allowance (so at most 600 for Pro). Lifetime does not roll over. Lapses when the subscription ends or drops to Core. | First |
| Bonus | Promotions, referrals, goodwill | 12 months from the grant, disclosed when granted | Second |
| Purchased | Packs, and converted legacy tokens | **Never.** Still usable after cancelling. If we close the service, unused purchased credits are refunded at their purchase value. | Third |

---

## 4. Schools (Australia, ex-GST)

**Unit of sale:** a language **department licence**, priced per enrolled student per year.
- Teachers are unlimited.
- Student numbers are counted at a census date (end of Term 1). Students added mid-year are pro-rated by term.
- Years 7–12 only at launch.

| Plan | Price (ex-GST) | What it includes |
|---|---|---|
| **Free Teacher** | A$0 | 1 class of up to 30 students. Catalogue tests and assignments. On-screen gradebook for the current term, with no export. Student DT capped at 10 a week. 200 pooled credits a year. |
| **Term Pilot** | A$0 for one term | Up to 3 classes with every feature. Timed for Terms 1–3, with conversion in Term 4 when budgets are set. |
| **Class** (new) | **A$450 a year** for 1 class of up to 30 | Department features for one class: CSV/PDF export, curriculum-tagged packs, SSO, full DT, 100 pooled credits per seat |
| **Department** | **A$15 per student per year**, minimum **A$750** (50 students) | Assignments, gradebook with CSV/PDF export, curriculum-tagged packs, SSO, full DT (fair use 20 a day per student), home access, **100 pooled credits per seat per year** |
| Senior Exam add-on (Years 11–12) | +A$15 per student (A$30 total) | VCE, HSC, QCE and SACE-aligned topic packs, timed mocks, criteria-based reports |
| Community language schools | 50% off Department, minimum A$375 | Grant-friendly quote. Chinese heritage schools fit the background-learner pathway. |

**Volume and caps**
- 1–300 students: A$15 per student. 301–600: A$13. 601 and over: A$11.
- A whole-school site cap of **A$9,500 ex-GST** keeps every deal under QLD's single-quote threshold of A$10k.
- A typical department of 60–250 students pays **A$900–3,750**. That needs one quote in VIC (written once over A$2.5k) and one quote in QLD.

**Credits in schools**
- Students never see credits.
- Teachers control the department pool. It pays for teacher-made custom tests, new-word imports for a class, reference sets and mock grading.
- Pool top-ups are **5,000 credits for A$50 ex-GST**, invoiced.

**Invoicing**
- Instant quote PDF, valid for 30 days, that the school can raise a PO against.
- Stripe Invoicing, net 30, bank transfer accepted.
- Billed annually in advance, aligned to the school calendar year.
- ABN-bearing tax invoice. This requires GST registration (D13).
- Seat true-up in Term 2.

**Tutors and tutoring colleges (card billing, GST included).** Founder decision D12 (2026-11-17): tutors are the first B2B buyers and launch at M13 (Jan 2028), before schools.
- **A$39 a month includes 10 student seats. Each extra seat is A$3 a month.**
- An ABN is required.
- Tutor seats unlock assigned content plus a capped daily session, not the full Pro features. This closes the "15 friends become a tutoring group" arbitrage.
- A typical tutor with 15 students pays A$54 a month, which is about A$43 per student per year. Solo Core costs A$75 a year and Pro A$129.

---

## 5. Translators (Australia first, then global)

### 5.1 Professional tier
| | Professional |
|---|---|
| Price | **A$24.99 a month / A$219 a year** (GST included); **US$16 / US$149** |
| Launch price (until the glossary ships) | A$179 a year / US$119, locked for founding subscribers |
| Includes | Everything in Pro. Domain packs, starting with health, legal and immigration, with finance/ATO and tech to follow. A fortnightly "domain digest" test with its new terms. Domain-tagged DT with a selectable direction, including *into* the native language, graded against reviewed L1 references. NAATI PD log export (D.4 and B.6; CSV and PDF; portable to ITI and CIOL). Phase 2: glossary with CSV import/export, and DT that enforces the glossary. Roadmap: MT post-edit drill. |
| Credits | **600 a month** (mock grading at 25, domain custom tests at 10, term imports at 8) |
| DT fair use | **40 a day** |

**Positioning**
- Sell it as **terminology currency**: keeping up with domain vocabulary in both languages.
- The PD log is a retention feature, not the reason to buy. NAATI caps D.4 at 20 points per 3-year period and B.6 at 10 points per activity.
- The price sits inside a freelancer's PD budget (about A$200–600 a year, E), well below CAT tools (Trados US$408–564 a year).

### 5.2 CT Exam Pass
- **A$79 for 3 months, one-off, no auto-renewal** (US$55).
- Professional features for one language pair, plus **1,000 credits** for mock-passage grading.
- **For NAATI Certified Translator (CT) candidates only.**
- CCL is an oral interpreting test, and LinguaDojo assesses neither speaking nor interpreting. CCL candidates are offered domain vocabulary and listening packs inside Pro. They are never sold "CCL exam prep".
- Never claim "NAATI-approved".

---

## 6. Launch offers, discounts, refunds and grandfathering

| Item | Policy |
|---|---|
| **Founding member** | First 500 subscribers or first 90 days: **US$69 / A$99 a year** for Pro, about 23% below the Pro annual price (US$89 / A$129). The rate is locked while the subscription runs without a break. There is no founding rate for Core. |
| **Lifetime** (D7) | Up to 100 seats at **US$299 / A$449** (about 3.4–3.5 years of Pro annual). Pro features only. **150 credits a month, no rollover.** DT fair use applies. Professional and school features are excluded. The terms define "lifetime" as *the life of the LinguaDojo Pro service*. If we discontinue it within 36 months of purchase, the refund is pro-rated over 36 months. |
| Annual discount | Pro about 28% in AUD (26% in USD); Core about 30% in AUD (32% in USD). See §3.2. |
| Student discount | Verified students pay **US$59 / A$89 a year** for Pro, about a third off Pro annual (31% in AUD, 34% in USD). Students leaving a school licence get the same. There is no student rate for Core, which is already cheaper. |
| Annual sale | One a year, in November ("Dojo Week"): **up to 20% off annual** (Pro A$103, Core A$60). This was 30% before the 2026-11-17 price cut; at 30% the Pro sale price (A$90) would undercut the founding rate. Monthly prices are never discounted. |
| **Cancellation** | One click in the account, as easy as signing up. This is ready for the unfair trading practices law from 1 Jul 2027. Monthly plans run to the end of the paid period. |
| **Refunds** | Annual plans: full refund within 14 days of the first charge and of each renewal, with a reminder email 14 days before renewal. Credit packs: refundable within 14 days if unused. Failed actions refund their credits automatically. Australian Consumer Law guarantees always apply. |
| **Grandfathering** | Every subscription stores a `price_version`. Subscribers keep their price and features while they stay subscribed. Price rises get 60 days' notice and apply only from the next period. New premium features may go into a higher tier, but nothing is removed from a paid tier. If the D19 trigger moves a feature from Core up to Pro, existing Core subscribers keep it. |
| **Existing 18 users** | Founding status. 2 free tests a day kept. Legacy token balances convert 1:1 to purchased credits. |

---

## 7. Margins per tier and usage profile

All figures are A$ per month, on an AU domestic card through Stripe.
- **Net revenue** excludes GST.
- **Payment fee** is 1.65% + A$0.30, plus about 0.7% for Stripe Billing on subscriptions.
- Fixed infrastructure is excluded; see [[business/business-case]] §9.

**Usage profiles**

| Profile | What it covers | Variable cost |
|---|---|---|
| **Light** | No DT, no credits | A$0 |
| **Typical** | 20 DT plus 10 new words | A$0.43 (all tiers). On Core the 10 new words would be paid from purchased credits, so this overstates Core's cost; pack revenue is counted separately. |
| **Heavy** | Pro and Professional: 150 DT plus the whole allowance spent on new words at the worst-case A$0.075. Core (no allowance): typical plus DT at the 5-a-day cap | Core A$0.58 (0.43 + 0.15); Pro A$3.06; Professional A$7.31 |
| **DT cap** | DT at the daily cap every day and no credits: 5 a day for Core, 25 for Pro, 40 for Professional | Core A$0.15 (150 grades at about A$0.001, the model's basis); Pro A$1.05; Professional A$1.68 |

**Margins by plan**

| Plan | Net revenue | Fee | Light | Typical | Heavy | DT cap |
|---|---|---|---|---|---|---|
| Core monthly A$8.99 | 8.17 | 0.51 | 94% | 88% | 87% | 92% |
| Core annual A$75 | 5.68 | 0.17 | 97% | 89% | 87% | 94% |
| Pro monthly A$14.99 | 13.63 | 0.65 | 95% | 92% | **73%** | 88% |
| Pro annual A$129 | 9.77 | 0.28 | 97% | 93% | **66%** | 86% |
| Founding A$99/yr | 7.50 | 0.22 | 97% | 91% | 56% | 83% |
| Student A$89/yr | 6.74 | 0.20 | 97% | 91% | 52% | 81% |
| Lifetime A$449 (A$397 net once) | — | — | Heavy worst case about A$1.66/mo, so the net payment covers about 20 years | | | |
| Professional monthly A$24.99 (typical A$2.50) | 22.72 | 0.89 | 96% | 85% | 64% | 89% |
| Professional annual A$219 | 16.59 | 0.45 | 97% | 82% | 53% | 87% |
| Professional launch A$179 | 13.56 | 0.38 | 97% | 79% | 43% | 85% |
| Tutor, 15 seats, A$54 | 49.09 | 1.57 | | 95% (variable about A$1) | | |
| School, per student per year, A$15 | 15.00 | ~0.15 | | about 96% (variable under A$0.50) | | |

**Arithmetic.** Net revenue = price ÷ 1.1 (÷ 12 for annual plans). Fee = (price × 2.35% + A$0.30) per charge (÷ 12 for annual). Margin = (net − fee − variable cost) ÷ net. Examples:
- Core monthly: 8.99 ÷ 1.1 = 8.17; fee 8.99 × 0.0235 + 0.30 = 0.51; typical (8.17 − 0.51 − 0.43) ÷ 8.17 = 88%.
- Core annual: 75 ÷ 1.1 ÷ 12 = 5.68; fee (1.76 + 0.30) ÷ 12 = 0.17; heavy (5.68 − 0.17 − 0.58) ÷ 5.68 = 87%.
- Pro monthly: 14.99 ÷ 1.1 = 13.63; fee 0.35 + 0.30 = 0.65; heavy (13.63 − 0.65 − 3.06) ÷ 13.63 = 73%.
- Pro annual: 129 ÷ 1.1 ÷ 12 = 9.77; fee (3.03 + 0.30) ÷ 12 = 0.28; heavy (9.77 − 0.28 − 3.06) ÷ 9.77 = 66%.

Core's fixed card fee is a bigger share of a smaller charge (6% of net on monthly), but its worst-case usage is low because it has no allowance; Core margins are therefore higher than Pro's in the heavy case. Founding, Student and Lifetime rows are unchanged because their prices did not change.

**Other routes**
- An international card through Stripe adds about A$0.40 a month (2.8% + 2% FX; the 2.8% rate is unverified, and some sources still show 3.5%).
- A merchant of record at 5% + US$0.50 (A$0.74) costs about A$1.49 a month on Pro monthly and A$1.19 on Core monthly. On Core monthly that is about 15% of net revenue, cutting the typical margin to about 80% (Pro monthly: about 86%). The MoR then remits GST and VAT. Revenue in the model is ex-tax, so nothing is counted twice.

**Credit packs (domestic Stripe, after GST and fees)**

| Pack | Net | All spent on new words, worst case (A$0.075) | All new words at average cost (~A$0.045) | All custom tests (A$0.02–0.05) |
|---|---|---|---|---|
| 500 / A$7.49 | 6.39 | 27% | 56% | 61–84% |
| 1,100 / A$14.99 | 13.08 | 21% | 53% | 58–83% |
| 2,500 / A$29.99 | 26.47 | 11% | 47% | 53–81% |

Every pack keeps a positive margin, even in the worst case. Any new sense or custom test a buyer creates is reused by every later learner.

---

## 8. Founder decisions (recommended default in **bold**; rows marked **Decided** were settled by the founder on 2026-11-17)

| # | Decision | Recommended default / decision | Alternative |
|---|---|---|---|
| D1 | What credits meter | **Only live-LLM actions. Tests are never metered.** (The 7-day Study Pass that was part of this default is retired: dearer than a month of Core.) | Keep per-test tokens |
| D2 | Solo tiers at launch | **Decided: two solo tiers at launch, Core + Pro.** Professional comes later. | One tier (Pro only), the earlier default; Pro + "Pro Plus" AI tier |
| D3 | Solo prices | **Decided: Core US$6 / US$49, A$8.99 / A$75; Pro US$10 / US$89, A$14.99 / A$129.** | The earlier draft: Pro only at US$12 / US$99, A$17.99 / A$149 |
| D4 | Payment stack | **Merchant of record for global consumers (verify Paddle's sub-US$10 terms and Stripe Managed Payments' AU eligibility). Stripe Invoicing for AU schools. Stripe for AU tutors.** | Stripe + Stripe Tax everywhere, with self-registration for EU/UK VAT |
| D5 | Trial | **21 days, no card, re-offered at day 45** | 7 days with a card |
| D6 | Free-tier tests | **1 new matched test a day; existing users keep 2** | 2 a day for everyone |
| D7 | Lifetime plan | **100 seats at US$299, 150 credits a month, "lifetime" defined in the terms** | Founding annual only |
| D8 | PPP pricing | **Off at launch; −40% zone after 3 months of data** | PPP at launch |
| D9 | New-word import | **8 credits; drop to 5 if the measured cost is under A$0.04** | 5 credits now |
| D10 | Credit expiry | **Purchased never expire; bonus after 12 months; allowance rolls over capped at 1×** | 24-month inactivity expiry (rejected: unfair-terms risk) |
| D11 | School price | **A$15 per student, A$750 minimum, Class A$450, Senior +A$15** | Flat A$2,000 per department up to 150 students |
| D12 | First B2B buyers | **Decided: tutors first, launching M13 (Jan 2028) at A$39 a month for 10 students then A$3 per student; then independent and Catholic secondaries. Start the ST4S Readiness Check now.** | Government schools first |
| D13 | GST | **Register now, voluntarily** | Wait for the A$75k threshold |
| D14 | Translator timing | **Founder order: after schools (G2), launched lean** | Before schools (cheaper to build) |
| D15 | Professional price | **A$219 / US$149 a year; A$179 launch** | A$179 permanently, or A$129 (rejected: it would equal the Pro annual price) |
| D16 | Founder cash commitment | **About A$50k of business cash.** The v3 base trough is −A$37.7k (Dec 2028); a ~A$12k buffer also covers the −A$45.2k trough if Core brings no conversion uplift. | About A$40k, with the M6 cost-cut trigger and the D19 Core trigger both enforced |
| D17 | Age policy | **16+ self-serve; 13–15 with under-18 defaults; no solo under 13** | 18+ only (simplest, loses HSK/JLPT teens) |
| D18 | Exam Pass scope | **CT candidates only** | Include CCL (rejected: misleading-conduct risk) |
| D19 | Core/Pro mix and conversion uplift (**open**) | **Treat the model's 50% Core share and 1.33× conversion uplift as assumptions and measure both in the first 90 days after launch. Trigger: if Core is over 60% of payers and sign-up → paid has not risen at least 33% over the Pro-only baseline (3.0%, so it is still below 4.0%), raise Core to US$7 / A$9.99 or move features up to Pro, for new subscribers only.** | Leave the ladder unchanged and accept the lower contribution per payer |

## Constraints and edge cases
- **Cancelling Core or Pro with credits left.** Allowance credits lapse. Bonus and purchased credits remain usable.
- **Downgrading from Pro to Core.** Applies at the end of the paid period. The allowance lapses, knowledge reports return to the summary, and the DT fair-use cap drops to 5 a day. Bonus and purchased credits remain usable.
- **Upgrading from Core to Pro mid-period.** The provider prorates the price difference. The allowance for the rest of that period is prorated too; the full 300 arrives with the first Pro renewal. This stops a last-day upgrade from buying 300 credits for a few cents.
- **Downgrading from Professional to Pro.** Professional-only features become read-only (the glossary can still be exported). The allowance resets to 300 at the next period.
- **A school student who also buys Pro.** Personal Pro takes precedence for the student's own study. School assignments still come from the school seat.
- **A failed LLM call** costs the user 0 credits.
- **A moderated custom test that is rejected for the catalogue** stays private to its creator. It is not refunded, because the user received it.
- **Refunds of credit packs.** Only unused credits can be refunded. Credits are spent in the order allowance, then bonus, then purchased, so purchased credits are the last to go.

## Related Pages
- [[business/pricing-plan.tech]] — Technical specification
- [[business/business-case]] — Unit economics and scenarios
- [[business/market-research]] — Competitor prices and sources
- [[decisions/ADR-047-credits-and-subscription-model]] — The decision record
- [[features/token-economy]] — Legacy token system being replaced
- [[features/dual-translation]] — DT grading (fair-use capped)
- [[business-rules/auth-and-access]] — Tier and role rules
