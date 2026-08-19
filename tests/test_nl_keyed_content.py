"""TASK-519 — schema-v2 nl-keyed content envelope.

Four groups:

  1. **Envelope gate** — nl text at the top level of a v2 item is rejected;
     legacy v1 content is left alone.
  2. **Construction / reading** — wrap_nl / read_nl / flatten_for_serve.
  3. **Generator shape** — the tl_nl / nl_tl generators emit the keyed shape
     for ZH and JA (and would for any nl, which is the point).
  4. **Lint** — no generation module reintroduces a hardcoded native language.
     This is the guard that actually keeps the corpus multilingual: the v1
     pipeline was English-only not by decision but by a string literal.
"""

import ast
import pathlib

import pytest

from services.exercise_generation.schemas import (
    SCHEMA_VERSION,
    EnvelopeError,
    flatten_for_serve,
    read_nl,
    validate_envelope,
    wrap_nl,
)
from services.exercise_generation.validators import ExerciseValidator

REPO = pathlib.Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _valid_tl_nl() -> dict:
    return {
        'schema_version': SCHEMA_VERSION,
        'tl_sentence': '他很高',
        'tl_language': 'zh',
        'nl': {'en': {'correct': 'He is tall',
                      'options': ['He is tall', 'He is old', 'He is busy']}},
    }


def _valid_nl_tl() -> dict:
    return {
        'schema_version': SCHEMA_VERSION,
        'tl_language': 'ja',
        'primary_tl': '彼は背が高い',
        'acceptable_variants': ['彼は長身だ'],
        'nl': {'en': {'prompt': 'He is tall', 'grading_notes': 'copula required'}},
    }


# ---------------------------------------------------------------------------
# 1. Envelope gate
# ---------------------------------------------------------------------------

def test_valid_v2_envelope_passes():
    assert validate_envelope(_valid_tl_nl(), 'tl_nl_translation') == []
    assert validate_envelope(_valid_nl_tl(), 'nl_tl_translation') == []


def test_nl_text_at_top_level_is_rejected():
    """The core rule: a gloss must not sit outside content.nl."""
    bad = _valid_tl_nl()
    bad['correct_nl'] = 'He is tall'

    errors = validate_envelope(bad, 'tl_nl_translation')

    assert errors
    assert any('correct_nl' in e and 'content.nl' in e for e in errors)


def test_options_at_top_level_is_rejected():
    bad = _valid_tl_nl()
    bad['options'] = ['He is tall', 'He is old', 'He is busy']

    errors = validate_envelope(bad, 'tl_nl_translation')

    assert any('options' in e for e in errors)


def test_missing_nl_map_is_rejected():
    bad = _valid_tl_nl()
    del bad['nl']

    errors = validate_envelope(bad, 'tl_nl_translation')

    assert any('content.nl' in e for e in errors)


def test_incomplete_nl_block_is_rejected():
    bad = _valid_tl_nl()
    del bad['nl']['en']['options']

    errors = validate_envelope(bad, 'tl_nl_translation')

    assert any("missing 'options'" in e for e in errors)


def test_legacy_v1_content_is_not_retroactively_invalidated():
    """The gate governs what new generators write, not the existing corpus."""
    v1 = {
        'tl_sentence': '他很高',
        'correct_nl': 'He is tall',
        'options': ['He is tall', 'He is old', 'He is busy'],
    }

    assert validate_envelope(v1, 'tl_nl_translation') == []


def test_validator_reports_envelope_violation():
    """ExerciseValidator surfaces the real cause, not N 'missing field' errors."""
    bad = _valid_tl_nl()
    bad['correct_nl'] = 'He is tall'

    ok, errors = ExerciseValidator().validate(bad, 'tl_nl_translation')

    assert ok is False
    assert any('schema-v2 violation' in e for e in errors)


def test_validator_accepts_a_well_formed_v2_item():
    ok, errors = ExerciseValidator().validate(_valid_tl_nl(), 'tl_nl_translation')
    assert ok, errors


# ---------------------------------------------------------------------------
# 2. Construction / reading
# ---------------------------------------------------------------------------

def test_wrap_nl_keys_the_native_language():
    content = wrap_nl(
        {'tl_sentence': '他很高', 'tl_language': 'zh'},
        'tl_nl_translation',
        'ja',
        {'correct_nl': '彼は背が高い', 'options': ['彼は背が高い', 'a', 'b']},
    )

    assert content['schema_version'] == SCHEMA_VERSION
    assert set(content['nl']) == {'ja'}
    assert content['nl']['ja']['correct'] == '彼は背が高い'
    # TL-facing content stays flat and nl-free.
    assert content['tl_sentence'] == '他很高'
    assert 'correct_nl' not in content


def test_wrap_nl_accumulates_multiple_native_languages():
    base = {'tl_sentence': '他很高', 'tl_language': 'zh'}
    en = wrap_nl(base, 'tl_nl_translation', 'en',
                 {'correct_nl': 'He is tall', 'options': ['He is tall', 'a', 'b']})
    both = wrap_nl(en, 'tl_nl_translation', 'ja',
                   {'correct_nl': '彼は背が高い', 'options': ['彼は背が高い', 'c', 'd']})

    assert set(both['nl']) == {'en', 'ja'}
    assert both['nl']['en']['correct'] == 'He is tall'


def test_wrap_nl_requires_an_explicit_language():
    with pytest.raises(EnvelopeError):
        wrap_nl({'tl_sentence': 'x'}, 'tl_nl_translation', '',
                {'correct_nl': 'y', 'options': ['y']})


def test_wrap_nl_rejects_a_field_that_is_not_nl_bearing():
    """Silently dropping it would produce a half-translated item."""
    with pytest.raises(EnvelopeError):
        wrap_nl({'tl_sentence': 'x'}, 'tl_nl_translation', 'en',
                {'tl_sentence': 'x'})


def test_read_nl_falls_back_to_the_only_block():
    content = _valid_tl_nl()
    assert read_nl(content, 'ja')['correct'] == 'He is tall'


def test_read_nl_returns_empty_for_legacy_content():
    assert read_nl({'tl_sentence': 'x'}, 'en') == {}


def test_flatten_for_serve_projects_v1_keys():
    flat = flatten_for_serve(_valid_tl_nl(), 'en')

    assert flat['correct_nl'] == 'He is tall'
    assert flat['options'][0] == 'He is tall'
    assert flat['tl_sentence'] == '他很高'
    assert 'nl' not in flat


def test_flatten_for_serve_passes_legacy_through_untouched():
    v1 = {'tl_sentence': '他很高', 'correct_nl': 'He is tall'}
    assert flatten_for_serve(v1, 'en') == v1


# ---------------------------------------------------------------------------
# 3. Generator shape (ZH + JA), LLM-free
# ---------------------------------------------------------------------------

class _FakeSingle:
    def __init__(self, code):
        self._code = code

    def execute(self):
        class R:
            data = {'language_code': self._code}
        return R()


class _FakeLangTable:
    def __init__(self, code):
        self._code = code

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def single(self):
        return _FakeSingle(self._code)


class _FakeDB:
    def __init__(self, code):
        self._code = code

    def table(self, _name):
        return _FakeLangTable(self._code)


def _build_tl_nl(monkeypatch, tl_code, nl_code):
    from services.exercise_generation.generators import translation as tmod

    gen = tmod.TlNlTranslationGenerator(
        _FakeDB(tl_code), language_id=1, model='m', nl_language_code=nl_code,
    )
    monkeypatch.setattr(gen, 'load_prompt_template',
                        lambda name: '{tl_sentence}/{nl_language}')
    monkeypatch.setattr(gen, 'call_llm', lambda *a, **k: {
        'correct_nl': 'CORRECT', 'wrong_options': ['W1', 'W2'],
    })
    return gen.generate_one({'sentence': 'S', 'test_id': 7}, source_id=1)


@pytest.mark.parametrize('tl_code,nl_code', [('zh', 'en'), ('ja', 'en'), ('zh', 'ja')])
def test_tl_nl_generator_emits_keyed_shape(monkeypatch, tl_code, nl_code):
    content = _build_tl_nl(monkeypatch, tl_code, nl_code)

    assert content['schema_version'] == SCHEMA_VERSION
    assert content['tl_language'] == tl_code
    assert set(content['nl']) == {nl_code}
    assert content['nl'][nl_code]['correct'] == 'CORRECT'
    # V3 rule preserved inside the keyed block.
    assert content['nl'][nl_code]['options'][0] == 'CORRECT'
    # Nothing nl-facing leaked to the top level.
    assert validate_envelope(content, 'tl_nl_translation') == []


def test_nl_tl_generator_emits_keyed_shape(monkeypatch):
    from services.exercise_generation.generators import translation as tmod

    gen = tmod.NlTlTranslationGenerator(
        _FakeDB('ja'), language_id=3, model='m', nl_language_code='en',
    )
    monkeypatch.setattr(gen, 'load_prompt_template',
                        lambda name: '{tl_sentence}/{nl_language}')
    monkeypatch.setattr(gen, 'call_llm', lambda *a, **k: {
        'nl_sentence': 'He is tall',
        'grading_notes': 'copula required',
        'acceptable_variants': ['彼は長身だ'],
    })

    content = gen.generate_one({'sentence': '彼は背が高い', 'test_id': 7}, source_id=1)

    assert content['nl']['en']['prompt'] == 'He is tall'
    assert content['nl']['en']['grading_notes'] == 'copula required'
    # TL-facing answer data stays flat — the learner types in the TL.
    assert content['primary_tl'] == '彼は背が高い'
    assert content['acceptable_variants'] == ['彼は長身だ']
    assert validate_envelope(content, 'nl_tl_translation') == []


# ---------------------------------------------------------------------------
# 4. Lint — no hardcoded native language in generation code paths
# ---------------------------------------------------------------------------

_GENERATION_DIRS = [
    REPO / 'services' / 'exercise_generation',
    REPO / 'services' / 'vocabulary_ladder',
]

# Parameter names that carry a native-language code. A literal default for any
# of these silently pins the whole pipeline to one language.
_NL_PARAM_NAMES = {'nl_language_code', 'nl_language', 'nl_code', 'native_language'}


# Legacy generators frozen by TASK-512 (the ladder becomes the sole vocab
# generator; grammar / conversation / style stay as-is and are not migrated to
# schema v2). Exempt by name so the exemption is visible and reviewable — if
# one of these is ever unfrozen, deleting its line here is the reminder that it
# owes an envelope migration.
_FROZEN_LEGACY = {
    'style.py',        # style_imitation — grammar/style path, frozen by TASK-512
}


def _generation_sources():
    for root in _GENERATION_DIRS:
        if not root.exists():
            continue
        for path in sorted(root.rglob('*.py')):
            # The envelope module documents the rule in prose and necessarily
            # names 'en' to do so.
            if path.name == 'envelope.py' or path.name in _FROZEN_LEGACY:
                continue
            yield path


def test_no_hardcoded_nl_default_in_generation_modules():
    """A default like ``nl_language_code: str = 'en'`` is the v1 bug itself.

    It makes every generated item English-only without any decision being
    recorded anywhere. The native language must be threaded in from the caller.
    """
    offenders = []

    for path in _generation_sources():
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            args = node.args
            paired = []
            if args.defaults:
                paired += list(zip(args.args[-len(args.defaults):], args.defaults))
            paired += [(a, d) for a, d in zip(args.kwonlyargs, args.kw_defaults) if d]
            for arg, default in paired:
                if arg.arg not in _NL_PARAM_NAMES:
                    continue
                if isinstance(default, ast.Constant) and isinstance(default.value, str):
                    offenders.append(
                        f"{path.relative_to(REPO)}:{node.lineno} "
                        f"{node.name}({arg.arg}={default.value!r})"
                    )

    assert not offenders, (
        'Hardcoded native-language defaults found in generation code. Thread '
        'the nl code in from the caller instead:\n  ' + '\n  '.join(offenders)
    )


def test_nl_bearing_keys_are_not_written_outside_the_envelope():
    """Generators must not write nl-bearing keys straight into content.

    Catches the regression where someone adds ``'correct_nl': ...`` back into a
    returned dict instead of routing it through ``wrap_nl``.
    """
    watched = {'correct_nl', 'grading_notes', 'nl_sentence'}
    offenders = []

    for path in _generation_sources():
        source = path.read_text(encoding='utf-8')
        if 'wrap_nl' in source:
            continue                     # already routed through the envelope
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key in node.keys:
                if isinstance(key, ast.Constant) and key.value in watched:
                    offenders.append(
                        f"{path.relative_to(REPO)}:{key.lineno} writes "
                        f"{key.value!r} outside content.nl"
                    )

    assert not offenders, (
        'Native-language text written outside the content.nl envelope:\n  '
        + '\n  '.join(offenders)
    )
