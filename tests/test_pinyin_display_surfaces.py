"""TASK-999: Chinese pronunciations reach the remaining learner views in one
form, tone-marked pinyin, at the payload boundary:

* the tap-a-word popover in tests and transcripts (GET /api/tests/test/<id>,
  ``definitions[*].reading``),
* flashcards, the /flashcards page and the session player
  (GET /api/flashcards/due, ``cards[*].pronunciation``),
* the admin vocabulary preview (GET /api/admin/vocab/word/<id>/preview,
  ``word.pronunciation``).

Japanese and other languages pass through exactly as stored.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services.pinyin_format import display_pronunciation


def _chain(data):
    chain = MagicMock()
    chain.execute.return_value = SimpleNamespace(data=data, count=len(data) if isinstance(data, list) else 0)
    for m in ('select', 'eq', 'neq', 'lte', 'single', 'order', 'or_', 'in_', 'not_',
              'is_', 'range', 'limit', 'offset', 'filter'):
        getattr(chain, m).return_value = chain
    chain.not_ = chain
    return chain


def _gloss_passthrough(db, rows, preferred):
    for r in rows:
        r['definition_language_id'] = r.get('language_id')
        r['definition_is_gloss'] = False


# ---------------------------------------------------------------------------
# display_pronunciation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('stored, lang, expected', [
    ('biàn dé (bian4 de2)', {'language_id': 1}, 'biàn dé'),
    ('bi3', {'language_id': 1}, 'bǐ'),
    ('lu:3 se4', {'language_code': 'zh'}, 'lǚ sè'),
    ('zhāng', {'language_id': 1}, 'zhāng'),
    ('zi (zi5)', {'language_id': '1'}, 'zi'),
    ('きょう', {'language_id': 3}, 'きょう'),
    ('すぴーど-speed', {'language_id': 3}, 'すぴーど-speed'),
    ('/ola/', {'language_id': 2}, '/ola/'),
    # not Chinese: even a numbered-looking string is left as stored
    ('bian4 de2', {'language_id': 3}, 'bian4 de2'),
    ('bian4 de2', {}, 'bian4 de2'),
    # the word's own language wins over the test's language code
    ('bian4 de2', {'language_id': 2, 'language_code': 'zh'}, 'bian4 de2'),
    ('bian4 de2', {'language_id': None, 'language_code': 'zh'}, 'biàn dé'),
    ('bian4 de2', {'language_id': 1, 'language_code': 'ja'}, 'biàn dé'),
    (None, {'language_id': 1}, ''),
    (None, {'language_id': 3}, ''),
    ('', {'language_id': 1}, ''),
])
def test_display_pronunciation(stored, lang, expected):
    assert display_pronunciation(stored, **lang) == expected


# ---------------------------------------------------------------------------
# Flashcards: one builder feeds the /flashcards page and the session player
# ---------------------------------------------------------------------------

def _card(sense_id, pron, lang_id, lemma):
    return {
        'id': sense_id, 'sense_id': sense_id, 'stability': 1.0, 'difficulty': 0.3,
        'due_date': '2026-11-17', 'last_review': None, 'reps': 0, 'lapses': 0,
        'state': 'new', 'example_sentence': None, 'audio_url': None,
        'dim_word_senses': {
            'id': sense_id, 'vocab_id': sense_id, 'definition': 'd', 'pronunciation': pron,
            'example_sentence': '', 'sense_rank': 1, 'definition_level': 1,
            'dim_vocabulary': {'lemma': lemma, 'language_id': lang_id, 'frequency_rank': 1},
        },
    }


@pytest.mark.parametrize('lang_id, stored, expected', [
    (1, 'biàn dé (bian4 de2)', 'biàn dé'),
    (1, 'bi3', 'bǐ'),
    (3, 'きょう', 'きょう'),
])
def test_flashcards_due_pronunciation(client, auth_headers, lang_id, stored, expected):
    db = MagicMock()
    db.table.return_value = _chain([_card(7, stored, lang_id, '词')])
    with patch('routes.flashcards.get_db', return_value=db), \
         patch('services.vocabulary.gloss_lookup.apply_definition_language_preference',
               side_effect=_gloss_passthrough):
        resp = client.get(f'/api/flashcards/due?language_id={lang_id}', headers=auth_headers)
    assert resp.status_code == 200
    card = json.loads(resp.data)['cards'][0]
    assert card['pronunciation'] == expected


def test_flashcards_due_missing_pronunciation_is_empty(client, auth_headers):
    db = MagicMock()
    db.table.return_value = _chain([_card(7, None, 1, '词')])
    with patch('routes.flashcards.get_db', return_value=db), \
         patch('services.vocabulary.gloss_lookup.apply_definition_language_preference',
               side_effect=_gloss_passthrough):
        resp = client.get('/api/flashcards/due?language_id=1', headers=auth_headers)
    assert json.loads(resp.data)['cards'][0]['pronunciation'] == ''


# ---------------------------------------------------------------------------
# Tap-a-word popover: GET /api/tests/test/<id> definitions
# ---------------------------------------------------------------------------

def _test_content(lang_code, lang_id, pron):
    test = {
        'id': 't1', 'slug': 'alpha', 'title': 'T', 'transcript': '变得',
        'dim_languages': {'language_code': lang_code, 'language_name': 'X'},
        'vocab_token_map': [['变得', 11]],
    }
    senses = [{
        'id': 11, 'vocab_id': 5, 'sense_rank': 1, 'definition_level': 1,
        'definition': 'to become', 'pronunciation': pron,
        'dim_vocabulary': {'lemma': '变得', 'part_of_speech': 'verb', 'language_id': lang_id},
    }]
    return {'test': test, 'questions': [], 'senses': senses}


@pytest.mark.parametrize('lang_code, lang_id, stored, expected', [
    ('zh', 1, 'biàn dé (bian4 de2)', 'biàn dé'),
    ('zh', 1, 'bi3', 'bǐ'),
    ('ja', 3, 'きょう', 'きょう'),
    ('zh', 1, None, None),
])
def test_popover_reading(client, lang_code, lang_id, stored, expected):
    content = _test_content(lang_code, lang_id, stored)
    with patch('routes.tests.catalog.get_db', return_value=MagicMock()), \
         patch('routes.tests.catalog.get_test_content',
               return_value=(content, ({}, False, None))), \
         patch('services.vocabulary.gloss_lookup.apply_definition_language_preference',
               side_effect=_gloss_passthrough):
        resp = client.get('/api/tests/test/alpha')
    assert resp.status_code == 200, resp.data
    body = json.loads(resp.data)
    data = body.get('data', body)
    assert data['definitions']['11']['reading'] == expected


# ---------------------------------------------------------------------------
# Admin vocabulary preview
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('lang_id, stored, expected', [
    (1, 'biàn dé (bian4 de2)', 'biàn dé'),
    (3, 'きょう', 'きょう'),
])
def test_admin_preview_pronunciation(client, auth_headers, lang_id, stored, expected):
    sense = {'id': 11, 'definition': 'd', 'pronunciation': stored, 'ipa_pronunciation': '',
             'morphological_forms': None,
             'dim_vocabulary': {'lemma': '变得', 'semantic_class': '', 'part_of_speech': 'verb',
                                'level_tag': 'T3'}}
    db = MagicMock()
    db.table.side_effect = lambda name: _chain(sense if name == 'dim_word_senses' else [])
    with patch('middleware.auth._user_has_tier', return_value=True), \
         patch('routes.vocab_admin.get_db', return_value=db):
        resp = client.get(f'/api/admin/vocab/word/11/preview?language_id={lang_id}',
                          headers=auth_headers)
    assert resp.status_code == 200, resp.data
    body = json.loads(resp.data)
    data = body.get('data', body)
    assert data['word']['pronunciation'] == expected
