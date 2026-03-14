"""
PredictionEngine - Combines spaced repetition with weakness targeting
to generate optimal focus_tags for problem selection.

Three blended signals:
1. Weakness (0.5): Error rate from rolling window + lifetime
2. Staleness (0.3): Time since last seen vs optimal interval
3. Strategic value (0.2): Frequency boost + trap tag bonus
"""
from datetime import datetime, timezone

# Optimal review intervals (hours) based on mastery level
INTERVALS = {
    'mastered': 48,    # >90% accuracy
    'strong': 24,      # 80-90%
    'learning': 8,     # 70-80%
    'weak': 4,         # <70%
}

TRAP_TAGS = {'trap:7x8', 'trap:6x7', 'trap:8x9', 'trap:6x9'}

# Tags relevant to each mode category
MODE_TAG_PREFIXES = {
    'financial': ['compound_interest', 'simple_interest', 'rule_of_72',
                  'margin', 'return', 'liquidity', 'valuation', 'ggm',
                  'perpetuity', 'npv', 'cagr', 'bonds', 'breakeven',
                  'dcf', 'terminal', 'gordon', 'duration'],
    'poker': ['pot_odds', 'auto_profit', 'combos', 'equity', 'range'],
}

MIN_ATTEMPTS = 5


def _get_blended_accuracy(tag_data):
    """Compute 70% rolling-window + 30% lifetime accuracy."""
    if tag_data['attempts'] == 0:
        return 0.5  # Unknown, assume neutral

    lifetime = tag_data['correct'] / tag_data['attempts']
    if tag_data['history']:
        recent = sum(tag_data['history']) / len(tag_data['history'])
    else:
        recent = lifetime
    return 0.7 * recent + 0.3 * lifetime


def _get_optimal_interval(accuracy):
    """Return optimal review interval in hours based on accuracy."""
    if accuracy >= 0.9:
        return INTERVALS['mastered']
    elif accuracy >= 0.8:
        return INTERVALS['strong']
    elif accuracy >= 0.7:
        return INTERVALS['learning']
    else:
        return INTERVALS['weak']


def _hours_since(iso_timestamp):
    """Calculate hours since an ISO timestamp."""
    if not iso_timestamp:
        return 999  # Never seen = very stale
    try:
        last = datetime.fromisoformat(iso_timestamp)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - last).total_seconds() / 3600
    except (ValueError, TypeError):
        return 999


def get_focus_tags(tag_stats, mode=None, max_tags=5):
    """
    Score all tags and return the top focus tags.

    Args:
        tag_stats: dict of {tag: {attempts, correct, total_time_ms, last_seen, history}}
        mode: optional mode filter ('financial', 'poker', or None for arithmetic)
        max_tags: max number of focus tags to return

    Returns:
        {
            focus_tags: [tag1, tag2, ...],
            rationale: [{tag, score, weakness, staleness, strategic, accuracy}, ...]
        }
    """
    if not tag_stats:
        return {'focus_tags': [], 'rationale': []}

    # Filter tags by mode
    filtered_tags = {}
    for tag, data in tag_stats.items():
        if mode == 'all':
            # No filtering — include all tags across all categories
            filtered_tags[tag] = data
        elif mode in MODE_TAG_PREFIXES:
            # For financial/poker, only include relevant tags
            prefixes = MODE_TAG_PREFIXES[mode]
            if any(tag.startswith(p) or tag == p for p in prefixes):
                filtered_tags[tag] = data
        elif mode is None or mode in ('standard', 'time_trial', 'space_defense', 'custom'):
            # For arithmetic modes, exclude financial/poker tags
            is_special = False
            for prefixes in MODE_TAG_PREFIXES.values():
                if any(tag.startswith(p) or tag == p for p in prefixes):
                    is_special = True
                    break
            if not is_special:
                filtered_tags[tag] = data

    if not filtered_tags:
        return {'focus_tags': [], 'rationale': []}

    # Find max attempts for strategic value normalization
    max_attempts = max(d['attempts'] for d in filtered_tags.values()) if filtered_tags else 1

    scored = []
    for tag, data in filtered_tags.items():
        if data['attempts'] < MIN_ATTEMPTS:
            continue

        accuracy = _get_blended_accuracy(data)

        # Signal 1: Weakness (weight 0.5)
        weakness = 1.0 - accuracy

        # Signal 2: Staleness (weight 0.3)
        hours = _hours_since(data['last_seen'])
        optimal = _get_optimal_interval(accuracy)
        staleness = min(hours / optimal, 3.0) / 3.0  # Normalize to 0-1, cap at 3x

        # Signal 3: Strategic value (weight 0.2)
        frequency_bonus = (data['attempts'] / max_attempts) * 0.5
        trap_bonus = 0.5 if tag in TRAP_TAGS else 0
        strategic = min(frequency_bonus + trap_bonus, 1.0)

        composite = 0.5 * weakness + 0.3 * staleness + 0.2 * strategic

        scored.append({
            'tag': tag,
            'score': round(composite, 4),
            'weakness': round(weakness, 3),
            'staleness': round(staleness, 3),
            'strategic': round(strategic, 3),
            'accuracy': round(accuracy * 100, 1),
            'is_revision': accuracy >= 0.85
        })

    scored.sort(key=lambda x: x['score'], reverse=True)

    # Select top tags, ensuring at least 1 revision tag
    focus = []
    revision_included = False

    for item in scored:
        if len(focus) >= max_tags:
            break
        focus.append(item)
        if item['is_revision']:
            revision_included = True

    # If no revision tag included, swap the last one for the best revision candidate
    if not revision_included and len(focus) >= 2:
        revision_candidates = [s for s in scored if s['is_revision'] and s not in focus]
        if revision_candidates:
            focus[-1] = revision_candidates[0]

    focus_tags = [f['tag'] for f in focus]
    return {
        'focus_tags': focus_tags,
        'rationale': focus
    }
