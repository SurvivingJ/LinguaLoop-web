"""The span↔form invariant for ``dt_error_instance`` rows.

The invariant, on every row the grader persists:

    reference[span_reference]      == corrected_form
    reproduction[span_reproduction] == learner_form

(with the empty-form omission/addition point as the one legitimate exception —
a zero-width or in-bounds span whose form is ``''``.)

``_reconcile_span_form`` (TASK-624/634) exists to *establish* this invariant, but
until now nothing anywhere asserted it had actually been established. That gap is
what let 15 of the 16 live ``dt_error_instance`` rows — all written before the
reconciler landed on 2026-07-19 — sit misaligned for seven weeks, until one of them
surfaced downstream as a cloze card whose prompt blanked one clause while asking for
a different one, i.e. a prompt containing its own answer.

The repair logic was never the missing piece. The tripwire on it was. These tests
are that tripwire: they run the invariant over the decoder's output and over the
rows that reach the ``dt_error_instance`` insert, and one of them proves the
tripwire is falsifiable by neutering the reconciler and watching it fire.

DB-free and OpenRouter-free — pure functions plus a call-capturing fake db.
"""

import pytest

from routes import dual_translation as dt_routes
from services.dual_translation import grader_cascade


TAXONOMY_CFG = {
    'pairs': {'en': {'subtypes': ['article_omission', 'preposition']}},
    'templates': {'article_omission': {'zh': '你写的是{learner_form}，应改为{corrected_form}。'}},
}
SUBTYPES = ['article_omission', 'preposition']


# ---------------------------------------------------------------------------
# The invariant itself
# ---------------------------------------------------------------------------

def assert_span_form_aligned(row: dict, reproduction: str, reference: str) -> None:
    """Assert one persisted-shape error row satisfies the span↔form invariant.

    An empty form is the legitimate omission/addition point: it only has to sit at
    an in-bounds offset pair, since there is no text at that point to match.
    """
    for text, span_key, form_key in (
        (reference, 'span_reference', 'corrected_form'),
        (reproduction, 'span_reproduction', 'learner_form'),
    ):
        span, form = row[span_key], row[form_key]
        assert isinstance(span, list) and len(span) == 2, f'{span_key}={span!r} is not an offset pair'
        lo, hi = span
        assert 0 <= lo <= hi <= len(text), f'{span_key}={span!r} out of bounds for len {len(text)}'
        if form:
            assert text[lo:hi] == form, (
                f'{span_key}={span!r} slices {text[lo:hi]!r} but {form_key} is {form!r}'
            )


def _base_raw(**overrides):
    raw = {
        'span_repro': [0, 1], 'span_ref': [0, 1],
        'category': 0, 'source': 0, 'severity': 0, 'subtype': 0,
        'learner_form': 'x', 'corrected_form': 'y',
        'confidence': 0.8, 'is_mistake': False,
    }
    raw.update(overrides)
    return raw


def _decode(raws, reproduction, reference, l2_code=''):
    return grader_cascade._decode_errors(
        raws, SUBTYPES, TAXONOMY_CFG, 'zh', reproduction, reference, l2_code,
    )


# ---------------------------------------------------------------------------
# The live regression: dt_error_instance id=5, the row behind the leaking card
# ---------------------------------------------------------------------------

# Verbatim from project kpfqrjtfxmujzolwsvdq, passage 1 / submission 2.
LIVE_REFERENCE = (
    '我最喜欢的T恤是一件非常特别的衣服。它不是那种很贵的牌子，也不是最新款式的，'
    '但它是我所有衣服里最喜欢的。这件T恤是蓝色的，颜色很正，洗了很多次也不会褪色。'
    '它的布料很舒服，穿在身上软软的，很透气，夏天穿也不会觉得热。'
)
LIVE_REPRODUCTION = (
    '我最喜欢的T恤真是件特别衣服。不是很贵的品牌，也不是最新的风格，但还是我最喜欢的衣服。'
    '这件T恤是蓝色的，真丰颜色。不管多少次洗，颜色不退色。'
    '这件T恤很舒服，对皮肤很软、很舒服、甚至在很热的夏天很凉快。'
)
# The spans as they were actually stored, by the pre-reconciler decoder.
LIVE_STORED_SPAN_REF = [23, 29]
LIVE_STORED_SPAN_REPRO = [21, 28]
LIVE_CORRECTED_FORM = '也不是最新款式的'
LIVE_LEARNER_FORM = '也不是最新的风格'


def test_live_stored_span_violated_the_invariant():
    """What the bug looked like: the stored span sliced a different clause
    (``很贵的牌子，``) than the one ``corrected_form`` names. Blanking that span
    left the answer sitting in the cloze prompt."""
    lo, hi = LIVE_STORED_SPAN_REF
    assert LIVE_REFERENCE[lo:hi] != LIVE_CORRECTED_FORM
    assert LIVE_REFERENCE[lo:hi] == '很贵的牌子，'


def test_current_reconciler_relocates_the_live_drifted_spans():
    """The decisive check: the *current* grader, fed the exact inputs that produced
    the leaking card, relocates both spans onto their forms. The defect is
    historical data, not live prompt quality — no re-prompting is warranted."""
    span_ref, form_ref = grader_cascade._reconcile_span_form(
        LIVE_REFERENCE, LIVE_STORED_SPAN_REF, LIVE_CORRECTED_FORM, 'zh',
    )
    assert span_ref == [29, 37]
    assert LIVE_REFERENCE[span_ref[0]:span_ref[1]] == form_ref == LIVE_CORRECTED_FORM

    span_repro, form_repro = grader_cascade._reconcile_span_form(
        LIVE_REPRODUCTION, LIVE_STORED_SPAN_REPRO, LIVE_LEARNER_FORM, 'zh',
    )
    assert span_repro == [23, 31]
    assert LIVE_REPRODUCTION[span_repro[0]:span_repro[1]] == form_repro == LIVE_LEARNER_FORM


def test_live_row_decoded_today_satisfies_the_invariant():
    """End-to-end through ``_decode_error``, not just the reconciler."""
    raw = _base_raw(
        span_repro=LIVE_STORED_SPAN_REPRO, learner_form=LIVE_LEARNER_FORM,
        span_ref=LIVE_STORED_SPAN_REF, corrected_form=LIVE_CORRECTED_FORM,
    )
    rows = _decode([raw], LIVE_REPRODUCTION, LIVE_REFERENCE, 'zh')
    assert len(rows) == 1
    assert_span_form_aligned(rows[0], LIVE_REPRODUCTION, LIVE_REFERENCE)


# ---------------------------------------------------------------------------
# The invariant over the decoder's whole output, on an adversarial matrix
# ---------------------------------------------------------------------------

DRIFT_CASES = [
    # (id, reproduction, reference, l2_code, raw overrides)
    ('end_off_by_one', 'the quick brown fox', 'the rapid brown fox', 'en',
     dict(span_repro=[4, 8], learner_form='quick', span_ref=[4, 8], corrected_form='rapid')),
    ('start_off_by_one', 'the quick brown fox', 'the rapid brown fox', 'en',
     dict(span_repro=[3, 9], learner_form='quick', span_ref=[3, 9], corrected_form='rapid')),
    ('drifted_to_other_clause', LIVE_REPRODUCTION, LIVE_REFERENCE, 'zh',
     dict(span_repro=LIVE_STORED_SPAN_REPRO, learner_form=LIVE_LEARNER_FORM,
          span_ref=LIVE_STORED_SPAN_REF, corrected_form=LIVE_CORRECTED_FORM)),
    ('repeated_token', 'go now and go home', 'go then and go home', 'en',
     dict(span_repro=[11, 13], learner_form='go', span_ref=[12, 14], corrected_form='go')),
    ('span_out_of_bounds', 'hello world', 'hello there', 'en',
     dict(span_repro=[900, 999], learner_form='world', span_ref=[900, 999], corrected_form='there')),
    ('malformed_end', 'hello world', 'hello there', 'en',
     dict(span_repro=[6, 'x'], learner_form='world', span_ref=[6, None], corrected_form='there')),
    ('fullwidth_fold', 'ＡＢＣ です', 'ABC desu', 'ja',
     dict(span_repro=[0, 3], learner_form='ABC', span_ref=[0, 3], corrected_form='ABC')),
    ('casefold', 'The dog', 'The cat', 'en',
     dict(span_repro=[4, 7], learner_form='DOG', span_ref=[4, 7], corrected_form='CAT')),
    ('empty_form_omission_point', 'abcdefghij', 'XYabcdefghij', 'en',
     dict(span_repro=[7, 7], learner_form='', span_ref=[0, 2], corrected_form='XY')),
    ('zero_width_at_end', 'abcdefghij', 'abcdefghijZZ', 'en',
     dict(span_repro=[10, 10], learner_form='', span_ref=[10, 12], corrected_form='ZZ')),
]


@pytest.mark.parametrize('case_id, repro, ref, l2, overrides', DRIFT_CASES,
                         ids=[c[0] for c in DRIFT_CASES])
def test_every_decoded_error_satisfies_the_invariant(case_id, repro, ref, l2, overrides):
    """No matter how the model misreports a span, a row that SURVIVES decode must
    satisfy the invariant. Persisting a misaligned row is never acceptable.

    Every case here is also pinned to survive. Dropping would satisfy the
    invariant vacuously, and each of these is a *real* error the reconciler is
    supposed to rescue — a case that starts being dropped is a regression in its
    own right (that is precisely the loss TASK-624 was built to stop)."""
    rows = _decode([_base_raw(**overrides)], repro, ref, l2)
    assert len(rows) == 1, 'the reconciler must rescue this error, not drop it'
    assert_span_form_aligned(rows[0], repro, ref)


def test_whole_batch_decode_satisfies_the_invariant():
    """The batch path (``_decode_errors``), not just one error at a time — the
    drifted live rows were written 14-at-a-time from a single submission."""
    repro, ref = LIVE_REPRODUCTION, LIVE_REFERENCE
    raws = [
        _base_raw(span_repro=[0, 4], learner_form='我最喜欢的T恤',
                  span_ref=[0, 4], corrected_form='我最喜欢的T恤'),
        _base_raw(span_repro=LIVE_STORED_SPAN_REPRO, learner_form=LIVE_LEARNER_FORM,
                  span_ref=LIVE_STORED_SPAN_REF, corrected_form=LIVE_CORRECTED_FORM),
        _base_raw(span_repro=[50, 53], learner_form='蓝色的',
                  span_ref=[55, 58], corrected_form='蓝色的'),
    ]
    rows = _decode(raws, repro, ref, 'zh')
    assert len(rows) == 3
    for row in rows:
        assert_span_form_aligned(row, repro, ref)


def test_unlocatable_form_is_dropped_not_persisted_misaligned():
    """The counter-case that keeps the invariant from being satisfiable by
    accident: a form absent from its text must be DROPPED, not silently written
    with whatever span the model guessed."""
    rows = _decode(
        [_base_raw(span_repro=[0, 3], learner_form='zzz', span_ref=[0, 3], corrected_form='hel')],
        'hello world', 'hello there', 'en',
    )
    assert rows == []


# ---------------------------------------------------------------------------
# The tripwire is falsifiable — it fires when the reconciler stops working
# ---------------------------------------------------------------------------

def test_invariant_fails_when_the_reconciler_is_neutered(monkeypatch):
    """A happy-path assertion is not evidence a guard fires (TASK-729). Replace
    ``_reconcile_span_form`` with the pre-TASK-624 pass-through — take the model's
    span and form as given — and the invariant must go RED on the live case. If
    this test ever passes vacuously, the assertion above is decorative."""
    monkeypatch.setattr(
        grader_cascade, '_reconcile_span_form',
        lambda text, span, form, language_code='': (list(span) if isinstance(span, (list, tuple)) else None,
                                                    form if isinstance(form, str) else ''),
    )
    raw = _base_raw(
        span_repro=LIVE_STORED_SPAN_REPRO, learner_form=LIVE_LEARNER_FORM,
        span_ref=LIVE_STORED_SPAN_REF, corrected_form=LIVE_CORRECTED_FORM,
    )
    rows = _decode([raw], LIVE_REPRODUCTION, LIVE_REFERENCE, 'zh')
    assert len(rows) == 1, 'the neutered decoder should still emit the row — that is the bug'
    with pytest.raises(AssertionError, match='span_reference'):
        assert_span_form_aligned(rows[0], LIVE_REPRODUCTION, LIVE_REFERENCE)


# ---------------------------------------------------------------------------
# The invariant at the persistence boundary — the rows that actually land in
# dt_error_instance, not just the decoder's return value
# ---------------------------------------------------------------------------

class _CapturingDB:
    """Minimal supabase-py stand-in that records ``(table, method, payload)``."""

    def __init__(self):
        self.calls = []

    def table(self, name):
        self._table = name
        return self

    def insert(self, payload):
        self.calls.append((self._table, 'insert', payload))
        return self

    def update(self, payload):
        self.calls.append((self._table, 'update', payload))
        return self

    def eq(self, *_args):
        return self

    def execute(self):
        return self


def _persisted_error_rows(db):
    return next(p for name, method, p in db.calls if name == 'dt_error_instance' and method == 'insert')


def test_every_row_reaching_the_dt_error_instance_insert_satisfies_the_invariant():
    """Decode → persist, asserting on the actual insert payload. This is the
    'every persisted row' form of the invariant: whatever the decoder does, the
    rows handed to ``dt_error_instance`` must be aligned on BOTH axes."""
    repro, ref = LIVE_REPRODUCTION, LIVE_REFERENCE
    raws = [
        _base_raw(span_repro=LIVE_STORED_SPAN_REPRO, learner_form=LIVE_LEARNER_FORM,
                  span_ref=LIVE_STORED_SPAN_REF, corrected_form=LIVE_CORRECTED_FORM),
        _base_raw(span_repro=[50, 52], learner_form='蓝色的',
                  span_ref=[55, 57], corrected_form='蓝色的'),
        # Unlocatable — must not reach the insert at all.
        _base_raw(span_repro=[0, 3], learner_form='qqqq', span_ref=[0, 3], corrected_form='wwww'),
    ]
    contract = {
        'scores': {'accuracy': 3}, 'overall_band': 3, 'diff': [], 'grader_trace': {'tier': 'tier1'},
        'errors': _decode(raws, repro, ref, 'zh'),
    }
    assert len(contract['errors']) == 2

    db = _CapturingDB()
    dt_routes._persist_grade(db, 5, repro, 'key-1', contract)

    rows = _persisted_error_rows(db)
    assert len(rows) == 2
    for row in rows:
        assert row['submission_id'] == 5
        assert_span_form_aligned(row, repro, ref)


def test_reproduction_side_invariant_holds_against_the_text_persist_writes_back():
    """The reproduction-side equivalent, pinned to the exact string ``_persist_grade``
    writes onto ``dt_submission.reproduction`` — the spans index into THAT text, so
    checking them against anything else would be checking the wrong string."""
    repro, ref = LIVE_REPRODUCTION, LIVE_REFERENCE
    contract = {
        'scores': {}, 'overall_band': 3, 'diff': [], 'grader_trace': {},
        'errors': _decode(
            [_base_raw(span_repro=LIVE_STORED_SPAN_REPRO, learner_form=LIVE_LEARNER_FORM,
                       span_ref=LIVE_STORED_SPAN_REF, corrected_form=LIVE_CORRECTED_FORM)],
            repro, ref, 'zh',
        ),
    }

    db = _CapturingDB()
    dt_routes._persist_grade(db, 5, repro, None, contract)

    written_repro = next(
        p for name, method, p in db.calls if name == 'dt_submission' and method == 'update'
    )['reproduction']
    for row in _persisted_error_rows(db):
        lo, hi = row['span_reproduction']
        assert written_repro[lo:hi] == row['learner_form']
