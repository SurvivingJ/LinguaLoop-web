# services/vocabulary_ladder/speed_round.py
"""``timed_speed_round`` — a serve-time fluency battery (TASK-533, §5 #21).

What it is
----------
Ten to twenty recognition items over words the learner has already **mastered**,
answered against a per-item clock. No new content is generated: the composer
picks existing L1-L3 items and wraps them in timing metadata.

Why mastered-only, and why that is the whole design
---------------------------------------------------
Time pressure trains *retrieval speed*, which is a different thing from
knowing a word. Applied to a word still being acquired, it does not accelerate
acquisition — it adds noise to the signal the ladder uses to decide whether the
learner knows it, and it teaches them to guess. So the pool is restricted to
``user_word_ladder.word_state = 'mastered'``, and every other filter in this
module exists to keep that restriction honest.

The other consequence: a speed round must not move the ladder. Results feed
FSRS — where "answered fast and correctly" genuinely is evidence for a longer
interval — but they do **not** touch family confidence, because a slow correct
answer under time pressure is not evidence that a learner's ``form_recognition``
has decayed. That split is enforced at the attempt path, and is recorded in
:data:`UPDATES_FAMILY_CONFIDENCE` so the intent is greppable from both sides.

Non-ladder by construction
--------------------------
The capability-matrix row for ``timed_speed_round`` carries
``ladder_level = NULL``, which is what keeps it out of ``active_levels`` and
therefore out of the normal drill rotation. It is reachable only through its
own route.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field

from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)

TYPE_CODE = 'timed_speed_round'

#: The only word state a battery may draw from.
MASTERED = 'mastered'

#: Recognition levels. L1 (phonetic), L2 (definition match) and L3 (cloze) are
#: all "see/hear it, pick it" — the skill a speed round is for. L4+ ask the
#: learner to *produce* something, which does not compress into a few seconds.
RECOGNITION_LEVELS = (1, 2, 3)

MIN_BATTERY = 10
MAX_BATTERY = 20

#: Per-item clock. Long enough that a mastered word is comfortably retrievable,
#: short enough that hesitation shows.
DEFAULT_SECONDS_PER_ITEM = 8
MIN_SECONDS_PER_ITEM = 3
MAX_SECONDS_PER_ITEM = 30

#: A speed round updates FSRS but never family confidence — see the module
#: docstring. Named rather than merely absent so the attempt path can assert it.
UPDATES_FAMILY_CONFIDENCE = False

#: At most one item per sense: twenty items over eight words is a memory test
#: of the last ten seconds, not a fluency battery.
MAX_ITEMS_PER_SENSE = 1


@dataclass
class Battery:
    """One composed round, or the reason there is not one."""

    items: list = field(default_factory=list)
    seconds_per_item: int = DEFAULT_SECONDS_PER_ITEM
    mastered_sense_count: int = 0
    reason: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.items)

    def to_payload(self) -> dict:
        payload = {
            'mode': TYPE_CODE,
            'items': self.items,
            'seconds_per_item': self.seconds_per_item,
            'total_seconds': self.seconds_per_item * len(self.items),
            'mastered_sense_count': self.mastered_sense_count,
            'updates_family_confidence': UPDATES_FAMILY_CONFIDENCE,
        }
        if not self.available:
            payload['no_content_reason'] = self.reason or 'unknown'
        return payload


class SpeedRoundComposer:
    """Assembles a battery from already-generated items. No LLM, no writes."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()

    # ------------------------------------------------------------------

    def compose(
        self,
        user_id: str,
        language_id: int,
        size: int = MAX_BATTERY,
        seconds_per_item: int = DEFAULT_SECONDS_PER_ITEM,
    ) -> Battery:
        """Build a battery for this learner, or explain why there is none."""
        size = max(MIN_BATTERY, min(int(size or MAX_BATTERY), MAX_BATTERY))
        seconds_per_item = max(
            MIN_SECONDS_PER_ITEM,
            min(int(seconds_per_item or DEFAULT_SECONDS_PER_ITEM), MAX_SECONDS_PER_ITEM),
        )

        sense_ids = self.mastered_sense_ids(user_id, language_id)
        if not sense_ids:
            return Battery(
                seconds_per_item=seconds_per_item,
                reason='no_mastered_words',
            )

        candidates = self.recognition_items(sense_ids, language_id)
        if not candidates:
            return Battery(
                seconds_per_item=seconds_per_item,
                mastered_sense_count=len(sense_ids),
                reason='no_recognition_items_for_mastered_words',
            )

        items = self._select(candidates, size)
        if len(items) < MIN_BATTERY:
            # Better no battery than a three-item "round": the format only
            # produces fluency pressure at length.
            return Battery(
                seconds_per_item=seconds_per_item,
                mastered_sense_count=len(sense_ids),
                reason='too_few_items_for_a_battery',
            )

        return Battery(
            items=items,
            seconds_per_item=seconds_per_item,
            mastered_sense_count=len(sense_ids),
        )

    # ------------------------------------------------------------------

    def mastered_sense_ids(self, user_id: str, language_id: int) -> list[int]:
        """Senses this learner has mastered, in this language.

        The language filter goes through the embedded ``dim_word_senses`` join
        rather than a column on ``user_word_ladder``, which has no language of
        its own — a learner studying two languages would otherwise get a
        battery mixing both.
        """
        try:
            resp = (
                self.db.table('user_word_ladder')
                .select(
                    'sense_id, '
                    'dim_word_senses!inner(dim_vocabulary!inner(language_id))'
                )
                .eq('user_id', user_id)
                .eq('word_state', MASTERED)
                .eq('dim_word_senses.dim_vocabulary.language_id', language_id)
                .execute()
            )
            rows = resp.data or []
        except Exception as exc:
            logger.error(
                'mastered-sense lookup failed for user=%s lang=%s: %s',
                user_id, language_id, exc,
            )
            return []

        return [row['sense_id'] for row in rows if row.get('sense_id')]

    def has_enough_mastered(self, user_id: str, language_id: int) -> bool:
        """Cheap necessary-condition check for "could there be a battery?".

        One item per sense (:data:`MAX_ITEMS_PER_SENSE`) means a battery needs
        at least :data:`MIN_BATTERY` distinct mastered senses. That is
        necessary but not sufficient — those senses still need L1-L3 items — so
        this gates whether to *offer* a round, and is never a promise of one.
        The caller must still handle an unavailable battery.

        Exists so the session queue can decide whether to show the entry point
        without paying for a full compose (which also fetches every candidate
        item) on every session load.
        """
        return len(self.mastered_sense_ids(user_id, language_id)) >= MIN_BATTERY

    def recognition_items(self, sense_ids: list[int], language_id: int) -> list[dict]:
        """Active L1-L3 items for the given senses.

        Restricted to ladder-generated content (``word_asset_id IS NOT NULL``)
        so a battery never surfaces a legacy item that the judges never saw.
        """
        if not sense_ids:
            return []
        try:
            resp = (
                self.db.table('exercises')
                .select('id, exercise_type, content, ladder_level, word_sense_id, '
                        'complexity_tier')
                .eq('language_id', language_id)
                .eq('is_active', True)
                .not_.is_('word_asset_id', 'null')
                .in_('ladder_level', list(RECOGNITION_LEVELS))
                .in_('word_sense_id', sense_ids)
                .execute()
            )
            return resp.data or []
        except Exception as exc:
            logger.error('speed-round item lookup failed: %s', exc)
            return []

    # ------------------------------------------------------------------

    @staticmethod
    def _select(candidates: list[dict], size: int) -> list[dict]:
        """Pick at most one item per sense, shuffled, capped at ``size``.

        Grouping first and sampling within the group keeps the battery spread
        across the learner's mastered vocabulary rather than clustering on
        whichever senses happen to have the most generated items.
        """
        by_sense: dict = {}
        for item in candidates:
            by_sense.setdefault(item.get('word_sense_id'), []).append(item)

        picked: list[dict] = []
        for items in by_sense.values():
            picked.extend(random.sample(items, min(MAX_ITEMS_PER_SENSE, len(items))))

        random.shuffle(picked)
        return [_to_item(item) for item in picked[:size]]


def _to_item(row: dict) -> dict:
    """Project an exercise row into the battery's item shape.

    ``seconds_per_item`` is a property of the round, not of the item, so it is
    deliberately absent here — the player reads it off the payload.
    """
    return {
        'exercise_id': row.get('id'),
        'exercise_type': row.get('exercise_type'),
        'content': row.get('content'),
        'ladder_level': row.get('ladder_level'),
        'sense_id': row.get('word_sense_id'),
        'complexity_tier': row.get('complexity_tier'),
        'is_speed_round': True,
    }


_composer: SpeedRoundComposer | None = None


def get_speed_round_composer() -> SpeedRoundComposer:
    """Process-wide singleton, matching the other service factories."""
    global _composer
    if _composer is None:
        _composer = SpeedRoundComposer()
    return _composer
