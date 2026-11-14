"""Configuration for the offline classifier-curation pipeline.

All model slugs are OpenRouter strings and are env-overridable so they stay
swappable without code changes (mirrors services/llm_service.py conventions).
"""

from services.measure_curation import curation_settings

LANGUAGE_ID_ZH = 1

# OpenRouter model slugs.
_settings = curation_settings('classifier', target_nouns=16)
GEN_MODEL = _settings.GEN_MODEL
JUDGE_MODEL = _settings.JUDGE_MODEL

# llm_calls observability tag.
PIPELINE = _settings.PIPELINE

# How many candidate nouns to request per classifier.
TARGET_NOUNS = _settings.TARGET_NOUNS

# Judge Likert (1-5): nouns rated >= this are accepted into the review JSON.
JUDGE_ACCEPT_THRESHOLD = _settings.JUDGE_ACCEPT_THRESHOLD

# Fixed semantic-group vocabulary the classify step must choose from. Mirrors
# dim_classifier_distractor_groups: the original 12 plus the 4 added by
# migrations/add_classifier_groups.sql.
GROUPS = [
    'general', 'people', 'animals', 'long_thin', 'flat', 'bound', 'vehicles',
    'containers', 'places', 'garments', 'events', 'plants',
    'abstract', 'small_round', 'strands', 'sections',
]

OUTPUT_DIR = _settings.OUTPUT_DIR
APPROVED_FILE = _settings.APPROVED_FILE
