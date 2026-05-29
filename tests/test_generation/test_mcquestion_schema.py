"""
Schema-level tests for MCQuestion.

These cover the normaliser + structural validators directly (no LLM).
A separate test in this module exercises the full call_llm path with a
mocked round-trip to confirm:

  1. Valid first try -> validated model returned.
  2. Invalid first try (answer-not-in-choices) -> repair retry succeeds ->
     validated model returned.
  3. Both attempts invalid -> ValidationError raised.

That covers the change of behaviour from the old silent
`answer = options[0]` fallback to schema+repair.
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from services.test_generation.schemas import MCQuestion
import services.llm_service as svc


# ---------------------------------------------------------------------------
# Schema-only tests
# ---------------------------------------------------------------------------

def test_named_shape_validates_and_indexes_correct_answer():
    q = MCQuestion.model_validate({
        'question_text': 'What is the main idea?',
        'choices': ['First', 'Second', 'Third', 'Fourth'],
        'answer': 'Third',
        'explanation': 'It summarises the passage.',
    })
    assert q.correct_answer_index == 2
    assert q.answer == 'Third'


def test_numeric_key_shape_normalises_to_named_fields():
    q = MCQuestion.model_validate({
        '1': 'What is the main idea?',
        '2': ['Alpha', 'Bravo', 'Charlie', 'Delta'],
        '3': 'Bravo',
        '5': ['x', None, 'y', 'z'],
    })
    assert q.question_text == 'What is the main idea?'
    assert q.correct_answer_index == 1
    assert q.distractor_types == ['x', None, 'y', 'z']


def test_letter_index_answer_is_promoted_to_choice_text():
    q = MCQuestion.model_validate({
        'question_text': '?',
        'choices': ['Alpha', 'Bravo', 'Charlie', 'Delta'],
        'answer': 'A',
    })
    assert q.answer == 'Alpha'
    assert q.correct_answer_index == 0


def test_answer_with_surrounding_whitespace_matches():
    q = MCQuestion.model_validate({
        'question_text': '?',
        'choices': ['Alpha', 'Bravo', 'Charlie', 'Delta'],
        'answer': '  Charlie  ',
    })
    assert q.correct_answer_index == 2


def test_wrong_number_of_choices_rejected():
    with pytest.raises(ValidationError, match='exactly 4'):
        MCQuestion.model_validate({
            'question_text': '?', 'choices': ['A', 'B', 'C'], 'answer': 'A',
        })


def test_answer_not_in_choices_rejected():
    with pytest.raises(ValidationError, match='not in choices'):
        MCQuestion.model_validate({
            'question_text': '?',
            'choices': ['Alpha', 'Bravo', 'Charlie', 'Delta'],
            'answer': 'Echo',
        })


def test_case_insensitive_duplicate_choices_rejected():
    with pytest.raises(ValidationError, match='distinct'):
        MCQuestion.model_validate({
            'question_text': '?',
            'choices': ['Alpha', 'alpha', 'Charlie', 'Delta'],
            'answer': 'Alpha',
        })


def test_empty_answer_rejected():
    with pytest.raises(ValidationError, match='empty'):
        MCQuestion.model_validate({
            'question_text': '?',
            'choices': ['A', 'B', 'C', 'D'],
            'answer': '',
        })


def test_empty_choice_after_strip_rejected():
    with pytest.raises(ValidationError, match='non-empty'):
        MCQuestion.model_validate({
            'question_text': '?',
            'choices': ['A', '   ', 'C', 'D'],
            'answer': 'A',
        })


def test_distractor_types_with_wrong_length_rejected():
    with pytest.raises(ValidationError, match='distractor_types must have 4'):
        MCQuestion.model_validate({
            'question_text': '?',
            'choices': ['Alpha', 'Bravo', 'Charlie', 'Delta'],
            'answer': 'Alpha',
            'distractor_types': [None, 'semantic', 'contextual'],
        })


def test_distractor_types_correct_slot_must_be_null():
    # 'Bravo' is the answer (index 1); its slot must be null, not a tag.
    with pytest.raises(ValidationError, match='must be null'):
        MCQuestion.model_validate({
            'question_text': '?',
            'choices': ['Alpha', 'Bravo', 'Charlie', 'Delta'],
            'answer': 'Bravo',
            'distractor_types': ['semantic', 'grammatical', 'contextual', 'semantic'],
        })


def test_distractor_types_valid_with_null_at_answer_index():
    q = MCQuestion.model_validate({
        'question_text': '?',
        'choices': ['Alpha', 'Bravo', 'Charlie', 'Delta'],
        'answer': 'Bravo',
        'distractor_types': ['semantic', None, 'contextual', 'grammatical'],
    })
    assert q.correct_answer_index == 1
    assert q.distractor_types == ['semantic', None, 'contextual', 'grammatical']


def test_distractor_types_absent_is_allowed():
    q = MCQuestion.model_validate({
        'question_text': '?',
        'choices': ['Alpha', 'Bravo', 'Charlie', 'Delta'],
        'answer': 'Alpha',
    })
    assert q.distractor_types is None


# ---------------------------------------------------------------------------
# Integration: schema + call_llm repair path
# ---------------------------------------------------------------------------

def _stub_seq(parsed_outputs):
    """Build a stub _make_one_call that yields parsed_outputs in order."""
    it = iter(parsed_outputs)

    def stub(**kw):
        parsed = next(it)
        # (parsed, raw_content, parsed_ok, latency_ms)
        return parsed, repr(parsed), True, 42
    return stub


@pytest.fixture(autouse=True)
def _silence_db_and_client():
    """Suppress llm_calls logging and the OpenAI client construction."""
    with patch.object(svc, '_log_llm_call', lambda **kw: None), \
         patch.object(svc, 'get_client', lambda *a, **kw: None):
        yield


def test_call_llm_valid_first_try_returns_validated_model():
    output = {
        'question_text': 'Q?',
        'choices': ['A', 'B', 'C', 'D'],
        'answer': 'C',
    }
    with patch.object(svc, '_make_one_call', _stub_seq([output])):
        result = svc.call_llm(
            'prompt',
            schema=MCQuestion,
            response_format='json_object',
            pipeline='test_gen',
            task_name='question_main_idea',
        )
    assert isinstance(result, MCQuestion)
    assert result.correct_answer_index == 2


def test_call_llm_answer_not_in_choices_repaired():
    # First attempt: answer doesn't match any choice → triggers repair retry.
    bad = {
        'question_text': 'Q?',
        'choices': ['Alpha', 'Bravo', 'Charlie', 'Delta'],
        'answer': 'Foxtrot',
    }
    # Repair turn: model fixes the answer.
    good = {
        'question_text': 'Q?',
        'choices': ['Alpha', 'Bravo', 'Charlie', 'Delta'],
        'answer': 'Charlie',
    }
    with patch.object(svc, '_make_one_call', _stub_seq([bad, good])):
        result = svc.call_llm(
            'prompt',
            schema=MCQuestion,
            response_format='json_object',
            pipeline='test_gen',
            task_name='question_main_idea',
        )
    assert isinstance(result, MCQuestion)
    assert result.answer == 'Charlie'
    assert result.correct_answer_index == 2


def test_call_llm_persistent_invalid_raises():
    bad1 = {'question_text': 'Q?', 'choices': ['A', 'B', 'C'], 'answer': 'A'}
    bad2 = {'question_text': 'Q?', 'choices': ['A', 'B', 'C'], 'answer': 'A'}
    with patch.object(svc, '_make_one_call', _stub_seq([bad1, bad2])):
        with pytest.raises(ValidationError):
            svc.call_llm(
                'prompt',
                schema=MCQuestion,
                response_format='json_object',
                pipeline='test_gen',
                task_name='question_main_idea',
            )
