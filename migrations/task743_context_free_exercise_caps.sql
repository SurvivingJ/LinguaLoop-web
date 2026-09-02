-- TASK-743 (plan §3d, T3d.1 / T3d.2) — classify exercise types by context
-- class, and stop context-free duplicates being re-minted.
--
-- Schema and constraints only. The one-off cleanup of existing duplicates is
-- a separate file: task743_dedupe_context_free_exercises.sql.
--
-- ORDER MATTERS. Section 2 below creates a unique index that cannot be built
-- while the 245 existing duplicates are still active, so run the dedupe file
-- FIRST. If this migration fails on "could not create unique index", that is
-- what it is telling you — it is a loud, safe failure, not a corrupted state.
--
-- Background. Exercise types split in two:
--
--   context-bearing  the item is anchored to a sentence, so every variant is a
--                    genuinely different question (each is mined from a
--                    different source passage). Supply-limited; never capped.
--   context-free     the item is a property of the word itself. A word has one
--                    tone; two tone_id_word rows for it are byte-identical,
--                    and two hanzi_to_pinyin rows are the same four options in
--                    a different order — and option order is a render-time
--                    concern (see T3d.3).
--
-- Measured on live content: 245 surplus context-free rows, of which 138 were
-- definition_match. They arise because the ladder renderer builds the
-- deterministic types once per A/B asset variant and both variants resolve to
-- the same word.
--
-- The cap is per (word_sense_id, exercise_type, context anchor) — NOT per
-- word. Capping per word would delete whole skill types: 做 (zuò) carries 33
-- exercises across 12 genuinely distinct skills.

BEGIN;

-- ---------------------------------------------------------------------
-- 1. T3d.1 — the classification, on its natural home
-- ---------------------------------------------------------------------

ALTER TABLE public.dim_exercise_types
    ADD COLUMN IF NOT EXISTS context_class text;

UPDATE public.dim_exercise_types SET context_class = 'context_free'
WHERE type_code IN (
    'tone_id_word', 'hanzi_to_pinyin', 'pinyin_to_hanzi',
    'kanji_to_reading', 'reading_to_kanji', 'phonetic_recognition',
    'classifier_match', 'counter_match',
    -- Context-free with respect to the target word, but their distractors are
    -- drawn from other words, so a second variant is a second question. Capped
    -- at 2 rather than 1 by the application; see the index note below.
    'definition_match', 'synonym_antonym_match'
);

UPDATE public.dim_exercise_types SET context_class = 'context_bearing'
WHERE type_code IN (
    'cloze_completion', 'cloze_typed', 'text_flashcard', 'listening_flashcard',
    'tl_nl_translation', 'nl_tl_translation', 'jumbled_sentence',
    'semantic_discrimination', 'spot_incorrect_sentence', 'spot_incorrect_part',
    'collocation_gap_fill', 'collocation_repair', 'morphology_slot',
    'particle_selection', 'word_family'
);

UPDATE public.dim_exercise_types SET context_class = 'not_sense_anchored'
WHERE type_code IN ('timed_speed_round');

-- Anything added later without a classification defaults to context-bearing —
-- the safe direction, since it means "leave it alone" rather than "cap to one".
UPDATE public.dim_exercise_types SET context_class = 'context_bearing'
WHERE context_class IS NULL;

ALTER TABLE public.dim_exercise_types
    ALTER COLUMN context_class SET NOT NULL,
    ALTER COLUMN context_class SET DEFAULT 'context_bearing';

ALTER TABLE public.dim_exercise_types
    DROP CONSTRAINT IF EXISTS dim_exercise_types_context_class_check;
ALTER TABLE public.dim_exercise_types
    ADD CONSTRAINT dim_exercise_types_context_class_check
    CHECK (context_class IN
           ('context_free', 'context_bearing', 'not_sense_anchored'));

COMMENT ON COLUMN public.dim_exercise_types.context_class IS
    'context_free: one meaningful question per word (capped per sense+type). '
    'context_bearing: anchored to a sentence, every variant differs '
    '(supply-limited, uncapped). not_sense_anchored: not tied to one sense. '
    'Mirrored in Python by vocabulary_ladder.config.EXERCISE_TYPE_CONTEXT_CLASS.';

-- ---------------------------------------------------------------------
-- 2. T3d.2 — the constraint
-- ---------------------------------------------------------------------

-- One active item per (sense, type, context anchor) for the cap-1 types.
--
-- The anchor is what keeps the single legitimate exception alive:
-- hanzi_to_pinyin / kanji_to_reading (and their reverses) store a
-- `context_sentence` for polyphonic words, where the reading genuinely depends
-- on the sentence. Two readings in two sentences are two real questions. Every
-- other context-free type leaves the key absent, so all its items share the
-- empty anchor and collapse to one.
--
-- definition_match and synonym_antonym_match are deliberately NOT in this
-- index: their cap is 2, which a unique index cannot express. The application
-- check in services/vocabulary_ladder/exercise_caps.py enforces those. This
-- index is the backstop for the types where a duplicate is unambiguously waste.
--
-- Partial on is_active so deactivating an item frees its slot for a
-- regenerated replacement.
CREATE UNIQUE INDEX IF NOT EXISTS uq_exercises_context_free_variant
    ON public.exercises (
        word_sense_id,
        exercise_type,
        md5(coalesce(content->>'context_sentence', ''))
    )
    WHERE is_active
      AND word_sense_id IS NOT NULL
      AND exercise_type IN (
          'tone_id_word', 'hanzi_to_pinyin', 'pinyin_to_hanzi',
          'kanji_to_reading', 'reading_to_kanji', 'phonetic_recognition',
          'classifier_match', 'counter_match'
      );

COMMIT;
