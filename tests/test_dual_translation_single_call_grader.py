"""Unit tests for the DT single-call generative grader (ADR-044).

DB-free and OpenRouter-free, in the style of test_dual_translation_grader_cascade.py:
the model boundary (``single_call_grader.call_structured``), the observability
boundary (``single_call_grader._log_call``) and the rubric/taxonomy loaders are
monkeypatched. The taxonomy and rubric are the real v6 seeds, parsed offline from
their migration files (the same extraction the seed tests use), because the frozen
prompt is only valid under taxonomy v6.
"""

import json
import os
import re
import sys

import pytest

import routes.dual_translation as dt_routes
from config import Config
from services.dimension_service import DimensionService
from services.dual_translation import (
    grader_cascade, single_call_grader as scg, single_call_prompts as sc_prompts, tier0,
)
from services.dual_translation.sentence_pairs import build_sentence_pairs

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG_IDS = {'zh': 1, 'en': 2, 'ja': 3}
LANG_CODES = {v: k for k, v in LANG_IDS.items()}

PRIMARY = 'openai/gpt-6-luna'
FALLBACK = 'deepseek/deepseek-v4.1-flash'


def _seed_literal(filename, tag):
    with open(os.path.join(_REPO, 'migrations', filename), encoding='utf-8') as fh:
        text = fh.read()
    return json.loads(re.search(rf"\${tag}\$(.*?)\${tag}\$", text, re.DOTALL).group(1))


TAXONOMY_V6 = _seed_literal('dt_taxonomy_v6_seed.sql', 'taxonomy')
RUBRIC_V6 = _seed_literal('dt_rubric_v6_seed.sql', 'rubric')


class _NoDB:
    """Any DB read raises — the variant resolver degrades to basis 'default'."""

    def table(self, *a, **k):
        raise RuntimeError('no DB in unit tests')


class _FakeModel:
    """Stands in for ``call_structured``. ``responses`` maps slug -> content
    string, dict (JSON-encoded on the way out) or Exception (raised)."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, slug, system_prompt, user_prompt, *, schema, max_tokens, extra=None, timeout=30):
        self.calls.append({
            'slug': slug, 'system': system_prompt, 'user': user_prompt,
            'schema': schema, 'max_tokens': max_tokens, 'extra': extra,
        })
        response = self.responses[slug]
        if isinstance(response, Exception):
            raise response
        content = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
        return {
            'content': content, 'tokens_in': 1700, 'tokens_out': 60, 'cached_tokens': 1024,
            'reasoning_tokens': 0, 'cost_usd': 0.00006, 'latency_s': 1.25,
            'provider': 'TestProvider', 'finish_reason': 'stop',
        }


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.setattr(DimensionService, 'get_language_code', classmethod(lambda cls, lid: LANG_CODES.get(lid)))
    monkeypatch.setattr(grader_cascade, 'get_active_rubric', lambda db: RUBRIC_V6)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: TAXONOMY_V6)
    monkeypatch.setattr(grader_cascade, 'get_active_rubric_version', lambda db: 6)
    monkeypatch.setattr(grader_cascade, 'get_active_taxonomy_version', lambda db: 6)
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_GRADER', False)
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_MODEL', PRIMARY)
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_FALLBACK_MODEL', FALLBACK)
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_FREE_TRANSLATION', False)
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_EXPLAINER', False)
    monkeypatch.setattr(Config, 'DT_TAXONOMY_COLUMNS', False)
    monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', False)
    tier0.clear_cache()
    yield
    tier0.clear_cache()


@pytest.fixture
def logged(monkeypatch):
    calls = []
    monkeypatch.setattr(
        scg, '_log_call',
        lambda attempt, **kw: calls.append({'attempt': attempt, **kw}),
    )
    return calls


def _use_model(monkeypatch, responses):
    model = _FakeModel(responses)
    monkeypatch.setattr(scg, 'call_structured', model)
    return model


def _no_other_flow(monkeypatch):
    """Fail the test if grading reaches the v1/v2 model boundary."""
    def _boom(*a, **k):
        raise AssertionError('the configured v1/v2 flow must not run')
    monkeypatch.setattr(grader_cascade, '_grade_v2', _boom)
    monkeypatch.setattr(grader_cascade, 'call_model_with_usage', _boom)


def _grade(gold, reproduction, l2, *, l1=None, single_call=True, **kwargs):
    l1 = l1 or ('zh' if l2 == 'en' else 'en')
    return grader_cascade.grade_submission(
        _NoDB(), passage_id=1, gold_l2=gold, reproduction=reproduction,
        l2_language_id=LANG_IDS[l2], l1_language_id=LANG_IDS[l1], age_tier=3,
        single_call=single_call, **kwargs,
    )


def _entry(sentence, span, type_, severity, explanation='Use the reference form here instead.'):
    return {'sentence': sentence, 'span': span, 'type': type_, 'severity': severity,
            'explanation': explanation}


EN_GOLD = ('First, you need an Arduino board. This is a small computer. '
           'You can make many things with it.')
EN_TENSE = EN_GOLD.replace('This is a small', 'This was a small')
EN_INVERTED = EN_GOLD.replace('things with it', 'things without it')
EN_SYNONYM = EN_GOLD.replace('a small computer', 'a little computer')

ZH_GOLD = '我买了一件衣服。这件衣服很漂亮。我非常开心。'
ZH_MEASURE = ZH_GOLD.replace('一件衣服', '一个衣服')

JA_GOLD = '必要な部品がセットになったキットがあります。これはとても便利です。'
JA_PARTICLE = JA_GOLD.replace('部品が', '部品は')

REQUIRED_ERROR_FIELDS = {
    'span_reproduction', 'span_reference', 'category', 'subtype', 'source', 'severity',
    'learner_form', 'corrected_form', 'explanation', 'confidence', 'is_mistake',
    'explanation_parts',
}


# ---------------------------------------------------------------------------
# Happy path, per language
# ---------------------------------------------------------------------------

class TestHappyPath:

    def test_en_error_is_decoded_into_the_contract_shape(self, monkeypatch, logged):
        _no_other_flow(monkeypatch)
        model = _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'verb_form_tense', 'minor', 'Use "is" for a present fact.'),
        ]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert len(model.calls) == 1 and model.calls[0]['slug'] == PRIMARY
        assert set(contract) >= {'scores', 'overall_band', 'diff', 'errors', 'grader_trace'}
        (err,) = contract['errors']
        assert REQUIRED_ERROR_FIELDS <= set(err)
        start, end = err['span_reproduction']
        assert EN_TENSE[start:end] == err['learner_form'] == 'was'
        rs, re_ = err['span_reference']
        assert EN_GOLD[rs:re_] == err['corrected_form'] == 'is'
        assert err['subtype'] == 'verb_form_tense'
        assert err['category'] == 'grammatical'
        assert err['sentence_index'] == 1
        assert err['span_source'] == 'model'
        assert err['correction_source'] == 'aligned_diff'
        # en + gpt-6-luna -> the taxonomy default severity (major) is applied;
        # the model's own value is kept alongside.
        assert err['severity'] == 'major'
        assert err['model_severity'] == 'minor'
        assert contract['scores']['accuracy'] == 3
        assert contract['grader_trace']['single_call']['severity_rule'] == 'prior'

    def test_zh_uses_the_models_own_severity(self, monkeypatch, logged):
        _no_other_flow(monkeypatch)
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(1, '一个', 'measure_word', 'major', '衣服 takes the classifier 件.'),
        ]}})

        contract = _grade(ZH_GOLD, ZH_MEASURE, 'zh')

        (err,) = contract['errors']
        assert err['learner_form'] == '一个' and err['corrected_form'] == '一件'
        assert ZH_MEASURE[err['span_reproduction'][0]:err['span_reproduction'][1]] == '一个'
        # measure_word defaults to minor in the taxonomy; zh keeps the model's major.
        assert TAXONOMY_V6['subtype_meta']['measure_word']['default_severity'] == 'minor'
        assert err['severity'] == err['model_severity'] == 'major'
        assert contract['grader_trace']['single_call']['severity_rule'] == 'model'
        assert err['sentence_index'] == 0

    def test_ja_error(self, monkeypatch, logged):
        _no_other_flow(monkeypatch)
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(1, 'は', 'case_particle', 'major', 'Use が to mark the included parts.'),
        ]}})

        contract = _grade(JA_GOLD, JA_PARTICLE, 'ja')

        (err,) = contract['errors']
        assert err['learner_form'] == 'は' and err['corrected_form'] == 'が'
        assert JA_GOLD[err['span_reference'][0]:err['span_reference'][1]] == 'が'
        assert err['severity'] == 'major'
        assert contract['grader_trace']['single_call']['severity_rule'] == 'model'
        assert contract['scores'] == {'accuracy': 3, 'fidelity': 4, 'understandability': 4}

    def test_explanation_is_the_template_and_the_model_note_is_separate(self, monkeypatch, logged):
        note = 'Use "is" for a present fact.'
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(2, 'was', 'verb_form_tense', 'major', note)]}})

        (err,) = _grade(EN_GOLD, EN_TENSE, 'en', l1='zh')['errors']

        template = TAXONOMY_V6['templates']['verb_form_tense']['zh']
        assert err['explanation'] == template.format(learner_form='was', corrected_form='is')
        assert note not in err['explanation']
        assert err['explanation_parts'] == {
            'rule': err['explanation'], 'application': None, 'model_note': note,
        }
        assert err['model_note'] == note

    def test_only_the_three_validated_dimensions_are_scored(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(2, 'was', 'verb_form_tense', 'major')]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert set(contract['scores']) == {'accuracy', 'fidelity', 'understandability'}
        assert contract['grader_trace']['single_call']['unscored_dimensions'] == ['naturalness', 'range']
        assert contract['provisional'] is False
        assert 1 <= contract['overall_band'] <= 4


class TestMeaningInversion:

    def test_inversion_is_critical_whatever_the_severity_rule(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(3, 'without', 'meaning_inversion', 'critical', 'This reverses the meaning.'),
        ]}})

        contract = _grade(EN_GOLD, EN_INVERTED, 'en')

        (err,) = contract['errors']
        assert err['severity'] == 'critical'
        assert (err['learner_form'], err['corrected_form']) == ('without', 'with')
        # meaning_inversion is a fidelity type; a critical error floors fidelity
        # and understandability under the v6 rubric weights.
        assert contract['scores']['fidelity'] == 1
        assert contract['scores']['understandability'] == 2
        assert contract['overall_band'] < 4

    def test_prior_rule_never_downgrades_a_model_critical(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(3, 'without', 'word_choice', 'critical')]}})

        (err,) = _grade(EN_GOLD, EN_INVERTED, 'en')['errors']

        assert TAXONOMY_V6['subtype_meta']['word_choice']['default_severity'] == 'minor'
        assert err['severity'] == 'critical'


class TestCleanSubmission:

    def test_no_errors_is_full_marks_on_the_scored_dimensions(self, monkeypatch, logged):
        _no_other_flow(monkeypatch)
        _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en')

        assert contract['errors'] == []
        assert contract['scores'] == {'accuracy': 4, 'fidelity': 4, 'understandability': 4}
        assert contract['overall_band'] == 4
        trace = contract['grader_trace']['single_call']
        assert trace['used'] is True and trace['errors_raw'] == 0 and trace['dropped_total'] == 0

    def test_exact_match_still_short_circuits_at_tier0(self, monkeypatch, logged):
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        contract = _grade(EN_GOLD, EN_GOLD, 'en')

        assert model.calls == []
        assert contract['grader_trace']['deterministic_prefilter'] is True
        assert 'single_call' not in contract['grader_trace']
        assert 'grading_assets' not in contract


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------

_V2_SENTINEL = {
    'scores': {'accuracy': 2}, 'overall_band': 2, 'diff': [], 'errors': [], 'highlights': [],
    'grader_trace': {'tier': 'tier2', 'tokens': {'in': 100, 'out': 10}, 'framework_version': 2},
    'provisional': False,
}


def _sentinel_v2(monkeypatch):
    calls = []

    def _fake_v2(db, **kwargs):
        calls.append(kwargs)
        return json.loads(json.dumps(_V2_SENTINEL))
    monkeypatch.setattr(grader_cascade, '_grade_v2', _fake_v2)
    return calls


class TestFallbacks:

    def test_malformed_json_falls_back_to_the_second_model(self, monkeypatch, logged):
        _no_other_flow(monkeypatch)
        model = _use_model(monkeypatch, {
            PRIMARY: 'Sure! Here are the errors: {"errors": [',
            FALLBACK: {'errors': [_entry(2, 'was', 'verb_form_tense', 'major')]},
        })

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert [c['slug'] for c in model.calls] == [PRIMARY, FALLBACK]
        trace = contract['grader_trace']
        sc = trace['single_call']
        assert sc['used'] is True and sc['path'] == 'fallback_model' and sc['model'] == FALLBACK
        assert [a['status'] for a in sc['attempts']] == ['malformed_json', 'ok']
        assert trace['reason'] == f'primary {PRIMARY} malformed_json'
        assert trace['tokens'] == {'in': 3400, 'out': 120}  # both attempts were paid for
        assert sc['cost_usd'] == pytest.approx(0.00012)
        assert len(contract['errors']) == 1
        # Each model sends its own validated "reasoning off" parameter.
        assert model.calls[0]['extra'] == {'reasoning': {'effort': 'none'}}
        assert model.calls[1]['extra'] == {'reasoning': {'enabled': False}}

    def test_wrong_shape_counts_as_unusable(self, monkeypatch, logged):
        _use_model(monkeypatch, {
            PRIMARY: {'decisions': []},
            FALLBACK: {'errors': []},
        })

        sc = _grade(EN_GOLD, EN_TENSE, 'en')['grader_trace']['single_call']

        assert [a['status'] for a in sc['attempts']] == ['malformed_shape', 'ok']

    def test_both_models_failing_falls_back_to_the_configured_flow(self, monkeypatch, logged):
        v2_calls = _sentinel_v2(monkeypatch)
        model = _use_model(monkeypatch, {
            PRIMARY: RuntimeError('503 upstream overloaded'),
            FALLBACK: 'not json at all',
        })

        contract = _grade(EN_GOLD, EN_TENSE, 'en', framework_v2=True)

        assert [c['slug'] for c in model.calls] == [PRIMARY, FALLBACK]  # the fallback is tried once
        assert len(v2_calls) == 1
        assert contract['scores'] == {'accuracy': 2} and contract['overall_band'] == 2
        trace = contract['grader_trace']
        assert trace['tier'] == 'tier2'
        sc = trace['single_call']
        assert sc['used'] is False and sc['path'] == 'fallback_flow:v2'
        assert sc['reason'] == f'primary {PRIMARY} call_failed; fallback {FALLBACK} malformed_json'
        assert [a['status'] for a in sc['attempts']] == ['call_failed', 'malformed_json']
        assert '503' in sc['attempts'][0]['error']
        # v2's own 100/10 plus the one fallback attempt that returned usage.
        assert trace['tokens'] == {'in': 1800, 'out': 70}
        assets = contract['grading_assets']
        assert [a['status'] for a in assets] == ['call_failed', 'malformed_json']
        assert assets[0]['raw_response'] is None
        assert assets[1]['raw_response'] == 'not json at all' and assets[1]['response'] is None

    def test_failure_never_awards_silent_full_marks(self, monkeypatch, logged):
        """Both single-call models down AND the v2 flow producing no scores ->
        the contract has no overall_band (the route then declines to persist)."""
        monkeypatch.setattr(grader_cascade, '_grade_v2', lambda db, **k: {
            'scores': {}, 'overall_band': None, 'diff': [], 'errors': [], 'highlights': [],
            'grader_trace': {'tokens': {'in': 0, 'out': 0}, 'framework_version': 2}, 'provisional': True,
        })
        _use_model(monkeypatch, {PRIMARY: RuntimeError('down'), FALLBACK: RuntimeError('down')})

        contract = _grade(EN_GOLD, EN_TENSE, 'en', framework_v2=True)

        assert contract['overall_band'] is None and contract['scores'] == {}
        assert contract['grader_trace']['single_call']['used'] is False

    def test_no_fallback_model_configured(self, monkeypatch, logged):
        _sentinel_v2(monkeypatch)
        monkeypatch.setattr(Config, 'DT_SINGLE_CALL_FALLBACK_MODEL', '')
        model = _use_model(monkeypatch, {PRIMARY: 'garbage'})

        contract = _grade(EN_GOLD, EN_TENSE, 'en', framework_v2=True)

        assert [c['slug'] for c in model.calls] == [PRIMARY]
        assert contract['grader_trace']['single_call']['path'] == 'fallback_flow:v2'

    def test_taxonomy_without_the_frozen_types_skips_the_call(self, monkeypatch, logged):
        v5_like = dict(TAXONOMY_V6, pairs={'en': {'subtypes': ['omission', 'tense_aspect']}})
        monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: v5_like)
        v2_calls = _sentinel_v2(monkeypatch)
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en', framework_v2=True)

        assert model.calls == [] and len(v2_calls) == 1
        sc = contract['grader_trace']['single_call']
        assert sc['used'] is False and sc['reason'].startswith('taxonomy mismatch')
        assert 'grading_assets' not in contract

    def test_unexpected_exception_inside_the_flow_falls_back(self, monkeypatch, logged):
        _sentinel_v2(monkeypatch)
        _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        def _explode(*a, **k):
            raise KeyError('boom')
        monkeypatch.setattr(scg, '_decode', _explode)

        contract = _grade(EN_GOLD, EN_TENSE, 'en', framework_v2=True)

        assert contract['overall_band'] == 2
        assert 'KeyError' in contract['grader_trace']['single_call']['reason']


# ---------------------------------------------------------------------------
# Span validation
# ---------------------------------------------------------------------------

class TestSpanValidation:

    def test_fragment_not_in_the_named_sentence_is_repaired_to_that_sentence(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'This were a tiny computer', 'verb_form_tense', 'major'),
        ]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        (err,) = contract['errors']
        assert err['span_source'] == 'sentence'
        assert err['learner_form'] == 'This was a small computer.'
        assert EN_TENSE[err['span_reproduction'][0]:err['span_reproduction'][1]] == err['learner_form']
        assert err['corrected_form'] == 'This is a small computer.'
        assert err['correction_source'] == 'reference_sentence'
        sc = contract['grader_trace']['single_call']
        assert sc['span_repaired'] == 1 and sc['dropped_total'] == 0

    def test_fragment_found_in_another_sentence_is_relocated(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(1, 'was', 'verb_form_tense', 'major')]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        (err,) = contract['errors']
        assert err['span_source'] == 'repaired'
        assert err['sentence_index'] == 1  # where the text actually is, not what the model said
        assert err['corrected_form'] == 'is'
        assert contract['grader_trace']['single_call']['span_repaired'] == 1

    def test_unlocatable_fragment_with_no_usable_sentence_is_dropped_and_counted(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(99, 'text that is nowhere', 'word_choice', 'major'),
            _entry(2, 'was', 'verb_form_tense', 'major'),
        ]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert [e['learner_form'] for e in contract['errors']] == ['was']
        sc = contract['grader_trace']['single_call']
        assert sc['errors_raw'] == 2 and sc['errors_kept'] == 1
        assert sc['dropped'] == {'invalid_entry': 0, 'span_unlocatable': 1, 'decode_rejected': 0}
        assert sc['dropped_total'] == 1
        assert contract['scores']['accuracy'] == 3  # only the kept error is scored

    def test_entry_with_a_type_outside_the_schema_is_dropped(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'not_a_type', 'major'),
            _entry(2, 'was', 'verb_form_tense', 'severe'),
            'a string, not an object',
        ]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert contract['errors'] == []
        assert contract['grader_trace']['single_call']['dropped']['invalid_entry'] == 3
        assert contract['scores']['accuracy'] == 4

    def test_dropped_word_next_to_the_flagged_text_is_pulled_into_the_correction(self, monkeypatch, logged):
        gold = 'It is not a toy. It is a tool.'
        repro = 'It is a toy. It is a tool.'
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(1, 'is', 'meaning_inversion', 'critical')]}})

        (err,) = _grade(gold, repro, 'en')['errors']

        assert (err['learner_form'], err['corrected_form']) == ('is', 'is not')
        assert gold[err['span_reference'][0]:err['span_reference'][1]] == 'is not'

    def test_free_rewrite_uses_the_whole_reference_sentence(self, monkeypatch, logged):
        gold = 'The weather was lovely yesterday. We stayed outside.'
        repro = 'Rain fell hard on Monday morning. We stayed outside.'
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(1, 'Rain fell hard', 'word_choice', 'major')]}})

        (err,) = _grade(gold, repro, 'en')['errors']

        assert err['learner_form'] == 'Rain fell hard' and err['span_source'] == 'model'
        assert err['corrected_form'] == 'The weather was lovely yesterday.'
        assert err['correction_source'] == 'reference_sentence'


class TestModelNoteGuards:

    @pytest.mark.parametrize('text', [None, '', '   ', 'x' * 241, 'two\nparagraphs', 'worth 3/4 marks', 7])
    def test_rejected(self, text):
        assert scg._validated_model_note(text) is None

    def test_accepted_and_trimmed(self):
        assert scg._validated_model_note('  Use "is" here.  ') == 'Use "is" here.'

    def test_rejected_note_does_not_drop_the_error(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(2, 'was', 'verb_form_tense', 'major', 'y' * 500)]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        (err,) = contract['errors']
        assert err['model_note'] is None and err['explanation_parts']['model_note'] is None
        # The raw text is still kept (capped) for later review.
        raw = contract['grader_trace']['single_call']['per_error'][0]['model_explanation']
        assert raw == 'y' * scg.RAW_FIELD_CAP


# ---------------------------------------------------------------------------
# Dispatch / flag
# ---------------------------------------------------------------------------

class TestDispatch:

    def test_flag_off_leaves_the_configured_flow_untouched(self, monkeypatch, logged):
        v2_calls = _sentinel_v2(monkeypatch)
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en', single_call=None, framework_v2=True)

        assert Config.DT_SINGLE_CALL_GRADER is False
        assert model.calls == [] and logged == []
        assert len(v2_calls) == 1
        assert contract == _V2_SENTINEL  # byte-for-byte the v2 contract: no single_call key, no assets

    def test_default_is_off(self):
        """Read the defaults in a fresh interpreter with the DT_* variables unset
        (reloading config in-process would swap the Config class under other tests)."""
        import subprocess
        env = {k: v for k, v in os.environ.items() if not k.startswith('DT_')}
        code = (
            "from config import Config as C; import json; print(json.dumps(["
            "C.DT_SINGLE_CALL_GRADER, C.DT_SINGLE_CALL_FREE_TRANSLATION, C.DT_SINGLE_CALL_EXPLAINER, "
            "C.DT_GRADING_ASSET_COLUMNS, C.DT_SINGLE_CALL_MODEL, C.DT_SINGLE_CALL_FALLBACK_MODEL]))"
        )
        out = subprocess.run(
            [sys.executable, '-c', code], cwd=_REPO, env=env, capture_output=True, text=True, check=True,
        ).stdout.strip().splitlines()[-1]
        assert json.loads(out) == [False, False, False, False, PRIMARY, FALLBACK]

    def test_config_flag_selects_the_flow(self, monkeypatch, logged):
        _no_other_flow(monkeypatch)
        monkeypatch.setattr(Config, 'DT_SINGLE_CALL_GRADER', True)
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en', single_call=None)

        assert len(model.calls) == 1
        assert contract['grader_trace']['tier'] == 'single_call'

    def test_explicit_false_overrides_the_config_flag(self, monkeypatch, logged):
        v2_calls = _sentinel_v2(monkeypatch)
        monkeypatch.setattr(Config, 'DT_SINGLE_CALL_GRADER', True)
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        _grade(EN_GOLD, EN_TENSE, 'en', single_call=False, framework_v2=True)

        assert model.calls == [] and len(v2_calls) == 1

    def test_model_slug_comes_from_config(self, monkeypatch, logged):
        monkeypatch.setattr(Config, 'DT_SINGLE_CALL_MODEL', 'vendor/other-model')
        model = _use_model(monkeypatch, {'vendor/other-model': {'errors': [_entry(2, 'was', 'verb_form_tense', 'minor')]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert model.calls[0]['slug'] == 'vendor/other-model'
        assert model.calls[0]['extra'] is None
        # No validated severity rule for an unknown slug -> the model's own severity.
        assert contract['grader_trace']['single_call']['severity_rule'] == 'model'
        assert contract['errors'][0]['severity'] == 'minor'

    def test_runs_even_when_the_token_budget_caps_the_cascade(self, monkeypatch, logged):
        _no_other_flow(monkeypatch)
        _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en', max_tier='tier1')

        assert contract['grader_trace']['single_call']['used'] is True


# ---------------------------------------------------------------------------
# Trace, assets, observability
# ---------------------------------------------------------------------------

class TestTraceAndAssets:

    def _graded(self, monkeypatch):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'verb_form_tense', 'minor', 'Use "is" for a present fact.'),
        ]}})
        return _grade(EN_GOLD, EN_TENSE, 'en')

    def test_trace_contents(self, monkeypatch, logged):
        trace = self._graded(monkeypatch)['grader_trace']

        assert trace['tier'] == 'single_call' and trace['framework_version'] == 'single_call'
        assert trace['tokens'] == {'in': 1700, 'out': 60}  # the shape the daily budget sums
        assert trace['fell_open'] is False and trace['provisional'] is False
        assert trace['prompt_version'] == {
            'rubric': 6, 'taxonomy': 6, 'single_call': sc_prompts.PROMPT_VERSION,
        }
        assert trace['slugs'] == [
            {'requested_tier': 'single_call', 'tier': 'single_call', 'slug': PRIMARY, 'fell_open': False},
        ]
        sc = trace['single_call']
        assert sc['used'] is True and sc['path'] == 'primary'
        assert sc['model'] == PRIMARY and sc['provider'] == 'TestProvider'
        assert sc['prompt_version'] == sc_prompts.PROMPT_VERSION
        assert sc['prompt_variant'] == 'p1_expl'
        assert sc['parse_status'] == 'ok'
        assert sc['usage'] == {'in': 1700, 'out': 60, 'cached': 1024, 'reasoning': 0}
        assert sc['cost_usd'] == pytest.approx(0.00006)
        assert sc['latency_ms'] == 1250
        assert sc['errors_raw'] == 1 and sc['errors_kept'] == 1 and sc['dropped_total'] == 0
        assert sc['defaults'] == {'source': 'intralingual', 'confidence': 0.5}
        assert sc['sentence_pairs'] == {'n': 3, 'aligned_ok': True}
        assert sc['per_error'] == [{
            'sentence_index': 1, 'subtype': 'verb_form_tense',
            'model_severity': 'minor', 'applied_severity': 'major',
            'span_source': 'model', 'correction_source': 'aligned_diff',
            'model_explanation': 'Use "is" for a present fact.', 'confidence': None,
        }]
        json.dumps(trace)  # must be storable as jsonb

    def test_asset_record_is_structured_and_carries_no_prompt_or_passage_text(self, monkeypatch, logged):
        contract = self._graded(monkeypatch)

        (asset,) = contract['grading_assets']
        assert asset['flow'] == 'single_call' and asset['role'] == 'primary'
        assert asset['model_slug'] == PRIMARY and asset['status'] == 'ok'
        assert asset['prompt_version'] == sc_prompts.PROMPT_VERSION
        assert asset['severity_rule'] == 'prior'
        assert (asset['tokens_in'], asset['tokens_out'], asset['cached_tokens']) == (1700, 60, 1024)
        assert asset['cost_usd'] == pytest.approx(0.00006) and asset['latency_ms'] == 1250
        assert asset['response'] == {'errors': [{
            'sentence': 2, 'span': 'was', 'type': 'verb_form_tense', 'severity': 'minor',
            'explanation': 'Use "is" for a present fact.',
        }]}
        assert asset['raw_response'] is None  # parsed fine -> no duplicate raw text
        assert (asset['errors_raw'], asset['errors_kept']) == (1, 1)
        blob = json.dumps(asset, ensure_ascii=False)
        assert EN_GOLD not in blob and 'Error types' not in blob
        assert len(blob) < 1200
        assert set(asset) <= set(dt_routes._GRADING_CALL_COLUMNS)

    def test_unparsable_raw_response_is_capped(self, monkeypatch, logged):
        _sentinel_v2(monkeypatch)
        monkeypatch.setattr(Config, 'DT_SINGLE_CALL_FALLBACK_MODEL', '')
        _use_model(monkeypatch, {PRIMARY: 'z' * 20000})

        (asset,) = _grade(EN_GOLD, EN_TENSE, 'en', framework_v2=True)['grading_assets']

        assert len(asset['raw_response']) == scg.RAW_RESPONSE_CAP
        assert asset['raw_truncated'] is True

    def test_every_attempt_is_logged_for_llm_calls(self, monkeypatch, logged):
        _use_model(monkeypatch, {
            PRIMARY: 'garbage',
            FALLBACK: {'errors': []},
        })

        _grade(EN_GOLD, EN_TENSE, 'en')

        assert [(c['attempt']['slug'], c['attempt']['status']) for c in logged] == [
            (PRIMARY, 'malformed_json'), (FALLBACK, 'ok'),
        ]
        assert logged[0]['raw_response'] == 'garbage' and logged[1]['raw_response'] is None
        assert all(c['l2_code'] == 'en' and len(c['prompt_hash']) == 32 for c in logged)

    def test_log_call_goes_through_the_shared_helper_and_is_fail_soft(self, monkeypatch):
        from services import llm_service
        rows = []
        monkeypatch.setattr(llm_service, '_log_llm_call', lambda **kw: rows.append(kw))
        attempt = {'role': 'fallback', 'slug': FALLBACK, 'status': 'ok', 'provider': 'P',
                   'tokens': {'in': 5, 'out': 2, 'cached': 1, 'reasoning': 0},
                   'cost_usd': 0.00001, 'latency_ms': 900, 'error': None}

        scg._log_call(attempt, l2_code='ja', prompt_hash=b'h' * 32, raw_response=None)

        (row,) = rows
        assert row['pipeline'] == 'dual_translation' and row['task_name'] == 'dt_single_call_grade'
        assert row['model'] == FALLBACK and row['language_code'] == 'ja'
        assert row['call_role'] == llm_service.CALL_ROLE_RETRY
        assert (row['input_tokens'], row['output_tokens'], row['cost_usd']) == (5, 2, 0.00001)
        assert row['parsed_ok'] is True and row['schema_ok'] is True

        def _raise(**kw):
            raise RuntimeError('supabase down')
        monkeypatch.setattr(llm_service, '_log_llm_call', _raise)
        scg._log_call(attempt, l2_code='ja', prompt_hash=b'h' * 32, raw_response=None)  # no raise

        monkeypatch.setattr(Config, 'DT_SINGLE_CALL_LOG_LLM_CALLS', False)
        monkeypatch.setattr(llm_service, '_log_llm_call', lambda **kw: rows.append(kw))
        scg._log_call(attempt, l2_code='ja', prompt_hash=b'h' * 32, raw_response=None)
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

class TestPrompt:

    def test_request_is_the_frozen_prompt_and_schema(self, monkeypatch, logged):
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        _grade(EN_GOLD, EN_TENSE, 'en')

        call = model.calls[0]
        assert call['system'] == sc_prompts.build_system_prompt('en')
        assert 'CLEARLY WRONG to a native reader' in call['system']
        assert '"Major" does NOT require a change of meaning' in call['system']
        assert 'free translations' not in call['system']
        assert call['user'] == (
            'S1 SAME: First, you need an Arduino board.\n'
            'S2 REF: This is a small computer.\n'
            'S2 LRN: This was a small computer.\n'
            'S3 SAME: You can make many things with it.'
        )
        assert call['max_tokens'] == 600
        schema = call['schema']
        assert schema['strict'] is True
        item = schema['schema']['properties']['errors']['items']
        assert item['required'] == ['sentence', 'span', 'type', 'severity', 'explanation']
        assert item['properties']['type']['enum'] == list(sc_prompts.FROZEN_TYPE_IDS['en'])

    def test_frozen_types_match_taxonomy_v6(self):
        for l2, ids in sc_prompts.FROZEN_TYPE_IDS.items():
            assert list(ids) == TAXONOMY_V6['pairs'][l2]['subtypes']
            system = sc_prompts.build_system_prompt(l2)
            for slug in ids:
                default = TAXONOMY_V6['subtype_meta'][slug]['default_severity']
                line = next(ln for ln in system.splitlines() if ln.startswith(f'- {slug}'))
                assert line.endswith(f'(usually {default})')

    def test_free_translation_paragraph_is_opt_in_and_recorded(self, monkeypatch, logged):
        monkeypatch.setattr(Config, 'DT_SINGLE_CALL_FREE_TRANSLATION', True)
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        system = model.calls[0]['system']
        assert system.startswith(sc_prompts.build_system_prompt('en'))
        assert 'IMPORTANT - free translations.' in system and 'natural English?' in system
        assert contract['grader_trace']['single_call']['prompt_variant'] == 'p1_expl_mit'
        assert contract['grading_assets'][0]['prompt_variant'] == 'p1_expl_mit'

    def test_prompt_is_byte_identical_to_the_validated_track_b_harness(self):
        """Drift guard: the production prompt, schema and sentence pairing must be
        exactly what data/eval/dt_decision_2026-11-14/track_b measured."""
        track_b = os.path.join(_REPO, 'data', 'eval', 'dt_decision_2026-11-14', 'track_b')
        if not os.path.isfile(os.path.join(track_b, 'common.py')):
            pytest.skip('Track B harness not present')
        saved_path = list(sys.path)
        sys.path.insert(0, track_b)
        saved_cwd = os.getcwd()
        try:
            try:
                import common as track_b_common
            except Exception as exc:  # harness deps (Sept sentence module, data files) missing
                pytest.skip(f'Track B harness not importable: {exc}')
            for l2 in ('en', 'zh', 'ja'):
                assert sc_prompts.build_system_prompt(l2) == track_b_common.system_p1(l2, 'expl')
                assert sc_prompts.response_schema(l2) == track_b_common.schema(l2, 'p1_expl')
                for item in track_b_common.load_set('gold', l2)[:10]:
                    pairs = build_sentence_pairs(item['reference'], item['reproduction']).pairs
                    assert sc_prompts.build_user_prompt(pairs) == track_b_common.user_p1(item, l2)
            assert sc_prompts.MAX_TOKENS == track_b_common.MAX_TOKENS['p1_expl']
        finally:
            os.chdir(saved_cwd)
            sys.path[:] = saved_path  # the harness also appends its own dirs
            sys.modules.pop('common', None)
            sys.modules.pop('sentences', None)


# ---------------------------------------------------------------------------
# Persistence (routes)
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table):
        self._db, self._table = db, table

    def select(self, columns='*', **k):
        self._db.calls.append((self._table, 'select', columns))
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, payload):
        if self._table == self._db.fail_table:
            raise RuntimeError(f'relation "{self._table}" does not exist')
        self._db.calls.append((self._table, 'insert', payload))
        return self

    def update(self, payload):
        self._db.calls.append((self._table, 'update', payload))
        return self

    def execute(self):
        return _Result(self._db.data.get(self._table, []))


class _DB:
    def __init__(self, data=None, fail_table=None):
        self.data, self.fail_table, self.calls = data or {}, fail_table, []

    def table(self, name):
        return _Query(self, name)

    def inserts(self, table):
        return [p for n, m, p in self.calls if n == table and m == 'insert']


_ASSET_ERROR_COLUMNS = ('sentence_index', 'model_severity', 'model_note', 'span_source', 'correction_source')


class TestPersistence:

    def _contract(self, monkeypatch):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'verb_form_tense', 'minor', 'Use "is" for a present fact.'),
        ]}})
        return _grade(EN_GOLD, EN_TENSE, 'en')

    def test_flag_off_writes_no_new_column_and_no_call_row(self, monkeypatch, logged):
        contract = self._contract(monkeypatch)
        assets = contract.pop('grading_assets')
        db = _DB()

        dt_routes._persist_grade(db, 5, EN_TENSE, None, contract)
        dt_routes._persist_grading_assets(db, 5, assets)

        (rows,) = db.inserts('dt_error_instance')
        assert not set(rows[0]) & set(_ASSET_ERROR_COLUMNS)
        assert 'explanation_parts' not in rows[0]
        assert db.inserts('dt_grading_call') == []
        # The trace on dt_grade still names the model, prompt version and usage.
        (grade,) = db.inserts('dt_grade')
        assert grade['grader_trace']['single_call']['model'] == PRIMARY
        assert grade['scores'] == {'accuracy': 3, 'fidelity': 4, 'understandability': 4}

    def test_flag_on_writes_the_per_error_fields_and_the_call_row(self, monkeypatch, logged):
        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        contract = self._contract(monkeypatch)
        assets = contract.pop('grading_assets')
        db = _DB()

        dt_routes._persist_grade(db, 5, EN_TENSE, None, contract)
        dt_routes._persist_grading_assets(db, 5, assets)

        (rows,) = db.inserts('dt_error_instance')
        row = rows[0]
        assert row['sentence_index'] == 1
        assert row['model_severity'] == 'minor' and row['severity'] == 'major'
        assert row['model_note'] == 'Use "is" for a present fact.'
        assert row['span_source'] == 'model' and row['correction_source'] == 'aligned_diff'
        assert 'explanation_parts' not in row and 'taxonomy_version' not in row
        (call_rows,) = db.inserts('dt_grading_call')
        (call_row,) = call_rows
        assert call_row['submission_id'] == 5
        assert call_row['model_slug'] == PRIMARY and call_row['status'] == 'ok'
        assert call_row['prompt_version'] == sc_prompts.PROMPT_VERSION
        assert call_row['response']['errors'][0]['span'] == 'was'

    def test_flag_on_tolerates_errors_from_the_old_flows(self, monkeypatch):
        """v1/v2 errors carry none of the new keys: the insert simply omits them."""
        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        old_error = {
            'span_reproduction': [0, 1], 'span_reference': [0, 1], 'category': 'lexical',
            'subtype': 'x', 'source': 'interlingual', 'severity': 'minor',
            'learner_form': 'a', 'corrected_form': 'b', 'explanation': 'why',
            'confidence': 0.9, 'is_mistake': False,
        }
        db = _DB()

        dt_routes._persist_grade(db, 5, 'repro', None, {
            'scores': {}, 'overall_band': 3, 'diff': [], 'grader_trace': {}, 'errors': [old_error],
        })
        dt_routes._persist_grading_assets(db, 5, None)

        (rows,) = db.inserts('dt_error_instance')
        assert not set(rows[0]) & set(_ASSET_ERROR_COLUMNS)
        assert db.inserts('dt_grading_call') == []

    def test_cached_select_names_the_new_columns_only_when_the_flag_is_on(self, monkeypatch):
        data = {'dt_grade': [{'scores': {}, 'overall_band': 3, 'diff': [], 'grader_trace': {}}]}

        db = _DB(data)
        dt_routes._cached_grade(db, 5)
        (off,) = [p for n, m, p in db.calls if n == 'dt_error_instance' and m == 'select']
        assert 'sentence_index' not in off

        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        db = _DB(data)
        dt_routes._cached_grade(db, 5)
        (on,) = [p for n, m, p in db.calls if n == 'dt_error_instance' and m == 'select']
        assert all(col in on for col in _ASSET_ERROR_COLUMNS)

    def test_call_row_failure_is_swallowed(self, monkeypatch, logged):
        """E.g. the flag was turned on before the migration was applied: the grade
        is already stored, and a missing dt_grading_call must not fail the request."""
        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        assets = self._contract(monkeypatch)['grading_assets']
        db = _DB(fail_table='dt_grading_call')

        dt_routes._persist_grading_assets(db, 5, assets)  # no raise

        assert db.inserts('dt_grading_call') == []

    def test_submit_stores_assets_and_never_returns_them(self, client, auth_headers, monkeypatch, logged):
        contract = self._contract(monkeypatch)
        stored = []
        monkeypatch.setattr(dt_routes, '_get_submission', lambda db, sid: {
            'id': 5, 'user_id': 'test-user-id-123', 'passage_id': 9, 'l1_language_id': 2})
        monkeypatch.setattr(dt_routes, '_cached_grade', lambda db, sid: None)
        monkeypatch.setattr(dt_routes, '_get_passage', lambda db, pid: {
            'id': 9, 'l2_text': EN_GOLD, 'l2_language_id': 2, 'age_tier': 3, 'status': 'active'})
        monkeypatch.setattr(dt_routes, '_tokens_used_today', lambda db, uid: 0)
        monkeypatch.setattr(dt_routes, 'grade_submission', lambda db, **kw: contract)
        monkeypatch.setattr(dt_routes, '_persist_grade', lambda db, sid, repro, key, c: stored.append(('grade', c)))
        monkeypatch.setattr(dt_routes, '_persist_grading_assets',
                            lambda db, sid, assets: stored.append(('assets', sid, assets)))
        monkeypatch.setattr(dt_routes, 'credit_study_time', lambda *a, **k: None)

        resp = client.post('/api/dual-translation/5/submit', headers=auth_headers,
                           json={'reproduction': EN_TENSE})

        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert 'grading_assets' not in json.dumps(body)
        assert stored[0][0] == 'grade' and 'grading_assets' not in stored[0][1]
        assert stored[1][0] == 'assets' and stored[1][1] == 5
        assert stored[1][2][0]['model_slug'] == PRIMARY
