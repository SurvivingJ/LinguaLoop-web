"""``storage`` / ``shadow`` read path behind ``store.hydrate`` and ``store.fetch_sense``.

Stub from TASK-976; TASK-978 implements it (ADR-047 §5 and §9). ``store`` imports
this module lazily, only in a non-``db`` read mode or from ``fetch_sense``.

Contract with ``store``:

* ``store.hydrate`` validates the arguments, returns early in ``db`` mode and
  calls ``hydrate(items, ..., mode=<'storage'|'shadow'>)`` with ``language_id``
  already an int or None, ``max_senses`` an int >= 0 and ``deadline_s`` a float
  > 0 (``None`` resolved from ``EXERCISE_CONTENT_MAX_SENSES_PER_CALL`` /
  ``EXERCISE_CONTENT_DEADLINE_S``). A direct call may still pass ``None`` for
  either; treat it the same way.
* In ``shadow`` mode ``store.hydrate`` swallows (and logs) any exception other
  than ``ValueError``; in ``storage`` mode exceptions propagate, so ``hydrate``
  must not raise for storage, network or data problems.
* Shared plumbing lives in ``store`` (see its module docstring):
  ``store.backend()``, ``store.decode_sense_file``, ``store._content_cache()``,
  ``store._negative_cache()``, ``store._cache_key(...)``, ``store._setting_*``,
  ``store._warn_once`` and ``store._on_reset(key, fn)`` for the fetch executor,
  the DB-fallback switch and the shadow queue, which ``store.reset_state()``
  must clear.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.exercise_content.store import HydrationReport


def hydrate(items: list[dict], *, language_id: int | None, id_key: str, sense_key: str,
            db, drop_missing: bool, max_senses: int | None, deadline_s: float | None,
            mode: str) -> HydrationReport:
    """``storage`` / ``shadow`` hydration of ``items`` in place (ADR-047 §9 ``hydrate``)."""
    raise NotImplementedError('TASK-978')


def fetch_sense(language_id: int, sense_id: int, version: int) -> dict[str, dict] | None:
    """exercise_id -> content of one file (fresh objects), via the cache; None when
    missing, unreadable or corrupt (logged). Never raises."""
    raise NotImplementedError('TASK-978')
