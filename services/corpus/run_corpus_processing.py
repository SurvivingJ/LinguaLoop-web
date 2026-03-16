"""
Entry point for scheduled / manual reprocessing of unprocessed corpus sources.
Can be run via Railway cron or manually:
    python services/corpus/run_corpus_processing.py

Finds corpus_sources where processed_at IS NULL and re-runs the analysis
pipeline on each, using the stored raw_text.
"""
import os
from supabase import create_client
from services.corpus.ingestion import CorpusIngestionService


def sweep_unprocessed_sources() -> int:
    """
    Find all corpus_sources with processed_at IS NULL and reprocess them.
    Only processes sources that have raw_text stored inline (not offloaded to R2).

    Returns:
        int: Number of sources successfully processed.
    """
    url  = os.environ['SUPABASE_URL']
    key  = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    db   = create_client(url, key)

    unprocessed = (
        db.table('corpus_sources')
        .select('id, raw_text, language_id, source_type, source_url, source_title, tags')
        .is_('processed_at', 'NULL')
        .not_.is_('raw_text', 'NULL')
        .execute()
    )

    if not unprocessed.data:
        print("No unprocessed sources found.")
        return 0

    service   = CorpusIngestionService(db=db)
    processed = 0

    for source in unprocessed.data:
        try:
            service._run_pipeline(
                raw_text=source['raw_text'],
                source_type=source['source_type'],
                source_url=source['source_url'],
                source_title=source['source_title'],
                language_id=source['language_id'],
                tags=source['tags'] or [],
            )
            processed += 1
            print(f"Processed corpus_source id={source['id']}: {source['source_title']}")
        except Exception as exc:
            print(f"Failed corpus_source id={source['id']}: {exc}")

    return processed


if __name__ == '__main__':
    n = sweep_unprocessed_sources()
    print(f"Done. Processed {n} sources.")
