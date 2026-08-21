"""Test generation must abort on a judge outage, not ship unjudged questions.

TASK-727/728/729. `batch_mode()` (TASK-510) exists because two total outages
came from a delisted OpenRouter model slug: every judge fell open with
`safe_accept()` and a whole batch shipped unjudged. The guard was wired into
exercise generation and never into *test* generation, so until TASK-727 a bulk
test run with a dead slug or a missing `prompt_templates` row wrote unjudged
questions to the `questions` table with nothing louder than a log warning.

Wiring the guard is two lines. The failure mode this file actually defends
against is the *second* one: `JudgeUnavailable` is an ordinary exception and
`orchestrator.py` has fifteen `except Exception` blocks, five of them around
the generation loop. Swallowed there, a loud abort degrades into "that one test
quietly failed to generate" — quieter than the bug it replaces, and the exact
trap `judges/base.py`'s module docstring warns about.

Four properties are pinned, and the middle two matter as much as the first:

1. **The guard fires.** A judge whose template will not load aborts the batch
   and NOTHING is written — no test row, no question rows.
2. **The serve path still fails open.** The identical outage outside
   `batch_mode()` still returns `safe_accept()` and still yields a question. A
   learner waiting on a session must never be blocked by a dead judge.
3. **`accept_item` still never aborts.** One missing per-distractor rating in
   an otherwise healthy response is not an outage; aborting a large batch over
   it would be the worse failure.
4. **Nothing on the path swallows it.** Pinned per layer, so a later refactor
   that widens a `try` is caught here rather than in production.

House rule behind (1): four guardrails in this codebase were silently inert for
months because nobody checked one actually fired. Every abort assertion below
therefore also asserts on what was *not* written.

Note for anyone extending this file: judges only run at `difficulty > 2`
(`run_judges = difficulty > 2` in `_generate_test`), so a fixture batch at d1/d2
never reaches a judge and would pass no matter how broken the guard is.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

import services.exercise_generation.judges.answer_entailment as ae_mod
import services.exercise_generation.judges.distractor_plausibility as dp_mod
from services.exercise_generation.judges.base import (
    JudgeUnavailable,
    batch_mode,
    is_batch_mode,
)
from services.test_generation.agents.question_generator import QuestionGenerator
from services.test_generation.orchestrator import (
    BatchConfig,
    TestGenerationOrchestrator,
)
from services.test_generation.schemas import (
    AnswerEntailmentVerdict,
    DistractorPlausibilityVerdict,
    MCQuestion,
)

PROSE = (
    'The harbour seals return to the bay each spring. They haul out on the '
    'flat rocks near the point, where the water is shallow and the current is '
    'weak enough for the pups to swim beside their mothers.'
)
DISTRACTORS = ['in the autumn', 'at midwinter', 'every other year']


# ---------------------------------------------------------------------------
# Doubles
# ---------------------------------------------------------------------------

def _dead_template(_db, _language_id):
    """The outage that caused the real incidents.

    Both judges funnel a template-load failure into
    `safe_accept('template load error: ...')` — the exact chokepoint
    `guard_fail_open` sits on (answer_entailment.py:131,
    distractor_plausibility.py:182). A delisted model slug arrives one line
    later and lands on the same helper.
    """
    raise RuntimeError(
        'no active prompt_templates row for lang=1 (simulated outage)'
    )


def _healthy_ae_cfg(_db, _language_id):
    return {'template': 'entailment {0} {1} {2}', 'model': 'test-model',
            'version': 3}


def _healthy_dp_cfg(_db, _language_id):
    return {'template': 'plausibility {0} {1} {2} {3} {4} {5}',
            'model': 'test-model', 'version': 7}


def _ae_accepts(*_a, **_kw):
    return AnswerEntailmentVerdict(rating=5, reason='stated explicitly')


def _dp_accepts(*_a, **_kw):
    return DistractorPlausibilityVerdict(
        fit=[5, 5, 5], confusability=[2, 2, 2],
        reasons=['on subject'] * 3,
    )


def _question(text='When do the seals return?'):
    return MCQuestion(
        question_text=text,
        choices=['in the spring', *DISTRACTORS],
        answer='in the spring',
        correct_answer_index=0,
    )


def _generator():
    """A QuestionGenerator without __init__ — it reads live config."""
    gen = object.__new__(QuestionGenerator)
    gen.api_key = 'unused'
    gen.model = 'test-model'
    gen.api_call_count = 0
    gen._validator = SimpleNamespace(
        validate_question=lambda *_a, **_kw: (True, None)
    )
    gen.last_rejections = []
    return gen


def _healthy_judges():
    """Patch set where both judges answer normally."""
    return (
        patch.object(ae_mod, '_load_cfg', _healthy_ae_cfg),
        patch.object(ae_mod, 'call_llm', _ae_accepts),
        patch.object(dp_mod, '_load_cfg', _healthy_dp_cfg),
        patch.object(dp_mod, 'call_llm', _dp_accepts),
    )


# ---------------------------------------------------------------------------
# 1. The chokepoint itself, through the real judge functions
# ---------------------------------------------------------------------------

def test_distractor_judge_outage_aborts_inside_a_batch():
    with patch.object(dp_mod, '_load_cfg', _dead_template):
        with batch_mode():
            with pytest.raises(JudgeUnavailable):
                dp_mod.judge_distractor_plausibility(
                    db=MagicMock(), passage=PROSE, question_text='Q',
                    answer='in the spring', distractors=DISTRACTORS,
                    language_id=1, type_code='literal_detail',
                )


def test_entailment_judge_outage_aborts_inside_a_batch():
    """Asserted separately: `_apply_judges` calls entailment FIRST, so a test
    that only covers the distractor judge would pass with entailment's guard
    missing entirely."""
    with patch.object(ae_mod, '_load_cfg', _dead_template):
        with batch_mode():
            with pytest.raises(JudgeUnavailable):
                ae_mod.judge_answer_entailment(
                    db=MagicMock(), passage=PROSE, question_text='Q',
                    answer='in the spring', language_id=1,
                )


def test_the_same_outage_fails_open_when_serving():
    """A learner waiting on a session is never blocked by a dead judge."""
    with patch.object(dp_mod, '_load_cfg', _dead_template), \
         patch.object(ae_mod, '_load_cfg', _dead_template):
        assert not is_batch_mode()

        dp = dp_mod.judge_distractor_plausibility(
            db=MagicMock(), passage=PROSE, question_text='Q',
            answer='in the spring', distractors=DISTRACTORS,
            language_id=1, type_code='literal_detail',
        )
        ae = ae_mod.judge_answer_entailment(
            db=MagicMock(), passage=PROSE, question_text='Q',
            answer='in the spring', language_id=1,
        )

    assert [o.verdict for o in dp] == ['accept'] * 3
    assert ae.verdict == 'accept'


def test_one_missing_rating_does_not_abort_a_batch():
    """`accept_item`, not `safe_accept`: the judge answered, one entry is blank.

    Aborting a large batch over a single unparseable rating would be a worse
    failure than shipping that one item — see `accept_item`'s docstring.
    """
    def _one_gap(*_a, **_kw):
        return DistractorPlausibilityVerdict(
            fit=[None, 5, 4], confusability=[None, 2, 2],
            reasons=['', 'on subject', 'on subject'],
        )

    with patch.object(dp_mod, '_load_cfg', _healthy_dp_cfg), \
         patch.object(dp_mod, 'call_llm', _one_gap):
        with batch_mode():
            outcomes = dp_mod.judge_distractor_plausibility(
                db=MagicMock(), passage=PROSE, question_text='Q',
                answer='in the spring', distractors=DISTRACTORS,
                language_id=1, type_code='literal_detail',
            )

    assert len(outcomes) == 3
    assert outcomes[0].verdict == 'accept'
    assert outcomes[0].confidence is None      # rated by no axis at all


def test_entailment_with_no_rating_does_not_abort_a_batch():
    def _no_rating(*_a, **_kw):
        return AnswerEntailmentVerdict(rating=None, reason='could not tell')

    with patch.object(ae_mod, '_load_cfg', _healthy_ae_cfg), \
         patch.object(ae_mod, 'call_llm', _no_rating):
        with batch_mode():
            outcome = ae_mod.judge_answer_entailment(
                db=MagicMock(), passage=PROSE, question_text='Q',
                answer='in the spring', language_id=1,
            )

    assert outcome.verdict == 'accept'


# ---------------------------------------------------------------------------
# 2. The question-generation layers must not swallow it
# ---------------------------------------------------------------------------

def test_apply_judges_lets_the_abort_through():
    """`_apply_judges` used to promise it "never raises". It does now."""
    gen = _generator()
    with patch.object(ae_mod, '_load_cfg', _dead_template):
        with batch_mode():
            with pytest.raises(JudgeUnavailable):
                gen._apply_judges(
                    q_entry={'question': 'Q', 'answer': 'in the spring',
                             'choices': ['in the spring', *DISTRACTORS]},
                    prose=PROSE, db=MagicMock(), language_id=1,
                    type_code='literal_detail',
                )


def test_retry_loop_does_not_convert_the_abort_into_a_missing_question():
    """The regression this pins.

    `_generate_validated_question` wraps `_generate_single_question` in
    `except Exception` and retries. If the judge call ever moves inside that
    `try`, a judge outage becomes two wasted regeneration attempts and a
    silently absent question — the abort turned back into a shrug.
    """
    gen = _generator()
    with patch.object(gen, '_generate_single_question',
                      lambda *_a, **_kw: _question()), \
         patch.object(dp_mod, '_load_cfg', _dead_template), \
         patch.object(ae_mod, '_load_cfg', _healthy_ae_cfg), \
         patch.object(ae_mod, 'call_llm', _ae_accepts):
        with batch_mode():
            with pytest.raises(JudgeUnavailable):
                gen._generate_validated_question(
                    prose=PROSE, language_name='English',
                    question_type_code='literal_detail', difficulty=6,
                    kept_questions=[], language_id=1, db=MagicMock(),
                )


def test_generate_questions_does_not_swallow_it():
    gen = _generator()
    with patch.object(gen, '_generate_single_question',
                      lambda *_a, **_kw: _question()), \
         patch.object(ae_mod, '_load_cfg', _dead_template):
        with batch_mode():
            with pytest.raises(JudgeUnavailable):
                gen.generate_questions(
                    prose=PROSE, language_name='English',
                    question_type_codes=['literal_detail', 'main_idea'],
                    difficulty=6, language_id=1, db=MagicMock(),
                )


def test_generate_questions_still_returns_a_question_when_serving():
    """Same outage, no batch: the question survives, judged by nobody."""
    gen = _generator()
    with patch.object(gen, '_generate_single_question',
                      lambda *_a, **_kw: _question()), \
         patch.object(ae_mod, '_load_cfg', _dead_template), \
         patch.object(dp_mod, '_load_cfg', _dead_template):
        questions = gen.generate_questions(
            prose=PROSE, language_name='English',
            question_type_codes=['literal_detail'],
            difficulty=6, language_id=1, db=MagicMock(),
        )

    assert len(questions) == 1
    assert questions[0]['answer'] == 'in the spring'


# ---------------------------------------------------------------------------
# 3. End to end: run_batch aborts and writes nothing
# ---------------------------------------------------------------------------

def _orchestrator(question_generator=None):
    """An orchestrator without __init__ — it would need live Supabase."""
    lang = SimpleNamespace(
        id=1, language_code='en', language_name='English',
        prose_model='test-model', question_model='test-model',
        tts_voice_ids=['v1'], tts_speed=1.0,
    )
    topic = SimpleNamespace(
        id=uuid4(), category_id=7, concept_english='Harbour seals',
        keywords=['seals', 'bay'], target_age_tier=None,
    )

    db = MagicMock()
    db.get_language_config_by_code.return_value = lang
    db.get_language_config.return_value = lang
    db.get_topic.return_value = topic
    db.get_category_name.return_value = 'Nature'
    db.get_cefr_config.return_value = SimpleNamespace(tier_code='T3')
    db.get_word_count_range.return_value = (80, 120)
    db.get_initial_elo.return_value = 1200
    # Four types, because `_generate_test` enforces a survival floor of
    # max(3, requested - 1) at d>=3 and would abort a healthy fixture on
    # "Too few valid questions" before proving anything about judging.
    db.get_question_distribution.return_value = [
        'literal_detail', 'main_idea', 'inference', 'vocabulary_context',
    ]
    db.get_prompt_template.return_value = 'question template'
    db.generate_test_slug.return_value = 'en-6-harbour-seals'
    db._get_status_id.return_value = 1
    db.client.table.return_value.select.return_value.eq.return_value \
        .eq.return_value.limit.return_value.execute.return_value = \
        SimpleNamespace(data=[{'id': str(uuid4()), 'topic_id': str(topic.id)}])

    orch = object.__new__(TestGenerationOrchestrator)
    orch.db = db
    orch.vocab_shortfalls = 0
    orch.metrics = None
    orch._vocab_cache = {}
    orch.topic_translator = SimpleNamespace(
        should_translate=lambda _code: False,
        translate=lambda **_kw: ('Harbour seals', ['seals']),
    )
    orch.prose_writer = SimpleNamespace(
        generate_prose=lambda **_kw: PROSE, client=None,
    )
    orch.title_generator = SimpleNamespace(
        generate_title=lambda **_kw: 'Seals in the bay',
    )
    orch.question_generator = question_generator or _generator()
    orch.question_validator = SimpleNamespace(
        validate_all_questions=lambda qs, _prose: (qs, []),
    )
    orch.audio_synthesizer = MagicMock()
    orch.vocab_pipeline = MagicMock()
    return orch


def test_run_batch_aborts_and_writes_nothing_on_a_judge_outage():
    """The whole point. Not "the run reported an error" — nothing was written."""
    gen = _generator()
    orch = _orchestrator(gen)

    with patch.object(gen, '_generate_single_question',
                      lambda *_a, **_kw: _question()), \
         patch.object(ae_mod, '_load_cfg', _dead_template):
        with pytest.raises(JudgeUnavailable):
            orch.run_batch(BatchConfig(
                language_code='en', count=4, difficulty=6,
                test_type='reading',
            ))

    orch.db.insert_test.assert_not_called()
    orch.db.insert_questions.assert_not_called()
    orch.db.insert_test_skill_ratings.assert_not_called()
    # Left pending on purpose: the batch is re-runnable once the judge's
    # prompt_templates row / model slug is fixed.
    orch.db.mark_queue_completed.assert_not_called()
    # And it is not filed as a finished run.
    orch.db.insert_generation_run.assert_not_called()


def test_run_batch_aborts_on_the_distractor_judge_too():
    gen = _generator()
    orch = _orchestrator(gen)

    with patch.object(gen, '_generate_single_question',
                      lambda *_a, **_kw: _question()), \
         patch.object(ae_mod, '_load_cfg', _healthy_ae_cfg), \
         patch.object(ae_mod, 'call_llm', _ae_accepts), \
         patch.object(dp_mod, '_load_cfg', _dead_template):
        with pytest.raises(JudgeUnavailable):
            orch.run_batch(BatchConfig(
                language_code='en', count=4, difficulty=6,
                test_type='reading',
            ))

    orch.db.insert_test.assert_not_called()
    orch.db.insert_questions.assert_not_called()


def test_run_aborts_on_a_judge_outage_too():
    """The queue-driven entry point, whose per-item handler marks the item
    failed and moves on — which would work through the whole queue."""
    gen = _generator()
    orch = _orchestrator(gen)
    item = SimpleNamespace(
        id=uuid4(), topic_id=orch.db.get_topic.return_value.id, language_id=1,
    )
    orch.db.get_pending_queue_items.return_value = [item]

    with patch.object(gen, '_generate_single_question',
                      lambda *_a, **_kw: _question()), \
         patch.object(ae_mod, '_load_cfg', _dead_template), \
         patch('services.test_generation.orchestrator.get_test_gen_config') as cfg:
        cfg.return_value = SimpleNamespace(
            dry_run=False, batch_size=5, target_difficulties=[6],
            question_regen_attempts=2, system_user_id='sys',
        )
        with pytest.raises(JudgeUnavailable):
            orch.run()

    orch.db.insert_test.assert_not_called()
    orch.db.mark_queue_failed.assert_not_called()   # not the item's fault
    orch.db.mark_queue_completed.assert_not_called()


def test_batch_mode_is_active_inside_the_generation_loop():
    """TASK-727's wiring, asserted where it has to hold: at the judge call.

    The flag is thread-local, so this is also the assertion that breaks first if
    the generation loop is ever parallelised without
    `BatchModeThreadPoolExecutor` — the fail-open regression wearing a new hat.
    """
    seen = []
    gen = _generator()
    orch = _orchestrator(gen)

    def _record_and_answer(*_a, **_kw):
        seen.append(is_batch_mode())
        return _ae_accepts()

    with patch.object(gen, '_generate_single_question',
                      lambda *_a, **_kw: _question()), \
         patch.object(ae_mod, '_load_cfg', _healthy_ae_cfg), \
         patch.object(ae_mod, 'call_llm', _record_and_answer), \
         patch.object(dp_mod, '_load_cfg', _healthy_dp_cfg), \
         patch.object(dp_mod, 'call_llm', _dp_accepts):
        orch.run_batch(BatchConfig(
            language_code='en', count=1, difficulty=6,
            test_type='reading', dry_run=True,
        ))

    assert seen, 'the judge was never reached — the fixture proves nothing'
    assert all(seen), 'judges ran fail-open inside a batch'


def test_serve_shaped_call_is_not_in_batch_mode():
    """The counterpart: `_generate_test` reached directly is not a batch."""
    seen = []
    gen = _generator()
    orch = _orchestrator(gen)

    def _record_and_answer(*_a, **_kw):
        seen.append(is_batch_mode())
        return _ae_accepts()

    with patch.object(gen, '_generate_single_question',
                      lambda *_a, **_kw: _question()), \
         patch.object(ae_mod, '_load_cfg', _healthy_ae_cfg), \
         patch.object(ae_mod, 'call_llm', _record_and_answer), \
         patch.object(dp_mod, '_load_cfg', _healthy_dp_cfg), \
         patch.object(dp_mod, 'call_llm', _dp_accepts):
        orch._generate_test(
            topic=orch.db.get_topic.return_value,
            lang_config=orch.db.get_language_config_by_code.return_value,
            category_name='Nature', difficulty=6,
            test_type='reading', dry_run=True,
        )

    assert seen, 'the judge was never reached — the fixture proves nothing'
    assert not any(seen), 'the serve path must keep the fail-open contract'
