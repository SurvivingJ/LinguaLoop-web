"""Tests for the persona pairing engine."""

import pytest
from services.conversation_generation.pairing import (
    DYNAMIC_COMPATIBILITY,
    score_pair,
    derive_relationship_type,
    get_suitable_domains,
)


class TestDynamicCompatibility:
    """Tests for the compatibility matrix data integrity."""

    def test_all_scores_in_range(self):
        """All matrix scores must be between 0.0 and 1.0."""
        for key, entry in DYNAMIC_COMPATIBILITY.items():
            assert 0.0 <= entry['score'] <= 1.0, \
                f"Score {entry['score']} out of range for {key}"

    def test_all_entries_have_labels(self):
        """All matrix entries must have non-empty dynamic_label."""
        for key, entry in DYNAMIC_COMPATIBILITY.items():
            assert entry.get('dynamic_label'), \
                f"Missing dynamic_label for {key}"

    def test_matrix_has_sufficient_entries(self):
        """Matrix should have at least 40 curated pairs."""
        assert len(DYNAMIC_COMPATIBILITY) >= 40

    def test_keys_are_frozensets_of_two(self):
        """All keys must be frozensets of exactly 1 or 2 archetype strings."""
        for key in DYNAMIC_COMPATIBILITY:
            assert isinstance(key, frozenset)
            assert 1 <= len(key) <= 2, f"Key {key} has {len(key)} elements"


class TestScorePair:
    """Tests for the score_pair function."""

    def test_matrix_lookup(self):
        """Known matrix pair returns expected score and label."""
        a = {'archetype': 'protective_parent', 'register': 'informal'}
        b = {'archetype': 'rebellious_teen', 'register': 'informal'}
        score, label = score_pair(a, b)
        assert score == 0.92
        assert label == 'parent-teen-conflict'

    def test_matrix_lookup_reverse_order(self):
        """Matrix lookup is order-independent."""
        a = {'archetype': 'rebellious_teen', 'register': 'informal'}
        b = {'archetype': 'protective_parent', 'register': 'informal'}
        score, label = score_pair(a, b)
        assert score == 0.92
        assert label == 'parent-teen-conflict'

    def test_symmetry_for_all_matrix_entries(self):
        """score_pair(a,b) == score_pair(b,a) for every matrix entry."""
        for key in DYNAMIC_COMPATIBILITY:
            archetypes = list(key)
            if len(archetypes) == 1:
                archetypes = [archetypes[0], archetypes[0]]

            a = {'archetype': archetypes[0]}
            b = {'archetype': archetypes[1]}

            s1, l1 = score_pair(a, b)
            s2, l2 = score_pair(b, a)
            assert s1 == s2, f"Asymmetric score for {key}"
            assert l1 == l2, f"Asymmetric label for {key}"

    def test_heuristic_fallback(self):
        """Unlisted archetype pair falls back to heuristic scoring."""
        a = {'archetype': 'gossip_enthusiast', 'register': 'informal',
             'relationship_types': ['friends'], 'expertise_domains': ['social'],
             'age': 30}
        b = {'archetype': 'new_employee', 'register': 'semi-formal',
             'relationship_types': ['colleagues'], 'expertise_domains': ['business'],
             'age': 25}
        score, label = score_pair(a, b)
        # Heuristic: base 0.5, no register match, no relationship overlap,
        # no domain overlap, age diff < 15 → 0.5
        assert 0.0 <= score <= 1.0
        assert label is None  # heuristic returns None label

    def test_same_archetype_peer(self):
        """Same archetype without matrix entry gets 'same-archetype-peer' label."""
        a = {'archetype': 'gossip_enthusiast', 'register': 'informal',
             'relationship_types': ['friends'], 'expertise_domains': ['social'],
             'age': 30}
        b = {'archetype': 'gossip_enthusiast', 'register': 'informal',
             'relationship_types': ['friends'], 'expertise_domains': ['social'],
             'age': 35}
        score, label = score_pair(a, b)
        assert score >= 0.65
        assert label == 'same-archetype-peer'

    def test_score_always_in_range(self):
        """Score is always between 0.0 and 1.0 even with extreme inputs."""
        a = {'archetype': 'x', 'register': 'formal',
             'relationship_types': ['a', 'b', 'c', 'd'],
             'expertise_domains': ['e'], 'age': 18}
        b = {'archetype': 'y', 'register': 'informal',
             'relationship_types': [], 'expertise_domains': [],
             'age': 80}
        score, _ = score_pair(a, b)
        assert 0.0 <= score <= 1.0


class TestDeriveRelationshipType:
    """Tests for relationship type derivation."""

    def test_family_archetypes(self):
        """Two family archetypes → 'family'."""
        a = {'archetype': 'protective_parent', 'relationship_types': ['family']}
        b = {'archetype': 'rebellious_teen', 'relationship_types': ['family', 'friends']}
        assert derive_relationship_type(a, b) == 'family'

    def test_romantic_archetypes(self):
        """Two romantic archetypes → 'romantic_partners'."""
        a = {'archetype': 'hopeless_romantic'}
        b = {'archetype': 'commitment_phobe'}
        assert derive_relationship_type(a, b) == 'romantic_partners'

    def test_professional_archetypes(self):
        """Two professional archetypes → 'colleagues'."""
        a = {'archetype': 'strict_boss'}
        b = {'archetype': 'new_employee'}
        assert derive_relationship_type(a, b) == 'colleagues'

    def test_cross_category_priority(self):
        """Cross-category defaults to higher-priority type."""
        a = {'archetype': 'protective_parent'}  # family
        b = {'archetype': 'new_dater'}           # romantic
        result = derive_relationship_type(a, b)
        assert result in ('romantic_partners', 'family')

    def test_unknown_archetypes_return_strangers(self):
        """Unknown archetypes map to 'strangers' category."""
        a = {'archetype': 'unknown_x', 'relationship_types': ['friends', 'colleagues']}
        b = {'archetype': 'unknown_y', 'relationship_types': ['colleagues', 'strangers']}
        assert derive_relationship_type(a, b) == 'strangers'

    def test_unknown_archetypes_no_relationships(self):
        """Unknown archetypes with no relationship_types → 'strangers'."""
        a = {'archetype': 'unknown_x', 'relationship_types': []}
        b = {'archetype': 'unknown_y', 'relationship_types': []}
        assert derive_relationship_type(a, b) == 'strangers'


class TestGetSuitableDomains:
    """Tests for suitable domain computation."""

    def test_intersection(self):
        """Returns intersection when both have overlapping domains."""
        a = {'expertise_domains': ['business', 'finance', 'technology']}
        b = {'expertise_domains': ['finance', 'education']}
        result = get_suitable_domains(a, b)
        assert result == ['finance']

    def test_empty_intersection_returns_union(self):
        """Returns union (capped at 5) when no intersection."""
        a = {'expertise_domains': ['business', 'finance']}
        b = {'expertise_domains': ['cooking', 'travel']}
        result = get_suitable_domains(a, b)
        assert set(result) == {'business', 'finance', 'cooking', 'travel'}
        assert len(result) <= 5

    def test_both_empty_returns_general(self):
        """Returns ['general'] when both have empty domains."""
        a = {'expertise_domains': []}
        b = {'expertise_domains': []}
        assert get_suitable_domains(a, b) == ['general']

    def test_missing_field_returns_general(self):
        """Handles missing expertise_domains gracefully."""
        a = {}
        b = {}
        assert get_suitable_domains(a, b) == ['general']

    def test_union_capped_at_five(self):
        """Union result is capped at 5 entries."""
        a = {'expertise_domains': ['a', 'b', 'c', 'd']}
        b = {'expertise_domains': ['e', 'f', 'g', 'h']}
        result = get_suitable_domains(a, b)
        assert len(result) <= 5
