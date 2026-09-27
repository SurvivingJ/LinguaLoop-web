from flask import Blueprint, request, g
from middleware.auth import jwt_required, admin_required
from services.supabase_factory import get_supabase_admin
from services.corpus.ingestion import CorpusIngestionService
from utils.responses import api_success, api_error, bad_request, not_found

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
        return bad_request('source_type and language_id are required')

    service = CorpusIngestionService(db=_get_db())

    try:
        if source_type == 'url':
            url = body.get('url')
            if not url:
                return bad_request('url is required for source_type=url')
            corpus_source_id = service.ingest_url(url, language_id, tags, analyze_style=analyze_style)

        elif source_type == 'text':
            text  = body.get('text')
            title = body.get('title', 'Untitled')
            if not text:
                return bad_request('text is required for source_type=text')
            corpus_source_id = service.ingest_text(text, title, language_id, tags, analyze_style=analyze_style)

        else:
            return bad_request(f'Unsupported source_type: {source_type}')

    except Exception as exc:
        return api_error(str(exc), 502)

    return api_success(data={'corpus_source_id': corpus_source_id})


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
        return bad_request('corpus_source_id and language_id are required')

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
        return not_found('Corpus source not found or has no stored text')

    try:
        service = CorpusIngestionService(db=db)
        profile_id = service._run_style_pipeline(
            raw_text=source.data['raw_text'],
            corpus_source_id=corpus_source_id,
            language_id=language_id,
        )
    except Exception as exc:
        return api_error(str(exc), 502)

    return api_success(data={'style_profile_id': profile_id})


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
        return not_found('No style profile found for this source')

    return api_success(data={'profile': result.data[0]})

