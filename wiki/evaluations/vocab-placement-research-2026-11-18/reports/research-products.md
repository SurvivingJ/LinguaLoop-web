# Product survey: how learning products place learners and check meaning and reading

Stage: research (product survey) for TASK-1073, the vocabulary placement test.
Date: 2026-11-18. Read-only. Nothing here is a wiki page.

Owner decisions this survey works inside (fixed, not reopened): build on the adaptive four-option
check with a stopping rule; no fake words and no Yes/No self-report; for Chinese and Japanese test
both meaning and reading; English tests meaning only.

## How to read this file

**Method and its limits.** WebFetch was blocked in this session: `knowledge.wanikani.com` and
`www.hackchinese.com` both failed DNS resolution ("outside the session's allowed network domains"),
so per the tool's instruction I stopped fetching pages. **Every web claim below comes from
WebSearch result extracts (the search tool's summary of the page), not from pages I opened.**
Quotes are as the extract gave them. Numbers in particular may be paraphrased or out of date.
To fetch the pages directly, `knowledge.wanikani.com` and `www.hackchinese.com` (and the other hosts
cited) would need to be allowed in the session's network settings.

**Labels.**
- **MEASURED**: the cited source states the fact directly (vendor documentation, a vendor blog or paper,
  a published paper, or the product's own forum staff). Still read through a search extract.
- **ESTIMATE**: a number or behaviour from a third-party site, a user report, or a dated page. It may be wrong today.
- **INFERENCE**: my own reading or conclusion. Not stated by any source.

Claims about LinguaDojo's own check cite wiki files by line.

---

## 1. Comparison table

"M" = meaning, "R" = reading (kana, pinyin or tone). "Placement" means any way to start past the
beginning, whether a test, a self-declared level or bulk "mark known".

| Product | Language | Placement format | Items / time | M and R: separate or together? How they combine | What the learner sees afterwards | Uncertainty and retakes | Paywall |
|---|---|---|---|---|---|---|---|
| WaniKani | ja | **None.** No test and no level skip, "not even if you email us and promise you know 10,000+ kanji" [W1] | n/a | **Separate prompts, both required.** Kanji and vocab ask M and R separately, typed, with no multiple choice [W2][W3][W4]. Wrong answers on either side count toward the same stage drop [W5]. Kana-only vocab is M only [W6] | Starts at level 1 | Can reset to a lower level. No upward move [W1][W7] | First levels free (1–2 or 1–3, sources disagree). About $9/mo, $89/yr [W8] ESTIMATE |
| KameSame (3rd-party WK companion) | ja | "Placement Test" lesson mode: correct answers mark items burned. "Mark as Learned" after a correct answer [K1] | Self-paced | Recall-style prompts. Not documented further | Burned or learned items | Applies to lessons only, not reviews [K1] | not verified |
| Bunpro | ja (grammar, vocab) | **No vocab placement test found.** Manual "mark known/mastered" per item or deck. Grammar can be marked known or given a manual SRS level [B1][B2] | n/a | Vocab reviews hide English and use a context sentence; "translate mode" shows kanji, you type English [B3]. Reading grading unclear [B3] | Per-deck progress. Since Sep 2025, full JLPT mock tests (5 per level) [B4] | Users report bulk "know all" not working and no multi-select [B1] | Free tier. 30-day Premium trial, no card [B5] MEASURED |
| Renshuu | ja | "I know this" on the term intro screen sets mastery for **all vectors** to a preset level. Still quizzed, at longer intervals [R1] | n/a | Separate facets. A kanji yields cards for meaning, each reading, stroke order [R2]. Users ask for split mastery kanji→reading vs reading→kanji [R3] | Mastery per term | Flagged terms can be filtered and unmarked in the Japanese Index [R1] | not verified |
| jpdb | ja | **No test.** "Mark as known" via a deck-state override page [J1]. Review grade "Never forget". Blacklist [J2] | n/a | **Together, self-graded.** One card. Users describe: meaning, kanji and reading all known → Pass (Hard/Okay/Easy). Partial → "Something" (a fail grade) [J2][J3] | Deck coverage %. Never-forget counts as known, blacklisted words drop out of the deck [J4] | Self-report. Many users grade loosely [J3] | not verified (Patreon-funded) |
| Migaku | ja, zh, others | **No proper placement test** (its own Notion page says so). Sort words Unknown/Track/Known/Ignore, or import a known-words list [MG1][MG2] | n/a | Not tested. Status is self-declared or auto-promoted | Known-word count, which staff call a proxy [MG3] | Known is promoted automatically after about a 14–20 day interval and never demoted automatically [MG4] ESTIMATE | not verified |
| Kanshudo | ja | No test. Infers mastery 0–4 per item from use and quiz results. A strong Word Quiz infers more basic words [KS1] | n/a | Per-item mastery | Overall mastery level mapped to JLPT (lvl 19 = N5 … 59 = N1) [KS1] | Inference revised by use | not verified |
| Hack Chinese | zh | Onboarding questionnaire or manual marking makes earlier-studied words **"assumed known"**. The app then **spot-checks** them daily [H1][H2] | Up to 30 checks/day on "Fast" [H2] | Self-graded cards. One review: pinyin and tone are checked first, then the definition [H3]. A competitor lists modes recognition, recall, listening, typing meaning→pinyin [H4] ESTIMATE | Progress bar with a separate segment for assumed-known-unchecked words [H5]. Progress against any exam level [H6] | Words remembered at their first check get boosted intervals [H5] | About $12/mo or $8/mo yearly [H7] ESTIMATE |
| Skritter | zh, ja | No test. Add list sections and "mark as learned" word by word. The SRS skips items you likely know [S1][S2] | n/a | **Separate "parts"**: writing, tone, reading, definition. Reading prompts hide the definition and definition prompts hide the reading. Tone/reading/definition graded binary (forgot / got it) [S3] | Per-part scheduling | Parts can be filtered per session. Users complained tone prompts dominate [S4] | $14.99/mo, 7-day trial [S5] ESTIMATE |
| Pleco | zh | No placement | n/a | **Separate test types**, each with its own score ("scorefiles"): self-graded, multiple choice (up to 5 options), fill-in, stroke order, tone practice [P1][P2]. "Ask for" chooses the tested field [P2]. **MC pinyin options always match the headword's syllable count** [P3]. Typed pinyin needs tone numbers [P4] | Per-test-type scores | n/a | Flashcards are a paid add-on (price not verified) |
| HelloChinese | zh | A placement test exists, per a third-party aggregator. No detail found [HC1] | not found | not found | Course level. The course is not mapped to HSK [HC2] | One user says support will set a higher start level by email [HC1] ESTIMATE | Freemium (not verified) |
| LingoDeer | ja, zh | **"Test Out"** skips to the next unit. Later levels selectable from the menu. No end-of-course test-out [LD1] | per unit | Mixed exercises (not detailed) | Unit unlocked | Retake by retrying the test-out (INFERENCE) | First unit free [LD1] |
| Duolingo (app) | all | **Adaptive placement**: assumes novice, starts simple, harder after a few correct, then "unlocks the skills we think you already know" [D1] | about 5–10 min [D2] ESTIMATE | Mixed exercises. Originally scored all-or-nothing. Partial credit added after learners were placed into lessons that were all too easy [D1] | Starting unit | Retake via "Jump here" (a small adaptive quiz) or course reset [D2] ESTIMATE | Free, with paid tier (not verified) |
| Duolingo English Test | en | High-stakes CAT. Opens with **15–18 adaptive Yes/No vocabulary items** (real vs pseudoword), **5 s per word** [DE1][DE2] | Whole test about an hour. An older doc says the CAT section ends after 25 items or 40 min [DE3] ESTIMATE | M only (and the format is one the owner rejected) | Score report | Rasch-style difficulty predicted from item features, not piloting [DE4]. AutoIRT cold-start calibration, BanditCAT exposure control [DE5] | Paid test |
| Busuu | many incl. zh, ja | Adaptive placement on vocabulary, grammar and reading [BU1] | "Only 5 minutes" [BU1]. An older story says about 10 min [BU2] | Mixed | "Suggested placement level", "just a suggestion" [BU1][BU3]. zh page maps CEFR↔HSK (approximate) [BU4] | Take it any time [BU4] | Free test |
| LingQ | many | No test. Known words accumulate while reading: paging marks remaining blue words known by default [LQ1] | n/a | Not tested. Self-report by reading | Level from known-word thresholds per language. Thresholds were revised, e.g. ja Intermediate 1 at 6,000 then 7,980 [LQ2] ESTIMATE | Importing a known-words list is not supported; users work around it via a lesson [LQ3] | Freemium (not verified) |
| Anki | any | No placement. Users suspend or skip known cards | n/a | **User's choice**: one note → several cards. Many split directions; some keep M+R on one card to save time [A1] | Deck stats | n/a | Free desktop (not verified) |
| GoEast vocab test (web) | zh | **3PL IRT with Bayesian estimation** [G1] | **about 20 questions**, 800+ calibrated items, HSK 1–9 [G1] | M (not detailed) | Vocab size, HSK level, downloadable word list [G1]. No interval shown | none documented | Free |
| HSKLord estimator (web) | zh | Adaptive, 4 item types incl. **character→pinyin** [HL1] | **20 questions** [HL1] | M and R items mixed in one score | **Highest HSK level with ≥60% correct** [HL1] | Warns it can't replicate listening, reading or writing [HL1] | Free |
| GyanMirai JLPT vocab size (web) | ja | Even sampling across N5–N1. A level's accuracy stands in for that level's list [GY1] | not found | M | Size estimate. About 60% at a level = "core words" known [GY1] | none | Free (vendor of paid courses) |
| martindbp placement (blog) | zh | Logistic regression: **prior from a self-reported HSK level**, words chosen by **entropy (active learning)**, refit until a stopping criterion [MD1] | not found | M (self-report vs test not confirmed) | Per-word P(known) → estimate [MD1] | Model-based | n/a |

---

## 2. Product notes (detail and sources)

### 2.1 WaniKani (Japanese kanji and vocabulary)
- **No placement and no skipping.** "There is no way to speed up or skip content on WaniKani. Not even
  if you email us and promise you know 10,000+ kanji." MEASURED [W1]. Requests for a test-out or
  placement test have run for years on the forum (threads 31038, 16515, 59980, 65270, 47361). A Trustpilot
  reviewer complains of no placement test and that support refuses to move a level forward. MEASURED that
  the complaints exist [W7].
- **Cost of no placement.** A learner who had passed N3 said it took about 4 months before reaching kanji
  they didn't know, but they still met new vocabulary on the way. ESTIMATE (single forum report) [W7].
- **Meaning and reading are separate prompts, both required.** "During your reviews, WaniKani will ask you
  to provide the readings and meanings for kanji and vocabulary separately". "You'll need to answer both
  correctly to complete the kanji 'set'". Same for vocabulary. MEASURED [W2][W3]. Reading answers are
  auto-converted to kana, meaning answers stay English. MEASURED [W4].
- **No multiple choice, on principle**: "does not and will not allow for multiple choice answers" because
  "you don't actually have to recall anything". MEASURED [W9].
- **How the two sides combine.** One SRS stage per item. The drop on failure is
  `new = current − ceil(incorrect/2) × penalty`, with penalty 2 at stage ≥5, otherwise 1. MEASURED [W5]
  (the KB formula; one commenter says the live code may differ). Community reports say a wrong reading and
  a wrong meaning both count. ESTIMATE [W5].
- **Words without kanji are meaning-only.** The 2023 kana-only vocabulary has only a meaning side, and
  typing the reading gives a shake, not a fail. MEASURED [W6].
- **Typos.** The Double-Check userscript, which lets you retype a typo or forgive it, is widely recommended
  "to help you avoid losing progress when answering with typos". MEASURED that it exists and is recommended [W10].
- **Paywall.** Early levels free. About $9/month, $89/year, $299 lifetime. ESTIMATE, dated third-party pages [W8].
- **Third party: KameSame** offers a "Placement Test" lesson mode where correct answers mark items burned,
  plus "Mark as Learned" after a correct answer. ESTIMATE (forum) [K1].

### 2.2 Bunpro (Japanese grammar and vocabulary)
- No vocabulary placement test found. Users mark vocab known or mastered one at a time or per deck. There is
  no multi-select, and "know all" on a unit reportedly does nothing. ESTIMATE (forum) [B1]. The official
  support page covers "marking grammar as known & setting manual SRS levels". MEASURED [B2].
- Vocab reviews hide the English by default so the learner infers meaning from the sentence. A "translate"
  setting shows the kanji and asks for typed English. Whether the reading is graded in vocab reviews is
  unclear from the sources. MEASURED (beta notes) and ESTIMATE (community) [B3].
- **JLPT mock tests** (Sep 2025): five complete tests per level. Passing adds a JLPT badge to the forum
  profile. One user found N4 mock scores of 78–85% close to their real result; another said the N3 mock did
  not reflect that summer's test. ESTIMATE (user reports) [B4].
- Paywall: free tier forever, 30-day Premium trial with no card. MEASURED [B5].

### 2.3 Renshuu (Japanese)
- "Selecting one of the 'I know this' options on the term intro screen sets the mastery for all vectors to
  a certain level (IIRC 2, 6, or 9). You will still be quizzed on that term as usual, there will just be a
  longer interval". ESTIMATE (forum user, from memory) [R1]. **This is the pattern of seeding "known" as a
  prior that practice still checks.**
- Separate facets: a kanji produces cards for meaning, each reading, stroke order, plus compounds.
  ESTIMATE (third-party review) [R2]. A forum topic asks for "schedule-specific mastery / split level for
  kanji→reading vs reading→kanji". MEASURED that the request exists [R3].

### 2.4 jpdb (Japanese)
- No placement test. The changelog says "Mark as known" moved from the deck dropdown to a "Deck state
  override" page. MEASURED [J1]. The FAQ lists grades Fail (1–2) and Pass (3–5), and "Never show this
  again" (blacklist). MEASURED [J2].
- **Meaning and reading on one self-graded card.** A user explains: know the meaning, the kanji and how to
  say it → Hard/Okay/Easy; know only some of those → "Something" (a fail); blank → "Nothing". Other users
  admit grading loosely, e.g. passing a card that missed only a rendaku. ESTIMATE (r/LearnJapanese) [J3].
- Never-forget counts toward coverage, while a blacklisted word disappears from the deck denominator, so
  "5000 words, you know 20%" becomes "4000 words, you know 0%". There is no bulk move between the two.
  ESTIMATE (user on WaniKani forum) [J4].

### 2.5 Migaku (immersion; Japanese, Chinese and others)
- Migaku's own Notion help page said a proper onboarding placement test did not exist yet. The workaround is
  to sort words Unknown / Track / Known / Ignore. MEASURED that it existed when written; it may be dated [MG1].
- Community: import a frequency list and mark the top 500 known; import known words from the home screen.
  ESTIMATE [MG2]. Staff call the known-word count a proxy for progress, not an exact figure.
  ESTIMATE [MG3].
- Cards are auto-promoted to Known once the interval passes about 20 days (another post says 14), and **Known
  is never demoted automatically**. ESTIMATE [MG4].

### 2.6 Kanshudo (Japanese)
- Infers a mastery level 0–4 for every kanji, word and grammar point from use and quizzes. "A strong Word
  Quiz result suggests you know more basic words too." Overall mastery level mapped to JLPT: level 19 = N5,
  29 = N4, 39 = N3, 49 = N2, 59 = N1. MEASURED [KS1].

### 2.7 Hack Chinese (Chinese)
- **Assume-known plus spot checks.** "Instead of marking all of them as memorized, the app tests you on
  some of the words it assumes you know each day". The check rate is configurable: "Fast" checks at most 30
  assumed-known words a day, "Slow" favours new words "at the cost of letting potential gaps … persist
  longer". MEASURED [H1][H2].
- The progress bar has a purple segment for words "assumed known but not yet checked" (2019). Words
  remembered at their first check get boosted intervals (2020). MEASURED [H5]. Users can check progress
  "against any level of the exam at any time". ESTIMATE (forum reply) [H6].
- Prompts: a reviewer says the card shows the character, and pinyin and tone are checked first, then the
  definition, all self-graded ("only works if you are honest with yourself"). ESTIMATE [H3]. A competitor
  lists recognition, recall, listening and typing (meaning→pinyin) modes. ESTIMATE, competitor source [H4].
- I found no dedicated placement **test**. Hack Chinese places by declared history, then verifies over
  time. INFERENCE from [H1][H2].

### 2.8 Skritter (Chinese and Japanese writing)
- Each word has separate **parts**: writing, tone, reading and definition. The API docs say "for reading
  prompts, don't show the definition until afterward; for definition prompts, don't show the reading until
  afterward", and tone, reading and definition prompts are scored only 1 (forgot) or 3 (got it). MEASURED [S3].
- Parts can be filtered per session. Beta-forum users complain tone prompts dominate, and the suggested fix is
  to uncheck tones. ESTIMATE [S4].
- Adding known words: there is no multi-select, so you "mark as learned" each word. Marking one word reportedly
  marked all earlier words in the list, and marking can cascade across decks. ESTIMATE and MEASURED [S1][S2].

### 2.9 Pleco (Chinese dictionary flashcards)
- Six test types including self-graded, multiple choice ("a list of up to five possible answers"),
  fill-in-the-blanks, stroke order and tone practice. "Ask For" chooses the tested field. MEASURED [P1][P2].
- **Scorefiles let a card have different scores for different types of test**: separate evidence per
  skill, not one blended score. MEASURED [P2].
- "Our multiple-choice tests always make sure that the number of characters in the headword match the
  number of syllables in all of the possible Pinyin answers". MEASURED [P3]. This removes the
  count-the-syllables shortcut.
- Typed pinyin answers need a tone number per syllable (`hao3`). ESTIMATE (2017 forum) [P4].

### 2.10 HelloChinese, LingoDeer
- HelloChinese: a third-party aggregator says a placement test exists. A Google Play reviewer says you can
  email support to be started higher. A review says the course is not mapped to HSK (about HSK 3–4 at the end).
  ESTIMATE [HC1][HC2]. I found no format or length details.
- LingoDeer: "'Test Outs' let you skip to the next unit without doing the previous lessons". No end-of-course
  test-out. A later level can be opened directly from the menu. The first unit is always free. MEASURED [LD1].

### 2.11 Duolingo (app placement)
- "At the beginning of a placement test, it's assumed that you're a novice … If you get a few questions
  right, we start asking tougher questions … we consider the difficulty of the questions we asked and
  whether you got them right or wrong, then we unlock the skills we think you already know." The test
  originally counted every answer "completely correct or completely incorrect—no in-between", and one
  learner was placed where lessons were all too easy, which led to partial-credit changes. MEASURED [D1].
- About 10 minutes (one guide says 5–10). Retake via "Jump here" or a course reset. ESTIMATE [D2].
- A WaniKani-forum user said the placement skipped most of the Japanese course but the content was still
  basic. ESTIMATE [D3].

### 2.12 Duolingo English Test (high-stakes, English)
- Opens with 15 to 18 adaptive Yes/No vocabulary items (real word vs English-like pseudoword such as
  "clerm"), one word at a time, 5 seconds each. A wrong vocab answer typically leads to an easier item.
  MEASURED [DE1][DE2].
- Item difficulty is estimated from linguistic features with a Rasch-style model rather than by piloting
  (Settles et al., TACL 2020). MEASURED [DE4]. AutoIRT calibrates cold-start items from item features, and
  BanditCAT selects items by Fisher information with Thompson sampling plus a randomisation step for
  exposure control. MEASURED [DE5]. An older scoring doc says the CAT ends after 25 items or 40 minutes.
  ESTIMATE [DE3].
- **Relevance to us:** the Yes/No-with-pseudowords format is rejected. The transferable parts are cold-start
  difficulty from item features (we have frequency and exam level) and randomised selection for exposure
  control. INFERENCE.

### 2.13 Busuu
- Adaptive ("the more questions you get right, the harder the test gets"). Help center: "only takes 5
  minutes", covers various skills, gives "a suggested placement level". The English page: "the result you
  get from the test is just a suggestion". MEASURED [BU1][BU3]. A 2017 story says 10 minutes on average,
  testing vocabulary, grammar, reading and comprehension. ESTIMATE (dated) [BU2]. The Chinese page maps
  CEFR to HSK (HSK 1 ≈ A1, HSK 4 ≈ B1), which is not an official equivalence. MEASURED [BU4].

### 2.14 LingQ
- No test. The known-word count grows as you read: by default, turning a page marks the remaining blue words
  Known. MEASURED [LQ1]. Levels come from per-language known-word thresholds, which were revised (ja
  Intermediate 1 reported at 6,000, later 7,980). ESTIMATE [LQ2]. Importing a known-words list is not
  supported, and users import a lesson then mark all known. ESTIMATE [LQ3].

### 2.15 Anki
- One note generates several cards (directions). r/LearnJapanese users mostly split recognition and recall.
  Some keep reading and meaning together on one recognition card because "separate reviews take longer for no
  reason". ESTIMATE (forum opinion) [A1]. A Chinese-Forums poster argues pronunciation should be drilled
  separately from meaning, on multi-character cards. ESTIMATE [A2].

### 2.16 Free web vocabulary and level tests (closest to what we are building)
- **GoEast Mandarin**: 3-parameter IRT, Bayesian estimation, "about 20 questions", 800+ calibrated items
  for HSK 1–9, result = vocab size + HSK level + downloadable word list. No interval shown, and the accuracy
  claims are the vendor's own. MEASURED (vendor) [G1].
- **HSKLord estimator**: 20 adaptive questions of four types (vocabulary, fill-in, **character→pinyin**,
  grammar). Result = "the highest level where you achieved at least 60 percent accuracy". States its own
  limits. MEASURED (vendor) [HL1].
- **GyanMirai (ja)**: samples evenly across N5–N1 and treats accuracy within a level as representative of
  the level list, with a 60% benchmark. MEASURED (vendor) [GY1].
- **Tofugu-listed Japanese Vocab Test**: a two-step test following Nation's Vocabulary Size Test approach.
  MEASURED (listing) [TF1].
- **NTT 語彙数推定テスト (Reiwa)**: a checkbox self-report test built for native speakers. Learners on
  r/LearnJapanese suspect it overstates learners, and results swing with how strictly people tick.
  ESTIMATE [N1].
- **martindbp (blog)**: logistic-regression placement with coefficients set from a user-provided rough
  HSK level, entropy-based word sampling, refit until a stopping criterion. MEASURED (author's blog,
  fragments only) [MD1].

### 2.17 Two research items that bear directly on the owner's decision 3
- **Zhang & Tamaoka, *Psychologia* 67(1), article 2023-A254**: "Japanese CFL learners, leveraging their L1
  knowledge in Chinese characters (kanji), demonstrated advanced understanding of word meanings in hanzi
  compared to pinyin". MEASURED (abstract) [L1]. This is the meaning-without-pinyin dissociation the owner
  described. The full text was not read (sample size unknown).
- **Zhou et al., BEA 2019 (W19-4403)**: a 3PL computerised adaptive vocabulary test for Chinese L2 with
  automatically generated items. A search extract claimed the CAT cut average length from 140 to 26 items
  while staying strongly correlated with a traditional placement test, but a second search could not
  confirm those numbers. ESTIMATE, unverified [L2].
- A 2024 SAGE Open study reported multiple-choice recognition items overestimating knowledge by about 20%
  relative to gap-fill post-tests. ESTIMATE (secondary summary only) [L3].

---

## 3. What serious JLPT and HSK learners rate as accurate vs annoying

The sources are mostly forum posts. No study measured how accurate any product's placement is. Treat these as
recurring opinions, not facts.

### Rated accurate or valued
1. **Demanding both meaning and reading.** WaniKani's whole model requires both sides for every kanji
   word [W2][W3], and the forum largely defends it. The Zhang & Tamaoka result [L1] gives the reason it
   matters for kanji-literate learners of Chinese. INFERENCE from [W2][L1].
2. **Recall or typed answers over multiple choice.** WaniKani refuses MC because "you don't actually have to
   recall anything" [W9]. Bunpro users say MC answers can be found "by process of elimination" [O1].
   INFERENCE: for a four-option placement, the counter-measures are distractor quality, an "I don't know" button
   and guess correction, not a format change.
3. **Verify, don't trust, declared knowledge.** Hack Chinese's spot-check of assumed-known words [H1][H2]
   and Renshuu's "I know this, but still quiz me later" [R1] both treat a declared or placed "known" as a
   starting point that practice confirms.
4. **Per-exam-level progress.** Hack Chinese lets you check progress against any exam level [H6], Kanshudo
   maps mastery to JLPT [KS1], and HSKLord/GyanMirai report per-level accuracy [HL1][GY1]. Learners want to see
   where they stand on the HSK/JLPT ladder. INFERENCE from the features existing and being advertised.
5. **Fair distractors.** Pleco matches syllable counts in pinyin MC [P3]. Our own Readings mode prefers the
   same syllable count but does not require it (wiki/features/calibration.tech.md:396-397).

### Rated annoying or inaccurate
1. **No placement at all.** WaniKani's level-1 start for experienced learners is a perennial complaint
   [W1][W7].
2. **Placement that over-places.** Duolingo's all-or-nothing scoring placed a learner into lessons that were
   all too easy [D1]. A Japanese-course user skipped most levels and still found the content basic [D3].
3. **Self-report that inflates.** The NTT checkbox test is seen as overestimating learners, with results
   depending on how strictly people tick [N1]. jpdb users admit loose self-grading [J3]. Migaku's known count is
   "a proxy" [MG3].
4. **"Known" that can't be undone.** Migaku never demotes Known automatically [MG4]. jpdb has no bulk move
   between blacklist and never-forget [J4]. Skritter's "mark as learned" cascades to earlier words [S2].
5. **Bulk-marking friction.** No multi-select and broken "know all" in Bunpro [B1] and Skritter [S1].
   LingQ cannot import a known list [LQ3].
6. **Typos punished as ignorance.** Typed reading answers fail on typos, which is why WaniKani's Double-Check
   script is popular [W10].
7. **Tone prompts dominating.** Skritter users turn tone prompts off because they crowd out everything else [S4].
   INFERENCE: tone should be tested inside the reading item, not as an extra item type.
8. **Placement that isn't a skill measure.** Busuu calls its own result "just a suggestion" [BU3]. HSKLord
   warns it can't replicate the real exam [HL1]. INFERENCE: learners accept a short test's limits when the
   product says so plainly.

---

## 4. Lessons for our design

Each lesson is INFERENCE unless marked otherwise. They assume the owner's decisions: adaptive four-option
items, no fake words, and both meaning and reading for zh and ja.

1. **Ask meaning and reading as two separate items about the same word, and score them separately.**
   WaniKani [W2], Skritter [S3], Pleco [P2] and Renshuu [R2][R3] all keep the two apart. Only jpdb blends
   them into one self-grade [J3]. Our check already pools the modes "separately, never averaged"
   (wiki/features/calibration.tech.md:450-455; wiki/features/calibration.md:157-158). The placement should
   report a **meaning result** and a **reading result**. For words probed in both, it should also report a
   **"meaning and reading" joint share**, the WaniKani-style "both required" figure, which is the one that
   answers the owner's question "do they actually know the word".
2. **Pair the two items on a shared subset of words, and delay feedback until both are answered.** Skritter
   hides the definition during a reading prompt and the reading during a definition prompt [S3]. Our check
   reveals the right answer after each item (wiki/features/calibration.md:36-38). In a pair that would leak the
   answer to the second item. Suggested order: meaning first, then reading, with both answers revealed
   together.
3. **The joint figure needs its own guess correction.** With four options, a pure guess gets both items
   right 1/16 of the time, against 1/4 for one item. A per-word joint state (both / meaning only / reading
   only / neither) is the useful output for the ja→zh cognate case [L1]: "meaning only" is exactly the
   kanji-literate learner who lacks the pinyin. The synthesis stage should derive the estimator. This
   survey only flags that ADR-051's single-mode K_b formula does not carry over unchanged.
4. **Length: 20–40 items is the product norm.** GoEast uses about 20 [G1], HSKLord 20 [HL1], the DET
   vocabulary section 15–18 [DE1], Busuu about 5 minutes [BU1] and Duolingo about 10 minutes [D2]. With
   zh/ja reading items added, a budget near 25 meaning + 10–15 reading items fits a phone session.
   ESTIMATE of minutes; our own per-item timing should be measured from `real_events.json` in another stage.
5. **Seed practice as "assumed known, to be checked", never as known.** Hack Chinese's spot-check rate [H2]
   and Renshuu's "still quizzed at longer intervals" [R1] are the patterns learners accept. Migaku's
   permanent Known [MG4] is the one they resent. This matches the planned separate evidence kind
   (TASK-1065) and the rule that placement never counts as "rated known".
6. **Report per exam level, with honest width, and never pass/fail.** Products report one level
   ("highest level with ≥60%" [HL1], "≈60% = core words" [GY1]) with no interval. Our report can do
   better: a known share per HSK/JLPT level with a range, the goal-path layout the owner prefers. Avoid
   the HSKLord-style threshold verdict, because the product must never predict pass/fail.
7. **Say plainly it is a suggestion, and make it easy to redo.** Busuu [BU3], Duolingo "Jump here" [D2]
   and HelloChinese's manual override [HC1] all allow correction. Retakes should use disjoint items and pool
   with earlier evidence, as calibration already pools runs (wiki/features/calibration.md:155-156).
8. **Cold start from what the learner tells us.** martindbp sets priors from a self-reported HSK level and
   samples by entropy [MD1]. Duolingo starts every learner as a novice [D1], which wastes items for advanced
   learners. DET predicts item difficulty from item features [DE4][DE5]. For us: start from the learner's
   stated goal level (the report's exam goal) and word frequency. Recalibrate item difficulty from responses
   later, with randomised selection among near-equal items to spread exposure [DE5].
9. **Reading items: make distractors fair, and keep tone inside the item.** Require the same syllable count
   (Pleco [P3]; ours only prefers it, calibration.tech.md:396-397). Keep tone-only distractors for zh,
   which our picker already does (calibration.tech.md:390-392). That lets the result say whether reading
   errors are mostly tone errors without adding Skritter-style tone prompts [S4]. Multiple choice also avoids
   the typo problem of typed readings [W10].
10. **Skip the reading item where it carries no information.** WaniKani's kana-only words are meaning-only
    [W6]. A Japanese word written in kana has no reading to test. The same goes for any zh/ja word whose
    reading distractors fail quality checks. INFERENCE.
11. **Label what the reading item measures.** A four-option reading item measures *recognising* the
    reading, not producing it. Pleco and WaniKani test production by typing [P4][W4]. The report should say
    "recognises the reading", not "can pronounce". INFERENCE.
12. **Keep the "I don't know" button and say why.** Elimination and familiarity guessing is the main
    complaint about multiple choice [O1][W9][L3]. The existing button (calibration.md:36-38) plus guess
    correction is the honest answer to that complaint without fake words. Tell learners up front that
    guessing lowers the accuracy of their result.

---

## 5. Sources

All URLs were reached through WebSearch result extracts only. None were opened with WebFetch (blocked; see top).

- [W1] WaniKani KB, skip content: https://knowledge.wanikani.com/wanikani/skip-content/ ; Trustpilot: https://ch.trustpilot.com/review/wanikani.com
- [W2] WaniKani KB, Readings vs Meanings: https://knowledge.wanikani.com/wanikani/japanese/readings-vs-meanings
- [W3] WaniKani KB, Unlocking Kanji / Vocabulary: https://knowledge.wanikani.com/getting-started/unlocking-kanji/ ; https://knowledge.wanikani.com/getting-started/unlocking-vocabulary
- [W4] WaniKani KB, Why isn't my answer accepted: https://knowledge.wanikani.com/wanikani/common-mistakes/
- [W5] WaniKani KB, SRS stages: https://knowledge.wanikani.com/wanikani/srs-stages/ ; forum: https://community.wanikani.com/t/is-there-a-difference-between-getting-wrong-a-reading-or-a-meaning/38855 ; https://community.wanikani.com/t/what-happens-if-you-get-an-item-wrong-twice-or-more-in-one-session/41966
- [W6] Kana-only vocabulary additions (2023): https://community.wanikani.com/t/kana-only-vocabulary-additions/61796
- [W7] Forum threads: https://community.wanikani.com/t/a-review-now-option-or-a-placement-test/31038 ; https://community.wanikani.com/t/testing-out/16515 ; https://community.wanikani.com/t/i-am-an-intermediate-level-learner-of-japanese-but-i-have-to-start-from-the-beginning-on-wanikani/59980 ; https://community.wanikani.com/t/starting-out-as-intermediate/65270 ; https://community.wanikani.com/t/determining-which-level-to-reset-to/59639
- [W8] Pricing (third-party, dated): https://www.alllanguageresources.com/wanikani/ ; https://www.mezzoguild.com/wanikani-review ; https://community.wanikani.com/t/cost-past-the-first-two-levels/18054
- [W9] WaniKani KB, Why no multiple choice: https://knowledge.wanikani.com/wanikani/multiple-choice/
- [W10] Double-Check userscript: https://community.wanikani.com/t/userscript-double-check-version-2x/31456 ; https://greasyfork.org/scripts/35063/code ; https://community.wanikani.com/t/wrong-answers-due-to-typos/55872
- [K1] KameSame thread: https://community.wanikani.com/t/kamesame-a-fast-feature-rich-japanese-memorization-webapp/31319
- [B1] Bunpro forum: https://community.bunpro.jp/t/easier-way-to-mark-vocab-as-known/51578 ; https://community.bunpro.jp/t/strategies-for-non-beginners/179895
- [B2] Bunpro support: https://bunpro.jp/support/using-bunpro
- [B3] Bunpro beta and vocab: https://community.bunpro.jp/t/bunpro-beta-june-24th-2021/34885 ; https://community.bunpro.jp/t/vocabulary/51670
- [B4] Bunpro JLPT tests (Sep 2025): https://community.bunpro.jp/t/bunpro-jlpt-tests-new-feature-sep-20th-2025/149777
- [B5] Bunpro pricing: https://bunpro.jp/pricing
- [R1] Renshuu forum ("I know this"): https://www.renshuu.org/forums/topics/9611/Is_there_a_way_to_see_all_words_marked_as_&quot;I_know_this&quot; (exact post not opened; the quote came from a search extract over renshuu forum topics)
- [R2] Coto Academy review: https://cotoacademy.com/learning-japanese-with-renshuu-app-review/
- [R3] Renshuu forum, split mastery: https://www.renshuu.org/forums/topics/7939/Schedule-specific_mastery_/_split_level_for_kanji%E2%86%92reading_vs_reading%E2%86%92kanji/p0
- [J1] jpdb changelog: https://jpdb.io/changelog
- [J2] jpdb FAQ: https://jpdb.io/faq
- [J3] r/LearnJapanese (mirror): https://redlib.hbubli.cc/r/LearnJapanese/comments/1ksd1hv/daily_thread_simple_questions_comments_that_dont/mtna1wm/?context=3
- [J4] jpdb on WaniKani forum: https://community.wanikani.com/t/getting-started-with-jpbd/58352
- [MG1] Migaku Notion: https://magenta-dirigible-0d8.notion.site/Teach-Migaku-the-words-you-already-know-de6c68b5f05848e98f56b24203d4bf3e
- [MG2] Migaku community: https://migaku.com/community/m/1310788995243835482 ; https://migaku.com/community/m/1374700378523832331
- [MG3] Migaku community: https://migaku.com/community/m/1305584195099164767
- [MG4] Migaku community: https://migaku.com/community/m/1371687365780963421 ; https://migaku.com/community/m/1372420470602993684
- [KS1] Kanshudo: https://www.kanshudo.com/howto/mastery ; https://www.kanshudo.com/howto/automatic_mastery
- [H1] Hack Chinese, Assuming knowledge: https://www.hackchinese.com/study-guide/assuming-knowledge
- [H2] Hack Chinese, Assumption check rate: https://www.hackchinese.com/study-guide/assumption-check-rate
- [H3] LTL review: https://ltl-school.com/hack-chinese/
- [H4] HSKLord comparison (competitor): https://hsklord.com/blog/hack-chinese-review
- [H5] Hack Chinese updates: https://www.hackchinese.com/updates?year=2019 ; https://www.hackchinese.com/updates?year=2020
- [H6] Domino forum: https://forum.dominochinese.com/channels/vocab/practice-vocab-with-hack-chinese
- [H7] Capterra: https://www.capterra.com/p/231719/Hack-Chinese/
- [S1] Skritter forum: https://forum.skritter.com/t/adding-words-you-already-know/4169 ; Skritter docs: https://docs.skritter.com/article/207-vocabulary-faq
- [S2] Skritter forum: https://forum.skritter.com/t/learn-single-words-marks-all-up-to-position/4177 ; https://docs.skritter.com/article/287-unexpected-words-being-added-after-learning-activity
- [S3] Skritter API docs: https://www.skritter.com/api/v0/docs/studying ; review: https://www.saymei.app/guides/skritter-review
- [S4] Skritter beta forum: https://beta.skritter.com/forum/topic?id=1958312107
- [S5] StudyCLI: https://studycli.org/what-is-skritter
- [P1] Pleco manual 3.1: https://android.pleco.com/manual/310/flash.html
- [P2] Pleco manual 2.4: https://android.pleco.com/manual/240/flash.html ; forum: https://www.plecoforums.com/threads/flash-card-test-types.3560
- [P3] Pleco iPhone manual: https://pleco.com/ipmanual/flash.html
- [P4] Pleco forum / blog: https://www.plecoforums.com/threads/flashcards-learning-workflow.5038/latest ; https://bewagner.github.io/blog/my-pleco-flashcard-setup
- [HC1] HelloChinese: https://superchinese.hubpickr.com/compare/hellochinese ; https://play.google.com/store/apps/details?id=com.hellochinese&hl=en_US
- [HC2] Mandarin Mosaic review: https://mandarinmosaic.com/blog/hellochinese-review
- [LD1] LingoDeer support: https://support.lingodeer.com/en/support/solutions/articles/61000281874-why-is-there-no-test-out-at-the-end-of-a-course- ; https://support.lingodeer.com/en/support/solutions/61000134750
- [D1] Duolingo blog: https://blog.duolingo.com/partial-credit-improvements-to-duolingos-placement-test/
- [D2] Lume Test guides (third-party): https://lumetest.com/blog/det/the-duolingo-placement-test-what-to-know-about-it ; https://lumetest.com/blog/duolingo-english-test/how-to-retake-the-placement-test-on-duolingo
- [D3] WaniKani forum: https://community.wanikani.com/t/duolingo-why-you-hate/19819?page=2
- [DE1] DET short paper: https://s3.amazonaws.com/duolingo-papers/other/DET_ShortPaper.pdf ; whitepaper: https://duolingo-papers.s3.amazonaws.com/reports/Duolingo_whitepaper_test_scoring_2024_v1.pdf
- [DE2] BanditCAT/AutoIRT (18 Y/N items, 5 s): https://arxiv.org/pdf/2410.21033
- [DE3] DET technical manual copy (third-party host): https://www.scribd.com/document/590100267/Det-Technical-Manual-Current
- [DE4] Settles et al., TACL 2020: https://aclweb.org/anthology/2020.tacl-1.17.pdf
- [DE5] AutoIRT: https://arxiv.org/pdf/2409.08823 ; BanditCAT: https://arxiv.org/html/2410.21033v1
- [BU1] Busuu help: https://help.busuu.com/hc/en-us/articles/16526383831569-What-is-a-Placement-Test
- [BU2] 2017 story: https://learningnews.com/news/busuu/2017/busuu-helps-employees-to-start-language-learning-at-the-right-level
- [BU3] Busuu English placement: https://busuu.com/en/english/placement-test
- [BU4] Busuu Chinese placement: https://www.busuu.com/en/chinese/chinese-placement-test
- [LQ1] LingQ support: https://lingq-support.groovehq.com/help/how-do-i-increase-my-known-words
- [LQ2] LingQ forum: https://forum.lingq.com/t/recent-updates-to-known-word-thresholds/37492?page=2 ; https://www.lingq.com/help/avatar/
- [LQ3] LingQ forum: https://forum.lingq.com/t/filling-out-known-words-for-new-users/162895
- [A1] r/LearnJapanese (mirror): https://reddit.birdcat.cafe/r/LearnJapanese/comments/1ih45a9/daily_thread_simple_questions_comments_that_dont/mb0dso7 ; Anki forum: https://forums.ankiweb.net/t/note-types-for-japanese/45033
- [A2] Chinese-Forums: https://chinese-forums.com/forums/topic/58045-flashcardsanki-splitting-up-pronunciation-and-meaning
- [G1] GoEast vocab test: https://goeastmandarin.com/chinese-vocabulary-test/
- [HL1] HSKLord estimator: https://hsklord.com/tools/hsk-estimator
- [GY1] GyanMirai: https://www.gyanmirai.com/tools/japanese-vocabulary-size-test
- [TF1] Tofugu listing: https://www.tofugu.com/japanese-learning-resources-database/japanese-vocab-test/
- [N1] r/LearnJapanese on the NTT test (mirror): https://reddit.fabiomanganiello.com/r/LearnJapanese/comments/195o0oy/test_how_many_words_you_know_in_japanese
- [MD1] martindbp: https://martindbp.com/posts/chinese-placement-test/
- [L1] Zhang & Tamaoka, Psychologia: https://www.jstage.jst.go.jp/article/psysoc/67/1/67_2023-A254/_article/-char/en
- [L2] Zhou et al., BEA 2019: https://aclweb.org/anthology/W19-4403.pdf
- [L3] SAGE Open 2024 (via secondary summary): https://doaj.org/article/1639061c58c247588e670f4958f2f547 ; https://elearningindustry.com/recognition-is-not-recall-why-your-multiple-choice-quizzes-overstate-learning
- [O1] Bunpro forum on elimination: https://community.bunpro.jp/t/recognition-in-bunpro/38750 ; https://community.bunpro.jp/t/something-i-dont-understand-about-bunpro/7941

## 6. Not verified / gaps
- Question counts for Duolingo app placement, Busuu, HelloChinese and LingoDeer test-outs: none published in what I found.
- HelloChinese placement format: not found at all.
- Hack Chinese: whether a failed spot check resets the word to new, and whether its tone check is separate from the pinyin check.
- Renshuu "I know this" preset levels (2, 6, 9) come from one user's memory.
- W19-4403 "140 → 26 items": the paper was not opened and a second search did not confirm the numbers.
- Paywall prices: mostly third-party and possibly dated. Several marked "not verified".
- No source measured how accurate any product's placement is against a later outcome. Every "accurate" judgment in section 3 is user opinion.
