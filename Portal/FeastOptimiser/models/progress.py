import json
from datetime import datetime


def _parse_progress(row):
    if not row:
        return None
    return {
        'id': int(row.get('id', 0)),
        'recipe_id': row.get('recipe_id', ''),
        'cuisine': row.get('cuisine', ''),
        'completed_date': row.get('completed_date', ''),
        'quality_ratings': json.loads(row['quality_ratings']) if row.get('quality_ratings') else {},
        'notes': row.get('notes', '') or None,
    }


def get_completed_recipes(store, cuisine=None):
    rows = store.read_all('progress')
    if cuisine:
        rows = [r for r in rows if r.get('cuisine') == cuisine]
    return [_parse_progress(r) for r in rows]


def get_completion_count(store, recipe_id):
    rows = store.query('progress', recipe_id=recipe_id)
    return len(rows)


def get_technique_completion_count(store, technique):
    rows = store.read_all('progress')
    count = 0
    for r in rows:
        ratings = json.loads(r['quality_ratings']) if r.get('quality_ratings') else {}
        if technique in ratings:
            count += 1
    return count


def insert_completion(store, completion_data):
    row = {
        'id': str(store.next_id('progress')),
        'recipe_id': completion_data.get('recipe_id', ''),
        'cuisine': completion_data.get('cuisine', ''),
        'completed_date': completion_data.get('completed_date', datetime.now().isoformat()),
        'quality_ratings': json.dumps(completion_data.get('quality_ratings', {})),
        'notes': completion_data.get('notes', ''),
    }
    store.append_row('progress', row)
    return row
