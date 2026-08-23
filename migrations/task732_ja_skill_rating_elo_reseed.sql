-- TASK-732 — re-seed Japanese dictation / pitch_accent ELOs off the flat 1400.
-- Data-only backfill. Defines no objects, so nothing here supersedes another
-- migration and nothing needs archiving.
-- =============================================================================
-- PROBLEM
--   get_recommended_tests ranks candidates by ABS(test_elo - user_elo) and takes
--   the nearest 10 per type. That is the ONLY difficulty signal in test
--   selection — `difficulty` itself is never filtered on.
--
--   For Japanese, reading and listening carried tier-seeded ELOs
--   (875 / 1175 / 1400 / 1550 / 1925, via difficulty_scorer.seed_test_elo), but
--   EVERY dictation and pitch_accent row sat at a flat 1400 regardless of
--   difficulty. The cause is historical: both type codes were added to existing
--   tests by backfills that hard-coded the constant —
--     migrations/add_dictation_mode.sql:42     SELECT DISTINCT tsr.test_id, dt.id, 1400, 0
--     migrations/add_pitch_accent_mode.sql:20  SELECT t.id, dt.id, 1400, 0
--   ZH/EN show a spread only because their rows have since drifted on real
--   attempts; JA has zero attempts, so the seed was still fully exposed.
--
--   Consequence: for half of Japan's plannable skills, selection was
--   difficulty-BLIND. A learner at the 1200 default sees all 80 dictation
--   candidates as equidistant (|1400-1200| = 200 for every one), so the
--   rank_in_type <= 10 cut is arbitrary and an N5/N4 learner can be handed an
--   840-character difficulty-9 dictation on day one.
--
--   The guard that should have caught that is inert in Japanese: the eligibility
--   filter measures transcript length with
--   `array_length(string_to_array(trim(transcript), ' '), 1)`, and Japanese is
--   written without inter-word spaces — live JA transcripts return 1.1 to 15
--   "words" no matter their true length, so dictation_max_words() never excludes
--   anything. That is a SEPARATE defect and is NOT fixed here; this migration
--   only restores the ELO signal, which is what actually drives selection.
--
-- FIX
--   Copy each test's own `reading` ELO onto its dictation / pitch_accent rows.
--   Deliberately NOT dim_complexity_tiers.initial_elo directly:
--     - the reading value is the tier midpoint ALREADY adjusted for the
--       passage's measured lexical complexity by seed_test_elo(), so copying it
--       preserves per-test resolution the bare midpoint would flatten
--       (e.g. difficulty 3 spans 1169-1177, not a uniform 1175); and
--     - it reproduces exactly what a NEWLY generated test looks like, because
--       database_client.insert_test_skill_ratings() writes one `initial_elo`
--       across every type it creates. Post-migration, backfilled and freshly
--       generated JA tests are indistinguishable.
--
--   No code change is needed for tests generated from here on — the orchestrator
--   path was always correct; only the two legacy backfills were not.
--
-- SAFETY / IDEMPOTENCY
--   Guarded on `total_attempts = 0 AND elo_rating = 1400`, so it can only touch
--   untouched backfill seeds: a rating that has drifted on real attempts is
--   never clobbered, and re-running is a no-op. The one JA difficulty-5 test is
--   unaffected despite tier T3's midpoint also being 1400 — its rows were
--   seeded at 1333, so the predicate does not match it.
--
--   Scoped to language_id = 3. ZH/EN carry the same 1400 seeds on
--   never-attempted rows and have the same latent problem; they are left alone
--   deliberately rather than swept up in a JA-driven change.
--
-- APPLIED LIVE: 2026-08-22 (160 rows: 80 dictation + 80 pitch_accent).
--   Verified after: all four JA skills now ascend monotonically with difficulty
--   (d1 875 -> d3 ~1175 -> d5 1333 -> d6 1550 -> d9 1925).
-- =============================================================================

BEGIN;

WITH reading_elo AS (
    SELECT tsr.test_id, tsr.elo_rating
    FROM public.test_skill_ratings tsr
    JOIN public.dim_test_types dtt
      ON dtt.id = tsr.test_type_id AND dtt.type_code = 'reading'
    JOIN public.tests t
      ON t.id = tsr.test_id AND t.language_id = 3
)
UPDATE public.test_skill_ratings tsr
SET elo_rating = re.elo_rating
FROM reading_elo re, public.dim_test_types dtt, public.tests t
WHERE tsr.test_id = re.test_id
  AND tsr.test_type_id = dtt.id
  AND t.id = tsr.test_id
  AND t.language_id = 3
  AND dtt.type_code IN ('dictation', 'pitch_accent')
  AND tsr.total_attempts = 0
  AND tsr.elo_rating = 1400;

COMMIT;
