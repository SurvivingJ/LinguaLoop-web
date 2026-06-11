# services/exercise_generation/generators/semantic.py

import logging

from services.exercise_generation.base_generator import ExerciseGenerator
from services.exercise_generation.judges.sentence_validity import judge_wrong_sentences

logger = logging.getLogger(__name__)


class SemanticDiscrimGenerator(ExerciseGenerator):
    """
    Generates semantic_discrimination exercises.
    LLM generates 4 sentences: 1 correct usage, 3 plausible-but-wrong usages.
    Correct sentence is always sentences[0] with is_correct=True.

    Every "wrong" sentence is routed through the ladder sentence-validity judge
    before shipping. The judge catches the keyed-answer bug (eval HIGH #4) where
    a polysemous word's "wrong" sentence is actually valid English in another
    sense — there is then no unique correct answer. Rejected wrong sentences are
    dropped; if fewer than 3 clean wrong sentences survive, the generator
    regenerates once and otherwise blocks the item (returns None).
    """

    exercise_type = 'semantic_discrimination'
    source_type   = 'vocabulary'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'vocabulary'):
        super().__init__(db, language_id, model)
        self.source_type = source_type

    def generate_one(self, sentence_dict: dict, source_id) -> dict | None:
        if self.source_type == 'conversation':
            return self._generate_from_sentence(sentence_dict)

        sense_row = self.db.table('dim_word_senses') \
            .select('definition, dim_vocabulary(lemma)') \
            .eq('id', source_id).single().execute().data
        if not sense_row:
            return None

        vocab = sense_row.get('dim_vocabulary') or {}
        word = vocab.get('lemma', '')
        definition = sense_row['definition']
        tier = sentence_dict.get('complexity_tier', 'T3')
        example = sentence_dict.get('sentence', '')

        gen = self._generate_raw(word, definition, tier, example)
        if not gen:
            return None
        correct, incorrect, explanation = gen

        kept_wrong = self._judge_wrong(word, incorrect, explanation)

        # If the judge culled too many, regenerate once and top up from the
        # fresh (already-judged) wrong sentences.
        if len(kept_wrong) < 3:
            logger.info(
                "semantic_discrimination: only %d/%d wrong sentences survived judge for '%s'; retrying",
                len(kept_wrong), len(incorrect), word,
            )
            retry = self._generate_raw(word, definition, tier, example)
            if retry:
                _, retry_incorrect, _ = retry
                kept_wrong = kept_wrong + self._judge_wrong(word, retry_incorrect, explanation)

        if len(kept_wrong) < 3:
            logger.warning(
                "semantic_discrimination: still short after retry (%d wrong) for '%s'; blocking item",
                len(kept_wrong), word,
            )
            return None

        ordered = [correct] + kept_wrong[:3]
        return {'sentences': ordered, 'explanation': explanation, 'target_word': word}

    def _generate_raw(
        self, word: str, definition: str, tier: str, example: str,
    ) -> tuple[dict, list[dict], str] | None:
        """One LLM round-trip → (correct_sentence, incorrect_sentences, explanation)."""
        template = self.load_prompt_template('semantic_discrimination_generation')
        prompt   = template.format(
            word=word, definition=definition,
            complexity_tier=tier, example_sentence=example,
        )
        try:
            result      = self.call_llm(prompt, response_format='json')
            sentences   = result.get('sentences', [])
            explanation = result.get('explanation', '')
            if len(sentences) < 4:
                return None
            correct   = [s for s in sentences if s.get('is_correct')]
            incorrect = [s for s in sentences if not s.get('is_correct')]
            if not correct:
                return None
            return correct[0], incorrect, explanation
        except Exception:
            return None

    def _judge_wrong(self, word: str, incorrect: list[dict], explanation: str) -> list[dict]:
        """Keep only wrong sentences the validity judge does NOT reject.

        A wrong sentence is dropped when the judge rules it actually acceptable
        (valid usage → no unique answer) or mislabeled. Judge errors safe-accept
        (keep) per the judge's failure-safe contract.
        """
        if not incorrect:
            return []
        pairs = [(s.get('text', ''), s.get('reason') or explanation) for s in incorrect]
        outcomes = judge_wrong_sentences(self.db, word, pairs, self.language_id)
        return [
            s for s, o in zip(incorrect, outcomes)
            if o.verdict != 'reject'
        ]


    def _generate_from_sentence(self, sentence_dict: dict) -> dict | None:
        """Generate semantic discrimination from a conversation sentence context."""
        sentence = sentence_dict.get('sentence', '')
        if not sentence:
            return None

        # Pick a key word from the sentence and generate discrimination items
        template = self.load_prompt_template('semantic_discrimination_from_context')
        prompt = template.format(
            sentence=sentence,
            complexity_tier=sentence_dict.get('complexity_tier', 'T3'),
        )
        try:
            result = self.call_llm(prompt, response_format='json')
            sentences = result.get('sentences', [])
            explanation = result.get('explanation', '')
            target_word = result.get('target_word', '')
            if len(sentences) < 4:
                return None
            correct = [s for s in sentences if s.get('is_correct')]
            incorrect = [s for s in sentences if not s.get('is_correct')]
            if not correct:
                return None
            ordered = correct[:1] + incorrect[:3]
            return {
                'sentences': ordered,
                'explanation': explanation,
                'target_word': target_word,
            }
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
