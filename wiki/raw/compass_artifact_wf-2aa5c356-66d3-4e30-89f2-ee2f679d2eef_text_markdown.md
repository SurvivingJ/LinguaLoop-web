# Designing a Dual-Translation (Back-Translation) Feature: Learning-Science and UX Report

## TL;DR
- **Build the feature as a "pushed-output + noticing" engine, not a translation test.** The core learning value of dual translation is that reproducing the L2 forces the learner to notice the gap between what they can produce and the target form (Swain's Output Hypothesis; Schmidt's Noticing Hypothesis), and the comparison step is where learning happens — so the rubric and error log must be engineered to make that gap *visible and actionable*, grounded in Sadler's "close the gap" model of formative assessment.
- **Feature 1 (Rubric):** Use an *analytic* rubric mapped onto validated constructs — Complexity/Accuracy/Fluency (Skehan; Housen, Kuiken & Vedder) and CEFR qualitative dimensions — and explicitly separate "understandability/intelligibility" from "nativeness," because Munro & Derwing show these are partially independent constructs (speech can be "heavily accented but highly intelligible") and over-weighting nativeness demotivates without improving communication.
- **Feature 2 (Error synthesis + remediation):** Aggregate errors using a Corder/James error taxonomy (interlingual vs. intralingual; global vs. local; error vs. mistake), then remediate with spaced retrieval practice (Cepeda et al.; Roediger & Karpicke), interleaving (Rohrer & Taylor), and well-formed cards (SuperMemo "minimum information principle") — always drilling the *corrected* form, never the error.

## Key Findings

1. **Translation is rehabilitated as a legitimate learning tool, but the literature does not call it "back-translation."** Guy Cook's *Translation in Language Teaching* (2010, OUP) argues for the reassessment of "Translation in Language Teaching" (TILT), distinguishing it from the discredited Grammar-Translation Method. Alan Duff's *Translation* (1989, OUP Resource Books for Teachers) is the classic practitioner resource. The single strongest empirical support is Laufer & Girsai (2008, *Applied Linguistics* 29(4):694–716), whose contrastive-analysis-and-translation (CAT) group — assigned bidirectional L2→L1 and L1→L2 translation tasks — "significantly outperformed the other two groups on all the tests," a result the authors explicitly discuss "in light of the 'noticing' hypothesis, 'pushed output', 'task-induced involvement load', and the influence that L1 exerts on the acquisition of L2 vocabulary." Caution: in academic and industry usage "back-translation" denotes professional translation QA or machine-translation data augmentation; anchor claims in "translation as practice / pushed output" and "languaging," not in a "back-translation" literature that does not exist pedagogically.

2. **The pedagogical mechanism is a chain: pushed output → noticing the gap → languaging → proceduralization.** Swain's Output Hypothesis identifies noticing/triggering, hypothesis-testing, and metalinguistic functions of output; Schmidt's Noticing Hypothesis holds that learners must consciously "notice the gap" between their interlanguage and the target for input to become intake; Swain's "languaging" (2006) is the meaning-making reflection that the comparison step enables; DeKeyser's Skill Acquisition Theory explains why repeating corrected forms drives the declarative→procedural→automatized progression.

3. **The desired rubric dimensions map cleanly onto validated constructs, with one critical caveat.** "Grammatical correctness" = accuracy; "articulateness/range" = complexity; "fluency (how native it sounds)" splits into the CAF "fluency" construct AND a nativeness/accentedness dimension; "understandability" = intelligibility/comprehensibility. Munro & Derwing's foundational finding — speech can be "heavily accented but highly intelligible" — means nativeness and understandability must be scored separately and nativeness must be de-emphasized to avoid demotivation.

4. **Analytic rubrics beat holistic for this use case.** Research on L2 writing assessment consistently finds analytic rubrics give more reliable, more diagnostic, more actionable feedback — exactly what feeds an error log — while holistic scores are better only for a single quick "overall" judgment.

5. **Spaced retrieval, interleaving, and desirable difficulties are the remediation backbone.** Cepeda et al. (2006, *Psychological Bulletin* 132(3):354–380) reviewed "839 assessments of distributed practice in 317 experiments located in 184 articles," confirming distributed practice and finding that the inter-study interval producing maximal retention increases as the retention interval lengthens; Roediger & Karpicke (2006) demonstrated the testing effect (on a one-week delayed test, retrieval-practice students recalled ~61% versus ~40% for repeated restudy); Rohrer & Taylor (2007, *Instructional Science* 35:481–498) found that "interleaving reduced practice scores yet tripled test scores (d = 1.34)" one week later; Bjork's "desirable difficulties" explains why effortful reproduction aids retention. FSRS now empirically outperforms the classic SM-2 scheduler.

## Details

### A. Theoretical Foundations for Dual Translation

**From Grammar-Translation to TILT.** Translation was "outlawed" from language teaching beginning at the end of the 19th century as the Reform Movement and Direct Method rejected the Grammar-Translation Method's heavy L1 presence. Guy Cook (2010) argues this baby-with-bathwater rejection was an error, and presents translation as "an aid to language acquisition, pedagogy, and testing" and "a contribution to student needs, rights, and empowerment." Juliane House's review (2012, *Applied Linguistics*) endorses the argument. The design implication: dual translation is defensible *because* it is contrastive and bilingual, not in spite of it — but it must be communicative and meaning-focused (TILT), not mechanical decoding (Grammar-Translation).

**Comprehensible Input is necessary but not sufficient (Krashen → Swain).** Krashen's Input Hypothesis (1982, 1985) holds that language is acquired by receiving comprehensible input slightly beyond the current level — "i+1," where "i" is the current level of competence and "+1" the next step along the natural order. The standard critique — and the entire rationale for an output-based feature — is that input alone is insufficient: Swain's observations of Canadian French immersion students (high comprehension, persistent production inaccuracies) led to the Output Hypothesis. Dual translation is a pure pushed-output task: it forces production, which is exactly the gap Krashen's model leaves open. (Krashen's "i+1" has also been criticized as imprecise and hard to test — Gass and others note the construct is underspecified.)

**Output Hypothesis (Swain).** Producing the L2 reproduction triggers three functions Swain identified (1985; Swain & Lapkin 1995, *Applied Linguistics* 16(3):371–391): (1) **noticing/triggering** — learners notice gaps between intended meaning and what they can produce; (2) **hypothesis-testing** — the reproduction is a "trial run" tested against the original; (3) **metalinguistic/reflective** — comparing reveals *why* a form was wrong. The reveal-and-compare step in dual translation is the literal embodiment of all three.

**Noticing Hypothesis (Schmidt).** Schmidt (1990) and Schmidt & Frota (1986) argue learners must consciously "notice the gap" between their output and the target form for intake to occur; Schmidt's weaker later formulation is "the more noticing, the more learning." This is the central reason the comparison UI matters more than the score: the product is noticing, not a grade.

**Languaging (Swain 2006).** Defined as "the process of making meaning and shaping knowledge and experience through language" (Swain 2006, in Byrnes ed., *Advanced Language Learning*); Swain argues "languaging about language is one of the ways we learn a second language to an advanced level." Operationalized via Language-Related Episodes, languaging draws on Vygotskian sociocultural theory. The rubric's per-dimension explanations and the error log are languaging scaffolds.

**Skill Acquisition Theory (DeKeyser).** L2 development moves declarative → procedural → automatized; proceduralization happens through meaningful practice resembling communicative activity. This justifies the "isolate-and-repeat" remediation: repeating the corrected translation is the practice that proceduralizes the fix. DeKeyser emphasizes meaningful over mechanical drills and skill-specificity (output practice builds production skill).

**Contrastive Analysis (Lado) and Error Analysis (Corder).** Lado's Contrastive Analysis Hypothesis (1957, *Linguistics Across Cultures*) predicted that L2 elements similar to L1 are easy and different ones are hard ("In the comparison between native and foreign language lies the key to ease or difficulty in foreign language learning"). The strong version was rejected (Wardhaugh 1970, *TESOL Quarterly*, called it "untenable"), but a moderate, diagnostic version survives — and dual translation is uniquely suited to surface exactly the interlingual/L1-transfer errors CAH was concerned with. Corder's Error Analysis (1967, 1971) reframed errors as evidence of learning, distinguishing **errors** (competence gaps) from **mistakes** (performance slips). This distinction is essential to Feature 2: only systematic errors should populate the SRS, not one-off slips.

**Cognitive Load Theory (Sweller) and Desirable Difficulties (Bjork).** The task is intrinsically demanding (two translation directions + comparison), so the UI must minimize *extraneous* load — clean diffs, one focal error at a time. But the *effort itself* is productive: Bjork's "desirable difficulties" framework holds that conditions that slow acquisition (effortful retrieval, spacing, interleaving) accelerate long-term retention. Don't make the task "easy"; make the *interface* clear.

### B. Feature 1 — The Grading Rubric

**Use analytic scoring.** Analytic rubrics (separate scores per dimension) are more reliable, more diagnostic, and more useful for feedback than holistic scoring in L2 writing assessment; research finds raters routinely underuse holistic categories, collapsing them, while analytic scales place learners along a more clearly defined ability continuum. Add one optional "overall impression" holistic line on top for motivation, but the analytic dimensions drive the error log.

**Map dimensions onto validated constructs.** Ground the rubric in the Complexity-Accuracy-Fluency (CAF) triad (Skehan 1996; Housen, Kuiken & Vedder 2012) and CEFR qualitative dimensions (range, accuracy, fluency, coherence, interaction):

| User's dimension | Validated construct | What it measures | Feedback focus |
|---|---|---|---|
| Grammatical correctness | **Accuracy** (CAF); CEFR Accuracy | Conformity to target norms; error-free production | Direct + metalinguistic correction of systematic errors |
| Articulateness | **Complexity/Range** (CAF); CEFR Range | Syntactic/lexical sophistication and variety | Suggest higher-range alternatives; never penalize correct simplicity harshly |
| Understandability | **Intelligibility/Comprehensibility** (Munro & Derwing) | Would a native actually grasp the intended meaning? | Flag global errors that impede meaning |
| Fluency (how native it sounds) | **Fluency** (CAF) + **Nativeness/idiomaticity** | Naturalness, idiomatic phrasing, collocation | Offer the idiomatic version; frame as "more natural," low stakes |
| Fidelity to source meaning | **Equivalence** (House TQA; functional/Skopos) | Did the reproduction preserve the original L2's meaning/register? | Compare against original; flag meaning drift |

**The critical nativeness/intelligibility nuance.** Munro & Derwing (1995, *Language Learning* 45(1):73–97) showed accentedness, comprehensibility, and intelligibility are "related, but partially independent," with the key observation that "speech can be heavily accented but highly intelligible." Translate to the rubric: a reproduction can be non-native-sounding but completely understandable and grammatically correct. **Weight understandability and accuracy highest; treat nativeness as aspirational, lower-stakes "polish."** Over-emphasizing nativeness risks demotivation (Derwing & Munro recommend intelligibility, not nativeness, as the realistic goal). This directly resolves the tension in the user's two listed dimensions.

**Translation Quality Assessment framing (House).** Juliane House's TQA model distinguishes overt vs. covert translation and overt vs. covert errors, comparing source and target on register and genre. For a learner feature, adapt this into a "fidelity/equivalence" dimension: did the L2 reproduction preserve the *function and register* of the original, not just word-for-word content? This is especially important for register-heavy languages (Japanese keigo).

**Scoring approach.** Use a 4-band analytic scale per dimension (e.g., 1 = impedes meaning / 4 = target-like) with concrete descriptors at each band, modeled on CEFR's "can-do" descriptor style. Avoid fine-grained point scores that imply false precision. Show a short verbal descriptor, not just a number.

**Effective feedback design (Hattie & Timperley; Bitchener & Ferris; Truscott debate).** Hattie & Timperley's "Power of Feedback" (2007) model requires three questions — *Where am I going?* (feed-up / show the original + standard), *How am I going?* (feed-back / the diff and rubric), *Where to next?* (feed-forward / the specific fix and next practice). They warn feedback at the "self" level ("you're smart") is ineffective; keep feedback at task and process levels. On corrective feedback type, the Truscott (1996) vs. Ferris (1999) debate remains unresolved, but the practical synthesis is: **direct correction** (give the right form) helps immediate uptake and low-proficiency learners; **indirect/metalinguistic** correction (flag + explain the rule) fosters autonomy and long-term self-editing. Recommendation: offer **direct correction + a metalinguistic tag** (the rule/category), and let advanced users toggle toward indirect (flag-only) mode — a desirable difficulty.

**Self-assessment and transparency (Sadler; Black & Wiliam).** Sadler (1989, *Instructional Science* 18(2):119–144) argues that "for students to be able to improve, they must develop the capacity to monitor the quality of their own work during actual production," which requires they "possess an appreciation of what high quality work is" — a concept of the standard — and that systems failing to build this evaluative expertise "set up artificial but potentially removable performance ceilings." Black & Wiliam (1998, "Inside the Black Box") found formative assessment one of the most powerful interventions for raising achievement ("We know of no other way of raising standards for which such a strong prima facie case can be made") and warn that a culture of grades/rewards makes learners chase marks rather than learning. Design implications: (1) show the rubric *before* the task so the learner internalizes the standard; (2) optionally have the learner self-rate before seeing the system's rating (a noticing/languaging prompt); (3) keep the emphasis on the diff and the fix, not the score.

### C. Feature 2 — Error Synthesis + Spaced-Repetition Remediation

**Error taxonomy for aggregation (Corder; James 1998).** Tag every flagged error along several axes so the system can synthesize patterns:
- **Category:** grammatical / lexical (vocabulary) / pragmatic-expressional (idiomaticity, register).
- **Source:** **interlingual** (L1 transfer/interference — dual translation surfaces these especially well) vs. **intralingual** (overgeneralization, incomplete rule application within the L2; James lists false analogy, misanalysis, incomplete rule application, overgeneralization, hypercorrection).
- **Severity:** **global** (impedes overall meaning — prioritize) vs. **local** (affects only a phrase/element).
- **Error vs. mistake (Corder):** only systematic, repeated deviations ("errors") should enter the SRS; self-corrected slips ("mistakes") should not. Use repetition across sessions to distinguish: if the learner gets it right when attention is drawn but wrong under production load, it's proceduralization-stage, not a knowledge gap.

**Synthesis logic.** Aggregate tagged errors over time into a personal "error profile" — e.g., "article omission (English, interlingual, local): 14 instances over 3 weeks." This profile is both a remediation queue and a **metacognitive tool** (see Section D). Surface the top recurring patterns; rank by frequency × severity (global errors first).

**Spaced repetition science.**
- **Spacing effect:** Cepeda et al. (2006) confirmed across 317 experiments that distributed practice beats massed; the optimal inter-study interval scales with the desired retention interval.
- **Testing effect / retrieval practice:** Roediger & Karpicke (2006, *Psychological Science* 17(3)) — on a one-week delayed test, retrieval-practice students recalled ~61% versus ~40% for repeated restudy, "even though repeated studying increased students' confidence." Every remediation card should require *production*, not recognition.
- **Algorithms:** Leitner (fixed boxes) → SM-2 (Wozniak 1987, ease-factor heuristic, used by Anki for ~17 years) → FSRS (machine-learning scheduler that models per-card retrievability/stability and empirically outperforms SM-2 on large public review datasets). Recommendation: use an FSRS-style scheduler; fall back to SM-2/Leitner-style intervals when there's insufficient personal review history.
- **Expanding vs. uniform spacing:** Cepeda's meta-analysis found expanding intervals modestly favorable but with high between-study variance; either works, so let the scheduler decide.

**Interleaving (Rohrer & Taylor 2007) and deliberate practice (Ericsson).** Rohrer & Taylor (2007) found interleaved practice "reduced practice scores yet tripled test scores (d = 1.34)" one week later; the large grade-7 classroom replication (Rohrer, Dedrick & Burgess 2014, *Psychonomic Bulletin & Review*) found interleaved vs. blocked test scores of "72% vs. 38%, d = 1.05" two weeks later — because interleaving forces discrimination (you must identify *which* rule applies). Mix error-remediation cards across categories within a session rather than drilling one error type to exhaustion. Deliberate practice (Ericsson) — targeted effort on specific weaknesses with feedback — is precisely what the error profile enables; this is the feature's deepest justification.

**"Isolate the problematic translation and repeat it" (Bjork; DeKeyser).** When an error recurs, extract the specific sentence/phrase and have the learner re-translate it after a delay (spaced), under retrieval conditions. This is a desirable difficulty (effortful reproduction) that proceduralizes the corrected form (DeKeyser).

**Turning errors into effective flashcards (SuperMemo "minimum information principle"; Wozniak).** Critical pitfalls and rules:
- **Never show the error as the prompt** — learners can inadvertently memorize the wrong form (interference). Always drill toward the *correct* form.
- **Minimum information principle (Wozniak):** each card should test one small, atomic fact; complex/compound cards (those violating this principle) "are repeated annoyingly often" and signal poor formulation.
- Use **cloze deletions** of the specific corrected element (e.g., delete just the particle or article) rather than whole-sentence recall, so the card isolates the target.
- Favor **productive recall** (produce the form) over receptive recognition, consistent with the testing effect and output focus.
- Provide context (the full corrected sentence) on the answer side to support transfer-appropriate processing.

**Feedback timing.** For the rubric/translation task, immediate feedback supports hypothesis-testing and noticing. For remediation cards, the spacing *between* reviews is what matters; within a card, immediate corrective feedback after the attempt is standard and effective.

### D. Habits of Proficient / "Good Language Learners"

The Good Language Learner tradition (Rubin 1975, "What the 'Good Language Learner' Can Teach Us," *TESOL Quarterly* 9(1):41–51; Naiman, Fröhlich, Stern & Todesco 1978; Stern 1975) found that successful learners: are willing, accurate guessers; have a strong drive to communicate; are uninhibited and willing to make mistakes; attend to form *and* meaning; constantly look for patterns; **practice**; and **monitor their own and others' speech**. These map directly onto the two features:
- The rubric scaffolds **attention to form** and **self-monitoring**.
- The error log scaffolds **pattern-seeking** and **metacognition**.
- The low-stakes, mistake-tolerant framing supports **risk-taking** (a GLL trait; over-penalizing nativeness suppresses it).

**Language learning strategies (Oxford 1990; O'Malley & Chamot).** Oxford's taxonomy (metacognitive, cognitive, memory, compensation, affective, social) and the metacognitive cycle (plan → monitor → evaluate) frame the error log as a **metacognitive / self-regulated-learning tool**: it lets learners plan (what to drill), monitor (track recurring errors), and evaluate (see error rates fall). Surfacing the error profile to the learner — "your article errors dropped 40% this month" — operationalizes self-regulated learning and sustains motivation without extrinsic gamification.

### E. Language-Specific Localization Notes

The rubric and error taxonomy are language-agnostic by default, but weightings and categories must localize. Note: tone/pitch-accent dimensions apply only if speech is involved; for text-based translation they are out of scope.

**English (analytic, SVO, article-heavy).** High-frequency error categories: articles (a/the — major source of interlingual errors for article-less L1s like Japanese, Chinese, Russian), prepositions, phrasal verbs, tense/aspect, subject-verb agreement. Because English is analytic, word-order and function-word errors dominate over morphology. Article omission is a classic local-but-frequent error ideal for cloze cards.

**Japanese (SOV, agglutinative, three scripts, honorifics).** Distinct error categories:
- **Particles (joshi):** は/が (topic vs. subject), を, に/で (location vs. destination/means) — empirically the single largest error category (one corpus-based study found particles at ~33% of grammatical errors). Strongly interlingual for L1s without particles.
- **Honorifics/politeness (keigo):** teineigo (polite), sonkeigo (respectful, others' actions), kenjougo (humble, own actions) — register errors. The rubric's **fidelity/register dimension is essential here**: a grammatically correct reproduction in the wrong politeness level is a real error. House's register-equivalence framing applies directly.
- **Scripts:** hiragana/katakana/kanji — kana and kanji selection errors; the inappropriate honorific prefix お on self-reference.
- **Topic-comment structure, counters/classifiers, no articles/plurals.** Long vs. short vowels and pitch accent are pronunciation-only (speech mode).
- **Localization:** raise the weight of the register/politeness and particle dimensions; treat keigo level as part of "fidelity," not optional polish.

**Chinese / Mandarin (SVO + topic-prominent, isolating, no inflection).** Distinct error categories:
- **Measure words/classifiers:** L2 learners over-rely on the general classifier 个 (ge) and underuse specific classifiers; classifier-noun agreement is a major lexical-grammatical error.
- **Topic-prominence:** Chinese is highly topic-prominent (Li & Thompson); learners (and reverse-direction transfer) produce double-subject / topic-comment structures; this transfer decreases with proficiency.
- **Aspect, not tense:** 了 (le), 过 (guo), 着 (zhe) mark aspect rather than tense — a major intralingual difficulty; the 把 (ba) construction is acquired late.
- **Characters (hanzi)** and **lack of inflection** mean errors cluster in word order, classifiers, aspect markers, and resultative complements rather than morphology.
- **Tones** are pronunciation-only (speech mode); irrelevant to text translation.
- **Localization:** weight classifier and aspect-marker categories heavily; tag topic-comment over-transfer as an interlingual structural error.

**General localization principle:** keep a shared cross-linguistic error schema (category × source × severity) but maintain a per-language sub-taxonomy of high-frequency error types and per-language dimension weightings (e.g., register weight high for Japanese, classifier weight high for Chinese, article weight high for English).

## Recommendations

**Stage 1 — MVP rubric + noticing loop (build first).**
1. Implement an **analytic rubric** with 4–5 dimensions: Accuracy, Understandability/Intelligibility, Fidelity/Register, Range/Articulateness, and a lower-stakes Naturalness/Nativeness line. Use 4-band CEFR-style descriptors.
2. Show the **original L2, the learner's reproduction, and a diff** side by side; make the diff the visual centerpiece (this is the noticing/comparison step — the actual learning event).
3. Show the rubric **before** the task (Sadler's "concept of the standard") and optionally prompt **self-rating** before revealing system scores.
4. Give feedback in Hattie & Timperley's three-part structure (feed-up / feed-back / feed-forward); use **direct correction + metalinguistic tag**.
5. **Weight understandability and accuracy highest; nativeness lowest.** *Benchmark to change this:* if user surveys or churn data show demotivation, reduce nativeness weight further or hide it for beginners.

**Stage 2 — Error synthesis.**
6. Tag each error by category × source (interlingual/intralingual) × severity (global/local) × error-vs-mistake.
7. Build a per-user **error profile** dashboard ranked by frequency × severity; expose it as a self-regulation tool ("article errors down 40%").
8. Only promote **systematic errors** (repeated ≥ N times, or wrong under production load) into the remediation queue.

**Stage 3 — Spaced remediation.**
9. Generate **cloze-deletion, production-oriented** cards isolating the corrected form; never show the error as the prompt; one atomic fact per card (minimum information principle).
10. Schedule with an **FSRS-style** algorithm; **interleave** error types within sessions (Rohrer & Taylor); include "isolate-and-re-translate the problem sentence" as a spaced, effortful card type.
11. Use **immediate** corrective feedback within a card; rely on **spacing** between reviews.

**Stage 4 — Localization.**
12. Ship the shared schema first, then per-language sub-taxonomies and dimension weightings (Japanese: particles + keigo register; Chinese: classifiers + aspect markers + topic-comment; English: articles + prepositions + tense/aspect).

**Cross-cutting:** Avoid extrinsic gamification of *scores* (Black & Wiliam's warning); instead make the **error profile shrinking** the reward (intrinsic, mastery-oriented, self-regulated). Keep nativeness aspirational. *Benchmark to revisit the whole approach:* track delayed re-test accuracy on previously-errored items — if spaced remediation isn't reducing recurrence within ~3–4 review cycles, revisit card formulation (likely violating the minimum information principle).

## Caveats
- **"Back-translation" is not an established pedagogical term.** The learning-science support comes from translation-as-pushed-output (Cook 2010; Duff 1989; Laufer & Girsai 2008), output/noticing theory, and skill acquisition — not from a body of work on "back-translation," which in academia means translation QA or MT data augmentation. The mechanism is sound; the label is the team's own.
- **The corrective-feedback evidence is genuinely contested.** The Truscott–Ferris debate is unresolved; direct vs. indirect superiority is "a matter of suitability rather than superiority." Treat the direct+metalinguistic recommendation as a defensible default, not settled fact, and A/B test.
- **The Noticing Hypothesis itself has critics** (Krashen and others dispute that conscious awareness is necessary). The feature does not depend on the strong version — the weaker "more noticing, more learning" formulation is sufficient justification.
- **Spacing/interleaving effect sizes come largely from lab and math/vocabulary studies;** generalization to translation-error remediation specifically is an inference, not a directly tested finding. Instrument the feature to measure recurrence reduction so you validate it on your own data.
- **Automated rubric scoring (if LLM-driven) will itself make errors,** especially on register/fidelity and on nativeness judgments where even human raters diverge. Surface confidence and allow learner override; this also doubles as a languaging prompt.
- **Some effect-size figures circulate in conflated forms** (e.g., a "63% vs. 20%" volume-formula result is from a separate Rohrer & Taylor study; a "59% vs. 36%" figure is Kornell & Bjork's painting study). The figures cited above (d = 1.34 in Rohrer & Taylor 2007; 72% vs. 38% in Rohrer, Dedrick & Burgess 2014) are the verified ones; page-number-level quotes from primary texts (Lado, Sadler, Krashen) were verified via reputable secondary sources and should be confirmed against primary editions before any public-facing citation.