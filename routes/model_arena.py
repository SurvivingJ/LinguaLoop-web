"""Model Arena blueprint — head-to-head OpenRouter model comparison."""

import json
import logging
import os
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

from services.task_runner import run_in_thread, is_task_stopped
from services.model_arena.pricing import fetch_model_list, get_pricing_map
from services.model_arena.arena_service import ArenaService
from services.model_arena.models import ArenaConfig

logger = logging.getLogger(__name__)

model_arena_bp = Blueprint('model_arena', __name__)

# task_id -> ArenaResults dict (kept in process for the dashboard to fetch)
ARENA_RESULTS: dict[str, dict] = {}

ARENA_RUNS_DIR = Path(__file__).resolve().parent.parent / 'data' / 'arena_runs'


@model_arena_bp.route('/api/models')
def list_openrouter_models():
    """Cached OpenRouter model catalogue for the dropdowns."""
    try:
        force = request.args.get('refresh') == '1'
        models = fetch_model_list(os.getenv('OPENROUTER_API_KEY'), force_refresh=force)
    except Exception as exc:
        logger.exception("Failed to fetch OpenRouter models: %s", exc)
        return jsonify({'error': str(exc), 'models': []}), 500

    simplified = []
    for m in models:
        pricing = m.get('pricing') or {}
        simplified.append({
            'id': m.get('id'),
            'name': m.get('name') or m.get('id'),
            'context_length': m.get('context_length', 0),
            'prompt_cost': pricing.get('prompt', '0'),
            'completion_cost': pricing.get('completion', '0'),
        })
    simplified.sort(key=lambda x: (x.get('id') or '').lower())
    return jsonify({'models': simplified})


@model_arena_bp.route('/api/run/arena', methods=['POST'])
def run_arena():
    body = request.get_json(force=True) or {}

    contestants = body.get('contestant_models') or []
    if not (2 <= len(contestants) <= 5):
        return jsonify({'error': 'Pick 2 to 5 contestant models'}), 400
    judge_model = body.get('judge_model')
    if not judge_model:
        return jsonify({'error': 'judge_model is required'}), 400
    if not body.get('language_id'):
        return jsonify({'error': 'language_id is required'}), 400
    gen_types = body.get('generation_types') or ['prose']
    valid_types = {'prose', 'questions'}
    gen_types = [g for g in gen_types if g in valid_types]
    if not gen_types:
        return jsonify({'error': 'generation_types must include prose or questions'}), 400

    num_trials = int(body.get('num_trials', 10))
    num_trials = max(1, min(50, num_trials))

    task_id = str(uuid.uuid4())
    run_in_thread(task_id, _do_arena_run, task_id, body, contestants, judge_model, gen_types, num_trials)
    return jsonify({'task_id': task_id}), 202


@model_arena_bp.route('/api/arena-results/<task_id>')
def get_arena_results(task_id: str):
    result = ARENA_RESULTS.get(task_id)
    if result is None:
        # Try filesystem
        path = ARENA_RUNS_DIR / f'{task_id}.json'
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return jsonify(json.load(f))
            except Exception as exc:
                return jsonify({'error': f'Failed to read saved run: {exc}'}), 500
        return jsonify({'error': 'Unknown task_id'}), 404
    return jsonify(result)


def _do_arena_run(task_id, body, contestants, judge_model, gen_types, num_trials):
    """Background task body — runs the arena and persists the result."""
    try:
        pricing = get_pricing_map(os.getenv('OPENROUTER_API_KEY'))
    except Exception as exc:
        logger.warning("Failed to fetch pricing — costs will be $0: %s", exc)
        pricing = {}

    config = ArenaConfig(
        language_id=int(body['language_id']),
        language_name=body.get('language_name', 'English'),
        language_code=body.get('language_code', 'en'),
        judge_model=judge_model,
        contestant_models=contestants,
        generation_types=gen_types,
        num_trials=num_trials,
        model_pricing=pricing,
    )

    service = ArenaService(config)
    results = service.run(stop_check=is_task_stopped)
    payload = results.to_dict()

    ARENA_RESULTS[task_id] = payload

    # Persist to disk for later review
    try:
        ARENA_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        with open(ARENA_RUNS_DIR / f'{task_id}.json', 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info("Arena run saved to %s", ARENA_RUNS_DIR / f'{task_id}.json')
    except Exception as exc:
        logger.warning("Failed to persist arena results: %s", exc)

    return payload
