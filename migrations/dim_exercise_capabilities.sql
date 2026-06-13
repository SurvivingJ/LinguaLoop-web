-- ============================================================================
-- dim_exercise_capabilities — the (language, type) routing matrix
-- Date: 2026-06-13
-- Task: TASK-504 (wiki/tasklist/exercise-generation-v2.tasks.md); plan §6.2 / §5 / §4.
--
-- One row per (language_id, type_code) declares how that exercise type behaves
-- for that language: which ratified semantic_class values it applies to
-- (pos_classes), which ladder rung it fills (ladder_level), how it is produced
-- (generator), what data it needs (requires), and which judge gates it
-- (judge_key, NULL only for deterministic generators). compute_active_levels,
-- the generation planner, and serving all read this table; adding a language or
-- type is an INSERT (audit B3.3 — the 小熊 incident is the proof).
--
-- pos_classes convention: the sentinel 'all' matches every ratified class
-- EXCEPT 'proper' (proper is never ladder-subscribed — definition-flashcard
-- only, §4). A row only applies to 'proper' if it names it explicitly.
--
-- DB-vs-spec resolution (flagged): the live dim_exercise_types had 25 rows but
-- NO 'morphology_slot' row, although it is L4's exercise_type in
-- services/vocabulary_ladder/config.py LADDER_LEVELS, is §5 #5, and is the
-- explicit example in the §6.2 DDL. TASK-503 added the 12 new types assuming
-- morphology_slot pre-existed among the original 13 (it never did). Because the
-- capability matrix FK-references dim_exercise_types(type_code), this migration
-- additively backfills that one missing row (form_production, 45s) before
-- seeding — the same additive DB-vs-spec pattern TASK-503 used for the 'fluency'
-- family CHECK. This file is the only repo definer of dim_exercise_capabilities;
-- it redefines no existing object, so no archival per migrations/CLAUDE.md.
--
-- Idempotent: CREATE TABLE IF NOT EXISTS, morphology_slot via ON CONFLICT DO
-- NOTHING, and seeds via ON CONFLICT (language_id, type_code) DO UPDATE (the
-- migration is forward-only and self-correcting — re-running re-asserts the
-- canonical matrix).
-- ============================================================================

-- 0. Backfill the missing morphology_slot type row (see header). Additive.
INSERT INTO public.dim_exercise_types (type_code, family, expected_seconds)
VALUES ('morphology_slot', 'form_production', 45)
ON CONFLICT (type_code) DO NOTHING;

-- 1. The routing matrix table (plan §6.2 DDL, verbatim columns).
CREATE TABLE IF NOT EXISTS public.dim_exercise_capabilities (
    language_id    smallint NOT NULL REFERENCES public.dim_languages(id),
    type_code      text     NOT NULL REFERENCES public.dim_exercise_types(type_code),
    pos_classes    text[]   NOT NULL DEFAULT '{all}',   -- semantic_class values from §4's ratified enum
    ladder_level   smallint,                            -- NULL = non-ladder (timed_speed_round, flashcards)
    generator      text     NOT NULL,                   -- 'deterministic' | 'llm' | 'hybrid'
    requires       text[]   NOT NULL DEFAULT '{}',      -- {'pronunciation','morph_forms>=2','classifier_dict','counter_dict','tts',...}
    judge_key      text,                                -- NULL only for deterministic generators
    is_enabled     boolean  NOT NULL DEFAULT true,
    PRIMARY KEY (language_id, type_code)
);

-- 2. Seed every enabled (language, type) pair per §5's Lang column, plus the
--    documented disabled marker for ZH morphology_slot (Chinese is analytic —
--    no inflection, so its L4 is classifier_match, not morphology). Languages:
--    1 = Chinese, 2 = English, 3 = Japanese.
INSERT INTO public.dim_exercise_capabilities
    (language_id, type_code, pos_classes, ladder_level, generator, requires, judge_key, is_enabled)
VALUES
    -- L1 phonetic_recognition (form_recognition) — ZH also needs pinyin for tone-confusable distractors
    (2, 'phonetic_recognition', ARRAY['all'], 1, 'llm', ARRAY['p1_sentences','tts'], 'l1_distractor', true),
    (3, 'phonetic_recognition', ARRAY['all'], 1, 'llm', ARRAY['p1_sentences','tts'], 'l1_distractor', true),
    (1, 'phonetic_recognition', ARRAY['all'], 1, 'llm', ARRAY['p1_sentences','tts','pronunciation'], 'l1_distractor', true),

    -- L2 definition_match (form_recognition) — deterministic same-tier sampler
    (1, 'definition_match', ARRAY['all'], 2, 'deterministic', ARRAY['same_tier_senses'], NULL, true),
    (2, 'definition_match', ARRAY['all'], 2, 'deterministic', ARRAY['same_tier_senses'], NULL, true),
    (3, 'definition_match', ARRAY['all'], 2, 'deterministic', ARRAY['same_tier_senses'], NULL, true),

    -- L3 cloze_completion (meaning_recall)
    (1, 'cloze_completion', ARRAY['all'], 3, 'llm', ARRAY['p1_sentences'], 'cloze', true),
    (2, 'cloze_completion', ARRAY['all'], 3, 'llm', ARRAY['p1_sentences'], 'cloze', true),
    (3, 'cloze_completion', ARRAY['all'], 3, 'llm', ARRAY['p1_sentences'], 'cloze', true),

    -- L4 cloze_typed (form_production) — general productive slot, every inflecting/non-inflecting language
    (1, 'cloze_typed', ARRAY['concrete','abstract','action','property'], 4, 'deterministic', ARRAY['cloze_asset'], NULL, true),
    (2, 'cloze_typed', ARRAY['concrete','abstract','action','property'], 4, 'deterministic', ARRAY['cloze_asset'], NULL, true),
    (3, 'cloze_typed', ARRAY['concrete','abstract','action','property'], 4, 'deterministic', ARRAY['cloze_asset'], NULL, true),

    -- L4 morphology_slot (form_production) — EN (+concrete plural) & JA inflection; ZH DISABLED (analytic)
    (2, 'morphology_slot', ARRAY['concrete','action','property'], 4, 'llm', ARRAY['morph_forms>=2'], 'sentence_validity', true),
    (3, 'morphology_slot', ARRAY['action','property'], 4, 'llm', ARRAY['morph_forms>=2'], 'sentence_validity', true),
    (1, 'morphology_slot', ARRAY['action','property'], 4, 'llm', ARRAY['morph_forms>=2'], 'sentence_validity', false),

    -- L4 classifier_match (form_production) — ZH concrete nouns, deterministic from classifier dict
    (1, 'classifier_match', ARRAY['concrete'], 4, 'deterministic', ARRAY['classifier_dict'], NULL, true),

    -- L4 particle_selection (form_production) — JA case particles
    (3, 'particle_selection', ARRAY['concrete','abstract','action'], 4, 'llm', ARRAY['p1_sentences','tokenised_particles'], 'particle', true),

    -- L4 counter_match (form_production) — JA counters (助数詞), deterministic from counter dict
    (3, 'counter_match', ARRAY['concrete'], 4, 'deterministic', ARRAY['counter_dict'], NULL, true),

    -- L5 collocation_gap_fill (collocation) — concrete nouns skip (no tight collocates)
    (1, 'collocation_gap_fill', ARRAY['abstract','action','property'], 5, 'llm', ARRAY['primary_collocate'], 'collocation', true),
    (2, 'collocation_gap_fill', ARRAY['abstract','action','property'], 5, 'llm', ARRAY['primary_collocate'], 'collocation', true),
    (3, 'collocation_gap_fill', ARRAY['abstract','action','property'], 5, 'llm', ARRAY['primary_collocate'], 'collocation', true),

    -- L6 semantic_discrimination
    (1, 'semantic_discrimination', ARRAY['all'], 6, 'llm', ARRAY['p1_definition'], 'sentence_validity', true),
    (2, 'semantic_discrimination', ARRAY['all'], 6, 'llm', ARRAY['p1_definition'], 'sentence_validity', true),
    (3, 'semantic_discrimination', ARRAY['all'], 6, 'llm', ARRAY['p1_definition'], 'sentence_validity', true),

    -- L7 spot_incorrect_sentence (semantic_discrimination)
    (1, 'spot_incorrect_sentence', ARRAY['all'], 7, 'llm', ARRAY['p1_sentences'], 'sentence_validity', true),
    (2, 'spot_incorrect_sentence', ARRAY['all'], 7, 'llm', ARRAY['p1_sentences'], 'sentence_validity', true),
    (3, 'spot_incorrect_sentence', ARRAY['all'], 7, 'llm', ARRAY['p1_sentences'], 'sentence_validity', true),

    -- L8 collocation_repair (collocation) — concrete nouns skip
    (1, 'collocation_repair', ARRAY['abstract','action','property'], 8, 'llm', ARRAY['primary_collocate'], 'collocation', true),
    (2, 'collocation_repair', ARRAY['abstract','action','property'], 8, 'llm', ARRAY['primary_collocate'], 'collocation', true),
    (3, 'collocation_repair', ARRAY['abstract','action','property'], 8, 'llm', ARRAY['primary_collocate'], 'collocation', true),

    -- L9 jumbled_sentence (form_production) — function words excluded (no productive syntax slot)
    (1, 'jumbled_sentence', ARRAY['concrete','abstract','action','property'], 9, 'deterministic', ARRAY['p1_sentences'], NULL, true),
    (2, 'jumbled_sentence', ARRAY['concrete','abstract','action','property'], 9, 'deterministic', ARRAY['p1_sentences'], NULL, true),
    (3, 'jumbled_sentence', ARRAY['concrete','abstract','action','property'], 9, 'deterministic', ARRAY['p1_sentences'], NULL, true),

    -- Ring-1 readings & tone (form_recognition) — deterministic from per-sense pronunciation
    (1, 'hanzi_to_pinyin', ARRAY['all'], 1, 'deterministic', ARRAY['pronunciation'], NULL, true),
    (1, 'pinyin_to_hanzi', ARRAY['all'], 1, 'deterministic', ARRAY['pronunciation'], NULL, true),
    (1, 'tone_id_word', ARRAY['all'], 1, 'deterministic', ARRAY['pronunciation'], NULL, true),
    (3, 'kanji_to_reading', ARRAY['all'], 1, 'deterministic', ARRAY['pronunciation'], NULL, true),
    (3, 'reading_to_kanji', ARRAY['all'], 1, 'deterministic', ARRAY['pronunciation'], NULL, true),

    -- synonym_antonym_match (semantic_discrimination, L6) — content words only
    (1, 'synonym_antonym_match', ARRAY['abstract','action','property'], 6, 'llm', ARRAY['sense_embedding'], 'relation', true),
    (2, 'synonym_antonym_match', ARRAY['abstract','action','property'], 6, 'llm', ARRAY['sense_embedding'], 'relation', true),
    (3, 'synonym_antonym_match', ARRAY['abstract','action','property'], 6, 'llm', ARRAY['sense_embedding'], 'relation', true),

    -- word_family (form_production, L4) — EN derivational morphology
    (2, 'word_family', ARRAY['abstract','action','property'], 4, 'llm', ARRAY['morph_forms>=2'], 'word_family', true),

    -- tl_nl / nl_tl translation (meaning_recall, L3) — ZH & JA only (auto-skipped when tl==nl)
    (1, 'tl_nl_translation', ARRAY['all'], 3, 'llm', ARRAY['p1_sentences','nl_gloss'], 'translation_uniqueness', true),
    (3, 'tl_nl_translation', ARRAY['all'], 3, 'llm', ARRAY['p1_sentences','nl_gloss'], 'translation_uniqueness', true),
    (1, 'nl_tl_translation', ARRAY['all'], 3, 'llm', ARRAY['p1_sentences','nl_gloss'], 'translation_uniqueness', true),
    (3, 'nl_tl_translation', ARRAY['all'], 3, 'llm', ARRAY['p1_sentences','nl_gloss'], 'translation_uniqueness', true),

    -- Flashcards — supplementary exposure, non-progression (ladder_level NULL)
    (1, 'text_flashcard', ARRAY['all'], NULL, 'deterministic', ARRAY['p1_sentences'], NULL, true),
    (2, 'text_flashcard', ARRAY['all'], NULL, 'deterministic', ARRAY['p1_sentences'], NULL, true),
    (3, 'text_flashcard', ARRAY['all'], NULL, 'deterministic', ARRAY['p1_sentences'], NULL, true),
    (1, 'listening_flashcard', ARRAY['all'], NULL, 'deterministic', ARRAY['p1_sentences','tts'], NULL, true),
    (2, 'listening_flashcard', ARRAY['all'], NULL, 'deterministic', ARRAY['p1_sentences','tts'], NULL, true),
    (3, 'listening_flashcard', ARRAY['all'], NULL, 'deterministic', ARRAY['p1_sentences','tts'], NULL, true),

    -- timed_speed_round (fluency) — serve-time composition over mastered senses, non-ladder
    (1, 'timed_speed_round', ARRAY['all'], NULL, 'deterministic', ARRAY[]::text[], NULL, true),
    (2, 'timed_speed_round', ARRAY['all'], NULL, 'deterministic', ARRAY[]::text[], NULL, true),
    (3, 'timed_speed_round', ARRAY['all'], NULL, 'deterministic', ARRAY[]::text[], NULL, true)
ON CONFLICT (language_id, type_code) DO UPDATE SET
    pos_classes  = EXCLUDED.pos_classes,
    ladder_level = EXCLUDED.ladder_level,
    generator    = EXCLUDED.generator,
    requires     = EXCLUDED.requires,
    judge_key    = EXCLUDED.judge_key,
    is_enabled   = EXCLUDED.is_enabled;
