# Particle drill content: authoring rules

Everything under `data/particle_drill/ja/` is static content for the Japanese
particle drill. The learner is an English speaker drilling particles until the
choice is automatic. A wrong answer key teaches a falsehood, so **correctness
beats volume, variety and cleverness**. When you are not certain, drop the
sentence and write a different one.

`catalog.json` is the fixed list of stages, particle groups and skills. A
*skill* is one function of one particle (`ni-time` = に marking a point in
time). Never invent skill ids; look them up in the catalog.

Check your files before you finish (read-only, run from the repo root):

    python scripts/particle_drill_validate.py items/ni-time.jsonl

It must print `0 errors`. Fix and re-run until it does.

## 1. Markup

    私[わたし]{は|wa-topic}毎朝[まいあさ]七時[しちじ]{に|ni-time}起[お]きます。

- **Furigana.** Every run of kanji is followed at once by its reading in
  hiragana in square brackets: `毎朝[まいあさ]`, `起[お]きます`, `食[た]べ物[もの]`.
  Okurigana stays outside. Numbers are written in kanji with a reading
  (`七時[しちじ]`) or as kana; no Arabic digits. Katakana words need no reading.
- **Slots.** A drillable particle is written `{answer|skill-id}`. If another
  particle would be just as natural **with the same English meaning**, list it
  after a slash: `{に/へ|ni-destination}`. The first answer is the best one.
  Answers are written the way they are normally written: kana for the simple
  particles, and kanji **with furigana inside the braces** for the compound
  particles that are normally written with kanji:
  `{に対[たい]して|nitaishite}`, `{を通[つう]じて/を通[とお]して|wotooshite}`,
  `{上[うえ]で|uede}`. Distractors follow the same rule
  (`"d":["に関[かん]して","にとって","として"]`).
- Mark **every** particle in the sentence that is a real, separate particle
  with a matching catalog skill (the learner also fills all of them at once in
  a later exercise). Do not mark particles inside fixed words (`こんにちは`,
  `それでは`, `ので` is one slot not two).
- No other use of `{ } [ ] | < >` in the text.

## 2. Exercise items (`items/<skill>.jsonl`, one JSON object per line)

    {"jp":"私[わたし]{は|wa-topic}毎朝[まいあさ]七時[しちじ]{に|ni-time}起[お]きます。","en":"I get up at seven every morning.","f":1,"d":["で","を","が"],"why":"A clock time you can point to takes に.","lv":5}

| field | meaning |
|-------|---------|
| `jp`  | one natural sentence, 8 to 45 characters, in the markup above |
| `en`  | natural English translation; it must settle any ambiguity the blank leaves |
| `f`   | index (0-based) of the **focus slot**: the slot that drills this file's skill |
| `d`   | exactly 3 wrong answers for the focus slot (clinic files: 1 to 3, see below) |
| `why` | one English sentence (15 to 160 characters): why the answer is right here |
| `lv`  | JLPT level of the hardest word or grammar in the sentence, 5 (easiest) to 1 |

Rules for the focus slot:

1. The focus slot's skill id is the file's skill id (except clinic files).
2. **Every distractor must be plainly wrong** for a native speaker: either
   ungrammatical, or it changes the meaning so that the English no longer
   fits. Never use a particle that is merely less common, more formal, or
   "also possible with a nuance". Examples of forbidden distractors: へ for a
   に destination; が for a は topic unless the sentence makes が impossible;
   は or も for any case particle (they can replace が and を almost anywhere,
   so only use は / も as a distractor where the result is clearly wrong);
   から for a ので reason.
3. If such a particle exists, it is an **alternative**, not a distractor:
   write it in the slot (`{に/へ|…}`).
4. Distractors should be the mistakes learners really make (the catalog
   `conf` list for the skill is the starting point), written like answers:
   kana, or kanji with furigana.
5. Other slots in the sentence need no distractors, but they do need their
   alternatives. Be generous there: a non-focus slot that could be は or が
   is written `{は/が|wa-topic}`.

Conjugating particles (て, たり, たら, ば, ても, ながら ...): put only the
particle itself in the slot when the stem is unambiguous
(`飲[の]ん{で|te-sequence}`, `安[やす]けれ{ば|ba-conditional}`). When the choice
between particles changes the stem (the conditional clinic), put the whole
conjugated word in the slot in kana and give whole-word distractors:
`{いけば|x-conditionals}` with `"d":["いくと","いったら","いくなら"]`.

Clinic files (`x-…`): the focus slot keeps the id of the function it really
has (`{は|wa-topic}`), or the clinic id when no single skill fits. `d` holds
the other members of the clinic's set (1 to 3 entries). Write minimal pairs
where you can: two sentences that differ in one word and take different
particles.

Sentences:

- Natural, modern, standard Japanese that a teacher would be happy to model.
  Polite and plain styles both, mixed. No textbook nonsense, no slang unless
  the skill is a casual particle.
- Vary subjects, verbs, tenses, sentence types (statement, question,
  negative, request) and topics. Avoid 私は at the start of more than one
  sentence in ten. Do not reuse a verb more than three times in a batch.
- Vocabulary follows the batch's level band. For an N5 skill most sentences
  use N5 vocabulary so the particle is the only difficulty.
- One blank must have one best answer given the English. If two readings are
  possible, rewrite.
- No offensive, sexual, political or brand content. Names: common Japanese
  family names with さん, or roles (先生, 母).

## 3. Pattern packs (`packs/<skill>.json`, a JSON array)

A pack is a sentence frame with interchangeable parts. The drill builds
sentences from it at random, so **every combination of values must be a
natural sentence with the same particle answers**.

    {"id":"de-place-1","lv":5,
     "tpl":"<who>{は|wa-topic}<place>{で|de-place}<act>。",
     "en":"<who> <act> at <place>.",
     "f":1,"d":["に","を","が"],
     "why":"The place where an action is carried out takes で.",
     "vars":{
       "who":[["田中[たなか]さん","Mr. Tanaka"],["母[はは]","My mother"]],
       "place":[["図書館[としょかん]","the library"],["家[いえ]","home"]],
       "act":[["本[ほん]{を|o-object}読[よ]みました","read a book"],["宿題[しゅくだい]{を|o-object}しました","did homework"]]}}

- `tpl` uses the item markup plus `<name>` variables. `en` uses the same
  variables. `f`, `d`, `why`, `lv` are as for items and refer to the slots of
  the expanded sentence (slots inside values count, left to right, so keep
  the focus slot in `tpl` and before any variable that contains slots, or
  give every value of a variable the same number of slots).
- Each variable has 6 to 12 values `[japanese, english]`; a pack has 2 to 4
  variables and at least 150 combinations.
- English must read correctly for every combination: use past tense or other
  forms that need no agreement, and give each value the exact English that
  slots into the frame (articles included).
- Keep parts that depend on each other inside one value (object + verb,
  counter + noun). Different packs of a skill use different frames
  (statement, question, negative, embedded clause ...).
- Pack ids are `<skill>-1`, `<skill>-2`, ...

## 4. Guides (`guides/<group>.json`)

One file per particle group in the catalog. It teaches; the drill does the
rest. Write for an adult learner: direct, concrete, no filler, British or
American spelling consistently, no emoji.

    {"group":"ni",
     "intro":"Two to four sentences: the single core image of this particle that ties its uses together.",
     "skills":[
       {"id":"ni-time",
        "rule":"One sentence the learner can recite.",
        "explain":"Two to four short paragraphs separated by a blank line. What it means, when it applies, where its edge is. Japanese inline is fine.",
        "patterns":["[clock time / date / day] に [verb]"],
        "examples":[{"jp":"七時[しちじ]{に}起[お]きます。","en":"I get up at seven."}],
        "contrast":[{"vs":"で","note":"What the neighbouring particle would mean or why it fails here."}],
        "mistakes":[{"bad":"明日[あした]{に}行[い]きます。","good":"明日[あした]行[い]きます。","note":"Relative time words take no に."}],
        "tip":"A short memory hook or a quick test the learner can apply in under a second."}]}

- `skills` lists exactly the group's skills from the catalog, in catalog
  order.
- 4 to 6 `examples` per skill, easiest first, the taught particle in braces
  (no skill id needed in guides), full furigana.
- 1 to 3 `contrast` entries (the particles learners confuse with this one)
  and 1 to 3 `mistakes` (a wrong sentence marked as wrong, and its fix).
- `explain` is 300 to 900 characters. State real rules, including the
  exceptions that matter; do not hedge.

## 5. Conjugation lexicon (`conjugation/verbs.json`, `adjectives.json`)

    {"d":"帰る","k":"かえる","c":"godan","t":"i","en":"go home, return","lv":5}
    {"d":"高い","k":"たかい","c":"i","en":"expensive; tall","lv":5}

- `d` dictionary form, `k` its full hiragana reading, `en` short gloss, `lv`
  JLPT level.
- Verbs: `c` is `godan`, `ichidan`, `suru` (する and noun+する) or `kuru`
  (来る); `t` is `t` (transitive) or `i` (intransitive). Take great care with
  godan verbs that end in -iru / -eru (帰る, 入る, 走る, 知る, 切る, 要る, 減る,
  喋る, 滑る, 蹴る, 握る, 参る, 限る, 焦る ...): they are `godan`.
- Adjectives: `c` is `i` or `na`; na-adjectives are listed without な
  (`静か`, reading `しずか`). いい is listed as `良い` / `よい`.
