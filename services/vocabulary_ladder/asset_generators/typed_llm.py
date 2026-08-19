# services/vocabulary_ladder/asset_generators/typed_llm.py
"""LLM generators that register against an exercise *type* (TASK-522, TASK-527).

Why this exists alongside the level renderers
---------------------------------------------
``LadderExerciseRenderer`` dispatches one renderer per ladder *level*, which
the capability matrix broke: L4 for Japanese is ``particle_selection`` where
for English it is ``morphology_slot``, and L6 carries
``semantic_discrimination`` *and* ``synonym_antonym_match``. Keying on level
cannot express that.

``vocabulary_ladder.deterministic`` already solved the same problem for the
no-LLM half of the corpus: builders register against a ``type_code`` and the
renderer walks the matrix rows. This module is the LLM half of that idea —
same registry shape, same skip contract, but each generator owns a prompt, a
schema-gated response, and a judge.

Why not just add levels to P2/P3
--------------------------------
Every type here is language-specific (particles are Japanese; word families
are English) or class-specific (syn/ant needs an abstract-ish sense). Folding
them into a shared prompt would recreate exactly the coupling TASK-520 spent
its budget undoing.

The two halves of a generator
-----------------------------
``generate``  (offline, in the pipeline)  → an asset fragment stored under
              ``word_assets.content[type_code]`` of the ``llm_types_{A,B}``
              asset.
``render``    (offline, in the renderer)  → an exercise ``content`` dict,
              judged on the way through, or None to skip the item.

Splitting them this way keeps regeneration cheap: re-rendering a sense after a
judge change costs nothing, because the model's answer is already stored.
"""

from __future__ import annotations

import logging
from typing import Iterable

from services.exercise_generation.schemas import error_escape
from services.vocabulary_ladder.asset_generators._split_base import SplitLevelGenerator
from services.vocabulary_ladder.config import (
    enabled_capabilities, normalize_semantic_class, requirements_met,
)

logger = logging.getLogger(__name__)

#: Asset type prefix. Variant A/B are stored separately, mirroring P2/P3.
ASSET_TYPE_PREFIX = 'llm_types'


def asset_type_for(variant: str) -> str:
    return f'{ASSET_TYPE_PREFIX}_{variant}'


class TypedLLMGenerator(SplitLevelGenerator):
    """A prompt that produces exactly one exercise *type* for one sense.

    Inherits the template resolution, the schema-gated call and the single
    retry from :class:`SplitLevelGenerator`; overrides only the result key,
    because a type-keyed generator has no ladder level to name its output
    after (``timed_speed_round`` and friends carry ``ladder_level = NULL``).
    """

    #: Set by subclasses. ``LADDER_LEVEL`` may be None for non-ladder types.
    LADDER_LEVEL: int | None = None

    #: Which sentence assignment slot this type draws from, when it needs a
    #: sentence at all. None means the generator does not use one.
    SENTENCE_SLOT: int | None = None

    @property
    def LEVEL(self) -> int:            # noqa: N802 — matches the base attribute
        """Only used for log messages in the base class."""
        return self.LADDER_LEVEL or 0

    def generate(
        self,
        sense_id: int,
        core_asset: dict,
        sentence_assignments: dict[int, int],
        used_distractors: list[str] | None = None,
    ) -> dict | None:
        """``{type_code: fragment}`` on success, ``{}`` skip, None failure."""
        sentence_index = self._sentence_index(core_asset, sentence_assignments)
        if sentence_index is None:
            logger.info(
                '%s skipped for sense %s — sense does not support the type',
                self.TYPE_CODE, sense_id,
            )
            return {}

        try:
            cfg = self.cfg
        except Exception as exc:
            logger.error(
                '%s template config unavailable for lang=%s: %s',
                self.TYPE_CODE, self.language_id, exc,
            )
            return None

        from services.vocabulary_ladder.asset_generators._renderer import render_template
        prompt = render_template(
            cfg['template'],
            **self._prompt_vars(core_asset, sentence_index, used_distractors or []),
        )

        raw = self._call_with_retry(prompt, cfg, sense_id)
        if raw is None:
            return None

        # Key 9: the model says this sense cannot carry the type. Same outcome
        # as a failed precondition — a skip, not a failure.
        declined = error_escape(raw)
        if declined:
            logger.info(
                '%s declined by the model for sense %s: %s',
                self.TYPE_CODE, sense_id, declined,
            )
            return {}

        fragment = self._remap(raw, sentence_index)
        # Recorded so the renderer can reconstruct which sentence the model
        # was shown without re-deriving the assignment table.
        if isinstance(fragment, dict):
            fragment.setdefault('sentence_index', sentence_index)
        return {self.TYPE_CODE: fragment}

    # ------------------------------------------------------------------

    def _sentence_index(
        self, core_asset: dict, sentence_assignments: dict[int, int],
    ) -> int | None:
        """Default: the variant's slot for this type, clamped to the pool.

        Generators with no sentence requirement set ``SENTENCE_SLOT = None``
        and get index 0 as a placeholder, so "is this sense usable?" stays a
        single decision made by :meth:`_supports` rather than being smeared
        across two methods.
        """
        if not self._supports(core_asset):
            return None
        sentences = self.sentences(core_asset)
        if self.SENTENCE_SLOT is None:
            return 0
        if not sentences:
            return None
        index = sentence_assignments.get(self.SENTENCE_SLOT, 0)
        if index >= len(sentences):
            index = len(sentences) - 1
        return index if index >= 0 else None

    def _supports(self, core_asset: dict) -> bool:
        """Whether this sense can carry the type at all. Override as needed."""
        return True

    def render(
        self, db, fragment: dict, core: dict, sense_id: int,
        language_id: int, nl_code: str,
    ) -> dict | None:
        """Turn a stored fragment into exercise content, or None to skip."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, type[TypedLLMGenerator]] = {}


def register(cls: type[TypedLLMGenerator]) -> type[TypedLLMGenerator]:
    """Class decorator: claim a ``type_code``.

    Registering a type twice raises rather than last-one-wins — two modules
    quietly fighting over ``word_family`` would be very hard to see in a batch
    report.
    """
    type_code = cls.TYPE_CODE
    if type_code in _REGISTRY:
        raise ValueError(
            f'typed LLM generator for {type_code!r} is already registered by '
            f'{_REGISTRY[type_code].__module__}'
        )
    _REGISTRY[type_code] = cls
    return cls


def _load_generators() -> None:
    """Import the generator modules so their decorators run.

    Lazy and function-local so import order stays irrelevant: the renderer
    imports this module, and the generators import config.
    """
    if _REGISTRY:
        return
    from services.vocabulary_ladder.asset_generators import (  # noqa: F401
        particle_selection, syn_ant, word_family,
    )


def registered_types() -> set[str]:
    _load_generators()
    return set(_REGISTRY)


def generator_class(type_code: str) -> type[TypedLLMGenerator] | None:
    _load_generators()
    return _REGISTRY.get(type_code)


def applicable_types(
    language_id: int,
    semantic_class: str | None,
    context: dict | None = None,
) -> list[dict]:
    """Enabled LLM capability rows that have a registered typed generator.

    Mirrors ``deterministic.deterministic_rows``: rows whose ``requires`` this
    word cannot meet are dropped here rather than inside each generator, so
    the reason a type is absent is uniform across the two halves.
    """
    _load_generators()
    gate_class = normalize_semantic_class(semantic_class)
    return [
        cap for cap in enabled_capabilities(language_id, gate_class)
        if cap['generator'] == 'llm'
        and cap['type_code'] in _REGISTRY
        and requirements_met(cap.get('requires', ()), context or {})
    ]


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

def generate_all(
    db,
    language_id: int,
    sense_id: int,
    core_asset: dict,
    semantic_class: str | None,
    sentence_assignments: dict[int, int],
    capability_context: dict | None = None,
    type_codes: Iterable[str] | None = None,
) -> tuple[dict, list[str]]:
    """Run every applicable typed generator for one sense and variant.

    Returns ``(fragments, failures)`` where ``fragments`` maps type_code to the
    stored asset fragment and ``failures`` names the types that ran and failed.
    A type that is simply not applicable appears in neither — it is not a
    failure, and reporting it as one would bury the real ones.
    """
    wanted = set(type_codes) if type_codes is not None else None
    fragments: dict = {}
    failures: list[str] = []

    for cap in applicable_types(language_id, semantic_class, capability_context):
        type_code = cap['type_code']
        if wanted is not None and type_code not in wanted:
            continue
        generator = _REGISTRY[type_code](db, language_id)
        try:
            produced = generator.generate(sense_id, core_asset, sentence_assignments)
        except Exception as exc:
            logger.error(
                'typed generator %s raised for sense %s: %s',
                type_code, sense_id, exc,
            )
            failures.append(type_code)
            continue
        if produced is None:
            failures.append(type_code)
        elif produced:
            fragments.update(produced)

    return fragments, failures
