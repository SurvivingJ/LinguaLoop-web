"""
LLM Output Cleaning & Validation Module

Provides a unified pipeline for cleaning and validating text returned by LLMs.
Two main entry points:

  clean_json_response(text) -> str
      Strips markdown code fences and extracts the outermost JSON object/array.
      Does NOT strip markdown inside values — some JSON fields contain intentional
      ** markers (e.g. flashcard front_sentence highlights a word with **word**).

  clean_text(text, **options) -> CleanResult
      Full prose cleaning pipeline for plain-text LLM outputs (translations,
      definitions, story prose, transcripts). Strips markdown artifacts, LLM
      preamble/postamble, normalises whitespace, and optionally validates language.

  validate_language(text, expected_lang) -> (bool, str)
      Language detection via langdetect with heuristic fallback.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── langdetect setup ─────────────────────────────────────────────────────────
# Seed for deterministic, thread-safe detection (important under Flask threads).
try:
    from langdetect import DetectorFactory
    DetectorFactory.seed = 0
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False

# Map langdetect ISO codes → app language codes (cn / en / jp)
_LANGDETECT_TO_APP: dict[str, str] = {
    'zh-cn': 'cn',
    'zh-tw': 'cn',
    'zh':    'cn',
    'ja':    'jp',
    'en':    'en',
}

# ── compiled regexes (module-level for performance) ──────────────────────────
_RE_ZERO_WIDTH   = re.compile(r'[\ufeff\u200b\u200c\u200d]')
_RE_BOLD_ITALIC  = re.compile(r'\*{1,2}(.+?)\*{1,2}', re.DOTALL)
_RE_HEADING      = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_RE_BLOCKQUOTE   = re.compile(r'^>\s?', re.MULTILINE)
_RE_BULLET       = re.compile(r'^(\s*)([-*]|\d+\.)\s+', re.MULTILINE)
_RE_MULTI_NEWLINE = re.compile(r'\n{3,}')
_RE_PLACEHOLDER  = re.compile(r'(\[(?:WORD|BLANK|TARGET|INSERT|FILL)\]|\{(?:WORD|BLANK|TARGET)\}|<(?:WORD|TARGET|BLANK)>)', re.IGNORECASE)

# Preamble patterns: lines/phrases at the start of a response that are not content
_PREAMBLE_PATTERNS = re.compile(
    r'^(?:'
    r'here(?:\s+is|\s+are|\s+\'s)[\s\S]*?[:：]\s*'
    r"|sure[!,.]?\s*"
    r"|certainly[!,.]?\s*"
    r"|of course[!,.]?\s*"
    r"|absolutely[!,.]?\s*"
    r"|great[!,.]?\s*"
    r"|no problem[!,.]?\s*"
    r')',
    re.IGNORECASE,
)

# Postamble: trailing lines that are notes/disclaimers
_POSTAMBLE_LINE = re.compile(
    r'^(?:note|please note|disclaimer|important note)[:\s]',
    re.IGNORECASE,
)

# Self-reference marker (logged as warning, NOT stripped)
_SELF_REFERENCE = re.compile(
    r'\b(as an? (AI|language model|large language model)|I(?:\'m| am) an? (AI|language model))\b',
    re.IGNORECASE,
)


# ── public types ─────────────────────────────────────────────────────────────

@dataclass
class CleanResult:
    """Result of clean_text()."""
    original: str
    cleaned: str
    warnings: list[str] = field(default_factory=list)
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)


# ── JSON response cleaner ─────────────────────────────────────────────────────

def clean_json_response(text: str) -> str:
    """
    Strip markdown code fences and return the outermost JSON object or array.

    Extracts whichever JSON structure ({…} or […]) starts first, ensuring
    arrays like [{…}, {…}] aren't misinterpreted as bare objects.

    Raises ValueError if the input is empty after stripping.
    Returns the cleaned string unchanged if no JSON structure is found
    (lets json.loads produce a clear error for the caller).
    """
    if not text:
        raise ValueError("Empty LLM response")

    # 1. Remove BOM and zero-width chars
    text = _RE_ZERO_WIDTH.sub('', text)

    # 2. Replace non-breaking spaces
    text = text.replace('\u00a0', ' ')

    # 3. Strip markdown code fences
    text = text.strip()
    if text.startswith('```'):
        text = text.replace('```json', '', 1).replace('```', '', 1)
    if text.endswith('```'):
        text = text.rsplit('```', 1)[0]
    text = text.strip()

    # 4. Extract outermost JSON structure — whichever starts first wins
    obj_start = text.find('{')
    obj_end   = text.rfind('}')
    arr_start = text.find('[')
    arr_end   = text.rfind(']')

    has_obj = obj_start != -1 and obj_end != -1 and obj_start < obj_end
    has_arr = arr_start != -1 and arr_end != -1 and arr_start < arr_end

    if has_obj and has_arr:
        # Whichever delimiter appears first is the outermost structure
        if arr_start < obj_start:
            return text[arr_start:arr_end + 1]
        else:
            return text[obj_start:obj_end + 1]
    elif has_obj:
        return text[obj_start:obj_end + 1]
    elif has_arr:
        return text[arr_start:arr_end + 1]

    return text


# ── language validation ───────────────────────────────────────────────────────

def validate_language(
    text: str,
    expected_lang: str,
    *,
    fallback_heuristic: bool = True,
) -> tuple[bool, str]:
    """
    Detect the language of *text* and compare to *expected_lang* (app code:
    'cn', 'en', or 'jp').

    Returns (is_correct, reason_string).

    Strategy:
    1. Try langdetect (if available and text is long enough)
    2. Fall back to Unicode-ratio heuristic from language_detection.py
    """
    if not text or not text.strip():
        return False, 'empty text'

    # Short texts (< 10 meaningful chars) are unreliable for langdetect
    meaningful = [c for c in text if not c.isspace()]
    if len(meaningful) < 10:
        if fallback_heuristic:
            from services.vocabulary.language_detection import check_text_language
            return check_text_language(text, expected_lang)
        return True, 'too short to classify'

    if _LANGDETECT_AVAILABLE:
        try:
            from langdetect import detect, LangDetectException
            detected_iso = detect(text)
            detected_app = _LANGDETECT_TO_APP.get(detected_iso)
            if detected_app is not None:
                return (detected_app == expected_lang), f'langdetect={detected_iso}'
            # Unmapped ISO code — fall through to heuristic
            logger.debug(f"langdetect returned unmapped code '{detected_iso}', using heuristic fallback")
        except Exception as exc:
            logger.debug(f"langdetect failed ({exc}), using heuristic fallback")

    if fallback_heuristic:
        from services.vocabulary.language_detection import check_text_language
        return check_text_language(text, expected_lang)

    return True, 'langdetect unavailable and no fallback'


# ── prose text cleaner ────────────────────────────────────────────────────────

def clean_text(
    text: str,
    *,
    strip_markdown: bool = True,
    strip_preamble: bool = True,
    normalize_whitespace: bool = True,
    min_length: int = 0,
    max_length: int | None = None,
    expected_lang: str | None = None,
    check_placeholders: bool = False,
) -> CleanResult:
    """
    Clean and validate a plain-text LLM response (translation, definition,
    story prose, transcript, etc.).

    Does NOT parse JSON — call clean_json_response() for JSON outputs.

    Args:
        text:               Raw LLM output string.
        strip_markdown:     Remove ** bold **, * italic *, # headings, > quotes,
                            bullet markers, and code fences.
        strip_preamble:     Remove conversational preamble ("Here is...", "Sure!")
                            and trailing note/disclaimer lines.
        normalize_whitespace: Collapse 3+ newlines to 2, strip leading/trailing.
        min_length:         If > 0, add validation error when cleaned text is shorter.
        max_length:         If set, add validation error when cleaned text is longer.
        expected_lang:      App language code ('cn', 'en', 'jp'). If given,
                            validate language and add error on mismatch.
        check_placeholders: If True, flag unfilled placeholder tokens like [WORD].

    Returns:
        CleanResult with .cleaned, .warnings, .is_valid, .validation_errors.
    """
    warnings: list[str] = []
    validation_errors: list[str] = []

    if not text:
        return CleanResult(
            original='',
            cleaned='',
            warnings=[],
            is_valid=False,
            validation_errors=['empty LLM response'],
        )

    cleaned = text

    # Step 1 — BOM and zero-width chars
    cleaned = _RE_ZERO_WIDTH.sub('', cleaned)

    # Step 2 — Non-breaking spaces
    cleaned = cleaned.replace('\u00a0', ' ')

    if strip_markdown:
        # Step 3 — Code fences
        cleaned = cleaned.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.replace('```json', '', 1).replace('```', '', 1)
        if cleaned.endswith('```'):
            cleaned = cleaned.rsplit('```', 1)[0]

        # Step 4 — Bold and italic markers (**text** and *text*)
        cleaned = _RE_BOLD_ITALIC.sub(r'\1', cleaned)

        # Step 5 — Heading markers (# at line start)
        cleaned = _RE_HEADING.sub('', cleaned)

        # Step 6 — Blockquote markers (> at line start)
        cleaned = _RE_BLOCKQUOTE.sub('', cleaned)

        # Step 7 — Bullet / ordered list markers at line start
        cleaned = _RE_BULLET.sub(r'\1', cleaned)

    if strip_preamble:
        # Step 8 — Leading preamble ("Here is your translation:", "Sure!", etc.)
        original_for_preamble = cleaned
        cleaned = _PREAMBLE_PATTERNS.sub('', cleaned).strip()
        if cleaned != original_for_preamble.strip():
            warnings.append('preamble stripped')

        # Step 9 — Trailing postamble lines ("Note: ...", "Please note ...")
        lines = cleaned.splitlines()
        kept_lines = []
        postamble_start = None
        for i, line in enumerate(lines):
            if _POSTAMBLE_LINE.match(line.strip()):
                postamble_start = i
                break
            kept_lines.append(line)
        if postamble_start is not None:
            cleaned = '\n'.join(kept_lines)
            warnings.append('postamble stripped')

    # Step 10 — Self-reference detection (warn, do NOT strip)
    if _SELF_REFERENCE.search(cleaned):
        warnings.append('self-reference detected ("as a language model" or similar)')

    if normalize_whitespace:
        # Step 11 — Collapse excessive newlines
        cleaned = _RE_MULTI_NEWLINE.sub('\n\n', cleaned)
        # Step 12 — Strip leading/trailing whitespace
        cleaned = cleaned.strip()

    # Step 13 — Placeholder detection
    if check_placeholders:
        placeholders = _RE_PLACEHOLDER.findall(cleaned)
        if placeholders:
            validation_errors.append(f'unfilled placeholder tokens: {placeholders}')

    # Step 14 — Length checks
    if min_length and len(cleaned) < min_length:
        validation_errors.append(f'response too short: {len(cleaned)} < {min_length} chars')
    if max_length is not None and len(cleaned) > max_length:
        validation_errors.append(f'response too long: {len(cleaned)} > {max_length} chars')

    # Step 15 — Language validation
    if expected_lang:
        is_correct, reason = validate_language(cleaned, expected_lang)
        if not is_correct:
            validation_errors.append(f'wrong language (expected={expected_lang}, reason={reason})')

    is_valid = len(validation_errors) == 0
    return CleanResult(
        original=text,
        cleaned=cleaned,
        warnings=warnings,
        is_valid=is_valid,
        validation_errors=validation_errors,
    )
