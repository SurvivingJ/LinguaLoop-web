"""Unit tests for the dual-translation grading cascade orchestrator (TASK-606).

DB-free and OpenRouter-free: every test mocks the cascade's boundaries —
``get_active_rubric``, ``get_active_taxonomy``, ``resolve_tier``, and
``call_model_with_usage`` — exactly like test_dual_translation_router.py mocks
``get_template_config``/``fetch_model_list``. Nothing here touches Supabase or
OpenRouter. ``DimensionService.get_language_code`` is also mocked since it
otherwise needs a populated class-level cache this test process never loads.
"""

import json
import threading
import time

import pytest

from services.dimension_service import DimensionService
from services.dual_translation import grader_cascade, prompts, tier0
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


def _ten_word_repro_five_wrong():
    # 5/10 tokens replaced -> tier-0 mismatch_ratio 0.5 > LARGE_DIFF_RATIO (0.3),
    # so the Tier-2 re-check is FORCED (independent of Tier-1 confidence) — the
    # TASK-643 concurrent branch.
    tokens = [f'word{i}' for i in range(10)]
    for i in range(5, 10):
        tokens[i] = f'diff{i}'
    return ' '.join(tokens)


# The error points at the ACTUAL diff between _ten_word_gold ("word0 .. word9")
# and _ten_word_repro_one_wrong ("word0 .. word8 totallydifferent"): word9 was
# replaced. 'totallydifferent' begins at char 54 in the reproduction; 'word9' is
# [54,59] in the gold. TASK-624 span discipline validates these forms against the
# real texts, so they must actually sit at their spans.
TIER1_OK = {
    'confidence': 0.9,
    'scores': {'accuracy': 3, 'range': 3},
    'errors': [{
        'span_repro': [54, 70], 'span_ref': [54, 59],
        'category': 1, 'source': 0, 'severity': 1, 'subtype': 0,
        'learner_form': 'totallydifferent', 'corrected_form': 'word9',
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
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False,
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
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False,
    )

    assert result['scores'] == {
        'accuracy': 3, 'range': 3, 'understandability': 4, 'fidelity': 3, 'naturalness': 2,
    }
    assert result['overall_band'] == 3  # weighted mean per RUBRIC_CFG = 3.2 -> round -> 3

    assert len(result['errors']) == 1
    err = result['errors'][0]
    assert err['span_reproduction'] == [54, 70]
    assert err['span_reference'] == [54, 59]
    assert err['category'] == 'lexical'
    assert err['source'] == 'interlingual'
    # TASK-625: severity index 1 now decodes to the MQM triad's 'major'
    # (SEVERITY_ENUM = minor/major/critical), not the old 'local'.
    assert err['severity'] == 'major'
    assert err['subtype'] == 'article_omission'
    assert err['learner_form'] == 'totallydifferent'
    assert err['corrected_form'] == 'word9'
    assert err['explanation'] == '你写的是totallydifferent，应改为word9。'
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
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False,
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
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False,
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
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False,
    )

    # Tier 2's recheck values win over Tier 1's original 3/3.
    assert result['scores']['accuracy'] == 2
    assert result['scores']['range'] == 2

    tier2_call = next(c for c in captured if c['model'] == 'tier2-slug')
    assert 'accuracy' in tier2_call['system_prompt'].lower() or 'grammatical' in tier2_call['system_prompt'].lower()


def test_grade_submission_missing_tier1_confidence_triggers_recheck(monkeypatch):
    """TASK-623: a Tier-1 response that OMITS `confidence` must escalate the
    Tier-2 accuracy/range re-check (default 0.0 < CONFIDENCE_ESCALATION_
    THRESHOLD), not sail through as fully-confident (the old default=1.0 that
    silently skipped the re-check)."""
    tier1_no_confidence = {  # note: no 'confidence' key
        'scores': {'accuracy': 3, 'range': 3},
        'errors': [],
    }
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
        'tier1-slug': tier1_no_confidence, 'tier2-slug': tier2_with_recheck,
    }, captured=captured))

    result = grader_cascade.grade_submission(
        db=None, passage_id=7, gold_l2=_ten_word_gold(), reproduction=_ten_word_repro_one_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False,
    )

    # Tier 2's recheck values win — proving the re-check fired despite no confidence.
    assert result['scores']['accuracy'] == 2
    assert result['scores']['range'] == 2

    tier2_call = next(c for c in captured if c['model'] == 'tier2-slug')
    assert 'accuracy' in tier2_call['system_prompt'].lower() or 'grammatical' in tier2_call['system_prompt'].lower()


# ---------------------------------------------------------------------------
# TASK-643: forced (large-diff) re-check runs Tier 1 + Tier 2 concurrently
# ---------------------------------------------------------------------------

# High Tier-1 confidence (0.9) on purpose: with the small-diff confidence gate
# NOT tripped, the ONLY thing that can trigger the Tier-2 re-check is the large
# diff — so these prove the forced path specifically.
_FORCED_TIER1 = {'confidence': 0.9, 'scores': {'accuracy': 3, 'range': 3}, 'errors': []}
_FORCED_TIER2_RECHECK = {
    'confidence': 0.85,
    'scores': {'understandability': 4, 'fidelity': 3, 'naturalness': 2, 'accuracy': 2, 'range': 2},
    'errors': [],
}


def test_forced_recheck_runs_tier1_and_tier2_concurrently(monkeypatch):
    """The two multi-second model calls are issued concurrently in the large-diff
    branch. A 2-party barrier proves the overlap: both tiers must arrive together
    to release it. If the calls ran sequentially, the first would wait alone, time
    out into a fail-open, and the Tier-2 re-check bands would never land."""
    barrier = threading.Barrier(2, timeout=5)
    captured = []
    clock = threading.Lock()
    responses = {'tier1-slug': _FORCED_TIER1, 'tier2-slug': _FORCED_TIER2_RECHECK}

    def _fake(model, prompt, *, system_prompt=None, temperature=0.0, **kwargs):
        barrier.wait()  # deadlocks-then-times-out unless both tiers are in flight
        with clock:
            captured.append({'model': model, 'system_prompt': system_prompt, 'prompt': prompt})
        return json.dumps(responses[model]), 10, 5, 0.05

    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', lambda db, tier, lid, **k: _route(tier, f'{tier}-slug'))
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _fake)

    result = grader_cascade.grade_submission(
        db=None, passage_id=643, gold_l2=_ten_word_gold(), reproduction=_ten_word_repro_five_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False,
    )

    # Merged identically to the sequential path: Tier 2's re-check bands override
    # Tier 1's 3/3; Tier-2-exclusive dims land; tokens sum BOTH calls.
    assert result['scores'] == {
        'accuracy': 2, 'range': 2, 'understandability': 4, 'fidelity': 3, 'naturalness': 2,
    }
    assert {c['model'] for c in captured} == {'tier1-slug', 'tier2-slug'}
    assert result['grader_trace']['tokens'] == {'in': 20, 'out': 10}
    assert result['grader_trace']['tier'] == 'tier2'
    assert result['grader_trace']['fell_open'] is False
    assert len(result['grader_trace']['slugs']) == 2
    # The concurrently-issued Tier-2 call still carried the accuracy/range re-check
    # (extra_dims), exactly as the sequential forced path would have.
    tier2_call = next(c for c in captured if c['model'] == 'tier2-slug')
    assert 'accuracy' in tier2_call['system_prompt'].lower() or 'grammatical' in tier2_call['system_prompt'].lower()


def test_confidence_gated_recheck_stays_sequential(monkeypatch):
    """The small-diff / low-confidence re-check must NOT parallelize — Tier 2's
    extra_dims depend on tier1_confidence, which doesn't exist until Tier 1
    returns. A max-in-flight tracker proves the two calls never overlap."""
    lock = threading.Lock()
    state = {'inflight': 0, 'max': 0}
    tier1_low = {'confidence': 0.2, 'scores': {'accuracy': 3, 'range': 3}, 'errors': []}
    responses = {'tier1-slug': tier1_low, 'tier2-slug': _FORCED_TIER2_RECHECK}

    def _fake(model, prompt, *, system_prompt=None, temperature=0.0, **kwargs):
        with lock:
            state['inflight'] += 1
            state['max'] = max(state['max'], state['inflight'])
        time.sleep(0.05)  # long enough that any real overlap would be observed
        with lock:
            state['inflight'] -= 1
        return json.dumps(responses[model]), 10, 5, 0.05

    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', lambda db, tier, lid, **k: _route(tier, f'{tier}-slug'))
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _fake)

    # Small diff (1/10 < LARGE_DIFF_RATIO): the re-check is confidence-gated, not forced.
    result = grader_cascade.grade_submission(
        db=None, passage_id=644, gold_l2=_ten_word_gold(), reproduction=_ten_word_repro_one_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False,
    )

    assert state['max'] == 1  # the two model calls never ran at the same time
    # The re-check still fired (low confidence): Tier 2's accuracy/range override.
    assert result['scores']['accuracy'] == 2
    assert result['scores']['range'] == 2


# ---------------------------------------------------------------------------
# TASK-635: incomplete Tier-1 scores must fall open, not sail through
# ---------------------------------------------------------------------------

# The leniency hole this task closes: well-formed JSON, high self-reported
# confidence, but no scores at all. It used to pass validation, skip the Tier-2
# re-check, and default accuracy/range to a perfect band with fell_open=False.
TIER1_EMPTY_SCORES = {'confidence': 0.9, 'scores': {}, 'errors': []}
# Same, but missing exactly one asked-for dimension ('range').
TIER1_MISSING_ONE_DIM = {'confidence': 0.9, 'scores': {'accuracy': 3}, 'errors': []}

TIER2_RECHECK = {
    'confidence': 0.85,
    'scores': {'understandability': 4, 'fidelity': 3, 'naturalness': 2, 'accuracy': 2, 'range': 2},
    'errors': [],
}


def _grade_with_tier1(monkeypatch, tier1_payload, passage_id, **kwargs):
    captured = []
    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', lambda db, tier, lid, **k: _route(tier, f'{tier}-slug'))
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _make_call_model({
        'tier1-slug': tier1_payload, 'tier2-slug': TIER2_RECHECK,
    }, captured=captured))
    result = grader_cascade.grade_submission(
        db=None, passage_id=passage_id, gold_l2=_ten_word_gold(),
        reproduction=_ten_word_repro_one_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False, **kwargs,
    )
    return result, captured


def test_grade_submission_incomplete_tier1_scores_falls_open_and_forces_recheck(monkeypatch):
    """scores={} + confidence=0.9 must not produce band-4 dimensions or skip the
    re-check: the response is discarded, the 0.0 confidence default escalates
    Tier 2's accuracy/range re-check, and the trace records why."""
    result, captured = _grade_with_tier1(monkeypatch, TIER1_EMPTY_SCORES, passage_id=8)

    # Tier 2's re-check supplied the real bands — NOT the fail-open 4.
    assert result['scores']['accuracy'] == 2
    assert result['scores']['range'] == 2

    trace = result['grader_trace']
    assert trace['fell_open'] is True
    assert 'tier1 incomplete scores' in trace['reason']
    assert 'accuracy' in trace['reason'] and 'range' in trace['reason']

    # The re-check genuinely fired: Tier 2's prompt was asked for accuracy too.
    tier2_call = next(c for c in captured if c['model'] == 'tier2-slug')
    assert 'accuracy' in tier2_call['system_prompt'].lower()


def test_grade_submission_tier1_missing_one_dimension_is_incomplete(monkeypatch):
    """A response covering accuracy but omitting range is incomplete too — the
    whole response is discarded rather than letting range default to MAX_BAND."""
    result, _captured = _grade_with_tier1(monkeypatch, TIER1_MISSING_ONE_DIM, passage_id=9)

    assert result['scores']['range'] == 2      # from the tier2 re-check, not 4
    assert result['scores']['accuracy'] == 2   # tier1's 3 went with the discarded response

    trace = result['grader_trace']
    assert trace['fell_open'] is True
    assert 'tier1 incomplete scores: range' in trace['reason']


def test_grade_submission_incomplete_tier1_scores_still_traced_when_tier2_is_capped(monkeypatch):
    """With no Tier 2 to re-check, the dimensions do fall open to MAX_BAND — but
    never silently: fell_open and the reason make the inflated grade auditable,
    which is what the old code lacked."""
    result, _captured = _grade_with_tier1(
        monkeypatch, TIER1_EMPTY_SCORES, passage_id=10, max_tier='tier1',
    )

    assert result['scores']['accuracy'] == 4   # honest fail-open...
    trace = result['grader_trace']
    assert trace['fell_open'] is True          # ...but declared, not silent
    assert 'tier1 incomplete scores' in trace['reason']


def test_prompts_band_scale_matches_tier0():
    # prompts.MAX_BAND is a deliberate mirror of tier0.MAX_BAND (prompts stays a
    # dependency-free string builder); this is the drift guard for that copy.
    assert prompts.MAX_BAND == tier0.MAX_BAND
    assert prompts.MIN_BAND == 1


def test_asked_dimensions_are_all_rubric_dimensions():
    # Validation requires a band for every asked dimension, and each of those must
    # be a real rubric dimension — else a dimension outside the rubric could gate
    # a response, or a rubric dimension could go unscored.
    for tier in ('tier1', 'tier2'):
        for dim in prompts.asked_dimensions(tier):
            assert dim in tier0.RUBRIC_DIMENSIONS
    # Together the two tiers cover the rubric exactly.
    covered = set(prompts.asked_dimensions('tier1')) | set(prompts.asked_dimensions('tier2'))
    assert covered == set(tier0.RUBRIC_DIMENSIONS)


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
        l2_language_id=2, l1_language_id=1, age_tier=3, max_tier='tier1', framework_v2=False,
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


def test_render_explanation_addition_with_empty_correction_omits_correction():
    """TASK-638: addition errors have a zero-width reference span, so the generic
    fallback must not quote an empty corrected_form."""
    text, used_fallback = grader_cascade.render_explanation(
        TAXONOMY_CFG, 'preposition', 'zh', learner_form='foo', corrected_form='',
    )
    assert used_fallback is True
    assert 'corrected:' not in text
    assert 'foo' in text


def test_render_explanation_falls_back_when_template_quotes_absent_correction():
    """A subtype template referencing {corrected_form} must not render an empty
    quotation when the correction is legitimately absent."""
    text, used_fallback = grader_cascade.render_explanation(
        TAXONOMY_CFG, 'article_omission', 'zh', learner_form='foo', corrected_form='',
    )
    assert used_fallback is True
    assert 'foo' in text


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


# ---------------------------------------------------------------------------
# TASK-624: tier-0 diff -> candidate regions
# ---------------------------------------------------------------------------

def test_diff_regions_filters_equal_and_maps_fields():
    diff = [
        {'op': 'equal', 'correct': 'word0', 'user': 'word0', 'is_correct': True},
        {'op': 'replace', 'correct': 'word9', 'user': 'totallydifferent', 'is_correct': False},
        {'op': 'delete', 'correct': 'gone', 'user': None, 'is_correct': False},
        {'op': 'insert', 'correct': None, 'user': 'extra', 'is_correct': False},
    ]
    regions = grader_cascade._diff_regions(diff)
    assert regions == [
        {'op': 'replace', 'ref': 'word9', 'repro': 'totallydifferent'},
        {'op': 'delete', 'ref': 'gone', 'repro': ''},
        {'op': 'insert', 'ref': '', 'repro': 'extra'},
    ]


def test_diff_regions_caps_at_20():
    diff = [{'op': 'replace', 'correct': f'c{i}', 'user': f'u{i}', 'is_correct': False} for i in range(50)]
    regions = grader_cascade._diff_regions(diff)
    assert len(regions) == grader_cascade.DIFF_REGION_CAP == 20


def test_grade_submission_passes_candidate_regions_to_the_tier_calls(monkeypatch):
    captured = []
    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', lambda db, tier, lid, **k: _route(tier, f'{tier}-slug'))
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _make_call_model({
        'tier1-slug': TIER1_OK, 'tier2-slug': TIER2_OK,
    }, captured=captured))

    grader_cascade.grade_submission(
        db=None, passage_id=42, gold_l2=_ten_word_gold(), reproduction=_ten_word_repro_one_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=False,
    )

    # The single replaced token surfaces as a candidate region in BOTH tier user prompts.
    for c in captured:
        assert 'CANDIDATE REGIONS' in c['prompt']
        assert 'totallydifferent' in c['prompt']


# ---------------------------------------------------------------------------
# TASK-624: _decode_error substring repair (before dropping)
# ---------------------------------------------------------------------------

def _base_raw(**overrides):
    raw = {
        'span_repro': [0, 1], 'span_ref': [0, 1],
        'category': 0, 'source': 0, 'severity': 0, 'subtype': 0,
        'learner_form': 'x', 'corrected_form': 'y',
        'confidence': 0.8, 'is_mistake': False,
    }
    raw.update(overrides)
    return raw


def test_decode_error_repairs_off_by_one_span_by_substring_search():
    reproduction = 'the quick brown fox'   # 'quick' is [4,9]
    reference = 'the rapid brown fox'       # 'rapid' is [4,9]
    raw = _base_raw(
        span_repro=[3, 8],           # off by one — text[3:8] == ' quic', not 'quick'
        learner_form='quick',
        span_ref=[4, 9], corrected_form='rapid',
    )
    decoded = grader_cascade._decode_error(raw, ['article_omission', 'preposition'], TAXONOMY_CFG, 'zh', reproduction, reference)
    assert decoded is not None
    assert decoded['span_reproduction'] == [4, 9]   # repaired
    assert decoded['learner_form'] == 'quick'


def test_decode_error_keeps_omission_with_empty_learner_form():
    # The baseline dropped a real omission (empty learner_form at a zero-width
    # span). It must now be kept: the corrected_form carries the omitted text.
    reproduction = 'abcdefghij'              # len 10; [7,7] is an in-bounds omission point
    reference = 'XYabcdefghij'               # 'XY' is [0,2]
    raw = _base_raw(
        span_repro=[7, 7], learner_form='',
        span_ref=[0, 2], corrected_form='XY',
    )
    decoded = grader_cascade._decode_error(raw, ['article_omission', 'preposition'], TAXONOMY_CFG, 'zh', reproduction, reference)
    assert decoded is not None
    assert decoded['span_reproduction'] == [7, 7]
    assert decoded['learner_form'] == ''
    assert decoded['corrected_form'] == 'XY'


def test_decode_error_drops_form_that_is_nowhere_in_text():
    reproduction = 'hello world'
    reference = 'hello there'
    raw = _base_raw(
        span_repro=[0, 3], learner_form='zzz',   # 'zzz' not in reproduction at all
        span_ref=[0, 3], corrected_form='hel',
    )
    decoded = grader_cascade._decode_error(raw, ['article_omission', 'preposition'], TAXONOMY_CFG, 'zh', reproduction, reference)
    assert decoded is None


# ---------------------------------------------------------------------------
# TASK-625: severity triad decode (range check widens via len(SEVERITY_ENUM))
# ---------------------------------------------------------------------------

def test_decode_error_severity_index_2_is_critical():
    # The third triad level must decode — TASK-624's 2-level enum had no index 2.
    reproduction = 'hello world'
    reference = 'goodbye world'
    raw = _base_raw(
        severity=2,
        span_repro=[0, 5], learner_form='hello',
        span_ref=[0, 7], corrected_form='goodbye',
    )
    decoded = grader_cascade._decode_error(raw, ['article_omission', 'preposition'], TAXONOMY_CFG, 'zh', reproduction, reference)
    assert decoded is not None
    assert decoded['severity'] == 'critical'


def test_decode_error_drops_out_of_range_severity_index():
    # Index 3 is past the triad — the enum-length range check must reject it.
    reproduction = 'hello world'
    reference = 'goodbye world'
    raw = _base_raw(
        severity=3,
        span_repro=[0, 5], learner_form='hello',
        span_ref=[0, 7], corrected_form='goodbye',
    )
    decoded = grader_cascade._decode_error(raw, ['article_omission', 'preposition'], TAXONOMY_CFG, 'zh', reproduction, reference)
    assert decoded is None


# ---------------------------------------------------------------------------
# TASK-634: nearest-occurrence snapping, normalization fallback, raw-text regions
# ---------------------------------------------------------------------------

def test_decode_error_repeated_token_off_by_one_snaps_to_nearest_occurrence():
    # 'the' occurs twice; the error is on the SECOND one ([12,15]). An off-by-one
    # span must relocate to the occurrence NEAREST the model's span, not the first
    # (TASK-634 (1) — text.find would teleport the highlight to the wrong 'the').
    reproduction = 'the cat saw the dog'   # 2nd 'the' is [12,15]
    reference = 'the cat saw the dog'
    raw = _base_raw(
        span_repro=[13, 16], learner_form='the',   # off by one, near the 2nd 'the'
        span_ref=[12, 15], corrected_form='the',
    )
    decoded = grader_cascade._decode_error(
        raw, ['article_omission', 'preposition'], TAXONOMY_CFG, 'zh', reproduction, reference, 'en',
    )
    assert decoded is not None
    assert decoded['span_reproduction'] == [12, 15]   # nearest, not [0, 3]
    assert decoded['learner_form'] == 'the'


def test_decode_error_first_occurrence_when_span_anchors_there():
    # Same repeated token, but the model's span sits by the FIRST 'the' ([0,3]);
    # an off-by-one there must stay on the first, proving it's genuinely nearest-
    # anchored and not just always snapping to the last occurrence.
    reproduction = 'the cat saw the dog'
    reference = 'the cat saw the dog'
    raw = _base_raw(
        span_repro=[1, 4], learner_form='the',      # off by one, near the 1st 'the'
        span_ref=[0, 3], corrected_form='the',
    )
    decoded = grader_cascade._decode_error(
        raw, ['article_omission', 'preposition'], TAXONOMY_CFG, 'zh', reproduction, reference, 'en',
    )
    assert decoded is not None
    assert decoded['span_reproduction'] == [0, 3]


def test_decode_error_resolves_fullwidth_halfwidth_katakana_via_folding():
    # JA: the learner text carries half-width katakana ｶﾒﾗ; the model echoed the
    # full-width form カメラ, so no exact substring exists. A normalization-aware
    # fallback (NFKC + kata2hira) must resolve it and map back to the raw half-width
    # span — instead of silently dropping a real error (TASK-634 (2)).
    reproduction = 'これはｶﾒﾗです'     # half-width katakana ｶﾒﾗ at [3,6]
    reference = 'これはカメラです'       # full-width katakana カメラ at [3,6]
    raw = _base_raw(
        span_repro=[3, 6], learner_form='カメラ',    # full-width echo — not a literal substring
        span_ref=[3, 6], corrected_form='カメラ',
    )
    decoded = grader_cascade._decode_error(
        raw, ['article_omission', 'preposition'], TAXONOMY_CFG, 'zh', reproduction, reference, 'ja',
    )
    assert decoded is not None
    assert decoded['span_reproduction'] == [3, 6]
    assert decoded['learner_form'] == 'ｶﾒﾗ'          # remapped to the raw half-width substring


def test_decode_error_resolves_capitalized_en_token_via_casefold():
    # EN: the learner wrote 'The' (sentence-initial); the model reported the form
    # lower-cased as 'the'. Casefold folding must resolve it and remap the form to
    # the raw capitalised substring (TASK-634 (2)).
    reproduction = 'The dog barks'      # 'The' at [0,3]
    reference = 'The dog barks'
    raw = _base_raw(
        span_repro=[0, 3], learner_form='the',       # lower-cased echo of 'The'
        span_ref=[0, 3], corrected_form='The',
    )
    decoded = grader_cascade._decode_error(
        raw, ['article_omission', 'preposition'], TAXONOMY_CFG, 'zh', reproduction, reference, 'en',
    )
    assert decoded is not None
    assert decoded['span_reproduction'] == [0, 3]
    assert decoded['learner_form'] == 'The'           # raw substring, not the lower-cased echo


def test_decode_error_drops_form_absent_even_under_folding():
    # A form that isn't in the text even after folding is still unrepairable.
    reproduction = 'The dog barks'
    reference = 'The dog barks'
    raw = _base_raw(
        span_repro=[0, 3], learner_form='ZZZ',
        span_ref=[0, 3], corrected_form='The',
    )
    decoded = grader_cascade._decode_error(
        raw, ['article_omission', 'preposition'], TAXONOMY_CFG, 'zh', reproduction, reference, 'en',
    )
    assert decoded is None


def test_diff_regions_emits_raw_substrings_not_normalized_tokens():
    # The tier-0 diff carries doubly-normalized tokens ('fox'/'dog'); the region
    # hints must be the RAW substrings ('Fox'/'Dog') as they appear in the raw
    # gold/reproduction, so the model quotes forms it can verify (TASK-634 (3)).
    gold = 'The Fox.'
    repro = 'The Dog.'
    diff = [{'op': 'replace', 'correct': 'fox', 'user': 'dog', 'is_correct': False}]
    regions = grader_cascade._diff_regions(diff, gold, repro, 'en')
    assert regions == [{'op': 'replace', 'ref': 'Fox', 'repro': 'Dog'}]


def test_diff_regions_repeated_token_maps_successive_occurrences():
    # A token that appears twice in the diff resolves to successive raw occurrences
    # via the per-side cursor, not the same first occurrence both times.
    gold = 'Go now, go now.'
    repro = 'x'
    diff = [
        {'op': 'replace', 'correct': 'go', 'user': 'a', 'is_correct': False},
        {'op': 'replace', 'correct': 'go', 'user': 'b', 'is_correct': False},
    ]
    regions = grader_cascade._diff_regions(diff, gold, repro, 'en')
    # First 'go' -> 'Go' at [0,2]; second 'go' -> the lower-case 'go' at [8,10].
    assert regions[0]['ref'] == 'Go'
    assert regions[1]['ref'] == 'go'


# ===========================================================================
# TASK-628 — Evidence-First Grading v2 (Detector / Verifier cascade).
#
# Both sections pin the framework explicitly (v1 tests pass framework_v2=False —
# they exercise the rollback path now that Config.DT_FRAMEWORK_V2 defaults ON
# since TASK-632; v2 tests pass framework_v2=True), so neither depends on the
# process-wide default. The v1 body remains the shipped
# flow unchanged. The rubric fixture carries the TASK-627 v5 scoring keys the
# derived-scoring module requires; the taxonomy fixture carries subtype_meta.
# ===========================================================================

# Rubric v5 shape: weights + the three derived-scoring keys (approved provisional
# defaults from the tech spec §4 / TASK-627 seed).
RUBRIC_CFG_V5 = {
    'weights': {
        'default': {
            'accuracy': 0.3, 'understandability': 0.3,
            'fidelity': 0.15, 'range': 0.15, 'naturalness': 0.1,
        },
    },
    'severity_weights': {'minor': 1, 'major': 5, 'critical': 25},
    'understandability_weights': {'minor': 0, 'major': 2, 'critical': 25},
    'band_thresholds': {
        'accuracy': [1, 6, 15], 'fidelity': [1, 6, 15], 'understandability': [2, 6, 25],
    },
}

# subtype index 0 = word_choice (fidelity), index 1 = tense_aspect (accuracy).
TAXONOMY_CFG_V5 = {
    'pairs': {'en': {'subtypes': ['word_choice', 'tense_aspect']}},
    'subtype_meta': {
        'word_choice': {'dimension': 'fidelity'},
        'tense_aspect': {'dimension': 'accuracy'},
    },
    'templates': {
        'word_choice': {'zh': '用词：{learner_form} → {corrected_form}。'},
        'tense_aspect': {'zh': '时态：{learner_form} → {corrected_form}。'},
    },
}

# One detector error: word_choice (fidelity) / major, at the real word9 diff.
DETECTOR_OK = {
    'confidence': 0.9,
    'errors': [{
        'span_repro': [54, 70], 'span_ref': [54, 59],
        'category': 1, 'source': 0, 'severity': 1, 'subtype': 0,
        'learner_form': 'totallydifferent', 'corrected_form': 'word9',
        'confidence': 0.8, 'is_mistake': False,
    }],
    'highlights': [{'span_repro': [0, 5], 'reason': 0}],
}

VERIFIER_OK = {
    'confidence': 0.9,
    'verdicts': [{'error_index': 0, 'verdict': 0}],
    'added_errors': [],
    'judgments': {
        'naturalness': {'band': 3, 'evidence_spans': [[0, 5]]},
        'range': {'band': 3, 'evidence_spans': [[6, 11]]},
    },
}

_ADDED_ERROR = {
    'span_repro': [54, 70], 'span_ref': [54, 59],
    'category': 1, 'source': 0, 'severity': 1, 'subtype': 0,
    'learner_form': 'totallydifferent', 'corrected_form': 'word9',
    'confidence': 0.8, 'is_mistake': False,
}


def _v2_setup(monkeypatch, responses, captured=None):
    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_CFG_V5)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_CFG_V5)
    monkeypatch.setattr(grader_cascade, 'get_active_rubric_version', lambda db: 5)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy_version', lambda db: 5)
    monkeypatch.setattr(grader_cascade, 'resolve_tier', lambda db, tier, lid, **k: _route(tier, f'{tier}-slug'))
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _make_call_model(responses, captured=captured))


def _run_v2(monkeypatch, responses, *, gold=None, repro=None, captured=None):
    _v2_setup(monkeypatch, responses, captured=captured)
    return grader_cascade.grade_submission(
        db=None, passage_id=99, gold_l2=gold or _ten_word_gold(),
        reproduction=repro or _ten_word_repro_one_wrong(),
        l2_language_id=2, l1_language_id=1, age_tier=3, framework_v2=True,
    )


# ---------------------------------------------------------------------------
# Happy path: detector + verifier -> derived scoring
# ---------------------------------------------------------------------------

def test_v2_happy_path_detector_verifier_derived_scoring(monkeypatch):
    result = _run_v2(monkeypatch, {'tier1-slug': DETECTOR_OK, 'tier2-slug': VERIFIER_OK})

    # Derived: fidelity penalty 5 (one major word_choice) -> band 3; accuracy 0 ->
    # 4; understandability 2 -> 4. Judged naturalness/range 3.
    assert result['scores'] == {
        'accuracy': 4, 'fidelity': 3, 'understandability': 4, 'naturalness': 3, 'range': 3,
    }
    assert result['overall_band'] == 4  # weighted mean 3.6 -> 4
    assert result['provisional'] is False

    assert len(result['errors']) == 1
    err = result['errors'][0]
    assert err['subtype'] == 'word_choice'
    assert err['severity'] == 'major'
    assert err['explanation'] == '用词：totallydifferent → word9。'

    assert result['highlights'] == [{'span_reproduction': [0, 5], 'reason': 'grammar'}]

    trace = result['grader_trace']
    assert trace['framework_version'] == 2
    assert trace['provisional'] is False
    assert trace['rejected_count'] == 0
    assert trace['prompt_version'] == {'rubric': 5, 'taxonomy': 5}
    assert trace['tier'] == 'tier2'


# ---------------------------------------------------------------------------
# Verdict merge rules
# ---------------------------------------------------------------------------

def test_v2_verdict_reject_drops_error_and_counts(monkeypatch):
    verifier = {**VERIFIER_OK, 'verdicts': [{'error_index': 0, 'verdict': 1}]}
    result = _run_v2(monkeypatch, {'tier1-slug': DETECTOR_OK, 'tier2-slug': verifier})

    assert result['errors'] == []              # rejected -> not shown
    assert result['grader_trace']['rejected_count'] == 1
    assert result['scores']['fidelity'] == 4   # penalty gone -> full band
    assert result['provisional'] is False


def test_v2_verdict_adjust_changes_severity_and_bands(monkeypatch):
    # Adjust the word_choice error from major -> critical.
    verifier = {**VERIFIER_OK, 'verdicts': [{'error_index': 0, 'verdict': 2, 'severity': 2}]}
    result = _run_v2(monkeypatch, {'tier1-slug': DETECTOR_OK, 'tier2-slug': verifier})

    assert result['errors'][0]['severity'] == 'critical'
    assert result['scores']['fidelity'] == 1          # penalty 25 > t2(15) -> band 1
    assert result['scores']['understandability'] == 2  # und penalty 25 -> band 2


def test_v2_missing_verdict_defaults_to_confirm(monkeypatch):
    verifier = {**VERIFIER_OK, 'verdicts': []}  # no verdict for error 0
    result = _run_v2(monkeypatch, {'tier1-slug': DETECTOR_OK, 'tier2-slug': verifier})

    assert len(result['errors']) == 1  # kept via default-confirm
    assert result['grader_trace']['rejected_count'] == 0


def test_v2_unknown_verdict_index_dropped(monkeypatch):
    # A reject aimed at a non-existent index must be ignored (not applied to error 0).
    verifier = {**VERIFIER_OK, 'verdicts': [{'error_index': 9, 'verdict': 1}]}
    result = _run_v2(monkeypatch, {'tier1-slug': DETECTOR_OK, 'tier2-slug': verifier})

    assert len(result['errors']) == 1              # error 0 still confirmed by default
    assert result['grader_trace']['rejected_count'] == 0


# ---------------------------------------------------------------------------
# Judgment evidence gate + renormalization
# ---------------------------------------------------------------------------

def test_v2_judgment_without_evidence_is_discarded_and_renormalized(monkeypatch):
    verifier = {
        **VERIFIER_OK,
        'judgments': {
            'naturalness': {'band': 1, 'evidence_spans': []},       # no evidence -> discarded
            'range': {'band': 3, 'evidence_spans': [[0, 5]]},
        },
    }
    result = _run_v2(monkeypatch, {'tier1-slug': DETECTOR_OK, 'tier2-slug': verifier})

    assert 'naturalness' not in result['scores']   # dropped -> not scored
    assert 'range' in result['scores']
    # Overall renormalizes over the remaining dims (its evidence-free band 1 for
    # naturalness never pulls the mean down).
    assert result['overall_band'] == 4
    assert result['provisional'] is False


# ---------------------------------------------------------------------------
# Failure matrix (§2)
# ---------------------------------------------------------------------------

def test_v2_detector_fail_verifier_detects_from_empty(monkeypatch):
    verifier = {
        'confidence': 0.9, 'verdicts': [], 'added_errors': [dict(_ADDED_ERROR)],
        'judgments': {
            'naturalness': {'band': 2, 'evidence_spans': [[0, 5]]},
            'range': {'band': 2, 'evidence_spans': [[6, 11]]},
        },
    }
    result = _run_v2(monkeypatch, {'tier1-slug': 'not json at all', 'tier2-slug': verifier})

    assert len(result['errors']) == 1              # detected by the verifier's added_errors
    assert result['provisional'] is True
    trace = result['grader_trace']
    assert trace['framework_version'] == 2
    assert 'detector' in trace['reason']


def test_v2_verifier_fail_uses_unverified_detector_errors_renormalized(monkeypatch):
    result = _run_v2(monkeypatch, {'tier1-slug': DETECTOR_OK, 'tier2-slug': 'not json'})

    assert len(result['errors']) == 1              # detector errors shown unverified
    assert result['provisional'] is True
    # No judgments -> naturalness/range omitted from the (renormalized) mean.
    assert 'naturalness' not in result['scores']
    assert 'range' not in result['scores']
    assert result['scores']['fidelity'] == 3       # derived scoring still ran
    assert 'verifier' in result['grader_trace']['reason']


def test_v2_both_fail_no_scores_provisional_diff_only(monkeypatch):
    result = _run_v2(monkeypatch, {'tier1-slug': 'x', 'tier2-slug': 'y'})

    assert result['scores'] == {}
    assert result['overall_band'] is None          # never a silent full-marks default
    assert result['errors'] == []
    assert result['provisional'] is True
    assert result['diff']                          # tier-0 diff still surfaced
    reason = result['grader_trace']['reason']
    assert 'detector' in reason and 'verifier' in reason


# ---------------------------------------------------------------------------
# Highlights cap
# ---------------------------------------------------------------------------

def test_v2_highlights_capped_at_three(monkeypatch):
    detector = {
        **DETECTOR_OK,
        'highlights': [{'span_repro': [i, i + 3], 'reason': i % 4} for i in range(0, 25, 5)],  # 5
    }
    result = _run_v2(monkeypatch, {'tier1-slug': detector, 'tier2-slug': VERIFIER_OK})

    assert len(result['highlights']) == 3


# ---------------------------------------------------------------------------
# Tier-3 arbiter (config-gated, default OFF)
# ---------------------------------------------------------------------------

def test_v2_arbiter_off_by_default_never_calls_tier3(monkeypatch):
    # Verifier rejects the only error at low confidence — both arbiter triggers —
    # but the flag is off, so tier3 is never resolved/called.
    verifier = {
        'confidence': 0.2, 'verdicts': [{'error_index': 0, 'verdict': 1}],
        'added_errors': [], 'judgments': VERIFIER_OK['judgments'],
    }
    captured = []
    result = _run_v2(monkeypatch, {'tier1-slug': DETECTOR_OK, 'tier2-slug': verifier}, captured=captured)

    assert not any(c['model'] == 'tier3-slug' for c in captured)
    assert 'arbiter' not in result['grader_trace']
    assert result['errors'] == []                  # verifier's rejection stands


def test_v2_arbiter_fires_when_enabled_and_triggered(monkeypatch):
    monkeypatch.setattr(grader_cascade.Config, 'DT_TIER3_ARBITER_ENABLED', True)
    verifier = {
        'confidence': 0.2, 'verdicts': [{'error_index': 0, 'verdict': 1}],  # reject_rate 1.0
        'added_errors': [], 'judgments': VERIFIER_OK['judgments'],
    }
    arbiter = {  # re-adjudicates: confirm the error the verifier rejected
        'confidence': 0.9, 'verdicts': [{'error_index': 0, 'verdict': 0}],
        'added_errors': [], 'judgments': VERIFIER_OK['judgments'],
    }
    captured = []
    result = _run_v2(monkeypatch, {
        'tier1-slug': DETECTOR_OK, 'tier2-slug': verifier, 'tier3-slug': arbiter,
    }, captured=captured)

    assert any(c['model'] == 'tier3-slug' for c in captured)
    trace = result['grader_trace']
    assert trace['arbiter']['triggered'] is True
    assert trace['arbiter']['used'] is True
    assert trace['tier'] == 'tier3'
    assert len(result['errors']) == 1              # arbiter re-confirmed it
    assert trace['rejected_count'] == 0
