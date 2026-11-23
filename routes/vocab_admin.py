# routes/vocab_admin.py
"""Admin route for the vocabulary ladder — word preview (templates/admin_vocab_preview.html).

Upload, asset generation, rendering and wipe run from scripts/ and the ladder
services, not from HTTP routes."""

from flask import Blueprint
import logging

from middleware.auth import admin_required
from routes.common import get_db
from services.pinyin_format import display_pronunciation
from utils.responses import api_errors, ApiResponse, api_success
from utils.validation import require_language_id

logger = logging.getLogger(__name__)
vocab_admin_bp = Blueprint("vocab_admin", __name__)


@vocab_admin_bp.route('/word/<int:sense_id>/preview', methods=['GET'])
@admin_required
@api_errors("Failed to preview word")
@require_language_id
def preview_word(sense_id: int, language_id: int) -> ApiResponse:
    """Get visual preview data for a word's exercises (JSON API).

    Query params:
        language_id: required
    """
    db = get_db()

    # Fetch word data
    sense_resp = (
        db.table('dim_word_senses')
        .select('id, definition, pronunciation, ipa_pronunciation, '
                'morphological_forms, dim_vocabulary(lemma, semantic_class, '
                'part_of_speech, level_tag)')
        .eq('id', sense_id)
        .single()
        .execute()
    )
    sense_data = sense_resp.data or {}
    vocab = sense_data.get('dim_vocabulary') or {}

    # Fetch assets
    assets_resp = (
        db.table('word_assets')
        .select('asset_type, content, model_used, is_valid, validation_errors, '
                'prompt_version, created_at')
        .eq('sense_id', sense_id)
        .execute()
    )
    assets = {row['asset_type']: row for row in (assets_resp.data or [])}

    # Fetch exercises; content through the exercise-content store (ADR-049),
    # filled before the jumbled preparation below reads it.
    from services.exercise_content import store
    ex_resp = (
        db.table('exercises')
        .select(store.select_columns(
            'id, exercise_type, {content}, complexity_tier, ladder_level, word_sense_id'))
        .eq('word_sense_id', sense_id)
        .eq('language_id', language_id)
        .eq('is_active', True)
        .not_.is_('ladder_level', 'null')
        .order('ladder_level')
        .execute()
    )
    exercises = ex_resp.data or []
    store.hydrate(exercises, language_id=language_id)

    # Prepare jumbled content
    from services.exercise_generation.language_processor import (
        needs_jumbled_prep, prepare_jumbled_content,
    )
    for ex in exercises:
        if (ex.get('exercise_type') == 'jumbled_sentence'
                and needs_jumbled_prep(ex.get('content'))):
            try:
                ex['content'] = prepare_jumbled_content(ex['content'], language_id)
            except Exception:
                pass

    from services.vocabulary_ladder.config import LADDER_LEVELS, compute_active_levels
    active_levels = compute_active_levels(vocab.get('semantic_class', ''))

    return api_success({
        'word': {
            'sense_id': sense_id,
            'lemma': vocab.get('lemma', ''),
            'pos': vocab.get('part_of_speech', ''),
            'semantic_class': vocab.get('semantic_class', ''),
            'definition': sense_data.get('definition', ''),
            # as a learner sees it: Chinese tone-marked only (TASK-999); the
            # stored form stays visible in the raw asset JSON below
            'pronunciation': display_pronunciation(
                sense_data.get('pronunciation'), language_id=language_id),
            'ipa': sense_data.get('ipa_pronunciation', ''),
            'complexity_tier': vocab.get('level_tag', 'T3'),
            'morphological_forms': sense_data.get('morphological_forms'),
            'active_levels': active_levels,
        },
        'assets': assets,
        'exercises': exercises,
        'ladder_levels': {
            str(k): v for k, v in LADDER_LEVELS.items()
        },
    })
