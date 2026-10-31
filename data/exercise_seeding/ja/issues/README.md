# JA fat-seed data issues (to fix later)

## 1. Corpus sentences tagged to the wrong sense — `corpus_wrong_sense.csv`

Mined (corpus) sentences that reviewers could not edit but flagged in their
notes: the target is used in a different sense, only inside a compound
(根源的, 食生活, 遊び小屋), as a prefix (数- in 数日), or the sentence drifts
from the sense / sits far above the learner tier.

- Built by `scratch_offline/collect_issues.py` from every
  `*/fat_seed/review/*.json` whose notes mention mined/corpus sentences together
  with a sense/compound/prefix problem. Re-run it after new reviews.
- Heuristic: a few rows only complain about tier or naturalness — check
  `reviewer_note` before acting.
- Columns: `sense_id, lemma, run, verdict, mined_sentences, reviewer_note`.
  `mined_sentences` lists the brief's mined sentences with their index; the
  note says which index is wrong.
- Fix: re-link those sentences (and their source tests' `vocab_sense_ids`) to
  the correct sense, or drop the link; then re-author the affected senses.

## 2. Suspect senses (not real standalone senses)

| sense_id | lemma | problem | status |
|---|---|---|---|
| 52225 | サワー | "sour taste" used standalone (サワーが強い, サワーな味) is unnatural; the meaning only occurs inside compounds (サワークリーム). Rejected in review (wf2/r0016). | investigate: delete or redefine |
| 52226 | サワー | same as 52225 | investigate: delete or redefine |

Related, also to check: 51993 (挑む) — definition does not match its own
`sense_fingerprint` ("challenge an opponent to a match") and reads like
sense 51994.

## 3. level_1 listening — too few one-mora neighbours

Forced distractors kept only to satisfy `check`; the live judge will likely drop
level_1 for: 鶏 (42822), 僅か (42853), クレヨン (51783, 51784),
力強い (51801, 51802), 広がる, 読み書き. Proposed fix: allow a formal
`no_minimal_pairs` decline for level_1 (needs `fat_seed.py` + `validators.py`).

## Rejected senses (production run, Oct 2026)

`rejected_senses.csv` lists the 293 senses whose core the reviewer rejected
(no assets were produced for them): 192 duplicate a sibling sense of the same
lemma, 24 have a definition that does not match the usage, 10 a wrong
headword / POS / reading, 67 other. These are dictionary-data problems:
regenerating will not fix them. Merge, correct or quarantine
(`calibration_anchor_blocklist`) as appropriate.
