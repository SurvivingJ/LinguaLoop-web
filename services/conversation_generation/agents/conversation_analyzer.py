"""
Conversation Analyzer Agent

Wraps the existing CorpusAnalyzer to extract linguistic features
from generated conversations. Also uses LLM for supplementary analysis.
"""

import json
import logging
from collections import Counter
from typing import Dict, List, Optional

from services.topic_generation.agents.base import BaseAgent
from services.corpus.analyzer import CorpusAnalyzer
from services.corpus.style_analyzer import StyleAnalyzer
from services.corpus.tokenizers import (
    EnglishTokenizer, ChineseTokenizer, JapaneseTokenizer,
)
from ..config import conv_gen_config

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

# Language ID -> tokenizer class mapping
TOKENIZER_MAP = {
    1: ChineseTokenizer,   # cn
    2: EnglishTokenizer,   # en
    3: JapaneseTokenizer,  # jp
}


class ConversationAnalyzer(BaseAgent):
    """Extracts linguistic features from generated conversations."""

    def __init__(self, api_key: str = None, model: str = None):
        if conv_gen_config.llm_provider == 'ollama':
            super().__init__(
                model=model or conv_gen_config.ollama_model,
                api_key='ollama',
                base_url=conv_gen_config.ollama_base_url,
                name="ConversationAnalyzer",
            )
        else:
            super().__init__(
                model=model or conv_gen_config.analysis_model,
                api_key=api_key or conv_gen_config.openrouter_api_key,
                base_url=OPENROUTER_BASE_URL,
                name="ConversationAnalyzer",
            )

    def analyze(
        self,
        turns: List[Dict],
        language_id: int,
        complexity_tier: str = 'T3',
        prompt_template: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict:
        """
        Analyze a conversation and return corpus features.

        Combines statistical analysis (via CorpusAnalyzer) with
        LLM-based feature extraction.

        Args:
            turns: List of turn dicts with 'text' field
            language_id: Language ID from dim_languages
            complexity_tier: Target complexity tier (T1-T6)
            prompt_template: Optional prompt template for LLM analysis

        Returns:
            Dict of corpus features for the conversations.corpus_features column.
        """
        # Concatenate all turn text
        full_text = '\n'.join(turn.get('text', '') for turn in turns)

        # Statistical analysis via existing CorpusAnalyzer
        stats = self._run_statistical_analysis(full_text, language_id)

        # LLM-based analysis (optional, for richer features)
        llm_features = {}
        if prompt_template:
            llm_features = self._run_llm_analysis(
                full_text, language_id, complexity_tier, prompt_template,
                model=model,
            )

        # Merge results
        features = {
            'turn_count': len(turns),
            'total_characters': len(full_text),
            'speakers': list({t.get('speaker') for t in turns}),
            **stats,
            **llm_features,
        }

        logger.info(
            "Analyzed conversation: %d turns, %d chars, %d collocations, "
            "%d entities, %d POS tags",
            len(turns), len(full_text),
            len(stats.get('top_collocations', [])),
            len(stats.get('named_entities', [])),
            len(stats.get('pos_distribution', {})),
        )

        return features

    def _run_statistical_analysis(self, text: str, language_id: int) -> Dict:
        """Run statistical corpus analysis using existing CorpusAnalyzer."""
        tokenizer_cls = TOKENIZER_MAP.get(language_id)
        if tokenizer_cls is None:
            logger.warning("No tokenizer for language_id=%d, skipping stats", language_id)
            return {}

        try:
            tokenizer = tokenizer_cls()
            analyzer = CorpusAnalyzer(tokenizer)

            # Full pipeline: extract n-grams (2-5), score with PMI/G²/T-Score
            scored = analyzer.score_ngrams(text)

            # Take top collocations by PMI
            top_collocations = sorted(
                scored, key=lambda x: x.get('pmi_score', 0), reverse=True
            )[:20]

            # NER extraction
            named_entities = sorted(tokenizer.extract_named_entities(text))

            # POS distribution
            pos_pairs = tokenizer.tokenize_with_pos(text)
            pos_distribution = dict(Counter(tag for _, tag in pos_pairs).most_common())

            # Vocabulary profile (TTR, MATTR, hapax ratio, Zipf distribution)
            unigrams = analyzer.extract_all_ngrams(text, max_n=1)[1]
            total_tokens = sum(unigrams.values())
            style = StyleAnalyzer(tokenizer)
            vocab_profile = style._extract_vocabulary_profile(unigrams, total_tokens)

            return {
                'scored_collocations': len(scored),
                'top_collocations': top_collocations,
                'named_entities': named_entities,
                'pos_distribution': pos_distribution,
                'vocabulary_profile': vocab_profile,
            }
        except Exception as exc:
            logger.error("Statistical analysis failed: %s", exc)
            return {}

    def _run_llm_analysis(
        self,
        text: str,
        language_id: int,
        complexity_tier: str,
        prompt_template: str,
        model: Optional[str] = None,
    ) -> Dict:
        """Run LLM-based feature extraction."""
        language_name = {1: 'Chinese', 2: 'English', 3: 'Japanese'}.get(language_id, 'English')

        prompt = prompt_template.format(
            conversation_text=text,
            language_name=language_name,
            complexity_tier=complexity_tier,
        )

        try:
            response_text = self._call_llm(
                prompt=prompt,
                json_mode=True,
                temperature=0.3,
                model=model,
            )
            features = json.loads(response_text) if isinstance(response_text, str) else response_text
            return {
                'vocabulary': features.get('vocabulary', []),
                'grammar_patterns': features.get('grammar_patterns', []),
                'register_markers': features.get('register_markers', []),
                'cultural_references': features.get('cultural_references', []),
                'estimated_tier': features.get('estimated_tier', complexity_tier),
            }
        except Exception as exc:
            logger.error("LLM analysis failed: %s", exc)
            return {}
