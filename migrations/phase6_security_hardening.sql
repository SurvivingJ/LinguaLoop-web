-- ============================================================================
-- Phase 6: Security Hardening
-- Date: 2026-04-12
--
-- 6.1 Enable RLS on users table
-- 6.2 Enable RLS on unprotected dimension tables
-- 6.3 Audit SECURITY DEFINER — fix exposed functions
-- ============================================================================


-- ============================================================================
-- 6.1 Enable RLS on users table
-- ============================================================================
-- Currently RLS disabled despite containing email, subscription tier,
-- organization membership, and activity data. A compromised client token
-- could read/modify any user's profile via direct Supabase client access.
--
-- IMPORTANT: Before running this migration, audit all Python code paths
-- that read/write the users table to ensure they use service_role client
-- for backend operations. Test in staging first.

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Users can read their own profile
CREATE POLICY "Users read own profile"
    ON public.users
    FOR SELECT
    USING (auth.uid() = id);

-- Users can update their own non-sensitive fields
CREATE POLICY "Users update own profile"
    ON public.users
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Service role (Python backend) has full access
CREATE POLICY "Service role full access on users"
    ON public.users
    FOR ALL
    USING (auth.role() = 'service_role');

-- Admin can read all users (for admin dashboard)
CREATE POLICY "Admin read all users"
    ON public.users
    FOR SELECT
    USING (is_admin(auth.uid()));


-- ============================================================================
-- 6.2 Enable RLS on unprotected dimension/infrastructure tables
-- ============================================================================

-- dim_complexity_tiers: read-only reference data
ALTER TABLE public.dim_complexity_tiers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read complexity tiers"
    ON public.dim_complexity_tiers
    FOR SELECT
    USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY "Service role manage complexity tiers"
    ON public.dim_complexity_tiers
    FOR ALL
    USING (auth.role() = 'service_role');

-- dim_question_types: read-only reference data
ALTER TABLE public.dim_question_types ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read question types"
    ON public.dim_question_types
    FOR SELECT
    USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY "Service role manage question types"
    ON public.dim_question_types
    FOR ALL
    USING (auth.role() = 'service_role');

-- dim_status: read-only reference data
ALTER TABLE public.dim_status ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read status codes"
    ON public.dim_status
    FOR SELECT
    USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY "Service role manage status codes"
    ON public.dim_status
    FOR ALL
    USING (auth.role() = 'service_role');

-- dim_lens: read-only reference data
ALTER TABLE public.dim_lens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read lens codes"
    ON public.dim_lens
    FOR SELECT
    USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY "Service role manage lens codes"
    ON public.dim_lens
    FOR ALL
    USING (auth.role() = 'service_role');

-- dim_grammar_patterns: read-only reference data
ALTER TABLE public.dim_grammar_patterns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read grammar patterns"
    ON public.dim_grammar_patterns
    FOR SELECT
    USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY "Service role manage grammar patterns"
    ON public.dim_grammar_patterns
    FOR ALL
    USING (auth.role() = 'service_role');

-- app_error_logs: authenticated users can insert, only admin/service can read
ALTER TABLE public.app_error_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated insert error logs"
    ON public.app_error_logs
    FOR INSERT
    WITH CHECK (auth.uid() IS NOT NULL OR auth.role() = 'service_role');

CREATE POLICY "Admin and service read error logs"
    ON public.app_error_logs
    FOR SELECT
    USING (is_admin(auth.uid()) OR auth.role() = 'service_role');

CREATE POLICY "Service role manage error logs"
    ON public.app_error_logs
    FOR ALL
    USING (auth.role() = 'service_role');


-- ============================================================================
-- 6.3 Audit SECURITY DEFINER — fix exposed functions
-- ============================================================================
-- Functions that access RLS-protected tables but run as the calling user
-- will fail after RLS is enabled. These need SECURITY DEFINER + search_path.

-- get_active_languages: reads dim_languages (RLS enabled)
CREATE OR REPLACE FUNCTION public.get_active_languages()
RETURNS TABLE(id integer, language_code text, language_name text, native_name text)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        dl.id::INTEGER,
        dl.language_code::TEXT,
        dl.language_name::TEXT,
        COALESCE(dl.native_name, dl.language_name)::TEXT AS native_name
    FROM dim_languages dl
    WHERE dl.is_active = true
    ORDER BY dl.display_order;
END;
$function$;

-- get_next_category: reads categories + dim_status
CREATE OR REPLACE FUNCTION public.get_next_category()
RETURNS TABLE(
    id integer,
    name text,
    status_id integer,
    target_language_id integer,
    last_used_at timestamp with time zone,
    cooldown_days integer
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.name::TEXT,
        c.status_id,
        c.target_language_id,
        c.last_used_at,
        c.cooldown_days
    FROM categories c
    JOIN dim_status s ON c.status_id = s.id
    WHERE s.status_code = 'active'
      AND c.target_language_id IS NULL
      AND (
          c.last_used_at IS NULL
          OR c.last_used_at < NOW() - (c.cooldown_days || ' days')::INTERVAL
      )
    ORDER BY c.last_used_at NULLS FIRST
    LIMIT 1;
END;
$function$;

-- match_topics: reads topics (no RLS but good practice for DEFINER + search_path)
CREATE OR REPLACE FUNCTION public.match_topics(
    query_category integer,
    query_embedding vector,
    match_threshold double precision DEFAULT 0.85,
    match_count integer DEFAULT 5
)
RETURNS TABLE(id uuid, concept_english text, similarity double precision)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.concept_english,
        (1 - (t.embedding <=> query_embedding))::FLOAT AS similarity
    FROM topics t
    WHERE t.category_id = query_category
      AND t.embedding IS NOT NULL
      AND (1 - (t.embedding <=> query_embedding)) > match_threshold
    ORDER BY t.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$;

-- get_word_quiz_candidates: reads user_vocabulary_knowledge + dim tables
CREATE OR REPLACE FUNCTION public.get_word_quiz_candidates(
    p_user_id uuid,
    p_sense_ids integer[],
    p_language_id smallint,
    p_max_words integer DEFAULT 5
)
RETURNS TABLE(
    out_sense_id integer,
    out_lemma text,
    out_definition text,
    out_pronunciation text,
    out_p_known numeric,
    out_score numeric
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        uvk.sense_id,
        dv.lemma,
        dws.definition,
        dws.pronunciation,
        uvk.p_known,
        (uvk.p_known * (1 - uvk.p_known) *
         (1.0 / GREATEST(1.0, ln(GREATEST(1.0, COALESCE(dv.frequency_rank, 1.0)::numeric))))
        ) AS score
    FROM user_vocabulary_knowledge uvk
    JOIN dim_word_senses dws ON dws.id = uvk.sense_id
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE uvk.user_id = p_user_id
      AND uvk.sense_id = ANY(p_sense_ids)
      AND uvk.p_known BETWEEN 0.25 AND 0.75
      AND uvk.status != 'user_marked_unknown'
    ORDER BY score DESC
    LIMIT p_max_words;
END;
$function$;

-- get_vocab_recommendations: reads tests + user_vocabulary + user_skill_ratings
-- Must DROP first because return type (OUT parameters) changed from original definition
DROP FUNCTION IF EXISTS public.get_vocab_recommendations(uuid, integer, double precision, double precision, integer);

CREATE OR REPLACE FUNCTION public.get_vocab_recommendations(
    p_user_id uuid,
    p_language_id integer,
    p_target_unknown_min double precision DEFAULT 0.03,
    p_target_unknown_max double precision DEFAULT 0.07,
    p_limit integer DEFAULT 10
)
RETURNS TABLE(
    id uuid,
    title text,
    slug text,
    unknown_pct float,
    unknown_count integer
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_known_sense_ids integer[];
    v_user_elo int;
BEGIN
    SELECT known_sense_ids INTO v_known_sense_ids
    FROM user_vocabulary
    WHERE user_id = p_user_id AND language_id = p_language_id;

    SELECT elo_rating INTO v_user_elo
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id
    LIMIT 1;

    IF v_known_sense_ids IS NULL THEN v_known_sense_ids := '{}'; END IF;
    IF v_user_elo IS NULL THEN v_user_elo := 1200; END IF;

    RETURN QUERY
    SELECT
        t.id,
        t.title,
        t.slug,
        (CARDINALITY(t.vocab_sense_ids) - CARDINALITY(t.vocab_sense_ids & v_known_sense_ids))::float
          / NULLIF(CARDINALITY(t.vocab_sense_ids), 0) as u_pct,
        (CARDINALITY(t.vocab_sense_ids) - CARDINALITY(t.vocab_sense_ids & v_known_sense_ids)) as u_count
    FROM public.tests t
    LEFT JOIN public.test_skill_ratings tsr ON tsr.test_id = t.id
    WHERE
        t.language_id = p_language_id
        AND t.is_active = true
        AND (tsr.elo_rating BETWEEN (v_user_elo - 200) AND (v_user_elo + 200) OR tsr.elo_rating IS NULL)
        AND CARDINALITY(t.vocab_sense_ids) > 0
    HAVING
        (CARDINALITY(t.vocab_sense_ids) - CARDINALITY(t.vocab_sense_ids & v_known_sense_ids))::float
          / NULLIF(CARDINALITY(t.vocab_sense_ids), 0)
        BETWEEN p_target_unknown_min AND p_target_unknown_max
    ORDER BY ABS(u_pct - 0.05)
    LIMIT p_limit;
END;
$function$;
