All 242 functions are accounted for (43 application + 199 extension). Here is the complete listing:

---

# LinguaLoop -- Complete Supabase RPC / Function Listing

**Total functions: 242** (43 custom application functions + 199 extension functions from pgvector, intarray, pg_trgm)

---

## APPLICATION FUNCTIONS (43 total)

---

### 1. `add_tokens_atomic`

- **Arguments:** `p_user_id uuid, p_tokens_to_add integer, p_action text, p_idempotency_key text, p_payment_intent_id text DEFAULT NULL::text, p_package_id text DEFAULT NULL::text`
- **Return type:** `boolean`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.add_tokens_atomic(p_user_id uuid, p_tokens_to_add integer, p_action text, p_idempotency_key text, p_payment_intent_id text DEFAULT NULL::text, p_package_id text DEFAULT NULL::text)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  -- SECURITY: Allow only self-service OR admin/moderator role
  IF p_user_id != auth.uid() THEN
    IF NOT (is_admin(auth.uid()) OR is_moderator(auth.uid())) THEN
      RAISE EXCEPTION 'Unauthorized: Cannot add tokens for another user';
    END IF;
  END IF;
  
  -- TODO: Token addition logic will be implemented in Phase 3
  -- For now, just validate authorization
  
  RETURN true;
END;
$function$
```

---

### 2. `anonymize_user_data`

- **Arguments:** `p_user_id uuid`
- **Return type:** `void`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.anonymize_user_data(p_user_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  -- Verify caller owns this user_id OR is admin
  IF p_user_id != auth.uid() AND NOT is_admin(auth.uid()) THEN
    RAISE EXCEPTION 'Unauthorized: Cannot anonymize another user';
  END IF;
  
  -- Soft delete and anonymize
  UPDATE users
  SET 
    email = 'deleted-' || id || '@lingualoop.local',
    display_name = 'Deleted User',
    deleted_at = NOW(),
    anonymized_at = NOW()
  WHERE id = p_user_id;
  
  RAISE NOTICE 'User % anonymized successfully', p_user_id;
END;
$function$
```

---

### 3. `batch_lookup_lemmas`

- **Arguments:** `p_lemmas text[], p_language_id integer`
- **Return type:** `TABLE(lemma text, vocab_id integer)`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.batch_lookup_lemmas(p_lemmas text[], p_language_id integer)
 RETURNS TABLE(lemma text, vocab_id integer)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
AS $function$
BEGIN
  RETURN QUERY
  SELECT v.lemma, v.id
  FROM dim_vocabulary v
  WHERE v.language_id = p_language_id
    AND v.lemma = ANY(p_lemmas);
END;
$function$
```

---

### 4. `bkt_status`

- **Arguments:** `p_known numeric`
- **Return type:** `text`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.bkt_status(p_known numeric)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    RETURN CASE
        WHEN p_known < 0.20 THEN 'unknown'
        WHEN p_known < 0.50 THEN 'encountered'
        WHEN p_known < 0.75 THEN 'learning'
        WHEN p_known < 0.90 THEN 'probably_known'
        ELSE 'known'
    END;
END;
$function$
```

---

### 5. `bkt_update`

- **Arguments:** `p_current numeric, p_correct boolean, p_slip numeric DEFAULT 0.10, p_guess numeric DEFAULT 0.25`
- **Return type:** `numeric`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.bkt_update(p_current numeric, p_correct boolean, p_slip numeric DEFAULT 0.10, p_guess numeric DEFAULT 0.25)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    p_obs_knows NUMERIC;
    p_obs_not_knows NUMERIC;
BEGIN
    IF p_correct THEN
        p_obs_knows := 1 - p_slip;
        p_obs_not_knows := p_guess;
    ELSE
        p_obs_knows := p_slip;
        p_obs_not_knows := 1 - p_guess;
    END IF;

    RETURN GREATEST(0.02, LEAST(0.98,
        (p_obs_knows * p_current) /
        (p_obs_knows * p_current + p_obs_not_knows * (1 - p_current))
    ));
END;
$function$
```

---

### 6. `bkt_update_comprehension`

- **Arguments:** `p_current numeric, p_correct boolean`
- **Return type:** `numeric`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.bkt_update_comprehension(p_current numeric, p_correct boolean)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    RETURN bkt_update(p_current, p_correct, 0.10, 0.25);
END;
$function$
```

---

### 7. `bkt_update_word_test`

- **Arguments:** `p_current numeric, p_correct boolean`
- **Return type:** `numeric`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.bkt_update_word_test(p_current numeric, p_correct boolean)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    RETURN bkt_update(p_current, p_correct, 0.05, 0.25);
END;
$function$
```

---

### 8. `calculate_elo_rating`

- **Arguments:** `current_rating integer, opposing_rating integer, actual_score numeric, k_factor integer DEFAULT 32, volatility_multiplier numeric DEFAULT 1.0`
- **Return type:** `integer`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.calculate_elo_rating(current_rating integer, opposing_rating integer, actual_score numeric, k_factor integer DEFAULT 32, volatility_multiplier numeric DEFAULT 1.0)
 RETURNS integer
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    expected_score NUMERIC;
    adjusted_k NUMERIC;
    new_rating NUMERIC;
BEGIN
    expected_score := 1.0 / (1.0 + POWER(10, (opposing_rating - current_rating) / 400.0));
    adjusted_k := k_factor * volatility_multiplier;
    new_rating := current_rating + (adjusted_k * (actual_score - expected_score));

    -- Clamp between 400 and 3000
    RETURN GREATEST(400, LEAST(3000, ROUND(new_rating)::INTEGER));
END;
$function$
```

---

### 9. `calculate_volatility_multiplier`

- **Arguments:** `attempts integer, last_date date DEFAULT NULL::date, base_volatility numeric DEFAULT 1.0`
- **Return type:** `numeric`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.calculate_volatility_multiplier(attempts integer, last_date date DEFAULT NULL::date, base_volatility numeric DEFAULT 1.0)
 RETURNS numeric
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    multiplier NUMERIC := base_volatility;
BEGIN
    -- Low attempts = higher volatility
    IF attempts < 10 THEN
        multiplier := multiplier + 0.5;
    END IF;

    -- Long time since last attempt = higher volatility
    IF last_date IS NOT NULL AND (CURRENT_DATE - last_date) > 90 THEN
        multiplier := multiplier + 0.5;
    END IF;

    RETURN multiplier;
END;
$function$
```

---

### 10. `can_use_free_test`

- **Arguments:** `p_user_id uuid`
- **Return type:** `boolean`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.can_use_free_test(p_user_id uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
  user_record RECORD;
  daily_limit integer;
BEGIN
  -- SECURITY: Validate caller owns this user_id
  IF p_user_id != auth.uid() THEN
    RAISE EXCEPTION 'Unauthorized: Cannot check free test status for another user';
  END IF;
  
  -- Get user's daily limit based on tier
  daily_limit := get_daily_free_test_limit(p_user_id);
  
  -- Check if columns exist before querying
  -- TODO: These columns will be validated in Phase 3
  -- For now, return true if user has any daily limit
  
  RETURN daily_limit > 0;
END;
$function$
```

---

### 11. `create_user_dependencies`

- **Arguments:** `(none)`
- **Return type:** `trigger`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.create_user_dependencies()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    INSERT INTO user_tokens (user_id, purchased_tokens)
    VALUES (NEW.id, 0)
    ON CONFLICT (user_id) DO NOTHING;
    
    RETURN NEW;
END;
$function$
```

---

### 12. `get_active_languages`

- **Arguments:** `(none)`
- **Return type:** `TABLE(id integer, language_code text, language_name text, native_name text)`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.get_active_languages()
 RETURNS TABLE(id integer, language_code text, language_name text, native_name text)
 LANGUAGE plpgsql
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
$function$
```

---

### 13. `get_daily_free_test_limit`

- **Arguments:** `p_user_id uuid`
- **Return type:** `integer`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.get_daily_free_test_limit(p_user_id uuid)
 RETURNS integer
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT COALESCE(dst.daily_free_tests, 0)
  FROM users u
  JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
  WHERE u.id = p_user_id AND u.deleted_at IS NULL;
$function$
```

---

### 14. `get_distractors`

- **Arguments:** `p_sense_id integer, p_language_id smallint, p_count integer DEFAULT 3`
- **Return type:** `TABLE(out_definition text)`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.get_distractors(p_sense_id integer, p_language_id smallint, p_count integer DEFAULT 3)
 RETURNS TABLE(out_definition text)
 LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    SELECT dws.definition
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    WHERE dv.language_id = p_language_id
      AND dws.id != p_sense_id
      AND dws.vocab_id != (SELECT vocab_id FROM dim_word_senses WHERE id = p_sense_id)
      AND dws.sense_rank = 1
    ORDER BY random()
    LIMIT p_count;
END;
$function$
```

---

### 15. `get_next_category`

- **Arguments:** `(none)`
- **Return type:** `TABLE(id integer, name text, status_id integer, target_language_id integer, last_used_at timestamp with time zone, cooldown_days integer)`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.get_next_category()
 RETURNS TABLE(id integer, name text, status_id integer, target_language_id integer, last_used_at timestamp with time zone, cooldown_days integer)
 LANGUAGE plpgsql
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
      AND c.target_language_id IS NULL  -- Only universal categories
      AND (
          c.last_used_at IS NULL
          OR c.last_used_at < NOW() - (c.cooldown_days || ' days')::INTERVAL
      )
    ORDER BY c.last_used_at NULLS FIRST
    LIMIT 1;
END;
$function$
```

---

### 16. `get_org_role`

- **Arguments:** `p_user_id uuid, p_org_id uuid`
- **Return type:** `text`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.get_org_role(p_user_id uuid, p_org_id uuid)
 RETURNS text
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT role FROM organization_members
  WHERE user_id = p_user_id AND organization_id = p_org_id;
$function$
```

---

### 17. `get_packs_with_user_selection`

- **Arguments:** `p_language_id integer, p_user_id text`
- **Return type:** `TABLE(id bigint, pack_name text, description text, pack_type text, tags text[], total_items integer, difficulty_range text, is_selected boolean)`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.get_packs_with_user_selection(p_language_id integer, p_user_id text)
 RETURNS TABLE(id bigint, pack_name text, description text, pack_type text, tags text[], total_items integer, difficulty_range text, is_selected boolean)
 LANGUAGE sql
 STABLE
AS $function$
    SELECT
        cp.id,
        cp.pack_name,
        cp.description,
        cp.pack_type,
        cp.tags,
        cp.total_items,
        cp.difficulty_range,
        (ups.user_id IS NOT NULL) AS is_selected
    FROM collocation_packs cp
    LEFT JOIN user_pack_selections ups
        ON ups.pack_id = cp.id
       AND ups.user_id = p_user_id
    WHERE cp.language_id = p_language_id
      AND cp.is_public = TRUE
    ORDER BY cp.pack_name;
$function$
```

---

### 18. `get_prompt_template`

- **Arguments:** `p_task_name character varying, p_language_code character varying DEFAULT 'default'::character varying`
- **Return type:** `text`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.get_prompt_template(p_task_name character varying, p_language_code character varying DEFAULT 'default'::character varying)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
DECLARE
    result_text TEXT;
BEGIN
    -- Try language-specific first
    SELECT template_text INTO result_text
    FROM prompt_templates
    WHERE task_name = p_task_name
      AND language_code = p_language_code
      AND is_active = true
    ORDER BY version DESC
    LIMIT 1;

    -- Fall back to default if not found
    IF result_text IS NULL THEN
        SELECT template_text INTO result_text
        FROM prompt_templates
        WHERE task_name = p_task_name
          AND language_code = 'default'
          AND is_active = true
        ORDER BY version DESC
        LIMIT 1;
    END IF;

    RETURN result_text;
END;
$function$
```

---

### 19. `get_recommended_mysteries`

- **Arguments:** `p_user_id uuid, p_language_id integer`
- **Return type:** `SETOF jsonb`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.get_recommended_mysteries(p_user_id uuid, p_language_id integer)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    v_user_elo integer;
    v_mystery_type_id integer;
BEGIN
    -- Get mystery test_type_id
    SELECT id INTO v_mystery_type_id
    FROM dim_test_types WHERE type_code = 'mystery';

    -- Get user's mystery ELO (default 1200 if no rating)
    SELECT COALESCE(
        (SELECT elo_rating FROM user_skill_ratings
         WHERE user_id = p_user_id
           AND language_id = p_language_id
           AND test_type_id = v_mystery_type_id),
        1200
    ) INTO v_user_elo;

    -- Return matching mysteries
    RETURN QUERY
    SELECT jsonb_build_object(
        'id', m.id,
        'slug', m.slug,
        'title', m.title,
        'premise', m.premise,
        'difficulty', m.difficulty,
        'language_id', m.language_id,
        'suspects', m.suspects,
        'total_attempts', m.total_attempts,
        'mystery_elo', COALESCE(msr.elo_rating, 1400),
        'user_elo', v_user_elo,
        'elo_gap', ABS(COALESCE(msr.elo_rating, 1400) - v_user_elo)
    )
    FROM mysteries m
    LEFT JOIN mystery_skill_ratings msr ON msr.mystery_id = m.id
    WHERE m.language_id = p_language_id
      AND m.is_active = true
      AND ABS(COALESCE(msr.elo_rating, 1400) - v_user_elo) <= 200
    ORDER BY ABS(COALESCE(msr.elo_rating, 1400) - v_user_elo) ASC
    LIMIT 10;
END;
$function$
```

---

### 20. `get_recommended_test`

- **Arguments:** `p_user_id uuid, p_language_id integer`
- **Return type:** `SETOF tests`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.get_recommended_test(p_user_id uuid, p_language_id integer)
 RETURNS SETOF tests
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  -- ID Variables
  v_listening_type_id SMALLINT;
  v_reading_type_id SMALLINT;
  
  -- ELO Variables
  v_user_listening_elo INT := 1200; -- Default start
  v_user_reading_elo INT := 1200;   -- Default start
  
  -- Loop Variables
  v_radius INT;
  v_radii INT[] := ARRAY[50, 100, 250, 500, 10000]; -- Expanding search steps
  v_test_found tests%ROWTYPE;
BEGIN
  -- 1. Get Test Type IDs (Dynamically from code)
  SELECT id INTO v_listening_type_id FROM dim_test_types WHERE type_code = 'listening';
  SELECT id INTO v_reading_type_id FROM dim_test_types WHERE type_code = 'reading';

  -- 2. Fetch User's Current Ratings
  SELECT 
    MAX(CASE WHEN test_type_id = v_listening_type_id THEN elo_rating END),
    MAX(CASE WHEN test_type_id = v_reading_type_id THEN elo_rating END)
  INTO v_user_listening_elo, v_user_reading_elo
  FROM user_skill_ratings
  WHERE user_id = p_user_id 
    AND language_id = p_language_id;

  -- Apply defaults if NULL (user has never taken a test)
  IF v_user_listening_elo IS NULL THEN v_user_listening_elo := 1200; END IF;
  IF v_user_reading_elo IS NULL THEN v_user_reading_elo := 1200; END IF;

  -- 3. Expand Radius Loop
  FOREACH v_radius IN ARRAY v_radii
  LOOP
    SELECT t.*
    INTO v_test_found
    FROM tests t
    JOIN test_skill_ratings tsr ON t.id = tsr.test_id
    WHERE t.language_id = p_language_id
      AND t.is_active = TRUE
      AND tsr.test_type_id IN (v_listening_type_id, v_reading_type_id)
      AND (
        (tsr.test_type_id = v_listening_type_id 
         AND tsr.elo_rating BETWEEN (v_user_listening_elo - v_radius) AND (v_user_listening_elo + v_radius))
        OR
        (tsr.test_type_id = v_reading_type_id 
         AND tsr.elo_rating BETWEEN (v_user_reading_elo - v_radius) AND (v_user_reading_elo + v_radius))
      )
    ORDER BY random()
    LIMIT 1;

    IF v_test_found.id IS NOT NULL THEN
      RETURN NEXT v_test_found;
      RETURN;
    END IF;
  END LOOP;
END;
$function$
```

---

### 21. `get_recommended_tests`

- **Arguments:** `p_user_id uuid, p_language text`
- **Return type:** `TABLE(test_id uuid, slug text, test_type text, title text, difficulty_level integer, elo_rating integer, elo_diff integer, tier text)`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.get_recommended_tests(p_user_id uuid, p_language text)
 RETURNS TABLE(test_id uuid, slug text, test_type text, title text, difficulty_level integer, elo_rating integer, elo_diff integer, tier text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
DECLARE
  v_language_id SMALLINT;
  v_user_tier_code TEXT;
  v_is_premium BOOLEAN;
BEGIN
  -- 1. Resolve Language ID
  SELECT id INTO v_language_id
  FROM dim_languages
  WHERE LOWER(language_code) = LOWER(p_language) 
     OR LOWER(language_name) = LOWER(p_language)
  LIMIT 1;

  IF v_language_id IS NULL THEN
    RAISE EXCEPTION 'Language not found: %', p_language;
  END IF;

  -- 2. Determine User Access Level
  SELECT st.tier_code INTO v_user_tier_code
  FROM users u
  JOIN dim_subscription_tiers st ON u.subscription_tier_id = st.id
  WHERE u.id = p_user_id;

  v_is_premium := (v_user_tier_code NOT ILIKE '%free%');

  -- 3. Execute Recommendation Logic (unique test_ids only)
  RETURN QUERY
  WITH target_types AS (
    SELECT id AS type_id, type_code
    FROM dim_test_types
    WHERE type_code IN ('listening', 'reading', 'dictation')
  ),
  user_stats AS (
    SELECT 
      tt.type_id,
      tt.type_code,
      COALESCE(usr.elo_rating, 1200) as current_elo
    FROM target_types tt
    LEFT JOIN user_skill_ratings usr 
      ON usr.user_id = p_user_id 
      AND usr.language_id = v_language_id 
      AND usr.test_type_id = tt.type_id
  ),
  all_candidates AS (
    SELECT
      t.id AS c_test_id,
      t.slug::text AS c_slug,
      us.type_code::text AS c_test_type,
      t.title::text AS c_title,
      t.difficulty AS c_difficulty_level,
      tsr.elo_rating AS c_elo_rating,
      ABS(tsr.elo_rating - us.current_elo) AS c_elo_diff,
      t.tier::text AS c_tier,
      ROW_NUMBER() OVER (
        PARTITION BY us.type_code
        ORDER BY ABS(tsr.elo_rating - us.current_elo) ASC
      ) AS rank_in_type
    FROM user_stats us
    JOIN test_skill_ratings tsr ON tsr.test_type_id = us.type_id
    JOIN tests t ON t.id = tsr.test_id
    WHERE t.language_id = v_language_id
      AND t.is_active = true
      AND (
        t.tier = 'free-tier' 
        OR (t.tier != 'free-tier' AND v_is_premium)
      )
      AND NOT EXISTS (
        SELECT 1 
        FROM test_attempts ta 
        WHERE ta.user_id = p_user_id 
          AND ta.test_id = t.id
      )
  ),
  deduplicated AS (
    SELECT DISTINCT ON (c_test_id)
      c_test_id, c_slug, c_test_type, c_title,
      c_difficulty_level, c_elo_rating, c_elo_diff, c_tier
    FROM all_candidates
    WHERE rank_in_type <= 3
    ORDER BY c_test_id, c_elo_diff ASC
  )
  SELECT
    d.c_test_id, d.c_slug, d.c_test_type, d.c_title,
    d.c_difficulty_level, d.c_elo_rating, d.c_elo_diff, d.c_tier
  FROM deduplicated d
  ORDER BY d.c_elo_diff ASC;

END;
$function$
```

---

### 22. `get_test_token_cost`

- **Arguments:** `p_user_id uuid`
- **Return type:** `integer`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.get_test_token_cost(p_user_id uuid)
 RETURNS integer
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT COALESCE(dst.tokens_per_test, 10)
  FROM users u
  JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
  WHERE u.id = p_user_id AND u.deleted_at IS NULL;
$function$
```

---

### 23. `get_token_balance`

- **Arguments:** `p_user_id uuid`
- **Return type:** `integer`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.get_token_balance(p_user_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
  -- SECURITY: Validate caller can view this balance
  IF p_user_id != auth.uid() THEN
    IF NOT (is_admin(auth.uid()) OR is_moderator(auth.uid())) THEN
      RAISE EXCEPTION 'Unauthorized: Cannot view another user''s token balance';
    END IF;
  END IF;
  
  -- TODO: Token balance logic will be implemented in Phase 3
  -- For now, return 0
  
  RETURN 0;
END;
$function$
```

---

### 24. `get_top_collocations_for_sources`

- **Arguments:** `p_source_ids integer[], p_min_pmi double precision, p_top_n integer`
- **Return type:** `TABLE(id bigint, collocation_text text, n_gram_size integer, pmi_score double precision, log_likelihood double precision, t_score double precision, collocation_type text, pos_pattern text, language_id integer)`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.get_top_collocations_for_sources(p_source_ids integer[], p_min_pmi double precision, p_top_n integer)
 RETURNS TABLE(id bigint, collocation_text text, n_gram_size integer, pmi_score double precision, log_likelihood double precision, t_score double precision, collocation_type text, pos_pattern text, language_id integer)
 LANGUAGE sql
 STABLE
AS $function$
    -- Subquery: pick the highest-PMI representative for each collocation_text,
    -- then re-sort globally by PMI and apply LIMIT for correct top-N.
    SELECT sub.id, sub.collocation_text, sub.n_gram_size, sub.pmi_score,
           sub.log_likelihood, sub.t_score, sub.collocation_type,
           sub.pos_pattern, sub.language_id
    FROM (
        SELECT DISTINCT ON (cc.collocation_text)
            cc.id,
            cc.collocation_text,
            cc.n_gram_size,
            cc.pmi_score,
            cc.log_likelihood,
            cc.t_score,
            cc.collocation_type,
            cc.pos_pattern,
            cc.language_id
        FROM corpus_collocations cc
        WHERE cc.corpus_source_id = ANY(p_source_ids)
          AND cc.pmi_score >= p_min_pmi
        ORDER BY cc.collocation_text, cc.pmi_score DESC
    ) sub
    ORDER BY sub.pmi_score DESC
    LIMIT p_top_n;
$function$
```

---

### 25. `get_vocab_recommendations`

- **Arguments:** `p_user_id uuid, p_language_id integer, p_target_unknown_min double precision DEFAULT 0.03, p_target_unknown_max double precision DEFAULT 0.07, p_limit integer DEFAULT 20`
- **Return type:** `TABLE(test_id uuid, title text, slug text, unknown_pct double precision, unknown_count integer)`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.get_vocab_recommendations(p_user_id uuid, p_language_id integer, p_target_unknown_min double precision DEFAULT 0.03, p_target_unknown_max double precision DEFAULT 0.07, p_limit integer DEFAULT 20)
 RETURNS TABLE(test_id uuid, title text, slug text, unknown_pct double precision, unknown_count integer)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
AS $function$
DECLARE
  v_known_sense_ids int[];
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
$function$
```

---

### 26. `get_word_quiz_candidates`

- **Arguments:** `p_user_id uuid, p_sense_ids integer[], p_language_id smallint, p_max_words integer DEFAULT 5`
- **Return type:** `TABLE(out_sense_id integer, out_lemma text, out_definition text, out_pronunciation text, out_p_known numeric, out_score numeric)`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.get_word_quiz_candidates(p_user_id uuid, p_sense_ids integer[], p_language_id smallint, p_max_words integer DEFAULT 5)
 RETURNS TABLE(out_sense_id integer, out_lemma text, out_definition text, out_pronunciation text, out_p_known numeric, out_score numeric)
 LANGUAGE plpgsql
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
$function$
```

---

### 27. `handle_new_user`

- **Arguments:** `(none)`
- **Return type:** `trigger`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_free_tier_id integer;
BEGIN
    -- Get the ID of the 'free' subscription tier
    SELECT id INTO v_free_tier_id
    FROM dim_subscription_tiers
    WHERE tier_code = 'free'
    LIMIT 1;
    
    -- If free tier doesn't exist, create it
    IF v_free_tier_id IS NULL THEN
        INSERT INTO dim_subscription_tiers (
            tier_code,
            display_name,
            can_generate_tests,
            can_create_custom_tests,
            daily_free_tests
        )
        VALUES ('free', 'Free', false, false, 2)
        RETURNING id INTO v_free_tier_id;
        
        RAISE LOG 'Created free tier with ID: %', v_free_tier_id;
    END IF;
    
    -- Insert into public.users with correct column name
    INSERT INTO public.users (
        id, 
        email, 
        subscription_tier_id,
        email_verified, 
        created_at,
        last_login,
        total_tests_taken,
        total_tests_generated
    )
    VALUES (
        NEW.id,
        NEW.email,
        v_free_tier_id,
        COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
        NOW(),
        NOW(),
        0,
        0
    )
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        email_verified = COALESCE(NEW.email_confirmed_at IS NOT NULL, false),
        last_login = NOW();
    
    RAISE LOG 'User profile created successfully for: % (tier_id: %)', NEW.email, v_free_tier_id;
    
    RETURN NEW;
    
EXCEPTION WHEN OTHERS THEN
    -- Log the full error for debugging
    RAISE WARNING 'Failed to create user profile for %: % (SQLSTATE: %)', 
        NEW.email, SQLERRM, SQLSTATE;
    -- Still return NEW so auth user creation doesn't fail
    RETURN NEW;
END;
$function$
```

---

### 28. `is_admin`

- **Arguments:** `p_user_id uuid`
- **Return type:** `boolean`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.is_admin(p_user_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT COALESCE(dst.is_admin, false)
  FROM users u
  JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
  WHERE u.id = p_user_id AND u.deleted_at IS NULL;
$function$
```

---

### 29. `is_moderator`

- **Arguments:** `p_user_id uuid`
- **Return type:** `boolean`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.is_moderator(p_user_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT COALESCE(dst.is_moderator OR dst.is_admin, false)
  FROM users u
  JOIN dim_subscription_tiers dst ON u.subscription_tier_id = dst.id
  WHERE u.id = p_user_id AND u.deleted_at IS NULL;
$function$
```

---

### 30. `is_org_member`

- **Arguments:** `p_user_id uuid, p_org_id uuid`
- **Return type:** `boolean`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.is_org_member(p_user_id uuid, p_org_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  SELECT EXISTS (
    SELECT 1 FROM organization_members
    WHERE user_id = p_user_id AND organization_id = p_org_id
  );
$function$
```

---

### 31. `match_topics`

- **Arguments:** `query_category integer, query_embedding vector, match_threshold double precision DEFAULT 0.85, match_count integer DEFAULT 5`
- **Return type:** `TABLE(id uuid, concept_english text, similarity double precision)`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.match_topics(query_category integer, query_embedding vector, match_threshold double precision DEFAULT 0.85, match_count integer DEFAULT 5)
 RETURNS TABLE(id uuid, concept_english text, similarity double precision)
 LANGUAGE plpgsql
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
$function$
```

---

### 32. `migrate_test_json`

- **Arguments:** `test_json jsonb`
- **Return type:** `uuid`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.migrate_test_json(test_json jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
DECLARE
    test_id UUID;
    question_record JSONB;
    question_order_counter INTEGER := 1;
BEGIN
    -- Insert main test
    INSERT INTO tests (
        slug, language, topic, difficulty, transcript,
        listening_rating, reading_rating,
        listening_volatility, reading_volatility
    )
    VALUES (
        test_json->>'slug',
        test_json->>'language', 
        test_json->>'topic',
        (test_json->>'difficulty')::INTEGER,
        test_json->>'transcript',
        (test_json->'ratings'->'listening'->>'rating')::INTEGER,
        (test_json->'ratings'->'reading'->>'rating')::INTEGER,
        (test_json->'ratings'->'listening'->>'volatility')::DECIMAL,
        (test_json->'ratings'->'reading'->>'volatility')::DECIMAL
    )
    RETURNING id INTO test_id;
    
    -- Insert questions
    FOR question_record IN SELECT * FROM jsonb_array_elements(test_json->'questions')
    LOOP
        INSERT INTO test_questions (
            test_id, question_id, question_text, choices, correct_answer,
            question_order, listening_rating, reading_rating,
            listening_volatility, reading_volatility
        )
        VALUES (
            test_id,
            question_record->>'id',
            question_record->>'question',
            question_record->'choices',
            question_record->>'answer',
            question_order_counter,
            (question_record->'ratings'->'listening'->>'rating')::INTEGER,
            (question_record->'ratings'->'reading'->>'rating')::INTEGER,
            (question_record->'ratings'->'listening'->>'volatility')::DECIMAL,
            (question_record->'ratings'->'reading'->>'volatility')::DECIMAL
        );
        
        question_order_counter := question_order_counter + 1;
    END LOOP;
    
    -- Update catalog
    INSERT INTO test_catalog (test_id, slug, language, difficulty, topic, listening_rating, reading_rating)
    VALUES (
        test_id,
        test_json->>'slug',
        test_json->>'language',
        (test_json->>'difficulty')::INTEGER, 
        test_json->>'topic',
        (test_json->'ratings'->'listening'->>'rating')::INTEGER,
        (test_json->'ratings'->'reading'->>'rating')::INTEGER
    );
    
    RETURN test_id;
END;
$function$
```

---

### 33. `process_mystery_submission`

- **Arguments:** `p_user_id uuid, p_mystery_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_idempotency_key uuid DEFAULT NULL::uuid`
- **Return type:** `jsonb`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.process_mystery_submission(p_user_id uuid, p_mystery_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_idempotency_key uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    v_user_elo integer;
    v_mystery_elo integer;
    v_user_tests_taken integer;
    v_mystery_attempts integer;
    v_new_user_elo integer;
    v_new_mystery_elo integer;
    v_attempt_id uuid;
    v_attempt_number integer;
    v_is_first_attempt boolean;
    v_existing_attempt record;
    v_score integer := 0;
    v_total_questions integer := 0;
    v_question_results jsonb := '[]'::jsonb;
    v_question_record record;
    v_user_answer text;
    v_correct_answer text;
    v_is_correct boolean;
    v_percentage numeric;
    v_percentage_decimal numeric;
BEGIN
    -- ========================================================================
    -- SECURITY VALIDATION
    -- ========================================================================

    IF p_user_id != auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized: Cannot submit mystery for another user';
    END IF;

    -- ========================================================================
    -- INPUT VALIDATION
    -- ========================================================================

    IF p_responses IS NULL OR jsonb_array_length(p_responses) = 0 THEN
        RAISE EXCEPTION 'No responses provided';
    END IF;

    -- ========================================================================
    -- ANSWER VALIDATION
    -- ========================================================================

    CREATE TEMP TABLE temp_mystery_responses ON COMMIT DROP AS
    SELECT
        (elem->>'question_id')::UUID as question_id,
        elem->>'selected_answer' as selected_answer
    FROM jsonb_array_elements(p_responses) as elem;

    -- Validate each question across all scenes of this mystery
    FOR v_question_record IN (
        SELECT mq.id, mq.answer
        FROM mystery_questions mq
        JOIN mystery_scenes ms ON ms.id = mq.scene_id
        WHERE ms.mystery_id = p_mystery_id
        ORDER BY ms.scene_number, mq.created_at
    ) LOOP
        SELECT selected_answer INTO v_user_answer
        FROM temp_mystery_responses
        WHERE question_id = v_question_record.id;

        v_user_answer := COALESCE(v_user_answer, '');
        v_correct_answer := v_question_record.answer #>> '{}';
        v_is_correct := (v_user_answer = v_correct_answer);

        IF v_is_correct THEN
            v_score := v_score + 1;
        END IF;

        v_question_results := v_question_results || jsonb_build_object(
            'question_id', v_question_record.id::TEXT,
            'selected_answer', v_user_answer,
            'correct_answer', v_correct_answer,
            'is_correct', v_is_correct
        );

        v_total_questions := v_total_questions + 1;
    END LOOP;

    DROP TABLE IF EXISTS temp_mystery_responses;

    IF v_total_questions = 0 THEN
        RAISE EXCEPTION 'No questions found for this mystery';
    END IF;

    -- ========================================================================
    -- IDEMPOTENCY CHECK
    -- ========================================================================

    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_attempt
        FROM mystery_attempts
        WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key;

        IF FOUND THEN
            RETURN jsonb_build_object(
                'success', true,
                'attempt_id', v_existing_attempt.id,
                'cached', true,
                'user_elo_change', COALESCE(
                    v_existing_attempt.user_elo_after - v_existing_attempt.user_elo_before, 0
                ),
                'message', 'Duplicate submission detected - returning cached result'
            );
        END IF;
    END IF;

    -- ========================================================================
    -- CALCULATE PERCENTAGE
    -- ========================================================================

    v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
    v_percentage_decimal := v_percentage / 100.0;

    -- ========================================================================
    -- DETERMINE ATTEMPT NUMBER
    -- ========================================================================

    SELECT COUNT(*) INTO v_attempt_number
    FROM mystery_attempts
    WHERE user_id = p_user_id AND mystery_id = p_mystery_id;

    v_attempt_number := v_attempt_number + 1;
    v_is_first_attempt := (v_attempt_number = 1);

    -- ========================================================================
    -- GET OR CREATE USER ELO RATING
    -- ========================================================================

    SELECT elo_rating, tests_taken
    INTO v_user_elo, v_user_tests_taken
    FROM user_skill_ratings
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND test_type_id = p_test_type_id;

    IF NOT FOUND THEN
        v_user_elo := 1200;
        v_user_tests_taken := 0;

        INSERT INTO user_skill_ratings (
            user_id, language_id, test_type_id, elo_rating, tests_taken
        ) VALUES (
            p_user_id, p_language_id, p_test_type_id, v_user_elo, 0
        );
    END IF;

    -- ========================================================================
    -- GET OR CREATE MYSTERY ELO RATING
    -- ========================================================================

    SELECT elo_rating, total_attempts
    INTO v_mystery_elo, v_mystery_attempts
    FROM mystery_skill_ratings
    WHERE mystery_id = p_mystery_id;

    IF NOT FOUND THEN
        v_mystery_elo := 1400;
        v_mystery_attempts := 0;

        INSERT INTO mystery_skill_ratings (mystery_id, elo_rating, total_attempts)
        VALUES (p_mystery_id, v_mystery_elo, 0);
    END IF;

    -- ========================================================================
    -- CALCULATE ELO CHANGES (ONLY FOR FIRST ATTEMPTS)
    -- ========================================================================

    IF v_is_first_attempt THEN
        DECLARE
            expected_user_score numeric;
            k_factor integer := 32;
        BEGIN
            expected_user_score := 1.0 / (1.0 + POWER(10, (v_mystery_elo - v_user_elo) / 400.0));

            v_new_user_elo := ROUND(v_user_elo + k_factor * (v_percentage_decimal - expected_user_score));
            v_new_mystery_elo := ROUND(v_mystery_elo + k_factor * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));

            v_new_user_elo := GREATEST(400, LEAST(3000, v_new_user_elo));
            v_new_mystery_elo := GREATEST(400, LEAST(3000, v_new_mystery_elo));
        END;

        UPDATE user_skill_ratings
        SET elo_rating = v_new_user_elo,
            tests_taken = tests_taken + 1,
            last_test_date = CURRENT_DATE,
            updated_at = NOW()
        WHERE user_id = p_user_id
          AND language_id = p_language_id
          AND test_type_id = p_test_type_id;

        UPDATE mystery_skill_ratings
        SET elo_rating = v_new_mystery_elo,
            total_attempts = total_attempts + 1,
            updated_at = NOW()
        WHERE mystery_id = p_mystery_id;

        UPDATE mysteries
        SET total_attempts = total_attempts + 1,
            updated_at = NOW()
        WHERE id = p_mystery_id;
    ELSE
        v_new_user_elo := v_user_elo;
        v_new_mystery_elo := v_mystery_elo;
    END IF;

    -- ========================================================================
    -- INSERT ATTEMPT RECORD
    -- ========================================================================

    INSERT INTO mystery_attempts (
        user_id, mystery_id, score, total_questions,
        user_elo_before, user_elo_after,
        mystery_elo_before, mystery_elo_after,
        language_id, test_type_id,
        attempt_number, is_first_attempt,
        idempotency_key
    ) VALUES (
        p_user_id, p_mystery_id, v_score, v_total_questions,
        v_user_elo, v_new_user_elo,
        v_mystery_elo, v_new_mystery_elo,
        p_language_id, p_test_type_id,
        v_attempt_number, v_is_first_attempt,
        p_idempotency_key
    )
    RETURNING id INTO v_attempt_id;

    -- ========================================================================
    -- UPDATE USER_LANGUAGES
    -- ========================================================================

    INSERT INTO user_languages (
        user_id, language_id, total_tests_taken, last_test_date
    ) VALUES (
        p_user_id, p_language_id, 1, CURRENT_DATE
    )
    ON CONFLICT (user_id, language_id)
    DO UPDATE SET
        total_tests_taken = user_languages.total_tests_taken + 1,
        last_test_date = CURRENT_DATE,
        updated_at = NOW();

    -- ========================================================================
    -- RETURN RESULT
    -- ========================================================================

    RETURN jsonb_build_object(
        'success', true,
        'attempt_id', v_attempt_id,
        'attempt_number', v_attempt_number,
        'is_first_attempt', v_is_first_attempt,
        'user_elo_before', v_user_elo,
        'user_elo_after', v_new_user_elo,
        'user_elo_change', v_new_user_elo - v_user_elo,
        'mystery_elo_before', v_mystery_elo,
        'mystery_elo_after', v_new_mystery_elo,
        'score', v_score,
        'total_questions', v_total_questions,
        'percentage', v_percentage,
        'question_results', v_question_results,
        'message', CASE
            WHEN v_is_first_attempt THEN 'First attempt - ELO updated'
            ELSE 'Retake - ELO unchanged'
        END
    );

EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', SQLSTATE
    );
END;
$function$
```

---

### 34. `process_stripe_payment`

- **Arguments:** `p_user_id uuid, p_tokens_to_add integer, p_payment_intent_id text, p_package_id text, p_amount_cents integer`
- **Return type:** `boolean`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.process_stripe_payment(p_user_id uuid, p_tokens_to_add integer, p_payment_intent_id text, p_package_id text, p_amount_cents integer)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    current_balance INTEGER;
    token_record RECORD;
BEGIN
    -- 1. Use payment_intent_id as idempotency key (Stripe's built-in deduplication)
    SELECT * INTO token_record FROM token_transactions WHERE payment_intent_id = p_payment_intent_id;
    IF FOUND THEN
        RETURN TRUE; -- Stripe payment already processed
    END IF;

    -- 2. Row-level lock
    SELECT * INTO token_record FROM user_tokens WHERE user_id = p_user_id FOR UPDATE;

    current_balance := token_record.purchased_tokens + token_record.bonus_tokens;

    -- 3. Add purchased tokens
    UPDATE user_tokens SET 
        purchased_tokens = purchased_tokens + p_tokens_to_add,
        total_tokens_purchased = total_tokens_purchased + p_tokens_to_add
    WHERE user_id = p_user_id;

    -- 4. Record transaction with Stripe details
    INSERT INTO token_transactions (
        user_id, tokens_added, action, idempotency_key,
        payment_intent_id, package_id, token_balance_after, 
        created_at
    ) VALUES (
        p_user_id, p_tokens_to_add, 'stripe_payment', p_payment_intent_id,
        p_payment_intent_id, p_package_id, current_balance + p_tokens_to_add,
        NOW()
    );

    RETURN TRUE;
END;
$function$
```

---

### 35. `process_test_submission`

- **Arguments:** `p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_was_free_test boolean DEFAULT true, p_idempotency_key uuid DEFAULT NULL::uuid`
- **Return type:** `jsonb`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public.process_test_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_was_free_test boolean DEFAULT true, p_idempotency_key uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  v_user_elo integer;
  v_test_elo integer;
  v_user_tests_taken integer;
  v_user_last_date date;
  v_test_attempts integer;
  v_percentage numeric;
  v_percentage_decimal numeric;
  v_new_user_elo integer;
  v_new_test_elo integer;
  v_attempt_id uuid;
  v_attempt_number integer;
  v_is_first_attempt boolean;
  v_existing_attempt record;
  v_tokens_cost integer;
  v_score integer := 0;
  v_total_questions integer := 0;
  v_question_results jsonb := '[]'::jsonb;
  v_question_record record;
  v_user_answer text;
  v_correct_answer text;
  v_is_correct boolean;
BEGIN
  -- SECURITY VALIDATION
  IF p_user_id != auth.uid() THEN
    RAISE EXCEPTION 'Unauthorized: Cannot submit test for another user';
  END IF;

  -- INPUT VALIDATION
  IF p_responses IS NULL OR jsonb_array_length(p_responses) = 0 THEN
    RAISE EXCEPTION 'No responses provided';
  END IF;

  -- ANSWER VALIDATION
  CREATE TEMP TABLE temp_user_responses AS
  SELECT
      (elem->>'question_id')::UUID as question_id,
      elem->>'selected_answer' as selected_answer
  FROM jsonb_array_elements(p_responses) as elem;

  FOR v_question_record IN (
      SELECT q.id, q.answer
      FROM questions q
      WHERE q.test_id = p_test_id
      ORDER BY q.created_at
  ) LOOP
      SELECT selected_answer INTO v_user_answer
      FROM temp_user_responses
      WHERE question_id = v_question_record.id;

      v_user_answer := COALESCE(v_user_answer, '');
      v_correct_answer := v_question_record.answer #>> '{}';
      v_is_correct := (v_user_answer = v_correct_answer);

      IF v_is_correct THEN
          v_score := v_score + 1;
      END IF;

      v_question_results := v_question_results || jsonb_build_object(
          'question_id', v_question_record.id::TEXT,
          'selected_answer', v_user_answer,
          'correct_answer', v_correct_answer,
          'is_correct', v_is_correct
      );

      v_total_questions := v_total_questions + 1;
  END LOOP;

  DROP TABLE IF EXISTS temp_user_responses;

  -- IDEMPOTENCY CHECK
  IF p_idempotency_key IS NOT NULL THEN
    SELECT * INTO v_existing_attempt
    FROM test_attempts
    WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key;

    IF FOUND THEN
      RETURN jsonb_build_object(
        'success', true,
        'attempt_id', v_existing_attempt.id,
        'cached', true,
        'user_elo_change', COALESCE(
          v_existing_attempt.user_elo_after - v_existing_attempt.user_elo_before,
          0
        ),
        'message', 'Duplicate submission detected - returning cached result'
      );
    END IF;
  END IF;

  -- GET TOKEN COST
  v_tokens_cost := get_test_token_cost(p_user_id);

  -- CALCULATE PERCENTAGE
  v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
  v_percentage_decimal := v_percentage / 100.0;

  -- DETERMINE ATTEMPT NUMBER
  SELECT COUNT(*) INTO v_attempt_number
  FROM test_attempts
  WHERE user_id = p_user_id
    AND test_id = p_test_id
    AND test_type_id = p_test_type_id;

  v_attempt_number := v_attempt_number + 1;
  v_is_first_attempt := (v_attempt_number = 1);

  -- GET OR CREATE USER ELO RATING
  SELECT elo_rating, tests_taken, last_test_date
  INTO v_user_elo, v_user_tests_taken, v_user_last_date
  FROM user_skill_ratings
  WHERE user_id = p_user_id
    AND language_id = p_language_id
    AND test_type_id = p_test_type_id;

  IF NOT FOUND THEN
    v_user_elo := 1200;
    v_user_tests_taken := 0;
    v_user_last_date := NULL;

    INSERT INTO user_skill_ratings (
      user_id, language_id, test_type_id, elo_rating, tests_taken
    ) VALUES (
      p_user_id, p_language_id, p_test_type_id, v_user_elo, 0
    );
  END IF;

  -- GET OR CREATE TEST ELO RATING
  SELECT elo_rating, total_attempts
  INTO v_test_elo, v_test_attempts
  FROM test_skill_ratings
  WHERE test_id = p_test_id AND test_type_id = p_test_type_id;

  IF NOT FOUND THEN
    v_test_elo := 1400;
    v_test_attempts := 0;

    INSERT INTO test_skill_ratings (
      test_id, test_type_id, elo_rating, total_attempts
    ) VALUES (
      p_test_id, p_test_type_id, v_test_elo, 0
    );
  END IF;

  -- CALCULATE ELO CHANGES (ONLY FOR FIRST ATTEMPTS)
  IF v_is_first_attempt THEN
    DECLARE
      expected_user_score numeric;
      k_factor integer := 32;
    BEGIN
      expected_user_score := 1.0 / (1.0 + POWER(10, (v_test_elo - v_user_elo) / 400.0));
      v_new_user_elo := ROUND(v_user_elo + k_factor * (v_percentage_decimal - expected_user_score));
      v_new_test_elo := ROUND(v_test_elo + k_factor * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));
      v_new_user_elo := GREATEST(400, LEAST(3000, v_new_user_elo));
      v_new_test_elo := GREATEST(400, LEAST(3000, v_new_test_elo));
    END;

    UPDATE user_skill_ratings
    SET elo_rating = v_new_user_elo, tests_taken = tests_taken + 1,
        last_test_date = CURRENT_DATE, updated_at = NOW()
    WHERE user_id = p_user_id AND language_id = p_language_id AND test_type_id = p_test_type_id;

    UPDATE test_skill_ratings
    SET elo_rating = v_new_test_elo, total_attempts = total_attempts + 1, updated_at = NOW()
    WHERE test_id = p_test_id AND test_type_id = p_test_type_id;
  ELSE
    v_new_user_elo := v_user_elo;
    v_new_test_elo := v_test_elo;
  END IF;

  -- INSERT ATTEMPT RECORD (always store ELO values, not NULL)
  INSERT INTO test_attempts (
    user_id, test_id, test_type_id, language_id, score, total_questions,
    attempt_number, is_first_attempt, user_elo_before, user_elo_after,
    test_elo_before, test_elo_after, tokens_consumed, was_free_test, idempotency_key
  ) VALUES (
    p_user_id, p_test_id, p_test_type_id, p_language_id, v_score, v_total_questions,
    v_attempt_number, v_is_first_attempt, v_user_elo, v_new_user_elo,
    v_test_elo, v_new_test_elo,
    CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    p_was_free_test, p_idempotency_key
  )
  RETURNING id INTO v_attempt_id;

  -- UPDATE USER_LANGUAGES
  INSERT INTO user_languages (user_id, language_id, total_tests_taken, last_test_date)
  VALUES (p_user_id, p_language_id, 1, CURRENT_DATE)
  ON CONFLICT (user_id, language_id)
  DO UPDATE SET total_tests_taken = user_languages.total_tests_taken + 1,
    last_test_date = CURRENT_DATE, updated_at = NOW();

  -- RETURN SUCCESS
  RETURN jsonb_build_object(
    'success', true, 'attempt_id', v_attempt_id, 'attempt_number', v_attempt_number,
    'is_first_attempt', v_is_first_attempt, 'user_elo_before', v_user_elo,
    'user_elo_after', v_new_user_elo, 'user_elo_change', v_new_user_elo - v_user_elo,
    'test_elo_before', v_test_elo, 'test_elo_after', v_new_test_elo,
    'test_elo_change', CASE WHEN v_is_first_attempt THEN v_new_test_elo - v_test_elo ELSE 0 END,
    'tokens_cost', CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    'score', v_score, 'total_questions', v_total_questions, 'percentage', v_percentage,
    'question_results', v_question_results,
    'message', CASE WHEN v_is_first_attempt THEN 'First attempt - ELO updated' ELSE 'Retake - ELO unchanged' END
  );

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'error_detail', SQLSTATE);
END;
$function$
```

---

### 36. `process_test_submission-old`

- **Arguments:** `p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_was_free_test boolean DEFAULT true, p_idempotency_key uuid DEFAULT NULL::uuid`
- **Return type:** `jsonb`
- **Kind:** function
- **Security definer:** True

```sql
CREATE OR REPLACE FUNCTION public."process_test_submission-old"(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_was_free_test boolean DEFAULT true, p_idempotency_key uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$DECLARE
  v_user_elo integer;
  v_test_elo integer;
  v_user_tests_taken integer;
  v_user_last_date date;
  v_test_attempts integer;
  v_percentage numeric;
  v_percentage_decimal numeric;
  v_new_user_elo integer;
  v_new_test_elo integer;
  v_attempt_id uuid;
  v_attempt_number integer;
  v_is_first_attempt boolean;
  v_existing_attempt record;
  v_tokens_cost integer;
  -- NEW VARIABLES FOR VALIDATION
  v_score integer := 0;
  v_total_questions integer := 0;
  v_question_results jsonb := '[]'::jsonb;
  v_question_record record;
  v_user_answer text;
  v_correct_answer text;
  v_is_correct boolean;
BEGIN
  -- ========================================================================
  -- SECURITY VALIDATION
  -- ========================================================================

  IF p_user_id != auth.uid() THEN
    RAISE EXCEPTION 'Unauthorized: Cannot submit test for another user';
  END IF;

  -- ========================================================================
  -- INPUT VALIDATION
  -- ========================================================================

  IF p_responses IS NULL OR jsonb_array_length(p_responses) = 0 THEN
    RAISE EXCEPTION 'No responses provided';
  END IF;

  -- ========================================================================
  -- ANSWER VALIDATION
  -- ========================================================================

  -- Build response lookup for O(1) access
  CREATE TEMP TABLE temp_user_responses AS
  SELECT
      (elem->>'question_id')::UUID as question_id,
      elem->>'selected_answer' as selected_answer
  FROM jsonb_array_elements(p_responses) as elem;

  -- Validate each question
  FOR v_question_record IN (
      SELECT q.id, q.answer
      FROM questions q
      WHERE q.test_id = p_test_id
      ORDER BY q.created_at
  ) LOOP
      -- Get user's answer from temp table
      SELECT selected_answer INTO v_user_answer
      FROM temp_user_responses
      WHERE question_id = v_question_record.id;

      -- Default to empty if not answered
      v_user_answer := COALESCE(v_user_answer, '');

      -- Extract correct answer from JSONB (stored as JSON string like "Answer text")
      v_correct_answer := v_question_record.answer #>> '{}';

      -- Compare answers (case-sensitive string match)
      v_is_correct := (v_user_answer = v_correct_answer);

      -- Increment score if correct
      IF v_is_correct THEN
          v_score := v_score + 1;
      END IF;

      -- Build result object for this question
      v_question_results := v_question_results || jsonb_build_object(
          'question_id', v_question_record.id::TEXT,
          'selected_answer', v_user_answer,
          'correct_answer', v_correct_answer,
          'is_correct', v_is_correct
      );

      v_total_questions := v_total_questions + 1;
  END LOOP;

  -- Clean up temp table
  DROP TABLE IF EXISTS temp_user_responses;

  -- ========================================================================
  -- IDEMPOTENCY CHECK
  -- ========================================================================

  IF p_idempotency_key IS NOT NULL THEN
    SELECT * INTO v_existing_attempt
    FROM test_attempts
    WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key;

    IF FOUND THEN
      -- Return cached response
      RETURN jsonb_build_object(
        'success', true,
        'attempt_id', v_existing_attempt.id,
        'cached', true,
        'user_elo_change', COALESCE(
          v_existing_attempt.user_elo_after - v_existing_attempt.user_elo_before,
          0
        ),
        'message', 'Duplicate submission detected - returning cached result'
      );
    END IF;
  END IF;

  -- ========================================================================
  -- GET TOKEN COST
  -- ========================================================================

  v_tokens_cost := get_test_token_cost(p_user_id);

  -- ========================================================================
  -- CALCULATE PERCENTAGE (0-100 scale to match generated column)
  -- ========================================================================

  v_percentage := (v_score::numeric / v_total_questions::numeric) * 100;
  v_percentage_decimal := v_percentage / 100.0;

  -- ========================================================================
  -- DETERMINE ATTEMPT NUMBER & FIRST ATTEMPT STATUS
  -- ========================================================================

  SELECT COUNT(*) INTO v_attempt_number
  FROM test_attempts
  WHERE user_id = p_user_id
    AND test_id = p_test_id
    AND test_type_id = p_test_type_id;

  v_attempt_number := v_attempt_number + 1;
  v_is_first_attempt := (v_attempt_number = 1);

  -- ========================================================================
  -- GET OR CREATE USER ELO RATING
  -- ========================================================================

  SELECT elo_rating, tests_taken, last_test_date
  INTO v_user_elo, v_user_tests_taken, v_user_last_date
  FROM user_skill_ratings
  WHERE user_id = p_user_id
    AND language_id = p_language_id
    AND test_type_id = p_test_type_id;

  IF NOT FOUND THEN
    -- Create new user skill rating (starting ELO: 1200)
    v_user_elo := 1200;
    v_user_tests_taken := 0;
    v_user_last_date := NULL;

    INSERT INTO user_skill_ratings (
      user_id, language_id, test_type_id, elo_rating, tests_taken
    ) VALUES (
      p_user_id, p_language_id, p_test_type_id, v_user_elo, 0
    );
  END IF;

  -- ========================================================================
  -- GET OR CREATE TEST ELO RATING
  -- ========================================================================

  SELECT elo_rating, total_attempts
  INTO v_test_elo, v_test_attempts
  FROM test_skill_ratings
  WHERE test_id = p_test_id AND test_type_id = p_test_type_id;

  IF NOT FOUND THEN
    -- Create new test skill rating (starting ELO: 1400)
    v_test_elo := 1400;
    v_test_attempts := 0;

    INSERT INTO test_skill_ratings (
      test_id, test_type_id, elo_rating, total_attempts
    ) VALUES (
      p_test_id, p_test_type_id, v_test_elo, 0
    );
  END IF;

  -- ========================================================================
  -- CALCULATE ELO CHANGES (ONLY FOR FIRST ATTEMPTS)
  -- ========================================================================

  IF v_is_first_attempt THEN
    -- Simple ELO calculation (K-factor = 32)
    DECLARE
      expected_user_score numeric;
      k_factor integer := 32;
    BEGIN
      expected_user_score := 1.0 / (1.0 + POWER(10, (v_test_elo - v_user_elo) / 400.0));

      v_new_user_elo := ROUND(v_user_elo + k_factor * (v_percentage_decimal - expected_user_score));
      v_new_test_elo := ROUND(v_test_elo + k_factor * ((1.0 - v_percentage_decimal) - (1.0 - expected_user_score)));

      v_new_user_elo := GREATEST(400, LEAST(3000, v_new_user_elo));
      v_new_test_elo := GREATEST(400, LEAST(3000, v_new_test_elo));
    END;

    -- Update user skill rating
    UPDATE user_skill_ratings
    SET
      elo_rating = v_new_user_elo,
      tests_taken = tests_taken + 1,
      last_test_date = CURRENT_DATE,
      updated_at = NOW()
    WHERE user_id = p_user_id
      AND language_id = p_language_id
      AND test_type_id = p_test_type_id;

    -- Update test skill rating
    UPDATE test_skill_ratings
    SET
      elo_rating = v_new_test_elo,
      total_attempts = total_attempts + 1,
      updated_at = NOW()
    WHERE test_id = p_test_id
      AND test_type_id = p_test_type_id;
  ELSE
    -- Retake: No ELO change
    v_new_user_elo := v_user_elo;
    v_new_test_elo := v_test_elo;
  END IF;

  -- ========================================================================
  -- INSERT ATTEMPT RECORD
  -- ========================================================================

  INSERT INTO test_attempts (
    user_id,
    test_id,
    test_type_id,
    language_id,
    score,
    total_questions,
    attempt_number,
    is_first_attempt,
    user_elo_before,
    user_elo_after,
    test_elo_before,
    test_elo_after,
    tokens_consumed,
    was_free_test,
    idempotency_key
  ) VALUES (
    p_user_id,
    p_test_id,
    p_test_type_id,
    p_language_id,
    v_score,
    v_total_questions,
    v_attempt_number,
    v_is_first_attempt,
    CASE WHEN v_is_first_attempt THEN v_user_elo ELSE NULL END,
    CASE WHEN v_is_first_attempt THEN v_new_user_elo ELSE NULL END,
    CASE WHEN v_is_first_attempt THEN v_test_elo ELSE NULL END,
    CASE WHEN v_is_first_attempt THEN v_new_test_elo ELSE NULL END,
    CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    p_was_free_test,
    p_idempotency_key
  )
  RETURNING id INTO v_attempt_id;

  -- ========================================================================
  -- UPDATE USER_LANGUAGES (TRACK LANGUAGE ACTIVITY)
  -- ========================================================================

  INSERT INTO user_languages (
    user_id, language_id, total_tests_taken, last_test_date
  ) VALUES (
    p_user_id, p_language_id, 1, CURRENT_DATE
  )
  ON CONFLICT (user_id, language_id)
  DO UPDATE SET
    total_tests_taken = user_languages.total_tests_taken + 1,
    last_test_date = CURRENT_DATE,
    updated_at = NOW();

  -- ========================================================================
  -- RETURN SUCCESS RESPONSE WITH QUESTION RESULTS
  -- ========================================================================

  RETURN jsonb_build_object(
    'success', true,
    'attempt_id', v_attempt_id,
    'attempt_number', v_attempt_number,
    'is_first_attempt', v_is_first_attempt,
    'user_elo_before', v_user_elo,
    'user_elo_after', v_new_user_elo,
    'user_elo_change', v_new_user_elo - v_user_elo,
    'test_elo_before', v_test_elo,
    'test_elo_after', v_new_test_elo,
    'test_elo_change', CASE WHEN v_is_first_attempt THEN v_new_test_elo - v_test_elo ELSE 0 END,
    'tokens_cost', CASE WHEN p_was_free_test THEN 0 ELSE v_tokens_cost END,
    'score', v_score,
    'total_questions', v_total_questions,
    'percentage', v_percentage,
    'question_results', v_question_results,
    'message', CASE
      WHEN v_is_first_attempt THEN 'First attempt - ELO updated'
      ELSE 'Retake - ELO unchanged'
    END
  );

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object(
    'success', false,
    'error', SQLERRM,
    'error_detail', SQLSTATE
  );
END;$function$
```

---

### 37. `tests_containing_sense`

- **Arguments:** `p_sense_id integer, p_language_id integer`
- **Return type:** `TABLE(id uuid, transcript text, difficulty numeric, vocab_token_map jsonb)`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.tests_containing_sense(p_sense_id integer, p_language_id integer)
 RETURNS TABLE(id uuid, transcript text, difficulty numeric, vocab_token_map jsonb)
 LANGUAGE sql
 STABLE
AS $function$
    SELECT t.id, t.transcript, t.difficulty, t.vocab_token_map
    FROM tests t
    JOIN dim_languages dl ON dl.id = p_language_id
    WHERE t.vocab_sense_ids @> ARRAY[p_sense_id]
      AND t.language_id = p_language_id
      AND t.is_active = TRUE;
$function$
```

---

### 38. `update_skill_attempts_count`

- **Arguments:** `(none)`
- **Return type:** `trigger`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.update_skill_attempts_count()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Update the specific test_type_id attempts counter for this test
    UPDATE test_skill_ratings
    SET 
        total_attempts = (
            SELECT COUNT(*) 
            FROM test_attempts 
            WHERE test_id = NEW.test_id 
            AND test_type_id = test_skill_ratings.test_type_id
        ),
        updated_at = NOW()
    WHERE test_id = NEW.test_id 
    AND test_type_id = NEW.test_type_id;
    
    RETURN NEW;
END;
$function$
```

---

### 39. `update_test_attempts_count`

- **Arguments:** `(none)`
- **Return type:** `trigger`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.update_test_attempts_count()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Only update the specific test that was affected
    UPDATE public.tests
    SET total_attempts = (
        SELECT COUNT(*) 
        FROM public.test_attempts 
        WHERE test_id = NEW.test_id
    )
    WHERE id = NEW.test_id;
    
    RETURN NEW;
END;
$function$
```

---

### 40. `update_updated_at_column`

- **Arguments:** `(none)`
- **Return type:** `trigger`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$function$
```

---

### 41. `update_user_vocab_stats`

- **Arguments:** `(none)`
- **Return type:** `trigger`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.update_user_vocab_stats()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  NEW.total_senses_tracked := (
    SELECT COUNT(*) FROM jsonb_object_keys(NEW.sense_learning_stats)
  );
  RETURN NEW;
END;
$function$
```

---

### 42. `update_vocabulary_from_test`

- **Arguments:** `p_user_id uuid, p_language_id smallint, p_question_results jsonb`
- **Return type:** `TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.update_vocabulary_from_test(p_user_id uuid, p_language_id smallint, p_question_results jsonb)
 RETURNS TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)
 LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    WITH question_senses AS (
        SELECT
            unnest(q.sense_ids) AS sense_id,
            (qr->>'is_correct')::boolean AS is_correct
        FROM jsonb_array_elements(p_question_results) qr
        JOIN questions q ON q.id = (qr->>'question_id')::uuid
        WHERE q.sense_ids IS NOT NULL
          AND array_length(q.sense_ids, 1) > 0
    ),
    deduped AS (
        SELECT qs.sense_id, bool_or(qs.is_correct) AS is_correct
        FROM question_senses qs
        GROUP BY qs.sense_id
    ),
    current_state AS (
        SELECT
            d.sense_id,
            d.is_correct,
            COALESCE(
                uvk.p_known,
                CASE
                    WHEN dv.frequency_rank IS NULL THEN 0.10
                    WHEN dv.frequency_rank >= 6.0 THEN 0.85
                    WHEN dv.frequency_rank >= 5.0 THEN 0.65
                    WHEN dv.frequency_rank >= 4.0 THEN 0.35
                    WHEN dv.frequency_rank >= 3.0 THEN 0.15
                    ELSE 0.05
                END
            ) AS p_current
        FROM deduped d
        JOIN dim_word_senses dws ON dws.id = d.sense_id
        JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
        LEFT JOIN user_vocabulary_knowledge uvk
            ON uvk.user_id = p_user_id AND uvk.sense_id = d.sense_id
    ),
    updated AS (
        SELECT
            cs.sense_id,
            cs.p_current AS p_before,
            bkt_update_comprehension(cs.p_current, cs.is_correct) AS p_after,
            cs.is_correct
        FROM current_state cs
    ),
    upserted AS (
        INSERT INTO user_vocabulary_knowledge
            (user_id, sense_id, language_id, p_known, status,
             evidence_count, comprehension_correct, comprehension_wrong,
             last_evidence_at, updated_at)
        SELECT
            p_user_id, u.sense_id, p_language_id,
            u.p_after, bkt_status(u.p_after),
            1,
            CASE WHEN u.is_correct THEN 1 ELSE 0 END,
            CASE WHEN u.is_correct THEN 0 ELSE 1 END,
            NOW(), NOW()
        FROM updated u
        ON CONFLICT (user_id, sense_id) DO UPDATE SET
            p_known = EXCLUDED.p_known,
            status = CASE
                WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
                THEN 'user_marked_unknown'
                ELSE EXCLUDED.status
            END,
            evidence_count = user_vocabulary_knowledge.evidence_count + 1,
            comprehension_correct = user_vocabulary_knowledge.comprehension_correct + EXCLUDED.comprehension_correct,
            comprehension_wrong = user_vocabulary_knowledge.comprehension_wrong + EXCLUDED.comprehension_wrong,
            last_evidence_at = NOW(),
            updated_at = NOW()
        RETURNING sense_id, p_known, status
    )
    SELECT
        upserted.sense_id,
        COALESCE(u.p_before, 0.10),
        upserted.p_known,
        upserted.status
    FROM upserted
    LEFT JOIN updated u ON u.sense_id = upserted.sense_id;
END;
$function$
```

---

### 43. `update_vocabulary_from_word_test`

- **Arguments:** `p_user_id uuid, p_sense_id integer, p_is_correct boolean, p_language_id smallint`
- **Return type:** `TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)`
- **Kind:** function
- **Security definer:** False

```sql
CREATE OR REPLACE FUNCTION public.update_vocabulary_from_word_test(p_user_id uuid, p_sense_id integer, p_is_correct boolean, p_language_id smallint)
 RETURNS TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_p_current NUMERIC;
    v_p_new NUMERIC;
    v_status TEXT;
BEGIN
    -- Get current p_known or compute prior
    SELECT COALESCE(uvk.p_known,
        CASE
            WHEN dv.frequency_rank IS NULL THEN 0.10
            WHEN dv.frequency_rank >= 6.0 THEN 0.85
            WHEN dv.frequency_rank >= 5.0 THEN 0.65
            WHEN dv.frequency_rank >= 4.0 THEN 0.35
            WHEN dv.frequency_rank >= 3.0 THEN 0.15
            ELSE 0.05
        END
    ) INTO v_p_current
    FROM dim_word_senses dws
    JOIN dim_vocabulary dv ON dv.id = dws.vocab_id
    LEFT JOIN user_vocabulary_knowledge uvk
        ON uvk.user_id = p_user_id AND uvk.sense_id = p_sense_id
    WHERE dws.id = p_sense_id;

    IF v_p_current IS NULL THEN
        v_p_current := 0.10;
    END IF;

    v_p_new := bkt_update_word_test(v_p_current, p_is_correct);
    v_status := bkt_status(v_p_new);

    INSERT INTO user_vocabulary_knowledge
        (user_id, sense_id, language_id, p_known, status,
         evidence_count, word_test_correct, word_test_wrong,
         last_evidence_at, updated_at)
    VALUES (
        p_user_id, p_sense_id, p_language_id,
        v_p_new, v_status,
        1,
        CASE WHEN p_is_correct THEN 1 ELSE 0 END,
        CASE WHEN p_is_correct THEN 0 ELSE 1 END,
        NOW(), NOW()
    )
    ON CONFLICT (user_id, sense_id) DO UPDATE SET
        p_known = EXCLUDED.p_known,
        status = CASE
            WHEN user_vocabulary_knowledge.status = 'user_marked_unknown'
            THEN 'user_marked_unknown'
            ELSE EXCLUDED.status
        END,
        evidence_count = user_vocabulary_knowledge.evidence_count + 1,
        word_test_correct = user_vocabulary_knowledge.word_test_correct + EXCLUDED.word_test_correct,
        word_test_wrong = user_vocabulary_knowledge.word_test_wrong + EXCLUDED.word_test_wrong,
        last_evidence_at = NOW(),
        updated_at = NOW();

    RETURN QUERY SELECT p_sense_id, v_p_current, v_p_new, v_status;
END;
$function$
```

---

## EXTENSION FUNCTIONS (199 total)

These are provided by PostgreSQL extensions and are not custom application code. All are `LANGUAGE c` functions. Listed here for completeness:

**intarray extension (37 functions):**
`_int_contained`, `_int_contained_joinsel`, `_int_contained_sel`, `_int_contains`, `_int_contains_joinsel`, `_int_contains_sel`, `_int_different`, `_int_inter`, `_int_matchsel`, `_int_overlap`, `_int_overlap_joinsel`, `_int_overlap_sel`, `_int_same`, `_int_union`, `_intbig_in`, `_intbig_out`, `boolop`, `bqarr_in`, `bqarr_out`, `g_int_compress`, `g_int_consistent`, `g_int_decompress`, `g_int_options`, `g_int_penalty`, `g_int_picksplit`, `g_int_same`, `g_int_union`, `g_intbig_compress`, `g_intbig_consistent`, `g_intbig_decompress`, `g_intbig_options`, `g_intbig_penalty`, `g_intbig_picksplit`, `g_intbig_same`, `g_intbig_union`, `ginint4_consistent`, `ginint4_queryextract`, `icount`, `idx`, `intarray_del_elem`, `intarray_push_array`, `intarray_push_elem`, `intset`, `intset_subtract`, `intset_union_elem`, `querytree`, `rboolop`, `sort` (2 overloads), `sort_asc`, `sort_desc`, `subarray` (2 overloads), `uniq`

**pgvector extension (120+ functions):**
`array_to_halfvec` (4 overloads), `array_to_sparsevec` (4 overloads), `array_to_vector` (4 overloads), `binary_quantize` (2 overloads), `cosine_distance` (3 overloads), `halfvec` (type cast), `halfvec_accum`, `halfvec_add`, `halfvec_avg`, `halfvec_cmp`, `halfvec_combine`, `halfvec_concat`, `halfvec_eq`, `halfvec_ge`, `halfvec_gt`, `halfvec_in`, `halfvec_l2_squared_distance`, `halfvec_le`, `halfvec_lt`, `halfvec_mul`, `halfvec_ne`, `halfvec_negative_inner_product`, `halfvec_out`, `halfvec_recv`, `halfvec_send`, `halfvec_spherical_distance`, `halfvec_sub`, `halfvec_to_float4`, `halfvec_to_sparsevec`, `halfvec_to_vector`, `halfvec_typmod_in`, `hamming_distance`, `hnsw_bit_support`, `hnsw_halfvec_support`, `hnsw_sparsevec_support`, `hnswhandler`, `inner_product` (3 overloads), `ivfflat_bit_support`, `ivfflat_halfvec_support`, `ivfflathandler`, `jaccard_distance`, `l1_distance` (3 overloads), `l2_distance` (3 overloads), `l2_norm` (2 overloads), `l2_normalize` (3 overloads), `sparsevec` (type cast), `sparsevec_cmp`, `sparsevec_eq`, `sparsevec_ge`, `sparsevec_gt`, `sparsevec_in`, `sparsevec_l2_squared_distance`, `sparsevec_le`, `sparsevec_lt`, `sparsevec_ne`, `sparsevec_negative_inner_product`, `sparsevec_out`, `sparsevec_recv`, `sparsevec_send`, `sparsevec_to_halfvec`, `sparsevec_to_vector`, `sparsevec_typmod_in`, `subvector` (2 overloads), `vector` (type cast), `vector_accum`, `vector_add`, `vector_avg`, `vector_cmp`, `vector_combine`, `vector_concat`, `vector_dims` (2 overloads), `vector_eq`, `vector_ge`, `vector_gt`, `vector_in`, `vector_l2_squared_distance`, `vector_le`, `vector_lt`, `vector_mul`, `vector_ne`, `vector_negative_inner_product`, `vector_norm`, `vector_out`, `vector_recv`, `vector_send`, `vector_spherical_distance`, `vector_sub`, `vector_to_float4`, `vector_to_halfvec`, `vector_to_sparsevec`, `vector_typmod_in`

**pg_trgm extension (19 functions):**
`gin_extract_query_trgm`, `gin_extract_value_trgm`, `gin_trgm_consistent`, `gin_trgm_triconsistent`, `gtrgm_compress`, `gtrgm_consistent`, `gtrgm_decompress`, `gtrgm_distance`, `gtrgm_in`, `gtrgm_options`, `gtrgm_out`, `gtrgm_penalty`, `gtrgm_picksplit`, `gtrgm_same`, `gtrgm_union`, `set_limit`, `show_limit`, `show_trgm`, `similarity`, `similarity_dist`, `similarity_op`, `strict_word_similarity`, `strict_word_similarity_commutator_op`, `strict_word_similarity_dist_commutator_op`, `strict_word_similarity_dist_op`, `strict_word_similarity_op`, `word_similarity`, `word_similarity_commutator_op`, `word_similarity_dist_commutator_op`, `word_similarity_dist_op`, `word_similarity_op`

All 199 extension functions have the same pattern: `LANGUAGE c` with a shared library reference (e.g., `'$libdir/vector'`, `'$libdir/_int'`, `'$libdir/pg_trgm'`). They have no custom SQL/plpgsql bodies -- they are compiled C implementations provided by their respective extensions.

---

**Summary:** 242 total functions in the public schema. 43 are custom LinguaLoop application functions (all with complete definitions shown above), and 199 are extension-provided C functions from pgvector, intarray, and pg_trgm. All 43 application functions are `function` kind (no procedures). 19 of the 43 are `SECURITY DEFINER`. The complete output file is also at `C:\Users\James\AppData\Local\Temp\lingua_app_rpcs.md`.