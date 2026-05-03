# services/vocabulary_ladder/validators.py
"""
Asset validation for the vocabulary ladder pipeline.

Validates LLM output from Prompts 1-3 before storage. Checks structural
correctness (required fields, types, counts) and basic linguistic validity
(substrings exist in sentences, correct option count, etc.).

Does NOT do semantic quality checks — that's for a future QA system.
"""

import logging
import re
from typing import Optional

from config import Config
from services.vocabulary_ladder.config import get_sentence_target

logger = logging.getLogger(__name__)


def contains_target_whole_word(sentence: str, word: str) -> bool:
    """Return True if `word` appears as a whole word in `sentence`.

    Word-boundary aware: rejects "new" inside "knew" or "renewal".
    Case-insensitive.
    """
    if not sentence or not word:
        return False
    return re.search(rf'\b{re.escape(word)}\b', sentence, re.IGNORECASE) is not None


class VocabAssetValidator:
    """Validates word asset content from each prompt."""

    # Valid POS values
    VALID_POS = {
        'noun', 'verb', 'adjective', 'adverb', 'preposition',
        'conjunction', 'pronoun', 'determiner', 'interjection',
    }

    # Valid semantic classes
    VALID_SEMANTIC_CLASSES = {
        'concrete_noun', 'abstract_noun', 'action_verb', 'state_verb',
        'adjective', 'adverb', 'other',
    }

    def validate_prompt1(self, content: dict) -> tuple[bool, list[str]]:
        """Validate Prompt 1 output (core asset).

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Required string fields
        for field in ('pos', 'semantic_class', 'definition'):
            if not content.get(field):
                errors.append(f"Missing required field: {field}")

        # POS validation
        pos = content.get('pos', '')
        if pos and pos not in self.VALID_POS:
            errors.append(f"Invalid POS: '{pos}'. Expected one of {self.VALID_POS}")

        # Semantic class validation
        sc = content.get('semantic_class', '')
        if sc and sc not in self.VALID_SEMANTIC_CLASSES:
            errors.append(f"Invalid semantic_class: '{sc}'. Expected one of {self.VALID_SEMANTIC_CLASSES}")

        # Sentences validation
        sentences = content.get('sentences', [])
        expected = Config.VOCAB_SENTENCES_PER_WORD
        if not isinstance(sentences, list):
            errors.append("'sentences' must be a list")
        elif len(sentences) < expected:
            errors.append(f"Expected {expected} sentences, got {len(sentences)}")
        else:
            for i, sent in enumerate(sentences):
                if not isinstance(sent, dict):
                    errors.append(f"Sentence {i} is not a dict")
                    continue
                text = sent.get('text', '')
                target = get_sentence_target(sent)
                if not text:
                    errors.append(f"Sentence {i} has empty text")
                if not target:
                    errors.append(f"Sentence {i} has empty target_word")
                elif not contains_target_whole_word(text, target):
                    errors.append(
                        f"Sentence {i}: target_word '{target}' is not a whole-word "
                        f"match in text (substring inside another word does not count)"
                    )

        # Morphological forms
        forms = content.get('morphological_forms', [])
        if not isinstance(forms, list) or len(forms) < 2:
            errors.append("Expected at least 2 morphological_forms")

        # IPA
        if not content.get('ipa'):
            errors.append("Missing IPA pronunciation")

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning("Prompt 1 validation failed: %s", errors)

        return is_valid, errors

    def validate_prompt2(
        self, content: dict, active_levels: list[int]
    ) -> tuple[bool, list[str]]:
        """Validate Prompt 2 output (lexical/semantic exercises).

        Checks that each active level in {1, 3, 5, 6} has valid structure.
        """
        errors = []
        p2_levels = {1, 3, 5, 6}
        expected_levels = [lv for lv in active_levels if lv in p2_levels]

        for level in expected_levels:
            key = f'level_{level}'
            if key not in content:
                errors.append(f"Missing {key}")
                continue

            level_data = content[key]

            if level == 6:
                # L6: dict with correct_sentence_index + wrong_sentences
                self._validate_level_6(level_data, errors)
            else:
                # L1, L3, L5: dict with options array
                self._validate_option_level(level, level_data, errors)

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning("Prompt 2 validation failed: %s", errors)

        return is_valid, errors

    def validate_prompt3(
        self, content: dict, active_levels: list[int]
    ) -> tuple[bool, list[str]]:
        """Validate Prompt 3 output (grammar/structure exercises)."""
        errors = []
        p3_levels = {4, 7, 8}
        expected_levels = [lv for lv in active_levels if lv in p3_levels]

        for level in expected_levels:
            key = f'level_{level}'
            if key not in content:
                errors.append(f"Missing {key}")
                continue

            level_data = content[key]

            if level == 4:
                self._validate_level_4(level_data, errors)
            elif level == 7:
                self._validate_level_7(level_data, errors)
            elif level == 8:
                self._validate_option_level(level, level_data, errors)

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning("Prompt 3 validation failed: %s", errors)

        return is_valid, errors

    # ------------------------------------------------------------------
    # Per-level validators
    # ------------------------------------------------------------------

    def _validate_option_level(self, level: int, data: dict, errors: list[str]):
        """Validate a standard MCQ level (L1, L3, L5, L8)."""
        options = data.get('options', [])
        if not isinstance(options, list):
            errors.append(f"Level {level}: 'options' must be a list")
            return

        if len(options) != 4:
            errors.append(f"Level {level}: expected 4 options, got {len(options)}")
            return

        correct_count = sum(1 for o in options if o.get('is_correct'))
        if correct_count != 1:
            errors.append(f"Level {level}: expected exactly 1 correct option, got {correct_count}")

        for i, opt in enumerate(options):
            if not opt.get('text'):
                errors.append(f"Level {level} option {i}: empty text")
            if not opt.get('explanation'):
                errors.append(f"Level {level} option {i}: missing explanation")

    def _validate_level_4(self, data: dict, errors: list[str]):
        """Validate Level 4 morphology slot."""
        self._validate_option_level(4, data, errors)

        if not data.get('correct_form'):
            errors.append("Level 4: missing correct_form")
        if not data.get('base_form'):
            errors.append("Level 4: missing base_form")
        if not data.get('form_label'):
            errors.append("Level 4: missing form_label")

    def _validate_level_6(self, data: dict, errors: list[str]):
        """Validate Level 6 semantic discrimination."""
        if not isinstance(data, dict):
            errors.append("Level 6: expected dict")
            return

        wrong = data.get('wrong_sentences', [])
        if not isinstance(wrong, list) or len(wrong) < 3:
            errors.append(f"Level 6: expected 3 wrong_sentences, got {len(wrong) if isinstance(wrong, list) else 0}")
            return

        for i, s in enumerate(wrong):
            if isinstance(s, dict):
                if not s.get('text'):
                    errors.append(f"Level 6 wrong_sentence {i}: empty text")
            else:
                errors.append(f"Level 6 wrong_sentence {i}: expected dict")

    def _validate_level_7(self, data: dict, errors: list[str]):
        """Validate Level 7 spot-incorrect sentence."""
        if not isinstance(data, dict):
            errors.append("Level 7: expected dict")
            return

        if not data.get('incorrect_sentence'):
            errors.append("Level 7: missing incorrect_sentence")
        if not data.get('corrected_sentence'):
            errors.append("Level 7: missing corrected_sentence")
        if not data.get('error_description'):
            errors.append("Level 7: missing error_description")

        # Incorrect and corrected must differ
        inc = data.get('incorrect_sentence', '')
        cor = data.get('corrected_sentence', '')
        if inc and cor and inc.strip() == cor.strip():
            errors.append("Level 7: incorrect_sentence and corrected_sentence are identical")
