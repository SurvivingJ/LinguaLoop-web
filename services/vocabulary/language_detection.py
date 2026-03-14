"""
Heuristic language detection for word sense definitions.

Checks whether a text is written in the expected language based on
character-class ratios. Used by both the validation script and
the SenseGenerator to catch wrong-language definitions.
"""


def check_text_language(text: str, expected_lang_code: str) -> tuple[bool, str]:
    """
    Heuristic check that text is in the expected language.

    Args:
        text: The text to check (definition or example sentence)
        expected_lang_code: 'cn', 'jp', or 'en'

    Returns:
        (is_correct_language, reason)
    """
    if not text or not text.strip():
        return False, 'empty'

    # Strip whitespace and punctuation for ratio calculation
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return False, 'empty after stripping'

    total = len(chars)

    if expected_lang_code == 'cn':
        # Chinese definitions should contain Chinese characters
        cn_chars = sum(1 for c in chars if '\u4e00' <= c <= '\u9fff')
        latin_chars = sum(1 for c in chars if c.isascii() and c.isalpha())
        ratio = cn_chars / total

        if latin_chars > total * 0.5:
            return False, f'mostly Latin ({latin_chars}/{total}), expected Chinese'
        if ratio < 0.2:
            return False, f'low Chinese char ratio ({cn_chars}/{total}={ratio:.0%})'
        return True, 'ok'

    elif expected_lang_code == 'jp':
        # Japanese definitions should contain Japanese characters
        jp_chars = sum(
            1 for c in chars
            if '\u3040' <= c <= '\u30ff'  # hiragana + katakana
            or '\u4e00' <= c <= '\u9fff'  # kanji
        )
        latin_chars = sum(1 for c in chars if c.isascii() and c.isalpha())
        ratio = jp_chars / total

        if latin_chars > total * 0.5:
            return False, f'mostly Latin ({latin_chars}/{total}), expected Japanese'
        if ratio < 0.2:
            return False, f'low Japanese char ratio ({jp_chars}/{total}={ratio:.0%})'
        return True, 'ok'

    elif expected_lang_code == 'en':
        # English definitions should be mostly Latin characters
        cjk_chars = sum(
            1 for c in chars
            if '\u4e00' <= c <= '\u9fff'
            or '\u3040' <= c <= '\u30ff'
        )
        if cjk_chars > total * 0.3:
            return False, f'too many CJK chars ({cjk_chars}/{total}), expected English'
        return True, 'ok'

    else:
        # Unknown language code — can't validate
        return True, f'no heuristic for {expected_lang_code}'
