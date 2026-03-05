"""Skill tree routes: cuisine overview, detail, practice recommendations."""

import json
import os
from flask import Blueprint, render_template, jsonify, current_app

from models.recipe import get_recipes_by_cuisine, get_recipes_by_tier
from models.progress import get_completed_recipes, get_technique_completion_count
from services.srs_engine import (
    calculate_mastery_percentage, calculate_retention_rate,
    get_due_techniques, get_effective_skill_level
)

skills_bp = Blueprint('skills', __name__)


def _load_skill_trees():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'data', 'cuisine_skill_trees.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


@skills_bp.route('/')
def skills_overview():
    store = current_app.store
    skill_trees = _load_skill_trees()

    cuisine_data = []
    for cuisine_key, cuisine in skill_trees.items():
        name = cuisine.get('name', cuisine_key.title())
        completions = get_completed_recipes(store, cuisine=cuisine_key)
        tiers = cuisine.get('tiers', {})
        if isinstance(tiers, dict):
            total_recipes = sum(len(t.get('recipes', [])) for t in tiers.values())
        else:
            total_recipes = sum(len(t.get('recipes', [])) for t in tiers)
        unique_completed = len(set(c['recipe_id'] for c in completions))

        all_techniques = cuisine.get('core_techniques', [])
        mastery_scores = [calculate_mastery_percentage(store, tech) for tech in all_techniques]
        avg_mastery = sum(mastery_scores) / len(mastery_scores) if mastery_scores else 0

        cuisine_data.append({
            'name': name,
            'key': cuisine_key,
            'description': cuisine.get('description', ''),
            'total_recipes': total_recipes,
            'completed_recipes': unique_completed,
            'progress_percent': round(unique_completed / total_recipes * 100) if total_recipes else 0,
            'avg_mastery': round(avg_mastery, 1),
            'core_techniques': all_techniques,
        })

    return render_template('skills.html', cuisines=cuisine_data)


@skills_bp.route('/<cuisine>')
def cuisine_detail(cuisine):
    store = current_app.store
    skill_trees = _load_skill_trees()

    tree = skill_trees.get(cuisine.lower())
    if not tree:
        return render_template('skills.html', cuisines=[], error=f'Cuisine "{cuisine}" not found.')

    completions = get_completed_recipes(store, cuisine=cuisine.lower())
    completed_ids = set(c['recipe_id'] for c in completions)

    tiers = tree.get('tiers', {})
    tiers_data = []
    tier_items = tiers.items() if isinstance(tiers, dict) else enumerate(tiers)
    for tier_key, tier in tier_items:
        tier_name = tier_key if isinstance(tier_key, str) else tier.get('name', str(tier_key))
        tier_recipes = get_recipes_by_tier(store, cuisine.lower(), tier_name)
        recipe_list = []
        for r in tier_recipes:
            recipe_list.append({
                **r,
                'completed': r['id'] in completed_ids,
                'completion_count': sum(1 for c in completions if c['recipe_id'] == r['id']),
            })

        tiers_data.append({
            'name': tier_name,
            'unlock_requirements': tier.get('unlock_requirements', ''),
            'recipes': recipe_list,
            'completed_count': sum(1 for r in recipe_list if r['completed']),
            'total_count': len(recipe_list),
        })

    technique_data = []
    for tech in tree.get('core_techniques', []):
        skill = get_effective_skill_level(store, tech)
        mastery = calculate_mastery_percentage(store, tech)
        retention = calculate_retention_rate(store, tech)
        technique_data.append({
            'name': tech,
            'display_name': tech.replace('_', ' ').title(),
            'mastery': mastery,
            'retention': retention,
            'level': skill['base_level'],
            'needs_practice': skill['needs_practice'],
        })

    return render_template('skills.html',
                           detail_mode=True,
                           cuisine_name=tree.get('name', cuisine.title()),
                           cuisine_description=tree.get('description', ''),
                           tiers=tiers_data,
                           techniques=technique_data)


@skills_bp.route('/practice-recommendations')
def practice_recommendations():
    store = current_app.store
    due = get_due_techniques(store, limit=10)
    return jsonify(due)
