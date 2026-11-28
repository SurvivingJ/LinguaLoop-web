#!/usr/bin/env python3
"""Create dim_vocabulary rows for a curated word list (e.g. a JLPT level), read-before-write.

The sense workflows (.claude/skills/batch-sense-generation, cross-language-glosses) only
define words that already exist in ``dim_vocabulary``; outside test generation nothing
creates those rows. This loader does, through the one shared writer
(``services.vocabulary.word_resolver.get_or_create_vocab_id``), so a new row gets the same
reading and Zipf frequency a test-pipeline row would, and an existing lemma is reused,
never duplicated.

Input: a JSON list of objects with ``lemma``, ``reading`` (hiragana) and ``pos`` (an
English label from services.vocabulary.pos.CANONICAL_POS, or a tagger tag it normalises).
Extra keys are ignored.

Usage:
    python scripts/load_vocab_list.py --input data/sense_seeding/ja_jlpt/n5n4_worklist.json --language ja
    python scripts/load_vocab_list.py --input ... --language ja --apply --out data/.../vocab_ids.json

Without --apply nothing is written: it reports which lemmas exist already and which would
be created.
"""
from __future__ import annotations

import json
import logging

try:
    from _common import admin_db, base_parser, bootstrap
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import admin_db, base_parser, bootstrap

bootstrap()

from services import language_registry  # noqa: E402
from services.vocabulary.pos import normalize_pos  # noqa: E402
from services.vocabulary.word_resolver import get_or_create_vocab_id  # noqa: E402

logger = logging.getLogger(__name__)
LANGUAGE_IDS = language_registry.code_to_id()


def load_items(path: str) -> list[dict]:
    with open(path, encoding='utf-8') as fh:
        items = json.load(fh)
    out, seen = [], set()
    for it in items:
        lemma = str(it.get('lemma') or '').strip()
        if not lemma or lemma in seen:
            continue
        seen.add(lemma)
        out.append({'lemma': lemma, 'reading': str(it.get('reading') or '').strip() or None,
                    'pos': normalize_pos(it.get('pos'))})
    return out


def existing_ids(db, lemmas: list[str], language_id: int) -> dict[str, int]:
    found: dict[str, int] = {}
    for i in range(0, len(lemmas), 200):
        rows = (db.table('dim_vocabulary').select('id,lemma').eq('language_id', language_id)
                .in_('lemma', lemmas[i:i + 200]).execute().data or [])
        found.update({r['lemma']: r['id'] for r in rows})
    return found


def main() -> int:
    parser = base_parser(__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--language', required=True, choices=sorted(LANGUAGE_IDS))
    parser.add_argument('--out', help='write {lemma: vocab_id} for every input lemma (with --apply)')
    args = parser.parse_args()

    language_id = LANGUAGE_IDS[args.language]
    db = admin_db()
    items = load_items(args.input)
    have = existing_ids(db, [i['lemma'] for i in items], language_id)
    new = [i for i in items if i['lemma'] not in have]
    logger.info('%d lemmas: %d exist already, %d to create', len(items), len(have), len(new))
    if have:
        logger.info('  existing: %s', ', '.join(list(have)[:30]) + ('…' if len(have) > 30 else ''))
    if not args.apply:
        for i in new[:20]:
            logger.info('  would create %s (%s, %s)', i['lemma'], i['reading'], i['pos'])
        logger.info('Dry run: nothing written. Re-run with --apply.')
        return 0

    ids = dict(have)
    cache: dict = {}
    for n, i in enumerate(new, 1):
        ids[i['lemma']] = get_or_create_vocab_id(db, {'lemma': i['lemma'], 'pos': i['pos'], 'reading': i['reading']},
                                                 language_id, args.language, cache=cache)
        if n % 100 == 0:
            logger.info('  %d / %d created', n, len(new))
    logger.info('Created %d rows; %d lemmas mapped', len(new), len(ids))
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as fh:
            json.dump(ids, fh, ensure_ascii=False, indent=1)
        logger.info('Wrote %s', args.out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
