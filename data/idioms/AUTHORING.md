# Idiom trainer content: authoring rules

Static content for the idiom trainer (`/idiom-trainer/zh`, `/idiom-trainer/ja`).
The learner is an English speaker at an intermediate level who learns each
idiom as a small story and then practises recognising the situation that
calls for it. An idiom taught with a wrong meaning, a wrong register or an
invented origin is worse than no idiom: **when you are not certain, leave it
out or say less.**

    data/idioms/<lang>/lists/<set>.json     the ranked list of a set (authority for id, text, reading, meaning)
    data/idioms/<lang>/cards/<set>-NN.json  full cards, ten idioms per file, in list order
    data/idioms/<lang>/review/<job>.json    what the reviewer changed

Check your files (read-only, from the repo root):

    python scripts/idiom_trainer.py validate data/idioms/zh/lists/chengyu.json
    python scripts/idiom_trainer.py validate data/idioms/zh/cards/chengyu-01.json

It must print `0 problems`.

## 1. Sets

| lang | set | what belongs in it |
|------|-----|--------------------|
| zh | `chengyu` | 成语: four-character idioms (a few longer fixed ones), the ones educated speakers actually use and learners meet up to HSK 5-6 |
| zh | `guanyong` | 惯用语: colloquial fixed expressions, mostly three characters (开夜车, 炒鱿鱼, 拍马屁, 走后门) |
| zh | `suyu` | 俗语 / 谚语: common sayings and proverbs (车到山前必有路, 三个臭皮匠，顶个诸葛亮) |
| ja | `kanyo` | 慣用句: idiomatic phrases, especially body-part and 気 expressions (腹が立つ, 手を貸す, 気が重い) |
| ja | `yoji` | 四字熟語: four-character compounds in real use (一石二鳥, 十人十色, 自業自得) |
| ja | `kotowaza` | ことわざ: proverbs people quote (猿も木から落ちる, 急がば回れ) |

Choose by **present-day frequency and usefulness**, most useful first. Leave
out the dated, the bookish, the regional and the offensive. If native
speakers would recognise it but never say or write it, it does not belong in
the core.

## 2. List file (`lists/<set>.json`, a JSON array, one object per line)

    {"id":"cy001","t":"画蛇添足","r":"huà shé tiān zú","mean":"to ruin something by adding what is not needed","lvl":2,"tag":"foolishness"}

- `id`: the set's two-letter code and a three-digit number in list order:
  `cy` chengyu, `gy` guanyong, `sy` suyu, `ky` kanyo, `yj` yoji, `kw` kotowaza.
- `t`: the idiom in its dictionary form. Chinese: simplified characters (a
  saying may contain one full-width comma). Japanese: normal spelling with
  kanji (`腹が立つ`), no furigana.
- `r`: the reading. Chinese: pinyin with tone marks, one syllable per
  character, separated by spaces, neutral tone unmarked. Japanese: hiragana.
- `mean`: what it means, in plain English, 3 to 70 characters, written so it
  can stand as an answer option: specific enough that no other idiom of the
  set has the same meaning line.
- `lvl`: 1 = everyday, 2 = common in writing and educated speech, 3 = less
  common but worth knowing.
- `tag`: one theme from this list (used to keep look-alike meanings apart in
  the options): `effort success failure caution haste joy anger fear sadness
  relationship speech knowledge foolishness change time quantity appearance
  behaviour luck difficulty money work`.

## 3. Card file (`cards/<set>-NN.json`, a JSON array of cards)

    {"id":"cy001","t":"画蛇添足","r":"huà shé tiān zú","mean":"to ruin something by adding what is not needed","lvl":2,"tag":"foolishness",
     "lit":"to draw a snake and add feet",
     "story":{"text":"Servants in the state of Chu were given one jug of wine, too little to share, so they agreed that whoever drew a snake first would drink it. One man finished early and, showing off, started adding feet. Another finished his snake, took the jug and said: a snake has no feet, so yours is not a snake.","source":"《战国策·齐策二》"},
     "use":{"reg":"neutral","tone":"criticism","how":"Used as a predicate or after 是: 这样做是画蛇添足。 Criticises an action already done or proposed."},
     "near":[{"t":"多此一举","diff":"多此一举 is any unnecessary extra step; 画蛇添足 says the extra step makes the result worse."}],
     "parts":["画蛇","添足"],
     "cue":"A colleague's report was clear, then he added three more pages that confused everyone. What did he do?",
     "ctx":[{"s":"这篇文章已经很完整了，再加一段解释就是{画蛇添足}。","en":"The essay is already complete; adding another paragraph of explanation would just spoil it."}],
     "bad":[{"s":"他工作很努力，每天都{画蛇添足}。","en":"(meant: he works hard every day)","why":"It is a criticism of one unnecessary addition, not praise for effort."}]}

`id`, `t`, `r`, `mean`, `lvl`, `tag` are copied from the list unchanged.

- `lit`: the literal sense or image, 5 to 120 characters. This is the memory
  hook when there is no story.
- `story`: **the origin, only when a real one exists and you are sure of it.**
  `text` tells it in 80 to 600 characters of plain English, as it is
  traditionally told; `source` names where it comes from (a classical text,
  a fable, a historical episode, a Buddhist term, a kabuki or sumo usage).
  Otherwise `null`. Never invent a story, never embellish one, never attach
  a source you are not certain of. Many colloquial expressions and
  body-part idioms have no story: for those the image in `lit` is the hook,
  and `story` is `null`. A wrong story is a defect; a missing one is not.
- `use`: `reg` is `spoken`, `written`, `formal` or `neutral`; `tone` is
  `praise`, `criticism`, `humorous` or `neutral`; `how` says in one or two
  sentences (10 to 200 characters) what grammatical slot it fills and what
  it is said about, with a short example where that helps.
- `near`: 0 to 2 idioms it is confused with, each with `diff`: the
  difference in one sentence (10 to 200 characters).
- `parts`: the idiom cut in two where a speaker would pause; the two parts
  joined give `t` exactly.
- `cue`: a situation in English, 20 to 200 characters, that calls for this
  idiom and no other in the set. It must not contain the meaning line.
- `ctx`: **exactly 6 contexts**, each a different situation, speaker and
  sentence shape (statement, question, dialogue line, narration), easiest
  first. The idiom appears once, in braces, in the form it takes there.
  One or two sentences; `en` is a natural translation of the whole.
- `bad`: **exactly 2 misuses**: a sentence a learner might write where the
  idiom is wrong (wrong meaning, wrong tone, wrong register or wrong
  grammar), `en` saying what was meant, and `why` (15 to 200 characters).
  The misuse must be clearly wrong to a native speaker, not merely unusual.

### Chinese sentences
Simplified characters, full-width punctuation, no Latin letters or Arabic
digits, 8 to 60 characters. In `chengyu` and `suyu` the braces hold the
idiom unchanged. In `guanyong` the expression may be split by other words
(炒了他的鱿鱼): put the whole stretch, from its first character to its last,
in the braces.

### Japanese sentences
The markup of `data/particle_drill/AUTHORING.md` section 1: every run of
kanji is followed by its reading in square brackets, also inside the braces
(`{腹[はら]が立[た]って}`), no Arabic digits, 8 to 70 characters. A 慣用句
is conjugated to fit its sentence. A 四字熟語 keeps its four characters and
may be followed by な, に, の, だ or する outside the braces.

## 4. What makes a good card
- The six contexts together show the idiom's range: who says it, about
  what, in which register. If it is only written, the contexts are written
  ones. If it is criticism, no context uses it as praise.
- A learner should be able to work out which idiom fits from the situation
  alone. Avoid contexts where a near-synonym from the same set would fit as
  well.
- Plain, modern, natural sentences that a teacher would be happy to model.
- No offensive, sexual or political content.
