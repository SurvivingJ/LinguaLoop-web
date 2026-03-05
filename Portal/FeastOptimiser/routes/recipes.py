"""Recipe routes: browse, detail, create, complete/assess."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from models.recipe import search_recipes, get_recipe_ingredients, _parse_recipe
from models.product import get_product_by_id
from models.price import get_current_prices_all_stores
from models.progress import get_completion_count, insert_completion
from services.srs_engine import record_practice

recipes_bp = Blueprint('recipes', __name__)


@recipes_bp.route('/')
def recipe_list():
    store = current_app.store
    filters = {k: v for k, v in {
        'cuisine': request.args.get('cuisine', ''),
        'difficulty_max': request.args.get('difficulty_max', ''),
        'time_max': request.args.get('time_max', ''),
        'text_query': request.args.get('q', ''),
        'technique': request.args.get('technique', ''),
    }.items() if v}

    recipes = search_recipes(store, filters)

    # Get unique cuisines and techniques for filter bar
    all_recipes = search_recipes(store, {})
    cuisines = sorted(set(r['cuisine'] for r in all_recipes if r['cuisine']))
    techniques = sorted(set(t for r in all_recipes for t in r.get('techniques_taught', [])))

    return render_template('recipes.html',
                           recipes=recipes,
                           cuisines=cuisines,
                           techniques=techniques,
                           filters=request.args)


@recipes_bp.route('/<recipe_id>')
def recipe_detail(recipe_id):
    store = current_app.store
    results = store.query('recipes', id=recipe_id)
    if not results:
        flash('Recipe not found.')
        return redirect(url_for('recipes.recipe_list'))

    recipe = _parse_recipe(results[0])
    ingredients = get_recipe_ingredients(store, recipe_id)

    enriched_ingredients = []
    for ing in ingredients:
        product = get_product_by_id(store, ing['canonical_product_id'])
        prices = get_current_prices_all_stores(store, ing['canonical_product_id']) if ing['canonical_product_id'] else {}
        enriched_ingredients.append({
            **ing,
            'product_name': product['name'] if product else ing['canonical_product_id'],
            'prices': prices,
        })

    completion_count = get_completion_count(store, recipe_id)

    return render_template('recipe_detail.html',
                           recipe=recipe,
                           ingredients=enriched_ingredients,
                           completion_count=completion_count)


@recipes_bp.route('/<recipe_id>/complete')
def recipe_complete(recipe_id):
    store = current_app.store
    results = store.query('recipes', id=recipe_id)
    if not results:
        flash('Recipe not found.')
        return redirect(url_for('recipes.recipe_list'))

    recipe = _parse_recipe(results[0])
    return render_template('self_assessment.html', recipe=recipe)


@recipes_bp.route('/<recipe_id>/assess', methods=['POST'])
def recipe_submit_assessment(recipe_id):
    store = current_app.store
    results = store.query('recipes', id=recipe_id)
    if not results:
        flash('Recipe not found.')
        return redirect(url_for('recipes.recipe_list'))

    recipe = _parse_recipe(results[0])

    quality_ratings = {}
    srs_results = []
    for technique in recipe.get('techniques_taught', []):
        rating = int(request.form.get(f'rating_{technique}', 3))
        quality_ratings[technique] = rating
        result = record_practice(store, technique, rating, notes=request.form.get('notes', ''))
        srs_results.append({'technique': technique, 'rating': rating, **result})

    insert_completion(store, {
        'recipe_id': recipe_id,
        'cuisine': recipe['cuisine'],
        'quality_ratings': quality_ratings,
        'notes': request.form.get('notes', ''),
    })

    flash(f'Great job completing {recipe["name"]}!')
    return render_template('self_assessment.html',
                           recipe=recipe,
                           results=srs_results,
                           show_results=True)
