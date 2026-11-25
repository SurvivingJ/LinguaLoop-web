-- ============================================================================
-- baseline_process_stripe_payment.sql — repo record of the live public.process_stripe_payment
-- ============================================================================
--
-- WHAT: Credits purchased tokens for a Stripe payment, idempotent on payment_intent_id, and records a token_transactions row.
-- Used by: No caller in the app code today (finding F-08; the token economy is a product decision).
--
-- WHY: this function exists live but had no CREATE in any migrations/ file
-- (including archive/): finding F-03 of the 2026-11-23 database review. The
-- definition below is pg_get_functiondef() read from live
-- (kpfqrjtfxmujzolwsvdq) on 2026-11-23, with CRLF line ends normalised to LF,
-- plus the live owner and the live ACL ({postgres=X/postgres,service_role=X/postgres}:
-- EXECUTE for service_role only, nothing for PUBLIC / anon / authenticated).
--
-- WHAT A LEARNER OR THE APP WOULD NOTICE: nothing. Applying this file is a
-- no-op: the body hashes equal to live (md5 of prosrc with -- comments and all
-- whitespace removed = f45bc5f77d0d5f9cac0fa2d870614dab), and the attributes, owner and grants
-- are the live ones. It exists so the repo can rebuild the database and so the
-- next change to this function has a file to start from.
--
-- PRECONDITIONS: none beyond the tables/functions the body reads, all live.
--
-- VERIFY (read-only; run before and after; expect body_matches = true,
-- definer = true, search_path = {search_path=public, pg_temp}, anon_x = false, auth_x = false,
-- service_x = true):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g'))
--            = 'f45bc5f77d0d5f9cac0fa2d870614dab' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.process_stripe_payment(uuid,integer,text,text,integer)'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.process_stripe_payment(p_user_id uuid, p_tokens_to_add integer, p_payment_intent_id text, p_package_id text, p_amount_cents integer)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
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
$function$;
ALTER FUNCTION public.process_stripe_payment(uuid,integer,text,text,integer) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.process_stripe_payment(uuid,integer,text,text,integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.process_stripe_payment(uuid,integer,text,text,integer) TO service_role;
