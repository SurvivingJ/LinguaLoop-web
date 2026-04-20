-- ============================================================================
-- Vocabulary Ladder Pipeline Schema Migration
-- Date: 2026-04-06
--
-- Creates the infrastructure for the 9-level vocabulary exercise ladder:
--   1. word_assets          — immutable LLM-generated content per word sense
--   2. user_word_ladder     — per-user per-word ladder progression state
--   3. ALTER dim_vocabulary  — add semantic_class column
--   4. ALTER dim_word_senses — add ipa_pronunciation, morphological_forms
--   5. ALTER exercises       — add word_asset_id, ladder_level
--   6. ALTER exercise_attempts — add is_first_attempt
--   7. Prompt templates for vocab asset generation
-- ============================================================================

-- ============================================================================
-- 1. word_assets — Immutable LLM output per word sense
-- ============================================================================
-- Stores the raw (remapped to descriptive keys) output from Prompts 1-3.
-- One row per (sense_id, asset_type). Never mutated after validation.
-- Exercises are rendered from these assets into the exercises table.

CREATE TABLE IF NOT EXISTS public.word_assets (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sense_id            integer NOT NULL REFERENCES public.dim_word_senses(id),
    language_id         integer NOT NULL REFERENCES public.dim_languages(id),
    asset_type          text NOT NULL CHECK (asset_type IN (
                            'prompt1_core',
                            'prompt2_exercises',
                            'prompt3_transforms'
                        )),
    content             jsonb NOT NULL,
    model_used          text NOT NULL,
    prompt_version      text NOT NULL DEFAULT 'v1',
    is_valid            boolean NOT NULL DEFAULT true,
    validation_errors   text[],
    generation_batch_id uuid,
    created_at          timestamptz NOT NULL DEFAULT now(),

    UNIQUE (sense_id, asset_type)
);

CREATE INDEX IF NOT EXISTS idx_word_assets_sense
    ON public.word_assets(sense_id);
CREATE INDEX IF NOT EXISTS idx_word_assets_batch
    ON public.word_assets(generation_batch_id)
    WHERE generation_batch_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_word_assets_valid
    ON public.word_assets(sense_id, asset_type)
    WHERE is_valid = true;

-- ============================================================================
-- 2. user_word_ladder — Per-user per-word ladder progression
-- ============================================================================
-- current_level tracks where the user is on the 1-9 ladder.
-- active_levels stores which levels apply (concrete nouns skip 5,8).
-- Computed once from semantic_class at init time, avoids recomputing on reads.

CREATE TABLE IF NOT EXISTS public.user_word_ladder (
    user_id         uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    sense_id        integer NOT NULL REFERENCES public.dim_word_senses(id),
    current_level   integer NOT NULL DEFAULT 1
                    CHECK (current_level BETWEEN 1 AND 9),
    active_levels   integer[] NOT NULL DEFAULT '{1,2,3,4,5,6,7,8,9}',
    updated_at      timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (user_id, sense_id)
);

CREATE INDEX IF NOT EXISTS idx_user_word_ladder_user
    ON public.user_word_ladder(user_id);

-- ============================================================================
-- 3. ALTER dim_vocabulary — add semantic_class
-- ============================================================================
-- Populated by Prompt 1 during asset generation.
-- Values: 'concrete_noun', 'abstract_noun', 'action_verb', 'state_verb',
--         'adjective', 'adverb', 'preposition', 'conjunction', etc.
-- Used to determine which ladder levels are active for a word.

ALTER TABLE public.dim_vocabulary
    ADD COLUMN IF NOT EXISTS semantic_class text;

-- ============================================================================
-- 4. ALTER dim_word_senses — add phonetic/morphology fields
-- ============================================================================
-- Populated by Prompt 1 during asset generation.

ALTER TABLE public.dim_word_senses
    ADD COLUMN IF NOT EXISTS ipa_pronunciation text,
    ADD COLUMN IF NOT EXISTS morphological_forms jsonb;

-- ============================================================================
-- 5. ALTER exercises — add word_asset_id and ladder_level
-- ============================================================================
-- word_asset_id links a rendered exercise back to its source asset.
-- ladder_level identifies which level (1-9) this exercise serves.
-- Non-ladder exercises have both columns NULL.

ALTER TABLE public.exercises
    ADD COLUMN IF NOT EXISTS word_asset_id bigint REFERENCES public.word_assets(id),
    ADD COLUMN IF NOT EXISTS ladder_level integer CHECK (
        ladder_level IS NULL OR (ladder_level BETWEEN 1 AND 9)
    );

-- Composite index for the hot serve path:
-- SELECT * FROM exercises WHERE word_sense_id = X AND ladder_level = Y
CREATE INDEX IF NOT EXISTS idx_exercises_ladder
    ON public.exercises(word_sense_id, ladder_level)
    WHERE ladder_level IS NOT NULL;

-- Relax the source FK constraint: ladder exercises have word_sense_id AND
-- word_asset_id both set. The old constraint required exactly 1 FK;
-- the new constraint requires at least 1 of the original FKs.
ALTER TABLE public.exercises DROP CONSTRAINT IF EXISTS chk_source_fk;
ALTER TABLE public.exercises ADD CONSTRAINT chk_source_fk CHECK (
    (grammar_pattern_id IS NOT NULL)::int +
    (word_sense_id IS NOT NULL)::int +
    (corpus_collocation_id IS NOT NULL)::int +
    (conversation_id IS NOT NULL)::int >= 1
);

-- ============================================================================
-- 6. ALTER exercise_attempts — add first-attempt tracking
-- ============================================================================
-- is_first_attempt: true for the user's first try at this exercise in a
-- session, false for retries. Only first attempts update BKT/ladder.

ALTER TABLE public.exercise_attempts
    ADD COLUMN IF NOT EXISTS is_first_attempt boolean DEFAULT true,
    ADD COLUMN IF NOT EXISTS ladder_level integer,
    ADD COLUMN IF NOT EXISTS time_taken_ms integer;

-- ============================================================================
-- 7. Prompt templates for vocabulary asset generation
-- ============================================================================

-- Deduplicate prompt_templates: keep only the newest row (highest id) per group
DELETE FROM public.prompt_templates a
USING public.prompt_templates b
WHERE a.task_name = b.task_name
  AND a.language_id = b.language_id
  AND a.version = b.version
  AND a.id < b.id;

-- Now create the unique constraint (may be missing from older migrations)
CREATE UNIQUE INDEX IF NOT EXISTS idx_prompt_templates_task_lang_ver
    ON public.prompt_templates(task_name, language_id, version);

-- Prompt 1: Core classification + sentences (Gemini Flash)
INSERT INTO public.prompt_templates (task_name, language_id, version, template_text, is_active)
VALUES (
    'vocab_prompt1_core',
    2,  -- English
    1,
    $PROMPT$Role: Expert computational linguist generating English vocabulary assets.

Target word: {word}
Existing definition: {existing_definition}
Learner tier: {complexity_tier}

Corpus sentences already approved (use these unchanged):
{corpus_sentences_json}

Task: Generate the base linguistic assets for this vocabulary word.

Rules:
1. All output values must be in English only.
2. Return the part of speech as one of: noun, verb, adjective, adverb, preposition, conjunction, pronoun, determiner, interjection.
3. Return the semantic class as one of: concrete_noun, abstract_noun, action_verb, state_verb, adjective, adverb, other.
4. Return a definition suitable for the learner tier. If an existing definition is provided and adequate, reuse it.
5. Return the primary collocate for this word if one is strongly relevant; otherwise return null.
6. Return exactly 6 correct example sentences total. Use the provided corpus sentences unchanged. Generate exactly {sentences_needed} additional sentences so the total is 6.
7. Every sentence must place the word in a meaningfully different context or sentence structure.
8. For each sentence, return the exact substring used for the target word as it appears in that sentence.
9. Return the IPA pronunciation.
10. Return the syllable count.
11. Return 3-5 morphological forms with labels (e.g. past_tense, plural, comparative).
12. Output valid JSON only using numeric keys.

Output schema:
"1" = part_of_speech (string)
"2" = semantic_class (string)
"3" = definition (string)
"4" = primary_collocate (string or null)
"5" = pronunciation (string, natural reading)
"6" = ipa (string)
"7" = syllable_count (integer)
"8" = array of sentence objects, each: {"1": full_sentence, "2": exact_target_substring, "3": source ("corpus" or "generated"), "4": complexity_tier}
"9" = array of morphological form objects, each: {"1": form_text, "2": form_label}$PROMPT$,
    true
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- Prompt 2: Lexical & semantic exercises (Claude Sonnet)
INSERT INTO public.prompt_templates (task_name, language_id, version, template_text, is_active)
VALUES (
    'vocab_prompt2_exercises',
    2,  -- English
    1,
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

Level "1" (Phonetic/Orthographic Recognition):
- Return 4 options. 1 correct = target word. 3 distractors look or sound similar.
- Distractors must NOT be semantic synonyms. Only form similarity.

Level "3" (Cloze Completion):
- Use sentence at index {level_3_sentence_index}.
- Correct option = the target substring from that sentence.
- 3 distractors: same POS, grammatically valid in context, but contextually wrong.

Level "5" (Collocation Gap Fill) — only if included:
- Use sentence at index {level_5_sentence_index}.
- Correct option = the primary collocate.
- 3 distractors: semantically close but collocationally unnatural with the target word.

Level "6" (Semantic Discrimination):
- Use sentence at index {level_6_sentence_index} as the correct usage.
- Generate 3 new sentences using the target word that are grammatical but semantically or pragmatically inappropriate.

Output schema:
Top-level keys are level numbers as strings.
Each level value is an array of 4 option objects: [{"1": text, "2": bool, "3": explanation}, ...]
Exception: Level "6" value is {"1": correct_sentence_index, "2": array of 3 wrong sentence objects [{"1": text, "2": explanation}, ...]}$PROMPT$,
    true
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- Prompt 3: Grammar & structure exercises (Claude Sonnet)
INSERT INTO public.prompt_templates (task_name, language_id, version, template_text, is_active)
VALUES (
    'vocab_prompt3_transforms',
    2,  -- English
    1,
    $PROMPT$Role: Expert computational linguist generating English grammar and usage exercises.

Target word: {word}
Part of speech: {pos}
Semantic class: {semantic_class}
Tier: {complexity_tier}
Primary collocate: {primary_collocate}

Base sentences:
{sentences_json}

Morphological forms available:
{morphological_forms_json}

Generate ONLY the exercise levels listed here: {active_levels_json}

Rules:
1. All output values must be in English only.
2. Output valid JSON only using numeric keys.
3. For option objects: "1" = text, "2" = true/false, "3" = explanation.

Level "4" (Morphology Slot):
- Use sentence at index {level_4_sentence_index}.
- Correct option = the exact target substring (an inflected form).
- "4" = base_form, "5" = form_label (e.g. "past_tense").
- 3 distractors: real morphological siblings that are wrong for this sentence context.

Level "7" (Spot Incorrect Sentence):
- Use sentences at indices {level_7_correct_indices} as 3 correct sentences.
- Generate 1 new sentence containing a common learner-like structural error with the target word spelled correctly.
- "1" = incorrect_sentence, "2" = corrected_sentence, "3" = error_description.

Level "8" (Collocation Repair) — only if included:
- Use sentence at index {level_8_sentence_index}.
- Replace the correct collocate with an unnatural-but-plausible substitute.
- Correct option = the real collocate. 3 distractors = unnatural substitutions.

Output schema:
Top-level keys are level numbers as strings.
Level "4": array of 4 option objects + "4": base_form + "5": form_label + "6": sentence_index
Level "7": {"1": incorrect_sentence, "2": corrected_sentence, "3": error_description, "4": array of correct_sentence_indices}
Level "8": array of 4 option objects + "4": sentence_index + "5": error_collocate$PROMPT$,
    true
)
ON CONFLICT (task_name, language_id, version) DO NOTHING;

-- ============================================================================
-- 8. Add vocab pipeline model columns to dim_languages
-- ============================================================================

ALTER TABLE public.dim_languages
    ADD COLUMN IF NOT EXISTS vocab_prompt1_model text,
    ADD COLUMN IF NOT EXISTS vocab_prompt2_model text,
    ADD COLUMN IF NOT EXISTS vocab_prompt3_model text;

-- Set defaults for English
UPDATE public.dim_languages
SET vocab_prompt1_model = 'google/gemini-2.5-flash-lite',
    vocab_prompt2_model = 'anthropic/claude-sonnet-4-6',
    vocab_prompt3_model = 'anthropic/claude-sonnet-4-6'
WHERE language_code = 'en';
