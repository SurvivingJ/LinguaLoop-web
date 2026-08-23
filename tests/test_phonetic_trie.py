"""Unit tests for the generic PhoneticTrie mechanics.

Deterministic, hand-built tries only -- no JMdict download, no network, no
Supabase. The full-dictionary behavior (real ja words, TASK-735's
fabrication/accent cases) is covered separately by
scripts/validate_ja_mora_trie.py, which needs the built artifact and isn't
a unit test. This file exists to pin down the trie's own contract so a
future change to trie.py can't silently break the guarantee the whole ja
mora-trie design leans on.
"""

from services.vocabulary_ladder.phonetic_trie.ja_mora import to_morae
from services.vocabulary_ladder.phonetic_trie.trie import PhoneticTrie


def _build(entries):
    """entries: list of (unit_sequence, surface_form)."""
    return PhoneticTrie().build(entries)


def test_exact_match_returns_homophones():
    trie = _build([
        (['a', 'b'], 'word1'),
        (['a', 'b'], 'word2'),  # true homophone of word1
        (['a', 'c'], 'word3'),
    ])
    assert set(trie.exact_matches(['a', 'b'])) == {'word1', 'word2'}
    assert trie.exact_matches(['a', 'c']) == ['word3']
    assert trie.exact_matches(['x', 'y']) == []


def test_one_substitution_neighbor_basic():
    trie = _build([
        (['a', 'b'], 'target'),
        (['a', 'c'], 'neighbor_pos1'),
        (['x', 'b'], 'neighbor_pos0'),
        (['a', 'b', 'c'], 'different_length'),  # not a neighbor: extra unit
    ])
    neighbors = {n.surface_form: n for n in trie.one_substitution_neighbors(['a', 'b'])}
    assert set(neighbors) == {'neighbor_pos0', 'neighbor_pos1'}
    assert neighbors['neighbor_pos0'].position == 0
    assert neighbors['neighbor_pos0'].original_unit == 'a'
    assert neighbors['neighbor_pos0'].substituted_unit == 'x'
    assert neighbors['neighbor_pos1'].position == 1
    assert neighbors['neighbor_pos1'].substituted_unit == 'c'


def test_one_substitution_never_returns_the_target_itself():
    """A word cannot be its own one-mora neighbor -- inserting the target
    twice under different surface forms must not produce a self-hit.
    """
    trie = _build([
        (['a', 'b'], 'target'),
        (['a', 'b'], 'homophone_of_target'),
    ])
    neighbors = trie.one_substitution_neighbors(['a', 'b'])
    assert neighbors == []


def test_structural_guarantee_same_reading_is_unreachable():
    """The property the ja mora-trie design depends on: a 0-substitution
    (same-reading) pair can never be produced by the 1-substitution query.
    This is what makes an accent-only collision like 機械/機会 -- two
    different words, identical reading -- structurally impossible to
    surface as a "one mora different" distractor.
    """
    trie = _build([
        (list('kikai'), '機械'),
        (list('kikai'), '機会'),  # same reading, different word
        (list('kikae'), '着替え'),  # a genuine one-substitution neighbor
    ])
    neighbor_surfaces = {n.surface_form for n in trie.one_substitution_neighbors(list('kikai'))}
    assert '機会' not in neighbor_surfaces
    assert '機械' not in neighbor_surfaces
    assert '着替え' in neighbor_surfaces


def test_same_node_identity_check():
    trie = _build([(['a', 'b'], 'w1'), (['a', 'c'], 'w2')])
    assert trie.same_node(['a', 'b'], ['a', 'b']) is True
    assert trie.same_node(['a', 'b'], ['a', 'c']) is False
    assert trie.same_node(['a', 'b'], ['z', 'z']) is False  # not in trie at all


def test_node_and_entry_counts():
    trie = _build([(['a', 'b'], 'w1'), (['a', 'b'], 'w2'), (['a', 'c'], 'w3')])
    # root + a + (a,b) + (a,c) = 4 nodes; a and (a,b)/(a,c) shared prefix collapses.
    assert trie.node_count == 4
    assert trie.entry_count == 3  # 3 inserts, even though 2 share a node


def test_duplicate_surface_form_not_double_stored():
    trie = _build([(['a'], 'w1'), (['a'], 'w1')])
    assert trie.exact_matches(['a']) == ['w1']


def test_save_and_load_roundtrip(tmp_path):
    trie = _build([(['a', 'b'], 'word1'), (['a', 'c'], 'word2')])
    path = tmp_path / 'trie.pkl'
    trie.save(str(path))
    loaded = PhoneticTrie.load(str(path))
    assert loaded.node_count == trie.node_count
    assert loaded.entry_count == trie.entry_count
    assert {n.surface_form for n in loaded.one_substitution_neighbors(['a', 'b'])} == {'word2'}


# --- ja_mora.to_morae ------------------------------------------------------

def test_to_morae_default_one_kana_one_mora():
    assert to_morae('むかし') == ['む', 'か', 'し']


def test_to_morae_youon_fuses_with_preceding_kana():
    assert to_morae('きゃく') == ['きゃ', 'く']
    assert to_morae('しゅくだい') == ['しゅ', 'く', 'だ', 'い']


def test_to_morae_choon_is_its_own_mora():
    assert to_morae('ビール') == ['ビ', 'ー', 'ル']


def test_to_morae_sokuon_is_its_own_mora():
    assert to_morae('ぶっか') == ['ぶ', 'っ', 'か']


def test_to_morae_katakana_small_vowel_loanword_combo():
    # フォーク (fork): フォ is one mora (small ォ fuses with フ), then ー, ク.
    assert to_morae('フォーク') == ['フォ', 'ー', 'ク']


def test_to_morae_empty_string():
    assert to_morae('') == []
