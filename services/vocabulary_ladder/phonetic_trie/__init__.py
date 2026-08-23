"""Build-once phonetic tries for L1 distractor lookup.

See .claude/reviews/l1-phonetic-trie-architecture.md for the design this
package implements. ``trie.py`` is the generic, language-agnostic data
structure; each ``<lang>_<unit>.py`` module supplies the tokenizer and
dictionary reader for one language's phonetic unit (ja morae, zh
initial/final/tone syllables, en ARPAbet phonemes).
"""
