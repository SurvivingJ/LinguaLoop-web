"""Unit tests for the dual-translation grading cascade orchestrator (TASK-606).

DB-free and OpenRouter-free: every test mocks the cascade's boundaries —
``get_active_rubric``, ``get_active_taxonomy``, ``resolve_tier``, and
``call_model_with_usage`` — exactly like test_dual_translation_router.py mocks
``get_template_config``/``fetch_model_list``. Nothing here touches Supabase or
OpenRouter. ``DimensionService.get_language_code`` is also mocked since it
otherwise needs a populated class-level cache this test process never loads.
"""

import json

import pytest

from services.dimension_service import DimensionService
from services.dual_translation import grader_cascade, tier0
from services.dual_translation.router import ResolvedRoute


# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------

LANG_CODES = {1: 'zh', 2: 'en', 3: 'ja'}

RUBRIC_CFG = {
    'weights': {
        'default': {
            'accuracy': 0.3, 'understandability': 0.3,
            'fidelity': 0.15, 'range': 0.15, 'naturalness': 0.1,
        },
    },
}

TAXONOMY_CFG = {
    'pairs': {'en': {'subtypes': ['article_omission', 'preposition']}},
    'templates': {'article_omission': {'zh': '你写的是{learner_form}，应改为{corrected_form}。'}},
}


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.setattr(DimensionService, 'get_language_code', classmethod(lambda cls, lid: LANG_CODES.get(lid)))
    tier0.clear_cache()
    yield
    tier0.clear_cache()


def _route(tier, slug):
    return ResolvedRoute(requested_tier=tier, used_tier=tier if slug else 'tier0', slug=slug, fell_open=slug is None)


def _ten_word_gold():
    return ' '.join(f'word{i}' for i in range(10))


def _ten_word_repro_one_wrong():
    tokens = [f'word{i}' for i in range(10)]
    tokens[9] = 'totallydifferent'
    return ' '.join(tokens)


TIER1_OK = {
    'confidence': 0.9,
    'scores': {'accuracy': 3, 'range': 3},
    'errors': [{
        'span_repro': [0, 5], 'span_ref': [0, 7],
        'category': 1, 'source': 0, 'severity': 1, 'subtype': 0,
        'learner_form': 'foo', 'corrected_form': 'foobar',
        'confidence': 0.8, 'is_mistake': False,
    }],
}

TIER2_OK = {
    'confidence': 0.85,
    'scores': {'understandability': 4, 'fidelity': 3, 'naturalness': 2},
    'errors': [],
}


def _make_call_model(responses: dict, captured: list = None):
    """responses: {model_slug: parsed_dict_or_raw_string}."""
    def _fake(model, prompt, *, system_prompt=None, temperature=0.0, **kwargs):
        if captured is not None:
            captured.append({'model': model, 'prompt': prompt, 'system_prompt': system_prompt})
        if model not in responses:
            raise AssertionError(f'unexpected model called: {model!r}')
        payload = responses[model]
        content = payload if isinstance(payload, str) else json.dumps(payload)
        return content, 10, 5, 0.05
    return _fake


# ---------------------------------------------------------------------------
# Tier 0 short-circuit
# ---------------------------------------------------------------------------

def test_grade_submission_tier0_resolved_short_circuits_no_model_call(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError('should not be called when Tier 0 resolves')

    monkeypatch.setattr(grader_cascade, 'get_active_rubric', _boom)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', _boom)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', _boom)
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _boom)

    gold = 'The quick brown fox jumps over the lazy dog'
    result = grader_cascade.grade_submission(
        db=None, passage_id=1, gold_l2=gold, reproduction=gold,
        l2_language_id=2, l1_language_id=1, age_tier=3,
    )

    assert result['scores'] == {dim: 4 for dim in tier0.RUBRIC_DIMENSIONS}
    assert result['overall_band'] == 4
    assert result['errors'] == []
    assert result['grader_trace']['tier'] == 'tier0'
    assert result['grader_trace']['deterministic_prefilter'] is True


# ---------------------------------------------------------------------------
# Happy path: tier1 + tier2, no recheck
# ---------------------------------------------------------------------------

def test_grade_submission_merges_tier1_and_tier2_no_recheck(monkeypatch):
    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', lambda db, tier, lid, **k: _route(tier, f'{tier}-slug'))
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _make_call_model({
        'tier1-slug': TIER1_OK, 'tier2-slug': TIER2_OK,
    }))

    result = grader_cascade.grade_submission(
        db=None, passage_id=2, gold_l2=_ten_word_gold(), reproduction=_ten_word_repro_one_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3,
    )

    assert result['scores'] == {
        'accuracy': 3, 'range': 3, 'understandability': 4, 'fidelity': 3, 'naturalness': 2,
    }
    assert result['overall_band'] == 3  # weighted mean per RUBRIC_CFG = 3.2 -> round -> 3

    assert len(result['errors']) == 1
    err = result['errors'][0]
    assert err['span_reproduction'] == [0, 5]
    assert err['span_reference'] == [0, 7]
    assert err['category'] == 'lexical'
    assert err['source'] == 'interlingual'
    assert err['severity'] == 'local'
    assert err['subtype'] == 'article_omission'
    assert err['learner_form'] == 'foo'
    assert err['corrected_form'] == 'foobar'
    assert err['explanation'] == '你写的是foo，应改为foobar。'
    assert err['is_mistake'] is False

    trace = result['grader_trace']
    assert trace['tier'] == 'tier2'
    assert trace['deterministic_prefilter'] is False
    assert trace['cache_hit'] is False
    assert trace['tokens'] == {'in': 20, 'out': 10}
    assert len(trace['slugs']) == 2
    assert trace['fell_open'] is False
    assert trace['reason'] is None


# ---------------------------------------------------------------------------
# Fail-open: malformed tier1 JSON
# ---------------------------------------------------------------------------

def test_grade_submission_fails_open_on_malformed_tier1_json(monkeypatch):
    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', lambda db, tier, lid, **k: _route(tier, f'{tier}-slug'))
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _make_call_model({
        'tier1-slug': 'this is not json at all',
        'tier2-slug': TIER2_OK,
    }))

    result = grader_cascade.grade_submission(
        db=None, passage_id=3, gold_l2=_ten_word_gold(), reproduction=_ten_word_repro_one_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3,
    )

    assert result['scores']['accuracy'] == 4  # fail-open default
    assert result['scores']['range'] == 4
    assert result['scores']['understandability'] == 4  # real tier2 data
    assert result['errors'] == []  # tier1's would-be error was never decoded
    assert result['grader_trace']['fell_open'] is True
    assert 'tier1 malformed JSON' in result['grader_trace']['reason']


# ---------------------------------------------------------------------------
# Fail-open: no usable slug at all (router exhausted)
# ---------------------------------------------------------------------------

def test_grade_submission_fails_open_when_no_slug_available(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError('call_model_with_usage must not be called when no slug is usable')

    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', lambda db, tier, lid, **k: _route(tier, None))
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _boom)

    result = grader_cascade.grade_submission(
        db=None, passage_id=4, gold_l2=_ten_word_gold(), reproduction=_ten_word_repro_one_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3,
    )

    assert result['scores'] == {dim: 4 for dim in tier0.RUBRIC_DIMENSIONS}
    assert result['overall_band'] == 4
    assert result['errors'] == []
    trace = result['grader_trace']
    assert trace['tier'] == 'tier0'
    assert trace['tokens'] == {'in': 0, 'out': 0}
    assert trace['fell_open'] is True
    assert 'tier1 unavailable' in trace['reason']
    assert 'tier2 unavailable' in trace['reason']


# ---------------------------------------------------------------------------
# Escalation: low Tier 1 confidence -> Tier 2 also rechecks accuracy/range
# ---------------------------------------------------------------------------

def test_grade_submission_low_tier1_confidence_triggers_recheck(monkeypatch):
    tier1_low_confidence = {**TIER1_OK, 'confidence': 0.2, 'errors': []}
    tier2_with_recheck = {
        'confidence': 0.85,
        'scores': {'understandability': 4, 'fidelity': 3, 'naturalness': 2, 'accuracy': 2, 'range': 2},
        'errors': [],
    }
    captured = []

    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', lambda db, tier, lid, **k: _route(tier, f'{tier}-slug'))
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _make_call_model({
        'tier1-slug': tier1_low_confidence, 'tier2-slug': tier2_with_recheck,
    }, captured=captured))

    result = grader_cascade.grade_submission(
        db=None, passage_id=5, gold_l2=_ten_word_gold(), reproduction=_ten_word_repro_one_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3,
    )

    # Tier 2's recheck values win over Tier 1's original 3/3.
    assert result['scores']['accuracy'] == 2
    assert result['scores']['range'] == 2

    tier2_call = next(c for c in captured if c['model'] == 'tier2-slug')
    assert 'accuracy' in tier2_call['system_prompt'].lower() or 'grammatical' in tier2_call['system_prompt'].lower()


# ---------------------------------------------------------------------------
# Budget-gate hook: max_tier caps the cascade
# ---------------------------------------------------------------------------

def test_grade_submission_max_tier_skips_tier2(monkeypatch):
    def _boom_if_tier2(db, tier, lid, **k):
        if tier == 'tier2':
            raise AssertionError('tier2 must not be resolved when max_tier=tier1')
        return _route(tier, f'{tier}-slug')

    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', _boom_if_tier2)
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _make_call_model({'tier1-slug': TIER1_OK}))

    result = grader_cascade.grade_submission(
        db=None, passage_id=6, gold_l2=_ten_word_gold(), reproduction=_ten_word_repro_one_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3, max_tier='tier1',
    )

    assert result['scores']['accuracy'] == 3  # real tier1 data
    assert result['scores']['understandability'] == 4  # fail-open default (tier2 never ran)
    assert result['grader_trace']['tier'] == 'tier1'


# ---------------------------------------------------------------------------
# render_explanation
# ---------------------------------------------------------------------------

def test_render_explanation_uses_template_when_present():
    text, used_fallback = grader_cascade.render_explanation(
        TAXONOMY_CFG, 'article_omission', 'zh', learner_form='foo', corrected_form='foobar',
    )
    assert used_fallback is False
    assert 'foo' in text and 'foobar' in text


def test_render_explanation_falls_back_when_template_missing():
    text, used_fallback = grader_cascade.render_explanation(
        TAXONOMY_CFG, 'preposition', 'zh', learner_form='foo', corrected_form='foobar',
    )
    assert used_fallback is True
    assert text  # never blank
    assert 'foobar' in text


# ---------------------------------------------------------------------------
# compute_overall_band
# ---------------------------------------------------------------------------

def test_compute_overall_band_weighted_mean():
    scores = {'accuracy': 3, 'understandability': 4, 'fidelity': 3, 'range': 3, 'naturalness': 2}
    band = grader_cascade.compute_overall_band(scores, RUBRIC_CFG, 'en')
    assert band == 3


def test_compute_overall_band_falls_back_to_equal_weights_when_unconfigured():
    scores = {dim: 4 for dim in tier0.RUBRIC_DIMENSIONS}
    band = grader_cascade.compute_overall_band(scores, {}, 'en')
    assert band == 4
