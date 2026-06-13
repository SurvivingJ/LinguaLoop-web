# services/vocabulary_ladder/config.py
"""
Vocabulary ladder constants and helper functions.

The ladder has 9 levels grouped into 4 rings, progressing from receptive
recognition to productive use. Each level belongs to a cognitive family.
BKT tracks per-family confidence; rings unlock via threshold gates.

Ring structure:
  R1 (L1-L2): form_recognition
  R2 (L3-L5): meaning_recall, form_production, collocation
  R3 (L6-L7): semantic_discrimination
  R4 (L8-L9): collocation (advanced), form_production (advanced)

Concrete nouns skip collocation levels (5, 8).
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Ladder level definitions — each level has a cognitive family and ring
# ---------------------------------------------------------------------------

LADDER_LEVELS: dict[int, dict] = {
    1: {'name': 'Phonetic/Orthographic', 'exercise_type': 'phonetic_recognition',
        'prompt': 'prompt2', 'family': 'form_recognition', 'ring': 1},
    2: {'name': 'Definition Match',      'exercise_type': 'definition_match',
        'prompt': 'database', 'family': 'form_recognition', 'ring': 1},
    3: {'name': 'Cloze Completion',      'exercise_type': 'cloze_completion',
        'prompt': 'prompt2', 'family': 'meaning_recall', 'ring': 2},
    4: {'name': 'Morphology Slot',       'exercise_type': 'morphology_slot',
        'prompt': 'prompt3', 'family': 'form_production', 'ring': 2},
    5: {'name': 'Collocation Gap',       'exercise_type': 'collocation_gap_fill',
        'prompt': 'prompt2', 'family': 'collocation', 'ring': 2},
    6: {'name': 'Semantic Discrimination','exercise_type': 'semantic_discrimination',
        'prompt': 'prompt2', 'family': 'semantic_discrimination', 'ring': 3},
    7: {'name': 'Spot Incorrect',        'exercise_type': 'spot_incorrect_sentence',
        'prompt': 'prompt3', 'family': 'semantic_discrimination', 'ring': 3},
    8: {'name': 'Collocation Repair',    'exercise_type': 'collocation_repair',
        'prompt': 'prompt3', 'family': 'collocation', 'ring': 4},
    9: {'name': 'Jumbled Sentence',      'exercise_type': 'jumbled_sentence',
        'prompt': 'local', 'family': 'form_production', 'ring': 4},
}

ALL_LEVELS: list[int] = list(range(1, 10))

# Levels served by each prompt
PROMPT2_LEVELS: set[int] = {1, 3, 5, 6}
PROMPT3_LEVELS: set[int] = {4, 7, 8}
DATABASE_LEVELS: set[int] = {2}
LOCAL_LEVELS: set[int] = {9}

# ---------------------------------------------------------------------------
# Exercise families — cognitive skill groupings with educational weights
# ---------------------------------------------------------------------------
# Weights reflect importance for overall vocabulary mastery.
# p_known_overall = Σ(family_weight × family_confidence)

FAMILY_WEIGHTS: dict[str, float] = {
    'form_recognition': 0.12,
    'meaning_recall': 0.18,
    'form_production': 0.20,
    'collocation': 0.16,
    'semantic_discrimination': 0.16,
    'contextual_use': 0.18,  # Future L10 capstone
}

# Default initial confidence for all families
DEFAULT_FAMILY_CONFIDENCE: dict[str, float] = {
    'form_recognition': 0.10,
    'meaning_recall': 0.10,
    'form_production': 0.10,
    'collocation': 0.10,
    'semantic_discrimination': 0.10,
    'contextual_use': 0.10,
}

# Which families are exercised by the current 9-level ladder
# (contextual_use has no levels yet — future L10)
ACTIVE_FAMILIES: set[str] = {
    'form_recognition', 'meaning_recall', 'form_production',
    'collocation', 'semantic_discrimination',
}

# ---------------------------------------------------------------------------
# Ring structure — progressive difficulty tiers with gate requirements
# ---------------------------------------------------------------------------

RINGS: dict[int, dict] = {
    1: {'levels': [1, 2], 'families': {'form_recognition'},
        'unlock': None},
    2: {'levels': [3, 4, 5], 'families': {'meaning_recall', 'form_production', 'collocation'},
        'unlock': 'r1_cleared'},
    3: {'levels': [6, 7], 'families': {'semantic_discrimination'},
        'unlock': 'gate_a'},
    4: {'levels': [8, 9], 'families': {'collocation', 'form_production'},
        'unlock': 'gate_b'},
}

# ---------------------------------------------------------------------------
# Threshold gates — diagnostic checkpoints between rings
# ---------------------------------------------------------------------------

GATES: dict[str, dict] = {
    'gate_a': {
        'after_ring': 2,
        'unlocks_ring': 3,
        'min_p_known': 0.72,
        'min_family_confidence': 0.50,
        'battery_size': 3,
        'pass_threshold': 2,   # at least 2/3 correct
        'require_production': True,
    },
    'gate_b': {
        'after_ring': 3,
        'unlocks_ring': 4,
        'min_p_known': 0.84,
        'min_family_confidence': 0.65,
        'battery_size': 3,
        'pass_threshold': 2,
        'require_production': True,
    },
}

# ---------------------------------------------------------------------------
# Stress test — graduation battery before mastery
# ---------------------------------------------------------------------------

STRESS_TEST = {
    'min_p_known': 0.88,
    'min_family_confidence': 0.72,
    'battery_size': 8,
    'pass_threshold': 6,  # at least 6/8
    'require_production': True,   # at least 1/2 form_production correct
    'require_contextual': True,   # at least 1/2 contextual_use correct
    'max_zero_families': 1,       # at most 1 family scores 0 in the test
    'composition': {
        'form_production': 2,
        'meaning_recall': 1,
        'form_recognition': 1,
        'collocation': 1,
        'semantic_discrimination': 1,
        'contextual_use': 2,
    },
}

# ---------------------------------------------------------------------------
# Momentum band scheduling — dynamic intervals during acquisition
# ---------------------------------------------------------------------------

MOMENTUM_BANDS: list[dict] = [
    {'name': 'low',    'max_p_known': 0.45, 'interval_days': 1},
    {'name': 'medium', 'max_p_known': 0.75, 'interval_days': 1},
    {'name': 'high',   'max_p_known': 1.01, 'interval_days': 2},
]

# Family BKT update rates (learn_rate on correct, slip_rate on incorrect)
FAMILY_BKT_RATES: dict[str, dict[str, float]] = {
    'standard':    {'learn': 0.15, 'slip': 0.12},
    'gate':        {'learn': 0.18, 'slip': 0.10},  # gentler on failure
    'stress_test': {'learn': 0.20, 'slip': 0.12},  # bonus on success
}

# Session limits
MAX_WORD_APPEARANCES_PER_SESSION = 2  # unless new or gate-failed

# P1 sentence judge (Phase 4): minimum number of base sentences that must
# survive as acceptable (verdict accept OR flag) after the judge plus one
# targeted repair pass. Below this, too many of P1's sentences are
# off-sense / off-register / not-whole-word to build a reliable ladder from,
# so the whole prompt1_core asset is blocked. Flags count as acceptable (kept
# and surfaced for review); only hard rejects that survive repair reduce the
# count. See wiki/tasklist/ladder-judge-layer.tasks.md (TASK-404, decision 4).
P1_MIN_ACCEPTABLE_SENTENCES: int = 6

# ---------------------------------------------------------------------------
# Maintenance review template distribution (post-mastery, FSRS-driven)
# ---------------------------------------------------------------------------

MAINTENANCE_FAMILY_WEIGHTS: dict[str, float] = {
    'form_recognition': 0.05,
    'meaning_recall': 0.25,
    'form_production': 0.20,
    'collocation': 0.15,
    'semantic_discrimination': 0.15,
    'contextual_use': 0.20,
}

# ---------------------------------------------------------------------------
# Session priority scoring weights
# ---------------------------------------------------------------------------

SESSION_PRIORITY_WEIGHTS: dict[str, float] = {
    'overdue': 0.35,
    'weakness': 0.25,
    'gate_urgency': 0.20,
    'novelty_need': 0.10,
    'relapse_risk': 0.10,
}

# ---------------------------------------------------------------------------
# Word states
# ---------------------------------------------------------------------------

WORD_STATES: list[str] = [
    'new', 'active', 'gated', 'pre_mastery', 'relearning', 'mastered',
]

# ---------------------------------------------------------------------------
# semantic_class -> active ladder levels routing (ratified enum, plan §4)
# ---------------------------------------------------------------------------
# The ratified controlled vocabulary is exactly six language-neutral values:
#   concrete | abstract | action | property | function | proper
# Routing (plan §4 table):
#   concrete                 -> skip L5/L8 (no tight collocates); L4 stays active
#                               and is routed to classifier/counter/plural by the
#                               capability matrix (TASK-504)
#   abstract/action/property -> full ladder
#   function                 -> L1-L3 + L6/L7 only (no collocation/morphology/jumble)
#   proper                   -> not subscribed to the ladder (definition-flashcard only)
#   NULL / unrecognised      -> permissive full ladder (pre-backfill default)

COLLOCATION_LEVELS: set[int] = {5, 8}
CONCRETE_CLASSES: frozenset[str] = frozenset({'concrete'})
FUNCTION_CLASSES: frozenset[str] = frozenset({'function'})
LADDER_EXCLUDED_CLASSES: frozenset[str] = frozenset({'proper'})
FUNCTION_ACTIVE_LEVELS: list[int] = [1, 2, 3, 6, 7]


def compute_active_levels(
    semantic_class: str | None,
    language_id: int = 2,  # reserved: TASK-504 replaces this with the capability matrix
) -> list[int]:
    """Return the active ladder levels for a word's ratified semantic_class.

    See the routing table above. `proper` is not subscribed to the ladder
    (returns []); `function` words get receptive + discrimination levels only;
    `concrete` nouns skip the collocation levels (5, 8); everything else
    (including unclassified pre-backfill words) gets the full 9-level ladder.

    `language_id` is accepted for forward-compatibility — the L4 *type* per
    language is the capability matrix's concern (TASK-504), not the level's
    presence — so the level set is derived from semantic_class alone for now.
    """
    if semantic_class in LADDER_EXCLUDED_CLASSES:
        return []
    if semantic_class in FUNCTION_CLASSES:
        return list(FUNCTION_ACTIVE_LEVELS)
    skip: set[int] = set()
    if semantic_class in CONCRETE_CLASSES:
        skip |= COLLOCATION_LEVELS
    if not skip:
        return list(ALL_LEVELS)
    return [lv for lv in ALL_LEVELS if lv not in skip]


# ---------------------------------------------------------------------------
# Per-language Prompt 1 validation profiles
# ---------------------------------------------------------------------------
# Different languages have structurally different P1 output. English inflects
# (so >=2 morphological_forms and an IPA string are normal) but Chinese does
# not — its P1 prompt rule 18 permits an empty morphological_forms list and it
# carries pinyin rather than IPA. A single global gate over-rejects both
# Chinese assets and invariant English words ("sheep", "the", "must"). Each
# language declares its own enum sets and how strict the morphology/IPA checks
# are; shortfalls against these are demoted to non-blocking warnings by the
# validator (see VocabAssetValidator.validate_prompt1).
#
# language_id convention (shared with services/corpus/classifier.py):
#   1 = Chinese (Mandarin), 2 = English, 3 = Japanese

_POS_EN: frozenset[str] = frozenset({
    'noun', 'verb', 'adjective', 'adverb', 'preposition',
    'conjunction', 'pronoun', 'determiner', 'interjection',
})

# Chinese adds compound-result and directional-complement categories that
# English doesn't have.
_POS_ZH: frozenset[str] = frozenset({
    '名词', '动词', '形容词', '副词', '介词', '连词', '代词',
    '量词', '助词', '叹词', '方向补语', '结果补语', '情态动词',
})

# Ratified semantic_class controlled vocabulary (plan §4). Language-neutral:
# the same six values key every language's validation profile and the
# capability matrix (TASK-504). Enforced as a CHECK constraint on
# dim_vocabulary.semantic_class (migrations/semantic_class_enum.sql).
SEMANTIC_CLASSES: frozenset[str] = frozenset({
    'concrete', 'abstract', 'action', 'property', 'function', 'proper',
})

# Merged POS enum — permissive default for unconfigured languages. POS stays
# per-language; semantic_class is now language-neutral.
DEFAULT_POS_SET: frozenset[str] = _POS_EN | _POS_ZH
DEFAULT_SEMANTIC_CLASS_SET: frozenset[str] = SEMANTIC_CLASSES

# Legacy semantic_class labels (the old EN/ZH P1 enums + historical DB values)
# mapped onto the ratified set. The P1 prompts still emit these older labels
# until they are reseeded, so any value written back to dim_vocabulary must be
# normalised first — otherwise it violates the CHECK constraint
# (migrations/semantic_class_enum.sql). Unrecognised / "other" -> None
# (unclassified; NULL is allowed pre-backfill). `proper` has no legacy label.
_LEGACY_SEMANTIC_CLASS_MAP: dict[str, str] = {
    'concrete_noun': 'concrete', '具体名词': 'concrete',
    'abstract_noun': 'abstract', '抽象名词': 'abstract',
    'action_verb':   'action',   '动作动词': 'action',
    'state_verb':    'action',   '状态动词': 'action',
    'adjective':     'property', '形容词':   'property',
    'adverb':        'property', '副词':     'property',
    'function_word': 'function', '功能词':   'function',
}


def normalize_semantic_class(raw: str | None) -> str | None:
    """Map a raw semantic_class label onto the ratified enum, or None.

    Already-ratified values pass through; known legacy EN/ZH labels are
    translated; empty or unrecognised input returns None (NULL-safe). Use this
    at every boundary that persists semantic_class to dim_vocabulary.
    """
    if not raw:
        return None
    value = raw.strip()
    if value in SEMANTIC_CLASSES:
        return value
    return _LEGACY_SEMANTIC_CLASS_MAP.get(value)


@dataclass(frozen=True)
class LanguageValidationProfile:
    """Per-language thresholds and enums for Prompt 1 asset validation.

    Attributes:
        language_id: The language this profile applies to.
        min_morphological_forms: Minimum expected morphological_forms entries.
            A shortfall is a non-blocking warning, not an error. Default 0
            (no expectation — correct for analytic languages like Chinese).
        ipa_required: Whether a missing `ipa` field should raise a warning.
        pos_set: Accepted part-of-speech enum values.
        semantic_class_set: Accepted semantic_class enum values.
    """
    language_id: int
    min_morphological_forms: int = 0
    ipa_required: bool = False
    pos_set: frozenset[str] = DEFAULT_POS_SET
    semantic_class_set: frozenset[str] = DEFAULT_SEMANTIC_CLASS_SET


LANGUAGE_VALIDATION_PROFILES: dict[int, LanguageValidationProfile] = {
    1: LanguageValidationProfile(  # Chinese (Mandarin)
        language_id=1,
        min_morphological_forms=0,   # P1 rule 18 permits empty forms
        ipa_required=False,          # carries pinyin, not IPA
        pos_set=_POS_ZH,
        semantic_class_set=SEMANTIC_CLASSES,
    ),
    2: LanguageValidationProfile(  # English
        language_id=2,
        min_morphological_forms=2,   # warn (not block) invariant words
        ipa_required=True,
        pos_set=_POS_EN,
        semantic_class_set=SEMANTIC_CLASSES,
    ),
    3: LanguageValidationProfile(  # Japanese
        language_id=3,
        min_morphological_forms=0,
        ipa_required=False,
        pos_set=DEFAULT_POS_SET,
        semantic_class_set=DEFAULT_SEMANTIC_CLASS_SET,
    ),
}


def get_validation_profile(language_id: int) -> LanguageValidationProfile:
    """Return the P1 validation profile for a language.

    Unconfigured languages fall back to a permissive default: merged EN/zh
    enum sets and no hard morphology/IPA expectations, so a new language can
    onboard without spurious validation failures.
    """
    return LANGUAGE_VALIDATION_PROFILES.get(
        language_id, LanguageValidationProfile(language_id=language_id)
    )


# ---------------------------------------------------------------------------
# BKT → starting ladder level mapping
# ---------------------------------------------------------------------------

# Each tuple is (p_known_upper_bound, starting_level).
# The first match wins: if p_known < threshold, start at that level.
BKT_TO_LEVEL: list[tuple[float, int]] = [
    (0.15, 1),
    (0.40, 3),
    (0.60, 5),
    (0.80, 7),
    (1.01, 9),
]


def bkt_to_starting_level(p_known: float, active_levels: list[int]) -> int:
    """Map a BKT probability to the appropriate starting ladder level.

    If the computed level is skipped (e.g. level 5 for concrete nouns),
    falls back to the nearest active level at or below the target.
    """
    target = 1
    for threshold, level in BKT_TO_LEVEL:
        if p_known < threshold:
            target = level
            break

    # Find nearest active level <= target
    candidates = [lv for lv in active_levels if lv <= target]
    if candidates:
        return candidates[-1]
    return active_levels[0]


def next_active_level(current: int, active_levels: list[int]) -> int | None:
    """Return the next level in active_levels after current, or None if at max."""
    try:
        idx = active_levels.index(current)
        if idx + 1 < len(active_levels):
            return active_levels[idx + 1]
    except ValueError:
        # current not in active_levels — find next above it
        above = [lv for lv in active_levels if lv > current]
        if above:
            return above[0]
    return None


def prev_active_level(current: int, active_levels: list[int]) -> int | None:
    """Return the previous level in active_levels before current, or None if at min."""
    try:
        idx = active_levels.index(current)
        if idx > 0:
            return active_levels[idx - 1]
    except ValueError:
        below = [lv for lv in active_levels if lv < current]
        if below:
            return below[-1]
    return None


def get_ring_for_level(level: int) -> int:
    """Return the ring number (1-4) for a given ladder level."""
    info = LADDER_LEVELS.get(level)
    return info['ring'] if info else 1


def get_family_for_level(level: int) -> str:
    """Return the cognitive family for a given ladder level."""
    info = LADDER_LEVELS.get(level)
    return info['family'] if info else 'form_recognition'


def get_levels_for_ring(ring: int, active_levels: list[int]) -> list[int]:
    """Return the active levels belonging to a specific ring."""
    ring_info = RINGS.get(ring)
    if not ring_info:
        return []
    return [lv for lv in ring_info['levels'] if lv in active_levels]


def get_levels_for_family(family: str, active_levels: list[int]) -> list[int]:
    """Return the active levels belonging to a specific cognitive family."""
    return [
        lv for lv in active_levels
        if LADDER_LEVELS.get(lv, {}).get('family') == family
    ]


def compute_p_known_overall(family_confidence: dict[str, float]) -> float:
    """Compute overall p_known as weighted aggregate of family confidences."""
    total = 0.0
    for family, weight in FAMILY_WEIGHTS.items():
        conf = family_confidence.get(family, 0.10)
        total += weight * conf
    return round(total, 4)


def get_momentum_band(p_known: float) -> dict:
    """Return the momentum band for a given p_known value."""
    for band in MOMENTUM_BANDS:
        if p_known < band['max_p_known']:
            return band
    return MOMENTUM_BANDS[-1]


def compute_word_state(
    current_ring: int,
    gates_passed: dict[str, bool],
    p_known: float,
    stress_test_passed: bool = False,
) -> str:
    """Compute the word_state from progression data."""
    if stress_test_passed:
        return 'mastered'
    if current_ring >= 4 and gates_passed.get('gate_b', False) and p_known >= STRESS_TEST['min_p_known']:
        return 'pre_mastery'
    # Check if waiting for a gate
    if current_ring == 2 and not gates_passed.get('gate_a', False):
        return 'gated'
    if current_ring == 3 and not gates_passed.get('gate_b', False):
        return 'gated'
    if current_ring <= 1 and p_known < 0.20:
        return 'new'
    return 'active'


# ---------------------------------------------------------------------------
# Sentence assignment: which P1 sentence feeds which level
# ---------------------------------------------------------------------------
# P1 generates 10 sentences (indices 0-9). Variant A and B draw from
# different subsets to produce distinct exercises for the same word.

DEFAULT_SENTENCE_ASSIGNMENTS: dict[int, int] = {
    3: 0,   # L3 Cloze uses sentence 0
    4: 1,   # L4 Morphology uses sentence 1
    5: 2,   # L5 Collocation Gap uses sentence 2
    6: 3,   # L6 Semantic Discrimination uses sentence 3
    7: 4,   # L7 Spot Incorrect uses sentence 4 (plus 0,1 as correct)
    8: 4,   # L8 Collocation Repair uses sentence 4
    9: 5,   # L9 Jumbled uses sentence 5
}

# Variant A uses sentences 0-5 (same as current/default)
SENTENCE_ASSIGNMENTS_A: dict[int, int] = {
    3: 0,   # L3 Cloze
    4: 1,   # L4 Morphology
    5: 2,   # L5 Collocation Gap
    6: 3,   # L6 Semantic Discrimination
    7: 4,   # L7 Spot Incorrect (plus 0,1 as correct)
    8: 4,   # L8 Collocation Repair
    9: 5,   # L9 Jumbled
}

# Variant B uses sentences 6-9 + overflow from 0-3
SENTENCE_ASSIGNMENTS_B: dict[int, int] = {
    3: 6,   # L3 Cloze
    4: 7,   # L4 Morphology
    5: 8,   # L5 Collocation Gap
    6: 9,   # L6 Semantic Discrimination
    7: 0,   # L7 Spot Incorrect (plus 6,7 as correct)
    8: 8,   # L8 Collocation Repair
    9: 3,   # L9 Jumbled
}

# Correct sentence indices for L7 (Spot Incorrect) per variant
L7_CORRECT_INDICES_A: list[int] = [0, 1, 2]
L7_CORRECT_INDICES_B: list[int] = [6, 7, 9]


# ---------------------------------------------------------------------------
# Numeric key remapping: LLM output → descriptive keys
# ---------------------------------------------------------------------------
# LLM prompts use numeric keys ("1", "2", ...) for language neutrality.
# We remap to descriptive keys before storing in word_assets.

PROMPT1_KEY_MAP: dict[str, str] = {
    '1': 'pos',
    '2': 'semantic_class',
    '3': 'definition',
    '4': 'primary_collocate',
    '5': 'pronunciation',
    '6': 'ipa',
    '7': 'syllable_count',
    '8': 'sentences',
    '9': 'morphological_forms',
    '10': 'register',
    '11': 'sense_fingerprint',
}

SENTENCE_KEY_MAP: dict[str, str] = {
    '1': 'text',
    '2': 'target_word',
    '3': 'source',
    '4': 'complexity_tier',
}


def get_sentence_target(sentence: dict) -> str:
    """Read the target word from a sentence dict, alias-aware for legacy data.

    New rows use 'target_word'; legacy word_assets rows still use the old
    'target_substring' key. Read both to keep historical data working until
    a regeneration cycle replaces it.
    """
    if not isinstance(sentence, dict):
        return ''
    return sentence.get('target_word') or sentence.get('target_substring', '') or ''

MORPH_FORM_KEY_MAP: dict[str, str] = {
    '1': 'form',
    '2': 'label',
}

OPTION_KEY_MAP: dict[str, str] = {
    '1': 'text',
    '2': 'is_correct',
    '3': 'explanation',
}


def remap_keys(data: dict | list, key_map: dict[str, str]) -> dict | list:
    """Recursively remap numeric string keys to descriptive keys."""
    if isinstance(data, list):
        return [remap_keys(item, key_map) if isinstance(item, (dict, list)) else item
                for item in data]
    if isinstance(data, dict):
        return {key_map.get(k, k): v for k, v in data.items()}
    return data
