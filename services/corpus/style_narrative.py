"""
Style Profile Narrative Generator

Takes a style profile dict (from StyleAnalyzer.analyze()) and generates
a human-readable summary of the corpus's stylistic characteristics via LLM.

The narrative highlights what makes the text distinctive and identifies
the top teachable features for language learners.
"""

import json
import logging
from services.corpus.llm_client import call_llm

logger = logging.getLogger(__name__)

_LANG_NAMES = {1: 'Chinese', 2: 'English', 3: 'Japanese'}


def _summarise_profile(profile: dict) -> str:
    """
    Condense a style profile dict into a compact text representation
    suitable for an LLM prompt.  Only includes non-empty, meaningful data.
    """
    parts = []

    parts.append(
        f"Corpus size: {profile.get('total_tokens', 0):,} tokens, "
        f"{profile.get('total_sentences', 0):,} sentences"
    )

    # Vocabulary profile
    vocab = profile.get('vocabulary_profile') or {}
    if vocab:
        parts.append(
            f"Vocabulary: TTR={vocab.get('ttr', '?')}, "
            f"MATTR={vocab.get('mattr', '?')}, "
            f"hapax ratio={vocab.get('hapax_ratio', '?')}, "
            f"avg word length={vocab.get('avg_word_length', '?')} chars, "
            f"unique words={vocab.get('unique_words', '?')}"
        )
        zipf = vocab.get('zipf_distribution')
        if zipf:
            parts.append(f"Zipf distribution: {json.dumps(zipf)}")

    # Syntactic preferences
    syntactic = profile.get('syntactic_preferences') or {}
    if syntactic:
        synth_lines = [
            f"  {k}: {v}"
            for k, v in syntactic.items()
            if k != 'total_sentences_analyzed'
        ]
        if synth_lines:
            parts.append("Syntactic preferences:\n" + '\n'.join(synth_lines))

    # Sentence structures
    structures = profile.get('sentence_structures') or {}
    avg_len = structures.get('avg_sentence_length')
    if avg_len:
        parts.append(f"Average sentence length: {avg_len} tokens")
    length_dist = structures.get('length_distribution')
    if length_dist:
        parts.append(f"Sentence length distribution: {json.dumps(length_dist)}")
    patterns = structures.get('patterns') or []
    if patterns:
        top_3 = patterns[:3]
        pat_lines = [
            f"  {p['template']} (freq={p['frequency']}, e.g. \"{p.get('example', '')[:80]}\")"
            for p in top_3
        ]
        parts.append("Top sentence patterns:\n" + '\n'.join(pat_lines))

    # Discourse patterns
    discourse = profile.get('discourse_patterns') or {}
    density = discourse.get('connective_density')
    if density:
        parts.append(f"Connective density: {density}")
    transitions = discourse.get('top_transitions') or []
    if transitions:
        top_5 = [f"{t['text']} ({t['frequency']})" for t in transitions[:5]]
        parts.append(f"Top discourse markers: {', '.join(top_5)}")
    openers = discourse.get('sentence_openers') or []
    if openers:
        top_5 = [f"{o['text']} ({o['frequency']})" for o in openers[:5]]
        parts.append(f"Common sentence openers: {', '.join(top_5)}")

    # Characteristic n-grams (keyness)
    char_ngrams = profile.get('characteristic_ngrams') or []
    if char_ngrams:
        top_10 = [
            f"\"{c['text']}\" (keyness={c['keyness_score']})"
            for c in char_ngrams[:10]
        ]
        parts.append(f"Most characteristic expressions: {', '.join(top_10)}")

    return '\n\n'.join(parts)


def generate_narrative(
    profile: dict,
    language_id: int,
    source_title: str = '',
) -> dict:
    """
    Generate a structured narrative from a style profile.

    Args:
        profile:      Style profile dict from StyleAnalyzer.analyze().
        language_id:  1=ZH, 2=EN, 3=JA.
        source_title: Name of the corpus source (for context).

    Returns:
        Dict with keys:
          - 'summary': 2-4 sentence overview of the writing style
          - 'distinctive_features': list of 3-5 feature dicts, each with
            'feature' (name) and 'explanation' (1-2 sentences)
          - 'teaching_notes': 2-3 sentences on what learners can gain
    """
    language = _LANG_NAMES.get(language_id, 'Unknown')
    profile_text = _summarise_profile(profile)

    title_context = f' titled "{source_title}"' if source_title else ''

    prompt = f"""You are an expert in {language} corpus linguistics and language pedagogy.

Below is a statistical style profile of a {language} text corpus{title_context}. Analyse these statistics and produce a structured style narrative.

{profile_text}

Return a JSON object with exactly these keys:
1. "summary": A 2-4 sentence overview describing the overall writing style. Mention register (formal/informal), complexity, and any standout characteristics.
2. "distinctive_features": An array of 3-5 objects, each with:
   - "feature": Short name (e.g. "High passive voice usage", "Dense academic vocabulary")
   - "explanation": 1-2 sentences explaining what this means stylistically and how it compares to typical {language} writing.
3. "teaching_notes": 2-3 sentences summarising what an intermediate {language} learner would gain from studying this corpus's style patterns.

Be specific and reference the actual numbers from the profile. Do not invent statistics not present above."""

    try:
        result = call_llm(prompt)

        # Validate structure
        narrative = {
            'summary': result.get('summary', ''),
            'distinctive_features': result.get('distinctive_features', []),
            'teaching_notes': result.get('teaching_notes', ''),
        }

        if not narrative['summary']:
            logger.warning('LLM returned empty summary for style narrative')

        logger.info(
            f"Generated style narrative for '{source_title}' "
            f"({len(narrative['distinctive_features'])} features)"
        )
        return narrative

    except Exception as exc:
        logger.error(f"Style narrative generation failed: {exc}")
        return {
            'summary': '',
            'distinctive_features': [],
            'teaching_notes': '',
        }
