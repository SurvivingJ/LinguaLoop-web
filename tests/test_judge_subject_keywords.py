"""The distractor judge's subject/domain slot must actually be populated.

Why this file exists: `judge_distractor_plausibility` has accepted a
``keywords=`` argument since v3, and its ONLY caller never passed it. Prompt
slot ``{5}`` therefore always rendered the fallback
"(infer the subject from the passage above)" in production, for every question
in every language, for the whole life of v3 and v4.

That mattered because band 2 ("off-topic / different subject") IS a
domain-membership test and produced 100% of all zh and ja rejects — the judge
was being asked to invent the domain boundary it was then scoring against. A
model that infers narrowly rejects; one that infers broadly accepts, which is
most of the measured qwen/gemini divergence.

Nothing failed when the parameter went dead. No test broke, no log fired, the
prompt rendered fine — it just quietly stopped carrying signal, and it took a
450-distractor sample to notice. These tests make it fail loudly instead:
`test_keywords_reach_the_rendered_prompt_end_to_end` drives the real
orchestrator-facing entry point and asserts the topic data comes out the far
end inside the actual prompt string.

See wiki/evaluations/distractor-judge-language-divergence-2026-08-16 §4.
"""

from unittest.mock import MagicMock, patch

import pytest

import services.exercise_generation.judges.distractor_plausibility as dp_mod
import services.test_generation.agents.question_generator as qg_mod
from services.exercise_generation.judges.base import JudgeOutcome
from services.exercise_generation.judges.distractor_plausibility import (
    judge_distractor_plausibility,
)
from services.test_generation.agents.question_generator import (
    QuestionGenerator,
    _format_subject,
)
from services.test_generation.orchestrator import _subject_kwargs
from services.test_generation.schemas import (
    DistractorPlausibilityVerdict,
    MCQuestion,
)

# Mirrors the live v5 row's slot layout: the judge fills six positional args
# and {4}/{5} are the two this file is about.
FAKE_TEMPLATE = (
    'passage={0}\nquestion={1}\nanswer={2}\ndistractors={3}\n'
    'TYPE={4}\nSUBJECT={5}\n'
)


def _cfg():
    return {'template': FAKE_TEMPLATE, 'model': 'vendor/model', 'version': 5}


def _capture_judge_prompt(**judge_kwargs):
    """Run the judge against a stub LLM and return the prompt it rendered."""
    seen = {}

    def fake_call_llm(prompt, **kw):
        seen['prompt'] = prompt
        return DistractorPlausibilityVerdict(
            per_distractor=[5, 5, 5], reasons=['a', 'b', 'c'])

    with patch.object(dp_mod, '_load_cfg', return_value=_cfg()), \
         patch.object(dp_mod, 'call_llm', side_effect=fake_call_llm), \
         patch.object(dp_mod, 'log_judge_verdict', lambda **kw: None):
        judge_distractor_plausibility(
            db=MagicMock(), passage='p', question_text='q?', answer='a',
            distractors=['d1', 'd2', 'd3'], language_id=1, **judge_kwargs,
        )
    return seen['prompt']


# ---------------------------------------------------------------------------
# _format_subject — how the topic data becomes the one string the slot takes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('concept, keywords, expected', [
    ('Urban gardening', ['compost', 'soil'], 'Urban gardening: compost, soil'),
    ('Urban gardening', [], 'Urban gardening'),
    ('Urban gardening', None, 'Urban gardening'),
    (None, ['compost', 'soil'], 'compost, soil'),
    ('', [''], ''),
    (None, None, ''),
])
def test_format_subject_shapes(concept, keywords, expected):
    assert _format_subject(concept, keywords) == expected


def test_format_subject_drops_blank_keywords_without_leaving_separators():
    """The translator returns a free-form list; blank entries must not render
    as a dangling ', ' that reads to the judge as an empty domain."""
    assert _format_subject('Topic', ['a', '', '  ', 'b']) == 'Topic: a, b'


def test_empty_subject_restores_the_infer_from_passage_fallback():
    """No topic data must mean "infer it", never an assertion of a blank
    domain — a blank domain line would make band 2 unanswerable."""
    prompt = _capture_judge_prompt(type_code='literal_detail', keywords='')
    assert 'SUBJECT=(infer the subject from the passage above)' in prompt


# ---------------------------------------------------------------------------
# The judge fills both slots when given them
# ---------------------------------------------------------------------------

def test_keywords_render_into_the_subject_slot():
    prompt = _capture_judge_prompt(
        type_code='vocabulary_context', keywords='Aviation: runway, altitude')
    assert 'SUBJECT=Aviation: runway, altitude' in prompt


def test_type_code_renders_as_the_string_not_an_id():
    """The type-conditional rubric in v5 matches on the literal type_code, so
    a bare integer (what the old measurement harness passed) would match no
    bullet at all."""
    prompt = _capture_judge_prompt(
        type_code='vocabulary_context', keywords='kw')
    assert 'TYPE=vocabulary_context' in prompt


# ---------------------------------------------------------------------------
# End to end — the regression guard
# ---------------------------------------------------------------------------

def test_keywords_reach_the_rendered_prompt_end_to_end():
    """Drive the real `generate_questions` entry point the orchestrator calls
    and assert the topic data arrives inside the judge's prompt.

    This is the test that would have caught the original defect: every
    narrower test still passed while the caller silently dropped the argument.
    """
    seen = {}

    def fake_judge_llm(prompt, **kw):
        seen['prompt'] = prompt
        return DistractorPlausibilityVerdict(
            per_distractor=[5, 5, 5], reasons=['a', 'b', 'c'])

    question = MCQuestion(
        question_text='What does the passage say?',
        choices=['right', 'wrong1', 'wrong2', 'wrong3'],
        answer='right',
        correct_answer_index=0,
    )

    with patch.object(qg_mod, 'call_llm', return_value=question), \
         patch.object(dp_mod, '_load_cfg', return_value=_cfg()), \
         patch.object(dp_mod, 'call_llm', side_effect=fake_judge_llm), \
         patch.object(dp_mod, 'log_judge_verdict', lambda **kw: None), \
         patch('services.exercise_generation.judges.answer_entailment.'
               'judge_answer_entailment',
               return_value=JudgeOutcome(
                   verdict='accept', confidence=1.0, reason='ok')), \
         patch.object(qg_mod.QuestionValidator, 'validate_question',
                      return_value=(True, None)):
        QuestionGenerator().generate_questions(
            prose='Some passage about composting.',
            language_name='Chinese',
            question_type_codes=['vocabulary_context'],
            prompt_templates={'vocabulary_context': 'tpl'},
            language_id=1,
            db=MagicMock(),
            topic_concept='家庭堆肥',
            keywords=['微生物', '土壤'],
        )

    prompt = seen['prompt']
    assert 'SUBJECT=家庭堆肥: 微生物, 土壤' in prompt, (
        'the caller dropped keywords= again — prompt slot {5} is dead:\n'
        + prompt
    )
    assert 'TYPE=vocabulary_context' in prompt


# ---------------------------------------------------------------------------
# The orchestrator's default-off gate
# ---------------------------------------------------------------------------

def test_orchestrator_withholds_the_subject_line_by_default(monkeypatch):
    """Default OFF is a measured decision (the subject line raised ja rejects),
    so it must be pinned. Without this, "no keywords in production" is
    indistinguishable from the TASK-717 bug having quietly returned."""
    monkeypatch.delenv('JUDGE_SUBJECT_KEYWORDS', raising=False)
    assert _subject_kwargs('家庭堆肥', ['微生物']) == {}


@pytest.mark.parametrize('value', ['1', 'true', 'TRUE', 'yes', 'on'])
def test_orchestrator_passes_the_subject_line_when_enabled(monkeypatch, value):
    """The plumbing must still be intact for TASK-718/719 to switch on."""
    monkeypatch.setenv('JUDGE_SUBJECT_KEYWORDS', value)
    assert _subject_kwargs('家庭堆肥', ['微生物']) == {
        'topic_concept': '家庭堆肥', 'keywords': ['微生物']}


@pytest.mark.parametrize('value', ['', '0', 'false', 'off', 'nope'])
def test_only_recognised_truthy_values_enable_it(monkeypatch, value):
    monkeypatch.setenv('JUDGE_SUBJECT_KEYWORDS', value)
    assert _subject_kwargs('家庭堆肥', ['微生物']) == {}
