"""What a language still needs before it can go live: the plug-in points beside the registry.

The registry (services/language_registry.py) says a language exists. Each
check below is one place where the app needs something written for that
language. ``report('it')`` runs them all; ``python scripts/check_language.py it``
prints the result. Checks read code and files only; what lives in the database
is listed by ``DATABASE_STEPS`` for a person to verify.

tests/test_language_readiness.py requires every active language to pass every
required check, so a check that drifts from the code fails there.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable, Optional

from services import language_registry
from services.language_registry import Language

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED = 'required'      # the app fails or silently misbehaves for the language without it
OPTIONAL = 'optional'      # there is a working default; quality or a feature is missing


@dataclass(frozen=True)
class Check:
    key: str
    level: str
    what: str                      # what must exist
    where: str                     # the file to edit
    test: Callable[[Language], Optional[str]]   # None when satisfied, else what is missing


@dataclass(frozen=True)
class Result:
    key: str
    level: str
    ok: bool
    what: str
    where: str
    detail: str


def _vocab_processor(lang):
    from services.vocabulary.pipeline import _PROCESSOR_CLASSES
    return None if lang.code in _PROCESSOR_CLASSES else f'no processor class for {lang.code!r}'


def _nlp_metadata(lang):
    from services.vocabulary.config import _NLP_METADATA
    return None if lang.code in _NLP_METADATA else f'no NLPMetadata for {lang.code!r}'


def _exercise_processor(lang):
    from services.exercise_generation.language_processor import PROCESSOR_CLASSES
    return None if lang.code in PROCESSOR_CLASSES else f'no LanguageProcessor for {lang.code!r}'


def _corpus_tokenizer(lang):
    from services.corpus.tokenizers import TOKENIZER_CLASSES
    return None if lang.code in TOKENIZER_CLASSES else f'no LanguageTokenizer for {lang.code!r}'


def _capabilities(lang):
    from services.vocabulary_ladder.config import _CAPABILITY_SPEC
    rows = [row for row in _CAPABILITY_SPEC if lang.id in row[1]]
    return None if rows else 'no exercise type lists this language id (it would get the legacy full ladder)'


def _validation_profile(lang):
    from services.vocabulary_ladder.config import LANGUAGE_VALIDATION_PROFILES
    return None if lang.id in LANGUAGE_VALIDATION_PROFILES else 'no profile: the merged English + Chinese default applies'


def _wordfreq(lang):
    return None if lang.wordfreq else 'Language.wordfreq is not set: no frequency scores or tier gate'


def _langdetect(lang):
    return None if lang.langdetect else 'Language.langdetect is empty: wrong-language output is not detected'


def _language_detection(lang):
    path = os.path.join(ROOT, 'services', 'vocabulary', 'language_detection.py')
    src = open(path, encoding='utf-8').read()
    return None if f"'{lang.code}'" in src else 'no branch: definitions in the wrong language pass unchecked'


def _i18n_name(lang):
    missing = []
    d = os.path.join(ROOT, 'static', 'i18n')
    for name in sorted(os.listdir(d)):
        if name.endswith('.json'):
            bundle = json.load(open(os.path.join(d, name), encoding='utf-8'))
            if f'lang_select.name_{lang.code}' not in bundle:
                missing.append(name)
    return None if not missing else f'lang_select.name_{lang.code} missing in ' + ', '.join(missing)


def _tier_thresholds(lang):
    from services.tier_classifier import SCORE_THRESHOLDS
    return None if lang.code in SCORE_THRESHOLDS else 'no fitted thresholds: DEFAULT_THRESHOLDS apply'


def _collocations(lang):
    from services.vocabulary_ladder.collocation_grounding import GROUNDING_SOURCES
    return None if GROUNDING_SOURCES.get(lang.id) else 'no grounding source: collocation levels must stay disabled'


def _cheat_sheet(lang):
    path = os.path.join(ROOT, '.claude', 'skills', 'fat-seed-authoring', 'cheatsheets', f'{lang.code}.md')
    return None if os.path.exists(path) else 'no fat-seed cheat sheet: the authoring pipeline refuses to start'


def _web_fonts(lang):
    if not lang.is_cjk:
        return None
    return None if lang.web_font_sans and lang.web_font_serif else 'CJK language without web fonts'


CHECKS: tuple = (
    Check('vocabulary_processor', REQUIRED, 'tokeniser / lemmatiser for vocabulary extraction',
          'services/vocabulary/pipeline.py _PROCESSOR_CLASSES (+ processors/<language>.py)', _vocab_processor),
    Check('nlp_metadata', REQUIRED, 'NLP tool, model and content parts of speech',
          'services/vocabulary/config.py _NLP_METADATA', _nlp_metadata),
    Check('exercise_processor', REQUIRED, 'sentence splitting and chunking for exercises',
          'services/exercise_generation/language_processor.py PROCESSOR_CLASSES', _exercise_processor),
    Check('capabilities', REQUIRED, 'which exercise types the language has',
          'services/vocabulary_ladder/config.py _CAPABILITY_SPEC (+ dim_exercise_capabilities rows)', _capabilities),
    Check('validation_profile', REQUIRED, 'parts of speech, IPA and form rules for generated cores',
          'services/vocabulary_ladder/config.py LANGUAGE_VALIDATION_PROFILES', _validation_profile),
    Check('wordfreq', REQUIRED, 'frequency data code', 'services/language_registry.py Language.wordfreq', _wordfreq),
    Check('i18n_name', REQUIRED, "the language's name in every UI bundle",
          'static/i18n/*.json lang_select.name_<code>', _i18n_name),
    Check('web_fonts', REQUIRED, 'web fonts for a CJK script',
          'services/language_registry.py Language.web_font_sans / web_font_serif', _web_fonts),
    Check('corpus_tokenizer', OPTIONAL, 'tokeniser for corpus ingestion and collocation mining',
          'services/corpus/tokenizers.py TOKENIZER_CLASSES', _corpus_tokenizer),
    Check('langdetect', OPTIONAL, 'langdetect codes for the output cleaner',
          'services/language_registry.py Language.langdetect', _langdetect),
    Check('language_detection', OPTIONAL, 'script heuristic for definitions',
          'services/vocabulary/language_detection.py', _language_detection),
    Check('tier_thresholds', OPTIONAL, 'fitted difficulty thresholds',
          'services/tier_classifier.py SCORE_THRESHOLDS (scripts/fit_tier_thresholds.py)', _tier_thresholds),
    Check('collocations', OPTIONAL, 'collocation grounding source',
          'services/vocabulary_ladder/collocation_grounding.py GROUNDING_SOURCES', _collocations),
    Check('cheat_sheet', OPTIONAL, 'fat-seed authoring cheat sheet',
          '.claude/skills/fat-seed-authoring/cheatsheets/<code>.md', _cheat_sheet),
)

# Not checkable from the repository: rows in the live database.
DATABASE_STEPS: tuple = (
    'dim_languages: one row with this id and code, tts_voice_ids (two voices), tts_speed',
    'dim_exercise_capabilities: one row per exercise type (mirror of _CAPABILITY_SPEC)',
    'prompt_templates: rows per task_name for this language_id (ladder generators and judges have no fallback)',
    'dim_study_plan_templates: three rows',
    'SQL functions with per-language branches: calibration_placement_rpcs.sql, knowledge_calibration_inputs.sql',
)


def report(ref) -> list:
    """Every check for a language (planned ones included), required first."""
    lang = language_registry.get(ref, include_planned=True)
    out = []
    for check in CHECKS:
        try:
            missing = check.test(lang)
        except Exception as exc:        # a check must never take the report down with it
            missing = f'check failed: {type(exc).__name__}: {exc}'
        out.append(Result(check.key, check.level, missing is None, check.what, check.where, missing or ''))
    return out


def blockers(ref) -> list:
    """The required checks a language fails."""
    return [r for r in report(ref) if r.level == REQUIRED and not r.ok]
