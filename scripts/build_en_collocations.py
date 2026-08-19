#!/usr/bin/env python
"""Build ``data/collocations/en_collocations.tsv`` from a plain-text corpus (TASK-523).

Why this exists
---------------
``collocation_grounding`` needs an offline, licence-clean answer to "is this
(lemma, collocate) pair actually attested?". The bundled English list is that
answer. This script derives it.

Why dependency parsing rather than bigram counts
------------------------------------------------
A raw bigram count cannot tell *make a decision* from *decision to make*, and
it scores adjacent function words far above the pairs we care about. Every pair
here comes from a syntactic relation instead, so ``strong``/``coffee`` is
recorded once whichever order it appeared in and ``of``/``the`` never is. It
also fills the ``relation`` column with something true rather than a guess.

The grounder indexes pairs unordered (``BundledCollocationList.key``), so the
head/collocate column order is presentational only.

Source and licence
------------------
Default corpus is the Open American National Corpus — public domain, no
attribution or redistribution restrictions. ``--download`` fetches a GitHub
mirror that serves the same plain-text files over a valid certificate
(anc.org's own certificate is expired). The mirror's repository licence covers
its code; the OANC text it carries is public domain either way.

Usage
-----
    PYTHONPATH=. python scripts/build_en_collocations.py --download
    PYTHONPATH=. python scripts/build_en_collocations.py --corpus-dir /path/to/txt
    PYTHONPATH=. python scripts/build_en_collocations.py --download --limit 500
"""

from __future__ import annotations

import argparse
import csv
import io
import logging
import os
import sys
import tarfile
import time
import urllib.request
from collections import Counter

logger = logging.getLogger('build_en_collocations')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(REPO_ROOT, 'data', 'collocations', 'en_collocations.tsv')

# Public-domain OANC plain text, mirrored on GitHub (see module docstring).
OANC_MIRROR = 'https://codeload.github.com/jly02/ngram/tar.gz/refs/heads/{ref}'
OANC_MIRROR_REFS = ('main', 'master')
OANC_MEMBER_PREFIX = 'oanc/'

# Must match services.vocabulary_ladder.collocation_grounding.MIN_LIST_FREQUENCY.
# Writing rarer pairs would bloat the file with rows the loader discards.
DEFAULT_MIN_FREQUENCY = 5

# Dependency label -> the relation name we record. The child's POS is checked
# too, because `amod` can attach a participle and `dobj` a pronoun.
RELATIONS = {
    'dobj':     ('verb_object',    {'NOUN', 'PROPN'}),
    'nsubj':    ('verb_subject',   {'NOUN', 'PROPN'}),
    'amod':     ('adjective_noun', {'ADJ'}),
    'advmod':   ('adverb_verb',    {'ADV'}),
    'compound': ('noun_noun',      {'NOUN', 'PROPN'}),
}

# Heads worth recording per relation, keyed by the same dependency label.
HEAD_POS = {
    'dobj':     {'VERB'},
    'nsubj':    {'VERB'},
    'amod':     {'NOUN', 'PROPN'},
    'advmod':   {'VERB', 'ADJ'},
    'compound': {'NOUN', 'PROPN'},
}

# Light verbs and pro-forms dominate any dependency count and teach nothing as
# a collocation. `make a decision` survives (make is not here as an *object*),
# but `be`/`have`/`do` as heads swamp everything they attach to.
STOP_LEMMAS = {
    'be', 'have', 'do', 'go', 'get', 'thing', 'one', 'it', 'they', 'we',
    'i', 'you', 'he', 'she', 'who', 'what', 'that', 'this', 'there', 'here',
    'not', 'also', 'so', 'very', 'too', 'then', 'now', 'just', 'more', 'most',
    'other', 'such', 'own', 'same', 'about', 'as', 'well', 'much', 'many',
}


# ---------------------------------------------------------------------------
# Corpus acquisition
# ---------------------------------------------------------------------------

def download_oanc(dest_dir: str) -> int:
    """Fetch the mirrored OANC plain text into ``dest_dir``. Returns file count."""
    os.makedirs(dest_dir, exist_ok=True)
    existing = [f for f in os.listdir(dest_dir) if f.endswith('.txt')]
    if existing:
        logger.info('Reusing %d already-downloaded files in %s', len(existing), dest_dir)
        return len(existing)

    data = None
    last_error: Exception | None = None
    for ref in OANC_MIRROR_REFS:
        try:
            started = time.time()
            data = urllib.request.urlopen(OANC_MIRROR.format(ref=ref), timeout=600).read()
            logger.info('Downloaded %.1f MB (ref=%s) in %.1fs',
                        len(data) / 1e6, ref, time.time() - started)
            break
        except Exception as exc:                                  # noqa: BLE001
            last_error = exc
            logger.debug('ref=%s failed: %s', ref, exc)
    if data is None:
        raise RuntimeError(f'could not download OANC mirror: {last_error}')

    count = 0
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            path = member.name.split('/', 1)[1] if '/' in member.name else member.name
            if not path.startswith(OANC_MEMBER_PREFIX) or not path.endswith('.txt'):
                continue
            payload = archive.extractfile(member)
            if payload is None:
                continue
            with open(os.path.join(dest_dir, os.path.basename(path)), 'wb') as handle:
                handle.write(payload.read())
            count += 1
    logger.info('Extracted %d text files to %s', count, dest_dir)
    return count


def iter_documents(corpus_dir: str, limit: int | None = None):
    """Yield the text of each ``.txt`` file under ``corpus_dir``."""
    names = sorted(f for f in os.listdir(corpus_dir) if f.endswith('.txt'))
    if limit:
        names = names[:limit]
    for name in names:
        path = os.path.join(corpus_dir, name)
        try:
            with open(path, encoding='utf-8', errors='replace') as handle:
                text = handle.read()
        except OSError as exc:                                    # noqa: PERF203
            logger.warning('Skipping %s: %s', name, exc)
            continue
        if text.strip():
            yield text


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _usable(token) -> bool:
    """A token worth putting in a collocation list."""
    lemma = token.lemma_.casefold()
    return (
        token.is_alpha
        and not token.is_stop
        and len(lemma) > 2
        and lemma not in STOP_LEMMAS
    )


def collocations_from_doc(doc) -> list[tuple[str, str, str]]:
    """Extract ``(head_lemma, child_lemma, relation)`` triples from a parsed doc."""
    found: list[tuple[str, str, str]] = []
    for token in doc:
        spec = RELATIONS.get(token.dep_)
        if spec is None:
            continue
        relation, child_pos = spec
        if token.pos_ not in child_pos:
            continue
        head = token.head
        if head is token or head.pos_ not in HEAD_POS[token.dep_]:
            continue
        if not (_usable(token) and _usable(head)):
            continue
        # casefold(), not lower(), because BundledCollocationList.key casefolds.
        # With lower() a handful of pairs (ß-class lemmas) key differently here
        # than at load time, and the loader's dict silently keeps whichever row
        # it read last instead of their combined frequency.
        found.append((head.lemma_.casefold(), token.lemma_.casefold(), relation))
    return found


def merge_pairs(counts: Counter) -> dict:
    """Collapse ``(head, child, relation)`` triples onto the unordered pair key.

    The loader keys on the unordered pair, so two relations for one pair must
    be summed here — emitting both as separate rows would let the second
    silently overwrite the first at load time. The label kept is the one with
    the highest single-relation count.
    """
    totals: dict[tuple[str, str], int] = {}
    best: dict[tuple[str, str], tuple[int, str]] = {}
    for (head, child, relation), count in counts.items():
        key = (head, child) if head <= child else (child, head)
        totals[key] = totals.get(key, 0) + count
        if key not in best or count > best[key][0]:
            best[key] = (count, relation)
    return {key: (total, best[key][1]) for key, total in totals.items()}


def build(corpus_dir: str, out_path: str, *,
          min_frequency: int = DEFAULT_MIN_FREQUENCY,
          limit: int | None = None,
          processes: int = 1) -> dict:
    """Parse the corpus and write the TSV. Returns a summary dict."""
    import spacy

    # The parser is the only component we need; NER is the expensive one we
    # do not. The lemmatizer/tagger stay because every pair is lemmatised.
    nlp = spacy.load('en_core_web_sm', exclude=['ner'])
    nlp.max_length = 2_000_000

    counts: Counter = Counter()
    docs = 0
    words = 0
    started = time.time()

    texts = iter_documents(corpus_dir, limit=limit)
    for doc in nlp.pipe(texts, batch_size=64, n_process=processes):
        docs += 1
        words += len(doc)
        counts.update(collocations_from_doc(doc))
        if docs % 500 == 0:
            logger.info('  %d docs, %.1fM words, %d distinct triples, %.0fs',
                        docs, words / 1e6, len(counts), time.time() - started)

    merged = merge_pairs(counts)
    rows = [(head, child, total, relation)
            for (head, child), (total, relation) in merged.items()
            if total >= min_frequency]
    rows.sort(key=lambda r: (-r[2], r[0], r[1]))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(
            '# English collocation frequencies derived from the Open American\n'
            '# National Corpus (OANC), public domain. Built by\n'
            '# scripts/build_en_collocations.py — see data/collocations/README.md.\n'
            f'# docs={docs} words={words} pairs={len(rows)} min_frequency={min_frequency}\n'
        )
        writer = csv.writer(handle, delimiter='\t', lineterminator='\n')
        writer.writerow(['head', 'collocate', 'frequency', 'relation'])
        writer.writerows(rows)

    summary = {
        'docs': docs,
        'words': words,
        'distinct_triples': len(counts),
        'distinct_pairs': len(merged),
        'written': len(rows),
        'seconds': round(time.time() - started, 1),
        'out_path': out_path,
    }
    logger.info('Wrote %d pairs to %s (%d docs, %.1fM words, %.0fs)',
                len(rows), out_path, docs, words / 1e6, summary['seconds'])
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--corpus-dir',
                        help='directory of .txt files to parse')
    parser.add_argument('--download', action='store_true',
                        help='fetch the public-domain OANC mirror first')
    parser.add_argument('--download-dir',
                        default=os.path.join(REPO_ROOT, '.cache', 'oanc'),
                        help='where --download puts the corpus (cached across runs)')
    parser.add_argument('--out', default=DEFAULT_OUT,
                        help=f'output TSV (default: {DEFAULT_OUT})')
    parser.add_argument('--min-frequency', type=int, default=DEFAULT_MIN_FREQUENCY,
                        help='drop pairs below this count (default: %(default)s)')
    parser.add_argument('--limit', type=int,
                        help='only parse the first N documents (smoke runs)')
    parser.add_argument('--processes', type=int, default=1,
                        help='spaCy n_process (default: %(default)s)')
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    corpus_dir = args.corpus_dir
    if args.download:
        download_oanc(args.download_dir)
        corpus_dir = corpus_dir or args.download_dir
    if not corpus_dir:
        parser.error('one of --corpus-dir or --download is required')
    if not os.path.isdir(corpus_dir):
        parser.error(f'corpus directory not found: {corpus_dir}')

    summary = build(corpus_dir, args.out,
                    min_frequency=args.min_frequency,
                    limit=args.limit,
                    processes=args.processes)
    for key, value in summary.items():
        print(f'{key}: {value}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
