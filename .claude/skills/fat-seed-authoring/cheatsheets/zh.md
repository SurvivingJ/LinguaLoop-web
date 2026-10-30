# Fat-seed ZH authoring (v1, from the ja v7 structure)

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

## 2. level_1 (listening): tone neighbours, real words
- Correct = the headword. Distractors are real words that differ from it ONLY
  in the tone of one syllable:
  - One syllable: 妈 mā → 麻 má, 马 mǎ, 骂 mà; 买 mǎi → 卖 mài.
  - Two syllables, one tone changed: 老师 lǎoshī → 老是 lǎoshì;
    主人 zhǔrén → 主任 zhǔrèn; 同意 tóngyì → 同一 tóngyī.
  - Not valid: 练习 liànxí → 联系 liánxì, because both syllables change.
- Never: a word with the same syllable AND tone (pure homophone), a synonym,
  a non-word, a word that differs in the initial or final as well.
- Explanation states the tone contrast: 「mǎ（第三声）与 mā（第一声）声调不同，意思是马」.
- B uses different words. Another character with the same contrasting
  syllable is fine: A 马 mǎ, B 码 mǎ. If a variant cannot get 3 real tone
  neighbours unused by the other variant, write `{"declined":
  "no_minimal_pairs"}` for that variant.

## 3. level_6 wrong sentences: grammatical, wrong only in how THIS word is used
Each wrong sentence reads as grammatical Chinese. A native speaker says
「这个词不这么用」, not 「语法错了」. Build each with one move:
- **Move A, near-synonym swap:** write a natural sentence for a word learners
  confuse with the target, then put the target in its place.
  - 提高 ← 增加: 「这个月我的体重提高了三公斤」
  - 发现 ← 发明: 「爱迪生发现了电灯」
  - 参观 ← 看望: 「周末我去医院参观生病的奶奶」
  - 经验 ← 经历: 「这次旅行是我最难忘的经验」
  - 安静 ← 平静: 「听到这个消息，她的心情很安静」
- **Move B, other sense:** a sentence natural for another sense of the same
  form. Teaching 意思 = meaning, use 「这是我的一点小意思」 (a small gift).
- **Move C, nouns only, wrong measure word for THIS noun:** 「我买了一只书」.
- Never use these in level_6; they belong to level_7: an aspect-marker or
  word-order slip, or a 离合词 used as transitive (见面老师).
- Also never: a sentence that is merely odd or false but uses the word
  correctly (「我在超市睡觉」), a nonsense pairing, an error on another word,
  or two problems at once.
- Explanation names the confusion: 「这里应该用〈增加〉。提高用于水平、质量，体重、人数等数量要用增加」.
  The three sentences use different moves or partners, and B uses none of A's.

## 4. level_7: one span, on the target
- A new sentence. Not a core sentence, and corrected_sentence equals no core
  sentence.
- The incorrect and corrected sentences differ in exactly ONE span. That span
  is the target or a word attached to it: its measure word, its 了/着/过, its
  complement, its position, its 离合 split. Examples:
  - 「我明天见面老师。」→「我明天跟老师见面。」
  - 「他慢慢站下来了。」→「他慢慢站起来了。」
  - 「我买了三只书。」→「我买了三本书。」 (target 书)
- The error must be one a native spots at once: a common learner error, not
  something natives also say.
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
  slot, but must not fit when the sentence is read as plain Chinese. Read each
  one in the blank. Run the substitution check: if a near-synonym of the target
  would make a distractor right, replace it. No homophones or near-homophones
  of the target in level_3 (those belong to level_1).
- A and B: B shares no distractor word, wrong sentence or error type with A.
