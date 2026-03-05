"""API routes: health, prices, products, techniques."""

from flask import Blueprint, jsonify, request, current_app

from models.product import get_all_products, get_product_by_id
from models.price import get_current_prices_all_stores, get_price_history
from services.srs_engine import calculate_mastery_percentage, calculate_retention_rate, get_effective_skill_level
from models.srs import get_card

api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health():
    return jsonify({'status': 'healthy'})


@api_bp.route('/prices/<product_id>')
def product_prices(product_id):
    store = current_app.store
    product = get_product_by_id(store, product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    prices = get_current_prices_all_stores(store, product_id)
    return jsonify({
        'product_id': product_id,
        'product_name': product['name'],
        'prices': prices,
    })


@api_bp.route('/prices/<product_id>/history')
def product_price_history(product_id):
    store = current_app.store
    days = int(request.args.get('days', 30))
    store_name = request.args.get('store')
    history = get_price_history(store, product_id, store_name=store_name, days=days)
    return jsonify({
        'product_id': product_id,
        'days': days,
        'history': history,
    })


@api_bp.route('/products/search')
def product_search():
    store = current_app.store
    query = request.args.get('query', '').lower()
    if not query or len(query) < 2:
        return jsonify([])

    products = get_all_products(store)
    matches = []
    for p in products:
        if query in p['name'].lower() or any(query in a.lower() for a in p.get('aliases', [])):
            matches.append({'id': p['id'], 'name': p['name'], 'category': p['category']})
            if len(matches) >= 10:
                break
    return jsonify(matches)


@api_bp.route('/techniques/<technique>')
def technique_detail(technique):
    store = current_app.store
    card = get_card(store, technique)
    if not card:
        return jsonify({
            'technique': technique,
            'mastery': 0,
            'retention': 0,
            'skill_level': {'base_level': 'novice', 'effective_score': 0},
            'history': [],
        })

    return jsonify({
        'technique': technique,
        'mastery': calculate_mastery_percentage(store, technique),
        'retention': calculate_retention_rate(store, technique),
        'skill_level': get_effective_skill_level(store, technique),
        'history': card.get('quality_history', []),
    })
