# services/exercise_generation/generators/collocation.py

from services.exercise_generation.base_generator import ExerciseGenerator
from services.exercise_generation.language_processor import LanguageProcessor


class CollocationGapFillGenerator(ExerciseGenerator):
    """
    Generates collocation_gap_fill exercises.
    Sentence contains the collocation; the collocate word is blanked.
    LLM generates 3 distractors. options[0] = correct collocate.
    """

    exercise_type = 'collocation_gap_fill'
    source_type   = 'collocation'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        col_row = self.db.table('corpus_collocations') \
            .select('collocation_text, head_word, collocate') \
            .eq('id', source_id).single().execute().data
        if not col_row:
            return None

        collocate = col_row.get('collocate', '')
        sentence  = sentence_dict['sentence']

        if not collocate or collocate.lower() not in sentence.lower():
            return None

        blanked  = sentence.replace(collocate, '___', 1)
        template = self.load_prompt_template('collocation_gap_fill_generation')
        prompt   = template.format(
            head_word=col_row.get('head_word', ''),
            collocate=collocate,
            sentence=sentence,
        )
        try:
            result      = self.call_llm(prompt, response_format='json')
            distractors = result.get('distractors', [])
            if len(distractors) < 3:
                return None
            return {
                'sentence':    blanked,
                'correct':     collocate,
                'options':     [collocate] + distractors[:3],
                'collocation': col_row.get('collocation_text', ''),
                'source_test_id': sentence_dict.get('test_id'),
            }
        except Exception:
            return None


class CollocationRepairGenerator(ExerciseGenerator):
    """
    Generates collocation_repair exercises.
    LLM replaces the correct collocate with an unnatural-but-plausible substitute.
    User must (1) identify the wrong word, then (2) type the correct one.
    """

    exercise_type = 'collocation_repair'
    source_type   = 'collocation'

    def __init__(self, db, language_id: int, model: str):
        super().__init__(db, language_id, model)
        self.lang_processor = LanguageProcessor.for_language(language_id)

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        col_row = self.db.table('corpus_collocations') \
            .select('collocation_text, head_word, collocate') \
            .eq('id', source_id).single().execute().data
        if not col_row:
            return None

        template = self.load_prompt_template('collocation_repair_generation')
        prompt   = template.format(
            sentence=sentence_dict['sentence'],
            collocate=col_row.get('collocate', ''),
            head_word=col_row.get('head_word', ''),
        )
        try:
            result = self.call_llm(prompt, response_format='json')
            if not result.get('error_word') or not result.get('correct_word'):
                return None
            words = self._segment_sentence(
                result['sentence_with_error'], result['error_word']
            )
            return {
                'sentence_with_error': result['sentence_with_error'],
                'error_word':          result['error_word'],
                'correct_word':        result['correct_word'],
                'explanation':         result.get('explanation', ''),
                'words':               words,
                'source_test_id':      sentence_dict.get('test_id'),
            }
        except Exception:
            return None

    def _segment_sentence(self, sentence: str, error_word: str) -> list[dict]:
        """Segment sentence into display-ready word objects with error marking."""
        from services.exercise_generation.config import LANG_CHINESE, LANG_JAPANESE
        if self.language_id in (LANG_CHINESE, LANG_JAPANESE):
            tokens = self.lang_processor.tokenize(sentence)
        else:
            tokens = sentence.split()

        words = []
        error_found = False
        for token in tokens:
            clean = token.strip('.,;:!?"\'-()[]').lower()
            is_error = not error_found and clean == error_word.lower()
            if is_error:
                error_found = True
            words.append({'text': token, 'is_error': is_error})
        return words


class OddCollocationOutGenerator(ExerciseGenerator):
    """
    Generates odd_collocation_out exercises.
    LLM generates 4 collocations for a head word - 3 natural, 1 unnatural.
    odd_index is always 3 in stored JSON (frontend shuffles).
    """

    exercise_type = 'odd_collocation_out'
    source_type   = 'collocation'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        col_row = self.db.table('corpus_collocations') \
            .select('head_word, collocate') \
            .eq('id', source_id).single().execute().data
        if not col_row:
            return None

        naturals = self._fetch_natural_collocates(col_row['head_word'], exclude_id=source_id)
        if len(naturals) < 2:
            return None

        template = self.load_prompt_template('odd_collocation_out_generation')
        prompt   = template.format(
            head_word=col_row['head_word'],
            natural_collocates=', '.join(naturals[:3]),
        )
        try:
            result       = self.call_llm(prompt, response_format='json')
            collocations = result.get('collocations', [])
            if len(collocations) != 4:
                return None
            return {
                'head_word':    col_row['head_word'],
                'collocations': collocations,
                'odd_index':    3,
                'explanation':  result.get('explanation', ''),
            }
        except Exception:
            return None

    def _fetch_natural_collocates(self, head_word: str, exclude_id: int) -> list[str]:
        result = self.db.table('corpus_collocations') \
            .select('collocate') \
            .eq('head_word', head_word) \
            .neq('id', exclude_id) \
            .gte('pmi_score', 3.0) \
            .limit(3) \
            .execute()
        return [r['collocate'] for r in (result.data or [])]
