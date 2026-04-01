# services/exercise_generation/difficulty.py

import logging
from services.exercise_generation.config import TIER_TO_IRT
from services.conversation_generation.categorical_maps import TIER_NUMERIC
from services.vocabulary.frequency_service import get_zipf_score

logger = logging.getLogger(__name__)

# Language ID -> app language code for wordfreq lookups
_LANG_ID_TO_CODE: dict[int, str] = {1: 'cn', 2: 'en', 3: 'jp'}


class DifficultyCalibrator:
    """
    Computes and attaches static difficulty + IRT seed values to exercise row dicts.
    Formula: difficulty_static = 0.40 x tier + 0.30 x sentence_length + 0.30 x word_frequency
    """

    def attach_difficulty(self, row: dict, complexity_tier: str) -> dict:
        """Compute and attach difficulty_static, irt_difficulty, irt_discrimination."""
        sentence = row.get('content', {}).get('original_sentence') \
                   or row.get('content', {}).get('sentence_with_blank') \
                   or row.get('content', {}).get('tl_sentence', '')

        language_id   = row.get('language_id', 2)
        tier_score    = TIER_NUMERIC.get(complexity_tier, 3.0)
        length_score  = self._sentence_length_score(sentence, language_id)
        freq_score    = self._word_frequency_score(sentence, language_id)
        static        = round(0.40 * tier_score + 0.30 * length_score + 0.30 * freq_score, 2)

        row['difficulty_static']  = static
        row['irt_difficulty']     = TIER_TO_IRT.get(complexity_tier, 0.0)
        row['irt_discrimination'] = 1.0
        row['complexity_tier']    = complexity_tier
        return row

    def _sentence_length_score(self, sentence: str, language_id: int) -> float:
        """Map sentence length to a 1-5 scale."""
        from services.exercise_generation.config import LANG_CHINESE, LANG_JAPANESE
        if not sentence:
            return 2.5
        if language_id == LANG_CHINESE:
            length = len(sentence)
            breakpoints = [(10, 1.0), (20, 2.0), (35, 3.0), (50, 4.0)]
        elif language_id == LANG_JAPANESE:
            length = len(sentence)
            breakpoints = [(10, 1.0), (25, 2.0), (40, 3.0), (60, 4.0)]
        else:
            length = len(sentence.split())
            breakpoints = [(5, 1.0), (10, 2.0), (18, 3.0), (28, 4.0)]

        for threshold, score in breakpoints:
            if length <= threshold:
                return score
        return 5.0

    def _word_frequency_score(self, sentence: str, language_id: int) -> float:
        """
        Compute difficulty score (1-5) based on mean word frequency.
        High Zipf = common words = easy (low score).
        Low Zipf = rare words = hard (high score).
        """
        if not sentence:
            return 2.5

        lang_code = _LANG_ID_TO_CODE.get(language_id)
        if not lang_code:
            return 2.5

        # Tokenize: whitespace split for EN, character-level for CJK
        from services.exercise_generation.config import LANG_CHINESE, LANG_JAPANESE
        if language_id in (LANG_CHINESE, LANG_JAPANESE):
            # For CJK, look up individual characters and short tokens
            # Filter out punctuation and whitespace
            tokens = [ch for ch in sentence if ch.strip() and not ch.isascii()]
        else:
            tokens = sentence.split()

        if not tokens:
            return 2.5

        scores = []
        for token in tokens:
            try:
                score = get_zipf_score(token.lower().strip('.,!?;:\'"()[]{}'), lang_code)
            except Exception:
                continue
            if score is not None:
                scores.append(score)

        if not scores:
            return 2.5

        mean_zipf = sum(scores) / len(scores)

        # Map mean Zipf to 1-5 difficulty (inverse relationship)
        if mean_zipf >= 5.5:
            return 1.0
        elif mean_zipf >= 4.5:
            return 2.0
        elif mean_zipf >= 3.5:
            return 3.0
        elif mean_zipf >= 2.5:
            return 4.0
        else:
            return 5.0
