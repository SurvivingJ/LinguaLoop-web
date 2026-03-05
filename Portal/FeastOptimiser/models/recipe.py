import json


def _parse_recipe(row):
    """Parse CSV string fields into proper types."""
    if not row:
        return None
    return {
        'id': row['id'],
        'name': row['name'],
        'cuisine': row.get('cuisine', ''),
        'difficulty': int(row.get('difficulty', 1)),
        'tier': row.get('tier', 'beginner'),
        'prep_time': int(row.get('prep_time', 0)),
        'cook_time': int(row.get('cook_time', 0)),
        'servings': int(row.get('servings', 4)),
        'techniques_taught': row.get('techniques_taught', '').split('|') if row.get('techniques_taught') else [],
        'key_learnings': row.get('key_learnings', ''),
        'builds_on': row.get('builds_on', '').split('|') if row.get('builds_on') else [],
        'macros_per_serving': json.loads(row['macros_per_serving']) if row.get('macros_per_serving') else {},
        'instructions': json.loads(row['instructions']) if row.get('instructions') else [],
        'video_url': row.get('video_url', '') or None,
        'video_timestamps': json.loads(row['video_timestamps']) if row.get('video_timestamps') and row['video_timestamps'] != 'None' else None,
        'source': row.get('source', 'manual'),
        'created_at': row.get('created_at', ''),
    }


def _serialize_recipe(data):
    """Serialize recipe dict for CSV storage."""
    return {
        'id': data['id'],
        'name': data['name'],
        'cuisine': data.get('cuisine', ''),
        'difficulty': str(data.get('difficulty', 1)),
        'tier': data.get('tier', 'beginner'),
        'prep_time': str(data.get('prep_time', 0)),
        'cook_time': str(data.get('cook_time', 0)),
        'servings': str(data.get('servings', 4)),
        'techniques_taught': '|'.join(data.get('techniques_taught', [])),
        'key_learnings': data.get('key_learnings', ''),
        'builds_on': '|'.join(data.get('builds_on', [])),
        'macros_per_serving': json.dumps(data.get('macros_per_serving', {})),
        'instructions': json.dumps(data.get('instructions', [])),
        'video_url': data.get('video_url', '') or '',
        'video_timestamps': json.dumps(data.get('video_timestamps')) if data.get('video_timestamps') else '',
        'source': data.get('source', 'manual'),
        'created_at': data.get('created_at', ''),
    }


def get_recipes_by_cuisine(store, cuisine):
    rows = store.query('recipes', cuisine=cuisine)
    recipes = [_parse_recipe(r) for r in rows]
    return sorted(recipes, key=lambda r: r['difficulty'])


def get_recipes_by_technique(store, technique):
    all_rows = store.read_all('recipes')
    results = []
    for row in all_rows:
        techniques = row.get('techniques_taught', '').split('|')
        if technique in techniques:
            results.append(_parse_recipe(row))
    return results


def get_recipes_by_tier(store, cuisine, tier):
    all_rows = store.read_all('recipes')
    results = []
    for row in all_rows:
        if row.get('cuisine') == cuisine and row.get('tier') == tier:
            results.append(_parse_recipe(row))
    return sorted(results, key=lambda r: r['difficulty'])


def search_recipes(store, filters):
    all_rows = store.read_all('recipes')
    results = []
    for row in all_rows:
        parsed = _parse_recipe(row)
        if filters.get('cuisine') and parsed['cuisine'] != filters['cuisine']:
            continue
        if filters.get('difficulty_max') and parsed['difficulty'] > int(filters['difficulty_max']):
            continue
        if filters.get('time_max'):
            total_time = parsed['prep_time'] + parsed['cook_time']
            if total_time > int(filters['time_max']):
                continue
        if filters.get('technique'):
            if filters['technique'] not in parsed['techniques_taught']:
                continue
        if filters.get('text_query'):
            query = filters['text_query'].lower()
            if query not in parsed['name'].lower():
                continue
        results.append(parsed)
    return results


def get_recipe_ingredients(store, recipe_id):
    rows = store.query('recipe_ingredients', recipe_id=recipe_id)
    return [{
        'recipe_id': r['recipe_id'],
        'canonical_product_id': r['canonical_product_id'],
        'quantity': float(r.get('quantity', 0)),
        'unit': r.get('unit', ''),
        'notes': r.get('notes', ''),
    } for r in rows]


def upsert_recipe(store, recipe_data, ingredients=None):
    serialized = _serialize_recipe(recipe_data)
    store.upsert('recipes', serialized, key_field='id')

    if ingredients is not None:
        # Delete existing ingredients for this recipe, then re-insert
        store.delete('recipe_ingredients', recipe_id=recipe_data['id'])
        for ing in ingredients:
            store.append_row('recipe_ingredients', {
                'recipe_id': recipe_data['id'],
                'canonical_product_id': ing.get('canonical_product_id', ''),
                'quantity': str(ing.get('quantity', 0)),
                'unit': ing.get('unit', ''),
                'notes': ing.get('notes', ''),
            })
    return serialized
