# Fat-seed ZH authoring (q2: v2 + level_1 tone rule, level_6 X-first, level_7 corrected-first)

Block shapes and plan values (anchor sentence, correct answer, `given`) are
fixed by the Block reference below; never choose them yourself. Everything
learner-facing is simplified Chinese: no English, no traditional characters
(except a 繁体 form), no pinyin inside sentences. These six sections are
where documents lose points.

## 1. Core sentences: whole word, given reading, given sense, natural
- `definition` = the given definition, in simplified Chinese. Exactly 10
  sentences; mined ones first, byte-for-byte. pos / semantic_class / register /
  form labels: exactly the values the brief lists (Chinese labels).
- The target's characters appear contiguously, as an independent word doing
  THIS sense. Discard a sentence where they sit inside another word (学 in
  学生, 电 in 电脑, 起来 in 一起来吧) or carry another reading. For 多音字, say
  the reading to yourself: 行 xíng/háng, 长 cháng/zhǎng, 得 dé/de/děi,
  重 zhòng/chóng, 还 hái/huán, 觉 jué/jiào, 种 zhǒng/zhòng.
- Single characters that are mostly bound in modern Chinese (国, 语, 民, 业)
  may appear only where they truly stand alone. 「他走过很多国」 is wrong:
  use 国家. If no such context exists at the tier, skip the sense as a
  fragment.
- Respect the tier: count 汉字 (T1 ≤10, T2 ≤16, T3 ≤22, T4 ≤30, T5 ≤40). Grammar
  ceilings: T1 has no 了/着/过, T2 adds 了, T3 adds 着/过 and simple 把, and
  T4 adds 被 and 如果…就….
- Only ordinary collocations: 提高水平 not 增加水平, 养成习惯 not 做习惯,
  犯错误 not 做错误, 发挥作用. One register per document.
- Each sentence has a context cue so the target is the only word that fits its
  slot when blanked.
- Pinyin: tone marks, syllables separated by spaces (qǐ lái), never tone
  numbers. syllable_count = number of characters. Broad IPA.
- Forms: only real ones. 量词 a native would use with this noun, 体标
  forms, real 复合 words, 重叠 only if the word reduplicates, and 繁体 only
  when it differs.

## 2. level_1 (listening): sounds confusable, real words
zh has no phonetic trie: a declined level_1 means the sense gets NO
listening exercise. Find neighbours; declining is the last resort.
- Correct = the headword. Each distractor is a real, common word of the same
  length that a listener can confuse with it. Two kinds are valid:
  - **Same syllables, other tones** (on one syllable OR on several):
    妈 mā → 马 mǎ; 老师 lǎoshī → 老是 lǎoshì; 练习 liànxí → 联系 liánxì;
    时间 shíjiān → 实践 shíjiàn; 美丽 měilì → 魅力 mèilì; 汉语 hànyǔ → 韩语 hányǔ;
    同志 tóngzhì → 统治 tǒngzhì; 经理 jīnglǐ → 经历 jīnglì.
  - **One sound changed in one syllable** (any tone): n/l 男 nán → 蓝 lán;
    z/zh, c/ch, s/sh 四 sì → 是 shì; an/ang 山 shān → 伤 shāng;
    en/eng 门 mén → 盟 méng; in/ing 心 xīn → 星 xīng; 新娘 xīnniáng → 新粮 xīnliáng.
- Search order for a word of two or more syllables: (1) say its syllables
  with other tones and list the real words you hear (练习 → 联系);
  (2) swap one initial or final for its partner above, the other syllables
  fixed. Write 5–6 candidates; the judge drops weak ones and 3 survive.
- Never: a pure homophone (same sounds AND tones: 经历/精力, 遇见/预见), a
  synonym, a non-word, a rare or literary word (墨刑, 魔星), a word that only
  looks similar, or sounds changed in two syllables (放松 fàngsōng → 防守 fángshǒu).
- Explanation states the contrast: 「liánxì（第二声、第四声）与 liànxí 声调不同，意思是联系」;
  「lán 与 nán 声母不同，意思是蓝色」.
- B uses different words from A. Decline (`{"declined": "no_minimal_pairs"}`)
  only when both kinds give fewer than 3 real words.

## 3. level_6 wrong sentences: grammatical, wrong only in how THIS word is used
Each wrong sentence reads as grammatical Chinese. A native speaker says
「这个词不这么用」, not 「语法错了」. Build each with one move:
- **Move A, near-synonym swap:** first write a natural sentence for a word X
  learners confuse with the target (X not already in the sentence), then put
  the target in X's place. X is the 〈X〉 of the explanation: never pick it
  afterwards.
  - 提高 ← 增加: 「这个月我的体重提高了三公斤」
  - 发现 ← 发明: 「爱迪生发现了电灯」
  - 参观 ← 看望: 「周末我去医院参观生病的奶奶」
  - 经验 ← 经历: 「这次旅行是我最难忘的经验」
  - 安静 ← 平静: 「听到这个消息，她的心情很安静」
- **Move B, other sense:** a sentence natural for another sense of the same
  form. Teaching 意思 = meaning, use 「这是我的一点小意思」 (a small gift).
  Its explanation names that sense and offers NO replacement: 「这里的“意思”是礼物的意思，不是“含义”」.
- **Move C, nouns only, wrong measure word for THIS noun:** 「我买了一只书」.
- Never use these in level_6; they belong to level_7: an aspect-marker or
  word-order slip, or a 离合词 used as transitive (见面老师).
- Also never: a sentence that is merely odd or false but uses the word
  correctly (「我在超市睡觉」), a nonsense pairing, an error on another word,
  or two problems at once.
- Explanation names the confusion: 「这里应该用〈增加〉。提高用于水平、质量，体重、人数等数量要用增加」.
  The three sentences use different moves or partners, and B uses none of A's.
- Context test. If any normal situation makes the sentence true and natural,
  it is not wrong: 「我每天在公司玩八个小时」 works for someone slacking off.
  Make the clash lexical, not situational.
- Fix test. When the explanation says 「这里应该用〈X〉」, put X in place of the
  target and read the whole sentence. It must be natural AND correct. A
  replacement that is a synonym of another word in the sentence fixes nothing
  (毫不立刻 → 马上: 立刻/马上 are synonyms; 这间厕所是大楼的〈卫生间〉 is a
  tautology). If the fix fails, the sentence was not built by Move A: rebuild it.

## 4. level_7: one span, on the target
- Write corrected_sentence FIRST: a new, plain sentence a native would say,
  using the target in THIS sense (not a core sentence). Then break one thing
  on the target to get incorrect_sentence.
- The incorrect and corrected sentences differ in exactly ONE span. That span
  is the target or a word attached to it: its measure word, its 了/着/过, its
  complement, its position, its 离合 split. Examples:
  - 「我明天见面老师。」→「我明天跟老师见面。」
  - 「他慢慢站下来了。」→「他慢慢站起来了。」
  - 「我买了三只书。」→「我买了三本书。」 (target 书)
- The error must be one a native spots at once: a common learner error, not
  something natives also say. Patterns natives use are NOT errors (V过了 as in
  看过了). The corrected sentence must itself be fully grammatical: re-check
  the measure word and the rest of the sentence.
- These are NOT errors. Natives say them, so never plant them: dropping 在
  after 放/摆/挂 before a place (放箱底, 放桌上); a verb taking its object
  directly where 于 is optional (垂直地面); topic-fronted objects
  (校园内外都打扫了一遍); leaving out 把.
- The error is ON the target or attached to it. Not on the target: a stray
  了 elsewhere (能帮我了的人), 把+被 together, 比…很, the measure word of
  ANOTHER noun (teaching 骑: 一只马 is about 马, not 骑).
- Safe error types, in order of preference: (1) the wrong measure word for the
  target noun; (2) a 离合词 used with an object; (3) the wrong complement on
  the target verb; (4) the target in the wrong position.
- Before writing error_description, read corrected_sentence aloud. If a native
  would still change it (两公斤肉类 → 两公斤肉), pick another sentence.
- Every claim in error_description must be true. Never say a word "cannot" do
  something it commonly does (一把 is a verbal measure: 推了一把).
- error_description, in Chinese, names the wrong form, the right form and why.

## 5. synonym_antonym_match: decline unless a dictionary lists the pair
- Return `{"declined": "no_relation"}` unless 《现代汉语词典》 or a 近义词／反义词
  dictionary lists the pair for THIS sense.
  - Valid pairs: 提高↔降低, 增加↔减少, 成功↔失败, 安静↔吵闹, 美丽↔漂亮.
  - Not pairs: 习惯↔例外, 电脑↔手机, 老师↔学生.
  - Concrete nouns rarely have one. A forced key is the worst defect.
- Distractors: same part of speech, in no relation to ANY sense of the word,
  and never sharing the target's characters (not 高度 for 提高).

## 6. Explanations and distractors everywhere
- Every explanation is specific and true: what the option means and why it
  clashes here.
- level_3: start each distractor's explanation with its failure tag (语义 /
  搭配 / 体貌 / 语域 / 配价), then the reason: 「搭配：“增加”说数量，不能说水平」.
  The three distractors cover at least two tags.
- Never a generic line such as 「意思不对」. Never English. Never contradict
  the definition.
- level_3 distractors have the same part of speech and are grammatical in the
  slot, but must not fit when the sentence is read as plain Chinese.
- Read each distractor in the blank as a complete sentence. If a native would
  accept it with no context, it fails: 爷爷年轻时讨厌过马, 两国合作的阻力,
  我从不坐地铁上班. Replace it.
- Do not use words from the target's own frame as distractors. Frequency
  adverbs, attitude verbs and transitive verbs with the same object all fit.
  Pick a word whose meaning clashes with a cue already in the sentence (a time
  word, the object, a complement), and say which cue in the explanation.
- The explanation must be true of this sentence. 爷爷 is a person, so
  「主语是有感情的人」 cannot be the reason.
- Run the substitution check: if a near-synonym of the target
  would make a distractor right, replace it. No homophones or near-homophones
  of the target in level_3 (those belong to level_1).
- A and B: B shares no distractor word, wrong sentence or error type with A.
