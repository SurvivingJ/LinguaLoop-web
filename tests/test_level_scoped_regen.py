"""TASK-811 — level-scoped regen.

Two halves, tested separately:

  1. `LadderExerciseRenderer.build_rows(..., levels=...)` — narrows the
     level-keyed render loop AND the deterministic/typed-LLM blocks to only
     the requested levels, with `levels=None` byte-for-byte unchanged from
     before this parameter existed (parity guard).
  2. `queue_drain._regenerate` — maps a coverage-gap row's
     `detail['missing_families']` to a level set via
     `services.vocabulary_ladder.config.families_to_levels`, threads it
     through to the pipeline and the renderer, and scopes the
     delete/insert to exactly those levels. A `regen`/`subscribe_topup` row
     (no family hint) still does a full, unscoped regen.

LLM-free and DB-free throughout — the renderer's asset loaders and the
queue_drain module's DB calls are all stubbed.
"""

import services.vocabulary_ladder.queue_drain as qd
from services.vocabulary_ladder import exercise_renderer as rendermod
from services.vocabulary_ladder.config import families_to_levels

LANG_ZH, LANG_EN = 1, 2

# ---------------------------------------------------------------------------
# Fixture: a ZH concrete noun with both a P3-owned level (7) and a
# deterministically-rendered level (4) — same shape test_p3_type_gating.py
# uses, so the render behaviour being filtered here is already pinned there.
# ---------------------------------------------------------------------------

ZH_CONCRETE_CORE = {
    'pos': '名词',
    'semantic_class': 'concrete',
    'definition': '书本；装订成册的印刷品',
    'primary_collocate': '',
    'pronunciation': 'shū',
    'morphological_forms': [],
    'sentences': [
        {'text': f'我买了一本书，编号{i}。', 'target_word': '书',
         'source': 'generated', 'complexity_tier': 'T2'}
        for i in range(10)
    ],
}

_ZH_P3 = {
    'level_4': {
        'options': [{'text': '书们', 'is_correct': True},
                    {'text': '书子', 'is_correct': False},
                    {'text': '书儿', 'is_correct': False},
                    {'text': '书头', 'is_correct': False}],
        'correct_form': '书们', 'base_form': '书', 'form_label': '复数',
        'sentence_index': 1, 'explanations': {'书们': '复数形式'},
    },
    'level_7': {
        'incorrect_sentence': '我买了一本书们。',
        'corrected_sentence': '我买了一本书。',
        'error_description': '量词错误',
        'correct_sentence_indices': [0, 1, 2],
    },
}


def _renderer_with(monkeypatch, core, p3_content):
    r = rendermod.LadderExerciseRenderer(db=object())
    monkeypatch.setattr(r, '_load_assets', lambda sense_id: {
        'prompt1_core': core,
        'prompt2_exercises_A': {},
        'prompt3_transforms_A': p3_content,
    })
    monkeypatch.setattr(r, '_load_asset_ids', lambda sense_id: {'prompt1_core': 'asset-1'})
    monkeypatch.setattr(r, '_render_hant_mirror', lambda content, language_id: None)
    return r


# ---------------------------------------------------------------------------
# 1. build_rows(levels=...)
# ---------------------------------------------------------------------------

def test_build_rows_levels_filter_narrows_active_levels(monkeypatch):
    """levels={7} keeps only the L7 row -- the stale L4 morphology blob (which
    is itself suppressed by the per-type gate and replaced by a deterministic
    L4 row, per test_p3_type_gating.py) must not appear either."""
    r = _renderer_with(monkeypatch, ZH_CONCRETE_CORE, _ZH_P3)

    rows = r.build_rows(sense_id=10, language_id=LANG_ZH, levels={7})

    assert rows, 'the requested level must still render'
    assert {row['ladder_level'] for row in rows} == {7}
    assert {row['exercise_type'] for row in rows} == {'spot_incorrect_sentence'}


def test_build_rows_levels_filter_excludes_deterministic_levels_too(monkeypatch):
    """levels={4} keeps only L4 (the deterministic classifier_match/cloze_typed
    rows) -- L7 must not sneak in even though its asset is present."""
    r = _renderer_with(monkeypatch, ZH_CONCRETE_CORE, _ZH_P3)

    rows = r.build_rows(sense_id=10, language_id=LANG_ZH, levels={4})

    assert rows, 'the requested level must still render'
    assert {row['ladder_level'] for row in rows} == {4}
    assert 'spot_incorrect_sentence' not in {row['exercise_type'] for row in rows}


def test_build_rows_levels_none_is_unchanged(monkeypatch):
    """Parity: no `levels` argument produces the exact same row set as the
    pre-TASK-811 signature did."""
    r = _renderer_with(monkeypatch, ZH_CONCRETE_CORE, _ZH_P3)

    unscoped = r.build_rows(sense_id=10, language_id=LANG_ZH)
    explicit_none = r.build_rows(sense_id=10, language_id=LANG_ZH, levels=None)

    def _fingerprint(rows):
        return sorted(
            (row['ladder_level'], row['exercise_type'], row['tags'].get('variant'))
            for row in rows
        )

    assert _fingerprint(unscoped) == _fingerprint(explicit_none)
    assert {row['ladder_level'] for row in unscoped} >= {4, 7}, (
        'fixture assumption changed -- both L4 and L7 should render unscoped'
    )


# ---------------------------------------------------------------------------
# 2. queue_drain._regenerate
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data):
        self.data = data


class _RecordingQuery:
    """Minimal chainable query double that records the call it was asked to
    make; enough surface for `_regenerate`'s delete/insert calls."""

    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self.filters: dict[str, list] = {}
        self._op = None
        self._payload = None

    def select(self, *_a, **_kw):
        self._op = self._op or 'select'
        return self

    def delete(self):
        self._op = 'delete'
        return self

    def insert(self, rows):
        self._op = 'insert'
        self._payload = rows
        return self

    def eq(self, col, val):
        self.filters.setdefault('eq', []).append((col, val))
        return self

    def in_(self, col, vals):
        self.filters.setdefault('in_', []).append((col, list(vals)))
        return self

    def gt(self, *_a, **_kw):
        return self

    def limit(self, *_a, **_kw):
        return self

    def single(self):
        return self

    @property
    def not_(self):
        return self

    def is_(self, col, val):
        self.filters.setdefault('is_', []).append((col, val))
        return self

    def execute(self):
        self.db.calls.append({
            'table': self.table_name, 'op': self._op,
            'filters': {k: list(v) for k, v in self.filters.items()},
            'payload': self._payload,
        })
        return _Result(self._payload if self._op == 'insert' else [])


class _FakeDB:
    def __init__(self):
        self.calls = []

    def table(self, name):
        return _RecordingQuery(self, name)


class _FakePipeline:
    last_levels = 'unset'

    def __init__(self, db):
        self.db = db

    def generate_for_sense(self, sense_id, language_id, force=True, levels=None):
        type(self).last_levels = levels
        return {'status': 'success', 'errors': []}


def _make_fake_renderer(rows_for_levels):
    class _FakeRenderer:
        last_levels = 'unset'

        def __init__(self, db):
            self.db = db
            self.last_skips = []

        def build_rows(self, sense_id, language_id, levels=None):
            type(self).last_levels = levels
            wanted = rows_for_levels if levels is None else levels
            return [{'id': f'ex-{lv}', 'ladder_level': lv, 'word_sense_id': sense_id}
                    for lv in sorted(wanted)]

    return _FakeRenderer


def _patch_regenerate_deps(monkeypatch, semantic_class, rows_for_levels):
    import services.vocabulary_ladder.asset_pipeline as pipeline_mod
    import services.vocabulary_ladder.exercise_renderer as renderer_mod

    monkeypatch.setattr(pipeline_mod, 'VocabAssetPipeline', _FakePipeline)
    fake_renderer_cls = _make_fake_renderer(rows_for_levels)
    monkeypatch.setattr(renderer_mod, 'LadderExerciseRenderer', fake_renderer_cls)
    monkeypatch.setattr(qd, '_semantic_class_for_sense', lambda db, sense_id: semantic_class)
    monkeypatch.setattr(qd, 'coverage_gaps', lambda db, sense_ids=None, language_id=None: [])
    return _FakePipeline, fake_renderer_cls


def test_families_to_levels_maps_form_production_to_l4_for_an_english_verb():
    """Sanity check on the mapping itself before trusting it in `_regenerate`."""
    assert families_to_levels(['form_production'], 'action', LANG_EN) == {4, 9}


def test_regenerate_scoped_delete_leaves_other_levels_untouched(monkeypatch):
    fake_pipeline_cls, fake_renderer_cls = _patch_regenerate_deps(
        monkeypatch, semantic_class='action', rows_for_levels={4, 9},
    )
    db = _FakeDB()
    row = {
        'sense_id': 42, 'language_id': LANG_EN, 'reason': qd.REASON_COVERAGE_GAP,
        'detail': {'missing_families': ['form_production']},
    }

    ok, detail = qd._regenerate(db, row)

    assert ok is True
    assert fake_pipeline_cls.last_levels == {4, 9}
    assert fake_renderer_cls.last_levels == {4, 9}
    assert detail['scoped_levels'] == [4, 9]

    delete_calls = [c for c in db.calls if c['table'] == 'exercises' and c['op'] == 'delete']
    assert len(delete_calls) == 1
    assert delete_calls[0]['filters']['in_'] == [('ladder_level', [4, 9])], (
        'a scoped regen must delete only the requested level(s)'
    )

    insert_calls = [c for c in db.calls if c['table'] == 'exercises' and c['op'] == 'insert']
    assert len(insert_calls) == 1
    assert {row['ladder_level'] for row in insert_calls[0]['payload']} == {4, 9}


def test_regenerate_full_regen_still_full(monkeypatch):
    """A `regen` row (no missing_families) keeps doing a full, unscoped
    regeneration -- parity with pre-TASK-811 behaviour."""
    fake_pipeline_cls, fake_renderer_cls = _patch_regenerate_deps(
        monkeypatch, semantic_class='action', rows_for_levels={1, 3, 4, 6, 7},
    )
    db = _FakeDB()
    row = {
        'sense_id': 43, 'language_id': LANG_EN, 'reason': qd.REASON_REGEN,
        'detail': {},
    }

    ok, detail = qd._regenerate(db, row)

    assert ok is True
    assert fake_pipeline_cls.last_levels is None
    assert fake_renderer_cls.last_levels is None
    assert 'scoped_levels' not in detail

    delete_calls = [c for c in db.calls if c['table'] == 'exercises' and c['op'] == 'delete']
    assert len(delete_calls) == 1
    assert 'in_' not in delete_calls[0]['filters'], (
        'an unscoped regen must not narrow the delete by ladder_level'
    )


def test_regenerate_coverage_gap_with_unmappable_family_falls_back_to_full(monkeypatch):
    """A family that maps to no known level (bad data, or a family this
    language/semantic_class has no capability row for) must not scope to
    nothing -- it falls back to a full regen instead."""
    fake_pipeline_cls, fake_renderer_cls = _patch_regenerate_deps(
        monkeypatch, semantic_class='action', rows_for_levels={1, 3, 4, 6, 7},
    )
    db = _FakeDB()
    row = {
        'sense_id': 44, 'language_id': LANG_EN, 'reason': qd.REASON_COVERAGE_GAP,
        'detail': {'missing_families': ['not_a_real_family']},
    }

    ok, detail = qd._regenerate(db, row)

    assert ok is True
    assert fake_pipeline_cls.last_levels is None
    assert fake_renderer_cls.last_levels is None
