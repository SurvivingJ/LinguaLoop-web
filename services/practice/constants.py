"""Tunables and small helpers shared by the practice service modules."""

from config import Config

# ----------------------------------------------------------------------
# Ladder intake tunables (plan §4c)
# ----------------------------------------------------------------------

# Safety ceiling on how many senses one intake pass may add. Intake is driven
# by the per-local-day new-word quota (admit_daily_new_words), not by a pool
# floor; this cap only bounds a pathological quota (npd up to 50) on one call.
LADDER_TOPUP_MAX_PER_CALL = 12

# Practice extra rounds (practice-extra-rounds, ADR-036): open-ended practice
# past the daily budget. At most this many new words per round; the learner
# sees the selection screen again between rounds. No daily cap, only a warning.
EXTRA_NEW_WORDS_MAX = 10
# Review items per extra round, and how long a just-attempted sense is kept
# out of review-ahead so consecutive rounds do not loop on the same words.
EXTRA_REVIEW_ITEMS = 10
EXTRA_REVIEW_RECENT_MINUTES = 10

# Ladder states that count towards the eligible pool. state='new' is in here,
# which is why a cold-start seed used to disarm all later intake.
LADDER_ELIGIBLE_STATES = ('new', 'active', 'gated', 'pre_mastery', 'relearning')

# T4.1 — the supply gate. A sense must already carry this many active
# exercises in the target language before it may be admitted to the ladder.
# Below three there is not enough material to cover even one ring of the
# family rotation, so the learner meets the same item every session; the
# measured floor is that 21 of 24 live subscriptions had *zero*.
LADDER_MIN_EXERCISES_PER_SENSE = 3

# T4.2 — evidence thresholds. One wrong answer can be a careless click or a
# bad distractor, so a single miss never subscribes: a sense needs either
# repeated evidence or a p_known the model is already confident about.
LADDER_EVIDENCE_MIN_COUNT = 2
LADDER_EVIDENCE_P_KNOWN_MAX = 0.40

# How many ranked nominations to run through the supply gate per slot wanted.
# Exercise coverage sits near 3% of tested senses, so most nominations fail
# the gate and a 1:1 slice would almost always come back empty.
NOMINATION_OVERFETCH = 20

# Row ceilings on the intake reads. All are per-user and comfortably above
# any real learner's history; they exist so a pathological account cannot pull
# an unbounded result set onto the request path.
SUPPLY_GATE_CHUNK = 100
SUPPLY_GATE_ROW_LIMIT = 10000
EVIDENCE_ROW_LIMIT = 2000
WRONG_ANSWER_ROW_LIMIT = 5000
LADDER_SUBSCRIBED_ROW_LIMIT = 5000

# Queue A1 (session-budget-settings, TASK-871): unknowns from tests and word
# quizzes the learner took recently. Tunable (assumed, no data). Config wins when
# it defines the name, so the planner and intake share one value.
RECENT_TEST_WINDOW_DAYS = getattr(Config, 'RECENT_TEST_WINDOW_DAYS', 28)
RECENT_TEST_ROW_LIMIT = 1000
RECENT_TEST_CHUNK = 100

# Queue A2 (TASK-873): calibration wrongs.
CALIBRATION_EVIDENCE_MAX_AGE_DAYS = getattr(
    Config, 'CALIBRATION_EVIDENCE_MAX_AGE_DAYS', 90)   # tunable (assumed, no data)
CALIBRATION_ROW_LIMIT = 500


# T4.3 — how many starved nominations one session request may queue for
# exercise generation. At ~3% exercise coverage of tested senses an unbounded
# pass would enqueue a learner's whole vocabulary history on the first request.
DEMAND_GENERATION_MAX_PER_CALL = 5

# T4.6 — session-size floor. A daily session that returns a handful of items
# reads as "there is nothing here" even when review work is available, so a
# short acquisition session is topped up from the maintenance (FSRS/BKT) pool.
PRACTICE_SESSION_MIN_ITEMS = 20

# Test prestudy next-day review (prestudy_followups): at most this many
# follow-up senses per Maintenance session, each one exercise long.
PRESTUDY_FOLLOWUPS_PER_SESSION = 5
PRESTUDY_FOLLOWUP_EXPECTED_SECONDS = 30

# TASK-701: practice time accrues at seconds granularity. An attempt whose
# measured elapsed exceeds this (a tab left open, a coffee break) is treated as
# absurd and falls back to the exercise's expected_seconds estimate.
PRACTICE_ATTEMPT_MAX_SECONDS = 300      # 5 minutes
# Final fallback when the item carries no expected_seconds estimate — matches
# the seed default in get_practice_session (COALESCE(..., 45)).
DEFAULT_EXPECTED_SECONDS = 45

# exercises.attempt_count is written conditionally on the value read; this is
# how many writes one attempt may make before giving up on the condition.
COUNTER_WRITE_ATTEMPTS = 3

# record_exercise_attempt (migrations/record_exercise_attempt.sql) is used only
# when this env flag is set. A "function not found" answer is remembered for
# ATTEMPT_RPC_RECHECK_SECONDS so requests do not pay a failing round trip.
ATTEMPT_RPC_ENV_FLAG = 'PRACTICE_ATTEMPT_RPC_ENABLED'
ATTEMPT_RPC_RECHECK_SECONDS = 600


def _settled(fn):
    """``fn`` as a callable returning ``(value, error)`` instead of raising, so
    a read run ahead of time fails where it is used, not where it was started."""
    def run():
        try:
            return fn(), None
        except Exception as e:
            return None, e
    return run


def _unwrap(outcome):
    value, error = outcome
    if error is not None:
        raise error
    return value

__all__ = [
    'ATTEMPT_RPC_ENV_FLAG',
    'ATTEMPT_RPC_RECHECK_SECONDS',
    'CALIBRATION_EVIDENCE_MAX_AGE_DAYS',
    'CALIBRATION_ROW_LIMIT',
    'COUNTER_WRITE_ATTEMPTS',
    'DEFAULT_EXPECTED_SECONDS',
    'DEMAND_GENERATION_MAX_PER_CALL',
    'EVIDENCE_ROW_LIMIT',
    'EXTRA_NEW_WORDS_MAX',
    'EXTRA_REVIEW_ITEMS',
    'EXTRA_REVIEW_RECENT_MINUTES',
    'LADDER_ELIGIBLE_STATES',
    'LADDER_EVIDENCE_MIN_COUNT',
    'LADDER_EVIDENCE_P_KNOWN_MAX',
    'LADDER_MIN_EXERCISES_PER_SENSE',
    'LADDER_SUBSCRIBED_ROW_LIMIT',
    'LADDER_TOPUP_MAX_PER_CALL',
    'NOMINATION_OVERFETCH',
    'PRACTICE_ATTEMPT_MAX_SECONDS',
    'PRACTICE_SESSION_MIN_ITEMS',
    'PRESTUDY_FOLLOWUPS_PER_SESSION',
    'PRESTUDY_FOLLOWUP_EXPECTED_SECONDS',
    'RECENT_TEST_CHUNK',
    'RECENT_TEST_ROW_LIMIT',
    'RECENT_TEST_WINDOW_DAYS',
    'SUPPLY_GATE_CHUNK',
    'SUPPLY_GATE_ROW_LIMIT',
    'WRONG_ANSWER_ROW_LIMIT',
]
