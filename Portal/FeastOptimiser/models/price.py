from datetime import datetime, timedelta


def _parse_price(row):
    if not row:
        return None
    return {
        'id': int(row.get('id', 0)),
        'product_id': row['product_id'],
        'store': row['store'],
        'price': float(row.get('price', 0)),
        'unit_price': float(row['unit_price']) if row.get('unit_price') else None,
        'promotion_active': row.get('promotion_active', 'False') == 'True',
        'promotion_details': row.get('promotion_details', '') or None,
        'timestamp': row.get('timestamp', ''),
    }


def get_current_price(store, product_id, store_name):
    rows = store.read_all('prices')
    matches = [r for r in rows if r.get('product_id') == product_id and r.get('store') == store_name]
    if not matches:
        return None
    matches.sort(key=lambda r: r.get('timestamp', ''), reverse=True)
    return float(matches[0].get('price', 0))


def get_current_prices_all_stores(store, product_id):
    rows = store.read_all('prices')
    matches = [r for r in rows if r.get('product_id') == product_id]
    # Group by store, keep latest per store
    latest = {}
    for r in matches:
        s = r.get('store', '')
        ts = r.get('timestamp', '')
        if s not in latest or ts > latest[s].get('timestamp', ''):
            latest[s] = r
    return {s: _parse_price(r) for s, r in latest.items()}


def get_cheapest_option(store, product_id):
    prices = get_current_prices_all_stores(store, product_id)
    if not prices:
        return None
    cheapest_store = min(prices, key=lambda s: prices[s]['price'])
    return prices[cheapest_store]


def get_price_history(store, product_id, store_name=None, days=30):
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    rows = store.read_all('prices')
    results = []
    for r in rows:
        if r.get('product_id') != product_id:
            continue
        if store_name and r.get('store') != store_name:
            continue
        if r.get('timestamp', '') >= cutoff:
            results.append(_parse_price(r))
    return sorted(results, key=lambda r: r['timestamp'])


def insert_price(store, price_data):
    row = {
        'id': str(store.next_id('prices')),
        'product_id': price_data['product_id'],
        'store': price_data['store'],
        'price': str(price_data['price']),
        'unit_price': str(price_data.get('unit_price', '')),
        'promotion_active': str(price_data.get('promotion_active', False)),
        'promotion_details': price_data.get('promotion_details', ''),
        'timestamp': price_data.get('timestamp', datetime.now().isoformat()),
    }
    store.append_row('prices', row)
    return row
