# services/exercise_generation/generators/translation.py

from services.exercise_generation.base_generator import ExerciseGenerator


class TlNlTranslationGenerator(ExerciseGenerator):
    """
    Generates tl_nl_translation (MCQ) exercises.
    TL sentence from pool -> LLM generates 1 correct + 2 wrong NL translations.
    options[0] is always the correct translation (V3 rule).
    """

    exercise_type = 'tl_nl_translation'
    source_type   = 'grammar'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'grammar',
                 nl_language_code: str = 'en'):
        super().__init__(db, language_id, model)
        self.source_type     = source_type
        self.nl_language_code = nl_language_code

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        tl_sentence = sentence_dict['sentence']
        template    = self.load_prompt_template('tl_nl_translation_generation')
        prompt      = template.format(
            tl_sentence=tl_sentence,
            nl_language=self.nl_language_code,
        )
        try:
            result      = self.call_llm(prompt, response_format='json')
            correct_nl  = result.get('correct_nl', '')
            wrong_nls   = result.get('wrong_options', [])
            if not correct_nl or len(wrong_nls) < 2:
                return None
            return {
                'tl_sentence':    tl_sentence,
                'tl_language':    self._get_language_code(),
                'nl_language':    self.nl_language_code,
                'correct_nl':     correct_nl,
                'options':        [correct_nl] + wrong_nls[:2],
                'source_test_id': sentence_dict.get('test_id'),
            }
        except Exception:
            return None

    def _get_language_code(self) -> str:
        row = self.db.table('dim_languages').select('language_code') \
            .eq('id', self.language_id).single().execute().data
        return row.get('language_code', 'unknown') if row else 'unknown'


class NlTlTranslationGenerator(ExerciseGenerator):
    """
    Generates nl_tl_translation (production) exercises.
    TL sentence from pool -> LLM generates NL version, grading_notes, acceptable_variants.
    """

    exercise_type = 'nl_tl_translation'
    source_type   = 'grammar'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'grammar',
                 nl_language_code: str = 'en'):
        super().__init__(db, language_id, model)
        self.source_type      = source_type
        self.nl_language_code = nl_language_code

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        tl_sentence = sentence_dict['sentence']
        template    = self.load_prompt_template('nl_tl_translation_generation')
        prompt      = template.format(
            tl_sentence=tl_sentence,
            nl_language=self.nl_language_code,
        )
        try:
            result = self.call_llm(prompt, response_format='json')
            if not result.get('nl_sentence') or not result.get('grading_notes'):
                return None
            return {
                'nl_sentence':         result['nl_sentence'],
                'nl_language':         self.nl_language_code,
                'tl_language':         self._get_language_code(),
                'primary_tl':          tl_sentence,
                'grading_notes':       result['grading_notes'],
                'acceptable_variants': result.get('acceptable_variants', []),
                'source_test_id':      sentence_dict.get('test_id'),
            }
        except Exception:
            return None

    def _get_language_code(self) -> str:
        row = self.db.table('dim_languages').select('language_code') \
            .eq('id', self.language_id).single().execute().data
        return row.get('language_code', 'unknown') if row else 'unknown'
