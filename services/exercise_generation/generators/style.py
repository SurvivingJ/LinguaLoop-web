# services/exercise_generation/generators/style.py

"""
Exercise generators for style pack items.

These generators create exercises that teach learners to recognise and
reproduce an author's or publication's characteristic writing patterns.
Each generator receives a style_pack_item dict (from style_pack_items table)
as the sentence_dict, plus the pack_id as source_id.
"""

import uuid
import logging
from services.exercise_generation.base_generator import ExerciseGenerator

logger = logging.getLogger(__name__)


class _StyleGeneratorBase(ExerciseGenerator):
    """
    Base for all style exercise generators.

    Overrides source_type and _build_exercise_row to work with style_pack_items
    instead of the standard grammar/vocabulary/collocation FK mapping.
    """

    source_type = 'style'

    def _build_exercise_row(
        self, content: dict, sentence_dict: dict, source_id: int, generation_batch_id: str,
    ) -> dict:
        return {
            'id':                    str(uuid.uuid4()),
            'language_id':           self.language_id,
            'exercise_type':         self.exercise_type,
            'source_type':           self.source_type,
            'style_pack_item_id':    sentence_dict.get('id'),
            'content':               content,
            'tags':                  {
                'source_type': 'style',
                'item_type': sentence_dict.get('item_type'),
                'pack_id': source_id,
            },
            'complexity_tier':        sentence_dict.get('complexity_tier'),
            'is_active':             True,
            'generation_batch_id':   generation_batch_id,
        }


class StyleSentenceCompletionGenerator(_StyleGeneratorBase):
    """
    Blank the author's characteristic n-gram in a sentence; pick from 4 options.

    Input sentence_dict should contain:
        item_text: the characteristic n-gram
        item_data: {"text": ..., "frequency": ...}
        item_type: 'frequent_ngram' or 'characteristic_ngram'
    """

    exercise_type = 'style_sentence_completion'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        ngram = sentence_dict.get('item_text', '')
        if not ngram:
            return None

        prompt = (
            f"You are helping create a language exercise about writing style.\n\n"
            f"The author frequently uses the phrase: \"{ngram}\"\n\n"
            f"1. Write a natural sentence (15-25 words) that uses this exact phrase.\n"
            f"2. Generate 3 alternative phrases that could plausibly fill the same position "
            f"but are NOT characteristic of this author.\n\n"
            f"Return JSON: {{"
            f"\"sentence\": \"...\", "
            f"\"sentence_with_blank\": \"... ___ ...\", "
            f"\"correct\": \"{ngram}\", "
            f"\"distractors\": [\"alt1\", \"alt2\", \"alt3\"]}}"
        )

        try:
            result = self.call_llm(prompt, response_format='json')
            distractors = result.get('distractors', [])
            if len(distractors) < 3:
                return None
            return {
                'sentence': result.get('sentence', ''),
                'sentence_with_blank': result.get('sentence_with_blank', ''),
                'correct': ngram,
                'options': [ngram] + distractors[:3],
                'style_item_type': sentence_dict.get('item_type'),
            }
        except Exception:
            return None


class StylePatternMatchGenerator(_StyleGeneratorBase):
    """
    Given 4 sentences, identify which one matches the author's characteristic
    sentence structure pattern.

    Input sentence_dict should contain:
        item_text: the POS template (e.g. "DET NOUN VERB ADP NOUN")
        item_data: {"template": ..., "example": ..., "frequency": ...}
        item_type: 'sentence_pattern'
    """

    exercise_type = 'style_pattern_match'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        data = sentence_dict.get('item_data', {})
        template = sentence_dict.get('item_text', '')
        example = data.get('example', '')
        if not template or not example:
            return None

        prompt = (
            f"You are creating a writing style exercise.\n\n"
            f"The author's characteristic sentence structure follows this POS pattern:\n"
            f"  {template}\n"
            f"Example: \"{example}\"\n\n"
            f"1. Write ONE new sentence that follows this same structure pattern.\n"
            f"2. Write THREE sentences that use clearly different structure patterns "
            f"(e.g., different word order, different clause types).\n\n"
            f"Return JSON: {{"
            f"\"matching_sentence\": \"...\", "
            f"\"other_sentences\": [\"...\", \"...\", \"...\"], "
            f"\"explanation\": \"Brief explanation of the pattern\"}}"
        )

        try:
            result = self.call_llm(prompt, response_format='json')
            others = result.get('other_sentences', [])
            if len(others) < 3:
                return None
            # correct is always index 0; frontend shuffles
            return {
                'sentences': [result['matching_sentence']] + others[:3],
                'correct_index': 0,
                'pattern_template': template,
                'explanation': result.get('explanation', ''),
            }
        except Exception:
            return None


class StyleVoiceTransformGenerator(_StyleGeneratorBase):
    """
    Given a sentence, rewrite it to match the author's syntactic preference
    (e.g., active → passive, or adding subordinate clauses).

    Input sentence_dict should contain:
        item_text: feature label (e.g. "passive")
        item_data: {"feature": "passive_ratio", "value": 0.35}
        item_type: 'syntactic_feature'
    """

    exercise_type = 'style_voice_transform'

    _FEATURE_INSTRUCTIONS = {
        'passive': 'Rewrite the sentence using passive voice.',
        'subordinate clause': 'Rewrite the sentence by adding a subordinate clause.',
        'relative clause': 'Rewrite the sentence by adding a relative clause.',
        'ba construction': 'Rewrite the sentence using a 把-construction.',
        'bei passive': 'Rewrite the sentence using a 被-construction (passive).',
    }

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        feature_label = sentence_dict.get('item_text', '')
        if not feature_label:
            return None

        instruction = self._FEATURE_INSTRUCTIONS.get(
            feature_label, f'Rewrite the sentence to emphasize {feature_label}.'
        )

        prompt = (
            f"You are creating a writing style exercise.\n\n"
            f"Task: {instruction}\n\n"
            f"1. Write a simple sentence (10-20 words) in active/neutral form.\n"
            f"2. Provide the correctly rewritten version.\n"
            f"3. Provide brief grading notes for evaluating student responses.\n\n"
            f"Return JSON: {{"
            f"\"original_sentence\": \"...\", "
            f"\"rewritten_sentence\": \"...\", "
            f"\"instruction\": \"{instruction}\", "
            f"\"grading_notes\": \"...\"}}"
        )

        try:
            result = self.call_llm(prompt, response_format='json')
            if not result.get('original_sentence') or not result.get('rewritten_sentence'):
                return None
            return {
                'original_sentence': result['original_sentence'],
                'rewritten_sentence': result['rewritten_sentence'],
                'instruction': instruction,
                'grading_notes': result.get('grading_notes', ''),
                'feature': feature_label,
            }
        except Exception:
            return None


class StyleTransitionFillGenerator(_StyleGeneratorBase):
    """
    Fill in a blanked discourse marker with the author's preferred transition.

    Input sentence_dict should contain:
        item_text: the discourse marker (e.g. "on the other hand")
        item_data: {"text": ..., "frequency": ...}
        item_type: 'discourse_pattern'
    """

    exercise_type = 'style_transition_fill'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        marker = sentence_dict.get('item_text', '')
        if not marker:
            return None

        prompt = (
            f"You are creating a discourse marker exercise.\n\n"
            f"The author frequently uses the transition: \"{marker}\"\n\n"
            f"1. Write a short paragraph (2-3 sentences) where \"{marker}\" naturally "
            f"connects ideas. Use ___ where the marker goes.\n"
            f"2. Generate 3 alternative transitions that could fit grammatically "
            f"but have different meanings or connotations.\n\n"
            f"Return JSON: {{"
            f"\"paragraph_with_blank\": \"...\", "
            f"\"correct\": \"{marker}\", "
            f"\"distractors\": [\"alt1\", \"alt2\", \"alt3\"]}}"
        )

        try:
            result = self.call_llm(prompt, response_format='json')
            distractors = result.get('distractors', [])
            if len(distractors) < 3:
                return None
            return {
                'paragraph_with_blank': result.get('paragraph_with_blank', ''),
                'correct': marker,
                'options': [marker] + distractors[:3],
            }
        except Exception:
            return None


class StyleImitationGenerator(_StyleGeneratorBase):
    """
    Capstone exercise: write a sentence on a given topic matching the author's style.
    Free-text, LLM-graded.

    Input sentence_dict can be any style item — we use the overall profile context.
    """

    exercise_type = 'style_imitation'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        # Build a style summary from the item's context
        item_type = sentence_dict.get('item_type', '')
        item_text = sentence_dict.get('item_text', '')

        prompt = (
            f"You are creating a writing imitation exercise.\n\n"
            f"The author's style includes this characteristic: "
            f"{item_type.replace('_', ' ')}: \"{item_text}\"\n\n"
            f"1. Choose a simple, everyday topic (e.g. weather, food, travel, work).\n"
            f"2. Write a model sentence on that topic that demonstrates this style feature.\n"
            f"3. Provide grading criteria for evaluating if a student's sentence "
            f"matches this style characteristic.\n\n"
            f"Return JSON: {{"
            f"\"topic\": \"...\", "
            f"\"instruction\": \"Write a sentence about [topic] using ...\", "
            f"\"model_answer\": \"...\", "
            f"\"grading_notes\": \"...\"}}"
        )

        try:
            result = self.call_llm(prompt, response_format='json')
            if not result.get('instruction') or not result.get('model_answer'):
                return None
            return {
                'topic': result.get('topic', ''),
                'instruction': result['instruction'],
                'model_answer': result['model_answer'],
                'grading_notes': result.get('grading_notes', ''),
                'style_feature': f"{item_type}: {item_text}",
            }
        except Exception:
            return None
