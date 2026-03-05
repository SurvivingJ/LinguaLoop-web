"""Cross-store product matching using barcode and fuzzy string matching."""

import re
from thefuzz import fuzz


# Brand names to strip during normalization
BRAND_NAMES = [
    'coles', 'woolworths', 'woolies', 'aldi', 'macro', 'community co',
    'homebrand', 'essentials', 'simply', 'farmers own',
]

# Weight/volume pattern
WEIGHT_PATTERN = re.compile(r'(\d+\.?\d*)\s*(g|kg|ml|l|L)\b', re.IGNORECASE)


def normalize_product_name(name):
    """Clean product name for comparison."""
    name = name.lower().strip()
    # Remove brand names
    for brand in BRAND_NAMES:
        name = name.replace(brand, '')
    # Remove weight/volume
    name = WEIGHT_PATTERN.sub('', name)
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def extract_metadata(name):
    """Extract weight/volume and tokenize for matching."""
    weight_match = WEIGHT_PATTERN.search(name)
    weight = weight_match.group(0) if weight_match else None

    # Normalize weight to grams for comparison
    weight_g = None
    if weight_match:
        val = float(weight_match.group(1))
        unit = weight_match.group(2).lower()
        if unit == 'kg':
            weight_g = val * 1000
        elif unit in ('g',):
            weight_g = val
        elif unit == 'l':
            weight_g = val * 1000  # treat mL as proxy
        elif unit == 'ml':
            weight_g = val

    cleaned = normalize_product_name(name)
    tokens = cleaned.split()

    return {
        'weight': weight,
        'weight_g': weight_g,
        'tokens': tokens,
    }


def find_barcode_match(barcode, store_products):
    """Find exact barcode match in product list."""
    if not barcode:
        return None
    for product in store_products:
        if product.get('barcode') == barcode:
            return product
    return None


def find_fuzzy_match(product, candidates, threshold=80):
    """Multi-level fuzzy matching. Weight/volume must match exactly."""
    source_meta = extract_metadata(product.get('name', ''))
    source_name = normalize_product_name(product.get('name', ''))

    best_match = None
    best_score = 0

    for candidate in candidates:
        cand_meta = extract_metadata(candidate.get('name', ''))

        # Weight must match if both have weights
        if source_meta['weight_g'] and cand_meta['weight_g']:
            if abs(source_meta['weight_g'] - cand_meta['weight_g']) > 1:
                continue

        cand_name = normalize_product_name(candidate.get('name', ''))

        # Multi-level scoring
        ratio = fuzz.ratio(source_name, cand_name)
        token_sort = fuzz.token_sort_ratio(source_name, cand_name)
        token_set = fuzz.token_set_ratio(source_name, cand_name)

        # Weighted average
        score = (ratio * 0.3) + (token_sort * 0.35) + (token_set * 0.35)

        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate
            best_match['_match_score'] = round(score, 1)

    return best_match


def match_products_across_stores(coles_products, woolworths_products):
    """Match products between stores. Returns canonical product entries."""
    matched = []
    unmatched_woolworths = list(woolworths_products)

    for coles_prod in coles_products:
        # Try barcode first
        barcode = coles_prod.get('barcode')
        match = find_barcode_match(barcode, unmatched_woolworths) if barcode else None

        if not match:
            # Fuzzy fallback
            match = find_fuzzy_match(coles_prod, unmatched_woolworths)

        if match:
            canonical = {
                'name': coles_prod.get('name', ''),
                'store_mappings': {
                    'coles': {'product_id': coles_prod.get('id'), 'name': coles_prod.get('name')},
                    'woolworths': {'product_id': match.get('id'), 'name': match.get('name')},
                },
                'match_confidence': match.get('_match_score', 100),
            }
            matched.append(canonical)
            unmatched_woolworths.remove(match)
        else:
            # Coles-only product
            matched.append({
                'name': coles_prod.get('name', ''),
                'store_mappings': {
                    'coles': {'product_id': coles_prod.get('id'), 'name': coles_prod.get('name')},
                },
                'match_confidence': 0,
            })

    return matched


def verify_match(store, canonical_product_id, store_name, store_product_id, confirmed):
    """Allow manual confirmation or rejection of automated matches."""
    from models.product import get_product_by_id, upsert_product
    product = get_product_by_id(store, canonical_product_id)
    if not product:
        return None

    if confirmed:
        product['store_mappings'][store_name] = {'product_id': store_product_id, 'verified': True}
    else:
        product['store_mappings'].pop(store_name, None)

    upsert_product(store, product)
    return product
