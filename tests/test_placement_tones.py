"""services/placement_tones: zh pinyin parse, re-mark, numbered form and tone variants.

TASK-1092 (ADR-060, tech §2 rule 4) and the TASK-1074 / TASK-1082 numbered-form fixtures.
The SQL mirrors (migrations/calibration_zh_normaliser_fix.sql, migrations/calibration_zh_tones.sql)
are compared with this module on real data by scripts/verify_zh_tone_variants.py; here the
rules are pinned on small cases.
"""

import hashlib
import itertools
import re
from pathlib import Path

import pytest

from services import placement_tones as pt

MIGRATIONS = Path(__file__).resolve().parent.parent / 'migrations'

# A small inventory in the shape calibration_zh_tone_inventory stores (base -> full tones).
INV = {
    'xie': {1, 2, 3, 4}, 'zi': {1, 3, 4},
    'hen': {2, 3, 4}, 'hao': {2, 3, 4},
    'dong': {1, 3, 4}, 'xi': {1, 2, 3, 4},
    'yi': {1, 2, 3, 4}, 'yang': {1, 2, 3, 4},
    'bu': {1, 2, 3, 4}, 'shi': {1, 2, 3, 4},
    'chang': {1, 2, 3, 4}, 'zhang': {1, 3, 4},
    'lu:': {3, 4}, 'nu:': {3}, 'lu:e': {4}, 'er': {2, 3, 4},
    'ma': set(), 'men': set(), 'ren': {2, 3, 4},
    'xin': {1, 4}, 'gan': {1, 3, 4}, 'jiu': {1, 3, 4}, 'qian': {1, 2, 3, 4},
}


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('token, base, tone', [
    ('mā', 'ma', 1), ('má', 'ma', 2), ('mǎ', 'ma', 3), ('mà', 'ma', 4), ('ma', 'ma', 5),
    ('lǜ', 'lu:', 4), ('nǚ', 'nu:', 3), ('lüè', 'lu:e', 4), ('lü', 'lu:', 5),
    ('Běi', 'bei', 3),
    ('ma\u0304', 'ma', 1),                      # decomposed mark
])
def test_parse_syllable(token, base, tone):
    s = pt.parse_syllable(token)
    assert (s.base, s.tone) == (base, tone)


@pytest.mark.parametrize('token', ['yíhuìr', 'yuan2', '你', 'ok!', ''])
def test_parse_syllable_rejects_non_syllables(token):
    s = pt.parse_syllable(token)
    assert s.base is None and s.tone == pt.NOT_A_SYLLABLE


def test_parse_drops_the_numbered_part_and_keeps_order():
    syls = pt.parse('bàn fǎ (ban4 fa3)')
    assert [(s.text, s.base, s.tone) for s in syls] == [('bàn', 'ban', 4), ('fǎ', 'fa', 3)]
    assert pt.display_form('bàn fǎ (ban4 fa3)') == 'bàn fǎ'
    assert pt.parse("xī'ān") == [pt.parse_syllable('xī'), pt.parse_syllable('ān')]
    assert pt.parse(None) == [] and pt.parse('') == []


def test_reading_key_ignores_separators_and_the_numbered_part():
    assert pt.reading_key('dōng xi') == ('dong xi', (1, 5))
    assert pt.reading_key('dōng xi (dong1 xi5)') == pt.reading_key('dōng-xi')


# ---------------------------------------------------------------------------
# mark_syllable: the standard mark rule
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('base, tone, marked', [
    ('hao', 3, 'hǎo'),     # a
    ('mei', 2, 'méi'),     # e
    ('lu:e', 4, 'lüè'),    # e, ü kept
    ('gou', 3, 'gǒu'),     # o of "ou"
    ('liu', 2, 'liú'),     # last vowel
    ('gui', 4, 'guì'),     # last vowel
    ('lu:', 4, 'lǜ'),      # ü re-marked
    ('nu:', 3, 'nǚ'),
    ('lu:', 1, 'lǖ'), ('lu:', 2, 'lǘ'),
    ('er', 2, 'ér'),
    ('zhuang', 1, 'zhuāng'), ('xiong', 2, 'xióng'),
    ('ng', 2, 'ńg'),       # no vowel: first m/n
    ('ma', 5, 'ma'), ('lu:', 5, 'lü'),
])
def test_mark_syllable(base, tone, marked):
    assert pt.mark_syllable(base, tone) == marked


def test_mark_then_parse_round_trips():
    for base in ['ba', 'bai', 'bao', 'bei', 'bian', 'biao', 'bie', 'bing', 'cuo', 'diu', 'dui',
                 'er', 'gou', 'guai', 'huang', 'jiong', 'jue', 'lu:', 'lu:e', 'nu:', 'nu:e',
                 'qu', 'shuo', 'xue', 'yu', 'yuan', 'zhi', 'zhuang', 'o', 'e', 'a']:
        for tone in (1, 2, 3, 4, 5):
            s = pt.parse_syllable(pt.mark_syllable(base, tone))
            assert (s.base, s.tone) == (base, tone)


# ---------------------------------------------------------------------------
# to_numbered (TASK-1074 SQL fixtures, TASK-1082)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('reading, numbered', [
    ('yuán xíng', 'yuan2 xing2'),
    ('bēi zi', 'bei1 zi5'),
    ('lǜ shī', 'lü4 shi1'),        # ü kept, as the stored numbered parts write it ('lü4')
    ('nǚ ér', 'nü3 er2'),
    ('ma', 'ma5'),
    ('yíhuìr', 'yi2 huir4'),      # one token, two syllables: the digit goes after each coda
    ('diǎnr', 'dianr3'),
    ('xīngān', 'xin1 gan1'),      # n before a vowel starts the next syllable
    ('Běi Jīng', 'bei3 jing1'),
    ('bàn fǎ (ban4 fa3)', 'ban4 fa3'),   # the numbered part is ignored; derived from the marks
    ('yuan2 xing2', 'yuan2 xing2'),      # already numbered
    ("xī'ān", 'xi1 an1'),
    ('', ''),
])
def test_to_numbered(reading, numbered):
    assert pt.to_numbered(reading) == numbered


def test_to_numbered_matches_the_sql_fixtures_in_the_migration_header():
    sql = (MIGRATIONS / 'calibration_zh_normaliser_fix.sql').read_text(encoding='utf-8')
    fixtures = re.findall(r"'([^'\n]+)'\s+->\s+'([a-zü0-9]+)'", sql)
    assert len(fixtures) >= 4
    for reading, normalised in fixtures:
        assert pt.to_numbered(reading).replace(' ', '') == normalised, reading


# ---------------------------------------------------------------------------
# build_inventory
# ---------------------------------------------------------------------------
def test_build_inventory():
    inv = pt.build_inventory(['hěn hǎo (hen3 hao3)', 'hào', 'mā ma', 'yíhuìr', None, 'lǜ'])
    assert inv == {'hen': {3}, 'hao': {3, 4}, 'ma': {1}, 'lu:': {4}}
    assert pt.build_inventory(['ma']) == {'ma': frozenset()}   # neutral only: listed, no tones


# ---------------------------------------------------------------------------
# variants: rule 4
# ---------------------------------------------------------------------------
def _all_attested(variant, inv):
    return all(s.tone not in pt.FULL_TONES or s.tone in inv.get(s.base, ())
               for s in pt.parse(variant))


def test_xie_uses_only_attested_tones_and_never_itself():
    assert set(pt.variants('xiě', '写', INV, ['xiě'])) == {'xiē', 'xié', 'xiè'}
    assert pt.variants('xiě', '写', {'xie': {3, 4}}, ['xiě']) == ['xiè']
    assert pt.variants('xiě', '写', {'xie': {3}}, ['xiě']) == []
    assert pt.variants('xiě', '写', {}, []) == []   # base not in the inventory: no change


def test_hen_hao_excludes_the_sandhi_form_only():
    out = pt.variants('hěn hǎo', '很好', INV, ['hěn hǎo'])
    assert 'hén hǎo' not in out                       # 3 -> 2 before 3 only: sandhi
    assert 'hěn hǎo' not in out
    assert {'hén háo', 'hén hào', 'hèn hǎo', 'hěn háo'} <= set(out)
    assert len(out) == 3 * 3 - 2


def test_sandhi_run_of_three_third_tones():
    inv = {'zhan': {2, 3}, 'lan': {2, 3}, 'guan': {2, 3}}
    out = pt.variants('zhǎn lǎn guǎn', '展览馆', inv, [])
    assert 'zhán lán guǎn' not in out and 'zhán lǎn guǎn' not in out and 'zhǎn lán guǎn' not in out
    assert 'zhǎn lǎn guán' in out                     # the last syllable has no tone-3 after it


def test_neutral_syllable_keeps_its_tone_and_nothing_becomes_neutral():
    out = pt.variants('dōng xi', '东西', INV, ['dōng xi', 'dōng xī'])
    assert set(out) == {'dǒng xi', 'dòng xi'}
    out = pt.variants('rén men', '人们', INV, [])
    assert set(out) == {'rěn men', 'rèn men'}
    assert all(pt.parse(v)[0].tone != 5 for v in pt.variants('xiě', '写', INV, []))


@pytest.mark.parametrize('reading, lemma, fixed', [
    ('yí yàng', '一样', 'yí'),
    ('bú shì', '不是', 'bú'),
    ('shí yī', '十一', 'yī'),
])
def test_yi_and_bu_never_change(reading, lemma, fixed):
    out = pt.variants(reading, lemma, INV, [reading])
    assert out
    pos = lemma.index('一' if '一' in lemma else '不')
    assert all(pt.parse(v)[pos].text == fixed for v in out)


def test_a_lone_yi_or_bu_has_no_variant():
    assert pt.variants('yī', '一', INV, ['yī']) == []
    assert pt.variants('bù', '不', INV, ['bù']) == []


def test_yi_changes_when_the_lemma_does_not_align():
    # 一点儿: three characters, two syllables written 'yì diǎn' here -> no alignment
    out = pt.variants('yì diǎn', '一点儿', {'yi': {1, 2, 4}, 'dian': {3}}, [])
    assert set(out) == {'yī diǎn', 'yí diǎn'}


def test_polyphones_never_return_another_reading_of_the_lemma():
    out = pt.variants('hǎo', '好', INV, ['hǎo', 'hào'])
    assert out == ['háo']
    out = pt.variants('cháng', '长', INV, ['cháng', 'zhǎng'])
    assert set(out) == {'chāng', 'chǎng', 'chàng'}
    out = pt.variants('cháng', '长', INV, ['cháng', 'chàng (chang4)'])
    assert set(out) == {'chāng', 'chǎng'}


# Character readings (calibration_zh_char_readings): 好 is listed only as hǎo, but 爱好 ài hào
# attests 好 hào; 因为 yīn wèi attests 为 wèi; 只是 zhǐ shì attests 只 zhǐ.
DICT = [('好', 'hǎo'), ('爱好', 'ài hào (ai4 hao4)'), ('为', 'wéi'), ('因为', 'yīn wèi'),
        ('只', 'zhī'), ('只是', 'zhǐ shì'), ('长', 'cháng'), ('长大', 'zhǎng dà'),
        ('一会儿', 'yíhuìr'), ('啤酒', 'pí jiǔ ba'), ('东西', 'dōng xi')]
CHARS = pt.build_char_readings(DICT)


def test_build_char_readings_maps_aligned_characters_to_their_syllables():
    assert CHARS['好'] == {('hao', 3), ('hao', 4)}
    assert CHARS['为'] == {('wei', 2), ('wei', 4)}
    assert CHARS['只'] == {('zhi', 1), ('zhi', 3)}
    assert CHARS['长'] == {('chang', 2), ('zhang', 3)}
    assert CHARS['西'] == {('xi', 5)}                       # neutral readings are listed too
    assert '会' not in CHARS and '儿' not in CHARS           # 一会儿 / yíhuìr: not aligned
    assert '啤' not in CHARS and '酒' not in CHARS           # 2 characters, 3 syllables
    assert pt.build_char_readings([(None, 'hǎo'), ('好', None), ('好', '')]) == {}


def test_single_character_lemma_never_yields_a_reading_its_character_has():
    assert set(pt.variants('hǎo', '好', INV, ['hǎo'])) == {'háo', 'hào'}
    assert pt.variants('hǎo', '好', INV, ['hǎo'], char_readings=CHARS) == ['háo']
    assert 'wèi' not in pt.variants('wéi', '为', {'wei': {1, 2, 3, 4}}, ['wéi'], char_readings=CHARS)
    assert 'zhǐ' not in pt.variants('zhī', '只', INV | {'zhi': {1, 2, 3, 4}}, ['zhī'],
                                    char_readings=CHARS)
    # another base of the same character changes nothing (zhǎng is never a variant of cháng)
    assert set(pt.variants('cháng', '长', INV, ['cháng'], char_readings=CHARS)) == {
        'chāng', 'chǎng', 'chàng'}


def test_character_readings_do_not_restrict_multi_character_lemmas():
    out = pt.variants('hǎo rén', '好人', INV, ['hǎo rén'], char_readings=CHARS)
    assert 'hào rén' in out


def test_u_umlaut_syllables_keep_the_umlaut_and_re_mark():
    assert pt.variants('lǜ', '绿', INV, ['lǜ']) == ['lǚ']
    assert pt.variants('nǚ ér', '女儿', INV, ['nǚ ér']) == sorted(
        ['nǚ ěr', 'nǚ èr'], key=lambda v: hashlib.md5(
            ''.join(str(s.tone) for s in pt.parse(v)).encode()).hexdigest())
    assert pt.variants('lüè', '略', {'lu:e': {3, 4}}, []) == ['lüě']


def test_separators_and_unchanged_tokens_keep_their_text():
    out = pt.variants("xī'ān", '西安', {'xi': {1, 2}, 'an': {1}}, [])
    assert out == ["xí'ān"]
    out = pt.variants('bàn fǎ (ban4 fa3)', '办法', {'ban': {3, 4}, 'fa': {3}}, [])
    assert out == ['bǎn fǎ']                          # the numbered part never appears


def test_non_syllable_tokens_are_kept():
    assert pt.variants('yíhuìr', '一会儿', INV, []) == []
    assert set(pt.variants('yíhuìr shì', None, INV, [])) == {'yíhuìr shī', 'yíhuìr shí', 'yíhuìr shǐ'}


def test_cap_order_and_attestation():
    reading = 'hěn jiǔ yǐ qián'
    full = pt.variants(reading, '很久以前', INV, [reading], cap=10_000)
    capped = pt.variants(reading, '很久以前', INV, [reading])
    assert len(full) > pt.VARIANT_CAP and len(capped) == pt.VARIANT_CAP
    assert capped == full[:pt.VARIANT_CAP]
    digits = [''.join(str(s.tone) for s in pt.parse(v)) for v in full]
    assert digits == sorted(digits, key=lambda d: (hashlib.md5(d.encode()).hexdigest(), d))
    assert len(set(full)) == len(full)
    assert all(_all_attested(v, INV) for v in full)
    # every combination of attested tones minus the original and the sandhi-only ones
    opts = [sorted(INV[b]) for b in ('hen', 'jiu', 'yi', 'qian')]
    assert len(full) == len(list(itertools.product(*opts))) - 1 - 1   # hén jiǔ yǐ qián is sandhi
    assert pt.variants(reading, '很久以前', INV, [], cap=0) == []


def test_a_variant_never_equals_the_key_or_an_own_reading():
    for reading, lemma in [('xiě zì', '写字'), ('hěn hǎo', '很好'), ('yí yàng', '一样')]:
        out = pt.variants(reading, lemma, INV, [reading])
        keys = {pt.reading_key(v) for v in out}
        assert pt.reading_key(reading) not in keys


def test_no_lemma_means_no_alignment_and_no_own_readings():
    assert set(pt.variants('yí', None, INV)) == {'yī', 'yǐ', 'yì'}
