"""USDA FoodData Central API client and nutrition calculator."""

import requests
from config import Config


# Standard conversion table: unit -> grams
UNIT_TO_GRAMS = {
    'cup': 240,
    'cups': 240,
    'tbsp': 15,
    'tablespoon': 15,
    'tablespoons': 15,
    'tsp': 5,
    'teaspoon': 5,
    'teaspoons': 5,
    'g': 1,
    'gram': 1,
    'grams': 1,
    'kg': 1000,
    'ml': 1,
    'l': 1000,
    'litre': 1000,
    'liter': 1000,
    'oz': 28.35,
    'ounce': 28.35,
    'lb': 453.6,
    'pound': 453.6,
}


def search_food(query):
    """Search USDA FoodData Central for matching foods."""
    if not Config.USDA_API_KEY:
        return []

    url = 'https://api.nal.usda.gov/fdc/v1/foods/search'
    params = {
        'query': query,
        'api_key': Config.USDA_API_KEY,
        'dataType': ['Foundation', 'SR Legacy'],
        'pageSize': 10,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [{
            'fdc_id': item['fdcId'],
            'description': item['description'],
            'data_type': item.get('dataType', ''),
        } for item in data.get('foods', [])]
    except Exception:
        return []


def get_nutrition(fdc_id):
    """Fetch macro nutrients per 100g from USDA API."""
    if not Config.USDA_API_KEY:
        return {}

    url = f'https://api.nal.usda.gov/fdc/v1/food/{fdc_id}'
    params = {'api_key': Config.USDA_API_KEY}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        nutrients = {}
        nutrient_map = {
            1003: 'protein',
            1004: 'fat',
            1005: 'carbs',
            1008: 'calories',
            1079: 'fiber',
        }

        for nutrient in data.get('foodNutrients', []):
            nid = nutrient.get('nutrient', {}).get('id')
            if nid in nutrient_map:
                nutrients[nutrient_map[nid]] = round(nutrient.get('amount', 0), 1)

        return nutrients
    except Exception:
        return {}


def convert_to_grams(quantity, unit, product=None):
    """Convert a quantity + unit to grams."""
    unit_lower = unit.lower().strip()

    # Direct unit conversion
    if unit_lower in UNIT_TO_GRAMS:
        return quantity * UNIT_TO_GRAMS[unit_lower]

    # Countable items (each, piece, clove, etc.)
    if unit_lower in ('each', 'piece', 'pieces', 'clove', 'cloves', 'slice', 'slices'):
        if product and product.get('average_weight_per_piece_g'):
            return quantity * product['average_weight_per_piece_g']
        return quantity * 50  # rough fallback

    # If unit is empty or unknown, assume grams
    return quantity


def calculate_recipe_macros(recipe, ingredients, products):
    """Calculate per-serving macros for a recipe.

    Args:
        recipe: recipe dict with 'servings'
        ingredients: list of {canonical_product_id, quantity, unit}
        products: dict mapping product_id to product dict
    """
    totals = {'protein': 0, 'carbs': 0, 'fat': 0, 'calories': 0, 'fiber': 0}
    servings = recipe.get('servings', 4)

    for ing in ingredients:
        prod_id = ing.get('canonical_product_id', '')
        product = products.get(prod_id)
        if not product or not product.get('nutrition_per_100g'):
            continue

        quantity = float(ing.get('quantity', 0))
        unit = ing.get('unit', 'g')
        grams = convert_to_grams(quantity, unit, product)

        nutrition = product['nutrition_per_100g']
        factor = grams / 100

        for macro in totals:
            totals[macro] += nutrition.get(macro, 0) * factor

    # Per serving
    per_serving = {k: round(v / servings, 1) for k, v in totals.items()}
    return per_serving
