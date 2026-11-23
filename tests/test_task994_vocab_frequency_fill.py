"""TASK-994: the dim_vocabulary.frequency_rank fill is sourced, guarded and reversible.

migrations/task994_vocab_frequency_fill.sql writes a Zipf score into rows whose
frequency_rank is NULL. These tests pin what a reviewer has to trust:

* every value is exactly what the app's own frequency function
  (services/vocabulary/frequency_service.get_zipf_score, wordfreq) gives for
  that lemma, so nothing is invented;
* the statement only writes NULL ranks on rows whose lemma/language are
  unchanged, and refuses to run unless the measured row count matches;
* the rollback names the same ids and only resets rows still holding the
  value the fill wrote;
* the very basic words from the bug report are in the fill.
"""

import re
from pathlib import Path

import pytest

from services.vocabulary.frequency_service import get_zipf_score

ROOT = Path(__file__).resolve().parents[1]
FORWARD = ROOT / 'migrations' / 'task994_vocab_frequency_fill.sql'
ROLLBACK = ROOT / 'migrations' / 'task994_vocab_frequency_fill_rollback.sql'
CODES = {1: 'zh', 2: 'en', 3: 'ja'}

_FWD_ROW = re.compile(r"^\s*\((\d+), (\d)::smallint, '((?:[^']|'')*)', (\d+\.\d\d)::real\),?$", re.M)
_RB_ROW = re.compile(r"^\s*\((\d+), (\d+\.\d\d)::real\),?$", re.M)


def _sql_without_comments(text: str) -> str:
    return '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('--'))


@pytest.fixture(scope='module')
def forward_rows():
    rows = [(int(i), int(lang), lemma.replace("''", "'"), float(z))
            for i, lang, lemma, z in _FWD_ROW.findall(FORWARD.read_text(encoding='utf-8'))]
    assert rows, 'no VALUES rows parsed from the forward migration'
    return rows


def test_expected_count_matches_the_values_list(forward_rows):
    text = FORWARD.read_text(encoding='utf-8')
    expected = int(re.search(r'v_expected constant integer := (\d+);', text).group(1))
    assert expected == len(forward_rows) == 770
    assert len({r[0] for r in forward_rows}) == len(forward_rows), 'duplicate ids'
    by_lang = {lang: sum(1 for r in forward_rows if r[1] == lang) for lang in CODES}
    assert by_lang == {1: 229, 2: 422, 3: 119}


@pytest.mark.requires('jieba', 'MeCab', 'ipadic')
def test_every_value_is_the_apps_own_wordfreq_score(forward_rows):
    mismatches = []
    for vid, lang, lemma, zipf in forward_rows:
        expected = get_zipf_score(lemma, CODES[lang])
        if expected is None or abs(expected - zipf) > 1e-9:
            mismatches.append((vid, lemma, zipf, expected))
    assert not mismatches, mismatches[:10]


# ja lemmas wordfreq splits into several tokens are scored by their parts with
# no compound penalty (zh compounds are divided by 10 per extra token), so the
# value reads far too common: 色ごと 4.77, 水のみ 4.99, バットレス 3.86, みず 5.53.
# Review 2026-11-17 left these NULL instead of writing an inflated rank.
JA_PART_SCORED_IDS = {22529, 24812, 24896, 24908, 24909, 24933, 24935, 24958,
                      24996, 25056, 25101, 32033}


@pytest.mark.requires('MeCab', 'ipadic')
def test_no_japanese_value_is_scored_from_its_parts(forward_rows):
    from wordfreq import tokenize
    split = [(vid, lemma) for vid, lang, lemma, _ in forward_rows
             if lang == 3 and len(tokenize(lemma, 'ja')) > 1]
    assert not split, split
    assert not JA_PART_SCORED_IDS & {r[0] for r in forward_rows}


@pytest.mark.requires('jieba', 'MeCab', 'ipadic')
def test_part_scored_japanese_compounds_would_be_inflated():
    # Pins the reason for the exclusion: if wordfreq ever starts penalising ja
    # compounds the exclusion can be revisited.
    from wordfreq import tokenize
    assert tokenize('色ごと', 'ja') == ['色', 'ごと']
    assert get_zipf_score('色ごと', 'ja') >= 4.5
    assert len(tokenize('更多', 'zh')) == 2
    assert get_zipf_score('更多', 'zh') < get_zipf_score('多', 'zh') - 1.0


def test_values_are_on_the_zipf_scale_of_the_column(forward_rows):
    # Stored range today is 0.11 .. 7.79; a rank-like integer would be a bug.
    assert all(0.0 < r[3] <= 8.0 for r in forward_rows)


@pytest.mark.parametrize('lang,lemma', [
    (1, '是'), (1, '都'), (1, '有'), (1, '不'), (1, '很'), (1, '人'),
    (3, 'する'), (3, 'ない'), (2, 'soon'),
])
def test_basic_words_from_the_report_are_filled_high(forward_rows, lang, lemma):
    hits = [r for r in forward_rows if r[1] == lang and r[2] == lemma]
    assert len(hits) == 1
    assert hits[0][3] >= 5.0


def test_forward_is_a_guarded_null_only_update():
    sql = _sql_without_comments(FORWARD.read_text(encoding='utf-8'))
    upper = sql.upper()
    for forbidden in ('DROP ', 'DELETE ', 'TRUNCATE', 'ALTER ', 'CREATE ', 'INSERT ', 'GRANT ', 'REVOKE '):
        assert forbidden not in upper, forbidden
    assert upper.count('UPDATE PUBLIC.DIM_VOCABULARY') == 1
    assert 'dv.frequency_rank IS NULL' in sql
    assert 'dv.lemma = f.lemma' in sql
    assert 'dv.language_id = f.language_id' in sql
    assert 'IF v_updated <> v_expected THEN' in sql and 'RAISE EXCEPTION' in sql


def test_rollback_resets_exactly_the_filled_values(forward_rows):
    text = ROLLBACK.read_text(encoding='utf-8')
    rb = {int(i): float(z) for i, z in _RB_ROW.findall(text)}
    assert rb == {r[0]: r[3] for r in forward_rows}
    sql = _sql_without_comments(text)
    assert 'SET frequency_rank = NULL' in sql
    assert 'dv.frequency_rank = f.zipf' in sql
    upper = sql.upper()
    for forbidden in ('DROP ', 'DELETE ', 'TRUNCATE', 'ALTER ', 'CREATE '):
        assert forbidden not in upper, forbidden
