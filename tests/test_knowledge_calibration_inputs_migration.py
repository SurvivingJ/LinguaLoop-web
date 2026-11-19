"""Static checks of migrations/knowledge_calibration_inputs.sql (TASK-1079).

wiki/features/vocab-placement.tech.md §9, §14; knowledge-report.tech.md §2.6. No database.
The behaviour (report fixture, D and instrument rule, pairs and gap by hand) is covered by
tests/sql/test_knowledge_calibration_inputs.sql (tests/test_calibration_placement_sql.py).
Named apart from tests/test_knowledge_report_migration.py, which the TASK-1034/1036 work owns.
"""
from __future__ import annotations

import re

from tests.test_exercise_content_migration_schema import (
    MIGRATIONS,
    function_def,
    function_defs,
    norm,
    revoke_grant_problems,
    statements,
)
from tests.test_migration_security_lint import scan_file

FILE = 'knowledge_calibration_inputs.sql'
ROLLBACK = 'knowledge_calibration_inputs_rollback.sql'


def read(name: str) -> str:
    return (MIGRATIONS / name).read_text(encoding='utf-8')


def test_signature_exactly_as_tech_14():
    fn = function_def(read(FILE), 'knowledge_calibration_inputs')
    assert fn.params == [
        ('p_user_id', 'uuid', None),
        ('p_language_id', 'smallint', None),
        ('p_as_of', 'timestamptz', 'now()'),
        ('p_window_days', 'integer', '180'),
        ('p_definition_language_id', 'smallint', 'NULL'),
        ('p_session_id', 'uuid', 'NULL'),
    ]
    header = fn.header.upper()
    assert header.startswith('RETURNS JSONB')
    assert 'STABLE' in header and 'SECURITY INVOKER' in header and 'SECURITY DEFINER' not in header
    assert 'SET SEARCH_PATH = PUBLIC, PG_TEMP' in header


def test_service_role_only_and_lint_clean():
    sql = read(FILE)
    fns = function_defs(sql)
    assert [f.name for f in fns] == ['knowledge_calibration_inputs']
    assert revoke_grant_problems(sql, fns[0]) == []
    assert scan_file(MIGRATIONS / FILE) == {'definer': [], 'rls': [], 'client_grant': [], 'uid_compare': []}
    assert not re.search(r'GRANT [^;]* TO (PUBLIC|anon|authenticated)', sql, re.I)


def test_return_keys_exactly_as_tech_14():
    body = function_def(read(FILE), 'knowledge_calibration_inputs').body
    final = body[body.rindex('SELECT jsonb_build_object('):]
    keys = re.findall(r"^\s*'(\w+)',\s", final, re.M)   # one key per line in the final SELECT
    assert keys == ['definition_language_id', 'instrument', 'bands', 'pairs', 'gap', 'alltime_n',
                    'first_at', 'last_at', 'placement_eligible', 'stop_reasons', 'rated_known_in_frame']


def test_sample_rules_in_sql():
    body = norm(function_def(read(FILE), 'knowledge_calibration_inputs').body)
    # legacy: ADR-051 rule 1 rows only
    assert "cs.mode = 'definition' AND cr.instrument IS NULL AND cr.probe_kind IS NULL" in body
    # bare instrument and probes excluded from every sample
    assert "WHEN cfg.instrument = 'meaning_bare_v1' THEN cr.instrument = 'meaning_bare_v1'" in body
    assert 'AND cr.probe_kind IS NULL' in body
    # rank-1 anchors, latest answer per lemma
    assert body.count('a.sense_rank = 1') >= 2
    assert body.count('ORDER BY m.v, m.answered_at DESC, m.id DESC') == 3
    # eligible placement: ended in the window, abandoned only with a frozen result
    assert "(cs.stop_reason <> 'abandoned' OR cs.result IS NOT NULL)" in body
    assert "coalesce(cs.result ->> 'eligible', 'true') <> 'false'" in body
    # pairs from placements only; a due reading must be answered
    assert "m.mode = 'placement'" in body
    assert 'ps AS (SELECT * FROM pj WHERE ex OR NOT mc OR r_ans)' in body
    # ja exempt words are the kana-only lemmas (same regex as the placement helper)
    assert "(p_language_id = 3 AND coalesce(v.lemma ~ '^[ぁ-ゟァ-ヿー・]+$', false))" in body
    # zh roles come from the stored option roles of the reading row
    assert 'rd.option_roles[rd.chosen_position + 1] AS role' in body
    # eligibility (b) precondition
    assert "win.stop_reason IN ('precision', 'cap', 'time', 'exhausted')" in body


def test_report_primary_row_rule():
    body = norm(function_def(read(FILE), 'knowledge_calibration_inputs').body)
    assert ('array_agg(k.p_known ORDER BY k.last_evidence_at DESC NULLS LAST, '
            'k.evidence_count DESC NULLS LAST, k.sense_id))[1]') in body
    assert 'g.wc > g.ww AND g.p_last >= 0.75 AND NOT g.marked_unknown' in body


def test_rollback():
    stmts = [norm(s) for s in statements(read(ROLLBACK))]
    assert stmts == ['DROP FUNCTION IF EXISTS public.knowledge_calibration_inputs'
                     '(uuid, smallint, timestamptz, integer, smallint, uuid)']
