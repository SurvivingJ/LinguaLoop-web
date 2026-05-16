# services/listening_lab_service.py
"""
Listening Lab Service — speed-graded listening comprehension.

Wraps the listening_lab_* RPCs and provides the read paths the Flask
blueprint needs (list, recommended, lookup-by-slug, active-session).

Token-economy integration is intentionally out of scope for this iteration —
the start_session RPC records `tokens_consumed` informationally only; no
wallet deduction is performed here.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import uuid4

from services.supabase_factory import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


class ListeningLabService:
    """Singleton service for Listening Lab operations."""

    def __init__(self, supabase_client=None, supabase_admin=None):
        self._client = supabase_client
        self._admin = supabase_admin

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase()
        return self._client

    @property
    def admin(self):
        if self._admin is None:
            self._admin = get_supabase_admin()
        return self._admin

    # -------------------------------------------------------------------------
    # PASSAGE LOOKUP
    # -------------------------------------------------------------------------

    def list_passages(
        self, language_id: int, difficulty: Optional[int] = None, limit: int = 50
    ) -> List[Dict]:
        """All active Lab-enrolled passages, optionally filtered by difficulty."""
        try:
            query = (
                self.admin.table('listening_lab_passages')
                .select(
                    'id, test_id, language_id, voice_id, pool_size, '
                    'enrolled_at, tests!inner(slug, title, difficulty, transcript)'
                )
                .eq('is_active', True)
                .eq('language_id', int(language_id))
            )

            if difficulty is not None:
                query = query.eq('tests.difficulty', int(difficulty))

            result = query.order('enrolled_at', desc=True).limit(limit).execute()
            return [self._flatten_passage(row) for row in (result.data or [])]

        except Exception as e:
            logger.error(f"Error listing listening lab passages: {e}")
            return []

    def get_passage_by_slug(self, slug: str) -> Optional[Dict]:
        """Resolve a test slug to its active Lab passage row + test metadata."""
        if not slug:
            return None

        try:
            result = (
                self.admin.table('listening_lab_passages')
                .select(
                    'id, test_id, language_id, voice_id, pool_size, is_active, '
                    'audio_url_075, audio_url_090, audio_url_100, audio_url_115, '
                    'tests!inner(slug, title, difficulty, transcript, language_id)'
                )
                .eq('tests.slug', slug)
                .eq('is_active', True)
                .limit(1)
                .execute()
            )

            if not result.data:
                return None

            return self._flatten_passage(result.data[0])

        except Exception as e:
            logger.error(f"Error fetching listening lab passage by slug '{slug}': {e}")
            return None

    def get_recommended(self, user_id: str, language_id: int) -> List[Dict]:
        """ELO-matched passage recommendations for the user."""
        try:
            result = self.admin.rpc(
                'get_listening_lab_recommendations',
                {
                    'p_user_id': user_id,
                    'p_language_id': int(language_id),
                },
            ).execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Error fetching listening lab recommendations: {e}")
            return []

    # -------------------------------------------------------------------------
    # SESSION LIFECYCLE
    # -------------------------------------------------------------------------

    def get_active_session(self, user_id: str, passage_id: str) -> Optional[Dict]:
        """Returns the user's open session for this passage, if any."""
        try:
            result = (
                self.admin.table('listening_lab_sessions')
                .select('*')
                .eq('user_id', user_id)
                .eq('passage_id', passage_id)
                .is_('completed_at', 'null')
                .is_('abandoned_at', 'null')
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Error fetching active session: {e}")
            return None

    def start_session(self, user_id: str, passage_id: str) -> Dict:
        """
        Start (or resume) a Listening Lab session.

        Idempotent at the DB level: an existing active session is returned
        instead of inserted, so a double-click on Start is safe.
        """
        try:
            result = self.admin.rpc(
                'start_listening_lab_session',
                {
                    'p_user_id': user_id,
                    'p_passage_id': passage_id,
                },
            ).execute()

            payload = result.data
            if isinstance(payload, list) and payload:
                payload = payload[0]

            if not payload or not payload.get('success'):
                error_msg = (payload or {}).get('error', 'Unknown error')
                logger.error(f"start_listening_lab_session failed: {error_msg}")
                return {'success': False, 'error': error_msg}

            return payload

        except Exception as e:
            logger.error(f"Error starting listening lab session: {e}")
            raise

    def submit_tier(
        self,
        user_id: str,
        session_id: str,
        tier: int,
        responses: List[Dict],
        idempotency_key: Optional[str] = None,
    ) -> Dict:
        """
        Submit answers for the current tier.

        Returns the RPC payload:
          - passed=True, completed=False  → advance, with next-tier payload
          - passed=False                  → retry with fresh questions
          - passed=True, completed=True   → final ELO result attached
        """
        try:
            params = {
                'p_user_id': user_id,
                'p_session_id': session_id,
                'p_tier': int(tier),
                'p_responses': responses,
                'p_idempotency_key': idempotency_key or str(uuid4()),
            }

            result = self.admin.rpc('submit_listening_lab_tier', params).execute()

            payload = result.data
            if isinstance(payload, list) and payload:
                payload = payload[0]

            if not payload or not payload.get('success'):
                error_msg = (payload or {}).get('error', 'Unknown error')
                logger.error(f"submit_listening_lab_tier failed: {error_msg}")
                return {'success': False, 'error': error_msg}

            return payload

        except Exception as e:
            logger.error(f"Error submitting listening lab tier {tier}: {e}")
            raise

    def abandon_session(self, user_id: str, session_id: str) -> bool:
        """Mark a session abandoned. No refunds, no ELO."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            result = (
                self.admin.table('listening_lab_sessions')
                .update({'abandoned_at': now, 'updated_at': now})
                .eq('id', session_id)
                .eq('user_id', user_id)
                .is_('completed_at', 'null')
                .is_('abandoned_at', 'null')
                .execute()
            )
            return bool(result.data)

        except Exception as e:
            logger.error(f"Error abandoning session {session_id}: {e}")
            return False

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @staticmethod
    def _flatten_passage(row: Dict) -> Dict:
        """Flatten the embedded tests row into the passage dict."""
        test = row.pop('tests', None) or {}
        # When Supabase returns a list (m2m), pick the first; for !inner it's a dict.
        if isinstance(test, list):
            test = test[0] if test else {}

        row['test_slug'] = test.get('slug')
        row['title'] = test.get('title')
        row['difficulty'] = test.get('difficulty')
        if 'transcript' in test:
            row['transcript'] = test['transcript']
        return row


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_listening_lab_service_instance: Optional[ListeningLabService] = None


def get_listening_lab_service() -> ListeningLabService:
    """Get the singleton ListeningLabService instance."""
    global _listening_lab_service_instance
    if _listening_lab_service_instance is None:
        _listening_lab_service_instance = ListeningLabService()
    return _listening_lab_service_instance
