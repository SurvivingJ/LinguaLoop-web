import threading
from services.corpus.ingestion import CorpusIngestionService


def run_ingestion_async(
    payload: dict,
    db_factory,
) -> None:
    """
    Run CorpusIngestionService._run_pipeline in a background thread.
    Use this for large author corpora or batch URL ingestion.

    Args:
        payload:    Dict with keys: raw_text, source_type, source_url,
                    source_title, language_id, tags.
        db_factory: Callable returning a fresh Supabase client
                    (cannot use Flask g outside request context).
    """
    def _worker():
        db      = db_factory()
        service = CorpusIngestionService(db=db)
        service._run_pipeline(**payload)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
