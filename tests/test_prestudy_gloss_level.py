"""services.prestudy._load_senses: the cross-language gloss is taken at the
linked sense's own definition level (TASK-994 / INT-1).

Each meaning is stored once per definition level ('simple' and 'standard' are
both sense_rank 1). Keying the gloss on (vocab_id, sense_rank) alone kept
whichever level the database returned last, and when a test linked both
levels of one meaning only one of them got a gloss.
"""

from services import prestudy


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    """Applies in_/eq filters to the table rows (select is ignored)."""

    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def in_(self, col, values):
        vals = set(values)
        return _Query([r for r in self._rows if r.get(col) in vals])

    def eq(self, col, value):
        return _Query([r for r in self._rows if r.get(col) == value])

    def execute(self):
        return _Result(list(self._rows))


class _DB:
    def __init__(self, senses):
        self._senses = senses

    def table(self, name):
        assert name == 'dim_word_senses'
        return _Query(self._senses)


ZH, EN = 1, 2
VOCAB = {'lemma': '是', 'part_of_speech': 'verb', 'frequency_rank': 7.17,
         'reading': None, 'language_id': ZH}


def _row(sid, level, lang, definition):
    return {'id': sid, 'vocab_id': 500, 'sense_rank': 1, 'definition_level': level,
            'definition_language_id': lang, 'definition': definition,
            'example_sentence': None, 'pronunciation': 'shì (shi4)', 'dim_vocabulary': VOCAB}


def _rows(english_order):
    native = [_row(1, 'standard', ZH, '表示判断'), _row(2, 'simple', ZH, '就是')]
    english = {
        'standard': _row(3, 'standard', EN, 'to be; used to say what something is'),
        'simple': _row(4, 'simple', EN, 'is'),
    }
    return native + [english[k] for k in english_order]


def test_linked_standard_sense_gets_the_standard_gloss_even_when_simple_comes_last():
    db = _DB(_rows(['standard', 'simple']))
    out = prestudy._load_senses(db, [1], EN)
    assert out['1']['glosses'][str(EN)]['def'] == 'to be; used to say what something is'


def test_linked_simple_sense_gets_the_simple_gloss_even_when_standard_comes_last():
    db = _DB(_rows(['simple', 'standard']))
    out = prestudy._load_senses(db, [2], EN)
    assert out['2']['glosses'][str(EN)]['def'] == 'is'


def test_both_levels_linked_each_get_their_own_gloss():
    for order in (['standard', 'simple'], ['simple', 'standard']):
        out = prestudy._load_senses(_DB(_rows(order)), [1, 2], EN)
        assert out['1']['glosses'][str(EN)]['def'] == 'to be; used to say what something is'
        assert out['2']['glosses'][str(EN)]['def'] == 'is'


def test_falls_back_to_another_level_when_the_linked_level_has_no_gloss():
    out = prestudy._load_senses(_DB(_rows(['standard'])), [2], EN)
    assert out['2']['glosses'][str(EN)]['def'] == 'to be; used to say what something is'


def test_no_gloss_language_or_same_language_reads_no_gloss():
    db = _DB(_rows(['standard', 'simple']))
    assert set(prestudy._load_senses(db, [1], None)['1']['glosses']) == {str(ZH)}
    assert set(prestudy._load_senses(db, [1], ZH)['1']['glosses']) == {str(ZH)}
