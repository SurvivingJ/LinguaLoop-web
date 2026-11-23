-- =============================================================================
-- knowledge_calibration_inputs.sql  (TASK-1079; ADR-051 extended by ADR-058/060)
-- =============================================================================
-- One STABLE function that supplies the calibration inputs of the Knowledge Report's
-- vocabulary-size estimate (report tech §2.6) and of the placement result (placement
-- tech §5.1, §9, §14). knowledge_report_summary (TASK-1036) embeds it, and the
-- placement's finish() calls it, so both run services/vocabulary/knowledge_estimate.py
-- on the same counts.
--
-- knowledge_calibration_inputs(p_user_id, p_language_id, p_as_of = now(),
--                              p_window_days = 180, p_definition_language_id = NULL,
--                              p_session_id = NULL) -> jsonb
--
-- Sample selection
--   * p_session_id given: that session's scored items only (the user and word
--     language must match; otherwise the result is empty). D = the session's D; a
--     placement uses instrument meaning_bare_v1, a legacy check session its legacy
--     rows. No window (answers up to p_as_of).
--   * otherwise the report's D and instrument rule (placement tech §9):
--     - an ELIGIBLE placement for L ended in (as_of - window, as_of] -> D = the latest
--       such placement's D (or p_definition_language_id: then only a placement in
--       that D counts), instrument = meaning_bare_v1;
--       eligible = stop_reason precision | cap | time | exhausted | learner (eligible
--       by construction: End now finishes only when eligible), or abandoned with a
--       frozen result; and never result->>'eligible' = 'false'.
--     - else ADR-051 rule 1 on legacy rows (mode 'definition', instrument NULL):
--       D* = most answers in the window, ties -> later last answer, ties -> lower id;
--       with no answer in the window, the same over all answers; p_definition_
--       language_id overrides D*.
-- Meaning bands: latest scored answer per anchor_vocab_id (rank-1 anchors, probes
-- excluded) in the window; bands[b] = [n, s, c] (n lemmas, s "I don't know", c right).
-- alltime_n: n per band without the window. first_at / last_at: over the windowed
-- sample, or over the all-time sample when the window is empty (report state E1c).
-- Pairs and gap (zh, ja, instrument meaning_bare_v1 only; placements only; latest
-- placement meaning answer per lemma in the window): a word is in the pair sample when
-- its meaning was answered and, if a reading was due (reading-ready word, meaning
-- right), the reading was answered too.
--   ja pairs [n', pc, prw]; ja gap [n', a43, b1, cm13]
--   zh pairs [n', pc, pkt, pf]; zh gap [n', f, idk, cm13, kt]
--   (tech §5.1 tables; ja kana-only lemmas are reading-exempt; zh has none).
-- placement_eligible: a placement in the sample stopped by precision, cap, time or
-- exhausted (the precondition of eligibility rule (b)). stop_reasons: the distinct
-- stop reasons of the placements in the sample.
-- rated_known_in_frame: rank-1 meanings with word_test_correct > word_test_wrong,
-- p_last >= 0.75 and not marked unknown (report §2.2 primary row, §2.4), whose lemma
-- is in the frame F(L, D); NULL when there is no D.
--
-- Return keys (exactly placement tech §14): definition_language_id, instrument,
-- bands, pairs, gap, alltime_n, first_at, last_at, placement_eligible, stop_reasons,
-- rated_known_in_frame.
--
-- Note for finish() (TASK-1080): an abandoned placement counts for the D/instrument
-- rule only once its result is frozen. For the combined call made before the freeze,
-- treat a returned instrument other than meaning_bare_v1 as "combined = this".
--
-- STABLE, SECURITY INVOKER, service role only. Reads the columns added by
-- calibration_placement.sql (TASK-1076): apply that first. The reading-exempt rule is
-- inlined (same regex as calibration_placement_reading_exempt) so this file does not
-- depend on calibration_placement_rpcs.sql.
-- Idempotent. REQUIRES USER APPROVAL TO APPLY LIVE.
-- Rollback: migrations/knowledge_calibration_inputs_rollback.sql.
-- Check after apply (read-only; report §2.6 fixture, D = 2):
--   SELECT knowledge_calibration_inputs('<de6fd05b uuid>', 3::smallint);
-- =============================================================================

CREATE OR REPLACE FUNCTION public.knowledge_calibration_inputs(
    p_user_id uuid,
    p_language_id smallint,
    p_as_of timestamptz DEFAULT now(),
    p_window_days integer DEFAULT 180,
    p_definition_language_id smallint DEFAULT NULL,
    p_session_id uuid DEFAULT NULL)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
WITH prm AS (
    SELECT p_as_of AS t1,
           p_as_of - make_interval(days => greatest(coalesce(p_window_days, 180), 0)) AS t0
),
sess AS (
    SELECT cs.*
      FROM calibration_sessions cs
     WHERE p_session_id IS NOT NULL
       AND cs.id = p_session_id AND cs.user_id = p_user_id AND cs.word_language_id = p_language_id
),
elig AS (
    SELECT cs.definition_language_id AS d
      FROM calibration_sessions cs, prm
     WHERE p_session_id IS NULL
       AND cs.user_id = p_user_id AND cs.word_language_id = p_language_id AND cs.mode = 'placement'
       AND cs.ended_at IS NOT NULL AND cs.ended_at <= prm.t1 AND cs.ended_at > prm.t0
       AND cs.stop_reason IS NOT NULL
       AND (cs.stop_reason <> 'abandoned' OR cs.result IS NOT NULL)
       AND coalesce(cs.result ->> 'eligible', 'true') <> 'false'
       AND (p_definition_language_id IS NULL OR cs.definition_language_id = p_definition_language_id)
     ORDER BY cs.ended_at DESC, cs.id
     LIMIT 1
),
legacy_a AS (
    SELECT cs.definition_language_id AS d, cr.answered_at
      FROM calibration_sessions cs
      JOIN calibration_responses cr ON cr.session_id = cs.id
      JOIN dim_word_senses a ON a.id = cr.anchor_sense_id AND a.sense_rank = 1, prm
     WHERE p_session_id IS NULL
       AND cs.user_id = p_user_id AND cs.word_language_id = p_language_id AND cs.mode = 'definition'
       AND cr.instrument IS NULL AND cr.probe_kind IS NULL
       AND cr.answered_at IS NOT NULL AND cr.answered_at <= prm.t1
),
dstar AS (
    SELECT x.d
      FROM (SELECT l.d,
                   count(*) FILTER (WHERE l.answered_at > prm.t0)          AS n_win,
                   max(l.answered_at) FILTER (WHERE l.answered_at > prm.t0) AS last_win,
                   count(*)                                                 AS n_all,
                   max(l.answered_at)                                       AS last_all
              FROM legacy_a l, prm
             GROUP BY l.d) x,
           (SELECT coalesce(bool_or(l.answered_at > prm.t0), false) AS any_win FROM legacy_a l, prm) w
     ORDER BY CASE WHEN w.any_win THEN x.n_win ELSE x.n_all END DESC,
              CASE WHEN w.any_win THEN x.last_win ELSE x.last_all END DESC NULLS LAST,
              x.d
     LIMIT 1
),
cfg AS (
    SELECT CASE WHEN p_session_id IS NOT NULL
                     THEN (SELECT CASE WHEN s.mode = 'placement' THEN 'meaning_bare_v1' END FROM sess s)
                WHEN EXISTS (SELECT 1 FROM elig) THEN 'meaning_bare_v1'
           END AS instrument,
           CASE WHEN p_session_id IS NOT NULL THEN (SELECT s.definition_language_id FROM sess s)
                ELSE coalesce(p_definition_language_id, (SELECT d FROM elig), (SELECT d FROM dstar))
           END AS d,
           (p_session_id IS NOT NULL) AS by_session,
           (p_session_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM sess)) AS no_session
),
mrows AS (
    SELECT cr.id, cr.session_id, cr.anchor_vocab_id AS v, cr.zipf_band AS b, cr.answered_at,
           cr.is_correct, (cr.chosen_sense_id IS NULL) AS skip, cr.chosen_position,
           cr.reading_exempt, cs.mode, cs.stop_reason
      FROM cfg, prm, calibration_sessions cs
      JOIN calibration_responses cr ON cr.session_id = cs.id
      JOIN dim_word_senses a ON a.id = cr.anchor_sense_id AND a.sense_rank = 1
     WHERE NOT cfg.no_session
       AND cs.user_id = p_user_id AND cs.word_language_id = p_language_id
       AND cs.definition_language_id = cfg.d
       AND (NOT cfg.by_session OR cs.id = p_session_id)
       AND cr.answered_at IS NOT NULL AND cr.answered_at <= prm.t1
       AND cr.probe_kind IS NULL
       AND CASE WHEN cfg.instrument = 'meaning_bare_v1' THEN cr.instrument = 'meaning_bare_v1'
                ELSE cr.instrument IS NULL AND cs.mode = 'definition' END
),
win AS (
    SELECT DISTINCT ON (m.v) m.*
      FROM mrows m, cfg, prm
     WHERE cfg.by_session OR m.answered_at > prm.t0
     ORDER BY m.v, m.answered_at DESC, m.id DESC
),
allt AS (
    SELECT DISTINCT ON (m.v) m.*
      FROM mrows m
     ORDER BY m.v, m.answered_at DESC, m.id DESC
),
pm AS (
    SELECT DISTINCT ON (m.v) m.*
      FROM mrows m, cfg, prm
     WHERE cfg.instrument = 'meaning_bare_v1' AND m.mode = 'placement'
       AND (cfg.by_session OR m.answered_at > prm.t0)
     ORDER BY m.v, m.answered_at DESC, m.id DESC
),
pj AS (
    SELECT pm.b,
           pm.is_correct AS mc,
           (pm.chosen_position IS NULL) AS m_idk,
           -- PQ23: the flag recorded when the meaning item was served (meaning-only words);
           -- rows served before it existed fall back to the lemma rule.
           coalesce(pm.reading_exempt,
                    p_language_id = 3 AND coalesce(v.lemma ~ '^[ぁ-ゟァ-ヿー・]+$', false)) AS ex,
           (rd.id IS NOT NULL) AS r_ans,
           coalesce(rd.is_correct, false) AS rc,
           (rd.id IS NOT NULL AND rd.chosen_position IS NULL) AS r_idk,
           rd.option_roles[rd.chosen_position + 1] AS role
      FROM pm
      JOIN dim_vocabulary v ON v.id = pm.v
      LEFT JOIN calibration_responses rd
        ON rd.pair_response_id = pm.id AND rd.item_kind = 'reading' AND rd.probe_kind IS NULL
       AND rd.answered_at IS NOT NULL AND rd.answered_at <= p_as_of
),
ps AS (SELECT * FROM pj WHERE ex OR NOT mc OR r_ans),
bands AS (SELECT g AS b FROM generate_series(1, 7) g),
bw AS (
    SELECT bands.b,
           jsonb_build_array(count(w.v), count(w.v) FILTER (WHERE w.skip),
                             count(w.v) FILTER (WHERE w.is_correct)) AS x
      FROM bands LEFT JOIN win w ON w.b = bands.b GROUP BY bands.b
),
ba AS (
    SELECT bands.b, count(a.v) AS n FROM bands LEFT JOIN allt a ON a.b = bands.b GROUP BY bands.b
),
pb AS (
    SELECT bands.b,
           CASE WHEN p_language_id = 1 THEN
               jsonb_build_array(count(ps.b),
                                 count(ps.b) FILTER (WHERE ps.mc AND (ps.ex OR ps.role = 'K')),
                                 count(ps.b) FILTER (WHERE ps.mc AND ps.role = 'KT'),
                                 count(ps.b) FILTER (WHERE ps.mc AND ps.role IN ('F', 'FT')))
           ELSE
               jsonb_build_array(count(ps.b),
                                 count(ps.b) FILTER (WHERE ps.mc AND (ps.ex OR ps.rc)),
                                 count(ps.b) FILTER (WHERE (ps.ex AND NOT ps.mc AND NOT ps.m_idk)
                                                         OR (NOT ps.ex AND ps.mc AND ps.r_ans
                                                             AND NOT ps.rc AND NOT ps.r_idk)))
           END AS pairs,
           CASE WHEN p_language_id = 1 THEN
               jsonb_build_array(count(ps.b),
                                 count(ps.b) FILTER (WHERE ps.mc AND ps.role IN ('F', 'FT')),
                                 count(ps.b) FILTER (WHERE ps.mc AND ps.r_idk),
                                 count(ps.b) FILTER (WHERE NOT ps.mc AND NOT ps.m_idk),
                                 count(ps.b) FILTER (WHERE ps.mc AND ps.role = 'KT'))
           ELSE
               jsonb_build_array(count(ps.b),
                                 count(ps.b) FILTER (WHERE NOT ps.ex AND ps.mc AND ps.r_ans
                                                       AND NOT ps.rc AND NOT ps.r_idk),
                                 count(ps.b) FILTER (WHERE NOT ps.ex AND ps.mc AND ps.r_idk),
                                 count(ps.b) FILTER (WHERE NOT ps.ex AND NOT ps.mc AND NOT ps.m_idk))
           END AS gap
      FROM bands LEFT JOIN ps ON ps.b = bands.b GROUP BY bands.b
),
rk AS (
    SELECT count(DISTINCT g.vocab_id) AS n
      FROM cfg,
           (SELECT s.vocab_id,
                   sum(k.word_test_correct) AS wc,
                   sum(k.word_test_wrong) AS ww,
                   (array_agg(k.p_known ORDER BY k.last_evidence_at DESC NULLS LAST,
                                                 k.evidence_count DESC NULLS LAST, k.sense_id))[1] AS p_last,
                   bool_or(k.status = 'user_marked_unknown') AS marked_unknown
              FROM user_vocabulary_knowledge k
              JOIN dim_word_senses s ON s.id = k.sense_id AND s.sense_rank = 1
             WHERE k.user_id = p_user_id AND k.language_id = p_language_id
             GROUP BY s.vocab_id) g
     WHERE g.wc > g.ww AND g.p_last >= 0.75 AND NOT g.marked_unknown
       AND EXISTS (SELECT 1
                     FROM calibration_anchor_pool p
                     JOIN dim_word_senses ps ON ps.id = p.sense_id AND ps.sense_rank = 1
                    WHERE p.word_language_id = p_language_id AND p.definition_language_id = cfg.d
                      AND p.vocab_id = g.vocab_id AND p.has_embedding
                      AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl WHERE bl.sense_id = p.sense_id))
)
SELECT jsonb_build_object(
    'definition_language_id', cfg.d,
    'instrument',             cfg.instrument,
    'bands',                  (SELECT jsonb_agg(bw.x ORDER BY bw.b) FROM bw),
    'pairs',                  CASE WHEN cfg.instrument = 'meaning_bare_v1' AND p_language_id IN (1, 3)
                                   THEN (SELECT jsonb_agg(pb.pairs ORDER BY pb.b) FROM pb) END,
    'gap',                    CASE WHEN cfg.instrument = 'meaning_bare_v1' AND p_language_id IN (1, 3)
                                   THEN (SELECT jsonb_agg(pb.gap ORDER BY pb.b) FROM pb) END,
    'alltime_n',              (SELECT jsonb_agg(ba.n ORDER BY ba.b) FROM ba),
    'first_at',               CASE WHEN EXISTS (SELECT 1 FROM win) THEN (SELECT min(answered_at) FROM win)
                                   ELSE (SELECT min(answered_at) FROM allt) END,
    'last_at',                CASE WHEN EXISTS (SELECT 1 FROM win) THEN (SELECT max(answered_at) FROM win)
                                   ELSE (SELECT max(answered_at) FROM allt) END,
    'placement_eligible',     EXISTS (SELECT 1 FROM win
                                       WHERE win.mode = 'placement'
                                         AND win.stop_reason IN ('precision', 'cap', 'time', 'exhausted')),
    'stop_reasons',           coalesce((SELECT jsonb_agg(DISTINCT win.stop_reason ORDER BY win.stop_reason)
                                          FROM win WHERE win.mode = 'placement' AND win.stop_reason IS NOT NULL),
                                       '[]'::jsonb),
    'rated_known_in_frame',   CASE WHEN cfg.d IS NOT NULL THEN (SELECT n FROM rk) END)
  FROM cfg;
$$;

REVOKE ALL ON FUNCTION public.knowledge_calibration_inputs(uuid, smallint, timestamptz, integer, smallint, uuid)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.knowledge_calibration_inputs(uuid, smallint, timestamptz, integer, smallint, uuid)
  TO service_role;
