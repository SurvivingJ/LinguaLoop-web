"""Hint templates, ladder kinds, rungs, rendering and the leak filter (tech 3.2, 5).

Pure: the taxonomy (for gloss fallbacks) is passed in, nothing reads the DB.

The template file ``hint_templates.json`` is loaded and validated once at import.
An invalid file makes ``available()`` False - the feature is then ineligible for
every submission (tech 3.2) - and is logged once; it never raises at import.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from services.dual_translation.tier0 import _normalize_l2

logger = logging.getLogger(__name__)

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "hint_templates.json")

LADDERS = ("full", "short", "none")
RUNG_WHERE, RUNG_KIND, RUNG_CLUE, RUNG_ANSWER = 1, 2, 3, 4
HINT_TYPES = {RUNG_WHERE: "where", RUNG_KIND: "kind", RUNG_CLUE: "clue"}
TEMPLATE_L1S = ("en", "zh", "ja")
CJK_L1S = ("zh", "ja")
_PLACEHOLDER_STANDIN = "xxxxxx"  # 6 characters, tech 5.2
_PLACEHOLDER_RE = re.compile(r"\{(\w*)\}")
_GLOSS_SEPARATORS = (" — ", "——", "—")

SOURCE_GRADER_SPAN = "grader_span"
SOURCE_TEMPLATE = "template"
SOURCE_GLOSS = "taxonomy_gloss"
SOURCE_NEUTRAL = "type_neutral"

_state: dict = {"data": None, "error": None}
_warned_slugs: set = set()


class TemplateError(ValueError):
    pass


def validate(data) -> dict:
    """Raise TemplateError unless ``data`` is a usable template document."""
    if not isinstance(data, dict):
        raise TemplateError("template file is not a JSON object")
    for key in ("version", "limits", "type_neutral", "subtypes"):
        if key not in data:
            raise TemplateError(f"missing key {key!r}")
    if not isinstance(data["version"], str) or not data["version"]:
        raise TemplateError("version must be a non-empty string")
    limits = data["limits"]
    try:
        latin, cjk, label_max = (int(limits["clue_max_latin"]), int(limits["clue_max_cjk"]),
                                 int(limits["label_max"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise TemplateError(f"bad limits: {exc}") from exc
    neutral = data["type_neutral"]
    if not isinstance(neutral, dict) or not all(isinstance(neutral.get(c), str) and neutral[c]
                                                 for c in TEMPLATE_L1S):
        raise TemplateError("type_neutral needs a text for en, zh and ja")
    if "{c}" in json.dumps(data, ensure_ascii=False):
        raise TemplateError("the corrected-form placeholder {c} must not appear")
    subtypes = data["subtypes"]
    if not isinstance(subtypes, dict) or not subtypes:
        raise TemplateError("subtypes must be a non-empty object")
    for slug, entry in subtypes.items():
        if not isinstance(entry, dict) or entry.get("ladder") not in LADDERS:
            raise TemplateError(f"{slug}: ladder must be one of {LADDERS}")
        for code, texts in (entry.get("l1") or {}).items():
            if not isinstance(texts, dict):
                raise TemplateError(f"{slug}.{code}: not an object")
            label, clue = texts.get("label"), texts.get("clue")
            if label is not None and (not isinstance(label, str) or not label or len(label) > label_max):
                raise TemplateError(f"{slug}.{code}: label empty or longer than {label_max}")
            if clue is not None:
                if not isinstance(clue, str) or not clue:
                    raise TemplateError(f"{slug}.{code}: empty clue")
                if set(_PLACEHOLDER_RE.findall(clue)) - {"l"}:
                    raise TemplateError(f"{slug}.{code}: only the {{l}} placeholder is allowed")
                limit = cjk if code in CJK_L1S else latin
                if len(clue.replace("{l}", _PLACEHOLDER_STANDIN)) > limit:
                    raise TemplateError(f"{slug}.{code}: clue longer than {limit}")
    return data


def load(path: str = TEMPLATE_PATH) -> Optional[dict]:
    """(Re)load and validate the template file; returns it or None (logged once)."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = validate(json.load(fh))
        _state.update(data=data, error=None)
        return data
    except Exception as exc:  # noqa: BLE001 - an invalid file disables the feature, never crashes
        if _state.get("error") is None:
            logger.error("dt_repair: hint templates unusable (%s); guided repair is off: %s", path, exc)
        _state.update(data=None, error=str(exc))
        return None


def available() -> bool:
    return _state["data"] is not None


def version() -> Optional[str]:
    return _state["data"]["version"] if _state["data"] else None


def data() -> Optional[dict]:
    return _state["data"]


# ---------------------------------------------------------------------------
# Ladder and rungs
# ---------------------------------------------------------------------------

def ladder_for(slug: str) -> str:
    """Ladder kind of a v6 subtype (tech 5.1). A slug missing from the file is
    ``short`` and logged once."""
    entry = ((_state["data"] or {}).get("subtypes") or {}).get(slug)
    if entry is None:
        if slug not in _warned_slugs:
            _warned_slugs.add(slug)
            logger.warning("dt_repair: subtype %r has no hint template entry; using the short ladder", slug)
        return "short"
    return entry["ladder"]


def rungs(ladder: str, location_available: bool, *, unsure: bool = False) -> list[int]:
    """Hint levels available for a step (tech 3.2 table)."""
    if unsure or ladder == "none":
        return []
    if ladder == "full":
        return [RUNG_WHERE, RUNG_KIND, RUNG_CLUE] if location_available else [RUNG_KIND, RUNG_CLUE]
    return [RUNG_WHERE] if location_available else []


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _template_l1(code: Optional[str]) -> str:
    return code if code in TEMPLATE_L1S else "en"


def _entry_text(slug: str, code: str, field: str) -> Optional[str]:
    entry = ((_state["data"] or {}).get("subtypes") or {}).get(slug) or {}
    return ((entry.get("l1") or {}).get(code) or {}).get(field)


def gloss_head(gloss: str) -> str:
    """A taxonomy gloss up to its first dash separator ("Register — how...")."""
    cut = len(gloss)
    for sep in _GLOSS_SEPARATORS:
        idx = gloss.find(sep)
        if 0 < idx < cut:
            cut = idx
    return gloss[:cut].strip()


def render_kind(slug: str, l1_code: Optional[str], taxonomy: Optional[dict] = None):
    """The kind label -> (text, lang, hint_source, template_id). Falls back
    template -> taxonomy gloss head -> English label (tech 5.3)."""
    code = l1_code or "en"
    label = _entry_text(slug, code, "label")
    if label:
        return label, code, SOURCE_TEMPLATE, f"{slug}.{code}.kind"
    gloss = (((taxonomy or {}).get("subtype_glosses") or {}).get(slug) or {}).get(code)
    if isinstance(gloss, str) and gloss_head(gloss):
        return gloss_head(gloss), code, SOURCE_GLOSS, f"gloss.{slug}.{code}"
    label = _entry_text(slug, "en", "label")
    if label:
        return label, "en", SOURCE_TEMPLATE, f"{slug}.en.kind"
    return slug.replace("_", " ").capitalize(), "en", SOURCE_TEMPLATE, f"{slug}.en.kind"


def type_neutral(l1_code: Optional[str]):
    code = _template_l1(l1_code)
    text = ((_state["data"] or {}).get("type_neutral") or {}).get(code, "")
    return text, code, SOURCE_NEUTRAL, f"type_neutral.{code}"


def render_clue(
    slug: str, l1_code: Optional[str], *, learner_form: str, current_text: str,
    corrected_form: str, l2_code: str, correction_source: Optional[str] = None,
    reference_sentence: str = "", learner_sentence: str = "",
):
    """The clue -> (text, lang, hint_source, template_id, leak_blocked).

    ``{l}`` is filled with the active error's learner form as it stands in the
    current text. A missing template, an empty / not-found ``{l}``, or a leak gives
    the type-neutral text instead (tech 5.3)."""
    code = l1_code or "en"
    template = _entry_text(slug, code, "clue")
    if not template:
        return (*type_neutral(code), False)
    form = (learner_form or "").strip()
    if "{l}" in template:
        if not form or form not in (current_text or ""):
            return (*type_neutral(code), False)
        text = template.replace("{l}", form)
    else:
        text = template
    if correction_source == "reference_sentence":
        blocked = leaks(text, learner_sentence or current_text, reference_sentence, l2_code)
    else:
        blocked = leaks(text, form, corrected_form, l2_code)
    if blocked:
        return (*type_neutral(code), True)
    return text, code, SOURCE_TEMPLATE, f"{slug}.{code}.clue", False


# ---------------------------------------------------------------------------
# Leak filter (tech 5.4)
# ---------------------------------------------------------------------------

def _norm(text: str, l2_code: str) -> str:
    return _normalize_l2(text or "", l2_code).casefold()


def _strip_common(corrected: str, learner: str) -> str:
    prefix = 0
    limit = min(len(corrected), len(learner))
    while prefix < limit and corrected[prefix] == learner[prefix]:
        prefix += 1
    suffix = 0
    while (suffix < len(corrected) - prefix and suffix < len(learner) - prefix
           and corrected[-1 - suffix] == learner[-1 - suffix]):
        suffix += 1
    return corrected[prefix:len(corrected) - suffix]


def leaks(text: str, learner_form: str, corrected_form: str, l2_code: str) -> bool:
    """True when ``text`` gives away the correction.

    All three are normalised (tier-0 width/kana fold, plus case fold). The
    corrected form minus the longest prefix and suffix it shares with the learner
    form is the fragment the learner has to produce; it leaks when it occurs in
    the text and is not part of the learner's own words (or occurs in the text
    more often than in them). The whole corrected form appearing verbatim, when
    it is not the learner's own text, is a leak too (Track D's first rule)."""
    t, lrn, cor = (_norm(x, l2_code) for x in (text, learner_form, corrected_form))
    if not cor.strip():
        return False
    if cor.strip() in t and cor.strip() not in lrn:
        return True
    fragment = _strip_common(cor, lrn).strip()
    if not fragment or fragment not in t:
        return False
    if fragment not in lrn:
        return True
    return len(fragment) > 1 and t.count(fragment) > lrn.count(fragment)


load()
