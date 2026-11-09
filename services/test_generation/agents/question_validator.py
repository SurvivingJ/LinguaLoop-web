"""
Question Validator Agent

Validates question format, content quality, and semantic overlap.
"""

import logging
import re
from typing import List, Dict, Optional, Tuple

from services.test_generation import quality_checks as qc

logger = logging.getLogger(__name__)


# Quoted-span extraction for the vocabulary_context hallucination check.
# Each pattern captures the text BETWEEN a matched pair of quote marks.
# Straight single quotes are word-boundary guarded so apostrophes inside
# contractions ("the author's point") are not mistaken for an opening quote.
_QUOTE_PATTERNS = [
    re.compile(r'"([^"]+?)"'),                              # straight double "
    re.compile(r'(?:^|[\s(\[{:])\'([^\']+?)\'(?=[\s).\]}?!,;:]|$)'),  # straight single '
    re.compile('“([^”]+?)”'),                # curly double “ ”
    re.compile('‘([^’]+?)’'),                # curly single ‘ ’
    re.compile('「([^」]+?)」'),                # CJK corner 「 」
    re.compile('『([^』]+?)』'),                # CJK white corner 『 』
]

# Bracket spans — only for vocabulary_context stems (TASK-916). Many ja stems
# mark the target as 文中の（他の人）の意味…, which the quote patterns miss.
_BRACKET_PATTERNS = [
    re.compile('（([^）]+?)）'),                # full-width （ ）
    re.compile(r'\(([^)]+?)\)'),                # ASCII ( )
]

#: Longest span (in characters) treated as a vocabulary item when it has no
#: spaces. "≤ 6 words" is meaningless for CJK: a 30-char span is one "word".
_MAX_SPAN_CHARS_NO_SPACE = 12


def _normalize_text(s: str) -> str:
    """Lowercase + collapse whitespace for a forgiving substring match."""
    return re.sub(r'\s+', ' ', s).strip().lower()


def check_quoted_phrase_in_passage(
    question_text: str, prose: str, include_brackets: bool = False,
) -> Optional[str]:
    """Catch hallucinated quoted phrases in a vocabulary-in-context question.

    Vocabulary questions often quote the target word/phrase (e.g. "What does
    'turn a blind eye' mean?"). When the LLM invents an idiom the passage never
    contains, the question is unanswerable. This is cheaply checkable without
    an LLM call.

    Extracts quoted spans (straight/curly/CJK quote marks) and, for any span of
    six or fewer words that is NOT present in the passage (case-insensitive,
    whitespace-normalized), returns an error string. Longer spans are skipped to
    avoid false positives on paraphrased multi-sentence quotes.

    Returns None when every short quoted span is found in the passage.
    """
    if not question_text or not prose:
        return None

    norm_prose = _normalize_text(prose)
    patterns = _QUOTE_PATTERNS + (_BRACKET_PATTERNS if include_brackets else [])

    for pattern in patterns:
        for raw_span in pattern.findall(question_text):
            span = raw_span.strip()
            if not span:
                continue
            # Only short spans (likely a word/idiom) — long quotes may be
            # legitimately paraphrased excerpts. Spaced text: ≤ 6 words;
            # unspaced (CJK): ≤ 12 characters.
            if ' ' in span:
                if len(span.split()) > 6:
                    continue
            elif len(span) > _MAX_SPAN_CHARS_NO_SPACE:
                continue
            if _normalize_text(span) not in norm_prose:
                return (
                    f"Quoted phrase {span!r} is not present in the passage "
                    f"(possible hallucinated vocabulary item)"
                )
    return None


class QuestionValidator:
    """Validates question quality and format."""

    def __init__(self):
        """Initialize the Question Validator."""
        self.validation_errors = []

    def validate_question(
        self,
        question: Dict,
        prose: str,
        previous_questions: List[str] = None,
        *,
        language_code: Optional[str] = None,
        tier: Optional[int] = None,
        previous: Optional[List[Dict]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a single question.

        Args:
            question: Question dict with question, choices, answer keys
            prose: Original prose text (for context validation)
            previous_questions: Previously validated questions

        Returns:
            Tuple of (is_valid, error_message)

        With ``language_code`` set, the deterministic quality checks
        (services/test_generation/quality_checks.py) also run: results in
        ``reject`` mode fail validation (the generator regenerates); ``flag``
        results are stored on ``question['_quality_flags']``. ``previous``
        (already-kept question dicts) feeds the within-test duplicate checks so
        a duplicate is caught while it can still be regenerated.
        """
        try:
            # Validate structure
            self._validate_structure(question)

            # Validate content
            self._validate_content(question)

            # Vocabulary-in-context questions sometimes quote an idiom/phrase
            # the passage never contains (hallucinated). Catch it for free.
            if question.get('type_code') == 'vocabulary_context':
                phrase_error = check_quoted_phrase_in_passage(
                    question.get('question', ''), prose, include_brackets=True,
                )
                if phrase_error:
                    raise ValueError(phrase_error)

            profile = qc.get_profile(language_code) if language_code in ('ja', 'zh', 'en') else None

            # Check for semantic overlap
            if previous_questions:
                # Legacy whitespace overlap stays as-is (it rejects); the
                # language-aware comparison is the `duplicate_stem` quality
                # check below, which runs in its calibrated mode.
                self._check_overlap(question['question'], previous_questions)

            if profile is not None:
                results = qc.run_question_checks(question, prose, profile, tier)
                # Pairwise duplicates only matter here when they reject (so the
                # generator can regenerate); flags for them come from the
                # test-scope pass in the orchestrator, once, not per attempt.
                dup = qc.pairwise_duplicate_checks(question, previous or [], profile)
                rejects = [r for r in results + dup if r.severity == 'reject']
                if rejects:
                    raise ValueError(f"qc:{rejects[0].code}: {rejects[0].message}")
                flags = [r.to_dict() for r in results]
                if flags:
                    question['_quality_flags'] = flags
                else:
                    question.pop('_quality_flags', None)

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

        # Answer-length giveaways are the `answer_length_outlier` quality
        # check (quality_checks.py), which flags/rejects instead of logging.

    def _check_overlap(
        self,
        new_question: str,
        previous_questions: List[str],
        threshold: float = 0.65,
        profile: Optional['qc.LanguageProfile'] = None,
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
        # Without a profile: whitespace tokens (legacy). With one: the
        # language's tokenizer — ja/zh have no spaces, so whitespace Jaccard
        # never fired for them except on identical strings.
        tok = profile.tokenize if profile is not None else (lambda s: s.lower().split())
        new_words = set(tok(new_question))

        for prev in previous_questions:
            prev_words = set(tok(prev))

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

        # Strip "A. "-style labels the model added itself (the UI labels
        # choices). Only when all four carry one; the answer follows its choice.
        if isinstance(fixed.get('choices'), list) and isinstance(fixed.get('answer'), str):
            fixed['choices'], fixed['answer'], _ = qc.strip_label_prefixes(
                fixed['choices'], fixed['answer'])

        # Fix answer if it's a letter index
        if 'answer' in fixed and 'choices' in fixed:
            answer = fixed['answer']
            if answer in ['A', 'B', 'C', 'D'] and len(fixed['choices']) == 4:
                idx = ord(answer) - ord('A')
                fixed['answer'] = fixed['choices'][idx]

        return fixed
