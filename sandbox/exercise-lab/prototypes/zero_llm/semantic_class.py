# FIDELITY GAP (read before trusting any capability-matrix number that
# depends on semantic_class): production's `dim_vocabulary.semantic_class`
# is set by an LLM P1 call (services/vocabulary_ladder/config.py
# SEMANTIC_CLASSES = {concrete, abstract, action, property, function, proper}).
# This sandbox seeds NO senses with a semantic_class at all (build_db.py never
# writes it — confirmed: `select semantic_class, count(*) from dim_vocabulary
# group by 1` returns a single NULL row per language). Since
# `config._pos_matches` only matches a NULL semantic_class against capability
# rows whose pos_classes tuple contains the literal 'all' sentinel,  a NULL
# semantic_class makes classifier_match, counter_match, cloze_typed and
# jumbled_sentence — ALL of which gate on ('concrete',) or
# ('concrete','abstract','action','property') rather than 'all' — permanently
# unreachable. Measuring the zero-LLM path with that left as NULL would
# understate its real capability, not overstate it, so this module supplies a
# heuristic, LLM-free proxy classification and every number derived from it in
# results-zero-llm.md is labelled as coming from this proxy, not from
# production's real (model-judged) semantic_class.
#
# en: real spaCy POS tags exist (dim_vocabulary.part_of_speech) — mapped
# directly, matching the coarse intent of each Universal POS tag.
# ja: real JMdict POS tags exist, comma-joined (e.g. "n,vs,vt") — parsed and
# mapped by the same intent.
# zh: CC-CEDICT carries NO part-of-speech field at all (part_of_speech is NULL
# for all 121,159 zh vocab rows — confirmed). The only signal available
# without an LLM is the English gloss text itself, so zh classification is a
# definition-text heuristic (leading "to " -> action; "(surname)"/single
# capitalised gloss -> proper; a fixed function-word stoplist -> function;
# CL: classifier annotation or default -> concrete). This is the weakest of
# the three and should be read as directional, not authoritative — it will
# misclassify most abstract nouns as concrete because CEDICT glosses do not
# reliably distinguish them without more than string matching.
from __future__ import annotations

import re

_EN_ACTION = {"VERB"}
_EN_PROPERTY = {"ADJ", "ADV"}
_EN_PROPER = {"PROPN"}
_EN_FUNCTION = {
    "ADP", "DET", "PRON", "CCONJ", "SCONJ", "AUX", "PART", "INTJ", "NUM", "X",
}


def classify_en(pos: str | None) -> str | None:
    if not pos:
        return None
    pos = pos.strip().upper()
    if pos in _EN_PROPER:
        return "proper"
    if pos in _EN_ACTION:
        return "action"
    if pos in _EN_PROPERTY:
        return "property"
    if pos in _EN_FUNCTION:
        return "function"
    if pos == "NOUN":
        return "concrete"
    return None


_JA_FUNCTION_TAGS = {
    "prt", "conj", "int", "aux", "aux-v", "aux-adj", "cop", "cop-da",
    "exp", "unc", "pn",
}
_JA_PROPERTY_TAGS = {"adj-i", "adj-na", "adj-no", "adj-pn", "adj-t", "adj-ix", "adv"}
_JA_ACTION_PREFIX = "v"  # v1, v5*, vs, vk, vz, ...
_JA_PROPER_TAGS = {"n-pr", "num"}


def classify_ja(pos_field: str | None) -> str | None:
    if not pos_field:
        return None
    tags = [t.strip().lower() for t in pos_field.split(",") if t.strip()]
    if not tags:
        return None
    if any(t in _JA_PROPER_TAGS for t in tags):
        return "proper"
    if any(t.startswith(_JA_ACTION_PREFIX) and t not in ("vt", "vi") for t in tags):
        return "action"
    if any(t in _JA_PROPERTY_TAGS for t in tags):
        return "property"
    if any(t in _JA_FUNCTION_TAGS for t in tags):
        return "function"
    if any(t == "n" for t in tags):
        return "concrete"
    return None


_ZH_ACTION_RE = re.compile(r"^\s*to\s+\w", re.IGNORECASE)
_ZH_PROPER_RE = re.compile(r"\(surname\)|proper name|place name", re.IGNORECASE)
_ZH_FUNCTION_GLOSSES = {
    "and", "or", "but", "not", "also", "very", "in", "at", "on", "of", "to",
    "the", "a", "is", "are", "this", "that", "these", "those", "with", "for",
    "as", "so", "than", "then", "just", "already", "again", "still", "only",
    "which", "who", "what", "where", "when", "how", "why", "measure word",
}


def classify_zh(definition: str | None) -> str | None:
    if not definition:
        return None
    text = definition.strip()
    first_gloss = text.split("/")[0].strip().lower()
    if _ZH_PROPER_RE.search(text):
        return "proper"
    if first_gloss in _ZH_FUNCTION_GLOSSES:
        return "function"
    if _ZH_ACTION_RE.match(first_gloss):
        return "action"
    if "CL:" in text:
        return "concrete"
    return "concrete"  # default: most CEDICT single/double-char headwords are nominal


def classify(language_id: int, pos: str | None, definition: str | None) -> str | None:
    """Dispatch by language. Returns None (permissive full ladder, matching
    config.compute_active_levels' own NULL-handling) when the heuristic has
    no signal at all."""
    if language_id == 2:
        return classify_en(pos)
    if language_id == 3:
        return classify_ja(pos)
    if language_id == 1:
        return classify_zh(definition)
    return None
