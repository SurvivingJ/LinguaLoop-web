-- ============================================================================
-- Reframe English L1 in vocab_prompt2_exercises as listening-only.
-- Date: 2026-05-07
--
-- L1 is rendered as an audio-then-MCQ listening exercise (renderer at
-- services/vocabulary_ladder/exercise_renderer.py:155 returns word, pronunciation,
-- ipa, options — frontend plays the audio and shows written options). The v2
-- prompt described it as "Phonetic/Orthographic Recognition" and instructed
-- the LLM to pick distractors that "look or sound similar" via "form
-- similarity". For a listening test, visual similarity is the wrong axis:
-- "tough" and "though" look almost identical but sound completely different,
-- so they make a useless audio distractor pair.
--
-- v3 reframes L1 as listening-only with phonetically-confusable distractors
-- (homophones, near-homophones, minimal pairs). All other levels (L3, L5, L6)
-- are unchanged.
--
-- Pairs with the analogous Chinese decision (CN P2 v1 in
-- migrations/seed_chinese_vocab_prompts.sql also restricts L1 distractors to
-- audio confusables — tonal confusables in that case).
-- ============================================================================

BEGIN;

UPDATE public.prompt_templates
SET is_active = false
WHERE task_name = 'vocab_prompt2_exercises'
  AND language_id = 2
  AND version = 2;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider
)
VALUES (
    'vocab_prompt2_exercises',
    2,
    3,
    $PROMPT$Role: Expert computational linguist generating English vocabulary exercises.

Target word: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Tier: {complexity_tier}
Definition: {definition}
Primary collocate: {primary_collocate}

Base sentences:
{sentences_json}

Generate ONLY the exercise levels listed here: {active_levels_json}

Rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. For every option: "1" = option text, "2" = true/false (correct?), "3" = explanation.
4. Explanations must be short, clear, and pedagogical.
5. Treat the target word as a discrete whole word. Never confuse it with a longer word that merely contains its letters (e.g. for the target "new", do NOT use "knew", "renew", or "renewal" anywhere in Level 3, Level 5, or Level 6 sentences or distractors).

Level "1" (Listening Recognition):
- Scenario: the learner HEARS the target word spoken aloud (TTS) and must select which of 4 written options matches what they heard.
- Return 4 options. 1 correct = the target word as it would naturally be written. 3 distractors are PHONETICALLY confusable with the target by ear.
- Use a mix of at least two of these phonetic-distractor types:
  * Homophones / near-homophones (e.g. for "their": "there", "they're"; for "knew": "new", "gnu"; for "to": "too", "two")
  * Minimal pairs differing by one phoneme (e.g. for "ship": "sheep", "chip", "shop"; for "ride": "rode", "raid")
  * Same-stress same-syllable-count rhymes a learner could plausibly mishear (e.g. for "cat": "cap", "cab"; for "thing": "think", "thin")
- Hard rules for L1 distractors:
  * Each distractor MUST be a real English word.
  * Distractors MUST NOT be selected on visual/spelling similarity alone. "tough" and "though" look alike but sound completely different — they are NOT valid L1 distractors for each other.
  * Distractors MUST NOT be semantic synonyms of the target.
  * Distractors MUST NOT be the target word itself with a different inflection (e.g. "ran" is not a valid distractor for "run").
- L1 is the only level where homophones/near-homophones of the target are permitted as distractors.
- For each option, "3" (explanation) briefly states the phonetic relationship to the target — e.g. "homophone: same /ðeə/ sound, different spelling and meaning" or "minimal pair: differs only in /ɪ/ vs /iː/" or "rhymes with target but starts with a different consonant".

Level "3" (Cloze Completion):
- Use sentence at index {level_3_sentence_index}.
- Correct option = the target word as it appears in that sentence (its exact inflected form).
- 3 distractors: same POS, grammatically valid in context, but contextually wrong.
- Do NOT use any homophone or near-homophone of the target as a distractor here.

Level "5" (Collocation Gap Fill) — only if included:
- Use sentence at index {level_5_sentence_index}.
- Correct option = the primary collocate.
- 3 distractors: semantically close but collocationally unnatural with the target word.

Level "6" (Semantic Discrimination):
- Use sentence at index {level_6_sentence_index} as the correct usage.
- Generate 3 new sentences using the target word that are grammatical but semantically or pragmatically inappropriate.
- Each new sentence MUST contain the target word as a whole word, never embedded in another word.

Output schema:
Top-level keys are level numbers as strings.
Each level value is an array of 4 option objects: [{"1": text, "2": bool, "3": explanation}, ...]
Exception: Level "6" value is {"1": correct_sentence_index, "2": array of 3 wrong sentence objects [{"1": text, "2": explanation}, ...]}$PROMPT$,
    true,
    'anthropic/claude-opus-4-7',
    'openrouter'
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- Idempotent backfill in case a re-apply or partial-apply state leaves
-- model/provider null.
UPDATE public.prompt_templates
SET model = 'anthropic/claude-opus-4-7',
    provider = 'openrouter'
WHERE task_name = 'vocab_prompt2_exercises'
  AND language_id = 2
  AND version = 3
  AND (model IS NULL OR provider IS NULL);

-- ============================================================================
-- Verification (run manually after migration)
-- ============================================================================
-- SELECT version, is_active, model, provider, char_length(template_text) AS len
-- FROM public.prompt_templates
-- WHERE task_name = 'vocab_prompt2_exercises' AND language_id = 2
-- ORDER BY version;

COMMIT;
