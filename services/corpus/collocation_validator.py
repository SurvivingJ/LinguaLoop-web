"""
LLM-based Collocation Validation

Accepts a batch of statistically-extracted collocations and asks an LLM
to rate their pedagogical value for language learners.  Collocations that
are cliches, near-literal, or not genuine multi-word units are filtered out.

Called as a post-processing step after statistical extraction in the
ingestion pipeline.
"""

import logging
from services.corpus.llm_client import call_llm

logger = logging.getLogger(__name__)

# Language ID → English name used in prompts
_LANG_NAMES = {1: 'Chinese', 2: 'English', 3: 'Japanese'}

# Process collocations in batches of this size per LLM call
BATCH_SIZE = 80

# Minimum score to keep (1-5 scale)
MIN_PEDAGOGICAL_SCORE = 2


def _build_prompt(collocations: list[dict], language: str) -> str:
    """Build the validation prompt for a batch of collocations."""
    lines = []
    for i, c in enumerate(collocations, 1):
        lines.append(
            f"{i}. \"{c['collocation_text']}\" "
            f"(type={c.get('collocation_type', '?')}, "
            f"freq={c.get('frequency', 0)}, "
            f"POS={c.get('pos_pattern', '?')})"
        )
    collocation_list = '\n'.join(lines)

    return f"""You are a {language} language teaching expert. Below is a list of statistically-extracted collocations from a {language} corpus. Your job is to rate each one for pedagogical value to an intermediate language learner.

Rate each collocation from 1 to 5:
  5 = Highly valuable: natural, frequently-used expression that learners should master (e.g. "make a decision", "strong coffee")
  4 = Useful: genuine collocation worth learning, perhaps slightly less common
  3 = Acceptable: real pattern but lower priority (very common/obvious, or domain-specific)
  2 = Low value: near-literal combination, cliche, or not a genuine multi-word unit
  1 = Remove: noise, fragment, name, or not actually a collocation

Also flag any item that is NOT a genuine collocation of {language} (e.g. code-mixed, a proper noun, or nonsensical).

Return a JSON object with a single key "ratings" containing an array. Each element must have:
- "index": the item number (1-based)
- "score": integer 1-5
- "reason": brief explanation (max 15 words)

Example:
{{"ratings": [{{"index": 1, "score": 5, "reason": "Natural verb-noun collocation, high teaching value"}}, {{"index": 2, "score": 1, "reason": "Proper noun, not a collocation"}}]}}

Collocations to rate:
{collocation_list}"""


def validate_collocations(
    collocations: list[dict],
    language_id: int,
) -> list[dict]:
    """
    Validate a list of collocation dicts via LLM.

    Each collocation dict is enriched with:
      - 'pedagogical_score': int 1-5
      - 'validation_reason': str

    Collocations that fail LLM parsing are kept with score=3 (benefit of doubt).

    Args:
        collocations: List of collocation row dicts (must have 'collocation_text').
        language_id:  1=ZH, 2=EN, 3=JA.

    Returns:
        The same list, enriched with scores. Does NOT filter — caller decides
        the threshold.
    """
    language = _LANG_NAMES.get(language_id, 'Unknown')

    if not collocations:
        return collocations

    # Default all to score 3 (in case LLM fails on a batch)
    for c in collocations:
        c.setdefault('pedagogical_score', 3)
        c.setdefault('validation_reason', '')

    # Process in batches
    for start in range(0, len(collocations), BATCH_SIZE):
        batch = collocations[start:start + BATCH_SIZE]
        prompt = _build_prompt(batch, language)

        try:
            result = call_llm(prompt)
            ratings = result.get('ratings', [])

            # Build index → rating map
            rating_map = {}
            for r in ratings:
                idx = r.get('index')
                if isinstance(idx, int) and 1 <= idx <= len(batch):
                    rating_map[idx] = r

            # Apply ratings to the batch
            for i, c in enumerate(batch, 1):
                if i in rating_map:
                    score = rating_map[i].get('score', 3)
                    if isinstance(score, int) and 1 <= score <= 5:
                        c['pedagogical_score'] = score
                    c['validation_reason'] = rating_map[i].get('reason', '')

            logger.info(
                f"Validated batch of {len(batch)} collocations "
                f"(scores: {[c['pedagogical_score'] for c in batch]})"
            )

        except Exception as exc:
            logger.warning(
                f"LLM validation failed for batch starting at {start}: {exc}. "
                f"Keeping default score=3 for {len(batch)} collocations."
            )

    return collocations
