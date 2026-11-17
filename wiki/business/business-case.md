---
title: LinguaDojo Business Case
type: overview
status: planned
tech_page: ./pricing-plan.tech.md
last_updated: 2026-11-17
open_questions:
  - "OPEN: Can LinguaDojo reach 400 free sign-ups in its first billing month (Jan 2027) from 18 users today? This is the most influential input; validate it within 90 days of launch and re-run the model."
  - "OPEN: How much business cash will the founder commit? The v3 base case needs about A$50k (trough −A$37.7k plus a buffer that also covers the no-uplift trough of −A$45.2k); the conservative case with cost cuts needs about A$40k."
  - "OPEN (D19): Does adding Core lift sign-up → paid by the assumed 1.33×, and what share of payers choose Core (assumed 50%)? Measure in the first 90 days after launch. The v3 base case only pays back if the uplift is real."
  - "OPEN: Which merchant of record (Paddle, or Stripe Managed Payments if available in AU) will handle global consumer sales, and on what terms for charges under US$10?"
  - "OPEN: What is the ST4S full-assessment fee and queue time? The model assumes A$7.5k (estimate)."
  - "OPEN: What does the final OAIC Children's Online Privacy Code (due 10 Dec 2026) require for 13–17-year-old solo users?"
  - "OPEN: Where are Supabase and Railway hosted today? This is needed before any data-residency claim to schools."
  - "OPEN: What does a DT grade cost in production? llm_calls cost logging is broken for DT (NULL cost_usd, 0 tokens) and grading appears to route to :free models."
---

# LinguaDojo Business Case

All money is in AUD unless marked. FX is 1 USD = A$1.47. Revenue figures are ex-GST. **E** marks an estimate. Market and competitor sources are in [[business/market-research]]. Prices and credit rules are in [[business/pricing-plan]]. The monetisation model is recorded in [[decisions/ADR-047-credits-and-subscription-model]].

## Revision 2026-11-17 (v3): Core + Pro

**What changed (founder decisions, [[business/pricing-plan]] §8):**
- **New middle tier, Core:** US$6 / US$49, A$8.99 / A$75. The full study loop, DT fair use 5 a day, BKT summary, no credit allowance (D2, D3).
- **Pro lowered:** US$10 / US$89, A$14.99 / A$129 (was US$12 / US$99, A$17.99 / A$149). Features unchanged.
- **7-day Study Pass retired.** At A$9.99 a week it cost more than a month of Core. Credit packs remain the PAYG route.
- **Tutors before schools decided** (D12): tutors launch M13.
- **New open decision D19:** the Core share and the conversion uplift are assumptions to measure in the first 90 days.

**Model v3** (`wiki/business/model/financial_model.py`): Core ARPU A$6.93, Pro ARPU A$10.97, 50% of payers on Core, and a 1.33× lift in sign-up → paid from having a cheaper tier.

| Metric | v2 (Pro only) | v3 (Core + Pro) |
|---|---|---|
| Contribution per solo payer per month | A$11.57 | **A$8.30** blended (Core A$6.65, Pro A$9.96) |
| Solo LTV at 9% churn | A$129 | **A$92** |
| Conservative: break-even / M36 cash | M35 / −A$31.7k | **none in 36 months / −A$37.3k** |
| Base: operating break-even | M16 | **M18** |
| Base: cash trough | −A$29.3k | **−A$37.7k** (Dec 2028) |
| Base: M36 cash | +A$8.4k | **−A$12.4k** |
| Base: solo payers at M36 | 811 | **1,078** |
| Base: ramen | M40 | **M46** (48-month run; not within 36 months) |
| Optimistic: break-even / ramen / M36 cash | M5 / M21 / +A$352.5k | **M7 / M22 / +A$289.5k** |
| Founder business cash | about A$40k | **about A$50k** |

**The plain implication.** The cheaper ladder brings in more payers (1,078 against 811 at M36) but each earns about 28% less. It only pays back if Core lifts paid conversion substantially: with no uplift the base case ends M36 at −A$32.4k; with a 1.5× uplift it ends at −A$2.1k. The founder should plan on about **A$50k of business cash** instead of about A$40k, and treat the D19 trigger as part of the plan.

---

## 1. Executive summary

**What it is.** LinguaDojo (LinguaLoop in older docs) sells serious study tools to serious learners of Chinese, Japanese and English. It is not a gamified streak app. Its core is measurement:
- a calibrated vocabulary-size placement;
- comprehension tests (reading, listening, dictation, pinyin tones) matched by dual ELO;
- knowledge tracing for each word sense, with FSRS review;
- a daily study plan with a time budget;
- dual-translation (DT) practice graded by an LLM, with guided self-repair.

**Why it can be profitable early.**
- **Content costs almost nothing.** Filling the current zh/ja/en catalogue gap to launch depth costs about A$3k in AI spend, shared across every user.
- **Use costs almost nothing.** A DT grade costs about A$0.0003. Tests, flashcards, the ladder and sessions cost A$0 per use.
- **The real costs are elsewhere:** the A$0.30 fixed card fee, fixed infrastructure (A$110–160 a month), and human review of content. Human review is more than 90% of the content cost in every segment.
- **Gross margin** on the solo subscriptions is about 87% blended (contribution A$8.30 per payer per month: Core A$6.65, Pro A$9.96).

**How it makes money.**
- **Subscriptions, two solo tiers.**
  - **Core** costs **US$6 a month or US$49 a year** (A$8.99 / A$75 including GST). It is the whole study loop: matched tests with no daily cap, the daily plan, Vocab Dojo, trainers, FSRS, the BKT summary and 5 graded translations a day. No credit allowance.
  - **Pro** costs **US$10 a month or US$89 a year** (A$14.99 / A$129). It adds production and personalisation: 25 graded translations a day, full per-word knowledge reports and **300 credits a month**.
- **PAYG credits** pay **only for actions that make a live LLM call**: custom tests, importing a word that is not in the dictionary, DT beyond the fair-use cap, deep re-grades and mock grading. Packs start at US$4.99 / A$7.49 for 500 credits, and purchased credits never expire. Packs are the PAYG route for non-subscribers; the 7-day Study Pass is retired.

**Who buys, in what order.** This is the founder's sequence, with tutors as the first B2B step because they are cheap to serve (decided by the founder on 2026-11-17, D12).
1. **Solo learners, worldwide.** Launch Jan 2027.
2. **Tutors and tutoring colleges in Australia.** From Jan 2028. They use the class and assignment layer and need no ST4S assessment.
3. **Australian schools.** The build is committed only at Gate G1 (base case Jul 2028). First paid school revenue is mid-2029 from independent schools; broad revenue starts Term 1 2030.
4. **Translators.** A lean Professional tier and a CT Exam Pass, from Jul 2029 in the base case.

**What the numbers say (model v3, §8).**

| Scenario | Operating break-even | Cash trough | Cash at M36 (Dec 2029) | MRR at M36 | Ramen profitable |
|---|---|---|---|---|---|
| Conservative (cost cuts at M6) | Not within 36 months | −A$37.3k (M36, still falling slowly) | −A$37.3k | A$2.5k | Not within 36 months |
| **Base** | **M18 (Jun 2028)** | **−A$37.7k (Dec 2028)** | **−A$12.4k** | **A$12.5k** | **Not within 36 months (M46, Oct 2030, in a 48-month run)** |
| Optimistic | M7 (Jul 2027) | −A$13.9k (Dec 2027) | +A$289.5k | A$50.5k | M22 (Oct 2028) |

- The red team's corrections (churn 9%, conversion 3%, 40 founding members, later schools, smaller tutor and translator volumes, A$7k native QA) already cut the draft base case to a thin positive M36 cash position. The v3 price ladder (see the revision note above) moves it below zero at M36, although the business is operating-profitable from M18 and cash is rising by about A$12k a quarter by late 2029.
- **This is a viable bootstrapped business, but a slow one.** It needs about **A$50k of founder business cash** and nearly 4 years before it pays the founder a salary.
- **The outcome depends mostly on organic sign-up volume, conversion and price discipline, not AI cost.** The cheaper ladder makes conversion (and whether Core lifts it) the most important thing to measure after launch.

**Decision asked of the founder.** The launch prices, the two solo tiers and tutors-first are now decided. Still to do: approve the hybrid model ([[decisions/ADR-047-credits-and-subscription-model]]), commit about A$50k of business cash (D16), accept the D19 measurement trigger, and build billing (Gate G0) for a January 2027 launch.

---

## 2. Positioning: serious tools for serious learners

**For** adult and senior-secondary learners preparing for HSK, JLPT, VCE, HSC or IB, or keeping a professional language current. **LinguaDojo** measures what you know, word sense by word sense, and gives you the next test, word and translation drill that moves you forward. **Unlike** gamified course apps, it never pays you for streaks. It shows you calibrated progress.

**Lead with measurement.** Free chatbots can grade a translation or write a reader on demand, so custom content and DT alone are not a moat. The defensible value is:
- **Calibrated placement.** A Zipf vocabulary-size estimate with its uncertainty.
- **Matching.** ELO-matched tests from a curated, audio-backed catalogue.
- **Knowledge tracking.** Per-sense BKT with FSRS decay ([[features/vocabulary-knowledge]]).
- **Daily plan.** A plan that respects a time budget ([[features/study-plans]], [[features/session-budget-settings]]).
- **Feedback.** Translation feedback that sends errors back for remediation ([[features/dual-translation]], [[features/dt-guided-self-repair]]).

**The value story.** "Replaces the reading, listening and vocabulary parts of your study stack."
- The stack: Satori Reader US$89.99/yr, LingQ US$119.99/yr, Du Chinese US$119.99/yr.
- LinguaDojo Core costs **US$49/yr** and Pro **US$89/yr**.
- **Do not** claim to replace WaniKani or Bunpro. LinguaDojo has no kanji-writing, mnemonic or grammar SRS, so that claim cannot be substantiated (ACL s18 risk).

**What we never do:**
- meter the core study loop;
- sell streak freezes or gems;
- show dark-pattern upsells.

Credit costs are shown before every action.

---

## 3. Segments, sequence and gates

| # | Segment | Market | What they buy | Launch (base) |
|---|---|---|---|---|
| 1 | Solo learners | Global; USD default, AUD/EUR/GBP local | Core or Pro subscription, credit packs, lifetime (100 seats) | Jan 2027 (M1) |
| 2a | Tutors and tutoring colleges | AU | Tutor plan (classes, assignments, gradebook): A$39 a month for 10 students, then A$3 per student | Jan 2028 (M13); founder decision D12 |
| 2b | Schools: language departments, Years 7–12, no primary at launch | AU | Class and Department licences, Senior add-on, credit pool | Build from Jul 2028; first paid mid-2029; broad Term 1 2030 |
| 3 | Translators and NAATI CT candidates | AU first, then global | Professional tier, CT Exam Pass | Jul 2029 (lean) |

### Gate metrics

Each segment opens only when its gate is passed. Each gate is checked monthly from the date shown.

| Gate | Earliest (base) | Must be true before committing | If missed |
|---|---|---|---|
| **G0: billing live** | M1 (Jan 2027) | Webhook, entitlements, subscriptions, credit ledger and pricing page shipped. Age gate and privacy policy live. DT on zero-data-retention (ZDR) providers. Waitlist ≥500. | Do not launch; fix first. |
| **Cost-cut trigger** | M6 | Any of these: sign-up → paid < 2%; monthly churn > 11%; fewer than 60 payers. | Cut fixed costs by about A$780 a month (AI tools, paid marketing tooling, contingency). This is the conservative path. |
| **G1a: tutor layer** (founder time only) | M7 → launch M13 | ≥100 paying solo users; churn ≤10%; ≥10 tutors on the waitlist | Defer the class layer by a quarter. |
| **G1: schools** (A$22.5k one-off + A$875/mo + about 6 months of founder build) | M19 (Jul 2028) | (a) ≥250 paying solo users; (b) operating surplus 2 months running; (c) churn ≤10%; (d) sign-up → paid ≥2.5%; (e) ≥10 tutor accounts and ≥3 schools committed to a free Term Pilot; (f) ≥A$25k cash available for the build | Stay solo + tutors. Start the ST4S Readiness Check anyway, because it is cheap and the queue is long. |
| **G2: translators** (lean: A$4k one-off + A$250/mo) | M31 (Jul 2029) | (a) ≥3 schools signed or converted from pilot; (b) ≥20 tutor accounts; (c) combined MRR ≥A$9k; (d) a translator waitlist ≥100, **or** an agreement with AUSIT or NAATI Learn for a PD module | Pause translators. |
| **G3: first hire** | about M49 (base, beyond the 36-month model), M24 (optimistic) | Operating surplus ≥A$7.5k a month for 3 consecutive months, **and** measured 12-month solo LTV/CAC above 3 | Stay solo and keep the cost base. |

### Why this order holds up
- **Solo comes first** because it needs only billing (about 3–5 solo-dev weeks), which is the shortest path to cash.
- **Tutors come before schools** (decided by the founder, D12).
  - They buy by card with no procurement and no ST4S.
  - They reuse the class and assignment layer that schools also need.
  - In the base case, doubling tutor volume adds A$17k of M36 cash.
- **Schools are the biggest prize after solo, but they pay back after month 36.**
  - Within 36 months, skipping schools would leave +A$31k more cash, because the A$22.5k build and ST4S costs land in 2028–29 and broad revenue starts Term 1 2030.
  - In the 48-month run, schools reach about 12 paying in 2030 and the investment is recovered.
  - The school buying calendar fixes the timing: budgets are set in Terms 3–4, pilots run in Terms 1–2, and renewals cluster in Nov–Feb.
- **Translators are a credibility niche.** Even at full cost (A$8k + A$650/mo) they move M36 cash by only about ±A$6k. Launch them lean, after schools, as the founder asked.

---

## 4. Market sizing

### Global solo learners
- **Exam takers:**
  - JLPT: about **1.94M applicants in 2025**, a record.
  - HSK: about **719k candidates in 2024**, with 750–800k expected in 2025; adults aged 19–45 are about 60% of new candidates.
- **Communities:** r/languagelearning about 3.4M members; r/LearnJapanese about 727k.
- **Willingness to pay:**
  - Serious learners pay **US$90–150 a year per tool**, and US$150–499 for lifetime plans.
  - Japanese learners often stack tools worth about US$230 a year.
- **Conversion benchmarks:**
  - Freemium converts about **2–5%**; a hard paywall about 10.7% (RevenueCat).
  - About 8.6% of Duolingo's MAU pay, at a scale we will never have.
- **Retention:** first-year annual renewal is about **28–31%**. That is equivalent to about 9.5% monthly churn, which is why the base uses 9%.
- **Serviceable estimate (E):** the paying market for serious zh/ja tools is likely in the low hundreds of thousands of people worldwide. Reaching 1,078 payers by Dec 2029 (base) is about 0.1–0.5% of that.

### Australian schools
- **Scale:** 4.16M students in 9,673 schools (ABS 2025). Independent schools grew 15.3% from 2021 to 2025.
- **Japanese:** about 415k learners in Australia (Japan Foundation). Most are in primary, so we estimate **about 120–150k secondary learners (E)**.
- **Senior certificates:** about **5,000–7,000 Year 11–12 students take Chinese or Japanese (E)**. Examples: NSW HSC 2025 Japanese Continuers about 795; QLD QCE 2024 Japanese 1,188.
- **EAL/D:** NSW public schools alone have 205,555 EAL/D learners (2025). This is potentially larger than zh + ja combined, but it needs English content tuned to school topics.
- **Price anchor:** **A$10–25 per student per year** (Education Perfect from about A$15 [unverified]; LiteracyPlanet A$15).
- **Illustrative serviceable market (E):** 1,000 secondary schools teaching Japanese or Chinese × about A$1,700 ACV ≈ A$1.7M a year.

### Australian translators and candidates
- **Practitioners:** 8,803 NAATI-certified practitioners hold 13,382 credentials (FY2024-25). By our estimate (E), about 1,000–2,000 are Chinese and 100–300 are Japanese.
- **Tests:** NAATI ran 29,971 tests in FY2024-25. About 2,500 were certification tests and about 27,000 (E) were CCL.
- **Spend:** a working translator spends about A$200–600 a year on PD (E). The CT test fee is A$605 per direction.
- **Size of the niche (E):** 10% of 1,500 zh/ja practitioners at A$15 a month is about A$27k a year. That makes translators a credibility niche, not a revenue engine.

---

## 5. Competition (summary; full tables in [[business/market-research]])

| Band | Examples (USD/yr) | Our stance |
|---|---|---|
| Utility SRS | Bunpro ~$50, renshuu $49.99, Readlang $48 | **Core at US$49 sits here**, with much more than an SRS (matched tests, daily plan, knowledge tracking) |
| Content / immersion | LingQ $119.99, Satori $89.99, Skritter $99.99, Migaku $96, Du Chinese $119.99 | **Pro at US$89 sits at the bottom of this band**, just under Satori |
| AI-heavy | Duolingo Max ~$168, Speak $164.99, Langua $149.99–199.99 | Below this band; AI cost is bundled, not the headline |
| Closest hybrid | Mandarin Temple Pro $15/mo, Pro Plus $27/mo with an AI-credit allowance and top-ups for paid members only | Our credit design follows its pattern, plus packs that never expire |
| AU schools | Education Perfect (incumbent, ~A$15/student [unverified]), Languagenut (site licence), Duolingo for Schools (free) | A$15/student, with zh/ja depth and LLM translation feedback the incumbents lack |
| Translators | Trados ~US$408–564/yr, memoQ ~US$400/yr (tools); PD courses A$49–£299 | Priced as terminology currency + PD (A$219/yr), not as a CAT tool |

---

## 6. Unit economics

### 6.1 Solo Core and Pro (A$ per payer per month, ex-GST)

| Line | Core | Pro | Blended (50% Core) | Basis |
|---|---|---|---|---|
| Subscription ARPU | 6.93 | 10.97 | 8.95 | Plan mix (E). Core: 50% monthly at 8.17, 50% annual at 5.68. Pro: 40% monthly at 13.63, 45% annual at 9.77, 15% founding/student at 7.50 |
| Credit packs | 0.60 | 0.60 | 0.60 | E. Unchanged from v2 although the Study Pass is retired: Core payers have no allowance, so they are the likelier pack buyers |
| Payment fees | −0.65 | −0.78 | −0.72 | Per charge: 70% MoR at 5% + A$0.74 (unverified), 30% Stripe AU at 2.35% + A$0.30 (1.65% + 0.7% Billing); annual fees spread over 12 months |
| Variable AI cost | −0.15 | −0.75 | −0.45 | Core: worst case, DT at the 5-a-day cap at about A$0.001 a grade. Pro: v2 buffer (60% light A$0.20, 30% typical A$0.43, 10% heavy A$4.75; heavy is now ≤A$3.06) for unmeasured production DT cost |
| Incremental infrastructure | −0.08 | −0.08 | −0.08 | E |
| **Contribution** | **6.65** (88%) | **9.96** (86%) | **8.30** (87%) | v2 Pro-only: 11.57 |

The blended contribution moves with the Core share: at 30% Core it is about A$8.97, at 70% about A$7.64.

**Lifetime value (blended contribution ÷ monthly churn):**

| Scenario | Monthly churn | LTV (blended) | Core / Pro |
|---|---|---|---|
| Base | 9% | **A$92** | A$74 / A$111 |
| Optimistic | 7% | A$119 | A$95 / A$142 |
| Conservative | 11% | A$75 | A$60 / A$91 |

**Customer acquisition cost by channel (base churn 9%, blended LTV A$92):**

| Channel | CAC | Payback | LTV/CAC | Pays back? |
|---|---|---|---|---|
| Organic (community, SEO comparison pages, free tools) | ~A$5 (E; founder time excluded) | 0.6 months | 18× | Yes |
| Affiliate/creator at 25% of first-year revenue (A$71.9 blended: (8.95 + 0.60) × 7.53 churn-weighted months) | A$18.00 | 2.2 months | 5.1× | Yes; the cost scales with revenue, so the ratio holds at any price |
| Reddit ads | A$243 (US$165) | 29 months | **0.38×** | No |
| YouTube sponsorship | A$353 (US$240) | 43 months | **0.26×** | No |
| **Blended 70 / 25 / 5** (5% Reddit) | **≈A$20** by channel; the model keeps A$22 | 2.7 months at A$22 | 4.2× at A$22 | Yes, while paid stays at 5% or less |

**Paid ads lose even more money at these prices.** Reddit and YouTube were already below 1× at v2 (0.53× and 0.36×); with blended LTV at A$92 they fall to 0.38× and 0.26×. Even if Core's conversion uplift cut the cost per payer of paid channels by a quarter, they would reach only about 0.5× (Reddit) and 0.35× (YouTube). Paid acquisition would need a CAC under about A$31 to reach 3×. Growth has to come from organic channels and affiliates until LTV is measured.

### 6.2 Other units

| Unit | Revenue (ex-GST) | Contribution | Churn | LTV | CAC | Payback |
|---|---|---|---|---|---|---|
| School (blended ACV: 70% Department at about 120 students plus Senior add-on and top-ups, A$2,100; 30% Class or small department, about A$800) | **A$1,700/yr** | A$1,633/yr (96%) | 15%/yr | A$6,056 (5-year cap); A$4,982 at 25% churn | ~A$750 (A$7.5k/yr events and pilots ÷ 10 new schools) | 5.5 months |
| Tutor (15 students: A$39 + 5 × A$3, GST-incl.) | A$49.09/mo | A$46.52 (95%) | 5%/mo | A$930 | A$50 | 1.1 months |
| Translator Professional (mix of monthly and launch-annual) | A$17.50/mo | A$13.85 (79%) | 5%/mo | A$277 | A$30 | 2.2 months |
| CT Exam Pass (A$79) | A$71.82 one-off | A$66.22 (92%) | n/a | A$66 | A$30 | immediate |

### 6.3 Content amortisation

| Item | Cost | Paid back by |
|---|---|---|
| Fill the zh/ja/en catalogue gap (AI) | A$3,000 | 361 payer-months (33 base-LTV payers) |
| **Native QA of the core catalogue and answer explanations, Y1 (new)**: 120 h × A$60 | **A$7,000** | 843 payer-months (76 payers) |
| New target language, one L1 (AI A$1,250 + 40 h QA) | A$3,650 (E) | 40 base-LTV payers |
| Each additional L1 | A$235 | 3 payers |
| School curriculum packs, zh + ja (AI about A$430 + 160 h teacher review) | A$10,000 (E) | 6 school-years |
| Translator domain packs, lean: 3 domains × 2 directions (AI about A$810 + 40 h NAATI-level review) | A$4,000 (E) | 289 Professional-months |

Machine generation is trivially cheap. **Budget reviewer hours, not tokens.**

---

## 7. Cost base (solo founder, A$/month)

| Item | Y1 |
|---|---|
| Infrastructure (Supabase, Railway, SMTP, domain) | 160 |
| AI/dev tools (Claude Max for `claude -p` authoring, OpenRouter dev) | 330 (E) |
| SaaS (email marketing, analytics, workspace) | 70 (E) |
| Accounting (Xero + accountant, BAS) | 260 (E) |
| Legal (T&Cs and privacy policy, A$3k amortised) | 250 (E) |
| Insurance (PI, public liability, cyber) | 180 (E) |
| Fixed marketing (SEO tools, content, community) | 300 (E) |
| Company admin | 50 (E) |
| **Contingency / contractor cover for bus factor (new)** | **150 (E)** |
| **Y1 total** | **1,750/mo ≈ A$21k/yr** |

**One-offs:**
- M1: A$3k content fill.
- M1–M6: A$7k native QA.
- M2: A$2k Children's Online Privacy Code and age-gate legal review.

**Step-ups:**
- Y2: +A$300 a month; Y3: a further +A$400.
- **Schools** (from the G1 build): A$22.5k one-off, made up of A$10k curriculum tagging and review, A$5k privacy/DPA/PIA legal and A$7.5k ST4S (E). Then +A$875 a month from pilots, made up of A$100 AU tenant hosting, A$150 cyber step-up and A$625 conferences. +A$500 a month once there are 25 or more schools.
- **Translators (lean):** A$4k one-off, then +A$250 a month.

---

## 8. 36-month scenarios (Jan 2027 = M1 … Dec 2029 = M36)

**Model basis.**
- **Revenue** is recognised monthly. Annual prepayments would bring cash forward, so cash is understated, which is the conservative choice.
- **Lifetime seats** are counted as cash when received. They are excluded from operating break-even and ramen tests, and in the statutory accounts they are deferred revenue.
- **Founder pay** is excluded; ramen is tested separately (§9).
- **Model file:** `wiki/business/model/financial_model.py` (v3, Core + Pro; run `python3 -I wiki/business/model/financial_model.py` for the scenarios and sensitivity table).
- **Solo revenue** uses the blended v3 unit economics in §6.1 (50% of payers on Core).

### Assumptions

| | Conservative | Base | Optimistic |
|---|---|---|---|
| Free sign-ups in M1; monthly growth to M24 / after | 200; 6% / 2% | 400; 8% / 3% | 600; 10% / 4% |
| Sign-up → paid, Pro-only baseline | 2.0% | **3.0%** | 4.5% |
| Conversion uplift from adding Core (applied to the line above) | ×1.33 (2.7%) | **×1.33 (4.0%)** | ×1.33 (6.0%) |
| Share of solo payers on Core | 50% | **50%** | 50% |
| Solo monthly churn | 11% | **9%** | 7% |
| Founding members (M1–3) / lifetime seats (M1–6) | 20 / 10 | **40 / 25** | 100 / 60 |
| Variable CAC per solo payer | A$28 | A$22 | A$18 |
| Tutors: launch, new per month | M13, 1 | M13, 2 | M13, 4 |
| Schools: build start; paid schools | never (G1 missed) | Jul 2028; 3 independents mid-2029; about 12 in 2030 | Jul 2027; 4 mid-2028; 20 more in 2029 |
| Translators: launch; Pro subs and Exam Passes per month | never | Jul 2029 lean; 4 and 4 | Jul 2028 full; 8 and 6 |
| Fixed-cost response | −A$780/mo from M7 | none | none |

### Conservative (solo + tutors; cost cuts at M6)

| Qtr | Solo payers | Tutors | MRR end | Revenue | Costs | Net | Cumulative cash |
|---|---|---|---|---|---|---|---|
| Q1'27 | 33 | 0 | 316 | 2,589 | 14,873 | −12,285 | −12,285 |
| Q2'27 | 41 | 0 | 396 | 3,045 | 9,470 | −6,425 | −18,710 |
| Q3'27 | 51 | 0 | 485 | 1,364 | 3,774 | −2,411 | −21,121 |
| Q4'27 | 62 | 0 | 587 | 1,657 | 3,941 | −2,284 | −23,405 |
| Q1'28 | 74 | 3 | 846 | 2,281 | 5,203 | −2,922 | −26,327 |
| Q2'28 | 89 | 5 | 1,106 | 3,058 | 5,457 | −2,399 | −28,726 |
| Q3'28 | 106 | 7 | 1,374 | 3,852 | 5,752 | −1,900 | −30,626 |
| Q4'28 | 126 | 9 | 1,658 | 4,686 | 6,098 | −1,412 | −32,038 |
| Q1'29 | 146 | 11 | 1,920 | 5,507 | 7,550 | −2,043 | −34,082 |
| Q2'29 | 163 | 12 | 2,150 | 6,225 | 7,737 | −1,511 | −35,593 |
| Q3'29 | 179 | 13 | 2,357 | 6,867 | 7,922 | −1,055 | −36,648 |
| Q4'29 | 194 | 14 | 2,548 | 7,456 | 8,109 | −654 | **−37,301** |

- **Annual revenue:** A$8.7k (2027), A$13.9k (2028), A$26.1k (2029). **Annual costs:** A$32.1k, A$22.5k, A$31.3k.
- The conservative case does not reach operating break-even within 36 months. Losses shrink every quarter in 2029 (−A$0.7k in Q4), so the trough is at M36 and close to its floor.
- Without the M6 cost cut, it reaches **−A$60.7k by M36**. The cost-cut trigger is therefore part of the plan, not an option.

### Base

| Qtr | Solo payers | Schools | Tutors | Translators | MRR end | Revenue | Costs | Net | Cumulative cash |
|---|---|---|---|---|---|---|---|---|---|
| Q1'27 | 84 | 0 | 0 | 0 | 802 | 6,476 | 15,994 | −9,518 | −9,518 |
| Q2'27 | 123 | 0 | 0 | 0 | 1,176 | 7,992 | 10,624 | −2,632 | −12,149 |
| Q3'27 | 168 | 0 | 0 | 0 | 1,607 | 4,375 | 7,663 | −3,288 | −15,438 |
| Q4'27 | 222 | 0 | 0 | 0 | 2,118 | 5,821 | 8,322 | −2,500 | −17,938 |
| Q1'28 | 287 | 0 | 6 | 0 | 3,019 | 8,137 | 10,371 | −2,234 | −20,171 |
| Q2'28 | 367 | 0 | 11 | 0 | 4,024 | 11,038 | 11,435 | −397 | −20,569 |
| Q3'28 | 466 | 0 | 15 | 0 | 5,180 | 14,343 | 22,755 | −8,411 | −28,980 |
| Q4'28 | 591 | 0 | 18 | 0 | 6,543 | 18,213 | 26,899 | −8,686 | **−37,666** |
| Q1'29 | 718 | 0 | 21 | 0 | 7,910 | 22,385 | 19,556 | 2,829 | −34,837 |
| Q2'29 | 839 | 0 | 24 | 0 | 9,197 | 26,316 | 24,645 | 1,671 | −33,166 |
| Q3'29 | 958 | 2 | 26 | 11 | 10,927 | 32,067 | 23,425 | 8,642 | −24,524 |
| Q4'29 | 1,078 | 3 | 28 | 21 | 12,480 | 36,896 | 24,748 | 12,147 | **−12,377** |

- **Annual revenue:** A$24.7k (2027), A$51.7k (2028), A$117.7k (2029).
- **Annual costs:** A$42.6k, A$71.5k, A$92.4k.
- Operating break-even (excluding lifetime cash) is reached at **M18 (Jun 2028)**. The cash trough is **−A$37.7k in Dec 2028 (M24)**, driven by the school build. The operating surplus is about A$4.4k a month at M36.
- More payers (1,078 against 811 in v2) do not make up for lower revenue per payer: MRR at M36 is A$12.5k against A$13.0k, and variable costs (fees, CAC) scale with payer count.
- **48-month extension** (the model file as it stands, which adds no schools after M34, so school revenue in 2030 is understated): by Dec 2030 there are 1,613 solo payers, MRR is A$18.3k and cumulative cash is about +A$56k. Ramen is reached at **M46 (Oct 2030)**.

### Optimistic

| Qtr | Solo payers | Schools | Tutors | Translators | MRR end | Revenue | Costs | Net | Cumulative cash |
|---|---|---|---|---|---|---|---|---|---|
| Q1'27 | 204 | 0 | 0 | 0 | 1,952 | 15,557 | 18,228 | −2,671 | −2,671 |
| Q2'27 | 312 | 0 | 0 | 0 | 2,984 | 19,505 | 12,692 | 6,813 | 4,142 |
| Q3'27 | 448 | 0 | 0 | 0 | 4,283 | 11,480 | 20,618 | −9,138 | −4,996 |
| Q4'27 | 623 | 0 | 0 | 0 | 5,950 | 16,087 | 24,974 | −8,887 | −13,883 |
| Q1'28 | 850 | 0 | 11 | 0 | 8,680 | 23,201 | 19,107 | 4,093 | −9,789 |
| Q2'28 | 1,149 | 0 | 21 | 0 | 12,010 | 32,543 | 30,430 | 2,113 | −7,676 |
| Q3'28 | 1,542 | 2 | 30 | 23 | 16,870 | 46,976 | 30,310 | 16,665 | 8,989 |
| Q4'28 | 2,064 | 4 | 37 | 43 | 22,843 | 63,701 | 36,352 | 27,349 | 36,338 |
| Q1'29 | 2,634 | 16 | 43 | 61 | 30,554 | 85,200 | 43,008 | 42,192 | 78,530 |
| Q2'29 | 3,215 | 20 | 48 | 77 | 37,205 | 106,238 | 47,844 | 58,394 | 136,924 |
| Q3'29 | 3,819 | 21 | 53 | 92 | 43,584 | 125,617 | 52,939 | 72,678 | 209,602 |
| Q4'29 | 4,459 | 24 | 57 | 104 | 50,528 | 145,855 | 65,963 | 79,892 | **289,494** |

- **Annual revenue:** A$62.6k (2027), A$166.4k (2028), A$462.9k (2029). **Annual costs:** A$76.5k, A$116.2k, A$209.8k.
- Operating break-even at **M7 (Jul 2027)**; trough −A$13.9k in Dec 2027; ramen at **M22 (Oct 2028)**.
- The optimistic case outgrows one person by about Q4 2028; Gate G3 (first hire) is passed at about M24.

### Sensitivity (base; M36 cash −A$12.4k, trough −A$37.7k, break-even M18)

No flex reaches ramen within 36 months, so the last column shows the operating break-even month instead.

| Rank | Assumption flexed | M36 cash change (resulting M36 cash) | Trough | Break-even |
|---|---|---|---|---|
| 1 | Sign-ups in M1: 250 / 600 | −A$30.3k (−A$42.7k) / +A$40.4k (+A$28.0k) | −A$51.4k / −A$27.0k | M22 / M15 |
| 2 | Variable CAC ×2 (more paid spend) | −A$54.5k (−A$66.8k) | −A$71.3k | M32 |
| 3 | Sign-up growth to M24: 6% / 10% | −A$21.0k (−A$33.4k) / +A$29.5k (+A$17.1k) | −A$43.7k / −A$33.9k | M20 / M17 |
| 4 | Conversion (Pro-only baseline): 2% / 4% | −A$26.9k (−A$39.3k) / +A$26.9k (+A$14.5k) | −A$49.3k / −A$30.4k | M21 / M16 |
| 5 | ARPU (plan mix, discounting, PPP) ±15% | ∓A$26.2k (−A$38.5k / +A$13.8k) | −A$49.5k / −A$29.5k | M21 / M16 |
| 6 | **Conversion uplift from Core: none (×1.0) / ×1.5** (new) | −A$20.0k (−A$32.4k) / +A$10.3k (−A$2.1k) | −A$45.2k / −A$34.6k | M20 / M17 |
| 7 | Churn: 11% / 7% | −A$14.4k (−A$26.8k) / +A$17.8k (+A$5.5k) | −A$42.3k / −A$32.8k | M20 / M17 |
| 8 | Schools off (within 36 months) | +A$31.1k (+A$18.7k; the payback lands after M36) | −A$20.6k | M18 |
| 9 | Tutors ×2 | +A$17.2k (+A$4.9k) | −A$33.7k | M17 |
| 10 | **Core share of solo payers: 30% / 70%** (new) | +A$10.9k (−A$1.5k) / −A$10.9k (−A$23.3k) | −A$33.8k / −A$41.8k | M17 / M19 |
| 11 | No lifetime seats | −A$9.3k (−A$21.7k) | −A$47.1k | M18 |
| 12 | Translators off / at full cost | +A$4.3k / −A$6.4k | unchanged | M18 |

**What follows from the sensitivity table:**
- Spend founder time on top-of-funnel growth.
- **Measure conversion and the Core share from the first month** (D19). Across their tested ranges, the uplift swings M36 cash by about A$30k and the Core share by about A$22k. If Core takes most payers without lifting conversion, act on the trigger.
- Protect price: annual by default, few discounts, and PPP only once there is data.
- Never scale paid ads before LTV is measured. Doubling CAC is now the single worst case.
- Keep the tutor wedge cheap and early.

---

## 9. Break-even and ramen

**Steady-state contribution per solo payer.** This is contribution minus the cost of replacing churned payers (churn × CAC).

| Scenario | Calculation | Per payer per month |
|---|---|---|
| Base | 8.30 − 0.09 × 22 | **A$6.32** |
| Conservative | 8.30 − 0.11 × 28 | A$5.22 |
| Optimistic | 8.30 − 0.07 × 18 | A$7.04 |

(v2, Pro only: A$9.59 base. Each v3 payer carries about a third less of the fixed costs, so more payers are needed.)

| Fixed cost base (A$/mo) | Solo payers needed (base) | Conservative | Optimistic |
|---|---|---|---|
| Y1: 1,750 | **277** | 335 (186 after the cut to A$970) | 249 |
| Y2, solo only: 2,050 | 324 | | |
| Y3, solo only: 2,450 | 388 | 469 (320 after the cut) | |
| Y3, all segments: 3,575 (4,075 with ≥25 schools) | 566 / 645; or for example 10 schools + 20 tutors + 30 translators + 170 solo | | |

(The mixed examples use per-unit contribution net of replacement CAC: school about A$127 a month, tutor about A$44, translator about A$12.)

**Ramen.** Assume a founder salary of A$80k plus 12% super = A$7,467 a month.

| Cost base | Calculation | Solo payers needed |
|---|---|---|
| Y1 | (1,750 + 7,467) ÷ 6.32 | **1,458** |
| Y3, all segments | (3,575 + 7,467) ÷ 6.32 | **1,747**, or about 1,200 solo + 12 schools + 30 tutors + 40 translators |

The base case has 1,078 solo payers at M36, so ramen falls outside the 36-month window (M46 in the 48-month run).

**Founder funding need:**
- **Base:** about **A$50k of business cash**: the trough of −A$37.7k plus about A$12k of buffer. The buffer is sized so that the base case still fits if Core brings no conversion uplift (trough −A$45.2k) or lifetime seats do not sell (−A$47.1k, leaving a thin margin). Add personal runway to about M46.
- **Conservative:** about A$40k (trough −A$37.3k at M36, still falling slowly), provided the cost-cut trigger is honoured.
- **Lifetime seats:** without them, the base trough deepens to −A$47.1k.
- **Why more than v2's A$40k:** the cheaper ladder lowers contribution per payer by 28%, which deepens the trough by about A$8k even with the assumed 1.33× conversion uplift.

---

## 10. Risks and mitigations

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| 1 | **Top-of-funnel volume.** There are 18 users today, and the base assumes 400 sign-ups in M1 growing 8% a month. | One of the largest swings in the model (−A$30k at 250 in M1) | Build a ≥500 waitlist before launch. Founder-led community work on Reddit and Discord. "X vs Y" SEO pages. A public sample test with no login. Affiliate revenue share. Re-run the model at day 90. Cost-cut trigger at M6. |
| 2 | **Content quality and catalogue depth.** ja 83 tests, zh 274; `answer_explanation` NULL on all 1,424 questions; LLM errors drive serious learners away. | Churn, refunds, reputation | A$3k content fill + A$7k native QA before and after launch. Answer explanations. A "report an error" button with credit refunds. Show catalogue counts per band rather than promising "unlimited". |
| 3 | **Price realisation, conversion and churn** | ±A$14–27k each | Annual by default. Discounts limited to founding and one November sale. 21-day trial re-offered at day 45. PPP only after 3 months of data. |
| 4 | **Compliance.** Children's Online Privacy Code (10 Dec 2026, applies to solo too); APP 8 (DT on `:free` and DeepSeek endpoints); ST4S; unfair trading practices law (1 Jul 2027); ACL claims and unfair contract terms | Blocks schools; regulator and reputation risk | Age gate and under-18 defaults at launch. DT only on ZDR providers, disclosed. Easy cancellation and reminders. Purchased credits never expire. Lifetime defined in the terms. ST4S Readiness Check started early. No "NAATI-approved" or "replaces WaniKani" claims. |
| 5 | **Founder bandwidth and bus factor.** One person does development, content QA, support, sales and community. | Slips the school timeline; schools ask about continuity | Gates stop parallel bets. A$150/mo contingency for contractor cover. Runbooks. Tutors before schools. Hire at G3. |
| 6 | Payment fees and MoR terms unverified (Paddle has separate terms under US$10; Stripe Managed Payments about +3.5%). **Core monthly (US$6) and Pro monthly (US$10) now sit at or below that line**, and the fixed per-charge fee is about 15% of Core monthly's net revenue through an MoR. | ±A$0.4–1.0 per payer per month | Verify before G0. If small-ticket terms are poor, run packs through Stripe or raise the smallest pack to US$9.99, and push Core buyers to annual billing (one charge a year). |
| 7 | Production DT cost unmeasured | Variable cost could be understated | Fix `llm_calls` cost logging first. Per-tier daily DT caps and token budgets. Re-price after 30 days of data. |
| 8 | Free chatbots commoditise DT and custom content | Weak differentiation | Lead with measurement (placement, ELO, BKT, plan) and curated audio. |
| 9 | School sales cycle (budgets set in Terms 3–4; ST4S queue) | School revenue lands in 2030 (base) | Tutors, independents and Catholic schools first. Term Pilot timed for conversion in Term 4. Small Class plan with no procurement cliff. |
| 10 | **The cheaper ladder depends on a conversion uplift (new, v3).** The model assumes Core lifts sign-up → paid by 1.33×. There is no measured baseline yet. | With no uplift, base M36 cash is −A$32.4k (−A$20k) and the trough −A$45.2k | Measure in the first 90 days (D19). Compare against the 3.0% Pro-only baseline. If the uplift is not there, apply the D19 trigger (raise Core to US$7 / A$9.99 or move features up to Pro for new subscribers). |
| 11 | **Core cannibalises Pro (new, v3).** Learners who would have paid for Pro take Core instead, especially light DT users who never touch the credit allowance. | At 70% Core, base M36 cash is −A$23.3k (−A$10.9k) | Keep a clear dividing line (Core = study loop; Pro = production + personalisation). The 21-day trial is a Pro trial, so learners feel DT volume and the allowance before choosing. Show the Pro upgrade at the DT cap and when a credit action is quoted. D19 trigger if Core passes 60% of payers. |

---

## 11. Next 90 days (17 Nov 2026 → mid-Feb 2027)

| Window | Work | Gate evidence |
|---|---|---|
| Weeks 1–2 | Fix `llm_calls` cost logging for DT. Move DT grading to ZDR providers only. Remove the hardcoded `p_was_free_test=True` and build the Stripe webhook ([[business/pricing-plan.tech]] §API). Register for GST. | DT cost per call measured |
| Weeks 2–6 | Entitlements layer. Subscriptions via the chosen MoR plus Stripe. Credit ledger with three pools. Pricing page. Age gate. Privacy policy and T&Cs, reviewed for unfair contract terms and the Children's Code. | G0 checklist |
| Weeks 1–8 | Content fill (A$3k). Native QA sprint and answer explanations (A$7k over M1–M6). Public sample test. Comparison pages. | ≥200 tests per band for zh and ja |
| Weeks 1–8 | Waitlist and founding offer (US$69/yr, A$99, for Pro). 100 lifetime seats (US$299 / A$449). Community presence. Pricing page with Core and Pro side by side. | Waitlist ≥500 |
| Jan 2027 (M1) | Launch billing. Convert the 18 existing users to founding status (2 free tests a day grandfathered; token balances move 1:1 to purchased credits). | |
| Days 1–90 after launch | Track **the Core share of new payers** and **sign-up → paid** against the 3.0% Pro-only baseline every month (a randomised Pro-only holdout would measure the uplift more cleanly, but it complicates the pricing page; founder's call). | D19 inputs |
| Days 60–90 after launch | Measure sign-ups, conversion, churn and credit burn. Re-run the model. Apply the cost-cut trigger if hit. Apply the D19 trigger if Core is over 60% of payers and conversion is still below 4.0%. Submit the ST4S Readiness Check. Open the tutor waitlist. | Cost-cut trigger / D19 / G1a inputs |

---

## Review notes (red-team corrections)

**Accepted and applied:**
- Churn 9% base (7% optimistic, 11% conservative).
- Conversion 3%; 40 founding members.
- Schools moved later, with build only at G1.
- Founder cash need raised to about A$40k (A$50k in v3).
- Lifetime cash basis stated explicitly.
- Pro allowance text corrected to about 30 custom tests.
- 3,000-credit pack replaced by 2,500 (+25%).
- New-word import at 8 credits.
- DT fair-use caps cut and per-tier token budgets added.
- DT on ZDR providers only.
- Study Pass priced directly. (Superseded: the Study Pass was retired in v3.)
- Tutor plan repriced to A$39 + A$3, GST-inclusive, with seat restrictions.
- School minimum A$750 plus a Class plan.
- Purchased credits never expire.
- A$7k native QA.
- Exam Pass limited to CT candidates, 4 a month.
- Positioning changed to "reading, listening and vocabulary stack".
- Age gate.
- MoR small-ticket terms flagged.

**Additional changes made here (not in the red team):**
- **Tutors launch at M13**, ahead of schools. The class layer costs founder time but no cash, and it is the cheapest B2B revenue. (Confirmed by the founder on 2026-11-17, D12.)
- **Base-case schools follow the gate.** The red team's re-run kept the school build at M13, but G1 is not met until about M19, so the build starts at M19 and broad school revenue moves to 2030.
- **Lifetime seats reduced to 25 in the base**, using the same waitlist-conversion logic as founding members.
- **Translators launch lean** (A$4k + A$250/mo), because at full cost they lose money within 36 months.
- **A$150/mo contingency added** for bus-factor cover.
- **A$2k legal for the Children's Code.**
- **A cost-cut trigger at M6.**

**Partly rejected:**
- **"Keep the free tier at 2 tests a day."** New free users get 1 a day, because the catalogue is shallow and the paywall needs a lever. The 18 existing users keep 2 a day, which removes the visible-downgrade problem.
- **"Professional must be cheaper because the PD log is weak."** The price stays at A$219 (launch A$179). It is repositioned as terminology currency, with the PD log as a retention feature, and remains a founder decision (D15).

## Related Pages
- [[business/pricing-plan]] — Prices, credits, policies, founder decisions
- [[business/pricing-plan.tech]] — Schema, entitlements, Stripe mapping
- [[business/market-research]] — Research appendix with sources
- [[decisions/ADR-047-credits-and-subscription-model]] — The monetisation decision
- [[overview/project]] — What LinguaDojo is
- [[features/token-economy]] — The legacy token system this replaces
- [[features/dual-translation]], [[features/comprehension-tests]], [[features/vocab-dojo]], [[features/study-plans]] — The product being sold
