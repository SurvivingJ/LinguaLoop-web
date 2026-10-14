-- =============================================================================
-- security_users_tokens_audit.sql  (TASK-875 pre-apply audit) -- READ-ONLY
-- =============================================================================
-- SELECT-only. Run BEFORE migrations/security_lock_users_tokens_reports.sql to see
-- whether the self-escalation / balance-forgery holes were already exploited.
-- Do NOT auto-fix any row from the results; report to the developer.
-- Section A returns counts only (no personal data). Sections B and C list user ids
-- and balances (personal data: run in a trusted session only).
-- Admin session rotation is a developer decision (decided: NO rotation).
-- =============================================================================

-- A1. Users by tier (counts only). Expect: only the default tier plus intended
--     paid tiers; any is_admin / is_moderator count should match known staff.
SELECT dst.id AS tier_id, dst.tier_code, dst.is_admin, dst.is_moderator,
       COUNT(u.id) AS users
  FROM public.dim_subscription_tiers dst
  LEFT JOIN public.users u ON u.subscription_tier_id = dst.id AND u.deleted_at IS NULL
 GROUP BY dst.id, dst.tier_code, dst.is_admin, dst.is_moderator
 ORDER BY dst.id;

-- A2. Token ledger consistency (counts only): users whose purchased_tokens differs
--     from the sum of valid ledger rows (tokens_added - tokens_consumed).
WITH ledger AS (
  SELECT user_id,
         COALESCE(SUM(COALESCE(tokens_added,0) - COALESCE(tokens_consumed,0)), 0) AS ledger_balance
    FROM public.token_transactions
   WHERE COALESCE(is_valid, true)
   GROUP BY user_id
)
SELECT COUNT(*)                                                     AS users_with_tokens_row,
       COUNT(*) FILTER (WHERE ut.purchased_tokens <> COALESCE(l.ledger_balance, 0)) AS mismatched,
       COUNT(*) FILTER (WHERE ut.purchased_tokens >  COALESCE(l.ledger_balance, 0)) AS balance_above_ledger
  FROM public.user_tokens ut
  LEFT JOIN ledger l ON l.user_id = ut.user_id;

-- B. (PERSONAL DATA) Admin / non-default-tier users. Default tier = the lowest
--    display_order tier; adjust if the free tier differs.
SELECT u.id, u.subscription_tier_id, dst.tier_code, dst.is_admin, dst.is_moderator,
       u.created_at, u.updated_at
  FROM public.users u
  JOIN public.dim_subscription_tiers dst ON dst.id = u.subscription_tier_id
 WHERE u.deleted_at IS NULL
   AND (dst.is_admin OR dst.is_moderator
        OR dst.display_order > (SELECT MIN(display_order) FROM public.dim_subscription_tiers))
 ORDER BY dst.is_admin DESC, dst.display_order DESC, u.created_at;

-- C. (PERSONAL DATA) Balance vs ledger mismatches.
WITH ledger AS (
  SELECT user_id,
         COALESCE(SUM(COALESCE(tokens_added,0) - COALESCE(tokens_consumed,0)), 0) AS ledger_balance
    FROM public.token_transactions
   WHERE COALESCE(is_valid, true)
   GROUP BY user_id
)
SELECT ut.user_id, ut.purchased_tokens, COALESCE(l.ledger_balance, 0) AS ledger_balance,
       ut.purchased_tokens - COALESCE(l.ledger_balance, 0) AS delta, ut.updated_at
  FROM public.user_tokens ut
  LEFT JOIN ledger l ON l.user_id = ut.user_id
 WHERE ut.purchased_tokens <> COALESCE(l.ledger_balance, 0)
 ORDER BY delta DESC;
