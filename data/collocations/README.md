# Bundled collocation frequency lists

Source data for `services/vocabulary_ladder/collocation_grounding.py` (TASK-523).

These lists answer one question: **is the `primary_collocate` that Prompt 1
asserted for a sense actually an attested pairing in the language?** They are
not used to *generate* anything — only to tag a pair `corpus_validated` or
`llm_asserted` so the L5/L8 corpus can be reported on and, over time, trimmed.

---

## Format

Tab-separated, UTF-8, one pair per line. Lines starting with `#` and a leading
`head` header row are ignored.

```
head	collocate	frequency	relation
make	decision	48213	verb_object
strong	coffee	9042	adjective_noun
```

| Column      | Meaning                                                          |
|-------------|------------------------------------------------------------------|
| `head`      | the content word                                                  |
| `collocate` | its partner                                                       |
| `frequency` | raw co-occurrence count in the source corpus (integer)            |
| `relation`  | optional grammatical relation label; recorded but not read        |

Pairs are indexed **unordered** — the loader normalises `(a, b)` and `(b, a)`
to the same key, because Prompt 1 does not tell us which side is the head.

Pairs below `MIN_LIST_FREQUENCY` (currently 5) are ignored at lookup time:
a long-tail count is an artefact of whichever corpus the list was built from,
not something to teach.

---

## Files

| Language | Filename              | Status                                    |
|----------|-----------------------|-------------------------------------------|
| English  | `en_collocations.tsv` | **not vendored** — see "Installing" below |
| Chinese  | —                     | uses `corpus_collocations` (PMI ≥ 5)      |
| Japanese | —                     | deferred, no source (TASK-523 scope note) |

A missing file is a supported state, not an error: the grounder logs once and
falls through to `corpus_collocations`, which is exactly the behaviour that
existed before this module. Nothing fails to generate because a list is absent.

---

## Installing the English list

The list is **not committed to this repository**. It is tens of megabytes of
third-party corpus derivative, it changes rarely, and vendoring it would put a
large blob into every clone for a feature that degrades gracefully without it.

### Recommended source

**Open American National Corpus (OANC)** — public domain, no attribution
required, no redistribution restrictions.

- Home: <https://anc.org/data/oanc/>
- Licence: public domain (the OANC is released with no restrictions on use,
  modification or redistribution)
- Size: ~15M words of contemporary written and spoken American English

Extract bigram counts filtered to content-word pairs, then write them in the
format above. Any equivalent openly-licensed source works — the loader only
cares about the columns.

### Alternatives, with the licence caveat that rules each out or in

| Source | Licence | Usable? |
|--------|---------|---------|
| OANC | Public domain | **Yes** — recommended |
| Google Books Ngrams | CC BY 3.0 | Yes, with attribution; very large, heavily skewed to books |
| COCA / BNC collocate lists | Commercial / academic licence | **No** — redistribution restricted |
| Oxford Collocations Dictionary | Proprietary | **No** |
| Wiktionary derivatives | CC BY-SA 3.0 | Yes, with share-alike; coverage is thin for collocations |

Do not drop a COCA or Oxford-derived list in here. The licence would follow the
file into the repository and out to every deployment.

### Where to put it

```
data/collocations/en_collocations.tsv
```

Then confirm it is being read:

```bash
PYTHONPATH=. python -c "
from services.vocabulary_ladder.collocation_grounding import bundled_list
print(len(bundled_list(2).pairs), 'pairs loaded')
"
```

---

## Checking coverage

`scripts/validate_collocates.py` grades every generated sense's collocate and
reports the validated share per language:

```bash
PYTHONPATH=. python scripts/validate_collocates.py --language en --dry-run
```

Japanese reports as *unmeasured* rather than 0% — `no_source` and
`llm_asserted` are deliberately different tags. See the module docstring in
`collocation_grounding.py` for why.
