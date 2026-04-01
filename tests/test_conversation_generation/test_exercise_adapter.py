"""Tests for ConversationExerciseAdapter."""

import pytest
from services.conversation_generation.exercise_adapter import ConversationExerciseAdapter


class TestConversationExerciseAdapter:
    """Tests for the conversation-to-sentence-pool adapter."""

    def setup_method(self):
        self.adapter = ConversationExerciseAdapter()

    def test_basic_sentence_extraction(self):
        """Extracts sentences from turns correctly."""
        turns = [
            {'turn': 0, 'speaker': 'Alice', 'persona_id': 1,
             'text': 'Hello, how are you today? I hope you are doing well.'},
            {'turn': 1, 'speaker': 'Bob', 'persona_id': 2,
             'text': 'I am doing great, thanks for asking.'},
        ]

        pool = self.adapter.build_sentence_pool(
            conversation_id='test-uuid',
            turns=turns,
            language_id=2,
            complexity_tier='T3',
        )

        assert len(pool) >= 2
        assert all(s['source'] == 'conversation' for s in pool)
        assert all(s['language_id'] == 2 for s in pool)
        assert all(s['complexity_tier'] == 'T3' for s in pool)

    def test_skips_short_sentences(self):
        """Sentences shorter than 5 chars are skipped."""
        turns = [
            {'turn': 0, 'speaker': 'Alice', 'persona_id': 1, 'text': 'Hi!'},
            {'turn': 1, 'speaker': 'Bob', 'persona_id': 2,
             'text': 'This is a proper sentence that should be included.'},
        ]

        pool = self.adapter.build_sentence_pool(
            conversation_id='test-uuid',
            turns=turns,
            language_id=2,
        )

        # "Hi!" should be skipped (< 5 chars)
        assert all(len(s['sentence']) >= 5 for s in pool)

    def test_empty_turns(self):
        """Empty turns list returns empty pool."""
        pool = self.adapter.build_sentence_pool(
            conversation_id='test-uuid',
            turns=[],
            language_id=2,
        )
        assert pool == []

    def test_chinese_sentence_splitting(self):
        """Chinese sentences are split on Chinese punctuation."""
        turns = [
            {'turn': 0, 'speaker': '张伟', 'persona_id': 1,
             'text': '你好，今天天气真好！我们去公园走走吧。'},
        ]

        pool = self.adapter.build_sentence_pool(
            conversation_id='test-uuid',
            turns=turns,
            language_id=1,
            complexity_tier='T2',
        )

        assert len(pool) >= 1
        assert pool[0]['language_id'] == 1

    def test_metadata_preserved(self):
        """Speaker and turn metadata are preserved in sentence dicts."""
        turns = [
            {'turn': 3, 'speaker': 'Alice', 'persona_id': 42,
             'text': 'This is a test sentence for metadata checking.'},
        ]

        pool = self.adapter.build_sentence_pool(
            conversation_id='conv-123',
            turns=turns,
            language_id=2,
        )

        assert len(pool) == 1
        assert pool[0]['speaker'] == 'Alice'
        assert pool[0]['persona_id'] == 42
        assert pool[0]['turn_number'] == 3
        assert pool[0]['source_id'] == 'conv-123'
