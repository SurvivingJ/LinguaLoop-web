"""
Persona Pairing Engine

Archetype-aware compatibility scoring, relationship derivation,
and domain matching for persona pairs. Pure functions — no LLM dependency.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# DYNAMIC COMPATIBILITY MATRIX
# =============================================================================
# Keyed by frozenset({archetype_a, archetype_b}) for order-independent lookup.
# Unlisted pairs fall through to heuristic scoring.

DYNAMIC_COMPATIBILITY: dict[frozenset, dict] = {
    # --- Family ---
    frozenset({'protective_parent', 'rebellious_teen'}):     {'score': 0.92, 'dynamic_label': 'parent-teen-conflict'},
    frozenset({'protective_parent', 'supportive_sibling'}):  {'score': 0.85, 'dynamic_label': 'parent-sibling-mediation'},
    frozenset({'protective_parent', 'new_parent'}):          {'score': 0.88, 'dynamic_label': 'parent-advising-new-parent'},
    frozenset({'protective_parent', 'new_dater'}):           {'score': 0.88, 'dynamic_label': 'parent-meeting-childs-date'},
    frozenset({'wise_grandparent', 'rebellious_teen'}):      {'score': 0.88, 'dynamic_label': 'grandparent-guidance'},
    frozenset({'wise_grandparent', 'new_parent'}):           {'score': 0.90, 'dynamic_label': 'generational-parenting-advice'},
    frozenset({'wise_grandparent', 'protective_parent'}):    {'score': 0.86, 'dynamic_label': 'elder-family-wisdom'},
    frozenset({'nagging_relative', 'rebellious_teen'}):      {'score': 0.87, 'dynamic_label': 'family-friction'},
    frozenset({'nagging_relative', 'new_parent'}):           {'score': 0.86, 'dynamic_label': 'unwanted-parenting-advice'},
    frozenset({'nagging_relative', 'supportive_spouse'}):    {'score': 0.84, 'dynamic_label': 'in-law-tension'},
    frozenset({'nagging_relative', 'long_term_partner'}):    {'score': 0.83, 'dynamic_label': 'in-law-meddling'},
    frozenset({'supportive_sibling', 'rebellious_teen'}):    {'score': 0.90, 'dynamic_label': 'sibling-support'},
    frozenset({'supportive_sibling', 'new_parent'}):         {'score': 0.84, 'dynamic_label': 'sibling-helping-new-parent'},

    # --- Romantic ---
    frozenset({'hopeless_romantic', 'commitment_phobe'}):    {'score': 0.90, 'dynamic_label': 'romantic-tension'},
    frozenset({'hopeless_romantic', 'new_dater'}):           {'score': 0.87, 'dynamic_label': 'early-romance'},
    frozenset({'hopeless_romantic', 'hopeless_romantic'}):   {'score': 0.82, 'dynamic_label': 'mutual-romantics'},
    frozenset({'long_term_partner', 'long_term_partner'}):   {'score': 0.95, 'dynamic_label': 'established-couple'},
    frozenset({'jealous_partner', 'supportive_spouse'}):     {'score': 0.92, 'dynamic_label': 'jealousy-in-relationship'},
    frozenset({'jealous_partner', 'commitment_phobe'}):      {'score': 0.88, 'dynamic_label': 'trust-issues'},
    frozenset({'jealous_partner', 'long_term_partner'}):     {'score': 0.90, 'dynamic_label': 'jealousy-in-long-relationship'},
    frozenset({'new_dater', 'new_dater'}):                   {'score': 0.85, 'dynamic_label': 'first-date'},
    frozenset({'supportive_spouse', 'long_term_partner'}):   {'score': 0.93, 'dynamic_label': 'stable-partnership'},
    frozenset({'supportive_spouse', 'supportive_spouse'}):   {'score': 0.90, 'dynamic_label': 'supportive-couple'},
    frozenset({'commitment_phobe', 'new_dater'}):            {'score': 0.86, 'dynamic_label': 'dating-reluctance'},

    # --- Friendship ---
    frozenset({'loyal_best_friend', 'loyal_best_friend'}):   {'score': 0.95, 'dynamic_label': 'best-friends'},
    frozenset({'loyal_best_friend', 'party_animal'}):        {'score': 0.85, 'dynamic_label': 'friend-encouraging-night-out'},
    frozenset({'loyal_best_friend', 'wise_counselor'}):      {'score': 0.88, 'dynamic_label': 'friend-seeking-advice'},
    frozenset({'competitive_friend', 'competitive_friend'}): {'score': 0.90, 'dynamic_label': 'competitive-peers'},
    frozenset({'party_animal', 'party_animal'}):             {'score': 0.82, 'dynamic_label': 'party-friends'},
    frozenset({'wise_counselor', 'competitive_friend'}):     {'score': 0.80, 'dynamic_label': 'advice-for-competitive-friend'},
    frozenset({'loyal_best_friend', 'competitive_friend'}):  {'score': 0.83, 'dynamic_label': 'friendly-rivalry'},

    # --- Professional ---
    frozenset({'strict_boss', 'new_employee'}):              {'score': 0.92, 'dynamic_label': 'authority-newcomer'},
    frozenset({'inspiring_mentor', 'new_employee'}):         {'score': 0.95, 'dynamic_label': 'mentor-mentee'},
    frozenset({'inspiring_mentor', 'ambitious_climber'}):    {'score': 0.90, 'dynamic_label': 'mentor-ambitious-protege'},
    frozenset({'strict_boss', 'burnt_out_worker'}):          {'score': 0.88, 'dynamic_label': 'boss-struggling-employee'},
    frozenset({'ambitious_climber', 'burnt_out_worker'}):    {'score': 0.85, 'dynamic_label': 'contrasting-work-attitudes'},
    frozenset({'strict_boss', 'ambitious_climber'}):         {'score': 0.86, 'dynamic_label': 'authority-vs-ambition'},
    frozenset({'new_employee', 'burnt_out_worker'}):         {'score': 0.82, 'dynamic_label': 'newcomer-meets-veteran'},
    frozenset({'new_employee', 'ambitious_climber'}):        {'score': 0.80, 'dynamic_label': 'fresh-start-vs-ambition'},

    # --- Service ---
    frozenset({'patient_service_worker', 'demanding_customer'}): {'score': 0.95, 'dynamic_label': 'customer-service-tension'},
    frozenset({'helpful_neighbor', 'new_parent'}):           {'score': 0.82, 'dynamic_label': 'neighbour-helping-new-parent'},
    frozenset({'helpful_neighbor', 'wise_grandparent'}):     {'score': 0.80, 'dynamic_label': 'friendly-neighbours'},
    frozenset({'helpful_neighbor', 'rebellious_teen'}):      {'score': 0.78, 'dynamic_label': 'neighbour-teen-interaction'},

    # --- Cross-category ---
    frozenset({'loyal_best_friend', 'jealous_partner'}):     {'score': 0.85, 'dynamic_label': 'friend-caught-in-relationship-drama'},
    frozenset({'wise_counselor', 'jealous_partner'}):        {'score': 0.84, 'dynamic_label': 'friend-counselling-jealous-partner'},
    frozenset({'loyal_best_friend', 'hopeless_romantic'}):   {'score': 0.86, 'dynamic_label': 'friend-supporting-romantic-quest'},
    frozenset({'gossip_enthusiast', 'loyal_best_friend'}):   {'score': 0.83, 'dynamic_label': 'gossiping-friends'},
    frozenset({'gossip_enthusiast', 'nagging_relative'}):    {'score': 0.82, 'dynamic_label': 'nosy-family-gossip'},
    frozenset({'gossip_enthusiast', 'party_animal'}):        {'score': 0.81, 'dynamic_label': 'social-gossip'},
    frozenset({'social_media_addict', 'party_animal'}):      {'score': 0.84, 'dynamic_label': 'social-butterflies'},
    frozenset({'social_media_addict', 'rebellious_teen'}):   {'score': 0.82, 'dynamic_label': 'online-generation'},
    frozenset({'community_organizer', 'helpful_neighbor'}):  {'score': 0.82, 'dynamic_label': 'community-collaboration'},
    frozenset({'ambitious_climber', 'supportive_spouse'}):   {'score': 0.86, 'dynamic_label': 'career-vs-relationship'},
    frozenset({'burnt_out_worker', 'supportive_spouse'}):    {'score': 0.88, 'dynamic_label': 'partner-supporting-burnout'},
    frozenset({'burnt_out_worker', 'loyal_best_friend'}):    {'score': 0.85, 'dynamic_label': 'friend-supporting-burnout'},
    frozenset({'wise_counselor', 'burnt_out_worker'}):       {'score': 0.84, 'dynamic_label': 'counselling-burnout'},
    frozenset({'wise_counselor', 'new_parent'}):             {'score': 0.83, 'dynamic_label': 'friend-advising-new-parent'},
    frozenset({'inspiring_mentor', 'rebellious_teen'}):      {'score': 0.80, 'dynamic_label': 'mentor-guiding-youth'},
    frozenset({'demanding_customer', 'strict_boss'}):        {'score': 0.78, 'dynamic_label': 'authority-clash'},
}


# =============================================================================
# ARCHETYPE CATEGORY MAPPING
# =============================================================================

_FAMILY_ARCHETYPES = {
    'protective_parent', 'rebellious_teen', 'supportive_sibling',
    'wise_grandparent', 'nagging_relative', 'new_parent',
}
_ROMANTIC_ARCHETYPES = {
    'hopeless_romantic', 'commitment_phobe', 'long_term_partner',
    'jealous_partner', 'supportive_spouse', 'new_dater',
}
_FRIEND_ARCHETYPES = {
    'loyal_best_friend', 'party_animal', 'wise_counselor',
    'competitive_friend',
}
_PROFESSIONAL_ARCHETYPES = {
    'ambitious_climber', 'burnt_out_worker', 'inspiring_mentor',
    'strict_boss', 'new_employee',
}
_SERVICE_ARCHETYPES = {
    'patient_service_worker', 'demanding_customer', 'helpful_neighbor',
}
_SOCIAL_ARCHETYPES = {
    'gossip_enthusiast', 'social_media_addict', 'community_organizer',
}


def _archetype_to_category(archetype: str) -> str:
    if archetype in _FAMILY_ARCHETYPES:       return 'family'
    if archetype in _ROMANTIC_ARCHETYPES:      return 'romantic_partners'
    if archetype in _FRIEND_ARCHETYPES:        return 'friends'
    if archetype in _PROFESSIONAL_ARCHETYPES:  return 'colleagues'
    if archetype in _SERVICE_ARCHETYPES:       return 'service'
    if archetype in _SOCIAL_ARCHETYPES:        return 'friends'
    return 'strangers'


# =============================================================================
# SCORING
# =============================================================================

def score_pair(persona_a: dict, persona_b: dict) -> tuple[float, Optional[str]]:
    """
    Score a persona pair. Returns (score, dynamic_label).

    Checks DYNAMIC_COMPATIBILITY by archetype pair first.
    Falls back to heuristic scoring if no matrix entry exists.
    dynamic_label is None for heuristic fallback.
    """
    arch_a = persona_a.get('archetype', '')
    arch_b = persona_b.get('archetype', '')

    # Matrix lookup
    key = frozenset({arch_a, arch_b})
    entry = DYNAMIC_COMPATIBILITY.get(key)
    if entry:
        return entry['score'], entry['dynamic_label']

    # Heuristic fallback (ported from PersonaDesigner.score_pair)
    score = 0.50

    reg_a = persona_a.get('register', 'informal')
    reg_b = persona_b.get('register', 'informal')
    if reg_a == reg_b:
        score += 0.15
    elif {reg_a, reg_b} == {'formal', 'informal'}:
        score -= 0.10

    rel_a = set(persona_a.get('relationship_types') or [])
    rel_b = set(persona_b.get('relationship_types') or [])
    overlap = rel_a & rel_b
    if overlap:
        score += 0.10 * min(len(overlap), 3)

    dom_a = set(persona_a.get('expertise_domains') or [])
    dom_b = set(persona_b.get('expertise_domains') or [])
    if dom_a & dom_b:
        score += 0.10

    age_a = persona_a.get('age', 30)
    age_b = persona_b.get('age', 30)
    if age_a and age_b and abs(age_a - age_b) > 15:
        score += 0.05

    # Same archetype gets a small label
    label = None
    if arch_a == arch_b:
        score = max(score, 0.65)
        label = 'same-archetype-peer'

    return max(0.0, min(1.0, score)), label


# =============================================================================
# RELATIONSHIP TYPE DERIVATION
# =============================================================================

def derive_relationship_type(persona_a: dict, persona_b: dict) -> str:
    """
    Derive the best relationship_type for a pair.

    Uses archetype categories first, then falls back to
    set intersection of relationship_types arrays.
    """
    arch_a = persona_a.get('archetype', '')
    arch_b = persona_b.get('archetype', '')

    cat_a = _archetype_to_category(arch_a)
    cat_b = _archetype_to_category(arch_b)

    # If both archetypes map to the same category, use it
    if cat_a == cat_b:
        return cat_a

    # Cross-category: prioritise by specificity
    cats = {cat_a, cat_b}
    for priority in ['romantic_partners', 'family', 'service', 'colleagues', 'friends']:
        if priority in cats:
            return priority

    # Final fallback: set intersection of relationship_types arrays
    rel_a = set(persona_a.get('relationship_types') or [])
    rel_b = set(persona_b.get('relationship_types') or [])
    overlap = rel_a & rel_b
    if overlap:
        return sorted(overlap)[0]

    return 'acquaintances'


# =============================================================================
# SUITABLE DOMAINS
# =============================================================================

def get_suitable_domains(persona_a: dict, persona_b: dict) -> list[str]:
    """
    Compute suitable_domains from personas' expertise_domains.

    Returns intersection if non-empty, otherwise union capped at 5.
    """
    dom_a = set(persona_a.get('expertise_domains') or [])
    dom_b = set(persona_b.get('expertise_domains') or [])

    intersection = dom_a & dom_b
    if intersection:
        return sorted(intersection)

    union = dom_a | dom_b
    if union:
        return sorted(union)[:5]

    return ['general']
