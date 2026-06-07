"""LLM generation steps for classifier curation (qwen via OpenRouter).

Two calls:
  * classify_classifier — assign a measure word its semantic group, tier, label
    (used for measure words being promoted out of the 'general' dumping ground).
  * generate_nouns      — propose common nouns that idiomatically take a given
    classifier, each with pinyin, gloss and an 数词+量词+名词 example phrase.
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm

from .config import GEN_MODEL, GROUPS, PIPELINE, TARGET_NOUNS
from .schemas import ClassifierMeta, NounList

logger = logging.getLogger(__name__)

_CLASSIFY_SYSTEM = (
    "You are a Mandarin Chinese linguist specialising in nominal measure words "
    "(classifiers / 量词). Answer ONLY with valid JSON, no commentary."
)

_GEN_SYSTEM = (
    "You are a Mandarin Chinese teacher building a measure-word drill. You output "
    "ONLY common, idiomatic noun-classifier pairings that native speakers actually "
    "use. Answer ONLY with valid JSON, no commentary."
)


def classify_classifier(hanzi: str, hint: str = '') -> ClassifierMeta:
    """Ask the model to assign a measure word its semantic group, tier and label."""
    prompt = (
        f"The Mandarin nominal measure word is 「{hanzi}」."
        f"{(' Context: ' + hint) if hint else ''}\n\n"
        "Return JSON with fields:\n"
        '  hanzi (the character), pinyin (numeric tone, e.g. "tiao2"),\n'
        '  pinyin_display (tone marks, e.g. "tiáo"),\n'
        f'  group (EXACTLY one of: {", ".join(GROUPS)}),\n'
        "  difficulty_tier (1=HSK1-2 core, 2=HSK3-4, 3=HSK5+, 4=rare/advanced),\n"
        "  semantic_label (a short English description of what it counts).\n\n"
        "Choose the group that best matches the nouns it counts. Use 'general' "
        "ONLY if it is a true catch-all with no semantic coherence."
    )
    return call_llm(
        prompt,
        model=GEN_MODEL,
        temperature=0.0,
        response_format='json_object',
        schema=ClassifierMeta,
        provider='openrouter',
        system_prompt=_CLASSIFY_SYSTEM,
        pipeline=PIPELINE,
        task_name='classify_classifier',
    )


def generate_nouns(hanzi: str, semantic_label: str = '', n: int = TARGET_NOUNS) -> NounList:
    """Ask for n common nouns that idiomatically take this classifier (never 个)."""
    label = f" ({semantic_label})" if semantic_label else ""
    prompt = (
        f"List {n} common Mandarin nouns that idiomatically take the measure word "
        f"「{hanzi}」{label}.\n\n"
        "Rules:\n"
        f"- The noun must genuinely be counted with 「{hanzi}」 in normal usage.\n"
        "- Prefer high-frequency, concrete nouns a learner would know.\n"
        "- Do NOT include nouns whose only natural classifier is 个.\n"
        "- No duplicates. Simplified characters only.\n\n"
        'Return JSON: {"nouns": [{"noun": "...", "pinyin": "... (tone marks)", '
        '"gloss": "... (short English)", "example_sentence": "... (a short '
        f"数词+量词+名词 phrase such as 一{hanzi}…)\", "
        '"ge_also_acceptable": true/false (is 个 also natural for this noun?)}]}'
    )
    return call_llm(
        prompt,
        model=GEN_MODEL,
        temperature=0.3,
        response_format='json_object',
        schema=NounList,
        provider='openrouter',
        system_prompt=_GEN_SYSTEM,
        pipeline=PIPELINE,
        task_name='generate_nouns',
    )
