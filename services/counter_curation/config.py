"""Configuration for the offline counter-curation pipeline.

All model slugs are OpenRouter strings and are env-overridable so they stay
swappable without code changes (mirrors services/classifier_curation/config.py).
"""

from services.measure_curation import curation_settings

LANGUAGE_ID_JA = 3

# OpenRouter model slugs. Qwen handles CJK morphology and the counter's
# euphonic readings noticeably better than the cheap Western-tuned models, and
# it is the model the Mandarin sibling already uses.
_settings = curation_settings('counter', target_nouns=20)
GEN_MODEL = _settings.GEN_MODEL
JUDGE_MODEL = _settings.JUDGE_MODEL

# llm_calls observability tag.
PIPELINE = _settings.PIPELINE

# How many candidate nouns to request per counter. Higher than the Mandarin
# default of 16 because the acceptance bar is >= 10 *accepted* nouns per
# counter, and the judge rejects a meaningful share.
TARGET_NOUNS = _settings.TARGET_NOUNS

# Judge Likert (1-5): nouns rated >= this are accepted into the review JSON.
JUDGE_ACCEPT_THRESHOLD = _settings.JUDGE_ACCEPT_THRESHOLD

# Fixed semantic-group vocabulary the classify step must choose from. Mirrors
# GROUPS in scripts/build_counter_dictionary.py, which owns the table seed —
# a group invented here would fail the pair insert's FK.
GROUPS = [
    'general', 'people', 'animals', 'long_thin', 'flat_thin', 'bound_volumes',
    'machines', 'vessels', 'buildings', 'clothing', 'correspondence',
    'occurrences', 'food_portions', 'groupings',
]

OUTPUT_DIR = _settings.OUTPUT_DIR
APPROVED_FILE = _settings.APPROVED_FILE
