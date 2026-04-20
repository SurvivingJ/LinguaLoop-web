# LinguaLoop: A Deterministic, LLM-Driven Vocabulary Acquisition Pipeline
### Grounded in Paul Nation's Receptive-to-Productive Continuum

***

## Executive Overview

This document specifies the complete architecture of the **LinguaLoop Vocabulary Acquisition Pipeline**: a deterministic, cacheable, ten-level exercise system that transitions a learner from zero knowledge of a target word to confident, native-like production. The design is grounded in Paul Nation's nine-component model of word knowledge, which distinguishes receptive from productive mastery across form, meaning, and use, and in empirical evidence that recognition knowledge is reliably acquired before recall knowledge across all word knowledge components.[^1][^2][^3]

The pipeline integrates three interconnected systems: a **Language Specification Router** that activates or bypasses exercise modules based on the typological features of the Target Language (TL); a **Part-of-Speech and Semantic Class Router** that enforces pedagogically appropriate sequencing for each word type; and a **deterministic LLM Generation Engine** that produces cacheable, zero-ambiguity exercise assets on first encounter and reuses them indefinitely. The ELO rating system provides the adaptive difficulty layer, simultaneously tracking learner proficiency and word difficulty in a validated, unsupervised manner.[^4][^5]

***

## Part I: Theoretical Foundations

### Paul Nation's Receptive-to-Productive Continuum

Word knowledge, in Nation's (2013) most comprehensive formulation, is not a binary state but a multi-component construct whose nine dimensions — spoken form, written form, word parts, form-meaning link, concepts and referents, associations, syntactic behavior, collocational behavior, and constraints on use — each possesses a receptive and a productive pole. The critical empirical finding driving this pipeline's ladder design is that **recognition (receptive) knowledge is acquired before recall (productive) knowledge** across all components without exception. Furthermore, structural equation modelling has established that the receptive and productive masteries of any given component must be treated as *separate constructs*, not as endpoints on a single scale.[^2][^3][^1]

Nation's "Four Strands" framework — meaning-focused input, meaning-focused output, language-focused learning, and fluency development — implies that no single exercise type is sufficient. LinguaLoop's ladder directly instantiates these strands: Levels 1–3 supply meaning-focused input; Levels 4–8 constitute language-focused learning; Level 9 demands syntactic assembly that bridges focused learning toward fluent output; and Level 10 is the productive output capstone.[^6]

The pipeline also draws on Nation's principle of **retrieval and elaboration**: productive retrieval (recalling the word form in order to express a meaning) creates deeper encoding than receptive retrieval (recognizing meaning from form). Each ascending level of the ladder demands a more effortful, productive operation, directly implementing Hulstijn and Laufer's (2001) finding that tasks requiring active involvement yield stronger acquisition outcomes.[^7][^8]

### Collocational Competence as a Distinct Acquisition Target

Collocations — recurring syntagmatic word pairings such as *make a decision* or *draw a conclusion* — are treated by the pipeline as a separate learning target, not an incidental by-product of semantic learning. Research on verb-noun collocations documents that even advanced learners frequently fail to improve their collocational accuracy as proficiency grows, because the abstract meaning of the verb-noun pairing (why *make* and not *do* for *mistake*?) requires explicit semantic restructuring through repeated, varied exposure to the same node word. The distinction between Collocation Gap Fill (Level 5, receptive recognition of the correct collocate) and Collocation Repair (Level 8, active selection of the most statistically frequent native-like collocate) directly operationalizes this research by spacing the two encounters and increasing productive demand at Level 8.[^9][^10][^11]

### ELO Ratings for Adaptive Matching

The pipeline assigns every learner and every word in the database a dynamic ELO rating, following the validated methodology of Hou et al. (2019), whose specialized ELO application to language learning showed a 0.90 correlation between ELO-predicted proficiency and teacher-assigned CEFR levels. Each exercise attempt produces a match: if the learner's rating significantly exceeds the word's difficulty rating, a correct answer yields a small positive delta; an incorrect answer yields a larger negative delta. The K-factor is set high for new learners (rapid calibration) and decreases as more attempts accumulate (stable equilibrium). Words are selected for a session from the zone of proximal development — exercises where the learner's ELO rating is within ±150 points of the word's difficulty rating — to maintain the cognitive challenge that drives acquisition.[^12][^5][^4]

***

## Part II: Language Specification Files

Each TL is characterized by a machine-readable spec object queried at pipeline initialization. The spec determines which Level 4 module variant is loaded and whether collocation modules are enriched with morphological consideration.

```json
{
  "EN": {
    "language_name": "English",
    "has_morphology": true,
    "morphology_types": ["verb_conjugation", "noun_plural", "comparative_adjective"],
    "has_grammatical_gender": false,
    "has_particles": false,
    "has_measure_words": false,
    "level_4_module": "morphology"
  },
  "ZH": {
    "language_name": "Mandarin Chinese",
    "has_morphology": false,
    "has_grammatical_gender": false,
    "has_particles": true,
    "particle_types": {
      "aspectual": ["了", "过", "着"],
      "structural": ["的", "得", "地"]
    },
    "has_measure_words": true,
    "measure_word_examples": ["个", "条", "张", "本", "把", "块"],
    "level_4_module": "particles_or_measure_words"
  },
  "JA": {
    "language_name": "Japanese",
    "has_morphology": true,
    "morphology_types": ["verb_conjugation_agglutinative", "adjective_conjugation"],
    "has_grammatical_gender": false,
    "has_particles": true,
    "particle_types": {
      "case_markers": ["は", "が", "を", "に", "で", "へ", "と", "から", "まで"]
    },
    "has_measure_words": true,
    "counter_examples": ["本", "枚", "匹", "台", "冊", "杯"],
    "level_4_module": "morphology_and_particles_or_counters"
  }
}
```

**Design rationale for Chinese:** Mandarin's morphological isolation is not a deficit but a structural choice — the language encodes aspect, transitivity, and nominal quantity through particles and classifiers rather than inflectional endings. This is a grammatical commitment of the same cognitive weight as English verb conjugation, and learners who bypass classifier training produce utterances that, while often interpretable, signal non-native processing. The pipeline therefore substitutes the Level 4 Morphology module with a Measure Word/Particle module for Chinese, rather than simply skipping Level 4 entirely.[^13][^14]

**Design rationale for Japanese:** Japanese is agglutinative, encoding tense, politeness, negation, and modality through sequential suffixation to verb stems. Its particle system simultaneously marks grammatical case, and L2 learners (particularly English L1 speakers who lack case marking) demonstrate persistent errors in particle selection that are qualitatively different from those of Japanese L1 speakers learning Korean — confirming that the particle acquisition challenge is a language-specific cognitive burden, not merely cross-linguistic transfer. Japanese therefore activates both the Morphology module (verb/adjective conjugation) and the Particle/Counter module within Level 4.[^15][^16]

***

## Part III: POS and Semantic Class Routing Logic

The routing table below governs which exercise modules are activated for a given word. The pipeline evaluates POS and semantic class at word registration time, writes the resulting module list to the database, and loads it for every subsequent session involving that word.

| POS / Semantic Class | L1 | L2 | L3 | L4 (EN) | L4 (ZH) | L4 (JA) | L5 Gap Fill | L6 Sem. Disc. | L7 Syntax | L8 Repair | L9 Jumble | L10 Cap. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Concrete Noun | ✓ | ✓ | ✓ | Morpho (plural) | Measure Word | Counter + Particle | ✗ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Abstract Noun | ✓ | ✓ | ✓ | Morpho (plural) | Particle (structural) | Counter + Particle | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Verb | ✓ | ✓ | ✓ | Morpho (conjugation) | Aspectual Particle | Verb Conjugation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Adjective | ✓ | ✓ | ✓ | Morpho (comparative) | Structural (的/地) | Adjective Conjugation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Notes:**
- "✗" denotes a **SKIP** enforced by the router; the level is not presented to the learner and does not affect their ELO calculation for that word.
- For concrete nouns in Chinese, the measure word module replaces the morphology module since Chinese nouns do not inflect. Generating morphological exercises for 书 (*shū*, book) would be linguistically invalid.[^13]
- Collocation exercises (L5, L8) are skipped for concrete nouns because such nouns do not possess high-frequency obligatory verb collocates; their co-occurrence patterns are looser and contextually motivated, unlike the tight lexical bonds of *make a decision* or *mitigate risk*.[^10][^1]

***

## Part IV: The Master Exercise Bank — Full Specification

The following section defines the complete generation guardrails for each level. When the LLM generation engine encounters a new word, it receives the Language Spec and POS routing table and outputs a single JSON asset object. This object is written to the database and never regenerated.

### Level 1 — Listening Flashcard (Phonetic Discrimination)

**Cognitive Target:** Distinguishing the target word's phonological and orthographic form from near-neighbors. This corresponds to Nation's *spoken form (receptive)* and *written form (receptive)* components.[^1]

**Generation Guardrails:**
- Generate 3 TL distractors that are **phonetically similar** (share 2+ phonemes with the target in the same syllabic position) or **orthographically similar** (differ by 1–2 characters/letters, e.g., homoglyphs, similar radicals in Chinese, similar kanji in Japanese).
- **Zero semantic overlap permitted.** Distractors must not be synonyms, near-synonyms, or semantically related to the target word.
- **Same or similar character/syllable length** where typologically possible (±1 syllable for English; same character count for Chinese/Japanese).
- The audio file for the target word is served to the learner; the text options display all four candidate words. This is a **listening test** as defined in the system spec.

**Example (EN, verb: *adapt*):** Audio plays "adapt." Options: *adept*, *adopt*, *apart*, *adapt* ✓

**Example (ZH, noun: 张 / *zhāng*, sheet of paper):** Audio plays *zhāng*. Options: 章 (*zhāng*, chapter), 长 (*zhǎng*, grow), 掌 (*zhǎng*, palm), 张 ✓ — exploiting tonal and orthographic near-identity[^17]

### Level 2 — Text Flashcard (Semantic Definition Matching)

**Cognitive Target:** Establishing the form-meaning link at a CEFR-appropriate level of abstraction.[^18]

**Generation Guardrails:**
- Generate 1 **TL definition** of the target word, calibrated to the learner's current CEFR band (A1–C2). At A1–A2, definitions use only the 1,000 most frequent words; at C1–C2, technical elaboration is permitted.[^19]
- Generate 3 **TL definitions of unrelated words** from the same CEFR frequency band. These are definitions of real words, not fabricated descriptions.
- **Core semantic meaning must not overlap** between any distractor definition and the target definition. A distractor defining "rapid" is inadmissible as a distractor for "swift"; "turbulent" is admissible.
- Display format: the target word is shown; the learner selects the correct definition.

**Distractor quality standard:** Following Cambridge Assessment English's evidence-based approach to distractor generation, distractors must be plausible enough to attract a learner who does not fully know the word, but clearly wrong to one who does.[^20][^21]

### Level 3 — Cloze Completion (Contextual Placement)

**Cognitive Target:** Activating knowledge of the word's syntactic environment and contextual fitness — Nation's *syntactic behavior (receptive)* component.[^3][^1]

**Generation Guardrails:**
- Generate a **simple TL sentence** at the learner's CEFR level with the target word blanked out. The sentence must make the target word strongly inferrable from context.
- Generate 3 distractor words that are: (a) the **same POS** as the target, (b) **grammatically valid** in the blank (i.e., the sentence is well-formed with the distractor), but (c) **contextually nonsensical or semantically anomalous** in that sentence.
- The TL definition from Level 2 is displayed as a UI hint beneath the sentence.
- This design follows the principle that MCQ distractors must represent typical learner confusions at the right proficiency level, not arbitrary noise.[^22][^20]

**Example (EN, verb: *mitigate*):** "The engineers developed new protocols to \_\_\_ the environmental damage." Options: *celebrate*, *mitigate* ✓, *identify*, *purchase* — all verbs, all grammatically valid, three contextually absurd.

### Level 4 — Language-Specific Grammar Slot

**Cognitive Target:** Nation's *word parts (receptive)* and *syntactic behavior (receptive)* components, implemented through the TL's dominant grammatical encoding system.[^3][^1]

This level is the most typologically differentiated module in the pipeline. The Language Spec routes the word to one of three sub-modules.

#### Sub-module 4A: Morphological Inflection (EN, JA)

For English verbs and adjectives, and for all Japanese verb/adjective classes, a sentence is generated requiring a **specific inflected form** of the target word. The four answer options are all morphological siblings of the target — valid surface forms of the same lexeme.

**EN example (verb: *adapt*):** "She quickly \_\_\_ to the new environment." Options: *adapt*, *adapts*, *adapted* ✓, *adapting* — each is a real form; only the past simple is grammatically correct here.

**JA example (verb: 食べる, *taberu*, to eat):** "明日、寿司を\_\_\_。" Options: 食べる (dictionary form), 食べた (past), 食べます ✓ (polite non-past, contextually required), 食べて (te-form) — exploiting Japanese's agglutinative morphological paradigm.[^16]

#### Sub-module 4B: Measure Words / Counters (ZH concrete nouns, JA concrete nouns)

A sentence is generated in which the target noun appears with a **blanked-out measure word or counter**. The four options are all legitimate measure words/counters drawn from the high-frequency inventory of that language.

**ZH example (noun: 书, *shū*, book):** "我想买\_\_\_书。" Target: 本 ✓. Distractors: 个, 条, 张 — all genuine classifiers in Chinese, but semantically and categorically incorrect for bound/codex objects.[^23][^24][^13]

**JA example (noun: 本, *hon*, book):** "三\_\_\_の本を読んだ。" Target: 冊 ✓. Distractors: 本 (cylindrical objects), 枚 (flat objects), 台 (machines) — all valid counters, misapplied.

#### Sub-module 4C: Aspectual/Case Particles (ZH verbs, JA verbs/nouns)

A sentence is generated using the target verb/noun with the **grammatical particle blanked out**.

**ZH example (verb: 去, *qù*, to go):** "我\_\_\_过北京。" Target: 去过 — blank is 过 ✓ (experiential aspect). Distractors: 了 (perfective), 着 (progressive), 的 (structural) — all valid particles in other syntactic configurations, creating genuine learner confusion.[^14]

**JA example (verb used as location argument):** "学校\_\_\_行く。" Target particle: に ✓ (direction marker). Distractors: が, を, で — each marks a different grammatical role, all superficially plausible.[^25]

### Level 5 — Collocation Gap Fill

**Activation:** Abstract nouns, verbs, adjectives only. **SKIP** for concrete nouns.

**Cognitive Target:** Nation's *collocational behavior (receptive)* component — recognizing the natural lexical partner of the target word.[^10][^1]

**Generation Guardrails:**
- Generate a sentence where the **target word is visible and present**, but its **primary natural collocate** is blanked out.
- The three distractors must be words that carry overlapping meaning to the correct collocate but are **unnatural or non-native in this collocation** — they must not be random words, but near-synonyms that learners from L1 backgrounds frequently substitute for the native collocate.[^11][^9]
- This specifically tests the learner's ability to distinguish native-like co-occurrence patterns from plausible-but-wrong substitutes.

**EN example (noun: *mistake*):** "It is very easy to \_\_\_ a mistake when you are tired." Correct: *make* ✓. Distractors: *do*, *commit*, *perform* — all verbs meaning "to carry out an action," all documented over-generalization errors in EFL learner corpora.[^11]

**EN example (noun: *decision*):** "The board will \_\_\_ a decision by Friday." Correct: *make* ✓. Distractors: *do*, *take*, *reach* — where *take* (British variant) and *reach* could be argued as acceptable in specific registers; the correct answer is specified as the highest-frequency native collocate in the relevant corpus.

**ZH example (abstract noun: 决定, *juédìng*, decision):** "他已经\_\_\_了决定。" Correct: 做 ✓ (make). Distractors: 说 (say), 想 (think), 有 (have) — grammatically plausible, collocationally anomalous.

### Level 6 — Semantic Discrimination

**Cognitive Target:** Nation's *concepts and referents (receptive)* and *constraints on use (receptive)* — distinguishing the word's semantic range and register.[^1][^3]

**Generation Guardrails:**
- Generate **4 complete TL sentences**, all using the target word as written (no spelling changes).
- **1 sentence is perfectly natural:** correct meaning, correct register, correct collocation.
- **3 sentences contain semantic/contextual errors:** the target word is grammatically embedded correctly, but used in the wrong semantic domain, the wrong register (formal word in casual context or vice versa), or with a meaning that violates the word's semantic restrictions.
- **Grammar must be correct in all 4 sentences.** The error is purely at the semantic/pragmatic level.
- This follows the Cambridge MCQ design principle that errors must be detectable by a knowledgeable learner but not by a purely grammatical analysis.[^21][^20]

**EN example (verb: *mitigate*):** 
1. ✓ "New safety measures were implemented to mitigate the risk of flooding."
2. ✗ "She mitigated her birthday cake with extra frosting." (wrong semantic domain: mitigate requires a negative entity)
3. ✗ "The children mitigated happily in the park." (intransitive misuse — mitigate requires a direct object)
4. ✗ "Please mitigate the window before dinner." (category violation: mitigate operates on abstract harms, not physical objects)

### Level 7 — Spot the Incorrect Sentence (Syntactic/Structural Accuracy)

**Cognitive Target:** Nation's *syntactic behavior (receptive)* at the productive threshold — identifying structurally ill-formed usage involving the target word.[^2][^1]

**Generation Guardrails:**
- Generate **3 TL sentences that are grammatically and structurally correct** with the target word.
- Generate **1 TL sentence containing a structural error** that mimics a documented learner mistake: wrong preposition, transitivity error, incorrect particle selection (ZH/JA), or improper word-order placement.
- **The spelling of the target word must be unchanged across all four sentences.**
- The error category must reflect authentic learner corpus data — not invented errors, but patterns documented in L2 production research.[^26][^15]

**EN example (verb: *adapt*):**
1. ✓ "The director adapted the novel for the screen."
2. ✓ "She adapts well to new challenges."
3. ✗ "The students adapted to quickly the new curriculum." (adverb misplacement — a documented L1-transfer error for Japanese/Chinese EFL learners)
4. ✓ "The technology was adapted from an older design."

**ZH example (verb: 去, *qù*):**
1. ✓ 我昨天去了图书馆。
2. ✓ 她明天去北京。
3. ✗ 我去了明天图书馆。 (time phrase placed after verb — violates Chinese time-before-verb-phrase rule, a documented L2 Chinese error)[^27]
4. ✓ 他们去学校了。

### Level 8 — Collocation Repair

**Activation:** Abstract nouns, verbs, adjectives only. **SKIP** for concrete nouns.

**Cognitive Target:** Nation's *collocational behavior (productive)* — the most cognitively demanding collocation task in the pipeline, requiring active selection of the statistically dominant native collocate.[^28][^9][^1]

**Generation Guardrails:**
- Generate **1 sentence containing a forced unnatural collocation** involving the target word — the collocate present in the sentence is plausible but non-native.
- Provide **4 replacement options** for the unnatural collocate.
- The **correct option must be the most statistically frequent native collocate** in a reference corpus (e.g., BNC/COCA for English, CCL for Chinese).
- The 3 distractors are: the original unnatural word, and 2 near-synonyms that are less frequent or register-restricted alternatives.

**EN example (noun: *attention*):** "You need to *give* attention to detail in this work." → Replace *give*: Options: *pay* ✓, *give*, *show*, *direct* — *pay attention* is the dominant BNC/COCA collocate; *give* is documented as an L1-transfer error (from languages where the equivalent verb is 给/donner/dar).[^11]

### Level 9 — Jumbled Sentence (Syntactic Assembly)

**Cognitive Target:** Nation's *syntactic behavior* at the full productive threshold — assembling the target word into a correctly ordered TL utterance from constituent syntactic chunks.[^1]

**Generation Guardrails:**
- Generate a **correct TL sentence** involving the target word and split it into **4–5 logical syntactic chunks** — not individual words, but phrasal units (NP, VP, PP, adverbial).
- Generate **3 incorrect chunk sequences** that reflect **documented learner word-order errors**, not random shuffles:
  - **English:** Misplaced adverbials (e.g., frequency adverbs after the main verb instead of before), wrong position of time phrases relative to clause.
  - **Chinese:** Time adverbial placed after the verb phrase rather than before (violating Chinese temporal-before-predicate ordering); manner adverb placed after verb rather than before.[^27]
  - **Japanese:** Object phrase placed after the verb rather than before (violating Japanese SOV order); topic marker misplaced.[^25]

**EN example (verb: *mitigate*):** Chunks: [The new policy] [significantly mitigated] [the economic impact] [of the crisis]. Incorrect sequence 1: [The new policy] [mitigated significantly] [the economic impact] [of the crisis] — adverb post-verb misplacement.

**ZH example (verb: 去):** Chunks: [我] [昨天] [去了] [图书馆]. Incorrect sequence: [我] [去了] [昨天] [图书馆] — time adverbial after verb.

### Level 10 — Capstone Dual Translation

**Cognitive Target:** Nation's full productive pole across all components: form, meaning, use, collocation, syntax, register — activated simultaneously in free production.[^8][^7][^1]

**Generation Guardrails (Content Retrieval):**
- The system queries the **corpus inverted index** to retrieve a paragraph in which: (a) the target word appears at least once, and (b) **100% of the remaining vocabulary** maps to words the learner has already completed at Level 10 (i.e., are in the learner's "productive inventory" as recorded in the database).
- The **L1 translation** of this paragraph is displayed to the learner.
- The learner **types the TL translation** in a free-text field.

**L1 is only permitted at this level.** All preceding levels (1–9) operate exclusively in the TL, enforcing TL-immersive processing from the first encounter.[^7]

**Grading Rubric (LLM-evaluated):**
The generated rubric for each word is stored in the database alongside the exercise assets. The grading LLM evaluates the learner's submission on four criteria:
1. **Lexical accuracy of target word** (correct form, correct morphological inflection if applicable): 0–3 points
2. **Collocational naturalness** of the target word's immediate context: 0–2 points
3. **Syntactic accuracy** of the full sentence containing the target word: 0–2 points
4. **Register and pragmatic appropriateness** relative to the L1 source text: 0–3 points

A score of 8/10 or above marks the word as **productively acquired** in the database, triggering a positive ELO adjustment for both the learner and the word.

***

## Part V: Determinism, Caching, and the LLM Generation Engine

### The Case for Generate-Once, Cache-Forever

The principal argument for exercise caching is not merely computational efficiency — it is **assessment validity**. A learner who encounters the same exercise twice is being tested on the same item, and their performance trajectory across encounters is a meaningful signal for spaced repetition scheduling. Regenerating the exercise on each encounter destroys this signal. It also reintroduces the risk of LLM output variance: even at temperature=0, modern large language models operating on mixture-of-experts architectures cannot guarantee bit-identical outputs across independent calls due to non-deterministic GPU kernel execution. The generate-once strategy eliminates this variance at the source.[^29][^30][^31]

### Database Schema for Exercise Assets

```json
{
  "word_id": "uuid",
  "target_word": "mitigate",
  "language": "EN",
  "pos": "verb",
  "semantic_class": "abstract_process",
  "cefr_band": "C1",
  "elo_difficulty": 1620,
  "active_levels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "exercises": {
    "level_1": {
      "type": "listening_flashcard",
      "audio_key": "s3://audio/mitigate.mp3",
      "options": ["mitigate", "meditate", "motivate", "moderate"],
      "correct_index": 0
    },
    "level_2": {
      "type": "text_flashcard",
      "target_definition": "to make something harmful or unpleasant less severe or serious",
      "options": [
        "to make something harmful or unpleasant less severe or serious",
        "to arrange objects in a specific order",
        "to increase the speed of a moving object",
        "to express a feeling of satisfaction"
      ],
      "correct_index": 0
    },
    "level_3": {
      "type": "cloze_completion",
      "sentence": "Engineers designed the new barrier system to ___ the risk of coastal flooding.",
      "hint": "to make something harmful less severe",
      "options": ["celebrate", "mitigate", "identify", "purchase"],
      "correct_index": 1
    },
    "level_4": {
      "submodule": "morphology_EN",
      "sentence": "The government has already ___ the worst effects of the economic downturn.",
      "options": ["mitigate", "mitigates", "mitigated", "mitigating"],
      "correct_index": 2,
      "target_form": "past_simple"
    },
    "level_5": {
      "type": "collocation_gap_fill",
      "sentence": "Policymakers are working to ___ the environmental damage caused by the spill.",
      "collocate_pos": "verb",
      "options": ["mitigate", "alleviate", "lessen", "reduce"],
      "correct_index": 0,
      "note": "Target word IS the correct answer; the gap is for the collocate."
    }
  },
  "generation_hash": "sha256:abc123...",
  "generated_at": "2026-04-06T00:00:00Z",
  "generation_model": "gpt-4o",
  "generation_prompt_version": "v2.3"
}
```

> **Note on Level 5 schema:** Level 5 (Collocation Gap Fill) blanks out the collocate *of* the target word, meaning the target word itself is visible in the sentence and the four options are candidate collocates. Level 8 (Collocation Repair) displays a sentence where the target word is present with a *wrong* collocate, and the four options are candidate replacements for that wrong collocate. These are structurally distinct operations targeting receptive vs. productive collocational knowledge.[^9]

### LLM Prompt Architecture for Generation

Following controlled LLM pipeline best practices, the generation prompt is structured with a static prefix (system role, language spec, guardrails) and a dynamic suffix (target word, POS, CEFR band). The static prefix is submitted to the prompt cache layer on the first call and serves all subsequent generation requests without re-tokenization.[^31][^32][^33]

```
SYSTEM (static, cached):
You are a computational linguist generating vocabulary exercise assets for LinguaLoop.
Language: {TL}
Language Spec: {lang_spec_json}
POS: {pos}
Semantic Class: {semantic_class}
Active Levels: {active_levels_list}
Guardrails: [full Level 1–10 specifications as structured JSON schema]
Output: A single valid JSON object matching the exercise_asset schema.
Temperature: 0
Response format: application/json

USER (dynamic):
Target word: "{word}"
CEFR band: "{cefr}"
Generate all exercise levels specified in Active Levels.
```

All outputs are validated against a JSON schema before database insertion. Any output that fails schema validation (e.g., an exercise where `options.length != 4`, or where the correct index is out of range) triggers an automatic retry with an augmented prompt that includes the validation error.[^32]

***

## Part VI: The ELO Matching and Scheduling Layer

### Rating Architecture

Two ELO pools are maintained:
1. **Learner ELO** (`elo_learner`): initialized at 1000 for new users; maps to CEFR A2–B1 threshold.[^12]
2. **Word ELO** (`elo_word`): initialized based on CEFR band (A1=800, A2=900, B1=1050, B2=1200, C1=1400, C2=1600) and refined through aggregated learner performance data.[^4]

The expected probability of a correct answer \( E \) is computed as:

\[ E = \frac{1}{1 + 10^{(R_{\text{word}} - R_{\text{learner}}) / 400}} \]

where \( R_{\text{word}} \) is the word's current ELO difficulty and \( R_{\text{learner}} \) is the learner's current ELO proficiency. After each attempt, both ratings are updated:

\[ R' = R + K \cdot (S - E) \]

where \( S = 1 \) for a correct answer and \( S = 0 \) for an incorrect answer, and \( K \) is the adaptive K-factor (K=32 for < 30 total attempts; K=16 for 30–100 attempts; K=8 for > 100 attempts).[^5][^12]

### Session Construction

Each session presents words such that the learner's ELO falls within ±150 points of the selected word's ELO. Words are drawn from a priority queue ordered by:
1. **Scheduled review date** (spaced repetition interval, computed from prior performance)
2. **ELO proximity to learner** (zone of proximal development enforcement)
3. **Incomplete ladder position** (words currently on Level 3 take precedence over new Level 1 introductions if the queue is non-empty)

### CEFR-ELO Bridge

| CEFR Level | Suggested Vocabulary Size[^19] | Word ELO Range |
|---|---|---|
| A1 | ~500 words | 700–850 |
| A2 | ~1,000 words | 850–1,000 |
| B1 | 2,000–3,000 words | 1,000–1,150 |
| B2 | 4,000 words | 1,150–1,350 |
| C1 | 5,000–6,000 words | 1,350–1,550 |
| C2 | 7,000–9,000 words | 1,550–1,750 |

***

## Part VII: The Full Generation Prompt for a Sample Word

The following is the complete LLM execution directive for the word *adapt* (EN, verb, abstract process, CEFR B2), illustrating how all five specification layers (language spec, POS routing, guardrails, output schema, determinism enforcement) converge into a single cacheable generation call.

```json
{
  "system_role": "You are an expert computational linguist generating vocabulary exercise assets. Follow all guardrails exactly. Output only valid JSON.",
  "language_spec": {
    "language": "EN",
    "has_morphology": true,
    "has_particles": false,
    "has_measure_words": false
  },
  "word": "adapt",
  "pos": "verb",
  "semantic_class": "abstract_process",
  "cefr_band": "B2",
  "active_levels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "guardrails": {
    "level_1": "3 phonetically/orthographically similar distractors. No semantic overlap. Similar length.",
    "level_2": "1 TL definition (B2-appropriate). 3 distractor definitions of unrelated B2 words.",
    "level_3": "Cloze sentence. 3 distractors: same POS, grammatically valid, contextually nonsensical.",
    "level_4": "Morphology submodule. 4 options = valid morphological forms of 'adapt'. One contextually correct.",
    "level_5": "Collocation gap fill. Target word present in sentence. Blank = primary collocate. Distractors = near-synonyms of correct collocate that are unnatural with 'adapt'.",
    "level_6": "4 complete sentences. 1 natural. 3 semantically/contextually wrong. All grammatically correct.",
    "level_7": "3 correct sentences. 1 with documented learner error (wrong preposition or adverb placement). Target word spelling unchanged.",
    "level_8": "1 sentence with unnatural collocate. 4 replacement options. Correct = highest-frequency BNC/COCA collocate.",
    "level_9": "1 sentence split into 4-5 syntactic chunks. 3 wrong orderings reflecting documented learner word-order errors.",
    "level_10": "Grading rubric: lexical accuracy (0-3), collocational naturalness (0-2), syntactic accuracy (0-2), register (0-3)."
  },
  "output_format": "exercise_asset_schema_v2.3",
  "temperature": 0
}
```

***

## Part VIII: Cross-Linguistic Design Notes

### Why Chinese Requires the Deepest Structural Departure

The pipeline's most significant typological accommodation is for Mandarin Chinese, and it reflects a principle that extends beyond system design into the philosophy of language pedagogy: **the absence of morphology in an isolating language is not a simplification, but a redistribution of cognitive labor**. Where English encodes tense through verb inflection (*walk / walked*), Mandarin encodes aspect through post-verbal particles (了, 过, 着) that cannot be reduced to mere suffixes — they carry distinct aspectual semantics (perfective completion, experiential past, ongoing state) that have no one-to-one English correspondence. A pipeline that simply skips Level 4 for Chinese would be generating fewer exercises while demanding more of the learner's implicit inference system. The present design assigns measure words and aspectual particles their own dedicated level, treating them as cognitive objects of equal standing to English morphological paradigms.[^14][^27]

Chinese classifier acquisition (量词, *liàngcí*) has been documented as particularly challenging for L2 learners because individual nouns do not carry classifier information morphologically — the correct classifier must be retrieved from semantic memory based on the noun's physical or conceptual properties (shape, flexibility, countability, conventionality). The Level 4B exercise specifically targets this retrieval challenge by presenting four formally distinct but categorically plausible classifiers as distractors, forcing the learner to activate semantic-categorical knowledge rather than surface pattern matching.[^13][^14]

### Japanese's Dual Grammar Burden

Japanese learners face the combinatorial challenge of a fully agglutinative morphological system *and* a case-marking particle system operating simultaneously. The pipeline does not simplify this by choosing one or the other: it presents both within Level 4 (morphology for verbs/adjectives; particles for grammatical arguments) and extends particle testing into the Level 7 error-spotting module, where misplaced or substituted particles constitute the most common documented learner error category in L2 Japanese corpora. The Level 9 jumbled sentence module reflects the SOV word order requirement, using incorrect sequences in which objects are displaced after the verb — a documented error pattern for L1 English learners of Japanese whose L1 grammar instills a default SVO schema.[^34][^26][^16][^25]

***

## Part IX: Quality Assurance and Validation Protocols

### Zero-Ambiguity Enforcement

Before any exercise is committed to the database, it passes through an automated validation pipeline:

1. **Schema validation:** JSON output matches the exercise_asset schema (4 options, 1 correct index, required string fields present).
2. **Ambiguity audit (LLM-as-judge):** A second LLM call, using a different model, evaluates whether any distractor could plausibly be argued as the correct answer. If ambiguity is detected, the exercise is flagged for human review and blocked from deployment.
3. **Semantic distinctness check:** For Level 2 (definition matching), a cosine similarity score between the correct definition's embedding and each distractor embedding must exceed 0.3 (sufficiently distinct); for Level 6 (semantic discrimination), the three incorrect sentences must score below 0.7 on a naturalness model to confirm they are detectable as wrong.[^35]
4. **TL-exclusivity audit (Levels 1–9):** A regex + language detection check confirms no L1 tokens appear in the exercise body, options, or hints of Levels 1–9.

### Human Review Triggers

Exercises are automatically routed to a human reviewer if:
- Ambiguity audit flags a distractor as potentially correct.
- The target word has fewer than 3 corpus attestations at the specified CEFR level.
- The word is a proper noun, acronym, or multi-word expression (edge cases requiring manual classification).
- Any generated sentence contains a named entity that may carry political, religious, or culturally sensitive connotations.

***

## Appendix: Routing Decision Flowchart (Pseudocode)

```python
def build_exercise_ladder(word: str, pos: str, semantic_class: str, lang: str) -> List[int]:
    spec = load_language_spec(lang)
    ladder = [1, 2, 3]  # Always include Levels 1, 2, 3

    # Level 4: Language-specific grammar
    if spec["has_morphology"] and pos in ["verb", "adjective"]:
        ladder.append({"level": 4, "submodule": "morphology"})
    if spec["has_morphology"] and pos == "noun":
        ladder.append({"level": 4, "submodule": "morphology_plural"})
    if spec["has_measure_words"] and pos in ["concrete_noun"]:
        ladder.append({"level": 4, "submodule": "measure_word"})
    if spec["has_particles"] and pos == "verb":
        ladder.append({"level": 4, "submodule": "particle_aspectual"})
    if spec["has_particles"] and pos == "noun":
        ladder.append({"level": 4, "submodule": "particle_case"})

    # Level 5 & 8: Collocations — skip for concrete nouns
    if semantic_class != "concrete_noun":
        ladder.append(5)  # Collocation Gap Fill
        ladder.append(8)  # Collocation Repair

    # Levels 6, 7, 9: Universal
    ladder.extend([6, 7, 9])

    # Level 10: Always last
    ladder.append(10)

    return sorted(set(ladder))
```

This routing logic guarantees a minimum of 7 levels (concrete nouns: 1, 2, 3, 4, 6, 7, 9, 10 = 8 levels) and a maximum of 10 levels (abstract nouns, verbs, adjectives in Japanese: all levels active). The ladder is deterministic for a given (word, POS, semantic_class, language) tuple and is stored in the database alongside the exercise assets.

---

## References

1. [Components Of Word Knowledge Adapted From Nations English ...](https://www.ukessays.com/essays/english-language/components-of-word-knowledge-adapted-from-nations-english-language-essay.php) - Amongst the first was by Richards (1976), who suggested seven aspects of word knowledge: syntactic b...

2. [Word Knowledge: Exploring the Relationships and Order of ...](https://academic.oup.com/applij/article/41/4/481/5270836) - Abstract. This study explores the overall nature of the vocabulary knowledge construct by examining ...

3. [[PDF] Word Knowledge - Nottingham Repository](https://nottingham-repository.worktribe.com/preview/1513668/Word%20Knowledge%20-%20RESUBMITTED.pdf) - ... word knowledge. Nation's (ibid.) framework suggests that receptive and productive knowledge are ...

4. [[PDF] Modeling language learning using specialized Elo rating](https://aclanthology.org/W19-4451.pdf) - This application of Elo provides ratings for learners and concepts which correlate well with subject...

5. [[PDF] Applications of the Elo Rating System in Adaptive Educational ...](https://www.fi.muni.cz/~xpelanek/publications/CAE-elo.pdf) - We argue that the Elo rating system is simple, robust, and effective and thus suitable for use in th...

6. [Paul Nation's Theory | PDF - Scribd](https://www.scribd.com/document/666244760/Paul-Nation-s-Theory) - Paul Nation's framework proposes four strands of language teaching: meaning-focused input, meaning-f...

7. [[PDF] How vocabulary is learned - Paul Nation - Neliti](https://media.neliti.com/media/publications/242518-how-vocabulary-is-learned-45a2c109.pdf) - In other words receptive knowledge can become productive knowledge. It is important that this relati...

8. [Receptive and productive vocabulary acquisition](https://dialnet.unirioja.es/descarga/articulo/7857659.pdf)

9. [On effective learning of English collocations: From perspectives of distributed practice and semantic restructuring](https://onlinelibrary.wiley.com/doi/full/10.1002/tesj.767) - ## Abstract

Knowledge of collocations facilitates second language (L2) learning by enhancing accura...

10. [Research on L2 learners' collocational competence and ...](http://www.eurosla.org/monographs/EM02/Henriksen.pdf)

11. [Gauging the effects of exercises on verb–noun collocations](https://ir.lib.uwo.ca/cgi/viewcontent.cgi?article=1105&context=edupub)

12. [ELO Rating for Language Learning: How It Works - Dialog Engine](https://dialogengine.ai/learn/elo-rating-language-learning) - Your ELO rating maps directly to CEFR levels, giving you a universally understood measure of where y...

13. [Wen-yu Huang](https://studenttheses.universiteitleiden.nl/access/item:2659912/view)

14. [07 RIEA Vol2 Num3.indd](https://www.revistas.ucr.ac.cr/index.php/riea/article/download/52212/54707/234185)

15. [[PDF] Cross-linguistic Influence in the L2 Acquisition of Korean Case ...](https://e-flt.nus.edu.sg/v10n22013/brown.pdf) - This study employs longitudinal data collected from multiple sources to investigate the acquisition ...

16. [Case in Japanese. A Morphological Approach (2022) - Academia.edu](https://www.academia.edu/73746583/Case_in_Japanese_A_Morphological_Approach_2022_) - Japanese nominal elements are agglutinative and can be systematically described by a morphological c...

17. [Chinese Measure Words: Complete Guide to Mandarin Classifiers](https://migaku.com/blog/chinese/chinese-measure-words) - Learn Chinese measure words the right way. Master 24 common classifiers in Mandarin Chinese through ...

18. [Level-based CEFR Vocabulary - LanGeek Help Center](https://help.langeek.co/content/vocabulary/cefr-vocabulary/) - It offers a systematic approach to vocabulary acquisition, tailored to the guidelines of the Common ...

19. [[DOC] doc18.4KBVocabulary and the CEFR](https://www.wgtn.ac.nz/lals/resources/paul-nations-resources/vocabulary-lists/vocabulary-cefr-and-word-family-size/vocabulary-and-the-cefr-docx) - Has sufficient vocabulary to conduct routine, everyday transactions involving familiar situations an...

20. [Designing effective multiple-choice questions for language ...](https://www.cambridgeassessment.org.uk/blogs/mcq-design-language-blog/) - To assist educators in improving their MCQ design for language assessment, Margaret Cooze, expert in...

21. [[PDF] based approach to distractor generation in multiple-choice language ...](https://www.cambridgeenglish.org/Images/526186-research-notes-72.pdf)

22. [Designing Multiple-Choice Questions | Centre for Teaching Excellence](https://uwaterloo.ca/centre-for-teaching-excellence/catalogs/tip-sheets/designing-multiple-choice-questions) - General strategies for creating effective multiple-choice questions, including tips for writing clea...

23. [Chinese classifier categorizations and the application to second ...](https://studenttheses.universiteitleiden.nl/handle/1887/52141)

24. [Chinese Measure Words and How to Use Them | The Chairman's Bao](https://www.thechairmansbao.com/blog/chinese-measure-words/) - Master Chinese measure words effortlessly! Explore this guide for practical insights and enhance you...

25. [Japanese word order - Grammar - Kanshudo](https://www.kanshudo.com/grammar/word_order) - Learn about Japanese word order on Kanshudo - the fastest and most enjoyable way to learn Japanese g...

26. [Analysis of Japanese complex particles in L2 learners' compositions](https://gupea.ub.gu.se/handle/2077/44454) - While the research on so-called complex particles – or compound case particles – has flourished in t...

27. [[PDF] CHINESE SENTENCE PROCESSING BY FIRST AND SECOND ...](https://scholarspace.manoa.hawaii.edu/bitstreams/6c1c1889-334b-4552-a825-c087e7a6d6f5/download) - test whether word order, animacy, and discourse context affect one another in sentence ... interpret...

28. [The impact of collocational proficiency features on expert ratings of ...](https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/impact-of-collocational-proficiency-features-on-expert-ratings-of-l2-english-learners-writing/66E56E465A7FDE3C1D506B3AF5F76253) - The impact of collocational proficiency features on expert ratings of L2 English learners’ writing -...

29. [LECTOR: LLM-Enhanced Concept-based Test-Oriented Repetition ...](https://arxiv.org/html/2508.03275v1) - Spaced repetition systems optimize learning by scheduling reviews at increasing intervals based on m...

30. [LECTOR: LLM-Enhanced Concept-based Test-Oriented ...](https://arxiv.org/abs/2508.03275) - Spaced repetition systems are fundamental to efficient learning and memory retention, but existing a...

31. [The Hidden Behavior of LLMs - Prompt Caching and Determinism](https://community.sap.com/t5/technology-blog-posts-by-sap/the-hidden-behavior-of-llms-prompt-caching-and-determinism/ba-p/14285663) - In this article, I explore three questions that emerged during my testing: why LLMs appear stateful,...

32. [Controlled LLM-Based Generation Pipeline - Emergent Mind](https://www.emergentmind.com/topics/controlled-llm-based-generation-pipeline) - A controlled LLM-based generation pipeline is a multi-stage architecture that programmatically compo...

33. [Caching Reasoning, Not Just Responses, in Agentic Systems - arXiv](https://arxiv.org/html/2601.16286v1) - Agentic AI pipelines suffer from a hidden inefficiency: they frequently reconstruct identical interm...

34. [Word Order in Chinese and Japanese | PDF | Cognitive Science](https://www.scribd.com/document/840277130/311212-%D0%A2%D0%B5%D0%BA%D1%81%D1%82-%D1%81%D1%82%D0%B0%D1%82%D1%82%D1%96-724202-1-10-20241009) - This study compares the word order in Chinese and Japanese, focusing on their basic structures (SVO ...

35. [Automatic distractor generation in multiple-choice questions: a systematic literature review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11623049/) - Multiple-choice questions (MCQs) are one of the most used assessment formats. However, creating MCQs...

