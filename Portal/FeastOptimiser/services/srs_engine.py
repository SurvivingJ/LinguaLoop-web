"""SM-2 Spaced Repetition Engine for cooking technique tracking."""

import math
from datetime import datetime, timedelta

from models import srs, progress


MAX_INTERVAL_DAYS = 60


def record_practice(store, technique, quality_rating, notes=None):
    """Core SM-2 algorithm. Update card after a practice session.

    Args:
        quality_rating: 0-5 scale (0=complete failure, 5=perfect)
    Returns:
        dict with new_easiness, next_review_days, next_review_date, mastery_percentage
    """
    card = srs.get_card(store, technique)
    now = datetime.now()

    if card is None:
        card = {
            'technique': technique,
            'easiness_factor': 2.5,
            'interval': 1,
            'repetitions': 0,
            'next_review_date': now.isoformat(),
            'last_practiced': None,
            'quality_history': [],
        }

    q = quality_rating
    ef = card['easiness_factor']

    # Update easiness factor
    ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ef = max(1.3, ef)

    # Update interval and repetitions
    if q < 3:
        # Failed — reset
        card['repetitions'] = 0
        card['interval'] = 1
    else:
        card['repetitions'] += 1
        reps = card['repetitions']
        if reps == 1:
            card['interval'] = 1
        elif reps == 2:
            card['interval'] = 6
        else:
            card['interval'] = round(card['interval'] * ef)

    # Cap interval
    card['interval'] = min(card['interval'], MAX_INTERVAL_DAYS)

    # Update card fields
    card['easiness_factor'] = round(ef, 4)
    card['next_review_date'] = (now + timedelta(days=card['interval'])).isoformat()
    card['last_practiced'] = now.isoformat()
    card['quality_history'].append({
        'date': now.isoformat(),
        'quality': q,
        'notes': notes or '',
    })

    srs.upsert_card(store, card)

    mastery = calculate_mastery_percentage(store, technique)

    return {
        'new_easiness': card['easiness_factor'],
        'next_review_days': card['interval'],
        'next_review_date': card['next_review_date'],
        'mastery_percentage': mastery,
    }


def get_due_techniques(store, limit=10):
    cards = srs.get_due_cards(store, limit=limit)
    now = datetime.now()
    results = []
    for card in cards:
        try:
            review_dt = datetime.fromisoformat(card['next_review_date'])
            days_overdue = (now - review_dt).days
        except (ValueError, TypeError):
            days_overdue = 0
        results.append({
            'technique': card['technique'],
            'days_overdue': days_overdue,
            'last_practiced': card['last_practiced'],
            'current_level': _level_from_reps(card['repetitions']),
        })
    return results


def get_upcoming_reviews(store, days=7):
    return srs.get_upcoming_reviews(store, days=days)


def calculate_mastery_percentage(store, technique):
    """Weighted mastery: 50% reps (cap 30) + 25% EF (1.3-2.5) + 25% avg quality."""
    card = srs.get_card(store, technique)
    if not card:
        return 0.0

    # Repetition component (50%)
    rep_score = min(card['repetitions'] / 30, 1.0) * 50

    # Easiness factor component (25%) — normalized from 1.3-2.5 range
    ef_score = min((card['easiness_factor'] - 1.3) / 1.2, 1.0) * 25

    # Average quality of last 5 ratings (25%)
    history = card.get('quality_history', [])
    if history:
        recent = [h['quality'] for h in history[-5:]]
        avg_quality = sum(recent) / len(recent)
        quality_score = (avg_quality / 5) * 25
    else:
        quality_score = 0

    return round(rep_score + ef_score + quality_score, 1)


def calculate_retention_rate(store, technique):
    """Forgetting curve: R(t) = e^(-t/S) where S = EF * (reps+1) * 7."""
    card = srs.get_card(store, technique)
    if not card or not card.get('last_practiced'):
        return 0.0

    try:
        last = datetime.fromisoformat(card['last_practiced'])
        t = (datetime.now() - last).days
    except (ValueError, TypeError):
        return 0.0

    s = card['easiness_factor'] * (card['repetitions'] + 1) * 7
    if s == 0:
        return 0.0

    retention = math.exp(-t / s) * 100
    return round(min(max(retention, 0), 100), 1)


def get_effective_skill_level(store, technique):
    """Combine completion thresholds with retention decay."""
    card = srs.get_card(store, technique)
    completions = progress.get_technique_completion_count(store, technique)
    retention = calculate_retention_rate(store, technique)

    # Base level from completion count
    if completions >= 30:
        base_level = 'expert'
    elif completions >= 15:
        base_level = 'advanced'
    elif completions >= 8:
        base_level = 'intermediate'
    elif completions >= 3:
        base_level = 'beginner'
    else:
        base_level = 'novice'

    # Effective score adjusted by retention
    level_scores = {'novice': 0, 'beginner': 25, 'intermediate': 50, 'advanced': 75, 'expert': 100}
    base_score = level_scores.get(base_level, 0)
    effective_score = base_score * (retention / 100) if retention > 0 else base_score * 0.5

    # Confidence
    if retention >= 80:
        confidence = 'high'
    elif retention >= 50:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'base_level': base_level,
        'effective_score': round(effective_score, 1),
        'retention': retention,
        'needs_practice': retention < 70,
        'confidence': confidence,
    }


def _level_from_reps(reps):
    if reps >= 30:
        return 'expert'
    elif reps >= 15:
        return 'advanced'
    elif reps >= 8:
        return 'intermediate'
    elif reps >= 3:
        return 'beginner'
    return 'novice'
