"""
Question Validator Agent

Validates question format, content quality, and semantic overlap.
"""

import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class QuestionValidator:
    """Validates question quality and format."""

    def __init__(self):
        """Initialize the Question Validator."""
        self.validation_errors = []

    def validate_question(
        self,
        question: Dict,
        prose: str,
        previous_questions: List[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a single question.

        Args:
            question: Question dict with question, choices, answer keys
            prose: Original prose text (for context validation)
            previous_questions: Previously validated questions

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate structure
            self._validate_structure(question)

            # Validate content
            self._validate_content(question)

            # Check for semantic overlap
            if previous_questions:
                self._check_overlap(question['question'], previous_questions)

            return (True, None)

        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"Question validation failed: {error_msg}")
            return (False, error_msg)

    def validate_all_questions(
        self,
        questions: List[Dict],
        prose: str
    ) -> Tuple[List[Dict], List[str]]:
        """
        Validate a list of questions.

        Args:
            questions: List of question dicts
            prose: Original prose text

        Returns:
            Tuple of (valid_questions, error_messages)
        """
        valid_questions = []
        errors = []
        validated_texts = []

        for i, q in enumerate(questions):
            is_valid, error = self.validate_question(
                q, prose, validated_texts
            )

            if is_valid:
                valid_questions.append(q)
                validated_texts.append(q.get('question', ''))
            else:
                errors.append(f"Q{i+1}: {error}")

        logger.info(f"Validated {len(valid_questions)}/{len(questions)} questions")
        return (valid_questions, errors)

    def _validate_structure(self, question: Dict) -> None:
        """Validate question has required structure."""
        # Check required fields
        required_fields = ['question', 'choices', 'answer']
        for field in required_fields:
            if field not in question:
                raise ValueError(f"Missing required field: {field}")

        # Validate question text
        q_text = question['question']
        if not isinstance(q_text, str) or len(q_text.strip()) < 5:
            raise ValueError("Question text too short or invalid")

        # Validate choices
        choices = question['choices']
        if not isinstance(choices, list):
            raise ValueError("Choices must be a list")
        if len(choices) != 4:
            raise ValueError(f"Expected 4 choices, got {len(choices)}")

        # Validate all choices are non-empty strings
        for i, choice in enumerate(choices):
            if not isinstance(choice, str) or not choice.strip():
                raise ValueError(f"Choice {i+1} is empty or invalid")

        # Validate answer
        answer = question['answer']
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Answer is empty or invalid")

        # Validate answer is in choices
        answer_stripped = answer.strip()
        choices_stripped = [c.strip() for c in choices]
        if answer_stripped not in choices_stripped:
            raise ValueError(f"Answer '{answer_stripped[:30]}' not found in choices")

    def _validate_content(self, question: Dict) -> None:
        """Validate question content quality."""
        q_text = question['question']
        choices = question['choices']
        answer = question['answer']

        # Check question ends with question mark (flexible for different languages)
        if not any(q_text.rstrip().endswith(c) for c in ['?', '？', '؟', '¿']):
            # Not a hard error, just log
            logger.debug(f"Question may not end with question mark: {q_text[:50]}")

        # Check for duplicate choices
        unique_choices = set(c.strip().lower() for c in choices)
        if len(unique_choices) < 4:
            raise ValueError("Duplicate choices detected")

        # Check choice length variety (all shouldn't be same length)
        lengths = [len(c.strip()) for c in choices]
        if len(set(lengths)) == 1 and max(lengths) > 20:
            logger.debug("All choices have same length - may indicate pattern")

        # Check answer isn't obviously the longest or shortest
        answer_len = len(answer.strip())
        if answer_len == max(lengths) and answer_len > 1.5 * min(lengths):
            logger.debug("Answer is notably longest option")

    def _check_overlap(
        self,
        new_question: str,
        previous_questions: List[str],
        threshold: float = 0.65
    ) -> None:
        """
        Check for semantic overlap with previous questions.

        Args:
            new_question: New question text
            previous_questions: List of previous question texts
            threshold: Jaccard similarity threshold

        Raises:
            ValueError: If overlap exceeds threshold
        """
        new_words = set(new_question.lower().split())

        for prev in previous_questions:
            prev_words = set(prev.lower().split())

            # Calculate Jaccard similarity
            intersection = new_words.intersection(prev_words)
            union = new_words.union(prev_words)

            if len(union) > 0:
                similarity = len(intersection) / len(union)
                if similarity >= threshold:
                    raise ValueError(
                        f"Question too similar to existing question "
                        f"(similarity: {similarity:.1%})"
                    )

    def fix_question(self, question: Dict) -> Dict:
        """
        Attempt to fix common question issues.

        Args:
            question: Question dict with potential issues

        Returns:
            Fixed question dict (may still be invalid)
        """
        fixed = question.copy()

        # Ensure question field exists
        if 'question' not in fixed and 'Question' in fixed:
            fixed['question'] = fixed.pop('Question')

        # Ensure choices field exists
        if 'choices' not in fixed and 'Options' in fixed:
            fixed['choices'] = fixed.pop('Options')

        # Ensure answer field exists
        if 'answer' not in fixed and 'Answer' in fixed:
            fixed['answer'] = fixed.pop('Answer')

        # Clean up text fields
        if 'question' in fixed:
            fixed['question'] = fixed['question'].strip()

        if 'choices' in fixed and isinstance(fixed['choices'], list):
            fixed['choices'] = [c.strip() for c in fixed['choices']]

        if 'answer' in fixed:
            fixed['answer'] = fixed['answer'].strip()

        # Fix answer if it's a letter index
        if 'answer' in fixed and 'choices' in fixed:
            answer = fixed['answer']
            if answer in ['A', 'B', 'C', 'D'] and len(fixed['choices']) == 4:
                idx = ord(answer) - ord('A')
                fixed['answer'] = fixed['choices'][idx]

        return fixed
