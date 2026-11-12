# data/lexicon

## cc_cedict_headwords.txt.gz
Multi-character headwords (simplified and traditional) from **CC-CEDICT**,
MDBG edition dated 2023-11-07 (122,143 entries), one per line after a short
`#` header. Used by `services/vocabulary/zh_segmenter.py` to decide whether a
word jieba *guessed* (its HMM unknown-word mode) is a real word before it can
become vocabulary.

- Source: CC-CEDICT, published by MDBG — https://www.mdbg.net/chinese/dictionary?page=cc-cedict
  (taken from the copy bundled in the `pycccedict` 1.2.0 package on PyPI,
  because mdbg.net is not reachable from the build sandbox).
- Referenced work: CEDICT, Copyright (C) 1997, 1998 Paul Andrew Denisowski.
- **Licence: Creative Commons Attribution-ShareAlike 4.0 International**
  (https://creativecommons.org/licenses/by-sa/4.0/). This derived word list is
  shared under the same licence. Keep this attribution with it; if the list is
  ever redistributed (for example in an app download), it stays CC BY-SA.

To refresh: download the current CC-CEDICT export from MDBG and rebuild the
list the same way (every simplified and traditional headword of two or more
characters).

## zh_extra_words.txt
Real Chinese words missing from CC-CEDICT (newer terms such as 产消者 or 禁塑)
that were reviewed and accepted, so jieba's guess is kept for them. One word
per line; `#` comments allowed. Written by the 2026-11-12 review of the
dictionary words jieba guessed (`data/zh_segmentation/`).
