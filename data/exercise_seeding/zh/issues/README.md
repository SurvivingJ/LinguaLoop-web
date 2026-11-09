# zh fat-seed issues (final, 2026-11-09)

Senses from the zh fat-seed pipeline that are not in the upload package, with the reason.
Totals over the 19,233 exported senses: 16,342 packaged, 805 skipped, 1,851 rejected, 235 not packaged.

- `skipped_senses.csv` (805): the author declined to write the sense. `category` groups `author_reason`:
  - `bound_morpheme_fragment` (681): a character that does not stand alone at the learner tier (率, 视, 谱).
  - `proper_noun` (48): place, person or organisation names.
  - `mined_sentence_wrong_sense` (42): the mined corpus sentences use another sense, or only a compound.
  - `not_a_word` (19): a segmentation artifact or free phrase in `dim_vocabulary` (厨余会, 天上飞).
  - `other` (15): read the reason.
- `rejected_senses.csv` (1,851): a reviewer rejected the core. `rejected_by` is the first-pass Haiku review (1,498)
  or the Opus second review (353). Typical causes: duplicate sibling senses, definition ≠ usage, wrong POS.
  These are dictionary-data problems: regenerating does not fix them.
- `not_packaged_senses.csv` (235): documents that did not pass the final validation check
  (147 after the Opus second review, 88 after the first pass). Their first-pass versions in `wf2/` may still be
  valid; re-review or re-author them to recover them.
