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

Nine levels is the ceiling, not the guarantee. The capability matrix decides
how many a given (language, semantic_class) actually runs, and Chinese and
Japanese currently run **seven** — L5 and L8 are disabled for both because
neither language has a collocation grounding source (see `_CAPABILITY_SPEC`).
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
        'prompt': 'l4_split', 'family': 'form_production', 'ring': 2},
    5: {'name': 'Collocation Gap',       'exercise_type': 'collocation_gap_fill',
        'prompt': 'prompt2', 'family': 'collocation', 'ring': 2},
    6: {'name': 'Semantic Discrimination','exercise_type': 'semantic_discrimination',
        'prompt': 'prompt2', 'family': 'semantic_discrimination', 'ring': 3},
    7: {'name': 'Spot Incorrect',        'exercise_type': 'spot_incorrect_sentence',
        'prompt': 'prompt3', 'family': 'semantic_discrimination', 'ring': 3},
    8: {'name': 'Collocation Repair',    'exercise_type': 'collocation_repair',
        'prompt': 'l8_split', 'family': 'collocation', 'ring': 4},
    9: {'name': 'Jumbled Sentence',      'exercise_type': 'jumbled_sentence',
        'prompt': 'local', 'family': 'form_production', 'ring': 4},
}

ALL_LEVELS: list[int] = list(range(1, 10))

# Levels served by each prompt
PROMPT2_LEVELS: set[int] = {1, 3, 5, 6}
DATABASE_LEVELS: set[int] = {2}
LOCAL_LEVELS: set[int] = {9}

# ---------------------------------------------------------------------------
# The P3 family: one shared prompt, plus the levels split out of it (TASK-520)
# ---------------------------------------------------------------------------
# ``PROMPT3_LEVELS`` is the set of levels the *P3 family* owns — it still keys
# the per-type generation gate (:func:`prompt3_levels_for_context`) and the
# renderer's suppression check, both of which reason about types rather than
# about which prompt produces them.
#
# ``PROMPT3_MONOLITH_LEVELS`` is the narrower set the shared prompt still emits.
# L4 and L8 moved to their own ``task_name``s so they get their own model,
# their own retry and a JSON-schema gate bound to their own prompt_version
# (audit B3.2 / B3.4); L7 keeps the shared prompt because nothing about it was
# failing and a third prompt row per language would be cost with no benefit.
PROMPT3_LEVELS: set[int] = {4, 7, 8}
PROMPT3_MONOLITH_LEVELS: set[int] = {7}

# level -> prompt_templates.task_name for the levels that left the monolith.
SPLIT_LEVEL_TASKS: dict[int, str] = {
    4: 'ladder_l4_morphology_generation',
    8: 'ladder_l8_collocation_repair_generation',
}

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
# Sentence provenance (TASK-513)
# ---------------------------------------------------------------------------
# Every P1 sentence records where it came from. `mined` sentences are real
# corpus usage lifted out of a test transcript via the sense index; `generated`
# ones the model wrote. Both go through the same tier gate and the same P1
# judge — provenance is a label, never a licence to skip a check.

SENTENCE_SOURCE_MINED: str = 'mined'
SENTENCE_SOURCE_GENERATED: str = 'generated'


# ---------------------------------------------------------------------------
# Sentence-tier hard gate (TASK-524)
# ---------------------------------------------------------------------------
# The eval's standing failure was a C2-lexis sentence shipped as the example
# for an A1 word ("the barista's meticulous extraction protocol yielded an
# exceptionally nuanced espresso" for *coffee*). The P1 judge is an LLM and
# costs money per sentence; this screen is deterministic, free, and runs first.
#
# Each token's Zipf frequency (wordfreq, the same scale stored in
# dim_vocabulary.frequency_rank) is compared against the *sense's* tier:
#
#   soft_floor       — below this a content word is "out of band" for the tier
#   max_out_of_band  — how many such words a sentence may carry
#   hard_floor       — a word this rare rejects the sentence on its own,
#                      however few of them there are
#   max_unknown      — tokens wordfreq has no entry for (names, typos,
#                      tokeniser artefacts). Not evidence of tier fit either
#                      way, so they get their own small budget.
#
# Calibrated against the eval fixtures in tests/test_tier_gate.py: an ordinary
# A1/A2 sentence scores 0-1 out-of-band in all three languages, while the
# coffee-corpus C2 sentence scores 6 (zh), 8 (ja) and 10 (en). T6 is
# ungated — at the top tier there is no such thing as lexis that is too hard.

TIER_GATE_PROFILES: dict[str, dict[str, float | int]] = {
    'T1': {'soft_floor': 4.0, 'max_out_of_band': 2, 'hard_floor': 2.5, 'max_unknown': 1},
    'T2': {'soft_floor': 3.7, 'max_out_of_band': 3, 'hard_floor': 2.5, 'max_unknown': 2},
    'T3': {'soft_floor': 3.4, 'max_out_of_band': 3, 'hard_floor': 2.0, 'max_unknown': 3},
    'T4': {'soft_floor': 3.0, 'max_out_of_band': 5, 'hard_floor': 1.5, 'max_unknown': 4},
    'T5': {'soft_floor': 2.5, 'max_out_of_band': 7, 'hard_floor': 0.0, 'max_unknown': 6},
    'T6': {'soft_floor': 0.0, 'max_out_of_band': 999, 'hard_floor': 0.0, 'max_unknown': 999},
}

# Fallback profile for an unrecognised tier label — permissive, so a bad tier
# string degrades to "no screen" rather than rejecting every sentence.
TIER_GATE_DEFAULT_TIER: str = 'T3'

# A lemma's own Zipf → the tier its example sentences are held to. This is
# what "an A1 word" means operationally: *coffee* (4.9) is a T2 word, so its
# sentences are screened at T2's band. Ordered high-frequency first; first
# match wins.
LEMMA_ZIPF_TO_TIER: list[tuple[float, str]] = [
    (5.0, 'T1'),
    (4.3, 'T2'),
    (3.6, 'T3'),
    (3.0, 'T4'),
    (2.3, 'T5'),
]

# language_id → wordfreq / ISO 639-1 code. Mirrors difficulty.py's map.
TIER_GATE_LANG_CODES: dict[int, str] = {1: 'zh', 2: 'en', 3: 'ja'}


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


# ---------------------------------------------------------------------------
# dim_exercise_capabilities — the (language, type) routing matrix (TASK-504)
# ---------------------------------------------------------------------------
# This in-code constant MIRRORS migrations/dim_exercise_capabilities.sql — the
# DB table is the runtime source of truth (cached by DimensionService), and this
# copy is the authoritative *seed* + the offline-testable routing source. KEEP
# THE TWO IN SYNC: any row change here must be reflected in that migration (and
# re-applied live) and vice versa. compute_active_levels and the §4 inventory
# invariant test (tests/test_capability_matrix.py) read this constant so routing
# stays correct with no DB dependency (asset_pipeline runs before any cache load
# and must never silently fall back to all-9-levels for a known class).
#
# pos_classes sentinel 'all' matches every ratified class EXCEPT 'proper'
# (proper is never ladder-subscribed). A row applies to 'proper' only if it
# names it explicitly. ladder_level None = non-ladder (speed round, flashcards)
# — excluded from active_levels.

POS_ALL: str = 'all'

# type_code -> cognitive family (mirror of dim_exercise_types, plan §5 / TASK-503).
EXERCISE_TYPE_FAMILY: dict[str, str] = {
    'phonetic_recognition':    'form_recognition',
    'definition_match':        'form_recognition',
    'cloze_completion':        'meaning_recall',
    'cloze_typed':             'form_production',
    'morphology_slot':         'form_production',
    'classifier_match':        'form_production',
    'particle_selection':      'form_production',
    'counter_match':           'form_production',
    'collocation_gap_fill':    'collocation',
    'semantic_discrimination': 'semantic_discrimination',
    'spot_incorrect_sentence': 'semantic_discrimination',
    'collocation_repair':      'collocation',
    'jumbled_sentence':        'form_production',
    'hanzi_to_pinyin':         'form_recognition',
    'pinyin_to_hanzi':         'form_recognition',
    'tone_id_word':            'form_recognition',
    'kanji_to_reading':        'form_recognition',
    'reading_to_kanji':        'form_recognition',
    'synonym_antonym_match':   'semantic_discrimination',
    'word_family':             'form_production',
    'tl_nl_translation':       'meaning_recall',
    'nl_tl_translation':       'meaning_recall',
    'text_flashcard':          'meaning_recall',
    'listening_flashcard':     'form_recognition',
    'timed_speed_round':       'fluency',
}

# Compact spec: (type_code, language_ids, pos_classes, ladder_level, generator,
# requires, judge_key, is_enabled). Expanded to one row per language below.
_CAPABILITY_SPEC: list[tuple] = [
    ('phonetic_recognition', (2, 3), ('all',), 1, 'llm', ('p1_sentences', 'tts'), 'l1_distractor', True),
    ('phonetic_recognition', (1,), ('all',), 1, 'llm', ('p1_sentences', 'tts', 'pronunciation'), 'l1_distractor', True),
    ('definition_match', (1, 2, 3), ('all',), 2, 'deterministic', ('same_tier_senses',), None, True),
    ('cloze_completion', (1, 2, 3), ('all',), 3, 'llm', ('p1_sentences',), 'cloze', True),
    ('cloze_typed', (1, 2, 3), ('concrete', 'abstract', 'action', 'property'), 4, 'deterministic', ('cloze_asset',), None, True),
    ('morphology_slot', (2,), ('concrete', 'action', 'property'), 4, 'llm', ('morph_forms>=2',), 'sentence_validity', True),
    ('morphology_slot', (3,), ('action', 'property'), 4, 'llm', ('morph_forms>=2',), 'sentence_validity', True),
    ('morphology_slot', (1,), ('action', 'property'), 4, 'llm', ('morph_forms>=2',), 'sentence_validity', False),
    ('classifier_match', (1,), ('concrete',), 4, 'deterministic', ('classifier_dict',), None, True),
    ('particle_selection', (3,), ('concrete', 'abstract', 'action'), 4, 'llm', ('p1_sentences', 'tokenised_particles'), 'particle', True),
    ('counter_match', (3,), ('concrete',), 4, 'deterministic', ('counter_dict',), None, True),
    # L5/L8 collocation is enabled only where a grounding source exists. See
    # collocation_grounding.GROUNDING_SOURCES: EN has a bundled frequency list,
    # ZH has only `corpus_collocations` (40 rows), JA has nothing by design.
    # asset_pipeline drops L5 unless the pair is corpus_validated, so leaving
    # these enabled for ZH/JA made the collocation family permanently
    # unsatisfiable — and v_sense_family_coverage re-enqueued every such sense
    # for a full P1+P2+P3+judges regeneration, nightly, forever (audit B1).
    # Re-enable ZH when its collocation corpus is ingested.
    ('collocation_gap_fill', (2,), ('abstract', 'action', 'property'), 5, 'llm', ('primary_collocate',), 'collocation', True),
    ('collocation_gap_fill', (1, 3), ('abstract', 'action', 'property'), 5, 'llm', ('primary_collocate',), 'collocation', False),
    ('semantic_discrimination', (1, 2, 3), ('all',), 6, 'llm', ('p1_definition',), 'sentence_validity', True),
    ('spot_incorrect_sentence', (1, 2, 3), ('all',), 7, 'llm', ('p1_sentences',), 'sentence_validity', True),
    ('collocation_repair', (2,), ('abstract', 'action', 'property'), 8, 'llm', ('primary_collocate',), 'collocation', True),
    ('collocation_repair', (1, 3), ('abstract', 'action', 'property'), 8, 'llm', ('primary_collocate',), 'collocation', False),
    ('jumbled_sentence', (1, 2, 3), ('concrete', 'abstract', 'action', 'property'), 9, 'deterministic', ('p1_sentences',), None, True),
    ('hanzi_to_pinyin', (1,), ('all',), 1, 'deterministic', ('pronunciation',), None, True),
    ('pinyin_to_hanzi', (1,), ('all',), 1, 'deterministic', ('pronunciation',), None, True),
    ('tone_id_word', (1,), ('all',), 1, 'deterministic', ('pronunciation',), None, True),
    ('kanji_to_reading', (3,), ('all',), 1, 'deterministic', ('pronunciation',), None, True),
    ('reading_to_kanji', (3,), ('all',), 1, 'deterministic', ('pronunciation',), None, True),
    ('synonym_antonym_match', (1, 2, 3), ('abstract', 'action', 'property'), 6, 'llm', ('sense_embedding',), 'relation', True),
    ('word_family', (2,), ('abstract', 'action', 'property'), 4, 'llm', ('morph_forms>=2',), 'word_family', True),
    ('tl_nl_translation', (1, 3), ('all',), 3, 'llm', ('p1_sentences', 'nl_gloss'), 'translation_uniqueness', True),
    ('nl_tl_translation', (1, 3), ('all',), 3, 'llm', ('p1_sentences', 'nl_gloss'), 'translation_uniqueness', True),
    ('text_flashcard', (1, 2, 3), ('all',), None, 'deterministic', ('p1_sentences',), None, True),
    ('listening_flashcard', (1, 2, 3), ('all',), None, 'deterministic', ('p1_sentences', 'tts'), None, True),
    ('timed_speed_round', (1, 2, 3), ('all',), None, 'deterministic', (), None, True),
]

CAPABILITY_MATRIX: list[dict] = [
    {
        'language_id': lang,
        'type_code': type_code,
        'pos_classes': list(pos_classes),
        'ladder_level': ladder_level,
        'generator': generator,
        'requires': list(requires),
        'judge_key': judge_key,
        'is_enabled': is_enabled,
    }
    for (type_code, langs, pos_classes, ladder_level, generator, requires, judge_key, is_enabled)
    in _CAPABILITY_SPEC
    for lang in langs
]


def _pos_matches(semantic_class: str | None, pos_classes: list[str]) -> bool:
    """Whether a ratified `semantic_class` is covered by a row's pos_classes.

    The 'all' sentinel covers every class EXCEPT 'proper'; 'proper' is matched
    only when listed explicitly.
    """
    if semantic_class in pos_classes:
        return True
    return POS_ALL in pos_classes and semantic_class != 'proper'


def enabled_capabilities(language_id: int, semantic_class: str | None) -> list[dict]:
    """Enabled capability rows for a (language, ratified semantic_class) pair."""
    return [
        cap for cap in CAPABILITY_MATRIX
        if cap['language_id'] == language_id
        and cap['is_enabled']
        and _pos_matches(semantic_class, cap['pos_classes'])
    ]


def _fallback_active_levels(semantic_class: str | None) -> list[int]:
    """Legacy semantic_class-only routing — used only when the matrix has no
    rows for the requested language (unconfigured language / misconfiguration).
    Mirrors the pre-TASK-504 behaviour so a new language degrades gracefully
    rather than returning nothing."""
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


def compute_active_levels(
    semantic_class: str | None,
    language_id: int = 2,
) -> list[int]:
    """Return the active ladder levels for a word, derived from the capability
    matrix (TASK-504, plan §6.2).

    The level set is the sorted distinct `ladder_level` over all *enabled*
    capability rows for `language_id` whose `pos_classes` cover the word's
    ratified `semantic_class`. This makes routing language-aware (e.g. ZH
    concrete L4 = classifier_match, EN/JA L4 = morphology/particle/counter) while
    keeping the canonical level sets: `proper` -> [] (not subscribed),
    `function` -> [1,2,3,6,7] (no productive/collocation levels), `concrete` ->
    [1,2,3,4,6,7,9] (collocation L5/L8 dropped), everything else -> full 9.

    Unclassified / unrecognised semantic_class (NULL or a legacy value not in the
    ratified enum) returns the permissive full ladder — the pre-backfill default.
    If the matrix has no rows for the language at all, falls back to the legacy
    semantic_class-only routing.
    """
    if semantic_class not in SEMANTIC_CLASSES:
        # Pre-backfill / unrecognised: permissive full ladder.
        return list(ALL_LEVELS)

    if not any(cap['language_id'] == language_id for cap in CAPABILITY_MATRIX):
        return _fallback_active_levels(semantic_class)

    levels = {
        cap['ladder_level']
        for cap in enabled_capabilities(language_id, semantic_class)
        if cap['ladder_level'] is not None
    }
    return sorted(levels)


def requirements_met(requires: list[str] | tuple[str, ...], context: dict) -> bool:
    """Whether a capability row's ``requires`` tokens are satisfied by ``context``.

    Tokens come in two shapes:

      * ``name>=N``  — a numeric threshold, e.g. ``morph_forms>=2``.
      * ``name``     — a presence flag, e.g. ``p1_sentences``, ``pronunciation``.

    **Unknown tokens count as satisfied.** Most requirements (``tts``,
    ``p1_sentences``) can only be judged at render time, when the asset exists;
    this function runs at *planning* time and must not drop a level just
    because it cannot see that far ahead. It gates only on what the caller
    actually supplied in ``context``, keeping the failure mode "plan it and let
    the renderer skip it" rather than "silently generate nothing".

    Introduced for TASK-514/B5: L4 morphology was previously planned for every
    word and the pipeline hoped the model would return null for languages
    without inflection. Hope is not a gate.
    """
    for token in requires or ():
        if '>=' in token:
            name, _, threshold = token.partition('>=')
            name = name.strip()
            if name not in context:
                continue                        # not evaluable at planning time
            try:
                if float(context[name] or 0) < float(threshold):
                    return False
            except (TypeError, ValueError):
                return False
        else:
            name = token.strip()
            if name not in context:
                continue                        # not evaluable at planning time
            if not context[name]:
                return False
    return True


def active_levels_for_context(
    semantic_class: str | None,
    language_id: int,
    context: dict | None = None,
) -> list[int]:
    """``compute_active_levels`` narrowed by what this specific word supports.

    A level survives only if at least one enabled capability row for it has its
    ``requires`` satisfied. With an empty context this is exactly
    ``compute_active_levels`` — every requirement is unevaluable, so nothing is
    dropped.

    The motivating case: a ZH concrete noun has no morphological forms, so the
    only L4 row that could serve it (``morphology_slot``, needing
    ``morph_forms>=2``) cannot fire. Passing ``{'morph_forms': 0}`` drops L4
    from the plan instead of asking the model for morphology that does not
    exist and trusting it to answer null.
    """
    base = compute_active_levels(semantic_class, language_id)
    if not context:
        return base
    if semantic_class not in SEMANTIC_CLASSES:
        return base
    if not any(cap['language_id'] == language_id for cap in CAPABILITY_MATRIX):
        return base

    supported = {
        cap['ladder_level']
        for cap in enabled_capabilities(language_id, semantic_class)
        if cap['ladder_level'] is not None
        and requirements_met(cap.get('requires', ()), context)
    }
    return [lv for lv in base if lv in supported]


# Which capability type_code each Prompt-3 level asks the model to produce.
# P3 is one LLM call covering L4/L7/L8, so gating it has to happen per *type*,
# not per level: a level can legitimately survive on a capability this prompt
# does not own. ZH `concrete` keeps L4 via `classifier_match` + `cloze_typed`
# (both deterministic), and the old level-only gate therefore still asked P3
# for morphology — which is how invented Chinese "inflections" reached the
# corpus. See TASK-514/B5.
PROMPT3_TYPE_FOR_LEVEL: dict[int, str] = {
    4: 'morphology_slot',
    7: 'spot_incorrect_sentence',
    8: 'collocation_repair',
}


def capability_context_from_core(core_asset: dict) -> dict:
    """Build a capability ``requires`` context from a prompt1_core asset.

    Only includes what P1 has actually established. Requirements this can't
    speak to (``tts``, ``same_tier_senses``, ``classifier_dict``) are
    deliberately absent so :func:`requirements_met` treats them as satisfied
    and leaves the decision to the renderer — see its docstring.

    Shared by the generation pipeline and the exercise renderer so both sides
    gate on identical facts.
    """
    forms = (core_asset or {}).get('morphological_forms') or []
    return {
        'morph_forms':   len(forms) if isinstance(forms, (list, tuple, dict)) else 0,
        'pronunciation': bool((core_asset or {}).get('pronunciation')),
        'p1_definition': bool((core_asset or {}).get('definition')),
        'p1_sentences':  bool((core_asset or {}).get('sentences')),
    }


def type_is_available(
    type_code: str,
    language_id: int,
    semantic_class: str | None,
    context: dict | None = None,
) -> bool:
    """Whether ``type_code`` can actually be generated for this word.

    True when at least one *enabled* capability row for (language_id,
    semantic_class) carries this ``type_code`` and has its ``requires``
    satisfied by ``context``. Unknown requirement tokens count as satisfied —
    see :func:`requirements_met`.

    Permissive in exactly the two places the rest of this module is: an
    unrecognised / NULL ``semantic_class`` (pre-backfill) and a language with
    no matrix rows at all both return True, so a misconfiguration degrades to
    the old behaviour instead of silently generating nothing.
    """
    if semantic_class not in SEMANTIC_CLASSES:
        return True
    if not any(cap['language_id'] == language_id for cap in CAPABILITY_MATRIX):
        return True
    return any(
        cap['type_code'] == type_code
        and requirements_met(cap.get('requires', ()), context or {})
        for cap in enabled_capabilities(language_id, semantic_class)
    )


def prompt3_levels_for_context(
    active_levels: list[int],
    semantic_class: str | None,
    language_id: int,
    context: dict | None = None,
) -> list[int]:
    """The P3 levels worth asking the model for, gated per exercise *type*.

    ``active_levels`` is the word's planned ladder (already narrowed by
    :func:`active_levels_for_context`); this narrows further to the subset
    whose P3-owned type can actually fire. Levels outside
    :data:`PROMPT3_TYPE_FOR_LEVEL` pass through untouched so a future P3
    level is never dropped merely for being unmapped.

    A ZH concrete noun keeps L4 in ``active_levels`` (classifier_match) but
    drops out here, because ``morphology_slot`` has no enabled ZH row.
    """
    result = []
    for level in sorted(lv for lv in active_levels if lv in PROMPT3_LEVELS):
        type_code = PROMPT3_TYPE_FOR_LEVEL.get(level)
        if type_code is None:
            result.append(level)
            continue
        if type_is_available(type_code, language_id, semantic_class, context):
            result.append(level)
    return result


def required_families(language_id: int, semantic_class: str | None) -> set[str]:
    """The cognitive families a (language, semantic_class) word must be able to
    practise — derived from its active ladder levels (§4 inventory contract).
    The capability matrix must supply >=1 enabled type per required family."""
    return {
        LADDER_LEVELS[lv]['family']
        for lv in compute_active_levels(semantic_class, language_id)
        if lv in LADDER_LEVELS
    }


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
    '5': 'furigana',  # JA P1: kana reading for this sentence occurrence (NULL/absent for ZH/EN)
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

# The split single-type ladder prompts (TASK-537) use the same numeric-key idea
# but a 0-based numbering, because their contract reserves two positions
# type-wide: 0 is always the option array and 9 is always the error escape. The
# P2 map above stays 1-based — its prompts are live and its stored assets are
# bound to that numbering, so aligning the two would mean re-authoring P2 for
# no gain. ``schemas/_shared.OPTION_KEY_LEGEND`` is the authoritative copy of
# what these indices mean; this map is how the generators spend it.
LADDER_OPTION_KEY_MAP: dict[str, str] = {
    '0': 'text',
    '1': 'is_correct',
    '2': 'explanation',
    '3': 'part_of_speech',
}


def remap_keys(data: dict | list, key_map: dict[str, str]) -> dict | list:
    """Recursively remap numeric string keys to descriptive keys."""
    if isinstance(data, list):
        return [remap_keys(item, key_map) if isinstance(item, (dict, list)) else item
                for item in data]
    if isinstance(data, dict):
        return {key_map.get(k, k): v for k, v in data.items()}
    return data
