"""Static checks of the Knowledge Report migrations (TASK-1034, TASK-1036, TASK-1044).

Spec: wiki/features/knowledge-report.tech.md §5.1, §5.2, §6.1, §12, §13. No database: the SQL is
parsed. Behaviour is covered by tests/sql/test_knowledge_report.sql, run on a throwaway database
(the local harness or a Supabase branch), never on production.
"""
from __future__ import annotations

import re

import pytest

from tests.test_exercise_content_migration_schema import (
    MIGRATIONS, code_without_strings, function_def, function_defs, norm, read, revoke_grant_problems,
    scan_file, statements)

FOUNDATION = 'knowledge_report_foundation.sql'
FOUNDATION_ROLLBACK = 'knowledge_report_foundation_rollback.sql'
BUCKET = 'reference_data_bucket.sql'
BUCKET_ROLLBACK = 'reference_data_bucket_rollback.sql'
SUMMARY = 'knowledge_report_summary.sql'
SUMMARY_ROLLBACK = 'knowledge_report_summary_rollback.sql'
WORDS = 'knowledge_report_words.sql'
WORDS_ROLLBACK = 'knowledge_report_words_rollback.sql'
ALL_FILES = (FOUNDATION, FOUNDATION_ROLLBACK, BUCKET, BUCKET_ROLLBACK, SUMMARY, SUMMARY_ROLLBACK, WORDS,
             WORDS_ROLLBACK)

INVOKER_HEADER = 'SECURITY INVOKER SET search_path = public, pg_temp'
READ_RPCS = {
    FOUNDATION: ('knowledge_frame_bands', 'knowledge_active_pairs'),
    SUMMARY: ('knowledge_report_summary',),
    WORDS: ('knowledge_report_words',),
}
SIGNATURES = {
    'knowledge_frame_bands': [],
    'knowledge_active_pairs': [('p_since', 'timestamptz', None)],
    'knowledge_snapshots_prune': [('p_keep_daily_days', 'integer', '120')],
    'knowledge_report_summary': [('p_user_id', 'uuid', None), ('p_language_id', 'smallint', None),
                                 ('p_as_of', 'timestamptz', 'now()'), ('p_window_days', 'integer', '180'),
                                 ('p_cal_since', 'timestamptz[]', "'{}'")],
    'knowledge_report_words': [('p_user_id', 'uuid', None), ('p_language_id', 'smallint', None),
                               ('p_definition_language_id', 'smallint', None), ('p_filters', 'jsonb', "'{}'"),
                               ('p_sort', 'text', "'useful'"), ('p_cursor', 'jsonb', 'NULL'),
                               ('p_limit', 'integer', '50'), ('p_as_of', 'timestamptz', 'now()')],
}
FILE_OF = {'knowledge_frame_bands': FOUNDATION, 'knowledge_active_pairs': FOUNDATION,
           'knowledge_snapshots_prune': FOUNDATION, 'knowledge_report_summary': SUMMARY,
           'knowledge_report_words': WORDS}

# tech §5.1, column by column: (name, type and constraints), whitespace-normalised.
SNAPSHOT_COLUMNS = [
    ('user_id', 'uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE'),
    ('language_id', 'smallint NOT NULL REFERENCES public.dim_languages(id)'),
    ('snapshot_date', 'date NOT NULL'),
    ('method_version', 'smallint NOT NULL DEFAULT 1'),
    ('tracked_words', 'integer NOT NULL'),
    ('tracked_meanings', 'integer NOT NULL'),
    ('rated_known_words', 'integer NOT NULL'),
    ('checked_meanings', 'integer NOT NULL'),
    ('missed_recent_meanings', 'integer NOT NULL'),
    ('idle60_meanings', 'integer NOT NULL'),
    ('practised_30_meanings', 'integer NOT NULL'),
    ('direct_checks_30', 'integer NOT NULL'),
    ('cal_definition_language_id', 'smallint REFERENCES public.dim_languages(id)'),
    ('cal_bands', 'smallint[] CHECK (cal_bands IS NULL OR array_length(cal_bands, 1) = 21)'),
    ('frame_bands', 'integer[] CHECK (frame_bands IS NULL OR array_length(frame_bands, 1) = 7)'),
    ('cal_answers', 'integer NOT NULL DEFAULT 0'),
    ('cal_first_answer_at', 'timestamptz'),
    ('cal_last_answer_at', 'timestamptz'),
    ('est_kind', 'smallint NOT NULL DEFAULT 0 CHECK (est_kind BETWEEN 0 AND 2)'),
    ('est_lo', 'integer'),
    ('est_hi', 'integer'),
    ('est_label', 'smallint CHECK (est_label BETWEEN 1 AND 3)'),
    ('source', "text NOT NULL DEFAULT 'nightly' CHECK (source IN ('nightly', 'manual'))"),
    ('computed_at', 'timestamptz NOT NULL DEFAULT now()'),
]

# The §2.4 rule, textually identical in the summary, the words RPC and (TASK-1049) knowledge_list_buckets.
RATED_KNOWN = '(m.wc > m.ww AND m.p_last >= 0.75 AND NOT m.marked_unknown) AS rated_known'
FORBIDDEN_NAMES = ('bkt_effective_p_known', 'bkt_apply_decay', 'level_tag')


def code(name: str) -> str:
    """File text without comments and string literals."""
    return code_without_strings(read(name))


def has(sql: str, pattern: str) -> bool:
    return any(re.fullmatch(pattern, norm(s), re.I | re.S) for s in statements(sql))


def split_columns(body: str) -> list[str]:
    parts, depth, buf = [], 0, []
    for ch in body:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append(''.join(buf))
    return [norm(p) for p in parts if p.strip()]


def snapshot_table_parts() -> list[str]:
    stmt = next(s for s in statements(read(FOUNDATION)) if 'CREATE TABLE' in s.upper())
    body = stmt[stmt.index('(') + 1:stmt.rindex(')')]
    return split_columns(body)


def cte_chain(name: str) -> str:
    """The shared WITH r ... st CTE chain of a report RPC body."""
    body = function_def(read(name), FILE_AND_FN[name]).body
    start = body.index('WITH r AS (')
    end = body.index('), st AS (')
    end = body.index('\n), ', end + len('), st AS ('))
    return body[start:end]


FILE_AND_FN = {SUMMARY: 'knowledge_report_summary', WORDS: 'knowledge_report_words'}


# --------------------------------------------------------------------------------------
# every file
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize('name', ALL_FILES)
def test_file_exists_is_one_transaction_and_lint_clean(name):
    sql = read(name)
    assert sql.strip(), name
    stmts = [norm(s).upper() for s in statements(sql)]
    assert stmts[0] == 'BEGIN' and stmts[-1] == 'COMMIT', name
    assert not any(scan_file(MIGRATIONS / name).values()), scan_file(MIGRATIONS / name)


@pytest.mark.parametrize('name', ALL_FILES)
def test_no_decay_function_and_no_level_tag(name):
    text = read(name)
    for forbidden in FORBIDDEN_NAMES:
        assert forbidden not in text, f'{name} mentions {forbidden}'


@pytest.mark.parametrize('name', ALL_FILES)
def test_no_list_table_no_policy_no_definer(name):
    c = code(name).upper()
    assert 'CREATE POLICY' not in c and 'SECURITY DEFINER' not in c
    assert 'DIM_WORD_LIST' not in c and 'WORD_LIST_ITEMS' not in c
    tables = re.findall(r'CREATE TABLE (?:IF NOT EXISTS )?(\S+)', norm(c))
    assert tables in ([], ['PUBLIC.USER_KNOWLEDGE_SNAPSHOTS']), tables


def test_no_file_reads_exercise_content():
    for name in (SUMMARY, WORDS, FOUNDATION):
        assert not re.search(r'\b\w+\.content\b', code(name)), name   # ADR-049 dropped exercises.content


# --------------------------------------------------------------------------------------
# functions: signatures, headers, ACLs
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize('fn', sorted(SIGNATURES))
def test_signature_and_defaults(fn):
    assert function_def(read(FILE_OF[fn]), fn).params == SIGNATURES[fn]


@pytest.mark.parametrize('name,fn', [(f, fn) for f, fns in READ_RPCS.items() for fn in fns])
def test_read_rpcs_are_sql_stable_invoker(name, fn):
    f = function_def(read(name), fn)
    assert f.or_replace
    assert f.header == f'RETURNS jsonb LANGUAGE sql STABLE {INVOKER_HEADER}', f.header
    body = code_without_strings(f.body).upper()
    for word in ('INSERT ', 'UPDATE ', 'DELETE ', 'TRUNCATE', 'MATERIALIZED', 'NOW()'):
        assert word not in body, (fn, word)


def test_prune_is_plpgsql_volatile_and_guards_35_days():
    f = function_def(read(FOUNDATION), 'knowledge_snapshots_prune')
    assert f.header == f'RETURNS integer LANGUAGE plpgsql VOLATILE {INVOKER_HEADER}', f.header
    body = norm(f.body)
    assert "IF p_keep_daily_days IS NULL OR p_keep_daily_days < 35 THEN RAISE EXCEPTION 'keep_daily_days_too_small'" in body
    assert ("DELETE FROM user_knowledge_snapshots WHERE snapshot_date < (now() AT TIME ZONE 'UTC')::date - p_keep_daily_days "
            "AND extract(isodow FROM snapshot_date) <> 1;") in body
    assert 'GET DIAGNOSTICS v_deleted = ROW_COUNT; RETURN v_deleted;' in body


@pytest.mark.parametrize('fn', sorted(SIGNATURES))
def test_revoke_and_grant(fn):
    sql = read(FILE_OF[fn])
    assert revoke_grant_problems(sql, function_def(sql, fn)) == []


def test_each_file_defines_only_its_functions():
    assert sorted(f.name for f in function_defs(read(FOUNDATION))) == [
        'knowledge_active_pairs', 'knowledge_frame_bands', 'knowledge_snapshots_prune']
    assert [f.name for f in function_defs(read(SUMMARY))] == ['knowledge_report_summary']
    assert [f.name for f in function_defs(read(WORDS))] == ['knowledge_report_words']
    for name in (BUCKET, BUCKET_ROLLBACK, FOUNDATION_ROLLBACK, SUMMARY_ROLLBACK, WORDS_ROLLBACK):
        assert function_defs(read(name)) == [], name


# --------------------------------------------------------------------------------------
# TASK-1034: snapshot table, frame, pairs, rollback
# --------------------------------------------------------------------------------------
def test_snapshot_table_matches_spec_5_1():
    parts = snapshot_table_parts()
    columns = [p for p in parts if not p.upper().startswith('PRIMARY KEY')]
    assert [(c.split(' ', 1)[0], c.split(' ', 1)[1]) for c in columns] == SNAPSHOT_COLUMNS
    assert [p for p in parts if p.upper().startswith('PRIMARY KEY')] == [
        'PRIMARY KEY (user_id, language_id, snapshot_date)']


def test_snapshot_table_rls_revoke_and_service_role_only():
    sql = read(FOUNDATION)
    assert has(sql, r'ALTER TABLE public\.user_knowledge_snapshots ENABLE ROW LEVEL SECURITY')
    assert has(sql, r'REVOKE ALL ON public\.user_knowledge_snapshots FROM PUBLIC, anon, authenticated')
    grants = [norm(s) for s in statements(sql) if norm(s).upper().startswith('GRANT') and ' ON public.' in s]
    assert grants == ['GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_knowledge_snapshots TO service_role']


def test_frame_sql_is_the_spec_query():
    body = norm(function_def(read(FOUNDATION), 'knowledge_frame_bands').body)
    for fragment in (
            'FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id AND s.sense_rank = 1',
            'WHERE p.has_embedding AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl WHERE bl.sense_id = p.sense_id)',
            'count(DISTINCT p.vocab_id) AS n',
            'GROUP BY 1, 2, 3',
            "pr.l::text || ':' || pr.d::text",
            'FROM generate_series(1, 7) AS g(b) LEFT JOIN c ON c.l = pr.l AND c.d = pr.d AND c.b = g.b',
            'jsonb_agg(coalesce(c.n, 0) ORDER BY g.b)'):
        assert fragment in body, fragment


def test_active_pairs_sql():
    body = norm(function_def(read(FOUNDATION), 'knowledge_active_pairs').body)
    assert 'SELECT DISTINCT k.user_id, k.language_id FROM user_vocabulary_knowledge k UNION' in body
    assert "WHERE cs.mode = 'definition' AND cr.answered_at > p_since" in body


def test_foundation_rollback_drops_everything():
    stmts = [norm(s) for s in statements(read(FOUNDATION_ROLLBACK))]
    assert stmts == ['BEGIN',
                     'DROP FUNCTION IF EXISTS public.knowledge_snapshots_prune(integer)',
                     'DROP FUNCTION IF EXISTS public.knowledge_active_pairs(timestamptz)',
                     'DROP FUNCTION IF EXISTS public.knowledge_frame_bands()',
                     'DROP TABLE IF EXISTS public.user_knowledge_snapshots',
                     "NOTIFY pgrst, 'reload schema'",
                     'COMMIT']


# --------------------------------------------------------------------------------------
# TASK-1034: reference-data bucket
# --------------------------------------------------------------------------------------
def test_bucket_is_exactly_the_spec_statement():
    stmts = [norm(s) for s in statements(read(BUCKET))]
    assert stmts == ['BEGIN',
                     "INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types) "
                     "VALUES ('reference-data', 'reference-data', false, 5242880, ARRAY['application/json']) "
                     "ON CONFLICT (id) DO NOTHING",
                     'COMMIT']


def test_bucket_files_touch_no_object_policy_or_table():
    for name in (BUCKET, BUCKET_ROLLBACK):
        c = code(name).upper()
        assert 'POLICY' not in c and 'CREATE TABLE' not in c and 'ALTER TABLE' not in c
        assert 'INSERT INTO STORAGE.OBJECTS' not in c and 'DELETE FROM STORAGE.OBJECTS' not in c


def test_bucket_rollback_refuses_while_objects_exist():
    stmts = [norm(s) for s in statements(read(BUCKET_ROLLBACK))]
    assert stmts[0] == 'BEGIN' and stmts[-1] == 'COMMIT'
    guard, delete = stmts[1], stmts[2]
    assert "IF EXISTS (SELECT 1 FROM storage.objects WHERE bucket_id = 'reference-data') THEN RAISE EXCEPTION" in guard
    assert delete == "DELETE FROM storage.buckets WHERE id = 'reference-data'"
    assert len(stmts) == 4


# --------------------------------------------------------------------------------------
# TASK-1036: summary
# --------------------------------------------------------------------------------------
def test_summary_embeds_knowledge_calibration_inputs_with_the_14_signature():
    sql = read(SUMMARY)
    body = norm(function_def(sql, 'knowledge_report_summary').body)
    assert ('knowledge_calibration_inputs(p_user_id, p_language_id, p_as_of, p_window_days, '
            'NULL::smallint, NULL::uuid)') in body
    assert ("to_regprocedure('public.knowledge_calibration_inputs(uuid, smallint, timestamptz, integer, smallint, uuid)') "
            "IS NULL") in norm(sql)
    assert 'CREATE OR REPLACE FUNCTION public.knowledge_calibration_inputs' not in sql


def test_summary_output_keys():
    body = code_without_strings(function_def(read(SUMMARY), 'knowledge_report_summary').body)
    raw = function_def(read(SUMMARY), 'knowledge_report_summary').body
    for key in ('as_of', 'language_id', 'method_version', 'tracked', 'states', 'rated_known_words',
                'rated_known_checked2_words', 'idle60_meanings', 'last_seen_at', 'activity', 'd30', 'd90',
                'practised_meanings', 'direct_outcomes', 'met_in_texts', 'missed_recent', 'flagged', 'groups',
                'calibration', 'window_days', 'answers', 'first_answer_at', 'last_answer_at', 'since', 'families',
                'syy', 'syn', 'snn', 'watchlist', 'seen_not_rated', 'no_evidence'):
        assert f"'{key}'" in raw, key
    assert "'lists'" not in raw and 'list_code' not in body


def test_summary_rules_follow_the_spec():
    body = norm(function_def(read(SUMMARY), 'knowledge_report_summary').body)
    for fragment in (
            # §2.2 primary row and sums
            '(array_agg(p_known ORDER BY last_evidence_at DESC NULLS LAST, evidence_count DESC, sense_id))[1] AS p_last',
            "bool_or(status = 'user_marked_unknown') AS marked_unknown",
            # §2.3 logged outcomes: first tries (any source) and word quiz, <= as_of, language via senses
            'WHERE ea.user_id = p_user_id AND ea.is_first_attempt AND s.word_language_id = p_language_id AND ea.created_at <= p_as_of',
            'FROM word_quiz_results w JOIN dim_word_senses s ON s.id = w.sense_id',
            # §2.4 states
            RATED_KNOWN,
            "CASE WHEN f.latest_wrong THEN 'missed_last' WHEN f.rated_known THEN 'rated_known' "
            "WHEN f.wc + f.ww > 0 THEN 'checked' ELSE 'not_checked' END AS state",
            # §2.5 idle
            "WHERE st.last_seen_at <= p_as_of - interval '60 days'",
            # §2.12 missed recently and flag
            "(f.latest_wrong AND f.latest_at > p_as_of - interval '90 days') AS missed_recent",
            'AND f.n_out >= 4 AND f.wrong5 >= 3 AND f.days5 >= 2) AS flagged',
            "count(DISTINCT (at AT TIME ZONE 'UTC')::date) FILTER (WHERE rn <= 5 AND NOT is_correct) AS days5",
            # §2.11 families: non-intro first tries in 90 days, sufficient statistics
            "AND coalesce(ea.source, 'practice') <> 'intro'",
            "AND ea.created_at > p_as_of - interval '90 days' AND ea.created_at <= p_as_of",
            'sum(fa.y * fa.y) AS syy, sum(fa.y * fa.n) AS syn, sum(fa.n * fa.n) AS snn',
            # §2.6 since sets: definition mode, rank-1 anchors, latest answer per lemma
            "JOIN dim_word_senses a ON a.id = cr.anchor_sense_id AND a.sense_rank = 1",
            'SELECT DISTINCT ON (u.ord, c.v)',
            'FROM unnest(p_cal_since) WITH ORDINALITY AS u(ts, ord)',
            # §2.9 watchlist
            'WHERE w.user_id = p_user_id AND w.language_id = p_language_id AND w.active'):
        assert fragment in body, fragment


# --------------------------------------------------------------------------------------
# TASK-1044: words
# --------------------------------------------------------------------------------------
def test_words_sorts_keyset_and_limit():
    body = norm(function_def(read(WORDS), 'knowledge_report_words').body)
    assert ("CASE WHEN p_sort IN ('useful', 'recent', 'oldest', 'common', 'lemma', 'id', 'missed') "
            "THEN p_sort ELSE 'useful' END AS sort") in body
    assert 'greatest(1, least(coalesce(p_limit, 50), 1000)) AS lim' in body
    assert "(CASE WHEN prm.sort = 'lemma' THEN fr.lemma ELSE '' END) COLLATE \"C\" AS kt" in body
    assert ("CASE fr.state WHEN 'missed_last' THEN 0 WHEN 'checked' THEN 1 WHEN 'not_checked' THEN 2 ELSE 3 END"
            in body)
    assert "WHEN 'useful' THEN -coalesce(fr.zipf::float8, -1)" in body
    assert ('(keyed.kt, keyed.k1, keyed.k2, keyed.vocab_id, keyed.sense_rank) > '
            '(cur.c_kt, cur.c_k1, cur.c_k2, cur.c_vocab_id, cur.c_sense_rank)') in body
    assert 'ORDER BY keyed.kt, keyed.k1, keyed.k2, keyed.vocab_id, keyed.sense_rank LIMIT (SELECT prm.lim + 1 FROM prm)' in body
    for cast in ("(p_cursor->>1)::float8", "(p_cursor->>2)::float8", "(p_cursor->>3)::integer", "(p_cursor->>4)::integer"):
        assert cast in body, cast


def test_words_filters_and_search():
    body = norm(function_def(read(WORDS), 'knowledge_report_words').body)
    for fragment in (
            "(flt.states IS NULL OR st.state = ANY (flt.states))",
            "(NOT flt.checked_several OR (st.rated_known AND st.wc >= 2))",
            "(NOT flt.missed_recent OR st.missed_recent)",
            "(flt.idle_days IS NULL OR st.last_seen_at <= p_as_of - make_interval(days => flt.idle_days))",
            "(flt.bands IS NULL OR st.band = ANY (flt.bands))",
            "(NOT flt.in_word_list OR st.in_word_list)",
            "(NOT flt.has_vocab_ids OR (st.sense_rank = 1 AND st.vocab_id IN (SELECT vs.vocab_id FROM vs)))",
            "st.lemma LIKE flt.q || '%' ESCAPE E'\\\\'",
            "st.lemma_traditional LIKE flt.q || '%' ESCAPE E'\\\\'",
            "st.reading LIKE flt.q || '%' ESCAPE E'\\\\'",
            "p_language_id = 1 AND flt.q ~ '^[ -~]+$' AND flt.qkey <> ''",
            "regexp_replace(lower(translate(split_part(ns.pronunciation, ' (', 1), "
            "'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü', 'aaaaeeeeiiiioooouuuuvvvvv')), '[^a-z]', '', 'g') LIKE flt.qkey || '%'"):
        assert fragment in body, fragment
    assert len('āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü') == len('aaaaeeeeiiiioooouuuuvvvvv') == 25


def test_words_row_fields_and_no_model_number():
    raw = function_def(read(WORDS), 'knowledge_report_words').body
    keys = re.findall(r"'(\w+)', (?:pg|pr|gl|lad|fc)\.", raw)
    for key in ('vocab_id', 'sense_rank', 'lemma', 'lemma_traditional', 'reading', 'pronunciation', 'gloss',
                'gloss_language_id', 'zipf', 'band', 'state', 'app_rates_known', 'checks_correct', 'checks_wrong',
                'tests_correct', 'tests_wrong', 'first_seen_at', 'last_seen_at', 'missed_recent', 'misses_90',
                'ladder_ring', 'ladder_state', 'flashcard_lapses', 'in_word_list'):
        assert key in keys, key
    for key in ("'last_direct'", "'idle_days'", "'missed_flag'", "'rows'", "'next_cursor'", "'matching'", "'as_of'"):
        assert key in raw, key
    assert "'p_known'" not in raw and "'status'" not in raw and 'bkt_status' not in raw
    assert "'app_rates_known', pg.p_last >= 0.75" in norm(raw)


def test_words_page_only_joins_and_family_of_one_outcome():
    body = norm(function_def(read(WORDS), 'knowledge_report_words').body)
    assert ("FROM (VALUES (1, p_definition_language_id, 'standard'), (2, p_definition_language_id, 'simple'), "
            "(3, p_language_id, 'standard')) AS pri(o, d, lvl)") in body
    assert ('SELECT det2.family FROM exercises e JOIN dim_exercise_types det2 ON det2.type_code = e.exercise_type '
            'WHERE e.id = pg.latest_exercise_id::uuid') in body
    assert "pg.latest_etype IN ('intro_def_mc', 'intro_rev_mc', 'intro_read_typed', 'intro_read_typed2')" in body
    assert "pg.latest_etype = 'intro_cloze_mc' THEN 'meaning_recall'" in body
    assert "pg.latest_etype IN ('intro_cloze_typed', 'intro_recall_typed') THEN 'form_production'" in body
    assert "'unmapped'" in body
    # exercises is read by primary key, exercise_type only
    assert re.findall(r'\be\.(\w+)', body) == ['exercise_type', 'id']
    assert 'WHERE pg.pos <= prm.lim' in body


# --------------------------------------------------------------------------------------
# one rule in two functions
# --------------------------------------------------------------------------------------
def test_summary_and_words_share_the_cte_chain_byte_for_byte():
    assert cte_chain(SUMMARY) == cte_chain(WORDS)
    assert RATED_KNOWN in norm(cte_chain(SUMMARY))
    assert 'ORDER BY at DESC, is_correct, src, oid) AS rn' in cte_chain(SUMMARY)   # ties: wrong first


@pytest.mark.parametrize('name,fn,args', [
    (SUMMARY_ROLLBACK, 'knowledge_report_summary', 'uuid, smallint, timestamptz, integer, timestamptz[]'),
    (WORDS_ROLLBACK, 'knowledge_report_words', 'uuid, smallint, smallint, jsonb, text, jsonb, integer, timestamptz'),
])
def test_rpc_rollbacks(name, fn, args):
    stmts = [norm(s) for s in statements(read(name))]
    assert stmts == ['BEGIN', f'DROP FUNCTION IF EXISTS public.{fn}({args})', "NOTIFY pgrst, 'reload schema'", 'COMMIT']


def test_harness_fixture_stub_stays_out_of_migrations():
    from pathlib import Path
    stub = Path(__file__).resolve().parent / 'sql' / 'fixtures' / 'knowledge_calibration_inputs_stub.sql'
    assert stub.exists()
    assert 'TEST-ONLY STUB' in stub.read_text(encoding='utf-8')
    assert [f.params for f in function_defs(stub.read_text(encoding='utf-8'))] == [[
        ('p_user_id', 'uuid', None), ('p_language_id', 'smallint', None), ('p_as_of', 'timestamptz', 'now()'),
        ('p_window_days', 'integer', '180'), ('p_definition_language_id', 'smallint', 'NULL'),
        ('p_session_id', 'uuid', 'NULL')]]
