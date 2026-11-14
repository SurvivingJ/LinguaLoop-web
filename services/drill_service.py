"""Recall drills: Chinese measure words and Japanese counters.

Both drills are a session RPC that deals items plus a submission that records
accuracy against a per-language sentinel test (ELO and a test_attempts row).
Submission goes through process_classifier_drill_submission for both: the RPC
is parameterised by test_id / test_type_id and has nothing classifier-specific.

Only the classifier drill tracks per-item mastery (there is no per-counter
mastery table); counter progress is carried by the sentinel test's ELO alone.
"""

import logging
from typing import Callable, Optional
from uuid import uuid4

from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)

ZH_LANGUAGE_ID = 1
JA_LANGUAGE_ID = 3

# A placeholder some imported classifiers carry instead of a meaning label.
_PLACEHOLDER_LABELS = {'(imported)', 'imported', ''}


def _clean_label(label: Optional[str]) -> Optional[str]:
    """The classifier's meaning label, or None for an import placeholder."""
    if label is None or label.strip().lower() in _PLACEHOLDER_LABELS:
        return None
    return label


def _attach_correct_pinyin(db, items: list[dict]) -> None:
    """Add ``correct_classifier_pinyin`` (parallel to correct_classifier_ids).

    The session RPC returns pinyin for the wrong options only, so the correct
    option was the one with no pinyin under it -- a giveaway. Best effort: on
    failure the field is empty and the player shows no pinyin on any option.
    """
    ids = sorted({cid for it in items for cid in (it.get('correct_classifier_ids') or [])})
    by_id: dict = {}
    if ids:
        try:
            rows = db.table('dim_classifiers').select('id, pinyin_display') \
                .in_('id', ids).execute().data or []
            by_id = {r['id']: r.get('pinyin_display') or '' for r in rows}
        except Exception as e:
            logger.warning("classifier pinyin lookup failed: %s", e)
    for it in items:
        it['correct_classifier_pinyin'] = [by_id.get(cid, '') for cid in (it.get('correct_classifier_ids') or [])]


def _classifier_item(r: dict) -> dict:
    return {
        'pair_id':                 r.get('out_pair_id'),
        'noun_lemma':              r.get('out_noun_lemma'),
        'noun_sense_id':           r.get('out_noun_sense_id'),
        'noun_gloss':              r.get('out_noun_gloss'),
        'noun_pronunciation':      r.get('out_noun_pronunciation'),
        'correct_classifier_ids':  r.get('out_correct_classifier_ids') or [],
        'correct_classifier_hanzi': r.get('out_correct_classifier_hanzi') or [],
        'distractor_ids':          r.get('out_distractor_ids') or [],
        'distractor_hanzi':        r.get('out_distractor_hanzi') or [],
        'distractor_pinyin':       r.get('out_distractor_pinyin') or [],
        'semantic_label':          _clean_label(r.get('out_semantic_label')),
        'distractor_group_label':  r.get('out_distractor_group_label'),
        'difficulty_tier':         r.get('out_difficulty_tier'),
        'level':                   r.get('out_level'),
        'classifier_id_primary':   r.get('out_classifier_id_primary'),
        'reverse_noun_options':    r.get('out_reverse_noun_options') or [],
        'cloze_sentence':          r.get('out_cloze_sentence'),
        'cloze_blanked':           r.get('out_cloze_blanked'),
    }


def _counter_item(r: dict) -> dict:
    # numeral_readings carries the euphonic changes (三本 is さんぼん, not
    # さんほん), which the Type mode shows the learner.
    return {
        'pair_id':                  r.get('out_pair_id'),
        'noun_lemma':               r.get('out_noun_lemma'),
        'noun_sense_id':            r.get('out_noun_sense_id'),
        'noun_gloss':               r.get('out_noun_gloss'),
        'noun_pronunciation':       r.get('out_noun_pronunciation'),
        'correct_counter_ids':      r.get('out_correct_counter_ids') or [],
        'correct_counter_text':     r.get('out_correct_counter_text') or [],
        'correct_counter_reading':  r.get('out_correct_counter_reading') or [],
        'distractor_ids':           r.get('out_distractor_ids') or [],
        'distractor_text':          r.get('out_distractor_text') or [],
        'distractor_reading':       r.get('out_distractor_reading') or [],
        'numeral_readings':         r.get('out_numeral_readings') or {},
        'semantic_label':           r.get('out_semantic_label'),
        'distractor_group_label':   r.get('out_distractor_group_label'),
        'difficulty_tier':          r.get('out_difficulty_tier'),
    }


class DrillService:
    """One drill: its language, sentinel test, session RPC and item shape."""

    def __init__(self, *, name: str, language_id: int, sentinel_slug: str,
                 session_rpc: str, to_item: Callable[[dict], dict],
                 finish_items: Optional[Callable] = None,
                 mastery_rpc: Optional[str] = None):
        self.name = name
        self.language_id = language_id
        self.sentinel_slug = sentinel_slug
        self.session_rpc = session_rpc
        self.to_item = to_item
        self.finish_items = finish_items
        self.mastery_rpc = mastery_rpc
        self._sentinel_test_id: Optional[str] = None

    def _fetch_sentinel_test_id(self, language_id: int) -> Optional[str]:
        """Look up (and cache) the sentinel test UUID."""
        if language_id != self.language_id:
            return None
        if self._sentinel_test_id is None:
            resp = (
                get_supabase_admin().table('tests')
                .select('id')
                .eq('slug', self.sentinel_slug)
                .single()
                .execute()
            )
            if not resp.data:
                logger.error("%s sentinel test not found for language_id=%s slug=%s",
                             self.name, language_id, self.sentinel_slug)
                return None
            self._sentinel_test_id = resp.data['id']
        return self._sentinel_test_id

    def get_session(self, user_id: str, language_id: int, count: int = 20) -> list[dict]:
        """A batch of drill items, ready for JSON. Empty list on error."""
        db = get_supabase_admin()
        try:
            rows = db.rpc(self.session_rpc, {
                'p_user_id': user_id,
                'p_language_id': language_id,
                'p_count': count,
            }).execute().data or []
        except Exception as e:
            logger.error("%s RPC failed: %s", self.session_rpc, e)
            return []

        items = [self.to_item(r) for r in rows]
        if self.finish_items:
            self.finish_items(db, items)
        return items

    def submit_session(
        self,
        user_id: str,
        language_id: int,
        test_type_id: int,
        correct_items: int,
        total_items: int,
        idempotency_key: Optional[str] = None,
        item_results: Optional[list[dict]] = None,
    ) -> Optional[dict]:
        """Persist a completed session and update ELO; None on hard failure.

        On a drill with a mastery RPC, each ``{classifier_id, is_correct}`` in
        ``item_results`` also updates the learner's per-item level and the
        result carries a ``mastery_updates`` list. Those updates are best
        effort: a failure does not fail the submission.
        """
        test_id = self._fetch_sentinel_test_id(language_id)
        if not test_id:
            logger.error("No sentinel test for language_id=%s", language_id)
            return None

        db = get_supabase_admin()
        try:
            result = db.rpc('process_classifier_drill_submission', {
                'p_user_id':         user_id,
                'p_test_id':         test_id,
                'p_language_id':     language_id,
                'p_test_type_id':    test_type_id,
                'p_correct_items':   int(correct_items),
                'p_total_items':     int(total_items),
                'p_was_free_test':   True,
                'p_idempotency_key': idempotency_key or str(uuid4()),
            }).execute().data or {}
        except Exception as e:
            # PostgREST surfaces a RAISE-with-JSON payload as an exception even
            # when the function succeeded.
            error_data = e.json() if hasattr(e, 'json') else (e.args[0] if e.args else {})
            if not (isinstance(error_data, dict) and error_data.get('success')):
                logger.error("%s submission failed: %s", self.name, error_data or e)
                return None
            result = error_data

        if self.mastery_rpc and isinstance(result, dict):
            result['mastery_updates'] = self._update_mastery(db, user_id, item_results or [])
        return result

    def _update_mastery(self, db, user_id: str, item_results: list[dict]) -> list[dict]:
        updates: list[dict] = []
        for item in item_results:
            cid = None
            try:
                cid = item.get('classifier_id')
                if cid is None:
                    continue
                resp = db.rpc(self.mastery_rpc, {
                    'p_user_id':       user_id,
                    'p_classifier_id': int(cid),
                    'p_is_correct':    bool(item.get('is_correct')),
                }).execute()
                if resp.data:
                    updates.append(resp.data)
            except Exception as exc:
                logger.warning("%s failed for cid=%s: %s", self.mastery_rpc, cid, exc)
        return updates


CLASSIFIER_DRILL = DrillService(
    name='classifier_drill',
    language_id=ZH_LANGUAGE_ID,
    sentinel_slug='__classifier_drill_zh',
    session_rpc='get_classifier_drill_session',
    to_item=_classifier_item,
    finish_items=_attach_correct_pinyin,
    mastery_rpc='update_classifier_mastery',
)

COUNTER_DRILL = DrillService(
    name='counter_drill',
    language_id=JA_LANGUAGE_ID,
    sentinel_slug='__counter_drill_ja',
    session_rpc='get_counter_drill_session',
    to_item=_counter_item,
)
