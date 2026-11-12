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


from services.vocabulary.pos import CANONICAL_POS, normalize_pos  # noqa: E402


@pytest.mark.parametrize('tag,expected', CASES['normalize_pos'])
def test_normalize_pos(tag, expected):
    assert normalize_pos(tag) == expected


def test_sense_generator_legends_are_standard():
    from services.vocabulary.sense_generator import POS_LEGENDS
    for legend in POS_LEGENDS.values():
        assert set(legend.values()) <= set(CANONICAL_POS)


def test_every_live_tag_seen_on_2026_11_11_is_mapped():
    live = ('noun verb n v adjective 名词 动词 adverb 形容词 a pronoun l conjunction d nr 副词 '
            'measure_word vn ns preposition i particle nz nrt 情态动词 vg numeral ng nt idiom 连词 '
            '代词 ad an 介词 叹词 NOUN ADJ VERB ADV phrase 名詞 動詞 形状詞 副詞 形容詞 auxiliary '
            '接尾辞 代名詞').split()
    unmapped = [t for t in live if normalize_pos(t) == 'other' and t != '接尾辞']
    assert unmapped == []


def test_sql_mapping_matches_python_table():
    """migrations/standardise_part_of_speech.sql's CASE is generated from
    services/vocabulary/pos.py _TAGS; this keeps the two in step."""
    import re
    from pathlib import Path
    from services.vocabulary.pos import _TAGS
    sql = (Path(__file__).parent.parent / 'migrations' / 'standardise_part_of_speech.sql').read_text('utf-8')
    found = {canon: [t.replace("''", "'") for t in re.findall(r"'((?:[^']|'')*)'", arr)]
             for arr, canon in re.findall(r"WHEN t = ANY \(ARRAY\[(.*?)\]\) THEN '(\w+)'", sql)}
    assert found == {k: list(v) for k, v in _TAGS.items()}
    check = re.search(r"part_of_speech = ANY \(ARRAY\[(.*?)\]\)\) NOT VALID", sql).group(1)
    assert tuple(re.findall(r"'(\w+)'", check)) == CANONICAL_POS


def test_pos_hint_prefers_the_original_tag():
    from services.vocabulary.pos import pos_hint
    assert pos_hint({'part_of_speech': 'noun', 'part_of_speech_raw': '名詞'}) == '名詞'
    assert pos_hint({'part_of_speech': 'noun'}) == 'noun'
    assert pos_hint(None) == ''


def _gen(lang):
    from unittest.mock import MagicMock
    from services.vocabulary.sense_generator import SenseGenerator
    gen = SenseGenerator.__new__(SenseGenerator)
    gen._db = MagicMock()
    gen._pos_legend = {1: 'noun', 0: 'other'}
    gen._language_code = lang
    return gen


def test_sense_generator_label_replaces_the_tokenizer_guess_for_chinese():
    gen = _gen('zh')
    gen._maybe_set_pos(42, 1)
    q = gen._db.table.return_value.update
    q.assert_called_once_with({'part_of_speech': 'noun'})
    assert q.return_value.eq.return_value.or_.call_args.args == (
        'part_of_speech.is.null,part_of_speech.eq.,part_of_speech.neq.noun',)
    gen._db.reset_mock()
    gen._maybe_set_pos(42, 0)          # 'other' never overwrites
    gen._db.table.assert_not_called()


def test_sense_generator_only_fills_blanks_for_japanese_and_english():
    for lang in ('ja', 'en'):
        gen = _gen(lang)
        gen._maybe_set_pos(42, 1)
        q = gen._db.table.return_value.update
        assert q.return_value.eq.return_value.or_.call_args.args == (
            'part_of_speech.is.null,part_of_speech.eq.',)
