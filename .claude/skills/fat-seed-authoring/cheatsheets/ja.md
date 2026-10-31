# Fat-seed JA authoring — v7 (short)

Block shapes and plan values (anchor sentence, correct answer, `given`) are
fixed by the Block reference below; never choose them yourself. Everything
else here is the five places where documents lose points. Do these five
things and the rest follows.

## 1. Core sentences: whole word, given reading, given sense, natural
- `definition` = the given definition. Exactly 10 sentences; mined ones first,
  byte-for-byte.
- Before you keep a written sentence, say to yourself (a) the reading of the
  target IN THAT SENTENCE and (b) the sense it carries. If the reading is not
  the given one (度 read たび instead of ど, 粒子 everyday vs physics) or the
  target sits inside a longer word (習熟度 for 度, ロックバンド for the physics
  バンド, プリント技法 for the product sense), discard the sentence.
- Only ordinary collocations: 節度を守る, never 度を守る; 価値観が合わない, never
  志向が合わない; beware homophones (誤りました reads as 謝りました).
- Each sentence has a clear referent and a context cue so the target is the
  only word that fits its slot when blanked (a reason, result or contrast
  clause), stays inside the tier length, and uses one register (declare it).
- pronunciation hiragana; syllable_count = morae (ッ・ン・ー count one each,
  small ゃゅょぁぃぅぇぉ do not); real IPA, no placeholder letters.

## 2. level_6 wrong sentences — build them with one of two moves
A level_6 wrong sentence is grammatical, natural-sounding, and wrong ONLY
because THIS word does not mean that. Build each of the three with a move:
- **Move A, other sense or other word:** write a sentence that is natural for
  a different sense of the same form, or for a different word, where the
  given definition does not fit. スーパー (supermarket): 「あの選手はスーパー
  な活躍をした」 (the adjective 'super', not the shop).
- **Move B, near-synonym swap:** write a natural sentence for a word learners
  confuse with the target, then put the target in its place:
  技術 (skill) ← 知識: 「彼は技術が豊富で、歴史の質問に何でも答える」;
  雑菌 (germs) ← ウイルス: 「雑菌でパソコンが動かなくなった」;
  採用 (formally adopt) ← 使用: 「この辞書は毎日採用している」;
  褪せる (colour fades) ← 薄れる: 「音がだんだん褪せていった」;
  あえて (deliberately) ← つい: 「寝坊して、あえて遅刻した」.
- Never: a particle or inflection slip (「色数が数える」「敬意を欠けた」 belong
  to level_7); a sentence that is merely odd or false but uses the word
  correctly (「スーパーで寝た」「請求書を愛している」「技術は感動を伝えている」);
  a nonsense verb (「色数を飲む」); an error on another word; two problems at
  once. Test: a native speaker says 「この言葉はこうは使わない」, not 「文法が
  変だ」 and not 「変な内容だ」.
- Explanation names the confusion: 「ここは〈知識〉の意味。技術は腕前や方法を
  指すので合わない」. Three different moves/partners; B uses none of A's.

## 3. level_7: one span, on the target
- A new sentence (not a core sentence; corrected_sentence must equal no core
  sentence). incorrect_sentence and corrected_sentence differ in exactly ONE
  span, and that span contains the target word or the particle/verb directly
  attached to it (its particle, its inflection, its collocate). A slip on
  another word, a factual error, or a sentence a native speaker could say
  (「おもちゃのグッズを拾いました」) is not an error.
- corrected_sentence is textbook-natural in the given reading and sense.
  error_description names wrong form, right form and why.

## 4. synonym_antonym_match: decline unless a dictionary lists the pair
- Return `{"declined": "no_relation"}` unless a 国語辞典／類語辞典 would list
  the pair as 類義語／対義語 for THIS sense. 習慣↔例外, 確率↔必然, ルーツ↔終点,
  プリント↔消去 are not pairs: decline. Most concrete nouns and loanwords have
  no antonym. A forced key is the worst defect; a declined block costs nothing.
- Distractors: same part of speech, not in the relation for ANY sense of the
  word, never containing the target word.

## 5. Explanations and distractors everywhere
- Every explanation is specific and true: what the option means and why that
  clashes here. Never 「形は合うが意味が合わない」 or any generic line; never
  English (error_tags, form_label too); never contradict the definition.
- level_3 / level_5 / particle distractors must not fit the slot when the
  sentence is read as plain Japanese (「嫌っていました」 fits 「この歌を___」);
  same part of speech, same domain, no two near-synonyms. Particle distractors
  are case particles only (が・を・に・で・と・へ・から・より・の), never ね/さ/よ/
  か/も; the blanked particle is attached to the target.
- A and B: B shares no distractor word, wrong sentence or error type with A.
