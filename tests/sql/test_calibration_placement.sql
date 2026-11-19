-- =============================================================================
-- test_calibration_placement.sql  (TASK-1077, TASK-1079)  ROLLBACK-ONLY behaviour test
-- =============================================================================
-- Scripted placement sessions per language (zh 1:2, ja 3:2, en 2:2, plus zh 1:3 and
-- ja 3:1 for rule 5) against the placement functions, with every tech §19 SQL check.
-- Assertions RAISE EXCEPTION; a clean run prints "PASS ..." notices, then ROLLBACK.
--
-- Local harness (sample pool, UTF8 cluster):
--   PG_EXTRA="tests/sql/fixtures/placement_harness_fks.sql
--             tests/sql/fixtures/calibration_zh_tone_variants_stub.sql   (or migrations/calibration_zh_tones.sql
--                                                                         + SELECT calibration_refresh_zh_tone_inventory())
--             migrations/calibration_placement.sql migrations/calibration_placement_rpcs.sql
--             migrations/knowledge_calibration_inputs.sql"
--   pg.sh <name> <port> reset
--   psql -v ON_ERROR_STOP=1 -f tests/sql/test_calibration_placement.sql
-- tests/test_calibration_placement_sql.py runs it when PLACEMENT_TEST_DSN is set.
-- The database must be UTF8 (CJK regex classes); the test refuses otherwise.
--
-- Checked (tech §19):
--   items never carry a key, roles, sense ids or (meaning items) the reading;
--   only placement-ready, rank-1 frame lemmas; none answered in 180 days; none twice;
--   reading options share the key's display syllable / mora count; ja foils match the
--   visible kana; zh items are exactly K, KT, F, FT with KT, FT tone variants of K, F
--   and F not a tone variant of K; forced_guess re-orders the same options;
--   tallies equal an independent hand count after every answer (zh [n',pc,pkt,pf],
--   ja [n',pc,prw]); probes <= 4 per session, <= 2 per kind, <= 1 per word;
--   double answers, foreign sessions, foreign responses, bad positions are rejected;
--   close leaves no unanswered row and is idempotent; close_stale; resend; nearest-
--   band fallback and exhaustion; recheck probes with disjoint foils;
--   knowledge_calibration_inputs on the same sessions (if installed).
-- =============================================================================

BEGIN;

DO $$
BEGIN
  IF current_setting('server_encoding') <> 'UTF8' THEN
    RAISE EXCEPTION 'test needs a UTF8 database (server_encoding = %)', current_setting('server_encoding');
  END IF;
END $$;

SELECT setseed(0.4242);

-- -----------------------------------------------------------------------------
-- Invariants of one served item (payload + stored row).
-- -----------------------------------------------------------------------------
CREATE FUNCTION pg_temp.plc_check_item(p_user uuid, p_sid uuid, p_item jsonb)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
  r      calibration_responses%ROWTYPE;
  s      calibration_sessions%ROWTYPE;
  root   calibration_responses%ROWTYPE;
  texts  text[];
  k      text;
  v_lemma text;
  v_read text;
  v_bad  text;
  n      integer;
  ks     text[];
BEGIN
  SELECT array_agg(x ORDER BY x) INTO ks FROM jsonb_object_keys(p_item) x;
  IF NOT ks <@ ARRAY['band','idk_allowed','kind','lemma','options','probe_kind','resent','response_id','vocab_id'] THEN
    RAISE EXCEPTION 'payload has unexpected keys: %', ks;
  END IF;
  IF p_item::text ~* '(key_position|option_sense_ids|option_roles|correct_position|"roles"|"pronunciation"\s*:|"reading"\s*:)' THEN
    RAISE EXCEPTION 'payload leaks a key or a reading: %', p_item;
  END IF;
  SELECT * INTO r FROM calibration_responses WHERE id = (p_item->>'response_id')::bigint;
  SELECT * INTO s FROM calibration_sessions WHERE id = r.session_id;
  IF r.session_id <> p_sid OR r.answered_at IS NOT NULL THEN RAISE EXCEPTION 'served row wrong: %', r.id; END IF;
  IF (p_item->>'vocab_id')::int <> r.anchor_vocab_id OR (p_item->>'band')::int <> r.zipf_band
     OR p_item->>'kind' <> r.item_kind OR (p_item->>'probe_kind') IS DISTINCT FROM r.probe_kind THEN
    RAISE EXCEPTION 'payload/row mismatch %', p_item;
  END IF;
  SELECT array_agg(x ORDER BY o) INTO texts FROM jsonb_array_elements_text(p_item->'options') WITH ORDINALITY e(x, o);
  n := cardinality(texts);
  IF n <> (CASE WHEN r.item_kind = 'sound_pair' THEN 2 ELSE 4 END)
     OR n <> cardinality(r.option_sense_ids) OR (SELECT count(DISTINCT x) FROM unnest(texts) x) <> n THEN
    RAISE EXCEPTION 'bad option set % for row %', texts, r.id;
  END IF;
  IF r.key_position IS NULL OR r.key_position < 0 OR r.key_position >= n THEN RAISE EXCEPTION 'bad key_position'; END IF;
  IF texts IS DISTINCT FROM calibration_placement_option_texts(r.id) THEN
    RAISE EXCEPTION 'payload options differ from the stored rebuild: % vs %', texts, calibration_placement_option_texts(r.id);
  END IF;
  IF (p_item->>'idk_allowed')::boolean IS DISTINCT FROM (r.probe_kind IS DISTINCT FROM 'forced_guess') THEN
    RAISE EXCEPTION 'idk_allowed wrong';
  END IF;
  SELECT lemma INTO v_lemma FROM dim_vocabulary WHERE id = r.anchor_vocab_id;
  v_read := calibration_placement_reveal_reading(r.anchor_vocab_id, s.word_language_id);
  k := texts[r.key_position + 1];

  IF r.item_kind = 'meaning' THEN
    -- rank-1 frame row of (L, D), placement-ready
    IF NOT EXISTS (SELECT 1 FROM calibration_anchor_pool p JOIN dim_word_senses ws ON ws.id = p.sense_id
                    WHERE p.sense_id = r.anchor_sense_id AND p.word_language_id = s.word_language_id
                      AND p.definition_language_id = s.definition_language_id AND p.has_embedding
                      AND ws.sense_rank = 1)
       OR EXISTS (SELECT 1 FROM calibration_anchor_blocklist b WHERE b.sense_id = r.anchor_sense_id) THEN
      RAISE EXCEPTION 'meaning anchor % not a rank-1 frame row', r.anchor_sense_id;
    END IF;
    IF r.option_sense_ids[r.key_position + 1] <> r.anchor_sense_id THEN RAISE EXCEPTION 'key sense mismatch'; END IF;
    IF (calibration_placement_meaning_parts(r.anchor_sense_id, s.word_language_id, s.definition_language_id,
                                            v_lemma, (SELECT definition FROM dim_word_senses WHERE id = r.anchor_sense_id))).status <> 'ok'
       OR (NOT calibration_placement_reading_exempt(v_lemma, s.word_language_id)
           AND NOT calibration_placement_reading_ready(r.anchor_vocab_id, s.word_language_id, v_lemma)) THEN
      RAISE EXCEPTION 'served a non-ready lemma %', v_lemma;
    END IF;
    IF NOT calibration_placement_reading_exempt(v_lemma, s.word_language_id) AND v_read = ANY (texts) THEN
      RAISE EXCEPTION 'meaning item shows the reading %', v_read;
    END IF;
    IF s.word_language_id IN (1, 3) AND s.definition_language_id IN (1, 3) AND s.word_language_id <> s.definition_language_id
       AND EXISTS (SELECT 1 FROM unnest(texts) t WHERE t ~ '^\s*[^；;—]{1,12}\s*(——|—)') THEN
      RAISE EXCEPTION 'cross-CJK option kept its equivalent-word prefix: %', texts;
    END IF;
    IF r.probe_kind IS NULL THEN
      IF r.instrument <> 'meaning_bare_v1' OR r.pair_response_id IS NOT NULL THEN RAISE EXCEPTION 'meaning row columns'; END IF;
      IF EXISTS (SELECT 1 FROM calibration_responses q WHERE q.user_id = p_user AND q.anchor_vocab_id = r.anchor_vocab_id
                    AND q.session_id <> p_sid AND q.answered_at > s.started_at - interval '180 days') THEN
        RAISE EXCEPTION 'served lemma % answered within 180 days', v_lemma;
      END IF;
      IF EXISTS (SELECT 1 FROM calibration_responses q WHERE q.session_id = p_sid AND q.anchor_vocab_id = r.anchor_vocab_id
                    AND q.id <> r.id) THEN
        RAISE EXCEPTION 'lemma % served twice in a session', v_lemma;
      END IF;
    ELSE  -- forced_guess
      SELECT * INTO root FROM calibration_responses WHERE id = r.pair_response_id;
      IF r.probe_kind <> 'forced_guess' OR root.chosen_position IS NOT NULL
         OR (SELECT array_agg(x ORDER BY x) FROM unnest(r.option_sense_ids) x)
            IS DISTINCT FROM (SELECT array_agg(x ORDER BY x) FROM unnest(root.option_sense_ids) x)
         OR r.option_sense_ids = root.option_sense_ids THEN
        RAISE EXCEPTION 'forced_guess must re-order the IDK item''s options';
      END IF;
    END IF;
  ELSIF r.item_kind = 'reading' THEN
    IF k IS DISTINCT FROM (SELECT reading FROM calibration_placement_reading_key(r.anchor_vocab_id, s.word_language_id)) THEN
      RAISE EXCEPTION 'reading key % is not the native rank-1 reading', k;
    END IF;
    IF EXISTS (SELECT 1 FROM unnest(texts) t
                WHERE calibration_placement_units(t, s.word_language_id) <> calibration_placement_units(k, s.word_language_id)) THEN
      RAISE EXCEPTION 'reading options differ in syllable/mora count: %', texts;
    END IF;
    IF r.probe_kind IS NULL AND (r.pair_response_id IS NULL OR NOT EXISTS (
          SELECT 1 FROM calibration_responses m WHERE m.id = r.pair_response_id AND m.is_correct AND m.item_kind = 'meaning')) THEN
      RAISE EXCEPTION 'scored reading item without a right meaning';
    END IF;
    IF s.word_language_id = 3 THEN
      IF r.instrument <> 'reading_v1' OR r.option_roles IS NOT NULL THEN RAISE EXCEPTION 'ja reading columns'; END IF;
      SELECT string_agg(t, ',') INTO v_bad FROM unnest(texts) t WHERE t !~ calibration_placement_kana_pattern(v_lemma);
      IF v_bad IS NOT NULL THEN RAISE EXCEPTION 'kana-inconsistent foil(s) % for %', v_bad, v_lemma; END IF;
    ELSE
      IF r.instrument <> 'reading_tone_v1' OR r.option_texts IS NULL
         OR (SELECT array_agg(x ORDER BY x) FROM unnest(r.option_roles) x) <> ARRAY['F','FT','K','KT'] THEN
        RAISE EXCEPTION 'zh roles not exactly K, KT, F, FT: %', r.option_roles;
      END IF;
      IF r.option_roles[r.key_position + 1] <> 'K' THEN RAISE EXCEPTION 'key role is not K'; END IF;
      DECLARE
        tk text  := texts[array_position(r.option_roles, 'K')];
        tkt text := texts[array_position(r.option_roles, 'KT')];
        tf text  := texts[array_position(r.option_roles, 'F')];
        tft text := texts[array_position(r.option_roles, 'FT')];
        vf integer := (SELECT vocab_id FROM dim_word_senses WHERE id = r.option_sense_ids[array_position(r.option_roles, 'F')]);
      BEGIN
        IF r.option_sense_ids[array_position(r.option_roles, 'KT')] IS NOT NULL
           OR r.option_sense_ids[array_position(r.option_roles, 'FT')] IS NOT NULL THEN
          RAISE EXCEPTION 'generated options must have no sense id';
        END IF;
        IF NOT tkt = ANY (calibration_zh_tone_variants(tk, r.anchor_vocab_id)) THEN RAISE EXCEPTION 'KT % not a variant of K %', tkt, tk; END IF;
        IF NOT tft = ANY (calibration_zh_tone_variants(tf, vf)) THEN RAISE EXCEPTION 'FT % not a variant of F %', tft, tf; END IF;
        IF calibration_placement_toneless(tf) = calibration_placement_toneless(tk) THEN RAISE EXCEPTION 'F % is a tone variant of K %', tf, tk; END IF;
        IF tf = ANY (calibration_placement_own_readings(r.anchor_vocab_id, 1::smallint))
           OR tft = ANY (calibration_placement_own_readings(r.anchor_vocab_id, 1::smallint)) THEN
          RAISE EXCEPTION 'a wrong option is a reading of the prompt lemma';
        END IF;
      END;
    END IF;
  ELSE  -- sound_pair
    IF s.word_language_id <> 3 OR r.probe_kind <> 'sound_pair'
       OR calibration_placement_mora_skeleton(texts[1]) <> calibration_placement_mora_skeleton(texts[2]) THEN
      RAISE EXCEPTION 'bad sound_pair %', texts;
    END IF;
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- A scripted learner: answers by a band-dependent knowledge rule, keeps its own
-- tallies, checks every item and every returned tally, and closes the session.
-- p_bands: fixed next-band schedule (cycled); p_cap: scored-item cap; p_probe: force
-- u_probe (NULL = random draw).
-- -----------------------------------------------------------------------------
CREATE FUNCTION pg_temp.plc_run(p_user uuid, p_l smallint, p_d smallint, p_cap integer,
                                p_bands smallint[], p_probe double precision DEFAULT NULL,
                                p_max_answers integer DEFAULT 400)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
  v_sid    uuid;
  v_item   jsonb;
  v_res    jsonb;
  r        calibration_responses%ROWTYPE;
  v_lemma  text;
  v_ex     boolean;
  v_pos    smallint;
  v_role   text;
  v_know   double precision;
  v_next   smallint;
  v_i      integer := 0;
  v_k      integer := 0;
  v_scored integer := 0;
  v_stop   text := NULL;
  hm       integer[] := array_fill(0, ARRAY[7, 3]);
  hp       integer[] := array_fill(0, ARRAY[7, 4]);
  b        integer;
  v_exp_m  jsonb;
  v_exp_mr jsonb;
  v_prev_root bigint;
  v_close  jsonb;
  v_close2 jsonb;
  v_reveals integer := 0;
  v_words  integer := 0;
BEGIN
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode)
  VALUES (p_user, p_l, p_d, 'placement') RETURNING id INTO v_sid;
  v_item := calibration_placement_next_item(p_user, v_sid, p_bands[1]);

  LOOP
    IF v_item IS NULL OR jsonb_typeof(v_item) = 'null' THEN v_stop := coalesce(v_stop, 'cap'); EXIT; END IF;
    IF v_item ? 'exhausted' THEN v_stop := 'exhausted'; EXIT; END IF;
    v_i := v_i + 1;
    EXIT WHEN v_i > p_max_answers;
    PERFORM pg_temp.plc_check_item(p_user, v_sid, v_item);
    SELECT * INTO r FROM calibration_responses WHERE id = (v_item->>'response_id')::bigint;
    SELECT lemma INTO v_lemma FROM dim_vocabulary WHERE id = r.anchor_vocab_id;
    v_ex := calibration_placement_reading_exempt(v_lemma, p_l);
    v_know := 0.10 + 0.11 * r.zipf_band;            -- band 7: 0.87, band 1: 0.21

    -- choose an answer (and remember its role for the hand count)
    v_role := NULL;
    IF r.item_kind = 'meaning' THEN
      IF random() < v_know THEN v_pos := r.key_position;
      ELSIF random() < 0.4 AND r.probe_kind IS NULL THEN v_pos := NULL;
      ELSE v_pos := floor(random() * 4)::smallint; END IF;
    ELSIF r.item_kind = 'reading' AND p_l = 1 THEN
      v_role := CASE WHEN random() < 0.55 THEN 'K' WHEN random() < 0.5 THEN 'KT'
                     WHEN random() < 0.5 THEN 'IDK' ELSE (ARRAY['K','KT','F','FT'])[1 + floor(random() * 4)::int] END;
      v_pos := CASE WHEN v_role = 'IDK' THEN NULL ELSE (array_position(r.option_roles, v_role) - 1)::smallint END;
    ELSIF r.item_kind = 'reading' THEN
      v_pos := CASE WHEN random() < 0.6 THEN r.key_position WHEN random() < 0.5 THEN NULL
                    ELSE ((r.key_position + 1 + floor(random() * 3)::int) % 4)::smallint END;
    ELSE
      v_pos := floor(random() * 2)::smallint;
    END IF;

    -- next band: only if this answer may start a new word under the cap
    IF r.probe_kind IS NULL AND v_scored + 1 >= p_cap THEN v_next := NULL;
    ELSIF r.probe_kind IS NOT NULL AND v_scored >= p_cap THEN v_next := NULL;
    ELSE v_next := p_bands[1 + (v_k % cardinality(p_bands))]; END IF;

    -- a double answer, an out-of-range position and a foreign response are rejected
    IF v_i = 3 THEN
      BEGIN
        PERFORM calibration_placement_answer(p_user, v_sid, r.id, 7::smallint, 1000, v_next, '{}'::jsonb);
        RAISE EXCEPTION 'out-of-range position accepted';
      EXCEPTION WHEN SQLSTATE '22023' THEN NULL; END;
    END IF;

    v_res := calibration_placement_answer(
               p_user, v_sid, r.id, v_pos, 2500 + floor(random() * 5000)::int, v_next,
               jsonb_build_object('u_probe', coalesce(p_probe, random()), 'u_seed', random()));

    IF v_i = 3 THEN
      BEGIN
        PERFORM calibration_placement_answer(p_user, v_sid, r.id, 0::smallint, 1000, v_next, '{}'::jsonb);
        RAISE EXCEPTION 'double answer accepted';
      EXCEPTION WHEN SQLSTATE '22023' THEN NULL; END;
    END IF;

    -- grading
    IF (v_res->'answer'->>'is_correct')::boolean IS DISTINCT FROM (v_pos IS NOT NULL AND v_pos = r.key_position)
       OR (v_res->'answer'->>'skipped')::boolean IS DISTINCT FROM (v_pos IS NULL)
       OR (v_res->'answer'->>'role') IS DISTINCT FROM (CASE WHEN v_pos IS NOT NULL THEN r.option_roles[v_pos + 1] END) THEN
      RAISE EXCEPTION 'grading wrong: % for pos % key %', v_res->'answer', v_pos, r.key_position;
    END IF;
    IF (SELECT chosen_position FROM calibration_responses WHERE id = r.id) IS DISTINCT FROM v_pos
       OR (SELECT chosen_sense_id FROM calibration_responses WHERE id = r.id) IS DISTINCT FROM
          (CASE WHEN v_pos IS NOT NULL THEN r.option_sense_ids[v_pos + 1] END) THEN
      RAISE EXCEPTION 'stored answer wrong';
    END IF;

    -- independent hand tally (scored items only)
    IF r.probe_kind IS NULL THEN
      v_scored := v_scored + 1;
      b := r.zipf_band;
      IF r.item_kind = 'meaning' THEN
        v_k := v_k + 1;
        v_words := v_words + 1;
        hm[b][1] := hm[b][1] + 1;
        IF v_pos = r.key_position THEN hm[b][2] := hm[b][2] + 1;
        ELSIF v_pos IS NOT NULL THEN hm[b][3] := hm[b][3] + 1; END IF;
        -- pair sample entries that need no reading
        IF v_ex THEN
          hp[b][1] := hp[b][1] + 1;
          IF v_pos = r.key_position THEN hp[b][2] := hp[b][2] + 1;
          ELSIF v_pos IS NOT NULL THEN hp[b][3] := hp[b][3] + 1; END IF;
        ELSIF v_pos IS DISTINCT FROM r.key_position THEN
          hp[b][1] := hp[b][1] + 1;
        END IF;
      ELSE  -- scored reading (meaning was right)
        hp[b][1] := hp[b][1] + 1;
        IF p_l = 1 THEN
          IF v_role = 'K' THEN hp[b][2] := hp[b][2] + 1;
          ELSIF v_role = 'KT' THEN hp[b][3] := hp[b][3] + 1;
          ELSIF v_role IN ('F', 'FT') THEN hp[b][4] := hp[b][4] + 1; END IF;
        ELSE
          IF v_pos = r.key_position THEN hp[b][2] := hp[b][2] + 1;
          ELSIF v_pos IS NOT NULL THEN hp[b][3] := hp[b][3] + 1; END IF;
        END IF;
      END IF;
    END IF;

    SELECT jsonb_agg(jsonb_build_array(hm[g][1], hm[g][2], hm[g][3]) ORDER BY g) INTO v_exp_m FROM generate_series(1, 7) g;
    SELECT CASE WHEN p_l = 1 THEN jsonb_agg(jsonb_build_array(hp[g][1], hp[g][2], hp[g][3], hp[g][4]) ORDER BY g)
                WHEN p_l = 3 THEN jsonb_agg(jsonb_build_array(hp[g][1], hp[g][2], hp[g][3]) ORDER BY g) END
      INTO v_exp_mr FROM generate_series(1, 7) g;
    IF v_res->'tallies'->'m' <> v_exp_m OR (v_res->'tallies'->'mr') IS DISTINCT FROM coalesce(v_exp_mr, 'null'::jsonb)
       OR (v_res->'tallies'->>'scored')::int <> v_scored THEN
      RAISE EXCEPTION 'tallies differ from the hand count after answer %: got m=% mr=% scored=%, want m=% mr=% scored=%',
        v_i, v_res->'tallies'->'m', v_res->'tallies'->'mr', v_res->'tallies'->>'scored', v_exp_m, v_exp_mr, v_scored;
    END IF;

    -- a reveal exactly when the word is complete; never a key before
    IF jsonb_typeof(v_res->'reveal') = 'object' THEN
      v_reveals := v_reveals + 1;
      IF jsonb_array_length(v_res->'reveal'->'parts') <>
         (SELECT count(*) FROM calibration_responses q WHERE q.session_id = v_sid
             AND (q.id = coalesce(r.pair_response_id, r.id) OR q.pair_response_id = coalesce(r.pair_response_id, r.id))) THEN
        RAISE EXCEPTION 'reveal parts do not cover the word';
      END IF;
      IF jsonb_typeof(v_res->'next_item') = 'object' AND (v_res->'next_item'->>'vocab_id')::int = r.anchor_vocab_id THEN
        RAISE EXCEPTION 'reveal with a follow-up item of the same word';
      END IF;
    ELSIF jsonb_typeof(v_res->'next_item') <> 'object'
          OR (v_res->'next_item'->>'vocab_id')::int <> r.anchor_vocab_id THEN
      RAISE EXCEPTION 'no reveal, yet the next item is not the same word';
    END IF;

    IF (v_res->>'exhausted')::boolean THEN v_stop := 'exhausted'; END IF;
    v_item := v_res->'next_item';
  END LOOP;

  -- probes: <= 4 per session, <= 2 per kind, <= 1 per word
  IF (SELECT count(*) FROM calibration_responses WHERE session_id = v_sid AND probe_kind IS NOT NULL) > 4
     OR EXISTS (SELECT 1 FROM calibration_responses WHERE session_id = v_sid AND probe_kind IS NOT NULL
                 GROUP BY probe_kind HAVING count(*) > 2)
     OR EXISTS (SELECT 1 FROM calibration_responses WHERE session_id = v_sid AND probe_kind IS NOT NULL
                   AND pair_response_id IS NOT NULL GROUP BY pair_response_id HAVING count(*) > 1) THEN
    RAISE EXCEPTION 'probe budget violated';
  END IF;
  IF v_scored > p_cap + 1 THEN RAISE EXCEPTION 'scored % above cap %', v_scored, p_cap; END IF;

  v_close := calibration_placement_close(p_user, v_sid, v_stop);
  IF EXISTS (SELECT 1 FROM calibration_responses WHERE session_id = v_sid AND answered_at IS NULL) THEN
    RAISE EXCEPTION 'close left an unanswered row';
  END IF;
  v_close2 := calibration_placement_close(p_user, v_sid, 'learner');
  IF NOT (v_close2->>'already_closed')::boolean OR v_close2->>'stop_reason' <> v_stop
     OR v_close2->'m' <> v_close->'m' OR (v_close2->'mr') IS DISTINCT FROM (v_close->'mr') THEN
    RAISE EXCEPTION 'close is not idempotent: % vs %', v_close, v_close2;
  END IF;
  IF v_close->'m' <> v_exp_m THEN RAISE EXCEPTION 'close tallies differ from the hand count'; END IF;

  RETURN jsonb_build_object('session_id', v_sid, 'answers', v_i, 'words', v_words, 'scored', v_scored,
                            'reveals', v_reveals, 'stop', v_stop, 'm', v_exp_m, 'mr', v_exp_mr,
                            'probes', (SELECT jsonb_object_agg(probe_kind, n) FROM (
                                         SELECT probe_kind, count(*) n FROM calibration_responses
                                          WHERE session_id = v_sid AND probe_kind IS NOT NULL GROUP BY 1) q),
                            'warmup_done', v_close->'warmup_done', 'active_ms', v_close->'active_ms');
END $$;

-- -----------------------------------------------------------------------------
-- Users and history for the 180-day exclusion
-- -----------------------------------------------------------------------------
CREATE TEMP TABLE plc_u (k text PRIMARY KEY, id uuid);
INSERT INTO plc_u VALUES ('zh', gen_random_uuid()), ('ja', gen_random_uuid()), ('en', gen_random_uuid()),
                         ('zhja', gen_random_uuid()), ('jazh', gen_random_uuid()), ('other', gen_random_uuid()),
                         ('exh', gen_random_uuid()), ('stale', gen_random_uuid());

-- The zh learner answered 10 band-7 and 10 band-6 words in a legacy check 30 days ago
-- (excluded for 180 days) and 5 band-7 words 200 days ago (no longer excluded).
DO $$
DECLARE u uuid := (SELECT id FROM plc_u WHERE k = 'zh'); s uuid;
BEGIN
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode, started_at)
  VALUES (u, 1, 2, 'definition', now() - interval '30 days') RETURNING id INTO s;
  INSERT INTO calibration_responses (session_id, user_id, anchor_sense_id, anchor_vocab_id, anchor_zipf, zipf_band,
                                     chosen_sense_id, is_correct, served_at, answered_at)
  SELECT s, u, p.sense_id, p.vocab_id, p.zipf, p.zipf_band, NULL, false,
         now() - CASE WHEN rn <= 10 OR p.zipf_band = 6 THEN interval '30 days' ELSE interval '200 days' END,
         now() - CASE WHEN rn <= 10 OR p.zipf_band = 6 THEN interval '30 days' ELSE interval '200 days' END
    FROM (SELECT p.*, row_number() OVER (PARTITION BY p.zipf_band ORDER BY p.vocab_id) rn
            FROM calibration_anchor_pool p WHERE p.word_language_id = 1 AND p.definition_language_id = 2
             AND p.zipf_band IN (6, 7)) p
   WHERE (p.zipf_band = 7 AND p.rn <= 15) OR (p.zipf_band = 6 AND p.rn <= 10);
END $$;

-- -----------------------------------------------------------------------------
-- 1. Scripted sessions per language
-- -----------------------------------------------------------------------------
CREATE TEMP TABLE plc_runs (k text, out jsonb);
INSERT INTO plc_runs SELECT 'zh', pg_temp.plc_run((SELECT id FROM plc_u WHERE k = 'zh'), 1::smallint, 2::smallint, 60,
                                                  ARRAY[7,6,5,4,3,2,1]::smallint[]);
INSERT INTO plc_runs SELECT 'ja', pg_temp.plc_run((SELECT id FROM plc_u WHERE k = 'ja'), 3::smallint, 2::smallint, 60,
                                                  ARRAY[7,6,5,4,3,2,1]::smallint[]);
INSERT INTO plc_runs SELECT 'en', pg_temp.plc_run((SELECT id FROM plc_u WHERE k = 'en'), 2::smallint, 2::smallint, 40,
                                                  ARRAY[7,6,5,4,3,2,1]::smallint[]);
-- rule 5 pairs, with probes forced (u_probe = 0) to exercise every probe branch and the budget
INSERT INTO plc_runs SELECT 'zhja', pg_temp.plc_run((SELECT id FROM plc_u WHERE k = 'zhja'), 1::smallint, 3::smallint, 60,
                                                    ARRAY[7,6,5,4,3,2,1]::smallint[], 0.0);
INSERT INTO plc_runs SELECT 'jazh', pg_temp.plc_run((SELECT id FROM plc_u WHERE k = 'jazh'), 3::smallint, 1::smallint, 60,
                                                    ARRAY[7,6,5,4,3,2,1]::smallint[], 0.0);
-- u_probe = 0.3: no forced_guess (< 0.15) or reading_after_miss (< 0.25), so the ja
-- sound_pair branch (< 0.5) is the only probe that can fire
INSERT INTO plc_u VALUES ('jasp', gen_random_uuid());
INSERT INTO plc_runs SELECT 'jasp', pg_temp.plc_run((SELECT id FROM plc_u WHERE k = 'jasp'), 3::smallint, 2::smallint, 60,
                                                    ARRAY[7,6,5,4,3,2,1]::smallint[], 0.3);

DO $$
DECLARE x record;
BEGIN
  FOR x IN SELECT * FROM plc_runs ORDER BY k LOOP
    RAISE NOTICE 'PASS session %: %', x.k, x.out;
    IF (x.out->>'scored')::int < (CASE WHEN x.k = 'en' THEN 40 ELSE 60 END) AND x.out->>'stop' <> 'exhausted' THEN
      RAISE EXCEPTION 'session % stopped early without exhaustion', x.k;
    END IF;
  END LOOP;
  IF NOT EXISTS (SELECT 1 FROM plc_runs WHERE k IN ('zhja', 'jazh') AND out->'probes' ? 'forced_guess')
     OR NOT EXISTS (SELECT 1 FROM plc_runs WHERE k IN ('zhja', 'jazh') AND out->'probes' ? 'reading_after_miss')
     OR NOT EXISTS (SELECT 1 FROM plc_runs WHERE k IN ('jazh', 'jasp') AND out->'probes' ? 'sound_pair') THEN
    RAISE EXCEPTION 'not every probe kind was exercised: %', (SELECT jsonb_object_agg(k, out->'probes') FROM plc_runs);
  END IF;
  IF (SELECT out->'probes' FROM plc_runs WHERE k = 'jasp') - 'sound_pair' <> '{}'::jsonb THEN
    RAISE EXCEPTION 'u_probe 0.3 fired a probe other than sound_pair';
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 2. Ownership: a foreign session (P0002), a foreign response (22023), a closed
--    session (22023), invalid inputs (22023)
-- -----------------------------------------------------------------------------
DO $$
DECLARE
  a uuid := (SELECT id FROM plc_u WHERE k = 'other');
  b uuid := (SELECT id FROM plc_u WHERE k = 'zh');
  sa uuid; sb uuid; ia jsonb; ib jsonb; ok boolean;
BEGIN
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode) VALUES (a, 1, 2, 'placement') RETURNING id INTO sa;
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode) VALUES (b, 1, 2, 'placement') RETURNING id INTO sb;
  ia := calibration_placement_next_item(a, sa, 5::smallint);
  ib := calibration_placement_next_item(b, sb, 5::smallint);

  ok := false; BEGIN PERFORM calibration_placement_next_item(a, sb, 5::smallint); EXCEPTION WHEN SQLSTATE 'P0002' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'next_item on a foreign session not rejected'; END IF;
  ok := false; BEGIN PERFORM calibration_placement_answer(a, sb, (ib->>'response_id')::bigint, 0::smallint, 100, 5::smallint, '{}'); EXCEPTION WHEN SQLSTATE 'P0002' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'answer on a foreign session not rejected'; END IF;
  ok := false; BEGIN PERFORM calibration_placement_answer(a, sa, (ib->>'response_id')::bigint, 0::smallint, 100, 5::smallint, '{}'); EXCEPTION WHEN SQLSTATE '22023' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'foreign response accepted'; END IF;
  ok := false; BEGIN PERFORM calibration_placement_close(a, sb, 'learner'); EXCEPTION WHEN SQLSTATE 'P0002' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'close on a foreign session not rejected'; END IF;
  ok := false; BEGIN PERFORM calibration_placement_answer(a, sa, (ia->>'response_id')::bigint, (-1)::smallint, 100, 5::smallint, '{}'); EXCEPTION WHEN SQLSTATE '22023' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'negative position accepted'; END IF;
  ok := false; BEGIN PERFORM calibration_placement_answer(a, sa, (ia->>'response_id')::bigint, 0::smallint, 100, 9::smallint, '{}'); EXCEPTION WHEN SQLSTATE '22023' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'band 9 accepted'; END IF;
  ok := false; BEGIN PERFORM calibration_placement_answer(a, sa, (ia->>'response_id')::bigint, 0::smallint, 100, 5::smallint, '{"u_probe": 2}'); EXCEPTION WHEN SQLSTATE '22023' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'u_probe 2 accepted'; END IF;
  ok := false; BEGIN PERFORM calibration_placement_close(a, sa, 'bored'); EXCEPTION WHEN SQLSTATE '22023' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'bad stop reason accepted'; END IF;
  -- a check session is not a placement
  UPDATE calibration_sessions SET mode = 'definition' WHERE id = sb;
  ok := false; BEGIN PERFORM calibration_placement_next_item(b, sb, 5::smallint); EXCEPTION WHEN SQLSTATE 'P0002' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'a check session was accepted as a placement'; END IF;
  UPDATE calibration_sessions SET mode = 'placement' WHERE id = sb;

  -- resend: the pending item comes back unchanged, no second row
  IF (calibration_placement_next_item(a, sa, 3::smallint)->>'response_id') <> ia->>'response_id'
     OR (SELECT count(*) FROM calibration_responses WHERE session_id = sa) <> 1 THEN
    RAISE EXCEPTION 'pending item not re-sent';
  END IF;
  IF (calibration_placement_next_item(a, sa, 3::smallint) - 'resent') <> ia THEN
    RAISE EXCEPTION 're-sent payload differs: % vs %', calibration_placement_next_item(a, sa, 3::smallint), ia;
  END IF;

  -- latency clamp; then closed session rejects answers
  PERFORM calibration_placement_answer(a, sa, (ia->>'response_id')::bigint, NULL, 9999999, NULL, '{"u_probe": 1, "u_seed": 0.5}');
  IF (SELECT latency_ms FROM calibration_responses WHERE id = (ia->>'response_id')::bigint) <> 600000 THEN
    RAISE EXCEPTION 'latency not clamped';
  END IF;
  PERFORM calibration_placement_close(a, sa, 'learner');
  ok := false; BEGIN PERFORM calibration_placement_next_item(a, sa, 5::smallint); EXCEPTION WHEN SQLSTATE '22023' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'next_item on a closed session not rejected'; END IF;
  ok := false; BEGIN PERFORM calibration_placement_answer(b, sb, (ib->>'response_id')::bigint, 0::smallint, 100, NULL, '{}');
                     PERFORM calibration_placement_answer(b, sb, (ib->>'response_id')::bigint, 0::smallint, 100, NULL, '{}');
               EXCEPTION WHEN SQLSTATE '22023' THEN ok := true; END;
  IF NOT ok THEN RAISE EXCEPTION 'second answer accepted'; END IF;
  DELETE FROM calibration_sessions WHERE id IN (sa, sb);
  RAISE NOTICE 'PASS ownership, validation, resend, latency clamp, closed session';
END $$;

-- -----------------------------------------------------------------------------
-- 3. close_stale: an open placement idle for 2 days is closed 'abandoned', its
--    pending row deleted; a fresh one is left open.
-- -----------------------------------------------------------------------------
DO $$
DECLARE u uuid := (SELECT id FROM plc_u WHERE k = 'stale'); s_old uuid; s_new uuid; it jsonb; ids uuid[];
BEGIN
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode) VALUES (u, 2, 2, 'placement') RETURNING id INTO s_old;
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode) VALUES (u, 2, 2, 'placement') RETURNING id INTO s_new;
  it := calibration_placement_next_item(u, s_old, 7::smallint);
  PERFORM calibration_placement_answer(u, s_old, (it->>'response_id')::bigint, NULL, 1000, 6::smallint, '{"u_probe": 1, "u_seed": 0.3}');
  PERFORM calibration_placement_next_item(u, s_new, 7::smallint);
  UPDATE calibration_sessions SET started_at = started_at - interval '2 days' WHERE id = s_old;
  UPDATE calibration_responses SET served_at = served_at - interval '2 days',
                                   answered_at = answered_at - interval '2 days' WHERE session_id = s_old;
  ids := calibration_placement_close_stale(u, interval '24 hours');
  IF ids <> ARRAY[s_old] THEN RAISE EXCEPTION 'close_stale returned %', ids; END IF;
  IF (SELECT stop_reason FROM calibration_sessions WHERE id = s_old) <> 'abandoned'
     OR (SELECT ended_at FROM calibration_sessions WHERE id = s_old) > now() - interval '1 day'
     OR EXISTS (SELECT 1 FROM calibration_responses WHERE session_id = s_old AND answered_at IS NULL)
     OR (SELECT ended_at FROM calibration_sessions WHERE id = s_new) IS NOT NULL THEN
    RAISE EXCEPTION 'close_stale closed the wrong thing';
  END IF;
  IF calibration_placement_close_stale(NULL, interval '24 hours') <> '{}'::uuid[] THEN
    RAISE EXCEPTION 'close_stale(NULL) found more sessions';
  END IF;
  RAISE NOTICE 'PASS close_stale';
END $$;

-- -----------------------------------------------------------------------------
-- 4. Nearest-band fallback and exhaustion (ja 3:2, always asking for band 7)
-- -----------------------------------------------------------------------------
DO $$
DECLARE u uuid := (SELECT id FROM plc_u WHERE k = 'exh'); o jsonb; bands smallint[]; s uuid; x jsonb;
BEGIN
  o := pg_temp.plc_run(u, 3::smallint, 2::smallint, 100000, ARRAY[7]::smallint[], 1.0, 2000);
  IF o->>'stop' <> 'exhausted' THEN RAISE EXCEPTION 'expected exhaustion: %', o; END IF;
  s := (o->>'session_id')::uuid;
  SELECT array_agg(zipf_band ORDER BY id) INTO bands FROM calibration_responses
   WHERE session_id = s AND item_kind = 'meaning' AND probe_kind IS NULL;
  IF EXISTS (SELECT 1 FROM generate_subscripts(bands, 1) i WHERE i > 1 AND bands[i] > bands[i - 1]) THEN
    RAISE EXCEPTION 'fallback did not move to the nearest band: %', bands;
  END IF;
  IF (SELECT count(*) FROM calibration_responses WHERE session_id = s AND item_kind = 'meaning' AND probe_kind IS NULL)
     <> (SELECT sum((b->>'ready_n')::int) FROM jsonb_array_elements(calibration_placement_ready_counts(3::smallint, 2::smallint)->'bands') b) THEN
    RAISE EXCEPTION 'exhausted before every ready word was served';
  END IF;
  -- a new session of the same learner: every ready word was answered today -> exhausted
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode) VALUES (u, 3, 2, 'placement') RETURNING id INTO s;
  x := calibration_placement_next_item(u, s, 4::smallint);
  IF x <> '{"exhausted": true}'::jsonb THEN RAISE EXCEPTION 'next_item on an exhausted pool: %', x; END IF;
  IF (calibration_placement_tallies(s)->>'warmup_done')::boolean IS NOT TRUE THEN
    RAISE EXCEPTION 'warm-up must count as done when no band has a word left';
  END IF;
  RAISE NOTICE 'PASS fallback and exhaustion: % meaning items, bands %', cardinality(bands), bands;
END $$;

-- -----------------------------------------------------------------------------
-- 5. Recheck probes: the zh learner's placement is moved 10 days back; a new
--    placement opens with rechecks of credited readings, foils disjoint from the
--    first serving, then scored items avoid every word of the first placement.
-- -----------------------------------------------------------------------------
DO $$
DECLARE
  u uuid := (SELECT id FROM plc_u WHERE k = 'zh');
  s0 uuid := (SELECT (out->>'session_id')::uuid FROM plc_runs WHERE k = 'zh');
  s uuid; it jsonb; res jsonb; r calibration_responses%ROWTYPE; e calibration_responses%ROWTYPE; n_re integer := 0;
BEGIN
  UPDATE calibration_sessions SET started_at = started_at - interval '10 days', ended_at = ended_at - interval '10 days' WHERE id = s0;
  UPDATE calibration_responses SET served_at = served_at - interval '10 days', answered_at = answered_at - interval '10 days' WHERE session_id = s0;
  IF NOT EXISTS (SELECT 1 FROM calibration_responses rr JOIN calibration_responses mm ON mm.id = rr.pair_response_id
                  WHERE rr.session_id = s0 AND rr.item_kind = 'reading' AND rr.probe_kind IS NULL AND rr.is_correct AND mm.is_correct) THEN
    RAISE EXCEPTION 'fixture: the zh run credited no reading';
  END IF;
  INSERT INTO calibration_sessions (user_id, word_language_id, definition_language_id, mode) VALUES (u, 1, 2, 'placement') RETURNING id INTO s;
  it := calibration_placement_next_item(u, s, 7::smallint);
  LOOP
    PERFORM pg_temp.plc_check_item(u, s, it);
    SELECT * INTO r FROM calibration_responses WHERE id = (it->>'response_id')::bigint;
    EXIT WHEN r.probe_kind IS DISTINCT FROM 'recheck';
    n_re := n_re + 1;
    SELECT rr.* INTO e FROM calibration_responses rr WHERE rr.session_id = s0 AND rr.anchor_vocab_id = r.anchor_vocab_id
       AND rr.item_kind = 'reading' AND rr.probe_kind IS NULL;
    IF NOT e.is_correct OR r.pair_response_id IS NOT NULL OR r.instrument <> 'reading_tone_v1'
       OR EXISTS (SELECT 1 FROM unnest(r.option_sense_ids) x WHERE x IS NOT NULL AND x = ANY (e.option_sense_ids)
                     AND x <> r.anchor_sense_id)
       OR EXISTS (SELECT 1 FROM unnest(r.option_texts) t WHERE t = ANY (e.option_texts)
                     AND t <> r.option_texts[r.key_position + 1]) THEN
      RAISE EXCEPTION 'recheck % not disjoint from its first serving % / %', r.option_texts, e.option_texts, r.option_sense_ids;
    END IF;
    res := calibration_placement_answer(u, s, r.id, r.key_position, 3000, 7::smallint, '{"u_probe": 1, "u_seed": 0.7}');
    IF jsonb_typeof(res->'reveal') <> 'object' THEN RAISE EXCEPTION 'recheck must reveal at once'; END IF;
    it := res->'next_item';
  END LOOP;
  IF n_re < 1 OR n_re > 2 THEN RAISE EXCEPTION 'expected 1-2 rechecks, got %', n_re; END IF;
  IF r.item_kind <> 'meaning' OR r.probe_kind IS NOT NULL THEN RAISE EXCEPTION 'after rechecks a scored meaning item must follow'; END IF;
  IF (calibration_placement_tallies(s)->>'scored')::int <> 0 OR (calibration_placement_tallies(s)->>'probes')::int <> n_re THEN
    RAISE EXCEPTION 'rechecks counted as scored';
  END IF;
  PERFORM calibration_placement_close(u, s, 'learner');
  RAISE NOTICE 'PASS recheck: % probe(s) with disjoint foils', n_re;
END $$;

-- -----------------------------------------------------------------------------
-- 6. ready_counts shape and consistency
-- -----------------------------------------------------------------------------
DO $$
DECLARE x record; j jsonb; b jsonb;
BEGIN
  FOR x IN SELECT * FROM (VALUES (1::smallint, 2::smallint), (1::smallint, 3::smallint), (3::smallint, 1::smallint),
                                 (3::smallint, 2::smallint), (2::smallint, 2::smallint)) v(l, d) LOOP
    j := calibration_placement_ready_counts(x.l, x.d);
    IF jsonb_array_length(j->'bands') <> 7 THEN RAISE EXCEPTION 'ready_counts bands'; END IF;
    IF (j->>'frame')::int <> (SELECT sum((e->>'frame_n')::int) FROM jsonb_array_elements(j->'bands') e)
       OR (j->>'ready')::int <> (SELECT sum((e->>'ready_n')::int) FROM jsonb_array_elements(j->'bands') e) THEN
      RAISE EXCEPTION 'ready_counts totals';
    END IF;
    FOR b IN SELECT * FROM jsonb_array_elements(j->'bands') LOOP
      IF (b->>'ready_n')::int > (b->>'meaning_ready_n')::int
         OR (b->>'ready_n')::int > (b->>'reading_ready_n')::int + (b->>'exempt_n')::int THEN
        RAISE EXCEPTION 'ready_counts band inconsistent: %', b;
      END IF;
    END LOOP;
    IF x.l = 2 AND (j->>'ready')::int <> (SELECT sum((e->>'meaning_ready_n')::int) FROM jsonb_array_elements(j->'bands') e) THEN
      RAISE EXCEPTION 'en: every meaning-ready word is ready';
    END IF;
    RAISE NOTICE 'ready_counts(%,%): frame % ready % rule5 % rule3b % tone %', x.l, x.d, j->>'frame', j->>'ready',
      (SELECT sum((e->>'excluded_rule5_n')::int) FROM jsonb_array_elements(j->'bands') e),
      (SELECT sum((e->>'excluded_rule3b_n')::int) FROM jsonb_array_elements(j->'bands') e),
      (SELECT sum((e->>'excluded_tone_n')::int) FROM jsonb_array_elements(j->'bands') e);
  END LOOP;
  IF calibration_placement_ready_counts(9::smallint, 9::smallint)->>'frame' <> '0' THEN RAISE EXCEPTION 'unknown pair'; END IF;
  RAISE NOTICE 'PASS ready_counts';
END $$;

-- -----------------------------------------------------------------------------
-- 7. A zh word without a tone variant is not reading-ready (rule 4 readiness)
-- -----------------------------------------------------------------------------
DO $$
DECLARE v integer; k record;
BEGIN
  SELECT p.vocab_id INTO v FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id AND s.sense_rank = 1
   WHERE p.word_language_id = 1 AND p.definition_language_id = 2
     AND calibration_placement_reading_ready(p.vocab_id, 1::smallint, p.lemma) LIMIT 1;
  SELECT * INTO k FROM calibration_placement_reading_key(v, 1::smallint);
  -- make the key's only full tone neutral: no variant exists, and it is no longer well-formed
  UPDATE dim_word_senses SET pronunciation = calibration_placement_toneless(k.reading) WHERE id = k.sense_id;
  IF calibration_placement_reading_ready(v, 1::smallint, (SELECT lemma FROM dim_vocabulary WHERE id = v)) THEN
    RAISE EXCEPTION 'an unmarked zh key counted as reading-ready';
  END IF;
  RAISE NOTICE 'PASS zh readiness needs a marked, variant-bearing key';
END $$;

-- -----------------------------------------------------------------------------
-- 8. knowledge_calibration_inputs on the scripted sessions (TASK-1079), if installed
-- -----------------------------------------------------------------------------
DO $$
DECLARE
  x record; j jsonb; s uuid; t jsonb;
BEGIN
  IF to_regprocedure('public.knowledge_calibration_inputs(uuid,smallint,timestamptz,integer,smallint,uuid)') IS NULL THEN
    RAISE NOTICE 'SKIP knowledge_calibration_inputs (not installed)';
    RETURN;
  END IF;
  FOR x IN SELECT r.k, (r.out->>'session_id')::uuid AS sid, u.id AS uid, r.out
             FROM plc_runs r JOIN plc_u u ON u.k = r.k WHERE r.k IN ('ja', 'en', 'zhja', 'jazh') LOOP
    -- p_as_of = clock_timestamp(): this test is one transaction, so now() precedes every answer
    j := knowledge_calibration_inputs(x.uid, (SELECT word_language_id FROM calibration_sessions WHERE id = x.sid),
                                      clock_timestamp(), 180, NULL, x.sid);
    -- bands [n, s, c] must agree with the session's m tallies [n, c, w]
    t := calibration_placement_tallies(x.sid);
    IF (SELECT jsonb_agg(jsonb_build_array(e->0, (e->>0)::int - (e->>1)::int - (e->>2)::int, e->1) ORDER BY o)
          FROM jsonb_array_elements(t->'m') WITH ORDINALITY q(e, o)) <> j->'bands' THEN
      RAISE EXCEPTION 'inputs(session) bands % vs tallies %', j->'bands', t->'m';
    END IF;
    IF (j->'pairs') IS DISTINCT FROM (CASE WHEN x.k = 'en' THEN 'null'::jsonb
                                          ELSE (SELECT jsonb_agg(e ORDER BY o) FROM jsonb_array_elements(t->'mr') WITH ORDINALITY q(e, o)) END) THEN
      RAISE EXCEPTION 'inputs(session) pairs % vs tallies %', j->'pairs', t->'mr';
    END IF;
    IF j->>'instrument' <> 'meaning_bare_v1' OR (j->'stop_reasons') <> jsonb_build_array(x.out->>'stop') THEN
      RAISE EXCEPTION 'inputs(session) header %', j;
    END IF;
    -- combined (no session): the eligible placement sets D and the instrument
    j := knowledge_calibration_inputs(x.uid, (SELECT word_language_id FROM calibration_sessions WHERE id = x.sid),
                                      clock_timestamp());
    IF j->>'instrument' <> 'meaning_bare_v1'
       OR (j->>'definition_language_id')::int <> (SELECT definition_language_id FROM calibration_sessions WHERE id = x.sid) THEN
      RAISE EXCEPTION 'inputs(combined) did not switch to the placement: %', j;
    END IF;
  END LOOP;
  RAISE NOTICE 'PASS knowledge_calibration_inputs agrees with the session tallies';
END $$;

ROLLBACK;
