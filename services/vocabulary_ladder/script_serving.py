# services/vocabulary_ladder/script_serving.py
"""Serve the Traditional-script mirror to learners who ask for it (TASK-526).

TASK-509 dual-stored the mirror: every ZH exercise carries ``content.hant``, a
deep Traditional conversion of its whole content dict, written once at
generation time. Nothing read it. This module is the read side.

Why field selection and not conversion
--------------------------------------
The operator decision (plan §6.7) was to convert at *generation* time, and the
reason is 發 / 髮. Both are written 发 in Simplified, and telling them apart
needs the surrounding phrase — which OpenCC's ``s2twp`` can do, given the whole
sentence, and which no serve-time helper should be attempting per request while
a learner waits. So the serve path does no conversion at all: it picks fields
out of a mirror that was already computed with full context, and a missing
field falls back to Simplified rather than being converted on the spot.

That constraint is enforced by a test, not just documented — see
``tests/test_script_variant_serving.py``.

Missing fields are flagged, not hidden
--------------------------------------
A mirror generated before a field existed will not have that field. The
Simplified value is served (better a learner sees 发 than nothing) and the
field path is recorded in ``content['script_fallback_fields']`` so a review
query can find every item whose mirror has drifted behind its content.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

VARIANT_SIMPLIFIED = 'simplified'
VARIANT_TRADITIONAL = 'traditional'
VALID_VARIANTS = (VARIANT_SIMPLIFIED, VARIANT_TRADITIONAL)

#: Only Chinese has a script variant to choose between.
SCRIPT_VARIANT_LANGUAGES = (1,)

#: Key the mirror lives under, written by LadderExerciseRenderer.
MIRROR_KEY = 'hant'

#: Where the per-item review flag lands.
FALLBACK_KEY = 'script_fallback_fields'

#: Never selected from the mirror. Schema bookkeeping is not learner-visible
#: text, and a "converted" schema_version would be nonsense.
_SKIP_KEYS = frozenset({'schema_version', 'nl_language', MIRROR_KEY, FALLBACK_KEY})


def variant_from_preferences(prefs: dict | None) -> str:
    """Read ``script_variant`` out of a user's ``exercise_preferences``.

    Anything unrecognised — including the key being absent, which is the state
    every existing user is in — reads as Simplified, the authored script.
    """
    value = (prefs or {}).get('script_variant')
    return value if value in VALID_VARIANTS else VARIANT_SIMPLIFIED


def applies_to(language_id: int, variant: str) -> bool:
    """Whether this (language, variant) pair needs any field selection."""
    return (
        variant == VARIANT_TRADITIONAL
        and language_id in SCRIPT_VARIANT_LANGUAGES
    )


def select_script_fields(content: dict, variant: str, language_id: int) -> dict:
    """Return ``content`` with learner-visible strings taken from the mirror.

    A new dict is returned; the caller's dict is never mutated. When the
    variant is Simplified, the language is not Chinese, or the item carries no
    mirror, the content is returned unchanged.
    """
    if not isinstance(content, dict) or not applies_to(language_id, variant):
        return content

    mirror = content.get(MIRROR_KEY)
    if not isinstance(mirror, dict) or not mirror:
        # Pre-TASK-509 content. Serving Simplified is correct; flagging it
        # per item would put a review marker on the entire legacy corpus, so
        # the absence is left to a coverage query instead.
        return content

    fallbacks: list[str] = []
    selected = _merge(content, mirror, fallbacks, path='')

    # The mirror is a serve-side detail; the learner's payload does not need
    # to carry a second copy of every string.
    selected.pop(MIRROR_KEY, None)
    selected['script_variant'] = VARIANT_TRADITIONAL
    if fallbacks:
        selected[FALLBACK_KEY] = fallbacks
    return selected


def _merge(source, mirror, fallbacks: list[str], path: str):
    """Recursively prefer ``mirror`` values whose shape matches ``source``.

    Shape agreement is the whole safety property. The mirror is a deep
    conversion of the same structure, so a type or length mismatch means the
    two have drifted — at which point the Simplified value is the one we know
    corresponds to the item, and the mismatch is worth recording.
    """
    if isinstance(source, dict):
        if not isinstance(mirror, dict):
            _flag(fallbacks, path, 'mirror is not an object')
            return source
        out = {}
        for key, value in source.items():
            if key in _SKIP_KEYS:
                out[key] = value
                continue
            child = f'{path}.{key}' if path else key
            if key not in mirror:
                _flag(fallbacks, child, 'absent from mirror')
                out[key] = value
                continue
            out[key] = _merge(value, mirror[key], fallbacks, child)
        return out

    if isinstance(source, list):
        if not isinstance(mirror, list) or len(mirror) != len(source):
            _flag(fallbacks, path, 'mirror list shape differs')
            return source
        return [
            _merge(item, mirror[i], fallbacks, f'{path}[{i}]')
            for i, item in enumerate(source)
        ]

    if isinstance(source, str):
        if not isinstance(mirror, str) or not mirror:
            _flag(fallbacks, path, 'mirror value missing or not a string')
            return source
        return mirror

    # Numbers, booleans and None have no script. Returning the source avoids
    # any chance of a converted-looking number sneaking through.
    return source


def _flag(fallbacks: list[str], path: str, reason: str) -> None:
    fallbacks.append(f'{path or "<root>"}: {reason}')


def apply_to_items(items, variant: str, language_id: int) -> int:
    """Apply field selection to every item in a session payload, in place.

    Returns the number of items that fell back on at least one field, which
    the caller surfaces so a drifted mirror shows up in logs rather than only
    in a learner's confusion.
    """
    if not applies_to(language_id, variant):
        return 0

    flagged = 0
    for item in items or []:
        if not isinstance(item, dict):
            continue
        content = item.get('content')
        if not isinstance(content, dict):
            continue
        item['content'] = select_script_fields(content, variant, language_id)
        if item['content'].get(FALLBACK_KEY):
            flagged += 1
    return flagged
