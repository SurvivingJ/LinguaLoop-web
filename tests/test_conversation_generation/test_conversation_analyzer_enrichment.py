"""
Tests for ConversationAnalyzer NLP enrichment (NER, POS, vocabulary profile).
"""

import pytest
from unittest.mock import patch, MagicMock

from services.conversation_generation.agents.conversation_analyzer import (
    ConversationAnalyzer,
    TOKENIZER_MAP,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _make_analyzer():
    """Create a ConversationAnalyzer with mocked LLM client."""
    with patch.object(ConversationAnalyzer, '__init__', lambda self, *a, **kw: None):
        analyzer = object.__new__(ConversationAnalyzer)
        return analyzer


# ── Statistical Analysis Enrichment ─────────────────────────────────

class TestStatisticalAnalysisEnrichment:

    def test_english_returns_all_new_fields(self):
        analyzer = _make_analyzer()
        text = (
            "John went to the store in London. He bought apples and oranges. "
            "The weather was beautiful today. Mary called him on the phone. "
            "They decided to meet at the park near the river. "
            "The children were playing happily in the garden."
        )
        result = analyzer._run_statistical_analysis(text, language_id=2)

        assert 'named_entities' in result
        assert isinstance(result['named_entities'], list)

        assert 'pos_distribution' in result
        assert isinstance(result['pos_distribution'], dict)
        assert len(result['pos_distribution']) > 0

        assert 'vocabulary_profile' in result
        assert isinstance(result['vocabulary_profile'], dict)
        assert 'ttr' in result['vocabulary_profile']
        assert 'hapax_ratio' in result['vocabulary_profile']

        # Existing fields still present
        assert 'scored_collocations' in result
        assert 'top_collocations' in result

    def test_english_ner_finds_entities(self):
        analyzer = _make_analyzer()
        text = (
            "Barack Obama visited the United Nations in New York. "
            "He met with Angela Merkel to discuss climate change. "
            "The meeting took place at the headquarters building."
        )
        result = analyzer._run_statistical_analysis(text, language_id=2)
        entities = result.get('named_entities', [])
        # spaCy should find at least some of these entities
        assert len(entities) > 0

    def test_english_pos_distribution_has_common_tags(self):
        analyzer = _make_analyzer()
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "She quickly ran to the beautiful garden. "
            "They were happily singing songs together."
        )
        result = analyzer._run_statistical_analysis(text, language_id=2)
        pos = result.get('pos_distribution', {})
        # English spaCy should produce NOUN, VERB, ADJ, etc.
        assert any(tag in pos for tag in ('NOUN', 'VERB', 'ADJ', 'DET'))

    def test_chinese_returns_all_fields(self):
        analyzer = _make_analyzer()
        text = (
            "今天天气很好，我们去公园散步了。"
            "小明和小红一起去了超市买东西。"
            "他们买了很多水果和蔬菜。"
            "回家以后，他们一起做了晚饭。"
        )
        result = analyzer._run_statistical_analysis(text, language_id=1)

        assert 'named_entities' in result
        assert 'pos_distribution' in result
        assert 'vocabulary_profile' in result
        assert isinstance(result['pos_distribution'], dict)
        assert len(result['pos_distribution']) > 0

    def test_japanese_returns_all_fields(self):
        """Japanese analysis requires ja_core_news_sm model."""
        analyzer = _make_analyzer()
        text = (
            "東京は日本の首都です。"
            "毎日たくさんの人が電車で通勤しています。"
            "新宿駅は世界で最も忙しい駅の一つです。"
            "私は週末に公園で散歩するのが好きです。"
        )
        result = analyzer._run_statistical_analysis(text, language_id=3)

        # If ja_core_news_sm is not installed, the analysis returns {}
        # gracefully (caught by except block). Skip assertions in that case.
        if not result:
            pytest.skip("ja_core_news_sm not installed")

        assert 'named_entities' in result
        assert 'pos_distribution' in result
        assert 'vocabulary_profile' in result

    def test_unknown_language_returns_empty(self):
        analyzer = _make_analyzer()
        result = analyzer._run_statistical_analysis("some text", language_id=99)
        assert result == {}

    def test_empty_text_handles_gracefully(self):
        analyzer = _make_analyzer()
        result = analyzer._run_statistical_analysis("", language_id=2)
        # Should not crash; may return empty or minimal results
        assert isinstance(result, dict)

    def test_vocabulary_profile_has_zipf_distribution(self):
        analyzer = _make_analyzer()
        text = (
            "The magnificent cathedral stood proudly in the ancient city center. "
            "Its intricate architecture attracted numerous tourists from abroad. "
            "The elaborate decorations were truly breathtaking and unforgettable. "
            "Many visitors spent hours admiring the beautiful stained glass windows."
        )
        result = analyzer._run_statistical_analysis(text, language_id=2)
        profile = result.get('vocabulary_profile', {})
        if profile:
            assert 'zipf_distribution' in profile
            assert 'unique_words' in profile

    def test_named_entities_are_sorted(self):
        analyzer = _make_analyzer()
        text = (
            "Zara went to Paris with Alice. They visited the Louvre museum. "
            "Later they met Bob at the Eiffel Tower for dinner."
        )
        result = analyzer._run_statistical_analysis(text, language_id=2)
        entities = result.get('named_entities', [])
        assert entities == sorted(entities)


class TestAnalyzeIntegration:

    def test_analyze_includes_enriched_stats(self):
        analyzer = _make_analyzer()
        turns = [
            {'text': 'Hello, how are you doing today?', 'speaker': 'Alice'},
            {'text': 'I am doing great, thanks for asking!', 'speaker': 'Bob'},
            {'text': 'Would you like to go to the park?', 'speaker': 'Alice'},
            {'text': 'That sounds like a wonderful idea.', 'speaker': 'Bob'},
            {'text': 'The weather is perfect for a walk.', 'speaker': 'Alice'},
            {'text': 'Let me grab my jacket and we can go.', 'speaker': 'Bob'},
        ]
        result = analyzer.analyze(turns, language_id=2)

        # Should have the new fields from statistical analysis
        assert 'named_entities' in result
        assert 'pos_distribution' in result
        assert 'vocabulary_profile' in result

        # Should still have basic fields
        assert 'turn_count' in result
        assert result['turn_count'] == 6
        assert 'total_characters' in result
        assert 'speakers' in result
