"""Generic phonetic trie: build once, query for near-homophones.

See ``.claude/reviews/l1-phonetic-trie-architecture.md`` §1 for the design
this implements verbatim. The trie is over sequences of arbitrary hashable
"units" — a ja mora, a zh (initial, final, tone) triple, an en ARPAbet
phoneme — so this module has no language-specific knowledge at all; that
lives in the per-language sibling modules (``ja_mora.py``, etc.).

Two queries matter:

* ``exact_matches`` — every other spelling sharing a target's *exact* unit
  sequence (0-substitution, i.e. true homophones).
* ``one_substitution_neighbors`` — every real word exactly one unit away
  from a target, found by walking the target's own shared prefix and
  looking sideways at the trie's other branches at each position. This is
  the mechanism that makes a same-reading pair (accent-only collisions like
  機械/機会) structurally unreachable: a "neighbor" is only ever produced
  when exactly one unit differs, so the target's own unchanged reading is
  never itself proposed back as a candidate.

Kept dependency-free on purpose — plain Python, no third-party trie
library — because the whole point is that nothing downstream of this
module can return a spelling that wasn't actually inserted from the source
dictionary. A fabricated candidate has no path to the output.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from typing import Hashable, Iterable, Iterator, Sequence


class _TrieNode:
    """One node. ``surface_forms is None`` means "not a word end" —
    distinct from an empty list, which would mean a dead-end word whose
    spellings were all filtered out (shouldn't happen, but the distinction
    costs nothing and self-documents `is_word_end`).
    """

    __slots__ = ("children", "surface_forms")

    def __init__(self) -> None:
        self.children: dict[Hashable, "_TrieNode"] = {}
        self.surface_forms: list[str] | None = None

    @property
    def is_word_end(self) -> bool:
        return self.surface_forms is not None


@dataclass(frozen=True)
class Neighbor:
    """One one-substitution neighbor, with the substitution that produced it.

    The (position, original_unit, substituted_unit) triple is exactly the
    content a templated explanation needs ("differs at mora 2: し→え") —
    per the architecture doc §5, this is free from the trie walk, not
    something a model has to reconstruct after the fact.
    """

    surface_form: str
    position: int
    original_unit: Hashable
    substituted_unit: Hashable


class PhoneticTrie:
    """A trie over sequences of hashable phonetic units.

    Usage::

        trie = PhoneticTrie()
        trie.build(entries)                      # entries: (units, surface_form) pairs
        trie.one_substitution_neighbors(target_units)
        trie.exact_matches(target_units)
    """

    def __init__(self) -> None:
        self._root = _TrieNode()
        self.entry_count = 0   # number of (units, surface_form) pairs inserted
        self.node_count = 1    # includes the root

    # -- building ----------------------------------------------------

    def insert(self, units: Sequence[Hashable], surface_form: str) -> None:
        node = self._root
        for unit in units:
            child = node.children.get(unit)
            if child is None:
                child = _TrieNode()
                node.children[unit] = child
                self.node_count += 1
            node = child
        if node.surface_forms is None:
            node.surface_forms = []
        if surface_form not in node.surface_forms:
            node.surface_forms.append(surface_form)
        self.entry_count += 1

    def build(self, entries: Iterable[tuple[Sequence[Hashable], str]]) -> "PhoneticTrie":
        for units, surface_form in entries:
            self.insert(units, surface_form)
        return self

    # -- querying ------------------------------------------------------

    def _walk(self, node: _TrieNode, units: Sequence[Hashable]) -> _TrieNode | None:
        for unit in units:
            node = node.children.get(unit)
            if node is None:
                return None
        return node

    def exact_matches(self, units: Sequence[Hashable]) -> list[str]:
        """Every surface form sharing this exact unit sequence.

        This is the 0-substitution query — same-pronunciation alternates
        (true homophones). Callers that don't want true homophones (ja, zh
        per the architecture doc's per-language decisions) simply don't
        call this; the trie itself takes no position on that policy.
        """
        node = self._walk(self._root, units)
        if node is None or node.surface_forms is None:
            return []
        return list(node.surface_forms)

    def one_substitution_neighbors(self, units: Sequence[Hashable]) -> list[Neighbor]:
        """Every real word exactly one unit away from ``units``.

        For each position i: walk the shared prefix ``units[:i]`` (unchanged
        so far), then at that node try every child unit other than
        ``units[i]``, then walk the remaining suffix ``units[i+1:]`` from
        there. Landing on a word-end node means every surface form there is
        a genuine one-substitution neighbor — tagged with exactly which
        position changed and how.

        If the prefix of length i isn't in the trie at all, no longer
        prefix can be either (a trie node at depth i+1 requires the depth-i
        node on the same path to exist first), so the loop stops rather
        than continuing to fail silently at every later position.
        """
        results: list[Neighbor] = []
        n = len(units)
        for i in range(n):
            prefix_node = self._walk(self._root, units[:i])
            if prefix_node is None:
                break
            target_unit = units[i]
            suffix = units[i + 1:]
            for candidate_unit, child in prefix_node.children.items():
                if candidate_unit == target_unit:
                    continue
                end_node = self._walk(child, suffix)
                if end_node is not None and end_node.surface_forms:
                    for surface in end_node.surface_forms:
                        results.append(Neighbor(
                            surface_form=surface,
                            position=i,
                            original_unit=target_unit,
                            substituted_unit=candidate_unit,
                        ))
        return results

    def same_node(self, units_a: Sequence[Hashable], units_b: Sequence[Hashable]) -> bool:
        """Whether two unit sequences resolve to the exact same trie node.

        Two different real words can share a surface form's *text* without
        sharing a reading (a headword can have more than one recorded
        pronunciation) — that's a legitimate, separate phenomenon, not a
        same-reading collision. This checks the thing the architecture doc
        actually claims is structurally impossible: that a
        one-substitution query ever resolves to the *identical* node
        (i.e. the identical full unit sequence) it started from.
        """
        node_a = self._walk(self._root, units_a)
        node_b = self._walk(self._root, units_b)
        return node_a is not None and node_a is node_b

    def iter_entries(self) -> Iterator[tuple[list[Hashable], list[str]]]:
        """Depth-first walk of every word-end node: ``(unit_path, surface_forms)``.

        Not needed for the hot query path — for build-time stats and
        validation (e.g. sampling real homophone clusters directly out of
        the built trie, rather than only hand-picked cases) without a
        second parallel index.
        """
        stack: list[tuple[_TrieNode, list[Hashable]]] = [(self._root, [])]
        while stack:
            node, path = stack.pop()
            if node.surface_forms is not None:
                yield list(path), list(node.surface_forms)
            for unit, child in node.children.items():
                stack.append((child, path + [unit]))

    # -- persistence -----------------------------------------------------
    # Pickle, not msgpack: the trie is a graph of Python objects with
    # shared/cyclic-shaped references-by-key (not a flat records format),
    # which is exactly what pickle is for and what msgpack is not designed
    # to serialize without first flattening the tree into some intermediate
    # records shape. There's no cross-language or cross-process-version
    # consumer of this artifact (it's read back by the same Python codebase
    # that wrote it), so pickle's usual portability caveat doesn't apply.

    def save(self, path: str) -> None:
        with open(path, "wb") as fh:
            pickle.dump(self, fh, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(path: str) -> "PhoneticTrie":
        with open(path, "rb") as fh:
            trie = pickle.load(fh)
        if not isinstance(trie, PhoneticTrie):
            raise TypeError(f"{path} does not contain a PhoneticTrie")
        return trie
