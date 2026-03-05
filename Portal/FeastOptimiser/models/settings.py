DEFAULTS = {
    'weekly_budget': '150',
    'daily_protein': '120',
    'daily_carbs': '250',
    'daily_fat': '65',
    'daily_calories': '2200',
    'owned_items': 'PROD_salt|PROD_pepper|PROD_olive_oil|PROD_vegetable_oil|PROD_sugar_white|PROD_flour_plain',
    'theme': 'bauhaus',
    'cuisine_preferences': 'chinese|italian|japanese',
}

NUMERIC_KEYS = {'weekly_budget', 'daily_protein', 'daily_carbs', 'daily_fat', 'daily_calories'}
LIST_KEYS = {'owned_items', 'cuisine_preferences'}


def get_settings(store):
    """Read settings as a dict. Initialize defaults if empty."""
    rows = store.read_all('settings')
    if not rows:
        _write_defaults(store)
        rows = store.read_all('settings')

    settings = {}
    for row in rows:
        key = row.get('key', '')
        value = row.get('value', '')
        if key in NUMERIC_KEYS:
            try:
                settings[key] = float(value)
            except (ValueError, TypeError):
                settings[key] = float(DEFAULTS.get(key, 0))
        elif key in LIST_KEYS:
            settings[key] = value.split('|') if value else []
        else:
            settings[key] = value
    return settings


def update_settings(store, updates):
    """Update one or more settings. Merges with existing."""
    current = store.read_all('settings')
    current_dict = {r['key']: r['value'] for r in current}

    for key, value in updates.items():
        if isinstance(value, list):
            current_dict[key] = '|'.join(str(v) for v in value)
        else:
            current_dict[key] = str(value)

    rows = [{'key': k, 'value': v} for k, v in current_dict.items()]
    store.write_all('settings', rows, fieldnames=['key', 'value'])


def get_owned_items(store):
    settings = get_settings(store)
    return settings.get('owned_items', [])


def _write_defaults(store):
    rows = [{'key': k, 'value': v} for k, v in DEFAULTS.items()]
    store.write_all('settings', rows, fieldnames=['key', 'value'])
