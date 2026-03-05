"""Wishlist routes: view, add, detail, mark purchased."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from models.wishlist import get_active_wishlist, get_upcoming_gifts, upsert_wishlist_item, mark_purchased
from services.wishlist_tracker import calculate_price_trends

wishlist_bp = Blueprint('wishlist', __name__)


@wishlist_bp.route('/')
def wishlist_view():
    store = current_app.store
    items = get_active_wishlist(store)
    gifts = get_upcoming_gifts(store)
    return render_template('wishlist.html', items=items, gifts=gifts)


@wishlist_bp.route('/add', methods=['POST'])
def wishlist_add():
    store = current_app.store
    stores = request.form.getlist('stores_to_track') or ['coles', 'woolworths']
    item = {
        'product_name': request.form['product_name'],
        'category': request.form.get('category', 'grocery_staple'),
        'target_price': request.form.get('target_price') or None,
        'alert_threshold_percent': request.form.get('alert_threshold_percent', 10),
        'baseline_price': request.form.get('baseline_price') or None,
        'stores_to_track': stores,
        'priority': request.form.get('priority', 'medium'),
        'recipient': request.form.get('recipient') or None,
        'occasion': request.form.get('occasion') or None,
        'occasion_date': request.form.get('occasion_date') or None,
    }
    upsert_wishlist_item(store, item)
    flash(f'Added "{item["product_name"]}" to wishlist.')
    return redirect(url_for('wishlist.wishlist_view'))


@wishlist_bp.route('/<int:item_id>')
def wishlist_item_detail(item_id):
    store = current_app.store
    items = get_active_wishlist(store)
    item = next((i for i in items if i['id'] == item_id), None)
    if not item:
        flash('Wishlist item not found.')
        return redirect(url_for('wishlist.wishlist_view'))

    trends = calculate_price_trends(store, item_id) if item.get('product_id') else None
    return render_template('wishlist.html',
                           items=get_active_wishlist(store),
                           gifts=get_upcoming_gifts(store),
                           detail_item=item,
                           trends=trends)


@wishlist_bp.route('/<int:item_id>/purchased', methods=['POST'])
def wishlist_mark_purchased(item_id):
    store = current_app.store
    mark_purchased(store, item_id)
    flash('Item marked as purchased.')
    return redirect(url_for('wishlist.wishlist_view'))
