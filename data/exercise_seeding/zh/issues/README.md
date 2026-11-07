# zh fat-seed issues (interim, runs finished by 2026-11-07)

Senses from the zh fat-seed pipeline (`data/exercise_seeding/zh/wf2`) that produced no word assets.
Both lists are dictionary-data problems: regenerating does not fix them.

- `skipped_senses.csv`: the author declined to write the sense. `category` is a keyword grouping of `author_reason`:
  - `bound_morpheme_fragment`: a character that does not stand alone at the learner tier (率, 视, 谱).
  - `proper_noun`: place, person or organisation names.
  - `mined_sentence_wrong_sense`: the mined corpus sentences use another sense, or only a compound.
  - `not_a_word`: a segmentation artifact or free phrase in `dim_vocabulary` (厨余会, 天上飞).
  - `other`: read the reason.
- `rejected_senses.csv`: the reviewer rejected the core (duplicate sibling sense, definition ≠ usage, wrong POS).
  Its notes and issues say why.

Covers only the 900 runs that had finished when the pipeline was paused. The rest are added when it completes.
