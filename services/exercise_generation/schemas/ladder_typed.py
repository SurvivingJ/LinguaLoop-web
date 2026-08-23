"""Output schemas for the type-registered ladder prompts.

Three types, one module: ``synonym_antonym_match`` and ``word_family``
(TASK-522) and ``particle_selection`` (TASK-527). They share the
option-array core, and keeping them together makes the one thing that
differs between them — what a *distractor* has to be — readable side by side.

Every shape is bound to ``prompt_version`` through the registry in
``schemas/__init__``; see ``ladder_l4_morphology`` for why an unregistered
version is an error rather than a fallback.

All three return numeric keys per the contract in ``_shared`` — 0 is always the
option array, 9 is always the error escape, and inside an option 0=text,
1=is_correct, 2=explanation.

  synonym_antonym_match (prompt_version 1)::

      {"0": [{"0": str, "1": bool, "2": str} x4],
       "1": "synonym" | "antonym"}
      {"9": "no_relation"}

    The relation (key 1) is the *question*: "which of these is a synonym of
    X?" A distractor here must be a real word that is NOT in that relation to
    the sense — crucially, not merely "not in that relation to the lemma",
    which is the polysemy failure the judge exists to catch.

  word_family (prompt_version 1)::

      {"0": [{"0": str, "1": bool, "2": str, "3": str} x4],
       "1": str}
      {"9": "no_family"}

    Distractors are *invented* derivations — morphologically well-formed but
    not real words ("decisionment"). ``part_of_speech`` (option key 3) is
    required because the slot the learner fills is defined by it. Key 1 is the
    stem.

  particle_selection (prompt_version 1)::

      {"0": [{"0": str, "1": bool, "2": str} x4],
       "1": str,
       "2": {particle: str}}
      {"9": "no_particle_slot"}

    Distractors are other particles. Key 1 is the blanked particle; key 2 is
    ``error_tags``, labelling the confusion class each wrong particle
    represents (direction, topic-vs-subject, …) so the practice engine can
    aggregate what a learner keeps getting wrong.
"""

from __future__ import annotations

from ._shared import (
    OPTIONS_KEY, OPT_PART_OF_SPEECH, is_correct, option_text, read_index,
    validate_escape, validate_options, validate_text,
)

SCHEMA_VERSION = 1
PROMPT_VERSIONS: frozenset[int] = frozenset({1, 2})

OPTION_COUNT = 4

RELATIONS = ('synonym', 'antonym')


# ---------------------------------------------------------------------------
# synonym_antonym_match
# ---------------------------------------------------------------------------

class _SynAnt:
    TYPE_CODE = 'synonym_antonym_match'
    PROMPT_VERSIONS = PROMPT_VERSIONS
    SCHEMA_VERSION = SCHEMA_VERSION
    ERROR_TOKEN = 'no_relation'
    KEY_LEGEND = {OPTIONS_KEY: 'options', '1': 'relation'}

    @staticmethod
    def validate(raw: object) -> list[str]:
        if not isinstance(raw, dict):
            return [f'synonym_antonym_match: expected an object, got {type(raw).__name__}']

        escape = validate_escape(raw, expected=_SynAnt.ERROR_TOKEN)
        if escape is not None:
            return escape

        errors = validate_options(read_index(raw, OPTIONS_KEY), expected=OPTION_COUNT)
        relation = read_index(raw, '1')
        if relation not in RELATIONS:
            errors.append(
                f'relation (key 1): expected one of {list(RELATIONS)}, got {relation!r}'
            )
        return errors


# ---------------------------------------------------------------------------
# word_family
# ---------------------------------------------------------------------------

class _WordFamily:
    TYPE_CODE = 'word_family'
    PROMPT_VERSIONS = PROMPT_VERSIONS
    SCHEMA_VERSION = SCHEMA_VERSION
    ERROR_TOKEN = 'no_family'
    KEY_LEGEND = {OPTIONS_KEY: 'options', '1': 'stem'}

    @staticmethod
    def validate(raw: object) -> list[str]:
        if not isinstance(raw, dict):
            return [f'word_family: expected an object, got {type(raw).__name__}']

        escape = validate_escape(raw, expected=_WordFamily.ERROR_TOKEN)
        if escape is not None:
            return escape

        errors = validate_options(read_index(raw, OPTIONS_KEY), expected=OPTION_COUNT)
        errors += validate_text(read_index(raw, '1'), 'stem', key='1')

        options = read_index(raw, OPTIONS_KEY)
        if isinstance(options, list):
            for i, opt in enumerate(options):
                if not isinstance(opt, dict):
                    continue
                if not str(read_index(opt, OPT_PART_OF_SPEECH) or '').strip():
                    errors.append(
                        f'options[{i}]: missing "part_of_speech" (key {OPT_PART_OF_SPEECH})'
                    )
        return errors


# ---------------------------------------------------------------------------
# particle_selection
# ---------------------------------------------------------------------------

class _ParticleSelection:
    TYPE_CODE = 'particle_selection'
    PROMPT_VERSIONS = PROMPT_VERSIONS
    SCHEMA_VERSION = SCHEMA_VERSION
    ERROR_TOKEN = 'no_particle_slot'
    KEY_LEGEND = {OPTIONS_KEY: 'options', '1': 'blanked_particle', '2': 'error_tags'}

    @staticmethod
    def validate(raw: object) -> list[str]:
        if not isinstance(raw, dict):
            return [f'particle_selection: expected an object, got {type(raw).__name__}']

        escape = validate_escape(raw, expected=_ParticleSelection.ERROR_TOKEN)
        if escape is not None:
            return escape

        errors = validate_options(read_index(raw, OPTIONS_KEY), expected=OPTION_COUNT)
        errors += validate_text(read_index(raw, '1'), 'blanked_particle', key='1')

        options = read_index(raw, OPTIONS_KEY)
        blanked = str(read_index(raw, '1') or '').strip()

        # The blanked particle IS the answer. A response whose correct option
        # is some other particle means the model re-chose the blank after
        # being told which one to use, and the renderer would then cut a hole
        # the answer does not fill.
        if blanked and isinstance(options, list):
            correct = [
                option_text(o) for o in options
                if isinstance(o, dict) and is_correct(o)
            ]
            if correct and correct[0] != blanked:
                errors.append(
                    f'options: the correct option {correct[0]!r} is not the '
                    f'blanked particle {blanked!r}'
                )

        error_tags = read_index(raw, '2')
        if error_tags is not None and not isinstance(error_tags, dict):
            errors.append(
                f'error_tags (key 2): expected an object, got {type(error_tags).__name__}'
            )
        return errors


# Module-level aliases so each type reads like its own schema module to the
# registry, which only needs TYPE_CODE / PROMPT_VERSIONS / validate.
synonym_antonym_match = _SynAnt
word_family = _WordFamily
particle_selection = _ParticleSelection

TYPED_SCHEMAS = (synonym_antonym_match, word_family, particle_selection)
