# services/exercise_generation/generators/cloze.py

import logging

from services.exercise_generation.base_generator import ExerciseGenerator
from services.exercise_generation.cloze_judge import filter_distractors

logger = logging.getLogger(__name__)


class ClozeGenerator(ExerciseGenerator):
    """
    Generates cloze_completion exercises.
    Per sentence: identifies the target word/phrase, blanks it, calls LLM for
    3 tagged distractors (semantic, form_error, learner_error), then routes
    them through cloze_judge to drop distractors that could themselves pass
    as the correct answer.
    """

    exercise_type = 'cloze_completion'
    source_type   = 'grammar'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'grammar'):
        super().__init__(db, language_id, model)
        self.source_type = source_type
        self._last_judge_meta: dict | None = None

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        self._last_judge_meta = None

        sentence    = sentence_dict['sentence']
        target_word = self._identify_target_word(sentence, source_id)
        if not target_word:
            return None

        blanked = sentence.replace(target_word, '___', 1)
        tier = sentence_dict.get('complexity_tier', 'T3')

        payload = self._generate_distractors(sentence, blanked, target_word, tier)
        if not payload:
            return None

        distractors = payload['distractors']
        kept, judge_meta = filter_distractors(
            self.db,
            sentence_with_blank=blanked,
            correct_answer=target_word,
            distractors=distractors,
            language_id=self.language_id,
        )

        # If the judge rejected any, ask the generator for a fresh batch and
        # judge again. One naive retry — if still short, skip this sentence.
        if len(kept) < 3:
            logger.info(
                "cloze_judge rejected %d/%d distractors; retrying",
                judge_meta['rejected'], len(distractors),
            )
            retry = self._generate_distractors(sentence, blanked, target_word, tier)
            if retry:
                retry_kept, retry_meta = filter_distractors(
                    self.db,
                    sentence_with_blank=blanked,
                    correct_answer=target_word,
                    distractors=retry['distractors'],
                    language_id=self.language_id,
                )
                if len(retry_kept) >= 3:
                    payload = retry
                    kept = retry_kept
                    judge_meta = {
                        'rejected': judge_meta['rejected'] + retry_meta['rejected'],
                        'rejected_items': judge_meta['rejected_items']
                                          + retry_meta['rejected_items'],
                        'model': retry_meta['model'],
                        'version': retry_meta['version'],
                    }

        if len(kept) < 3:
            logger.warning(
                "cloze_judge still short after retry (%d kept) for: %s",
                len(kept), sentence[:60],
            )
            return None

        kept = kept[:3]
        self._last_judge_meta = judge_meta

        result = {
            'sentence_with_blank': blanked,
            'original_sentence':   sentence,
            'correct_answer':      target_word,
            'options':             [target_word] + kept,
            'distractor_tags':     {
                d: payload['distractor_tags'].get(d, '')
                for d in kept
            },
            'explanation':         payload.get('explanation', ''),
            'source_test_id':      sentence_dict.get('test_id'),
        }

        # Include word definition for vocabulary-sourced cloze exercises
        if self.source_type == 'vocabulary':
            definition = self._load_definition(source_id)
            if definition:
                result['word_definition'] = definition

        return result

    def _build_tags(self, source_id: int, sentence_dict: dict) -> dict:
        tags = super()._build_tags(source_id, sentence_dict)
        if self._last_judge_meta is not None:
            tags['cloze_judge'] = self._last_judge_meta
        return tags

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
        self, original_sentence: str, blanked: str, correct_answer: str, complexity_tier: str,
    ) -> dict | None:
        template = self.load_prompt_template('cloze_distractor_generation')
        prompt   = template.format(
            original_sentence=original_sentence,
            sentence_with_blank=blanked,
            correct_answer=correct_answer,
            complexity_tier=complexity_tier,
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
