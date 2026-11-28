"""PhraseDetector._parse_first_object tolerates trailing text after the JSON object."""

import json

import pytest

from services.vocabulary.phrase_detector import PhraseDetector


def test_plain_object():
    assert PhraseDetector._parse_first_object('{"phrases": []}') == {'phrases': []}


def test_object_followed_by_more_braces():
    raw = '{"phrases": [{"phrase": "気を付ける", "components": ["気", "付ける"]}]}\n\n{"note": "done"}'
    assert PhraseDetector._parse_first_object(raw)['phrases'][0]['phrase'] == '気を付ける'


def test_fenced_object_with_commentary():
    raw = '```json\n{"phrases": []}\n```\nI found no phrases {really}.'
    assert PhraseDetector._parse_first_object(raw) == {'phrases': []}


def test_unrecoverable_still_raises():
    with pytest.raises(json.JSONDecodeError):
        PhraseDetector._parse_first_object('{"phrases": [1 2]}')
