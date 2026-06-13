-- ============================================================================
-- Fix dim_exercise_types.family mis-mappings + register the new type taxonomy
-- Date: 2026-06-13
-- Task: TASK-503 (wiki/tasklist/exercise-generation-v2.tasks.md); plan §5.
--
-- Live rows mis-mapped legacy types (cloze->collocation, jumbled->collocation,
-- listening_flashcard->meaning_recall, definition_match->meaning_recall,
-- spot_incorrect_*->meaning_recall), so Acquisition-mode family targeting
-- mis-drills (finding G4). This corrects every row to the §5 Family column and
-- inserts the 12 new type_codes with realistic expected_seconds.
--
-- timed_speed_round uses the §5 "fluency" family — a non-BKT family (ladder_level
-- NULL; does not feed family confidence / p_known). The family CHECK is extended
-- additively to permit it. (The dim_exercise_types_family_check constraint was
-- first defined in phase12_dim_exercise_types.sql, which remains the table's
-- canonical record; this file is the newest definer of that one constraint.)
--
-- Idempotent: keyed UPDATEs (fixed targets), DROP CONSTRAINT IF EXISTS before
-- re-ADD, and INSERT ... ON CONFLICT (type_code) DO NOTHING.
-- ============================================================================

-- 1. Correct mis-mapped families on the existing rows (keyed, idempotent).
UPDATE public.dim_exercise_types SET family = 'meaning_recall'          WHERE type_code = 'cloze_completion';
UPDATE public.dim_exercise_types SET family = 'form_recognition'        WHERE type_code = 'definition_match';
UPDATE public.dim_exercise_types SET family = 'form_production'         WHERE type_code = 'jumbled_sentence';
UPDATE public.dim_exercise_types SET family = 'form_recognition'        WHERE type_code = 'listening_flashcard';
UPDATE public.dim_exercise_types SET family = 'semantic_discrimination' WHERE type_code = 'spot_incorrect_sentence';
-- spot_incorrect_part: legacy comprehension-test variant, not in §5; mapped
-- alongside its sentence sibling.
UPDATE public.dim_exercise_types SET family = 'semantic_discrimination' WHERE type_code = 'spot_incorrect_part';

-- 2. Permit the 'fluency' family (timed_speed_round, §5 #21). Additive.
ALTER TABLE public.dim_exercise_types DROP CONSTRAINT IF EXISTS dim_exercise_types_family_check;
ALTER TABLE public.dim_exercise_types ADD CONSTRAINT dim_exercise_types_family_check
    CHECK (family = ANY (ARRAY[
        'form_recognition', 'meaning_recall', 'form_production',
        'collocation', 'semantic_discrimination', 'contextual_use', 'fluency'
    ]));

-- 3. Register the 12 new exercise types (§5). expected_seconds: readings/tone
--    ~15s, speed-round ~8s, everything else ~45s.
INSERT INTO public.dim_exercise_types (type_code, family, expected_seconds) VALUES
    ('cloze_typed',           'form_production',         45),
    ('classifier_match',      'form_production',         45),
    ('particle_selection',    'form_production',         45),
    ('counter_match',         'form_production',         45),
    ('hanzi_to_pinyin',       'form_recognition',        15),
    ('kanji_to_reading',      'form_recognition',        15),
    ('pinyin_to_hanzi',       'form_recognition',        15),
    ('reading_to_kanji',      'form_recognition',        15),
    ('tone_id_word',          'form_recognition',        15),
    ('synonym_antonym_match', 'semantic_discrimination', 45),
    ('word_family',           'form_production',         45),
    ('timed_speed_round',     'fluency',                  8)
ON CONFLICT (type_code) DO NOTHING;
