-- =============================================================================
-- LOCAL HARNESS FIXTURE (not a migration; never run against production).
-- Live DDL (fetched read-only from the production catalog on 2026-11-19, PostgreSQL 17.4) of the
-- tables the Knowledge Report RPCs read that the shared local harness does not define:
--   users, exercise_attempts, word_quiz_results, exercises, dim_exercise_types,
--   user_flashcards, user_word_ladder, user_word_watchlist
-- plus the live dim_exercise_types rows and the Supabase default table privileges for
-- service_role (Supabase grants ALL on public tables to service_role through default privileges;
-- the SECURITY INVOKER report functions need them when called as service_role).
-- Foreign keys are omitted, as in the harness's own 10_tables.sql.
--
-- Load order (PG_EXTRA of the harness's pg.sh, absolute paths):
--   tests/sql/fixtures/knowledge_report_tables.sql
--   migrations/knowledge_report_foundation.sql
--   migrations/reference_data_bucket.sql
--   tests/sql/fixtures/knowledge_calibration_inputs_stub.sql   (until TASK-1079 exists)
--   migrations/knowledge_report_summary.sql
--   migrations/knowledge_report_words.sql
-- then: psql -v ON_ERROR_STOP=1 -f tests/sql/test_knowledge_report.sql
-- =============================================================================

CREATE TYPE public.exercise_source_type AS ENUM ('grammar', 'vocabulary', 'collocation', 'conversation', 'style');

CREATE TABLE public.users (
  id uuid NOT NULL,
  email text NOT NULL,
  display_name text,
  email_verified boolean DEFAULT false,
  total_tests_taken integer DEFAULT 0,
  total_tests_generated integer DEFAULT 0,
  last_activity_at timestamp with time zone,
  last_free_test_date date DEFAULT (CURRENT_DATE - '1 day'::interval),
  free_tests_used_today integer DEFAULT 0,
  total_free_tests_used integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  last_login timestamp with time zone DEFAULT now(),
  subscription_tier_id smallint DEFAULT 1 NOT NULL,
  deleted_at timestamp with time zone,
  anonymized_at timestamp with time zone,
  organization_id uuid,
  exercise_preferences jsonb DEFAULT '{"session_size": 20}'::jsonb,
  has_seen_welcome boolean DEFAULT false NOT NULL,
  native_language_id smallint,
  CONSTRAINT users_email_key UNIQUE (email),
  CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE TABLE public.dim_exercise_types (
  type_code text NOT NULL,
  family text NOT NULL,
  expected_seconds smallint DEFAULT 45 NOT NULL,
  expected_seconds_p50 numeric(5,1),
  is_active boolean DEFAULT true NOT NULL,
  context_class text DEFAULT 'context_bearing'::text NOT NULL,
  CONSTRAINT dim_exercise_types_context_class_check CHECK ((context_class = ANY (ARRAY['context_free'::text, 'context_bearing'::text, 'not_sense_anchored'::text]))),
  CONSTRAINT dim_exercise_types_expected_seconds_positive CHECK (((expected_seconds > 0) AND (expected_seconds <= 600))),
  CONSTRAINT dim_exercise_types_family_check CHECK ((family = ANY (ARRAY['form_recognition'::text, 'meaning_recall'::text, 'form_production'::text, 'collocation'::text, 'semantic_discrimination'::text, 'contextual_use'::text, 'fluency'::text]))),
  CONSTRAINT dim_exercise_types_p50_positive CHECK (((expected_seconds_p50 IS NULL) OR ((expected_seconds_p50 > (0)::numeric) AND (expected_seconds_p50 <= (600)::numeric)))),
  CONSTRAINT dim_exercise_types_pkey PRIMARY KEY (type_code)
);

CREATE TABLE public.exercise_attempts (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  user_id uuid NOT NULL,
  exercise_id uuid,
  user_response jsonb,
  is_correct boolean NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  exercise_type text,
  sense_id integer,
  is_first_attempt boolean DEFAULT true,
  ladder_level integer,
  time_taken_ms integer,
  p_known_before numeric,
  p_known_after numeric,
  source text,
  CONSTRAINT exercise_attempts_pkey PRIMARY KEY (id),
  CONSTRAINT exercise_attempts_source_check CHECK (((source IS NULL) OR (source = ANY (ARRAY['prestudy'::text, 'intro'::text]))))
);
CREATE INDEX idx_ea_user_exercise ON public.exercise_attempts USING btree (user_id, exercise_id);
CREATE INDEX idx_ea_exercise_id ON public.exercise_attempts USING btree (exercise_id);
CREATE INDEX idx_ea_user_created ON public.exercise_attempts USING btree (user_id, created_at DESC);
CREATE INDEX idx_ea_user_sense_type ON public.exercise_attempts USING btree (user_id, sense_id, exercise_type, created_at DESC);

CREATE TABLE public.exercises (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  language_id integer NOT NULL,
  exercise_type text NOT NULL,
  source_type exercise_source_type NOT NULL,
  word_sense_id integer,
  corpus_collocation_id integer,
  tags jsonb DEFAULT '{}'::jsonb NOT NULL,
  difficulty_static numeric(4,2),
  irt_difficulty numeric(5,3) DEFAULT 0.0 NOT NULL,
  irt_discrimination numeric(5,3) DEFAULT 1.0 NOT NULL,
  complexity_tier text,
  attempt_count integer DEFAULT 0 NOT NULL,
  correct_count integer DEFAULT 0 NOT NULL,
  is_active boolean DEFAULT true NOT NULL,
  generation_batch_id uuid,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  pattern_code text,
  word_asset_id bigint,
  ladder_level integer,
  irt_n_attempts integer DEFAULT 0 NOT NULL,
  irt_calibrated_at timestamp with time zone,
  irt_se_difficulty numeric(5,3),
  content_version integer DEFAULT 0 NOT NULL,
  dedupe_key text,
  CONSTRAINT chk_source_fk CHECK (((((word_sense_id IS NOT NULL))::integer + ((corpus_collocation_id IS NOT NULL))::integer) >= 1)),
  CONSTRAINT exercises_complexity_tier_check CHECK ((complexity_tier = ANY (ARRAY['T1'::text, 'T2'::text, 'T3'::text, 'T4'::text, 'T5'::text, 'T6'::text]))),
  CONSTRAINT exercises_ladder_level_check CHECK (((ladder_level IS NULL) OR ((ladder_level >= 1) AND (ladder_level <= 9)))),
  CONSTRAINT exercises_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_exercises_sense ON public.exercises USING btree (word_sense_id) WHERE (word_sense_id IS NOT NULL);

CREATE TABLE public.user_flashcards (
  id bigint GENERATED BY DEFAULT AS IDENTITY NOT NULL,
  user_id uuid NOT NULL,
  sense_id integer NOT NULL,
  language_id smallint NOT NULL,
  stability real DEFAULT 0,
  difficulty real DEFAULT 0.3,
  due_date date,
  last_review timestamp with time zone,
  reps integer DEFAULT 0,
  lapses integer DEFAULT 0,
  state text DEFAULT 'new'::text,
  example_sentence text,
  audio_url text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_flashcards_pkey PRIMARY KEY (id),
  CONSTRAINT user_flashcards_state_check CHECK ((state = ANY (ARRAY['new'::text, 'learning'::text, 'review'::text, 'relearning'::text]))),
  CONSTRAINT user_flashcards_user_id_sense_id_key UNIQUE (user_id, sense_id)
);
CREATE INDEX idx_uf_user_due ON public.user_flashcards USING btree (user_id, language_id, due_date);

CREATE TABLE public.user_word_ladder (
  user_id uuid NOT NULL,
  sense_id integer NOT NULL,
  current_level integer DEFAULT 1 NOT NULL,
  active_levels integer[] DEFAULT '{1,2,3,4,5,6,7,8,9}'::integer[] NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  first_try_success_count integer DEFAULT 0 NOT NULL,
  first_try_failure_count integer DEFAULT 0 NOT NULL,
  consecutive_failures integer DEFAULT 0 NOT NULL,
  total_attempts integer DEFAULT 0 NOT NULL,
  word_state text DEFAULT 'active'::text NOT NULL,
  last_success_session_date date,
  review_due_at timestamp with time zone,
  family_confidence jsonb DEFAULT '{"collocation": 0.10, "contextual_use": 0.10, "meaning_recall": 0.10, "form_production": 0.10, "form_recognition": 0.10, "semantic_discrimination": 0.10}'::jsonb NOT NULL,
  gates_passed jsonb DEFAULT '{"gate_a": false, "gate_b": false}'::jsonb NOT NULL,
  current_ring integer DEFAULT 1 NOT NULL,
  stress_test_score real,
  last_exercised_family text,
  family_success_dates jsonb DEFAULT '{"collocation": [], "contextual_use": [], "meaning_recall": [], "form_production": [], "form_recognition": [], "semantic_discrimination": []}'::jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  intro_stage smallint,
  intro_due_date date,
  intro_history jsonb DEFAULT '[]'::jsonb NOT NULL,
  CONSTRAINT user_word_ladder_current_level_check CHECK (((current_level >= 1) AND (current_level <= 9))),
  CONSTRAINT user_word_ladder_current_ring_check CHECK (((current_ring >= 1) AND (current_ring <= 4))),
  CONSTRAINT user_word_ladder_intro_stage_check CHECK (((intro_stage IS NULL) OR ((intro_stage >= 1) AND (intro_stage <= 4)))),
  CONSTRAINT user_word_ladder_pkey PRIMARY KEY (user_id, sense_id),
  CONSTRAINT user_word_ladder_word_state_check CHECK ((word_state = ANY (ARRAY['new'::text, 'active'::text, 'gated'::text, 'pre_mastery'::text, 'relearning'::text, 'mastered'::text, 'intro'::text])))
);

CREATE TABLE public.user_word_watchlist (
  id bigint GENERATED BY DEFAULT AS IDENTITY NOT NULL,
  user_id uuid NOT NULL,
  sense_id integer NOT NULL,
  language_id smallint NOT NULL,
  upload_batch_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  ladder_exercises_generated boolean DEFAULT false NOT NULL,
  last_matched_test_id uuid,
  last_matched_at timestamp with time zone,
  active boolean DEFAULT true NOT NULL,
  last_matched_surfaced_at timestamp with time zone,
  CONSTRAINT user_word_watchlist_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_user_word_watchlist_user_id ON public.user_word_watchlist USING btree (user_id);

CREATE TABLE public.word_quiz_results (
  id bigint GENERATED BY DEFAULT AS IDENTITY NOT NULL,
  user_id uuid NOT NULL,
  attempt_id uuid,
  sense_id integer NOT NULL,
  is_correct boolean NOT NULL,
  selected_answer text,
  correct_answer text,
  response_time_ms integer,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT word_quiz_results_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_wqr_user ON public.word_quiz_results USING btree (user_id);

-- Live dim_exercise_types rows (type_code -> family), 2026-11-19.
INSERT INTO public.dim_exercise_types (type_code, family) VALUES
  ('classifier_match', 'form_production'), ('cloze_completion', 'meaning_recall'),
  ('cloze_typed', 'form_production'), ('collocation_gap_fill', 'collocation'),
  ('collocation_repair', 'collocation'), ('counter_match', 'form_production'),
  ('definition_match', 'form_recognition'), ('hanzi_to_pinyin', 'form_recognition'),
  ('jumbled_sentence', 'form_production'), ('kanji_to_reading', 'form_recognition'),
  ('listening_flashcard', 'form_recognition'), ('morphology_slot', 'form_production'),
  ('nl_tl_translation', 'meaning_recall'), ('particle_selection', 'form_production'),
  ('phonetic_recognition', 'form_recognition'), ('pinyin_to_hanzi', 'form_recognition'),
  ('reading_to_kanji', 'form_recognition'), ('semantic_discrimination', 'semantic_discrimination'),
  ('spot_incorrect_part', 'semantic_discrimination'), ('spot_incorrect_sentence', 'semantic_discrimination'),
  ('synonym_antonym_match', 'semantic_discrimination'), ('text_flashcard', 'meaning_recall'),
  ('timed_speed_round', 'fluency'), ('tl_nl_translation', 'meaning_recall'),
  ('tone_id_word', 'form_recognition'), ('word_family', 'form_production');

-- Supabase default privileges: service_role has ALL on public tables (anon/authenticated also
-- receive table grants on Supabase, but the report functions are not executable by them).
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT USAGE ON SCHEMA storage TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA storage TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
