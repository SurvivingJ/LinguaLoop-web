from datetime import date, datetime, timedelta


def _parse_wishlist_item(row):
    if not row:
        return None
    return {
        'id': int(row.get('id', 0)),
        'product_name': row.get('product_name', ''),
        'product_id': row.get('product_id', '') or None,
        'category': row.get('category', 'grocery_staple'),
        'target_price': float(row['target_price']) if row.get('target_price') and row['target_price'] != 'None' else None,
        'alert_threshold_percent': int(row.get('alert_threshold_percent', 10)),
        'baseline_price': float(row['baseline_price']) if row.get('baseline_price') and row['baseline_price'] != 'None' else None,
        'current_best_price': float(row['current_best_price']) if row.get('current_best_price') and row['current_best_price'] != 'None' else None,
        'current_best_store': row.get('current_best_store', '') or None,
        'stores_to_track': row.get('stores_to_track', '').split('|') if row.get('stores_to_track') else [],
        'recipient': row.get('recipient', '') or None,
        'occasion': row.get('occasion', '') or None,
        'occasion_date': row.get('occasion_date', '') or None,
        'priority': row.get('priority', 'medium'),
        'purchased': row.get('purchased', 'False') == 'True',
        'created_at': row.get('created_at', ''),
    }


def get_active_wishlist(store):
    rows = store.read_all('wishlist')
    return [_parse_wishlist_item(r) for r in rows if r.get('purchased', 'False') != 'True']


def get_upcoming_gifts(store, days=60):
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    today_str = date.today().isoformat()
    rows = store.read_all('wishlist')
    results = []
    for r in rows:
        if r.get('purchased', 'False') == 'True':
            continue
        occ_date = r.get('occasion_date', '')
        if occ_date and today_str <= occ_date <= cutoff:
            results.append(_parse_wishlist_item(r))
    return sorted(results, key=lambda x: x['occasion_date'] or '')


def upsert_wishlist_item(store, item_data):
    if 'id' not in item_data or not item_data['id']:
        item_data['id'] = store.next_id('wishlist')
    row = {
        'id': str(item_data['id']),
        'product_name': item_data.get('product_name', ''),
        'product_id': str(item_data.get('product_id', '') or ''),
        'category': item_data.get('category', 'grocery_staple'),
        'target_price': str(item_data.get('target_price', '')),
        'alert_threshold_percent': str(item_data.get('alert_threshold_percent', 10)),
        'baseline_price': str(item_data.get('baseline_price', '')),
        'current_best_price': str(item_data.get('current_best_price', '')),
        'current_best_store': str(item_data.get('current_best_store', '')),
        'stores_to_track': '|'.join(item_data.get('stores_to_track', [])),
        'recipient': str(item_data.get('recipient', '') or ''),
        'occasion': str(item_data.get('occasion', '') or ''),
        'occasion_date': str(item_data.get('occasion_date', '') or ''),
        'priority': item_data.get('priority', 'medium'),
        'purchased': str(item_data.get('purchased', False)),
        'created_at': item_data.get('created_at', datetime.now().isoformat()),
    }
    return store.upsert('wishlist', row, key_field='id')


def mark_purchased(store, item_id):
    rows = store.read_all('wishlist')
    for r in rows:
        if r.get('id') == str(item_id):
            r['purchased'] = 'True'
    store.write_all('wishlist', rows)
