# services/vocabulary_ladder/bundle/mapping.py
"""Map ``vocab_bundle_generation`` output onto the EXISTING word_assets shapes.

TASK-815's whole point is "one call, then N existing remaps" (see the header
of ``migrations/exercise_gen_bundle_prompts_draft.sql``): every function here
takes the raw numeric-keyed fragment for ONE block of ONE variant and calls
the SAME remap method the corresponding per-generator module already uses,
then runs the SAME schema/validator gate that generator's caller already
runs. Nothing here re-implements a remap or a validation rule — it only
decides which existing one applies to which bundle key, and reproduces the
few lines (error-escape handling for the split/typed families) that those
generators inline into their own ``generate()`` rather than exposing as a
standalone function.

Two numeric-key conventions coexist in one bundle response, matching the two
conventions the individual prompts already use (see
``services.vocabulary_ladder.config.OPTION_KEY_MAP`` vs
``LADDER_OPTION_KEY_MAP``, and the docstring of
``services.exercise_generation.schemas._shared``):

* P2 family (levels 1/3/5/6): 1-based option keys (``OPTION_KEY_MAP``),
  handled by :func:`build_p2_content`.
* P3-split/typed family (levels 4/8, and the typed types): 0-based option
  keys with a reserved ``"9"`` error-escape, handled by
  :func:`build_l4_fragment`, :func:`build_l8_fragment`,
  :func:`build_typed_fragment`. The P3 monolith's own level 7 has neither
  convention (it isn't an option array at all) and is handled by
  :func:`build_l7_fragment`.

Every ``build_*`` function returns ``(content_or_fragment, errors)``:

* ``errors`` non-empty  → schema/validator rejected the block; the caller
  (``generator.BundleGenerator``) falls back to the real per-generator call
  for just this asset family.
* ``errors == []`` and the result is ``{}``  → a clean skip (not requested,
  or the model correctly declined via the "9" escape) — NOT a failure, and
  must not trigger a fallback call.
* ``errors == []`` and the result is a non-empty dict → ready to store,
  identical in shape to what the existing generator/validator pair would
  have produced.

None of these functions perform I/O: no ``db``, no ``call_llm``. They
instantiate the existing generator classes with ``db=None`` purely to reuse
their (pure) ``_remap``/``_remap_output`` instance methods, none of which
touch ``self.db`` — only the fallback path in ``generator.py`` uses a real
``db``.
"""

from __future__ import annotations

from services.exercise_generation.schemas import (
    SchemaError, error_escape, validate_ladder_output,
)
from services.vocabulary_ladder.asset_generators.l4_morphology import (
    MorphologySlotGenerator,
)
from services.vocabulary_ladder.asset_generators.l8_repair import (
    CollocationRepairGenerator,
)
from services.vocabulary_ladder.asset_generators.prompt2_exercises import (
    ExerciseAssetGenerator,
)
from services.vocabulary_ladder.asset_generators.prompt3_transforms import (
    TransformAssetGenerator,
)
from services.vocabulary_ladder.asset_generators import typed_llm
from services.vocabulary_ladder.config import PROMPT2_LEVELS
from services.vocabulary_ladder.validators import VocabAssetValidator

# The schema version bundle-produced fragments are gated against. Independent
# of prompt_templates.version for the per-language split/typed rows (those
# may sit on version 2 by the time this ships) — 1 is the shape every
# registered schema module in services/exercise_generation/schemas accepts
# today (PROMPT_VERSIONS includes 1 for all of morphology_slot,
# collocation_repair, synonym_antonym_match, word_family,
# particle_selection), and it is what this bundle prompt's draft text
# documents. Re-derive if the bundle prompt is ever versioned past the shape
# those modules' version-1 branch expects.
SCHEMA_GATE_VERSION = 1

_validator = VocabAssetValidator()


# ---------------------------------------------------------------------------
# P2 family — levels 1, 3, 5, 6 (1-based option contract)
# ---------------------------------------------------------------------------

def build_p2_content(
    raw_variant: dict,
    p2_active_levels: list[int],
    sentence_assignments: dict[int, int],
    language_id: int,
) -> tuple[dict, list[str]]:
    """The P2 (level_1/level_3/level_5/level_6) content for one variant.

    ``raw_variant`` is the bundle's per-variant dict (e.g. ``bundle['A']``);
    only the keys in ``p2_active_levels`` are read from it, mirroring
    ``ExerciseAssetGenerator.generate``'s own ``p2_active`` filter.

    Returns ``({}, [])`` when ``p2_active_levels`` is empty (P2 not
    requested at all this sense) — a clean skip, matching
    ``ExerciseAssetGenerator.generate``'s "no Prompt 2 levels active" return.
    """
    p2_levels = sorted(lv for lv in p2_active_levels if lv in PROMPT2_LEVELS)
    if not p2_levels:
        return {}, []

    numeric_raw = {
        str(lv): (raw_variant or {}).get(str(lv))
        for lv in p2_levels
        if str(lv) in (raw_variant or {})
    }
    gen = ExerciseAssetGenerator(db=None, language_id=language_id)
    content = gen._remap_output(numeric_raw, p2_levels, sentence_assignments)
    _, errors = _validator.validate_prompt2(content, p2_levels)
    return content, errors


# ---------------------------------------------------------------------------
# P3 monolith — level 7 only (its own ad hoc numeric contract, not an
# option array)
# ---------------------------------------------------------------------------

def build_l7_fragment(raw_variant: dict, language_id: int) -> tuple[dict, list[str]]:
    """The ``{'level_7': {...}}`` fragment for one variant, or ``({}, [])``.

    ``raw_variant.get('7')`` absent means L7 was not requested (or the model
    omitted it) — treated as a clean skip here; the caller decides whether an
    *expected* L7 going missing counts as a failure (it does, via the same
    "missing level" contract ``TransformAssetGenerator.generate`` already
    has, reproduced by the caller checking ``'level_7' not in fragment`` when
    L7 was in ``active_levels``).
    """
    if '7' not in (raw_variant or {}):
        return {}, []

    gen = TransformAssetGenerator(db=None, language_id=language_id)
    fragment = gen._remap_output({'7': raw_variant['7']}, [7])
    if 'level_7' not in fragment:
        return {}, ['Missing level_7']

    errors: list[str] = []
    _validator._validate_level_7(fragment['level_7'], errors)
    return fragment, errors


# ---------------------------------------------------------------------------
# Split family — level 4 (morphology_slot) and level 8 (collocation_repair):
# 0-based option contract with a reserved "9" error escape.
# ---------------------------------------------------------------------------

def build_l4_fragment(
    raw_block: object, sentence_index: int, language_id: int,
) -> tuple[dict, list[str]]:
    """The ``{'level_4': {...}}`` fragment, ``({}, [])`` clean skip, or
    ``(None, errors)`` on a schema failure the caller should fall back on.
    """
    return _build_split_fragment(
        type_code='morphology_slot',
        level=4,
        generator_cls=MorphologySlotGenerator,
        raw_block=raw_block,
        sentence_index=sentence_index,
        language_id=language_id,
    )


def build_l8_fragment(
    raw_block: object, sentence_index: int, language_id: int,
) -> tuple[dict, list[str]]:
    """The ``{'level_8': {...}}`` fragment, ``({}, [])`` clean skip, or
    ``(None, errors)`` on a schema failure the caller should fall back on.
    """
    return _build_split_fragment(
        type_code='collocation_repair',
        level=8,
        generator_cls=CollocationRepairGenerator,
        raw_block=raw_block,
        sentence_index=sentence_index,
        language_id=language_id,
    )


def _build_split_fragment(
    *, type_code: str, level: int, generator_cls, raw_block: object,
    sentence_index: int, language_id: int,
) -> tuple[dict | None, list[str]]:
    if raw_block is None:
        return {}, []

    try:
        errors = validate_ladder_output(type_code, SCHEMA_GATE_VERSION, raw_block)
    except SchemaError as exc:
        # An unregistered (type_code, version) pair is a deploy problem, not
        # model noise — surface it as a hard failure so the fallback path
        # (which calls the real per-language generator, unaffected by this
        # gate's version constant) still has a chance to produce the level.
        return None, [str(exc)]
    if errors:
        return None, errors

    # A valid escape (`{"9": "..."}`) passes the schema gate with no errors
    # but carries nothing to remap.
    if error_escape(raw_block):
        return {}, []

    gen = generator_cls(db=None, language_id=language_id)
    fragment = gen._remap(raw_block, sentence_index)
    return {f'level_{level}': fragment}, []


# ---------------------------------------------------------------------------
# Typed family — synonym_antonym_match / word_family / particle_selection:
# same 0-based option contract, dispatched via the typed_llm registry so a
# new registered type needs no change here.
# ---------------------------------------------------------------------------

def build_typed_fragment(
    type_code: str,
    raw_block: object,
    sentence_index: int,
    language_id: int,
    sense_id: int | None = None,
) -> tuple[dict, list[str]]:
    """``{type_code: {...}}`` fragment, ``({}, [])`` clean skip/declined, or
    ``(None, errors)`` on a schema failure the caller should fall back on.

    Unlike the split levels, the escape check is NOT duplicated here —
    ``TypedLLMGenerator.fragment_from_raw`` (the same post-call step
    ``TypedLLMGenerator.generate`` itself uses) already handles it, so this
    reuses that method directly rather than re-deriving its two-line escape
    branch a third time.
    """
    if raw_block is None:
        return {}, []

    generator_cls = typed_llm.generator_class(type_code)
    if generator_cls is None:
        return None, [f'no registered typed generator for type_code={type_code!r}']

    try:
        errors = validate_ladder_output(type_code, SCHEMA_GATE_VERSION, raw_block)
    except SchemaError as exc:
        return None, [str(exc)]
    if errors:
        return None, errors

    gen = generator_cls(db=None, language_id=language_id)
    fragment = gen.fragment_from_raw(raw_block, sentence_index, sense_id)
    return fragment, []
