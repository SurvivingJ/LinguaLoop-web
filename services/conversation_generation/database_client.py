"""
Conversation Generation Database Client

Handles all database interactions for the conversation generation system.
Uses the existing SupabaseFactory for client management.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from ..supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)


# ============================================================
# Data Models
# ============================================================

@dataclass
class ConvDomain:
    """Represents a row from conversation_domains table."""
    id: int
    domain_name: str
    description: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    suitable_registers: List[str] = field(default_factory=list)
    suitable_relationship_types: List[str] = field(default_factory=list)
    parent_domain: Optional[str] = None
    category_id: Optional[int] = None


@dataclass
class Persona:
    """Represents a row from personas table."""
    id: int
    name: str
    language_id: int
    archetype: str
    system_prompt: str
    personality: Dict = field(default_factory=dict)
    age: Optional[int] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    occupation: Optional[str] = None
    register: Optional[str] = None
    expertise_domains: List[str] = field(default_factory=list)
    relationship_types: List[str] = field(default_factory=list)
    generation_method: str = 'template'


@dataclass
class PersonaPair:
    """Represents a row from persona_pairs table."""
    id: int
    persona_a_id: int
    persona_b_id: int
    compatibility_score: float = 0.50
    relationship_type: Optional[str] = None
    dynamic_label: Optional[str] = None
    suitable_domains: List[str] = field(default_factory=list)


@dataclass
class Scenario:
    """Represents a row from scenarios table."""
    id: int
    domain_id: int
    language_id: int
    title: str
    context_description: str
    goals: Dict = field(default_factory=dict)
    required_register: Optional[str] = None
    required_relationship_type: Optional[str] = None
    cefr_level: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    suitable_archetypes: List[str] = field(default_factory=list)
    cultural_note: Optional[str] = None
    generation_method: str = 'template'


@dataclass
class ConvQueueItem:
    """Represents a row from conversation_generation_queue table."""
    id: UUID
    scenario_id: int
    persona_pair_id: int
    language_id: int
    status_id: int
    created_at: datetime
    conversations_generated: int = 0
    error_log: Optional[str] = None


@dataclass
class ConvGenMetrics:
    """Metrics for a conversation generation run."""
    run_date: datetime
    queue_items_processed: int = 0
    conversations_generated: int = 0
    conversations_failed: int = 0
    exercises_generated: int = 0
    execution_time_seconds: Optional[int] = None
    error_message: Optional[str] = None


# ============================================================
# Database Client
# ============================================================

class ConversationDatabaseClient:
    """Supabase database client for conversation generation."""

    def __init__(self):
        self.client = get_supabase_admin()
        if not self.client:
            raise RuntimeError("Supabase admin client not available")

        # Caches
        self._domain_cache: Optional[Dict[int, ConvDomain]] = None
        self._persona_cache: Optional[Dict[int, Persona]] = None
        self._status_cache: Optional[Dict[str, int]] = None
        self._language_cache: Optional[Dict[int, Dict]] = None

    # ============================================================
    # QUEUE OPERATIONS
    # ============================================================

    def get_pending_queue_items(self, limit: int = 20) -> List[ConvQueueItem]:
        """Fetch pending items from conversation_generation_queue."""
        pending_status_id = self._get_status_id('pending')

        response = self.client.table('conversation_generation_queue') \
            .select('*') \
            .eq('status_id', pending_status_id) \
            .order('created_at') \
            .limit(limit) \
            .execute()

        if not response.data:
            logger.info("No pending conversation queue items found")
            return []

        items = [
            ConvQueueItem(
                id=UUID(row['id']),
                scenario_id=row['scenario_id'],
                persona_pair_id=row['persona_pair_id'],
                language_id=row['language_id'],
                status_id=row['status_id'],
                created_at=datetime.fromisoformat(
                    row['created_at'].replace('Z', '+00:00')
                ),
                conversations_generated=row.get('conversations_generated', 0) or 0,
                error_log=row.get('error_log'),
            )
            for row in response.data
        ]

        logger.info(f"Found {len(items)} pending conversation queue items")
        return items

    def update_queue_status(
        self,
        queue_id: UUID,
        status_code: str,
        conversations_generated: int = 0,
        error_log: Optional[str] = None,
    ) -> None:
        """Update queue item status."""
        status_id = self._get_status_id(status_code)
        update_data: Dict[str, Any] = {
            'status_id': status_id,
            'conversations_generated': conversations_generated,
            'processed_at': datetime.utcnow().isoformat(),
        }
        if error_log:
            update_data['error_log'] = error_log

        self.client.table('conversation_generation_queue') \
            .update(update_data) \
            .eq('id', str(queue_id)) \
            .execute()

    # ============================================================
    # DOMAIN OPERATIONS
    # ============================================================

    def get_domains(self, active_only: bool = True) -> List[ConvDomain]:
        """Fetch all conversation domains."""
        if self._domain_cache is not None:
            domains = list(self._domain_cache.values())
            return domains

        query = self.client.table('conversation_domains').select('*')
        if active_only:
            query = query.eq('is_active', True)
        response = query.execute()

        self._domain_cache = {}
        for row in response.data or []:
            domain = ConvDomain(
                id=row['id'],
                domain_name=row['domain_name'],
                description=row.get('description'),
                keywords=row.get('keywords', []),
                suitable_registers=row.get('suitable_registers', []),
                suitable_relationship_types=row.get('suitable_relationship_types', []),
                parent_domain=row.get('parent_domain'),
                category_id=row.get('category_id'),
            )
            self._domain_cache[domain.id] = domain

        return list(self._domain_cache.values())

    def get_domain(self, domain_id: int) -> Optional[ConvDomain]:
        """Get a single domain by ID."""
        if self._domain_cache is None:
            self.get_domains()
        return self._domain_cache.get(domain_id)

    # ============================================================
    # PERSONA OPERATIONS
    # ============================================================

    def get_personas_for_language(self, language_id: int) -> List[Persona]:
        """Fetch active personas for a given language."""
        response = self.client.table('personas') \
            .select('*') \
            .eq('language_id', language_id) \
            .eq('is_active', True) \
            .execute()

        return [self._row_to_persona(row) for row in response.data or []]

    def get_persona(self, persona_id: int) -> Optional[Persona]:
        """Get a single persona by ID."""
        if self._persona_cache and persona_id in self._persona_cache:
            return self._persona_cache[persona_id]

        response = self.client.table('personas') \
            .select('*') \
            .eq('id', persona_id) \
            .single() \
            .execute()

        if not response.data:
            return None

        persona = self._row_to_persona(response.data)
        if self._persona_cache is None:
            self._persona_cache = {}
        self._persona_cache[persona.id] = persona
        return persona

    def insert_persona(self, data: Dict) -> int:
        """Insert a new persona and return its ID."""
        response = self.client.table('personas') \
            .insert(data) \
            .execute()
        return response.data[0]['id']

    def insert_personas_batch(self, personas: List[Dict]) -> List[int]:
        """Batch insert personas and return list of IDs."""
        if not personas:
            return []
        response = self.client.table('personas') \
            .insert(personas) \
            .execute()
        return [row['id'] for row in response.data]

    def _row_to_persona(self, row: Dict) -> Persona:
        return Persona(
            id=row['id'],
            name=row['name'],
            language_id=row['language_id'],
            archetype=row['archetype'],
            system_prompt=row['system_prompt'],
            personality=row.get('personality', {}),
            age=row.get('age'),
            gender=row.get('gender'),
            nationality=row.get('nationality'),
            occupation=row.get('occupation'),
            register=row.get('register'),
            expertise_domains=row.get('expertise_domains', []),
            relationship_types=row.get('relationship_types', []),
            generation_method=row.get('generation_method', 'template'),
        )

    # ============================================================
    # PERSONA PAIR OPERATIONS
    # ============================================================

    def get_persona_pair(self, pair_id: int) -> Optional[PersonaPair]:
        """Get a persona pair by ID."""
        response = self.client.table('persona_pairs') \
            .select('*') \
            .eq('id', pair_id) \
            .single() \
            .execute()

        if not response.data:
            return None

        row = response.data
        return PersonaPair(
            id=row['id'],
            persona_a_id=row['persona_a_id'],
            persona_b_id=row['persona_b_id'],
            compatibility_score=float(row.get('compatibility_score', 0.50)),
            relationship_type=row.get('relationship_type'),
            dynamic_label=row.get('dynamic_label'),
            suitable_domains=row.get('suitable_domains', []),
        )

    def insert_persona_pair(self, data: Dict) -> int:
        """Insert a new persona pair and return its ID."""
        response = self.client.table('persona_pairs') \
            .insert(data) \
            .execute()
        return response.data[0]['id']

    def insert_persona_pairs_batch(self, pairs: List[Dict]) -> List[int]:
        """Batch insert persona pairs and return list of IDs."""
        if not pairs:
            return []
        response = self.client.table('persona_pairs') \
            .insert(pairs) \
            .execute()
        return [row['id'] for row in response.data]

    def update_persona_pair(self, pair_id: int, data: Dict) -> None:
        """Update fields on an existing persona pair."""
        self.client.table('persona_pairs') \
            .update(data) \
            .eq('id', pair_id) \
            .execute()

    def get_persona_pairs_for_language(self, language_id: int) -> List[Dict]:
        """Fetch all persona pairs where persona_a belongs to a language."""
        # Get persona IDs for this language
        personas_resp = self.client.table('personas') \
            .select('id') \
            .eq('language_id', language_id) \
            .eq('is_active', True) \
            .execute()

        if not personas_resp.data:
            return []

        persona_ids = [p['id'] for p in personas_resp.data]

        # Fetch pairs where persona_a_id is in our set
        pairs_resp = self.client.table('persona_pairs') \
            .select('*') \
            .in_('persona_a_id', persona_ids) \
            .execute()

        return pairs_resp.data or []

    def get_pairs_for_scenario(
        self,
        scenario: 'Scenario',
        language_id: int,
        limit: int = 5,
        min_score: float = 0.5,
    ) -> List[PersonaPair]:
        """
        Find best persona pairs for a scenario.

        Filters by language, min compatibility score, and optionally
        by relationship_type. Orders by compatibility_score DESC.
        """
        # Get persona IDs for this language
        personas_resp = self.client.table('personas') \
            .select('id') \
            .eq('language_id', language_id) \
            .eq('is_active', True) \
            .execute()

        if not personas_resp.data:
            return []

        persona_ids = [p['id'] for p in personas_resp.data]

        query = self.client.table('persona_pairs') \
            .select('*') \
            .in_('persona_a_id', persona_ids) \
            .gte('compatibility_score', min_score) \
            .order('compatibility_score', desc=True) \
            .limit(limit)

        # Filter by relationship type if scenario specifies one
        if scenario.required_relationship_type:
            query = query.eq('relationship_type', scenario.required_relationship_type)

        response = query.execute()

        return [
            PersonaPair(
                id=row['id'],
                persona_a_id=row['persona_a_id'],
                persona_b_id=row['persona_b_id'],
                compatibility_score=float(row.get('compatibility_score', 0.50)),
                relationship_type=row.get('relationship_type'),
                dynamic_label=row.get('dynamic_label'),
                suitable_domains=row.get('suitable_domains', []),
            )
            for row in response.data or []
        ]

    # ============================================================
    # SCENARIO OPERATIONS
    # ============================================================

    def get_scenario(self, scenario_id: int) -> Optional[Scenario]:
        """Get a scenario by ID."""
        response = self.client.table('scenarios') \
            .select('*') \
            .eq('id', scenario_id) \
            .single() \
            .execute()

        if not response.data:
            return None

        return self._row_to_scenario(response.data)

    def get_scenarios_for_domain(self, domain_id: int, language_id: int) -> List[Scenario]:
        """Fetch active scenarios for a domain and language."""
        response = self.client.table('scenarios') \
            .select('*') \
            .eq('domain_id', domain_id) \
            .eq('language_id', language_id) \
            .eq('is_active', True) \
            .execute()

        return [self._row_to_scenario(row) for row in response.data or []]

    def get_unvalidated_scenarios(
        self,
        domain_id: Optional[int] = None,
        language_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Scenario]:
        """Fetch scenarios where is_validated=False and is_active=True."""
        query = self.client.table('scenarios') \
            .select('*') \
            .eq('is_validated', False) \
            .eq('is_active', True)

        if domain_id is not None:
            query = query.eq('domain_id', domain_id)
        if language_id is not None:
            query = query.eq('language_id', language_id)

        response = query.order('domain_id').order('created_at').limit(limit).execute()
        return [self._row_to_scenario(row) for row in response.data or []]

    def get_scenario_counts(
        self, language_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Return per-domain scenario counts (total and validated).

        Returns list of dicts: {domain_id, domain_name, language_id, total, validated}
        """
        query = self.client.table('scenarios') \
            .select('domain_id, language_id, is_validated') \
            .eq('is_active', True)

        if language_id is not None:
            query = query.eq('language_id', language_id)

        response = query.execute()
        rows = response.data or []

        # Aggregate client-side
        counts: Dict[tuple, Dict] = {}
        for row in rows:
            key = (row['domain_id'], row['language_id'])
            if key not in counts:
                counts[key] = {'domain_id': row['domain_id'], 'language_id': row['language_id'], 'total': 0, 'validated': 0}
            counts[key]['total'] += 1
            if row['is_validated']:
                counts[key]['validated'] += 1

        # Enrich with domain names
        domains = {d.id: d.domain_name for d in self.get_domains()}
        for entry in counts.values():
            entry['domain_name'] = domains.get(entry['domain_id'], f"Domain {entry['domain_id']}")

        return sorted(counts.values(), key=lambda x: (x['language_id'], x['domain_id']))

    def insert_scenario(self, data: Dict) -> int:
        """Insert a new scenario and return its ID."""
        response = self.client.table('scenarios') \
            .insert(data) \
            .execute()
        return response.data[0]['id']

    def insert_scenarios_batch(self, scenarios: List[Dict]) -> List[int]:
        """Batch insert scenarios and return list of IDs."""
        if not scenarios:
            return []
        response = self.client.table('scenarios') \
            .insert(scenarios) \
            .execute()
        return [row['id'] for row in response.data]

    def validate_scenarios(self, scenario_ids: List[int]) -> int:
        """Mark scenarios as validated. Returns count updated."""
        if not scenario_ids:
            return 0
        for sid in scenario_ids:
            self.client.table('scenarios') \
                .update({'is_validated': True}) \
                .eq('id', sid) \
                .execute()
        return len(scenario_ids)

    def deactivate_scenarios(self, scenario_ids: List[int]) -> int:
        """Soft-delete scenarios by setting is_active=False. Returns count."""
        if not scenario_ids:
            return 0
        for sid in scenario_ids:
            self.client.table('scenarios') \
                .update({'is_active': False}) \
                .eq('id', sid) \
                .execute()
        return len(scenario_ids)

    def _row_to_scenario(self, row: Dict) -> Scenario:
        """Convert a database row dict to a Scenario dataclass."""
        return Scenario(
            id=row['id'],
            domain_id=row['domain_id'],
            language_id=row['language_id'],
            title=row['title'],
            context_description=row['context_description'],
            goals=row.get('goals', {}),
            required_register=row.get('required_register'),
            required_relationship_type=row.get('required_relationship_type'),
            cefr_level=row.get('cefr_level'),
            keywords=row.get('keywords', []),
            suitable_archetypes=row.get('suitable_archetypes', []),
            cultural_note=row.get('cultural_note'),
            generation_method=row.get('generation_method', 'template'),
        )

    # ============================================================
    # CONVERSATION OPERATIONS
    # ============================================================

    def insert_conversation(self, data: Dict) -> str:
        """Insert a generated conversation and return its UUID."""
        response = self.client.table('conversations') \
            .insert(data) \
            .execute()
        return response.data[0]['id']

    def update_conversation(self, conversation_id: str, data: Dict) -> None:
        """Update a conversation record."""
        self.client.table('conversations') \
            .update(data) \
            .eq('id', conversation_id) \
            .execute()

    def get_conversations_for_scenario(
        self, scenario_id: int, passed_qc_only: bool = False
    ) -> List[Dict]:
        """Fetch conversations for a scenario."""
        query = self.client.table('conversations') \
            .select('*') \
            .eq('scenario_id', scenario_id) \
            .eq('is_active', True)

        if passed_qc_only:
            query = query.eq('passed_qc', True)

        response = query.order('created_at', desc=True).execute()
        return response.data or []

    def get_validated_scenarios_for_domain(
        self, domain_id: int, language_id: int,
    ) -> List[Scenario]:
        """Fetch validated, active scenarios for a domain and language."""
        response = self.client.table('scenarios') \
            .select('*') \
            .eq('domain_id', domain_id) \
            .eq('language_id', language_id) \
            .eq('is_active', True) \
            .eq('is_validated', True) \
            .execute()
        return [self._row_to_scenario(row) for row in response.data or []]

    def conversation_exists(
        self, scenario_id: int, persona_pair_id: int,
    ) -> bool:
        """Check if a conversation already exists for this scenario + pair."""
        response = self.client.table('conversations') \
            .select('id') \
            .eq('scenario_id', scenario_id) \
            .eq('persona_pair_id', persona_pair_id) \
            .eq('is_active', True) \
            .limit(1) \
            .execute()
        return bool(response.data)

    def get_existing_conversation_keys(
        self, scenario_ids: list[int],
    ) -> set[tuple[int, int]]:
        """
        Bulk-fetch all existing (scenario_id, persona_pair_id) pairs
        for the given scenario IDs in a single query.

        Returns:
            Set of (scenario_id, persona_pair_id) tuples.
        """
        if not scenario_ids:
            return set()
        response = self.client.table('conversations') \
            .select('scenario_id, persona_pair_id') \
            .in_('scenario_id', scenario_ids) \
            .eq('is_active', True) \
            .execute()
        return {
            (row['scenario_id'], row['persona_pair_id'])
            for row in response.data or []
        }

    def get_conversation_count_by_domain(
        self, domain_id: int, language_id: int,
    ) -> int:
        """Count existing active conversations for a domain + language."""
        scenarios = self.get_scenarios_for_domain(domain_id, language_id)
        if not scenarios:
            return 0
        scenario_ids = [s.id for s in scenarios]
        response = self.client.table('conversations') \
            .select('id') \
            .in_('scenario_id', scenario_ids) \
            .eq('is_active', True) \
            .execute()
        return len(response.data or [])

    # ============================================================
    # LANGUAGE OPERATIONS
    # ============================================================

    def get_language_config(self, language_id: int) -> Dict:
        """Get language configuration from dim_languages."""
        if self._language_cache and language_id in self._language_cache:
            return self._language_cache[language_id]

        response = self.client.table('dim_languages') \
            .select('*') \
            .eq('id', language_id) \
            .single() \
            .execute()

        if not response.data:
            raise ValueError(f"Language ID {language_id} not found")

        if self._language_cache is None:
            self._language_cache = {}
        self._language_cache[language_id] = response.data
        return response.data

    def get_conversation_model(self, language_id: int) -> str:
        """Get the conversation model for a language."""
        lang = self.get_language_config(language_id)
        return lang.get('conversation_model') or 'google/gemini-2.0-flash-001'

    # ============================================================
    # PROMPT TEMPLATE OPERATIONS
    # ============================================================

    def get_prompt_template(self, task_name: str, language_id: int) -> str:
        """Fetch the latest version of a named prompt template for a language."""
        result = self.client.table('prompt_templates') \
            .select('template_text') \
            .eq('task_name', task_name) \
            .eq('language_id', language_id) \
            .order('version', desc=True) \
            .limit(1) \
            .execute()

        if not result.data:
            raise RuntimeError(
                f"No prompt template for task_name='{task_name}', language_id={language_id}"
            )
        return result.data[0]['template_text']

    # ============================================================
    # HELPERS
    # ============================================================

    def _get_status_id(self, status_code: str) -> int:
        """Look up a status_id from dim_status, with caching."""
        if self._status_cache is None:
            response = self.client.table('dim_status').select('id, status_code').execute()
            self._status_cache = {
                row['status_code']: row['id'] for row in response.data or []
            }

        status_id = self._status_cache.get(status_code)
        if status_id is None:
            raise ValueError(f"Unknown status_code: {status_code}")
        return status_id

    def clear_caches(self) -> None:
        """Reset all internal caches."""
        self._domain_cache = None
        self._persona_cache = None
        self._status_cache = None
        self._language_cache = None
