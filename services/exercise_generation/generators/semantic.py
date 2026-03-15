# services/exercise_generation/generators/semantic.py

from services.exercise_generation.base_generator import ExerciseGenerator


class SemanticDiscrimGenerator(ExerciseGenerator):
    """
    Generates semantic_discrimination exercises.
    LLM generates 4 sentences: 1 correct usage, 3 plausible-but-wrong usages.
    Correct sentence is always sentences[0] with is_correct=True.
    """

    exercise_type = 'semantic_discrimination'
    source_type   = 'vocabulary'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'vocabulary'):
        super().__init__(db, language_id, model)
        self.source_type = source_type

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        sense_row = self.db.table('dim_word_senses') \
            .select('definition, dim_vocabulary(lemma)') \
            .eq('id', source_id).single().execute().data
        if not sense_row:
            return None

        vocab = sense_row.get('dim_vocabulary') or {}
        word = vocab.get('lemma', '')
        template = self.load_prompt_template('semantic_discrimination_generation')
        prompt   = template.format(
            word=word,
            definition=sense_row['definition'],
            cefr_level=sentence_dict.get('cefr_level', 'B1'),
            example_sentence=sentence_dict.get('sentence', ''),
        )
        try:
            result     = self.call_llm(prompt, response_format='json')
            sentences  = result.get('sentences', [])
            explanation = result.get('explanation', '')
            if len(sentences) < 4:
                return None
            correct    = [s for s in sentences if s.get('is_correct')]
            incorrect  = [s for s in sentences if not s.get('is_correct')]
            if not correct:
                return None
            ordered    = correct[:1] + incorrect[:3]
            return {'sentences': ordered, 'explanation': explanation}
        except Exception:
            return None


class OddOneOutGenerator(ExerciseGenerator):
    """
    Generates odd_one_out exercises.
    LLM generates 4 words/phrases: 3 share a semantic property, 1 does not.
    odd_index is always 3 in stored JSON (frontend shuffles).
    """

    exercise_type = 'odd_one_out'
    source_type   = 'vocabulary'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'vocabulary'):
        super().__init__(db, language_id, model)
        self.source_type = source_type

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        sense_row = self.db.table('dim_word_senses') \
            .select('definition, dim_vocabulary(lemma)') \
            .eq('id', source_id).single().execute().data
        if not sense_row:
            return None

        vocab = sense_row.get('dim_vocabulary') or {}
        word = vocab.get('lemma', '')
        template = self.load_prompt_template('odd_one_out_generation')
        prompt   = template.format(
            word=word,
            definition=sense_row['definition'],
        )
        try:
            result = self.call_llm(prompt, response_format='json')
            items  = result.get('items', [])
            if len(items) != 4:
                return None
            odd_item  = result.get('odd_item')
            odd_index = items.index(odd_item) if odd_item in items else None
            if odd_index is None:
                return None
            group = [i for i in items if i != odd_item] + [odd_item]
            return {
                'items':           group,
                'odd_index':       3,
                'shared_property': result.get('shared_property', ''),
                'explanation':     result.get('explanation', ''),
            }
        except Exception:
            return None
