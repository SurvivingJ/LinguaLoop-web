"""
Template-Based Persona Generator

Deterministic persona generation using random sampling from predefined
archetype templates and seed pools. Produces persona dicts matching
the personas table schema.
"""

import random
import logging

from services.conversation_generation.archetypes import (
    ARCHETYPES,
    NAME_POOLS,
    OCCUPATION_POOLS,
    PERSONALITY_TRAIT_POOLS,
    SYSTEM_PROMPT_TEMPLATES,
)

logger = logging.getLogger(__name__)


# ===================================================================
# Domain expertise mapping
# ===================================================================

CATEGORY_DOMAINS = {
    'family': ['family', 'education', 'cooking'],
    'romantic': ['social', 'travel', 'food'],
    'friendship': ['social', 'sports', 'entertainment'],
    'professional': ['business', 'finance', 'technology'],
    'service': ['retail', 'hospitality', 'community'],
    'social': ['social media', 'community', 'entertainment'],
}

# Simple gender heuristic for Chinese/Japanese names
# Common feminine endings/characters
_FEMININE_CHARS_ZH = set('芳花美丽娜婷莉玲燕霞慧雪兰婉娟丹秀玉琴月梅英凤')
_FEMININE_CHARS_JA = set('子美花香奈衣月菜織葉華音乃')


def _guess_gender_cjk(name: str) -> str:
    last_char = name[-1]
    if last_char in _FEMININE_CHARS_ZH or last_char in _FEMININE_CHARS_JA:
        return 'female'
    return 'male'


# English name → gender fallback
GENDER_MAP = {
    # Male first names
    'james': 'male', 'john': 'male', 'robert': 'male', 'michael': 'male',
    'william': 'male', 'david': 'male', 'richard': 'male', 'joseph': 'male',
    'thomas': 'male', 'daniel': 'male', 'matthew': 'male', 'anthony': 'male',
    'mark': 'male', 'steven': 'male', 'paul': 'male', 'andrew': 'male',
    'joshua': 'male', 'kevin': 'male', 'brian': 'male', 'edward': 'male',
    'oliver': 'male', 'ryan': 'male', 'liam': 'male', 'noah': 'male',
    'ethan': 'male', 'lucas': 'male', 'jack': 'male', 'benjamin': 'male',
    'aiden': 'male', 'samuel': 'male', 'connor': 'male', 'marcus': 'male',
    'jayden': 'male', 'kai': 'male', 'tyler': 'male', 'nathan': 'male',
    'ravi': 'male', 'diego': 'male', 'alexander': 'male', 'henry': 'male',
    'sebastian': 'male', 'owen': 'male', 'caleb': 'male', 'isaac': 'male',
    'leo': 'male', 'finn': 'male', 'jake': 'male', 'dylan': 'male',
    'maxwell': 'male', 'adrian': 'male', 'patrick': 'male', 'george': 'male',
    'dominic': 'male', 'trevor': 'male', 'vincent': 'male', 'xavier': 'male',
    'cameron': 'male', 'blake': 'male', 'miles': 'male', 'oscar': 'male',
    'rowan': 'male', 'elliot': 'male', 'tristan': 'male', 'callum': 'male',
    'declan': 'male', 'kieran': 'male', 'brandon': 'male', 'ashton': 'male',
    'stefan': 'male', 'kwame': 'male', 'tariq': 'male', 'mateo': 'male',
    'jamal': 'male', 'kofi': 'male',
    # Female first names
    'mary': 'female', 'patricia': 'female', 'jennifer': 'female', 'linda': 'female',
    'elizabeth': 'female', 'barbara': 'female', 'susan': 'female', 'jessica': 'female',
    'sarah': 'female', 'karen': 'female', 'nancy': 'female', 'lisa': 'female',
    'betty': 'female', 'margaret': 'female', 'dorothy': 'female', 'sandra': 'female',
    'ashley': 'female', 'emily': 'female', 'donna': 'female', 'michelle': 'female',
    'emma': 'female', 'olivia': 'female', 'sophia': 'female', 'charlotte': 'female',
    'amelia': 'female', 'mia': 'female', 'harper': 'female', 'evelyn': 'female',
    'alice': 'female', 'rachel': 'female', 'hannah': 'female', 'grace': 'female',
    'sophie': 'female', 'megan': 'female', 'amara': 'female', 'isabella': 'female',
    'ava': 'female', 'priya': 'female', 'chloe': 'female', 'fatima': 'female',
    'zara': 'female', 'lily': 'female', 'nadia': 'female', 'courtney': 'female',
    'aaliyah': 'female', 'abigail': 'female', 'eleanor': 'female', 'scarlett': 'female',
    'victoria': 'female', 'penelope': 'female', 'layla': 'female', 'stella': 'female',
    'naomi': 'female', 'isla': 'female', 'ruby': 'female', 'clara': 'female',
    'sienna': 'female', 'maya': 'female', 'ellie': 'female', 'jasmine': 'female',
    'brooke': 'female', 'hazel': 'female', 'tessa': 'female', 'audrey': 'female',
    'leah': 'female', 'natasha': 'female', 'iris': 'female', 'freya': 'female',
    'phoebe': 'female', 'imogen': 'female', 'amelie': 'female', 'willow': 'female',
    'daisy': 'female', 'cora': 'female', 'alina': 'female', 'yuki': 'female',
    'ingrid': 'female', 'anya': 'female', 'mei-ling': 'female', 'sanna': 'female',
}


# ===================================================================
# Template Persona Generator
# ===================================================================

class TemplatePersonaGenerator:
    """Generates personas deterministically from archetype templates and seed pools."""

    def __init__(self, language_id: int):
        self.language_id = language_id
        self._used_names: set[str] = set()

    def generate(self, archetype_key: str) -> dict:
        """
        Generate one persona dict from an archetype using random sampling.

        Returns a dict matching the personas table schema:
        {name, language_id, age, gender, occupation, archetype, personality,
         register, expertise_domains, relationship_types, system_prompt, generation_method}
        """
        archetype = ARCHETYPES[archetype_key]

        # Sample unique name
        name = self._sample_name()

        # Age from archetype range
        age_lo, age_hi = archetype['age_range']
        age = random.randint(age_lo, age_hi)

        # Gender
        gender = self._determine_gender(name)

        # Occupation from category pool
        category = archetype['category']
        occupation = random.choice(OCCUPATION_POOLS[self.language_id][category])

        # Personality traits: 2 positive + 1 negative + 1 neutral
        trait_pool = PERSONALITY_TRAIT_POOLS[self.language_id]
        positive_traits = random.sample(trait_pool['positive'], 2)
        negative_traits = random.sample(trait_pool['negative'], 1)
        neutral_traits = random.sample(trait_pool['neutral'], 1)
        traits = positive_traits + negative_traits + neutral_traits

        # Speaking style
        speaking_style = random.choice(trait_pool['speaking_style'])

        # JSONB personality dict (matches existing seed data format)
        personality = {'traits': traits, 'speaking_style': speaking_style}

        # Register
        register = random.choice(archetype['typical_registers'])

        # Expertise domains from category
        expertise_domains = CATEGORY_DOMAINS.get(category, ['general'])

        # Relationship types from archetype
        relationship_types = archetype['typical_relationship_types']

        # System prompt
        system_prompt = SYSTEM_PROMPT_TEMPLATES[self.language_id].format(
            name=name,
            age=age,
            occupation=occupation,
            traits_str=', '.join(traits),
            speaking_style=speaking_style,
        )

        return {
            'name': name,
            'language_id': self.language_id,
            'age': age,
            'gender': gender,
            'occupation': occupation,
            'archetype': archetype_key,
            'personality': personality,
            'register': register,
            'expertise_domains': expertise_domains,
            'relationship_types': relationship_types,
            'system_prompt': system_prompt,
            'generation_method': 'template',
        }

    def generate_batch(self, archetype_key: str, count: int = 4) -> list[dict]:
        """Generate multiple unique personas for one archetype."""
        personas = []
        for _ in range(count):
            try:
                persona = self.generate(archetype_key)
                personas.append(persona)
            except Exception as exc:
                logger.warning("Failed to generate persona for %s: %s", archetype_key, exc)
        return personas

    def generate_all_archetypes(self, per_archetype: int = 4) -> list[dict]:
        """Generate personas across all 26 archetypes. Returns list of persona dicts."""
        all_personas = []
        for archetype_key in ARCHETYPES:
            batch = self.generate_batch(archetype_key, count=per_archetype)
            all_personas.extend(batch)
            logger.info("Generated %d personas for archetype '%s'", len(batch), archetype_key)
        logger.info("Total template personas generated: %d", len(all_personas))
        return all_personas

    # ---------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------

    def _sample_name(self) -> str:
        available = [n for n in NAME_POOLS[self.language_id] if n not in self._used_names]
        if not available:
            raise ValueError(f"No unused names left for language_id={self.language_id}")
        name = random.choice(available)
        self._used_names.add(name)
        return name

    def _determine_gender(self, name: str) -> str:
        # Chinese (language_id typically 1) / Japanese (typically 3) heuristic
        if self.language_id in (1, 3):
            return _guess_gender_cjk(name)

        # English and other Latin-script languages: look up map, fall back to random
        lookup = name.lower().split()[0]  # first name only
        if lookup in GENDER_MAP:
            return GENDER_MAP[lookup]
        return random.choice(['male', 'female'])
