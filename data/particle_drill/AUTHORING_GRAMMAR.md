# Grammar drill content: authoring rules

Everything under `data/particle_drill/ja-grammar/` is static content for the
second Japanese sentence drill: giving and receiving, transitive pairs, keigo,
こそあど and question words, connectors, adverbs, sound and manner words,
conditionals, sentence patterns, kanji readings and look-alike kanji.

**Read `AUTHORING.md` first.** Its markup (section 1), item format (section 2),
pack format (section 3) and guide format (section 4) apply here unchanged,
except where this file says otherwise. Where the two differ, this file wins.
Wherever `AUTHORING.md` says "particle", read "the expression in the slot".

Validator for this course (read-only, run from the repo root):

    python scripts/grammar_drill_validate.py items/pt-tekudasai.jsonl
    python scripts/grammar_drill_validate.py --expand packs/pt-tekudasai.json

`catalog.json` in this directory is the fixed list of stages, groups and
skills. A skill's `title` names the words or patterns it covers; `conf` is a
starting point for wrong answers; `ask` is set for the two kanji areas.

## 1. What goes in the slot

- The slot holds **exactly what the learner must produce**, written as it is
  normally written (kana, or kanji with furigana inside the braces).
- If every option attaches to the same stem, the slot holds only the ending:
  `ここで写真[しゃしん]を撮[と]っ{てもいいですか|pt-temoii}。`
- If the options need different stems, the slot holds the **whole conjugated
  word** and so does every distractor:
  `富士山[ふじさん]に{登[のぼ]ったことがあります|pt-takotogaaru}。` with
  `"d":["登[のぼ]るつもりです","登[のぼ]ってもいいです","登[のぼ]ることにします"]`.
- **One slot per sentence is enough.** Do not mark particles: their skills
  belong to the other course and are not in this catalog. Add a second slot
  only when another skill of this catalog occurs and you are sure of its id.
- No alternatives unless two answers are truly interchangeable with the same
  English; then list both (`{だから/それで|cn-dakara}`).

## 2. Distractors

- Exactly 3 (1 to 3 in `x-` files), each **plainly wrong** in this sentence
  with this English: it changes the meaning, the direction, the logic or the
  register, or it is ungrammatical here.
- Distractors are **well-formed words**. The learner should fail because they
  chose the wrong expression, not because one option is misspelled. (The
  exceptions are skills that drill formation itself, such as the okurigana
  skill.)
- Draw them from what learners really confuse: the other members of the
  skill's set, the skill's `conf`, the neighbouring skills of its group.
- The sentence must contain what decides the answer: who gives and who
  receives, whose action it is, where the thing is, the logical relation
  between the two clauses. If the English is the only thing that decides it,
  make the English explicit ("that one near you").

## 3. Sets and mixed skills

Many skills cover a set of words (`title` lists them). In such a file the
**answers rotate evenly over the members of the set**, and the distractors
are mostly the other members. A file whose answer is the same word in every
line is wrong unless the skill names a single expression.

`x-` skills mix the skills of their stage: the focus slot keeps the id of the
skill it really belongs to (or the `x-` id when none fits), and `d` holds the
competing expressions.

## 4. Sentences

- Length up to 70 characters. Two short sentences are allowed, and are
  required where the answer depends on context: connectors
  (`雨[あめ]が降[ふ]っていました。{それでも|cn-sorenanoni}、試合[しあい]は行[おこな]われました。`),
  こそあど, あげる / くれる.
- Otherwise as `AUTHORING.md`: natural modern standard Japanese, full
  furigana, kanji numerals, varied subjects and verbs, level-appropriate
  vocabulary.

## 5. Notes by area

**Giving and receiving (`gv-`, `x-give`).** State giver and receiver, and make
the in-group clear (私, 弟, うちの母 against 友達, 先生). The particles
around the blank stay in the text: they are part of the clue. Whole verb in
the slot (`{くれました|gv-kureru}`).

**Transitive pairs (`tr-`, `x-trans`).** The verb is in the slot, conjugated,
with furigana; the particle before it (が / を) stays visible. Distractors:
the partner verb in the same form, plus two other wrong forms (passive or
potential of either verb). Use only clear pairs; avoid verbs that work both
ways (開く read ひらく, 閉じる, 増す) and sentences where both members are
natural.

**Keigo (`kg-`, `x-keigo`).** Make it obvious whose action it is and who is
being respected (社長, 先生, お客様 against 私, 弟). Whole verb phrase in the
slot. Distractors are the plain form's other keigo versions (humble for
honorific and the reverse, double keigo, the plain polite form where it is
clearly not enough is NOT a valid distractor: it is merely less polite).

**こそあど and question words (`ko-`).** Distance and ownership come from the
context sentence or from the English. For それ / あれ in conversation, state
whether both speakers know the thing.

**Connectors (`cn-`, `x-connect`).** Two sentences; the blank is the connector
that opens the second. The logic between them must allow only one family of
connectors.

**Adverbs (`av-`, `x-adverb`).** In about half the items the blank is the
adverb (the ending is given); in the other half the blank is the ending the
adverb demands (the adverb is given).

**Sound and manner words (`on-`, `x-ono`).** The scene must force one word.
Hiragana or katakana as usual for the word.

**Conditionals (`cd-`, `x-cond`).** Whole conjugated word or clause ending in
the slot (`{行[い]けば|cd-ba}`), with the other conditionals of the same word
as distractors. Only use sentences where the others are really excluded (a
request after と, a past single event with ば, and so on); where two
conditionals are both fine, list both as alternatives.

**Sentence patterns (`pt-`).** See section 1. Mix polite and plain endings.
For a skill that lists several patterns, rotate them.

**Kanji readings (`ym-`, `x-yomi`; catalog `ask: "reading"`).** The learner
sees the word in kanji and gives its reading. The slot is the whole word with
its reading, `{今朝[けさ]|ym-n5-time}`; `d` is 3 wrong readings **in hiragana
only**: the readings a learner would wrongly assemble from the kanji's other
readings (`"d":["こんあさ","いまあさ","こんちょう"]`). The sentence must fix
the reading; skip words with two accepted readings in that context.

**Look-alike kanji and spelling (`nt-`, `x-nita`; catalog `ask: "kanji"`).**
The learner sees the reading and chooses the written form. The slot is the
word with furigana, `{待[ま]って|nt-n5}`; each distractor is the same word
written with the confusable kanji (or the wrong okurigana), **carrying the
same reading as the answer** so that only the writing differs:
`"d":["持[ま]って","特[ま]って","侍[ま]って"]`. For homophones the sentence
meaning decides (`{暑[あつ]い|nt-homophone}`, `"d":["熱[あつ]い","厚[あつ]い"]`
plus one more).

**Collocations (`cl-`, `x-colloc`).** The noun and its particle stay in the
text; the verb (or adjective) is in the slot, conjugated, with furigana.
Distractors are the verbs an English speaker would reach for (取る for 飲む
with medicine, 遊ぶ for 弾く with an instrument), in the same form. Rotate the
nouns of the skill's set.

**Idioms (`id-`, `x-idiom`).** The situation in the sentence (or the English)
must point to one expression. Put the whole expression in the slot, or only
the part that varies (`気{になって|id-ki1}`) when every option shares the rest.
Distractors are the neighbouring expressions of the set.

**Casual contractions (`cs-`, `x-casual`).** Each item is a spoken sentence
whose slot holds the contracted form; the English is natural, and the `why`
states the full form it comes from (`食べちゃった ← 食べてしまった`).
Distractors are other contractions, or the same contraction with the wrong
sound (ちゃう where じゃう is needed). In about a third of the items reverse
it: the sentence is in careful style and the slot holds the full form, with
contracted forms of other patterns as distractors. Hiragana only in the slot
unless the verb stem is inside it.

**Compound verbs (`cv-`, `x-compound`).** The whole compound verb is in the
slot, conjugated, with furigana (`{飛[と]び込[こ]んだ|cv-komu}`). Distractors
are the same first verb with another second verb (飛び出した, 飛び上がった),
all real words where possible.

**Loanword traps (`gr-`, `x-gairaigo`).** The slot holds the katakana word
the Japanese sentence needs; the English uses the real English word for the
thing (apartment building for マンション). Distractors are other katakana
words, including the one an English speaker would wrongly expect (アパート
is acceptable for some flats: avoid sentences where both fit).

## 6. Guides

Format as `AUTHORING.md` section 4, one file per group, the taught expression
in braces in every example. A guide for a set teaches how to choose between
its members; a guide for a kanji group lists the readings or the
distinguishing strokes and gives a way to remember them.

## 7. Katakana list (`reading/katakana.json`)

A JSON array for the speed-reading drill:

    {"k":"コーヒー","en":"coffee","lv":5}

`k` is a common loanword in katakana (2 to 9 characters, long vowels with ー),
`en` a short gloss, `lv` the JLPT level. No names of brands or people.
