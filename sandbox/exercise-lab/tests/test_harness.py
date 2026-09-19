"""Proves the harness times correctly, aggregates telemetry, reports both
single-item latency and batch throughput, and survives a broken generator."""
import time

from lab.harness import run_harness
from lab.models import ExerciseRow, SenseRow


def make_sense(i: int) -> SenseRow:
    return SenseRow(
        sense_id=i,
        vocab_id=i,
        language_id=1,
        lemma=f"word{i}",
        part_of_speech=None,
        frequency_rank=None,
        definition="def",
        definition_level="standard",
        pronunciation=None,
        example_sentence=None,
        sense_rank=1,
    )


class SleepyGenerator:
    name = "sleepy"

    def __init__(self, sleep_s: float = 0.02):
        self.sleep_s = sleep_s

    def generate(self, sense: SenseRow) -> list[ExerciseRow]:
        time.sleep(self.sleep_s)
        return [
            ExerciseRow(
                exercise_type="definition_match",
                content={"sense_id": sense.sense_id},
                word_sense_id=sense.sense_id,
                language_id=sense.language_id,
                passed_validation=True,
            )
        ]


def test_harness_times_and_aggregates_serially():
    senses = [make_sense(i) for i in range(5)]
    report = run_harness(SleepyGenerator(0.02), senses, concurrency=1)
    assert report.n_senses == 5
    assert report.total_exercises_produced == 5
    assert report.total_exercises_passing == 5
    assert report.validation_pass_rate == 1.0
    # each sense sleeps 20ms; serial mean latency must reflect that, not be ~0
    assert report.single_item_latency_ms_mean >= 15
    assert report.errors == 0


def test_concurrency_improves_wall_clock_and_throughput():
    senses = [make_sense(i) for i in range(12)]
    serial = run_harness(SleepyGenerator(0.03), senses, concurrency=1)
    parallel = run_harness(SleepyGenerator(0.03), senses, concurrency=6)
    # this is the whole point of separating the two metrics: per-item latency
    # is roughly unchanged, but wall clock / throughput should improve a lot
    assert parallel.total_wall_clock_s < serial.total_wall_clock_s * 0.6
    assert parallel.throughput_senses_per_min > serial.throughput_senses_per_min


def test_harness_survives_a_generator_that_raises():
    class Flaky:
        name = "flaky"

        def generate(self, sense: SenseRow) -> list[ExerciseRow]:
            if sense.sense_id % 2 == 0:
                raise ValueError("boom")
            return [
                ExerciseRow(
                    exercise_type="x", content={}, word_sense_id=sense.sense_id, language_id=1
                )
            ]

    senses = [make_sense(i) for i in range(4)]
    report = run_harness(Flaky(), senses, concurrency=1)
    assert report.n_senses == 4
    assert report.errors == 2
    assert report.total_exercises_produced == 2


def test_report_serializes_to_json_and_markdown():
    senses = [make_sense(0)]
    report = run_harness(SleepyGenerator(0.0), senses)
    assert '"generator_name"' in report.to_json()
    md = report.to_markdown()
    assert "single-item latency" in md
    assert "batch throughput" in md
