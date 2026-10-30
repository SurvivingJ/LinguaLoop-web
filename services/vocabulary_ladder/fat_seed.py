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

import difflib
import json
import os
import re

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
# level_1 has no escape in the live P2 contract: a declined level_1 is left
# out of the P2 asset and listed in the answer's ``declined_levels``, which
# upload subtracts from the levels it requires. The renderer already returns
# no L1 item when the asset has no level_1 block.
ESCAPE_TOKENS: dict[str, str] = {
    'level_1': 'no_minimal_pairs',
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
                if _escape(f'level_{lv}', b, errors) is not None:
                    answer.setdefault('declined_levels', []).append(lv)
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
    errors += lint_variants(doc, variants, item)
    return entry, errors, surplus


def _distractors(block) -> frozenset:
    if not isinstance(block, dict) or not isinstance(block.get('options'), list):
        return frozenset()
    return frozenset(o.get('text') for o in block['options']
                     if isinstance(o, dict) and not o.get('is_correct'))


# Opt-in (FAT_SEED_LINT_ALL_BLOCKS=1): the A/B distractor-overlap lint on every
# option block, not just level_1. Being trialled by the optimisation arms.
OVERLAP_LINT_BLOCKS = (
    ('level_1', 'level_3', 'level_4', 'level_5', 'level_8', 'synonym_antonym_match',
     'particle_selection', 'word_family')
    if os.environ.get('FAT_SEED_LINT_ALL_BLOCKS') == '1' else ('level_1',))

#: Same opt-in: the content lints below (generic explanations, level_7 pairs
#: that do not test the target or change two things, particle blanks the
#: renderer would cut in the wrong place). Measured on 356 reviewed production
#: documents before being enabled; see tests/test_fat_seed.py.
LINT_ALL = os.environ.get('FAT_SEED_LINT_ALL_BLOCKS') == '1'
#: Comma-separated rule ids to leave out of the opt-in content lints, so a rule
#: can be demoted without a code change: l3_generic_expl, l6_shared_expl,
#: l6_copied_expl, l7_target_absent, l7_multi_span, l7_edit_far, ps_slot.
LINT_SKIP = frozenset(r.strip() for r in os.environ.get('FAT_SEED_LINT_SKIP', '').split(',') if r.strip())

_EXPL_NOISE = re.compile(r'[「」『』“”"\'、。．，,.！？!?・\s（）()\[\]【】…:：;；〜~\-]')
_EXPL_LEAD = re.compile(r'^(は|が|を|も|だと|では|なら|というのは|とは|の|と|で|に|という)+')
#: Explanations that only restate the rule. Normalised (option text, brackets,
#: punctuation and a leading particle removed); anything this short or on this
#: list tells the learner nothing about the word.
GENERIC_EXPLANATION_MAX = 12
GENERIC_EXPLANATIONS = frozenset({
    '形は合うが意味が合わない', '形は合うがこの文脈では意味が合わない', '形は合うが文脈に合わない',
    '形は合うが意味や文脈が合わない', '形は合うが意味が異なる', '意味や形が合わず', '意味が合わない',
    '反対の関係ではない', '反対の意味ではない', '反対の意味ではありません',
})
_KANJI_RUN = re.compile(r'^[一-鿿]+')
_SURU = 'すしさせで'  # 採用す/採用し/採用さ(れる)/採用せ(ず)/採用で(きる): a noun used as a verb


def _norm_expl(text, option_text: str = '') -> str:
    t = str(text or '')
    if option_text:
        t = t.replace(option_text, '')
    return _EXPL_LEAD.sub('', _EXPL_NOISE.sub('', t))


def _option_rows(block) -> list[dict]:
    opts = block.get('options') if isinstance(block, dict) else None
    return [o for o in opts if isinstance(o, dict)] if isinstance(opts, list) else []


def _target_forms(doc: dict) -> set[str]:
    """Surface forms that count as "the target word is present".

    The lemma, every core ``target_word`` and morphological form, plus the
    lemma's leading kanji run (減 for 減らす: a misconjugated target is still
    the target) or, for a kana lemma, all but its last character (プリン for
    プリント). Lenient on purpose: this backs a "target absent" check.
    """
    core = doc.get('core') if isinstance(doc.get('core'), dict) else {}
    lemma = doc.get('lemma') if isinstance(doc.get('lemma'), str) else ''
    forms = {lemma}
    forms |= {s.get('target_word') for s in core.get('sentences') or [] if isinstance(s, dict)}
    forms |= {f.get('form') for f in core.get('morphological_forms') or [] if isinstance(f, dict)}
    forms = {f for f in forms if isinstance(f, str) and f}
    m = _KANJI_RUN.match(lemma)
    if m:
        forms.add(m.group(0))
    elif len(lemma) >= 4:
        forms.add(lemma[:-1])
    return forms


def _occurrences(text: str, forms: set[str]) -> list[tuple[int, int]]:
    out = []
    for f in forms:
        i = text.find(f)
        while i >= 0:
            out.append((i, i + len(f)))
            i = text.find(f, i + 1)
    return out


def _edit_spans(a: str, b: str) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Changed regions between a and b as ((a_start, a_end), (b_start, b_end)).

    Edits one unchanged character apart count as one region (a conjugation
    change is one error); regions that only move punctuation are dropped.
    """
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    spans: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        if spans and j1 - spans[-1][1][1] <= 1:
            spans[-1] = ((spans[-1][0][0], i2), (spans[-1][1][0], j2))
        else:
            spans.append(((i1, i2), (j1, j2)))
    return [(sa, sb) for sa, sb in spans if _EXPL_NOISE.sub('', a[sa[0]:sa[1]] + b[sb[0]:sb[1]])]


def _gap(span: tuple[int, int], occ: list[tuple[int, int]]) -> int | None:
    """Characters between ``span`` and the nearest occurrence (0 = touching or overlapping)."""
    a, b = span
    best = None
    for s, e in occ:
        g = 0 if (a < e and s < b) else (s - b if s >= b else a - e)
        best = g if best is None else min(best, g)
    return best


def _tokenised_particles(text: str) -> list[dict]:
    """``{particle, index}`` spans from the tokeniser the particle_selection
    renderer cuts the blank with; ``[]`` when it is unavailable, which skips
    the slot lint rather than guessing from the raw string (に in にんじん)."""
    try:
        from services.vocabulary_ladder.asset_generators.particle_selection import particle_spans
        return particle_spans(text) or []
    except Exception:  # noqa: BLE001 — optional dependency path
        return []


def _slot_touches_target(anchor: str, start: int, particle: str, occ: list[tuple[int, int]],
                         predicate: bool = True, particle_starts: tuple[int, ...] = ()) -> bool:
    """The particle at ``start`` closes a target form (敬意|を); for a predicate
    target it may also mark the argument right before it (結果を細かく|記録した:
    at most 6 characters apart with no other particle or comma between); for a
    noun only a modifying の may precede it (絵の|プリント) — 塩は|イオン marks
    塩, not the target. ``particle_starts`` are the anchor's tokenised particle
    offsets, so a か inside 細かく does not count as a particle."""
    end = start + len(particle)
    for s, e in occ:
        if e == start:
            return True
        if end <= s and s - end <= 6 and '、' not in anchor[end:s] \
                and not any(end <= i < s for i in particle_starts):
            if predicate or (particle == 'の' and end == s):
                return True
    return False


def lint_variants(doc: dict, variants: dict, item: dict | None = None) -> list[str]:
    """Catch the defects reviewers fixed most often, so authors fix them first.

    - B's level_1 distractors repeat A's (reordering is not a new variant).
    - B's level_6 wrong sentences repeat A's.
    - A level_7 incorrect sentence copies a core sentence or equals its
      own correction, so the item marks one sentence both right and wrong.

    With ``FAT_SEED_LINT_ALL_BLOCKS=1`` (``LINT_ALL``) also:

    - level_3 distractor explanations that are a bare template
      (形は合うが意味が合わない) or are shared between distractors.
    - level_6 wrong sentences sharing one explanation, or B reusing A's.
    - level_7 incorrect sentence without the target word, a correction that
      changes two separate places (not a minimal pair), or one whose single
      edit is not on or next to the target word.
    - particle_selection blank that the renderer would cut at a different
      occurrence than the one next to the target, or that is no particle of
      the anchor at all (needs ``item`` for the anchor index).
    """
    errors: list[str] = []
    a, b = variants.get('A') or {}, variants.get('B') or {}
    for block in OVERLAP_LINT_BLOCKS:
        da, db = _distractors(a.get(block)), _distractors(b.get(block))
        # particles come from a small closed set, so only a verbatim copy counts
        need = min(len(da), len(db)) if block == 'particle_selection' else max(2, min(len(da), len(db)) - 1)
        if da and db and len(da & db) >= need:
            errors.append(f'[B] {block}: distractors repeat A — write new ones for B')
    wa = {w.get('text') for w in (a.get('level_6') or {}).get('wrong_sentences') or []
          if isinstance(w, dict)}
    wb = {w.get('text') for w in (b.get('level_6') or {}).get('wrong_sentences') or []
          if isinstance(w, dict)}
    if wa & wb:
        errors.append('[B] level_6: wrong sentences repeat A — write new ones for B')
    core_texts = {s.get('text') for s in (doc.get('core') or {}).get('sentences') or []
                  if isinstance(s, dict)}
    for v, var in (('A', a), ('B', b)):
        l7 = var.get('level_7')
        if not isinstance(l7, dict) or is_declined(l7):
            continue
        wrong = l7.get('incorrect_sentence')
        if wrong and wrong == l7.get('corrected_sentence'):
            errors.append(f'[{v}] level_7: incorrect and corrected sentences are identical')
        elif wrong and wrong in core_texts:
            errors.append(f'[{v}] level_7: incorrect sentence is a core sentence verbatim')
        # The corrected twin of the planted error must not be one of the core
        # sentences shown beside it, or the item gives its answer away.
        if (len(OVERLAP_LINT_BLOCKS) > 1 and l7.get('corrected_sentence')
                and l7.get('corrected_sentence') in core_texts):
            errors.append(f'[{v}] level_7: corrected sentence is a core sentence verbatim — '
                          'plant the error in a new sentence, not a copy of a core one')
    if LINT_ALL:
        errors += _lint_content(doc, a, b, item)
    return errors


def content_lints(doc: dict, variants: dict, item: dict | None = None) -> list[tuple[str, str]]:
    """The opt-in content lints as ``(rule_id, message)`` pairs, ignoring the env
    gates, so a caller can report them as warnings (the repair loop they trigger
    as check failures did not pay for itself on Haiku or Sonnet, gold100)."""
    a, b = variants.get('A') or {}, variants.get('B') or {}
    return _lint_content(doc, a, b, item, skip=frozenset(), tagged=True)


def _lint_content(doc: dict, a: dict, b: dict, item: dict | None,
                  skip: frozenset | None = None, tagged: bool = False) -> list:
    skip = LINT_SKIP if skip is None else skip

    class _Errors(list):
        """append(rule_id, message): dropped when the rule is skipped."""
        def append(self, rule, msg=None):  # noqa: D401
            if msg is None:
                rule, msg = '', rule
            if rule not in skip:
                list.append(self, (rule, msg) if tagged else msg)
    errors = _Errors()
    forms = _target_forms(doc)
    lemma = doc.get('lemma') if isinstance(doc.get('lemma'), str) else ''
    sentences = [s for s in ((doc.get('core') or {}).get('sentences') or []) if isinstance(s, dict)]
    # a noun that conjugates (採取する, 採取して, 改善され, 採用でき) is a predicate in use
    predicate = (str((doc.get('core') or {}).get('pos') or '') not in ('名詞', '代名詞')
                 or any(f.startswith(lemma) and len(f) > len(lemma) and f[len(lemma)] in _SURU
                        for f in forms))
    l6_expl_a: set[str] = set()
    for v, var in (('A', a), ('B', b)):
        l3 = var.get('level_3')
        if isinstance(l3, dict) and not is_declined(l3):
            rows = [(str(o.get('text') or ''), _norm_expl(o.get('explanation'), str(o.get('text') or '')))
                    for o in _option_rows(l3) if not o.get('is_correct')]
            normed = [n for _, n in rows]
            bad = [t for t, n in rows
                   if len(n) <= GENERIC_EXPLANATION_MAX or n in GENERIC_EXPLANATIONS
                   or (len(n) <= 16 and normed.count(n) > 1)]
            if bad:
                # Haiku rewrote distractors when told the explanations were generic, and the new
                # distractors fitted the blank (b_rep3_100): say exactly what may change.
                errors.append('l3_generic_expl', f'[{v}] level_3: the explanations for {"、".join(f"「{t}」" for t in bad)} are a '
                              'generic template — rewrite ONLY these explanation texts (say what the word '
                              'means and why it fails in this sentence); keep every option text exactly as it is')
        l6 = var.get('level_6')
        if isinstance(l6, dict) and not is_declined(l6):
            ex = [_norm_expl(w.get('explanation')) for w in l6.get('wrong_sentences') or []
                  if isinstance(w, dict)]
            ex = [e for e in ex if e]
            if len(set(ex)) < len(ex):
                errors.append('l6_shared_expl', f'[{v}] level_6: wrong sentences share one explanation — each needs its '
                              'own, naming how the target is misused in that sentence')
            if v == 'A':
                l6_expl_a = set(ex)
            elif set(ex) & l6_expl_a:
                errors.append('l6_copied_expl', '[B] level_6: explanations repeat A word for word — write B independently')
        l7 = var.get('level_7')
        if isinstance(l7, dict) and not is_declined(l7):
            wrong, fixed = l7.get('incorrect_sentence'), l7.get('corrected_sentence')
            if forms and isinstance(wrong, str) and wrong and not any(f in wrong for f in forms):
                errors.append('l7_target_absent', f'[{v}] level_7: the incorrect sentence does not contain 「{lemma}」 — '
                              'the single error must involve the target word')
            if isinstance(wrong, str) and isinstance(fixed, str) and wrong and fixed and wrong != fixed:
                spans = _edit_spans(wrong, fixed)
                if len(spans) >= 2:
                    changed = '、'.join(f'「{wrong[sa[0]:sa[1]]}→{fixed[sb[0]:sb[1]]}」' for sa, sb in spans)
                    errors.append('l7_multi_span', f'[{v}] level_7: the correction changes {len(spans)} separate places '
                                  f'({changed}) — plant exactly one error and fix only that')
                elif len(spans) == 1 and forms:
                    # the one edit must sit on the target or right next to it (a particle between
                    # them is fine): 敬意を[払う→食べる] tests 敬意, 机の上に[咲いた→広がった] does not test 液
                    (sa, sb), = spans
                    gaps = [g for g in (_gap(sa, _occurrences(wrong, forms)), _gap(sb, _occurrences(fixed, forms)))
                            if g is not None]
                    if gaps and min(gaps) > 1:
                        errors.append('l7_edit_far', f'[{v}] level_7: the only change (「{wrong[sa[0]:sa[1]]}→{fixed[sb[0]:sb[1]]}」) '
                                      f'is {min(gaps)} characters away from 「{lemma}」 — the single error must '
                                      'be on the target word or the word right next to it')
        ps = var.get('particle_selection')
        if isinstance(ps, dict) and not is_declined(ps) and isinstance(item, dict):
            spec = (((item.get('variants') or {}).get(v) or {}).get('typed') or {}).get('particle_selection')
            idx = spec.get('sentence_index') if isinstance(spec, dict) else None
            particle = str(ps.get('blanked_particle') or '').strip()
            if particle and isinstance(idx, int) and 0 <= idx < len(sentences):
                anchor = str(sentences[idx].get('text') or '')
                spans = _tokenised_particles(anchor)
                mine = [s['index'] for s in spans
                        if s.get('particle') == particle and isinstance(s.get('index'), int)]
                starts = tuple(s['index'] for s in spans if isinstance(s.get('index'), int))
                occ = _occurrences(anchor, forms)
                # the noun may be a verb in this very sentence (同じ技術を採用すれば)
                pred_here = predicate or any(anchor[e:e + 1] in _SURU for _, e in occ)
                if spans and not mine:
                    have = '／'.join(sorted({str(s.get('particle')) for s in spans}))
                    errors.append('ps_slot', f'[{v}] particle_selection: 「{particle}」 is not a particle of the anchor '
                                  f'「{anchor}」 (the renderer would drop the item) — blank one of {have} '
                                  'or decline with "no_particle_slot"')
                elif mine and not _slot_touches_target(anchor, mine[0], particle, occ, pred_here, starts):
                    if any(_slot_touches_target(anchor, i, particle, occ, pred_here, starts) for i in mine[1:]):
                        lo, hi = max(0, mine[0] - 4), mine[0] + len(particle) + 4
                        errors.append('ps_slot', f'[{v}] particle_selection: the anchor has 「{particle}」 {len(mine)} times '
                                      f'and the renderer blanks the FIRST one (…{anchor[lo:hi]}…), which is '
                                      f'not the slot next to 「{lemma}」 — blank a particle whose first '
                                      'occurrence attaches to the target, or decline with "no_particle_slot"')
                    else:
                        errors.append('ps_slot', f'[{v}] particle_selection: 「{particle}」 in the anchor 「{anchor}」 does '
                                      f'not attach to 「{lemma}」 — blank a particle that relates to the '
                                      'target or decline with "no_particle_slot"')
    return list(errors)


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
