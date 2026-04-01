"""
Batch Scenario Generator

Generates conversation scenarios in LLM-powered batches (default 5 at a time)
for each domain x language combination. Uses the existing conversation generation
infrastructure (database client, LLM client, config).
"""

import json
import logging
import time
from typing import Dict, List, Optional, Set

from .categorical_maps import (
    SCENARIO_KEY_MAP,
    GOALS_KEY_MAP,
    build_tier_legend,
    localize_list,
    remap_numeric_keys,
    reverse_lookup,
)
from .config import conv_gen_config
from .database_client import ConversationDatabaseClient, Scenario, ConvDomain
from .llm_client import call_llm

logger = logging.getLogger(__name__)

# Language ID to display name mapping (matches dim_languages)
LANGUAGE_NAMES = {
    1: 'Mandarin Chinese',
    2: 'English',
    3: 'Japanese',
}

# Required keys in each scenario returned by the LLM
REQUIRED_SCENARIO_KEYS = {'title', 'context_description', 'goals'}


class ScenarioBatchGenerator:
    """Generates conversation scenarios in batches via LLM."""

    def __init__(self):
        self.db = ConversationDatabaseClient()

    # ================================================================
    # Public API
    # ================================================================

    def generate_for_domain(
        self,
        domain_id: int,
        language_id: int,
        target_count: int = 10,
        batch_size: int = 5,
    ) -> List[int]:
        """
        Generate scenarios for a single domain + language combination.

        Returns list of newly inserted scenario IDs.
        """
        domain = self.db.get_domain(domain_id)
        if not domain:
            raise ValueError(f"Domain ID {domain_id} not found")

        language_name = LANGUAGE_NAMES.get(language_id)
        if not language_name:
            lang_config = self.db.get_language_config(language_id)
            language_name = lang_config.get('language_name', f'Language {language_id}')

        # Collect existing titles for deduplication
        existing = self.db.get_scenarios_for_domain(domain_id, language_id)
        existing_titles: Set[str] = {s.title.strip().lower() for s in existing}
        remaining = target_count - len(existing)

        if remaining <= 0:
            logger.info(
                "Domain '%s' (lang=%d) already has %d scenarios (target=%d) - skipping",
                domain.domain_name, language_id, len(existing), target_count,
            )
            return []

        logger.info(
            "Generating %d scenarios for '%s' (%s) — %d already exist",
            remaining, domain.domain_name, language_name, len(existing),
        )

        tiers = conv_gen_config.target_complexity_tiers or ['T3']
        all_ids: List[int] = []
        batch_num = 0

        while remaining > 0:
            count = min(batch_size, remaining)
            complexity_tier = tiers[batch_num % len(tiers)]
            batch_num += 1

            try:
                batch = self._generate_batch(
                    domain=domain,
                    language_id=language_id,
                    language_name=language_name,
                    complexity_tier=complexity_tier,
                    existing_titles=list(existing_titles),
                    count=count,
                )
            except Exception as e:
                logger.error(
                    "Batch %d failed for '%s' (%s): %s",
                    batch_num, domain.domain_name, language_name, e,
                )
                continue

            ids = self._deduplicate_and_insert(
                scenarios=batch,
                domain_id=domain_id,
                language_id=language_id,
                existing_titles=existing_titles,
            )
            all_ids.extend(ids)
            remaining -= len(ids)

            logger.info(
                "  Batch %d: inserted %d scenarios (tier %s), %d remaining",
                batch_num, len(ids), complexity_tier, max(remaining, 0),
            )

        return all_ids

    def generate_all(
        self,
        language_ids: Optional[List[int]] = None,
        target_per_domain: int = 10,
        batch_size: int = 5,
    ) -> Dict:
        """
        Generate scenarios for all active domains across specified languages.

        Returns summary: {total_generated, by_language: {lang_id: count}}
        """
        language_ids = language_ids or [1, 2, 3]
        domains = self.db.get_domains(active_only=True)

        summary = {'total_generated': 0, 'by_language': {}}

        for lang_id in language_ids:
            lang_name = LANGUAGE_NAMES.get(lang_id, f'Language {lang_id}')
            logger.info("\n=== Generating scenarios: %s (language_id=%d) ===", lang_name, lang_id)
            lang_count = 0

            for domain in domains:
                ids = self.generate_for_domain(
                    domain_id=domain.id,
                    language_id=lang_id,
                    target_count=target_per_domain,
                    batch_size=batch_size,
                )
                lang_count += len(ids)

            summary['by_language'][lang_id] = lang_count
            summary['total_generated'] += lang_count
            logger.info("  %s total: %d new scenarios", lang_name, lang_count)

        return summary

    def get_coverage_report(
        self, language_ids: Optional[List[int]] = None
    ) -> Dict:
        """
        Return coverage report with per-domain counts.

        Returns: {
            by_language: {lang_id: {domains: [...], total, validated, ready}},
            overall_ready: bool
        }
        """
        language_ids = language_ids or [1, 2, 3]
        report: Dict = {'by_language': {}, 'overall_ready': True}
        min_validated = 5

        for lang_id in language_ids:
            counts = self.db.get_scenario_counts(language_id=lang_id)
            lang_ready = True
            domains_info = []

            for entry in counts:
                ready = entry['validated'] >= min_validated
                if not ready:
                    lang_ready = False
                domains_info.append({
                    'domain_id': entry['domain_id'],
                    'domain_name': entry['domain_name'],
                    'total': entry['total'],
                    'validated': entry['validated'],
                    'ready': ready,
                })

            total = sum(d['total'] for d in domains_info)
            validated = sum(d['validated'] for d in domains_info)

            report['by_language'][lang_id] = {
                'language_name': LANGUAGE_NAMES.get(lang_id, f'Language {lang_id}'),
                'domains': domains_info,
                'total': total,
                'validated': validated,
                'ready': lang_ready,
            }

            if not lang_ready:
                report['overall_ready'] = False

        return report

    def get_validation_candidates(
        self,
        domain_id: Optional[int] = None,
        language_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Scenario]:
        """Fetch unvalidated scenarios for human review."""
        return self.db.get_unvalidated_scenarios(
            domain_id=domain_id,
            language_id=language_id,
            limit=limit,
        )

    # ================================================================
    # Private Methods
    # ================================================================

    def _generate_batch(
        self,
        domain: ConvDomain,
        language_id: int,
        language_name: str,
        complexity_tier: str,
        existing_titles: List[str],
        count: int = 5,
    ) -> List[Dict]:
        """
        Call LLM to generate a batch of scenarios.

        Returns list of validated scenario dicts.
        """
        try:
            template = self.db.get_prompt_template('scenario_batch_generation', language_id)
        except RuntimeError:
            # Fall back to the hardcoded prompt if no template exists yet
            logger.warning("No prompt template for scenario_batch_generation (lang=%d), using fallback", language_id)
            template = self._fallback_prompt_template()

        # Localize categorical values for prompt injection
        localized_registers = (
            localize_list('register', domain.suitable_registers, language_id)
            if domain.suitable_registers else 'any'
        )
        localized_relationships = (
            localize_list('relationship_type', domain.suitable_relationship_types, language_id)
            if domain.suitable_relationship_types else 'any'
        )

        prompt = template.format(
            count=count,
            domain_name=domain.domain_name,
            domain_description=domain.description or domain.domain_name,
            domain_keywords=', '.join(domain.keywords) if domain.keywords else 'general',
            suitable_registers=localized_registers,
            suitable_relationship_types=localized_relationships,
            complexity_tier=complexity_tier,
            tier_legend=build_tier_legend(language_id),
            language_name=language_name,
            existing_titles=json.dumps(existing_titles[:50]),  # Cap to avoid prompt bloat
        )

        last_error = None
        for attempt in range(conv_gen_config.max_retries):
            try:
                result = call_llm(
                    prompt=prompt,
                    response_format='json',
                    temperature=0.85,
                )

                scenarios = self._parse_and_validate(result, language_id)
                return scenarios

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                last_error = e
                logger.warning(
                    "Batch attempt %d/%d failed: %s",
                    attempt + 1, conv_gen_config.max_retries, e,
                )
                if attempt < conv_gen_config.max_retries - 1:
                    time.sleep(conv_gen_config.retry_delay)

        raise RuntimeError(f"All {conv_gen_config.max_retries} attempts failed: {last_error}")

    def _parse_and_validate(self, result, language_id: int = 2) -> List[Dict]:
        """Validate LLM response structure and extract scenario list.

        Handles both numeric-key output (new prompts) and English-key output
        (legacy prompts / backward compatibility).
        """
        if isinstance(result, list):
            scenarios = result
        elif isinstance(result, dict):
            scenarios = result.get('scenarios', [])
            if not scenarios:
                # Try the result itself as a single scenario
                if 'title' in result or '1' in result:
                    scenarios = [result]
                else:
                    raise ValueError(f"Response missing 'scenarios' key. Keys: {list(result.keys())}")
        else:
            raise ValueError(f"Unexpected response type: {type(result)}")

        validated = []
        for i, s in enumerate(scenarios):
            # Detect numeric keys and remap to English DB columns
            if '1' in s and 'title' not in s:
                s = remap_numeric_keys(s, SCENARIO_KEY_MAP)
                # Remap goals sub-object if also numeric
                goals = s.get('goals', {})
                if isinstance(goals, dict) and '1' in goals and 'persona_a' not in goals:
                    s['goals'] = remap_numeric_keys(goals, GOALS_KEY_MAP)

            # Reverse-lookup localized categorical values to English enums
            reg = s.get('required_register')
            if reg:
                mapped = reverse_lookup('register', str(reg), language_id)
                s['required_register'] = mapped or reg

            rel = s.get('required_relationship_type')
            if rel:
                mapped = reverse_lookup('relationship_type', str(rel), language_id)
                s['required_relationship_type'] = mapped or rel

            missing = REQUIRED_SCENARIO_KEYS - set(s.keys())
            if missing:
                logger.warning("Scenario %d missing keys %s — skipping", i, missing)
                continue

            # Validate goals structure
            goals = s.get('goals', {})
            if isinstance(goals, dict) and 'persona_a' in goals and 'persona_b' in goals:
                pass  # Good format
            elif 'goal_persona_a' in s and 'goal_persona_b' in s:
                # Handle alternate format from LLM
                s['goals'] = {
                    'persona_a': s.pop('goal_persona_a'),
                    'persona_b': s.pop('goal_persona_b'),
                }
            else:
                logger.warning("Scenario %d ('%s') has invalid goals structure — skipping", i, s.get('title', '?'))
                continue

            validated.append(s)

        if not validated:
            raise ValueError("No valid scenarios in LLM response")

        return validated

    def _deduplicate_and_insert(
        self,
        scenarios: List[Dict],
        domain_id: int,
        language_id: int,
        existing_titles: Set[str],
    ) -> List[int]:
        """Filter duplicates by title, insert remaining, update existing_titles set."""
        to_insert = []

        for s in scenarios:
            title_key = s['title'].strip().lower()
            if title_key in existing_titles:
                logger.debug("Skipping duplicate title: %s", s['title'])
                continue

            row = {
                'domain_id': domain_id,
                'language_id': language_id,
                'title': s['title'].strip(),
                'context_description': s['context_description'].strip(),
                'goals': s['goals'],
                'required_register': s.get('required_register'),
                'required_relationship_type': s.get('required_relationship_type'),
                'complexity_tier': s.get('complexity_tier'),
                'keywords': s.get('keywords', []),
                'suitable_archetypes': s.get('suitable_archetypes', []),
                'cultural_note': s.get('cultural_note'),
                'generation_method': 'llm',
                'is_validated': False,
                'is_active': True,
            }
            to_insert.append(row)
            existing_titles.add(title_key)

        if not to_insert:
            return []

        ids = self.db.insert_scenarios_batch(to_insert)
        logger.info("Inserted %d scenarios for domain_id=%d, language_id=%d", len(ids), domain_id, language_id)
        return ids

    @staticmethod
    def _fallback_prompt_template() -> str:
        """Hardcoded fallback prompt if no DB template exists yet.

        Uses numeric JSON keys to prevent English leaking into target-language output.
        """
        return """You are designing conversation scenarios for a language learning application.
The target language for ALL generated content is: {language_name}.

Generate {count} UNIQUE and REALISTIC conversation scenarios for:
- Domain: {domain_name} — {domain_description}
- Domain keywords: {domain_keywords}
- Language/Culture: {language_name}
- Target complexity: {complexity_tier}
- Suitable registers: {suitable_registers}
- Suitable relationship types: {suitable_relationship_types}

Complexity Tier Legend:
{tier_legend}

Each scenario must:
1. Be culturally authentic for {language_name} speakers — NOT a translated Western situation
2. Give each speaker a GENUINELY DIFFERENT goal, perspective, or emotional position
3. Be specific enough that the speakers have something real to disagree about or explore
4. Be able to sustain 10-14 turns of natural dialogue without running out of content
5. Contain vocabulary and cultural references natural to this domain

CRITICAL: ALL string values MUST be in {language_name}. Do NOT include English words in the JSON output (except for tier codes and archetype codes).

IMPORTANT: Do NOT repeat any of these existing scenario titles:
{existing_titles}

OUTPUT FORMAT: Use STRICTLY NUMERIC KEYS according to this legend.

Key Legend:
"1" = Title (short descriptive title in {language_name})
"2" = Context Description (2-3 sentences setting the scene in {language_name})
"3" = Goals (object with "1" = speaker A goal, "2" = speaker B goal, both in {language_name})
"4" = Keywords (array of 5-8 {language_name} vocabulary words)
"5" = Suitable Archetypes (array of 2 archetype codes from the list below)
"6" = Required Register (choose exactly one from: {suitable_registers})
"7" = Required Relationship Type (choose exactly one from: {suitable_relationship_types})
"8" = Complexity Tier (choose exactly one: T1, T2, T3, T4, T5, T6)
"9" = Cultural Note (one sentence in {language_name} noting any culturally specific element)

Return ONLY valid JSON with this exact structure:
{{
  "scenarios": [
    {{
      "1": "...",
      "2": "...",
      "3": {{"1": "...", "2": "..."}},
      "4": ["...", "...", "..."],
      "5": ["archetype_a", "archetype_b"],
      "6": "...",
      "7": "...",
      "8": "{complexity_tier}",
      "9": "..."
    }}
  ]
}}

Valid archetypes: protective_parent, rebellious_teen, supportive_sibling, wise_grandparent, nagging_relative, new_parent, hopeless_romantic, commitment_phobe, long_term_partner, jealous_partner, supportive_spouse, new_dater, loyal_best_friend, party_animal, wise_counselor, competitive_friend, ambitious_climber, burnt_out_worker, inspiring_mentor, strict_boss, new_employee, patient_service_worker, demanding_customer, helpful_neighbor, gossip_enthusiast, social_media_addict, community_organizer

Make every scenario GENUINELY DIFFERENT from the others. Avoid generic or cliched situations."""
