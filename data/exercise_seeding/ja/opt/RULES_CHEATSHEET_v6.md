# Fat-seed JA authoring cheat sheet (v6, author-side)

Condensed from the live prompts (`rules_core.md`, `rules_exercises.md` in each
run) and from what reviewers reject most often. Block shapes:
`.claude/skills/fat-seed-authoring/SKILL.md` → "Block reference".

## Core (one sense)
- Pin ONE sense: the given definition. `definition` = the given definition
  (polish wording only; never change its meaning, never invent a new one).
  `sense_fingerprint` must agree with it. Every sentence uses the target as an
  independent word in THAT sense: not inside a compound (作者 for 者, プリント技法
  for the product sense of プリント), not a homograph (着る for 来る), not a
  neighbouring sense (「グラフィックの仕事」= the design field, not an image).
- Exactly 10 sentences. Mined sentences first, byte-for-byte; write the rest.
- Every core sentence is later shown to learners as a model of correct use
  (level_6 correct sentence, level_7 correct sentences, cloze anchors), so
  each one must be flawless and idiomatic on its own.
- Code later blanks the target out of these sentences for cloze items, so
  each written sentence must carry a context cue that makes the target the
  only natural word in its slot: a reason, result or contrast clause. 「祖母は
  この歌をずっと愛していた」 lets 嫌っていた／歌っていた fill the blank; 「祖母は
  この歌を愛していて、毎晩口ずさんでいた」 does not. A bare 「Xを[target]た」
  sentence with no cue is a defect waiting to happen.
- Written sentences are natural, specific Japanese a native speaker would say:
  a clear referent (whose colours? which print?), no tautology (色数を数える),
  no redundancy (休みが取れるのに休暇を), standard orthography (絵の具, not 絵具).
- Tier limits (max chars / grammar): T1 10 plain · T2 16 です/ます+た ·
  T3 22 て形/ている/可能 · T4 30 passive/causative/conditional · T5 40 · T6 any.
  Keep all written sentences inside the tier; do not copy the length or
  abstraction of a long mined sentence.
- Register: pick ONE register for the sentences you write and declare it.
  plain = だ/る/た endings in every written sentence; polite = です/ます in every
  written sentence. Mixing です/ます sentences into a set declared `plain` is
  a defect. (A mined sentence may differ; that is accepted.)
- Target in ≥3 syntactic roles; no structure more than 4 times.
- `target_word` = exact surface in the sentence (full inflected form, e.g.
  高かった not 高か).
- pos ∈ the POS set in the brief; semantic_class ∈ concrete/abstract/action/
  property/function/proper. A verb of non-volitional change (褪せる, 枯れる)
  is `action` only if the brief's enum has nothing better; name it honestly.
- primary_collocate: null unless swapping the partner for a synonym sounds
  wrong (水を飲む, 敬意を払う). When in doubt, null.
- morphological_forms 3–5, labels 助数詞/活用/派生/敬語形. Only REAL inflections
  or derivations of THIS word in THIS sense: no compounds (プリントアウト), no
  different words (愛しい for 愛する), no fake 「つ」 counters. Empty list if none.
- pronunciation hiragana; syllable_count = number of morae: ッ, ン and ー each
  count 1, a small ゃ/ゅ/ょ/ぁ/ぃ/ぅ/ぇ/ぉ joins the previous mora
  (グラフィック = 5, グッズ = 3, ニュアンス = 4). ipa = real IPA, geminate as a
  doubled consonant (ɡɯddzɯ), never a placeholder letter such as Q.
- fingerprint "品詞 | 10–18字".

## Exercises — rules that apply to EVERY block
- Explanations are one short Japanese sentence, SPECIFIC and TRUE for this
  anchor: name what the option means and why that fails here
  (「捨てる」は手放す意味で、音楽を愛し続ける文脈に合わない). Never a generic line
  (「形は合うが意味が合わない」「意味が合わない」「文の意味に合わない」 alone is a
  defect). Never claim something false to make a distractor fail (煮た記憶 is
  grammatical; say the MEANING clashes). Never contradict the core definition.
- Distractors must be excluded only by someone who knows THIS word: same
  part of speech, same semantic domain, plausible-looking. 郵便局 for バンド or
  飲む for 愛する is useless because any reader excludes it without knowing
  the word. No two distractors that are near-synonyms (偶然 / たまたま).
- Read every option in the full sentence before you keep it. If the sentence
  is sayable with it — even with a different meaning — replace the option.
- All text in Japanese, including `error_tags`, `form_label`,
  `error_description`.

## A and B
A and B are two different exercises on the same sense, written as if by two
authors. Write all of A, then write B without reusing anything from A:
- B's distractors share NO word with A's in the same block (level_3, level_4,
  level_5, level_8, synonym_antonym_match, particle_selection).
- B's level_6 wrong sentences use different error types and different verbs
  or partner words than A's; B's level_7 plants a different error type.
- B's particle_selection blanks a different particle, or a different sentence
  position, with a different distractor set (not the same を/に/へ/が set).
A B that copies A, re-orders A, or rewrites A in kana/kanji is worse than none.

## Per block
- **level_3 cloze**: correct = the form in the anchor sentence. 3 distractors,
  same POS, grammatical in the slot but wrong in meaning, and from the same
  domain as the target (a count noun for 色数, an adverb of attitude for
  あえて). Kill any distractor that gives a natural sentence (「音楽を恐れている」
  is natural, so 恐れて is not a distractor). No sound-alikes.
- **level_5 collocation gap**: correct = collocate; distractors near in
  meaning but unidiomatic with the target.
- **level_6 semantic discrimination**: 3 wrong sentences, each a NATURAL-
  LOOKING, fully grammatical sentence that a learner could actually write,
  where the ONLY flaw is the MEANING of the target word in it. Allowed error
  types (use a different one for each sentence): (a) the target used where a
  near-synonym belongs because the target's sense does not cover it (「音が
  褪せる」 — sound 薄れる, it does not fade like a colour; 「敬意を飲む」 is NOT
  this: that is nonsense); (b) the target used in a sense it does not have
  (「ルーツを植える」 as if ルーツ were plant roots); (c) a partner word the
  target never takes although the sentence is otherwise sensible (「色数を
  数える」 is fine, so pick a true non-collocate). Forbidden, because the
  judge rejects them: particle or inflection errors, even on the target
  (「色数が数える」「敬意を欠けた」 are grammar slips, not misuse — those belong
  to level_7 / particle_selection); absurd verb swaps or nonsense (色数を飲む,
  グラフィックを演奏する, 色数の香り); a sentence that is merely odd or false
  about the world but uses the word correctly (「請求書を愛している」 is a
  correct use of 愛する); errors elsewhere in the sentence (tense clashes,
  counters, word order, a slip on another noun); a second oddity besides the
  intended one; a metaphor a native speaker would accept (「敬意を温める」).
  Test: a native speaker who knows the word says 「この言葉はこうは使わない」,
  not 「文法が変だ」 and not 「変な内容だ」. Each wrong sentence has its OWN
  explanation naming how the target is misused and which word or sense would
  be right. B's three use different error types and partner words than A's.
- **level_7 spot incorrect**: a BRAND-NEW incorrect sentence (not a core
  sentence, not a core sentence with one word changed: `corrected_sentence`
  must not equal any core sentence either, or the item gives its answer away).
  Exactly ONE language error, and the error is ON THE TARGET: the particle
  attached to the target, its inflection, its collocate, or its sense. A slip
  on another word (美しいだ) or a factual error (流れやすい→流れにくい) does not
  count. The incorrect sentence must be clearly wrong to any native speaker
  (no double-nominative or other marginal constructions). If this variant also has particle_selection, do not
  make level_7 a particle error on the same word in the same kind of sentence:
  use a collocation, inflection or sense error instead. `corrected_sentence` =
  the same sentence with only that error fixed, and it must itself be
  textbook-natural Japanese in THIS sense (read it aloud: no leftover oddity,
  no second slip, not the colour sense when the pinned sense is memory).
  Read the incorrect sentence aloud too: if a native speaker could say it
  (「おもちゃのグッズを拾いました」 — picking something up is fine), it is not an
  error; plant one that is unmistakable. `error_description` names the wrong
  form, the right form and why.
- **level_4 morphology**: correct = the form in the anchor; distractors = real
  forms of the SAME word that are UNGRAMMATICAL in the slot because of what
  follows or precedes the blank (before ています only the 連用形 fits; after
  ない only certain forms; a 連体形 slot rejects ました). If the blank is the
  whole predicate at the end of the sentence, other tenses and polarities
  (褪せた / 褪せない / 褪せます) all fit and the item is broken: choose distractors
  that fail there for a grammatical reason (褪せ, 褪せて, 褪せれば) or decline
  `no_inflection` if the plan allows. In explanations, rebuild the sentence
  with the distractor exactly as the slot would read (blank before ています →
  愛したています, not 愛したしています).
- **level_8 collocation repair**: correct = collocate; error_collocate is
  planted, not among options.
- **synonym_antonym_match**: the correct option must be a word a Japanese
  dictionary or thesaurus lists as a 類義語/対義語 of the target IN THIS SENSE
  (褪せる↔色づく is not; 採用↔不採用 is). If you cannot name one with
  confidence, you MUST return `{"declined": "no_relation"}`: a forced answer
  (終点 for ルーツ, 重なり for バンド, 消去 for プリント) is the worst defect an
  item can have, a declined block costs nothing. Most concrete nouns and
  loanwords have no antonym — decline them. Distractors must not hold the
  relation for ANY sense of the word, must have the same part of speech as
  the target, and no option may contain the target word (バンドギャップ).
- **particle_selection**: blank a particle from `given.particle_spans_json`
  that is attached to the target word (right after it) or marks the target's
  own argument. The FIRST occurrence of that particle in the sentence is the
  one blanked, so if the same particle occurs earlier at another noun, choose
  a different particle. If no listed particle relates to the target, decline
  `no_particle_slot` (a blank on another noun does not test the word). Distractors must make the sentence
  ungrammatical or clearly unnatural, not merely change its meaning. Use only
  case particles as distractors (が・を・に・で・と・へ・から・より・の); never
  ね/さ/よ/か/な (they do occur mid-sentence, so claims that they cannot are
  false), never も (it fits almost any は/が/を slot), and avoid pairs that
  both work: に/へ, は/が, を/が (with 〜たい, potential, stative predicates). Read the
  sentence aloud with each distractor; if it is grammatical with any meaning,
  replace it. Explanations say which verb or noun rejects the particle and
  why (「選ぶ」は他動詞なので、相手を示す「に」では目的語が立たない). `error_tags`
  = one short Japanese label per distractor.
- **Mined sentence in the wrong sense / prefix use** (数- in 数日): never
  anchor a block on it; anchor on a written sentence instead.

## Before you answer, check each sense
1. level_7: is the error on the target? Is `corrected_sentence` different
   from every core sentence? Is `incorrect_sentence` clearly wrong?
2. level_3 / level_5 / particle: read each distractor in the sentence — none
   gives a sayable sentence; none is off-domain or trivially excluded.
3. level_6: each wrong sentence is natural apart from the target's misuse,
   nothing absurd, three different error types.
4. Explanations: specific, true, consistent with the definition; no generic
   line, no English.
5. B shares no distractor word, wrong sentence, or error pattern with A.
