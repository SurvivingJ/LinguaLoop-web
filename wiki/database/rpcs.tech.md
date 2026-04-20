---
title: "RPC & Functions — Technical Specification"
type: api-tech
status: complete
prose_page: ../database/rpcs.md
last_updated: 2026-04-16
dependencies:
  - "All tables in schema.tech.md"
breaking_change_risk: high
---

# RPC & Functions — Technical Specification

## Overview

| Metric | Value |
|--------|-------|
| Total application functions | 48 |
| SECURITY DEFINER | 24 |
| SECURITY INVOKER | 24 |
| Trigger functions | 6 |
| Pure/IMMUTABLE functions | 10 |
| STABLE functions | 10 |
| Extension functions (not documented here) | 199 (pgvector, intarray, pg_trgm) |

### Categories at a Glance

| Category | Count | Functions |
|----------|-------|-----------|
| Auth & User Management | 7 | `is_admin`, `is_moderator`, `is_org_member`, `get_org_role`, `handle_new_user`, `create_user_dependencies`, `anonymize_user_data` |
| Token Economy | 5 | `add_tokens_atomic`, `get_token_balance`, `get_test_token_cost`, `get_daily_free_test_limit`, `can_use_free_test` |
| Payment Processing | 1 | `process_stripe_payment` |
| ELO / Skill Rating | 3 | `calculate_elo_rating`, `calculate_volatility_multiplier`, `update_skill_attempts_count` |
| Test & Content | 5 | `get_recommended_test`, `get_recommended_tests`, `process_test_submission`, `update_test_attempts_count`, `tests_containing_sense` |
| Vocabulary & Knowledge (BKT) | 14 | `bkt_update`, `bkt_status`, `bkt_update_comprehension`, `bkt_update_word_test`, `bkt_update_exercise`, `bkt_apply_decay`, `bkt_effective_p_known`, `bkt_phase`, `bkt_phase_thresholds`, `update_vocabulary_from_test`, `update_vocabulary_from_word_test`, `get_vocab_recommendations`, `get_word_quiz_candidates`, `update_user_vocab_stats` |
| Vocabulary Lookup | 2 | `batch_lookup_lemmas`, `get_distractors` |
| Mystery System | 2 | `get_recommended_mysteries`, `process_mystery_submission` |
| Packs & Content Discovery | 2 | `get_packs_with_user_selection`, `get_active_languages` |
| Model Config | 1 | `get_model_for_task` |
| Corpus & Collocations | 1 | `get_top_collocations_for_sources` |
| Category / Topic Matching | 2 | `get_next_category`, `match_topics` |
| Prompt Templates | 1 | `get_prompt_template` |
| Utility / Triggers | 2 | `update_updated_at_column`, `sync_exercise_history` |

---

## Auth & User Management

---

### `is_admin(p_user_id uuid): boolean`

- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Checks whether a user has admin privileges by joining the `users` table to `dim_subscription_tiers`. Returns `false` if the user is deleted or not found.

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

- **Key behaviors:** Returns NULL (falsy) if user not found; explicitly excludes soft-deleted users.

---

### `is_moderator(p_user_id uuid): boolean`

- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Checks whether a user has moderator OR admin privileges. Admins are always treated as moderators.

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

- **Key behaviors:** Admin implies moderator. Soft-deleted users excluded.

---

### `is_org_member(p_user_id uuid, p_org_id uuid): boolean`

- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Checks whether a user belongs to a specific organization by querying `organization_members`.

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

### `get_org_role(p_user_id uuid, p_org_id uuid): text`

- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Returns the role string (e.g. `'admin'`, `'member'`) for a user within an organization. Returns NULL if not a member.

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

### `handle_new_user(): trigger`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Trigger function fired on `auth.users` INSERT. Creates a corresponding row in `public.users` with the free subscription tier. Auto-creates the free tier in `dim_subscription_tiers` if it does not exist. Uses `ON CONFLICT` for idempotency. Catches all exceptions to avoid blocking auth user creation.

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

- **Side effects:** Creates user row, potentially creates free tier row. Never fails (exception swallowed to protect auth flow).
- **Tables written:** `users`, possibly `dim_subscription_tiers`.

---

### `create_user_dependencies(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Trigger function that creates a `user_tokens` row with zero purchased tokens when a new user is created. Uses `ON CONFLICT` for idempotency.

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

- **Tables written:** `user_tokens`.

---

### `anonymize_user_data(p_user_id uuid): void`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Soft-deletes and anonymizes a user by replacing their email and display name with generic placeholders and setting `deleted_at` and `anonymized_at` timestamps. Only the user themselves or an admin can invoke this.

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

- **Auth:** Caller must be the user or an admin.
- **Side effects:** Irreversibly overwrites PII fields.

---

## Token Economy

---

### `add_tokens_atomic(p_user_id uuid, p_tokens_to_add integer, p_action text, p_idempotency_key text, p_payment_intent_id text DEFAULT NULL, p_package_id text DEFAULT NULL): boolean`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Adds tokens to a user's balance atomically. Currently a stub that validates authorization only (Phase 3 TODO). Only the user themselves or an admin/moderator can call this.

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

- **Auth:** Self or admin/moderator.
- **Note:** Stub implementation -- always returns true.

---

### `get_token_balance(p_user_id uuid): integer`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Returns a user's current token balance (purchased + bonus). Only the user themselves or an admin/moderator can view the balance. Implemented in Phase 3 (was stub returning 0).

```sql
CREATE OR REPLACE FUNCTION public.get_token_balance(p_user_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_balance integer;
BEGIN
    IF p_user_id != auth.uid() THEN
        IF NOT (is_admin(auth.uid()) OR is_moderator(auth.uid())) THEN
            RAISE EXCEPTION 'Unauthorized: Cannot view another user''s token balance';
        END IF;
    END IF;

    SELECT COALESCE(purchased_tokens + bonus_tokens, 0)
    INTO v_balance
    FROM user_tokens
    WHERE user_id = p_user_id;

    RETURN COALESCE(v_balance, 0);
END;
$function$
```

- **Tables read:** `user_tokens`.

---

### `get_test_token_cost(p_user_id uuid): integer`

- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Returns the per-test token cost for a user based on their subscription tier. Defaults to 10 tokens if not configured.

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

### `get_daily_free_test_limit(p_user_id uuid): integer`

- **Security:** DEFINER
- **Language:** SQL (STABLE)
- **Description:** Returns the daily free test limit for a user based on their subscription tier. Returns 0 if the user is deleted or has no tier.

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

### `can_use_free_test(p_user_id uuid): boolean`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Checks whether a user can take a free test today. Properly enforces daily count (Phase 3 — was stub returning `daily_limit > 0`). Reads `free_tests_used_today` and `last_free_test_date` from users table; resets counter if last date is not today.

```sql
CREATE OR REPLACE FUNCTION public.can_use_free_test(p_user_id uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_daily_limit integer;
    v_used_today integer;
    v_last_free_date date;
BEGIN
    IF p_user_id != auth.uid() THEN
        RAISE EXCEPTION 'Unauthorized: Cannot check free test status for another user';
    END IF;

    v_daily_limit := get_daily_free_test_limit(p_user_id);

    SELECT free_tests_used_today, last_free_test_date
    INTO v_used_today, v_last_free_date
    FROM users
    WHERE id = p_user_id AND deleted_at IS NULL;

    IF v_last_free_date IS NULL OR v_last_free_date < CURRENT_DATE THEN
        v_used_today := 0;
    END IF;

    RETURN COALESCE(v_used_today, 0) < v_daily_limit;
END;
$function$
```

- **Auth:** Caller must be the user (strict self-only).
- **Tables read:** `users`, `dim_subscription_tiers` (via `get_daily_free_test_limit`).

---

## Payment Processing

---

### `process_stripe_payment(p_user_id uuid, p_tokens_to_add integer, p_payment_intent_id text, p_package_id text, p_amount_cents integer): boolean`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Processes a Stripe payment by adding purchased tokens to a user's balance and recording the transaction. Uses `payment_intent_id` as an idempotency key (Stripe's built-in deduplication). Acquires a row-level lock on `user_tokens` to prevent race conditions.

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

- **Side effects:** Updates `user_tokens`, inserts into `token_transactions`.
- **Concurrency:** Uses `FOR UPDATE` row-level locking.
- **Idempotency:** Checks `token_transactions.payment_intent_id` before processing.

---

## ELO / Skill Rating

---

### `calculate_elo_rating(current_rating integer, opposing_rating integer, actual_score numeric, k_factor integer DEFAULT 32, volatility_multiplier numeric DEFAULT 1.0): integer`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** Pure ELO calculation function. Computes a new rating given the current rating, opposing rating, and actual score (0.0 to 1.0). Supports adjustable K-factor and volatility multiplier. Clamps result between 400 and 3000.

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

- **Key behaviors:** Standard ELO formula. Rating floor 400, ceiling 3000.

---

### `calculate_volatility_multiplier(attempts integer, last_date date DEFAULT NULL, base_volatility numeric DEFAULT 1.0): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** Calculates a volatility multiplier for ELO adjustments. Increases volatility for users with few attempts (<10) and for users who have been inactive for >90 days.

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

- **Key behaviors:** Base 1.0 + 0.5 for low attempts + 0.5 for inactivity. Max possible: 2.0.

---

### `update_skill_attempts_count(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Trigger function that increments `total_attempts` in `test_skill_ratings` after a new test attempt. Phase 3 fix: uses O(1) increment instead of COUNT(*) scan.

```sql
CREATE OR REPLACE FUNCTION public.update_skill_attempts_count()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    UPDATE test_skill_ratings
    SET total_attempts = total_attempts + 1,
        updated_at = NOW()
    WHERE test_id = NEW.test_id
      AND test_type_id = NEW.test_type_id;
    RETURN NEW;
END;
$function$
```

- **Tables written:** `test_skill_ratings`.
- **Phase 3 fix:** Was `COUNT(*)` scan, now O(1) increment. Duplicate trigger `update_skill_attempts_count_trigger` was removed in Phase 1.

---

## Test & Content

---

### `get_recommended_test(p_user_id uuid, p_language_id integer): SETOF tests`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Returns a single recommended test for a user by expanding ELO radius search. Tries radii of 50, 100, 250, 500, and 10000 around the user's listening and reading ELO ratings until a match is found. Returns a random test within the matching radius. **Phase 3 fix:** Now excludes tests the user has already attempted via `NOT EXISTS` on `test_attempts`. Also adds `SET search_path`.

```sql
CREATE OR REPLACE FUNCTION public.get_recommended_test(
    p_user_id uuid,
    p_language_id integer
)
 RETURNS SETOF tests
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_listening_type_id SMALLINT;
    v_reading_type_id SMALLINT;
    v_user_listening_elo INT := 1200;
    v_user_reading_elo INT := 1200;
    v_radius INT;
    v_radii INT[] := ARRAY[50, 100, 250, 500, 10000];
    v_test_found tests%ROWTYPE;
BEGIN
    SELECT id INTO v_listening_type_id FROM dim_test_types WHERE type_code = 'listening';
    SELECT id INTO v_reading_type_id FROM dim_test_types WHERE type_code = 'reading';

    SELECT
        MAX(CASE WHEN test_type_id = v_listening_type_id THEN elo_rating END),
        MAX(CASE WHEN test_type_id = v_reading_type_id THEN elo_rating END)
    INTO v_user_listening_elo, v_user_reading_elo
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND language_id = p_language_id;

    IF v_user_listening_elo IS NULL THEN v_user_listening_elo := 1200; END IF;
    IF v_user_reading_elo IS NULL THEN v_user_reading_elo := 1200; END IF;

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
               AND tsr.elo_rating BETWEEN (v_user_listening_elo - v_radius)
                                       AND (v_user_listening_elo + v_radius))
              OR
              (tsr.test_type_id = v_reading_type_id
               AND tsr.elo_rating BETWEEN (v_user_reading_elo - v_radius)
                                       AND (v_user_reading_elo + v_radius))
          )
          -- FIX (Phase 3): Exclude already-attempted tests
          AND NOT EXISTS (
              SELECT 1 FROM test_attempts ta
              WHERE ta.user_id = p_user_id AND ta.test_id = t.id
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

- **Key behaviors:** Expanding radius search (50 -> 10000). Default ELO 1200. Returns 0 or 1 row. **Phase 3: Now excludes already-attempted tests.**

---

### `get_recommended_tests(p_user_id uuid, p_language text): TABLE(...)`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Returns multiple recommended tests for a user by language name/code. Resolves language dynamically. Checks subscription tier for premium access. Excludes tests the user has already attempted. Returns up to 3 tests per test type (listening, reading, dictation), deduplicated by test_id, sorted by ELO proximity.

**Returns:** `TABLE(test_id uuid, slug text, test_type text, title text, difficulty_level integer, elo_rating integer, elo_diff integer, tier text)`

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

- **Key behaviors:** Free-tier users only see `free-tier` tests. Already-attempted tests are excluded. Top 3 per test type, deduplicated.
- **Tables read:** `dim_languages`, `users`, `dim_subscription_tiers`, `dim_test_types`, `user_skill_ratings`, `test_skill_ratings`, `tests`, `test_attempts`.

---

### `process_test_submission(p_user_id uuid, p_test_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_was_free_test boolean DEFAULT true, p_idempotency_key uuid DEFAULT NULL): jsonb`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** The primary test submission handler. Validates answers server-side against the `questions` table, calculates score, updates ELO ratings (only on first attempt), records the attempt, and updates user language activity. Supports idempotency via UUID key. Returns a comprehensive JSON result with score, ELO changes, and per-question results.

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

- **Auth:** Caller must be the user (`auth.uid()` check).
- **Side effects:** Creates/updates `user_skill_ratings`, `test_skill_ratings`, inserts `test_attempts`, upserts `user_languages`.
- **Key behaviors:** ELO only changes on first attempt per test+type combo. Uses temp table (`ON COMMIT DROP`) for answer lookup. **Phase 3 fix:** Volatility multiplier re-enabled via `calculate_volatility_multiplier()`. Asymmetric K-factors: K=32 with volatility for users, K=16 with no volatility for tests. Catches all exceptions and returns error JSON.
- **Idempotency:** Returns cached result if `idempotency_key` matches existing attempt.

---

> **`process_test_submission-old` — DROPPED** (Phase 1). Was a duplicate of `process_test_submission`.

> **`migrate_test_json` — DROPPED** (Phase 1). Referenced non-existent tables (`test_questions`, `test_catalog`). Was broken since schema V2.

---

### `update_test_attempts_count(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Trigger function that increments `total_attempts` on the `tests` table. Phase 3 fix: O(1) increment instead of COUNT(*).

```sql
CREATE OR REPLACE FUNCTION public.update_test_attempts_count()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    UPDATE public.tests
    SET total_attempts = total_attempts + 1
    WHERE id = NEW.test_id;
    RETURN NEW;
END;
$function$
```

- **Tables written:** `tests`.

---

### `tests_containing_sense(p_sense_id integer, p_language_id integer): TABLE(id uuid, transcript text, difficulty numeric, vocab_token_map jsonb)`

- **Security:** INVOKER
- **Language:** SQL (STABLE)
- **Description:** Returns all active tests in a given language that contain a specific vocabulary sense ID, using the `vocab_sense_ids` integer array with the `@>` (contains) operator.

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

## Vocabulary & Knowledge (BKT)

---

### `bkt_update(p_current numeric, p_correct boolean, p_slip numeric DEFAULT 0.10, p_guess numeric DEFAULT 0.25): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** Core Bayesian Knowledge Tracing (BKT) update function. Given a current knowledge probability, whether the answer was correct, and slip/guess parameters, returns the updated probability of knowledge. Clamps output between 0.02 and 0.98.

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

- **Key behaviors:** Pure function. Floor 0.02, ceiling 0.98. Default slip=0.10, guess=0.25.

---

### `bkt_status(p_known numeric): text`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** Maps a BKT knowledge probability to a human-readable status string. Thresholds: <0.20 = unknown, <0.50 = encountered, <0.75 = learning, <0.90 = probably_known, >=0.90 = known.

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

### `bkt_update_comprehension(p_current numeric, p_correct boolean): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** BKT update wrapper for comprehension test evidence. Uses slip=0.10, guess=0.25 (standard parameters for multiple-choice comprehension questions). **(Phase 7)** Now includes transit credit P(T)=0.02 after posterior update.

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

### `bkt_update_word_test(p_current numeric, p_correct boolean): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** BKT update wrapper for word test evidence. Uses slip=0.05, guess=0.25 (lower slip because word tests are more direct assessments of knowledge). **(Phase 7)** Now includes transit credit P(T)=0.05 after posterior update.

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

### `bkt_update_exercise(p_current numeric, p_correct boolean, p_exercise_type text): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** **(Phase 5, Phase 7 transit)** Exercise-type-specific BKT update. Four tiers based on cognitive demand: Recognition (high guess 0.25, low slip 0.05, transit 0.05), Recall (low guess 0.10, moderate slip 0.10, transit 0.08), Nuanced (moderate guess 0.20, higher slip 0.15, transit 0.08), Production (very low guess 0.05, highest slip 0.20, transit 0.10). Falls back to default (slip=0.05, guess=0.25, transit 0.05) for unknown types.

```sql
-- See migrations/phase5_algorithm_fixes.sql for full definition
-- Routes to bkt_update() with exercise-type-specific slip/guess parameters
```

- **Tier mapping:**
  - Recognition: phonetic_recognition, definition_match, text_flashcard, listening_flashcard, cloze_completion
  - Recall: morphology_slot, jumbled_sentence, tl_nl_translation, nl_tl_translation, spot_incorrect_*
  - Nuanced: semantic_discrimination, collocation_gap_fill, collocation_repair, odd_one_out, odd_collocation_out
  - Production: verb_noun_match, context_spectrum, timed_speed_round, style_imitation, free_production, sentence_writing

---

### `bkt_apply_decay(p_known numeric, p_last_evidence_at timestamptz, p_stability real DEFAULT NULL, p_evidence_count integer DEFAULT 0): numeric`

- **Security:** INVOKER
- **Language:** plpgsql (IMMUTABLE)
- **Description:** **(Phase 7, supersedes Phase 5)** FSRS stability-informed temporal decay. Two-path model:
  - **Path A:** If `p_stability > 0`, uses `retrievability = exp(-days / stability)` (FSRS-backed)
  - **Path B:** Fallback to evidence-count-scaled half-life: `30 * (1 + 0.5 * ln(1 + evidence_count))`
  - Floor: 0.10. No decay within 1 day.

---

### `bkt_effective_p_known(p_known numeric, p_last_evidence_at timestamptz, p_stability real DEFAULT NULL, p_evidence_count integer DEFAULT 0): numeric`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** **(Phase 7)** Convenience wrapper calling `bkt_apply_decay` with all parameters. Used by `get_session_senses()` and any query needing decay-applied p_known.

---

### `get_session_senses(p_user_id uuid, p_language_id smallint, p_due_limit integer DEFAULT 30, p_learning_limit integer DEFAULT 30, p_new_limit integer DEFAULT 30): TABLE(out_sense_id integer, out_effective_p_known numeric, out_bucket text, out_entropy numeric)`

- **Security:** INVOKER
- **Language:** plpgsql (STABLE)
- **Description:** **(Phase 7)** Unified session-building RPC that returns all candidate senses with decay-applied effective p_known and bucket labels. Replaces three separate Python fetch methods. LEFT JOINs `user_flashcards` for FSRS stability. Returns three buckets:
  - `'due'`: FSRS due flashcards (state in review/relearning, due_date <= today)
  - `'learning'`: Uncertainty zone (effective 0.25–0.75), sorted by entropy DESC
  - `'new'`: Low effective p_known (< 0.30), status encountered/unknown

---

### `bkt_apply_lapse_penalty(p_user_id uuid, p_sense_id integer): void`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** **(Phase 7)** Applies 20% p_known penalty when FSRS records a lapse. `p_known *= 0.80`, clamped to floor 0.10. Preserves `user_marked_unknown` status. Called from Python after FSRS `schedule_review()` detects `new_card.lapses > old_card.lapses`.

---

### `bkt_infer_from_frequency(p_user_id uuid, p_language_id smallint, p_known_sense_id integer, p_new_p_known numeric): integer`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** **(Phase 7)** Frequency-tier inference. When a rare word reaches "known" (p_known ≥ 0.90), boosts common words with `evidence_count < 3` and `frequency_rank > known_word_rank + 1.0` to their frequency-based prior floor. Returns count of words boosted. Only raises p_known floors, never lowers.

---

### `bkt_contextual_inference(p_user_id uuid, p_language_id smallint, p_contextual_sense_ids integer[], p_score_ratio numeric): integer`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** **(Phase 7)** Sentence-level contextual inference. Applies dampened positive BKT update to vocabulary in test transcript that was NOT directly tested by any question. Dampening = 0.30 × score_ratio. Only fires when score ≥ 50%. Positive-only (never lowers p_known). Preserves `user_marked_unknown` status. Returns count of senses updated.

---

### `bkt_phase(p_known numeric): text`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** **(Phase 5)** Canonical phase thresholds — single source of truth. Returns 'A' (<0.30), 'B' (<0.55), 'C' (<0.80), 'D' (>=0.80). Python should import from config or call this function rather than hardcoding thresholds.

---

### `bkt_phase_thresholds(): TABLE(phase text, min_p_known numeric, max_p_known numeric)`

- **Security:** INVOKER
- **Language:** SQL (IMMUTABLE)
- **Description:** **(Phase 5)** Exposes phase thresholds as a table for Python to query. Returns 4 rows: A(0.00-0.30), B(0.30-0.55), C(0.55-0.80), D(0.80-1.00).

---

### `update_vocabulary_from_test(p_user_id uuid, p_language_id smallint, p_question_results jsonb): TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Bulk updates vocabulary knowledge for a user after a comprehension test. Extracts sense IDs from each question's `sense_ids` array, deduplicates (using `bool_or` for correctness), computes BKT updates, and upserts into `user_vocabulary_knowledge`. Computes initial priors from word frequency rank when no prior knowledge exists. Preserves `user_marked_unknown` status.

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

- **Key behaviors:** Frequency-rank-based priors for new words. `user_marked_unknown` status is never overwritten by BKT. Uses `bool_or` dedup (if a sense appears in multiple questions, one correct answer counts as correct).
- **Tables written:** `user_vocabulary_knowledge`.

---

### `update_vocabulary_from_word_test(p_user_id uuid, p_sense_id integer, p_is_correct boolean, p_language_id smallint, p_exercise_type text DEFAULT NULL): TABLE(out_sense_id integer, out_p_known_before numeric, out_p_known_after numeric, out_status text)`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Updates vocabulary knowledge for a single word after a word quiz or exercise. **Phase 5:** Added optional `p_exercise_type` parameter. When provided, routes to `bkt_update_exercise()` (exercise-type-specific slip/guess); when NULL, falls back to `bkt_update_word_test()`. Computes frequency-based priors for new words. Preserves `user_marked_unknown` status.

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

- **Tables written:** `user_vocabulary_knowledge`.

---

### `get_vocab_recommendations(p_user_id uuid, p_language_id integer, p_target_unknown_min double precision DEFAULT 0.03, p_target_unknown_max double precision DEFAULT 0.07, p_limit integer DEFAULT 10): TABLE(id uuid, title text, slug text, unknown_pct float, unknown_count integer)`

- **Security:** DEFINER — **Phase 6 fix:** Added `SET search_path TO 'public', 'pg_temp'`. Also: return type changed (column `test_id` → `id`, `double precision` → `float`), default `p_limit` changed from 20 → 10, old signature explicitly dropped first.
- **Language:** plpgsql
- **Description:** Recommends tests for vocabulary acquisition by finding tests where the percentage of unknown words falls within a target range (default 3-7%). Uses the user's known sense IDs and ELO rating (within +/-200) to filter. Sorts by proximity to the 5% ideal unknown ratio.

```sql
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
$function$
```

- **Key behaviors:** Uses intarray `&` operator for set intersection. Targets i+1 comprehensible input (3-7% unknown words). Old signature must be explicitly dropped first because return type (OUT parameter names) changed.
- **Tables read:** `user_vocabulary`, `user_skill_ratings`, `tests`, `test_skill_ratings`.

---

### `get_word_quiz_candidates(p_user_id uuid, p_sense_ids integer[], p_language_id smallint, p_max_words integer DEFAULT 5): TABLE(...)`

- **Security:** DEFINER (STABLE) — **Phase 6 fix:** Changed from INVOKER to SECURITY DEFINER with `SET search_path TO 'public', 'pg_temp'` because this function reads RLS-protected `user_vocabulary_knowledge`, `dim_word_senses`, and `dim_vocabulary` tables.
- **Language:** plpgsql
- **Description:** Selects word quiz candidates from a set of sense IDs, targeting words the user is actively learning (p_known between 0.25 and 0.75). Scores candidates by knowledge uncertainty weighted by inverse log frequency rank. Excludes words marked as `user_marked_unknown`.

**Returns:** `TABLE(out_sense_id integer, out_lemma text, out_definition text, out_pronunciation text, out_p_known numeric, out_score numeric)`

```sql
CREATE OR REPLACE FUNCTION public.get_word_quiz_candidates(
    p_user_id uuid,
    p_sense_ids integer[],
    p_language_id smallint,
    p_max_words integer DEFAULT 5
)
 RETURNS TABLE(out_sense_id integer, out_lemma text, out_definition text, out_pronunciation text, out_p_known numeric, out_score numeric)
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
$function$
```

- **Key behaviors:** Score formula: `p_known * (1 - p_known) * (1 / ln(frequency_rank))`. Targets maximum uncertainty words weighted toward high-frequency.

---

### `update_user_vocab_stats(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Trigger function that recalculates `total_senses_tracked` by counting keys in the `sense_learning_stats` JSONB column before each row update.

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

## Vocabulary Lookup

---

### `batch_lookup_lemmas(p_lemmas text[], p_language_id integer): TABLE(lemma text, vocab_id integer)`

- **Security:** DEFINER (STABLE)
- **Language:** plpgsql
- **Description:** Bulk lookup of vocabulary IDs by lemma strings for a given language. Used during test ingestion/creation to resolve lemma text to vocabulary table IDs.

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

### `get_distractors(p_sense_id integer, p_language_id smallint, p_count integer DEFAULT 3): TABLE(out_definition text)`

- **Security:** DEFINER (Phase 3 — was INVOKER with no auth check)
- **Language:** plpgsql (STABLE)
- **Description:** Returns random distractor definitions for a word quiz. Now requires authentication. Selects definitions from the same language that are NOT from the same vocabulary item as the target sense, restricted to primary senses (`sense_rank = 1`).

```sql
CREATE OR REPLACE FUNCTION public.get_distractors(p_sense_id integer, p_language_id smallint, p_count integer DEFAULT 3)
 RETURNS TABLE(out_definition text)
 LANGUAGE plpgsql
 STABLE
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Authentication required';
    END IF;

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

- **Key behaviors:** Random selection. Excludes all senses from the same vocab item. **Phase 3:** Now SECURITY DEFINER with auth check and search_path pinning.

---

## Mystery System

---

### `get_recommended_mysteries(p_user_id uuid, p_language_id integer): SETOF jsonb`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** Returns up to 10 recommended mystery games for a user, matched by ELO proximity (within 200 points). Returns JSONB objects with mystery metadata, both ELO ratings, and the ELO gap.

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

- **Key behaviors:** Default mystery ELO 1400. User default 1200. Max 200 ELO gap. Up to 10 results.

---

### `process_mystery_submission(p_user_id uuid, p_mystery_id uuid, p_language_id smallint, p_test_type_id smallint, p_responses jsonb, p_idempotency_key uuid DEFAULT NULL): jsonb`

- **Security:** DEFINER
- **Language:** plpgsql
- **Description:** The mystery submission handler -- analogous to `process_test_submission` but for mystery games. Validates answers against `mystery_questions` (across all scenes), calculates score, updates ELO for both user and mystery (first attempt only), records the attempt, and updates user language activity. Supports idempotency.

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

- **Auth:** Caller must be the user.
- **Side effects:** Creates/updates `user_skill_ratings`, `mystery_skill_ratings`, `mysteries`, inserts `mystery_attempts`, upserts `user_languages`.
- **Key behaviors:** Questions span multiple scenes via `mystery_scenes` join. Uses `ON COMMIT DROP` temp table. ELO only updates on first attempt.

---

## Packs & Content Discovery

---

### `get_packs_with_user_selection(p_language_id integer, p_user_id uuid): TABLE(...)`

- **Security:** INVOKER
- **Language:** SQL (STABLE)
- **Description:** Returns all public collocation packs for a language with a boolean flag indicating whether the user has selected each pack. Used to render the pack selection UI. **Phase 2:** `p_user_id` changed from `text` to `uuid` to match the rebuilt `user_pack_selections` table.

**Returns:** `TABLE(id bigint, pack_name text, description text, pack_type text, tags text[], total_items integer, difficulty_range text, is_selected boolean)`

```sql
CREATE OR REPLACE FUNCTION public.get_packs_with_user_selection(p_language_id integer, p_user_id uuid)
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

- **Phase 2:** Old signature with `text` parameter dropped.

---

### `get_active_languages(): TABLE(id integer, language_code text, language_name text, native_name text)`

- **Security:** DEFINER (Phase 6 — was INVOKER. Needs DEFINER to read RLS-protected dim_languages.)
- **Language:** plpgsql (STABLE)
- **Description:** Returns all active languages from `dim_languages`, ordered by display order. Falls back to `language_name` if `native_name` is NULL.

```sql
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
$function$
```

---

## Corpus & Collocations

---

### `get_top_collocations_for_sources(p_source_ids integer[], p_min_pmi double precision, p_top_n integer): TABLE(...)`

- **Security:** INVOKER
- **Language:** SQL (STABLE)
- **Description:** Returns the top N collocations (by PMI score) from a set of corpus sources, deduplicated by collocation text (keeping the highest-PMI representative).

**Returns:** `TABLE(id bigint, collocation_text text, n_gram_size integer, pmi_score double precision, log_likelihood double precision, t_score double precision, collocation_type text, pos_pattern text, language_id integer)`

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

- **Key behaviors:** Two-phase deduplication: `DISTINCT ON` per collocation_text, then global sort + limit.

---

## Category / Topic Matching

---

### `get_next_category(): TABLE(id integer, name text, status_id integer, target_language_id integer, last_used_at timestamp with time zone, cooldown_days integer)`

- **Security:** DEFINER (Phase 6 — was INVOKER. Needs DEFINER to read RLS-protected dim_status.)
- **Language:** plpgsql
- **Description:** Returns the next available universal category (no specific target language) that is active and has either never been used or has passed its cooldown period. Returns at most 1 row, ordered by least recently used.

```sql
CREATE OR REPLACE FUNCTION public.get_next_category()
 RETURNS TABLE(id integer, name text, status_id integer, target_language_id integer, last_used_at timestamp with time zone, cooldown_days integer)
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

### `match_topics(query_category integer, query_embedding vector, match_threshold double precision DEFAULT 0.85, match_count integer DEFAULT 5): TABLE(id uuid, concept_english text, similarity double precision)`

- **Security:** DEFINER (Phase 6 — was INVOKER. Good practice for DEFINER + search_path.)
- **Language:** plpgsql
- **Description:** Performs cosine similarity search over topic embeddings within a given category using pgvector. Returns topics exceeding the similarity threshold, sorted by similarity descending.

```sql
CREATE OR REPLACE FUNCTION public.match_topics(query_category integer, query_embedding vector, match_threshold double precision DEFAULT 0.85, match_count integer DEFAULT 5)
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
$function$
```

- **Key behaviors:** Uses pgvector cosine distance operator (`<=>`). Converts to similarity (1 - distance). Default threshold 0.85.

---

## Model Config

---

### `get_model_for_task(p_task_key text, p_language_id smallint): text`

- **Security:** INVOKER (STABLE)
- **Language:** plpgsql
- **Description:** Looks up the active LLM model name for a given task key and language from the `language_model_config` table. Returns NULL if no active config exists. **Phase 4 addition** — part of the normalization that replaces growing model columns on `dim_languages`.

```sql
CREATE OR REPLACE FUNCTION public.get_model_for_task(
    p_task_key text,
    p_language_id smallint
)
RETURNS text
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    v_model text;
BEGIN
    SELECT model_name INTO v_model
    FROM language_model_config
    WHERE task_key = p_task_key
      AND language_id = p_language_id
      AND is_active = true
    LIMIT 1;

    RETURN v_model;
END;
$function$
```

- **Key behaviors:** Simple key-value lookup. Returns NULL (not error) when no config found — callers must handle fallback. Only returns active configs.
- **Tables read:** `language_model_config`.

---

## Prompt Templates

---

### `get_prompt_template(p_task_name character varying, p_language_id integer DEFAULT 2): text`

- **Security:** INVOKER
- **Language:** plpgsql (STABLE)
- **Description:** Retrieves the latest active prompt template for a given task, with language-specific override support. **Phase 1 fix:** Now uses `language_id` (integer) instead of `language_code` (text), since `prompt_templates` has `language_id` not `language_code`. Falls back to language_id=2 (English default). Old signature with text parameter dropped.

```sql
CREATE OR REPLACE FUNCTION public.get_prompt_template(
    p_task_name character varying,
    p_language_id integer DEFAULT 2
)
RETURNS text
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    result_text TEXT;
BEGIN
    -- Try language-specific first
    SELECT template_text INTO result_text
    FROM prompt_templates
    WHERE task_name = p_task_name
      AND language_id = p_language_id
      AND is_active = true
    ORDER BY version DESC
    LIMIT 1;

    -- Fall back to English (language_id=2) if not found
    IF result_text IS NULL AND p_language_id != 2 THEN
        SELECT template_text INTO result_text
        FROM prompt_templates
        WHERE task_name = p_task_name
          AND language_id = 2
          AND is_active = true
        ORDER BY version DESC
        LIMIT 1;
    END IF;

    RETURN result_text;
END;
$function$
```

- **Key behaviors:** Language-specific -> English (language_id=2) fallback. Versioned (latest version wins). Only active templates. Old signature with `language_code text` parameter explicitly dropped.

---

## Utility / Triggers

---

### `update_updated_at_column(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Generic trigger function that sets the `updated_at` column to `NOW()` on every row update. Attached to multiple tables throughout the schema.

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

### `sync_exercise_history(): trigger`

- **Security:** INVOKER
- **Language:** plpgsql
- **Description:** Trigger function that auto-populates `user_exercise_history` on every `exercise_attempts` INSERT. Copies user_id, exercise_id, sense_id, exercise_type, is_correct, is_first_attempt, and looks up language_id from the exercises table. **Phase 4 addition** — enables the anti-repetition table without changing existing INSERT paths. Silently catches errors (RAISE WARNING) so the main insert is never blocked.

```sql
CREATE OR REPLACE FUNCTION public.sync_exercise_history()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    INSERT INTO public.user_exercise_history (
        user_id, language_id, exercise_id, sense_id,
        exercise_type, is_correct, is_first_attempt, session_date
    )
    SELECT
        NEW.user_id,
        e.language_id,
        NEW.exercise_id,
        NEW.sense_id,
        NEW.exercise_type,
        NEW.is_correct,
        COALESCE(NEW.is_first_attempt, true),
        CURRENT_DATE
    FROM exercises e
    WHERE e.id = NEW.exercise_id;

    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'sync_exercise_history failed: %', SQLERRM;
    RETURN NEW;
END;
$function$
```

- **Trigger:** `trigger_sync_exercise_history` AFTER INSERT ON `exercise_attempts` FOR EACH ROW.
- **Key behaviors:** Joins exercises table for language_id. Defaults is_first_attempt to true. Session_date = CURRENT_DATE. Exception handler ensures main insert always succeeds.

---

## Security Summary

The following table lists all 48 application functions and their security model:

| # | Function | Security | Auth Check |
|---|----------|----------|------------|
| 1 | `add_tokens_atomic` | DEFINER | Self or admin/moderator |
| 2 | `anonymize_user_data` | DEFINER | Self or admin |
| 3 | `batch_lookup_lemmas` | DEFINER | None (STABLE) |
| 4 | `bkt_apply_decay` | INVOKER | None (IMMUTABLE) |
| 5 | `bkt_effective_p_known` | INVOKER | None (STABLE) |
| 6 | `bkt_phase` | INVOKER | None (IMMUTABLE) |
| 7 | `bkt_phase_thresholds` | INVOKER | None (IMMUTABLE) |
| 8 | `bkt_status` | INVOKER | None (IMMUTABLE) |
| 9 | `bkt_update` | INVOKER | None (IMMUTABLE) |
| 10 | `bkt_update_comprehension` | INVOKER | None (IMMUTABLE) |
| 11 | `bkt_update_exercise` | INVOKER | None (IMMUTABLE) |
| 12 | `bkt_update_word_test` | INVOKER | None (IMMUTABLE) |
| 13 | `calculate_elo_rating` | INVOKER | None (IMMUTABLE) |
| 14 | `calculate_volatility_multiplier` | INVOKER | None (IMMUTABLE) |
| 15 | `can_use_free_test` | DEFINER | Self only |
| 16 | `create_user_dependencies` | INVOKER | Trigger (no direct call) |
| 17 | `get_active_languages` | DEFINER | None (Phase 6: INVOKER→DEFINER) |
| 18 | `get_daily_free_test_limit` | DEFINER | None (called internally) |
| 19 | `get_distractors` | DEFINER | `auth.uid()` required (Phase 3: INVOKER→DEFINER) |
| 20 | `get_model_for_task` | INVOKER | None (STABLE) |
| 21 | `get_next_category` | DEFINER | None (Phase 6: INVOKER→DEFINER) |
| 22 | `get_org_role` | DEFINER | None (STABLE) |
| 23 | `get_packs_with_user_selection` | INVOKER | None (STABLE) |
| 24 | `get_prompt_template` | INVOKER | None (STABLE) |
| 25 | `get_recommended_mysteries` | DEFINER | None |
| 26 | `get_recommended_test` | DEFINER | None |
| 27 | `get_recommended_tests` | DEFINER | None |
| 28 | `get_test_token_cost` | DEFINER | None (called internally) |
| 29 | `get_token_balance` | DEFINER | Self or admin/moderator |
| 30 | `get_top_collocations_for_sources` | INVOKER | None (STABLE) |
| 31 | `get_vocab_recommendations` | DEFINER | None (Phase 6: search_path hardened) |
| 32 | `get_word_quiz_candidates` | DEFINER | None (Phase 6: INVOKER→DEFINER) |
| 33 | `handle_new_user` | DEFINER | Trigger (no direct call) |
| 34 | `is_admin` | DEFINER | None (STABLE) |
| 35 | `is_moderator` | DEFINER | None (STABLE) |
| 36 | `is_org_member` | DEFINER | None (STABLE) |
| 37 | `match_topics` | DEFINER | None (Phase 6: INVOKER→DEFINER) |
| 38 | `process_mystery_submission` | DEFINER | Self only (`auth.uid()`) |
| 39 | `process_stripe_payment` | DEFINER | None (server-side only) |
| 40 | `process_test_submission` | DEFINER | Self only (`auth.uid()`) |
| 41 | `sync_exercise_history` | INVOKER | Trigger (no direct call) |
| 42 | `tests_containing_sense` | INVOKER | None (STABLE) |
| 43 | `update_skill_attempts_count` | INVOKER | Trigger (no direct call) |
| 44 | `update_test_attempts_count` | INVOKER | Trigger (no direct call) |
| 45 | `update_updated_at_column` | INVOKER | Trigger (no direct call) |
| 46 | `update_user_vocab_stats` | INVOKER | Trigger (no direct call) |
| 47 | `update_vocabulary_from_test` | INVOKER | None |
| 48 | `update_vocabulary_from_word_test` | INVOKER | None |

### SECURITY DEFINER Functions (24 total)

These functions execute with the **privileges of the function owner** (typically the database admin), bypassing RLS. They require careful review:

| Function | Reason for DEFINER |
|----------|-------------------|
| `add_tokens_atomic` | Cross-table token operations |
| `anonymize_user_data` | Needs write access to user PII fields |
| `batch_lookup_lemmas` | Reads dimension tables without RLS overhead |
| `can_use_free_test` | Reads subscription tier data |
| `get_active_languages` | Reads RLS-protected dim_languages (Phase 6, +search_path) |
| `get_daily_free_test_limit` | Reads subscription tier data |
| `get_distractors` | Reads RLS-protected dim tables, requires auth (Phase 3, +search_path) |
| `get_next_category` | Reads categories + dim_status (Phase 6, +search_path) |
| `get_org_role` | Reads organization membership |
| `get_recommended_mysteries` | Reads across mystery + skill rating tables |
| `get_recommended_test` | Reads across test + skill rating tables |
| `get_recommended_tests` | Reads across test + skill rating + subscription tables |
| `get_test_token_cost` | Reads subscription tier data |
| `get_token_balance` | Reads token balance (sensitive) |
| `get_vocab_recommendations` | Reads user vocabulary + test data (Phase 6, +search_path) |
| `get_word_quiz_candidates` | Reads RLS-protected vocabulary knowledge tables (Phase 6, +search_path) |
| `handle_new_user` | Creates user rows (auth trigger) |
| `is_admin` | Reads subscription tier admin flag |
| `is_moderator` | Reads subscription tier moderator flag |
| `is_org_member` | Reads organization membership |
| `match_topics` | Reads topics table (Phase 6, +search_path) |
| `process_mystery_submission` | Multi-table transactional write |
| `process_stripe_payment` | Financial transaction with row locking |
| `process_test_submission` | Multi-table transactional write |
