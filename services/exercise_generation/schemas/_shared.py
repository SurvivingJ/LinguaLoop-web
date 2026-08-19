"""Shared shape checks for the per-exercise-type ladder schemas (TASK-520).

The split prompts (L4 morphology, L8 collocation repair) both return a
four-option MCQ block, so the option-array rules live here rather than being
written twice and drifting apart.

These are deliberately hand-rolled rather than `jsonschema`-backed: the project
carries no JSON-Schema dependency, the shapes are small, and the error strings
need to name the offending index so a batch report can point an operator at the
exact option that came back malformed.

The numeric-key contract (TASK-537)
-----------------------------------
Every ladder prompt returns **numeric keys**, not field names — the same
convention P1/P2 already use (``PROMPT1_KEY_MAP`` and friends in
``vocabulary_ladder.config``). The reason is contamination, not compactness: an
English field name like ``is_correct`` sitting in the output contract of a
Chinese or Japanese prompt is English inside the generation context, and it
pulls the model's prose toward English.

Two rules hold across every type:

* **``0`` is always the option array.**
* **``9`` is always the error escape** — ``{"9": "no_inflection"}`` and its
  per-type equivalents, which say "this sense cannot support this exercise"
  rather than "generation failed".

The escape *tokens* stay English ASCII on purpose: they are machine enum values
matched by code and never shown to a learner, so localising them would only
break the generators' branch conditions.

Keys deserialise from JSON as strings, but ``read_index`` accepts ints too so a
hand-written test fixture can use either.
"""

from __future__ import annotations


class SchemaError(ValueError):
    """LLM output does not match the schema bound to its ``prompt_version``."""


# ---------------------------------------------------------------------------
# The numeric-key contract
# ---------------------------------------------------------------------------

#: Uniform across every ladder type.
OPTIONS_KEY = '0'
ERROR_ESCAPE_KEY = '9'

#: Keys inside one option object.
OPT_TEXT = '0'
OPT_IS_CORRECT = '1'
OPT_EXPLANATION = '2'
OPT_PART_OF_SPEECH = '3'

#: Keys inside one *judge* entry. A judge response stays keyed by 1-based
#: candidate number at the top level — that numbering is the candidate list the
#: prompt was handed, not a field name, so there is no English in it to remove.
JUDGE_RATING_KEY = '0'
JUDGE_REASON_KEY = '1'

#: The shared key legend: index → the descriptive name it stands for. This is
#: the authoritative record of the option contract — error strings name the
#: position *and* the key from here, the prompts declare it in their own
#: language, and ``config.LADDER_OPTION_KEY_MAP`` remaps against it.
OPTION_KEY_LEGEND: dict[str, str] = {
    OPT_TEXT: 'text',
    OPT_IS_CORRECT: 'is_correct',
    OPT_EXPLANATION: 'explanation',
    OPT_PART_OF_SPEECH: 'part_of_speech',
}


def read_index(obj: object, index: str | int) -> object:
    """Read a numeric key from a decoded JSON object, str or int alike.

    JSON object keys always deserialise as strings, so the string form is
    tried first; the int fallback exists for fixtures and for any caller that
    built the dict in Python rather than parsing it.
    """
    if not isinstance(obj, dict):
        return None
    key = str(index)
    if key in obj:
        return obj[key]
    try:
        return obj.get(int(key))
    except (TypeError, ValueError):
        return None


def labelled(name: str, key: str | int | None) -> str:
    """``'base_form (key 1)'`` — the field name *and* the index it came in on.

    Naming only the key would regress the error messages to ``key '1'
    missing``, which was the original argument against numeric keys; naming
    only the field would leave an operator unable to see which index the model
    actually got wrong.
    """
    return f'{name} (key {key})' if key is not None else name


def error_escape(raw: object) -> str | None:
    """The escape token when ``raw`` is ``{"9": "<token>"}``, else None.

    Key 9 wins over everything else in the payload: a model that emits the
    escape *and* a half-built option array is telling us the sense is
    unsupportable, and the array is not worth reading.
    """
    value = read_index(raw, ERROR_ESCAPE_KEY)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def validate_escape(raw: object, *, expected: str) -> list[str] | None:
    """Three-way: None = not an escape, [] = a valid one, else errors.

    An unrecognised token is an error rather than a skip. The tokens are a
    closed enum matched by code, so a novel one means the prompt and the
    generator have drifted apart — which must fail loudly, not silently drop
    every sense it touches.
    """
    token = error_escape(raw)
    if token is None:
        return None
    if token != expected:
        return [
            f'{labelled("error escape", ERROR_ESCAPE_KEY)}: unknown token '
            f'{token!r} (expected {expected!r})'
        ]
    return []


# ---------------------------------------------------------------------------
# Field checks
# ---------------------------------------------------------------------------

def validate_options(
    options: object,
    *,
    expected: int = 4,
    require_explanation: bool = True,
    label: str = 'options',
) -> list[str]:
    """Check an MCQ option array. Returns error strings (empty when valid).

    Rules: exactly ``expected`` entries, each an object with non-empty text
    (key 0) and a boolean is_correct (key 1), and exactly one entry flagged
    correct. An explanation (key 2) is required by default — every ladder MCQ
    shows one after the answer, and an option without one renders a blank
    rationale.
    """
    errors: list[str] = []

    if not isinstance(options, list):
        return [f'{label}: expected a list, got {type(options).__name__}']
    if len(options) != expected:
        errors.append(f'{label}: expected {expected} entries, got {len(options)}')

    correct = 0
    for i, opt in enumerate(options):
        if not isinstance(opt, dict):
            errors.append(f'{label}[{i}]: expected an object, got {type(opt).__name__}')
            continue

        text = read_index(opt, OPT_TEXT)
        if not isinstance(text, str) or not text.strip():
            errors.append(f'{label}[{i}]: missing non-empty "text" (key {OPT_TEXT})')

        flag = read_index(opt, OPT_IS_CORRECT)
        if not isinstance(flag, bool):
            errors.append(
                f'{label}[{i}]: "is_correct" (key {OPT_IS_CORRECT}) must be a boolean'
            )
        elif flag:
            correct += 1

        if require_explanation and not str(read_index(opt, OPT_EXPLANATION) or '').strip():
            errors.append(
                f'{label}[{i}]: missing non-empty "explanation" (key {OPT_EXPLANATION})'
            )

    if isinstance(options, list) and correct != 1:
        errors.append(f'{label}: expected exactly 1 correct option, got {correct}')

    return errors


def option_text(opt: object) -> str:
    """The option's text (key 0) as a stripped string, '' when absent."""
    return str(read_index(opt, OPT_TEXT) or '').strip()


def is_correct(opt: object) -> bool:
    """Whether this option is flagged correct (key 1)."""
    return read_index(opt, OPT_IS_CORRECT) is True


def validate_index(
    value: object, name: str, *, key: str | int | None = None,
) -> list[str]:
    """Check an optional sentence index: a non-negative int when present."""
    label = labelled(name, key)
    if value is None:
        return []
    if isinstance(value, bool) or not isinstance(value, int):
        return [f'{label}: expected an integer, got {type(value).__name__}']
    if value < 0:
        return [f'{label}: expected a non-negative integer, got {value}']
    return []


def validate_text(
    value: object, name: str, *, key: str | int | None = None, required: bool = True,
) -> list[str]:
    """Check a string field: present and non-empty when ``required``."""
    label = labelled(name, key)
    if value is None or (isinstance(value, str) and not value.strip()):
        return [f'{label}: missing non-empty string'] if required else []
    if not isinstance(value, str):
        return [f'{label}: expected a string, got {type(value).__name__}']
    return []
