"""Settings routes: macros, budget, pantry, offers, theme."""

import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app

from models.settings import get_settings, update_settings
from models.offer import get_active_offers, insert_offers
from models.product import get_all_products
from services.offer_parser import extract_offers_from_screenshots

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/')
def settings_view():
    store = current_app.store
    settings = get_settings(store)
    offers = get_active_offers(store)
    products = get_all_products(store)

    # Group products by category for owned items selector
    categories = {}
    for p in products:
        cat = p.get('category', 'Other')
        categories.setdefault(cat, []).append(p)

    return render_template('settings.html',
                           settings=settings,
                           offers=offers,
                           product_categories=categories,
                           all_products=products)


@settings_bp.route('/macros', methods=['POST'])
def save_macros():
    store = current_app.store
    update_settings(store, {
        'daily_protein': request.form.get('daily_protein', 120),
        'daily_carbs': request.form.get('daily_carbs', 250),
        'daily_fat': request.form.get('daily_fat', 65),
        'daily_calories': request.form.get('daily_calories', 2200),
    })
    flash('Macro targets updated.')
    return redirect(url_for('settings.settings_view'))


@settings_bp.route('/budget', methods=['POST'])
def save_budget():
    store = current_app.store
    update_settings(store, {
        'weekly_budget': request.form.get('weekly_budget', 150),
    })
    flash('Weekly budget updated.')
    return redirect(url_for('settings.settings_view'))


@settings_bp.route('/owned-items', methods=['POST'])
def save_owned_items():
    store = current_app.store
    items = request.form.getlist('owned_items')
    update_settings(store, {'owned_items': items})
    flash('Pantry items updated.')
    return redirect(url_for('settings.settings_view'))


@settings_bp.route('/cuisine-preferences', methods=['POST'])
def save_cuisine_preferences():
    store = current_app.store
    cuisines = request.form.getlist('cuisine_preferences')
    update_settings(store, {'cuisine_preferences': cuisines})
    flash('Cuisine preferences updated.')
    return redirect(url_for('settings.settings_view'))


@settings_bp.route('/upload-offers', methods=['POST'])
def upload_offers():
    store = current_app.store
    files = request.files.getlist('screenshots')
    if not files or not files[0].filename:
        flash('No screenshots uploaded.')
        return redirect(url_for('settings.settings_view'))

    offers = extract_offers_from_screenshots(files)
    if not offers:
        flash('No offers could be extracted from the screenshots.')
        return redirect(url_for('settings.settings_view'))

    # Store parsed offers in session for confirmation
    return render_template('settings.html',
                           settings=get_settings(store),
                           offers=get_active_offers(store),
                           product_categories={},
                           all_products=get_all_products(store),
                           pending_offers=offers)


@settings_bp.route('/confirm-offers', methods=['POST'])
def confirm_offers():
    store = current_app.store
    offers_json = request.form.get('offers_data', '[]')
    try:
        offers = json.loads(offers_json)
    except json.JSONDecodeError:
        flash('Invalid offer data.')
        return redirect(url_for('settings.settings_view'))

    if offers:
        insert_offers(store, offers)
        flash(f'{len(offers)} offers added.')
    return redirect(url_for('settings.settings_view'))


@settings_bp.route('/theme', methods=['POST'])
def save_theme():
    store = current_app.store
    theme = request.json.get('theme', 'bauhaus') if request.is_json else request.form.get('theme', 'bauhaus')
    update_settings(store, {'theme': theme})
    if request.is_json:
        return jsonify({'status': 'ok', 'theme': theme})
    flash('Theme updated.')
    return redirect(url_for('settings.settings_view'))
