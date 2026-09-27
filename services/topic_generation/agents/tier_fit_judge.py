"""Tier-fit validator for generated topics (plan §3, T3.1) — jev-backed (ADR-029).

Judges an *existing* topic against the tier it is stamped with, on the evidence
of its ``distinctive_vocabulary``: is this vocabulary reachable by a reader at
this tier? Pass/fail plus a reason.

One jev *score* call places the topic on the six-tier scale
(``services.tier_classifier.classify_topic``); the topic fits a tier when its
assessed tier is at or below it. Tier is a *floor* on reader capability: a topic
an 8-year-old can reach is reachable at every tier above, so only a topic that
assesses *harder* than its stamped tier is rejected. The old per-tier yes/no
chat-model walk (up to six sequential calls, fail-open) is gone; a jev failure
raises ``services.jev_client.JevError`` instead of passing the topic unjudged.

Why not fan one topic across six tiers: ``test_generation/dedup.py`` scopes its
checks to (topic_id, target_age_tier) and never compares across tiers, so six
tier-variants of one concept would become six rows no dedup check compares, and
a learner would meet the same concept three times. Unchanged from the original.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from services import tier_classifier
from services.tier_classifier import TierAssessment

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TierFitVerdict:
    """One judge decision about one (topic, tier) pair."""

    fits: bool
    reason: str
    #: What jev actually said, for callers that want the tier itself.
    assessment: Optional[TierAssessment] = None


def _vocabulary_text(distinctive_vocabulary) -> str:
    """Flatten the topic's distinctive_vocabulary blob to a comma list."""
    if not distinctive_vocabulary:
        return ''
    if isinstance(distinctive_vocabulary, str):
        return distinctive_vocabulary
    if isinstance(distinctive_vocabulary, dict):
        # Tolerate {'en': [...]} and {'words': [...]} shapes alike.
        values: list = []
        for value in distinctive_vocabulary.values():
            if isinstance(value, (list, tuple)):
                values.extend(value)
            elif value:
                values.append(value)
        return ', '.join(str(v) for v in values)
    if isinstance(distinctive_vocabulary, (list, tuple)):
        return ', '.join(str(v) for v in distinctive_vocabulary)
    return str(distinctive_vocabulary)


class TierFitJudge:
    """Places a topic on the tier scale with jev. See the module docstring."""

    def __init__(self, classify: Optional[Callable[..., TierAssessment]] = None):
        self._classify = classify or tier_classifier.classify_topic

    def assess(self, concept: str, distinctive_vocabulary) -> TierAssessment:
        """The tier jev assigns this topic. Raises JevError on failure."""
        return self._classify(concept, _vocabulary_text(distinctive_vocabulary))

    def judge(
        self,
        concept: str,
        distinctive_vocabulary,
        tier: int,
        language_code: Optional[str] = None,
    ) -> TierFitVerdict:
        """Is ``concept``'s vocabulary reachable for a reader at ``tier``?

        ``language_code`` is accepted for call-site compatibility and unused:
        topics are English.
        """
        if not 1 <= int(tier) <= tier_classifier.N_TIERS:
            raise ValueError(f'unknown tier {tier!r}')
        assessment = self.assess(concept, distinctive_vocabulary)
        fits = assessment.tier <= int(tier)
        conf = (f', confidence {assessment.confidence:.2f}'
                if assessment.confidence is not None else '')
        reason = (
            f'jev assessed T{assessment.tier} (expected tier '
            f'{assessment.expected_tier:.2f}{conf}) against stamped T{tier}'
        )
        return TierFitVerdict(fits=fits, reason=reason, assessment=assessment)
