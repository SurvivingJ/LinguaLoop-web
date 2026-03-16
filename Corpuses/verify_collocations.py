"""
Verify unvalidated collocations using substitution entropy scoring.

Usage:
    python Corpuses/verify_collocations.py --language chinese
    python Corpuses/verify_collocations.py --language english --limit 200 --entropy-threshold 2.5

Reads corpus_collocations where is_validated IS NULL, scores each,
writes substitution_entropy + updates is_validated (True/False).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from services.corpus.verifier import substitution_entropy, is_worth_keeping

LANGUAGE_MAP = {
    'english': 2, 'en': 2,
    'chinese': 1, 'zh': 1,
    'japanese': 3, 'ja': 3,
}


def main():
    parser = argparse.ArgumentParser(description='Verify collocations with substitution entropy')
    parser.add_argument('--language', required=True, help='Language name or code (english, zh, japanese)')
    parser.add_argument('--limit', type=int, default=500, help='Max rows to process (default: 500)')
    parser.add_argument('--entropy-threshold', type=float, default=2.8,
                        help='Max acceptable entropy (default: 2.8, lower = stricter)')
    parser.add_argument('--source-id', type=int, default=None,
                        help='Restrict to one corpus_source_id')
    args = parser.parse_args()

    language_id = LANGUAGE_MAP.get(args.language.lower())
    if not language_id:
        print(f"Unknown language: {args.language}")
        sys.exit(1)

    db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

    query = (
        db.table('corpus_collocations')
        .select('id, collocation_text, pmi_score, lmi_score, extraction_method')
        .eq('language_id', language_id)
        .is_('is_validated', 'null')
        .order('lmi_score', desc=True)
        .limit(args.limit)
    )
    if args.source_id:
        query = query.eq('corpus_source_id', args.source_id)

    rows = query.execute().data
    print(f"Verifying {len(rows)} collocations...")

    kept = 0
    dropped = 0
    for row in rows:
        entropy = substitution_entropy(row['collocation_text'], language_id)
        keep = is_worth_keeping(entropy, row['pmi_score'], args.entropy_threshold)

        db.table('corpus_collocations').update({
            'substitution_entropy': entropy,
            'is_validated': keep,
        }).eq('id', row['id']).execute()

        if keep:
            kept += 1
            status = 'keep'
        else:
            dropped += 1
            status = 'drop'
        method = row.get('extraction_method', 'ngram')
        print(f"  [{status:4s}] [{method:10s}] {row['collocation_text']:25s}  "
              f"entropy={entropy:.3f}  pmi={row['pmi_score']:.2f}  lmi={row.get('lmi_score', 0):.1f}")

    print(f"\nDone. Kept: {kept}, Dropped: {dropped}")


if __name__ == '__main__':
    main()
