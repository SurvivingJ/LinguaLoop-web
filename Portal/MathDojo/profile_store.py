"""
ProfileStore - Read/write JSON stats file for user profiles.
Handles recording problem results, session tracking, and stats summaries.
"""
import json
import os
import threading
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ROLLING_WINDOW = 30
MAX_SESSIONS = 100

_lock = threading.Lock()


def _stats_path(profile_name):
    return os.path.join(DATA_DIR, f'{profile_name}_stats.json')


def _empty_profile(name):
    return {
        'profile': name,
        'created': datetime.now(timezone.utc).isoformat(),
        'tag_stats': {},
        'sessions': []
    }


def _empty_tag():
    return {
        'attempts': 0,
        'correct': 0,
        'total_time_ms': 0,
        'last_seen': None,
        'history': []
    }


def load_profile(name):
    """Load profile from JSON file. Returns empty profile if not found."""
    path = _stats_path(name)
    if not os.path.exists(path):
        return _empty_profile(name)
    with open(path, 'r') as f:
        return json.load(f)


def save_profile(data):
    """Save profile data to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = _stats_path(data['profile'])
    with _lock:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


def record_results(profile_name, results, session_info=None):
    """
    Record a batch of problem results.

    Args:
        profile_name: 'james' etc.
        results: list of {tags: [...], correct: bool, time_ms: int}
        session_info: optional {mode, duration_s, problems_attempted, correct}
    """
    with _lock:
        data = load_profile(profile_name)
        now = datetime.now(timezone.utc).isoformat()

        for result in results:
            tags = result.get('tags', [])
            correct = result.get('correct', False)
            time_ms = result.get('time_ms', 0)

            for tag in tags:
                if tag not in data['tag_stats']:
                    data['tag_stats'][tag] = _empty_tag()

                ts = data['tag_stats'][tag]
                ts['attempts'] += 1
                if correct:
                    ts['correct'] += 1
                ts['total_time_ms'] += time_ms
                ts['last_seen'] = now
                ts['history'].append(1 if correct else 0)
                # Keep rolling window
                if len(ts['history']) > ROLLING_WINDOW:
                    ts['history'] = ts['history'][-ROLLING_WINDOW:]

        if session_info:
            session_info['date'] = now
            data['sessions'].append(session_info)
            # Cap sessions
            if len(data['sessions']) > MAX_SESSIONS:
                data['sessions'] = data['sessions'][-MAX_SESSIONS:]

        # Save without lock (we already hold it)
        os.makedirs(DATA_DIR, exist_ok=True)
        path = _stats_path(data['profile'])
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    return data


def get_stats_summary(profile_name):
    """
    Compute a stats summary for the dashboard.

    Returns:
        {
            operation_accuracy: {add: {attempts, correct, pct}, ...},
            weakest_tags: [{tag, accuracy, attempts}, ...],
            strongest_tags: [{tag, accuracy, attempts}, ...],
            recent_sessions: [...],
            overall: {total_problems, total_correct, avg_time_ms}
        }
    """
    data = load_profile(profile_name)
    tag_stats = data.get('tag_stats', {})

    # Operation-level accuracy
    op_accuracy = {}
    for op in ['op:add', 'op:sub', 'op:mul', 'op:div']:
        ts = tag_stats.get(op)
        if ts and ts['attempts'] > 0:
            op_accuracy[op] = {
                'attempts': ts['attempts'],
                'correct': ts['correct'],
                'pct': round(ts['correct'] / ts['attempts'] * 100, 1)
            }

    # Tag-level accuracy for all tags with enough data
    tag_accuracies = []
    for tag, ts in tag_stats.items():
        if ts['attempts'] >= 3:
            # Use rolling window for recency-weighted accuracy
            if ts['history']:
                recent_acc = sum(ts['history']) / len(ts['history'])
            else:
                recent_acc = ts['correct'] / ts['attempts']
            lifetime_acc = ts['correct'] / ts['attempts']
            blended = 0.7 * recent_acc + 0.3 * lifetime_acc
            avg_time = ts['total_time_ms'] / ts['attempts'] if ts['attempts'] > 0 else 0

            tag_accuracies.append({
                'tag': tag,
                'accuracy': round(blended * 100, 1),
                'attempts': ts['attempts'],
                'avg_time_ms': round(avg_time),
                'last_seen': ts['last_seen']
            })

    # Sort for weakest/strongest
    tag_accuracies.sort(key=lambda x: x['accuracy'])
    weakest = [t for t in tag_accuracies if not t['tag'].startswith('op:')][:10]
    strongest = [t for t in reversed(tag_accuracies) if not t['tag'].startswith('op:')][:10]

    # Overall stats
    total_problems = sum(ts['attempts'] for ts in tag_stats.values() if ts.get('attempts'))
    total_correct = sum(ts['correct'] for ts in tag_stats.values() if ts.get('correct'))
    total_time = sum(ts['total_time_ms'] for ts in tag_stats.values() if ts.get('total_time_ms'))
    # Avoid double-counting: use operation tags only for overall
    op_tags = [tag_stats.get(op) for op in ['op:add', 'op:sub', 'op:mul', 'op:div'] if op in tag_stats]
    if op_tags:
        total_problems = sum(t['attempts'] for t in op_tags)
        total_correct = sum(t['correct'] for t in op_tags)
        total_time = sum(t['total_time_ms'] for t in op_tags)

    return {
        'operation_accuracy': op_accuracy,
        'weakest_tags': weakest,
        'strongest_tags': strongest,
        'recent_sessions': data.get('sessions', [])[-10:],
        'overall': {
            'total_problems': total_problems,
            'total_correct': total_correct,
            'avg_time_ms': round(total_time / total_problems) if total_problems > 0 else 0
        }
    }
