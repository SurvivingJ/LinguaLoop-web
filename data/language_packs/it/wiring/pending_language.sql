-- ============================================================================
-- NOT APPLIED
-- ============================================================================
-- Italian (language_code 'it', proposed dim_languages.id = 4): the language row
-- and its (language, type) capability matrix.
--
-- Written by the new-language content team's wiring planner on 2026-11-28 from
-- data/language_packs/it/profile.json. NOTHING in this file has been run against
-- any LinguaLoop database. It is a proposal for an engineer to review, move
-- into migrations/ under a task id, and apply. See wiring/tasks.md for the
-- order (task 1 applies it; task 13 mirrors sections 2 and 3 in code).
--
-- What it does
--   0. Refuses to run if id 4 or the code 'it' is already used differently.
--   1. dim_languages: one row, id 4, INACTIVE (is_active = false).
--   2. dim_exercise_types: the six type codes Italian adds (FK target of 3).
--   3. dim_exercise_capabilities: one row per ladder type the profile keeps
--      (17 carried over + 6 new = 23 rows for language 4).
--   4. Statements for LATER, commented out: enabling each new type, enabling
--      the collocation levels, activating the language.
--
-- Why the language is inserted inactive
--   services/test_generation/database_client.py and services/irt/calibrator.py
--   iterate over the active rows of dim_languages. An active row with no
--   prompt rows, no NLP processor and no entry in Config.LANGUAGES would be
--   picked up by the production queue and the nightly calibration before the
--   code knows the language. The capability rows only need the row to exist
--   (FK). Section 4c flips is_active as the last go-live step.
--
-- Why id 4 is written explicitly
--   phase13_dim_study_plan_templates.sql notes that dim_languages.id is not
--   stable across environments, but application code is: config.py
--   Config.LANGUAGES and about twenty copies of {1: 'zh', 2: 'en', 3: 'ja'}
--   key on the integer. The pack's profile fixes proposed_language_id = 4, so
--   the row is inserted with that id and the guard in section 0 stops the
--   file where 4 is taken by another language.
--
-- is_enabled, row by row (profile status -> value)
--   reuse / adapt -> true, with one exception (next paragraph)
--   new           -> false: the generator, renderer and tests do not exist yet;
--                    each is enabled by its own task (section 4a)
--   not_applicable (hanzi_to_pinyin, pinyin_to_hanzi, tone_id_word,
--   kanji_to_reading, reading_to_kanji, classifier_match, counter_match,
--   particle_selection) -> no row at all.
--
--   EXCEPTION, flagged for review: collocation_gap_fill and collocation_repair
--   are 'adapt' in the profile but are inserted DISABLED. The profile's own
--   note says they are "enabled only for senses whose pair is in the reviewed
--   collocations dictionary ... without it the type stays disabled, as for zh
--   and ja". services/vocabulary_ladder/collocation_grounding.py has no
--   grounding source for language 4 yet; enabling the rows before one exists
--   reproduces audit B1 (ladder_collocation_disable_zh_ja.sql): the collocation
--   family becomes unsatisfiable and v_sense_family_coverage re-enqueues every
--   sense for a full regeneration every night. Section 4b enables them once
--   the Italian grounding list is loaded.
--
-- requires tokens that are new with this language
--   noun_gender_dict, verb_conjugation_dict, verb_government_dict,
--   collocations_dict, false_friends_dict. config.requirements_met() treats a
--   token it is not given as satisfied, and capability_context_from_core()
--   deliberately leaves classifier_dict / counter_dict out so that the builder
--   decides and records a Skip. The new tokens follow that convention: they
--   document what the type reads, and the builder (or, for the collocation
--   levels, collocation_grounding) does the gating. If they are ever put into
--   the context, false_friends_dict on the two translation rows must mean "the
--   dictionary is loaded for this language", NOT "this word is in it": about
--   200 words are false friends, and a per-word flag would switch translation
--   off for every other word.
--
-- judge_key
--   Carried-over LLM rows use the judge the English / Japanese rows use.
--   preposition_selection names a judge that does not exist yet
--   ('preposition'; prompt task ladder_preposition_judge, see
--   wiring/prompt_tasks.txt). The row is disabled until it does.
--
-- Idempotent. Re-running re-asserts every column EXCEPT:
--   dim_languages.is_active and dim_exercise_capabilities.is_enabled, which are
--   written on first insert only, so a re-run after go-live does not switch the
--   language or an enabled type back off; and tts_voice_ids / tts_speed, which
--   are only overwritten when still unset or holding the OpenAI default list
--   (the convention of seed_chinese_tts_voices.sql).
--
-- Preconditions: public.dim_languages, public.dim_exercise_types (with
-- context_class, task743_context_free_exercise_caps.sql) and
-- public.dim_exercise_capabilities (dim_exercise_capabilities.sql) exist.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Guard: id 4 and code 'it' must be free, or already be this row.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    v_code text;
    v_id   smallint;
BEGIN
    SELECT language_code INTO v_code FROM public.dim_languages WHERE id = 4;
    IF v_code IS NOT NULL AND v_code <> 'it' THEN
        RAISE EXCEPTION 'dim_languages.id = 4 is already language_code=%; '
            'choose another id and change it in profile.json, config.py and this file', v_code;
    END IF;

    SELECT id INTO v_id FROM public.dim_languages WHERE language_code = 'it';
    IF v_id IS NOT NULL AND v_id <> 4 THEN
        RAISE EXCEPTION 'language_code=it already exists with id=% (expected 4)', v_id;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. dim_languages row (inactive until go-live, section 4c)
--    Voices: two Azure neural voices, one female and one male, from the
--    profile. NOT checked against the live Azure voice list (tasks.md, task 1).
--    grammar_check_enabled = false: no Italian grammar tooling is wired.
-- ---------------------------------------------------------------------------
INSERT INTO public.dim_languages
    (id, language_code, language_name, native_name, iso_639_1, iso_639_3,
     is_active, display_order, tts_voice_ids, tts_speed, grammar_check_enabled)
VALUES
    (4, 'it', 'Italian', 'Italiano', 'it', 'ita',
     false, 4,
     '["it-IT-IsabellaNeural", "it-IT-DiegoNeural"]'::jsonb,
     1.0, false)
ON CONFLICT (id) DO UPDATE SET
    language_code = EXCLUDED.language_code,
    language_name = EXCLUDED.language_name,
    native_name   = EXCLUDED.native_name,
    iso_639_1     = EXCLUDED.iso_639_1,
    iso_639_3     = EXCLUDED.iso_639_3,
    display_order = EXCLUDED.display_order,
    tts_voice_ids = CASE
        WHEN public.dim_languages.tts_voice_ids IS NULL
          OR public.dim_languages.tts_voice_ids = '[]'::jsonb
          OR public.dim_languages.tts_voice_ids @> '["alloy"]'::jsonb
        THEN EXCLUDED.tts_voice_ids
        ELSE public.dim_languages.tts_voice_ids
    END,
    tts_speed     = COALESCE(public.dim_languages.tts_speed, EXCLUDED.tts_speed),
    updated_at    = now();

-- The id was written explicitly: move the id sequence past it so that the
-- next language inserted without an id does not collide with 4.
SELECT setval(
    pg_get_serial_sequence('public.dim_languages', 'id'),
    GREATEST((SELECT max(id) FROM public.dim_languages), 1)
);

-- ---------------------------------------------------------------------------
-- 2. dim_exercise_types: the six types Italian adds.
--    Family and expected_seconds follow the analogue each one replaces:
--      stress_position        <- tone_id_word       (form_recognition, 15 s)
--      article_match          <- classifier_match   (form_production, 45 s)
--      auxiliary_choice       <- classifier_match   (form_production, 45 s)
--      conjugation_form       <- classifier_match   (form_production, 45 s)
--      government_match       <- counter_match      (form_production, 45 s)
--      preposition_selection  <- particle_selection (form_production, 45 s)
--    context_class: the five deterministic types are a property of the word
--    (no sentence), preposition_selection is anchored to a core sentence.
--    Four of the context-free types produce MORE THAN ONE distinct question
--    per word (article_match has four modes, conjugation_form many cells,
--    government_match one item per government row), so they must NOT be added
--    to the one-per-word unique index; see tasks.md, task 13.
-- ---------------------------------------------------------------------------
INSERT INTO public.dim_exercise_types (type_code, family, expected_seconds, context_class)
VALUES
    ('stress_position',       'form_recognition', 15, 'context_free'),
    ('article_match',         'form_production',  45, 'context_free'),
    ('auxiliary_choice',      'form_production',  45, 'context_free'),
    ('conjugation_form',      'form_production',  45, 'context_free'),
    ('government_match',      'form_production',  45, 'context_free'),
    ('preposition_selection', 'form_production',  45, 'context_bearing')
ON CONFLICT (type_code) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. dim_exercise_capabilities: language 4 = Italian.
--    Columns and conventions as in migrations/dim_exercise_capabilities.sql.
--    pos_classes / ladder_level / generator / requires are the profile's
--    ladder rows, unchanged. The trailing comment is the profile's status.
-- ---------------------------------------------------------------------------
INSERT INTO public.dim_exercise_capabilities
    (language_id, type_code, pos_classes, ladder_level, generator, requires, judge_key, is_enabled)
VALUES
    -- L1 phonetic_recognition: distractors are single/double consonant, gl/l, gn/n neighbours
    (4, 'phonetic_recognition', ARRAY['all'], 1, 'llm', ARRAY['p1_sentences','tts'], 'l1_distractor', true),  -- adapt

    -- L2 definition_match: deterministic same-tier sampler
    (4, 'definition_match', ARRAY['all'], 2, 'deterministic', ARRAY['same_tier_senses'], NULL, true),  -- reuse

    -- L3 cloze_completion: distractors must match gender, number and first sound of the answer
    (4, 'cloze_completion', ARRAY['all'], 3, 'llm', ARRAY['p1_sentences'], 'cloze', true),  -- adapt

    -- L3 translation (Italian <-> learner's language): false friends forced in as distractors;
    -- nouns answered with their article. false_friends_dict is a language-level flag (header).
    (4, 'tl_nl_translation', ARRAY['all'], 3, 'llm', ARRAY['p1_sentences','nl_gloss','false_friends_dict'], 'translation_uniqueness', true),  -- adapt
    (4, 'nl_tl_translation', ARRAY['all'], 3, 'llm', ARRAY['p1_sentences','nl_gloss','false_friends_dict'], 'translation_uniqueness', true),  -- adapt

    -- L4 cloze_typed: accents are significant, a wrong accent is reported as an accent error
    (4, 'cloze_typed', ARRAY['concrete','abstract','action','property'], 4, 'deterministic', ARRAY['cloze_asset'], NULL, true),  -- adapt

    -- L4 morphology_slot: verbs, adjectives and nouns (plural formation lives here)
    (4, 'morphology_slot', ARRAY['concrete','abstract','action','property'], 4, 'llm', ARRAY['morph_forms>=2','inflecting_pos'], 'sentence_validity', true),  -- adapt

    -- L4 word_family: carried over from English (decidere / decisione / deciso)
    (4, 'word_family', ARRAY['abstract','action','property'], 4, 'llm', ARRAY['morph_forms>=2'], 'word_family', true),  -- adapt

    -- L5 collocation_gap_fill: DISABLED until the collocations dictionary is the grounding
    -- source for language 4 (header, EXCEPTION). Concrete nouns included (fare colazione).
    (4, 'collocation_gap_fill', ARRAY['abstract','action','property','concrete'], 5, 'llm', ARRAY['primary_collocate','collocations_dict'], 'collocation', false),  -- adapt

    -- L6 semantic_discrimination / synonym_antonym_match
    (4, 'semantic_discrimination', ARRAY['all'], 6, 'llm', ARRAY['p1_definition'], 'sentence_validity', true),  -- reuse
    (4, 'synonym_antonym_match', ARRAY['abstract','action','property'], 6, 'llm', ARRAY['sense_embedding'], 'relation', true),  -- reuse

    -- L7 spot_incorrect_sentence: one error on the target, of a kind English speakers make
    (4, 'spot_incorrect_sentence', ARRAY['all'], 7, 'llm', ARRAY['p1_sentences'], 'sentence_validity', true),  -- adapt

    -- L8 collocation_repair: DISABLED for the same reason as L5
    (4, 'collocation_repair', ARRAY['abstract','action','property','concrete'], 8, 'llm', ARRAY['primary_collocate','collocations_dict'], 'collocation', false),  -- adapt

    -- L9 jumbled_sentence: split on spaces only (l'amico is one tile), at most eight tiles
    (4, 'jumbled_sentence', ARRAY['concrete','abstract','action','property'], 9, 'deterministic', ARRAY['p1_sentences'], NULL, true),  -- adapt

    -- Flashcards and speed round: non-ladder (ladder_level NULL)
    (4, 'text_flashcard', ARRAY['all'], NULL, 'deterministic', ARRAY['p1_sentences'], NULL, true),  -- reuse
    (4, 'listening_flashcard', ARRAY['all'], NULL, 'deterministic', ARRAY['p1_sentences','tts'], NULL, true),  -- reuse
    (4, 'timed_speed_round', ARRAY['all'], NULL, 'deterministic', ARRAY['same_tier_senses'], NULL, true),  -- reuse

    -- New for Italian: inserted DISABLED; each is enabled by its own task (section 4a).
    -- L1 stress_position: tap the stressed syllable; analogue of tone_id_word
    (4, 'stress_position', ARRAY['all'], 1, 'deterministic', ARRAY['pronunciation','tts'], NULL, false),  -- new
    -- L4 article_match: article and preposition + article from noun_gender; analogue of classifier_match
    (4, 'article_match', ARRAY['concrete','abstract'], 4, 'deterministic', ARRAY['noun_gender_dict'], NULL, false),  -- new
    -- L4 auxiliary_choice: avere / essere and participle agreement from verb_conjugation
    (4, 'auxiliary_choice', ARRAY['action'], 4, 'deterministic', ARRAY['verb_conjugation_dict'], NULL, false),  -- new
    -- L4 conjugation_form: one paradigm cell without a sentence, from verb_conjugation
    (4, 'conjugation_form', ARRAY['action'], 4, 'deterministic', ARRAY['verb_conjugation_dict'], NULL, false),  -- new
    -- L4 government_match: the preposition a head word takes, from verb_government
    (4, 'government_match', ARRAY['action','property','abstract'], 4, 'deterministic', ARRAY['verb_government_dict'], NULL, false),  -- new
    -- L4 preposition_selection: authored per sentence; analogue of particle_selection
    (4, 'preposition_selection', ARRAY['concrete','abstract','action','property'], 4, 'llm', ARRAY['p1_sentences'], 'preposition', false)  -- new
ON CONFLICT (language_id, type_code) DO UPDATE SET
    pos_classes  = EXCLUDED.pos_classes,
    ladder_level = EXCLUDED.ladder_level,
    generator    = EXCLUDED.generator,
    requires     = EXCLUDED.requires,
    judge_key    = EXCLUDED.judge_key;
    -- is_enabled is deliberately NOT re-asserted: see the header.

COMMIT;

-- ============================================================================
-- 4. LATER. Each statement belongs to the task named beside it in
--    wiring/tasks.md and is run when that task's verification passes.
--    Left commented out so that running this file end to end enables nothing.
-- ============================================================================

-- 4a. Enable a new type once its generator, renderer and tests are merged and
--     the same row is flipped in services/vocabulary_ladder/config.py
--     _CAPABILITY_SPEC (tests/test_capability_matrix.py pins the two together).
--
-- UPDATE public.dim_exercise_capabilities SET is_enabled = true
--  WHERE language_id = 4 AND type_code = 'stress_position';        -- task 21
-- UPDATE public.dim_exercise_capabilities SET is_enabled = true
--  WHERE language_id = 4 AND type_code = 'article_match';          -- task 22
-- UPDATE public.dim_exercise_capabilities SET is_enabled = true
--  WHERE language_id = 4 AND type_code = 'auxiliary_choice';       -- task 23
-- UPDATE public.dim_exercise_capabilities SET is_enabled = true
--  WHERE language_id = 4 AND type_code = 'conjugation_form';       -- task 24
-- UPDATE public.dim_exercise_capabilities SET is_enabled = true
--  WHERE language_id = 4 AND type_code = 'government_match';       -- task 25
-- UPDATE public.dim_exercise_capabilities SET is_enabled = true
--  WHERE language_id = 4 AND type_code = 'preposition_selection';  -- task 26

-- 4b. Enable the collocation levels once the reviewed collocations dictionary
--     is registered as the grounding source for language 4 (task 19).
--
-- UPDATE public.dim_exercise_capabilities SET is_enabled = true
--  WHERE language_id = 4 AND type_code IN ('collocation_gap_fill', 'collocation_repair');

-- 4c. Go-live (task 34): the language becomes visible to test generation, the
--     nightly calibration and the language picker.
--
-- UPDATE public.dim_languages SET is_active = true, updated_at = now() WHERE id = 4;

-- ============================================================================
-- Verification (run manually after applying sections 0 to 3)
-- ============================================================================
-- SELECT id, language_code, language_name, native_name, is_active, tts_voice_ids
--   FROM public.dim_languages WHERE id = 4;
--   -- expect: 4 | it | Italian | Italiano | f | ["it-IT-IsabellaNeural", "it-IT-DiegoNeural"]
--
-- SELECT count(*) AS it_rows,
--        count(*) FILTER (WHERE is_enabled)     AS enabled,
--        count(*) FILTER (WHERE NOT is_enabled) AS disabled
--   FROM public.dim_exercise_capabilities WHERE language_id = 4;
--   -- expect: 23 | 15 | 8   (8 = six new types + the two collocation levels)
--
-- SELECT type_code FROM public.dim_exercise_capabilities
--  WHERE language_id = 4 AND generator <> 'deterministic' AND judge_key IS NULL;
--   -- expect: no rows (judge_key is NULL only for deterministic generators)
--
-- SELECT c.type_code FROM public.dim_exercise_capabilities c
--   LEFT JOIN public.dim_exercise_types t USING (type_code)
--  WHERE c.language_id = 4 AND t.type_code IS NULL;
--   -- expect: no rows
--
-- The ladder Italian runs today (enabled rows only), by semantic class:
-- SELECT cls, array_agg(DISTINCT ladder_level ORDER BY ladder_level) AS levels
--   FROM public.dim_exercise_capabilities,
--        unnest(ARRAY['concrete','abstract','action','property','function']) AS cls
--  WHERE language_id = 4 AND is_enabled AND ladder_level IS NOT NULL
--    AND (pos_classes @> ARRAY[cls] OR pos_classes @> ARRAY['all'])
--  GROUP BY cls ORDER BY cls;
--   -- expect: concrete/abstract/action/property -> {1,2,3,4,6,7,9}; function -> {1,2,3,6,7}
-- ============================================================================
