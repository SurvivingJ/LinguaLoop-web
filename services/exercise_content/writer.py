"""``dual`` write path behind ``store.write_sense`` (ADR-047 §4, §8, §9).

Stub from TASK-976; TASK-979 implements it. ``store`` imports this module
lazily, only when ``write_mode() == 'dual'``.

Contract with ``store``: ``store.write_sense`` has already

* validated the arguments without I/O in strict mode: ``sense_id`` and
  ``language_id`` are positive ints; every insert row is a dict with a
  canonical lowercase UUID ``id`` (unique in the call), ``word_sense_id`` equal
  to ``sense_id`` (int-like), ``language_id`` equal to ``language_id`` and a
  dict ``content``; every update id is a canonical UUID not inserted in the same
  call, with a dict value; ``max_retries >= 1``;
* normalised the arguments: ``insert_rows`` is a ``list``, ``delete_where`` a
  ``store.DeleteWhere`` (levels a sorted tuple of unique ints) or None,
  ``update_contents`` a ``dict`` (possibly empty);
* returned early, without calling this module, when there is nothing to do.

Still the writer's job (they need ``exercise_content_begin``): update ids must
belong to the sense and not be deleted by ``delete_where`` (``ValueError``
before any upload).

Shared plumbing in ``store`` (see its module docstring): ``store.backend()``,
``store.content_path``, ``store.encode_sense_file`` / ``decode_sense_file``,
``store.COMMIT_LOCK_NAMESPACE``, ``store._warn_once``, and for warming the read
cache after a commit ``store._content_cache()`` (``None`` until TASK-977's
``cache.py`` exists — that is the feature detection) keyed by
``store._cache_key(language_id, sense_id, version)``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.exercise_content.store import DeleteWhere, WriteResult


def write_sense_dual(db, sense_id: int, language_id: int, *, insert_rows: Sequence[dict],
                     delete_where: DeleteWhere | None, update_contents: Mapping[str, dict],
                     max_retries: int) -> WriteResult:
    """File first, then the rows by compare-and-swap (ADR-047 §4)."""
    raise NotImplementedError('TASK-979')
