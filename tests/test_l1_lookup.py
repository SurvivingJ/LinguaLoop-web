"""Unit tests for services.vocabulary_ladder.l1_lookup.

Uses a hand-built trie (monkeypatched in place of the real ~600k-node ja
artifact) and stubbed wordfreq/tier lookups, so these run fast and
deterministically without the built pickle or a network dependency. The
built-artifact behavior against real ja words is covered separately by
scripts/validate_ja_mora_trie.py.
"""

import pytest

from services.vocabulary_ladder import l1_lookup
from services.vocabulary_ladder.phonetic_trie.trie import PhoneticTrie


def _fake_trie():
    """A trie mimicking the 昔 case, plus a self-collision-via-alt-reading
    case and a too-rare candidate, using ASCII stand-ins so intent is easy
    to read without relying on the reader's ja literacy.
    """
    return PhoneticTrie().build([
        (['m', 'u', 'k', 'a', 'shi'], '昔'),        # target
        (['m', 'u', 'k', 'a', 'e'], '迎え'),         # real one-mora neighbor (pos 4)
        (['m', 'u', 'k', 'a', 'de'], '百足'),        # another real neighbor (pos 4)
        (['m', 'u', 'k', 'a', 'go'], '零余子'),      # a rare candidate -- filtered by tier floor (pos 4)
        (['x', 'u', 'k', 'a', 'shi'], '別語'),       # a 4th real neighbor (pos 0)
        (['m', 'u', 'k', 'o', 'de'], '向こうし'),    # 2 positions different -- NOT a valid neighbor
        (['m', 'i', 'k', 'a', 'shi'], '昔'),         # 昔's OWN alternate reading (pos 1) -- self-collision
    ])


@pytest.fixture(autouse=True)
def _patch_registry(monkeypatch):
    monkeypatch.setitem(
        l1_lookup._TRIE_REGISTRY, 3,
        (l1_lookup._JA_TRIE_PATH, lambda reading: list(reading.split('-')), 'ja'),
    )
    monkeypatch.setattr(l1_lookup, '_get_trie', lambda language_id, path: _fake_trie())


def _tokenized_reading(units):
    return '-'.join(units)


def test_build_candidates_excludes_self_collision_via_alt_reading(monkeypatch):
    monkeypatch.setattr(l1_lookup, 'zipf_frequency', lambda word, lang: 5.0)  # nothing filtered by tier
    result = l1_lookup.build_candidates(
        '昔', _tokenized_reading(['m', 'u', 'k', 'a', 'shi']), language_id=3,
    )
    assert result is not None
    assert '昔' not in result['candidates']
    assert set(result['candidates']) >= {'迎え', '百足'}


def test_build_candidates_applies_tier_floor(monkeypatch):
    scores = {'迎え': 5.0, '百足': 5.0, '別語': 5.0, '零余子': 0.5}
    monkeypatch.setattr(l1_lookup, 'zipf_frequency', lambda word, lang: scores.get(word, 5.0))
    monkeypatch.setattr(l1_lookup, 'profile_for_tier', lambda tier: {'hard_floor': 1.0})
    result = l1_lookup.build_candidates(
        '昔', _tokenized_reading(['m', 'u', 'k', 'a', 'shi']), language_id=3,
    )
    assert result is not None
    assert '零余子' not in result['candidates']  # below the floor
    assert set(result['candidates']) == {'迎え', '百足', '別語'}


def test_build_candidates_does_not_punish_wordfreq_coverage_gaps(monkeypatch):
    """A real candidate wordfreq has no entry for (score 0.0) must not be
    dropped -- 0.0 means "unknown to the corpus", not "known to be rare"
    (the same distinction tier_gate.py's own docstring draws).
    """
    monkeypatch.setattr(l1_lookup, 'zipf_frequency', lambda word, lang: 0.0)
    monkeypatch.setattr(l1_lookup, 'profile_for_tier', lambda tier: {'hard_floor': 3.0})
    result = l1_lookup.build_candidates(
        '昔', _tokenized_reading(['m', 'u', 'k', 'a', 'shi']), language_id=3,
    )
    assert result is not None
    assert set(result['candidates']) >= {'迎え', '百足', '零余子'}


def test_build_candidates_returns_none_below_three_survivors(monkeypatch):
    # Everything but one candidate filtered out by the floor -> < 3 left.
    scores = {'迎え': 5.0}
    monkeypatch.setattr(l1_lookup, 'zipf_frequency', lambda word, lang: scores.get(word, 0.5))
    monkeypatch.setattr(l1_lookup, 'profile_for_tier', lambda tier: {'hard_floor': 1.0})
    result = l1_lookup.build_candidates(
        '昔', _tokenized_reading(['m', 'u', 'k', 'a', 'shi']), language_id=3,
    )
    assert result is None


def test_build_candidates_unsupported_language_returns_none():
    result = l1_lookup.build_candidates('word', 'reading', language_id=999)
    assert result is None


def test_build_candidates_empty_reading_returns_none():
    assert l1_lookup.build_candidates('昔', '', language_id=3) is None
    assert l1_lookup.build_candidates('', 'むかし', language_id=3) is None


def test_explanation_present_for_target_and_each_candidate(monkeypatch):
    monkeypatch.setattr(l1_lookup, 'zipf_frequency', lambda word, lang: 5.0)
    result = l1_lookup.build_candidates(
        '昔', _tokenized_reading(['m', 'u', 'k', 'a', 'shi']), language_id=3,
        definition='a long time ago',
    )
    assert '昔' in result['explanations']
    assert 'a long time ago' in result['explanations']['昔']
    for surface in result['candidates']:
        assert result['explanations'][surface]  # non-empty


# --- contrast classification (used only for explanation prose) ------------

def test_classify_contrast_choon():
    assert l1_lookup._classify_contrast('う', 'ー') == '長音（のばす音）の有無'


def test_classify_contrast_sokuon():
    assert l1_lookup._classify_contrast('か', 'っ') == '促音（つまる音）の有無'


def test_classify_contrast_hatsuon():
    assert l1_lookup._classify_contrast('し', 'ん') == '撥音「ん」の有無'


def test_classify_contrast_dakuten():
    assert l1_lookup._classify_contrast('か', 'が') == '清濁・半濁音の対立'
    assert l1_lookup._classify_contrast('きゃ', 'ぎゃ') == '清濁・半濁音の対立'


def test_classify_contrast_default():
    assert l1_lookup._classify_contrast('む', 'ひ') == '一部の音の違い'
