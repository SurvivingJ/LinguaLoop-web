from flask import Blueprint, request, jsonify, g
from middleware.auth import jwt_required, admin_required
from services.supabase_factory import get_supabase_admin
from services.corpus.ingestion import CorpusIngestionService
from services.corpus.pack_service import CollocationPackService

corpus_bp = Blueprint('corpus', __name__)


def _get_db():
    """Return the admin Supabase client (bypasses RLS)."""
    return get_supabase_admin()


@corpus_bp.route('/ingest', methods=['POST'])
@admin_required
def ingest_corpus():
    """
    Ingest a new corpus source and run the full analysis pipeline.
    Admin-only.

    Request body (JSON):
        source_type  (str, required): 'url' or 'text'
        language_id  (int, required): 1=ZH, 2=EN, 3=JA
        tags         (list[str], optional): Tag strings for this source
        url          (str): Required when source_type='url'
        text         (str): Required when source_type='text'
        title        (str): Required when source_type='text'

    Response (200):
        {"status": "success", "corpus_source_id": <int>}
    """
    body        = request.get_json(force=True)
    source_type = body.get('source_type')
    language_id = body.get('language_id')
    tags        = body.get('tags', [])

    if not source_type or not language_id:
        return jsonify({'error': 'source_type and language_id are required'}), 400

    service = CorpusIngestionService(db=_get_db())

    try:
        if source_type == 'url':
            url = body.get('url')
            if not url:
                return jsonify({'error': 'url is required for source_type=url'}), 400
            corpus_source_id = service.ingest_url(url, language_id, tags)

        elif source_type == 'text':
            text  = body.get('text')
            title = body.get('title', 'Untitled')
            if not text:
                return jsonify({'error': 'text is required for source_type=text'}), 400
            corpus_source_id = service.ingest_text(text, title, language_id, tags)

        else:
            return jsonify({'error': f'Unsupported source_type: {source_type}'}), 400

    except Exception as exc:
        return jsonify({'error': str(exc)}), 502

    return jsonify({'status': 'success', 'corpus_source_id': corpus_source_id})


@corpus_bp.route('/packs', methods=['GET'])
@jwt_required
def list_packs():
    """
    List public collocation packs for a language, with user selection state.

    Query params:
        language_id (int, required): Filter packs by language.

    Response (200):
        {"packs": [...]}
    """
    language_id_str = request.args.get('language_id')
    if not language_id_str:
        return jsonify({'error': 'language_id is required'}), 400

    try:
        language_id = int(language_id_str)
    except ValueError:
        return jsonify({'error': 'language_id must be an integer'}), 400

    user_id = g.current_user_id
    service = CollocationPackService(db=_get_db())
    packs   = service.get_packs_for_user(language_id, user_id)
    return jsonify({'packs': packs})


@corpus_bp.route('/packs/<int:pack_id>/select', methods=['POST'])
@jwt_required
def select_pack(pack_id: int):
    """
    Record that the authenticated user has selected a collocation pack.
    Idempotent — re-selecting the same pack is safe.

    Response (200):
        {"status": "success"}
    """
    user_id = g.current_user_id
    service = CollocationPackService(db=_get_db())
    service.select_pack(user_id, pack_id)
    return jsonify({'status': 'success'})
