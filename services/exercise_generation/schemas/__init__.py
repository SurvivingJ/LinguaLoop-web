"""Content schema definitions for the exercise-generation pipeline.

Two families live here:

* **The v2 nl-keyed content envelope** (TASK-519, ``envelope.py``) — governs
  what a *rendered exercise* may put at the top level of ``content``.
* **Per-exercise-type LLM output schemas** (TASK-520, ``ladder_*.py``) — govern
  the raw JSON a single-type generation prompt returns, before any remap.

The second family is registered by ``(type_code, prompt_version)`` rather than
by type alone. Binding the shape to the prompt version is the point: the
monolithic P3 prompt could be re-authored freely because its remap guessed at
whatever came back, and a shape change surfaced as an empty exercise weeks
later. Here, output from a prompt version no schema declares is a hard error.
"""

from . import ladder_l4_morphology, ladder_l8_repair, ladder_typed
from ._shared import (
    ERROR_ESCAPE_KEY,
    JUDGE_RATING_KEY,
    JUDGE_REASON_KEY,
    OPTIONS_KEY,
    OPTION_KEY_LEGEND,
    OPT_EXPLANATION,
    OPT_IS_CORRECT,
    OPT_PART_OF_SPEECH,
    OPT_TEXT,
    SchemaError,
    error_escape,
    read_index,
)
from .envelope import (
    SCHEMA_VERSION,
    NL_BEARING_FIELDS,
    EnvelopeError,
    assert_envelope,
    flatten_for_serve,
    read_nl,
    v2_key,
    validate_envelope,
    wrap_nl,
)

# Every module that declares a per-type LLM output schema. Adding one here is
# what makes its (type_code, prompt_version) pairs gateable.
_LADDER_SCHEMA_MODULES: tuple = (
    ladder_l4_morphology,
    ladder_l8_repair,
    *ladder_typed.TYPED_SCHEMAS,
)

LADDER_SCHEMAS: dict[tuple[str, int], object] = {
    (module.TYPE_CODE, version): module
    for module in _LADDER_SCHEMA_MODULES
    for version in module.PROMPT_VERSIONS
}


def ladder_schema(type_code: str, prompt_version: int):
    """The schema module governing ``type_code`` at ``prompt_version``.

    Raises ``SchemaError`` when the pair is unregistered. That is deliberately
    fail-closed: an unrecognised prompt version means somebody re-authored the
    prompt without updating the gate, and validating it against the *old*
    schema would be worse than refusing — it would either reject good output or
    wave through a shape the remap cannot read.
    """
    module = LADDER_SCHEMAS.get((type_code, int(prompt_version)))
    if module is None:
        known = sorted(v for (t, v) in LADDER_SCHEMAS if t == type_code)
        raise SchemaError(
            f'no output schema registered for type_code={type_code!r} '
            f'prompt_version={prompt_version} (known versions: {known or "none"}). '
            f'Add the version to PROMPT_VERSIONS in its schema module, or seed '
            f'the prompt at a version the gate knows.'
        )
    return module


def validate_ladder_output(
    type_code: str, prompt_version: int, raw: object,
) -> list[str]:
    """Schema errors for one raw single-type generation response.

    Returns an empty list when the payload matches. Raises ``SchemaError`` only
    when no schema is registered for the pair — a payload problem is reported,
    an ungated prompt is raised.
    """
    return ladder_schema(type_code, prompt_version).validate(raw)


__all__ = [
    'SCHEMA_VERSION',
    'ERROR_ESCAPE_KEY',
    'JUDGE_RATING_KEY',
    'JUDGE_REASON_KEY',
    'NL_BEARING_FIELDS',
    'OPTIONS_KEY',
    'OPTION_KEY_LEGEND',
    'OPT_EXPLANATION',
    'OPT_IS_CORRECT',
    'OPT_PART_OF_SPEECH',
    'OPT_TEXT',
    'EnvelopeError',
    'LADDER_SCHEMAS',
    'SchemaError',
    'assert_envelope',
    'error_escape',
    'flatten_for_serve',
    'ladder_schema',
    'read_index',
    'read_nl',
    'v2_key',
    'validate_envelope',
    'validate_ladder_output',
    'wrap_nl',
]
