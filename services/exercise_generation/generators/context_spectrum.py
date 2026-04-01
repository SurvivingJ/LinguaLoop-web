# services/exercise_generation/generators/context_spectrum.py

from services.exercise_generation.base_generator import ExerciseGenerator


class ContextSpectrumGenerator(ExerciseGenerator):
    """
    Generates context_spectrum exercises.
    LLM generates register variants (informal/neutral/formal/very formal).
    User selects the variant that fits the given exercise context.
    correct_variant_index is always 0 in stored JSON (frontend shuffles).
    """

    exercise_type = 'context_spectrum'
    source_type   = 'grammar'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        sentence = sentence_dict['sentence']
        template = self.load_prompt_template('context_spectrum_generation')
        prompt   = template.format(
            sentence=sentence,
            complexity_tier=sentence_dict.get('complexity_tier', 'T3'),
        )
        try:
            result   = self.call_llm(prompt, response_format='json')
            variants = result.get('variants', [])
            if len(variants) < 3:
                return None
            context  = result.get('exercise_context', '')
            correct  = result.get('correct_variant', variants[0])
            others   = [v for v in variants if v != correct]
            ordered  = [correct] + others[:3]
            return {
                'variants':              ordered,
                'exercise_context':      context,
                'correct_variant_index': 0,
                'source_test_id':        sentence_dict.get('test_id'),
            }
        except Exception:
            return None
