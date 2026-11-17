-- ============================================================================
-- test_sentence_references_faithful_reviews.sql — reviewer agreement overrides
-- the tightness floor (ADR-049, TASK-1009)
-- Date: 2026-11-17
-- Spec: wiki/features/test-sentence-references.tech.md ("Floor override")
--       wiki/decisions/ADR-049-reviewer-agreement-overrides-tightness-floor.md
--
-- Adds:
--   * test_sentence_references.faithful_reviews — how many independent reviews
--     (distinct run_id) gave this exact l1_text a `pass` or wrote it as their
--     `rewritten` text, for the same (sentence, L1). The window gate
--     (passage_builder.window_meets_floor, used by select_window_for_primed for
--     GET /next and Produce; mirrored in build_daily_session_dt_agreed.sql) leaves
--     a sentence with faithful_reviews >= 2 out of the window's mean tightness:
--     two reviewers agreeing beats a noisy back-translation score. A second
--     review (scripts/sentence_ref_recheck.py) is always blind-first, so any
--     count of 2 includes a blind judgement of this exact text.
--
-- Backfill: computed from the rows already present (active and inactive).
-- scripts/upload_sentence_references.py sets it on every new row.
--
-- Additive and idempotent. Rollback: ALTER TABLE ... DROP COLUMN faithful_reviews
-- (no code path needs it until the TASK-1009 code is deployed; that code reads
-- it, so deploy after this file is applied).
-- RLS/privileges unchanged (table is service-role only, ADR-034).
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/test_sentence_references_faithful_reviews.sql
-- ============================================================================

BEGIN;

ALTER TABLE public.test_sentence_references
    ADD COLUMN IF NOT EXISTS faithful_reviews smallint NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'test_sentence_references_faithful_reviews_chk'
    ) THEN
        ALTER TABLE public.test_sentence_references
            ADD CONSTRAINT test_sentence_references_faithful_reviews_chk
            CHECK (faithful_reviews >= 0);
    END IF;
END $$;

COMMENT ON COLUMN public.test_sentence_references.faithful_reviews IS
    'Independent reviews (distinct run_id) that passed or wrote this exact l1_text for this '
    '(sentence, L1). >= 2 lets the sentence skip the tightness floor in window selection (ADR-049).';

UPDATE public.test_sentence_references r
SET faithful_reviews = sub.n
FROM (
    SELECT r2.id,
           (SELECT count(DISTINCT x.run_id)
            FROM public.test_sentence_references x
            WHERE x.sentence_id = r2.sentence_id
              AND x.l1_language_id = r2.l1_language_id
              AND x.l1_text = r2.l1_text
              AND x.review_verdict IN ('pass', 'rewritten'))::smallint AS n
    FROM public.test_sentence_references r2
    WHERE r2.review_verdict IN ('pass', 'rewritten')
) sub
WHERE r.id = sub.id
  AND r.faithful_reviews IS DISTINCT FROM sub.n;

COMMIT;
