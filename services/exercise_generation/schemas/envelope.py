"""
Schema-v2 content envelope — the nl-keyed map rule (§6.4, TASK-519).

The rule
--------
An exercise's content splits cleanly in two:

  * **TL-facing content** — the sentence the learner reads, the target word,
    the acceptable answers they type. Written in the *target* language. It is
    the same regardless of who is studying, so it stays at the top level and
    must contain no native-language text.

  * **NL-facing content** — glosses, grading notes, translated options,
    explanations. These depend on the learner's native language, so one stored
    item must be able to carry several. They live under a keyed map::

        {"schema_version": 2,
         "tl_sentence": "他很高",
         "tl_language": "zh",
         "nl": {"en": {"correct": "He is tall",
                       "options": ["He is tall", "He is old", "He is busy"]},
                "ja": {"correct": "彼は背が高い", "options": [...]}}}

Why it matters
--------------
v1 put nl text at the top level (``correct_nl``, ``grading_notes``,
``nl_sentence``) and hardcoded ``'en'`` throughout generation. That silently
made every generated item English-only: adding a second native language would
have meant regenerating the whole corpus. Operator decision (task §7) is to
adopt nl-keyed maps from the first batch — before that corpus exists.

What this module provides
-------------------------
``NL_BEARING_FIELDS``  — per exercise type, which v1 fields carry nl text.
``validate_envelope``  — the gate: rejects nl text found at the top level.
``wrap_nl``            — build a v2 envelope from a flat generator result.
``read_nl``            — resolve one learner's nl block, with fallback.
``flatten_for_serve``  — project v2 back onto flat keys for a given nl, so
                         serve-side consumers that predate v2 keep working.

Reading is deliberately tolerant (v1 content still serves); *writing* is
strict (new generators must emit v2).
"""

from __future__ import annotations

SCHEMA_VERSION = 2

# Per exercise type: the content fields whose values are native-language text.
# These are exactly the keys that must appear under ``content.nl.<code>`` in a
# v2 envelope, and must NOT appear at the top level.
NL_BEARING_FIELDS: dict[str, tuple[str, ...]] = {
    'tl_nl_translation':       ('correct_nl', 'options'),
    'nl_tl_translation':       ('nl_sentence', 'grading_notes'),
    'text_flashcard':          ('definition', 'gloss'),
    'listening_flashcard':     ('definition', 'gloss'),
    'definition_match':        ('options', 'correct_answer'),
    'phonetic_recognition':    ('gloss',),
    'cloze_completion':        ('word_definition', 'explanation'),
    'semantic_discrimination': ('explanation',),
    'morphology_slot':         ('explanation',),
    'collocation_gap_fill':    ('explanation',),
    'spot_incorrect_sentence': ('explanation',),
    # TASK-522 / TASK-527. The options for all three are target-language words
    # or particles, so they stay at the top level; only the prose a learner
    # reads *about* the answer is native-language.
    'synonym_antonym_match':   ('word_definition', 'explanation'),
    'word_family':             ('explanation',),
    'particle_selection':      ('explanation',),
}

# Canonical v2 key for each v1 field, so the map is stable across types.
# Fields absent from this map keep their own name inside the nl block.
_V2_KEY = {
    'correct_nl':      'correct',
    'nl_sentence':     'prompt',
    'grading_notes':   'grading_notes',
    'word_definition': 'definition',
}

# Reverse direction, for flatten_for_serve.
_V1_KEY = {v: k for k, v in _V2_KEY.items()}


class EnvelopeError(ValueError):
    """A content dict violates the schema-v2 envelope rule."""


def v2_key(field: str) -> str:
    """Map a v1 nl-bearing field name to its key inside ``content.nl.<code>``."""
    return _V2_KEY.get(field, field)


# ---------------------------------------------------------------------------
# Validation gate
# ---------------------------------------------------------------------------

def validate_envelope(content: dict, exercise_type: str) -> list[str]:
    """Check a v2 content dict against the envelope rule.

    Returns a list of error strings (empty when valid). Content that does not
    declare ``schema_version >= 2`` is treated as legacy and skipped — this
    gate governs what new generators *write*, and must not retroactively
    invalidate the v1 corpus still sitting in the exercises table.
    """
    errors: list[str] = []
    if not isinstance(content, dict):
        return ['content must be a dict']

    if int(content.get('schema_version') or 0) < SCHEMA_VERSION:
        return errors                     # legacy content — not this gate's business

    nl_fields = NL_BEARING_FIELDS.get(exercise_type, ())
    if not nl_fields:
        # Type carries no nl text; an `nl` block would be meaningless but is
        # not harmful. Nothing to enforce.
        return errors

    # 1. nl text must not sit at the top level.
    for field in nl_fields:
        if field in content:
            errors.append(
                f"schema-v2 violation: {exercise_type}.{field} is native-language "
                f"text and must live under content.nl.<code>.{v2_key(field)}, "
                f"not at the top level"
            )

    # 2. the nl map must exist and be well-formed.
    nl = content.get('nl')
    if not isinstance(nl, dict) or not nl:
        errors.append(
            f"schema-v2 violation: {exercise_type} requires a non-empty "
            f"content.nl map keyed by native-language code"
        )
        return errors

    for code, block in nl.items():
        if not isinstance(code, str) or not code:
            errors.append(f"content.nl key {code!r} is not a language code")
            continue
        if not isinstance(block, dict):
            errors.append(f"content.nl.{code} must be an object")
            continue
        for field in nl_fields:
            key = v2_key(field)
            if key not in block:
                errors.append(f"content.nl.{code} is missing {key!r}")

    return errors


def assert_envelope(content: dict, exercise_type: str) -> None:
    """Raise ``EnvelopeError`` if the envelope rule is violated."""
    errors = validate_envelope(content, exercise_type)
    if errors:
        raise EnvelopeError('; '.join(errors))


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def wrap_nl(base: dict, exercise_type: str, nl_code: str, nl_values: dict) -> dict:
    """Build a v2 envelope: TL-facing ``base`` plus one keyed nl block.

    ``nl_values`` is keyed by v1 field name (``correct_nl``, ``grading_notes``,
    …); those keys are translated to their canonical v2 names. Passing a field
    that isn't nl-bearing for this type is a programming error and raises —
    silently dropping it would produce a half-translated item.

    ``nl_code`` must be supplied by the caller: there is deliberately no
    ``'en'`` default anywhere in this module (see the lint test).
    """
    if not nl_code:
        raise EnvelopeError(
            'wrap_nl requires an explicit nl_code; hardcoding a native '
            'language is what schema v2 exists to prevent'
        )

    allowed = set(NL_BEARING_FIELDS.get(exercise_type, ()))
    unknown = set(nl_values) - allowed
    if unknown:
        raise EnvelopeError(
            f"{exercise_type}: {sorted(unknown)} are not nl-bearing fields for "
            f"this type (known: {sorted(allowed)})"
        )

    block = {v2_key(field): value for field, value in nl_values.items()}
    content = dict(base)
    content['schema_version'] = SCHEMA_VERSION
    existing = content.get('nl') if isinstance(content.get('nl'), dict) else {}
    content['nl'] = {**existing, nl_code: block}
    return content


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def read_nl(content: dict, nl_code: str) -> dict:
    """Return the nl block for ``nl_code``.

    Falls back to the envelope's single block when the requested language is
    absent (better a gloss in the wrong language than a blank exercise), and
    to ``{}`` for legacy content.
    """
    nl = content.get('nl')
    if not isinstance(nl, dict) or not nl:
        return {}
    block = nl.get(nl_code)
    if isinstance(block, dict):
        return block
    if len(nl) == 1:
        only = next(iter(nl.values()))
        return only if isinstance(only, dict) else {}
    return {}


def flatten_for_serve(content: dict, nl_code: str) -> dict:
    """Project a v2 envelope onto flat v1 keys for one native language.

    Lets consumers written against v1 (the practice-session renderers) read v2
    content unchanged. Legacy content passes through untouched, so this is safe
    to apply unconditionally.
    """
    if int(content.get('schema_version') or 0) < SCHEMA_VERSION:
        return content

    block = read_nl(content, nl_code)
    if not block:
        return content

    flat = {k: v for k, v in content.items() if k != 'nl'}
    for key, value in block.items():
        flat[_V1_KEY.get(key, key)] = value
    flat['nl_language'] = nl_code
    return flat
