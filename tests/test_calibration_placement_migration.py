"""Static checks of the vocabulary-placement migrations (TASK-1076, TASK-1077).

wiki/features/vocab-placement.tech.md §13 (schema), §14 (functions), §18 (security).
No database: the SQL is parsed. The behaviour (scripted sessions, tallies against a
hand count, probes, ownership, close, rechecks) is covered by
tests/sql/test_calibration_placement.sql, which tests/test_calibration_placement_sql.py
runs when PLACEMENT_TEST_DSN points at a harness database.
"""
from __future__ import annotations

import re

import pytest

from tests.test_exercise_content_migration_schema import (
    MIGRATIONS,
    bare_statements,
    code_without_strings,
    function_def,
    function_defs,
    norm,
    revoke_grant_problems,
    statements,
)
from tests.test_migration_security_lint import scan_file

SCHEMA = 'calibration_placement.sql'
SCHEMA_RB = 'calibration_placement_rollback.sql'
RPCS = 'calibration_placement_rpcs.sql'
RPCS_RB = 'calibration_placement_rpcs_rollback.sql'


def read(name: str) -> str:
    return (MIGRATIONS / name).read_text(encoding='utf-8')


def code(name: str) -> str:
    """The file without comments, whitespace collapsed (statements re-joined)."""
    return ' '.join(norm(s) for s in statements(read(name)))


def in_types(fn) -> tuple[str, ...]:
    """IN parameter types (OUT parameters are not part of the signature)."""
    return tuple(t for n, t, _d in fn.params if n.upper() != 'OUT')


class _InOnly:
    def __init__(self, fn):
        self.name = fn.name
        self.arg_types = in_types(fn)


# --------------------------------------------------------------------------------------
# TASK-1076: schema
# --------------------------------------------------------------------------------------
NEW_RESPONSE_COLUMNS = {
    'item_kind': 'text',
    'probe_kind': 'text',
    'instrument': 'text',
    'pair_response_id': 'bigint',
    'option_sense_ids': 'integer[]',
    'key_position': 'smallint',
    'option_roles': 'text[]',
    'option_texts': 'text[]',
    'chosen_position': 'smallint',
}
NEW_SESSION_COLUMNS = {'stop_reason': 'text', 'result': 'jsonb'}

CHECKS = {
    'calibration_sessions_mode_chk':
        "CHECK (mode IN ('definition', 'pronunciation', 'placement'))",
    'calibration_sessions_stop_reason_chk':
        "CHECK (stop_reason IS NULL OR stop_reason IN "
        "('precision', 'cap', 'time', 'exhausted', 'learner', 'abandoned'))",
    'calibration_responses_item_kind_chk':
        "CHECK (item_kind IS NULL OR item_kind IN ('meaning', 'reading', 'sound_pair'))",
    'calibration_responses_probe_kind_chk':
        "CHECK (probe_kind IS NULL OR probe_kind IN "
        "('recheck', 'reading_after_miss', 'forced_guess', 'sound_pair'))",
    'calibration_responses_instrument_chk':
        "CHECK (instrument IS NULL OR instrument IN ('meaning_bare_v1', 'reading_v1', 'reading_tone_v1'))",
}


@pytest.mark.parametrize('table,cols', [('calibration_responses', NEW_RESPONSE_COLUMNS),
                                        ('calibration_sessions', NEW_SESSION_COLUMNS)])
def test_new_columns_are_nullable_without_default(table, cols):
    sql = code(SCHEMA)
    for col, typ in cols.items():
        m = re.search(rf'ADD COLUMN IF NOT EXISTS {col} (\S+(?: \S+)?) NULL(?=,| |$)', sql)
        assert m, f'{table}.{col} not added as a nullable column'
        assert m.group(1).lower() == typ, f'{col}: {m.group(1)} != {typ}'
    # no rewrite: no DEFAULT, no NOT NULL, no type change anywhere in the schema file
    assert ' DEFAULT ' not in sql.upper()
    assert not re.search(r'(?<!IS )NOT NULL', sql.upper())   # index predicates use IS NOT NULL
    assert 'ALTER COLUMN' not in sql.upper()


@pytest.mark.parametrize('name,check', sorted(CHECKS.items()))
def test_checks_exact_not_valid_then_validated(name, check):
    stmts = [norm(s) for s in statements(read(SCHEMA))]
    adds = [s for s in stmts if f'ADD CONSTRAINT {name}' in s]
    assert len(adds) == 1, name
    assert adds[0].endswith(f'{check} NOT VALID'), adds[0]
    validate = [i for i, s in enumerate(stmts) if s.endswith(f'VALIDATE CONSTRAINT {name}')]
    commit = stmts.index('COMMIT')
    assert validate and validate[0] > commit, f'{name}: VALIDATE must run after the COMMIT'


def test_pair_fk_and_indexes():
    sql = code(SCHEMA)
    assert ('ADD CONSTRAINT calibration_responses_pair_response_id_fkey FOREIGN KEY (pair_response_id) '
            'REFERENCES public.calibration_responses(id) ON DELETE CASCADE NOT VALID') in sql
    assert 'VALIDATE CONSTRAINT calibration_responses_pair_response_id_fkey' in sql
    assert ('CREATE INDEX IF NOT EXISTS idx_calibration_responses_user_vocab_answered ON '
            'public.calibration_responses (user_id, anchor_vocab_id) WHERE answered_at IS NOT NULL') in sql
    assert ('CREATE INDEX IF NOT EXISTS idx_calibration_responses_pair ON public.calibration_responses '
            '(pair_response_id) WHERE pair_response_id IS NOT NULL') in sql


def test_schema_grants_nothing_and_touches_no_row():
    upper = code(SCHEMA).upper()
    for word in ('GRANT ', 'INSERT ', 'UPDATE ', 'DELETE ', 'TRUNCATE', 'CREATE TABLE'):
        assert word not in upper.replace('ON DELETE CASCADE', ''), word


def test_schema_rollback_is_symmetric():
    rb = code(SCHEMA_RB)
    for col in list(NEW_RESPONSE_COLUMNS) + list(NEW_SESSION_COLUMNS):
        assert f'DROP COLUMN IF EXISTS {col}' in rb, col
    for name in list(CHECKS) + ['calibration_responses_pair_response_id_fkey']:
        assert f'DROP CONSTRAINT IF EXISTS {name}' in rb, name
    for idx in ('idx_calibration_responses_user_vocab_answered', 'idx_calibration_responses_pair'):
        assert f'DROP INDEX IF EXISTS public.{idx}' in rb, idx
    assert ("ADD CONSTRAINT calibration_sessions_mode_chk CHECK (mode IN ('definition', 'pronunciation'))"
            in rb)
    # refuses to drop placement data silently
    assert "WHERE mode = 'placement'" in rb and 'RAISE EXCEPTION' in rb


# --------------------------------------------------------------------------------------
# TASK-1077: functions
# --------------------------------------------------------------------------------------
# tech §14 signatures: (name, [(param, type, default)], returns, definer)
PUBLIC_API = {
    'calibration_placement_ready_counts': (
        [('p_word_language_id', 'smallint', None), ('p_definition_language_id', 'smallint', None)],
        'jsonb', False),
    'calibration_placement_next_item': (
        [('p_user_id', 'uuid', None), ('p_session_id', 'uuid', None), ('p_band', 'smallint', None),
         ('p_exclude_days', 'integer', '180')],
        'jsonb', True),
    'calibration_placement_answer': (
        [('p_user_id', 'uuid', None), ('p_session_id', 'uuid', None), ('p_response_id', 'bigint', None),
         ('p_position', 'smallint', None), ('p_latency_ms', 'integer', None),
         ('p_next_band', 'smallint', None), ('p_draws', 'jsonb', None)],
        'jsonb', True),
    'calibration_placement_close': (
        [('p_user_id', 'uuid', None), ('p_session_id', 'uuid', None), ('p_reason', 'text', None)],
        'jsonb', True),
    'calibration_placement_close_stale': (
        [('p_user_id', 'uuid', None), ('p_older_than', 'interval', "'24 hours'")],
        'uuid[]', True),
}


def _returns(fn) -> str:
    m = re.match(r'RETURNS (.+?) LANGUAGE', fn.header, re.I)
    return m.group(1).lower() if m else ''


@pytest.mark.parametrize('name', sorted(PUBLIC_API))
def test_public_signatures_exact(name):
    params, returns, definer = PUBLIC_API[name]
    fn = function_def(read(RPCS), name)
    assert fn.or_replace
    assert fn.params == params, fn.params
    assert _returns(fn) == returns
    assert ('SECURITY DEFINER' in fn.header.upper()) == definer
    if name == 'calibration_placement_ready_counts':
        assert 'STABLE' in fn.header.upper()


def test_every_function_locked_down():
    sql = read(RPCS)
    fns = function_defs(sql)
    assert len(fns) >= 30
    problems = []
    for fn in fns:
        if not re.search(r'SET search_path = public, pg_temp', fn.header):
            problems.append(f'{fn.name}: no SET search_path')
        problems += revoke_grant_problems(sql, _InOnly(fn))
    assert not problems, problems
    assert all(fn.name.startswith('calibration_placement_') for fn in fns)
    assert scan_file(MIGRATIONS / RPCS) == {'definer': [], 'rls': [], 'client_grant': [], 'uid_compare': []}
    assert scan_file(MIGRATIONS / SCHEMA) == {'definer': [], 'rls': [], 'client_grant': [], 'uid_compare': []}


def test_only_writers_are_definers():
    definers = {fn.name for fn in function_defs(read(RPCS)) if 'SECURITY DEFINER' in fn.header.upper()}
    assert definers == {'calibration_placement_next_item', 'calibration_placement_answer',
                        'calibration_placement_close', 'calibration_placement_close_stale'}


def test_rollback_drops_every_function():
    created = {(fn.name, in_types(fn)) for fn in function_defs(read(RPCS))}
    rb = code(RPCS_RB)
    for name, types in created:
        assert f'DROP FUNCTION IF EXISTS public.{name}({", ".join(types)})' in rb, name
    assert len(re.findall(r'DROP FUNCTION IF EXISTS', rb)) == len(created)
    assert 'calibration_zh_tone_variants' not in rb


def test_requires_schema_and_zh_tone_variants_first():
    sql = code(RPCS)
    assert "column_name = 'option_roles'" in sql
    assert "to_regprocedure('public.calibration_zh_tone_variants(text,integer)') IS NULL" in sql
    # called with the TASK-1092 signature (text, integer)
    for m in re.finditer(r'calibration_zh_tone_variants\(([^()]*)\)', code_without_strings(read(RPCS))):
        assert len(m.group(1).split(',')) == 2, m.group(0)


def test_ownership_and_error_codes():
    sql = read(RPCS)
    for name in ('calibration_placement_next_item', 'calibration_placement_answer',
                 'calibration_placement_close'):
        body = norm(function_def(sql, name).body)
        assert ("WHERE id = p_session_id AND user_id = p_user_id AND mode = 'placement' FOR UPDATE" in body), name
        assert "USING ERRCODE = 'P0002'" in body, name
    answer = norm(function_def(sql, 'calibration_placement_answer').body)
    assert answer.count("USING ERRCODE = '22023'") >= 5   # closed, band, draws, foreign, answered, position
    assert 'answered_at IS NOT NULL THEN RAISE' in answer
    assert 'least(greatest(p_latency_ms, 0), 600000)' in answer


def test_probe_rules_use_injected_draws_only():
    body = code_without_strings(function_def(read(RPCS), 'calibration_placement_answer').body)
    flat = norm(body)
    # random() only as the fallback seed when u_seed is missing, never for a probe decision
    assert flat.count('random()') == 1 and 'v_u_seed := random()' in flat
    assert 'v_u_probe < 0.15 AND v_probes < 4 AND v_fg < 2' in flat          # forced_guess
    assert 'v_u_probe < 0.25 AND v_probes < 4 AND v_ram < 2' in flat         # reading_after_miss
    assert 'v_l = 3 AND v_correct AND v_u_probe < 0.5 AND v_probes < 4 AND v_sp < 2' in flat  # sound_pair, ja only
    assert 'v_scored_rows = 0 AND v_rc < 2 AND v_probes < 4' in flat         # second recheck


def test_payload_never_carries_a_key():
    sql = read(RPCS)
    for name in ('calibration_placement_insert_item', 'calibration_placement_item_payload'):
        body = norm(function_def(sql, name).body)
        keys = re.findall(r"'(\w+)',\s", body.split('jsonb_build_object(', 1)[1])
        assert set(keys) <= {'response_id', 'vocab_id', 'lemma', 'band', 'kind', 'probe_kind',
                             'options', 'idk_allowed'}, keys


def test_item_rules_in_sql():
    sql = read(RPCS)
    strip = norm(function_def(sql, 'calibration_placement_strip_definition').body)
    assert r"'^\s*[^；;—]{1,12}\s*(；|;|——|—)\s*'" in strip           # tech §2 rule 5
    assert '((1, 3), (3, 1))' in strip                                   # cross-CJK pairs only
    units = norm(function_def(sql, 'calibration_placement_units').body)
    assert "'[ゃゅょぁぃぅぇぉャュョァィゥェォ]'" in units               # rule 3 (ja, display form)
    assert r"regexp_split_to_array(btrim(p_text), '\s+')" in units      # rule 3 (zh, display form)
    kana = norm(function_def(sql, 'calibration_placement_kana_pattern').body)
    assert "'^' || regexp_replace(p_lemma, '[^ぁ-ゟー]+', '.+', 'g') || '$'" in kana  # rule 3b
    tone = norm(function_def(sql, 'calibration_placement_toneless').body)
    assert "'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü', 'aaaaeeeeiiiioooouuuuvvvvv'" in tone   # rule 4
    parts = norm(function_def(sql, 'calibration_placement_reading_parts').body)
    assert "jsonb_build_array('K', 'KT', 'F', 'FT')" in parts
    assert 'calibration_placement_toneless(o.option_text) <> calibration_placement_toneless(p_key)' in parts
    assert 'o.option_text ~ calibration_placement_kana_pattern(p_lemma)' in parts
    meaning = norm(function_def(sql, 'calibration_placement_meaning_parts').body)
    assert "calibration_cached_options('definition', p_anchor_sense_id)" in meaning
    assert 'LIMIT 3' in meaning and "'rule5'" in meaning
    cand = norm(function_def(sql, 'calibration_placement_candidates').body)
    assert 's.sense_rank = 1' in cand and 'p.has_embedding' in cand
    assert 'r.answered_at > now() - make_interval(days =>' in cand


def test_no_table_ddl_or_grants_to_clients_in_rpcs():
    upper = ' '.join(bare_statements(read(RPCS))).upper()
    assert 'CREATE TABLE' not in upper and 'ALTER TABLE' not in upper
    assert not re.search(r'GRANT [^;]* TO (PUBLIC|ANON|AUTHENTICATED)', upper)


def test_schema_refuses_when_keys_would_be_readable():
    sql = code(SCHEMA)
    assert "has_table_privilege('anon', 'public.calibration_responses', 'SELECT')" in sql
    assert "has_table_privilege('authenticated', 'public.calibration_responses', 'SELECT')" in sql
    assert sql.index('has_table_privilege') < sql.index('ADD COLUMN')
