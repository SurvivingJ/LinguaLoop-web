# Proposed edits to cheatsheets/zh.md (v1 -> v2), from gold100: a_prod100 vs b_base100
Not applied. Each edit targets one defect class from `nt_experiment.py --loss a_prod100 --against b_base100`.

## Edit 1, section 4 (level_7), +0.65 pts/sense lost (fatal +0.37, major +0.28)
Add after "Patterns natives use are NOT errors":
- These are NOT errors. Natives say them, so never plant them:
  - dropping 在 after 放/摆/挂 before a place (放箱底, 放桌上)
  - a verb taking its object directly where 于 is optional (垂直地面)
  - topic-fronted objects (校园内外都打扫了一遍)
  - leaving out 把
- The error is ON the target or attached to it. Never a stray 了 elsewhere (能帮我了的人).
- Safe error types, in order of preference:
  1. the wrong measure word for the target noun
  2. a 离合词 used with an object
  3. the wrong complement on the target verb
  4. the target in the wrong position
- Before writing error_description, read corrected_sentence aloud. If a native would still change it (两公斤肉类 -> 两公斤肉), pick another sentence.
- Every claim in error_description must be true. Never say a word "cannot" do something it commonly does (一把 is a verbal measure: 推了一把).

## Edit 2, section 3 (level_6), +0.53 pts/sense lost (major +0.38, minor +0.12)
Add:
- Context test. If any normal situation makes the sentence true and natural, it is not wrong: 「我每天在公司玩八个小时」 works for someone slacking off. Make the clash lexical, not situational.
- Fix test. When the explanation says 「这里应该用〈X〉」, put X in place of the target and read the whole sentence. It must be natural AND correct. A replacement that is a synonym of another word in the sentence fixes nothing (毫不立刻 -> 马上: 立刻/马上 are synonyms). For a Move B (other sense) sentence, do not offer a replacement. Only name the sense the sentence uses.

## Edit 3, section 6 (level_3 distractors), +0.24 pts/sense lost (fatal)
Replace "Read each one in the blank" with:
- Read each distractor in the blank as a complete sentence. If a native would accept it with no context, it fails: 爷爷年轻时讨厌过马, 两国合作的阻力, 我从不坐地铁上班. Replace it.
- Do not use words from the target's own frame as distractors. Frequency adverbs, attitude verbs and transitive verbs with the same object all fit. Pick a word whose meaning clashes with a cue that is already in the sentence (a time word, the object, a complement), and say which cue in the explanation.
- The explanation must be true of this sentence. 爷爷 is a person, so 「主语是有感情的人」 cannot be the reason.

## Edit 4, section 2 (level_1), coverage: 87% of variants declined (prod), 78% (baseline)
Only single-character lemmas got a level_1 in production. The rule "differs by ONE thing in ONE syllable" plus the never-list makes the author decline almost every two-syllable word. Add worked two-syllable cases and an explicit search order:
- For a two-syllable word, try each syllable's other tones, then the n/l, z/zh, an/ang, en/eng, in/ing partner, keeping the other syllable fixed:
  - 放松 fàngsōng -> 放送 fàngsòng
  - 放松 fàngsōng -> 放纵 fàngzòng is two changes, never.
  - 新娘 xīnniáng -> 新粮 xīnliáng (n/l).
  - 遇见 yùjiàn -> 预见 yùjiàn is a homophone, never. 意见 yìjiàn is a changed initial vowel, allowed.
- Write 5–6 candidates. The judge drops weak ones and the item survives with 3.
- Decline only when fewer than 3 real words were found after the search.
(Edit 4 adds options, so it may raise level_1 defect counts while adding listening items. Judge it on coverage plus the level_1 fatal/major rate, not on score alone.)
