-- =============================================================================
-- exercise_content_drop_column_rollback.sql — undo the ADR-049 cut-over
-- (migrations/exercise_content_drop_column.sql, step 3)
-- Date: 2026-11-17   Task: TASK-1018   Spec: wiki/decisions/ADR-049-exercise-content-in-storage.md
--
-- STATUS: NOT applied. A runbook: run the steps in order, each on its own.
--
-- The cut-over deleted data from the database; SQL alone cannot bring it back. This file
-- restores the SCHEMA and the pre-drop RPCs; the data comes back in step R2 from Storage.
-- A rollback therefore ALSO NEEDS A REFILL OF exercises.content FROM STORAGE (step R2), for
-- which no script exists.
-- Note (TASK-1031, 2026-11-19): the code no longer has the EXERCISE_CONTENT_SOURCE /
-- EXERCISE_CONTENT_WRITE flags. It always passes p_include_content = false, hydrates from the
-- files and writes the files first, whatever this rollback restores; serving or writing
-- exercises.content again would also need the code from before TASK-1031. The pre-drop
-- bodies restored in R1 are those of migrations/exercise_content_storage.sql and
-- migrations/archive/exercise_content_session_rpcs.sql.
-- Space: the refilled column costs ~119 MB again (~470 MB database); check the cap first.
--
-- What is NOT restored by SQL (restore from exercise-content/_archive/ if wanted):
--   * the rows with no sense (_archive/exercises-no-sense-<YYYYMMDD>.json),
--   * backup_semdisc_content_20261115, semdisc_rewrite_work and apply_semdisc_notes(jsonb)
--     (_archive/semdisc-20261115/: {table}.jsonl.gz and apply_semdisc_notes.sql).
-- uq_exercises_context_free_variant_v2 and dedupe_key stay: the pre-drop commit RPC keeps
-- maintaining them, exactly as between TASK-1026 and the cut-over.
-- Renumbered 2026-11-17 when merged with main: ADR-047 -> ADR-049 and TASK-976..999 ->
-- TASK-1008..1031 (main already used those ids). Function bodies and COMMENT strings keep
-- the old ids: they are (or will be) the live text, md5-compared against the database.
-- =============================================================================


-- =============================================================================
-- STEP R1 — one transaction: the column back (nullable, catalog-only) and the pre-drop
-- versions of exercise_content_commit and the session RPCs (identical to
-- exercise_content_storage.sql / exercise_content_session_rpcs.sql; checked by
-- tests/test_exercise_content_migration_cutover.py).
-- =============================================================================
BEGIN;

ALTER TABLE public.exercises ADD COLUMN IF NOT EXISTS content jsonb;

CREATE OR REPLACE FUNCTION public.exercise_content_commit(
    p_sense_id         integer,
    p_expected_version integer,
    p_expected_ids     uuid[],
    p_new_version      integer,
    p_delete_ids       uuid[] DEFAULT '{}',
    p_insert_rows      jsonb  DEFAULT '[]',
    p_update_contents  jsonb  DEFAULT '{}'
)
RETURNS jsonb
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
    -- The 8 types of uq_exercises_context_free_variant (task743_context_free_exercise_caps.sql)
    -- and _CONTEXT_FREE_UNIQUE_TYPES (services/vocabulary_ladder/exercise_renderer.py).
    c_context_free constant text[] := ARRAY[
        'tone_id_word', 'hanzi_to_pinyin', 'pinyin_to_hanzi',
        'kanji_to_reading', 'reading_to_kanji', 'phonetic_recognition',
        'classifier_match', 'counter_match'
    ];
    v_delete_ids   uuid[] := COALESCE(p_delete_ids, '{}');
    v_insert_rows  jsonb  := COALESCE(p_insert_rows, '[]'::jsonb);
    v_updates      jsonb  := COALESCE(p_update_contents, '{}'::jsonb);
    v_row          jsonb;
    v_key          text;
    v_bad_id       uuid;
    v_current      integer;
    v_live_ids     uuid[];
    v_expected_ids uuid[];
    v_deleted      integer := 0;
    v_inserted     integer := 0;
    v_updated      integer := 0;
BEGIN
    -- 1. Arguments that are wrong whatever the table holds (22023; nothing changed).
    IF p_sense_id IS NULL OR p_expected_version IS NULL OR p_expected_ids IS NULL
       OR p_new_version IS NULL THEN
        RAISE EXCEPTION 'exercise_content_commit: p_sense_id, p_expected_version, p_expected_ids '
                        'and p_new_version are required'
            USING ERRCODE = '22023';
    END IF;
    IF array_position(p_expected_ids, NULL) IS NOT NULL
       OR array_position(v_delete_ids, NULL) IS NOT NULL THEN
        RAISE EXCEPTION 'exercise_content_commit: p_expected_ids and p_delete_ids must not contain NULL'
            USING ERRCODE = '22023';
    END IF;
    IF jsonb_typeof(v_insert_rows) <> 'array' THEN
        RAISE EXCEPTION 'exercise_content_commit: p_insert_rows must be a JSON array'
            USING ERRCODE = '22023';
    END IF;
    IF jsonb_typeof(v_updates) <> 'object' THEN
        RAISE EXCEPTION 'exercise_content_commit: p_update_contents must be a JSON object'
            USING ERRCODE = '22023';
    END IF;
    FOR v_row IN SELECT r.value FROM jsonb_array_elements(v_insert_rows) AS r(value) LOOP
        IF jsonb_typeof(v_row) <> 'object' THEN
            RAISE EXCEPTION 'exercise_content_commit: every insert row must be a JSON object'
                USING ERRCODE = '22023';
        END IF;
        IF v_row ->> 'id' IS NULL THEN
            RAISE EXCEPTION 'exercise_content_commit: insert row without id'
                USING ERRCODE = '22023';
        END IF;
        IF (v_row ->> 'word_sense_id')::integer IS DISTINCT FROM p_sense_id THEN
            RAISE EXCEPTION 'exercise_content_commit: insert row % has word_sense_id %, not %',
                            v_row ->> 'id', v_row ->> 'word_sense_id', p_sense_id
                USING ERRCODE = '22023';
        END IF;
        IF jsonb_typeof(v_row -> 'content') IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'exercise_content_commit: insert row % has no JSON object under "content"',
                            v_row ->> 'id'
                USING ERRCODE = '22023';
        END IF;
    END LOOP;
    FOR v_key, v_row IN SELECT u.key, u.value FROM jsonb_each(v_updates) AS u(key, value) LOOP
        IF jsonb_typeof(v_row) <> 'object' THEN
            RAISE EXCEPTION 'exercise_content_commit: the update for % is not a JSON object', v_key
                USING ERRCODE = '22023';
        END IF;
    END LOOP;

    -- 2. One writer per sense at a time (ADR-047 §4; store.COMMIT_LOCK_NAMESPACE = 47047).
    PERFORM pg_advisory_xact_lock(47047, p_sense_id);

    -- 3. Compare-and-swap. A fresh statement after the lock, so a writer that held the lock
    --    before us is visible here.
    SELECT COALESCE(max(e.content_version), 0),
           COALESCE(array_agg(e.id ORDER BY e.id), '{}')
      INTO v_current, v_live_ids
      FROM public.exercises e
     WHERE e.word_sense_id = p_sense_id;

    IF v_current <> p_expected_version THEN
        RETURN jsonb_build_object('ok', false, 'reason', 'version_conflict',
                                  'current_version', v_current);
    END IF;

    SELECT COALESCE(array_agg(DISTINCT x.id ORDER BY x.id), '{}')
      INTO v_expected_ids
      FROM unnest(p_expected_ids) AS x(id);

    IF v_live_ids IS DISTINCT FROM v_expected_ids THEN
        RETURN jsonb_build_object('ok', false, 'reason', 'rows_changed',
                                  'current_version', v_current);
    END IF;

    -- 4. Arguments checked against the sense's rows (22023; nothing changed).
    IF p_new_version <= v_current THEN
        RAISE EXCEPTION 'exercise_content_commit: p_new_version % is not greater than the current version % of sense %',
                        p_new_version, v_current, p_sense_id
            USING ERRCODE = '22023';
    END IF;
    SELECT d.id INTO v_bad_id
      FROM unnest(v_delete_ids) AS d(id)
     WHERE d.id <> ALL (v_live_ids)
     LIMIT 1;
    IF v_bad_id IS NOT NULL THEN
        RAISE EXCEPTION 'exercise_content_commit: delete id % is not a row of sense %', v_bad_id, p_sense_id
            USING ERRCODE = '22023';
    END IF;
    FOR v_key IN SELECT jsonb_object_keys(v_updates) LOOP
        IF v_key::uuid <> ALL (v_live_ids) THEN
            RAISE EXCEPTION 'exercise_content_commit: update id % is not a row of sense %', v_key, p_sense_id
                USING ERRCODE = '22023';
        END IF;
        IF v_key::uuid = ANY (v_delete_ids) THEN
            RAISE EXCEPTION 'exercise_content_commit: update id % is also deleted', v_key
                USING ERRCODE = '22023';
        END IF;
    END LOOP;

    -- 5. Apply: deletes, inserts, updates, then the version stamp.
    DELETE FROM public.exercises e
     WHERE e.word_sense_id = p_sense_id
       AND e.id = ANY (v_delete_ids);
    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    -- dedupe_key is computed from the JSON passed in, never from the column, so the
    -- post-drop version of this function computes it the same way.
    INSERT INTO public.exercises (
        id, language_id, exercise_type, source_type, word_sense_id,
        corpus_collocation_id, word_asset_id,
        content,
        tags, difficulty_static, complexity_tier, ladder_level, pattern_code,
        is_active, generation_batch_id,
        content_version, dedupe_key
    )
    SELECT r.id, r.language_id, r.exercise_type, r.source_type::public.exercise_source_type,
           r.word_sense_id, r.corpus_collocation_id, r.word_asset_id,
           x.row_json -> 'content',
           COALESCE(r.tags, '{}'::jsonb), r.difficulty_static, r.complexity_tier,
           r.ladder_level, r.pattern_code,
           COALESCE(r.is_active, true), r.generation_batch_id,
           p_new_version,
           CASE WHEN r.exercise_type = ANY (c_context_free)
                THEN md5(coalesce(x.row_json -> 'content' ->> 'context_sentence', ''))
           END
      FROM jsonb_array_elements(v_insert_rows) WITH ORDINALITY AS x(row_json, ord)
     CROSS JOIN LATERAL jsonb_to_record(x.row_json) AS r(
           id                    uuid,
           language_id           integer,
           exercise_type         text,
           source_type           text,
           word_sense_id         integer,
           corpus_collocation_id integer,
           word_asset_id         bigint,
           tags                  jsonb,
           difficulty_static     numeric,
           complexity_tier       text,
           ladder_level          integer,
           pattern_code          text,
           is_active             boolean,
           generation_batch_id   uuid)
     ORDER BY x.ord;
    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    UPDATE public.exercises e
       SET dedupe_key = CASE WHEN e.exercise_type = ANY (c_context_free)
                             THEN md5(coalesce(u.value ->> 'context_sentence', ''))
                        END
         , content = u.value
      FROM jsonb_each(v_updates) AS u(key, value)
     WHERE e.word_sense_id = p_sense_id
       AND e.id = u.key::uuid;
    GET DIAGNOSTICS v_updated = ROW_COUNT;

    UPDATE public.exercises e
       SET content_version = p_new_version
     WHERE e.word_sense_id = p_sense_id
       AND e.content_version IS DISTINCT FROM p_new_version
       AND e.id = ANY (v_live_ids);

    RETURN jsonb_build_object('ok', true, 'version', p_new_version, 'deleted', v_deleted,
                              'inserted', v_inserted, 'updated', v_updated);
END
$$;

CREATE OR REPLACE FUNCTION public.get_practice_session(
    p_user_id           uuid,
    p_language_id       smallint,
    p_mode              text     DEFAULT 'auto',
    p_target_minutes    smallint DEFAULT 15,
    p_user_theta        numeric  DEFAULT NULL,
    p_include_content   boolean  DEFAULT true
) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path = public, pg_temp AS $$
DECLARE
    v_mode            text;
    v_theta           numeric;
    v_weights         jsonb;
    v_alpha           numeric;
    v_beta            numeric;
    v_gamma           numeric;
    v_delta           numeric;
    v_target_seconds  integer;
    v_elapsed_seconds integer := 0;
    v_items           jsonb := '[]'::jsonb;
    v_no_content      text   := NULL;
    v_session_id      uuid   := gen_random_uuid();
    v_due_today       integer;
    v_decayed_count   integer;
    v_active_ladder   integer;
    v_today           date   := CURRENT_DATE;
    v_eligible_count  integer;
    v_word            RECORD;
    v_item            RECORD;
    v_fam             text;
    v_active_levels   integer[] := ARRAY[1,2,3,4,5,6,7,8,9];
BEGIN
    -- =============================================================
    -- 1. Validate inputs
    -- =============================================================
    IF NOT EXISTS (
        SELECT 1 FROM public.dim_languages
        WHERE id = p_language_id AND is_active
    ) THEN
        RETURN jsonb_build_object('error','language_not_active','code','E_LANG');
    END IF;

    IF p_mode NOT IN ('acquisition','maintenance','auto') THEN
        RETURN jsonb_build_object('error','invalid_mode','code','E_MODE');
    END IF;

    IF p_target_minutes IS NULL OR p_target_minutes < 1 OR p_target_minutes > 180 THEN
        RETURN jsonb_build_object('error','target_minutes_out_of_range','code','E_RANGE');
    END IF;

    v_target_seconds := p_target_minutes * 60;

    -- =============================================================
    -- 2. Resolve mode (auto dispatch)
    -- =============================================================
    IF p_mode = 'auto' THEN
        SELECT COUNT(*) INTO v_due_today
        FROM public.user_flashcards fc
        WHERE fc.user_id = p_user_id
          AND fc.language_id = p_language_id
          AND fc.due_date <= v_today;

        SELECT COUNT(*) INTO v_decayed_count
        FROM public.user_vocabulary_knowledge uvk
        LEFT JOIN public.user_flashcards fc
            ON fc.user_id = uvk.user_id AND fc.sense_id = uvk.sense_id
        WHERE uvk.user_id = p_user_id
          AND uvk.language_id = p_language_id
          AND public.bkt_effective_p_known(
                uvk.p_known, uvk.last_evidence_at,
                fc.stability, uvk.evidence_count
              ) < uvk.p_known - 0.05;

        SELECT COUNT(*) INTO v_active_ladder
        FROM public.user_word_ladder uwl
        JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
        JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
        WHERE uwl.user_id = p_user_id
          AND dv.language_id = p_language_id
          AND uwl.word_state IN ('active','gated','pre_mastery','relearning');

        v_mode := CASE
            WHEN (v_due_today + v_decayed_count) >= v_active_ladder
                 AND (v_due_today + v_decayed_count) > 0
                THEN 'maintenance'
            ELSE 'acquisition'
        END;
    ELSE
        v_mode := p_mode;
    END IF;

    -- =============================================================
    -- 3. Resolve theta
    -- =============================================================
    v_theta := COALESCE(p_user_theta,
                        public.irt_compute_user_theta(p_user_id, p_language_id),
                        0.0);

    -- =============================================================
    -- 4. Load mode weights
    -- =============================================================
    SELECT default_weights INTO v_weights
    FROM public.dim_practice_modes
    WHERE name = v_mode AND is_active;

    IF v_weights IS NULL THEN
        -- Should never happen given validation above, but defensive.
        RETURN jsonb_build_object('error','invalid_mode_weights','code','E_WEIGHTS');
    END IF;

    v_alpha := (v_weights->>'alpha')::numeric;
    v_beta  := (v_weights->>'beta' )::numeric;
    v_gamma := (v_weights->>'gamma')::numeric;
    v_delta := (v_weights->>'delta')::numeric;

    -- =============================================================
    -- 5. Run mode loop
    -- =============================================================
    IF v_mode = 'maintenance' THEN
        -- ----- Maintenance candidate pool + ranking -----
        FOR v_item IN
            WITH due_or_decayed AS (
                SELECT DISTINCT
                    uvk.sense_id,
                    fc.stability,
                    fc.due_date,
                    uvk.p_known
                FROM public.user_vocabulary_knowledge uvk
                LEFT JOIN public.user_flashcards fc
                    ON fc.user_id = uvk.user_id AND fc.sense_id = uvk.sense_id
                WHERE uvk.user_id = p_user_id
                  AND uvk.language_id = p_language_id
                  AND (
                      (fc.due_date IS NOT NULL AND fc.due_date <= v_today + 7)
                      OR public.bkt_effective_p_known(
                            uvk.p_known, uvk.last_evidence_at,
                            fc.stability, uvk.evidence_count
                         ) < uvk.p_known - 0.05
                  )
            ),
            top_senses AS (
                SELECT *,
                    GREATEST(0, (v_today - due_date)::numeric
                              / NULLIF(stability, 0)) AS urg
                FROM due_or_decayed
                ORDER BY urg DESC NULLS LAST, sense_id
                LIMIT 200
            ),
            candidates AS (
                SELECT
                    e.id            AS exercise_id,
                    e.word_sense_id AS sense_id,
                    e.exercise_type,
                    CASE WHEN p_include_content THEN e.content END AS content,
                    e.content_version,
                    e.ladder_level,
                    public.ladder_get_family(e.ladder_level) AS family,
                    COALESCE(det.expected_seconds_p50::int,
                             det.expected_seconds, 45) AS expected_seconds,
                    e.irt_discrimination,
                    e.irt_difficulty,
                    s.stability,
                    s.due_date,
                    s.p_known,
                    uwl.family_confidence,
                    uwl.current_ring,
                    uwl.word_state,
                    uwl.review_due_at,
                    uwl.last_exercised_family,
                    public.practice_unified_score(
                        e.irt_discrimination, e.irt_difficulty, v_theta,
                        s.p_known,
                        s.due_date, s.stability, v_today,
                        CASE WHEN uwl.sense_id IS NULL THEN 0
                             ELSE public.ladder_compute_priority(
                                uwl.current_ring, uwl.word_state,
                                uwl.family_confidence, uwl.review_due_at,
                                uwl.last_exercised_family
                             )
                        END,
                        v_alpha, v_beta, v_gamma, v_delta
                    ) AS score
                FROM top_senses s
                JOIN public.exercises e
                    ON e.word_sense_id = s.sense_id
                   AND e.language_id   = p_language_id
                   AND e.is_active
                   AND e.word_sense_id IS NOT NULL
                LEFT JOIN public.dim_exercise_types det
                    ON det.type_code = e.exercise_type
                LEFT JOIN public.user_word_ladder uwl
                    ON uwl.user_id = p_user_id AND uwl.sense_id = e.word_sense_id
            )
            SELECT * FROM candidates
            ORDER BY score DESC
            LIMIT 60                    -- enough to cover 60×30s = 30 min budget
        LOOP
            EXIT WHEN v_elapsed_seconds >= v_target_seconds;
            v_items := v_items || jsonb_build_object(
                'exercise_id',      v_item.exercise_id,
                'sense_id',         v_item.sense_id,
                'exercise_type',    v_item.exercise_type,
                'family',           v_item.family,
                'content_version',  v_item.content_version,
                'ladder_level',     v_item.ladder_level,
                'p_known',          v_item.p_known,
                'expected_seconds', v_item.expected_seconds,
                'mode',             'maintenance'
            );
            -- content only when p_include_content: added to the item just appended
            IF p_include_content THEN v_items := jsonb_set(v_items, '{-1,content}', COALESCE(v_item.content, 'null'::jsonb)); END IF;
            v_elapsed_seconds := v_elapsed_seconds + v_item.expected_seconds;
        END LOOP;

        -- ----- Fall-through: if Maintenance dry, continue in Acquisition -----
        IF v_elapsed_seconds < v_target_seconds AND jsonb_array_length(v_items) < 60 THEN
            -- Mark fall-through; continue inline with Acquisition logic
            v_mode := 'acquisition';
            -- Reload weights to Acquisition values for the fall-through items
            SELECT default_weights INTO v_weights
            FROM public.dim_practice_modes WHERE name = 'acquisition';
            v_alpha := (v_weights->>'alpha')::numeric;
            v_beta  := (v_weights->>'beta' )::numeric;
            v_gamma := (v_weights->>'gamma')::numeric;
            v_delta := (v_weights->>'delta')::numeric;
        END IF;
    END IF;

    -- =============================================================
    -- Acquisition path (also runs as fall-through from Maintenance)
    -- =============================================================
    IF v_mode = 'acquisition' AND v_elapsed_seconds < v_target_seconds THEN
        -- Count eligible words for the no-content check.
        -- FIX: scoped to p_language_id via dim_word_senses -> dim_vocabulary
        -- (user_word_ladder has no language of its own — a learner's ladder
        -- row in one language must not mask an empty ladder in another).
        SELECT COUNT(*) INTO v_eligible_count
        FROM public.user_word_ladder uwl
        JOIN public.dim_word_senses dws ON dws.id = uwl.sense_id
        JOIN public.dim_vocabulary  dv  ON dv.id  = dws.vocab_id
        WHERE uwl.user_id = p_user_id
          AND dv.language_id = p_language_id
          AND uwl.word_state IN ('new','active','gated','pre_mastery','relearning')
          AND COALESCE(uwl.review_due_at, '1970-01-01'::timestamptz) <= now();

        IF v_eligible_count = 0 THEN
            -- Caller (Python service) is expected to auto-subscribe from packs
            -- per R4.9 before calling, but if it didn't, we return a marker so
            -- the FE can show the "select a pack" nudge.
            IF jsonb_array_length(v_items) = 0 THEN
                v_no_content := 'no_eligible_words';
            END IF;
        ELSE
            -- Word-anchored loop: top 50 by priority
            FOR v_word IN
                SELECT
                    uwl.sense_id,
                    uwl.current_ring,
                    uwl.word_state,
                    uwl.family_confidence,
                    uwl.review_due_at,
                    uwl.last_exercised_family,
                    uwl.active_levels,
                    public.ladder_compute_priority(
                        uwl.current_ring, uwl.word_state,
                        uwl.family_confidence, uwl.review_due_at,
                        uwl.last_exercised_family
                    ) AS priority
                FROM public.user_word_ladder uwl
                WHERE uwl.user_id = p_user_id
                  AND uwl.word_state IN ('new','active','gated','pre_mastery','relearning')
                  AND COALESCE(uwl.review_due_at, '1970-01-01'::timestamptz) <= now()
                  AND EXISTS (
                    SELECT 1 FROM public.exercises e
                    WHERE e.word_sense_id = uwl.sense_id
                      AND e.language_id = p_language_id
                      AND e.is_active
                      AND e.ladder_level IS NOT NULL
                  )
                ORDER BY priority DESC
                LIMIT 50
            LOOP
                EXIT WHEN v_elapsed_seconds >= v_target_seconds;

                -- For each ring-required family, pick the top-scored item
                FOREACH v_fam IN ARRAY
                    public.ladder_ring_families(
                        v_word.current_ring,
                        COALESCE(v_word.active_levels, v_active_levels)
                    )
                LOOP
                    EXIT WHEN v_elapsed_seconds >= v_target_seconds;

                    SELECT
                        e.id        AS exercise_id,
                        e.exercise_type,
                        CASE WHEN p_include_content THEN e.content END AS content,
                        e.content_version,
                        e.ladder_level,
                        public.ladder_get_family(e.ladder_level) AS family,
                        COALESCE(det.expected_seconds_p50::int,
                                 det.expected_seconds, 45) AS expected_seconds,
                        uvk.p_known
                    INTO v_item
                    FROM public.exercises e
                    LEFT JOIN public.dim_exercise_types det
                        ON det.type_code = e.exercise_type
                    LEFT JOIN public.user_vocabulary_knowledge uvk
                        ON uvk.user_id = p_user_id AND uvk.sense_id = e.word_sense_id
                    LEFT JOIN public.user_flashcards fc
                        ON fc.user_id = p_user_id AND fc.sense_id = e.word_sense_id
                    WHERE e.word_sense_id = v_word.sense_id
                      AND e.language_id   = p_language_id
                      AND e.is_active
                      AND e.ladder_level IS NOT NULL
                      AND public.ladder_get_family(e.ladder_level) = v_fam
                      -- Anti-repetition: not seen today
                      AND NOT EXISTS (
                        SELECT 1 FROM public.user_exercise_history ueh
                        WHERE ueh.user_id = p_user_id
                          AND ueh.exercise_id = e.id
                          AND ueh.session_date = v_today
                      )
                    ORDER BY public.practice_unified_score(
                        e.irt_discrimination, e.irt_difficulty, v_theta,
                        uvk.p_known,
                        fc.due_date, fc.stability, v_today,
                        v_word.priority,
                        v_alpha, v_beta, v_gamma, v_delta
                    ) DESC,
                    RANDOM()
                    LIMIT 1;

                    IF FOUND THEN
                        v_items := v_items || jsonb_build_object(
                            'exercise_id',      v_item.exercise_id,
                            'sense_id',         v_word.sense_id,
                            'exercise_type',    v_item.exercise_type,
                            'family',           v_item.family,
                            'content_version',  v_item.content_version,
                            'ladder_level',     v_item.ladder_level,
                            'p_known',          v_item.p_known,
                            'expected_seconds', v_item.expected_seconds,
                            'mode',             'acquisition'
                        );
                        -- content only when p_include_content: added to the item just appended
                        IF p_include_content THEN v_items := jsonb_set(v_items, '{-1,content}', COALESCE(v_item.content, 'null'::jsonb)); END IF;
                        v_elapsed_seconds := v_elapsed_seconds + v_item.expected_seconds;
                    END IF;
                END LOOP;

                -- Gate marker: word is gated → caller dispatches via
                -- /api/vocab-dojo/gate with the appropriate gate_name.
                IF v_word.word_state = 'gated'
                   AND v_elapsed_seconds < v_target_seconds THEN
                    v_items := v_items || jsonb_build_object(
                        'is_gate_marker',  true,
                        'gate_name',
                            CASE WHEN v_word.current_ring = 2 THEN 'gate_a'
                                 WHEN v_word.current_ring = 3 THEN 'gate_b'
                                 ELSE 'unknown' END,
                        'sense_id',        v_word.sense_id,
                        'expected_seconds', 180,
                        'mode',            'acquisition'
                    );
                    v_elapsed_seconds := v_elapsed_seconds + 180;
                END IF;

                -- Stress-test marker: word is in pre_mastery → caller
                -- dispatches via /api/vocab-dojo/stress-test.
                IF v_word.word_state = 'pre_mastery'
                   AND v_elapsed_seconds < v_target_seconds THEN
                    v_items := v_items || jsonb_build_object(
                        'is_stress_test_marker', true,
                        'sense_id',              v_word.sense_id,
                        'expected_seconds',      420,
                        'mode',                  'acquisition'
                    );
                    v_elapsed_seconds := v_elapsed_seconds + 420;
                END IF;
            END LOOP;
        END IF;
    END IF;

    -- =============================================================
    -- 6. Assemble final response
    -- =============================================================
    IF jsonb_array_length(v_items) = 0 AND v_no_content IS NULL THEN
        v_no_content := 'all_complete';
    END IF;

    RETURN jsonb_build_object(
        'session_id',       v_session_id,
        'mode_requested',   p_mode,
        'mode_resolved',    v_mode,
        'target_minutes',   p_target_minutes,
        'elapsed_seconds',  v_elapsed_seconds,
        'items',            v_items,
        'no_content_reason', v_no_content
    );
END $$;

CREATE OR REPLACE FUNCTION public.get_review_ahead_items(
    p_user_id                  uuid,
    p_language_id              smallint,
    p_limit                    integer   DEFAULT 10,
    p_exclude_recent_minutes   integer   DEFAULT 10,
    p_exclude_sense_ids        integer[] DEFAULT '{}',
    p_include_content          boolean   DEFAULT true
) RETURNS jsonb LANGUAGE sql VOLATILE
SET search_path = public, pg_temp
AS $$
    WITH recent AS (
        SELECT DISTINCT ea.sense_id
        FROM public.exercise_attempts ea
        WHERE ea.user_id = p_user_id
          AND ea.sense_id IS NOT NULL
          AND ea.created_at >= now() - make_interval(mins => GREATEST(p_exclude_recent_minutes, 0))
    ),
    pool AS (
        SELECT
            fc.sense_id,
            fc.due_date,
            uvk.p_known,
            public.bkt_effective_p_known(
                COALESCE(uvk.p_known, 0.10), uvk.last_evidence_at,
                fc.stability, COALESCE(uvk.evidence_count, 0)
            ) AS eff_p_known
        FROM public.user_flashcards fc
        LEFT JOIN public.user_vocabulary_knowledge uvk
            ON uvk.user_id = fc.user_id AND uvk.sense_id = fc.sense_id
        WHERE fc.user_id = p_user_id
          AND fc.language_id = p_language_id
          AND COALESCE(fc.reps, 0) > 0
          AND fc.sense_id <> ALL (COALESCE(p_exclude_sense_ids, '{}'))
          AND NOT EXISTS (SELECT 1 FROM recent r WHERE r.sense_id = fc.sense_id)
        ORDER BY eff_p_known ASC NULLS FIRST, fc.due_date ASC NULLS LAST, fc.sense_id
        LIMIT GREATEST(LEAST(p_limit, 50), 0)
    ),
    last_seen AS (
        SELECT ea.exercise_id, max(ea.created_at) AS seen_at
        FROM public.exercise_attempts ea
        JOIN pool p ON p.sense_id = ea.sense_id
        WHERE ea.user_id = p_user_id
        GROUP BY ea.exercise_id
    ),
    picked AS (
        SELECT DISTINCT ON (p.sense_id)
            e.id            AS exercise_id,
            p.sense_id,
            e.exercise_type,
            CASE WHEN p_include_content THEN e.content END AS content,
            e.content_version,
            e.ladder_level,
            public.ladder_get_family(e.ladder_level) AS family,
            p.p_known,
            p.eff_p_known,
            p.due_date,
            COALESCE(det.expected_seconds_p50::int, det.expected_seconds, 45) AS expected_seconds
        FROM pool p
        JOIN public.exercises e
            ON e.word_sense_id = p.sense_id
           AND e.language_id   = p_language_id
           AND e.is_active
        LEFT JOIN public.dim_exercise_types det ON det.type_code = e.exercise_type
        LEFT JOIN last_seen ls ON ls.exercise_id = e.id
        ORDER BY p.sense_id, ls.seen_at ASC NULLS FIRST, random()
    )
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'exercise_id',      exercise_id,
        'sense_id',         sense_id,
        'exercise_type',    exercise_type,
        'family',           family,
        'content_version',  content_version
    ) || CASE WHEN p_include_content THEN jsonb_build_object('content', content) ELSE '{}'::jsonb END || jsonb_build_object(
        'ladder_level',     ladder_level,
        'p_known',          p_known,
        'expected_seconds', expected_seconds,
        'mode',             'maintenance',
        'review_ahead',     true
    ) ORDER BY eff_p_known ASC NULLS FIRST, due_date ASC NULLS LAST, sense_id), '[]'::jsonb)
    FROM picked;
$$;

REVOKE ALL ON FUNCTION public.exercise_content_commit(integer, integer, uuid[], integer, uuid[], jsonb, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.exercise_content_commit(integer, integer, uuid[], integer, uuid[], jsonb, jsonb) TO service_role;
REVOKE ALL ON FUNCTION public.get_practice_session(uuid, smallint, text, smallint, numeric, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_practice_session(uuid, smallint, text, smallint, numeric, boolean) TO service_role;
REVOKE ALL ON FUNCTION public.get_review_ahead_items(uuid, smallint, integer, integer, integer[], boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_review_ahead_items(uuid, smallint, integer, integer, integer[], boolean) TO service_role;

COMMENT ON FUNCTION public.exercise_content_commit(integer, integer, uuid[], integer, uuid[], jsonb, jsonb) IS
    'ADR-047 §4/§8: compare-and-swap commit of one sense (pre-drop version, restored by '
    'exercise_content_drop_column_rollback.sql): also writes exercises.content.';
COMMENT ON FUNCTION public.get_practice_session(uuid, smallint, text, smallint, numeric, boolean) IS
    'Unified Practice surface (ADR-047 pre-drop version, restored by '
    'exercise_content_drop_column_rollback.sql): items carry content_version; content only when '
    'p_include_content.';
COMMENT ON FUNCTION public.get_review_ahead_items(uuid, smallint, integer, integer, integer[], boolean) IS
    'Practice extra rounds: review-ahead items (ADR-047 pre-drop version, restored by '
    'exercise_content_drop_column_rollback.sql): items carry content_version; content only when '
    'p_include_content.';

NOTIFY pgrst, 'reload schema';

COMMIT;


-- =============================================================================
-- STEP R2 — refill exercises.content (outside SQL).
-- =============================================================================
-- For every row: content = the entry for its id in the file of its (word_sense_id,
-- content_version) — store.fetch_sense(language_id, word_sense_id, content_version) — which
-- includes every write made after the cut-over; rows whose file is missing come from the
-- _archive/exercises-content-<TAG>/ export taken on cut-over day (not taken: TASK-1030 skipped
-- --archive-all, every row had a verified file). No script does this yet (TASK-1023's backfill
-- only exported and verified, and was retired in TASK-1031): write one before relying on this
-- rollback.
-- It must update in batches of <= 2,000 rows with a plain VACUUM public.exercises between
-- batches (the same reasoning as step 1 of the cut-over).


-- =============================================================================
-- STEP R3 — read-only check: expect 0 before going on.
-- =============================================================================
SELECT count(*) AS rows_without_content FROM public.exercises WHERE content IS NULL;


-- =============================================================================
-- STEP R4 — NOT NULL again, without a long exclusive lock: a NOT VALID check is validated
-- under SHARE UPDATE EXCLUSIVE, then SET NOT NULL uses it instead of scanning the table.
-- Run each statement on its own.
-- =============================================================================
ALTER TABLE public.exercises
    ADD CONSTRAINT exercises_content_not_null_rollback CHECK (content IS NOT NULL) NOT VALID;
ALTER TABLE public.exercises VALIDATE CONSTRAINT exercises_content_not_null_rollback;
ALTER TABLE public.exercises ALTER COLUMN content SET NOT NULL;
ALTER TABLE public.exercises DROP CONSTRAINT exercises_content_not_null_rollback;


-- =============================================================================
-- STEP R5 — the original content-expression unique index (outside any transaction block;
-- run it alone), exactly as migrations/task743_context_free_exercise_caps.sql defines it.
-- =============================================================================
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_exercises_context_free_variant
    ON public.exercises (
        word_sense_id,
        exercise_type,
        md5(coalesce(content->>'context_sentence', ''))
    )
    WHERE is_active
      AND word_sense_id IS NOT NULL
      AND exercise_type IN (
      'tone_id_word', 'hanzi_to_pinyin', 'pinyin_to_hanzi',
      'kanji_to_reading', 'reading_to_kanji', 'phonetic_recognition',
      'classifier_match', 'counter_match');

-- Expect indisvalid = true (otherwise DROP INDEX CONCURRENTLY it, fix, and repeat R5).
SELECT c.relname, i.indisvalid
  FROM pg_index i
  JOIN pg_class c ON c.oid = i.indexrelid
 WHERE i.indexrelid = to_regclass('public.uq_exercises_context_free_variant');
