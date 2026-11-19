-- =============================================================================
-- Knowledge Report foundation (TASK-1034): snapshot table + frame / pairs / prune functions
-- Spec: wiki/features/knowledge-report.tech.md §5.1, §6.1, §7; ADR-051, ADR-053.
--
-- *** LIVE-DB: the OWNER applies this file to production (the only Supabase project).
-- *** Agents never apply it. Apply order and post-apply checks: see the report of TASK-1034.
--
-- Objects (all new; no existing table, column, index or function is altered):
--   table    public.user_knowledge_snapshots          one row per (user, language, UTC day)
--   function public.knowledge_frame_bands()            frame sizes N_b per (word lang, definition lang)
--   function public.knowledge_active_pairs(timestamptz) (user, language) pairs the nightly job snapshots
--   function public.knowledge_snapshots_prune(integer) daily rows for N days, then Mondays only
--
-- Writes only through Flask (service role): RLS on, no policy, no client privilege.
-- The report never calls a decay function (ADR-052) and never reads the level-tag column.
--
-- SIZE: table ~24 KB empty; ~300 B per row (MEASURED composite 256 B, tech Appendix B K8);
--       ~0.23 MB in year one at today's 5 pairs with pruning. Functions: catalog only.
-- RETENTION: knowledge_snapshots_prune(120) keeps 120 days of daily rows, then Mondays.
-- VERIFY (read-only, after apply):
--   tests/sql/check_function_acls.sql                    -> every result set empty
--   SELECT knowledge_frame_bands()->'3:2';               -> [577,425,621,655,537,283,77] (2026-11-19)
--   SELECT knowledge_active_pairs(now() - interval '180 days');
--   SELECT pg_database_size(current_database());         -> grows by < 0.3 MB
-- Idempotent: CREATE TABLE IF NOT EXISTS / CREATE OR REPLACE / repeatable REVOKE + GRANT.
-- Rollback: migrations/knowledge_report_foundation_rollback.sql
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. user_knowledge_snapshots (tech §5.1, ADR-053)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_knowledge_snapshots (
  user_id                    uuid        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  language_id                smallint    NOT NULL REFERENCES public.dim_languages(id),
  snapshot_date              date        NOT NULL,              -- UTC date of the job run
  method_version             smallint    NOT NULL DEFAULT 1,    -- bump when any §2 definition changes
  tracked_words              integer     NOT NULL,
  tracked_meanings           integer     NOT NULL,
  rated_known_words          integer     NOT NULL,
  checked_meanings           integer     NOT NULL,
  missed_recent_meanings     integer     NOT NULL,
  idle60_meanings            integer     NOT NULL,
  practised_30_meanings      integer     NOT NULL,
  direct_checks_30           integer     NOT NULL,
  cal_definition_language_id smallint    REFERENCES public.dim_languages(id),   -- D*; NULL = no answers
  cal_bands                  smallint[]  CHECK (cal_bands IS NULL OR array_length(cal_bands, 1) = 21),
                                         -- n_1..n_7, s_1..s_7, c_1..c_7 (latest answer per lemma, rank 1, window)
  frame_bands                integer[]   CHECK (frame_bands IS NULL OR array_length(frame_bands, 1) = 7),
  cal_answers                integer     NOT NULL DEFAULT 0,
  cal_first_answer_at        timestamptz,
  cal_last_answer_at         timestamptz,
  est_kind                   smallint    NOT NULL DEFAULT 0 CHECK (est_kind BETWEEN 0 AND 2),  -- 0 none, 1 range, 2 upper only
  est_lo                     integer,
  est_hi                     integer,
  est_label                  smallint    CHECK (est_label BETWEEN 1 AND 3),                    -- 1 rough, 2 medium, 3 good
  source                     text        NOT NULL DEFAULT 'nightly' CHECK (source IN ('nightly', 'manual')),
  computed_at                timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, language_id, snapshot_date)
);

ALTER TABLE public.user_knowledge_snapshots ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.user_knowledge_snapshots FROM PUBLIC, anon, authenticated;
-- No policies: only Flask (service role) reads and writes it (nightly upsert, anchor reads, prune).
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_knowledge_snapshots TO service_role;

COMMENT ON TABLE public.user_knowledge_snapshots IS
    'Knowledge Report history (ADR-053, TASK-1034): one row per (user, language, UTC snapshot_date), '
    'written by the nightly job services/knowledge_snapshots.py; stores measured counts, the '
    'estimator inputs (cal_bands n/s/c x 7, frame_bands) and outputs. Service role only.';

-- -----------------------------------------------------------------------------
-- 2. knowledge_frame_bands(): {"<L>:<D>": [N_1..N_7]} (tech §2.1, §6.1; ADR-051)
--    Frame F(L, D) = lemmas with a rank-1 sense row in calibration_anchor_pool for (L, D),
--    has_embedding, not blocklisted; N_b = count(DISTINCT vocab_id) per pool zipf_band.
--    Missing bands are 0. Flask caches the result per process for 3,600 s.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.knowledge_frame_bands()
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
    WITH c AS (
        SELECT p.word_language_id AS l, p.definition_language_id AS d, p.zipf_band AS b,
               count(DISTINCT p.vocab_id) AS n
          FROM calibration_anchor_pool p
          JOIN dim_word_senses s ON s.id = p.sense_id AND s.sense_rank = 1
         WHERE p.has_embedding
           AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl WHERE bl.sense_id = p.sense_id)
         GROUP BY 1, 2, 3
    ), pairs AS (
        SELECT DISTINCT l, d FROM c
    )
    SELECT coalesce(jsonb_object_agg(
               pr.l::text || ':' || pr.d::text,
               (SELECT jsonb_agg(coalesce(c.n, 0) ORDER BY g.b)
                  FROM generate_series(1, 7) AS g(b)
                  LEFT JOIN c ON c.l = pr.l AND c.d = pr.d AND c.b = g.b)),
           '{}'::jsonb)
      FROM pairs pr;
$$;

REVOKE ALL ON FUNCTION public.knowledge_frame_bands() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.knowledge_frame_bands() TO service_role;

COMMENT ON FUNCTION public.knowledge_frame_bands() IS
    'Knowledge Report frame sizes (ADR-051, TASK-1034): {"<word_language_id>:<definition_language_id>": '
    '[N_1..N_7]}, N_b = distinct rank-1 pool lemmas (has_embedding, not blocklisted) per zipf_band.';

-- -----------------------------------------------------------------------------
-- 3. knowledge_active_pairs(p_since): [{"user_id", "language_id"}] (tech §6.1, §7)
--    Pairs with >= 1 UVK row, UNION pairs with a definition-mode check answer after p_since.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.knowledge_active_pairs(p_since timestamptz)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
    SELECT coalesce(jsonb_agg(jsonb_build_object('user_id', x.user_id, 'language_id', x.language_id)
                              ORDER BY x.user_id, x.language_id),
                    '[]'::jsonb)
      FROM (
          SELECT DISTINCT k.user_id, k.language_id
            FROM user_vocabulary_knowledge k
          UNION
          SELECT cs.user_id, cs.word_language_id
            FROM calibration_sessions cs
            JOIN calibration_responses cr ON cr.session_id = cs.id
           WHERE cs.mode = 'definition'
             AND cr.answered_at > p_since
      ) x;
$$;

REVOKE ALL ON FUNCTION public.knowledge_active_pairs(timestamptz) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.knowledge_active_pairs(timestamptz) TO service_role;

COMMENT ON FUNCTION public.knowledge_active_pairs(timestamptz) IS
    'Knowledge Report nightly job input (ADR-053, TASK-1034): (user, language) pairs with a UVK row, '
    'or a definition-mode check answer after p_since (NULL p_since adds no check pairs).';

-- -----------------------------------------------------------------------------
-- 4. knowledge_snapshots_prune(p_keep_daily_days): rows deleted (tech §6.1, §5.1)
--    Keeps every row of the last p_keep_daily_days UTC days and Monday rows (ISO dow 1) before.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.knowledge_snapshots_prune(p_keep_daily_days integer DEFAULT 120)
RETURNS integer
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_deleted integer;
BEGIN
    IF p_keep_daily_days IS NULL OR p_keep_daily_days < 35 THEN
        RAISE EXCEPTION 'keep_daily_days_too_small' USING ERRCODE = '22023';
    END IF;

    DELETE FROM user_knowledge_snapshots
     WHERE snapshot_date < (now() AT TIME ZONE 'UTC')::date - p_keep_daily_days
       AND extract(isodow FROM snapshot_date) <> 1;
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$;

REVOKE ALL ON FUNCTION public.knowledge_snapshots_prune(integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.knowledge_snapshots_prune(integer) TO service_role;

COMMENT ON FUNCTION public.knowledge_snapshots_prune(integer) IS
    'Knowledge Report retention (ADR-053, TASK-1034): deletes snapshot rows older than '
    'p_keep_daily_days UTC days except Mondays; returns the number deleted; raises '
    'keep_daily_days_too_small below 35.';

NOTIFY pgrst, 'reload schema';

COMMIT;
