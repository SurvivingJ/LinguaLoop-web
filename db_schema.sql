-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.flagged_content (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  content_hash text NOT NULL,
  content_type text NOT NULL,
  flagged_categories jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT flagged_content_pkey PRIMARY KEY (id),
  CONSTRAINT flagged_content_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.questions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  test_id uuid NOT NULL,
  question_id text NOT NULL,
  question_text text NOT NULL,
  question_type text NOT NULL DEFAULT 'multiple_choice'::text CHECK (question_type = ANY (ARRAY['multiple_choice'::text, 'fill_blank'::text, 'true_false'::text, 'matching'::text, 'ordering'::text, 'speaking_prompt'::text, 'writing_prompt'::text])),
  choices jsonb,
  correct_answer jsonb NOT NULL,
  answer_explanation text,
  points integer DEFAULT 1,
  audio_url text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT questions_pkey PRIMARY KEY (id),
  CONSTRAINT questions_test_id_fkey FOREIGN KEY (test_id) REFERENCES public.tests(id)
);
CREATE TABLE public.test_attempts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  test_id uuid NOT NULL,
  score integer NOT NULL CHECK (score >= 0),
  total_questions integer NOT NULL CHECK (total_questions > 0),
  percentage real DEFAULT 
CASE
    WHEN (total_questions > 0) THEN (((score)::real / (total_questions)::real) * (100)::double precision)
    ELSE (0)::double precision
END,
  test_mode text NOT NULL CHECK (test_mode = ANY (ARRAY['listening'::text, 'reading'::text, 'dictation'::text, 'grammar'::text, 'vocabulary'::text, 'speaking'::text, 'writing'::text])),
  language text NOT NULL,
  user_elo_before integer NOT NULL,
  test_elo_before integer NOT NULL,
  user_elo_after integer NOT NULL,
  test_elo_after integer NOT NULL,
  elo_change integer DEFAULT (user_elo_after - user_elo_before),
  was_free_test boolean DEFAULT false,
  tokens_consumed integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT test_attempts_pkey PRIMARY KEY (id),
  CONSTRAINT test_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT test_attempts_test_id_fkey FOREIGN KEY (test_id) REFERENCES public.tests(id)
);
CREATE TABLE public.test_skill_ratings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  test_id uuid NOT NULL,
  skill_type text NOT NULL CHECK (skill_type = ANY (ARRAY['listening'::text, 'reading'::text, 'dictation'::text, 'grammar'::text, 'vocabulary'::text, 'speaking'::text, 'writing'::text])),
  elo_rating integer DEFAULT 1400 CHECK (elo_rating >= 400 AND elo_rating <= 3000),
  volatility real DEFAULT 1.0 CHECK (volatility > 0::double precision),
  total_attempts integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT test_skill_ratings_pkey PRIMARY KEY (id),
  CONSTRAINT test_skill_ratings_test_id_fkey FOREIGN KEY (test_id) REFERENCES public.tests(id)
);
CREATE TABLE public.tests (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  gen_user uuid NOT NULL,
  slug text NOT NULL UNIQUE,
  language text NOT NULL,
  topic text NOT NULL,
  difficulty integer NOT NULL CHECK (difficulty >= 1 AND difficulty <= 9),
  style text DEFAULT 'academic'::text CHECK (style = ANY (ARRAY['academic'::text, 'conversational'::text, 'business'::text, 'casual'::text, 'technical'::text])),
  tier text NOT NULL DEFAULT 'free-tier'::text CHECK (tier = ANY (ARRAY['free-tier'::text, 'premium-tier'::text, 'enterprise-tier'::text])),
  title text,
  transcript text,
  audio_url text,
  total_attempts integer DEFAULT 0,
  is_active boolean DEFAULT true,
  is_featured boolean DEFAULT false,
  is_custom boolean DEFAULT false,
  generation_model text DEFAULT 'gpt-4.1-nano'::text,
  audio_generated boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT tests_pkey PRIMARY KEY (id),
  CONSTRAINT tests_gen_user_fkey FOREIGN KEY (gen_user) REFERENCES public.users(id)
);
CREATE TABLE public.token_transactions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  tokens_consumed integer DEFAULT 0 CHECK (tokens_consumed >= 0),
  tokens_added integer DEFAULT 0 CHECK (tokens_added >= 0),
  token_balance_after integer NOT NULL CHECK (token_balance_after >= 0),
  action text NOT NULL,
  payment_intent_id text,
  package_id text,
  test_id uuid,
  attempt_id uuid,
  is_valid boolean DEFAULT true,
  invalidated_at timestamp with time zone,
  invalidation_reason text,
  created_by_system boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT token_transactions_pkey PRIMARY KEY (id),
  CONSTRAINT token_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT token_transactions_test_id_fkey FOREIGN KEY (test_id) REFERENCES public.tests(id),
  CONSTRAINT token_transactions_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.test_attempts(id)
);
CREATE TABLE public.user_languages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  language text NOT NULL,
  total_tests_taken integer DEFAULT 0,
  last_test_date date,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_languages_pkey PRIMARY KEY (id),
  CONSTRAINT user_languages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.user_skill_ratings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  language text NOT NULL,
  skill_type text NOT NULL CHECK (skill_type = ANY (ARRAY['listening'::text, 'reading'::text, 'dictation'::text, 'grammar'::text, 'vocabulary'::text, 'speaking'::text, 'writing'::text])),
  elo_rating integer DEFAULT 1200 CHECK (elo_rating >= 400 AND elo_rating <= 3000),
  volatility real DEFAULT 2.0 CHECK (volatility > 0::double precision),
  tests_taken integer DEFAULT 0,
  last_test_date date,
  current_streak integer DEFAULT 0,
  longest_streak integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_skill_ratings_pkey PRIMARY KEY (id),
  CONSTRAINT user_skill_ratings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.user_tokens (
  user_id uuid NOT NULL,
  purchased_tokens integer DEFAULT 0 CHECK (purchased_tokens >= 0),
  bonus_tokens integer DEFAULT 0 CHECK (bonus_tokens >= 0),
  total_tokens_earned integer DEFAULT 0,
  total_tokens_spent integer DEFAULT 0,
  total_tokens_purchased integer DEFAULT 0,
  tokens_spent_tests integer DEFAULT 0,
  tokens_spent_generation integer DEFAULT 0,
  tokens_spent_premium_features integer DEFAULT 0,
  referral_tokens_earned integer DEFAULT 0,
  achievement_tokens_earned integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_tokens_pkey PRIMARY KEY (user_id),
  CONSTRAINT user_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.users (
  id uuid NOT NULL,
  email text NOT NULL UNIQUE,
  display_name text,
  email_verified boolean DEFAULT false,
  total_tests_taken integer DEFAULT 0,
  total_tests_generated integer DEFAULT 0,
  last_activity_at timestamp with time zone,
  last_free_test_date date DEFAULT (CURRENT_DATE - '1 day'::interval),
  free_tests_used_today integer DEFAULT 0,
  total_free_tests_used integer DEFAULT 0,
  subscription_tier text DEFAULT 'free'::text CHECK (subscription_tier = ANY (ARRAY['free'::text, 'premium'::text, 'enterprise'::text, 'moderator'::text, 'admin'::text])),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  last_login timestamp with time zone DEFAULT now(),
  CONSTRAINT users_pkey PRIMARY KEY (id),
  CONSTRAINT users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id)
);
CREATE TABLE public.users_backup (
  id uuid,
  email character varying,
  created_at timestamp with time zone,
  updated_at timestamp with time zone,
  last_login timestamp with time zone,
  display_name character varying,
  native_language character varying,
  target_languages jsonb,
  timezone character varying,
  is_active boolean,
  email_verified boolean
);