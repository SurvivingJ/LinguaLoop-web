"""TASK-525 — the tl_nl uniqueness judge.

The eval scored tl_nl at 0% accept. The translations were fine; the distractors
were also-correct, so a learner who chose right could be marked wrong. This
judge drops those options and blocks the item when too few survive.

The single most important thing under test is the **rating orientation**. The
Likert scale runs in the direction of keep (5 = ideal distractor, 1 =
also-correct), matching every other ladder judge so ``likert_to_verdict``
applies with no negation. Written the intuitive way round the judge would keep
exactly what it exists to remove, and the item would still look well-formed —
so the direction is asserted here rather than trusted to the prompt.

LLM-free and DB-free: the template and ``call_llm`` boundary are monkeypatched.
"""

import pytest

from services.exercise_generation.generators import translation as transmod
from services.exercise_generation.judges import translation_uniqueness as tumod
from services.exercise_generation.judges.translation_uniqueness import (
    MIN_SURVIVING_DISTRACTORS,
    filter_translation_distractors,
    judge_translation_item,
)

LANG_ZH, LANG_EN, LANG_JA = 1, 2, 3

_TEMPLATE = (
    'src={tl_sentence} key={correct_translation} nl={nl_language}\n'
    '{candidates_numbered}'
)

TL = '我每天早上都喝咖啡。'
KEY = 'I drink coffee every morning.'


@pytest.fixture(autouse=True)
def _clear_cfg_cache():
    tumod._cfg_cache.clear()
    yield
    tumod._cfg_cache.clear()


def _patch(monkeypatch, reply, template=_TEMPLATE, raises=None):
    """Wire the judge to a fixed reply; returns the captured prompt list."""
    prompts: list[str] = []

    def _cfg(db, task_name, language_id):
        if isinstance(template, Exception):
            raise template
        return {'template': template, 'model': 'test-model',
                'provider': 'openrouter', 'version': 1}

    def _call(prompt, **kwargs):
        prompts.append(prompt)
        if raises:
            raise raises
        return reply

    monkeypatch.setattr(tumod, 'get_template_config', _cfg)
    monkeypatch.setattr(tumod, 'call_llm', _call)
    monkeypatch.setattr(tumod, 'log_judge_verdict', lambda **kw: None)
    return prompts


def _ratings(**by_index):
    """Build a judge reply: _ratings(**{'1': 5, '2': 1})."""
    return {k: {'rating': v, 'reason': 'because'} for k, v in by_index.items()}


# ---------------------------------------------------------------------------
# Rating orientation — the thing that must never silently flip
# ---------------------------------------------------------------------------

def test_rating_five_keeps_the_distractor(monkeypatch):
    """5 = clearly NOT an acceptable translation = an ideal distractor."""
    _patch(monkeypatch, _ratings(**{'1': 5}))

    kept, meta = filter_translation_distractors(
        None, TL, KEY, ['I eat bread every evening.'], LANG_ZH, 'en')

    assert kept == ['I eat bread every evening.']
    assert meta['rejected'] == 0


def test_rating_one_drops_the_distractor(monkeypatch):
    """1 = a fully acceptable rendering = also-correct = must go.

    This is the planted-defect case from the AC.
    """
    _patch(monkeypatch, _ratings(**{'1': 1}))
    planted = 'Every morning I have coffee.'      # a valid rendering of TL

    kept, meta = filter_translation_distractors(
        None, TL, KEY, [planted], LANG_ZH, 'en')

    assert kept == []
    assert meta['rejected'] == 1
    assert meta['rejected_items'] == [planted]


@pytest.mark.parametrize('rating,expect_kept', [
    (5, True), (4, True), (3, True), (2, False), (1, False),
])
def test_the_full_scale_runs_in_the_keep_direction(monkeypatch, rating, expect_kept):
    _patch(monkeypatch, _ratings(**{'1': rating}))

    kept, _ = filter_translation_distractors(None, TL, KEY, ['x'], LANG_ZH, 'en')

    assert bool(kept) is expect_kept


def test_mixed_batch_drops_only_the_also_correct_options(monkeypatch):
    _patch(monkeypatch, _ratings(**{'1': 5, '2': 1, '3': 4}))

    kept, meta = filter_translation_distractors(
        None, TL, KEY, ['wrong-a', 'also-right', 'wrong-b'], LANG_ZH, 'en')

    assert kept == ['wrong-a', 'wrong-b']
    assert meta['rejected_items'] == ['also-right']


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def test_candidates_are_numbered_from_one(monkeypatch):
    prompts = _patch(monkeypatch, _ratings(**{'1': 5, '2': 5}))

    filter_translation_distractors(None, TL, KEY, ['alpha', 'beta'], LANG_ZH, 'en')

    assert '1. alpha' in prompts[0]
    assert '2. beta' in prompts[0]


def test_the_source_sentence_and_key_reach_the_prompt(monkeypatch):
    prompts = _patch(monkeypatch, _ratings(**{'1': 5}))

    filter_translation_distractors(None, TL, KEY, ['x'], LANG_ZH, 'en')

    assert TL in prompts[0]
    assert KEY in prompts[0]
    assert 'nl=en' in prompts[0]


def test_a_missing_key_translation_is_labelled_not_blank(monkeypatch):
    prompts = _patch(monkeypatch, _ratings(**{'1': 5}))

    filter_translation_distractors(None, TL, '', ['x'], LANG_ZH, 'en')

    assert '(none provided)' in prompts[0]


# ---------------------------------------------------------------------------
# Whole-item verdict
# ---------------------------------------------------------------------------

def test_item_survives_with_enough_unique_distractors(monkeypatch):
    _patch(monkeypatch, _ratings(**{'1': 5, '2': 5}))

    kept, outcome, _ = judge_translation_item(
        None, TL, KEY, ['a', 'b'], LANG_ZH, 'en')

    assert outcome.verdict == 'accept'
    assert len(kept) == 2
    assert outcome.confidence == 2.0


def test_item_is_blocked_when_too_few_distractors_survive(monkeypatch):
    """AC: 'Block items with <2 surviving distractors'."""
    _patch(monkeypatch, _ratings(**{'1': 5, '2': 1, '3': 1}))

    kept, outcome, _ = judge_translation_item(
        None, TL, KEY, ['a', 'b', 'c'], LANG_ZH, 'en')

    assert len(kept) < MIN_SURVIVING_DISTRACTORS
    assert outcome.verdict == 'reject'
    assert 'blocked' in outcome.reason


def test_the_block_threshold_is_two():
    assert MIN_SURVIVING_DISTRACTORS == 2


# ---------------------------------------------------------------------------
# Fail-open
# ---------------------------------------------------------------------------

def test_llm_failure_keeps_every_distractor(monkeypatch):
    _patch(monkeypatch, None, raises=RuntimeError('502 from provider'))

    kept, meta = filter_translation_distractors(
        None, TL, KEY, ['a', 'b'], LANG_ZH, 'en')

    assert kept == ['a', 'b']
    assert meta['rejected'] == 0


def test_template_failure_keeps_every_distractor(monkeypatch):
    _patch(monkeypatch, None, template=LookupError('no such prompt'))

    kept, _ = filter_translation_distractors(None, TL, KEY, ['a'], LANG_ZH, 'en')

    assert kept == ['a']


def test_non_dict_response_keeps_every_distractor(monkeypatch):
    _patch(monkeypatch, ['not', 'a', 'dict'])

    kept, _ = filter_translation_distractors(None, TL, KEY, ['a'], LANG_ZH, 'en')

    assert kept == ['a']


def test_a_missing_per_candidate_verdict_never_manufactures_a_reject(monkeypatch):
    _patch(monkeypatch, _ratings(**{'1': 1}))     # says nothing about candidate 2

    kept, _ = filter_translation_distractors(
        None, TL, KEY, ['also-right', 'unjudged'], LANG_ZH, 'en')

    assert kept == ['unjudged']


def test_an_unparseable_rating_keeps_the_distractor(monkeypatch):
    _patch(monkeypatch, {'1': {'rating': 'very high'}})

    kept, _ = filter_translation_distractors(None, TL, KEY, ['a'], LANG_ZH, 'en')

    assert kept == ['a']


def test_no_distractors_is_not_an_error(monkeypatch):
    prompts = _patch(monkeypatch, {})

    kept, meta = filter_translation_distractors(None, TL, KEY, [], LANG_ZH, 'en')

    assert kept == []
    assert meta['rejected'] == 0
    assert prompts == [], 'no LLM spend with nothing to judge'


# ---------------------------------------------------------------------------
# Generator wiring
# ---------------------------------------------------------------------------

class _StubGen(transmod.TlNlTranslationGenerator):
    """TlNlTranslationGenerator with its DB and LLM boundaries removed."""

    def __init__(self, llm_reply):
        self.db = object()
        self.language_id = LANG_ZH
        self.model = 'test-model'
        self.source_type = 'vocabulary'
        self.nl_language_code = 'en'
        self._llm_reply = llm_reply

    def load_prompt_template(self, task_name):
        return 'tl={tl_sentence} nl={nl_language}'

    def call_llm(self, prompt, **kwargs):
        return self._llm_reply

    def _get_language_code(self):
        return 'zh'


def _sentence():
    return {'sentence': TL, 'test_id': 't-1'}


def test_generator_ships_an_item_whose_distractors_are_unique(monkeypatch):
    _patch(monkeypatch, _ratings(**{'1': 5, '2': 5}))
    gen = _StubGen({'correct_nl': KEY,
                    'wrong_options': ['I eat bread.', 'She reads books.']})

    content = gen.generate_one(_sentence(), source_id=1)

    assert content is not None
    assert content['nl']['en']['options'][0] == KEY
    assert len(content['nl']['en']['options']) == 3


def test_generator_blocks_an_item_with_two_correct_answers(monkeypatch):
    """End to end: the eval failure no longer reaches the corpus."""
    _patch(monkeypatch, _ratings(**{'1': 1, '2': 1}))
    gen = _StubGen({'correct_nl': KEY,
                    'wrong_options': ['Every morning I have coffee.',
                                      'I have coffee each morning.']})

    assert gen.generate_one(_sentence(), source_id=1) is None


def test_generator_attaches_the_judge_sidecar(monkeypatch):
    _patch(monkeypatch, _ratings(**{'1': 5, '2': 5}))
    gen = _StubGen({'correct_nl': KEY, 'wrong_options': ['a', 'b']})

    content = gen.generate_one(_sentence(), source_id=1)

    assert 'translation_uniqueness' in content['__judge_metas']
    assert content['__judge_metas']['translation_uniqueness']['kept'] == 2


def test_generator_still_rejects_a_malformed_llm_response(monkeypatch):
    _patch(monkeypatch, _ratings(**{'1': 5}))
    gen = _StubGen({'correct_nl': '', 'wrong_options': []})

    assert gen.generate_one(_sentence(), source_id=1) is None


def test_capability_matrix_points_translation_types_at_this_judge():
    """The matrix reserved the judge_key; make sure it still matches."""
    from services.vocabulary_ladder.config import CAPABILITY_MATRIX

    keys = {cap['judge_key'] for cap in CAPABILITY_MATRIX
            if cap['type_code'] in ('tl_nl_translation', 'nl_tl_translation')}

    assert keys == {'translation_uniqueness'}
