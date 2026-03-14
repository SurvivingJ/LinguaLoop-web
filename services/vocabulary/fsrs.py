"""
FSRS-4.5 Scheduler — Free Spaced Repetition Scheduler

Implements the FSRS algorithm for optimal review scheduling.
Based on the open-source FSRS-4.5 algorithm.

Card states: new → learning → review ↔ relearning
Ratings: again (1), hard (2), good (3), easy (4)

References:
- https://github.com/open-spaced-repetition/fsrs4.5
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta


# Default FSRS-4.5 parameters (optimized from Anki data)
DEFAULT_PARAMS = {
    'w': [
        0.4, 0.6, 2.4, 5.8,    # initial stability for again/hard/good/easy
        4.93, 0.94, 0.86, 0.01, # difficulty parameters
        1.49, 0.14, 0.94,       # stability after failure
        2.18, 0.05, 0.34,       # stability increase
        1.26, 0.29, 2.61,       # difficulty adjustment
    ],
    'request_retention': 0.9,    # Target retention rate
    'maximum_interval': 365,     # Max days between reviews
}

# Rating constants
AGAIN = 1
HARD = 2
GOOD = 3
EASY = 4


@dataclass
class CardState:
    """Represents the current scheduling state of a flashcard."""
    stability: float = 0.0
    difficulty: float = 0.3
    due_date: date | None = None
    last_review: date | None = None
    reps: int = 0
    lapses: int = 0
    state: str = 'new'  # new, learning, review, relearning


def schedule_review(card: CardState, rating: int, review_date: date | None = None) -> CardState:
    """
    Schedule the next review based on the current card state and rating.

    Args:
        card: Current card state
        rating: 1=again, 2=hard, 3=good, 4=easy
        review_date: Date of this review (defaults to today)

    Returns:
        Updated CardState with new scheduling parameters
    """
    if review_date is None:
        review_date = date.today()

    w = DEFAULT_PARAMS['w']
    request_retention = DEFAULT_PARAMS['request_retention']
    max_interval = DEFAULT_PARAMS['maximum_interval']

    if card.state == 'new':
        return _schedule_new(card, rating, review_date, w, request_retention, max_interval)
    elif card.state in ('learning', 'relearning'):
        return _schedule_learning(card, rating, review_date, w, request_retention, max_interval)
    else:  # review
        return _schedule_review(card, rating, review_date, w, request_retention, max_interval)


def _schedule_new(card, rating, review_date, w, retention, max_interval):
    """Schedule a new card's first review."""
    # Initial stability from rating
    s = w[rating - 1]
    # Initial difficulty
    d = _init_difficulty(w, rating)

    new_card = CardState(
        stability=s,
        difficulty=d,
        last_review=review_date,
        reps=1,
        lapses=1 if rating == AGAIN else 0,
    )

    if rating == AGAIN:
        new_card.state = 'learning'
        new_card.due_date = review_date + timedelta(minutes=1)
    elif rating == HARD:
        new_card.state = 'learning'
        new_card.due_date = review_date + timedelta(minutes=5)
    elif rating == GOOD:
        new_card.state = 'review'
        interval = _next_interval(s, retention, max_interval)
        new_card.due_date = review_date + timedelta(days=interval)
    else:  # easy
        new_card.state = 'review'
        interval = _next_interval(s, retention, max_interval)
        new_card.due_date = review_date + timedelta(days=max(interval, 4))

    return new_card


def _schedule_learning(card, rating, review_date, w, retention, max_interval):
    """Schedule a card in learning/relearning state."""
    d = _next_difficulty(w, card.difficulty, rating)
    s = _short_term_stability(w, card.stability, rating)

    new_card = CardState(
        stability=s,
        difficulty=d,
        last_review=review_date,
        reps=card.reps + 1,
        lapses=card.lapses + (1 if rating == AGAIN else 0),
    )

    if rating == AGAIN:
        new_card.state = 'relearning' if card.state == 'review' else 'learning'
        new_card.due_date = review_date + timedelta(minutes=1)
    elif rating == HARD:
        new_card.state = card.state
        new_card.due_date = review_date + timedelta(minutes=10)
    elif rating == GOOD:
        new_card.state = 'review'
        interval = _next_interval(s, retention, max_interval)
        new_card.due_date = review_date + timedelta(days=max(interval, 1))
    else:  # easy
        new_card.state = 'review'
        interval = _next_interval(s, retention, max_interval)
        new_card.due_date = review_date + timedelta(days=max(interval, 4))

    return new_card


def _schedule_review(card, rating, review_date, w, retention, max_interval):
    """Schedule a card in review state."""
    elapsed_days = (review_date - card.last_review).days if card.last_review else 0
    d = _next_difficulty(w, card.difficulty, rating)

    new_card = CardState(
        difficulty=d,
        last_review=review_date,
        reps=card.reps + 1,
    )

    if rating == AGAIN:
        s = _stability_after_failure(w, card.stability, d, elapsed_days)
        new_card.stability = s
        new_card.state = 'relearning'
        new_card.lapses = card.lapses + 1
        new_card.due_date = review_date + timedelta(minutes=1)
    else:
        s = _stability_after_success(w, card.stability, d, elapsed_days, rating)
        new_card.stability = s
        new_card.state = 'review'
        new_card.lapses = card.lapses
        interval = _next_interval(s, retention, max_interval)

        if rating == HARD:
            interval = max(interval, 1)
        elif rating == EASY:
            interval = max(interval, elapsed_days + 1)

        new_card.due_date = review_date + timedelta(days=interval)

    return new_card


# ============================================================================
# FSRS MATH
# ============================================================================

def _init_difficulty(w, rating):
    """Initial difficulty from first rating."""
    d = w[4] - (rating - 3) * w[5]
    return min(10.0, max(1.0, d))


def _next_difficulty(w, d, rating):
    """Update difficulty based on rating."""
    delta = -(rating - 3) * w[6]
    d_new = d + delta * (w[7] * (10 - d))
    # Mean revert towards initial difficulty
    d_new = w[4] * (1 - w[7]) + d_new * w[7] if w[7] > 0 else d_new
    return min(10.0, max(1.0, d_new))


def _next_interval(stability, retention, max_interval):
    """Calculate next interval from stability and target retention."""
    interval = stability * 9 * (1 / retention - 1)
    return min(max(round(interval), 1), max_interval)


def _short_term_stability(w, s, rating):
    """Stability update for learning/relearning cards."""
    if rating == AGAIN:
        return w[0]
    return s * math.exp(w[8] * (rating - 3 + w[9]))


def _stability_after_success(w, s, d, elapsed_days, rating):
    """Stability increase after successful review."""
    retrievability = math.exp(-elapsed_days / s) if s > 0 else 0
    s_new = s * (
        1 + math.exp(w[10]) *
        (11 - d) *
        math.pow(s, -w[11]) *
        (math.exp((1 - retrievability) * w[12]) - 1) *
        (1 if rating == HARD else 1) *
        (1 if rating != EASY else w[15])
    )
    return max(s_new, s + 0.1)  # Stability should always increase on success


def _stability_after_failure(w, s, d, elapsed_days):
    """Stability decrease after lapse."""
    retrievability = math.exp(-elapsed_days / s) if s > 0 else 0
    s_new = w[13] * math.pow(d, -w[14]) * (math.pow(s + 1, w[15]) - 1) * math.exp((1 - retrievability) * w[16])
    return max(s_new, 0.1)  # Minimum stability


def difficulty_from_p_known(p_known: float) -> float:
    """
    Map BKT p_known to initial FSRS difficulty.

    Low p_known → hard card (high difficulty)
    High p_known → easy card (low difficulty)
    """
    if p_known < 0.3:
        return 7.0  # Hard
    elif p_known < 0.5:
        return 5.5  # Medium-hard
    elif p_known < 0.7:
        return 4.0  # Medium
    else:
        return 2.5  # Easy
