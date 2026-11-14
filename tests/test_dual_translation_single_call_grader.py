"""Unit tests for the DT single-call generative grader (ADR-044).

DB-free and OpenRouter-free, in the style of test_dual_translation_grader_cascade.py:
the model boundary (``single_call_grader.call_structured``), the observability
boundary (``single_call_grader._log_call``) and the rubric/taxonomy loaders are
monkeypatched. The taxonomy and rubric are the real v6 seeds, parsed offline from
their migration files (the same extraction the seed tests use), because the
hardcoded type list is only valid under taxonomy v6.
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
    monkeypatch.setattr(Config, 'DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE', False)
    monkeypatch.setitem(dt_routes._asset_columns_state, 'unavailable_until', 0.0)
    monkeypatch.setitem(dt_routes._asset_columns_state, 'logged', False)
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


def _entry(sentence, quote, type_, severity, explanation='Use the reference form here instead.',
           *, ref='', confidence='high', source='intralingual'):
    """One model error entry in the v2 response shape."""
    return {'sentence': sentence, 'learner_quote': quote, 'reference_quote': ref, 'type': type_,
            'severity': severity, 'confidence': confidence, 'source': source,
            'explanation': explanation}


def _payload(errors, *, naturalness=None, range_=None):
    """A full v2 response. A judgment is (band, evidence quote); None leaves it out."""
    payload = {'errors': errors}
    for dim, judgment in (('naturalness', naturalness), ('range', range_)):
        if judgment is not None:
            payload[dim] = {'band': judgment[0], 'evidence': judgment[1]}
    return payload


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
    'explanation_parts', 'explanation_source', 'confidence_label', 'span_source',
    'correction_source', 'sentence_index', 'model_severity', 'model_note',
}


# ---------------------------------------------------------------------------
# Happy path, per language
# ---------------------------------------------------------------------------

class TestHappyPath:

    def test_en_error_is_decoded_into_the_contract_shape(self, monkeypatch, logged):
        _no_other_flow(monkeypatch)
        model = _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'verb_form_tense', 'minor', '这里应该用“is”，不是“was”。', ref='is'),
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
        assert err['span_source'] == 'exact'
        assert err['correction_source'] == 'model_quote'
        # en + gpt-6-luna -> the taxonomy default severity (major) is applied;
        # the model's own value is kept alongside.
        assert err['severity'] == 'major'
        assert err['model_severity'] == 'minor'
        assert contract['scores']['accuracy'] == 3
        assert contract['grader_trace']['single_call']['severity_rule'] == 'prior'

    def test_zh_uses_the_models_own_severity(self, monkeypatch, logged):
        _no_other_flow(monkeypatch)
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(1, '一个', 'measure_word', 'major', '衣服 takes the classifier 件, so write 一件.', ref='一件'),
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
            _entry(1, 'は', 'case_particle', 'major', 'Use が to mark the included parts.', ref='が'),
        ]}})

        contract = _grade(JA_GOLD, JA_PARTICLE, 'ja')

        (err,) = contract['errors']
        assert err['learner_form'] == 'は' and err['corrected_form'] == 'が'
        assert JA_GOLD[err['span_reference'][0]:err['span_reference'][1]] == 'が'
        assert err['severity'] == 'major'
        assert contract['grader_trace']['single_call']['severity_rule'] == 'model'
        # No judgments in this response -> only the derived dimensions.
        assert contract['scores'] == {'accuracy': 3, 'fidelity': 4, 'understandability': 4}


# ---------------------------------------------------------------------------
# Item 1 — all five rubric dimensions
# ---------------------------------------------------------------------------

class TestFiveDimensions:

    def test_all_five_dimensions_are_scored_and_weighed(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: _payload(
            [], naturalness=(4, 'a little computer'), range_=(4, 'many things with it'))})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en')

        assert contract['scores'] == {
            'accuracy': 4, 'fidelity': 4, 'understandability': 4, 'naturalness': 4, 'range': 4,
        }
        assert contract['overall_band'] == 4
        sc = contract['grader_trace']['single_call']
        assert sc['unscored_dimensions'] == []
        assert sc['judgments']['naturalness']['status'] == 'ok'
        start, end = sc['judgments']['naturalness']['evidence_span']
        assert EN_SYNONYM[start:end] == 'a little computer'

    def test_the_judged_bands_move_the_overall_band(self, monkeypatch, logged):
        """Same error list, different judgments -> a different overall band, so the
        overall really is computed over all five (v6 weights .3/.15/.3/.1/.15)."""
        _use_model(monkeypatch, {PRIMARY: _payload(
            [], naturalness=(1, 'a little computer'), range_=(1, 'many things with it'))})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en')

        assert contract['scores']['naturalness'] == 1 and contract['scores']['range'] == 1
        assert contract['overall_band'] == 3  # (4*.3 + 4*.15 + 4*.3 + 1*.1 + 1*.15) = 3.25

    def test_judgment_without_real_evidence_is_left_out_not_defaulted(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: _payload(
            [], naturalness=(2, 'words that are not in the learner text'), range_=(4, 'many things with it'))})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en')

        assert 'naturalness' not in contract['scores'] and contract['scores']['range'] == 4
        sc = contract['grader_trace']['single_call']
        assert sc['unscored_dimensions'] == ['naturalness']
        assert sc['judgments']['naturalness'] == {'status': 'no_evidence', 'band': 2}

    @pytest.mark.parametrize('band', [0, 5, '4', True, None, 3.5])
    def test_judgment_with_an_unusable_band_is_left_out(self, monkeypatch, logged, band):
        payload = _payload([], range_=(4, 'many things with it'))
        payload['naturalness'] = {'band': band, 'evidence': 'a little computer'}
        _use_model(monkeypatch, {PRIMARY: payload})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en')

        assert set(contract['scores']) == {'accuracy', 'fidelity', 'understandability', 'range'}
        assert contract['grader_trace']['single_call']['judgments']['naturalness']['status'] == 'bad_band'

    def test_missing_judgments_do_not_fail_the_grade(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en')

        assert set(contract['scores']) == {'accuracy', 'fidelity', 'understandability'}
        assert contract['grader_trace']['single_call']['unscored_dimensions'] == ['naturalness', 'range']
        assert contract['overall_band'] == 4 and contract['provisional'] is False

    def test_lowered_naturalness_whose_evidence_is_a_scored_grammar_error_is_discarded(self, monkeypatch, logged):
        """The tense error is already scored on accuracy; quoting it as the reason
        for naturalness 3 would count it twice."""
        _use_model(monkeypatch, {PRIMARY: _payload(
            [_entry(2, 'was', 'verb_form_tense', 'major', ref='is')],
            naturalness=(3, 'This was a small computer'), range_=(4, 'many things with it'))})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert 'naturalness' not in contract['scores']
        judgment = contract['grader_trace']['single_call']['judgments']['naturalness']
        assert judgment['status'] == 'evidence_is_scored_error' and judgment['band'] == 3

    def test_lowered_naturalness_on_a_naturalness_type_error_stands(self, monkeypatch, logged):
        assert TAXONOMY_V6['subtype_meta']['collocation']['dimension'] == 'naturalness'
        _use_model(monkeypatch, {PRIMARY: _payload(
            [_entry(2, 'little', 'collocation', 'minor', ref='small')],
            naturalness=(3, 'a little computer'), range_=(4, 'many things with it'))})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en')

        assert contract['scores']['naturalness'] == 3

    def test_lowered_naturalness_with_independent_evidence_stands(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: _payload(
            [_entry(2, 'was', 'verb_form_tense', 'major', ref='is')],
            naturalness=(3, 'many things with it'), range_=(4, 'Arduino board'))})

        assert _grade(EN_GOLD, EN_TENSE, 'en')['scores']['naturalness'] == 3

    def test_band_descriptors_for_the_age_tier_are_in_the_prompt(self, monkeypatch, logged):
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        _grade(EN_GOLD, EN_SYNONYM, 'en')  # age_tier=3

        system = model.calls[0]['system']
        descriptor = RUBRIC_V6['band_descriptors']['3']['naturalness']['en']['4']
        assert 'Band descriptors:' in system and descriptor in system
        assert RUBRIC_V6['band_descriptors']['3']['range']['en']['2'] in system
        # ... and they come after everything that is shared across age tiers.
        assert system.startswith(sc_prompts.build_system_prompt('en'))

    def test_judged_dimensions_match_the_v2_contract(self):
        from services.dual_translation import prompts, scoring
        assert sc_prompts.JUDGED_DIMENSIONS == prompts.JUDGE_DIMENSIONS
        assert set(scoring.DERIVED_DIMENSIONS) | set(sc_prompts.JUDGED_DIMENSIONS) == set(tier0.RUBRIC_DIMENSIONS)
        assert sc_prompts.SOURCES == prompts.SOURCE_ENUM


# ---------------------------------------------------------------------------
# Item 2 — confidence and source are model judgments
# ---------------------------------------------------------------------------

class TestConfidenceAndSource:

    @pytest.mark.parametrize('label,value', [('high', 0.9), ('medium', 0.6)])
    def test_confidence_label_is_mapped_to_a_number(self, monkeypatch, logged, label, value):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'verb_form_tense', 'major', ref='is', confidence=label),
        ]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        (err,) = contract['errors']
        assert err['confidence'] == value and err['confidence_label'] == label
        row = contract['grader_trace']['single_call']['per_error'][0]
        assert (row['confidence'], row['confidence_label']) == (value, label)

    def test_source_is_the_models_judgment(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'verb_form_tense', 'major', ref='is', source='interlingual'),
        ]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert contract['errors'][0]['source'] == 'interlingual'
        assert contract['grader_trace']['single_call']['defaulted'] == {'confidence': 0, 'source': 0}

    def test_low_confidence_entry_is_withheld_counted_and_not_scored(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'little', 'word_choice', 'minor', ref='small', confidence='low'),
        ]}})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en')

        assert contract['errors'] == [] and contract['scores']['fidelity'] == 4
        sc = contract['grader_trace']['single_call']
        assert sc['dropped']['low_confidence'] == 1 and sc['errors_raw'] == 1 and sc['errors_kept'] == 0
        assert sc['withheld_low_confidence'] == [{
            'sentence': 2, 'learner_quote': 'little', 'reference_quote': 'small',
            'type': 'word_choice', 'severity': 'minor',
        }]

    def test_low_confidence_entries_can_be_kept_by_config(self, monkeypatch, logged):
        monkeypatch.setattr(Config, 'DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE', True)
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'little', 'word_choice', 'minor', ref='small', confidence='low'),
        ]}})

        (err,) = _grade(EN_GOLD, EN_SYNONYM, 'en')['errors']

        assert err['confidence'] == 0.3 and err['confidence_label'] == 'low'

    def test_numeric_confidence_from_a_model_that_ignored_the_enum_is_bucketed(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'verb_form_tense', 'major', ref='is', confidence=0.8),
        ]}})

        (err,) = _grade(EN_GOLD, EN_TENSE, 'en')['errors']

        assert err['confidence'] == 0.8 and err['confidence_label'] == 'high'

    def test_missing_confidence_and_source_fall_back_and_are_counted(self, monkeypatch, logged):
        entry = _entry(2, 'was', 'verb_form_tense', 'major', ref='is')
        entry['confidence'], entry['source'] = 'very', 'L1'
        _use_model(monkeypatch, {PRIMARY: {'errors': [entry]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        (err,) = contract['errors']
        assert err['confidence'] == scg.DEFAULT_CONFIDENCE and err['confidence_label'] is None
        assert err['source'] == scg.DEFAULT_SOURCE
        assert contract['grader_trace']['single_call']['defaulted'] == {'confidence': 1, 'source': 1}


# ---------------------------------------------------------------------------
# Item 3 — the model's explanation is shown (L1, guarded, template fallback)
# ---------------------------------------------------------------------------

class TestShownExplanation:

    def test_valid_l1_explanation_is_the_application_layer_and_the_template_is_intact(self, monkeypatch, logged):
        note = '这里说的是现在的事实，应该用“is”，不是“was”。'
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(2, 'was', 'verb_form_tense', 'major', note, ref='is')]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en', l1='zh')

        (err,) = contract['errors']
        template = TAXONOMY_V6['templates']['verb_form_tense']['zh']
        # ADR-015: `explanation` is still exactly the eager template text.
        assert err['explanation'] == template.format(learner_form='was', corrected_form='is')
        assert note not in err['explanation']
        # ... and the model's text sits where the results UI renders the
        # this-sentence layer (static/js/dual_translation.js buildExplanation).
        assert err['explanation_parts'] == {'rule': err['explanation'], 'application': note}
        assert err['explanation_source'] == 'model' and err['model_note'] == note
        sc = contract['grader_trace']['single_call']
        assert sc['explanation_sources'] == {'model': 1, 'template': 0}
        assert sc['per_error'][0]['explanation_source'] == 'model'
        assert sc['per_error'][0]['explanation_rejected'] is None

    @pytest.mark.parametrize('text,reason', [
        (None, 'missing'),
        ('   ', 'missing'),
        ('“was”' + '很' * 240, 'too_long'),
        ('应该用“is”。\n不是“was”。', 'multi_paragraph'),
        ('这里“was”只能得 3/4 分。', 'score_pattern'),
        ('这里的时态不对，请再想一想应该用哪个词。', 'no_form_mention'),
        ('Use "is" for a present fact, not "was".', 'wrong_language'),
    ])
    def test_rejected_explanation_falls_back_to_the_template(self, monkeypatch, logged, text, reason):
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(2, 'was', 'verb_form_tense', 'major', text, ref='is')]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en', l1='zh')

        (err,) = contract['errors']  # a rejected explanation never drops the error
        assert err['explanation_parts'] == {'rule': err['explanation'], 'application': None}
        assert err['explanation_source'] == 'template' and err['model_note'] is None
        sc = contract['grader_trace']['single_call']
        assert sc['explanation_rejections'] == {reason: 1}
        assert sc['per_error'][0]['explanation_rejected'] == reason

    def test_rejected_text_is_still_kept_capped_in_the_trace(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(2, 'was', 'verb_form_tense', 'major', 'y' * 500, ref='is')]}})

        raw = _grade(EN_GOLD, EN_TENSE, 'en')['grader_trace']['single_call']['per_error'][0]['model_explanation']

        assert raw == 'y' * scg.RAW_FIELD_CAP

    def test_guard_is_the_explainers_own(self):
        from services.dual_translation import explainer
        ok = '「部品は」ではなく「部品が」を使います。'
        assert scg._validate_explanation(ok, '部品は', '部品が', 'ja') == (ok, None)
        assert explainer._validated_application(ok, '部品は', '部品が') == ok
        # trimmed, like the Explainer's
        assert scg._validate_explanation('  Use "is" here.  ', 'was', 'is', 'en') == ('Use "is" here.', None)

    @pytest.mark.parametrize('l1,text,wrong', [
        ('en', 'Use 一件 for clothes, not 一个.', False),
        ('en', '衣服要用“一件”，不能用“一个”。', True),
        ('zh', '衣服要用“一件”，不能用“一个”。', False),
        ('zh', '「一个」ではなく「一件」を使います。', True),
        ('ja', '「部品は」ではなく「部品が」を使います。', False),
        ('ja', '这里应该用“部品が”，不能用“部品は”。', True),
        ('ko', 'anything goes for an L1 that is not checked 部品は', False),
    ])
    def test_wrong_language_check(self, l1, text, wrong):
        forms = ('一个', '一件') if '一' in text else ('部品は', '部品が')
        assert scg._wrong_language(text, l1, forms) is wrong

    def test_prompt_asks_for_the_learners_l1(self, monkeypatch, logged):
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        _grade(JA_GOLD, JA_PARTICLE, 'ja', l1='zh')

        user = model.calls[0]['user']
        assert user.splitlines()[0] == "Learner's L1: Chinese (Mandarin, simplified)."
        assert user.splitlines()[-1].startswith('Write every explanation in Chinese (Mandarin, simplified)')
        assert "WRITTEN IN THE LEARNER'S L1" in model.calls[0]['system']

    def test_opt_in_explainer_call_takes_precedence(self, monkeypatch, logged):
        from services.dual_translation import explainer
        monkeypatch.setattr(Config, 'DT_SINGLE_CALL_EXPLAINER', True)

        def _fake_explainer(db, *, errors, **kwargs):
            for e in errors:
                e['explanation_parts'] = {'rule': e['explanation'], 'application': 'from the explainer: was'}
            return errors, 10, 5, None
        monkeypatch.setattr(explainer, 'attach_explanations', _fake_explainer)
        note = '应该用“is”，不是“was”。'
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(2, 'was', 'verb_form_tense', 'major', note, ref='is')]}})

        (err,) = _grade(EN_GOLD, EN_TENSE, 'en', l1='zh')['errors']

        assert err['explanation_source'] == 'explainer'
        assert err['explanation_parts']['application'] == 'from the explainer: was'


class TestMeaningInversion:

    def test_inversion_is_critical_whatever_the_severity_rule(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(3, 'without', 'meaning_inversion', 'critical', 'This reverses the meaning.', ref='with'),
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
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(3, 'without', 'word_choice', 'critical', ref='with')]}})

        (err,) = _grade(EN_GOLD, EN_INVERTED, 'en')['errors']

        assert TAXONOMY_V6['subtype_meta']['word_choice']['default_severity'] == 'minor'
        assert err['severity'] == 'critical'


class TestCleanSubmission:

    def test_no_errors_is_full_marks(self, monkeypatch, logged):
        _no_other_flow(monkeypatch)
        _use_model(monkeypatch, {PRIMARY: _payload(
            [], naturalness=(4, 'a little computer'), range_=(4, 'many things with it'))})

        contract = _grade(EN_GOLD, EN_SYNONYM, 'en')

        assert contract['errors'] == []
        assert set(contract['scores'].values()) == {4} and len(contract['scores']) == 5
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

    def test_taxonomy_without_the_hardcoded_types_skips_the_call(self, monkeypatch, logged):
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
# Item 4 — span location ladder
# ---------------------------------------------------------------------------

def _one(monkeypatch, gold, repro, l2, entry):
    _use_model(monkeypatch, {PRIMARY: {'errors': [entry]}})
    contract = _grade(gold, repro, l2)
    return contract, contract['grader_trace']['single_call']


class TestSpanLocation:

    def test_exact_quote_in_the_named_sentence(self, monkeypatch, logged):
        contract, sc = _one(monkeypatch, EN_GOLD, EN_TENSE, 'en',
                            _entry(2, 'was', 'verb_form_tense', 'major', ref='is'))

        (err,) = contract['errors']
        assert err['span_source'] == 'exact' and err['learner_form'] == 'was'
        assert sc['span_resolution'] == {'exact': 1, 'normalised': 0, 'fuzzy': 0, 'diff_hunk': 0, 'sentence': 0}
        assert sc['correction_resolution'] == {'model_quote': 1, 'aligned_diff': 0, 'reference_sentence': 0}

    def test_repeated_short_quote_resolves_to_the_changed_occurrence(self, monkeypatch, logged):
        gold = 'The cat saw the dog near the door.'
        repro = 'The cat saw the dog near a door.'.replace('saw the dog', 'saw a dog').replace('near a door', 'near the door')
        assert repro == 'The cat saw a dog near the door.'
        contract, _ = _one(monkeypatch, gold, repro, 'en',
                           _entry(1, 'a', 'article_determiner', 'minor', ref='the'))

        (err,) = contract['errors']
        assert repro[err['span_reproduction'][0]:err['span_reproduction'][1]] == 'a'
        assert err['span_reproduction'][0] == repro.index('a dog')  # not the "a" inside "cat"/"saw"
        # "the" occurs three times in the reference; the changed one is picked.
        assert err['span_reference'][0] == gold.index('the dog')
        assert err['correction_source'] == 'model_quote'

    @pytest.mark.parametrize('quote', ['WAS A SMALL', 'was a small.', 'was  a small'.replace('  ', ' ') + '!'])
    def test_normalised_match_case_and_punctuation(self, monkeypatch, logged, quote):
        contract, sc = _one(monkeypatch, EN_GOLD, EN_TENSE, 'en',
                            _entry(2, quote, 'verb_form_tense', 'major', ref='is a small'))

        (err,) = contract['errors']
        assert err['span_source'] == 'normalised'
        assert err['learner_form'].lower().startswith('was a small')
        assert EN_TENSE[err['span_reproduction'][0]:err['span_reproduction'][1]] == err['learner_form']
        assert sc['span_resolution']['normalised'] == 1

    def test_normalised_match_full_width_and_kana(self, monkeypatch, logged):
        gold = 'キットがあります。これはとても便利です。'
        repro = 'キットはあります。これはとても便利です。'
        contract, _ = _one(monkeypatch, gold, repro, 'ja',
                           _entry(1, 'きっとは', 'case_particle', 'major', ref='キットが'))

        (err,) = contract['errors']
        assert err['span_source'] == 'normalised' and err['learner_form'] == 'キットは'
        assert err['corrected_form'] == 'キットが'

    def test_exact_quote_found_in_another_sentence(self, monkeypatch, logged):
        contract, sc = _one(monkeypatch, EN_GOLD, EN_TENSE, 'en',
                            _entry(1, 'was', 'verb_form_tense', 'major', ref='is'))

        (err,) = contract['errors']
        assert err['span_source'] == 'exact'
        assert err['sentence_index'] == 1  # where the text actually is, not what the model said
        assert err['corrected_form'] == 'is'
        assert sc['span_other_sentence'] == 1

    def test_fuzzy_match_inside_the_named_sentence(self, monkeypatch, logged):
        """The model 'corrected' a typo while quoting: not verbatim, not normalisable."""
        gold = 'She has lived in London for ten years. It is big.'
        repro = 'She has livd in Londn since ten years. It is big.'
        contract, sc = _one(monkeypatch, gold, repro, 'en',
                            _entry(1, 'in London since ten years', 'preposition', 'major', ref='for ten years'))

        (err,) = contract['errors']
        assert err['span_source'] == 'fuzzy'
        assert err['learner_form'] == 'in Londn since ten years'
        assert repro[err['span_reproduction'][0]:err['span_reproduction'][1]] == err['learner_form']
        assert err['corrected_form'] == 'for ten years' and err['correction_source'] == 'model_quote'
        assert sc['span_resolution']['fuzzy'] == 1 and sc['span_resolution']['sentence'] == 0

    def test_fuzzy_match_never_leaves_the_named_sentence(self):
        text = 'Alpha beta gamma. Delta epsilon zeta.'
        first_end = text.index('Delta')
        assert scg._fuzzy_find(grader_cascade, text, 0, first_end, 'Delta epsilom zeta', 'en') is None
        hit = scg._fuzzy_find(grader_cascade, text, first_end, len(text), 'Delta epsilom zeta', 'en')
        assert text[hit[0]:hit[1]] == 'Delta epsilon zeta'

    def test_diff_hunk_when_the_quote_cannot_be_matched(self, monkeypatch, logged):
        """The quote is a paraphrase of the learner text (no exact, normalised or
        fuzzy match), but it shares a word with the one changed region."""
        gold = 'We walked to the old library after lunch. It was quiet.'
        repro = 'We walked to the ancient library after lunch. It was quiet.'
        contract, sc = _one(monkeypatch, gold, repro, 'en',
                            _entry(1, 'the word ancient is odd', 'word_choice', 'minor', ref='old'))

        (err,) = contract['errors']
        assert err['span_source'] == 'diff_hunk' and err['learner_form'] == 'ancient'
        assert err['corrected_form'] == 'old' and err['correction_source'] == 'model_quote'
        assert sc['span_resolution']['diff_hunk'] == 1 and sc['span_resolution']['sentence'] == 0

    def test_diff_hunk_for_a_dropped_word_with_an_empty_learner_quote(self, monkeypatch, logged):
        gold = 'It is not a toy. It is a tool.'
        repro = 'It is a toy. It is a tool.'
        contract, _ = _one(monkeypatch, gold, repro, 'en',
                           _entry(1, '', 'meaning_inversion', 'critical', ref='not'))

        (err,) = contract['errors']
        assert err['span_source'] == 'diff_hunk'
        start, end = err['span_reproduction']
        assert start == end and err['learner_form'] == ''  # a point where the word is missing
        assert err['corrected_form'] == 'not' and gold[err['span_reference'][0]:err['span_reference'][1]] == 'not'
        assert err['sentence_index'] == 0

    def test_diff_hunk_picks_the_hunk_that_overlaps_the_quote(self, monkeypatch, logged):
        gold = 'The red car stopped near the tall tree. End.'
        repro = 'The blue car stopped near the short tree. End.'
        contract, _ = _one(monkeypatch, gold, repro, 'en',
                           _entry(1, 'tree is short here', 'word_choice', 'major', ref='the tall one'))

        (err,) = contract['errors']
        assert (err['span_source'], err['learner_form']) == ('diff_hunk', 'short')
        assert err['corrected_form'] == 'tall' and err['correction_source'] == 'aligned_diff'

    def test_whole_sentence_is_the_last_resort_and_says_so(self, monkeypatch, logged):
        """Nothing matches and the sentence has no changed region the quote overlaps."""
        contract, sc = _one(monkeypatch, EN_GOLD, EN_TENSE, 'en',
                            _entry(2, 'zzz qqq xxx', 'verb_form_tense', 'major', ref='yyy'))

        (err,) = contract['errors']
        assert err['span_source'] == 'sentence'
        assert err['learner_form'] == 'This was a small computer.'
        assert EN_TENSE[err['span_reproduction'][0]:err['span_reproduction'][1]] == err['learner_form']
        assert err['corrected_form'] == 'This is a small computer.'
        assert err['correction_source'] == 'reference_sentence'
        assert sc['span_resolution'] == {'exact': 0, 'normalised': 0, 'fuzzy': 0, 'diff_hunk': 0, 'sentence': 1}
        assert sc['dropped_total'] == 0

    def test_unlocatable_quote_with_no_usable_sentence_is_dropped_and_counted(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(99, 'text that is nowhere', 'word_choice', 'major', ref='x'),
            _entry(2, 'was', 'verb_form_tense', 'major', ref='is'),
        ]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert [e['learner_form'] for e in contract['errors']] == ['was']
        sc = contract['grader_trace']['single_call']
        assert sc['errors_raw'] == 2 and sc['errors_kept'] == 1
        assert sc['dropped'] == {'invalid_entry': 0, 'unknown_type': 0, 'low_confidence': 0,
                                 'span_unlocatable': 1, 'decode_rejected': 0}
        assert sc['dropped_total'] == 1
        assert contract['scores']['accuracy'] == 3  # only the kept error is scored

    def test_every_resolution_path_is_counted_in_one_trace(self, monkeypatch, logged):
        gold = 'This is a small computer. We walked to the old library. She has lived here for ten years. Stop.'
        repro = 'This was a small computer. We walked to the ancient library. She has livd here since ten years. Go.'
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(1, 'was', 'verb_form_tense', 'major', ref='is'),
            _entry(1, 'SMALL COMPUTER', 'orthography', 'minor', ref='small computer.'),
            _entry(3, 'lived here since ten years', 'preposition', 'major', ref='for ten years'),
            _entry(2, 'the word ancient is odd', 'word_choice', 'minor', ref='old'),
            _entry(4, 'qqq zzz', 'word_choice', 'major', ref='www'),
        ]}})

        sc = _grade(gold, repro, 'en')['grader_trace']['single_call']

        assert sc['span_resolution'] == {'exact': 1, 'normalised': 1, 'fuzzy': 1, 'diff_hunk': 1, 'sentence': 1}
        assert [row['span_source'] for row in sc['per_error']] == [
            'exact', 'normalised', 'fuzzy', 'diff_hunk', 'sentence']


class TestReferenceSide:

    def test_model_reference_quote_is_the_correction(self, monkeypatch, logged):
        gold = 'It is not a toy. It is a tool.'
        repro = 'It is a toy. It is a tool.'
        contract, _ = _one(monkeypatch, gold, repro, 'en',
                           _entry(1, 'is a', 'meaning_inversion', 'critical', ref='is not a'))

        (err,) = contract['errors']
        assert (err['learner_form'], err['corrected_form']) == ('is a', 'is not a')
        assert gold[err['span_reference'][0]:err['span_reference'][1]] == 'is not a'
        assert err['correction_source'] == 'model_quote'

    def test_missing_reference_quote_falls_back_to_the_alignment(self, monkeypatch, logged):
        gold = 'It is not a toy. It is a tool.'
        repro = 'It is a toy. It is a tool.'
        contract, _ = _one(monkeypatch, gold, repro, 'en', _entry(1, 'is', 'meaning_inversion', 'critical'))

        (err,) = contract['errors']
        assert (err['learner_form'], err['corrected_form']) == ('is', 'is not')
        assert err['correction_source'] == 'aligned_diff'

    def test_reference_quote_identical_to_the_learner_text_is_not_used(self, monkeypatch, logged):
        contract, _ = _one(monkeypatch, EN_GOLD, EN_TENSE, 'en',
                           _entry(2, 'a small', 'word_choice', 'minor', ref='a small'))

        (err,) = contract['errors']
        assert err['correction_source'] != 'model_quote'

    def test_reference_quote_that_is_the_whole_sentence_is_not_a_local_correction(self, monkeypatch, logged):
        gold = 'The weather was lovely yesterday. We stayed outside.'
        repro = 'Rain fell hard on Monday morning. We stayed outside.'
        contract, sc = _one(monkeypatch, gold, repro, 'en',
                            _entry(1, 'Rain fell hard', 'word_choice', 'major', ref='The weather was lovely yesterday.'))

        (err,) = contract['errors']
        assert err['learner_form'] == 'Rain fell hard' and err['span_source'] == 'exact'
        assert err['corrected_form'] == 'The weather was lovely yesterday.'
        assert err['correction_source'] == 'reference_sentence'
        assert sc['correction_resolution']['reference_sentence'] == 1

    def test_reference_quote_is_fuzzy_matched_too(self, monkeypatch, logged):
        contract, _ = _one(monkeypatch, EN_GOLD, EN_TENSE, 'en',
                           _entry(2, 'was a small', 'verb_form_tense', 'major', ref='is a smoll'))

        (err,) = contract['errors']
        assert err['corrected_form'] == 'is a small' and err['correction_source'] == 'model_quote'


# ---------------------------------------------------------------------------
# Item 5 — exhaustive hardcoded type list; unknown slugs handled explicitly
# ---------------------------------------------------------------------------

class TestTypeListExhaustive:
    """Fails whenever the hardcoded list and migrations/dt_taxonomy_v6_seed.sql
    diverge: a slug missing or extra for a language, a different order, an empty
    definition, or a severity hint that is not the taxonomy default."""

    def _allowed(self, l2):
        """Every subtype the taxonomy allows for this L2: its baseline list and
        every directed pair <l1>-<l2>."""
        keys = [k for k in TAXONOMY_V6['pairs'] if k == l2 or k.endswith(f'-{l2}')]
        assert l2 in keys and len(keys) >= 2
        return {k: TAXONOMY_V6['pairs'][k]['subtypes'] for k in keys}

    def test_every_taxonomy_l2_has_a_hardcoded_list(self):
        taxonomy_l2s = {k.split('-')[-1] for k in TAXONOMY_V6['pairs']}
        assert set(sc_prompts.TYPE_DEFINITIONS) == taxonomy_l2s == {'en', 'zh', 'ja'}

    @pytest.mark.parametrize('l2', ['en', 'zh', 'ja'])
    def test_no_slug_is_missing_or_extra_for_any_pair(self, l2):
        hardcoded = [row[0] for row in sc_prompts.TYPE_DEFINITIONS[l2]]
        assert len(hardcoded) == len(set(hardcoded)), 'duplicate slug in the hardcoded list'
        for pair_key, subtypes in self._allowed(l2).items():
            missing = sorted(set(subtypes) - set(hardcoded))
            extra = sorted(set(hardcoded) - set(subtypes))
            assert not missing, f'{pair_key}: taxonomy v6 slugs missing from the hardcoded list: {missing}'
            assert not extra, f'{pair_key}: hardcoded slugs that taxonomy v6 does not allow: {extra}'
            assert hardcoded == subtypes, f'{pair_key}: same slugs, different order'
        assert sc_prompts.TYPE_IDS[l2] == tuple(hardcoded)

    @pytest.mark.parametrize('l2', ['en', 'zh', 'ja'])
    def test_every_slug_has_a_definition_and_the_taxonomy_severity_hint(self, l2):
        system = sc_prompts.build_system_prompt(l2)
        for slug, native, definition, usual in sc_prompts.TYPE_DEFINITIONS[l2]:
            assert isinstance(definition, str) and len(definition.strip()) >= 20, slug
            assert definition.count('(') == definition.count(')'), f'{slug}: unbalanced definition'
            assert usual == TAXONOMY_V6['subtype_meta'][slug]['default_severity'], slug
            if l2 != 'en':
                assert native.strip(), f'{slug}: no native name'
            line = next(ln for ln in system.splitlines() if ln.startswith(f'- {slug}'))
            assert definition in line and line.endswith(f'(usually {usual})')

    def test_the_test_really_detects_divergence(self, monkeypatch):
        rows = sc_prompts.TYPE_DEFINITIONS['zh']
        monkeypatch.setitem(sc_prompts.TYPE_DEFINITIONS, 'zh', rows[:-1])
        with pytest.raises(AssertionError, match='missing from the hardcoded list'):
            self.test_no_slug_is_missing_or_extra_for_any_pair('zh')
        monkeypatch.setitem(sc_prompts.TYPE_DEFINITIONS, 'zh', rows + (('keigo', 'x', 'y' * 30, 'major'),))
        with pytest.raises(AssertionError, match='does not allow'):
            self.test_no_slug_is_missing_or_extra_for_any_pair('zh')

    def test_naturalness_types_are_the_taxonomys_naturalness_dimension(self):
        for l2, ids in sc_prompts.TYPE_IDS.items():
            mapped = {s for s in ids if TAXONOMY_V6['subtype_meta'][s]['dimension'] == 'naturalness'}
            assert mapped == {s for s in sc_prompts.NATURALNESS_TYPES if s in ids}

    def test_schema_enum_is_the_hardcoded_list(self):
        for l2 in ('en', 'zh', 'ja'):
            item = sc_prompts.response_schema(l2)['schema']['properties']['errors']['items']
            assert item['properties']['type']['enum'] == list(sc_prompts.TYPE_IDS[l2])

    def test_taxonomy_with_a_slug_the_list_lacks_skips_the_call(self, monkeypatch, logged):
        """Run time: a loaded taxonomy that allows a slug the hardcoded list does
        not have (the list is no longer exhaustive) must not be graded with it."""
        pairs = dict(TAXONOMY_V6['pairs'])
        pairs['zh-en'] = {'subtypes': TAXONOMY_V6['pairs']['en']['subtypes'] + ['brand_new_type']}
        monkeypatch.setattr(grader_cascade, 'get_active_taxonomy', lambda db: dict(TAXONOMY_V6, pairs=pairs))
        v2_calls = _sentinel_v2(monkeypatch)
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en', framework_v2=True)

        assert model.calls == [] and len(v2_calls) == 1
        reason = contract['grader_trace']['single_call']['reason']
        assert reason.startswith('taxonomy mismatch') and 'brand_new_type' in reason


class TestUnknownType:

    def test_unknown_slug_is_dropped_counted_and_logged(self, monkeypatch, logged, caplog):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'not_a_type', 'major', ref='is'),
            _entry(2, 'was', None, 'major', ref='is'),
            _entry(2, 'was', 'keigo', 'major', ref='is'),  # a real slug, but not an English one
        ]}})

        with caplog.at_level('WARNING', logger='services.dual_translation.single_call_grader'):
            contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert contract['errors'] == []
        sc = contract['grader_trace']['single_call']
        assert sc['dropped']['unknown_type'] == 3 and sc['dropped']['invalid_entry'] == 0
        assert sc['dropped_total'] == 3 and sc['type_aliased'] == 0
        assert contract['scores']['accuracy'] == 4
        assert sum('unknown error type' in r.getMessage() for r in caplog.records) == 3
        assert contract['grading_assets'][0]['dropped']['unknown_type'] == 3

    def test_legacy_v5_slug_is_mapped_and_counted(self, monkeypatch, logged, caplog):
        assert TAXONOMY_V6['legacy_aliases']['classifier']['to'] == 'measure_word'
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(1, '一个', 'classifier', 'major', ref='一件')]}})

        with caplog.at_level('WARNING', logger='services.dual_translation.single_call_grader'):
            contract = _grade(ZH_GOLD, ZH_MEASURE, 'zh')

        (err,) = contract['errors']
        assert err['subtype'] == 'measure_word'
        sc = contract['grader_trace']['single_call']
        assert sc['type_aliased'] == 1 and sc['dropped_total'] == 0
        assert sc['per_error'][0]['type_aliased_from'] == 'classifier'
        assert any('mapped legacy error type' in r.getMessage() for r in caplog.records)

    def test_legacy_slug_that_maps_outside_this_language_is_dropped(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [_entry(2, 'was', 'classifier', 'major', ref='is')]}})

        sc = _grade(EN_GOLD, EN_TENSE, 'en')['grader_trace']['single_call']

        assert sc['dropped']['unknown_type'] == 1 and sc['type_aliased'] == 0

    def test_invalid_severity_or_non_object_entry_is_dropped_and_counted(self, monkeypatch, logged):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'verb_form_tense', 'severe', ref='is'),
            'a string, not an object',
        ]}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        assert contract['errors'] == []
        assert contract['grader_trace']['single_call']['dropped']['invalid_entry'] == 2


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

_TRACE_NOTE = '应该用“is”，不是“was”。'


class TestTraceAndAssets:

    def _graded(self, monkeypatch):
        _use_model(monkeypatch, {PRIMARY: _payload(
            [_entry(2, 'was', 'verb_form_tense', 'minor', _TRACE_NOTE, ref='is', source='interlingual')],
            naturalness=(4, 'many things with it'), range_=(4, 'Arduino board'))})
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
        assert sc['prompt_variant'] == 'v2'
        assert sc['parse_status'] == 'ok'
        assert sc['usage'] == {'in': 1700, 'out': 60, 'cached': 1024, 'reasoning': 0}
        assert sc['cost_usd'] == pytest.approx(0.00006)
        assert sc['latency_ms'] == 1250
        assert sc['errors_raw'] == 1 and sc['errors_kept'] == 1 and sc['dropped_total'] == 0
        assert sc['defaulted'] == {'confidence': 0, 'source': 0}
        assert sc['confidence_scale'] == {'high': 0.9, 'medium': 0.6, 'low': 0.3}
        assert sc['sentence_pairs'] == {'n': 3, 'aligned_ok': True}
        assert sc['span_resolution'] == {'exact': 1, 'normalised': 0, 'fuzzy': 0, 'diff_hunk': 0, 'sentence': 0}
        assert sc['correction_resolution'] == {'model_quote': 1, 'aligned_diff': 0, 'reference_sentence': 0}
        assert sc['explanation_sources'] == {'model': 1, 'template': 0}
        assert sc['judgments'] == {
            'naturalness': {'status': 'ok', 'band': 4, 'evidence_span': [
                EN_TENSE.index('many things with it'), EN_TENSE.index('many things with it') + 19]},
            'range': {'status': 'ok', 'band': 4, 'evidence_span': [
                EN_TENSE.index('Arduino board'), EN_TENSE.index('Arduino board') + 13]},
        }
        assert sc['unscored_dimensions'] == [] and sc['band_descriptors'] is True
        assert sc['per_error'] == [{
            'sentence_index': 1, 'subtype': 'verb_form_tense', 'type_aliased_from': None,
            'model_severity': 'minor', 'applied_severity': 'major',
            'confidence': 0.9, 'confidence_label': 'high', 'source': 'interlingual',
            'span_source': 'exact', 'correction_source': 'model_quote',
            'model_explanation': _TRACE_NOTE, 'explanation_rejected': None,
            'explanation_source': 'model',
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
        assert asset['response'] == {
            'errors': [{
                'sentence': 2, 'learner_quote': 'was', 'reference_quote': 'is',
                'type': 'verb_form_tense', 'severity': 'minor', 'confidence': 'high',
                'source': 'interlingual', 'explanation': _TRACE_NOTE,
            }],
            'naturalness': {'band': 4, 'evidence': 'many things with it'},
            'range': {'band': 4, 'evidence': 'Arduino board'},
        }
        assert asset['raw_response'] is None  # parsed fine -> no duplicate raw text
        assert (asset['errors_raw'], asset['errors_kept']) == (1, 1)
        blob = json.dumps(asset, ensure_ascii=False)
        assert EN_GOLD not in blob and 'Error types' not in blob
        assert len(blob) < 1500
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

    def test_request_prompt_and_schema(self, monkeypatch, logged):
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        _grade(EN_GOLD, EN_TENSE, 'en')

        call = model.calls[0]
        assert call['system'].startswith(sc_prompts.build_system_prompt('en'))
        assert 'CLEARLY WRONG to a native reader' in call['system']
        assert '"Major" does NOT require a change of meaning' in call['system']
        assert 'free translations' not in call['system']
        assert call['user'] == (
            "Learner's L1: Chinese (Mandarin, simplified).\n"
            'S1 SAME: First, you need an Arduino board.\n'
            'S2 REF: This is a small computer.\n'
            'S2 LRN: This was a small computer.\n'
            'S3 SAME: You can make many things with it.\n'
            "Write every explanation in Chinese (Mandarin, simplified) (the learner's L1), not in the "
            'language of the passage; quote the English words exactly as written.'
        )
        assert call['max_tokens'] == sc_prompts.MAX_TOKENS == 1400
        assert sc_prompts.TEMPERATURE == 0.0
        schema = call['schema']
        assert schema['strict'] is True
        # Output order: the error list first, the two judgments after it.
        assert list(schema['schema']['properties']) == ['errors', 'naturalness', 'range']
        assert schema['schema']['required'] == ['errors', 'naturalness', 'range']
        item = schema['schema']['properties']['errors']['items']
        assert item['required'] == [
            'sentence', 'learner_quote', 'reference_quote', 'type', 'severity',
            'confidence', 'source', 'explanation',
        ]
        assert item['properties']['type']['enum'] == list(sc_prompts.TYPE_IDS['en'])
        assert item['properties']['confidence']['enum'] == ['high', 'medium', 'low']
        assert item['properties']['source']['enum'] == ['interlingual', 'intralingual']
        assert 'Chinese (Mandarin, simplified)' in item['properties']['explanation']['description']
        judgment = schema['schema']['properties']['naturalness']
        assert judgment['required'] == ['band', 'evidence'] and judgment['properties']['band']['enum'] == [1, 2, 3, 4]

    def test_prompt_version_was_bumped_from_the_track_b_port(self):
        assert sc_prompts.PROMPT_VERSION != 'dt-single-call/p1_expl/2026-11-14'
        assert sc_prompts.PROMPT_VERSION.startswith('dt-single-call/v2')

    def test_error_instructions_come_before_the_judgment_instructions(self):
        for l2 in ('en', 'zh', 'ja'):
            system = sc_prompts.build_system_prompt(l2, band_descriptors='- naturalness: 4=x')
            assert system.index('Find every translation error') < system.index('Error types (pick exactly one id')
            assert system.index('Error types (pick exactly one id') < system.index('After the error list, judge')
            assert system.endswith('Band descriptors:\n- naturalness: 4=x')
            for field in ('learner_quote', 'reference_quote', 'confidence', 'source', 'explanation'):
                assert f'- {field}:' in system

    def test_free_translation_paragraph_is_opt_in_and_recorded(self, monkeypatch, logged):
        monkeypatch.setattr(Config, 'DT_SINGLE_CALL_FREE_TRANSLATION', True)
        model = _use_model(monkeypatch, {PRIMARY: {'errors': []}})

        contract = _grade(EN_GOLD, EN_TENSE, 'en')

        system = model.calls[0]['system']
        assert 'IMPORTANT - free translations.' in system and 'natural English?' in system
        assert system.index('IMPORTANT - free translations.') < system.index('After the error list, judge')
        assert contract['grader_trace']['single_call']['prompt_variant'] == 'v2_mit'
        assert contract['grading_assets'][0]['prompt_variant'] == 'v2_mit'


# ---------------------------------------------------------------------------
# Persistence (routes)
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data):
        self.data = data


class _MissingColumn(Exception):
    """What postgrest-py raises for PGRST204 / 42703."""
    code = 'PGRST204'


class _Query:
    def __init__(self, db, table):
        self._db, self._table = db, table

    def select(self, columns='*', **k):
        self._db.calls.append((self._table, 'select', columns))
        if self._db.missing_columns and any(c in columns for c in self._db.missing_columns):
            raise _MissingColumn(f'column {self._table}.{self._db.missing_columns[0]} does not exist')
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, payload):
        if self._table == self._db.fail_table:
            raise RuntimeError(f'relation "{self._table}" does not exist (PGRST205)')
        rows = payload if isinstance(payload, list) else [payload]
        if self._db.missing_columns and any(c in row for row in rows for c in self._db.missing_columns):
            self._db.rejected.append((self._table, payload))
            raise _MissingColumn(
                f"Could not find the '{self._db.missing_columns[0]}' column of '{self._table}' in the schema cache")
        self._db.calls.append((self._table, 'insert', payload))
        return self

    def update(self, payload):
        self._db.calls.append((self._table, 'update', payload))
        return self

    def execute(self):
        return _Result(self._db.data.get(self._table, []))


class _DB:
    def __init__(self, data=None, fail_table=None, missing_columns=()):
        self.data, self.fail_table, self.calls = data or {}, fail_table, []
        self.missing_columns, self.rejected = tuple(missing_columns), []

    def table(self, name):
        return _Query(self, name)

    def inserts(self, table):
        return [p for n, m, p in self.calls if n == table and m == 'insert']

    def selects(self, table):
        return [p for n, m, p in self.calls if n == table and m == 'select']


_ASSET_ERROR_COLUMNS = (
    'sentence_index', 'model_severity', 'model_note', 'span_source', 'correction_source',
    'confidence_label', 'explanation_source',
)
_NOTE = '这里说的是现在的事实，应该用“is”，不是“was”。'


class TestPersistence:

    def _contract(self, monkeypatch):
        _use_model(monkeypatch, {PRIMARY: _payload(
            [_entry(2, 'was', 'verb_form_tense', 'minor', _NOTE, ref='is', confidence='medium')],
            naturalness=(4, 'many things with it'), range_=(4, 'Arduino board'))})
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
        assert grade['scores'] == {
            'accuracy': 3, 'fidelity': 4, 'understandability': 4, 'naturalness': 4, 'range': 4}

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
        assert row['model_note'] == _NOTE and row['explanation_source'] == 'model'
        assert _NOTE not in row['explanation']  # the stored explanation is the template
        assert row['confidence'] == 0.6 and row['confidence_label'] == 'medium'
        assert row['span_source'] == 'exact' and row['correction_source'] == 'model_quote'
        assert 'explanation_parts' not in row and 'taxonomy_version' not in row
        (call_rows,) = db.inserts('dt_grading_call')
        (call_row,) = call_rows
        assert call_row['submission_id'] == 5
        assert call_row['model_slug'] == PRIMARY and call_row['status'] == 'ok'
        assert call_row['prompt_version'] == sc_prompts.PROMPT_VERSION
        assert call_row['response']['errors'][0]['learner_quote'] == 'was'
        assert call_row['response']['naturalness'] == {'band': 4, 'evidence': 'many things with it'}

    def test_every_value_written_passes_the_migration_checks(self, monkeypatch, logged):
        """The value sets in code and the CHECKs in dt_grading_assets.sql are one list."""
        with open(os.path.join(_REPO, 'migrations', 'dt_grading_assets.sql'), encoding='utf-8') as fh:
            sql = fh.read()

        def allowed(column):
            body = re.search(rf"CHECK \({column} IS NULL\s+OR {column} IN \(([^)]*)\)\)", sql).group(1)
            return set(re.findall(r"'([^']+)'", body))

        assert allowed('span_source') == set(scg.SPAN_SOURCES)
        assert allowed('correction_source') == set(scg.CORRECTION_SOURCES)
        assert allowed('confidence_label') == set(sc_prompts.CONFIDENCE_LABELS)
        assert allowed('explanation_source') == {
            scg.EXPLANATION_FROM_MODEL, scg.EXPLANATION_FROM_TEMPLATE, scg.EXPLANATION_FROM_EXPLAINER}
        for column in _ASSET_ERROR_COLUMNS:
            assert re.search(rf"ADD COLUMN IF NOT EXISTS {column}\s", sql), column
        from services.dual_translation import explainer
        assert f'char_length(model_note) <= {explainer.MAX_APPLICATION_CHARS}' in sql

    def test_migration_is_additive_and_idempotent(self):
        with open(os.path.join(_REPO, 'migrations', 'dt_grading_assets.sql'), encoding='utf-8') as fh:
            statements = '\n'.join(
                line for line in fh.read().splitlines() if not line.lstrip().startswith('--'))
        for forbidden in (r'\bDROP\b', r'\bDELETE\s+FROM\b', r'\bTRUNCATE\b', r'\bALTER\s+COLUMN\b',
                          r'\bRENAME\b', r'\bUPDATE\s+public\b'):
            assert not re.search(forbidden, statements, re.IGNORECASE), forbidden
        assert not re.search(r'ADD COLUMN (?!IF NOT EXISTS)', statements)
        assert not re.search(r'CREATE TABLE (?!IF NOT EXISTS)', statements)
        assert not re.search(r'CREATE INDEX (?!IF NOT EXISTS)', statements)
        # every CHECK on the existing table is added only when absent
        assert statements.count('ADD CONSTRAINT') == statements.count('IF NOT EXISTS (SELECT 1 FROM pg_constraint')

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
        (off,) = db.selects('dt_error_instance')
        assert 'sentence_index' not in off

        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        db = _DB(data)
        dt_routes._cached_grade(db, 5)
        (on,) = db.selects('dt_error_instance')
        assert all(col in on for col in _ASSET_ERROR_COLUMNS)

    def test_reloaded_grade_shows_the_model_explanation_again(self, monkeypatch):
        """explanation_parts is not a column; a cached grade rebuilds it from
        model_note + explanation_source so the learner sees the same two layers."""
        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        data = {
            'dt_grade': [{'scores': {}, 'overall_band': 3, 'diff': [], 'grader_trace': {}}],
            'dt_error_instance': [
                {'explanation': 'RULE', 'model_note': _NOTE, 'explanation_source': 'model'},
                {'explanation': 'RULE', 'model_note': None, 'explanation_source': 'template'},
                {'explanation': 'RULE\nAPP', 'model_note': None, 'explanation_source': None},
            ],
        }

        errors = dt_routes._cached_grade(_DB(data), 5)['errors']

        assert errors[0]['explanation_parts'] == {'rule': 'RULE', 'application': _NOTE}
        assert 'explanation_parts' not in errors[1] and 'explanation_parts' not in errors[2]

    def test_call_row_failure_is_swallowed(self, monkeypatch, logged):
        """A missing dt_grading_call must not fail the request: the grade is
        already stored."""
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
        # The learner-facing response carries the model's explanation where the UI renders it.
        (err,) = (body.get('data') or body)['errors']
        assert err['explanation_parts']['application'] == _NOTE


# ---------------------------------------------------------------------------
# Item 6 — defaults are ON, and a missing migration cannot cost a grade
# ---------------------------------------------------------------------------

class TestDefaultsOnAndMissingMigration:

    def test_defaults(self):
        """Read the defaults in a fresh interpreter with the DT_* variables unset
        (reloading config in-process would swap the Config class under other tests)."""
        out = self._config_values({})
        assert out == {
            'DT_SINGLE_CALL_GRADER': True, 'DT_GRADING_ASSET_COLUMNS': True,
            'DT_SINGLE_CALL_FREE_TRANSLATION': False, 'DT_SINGLE_CALL_EXPLAINER': False,
            'DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE': False,
            'DT_SINGLE_CALL_MODEL': PRIMARY, 'DT_SINGLE_CALL_FALLBACK_MODEL': FALLBACK,
        }

    def test_env_vars_still_override_the_defaults(self):
        out = self._config_values({'DT_SINGLE_CALL_GRADER': 'false', 'DT_GRADING_ASSET_COLUMNS': 'False'})
        assert out['DT_SINGLE_CALL_GRADER'] is False and out['DT_GRADING_ASSET_COLUMNS'] is False

    @staticmethod
    def _config_values(overrides):
        import subprocess
        names = ['DT_SINGLE_CALL_GRADER', 'DT_GRADING_ASSET_COLUMNS', 'DT_SINGLE_CALL_FREE_TRANSLATION',
                 'DT_SINGLE_CALL_EXPLAINER', 'DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE',
                 'DT_SINGLE_CALL_MODEL', 'DT_SINGLE_CALL_FALLBACK_MODEL']
        env = {k: v for k, v in os.environ.items() if not k.startswith('DT_')}
        env.update(overrides)
        code = ("from config import Config as C; import json; "
                f"print(json.dumps({{n: getattr(C, n) for n in {names!r}}}))")
        out = subprocess.run(
            [sys.executable, '-c', code], cwd=_REPO, env=env, capture_output=True, text=True, check=True,
        ).stdout.strip().splitlines()[-1]
        return json.loads(out)

    def _contract(self, monkeypatch):
        _use_model(monkeypatch, {PRIMARY: {'errors': [
            _entry(2, 'was', 'verb_form_tense', 'minor', _NOTE, ref='is'),
        ]}})
        return _grade(EN_GOLD, EN_TENSE, 'en')

    @pytest.mark.parametrize('missing', [
        _ASSET_ERROR_COLUMNS,          # migration not applied at all
        ('explanation_source',),       # an older copy of the migration was applied
    ])
    def test_missing_column_still_saves_the_grade(self, monkeypatch, logged, caplog, missing):
        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        contract = self._contract(monkeypatch)
        assets = contract.pop('grading_assets')
        db = _DB(missing_columns=missing, fail_table='dt_grading_call')

        with caplog.at_level('ERROR', logger=dt_routes.logger.name):
            dt_routes._persist_grade(db, 5, EN_TENSE, None, contract)   # must not raise
            dt_routes._persist_grading_assets(db, 5, assets)            # must not raise

        assert len(db.rejected) == 1                       # the first attempt named the columns
        (rows,) = db.inserts('dt_error_instance')          # ... the retry did not, and landed
        assert not set(rows[0]) & set(_ASSET_ERROR_COLUMNS)
        assert rows[0]['learner_form'] == 'was' and rows[0]['explanation']
        (grade,) = db.inserts('dt_grade')                  # the grade row is written
        assert grade['overall_band'] == contract['overall_band']
        assert db.inserts('dt_grading_call') == []
        errors = [r for r in caplog.records if 'grading-asset columns unavailable' in r.getMessage()]
        assert len(errors) == 1 and 'dt_grading_assets.sql' in errors[0].getMessage()

    def test_missing_column_is_logged_once_and_later_submissions_skip_the_doomed_attempt(
            self, monkeypatch, logged, caplog):
        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        contract = self._contract(monkeypatch)
        contract.pop('grading_assets')
        db = _DB(missing_columns=_ASSET_ERROR_COLUMNS)

        with caplog.at_level('ERROR', logger=dt_routes.logger.name):
            for submission_id in (5, 6, 7):
                dt_routes._persist_grade(db, submission_id, EN_TENSE, None, contract)

        assert len(db.inserts('dt_error_instance')) == 3 and len(db.inserts('dt_grade')) == 3
        assert len(db.rejected) == 1  # only the first submission paid for a failed insert
        assert sum('grading-asset columns unavailable' in r.getMessage() for r in caplog.records) == 1

    def test_columns_are_probed_again_after_the_pause(self, monkeypatch, logged):
        """Applying the migration later needs no restart."""
        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        contract = self._contract(monkeypatch)
        contract.pop('grading_assets')
        dt_routes._persist_grade(_DB(missing_columns=_ASSET_ERROR_COLUMNS), 5, EN_TENSE, None, contract)
        assert dt_routes._asset_columns_usable() is False

        dt_routes._asset_columns_state['unavailable_until'] = 0.0  # the pause is over; migration applied
        db = _DB()
        dt_routes._persist_grade(db, 6, EN_TENSE, None, contract)

        (rows,) = db.inserts('dt_error_instance')
        assert rows[0]['span_source'] == 'exact'

    def test_a_failure_of_the_plain_insert_still_propagates(self, monkeypatch, logged):
        """Only the extra columns are optional. If the insert fails without them
        too, the submission stays ungraded (no dt_grade row), exactly as before."""
        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        contract = self._contract(monkeypatch)
        contract.pop('grading_assets')
        db = _DB(fail_table='dt_error_instance')

        with pytest.raises(RuntimeError):
            dt_routes._persist_grade(db, 5, EN_TENSE, None, contract)

        assert db.inserts('dt_grade') == []
        assert dt_routes._asset_columns_usable() is True  # not blamed on the asset columns

    def test_missing_column_on_read_still_serves_the_cached_grade(self, monkeypatch, caplog):
        monkeypatch.setattr(Config, 'DT_GRADING_ASSET_COLUMNS', True)
        data = {
            'dt_grade': [{'scores': {'accuracy': 3}, 'overall_band': 3, 'diff': [], 'grader_trace': {}}],
            'dt_error_instance': [{'explanation': 'RULE', 'learner_form': 'was'}],
        }
        db = _DB(data, missing_columns=('confidence_label',))

        with caplog.at_level('ERROR', logger=dt_routes.logger.name):
            cached = dt_routes._cached_grade(db, 5)

        assert cached['overall_band'] == 3 and cached['errors'] == data['dt_error_instance']
        first, second = db.selects('dt_error_instance')
        assert 'confidence_label' in first and not any(c in second for c in _ASSET_ERROR_COLUMNS)
        assert sum('grading-asset columns unavailable' in r.getMessage() for r in caplog.records) == 1
