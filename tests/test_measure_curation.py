"""Classifier and counter curation share one engine behind their own names."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import services.classifier_curation.config as zh_config
import services.classifier_curation.generator as zh_gen
import services.classifier_curation.judge as zh_judge
import services.counter_curation.config as ja_config
import services.counter_curation.generator as ja_gen
import services.counter_curation.judge as ja_judge
from services.classifier_curation.schemas import ClassifierMeta, JudgeRatings
from services.counter_curation.schemas import CounterMeta, NounExample


def _capture(monkeypatch, module, result):
    seen = []

    def fake(prompt, **kwargs):
        seen.append((prompt, kwargs))
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(module, 'call_llm', fake)
    return seen


def test_output_paths_and_pipeline_tags_are_unchanged():
    assert zh_config.PIPELINE == 'classifier_curation'
    assert ja_config.PIPELINE == 'counter_curation'
    assert zh_config.OUTPUT_DIR.replace('\\', '/').endswith('data/classifier_curation')
    assert ja_config.OUTPUT_DIR.replace('\\', '/').endswith('data/counter_curation')
    assert zh_config.APPROVED_FILE.endswith('approved_curation.json')
    assert (zh_config.TARGET_NOUNS, ja_config.TARGET_NOUNS) == (16, 20)
    assert zh_config.LANGUAGE_ID_ZH == 1 and ja_config.LANGUAGE_ID_JA == 3


@pytest.mark.parametrize('judge,config,opening', [
    (zh_judge, zh_config, 'Measure word: 「条」 (long things)'),
    (ja_judge, ja_config, 'Counter: 「条」 (long things)'),
])
def test_judge_clamps_ratings_and_tags_the_call(monkeypatch, judge, config, opening):
    seen = _capture(monkeypatch, judge, SimpleNamespace(ratings=[9, 0, 4]))
    assert judge.judge_nouns('条', ['a', 'b', 'c'], 'long things') == [5, 1, 4]
    prompt, kwargs = seen[0]
    assert prompt.startswith(opening)
    assert '1. a\n2. b\n3. c' in prompt
    assert '{"ratings": [int per noun, in order]' in prompt
    assert kwargs['model'] == config.JUDGE_MODEL
    assert kwargs['pipeline'] == config.PIPELINE
    assert kwargs['task_name'] == 'judge_nouns'
    assert kwargs['schema'] is JudgeRatings
    assert kwargs['provider'] == 'openrouter'


@pytest.mark.parametrize('judge', [zh_judge, ja_judge])
def test_judge_fails_open(monkeypatch, judge):
    _capture(monkeypatch, judge, RuntimeError('down'))
    assert judge.judge_nouns('条', ['a', 'b']) == [5, 5]
    _capture(monkeypatch, judge, SimpleNamespace(ratings=[1]))
    assert judge.judge_nouns('条', ['a', 'b']) == [5, 5]
    assert judge.judge_nouns('条', []) == []


def test_generators_keep_their_schemas_and_task_names(monkeypatch):
    zh = _capture(monkeypatch, zh_gen, 'ok')
    ja = _capture(monkeypatch, ja_gen, 'ok')
    zh_gen.classify_classifier('条')
    zh_gen.generate_nouns('条')
    ja_gen.classify_counter('本')
    ja_gen.generate_nouns('本')
    assert [k['task_name'] for _, k in zh] == ['classify_classifier', 'generate_nouns']
    assert [k['task_name'] for _, k in ja] == ['classify_counter', 'generate_nouns']
    assert zh[0][1]['schema'] is ClassifierMeta and ja[0][1]['schema'] is CounterMeta
    assert (zh[0][1]['temperature'], zh[1][1]['temperature']) == (0.0, 0.3)
    assert f'List {ja_config.TARGET_NOUNS} common Japanese nouns' in ja[1][0]


def test_group_vocabulary_is_enforced_per_package():
    ClassifierMeta(hanzi='条', group='flat', difficulty_tier=1)
    CounterMeta(counter='本', group='flat_thin', difficulty_tier=5)
    with pytest.raises(ValidationError):
        ClassifierMeta(hanzi='条', group='flat_thin', difficulty_tier=1)
    with pytest.raises(ValidationError):
        CounterMeta(counter='本', group='flat', difficulty_tier=1)
    assert NounExample(noun='兎', also_acceptable_counters='羽').also_acceptable_counters == ['羽']
    assert JudgeRatings(ratings=[5, 4]).reasons == ['', '']
