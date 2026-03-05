"""Meal planner routes: form, generate, accept, shopping list."""

from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from models.settings import get_settings, get_owned_items
from models.recipe import search_recipes, get_recipe_ingredients
from models.product import get_all_products
from models.offer import get_active_offers
from models.meal_plan import save_plan, accept_plan, get_current_plan
from services.optimizer import optimize_meal_plan
from services.shopping_list import generate_from_meal_plan

planner_bp = Blueprint('planner', __name__)


@planner_bp.route('/')
def planner_form():
    store = current_app.store
    settings = get_settings(store)
    return render_template('planner.html', settings=settings)


@planner_bp.route('/generate', methods=['POST'])
def generate_plan():
    store = current_app.store
    settings = get_settings(store)

    budget = float(request.form.get('weekly_budget', settings['weekly_budget']))
    macros = {
        'protein': float(request.form.get('daily_protein', settings['daily_protein'])),
        'carbs': float(request.form.get('daily_carbs', settings['daily_carbs'])),
        'fat': float(request.form.get('daily_fat', settings['daily_fat'])),
        'calories': float(request.form.get('daily_calories', settings['daily_calories'])),
    }
    meal_counts = {
        'breakfast': int(request.form.get('breakfast', 7)),
        'lunch': int(request.form.get('lunch', 7)),
        'dinner': int(request.form.get('dinner', 7)),
    }
    cuisine_focus = request.form.get('cuisine_focus', '') or None
    learning_mode = request.form.get('learning_mode') == 'on'

    # Get all recipes and enrich with ingredients
    recipes = search_recipes(store, {})
    products_list = get_all_products(store)
    products = {p['id']: p for p in products_list}
    offers = get_active_offers(store)
    owned = get_owned_items(store)

    for r in recipes:
        r['_ingredients'] = get_recipe_ingredients(store, r['id'])

    result = optimize_meal_plan(
        recipes=recipes,
        products=products,
        macros=macros,
        budget=budget,
        meal_counts=meal_counts,
        active_offers=offers,
        owned_items=owned,
        cuisine_focus=cuisine_focus,
        learning_mode=learning_mode,
    )

    if result is None:
        flash('Could not find a feasible meal plan. Try increasing your budget or relaxing macro targets.')
        return redirect(url_for('planner.planner_form'))

    # Calculate week start (next Monday)
    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

    plan = save_plan(store, {
        'week_start': next_monday.isoformat(),
        'plan_data': result['meal_plan'],
        'total_cost': result['total_cost'],
        'macro_summary': result['macro_summary'],
        'shopping_list': result['shopping_list'],
        'savings_from_offers': result['savings_from_offers'],
    })

    return render_template('planner_results.html',
                           plan=plan,
                           macros=macros,
                           budget=budget)


@planner_bp.route('/accept/<int:plan_id>', methods=['POST'])
def accept_plan_route(plan_id):
    store = current_app.store
    accept_plan(store, plan_id)
    flash('Meal plan accepted! View your shopping list below.')
    return redirect(url_for('planner.shopping_list_view'))


@planner_bp.route('/shopping-list')
def shopping_list_view():
    store = current_app.store
    plan = get_current_plan(store)
    if not plan:
        flash('No meal plan found. Generate one first.')
        return redirect(url_for('planner.planner_form'))

    # Use pre-generated shopping list from plan, or regenerate
    shopping_list = plan.get('shopping_list', {})
    if not shopping_list and plan.get('plan_data'):
        owned = get_owned_items(store)
        shopping_list = generate_from_meal_plan(store, plan['plan_data'], owned)

    return render_template('shopping_list.html',
                           plan=plan,
                           shopping_list=shopping_list)
