import json
from datetime import date, datetime


def _parse_offer(row):
    if not row:
        return None
    return {
        'id': int(row.get('id', 0)),
        'program': row.get('program', ''),
        'offer_type': row.get('offer_type', ''),
        'title': row.get('title', ''),
        'details': json.loads(row['details']) if row.get('details') else {},
        'expiry_date': row.get('expiry_date', ''),
        'activated': row.get('activated', 'False') == 'True',
        'created_at': row.get('created_at', ''),
    }


def get_active_offers(store):
    today = date.today().isoformat()
    rows = store.read_all('offers')
    return [_parse_offer(r) for r in rows if r.get('expiry_date', '') >= today]


def get_offers_by_program(store, program):
    today = date.today().isoformat()
    rows = store.read_all('offers')
    return [_parse_offer(r) for r in rows
            if r.get('program') == program and r.get('expiry_date', '') >= today]


def insert_offers(store, offers_list):
    results = []
    for offer in offers_list:
        row = {
            'id': str(store.next_id('offers')),
            'program': offer.get('program', ''),
            'offer_type': offer.get('offer_type', ''),
            'title': offer.get('title', ''),
            'details': json.dumps(offer.get('details', {})),
            'expiry_date': offer.get('expiry_date', ''),
            'activated': str(offer.get('activated', False)),
            'created_at': datetime.now().isoformat(),
        }
        store.append_row('offers', row)
        results.append(row)
    return results


def expire_old_offers(store):
    today = date.today().isoformat()
    rows = store.read_all('offers')
    active = [r for r in rows if r.get('expiry_date', '') >= today]
    deleted_count = len(rows) - len(active)
    if deleted_count > 0:
        store.write_all('offers', active)
    return deleted_count
