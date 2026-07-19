"""Unit tests for the Dual Translation Explainer pass (TASK-630, §6c/§7e).

DB-free and OpenRouter-free: the explainer's two boundaries — ``resolve_tier`` and
``call_model_with_usage`` — are monkeypatched in the module's own namespace, exactly
like test_dual_translation_grader_cascade.py mocks the cascade's boundaries. Nothing
here touches Supabase or OpenRouter.
"""

import json

import pytest

from services.dual_translation import explainer, prompts
from services.dual_translation.router import ResolvedRoute


# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------

TAXONOMY_CFG = {
    'subtype_glosses': {
        'particle_wa_ga': {'en': 'topic vs subject particle (は/が)'},
        'tense_aspect': {'en': 'verb tense/aspect'},
    },
}


def _route(slug):
    return ResolvedRoute(
        requested_tier='tier1', used_tier='tier1' if slug else 'tier0',
        slug=slug, fell_open=slug is None,
    )


def _error(learner_form='lives', corrected_form='has lived', subtype='tense_aspect', rule='Use the perfect for a state that began in the past and continues.'):
    """A decoded-error dict in the grader_cascade shape, with its Rule-layer
    explanation already rendered (what the merge hands the explainer)."""
    return {
        'span_reproduction': [0, len(learner_form)],
        'span_reference': [0, len(corrected_form)],
        'category': 'grammatical',
        'subtype': subtype,
        'source': 'intralingual',
        'severity': 'major',
        'learner_form': learner_form,
        'corrected_form': corrected_form,
        'explanation': rule,
        'confidence': 0.9,
        'is_mistake': False,
    }


def _patch_model(monkeypatch, *, slug='tier1-slug', response=None, raises=None):
    monkeypatch.setattr(explainer, 'resolve_tier', lambda db, tier, lid, **k: _route(slug))

    def _call(model_slug, user_prompt, system_prompt=None, temperature=0.0):
        if raises is not None:
            raise raises
        return response, 11, 7, 0.4

    monkeypatch.setattr(explainer, 'call_model_with_usage', _call)


def _run(errors, monkeypatch, **kwargs):
    return explainer.attach_explanations(
        db=object(),
        errors=errors,
        reference='She has lived in Osaka since 2019.',
        reproduction='She lives in Osaka since 2019.',
        l1_code='en',
        l2_language_id=2,
        taxonomy_cfg=TAXONOMY_CFG,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_valid_application_is_concatenated_and_split_into_parts(monkeypatch):
    app_text = 'Here "lives" describes an ongoing state, so "has lived" is needed to show it began in 2019 and continues.'
    _patch_model(monkeypatch, response=json.dumps({
        'explanations': [{'error_index': 0, 'text': app_text}],
    }))

    errors = [_error()]
    out, t_in, t_out, reason = _run(errors, monkeypatch)

    assert reason is None
    assert (t_in, t_out) == (11, 7)
    e = out[0]
    assert e['explanation_parts'] == {
        'rule': 'Use the perfect for a state that began in the past and continues.',
        'application': app_text,
    }
    assert e['explanation'] == (
        'Use the perfect for a state that began in the past and continues.\n' + app_text
    )


def test_error_bearing_only_empty_errors_make_no_call(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError('the explainer must not resolve a slug or call the model with no errors')

    monkeypatch.setattr(explainer, 'resolve_tier', _boom)
    monkeypatch.setattr(explainer, 'call_model_with_usage', _boom)

    out, t_in, t_out, reason = _run([], monkeypatch)
    assert out == []
    assert (t_in, t_out, reason) == (0, 0, None)


def test_every_error_gets_explanation_parts_even_when_unaddressed(monkeypatch):
    # Model only explains error 0; error 1 must still carry Rule-only parts.
    _patch_model(monkeypatch, response=json.dumps({
        'explanations': [{'error_index': 0, 'text': 'The word "lives" should be "has lived" here.'}],
    }))
    errors = [_error(), _error(learner_form='go', corrected_form='went', rule='Past tense of go is went.')]
    out, *_ = _run(errors, monkeypatch)

    assert out[0]['explanation_parts']['application'] is not None
    assert out[1]['explanation_parts'] == {'rule': 'Past tense of go is went.', 'application': None}
    assert out[1]['explanation'] == 'Past tense of go is went.'  # unchanged Rule-only


# ---------------------------------------------------------------------------
# Per-item validation → Rule-only (AC: overlong / no-mention / score / missing index)
# ---------------------------------------------------------------------------

def _single_item_rule_only(monkeypatch, text):
    _patch_model(monkeypatch, response=json.dumps({
        'explanations': [{'error_index': 0, 'text': text}],
    }))
    errors = [_error()]
    out, *_ = _run(errors, monkeypatch)
    return out[0]


def test_overlong_application_falls_back_to_rule_only(monkeypatch):
    long_text = 'The word "lives" ' + ('x' * 300)
    e = _single_item_rule_only(monkeypatch, long_text)
    assert e['explanation_parts']['application'] is None
    assert e['explanation'] == e['explanation_parts']['rule']


def test_application_without_form_mention_falls_back_to_rule_only(monkeypatch):
    e = _single_item_rule_only(monkeypatch, 'This tense choice matters for the meaning of the whole sentence.')
    assert e['explanation_parts']['application'] is None


def test_application_with_score_pattern_falls_back_to_rule_only(monkeypatch):
    e = _single_item_rule_only(monkeypatch, 'Because of "lives" your accuracy is 3/4 here.')
    assert e['explanation_parts']['application'] is None


def test_multiparagraph_application_falls_back_to_rule_only(monkeypatch):
    e = _single_item_rule_only(monkeypatch, 'The word "lives" is wrong.\nUse "has lived" instead.')
    assert e['explanation_parts']['application'] is None


def test_missing_index_and_out_of_range_are_ignored(monkeypatch):
    _patch_model(monkeypatch, response=json.dumps({
        'explanations': [
            {'text': 'no index, mentions "lives"'},            # missing error_index
            {'error_index': 5, 'text': 'out of range "lives"'},  # out of range
            {'error_index': True, 'text': 'boolean index "lives"'},  # bool not an index
        ],
    }))
    errors = [_error()]
    out, *_ = _run(errors, monkeypatch)
    assert out[0]['explanation_parts']['application'] is None


def test_duplicate_index_first_valid_wins(monkeypatch):
    _patch_model(monkeypatch, response=json.dumps({
        'explanations': [
            {'error_index': 0, 'text': 'First: "lives" becomes "has lived".'},
            {'error_index': 0, 'text': 'Second: "lives" is also wrong.'},
        ],
    }))
    errors = [_error()]
    out, *_ = _run(errors, monkeypatch)
    assert out[0]['explanation_parts']['application'] == 'First: "lives" becomes "has lived".'


def test_corrected_form_mention_alone_is_enough(monkeypatch):
    # Text mentions only the corrected form, not the learner form.
    e = _single_item_rule_only(monkeypatch, 'You need "has lived" to express the continuing state.')
    assert e['explanation_parts']['application'] == 'You need "has lived" to express the continuing state.'


# ---------------------------------------------------------------------------
# Fail-silent (AC: never blocks; failure logged, Rule-only, no exception)
# ---------------------------------------------------------------------------

def test_no_slug_keeps_rule_only(monkeypatch):
    _patch_model(monkeypatch, slug=None)
    errors = [_error()]
    out, t_in, t_out, reason = _run(errors, monkeypatch)
    assert reason == 'no slug'
    assert (t_in, t_out) == (0, 0)
    assert out[0]['explanation_parts'] == {'rule': out[0]['explanation'], 'application': None}


def test_call_raising_keeps_rule_only(monkeypatch):
    _patch_model(monkeypatch, raises=RuntimeError('network down'))
    errors = [_error()]
    out, t_in, t_out, reason = _run(errors, monkeypatch)
    assert reason == 'call failed'
    assert out[0]['explanation_parts']['application'] is None
    assert out[0]['explanation'] == out[0]['explanation_parts']['rule']


def test_malformed_json_keeps_rule_only_but_counts_tokens(monkeypatch):
    _patch_model(monkeypatch, response='not json at all')
    errors = [_error()]
    out, t_in, t_out, reason = _run(errors, monkeypatch)
    assert reason == 'malformed JSON'
    assert (t_in, t_out) == (11, 7)  # tokens still accounted even on a bad body
    assert out[0]['explanation_parts']['application'] is None


def test_wrong_shape_keeps_rule_only(monkeypatch):
    _patch_model(monkeypatch, response=json.dumps({'explanations': 'not a list'}))
    errors = [_error()]
    out, _t_in, _t_out, reason = _run(errors, monkeypatch)
    assert reason == 'malformed shape'
    assert out[0]['explanation_parts']['application'] is None


# ---------------------------------------------------------------------------
# Prompt builders (§7e) + response validator (§6c)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('l1_code', ['en', 'zh', 'ja'])
def test_explainer_system_prompt_authored_per_l1(l1_code):
    sys = prompts.build_explainer_system_prompt(l1_code)
    assert isinstance(sys, str) and sys
    # The output-shape contract token appears in every L1's header.
    assert 'explanations' in sys


def test_explainer_system_prompt_unknown_l1_raises():
    with pytest.raises(ValueError):
        prompts.build_explainer_system_prompt('fr')


def test_explainer_user_prompt_carries_reference_learner_and_numbered_errors():
    numbered = [{'i': 0, 'learner_form': 'lives', 'corrected_form': 'has lived',
                 'type': 'verb tense/aspect', 'rule': 'Use the perfect …'}]
    usr = prompts.build_explainer_user_prompt('en', 'REF TEXT', 'LEARNER TEXT', numbered)
    assert 'REF TEXT' in usr and 'LEARNER TEXT' in usr
    assert '"learner_form": "lives"' in usr
    assert '"i": 0' in usr


@pytest.mark.parametrize('payload,expected', [
    ({'explanations': []}, True),
    ({'explanations': [{'error_index': 0, 'text': 'x'}]}, True),
    ({'explanations': 'nope'}, False),
    ({}, False),
    ([], False),
    ('nope', False),
])
def test_validate_explainer_response(payload, expected):
    assert prompts.validate_explainer_response(payload) is expected


# ---------------------------------------------------------------------------
# Subtype gloss resolution (L1)
# ---------------------------------------------------------------------------

def test_numbered_error_uses_l1_subtype_gloss(monkeypatch):
    captured = {}

    def _call(model_slug, user_prompt, system_prompt=None, temperature=0.0):
        captured['user'] = user_prompt
        return json.dumps({'explanations': []}), 1, 1, 0.1

    monkeypatch.setattr(explainer, 'resolve_tier', lambda db, tier, lid, **k: _route('tier1-slug'))
    monkeypatch.setattr(explainer, 'call_model_with_usage', _call)

    _run([_error(subtype='particle_wa_ga')], monkeypatch)
    assert 'topic vs subject particle' in captured['user']


def test_numbered_error_falls_back_to_slug_when_no_gloss(monkeypatch):
    captured = {}

    def _call(model_slug, user_prompt, system_prompt=None, temperature=0.0):
        captured['user'] = user_prompt
        return json.dumps({'explanations': []}), 1, 1, 0.1

    monkeypatch.setattr(explainer, 'resolve_tier', lambda db, tier, lid, **k: _route('tier1-slug'))
    monkeypatch.setattr(explainer, 'call_model_with_usage', _call)

    _run([_error(subtype='no_such_subtype')], monkeypatch)
    assert 'no_such_subtype' in captured['user']
