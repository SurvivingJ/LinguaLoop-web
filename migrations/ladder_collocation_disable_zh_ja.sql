-- ============================================================================
-- Disable L5/L8 collocation for Chinese and Japanese
-- Date: 2026-08-14
-- Audit finding: B1 ("the coverage sweep will bill you forever for a gap it
--                     cannot close")
--
-- The problem
-- -----------
-- v_sense_family_coverage derives a sense's *required* families purely from
-- dim_exercise_capabilities: any enabled row whose pos_classes match the sense
-- contributes its level's family. L5 (collocation_gap_fill) and L8
-- (collocation_repair) were enabled for abstract/action/property in all three
-- languages, so every such sense was required to hold the `collocation` family.
--
-- But services/vocabulary_ladder/asset_pipeline.py drops L5 unless the
-- (lemma, collocate) pair is `corpus_validated`, and the grounding sources say
-- that can almost never happen outside English —
-- collocation_grounding.GROUNDING_SOURCES:
--     1 (zh) -> corpus_collocations only  (the table holds 40 rows)
--     2 (en) -> bundled frequency list, then corpus
--     3 (ja) -> ()  — deferred by design, no source exists
--
-- So the requirement was unsatisfiable for zh and ja. queue_drain.
-- enqueue_coverage_gaps runs after every batch, re-enqueued each unsatisfiable
-- sense, and run_nightly_drain then paid for a full P1+P2+P3+judges
-- regeneration per sense. The gap did not close and the row returned the next
-- night. At a 9,000-sense fill that is ~6,000 permanently stuck rows grinding
-- through the 50-per-night cap indefinitely, crowding out real regeneration.
--
-- The fix
-- -------
-- The capability matrix is the routing source of truth, so flipping is_enabled
-- corrects the coverage view, the generation planner and the exercise renderer
-- together. It also states the honest thing: zh and ja run a 7-level ladder,
-- not a 9-level one.
--
-- English is deliberately untouched — it has a real grounding source, and its
-- remaining collocation gaps are ordinary generation misses, not an
-- unsatisfiable requirement.
--
-- Re-enable Chinese by flipping these two rows back once corpus_collocations
-- has been filled for zh (see the "collocation corpus fill" work item).
-- Japanese stays disabled until a JA grounding source exists at all.
--
-- Redefines no object (data-only UPDATE on an existing table), so nothing is
-- archived per migrations/CLAUDE.md. The canonical seed
-- migrations/dim_exercise_capabilities.sql has been updated in place to match,
-- so re-asserting the matrix does not silently undo this.
--
-- Idempotent: re-running is a no-op once the flags are false.
-- ============================================================================

UPDATE public.dim_exercise_capabilities
SET is_enabled = false
WHERE type_code IN ('collocation_gap_fill', 'collocation_repair')
  AND language_id IN (1, 3)          -- 1 = Chinese, 3 = Japanese
  AND is_enabled;

-- Verify (expect 4 rows, all is_enabled = false):
--   SELECT language_id, type_code, ladder_level, is_enabled
--   FROM public.dim_exercise_capabilities
--   WHERE type_code IN ('collocation_gap_fill','collocation_repair')
--     AND language_id IN (1,3);
--
-- And that the coverage view no longer demands the family (expect no
-- `collocation` row for language_id 1 or 3):
--   SELECT language_id, unnest(missing_families) AS family, count(*)
--   FROM v_sense_family_coverage WHERE missing_count > 0 GROUP BY 1,2;
