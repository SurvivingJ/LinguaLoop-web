#!/usr/bin/env python3
"""Populate ``dim_character_components`` from openly-licensed CJK data (TASK-529).

What this feeds
---------------
The visual-similarity tier of the reverse-reading distractor ladder. When a
reading's homophone set is too thin to fill four options,
``Lexicon.component_neighbours`` pads the foils with characters that share
structure — the 张/章/掌 case. Without this table that tier is simply skipped,
which is a supported (if weaker) state.

Sources and why these ones
--------------------------
============  ==========================================  =====================
Data          Source                                      Licence
============  ==========================================  =====================
components    amake/cjk-decomp (CJK decomposition data)   Apache-2.0
radical,      Unicode Unihan database                     Unicode License
strokes       (``Unihan_IRGSources.txt``)
============  ==========================================  =====================

Both are permissive and redistributable. The obvious alternative,
``cjkvi-ids``, is **GPLv2** — copyleft on a data file vendored into this
repository would follow it out to every deployment, which is the same test
``data/collocations/README.md`` applies to the English collocation list.
KanjiVG (CC BY-SA 3.0) is share-alike and covers only kanji, so it would miss
simplified-only hanzi; cjk-decomp covers simplified, traditional and kanji.

The component-frequency filter
------------------------------
A recursive decomposition bottoms out in strokes and near-universal parts
(一, 丨, 丶). Those match everything, so a distractor chosen by "shares the
most components" would be dominated by them and the foils would be arbitrary.
Components appearing in more than ``--max-component-share`` of all characters
are therefore dropped: a component only discriminates if it is *not*
everywhere. Same reasoning as a stopword list, applied to strokes.

Usage
-----
    PYTHONPATH=. python scripts/import_character_components.py --dry-run
    PYTHONPATH=. python scripts/import_character_components.py
    PYTHONPATH=. python scripts/import_character_components.py --max-depth 3
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import re
import sys
import urllib.request
import zipfile
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from services.supabase_factory import SupabaseFactory, get_supabase_admin

logger = logging.getLogger('import_character_components')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO_ROOT, '.cache', 'components')

CJK_DECOMP_URL = 'https://raw.githubusercontent.com/amake/cjk-decomp/master/cjk-decomp.txt'
UNIHAN_URL = 'https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip'

SOURCE = 'cjk-decomp+unihan'
LICENCE = 'cjk-decomp: Apache-2.0; Unihan: Unicode License'

# `char:type(arg,arg)` — the key and args are either a real character or a
# numeric id standing for an unencoded component.
DECOMP_LINE = re.compile(r'^([^:]+):([a-z/]+)\(([^)]*)\)\s*$')

# Decomposition types meaning "this is atomic" — no useful parts to record.
ATOMIC_TYPES = {'c'}

# CJK Unified Ideographs, Extension A, and Compatibility Ideographs. Anything
# outside these is a stroke, a radical form, or a PUA placeholder.
CJK_RANGES = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF))

DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_COMPONENT_SHARE = 0.05
BATCH = 500


def is_cjk(char: str) -> bool:
    if len(char) != 1:
        return False
    point = ord(char)
    return any(low <= point <= high for low, high in CJK_RANGES)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def _cached(url: str, filename: str, timeout: int = 600) -> bytes:
    """Fetch ``url`` once, caching under ``.cache/components``."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, filename)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        logger.info('Using cached %s', path)
        with open(path, 'rb') as handle:
            return handle.read()
    logger.info('Downloading %s', url)
    payload = urllib.request.urlopen(url, timeout=timeout).read()
    with open(path, 'wb') as handle:
        handle.write(payload)
    logger.info('Cached %.1f MB to %s', len(payload) / 1e6, path)
    return payload


# ---------------------------------------------------------------------------
# cjk-decomp
# ---------------------------------------------------------------------------

def parse_decompositions(text: str) -> dict:
    """``key -> (raw_expression, [direct parts])`` for every parsable line."""
    table: dict = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = DECOMP_LINE.match(line)
        if not match:
            continue
        key, kind, args = match.group(1), match.group(2), match.group(3)
        parts = [a.strip() for a in args.split(',') if a.strip()]
        if kind in ATOMIC_TYPES:
            parts = []
        table[key] = (f'{kind}({args})', parts)
    return table


def resolve_components(key: str, table: dict, max_depth: int) -> set:
    """Real-character components of ``key``, expanded to ``max_depth``.

    Numeric ids (unencoded components) are transparent: they are expanded
    through without being recorded, because they can never be shown to a
    learner or matched against a lemma. A ``seen`` set guards the cycles the
    source data does contain.
    """
    found: set = set()
    seen: set = {key}
    frontier = [(key, 0)]
    while frontier:
        node, depth = frontier.pop()
        entry = table.get(node)
        if entry is None:
            continue
        for part in entry[1]:
            if part == node or part in seen:
                continue
            if is_cjk(part):
                found.add(part)
                # A real character costs one level of depth budget.
                if depth + 1 < max_depth:
                    seen.add(part)
                    frontier.append((part, depth + 1))
            else:
                # Numeric/PUA placeholder: descend without spending depth and
                # without recording it, since it is not a character.
                seen.add(part)
                frontier.append((part, depth))
    found.discard(key)
    return found


# ---------------------------------------------------------------------------
# Unihan
# ---------------------------------------------------------------------------

def parse_unihan(payload: bytes) -> dict:
    """``character -> {'radical': str|None, 'stroke_count': int|None}``."""
    fields: dict = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name in [n for n in archive.namelist() if n.endswith('.txt')]:
            with archive.open(name) as handle:
                for raw in io.TextIOWrapper(handle, encoding='utf-8'):
                    if not raw or raw.startswith('#'):
                        continue
                    bits = raw.rstrip('\n').split('\t')
                    if len(bits) < 3:
                        continue
                    code, key, value = bits[0], bits[1], bits[2]
                    if key not in ('kRSUnicode', 'kTotalStrokes'):
                        continue
                    try:
                        char = chr(int(code[2:], 16))
                    except (ValueError, IndexError):
                        continue
                    slot = fields.setdefault(char, {})
                    if key == 'kTotalStrokes':
                        first = value.split()[0]
                        if first.isdigit():
                            slot['stroke_count'] = int(first)
                    else:
                        # "85.5" / "85'.5" — the number before the dot is the
                        # Kangxi radical index, 1..214.
                        head = value.split()[0].split('.')[0].rstrip("'")
                        if head.isdigit() and 1 <= int(head) <= 214:
                            slot['radical'] = chr(0x2F00 + int(head) - 1)
    return fields


# ---------------------------------------------------------------------------
# Build + load
# ---------------------------------------------------------------------------

def build_rows(*, max_depth: int, max_component_share: float) -> list:
    decomp_text = _cached(CJK_DECOMP_URL, 'cjk-decomp.txt').decode('utf-8', 'replace')
    table = parse_decompositions(decomp_text)
    logger.info('Parsed %d decomposition entries', len(table))

    characters = [k for k in table if is_cjk(k)]
    logger.info('%d of them are CJK characters', len(characters))

    resolved: dict = {}
    for char in characters:
        parts = resolve_components(char, table, max_depth)
        if parts:
            resolved[char] = parts

    # Drop components too common to discriminate (see module docstring).
    frequency: Counter = Counter()
    for parts in resolved.values():
        frequency.update(parts)
    ceiling = max(1, int(len(resolved) * max_component_share))
    ubiquitous = {c for c, n in frequency.items() if n > ceiling}
    logger.info('Dropping %d components appearing in >%d characters (%.1f%%)',
                len(ubiquitous), ceiling, max_component_share * 100)

    unihan = parse_unihan(_cached(UNIHAN_URL, 'Unihan.zip'))
    logger.info('Parsed Unihan fields for %d characters', len(unihan))

    rows: list = []
    for char in sorted(resolved):
        parts = sorted(resolved[char] - ubiquitous)
        if not parts:
            continue
        extra = unihan.get(char, {})
        rows.append({
            'character': char,
            'components': parts,
            'radical': extra.get('radical'),
            'stroke_count': extra.get('stroke_count'),
            'decomposition': table[char][0],
            'source': SOURCE,
            'licence': LICENCE,
        })
    logger.info('Built %d rows with at least one discriminating component', len(rows))
    return rows


def upload(db, rows: list) -> int:
    written = 0
    for start in range(0, len(rows), BATCH):
        chunk = rows[start:start + BATCH]
        db.table('dim_character_components').upsert(
            chunk, on_conflict='character',
        ).execute()
        written += len(chunk)
        if written % (BATCH * 10) == 0 or written == len(rows):
            logger.info('  upserted %d/%d', written, len(rows))
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--dry-run', action='store_true',
                        help='build and report, write nothing')
    parser.add_argument('--max-depth', type=int, default=DEFAULT_MAX_DEPTH,
                        help='recursion depth through real characters (default: %(default)s)')
    parser.add_argument('--max-component-share', type=float,
                        default=DEFAULT_MAX_COMPONENT_SHARE,
                        help='drop components in more than this share of characters '
                             '(default: %(default)s)')
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    load_dotenv()

    rows = build_rows(max_depth=args.max_depth,
                      max_component_share=args.max_component_share)
    if not rows:
        logger.error('No rows built — refusing to continue')
        return 1

    by_char = {r['character']: r for r in rows}
    for char in ('掌', '章', '张', '請', '晴'):
        row = by_char.get(char)
        if row:
            logger.info('  %s -> %s (radical=%s strokes=%s)',
                        char, ''.join(row['components']),
                        row['radical'], row['stroke_count'])

    if args.dry_run:
        print(f'dry-run: {len(rows)} rows would be upserted')
        print(f'source:  {SOURCE}')
        print(f'licence: {LICENCE}')
        return 0

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    written = upload(get_supabase_admin(), rows)
    print(f'upserted: {written}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
