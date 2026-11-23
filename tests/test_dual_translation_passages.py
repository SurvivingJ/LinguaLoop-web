"""Unit tests for the dual-translation passage helpers (TASK-603).

Pure functions, no DB. The whole-transcript builder these tests used to cover
(segmentation, windowing, dedupe, whole-passage L1 references) had no
production caller and was deleted; sentence segmentation is tested against
its only implementation in tests/test_sentence_refs.py. Primed-window selection
is covered by tests/test_window_selector.py and
tests/test_sentence_ref_floor_override.py.
"""

import pytest

from services.dual_translation import passage_builder as pb


# ---------------------------------------------------------------------------
# difficulty_to_age_tier
# ---------------------------------------------------------------------------

class TestDifficultyToAgeTier:

    @pytest.mark.parametrize('difficulty,expected', [
        # Bands mirror dim_complexity_tiers (see DIFFICULTY_TO_TIER): d4 is T2.
        (1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (6, 4), (7, 5), (8, 6), (9, 6),
    ])
    def test_mapping(self, difficulty, expected):
        assert pb.difficulty_to_age_tier(difficulty) == expected

    def test_none_falls_back_to_t3(self):
        assert pb.difficulty_to_age_tier(None) == 3

    def test_result_always_in_check_range(self):
        for d in range(1, 10):
            assert 1 <= pb.difficulty_to_age_tier(d) <= 6


# ---------------------------------------------------------------------------
# join_sentences
# ---------------------------------------------------------------------------

class TestJoinSentences:

    def test_cjk_joins_without_a_separator(self):
        assert pb.join_sentences(['我喜欢猫。', '你呢？'], 'zh') == '我喜欢猫。你呢？'
        assert pb.join_sentences(['猫です。', '犬です。'], 'JA') == '猫です。犬です。'

    def test_space_delimited_languages_join_with_one_space(self):
        assert pb.join_sentences(['The cat sat.', 'It slept.'], 'en') == 'The cat sat. It slept.'
        assert pb.join_sentences(['One.', 'Two.'], None) == 'One. Two.'
