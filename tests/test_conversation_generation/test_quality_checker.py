"""
Tests for ConversationQualityChecker.
"""

import pytest
from unittest.mock import patch

from services.conversation_generation.quality_checker import (
    ConversationQualityChecker,
    QualityResult,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _make_turns(texts: list[str], speakers=('Alice', 'Bob')) -> list[dict]:
    """Build a list of turn dicts from a list of text strings."""
    return [
        {
            'turn': i,
            'speaker': speakers[i % len(speakers)],
            'persona_id': i % len(speakers) + 1,
            'text': text,
        }
        for i, text in enumerate(texts)
    ]


@pytest.fixture
def checker():
    return ConversationQualityChecker()


# ── Pre-check: turn count ────────────────────────────────────────────

class TestTurnCountPreCheck:

    def test_too_few_turns_fails(self, checker):
        turns = _make_turns(['Hello', 'Hi'])  # 2 turns, below default min of 6
        result = checker.check(turns, language_id=2)
        assert result.score == 0.0
        assert result.passed is False
        assert 'Turn count' in result.details.get('reason', '')

    def test_empty_turns_fails(self, checker):
        result = checker.check([], language_id=2)
        assert result.score == 0.0
        assert result.passed is False


# ── Language consistency ─────────────────────────────────────────────

class TestLanguageConsistency:

    def test_all_english_scores_high(self, checker):
        texts = [
            "I think we should go to the market this afternoon.",
            "That sounds like a great idea, let me grab my coat.",
            "Do you want to pick up some fresh vegetables?",
            "Yes, and maybe some fruit too if they have good peaches.",
            "Last time the strawberries were amazing there.",
            "I remember, we ate them all on the way home!",
            "Should we bring a bigger bag this time?",
            "Definitely, and maybe a cooler for the cheese.",
        ]
        turns = _make_turns(texts)
        score, details = checker._score_language_consistency(turns, 'en')
        assert score >= 0.8
        assert details['violations'] == 0

    def test_mixed_languages_scores_low(self, checker):
        texts = [
            "Hello, how are you doing today?",
            "Je suis très bien, merci beaucoup!",
            "I was hoping we could discuss the project.",
            "Oui, le projet est très intéressant.",
            "Can you send me the latest report?",
            "Bien sûr, je vais vous l'envoyer maintenant.",
            "Thanks, I appreciate your help with this.",
            "De rien, c'est toujours un plaisir de vous aider.",
        ]
        turns = _make_turns(texts)
        score, details = checker._score_language_consistency(turns, 'en')
        assert score < 0.7
        assert details['violations'] > 0

    def test_short_turns_skipped(self, checker):
        texts = ['Hi', 'Ok', 'Yes', 'No', 'Hmm', 'Ah', 'Oh', 'Wow']
        turns = _make_turns(texts)
        score, details = checker._score_language_consistency(turns, 'en')
        assert details['checked'] == 0
        assert score == 1.0  # All skipped, assume ok


# ── Repetition ───────────────────────────────────────────────────────

class TestRepetition:

    def test_varied_text_scores_high(self, checker):
        texts = [
            "The weather is beautiful today.",
            "I agree, let's go for a walk.",
            "We could visit the park nearby.",
            "That sounds wonderful, I'll bring lunch.",
            "Maybe we can sit by the lake.",
            "Great idea, I love watching the ducks.",
            "Should we invite Sarah to join?",
            "Yes, she would really enjoy it.",
        ]
        turns = _make_turns(texts)
        score, _ = checker._score_repetition(turns, is_cjk=False)
        assert score >= 0.8

    def test_highly_repetitive_scores_low(self, checker):
        texts = [
            "the the the the the the",
            "yes yes yes yes yes yes",
            "good good good good good good",
            "ok ok ok ok ok ok ok",
            "right right right right right right",
            "sure sure sure sure sure sure",
            "fine fine fine fine fine fine",
            "well well well well well well",
        ]
        turns = _make_turns(texts)
        score, details = checker._score_repetition(turns, is_cjk=False)
        assert score < 0.5
        assert details['repetition_ratio'] > 0.1


# ── Turn length variance ─────────────────────────────────────────────

class TestTurnLengthVariance:

    def test_uniform_lengths_score_low(self, checker):
        # All turns exactly 20 chars
        texts = ['A' * 20] * 8
        turns = _make_turns(texts)
        score, details = checker._score_turn_length_variance(turns)
        assert score == 0.2
        assert details['std'] < 5

    def test_varied_lengths_score_high(self, checker):
        texts = [
            "Short.",
            "This is a medium length response to what was said.",
            "OK",
            "I completely disagree with your assessment and think we should reconsider the entire approach from scratch.",
            "Why?",
            "Because the data shows a clear trend in the opposite direction of what you suggested earlier.",
            "Hmm.",
            "Let me explain in more detail what I mean by that.",
        ]
        turns = _make_turns(texts)
        score, details = checker._score_turn_length_variance(turns)
        assert score >= 0.6
        assert details['std'] >= 15


# ── Speaker distinctiveness ──────────────────────────────────────────

class TestSpeakerDistinctiveness:

    def test_distinct_vocab_scores_high(self, checker):
        texts = [
            "The quarterly revenue exceeded projections by fifteen percent.",
            "My garden tomatoes are finally ripe after weeks of rain.",
            "We need to discuss the merger timeline with stakeholders.",
            "I planted sunflowers along the fence near the birdbath.",
            "The board approved the restructuring proposal unanimously.",
            "Composting has really improved my soil quality this year.",
            "Shareholder meetings are scheduled for next Thursday morning.",
            "The butterflies love the lavender bushes by the patio.",
        ]
        turns = _make_turns(texts)
        score, details = checker._score_speaker_distinctiveness(turns, is_cjk=False)
        assert score >= 0.5

    def test_identical_vocab_scores_low(self, checker):
        base = "the quick brown fox jumps over the lazy dog again"
        texts = [base] * 8
        turns = _make_turns(texts)
        score, details = checker._score_speaker_distinctiveness(turns, is_cjk=False)
        assert score < 0.1

    def test_single_speaker_scores_zero(self, checker):
        turns = _make_turns(['Hello'] * 8, speakers=('Alice',))
        # Override to have only one unique speaker
        for t in turns:
            t['speaker'] = 'Alice'
        score, details = checker._score_speaker_distinctiveness(turns, is_cjk=False)
        assert score == 0.0


# ── Composite score ──────────────────────────────────────────────────

class TestCompositeScore:

    def test_good_conversation_passes(self, checker):
        """A well-formed English conversation should pass QC."""
        texts = [
            "I've been thinking about changing careers lately.",
            "Really? What kind of work interests you now?",
            "Something in renewable energy, maybe solar panel installation.",
            "That's a growing field. Have you looked into certification programs?",
            "Yes, there's one at the community college starting in March.",
            "My cousin works for a solar company. Want me to ask about openings?",
            "That would be amazing! I'd love an insider perspective.",
            "Sure, I'll text him tonight. He loves talking about his work.",
        ]
        turns = _make_turns(texts)
        result = checker.check(turns, language_id=2)
        assert isinstance(result, QualityResult)
        assert result.score > 0.0
        assert 'language_consistency' in result.dimensions
        assert 'repetition' in result.dimensions
        assert 'turn_length_variance' in result.dimensions
        assert 'speaker_distinctiveness' in result.dimensions

    def test_weights_sum_to_one(self):
        total = sum(ConversationQualityChecker.WEIGHTS.values())
        assert abs(total - 1.0) < 1e-6

    def test_result_dataclass_structure(self, checker):
        turns = _make_turns(['Hello there!'] * 8)
        result = checker.check(turns, language_id=2)
        assert hasattr(result, 'score')
        assert hasattr(result, 'passed')
        assert hasattr(result, 'dimensions')
        assert hasattr(result, 'details')
        assert isinstance(result.passed, bool)


# ── CJK support ──────────────────────────────────────────────────────

class TestCJKSupport:

    def test_chinese_tokenization(self, checker):
        tokens = checker._tokenize_to_set('你好 世界', is_cjk=True)
        # jieba word-level tokenization: '你好' and '世界' are words
        assert '你好' in tokens
        assert '世界' in tokens
        assert ' ' not in tokens

    def test_english_tokenization(self, checker):
        tokens = checker._tokenize_to_set('Hello World', is_cjk=False)
        assert 'hello' in tokens
        assert 'world' in tokens
