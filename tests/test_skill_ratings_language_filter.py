"""Language-specific test types only get test_skill_ratings rows for their own
language. A cross-language row (e.g. pitch_accent on a zh test) makes the
recommender offer that type to the wrong learners — see
migrations/cleanup_cross_language_test_skill_ratings.sql.
"""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from config import Config
from services.test_generation.database_client import TestDatabaseClient

ZH, EN, JA = 1, 2, 3

ACTIVE_TYPES = [
    {'id': 1, 'type_code': 'reading', 'requires_audio': False},
    {'id': 2, 'type_code': 'listening', 'requires_audio': True},
    {'id': 11, 'type_code': 'pinyin', 'requires_audio': False},
    {'id': 13, 'type_code': 'pitch_accent', 'requires_audio': False},
    {'id': 14, 'type_code': 'classifier_drill', 'requires_audio': False},
    {'id': 15, 'type_code': 'counter_drill', 'requires_audio': False},
]


def _inserted_type_codes(language_id, has_audio=True):
    db = TestDatabaseClient.__new__(TestDatabaseClient)
    db.client = MagicMock()
    db.get_active_test_types = lambda: ACTIVE_TYPES
    db.insert_test_skill_ratings(uuid4(), 1400, has_audio=has_audio, language_id=language_id)
    rows = db.client.table.return_value.insert.call_args.args[0]
    by_id = {t['id']: t['type_code'] for t in ACTIVE_TYPES}
    return {by_id[r['test_type_id']] for r in rows}


@pytest.mark.parametrize('language_id, expected', [
    (ZH, {'reading', 'listening', 'pinyin', 'classifier_drill'}),
    (EN, {'reading', 'listening'}),
    (JA, {'reading', 'listening', 'pitch_accent', 'counter_drill'}),
])
def test_generation_only_creates_in_language_types(language_id, expected):
    assert _inserted_type_codes(language_id) == expected


def test_audio_filter_still_applies():
    assert 'listening' not in _inserted_type_codes(ZH, has_audio=False)


def test_unrestricted_type_applies_everywhere():
    assert Config.test_type_applies_to_language('reading', EN)
    assert not Config.test_type_applies_to_language('pitch_accent', ZH)
    assert not Config.test_type_applies_to_language('pinyin', EN)
