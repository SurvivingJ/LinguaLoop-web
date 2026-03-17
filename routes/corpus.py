from flask import Blueprint, request, jsonify, g
from middleware.auth import jwt_required, admin_required
from services.supabase_factory import get_supabase_admin
from services.corpus.ingestion import CorpusIngestionService
from services.corpus.pack_service import CollocationPackService
from services.corpus.style_pack_service import StylePackService

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
    body          = request.get_json(force=True)
    source_type   = body.get('source_type')
    language_id   = body.get('language_id')
    tags          = body.get('tags', [])
    analyze_style = body.get('analyze_style', False)

    if not source_type or not language_id:
        return jsonify({'error': 'source_type and language_id are required'}), 400

    service = CorpusIngestionService(db=_get_db())

    try:
        if source_type == 'url':
            url = body.get('url')
            if not url:
                return jsonify({'error': 'url is required for source_type=url'}), 400
            corpus_source_id = service.ingest_url(url, language_id, tags, analyze_style=analyze_style)

        elif source_type == 'text':
            text  = body.get('text')
            title = body.get('title', 'Untitled')
            if not text:
                return jsonify({'error': 'text is required for source_type=text'}), 400
            corpus_source_id = service.ingest_text(text, title, language_id, tags, analyze_style=analyze_style)

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


# ── Style analysis routes ──────────────────────────────────────────────


@corpus_bp.route('/style-analyze', methods=['POST'])
@admin_required
def analyze_style():
    """
    Run style analysis on an existing corpus source.
    Admin-only.

    Request body (JSON):
        corpus_source_id (int, required): ID of the corpus source to analyse.
        language_id      (int, required): 1=ZH, 2=EN, 3=JA.

    Response (200):
        {"status": "success", "style_profile_id": <int>}
    """
    body = request.get_json(force=True)
    corpus_source_id = body.get('corpus_source_id')
    language_id = body.get('language_id')

    if not corpus_source_id or not language_id:
        return jsonify({'error': 'corpus_source_id and language_id are required'}), 400

    # Load the raw text from the source
    db = _get_db()
    source = (
        db.table('corpus_sources')
        .select('raw_text')
        .eq('id', corpus_source_id)
        .single()
        .execute()
    )
    if not source.data or not source.data.get('raw_text'):
        return jsonify({'error': 'Corpus source not found or has no stored text'}), 404

    try:
        service = CorpusIngestionService(db=db)
        profile_id = service._run_style_pipeline(
            raw_text=source.data['raw_text'],
            corpus_source_id=corpus_source_id,
            language_id=language_id,
        )
    except Exception as exc:
        return jsonify({'error': str(exc)}), 502

    return jsonify({'status': 'success', 'style_profile_id': profile_id})


@corpus_bp.route('/style-profile/<int:source_id>', methods=['GET'])
@admin_required
def get_style_profile(source_id: int):
    """
    Fetch the style profile for a corpus source.

    Response (200):
        {"profile": {...}}
    """
    db = _get_db()
    result = (
        db.table('corpus_style_profiles')
        .select('*')
        .eq('corpus_source_id', source_id)
        .execute()
    )
    if not result.data:
        return jsonify({'error': 'No style profile found for this source'}), 404

    return jsonify({'profile': result.data[0]})


@corpus_bp.route('/style-packs', methods=['POST'])
@admin_required
def create_style_pack():
    """
    Create a style pack from a corpus source's style profile.
    Admin-only.

    Request body (JSON):
        corpus_source_id (int, required)
        pack_name        (str, required)
        description      (str, optional)
        language_id      (int, required)

    Response (200):
        {"status": "success", "pack_id": <int>}
    """
    body = request.get_json(force=True)
    corpus_source_id = body.get('corpus_source_id')
    pack_name = body.get('pack_name')
    language_id = body.get('language_id')
    description = body.get('description', '')

    if not corpus_source_id or not pack_name or not language_id:
        return jsonify({'error': 'corpus_source_id, pack_name, and language_id are required'}), 400

    try:
        service = StylePackService(db=_get_db())
        pack_id = service.create_pack_from_profile(
            corpus_source_id=corpus_source_id,
            pack_name=pack_name,
            description=description,
            language_id=language_id,
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 502

    return jsonify({'status': 'success', 'pack_id': pack_id})


@corpus_bp.route('/style-packs', methods=['GET'])
@jwt_required
def list_style_packs():
    """
    List public style packs for a language.

    Query params:
        language_id (int, required)

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

    service = StylePackService(db=_get_db())
    packs = service.get_style_packs(language_id)
    return jsonify({'packs': packs})


@corpus_bp.route('/style-packs/<int:pack_id>/items', methods=['GET'])
@jwt_required
def get_style_pack_items(pack_id: int):
    """
    Get all items in a style pack.

    Response (200):
        {"items": [...]}
    """
    service = StylePackService(db=_get_db())
    items = service.get_pack_items(pack_id)
    return jsonify({'items': items})
