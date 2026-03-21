# services/exercise_generation/generators/cloze.py

from services.exercise_generation.base_generator import ExerciseGenerator


class ClozeGenerator(ExerciseGenerator):
    """
    Generates cloze_completion exercises.
    Per sentence: identifies the target word/phrase, blanks it, calls LLM for
    3 tagged distractors (semantic, form_error, learner_error).
    """

    exercise_type = 'cloze_completion'
    source_type   = 'grammar'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'grammar'):
        super().__init__(db, language_id, model)
        self.source_type = source_type

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        sentence    = sentence_dict['sentence']
        target_word = self._identify_target_word(sentence, source_id)
        if not target_word:
            return None

        blanked = sentence.replace(target_word, '___', 1)
        payload = self._generate_distractors(
            sentence, blanked, target_word, sentence_dict.get('cefr_level', 'B1')
        )
        if not payload:
            return None

        result = {
            'sentence_with_blank': blanked,
            'original_sentence':   sentence,
            'correct_answer':      target_word,
            'options':             [target_word] + payload['distractors'],
            'distractor_tags':     payload['distractor_tags'],
            'explanation':         payload.get('explanation', ''),
            'source_test_id':      sentence_dict.get('test_id'),
        }

        # Include word definition for vocabulary-sourced cloze exercises
        if self.source_type == 'vocabulary':
            definition = self._load_definition(source_id)
            if definition:
                result['word_definition'] = definition

        return result

    def _identify_target_word(self, sentence: str, source_id) -> str | None:
        if self.source_type == 'vocabulary':
            row = self.db.table('dim_word_senses') \
                .select('dim_vocabulary(lemma)') \
                .eq('id', source_id).single().execute().data
            vocab = (row or {}).get('dim_vocabulary') or {}
            word = vocab.get('lemma', '')
            return word if word and word.lower() in sentence.lower() else None

        elif self.source_type == 'collocation':
            row = self.db.table('corpus_collocations').select('collocation_text') \
                .eq('id', source_id).single().execute().data
            col = row.get('collocation_text', '') if row else ''
            return col if col and col.lower() in sentence.lower() else None

        elif self.source_type in ('grammar', 'conversation'):
            return self._identify_target_word_via_llm(sentence)

        return None

    def _identify_target_word_via_llm(self, sentence: str) -> str | None:
        """Use the LLM to pick a meaningful word to blank out."""
        template = self.load_prompt_template('cloze_target_selection')
        prompt = template.format(sentence=sentence)
        try:
            result = self.call_llm(prompt, response_format='json')
            word = result.get('target_word', '').strip()
            if word and word.lower() in sentence.lower():
                return word
        except Exception:
            pass
        return None

    def _load_definition(self, source_id: int) -> str:
        row = self.db.table('dim_word_senses') \
            .select('definition') \
            .eq('id', source_id).single().execute().data
        return (row or {}).get('definition', '')

    def _generate_distractors(
        self, original_sentence: str, blanked: str, correct_answer: str, cefr_level: str,
    ) -> dict | None:
        template = self.load_prompt_template('cloze_distractor_generation')
        prompt   = template.format(
            original_sentence=original_sentence,
            sentence_with_blank=blanked,
            correct_answer=correct_answer,
            cefr_level=cefr_level,
        )
        try:
            result = self.call_llm(prompt, response_format='json')
            distractors = result.get('distractors', [])
            # Remove any distractor that duplicates the correct answer
            distractors = [
                d for d in distractors
                if d.lower().strip() != correct_answer.lower().strip()
            ]
            if len(distractors) < 3:
                return None
            return {
                'distractors':     distractors[:3],
                'distractor_tags': result.get('distractor_tags', {}),
                'explanation':     result.get('explanation', ''),
            }
        except Exception:
            return None
