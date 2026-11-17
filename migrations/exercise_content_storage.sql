-- =============================================================================
-- exercise_content_storage.sql — ADR-049 Phase 1: content versions, the version sequence,
-- the write-side RPCs and the private Storage bucket for exercise content.
-- Date: 2026-11-17   Task: TASK-1016
-- Spec: wiki/decisions/ADR-049-exercise-content-in-storage.md
--       (§3 versions, §4 concurrency rule, §7 schema changes, §8 RPC contract — normative)
--
-- STATUS: applied live 2026-11-17 (TASK-1026, Supabase migration `exercise_content_storage`);
-- function bodies and comments md5-checked against this file after the apply.
--
-- Apply order (staging first if one exists):
--   1. migrations/exercise_content_storage.sql        (this file)
--   2. migrations/exercise_content_session_rpcs.sql
-- Both are inert while EXERCISE_CONTENT_SOURCE=db and EXERCISE_CONTENT_WRITE=db: nothing calls
-- the new functions and nothing reads the new columns until the flags change.
--
-- Additive only. No existing row of public.exercises is rewritten: the database is ~30 MB under
-- the 500 MB Free cap, and an UPDATE of its 144k rows would write ~190 MB of new row versions.
--   * exercises.content_version integer NOT NULL DEFAULT 0. Version 0 is the backfill export;
--     the constant default makes ADD COLUMN a catalog-only change.
--   * exercises.dedupe_key text, NULL. exercise_content_commit fills it for the 8 context-free
--     types of uq_exercises_context_free_variant from the JSON it is given; the cut-over
--     (exercise_content_drop_column.sql) backfills the remaining rows in batches and builds
--     uq_exercises_context_free_variant_v2 on it before the content column goes.
--   * public.exercise_content_version_seq: every version after 0 (global, increasing, gaps
--     allowed), so every file name {lang}/{sense}.v{version}.json is written once.
--   * exercise_content_begin / exercise_content_commit / exercise_content_live_versions
--     (SECURITY INVOKER, service_role only).
--   * the private bucket exercise-content (1 MB per file, application/json).
--
-- Rollback: migrations/exercise_content_storage_rollback.sql. Valid ONLY before
-- EXERCISE_CONTENT_WRITE=dual was ever set in any environment: after that, rows carry versions
-- whose files exist only in Storage. Roll back exercise_content_session_rpcs.sql first (its
-- functions read exercises.content_version).
-- Renumbered 2026-11-17 when merged with main: ADR-047 -> ADR-049 and TASK-976..999 ->
-- TASK-1008..1031 (main already used those ids). Function bodies and COMMENT strings keep
-- the old ids: they are (or will be) the live text, md5-compared against the database.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Columns (catalog-only: constant default, no table rewrite)
-- -----------------------------------------------------------------------------
ALTER TABLE public.exercises
    ADD COLUMN IF NOT EXISTS content_version integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS dedupe_key text;

COMMENT ON COLUMN public.exercises.content_version IS
    'ADR-047: version of the Storage file holding this row''s content '
    '(exercise-content/{lang}/{word_sense_id}.v{content_version}.json). 0 = backfill export; '
    'later versions come from exercise_content_version_seq via exercise_content_commit.';
COMMENT ON COLUMN public.exercises.dedupe_key IS
    'ADR-047: md5(coalesce(content->>''context_sentence'','''')) for the 8 context-free types '
    '(set by exercise_content_commit; backfilled at the cut-over); NULL otherwise. Replaces the '
    'content expression of uq_exercises_context_free_variant (v2 index).';

-- -----------------------------------------------------------------------------
-- 2. Version sequence
-- -----------------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS public.exercise_content_version_seq AS integer START WITH 1;

REVOKE ALL ON SEQUENCE public.exercise_content_version_seq FROM PUBLIC, anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.exercise_content_version_seq TO service_role;

COMMENT ON SEQUENCE public.exercise_content_version_seq IS
    'ADR-047: exercise content versions after 0. Global and increasing, gaps allowed; drawn by '
    'exercise_content_begin.';

-- -----------------------------------------------------------------------------
-- 3. exercise_content_begin — current version, a fresh version and the sense's rows
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.exercise_content_begin(p_sense_id integer)
RETURNS jsonb
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_current integer;
    v_rows    jsonb;
BEGIN
    IF p_sense_id IS NULL THEN
        RAISE EXCEPTION 'exercise_content_begin: p_sense_id is required'
            USING ERRCODE = '22023';
    END IF;

    -- One statement, so current_version and rows come from the same snapshot.
    SELECT COALESCE(max(e.content_version), 0),
           COALESCE(jsonb_agg(jsonb_build_object(
               'id',              e.id,
               'language_id',     e.language_id,
               'exercise_type',   e.exercise_type,
               'ladder_level',    e.ladder_level,
               'word_asset_id',   e.word_asset_id,
               'is_active',       e.is_active,
               'content_version', e.content_version
           ) ORDER BY e.id), '[]'::jsonb)
      INTO v_current, v_rows
      FROM public.exercises e
     WHERE e.word_sense_id = p_sense_id;

    RETURN jsonb_build_object(
        'sense_id',        p_sense_id,
        'current_version', v_current,
        'new_version',     nextval('public.exercise_content_version_seq')::integer,
        'rows',            v_rows
    );
END
$$;

REVOKE ALL ON FUNCTION public.exercise_content_begin(integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.exercise_content_begin(integer) TO service_role;

COMMENT ON FUNCTION public.exercise_content_begin(integer) IS
    'ADR-047 §8 (TASK-984): step 1 of store.write_sense in dual mode. Returns {sense_id, '
    'current_version (max content_version of the sense, 0 when it has no rows), new_version '
    '(nextval of exercise_content_version_seq), rows: [{id, language_id, exercise_type, '
    'ladder_level, word_asset_id, is_active, content_version}] ordered by id}. Takes no lock.';

-- -----------------------------------------------------------------------------
-- 4. exercise_content_commit — compare-and-swap commit of one sense
-- -----------------------------------------------------------------------------
-- Under pg_advisory_xact_lock(47047, sense): the sense must still be at p_expected_version
-- with exactly the row ids p_expected_ids (what exercise_content_begin returned); otherwise
-- {"ok": false, "reason": "version_conflict" | "rows_changed"} and nothing changes. Then
-- deletes, inserts and content updates are applied and every row of the sense is stamped with
-- p_new_version, in the caller's transaction (one PostgREST call = one transaction).
-- The rows stamped are exactly the ones checked (plus the inserts), so a row inserted outside
-- the store while this runs keeps its own version instead of being stamped with a version
-- whose file does not contain it.
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

REVOKE ALL ON FUNCTION public.exercise_content_commit(integer, integer, uuid[], integer, uuid[], jsonb, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.exercise_content_commit(integer, integer, uuid[], integer, uuid[], jsonb, jsonb) TO service_role;

COMMENT ON FUNCTION public.exercise_content_commit(integer, integer, uuid[], integer, uuid[], jsonb, jsonb) IS
    'ADR-047 §4/§8 (TASK-984): compare-and-swap commit of one sense under '
    'pg_advisory_xact_lock(47047, sense). Lost race: {ok:false, reason: version_conflict | '
    'rows_changed, current_version}, nothing changed. Success: deletes p_delete_ids, inserts '
    'p_insert_rows (content_version := p_new_version, dedupe_key from row->content), applies '
    'p_update_contents {uuid: content} (recomputing dedupe_key), stamps p_new_version on the '
    'sense''s rows; returns {ok:true, version, deleted, inserted, updated}. Bad input raises '
    'SQLSTATE 22023. Pre-drop version: also writes exercises.content.';

-- -----------------------------------------------------------------------------
-- 5. exercise_content_live_versions — {sense_id: [versions]} for one language
-- -----------------------------------------------------------------------------
-- One jsonb value, so PostgREST's 1,000-row cap does not apply (backfill and sweep).
CREATE OR REPLACE FUNCTION public.exercise_content_live_versions(p_language_id integer)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
    SELECT COALESCE(jsonb_object_agg(v.word_sense_id::text, v.versions), '{}'::jsonb)
      FROM (
          SELECT e.word_sense_id,
                 jsonb_agg(DISTINCT e.content_version ORDER BY e.content_version) AS versions
            FROM public.exercises e
           WHERE e.language_id = p_language_id
             AND e.word_sense_id IS NOT NULL
           GROUP BY e.word_sense_id
      ) v;
$$;

REVOKE ALL ON FUNCTION public.exercise_content_live_versions(integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.exercise_content_live_versions(integer) TO service_role;

COMMENT ON FUNCTION public.exercise_content_live_versions(integer) IS
    'ADR-047 §8 (TASK-984): {"<sense_id>": [<content_version>, ...ascending]} over every row of '
    'the language that has a sense (active or not). Used by the backfill and the orphan-file sweep.';

-- -----------------------------------------------------------------------------
-- 6. Private bucket (read and written with the service key only; no signed URLs)
-- -----------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('exercise-content', 'exercise-content', false, 1048576, ARRAY['application/json'])
ON CONFLICT (id) DO NOTHING;

NOTIFY pgrst, 'reload schema';

COMMIT;
