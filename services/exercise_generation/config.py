# services/exercise_generation/config.py

from typing import FrozenSet

# --- Exercise type registry ---------------------------------------------------

ALL_EXERCISE_TYPES: list[str] = [
    'cloze_completion', 'jumbled_sentence', 'tl_nl_translation', 'nl_tl_translation',
    'collocation_gap_fill', 'text_flashcard', 'listening_flashcard',
    'semantic_discrimination', 'collocation_repair', 'spot_incorrect_sentence',
    'spot_incorrect_part', 'timed_speed_round', 'odd_one_out', 'context_spectrum',
    'odd_collocation_out', 'verb_noun_match',
]

# Exercise types that require an MCQ options array
MCQ_TYPES: FrozenSet[str] = frozenset({
    'cloze_completion', 'tl_nl_translation', 'collocation_gap_fill',
    'odd_one_out', 'odd_collocation_out',
})

# Expected option counts per MCQ type
EXPECTED_OPTION_COUNT: dict[str, int] = {
    'cloze_completion':     4,
    'tl_nl_translation':    3,
    'collocation_gap_fill': 4,
    'odd_one_out':          4,
    'odd_collocation_out':  4,
}

# --- Required JSONB fields per type ------------------------------------------

REQUIRED_FIELDS_BY_TYPE: dict[str, list[str]] = {
    'cloze_completion':        ['sentence_with_blank', 'correct_answer', 'options',
                                'explanation', 'distractor_tags'],
    'jumbled_sentence':        ['chunks', 'correct_ordering', 'original_sentence'],
    'tl_nl_translation':       ['tl_sentence', 'correct_nl', 'options'],
    'nl_tl_translation':       ['nl_sentence', 'primary_tl', 'grading_notes'],
    'text_flashcard':          ['front_sentence', 'highlight_word', 'back_sentence',
                                'word_of_interest', 'sense_id'],
    'listening_flashcard':     ['front_audio_url', 'back_sentence', 'word_of_interest', 'sense_id'],
    'semantic_discrimination': ['sentences', 'explanation'],
    'odd_one_out':             ['items', 'odd_index', 'shared_property', 'explanation'],
    'context_spectrum':        ['variants', 'exercise_context', 'correct_variant_index'],
    'collocation_gap_fill':    ['sentence', 'correct', 'options', 'collocation'],
    'collocation_repair':      ['sentence_with_error', 'error_word', 'correct_word'],
    'odd_collocation_out':     ['head_word', 'collocations', 'odd_index', 'explanation'],
    'verb_noun_match':         ['verbs', 'nouns', 'valid_pairs'],
    'spot_incorrect_sentence': ['sentences'],
    'spot_incorrect_part':     ['sentence', 'parts'],
}

# --- Distribution targets per grammar pattern --------------------------------

GRAMMAR_DISTRIBUTION: dict[str, int] = {
    'cloze_completion':        150,
    'jumbled_sentence':        120,
    'tl_nl_translation':        80,
    'nl_tl_translation':        60,
    'collocation_gap_fill':     80,
    'text_flashcard':           80,
    'listening_flashcard':      80,
    'semantic_discrimination':  60,
    'collocation_repair':       50,
    'spot_incorrect_sentence':  40,
    'spot_incorrect_part':      30,
    'timed_speed_round':        50,
    'odd_one_out':              40,
    'context_spectrum':         30,
    'odd_collocation_out':      30,
    'verb_noun_match':          20,
}

VOCABULARY_DISTRIBUTION: dict[str, int] = {
    'text_flashcard':          3,
    'listening_flashcard':     3,
    'cloze_completion':        5,
    'tl_nl_translation':       3,
    'semantic_discrimination': 2,
}

COLLOCATION_DISTRIBUTION: dict[str, int] = {
    'collocation_gap_fill':  5,
    'collocation_repair':    3,
    'odd_collocation_out':   3,
    'text_flashcard':        2,
    'verb_noun_match':       1,
}

# --- Sentence pool thresholds ------------------------------------------------
MIN_TRANSCRIPT_SENTENCES: int = 80
DEFAULT_SENTENCE_TARGET:  int = 200
LLM_BATCH_SIZE:           int = 25

# --- CEFR -> IRT difficulty seed ----------------------------------------------
CEFR_TO_IRT: dict[str, float] = {
    'A1': -2.0, 'A2': -1.0, 'B1': 0.0, 'B2': 0.5, 'C1': 1.0, 'C2': 2.0,
}

# --- Grammar pattern heuristics (for transcript mining) ---------------------
PATTERN_HEURISTICS: dict[str, str] = {
    'en_present_perfect_cont': r'\b(has|have)\s+been\s+\w+ing\b',
    'en_passive_voice_simple':  r'\b(is|was|are|were|been)\s+\w+ed\b',
    'en_reported_speech':       r'\b(said|told|asked|thought)\s+(that|if|whether)\b',
    'cn_ba_construction':       r'把',
    'cn_bei_passive':           r'被',
    'jp_te_form_progressive':   r'ている|ています',
    'jp_keigo_sonkeigo':        r'ていらっしゃ|いらっしゃ|ございます',
}

# --- Language IDs (mirrors dim_languages) ------------------------------------
LANG_CHINESE:  int = 1
LANG_ENGLISH:  int = 2
LANG_JAPANESE: int = 3

# --- Phase membership (mirrors spec section 1.17) ----------------------------
PHASE_MAP: dict[str, list[str]] = {
    'A': ['text_flashcard', 'listening_flashcard', 'cloze_completion'],
    'B': ['jumbled_sentence', 'spot_incorrect_sentence', 'spot_incorrect_part',
          'tl_nl_translation', 'nl_tl_translation'],
    'C': ['semantic_discrimination', 'collocation_gap_fill', 'collocation_repair',
          'odd_collocation_out', 'odd_one_out'],
    'D': ['verb_noun_match', 'context_spectrum', 'timed_speed_round'],
}
