"""Test generation stores the tier jev assigns, not the tier it aimed at (ADR-029).

Drives ``TestGenerationOrchestrator._generate_test`` with every collaborator
doubled, so what is pinned is the wiring: the jev tier reaches the stored tier,
the legacy difficulty, the ELO seed, the question mix and the dedup scope — and
a jev failure writes nothing and marks the queue item failed, never completed.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

import services.test_generation.orchestrator as orch
from services.jev_client import JevError
from services.test_generation.orchestrator import TestGenerationOrchestrator
from services.tier_classifier import TierAssessment

PROSE = 'The seals return to the bay each spring. ' * 6
INITIAL_ELO = {1: 875, 2: 1175, 3: 1400, 4: 1550, 5: 1700, 6: 1925}
DIFFICULTY_MIN = {1: 1, 2: 3, 3: 5, 4: 6, 5: 7, 6: 8}


def assessment(tier, score=None, confidence=0.81):
    score = tier - 1.0 if score is None else score
    return TierAssessment(
        tier=tier, expected_tier=score + 1, score=score, confidence=confidence,
        probabilities={t: (0.9 if t == tier else 0.02) for t in range(1, 7)},
        model='typesafe/jev-1.13-test', cost_usd=0.00004,
    )


class Harness:
    """A TestGenerationOrchestrator with no I/O, plus what it was asked to do."""

    def __init__(self, classify):
        self.dedup_tiers = []
        self.seed_calls = []
        self.mix_calls = []
        db = MagicMock()
        db.get_tier_config.side_effect = lambda t: SimpleNamespace(
            tier_code=f'T{t}', difficulty_min=DIFFICULTY_MIN[t])
        db.get_tier_word_count_range.return_value = (30, 120)
        db.get_tier_initial_elo.side_effect = lambda t: INITIAL_ELO[t]
        db.get_tier_question_distribution.side_effect = (
            lambda t: [f'type_for_tier_{t}'] * 4)
        db.generate_test_slug.side_effect = (
            lambda lang, difficulty, concept: f'{lang}-d{difficulty}-slug')
        db.get_prompt_template.return_value = 'template'
        db.get_question_type_id.return_value = 1
        db.get_recent_question_stems.return_value = []
        self.db = db

        o = object.__new__(TestGenerationOrchestrator)
        o.db = db
        o.classify_passage = classify
        o.topic_translator = SimpleNamespace(should_translate=lambda code: False)
        o.prose_writer = MagicMock()
        o.prose_writer.generate_prose.return_value = PROSE
        o.title_generator = MagicMock()
        o.title_generator.generate_title.return_value = 'A title'
        o.question_generator = MagicMock()
        o.question_generator.generate_questions.return_value = [
            {'type_code': 'x', 'question': f'q{i}', 'choices': ['a', 'b', 'c', 'd'],
             'answer': 'a'} for i in range(4)
        ]
        o.question_validator = MagicMock()
        o.question_validator.validate_all_questions.side_effect = (
            lambda qs, prose: (qs, []))
        o.audio_synthesizer = MagicMock()
        o.audio_synthesizer.generate_and_upload.return_value = 'https://audio/x.mp3'
        o._generate_vocabulary = MagicMock()
        o._run_id = None
        self.o = o

    def patches(self):
        harness = self

        class FakeDedup:
            def __init__(self, db):
                pass

            def check_duplicate(self, topic_id, tier_id, prose):
                harness.dedup_tiers.append(tier_id)
                return SimpleNamespace(is_duplicate=False), 'hash', [0.0]

        def fake_seed(prose, language_code, tier_id, tier_initial_elo):
            harness.seed_calls.append((tier_id, tier_initial_elo))
            return tier_initial_elo + 25, {}

        cfg = SimpleNamespace(system_user_id='sys', dry_run=False)
        return [
            patch.object(orch, 'get_test_gen_config', lambda: cfg),
            patch.object(orch, 'log_stage_seconds', lambda *a, **k: None),
            patch.object(orch, '_write_review_queue_rows', lambda **k: None),
            patch.object(orch, '_subject_kwargs', lambda *a, **k: {}),
            patch.object(
                orch, 'report_question_mix',
                lambda **k: harness.mix_calls.append(k)),
            patch('services.test_generation.dedup.PassageDedupChecker', FakeDedup),
            patch(
                'services.test_generation.difficulty_scorer.seed_test_elo',
                fake_seed),
        ]

    def generate(self, target_tier, lang='en'):
        topic = SimpleNamespace(
            id=uuid4(), concept_english='Seals', keywords=['seal'],
            target_age_tier=target_tier)
        lang_config = SimpleNamespace(
            id=2, language_code=lang, language_name='English',
            prose_model='m', question_model='m', tts_voice_ids=['v'],
            tts_speed=1.0)
        stack = self.patches()
        for p in stack:
            p.start()
        try:
            return self.o._generate_test(
                topic=topic, lang_config=lang_config, category_name='nature',
                tier_id=target_tier, test_type='listening', dry_run=False)
        finally:
            for p in stack:
                p.stop()

    @property
    def inserted(self):
        return self.db.insert_test.call_args.args[0]


def test_stored_tier_is_the_jev_tier_not_the_target():
    h = Harness(lambda text, lang: assessment(4, score=3.4, confidence=0.7))
    assert h.generate(target_tier=1) is True

    test = h.inserted
    assert test.target_age_tier == 4
    assert test.difficulty == 6                      # bottom of T4's band
    assert test.slug == 'en-d6-slug'                 # slug from assigned difficulty
    assert test.age_tier_score == pytest.approx(3.4)
    assert test.age_tier_confidence == pytest.approx(0.7)
    assert test.age_tier_probabilities['T4'] == pytest.approx(0.9)
    assert set(test.age_tier_probabilities) == {f'T{t}' for t in range(1, 7)}
    assert test.age_tier_model == 'typesafe/jev-1.13-test'
    assert test.age_tier_calibration == 'default'


def test_the_score_table_that_made_the_tier_is_stored():
    import dataclasses
    h = Harness(lambda text, lang: dataclasses.replace(
        assessment(4), calibration='ja-2026-09-27'))
    h.generate(target_tier=4, lang='ja')
    assert h.inserted.age_tier_calibration == 'ja-2026-09-27'


def test_the_passage_is_still_written_for_the_target_tier():
    h = Harness(lambda text, lang: assessment(4))
    h.generate(target_tier=1)
    kwargs = h.o.prose_writer.generate_prose.call_args.kwargs
    assert kwargs['complexity_tier'] == 'T1'
    assert kwargs['difficulty'] == 1
    h.db.get_tier_word_count_range.assert_called_once_with(1)


def test_downstream_tier_keyed_work_uses_the_assigned_tier():
    h = Harness(lambda text, lang: assessment(5))
    h.generate(target_tier=2)

    assert h.dedup_tiers == [5]                       # dedup scope
    assert h.seed_calls == [(5, 1700)]                # ELO anchored on T5
    assert h.inserted.initial_elo == 1725
    h.db.get_tier_question_distribution.assert_called_once_with(5)
    assert h.o.question_generator.generate_questions.call_args.kwargs[
        'rotation_key'].endswith(':5')
    assert h.mix_calls[0]['tier_id'] == 5
    assert h.o.title_generator.generate_title.call_args.kwargs[
        'complexity_tier'] == 'T5'


def test_jev_is_asked_about_the_final_passage_in_its_language():
    seen = []
    h = Harness(lambda text, lang: seen.append((text, lang)) or assessment(2))
    h.generate(target_tier=2, lang='zh')
    assert seen == [(PROSE, 'zh')]


def test_jev_failure_writes_nothing_and_does_not_guess_a_tier():
    def down(text, lang):
        raise JevError('gave up after 5 attempts', status=503)

    h = Harness(down)
    with pytest.raises(JevError):
        h.generate(target_tier=3)

    h.db.insert_test.assert_not_called()
    h.db.insert_questions.assert_not_called()
    h.db.insert_test_skill_ratings.assert_not_called()
    h.o.question_generator.generate_questions.assert_not_called()
    h.o.audio_synthesizer.generate_and_upload.assert_not_called()
    assert h.seed_calls == []


def test_queue_item_with_a_jev_failure_is_failed_not_completed():
    def down(text, lang):
        raise JevError('payment required', status=402)

    h = Harness(down)
    o, db = h.o, h.db
    item = SimpleNamespace(id='q1', topic_id='t1', language_id=2)
    db.get_topic.return_value = SimpleNamespace(
        id='t1', concept_english='Seals', keywords=[], category_id=1,
        target_age_tier=3)
    db.get_language_config.return_value = SimpleNamespace(
        id=2, language_code='en', language_name='English')
    db.get_category_name.return_value = 'nature'
    db.count_recent_tests_for_topic.return_value = 0
    db.get_pending_queue_items.return_value = [item]
    o.metrics = None
    o._finalize = lambda start, dry: o.metrics

    cfg = SimpleNamespace(
        system_user_id='sys', dry_run=False, batch_size=1,
        topic_recency_window_days=7, max_tests_per_topic=3)
    with patch.object(orch, 'get_test_gen_config', lambda: cfg), \
            patch.object(o, '_generate_test', side_effect=JevError('x', status=402)):
        with pytest.raises(JevError):
            o._process_queue_item(item, dry_run=False)
        db.mark_queue_completed.assert_not_called()

        o._run_impl()

    db.mark_queue_failed.assert_called_once()
    assert 'x' in db.mark_queue_failed.call_args.args[1]
    db.mark_queue_completed.assert_not_called()
    assert o.metrics.tests_failed == 1

