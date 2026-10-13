"""L2 (definition_match) must be rendered ONLY by the deterministic builder.

Regression guard, same shape as test_jumbled_renderer_wiring.py. A legacy
``LadderExerciseRenderer._render_definition_match`` (get_distractors RPC, no
language or tier control, sentence-target ``word``) used to be dispatched for
level 2 alongside ``deterministic/definition_match.py``, so every sense had two
definition_match rows. The legacy row was emitted first, so ``apply_caps``
kept it over the deterministic one — and its distractor pool was where the
mixed-language options came from. Live data (2026-10-12): every definition_match
sense had one row with ``tags.generator == 'deterministic'`` and one without.
"""

from services.vocabulary_ladder import exercise_renderer as rendermod
from services.vocabulary_ladder.deterministic import lexicon as lexmod

LANG_JA = 3

_CORE = {
    'pos': 'verb',
    'semantic_class': 'action',
    'definition': '絵や図を、筆などでかく。',
    'pronunciation': 'えがく',
    'morphological_forms': [],
    'sentences': [
        {'text': '姉は毎日、公園で絵を描いています。', 'target_word': '描い',
         'source': 'generated', 'complexity_tier': 'A2'}
        for _ in range(10)
    ],
}


def _renderer(monkeypatch):
    r = rendermod.LadderExerciseRenderer(db=object())
    monkeypatch.setattr(r, '_load_assets', lambda sense_id: {
        'prompt1_core': _CORE, 'prompt2_exercises_A': {}, 'prompt3_transforms_A': {},
    })
    monkeypatch.setattr(r, '_load_asset_ids', lambda sense_id: {'prompt1_core': 'asset-1'})
    monkeypatch.setattr(r, '_render_hant_mirror', lambda content, language_id: None)
    monkeypatch.setattr(r, '_vocab_lemma', lambda sense_id: '描く')
    return r


def _install_lexicon():
    lexmod.reset_cache()
    lex = lexmod.Lexicon(language_id=LANG_JA)
    for idx, (lemma, definition) in enumerate([
        ('水', '飲み物として使う、透明な液体。'),
        ('茶', '葉を煮出して作る、飲み物。'),
        ('牛乳', '牛から取れる、白い飲み物。'),
    ], start=100):
        entry = lexmod.LexEntry(
            sense_id=idx, lemma=lemma, definition=definition, pronunciation='',
            reading_key='', tier='A2', frequency=5.0, semantic_class='concrete',
            sense_rank=1,
        )
        lex.entries.append(entry)
        lex.by_lemma.setdefault(lemma, entry)
    lexmod._cache[LANG_JA] = lex


def test_renderer_has_no_legacy_definition_match_path(monkeypatch):
    r = _renderer(monkeypatch)
    assert not hasattr(r, '_render_definition_match')
    assert r._render_level(2, _CORE, {}, {}, 1, LANG_JA, {}) is None


def test_definition_match_rows_come_only_from_the_deterministic_builder(monkeypatch):
    _install_lexicon()
    try:
        rows = _renderer(monkeypatch).build_rows(sense_id=99101, language_id=LANG_JA, levels={2})
    finally:
        lexmod.reset_cache()

    dm = [row for row in rows if row['exercise_type'] == 'definition_match']
    assert dm, 'fixture must produce a definition_match row'
    assert all(row['tags'].get('generator') == 'deterministic' for row in dm), dm
    # Deterministic rows use the schema-v2 nl envelope, never flat `options`.
    assert all('nl' in row['content'] and 'options' not in row['content'] for row in dm)
    # The word is the dictionary form, not the sentence's inflected target.
    assert all(row['content']['word'] == '描く' for row in dm)
