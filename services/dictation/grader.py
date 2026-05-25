"""Dictation transcript grader.

Public API: grade_dictation(correct, user, language_code) -> GradingResult.

Algorithm:
  1. Normalize both transcripts (lowercase, strip punctuation, strip diacritics).
  2. Tokenize per language (whitespace for most, jieba for Chinese).
  3. Run difflib.SequenceMatcher.get_opcodes() to align the token streams.
  4. For each aligned pair: exact match OR Levenshtein distance ≤ 1 on
     words ≥ 4 chars → correct. Insertions (extra user words) are recorded
     for the UI diff but do NOT count toward word_total.

The result is shipped to process_dictation_submission as
{word_correct, word_total, replay_count, diff_payload}.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import List, Literal, Optional

from services.dictation.tokenizer import normalize, tokenize


OpCode = Literal["equal", "replace", "insert", "delete"]


@dataclass
class WordDiff:
    """Per-token alignment record for the result-screen diff.

    op:
      - 'equal'   → tokens match exactly (case/diacritics already normalized)
      - 'replace' → both sides had a token here but they differ
      - 'insert'  → extra word in user input that wasn't in canonical
      - 'delete'  → canonical word the user missed

    is_correct: final verdict after Levenshtein fuzzy tolerance.
    sense_id: filled by the Flask handler post-grade, never by the grader.
    """

    op: OpCode
    correct: Optional[str]
    user: Optional[str]
    is_correct: bool
    sense_id: Optional[int] = None


@dataclass
class GradingResult:
    word_correct: int
    word_total: int
    accuracy: float
    diff: List[WordDiff] = field(default_factory=list)
    canonical_tokens: List[str] = field(default_factory=list)
    user_tokens: List[str] = field(default_factory=list)

    def diff_payload(self) -> list[dict]:
        """Serialize the diff for jsonb storage."""
        return [asdict(d) for d in self.diff]


# Words shorter than this don't get Levenshtein tolerance — a 1-char edit on
# a 3-char word is a meaningful difference (e.g. "cat" vs "bat").
_FUZZY_MIN_LEN = 4

# Maximum Levenshtein distance for a fuzzy match on words ≥ _FUZZY_MIN_LEN.
_FUZZY_MAX_DISTANCE = 1


def _levenshtein(a: str, b: str, max_distance: int = _FUZZY_MAX_DISTANCE) -> int:
    """Bounded Levenshtein distance.

    Returns max_distance + 1 as soon as the distance is known to exceed
    max_distance — avoids the full O(m*n) computation when we only care
    "is it close?". Pure Python; no C extension dependency.
    """
    if a == b:
        return 0
    if abs(len(a) - len(b)) > max_distance:
        return max_distance + 1

    # Ensure a is the shorter string (smaller working array).
    if len(a) > len(b):
        a, b = b, a

    prev = list(range(len(a) + 1))
    for j, cb in enumerate(b, start=1):
        curr = [j] + [0] * len(a)
        row_min = curr[0]
        for i, ca in enumerate(a, start=1):
            cost = 0 if ca == cb else 1
            curr[i] = min(
                prev[i] + 1,        # deletion
                curr[i - 1] + 1,    # insertion
                prev[i - 1] + cost, # substitution
            )
            if curr[i] < row_min:
                row_min = curr[i]
        # Early-exit: every value in the row already exceeds the budget.
        if row_min > max_distance:
            return max_distance + 1
        prev = curr

    return prev[-1]


def _fuzzy_equal(a: str, b: str) -> bool:
    """Token-level equality with bounded Levenshtein tolerance."""
    if a == b:
        return True
    if len(a) < _FUZZY_MIN_LEN or len(b) < _FUZZY_MIN_LEN:
        return False
    return _levenshtein(a, b) <= _FUZZY_MAX_DISTANCE


def grade_dictation(
    correct_transcript: str,
    user_transcript: str,
    language_code: str,
) -> GradingResult:
    """Grade a typed transcript against the canonical one.

    Args:
        correct_transcript: The original passage text.
        user_transcript:    What the user typed.
        language_code:      ISO 639-1: 'zh', 'en', 'es', 'ja', etc. Controls tokenization.

    Returns:
        GradingResult with per-token diff, counts, and overall accuracy.

    The result's diff list contains one WordDiff per opcode-pair:
        - 'equal' / 'replace' blocks emit one entry per token pair.
        - 'delete' blocks emit one entry per canonical-side token (counts against total).
        - 'insert' blocks emit one entry per user-side token (display only, never counted).
    """
    canonical_norm = normalize(correct_transcript)
    user_norm = normalize(user_transcript)

    canonical = tokenize(canonical_norm, language_code)
    user = tokenize(user_norm, language_code)

    diff: List[WordDiff] = []
    word_correct = 0
    word_total = 0

    matcher = SequenceMatcher(a=canonical, b=user, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                tok = canonical[i1 + k]
                diff.append(WordDiff(op="equal", correct=tok, user=tok, is_correct=True))
                word_total += 1
                word_correct += 1

        elif tag == "replace":
            # Zip-align overlapping pairs, then trailing tokens become insert/delete.
            overlap = min(i2 - i1, j2 - j1)
            for k in range(overlap):
                c_tok = canonical[i1 + k]
                u_tok = user[j1 + k]
                ok = _fuzzy_equal(c_tok, u_tok)
                diff.append(WordDiff(op="replace", correct=c_tok, user=u_tok, is_correct=ok))
                word_total += 1
                if ok:
                    word_correct += 1
            # Extra canonical tokens (user missed them)
            for k in range(overlap, i2 - i1):
                c_tok = canonical[i1 + k]
                diff.append(WordDiff(op="delete", correct=c_tok, user=None, is_correct=False))
                word_total += 1
            # Extra user tokens (display only)
            for k in range(overlap, j2 - j1):
                u_tok = user[j1 + k]
                diff.append(WordDiff(op="insert", correct=None, user=u_tok, is_correct=False))

        elif tag == "delete":
            for k in range(i2 - i1):
                c_tok = canonical[i1 + k]
                diff.append(WordDiff(op="delete", correct=c_tok, user=None, is_correct=False))
                word_total += 1

        elif tag == "insert":
            for k in range(j2 - j1):
                u_tok = user[j1 + k]
                diff.append(WordDiff(op="insert", correct=None, user=u_tok, is_correct=False))

    accuracy = (word_correct / word_total) if word_total > 0 else 0.0

    return GradingResult(
        word_correct=word_correct,
        word_total=word_total,
        accuracy=accuracy,
        diff=diff,
        canonical_tokens=canonical,
        user_tokens=user,
    )
