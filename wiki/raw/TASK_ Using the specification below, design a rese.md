<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# TASK: Using the specification below, design a research-based vocabulary acquisition pipeline that transitions a user from not knowing a word to both being able to recognise it and use it effectively. Ensure you work within the specified constraints.

Role: Expert Computational Linguist and Systems Architect.
Objective: Redesign a deterministic, LLM-driven vocabulary acquisition pipeline based on Paul Nation’s receptive-to-productive continuum. The pipeline must dynamically adjust its exercise ladder based on the Target Language's (TL) specific features (morphology, particles) and the word's Part of Speech (POS) and semantic class (e.g., concrete vs. abstract nouns).

1. Core Architecture \& Determinism
All generated exercises must be deterministic and cacheable. Once an exercise is generated for a word, it is stored in the database and reused unlimited times.
Format: Questions 1-9 are strictly multiple-choice (1 correct answer, 3 distractors). Question 10 is free-text translation.
Constraint: Distractors must target specific cognitive/linguistic errors, never random noise. There must be zero ambiguity about the correct answer.
No L1 Rule: Levels 1-9 must operate entirely in the Target Language (TL). L1 is only permitted in the Capstone Level 10.
2. Language Specification Files
The pipeline must query a language specification file to determine which exercise modules to activate or bypass.
English (EN) Spec:
has_morphology: true (verb conjugations, noun plurals, comparative adjectives)
has_grammatical_gender: false
has_particles: false
has_measure_words: false
Chinese (ZH) Spec:
has_morphology: false (strict isolation; verbs/nouns do not conjugate)
has_grammatical_gender: false
has_particles: true (aspectual: 了, 过, 着; structural: 的, 得, 地)
has_measure_words: true (量词: 个, 条, 张)
Japanese (JA) Spec:
has_morphology: true (agglutinative verb/adjective conjugations)
has_grammatical_gender: false
has_particles: true (case markers: は, が, を, に, で)
has_measure_words: true (counters: 本, 枚, 匹)
3. Part of Speech (POS) \& Semantic Routing Rules
Not all exercises fit all words. A concrete noun like "apple" does not have strong verb-like collocations, whereas an abstract noun like "decision" (make a decision) or a verb like "mitigate" (mitigate risk) relies entirely on collocations.
Routing Logic:
Concrete Nouns (e.g., apple, table): SKIP Collocation Gap Fill and Collocation Repair. DO NOT generate morphology for Chinese. DO test measure words/counters for Chinese and Japanese.
Abstract Nouns (e.g., decision, theory): INCLUDE Collocation exercises (e.g., verbs that pair with the noun).
Verbs \& Adjectives: INCLUDE Morphology (if language spec allows), INCLUDE Collocations (adverbs for verbs; nouns for adjectives).
4. The Dynamic Master Exercise Bank \& Generation Guardrails
When generating the assets for a new word, the LLM must follow these strict guardrails to produce the database entries. The user's specific ladder is dynamically built by selecting 7 to 10 of these modules based on the Language Spec and POS routing.
Level 1: Listening Flashcard (Phonetic)
Action: Generate 3 TL distractors that sound phonetically similar or look orthographically similar to the target word.
Rule: No semantic synonyms allowed. Same character length where possible.
Level 2: Text Flashcard (Semantic)
Action: Generate 1 TL definition (matched to CEFR level) and 3 distractor TL definitions of unrelated words in the same frequency band.
Rule: Distractors must not share core semantic meaning with the target word.
Level 3: Cloze Completion (Context)
Action: Generate a simple TL sentence with the target word blanked out. Generate 3 distractor words.
Rule: Distractors must be the same POS and grammatically valid in the blank, but contextually nonsensical. Provide the TL definition as a UI hint.
Level 4: Language-Specific Grammar Slot (Morphology / Particles)
Action (EN/JA - Morphology): Generate a sentence requiring a specific inflection/conjugation of the target word. Distractors are actual, valid morphological siblings (e.g., adapt, adapts, adapted, adapting).
Action (ZH/JA - Measure Words): Generate a sentence using the target noun. Blank out the measure word/counter. Distractors are other common measure words (e.g., target: 张; distractors: 个, 条, 本).
Action (ZH/JA - Particles): Generate a sentence using the target verb. Blank out the aspectual/case particle. Distractors are other valid particles (e.g., target: 过; distractors: 了, 着, 的).
Level 5: Collocation Gap Fill (If applicable by POS)
Action: Generate a sentence where the target word is present, but its primary natural pairing (collocate) is blanked out.
Rule: Distractors must be words that mean something similar but are unnatural in native usage (e.g., Target word: mistake. Blank: ___ a mistake. Correct: make. Distractor: do).
Level 6: Semantic Discrimination
Action: Generate 4 complete TL sentences using the target word. 1 is perfectly natural. 3 use the word in the wrong semantic context or register.
Rule: The grammar must be correct in all 4 sentences; the error must be purely semantic/contextual.
Level 7: Spot Incorrect Sentence (Syntax/Usage)
Action: Generate 3 correct TL sentences and 1 grammatically/structurally incorrect sentence involving the target word.
Rule: The error must mimic a common learner mistake (wrong preposition, transitivity error). The spelling of the target word itself must remain unchanged.
Level 8: Collocation Repair (If applicable by POS)
Action: Generate 1 sentence with a forced unnatural collocation involving the target word. Provide 4 options to replace the unnatural word.
Rule: The correct option must be the most statistically frequent native collocate.
Level 9: Jumbled Sentence (Syntactic Assembly)
Action: Generate a correct TL sentence and split it into 4-5 logical syntactic chunks (phrases, not individual words).
Rule: Generate 3 incorrect sequences. The incorrect sequences must reflect common learner word-order errors (e.g., misplacing time phrases in Chinese, or adverbial placement in English), not random mathematical shuffles.
Level 10: Capstone Dual Translation
Action: Retrieve a paragraph from the corpus where 100% of the vocabulary is known to the user (via database inverted index). Display the L1 translation. The user types the TL translation.
Rule: System evaluates the exact usage of the target word and syntax via strict LLM grading rubric.
5. Execution Directive
To the LLM generating the content: For the given target word, reference the Language Specification and the Part of Speech. Output a JSON object containing ONLY the valid exercises for that word type, strictly adhering to the distractors and correct answer guardrails defined above.

Here is the full pipeline specification. The report covers every architectural layer in depth — but to orient you through its logic before you read:

The design is built on a foundational tension that Nation's research illuminates: **recognition and production are not two ends of a single scale but separate cognitive constructs**, each requiring its own acquisition pathway. The pipeline operationalises this by enforcing a strict ascending ladder — phonetic discrimination first, free TL translation last — with every intervening level demanding a measurably more effortful retrieval operation.[^1_1][^1_2][^1_3][^1_4]

The Language Specification layer is where the architecture does its most sophisticated work. The decision to substitute a Morphology module with a Measure Word/Particle module for Mandarin is not a mere workaround for Chinese's lack of inflection — it reflects a substantive insight: **isolating languages do not simplify grammar, they redistribute it**. Where English encodes aspect through verb endings, Mandarin encodes it through post-verbal particles (了, 过, 着) whose semantic distinctions — perfective completion, experiential past, ongoing state — demand their own dedicated exercise module, not an implicit skip. Japanese doubles the burden by requiring both agglutinative morphology exercises and particle/counter training simultaneously.[^1_5][^1_6][^1_7][^1_8]

The distractor design is grounded in Cambridge Assessment English's evidence-based approach: distractors must represent **authentic learner errors** drawn from L2 corpus data, not random noise — a distinction that separates pedagogically meaningful exercises from trivia. The ELO system running beneath the ladder is validated to a 0.90 correlation with teacher-assigned CEFR levels, ensuring that word difficulty ratings and learner proficiency ratings converge on the same numerical space.[^1_9][^1_10][^1_11][^1_12][^1_13]

The report includes the full JSON database schema, the LLM generation prompt architecture, the pseudocode routing function, the CEFR-to-ELO bridge table, and the zero-ambiguity validation protocol — everything needed to implement this as a production-grade system within LinguaLoop.
<span style="display:none">[^1_14][^1_15][^1_16][^1_17][^1_18][^1_19][^1_20][^1_21][^1_22][^1_23][^1_24][^1_25][^1_26][^1_27][^1_28][^1_29][^1_30][^1_31][^1_32][^1_33][^1_34][^1_35][^1_36][^1_37][^1_38][^1_39][^1_40][^1_41][^1_42][^1_43][^1_44][^1_45][^1_46][^1_47][^1_48][^1_49][^1_50][^1_51][^1_52][^1_53][^1_54][^1_55][^1_56][^1_57][^1_58][^1_59]</span>

<div align="center">⁂</div>

[^1_1]: https://www.ukessays.com/essays/english-language/components-of-word-knowledge-adapted-from-nations-english-language-essay.php

[^1_2]: https://academic.oup.com/applij/article/41/4/481/5270836

[^1_3]: https://nottingham-repository.worktribe.com/preview/1513668/Word Knowledge - RESUBMITTED.pdf

[^1_4]: https://aclanthology.org/W19-4451.pdf

[^1_5]: https://www.fi.muni.cz/~xpelanek/publications/CAE-elo.pdf

[^1_6]: https://www.scribd.com/document/666244760/Paul-Nation-s-Theory

[^1_7]: https://media.neliti.com/media/publications/242518-how-vocabulary-is-learned-45a2c109.pdf

[^1_8]: https://dialnet.unirioja.es/descarga/articulo/7857659.pdf

[^1_9]: https://onlinelibrary.wiley.com/doi/full/10.1002/tesj.767

[^1_10]: http://www.eurosla.org/monographs/EM02/Henriksen.pdf

[^1_11]: https://ir.lib.uwo.ca/cgi/viewcontent.cgi?article=1105\&context=edupub

[^1_12]: https://dialogengine.ai/learn/elo-rating-language-learning

[^1_13]: https://studenttheses.universiteitleiden.nl/access/item:2659912/view

[^1_14]: https://www.revistas.ucr.ac.cr/index.php/riea/article/download/52212/54707/234185

[^1_15]: https://e-flt.nus.edu.sg/v10n22013/brown.pdf

[^1_16]: https://www.academia.edu/73746583/Case_in_Japanese_A_Morphological_Approach_2022_

[^1_17]: https://migaku.com/blog/chinese/chinese-measure-words

[^1_18]: https://help.langeek.co/content/vocabulary/cefr-vocabulary/

[^1_19]: https://www.wgtn.ac.nz/lals/resources/paul-nations-resources/vocabulary-lists/vocabulary-cefr-and-word-family-size/vocabulary-and-the-cefr-docx

[^1_20]: https://www.cambridgeassessment.org.uk/blogs/mcq-design-language-blog/

[^1_21]: https://www.cambridgeenglish.org/Images/526186-research-notes-72.pdf

[^1_22]: https://uwaterloo.ca/centre-for-teaching-excellence/catalogs/tip-sheets/designing-multiple-choice-questions

[^1_23]: https://studenttheses.universiteitleiden.nl/handle/1887/52141

[^1_24]: https://www.thechairmansbao.com/blog/chinese-measure-words/

[^1_25]: https://www.kanshudo.com/grammar/word_order

[^1_26]: https://gupea.ub.gu.se/handle/2077/44454

[^1_27]: https://scholarspace.manoa.hawaii.edu/bitstreams/6c1c1889-334b-4552-a825-c087e7a6d6f5/download

[^1_28]: https://www.cambridge.org/core/journals/studies-in-second-language-acquisition/article/impact-of-collocational-proficiency-features-on-expert-ratings-of-l2-english-learners-writing/66E56E465A7FDE3C1D506B3AF5F76253

[^1_29]: https://arxiv.org/html/2508.03275v1

[^1_30]: https://arxiv.org/abs/2508.03275

[^1_31]: https://community.sap.com/t5/technology-blog-posts-by-sap/the-hidden-behavior-of-llms-prompt-caching-and-determinism/ba-p/14285663

[^1_32]: https://www.emergentmind.com/topics/controlled-llm-based-generation-pipeline

[^1_33]: https://arxiv.org/html/2601.16286v1

[^1_34]: https://www.scribd.com/document/840277130/311212-Текст-статті-724202-1-10-20241009

[^1_35]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11623049/

[^1_36]: https://cunningham.acer.edu.au/inted/eaconf95/nation2.pdf

[^1_37]: https://www.youtube.com/watch?v=CLnh8Vv5RRc

[^1_38]: https://www.reading.ac.uk/elal/-/media/project/uor-main/schools-departments/elal/lswp/lswp-4/elal_lswp_vol_4_pignot_shahov.pdf

[^1_39]: https://minddory.com/blog/spaced-repetition-effectiveness

[^1_40]: https://eric.ed.gov/?id=EJ1186015

[^1_41]: https://www.sciencedirect.com/science/article/pii/S0950705125019926?dgcid=rss_sd_all

[^1_42]: https://www.lognostics.co.uk/vlibrary/meara1996c.pdf

[^1_43]: https://www.cambridge.org/core/journals/bilingualism-language-and-cognition/article/on-the-nature-of-morphological-awareness-in-japaneseenglish-bilingual-children-a-crosslinguistic-perspective/8E491720B7A92C5D1C2576C95F5B2FA4

[^1_44]: https://www.sciencedirect.com/science/article/pii/S2666920X25000165

[^1_45]: https://pmc.ncbi.nlm.nih.gov/articles/PMC9366885/

[^1_46]: https://dl.acm.org/doi/fullHtml/10.1145/3511886

[^1_47]: https://www.linkedin.com/posts/srgrace_ai-ml-llms-activity-7380972686757376000-GAXZ

[^1_48]: https://www.semanticscholar.org/paper/Automatic-distractor-generation-for-multiple-choice-Susanti-Tokunaga/730b53bcdf2bb3ccb92ffee5b84c53c16555a4cd

[^1_49]: https://www.reddit.com/r/languagelearning/comments/19a2zon/what_defines_the_cefr_level_of_a_word/

[^1_50]: https://api.macmillanenglish.com/fileadmin/user_upload/Blog_and_Resources/Blogs_and_articles/CEFR-all-scales-and-all-skills.pdf

[^1_51]: https://www.reddit.com/r/ExperiencedDevs/comments/1pos2zg/unrealistic_expectation_to_build_an_nlp_api_in_23/

[^1_52]: https://www.scribd.com/document/704636652/vocabulary-and-the-CEFR

[^1_53]: https://coerll.utexas.edu/quiz/chinese/word-order/index.php

[^1_54]: https://files.eric.ed.gov/fulltext/EJ1288698.pdf

[^1_55]: http://www.lingref.com/cpp/gasla/9/paper1630.pdf

[^1_56]: https://www.eurosla.org/monographs/EM02/EM02tot.pdf

[^1_57]: https://docs.lib.purdue.edu/cgi/viewcontent.cgi?article=1056\&context=plcc

[^1_58]: https://www.lenny.com/lesson/collocation-mastery-lesson-504850

[^1_59]: https://files.eric.ed.gov/fulltext/EJ1184808.pdf


---

# What is the minimal number of prompts we will realistically need to create the complete set of exercises for a word? Remember that we want to put that word in multiple sentences so that we can show the user it in different contexts and ensure tehy are not just memorising the shape of the sentence etc.

We will need to generate the correct sentences separately, because some may come from our corpus.

Additionally, the levels are defined below, we do not use CEFR:
Tier 1: The Toddler (Age 4-5) ~ CEFR A1
Vocabulary: 500 words. Immediate environment.
LLM Instruction: "Use only the most common basic verbs and concrete nouns. No abstract concepts. One idea per sentence."
Tier 2: The Primary Schooler (Age 8-9) ~ CEFR A2
Vocabulary: 2,000 words. Routines, basic past/future.
LLM Instruction: "Use compound sentences (and, but, because). Keep topics literal and concrete. Avoid idioms and professional jargon."
Tier 3: The Young Teen (Age 13-14) ~ CEFR B1
Vocabulary: 5,000 words. Opinions, social dynamics, media.
LLM Instruction: "Introduce common colloquialisms and mild idioms. Use conditional sentences. The language should feel entirely natural for everyday conversation, but avoid highly specialized or academic words."
Tier 4: The High Schooler (Age 16-17) ~ CEFR B2
Vocabulary: 10,000 words. Deeper arguments, abstract concepts.
LLM Instruction: "Use standard adult grammatical structures and common abstract nouns. You may use moderate domain jargon. This is fluent, everyday adult language."
(Note: This is the level most adult learners strive for—the ability to live and work comfortably in the country.)
Tier 5: The Uni Student (Age 19-21) ~ CEFR C1
Vocabulary: 15,000+ words. Debate, cultural references, complex narratives.
LLM Instruction: "Use the full breadth of standard language, including complex subordinate clauses, cultural idioms, and rich descriptive vocabulary. Characters should speak with articulate, highly fluent pacing."
Tier 6: The Educated Professional (Age 30+) ~ CEFR C2
Vocabulary: 25,000+ words. Diplomacy, niche expertise, high-register precision.
LLM Instruction: "Use high-register vocabulary, precise domain-specific jargon, and advanced rhetorical devices (e.g., passive voice for diplomacy, subtle sarcasm, circumlocution). The dialogue should reflect highly educated, specialized adult professionals communicating at the peak of their field."

no babel

To build a robust, deterministic pipeline that accommodates external corpus sentences, varied contexts, and your custom 6-Tier difficulty system, the absolute **minimal number of prompts required per word is two**.

Attempting to compress this into a single prompt will result in "constraint leakage" (where the LLM gets confused between generating correct contexts and generating intentional errors) and context window degradation.

Here is the technical architecture for the **Two-Prompt Pipeline**.

***

### The Two-Prompt Architecture

We decouple the generation of "Ground Truth" (definitions and valid contexts) from "Perturbations" (distractors and errors).

#### Pipeline Prerequisites (System/DB layer)

Before calling the LLM, your backend queries the corpus for the target word.

* **Input:** Target Word
* **Output:** Array of $X$ valid sentences from the corpus (e.g., `[Corpus_S1, Corpus_S2]`).

***

### Prompt 1: The Context \& Definition Generator

**Purpose:** Establish the ground truth. This prompt ensures the word is framed correctly for the user's specific Tier, defines it, and fills the quota of required valid sentences so the word is seen in multiple distinct contexts.

* **System Prompt Variables:**
    * `Target Word`: (e.g., "mitigate")
    * `POS`: (e.g., "verb")
    * `Tier Context`: (e.g., "Tier 4: The High Schooler. Vocabulary: 10,000 words. Use standard adult grammatical structures...")
    * `Corpus Sentences`: `[Corpus_S1, Corpus_S2]`
* **LLM Task Instructions:**

1. Write a definition for the target word strictly adhering to the syntax and vocabulary limits of the provided Tier.
2. Identify the highest-frequency primary collocate for this word (if applicable).
3. We need a total of 6 valid sentences to populate the exercise ladder. You have been provided $X$ sentences from our corpus. Generate the remaining $(6 - X)$ sentences.
4. **Context Constraint:** Each generated sentence must use the word in a completely different context, subject matter, and sentence structure (e.g., one interrogative, one negative, different subject pronouns) to prevent shape-memorization.
* **Output Schema (JSON):**

```json
{
  "definition": "...",
  "primary_collocate": "...",
  "valid_sentences": [
    "Corpus_S1",
    "Corpus_S2",
    "Generated_S3",
    "Generated_S4",
    "Generated_S5",
    "Generated_S6"
  ]
}
```


***

### Prompt 2: The Mutation \& Distractor Engine

**Purpose:** Generate the actual exercise mechanics (Levels 1–9). By feeding the LLM the locked, validated sentences from Prompt 1, you drastically reduce hallucination and ensure the distractors strictly target the base sentences.

* **System Prompt Variables:**
    * `Target Word`, `POS`, `Language Spec`
    * `Definition` (from Prompt 1)
    * `Primary Collocate` (from Prompt 1)
    * `Valid Sentences` (Array of 6 sentences from Prompt 1)
* **LLM Task Instructions:**
Generate the distractors and deliberate errors for the exercise ladder using the provided `Valid Sentences` array as your base material.
    * For **Level 3 (Cloze)**: Use `Valid_Sentence[0]`. Generate 3 grammatically valid but contextually nonsensical distractor words.
    * For **Level 4 (Morphology/Particle)**: Use `Valid_Sentence[1]`. Generate 3 morphologically or typologically accurate distractors.
    * For **Level 5 (Collocation Gap)**: Use `Valid_Sentence[2]`. Provide 3 unnatural distractors for the `primary_collocate`.
    * For **Level 6 (Semantic Discrimination)**: Generate 3 *new* sentences where the target word is grammatically correct but semantically anomalous. (The 1 correct option will be `Valid_Sentence[3]`).
    * For **Level 7 (Syntax Spot)**: Generate 1 *new* syntactically incorrect sentence mimicking a common L2 error. (The 3 correct options will be `Valid_Sentence[4]` + 2 others).
    * For **Level 8 (Colloc Repair)**: Generate 1 *new* sentence using an unnatural collocate.
    * For **Level 9 (Jumble)**: Chunk `Valid_Sentence[5]` into logical phrases and generate 3 incorrect sequence arrays.
* **Output Schema (JSON):**

```json
{
  "level_1_phonetic": ["dist1", "dist2", "dist3"],
  "level_2_semantic": ["def_dist1", "def_dist2", "def_dist3"],
  "level_3_cloze": { "sentence_index": 0, "distractors": [...] },
  "level_4_grammar": { "sentence_index": 1, "distractors": [...] },
  "level_5_colloc": { "sentence_index": 2, "distractors": [...] },
  "level_6_semantic_errs": ["err_sentence1", "err_sentence2", "err_sentence3"],
  "level_7_syntax_err": "syntax_err_sentence",
  "level_8_colloc_repair": { "bad_sentence": "...", "distractors": [...] },
  "level_9_jumble": { "sentence_index": 5, "correct_chunks": [...], "bad_sequences": [...] }
}
```


### Why this is the optimal engineering approach:

1. **Separation of Concerns:** Prompt 1 only worries about generating highly accurate, Tier-appropriate context. Prompt 2 only worries about linguistic edge-cases and distractor logic.
2. **Corpus Integration:** Passing corpus sentences into Prompt 1 allows the LLM to "fill the gap" contextually, ensuring it doesn't generate a sentence conceptually identical to one you already have.
3. **Cost \& Speed:** Two prompts run sequentially are highly cacheable. If a user flags a bad distractor in production, you only need to re-run Prompt 2 (the Mutation Engine), saving the tokens and compute required to regenerate the definitions and base contexts.

---

# we need to design the prompt to work in all languages without mixing them. e.g. the json output keys should be numerical indices, with descriptions of what they will be in the prompt.

Additionally, for all output in the second prompt, i think that we should provide reasoning in that language as to why each option is correct/incorrect. We should be able to separate it by answer.

Here is the revised two-prompt architecture. It enforces strict language separation by using numerical and structural keys (parsed by your backend) while demanding that all *values*—including the newly added per-option reasoning—are generated exclusively in the Target Language (TL).

### Prompt 1: Ground Truth \& Context Generator

**System Prompt:**

```text
Role: Expert Computational Linguist.
Task: Generate base linguistic assets for a vocabulary acquisition pipeline.
Target Language (TL): {target_language}
Target Word: {target_word}
Part of Speech (POS): {pos}
Tier Level: {tier_description} (e.g., "Tier 4: The High Schooler. Vocabulary: 10,000 words. Use standard adult grammatical structures...")
Provided Corpus Sentences: {corpus_sentences_array}

Instructions:
1. All generated text values MUST be strictly in the Target Language. Do not mix languages.
2. Generate a definition suitable for the specified Tier Level.
3. Identify the highest-frequency primary collocate for this word (if applicable for the POS).
4. Output exactly 6 valid sentences. Include the {corpus_sentences_array}. Generate the remainder to reach exactly 6.
5. Each sentence must use the target word in a completely different context, subject matter, and syntactic structure.

Output strictly in JSON format using the numerical keys defined below:
"1": The TL definition.
"2": The primary TL collocate (or null if not applicable).
"3": An array of exactly 6 TL sentences.
```

**Output JSON Schema (Prompt 1):**

```json
{
  "1": "減少或減輕（危害、痛苦等）的程度",
  "2": "風險",
  "3": [
    "Corpus_Sentence_1",
    "Corpus_Sentence_2",
    "Generated_Sentence_3",
    "Generated_Sentence_4",
    "Generated_Sentence_5",
    "Generated_Sentence_6"
  ]
}
```


***

### Prompt 2: Mutation, Distractor \& Reasoning Engine

**System Prompt:**

```text
Role: Expert Computational Linguist.
Task: Generate vocabulary exercise distractors and pedagogical reasoning.
Target Language (TL): {target_language}
Target Word: {target_word}
Tier Level: {tier_description}
Language Spec: {language_spec_json}
Active Levels: {active_levels_array} (e.g., [1, 2, 3, 4, 6, 7, 9])
Base Assets: {prompt_1_output_json}

Instructions:
1. ALL generated content (sentences, distractors, and reasoning) MUST be written entirely in the Target Language. Do not use English in the JSON values.
2. For each number in the Active Levels array, generate the corresponding exercise module.
3. Use the sentences from Base Assets "3" as the foundation for Levels 3, 4, 5, and 9.
4. For EVERY option in EVERY level, provide a concise explanation (in the TL) explaining why it is correct or incorrect. The reasoning must be pedagogical and appropriate for the Tier Level.
   - Incorrect reasoning should explain *why* a learner might make this mistake (e.g., wrong part of speech, wrong semantic context, unnatural collocation).

Exercise Level Definitions (Key maps to Level number):
"1": Phonetic/Orthographic Flashcard (3 similar-looking/sounding distractors).
"2": Semantic Flashcard (3 definitions of unrelated words in the same Tier).
"3": Cloze Completion (Blank out target word in Base Sentence index 0. 3 grammatically valid but contextually wrong distractors).
"4": Grammar Slot (Apply Language Spec rules to Base Sentence index 1).
"5": Collocation Gap (Blank out collocate in Base Sentence index 2. 3 unnatural near-synonyms).
"6": Semantic Discrimination (1 correct sentence, 3 semantically anomalous sentences using the target word).
"7": Syntax Spot (3 correct sentences, 1 with a common L2 structural error).
"8": Collocation Repair (1 sentence with a forced bad collocate, 4 replacement options).
"9": Jumbled Sentence (Chunk Base Sentence index 5. 1 correct sequence, 3 sequences with common L2 word-order errors).

Output strictly in JSON format. The top-level keys must be the numerical indices from Active Levels.
```

**Output JSON Schema (Prompt 2):**
*(Example showing output for a Spanish word "mitigar" at Level 3 and 7 to illustrate the structure and TL reasoning)*

```json
{
  "3": {
    "context": "Los ingenieros construyeron un muro para ___ el impacto de las inundaciones.",
    "options": [
      {
        "id": 1,
        "text": "mitigar",
        "is_correct": true,
        "reasoning": "Correcto. 'Mitigar' significa reducir la severidad de un daño, lo cual tiene sentido en el contexto de un muro contra inundaciones."
      },
      {
        "id": 2,
        "text": "celebrar",
        "is_correct": false,
        "reasoning": "Incorrecto. Gramaticalmente es un verbo válido, pero no tiene sentido celebrar un desastre natural."
      },
      {
        "id": 3,
        "text": "comprar",
        "is_correct": false,
        "reasoning": "Incorrecto. El impacto de una inundación no es un objeto físico que se pueda comprar."
      },
      {
        "id": 4,
        "text": "traducir",
        "is_correct": false,
        "reasoning": "Incorrecto. Las inundaciones no son un idioma o texto que requiera traducción."
      }
    ]
  },
  "7": {
    "context": "Selecciona la oración con el error gramatical o estructural.",
    "options": [
      {
        "id": 1,
        "text": "El gobierno intentó de mitigar los daños rápidamente.",
        "is_correct": true, 
        "reasoning": "Este es el error. El verbo 'intentar' va seguido directamente por el infinitivo, no requiere la preposición 'de'. Es un error común de interferencia."
      },
      {
        "id": 2,
        "text": "El gobierno intentó mitigar los daños rápidamente.",
        "is_correct": false,
        "reasoning": "Esta oración es estructuralmente y gramaticalmente perfecta."
      },
      {
        "id": 3,
        "text": "Se tomaron medidas para mitigar el dolor del paciente.",
        "is_correct": false,
        "reasoning": "Esta oración es estructuralmente y gramaticalmente perfecta."
      },
      {
        "id": 4,
        "text": "Las nuevas leyes mitigan el riesgo financiero.",
        "is_correct": false,
        "reasoning": "Esta oración es estructuralmente y gramaticalmente perfecta."
      }
    ]
  }
}
```


### Engineering Advantages of this Schema:

1. **Language Safety:** By strictly mapping output to generic structural keys (`context`, `options`, `id`, `text`, `is_correct`, `reasoning`), your frontend code remains 100% agnostic to the language being learned.
2. **Instant Feedback:** Because the reasoning is generated upfront and cached alongside the exercise, you don't need to make an LLM call when the user clicks an answer. You simply render `option.reasoning` in the UI immediately.
3. **Dynamic Routing:** Prompt 2 only generates keys for the numbers passed into `Active Levels`. If a word skips Level 5 (Collocations) because it's a concrete noun, key `"5"` simply won't exist in the JSON, matching your routing logic perfectly.

---

# Should we have it generate all definitions in the one prompt? Also, I think it makes sense that we simply ask it for the number of sentences we want, not ask a riddle.

Same for prompt 2 - we want to minimise the amount of thinking. As a result, we will want to include/exclude exercises deterministically and ensure that those exercises that we do not need are not included in the prompt.

Moreover, the cloze completion exercise should just be asking it to generate x distractors for the given sentence. We know what the target word is - we do not want it blanking it out, we will do that. In fact, for all blanking out exercises, we want the full sentence, with the target word and distractors as items - we will blank it out on the frontend.

We will not include jumbled sentence because we will use libraries like jieba to segment the sentence.

Also, I'm not sure how many correct sentences we will need to generate in prompt 2 - ideally we use the ones we generated already.

Ask me any further clarifying questions, and then we will redesign the prompts (we can use more than two prompts)

These are excellent architectural refinements. Removing the "math riddle", offloading the blanking and chunking to the frontend, and dynamically building the prompt to strictly exclude skipped levels will drastically reduce LLM hallucination and constraint leakage.

Before I write the exact JSON schemas and prompt templates for this new pipeline, I have 5 clarifying questions to ensure the data structure perfectly matches your backend needs:

### 1. Definition Distractors (Level 2)

If we move the generation of the 3 distractor definitions to Prompt 1, should the LLM also provide the "hidden" target words those distractor definitions belong to?
*Example: If target is "mitigate", distractor definition is "to express satisfaction". Should the JSON just return the definition string, or an object like `{"word": "celebrate", "definition": "to express satisfaction"}` so your database has a record of what it actually defined?*

### 2. Frontend Blanking \& Exact Substrings

If the frontend is handling the blanking for Levels 3, 4, and 5, it needs to know exactly which characters to hide. However, in morphologically rich languages, the word in the sentence might be inflected (e.g., Target: *adapt*, Sentence: "She *adapted* quickly").
*Do you need the LLM to explicitly return the exact substring used in the sentence (e.g., `"target_substring": "adapted"`) so your frontend can do a simple string replace, or will your backend use a lemmatizer to find it?*

### 3. Sentence Quota and Reusability

Since we are removing the math riddle, your backend will calculate exactly how many new sentences are needed. To reuse these effectively across the exercises without repetition fatigue, how many **total distinct correct sentences** do you want to power one word's entire exercise ladder?
*I recommend a total of 4 or 5 correct sentences. E.g., Sentence 1 for Cloze, Sentence 2 for Grammar Slot, Sentence 3 for Collocation, and we recycle Sentences 1, 2, and 4 for the Syntax/Semantic correct options. Does 5 total sentences sound correct?*

### 4. Level 8 (Collocation Repair) Mechanics

Level 8 requires presenting the user with a sentence containing a *forced unnatural* collocate, which they must fix.
*Should the LLM in Prompt 2 generate this unnatural sentence from scratch, OR should it take the correct Collocation sentence generated in Prompt 1 and just swap the collocate for an unnatural one?*

### 5. Prompt Splitting (2 vs 3 Prompts)

To truly minimize "thinking," we could split this into a **3-Prompt Pipeline**:

* **Prompt 1 (Ground Truth):** Definitions, Collocates, and $N$ Correct Sentences.
* **Prompt 2 (Lexical/Semantic Exercises):** Distractors for Levels 1, 3, 5, and 6 (using Sentences 1, 2, 3).
* **Prompt 3 (Grammar/Structural Exercises):** Distractors for Levels 4, 7, and 8 (using Sentences 4, 5).
*Would you prefer to keep it to 2 prompts for cost/latency, or go to 3 prompts for maximum determinism and smaller context windows?* (Since this is a background caching job, latency usually isn't an issue).

Let me know your thoughts on these, and I will write the precise, deterministic prompt templates and JSON schemas!

---

# 1. I feel like the definition distractors could just be grabbed from other words in our database randomly. It is a level 2 exercise after all.

2. Yes, return the target substring.
3. Lets have 6 total sentences because we will be able to use multiple in some exercises.
4. Take the correct collocation sentences genereated in prompt 1 and just swap the collocate for an unnatural one (or provide it as "unnatural_collocate". maybe give us multiple)
5. 3 prompts sounds good

Here is the complete **3-Prompt Architecture**. It is highly deterministic, removes all math logic from the LLM, offloads blanking/chunking to the frontend, and ensures the LLM focuses purely on linguistic accuracy and pedagogical reasoning.

To achieve your goal of minimizing "thinking," your backend will dynamically assemble Prompts 2 and 3. If a word skips Level 5 and 8 (e.g., a concrete noun), your backend simply omits those instruction blocks from the prompt string.

***

### Prompt 1: The Ground Truth Generator

**Purpose:** Establish the definition, primary collocate, and exactly 6 perfect reference sentences. The frontend uses the `target_substring` to perform exact string-replacement for blanking.

**System Prompt Template:**

```text
Role: Expert Computational Linguist.
Task: Generate base linguistic assets for a vocabulary exercise pipeline.
Target Language (TL): {target_language}
Target Word: {target_word}
Part of Speech (POS): {pos}
Tier Level: {tier_description}

Instructions:
1. All generated text MUST be strictly in the Target Language. Do not mix languages.
2. Generate a definition suitable for the specified Tier Level.
3. Identify the highest-frequency primary collocate for this word (if applicable for the POS. If none, return null).
4. We require exactly 6 correct sentences using the target word. You have been provided {X} sentences from our corpus. Generate exactly {6 - X} additional sentences to reach a total of 6.
5. Each sentence must use the word in a completely different context and syntactic structure.
6. For every sentence, provide the `target_substring`—the exact characters of the target word as it is inflected or written in that specific sentence.

Corpus Sentences Provided:
{corpus_sentences_json}

Output strictly in this JSON format:
{
  "1": "TL Definition",
  "2": "Primary TL Collocate (or null)",
  "3": [
    { "text": "Sentence 1...", "target_substring": "..." },
    { "text": "Sentence 2...", "target_substring": "..." },
    // ... exactly 6 items
  ]
}
```


***

### Prompt 2: Lexical \& Semantic Exercises (Levels 1, 3, 5, 6)

**Purpose:** Generate distractors and reasoning for meaning-based exercises using Sentences 1–3 from Prompt 1.
*(Backend Logic: Only inject instructions for Level 5 if it is active for this POS).*

**System Prompt Template:**

```text
Role: Expert Computational Linguist.
Task: Generate vocabulary exercise distractors and pedagogical reasoning.
Target Language (TL): {target_language}
Target Word: {target_word}
Tier Level: {tier_description}

Base Assets:
- Sentence 1: "{sentence_1_text}" (Target: "{sentence_1_substring}")
- Sentence 2: "{sentence_2_text}" (Target: "{sentence_2_substring}", Collocate: "{collocate}")
- Sentence 3: "{sentence_3_text}" (Target: "{sentence_3_substring}")

Instructions:
1. ALL generated content and pedagogical reasoning MUST be written entirely in the Target Language.
2. For each option, provide `reasoning` explaining why it is correct or incorrect for a learner.

Exercise Modules to Generate:
"1": Phonetic/Orthographic Flashcard. Generate 3 distractors that sound or look similar to the target word but have no semantic overlap. (No base sentence needed).
"3": Cloze Completion. Using Sentence 1, generate 3 distractor words. They must be the same POS and grammatically valid in the sentence, but contextually nonsensical.
[INJECT IF ACTIVE] "5": Collocation GapFill. Using Sentence 2, the correct collocate is "{collocate}". Generate 3 distractor collocates that are near-synonyms but unnatural in native usage.
"6": Semantic Discrimination. Sentence 3 is the correct option. Generate 3 NEW sentences where the target word is used correctly grammatically, but incorrectly semantically or pragmatically.

Output strictly in JSON format using the numerical keys "1", "3", "5", "6".
```

**JSON Output Schema (Prompt 2):**

```json
{
  "1": {
    "options": [
      { "text": "target_word", "is_correct": true, "reasoning": "..." },
      { "text": "distractor_1", "is_correct": false, "reasoning": "..." },
      { "text": "distractor_2", "is_correct": false, "reasoning": "..." },
      { "text": "distractor_3", "is_correct": false, "reasoning": "..." }
    ]
  },
  "3": {
    "options": [
      { "text": "target_substring", "is_correct": true, "reasoning": "..." },
      { "text": "distractor_1", "is_correct": false, "reasoning": "..." }
      // ... 4 options total
    ]
  },
  "5": {
    "options": [
      { "text": "collocate", "is_correct": true, "reasoning": "..." },
      { "text": "unnatural_synonym_1", "is_correct": false, "reasoning": "..." }
      // ... 4 options total
    ]
  },
  "6": {
    "options": [
      { "text": "Sentence 3 (Correct)", "is_correct": true, "reasoning": "..." },
      { "text": "New Sentence (Semantic Error 1)", "is_correct": false, "reasoning": "..." }
      // ... 4 options total
    ]
  }
}
```


***

### Prompt 3: Grammar \& Structural Exercises (Levels 4, 7, 8)

**Purpose:** Generate distractors and reasoning for structural exercises using Sentences 4–6 from Prompt 1.
*(Backend Logic: Only inject instructions for Levels 4 and 8 if active. Inject the correct rule for Level 4 based on the Language Spec).*

**System Prompt Template:**

```text
Role: Expert Computational Linguist.
Task: Generate vocabulary exercise distractors and pedagogical reasoning focusing on syntax and grammar.
Target Language (TL): {target_language}
Target Word: {target_word}
Tier Level: {tier_description}

Base Assets:
- Sentence 4: "{sentence_4_text}" (Target: "{sentence_4_substring}")
- Sentence 5: "{sentence_5_text}" (Target: "{sentence_5_substring}")
- Sentence 6: "{sentence_6_text}" (Target: "{sentence_6_substring}", Collocate: "{collocate}")

Instructions:
1. ALL generated content and pedagogical reasoning MUST be written entirely in the Target Language.
2. For each option, provide `reasoning` explaining why it is correct or incorrect.

Exercise Modules to Generate:
[INJECT IF ACTIVE] "4": Grammar Slot. Using Sentence 4, the correct answer is "{sentence_4_substring}". Generate 3 distractors that are [INJECT LANG SPEC RULE: e.g., "valid morphological siblings of the target word" OR "other valid Chinese measure words"]. 
"7": Syntax Spot. Generate 1 NEW sentence containing a common L2 structural/grammatical error involving the target word (e.g., wrong preposition, bad word order). The target word's spelling must not change. Provide the correct version as well.
[INJECT IF ACTIVE] "8": Collocation Repair. Using Sentence 6, generate 3 unnatural/incorrect collocates that learners frequently mistakenly use instead of "{collocate}". 

Output strictly in JSON format using the numerical keys "4", "7", "8".
```

**JSON Output Schema (Prompt 3):**

```json
{
  "4": {
    "options": [
      { "text": "sentence_4_substring", "is_correct": true, "reasoning": "..." },
      { "text": "distractor_form_1", "is_correct": false, "reasoning": "..." },
      { "text": "distractor_form_2", "is_correct": false, "reasoning": "..." },
      { "text": "distractor_form_3", "is_correct": false, "reasoning": "..." }
    ]
  },
  "7": {
    "error_sentence": "New Sentence with Syntax Error...",
    "error_reasoning": "Explanation of why this grammar/structure is wrong...",
    "corrected_sentence": "The grammatically correct version of the error sentence..."
  },
  "8": {
    "options": [
      { "text": "collocate", "is_correct": true, "reasoning": "..." },
      { "text": "unnatural_collocate_1", "is_correct": false, "reasoning": "..." },
      { "text": "unnatural_collocate_2", "is_correct": false, "reasoning": "..." },
      { "text": "unnatural_collocate_3", "is_correct": false, "reasoning": "..." }
    ]
  }
}
```


### System Architecture Notes for the Backend:

* **Level 2 (Semantic Flashcard):** Handled purely by your DB. You fetch the definition from Prompt 1, and query your DB for 3 random definitions from other words in the same Tier.
* **Level 7 (Syntax Spot) Assembly:** Prompt 3 only generates the *one* error sentence and its correction. To build the 4-option multiple-choice question in the frontend, your backend pulls the error sentence from Prompt 3, and pairs it with Sentence 5, the Corrected Sentence from Prompt 3, and perhaps Sentence 1 from the DB to make the 4 options.
* **Level 8 (Collocation Repair) Assembly:** The frontend displays Sentence 6, but uses string replacement to swap the true `{collocate}` with `unnatural_collocate_1` in the display text. The 4 MCQ options are the true collocate and the 3 unnatural ones.
* **Level 9 (Jumble):** Handled purely by your backend. You take Sentence 6, pass it through `jieba` (for Chinese) or a standard tokenizer, and shuffle the array on the frontend.

---

# \# Editing Notes

1. Remember, we need to only use indices for the output json schema keys
2. I think we need to define what exactly a distractor should be - should it be close semantically or not? Should it be a contextual error or grammatical?

Here is the refined 3-Prompt Architecture.

I have strictly mapped **all JSON keys to numerical indices** to ensure zero language leakage and maximum programmatic predictability. I have also heavily fortified the **distractor definitions** in the prompt instructions so the LLM knows exactly what axis (semantic, grammatical, or contextual) it is mutating for each specific exercise.

### Universal JSON Key Mapping (For your Backend to Parse)

* **Top-Level Keys:** Always represent the Level ID (e.g., `"1"`, `"3"`, `"5"`).
* **Array Items (Options):**
    * `"1"`: The text (the sentence, the distractor word, or the substring).
    * `"2"`: Boolean (`true` if correct, `false` if distractor/error).
    * `"3"`: Pedagogical reasoning in the Target Language (TL).

***

### Prompt 1: The Ground Truth Generator

**System Prompt:**

```text
Role: Expert Computational Linguist.
Task: Generate base linguistic assets for a vocabulary exercise pipeline.
Target Language (TL): {target_language}
Target Word: {target_word}
Part of Speech (POS): {pos}
Tier Level: {tier_description}

Instructions:
1. All generated text values MUST be strictly in the Target Language. Do not mix languages.
2. We require exactly 6 correct sentences. You have been provided {X} sentences from our corpus. Generate {6 - X} additional sentences to reach exactly 6.
3. Each sentence must use the word in a completely different context and syntactic structure.

Output strictly in JSON format using ONLY the following numerical keys:
"1": The TL definition suitable for the Tier Level.
"2": The highest-frequency primary TL collocate (or null if none).
"3": An array of exactly 6 sentence objects. 
     Inside each sentence object:
     "1": The full sentence text.
     "2": The exact target word substring as it appears inflected in the sentence.

Corpus Sentences Provided:
{corpus_sentences_json}
```

**Output Schema Example:**

```json
{
  "1": "減少或減輕（危害、痛苦等）的程度",
  "2": "風險",
  "3": [
    { "1": "Corpus_Sentence_1...", "2": "substring" },
    { "1": "Corpus_Sentence_2...", "2": "substring" },
    { "1": "Generated_Sentence_3...", "2": "substring" },
    { "1": "Generated_Sentence_4...", "2": "substring" },
    { "1": "Generated_Sentence_5...", "2": "substring" },
    { "1": "Generated_Sentence_6...", "2": "substring" }
  ]
}
```


***

### Prompt 2: Lexical \& Semantic Exercises (Levels 1, 3, 5, 6)

**System Prompt:**

```text
Role: Expert Computational Linguist.
Task: Generate vocabulary exercise distractors and pedagogical reasoning.
Target Language (TL): {target_language}
Target Word: {target_word}
Tier Level: {tier_description}

Base Assets:
- Sentence 1: "{sentence_1_text}" (Target: "{sentence_1_substring}")
- Sentence 2: "{sentence_2_text}" (Target: "{sentence_2_substring}", Collocate: "{collocate}")
- Sentence 3: "{sentence_3_text}" (Target: "{sentence_3_substring}")

Instructions:
1. ALL text values and pedagogical reasoning MUST be in the Target Language.
2. Output ONLY numerical keys. The top-level keys are the Exercise Levels.
3. For each Level's array of options, use these keys:
   "1": The option text.
   "2": Boolean (true if correct, false if distractor).
   "3": Reasoning explaining why it is correct or incorrect.

Distractor Rules per Exercise Level:
"1" (Phonetic Flashcard): 1 correct target word. 3 distractors must sound or look highly similar to the target word, but have ZERO semantic overlap. Do not use synonyms.
"3" (Cloze Completion - uses Sentence 1): 1 correct target substring. 3 distractors must be the EXACT SAME Part of Speech and GRAMMATICALLY VALID in the blank, but CONTEXTUALLY NONSENSICAL or absurd in meaning.
[INJECT IF ACTIVE] "5" (Collocation GapFill - uses Sentence 2): 1 correct "{collocate}". 3 distractors must be NEAR-SYNONYMS to the collocate (semantically close) but STATISTICALLY UNNATURAL or non-native when paired with the target word.
"6" (Semantic Discrimination): 1 correct sentence (Sentence 3). Generate 3 NEW distractor sentences where the target word is GRAMMATICALLY CORRECT, but violates SEMANTIC/PRAGMATIC constraints (e.g., using an abstract verb on a physical object).

Output JSON Format:
{
  "1": [ { "1": "text", "2": true/false, "3": "reasoning" }, ... ],
  "3": [ { "1": "text", "2": true/false, "3": "reasoning" }, ... ],
  "5": [ { "1": "text", "2": true/false, "3": "reasoning" }, ... ],
  "6": [ { "1": "text", "2": true/false, "3": "reasoning" }, ... ]
}
```


***

### Prompt 3: Grammar \& Structural Exercises (Levels 4, 7, 8)

**System Prompt:**

```text
Role: Expert Computational Linguist.
Task: Generate vocabulary exercise distractors and pedagogical reasoning focusing on syntax and grammar.
Target Language (TL): {target_language}
Target Word: {target_word}
Tier Level: {tier_description}

Base Assets:
- Sentence 4: "{sentence_4_text}" (Target: "{sentence_4_substring}")
- Sentence 5: "{sentence_5_text}" (Target: "{sentence_5_substring}", Collocate: "{collocate}")

Instructions:
1. ALL text values and pedagogical reasoning MUST be in the Target Language.
2. Output ONLY numerical keys. 

Distractor Rules per Exercise Level:
[INJECT IF ACTIVE] "4" (Grammar Slot - uses Sentence 4): 
   - 1 correct "{sentence_4_substring}". 
   - 3 distractors must be [INJECT LANG SPEC RULE: e.g., "valid morphological conjugations of the target word" OR "other valid measure words"]. They must be real words/forms, but GRAMMATICALLY INCORRECT for this specific sentence context.
   - Output as an array of 4 option objects: { "1": "text", "2": true/false, "3": "reasoning" }.

"7" (Syntax Spot): 
   - Generate 1 NEW sentence containing a COMMON L2 STRUCTURAL ERROR involving the target word (e.g., wrong preposition, transitivity error, bad word order). The target word's spelling must remain correct. 
   - Output as a single object:
     "1": The error sentence.
     "2": The corrected, grammatically perfect version of the sentence.
     "3": The reasoning explaining the grammatical rule that was broken.

[INJECT IF ACTIVE] "8" (Collocation Repair - uses Sentence 5): 
   - 1 correct "{collocate}". 
   - 3 distractors must be UNNATURAL COLLOCATES that L2 learners frequently and mistakenly use via L1-transfer (e.g., using "do" instead of "make").
   - Output as an array of 4 option objects: { "1": "text", "2": true/false, "3": "reasoning" }.

Output JSON Format:
{
  "4": [ { "1": "text", "2": true/false, "3": "reasoning" }, ... ],
  "7": { "1": "error_sentence", "2": "corrected_sentence", "3": "reasoning" },
  "8": [ { "1": "text", "2": true/false, "3": "reasoning" }, ... ]
}
```


### Engineering Summary for Implementation:

* **Data Serialization:** Because the JSON keys are universally strictly numbered (`"1"`, `"2"`, `"3"`), your backend models/structs can parse them via deterministic indexing without ever worrying about the LLM hallucinating translated keys (e.g., accidentally outputting `"opciones"` instead of `"options"`).
* **Clear Distractor Boundaries:** The LLM is explicitly told *how* the distractor should fail:
    * Level 3: Fails on Context.
    * Level 4: Fails on Grammar.
    * Level 5 \& 8: Fails on Collocational Frequency.
    * Level 6: Fails on Semantic Rules.
* **Level 7 Assembly:** Your backend takes `"1"` (the error sentence) from Level 7 and combines it with 3 correct sentences (e.g., Sentence 6, Sentence 1, and the corrected sentence `"2"` from Level 7) to build the 4-choice frontend view.

---

# estimate how many tokens we might use for one word using all three prompts. What cost could we be looking at per word? Check openrouter prices for anthropic, alibaba, deepseek, and google model prices

Based on the 3-prompt architecture, we can estimate the token usage per word by breaking down the inputs (system prompt instructions, JSON schemas, corpus sentences) and outputs (generated sentences, definitions, distractors, and TL pedagogical reasoning) across all three calls.

### Estimated Token Usage Per Word

| Prompt | Estimated Input Tokens | Estimated Output Tokens | Notes |
| :-- | :-- | :-- | :-- |
| **Prompt 1** (Ground Truth) | 400 | 300 | System rules + ~2-4 corpus sentences in. Outputs 6 short sentences + definition. |
| **Prompt 2** (Semantic) | 600 | 400 | Injects Sentences 1-3. Outputs 4 sets of MCQ options + reasoning. |
| **Prompt 3** (Structural) | 500 | 300 | Injects Sentences 4-6. Outputs 2-3 sets of MCQ options + reasoning. |
| **Total (Average)** | **~1,500 Tokens** | **~1,000 Tokens** | Assuming a word that triggers all exercise levels. |

*Note: Morphologically dense languages (like Japanese) or isolating languages with complex character sets (like Chinese) may use slightly different tokenization patterns, but these estimates provide a solid baseline for budgeting.*

### Estimated Cost via OpenRouter (April 2026 Prices)

Using current OpenRouter API pricing for the requested models, here is the cost breakdown to generate the complete 10-level exercise ladder for one word, as well as the projected cost to build a database of 10,000 words.


| Model | Input Price (per 1M) | Output Price (per 1M) | Est. Cost per Word | Cost for 10,000 Words |
| :-- | :-- | :-- | :-- | :-- |
| **Google Gemini 1.5 Flash** | \$0.075 | \$0.30 | **\$0.00041** | **\$4.12** |
| **DeepSeek V3** | \$0.32 | \$0.89 | **\$0.00137** | **\$13.70** |
| **Google Gemini 2.5 Flash** | \$0.30 | \$2.50 | **\$0.00295** | **\$29.50** |
| **DeepSeek R1** | \$0.70 | \$2.50 | **\$0.00355** | **\$35.50** |
| **Claude 3.5 Haiku** | \$0.80 | \$4.00 | **\$0.00520** | **\$52.00** |
| **Google Gemini 1.5 Pro** | \$1.25 | \$5.00 | **\$0.00688** | **\$68.75** |
| **Claude 3.5 Sonnet** | \$3.00 | \$15.00 | **\$0.01950** | **\$195.00** |

### Strategic Recommendation

For this specific architecture, **DeepSeek V3** or **Claude 3.5 Haiku** represent the optimal balance of intelligence and cost.

Because we have heavily constrained the LLM—removing mathematical riddles, strictly formatting the JSON with numerical indices, and isolating the generation of ground-truth context from the generation of linguistic errors—you do not necessarily need the expensive reasoning capabilities of Sonnet or DeepSeek R1. The task is highly deterministic and heavily reliant on clear structural instructions, which models in the V3/Haiku tier handle exceptionally well.
<span style="display:none">[^7_1][^7_10][^7_11][^7_12][^7_13][^7_14][^7_15][^7_16][^7_17][^7_18][^7_19][^7_2][^7_20][^7_21][^7_22][^7_23][^7_24][^7_25][^7_26][^7_27][^7_3][^7_4][^7_5][^7_6][^7_7][^7_8][^7_9]</span>

<div align="center">⁂</div>

[^7_1]: https://openrouter.ai/anthropic/claude-3.5-haiku

[^7_2]: https://openrouter.ai/anthropic/claude-3-haiku

[^7_3]: https://platform.claude.com/docs/en/about-claude/pricing

[^7_4]: https://www.juheapi.com/blog/claude-pricing-explained-2025-sonnet-opus-haiku-costs

[^7_5]: https://costgoat.com/pricing/claude-api

[^7_6]: https://openrouter.ai/deepseek/deepseek-r1

[^7_7]: https://okrouter.com/models/gemini-1.5-flash

[^7_8]: https://costgoat.com/pricing/openrouter

[^7_9]: https://openrouter.ai/deepseek/deepseek-chat

[^7_10]: https://ai.google.dev/gemini-api/docs/pricing

[^7_11]: https://openrouter.ai/google/gemini-pro-1.5

[^7_12]: https://calculator.holori.com/llm/google/openrouter%2Fgoogle%2Fgemini-pro-1.5

[^7_13]: https://openrouter.ai/compare/google/gemini-pro-1.5

[^7_14]: https://openrouter.ai/pricing

[^7_15]: https://openrouter.ai/google/gemini-2.5-pro-preview-03-25

[^7_16]: https://www.juheapi.com/blog/claude-api-pricing-comparison-anthropic-vs-openrouter-vs-wisdom-gate

[^7_17]: https://www.typingmind.com/guide/openrouter/claude-3.5-sonnet

[^7_18]: https://openrouter.ai/google/gemini-3.1-pro-preview

[^7_19]: https://openrouter.ai/anthropic/claude-3.5-sonnet

[^7_20]: https://openrouter.ai/gemini-pro-1.5

[^7_21]: https://www.reddit.com/r/ChatGPTCoding/comments/1jrp1tj/a_simple_guide_to_setting_up_gemini_25_pro_free/

[^7_22]: https://openrouter.ai/google/gemini-2.5-flash

[^7_23]: https://openrouter.ai/gemini-flash-1.5

[^7_24]: https://openrouter.ai/google/gemini-flash-1.5

[^7_25]: https://portkey.ai/models/openrouter/google%2Fgemini-2.5-flash

[^7_26]: https://openrouter.wk-xj.com/google/gemini-flash-1.5

[^7_27]: https://openrouter.proxyus.insight-aigc.com/deepseek/deepseek-chat-v3


---

# do it for qwen models as well. Which level of reasoning do you think that we will need to make truly effective pipeline? Maybe we can use flash for generating correct sentences, but pro for doing exercise generation?

Here is the cost analysis with the Alibaba Qwen models included, along with an evaluation of the "Hybrid Pipeline" approach you suggested.

### OpenRouter Cost Analysis (Including Qwen \& Hybrid Pipelines)

| Model | Input Price (1M) | Output Price (1M) | Est. Cost per Word | Cost for 10,000 Words |
| :-- | :-- | :-- | :-- | :-- |
| **Gemini 1.5 Flash** | \$0.075 | \$0.30 | **\$0.00041** | **\$4.12** |
| **Qwen 2.5 72B Instruct** | \$0.12 | \$0.39 | **\$0.00057** | **\$5.70** |
| **QwQ 32B** (Reasoning) | \$0.15 | \$0.58 | **\$0.00080** | **\$8.05** |
| **DeepSeek V3** | \$0.32 | \$0.89 | **\$0.00137** | **\$13.70** |
| **Qwen-Plus** | \$0.40 | \$1.20 | **\$0.00180** | **\$18.00** |
| **Hybrid (Flash + Gemini Pro)** | Mixed | Mixed | **\$0.00500** | **\$49.95** |
| **Claude 3.5 Haiku** | \$0.80 | \$4.00 | **\$0.00520** | **\$52.00** |
| **Hybrid (Qwen 72B + Qwen3-Max)** | Mixed | Mixed | **\$0.00568** | **\$56.85** |
| **Gemini 1.5 Pro** | \$1.25 | \$5.00 | **\$0.00688** | **\$68.75** |
| **Qwen3-Max** | \$1.20 | \$6.00 | **\$0.00780** | **\$78.00** |
| **Hybrid (Flash + Sonnet)** | Mixed | Mixed | **\$0.01392** | **\$139.20** |
| **Claude 3.5 Sonnet** | \$3.00 | \$15.00 | **\$0.01950** | **\$195.00** |

### The Hybrid Pipeline Strategy: An Architectural Evaluation

Your intuition to split the pipeline between a "Flash/72B" model and a "Pro/Max" model is **the exact right approach from an engineering and cost-optimization standpoint**. Here is a breakdown of the reasoning levels actually required for each step:

#### Prompt 1 (Ground Truth): Requires "Compliance \& Creativity"

* **The Task:** Generating contextually distinct, tier-appropriate sentences. It does not require deep logical puzzle-solving; it requires high compliance with length, vocabulary constraints, and JSON syntax.
* **The Model Fit:** Fast, cheap models like **Gemini 1.5 Flash** or **Qwen 2.5 72B** are exceptional at this. Their training heavily biases toward standard language generation. Using a "Pro" model here is a waste of compute because generating a grammatically correct sentence about an apple is a solved problem for parameter sizes >8B.


#### Prompts 2 \& 3 (Distractor Engine): Requires "Pedagogical Reasoning"

* **The Task:** Designing a multiple-choice question where the wrong answers are *wrong for a specific, identifiable reason*, and then writing an explanation for that specific error in the target language.
* **The Model Fit:** This requires **"Pro" level reasoning** (Gemini 1.5 Pro, Qwen3-Max, Claude 3.5 Sonnet, or DeepSeek V3).
    * *Why Flash/72B fail here:* Smaller models suffer from "distractor bleed." If you ask for a contextually wrong distractor (Level 3), a small model might accidentally generate a word that is *also* grammatically wrong, meaning the student gets it right for the wrong reason. Smaller models also struggle to explain *why* a collocation is unnatural without hallucinating corpus data.
    * *The "Pro" Advantage:* Pro models excel at linguistic boundary-testing. They can generate a sentence that is grammatically flawless but semantically absurd (Level 6) and explain the semantics accurately.


### The Verdict on Qwen vs. Gemini vs. DeepSeek

1. **If you want the cheapest "Good Enough" Pipeline:** Use **DeepSeek V3** (\$13.70 / 10k words) for the entire pipeline. It has "Pro" level reasoning but is priced closer to a "Flash" model.
2. **If you want the most robust Hybrid Pipeline:** Pair **Qwen 2.5 72B** for Prompt 1 with **Qwen3-Max** or **Gemini 1.5 Pro** for Prompts 2 \& 3 (\$50 - \$56 / 10k words). Qwen is currently the undisputed king of non-English language generation, particularly for Mandarin, Japanese, and European languages. If LinguaLoop is heavily targeting Asian languages, Qwen models will generate much more authentic idiomatic contexts than Gemini.
3. **If you need absolute linguistic perfection (Zero-Shot):** Pair **Flash** (Prompt 1) with **Claude 3.5 Sonnet** (Prompts 2/3) at ~\$139 / 10k words. Sonnet's formatting compliance and pedagogical reasoning logic are still slightly ahead of Gemini Pro.
<span style="display:none">[^8_1][^8_10][^8_2][^8_3][^8_4][^8_5][^8_6][^8_7][^8_8][^8_9]</span>

<div align="center">⁂</div>

[^8_1]: https://openrouter.ai/qwen/qwen-2.5-72b-instruct

[^8_2]: https://openrouter.ai/qwen/qwen2.5-vl-72b-instruct

[^8_3]: https://openrouter.ai/eva-unit-01/eva-qwen-2.5-72b

[^8_4]: https://openrouter.ai/Qwen/Qwen2.5-VL-72B-Instruct/providers

[^8_5]: https://www.typingmind.com/guide/openrouter/qwen-2.5-72b-instruct

[^8_6]: https://pricepertoken.com/pricing-page/model/qwen-qwq-32b

[^8_7]: https://wavespeed.ai/llm/model/qwen/qwen-2.5-72b-instruct

[^8_8]: https://www.typingmind.com/guide/openrouter/qwen3-32b

[^8_9]: https://www.alibabacloud.com/help/en/model-studio/models

[^8_10]: https://www.eesel.ai/blog/qwen-pricing


---

# Write out a complete report detailing the prompts, exercise ladder, how users move up and down the ladder. We will start by building the english pipeline - let's use gemini 2.5 flash lite for prompt 1, and claude sonnet 4.6 for the other prompts

Yes — below is a complete working report for the **English-first LinguaLoop vocabulary pipeline**, using your chosen split: **Gemini 2.5 Flash Lite for Prompt 1** and **Claude Sonnet 4.6 for Prompts 2 and 3**. The design keeps generation deterministic and cacheable, moves the learner from receptive recognition toward controlled production, and treats progression not as a simple upward march but as a managed cycle of stabilization, promotion, and repair, which aligns well with the receptive-to-productive distinction in vocabulary acquisition research.[^9_1][^9_2]

# LinguaLoop English Vocabulary Pipeline

## System design

The pipeline is built around a simple principle: generate once, store forever. Every word receives a fixed asset pack in the database the first time it is introduced; after that, the system never asks the model to improvise again unless a human flags the item for repair. This matters pedagogically as much as technically, because learner performance only becomes interpretable when the item itself remains stable across repeated exposures; otherwise, one is not measuring progress on a word, but progress on a shifting test.[^9_3][^9_1]

For the English launch, the system uses three prompts. **Prompt 1** creates ground truth: one learner-tier definition, one primary collocate where relevant, and six correct example sentences with the exact target substring returned for frontend blanking. **Prompt 2** creates lexical and semantic exercise assets: phonetic distractors, cloze distractors, collocation gap distractors when applicable, and semantic misuse sentences. **Prompt 3** creates grammar and structure assets: morphology distractors, one syntax-error sentence with correction and explanation, and collocation-repair options when applicable. This division is efficient because sentence generation is mostly a compliance task, whereas distractor design requires finer pedagogical judgment about why an option is wrong.

The whole system is dynamic but deterministic. The backend decides in advance which exercise levels are active for a given word, then injects only those exercise instructions into Prompts 2 and 3. In other words, the model is never asked to “decide what to do”; it is only asked to fill a sharply bounded template. That reduction in freedom is not a limitation but a design virtue — the same way a good exam constrains ambiguity in order to reveal knowledge rather than reward guesswork.

## Exercise ladder

For English, the ladder should contain **nine operational levels**, because you have chosen to exclude jumbled sentence generation from the LLM stage and handle segmentation or assembly elsewhere. The ladder therefore becomes: 1) phonetic/orthographic recognition, 2) semantic definition matching, 3) cloze completion, 4) morphology slot, 5) collocation gap fill when applicable, 6) semantic discrimination, 7) spot the incorrect sentence, 8) collocation repair when applicable, and 9) capstone translation or production task. This still preserves the deep logic of the receptive-to-productive continuum: first form, then meaning, then contextual fit, then grammatical control, then lexical-naturalness, then controlled production.[^9_4][^9_1]

The crucial design choice is that each level must test a **different failure mode**. Level 1 distractors fail on form similarity only. Level 2 distractors fail on meaning. Level 3 distractors are grammatically legal but contextually absurd. Level 4 distractors are real morphological siblings but wrong for the sentence. Level 5 distractors are semantically near but collocationally unnatural. Level 6 distractors are grammatically correct sentences that misuse the target semantically or pragmatically. Level 7 contains one structurally wrong sentence that mimics a learner error. Level 8 asks the learner to repair an unnatural collocation. Level 9 demands actual production under controlled conditions. This separation is important because weak multiple-choice design often collapses all wrongness into one indistinct fog; good design isolates the kind of mistake being tested.[^9_5][^9_6]

For English routing, concrete nouns skip Levels 5 and 8, because their lexical learning burden is usually not driven by strong collocational dependency in the same way as abstract nouns, verbs, and adjectives. Abstract nouns, verbs, and adjectives take the full ladder, because their productive mastery depends heavily on syntactic behavior and collocational behavior, both of which are distinct parts of word knowledge in Nation’s framework.[^9_2][^9_7][^9_8]

### English ladder map

| Level | Name | Purpose | Correct option type | Distractor type |
| :-- | :-- | :-- | :-- | :-- |
| 1 | Phonetic/Orthographic | Recognise the word’s form | exact target word | similar-looking/sounding, no semantic overlap |
| 2 | Definition Match | Link form to meaning | correct database definition | unrelated definitions from other words |
| 3 | Cloze Completion | Fit word to context | target substring | same POS, grammatically valid, contextually wrong |
| 4 | Morphology Slot | Choose correct inflected form | exact substring used in sentence | valid morphological siblings, wrong in context |
| 5 | Collocation Gap | Recognise natural collocate | primary collocate | semantically close but unnatural pairings |
| 6 | Semantic Discrimination | Detect semantic misuse | one natural sentence | three grammatical but semantically/pragmatically wrong sentences |
| 7 | Spot Incorrect Sentence | Detect structural error | the incorrect sentence | three structurally correct sentences |
| 8 | Collocation Repair | Repair unnatural phrase | best collocate | transfer-like or weak collocates |
| 9 | Capstone Production | Produce controlled output | learner-generated text | no MCQ distractors |

## Prompt architecture

The prompt architecture should be explicit, sparse, and mechanical. Do not ask the model to infer omitted business rules, do not hide schema expectations inside prose, and do not let it decide whether an exercise is needed. Your backend already knows that. The prompts should therefore be assembled like a compiler prepares instructions for a deterministic function.

### Prompt 1

Prompt 1 should go to **Gemini 2.5 Flash Lite**, because this stage is primarily about fluent, tier-controlled sentence generation and exact string return, not subtle error design. The model receives the target word, POS, learner tier, corpus sentences already approved if any, and the required number of additional sentences needed to reach six. You were right to reject the earlier “riddle” phrasing; simply tell it the number required. That removes pointless reasoning overhead.

The output keys should be numeric only. A clean version is:

```json
{
  "1": "tier-appropriate definition",
  "2": "primary collocate or null",
  "3": [
    { "1": "full sentence", "2": "exact target substring" },
    { "1": "full sentence", "2": "exact target substring" },
    { "1": "full sentence", "2": "exact target substring" },
    { "1": "full sentence", "2": "exact target substring" },
    { "1": "full sentence", "2": "exact target substring" },
    { "1": "full sentence", "2": "exact target substring" }
  ]
}
```

A complete Prompt 1 template for English can be written as follows:

```text
Role: Expert computational linguist generating English vocabulary assets.

Language: English
Target word: {WORD}
Part of speech: {POS}
Tier: {TIER_NAME}
Tier instruction: {TIER_INSTRUCTION}

Corpus sentences already approved:
{CORPUS_SENTENCES_JSON}

Task:
Generate the base assets for one English vocabulary word.

Rules:
1. All output values must be in English only.
2. Return exactly one definition suitable for the learner tier.
3. Return the primary collocate for this word if one is strongly relevant; otherwise return null.
4. Return exactly 6 correct example sentences total.
5. Use the provided corpus sentences unchanged.
6. Generate exactly {N} additional sentences so that the total is 6.
7. Every sentence must place the word in a meaningfully different context or sentence structure.
8. For each sentence, return the exact substring used for the target word as it appears in that sentence.
9. Do not generate explanations.
10. Output valid JSON only.

Output schema:
"1" = definition
"2" = primary collocate or null
"3" = array of 6 objects
Inside each object:
  "1" = full sentence
  "2" = exact target substring
```

The backend should validate this output before storage. If the word is “adapt” and one sentence contains “adapted,” the returned substring must be exactly “adapted,” not the lemma. This is what lets the frontend blank deterministically without asking a morphological parser to improvise.

### Prompt 2

Prompt 2 should go to **Claude Sonnet 4.6**, because this is where the system starts requiring educational discrimination rather than mere generation. A distractor is not just a wrong answer; it is a deliberately shaped error that reveals a specific misunderstanding. Designing such errors cleanly is a much higher-order task than writing six natural sentences.

For English, Prompt 2 should cover Levels 1, 3, 5 if active, and 6. The output should again use numeric keys only. At the option level:

- `"1"` = option text
- `"2"` = boolean correctness
- `"3"` = explanation in English of why the option is correct or incorrect

Schema:

```json
{
  "1": [
    { "1": "text", "2": true, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" }
  ],
  "3": [
    { "1": "text", "2": true, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" }
  ],
  "5": [
    { "1": "text", "2": true, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" }
  ],
  "6": [
    { "1": "sentence", "2": true, "3": "reason" },
    { "1": "sentence", "2": false, "3": "reason" },
    { "1": "sentence", "2": false, "3": "reason" },
    { "1": "sentence", "2": false, "3": "reason" }
  ]
}
```

A working Prompt 2 template:

```text
Role: Expert computational linguist generating English vocabulary exercises.

Language: English
Target word: {WORD}
Part of speech: {POS}
Tier: {TIER_NAME}
Tier instruction: {TIER_INSTRUCTION}

Base assets:
Definition: {DEF}
Primary collocate: {COLLOCATE_OR_NULL}
Sentence A: {S1}
Target substring A: {SS1}
Sentence B: {S2}
Target substring B: {SS2}
Sentence C: {S3}
Target substring C: {SS3}

Generate only the exercise levels listed here:
{ACTIVE_LEVELS_JSON}

Rules for all output:
1. All output values must be in English only.
2. Output valid JSON only.
3. Use numeric keys only.
4. For every option object:
   "1" = option text
   "2" = true or false
   "3" = explanation of why it is correct or incorrect
5. Explanations must be short, clear, and pedagogical.

Level rules:
For "1":
- Return 4 options total.
- 1 correct option = target word.
- 3 distractors must look or sound similar.
- Distractors must not be semantic synonyms.

For "3":
- Use Sentence A.
- The correct option is Target substring A.
- Generate 3 distractors.
- Distractors must be the same part of speech and grammatically valid in the sentence.
- Distractors must be contextually wrong, not grammatically wrong.

For "5" if included:
- Use Sentence B.
- The correct option is the primary collocate.
- Generate 3 distractors that are semantically close but collocationally unnatural.

For "6":
- Use Sentence C as the correct option.
- Generate 3 new sentences using the target word.
- Each wrong sentence must be grammatical, but semantically or pragmatically inappropriate.
```


### Prompt 3

Prompt 3 also goes to **Claude Sonnet 4.6**, because morphology, structural learner-like errors, and collocation repair require controlled mutation rather than free generation. For English, this prompt covers Level 4, Level 7, and Level 8 if active.

Schema:

```json
{
  "4": [
    { "1": "text", "2": true, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" }
  ],
  "7": {
    "1": "incorrect sentence",
    "2": "corrected sentence",
    "3": "explanation"
  },
  "8": [
    { "1": "text", "2": true, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" },
    { "1": "text", "2": false, "3": "reason" }
  ]
}
```

Prompt 3 template:

```text
Role: Expert computational linguist generating English grammar and usage exercises.

Language: English
Target word: {WORD}
Part of speech: {POS}
Tier: {TIER_NAME}
Tier instruction: {TIER_INSTRUCTION}

Base assets:
Primary collocate: {COLLOCATE_OR_NULL}
Sentence D: {S4}
Target substring D: {SS4}
Sentence E: {S5}
Target substring E: {SS5}
Sentence F: {S6}
Target substring F: {SS6}

Generate only the exercise levels listed here:
{ACTIVE_LEVELS_JSON}

Rules for all output:
1. All output values must be in English only.
2. Output valid JSON only.
3. Use numeric keys only.
4. For option objects:
   "1" = option text
   "2" = true or false
   "3" = explanation

Level rules:
For "4":
- Use Sentence D.
- Correct option = Target substring D.
- Generate 3 distractors that are real morphological siblings of the target word.
- Distractors must be wrong because of sentence grammar, tense, agreement, or form.

For "7":
- Generate one new sentence containing a common learner-like structural error.
- Keep the target word spelled correctly.
- "1" = incorrect sentence
- "2" = corrected sentence
- "3" = explanation of the error

For "8" if included:
- Use Sentence F and the known collocate.
- Return the correct collocate plus 3 unnatural collocates.
- Wrong options should reflect plausible learner substitution or weak collocation.
```


## Movement through the ladder

The learner should not move through the ladder in a rigid once-only line. Instead, every word should live in one of several states: **new**, **active**, **fragile**, **stable receptive**, **stable productive**, or **retired for long-interval review**. This matters because a learner may recognise a word long before being able to use it, and the system should record that distinction rather than pretending a single correct answer means mastery.[^9_9][^9_1]

The cleanest rule is this: each word has a **current ladder position** and a **stability score**. A user moves upward only when they answer the current level correctly under the required repetition condition. A user moves downward when they fail in a way that reveals the relevant knowledge has not consolidated. The ladder is therefore less like climbing a staircase and more like crossing stepping stones over water; hesitation is expected, and falling back one or two stones is part of the design, not evidence of failure.

### Promotion rules

A practical English launch version could use these rules:


| Current level | Promote when | On promotion |
| :-- | :-- | :-- |
| 1 | 2 correct attempts across 2 sessions | move to 2 |
| 2 | 2 correct attempts across 2 sessions | move to 3 |
| 3 | 2 correct attempts across 2 sessions | move to 4 |
| 4 | 2 correct attempts across 2 sessions | move to next active level |
| 5 | 2 correct attempts across 2 sessions | move to 6 |
| 6 | 2 correct attempts across 2 sessions | move to 7 |
| 7 | 2 correct attempts across 2 sessions | move to next active level |
| 8 | 2 correct attempts across 2 sessions | move to 9 |
| 9 | 2 successful graded productions | mark productively stable |

This “two sessions” rule matters because one correct answer can be luck, recency, or sentence-shape memory. Repeating success across spaced sessions is a better signal that the learner is beginning to own the word rather than merely echo it. That principle is consistent with the broader literature on retrieval and strengthening over time.[^9_10][^9_4]

### Demotion rules

Demotion should be conservative but real. A word should drop only when the error suggests loss of the knowledge that the current level presupposes.


| Failure point | Demotion rule |
| :-- | :-- |
| Level 1 | stay at 1 |
| Level 2 | drop to 1 after 2 failures in separate sessions |
| Level 3 | drop to 2 after 2 failures |
| Level 4 | drop to 3 after 2 failures |
| Level 5 | drop to 4 after 2 failures |
| Level 6 | drop to 5 after 2 failures |
| Level 7 | drop to 6 after 2 failures |
| Level 8 | drop to 7 after 2 failures |
| Level 9 | drop to highest previously stable receptive level |

This creates a pipeline that is firm without being punitive. A learner who fails a productive capstone does not return to total ignorance; they return to the highest level at which performance was stable. That distinction is humane, but it is also analytically useful: the system begins to map not just whether the learner knows the word, but where the breakdown occurs — form, meaning, collocation, syntax, or production.

## Implementation rules

Level 2 should use your database, not the model. The correct definition comes from Prompt 1; the three distractor definitions should be sampled from other English words in the same tier band. This is cheap, deterministic, and entirely adequate for an early-stage exercise. Level 2 is not meant to be the crown jewel of the pipeline; it is a bridge between word recognition and contextual recognition.

For all blanking exercises, the backend or frontend should blank the substring itself. The model should always return the full sentence plus the exact answer item. That applies to Level 3, Level 4, and Level 5. Likewise, for Level 8 the model should return the correct collocate and several unnatural ones; the frontend can render the sentence with one wrong collocate swapped in for display. This is the right division of labour: the model decides language, while the product code decides rendering.

The best first production version for English is therefore:

- **Prompt 1:** Gemini 2.5 Flash Lite
- **Prompt 2:** Claude Sonnet 4.6
- **Prompt 3:** Claude Sonnet 4.6
- **Level 2 distractors:** database only
- **Blanking/rendering:** frontend/backend only
- **Jumbled sentence:** excluded from LLM generation
- **Caching:** all outputs stored once per word
- **Human review triggers:** ambiguity, duplicate sentence shapes, collocational uncertainty, malformed JSON, or suspiciously weak explanations

This split is sound because Prompt 1 is essentially controlled sentence manufacture, while Prompts 2 and 3 are closer to assessment design — and assessment design, like translation in its most serious sense, is not simply language generation but the deliberate arrangement of difference. A system becomes educational when it knows not only the right answer, but why the wrong ones are seductive.

Would you like the next step to be a **production-ready TypeScript interface/schema set** for these three prompt outputs and the word-state progression logic?

<div align="center">⁂</div>

[^9_1]: https://academic.oup.com/applij/article/41/4/481/5270836

[^9_2]: https://nottingham-repository.worktribe.com/preview/1513668/Word Knowledge - RESUBMITTED.pdf

[^9_3]: https://aclanthology.org/W19-4451.pdf

[^9_4]: https://media.neliti.com/media/publications/242518-how-vocabulary-is-learned-45a2c109.pdf

[^9_5]: https://www.cambridgeassessment.org.uk/blogs/mcq-design-language-blog/

[^9_6]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11623049/

[^9_7]: https://www.ukessays.com/essays/english-language/components-of-word-knowledge-adapted-from-nations-english-language-essay.php

[^9_8]: http://www.eurosla.org/monographs/EM02/Henriksen.pdf

[^9_9]: https://eric.ed.gov/?id=EJ1186015

[^9_10]: https://onlinelibrary.wiley.com/doi/full/10.1002/tesj.767


---

# A few notes:

- Keep the jumbled sentence in teh levels table, just note that it will not need llm generation
- If the user gets the exercise incorrect in the session, they will need to keep doing it until they get it correct

These are perfect refinements. Forcing the user to reach the correct answer within the session ensures they actually read the pedagogical reasoning we spent tokens generating, rather than just clicking away.

Here is the corrected ladder map and the updated progression logic incorporating the intra-session loop.

### Updated English Ladder Map (10 Levels)

Level 9 (Jumbled Sentence) is restored to the structural progression. It requires no LLM generation because your backend will tokenize one of the validated sentences (e.g., Sentence 6) and the frontend will handle the drag-and-drop UI.


| Level | Name | Purpose | Correct Option | Distractor / Error Source | LLM Prompt |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **1** | Phonetic/Orthographic | Recognise the word’s form | exact target word | similar-looking/sounding, no semantic overlap | Prompt 2 |
| **2** | Definition Match | Link form to meaning | target definition | unrelated definitions from other words | Database |
| **3** | Cloze Completion | Fit word to context | target substring | same POS, grammatically valid, contextually wrong | Prompt 2 |
| **4** | Morphology Slot | Choose correct inflection | exact substring | valid morphological siblings, wrong in context | Prompt 3 |
| **5** | Collocation Gap | Recognise natural collocate | primary collocate | semantically close but unnatural pairings | Prompt 2 |
| **6** | Sem. Discrimination | Detect semantic misuse | one natural sentence | grammatical but semantically wrong sentences | Prompt 2 |
| **7** | Spot Incorrect Syntax | Detect structural error | the incorrect sentence | three structurally correct sentences | Prompt 3 |
| **8** | Collocation Repair | Repair unnatural phrase | best collocate | transfer-like or weak collocates | Prompt 3 |
| **9** | **Jumbled Sentence** | **Assemble correct syntax** | **correctly ordered chunks** | **N/A (Frontend shuffles chunks)** | **None** |
| **10** | Capstone Production | Produce controlled output | learner-generated text | N/A (LLM grades the free-text input) | Dynamic |


***

### Updated Movement \& Progression Logic

Because we now force the user to complete the exercise in the session, we must distinguish between **intra-session behavior** (what happens right now) and **inter-session progression** (how they move up and down the ladder over time).

#### 1. Intra-Session Loop (Forced Mastery)

If a user selects an incorrect option:

1. The UI immediately displays the `reasoning` string for that specific distractor (explaining *why* their choice was wrong).
2. The user is penalized in the ELO calculation.
3. **The user cannot proceed to the next card until they select the correct answer.**
4. Once they select the correct answer, the UI displays the `reasoning` for the correct choice to reinforce the learning, and the session continues.

#### 2. Inter-Session Ladder Movement

Because they are forced to eventually get it right, "success" for the sake of ladder movement is strictly defined as **getting it right on the first attempt**.

* **Promotion Rule:** A word promotes to the next active level when the user achieves a **first-try success in 2 separate spaced-repetition sessions**. (This proves the knowledge is stabilizing, not just a fluke).
* **Demotion Rule:** A word drops down one active level if the user fails the *first try* in 2 consecutive sessions.

This creates a highly resilient learning loop: the user is never allowed to ignore a mistake (thanks to the intra-session lock), but the system doesn't artificially inflate their progress just because they eventually clicked the right button.

***

Would you like me to write out the **production-ready TypeScript interfaces and Zod schemas** for this pipeline? This will give your backend the exact types needed to parse the JSON from Gemini (Prompt 1) and Claude (Prompts 2 \& 3), and construct the unified Database Object for the word.

---

# Just write out the production ready plan and task list. Remember, we want this to be modular, robust and easily expandable in future

The correct production plan is to treat this vocabulary pipeline not as a single feature, but as a small assessment engine with cleanly separated domains: lexical generation, exercise assembly, learner-state progression, review scheduling, and quality assurance. If you build those domains as independent modules now, the English pipeline will ship faster *and* you will avoid the usual trap in language products, where every later language becomes a pile of exceptions duct-taped onto an English-first core. Nation’s framework is helpful here precisely because it reminds us that vocabulary knowledge is multi-component — form, meaning, syntax, collocation, and use — so the software should mirror that separability instead of collapsing everything into one monolithic “quiz generator.”[^11_1][^11_2]

The immediate implementation target should therefore be a modular, deterministic English pipeline using **Gemini 2.5 Flash Lite** for Prompt 1 and **Claude Sonnet 4.6** for Prompts 2 and 3, with all generated assets cached permanently after validation. Because the system forces the learner to continue until they reach the correct answer in-session, progression must be based on **first-attempt correctness**, not eventual correctness; that distinction preserves the pedagogical value of the generated explanations while keeping the mastery signal analytically honest.[^11_3][^11_4]

## Architecture

The production system should be divided into six modules, each with a narrow responsibility. First, a **Word Intake Module** classifies the word by language, part of speech, semantic class, tier, and exercise eligibility. Second, an **Asset Generation Module** runs the three prompts, validates the outputs, and writes immutable exercise assets to the database. Third, an **Exercise Delivery Module** assembles UI-ready cards from stored assets, including blanking substrings and swapping collocates where needed. Fourth, a **Learner State Module** tracks current ladder level, first-try accuracy, intra-session retries, and stable versus fragile knowledge states. Fifth, a **Scheduling Module** selects which word-level exercise appears next based on review timing and word state. Sixth, a **QA and Repair Module** identifies malformed, ambiguous, repetitive, or pedagogically weak assets for regeneration or human review.[^11_5][^11_6]

This separation matters because it lets you replace one layer without contaminating the others. If you later move Prompt 1 from Gemini to Qwen for Japanese, or introduce a Chinese particle module, the learner-state engine should not notice. Good software architecture, like good morphology, gains power by factoring variation into reusable forms.

## Exercise system

The English ladder should retain all ten levels in the product design, with **Level 9 Jumbled Sentence included in the ladder but excluded from LLM generation**, since it will be built from already approved sentences using backend tokenization and frontend assembly. The levels are: 1) phonetic/orthographic recognition, 2) definition match, 3) cloze completion, 4) morphology slot, 5) collocation gap fill where applicable, 6) semantic discrimination, 7) spot incorrect syntax, 8) collocation repair where applicable, 9) jumbled sentence, and 10) capstone production.[^11_2][^11_7]

Every level must preserve a single dominant error axis. Level 3 distractors fail contextually but remain grammatically valid; Level 4 distractors fail grammatically but remain real English forms; Levels 5 and 8 fail collocationally rather than semantically; Level 6 fails semantically while remaining grammatical; Level 7 fails structurally in one sentence only. This is non-negotiable, because once distractors become wrong in multiple ways, the exercise stops measuring the intended skill and starts rewarding test-taking instinct over lexical acquisition.[^11_8][^11_5]

## Prompt plan

The prompt layer should be implemented as three independent services, each with strict contracts and numeric JSON keys only. **Prompt 1** generates the tier-appropriate definition, primary collocate or null, and exactly six correct sentences with exact target substrings. **Prompt 2** generates Levels 1, 3, 5, and 6, but only the levels that the backend explicitly includes for that word. **Prompt 3** generates Levels 4, 7, and 8 under the same deterministic inclusion rule. Level 2 uses database definitions; Level 9 uses existing approved sentences and local chunking logic; Level 10 uses runtime evaluation rather than precomputed MCQ assets.

The key implementation principle is that the backend must assemble prompts from known flags, rather than asking the model to infer applicability. If a concrete noun should skip collocation work, the prompt should not mention Level 5 or 8 at all. If the word is English, the prompt should contain only English rules, not multilingual abstractions. The prompt is therefore not a brainstorming instruction but an execution manifest.

## User progression

A user should encounter one exercise level for one word at a time, and if they answer incorrectly, they must continue attempting that same exercise until they answer correctly in the session. This means the system has two kinds of truth: **session completion truth**, where the learner eventually reaches the right answer, and **progression truth**, where only first-attempt correctness counts toward movement up the ladder. That distinction is essential, because otherwise the product confuses assisted correction with mastery.

Promotion should occur when the learner gets the current level correct on the first attempt in two separate review sessions. Demotion should occur when the learner misses the first attempt for the same level in two consecutive sessions, dropping the word down one active level. If they fail the capstone, the word should return to the highest receptive level at which first-attempt performance remains stable. This creates a system that is strict without being absurdly punitive, and it maps naturally onto the empirically supported gap between receptive and productive knowledge.[^11_9][^11_2]

## Data design

At the database level, each word should have a stable **Word Asset Record**, a dynamic **Word Routing Record**, and a per-user **Word Progress Record**. The asset record stores the immutable outputs from Prompts 1–3 plus metadata such as generation model, prompt version, validation status, and timestamps. The routing record stores whether the word is a concrete noun, abstract noun, verb, adjective, whether collocation levels are active, and which sentence IDs feed which levels. The progress record stores the learner’s current active level, first-attempt success history, retry counts, review due date, stable/fragile state, and capstone status.

This separation is worth preserving because content facts should not mutate when learner behavior changes. The sentence “She adapted quickly to the new school” is a content asset; whether a given learner currently struggles with its morphological slot is a progress fact. Conflating the two would make analytics messy and repair workflows brittle.

## Quality controls

The generation pipeline should include four mandatory validation layers before a word becomes live. First, **schema validation** checks JSON structure and required numeric keys. Second, **linguistic validation** checks that returned substrings occur exactly in the sentence, that morphology distractors are valid English forms, and that collocation fields are null only when appropriate. Third, **pedagogical validation** checks that distractors obey the intended error axis for each level. Fourth, **content quality validation** checks for duplicate sentence shapes, repeated semantic contexts, ambiguity, malformed English, or explanations that merely restate correctness without teaching anything useful.[^11_6][^11_5]

A manual review queue should trigger when the model returns suspiciously weak assets: repeated sentence templates, multiple distractors that could arguably be correct, flat or tautological explanations, or collocates that appear low-confidence. This is especially important in the early English launch, because your first few thousand words will define the norms from which later automation inherits its habits.

## Delivery roadmap

The most robust delivery path is to ship in five phases. **Phase 1** should build the core schemas, prompt services, validation layer, and asset storage. **Phase 2** should build exercise rendering for Levels 1–8 plus Level 9 from local chunking. **Phase 3** should implement learner progression, first-attempt logic, retry-in-session behavior, and scheduling. **Phase 4** should implement analytics, QA review tools, and asset repair workflows. **Phase 5** should generalize the English architecture into a language-spec-driven engine for Chinese and Japanese.

This staged rollout matters because product systems often fail not at generation but at re-generation, correction, migration, and analytics. Shipping the glamorous part first — the LLM prompts — without the sober part — validation, state tracking, repair, and review — produces a demo rather than a platform.

## Task list

### Phase 1: Core domain model

Define the canonical entities for `Word`, `WordSense`, `WordAsset`, `ExerciseAsset`, `WordRouting`, `UserWordProgress`, `SessionAttempt`, and `ReviewSchedule`. Implement numeric-key JSON parsers for Prompt 1, Prompt 2, and Prompt 3 outputs, and version every schema so regenerated assets can coexist with legacy ones during future migrations.

Create the English routing rules as configuration, not hardcoded conditionals scattered through business logic. That configuration should decide which levels are active for concrete nouns, abstract nouns, verbs, and adjectives, and it should map which of the six stored sentences feed each level. This makes later language expansion architectural rather than surgical.

### Phase 2: Prompt services

Build a dedicated Prompt 1 service for Gemini 2.5 Flash Lite with strict response parsing, retries on invalid JSON, and sentence-count enforcement. Build Prompt 2 and Prompt 3 services for Claude Sonnet 4.6 with modular prompt block injection so skipped exercises are omitted entirely from the prompt payload.

Store prompt templates as versioned files, not inline strings buried in controllers. Add prompt test fixtures for representative English word types: concrete noun, abstract noun, verb, adjective. This is the software equivalent of building with interchangeable beams rather than pouring one slab and hoping it can later be carved into rooms.

### Phase 3: Asset validation and persistence

Implement automated validators for substring matching, duplicate sentence detection, distractor count, option correctness cardinality, and explanation presence. Add exercise-specific validators: for Level 3, ensure distractors are not identical to the target substring; for Level 4, ensure distractors are real morphological siblings; for Level 5 and 8, ensure a collocate exists before activation; for Level 7, ensure the incorrect sentence differs meaningfully from the corrected sentence.

Persist approved assets in immutable tables with `model_name`, `model_version`, `prompt_version`, `generated_at`, and `validated_at`. Add a repair table for flagged assets so regeneration does not overwrite production content invisibly.

### Phase 4: Exercise delivery

Build a service that converts stored assets into UI-ready exercise cards. This service should perform all blanking operations, option shuffling, answer-key marking, and Level 8 collocate substitution at runtime while leaving the underlying stored asset unchanged. It should also generate Level 2 from database definitions and Level 9 from stored sentences using backend chunking logic.

Ensure the frontend can render per-option explanations immediately after a wrong answer, then keep the learner on the same exercise until they answer correctly. Track first-attempt correctness separately from later in-session correction, because those are pedagogically different events.

### Phase 5: Progression engine

Implement level movement rules with two distinct counters: `first_try_success_sessions` and `first_try_failure_sessions`. Promotion should require two successful sessions at the current level; demotion should require two consecutive failed first attempts at that level. Record retries within the session, but do not let eventual success count as ladder mastery.

Add word states such as `new`, `learning`, `fragile_receptive`, `stable_receptive`, `fragile_productive`, and `stable_productive`. This gives the scheduling layer richer control and prepares the system for future adaptive review models.

### Phase 6: Scheduling and analytics

Create a scheduler that selects the next word-level exercise based on due date, current ladder level, learner fatigue rules, and recent failure patterns. Add analytics for first-attempt accuracy by level, retry counts by level, ambiguity flags by word type, and explanation usefulness signals inferred from correction behavior.

This will show whether the pipeline is failing linguistically or structurally. If Level 6 collapses across many abstract verbs, for example, the issue may not be the learners but the quality of semantically wrong yet grammatical distractors — an insight that only becomes visible if the analytics mirror the architecture.

### Phase 7: QA and authoring tools

Build an internal review dashboard where staff can inspect a word’s six base sentences, active levels, generated distractors, explanations, and current learner performance. Allow reviewers to disable a single level, regenerate one prompt only, or mark a word for semantic-class correction without deleting the rest of the word asset.

This is the difference between a system that can evolve and a system that must be rebuilt every time it errs. Language products mature by revision, and revision requires handles.

### Phase 8: Expansion readiness

Abstract the language-specific logic into a `LanguageSpec` layer even before Chinese and Japanese ship. For English now, it can contain morphology settings and level-routing defaults; later, it will govern particles, measure words, counters, and language-specific grammar slots. Also abstract the tier system into configuration so English tier prompts today can become multilingual learner-age scaffolds tomorrow without reworking the core pipeline.

Do not wait until the second language to create this seam. By then, architecture hardens into habit, and habit in software, as in language learning, is both efficient and tyrannical.

## Immediate build order

The most practical order for the next sprint is this: first define schemas and database tables; then implement Prompt 1 end-to-end; then Prompt 2; then Prompt 3; then validation; then exercise assembly; then first-attempt progression logic; then review scheduling; then QA tooling. That sequence lets you get one English word from intake to playable exercise cards before you widen the surface area.

A concise build queue for engineering would be:

1. Define database schema and versioned JSON contracts.
2. Implement English routing config by POS and semantic class.
3. Build Prompt 1 service on Gemini 2.5 Flash Lite.
4. Build Prompt 2 service on Claude Sonnet 4.6.
5. Build Prompt 3 service on Claude Sonnet 4.6.
6. Implement validation pipeline and failure states.
7. Store immutable word assets and repair records.
8. Build Levels 1–8 renderer plus Level 9 local chunking.
9. Implement in-session retry-until-correct behavior.
10. Implement first-attempt-only promotion/demotion logic.
11. Build scheduler and review queues.
12. Build internal QA dashboard and targeted regeneration tools.
13. Pilot on a controlled English word list before scaling.

The plan is now stable enough to implement without guessing. The next best artifact is a **technical spec with database tables, JSON schemas, and service boundaries**, because once those are fixed, the prompts become contracts rather than hopes.

<div align="center">⁂</div>

[^11_1]: https://www.ukessays.com/essays/english-language/components-of-word-knowledge-adapted-from-nations-english-language-essay.php

[^11_2]: https://academic.oup.com/applij/article/41/4/481/5270836

[^11_3]: https://aclanthology.org/W19-4451.pdf

[^11_4]: https://www.fi.muni.cz/~xpelanek/publications/CAE-elo.pdf

[^11_5]: https://www.cambridgeassessment.org.uk/blogs/mcq-design-language-blog/

[^11_6]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11623049/

[^11_7]: https://media.neliti.com/media/publications/242518-how-vocabulary-is-learned-45a2c109.pdf

[^11_8]: https://www.cambridgeenglish.org/Images/526186-research-notes-72.pdf

[^11_9]: https://eric.ed.gov/?id=EJ1186015


---

# great, provide that artifact now

Here is the complete technical artifact for the LinguaLoop English vocabulary pipeline. This spec defines the database entities, strict TypeScript/Zod schemas for LLM validation, and the service boundaries required to build the system modularly.

***

### Part 1: Database Schema (Prisma/SQL Structure)

This schema strictly separates **Content Truth** (immutable generated assets) from **Progression Truth** (how a user is performing).

```prisma
// 1. Core Dictionary
model Word {
  id              String      @id @default(uuid())
  language        String      // e.g., "EN"
  text            String      // e.g., "mitigate"
  pos             String      // "noun", "verb", "adjective"
  semantic_class  String      // "concrete", "abstract", etc.
  tier            Int         // 1 to 6 (maps to Age/CEFR tiers)
  base_elo        Int         // Initial difficulty rating
  active_levels   Int[]       // e.g., [1, 2, 3, 4, 6, 7, 9, 10] (skips 5/8 if concrete)
  
  assets          WordAsset[]
  progress        UserWordProgress[]
}

// 2. Immutable Generated Assets
model WordAsset {
  id              String      @id @default(uuid())
  word_id         String
  word            Word        @relation(fields: [word_id], references: [id])
  
  // Stored exactly as validated from the LLMs
  prompt1_data    Json        // Ground Truth Sentences & Defs
  prompt2_data    Json?       // Lexical/Semantic Exercises
  prompt3_data    Json?       // Structural Exercises
  
  status          String      @default("PENDING_VALIDATION") // "ACTIVE", "FLAGGED", "RETIRED"
  generated_at    DateTime    @default(now())
  generator_models String     // e.g., "p1:gemini-2.5-flash|p2,3:claude-3.5-sonnet"
}

// 3. User Progression State
model UserWordProgress {
  id                 String   @id @default(uuid())
  user_id            String
  word_id            String
  word               Word     @relation(fields: [word_id], references: [id])
  
  current_level      Int      @default(1) // Where they are on the 1-10 ladder
  elo_rating         Int      // User's specific proficiency rating for this word
  state              String   @default("NEW") // "LEARNING", "FRAGILE", "STABLE_RECEPTIVE", "STABLE_PRODUCTIVE"
  
  // Inter-session promotion tracking
  consecutive_correct Int     @default(0) // Resets on failure. Reaching 2 triggers promotion.
  consecutive_failed  Int     @default(0) // Resets on success. Reaching 2 triggers demotion.
  
  next_review_date   DateTime @default(now())
  
  @@unique([user_id, word_id])
}

// 4. Intra-Session Analytics
model SessionAttempt {
  id                 String   @id @default(uuid())
  user_id            String
  word_id            String
  level_attempted    Int
  
  is_first_try_correct Boolean // Crucial for ladder movement
  total_retries      Int       // How many wrong options clicked before getting it right in-session
  time_spent_ms      Int
  
  created_at         DateTime  @default(now())
}
```


***

### Part 2: JSON Validation Schemas (TypeScript \& Zod)

These schemas ensure that if Gemini or Claude hallucinates a key, returns a string instead of a boolean, or misses an option, the pipeline catches it immediately and triggers an automated retry.

```typescript
import { z } from "zod";

// --- Reusable Base Types ---
const OptionSchema = z.object({
  "1": z.string().describe("The option text"),
  "2": z.boolean().describe("True if correct, false if distractor"),
  "3": z.string().describe("Pedagogical reasoning in the target language")
});

const SentenceSchema = z.object({
  "1": z.string().describe("The full sentence text"),
  "2": z.string().describe("The exact target substring used in the sentence")
});

// --- Prompt 1: Ground Truth (Gemini 2.5 Flash Lite) ---
export const Prompt1Schema = z.object({
  "1": z.string().describe("Tier-appropriate definition"),
  "2": z.string().nullable().describe("Primary collocate, or null if N/A"),
  "3": z.array(SentenceSchema).length(6).describe("Exactly 6 correct sentences")
});

export type Prompt1Output = z.infer<typeof Prompt1Schema>;

// --- Prompt 2: Lexical & Semantic Exercises (Claude 3.5 Sonnet) ---
// All keys are optional because the backend only requests them if active for that word type.
export const Prompt2Schema = z.object({
  "1": z.array(OptionSchema).length(4).optional().describe("Phonetic flashcard options"),
  "3": z.array(OptionSchema).length(4).optional().describe("Cloze completion options"),
  "5": z.array(OptionSchema).length(4).optional().describe("Collocation gap options"),
  "6": z.array(OptionSchema).length(4).optional().describe("Semantic discrimination options")
});

export type Prompt2Output = z.infer<typeof Prompt2Schema>;

// --- Prompt 3: Grammar & Structure (Claude 3.5 Sonnet) ---
export const Prompt3Schema = z.object({
  "4": z.array(OptionSchema).length(4).optional().describe("Morphology options"),
  "7": z.object({
    "1": z.string().describe("Incorrect sentence with structural error"),
    "2": z.string().describe("Corrected sentence"),
    "3": z.string().describe("Reasoning for the grammar rule broken")
  }).optional().describe("Spot incorrect syntax"),
  "8": z.array(OptionSchema).length(4).optional().describe("Collocation repair options")
});

export type Prompt3Output = z.infer<typeof Prompt3Schema>;
```


***

### Part 3: Service Boundaries (Backend Architecture)

To ensure this pipeline is modular and doesn't turn into a monolith, isolate these four specific services.

#### 1. `PipelineOrchestratorService`

* **Responsibility:** The manager. It receives a new word, figures out what needs to be generated, calls the LLM services, validates the output, and saves it to the database.
* **Key Methods:**
    * `generateWordAssets(wordId: string)`: Main entry point.
    * `determineActiveLevels(pos: string, semanticClass: string)`: Returns array of active levels (e.g., skips 5 and 8 for concrete nouns).
    * `runValidationPipeline(rawJson: any, schema: ZodSchema)`: Parses output and triggers a retry with error injection if validation fails.


#### 2. `LLMGenerationService`

* **Responsibility:** Interacting directly with the OpenRouter/Native APIs. It handles prompt assembly and model-specific parameters (e.g., setting temperature to 0).
* **Key Methods:**
    * `callPrompt1(word, activeLevels)` -> Calls Gemini Flash.
    * `callPrompt2(word, activeLevels, p1Output)` -> Calls Claude Sonnet.
    * `callPrompt3(word, activeLevels, p1Output)` -> Calls Claude Sonnet.
    * *Note: This service dynamically strips the instructions for inactive levels from the prompt strings to save tokens and prevent hallucinations.*


#### 3. `ExerciseAssemblyService` (The Presentation Layer)

* **Responsibility:** Taking the raw stored JSON from `WordAsset` and turning it into a playable card for the frontend.
* **Key Methods:**
    * `buildLevel3Card(asset)`: Takes Sentence 1, finds the `target_substring`, replaces it with `___`, and packages it with the 4 options.
    * `buildLevel7Card(asset)`: Combines the 1 error sentence from P3 with 3 correct sentences from P1, shuffles them, and outputs a 4-option MCQ.
    * `buildLevel9Card(asset)`: Takes Sentence 6 from P1, passes it to a lightweight NLP tokenizer (e.g., `compromise` for English or `jieba` for Chinese), and returns an array of shuffled chunks for drag-and-drop.


#### 4. `ProgressionEngineService`

* **Responsibility:** Handles what happens when a user clicks an answer. Updates ELO, controls intra-session locks, and calculates spaced repetition inter-session movement.
* **Key Methods:**
    * `handleAnswerSubmission(userId, wordId, level, isCorrect, isFirstTry)`: Updates `SessionAttempt` and recalculates the user's ELO.
    * `evaluateLadderMovement(userId, wordId)`: Checks `consecutive_correct` and `consecutive_failed`. If `correct == 2`, increments `current_level`. Updates `next_review_date`.

