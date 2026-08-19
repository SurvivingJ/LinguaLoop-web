"""LLM generation steps for counter curation (qwen via OpenRouter).

Two calls:
  * classify_counter — assign a counter its semantic group, tier and label, and
    decide whether it is a real counter that counts showable nouns at all.
  * generate_nouns   — propose common nouns that idiomatically take a given
    counter, each with reading, gloss and a 名詞+数詞+助数詞 example phrase.
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm

from .config import GEN_MODEL, GROUPS, PIPELINE, TARGET_NOUNS
from .schemas import CounterMeta, NounList

logger = logging.getLogger(__name__)

_CLASSIFY_SYSTEM = (
    "You are a Japanese linguist specialising in counters (助数詞). Answer ONLY "
    "with valid JSON, no commentary."
)

_GEN_SYSTEM = (
    "You are a Japanese teacher building a counter drill. You output ONLY common, "
    "idiomatic noun-counter pairings that native speakers actually use. Answer "
    "ONLY with valid JSON, no commentary."
)


def classify_counter(counter: str, hint: str = '') -> CounterMeta:
    """Assign a counter its semantic group, tier and label.

    Also asks two gating questions the Mandarin sibling does not need, because
    both failure modes were seen in the first curation pass: whether the token
    is a counter at all, and whether it counts a noun that can be shown to a
    learner.
    """
    prompt = (
        f"The Japanese counter (助数詞) is 「{counter}」."
        f"{(' Context: ' + hint) if hint else ''}\n\n"
        "Return JSON with fields:\n"
        '  counter (the counter itself), reading (its kana reading, e.g. "ほん"),\n'
        f'  group (EXACTLY one of: {", ".join(GROUPS)}),\n'
        "  difficulty_tier (1=JLPT N5 core, 2=N4, 3=N3, 4=N2-N1, 5=rare/literary),\n"
        "  semantic_label (a short English description of what it counts),\n"
        "  is_real_counter (false if this is not actually a Japanese counter),\n"
        "  counts_nouns (see below).\n\n"
        "Set counts_nouns to FALSE when the thing counted is not a noun a learner "
        "could be shown as a drill prompt. Examples where it must be false:\n"
        "  - 階 counts storeys of a building; the counted thing is the floor "
        "itself, not a noun that 'takes' 階.\n"
        "  - 度 counts degrees or occurrences, not objects.\n"
        "  - 番 counts ordinal positions.\n"
        "Answering false here is a correct and useful answer, not a failure. Do "
        "NOT invent a noun list for such a counter."
    )
    return call_llm(
        prompt,
        model=GEN_MODEL,
        temperature=0.0,
        response_format='json_object',
        schema=CounterMeta,
        provider='openrouter',
        system_prompt=_CLASSIFY_SYSTEM,
        pipeline=PIPELINE,
        task_name='classify_counter',
    )


def generate_nouns(counter: str, semantic_label: str = '',
                   n: int = TARGET_NOUNS) -> NounList:
    """Ask for n common nouns that idiomatically take this counter."""
    label = f" ({semantic_label})" if semantic_label else ""
    prompt = (
        f"List {n} common Japanese nouns that idiomatically take the counter "
        f"「{counter}」{label}.\n\n"
        "Rules:\n"
        f"- The noun must genuinely be counted with 「{counter}」 in normal usage.\n"
        "- Prefer high-frequency, concrete nouns a learner would know.\n"
        "- Do NOT include nouns whose only natural counter is つ or 個.\n"
        f"- If a noun's usual counter is something other than 「{counter}」, leave "
        "it out entirely rather than including it as a weak match.\n"
        "- No duplicates. Write each noun as it is normally written.\n"
        "- If a native speaker would ALSO accept a different counter for a noun, "
        "list those in also_acceptable_counters. This matters: the drill marks "
        "every listed counter correct, so an omission teaches a falsehood "
        "(兎 takes both 匹 and 羽).\n\n"
        'Return JSON: {"nouns": [{"noun": "...", "reading": "... (kana)", '
        '"gloss": "... (short English)", "example_phrase": "... (a short '
        f'名詞+数詞+助数詞 phrase such as ペンを三{counter})", '
        '"also_acceptable_counters": ["..."]}]}'
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
