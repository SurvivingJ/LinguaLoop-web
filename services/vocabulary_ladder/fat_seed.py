"""Fat-seed authoring: one named-field JSON document per word sense.

The cheap/fast sibling of the staged CSV chain (``stage_runner``). Instead of
answering each live prompt in its numeric contract, stage by stage, a subagent
writes one document per sense in descriptive field names::

    {"sense_id": 123, "lemma": "…",
     "core": {…prompt1_core fields…},
     "variants": {"A": {"level_1": {…}, …, "synonym_antonym_match": {…}},
                  "B": {…}}}

or ``{"sense_id": 123, "lemma": "…", "skip": "proper noun"}``.

This module turns that document back into exactly the raw numeric-keyed
answers ``scripts/upload_exercises.py`` consumes, so every existing gate
(PROMPT1 remap, VocabAssetValidator, the split/typed schema gates, the tier
screen, collocate grounding) runs unchanged. Nothing here validates content;
it only translates shape and reports blocks that are missing or surplus
against the level plan ``export_exercise_worklist.build_exercise_item``
derives from the core.

Pure functions: no database, no LLM. The CLI is ``scripts/fat_seed_runner.py``.
"""

from __future__ import annotations

import json

from services.vocabulary_ladder.config import (
    MORPH_FORM_KEY_MAP, OPTION_KEY_MAP, PROMPT1_KEY_MAP, SENTENCE_KEY_MAP,
)
from services.exercise_generation.schemas._shared import (
    ERROR_ESCAPE_KEY, OPTION_KEY_LEGEND, OPTIONS_KEY,
)

# Descriptive name -> numeric key, the inverse of each remap table.
_P1 = {v: k for k, v in PROMPT1_KEY_MAP.items()}
_SENT = {v: k for k, v in SENTENCE_KEY_MAP.items()}
_MORPH = {v: k for k, v in MORPH_FORM_KEY_MAP.items()}
_P2_OPT = {v: k for k, v in OPTION_KEY_MAP.items()}          # 1-based (P2/P3)
_SPLIT_OPT = {v: k for k, v in OPTION_KEY_LEGEND.items()}    # 0-based (L4/L8/typed)

P2_OPTION_LEVELS = (1, 3, 5)
DECLINED = 'declined'

# The escape token each declinable block uses (key 9 in its live contract).
ESCAPE_TOKENS: dict[str, str] = {
    'level_4': 'no_inflection',
    'level_8': 'no_collocation',
    'synonym_antonym_match': 'no_relation',
    'word_family': 'no_family',
    'particle_selection': 'no_particle_slot',
}

# Top-level fields of each typed block, in its live numeric contract
# (key 0 is always the option array).
_TYPED_FIELDS: dict[str, dict[str, str]] = {
    'synonym_antonym_match': {'relation': '1'},
    'word_family': {'stem': '1'},
    'particle_selection': {'blanked_particle': '1', 'error_tags': '2'},
}


class FatSeedError(ValueError):
    """The document cannot be translated (not a content problem)."""


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def core_to_raw(core: dict) -> dict:
    """Named ``core`` -> the numeric P1 answer ``CoreAssetGenerator`` remaps.

    Unknown fields are dropped rather than passed through: the P1 remap only
    reads mapped keys, so a stray field would vanish anyway, silently.
    ``sentence_source`` is never taken from the author — upload derives it.
    """
    if not isinstance(core, dict):
        raise FatSeedError('core must be an object')
    raw: dict = {}
    for name, value in core.items():
        key = _P1.get(name)
        if key is None:
            continue
        if name == 'sentences' and isinstance(value, list):
            value = [_rekey(s, _SENT, drop=('sentence_source',)) for s in value]
        elif name == 'morphological_forms' and isinstance(value, list):
            value = [_rekey(f, _MORPH) for f in value]
        raw[key] = value
    return raw


def _rekey(obj, table: dict[str, str], drop: tuple[str, ...] = ()):
    if not isinstance(obj, dict):
        return obj
    return {table.get(k, k): v for k, v in obj.items() if k not in drop}


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------

def expected_blocks(variant_plan: dict) -> list[str]:
    """Block names a plan variant (from ``build_exercise_item``) requires."""
    blocks = [f'level_{lv}' for lv in (variant_plan.get('p2') or {}).get('levels', [])]
    blocks += [f'level_{lv}' for lv in (variant_plan.get('p3') or {}).get('levels', [])]
    blocks += [f'level_{lv}' for lv in (4, 8) if f'l{lv}' in variant_plan]
    blocks += sorted(variant_plan.get('typed') or {})
    return blocks


def is_declined(block) -> bool:
    return isinstance(block, dict) and bool(block.get(DECLINED))


def _escape(name: str, block: dict, errors: list[str]) -> dict | None:
    token = block.get(DECLINED)
    expected = ESCAPE_TOKENS.get(name)
    if expected is None:
        errors.append(f'{name}: cannot be declined — write the block')
        return None
    if token not in (True, expected):
        errors.append(f'{name}: declined token must be {expected!r}, got {token!r}')
        return None
    return {ERROR_ESCAPE_KEY: expected}


def _options(block: dict, table: dict[str, str], name: str,
             errors: list[str]) -> list | None:
    opts = block.get('options')
    if not isinstance(opts, list):
        errors.append(f'{name}: options must be a list')
        return None
    return [_rekey(o, table) for o in opts]


def variant_to_raw(doc_variant: dict, variant_plan: dict
                   ) -> tuple[dict, list[str], list[str]]:
    """One authored variant -> the upload answer for that variant.

    Returns ``(answer, errors, surplus)``. ``answer`` has the shape
    ``prepare_exercises`` reads: ``{"p2": {...}, "p3": {...}, "l4": {...},
    "l8": {...}, "typed": {code: {...}}}``, each in its live numeric contract.
    ``errors`` are required blocks that are missing or untranslatable;
    ``surplus`` are authored blocks the plan does not ask for (dropped).
    """
    doc_variant = doc_variant if isinstance(doc_variant, dict) else {}
    errors: list[str] = []
    answer: dict = {}
    wanted = expected_blocks(variant_plan)
    surplus = sorted(set(doc_variant) - set(wanted))

    def block(name):
        b = doc_variant.get(name)
        if not isinstance(b, dict):
            errors.append(f'{name}: missing')
            return None
        return b

    p2_levels = (variant_plan.get('p2') or {}).get('levels', [])
    if p2_levels:
        p2: dict = {}
        for lv in p2_levels:
            b = block(f'level_{lv}')
            if b is None:
                continue
            if is_declined(b):
                _escape(f'level_{lv}', b, errors)
                continue
            if lv == 6:
                wrong = b.get('wrong_sentences')
                if not isinstance(wrong, list):
                    errors.append('level_6: wrong_sentences must be a list')
                    continue
                p2['6'] = {
                    '1': b.get('correct_sentence_index'),
                    '2': [{'1': w.get('text', ''), '2': w.get('explanation', '')}
                          if isinstance(w, dict) else w for w in wrong],
                }
            else:
                opts = _options(b, _P2_OPT, f'level_{lv}', errors)
                if opts is not None:
                    p2[str(lv)] = opts
        answer['p2'] = p2

    p3_levels = (variant_plan.get('p3') or {}).get('levels', [])
    if p3_levels:
        p3: dict = {}
        if 7 in p3_levels:
            b = block('level_7')
            if b is not None and is_declined(b):
                _escape('level_7', b, errors)
            elif b is not None:
                p3['7'] = {
                    '1': b.get('incorrect_sentence', ''),
                    '2': b.get('corrected_sentence', ''),
                    '3': b.get('error_description', ''),
                    '4': b.get('correct_sentence_indices',
                               variant_plan['p3'].get('l7_correct_indices')),
                }
        answer['p3'] = p3

    for lv, extra in ((4, {'base_form': '1', 'form_label': '2'}),
                      (8, {'error_collocate': '1'})):
        spec = variant_plan.get(f'l{lv}')
        if not spec:
            continue
        name = f'level_{lv}'
        b = block(name)
        if b is None:
            continue
        if is_declined(b):
            raw = _escape(name, b, errors)
        else:
            opts = _options(b, _SPLIT_OPT, name, errors)
            raw = None if opts is None else {OPTIONS_KEY: opts}
            if raw is not None:
                for field, key in extra.items():
                    raw[key] = b.get(field)
                if lv == 4:
                    # The live L4 contract carries the sentence index; the
                    # plan fixes it, so the author never chooses it.
                    raw['3'] = spec['sentence_index']
        if raw is not None:
            answer[f'l{lv}'] = raw

    typed_plan = variant_plan.get('typed')
    if typed_plan is not None:
        typed: dict = {}
        for code in sorted(typed_plan):
            b = block(code)
            if b is None:
                continue
            if is_declined(b):
                raw = _escape(code, b, errors)
            else:
                opts = _options(b, _SPLIT_OPT, code, errors)
                raw = None if opts is None else {OPTIONS_KEY: opts}
                if raw is not None:
                    for field, key in _TYPED_FIELDS.get(code, {}).items():
                        if field in b:
                            raw[key] = b[field]
            if raw is not None:
                typed[code] = raw
        answer['typed'] = typed

    return answer, errors, surplus


def exercise_answer(doc: dict, item: dict) -> tuple[dict, list[str], list[str]]:
    """Both variants -> ``{"sense_id", "A": {...}, "B": {...}}`` for upload."""
    variants = doc.get('variants') if isinstance(doc.get('variants'), dict) else {}
    entry: dict = {'sense_id': item['sense_id']}
    errors: list[str] = []
    surplus: list[str] = []
    for v, variant_plan in item['variants'].items():
        ans, errs, extra = variant_to_raw(variants.get(v) or {}, variant_plan)
        entry[v] = ans
        errors += [f'[{v}] {e}' for e in errs]
        surplus += [f'[{v}] {e}' for e in extra]
    return entry, errors, surplus


# ---------------------------------------------------------------------------
# Review bookkeeping
# ---------------------------------------------------------------------------

def canon(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def changed_paths(before, after, path: str = '') -> list[str]:
    """Leaf paths that differ between two documents (for review records)."""
    if isinstance(before, dict) and isinstance(after, dict):
        out: list[str] = []
        for k in sorted(set(before) | set(after), key=str):
            out += changed_paths(before.get(k), after.get(k), f'{path}.{k}' if path else str(k))
        return out
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        out = []
        for i, (b, a) in enumerate(zip(before, after)):
            out += changed_paths(b, a, f'{path}[{i}]')
        return out
    return [] if canon(before) == canon(after) else [path or '(root)']
