# services/test_intro_service.py
"""First-time test-type explainer popup — "seen" tracking.

Backs the small "i" info button shown on every test-taking page: the first
time a user reaches a given test type they get an explainer modal shown
automatically; after that it's only reachable via the info button. Mirrors
users.has_seen_welcome (see services/auth_service.py mark_welcome_seen) but
keyed per test_type instead of being a single global flag — see
migrations/add_test_intro_seen.sql for why this is a table and not another
boolean column on users.

Valid test_type values (kept in sync with the frontend's TEST_TYPE_INTRO_KEYS
in static/js/test-intro.js): reading, listening, dictation, pinyin,
pitch_accent, classifier_drill, counter_drill.
"""

import logging
from typing import Set

from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)


def get_seen_test_types(user_id: str) -> Set[str]:
    """Return the set of test_type codes this user has already seen the intro for."""
    try:
        db = get_supabase_admin()
        resp = (
            db.table('user_test_intros_seen')
              .select('test_type')
              .eq('user_id', user_id)
              .execute()
        )
        return {row['test_type'] for row in (resp.data or [])}
    except Exception as e:
        logger.error('get_seen_test_types failed for user %s: %s', user_id, e)
        # Degrade to "nothing seen yet" rather than raising — worst case a
        # transient DB hiccup re-shows an explainer popup the user has
        # already seen, which is harmless, versus breaking the test page.
        return set()


def mark_test_intro_seen(user_id: str, test_type: str) -> dict:
    """Flag a test type's intro as seen for this user. Idempotent."""
    try:
        db = get_supabase_admin()
        db.table('user_test_intros_seen').upsert({
            'user_id': user_id,
            'test_type': test_type,
        }, on_conflict='user_id,test_type').execute()
        return {'success': True}
    except Exception as e:
        logger.error('mark_test_intro_seen failed for user %s type %s: %s', user_id, test_type, e)
        return {'success': False, 'error': 'Failed to record intro as seen'}
