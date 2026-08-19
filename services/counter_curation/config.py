"""Configuration for the offline counter-curation pipeline.

All model slugs are OpenRouter strings and are env-overridable so they stay
swappable without code changes (mirrors services/classifier_curation/config.py).
"""

import os

LANGUAGE_ID_JA = 3

# OpenRouter model slugs. Qwen handles CJK morphology and the counter's
# euphonic readings noticeably better than the cheap Western-tuned models, and
# it is the model the Mandarin sibling already uses.
GEN_MODEL = os.getenv('COUNTER_GEN_MODEL', 'qwen/qwen3.7-plus')
JUDGE_MODEL = os.getenv('COUNTER_JUDGE_MODEL', GEN_MODEL)

# llm_calls observability tag.
PIPELINE = 'counter_curation'

# How many candidate nouns to request per counter. Higher than the Mandarin
# default of 16 because the acceptance bar is >= 10 *accepted* nouns per
# counter, and the judge rejects a meaningful share.
TARGET_NOUNS = int(os.getenv('COUNTER_TARGET_NOUNS', '20'))

# Judge Likert (1-5): nouns rated >= this are accepted into the review JSON.
JUDGE_ACCEPT_THRESHOLD = int(os.getenv('COUNTER_JUDGE_THRESHOLD', '4'))

# Fixed semantic-group vocabulary the classify step must choose from. Mirrors
# GROUPS in scripts/build_counter_dictionary.py, which owns the table seed —
# a group invented here would fail the pair insert's FK.
GROUPS = [
    'general', 'people', 'animals', 'long_thin', 'flat_thin', 'bound_volumes',
    'machines', 'vessels', 'buildings', 'clothing', 'correspondence',
    'occurrences', 'food_portions', 'groupings',
]

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(_ROOT, 'data', 'counter_curation')
APPROVED_FILE = os.path.join(OUTPUT_DIR, 'approved_curation.json')
