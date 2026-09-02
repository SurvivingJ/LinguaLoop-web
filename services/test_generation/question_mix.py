"""Realised-vs-requested question mix reporting (plan §1, T1.3).

``question_type_distributions_by_tier`` was created 2026-08-29. All 307 tests
in the corpus predate it, so no test had ever been generated through the
tier-keyed loader when this was written — its correctness was inferred from
reading ``database_client.get_tier_question_distribution``, not observed.

What a silently-wrong distribution looks like is already on record in the
legacy content: at T6, ``supporting_detail`` is 0 and ``author_purpose`` runs
at twice its intended rate. This module makes the same failure impossible to
miss the next time, by comparing what the tier table asked for against what
the test actually ended up with.

A shortfall is not automatically a defect — the survival floor in the
orchestrator deliberately tolerates losing a question to the judges or the
validator, so a T1 test legitimately ships 3 of 5. The distinction this draws:

  * a type that is **short** was requested and partly lost — expected, INFO.
  * a type that is **absent** was requested and produced nothing — WARNING,
    because it is indistinguishable from a loader that never asked for it.
  * a type that is **unrequested** appeared anyway — WARNING, and a real bug:
    the generator produced a type the tier table did not name.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)


class MixReport:
    """Difference between a requested and a realised question mix."""

    __slots__ = ('requested', 'realised', 'missing', 'short', 'unrequested')

    def __init__(
        self,
        requested: Counter,
        realised: Counter,
        missing: Dict[str, int],
        short: Dict[str, int],
        unrequested: Dict[str, int],
    ):
        self.requested = requested
        self.realised = realised
        #: requested types that produced nothing at all
        self.missing = missing
        #: requested types that produced fewer than asked (excluding `missing`)
        self.short = short
        #: types that appeared without being requested
        self.unrequested = unrequested

    @property
    def matches(self) -> bool:
        """True when the realised mix is exactly what the tier table asked."""
        return not (self.missing or self.short or self.unrequested)

    def __repr__(self) -> str:
        return (
            'MixReport(missing=%r, short=%r, unrequested=%r)'
            % (self.missing, self.short, self.unrequested)
        )


def compare_question_mix(
    requested: Sequence[str],
    realised: Iterable[Optional[str]],
) -> MixReport:
    """Compare a requested type list against the types actually produced.

    ``realised`` entries that are None or blank are ignored rather than counted
    as an unrequested type — a question with no recorded type is a separate
    defect and not this function's to diagnose.
    """
    want = Counter(t for t in requested if t)
    got = Counter(t for t in realised if t)

    missing: Dict[str, int] = {}
    short: Dict[str, int] = {}
    for type_code, n in want.items():
        produced = got.get(type_code, 0)
        if produced == 0:
            missing[type_code] = n
        elif produced < n:
            short[type_code] = n - produced

    unrequested = {
        type_code: n for type_code, n in got.items()
        if type_code not in want
    }
    return MixReport(want, got, missing, short, unrequested)


def report_question_mix(
    requested: Sequence[str],
    realised: Iterable[Optional[str]],
    tier_id: int,
    language_code: str,
) -> MixReport:
    """Compare and log. Returns the report so callers can assert on it."""
    report = compare_question_mix(requested, realised)

    if report.matches:
        logger.info(
            'question mix matches tier %s distribution (%s): %s',
            tier_id, language_code, _fmt(report.realised),
        )
        return report

    if report.unrequested:
        logger.warning(
            'question mix DIVERGED for tier %s (%s): produced type(s) the '
            'tier table never requested: %s | requested=%s realised=%s',
            tier_id, language_code, _fmt(report.unrequested),
            _fmt(report.requested), _fmt(report.realised),
        )

    if report.missing:
        logger.warning(
            'question mix SHORT for tier %s (%s): requested type(s) produced '
            'nothing at all: %s | requested=%s realised=%s',
            tier_id, language_code, _fmt(report.missing),
            _fmt(report.requested), _fmt(report.realised),
        )

    if report.short and not (report.missing or report.unrequested):
        # Partial loss to the judges or the validator, which the survival
        # floor exists to tolerate.
        logger.info(
            'question mix thinned for tier %s (%s): %s (survival floor '
            'absorbed the loss) | requested=%s realised=%s',
            tier_id, language_code, _fmt(report.short),
            _fmt(report.requested), _fmt(report.realised),
        )

    return report


def _fmt(counts) -> str:
    items: List[str] = [
        f'{code} x{n}' for code, n in sorted(dict(counts).items())
    ]
    return ', '.join(items) if items else '(none)'
