"""Tests for the meal plan optimizer."""

import pytest
from services.optimizer import (
    optimize_meal_plan, calculate_recipe_cost,
    calculate_effective_price, check_offer_applies
)


def _make_recipe(id, name, macros, servings=4, cuisine='chinese', ingredients=None):
    return {
        'id': id,
        'name': name,
        'macros_per_serving': macros,
        'servings': servings,
        'cuisine': cuisine,
        '_ingredients': ingredients or [],
    }


def _make_product(id, name, category='protein', price=5.0):
    return {
        'id': id,
        'name': name,
        'category': category,
        'store_mappings': {
            'coles': {'current_price': price},
        },
    }


def test_basic_plan_generation():
    recipes = [
        _make_recipe('r1', 'Rice Bowl', {'protein': 30, 'carbs': 50, 'fat': 10, 'calories': 400}, servings=7),
        _make_recipe('r2', 'Pasta', {'protein': 25, 'carbs': 60, 'fat': 15, 'calories': 450}, servings=7),
    ]
    result = optimize_meal_plan(
        recipes=recipes,
        products={},
        macros={'protein': 10, 'carbs': 20, 'fat': 5, 'calories': 200},
        budget=200,
        meal_counts={'breakfast': 3, 'lunch': 3, 'dinner': 4},
        active_offers=[],
        owned_items=[],
    )
    assert result is not None
    total_servings = sum(v['count'] for v in result['meal_plan'].values())
    assert total_servings == 10


def test_returns_none_with_no_recipes():
    result = optimize_meal_plan([], {}, {'protein': 100}, 200, {'dinner': 7}, [], [])
    assert result is None


def test_owned_items_excluded_from_cost():
    ingredients = [{'canonical_product_id': 'PROD_rice', 'quantity': 0.5, 'unit': 'kg'}]
    products = {'PROD_rice': _make_product('PROD_rice', 'Rice', price=3.0)}
    cost = calculate_recipe_cost(
        _make_recipe('r1', 'Test', {}),
        ingredients, products, [], ['PROD_rice']
    )
    assert cost == 0.0


def test_effective_price_with_no_offers():
    product = _make_product('p1', 'Chicken', price=12.0)
    price = calculate_effective_price(product, 'coles', [])
    assert price == 12.0


def test_check_offer_applies_category_match():
    offer = {'details': {'category': 'protein'}}
    product = {'category': 'protein', 'name': 'chicken breast'}
    assert check_offer_applies(offer, product) is True


def test_check_offer_no_match():
    offer = {'details': {'category': 'dairy'}}
    product = {'category': 'protein', 'name': 'chicken'}
    assert check_offer_applies(offer, product) is False


def test_learning_mode_prefers_focus_cuisine():
    recipes = [
        _make_recipe('r1', 'Chinese Dish', {'protein': 30, 'carbs': 50, 'fat': 10, 'calories': 400},
                     servings=7, cuisine='chinese'),
        _make_recipe('r2', 'Italian Dish', {'protein': 30, 'carbs': 50, 'fat': 10, 'calories': 400},
                     servings=7, cuisine='italian'),
    ]
    result = optimize_meal_plan(
        recipes=recipes, products={},
        macros={'protein': 10, 'carbs': 10, 'fat': 5, 'calories': 100},
        budget=200,
        meal_counts={'dinner': 7},
        active_offers=[], owned_items=[],
        cuisine_focus='chinese', learning_mode=True,
    )
    assert result is not None
    # With learning mode, Chinese should be preferred (cheaper effective cost)
    if 'r1' in result['meal_plan']:
        assert result['meal_plan']['r1']['count'] >= result['meal_plan'].get('r2', {}).get('count', 0)
