# routes/conversations.py
"""Conversation reader routes — browse and read generated conversations."""

from flask import Blueprint, request
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from utils.responses import ApiResponse, api_success, bad_request, not_found, server_error
from services.supabase_factory import get_supabase_admin
from services.dimension_service import parse_language_id

logger = logging.getLogger(__name__)
conversations_bp = Blueprint("conversations", __name__)


@conversations_bp.route('/', methods=['GET'])
@supabase_jwt_required
def list_conversations() -> ApiResponse:
    """List conversations with optional filters.

    Query params: language_id (required), cefr_level (optional), limit, offset
    """
    try:
        language_id = parse_language_id(request.args.get('language_id'))
        if not language_id:
            return bad_request("language_id required")

        cefr_level = request.args.get('cefr_level')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        client = get_supabase_admin()

        query = client.table('conversations').select(
            'id, turn_count, quality_score, passed_qc, created_at, '
            'scenarios(title, context_description, cefr_level, conversation_domains(domain_name)), '
            'persona_pairs(relationship_type, dynamic_label, '
            'persona_a:personas!persona_pairs_persona_a_id_fkey(name, archetype), '
            'persona_b:personas!persona_pairs_persona_b_id_fkey(name, archetype))'
        ).eq('language_id', language_id).eq('is_active', True)

        if cefr_level:
            query = query.eq('scenarios.cefr_level', cefr_level)

        response = query.order('created_at', desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        return api_success({'conversations': response.data or []})

    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return server_error("Failed to fetch conversations")


@conversations_bp.route('/<conversation_id>', methods=['GET'])
@supabase_jwt_required
def get_conversation(conversation_id: str) -> ApiResponse:
    """Get a single conversation with full turns."""
    try:
        client = get_supabase_admin()

        response = client.table('conversations').select(
            'id, turn_count, quality_score, passed_qc, turns, corpus_features, '
            'model_used, temperature, created_at, '
            'scenarios(title, context_description, cefr_level, keywords, '
            'conversation_domains(domain_name)), '
            'persona_pairs(relationship_type, dynamic_label, '
            'persona_a:personas!persona_pairs_persona_a_id_fkey(id, name, archetype, occupation, personality), '
            'persona_b:personas!persona_pairs_persona_b_id_fkey(id, name, archetype, occupation, personality))'
        ).eq('id', conversation_id).eq('is_active', True).single().execute()

        if not response.data:
            return not_found("Conversation not found")

        # Map persona_id in turns to persona names for easy rendering
        conv = response.data
        pair = conv.get('persona_pairs') or {}
        persona_a = pair.get('persona_a') or {}
        persona_b = pair.get('persona_b') or {}

        persona_map = {}
        if persona_a.get('id'):
            persona_map[persona_a['id']] = persona_a['name']
        if persona_b.get('id'):
            persona_map[persona_b['id']] = persona_b['name']

        if conv.get('turns'):
            for turn in conv['turns']:
                pid = turn.get('persona_id')
                if pid and pid in persona_map:
                    turn['speaker_name'] = persona_map[pid]

        return api_success({'conversation': conv})

    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {e}")
        return server_error("Failed to fetch conversation")
