"""
Conversation Quality Checker

Multi-dimensional quality scoring for generated conversations.
Evaluates language consistency, repetition, turn length variance,
and speaker distinctiveness.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from langdetect import detect, LangDetectException

from .config import conv_gen_config

logger = logging.getLogger(__name__)

# langdetect ISO 639-1 codes for our supported languages
LANGDETECT_CODE_MAP = {
    1: 'zh-cn',  # Chinese
    2: 'en',     # English
    3: 'ja',     # Japanese
}

# Languages that use character-level tokenization
CJK_LANGUAGE_IDS = {1, 3}

# Minimum character length for reliable language detection
MIN_CHARS_FOR_LANGDETECT = 10
MIN_CHARS_FOR_LANGDETECT_CJK = 20


@dataclass
class QualityResult:
    """Result of a conversation quality check."""
    score: float                              # Weighted composite 0.0-1.0
    passed: bool                              # score >= threshold
    dimensions: dict[str, float] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


class ConversationQualityChecker:
    """Multi-dimensional quality scoring for generated conversations."""

    WEIGHTS = {
        'language_consistency': 0.40,
        'repetition': 0.30,
        'turn_length_variance': 0.15,
        'speaker_distinctiveness': 0.15,
    }

    def check(
        self,
        turns: list[dict],
        language_id: int,
        language_code: str | None = None,
    ) -> QualityResult:
        """
        Score a conversation on 4 dimensions.

        Args:
            turns: List of turn dicts with 'text', 'speaker', 'turn' keys.
            language_id: Language ID (1=Chinese, 2=English, 3=Japanese).
            language_code: Optional langdetect code override.

        Returns:
            QualityResult with composite score and per-dimension breakdown.
        """
        # Pre-check: turn count must be in valid range
        turn_count = len(turns)
        if turn_count < conv_gen_config.turns_min or turn_count > conv_gen_config.turns_max:
            return QualityResult(
                score=0.0,
                passed=False,
                dimensions={k: 0.0 for k in self.WEIGHTS},
                details={'reason': f'Turn count {turn_count} outside range '
                         f'[{conv_gen_config.turns_min}, {conv_gen_config.turns_max}]'},
            )

        if not turns:
            return QualityResult(score=0.0, passed=False,
                                 details={'reason': 'Empty turns'})

        # Always prefer our own langdetect code map (keyed by language_id)
        # over the DB language_code which may use non-langdetect codes (e.g. 'cn')
        expected_lang = LANGDETECT_CODE_MAP.get(language_id) or language_code or 'en'
        is_cjk = language_id in CJK_LANGUAGE_IDS

        dimensions = {}
        details = {}

        # 1. Language consistency
        lang_score, lang_details = self._score_language_consistency(
            turns, expected_lang, is_cjk
        )
        dimensions['language_consistency'] = lang_score
        details['language_consistency'] = lang_details

        # 2. Repetition
        rep_score, rep_details = self._score_repetition(turns, is_cjk)
        dimensions['repetition'] = rep_score
        details['repetition'] = rep_details

        # 3. Turn length variance
        var_score, var_details = self._score_turn_length_variance(turns, is_cjk)
        dimensions['turn_length_variance'] = var_score
        details['turn_length_variance'] = var_details

        # 4. Speaker distinctiveness
        dist_score, dist_details = self._score_speaker_distinctiveness(
            turns, is_cjk
        )
        dimensions['speaker_distinctiveness'] = dist_score
        details['speaker_distinctiveness'] = dist_details

        # Weighted composite
        composite = sum(
            dimensions[k] * self.WEIGHTS[k] for k in self.WEIGHTS
        )
        composite = round(max(0.0, min(1.0, composite)), 3)

        logger.info(
            "  QC dimensions: lang=%.3f rep=%.3f var=%.3f dist=%.3f -> %.3f",
            dimensions['language_consistency'],
            dimensions['repetition'],
            dimensions['turn_length_variance'],
            dimensions['speaker_distinctiveness'],
            composite,
        )

        return QualityResult(
            score=composite,
            passed=composite >= conv_gen_config.min_quality_score,
            dimensions=dimensions,
            details=details,
        )

    def _score_language_consistency(
        self, turns: list[dict], expected_lang: str, is_cjk: bool = False,
    ) -> tuple[float, dict]:
        """
        Check what fraction of turns are in the expected language.
        Skips turns shorter than MIN_CHARS_FOR_LANGDETECT.
        Returns (score 0.0-1.0, details dict).
        """
        min_chars = MIN_CHARS_FOR_LANGDETECT_CJK if is_cjk else MIN_CHARS_FOR_LANGDETECT
        texts = [t.get('text', '') for t in turns]
        checked = 0
        violations = 0
        violation_turns = []

        for i, text in enumerate(texts):
            if len(text) < min_chars:
                continue
            checked += 1
            try:
                detected = detect(text)
                if not self._lang_matches(detected, expected_lang):
                    violations += 1
                    violation_turns.append(i)
                    logger.debug(
                        "  Lang violation turn %d: detected=%s expected=%s text=%.40s",
                        i, detected, expected_lang, text,
                    )
            except LangDetectException:
                violations += 1
                violation_turns.append(i)

        if checked == 0:
            # All turns too short to check — assume ok
            return 1.0, {'checked': 0, 'violations': 0}

        score = 1.0 - (violations / checked)
        return round(score, 3), {
            'checked': checked,
            'violations': violations,
            'violation_turns': violation_turns[:5],
        }

    def _score_repetition(
        self, turns: list[dict], is_cjk: bool,
    ) -> tuple[float, dict]:
        """
        Measure consecutive token repetition across the conversation.
        Returns (score 0.0-1.0, details dict). Higher = less repetition.
        """
        full_text = ' '.join(t.get('text', '') for t in turns)

        if is_cjk:
            # Word-level tokenization for CJK — character-level inflates
            # repetition because common single chars repeat naturally.
            try:
                import jieba
                tokens = jieba.lcut(full_text)
                tokens = [t for t in tokens if t.strip()]
            except ImportError:
                tokens = list(full_text.replace(' ', ''))
        else:
            tokens = full_text.lower().split()

        if len(tokens) < 2:
            return 0.5, {'token_count': len(tokens), 'repetition_ratio': 0.0}

        repeated = sum(
            1 for i in range(1, len(tokens)) if tokens[i] == tokens[i - 1]
        )
        rep_ratio = repeated / len(tokens)

        # Penalise: ratio * 2.5, capped at 1.0 penalty
        penalty = min(rep_ratio * 2.5, 1.0)
        score = round(1.0 - penalty, 3)

        return score, {
            'token_count': len(tokens),
            'repetition_ratio': round(rep_ratio, 4),
        }

    def _score_turn_length_variance(
        self, turns: list[dict], is_cjk: bool = False,
    ) -> tuple[float, dict]:
        """
        Score based on standard deviation of turn character lengths.
        Very uniform lengths suggest robotic output.
        CJK characters convey more meaning per char, so thresholds are lower.
        Returns (score 0.0-1.0, details dict).
        """
        lengths = [len(t.get('text', '')) for t in turns]
        std = float(np.std(lengths))

        # CJK conversations have naturally shorter turns (fewer chars = more meaning)
        if is_cjk:
            if std < 3:
                score = 0.2
            elif std < 8:
                score = 0.6
            elif std <= 50:
                score = 1.0
            else:
                score = 0.7
        else:
            if std < 5:
                score = 0.2
            elif std < 15:
                score = 0.6
            elif std <= 80:
                score = 1.0
            else:
                score = 0.7

        return score, {'std': round(std, 2), 'lengths': lengths}

    def _score_speaker_distinctiveness(
        self, turns: list[dict], is_cjk: bool,
    ) -> tuple[float, dict]:
        """
        Measure lexical distinctiveness between speakers using Jaccard distance.
        Returns (score 0.0-1.0, details dict).
        """
        speakers = set(t.get('speaker') for t in turns)
        if len(speakers) < 2:
            return 0.0, {'reason': 'fewer than 2 speakers'}

        # Split turns by even/odd index (persona A vs B)
        a_texts = [t['text'] for t in turns if t.get('turn', 0) % 2 == 0]
        b_texts = [t['text'] for t in turns if t.get('turn', 0) % 2 != 0]

        vocab_a = self._tokenize_to_set(' '.join(a_texts), is_cjk)
        vocab_b = self._tokenize_to_set(' '.join(b_texts), is_cjk)

        union = vocab_a | vocab_b
        if not union:
            return 0.0, {'reason': 'empty vocabulary'}

        symmetric_diff = (vocab_a - vocab_b) | (vocab_b - vocab_a)
        jaccard_distance = len(symmetric_diff) / len(union)

        return round(jaccard_distance, 3), {
            'vocab_a_size': len(vocab_a),
            'vocab_b_size': len(vocab_b),
            'unique_tokens': len(symmetric_diff),
            'jaccard_distance': round(jaccard_distance, 3),
        }

    @staticmethod
    def _lang_matches(detected: str, expected: str) -> bool:
        """Check if detected language matches expected, using prefix matching.

        langdetect returns variants like 'zh-cn', 'zh-tw' for Chinese.
        We consider any 'zh-*' variant a match when expected is 'zh-cn'.
        """
        if detected == expected:
            return True
        # Prefix match: 'zh-tw' matches 'zh-cn' (both are Chinese)
        d_prefix = detected.split('-')[0]
        e_prefix = expected.split('-')[0]
        return d_prefix == e_prefix

    @staticmethod
    def _tokenize_to_set(text: str, is_cjk: bool) -> set[str]:
        """Tokenize text to a set of tokens for vocabulary comparison."""
        if is_cjk:
            # Word-level tokenization for CJK — character-level gives
            # artificially low distinctiveness because common chars
            # (的、了、是、我) appear in every speaker's vocabulary.
            try:
                import jieba
                tokens = jieba.lcut(text)
                # Filter out single-char function words and punctuation
                return {t for t in tokens if len(t) > 1 and not t.isascii()}
            except ImportError:
                return set(text.replace(' ', ''))
        return set(text.lower().split())
