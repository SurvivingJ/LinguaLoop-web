-- ============================================================================
-- baseline_semdisc_note_is_vague.sql — repo record of the live public.semdisc_note_is_vague
-- ============================================================================
--
-- WHAT: IMMUTABLE predicate: true when a semantic-discrimination explanation note is missing, short, or a stock phrase.
-- Used by: No caller in the app code or the database (finding F-08); left over from the semdisc rewrite (TASK-1031 dropped its other objects).
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
-- whitespace removed = e1620c946d6f773b58a610296088a7a9), and the attributes, owner and grants
-- are the live ones. It exists so the repo can rebuild the database and so the
-- next change to this function has a file to start from.
--
-- Live this function is SECURITY INVOKER with no pinned search_path; reproduced as live
-- (advisor function_search_path_mutable, finding F-14, is a separate task).
--
-- The regex keeps its literal kana/kanji range (ぁ-ん, ァ-ン, 一-龥) as live
-- has it. None of those code points (U+3041, U+3093, U+30A1, U+30F3,
-- U+4E00, U+9FA5) changes under Unicode NFC, so the apply path cannot alter
-- them (contrast finding F-05).
--
-- PRECONDITIONS: none beyond the tables/functions the body reads, all live.
--
-- VERIFY (read-only; run before and after; expect body_matches = true,
-- definer = false, search_path = NULL, anon_x = false, auth_x = false,
-- service_x = true):
--   SELECT md5(regexp_replace(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'), '\s', '', 'g'))
--            = 'e1620c946d6f773b58a610296088a7a9' AS body_matches,
--          p.prosecdef AS definer, p.proconfig AS search_path, pg_get_userbyid(p.proowner) AS owner,
--          has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_x,
--          has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_x,
--          has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_x
--     FROM pg_proc p WHERE p.oid = 'public.semdisc_note_is_vague(text)'::regprocedure;
--
-- ROLLBACK: none needed (the file changes nothing). If a later edit of this
-- file is applied by mistake, re-apply this file at the commit that added it.
--
-- Idempotent: CREATE OR REPLACE + REVOKE/GRANT; safe to re-run.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.semdisc_note_is_vague(n text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
  select n is null or length(trim(n)) < 40
    or n ~* '(does ?n.t fit (the|this)? ?context|doesn.t fit|not appropriate here|is (used )?incorrect(ly)?\.?$|wrong usage\.?$|unnatural\.?$|inappropriate\.?$)'
    or n ~ '[ぁ-んァ-ン一-龥]{20,}' and n !~ '[A-Za-z]{3,}'
$function$;
ALTER FUNCTION public.semdisc_note_is_vague(text) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.semdisc_note_is_vague(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.semdisc_note_is_vague(text) TO service_role;
