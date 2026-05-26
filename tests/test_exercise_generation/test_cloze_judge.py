"""Tests for the cloze distractor judge.

The judge is an LLM call, so we mock the LLM transport at the module
boundary (services.exercise_generation.judges.cloze.call_llm) and assert
the wiring around it: template loading, prompt formatting, verdict
parsing, fallback behaviour on errors.

cloze_judge.py is now a backward-compat shim; the implementation lives in
services.exercise_generation.judges.cloze.  All tests target that module
directly via ``from services.exercise_generation.judges import cloze as
cloze_judge`` so patch.object / cache manipulation hit the live module.
"""

from unittest.mock import MagicMock, patch

import pytest

from services.exercise_generation.judges import cloze as cloze_judge
from services.exercise_generation.judges.cloze import (
    filter_distractors,
    judge_distractors,
)

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

_FAKE_CFG = {
    'template': 'TEMPLATE {sentence_with_blank} {correct_answer} {distractors_numbered}',
    'model': 'google/gemini-2.5-flash-lite',
    'provider': 'openrouter',
    'version': 1,
}
_CACHE_KEY = (cloze_judge._TASK_NAME, 2)   # task_name + language_id=2


@pytest.fixture(autouse=True)
def clear_template_cache():
    """Pre-populate _cfg_cache so tests don't hit the DB via get_template_config."""
    cloze_judge._cfg_cache.clear()
    cloze_judge._cfg_cache[_CACHE_KEY] = _FAKE_CFG
    yield
    cloze_judge._cfg_cache.clear()


# ---------------------------------------------------------------------------
# judge_distractors
# ---------------------------------------------------------------------------

def test_returns_empty_for_no_distractors():
    db = MagicMock()
    out = judge_distractors(db, "x ___ y", "correct", [], language_id=2)
    assert out['verdicts'] == {}
    # _empty_result is returned before cfg is loaded, so version is 0.
    assert out['version'] == 0


def test_keeps_all_when_template_missing():
    # Evict pre-populated entry so _load_cfg calls get_template_config.
    cloze_judge._cfg_cache.clear()
    db = MagicMock()
    with patch.object(cloze_judge, 'get_template_config',
                      side_effect=RuntimeError("no row")):
        out = judge_distractors(db, "x ___ y", "correct", ['a', 'b'], language_id=2)
    assert out['verdicts'] == {'a': 'keep', 'b': 'keep'}


def test_parses_keep_and_reject_verdicts():
    db = MagicMock()
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
    db = MagicMock()
    fake = {'1': {'verdict': 'maybe', 'reason': '?'}}
    with patch.object(cloze_judge, 'call_llm', return_value=fake):
        out = judge_distractors(db, "x ___ y", "c", ['a'], language_id=2)
    assert out['verdicts'] == {'a': 'keep'}


def test_keeps_all_on_llm_exception():
    db = MagicMock()
    with patch.object(cloze_judge, 'call_llm', side_effect=RuntimeError("boom")):
        out = judge_distractors(db, "x ___ y", "c", ['a', 'b'], language_id=2)
    assert out['verdicts'] == {'a': 'keep', 'b': 'keep'}


def test_keeps_all_on_non_dict_response():
    db = MagicMock()
    with patch.object(cloze_judge, 'call_llm', return_value="not a dict"):
        out = judge_distractors(db, "x ___ y", "c", ['a'], language_id=2)
    assert out['verdicts'] == {'a': 'keep'}


def test_loads_template_with_correct_task_name():
    # Evict pre-populated entry so _load_cfg calls get_template_config.
    cloze_judge._cfg_cache.clear()
    db = MagicMock()
    with patch.object(cloze_judge, 'get_template_config',
                      return_value=_FAKE_CFG) as mock_cfg:
        with patch.object(cloze_judge, 'call_llm',
                          return_value={'1': {'verdict': 'keep', 'reason': ''}}):
            judge_distractors(db, "x ___ y", "c", ['a'], language_id=2)
    mock_cfg.assert_called_once_with(db, cloze_judge._TASK_NAME, 2)


def test_template_cache_avoids_second_db_call():
    # Start cold so the first call populates the cache.
    cloze_judge._cfg_cache.clear()
    db = MagicMock()
    with patch.object(cloze_judge, 'get_template_config',
                      return_value=_FAKE_CFG) as mock_cfg:
        with patch.object(cloze_judge, 'call_llm',
                          return_value={'1': {'verdict': 'keep', 'reason': ''}}):
            judge_distractors(db, "x ___ y", "c", ['a'], language_id=2)
            judge_distractors(db, "x ___ y", "c", ['b'], language_id=2)
    # Second call hits the in-process cache; get_template_config called only once.
    assert mock_cfg.call_count == 1


# ---------------------------------------------------------------------------
# filter_distractors
# ---------------------------------------------------------------------------

def test_filter_returns_kept_and_meta():
    db = MagicMock()
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
    assert meta['version'] == 1   # _FAKE_CFG['version']
