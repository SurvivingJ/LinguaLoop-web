"""Tests for the persona generation system."""

import pytest
from services.conversation_generation.archetypes import (
    ARCHETYPES, NAME_POOLS, OCCUPATION_POOLS,
    PERSONALITY_TRAIT_POOLS, SYSTEM_PROMPT_TEMPLATES,
)
from services.conversation_generation.template_generator import TemplatePersonaGenerator


class TestArchetypeDefinitions:
    """Tests for archetype data integrity."""

    def test_all_archetypes_have_required_fields(self):
        """Every archetype must have label, category, registers, relationship_types, description, age_range."""
        required = {'label', 'category', 'typical_registers', 'typical_relationship_types', 'description', 'age_range'}
        for key, arch in ARCHETYPES.items():
            missing = required - set(arch.keys())
            assert not missing, f"Archetype '{key}' missing fields: {missing}"

    def test_valid_categories(self):
        """All archetypes belong to a valid category."""
        valid = {'family', 'romantic', 'friendship', 'professional', 'service', 'social'}
        for key, arch in ARCHETYPES.items():
            assert arch['category'] in valid, f"Archetype '{key}' has invalid category '{arch['category']}'"

    def test_valid_registers(self):
        """All archetype registers are valid values."""
        valid = {'formal', 'semi-formal', 'informal'}
        for key, arch in ARCHETYPES.items():
            for reg in arch['typical_registers']:
                assert reg in valid, f"Archetype '{key}' has invalid register '{reg}'"

    def test_age_ranges_valid(self):
        """Age ranges must be (min, max) with min >= 18 and max <= 80."""
        for key, arch in ARCHETYPES.items():
            lo, hi = arch['age_range']
            assert 18 <= lo <= hi <= 80, f"Archetype '{key}' has invalid age_range ({lo}, {hi})"

    def test_archetype_count(self):
        """Should have at least 26 archetypes."""
        assert len(ARCHETYPES) >= 26


class TestSeedPools:
    """Tests for seed data pool completeness."""

    @pytest.mark.parametrize("language_id", [1, 2, 3])
    def test_name_pool_size(self, language_id):
        """Each language should have at least 30 names."""
        assert len(NAME_POOLS[language_id]) >= 30

    @pytest.mark.parametrize("language_id", [1, 2, 3])
    def test_name_pool_no_duplicates(self, language_id):
        """Names within a language should be unique."""
        names = NAME_POOLS[language_id]
        assert len(names) == len(set(names)), f"Language {language_id} has duplicate names"

    @pytest.mark.parametrize("language_id", [1, 2, 3])
    def test_occupation_pools_cover_all_categories(self, language_id):
        """Occupation pools should cover all archetype categories."""
        categories = {arch['category'] for arch in ARCHETYPES.values()}
        for cat in categories:
            assert cat in OCCUPATION_POOLS[language_id], \
                f"Language {language_id} missing occupation pool for category '{cat}'"
            assert len(OCCUPATION_POOLS[language_id][cat]) >= 5

    @pytest.mark.parametrize("language_id", [1, 2, 3])
    def test_personality_trait_pools(self, language_id):
        """Each language should have all trait categories with enough entries."""
        for trait_type in ['positive', 'negative', 'neutral', 'speaking_style']:
            assert trait_type in PERSONALITY_TRAIT_POOLS[language_id]
            assert len(PERSONALITY_TRAIT_POOLS[language_id][trait_type]) >= 10

    @pytest.mark.parametrize("language_id", [1, 2, 3])
    def test_system_prompt_template_exists(self, language_id):
        """Each language should have a system prompt template."""
        assert language_id in SYSTEM_PROMPT_TEMPLATES
        template = SYSTEM_PROMPT_TEMPLATES[language_id]
        assert '{name}' in template
        assert '{age}' in template
        assert '{occupation}' in template


class TestTemplatePersonaGenerator:
    """Tests for the template-based persona generator."""

    def test_generate_single_persona(self):
        """Generator produces a valid persona dict."""
        gen = TemplatePersonaGenerator(language_id=2)
        persona = gen.generate('protective_parent')

        assert persona['language_id'] == 2
        assert persona['archetype'] == 'protective_parent'
        assert persona['generation_method'] == 'template'
        assert isinstance(persona['name'], str)
        assert isinstance(persona['age'], int)
        assert 35 <= persona['age'] <= 55  # protective_parent age range
        assert persona['gender'] in ('male', 'female')
        assert isinstance(persona['personality'], dict)
        assert 'traits' in persona['personality']
        assert 'speaking_style' in persona['personality']
        assert isinstance(persona['system_prompt'], str)
        assert len(persona['system_prompt']) > 10
        assert persona['register'] in ('informal', 'semi-formal')

    def test_generate_chinese_persona(self):
        """Generator works for Chinese (language_id=1)."""
        gen = TemplatePersonaGenerator(language_id=1)
        persona = gen.generate('wise_grandparent')

        assert persona['language_id'] == 1
        assert persona['archetype'] == 'wise_grandparent'
        assert 60 <= persona['age'] <= 80

    def test_generate_japanese_persona(self):
        """Generator works for Japanese (language_id=3)."""
        gen = TemplatePersonaGenerator(language_id=3)
        persona = gen.generate('new_employee')

        assert persona['language_id'] == 3
        assert persona['archetype'] == 'new_employee'
        assert 22 <= persona['age'] <= 30

    def test_generate_batch_unique_names(self):
        """Batch generation produces personas with unique names."""
        gen = TemplatePersonaGenerator(language_id=2)
        batch = gen.generate_batch('loyal_best_friend', count=5)

        assert len(batch) == 5
        names = [p['name'] for p in batch]
        assert len(names) == len(set(names)), "Names should be unique within batch"

    def test_generate_all_archetypes(self):
        """generate_all_archetypes produces personas for every archetype."""
        gen = TemplatePersonaGenerator(language_id=2)
        all_personas = gen.generate_all_archetypes(per_archetype=1)

        archetypes_seen = {p['archetype'] for p in all_personas}
        assert archetypes_seen == set(ARCHETYPES.keys())

    def test_persona_has_all_db_fields(self):
        """Generated persona dict has all fields needed for DB insertion."""
        gen = TemplatePersonaGenerator(language_id=2)
        persona = gen.generate('ambitious_climber')

        required_fields = {
            'name', 'language_id', 'age', 'gender', 'occupation',
            'archetype', 'personality', 'register', 'expertise_domains',
            'relationship_types', 'system_prompt', 'generation_method',
        }
        assert required_fields.issubset(persona.keys())

    def test_name_exhaustion_raises(self):
        """When all names are used up, generate raises ValueError."""
        gen = TemplatePersonaGenerator(language_id=2)
        # Use up all names
        gen._used_names = set(NAME_POOLS[2])

        with pytest.raises(ValueError, match="No unused names"):
            gen.generate('party_animal')
