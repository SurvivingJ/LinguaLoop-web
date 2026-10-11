-- ============================================================================
-- Dual Translation — one-time v5 -> v6 history rewrite + restore (TASK-852)
-- Date: 2026-10-04
--
-- INERT ON APPLY: this file only CREATE OR REPLACEs three functions. Nothing
-- runs until the TASK-853 cutover calls them through
-- scripts/dt_rewrite_history_v6.py (--apply / --rehearse / --restore).
--
-- ADR-031 user decisions 2026-10-04: (2) split v5 types bulk-remapped to the
-- closest v6 type with remap_flag; (3) ONE-TIME rewrite of every historical
-- record to v6 names, snapshot first, rollback = restore snapshot + revert the
-- taxonomy version; (4) ja script_choice profile entries, error instances and
-- cards (+ those cards' dt_card_review rows) deleted after the snapshot. Past
-- dt_grade bands are NOT recalculated: dt_grade / dt_submission are untouched.
--
-- Division of labour: the Python planner (scripts/dt_rewrite_history_v6.py,
-- plan_rewrite) decides every row's outcome — v6 slug, remap_flag, merge
-- survivor, summed count, severity_rank (synthesis.severity_rank) and trend
-- (synthesis.build_trend) — and passes it as p_plan. These functions own the
-- transaction (PostgREST cannot run multi-statement transactions) and refuse
-- anything the plan did not foresee:
--
-- dt_rewrite_history_v6(p_plan jsonb, p_dry_run boolean DEFAULT true) -> jsonb
--   1. Target version must be seeded, and ACTIVE unless p_dry_run.
--   2. LOCK the four tables IN EXCLUSIVE MODE (reads continue; grading inserts
--      and card reviews wait for the few ms the rewrite takes).
--   3. Empty plan -> verify the DB is already clean (post-conditions) and
--      return 'noop' WITHOUT touching the snapshot (so a second run is a no-op).
--   4. Fail closed: any snapshot table non-empty (no double snapshot); any
--      plan row whose current subtype / taxonomy_version / profile_entry_id no
--      longer matches what the planner read (stale plan); an id in both an
--      update and a delete list; a target slug outside the v6 pair lists; a
--      source column missing from its LIKE-frozen snapshot table.
--   5. Snapshot (same transaction, before any change) into the TASK-842 tables.
--   6. Writes, child-first because every FK is NO ACTION: reviews -> cards
--      deleted -> cards updated/repointed -> profile entries deleted (dropped +
--      merged-away, after their cards moved) -> profile entries updated ->
--      error instances deleted -> error instances updated. Each statement's row
--      count must equal its plan list length.
--   7. Post-conditions (raise = rollback): 0 covered rows with a subtype
--      outside the v6 pair lists or a taxonomy_version <> 6; 0 rows on a dropped
--      slug (script_choice); 0 cards whose subtype <> their profile entry's.
--   8. p_dry_run -> everything above runs, then the sub-block is rolled back
--      (custom SQLSTATE 'DTDRY') and the would-be result is returned.
--
-- dt_restore_history_v5(p_confirm_drop_snapshot boolean DEFAULT false,
--                       p_dry_run boolean DEFAULT false) -> jsonb
--   Parent-first: re-insert deleted error instances (OVERRIDING SYSTEM VALUE —
--   ids are GENERATED ALWAYS) -> restore updated error rows' subtype /
--   taxonomy_version / remap_flag -> restore updated profile rows' subtype /
--   count / severity_rank / trend / remediation_status / taxonomy_version /
--   remap_flag -> re-insert deleted profile rows -> restore cards' subtype /
--   profile_entry_id / taxonomy_version -> re-insert deleted cards -> re-insert
--   deleted reviews. Only snapshot ids are touched: rows created after the
--   cutover keep their v6 slugs, and a card's post-cutover FSRS progress is not
--   rolled back — but a snapshot PROFILE row's count / severity_rank / trend /
--   remediation_status return to the snapshot, so profile progress since the
--   cutover is lost. Clean only before new DT traffic; after that the policy is
--   fix-forward (TASK-853/854, ADR-031). Refuses (before any write) when a v5
--   profile key is now held by a post-cutover row (composite UNIQUE guard).
--   Idempotent (updates are absolute, inserts skip present ids).
--   Truncates the five snapshot tables only with p_confirm_drop_snapshot.
--
-- Runbook position (TASK-853): after dt_taxonomy_v6_columns.sql,
-- dt_taxonomy_v6_seed.sql and dt_taxonomy_v6_activate.sql, with the nightly
-- synthesis cron paused and the app restarted.
--
-- Depends on: dual_translation_groundwork.sql, dt_error_profile.sql,
-- dt_cards.sql, dt_taxonomy_v6_columns.sql (columns + snapshot tables),
-- dt_taxonomy_v6_seed.sql (legacy_aliases + pairs read at call time).
-- Supabase roles: EXECUTE revoked from PUBLIC/anon/authenticated, granted to
-- service_role (guarded, so the file also applies to a plain local Postgres —
-- the TASK-852 integration test in tests/test_dt_rewrite_history_v6.py).
--
-- SEARCH-BEFORE-ARCHIVE (migrations/CLAUDE.md): new functions only; nothing
-- defined elsewhere is redefined.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- Helper: quoted, attnum-ordered list of the source columns that also exist in
-- the snapshot table (explicit column lists — the snapshot tables are
-- LIKE-frozen, TASK-842 note). p_missing_only => the source columns MISSING
-- from the snapshot instead (non-NULL result = refuse to snapshot).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.dt_rewrite_snapshot_columns(
    p_src regclass, p_snap regclass, p_missing_only boolean DEFAULT false
)
RETURNS text
LANGUAGE sql
STABLE
SET search_path = public, pg_temp
AS $fn$
    SELECT string_agg(quote_ident(a.attname), ', ' ORDER BY a.attnum)
    FROM pg_attribute a
    WHERE a.attrelid = p_src
      AND a.attnum > 0
      AND NOT a.attisdropped
      AND a.attgenerated = ''
      AND EXISTS (
          SELECT 1 FROM pg_attribute b
          WHERE b.attrelid = p_snap AND b.attname = a.attname
            AND b.attnum > 0 AND NOT b.attisdropped
      ) <> p_missing_only;
$fn$;

-- ----------------------------------------------------------------------------
-- Apply
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.dt_rewrite_history_v6(
    p_plan jsonb, p_dry_run boolean DEFAULT true
)
RETURNS jsonb
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $fn$
DECLARE
    v_target    integer := (p_plan->>'taxonomy_version')::integer;
    v_tax       jsonb;
    v_active    boolean;
    v_slugs     text[];
    v_dropped   text[];
    v_bad       text;
    v_n         bigint;
    v_cols      text;
    v_counts    jsonb := '{}'::jsonb;
    v_result    jsonb;
    -- id arrays per plan list
    v_ei_upd    bigint[];
    v_ei_del    bigint[];
    v_pe_upd    bigint[];
    v_pe_del    bigint[];
    v_cd_upd    bigint[];
    v_cd_del    bigint[];
    v_rv_del    bigint[];
    k           text;
BEGIN
    IF v_target IS DISTINCT FROM 6 THEN
        RAISE EXCEPTION 'dt_rewrite_history_v6: plan targets taxonomy_version %, expected 6', v_target;
    END IF;
    SELECT taxonomy, is_active INTO v_tax, v_active
    FROM public.dt_taxonomy_version WHERE version = v_target;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'dt_rewrite_history_v6: dt_taxonomy_version % is not seeded', v_target;
    END IF;
    IF NOT v_active AND NOT p_dry_run THEN
        RAISE EXCEPTION 'dt_rewrite_history_v6: taxonomy v% is not active — activate it first (TASK-853 runbook)', v_target;
    END IF;

    SELECT array_agg(DISTINCT s) INTO v_slugs
    FROM jsonb_each(v_tax->'pairs') AS p(key, val),
         jsonb_array_elements_text(p.val->'subtypes') AS s;
    SELECT coalesce(array_agg(a.key), '{}') INTO v_dropped
    FROM jsonb_each(v_tax->'legacy_aliases') AS a(key, val)
    WHERE a.val->'to' IS NULL OR jsonb_typeof(a.val->'to') = 'null';
    IF v_slugs IS NULL THEN
        RAISE EXCEPTION 'dt_rewrite_history_v6: taxonomy v% has no pair lists', v_target;
    END IF;

    LOCK TABLE public.dt_error_instance, public.dt_error_profile_entry,
               public.dt_card, public.dt_card_review IN EXCLUSIVE MODE;

    SELECT coalesce(array_agg((x->>'id')::bigint), '{}') INTO v_ei_upd FROM jsonb_array_elements(coalesce(p_plan->'error_updates',   '[]')) x;
    SELECT coalesce(array_agg((x->>'id')::bigint), '{}') INTO v_ei_del FROM jsonb_array_elements(coalesce(p_plan->'error_deletes',   '[]')) x;
    SELECT coalesce(array_agg((x->>'id')::bigint), '{}') INTO v_pe_upd FROM jsonb_array_elements(coalesce(p_plan->'profile_updates', '[]')) x;
    SELECT coalesce(array_agg((x->>'id')::bigint), '{}') INTO v_pe_del FROM jsonb_array_elements(coalesce(p_plan->'profile_deletes', '[]')) x;
    SELECT coalesce(array_agg((x->>'id')::bigint), '{}') INTO v_cd_upd FROM jsonb_array_elements(coalesce(p_plan->'card_updates',    '[]')) x;
    SELECT coalesce(array_agg((x->>'id')::bigint), '{}') INTO v_cd_del FROM jsonb_array_elements(coalesce(p_plan->'card_deletes',    '[]')) x;
    SELECT coalesce(array_agg((x->>'id')::bigint), '{}') INTO v_rv_del FROM jsonb_array_elements(coalesce(p_plan->'review_deletes',  '[]')) x;

    v_counts := jsonb_build_object(
        'error_updates', cardinality(v_ei_upd), 'error_deletes', cardinality(v_ei_del),
        'profile_updates', cardinality(v_pe_upd), 'profile_deletes', cardinality(v_pe_del),
        'card_updates', cardinality(v_cd_upd), 'card_deletes', cardinality(v_cd_del),
        'review_deletes', cardinality(v_rv_del));
    IF p_plan ? 'counts' AND p_plan->'counts' <> v_counts THEN
        RAISE EXCEPTION 'dt_rewrite_history_v6: plan counts % do not match plan lists %', p_plan->'counts', v_counts;
    END IF;
    IF jsonb_array_length(coalesce(p_plan->'unmappable', '[]')) > 0 THEN
        RAISE EXCEPTION 'dt_rewrite_history_v6: plan lists unmappable rows: %', p_plan->'unmappable';
    END IF;

    BEGIN  -- sub-block: rolled back as a unit when p_dry_run
        IF cardinality(v_ei_upd) + cardinality(v_ei_del) + cardinality(v_pe_upd) + cardinality(v_pe_del)
           + cardinality(v_cd_upd) + cardinality(v_cd_del) + cardinality(v_rv_del) = 0 THEN
            v_result := jsonb_build_object('status', 'noop', 'counts', v_counts);
        ELSE
            -- ---- fail closed -------------------------------------------------
            IF EXISTS (SELECT 1 FROM public.dt_v5_snapshot_error_instance)
               OR EXISTS (SELECT 1 FROM public.dt_v5_snapshot_error_instance_full)
               OR EXISTS (SELECT 1 FROM public.dt_v5_snapshot_profile_entry)
               OR EXISTS (SELECT 1 FROM public.dt_v5_snapshot_card)
               OR EXISTS (SELECT 1 FROM public.dt_v5_snapshot_card_review) THEN
                RAISE EXCEPTION 'dt_rewrite_history_v6: snapshot tables are not empty — refusing to snapshot twice (restore or drop the old snapshot first)';
            END IF;

            FOR k, v_cols IN VALUES
                ('dt_error_instance', public.dt_rewrite_snapshot_columns('public.dt_error_instance', 'public.dt_v5_snapshot_error_instance_full', true)),
                ('dt_error_profile_entry', public.dt_rewrite_snapshot_columns('public.dt_error_profile_entry', 'public.dt_v5_snapshot_profile_entry', true)),
                ('dt_card', public.dt_rewrite_snapshot_columns('public.dt_card', 'public.dt_v5_snapshot_card', true)),
                ('dt_card_review', public.dt_rewrite_snapshot_columns('public.dt_card_review', 'public.dt_v5_snapshot_card_review', true))
            LOOP
                IF v_cols IS NOT NULL THEN
                    RAISE EXCEPTION 'dt_rewrite_history_v6: %.(%) missing from its snapshot table — add them there first', k, v_cols;
                END IF;
            END LOOP;

            IF v_ei_upd && v_ei_del OR v_pe_upd && v_pe_del OR v_cd_upd && v_cd_del THEN
                RAISE EXCEPTION 'dt_rewrite_history_v6: an id is in both an update and a delete list';
            END IF;

            SELECT string_agg(DISTINCT s, ', ') INTO v_bad FROM (
                SELECT x->>'subtype' AS s FROM jsonb_array_elements(p_plan->'error_updates') x
                UNION ALL SELECT x->>'subtype' FROM jsonb_array_elements(p_plan->'profile_updates') x
                UNION ALL SELECT x->>'subtype' FROM jsonb_array_elements(p_plan->'card_updates') x
            ) t WHERE s IS NULL OR NOT (s = ANY (v_slugs));
            IF v_bad IS NOT NULL THEN
                RAISE EXCEPTION 'dt_rewrite_history_v6: plan targets slugs outside the v% pair lists: %', v_target, v_bad;
            END IF;

            -- stale-plan checks: every row must still be exactly what the planner read
            SELECT string_agg(x.id::text, ',') INTO v_bad
            FROM jsonb_to_recordset(p_plan->'error_updates') AS x(id bigint, from_subtype text, from_version smallint)
            LEFT JOIN public.dt_error_instance e ON e.id = x.id
            WHERE e.id IS NULL OR e.subtype IS DISTINCT FROM x.from_subtype
               OR e.taxonomy_version IS DISTINCT FROM x.from_version;
            IF v_bad IS NOT NULL THEN RAISE EXCEPTION 'dt_rewrite_history_v6: stale plan, dt_error_instance ids %', v_bad; END IF;

            SELECT string_agg(x.id::text, ',') INTO v_bad
            FROM jsonb_to_recordset(p_plan->'error_deletes') AS x(id bigint, from_subtype text)
            LEFT JOIN public.dt_error_instance e ON e.id = x.id
            WHERE e.id IS NULL OR e.subtype IS DISTINCT FROM x.from_subtype;
            IF v_bad IS NOT NULL THEN RAISE EXCEPTION 'dt_rewrite_history_v6: stale plan, dt_error_instance (delete) ids %', v_bad; END IF;

            SELECT string_agg(x.id::text, ',') INTO v_bad
            FROM jsonb_to_recordset(p_plan->'profile_updates') AS x(id bigint, from_subtype text, from_version smallint)
            LEFT JOIN public.dt_error_profile_entry p ON p.id = x.id
            WHERE p.id IS NULL OR p.subtype IS DISTINCT FROM x.from_subtype
               OR p.taxonomy_version IS DISTINCT FROM x.from_version;
            IF v_bad IS NOT NULL THEN RAISE EXCEPTION 'dt_rewrite_history_v6: stale plan, dt_error_profile_entry ids %', v_bad; END IF;

            SELECT string_agg(x.id::text, ',') INTO v_bad
            FROM jsonb_to_recordset(p_plan->'profile_deletes') AS x(id bigint, from_subtype text)
            LEFT JOIN public.dt_error_profile_entry p ON p.id = x.id
            WHERE p.id IS NULL OR p.subtype IS DISTINCT FROM x.from_subtype;
            IF v_bad IS NOT NULL THEN RAISE EXCEPTION 'dt_rewrite_history_v6: stale plan, dt_error_profile_entry (delete) ids %', v_bad; END IF;

            SELECT string_agg(x.id::text, ',') INTO v_bad
            FROM jsonb_to_recordset(p_plan->'card_updates')
                 AS x(id bigint, from_subtype text, from_version smallint, from_profile_entry_id bigint)
            LEFT JOIN public.dt_card c ON c.id = x.id
            WHERE c.id IS NULL OR c.subtype IS DISTINCT FROM x.from_subtype
               OR c.taxonomy_version IS DISTINCT FROM x.from_version
               OR c.profile_entry_id IS DISTINCT FROM x.from_profile_entry_id;
            IF v_bad IS NOT NULL THEN RAISE EXCEPTION 'dt_rewrite_history_v6: stale plan, dt_card ids %', v_bad; END IF;

            SELECT string_agg(i::text, ',') INTO v_bad
            FROM unnest(v_cd_del) i WHERE NOT EXISTS (SELECT 1 FROM public.dt_card c WHERE c.id = i);
            IF v_bad IS NOT NULL THEN RAISE EXCEPTION 'dt_rewrite_history_v6: stale plan, dt_card (delete) ids %', v_bad; END IF;

            SELECT string_agg(i::text, ',') INTO v_bad
            FROM unnest(v_rv_del) i WHERE NOT EXISTS (SELECT 1 FROM public.dt_card_review r WHERE r.id = i);
            IF v_bad IS NOT NULL THEN RAISE EXCEPTION 'dt_rewrite_history_v6: stale plan, dt_card_review ids %', v_bad; END IF;

            -- ---- snapshot (before any change) --------------------------------
            INSERT INTO public.dt_v5_snapshot_error_instance (id, subtype, taxonomy_version, remap_flag)
            SELECT id, subtype, taxonomy_version, remap_flag
            FROM public.dt_error_instance WHERE id = ANY (v_ei_upd);

            v_cols := public.dt_rewrite_snapshot_columns('public.dt_error_instance', 'public.dt_v5_snapshot_error_instance_full');
            EXECUTE format('INSERT INTO public.dt_v5_snapshot_error_instance_full (%1$s) SELECT %1$s FROM public.dt_error_instance WHERE id = ANY ($1)', v_cols)
                USING v_ei_del;

            v_cols := public.dt_rewrite_snapshot_columns('public.dt_error_profile_entry', 'public.dt_v5_snapshot_profile_entry');
            EXECUTE format('INSERT INTO public.dt_v5_snapshot_profile_entry (%1$s) SELECT %1$s FROM public.dt_error_profile_entry WHERE id = ANY ($1)', v_cols)
                USING v_pe_upd || v_pe_del;

            v_cols := public.dt_rewrite_snapshot_columns('public.dt_card', 'public.dt_v5_snapshot_card');
            EXECUTE format('INSERT INTO public.dt_v5_snapshot_card (%1$s) SELECT %1$s FROM public.dt_card WHERE id = ANY ($1)', v_cols)
                USING v_cd_upd || v_cd_del;

            v_cols := public.dt_rewrite_snapshot_columns('public.dt_card_review', 'public.dt_v5_snapshot_card_review');
            EXECUTE format('INSERT INTO public.dt_v5_snapshot_card_review (%1$s) SELECT %1$s FROM public.dt_card_review WHERE id = ANY ($1)', v_cols)
                USING v_rv_del;

            -- ---- writes, child-first ----------------------------------------
            DELETE FROM public.dt_card_review WHERE id = ANY (v_rv_del);
            GET DIAGNOSTICS v_n = ROW_COUNT;
            IF v_n <> cardinality(v_rv_del) THEN RAISE EXCEPTION 'review_deletes: % rows, plan %', v_n, cardinality(v_rv_del); END IF;

            DELETE FROM public.dt_card WHERE id = ANY (v_cd_del);
            GET DIAGNOSTICS v_n = ROW_COUNT;
            IF v_n <> cardinality(v_cd_del) THEN RAISE EXCEPTION 'card_deletes: % rows, plan %', v_n, cardinality(v_cd_del); END IF;

            UPDATE public.dt_card c
               SET subtype = x.subtype, profile_entry_id = x.profile_entry_id,
                   taxonomy_version = x.taxonomy_version
              FROM jsonb_to_recordset(p_plan->'card_updates')
                   AS x(id bigint, subtype text, profile_entry_id bigint, taxonomy_version smallint)
             WHERE c.id = x.id;
            GET DIAGNOSTICS v_n = ROW_COUNT;
            IF v_n <> cardinality(v_cd_upd) THEN RAISE EXCEPTION 'card_updates: % rows, plan %', v_n, cardinality(v_cd_upd); END IF;

            DELETE FROM public.dt_error_profile_entry WHERE id = ANY (v_pe_del);
            GET DIAGNOSTICS v_n = ROW_COUNT;
            IF v_n <> cardinality(v_pe_del) THEN RAISE EXCEPTION 'profile_deletes: % rows, plan %', v_n, cardinality(v_pe_del); END IF;

            UPDATE public.dt_error_profile_entry p
               SET subtype = x.subtype, "count" = x."count", severity_rank = x.severity_rank,
                   trend = x.trend, remediation_status = x.remediation_status,
                   taxonomy_version = x.taxonomy_version, remap_flag = x.remap_flag
              FROM jsonb_to_recordset(p_plan->'profile_updates')
                   AS x(id bigint, subtype text, "count" integer, severity_rank real, trend jsonb,
                        remediation_status text, taxonomy_version smallint, remap_flag text)
             WHERE p.id = x.id;
            GET DIAGNOSTICS v_n = ROW_COUNT;
            IF v_n <> cardinality(v_pe_upd) THEN RAISE EXCEPTION 'profile_updates: % rows, plan %', v_n, cardinality(v_pe_upd); END IF;

            DELETE FROM public.dt_error_instance WHERE id = ANY (v_ei_del);
            GET DIAGNOSTICS v_n = ROW_COUNT;
            IF v_n <> cardinality(v_ei_del) THEN RAISE EXCEPTION 'error_deletes: % rows, plan %', v_n, cardinality(v_ei_del); END IF;

            UPDATE public.dt_error_instance e
               SET subtype = x.subtype, taxonomy_version = x.taxonomy_version, remap_flag = x.remap_flag
              FROM jsonb_to_recordset(p_plan->'error_updates')
                   AS x(id bigint, subtype text, taxonomy_version smallint, remap_flag text)
             WHERE e.id = x.id;
            GET DIAGNOSTICS v_n = ROW_COUNT;
            IF v_n <> cardinality(v_ei_upd) THEN RAISE EXCEPTION 'error_updates: % rows, plan %', v_n, cardinality(v_ei_upd); END IF;

            v_result := jsonb_build_object('status', 'applied', 'counts', v_counts);
        END IF;

        -- ---- post-conditions (also guard the noop path) ----------------------
        SELECT string_agg(format('%s:%s=%s', t, s, n), ', ') INTO v_bad FROM (
            SELECT 'dt_error_instance' AS t, subtype AS s, count(*) AS n FROM public.dt_error_instance
             WHERE NOT (subtype = ANY (v_slugs)) OR taxonomy_version IS DISTINCT FROM v_target GROUP BY subtype
            UNION ALL
            SELECT 'dt_error_profile_entry', subtype, count(*) FROM public.dt_error_profile_entry
             WHERE NOT (subtype = ANY (v_slugs)) OR taxonomy_version IS DISTINCT FROM v_target GROUP BY subtype
            UNION ALL
            SELECT 'dt_card', subtype, count(*) FROM public.dt_card
             WHERE NOT (subtype = ANY (v_slugs)) OR taxonomy_version IS DISTINCT FROM v_target GROUP BY subtype
        ) z;
        IF v_bad IS NOT NULL THEN
            RAISE EXCEPTION 'dt_rewrite_history_v6: post-condition failed, rows outside v% (slug or taxonomy_version): % — re-plan', v_target, v_bad;
        END IF;

        IF EXISTS (SELECT 1 FROM public.dt_error_instance WHERE subtype = ANY (v_dropped))
           OR EXISTS (SELECT 1 FROM public.dt_error_profile_entry WHERE subtype = ANY (v_dropped))
           OR EXISTS (SELECT 1 FROM public.dt_card WHERE subtype = ANY (v_dropped)) THEN
            RAISE EXCEPTION 'dt_rewrite_history_v6: post-condition failed, rows remain on a dropped slug (%)', v_dropped;
        END IF;

        SELECT string_agg(c.id::text, ',') INTO v_bad
        FROM public.dt_card c JOIN public.dt_error_profile_entry p ON p.id = c.profile_entry_id
        WHERE c.subtype <> p.subtype;
        IF v_bad IS NOT NULL THEN
            RAISE EXCEPTION 'dt_rewrite_history_v6: post-condition failed, cards whose subtype differs from their profile entry: %', v_bad;
        END IF;

        IF p_dry_run THEN
            RAISE EXCEPTION USING ERRCODE = 'DTDRY', MESSAGE = v_result::text;
        END IF;
    EXCEPTION WHEN SQLSTATE 'DTDRY' THEN
        RETURN jsonb_set(SQLERRM::jsonb, '{dry_run}', 'true') || jsonb_build_object('rolled_back', true);
    END;

    RETURN v_result || jsonb_build_object('dry_run', false);
END;
$fn$;

-- ----------------------------------------------------------------------------
-- Restore
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.dt_restore_history_v5(
    p_confirm_drop_snapshot boolean DEFAULT false, p_dry_run boolean DEFAULT false
)
RETURNS jsonb
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $fn$
DECLARE
    v_cols   text;
    v_n      bigint;
    v_res    jsonb := '{}'::jsonb;
    v_bad    text;
BEGIN
    LOCK TABLE public.dt_error_instance, public.dt_error_profile_entry,
               public.dt_card, public.dt_card_review IN EXCLUSIVE MODE;

    IF NOT EXISTS (SELECT 1 FROM public.dt_v5_snapshot_error_instance)
       AND NOT EXISTS (SELECT 1 FROM public.dt_v5_snapshot_error_instance_full)
       AND NOT EXISTS (SELECT 1 FROM public.dt_v5_snapshot_profile_entry)
       AND NOT EXISTS (SELECT 1 FROM public.dt_v5_snapshot_card)
       AND NOT EXISTS (SELECT 1 FROM public.dt_v5_snapshot_card_review) THEN
        RETURN jsonb_build_object('status', 'noop', 'reason', 'snapshot tables are empty', 'dry_run', p_dry_run);
    END IF;

    -- Composite UNIQUE (user_id, l1, l2, subtype) guard: a snapshot profile row
    -- goes back to its v5 key, so that key must not be held by a row created
    -- after the cutover (not in the snapshot). Snapshot keys are distinct among
    -- themselves, so only a non-snapshot holder can collide. Refuse up front with
    -- a clear message instead of a mid-restore unique_violation.
    SELECT string_agg(format('%s (held by %s)', s.id, p.id), ', ' ORDER BY s.id) INTO v_bad
      FROM public.dt_v5_snapshot_profile_entry s
      JOIN public.dt_error_profile_entry p
        ON p.user_id = s.user_id AND p.l1_language_id = s.l1_language_id
       AND p.l2_language_id = s.l2_language_id AND p.subtype = s.subtype
     WHERE NOT EXISTS (SELECT 1 FROM public.dt_v5_snapshot_profile_entry s2 WHERE s2.id = p.id);
    IF v_bad IS NOT NULL THEN
        RAISE EXCEPTION 'dt_restore_history_v5: v5 profile keys now held by post-cutover dt_error_profile_entry rows: %. Restore aborted (nothing changed); policy after new DT traffic is fix-forward (re-pin v5 only as an emergency stop).', v_bad;
    END IF;

    BEGIN  -- sub-block: rolled back as a unit when p_dry_run
        -- 1. deleted error instances (parents of cards)
        v_cols := public.dt_rewrite_snapshot_columns('public.dt_error_instance', 'public.dt_v5_snapshot_error_instance_full');
        EXECUTE format(
            'INSERT INTO public.dt_error_instance (%1$s) OVERRIDING SYSTEM VALUE '
            'SELECT %1$s FROM public.dt_v5_snapshot_error_instance_full s '
            'WHERE NOT EXISTS (SELECT 1 FROM public.dt_error_instance e WHERE e.id = s.id) ORDER BY s.id', v_cols);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        v_res := v_res || jsonb_build_object('error_reinserted', v_n);

        -- 2. updated error instances
        UPDATE public.dt_error_instance e
           SET subtype = s.subtype, taxonomy_version = s.taxonomy_version, remap_flag = s.remap_flag
          FROM public.dt_v5_snapshot_error_instance s
         WHERE e.id = s.id;
        GET DIAGNOSTICS v_n = ROW_COUNT;
        v_res := v_res || jsonb_build_object('error_restored', v_n);

        -- 3. updated profile entries (before re-inserting merged-away rows, so a
        --    survivor gives its v6 key back before the v5 owner of it returns)
        UPDATE public.dt_error_profile_entry p
           SET subtype = s.subtype, "count" = s."count", severity_rank = s.severity_rank,
               trend = s.trend, remediation_status = s.remediation_status,
               taxonomy_version = s.taxonomy_version, remap_flag = s.remap_flag
          FROM public.dt_v5_snapshot_profile_entry s
         WHERE p.id = s.id;
        GET DIAGNOSTICS v_n = ROW_COUNT;
        v_res := v_res || jsonb_build_object('profile_restored', v_n);

        -- 4. deleted profile entries (dropped + merged-away)
        v_cols := public.dt_rewrite_snapshot_columns('public.dt_error_profile_entry', 'public.dt_v5_snapshot_profile_entry');
        EXECUTE format(
            'INSERT INTO public.dt_error_profile_entry (%1$s) OVERRIDING SYSTEM VALUE '
            'SELECT %1$s FROM public.dt_v5_snapshot_profile_entry s '
            'WHERE NOT EXISTS (SELECT 1 FROM public.dt_error_profile_entry p WHERE p.id = s.id) ORDER BY s.id', v_cols);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        v_res := v_res || jsonb_build_object('profile_reinserted', v_n);

        -- 5. updated cards — only the columns the rewrite changed, so FSRS
        --    progress made after the cutover survives the rollback
        UPDATE public.dt_card c
           SET subtype = s.subtype, profile_entry_id = s.profile_entry_id,
               taxonomy_version = s.taxonomy_version
          FROM public.dt_v5_snapshot_card s
         WHERE c.id = s.id;
        GET DIAGNOSTICS v_n = ROW_COUNT;
        v_res := v_res || jsonb_build_object('card_restored', v_n);

        -- 6. deleted cards
        v_cols := public.dt_rewrite_snapshot_columns('public.dt_card', 'public.dt_v5_snapshot_card');
        EXECUTE format(
            'INSERT INTO public.dt_card (%1$s) OVERRIDING SYSTEM VALUE '
            'SELECT %1$s FROM public.dt_v5_snapshot_card s '
            'WHERE NOT EXISTS (SELECT 1 FROM public.dt_card c WHERE c.id = s.id) ORDER BY s.id', v_cols);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        v_res := v_res || jsonb_build_object('card_reinserted', v_n);

        -- 7. deleted reviews
        v_cols := public.dt_rewrite_snapshot_columns('public.dt_card_review', 'public.dt_v5_snapshot_card_review');
        EXECUTE format(
            'INSERT INTO public.dt_card_review (%1$s) OVERRIDING SYSTEM VALUE '
            'SELECT %1$s FROM public.dt_v5_snapshot_card_review s '
            'WHERE NOT EXISTS (SELECT 1 FROM public.dt_card_review r WHERE r.id = s.id) ORDER BY s.id', v_cols);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        v_res := v_res || jsonb_build_object('review_reinserted', v_n);

        -- every snapshotted row must be back (a row deleted since the cutover
        -- cannot be restored from the narrow error snapshot: refuse)
        SELECT string_agg(s.id::text, ',') INTO v_bad FROM public.dt_v5_snapshot_error_instance s
        WHERE NOT EXISTS (SELECT 1 FROM public.dt_error_instance e WHERE e.id = s.id);
        IF v_bad IS NOT NULL THEN
            RAISE EXCEPTION 'dt_restore_history_v5: dt_error_instance ids % were deleted after the cutover; restore cannot rebuild them', v_bad;
        END IF;

        IF p_confirm_drop_snapshot THEN
            TRUNCATE public.dt_v5_snapshot_error_instance, public.dt_v5_snapshot_error_instance_full,
                     public.dt_v5_snapshot_profile_entry, public.dt_v5_snapshot_card,
                     public.dt_v5_snapshot_card_review;
            v_res := v_res || jsonb_build_object('snapshot_truncated', true);
        ELSE
            v_res := v_res || jsonb_build_object('snapshot_truncated', false);
        END IF;
        v_res := v_res || jsonb_build_object('status', 'restored');

        IF p_dry_run THEN
            RAISE EXCEPTION USING ERRCODE = 'DTDRY', MESSAGE = v_res::text;
        END IF;
    EXCEPTION WHEN SQLSTATE 'DTDRY' THEN
        RETURN SQLERRM::jsonb || jsonb_build_object('dry_run', true, 'rolled_back', true);
    END;

    RETURN v_res || jsonb_build_object('dry_run', false);
END;
$fn$;

COMMENT ON FUNCTION public.dt_rewrite_history_v6(jsonb, boolean) IS
    'TASK-852: one-time v5->v6 rewrite of dt_error_instance / dt_error_profile_entry / '
    'dt_card (+ script_choice delete incl. dt_card_review), executing a plan built by '
    'scripts/dt_rewrite_history_v6.py. Snapshot first, one transaction, fails closed. '
    'p_dry_run (default true) rolls everything back. Invoked only by the TASK-853 cutover.';
COMMENT ON FUNCTION public.dt_restore_history_v5(boolean, boolean) IS
    'TASK-852: undo dt_rewrite_history_v6 from the dt_v5_snapshot_* tables (parent-first, '
    'OVERRIDING SYSTEM VALUE). Truncates the snapshot only with p_confirm_drop_snapshot.';

REVOKE ALL ON FUNCTION public.dt_rewrite_snapshot_columns(regclass, regclass, boolean) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dt_rewrite_history_v6(jsonb, boolean) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dt_restore_history_v5(boolean, boolean) FROM PUBLIC;

DO $grants$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON FUNCTION public.dt_rewrite_snapshot_columns(regclass, regclass, boolean) FROM anon, authenticated;
        REVOKE ALL ON FUNCTION public.dt_rewrite_history_v6(jsonb, boolean) FROM anon, authenticated;
        REVOKE ALL ON FUNCTION public.dt_restore_history_v5(boolean, boolean) FROM anon, authenticated;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT EXECUTE ON FUNCTION public.dt_rewrite_snapshot_columns(regclass, regclass, boolean) TO service_role;
        GRANT EXECUTE ON FUNCTION public.dt_rewrite_history_v6(jsonb, boolean) TO service_role;
        GRANT EXECUTE ON FUNCTION public.dt_restore_history_v5(boolean, boolean) TO service_role;
    END IF;
END
$grants$;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying; all read-only):
--
-- Functions present, not callable by API roles (expect 3 rows; anon/auth = f):
-- SELECT p.proname,
--        has_function_privilege('anon', p.oid, 'EXECUTE') AS anon,
--        has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth,
--        has_function_privilege('service_role', p.oid, 'EXECUTE') AS service
-- FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
-- WHERE n.nspname = 'public'
--   AND p.proname IN ('dt_rewrite_history_v6', 'dt_restore_history_v5', 'dt_rewrite_snapshot_columns');
--
-- No source column missing from its snapshot (expect four NULLs):
-- SELECT public.dt_rewrite_snapshot_columns('public.dt_error_instance', 'public.dt_v5_snapshot_error_instance_full', true),
--        public.dt_rewrite_snapshot_columns('public.dt_error_profile_entry', 'public.dt_v5_snapshot_profile_entry', true),
--        public.dt_rewrite_snapshot_columns('public.dt_card', 'public.dt_v5_snapshot_card', true),
--        public.dt_rewrite_snapshot_columns('public.dt_card_review', 'public.dt_v5_snapshot_card_review', true);
--
-- After --apply (TASK-853): expect 0 / 0 / 0 rows outside v6 and the snapshot sizes
-- to equal the plan's error_updates / error_deletes / profile_* / card_* / review_deletes.
-- ============================================================================
