#!/usr/bin/env python3
"""
Build the ja mora-trie L1 distractor lookup.

See .claude/reviews/l1-phonetic-trie-architecture.md (§2 ja-specific, §6
storage) for the design. This script:

  1. Downloads (if missing) the latest JMdict-simplified "eng" release --
     the ja headword/reading dictionary restricted to English glosses. We
     don't read the glosses at all; "eng" is simply the smallest
     JMdict-simplified flavour that isn't missing ja headwords the way
     "eng-common" would be (its common-words-only filter would silently
     drop exactly the kind of word TASK-735 needs as a distractor -- 迎え,
     向かい, 百足 are not "common" words, but they are real ones).
  2. Mora-tokenizes every reading (ja_mora.to_morae) and inserts
     (mora_sequence, surface_form) into a PhoneticTrie.
  3. Pickles the trie to a build artifact.

Neither the downloaded JMdict source nor the built trie is committed to
git -- see the .gitignore entries added alongside this script. That's a
deliberate departure from cedict_ts.u8 (which the classifier importer does
commit to raw/): cedict is ~9MB of source text, small enough that keeping
it avoids a network dependency at deploy time; the decompressed JMdict-eng
source is ~110MB and the built trie is itself a *derived* binary, not
source data -- more like the project's existing `build/` gitignore entry
than like `raw/cedict_ts.u8`. Both are one `python scripts/build_ja_mora_trie.py`
away from being regenerated, which is the same "rebuild on deploy" story
node_modules and build/ already have in this repo.

Usage:
    python scripts/build_ja_mora_trie.py                  # full build
    python scripts/build_ja_mora_trie.py --limit 5000      # fast smoke build
    python scripts/build_ja_mora_trie.py --force-download  # redownload JMdict
"""

import argparse
import json
import logging
import os
import sys
import tarfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vocabulary_ladder.phonetic_trie.ja_mora import iter_jmdict_entries
from services.vocabulary_ladder.phonetic_trie.trie import PhoneticTrie

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, 'raw')
JMDICT_PATH = os.path.join(RAW_DIR, 'jmdict_eng.json')
OUT_PATH = os.path.join(ROOT, 'data', 'content_builds', 'phonetic_trie', 'ja_mora_trie.pkl')

RELEASES_API = 'https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest'
ASSET_PREFIX = 'jmdict-eng-'
ASSET_SUFFIX = '.json.tgz'


def _latest_asset_url() -> str:
    req = urllib.request.Request(RELEASES_API, headers={'User-Agent': 'lingualoop-build-script'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        release = json.loads(resp.read().decode('utf-8'))
    for asset in release.get('assets', []):
        name = asset.get('name', '')
        if name.startswith(ASSET_PREFIX) and name.endswith(ASSET_SUFFIX):
            return asset['browser_download_url']
    raise RuntimeError(
        f"No {ASSET_PREFIX}*{ASSET_SUFFIX} asset found in the latest "
        f"jmdict-simplified release -- check {RELEASES_API} by hand."
    )


def _ensure_jmdict_file(force: bool = False) -> str:
    """Download + extract JMdict-simplified (eng) to raw/jmdict_eng.json."""
    if os.path.exists(JMDICT_PATH) and not force:
        return JMDICT_PATH
    os.makedirs(RAW_DIR, exist_ok=True)
    url = _latest_asset_url()
    tgz_path = JMDICT_PATH + '.tgz'
    logger.info(f"Downloading JMdict-simplified (eng) from {url} ...")
    urllib.request.urlretrieve(url, tgz_path)
    logger.info("Extracting...")
    with tarfile.open(tgz_path, 'r:gz') as tar:
        members = [m for m in tar.getmembers() if m.name.endswith('.json')]
        if not members:
            raise RuntimeError("No .json member found in the JMdict-simplified tarball")
        member = members[0]
        member.name = os.path.basename(member.name)  # strip any leading dirs
        tar.extract(member, path=RAW_DIR)
        extracted_path = os.path.join(RAW_DIR, member.name)
    if os.path.abspath(extracted_path) != os.path.abspath(JMDICT_PATH):
        os.replace(extracted_path, JMDICT_PATH)
    os.remove(tgz_path)
    logger.info(f"JMdict-simplified ready at {JMDICT_PATH}")
    return JMDICT_PATH


def build(limit: int | None = None) -> PhoneticTrie:
    path = _ensure_jmdict_file()
    trie = PhoneticTrie()
    count = 0
    for morae, spelling, _reading in iter_jmdict_entries(path):
        trie.insert(morae, spelling)
        count += 1
        if limit and count >= limit:
            break
    return trie


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--limit', type=int, default=None,
        help='Stop after N (mora_sequence, spelling) inserts -- for a fast smoke build.',
    )
    parser.add_argument(
        '--force-download', action='store_true',
        help='Redownload JMdict-simplified even if raw/jmdict_eng.json already exists.',
    )
    parser.add_argument('--out', default=OUT_PATH, help='Output pickle path.')
    args = parser.parse_args()

    if args.force_download:
        _ensure_jmdict_file(force=True)

    t0 = time.monotonic()
    trie = build(limit=args.limit)
    elapsed = time.monotonic() - t0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    trie.save(args.out)
    size_bytes = os.path.getsize(args.out)

    logger.info(f"Built trie: {trie.node_count:,} nodes, {trie.entry_count:,} entries, {elapsed:.1f}s")
    logger.info(f"Saved to {args.out} ({size_bytes / 1e6:.1f} MB)")


if __name__ == '__main__':
    main()
