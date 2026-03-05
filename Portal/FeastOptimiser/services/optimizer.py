"""Meal plan optimization using PuLP linear programming."""

import logging
from pulp import LpProblem, LpMinimize, LpVariable, LpInteger, lpSum, value, LpStatus

from services.offer_parser import calculate_offer_value

logger = logging.getLogger(__name__)


def optimize_meal_plan(recipes, products, macros, budget, meal_counts,
                       active_offers, owned_items, cuisine_focus=None,
                       learning_mode=False):
    """Core optimization: find cheapest meal plan meeting macro and budget constraints.

    Args:
        recipes: list of recipe dicts (with macros_per_serving populated)
        products: dict mapping product_id -> product dict
        macros: daily targets dict {protein, carbs, fat, calories}
        budget: float, maximum weekly spend
        meal_counts: dict {breakfast: int, lunch: int, dinner: int}
        active_offers: list of offer dicts
        owned_items: list of canonical product IDs to exclude from cost
        cuisine_focus: str or None, cuisine to weight higher
        learning_mode: bool, apply learning bonus to cuisine-focus recipes

    Returns:
        dict {meal_plan, total_cost, macro_summary, shopping_list, savings_from_offers}
        or None if no feasible plan found
    """
    if not recipes:
        return None

    # Pre-calculate cost per serving for each recipe
    recipe_costs = {}
    recipe_ingredients = {}
    for r in recipes:
        ingredients = r.get('_ingredients', [])
        cost = calculate_recipe_cost(r, ingredients, products, active_offers, owned_items)
        servings = max(r.get('servings', 4), 1)
        recipe_costs[r['id']] = cost / servings
        recipe_ingredients[r['id']] = ingredients

    total_meals = sum(meal_counts.values())
    if total_meals == 0:
        return None

    # Set up LP problem
    prob = LpProblem("MealPlan", LpMinimize)

    # Decision variables: how many servings of each recipe to include
    # Cap per recipe to encourage variety, but ensure feasibility
    n_recipes = len(recipes)
    if n_recipes >= 6:
        max_per_recipe = max(total_meals // 3, 2)
    else:
        # Few recipes available — allow enough to fill all slots
        max_per_recipe = total_meals
    recipe_vars = {}
    for r in recipes:
        recipe_vars[r['id']] = LpVariable(f"r_{r['id']}", 0, max_per_recipe, cat=LpInteger)

    # Effective costs (with learning mode adjustment)
    effective_costs = dict(recipe_costs)
    if learning_mode and cuisine_focus:
        for r in recipes:
            if r.get('cuisine') == cuisine_focus:
                effective_costs[r['id']] *= 0.8

    # Slack variables for macro shortfalls (soft constraints)
    # Penalize missing macros rather than making them hard constraints
    macro_slack = {}
    macro_penalty_weights = {'protein': 0.5, 'carbs': 0.1, 'fat': 0.2, 'calories': 0.01}
    for macro in ['protein', 'carbs', 'fat', 'calories']:
        if macros.get(macro):
            weekly_target = macros[macro] * 7
            macro_slack[macro] = LpVariable(f"slack_{macro}", 0, weekly_target)

    # Objective: minimize cost + penalty for macro shortfalls
    cost_expr = lpSum(recipe_vars[r['id']] * effective_costs[r['id']] for r in recipes)
    penalty_expr = lpSum(
        macro_slack[macro] * macro_penalty_weights.get(macro, 0.1)
        for macro in macro_slack
    )
    prob += cost_expr + penalty_expr

    # Constraint: total servings = total meals requested
    prob += lpSum(recipe_vars[r['id']] for r in recipes) == total_meals

    # Soft macro constraints: actual + slack >= target
    for macro in ['protein', 'carbs', 'fat', 'calories']:
        if macros.get(macro) and macro in macro_slack:
            prob += (
                lpSum(
                    recipe_vars[r['id']] * r.get('macros_per_serving', {}).get(macro, 0)
                    for r in recipes
                ) + macro_slack[macro] >= macros[macro] * 7
            )

    # Constraint: total actual cost <= budget (only if any recipes have cost)
    if any(recipe_costs[r['id']] > 0 for r in recipes):
        prob += lpSum(recipe_vars[r['id']] * recipe_costs[r['id']] for r in recipes) <= budget

    # Solve (suppress verbose CBC output)
    from pulp import PULP_CBC_CMD
    prob.solve(PULP_CBC_CMD(msg=0))

    if LpStatus[prob.status] != 'Optimal':
        logger.warning(f"Optimization status: {LpStatus[prob.status]}")
        return None

    # Extract solution
    selected = {}
    for r in recipes:
        count = int(value(recipe_vars[r['id']]) or 0)
        if count > 0:
            selected[r['id']] = {
                'recipe': r,
                'count': count,
                'cost_per_serving': recipe_costs[r['id']],
                'total_cost': recipe_costs[r['id']] * count,
            }

    # Calculate totals
    total_cost = sum(s['total_cost'] for s in selected.values())
    total_cost_with_offers = sum(
        effective_costs[rid] * s['count'] for rid, s in selected.items()
    )
    savings = total_cost - total_cost_with_offers if learning_mode else 0

    # Macro summary
    macro_summary = {'protein': 0, 'carbs': 0, 'fat': 0, 'calories': 0, 'fiber': 0}
    for rid, s in selected.items():
        for macro in macro_summary:
            macro_summary[macro] += s['recipe'].get('macros_per_serving', {}).get(macro, 0) * s['count']
    macro_summary = {k: round(v, 1) for k, v in macro_summary.items()}

    # Generate shopping list
    shopping_list = generate_shopping_list(selected, products, active_offers, owned_items)

    return {
        'meal_plan': {rid: {'name': s['recipe']['name'], 'count': s['count'],
                            'cost': round(s['total_cost'], 2),
                            'cuisine': s['recipe'].get('cuisine', '')}
                      for rid, s in selected.items()},
        'total_cost': round(total_cost, 2),
        'macro_summary': macro_summary,
        'shopping_list': shopping_list,
        'savings_from_offers': round(savings, 2),
    }


def calculate_recipe_cost(recipe, ingredients, products, active_offers, owned_items):
    """Calculate total cost for a recipe after offer adjustments."""
    total = 0.0
    for ing in ingredients:
        prod_id = ing.get('canonical_product_id', '')
        if prod_id in owned_items:
            continue
        product = products.get(prod_id)
        if not product:
            continue

        # Find cheapest store
        cheapest_price = None
        for store_name in ['coles', 'woolworths', 'aldi']:
            store_info = product.get('store_mappings', {}).get(store_name)
            if not store_info:
                continue
            base_price = store_info.get('current_price', 0)
            if base_price:
                effective = calculate_effective_price(product, store_name, active_offers)
                if cheapest_price is None or effective < cheapest_price:
                    cheapest_price = effective

        if cheapest_price:
            quantity = float(ing.get('quantity', 1))
            total += cheapest_price * quantity

    return total


def calculate_effective_price(product, store_name, active_offers):
    """Calculate price after loyalty offer adjustments."""
    store_info = product.get('store_mappings', {}).get(store_name, {})
    base_price = store_info.get('current_price', 0)
    if not base_price:
        return float('inf')

    for offer in active_offers:
        if check_offer_applies(offer, product):
            discount = calculate_offer_value(offer, base_price)
            base_price -= discount

    return max(base_price, 0)


def check_offer_applies(offer, product):
    """Check if an offer applies to a product."""
    details = offer.get('details', {})
    offer_category = details.get('category', '').lower()
    product_category = product.get('category', '').lower()
    product_name = product.get('name', '').lower()

    if not offer_category:
        return False

    # Category match
    if offer_category in product_category:
        return True
    # Name substring match
    if offer_category in product_name:
        return True

    return False


def generate_shopping_list(selected_recipes, products, active_offers, owned_items):
    """Aggregate ingredients from selected recipes into store-grouped shopping list."""
    # Aggregate all ingredients
    aggregated = {}  # product_id -> total quantity
    for rid, selection in selected_recipes.items():
        recipe = selection['recipe']
        count = selection['count']
        for ing in recipe.get('_ingredients', []):
            pid = ing.get('canonical_product_id', '')
            if not pid or pid in owned_items:
                continue
            qty = float(ing.get('quantity', 0)) * count
            if pid in aggregated:
                aggregated[pid]['quantity'] += qty
            else:
                aggregated[pid] = {
                    'product_id': pid,
                    'quantity': qty,
                    'unit': ing.get('unit', ''),
                }

    # Assign to cheapest store
    store_lists = {}
    for pid, item in aggregated.items():
        product = products.get(pid)
        if not product:
            continue

        best_store = None
        best_price = float('inf')
        for store_name in ['coles', 'woolworths', 'aldi']:
            store_info = product.get('store_mappings', {}).get(store_name)
            if store_info and store_info.get('current_price'):
                eff_price = calculate_effective_price(product, store_name, active_offers)
                if eff_price < best_price:
                    best_price = eff_price
                    best_store = store_name

        if best_store:
            if best_store not in store_lists:
                store_lists[best_store] = []
            store_lists[best_store].append({
                'product_id': pid,
                'product_name': product['name'],
                'quantity': round(item['quantity'], 2),
                'unit': item['unit'],
                'price': round(best_price * item['quantity'], 2),
            })

    return store_lists
