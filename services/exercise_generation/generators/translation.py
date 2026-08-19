# services/exercise_generation/generators/translation.py
"""
Translation exercise generators — schema-v2 (nl-keyed) output.

Both types here are the *most* native-language-dependent content the pipeline
produces: the whole exercise is a translation into (or out of) the learner's
native language. Under schema v2 (TASK-519) that text lives under
``content.nl.<code>`` rather than at the top level, so one stored item can
serve learners with different native languages instead of being silently
English-only.

``nl_language_code`` is a required keyword argument — there is no ``'en'``
default. The lint test in tests/test_nl_keyed_content.py fails the build if one
reappears; a default is exactly how the v1 corpus became monolingual.
"""

from services.exercise_generation.base_generator import ExerciseGenerator
from services.exercise_generation.judges.translation_uniqueness import (
    judge_translation_item,
)
from services.exercise_generation.schemas import wrap_nl


class TlNlTranslationGenerator(ExerciseGenerator):
    """
    Generates tl_nl_translation (MCQ) exercises.
    TL sentence from pool -> LLM generates 1 correct + 2 wrong NL translations.

    ``nl.<code>.options[0]`` is always the correct translation (V3 rule).
    """

    exercise_type = 'tl_nl_translation'
    source_type   = 'grammar'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'grammar',
                 *, nl_language_code: str):
        super().__init__(db, language_id, model)
        self.source_type      = source_type
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

            # Uniqueness gate (TASK-525). The eval's 0% accept rate on this
            # type was not bad translation but options that were *also* right,
            # so a correct learner got marked wrong. Drop the also-acceptable
            # ones, and block the item outright rather than serve a two-option
            # question padded back up to size.
            kept, outcome, judge_meta = judge_translation_item(
                self.db, tl_sentence, correct_nl, list(wrong_nls),
                self.language_id, self.nl_language_code,
            )
            if outcome.verdict == 'reject':
                return None

            # TL-facing content at the top level, nl-facing content keyed.
            content = wrap_nl(
                {
                    'tl_sentence':    tl_sentence,
                    'tl_language':    self._get_language_code(),
                    'nl_language':    self.nl_language_code,
                    'source_test_id': sentence_dict.get('test_id'),
                },
                self.exercise_type,
                self.nl_language_code,
                {
                    'correct_nl': correct_nl,
                    'options':    [correct_nl] + kept[:2],
                },
            )
            content['__judge_metas'] = {'translation_uniqueness': judge_meta}
            return content
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

    ``primary_tl`` and ``acceptable_variants`` are TL-facing (what the learner
    types) and stay at the top level; the prompt sentence and the grading notes
    are nl-facing and are keyed.
    """

    exercise_type = 'nl_tl_translation'
    source_type   = 'grammar'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'grammar',
                 *, nl_language_code: str):
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
            return wrap_nl(
                {
                    'tl_language':         self._get_language_code(),
                    'nl_language':         self.nl_language_code,
                    'primary_tl':          tl_sentence,
                    'acceptable_variants': result.get('acceptable_variants', []),
                    'source_test_id':      sentence_dict.get('test_id'),
                },
                self.exercise_type,
                self.nl_language_code,
                {
                    'nl_sentence':   result['nl_sentence'],
                    'grading_notes': result['grading_notes'],
                },
            )
        except Exception:
            return None

    def _get_language_code(self) -> str:
        row = self.db.table('dim_languages').select('language_code') \
            .eq('id', self.language_id).single().execute().data
        return row.get('language_code', 'unknown') if row else 'unknown'
