"""Prestudy sense readings: a tone-marked-only zh reading gains its numbered part (vocab-placement E17)."""
from services.prestudy import _with_zh_numbered


def test_zh_reading_gains_numbered_part():
    assert _with_zh_numbered('mù tou', 1) == 'mù tou (mu4 tou5)'
    assert _with_zh_numbered('lǜ shī', 1) == 'lǜ shī (lü4 shi1)'


def test_unchanged_cases():
    assert _with_zh_numbered('mù tou (mu4 tou5)', 1) == 'mù tou (mu4 tou5)'
    assert _with_zh_numbered('かんがえ', 3) == 'かんがえ'
    assert _with_zh_numbered(None, 1) is None
    assert _with_zh_numbered('', 1) == ''
    assert _with_zh_numbered('12', 1) == '12'
