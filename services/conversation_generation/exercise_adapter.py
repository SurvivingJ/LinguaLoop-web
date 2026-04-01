"""
Exercise Adapter

Converts conversation turns into the sentence_pool format expected by
the existing ExerciseGenerationOrchestrator generators.

The sentence_pool is a list of dicts, each representing one sentence
with metadata for exercise generation.
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Simple sentence splitters per language
SENTENCE_SPLITTERS = {
    2: re.compile(r'(?<=[.!?])\s+'),                    # English
    1: re.compile(r'(?<=[。！？])\s*'),                    # Chinese
    3: re.compile(r'(?<=[。！？])\s*'),                    # Japanese
}


class ConversationExerciseAdapter:
    """Converts conversation turns into sentence_pool format for exercise generators."""

    def build_sentence_pool(
        self,
        conversation_id: str,
        turns: List[Dict],
        language_id: int,
        complexity_tier: str = 'B1',
        corpus_features: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Extract individual sentences from conversation turns and tag
        with metadata for exercise generation.

        Args:
            conversation_id: UUID of the conversation record
            turns: List of turn dicts with 'text', 'speaker', 'persona_id'
            language_id: Language ID from dim_languages
            complexity_tier: Complexity tier for difficulty tagging
            corpus_features: Optional extracted features for enrichment

        Returns:
            List of sentence dicts compatible with ExerciseGenerator.generate_batch()
        """
        splitter = SENTENCE_SPLITTERS.get(language_id, SENTENCE_SPLITTERS[2])
        sentence_pool = []

        for turn in turns:
            text = turn.get('text', '').strip()
            if not text:
                continue

            # Split turn text into individual sentences
            sentences = [s.strip() for s in splitter.split(text) if s.strip()]

            for sentence in sentences:
                # Skip very short sentences (greetings, interjections)
                if len(sentence) < 5:
                    continue

                sentence_dict = {
                    'sentence': sentence,
                    'complexity_tier': complexity_tier,
                    'source': 'conversation',
                    'source_id': conversation_id,
                    'language_id': language_id,
                    'speaker': turn.get('speaker', ''),
                    'persona_id': turn.get('persona_id'),
                    'turn_number': turn.get('turn', 0),
                }

                sentence_pool.append(sentence_dict)

        logger.info(
            "Built sentence pool: %d sentences from %d turns (conversation %s)",
            len(sentence_pool), len(turns), conversation_id,
        )

        return sentence_pool
