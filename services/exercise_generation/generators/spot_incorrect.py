# services/exercise_generation/generators/spot_incorrect.py

import logging
from services.exercise_generation.base_generator import ExerciseGenerator
from services.exercise_generation.validators import ExerciseValidator
from services.exercise_generation.difficulty import DifficultyCalibrator

logger = logging.getLogger(__name__)


class SpotIncorrectGenerator(ExerciseGenerator):
    """
    Generates spot_incorrect_sentence + spot_incorrect_part pairs.
    One LLM call produces content for both exercise types.
    Overrides generate_batch() because one call -> two exercise rows.
    """

    exercise_type = 'spot_incorrect_sentence'
    source_type   = 'grammar'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        raise NotImplementedError("Use generate_batch() for SpotIncorrectGenerator")

    def generate_batch(
        self,
        sentence_pool: list[dict],
        source_id: int,
        target_count: int,
        generation_batch_id: str,
    ) -> list[dict]:
        validator  = ExerciseValidator()
        calibrator = DifficultyCalibrator()
        results    = []

        triplets = [sentence_pool[i:i+3] for i in range(0, len(sentence_pool) - 2, 3)]

        for triplet in triplets:
            if len(results) >= target_count * 2:
                break
            if len(triplet) < 3:
                continue

            pair = self._generate_pair(triplet, source_id)
            if pair is None:
                continue

            sent_content, part_content = pair
            tier = triplet[0].get('complexity_tier', 'T3')

            for ex_type, content in [
                ('spot_incorrect_sentence', sent_content),
                ('spot_incorrect_part',     part_content),
            ]:
                is_valid, errors = validator.validate(content, ex_type)
                if not is_valid:
                    logger.warning("Validation failed for %s: %s", ex_type, errors)
                    break
                row = self._build_exercise_row(content, triplet[0], source_id, generation_batch_id)
                row['exercise_type'] = ex_type
                row = calibrator.attach_difficulty(row, tier)
                results.append(row)

        return results

    def _generate_pair(
        self, triplet: list[dict], source_id: int
    ) -> tuple[dict, dict] | None:
        correct_texts = [s['sentence'] for s in triplet]
        template      = self.load_prompt_template('spot_incorrect_generation')
        prompt        = template.format(
            sentence_1=correct_texts[0],
            sentence_2=correct_texts[1],
            sentence_3=correct_texts[2],
        )
        try:
            result = self.call_llm(prompt, response_format='json')
        except Exception:
            return None

        incorrect_sentence = result.get('incorrect_sentence', '')
        error_description  = result.get('error_description', '')
        error_type         = result.get('error_type', '')
        parts              = result.get('parts', [])

        if not incorrect_sentence or not parts:
            return None

        sentence_content = {
            'sentences': [
                {'text': correct_texts[0], 'is_correct': True, 'source_test_id': triplet[0].get('test_id')},
                {'text': correct_texts[1], 'is_correct': True, 'source_test_id': triplet[1].get('test_id')},
                {'text': correct_texts[2], 'is_correct': True, 'source_test_id': triplet[2].get('test_id')},
                {'text': incorrect_sentence, 'is_correct': False,
                 'error_description': error_description, 'error_type': error_type},
            ]
        }

        part_content = {
            'sentence': incorrect_sentence,
            'parts':    parts,
        }

        return sentence_content, part_content
