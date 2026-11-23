-- =============================================================================
-- test_knowledge_calibration_inputs.sql  (TASK-1079)  ROLLBACK-ONLY fixture test
-- =============================================================================
-- Hand-built calibration rows (not through the placement RPCs) with known answers:
--   A. legacy only: bands equal the report §2.6 fixture of de6fd05b/ja (D = 2); the
--      latest answer per lemma wins; non-rank-1 rows and rows outside the window are
--      ignored (the latter count in alltime_n); pairs and gap are null; D override.
--   B. D* ties: most answers in the window, then the later last answer; with no answer
--      in the window, the same rule over all answers.
--   C. PSY M15: legacy answers in D = en plus an eligible placement in D = ja -> D = ja,
--      instrument meaning_bare_v1, placement rows only; ja pairs and gap by hand
--      (kana-only exempt words, IDK, wrong, a pending reading, probes excluded);
--      session mode returns the same; rated_known_in_frame by hand.
--   D. eligibility of the switch: abandoned without a result, or result.eligible =
--      false, does not switch; abandoned with a frozen result does.
--   E. zh pairs [n', pc, pkt, pf] and gap [n', f, idk, cm13, kt] by hand.
-- Needs migrations/calibration_placement.sql and knowledge_calibration_inputs.sql;
-- run on the local harness (UTF8):
--   psql -v ON_ERROR_STOP=1 -f tests/sql/test_knowledge_calibration_inputs.sql
-- =============================================================================

BEGIN;

CREATE FUNCTION pg_temp.kci_resp(p_session uuid, p_user uuid, p_sense integer, p_band integer,
                                 p_at timestamptz, p_correct boolean, p_skip boolean,
                                 p_kind text DEFAULT NULL, p_instrument text DEFAULT NULL,
                                 p_probe text DEFAULT NULL, p_pair bigint DEFAULT NULL,
                                 p_roles text[] DEFAULT NULL, p_role text DEFAULT NULL)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE v_id bigint; v_vocab integer; v_pos smallint; v_key smallint := 0;
BEGIN
  SELECT vocab_id INTO v_vocab FROM dim_word_senses WHERE id = p_sense;
  IF p_kind IS NOT NULL THEN
    v_key := CASE WHEN p_roles IS NOT NULL THEN array_position(p_roles, 'K') - 1 ELSE 0 END;
    v_pos := CASE WHEN p_skip OR p_at IS NULL THEN NULL
                  WHEN p_roles IS NOT NULL THEN array_position(p_roles, p_role) - 1
                  WHEN p_correct THEN v_key ELSE 1 END;
  END IF;
  INSERT INTO calibration_responses (session_id, user_id, anchor_sense_id, anchor_vocab_id, anchor_zipf, zipf_band,
                                     chosen_sense_id, is_correct, served_at, answered_at,
                                     item_kind, instrument, probe_kind, pair_response_id,
                                     option_sense_ids, key_position, option_roles, chosen_position)
  VALUES (p_session, p_user, p_sense, v_vocab, 4.0, p_band,
          CASE WHEN p_at IS NULL OR p_skip THEN NULL WHEN p_correct THEN p_sense ELSE p_sense + 0 END,
          CASE WHEN p_at IS NULL THEN NULL ELSE p_correct END,
          coalesce(p_at, now()), p_at,
          p_kind, p_instrument, p_probe, p_pair,
          CASE WHEN p_kind IS NOT NULL THEN ARRAY[p_sense, p_sense, p_sense, p_sense] END,
          CASE WHEN p_kind IS NOT NULL THEN v_key END, p_roles, v_pos)
  RETURNING id INTO v_id;
  RETURN v_id;
END $$;

-- rank-1 senses to draw from, per (L, D), kana-only flag
CREATE TEMP TABLE kci_s AS
SELECT s.id, s.vocab_id, s.word_language_id AS l, s.definition_language_id AS d,
       (v.lemma ~ '^[ぁ-ゟァ-ヿー・]+$') AS kana,
       row_number() OVER (PARTITION BY s.word_language_id, s.definition_language_id, (v.lemma ~ '^[ぁ-ゟァ-ヿー・]+$')
                          ORDER BY s.id) AS rn
  FROM dim_word_senses s JOIN dim_vocabulary v ON v.id = s.vocab_id
 WHERE s.sense_rank = 1 AND s.definition_level = 'standard';

-- -----------------------------------------------------------------------------
-- A. legacy only (report §2.6 fixture)
-- -----------------------------------------------------------------------------
DO $$
DECLARE
  u uuid := gen_random_uuid(); s2 uuid; s1 uuid;
  fx integer[] := ARRAY[[26,16,7],[23,16,5],[26,14,9],[24,12,9],[25,9,13],[25,8,15],[23,0,21]];
  b integer; i integer; k integer := 0; t timestamptz; j jsonb; v_old integer;
BEGIN
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode)
  VALUES (u, 3, 2, 'definition') RETURNING id INTO s2;
  FOR b IN 1..7 LOOP
    FOR i IN 1..fx[b][1] LOOP
      k := k + 1;
      t := now() - interval '60 days' + k * interval '5 minutes';
      PERFORM pg_temp.kci_resp(s2, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 2 AND NOT kana AND rn = k), b, t,
                               i > fx[b][2] AND i <= fx[b][2] + fx[b][3],  -- correct
                               i <= fx[b][2]);                               -- skip
    END LOOP;
  END LOOP;
  -- an older, superseded answer to lemma 1 (latest: a skip in band 1): ignored
  PERFORM pg_temp.kci_resp(s2, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 2 AND NOT kana AND rn = 1), 1,
                           now() - interval '90 days', true, false);
  -- a non-rank-1 anchor: ignored
  SELECT s.id INTO v_old FROM dim_word_senses s WHERE s.word_language_id = 3 AND s.definition_language_id = 2
     AND s.sense_rank = 2 LIMIT 1;
  IF v_old IS NOT NULL THEN
    PERFORM pg_temp.kci_resp(s2, u, v_old, 4, now() - interval '10 days', true, false);
  END IF;
  -- an answer outside the window (200 days): only in alltime_n (band 3)
  PERFORM pg_temp.kci_resp(s2, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 2 AND NOT kana AND rn = 500), 3,
                           now() - interval '200 days', true, false);
  -- an unanswered prefetch row: ignored
  PERFORM pg_temp.kci_resp(s2, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 2 AND NOT kana AND rn = 501), 2, NULL, NULL, NULL);
  -- 10 answers in D = 1 inside the window: fewer, so D* = 2
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode)
  VALUES (u, 3, 1, 'definition') RETURNING id INTO s1;
  FOR i IN 1..10 LOOP
    PERFORM pg_temp.kci_resp(s1, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 1 AND NOT kana AND rn = i), 7,
                             now() - interval '1 day', i <= 6, i > 8);
  END LOOP;

  j := knowledge_calibration_inputs(u, 3::smallint);
  IF j->'bands' <> '[[26,16,7],[23,16,5],[26,14,9],[24,12,9],[25,9,13],[25,8,15],[23,0,21]]'::jsonb THEN
    RAISE EXCEPTION 'A: bands % differ from the report fixture', j->'bands';
  END IF;
  IF (j->>'definition_language_id')::int <> 2 OR j->'instrument' <> 'null'::jsonb
     OR j->'pairs' <> 'null'::jsonb OR j->'gap' <> 'null'::jsonb
     OR j->'alltime_n' <> '[26,23,27,24,25,25,23]'::jsonb
     OR (j->>'placement_eligible')::boolean OR j->'stop_reasons' <> '[]'::jsonb
     OR (j->>'rated_known_in_frame')::int <> 0 THEN
    RAISE EXCEPTION 'A: header %', j - 'bands';
  END IF;
  -- the window sample spans now - 60 days + 5 min ... + 172 x 5 min (the 90-day superseded answer is not in it)
  IF (j->>'first_at')::timestamptz <> now() - interval '60 days' + interval '5 minutes'
     OR (j->>'last_at')::timestamptz <> now() - interval '60 days' + 172 * interval '5 minutes' THEN
    RAISE EXCEPTION 'A: dates %, %', j->>'first_at', j->>'last_at';
  END IF;
  j := knowledge_calibration_inputs(u, 3::smallint, now(), 180, 1::smallint);
  IF (j->>'definition_language_id')::int <> 1 OR j->'bands'->6 <> '[10, 2, 6]'::jsonb THEN
    RAISE EXCEPTION 'A: D override %', j;
  END IF;
  -- as_of 100 days ago: only the 200-day answer (band 3) is <= as_of, and it is inside
  -- that as_of's window (as_of - 180 days = 280 days ago)
  j := knowledge_calibration_inputs(u, 3::smallint, now() - interval '100 days');
  IF j->'bands' <> '[[0,0,0],[0,0,0],[1,0,1],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]'::jsonb THEN
    RAISE EXCEPTION 'A: as_of %', j->'bands';
  END IF;
  RAISE NOTICE 'PASS A legacy fixture: %', j->'bands';
END $$;

-- -----------------------------------------------------------------------------
-- B. D* ties
-- -----------------------------------------------------------------------------
DO $$
DECLARE u uuid := gen_random_uuid(); sa uuid; sb uuid; i integer; j jsonb;
BEGIN
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode) VALUES (u, 3, 2, 'definition') RETURNING id INTO sa;
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode) VALUES (u, 3, 3, 'definition') RETURNING id INTO sb;
  FOR i IN 1..5 LOOP
    PERFORM pg_temp.kci_resp(sa, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 2 AND NOT kana AND rn = i), 5, now() - interval '20 days', true, false);
    PERFORM pg_temp.kci_resp(sb, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 3 AND NOT kana AND rn = i), 5, now() - interval '10 days', true, false);
  END LOOP;
  j := knowledge_calibration_inputs(u, 3::smallint);
  IF (j->>'definition_language_id')::int <> 3 THEN RAISE EXCEPTION 'B: tie -> later last answer: %', j->>'definition_language_id'; END IF;
  -- move everything out of the window: D = 2 now has more answers overall
  PERFORM pg_temp.kci_resp(sa, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 2 AND NOT kana AND rn = 6), 5, now() - interval '20 days', true, false);
  UPDATE calibration_responses SET answered_at = answered_at - interval '400 days' WHERE user_id = u;
  j := knowledge_calibration_inputs(u, 3::smallint);
  IF (j->>'definition_language_id')::int <> 2 OR j->'bands'->4 <> '[0,0,0]'::jsonb OR (j->'alltime_n'->>4)::int <> 6
     OR j->>'last_at' IS NULL THEN
    RAISE EXCEPTION 'B: no answer in the window -> D* over all answers (E1c): %', j;
  END IF;
  RAISE NOTICE 'PASS B D* rule';
END $$;

-- -----------------------------------------------------------------------------
-- C. PSY M15: legacy D = en + eligible placement D = ja -> placement rows only
-- -----------------------------------------------------------------------------
DO $$
DECLARE
  u uuid := gen_random_uuid(); sl uuid; sp uuid; j jsonb; js jsonb; m bigint; i integer;
  -- frame (3,3) lemmas: kanji words and kana-only words
  kj integer[]; kn integer[]; t timestamptz := now() - interval '5 days';
BEGIN
  SELECT array_agg(p.sense_id ORDER BY p.sense_id) INTO kj FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id
   WHERE p.word_language_id = 3 AND p.definition_language_id = 3 AND s.sense_rank = 1 AND p.has_embedding
     AND p.lemma !~ '^[ぁ-ゟァ-ヿー・]+$';
  SELECT array_agg(s.id ORDER BY s.id) INTO kn FROM kci_s s WHERE s.l = 3 AND s.d = 3 AND s.kana;
  -- 40 legacy answers in D = 2
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode) VALUES (u, 3, 2, 'definition') RETURNING id INTO sl;
  FOR i IN 1..40 LOOP
    PERFORM pg_temp.kci_resp(sl, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 2 AND NOT kana AND rn = 600 + i), 1 + i % 7,
                             now() - interval '30 days', true, false);
  END LOOP;
  -- the placement (D = 3), stopped by the cap
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode, started_at, ended_at, stop_reason)
  VALUES (u, 3, 3, 'placement', t, t + interval '7 minutes', 'cap') RETURNING id INTO sp;
  -- band 7: w1 m+ r+ | w2 m+ r- | w3 m+ r? | w4 m- | w5 m? (+ forced_guess) | w6 m+ reading pending
  m := pg_temp.kci_resp(sp, u, kj[1], 7, t, true, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, kj[1], 7, t, true, false, 'reading', 'reading_v1', NULL, m);
  m := pg_temp.kci_resp(sp, u, kj[2], 7, t, true, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, kj[2], 7, t, false, false, 'reading', 'reading_v1', NULL, m);
  m := pg_temp.kci_resp(sp, u, kj[3], 7, t, true, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, kj[3], 7, t, false, true, 'reading', 'reading_v1', NULL, m);
  m := pg_temp.kci_resp(sp, u, kj[4], 7, t, false, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, kj[4], 7, t, true, false, 'reading', 'reading_v1', 'reading_after_miss', m);
  m := pg_temp.kci_resp(sp, u, kj[5], 7, t, false, true, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, kj[5], 7, t, true, false, 'meaning', 'meaning_bare_v1', 'forced_guess', m);
  m := pg_temp.kci_resp(sp, u, kj[6], 7, t, true, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, kj[6], 7, NULL, NULL, NULL, 'reading', 'reading_v1', NULL, m);
  -- band 6: kana-only (exempt) k1 m+ | k2 m- | k3 m?
  PERFORM pg_temp.kci_resp(sp, u, kn[1], 6, t, true, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, kn[2], 6, t, false, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, kn[3], 6, t, false, true, 'meaning', 'meaning_bare_v1');
  -- a recheck probe: excluded everywhere
  PERFORM pg_temp.kci_resp(sp, u, kj[7], 5, t, true, false, 'reading', 'reading_v1', 'recheck');

  -- UVK: rated known in frame (3,3) = 1 (kj[1]); kj[2] p 0.5; kj[3] primary row p 0.6
  INSERT INTO user_vocabulary_knowledge (user_id, sense_id, language_id, p_known, word_test_correct, word_test_wrong, last_evidence_at)
  VALUES (u, kj[1], 3, 0.90, 2, 0, now() - interval '3 days'),
         (u, kj[2], 3, 0.50, 2, 0, now() - interval '3 days'),
         (u, kj[3], 3, 0.90, 2, 0, now() - interval '9 days'),
         (u, (SELECT s.id FROM dim_word_senses s WHERE s.vocab_id = (SELECT vocab_id FROM dim_word_senses WHERE id = kj[3])
                AND s.sense_rank = 1 AND s.id <> kj[3] LIMIT 1), 3, 0.60, 0, 0, now() - interval '1 day');

  j := knowledge_calibration_inputs(u, 3::smallint);
  IF (j->>'definition_language_id')::int <> 3 OR j->>'instrument' <> 'meaning_bare_v1' THEN
    RAISE EXCEPTION 'C: D/instrument rule: %', j;
  END IF;
  IF j->'bands' <> '[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[3,1,1],[6,1,4]]'::jsonb THEN
    RAISE EXCEPTION 'C: bands %', j->'bands';
  END IF;
  IF j->'pairs' <> '[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[3,1,1],[5,1,1]]'::jsonb THEN
    RAISE EXCEPTION 'C: pairs %', j->'pairs';
  END IF;
  IF j->'gap' <> '[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0],[3,0,0,0],[5,1,1,1]]'::jsonb THEN
    RAISE EXCEPTION 'C: gap %', j->'gap';
  END IF;
  IF NOT (j->>'placement_eligible')::boolean OR j->'stop_reasons' <> '["cap"]'::jsonb THEN
    RAISE EXCEPTION 'C: eligibility %', j;
  END IF;
  IF (j->>'rated_known_in_frame')::int <> 1 THEN RAISE EXCEPTION 'C: rated_known_in_frame %', j->>'rated_known_in_frame'; END IF;
  js := knowledge_calibration_inputs(u, 3::smallint, now(), 180, NULL, sp);
  IF js <> j THEN RAISE EXCEPTION 'C: session mode % differs from combined %', js, j; END IF;
  -- the legacy D can still be asked for explicitly: no placement in D = 2 -> legacy
  j := knowledge_calibration_inputs(u, 3::smallint, now(), 180, 2::smallint);
  IF j->'instrument' <> 'null'::jsonb OR (SELECT sum((e->>0)::int) FROM jsonb_array_elements(j->'bands') e) <> 40 THEN
    RAISE EXCEPTION 'C: D = 2 override %', j;
  END IF;
  RAISE NOTICE 'PASS C PSY M15 switch, ja pairs/gap, session mode, rated_known_in_frame';
END $$;

-- -----------------------------------------------------------------------------
-- D. which placements switch the report
-- -----------------------------------------------------------------------------
DO $$
DECLARE u uuid := gen_random_uuid(); sl uuid; sp uuid; j jsonb;
BEGIN
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode) VALUES (u, 3, 2, 'definition') RETURNING id INTO sl;
  PERFORM pg_temp.kci_resp(sl, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 2 AND NOT kana AND rn = 1), 5, now() - interval '3 days', true, false);
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode, ended_at, stop_reason)
  VALUES (u, 3, 3, 'placement', now() - interval '1 day', 'abandoned') RETURNING id INTO sp;
  PERFORM pg_temp.kci_resp(sp, u, (SELECT id FROM kci_s WHERE l = 3 AND d = 3 AND NOT kana AND rn = 1), 5, now() - interval '1 day',
                           true, false, 'meaning', 'meaning_bare_v1');
  j := knowledge_calibration_inputs(u, 3::smallint);
  IF (j->>'definition_language_id')::int <> 2 OR j->'instrument' <> 'null'::jsonb THEN
    RAISE EXCEPTION 'D: an abandoned placement without a result switched the report: %', j;
  END IF;
  UPDATE calibration_sessions SET result = '{"version": 1, "eligible": false}' WHERE id = sp;
  IF knowledge_calibration_inputs(u, 3::smallint)->'instrument' <> 'null'::jsonb THEN
    RAISE EXCEPTION 'D: result.eligible = false switched the report';
  END IF;
  UPDATE calibration_sessions SET result = '{"version": 1}' WHERE id = sp;
  j := knowledge_calibration_inputs(u, 3::smallint);
  IF (j->>'definition_language_id')::int <> 3 OR j->>'instrument' <> 'meaning_bare_v1'
     OR (j->>'placement_eligible')::boolean OR j->'stop_reasons' <> '["abandoned"]'::jsonb THEN
    RAISE EXCEPTION 'D: an abandoned placement with a frozen result must switch: %', j;
  END IF;
  -- a placement ended outside the window does not switch
  UPDATE calibration_sessions SET ended_at = now() - interval '181 days' WHERE id = sp;
  IF knowledge_calibration_inputs(u, 3::smallint)->'instrument' <> 'null'::jsonb THEN
    RAISE EXCEPTION 'D: a placement outside the window switched the report';
  END IF;
  -- no data at all
  j := knowledge_calibration_inputs(gen_random_uuid(), 1::smallint);
  IF j->'definition_language_id' <> 'null'::jsonb OR j->'bands' <> '[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]'::jsonb
     OR j->'rated_known_in_frame' <> 'null'::jsonb OR j->'first_at' <> 'null'::jsonb THEN
    RAISE EXCEPTION 'D: empty learner %', j;
  END IF;
  -- a foreign session id gives the empty shape
  IF knowledge_calibration_inputs(gen_random_uuid(), 3::smallint, now(), 180, NULL, sp)->'definition_language_id' <> 'null'::jsonb THEN
    RAISE EXCEPTION 'D: foreign session leaked';
  END IF;
  RAISE NOTICE 'PASS D switch eligibility, window, empty learner, foreign session';
END $$;

-- -----------------------------------------------------------------------------
-- E. zh pairs and gap by hand (band 5)
-- -----------------------------------------------------------------------------
DO $$
DECLARE u uuid := gen_random_uuid(); sp uuid; m bigint; j jsonb; t timestamptz := now() - interval '2 days';
        roles text[] := ARRAY['F', 'K', 'FT', 'KT']; z integer[];
BEGIN
  SELECT array_agg(id ORDER BY id) INTO z FROM kci_s WHERE l = 1 AND d = 2 AND rn <= 7;
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode, started_at, ended_at, stop_reason)
  VALUES (u, 1, 2, 'placement', t, t + interval '6 minutes', 'precision') RETURNING id INTO sp;
  m := pg_temp.kci_resp(sp, u, z[1], 5, t, true, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, z[1], 5, t, true, false, 'reading', 'reading_tone_v1', NULL, m, roles, 'K');
  m := pg_temp.kci_resp(sp, u, z[2], 5, t, true, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, z[2], 5, t, false, false, 'reading', 'reading_tone_v1', NULL, m, roles, 'KT');
  m := pg_temp.kci_resp(sp, u, z[3], 5, t, true, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, z[3], 5, t, false, false, 'reading', 'reading_tone_v1', NULL, m, roles, 'F');
  m := pg_temp.kci_resp(sp, u, z[4], 5, t, true, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, z[4], 5, t, false, false, 'reading', 'reading_tone_v1', NULL, m, roles, 'FT');
  m := pg_temp.kci_resp(sp, u, z[5], 5, t, true, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, z[5], 5, t, false, true, 'reading', 'reading_tone_v1', NULL, m, roles, NULL);
  PERFORM pg_temp.kci_resp(sp, u, z[6], 5, t, false, false, 'meaning', 'meaning_bare_v1');
  PERFORM pg_temp.kci_resp(sp, u, z[7], 5, t, false, true, 'meaning', 'meaning_bare_v1');
  j := knowledge_calibration_inputs(u, 1::smallint);
  IF j->'bands'->4 <> '[7, 1, 5]'::jsonb OR j->'pairs'->4 <> '[7, 1, 1, 2]'::jsonb OR j->'gap'->4 <> '[7, 2, 1, 1, 1]'::jsonb
     OR j->'pairs'->0 <> '[0, 0, 0, 0]'::jsonb OR NOT (j->>'placement_eligible')::boolean THEN
    RAISE EXCEPTION 'E: zh % / % / %', j->'bands'->4, j->'pairs'->4, j->'gap'->4;
  END IF;
  RAISE NOTICE 'PASS E zh pairs [7,1,1,2] gap [7,2,1,1,1]';
END $$;

ROLLBACK;
