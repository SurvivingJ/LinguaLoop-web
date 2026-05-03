-- ============================================================================
-- Restrict L5 collocation eligibility & guarantee L8 sentence coverage
-- Date: 2026-05-03
--
-- Two prompt-side changes that pair with code changes shipped at the same
-- time (services/vocabulary_ladder/asset_pipeline.py and
-- services/vocabulary_ladder/asset_generators/prompt3_transforms.py):
--
--   1. P1 Rule 7 tightened: return primary_collocate ONLY for fixed lexical
--      collocations, not merely frequent co-occurrences. This stops words
--      like "personalize" from emitting "advertising" as a collocate when
--      really almost any marketing-domain noun fits.
--
--   2. P1 Rule 12-bis added: when primary_collocate is non-null, at least
--      one of the 10 sentences must contain that exact collocate as a whole
--      word. This guarantees L8 has a viable sentence to anchor to and
--      removes the "skip L8 because sentence index 4 doesn't contain the
--      collocate" failure mode.
--
-- Versions:
--   vocab_prompt1_core   v4   (deactivates v3)
--   P2 v2 and P3 v2 are unchanged.
-- ============================================================================

BEGIN;

UPDATE public.prompt_templates
SET is_active = false
WHERE task_name = 'vocab_prompt1_core' AND language_id = 2 AND version = 3;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider
)
VALUES (
    'vocab_prompt1_core',
    2,
    4,
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
7. Return the primary_collocate ONLY if the (target word, collocate) pair is a fixed lexical collocation. A fixed collocation means:
   - Swapping the collocate for a near-synonym would produce a noticeably less natural sentence in MOST contexts (e.g. "make a decision" → "do a decision" sounds wrong; "heavy rain" → "weighty rain" sounds wrong).
   - The pair appears together far more often than chance would predict.
   It is NOT enough that the collocate co-occurs frequently within a topic domain. For example "personalize" co-occurs often with "advertising", "marketing", "promotion", "publicity" — none of these are fixed collocations of "personalize" because they are interchangeable. In that situation return null.
   When in doubt, return null. False positives produce broken exercises.
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
14. Collocate sentence coverage (only when primary_collocate is non-null):
   - At least one of the 10 sentences MUST contain the primary_collocate as a free-standing whole word.
   - Prefer to place it in 2–3 of the 10 sentences so downstream exercises have flexibility.
   - If no natural sentence using both target and primary_collocate together can be written within the tier constraints, return null for primary_collocate instead.
15. Return the pronunciation as a natural reading string.
16. Return the IPA pronunciation as a standard broad dictionary-style transcription.
17. Return the syllable count as an integer.
18. Return 3–5 morphological forms with labels.
   - Use contemporary standard English forms.
   - If a form is archaic, obsolete, or dialectal, avoid it unless it is still widely recognized.
19. Create a short sense fingerprint for downstream prompts.
   - It must be a concise English string that uniquely identifies the chosen sense.
   - Format: "[part_of_speech] | [8–14 word sense summary]"
20. Pre-output verification:
   - Confirm the JSON is valid.
   - Confirm there are exactly 10 sentences.
   - Confirm every generated sentence fits the tier constraints.
   - Confirm no sentence violates the whole-word rule.
   - If primary_collocate is non-null, confirm at least one sentence contains it as a whole word.

Output schema:
"1" = part_of_speech (string)
"2" = semantic_class (string)
"3" = definition (string)
"4" = primary_collocate (string or null) — null is the safe default; only emit a string for genuine fixed collocations per Rule 7
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
    true,
    'google/gemini-2.5-flash-lite',
    'openrouter'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- Backfill model/provider on the v4 row in case an earlier (model-less)
-- version of this migration has already been applied. Idempotent.
UPDATE public.prompt_templates
SET model = 'google/gemini-2.5-flash-lite',
    provider = 'openrouter'
WHERE task_name = 'vocab_prompt1_core'
  AND language_id = 2
  AND version = 4
  AND (model IS NULL OR provider IS NULL);

-- ============================================================================
-- Verification (run manually after migration)
-- ============================================================================
-- SELECT task_name, version, is_active
-- FROM public.prompt_templates
-- WHERE task_name = 'vocab_prompt1_core' AND language_id = 2
-- ORDER BY version;

COMMIT;
