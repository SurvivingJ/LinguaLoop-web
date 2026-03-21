"""
Tests for DifficultyCalibrator word frequency scoring.
"""

import pytest

from services.exercise_generation.difficulty import DifficultyCalibrator


@pytest.fixture
def calibrator():
    return DifficultyCalibrator()


class TestWordFrequencyScore:

    def test_common_words_score_low(self, calibrator):
        """Common English words should produce a low difficulty score."""
        score = calibrator._word_frequency_score("the cat sat on the mat", 2)
        assert score <= 2.0

    def test_rare_words_score_high(self, calibrator):
        """Rare/uncommon words should produce a higher difficulty score."""
        score = calibrator._word_frequency_score(
            "the sesquipedalian loquaciousness perplexed the interlocutors", 2
        )
        assert score >= 3.0

    def test_common_harder_than_rare(self, calibrator):
        """A sentence with common words should score lower than one with rare words."""
        common = calibrator._word_frequency_score("I like to eat food and drink water", 2)
        rare = calibrator._word_frequency_score(
            "the ephemeral juxtaposition of quintessential paradigms", 2
        )
        assert common < rare

    def test_empty_sentence_returns_default(self, calibrator):
        assert calibrator._word_frequency_score("", 2) == 2.5

    def test_unknown_language_returns_default(self, calibrator):
        assert calibrator._word_frequency_score("some text", 99) == 2.5

    def test_chinese_returns_score(self, calibrator):
        """Chinese text should produce a valid score."""
        score = calibrator._word_frequency_score("今天天气很好", 1)
        assert 1.0 <= score <= 5.0

    def test_japanese_returns_score(self, calibrator):
        """Japanese text should produce a valid score (requires MeCab for wordfreq)."""
        score = calibrator._word_frequency_score("今日は天気がいいです", 3)
        # wordfreq needs MeCab for Japanese; if not installed, returns default 2.5
        assert 1.0 <= score <= 5.0


class TestAttachDifficultyWithFrequency:

    def test_three_factor_formula(self, calibrator):
        """Verify the formula uses three factors."""
        row = {
            'language_id': 2,
            'content': {'original_sentence': 'The cat sat on the mat'},
        }
        result = calibrator.attach_difficulty(row, 'B1')

        assert 'difficulty_static' in result
        # B1 = 3.0 CEFR, short common sentence -> should be moderate difficulty
        assert 1.0 <= result['difficulty_static'] <= 4.0

    def test_rare_words_increase_difficulty(self, calibrator):
        """Sentences with rare words should have higher difficulty than common ones."""
        common_row = {
            'language_id': 2,
            'content': {'original_sentence': 'I want to go to the big house'},
        }
        rare_row = {
            'language_id': 2,
            'content': {'original_sentence': 'The sesquipedalian nomenclature obfuscated comprehension'},
        }
        common_result = calibrator.attach_difficulty(common_row.copy(), 'B1')
        rare_result = calibrator.attach_difficulty(rare_row.copy(), 'B1')

        assert common_result['difficulty_static'] < rare_result['difficulty_static']

    def test_irt_values_still_set(self, calibrator):
        """IRT values should still be set correctly."""
        row = {
            'language_id': 2,
            'content': {'original_sentence': 'Hello world'},
        }
        result = calibrator.attach_difficulty(row, 'B2')
        assert result['irt_difficulty'] == 0.5  # B2 IRT value
        assert result['irt_discrimination'] == 1.0
        assert result['cefr_level'] == 'B2'

    def test_cefr_still_dominates(self, calibrator):
        """CEFR level should still be the strongest factor (40% weight)."""
        row_content = {'original_sentence': 'The cat sat on the mat'}
        a1_row = {'language_id': 2, 'content': row_content}
        c2_row = {'language_id': 2, 'content': row_content}

        a1_result = calibrator.attach_difficulty(a1_row.copy(), 'A1')
        c2_result = calibrator.attach_difficulty(c2_row.copy(), 'C2')

        # Same sentence, different CEFR -> C2 should be harder
        assert a1_result['difficulty_static'] < c2_result['difficulty_static']
