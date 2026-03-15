# services/exercise_generation/difficulty.py

from services.exercise_generation.config import CEFR_TO_IRT


class DifficultyCalibrator:
    """
    Computes and attaches static difficulty + IRT seed values to exercise row dicts.
    Formula: difficulty_static = 0.50 x cefr_numeric + 0.50 x sentence_length_score
    """

    CEFR_NUMERIC: dict[str, float] = {
        'A1': 1.0, 'A2': 2.0, 'B1': 3.0, 'B2': 3.5, 'C1': 4.0, 'C2': 5.0,
    }

    def attach_difficulty(self, row: dict, cefr_level: str) -> dict:
        """Compute and attach difficulty_static, irt_difficulty, irt_discrimination."""
        sentence = row.get('content', {}).get('original_sentence') \
                   or row.get('content', {}).get('sentence_with_blank') \
                   or row.get('content', {}).get('tl_sentence', '')

        cefr_score    = self.CEFR_NUMERIC.get(cefr_level, 3.0)
        length_score  = self._sentence_length_score(sentence, row.get('language_id', 2))
        static        = round(0.5 * cefr_score + 0.5 * length_score, 2)

        row['difficulty_static']  = static
        row['irt_difficulty']     = CEFR_TO_IRT.get(cefr_level, 0.0)
        row['irt_discrimination'] = 1.0
        row['cefr_level']         = cefr_level
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
