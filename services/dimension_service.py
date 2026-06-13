# services/dimension_service.py
"""
Dimension Service - Cached lookups for language and test-type dimension tables.
Extracted from test_service.py for separation of concerns.
"""

import logging
from typing import Optional, Dict, List, Tuple

from config import Config
from services.supabase_factory import get_supabase

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS - Re-exported from Config (single source of truth)
# ============================================================================

VALID_LANGUAGE_IDS = Config.VALID_LANGUAGE_IDS
LANGUAGE_ID_TO_NAME = Config.LANGUAGE_ID_TO_NAME
LANGUAGE_NAME_TO_ID = {v: k for k, v in LANGUAGE_ID_TO_NAME.items()}


# ============================================================================
# DIMENSION TABLE HELPERS
# ============================================================================

class DimensionService:
    """Handles dimension table lookups with caching."""

    _language_cache: Dict[str, int] = {}
    _test_type_cache: Dict[str, int] = {}
    _languages_metadata: List[Dict] = []
    _test_types_metadata: List[Dict] = []
    _exercise_capabilities: List[Dict] = []
    _initialized: bool = False

    @classmethod
    def initialize(cls, supabase_client=None) -> None:
        """Pre-load dimension tables into cache."""
        client = supabase_client or get_supabase()
        if not client:
            return

        try:
            # Cache languages with full metadata
            langs = client.table('dim_languages')\
                .select('id, language_code, language_name, native_name')\
                .eq('is_active', True)\
                .order('display_order')\
                .execute()
            cls._languages_metadata = langs.data or []
            cls._language_cache = {r['language_code']: r['id'] for r in cls._languages_metadata}

            # Cache test types with full metadata
            types = client.table('dim_test_types')\
                .select('id, type_code, type_name, requires_audio')\
                .eq('is_active', True)\
                .order('display_order')\
                .execute()
            cls._test_types_metadata = types.data or []
            cls._test_type_cache = {r['type_code']: r['id'] for r in cls._test_types_metadata}

            # Cache the exercise capability matrix (dim_exercise_capabilities,
            # TASK-504). Isolated in its own try so a missing/empty table never
            # blocks core dimension init — routing falls back to the in-code
            # CAPABILITY_MATRIX mirror in services.vocabulary_ladder.config.
            try:
                caps = client.table('dim_exercise_capabilities')\
                    .select('language_id, type_code, pos_classes, ladder_level, '
                            'generator, requires, judge_key, is_enabled')\
                    .execute()
                cls._exercise_capabilities = caps.data or []
            except Exception as cap_err:
                logger.error(f"Failed to cache dim_exercise_capabilities: {cap_err}")
                cls._exercise_capabilities = []

            cls._initialized = True
            logger.info(
                f"DimensionService initialized: {len(cls._language_cache)} languages, "
                f"{len(cls._test_type_cache)} test types, "
                f"{len(cls._exercise_capabilities)} exercise capabilities"
            )

        except Exception as e:
            logger.error(f"Failed to initialize DimensionService: {e}")

    @classmethod
    def get_all_languages(cls) -> List[Dict]:
        """Return cached language metadata for /api/metadata endpoint."""
        return cls._languages_metadata

    @classmethod
    def get_exercise_capabilities(cls, language_id: Optional[int] = None) -> List[Dict]:
        """Return cached dim_exercise_capabilities rows (TASK-504 routing matrix).

        With `language_id`, returns only that language's rows. The DB copy is the
        runtime source of truth; the in-code mirror in
        services.vocabulary_ladder.config (CAPABILITY_MATRIX) is the seed +
        offline routing source and must stay in sync with it.
        """
        if language_id is None:
            return cls._exercise_capabilities
        return [r for r in cls._exercise_capabilities if r.get('language_id') == language_id]

    @classmethod
    def get_all_test_types(cls, supabase_client=None) -> List[Dict] | Tuple[Dict[str, int], Dict[int, str]]:
        """Return cached test type metadata.

        When called with no arguments and metadata is available, returns the
        list of test-type dicts (for /api/metadata).  When the cache contains
        only code→id mappings (populated via DB query fallback), returns a
        (code_to_id, id_to_code) tuple instead.
        """
        # Primary path: return metadata list
        if cls._test_types_metadata:
            return cls._test_types_metadata

        # Fallback: return mapping tuple (legacy callers)
        if cls._test_type_cache:
            id_to_code = {v: k for k, v in cls._test_type_cache.items()}
            return cls._test_type_cache.copy(), id_to_code

        client = supabase_client or get_supabase()
        if not client:
            return []

        try:
            result = client.table('dim_test_types')\
                .select('id, type_code')\
                .eq('is_active', True)\
                .execute()

            code_to_id = {row['type_code']: row['id'] for row in result.data}
            id_to_code = {row['id']: row['type_code'] for row in result.data}
            cls._test_type_cache = code_to_id
            return code_to_id, id_to_code
        except Exception as e:
            logger.error(f"Error fetching test types: {e}")
            return []

    @classmethod
    def get_language_id(cls, language_code: str, supabase_client=None) -> Optional[int]:
        """Get language ID from code (cn, en, jp)."""
        if not language_code:
            return None

        code = language_code.lower()

        # Check cache first
        if code in cls._language_cache:
            return cls._language_cache[code]

        # Query database if not cached
        client = supabase_client or get_supabase()
        if not client:
            return None

        try:
            result = client.table('dim_languages')\
                .select('id')\
                .eq('language_code', code)\
                .eq('is_active', True)\
                .limit(1)\
                .execute()
            if result.data:
                cls._language_cache[code] = result.data[0]['id']
                return result.data[0]['id']
        except Exception as e:
            logger.error(f"Error fetching language ID for '{code}': {e}")

        return None

    @classmethod
    def get_language_code(cls, language_id: int) -> Optional[str]:
        """Reverse lookup: language_id → language_code (e.g. 1 → 'zh')."""
        if language_id is None:
            return None
        for row in cls._languages_metadata:
            if row.get('id') == language_id:
                return row.get('language_code')
        return None

    @classmethod
    def get_test_type_id(cls, type_code: str, supabase_client=None) -> Optional[int]:
        """Get test type ID from code (listening, reading, dictation)."""
        if not type_code:
            return None

        code = type_code.lower()

        # Check cache first
        if code in cls._test_type_cache:
            return cls._test_type_cache[code]

        # Query database if not cached
        client = supabase_client or get_supabase()
        if not client:
            return None

        try:
            result = client.table('dim_test_types')\
                .select('id')\
                .eq('type_code', code)\
                .eq('is_active', True)\
                .limit(1)\
                .execute()
            if result.data:
                cls._test_type_cache[code] = result.data[0]['id']
                return result.data[0]['id']
        except Exception as e:
            logger.error(f"Error fetching test type ID for '{code}': {e}")

        return None


def parse_language_id(language_id_input) -> Optional[int]:
    """Parse and validate language_id - only accepts integer IDs."""
    if language_id_input is None:
        return None

    try:
        lang_id = int(language_id_input)
        return lang_id if lang_id in VALID_LANGUAGE_IDS else None
    except (ValueError, TypeError):
        return None
