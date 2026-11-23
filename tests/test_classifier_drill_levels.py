"""Measure-word drill levels and mastery wiring (TASK-998).

The live get_classifier_drill_session returned no level / answer classifier,
so Auto mode never left level 1 and the player never sent an answer to
update_classifier_mastery. These tests pin, without a database:

* the item shape built from a get_classifier_drill_session_v2 row and from an
  old (v1) row, including the answer classifier fallback that keeps mastery
  recording working before the migration is applied;
* the service's fallback to the v1 function when v2 is missing;
* which item_results reach update_classifier_mastery (validated, capped);
* the migration files: v2 is a new function with the v1 arguments, the
  mastery function keeps its signature and grants, the rollback restores the
  captured definition, the data fill is guarded by an exact row count.

The SQL behaviour itself is checked by
tests/sql/test_task998_classifier_drill_levels.sql (rollback-only).
"""

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import services.drill_service as ds

MIGRATIONS = Path(__file__).resolve().parent.parent / 'migrations'


def _v1_row(**over):
    row = {
        'out_pair_id': 1, 'out_noun_lemma': '书', 'out_noun_sense_id': None,
        'out_noun_gloss': None, 'out_noun_pronunciation': 'shu1',
        'out_correct_classifier_ids': [379, 440], 'out_correct_classifier_hanzi': ['本', '种'],
        'out_distractor_ids': [1, 2, 3], 'out_distractor_hanzi': ['册', '部', '份'],
        'out_distractor_pinyin': ['ce4', 'bu4', 'fen4'], 'out_semantic_label': 'bound',
        'out_distractor_group_label': 'bound', 'out_difficulty_tier': 1,
    }
    row.update(over)
    return row


def _v2_row(**over):
    row = _v1_row(
        out_level=4, out_mastery_level=4, out_classifier_id_primary=379,
        out_reverse_noun_options=['猫', '车', '鱼'],
        out_cloze_sentence='这本书很好看。', out_cloze_blanked='这___书很好看。',
        out_max_tier=1,
    )
    row.update(over)
    return row


# ---------------------------------------------------------------------------
# Item shape
# ---------------------------------------------------------------------------

def test_v2_row_carries_level_primary_reverse_and_cloze():
    item = ds._classifier_item(_v2_row())
    assert item['level'] == 4
    assert item['mastery_level'] == 4
    assert item['classifier_id_primary'] == 379
    assert item['reverse_noun_options'] == ['猫', '车', '鱼']
    assert item['cloze_blanked'] == '这___书很好看。'
    assert item['noun_pronunciation'] == 'shū'


def test_v1_row_names_the_first_correct_classifier_for_mastery():
    """Before the migration: no level, but answers still reach mastery."""
    item = ds._classifier_item(_v1_row())
    assert item['level'] is None
    assert item['classifier_id_primary'] == 379
    assert item['reverse_noun_options'] == []
    assert item['cloze_blanked'] is None


def test_v1_row_without_correct_ids_has_no_primary():
    assert ds._classifier_item(_v1_row(out_correct_classifier_ids=None))['classifier_id_primary'] is None


@pytest.mark.parametrize('over, level', [
    ({'out_cloze_blanked': None}, 3),                                   # no cloze -> Reverse
    ({'out_cloze_blanked': '', 'out_reverse_noun_options': ['猫']}, 2),  # nor 3 reverse nouns -> Type
    ({'out_level': 3, 'out_reverse_noun_options': []}, 2),
    ({'out_level': 9}, 4),
    ({'out_level': 0}, 1),
    ({'out_level': 'x'}, None),
    ({'out_level': 2}, 2),
])
def test_level_never_exceeds_what_the_content_supports(over, level):
    assert ds._classifier_item(_v2_row(**over))['level'] == level


@pytest.mark.parametrize('gloss, answers, expected', [
    ('地图是一张纸，上面画着道路。', ['张', '幅'], '地图是一＿纸，上面画着道路。'),
    ('天然形成的水道，能流入另一条河。', ['条', '道'], '天然形成的水道，能流入另一＿河。'),  # 道 not counted
    ('一种电子设备。', ['台', '种'], '一＿电子设备。'),
    ('每3本书', ['本'], '每3＿书'),
    ('一本书', ['张'], '一本书'),        # not an answer: kept
    ('张开嘴', ['张'], '张开嘴'),        # not counted: kept
    (None, ['张'], None),
    ('', ['张'], ''),
])
def test_gloss_does_not_give_the_answer_away(gloss, answers, expected):
    item = ds._classifier_item(_v2_row(out_noun_gloss=gloss, out_correct_classifier_hanzi=answers))
    assert item['noun_gloss'] == expected


# ---------------------------------------------------------------------------
# Session RPC fallback
# ---------------------------------------------------------------------------

class _MissingFunction(Exception):
    code = 'PGRST202'


def _db_with_rpcs(handlers):
    db = MagicMock()
    called = []

    def rpc(name, params):
        called.append(name)
        result = handlers[name]
        chain = MagicMock()
        if isinstance(result, Exception):
            chain.execute.side_effect = result
        else:
            chain.execute.return_value = SimpleNamespace(data=result)
        return chain

    db.rpc.side_effect = rpc
    db.called = called
    return db


def _drill():
    return ds.DrillService(
        name='classifier_drill', language_id=1, sentinel_slug='__classifier_drill_zh',
        session_rpc='get_classifier_drill_session_v2',
        fallback_session_rpc='get_classifier_drill_session',
        to_item=ds._classifier_item, mastery_rpc='update_classifier_mastery',
    )


def test_session_reads_v2():
    db = _db_with_rpcs({'get_classifier_drill_session_v2': [_v2_row()]})
    with patch.object(ds, 'get_supabase_admin', return_value=db):
        items = _drill().get_session('u', 1, 20)
    assert db.called == ['get_classifier_drill_session_v2']
    assert items[0]['level'] == 4


def test_session_falls_back_to_v1_when_v2_is_missing_and_remembers():
    db = _db_with_rpcs({
        'get_classifier_drill_session_v2': _MissingFunction('Could not find the function'),
        'get_classifier_drill_session': [_v1_row()],
    })
    drill = _drill()
    with patch.object(ds, 'get_supabase_admin', return_value=db):
        first = drill.get_session('u', 1, 20)
        second = drill.get_session('u', 1, 20)
    assert db.called == ['get_classifier_drill_session_v2', 'get_classifier_drill_session',
                         'get_classifier_drill_session']
    assert first[0]['classifier_id_primary'] == 379
    assert second[0]['noun_lemma'] == '书'


def test_session_other_errors_do_not_fall_back():
    db = _db_with_rpcs({'get_classifier_drill_session_v2': RuntimeError('timeout')})
    with patch.object(ds, 'get_supabase_admin', return_value=db):
        assert _drill().get_session('u', 1, 20) == []
    assert db.called == ['get_classifier_drill_session_v2']


def test_registered_classifier_drill_uses_v2_with_v1_fallback():
    assert ds.CLASSIFIER_DRILL.session_rpc == 'get_classifier_drill_session_v2'
    assert ds.CLASSIFIER_DRILL.fallback_session_rpc == 'get_classifier_drill_session'
    assert ds.CLASSIFIER_DRILL.mastery_rpc == 'update_classifier_mastery'
    # The counter drill has no levels or mastery (no per-counter table).
    assert ds.COUNTER_DRILL.mastery_rpc is None
    assert ds.COUNTER_DRILL.fallback_session_rpc is None


# ---------------------------------------------------------------------------
# Mastery updates
# ---------------------------------------------------------------------------

def _mastery_db():
    db = MagicMock()
    sent = []

    def rpc(name, params):
        sent.append((name, params))
        chain = MagicMock()
        chain.execute.return_value = SimpleNamespace(data={'classifier_id': params['p_classifier_id']})
        return chain

    db.rpc.side_effect = rpc
    return db, sent


def test_each_valid_answer_updates_mastery_in_order():
    db, sent = _mastery_db()
    out = _drill()._update_mastery(db, 'u', [
        {'classifier_id': 379, 'is_correct': True, 'level': 1},
        {'classifier_id': 376, 'is_correct': False, 'level': 2},
    ], limit=2)
    # Different classifiers' chains run concurrently, so the order the two
    # calls are SENT in is not fixed; the updates come back in answer order.
    assert sorted((p['p_classifier_id'], p['p_is_correct']) for _, p in sent) == [
        (376, False), (379, True)]
    assert all(n == 'update_classifier_mastery' and p['p_user_id'] == 'u' for n, p in sent)
    assert [row['classifier_id'] for row in out] == [379, 376]


def test_malformed_answers_are_skipped():
    db, sent = _mastery_db()
    _drill()._update_mastery(db, 'u', [
        {'classifier_id': None, 'is_correct': True},
        {'classifier_id': '379', 'is_correct': True},
        {'classifier_id': True, 'is_correct': True},
        {'classifier_id': 0, 'is_correct': True},
        {'classifier_id': 40000, 'is_correct': True},
        'junk',
        {'classifier_id': 379, 'is_correct': 'yes'},  # not a boolean True: counted wrong
    ], limit=20)
    assert [(p['p_classifier_id'], p['p_is_correct']) for _, p in sent] == [(379, False)]


def test_each_classifier_is_updated_in_answer_order_and_results_keep_answer_order():
    """Chains per classifier run concurrently; within a chain the order holds."""
    import threading
    db = MagicMock()
    seen = {}
    lock = threading.Lock()

    def rpc(name, params):
        cid, ok = params['p_classifier_id'], params['p_is_correct']
        chain = MagicMock()

        def execute():
            with lock:
                seen.setdefault(cid, []).append(ok)
                n = len(seen[cid])
            if cid == 376 and n == 2:
                raise RuntimeError('boom')
            return SimpleNamespace(data={'classifier_id': cid, 'n': n})
        chain.execute.side_effect = execute
        return chain

    db.rpc.side_effect = rpc
    answers = [
        {'classifier_id': 379, 'is_correct': True},
        {'classifier_id': 376, 'is_correct': False},
        {'classifier_id': 379, 'is_correct': False},
        {'classifier_id': 376, 'is_correct': True},   # fails: left out
        {'classifier_id': 381, 'is_correct': True},
        {'classifier_id': 379, 'is_correct': True},
    ]
    out = _drill()._update_mastery(db, 'u', answers, limit=20)
    assert seen == {379: [True, False, True], 376: [False, True], 381: [True]}
    assert [(u['classifier_id'], u['n']) for u in out] == [
        (379, 1), (376, 1), (379, 2), (381, 1), (379, 3)]


def test_answers_are_capped_at_the_batch_size_and_forty():
    db, sent = _mastery_db()
    answers = [{'classifier_id': 379, 'is_correct': True}] * 100
    _drill()._update_mastery(db, 'u', answers, limit=20)
    assert len(sent) == 20
    db, sent = _mastery_db()
    _drill()._update_mastery(db, 'u', answers, limit=1000)
    assert len(sent) == ds.MAX_ITEM_RESULTS == 40


def test_submit_passes_total_items_as_the_cap():
    drill = _drill()
    drill._sentinel_test_id = 'sentinel'
    db = MagicMock()
    db.rpc.return_value.execute.return_value = SimpleNamespace(data={'success': True})
    with patch.object(ds, 'get_supabase_admin', return_value=db), \
         patch.object(drill, '_update_mastery', return_value=[]) as upd:
        result = drill.submit_session('u', 1, 14, 2, 3, item_results=[{'classifier_id': 1}])
    upd.assert_called_once()
    assert upd.call_args.kwargs['limit'] == 3
    assert result['mastery_updates'] == []


def test_replayed_submission_does_not_update_mastery_again():
    """process_classifier_drill_submission answers a repeated idempotency key
    with the cached attempt ('cached': true); its answers were already applied."""
    drill = _drill()
    drill._sentinel_test_id = 'sentinel'
    db = MagicMock()
    db.rpc.return_value.execute.return_value = SimpleNamespace(
        data={'success': True, 'cached': True, 'attempt_id': 'a1'})
    with patch.object(ds, 'get_supabase_admin', return_value=db), \
         patch.object(drill, '_update_mastery', return_value=[{'x': 1}]) as upd:
        result = drill.submit_session('u', 1, 14, 1, 1, idempotency_key='k',
                                      item_results=[{'classifier_id': 379, 'is_correct': True}])
    upd.assert_not_called()
    assert result['mastery_updates'] == []
    assert result['attempt_id'] == 'a1'


# ---------------------------------------------------------------------------
# Migration files
# ---------------------------------------------------------------------------

def _read(name):
    return (MIGRATIONS / name).read_text(encoding='utf-8')


def test_v2_is_a_new_function_and_v1_is_untouched():
    sql = _read('task998_classifier_drill_levels.sql')
    assert re.search(r'CREATE OR REPLACE FUNCTION public\.get_classifier_drill_session_v2\(\s*'
                     r'p_user_id\s+uuid,\s*p_language_id\s+smallint,\s*p_count\s+integer DEFAULT 20', sql)
    assert 'FUNCTION public.get_classifier_drill_session(' not in sql
    assert 'REVOKE ALL ON FUNCTION public.get_classifier_drill_session_v2(uuid, smallint, integer)\n' \
           '    FROM PUBLIC, anon, authenticated;' in sql
    assert 'GRANT EXECUTE ON FUNCTION public.get_classifier_drill_session_v2(uuid, smallint, integer) TO service_role;' in sql


def test_v2_returns_the_v1_columns_first_then_the_new_ones():
    sql = _read('task998_classifier_drill_levels.sql')
    v1 = _read('get_classifier_drill_session.sql')

    def cols(text, fn):
        head = text[text.index(f'FUNCTION public.{fn}('):]
        block = head[head.index('RETURNS TABLE ('):head.index(') LANGUAGE')]
        return re.findall(r'\b(out_\w+)\s+\w', block)

    old = cols(v1, 'get_classifier_drill_session')
    new = cols(sql, 'get_classifier_drill_session_v2')
    assert len(old) == 13
    assert new[:13] == old
    assert new[13:] == ['out_level', 'out_mastery_level', 'out_classifier_id_primary',
                        'out_reverse_noun_options', 'out_cloze_sentence', 'out_cloze_blanked',
                        'out_max_tier']
    # Every output column is labelled in the final SELECT, in order.
    final = sql[sql.index('    SELECT\n        wr.pair_id'):sql.index('    FROM with_reverse wr')]
    labels = re.findall(r'\bAS (\w+),?\n', final)
    assert ['out_' + x for x in labels] == new


def test_mastery_function_keeps_signature_security_and_grants():
    sql = _read('task998_classifier_drill_levels.sql')
    assert re.search(r'CREATE OR REPLACE FUNCTION public\.update_classifier_mastery\(\s*'
                     r'p_user_id uuid,\s*p_classifier_id smallint,\s*p_is_correct boolean\s*\) RETURNS jsonb', sql)
    body = sql[sql.index('FUNCTION public.update_classifier_mastery'):]
    body = body[:body.index('$function$;')]
    assert 'SECURITY DEFINER' in body and 'SET search_path = public, pg_temp' in body
    # Promotion counts answers at the current level and restarts them.
    assert 'v_level_n >= 5 AND v_row.ewma_accuracy >= 0.80' in body
    assert body.count('v_level_n := 0;') == 2
    # Old keys are all still returned.
    for key in ('classifier_id', 'attempts', 'correct', 'ewma_accuracy', 'current_level',
                'old_level', 'promoted', 'demoted'):
        assert f"'{key}'" in body
    assert 'REVOKE ALL ON FUNCTION public.update_classifier_mastery(uuid, smallint, boolean)' in sql


def test_forward_migration_is_additive_only():
    sql = _read('task998_classifier_drill_levels.sql')
    code = '\n'.join(l for l in sql.splitlines() if not l.lstrip().startswith('--'))
    for banned in ('DROP ', 'TRUNCATE', 'DELETE ', 'GRANT EXECUTE ON FUNCTION public.get_classifier_drill_session_v2(uuid, smallint, integer) TO authenticated'):
        assert banned not in code
    assert 'ADD COLUMN IF NOT EXISTS level_attempts integer;' in code
    assert 'level_attempts integer DEFAULT' not in code and 'NOT NULL' not in code.split('ADD COLUMN')[1].split(';')[0]


def test_rollback_restores_the_captured_mastery_definition():
    rb = _read('task998_classifier_drill_levels_rollback.sql')
    assert '-- Promotion: attempts >= 5 AND ewma >= 0.80 AND level < 4' in rb
    assert 'IF v_row.attempts >= 5 AND v_row.ewma_accuracy >= 0.80' in rb
    assert 'level_attempts' not in rb.split('$function$;')[0].split('AS $function$')[1]
    assert 'DROP FUNCTION IF EXISTS public.get_classifier_drill_session_v2(uuid, smallint, integer);' in rb
    # The column goes only after the function that writes it is restored.
    assert rb.index('DROP COLUMN IF EXISTS level_attempts') > rb.index('$function$;')


def test_cloze_fill_is_guarded_and_null_only():
    sql = _read('task998_classifier_cloze_sentences_fill.sql')
    code = '\n'.join(l for l in sql.splitlines() if not l.lstrip().startswith('--'))
    assert re.search(r'v_expected constant integer := \d+;', code)
    assert 'IF v_updated <> v_expected THEN\n        RAISE EXCEPTION' in code
    assert "AND (p.example_sentence IS NULL OR p.example_sentence = '');" in code
    assert code.count('UPDATE ') == 1 and 'DELETE' not in code and 'TRUNCATE' not in code
    rb = _read('task998_classifier_cloze_sentences_fill_rollback.sql')
    assert 'SET example_sentence = NULL' in rb
