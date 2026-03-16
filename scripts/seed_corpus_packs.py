"""
One-time seed script: ingest starter corpus sources and create initial packs.

Usage:
    python scripts/seed_corpus_packs.py

Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY in environment.

Public-domain texts are fetched from Project Gutenberg or provided inline.
Adjust SOURCES list as needed.
"""
import os
from supabase import create_client
from services.corpus.ingestion import CorpusIngestionService
from services.corpus.pack_service import CollocationPackService

# ---------------------------------------------------------------------------
# Starter source definitions
# Each entry: (source_type, identifier, language_id, tags, pack_meta)
# ---------------------------------------------------------------------------
SOURCES = [
    {
        'source_type': 'url',
        'url': 'https://www.theguardian.com/business/economics',
        'language_id': 2,
        'tags': ['economics_reporting', 'news'],
        'pack': {
            'pack_name':   'Economics Reporting',
            'description': 'Collocations from economics news reporting',
            'pack_type':   'genre',
        },
    },
    {
        'source_type': 'url',
        # Gulliver's Travels — full public domain text via Gutenberg
        'url': 'https://www.gutenberg.org/files/829/829-0.txt',
        'language_id': 2,
        'tags': ['author_jonathan_swift', 'literature'],
        'pack': {
            'pack_name':   'Jonathan Swift',
            'description': "Collocations from Swift's prose",
            'pack_type':   'author',
        },
    },
]


def run_seed():
    """
    Ingest each source and create its corresponding pack.
    Safe to re-run — duplicate corpus_sources rows will be created
    but existing pack data is unaffected.
    """
    url  = os.environ['SUPABASE_URL']
    key  = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    db   = create_client(url, key)

    ingestor    = CorpusIngestionService(db=db)
    pack_svc    = CollocationPackService(db=db)

    for s in SOURCES:
        print(f"Ingesting: {s.get('url', s.get('title', '?'))}")

        if s['source_type'] == 'url':
            source_id = ingestor.ingest_url(
                url=s['url'],
                language_id=s['language_id'],
                tags=s['tags'],
            )
        elif s['source_type'] == 'text':
            source_id = ingestor.ingest_text(
                text=s['text'],
                title=s['title'],
                language_id=s['language_id'],
                tags=s['tags'],
            )
        else:
            print(f"  Skipping unknown source_type: {s['source_type']}")
            continue

        print(f"  corpus_source_id={source_id}. Creating pack...")
        pack_id = pack_svc.create_pack_from_corpus(
            corpus_source_id=source_id,
            pack_name=s['pack']['pack_name'],
            description=s['pack']['description'],
            pack_type=s['pack']['pack_type'],
            language_id=s['language_id'],
        )
        print(f"  pack_id={pack_id} created: {s['pack']['pack_name']}")

    print("Seed complete.")


if __name__ == '__main__':
    run_seed()
