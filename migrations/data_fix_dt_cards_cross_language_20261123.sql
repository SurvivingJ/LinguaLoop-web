-- ============================================================================
-- DATA FIX (ONE-OFF) — delete two review cards built from the wrong language
-- and re-queue their profile entry
-- Date: 2026-11-23   Review: pkg8 (coordinator item 2). NOT APPLIED.
--
-- APPLY ONLY AFTER the code fix to services/dual_translation/cards.py (the
-- language filter in _latest_error_for_subtype / generate_cards_for_queued_entries)
-- is DEPLOYED. Before that, the next GET /next or /cards/due rebuilds the same
-- wrong cards from the same Japanese error.
--
-- WHAT IS WRONG (checked read-only 2026-11-23):
--   dt_card 11 (cloze) and 12 (isolate_retranslate) belong to
--   dt_error_profile_entry 10 (l1 2, l2 1 = zh, subtype word_choice,
--   remediation_status 'drilling'), but their origin_error_id 49 belongs to
--   dt_submission 111 on dt_passage 120, whose l2_language_id is 3 (ja).
--   generate_cards_for_queued_entries picked "the user's latest error of this
--   subtype" without a language filter. Both cards are state 'new' with 0
--   dt_card_review rows (dt_card_review has 0 rows in total).
--   Cards 15 and 16 also come from error 49 but belong to entry 16 (l2 3 = ja):
--   they are correct and are NOT touched.
--   Whole-table check (query below): cards 11 and 12 are the only dt_card rows
--   whose origin error's passage language differs from the profile entry's
--   l2 (4 cards in total live); no card has an L1 mismatch either.
--   The user has 6 zh word_choice errors (ids 23, 28, 34, 39, 40, 43), so the
--   fixed code has a correct error to build new cards from.
--
-- WHAT THIS DOES (one transaction):
--   1. asserts the state above;
--   2. DELETE FROM dt_card WHERE id IN (11, 12)  (dt_card_review children: 0,
--      asserted; dt_card has no other FK children);
--   3. sets dt_error_profile_entry 10 remediation_status 'drilling' -> 'queued'.
--   generate_cards_for_queued_entries cards an entry when its status is
--   'queued' AND it has no dt_card row; after this both hold for entry 10, so
--   the next /next (or /cards/due) for that user builds fresh cards and flips
--   it back to 'drilling'. Nightly synthesis keeps 'queued' as 'queued'
--   (synthesis.decide_status).
--
-- WHAT A LEARNER WOULD NOTICE: the one affected learner (zh, L1 2) stops being
-- shown two Japanese-sentence cards in their Chinese word_choice drill and gets
-- two cards built from a Chinese error instead. No review history is lost.
--
-- HOW TO RUN: as one session (psql or the SQL editor, NOT a migration tool that
-- auto-commits). The file stops before COMMIT: read the NOTICE lines, then run
-- COMMIT; yourself (or ROLLBACK;). Any assertion failure raises and aborts the
-- transaction with nothing changed. Re-running after commit fails the first
-- assertion (cards gone), which is the intended guard.
--
-- PRE-CHECK (read-only; expect exactly cards 11 and 12, each with
-- passage_l2 = 3, entry_l2 = 1, reviews = 0):
--   SELECT c.id AS card_id, c.profile_entry_id, pe.l1_language_id AS entry_l1,
--          pe.l2_language_id AS entry_l2, s.l1_language_id AS sub_l1,
--          p.l2_language_id AS passage_l2, pe.remediation_status,
--          (SELECT count(*) FROM public.dt_card_review r WHERE r.card_id = c.id) AS reviews
--     FROM public.dt_card c
--     JOIN public.dt_error_profile_entry pe ON pe.id = c.profile_entry_id
--     JOIN public.dt_error_instance ei ON ei.id = c.origin_error_id
--     JOIN public.dt_submission s ON s.id = ei.submission_id
--     JOIN public.dt_passage p ON p.id = s.passage_id
--    WHERE p.l2_language_id IS DISTINCT FROM pe.l2_language_id
--       OR s.l1_language_id IS DISTINCT FROM pe.l1_language_id;
-- POST-CHECK (read-only; expect the query above to return 0 rows, and
-- entry 10 'queued' with 0 cards until the user's next /next, then 'drilling'
-- with new cards whose passage l2 is 1):
--   SELECT pe.id, pe.remediation_status, count(c.id) AS cards
--     FROM public.dt_error_profile_entry pe
--     LEFT JOIN public.dt_card c ON c.profile_entry_id = pe.id
--    WHERE pe.id = 10 GROUP BY pe.id, pe.remediation_status;
--
-- ROLLBACK (after COMMIT): not needed for correctness. The deleted rows are
-- reproducible by the old code; their exact values can be saved first with
--   SELECT * FROM public.dt_card WHERE id IN (11, 12);
-- and re-inserted, then UPDATE dt_error_profile_entry SET remediation_status =
-- 'drilling' WHERE id = 10.
--
-- After it has run: move this file to migrations/archive/ with a README row
-- (spent one-shot, like phase13_wipe_user_state_for_launch.sql).
-- ============================================================================

BEGIN;

DO $$
DECLARE
    v_n integer;
BEGIN
    SELECT count(*) INTO v_n
      FROM public.dt_card c
      JOIN public.dt_error_profile_entry pe ON pe.id = c.profile_entry_id
      JOIN public.dt_error_instance ei ON ei.id = c.origin_error_id
      JOIN public.dt_submission s ON s.id = ei.submission_id
      JOIN public.dt_passage p ON p.id = s.passage_id
     WHERE c.id IN (11, 12)
       AND c.profile_entry_id = 10
       AND c.origin_error_id = 49
       AND pe.l2_language_id = 1
       AND p.l2_language_id = 3;
    IF v_n <> 2 THEN
        RAISE EXCEPTION 'data fix: expected cards 11 and 12 (entry 10, zh) built from ja error 49, found % matching rows', v_n;
    END IF;

    SELECT count(*) INTO v_n FROM public.dt_card_review WHERE card_id IN (11, 12);
    IF v_n <> 0 THEN
        RAISE EXCEPTION 'data fix: cards 11/12 have % reviews; decide what to do with them before deleting', v_n;
    END IF;

    SELECT count(*) INTO v_n FROM public.dt_card WHERE profile_entry_id = 10 AND id NOT IN (11, 12);
    IF v_n <> 0 THEN
        RAISE EXCEPTION 'data fix: entry 10 has % other cards; re-queueing would not regenerate', v_n;
    END IF;

    SELECT count(*) INTO v_n FROM public.dt_error_profile_entry
     WHERE id = 10 AND remediation_status = 'drilling';
    IF v_n <> 1 THEN
        RAISE EXCEPTION 'data fix: entry 10 is not in drilling';
    END IF;
END $$;

DO $$
DECLARE
    v_n integer;
BEGIN
    DELETE FROM public.dt_card WHERE id IN (11, 12);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    IF v_n <> 2 THEN
        RAISE EXCEPTION 'data fix: deleted % dt_card rows, expected 2', v_n;
    END IF;
    RAISE NOTICE 'data fix: deleted dt_card 11, 12';

    UPDATE public.dt_error_profile_entry
       SET remediation_status = 'queued', updated_at = now()
     WHERE id = 10 AND remediation_status = 'drilling';
    GET DIAGNOSTICS v_n = ROW_COUNT;
    IF v_n <> 1 THEN
        RAISE EXCEPTION 'data fix: updated % profile entries, expected 1', v_n;
    END IF;
    RAISE NOTICE 'data fix: dt_error_profile_entry 10 -> queued';
END $$;

-- Review the NOTICE lines above, then run ONE of:
-- COMMIT;
-- ROLLBACK;
