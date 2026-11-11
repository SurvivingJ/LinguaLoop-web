"""services/vocabulary/lexicon.py against the shared fixture (also replayed by
tests/unit/lexicon.test.js)."""

import json
from pathlib import Path

import pytest

from services.vocabulary.lexicon import mask_headword, pos_class

CASES = json.loads((Path(__file__).parent / 'fixtures' / 'lexicon' / 'cases.json').read_text('utf-8'))


@pytest.mark.parametrize('tag,expected', CASES['pos_class'])
def test_pos_class(tag, expected):
    assert pos_class(tag) == expected


@pytest.mark.parametrize('text,lemma,expected', CASES['mask_headword'])
def test_mask_headword(text, lemma, expected):
    assert mask_headword(text, lemma) == expected
