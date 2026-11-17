---
title: LinguaDojo Business Case
type: overview
status: planned
tech_page: ./pricing-plan.tech.md
last_updated: 2026-11-17
open_questions:
  - "OPEN: Can LinguaDojo reach 400 free sign-ups in its first billing month (Jan 2027) from 18 users today? This is the most influential input; validate it within 90 days of launch and re-run the model."
  - "OPEN: How much business cash will the founder commit? The corrected base case needs about A$40k (trough −A$29k plus a buffer); the conservative case with cost cuts needs about A$32k."
  - "OPEN: Which merchant of record (Paddle, or Stripe Managed Payments if available in AU) will handle global consumer sales, and on what terms for charges under US$10?"
  - "OPEN: What is the ST4S full-assessment fee and queue time? The model assumes A$7.5k (estimate)."
  - "OPEN: What does the final OAIC Children's Online Privacy Code (due 10 Dec 2026) require for 13–17-year-old solo users?"
  - "OPEN: Where are Supabase and Railway hosted today? This is needed before any data-residency claim to schools."
  - "OPEN: What does a DT grade cost in production? llm_calls cost logging is broken for DT (NULL cost_usd, 0 tokens) and grading appears to route to :free models."
---

# LinguaDojo Business Case

All money is in AUD unless marked. FX is 1 USD = A$1.47. Revenue figures are ex-GST. **E** marks an estimate. Market and competitor sources are in [[business/market-research]]. Prices and credit rules are in [[business/pricing-plan]]. The monetisation model is recorded in [[decisions/ADR-047-credits-and-subscription-model]].

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
- **Gross margin** on the solo subscription is about 87% blended (contribution A$11.57 per payer per month).

**How it makes money.**
- **Subscription.** Pro costs **US$12 a month or US$99 a year** (A$17.99 / A$149 including GST). It includes the whole study loop and **300 credits a month**.
- **PAYG credits** pay **only for actions that make a live LLM call**: custom tests, importing a word that is not in the dictionary, DT beyond the fair-use cap, deep re-grades and mock grading. Packs start at US$4.99 / A$7.49 for 500 credits, and purchased credits never expire.
- **Non-subscribers** also get a PAYG route into the core loop: a 7-day Study Pass at US$6.99 / A$9.99.

**Who buys, in what order.** This is the founder's sequence, with one change: tutors become the first B2B step because they are cheap to serve.
1. **Solo learners, worldwide.** Launch Jan 2027.
2. **Tutors and tutoring colleges in Australia.** From Jan 2028. They use the class and assignment layer and need no ST4S assessment.
3. **Australian schools.** The build is committed only at Gate G1 (base case Jul 2028). First paid school revenue is mid-2029 from independent schools; broad revenue starts Term 1 2030.
4. **Translators.** A lean Professional tier and a CT Exam Pass, from Jul 2029 in the base case.

**What the numbers say (corrected model, §8).**

| Scenario | Operating break-even | Cash trough | Cash at M36 (Dec 2029) | MRR at M36 | Ramen profitable |
|---|---|---|---|---|---|
| Conservative (cost cuts at M6) | M35 (Nov 2029) | −A$31.8k | −A$31.7k | A$2.6k | Not within 36 months |
| **Base** | **M16 (Apr 2028)** | **−A$29.3k (Oct 2028)** | **+A$8.4k** | **A$13.0k** | **M40 (Apr 2030)** |
| Optimistic | M5 (May 2027) | −A$7.8k | +A$352.5k | A$52.7k | M21 (Sep 2028) |

- The draft model showed a base of +A$161k at M36. The red team's corrections cut that to +A$8.4k:
  - churn 9% (was 7%)
  - conversion 3% (was 4%)
  - 40 founding members (was 100)
  - schools a year later
  - smaller tutor and translator volumes
  - A$7k of native-speaker QA
- **This is a viable bootstrapped business, but a slow one.** It needs about **A$40k of founder cash** and about 3 years before it pays the founder a salary.
- **The outcome depends mostly on organic sign-up volume and price discipline, not AI cost.**

**Decision asked of the founder.** Approve the hybrid model ([[decisions/ADR-047-credits-and-subscription-model]]) and the launch prices. Commit the business cash. Build billing (Gate G0) for a January 2027 launch.

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
- LinguaDojo costs **US$99/yr**.
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
| 1 | Solo learners | Global; USD default, AUD/EUR/GBP local | Pro subscription, credit packs, Study Pass, lifetime (100 seats) | Jan 2027 (M1) |
| 2a | Tutors and tutoring colleges | AU | Tutor plan (classes, assignments, gradebook) | Jan 2028 (M13) |
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
| **G3: first hire** | about M40 (base), M21 (optimistic) | Operating surplus ≥A$7.5k a month for 3 consecutive months, **and** measured 12-month solo LTV/CAC above 3 | Stay solo and keep the cost base. |

### Why this order holds up
- **Solo comes first** because it needs only billing (about 3–5 solo-dev weeks), which is the shortest path to cash.
- **Tutors come before schools.**
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
- **Serviceable estimate (E):** the paying market for serious zh/ja tools is likely in the low hundreds of thousands of people worldwide. Reaching 811 payers by Dec 2029 (base) is about 0.1–0.5% of that.

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
| Utility SRS | Bunpro ~$50, renshuu $49.99, Readlang $48 | We do more than SRS; above this band |
| Content / immersion | LingQ $119.99, Satori $89.99, Skritter $99.99, Migaku $96, Du Chinese $119.99 | **Pro at US$99 sits here** |
| AI-heavy | Duolingo Max ~$168, Speak $164.99, Langua $149.99–199.99 | Below this band; AI cost is bundled, not the headline |
| Closest hybrid | Mandarin Temple Pro $15/mo, Pro Plus $27/mo with an AI-credit allowance and top-ups for paid members only | Our credit design follows its pattern, plus packs that never expire |
| AU schools | Education Perfect (incumbent, ~A$15/student [unverified]), Languagenut (site licence), Duolingo for Schools (free) | A$15/student, with zh/ja depth and LLM translation feedback the incumbents lack |
| Translators | Trados ~US$408–564/yr, memoQ ~US$400/yr (tools); PD courses A$49–£299 | Priced as terminology currency + PD (A$219/yr), not as a CAT tool |

---

## 6. Unit economics

### 6.1 Solo Pro (A$ per payer per month, ex-GST)

| Line | A$ | Basis |
|---|---|---|
| Subscription ARPU | 12.75 | Plan mix (E): 40% monthly at 16.35, 45% annual at 11.29, 15% founding/student at 7.50 |
| Credit packs + Study Pass | 0.60 | E |
| Payment fees | −0.95 | 70% MoR at 5% + A$0.74 (unverified), 30% Stripe AU at 1.65% + A$0.30 + 0.7% Billing |
| Variable AI cost | −0.75 | 60% light A$0.20, 30% typical A$0.43, 10% heavy A$4.75 (heavy is now ≤A$3.06; kept as a buffer for unmeasured production DT cost) |
| Incremental infrastructure | −0.08 | E |
| **Contribution** | **11.57** | About 87% |

**Lifetime value (contribution ÷ monthly churn):**

| Scenario | Monthly churn | LTV |
|---|---|---|
| Base | 9% | **A$129** |
| Optimistic | 7% | A$165 |
| Conservative | 11% | A$105 |

**Customer acquisition cost by channel (base churn 9%):**

| Channel | CAC | Payback | LTV/CAC |
|---|---|---|---|
| Organic (community, SEO comparison pages, free tools) | ~A$5 (E; founder time excluded) | 0.4 months | 26× |
| Affiliate/creator at 25% of first-year revenue (A$100.5) | A$25.10 | 2.2 months | 5.1× |
| Reddit ads | A$243 (US$165) | 21 months | **0.53×** |
| YouTube sponsorship | A$353 (US$240) | 31 months | **0.36×** |
| **Blended 70 / 25 / 5** | **≈A$22** | 1.9 months | 5.8× |

**Paid ads lose money at these prices.** Growth has to come from organic channels and affiliates until LTV is measured.

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
| Fill the zh/ja/en catalogue gap (AI) | A$3,000 | 259 payer-months (23 base-LTV payers) |
| **Native QA of the core catalogue and answer explanations, Y1 (new)**: 120 h × A$60 | **A$7,000** | 605 payer-months (54 payers) |
| New target language, one L1 (AI A$1,250 + 40 h QA) | A$3,650 (E) | 28 base-LTV payers |
| Each additional L1 | A$235 | 2 payers |
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
- **Model file:** `wiki/business/model/financial_model.py` (corrected v2; run `python3 -I wiki/business/model/financial_model.py` for the scenarios and sensitivity table).

### Assumptions

| | Conservative | Base | Optimistic |
|---|---|---|---|
| Free sign-ups in M1; monthly growth to M24 / after | 200; 6% / 2% | 400; 8% / 3% | 600; 10% / 4% |
| Sign-up → paid | 2.0% | **3.0%** | 4.5% |
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
| Q1'27 | 29 | 0 | 391 | 2,745 | 14,782 | −12,037 | −12,037 |
| Q2'27 | 34 | 0 | 458 | 3,242 | 9,367 | −6,125 | −18,162 |
| Q3'27 | 40 | 0 | 539 | 1,532 | 3,643 | −2,110 | −20,272 |
| Q4'27 | 48 | 0 | 638 | 1,811 | 3,776 | −1,966 | −22,238 |
| Q1'28 | 57 | 3 | 897 | 2,432 | 5,001 | −2,570 | −24,808 |
| Q2'28 | 67 | 5 | 1,159 | 3,214 | 5,212 | −1,998 | −26,806 |
| Q3'28 | 80 | 7 | 1,433 | 4,021 | 5,456 | −1,435 | −28,240 |
| Q4'28 | 95 | 9 | 1,724 | 4,876 | 5,742 | −866 | −29,107 |
| Q1'29 | 110 | 11 | 1,994 | 5,721 | 7,159 | −1,437 | −30,544 |
| Q2'29 | 123 | 12 | 2,231 | 6,462 | 7,323 | −860 | −31,405 |
| Q3'29 | 135 | 13 | 2,445 | 7,125 | 7,484 | −359 | −31,763 |
| Q4'29 | 146 | 14 | 2,643 | 7,734 | 7,645 | 90 | **−31,674** |

Without the M6 cost cut, the conservative case reaches **−A$55.1k by M36 and never breaks even**. The cost-cut trigger is therefore part of the plan, not an option.

### Base

| Qtr | Solo payers | Schools | Tutors | Translators | MRR end | Revenue | Costs | Net | Cumulative cash |
|---|---|---|---|---|---|---|---|---|---|
| Q1'27 | 72 | 0 | 0 | 0 | 964 | 6,808 | 15,767 | −8,959 | −8,959 |
| Q2'27 | 99 | 0 | 0 | 0 | 1,327 | 8,453 | 10,357 | −1,904 | −10,864 |
| Q3'27 | 132 | 0 | 0 | 0 | 1,757 | 4,823 | 7,310 | −2,486 | −13,350 |
| Q4'27 | 171 | 0 | 0 | 0 | 2,277 | 6,287 | 7,858 | −1,571 | −14,921 |
| Q1'28 | 219 | 0 | 6 | 0 | 3,197 | 8,649 | 9,772 | −1,122 | −16,044 |
| Q2'28 | 278 | 0 | 11 | 0 | 4,230 | 11,627 | 10,668 | 959 | −15,085 |
| Q3'28 | 352 | 0 | 15 | 0 | 5,427 | 15,043 | 21,777 | −6,734 | −21,819 |
| Q4'28 | 445 | 0 | 18 | 0 | 6,845 | 19,062 | 25,657 | −6,596 | **−28,414** |
| Q1'29 | 541 | 0 | 21 | 0 | 8,270 | 23,408 | 18,144 | 5,264 | −23,150 |
| Q2'29 | 632 | 0 | 24 | 0 | 9,612 | 27,507 | 23,115 | 4,392 | −18,758 |
| Q3'29 | 721 | 2 | 26 | 11 | 11,398 | 33,423 | 21,762 | 11,661 | −7,097 |
| Q4'29 | 811 | 3 | 28 | 21 | 13,007 | 38,419 | 22,938 | 15,482 | **8,385** |

- **Annual revenue:** A$26.4k (2027), A$54.4k (2028), A$122.8k (2029).
- **Annual costs:** A$41.3k, A$67.9k, A$86.0k.
- The monthly trough is **−A$29.3k in Oct 2028 (M22)**, driven by the school build.
- **48-month extension:** by Dec 2030 there are 1,213 solo payers and about 12 schools. MRR reaches A$20.5k and cumulative cash about +A$106k. Ramen is reached at M40.

### Optimistic

| Qtr | Solo payers | Schools | Tutors | Translators | MRR end | Revenue | Costs | Net | Cumulative cash |
|---|---|---|---|---|---|---|---|---|---|
| Q1'27 | 177 | 0 | 0 | 0 | 2,360 | 16,388 | 17,838 | −1,450 | −1,450 |
| Q2'27 | 254 | 0 | 0 | 0 | 3,384 | 20,705 | 12,214 | 8,492 | 7,042 |
| Q3'27 | 352 | 0 | 0 | 0 | 4,699 | 12,707 | 19,930 | −7,223 | −181 |
| Q4'27 | 480 | 0 | 0 | 0 | 6,412 | 17,421 | 24,002 | −6,581 | −6,762 |
| Q1'28 | 649 | 0 | 11 | 0 | 9,221 | 24,735 | 17,766 | 6,970 | 208 |
| Q2'28 | 871 | 0 | 21 | 0 | 12,670 | 34,392 | 28,602 | 5,791 | 5,999 |
| Q3'28 | 1,166 | 2 | 30 | 23 | 17,699 | 49,282 | 27,840 | 21,442 | 27,441 |
| Q4'28 | 1,557 | 4 | 37 | 43 | 23,909 | 66,645 | 33,030 | 33,615 | 61,056 |
| Q1'29 | 1,985 | 16 | 43 | 61 | 31,883 | 88,922 | 39,104 | 49,818 | 110,874 |
| Q2'29 | 2,421 | 20 | 48 | 77 | 38,804 | 110,762 | 43,514 | 67,248 | 178,122 |
| Q3'29 | 2,874 | 21 | 53 | 92 | 45,466 | 130,977 | 48,116 | 82,861 | 260,983 |
| Q4'29 | 3,354 | 24 | 57 | 104 | 52,713 | 152,103 | 60,575 | 91,527 | **352,510** |

The optimistic case outgrows one person by about Q3 2028; Gate G3 (first hire) is passed at about M21.

### Sensitivity (base; M36 cash +A$8.4k, trough −A$29.3k)

| Rank | Assumption flexed | M36 cash change | Trough | Ramen within 36 months? |
|---|---|---|---|---|
| 1 | Sign-ups in M1: 250 / 600 | −A$37.6k / +A$50.2k | −A$41.9k / −A$15.8k | no / M34 |
| 2 | Variable CAC ×2 (more paid spend) | −A$41.2k | −A$47.6k | no |
| 3 | Sign-up growth to M24: 6% / 10% | −A$26.7k / +A$37.8k | −A$34.2k / −A$24.3k | no / M34 |
| 4 | Conversion: 2% / 4% | −A$33.5k / +A$33.5k | −A$39.7k / −A$20.3k | no / M36 |
| 5 | ARPU (plan mix, discounting, PPP) ±15% | ∓A$27.9k | −A$38.6k / −A$21.0k | no |
| 6 | Churn: 11% / 7% | −A$15.3k / +A$19.0k | −A$33.5k / −A$24.7k | no / M36 |
| 7 | Schools off (within 36 months) | +A$31.1k (the payback lands after M36) | −A$16.0k | no |
| 8 | Tutors ×2 | +A$17.2k | −A$25.9k | no |
| 9 | No lifetime seats | −A$9.1k | −A$38.7k | no |
| 10 | Translators off / at full cost | +A$4.3k / −A$6.4k | unchanged | no |

**What follows from the sensitivity table:**
- Spend founder time on top-of-funnel growth.
- Protect price: annual by default, few discounts, and PPP only once there is data.
- Never scale paid ads before LTV is measured.
- Keep the tutor wedge cheap and early.

---

## 9. Break-even and ramen

**Steady-state contribution per solo payer.** This is contribution minus the cost of replacing churned payers (churn × CAC).

| Scenario | Calculation | Per payer per month |
|---|---|---|
| Base | 11.57 − 0.09 × 22 | **A$9.59** |
| Conservative | 11.57 − 0.11 × 28 | A$8.49 |
| Optimistic | 11.57 − 0.07 × 18 | A$10.31 |

| Fixed cost base (A$/mo) | Solo payers needed (base) | Conservative | Optimistic |
|---|---|---|---|
| Y1: 1,750 | **183** | 207 (115 after the cut to A$970) | 170 |
| Y2, solo only: 2,050 | 214 | | |
| Y3, solo only: 2,450 | 256 | 289 (197 after the cut) | |
| Y3, all segments: 3,575 (4,075 with ≥25 schools) | 373 / 425; or for example 10 schools + 20 tutors + 30 translators + 120 solo | | |

**Ramen.** Assume a founder salary of A$80k plus 12% super = A$7,467 a month.

| Cost base | Calculation | Solo payers needed |
|---|---|---|
| Y1 | (1,750 + 7,467) ÷ 9.59 | **961** |
| Y3, all segments | (3,575 + 7,467) ÷ 9.59 | **1,151**, or about 800 solo + 12 schools + 30 tutors + 40 translators |

**Founder funding need:**
- **Base:** about **A$40k of business cash** (trough A$29.3k plus about A$10k buffer), plus personal runway to about M40.
- **Conservative:** about A$32k, provided the cost-cut trigger is honoured.
- **Lifetime seats:** without them, the base trough deepens to −A$38.7k.

---

## 10. Risks and mitigations

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| 1 | **Top-of-funnel volume.** There are 18 users today, and the base assumes 400 sign-ups in M1 growing 8% a month. | The largest swing in the model (−A$38k at 250 a month) | Build a ≥500 waitlist before launch. Founder-led community work on Reddit and Discord. "X vs Y" SEO pages. A public sample test with no login. Affiliate revenue share. Re-run the model at day 90. Cost-cut trigger at M6. |
| 2 | **Content quality and catalogue depth.** ja 83 tests, zh 274; `answer_explanation` NULL on all 1,424 questions; LLM errors drive serious learners away. | Churn, refunds, reputation | A$3k content fill + A$7k native QA before and after launch. Answer explanations. A "report an error" button with credit refunds. Show catalogue counts per band rather than promising "unlimited". |
| 3 | **Price realisation, conversion and churn** | ±A$28–34k each | Annual by default. Discounts limited to founding and one November sale. 21-day trial re-offered at day 45. PPP only after 3 months of data. |
| 4 | **Compliance.** Children's Online Privacy Code (10 Dec 2026, applies to solo too); APP 8 (DT on `:free` and DeepSeek endpoints); ST4S; unfair trading practices law (1 Jul 2027); ACL claims and unfair contract terms | Blocks schools; regulator and reputation risk | Age gate and under-18 defaults at launch. DT only on ZDR providers, disclosed. Easy cancellation and reminders. Purchased credits never expire. Lifetime defined in the terms. ST4S Readiness Check started early. No "NAATI-approved" or "replaces WaniKani" claims. |
| 5 | **Founder bandwidth and bus factor.** One person does development, content QA, support, sales and community. | Slips the school timeline; schools ask about continuity | Gates stop parallel bets. A$150/mo contingency for contractor cover. Runbooks. Tutors before schools. Hire at G3. |
| 6 | Payment fees and MoR terms unverified (Paddle has separate terms under US$10; Stripe Managed Payments about +3.5%) | ±A$0.4–1.0 per payer per month | Verify before G0. If small-ticket terms are poor, run packs through Stripe or raise the smallest pack to US$9.99. |
| 7 | Production DT cost unmeasured | Variable cost could be understated | Fix `llm_calls` cost logging first. Per-tier daily DT caps and token budgets. Re-price after 30 days of data. |
| 8 | Free chatbots commoditise DT and custom content | Weak differentiation | Lead with measurement (placement, ELO, BKT, plan) and curated audio. |
| 9 | School sales cycle (budgets set in Terms 3–4; ST4S queue) | School revenue lands in 2030 (base) | Tutors, independents and Catholic schools first. Term Pilot timed for conversion in Term 4. Small Class plan with no procurement cliff. |

---

## 11. Next 90 days (17 Nov 2026 → mid-Feb 2027)

| Window | Work | Gate evidence |
|---|---|---|
| Weeks 1–2 | Fix `llm_calls` cost logging for DT. Move DT grading to ZDR providers only. Remove the hardcoded `p_was_free_test=True` and build the Stripe webhook ([[business/pricing-plan.tech]] §API). Register for GST. | DT cost per call measured |
| Weeks 2–6 | Entitlements layer. Subscriptions via the chosen MoR plus Stripe. Credit ledger with three pools. Pricing page. Age gate. Privacy policy and T&Cs, reviewed for unfair contract terms and the Children's Code. | G0 checklist |
| Weeks 1–8 | Content fill (A$3k). Native QA sprint and answer explanations (A$7k over M1–M6). Public sample test. Comparison pages. | ≥200 tests per band for zh and ja |
| Weeks 1–8 | Waitlist and founding offer (US$69/yr, A$99). 100 lifetime seats (US$299 / A$449). Community presence. | Waitlist ≥500 |
| Jan 2027 (M1) | Launch billing. Convert the 18 existing users to founding status (2 free tests a day grandfathered; token balances move 1:1 to purchased credits). | |
| Days 60–90 after launch | Measure sign-ups, conversion, churn and credit burn. Re-run the model. Apply the cost-cut trigger if hit. Submit the ST4S Readiness Check. Open the tutor waitlist. | Cost-cut trigger / G1a inputs |

---

## Review notes (red-team corrections)

**Accepted and applied:**
- Churn 9% base (7% optimistic, 11% conservative).
- Conversion 3%; 40 founding members.
- Schools moved later, with build only at G1.
- Founder cash need raised to about A$40k.
- Lifetime cash basis stated explicitly.
- Pro allowance text corrected to about 30 custom tests.
- 3,000-credit pack replaced by 2,500 (+25%).
- New-word import at 8 credits.
- DT fair-use caps cut and per-tier token budgets added.
- DT on ZDR providers only.
- Study Pass priced directly.
- Tutor plan repriced to A$39 + A$3, GST-inclusive, with seat restrictions.
- School minimum A$750 plus a Class plan.
- Purchased credits never expire.
- A$7k native QA.
- Exam Pass limited to CT candidates, 4 a month.
- Positioning changed to "reading, listening and vocabulary stack".
- Age gate.
- MoR small-ticket terms flagged.

**Additional changes made here (not in the red team):**
- **Tutors launch at M13**, ahead of schools. The class layer costs founder time but no cash, and it is the cheapest B2B revenue.
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
