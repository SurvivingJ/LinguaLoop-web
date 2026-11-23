---
title: LinguaDojo Market Research Appendix
type: overview
status: planned
last_updated: 2026-11-17
open_questions:
  - "OPEN: Verified AUD storefront prices for the main competitors (most figures are USD or App Store tiers)."
  - "OPEN: ST4S full-assessment fee and queue length."
  - "OPEN: NAATI practitioner counts for Chinese and Japanese, and CCL tests by language (needs a data request)."
  - "OPEN: Current NAATI recertification fee and post-June-2026 PD category minimums."
  - "OPEN: Conversion and churn data for niche serious-learner tools (none published)."
  - "OPEN: Paddle terms for transactions under US$10; Stripe Managed Payments availability in AU; Stripe AU international card rate (2.8% vs 3.5%)."
---

# LinguaDojo Market Research Appendix

This is a condensed appendix to [[business/business-case]] and [[business/pricing-plan]]. The research was done on 2026-11-17 by web search.

**Verify before quoting.** Several vendor sites could not be fetched from the research session's network: stripe.com, supabase.com, azure, railway, cloudflare, skritter, renshuu, naati.com.au, education.gov.au and st4s. Their figures come from search summaries and third-party pages. Check every price on the vendor's live page before using it externally.

**Notation:**
- **[unverified]** means the figure was not confirmed against a primary page.
- **E** marks an estimate.
- FX is 1 USD = A$1.47 ([stockwirex, 12 Nov 2026](https://stockwirex.com/?p=55967)).

---

## 1. Cost to serve (internal, measured)

| Item | A$ | Basis |
|---|---|---|
| One test, no references (LLM + TTS) | 0.02–0.05 | `wiki/evaluations/test-gen-20-run-2026-08-21.md`; Azure TTS at US$15 per 1M characters |
| One test with one L1 reference set | 0.19–0.23 | `wiki/evaluations/sentence-refs-pilot-2026-10-30.md` (E: Sonnet API-equivalent) |
| One word sense, all-in (definition, ladder, judge) | ~0.075 | prod `llm_calls` 2026-11-15; fat-seed skill |
| One language to launch depth (1,200 tests, 13k senses) | ~1,250 | E |
| Remaining zh/ja/en gap | under 3,000 | prod counts |
| DT grade (ADR-044 single call) | 0.0002–0.0004 | `wiki/evaluations/dt-decision-grading-2026-11-14.md` |
| DT fallback (v2 Detector/Verifier) | 0.04–0.07 | [[decisions/ADR-044-dt-single-call-generative-grader]] |
| New word sense imported live | 0.015–0.075 | pipeline evals |
| Fixed platform costs per month | 110–160 | see sources below |

**Fixed-cost sources:**
- Supabase: [toolradar](https://toolradar.com/tools/supabase/pricing), [schematichq](https://schematichq.com/blog/supabase-pricing), [makerkit](https://makerkit.dev/pricing-calculator/supabase), [focusreactive](https://focusreactive.com/blog/supabase-price/)
- Railway: [docs.railway.com/pricing/plans](https://docs.railway.com/pricing/plans)
- Cloudflare R2: [developers.cloudflare.com/r2/pricing](https://developers.cloudflare.com/r2/pricing)
- Azure Speech: [pricing](https://azure.microsoft.com/pricing/details/cognitive-services/speech-services), [beri.net comparison](https://www.beri.net/article/elevenlabs-vs-cartesia-vs-azure-tts-latency-pricing-voice-cloning-2026)

**Data caveat:** production DT cost is unmeasured. `llm_calls` DT rows have a NULL `cost_usd` and 0 tokens, and most rows went to `:free` models.

### Payment fees

| Provider | Fee | Source / status |
|---|---|---|
| Stripe AU, domestic card | 1.65% + A$0.30 (from 1 Oct 2026) | [Stripe support](https://support.stripe.com/questions/updates-to-card-pricing-in-australia-from-october-2026) (confirmed) |
| Stripe AU, international card | 2.80% + A$0.30, plus 2% FX conversion | [Stripe Connect AU](https://stripe.com/zh-cn-au/connect/pricing), [Wise](https://wise.com/au/blog/stripe-fees), [Aspire](https://aspireapp.com/en-au/blog/stripe-fees-australia). **2.8% is unverified; some sources show 3.5%** |
| Stripe Billing | ~0.7% | E, unverified |
| Paddle (merchant of record) | 5% + US$0.50; separate terms under US$10 | [Paddle pricing](https://www.paddle.com/pricing), [Paddle 101](https://www.paddle.com/paddle-101), [dodopayments](https://dodopayments.com/blogs/paddle-fees-explained) |
| Stripe Managed Payments | Reported at about +3.5% on top of processing; AU eligibility unconfirmed | [stripe.com/au/managed-payments](https://stripe.com/au/managed-payments), [dodopayments](https://dodopayments.com/blogs/stripe-managed-payments-fees-explained) |

---

## 2. Solo learners (global)

### Competitor prices (USD unless marked)

| Product | Focus | Monthly | Annual | Lifetime / other | AI tier or credits | Source |
|---|---|---|---|---|---|---|
| LingQ | Reading and listening | $14.99 | $119.99 | 24 months for $215.76 | Premium Plus $29.99/mo, $269.99/yr | [storylearning](https://www.storylearning.com/lingq-review), [lingq blog](https://www.lingq.com/blog/lingq-free-vs-premium/) |
| Migaku | Immersion and mining | $10 (Early Access $15) | $96 (EA $144) | $499; sale $240 | — | [migaku.com/pricing](https://migaku.com/pricing), [copycatcafe](https://copycatcafe.com/blog/migaku-black-friday) |
| Satori Reader | Graded Japanese reading | $8.99 (¥1,000) | $89.99 | — | — | [App Store](https://apps.apple.com/gb/app/satori-reader/id1382950847) |
| WaniKani | Kanji SRS | (not confirmed) | $89 | $299 | — | [WaniKani KB](https://knowledge.wanikani.com/account-and-membership/payment-and-billing/subscription-plans/) |
| Bunpro | Japanese grammar SRS | $5 web / $6.49 iOS | ~$50 web / $64.99 iOS | $150 web | — | [bunpro.jp/pricing](https://bunpro.jp/pricing), [App Store](https://apps.apple.com/app/bunpro-japanese-srs/id1615337616) |
| renshuu | Japanese all-in-one | $3.99–6.99 | $49.99 | $109.99–129.99 | — | [App Store](https://apps.apple.com/us/app/renshuu/id1542730063), [alternativeto](https://alternativeto.net/software/renshuu/about) |
| Clozemaster | Cloze sentences | $12.99 | $79.99 | Lifetime dropped ~Feb 2026 | — | [copycatcafe](https://copycatcafe.com/blog/clozemaster-black-friday), [clozemaster.com/pro](https://www.clozemaster.com/pro) |
| Readlang | Web reader | $6 | $48 | — | Premium Plus $15/mo, $120/yr | [uservoice](https://readlang.uservoice.com/knowledgebase/articles/737319), [copycatcafe](https://copycatcafe.com/blog/readlang-review) |
| Language Reactor | Subtitles | ~$5–6 | available | — | — | [languagereactor.com](https://www.languagereactor.com/pro-mode), [mezzoguild](https://www.mezzoguild.com/language-reactor-review/) |
| Du Chinese | Graded Chinese reading | $14.99 | $119.99 | $399 ($299 on sale) | Schools >90% off | [App Store](https://apps.apple.com/us/app/-/id1052961520), [duchinese.net/blackfriday](https://duchinese.net/blackfriday), [duchinese.net/schools](https://duchinese.net/schools) |
| HelloChinese | Beginner course | $11.99 | $69.99 | — | Premium+ $19.99/mo, $149.99/yr | [App Store](https://apps.apple.com/us/app/-/id1001507516) |
| Skritter | Hanzi and kanji writing | $14.99 | $99.99 | — | — | [App Store](https://apps.apple.com/us/app/-/id1370892114) |
| Mandarin Temple | HSK-structured Chinese | Pro $15; Pro Plus $27 | — | — | 300 credits/mo free; 12,000/mo Pro Plus; top-ups for paid members only | [mandarintemple.com/pricing/learners](https://mandarintemple.com/pricing/learners), [AI credits guide](https://beta.mandarintemple.com/guide/pro/ai-credits-explained) |
| Busuu | Course | ~$7.49–19.95 | Premium $72.99; Premium Plus $87.90 (web) | — | AI in Premium Plus | [subger](https://subger.com/en/service/busuu), [apppricinglab](https://apppricinglab.com/iap/apple/379968583) |
| Babbel | Course | $13.95–17.95 | $83.40–107.40 | $299.99 | — | [testprepinsight](https://testprepinsight.com/resources/how-much-does-babbel-cost/), [Babbel support](https://support.babbel.com/hc/en-gb/articles/19650417983378-Pricing) |
| Pimsleur | Audio | $19.95–20.95 | $164.95 | $798 | — | [storylearning](https://www.storylearning.com/blog/pimsleur-review), [copycatcafe](https://copycatcafe.com/blog/pimsleur-cost) |
| Duolingo Super | Gamified | ~A$10.83 effective | A$129.99 (undated) | — | — | [subger](https://subger.com/en/service/duolingo-plus) |
| Duolingo Max | Gamified + AI | ~$29.99 | ~$168 | — | AI bundled | [lingoly](https://lingoly.io/is-duolingo-max-super-duolingo-same/) |
| Speak | AI speaking tutor | Premium Plus $39.99 | $164.99 | — | — | [App Store](https://apps.apple.com/us/app/speak-learn-english/id1286609883), [speakshark](https://speakshark.com/blog/speak-app-review-2026) |
| Praktika | AI tutor | ~$14 | ~$96 | — | — | [praktika.ai](https://praktika.ai/blog/how-much-does-it-cost-to-learn-spanish-september-2026) |
| Langua | AI tutor | $19.99 capped; $29.99 unlimited | $149.99 / $199.99 | Institutions from $500/mo | Daily caps | [lingrow](https://lingrow.io/blog/langua-review) |
| italki / Preply | Human tutors | italki $4–20/hr; Preply $3–40+/lesson | — | — | Prepaid wallet | [italki blog](https://www.italki.com/en/blog/japanese-tutor-cost), [preply](https://preply.com/en/online/japanese-tutors) |
| Anki | Free SRS | Free | — | AnkiMobile $24.99 | — | [Anki FAQ](https://docs.ankiweb.net/faqs/why-does-ankimobile-cost-more-than-a-typical-mobile-app) |
| jpdb.io | Free JA SRS and reader | Patreon | — | — | ~618 patrons ≈ $2.8k/mo (undated) | [patreon.com/jpdb](https://www.patreon.com/jpdb/about) |

### Pricing patterns

| Pattern | Figures |
|---|---|
| Price bands | Utility SRS $50–65/yr; content and immersion $80–120/yr; AI-heavy $150–270/yr; lifetime $110–499 |
| Annual discount | 17–49% below 12× monthly; typically 30–40% |
| "Plus" AI tiers | Price at 1.5–2.5× the base tier |

### Conversion and retention benchmarks

| Benchmark | Figure | Source |
|---|---|---|
| Download → paid by day 35 | ~2.0% non-AI, 2.4% AI apps | [RevenueCat State of Subscription Apps](https://www.revenuecat.com/state-of-subscription-apps), [ppc.land](https://ppc.land/ai-apps-earn-41-more-per-user-but-churn-30-faster-revenuecat-finds) |
| Hard paywall vs freemium | 10.7% vs 2.1% | [SaaStr summary](https://www.saastr.com/the-top-10-learnings-from-revenuecats-state-of-subscription-apps) |
| Trial length | Trials of 17+ days convert 42.5%; shorter trials 25.5% | [SaaStr summary](https://www.saastr.com/the-top-10-learnings-from-revenuecats-state-of-subscription-apps) |
| Language-app freemium | 2–5% (weakly sourced) | [appsops.store](https://appsops.store/blog/language-learning-app-subscription-pricing-2026) |
| Duolingo Q3 2026 | 13.1M paid / 153.1M MAU ≈ 8.6% (our calculation) | [SEC filing](https://www.sec.gov/Archives/edgar/data/0001562088/000162828026069474/q3fy26duolingo9-30x26share.htm) |
| Education apps (Adapty) | 12-month LTV $45.10; trial users worth +50.4%; 23.5% of trials start after day 31 | [Adapty](https://adapty.io/blog/education-app-subscription-benchmarks/) |
| Annual retention | First-year renewal fell from 31% to 28%. 95% of cancelled annual subscribers never return. | [9to5mac](https://9to5mac.com/2026/05/27/new-report-shows-annual-app-subscribers-rarely-return-after-they-cancel/) |

### Hybrid credits: prevalence and practice

**Prevalence:**
- About 65% of SaaS vendors adding generative AI moved to hybrid pricing ([HubSpot, citing Bain](https://blog.hubspot.com/website/ai-credits-buyers-guide)).
- Most of the 50 AI pricing models Metronome catalogued use a hybrid ([Metronome](https://metronome.com/blog/2026-trends-from-cataloging-50-ai-pricing-models)).

**How vendors handle credits:**

| Vendor | Practice | Source |
|---|---|---|
| ElevenLabs | Subscription credits roll over up to 2×; PAYG credits expire after 12 months | [ElevenLabs](https://elevenlabs.io/docs/help-center/account/general/how-does-credit-rollover-work) |
| DataCamp | Top-ups expire after 12 months and need a subscription | [DataCamp](https://support.datacamp.com/hc/en-us/articles/42136382698263) |
| Suno | Add-on credits usable only while subscribed | [Suno](https://help.suno.com/en/articles/2643713) |
| Spotify | Pro credits sold once a usage limit is hit | [Spotify](https://support.spotify.com/us/article/ai-usage-limits/) |

**Complaints:**
- Stranded credits ([arnon.dk](https://arnon.dk/the-stranded-asset-in-ai-pricing/))
- Opaque burn rate ([sikayetvar](https://www.sikayetvar.com/en/chatgpt-us/chatgpt-business-subscription-credits-ran-out-after-a-few-questions))
- Quotas that expire ([datallmlab](https://datallmlab.com/blog/credit-based-ai-coding-pricing.html))
- The counter-view, that subscriptions beat credits: [Vellum](https://www.vellum.ai/blog/why-subscriptions-beat-credits-for-ai-products)

### Audience size

| Measure | Figure | Source |
|---|---|---|
| JLPT applicants, 2025 | ~1.94M | [jlpt.jp statistics](https://www.jlpt.jp/e/statistics/index.html), [Dec 2025 PDF](https://www.jlpt.jp/statistics/pdf/2025_2_2.pdf), [lingobright](https://lingobright.com/statistics/complete-list-of-language-proficiency-certifications-compared/) |
| HSK candidates, 2024 | ~719k | [China Daily HK](https://www.chinadailyhk.com/article/623446), [hsklord](https://hsklord.com/blog/what-is-hsk) |
| r/languagelearning | ~3.4M members | [thehiveindex](https://thehiveindex.com/communities/r-languagelearning/) |
| r/LearnJapanese | ~727k members | [mirror](https://r-weld.vercel.app/r/LearnJapanese) |
| Typical JA tool stack | ~$230/yr | [WaniKani forum](https://community.wanikani.com/t/is-the-price-of-wanikani-bunpro-really-worth-it-for-learning-japanese/63399) |

### Acquisition costs

| Channel / measure | Figure | Source |
|---|---|---|
| Reddit CPC | $0.50–2.00 | [webtonic](https://webtonic.io/blog/education-coaching-reddit-ads-statistics), [stackmatix](https://www.stackmatix.com/blog/reddit-ads-cost-guide-2026) |
| YouTube sponsorship | $15–45 CPM | [outlierkit](https://outlierkit.com/resources/youtube-sponsorship-rates/), [1of10](https://1of10.com/blog/youtube-sponsorship-rates/) |
| Paid share of education installs | 28%, with organic uplift up to 2.1× | [rocketshiphq](https://www.rocketshiphq.com) |
| Modelled CAC (E) | Reddit ~US$165; YouTube ~US$240 | Our model |

---

## 3. Australian schools

### Market

| Measure | Figure | Source |
|---|---|---|
| Students and schools | 4,160,918 students in 9,673 schools (ABS 2025); independent schools +15.3% 2021–25 | [ABS Schools 2025](https://www.abs.gov.au/statistics/people/education/schools/2025), [ABS release](https://www.abs.gov.au/media-centre/media-releases/independent-schools-drive-rise-enrolments) |
| Schools by sector | 69.7% government / 18.2% Catholic / 12.1% independent | [ACARA](https://acara.edu.au/reporting/national-report-on-schooling-in-australia/school-numbers) |
| Senior language uptake | ~7.6% in 2023, down from 11.3% in 2010 [unverified] | [AACRAO](https://www.aacrao.org/edge/emergent-news/australia-proposes-bonus-atar-points-to-rescue-plunging-asian-language-enrollment/), [ACARA Y12](https://acara.edu.au/reporting/national-report-on-schooling-in-australia/year-12-subject-enrolments) |
| VIC Year 12 languages, 2025 | +8.7%; Chinese +11.8% | [ACICIS](https://www.acicis.edu.au/wp-content/uploads/2026/08/20260817_LP-Deck-2025_VIC.pdf) |
| QCAA Chinese, 2024–25 | +15.29% | [QCAA](https://www.qcaa.qld.edu.au/downloads/senior-qce/languages/snr_chinese_25_subj_rpt.pdf) |
| Japanese learners in AU | ~415k; Oceania 59.4% primary | [JF survey](https://www.jpf.go.jp/e/project/japanese/survey/result/dl/survey2021/4_Oceania.pdf), [JF Sydney](https://sydney.jpf.go.jp/events/survey-of-japanese-language-education/) |
| NSW HSC 2025, Japanese | Continuers ~795 / Beginners ~358 | [NESA](https://www.nsw.gov.au/education-and-training/nesa/hsc/facts-and-figures/enrolment-data/courses) |
| NSW HSC 2025, Chinese | Continuers 334 / Beginners 57 / Chinese & Literature 309 | [NESA](https://www.nsw.gov.au/education-and-training/nesa/hsc/facts-and-figures/enrolment-data/courses) |
| NSW Year 11, 2025 | Japanese Continuers/Beginners 1,016/689; Chinese 446/82 | [NESA Yr 11](https://boardofstudies.nsw.edu.au/ebos/static/EN_SX_2025_11.html) |
| QLD QCE 2024 Japanese | 1,188 | [QCAA](https://www.qcaa.qld.edu.au/downloads/publications/qcaa_stats_yr12_cert_summary_2024.pdf) |
| SA SACE 2025 Japanese Continuers | 203 | [SACE](https://www.sace.sa.edu.au/documents/838603/1f2f0e01-399f-9e1f-e1ed-41f9ff23087a) |
| VCE Chinese SL Advanced, Units 1–2 | ~549 [unverified] | [VCAA](https://www.vcaa.vic.edu.au/sites/default/files/2026-04/vce_lote_chinese_second_language_advanced_25.pdf) |
| VCE study designs | Japanese SL; Chinese SL | [VCE Japanese SL](https://www.vcaa.vic.edu.au/sites/default/files/2026-04/vce_lote_japanese_second_language_25.pdf), [VCE Chinese SL](https://www.vcaa.vic.edu.au/sites/default/files/2026-04/vce_lote_chinese_second_language_25.pdf) |
| WACE | Languages offered; no counts found | [SCSA](https://scsa.wa.edu.au/7to12-circulars/edition-5-june-2025/7.-enrolments/wace-language-applications-year-11-2026) |
| Chinese pathways (AC v9) | Second-language / background / first-language | [Asia Education](https://asiaeducation.edu.au/curriculum/languages/chinese), [AC v9](https://v9.australiancurriculum.edu.au/teacher-resources/understand-this-learning-area/languages) |
| EAL/D, NSW public schools | 205,555 (2025) | [CESE factsheet](https://education.nsw.gov.au/content/dam/main-education/about-us/educational-data/cese/2025_EALD_learners_factsheet.pdf) |
| EAL/D, national estimate | ~25% of students | [Deakin TESOL](https://ojs.deakin.edu.au/index.php/tesol/article/download/2108/1785/8656) |
| VIC newly arrived EAL, 2024 | 8,678 | [VIC EAL stats](https://www.education.vic.gov.au/Documents/school/teachers/teachingresources/diversity/eal/EAL%20Statistics%20Summary%202024.pdf) |

**Estimates (E):**
- About 120–150k secondary Japanese learners.
- About 5,000–7,000 Year 11–12 Chinese or Japanese certificate students nationally.

### Competitors and price anchors

| Product | Model | Price | Source |
|---|---|---|---|
| Education Perfect | Per student, by quote | "From ~$15/pupil" [unverified] | [pricing](https://www.educationperfect.com/pricing/), [edtechimpact](https://edtechimpact.com/products/education-perfect/), [itbrief](https://itbrief.com.au/story/education-perfect-revamps-languages-platform-for-schools-in-anz) |
| Languagenut | Site licence, by quote | not public | [FAQ](https://www.languagenut.com/en-au/faqs/) |
| Duolingo for Schools | Free | $0 | [SA DoE](https://www.education.sa.gov.au/our-learning-sa/learning-home-activities/languages/duolingo) |
| Quizlet Plus Teachers | Per teacher | ~US$35.99/yr [unverified] | [brighterly](https://brighterly.com/blog/quizlet-cost) |
| Kahoot! EDU | Per teacher | US$179.88–299.88/yr | [kahoot.com](https://kahoot.com/schools/plans/) |
| Wordwall | School plan | US$308–464/yr | [wordwall.net](https://wordwall.net/price-plans/school) |
| LingQ Classroom | Per learner | ~US$84–96/yr [unverified] | [lingq.com/schools](https://www.lingq.com/en/schools/) |
| ChinesePod / Hack Chinese | Consumer only | US$14–29 / US$8–12 per month | [mezzoguild](https://www.mezzoguild.com/chinesepod-review), [capterra](https://www.capterra.co.uk/software/1014389/hack-chinese) |
| LiteracyPlanet | Per student | A$15/student/yr | [literacyplanet](https://www.literacyplanet.com/?p=8833) |
| Schoolbox LMS | Per student | A$28/student/yr, 300 minimum | [schoolbox](https://schoolbox.education/pricing/) |

### How schools buy

**Procurement thresholds:**

| Jurisdiction | Thresholds | Source |
|---|---|---|
| VIC | One quote up to A$2.5k; one written quote A$2.5–25k; three quotes A$25–150k | [Horsham College policy](https://www.horsham-college.vic.edu.au/wp-content/uploads/2026/03/Purchasing-and-Authorities-Policy.pdf), [VIC PAL](https://www2.education.vic.gov.au/pal/procurement-in-schools/policy) |
| QLD | One quote up to A$10k ex-GST; two written quotes up to A$20k; three quotes up to A$250k | [QLD DoE](https://ppr.qed.qld.gov.au/pp/purchasing-and-procurement-procedure) |
| NSW | Staff-only procedures; EdBuy | [NSW policy](https://education.nsw.gov.au/policy-library/policies/pd-2020-0472-09) |

**Compliance:**

| Requirement | Detail | Source |
|---|---|---|
| ST4S | Readiness Check, then full assessment; valid 2 years | [ESA](https://esa.edu.au/solutions/our-solutions/safer-technologies-4-schools), [validity](https://d2rjmq04xy91c3.cloudfront.net/docs/how-long-is-an-assessment-valid-for), [badge FAQ](https://d2rjmq04xy91c3.cloudfront.net/?p=944) |
| VIC | Mandatory ST4S/PIA process | [VIC PAL](https://www2.education.vic.gov.au/pal/ict-software-schools-risk-assessment/policy) |
| NSW | Approved apps | [T4L](https://t4l.schools.nsw.gov.au/news-t4l/2023/issue94.html) |
| Catholic sector | ST4S via NCEC | [NCEC](https://ncec.catholic.edu.au/resource-hub/safe-technologies-4-schools-in-the-catholic-sector) |
| Children's Online Privacy Code | Due 10 Dec 2026; covers services likely to be accessed by children | [OAIC](https://www.oaic.gov.au/privacy/privacy-registers/privacy-codes/childrens-online-privacy-code), [Pinsent Masons](https://www.pinsentmasons.com/out-law/analysis/australia-online-privacy-code-children-means-service-providers) |
| AU-hosted data | Market expectation | [EP security](https://www.educationperfect.com/legal/security-and-risk-assessment/), [Essential Assessment](https://www.essentialassessment.com.au/security/) |
| LMS | Compass (3,000+ schools), Schoolbox (LTI 1.3) | [Compass](https://www.compass.education/post/how-compass-connects-your-lms-to-the-bigger-picture/), [Schoolbox partners](https://schoolbox.education/partners/) |

**Teacher workload:**
- Marking is a significant stressor for half of AU teachers (TALIS 2024).
- Lower-secondary teachers average 46.4 hours a week.
- Sources: [The Educator](https://www.theeducatoronline.com/k12/news/teacher-workload-crisis-worsening-report-shows/288480), [AITSL](https://www.aitsl.edu.au/research/australian-teacher-workforce-data/australian-teacher-workforce-survey).

### Adjacent segments

| Segment | Figures | Sources |
|---|---|---|
| Private tutoring | ~A$1–2.2bn market; up to ~80k tutors | [Sydney Uni](https://www.sydney.edu.au/news-opinion/news/2025/09/30/unregulated-and-unfair-how-private-tutoring-is-falling-short-for-families.html), [The Educator](https://www.theeducatoronline.com/k12/news/deep-dive-how-the-maths-slump-is-driving-australias-tutoring-boom/288991) |
| Community language schools | ~600 schools, 90k+ students; A$25.6m federal funding over 4 years | [PBO](https://www.pbo.gov.au/elections/2025-general-election/2025-election-commitments-costings/community-language-schools), [VIC report](https://www.vic.gov.au/victorian-government-report-multicultural-affairs-2024-25/appendix-b-multicultural-related-indicators/benefits-diversity), [WA](https://www.wa.gov.au/government/media-statements/Cook%20Labor%20Government/Community-language-schools-chalk-up-a-win-with-record-funding--20250804) |

---

## 4. Translators

### The profession

| Measure | Figure | Source |
|---|---|---|
| NAATI-certified practitioners | 8,803, holding 13,382 credentials in 172 languages (FY2024-25) | [NAATI annual report 2025](https://www.naati.com.au/wp-content/uploads/2025/11/NAATI-2025-AR.pdf) |
| NAATI tests, FY2024-25 | 29,971 total; ~2,500 certification; ~27,000 CCL (E) | [NAATI FY25 financial statements](https://www.naati.com.au/wp-content/uploads/2025/11/SIGNED_Financial-statements_FY2024-25.pdf) |
| AU interpreters and translators employed | ~5,600 (2021) | [Jobs and Skills Australia](https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles/occupations-osca/4115-interpreters-and-translators) |
| AUSIT members | 1,200+ | [NAATI news](https://www.naati.com.au/news/ausit-membership/), [ausit.org](https://ausit.org) |
| ATA members | ~8,500–11,000 | [Wikipedia](https://en.wikipedia.org/wiki/American_Translators_Association) |
| ITI members | 3,148 | [CPD Standards](https://directory.cpdstandards.com/sectors/institute-of-translation-and-interpreting-iti/) |
| US interpreter and translator jobs | 73,900 | [BLS](https://www.bls.gov/ooh/media-and-communication/interpreters-and-translators.htm) |
| Translators worldwide | "~640k" [untraced] | [redokun](https://redokun.com/blog/translation-statistics) |
| Impact of AI on translators | 36% lost work to AI; 43% income down | [The Bookseller](https://thebookseller.com/news/a-third-of-translators-report-losing-work-to-generative-ai-systems-soa-survey-reveals) |

**Estimate (E):** about 1,000–2,000 Chinese/Mandarin credential holders and 100–300 Japanese. Check against the [NAATI directory](https://directory.naati.com.au).

### NAATI recertification and PD

**Rules:**
- A 3-year cycle and 120 points.
- About 5 points per hour of activity.
- B.6 (self-directed study) is capped at 10 points per activity.
- D.4 (reading, listening or watching in the credentialed language) is capped at 20 points per period.

**Sources:**
- [Recertification](https://www.naati.com.au/certification/recertification/)
- [FAQs](https://www.naati.com.au/resources/recertification-faqs/)
- [Catalogue](https://www.naati.com.au/resources/recertification-catalogue/)
- [Comparison guide](https://www.naati.com.au/wp-content/uploads/2026/06/Catalogue-comparison-guide.pdf)
- NAATI Learn, which sells paid courses such as A$49 for 10 points: [update](https://www.naati.com.au/news/update-naati-learn-course-catalogue/)

### What translators and candidates pay

| Item | Price | Source |
|---|---|---|
| Trados Studio Freelance | US$408–564/yr | [capterra](https://www.capterra.com/p/151746/Trados-Studio/pricing/), [trados.com](https://www.trados.com/pricing/freelance-translators/) |
| memoQ translator pro | ~US$396–400/yr | [spotsaas](https://www.spotsaas.com/product/memoq-translator-pro/pricing) |
| Phrase TMS Freelancer | US$27/mo | [capterra](https://www.capterra.com/p/276186/Phrase/pricing/) |
| ProZ Plus / Premium | US$180 / US$300 a year | [proz.com](https://go.proz.com/membership) |
| Legal translation CPD course | £199–299 | [Linguist Training](https://linguisttraining.thinkific.com/collections/iltd) |
| ProZ legal terminology course | US$99 | [ProZ](https://connect.proz.com/translator-training/course/5705) |
| University legal or medical translation course | US$850 | [Arizona](https://ce.arizona.edu/node/675) |
| Sketch Engine | ~€100/yr (2017) | [ATA](https://www.atanet.org/resources/language-sketching/) |
| CCL test | A$814; marked practice test A$165 | [NAATI](https://www.naati.com.au/?p=34314) |
| Certified Translator test | A$605 per direction | [NAATI CT](https://www.naati.com.au/certification/ct) |
| CCL coaching | A$250–400+ | [visionlanguageexperts](https://www.test.visionlanguageexperts.com.au/naati-ccl-online-coaching) |
| Mandarin CCL vocabulary list | A$9.99 | [gumroad](https://ashishsurani.gumroad.com/l/wnjhgc) |
| Translation diploma | A$6,500 for 33 weeks | [courses.com.au](https://courses.com.au/provider-course/advanced-diploma-of-translating-english-chinese-australia-international-institute-of-workplace-training) |
| RMIT NAATI CT prep skill set | — | [RMIT](https://www.rmit.edu.au/study-with-us/levels-of-study/vocational-study/skill-sets/translating-skills-for-naati-certification-s0147) |
| WSU LANG7030 | — | [WSU](https://hbook.westernsydney.edu.au/subject-details/lang7030) |

**Terminology management.** The market sells terminology management tools, not ways to learn terminology. See [Sketch Engine](https://www.sketchengine.eu/user-guide/translators-term-extraction/) and [Rubric](https://rubric.com/en-us/what-is-terminology-management-and-do-you-need-it).

### Channels

**Professional bodies:**
- AUSIT ([ausit.org](https://ausit.org); conference worth 40 PD points: [ausit.org/?p=12021](https://ausit.org/?p=12021))
- NAATI Practitioner Hub ([link](https://www.naati.com.au/practitioner-hub/))

**University translation programmes:**
- [UNSW](https://www.unsw.edu.au/study/postgraduate/master-of-translation-and-interpreting)
- [UQ](https://future-students.uq.edu.au/study/programs/master-arts-translation-and-interpreting-5752)
- [Macquarie](https://mq.edu.au/about/about-the-university/our-faculties/medicine-and-health-sciences/departments-and-centres/department-of-linguistics/study-with-us/translation-and-interpreting-program)
- [UWA](https://www.uwa.edu.au/study/courses/master-of-translation-studies)

---

## 5. Australian consumer law and regulation (pricing-relevant)

| Area | Rule | Source |
|---|---|---|
| Unfair trading practices | Prohibitions passed 2 July 2026, in force 1 July 2027: easy cancellation, upfront disclosure, trial and renewal reminders, no manipulative design | [McCullough](https://mccullough.com.au/2026/07/03/unfair-trading-practices-laws-australia-2027/), [Brightlaw](https://www.brightlaw.com.au/unfair-trading-practices-ban-passed-by-parliament/) |
| Unfair contract terms | Penalties since Nov 2023; credit forfeiture terms are a risk | General knowledge; verify with counsel |
| GST | A$75k registration threshold; voluntary registration allowed | Verify at ato.gov.au |

## Related Pages
- [[business/business-case]] — Uses these figures
- [[business/pricing-plan]] — Prices derived from them
- [[business/pricing-plan.tech]] — Implementation
- [[decisions/ADR-047-credits-and-subscription-model]] — Decision record
