"""Shopping list generation and store splitting."""

from models.product import get_all_products
from models.offer import get_active_offers
from models.recipe import get_recipe_ingredients
from models.price import get_cheapest_option, get_current_prices_all_stores
from services.optimizer import calculate_effective_price


def generate_from_meal_plan(store, meal_plan, owned_items):
    """Generate a store-split shopping list from an accepted meal plan.

    Args:
        store: CSVStore instance
        meal_plan: dict from meal_plan.plan_data (recipe_id -> {name, count, ...})
        owned_items: list of canonical product IDs to exclude
    """
    products_list = get_all_products(store)
    products = {p['id']: p for p in products_list}
    offers = get_active_offers(store)

    aggregated = aggregate_ingredients(store, meal_plan)
    store_grouped = assign_to_stores(store, aggregated, products, offers, owned_items)
    return format_for_display(store_grouped)


def aggregate_ingredients(store, meal_plan):
    """Sum quantities of each ingredient across all selected recipes."""
    totals = {}  # product_id -> {quantity, unit}

    for recipe_id, plan_info in meal_plan.items():
        count = plan_info.get('count', 1)
        ingredients = get_recipe_ingredients(store, recipe_id)

        for ing in ingredients:
            pid = ing['canonical_product_id']
            if not pid:
                continue
            qty = ing['quantity'] * count
            if pid in totals:
                totals[pid]['quantity'] += qty
            else:
                totals[pid] = {
                    'product_id': pid,
                    'quantity': qty,
                    'unit': ing['unit'],
                }

    return totals


def assign_to_stores(store, aggregated, products, offers, owned_items):
    """Assign each ingredient to the cheapest store."""
    store_lists = {}

    for pid, item in aggregated.items():
        if pid in owned_items:
            continue

        product = products.get(pid)
        if not product:
            continue

        # Get current prices
        prices = get_current_prices_all_stores(store, pid)
        if not prices:
            # No price data — add to generic list
            store_lists.setdefault('unknown', []).append({
                'product_id': pid,
                'product_name': product['name'],
                'quantity': item['quantity'],
                'unit': item['unit'],
                'base_price': 0,
                'effective_price': 0,
                'promotion_active': False,
            })
            continue

        # Find cheapest effective price
        best_store = None
        best_effective = float('inf')
        best_base = 0
        best_promo = False

        for store_name, price_info in prices.items():
            base = price_info['price']
            effective = calculate_effective_price(product, store_name, offers)
            if effective < best_effective:
                best_effective = effective
                best_store = store_name
                best_base = base
                best_promo = price_info.get('promotion_active', False)

        if best_store:
            store_lists.setdefault(best_store, []).append({
                'product_id': pid,
                'product_name': product['name'],
                'quantity': round(item['quantity'], 2),
                'unit': item['unit'],
                'base_price': round(best_base * item['quantity'], 2),
                'effective_price': round(best_effective * item['quantity'], 2),
                'promotion_active': best_promo,
            })

    return store_lists


def format_for_display(store_grouped):
    """Add display formatting: currency strings, store totals."""
    formatted = {}
    for store_name, items in store_grouped.items():
        store_total = sum(i['effective_price'] for i in items)
        base_total = sum(i['base_price'] for i in items)
        formatted[store_name] = {
            'items': items,
            'total': round(store_total, 2),
            'base_total': round(base_total, 2),
            'savings': round(base_total - store_total, 2),
            'item_count': len(items),
        }
    return formatted
