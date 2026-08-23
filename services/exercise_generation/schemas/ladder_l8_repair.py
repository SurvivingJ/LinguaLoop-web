"""Output schema for the L8 collocation-repair prompt (TASK-520).

Same story as ``ladder_l4_morphology``: L8's remap inside the P3 monolith
carried speculative branches for a bare list, an ``options`` key and a ``"1"``
key because no gate told it which one the prompt actually produced. On its own
prompt there is one shape, validated before remap and bound to
``prompt_version``.

Accepted shape (prompt_version 1) — numeric keys per ``_shared``: 0=options,
1=error_collocate, and within each option 0=text, 1=is_correct,
2=explanation::

    {"0": [{"0": "brew", "1": true,
            "2": "'brew coffee' is the idiomatic pairing"},
           ... exactly 4 ...],
     "1": "cook"}

Or the escape, when the sense has no collocation worth repairing::

    {"9": "no_collocation"}

There is deliberately no sentence-index key. The generator picks the sentence
it has already verified attests the collocate and passes that index through
itself, so a model-nominated index could only ever disagree with the sentence
the model was shown.

``error_collocate`` (key 1) is the wrong collocate planted in the sentence for
the learner to repair. It is required: without it the renderer has nothing to
substitute, and the item silently disappears. The collocation judge
(``judges/collocation.judge_collocation_repair``) still owns the *semantic*
question of whether that word is a genuine non-collocate — this gate only
guarantees the field is there and well-typed.
"""

from __future__ import annotations

from ._shared import (
    OPTIONS_KEY, option_text, read_index, validate_escape, validate_options,
    validate_text,
)

SCHEMA_VERSION = 1
TYPE_CODE = 'collocation_repair'

PROMPT_VERSIONS: frozenset[int] = frozenset({1, 2})

OPTION_COUNT = 4

#: This type's escape token: the sense has no collocation to repair.
ERROR_TOKEN = 'no_collocation'

#: Top-level index → field name; declared in each prompt's own language.
KEY_LEGEND: dict[str, str] = {
    OPTIONS_KEY: 'options',
    '1': 'error_collocate',
}


def validate(raw: object) -> list[str]:
    """Return schema errors for one raw L8 response (empty when valid)."""
    if not isinstance(raw, dict):
        return [f'collocation_repair: expected an object, got {type(raw).__name__}']

    escape = validate_escape(raw, expected=ERROR_TOKEN)
    if escape is not None:
        return escape

    errors: list[str] = []
    errors += validate_options(read_index(raw, OPTIONS_KEY), expected=OPTION_COUNT)
    errors += validate_text(read_index(raw, '1'), 'error_collocate', key='1')

    # The planted error word must not be one of the offered options: the
    # learner picks the repair from those, so an error word sitting among them
    # would make the "wrong" answer selectable as the fix.
    planted = read_index(raw, '1')
    error_word = str(planted or '').strip().casefold()
    options = read_index(raw, OPTIONS_KEY)
    if error_word and isinstance(options, list):
        for i, opt in enumerate(options):
            if isinstance(opt, dict) and option_text(opt).casefold() == error_word:
                errors.append(
                    f'error_collocate (key 1): {planted!r} also appears as '
                    f'options[{i}] — the planted error must not be selectable as the repair'
                )
    return errors
