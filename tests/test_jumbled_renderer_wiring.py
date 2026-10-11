"""L9 (jumbled_sentence) must be rendered ONLY by the real chunking generator.

Regression guard for a bug where `LadderExerciseRenderer._render_level`
dispatched level 9 to a legacy `_render_jumbled` stub that stored only
``{'original_sentence': text}`` — no ``chunks``/``shuffled_chunks`` — with
chunking deferred to serve time and never actually verified. That stub ran
*alongside* the real generator (services/vocabulary_ladder/deterministic/
jumbled.py, registered in the capability matrix as the 'deterministic'
builder for 'jumbled_sentence'), so every sense produced one correct,
chunk-verified row and one broken, chunkless duplicate — 305 such chunkless
rows were found across data/eval/runs.

The fix removes the stub and its dispatch entry entirely; `jumbled_sentence`
now reaches the exercises table exclusively through
`LadderExerciseRenderer._render_deterministic` ->
`services.vocabulary_ladder.deterministic.generate()` ->
`deterministic/jumbled.py`'s own reconstruction-invariant check. These tests
drive the renderer end to end (`build_rows`) rather than calling the
generator module directly (already covered by test_deterministic_generators.py)
so a regression that re-adds *any* second code path emitting
`jumbled_sentence` would be caught here.
"""

import re

from services.vocabulary_ladder import exercise_renderer as rendermod
from services.vocabulary_ladder.deterministic import jumbled as jumbled_mod

LANG_EN = 2

_PUNCT_RE = re.compile(r'[^\w\s]', re.UNICODE)


def _normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', _PUNCT_RE.sub('', text)).strip()


def _reconstructs(row: dict) -> bool:
    """Whether a jumbled_sentence row's chunks join back into its sentence."""
    content = row['content']
    chunks = content.get('chunks')
    if not chunks:
        return False
    joiner = '' if row.get('language_id') in (1, 3) else ' '
    return _normalize(joiner.join(chunks)) == _normalize(content['original_sentence'])


_SENTENCE = 'It will quickly waterlog the field.'
_CHUNKS = ['It', 'will quickly waterlog', 'the field']

_EN_CORE = {
    'pos': 'verb',
    'semantic_class': 'action',
    'definition': 'to cause standing water to accumulate on (land)',
    'pronunciation': None,
    'morphological_forms': [],
    'sentences': [
        {'text': _SENTENCE, 'target_word': 'waterlog',
         'source': 'generated', 'complexity_tier': 'B1'}
        for _ in range(10)
    ],
}


def _renderer_with(monkeypatch, core):
    r = rendermod.LadderExerciseRenderer(db=object())
    monkeypatch.setattr(r, '_load_assets', lambda sense_id: {
        'prompt1_core': core,
        'prompt2_exercises_A': {},
        'prompt3_transforms_A': {},
    })
    monkeypatch.setattr(r, '_load_asset_ids', lambda sense_id: {'prompt1_core': 'asset-1'})
    monkeypatch.setattr(r, '_render_hant_mirror', lambda content, language_id: None)
    return r


def test_build_rows_emits_exactly_one_jumbled_sentence_row_per_variant(monkeypatch):
    """No duplicate (stub + real) rows for the same level/variant."""
    monkeypatch.setattr(jumbled_mod, '_chunk', lambda text, lang: list(_CHUNKS))
    r = _renderer_with(monkeypatch, _EN_CORE)

    rows = r.build_rows(sense_id=99001, language_id=LANG_EN, levels={9})

    jumbled_rows = [row for row in rows if row['exercise_type'] == 'jumbled_sentence']
    assert len(jumbled_rows) == 1, (
        f'expected exactly one jumbled_sentence row, got {len(jumbled_rows)}: '
        f'{jumbled_rows}'
    )


def test_every_rendered_jumbled_sentence_row_has_chunks_that_reconstruct(monkeypatch):
    """The core regression: no chunkless jumbled_sentence row may ever be
    produced by build_rows(), and whatever chunks ARE produced must
    reconstruct the source sentence."""
    monkeypatch.setattr(jumbled_mod, '_chunk', lambda text, lang: list(_CHUNKS))
    r = _renderer_with(monkeypatch, _EN_CORE)

    rows = r.build_rows(sense_id=99002, language_id=LANG_EN)

    jumbled_rows = [row for row in rows if row['exercise_type'] == 'jumbled_sentence']
    assert jumbled_rows, 'fixture must produce at least one jumbled_sentence row'

    for row in jumbled_rows:
        content = row['content']
        assert content.get('chunks'), f'chunkless jumbled_sentence row: {row}'
        assert content.get('shuffled_chunks'), f'no shuffled_chunks: {row}'
        assert _reconstructs(row), (
            f"chunks {content['chunks']!r} do not reconstruct "
            f"{content['original_sentence']!r}"
        )


def test_build_rows_skips_jumbled_sentence_when_unchunkable(monkeypatch):
    """A sentence the chunker cannot split into >= 3 pieces must produce NO
    row at all for L9 — not a chunkless fallback."""
    monkeypatch.setattr(jumbled_mod, '_chunk', lambda text, lang: ['one', 'two'])
    r = _renderer_with(monkeypatch, _EN_CORE)

    rows = r.build_rows(sense_id=99003, language_id=LANG_EN, levels={9})

    assert not [row for row in rows if row['exercise_type'] == 'jumbled_sentence']
