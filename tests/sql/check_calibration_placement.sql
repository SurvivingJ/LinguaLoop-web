-- =============================================================================
-- check_calibration_placement.sql  (TASK-1076, TASK-1077, TASK-1079)  READ-ONLY
-- =============================================================================
-- Run after the owner applies, in order, calibration_placement.sql,
-- calibration_zh_tones.sql (TASK-1092), calibration_placement_rpcs.sql and
-- knowledge_calibration_inputs.sql. SELECTs only; nothing is written.
--   psql "$DATABASE_URL" -f tests/sql/check_calibration_placement.sql
-- or paste section by section into the Supabase SQL editor. Section 5 (ready counts)
-- takes ~30 s per zh pair on the live pool (two calibration_zh_tone_variants calls per
-- lemma), above PostgREST's 8 s statement timeout: run it here, not through an RPC.
-- Also run tests/sql/check_function_acls.sql (every result set empty) and
-- scripts/verify_placement_rpcs.py --user <test account>.
-- =============================================================================

-- 1. Columns (TASK-1076): 2 new on calibration_sessions, 9 on calibration_responses
SELECT table_name, column_name, data_type, udt_name, is_nullable, column_default
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND ((table_name = 'calibration_sessions' AND column_name IN ('stop_reason', 'result'))
     OR (table_name = 'calibration_responses' AND column_name IN (
           'item_kind', 'probe_kind', 'instrument', 'pair_response_id', 'option_sense_ids',
           'key_position', 'option_roles', 'option_texts', 'chosen_position')))
 ORDER BY table_name, column_name;

-- 2. Constraints: all validated; the mode check admits 'placement'
SELECT conrelid::regclass AS tbl, conname, convalidated, pg_get_constraintdef(oid) AS def
  FROM pg_constraint
 WHERE conrelid IN ('public.calibration_sessions'::regclass, 'public.calibration_responses'::regclass)
 ORDER BY 1, 2;

-- 3. Indexes and sizes; relfilenode must equal the pre-apply value (179439 / 179461 on
--    2026-11-19): no table rewrite
SELECT indexrelid::regclass AS index, pg_size_pretty(pg_relation_size(indexrelid)) AS size,
       pg_get_indexdef(indexrelid) AS def
  FROM pg_index WHERE indrelid = 'public.calibration_responses'::regclass ORDER BY 1;
SELECT relname, relfilenode, pg_size_pretty(pg_total_relation_size(oid)) AS total
  FROM pg_class WHERE relname IN ('calibration_sessions', 'calibration_responses');

-- 4. Functions present, service role only (expect: anon f, authenticated f, service_role t)
SELECT p.oid::regprocedure AS fn, p.prosecdef AS definer,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
       has_function_privilege('authenticated', p.oid, 'EXECUTE') AS authenticated,
       has_function_privilege('service_role', p.oid, 'EXECUTE') AS service_role
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname = 'public'
 WHERE p.proname LIKE 'calibration_placement%' OR p.proname IN ('knowledge_calibration_inputs',
                                                                 'calibration_zh_tone_variants')
 ORDER BY 1;

-- 5. Launch gate (tech §2; record in wiki/log.md): ready counts for the five pairs
SELECT l, d, x->>'frame' AS frame, x->>'ready' AS ready,
       round(100.0 * (x->>'ready')::int / nullif((x->>'frame')::int, 0), 1) AS ready_pct,
       (SELECT min(round(100.0 * (b->>'ready_n')::int / nullif((b->>'frame_n')::int, 0), 1))
          FROM jsonb_array_elements(x->'bands') b) AS worst_band_pct,
       (SELECT sum((b->>'excluded_rule5_n')::int) FROM jsonb_array_elements(x->'bands') b) AS excl_rule5,
       (SELECT sum((b->>'excluded_rule3b_n')::int) FROM jsonb_array_elements(x->'bands') b) AS excl_rule3b,
       (SELECT sum((b->>'excluded_tone_n')::int) FROM jsonb_array_elements(x->'bands') b) AS excl_tone,
       x->'bands' AS bands
  FROM (VALUES (1::smallint, 2::smallint), (1::smallint, 3::smallint), (3::smallint, 1::smallint),
               (3::smallint, 2::smallint), (2::smallint, 2::smallint)) v(l, d)
 CROSS JOIN LATERAL (SELECT calibration_placement_ready_counts(v.l, v.d) AS x) r;

-- 6. Rule 5 residual (research Q4 with the new strip): share of zh/ja and ja/zh rank-1
--    anchors whose stripped key contains the lemma while none of the 3 served foils
--    does. Measured 2026-11-19 (live, read-only): zh/ja 1 of 3,623 (0.03%); ja/zh 50 of
--    3,175 (1.57%) with the one-pass strip, 48 (1.51%) with the two-pass strip.
--    Those anchors are not meaning-ready (excluded_rule5_n), so 0 are served.
SELECT p.word_language_id AS l, p.definition_language_id AS d, count(*) AS anchors,
       count(*) FILTER (WHERE m.status = 'rule5') AS residual,
       round(100.0 * count(*) FILTER (WHERE m.status = 'rule5') / count(*), 2) AS residual_pct
  FROM calibration_anchor_pool p
  JOIN dim_word_senses s ON s.id = p.sense_id AND s.sense_rank = 1
 CROSS JOIN LATERAL calibration_placement_meaning_parts(p.sense_id, p.word_language_id,
                                                        p.definition_language_id, p.lemma, s.definition) m
 WHERE p.has_embedding AND (p.word_language_id, p.definition_language_id) IN ((1, 3), (3, 1))
   AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = p.sense_id)
 GROUP BY 1, 2 ORDER BY 1, 2;

-- 7. Placement data health: at most one unanswered row per open placement; none in a
--    closed one; every scored reading row points at a right meaning row
SELECT 'open placement with > 1 pending row' AS check_name, session_id::text AS object
  FROM calibration_responses r JOIN calibration_sessions s ON s.id = r.session_id
 WHERE s.mode = 'placement' AND s.ended_at IS NULL AND r.answered_at IS NULL
 GROUP BY session_id HAVING count(*) > 1
UNION ALL
SELECT 'closed placement with a pending row', r.session_id::text
  FROM calibration_responses r JOIN calibration_sessions s ON s.id = r.session_id
 WHERE s.mode = 'placement' AND s.ended_at IS NOT NULL AND r.answered_at IS NULL
UNION ALL
SELECT 'scored reading row without a right meaning', r.id::text
  FROM calibration_responses r
  LEFT JOIN calibration_responses m ON m.id = r.pair_response_id
 WHERE r.item_kind = 'reading' AND r.probe_kind IS NULL AND (m.id IS NULL OR m.is_correct IS NOT TRUE);

-- 8. knowledge_calibration_inputs on the report fixture learner (report tech §2.6):
--    D = 2, bands [[26,16,7],[23,16,5],[26,14,9],[24,12,9],[25,9,13],[25,8,15],[23,0,21]],
--    pairs and gap null while that learner has no placement (verified 2026-11-19 on live
--    with the equivalent read-only SELECT)
SELECT knowledge_calibration_inputs(u.user_id, 3::smallint)
  FROM (SELECT DISTINCT user_id FROM calibration_sessions WHERE user_id::text LIKE 'de6fd05b%') u;
