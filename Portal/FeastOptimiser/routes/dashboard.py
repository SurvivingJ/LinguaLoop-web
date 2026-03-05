"""Dashboard route: aggregated overview of all sections."""

from flask import Blueprint, render_template, current_app

from models.settings import get_settings
from models.meal_plan import get_current_plan
from models.progress import get_completed_recipes
from models.wishlist import get_active_wishlist, get_upcoming_gifts
from services.srs_engine import get_due_techniques

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def dashboard_view():
    store = current_app.store
    settings = get_settings(store)

    # Current plan
    plan = get_current_plan(store)
    budget_remaining = settings['weekly_budget'] - (plan['total_cost'] if plan else 0)

    # Progress stats
    completions = get_completed_recipes(store)
    unique_recipes = len(set(c['recipe_id'] for c in completions))

    # Cuisine progress
    cuisine_progress = {}
    for c in completions:
        cuisine = c.get('cuisine', 'unknown')
        cuisine_progress.setdefault(cuisine, set()).add(c['recipe_id'])
    cuisine_progress = {k: len(v) for k, v in cuisine_progress.items()}

    # Due techniques
    due_techniques = get_due_techniques(store, limit=5)

    # Wishlist
    wishlist_items = get_active_wishlist(store)
    deals = [i for i in wishlist_items if i.get('current_best_price') and i.get('target_price')
             and i['current_best_price'] <= i['target_price']]
    gifts = get_upcoming_gifts(store, days=30)

    return render_template('dashboard.html',
                           settings=settings,
                           plan=plan,
                           budget_remaining=round(budget_remaining, 2),
                           total_completions=len(completions),
                           unique_recipes=unique_recipes,
                           cuisine_progress=cuisine_progress,
                           due_techniques=due_techniques,
                           deals=deals,
                           gifts=gifts)
