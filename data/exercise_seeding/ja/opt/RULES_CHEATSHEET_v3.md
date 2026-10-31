# Fat-seed JA authoring cheat sheet

Condensed from the live prompts (`rules_core.md`, `rules_exercises.md` in each
run). Read this instead of them; open the full file only to settle a doubt.
Block shapes: `.claude/skills/fat-seed-authoring/SKILL.md` → "Block reference".

## Core (one sense)
- Pin ONE sense (the given definition). Every sentence uses the target as an
  independent word in that sense. Reject: target inside a compound
  (作者 for 者, 消費者 for 消費), homographs (着る for 来る), other readings.
- Exactly 10 sentences. Mined sentences first, byte-for-byte; write the rest.
- Tier limits (max chars / grammar): T1 10 plain · T2 16 です/ます+た ·
  T3 22 て形/ている/可能 · T4 30 passive/causative/conditional · T5 40 · T6 any.
- Target in ≥3 syntactic roles; no structure more than 4 times.
- `target_word` = exact surface in the sentence (full inflected form, e.g.
  高かった not 高か).
- pos ∈ the POS set in the brief; semantic_class ∈ concrete/abstract/action/
  property/function/proper. register ∈ plain/polite/honorific/humble/formal/casual.
- primary_collocate: null unless swapping the partner for a synonym sounds
  wrong (水を飲む). When in doubt, null.
- morphological_forms 3–5, labels 助数詞/活用/派生/敬語形. Only REAL forms of
  this word (no 関数 for 変数, no fake 「つ」 counters). Empty list if none.
- pronunciation hiragana; syllable_count = morae; fingerprint "品詞 | 10–18字".

## Exercises (A and B written independently — every block)
B is never A re-worded. For EVERY block (level_3, level_4, level_5, level_8,
synonym_antonym_match, particle_selection, level_6, level_7): B's distractors
share NO word with A's, B's wrong sentences and level_7 sentences are new.
Write all of A, then write B as if you had never seen A.
- **level_3 cloze**: correct = form in the anchor sentence. 3 distractors,
  same POS, grammatical in the slot but wrong in meaning. Read each one in the
  blank — if any sounds natural, replace it. No sound-alikes. Each
  explanation is SPECIFIC: say what the distractor means and why that meaning
  clashes with this sentence (e.g. 「捨てる」は手放す意味で、音楽を愛する文脈に合わない).
  Never a generic line such as 「形は合うが意味が合わない」 or 「意味が合わない」.
- **level_5 collocation gap**: correct = collocate; distractors near in
  meaning but unidiomatic with the target.
- **level_6 semantic discrimination**: 3 wrong sentences that MISUSE THE
  TARGET (wrong sense, wrong collocation, wrong particle with it). Not
  tense clashes (明日…た), counters, word order or errors elsewhere. Each must
  be clearly wrong; exactly one error. Wrong in MEANING, grammatical in FORM:
  no bad inflection (凛とに, 弾力な, 本来な) — that is level_4's job.
  NEVER jumbled/random word salad. Each
  wrong sentence gets its OWN explanation naming how the target is misused
  (no shared generic line).
- **level_7 spot incorrect**: write a BRAND-NEW sentence (not a core
  sentence, not a core sentence with one word changed: the corrected
  sentence must not equal any core sentence either, or the item gives its
  answer away). Exactly ONE error, and the error is ON THE TARGET: its
  particle, its inflection, its collocate or its sense. A particle error on
  some other noun does not count. corrected_sentence = the same sentence
  with only that error fixed.
- **level_4 morphology**: correct = the form in the anchor; distractors =
  real forms of the SAME word that clearly fail in the slot.
- **level_8 collocation repair**: correct = collocate; error_collocate is
  planted, not among options.
- **synonym_antonym_match**: the relation must hold for THIS sense;
  distractors must not hold it for any other sense. Decline `no_relation` if
  there is no clean one.
- **particle_selection**: blank a particle that occurs in the anchor and
  relates to the target. Distractors must be clearly ungrammatical there
  (に/へ, は/が often both work — avoid; も fits almost any は/が/を slot —
  never use it as a distractor there). Read the sentence aloud with each
  distractor; if it is grammatical with any meaning, replace it. Decline
  `no_particle_slot` if none.
- **Mined sentence in the wrong sense / prefix use** (数- in 数日): never
  anchor a block on it; anchor on a written sentence instead.
- Explanations: one short Japanese sentence per option, true for THIS anchor.
