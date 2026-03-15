# services/exercise_generation/generators/jumbled_sentence.py

from services.exercise_generation.base_generator import ExerciseGenerator
from services.exercise_generation.language_processor import LanguageProcessor


class JumbledSentenceGenerator(ExerciseGenerator):
    """
    Generates jumbled_sentence exercises using Python NLP only - no LLM.
    Delegates to LanguageProcessor.chunk_sentence() for language-appropriate chunking.
    """

    exercise_type = 'jumbled_sentence'
    source_type   = 'grammar'

    def __init__(self, db, language_id: int, model: str = '', source_type: str = 'grammar'):
        super().__init__(db, language_id, model)
        self.source_type    = source_type
        self.lang_processor = LanguageProcessor.for_language(language_id)

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        sentence = sentence_dict['sentence']
        try:
            chunks = self.lang_processor.chunk_sentence(sentence)
        except ValueError:
            return None

        if len(chunks) < 3:
            return None

        return {
            'original_sentence': sentence,
            'chunks':            chunks,
            'correct_ordering':  list(range(len(chunks))),
            'source_test_id':    sentence_dict.get('test_id'),
        }
