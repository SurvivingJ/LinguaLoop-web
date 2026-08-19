"""Output schema for the L4 morphology-slot prompt (TASK-520).

L4 used to be one branch of the P3 monolith, and its remap had to guess between
four shapes the model might return (a bare list, ``{"options": [...]}``,
``{"1": [...]}``, or ``{"0": {...}, "1": {...}}``). Those branches existed
because nothing validated the response — a shape drift showed up as a silently
empty exercise rather than as an error.

With L4 on its own prompt there is exactly ONE accepted shape, and it is
checked before the remap runs. The shape is bound to ``prompt_version``: the
registry in ``schemas/__init__`` refuses to validate output from a prompt
version this module does not declare, so re-authoring the prompt without
updating the gate fails loudly instead of shipping unparsed content.

Accepted shape (prompt_version 1) — numeric keys, per the contract in
``_shared``: 0=options, 1=base_form, 2=form_label, 3=sentence_index, and
within each option 0=text, 1=is_correct, 2=explanation::

    {"0": [{"0": "ran", "1": true,
            "2": "past simple, matches 'yesterday'"},
           ... exactly 4 ...],
     "1": "run",
     "2": "past simple",
     "3": 1}

Or the escape, when the lemma has no inflection worth testing::

    {"9": "no_inflection"}

This module once argued the opposite — that numeric keys earn their keep only
in a *multi-level* prompt, and that a single-level prompt should name its
fields so the gate could report ``base_form missing`` rather than ``key '1'
missing``. That reasoning is superseded (TASK-537). The cost it weighed was
real but small, and it is now paid off directly: ``_shared.labelled`` puts the
field name *and* the index in every error string, so the diagnostics read
``base_form (key 1): missing non-empty string``. The cost it did not weigh is
the one that decided it — English field names in the output contract of a ZH or
JA prompt are English inside the generation context, and they drag the model's
prose toward English.
"""

from __future__ import annotations

from ._shared import (
    OPTIONS_KEY, read_index, validate_escape, validate_index, validate_options,
    validate_text,
)

SCHEMA_VERSION = 1
TYPE_CODE = 'morphology_slot'

# Prompt template versions this schema governs. A version outside this set is
# an ungated prompt — see ``schemas.validate_ladder_output``.
PROMPT_VERSIONS: frozenset[int] = frozenset({1})

OPTION_COUNT = 4

#: This type's escape token: the sense has no inflected form worth a slot.
ERROR_TOKEN = 'no_inflection'

#: Top-level index → field name. The prompt declares this same legend in its
#: own language; a test pins the two together.
KEY_LEGEND: dict[str, str] = {
    OPTIONS_KEY: 'options',
    '1': 'base_form',
    '2': 'form_label',
    '3': 'sentence_index',
}


def validate(raw: object) -> list[str]:
    """Return schema errors for one raw L4 response (empty when valid)."""
    if not isinstance(raw, dict):
        return [f'morphology_slot: expected an object, got {type(raw).__name__}']

    escape = validate_escape(raw, expected=ERROR_TOKEN)
    if escape is not None:
        return escape

    errors: list[str] = []
    errors += validate_options(read_index(raw, OPTIONS_KEY), expected=OPTION_COUNT)
    errors += validate_text(read_index(raw, '1'), 'base_form', key='1')
    errors += validate_text(read_index(raw, '2'), 'form_label', key='2')
    errors += validate_index(read_index(raw, '3'), 'sentence_index', key='3')
    return errors
