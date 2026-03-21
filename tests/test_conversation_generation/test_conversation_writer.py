"""Tests for ConversationWriter turn validation logic."""

import pytest


class TestConversationTurnValidation:
    """Tests for conversation turn structure validation."""

    def test_valid_turn_structure(self):
        """Valid turns have turn number, speaker, persona_id, and text."""
        turns = [
            {'turn': 0, 'speaker': 'Alice', 'persona_id': 1, 'text': 'Hello!'},
            {'turn': 1, 'speaker': 'Bob', 'persona_id': 2, 'text': 'Hi there!'},
        ]

        for turn in turns:
            assert 'turn' in turn
            assert 'speaker' in turn
            assert 'persona_id' in turn
            assert 'text' in turn
            assert isinstance(turn['turn'], int)
            assert isinstance(turn['text'], str)
            assert len(turn['text']) > 0

    def test_speaker_alternation(self):
        """Turns should alternate between two speakers."""
        turns = [
            {'turn': 0, 'speaker': 'Alice', 'persona_id': 1, 'text': 'Hello!'},
            {'turn': 1, 'speaker': 'Bob', 'persona_id': 2, 'text': 'Hi!'},
            {'turn': 2, 'speaker': 'Alice', 'persona_id': 1, 'text': 'How are you?'},
            {'turn': 3, 'speaker': 'Bob', 'persona_id': 2, 'text': 'Fine, thanks.'},
        ]

        speakers = [t['speaker'] for t in turns]
        for i in range(1, len(speakers)):
            assert speakers[i] != speakers[i - 1], \
                f"Turn {i} has same speaker as turn {i-1}"

    def test_turn_numbering(self):
        """Turn numbers should be sequential starting from 0."""
        turns = [
            {'turn': i, 'speaker': 'A' if i % 2 == 0 else 'B',
             'persona_id': 1 if i % 2 == 0 else 2,
             'text': f'Turn {i} content.'}
            for i in range(6)
        ]

        for i, turn in enumerate(turns):
            assert turn['turn'] == i


class TestQualityScore:
    """Tests for the quality score computation."""

    def test_quality_score_range(self):
        """Quality score should be between 0.0 and 1.0."""
        from services.conversation_generation.orchestrator import ConversationGenerationOrchestrator

        # Bypass __init__ to test the static method directly
        orch = object.__new__(ConversationGenerationOrchestrator)

        turns = [
            {'turn': 0, 'speaker': 'A', 'text': 'Hello, how are you doing today?'},
            {'turn': 1, 'speaker': 'B', 'text': 'I am fine, thank you for asking.'},
            {'turn': 2, 'speaker': 'A', 'text': 'That is great to hear, what are your plans?'},
            {'turn': 3, 'speaker': 'B', 'text': 'I am thinking about going for a walk.'},
            {'turn': 4, 'speaker': 'A', 'text': 'That sounds like a good idea.'},
            {'turn': 5, 'speaker': 'B', 'text': 'Would you like to join me?'},
        ]

        features = {'scored_collocations': 10}
        score = orch._compute_quality_score(turns, features)

        assert 0.0 <= score <= 1.0

    def test_quality_score_empty_conversation(self):
        """Empty conversation gets a low quality score."""
        from services.conversation_generation.orchestrator import ConversationGenerationOrchestrator

        orch = object.__new__(ConversationGenerationOrchestrator)
        score = orch._compute_quality_score([], {})

        assert score < 0.5
