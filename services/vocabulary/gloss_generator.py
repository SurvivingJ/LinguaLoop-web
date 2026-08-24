"""
Cross-language gloss generator.

Translates an existing dim_word_senses definition into a DIFFERENT language
than the word's own -- e.g. an English gloss for a Japanese word's Japanese
definition. This is deliberately translation-only (no independent
cross-lingual generation): it takes a definition that already exists and
already carries the right register (simple/standard), and renders it in
another language.

Output is written back as an ADDITIONAL dim_word_senses row: same vocab_id,
sense_rank, and definition_level as the source row, but definition_language_id
set to the gloss language and source='llm_gloss'. It never touches the
source row's own sense_id -- everything that already references that id
(word_assets, exercises, user_word_ladder, ...) is unaffected.

See scripts/backfill_gloss_definitions.py for the batch driver.
"""

import logging

from services.llm_service import call_llm
from services.vocabulary.language_detection import check_text_language

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
}

TASK_NAME = 'vocab_gloss_translation'


def build_gloss_prompt(
    lemma: str,
    source_lang_code: str,
    target_lang_code: str,
    definition: str,
    example_sentence: str | None = None,
) -> str:
    """Build the translation prompt for one definition."""
    source_lang = LANGUAGE_NAMES.get(source_lang_code, source_lang_code)
    target_lang = LANGUAGE_NAMES.get(target_lang_code, target_lang_code)

    example_line = ""
    if example_sentence and example_sentence.strip():
        example_line = (
            f'Example sentence (for context only, do not translate): '
            f'"{example_sentence.strip()}"\n'
        )

    return (
        f'Translate this dictionary definition of the {source_lang} word '
        f'"{lemma}" into {target_lang}.\n\n'
        f'Definition to translate: "{definition}"\n'
        f'{example_line}\n'
        'Rules:\n'
        f'- Write a natural {target_lang} definition, not a word-for-word '
        'translation of the source definition.\n'
        f'- A {target_lang} reader who has never seen "{lemma}" should '
        'understand what it means from your definition alone.\n'
        '- Keep it about the same length as the source definition.\n'
        f'- Output ONLY in {target_lang}. Do not include the word '
        f'"{lemma}" itself in your definition.\n\n'
        'Reply with ONLY a JSON object: {"definition": "..."}'
    )


def translate_definition(
    lemma: str,
    source_lang_code: str,
    target_lang_code: str,
    definition: str,
    example_sentence: str | None,
    model: str,
) -> str | None:
    """Translate one definition into the target language.

    Returns the translated text, or None on failure / a response that fails
    the target-language heuristic check (better to skip a gloss row than
    write one in the wrong language).
    """
    prompt = build_gloss_prompt(
        lemma, source_lang_code, target_lang_code, definition, example_sentence,
    )

    try:
        raw = call_llm(
            prompt,
            model=model,
            provider='openrouter',
            temperature=0.0,
            max_tokens=200,
            response_format='json',
            pipeline='vocab_glosses',
            task_name=TASK_NAME,
            language_code=target_lang_code,
        )
    except Exception as e:
        logger.warning(
            "Gloss translation failed for '%s' (%s->%s): %s",
            lemma, source_lang_code, target_lang_code, e,
        )
        return None

    if not isinstance(raw, dict):
        return None

    translated = str(raw.get('definition', '') or '').strip()
    if not translated:
        return None

    ok, reason = check_text_language(translated, target_lang_code)
    if not ok:
        logger.warning(
            "Gloss for '%s' (%s->%s) failed language check (%s): %s",
            lemma, source_lang_code, target_lang_code, reason, translated[:80],
        )
        return None

    return translated
