"""Recipe import from TheMealDB and web scraping."""

import re
import json
import requests
from bs4 import BeautifulSoup


MEALDB_BASE = 'https://www.themealdb.com/api/json/v1/1'

# Fraction patterns
FRACTION_MAP = {
    '1/4': 0.25, '1/3': 0.333, '1/2': 0.5, '2/3': 0.667, '3/4': 0.75,
    '1/8': 0.125, '3/8': 0.375, '5/8': 0.625, '7/8': 0.875,
}


def import_from_mealdb(meal_name):
    """Search TheMealDB by name, return partially populated recipe dict."""
    try:
        resp = requests.get(f'{MEALDB_BASE}/search.php', params={'s': meal_name}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        meals = data.get('meals')
        if not meals:
            return None
        return _parse_mealdb_meal(meals[0])
    except Exception:
        return None


def import_from_mealdb_by_id(meal_id):
    """Lookup a single meal by ID from TheMealDB."""
    try:
        resp = requests.get(f'{MEALDB_BASE}/lookup.php', params={'i': meal_id}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        meals = data.get('meals')
        if not meals:
            return None
        return _parse_mealdb_meal(meals[0])
    except Exception:
        return None


def import_from_mealdb_by_cuisine(cuisine):
    """Bulk import all recipes for a cuisine from TheMealDB."""
    try:
        resp = requests.get(f'{MEALDB_BASE}/filter.php', params={'a': cuisine}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        meals = data.get('meals') or []

        results = []
        for meal_summary in meals:
            meal = import_from_mealdb_by_id(meal_summary['idMeal'])
            if meal:
                results.append(meal)
        return results
    except Exception:
        return []


def _parse_mealdb_meal(meal):
    """Parse a TheMealDB meal object into our recipe format."""
    ingredients_raw = []
    for i in range(1, 21):
        name = (meal.get(f'strIngredient{i}') or '').strip()
        measure = (meal.get(f'strMeasure{i}') or '').strip()
        if name:
            ingredients_raw.append({'name': name, 'measure': measure})

    instructions_text = meal.get('strInstructions', '')
    # Split on numbered steps or newlines
    steps = re.split(r'\r?\n|\d+\.\s*', instructions_text)
    steps = [s.strip() for s in steps if s.strip()]

    return {
        'mealdb_id': meal.get('idMeal', ''),
        'name': meal.get('strMeal', ''),
        'cuisine': (meal.get('strArea', '') or '').lower(),
        'category': meal.get('strCategory', ''),
        'instructions': steps,
        'ingredients_raw': ingredients_raw,
        'video_url': meal.get('strYoutube', '') or None,
        'thumbnail': meal.get('strMealThumb', ''),
        'source': 'themealdb',
    }


def parse_measure_string(measure):
    """Parse free-text measurements into (quantity, unit).

    Examples:
        "2 cups" -> (2.0, "cups")
        "1/2 tsp" -> (0.5, "tsp")
        "2 1/2 cups" -> (2.5, "cups")
        "400g" -> (400.0, "g")
        "3 cloves" -> (3.0, "cloves")
        "" -> (1.0, "each")
    """
    if not measure or not measure.strip():
        return (1.0, 'each')

    measure = measure.strip().lower()

    # Pattern: "400g" or "200ml" (no space)
    match = re.match(r'^(\d+\.?\d*)\s*(g|kg|ml|l)$', measure)
    if match:
        return (float(match.group(1)), match.group(2))

    # Pattern: mixed number + fraction + unit: "2 1/2 cups"
    match = re.match(r'^(\d+)\s+(\d+/\d+)\s*(.*)$', measure)
    if match:
        whole = float(match.group(1))
        frac = FRACTION_MAP.get(match.group(2), 0)
        unit = match.group(3).strip() or 'each'
        return (whole + frac, unit)

    # Pattern: fraction + unit: "1/2 tsp"
    match = re.match(r'^(\d+/\d+)\s*(.*)$', measure)
    if match:
        frac = FRACTION_MAP.get(match.group(1), 0)
        if frac == 0:
            parts = match.group(1).split('/')
            try:
                frac = float(parts[0]) / float(parts[1])
            except (ValueError, ZeroDivisionError):
                frac = 1.0
        unit = match.group(2).strip() or 'each'
        return (frac, unit)

    # Pattern: number + unit: "2 cups"
    match = re.match(r'^(\d+\.?\d*)\s+(.+)$', measure)
    if match:
        return (float(match.group(1)), match.group(2).strip())

    # Pattern: just a number: "3"
    match = re.match(r'^(\d+\.?\d*)$', measure)
    if match:
        return (float(match.group(1)), 'each')

    # Fallback: treat entire string as unit with quantity 1
    return (1.0, measure)


def map_ingredients_to_canonical(store, ingredients_raw):
    """Map TheMealDB ingredients to canonical products using fuzzy matching."""
    from models.product import get_all_products
    from services.product_matcher import normalize_product_name, find_fuzzy_match

    products = get_all_products(store)
    mapped = []

    for ing in ingredients_raw:
        name = ing.get('name', '')
        measure = ing.get('measure', '')
        quantity, unit = parse_measure_string(measure)

        # Try to find canonical product
        source = {'name': name}
        candidates = [{'name': p['name'], 'id': p['id']} for p in products]
        match = find_fuzzy_match(source, candidates, threshold=70)

        mapped.append({
            'canonical_product_id': match['id'] if match else '',
            'original_name': name,
            'quantity': quantity,
            'unit': unit,
            'notes': f'Original: {measure} {name}' if not match else '',
        })

    return mapped


def scrape_recipe_from_url(url):
    """Extract structured recipe data from websites using schema.org JSON-LD."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; FeastOptimizer/1.0)'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Look for JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                # Handle both direct Recipe and @graph array
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Recipe':
                            return _parse_schema_recipe(item)
                elif isinstance(data, dict):
                    if data.get('@type') == 'Recipe':
                        return _parse_schema_recipe(data)
                    if '@graph' in data:
                        for item in data['@graph']:
                            if item.get('@type') == 'Recipe':
                                return _parse_schema_recipe(item)
            except (json.JSONDecodeError, TypeError):
                continue

        return None
    except Exception:
        return None


def _parse_schema_recipe(data):
    """Parse a schema.org Recipe JSON-LD object."""
    ingredients = []
    for ing in data.get('recipeIngredient', []):
        quantity, unit = parse_measure_string(ing)
        # Try to separate ingredient name from measure
        name = re.sub(r'^[\d\s/]+\s*(cups?|tbsp|tsp|g|kg|ml|l|oz|lb|cloves?|pieces?)\s*', '', ing, flags=re.IGNORECASE).strip()
        ingredients.append({
            'name': name or ing,
            'measure': ing,
            'quantity': quantity,
            'unit': unit,
        })

    instructions = []
    for step in data.get('recipeInstructions', []):
        if isinstance(step, str):
            instructions.append(step)
        elif isinstance(step, dict):
            instructions.append(step.get('text', ''))

    return {
        'name': data.get('name', ''),
        'instructions': instructions,
        'ingredients_raw': ingredients,
        'prep_time': _parse_duration(data.get('prepTime', '')),
        'cook_time': _parse_duration(data.get('cookTime', '')),
        'servings': _parse_yield(data.get('recipeYield', '')),
        'source': 'scraped',
    }


def _parse_duration(duration_str):
    """Parse ISO 8601 duration (PT30M, PT1H30M) to minutes."""
    if not duration_str:
        return 0
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', duration_str)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        return hours * 60 + minutes
    return 0


def _parse_yield(yield_str):
    """Parse recipe yield to integer servings."""
    if not yield_str:
        return 4
    match = re.search(r'(\d+)', str(yield_str))
    return int(match.group(1)) if match else 4
