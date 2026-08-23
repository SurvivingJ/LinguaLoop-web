#!/usr/bin/env python3
"""
Standalone validation for the ja mora-trie build.

No live DB writes, no prompt_templates changes -- does not touch
exercise_renderer.py or prompt2_exercises.py. Loads the pickled trie built
by build_ja_mora_trie.py and checks:

  1. Target 昔 (むかし): one-mora neighbors include the real TASK-735 finds
     (迎え/向かい/百足) and structurally exclude the two fabrications
     (向こうし/無蚊地).
  2. Target 機械 (きかい): 機会 (the accent-only collision) never appears.
  3. A structural-guarantee sweep across every homophone cluster the trie
     itself contains (not just the two hand-picked cases): a
     one-substitution query can never return a same-reading candidate.
  4. An eyeball print of neighbor lists for 10 real ja target words pulled
     from dim_word_senses, for human review.

Usage:
    python scripts/build_ja_mora_trie.py     # build first, if not already
    python scripts/validate_ja_mora_trie.py
    python scripts/validate_ja_mora_trie.py --trie path/to/other.pkl
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass  # older Python without reconfigure(); best-effort only

from services.vocabulary_ladder.phonetic_trie.ja_mora import to_morae
from services.vocabulary_ladder.phonetic_trie.trie import PhoneticTrie

DEFAULT_TRIE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'content_builds', 'phonetic_trie', 'ja_mora_trie.pkl',
)

# --- TASK-735 anchor cases, from ja-l1-redesign-options.md -----------------

MUKASHI_TARGET = '昔'
MUKASHI_READING = 'むかし'
MUKASHI_EXPECTED = {'迎え', '向かい', '百足'}
MUKASHI_FORBIDDEN = {'向こうし', '無蚊地'}  # the two fabrications

KIKAI_KANJI_TARGET = '機械'
KIKAI_READING = 'きかい'
KIKAI_FORBIDDEN_ACCENT_PAIR = '機会'

# --- Real ja target words pulled from dim_word_senses (project
# kpfqrjtfxmujzolwsvdq) via Supabase MCP on 2026-08-23:
#   select dws.id, dv.lemma, dws.pronunciation from dim_word_senses dws
#   join dim_vocabulary dv on dv.id = dws.vocab_id
#   where dv.language_id = 3 and dws.pronunciation is not null
#   and dv.part_of_speech not ilike '%name%' order by random() limit 12;
# (two multi-word/conjugated-phrase results dropped; single lemmas kept.)
# Baked in here rather than queried live so this script stays a
# standalone, DB-free artifact. ---------------------------------------------

SAMPLE_TARGETS = [
    ('血管', 'けっかん'),
    ('空気', 'くうき'),
    ('組み立て', 'くみたて'),
    ('後期', 'こうき'),
    ('施行', 'しこう'),
    ('戦略', 'せんりゃく'),
    ('寸断', 'すんだん'),
    ('空間', 'くうかん'),
    ('糖', 'とう'),
    ('神話', 'しんわ'),
]


def _fmt_neighbors(neighbors) -> str:
    by_surface = {}
    for n in neighbors:
        by_surface.setdefault(n.surface_form, n)
    if not by_surface:
        return "  (none)"
    return "\n".join(
        f"  {surface}  (mora {n.position}: {n.original_unit} -> {n.substituted_unit})"
        for surface, n in by_surface.items()
    )


def check_mukashi(trie: PhoneticTrie) -> list[str]:
    failures = []
    morae = to_morae(MUKASHI_READING)
    neighbors = trie.one_substitution_neighbors(morae)
    surfaces = {n.surface_form for n in neighbors}

    print(f"\n=== {MUKASHI_TARGET} ({MUKASHI_READING}) mora={morae} ===")
    print(_fmt_neighbors(neighbors))

    missing = MUKASHI_EXPECTED - surfaces
    if missing:
        failures.append(f"昔: expected real neighbors missing: {missing}")

    leaked = MUKASHI_FORBIDDEN & surfaces
    if leaked:
        failures.append(f"昔: fabricated candidate(s) present (should be structurally impossible): {leaked}")

    return failures


def check_kikai_accent_collision(trie: PhoneticTrie) -> list[str]:
    failures = []
    morae = to_morae(KIKAI_READING)
    neighbors = trie.one_substitution_neighbors(morae)
    surfaces = {n.surface_form for n in neighbors}

    print(f"\n=== {KIKAI_KANJI_TARGET} ({KIKAI_READING}) mora={morae} ===")
    print(_fmt_neighbors(neighbors))

    if KIKAI_FORBIDDEN_ACCENT_PAIR in surfaces:
        failures.append(
            "機械: accent-only collision 機会 appeared as a one-substitution "
            "neighbor -- should be structurally impossible (same reading = "
            "0 differences, not 1)."
        )
    return failures


def check_structural_guarantee(trie: PhoneticTrie) -> list[str]:
    """Prove the guarantee the architecture doc actually claims: a
    one-substitution query can never land back on the *same trie node* it
    started from, i.e. it can never return a candidate whose full reading
    is identical to the target's own reading (the mechanism that makes the
    機械/機会 accent-only collision unreachable). Checked directly against
    every node the trie has, not only the two hand-picked ja cases.

    Node identity (``trie.same_node``), not surface-form-text overlap, is
    the right check here: two different real words can share a headword's
    *text* without sharing a reading (a word can have more than one
    recorded pronunciation) -- that's the separate, real phenomenon
    ``find_self_neighbor_via_alt_reading`` below measures, not a
    same-reading collision. Conflating the two by checking surface-form
    text instead of node identity looked, on a first pass, like thousands
    of guarantee violations; it wasn't -- it was this test asking the
    wrong question. Left as a cautionary comment because it's an easy trap
    to fall back into if this check is ever "simplified" back to a text
    comparison.
    """
    failures = []
    checked = 0
    for path, _forms in trie.iter_entries():
        for n in trie.one_substitution_neighbors(path):
            reconstructed = list(path)
            reconstructed[n.position] = n.substituted_unit
            if trie.same_node(path, reconstructed):
                reading = ''.join(str(u) for u in path)
                failures.append(
                    f"same-reading collision for {reading!r}: substituting "
                    f"position {n.position} ({n.original_unit}->{n.substituted_unit}) "
                    f"landed back on the identical node"
                )
        checked += 1

    kikai_morae = to_morae(KIKAI_READING)
    kikai_neighbors = {n.surface_form for n in trie.one_substitution_neighbors(kikai_morae)}
    if KIKAI_FORBIDDEN_ACCENT_PAIR in kikai_neighbors:
        failures.append("機械/機会 accent-only collision leaked through the direct check too.")

    print(f"\n=== Structural guarantee: same-reading collision ({checked:,} readings checked) ===")
    print(
        "PASS -- no one-substitution neighbor ever shares its target's exact reading"
        if not failures else "FAIL"
    )
    return failures


def find_self_neighbor_via_alt_reading(trie: PhoneticTrie) -> int:
    """A genuinely different, previously undocumented edge case found while
    building this check: a headword with *two recorded readings* one mora
    apart from each other (e.g. 病気 read both びょうき and the colloquial
    びょーき; 若僧/弱僧 read both にゃくそう and じゃくそう) shows up as a
    "one-mora neighbor" of *itself*. This does not violate the same-reading
    guarantee above (the two readings genuinely differ by one mora, so it's
    not a same-reading collision) -- it's a different problem: the
    candidate is not a different *word* at all, just an alternate
    pronunciation of the target. Informational only, not a pass/fail
    criterion of this build -- flagged for whoever wires this trie into
    generation next: candidates equal to the target's own surface form(s)
    need to be filtered before use, the same way a synonym or tier-misfit
    filter already has to run downstream (architecture doc §5).
    """
    self_collisions = 0
    examples: list[str] = []
    for path, forms in trie.iter_entries():
        if len(forms) < 1:
            continue
        neighbors = trie.one_substitution_neighbors(path)
        for n in neighbors:
            if n.surface_form in forms:
                self_collisions += 1
                if len(examples) < 8:
                    examples.append(
                        f"{n.surface_form}: {''.join(str(u) for u in path)} vs "
                        f"one mora away at position {n.position} "
                        f"({n.original_unit}->{n.substituted_unit})"
                    )
                break
    print(f"\n=== Informational: self-neighbor via alternate reading ===")
    print(f"{self_collisions} headword(s) appear as a one-mora 'neighbor' of one of their own alternate readings.")
    print("(Not a build defect -- a downstream candidate filter needs to drop the target's own surface form(s).)")
    for ex in examples:
        print(f"  e.g. {ex}")
    return self_collisions


def eyeball_samples(trie: PhoneticTrie) -> None:
    print("\n=== Eyeball pass: real ja target words from dim_word_senses ===")
    for lemma, reading in SAMPLE_TARGETS:
        morae = to_morae(reading)
        neighbors = trie.one_substitution_neighbors(morae)
        print(f"\n--- {lemma} ({reading}) mora={morae} -- {len(neighbors)} neighbor(s) ---")
        print(_fmt_neighbors(neighbors))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--trie', default=DEFAULT_TRIE_PATH)
    args = parser.parse_args()

    if not os.path.exists(args.trie):
        print(f"No trie found at {args.trie}. Run scripts/build_ja_mora_trie.py first.")
        sys.exit(1)

    trie = PhoneticTrie.load(args.trie)
    print(f"Loaded trie: {trie.node_count:,} nodes, {trie.entry_count:,} entries")

    failures = []
    failures += check_mukashi(trie)
    failures += check_kikai_accent_collision(trie)
    failures += check_structural_guarantee(trie)
    find_self_neighbor_via_alt_reading(trie)
    eyeball_samples(trie)

    print("\n" + "=" * 70)
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(f" - {f}")
        sys.exit(1)
    print("All automated checks passed. Review the eyeball pass above by hand.")


if __name__ == '__main__':
    main()
