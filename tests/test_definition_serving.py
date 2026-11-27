"""definition_match options in the learner's language (services/vocabulary_ladder/definition_serving.py).

Reported 2026-11-26: a learner with English as their native language, studying
Japanese, was shown definition_match items whose four options were Japanese
definitions. The stored items carry the word's own-language definitions filed
under ``nl.en``; serve time rebuilds them from the English gloss rows.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from services import intro_drill, prestudy
from services.exercise_content import store
from services.vocabulary_ladder import definition_serving as ds

JA, EN, ZH = 3, 2, 1


# ---------------------------------------------------------------------------
# A PostgREST-ish fake over in-memory tables
# ---------------------------------------------------------------------------

class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.filters, self.order_col, self.window = [], None, None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters.append(lambda r, c=col, v=val: r.get(c) == v)
        return self

    def in_(self, col, vals):
        vals = set(vals)
        self.filters.append(lambda r, c=col: r.get(c) in vals)
        return self

    def gte(self, col, val):
        self.filters.append(lambda r, c=col, v=val: r.get(c) is not None and r.get(c) >= v)
        return self

    def order(self, col, desc=False):
        self.order_col = col
        return self

    def range(self, a, b):
        self.window = (a, b + 1)
        return self

    def limit(self, n):
        self.window = (0, n)
        return self

    def single(self):
        return self

    def execute(self):
        self.db.calls.append(self.name)
        rows = [copy.deepcopy(r) for r in self.db.tables.get(self.name, [])
                if all(f(r) for f in self.filters)]
        if self.order_col:
            rows.sort(key=lambda r: r.get(self.order_col))
        if self.window:
            rows = rows[self.window[0]:self.window[1]]
        return SimpleNamespace(data=rows)


class FakeDB:
    def __init__(self, tables):
        self.tables = tables
        self.calls: list[str] = []

    def table(self, name):
        return _Query(self, name)


NOUN_GLOSSES = ['a chicken', 'a door', 'a painting', 'a battery', 'a leaf', 'the sun', 'a bond',
                'livestock', 'a plan', 'art', 'lighting', 'a voice', 'history', 'thirty']
VERB_GLOSSES = ['to tease', 'to rely on', 'to pack', 'to accept', 'to heat', 'to meet',
                'to stare at', 'to imitate', 'to shorten', 'to endure']


def _tables(extra_nouns: int = 60, extra_verbs: int = 60) -> dict:
    """ja words with native (ja) senses and English glosses.

    vocab 1 = 人間 (noun; native sense 100 'standard'), with an English gloss at
    both levels; vocab 2 = する (verb); vocab 3 = 犬 (noun) with NO English
    gloss. Plenty of other nouns and verbs supply distractors.
    """
    vocab = [
        {'id': 1, 'lemma': '人間', 'frequency_rank': 4.5, 'part_of_speech': 'noun', 'language_id': JA},
        {'id': 2, 'lemma': '為る', 'frequency_rank': 6.0, 'part_of_speech': 'verb', 'language_id': JA},
        {'id': 3, 'lemma': '犬', 'frequency_rank': 4.4, 'part_of_speech': 'noun', 'language_id': JA},
    ]
    senses = [
        # native rows (what the stored items were built from)
        {'id': 100, 'vocab_id': 1, 'sense_rank': 1, 'definition_level': 'standard',
         'definition': '人類または個人としての人を指す言葉。', 'word_language_id': JA, 'definition_language_id': JA},
        {'id': 200, 'vocab_id': 2, 'sense_rank': 1, 'definition_level': 'simple',
         'definition': '何かを行うこと。', 'word_language_id': JA, 'definition_language_id': JA},
        {'id': 300, 'vocab_id': 3, 'sense_rank': 1, 'definition_level': 'standard',
         'definition': '人に飼われる動物。', 'word_language_id': JA, 'definition_language_id': JA},
        # English glosses
        {'id': 1001, 'vocab_id': 1, 'sense_rank': 1, 'definition_level': 'standard',
         'definition': 'a human; a person — the human species or one of its members',
         'word_language_id': JA, 'definition_language_id': EN},
        {'id': 1002, 'vocab_id': 1, 'sense_rank': 1, 'definition_level': 'simple',
         'definition': 'a person', 'word_language_id': JA, 'definition_language_id': EN},
        {'id': 2001, 'vocab_id': 2, 'sense_rank': 1, 'definition_level': 'simple',
         'definition': 'to do; to perform', 'word_language_id': JA, 'definition_language_id': EN},
    ]
    next_vocab, next_sense = 10, 5000
    for i in range(extra_nouns):
        text = f'{NOUN_GLOSSES[i % len(NOUN_GLOSSES)]} {i}'
        vocab.append({'id': next_vocab, 'lemma': f'名{i}', 'frequency_rank': 4.5,
                      'part_of_speech': 'noun', 'language_id': JA})
        for level in ('standard', 'simple'):
            senses.append({'id': next_sense, 'vocab_id': next_vocab, 'sense_rank': 1,
                           'definition_level': level, 'definition': f'{text} — a thing',
                           'word_language_id': JA, 'definition_language_id': EN})
            next_sense += 1
        next_vocab += 1
    for i in range(extra_verbs):
        text = f'{VERB_GLOSSES[i % len(VERB_GLOSSES)]} {i}'
        vocab.append({'id': next_vocab, 'lemma': f'動{i}', 'frequency_rank': 5.5,
                      'part_of_speech': 'verb', 'language_id': JA})
        for level in ('standard', 'simple'):
            senses.append({'id': next_sense, 'vocab_id': next_vocab, 'sense_rank': 1,
                           'definition_level': level, 'definition': text,
                           'word_language_id': JA, 'definition_language_id': EN})
            next_sense += 1
        next_vocab += 1
    # A near-synonym of 人間's key that must never be offered as "wrong".
    vocab.append({'id': 9, 'lemma': '人', 'frequency_rank': 4.5, 'part_of_speech': 'noun',
                  'language_id': JA})
    senses.append({'id': 9001, 'vocab_id': 9, 'sense_rank': 1, 'definition_level': 'standard',
                   'definition': 'a person; someone — an individual', 'word_language_id': JA,
                   'definition_language_id': EN})
    return {'dim_vocabulary': vocab, 'dim_word_senses': senses}


def _stored_v2(word='人間'):
    """A definition_match item as the generator stores it: ja text under nl.en."""
    return {'word': word, 'pronunciation': 'にんげん', 'tier': 'T6', 'schema_version': 2,
            'nl': {'en': {'correct_answer': '人類または個人としての人を指す言葉。',
                          'options': ['利益を得るために、資金や資本を出すこと。',
                                      '人類または個人としての人を指す言葉。',
                                      '頭の中で何かを考えることです。',
                                      '野菜や果物を育てるための、広い土地のことです。']}}}


def _item(sense_id, content, exercise_type='definition_match', **extra):
    return {'exercise_id': f'e{sense_id}', 'sense_id': sense_id,
            'exercise_type': exercise_type, 'content': content, **extra}


@pytest.fixture(autouse=True)
def _fresh_pools():
    ds.reset_cache()
    yield
    ds.reset_cache()


# ---------------------------------------------------------------------------
# Rebuilding
# ---------------------------------------------------------------------------

def test_japanese_options_filed_under_en_are_rebuilt_in_english():
    db = FakeDB(_tables())
    items = [_item(100, _stored_v2())]
    assert ds.localise(db, items, language_id=JA, nl_language_id=EN) == 0
    c = items[0]['content']
    key = 'a human; a person — the human species or one of its members'
    assert c['correct_answer'] == c['correct_definition'] == key     # the item's own level
    assert key in c['options'] and len(c['options']) == 4 and len(set(c['options'])) == 4
    assert all(ds.script_family(o) == 'latin' for o in c['options'])
    assert 'nl' not in c and 'schema_version' not in c                # flat: every reader takes it
    assert c['word'] == '人間' and c['pronunciation'] == 'にんげん'
    assert c['definition_language_id'] == EN and c['nl_language'] == 'en'


def test_wrong_options_share_the_part_of_speech_and_never_a_gloss_term():
    db = FakeDB(_tables())
    items = [_item(100, _stored_v2()), _item(200, _stored_v2('為る'))]
    ds.localise(db, items, language_id=JA, nl_language_id=EN)
    noun, verb = items[0]['content'], items[1]['content']
    noun_wrong = [o for o in noun['options'] if o != noun['correct_answer']]
    verb_wrong = [o for o in verb['options'] if o != verb['correct_answer']]
    assert not any(o.startswith('to ') for o in noun_wrong)
    assert all(o.startswith('to ') for o in verb_wrong)
    assert verb['correct_answer'] == 'to do; to perform'
    # 'a person; someone' shares 'person' with the key: never offered as wrong.
    assert not any('someone' in o for o in noun_wrong)
    assert not any(o in ('a person',) for o in noun_wrong)            # the word's own other level


def test_rebuilding_is_deterministic_per_sense_and_language():
    a = [_item(100, _stored_v2())]
    b = [_item(100, _stored_v2())]
    ds.localise(FakeDB(_tables()), a, language_id=JA, nl_language_id=EN)
    ds.reset_cache()
    ds.localise(FakeDB(_tables()), b, language_id=JA, nl_language_id=EN)
    assert a[0]['content']['options'] == b[0]['content']['options']


def test_an_item_with_no_gloss_in_the_learners_language_is_dropped_not_shown():
    db = FakeDB(_tables())
    items = [_item(300, _stored_v2('犬')), _item(100, _stored_v2()),
             _item(55, {'q': 'cloze'}, exercise_type='cloze_completion')]
    assert ds.localise(db, items, language_id=JA, nl_language_id=EN) == 1
    assert [i['sense_id'] for i in items] == [100, 55]                  # order kept
    assert items[1]['content'] == {'q': 'cloze'}                        # other types untouched


def test_an_unrebuildable_item_already_in_the_learners_script_is_kept():
    # e.g. an English word's definitions for a learner whose language has no
    # gloss rows: still readable, so it stays.
    db = FakeDB({'dim_vocabulary': [], 'dim_word_senses': []})
    content = {'word': 'run', 'options': ['to move fast', 'to eat', 'to sleep', 'to sing'],
               'correct_definition': 'to move fast'}
    items = [_item(7, dict(content))]
    assert ds.localise(db, items, language_id=ZH, nl_language_id=EN) == 0
    assert items[0]['content'] == content


def test_content_already_in_the_learners_language_is_left_alone():
    db = FakeDB(_tables())
    content = {'word': '人間', 'options': ['w', 'x', 'y', 'z'], 'correct_answer': 'x',
               'definition_language_id': EN}
    items = [_item(100, dict(content))]
    ds.localise(db, items, language_id=JA, nl_language_id=EN)
    assert items[0]['content'] == content


def test_nothing_is_read_when_the_learner_reads_the_studied_language_or_none():
    db = FakeDB(_tables())
    items = [_item(100, _stored_v2())]
    before = copy.deepcopy(items)
    ds.localise(db, items, language_id=JA, nl_language_id=JA)
    ds.localise(db, items, language_id=JA, nl_language_id=None)
    assert items == before and db.calls == []


def test_a_failed_pool_load_drops_unreadable_items_rather_than_serving_them():
    class Broken(FakeDB):
        def table(self, name):
            if name == 'dim_vocabulary':
                raise RuntimeError('statement timeout')
            return super().table(name)

    items = [_item(100, _stored_v2())]
    assert ds.localise(Broken(_tables()), items, language_id=JA, nl_language_id=EN) == 1
    assert items == []


def test_the_pool_is_loaded_once_and_paged():
    db = FakeDB(_tables(extra_nouns=700, extra_verbs=0))     # > 1000 gloss rows: two pages
    ds.localise(db, [_item(100, _stored_v2())], language_id=JA, nl_language_id=EN)
    first = list(db.calls)
    ds.localise(db, [_item(100, _stored_v2())], language_id=JA, nl_language_id=EN)
    assert first.count('dim_vocabulary') >= 1 and first.count('dim_word_senses') >= 3
    # the second request reads only the items' own meanings
    assert db.calls[len(first):] == ['dim_word_senses']
    pool = ds.get_pool(db, JA, EN)
    assert len(pool.rows) == len([s for s in db.tables['dim_word_senses']
                                  if s['definition_language_id'] == EN])


def test_gloss_terms_normalise_the_listed_equivalents():
    assert ds.gloss_terms('a human; a person — the species') == {'human', 'person'}
    assert ds.gloss_terms('to do; to perform') == {'do', 'perform'}
    assert ds.gloss_terms('人；人間') == {'人', '人間'}


# ---------------------------------------------------------------------------
# Where items are served
# ---------------------------------------------------------------------------

def test_intro_drill_option_pool_comes_from_the_cached_pool():
    db = FakeDB(_tables())
    ds.get_pool(db, JA, EN)
    db.calls.clear()
    pool = intro_drill._distractor_pool(db, JA, EN, [5000, 5002], {5000})
    assert db.calls == []                                       # no query
    assert pool and all({'lemma', 'def', 'pos'} <= set(p) for p in pool)
    assert len({p['lemma'] for p in pool}) == len(pool)


def test_prestudy_exercises_carry_english_definition_options(monkeypatch):
    tables = _tables()
    tables['exercises'] = [{'id': 'd1', 'word_sense_id': 100, 'exercise_type': 'definition_match',
                            'ladder_level': 2, 'is_active': True, 'content_version': 0}]
    db = FakeDB(tables)

    def fake_hydrate(rows, language_id=None, **_k):
        for r in rows:
            r['content'] = _stored_v2()
    monkeypatch.setattr(store, 'hydrate', fake_hydrate)
    out = prestudy._load_exercises(db, [100], language_id=JA, nl_language_id=EN)
    c = out['100'][0]['c']
    assert c['correct_definition'].startswith('a human') and len(c['options']) == 4
    assert all(ds.script_family(o) == 'latin' for o in c['options'])


def test_practice_hydrate_step_localises_definition_items(monkeypatch):
    from services.practice_session_service import PracticeSessionService
    tables = _tables()
    db = FakeDB(tables)

    def fake_hydrate(items, **_k):
        for it in items:
            it['content'] = _stored_v2() if it['exercise_type'] == 'definition_match' else {'q': 1}
        return store.HydrationReport()
    monkeypatch.setattr(store, 'hydrate', fake_hydrate)
    svc = PracticeSessionService.__new__(PracticeSessionService)
    svc.db = db
    payload = {'items': [
        {'exercise_id': 'a', 'sense_id': 100, 'exercise_type': 'definition_match'},
        {'exercise_id': 'b', 'sense_id': 300, 'exercise_type': 'definition_match'},
        {'exercise_id': 'c', 'sense_id': 100, 'exercise_type': 'cloze_completion'},
    ]}
    svc._hydrate_items(payload, JA, nl_language_id=EN)
    assert [i['exercise_id'] for i in payload['items']] == ['a', 'c']   # 犬 has no English gloss
    assert payload['items'][0]['content']['correct_answer'].startswith('a human')
