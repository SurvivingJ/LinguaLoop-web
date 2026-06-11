"""Integration tests for ClozeGenerator + cloze_judge.

We mock the LLM transport and the judge result to assert that:
- the judge gets called on every generated cloze
- distractors flagged 'reject' are dropped before the result is returned
- judge metadata lands in tags via _build_tags
- when the judge leaves < 3 distractors and retry also fails, generate_one returns None

cloze_judge.py is now a backward-compat shim; the implementation lives in
services.exercise_generation.judges.cloze.  Tests target that module
directly so patch.object / cache manipulation hit the live module.
"""

from unittest.mock import MagicMock, patch

import pytest

from services.exercise_generation.judges import cloze as cloze_judge
from services.exercise_generation.generators.cloze import ClozeGenerator

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_FAKE_JUDGE_CFG = {
    'template': 'JUDGE {sentence_with_blank} {correct_answer} {distractors_numbered}',
    'model': 'google/gemini-2.5-flash-lite',
    'provider': 'openrouter',
    'version': 1,
}
_CACHE_KEY = (cloze_judge._TASK_NAME, 2)   # task_name + language_id=2


@pytest.fixture(autouse=True)
def clear_judge_cache():
    """Pre-populate _cfg_cache so tests don't hit the DB via get_template_config."""
    cloze_judge._cfg_cache.clear()
    cloze_judge._cfg_cache[_CACHE_KEY] = _FAKE_JUDGE_CFG
    yield
    cloze_judge._cfg_cache.clear()


def _make_generator():
    db = MagicMock()
    # Judge template is pre-populated in _cfg_cache by the fixture;
    # no DB chain setup needed for the judge lookup.
    gen = ClozeGenerator(db, language_id=2, model='test-model', source_type='grammar')
    # Bypass the target-selection LLM call.
    gen._identify_target_word = MagicMock(return_value='ran')
    return gen


def _distractor_payload(distractors, tags=None):
    return {
        'distractors': distractors,
        'distractor_tags': tags or {d: 'semantic' for d in distractors},
        'explanation': 'because',
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_judge_keeps_all_returns_full_result():
    gen = _make_generator()
    gen._generate_distractors = MagicMock(
        return_value=_distractor_payload(['runs', 'walked', 'eats']),
    )

    judge_response = {
        '1': {'verdict': 'keep', 'reason': 'wrong tense'},
        '2': {'verdict': 'keep', 'reason': 'wrong sense'},
        '3': {'verdict': 'keep', 'reason': 'wrong concept'},
    }
    with patch.object(cloze_judge, 'call_llm', return_value=judge_response):
        result = gen.generate_one(
            {'sentence': 'She ran home.', 'complexity_tier': 'T3'},
            source_id=1,
        )

    assert result is not None
    assert result['options'] == ['ran', 'runs', 'walked', 'eats']
    assert gen._last_judge_meta['rejected'] == 0


def test_judge_rejects_one_retry_succeeds():
    gen = _make_generator()
    gen._generate_distractors = MagicMock(side_effect=[
        _distractor_payload(['runs', 'walked', 'eats']),    # first call
        _distractor_payload(['galloped', 'sprinted', 'ate']),  # retry
    ])

    # First judge call rejects 'walked'; second judge call keeps all.
    responses = [
        {
            '1': {'verdict': 'keep',   'reason': 'wrong tense'},
            '2': {'verdict': 'reject', 'reason': 'synonym'},
            '3': {'verdict': 'keep',   'reason': 'wrong concept'},
        },
        {
            '1': {'verdict': 'keep', 'reason': 'past participle wrong'},
            '2': {'verdict': 'keep', 'reason': 'wrong tense'},
            '3': {'verdict': 'keep', 'reason': 'wrong concept'},
        },
    ]
    with patch.object(cloze_judge, 'call_llm', side_effect=responses):
        result = gen.generate_one(
            {'sentence': 'She ran home.', 'complexity_tier': 'T3'},
            source_id=1,
        )

    assert result is not None
    assert result['correct_answer'] == 'ran'
    # Distractors are POOLED across batches (see ClozeGenerator docstring):
    # the two batch-1 survivors ('runs', 'eats') are kept and topped up from the
    # retry batch ('galloped'), then trimmed to the first 3.
    assert result['options'] == ['ran', 'runs', 'eats', 'galloped']
    assert gen._last_judge_meta['rejected'] >= 1
    assert 'walked' in gen._last_judge_meta['rejected_items']


def test_judge_rejects_repeatedly_returns_none():
    gen = _make_generator()
    gen._generate_distractors = MagicMock(side_effect=[
        _distractor_payload(['a', 'b', 'c']),
        _distractor_payload(['d', 'e', 'f']),
    ])

    reject_all = {
        '1': {'verdict': 'reject', 'reason': 'r'},
        '2': {'verdict': 'reject', 'reason': 'r'},
        '3': {'verdict': 'reject', 'reason': 'r'},
    }
    with patch.object(cloze_judge, 'call_llm', return_value=reject_all):
        result = gen.generate_one(
            {'sentence': 'She ran home.', 'complexity_tier': 'T3'},
            source_id=1,
        )

    assert result is None
    assert gen._last_judge_meta is None


def test_build_tags_includes_judge_meta_after_generation():
    gen = _make_generator()
    gen._generate_distractors = MagicMock(
        return_value=_distractor_payload(['a', 'b', 'c']),
    )
    keep_all = {
        '1': {'verdict': 'keep', 'reason': ''},
        '2': {'verdict': 'keep', 'reason': ''},
        '3': {'verdict': 'keep', 'reason': ''},
    }
    with patch.object(cloze_judge, 'call_llm', return_value=keep_all):
        gen.generate_one(
            {'sentence': 'She ran home.', 'complexity_tier': 'T3'},
            source_id=1,
        )

    tags = gen._build_tags(
        source_id=1,
        sentence_dict={'sentence': 'She ran home.', 'complexity_tier': 'T3'},
    )
    assert 'cloze_judge' in tags
    assert tags['cloze_judge']['rejected'] == 0
    assert tags['cloze_judge']['version'] >= 1


def test_distractor_payload_failure_returns_none_without_judge_call():
    gen = _make_generator()
    gen._generate_distractors = MagicMock(return_value=None)

    with patch.object(cloze_judge, 'call_llm') as mock_llm:
        result = gen.generate_one(
            {'sentence': 'She ran home.', 'complexity_tier': 'T3'},
            source_id=1,
        )

    assert result is None
    mock_llm.assert_not_called()
