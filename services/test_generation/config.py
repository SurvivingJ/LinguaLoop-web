"""
Test Generation Configuration

Extends main Config with test generation specific settings.
All settings can be overridden via environment variables.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class TestGenConfig:
    """Configuration for test generation system."""

    # Generation parameters
    batch_size: int = field(
        default_factory=lambda: int(os.getenv('TEST_GEN_BATCH_SIZE', '50'))
    )
    target_difficulties: List[int] = field(
        default_factory=lambda: [1, 3, 6, 9]  # Default: A2, B2, C2
    )
    questions_per_test: int = field(
        default_factory=lambda: int(os.getenv('TEST_GEN_QUESTIONS', '5'))
    )
    # Per-question-type regeneration budget. Each question type is generated →
    # judged → validated as a unit; on any judge/validator rejection the type is
    # regenerated with feedback (the rejected attempt + reason) up to this many
    # attempts total (1 original + N-1 retries). Default 2 = one regen. Keeps a
    # single recoverable bad question from sinking the whole test under the floor.
    question_regen_attempts: int = field(
        default_factory=lambda: int(os.getenv('TEST_GEN_QUESTION_REGEN_ATTEMPTS', '2'))
    )

    # Concurrency (TASK-737 throughput work). Both loops were previously
    # fully serial — one word/test at a time — which the batch economics
    # showed as the dominant cost (vocab enrichment: ~82% of per-test wall
    # clock). Workers run inside BatchModeThreadPoolExecutor so the
    # fail-closed judge contract carries into the pool (see judges/base.py).
    #
    # vocab_sense_workers: concurrent generate_sense() calls per test, one
    # per extracted vocab word. Words are independent — no cross-word
    # dependency — so this is pure fan-out.
    #
    # Lowered 5->3 after live batch validation: at 5 vocab_sense_workers x 3
    # batch_test_workers (peak ~15 concurrent Supabase-touching threads from
    # this pipeline alone), Supabase/Cloudflare started rejecting some
    # requests outright (HTTP/2 ConnectionTerminated, a literal Cloudflare
    # 400) — not just dropping idle keep-alive connections, which
    # retry_transient_db_call (sense_generator.py) already covers. Those
    # residual errors degrade gracefully into a non-fatal VOCAB SHORTFALL
    # rather than failing the test, but the lower default avoids manufacturing
    # them as routinely. Raise again only after confirming the retry/error
    # rate stays flat at the higher value.
    vocab_sense_workers: int = field(
        default_factory=lambda: int(os.getenv('TEST_GEN_VOCAB_SENSE_WORKERS', '3'))
    )
    # batch_test_workers: concurrent tests in flight inside run_batch's main
    # loop. Lowered 3->2 for the same reason as vocab_sense_workers above —
    # this and that knob multiply (peak concurrent DB load is roughly their
    # product), so both came down together rather than leaving one high
    # enough to reproduce the same peak on its own.
    batch_test_workers: int = field(
        default_factory=lambda: int(os.getenv('TEST_GEN_BATCH_TEST_WORKERS', '2'))
    )

    # TASK-744 (plan §2, T2.3) — cap how much vocabulary is enriched *inline*.
    #
    # Concurrency is not the lever (see the note above: 5x3 workers made
    # Supabase and Cloudflare reject requests outright), so the remaining way
    # to cut enrichment wall clock is to do less of it synchronously. Measured
    # senses per test, live 2026-08-31:
    #
    #     tier   avg    p90    max
    #     T1      19     31     43
    #     T2      32     48     64
    #     T4      73    135    154
    #     T6     177    333    382
    #
    # 80 is chosen against that distribution, not picked round: it leaves T1
    # and T2 completely untouched, trims only T4's tail, and roughly halves the
    # worst tier. A cap of 40 (the plan's opening suggestion) would have bitten
    # T4's median as well.
    #
    # The tail is deferred, not dropped. Every deferred word still gets its
    # dim_vocabulary row — that costs no LLM call — which is exactly what
    # scripts/backfill_senses.py selects on, and the lemmas are recorded in
    # tests.vocab_sense_stats.deferred_lemmas so
    # scripts/relink_deferred_vocab.py can attach the senses to the test once
    # the backfill has produced them.
    #
    # 0 disables the cap (enrich everything inline, the pre-TASK-744 behaviour).
    inline_enrichment_cap: int = field(
        default_factory=lambda: int(
            os.getenv('TEST_GEN_INLINE_ENRICHMENT_CAP', '80')
        )
    )

    # TASK-740 Phase 4: bounded, spaced test fan-out per topic (finding #2,
    # 2026-08-29 review — a topic re-entering the queue could otherwise
    # generate an unbounded number of near-duplicate tests over time, since
    # each pass produces exactly one test at the topic's mandatory tier with
    # no cap or recency check). max_tests_per_topic is deliberately small:
    # a topic only has one tier now (no difficulty fan-out), so a second or
    # third test at the same tier is already a near-duplicate; a handful is
    # enough headroom for legitimate re-runs (a failed generation retried,
    # or an operator wanting a couple of variants) without letting a topic
    # that keeps re-entering the queue run away. topic_recency_window_days
    # bounds how far back the count looks — old tests don't count against a
    # topic that hasn't been touched in a long time.
    max_tests_per_topic: int = field(
        default_factory=lambda: int(os.getenv('TEST_GEN_MAX_TESTS_PER_TOPIC', '3'))
    )
    topic_recency_window_days: int = field(
        default_factory=lambda: int(os.getenv('TEST_GEN_TOPIC_RECENCY_WINDOW_DAYS', '30'))
    )

    # TASK-740 Phase 5 (finding #3): near-duplicate passage detection,
    # scoped to (topic_id, target_age_tier). Cosine similarity above this
    # threshold is treated as a near-duplicate of an existing passage at the
    # same topic+tier and triggers the retry-then-skip path in
    # services/test_generation/dedup.py. 0.92 was picked as "clearly the
    # same passage reworded", not "same topic in general" — two independent
    # passages about the same narrow topic still commonly land ~0.80-0.88.
    passage_dedup_similarity_threshold: float = field(
        default_factory=lambda: float(
            os.getenv('TEST_GEN_PASSAGE_DEDUP_THRESHOLD', '0.92')
        )
    )

    # LLM Configuration (via OpenRouter)
    default_prose_model: str = field(
        default_factory=lambda: os.getenv('TEST_GEN_PROSE_MODEL', 'google/gemini-3.5-flash-lite')
    )
    default_question_model: str = field(
        default_factory=lambda: os.getenv('TEST_GEN_QUESTION_MODEL', 'google/gemini-3.5-flash-lite')
    )
    prose_temperature: float = field(
        default_factory=lambda: float(os.getenv('TEST_GEN_PROSE_TEMP', '0.7'))
    )
    question_temperature: float = field(
        default_factory=lambda: float(os.getenv('TEST_GEN_QUESTION_TEMP', '0.3'))
    )

    # TTS Configuration
    default_tts_model: str = field(
        default_factory=lambda: os.getenv('TEST_GEN_TTS_MODEL', 'tts-1')
    )
    default_tts_voice: str = field(
        default_factory=lambda: os.getenv('TEST_GEN_TTS_VOICE', 'alloy')
    )
    default_tts_speed: float = field(
        default_factory=lambda: float(os.getenv('TEST_GEN_TTS_SPEED', '1.0'))
    )

    # Retry Configuration
    max_retries: int = field(
        default_factory=lambda: int(os.getenv('TEST_GEN_MAX_RETRIES', '3'))
    )
    retry_delay: float = field(
        default_factory=lambda: float(os.getenv('TEST_GEN_RETRY_DELAY', '2.0'))
    )

    # Operational Settings
    dry_run: bool = field(
        default_factory=lambda: os.getenv('TEST_GEN_DRY_RUN', 'false').lower() == 'true'
    )
    log_level: str = field(
        default_factory=lambda: os.getenv('TEST_GEN_LOG_LEVEL', 'INFO')
    )

    # System user ID (for gen_user field)
    system_user_id: Optional[str] = field(
        default_factory=lambda: os.getenv('TEST_GEN_SYSTEM_USER_ID', 'de6fd05b-0871-45d4-a2d8-0195fdf5355e')
    )

    # API Keys (fallback to main config)
    openrouter_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv('OPENROUTER_API_KEY')
    )
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv('OPENAI_API_KEY')
    )

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY not set - LLM calls will fail")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set - TTS and embedding calls will fail")

        # Parse target_difficulties from env if set
        env_difficulties = os.getenv('TEST_GEN_TARGET_DIFFICULTIES')
        if env_difficulties:
            try:
                import json
                self.target_difficulties = json.loads(env_difficulties)
            except Exception:
                logger.warning(f"Invalid TEST_GEN_TARGET_DIFFICULTIES: {env_difficulties}")

        # Configure logging level
        logging.getLogger('services.test_generation').setLevel(
            getattr(logging, self.log_level.upper(), logging.INFO)
        )

    def validate(self) -> bool:
        """Check if all required configuration is present."""
        errors = []

        if not self.openrouter_api_key:
            errors.append("OPENROUTER_API_KEY is required")
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        if self.batch_size < 1:
            errors.append("TEST_GEN_BATCH_SIZE must be >= 1")
        if self.vocab_sense_workers < 1:
            errors.append("TEST_GEN_VOCAB_SENSE_WORKERS must be >= 1")
        if self.batch_test_workers < 1:
            errors.append("TEST_GEN_BATCH_TEST_WORKERS must be >= 1")
        if self.inline_enrichment_cap < 0:
            errors.append(
                "TEST_GEN_INLINE_ENRICHMENT_CAP must be >= 0 (0 = no cap)"
            )
        if self.max_tests_per_topic < 1:
            errors.append("TEST_GEN_MAX_TESTS_PER_TOPIC must be >= 1")
        if self.topic_recency_window_days < 1:
            errors.append("TEST_GEN_TOPIC_RECENCY_WINDOW_DAYS must be >= 1")
        if not self.target_difficulties:
            errors.append("target_difficulties must not be empty")
        for d in self.target_difficulties:
            if not 1 <= d <= 9:
                errors.append(f"Invalid difficulty level: {d}")

        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False

        return True


# Singleton instance - lazily evaluated
_config_instance: Optional[TestGenConfig] = None


def get_test_gen_config() -> TestGenConfig:
    """Get the test generation configuration singleton.

    Lazily instantiated on first call so importing this module never triggers
    config construction (and its missing-API-key warnings) at import time —
    e.g. in test environments that never run generation.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = TestGenConfig()
    return _config_instance
