# Vocabulary placement test: literature review (research stage)

Date: 2026-11-18. Stage: LITERATURE. Feeds TASK-1073 (the placement-test research and design task).
Owner decisions, which this review does not reopen: (1) build on the **adaptive check** (the existing four-option items,
chosen adaptively, with a stopping rule); (2) **no fake words, pseudowords or Yes/No self-report**; (3) for **Chinese and
Japanese, test both meaning (definition) and reading (pronunciation)**. English is tested on meaning only.

## How to read this file

- **Labels.** MEASURED = a number a cited study reports, or one I computed exactly from a stated formula. ESTIMATE = a number I
  derived from a model with stated assumptions. INFERENCE = my reasoning from the sources to our design. Each finding in Part B
  carries one label.
- **How much I checked.** `WebFetch` could not reach any publisher or repository host in this session. It failed on
  `vuw-web.matrix.squiz.cloud`, `www.lextutor.ca`, `openaccess.hacettepe.edu.tr` and `scholarspace`-type hosts (DNS refused),
  so I stopped trying, as the session rules require. **Every source below was checked through search-engine abstracts and
  snippets only, never the full text.** Where a number appears only in a secondary summary I say so. To read full texts, these
  hosts would have to be allowed in the session's network settings.
- **Numbering.** Bibliography items are numbered 1–67 across Part A. "A2-18" means section A2, item 18.
- **Paywalls.** [PW] = publisher paywall (abstract free). [OA] = an open copy exists at the link given. [?] = access unclear.
- **Codebase anchors** (read in this session): `wiki/features/calibration.tech.md:274` (a skip is recorded as incorrect),
  `:331` (person curve `p(z) = 0.25 + 0.75·σ(slope·(z − midpoint))`, guess floor fixed), `:354–360` (measured precision by item
  count), `:388–392` (reading distractors: homophones excluded, tone-only distractors kept), `:404` (English reading mode
  refused), `:453` (meaning and reading modes pooled separately); `wiki/decisions/ADR-051-vocabulary-size-from-calibration-frame.md:40`
  (`K_b = c/n − (1/3)·w/n`, skip = not known); `services/irt/calibrator.py:1-17` (2PL with no guessing floor, theta = logit of
  accuracy), `:32-35, 113-115` (shrinkage toward a seeded difficulty with pseudocount k = 10).

---

## Part A: Annotated bibliography

### A1. Vocabulary size and levels tests, and how valid four-option meaning items are

1. **Nation, I.S.P. & Beglar, D. (2007). A vocabulary size test. *The Language Teacher* 31(7), 9–13.** [?]
   Citation confirmed by search (via the Holster and Lake TEVAL PDF, https://teval.jalt.org/sites/default/files/26_01_01_Holster_Lake_vocab_size_0.pdf).
   The VST is a four-option meaning-recognition test sampled by 1,000-word frequency bands. Its size estimate is the raw score
   multiplied by a constant (100 or 200), which is why guessing inflates it (see Stewart 2014). *Relevance:* the closest
   template for our check (four options, frequency bands). Its design detail (14 bands × 10 items) comes from Beglar (2010)
   summaries and from my memory of the test, not from the 2007 text.

2. **Beglar, D. (2010). A Rasch-based validation of the Vocabulary Size Test. *Language Testing* 27(1), 101–118.** [PW]
   Reported (in secondary citations) that a 10-items-per-1,000-words sampling ratio estimates knowledge "with a high degree of
   precision", and that **as few as 5 items per band** give adequate reliability and item separation **for the test as a
   whole**. Sample size not confirmed. *Relevance:* whole-test reliability can be good with few items per band. Gyllstad et al.
   (2021, A1-5) show that this does **not** carry over to per-band estimates. That distinction matters for the per-exam-level output.

3. **Webb, S., Sasao, Y. & Ballance, O. (2017). The updated Vocabulary Levels Test. *ITL – International Journal of Applied
   Linguistics* 168(1), 33–69.** https://www.lextutor.ca/tests/webb_sasao_ballance_2017.pdf [OA, but the host was not reachable this session]
   Two new forms covering the 1K–5K levels, drawn from the BNC/COCA lists and validated within Messick's framework (confirmed by
   search). The 30 items per level, the matching format and the mastery cut-offs (29/30 for 1–3K, 24/30 for 4–5K) are **from
   memory, unverified this session**. *Relevance:* a levels test reports mastery **per level**, which is the shape of our
   exam-level output. It needs many items per level to do so.

4. **Stoeckel, T., McLean, S. & Nation, P. (2021). Limitations of size and levels tests of written receptive vocabulary
   knowledge. *Studies in Second Language Acquisition* 43(1), 181–203.** https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/limitations-of-size-and-levels-tests-of-written-receptive-vocabulary-knowledge/00A2861F34D3AE984AB2D61AF50F482F [PW; author preprint at a VUW host not reachable this session]
   A state-of-the-art review. It names the sources of **overestimation** in meaning-recognition formats (guessing and test-taking
   strategies, assumed knowledge of whole word families) and recommends meaning-recall items, fewer word-family assumptions and
   adequate test length. Critiqued by Webb (2021) in "A different perspective" (same journal), who argues the tests serve their
   reading-focused purpose. *Relevance:* our four-option format measures **recognition**, an upper-leaning estimate. The result
   should be labelled that way.

5. **Gyllstad, H., McLean, S. & Stewart, J. (2021). Using confidence intervals to determine adequate item sample sizes for
   vocabulary tests. *Language Testing* 38(4), 558–579.** https://journals.sagepub.com/doi/abs/10.1177/0265532220979562 [PW]
   Bootstrapped confidence intervals for **individual learners'** band estimates, using adult L1-Japanese learners on two English
   formats with 1,000 words each. Conclusion: 5–10 items per 1,000-word band are rarely adequate; **30 or more items per band**,
   and tests with fewer bands, are recommended. *Relevance:* a 3–8-minute test cannot measure 6–9 exam levels **directly** to
   that standard. Per-level counts must therefore come from a model that borrows strength across levels.

6. **Gyllstad, H., Vilkaitė, L. & Schmitt, N. (2015). Assessing vocabulary size through multiple-choice formats: issues with
   guessing and sampling rates. *ITL* 166(2), 278–306.** https://eprints.nottingham.ac.uk/32284 [OA repository record]
   Criterion-related validation of the VST against an open interview test. The **multiple-choice format overestimated size**
   relative to the interview, attributed to guessing and elimination strategies. Higher sampling rates are needed. Sample size
   not confirmed. *Relevance:* independent support for A1-4.

7. **McLean, S., Stewart, J. & Batty, A.O. (2020). Predicting L2 reading proficiency with modalities of vocabulary knowledge: a
   bootstrapping approach. *Language Testing* 37(3), 389–411.** Accepted version: https://researchmap.jp/stuartmclean/published_papers/24584839/attachment_file.pdf [OA]
   **N = 103** learners answered 1,000 items (NGSL 3K band) in four formats: Yes/No, form recall, meaning recall and meaning
   recognition. Simulated tests of 5–200 items were correlated with TOEIC Reading. **Meaning recall correlated highest at every
   test length, then form recall. Recognition formats were weaker predictors.** *Relevance:* if the placement result is used to
   predict reading level (test difficulty), a recognition score is a weaker predictor. Validation should check predictions
   against later reading performance rather than assume them.

8. **Kremmel, B. & Schmitt, N. (2016). Interpreting vocabulary test scores: what do various item formats tell us about
   learners' ability to employ words? *Language Assessment Quarterly* 13(4), 377–392.** https://nottingham-repository.worktribe.com/output/1126824 [PW]
   Compared four item formats against learners' ability to use the words. A thesis summary says all formats showed considerable
   measurement error and that multiple choice may be the most useful; the exact figures are **unverified**. *Relevance:* no
   format is clean, and multiple choice is defensible.

9. **Hashimoto, B. (2021). Is frequency enough? The frequency model in vocabulary size testing. *Language Assessment
   Quarterly*.** https://scholarsarchive.byu.edu/facpub/6673 [OA record]; thesis https://scholarsarchive.byu.edu/etd/5958
   **N = 403** learners on a 10% systematic sample of the first 5,000 COCA words (VAST test). Rasch difficulty correlated with
   frequency at **r = 0.50 (r² = 0.25)**. The thesis found r = 0.474 over 501 items, falling to **r = 0.306 when frequency was
   grouped into 1,000-word bands**. The thesis and article probably share data. Corroborated by Akase (2022, *Language Testing
   in Asia*, https://link.springer.com/doi/10.1186/s40468-022-00155-8): item difficulty overlaps heavily across frequency bands.
   *Relevance:* **frequency is a weak prior on item difficulty.** A cold-start prior from Zipf must be wide, and per-item
   difficulties must be learned from responses.

10. **Brysbaert, M., Mandera, P., McCormick, S. & Keuleers, E. (2019). Word prevalence norms for 62,000 English lemmas.
    *Behavior Research Methods* 51, 467–479.** https://link.springer.com/10.3758/s13428-019-01272-8 [OA]
    "Prevalence" (the share of people who know a word, crowdsourced) predicts word processing **over and above** frequency.
    L1 English adults. *Relevance:* by analogy, a per-word "learner prevalence" learned from our own answers is the right
    replacement for frequency once data accrue (INFERENCE).

11. **Laufer, B. & Ravenhorst-Kalovski, G. (2010). Lexical threshold revisited. *Reading in a Foreign Language* 22(1), 15–30.**
    https://scholarspace.manoa.hawaii.edu/items/eaead47e-853e-4797-ba6f-596df150c1d7 [OA]
    Proposes ~4,000–5,000 word families for 95% text coverage (minimal comprehension) and ~8,000 for 98% (optimal). The exact
    values are contested (see the critique in the same search). *Relevance:* background only, for linking a range to reading
    materials. English word-family thresholds do not transfer directly to Chinese or Japanese.

12. **Gonzalez-Fernandez, B. & Webb, S. (2024). How well are primary and secondary meanings of L2 words acquired? *SSLA*.**
    https://eprints.whiterose.ac.uk/209826/ [OA preprint]
    Learning a further meaning of a familiar word was as hard as learning the primary meaning of an unfamiliar word. *Relevance:*
    supports testing **one lemma at its rank-1 sense** (TASK-1062), and treating "knows the word" as "knows its main sense".

### A2. Guessing, "I don't know", and score correction

13. **Zhang, X. (2013). The I Don't Know option in the Vocabulary Size Test. *TESOL Quarterly* (volume/issue not confirmed; doi 10.1002/tesq.98).** https://zendy.io/title/10.1002/tesq.98 [PW]
    **N = 150** Chinese first-year university students, randomly assigned to three VST versions: original, with IDK, and with
    IDK plus a penalty warning. A meaning-recall task followed. **IDK reduced guessing but also suppressed partial knowledge.**
    Whether to use it depends on the purpose. *Relevance:* our check already has IDK, so expect fewer blind guesses but some
    under-credit of partly known words.

14. **Stoeckel, T., Bennett, P. & McLean, S. (2016). Is "I don't know" a viable answer choice on the Vocabulary Size Test?
    *TESOL Quarterly* 50(4), 965–975.** https://www.researchgate.net/publication/311665049 [?]
    Simulation study. **Different learners use IDK differently, and that weakens the correlation with meaning-recall
    knowledge.** Exact figures unverified.

15. **Stoeckel, T. et al. (2019). The relationship of four variants of the Vocabulary Size Test to a criterion measure of
    meaning recall vocabulary knowledge. *System* 87, 102161.** https://www.researchgate.net/publication/336560126 [PW]
    **N = 200** Japanese university students, randomly assigned to monolingual, monolingual + IDK, bilingual, or bilingual + IDK.
    Correlation with meaning recall: **bilingual + IDK r = .77, significantly lower than the other three (r = .88–.91)**,
    attributed to differences in IDK use. IDK use tracked proficiency and frequency, and **guesses were more often informed than
    uninformed**. For estimating reading vocabulary size the authors recommend meaning recall or adjusted VST scores.
    *Relevance:* our check is bilingual (L1 definitions) with IDK, the variant that did worst here. The scoring model must
    absorb **per-person differences in IDK use**, not assume everyone guesses or everyone skips.

16. **Stewart, J. (2014). Do multiple-choice options inflate estimates of vocabulary size on the VST? *LAQ* 11, 271–282.** [PW]
    and **Stewart, J. & White, D.A. (2011). Estimating guessing effects on the Vocabulary Levels Test for differing degrees of
    word knowledge. *TESOL Quarterly* 45(2), 370–380.** https://tus.elsevierpure.com/en/publications/estimating-guessing-effects-on-the-vocabulary-levels-test-for-dif-4/ [PW]
    Multiple-choice options inflate size estimates. Stewart & White (as summarised by Kremmel & Schmitt) estimate the VLT raw score
    inflation at roughly **16–17 points on a 99-item test**, tapering off once more than 60% of words are known, and note that
    the matching format makes items depend on each other. *Relevance:* the guess correction matters most for **low** scorers,
    which is exactly the beginner end of a placement test.

17. **Holster, T. & Lake, J. (2016). Guessing and the Rasch model. *LAQ* 13(2)** and **Stewart, J., McLean, S. & Kramer, B.
    (2017). A response to Holster and Lake regarding guessing and the Rasch model. *LAQ* 14(1).** https://eld.bl.uk/catalog/100041790523_0x000001 [PW]
    A debate over whether Rasch fit statistics detect guessing. The response argues they do not, and discusses using the
    **3PL** model. *Relevance:* do not rely on Rasch fit to clean up guessing; model the guess floor explicitly (as
    `calibration.tech.md:331` already does for the person curve).

18. **Elgort, I. (2013). Effects of L1 definitions and cognate status of test items on the Vocabulary Size Test. *Language
    Testing* 30(2), 253–272.** https://eld.bl.uk/catalog/100180908557_0x000001 [PW]
    **N = 121** Russian-speaking learners. Scores were significantly higher on the **bilingual** (L1-definition) VST, and **items
    were reliably easier when they were cognates**. The L1 benefit was larger at low proficiency, and the cognate advantage shrank
    as frequency rose (per secondary summary). *Relevance:* direct evidence that item difficulty needs **an L1 × cognate term**,
    and that the term interacts with frequency.

### A3. Computerised adaptive testing: models, stopping, exposure, estimation

19. **Linacre, J.M. (2006). Computer-adaptive tests (CAT), standard errors and stopping rules. *Rasch Measurement Transactions*
    20(2), 1062.** https://rasch.org/rmt/rmt202f.htm [OA]
    Item information is P(1−P) and SE = 1/√(Σ information), so precision peaks when P = 0.5 for each item. The note tabulates
    targeting against SE and the minimum number of items. A companion RMT note (Halkitis 1993, https://www.rasch.org/rmt/rmt64cat.htm)
    targets items about 0.5 logits easier than the estimate and reports SE ≈ 0.4 logits after 30 items. *Relevance:* the
    arithmetic behind any stopping rule. See B3 for the guessing-floor version.

20. **Babcock, B. & Weiss, D.J. (2012). Termination criteria in computerized adaptive tests: do variable-length CATs provide
    efficient and effective measurement? *Journal of Computerized Adaptive Testing*.** (DOI 10.7333/1212-0101001) [OA journal; not fetched]
    Compares stopping rules (SE threshold, minimum information, change in theta) and proposes a change-in-theta rule. The SE rule
    is the most studied. Exact recommended thresholds **unverified**. A 2018 *Behavior Research Methods* simulation
    (https://link.springer.com/article/10.3758/s13428-018-1068-x) used SE = 0.35 (lenient) and 0.30 (stringent) as typical settings.

21. **Choi, S.W., Grady, M.W. & Dodd, B.G. (2010/2011). A new stopping rule for computerized adaptive testing. *Educational and
    Psychological Measurement* 70.** https://typeset.io/pdf/a-new-stopping-rule-for-computerized-adaptive-testing-2pl15fyr0o.pdf [?]
    **Predicted standard error reduction (PSER):** stop when one more item would barely reduce the SE, even if the SE target has
    not been reached. It uses pools efficiently and helps people the bank targets poorly. *Relevance:* our bank will be thin at
    the extremes (complete beginners, near-native learners), which is exactly where PSER helps.

22. **Bock, R.D. & Mislevy, R.J. (1982). Adaptive EAP estimation of ability in a microcomputer environment. *Applied
    Psychological Measurement* 6.** [PW] (secondary sources only)
    The expected a posteriori (EAP) estimate is finite for all-correct and all-wrong patterns, where maximum likelihood diverges,
    and it is more stable early in an adaptive test. The cost is shrinkage toward the prior at the extremes. *Relevance:* a short
    placement test **must** use a Bayesian estimate. `services/irt/calibrator.py:9-11` currently clips accuracy at 5–95% instead.

23. **Georgiadou, E., Triantafillou, E. & Economides, A. (2007). A review of item exposure control strategies for CAT developed
    from 1983 to 2005. *Journal of Technology, Learning, and Assessment* 5.** https://ejournals.bc.edu/index.php/jtla/article/view/1647 [OA]
    Also: **Kingsbury & Zara (1989)** "randomesque" selection, which picks at random among the 5 most informative items, and
    **Sympson & Hetter (1985)** exposure parameters (secondary sources). A testlet simulation found Sympson-Hetter capped exposure
    but used the pool poorly, while randomisation methods kept exposure low but used only ~70% of the pool. *Relevance:* we have
    no security stake. Randomesque selection is enough to vary retakes and spread calibration data across the pool (INFERENCE).

24. **Mislevy, R.J. & Wu, P.-K. (1996). Missing responses and IRT ability estimation: omits, choice, time limits, and adaptive
    testing.** ETS RR-96-30. https://www.ets.org/research/policy_research_reports/publications/report/1996/hxus.html [OA]
    and **Lord, F.M. (1974). Estimation of latent ability and item parameters when there are omitted responses. *Psychometrika*
    39(2), 247–264.** [PW]
    Omitted responses should not simply be scored wrong: they are usually not ignorable, and scoring them wrong biases ability
    downward, especially for strong examinees. A related model treats the "don't know" choice as a second latent process
    (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6297845/). *Relevance:* how the model treats our IDK answer matters. B5 shows a
    simple, correct treatment.

25. **Han, K.T. (2012). Fixing the c parameter in the three-parameter logistic model. *Practical Assessment, Research &
    Evaluation*.** https://openpublishing.library.umass.edu/pare/article/id/1349 [OA]
    A 3PL with **c fixed at 1/k** (k = number of options) performed well in simulated and real data. Free estimation of c needs
    samples in the thousands, because its standard errors are huge below about 2,000 (secondary sources). *Relevance:* with our
    numbers of users, c must be fixed or tightly bounded, never estimated per item.

### A4. Calibrating item difficulty with few users

26. **McCarthy, A.D., Yancey, K.P., LaFlair, G.T., Egbert, J., Liao, M. & Settles, B. (2021). Jump-starting item parameters
    for adaptive language tests. *EMNLP 2021*, 883–899.** https://aclanthology.org/2021.emnlp-main.67 [OA]
    Duolingo English Test data. A generalised linear model with BERT features predicted item difficulty with **as few as 500 test
    takers and about 6 exposures per item over about 4,000 items**, so new items can be used without piloting.

27. **Settles, B., LaFlair, G.T. & Hagiwara, M. (2020). Machine learning-driven language assessment. *TACL* 8, 247–263.**
    https://aclanthology.org/2020.tacl-1.17 [OA]
    Item difficulty predicted from linguistic features instead of pilot testing, used for a live high-stakes CAT. *Relevance
    (26–27):* the established way to cold-start an adaptive language test is **feature-predicted difficulty as a prior, then
    update from responses**. Our features would be Zipf, exam level, part of speech, script (kana-only or kanji), L1 cognate
    status and distractor similarity (INFERENCE).

28. **Pelánek, R. (2016). Applications of the Elo rating system in adaptive educational systems. *Computers & Education*.**
    https://www.fi.muni.cz/~xpelanek/publications/CAE-elo.pdf [OA]
    Treats each answer as a "match" between learner and item, updating both online. Elo difficulty estimates correlate highly
    with joint maximum-likelihood estimates. **Pankiewicz (2020)** (https://library.apsce.net/index.php/ICCE/article/view/3939)
    found Elo beats proportion-correct at small samples in the cold-start phase. *Relevance:* an online, cheap difficulty update
    that fits a small Postgres table. The product already has an ELO system.

29. **König, C., Spoden, C. & Frey, A. (2020). An optimized Bayesian hierarchical two-parameter logistic model for
    small-sample item calibration. *Applied Psychological Measurement*.** https://publikationen.ub.uni-frankfurt.de/files/54836/0146621619893786.pdf [OA]
    Hierarchical priors pool information across items. A 2023 follow-up (https://link.springer.com/10.3758/s13428-022-02000-5)
    reports unbiased estimates at **N = 50**, but only under one hyperprior and limited conditions. Matteucci & Veldkamp: empirical
    priors beat vague and generic informative priors in a 20-item test. *Relevance:* a hierarchical prior with "difficulty =
    f(features) + item residual" is the principled form of `apply_prior()` (`calibrator.py:113-115`).

30. **Mislevy, R.J. (1988). Exploiting auxiliary information about items in the estimation of Rasch item difficulty
    parameters. *Applied Psychological Measurement* 12, 725–737**, and **De Boeck, P. & Wilson, M. (eds.) (2004). *Explanatory
    Item Response Models*** (LLTM: Fischer 1973). [PW] (bibliographic records only)
    Item difficulty can be modelled as a function of item features (LLTM), with the residual left free (Mislevy's "collateral
    information"). *Relevance:* the formal name for the A4-26/27 approach.

### A5. Dimensions of word knowledge, and testing more than one per word

31. **Nation, I.S.P. (2001/2013/2022). *Learning Vocabulary in Another Language*, chapter "Knowing a word". Cambridge.**
    https://resolve.cambridge.org/core/books/abs/learning-vocabulary-in-another-language/knowing-a-word/11C16210DBC513BC703EB530D52803C5 [PW]
    Word knowledge splits into **form** (spoken, written, word parts), **meaning** (form–meaning link, concept and referents,
    associations) and **use**, each receptive and productive: nine components in all (Schmitt 2019 summary). *Relevance:* our
    two dimensions map to **form–meaning (meaning items)** and **written form → spoken form (reading items)**. In logographic
    scripts the second is not predictable from the first, unlike in English.

32. **Henriksen, B. (1999). Three dimensions of vocabulary development. *SSLA* 21(2), 303–317.** https://scilit.com/publications/e5f13410fc8ae11ecec7acec5ccc95d3 [PW]
    Three dimensions: **partial → precise** knowledge, depth, and receptive → productive. *Relevance:* semantically close
    distractors (ADR-025) push our meaning items toward the "precise" end.

33. **Laufer, B. & Goldstein, Z. (2004). Testing vocabulary knowledge: size, strength, and computer adaptiveness. *Language
    Learning* 54(3), 399–436**, and **Aviad-Levitzky, T., Laufer, B. & Goldstein, Z. (2019). The new Computer Adaptive Test of
    Size and Strength (CATSS). *LAQ* 16(3), 345–368.** https://lexisite.com/catss/catss-info [test site OA; papers PW]
    "Strength" is a hierarchy: productive recall > receptive recall > productive recognition > receptive recognition. The
    hierarchy held at every frequency level, and **passive recall best predicted classroom performance** (2004). The CATSS was
    validated with **453 students** at three levels (2019). It uses a **conditional design**: a word answered correctly in one
    modality is **not retested** in the following ones. *Relevance:* the only operational vocabulary CAT I found that tests
    **several dimensions of the same word in sequence and skips by rule**. This is the precedent for "ask the reading only after
    the meaning" (or the reverse).

34. **Webb, S. (2005), *SSLA*; Webb (2007), *Applied Linguistics* 28, 46–65.** https://cambridge.org/core/journals/studies-in-second-language-acquisition/article/receptive-and-productive-vocabulary-learning-the-effects-of-reading-and-writing-on-word-knowledge/DDF362AE7B13D1949B1CD591DA2F3414 [PW]
    Measured several aspects (orthography, syntax, association, grammatical functions, meaning and form) on the same target
    words, receptively and productively. Different aspects emerged at different rates. Small word sets.

35. **González-Fernández, B. & Schmitt, N. (2020). Word knowledge: exploring the relationships and order of acquisition of
    vocabulary knowledge components. *Applied Linguistics* 41(4), 481–505.** https://eprints.whiterose.ac.uk/146027 [OA]
    **N = 144** Spanish L1 learners of English, tested on four components (form–meaning link, derivatives, multiple meanings,
    collocations) at recognition and recall. The components were **strongly intercorrelated**, recognition preceded recall, and
    structural equation modelling showed **recognition and recall of a component are separate constructs**. A Chinese group in the
    first author's thesis corroborated the order. *Relevance:* meaning and reading are likely **correlated but separable** traits.
    Model two correlated abilities, not one.

36. **Milton, J. & Hopkins, N. (2006). Comparing phonological and orthographic vocabulary size: do vocabulary tests
    underestimate the knowledge of some learners? *Canadian Modern Language Review* 63(1), 127–147.** https://cronfa.swansea.ac.uk/Record/cronfa29234 [?]
    Separate aural and written size tests (both Yes/No checklists) diverge for some L1 groups. A follow-up with N = 82 Arabic learners
    (Masrai 2021, secondary summary) found phonological size correlated more strongly with reading speed (r = .61) than
    orthographic size (r = .32). *Relevance:* a learner's spoken and written vocabularies can differ, so the form dimension needs
    its own measure.

### A6. Scoring two items on the same word

37. **Wainer, H., Bradlow, E.T. & Wang, X. (2007). *Testlet Response Theory and Its Applications*. Cambridge.**
    https://www.cambridge.org/core/books/testlet-response-theory-and-its-applications/fitting-testlets-with-polytomous-irt-models/CFDC00D5DC8E514490B36B9699425DBB [PW]
    Items that share a stimulus break local independence. Ignoring this **overstates precision** and biases item parameters
    (a TOEFL application says so explicitly). Remedies: (a) a testlet random effect, or (b) **score the bundle as one polytomous
    item**, after which the dependence largely disappears. A TestDaF listening study applied a mixed testlet model.
    *Relevance:* a meaning item and a reading item on the same word form a two-item testlet.

38. **Tutz, G. (1990). Sequential item response models with an ordered response. *British Journal of Mathematical and
    Statistical Psychology* 43, 39–55**, and **Hemker, B.T., van der Ark, L.A. & Sijtsma, K. (2001). On measurement properties
    of continuation ratio models. *Psychometrika* 66(4), 487–506.** https://cito.nl/media/ujon4hmb/2000-on-measurement-properties-of-continuation-ratio-models.pdf [OA]
    The **sequential (step) model**: step 2 is attempted only if step 1 succeeds, and each step is a binary IRT model conditional
    on the earlier ones (Verhelst et al. 1997 call it the "steps model"). *Relevance:* the exact model for "**ask the reading only
    if the meaning is right**". Score 0 = meaning wrong, 1 = meaning right but reading wrong, 2 = both right. Missing reading
    answers after a wrong meaning are **by design**, not missing data.

39. **Bifactor and multidimensional IRT.** Tutorial: https://derekcbriggs.github.io/Measurement-and-Psychometrics/chapters/21-mirt.html [OA].
    A bifactor model is a practical alternative to testlet models. The vocabulary evidence is mixed: one L1 study found a bifactor
    structure (https://https-sage-cnpereading-com-443.webvpn1.xju.edu.cn/doi/10.1177/1534508420966383, a proxy mirror, so verify
    before citing), while Gonzalez-Fernandez (2022, https://eprints.whiterose.ac.uk/202772/) found unidimensional behaviour in one L2
    group. *Relevance:* whether meaning and reading separate enough to justify two scales is an **empirical question for our
    data**. The answer probably differs by L1 group (see A8 and A9).

### A7. Japanese: instruments and kanji reading

40. **J-CAT (Japanese Computerized Adaptive Test).** Imai, S., Akagi, Y. & Nakasono, H. (2009). Developing character and
    vocabulary test items for the computer adaptive Japanese test. Yamaguchi University. https://petit.lib.yamaguchi-u.ac.jp/16770 [OA]
    Engine description: https://petit.lib.yamaguchi-u.ac.jp/16769/files/150671 [OA]
    Four sections, vocabulary among them, each scored 0–100 (0–400 in total). Items carry difficulty and discrimination
    parameters, and ability is re-estimated after every answer. Vocabulary items were designed from **word familiarity and
    frequency**, and **wrong options were built from learners' actual errors**. *Relevance:* an operational Japanese vocabulary
    CAT. Error-derived distractors are a model for our reading distractors.

41. **Kano, C. (Tsukuba), kanji-ability diagnostic test, part of TTBJ (Tsukuba Test-Battery of Japanese).**
    https://www.jstage.jst.go.jp/article/jslk/10/0/10_1/_pdf [OA]; https://tsukuba.repo.nii.ac.jp/record/41061/files/JJlt32-47.pdf [OA]
    Measures kanji knowledge **separately** by form recognition, **meaning**, **reading**, writing, usage and audio processing (12
    subtests in the 1990s version, shown as a profile chart). Four-option items include reading items. *Relevance:* Japanese
    pedagogy already treats **meaning and reading of kanji words as separate dimensions** and reports them as a profile.

42. **JLPT item type 漢字読み (kanji reading).** *New JLPT Guidebook* (2009). https://www.jlpt.jp/reference/pdf/guidebook1.pdf [OA]
    The JLPT vocabulary section includes **choosing the kana reading of a kanji-written word** as a standard item type.
    *Relevance:* our Japanese Readings mode is **exam-congruent**, so its results speak directly to JLPT preparation.

43. **SPOT (Simple Performance-Oriented Test).** NINJAL (2024) paper: https://repository.ninjal.ac.jp/record/2000154/files/papers2603.pdf [OA]
    SPOT measures automatic processing ("operational ability"), **not kanji or vocabulary size**. The same paper validates a
    low-stakes "Kantan Nihongo Test" with vocabulary and grammar sections on **113** participants (coefficients not seen).
    *Relevance:* SPOT is not a model for us.

44. **Rothville, K. (2024). Developing a Japanese Vocabulary Levels Test for the purposes of extensive reading. *Journal of
    Extensive Reading* 11(2).** https://jalt-publications.org/content/index.php/jer/article/view/1221 [OA]
    Built from Matsushita's General Learners' Vocabulary List and expanded from 2,000 to **5,000** words after the first version
    proved too narrow. **KR-21 = .98** with second- and third-year learners at a New Zealand university. Items per level not seen.
    *Relevance:* the closest published Japanese L2 levels test.

45. **Yamato, Y., Tamaoka, K. & Kayamoto (2016). Developing and evaluating a lexical knowledge test for Japanese learners with
    non-kanji backgrounds (Filipino learners).** KAKEN report: https://kaken.nii.ac.jp/en/report/KAKENHI-PROJECT-16K21145/16K21145seika [OA report]
    A lexical knowledge test for non-kanji-background learners, plus work on the causal links between lexical knowledge and kanji
    reading and writing. Details unverified.

46. **Matsunaga, S. (1999). Kanji knowledge transfer in reading Japanese.** Japan Foundation, *Sekai no Nihongo Kyouiku* 9.
    https://jpf.repo.nii.ac.jp/record/284/files/Sekai09_matsunaga.pdf [OA]
    Learners who could transfer L1 (Chinese) kanji knowledge **comprehended kanji-heavy texts without knowing the Japanese readings
    of the words**. *Relevance:* direct evidence that **meaning knowledge without reading knowledge** is common in Chinese-L1
    learners of Japanese, which is the case the owner wants to catch.

47. **Chinese-L1 learners' reading errors on Japanese kanji words.** Hu Xiaorui (2012), Meikai Nihongo 17:
    https://www.urayasu.meikai.ac.jp/japanese/meikainihongo/17/ko.pdf [OA]. Tokuhiro Yasuyo, JSL Kanji Gakushuu 9:
    https://www.jstage.jst.go.jp/article/jslk/9/0/9_11/_pdf/-char/ja [OA]. Cantonese speakers: https://www.japanese-edu.org.hk/jp/publish/gakkan/pdf/hkgk02304.pdf [OA].
    Typical errors: **vowel length, voicing, geminate っ and moraic ん** (for example writing 潔 as せっけつ, an added geminate). Reading a long vowel as ん
    is common across kanji-background learners. *Relevance:* the reading distractors that discriminate best for these learners
    are **special-mora and voicing variants**, which an edit-distance-one picker already tends to produce (INFERENCE).

48. **Zhao (2025). Overreliance on orthographic similarity in L2-Japanese conceptual processing by L1-Chinese learners. *IJAL*.**
    https://onlinelibrary.wiley.com/doi/10.1111/ijal.70016 [PW]. Also, on phonological processing of kanji words by L1-Chinese
    learners: *Applied Psycholinguistics*, https://www.cambridge.org/core/journals/applied-psycholinguistics/article/phonological-processing-of-japanese-kanji-word-by-l1chinese-learners-of-japanese-verification-of-consistency-and-frequency-effects/3D8611EC3445D7034F54C77A2392AECE [PW]
    L1-Chinese learners lean on kanji form for lexical access: kana-only words were notably slower. Reading errors come from
    sub-character phonological cues, **"not due to any lack of word semantic knowledge"**.

### A8. Chinese: instruments, pinyin and tones

49. **Zhang, D., Lin, C.-H., Zhang, Y. & Choi, Y. (2017/2019). Pinyin or no pinyin: does access to word pronunciation matter in
    the assessment of Chinese learners' vocabulary knowledge? *The Language Learning Journal* 47(3), 344–353.**
    https://ore.exeter.ac.uk/repository/handle/10871/28116 [OA record]
    Heritage and foreign-language learners at US universities answered character-only items, then the same items with pinyin.
    **Adding pinyin substantially raised reliability for both groups. Without pinyin the groups did not differ; with pinyin,
    heritage learners scored significantly higher**, and they revised more answers. *Relevance:* **whether the reading is shown
    changes what a meaning item measures.** Showing pinyin lets learners recognise a word by sound, so it measures spoken
    vocabulary as well. Showing characters only measures written-form → meaning. In a paired design, a meaning item shown with
    its reading also leaks the answer to the reading item.

50. **Pelzl, E., Lau, E.F., Guo, T. & DeKeyser, R. (2019). Advanced second language learners' perception of lexical tone
    contrasts. *SSLA*,** and **(2021). Even in the best-case scenario L2 learners have persistent difficulty perceiving and
    utilizing tones in Mandarin. *SSLA*.**
    https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/even-in-the-bestcase-scenario-l2-learners-have-persistent-difficulty-perceiving-and-utilizing-tones-in-mandarin/8316AA7FA2886AB59FC191CAD941602F [PW]
    Advanced learners identified the tones of isolated syllables accurately but **largely failed to reject disyllabic words that
    differed only in tone**. This held even for words whose tones they had identified correctly and confidently on an offline
    written vocabulary test. A 2021 *Frontiers in Communication* follow-up (https://www.frontiersin.org/articles/10.3389/fcomm.2021.689423/text)
    found tone-mismatched targets rejected less accurately than vowel-mismatched ones. *Relevance:* tone knowledge **lags
    segmental knowledge even in strong learners**. Our reading items keep tone-only distractors (`calibration.tech.md:390-392`),
    so they are systematically harder and partly test **written tone knowledge**, a sub-skill. Model tone-only items with their own
    difficulty offset, or report "segments right, tone wrong" separately (INFERENCE).

51. **Japanese learners' Mandarin tone difficulty.** Review: https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2024.1403816/pdf [OA].
    Production: https://www.isca-archive.org/speechprosody_2024/wu24b_speechprosody.pdf [OA]
    Difficulty order for Japanese learners: **Tone 3 > Tone 2 > Tone 1 = Tone 4**, with frequent **T2/T3 confusion**.
    *Relevance:* for Japanese-L1 Chinese learners, reading items with T2/T3-only distractors will be hardest. That is the
    knowledge gap the owner wants to expose.

52. **Li, Q. (2026, in press/online). Phonological vocabulary size: validating measurement and tracking development among
    Chinese L2 learners. *IJAL*, doi 10.1111/ijal.70225.** https://onlinelibrary.wiley.com/doi/10.1111/ijal.70225 [PW]
    A Chinese Phonological Vocabulary Levels Test (CPVLT), **N = 72** post-secondary learners. Rasch analysis showed adequate
    difficulty spread and good item fit. Tracked over time, it showed **gains and attrition** (decline, progress and off-and-on
    patterns). Whether it tests tones is not in the abstract. *Relevance:* the only validated Chinese **phonological** size test
    I found. Attrition argues for **re-placement** rather than treating a placement result as permanent.

53. **Qi (2025/2026). The development and validation of the Chinese Vocabulary Levels Test (CVLT). *IJAL*, doi 10.1111/ijal.70190.**
    https://onlinelibrary.wiley.com/doi/10.1111/ijal.70190 [PW]
    For intermediate learners, built on **levels 4–6 of the Chinese Proficiency Grading Standards** (the HSK 3.0 framework).
    Stronger learners scored higher. *Relevance:* a published precedent for **levels tests keyed to the HSK 3.0 standard**.

54. **The Chinese Vocabulary Proficiency Test (CVPT).** https://www.researchgate.net/publication/377319010 [?]
    A 100-item test analysed with IRT, **N = 170 (Indonesia) and 354 (Thailand)**.

55. **Zhou, W., Hu, R., Sun, F. & Huang, R. (2019). An intelligent testing strategy for vocabulary assessment of Chinese second
    language learners. *BEA Workshop @ ACL*, 21–29.** https://aclanthology.org/W19-4403/ [OA]
    Automatically generated items of three types (using learner writing-error data) were calibrated into a balanced pool and run as
    a **3PL CAT**. The authors report that this cut test cost significantly. Pool size and reliability not seen. *Relevance:* a
    Chinese L2 vocabulary CAT with machine-made items, the closest technical precedent for us.

56. **TOCFL-CAT (Taiwan): Chen, P.-H. & Hsu, C.-L. (2019), IACAT conference.** https://repository.eduhk.hk/en/publications/the-development-and-efficiency-of-the-computerized-adaptive-testi/ [abstract];
    TUFS slides: https://mdle.tufs.ac.jp/resource/pdf/IWALS3_presentations/japan20150729.pdf [OA]
    A Rasch-based CAT covering listening and reading (not vocabulary alone). A simulation found **more than 30% fewer items for the
    same precision** as the fixed test. The motivation: candidates could not choose the right band in advance. *Relevance:* that
    is the placement problem itself. The size of the gain (30%) is a realistic expectation for adaptivity.

57. **Beijing Language and Culture University master's thesis (2012). Measuring vocabulary size in Chinese as a second
    language.** https://cdmd.cnki.com.cn/Article/CDMD-10032-1017831328.htm [CNKI, PW]
    A definition-format test built from frequency lists and the HSK syllabus, given to **60** intermediate and advanced learners.
    Reported high reliability, **lower accuracy on lower-frequency words**, and size correlated with HSK level. Also: a Hanzi
    recognition-size test (100 characters sampled from 3,000) for CSL learners, https://www.researchgate.net/publication/348563235 [?]

58. **EdUHK (2025). A school-based computerized multistage test (MST) for Chinese vocabulary. *IJCLE* 17.**
    https://ijcle.eduhk.hk/article/345 [OA]
    One institution's multistage test. The authors report accurate levels with fewer items and less time (no metrics seen). A
    **multistage** test (blocks of items, branching between blocks) is a simpler alternative to item-level CAT.

### A9. Cross-language effects: ja↔zh shared characters and katakana loanwords

59. **Matsushita, T., Chen, M., Wang, X. & Chen, L. (2020). Developing a database of Japanese kanji vocabulary in contrast to
    Chinese (JKVC). *Journal of Japanese Language Teaching* 177, 62–76.** https://www.nkg.or.jp/gakkaishi/.assets/177_5abstract.pdf [OA abstract]
    Of the 20,000 most frequent Japanese words, **about half are Sino-Japanese**. Of those, **about 70% are written identically
    to a Chinese cognate**; the other 30% have no same-form counterpart or differ in meaning. Six meaning-correspondence types
    (after the Agency for Cultural Affairs 1978 list and Miura 1984). About 1 in 5–6 isographic words differ partly or wholly in
    meaning. Download availability unknown. *Relevance:* (a) for ja↔zh learners a large share of the meaning items is answerable
    from L1 alone; (b) a ready **cognate classification** exists to use as an item feature; (c) same-form, different-meaning words
    are diagnostic traps.

60. **Other ja↔zh resources.** Yu's database of two-kanji compounds across Chinese, Japanese, Korean and Vietnamese, with
    phonological distance (generalised Levenshtein); a Nagoya University database of about 2,060 orthographically similar two-kanji
    compounds (https://nagoya.repo.nii.ac.jp/records/28787); ANLP 2022: 173 cognates vs 173 interlingual homographs
    (https://www.anlp.jp/proceedings/annual_meeting/2022/pdf_dir/A8-1.pdf). Availability unverified.

61. **Machida, S. (2001). Japanese text comprehension by Chinese and non-Chinese background learners. *System* 29.** [PW] (via
    https://www.researchgate.net/publication/221953887). Chinese-background knowledge helped with **same-meaning cognates but not
    with same-form different-meaning words or Japan-coined kanji words**, and **non-Chinese-background learners were better at
    pronouncing kanji**. The bibliographic details could not be confirmed this session. *Relevance:* meaning transfers through
    characters and readings do not. This is the asymmetry the paired meaning-and-reading test is meant to expose.

62. **Chinese learning by Japanese L1 speakers: same-form, near-meaning words.** Aichi University paper:
    https://aichiu.repo.nii.ac.jp/record/10493/files/9_04_%E7%94%B0%E7%A6%BE_C.pdf [OA]; Zhengzhou University and other papers
    cited in the same search. Most errors are on **same-form near-synonyms** (for example 享受/享乐, 出售/出卖) whose use and
    connotation differ, not on exact cognates. Errors stay hidden at higher levels. *Relevance:* for ja-L1 learners, semantically
    close distractors on cognate words do the discriminating work.

63. **Daulton, F.E. (2008). *Japan's Built-in Lexicon of English-based Loanwords*. Multilingual Matters.**
    https://www.degruyterbrill.com/document/doi/10.21832/9781847690319/html [PW] and **Rogers, J., Webb, S. & Nakata, T. (2015).
    Do the cognacy characteristics of loanwords make them more easily learned than noncognates? *Language Teaching Research*
    19(1), 9–27.** https://ir.lib.uwo.ca/edupub/90 [OA record]
    Japanese learners of English recalled more loanword cognates than noncognates on form recall (the reverse direction of our
    case). Learners of Japanese struggle to map katakana to English sources because transliteration is ambiguous, and there are
    false friends (for example マンション, "apartment"): https://academicworks.cuny.edu/cgi/viewcontent.cgi?article=5964&context=gc_etds,
    https://www.cla.purdue.edu/academic/slc/l/japanese/documents/catj30/suemasa-sakaue-nakayama-morita.pdf [OA]. *Relevance:*
    for English-L1 learners of Japanese, katakana loanwords are probably easier as **meaning** items once katakana is decoded
    (INFERENCE, direction-reversed evidence). A kana-only word has **no separate reading to test**.

64. **Cognates in frequency-based size tests.** Jordan (2012), "Cognates in vocabulary size testing: a distorting influence?"
    https://research-portal.st-andrews.ac.uk/en/publications/cognates-in-vocabulary-size-testing-a-distorting-influence/ [?].
    A 2018 *Applied Linguistics Review* study of Spanish-L1 learners on a Yes/No test (https://www.degruyterbrill.com/document/doi/10.1515/applirev-2018-0109/html):
    item facility was explained mostly by frequency, **then cognateness**, and **frequency predicted facility better for
    non-cognates than for cognates**. *Relevance:* with the Elgort paper (A2-18), this supports a **frequency × cognate
    interaction** in the difficulty prior.

### A10. Reporting uncertainty from short tests

65. **van der Bles, A.M., van der Linden, S., Freeman, A.L.J. & Spiegelhalter, D.J. (2020). The effects of communicating
    uncertainty on public trust in facts and numbers. *PNAS* 117(14).** https://core.ac.uk/download/305110478.pdf [OA]
    UK survey experiments plus a BBC field test. A **numeric range** lowered trust in the number only slightly and **did not lower
    trust in the source**. A **verbal** uncertainty statement lowered both more. The source presenting an estimate with its range
    was trusted most. *Relevance:* show "about 1,800–2,400 words" rather than "results may vary".

66. **Kay, M., Kola, T., Hullman, J. & Munson, S. (2016). When(ish) is my bus? User-centered visualizations of uncertainty in
    everyday, mobile predictive systems. *CHI 2016*.** https://vis.mit.edu/classes/6.859/readings/pdfs/Kay-WhenishIsMyBus.pdf [OA]
    **Quantile dotplots** (a distribution drawn as about 20 countable dots) gave about 1.15× lower variance in users' probability
    estimates than density plots on **mobile**, and users were more confident. *Relevance:* a phone-sized way to show a range.

67. **Zwick, R., Zapata-Rivera, D. & Hegarty, M. (2014). Comparing graphical and verbal representations of measurement error
    in test score reports. *Educational Assessment* 19(2), 116–138.** https://ets.org/research/policy_research_reports/publications/article/2014/jsiq.html [PW]
    Four randomly assigned report designs. **Misconceptions about measurement error were widespread.** Which design won was not
    seen in the abstract. With **Zenisky & Hambleton** score-reporting guidelines (summarised in the Ofqual report,
    https://assets.publishing.service.gov.uk/media/5a81b98ce5274a2e87dbf2cf/2010-03-18-on-the-reporting-of-measurement-uncertainty-and-reliability.pdf [OA]):
    show **score bands**, explain that overlapping bands mean similar performance, and avoid over-reading small differences.

### A11. Excluded by owner decision (listed for completeness only)

Pseudoword and Yes/No tests: LexTALE-type tests for Chinese (LEXTALE_CH, Chan & Chang 2018; **LexCHI**, Wen et al. 2024, *BRM*
56(3), 60 two-character items, https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10991040/; LexCH, *Applied Linguistics Review* 2022)
and Japanese (**LexJP**, 2025, https://www.sciencedirect.com/science/article/pii/S2772766125000291), the Duolingo Yes/No items, and
Meara-style checklists. **Not used** (owner decision 2). One relevant number: McLean et al. (2020, A1-7) found Yes/No a weaker
predictor of reading than meaning recall, which independently supports the decision.

---

## Part B: Findings that should shape the design

Each finding gives a claim, its label, its citation, and what it implies for us.

### B1. What the result can honestly claim

1. **A four-option meaning test measures recognition, and recognition overestimates usable knowledge.** MEASURED in other
   populations: MC > interview (A1-6, Gyllstad 2015); VLT raw-score inflation ≈ 16–17/99 from guessing (A2-16, Stewart & White
   2011); recall formats predict reading better (A1-7, N = 103). → Call the result "words you **recognise**", consistent with the
   Knowledge Report ("known must mean recognition", TASK-1073 notes). Never present it as productive or recall vocabulary.
   (INFERENCE)

2. **"Knowing a word" is multi-dimensional, and in logographic scripts meaning and reading separate.** MEASURED: L1-Chinese
   learners of Japanese comprehend kanji text without knowing the readings (A7-46, Matsunaga 1999), and non-Chinese-background
   learners pronounce kanji better (A9-61, Machida 2001). Recognition and recall of a component are separate constructs, though
   strongly correlated (A5-35, N = 144). Kanji tests in Japan report meaning and reading as separate subtests (A7-41). → For ja
   and zh, report **meaning-known** and **meaning-and-reading-known** separately. The owner's two dimensions match established
   practice. (INFERENCE)

3. **Per-exam-level counts cannot be measured directly in a few minutes. They must be model-based.** MEASURED: individual band
   estimates need **≥30 items per band** for usable confidence intervals (A1-5, Gyllstad, McLean & Stewart 2021), whereas whole-test
   reliability is fine with ~5 per band (A1-2, Beglar 2010). → Estimate one or two abilities from all answers, then **predict**
   P(known) for every word in each HSK or JLPT list and sum, propagating the ability's uncertainty. Label per-level numbers as
   model estimates with ranges. (INFERENCE)

4. **Show the uncertainty as a numeric range, not a verbal hedge.** MEASURED: numeric ranges barely affect trust, while verbal
   hedges reduce it (A10-65, PNAS 2020). Quantile dotplots work on mobile (A10-66). Lay readers misread measurement error (A10-67).
   → "About 1,900 words (likely 1,600–2,300)". A dot strip or band per exam level. No pass/fail. Wording that says "estimate".
   The calibration UI already renders `4.31 ± 0.24` style ranges (`calibration.tech.md:364-367`). (INFERENCE)

### B2. Scoring model

5. **Guessing must be modelled with a fixed lower asymptote, never estimated per item at our sample sizes.** MEASURED/cited: the
   c parameter needs thousands of examinees (A3-25 secondary); a 3PL with c fixed at 1/k performs well (A3-25, Han 2012); Rasch fit
   does not detect guessing (A2-17). The codebase already fixes the floor at 0.25 for the person curve (`calibration.tech.md:331`),
   but `services/irt/calibrator.py:1-17` has none. → Item model: P(correct) = K + (1 − K)·g, with K = σ(a(θ − b)) and g fixed by the
   IDK rule in finding 6. (INFERENCE)

6. **"I don't know" can be handled exactly, and the guessing floor depends on how much each person skips.** Derivation
   (INFERENCE, from the know-or-guess model that ADR-051 already assumes): let K = P(knows), s = the person's probability of
   pressing IDK when they don't know, and random guessing among 4 options otherwise. Then
   P(correct) = K + (1 − K)(1 − s)/4, P(wrong) = (1 − K)(1 − s)·3/4, P(IDK) = (1 − K)·s.
   (a) **A wrong answer and an IDK carry the same information about θ** (both are proportional to 1 − K). s only scales them.
   (b) The effective guessing floor is **(1 − s)/4**, so it is **person-specific**: about 0.25 for someone who never skips, near 0
   for someone who always skips honestly. (c) The ADR-051 estimator c/n − (1/3)·w/n has expectation exactly K **whatever s is**
   (check: K + (1 − K)(1 − s)/4 − (1/3)(1 − K)(1 − s)(3/4) = K), so the Knowledge Report's band estimator is already IDK-robust.
   The literature motivates (b): IDK use **differs between learners** and degrades validity when ignored (A2-14, A2-15:
   r = .77 vs .88–.91, N = 200). IDK cuts guessing but under-credits partial knowledge (A2-13, N = 150). → Estimate s per person
   (it is identified from the IDK rate), and **do not score IDK as a wrong guess under a fixed 0.25 floor**. Today the API records a
   skip as incorrect (`calibration.tech.md:274`), which is the "naive" skip model ADR-051 lists among rejected alternatives (`ADR-051-vocabulary-size-from-calibration-frame.md:81-82`). (Formula: INFERENCE. The premises
   about IDK behaviour: MEASURED in A2.)

7. **Guesses are often informed, not random. Semantically close distractors reduce that, at a cost in difficulty.** MEASURED:
   "guesses were more likely informed than uninformed" (A2-15). Distractors related in meaning or spelling make items **harder and
   more discriminating** (Ludewig, Schwerter & McElvany 2023, https://eldorado.tu-dortmund.de/items/2f2f24a7-464f-48d5-908b-d9e7ea2a97a9;
   German fourth graders). → With ADR-025 distractors, partial knowledge is less likely to be credited, so the 1/4 floor is roughly
   right but items are harder than Zipf alone predicts. Include **distractor similarity as a difficulty feature** (finding 11).
   (INFERENCE)

8. **Use a Bayesian (EAP or MAP) ability estimate with a prior. Never use maximum likelihood or clipping.** MEASURED/cited: ML
   diverges on all-correct or all-wrong patterns, which are common early in a CAT and for beginners and advanced learners; EAP stays
   finite and is more stable early (A3-22). → Replace the 5–95% clipping pattern (`calibrator.py:9-11`) in anything placement-related.
   The prior can come from the learner's stated level or exam goal (a cold-start benefit), but its weight must be visible in the
   reported range. (INFERENCE)

### B3. Adaptive selection and stopping

9. **A guessing floor costs about 40% of each item's information, and the best item is one the learner probably knows.**
   ESTIMATE, computed exactly from the 3PL information function (script `placement/info_calc.py`, logit scale, no D constant):

   | slope a | floor c | max info per item | P(correct) at max | items for SE 0.5 / 0.4 / 0.3 (perfect targeting) |
   |---|---|---|---|---|
   | 1.0 | 0 | 0.250 | 0.50 | 16 / 25 / 45 |
   | 1.0 | 0.25 | 0.155 | 0.68 | 26 / 41 / 72 |
   | 1.5 | 0 | 0.563 | 0.50 | 8 / 12 / 20 |
   | 1.5 | 0.25 | 0.348 | 0.68 | 12 / 18 / 32 |
   | 2.0 | 0.25 | 0.619 | 0.68 | 7 / 11 / 18 |

   With c = 0.25, **an item 1 logit too hard keeps 57% of peak information (a = 1), while one 1 logit too easy keeps 87%**. For
   a = 1.5 the figures are 34% and 69%. → Target items where the predicted P(correct) is **about 0.65–0.70, not 0.5**, and when
   unsure **err easy**. This is both more informative and less discouraging. A learner who honestly uses IDK lowers their own floor
   (finding 6) and gains information per item. Linacre and Halkitis reach the same advice of targeting slightly easy items
   (A3-19). (ESTIMATE, plus cited)

10. **Stopping rule: an SE threshold plus minimum and maximum item counts, plus a predicted-SE-reduction rule for learners at the
    edges.** Cited: the SE rule is the most studied; typical thresholds 0.30–0.35 logits (A3-20, BRM 2018). PSER stops when more
    items would not help, which suits poorly targeted examinees (A3-21). Adaptive saves about 30% of items against a fixed test for
    the same precision (A8-56, TOCFL-CAT simulation). → Combined with finding 9 and the measured non-adaptive precision of the
    current check (person-curve sd 0.42 Zipf at 40 items, 0.27 at 60, `calibration.tech.md:354-360`), a **25–40-item** adaptive
    test for one dimension is plausible. The actual Zipf-scale SE must be **simulated on our data** (other stages). (INFERENCE)

11. **Cold-start item difficulty: a feature-based prior, then online updates. Frequency alone is weak.** MEASURED: frequency
    explains about **25%** of item-difficulty variance (r = 0.50, N = 403), and only ~9% when grouped into 1,000-word bands
    (A1-9). Duolingo calibrates from features with 500 examinees and about 6 exposures per item (A4-26, A4-27). Hierarchical priors
    stabilise calibration at N ≈ 50 under some conditions (A4-29). Elo is cheap and beats proportion correct at small n (A4-28).
    → Prior b = f(Zipf, exam level, part of speech, script, L1-cognate status, distractor similarity, mode) with a **wide residual
    SD**. Update per item with Elo-style or hierarchical shrinkage, which generalises `apply_prior()` (`calibrator.py:113-115`).
    Store only per-item (b, n) per mode and L1 group: a few thousand rows per language, small for the database cap. (INFERENCE)

12. **Exposure control is for data quality and retakes, not security.** Cited: randomesque selection (choose among the top 5)
    is simple and keeps exposure low (A3-23). → Use randomesque selection so retakes see different words (TASK-1073 requires
    disjoint retake items) and calibration data spread over the pool rather than piling onto a few "most informative" words.
    (INFERENCE)

### B4. Testing meaning and reading on the same word (zh, ja)

13. **Two items on one word are a testlet. Treating them as independent overstates precision.** MEASURED in testlet studies
    (A6-37). → Do not add meaning and reading answers as independent evidence for one θ. (INFERENCE)

14. **Recommended structure: a conditional, sequential pair, meaning first and then reading only when the meaning is right.**
    Supported by: the CATSS skip rule (A5-33, N = 453) as an operational precedent; the Tutz sequential (steps) model (A6-38) as an
    exactly matching IRT model; and the owner's target case (A7-46, A9-61: meaning known via characters, reading not), which this
    order detects directly. Score each word 0 (meaning not known), 1 (meaning known, reading not), 2 (both). Benefits (INFERENCE):
    (a) it saves time, because reading items for words whose meaning is unknown add little; (b) it treats the pair as one polytomous
    item, which removes the local-dependence problem (A6-37); (c) the chance of guessing a full "2" is 1/16, not 1/4, so a "2" is
    strong evidence. Cost: the readings of words whose meaning is missed are never seen. Heritage learners, who may know a word's
    sound but not its characters (A8-49), would be under-measured on reading. → Optionally ask a few unconditional reading items
    for calibration, or reverse the order for learners who report a heritage background. (INFERENCE)

15. **Do not show the reading in the meaning item, and do not give right/wrong feedback between the two items of a pair.**
    MEASURED: showing pinyin changes what is measured and who scores higher (A8-49, heritage learners gain). → Meaning items show
    characters only. The reading item follows without revealing the meaning item's answer, and the meaning item never shows the
    reading's answer. (INFERENCE)

16. **Model two correlated abilities (meaning, reading), with the correlation depending on L1.** Cited: components are separable
    but correlated (A5-35). For Chinese-L1 learners of Japanese, meaning transfers and reading does not (A7-46, A9-61), so the
    correlation is presumably lower for ja↔zh learners than for English-L1 learners (INFERENCE). → A two-dimensional model (or the
    sequential model's two step parameters per word) with an L1-group-specific correlation lets reading answers inform the meaning
    estimate when the dimensions agree. Whether two dimensions are needed should be **tested on our data** (A6-39 is mixed).
    The existing pooling already keeps the modes separate (`calibration.tech.md:453`). (INFERENCE)

17. **Tone deserves its own handling in Chinese reading items.** MEASURED: advanced learners fail to reject tone-only mismatches
    even for words whose tones they identified correctly on a written test (A8-50). Japanese learners confuse T2 and T3 most
    (A8-51). → Tag each reading distractor as **tone-only** or **segmental**, and give tone-only items their own difficulty term.
    Report "pinyin known, tones not yet" as a partial state rather than a plain miss. This sharpens the "do they really know it"
    signal the owner asked for. (INFERENCE)

18. **Japanese reading distractors should target special morae and voicing.** MEASURED (error studies, small samples):
    Chinese-L1 errors centre on vowel length, っ, ん and voicing (A7-47). J-CAT builds its distractors from real learner errors
    (A7-40). JLPT uses exactly this item type (A7-42). → Prefer edit-one distractors that change a long vowel, a geminate, a moraic
    nasal or voicing over arbitrary one-letter changes. Exclude kana-only words from reading items, since their spelling is their
    reading. (INFERENCE)

### B5. Cross-language effects

19. **Difficulty needs an L1 × cognate term that interacts with frequency.** MEASURED: cognate items are easier, the L1 benefit is
    larger at low proficiency, and the cognate advantage shrinks with frequency (A2-18, N = 121). Frequency predicts facility less
    well for cognates (A9-64). JKVC: about half of frequent Japanese words are Sino-Japanese, about 70% of those are isographic with
    Chinese (A9-59). → For ja-L1 learners of zh and zh-L1 learners of ja, flag isographic cognates (computable by comparing our zh
    and ja lemmas after simplified/traditional/shinjitai normalisation, which the data stage should verify). Give them a separate
    difficulty offset in **meaning** mode only. Same-form, different-meaning words (A9-59, A9-62) are the most diagnostic meaning
    items for these learners. (INFERENCE)

20. **For ja↔zh learners the meaning-only range will be inflated by L1 knowledge. The paired score is the honest headline.**
    MEASURED premises A7-46 and A9-61. → For these learners the report should lead with "meaning and reading known" and present
    meaning-only as "recognisable through characters". This is the "do they actually know the word" distinction the owner asked for.
    (INFERENCE)

21. **Katakana loanwords: probably easier meaning items for English-L1 learners, and not reading items at all.** Direction-reversed
    and qualitative evidence (A9-63). → Use script (kana-only, kanji, mixed) and loanword status as difficulty features. Exclude
    kana-only words from reading items. (INFERENCE)

### B6. Validation with little data

22. **Validate against later behaviour, not only internal fit.** Cited: Rasch fit is not enough (A1-1 critique; A2-17). Recall
    predicts reading better than recognition (A1-7). → Check predictions against (a) later first-try accuracy on practice items for
    the same words; (b) retest agreement on disjoint items (randomesque selection makes this possible); (c) self-reported exam level
    (the CVLT and BLCU studies used proficiency-group ordering, A8-53, A8-57). Report calibration (predicted vs observed accuracy by
    decile), not just correlation. (INFERENCE)

23. **Plan for attrition and re-placement.** MEASURED: phonological vocabulary size declined over time for some learners (A8-52,
    N = 72). → A placement result should decay to "estimate from N weeks ago" and invite a short re-check. It should not freeze
    into known words (TASK-1065 evidence kinds). (INFERENCE)

---

## Part C: Gaps, unverified items, open questions

- **No full texts were read** (WebFetch was blocked on every publisher host tried). All figures are from abstracts or secondary
  summaries. Before the ADR cites a number, someone should confirm these against full texts: Beglar (2010), the Webb et al.
  (2017) format and cut-offs, Babcock & Weiss (2012) thresholds, the Mizumoto, Sasao & Webb (2019) CAT-WPLT stopping rule
  (*Language Testing* 36(1), 101–123; open copy at https://kansai-u.repo.nii.ac.jp/records/748), and the Tseng (2016) results
  (*Computers & Education* 97, 69–85).
- **Not found:** a published adaptive vocabulary test for **Japanese** that tests reading and meaning as separate adaptive
  dimensions; a DIF study of HSK vocabulary by Japanese or Korean (character-background) examinees; any study quantifying how
  much an IDK option changes CAT precision.
- **Open questions for the design and data stages:**
  1. Is the meaning–reading correlation in our own data (the owner's calibration answers in `real_events.json`) high enough that
     one ability would do for English-L1 learners? It should be measured, not assumed.
  2. What is the item slope on the Zipf scale? It sets how many items finding 9 actually needs and has to be fitted from our data.
  3. Can isographic ja↔zh cognates be flagged reliably from our dictionaries alone, or is JKVC needed (and licensable)?
  4. Meaning-first conditional order versus unconditional pairs: simulate both for a ja-L1 learner of zh and an English-L1
     learner.
  5. Per-person skip propensity s (finding 6): how much does it vary in real data, and does it depend on ability?
