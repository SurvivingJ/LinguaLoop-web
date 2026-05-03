# routes/vocab_admin.py
"""Admin routes for vocabulary ladder — word upload, asset generation, preview."""

from flask import Blueprint, request, render_template
import logging

from utils.responses import ApiResponse, api_success, bad_request, server_error

logger = logging.getLogger(__name__)
vocab_admin_bp = Blueprint("vocab_admin", __name__)


@vocab_admin_bp.route('/upload-words', methods=['POST'])
def upload_words() -> ApiResponse:
    """Upload a word list and trigger asset generation.

    Body (JSON):
        language_id: required (int)
        words: required, list of dicts with at least 'lemma' key.
            Optional keys: definition, pos, complexity_tier.

    The endpoint:
    1. Upserts words into dim_vocabulary + dim_word_senses
    2. Triggers the asset pipeline for each sense
    3. Renders exercises from generated assets
    4. Returns a batch summary
    """
    try:
        data = request.get_json()
        if not data:
            return bad_request("Request body required")

        language_id = data.get('language_id')
        words = data.get('words', [])

        if not language_id or not words:
            return bad_request("language_id and words[] required")

        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        # Step 1: Upsert words into dim_vocabulary + dim_word_senses
        sense_ids = []
        for word_data in words:
            lemma = word_data.get('lemma', '').strip()
            if not lemma:
                continue

            sense_id = _upsert_word(
                db, language_id, lemma,
                definition=word_data.get('definition', ''),
                pos=word_data.get('pos'),
                complexity_tier=word_data.get('complexity_tier', 'T3'),
            )
            if sense_id:
                sense_ids.append(sense_id)

        if not sense_ids:
            return bad_request("No valid words to process")

        # Step 2: Run asset pipeline
        from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
        pipeline = VocabAssetPipeline(db)
        pipeline_result = pipeline.generate_batch(sense_ids, language_id)

        # Step 3: Render exercises for successfully generated assets
        from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer
        renderer = LadderExerciseRenderer(db)

        rendered_count = 0
        for sense_id in sense_ids:
            try:
                exercise_ids = renderer.render_all(sense_id, language_id)
                rendered_count += len(exercise_ids)
            except Exception as e:
                logger.error("Exercise rendering failed for sense %s: %s", sense_id, e)

        pipeline_result['exercises_rendered'] = rendered_count
        return api_success(pipeline_result)

    except Exception as e:
        logger.error("Word upload failed: %s", e)
        return server_error("Failed to upload words")


@vocab_admin_bp.route('/generate-assets', methods=['POST'])
def generate_assets() -> ApiResponse:
    """Trigger asset generation for specific sense IDs.

    Body:
        language_id: required
        sense_ids: required (list of ints)
        force: optional (bool, default false — regenerate even if exists)
    """
    try:
        data = request.get_json()
        if not data:
            return bad_request("Request body required")

        language_id = data.get('language_id')
        sense_ids = data.get('sense_ids', [])
        force = bool(data.get('force', False))

        if not language_id or not sense_ids:
            return bad_request("language_id and sense_ids[] required")

        from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        pipeline = VocabAssetPipeline(db)
        result = pipeline.generate_batch(sense_ids, language_id, force=force)

        return api_success(result)

    except Exception as e:
        logger.error("Asset generation failed: %s", e)
        return server_error("Failed to generate assets")


@vocab_admin_bp.route('/render-exercises', methods=['POST'])
def render_exercises() -> ApiResponse:
    """Render exercises from existing word_assets for specific senses.

    Body:
        language_id: required
        sense_ids: required (list of ints)
    """
    try:
        data = request.get_json()
        if not data:
            return bad_request("Request body required")

        language_id = data.get('language_id')
        sense_ids = data.get('sense_ids', [])

        if not language_id or not sense_ids:
            return bad_request("language_id and sense_ids[] required")

        from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer
        from services.supabase_factory import get_supabase_admin

        renderer = LadderExerciseRenderer(get_supabase_admin())
        total = 0
        for sense_id in sense_ids:
            ids = renderer.render_all(sense_id, language_id)
            total += len(ids)

        return api_success({
            'senses_processed': len(sense_ids),
            'exercises_rendered': total,
        })

    except Exception as e:
        logger.error("Exercise rendering failed: %s", e)
        return server_error("Failed to render exercises")


@vocab_admin_bp.route('/words', methods=['GET'])
def list_words() -> ApiResponse:
    """List words with their asset generation status.

    Query params:
        language_id: required
        limit: optional (default 50)
        offset: optional (default 0)
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        limit = min(request.args.get('limit', 50, type=int), 200)
        offset = request.args.get('offset', 0, type=int)

        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        # Fetch words with senses
        resp = (
            db.table('dim_word_senses')
            .select('id, definition, pronunciation, '
                    'dim_vocabulary!inner(id, lemma, part_of_speech, semantic_class, '
                    'language_id)')
            .eq('dim_vocabulary.language_id', language_id)
            .order('id', desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        senses = resp.data or []

        # Batch check which senses have assets
        sense_ids = [s['id'] for s in senses]
        asset_map = {}
        if sense_ids:
            asset_resp = (
                db.table('word_assets')
                .select('sense_id, asset_type, is_valid')
                .in_('sense_id', sense_ids)
                .execute()
            )
            for row in (asset_resp.data or []):
                sid = row['sense_id']
                if sid not in asset_map:
                    asset_map[sid] = {}
                asset_map[sid][row['asset_type']] = row['is_valid']

        # Batch check which senses have ladder exercises (count + levels)
        exercise_count_map = {}
        exercise_levels_map: dict[int, list[int]] = {}
        if sense_ids:
            ex_resp = (
                db.table('exercises')
                .select('word_sense_id, ladder_level')
                .in_('word_sense_id', sense_ids)
                .not_.is_('ladder_level', 'null')
                .eq('is_active', True)
                .execute()
            )
            for row in (ex_resp.data or []):
                sid = row['word_sense_id']
                exercise_count_map[sid] = exercise_count_map.get(sid, 0) + 1
                exercise_levels_map.setdefault(sid, []).append(row['ladder_level'])
            for sid in exercise_levels_map:
                exercise_levels_map[sid] = sorted(set(exercise_levels_map[sid]))

        # Build response
        words = []
        for s in senses:
            vocab = s.get('dim_vocabulary') or {}
            sid = s['id']
            assets = asset_map.get(sid, {})
            words.append({
                'sense_id': sid,
                'lemma': vocab.get('lemma', ''),
                'pos': vocab.get('part_of_speech', ''),
                'semantic_class': vocab.get('semantic_class', ''),
                'definition': s.get('definition', ''),
                'has_prompt1': assets.get('prompt1_core', False),
                'has_prompt2': assets.get('prompt2_exercises', False),
                'has_prompt3': assets.get('prompt3_transforms', False),
                'exercise_count': exercise_count_map.get(sid, 0),
                'levels': exercise_levels_map.get(sid, []),
            })

        return api_success({'words': words, 'count': len(words)})

    except Exception as e:
        logger.error("Error listing words: %s", e)
        return server_error("Failed to list words")


@vocab_admin_bp.route('/word/<int:sense_id>/wipe', methods=['POST'])
def wipe_word(sense_id: int) -> ApiResponse:
    """Hard-delete word_assets and exercises for a sense — used before regenerate."""
    try:
        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        ex_resp = db.table('exercises').delete().eq('word_sense_id', sense_id).execute()
        as_resp = db.table('word_assets').delete().eq('sense_id', sense_id).execute()

        return api_success({
            'sense_id': sense_id,
            'exercises_deleted': len(ex_resp.data or []),
            'assets_deleted': len(as_resp.data or []),
        })
    except Exception as e:
        logger.error("Wipe failed for sense %s: %s", sense_id, e)
        return server_error("Failed to wipe word")


@vocab_admin_bp.route('/word/<int:sense_id>/level/<int:level>', methods=['DELETE'])
def remove_level(sense_id: int, level: int) -> ApiResponse:
    """Soft-delete exercises at one ladder level for one sense."""
    try:
        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        resp = (
            db.table('exercises')
            .update({'is_active': False})
            .eq('word_sense_id', sense_id)
            .eq('ladder_level', level)
            .execute()
        )
        return api_success({
            'sense_id': sense_id,
            'level': level,
            'removed': len(resp.data or []),
        })
    except Exception as e:
        logger.error("Remove level %s for sense %s failed: %s", level, sense_id, e)
        return server_error("Failed to remove level")


@vocab_admin_bp.route('/word/<int:sense_id>/preview', methods=['GET'])
def preview_word(sense_id: int) -> ApiResponse:
    """Get visual preview data for a word's exercises (JSON API).

    Query params:
        language_id: required
    """
    try:
        language_id = request.args.get('language_id', type=int)
        if not language_id:
            return bad_request("language_id required")

        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

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

        # Fetch exercises
        ex_resp = (
            db.table('exercises')
            .select('id, exercise_type, content, complexity_tier, ladder_level')
            .eq('word_sense_id', sense_id)
            .eq('language_id', language_id)
            .eq('is_active', True)
            .not_.is_('ladder_level', 'null')
            .order('ladder_level')
            .execute()
        )
        exercises = ex_resp.data or []

        # Prepare jumbled content
        from services.exercise_generation.language_processor import prepare_jumbled_content
        for ex in exercises:
            if (ex.get('exercise_type') == 'jumbled_sentence'
                    and isinstance(ex.get('content'), dict)
                    and 'chunks' not in ex['content']):
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
                'pronunciation': sense_data.get('pronunciation', ''),
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

    except Exception as e:
        logger.error("Error previewing word %s: %s", sense_id, e)
        return server_error("Failed to preview word")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upsert_word(
    db, language_id: int, lemma: str,
    definition: str = '', pos: str | None = None,
    complexity_tier: str = 'T3',
) -> int | None:
    """Upsert a word into dim_vocabulary + dim_word_senses. Returns sense_id."""
    try:
        # Check if vocab entry exists
        existing = (
            db.table('dim_vocabulary')
            .select('id')
            .eq('language_id', language_id)
            .eq('lemma', lemma)
            .execute()
        )

        if existing.data:
            vocab_id = existing.data[0]['id']
            if pos:
                db.table('dim_vocabulary').update(
                    {'part_of_speech': pos}
                ).eq('id', vocab_id).execute()
        else:
            insert_resp = db.table('dim_vocabulary').insert({
                'language_id': language_id,
                'lemma': lemma,
                'part_of_speech': pos or 'unknown',
                'level_tag': complexity_tier,
            }).execute()
            vocab_id = insert_resp.data[0]['id']

        # Check if sense exists
        sense_existing = (
            db.table('dim_word_senses')
            .select('id')
            .eq('vocab_id', vocab_id)
            .eq('definition_language_id', language_id)
            .execute()
        )

        if sense_existing.data:
            sense_id = sense_existing.data[0]['id']
            if definition:
                db.table('dim_word_senses').update(
                    {'definition': definition}
                ).eq('id', sense_id).execute()
        else:
            sense_resp = db.table('dim_word_senses').insert({
                'vocab_id': vocab_id,
                'definition_language_id': language_id,
                'definition': definition or f'Definition for {lemma}',
                'sense_rank': 1,
            }).execute()
            sense_id = sense_resp.data[0]['id']

        return sense_id

    except Exception as e:
        logger.error("Failed to upsert word '%s': %s", lemma, e)
        return None
