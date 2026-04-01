"""
Categorical Maps, Numeric Key Infrastructure & Age-Tier Complexity System

Provides:
- CATEGORICAL_MAPS: English enum → per-language translations for register and relationship_type
- SCENARIO_KEY_MAP / GOALS_KEY_MAP: numeric JSON key → English DB column mappings
- Age-tier complexity system: VALID_TIERS, TIER_CONSTRAINTS, TIER_DISPLAY_NAMES, mappings
- Helper functions for localizing prompt inputs, reverse-looking-up LLM output, and tier lookups
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Categorical translations ────────────────────────────────────────────────
# Maps English DB enum values to target-language translations.
# Language IDs: 1=Chinese, 2=English, 3=Japanese

CATEGORICAL_MAPS: Dict[str, Dict[str, Dict[int, str]]] = {
    'register': {
        'formal':      {1: '正式', 2: 'formal', 3: 'フォーマル'},
        'semi-formal': {1: '半正式', 2: 'semi-formal', 3: 'セミフォーマル'},
        'informal':    {1: '非正式', 2: 'informal', 3: 'カジュアル'},
    },
    'relationship_type': {
        'family':            {1: '家庭', 2: 'family', 3: '家族'},
        'romantic_partners': {1: '恋人', 2: 'romantic partners', 3: '恋人'},
        'friends':           {1: '朋友', 2: 'friends', 3: '友人'},
        'colleagues':        {1: '同事', 2: 'colleagues', 3: '同僚'},
        'service':           {1: '服务', 2: 'service', 3: 'サービス'},
        'strangers':         {1: '陌生人', 2: 'strangers', 3: '他人'},
        'acquaintances':     {1: '熟人', 2: 'acquaintances', 3: '知人'},
    },
}

# ── Numeric key → English DB column mappings ────────────────────────────────
# Used to remap LLM output from numeric keys back to named DB columns.

SCENARIO_KEY_MAP: Dict[str, str] = {
    '1': 'title',
    '2': 'context_description',
    '3': 'goals',
    '4': 'keywords',
    '5': 'suitable_archetypes',
    '6': 'required_register',
    '7': 'required_relationship_type',
    '8': 'complexity_tier',
    '9': 'cultural_note',
}

GOALS_KEY_MAP: Dict[str, str] = {
    '1': 'persona_a',
    '2': 'persona_b',
}

# ── Language-specific delimiters ────────────────────────────────────────────

_DELIMITERS: Dict[int, str] = {
    1: '、',   # Chinese comma
    2: ', ',   # English comma
    3: '、',   # Japanese comma
}


# ── Helper functions ────────────────────────────────────────────────────────

def localize_categorical(
    category: str, english_value: str, language_id: int,
) -> str:
    """Translate a single English enum value to its target-language equivalent.

    Returns the original English value as fallback if no translation exists.
    """
    cat_map = CATEGORICAL_MAPS.get(category, {})
    translations = cat_map.get(english_value)
    if translations is None:
        logger.warning(
            "No translation for %s='%s' — returning English value",
            category, english_value,
        )
        return english_value
    return translations.get(language_id, english_value)


def localize_list(
    category: str, english_values: List[str], language_id: int,
) -> str:
    """Translate a list of English enum values and join with language-appropriate delimiter."""
    if not english_values:
        return ''
    delimiter = _DELIMITERS.get(language_id, ', ')
    return delimiter.join(
        localize_categorical(category, v, language_id) for v in english_values
    )


def reverse_lookup(
    category: str, localized_value: str, language_id: int,
) -> Optional[str]:
    """Map a localized value back to its English DB enum.

    Handles whitespace/punctuation stripping. Returns None if no match found.
    """
    cat_map = CATEGORICAL_MAPS.get(category, {})
    if not cat_map:
        logger.warning("Unknown category for reverse lookup: '%s'", category)
        return None

    # Normalise: strip whitespace and common trailing punctuation
    cleaned = localized_value.strip(' \t.。、，,')

    # Build reverse map for the requested language
    reverse: Dict[str, str] = {}
    for english_key, translations in cat_map.items():
        loc = translations.get(language_id)
        if loc is not None:
            reverse[loc] = english_key

    # Exact match
    if cleaned in reverse:
        return reverse[cleaned]

    # Case-insensitive match (mainly for English)
    cleaned_lower = cleaned.lower()
    for loc_val, eng_key in reverse.items():
        if loc_val.lower() == cleaned_lower:
            return eng_key

    # Substring containment fallback (handles e.g. "正式的" matching "正式")
    for loc_val, eng_key in reverse.items():
        if loc_val in cleaned or cleaned in loc_val:
            logger.info(
                "Fuzzy match: '%s' → '%s' (via '%s')", localized_value, eng_key, loc_val,
            )
            return eng_key

    logger.warning(
        "Reverse lookup failed for %s='%s' (lang=%d)", category, localized_value, language_id,
    )
    return None


def remap_numeric_keys(raw: dict, key_map: Dict[str, str]) -> dict:
    """Translate numeric string keys to English DB column names.

    Unknown keys are dropped with a debug log.
    """
    remapped = {}
    for num_key, value in raw.items():
        db_col = key_map.get(str(num_key))
        if db_col is None:
            logger.debug("Ignoring unknown numeric key '%s'", num_key)
            continue
        remapped[db_col] = value
    return remapped


# ── Age-Tier Complexity System ─────────────────────────────────────────────
# Replaces CEFR (A1-C2) with 6 age-equivalent tiers (T1-T6).
# Language IDs: 1=Chinese, 2=English, 3=Japanese

VALID_TIERS = ('T1', 'T2', 'T3', 'T4', 'T5', 'T6')

# 1:1 migration mapping (for legacy data conversion)
CEFR_TO_TIER = {'A1': 'T1', 'A2': 'T2', 'B1': 'T3', 'B2': 'T4', 'C1': 'T5', 'C2': 'T6'}
TIER_TO_CEFR = {v: k for k, v in CEFR_TO_TIER.items()}

# Display names per language
TIER_DISPLAY_NAMES: Dict[str, Dict[int, str]] = {
    'T1': {1: '幼儿（4-5岁）',     2: 'The Toddler (Age 4-5)',           3: '幼児（4-5歳）'},
    'T2': {1: '小学生（8-9岁）',    2: 'The Primary Schooler (Age 8-9)',  3: '小学生（8-9歳）'},
    'T3': {1: '初中生（13-14岁）',  2: 'The Young Teen (Age 13-14)',      3: '中学生（13-14歳）'},
    'T4': {1: '高中生（16-17岁）',  2: 'The High Schooler (Age 16-17)',   3: '高校生（16-17歳）'},
    'T5': {1: '大学生（19-21岁）',  2: 'The Uni Student (Age 19-21)',     3: '大学生（19-21歳）'},
    'T6': {1: '专业人士（30+岁）',  2: 'The Educated Professional (Age 30+)', 3: '社会人（30歳以上）'},
}

# Constraint definitions injected into prompts — all in target language
TIER_CONSTRAINTS: Dict[str, Dict[int, str]] = {
    'T1': {
        1: '只使用最常见的基本动词和具体名词。不使用抽象概念。每句话只表达一个意思。',
        2: 'Use only the most common basic verbs and concrete nouns. No abstract concepts. One idea per sentence.',
        3: '最も一般的な基本動詞と具体名詞のみを使用してください。抽象的な概念は使わないでください。一文に一つの考えだけ。',
    },
    'T2': {
        1: '使用复合句（和、但是、因为）。话题保持具体和直观。避免成语和专业术语。',
        2: 'Use compound sentences (and, but, because). Keep topics literal and concrete. Avoid idioms and professional jargon.',
        3: '複合文（そして、でも、なぜなら）を使ってください。話題は具体的で直接的に保ってください。慣用句や専門用語は避けてください。',
    },
    'T3': {
        1: '引入常见口语表达和轻度成语。使用条件句。语言应该完全自然地用于日常对话，但避免高度专业化或学术性的词汇。',
        2: (
            'Introduce common colloquialisms and mild idioms. Use conditional sentences. '
            'The language should feel entirely natural for everyday conversation, but avoid '
            'highly specialized or academic words.'
        ),
        3: (
            '一般的な口語表現や軽い慣用句を取り入れてください。条件文を使ってください。'
            '日常会話として完全に自然に感じられるべきですが、高度に専門的または学術的な言葉は避けてください。'
        ),
    },
    'T4': {
        1: '使用标准成人语法结构和常见抽象名词。可以使用适度的领域术语。这是流利的日常成人语言。',
        2: (
            'Use standard adult grammatical structures and common abstract nouns. '
            'You may use moderate domain jargon. This is fluent, everyday adult language.'
        ),
        3: (
            '標準的な大人の文法構造と一般的な抽象名詞を使ってください。'
            '適度な専門用語を使ってもかまいません。これは流暢な日常的な大人の言葉です。'
        ),
    },
    'T5': {
        1: '使用标准语言的全部广度，包括复杂的从句、文化习语和丰富的描述性词汇。角色应该以流畅、清晰的节奏说话。',
        2: (
            'Use the full breadth of standard language, including complex subordinate clauses, '
            'cultural idioms, and rich descriptive vocabulary. Characters should speak with '
            'articulate, highly fluent pacing.'
        ),
        3: (
            '複雑な従属節、文化的慣用句、豊かな描写的語彙を含む標準言語の全幅を使ってください。'
            'キャラクターは明瞭で非常に流暢なペースで話すべきです。'
        ),
    },
    'T6': {
        1: (
            '使用高语体词汇、精确的专业术语和高级修辞手法'
            '（如外交被动语态、微妙讽刺、迂回表达）。'
            '对话应反映高学历专业人士在其领域巅峰的交流水平。'
        ),
        2: (
            'Use high-register vocabulary, precise domain-specific jargon, and advanced '
            'rhetorical devices (e.g., passive voice for diplomacy, subtle sarcasm, '
            'circumlocution). The dialogue should reflect highly educated, specialized '
            'adult professionals communicating at the peak of their field.'
        ),
        3: (
            '高レジスターの語彙、正確な専門用語、高度な修辞技法'
            '（外交的受動態、微妙な皮肉、婉曲表現など）を使ってください。'
            '対話は、その分野の頂点で交流する高学歴の専門家を反映すべきです。'
        ),
    },
}

# Numeric scores for difficulty calculation (replaces CEFR_NUMERIC)
TIER_NUMERIC: Dict[str, float] = {
    'T1': 1.0, 'T2': 2.0, 'T3': 3.0, 'T4': 3.5, 'T5': 4.0, 'T6': 5.0,
}

# IRT difficulty seeds (replaces CEFR_TO_IRT)
TIER_TO_IRT: Dict[str, float] = {
    'T1': -2.0, 'T2': -1.0, 'T3': 0.0, 'T4': 0.5, 'T5': 1.0, 'T6': 2.0,
}

# Cognitive phase mapping (replaces _CEFR_TO_PHASE)
TIER_TO_PHASE: Dict[str, str] = {
    'T1': 'A', 'T2': 'A', 'T3': 'B', 'T4': 'C', 'T5': 'D', 'T6': 'D',
}

# Difficulty integer → tier (replaces difficulty_to_cefr mappings)
DIFFICULTY_TO_TIER: Dict[int, str] = {
    1: 'T1', 2: 'T1', 3: 'T2', 4: 'T3', 5: 'T3',
    6: 'T4', 7: 'T5', 8: 'T6', 9: 'T6',
}


# ── Tier helper functions ──────────────────────────────────────────────────

def get_tier_constraint(tier: str, language_id: int) -> str:
    """Return the constraint definition for a tier in the target language."""
    tier_def = TIER_CONSTRAINTS.get(tier, TIER_CONSTRAINTS['T3'])
    return tier_def.get(language_id, tier_def[2])


def get_tier_display(tier: str, language_id: int) -> str:
    """Return the display name for a tier in the target language."""
    names = TIER_DISPLAY_NAMES.get(tier, TIER_DISPLAY_NAMES['T3'])
    return names.get(language_id, names[2])


def build_tier_legend(language_id: int) -> str:
    """Build the full tier legend for scenario generation prompts.

    Returns a multi-line string with each tier's display name and constraint.
    """
    lines = []
    for tier in VALID_TIERS:
        display = get_tier_display(tier, language_id)
        constraint = get_tier_constraint(tier, language_id)
        lines.append(f'{tier} = {display}: {constraint}')
    return '\n'.join(lines)
