import json


def _parse_product(row):
    """Parse CSV string fields into proper types."""
    if not row:
        return None
    return {
        'id': row['id'],
        'name': row['name'],
        'category': row.get('category', ''),
        'base_unit': row.get('base_unit', 'kg'),
        'nutrition_per_100g': json.loads(row['nutrition_per_100g']) if row.get('nutrition_per_100g') else {},
        'usda_fdc_id': int(row['usda_fdc_id']) if row.get('usda_fdc_id') and row['usda_fdc_id'] != 'None' else None,
        'aliases': row.get('aliases', '').split('|') if row.get('aliases') else [],
        'store_mappings': json.loads(row['store_mappings']) if row.get('store_mappings') else {},
        'average_weight_per_piece_g': float(row['average_weight_per_piece_g']) if row.get('average_weight_per_piece_g') and row['average_weight_per_piece_g'] != 'None' else None,
        'created_at': row.get('created_at', ''),
    }


def _serialize_product(data):
    """Serialize product dict for CSV storage."""
    return {
        'id': data['id'],
        'name': data['name'],
        'category': data.get('category', ''),
        'base_unit': data.get('base_unit', 'kg'),
        'nutrition_per_100g': json.dumps(data.get('nutrition_per_100g', {})),
        'usda_fdc_id': str(data.get('usda_fdc_id', '')),
        'aliases': '|'.join(data.get('aliases', [])),
        'store_mappings': json.dumps(data.get('store_mappings', {})),
        'average_weight_per_piece_g': str(data.get('average_weight_per_piece_g', '')),
        'created_at': data.get('created_at', ''),
    }


def get_all_products(store):
    rows = store.read_all('products')
    return [_parse_product(r) for r in rows]


def get_product_by_id(store, product_id):
    results = store.query('products', id=product_id)
    return _parse_product(results[0]) if results else None


def upsert_product(store, product_data):
    serialized = _serialize_product(product_data)
    return store.upsert('products', serialized, key_field='id')
