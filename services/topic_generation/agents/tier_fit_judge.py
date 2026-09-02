"""Tier-fit validator for generated topics (plan §3, T3.1).

Judges an *existing* topic against the tier it is stamped with, on the evidence
of its ``distinctive_vocabulary``: is this vocabulary reachable by a reader at
this tier? Returns pass/fail plus a reason, one call per (topic, tier).

Why this shape and not the other one
------------------------------------
The idea originally floated was a judge that rewrites one topic for all six
tiers at once, blanking the tiers where the language would be too hard. The
"blank if unsuitable" half is the valuable half and is what this implements.
The fan-one-topic-across-six-tiers half is deliberately not built:

1. **It amplifies the duplicate-content problem.** ``test_generation/dedup.py``
   scopes its checks to (topic_id, target_age_tier) and never compares across
   tiers, by design. Six tier-variants of one concept become six topic rows
   that no dedup check will ever compare, and a learner progressing T1 -> T2 ->
   T3 meets the same concept three times.
2. **The Explorer is not what is broken.** Per-tier ideation already produces
   good, age-appropriate topics — measured T1 output includes "A red ball
   bouncing" and "Baby's first bath time", and passage length and vocabulary
   load scale cleanly from T1 (350 chars / 22 senses) to T6 (4802 / 266).
   Replacing a working generator to fix a coverage gap is disproportionate.
3. **Asking for all six tiers in one call invites over-production.** A model
   told "blank if unsuitable" treats blanking as failure and fills all six.
   That is the trap already on record in the ja judge/generator doctrine: a
   closed enumeration inside a judge prompt behaves as an allow-list. So each
   tier is asked about **independently**, and every answer is a real yes/no.

Fails **open**: an unreachable or unparseable judge returns ``pass`` with a
reason saying why it could not decide. A topic is not worth losing to a judge
outage, and the caller can tell an unjudged pass from a judged one.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional, Sequence

logger = logging.getLogger(__name__)

# ADR-003 age tiers, described by the reader rather than by a number so the
# judge is reasoning about a person, not an ordinal. Mirrors
# dim_complexity_tiers.description.
TIER_READERS: dict[int, str] = {
    1: 'a 4-5 year old (about 500 words; basic verbs and nouns; '
       'one idea per sentence)',
    2: 'an 8-9 year old (about 2,000 words; compound sentences; '
       'literal and concrete)',
    3: 'a 13-14 year old (about 5,000 words; colloquialisms, mild idiom, '
       'conditionals)',
    4: 'a 16-17 year old (about 10,000 words; standard adult grammar, '
       'moderate jargon)',
    5: 'a university student aged 19-21 (15,000+ words; full breadth, '
       'complex clauses)',
    6: 'an educated professional aged 30+ (25,000+ words; high register, '
       'domain jargon, rhetoric)',
}

_PROMPT = """You are checking whether one topic is pitched at the right level \
for one specific reader.

READER: {reader}

TOPIC: {concept}
DISTINCTIVE VOCABULARY: {vocabulary}

The distinctive vocabulary is the wording a passage on this topic would have to \
use. Judge ONLY whether that vocabulary is reachable for this reader — a word \
they either know or could reasonably meet and learn from context at this level.

Do not judge whether the topic is interesting, whether it is well written, or \
whether the reader would enjoy it. Judge reachability of the language.

Answer with JSON only:
{{"fits": true or false, "reason": "<one short sentence>"}}"""


@dataclass(frozen=True)
class TierFitVerdict:
    """One judge decision about one (topic, tier) pair."""

    fits: bool
    reason: str
    #: False when the judge could not be reached or could not be parsed, so the
    #: `fits=True` above is a fail-open default rather than an actual opinion.
    judged: bool = True

    @property
    def unjudged_pass(self) -> bool:
        return self.fits and not self.judged


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


def _parse(raw: str) -> Optional[TierFitVerdict]:
    """Parse the judge's reply, tolerating a fenced or chatty wrapper."""
    if not raw:
        return None
    text = raw.strip()
    match = re.search(r'\{.*\}', text, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or 'fits' not in data:
        return None
    fits = data.get('fits')
    if not isinstance(fits, bool):
        return None
    return TierFitVerdict(
        fits=fits,
        reason=str(data.get('reason') or '').strip() or 'no reason given',
    )


class TierFitJudge:
    """Judges one (topic, tier) pair at a time. See the module docstring."""

    def __init__(self, call_llm=None, model: Optional[str] = None):
        if call_llm is None:
            from services.llm_service import call_llm as _call
            call_llm = _call
        self._call_llm = call_llm
        self._model = model

    def judge(
        self,
        concept: str,
        distinctive_vocabulary,
        tier: int,
        language_code: Optional[str] = None,
    ) -> TierFitVerdict:
        """Does ``concept``'s vocabulary suit a reader at ``tier``?"""
        reader = TIER_READERS.get(int(tier)) if tier is not None else None
        if reader is None:
            return TierFitVerdict(
                True, f'no reader profile for tier {tier!r}', judged=False,
            )

        vocabulary = _vocabulary_text(distinctive_vocabulary)
        if not vocabulary:
            # Nothing to judge on. Explicitly unjudged rather than a quiet
            # pass: a topic with no distinctive vocabulary is itself a gap.
            return TierFitVerdict(
                True, 'topic has no distinctive_vocabulary to judge',
                judged=False,
            )

        prompt = _PROMPT.format(
            reader=reader, concept=concept, vocabulary=vocabulary,
        )
        try:
            raw = self._call_llm(
                prompt,
                model=self._model,
                response_format='json_object',
                task_name='judge_topic_tier_fit',
                language_code=language_code,
            )
        except Exception as exc:
            logger.warning(
                'tier-fit judge unavailable for %r at T%s: %s',
                concept[:40], tier, exc,
            )
            return TierFitVerdict(
                True, f'judge unavailable: {type(exc).__name__}', judged=False,
            )

        verdict = _parse(raw if isinstance(raw, str) else json.dumps(raw))
        if verdict is None:
            logger.warning(
                'tier-fit judge returned unparseable output for %r at T%s',
                concept[:40], tier,
            )
            return TierFitVerdict(
                True, 'judge output unparseable', judged=False,
            )
        return verdict

    def best_tier(
        self,
        concept: str,
        distinctive_vocabulary,
        candidate_tiers: Sequence[int],
        language_code: Optional[str] = None,
    ) -> tuple[Optional[int], list[tuple[int, TierFitVerdict]]]:
        """Lowest tier from ``candidate_tiers`` whose reader can reach the
        vocabulary, plus every verdict collected on the way.

        Used to stamp a tier on the topics that have none (T3.4). Lowest-fitting
        rather than best-fitting because tier is a *floor* on reader capability:
        a topic an 8-year-old can read is also readable at every tier above, and
        placing it as low as it honestly goes is what widens coverage at the
        thin end.

        Tiers are asked about one at a time, ascending, and the walk stops at
        the first fit — so the common case costs one or two calls, not six, and
        no single call is ever handed a menu of six options to fill in.

        Returns ``(None, verdicts)`` when no candidate tier fits, or when every
        verdict was a fail-open unjudged pass — an unjudged pass is not evidence
        and must not be used to stamp a tier.
        """
        verdicts: list[tuple[int, TierFitVerdict]] = []
        for tier in sorted(candidate_tiers):
            verdict = self.judge(
                concept, distinctive_vocabulary, tier, language_code,
            )
            verdicts.append((tier, verdict))
            if verdict.fits and verdict.judged:
                return tier, verdicts
        return None, verdicts
