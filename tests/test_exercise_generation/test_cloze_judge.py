"""Tests for the cloze distractor judge.

The judge is an LLM call, so we mock the LLM transport at the module
boundary (services.exercise_generation.cloze_judge.call_llm) and assert
the wiring around it: template loading, prompt formatting, verdict
parsing, fallback behaviour on errors.
"""

from unittest.mock import MagicMock, patch

import pytest

from services.exercise_generation import cloze_judge
from services.exercise_generation.cloze_judge import (
    CLOZE_JUDGE_TASK,
    CLOZE_JUDGE_VERSION,
    filter_distractors,
    judge_distractors,
)


@pytest.fixture(autouse=True)
def clear_template_cache():
    cloze_judge._TEMPLATE_CACHE.clear()
    yield
    cloze_judge._TEMPLATE_CACHE.clear()


def _mock_db(template_text: str | None = "TEMPLATE {sentence_with_blank} {correct_answer} {distractors_numbered}"):
    """Build a mock supabase client whose prompt_templates query returns a row."""
    db = MagicMock()
    chain = db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value
    if template_text is None:
        chain.execute.return_value = MagicMock(data=[])
    else:
        chain.execute.return_value = MagicMock(data=[{'template_text': template_text}])
    return db


# ---------------------------------------------------------------------------
# judge_distractors
# ---------------------------------------------------------------------------

def test_returns_empty_for_no_distractors():
    db = _mock_db()
    out = judge_distractors(db, "x ___ y", "correct", [], language_id=2)
    assert out['verdicts'] == {}
    assert out['version'] == CLOZE_JUDGE_VERSION


def test_keeps_all_when_template_missing():
    db = _mock_db(template_text=None)  # no row -> RuntimeError -> fallback
    out = judge_distractors(db, "x ___ y", "correct", ['a', 'b'], language_id=2)
    assert out['verdicts'] == {'a': 'keep', 'b': 'keep'}


def test_parses_keep_and_reject_verdicts():
    db = _mock_db()
    fake = {
        '1': {'verdict': 'keep',   'reason': 'wrong tense'},
        '2': {'verdict': 'reject', 'reason': 'could be correct'},
        '3': {'verdict': 'keep',   'reason': 'wrong sense'},
    }
    with patch.object(cloze_judge, 'call_llm', return_value=fake) as mock_llm:
        out = judge_distractors(db, "She ___ home.", "ran",
                                ['runs', 'walked', 'eats'], language_id=2)

    mock_llm.assert_called_once()
    assert out['verdicts'] == {'runs': 'keep', 'walked': 'reject', 'eats': 'keep'}
    assert out['reasons']['walked'] == 'could be correct'


def test_unknown_verdict_treated_as_keep():
    db = _mock_db()
    fake = {'1': {'verdict': 'maybe', 'reason': '?'}}
    with patch.object(cloze_judge, 'call_llm', return_value=fake):
        out = judge_distractors(db, "x ___ y", "c", ['a'], language_id=2)
    assert out['verdicts'] == {'a': 'keep'}


def test_keeps_all_on_llm_exception():
    db = _mock_db()
    with patch.object(cloze_judge, 'call_llm', side_effect=RuntimeError("boom")):
        out = judge_distractors(db, "x ___ y", "c", ['a', 'b'], language_id=2)
    assert out['verdicts'] == {'a': 'keep', 'b': 'keep'}


def test_keeps_all_on_non_dict_response():
    db = _mock_db()
    with patch.object(cloze_judge, 'call_llm', return_value="not a dict"):
        out = judge_distractors(db, "x ___ y", "c", ['a'], language_id=2)
    assert out['verdicts'] == {'a': 'keep'}


def test_loads_template_with_correct_task_name():
    db = _mock_db()
    with patch.object(cloze_judge, 'call_llm',
                      return_value={'1': {'verdict': 'keep', 'reason': ''}}):
        judge_distractors(db, "x ___ y", "c", ['a'], language_id=2)
    db.table.assert_called_with('prompt_templates')
    db.table.return_value.select.return_value.eq.assert_called_with(
        'task_name', CLOZE_JUDGE_TASK,
    )


def test_template_cache_avoids_second_db_call():
    db = _mock_db()
    with patch.object(cloze_judge, 'call_llm',
                      return_value={'1': {'verdict': 'keep', 'reason': ''}}):
        judge_distractors(db, "x ___ y", "c", ['a'], language_id=2)
        judge_distractors(db, "x ___ y", "c", ['b'], language_id=2)
    # Only one DB lookup for the template.
    assert db.table.call_count == 1


# ---------------------------------------------------------------------------
# filter_distractors
# ---------------------------------------------------------------------------

def test_filter_returns_kept_and_meta():
    db = _mock_db()
    fake = {
        '1': {'verdict': 'keep',   'reason': 'wrong'},
        '2': {'verdict': 'reject', 'reason': 'synonym'},
        '3': {'verdict': 'keep',   'reason': 'wrong'},
    }
    with patch.object(cloze_judge, 'call_llm', return_value=fake):
        kept, meta = filter_distractors(
            db, "She ___ home.", "ran",
            ['runs', 'walked', 'eats'], language_id=2,
        )
    assert kept == ['runs', 'eats']
    assert meta['rejected'] == 1
    assert meta['rejected_items'] == ['walked']
    assert meta['version'] == CLOZE_JUDGE_VERSION
