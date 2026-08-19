"""
Deterministic ladder generators — the no-LLM half of the corpus (TASK-516).

Every exercise type in the capability matrix carries a ``generator`` column of
either ``'llm'`` or ``'deterministic'``. The LLM half runs through the P1/P2/P3
asset pipeline and its judges. This package owns the other half: types whose
content can be derived from data we already hold — a sense's definition, its
pronunciation, a P1 sentence, a classifier dictionary — with no model call and
therefore no cost, no latency, and no judge.

Why a registry rather than more renderer methods
------------------------------------------------
``LadderExerciseRenderer`` dispatches one renderer per *ladder level*, which
worked while the mapping was 1:1. The capability matrix broke that assumption:
L1 for Chinese is ``phonetic_recognition`` *and* ``hanzi_to_pinyin`` *and*
``pinyin_to_hanzi`` *and* ``tone_id_word``; L4 for a Chinese concrete noun is
``classifier_match`` and ``cloze_typed`` where for English it is
``morphology_slot``. Keying on level cannot express that.

So generators register against a **type_code**, and the renderer walks the
matrix rows for the (language, semantic_class) at hand, asking each registered
builder for content. Adding a type becomes: write a module, register it, add a
matrix row. No renderer surgery.

The skip contract (§6.10)
-------------------------
A builder returns ``[]`` when it cannot produce an item, and records *why* via
:class:`Skip`. Silence is not acceptable — "no classifier_match items for this
noun" must be distinguishable from "the classifier dictionary lookup threw".
The batch report and the coverage check (TASK-517) both read these reasons, so
a missing family always has an explanation attached.

Builders never write to the database and never call an LLM. They receive a
:class:`SenseContext` and return content dicts. Anything requiring a network
round-trip belongs on the LLM side of the matrix.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Iterable

from services.vocabulary_ladder.config import (
    EXERCISE_TYPE_FAMILY,
    enabled_capabilities,
    normalize_semantic_class,
    requirements_met,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class SenseContext:
    """Everything a deterministic builder is allowed to see.

    Deliberately a value object over an already-fetched asset rather than a
    handle to the pipeline: a builder that can only read what it was given
    cannot accidentally become a second, undeclared source of LLM calls or
    schema writes.

    ``db`` is the exception — some builders need a dictionary lookup
    (``classifier_match``) or a distractor pool query (``definition_match``).
    It may be None in tests, and every builder must degrade to a skip rather
    than raise when it is.
    """

    sense_id: int
    language_id: int
    lemma: str
    core: dict                                  # the prompt1_core asset
    semantic_class: str | None = None
    tier: str | None = None
    pronunciation: str | None = None
    definition: str | None = None
    db: object | None = None
    nl_language_code: str = 'en'
    # Per-variant sentence assignment, so A and B draw different sentences.
    variant: str = 'A'
    sentence_assignments: dict[int, int] = field(default_factory=dict)

    @property
    def sentences(self) -> list[dict]:
        return (self.core or {}).get('sentences') or []

    def sentence_for_level(self, level: int, default: int = 0) -> dict | None:
        """The sentence this variant assigns to ``level``, or None.

        Clamps rather than raising: an asset with fewer sentences than the
        assignment table expects should yield the last sentence, not an
        exception that kills the whole render.
        """
        sentences = self.sentences
        if not sentences:
            return None
        idx = self.sentence_assignments.get(level, default)
        if idx >= len(sentences):
            idx = len(sentences) - 1
        if idx < 0:
            return None
        return sentences[idx]


@dataclass(frozen=True)
class Skip:
    """A builder's reason for producing nothing, for the batch report."""

    type_code: str
    reason: str


@dataclass(frozen=True)
class Item:
    """One rendered deterministic exercise, before it becomes a row."""

    type_code: str
    ladder_level: int | None
    content: dict

    @property
    def family(self) -> str | None:
        return EXERCISE_TYPE_FAMILY.get(self.type_code)


# A builder takes a context and returns content dicts. Returning [] is normal
# and means "not applicable to this sense" — it must append a Skip to explain.
Builder = Callable[[SenseContext, list], list[dict]]

_REGISTRY: dict[str, Builder] = {}

#: Whether _load_builders() has completed its import sweep. Tracked separately
#: from _REGISTRY because the registry fills up one builder at a time and a
#: partially-filled registry is indistinguishable from a complete one.
_BUILDERS_LOADED = False


def register(type_code: str) -> Callable[[Builder], Builder]:
    """Register a builder for an exercise ``type_code``.

    Registering the same type twice is a programming error rather than a
    last-one-wins merge — two modules quietly fighting over ``readings`` would
    be extremely hard to see in a batch report.
    """
    def decorator(fn: Builder) -> Builder:
        if type_code in _REGISTRY:
            raise ValueError(
                f'deterministic builder for {type_code!r} is already registered '
                f'by {_REGISTRY[type_code].__module__}'
            )
        _REGISTRY[type_code] = fn
        return fn
    return decorator


def registered_types() -> set[str]:
    """Type codes that currently have a deterministic builder."""
    _load_builders()
    return set(_REGISTRY)


def _load_builders() -> None:
    """Import the builder modules so their ``@register`` decorators run.

    Done lazily and inside the function to keep import order irrelevant: the
    renderer imports this package, and the builders import config, so a
    module-level import chain here would be circular for anything that later
    wants to import the renderer from a builder.
    """
    # Guarded on a dedicated flag, NOT on `if _REGISTRY:`. A non-empty registry
    # does not mean the builders were loaded — it means *at least one* of them
    # was imported, which happens whenever anything imports a builder module
    # directly. routes/practice.py does exactly that to reach cloze_typed.grade,
    # and under the old guard that single import made this function a no-op and
    # left the other six builders permanently unregistered: every sense would
    # silently generate one exercise type instead of seven, with no skip reason
    # to explain it. Re-running the imports is cheap and idempotent.
    global _BUILDERS_LOADED
    if _BUILDERS_LOADED:
        return
    _BUILDERS_LOADED = True
    from services.vocabulary_ladder.deterministic import (  # noqa: F401
        classifier_match, cloze_typed, counter_match,
        definition_match, jumbled, readings, tone,
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def deterministic_rows(
    language_id: int,
    semantic_class: str | None,
    context: dict | None = None,
) -> list[dict]:
    """Enabled deterministic capability rows that have a registered builder.

    ``context`` is the ``requires`` context (see ``config.requirements_met``);
    rows whose requirements this word cannot meet are dropped here rather than
    inside each builder, so the "why" is uniform.
    """
    _load_builders()
    gate_class = normalize_semantic_class(semantic_class)
    return [
        cap for cap in enabled_capabilities(language_id, gate_class)
        if cap['generator'] == 'deterministic'
        and cap['type_code'] in _REGISTRY
        and requirements_met(cap.get('requires', ()), context or {})
    ]


def generate(
    ctx: SenseContext,
    type_codes: Iterable[str] | None = None,
    context: dict | None = None,
) -> tuple[list[Item], list[Skip]]:
    """Run every applicable deterministic builder for one sense.

    Returns ``(items, skips)``. A builder that raises is logged and recorded as
    a skip — one broken generator must not cost a sense its other seven
    exercise types.

    ``type_codes`` narrows the run (used by the queue drain to regenerate a
    single missing family); None means "everything the matrix allows".
    """
    wanted = set(type_codes) if type_codes is not None else None
    items: list[Item] = []
    skips: list[Skip] = []

    for cap in deterministic_rows(ctx.language_id, ctx.semantic_class, context):
        type_code = cap['type_code']
        if wanted is not None and type_code not in wanted:
            continue
        builder = _REGISTRY[type_code]
        try:
            contents = builder(ctx, skips) or []
        except Exception as exc:
            logger.error(
                'deterministic builder %s failed for sense %s: %s',
                type_code, ctx.sense_id, exc,
            )
            skips.append(Skip(type_code, f'builder raised: {exc}'))
            continue
        for content in contents:
            if content:
                items.append(Item(type_code, cap['ladder_level'], content))

    return items, skips
