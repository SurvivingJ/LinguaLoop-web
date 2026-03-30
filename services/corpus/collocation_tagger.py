"""
LLM-based Collocation Semantic Tagger

Assigns domain/theme tags to collocations so they can be grouped
semantically within packs.  E.g. "monetary policy" and "interest rates"
both get tagged ["finance", "economics"].

Called after collocation validation in the ingestion pipeline.
"""

import logging
from services.corpus.llm_client import call_llm

logger = logging.getLogger(__name__)

_LANG_NAMES = {1: 'Chinese', 2: 'English', 3: 'Japanese'}

BATCH_SIZE = 100


def _build_prompt(collocations: list[dict], language: str) -> str:
    numbered = '\n'.join(
        f"{i+1}. \"{c['collocation_text']}\" ({c.get('collocation_type', '?')})"
        for i, c in enumerate(collocations)
    )

    return f"""You are a {language} corpus linguistics expert. Below is a list of collocations extracted from a {language} text. Assign 1-3 semantic domain tags to each collocation.

Use short, consistent tag names from this suggested palette (but you may add others if none fit):
- everyday, social, emotion, body, food, travel, weather, time
- academic, formal, argumentation, cause-effect, comparison
- business, finance, economics, politics, law, technology, science
- literature, narrative, description, dialogue
- grammar-pattern (for collocations that are more structural than semantic)

Return a JSON object with a single key "tags" containing an array. Each element must have:
- "index": item number (1-based)
- "tags": array of 1-3 tag strings (lowercase, hyphenated)

Collocations:
{numbered}"""


def tag_collocations(
    collocations: list[dict],
    language_id: int,
) -> list[dict]:
    """
    Enrich collocation dicts with 'semantic_tags' (list[str]).

    Collocations that fail tagging get an empty tag list.
    Does not modify any other fields.

    Args:
        collocations: List of collocation row dicts.
        language_id:  1=ZH, 2=EN, 3=JA.

    Returns:
        The same list, with 'semantic_tags' added to each dict.
    """
    language = _LANG_NAMES.get(language_id, 'Unknown')

    for c in collocations:
        c.setdefault('semantic_tags', [])

    if not collocations:
        return collocations

    for start in range(0, len(collocations), BATCH_SIZE):
        batch = collocations[start:start + BATCH_SIZE]
        prompt = _build_prompt(batch, language)

        try:
            result = call_llm(prompt)
            tag_entries = result.get('tags', [])

            tag_map = {}
            for entry in tag_entries:
                idx = entry.get('index')
                tags = entry.get('tags', [])
                if isinstance(idx, int) and 1 <= idx <= len(batch):
                    if isinstance(tags, list):
                        tag_map[idx] = [
                            t.lower().strip()
                            for t in tags
                            if isinstance(t, str)
                        ][:3]

            for i, c in enumerate(batch, 1):
                if i in tag_map:
                    c['semantic_tags'] = tag_map[i]

            tagged_count = sum(1 for c in batch if c['semantic_tags'])
            logger.info(
                f"Tagged {tagged_count}/{len(batch)} collocations with semantic tags"
            )

        except Exception as exc:
            logger.warning(
                f"Semantic tagging failed for batch starting at {start}: {exc}"
            )

    return collocations
