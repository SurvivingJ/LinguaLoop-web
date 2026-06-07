"""Configuration for the offline classifier-curation pipeline.

All model slugs are OpenRouter strings and are env-overridable so they stay
swappable without code changes (mirrors services/llm_service.py conventions).
"""

import os

LANGUAGE_ID_ZH = 1

# OpenRouter model slugs.
GEN_MODEL = os.getenv('CLASSIFIER_GEN_MODEL', 'qwen/qwen3.7-plus')
JUDGE_MODEL = os.getenv('CLASSIFIER_JUDGE_MODEL', GEN_MODEL)

# llm_calls observability tag.
PIPELINE = 'classifier_curation'

# How many candidate nouns to request per classifier.
TARGET_NOUNS = int(os.getenv('CLASSIFIER_TARGET_NOUNS', '16'))

# Judge Likert (1-5): nouns rated >= this are accepted into the review JSON.
JUDGE_ACCEPT_THRESHOLD = int(os.getenv('CLASSIFIER_JUDGE_THRESHOLD', '4'))

# Fixed semantic-group vocabulary the classify step must choose from. Mirrors
# dim_classifier_distractor_groups: the original 12 plus the 4 added by
# migrations/add_classifier_groups.sql.
GROUPS = [
    'general', 'people', 'animals', 'long_thin', 'flat', 'bound', 'vehicles',
    'containers', 'places', 'garments', 'events', 'plants',
    'abstract', 'small_round', 'strands', 'sections',
]

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(_ROOT, 'data', 'classifier_curation')
APPROVED_FILE = os.path.join(OUTPUT_DIR, 'approved_curation.json')
