-- ============================================================================
-- Improve Vocabulary Ladder Pipeline Prompts
-- Date: 2026-05-03
--
-- Replaces the three vocab pipeline prompt templates with revisions that add:
--   - Tier calibration tables (T1–T6 → hard sentence-level constraints)
--   - Sense lock + sense_fingerprint propagation across P1 → P2 → P3
--   - Register lock (formal / neutral / informal / technical)
--   - Mandatory whole-word substring audit
--   - Mixed-L1 guardrail (no false-friend / transfer-error distractors)
--   - used_distractors_json deduping across an item set
--   - Pre-output verification rules
--   - Stronger L1 distractor rules (Levenshtein, first/last letter, homophones)
--   - L8 anti-substitution test
--   - Two new P1 output fields: register ("10") and sense_fingerprint ("11")
--
-- Versions inserted:
--   vocab_prompt1_core         v3   (deactivates v2)
--   vocab_prompt2_exercises    v2   (deactivates v1)
--   vocab_prompt3_transforms   v2   (deactivates v1)
--
-- Required code changes (must be deployed alongside this migration):
--   - services/vocabulary_ladder/config.py:
--       PROMPT1_KEY_MAP gains "10": "register", "11": "sense_fingerprint"
--   - services/vocabulary_ladder/asset_generators/prompt1_core.py:
--       _build_prompt passes {sense_id} and {sense_definition}
--   - services/vocabulary_ladder/asset_generators/prompt2_exercises.py:
--       _build_prompt passes {register}, {sense_fingerprint}, {used_distractors_json}
--   - services/vocabulary_ladder/asset_generators/prompt3_transforms.py:
--       _build_prompt passes {register}, {sense_fingerprint}, {used_distractors_json}
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Deactivate the currently-active rows
-- ============================================================================

UPDATE public.prompt_templates
SET is_active = false
WHERE task_name = 'vocab_prompt1_core' AND language_id = 2 AND version = 2;

UPDATE public.prompt_templates
SET is_active = false
WHERE task_name = 'vocab_prompt2_exercises' AND language_id = 2 AND version = 1;

UPDATE public.prompt_templates
SET is_active = false
WHERE task_name = 'vocab_prompt3_transforms' AND language_id = 2 AND version = 1;

-- ============================================================================
-- 2. Prompt 1 v3 — Core Asset Generator
-- ============================================================================

INSERT INTO public.prompt_templates (task_name, language_id, version, template_text, is_active)
VALUES (
    'vocab_prompt1_core',
    2,
    3,
    $PROMPT$Role: Expert computational linguist generating English vocabulary assets.

Target word: {word}
Existing definition: {existing_definition}
Sense ID (optional): {sense_id}
Sense definition (optional): {sense_definition}
Learner tier: {complexity_tier}

Corpus sentences already approved (use these unchanged):
{corpus_sentences_json}

Task: Generate the base linguistic assets for this vocabulary word for exactly one sense only.

Tier calibration (mandatory)
Map {complexity_tier} to these hard constraints. Do not exceed them in generated learner-facing text.

| Tier | Name | Age Analog | Max sentence length | Tense/aspect ceiling | Topic/context register | Abstract language |
|------|------|------------|---------------------|----------------------|------------------------|-------------------|
| 1 | The Toddler | 4–5 | 12 words | Simple present/past only | Home, animals, food, concrete actions | Forbidden |
| 2 | The Primary Schooler | 8–9 | 18 words | Future simple allowed | School, family, hobbies, familiar places | Forbidden |
| 3 | The Young Teen | 13–14 | 25 words | Present/past continuous, perfect simple | Emotions, opinions, social events | Minimal |
| 4 | The High Schooler | 16–17 | 35 words | All perfects, passive, first/second conditional | Academic, media, abstract social issues | Allowed |
| 5 | The Uni Student | 19–21 | 45 words | Modals, embedded clauses, inversion | University, professional, technical | Expected |
| 6 | The Educated Professional | 30+ | No hard cap | Any structure including rare patterns | Technical, literary, highly nuanced | Full range |

Hard rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. Return the part of speech as one of:
   noun, verb, adjective, adverb, preposition, conjunction, pronoun, determiner, interjection
4. Return the semantic class as one of:
   concrete_noun, abstract_noun, action_verb, state_verb, adjective, adverb, other
5. Sense lock:
   - Generate assets for exactly ONE sense only.
   - If {sense_id} or {sense_definition} is provided, lock to that sense.
   - Otherwise infer the sense from the approved corpus sentences.
   - If the corpus sentences mix senses, use the majority sense and keep all generated content aligned to it.
6. Return a definition suitable for the learner tier.
   - If {existing_definition} is provided and is adequate for the chosen sense and tier, reuse it.
   - If not adequate, rewrite it in simpler or more precise English while preserving the same sense.
7. Return the primary collocate for this word if one is strongly relevant for the chosen sense; otherwise return null.
8. Determine the register of the chosen sense as one of:
   formal, neutral, informal, technical
9. Return exactly 10 correct example sentences total.
   - Use the provided corpus sentences unchanged.
   - Generate exactly {sentences_needed} additional sentences so the total is 10.
10. All 10 sentences must:
   - express the SAME sense of the word;
   - fit the learner tier;
   - respect the register identified in Rule 8.
11. Syntactic frame diversity mandate:
   - Across all 10 sentences, the target word must appear in at least three distinct grammatical roles or frames.
   - No more than four sentences may use an identical frame.
12. For each sentence, return the exact target word as it appears in that sentence.
   - It must be a whole word only, never a substring of another word.
   - Match case and inflection exactly as written in the sentence.
13. Substring audit (mandatory verification):
   - Before returning output, verify that every sentence uses the target as a free-standing whole word.
   - If the target is "new", then "knew", "renew", and "renewal" do NOT count.
   - Reject and regenerate any violating sentence.
14. Return the pronunciation as a natural reading string.
15. Return the IPA pronunciation as a standard broad dictionary-style transcription.
16. Return the syllable count as an integer.
17. Return 3–5 morphological forms with labels.
   - Use contemporary standard English forms.
   - If a form is archaic, obsolete, or dialectal, avoid it unless it is still widely recognized.
18. Create a short sense fingerprint for downstream prompts.
   - It must be a concise English string that uniquely identifies the chosen sense.
   - Format: "[part_of_speech] | [8–14 word sense summary]"
19. Pre-output verification:
   - Confirm the JSON is valid.
   - Confirm there are exactly 10 sentences.
   - Confirm every generated sentence fits the tier constraints.
   - Confirm no sentence violates the whole-word rule.

Output schema:
"1" = part_of_speech (string)
"2" = semantic_class (string)
"3" = definition (string)
"4" = primary_collocate (string or null)
"5" = pronunciation (string, natural reading)
"6" = ipa (string)
"7" = syllable_count (integer)
"8" = array of sentence objects, each:
      "1": full_sentence, "2": exact_target_word, "3": source ("corpus" or "generated"), "4": complexity_tier
"9" = array of morphological form objects, each:
      "1": form_text, "2": form_label
"10" = register (string: formal / neutral / informal / technical)
"11" = sense_fingerprint (string)

Return JSON only. No prose, no markdown fences.

Literal JSON template:
{
  "1": "",
  "2": "",
  "3": "",
  "4": null,
  "5": "",
  "6": "",
  "7": 0,
  "8": [
    {"1": "", "2": "", "3": "corpus", "4": ""},
    {"1": "", "2": "", "3": "generated", "4": ""}
  ],
  "9": [
    {"1": "", "2": ""}
  ],
  "10": "",
  "11": ""
}$PROMPT$,
    true
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- ============================================================================
-- 3. Prompt 2 v2 — Lexical & Semantic Exercises
-- ============================================================================

INSERT INTO public.prompt_templates (task_name, language_id, version, template_text, is_active)
VALUES (
    'vocab_prompt2_exercises',
    2,
    2,
    $PROMPT$Role: Expert computational linguist generating English vocabulary exercises.

Target word: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Tier: {complexity_tier}
Definition: {definition}
Primary collocate: {primary_collocate}
Register: {register}
Sense fingerprint: {sense_fingerprint}

Base sentences:
{sentences_json}

Generate ONLY the exercise levels listed here:
{active_levels_json}

Used distractors already assigned elsewhere in this item set:
{used_distractors_json}

Sentence indexing note:
- All referenced sentence indices are exactly as provided by the calling system.

Tier calibration (mandatory)
All learner-facing text you generate must fit the tier.

| Tier | Name | Age Analog | New sentence difficulty | Explanation difficulty |
|------|------|------------|--------------------------|------------------------|
| 1 | The Toddler | 4–5 | very short, concrete only | 4–8 words |
| 2 | The Primary Schooler | 8–9 | short, familiar contexts | 5–10 words |
| 3 | The Young Teen | 13–14 | moderate length, basic abstraction | 6–14 words |
| 4 | The High Schooler | 16–17 | more complex syntax, abstract themes | 8–18 words |
| 5 | The Uni Student | 19–21 | nuanced academic/professional language | 8–24 words |
| 6 | The Educated Professional | 30+ | full range, subtle distinctions allowed | 8–30 words |

Global rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. For every option object:
   - "1" = option text
   - "2" = true/false
   - "3" = short pedagogical explanation
4. Mixed-L1 guardrail:
   - This system serves mixed-L1 cohorts.
   - Do NOT rely on L1-specific false friends, transfer patterns, or culturally narrow assumptions.
5. Sense lock:
   - Every exercise must match {sense_fingerprint}.
   - Do not generate distractors or wrong examples that depend on a different sense.
6. Register lock:
   - Respect {register} in all normal items.
   - Only Level 6 may deliberately violate register for pragmatic misuse.
7. Treat the target word as a discrete whole word.
   - Apply a whole-word boundary check mentally before returning output.
8. If a level is not included in {active_levels_json}, omit it entirely.
9. Do not reuse any distractor present in {used_distractors_json}.
10. Do not repeat the same distractor across multiple levels in this response.
11. Explanations must teach the learner why the answer is correct or wrong.
12. Do not use bare synonyms of the target as distractors unless the level allows form-similar items.
13. Do not use antonyms as distractors for Tier 1 or Tier 2.
14. Pre-output verification:
   a. Exactly one option per multiple-choice level has "2": true.
   b. No distractor is duplicated.
   c. No distractor violates the whole-word rule.

Level "1" (Phonetic/Orthographic Recognition):
- Return 4 options total.
- Exactly 1 correct option = the target word.
- Exactly 3 distractors must be form-similar only.
- Distractors must satisfy at least ONE of these criteria:
  (i) Levenshtein edit distance of 1 or 2 from the target;
  (ii) same first and last letter as the target;
  (iii) homophone or near-homophone in standard English.
- Distractors must NOT be semantic synonyms, antonyms, or translation equivalents.
- Level 1 is the only level where homophones or near-homophones are allowed.

Level "3" (Cloze Completion):
- Use sentence at index {level_3_sentence_index}.
- Correct option = the target word exactly as it appears in that sentence, including inflection.
- Return 4 options total.
- 3 distractors must:
  - be the same part of speech as the correct answer;
  - be grammatically valid in the sentence;
  - be contextually wrong.
- Anti-substitution test:
  - If replacing the target with a close synonym would make the distractor also sound natural, reject that distractor.
- Do NOT use homophones or near-homophones of the target.

Level "5" (Collocation Gap Fill) — only if included:
- Use sentence at index {level_5_sentence_index}.
- Correct option = the primary collocate.
- Return 4 options total.
- 3 distractors must:
  - be the same part of speech as the correct collocate;
  - be semantically near enough to tempt a learner;
  - be collocationally unnatural with the target word in this sentence.
- Distractor explanations must say specifically why the pairing is unnatural.
- If {primary_collocate} is null, omit Level 5 even if requested.

Level "6" (Semantic Discrimination):
- Use sentence at index {level_6_sentence_index} as the correct usage.
- Generate 3 new wrong sentences that all contain the target word as a whole word.
- The 3 wrong sentences must be grammatical, but semantically or pragmatically inappropriate.
- At least 1 must be semantically inappropriate (factually or logically impossible).
- At least 1 must be pragmatically inappropriate (wrong register, social fit, or usage norm).
- Each wrong sentence explanation must label the misuse type: "semantic" or "pragmatic".

Return JSON only. No prose, no markdown fences.

Literal JSON template:
{
  "1": [
    {"1": "", "2": true, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""}
  ],
  "3": [
    {"1": "", "2": true, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""}
  ],
  "5": [
    {"1": "", "2": true, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""},
    {"1": "", "2": false, "3": ""}
  ],
  "6": {
    "1": 0,
    "2": [
      {"1": "", "2": "semantic: "},
      {"1": "", "2": "pragmatic: "},
      {"1": "", "2": ""}
    ]
  }
}$PROMPT$,
    true
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- ============================================================================
-- 4. Prompt 3 v2 — Grammar & Structure Exercises
-- ============================================================================

INSERT INTO public.prompt_templates (task_name, language_id, version, template_text, is_active)
VALUES (
    'vocab_prompt3_transforms',
    2,
    2,
    $PROMPT$Role: Expert computational linguist generating English grammar and usage exercises.

Target word: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Tier: {complexity_tier}
Primary collocate: {primary_collocate}
Register: {register}
Sense fingerprint: {sense_fingerprint}

Base sentences:
{sentences_json}

Morphological forms available:
{morphological_forms_json}

Generate ONLY the exercise levels listed here:
{active_levels_json}

Used distractors already assigned elsewhere in this item set:
{used_distractors_json}

Sentence indexing note:
- All referenced sentence indices are exactly as provided by the calling system.

Tier calibration (mandatory)
All learner-facing text must fit the tier.

| Tier | Name | Age Analog | Error subtlety |
|------|------|------------|----------------|
| 1 | The Toddler | 4–5 | very obvious |
| 2 | The Primary Schooler | 8–9 | obvious |
| 3 | The Young Teen | 13–14 | moderate |
| 4 | The High Schooler | 16–17 | moderately subtle |
| 5 | The Uni Student | 19–21 | subtle |
| 6 | The Educated Professional | 30+ | very subtle |

Global rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. For option objects: "1" = text, "2" = true/false, "3" = explanation.
4. Mixed-L1 guardrail:
   - This system serves mixed-L1 cohorts.
   - Do NOT use L1-specific transfer errors or false-friend traps.
5. Sense lock:
   - All exercises must align with {sense_fingerprint}.
6. Register lock:
   - Normal items must respect {register}.
   - An incorrect sentence may violate grammar, but it must still be plausible.
7. Treat the target word as a discrete whole word.
8. Do not reuse any distractor present in {used_distractors_json}.
9. If a level is not included in {active_levels_json}, omit it entirely.

Level "4" (Morphology Slot):
- Use sentence at index {level_4_sentence_index}.
- Correct option = the exact target word as it appears in that sentence.
- Return 4 options total.
- 3 distractors must be real morphological siblings of the SAME lemma.
- Distractors must be wrong for this exact sentence context.
- Required metadata keys attached to the level object (not the options):
  - "4" = base_form
  - "5" = form_label
  - "6" = sentence_index

Level "7" (Spot Incorrect Sentence):
- Use sentences at indices {level_7_correct_indices} as 3 correct sentences.
- Generate 1 new incorrect sentence containing the target word spelled correctly.
- The incorrect sentence must contain exactly ONE structural error from this whitelist:
  - article omission or misuse
  - subject-verb agreement error
  - countable/uncountable noun misuse
  - basic word order inversion
  - tense/aspect mismatch
- Scale error type by tier.
- Output keys directly on the level object:
  - "1" = incorrect_sentence
  - "2" = corrected_sentence
  - "3" = error_description
  - "4" = array of correct_sentence_indices

Level "8" (Collocation Repair) — only if included:
You are building a multiple-choice exercise that tests whether a learner knows the natural collocate of "{word}" in a specific sentence.

The source sentence (sentence at index {level_8_sentence_index}) is:
"{level_8_sentence_text}"

The natural, correct collocate of "{word}" in this sentence is exactly:
"{level_8_collocate_word}"

Produce 4 options for the learner:
- Option 1 (correct): the text MUST equal "{level_8_collocate_word}" character-for-character.
- Options 2, 3, 4 (distractors): three different words you generate.
- Each distractor must NOT collocate naturally with "{word}" in this sentence.
- Distractor anti-substitution test: mentally replace "{word}" with a close synonym in the sentence. If the sentence would still sound natural with that distractor, reject the distractor.

Hard rules for Level "8":
- Option 1 MUST have "2": true. The distractors have "2": false.
- Do not return a distractor identical to "{level_8_collocate_word}".
- Required metadata keys attached to the level object (not the options):
  - "4" = sentence_index
  - "5" = error_collocate (one of the distractors you generated)

Return JSON only. No prose, no markdown fences.

Literal JSON template:
{
  "4": {
    "1": [
      {"1": "", "2": true, "3": ""},
      {"1": "", "2": false, "3": ""},
      {"1": "", "2": false, "3": ""},
      {"1": "", "2": false, "3": ""}
    ],
    "4": "",
    "5": "",
    "6": 0
  },
  "7": {
    "1": "",
    "2": "",
    "3": "",
    "4": [0, 1, 2]
  },
  "8": {
    "1": [
      {"1": "", "2": true, "3": ""},
      {"1": "", "2": false, "3": ""},
      {"1": "", "2": false, "3": ""},
      {"1": "", "2": false, "3": ""}
    ],
    "4": 0,
    "5": ""
  }
}$PROMPT$,
    true
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- ============================================================================
-- 5. Verification queries (run manually after migration)
-- ============================================================================
-- SELECT task_name, language_id, version, is_active
-- FROM public.prompt_templates
-- WHERE task_name LIKE 'vocab_prompt%' AND language_id = 2
-- ORDER BY task_name, version;

COMMIT;
