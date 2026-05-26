"""Cloze distractor judge — backward-compat shim.

The implementation has moved to
``services.exercise_generation.judges.cloze``.  This module re-exports the
public surface so existing callers
(``services.exercise_generation.generators.cloze``,
``services.vocabulary_ladder.exercise_renderer``) continue to work without
modification.

Do not add new logic here.  Extend ``judges/cloze.py`` instead.
"""

# Re-export public surface — callers import from here unchanged.
from services.exercise_generation.judges.cloze import (   # noqa: F401
    judge_distractors,
    filter_distractors,
)
