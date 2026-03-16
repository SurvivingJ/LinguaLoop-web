"""
Ingest text into the corpus analysis pipeline.

Modes:
    FILE MODE:        Analyse a .txt file from the Corpuses/ folder.
    TRANSCRIPT MODE:  Analyse all test transcripts for a language from the DB.

Usage:
    python Corpuses/ingest_corpus.py <filename> <language>
    python Corpuses/ingest_corpus.py --transcripts <language>

Examples:
    python Corpuses/ingest_corpus.py economics_article.txt english
    python Corpuses/ingest_corpus.py news_zh.txt chinese
    python Corpuses/ingest_corpus.py --transcripts english
    python Corpuses/ingest_corpus.py --transcripts zh --create-pack

Arguments:
    filename        Name of the .txt file inside the Corpuses/ folder
    language        One of: english, chinese, japanese (or en, zh, ja)

Optional:
    --transcripts   Use all test transcripts from the DB instead of a file
    --tags          Comma-separated tags (default: derived from filename)
    --title         Custom title (default: derived from filename)
    --create-pack   Also create a collocation pack from the results
"""
import argparse
import os
import sys

# Add project root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from services.corpus.ingestion import CorpusIngestionService
from services.corpus.pack_service import CollocationPackService

LANGUAGE_MAP = {
    'english': 2, 'en': 2,
    'chinese': 1, 'zh': 1,
    'japanese': 3, 'ja': 3,
}

LANGUAGE_NAMES = {1: 'Chinese', 2: 'English', 3: 'Japanese'}

CORPUSES_DIR = os.path.dirname(os.path.abspath(__file__))


def _get_db():
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)
    return create_client(supabase_url, supabase_key)


def _resolve_language(lang_str: str) -> int:
    language_id = LANGUAGE_MAP.get(lang_str.lower())
    if language_id is None:
        print(f"Error: Unknown language '{lang_str}'.")
        print(f"Valid options: {', '.join(LANGUAGE_MAP.keys())}")
        sys.exit(1)
    return language_id


def _create_pack(db, source_id, title, language_id):
    print("Creating collocation pack...")
    pack_svc = CollocationPackService(db=db)
    try:
        pack_id = pack_svc.create_pack_from_corpus(
            corpus_source_id=source_id,
            pack_name=title,
            description=f"Collocations from {title}",
            pack_type='topic',
            language_id=language_id,
        )
        print(f"Pack created! pack_id = {pack_id}")
    except ValueError as e:
        print(f"Pack creation skipped: {e}")


def run_file_mode(args):
    """Ingest a .txt file from the Corpuses/ folder."""
    language_id = _resolve_language(args.language)

    filepath = os.path.join(CORPUSES_DIR, args.filename)
    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}")
        print(f"Place your .txt file in the Corpuses/ folder and try again.")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    if not text.strip():
        print(f"Error: File is empty: {filepath}")
        sys.exit(1)

    word_count = len(text.split())
    basename = os.path.splitext(args.filename)[0]
    title = args.title or basename.replace('_', ' ').replace('-', ' ').title()
    tags = [t.strip() for t in args.tags.split(',')] if args.tags else [basename.lower().replace(' ', '_')]

    print(f"File:     {args.filename}")
    print(f"Language: {LANGUAGE_NAMES[language_id]} (id={language_id})")
    print(f"Words:    {word_count:,}")
    print(f"Title:    {title}")
    print(f"Tags:     {tags}")
    print()

    db = _get_db()
    service = CorpusIngestionService(db=db)

    print("Running corpus analysis pipeline...")
    source_id = service.ingest_text(text, title, language_id, tags)
    print(f"Done! corpus_source_id = {source_id}")

    if args.create_pack:
        _create_pack(db, source_id, title, language_id)

    print()
    print("Verify results:")
    print(f"  SELECT collocation_text, head_word, collocate, pmi_score, frequency, collocation_type")
    print(f"  FROM corpus_collocations WHERE corpus_source_id = {source_id}")
    print(f"  ORDER BY pmi_score DESC LIMIT 30;")


def run_transcript_mode(args):
    """Ingest all test transcripts for a language from the database."""
    language_id = _resolve_language(args.language)
    lang_name = LANGUAGE_NAMES[language_id]

    print(f"Language: {lang_name} (id={language_id})")
    print(f"Source:   All active test transcripts")
    print()

    db = _get_db()
    service = CorpusIngestionService(db=db)

    extra_tags = [t.strip() for t in args.tags.split(',')] if args.tags else None

    print("Fetching transcripts and running corpus analysis pipeline...")
    try:
        source_id = service.ingest_transcripts(language_id, extra_tags=extra_tags)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Done! corpus_source_id = {source_id}")

    title = args.title or f"{lang_name} Transcripts"
    if args.create_pack:
        _create_pack(db, source_id, title, language_id)

    print()
    print("Verify results:")
    print(f"  SELECT collocation_text, head_word, collocate, pmi_score, frequency, collocation_type")
    print(f"  FROM corpus_collocations WHERE corpus_source_id = {source_id}")
    print(f"  ORDER BY pmi_score DESC LIMIT 30;")


def main():
    parser = argparse.ArgumentParser(
        description='Ingest text into the corpus analysis pipeline.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('filename', nargs='?', default=None,
                        help='Name of the .txt file inside the Corpuses/ folder')
    parser.add_argument('language', help='Language: english/en, chinese/zh, japanese/ja')
    parser.add_argument('--transcripts', action='store_true',
                        help='Analyse all test transcripts from DB instead of a file')
    parser.add_argument('--tags', default=None,
                        help='Comma-separated tags (e.g. "news,economics")')
    parser.add_argument('--title', default=None,
                        help='Custom title for the corpus source')
    parser.add_argument('--create-pack', action='store_true',
                        help='Also create a collocation pack from the results')
    args = parser.parse_args()

    if args.transcripts:
        run_transcript_mode(args)
    elif args.filename:
        run_file_mode(args)
    else:
        print("Error: Provide a filename or use --transcripts")
        print("  python Corpuses/ingest_corpus.py my_text.txt english")
        print("  python Corpuses/ingest_corpus.py --transcripts english")
        sys.exit(1)


if __name__ == '__main__':
    main()
