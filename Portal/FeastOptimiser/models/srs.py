import json
from datetime import datetime, timedelta


def _parse_card(row):
    if not row:
        return None
    return {
        'technique': row['technique'],
        'easiness_factor': float(row.get('easiness_factor', 2.5)),
        'interval': int(row.get('interval', 1)),
        'repetitions': int(row.get('repetitions', 0)),
        'next_review_date': row.get('next_review_date', ''),
        'last_practiced': row.get('last_practiced', '') or None,
        'quality_history': json.loads(row['quality_history']) if row.get('quality_history') else [],
    }


def _serialize_card(data):
    return {
        'technique': data['technique'],
        'easiness_factor': str(data.get('easiness_factor', 2.5)),
        'interval': str(data.get('interval', 1)),
        'repetitions': str(data.get('repetitions', 0)),
        'next_review_date': data.get('next_review_date', datetime.now().isoformat()),
        'last_practiced': data.get('last_practiced', '') or '',
        'quality_history': json.dumps(data.get('quality_history', [])),
    }


def get_card(store, technique):
    results = store.query('srs_cards', technique=technique)
    return _parse_card(results[0]) if results else None


def get_due_cards(store, limit=10):
    now = datetime.now().isoformat()
    rows = store.read_all('srs_cards')
    due = [_parse_card(r) for r in rows if r.get('next_review_date', '') <= now]
    due.sort(key=lambda c: c['next_review_date'])
    return due[:limit]


def get_upcoming_reviews(store, days=7):
    now = datetime.now()
    cutoff = (now + timedelta(days=days)).isoformat()
    now_str = now.isoformat()
    rows = store.read_all('srs_cards')
    upcoming = []
    for r in rows:
        review = r.get('next_review_date', '')
        if now_str <= review <= cutoff:
            upcoming.append(_parse_card(r))
    return sorted(upcoming, key=lambda c: c['next_review_date'])


def upsert_card(store, card_data):
    serialized = _serialize_card(card_data)
    return store.upsert('srs_cards', serialized, key_field='technique')
