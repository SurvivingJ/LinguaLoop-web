# Single-sentence error taxonomy — zh / ja / en

Date: 2026-09-26
Purpose: a shared definition of "what counts as an error" in one generated P1 core sentence, for
(a) writing deliberately broken versions of correct sentences, (b) independently verifying that each broken
version contains exactly one real error, and (c) grouping error types into narrow yes/no questions for a cheap
classifier (jev, `typesafe/jev-1.13`, `noul` mode).

Background read for this document:
- `wiki/evaluations/jev-judge-feasibility-2026-09-26.md` §3.1 — the first controlled corruption set (45 items per
  language, 5 defect types × 3 subtlety levels). AUC 0.87–0.94, recall 1.00, precision 0.65–0.83; weakest
  category was particles / measure words.
- `migrations/seed_ladder_judge_prompts.sql` (en, zh) and `migrations/ja_prompt_seeds.sql` §4 (ja) —
  `ladder_p1_sentence_judge`. The live rubric checks three things per sentence against one locked sense:
  sense match, register, and whole-word / whole-sense; a rating of 1 also covers "ungrammatical" and
  "target absent".
- `data/eval/jev_2026-09-26/exp_a/controlled_set.py` — the items from §3.1.

Changelog:
- 2026-09-28 — Folded in `taxonomy_addendum_2026-09-27.md` (kept as the review record): new types
  `en.phrasal_verb` (en.B1), `ja.particle_other` (new bucket ja.B9), `en.plural_number` (en.B4),
  `zh.topic_comment` (zh.B4), `ja.topic_comment` (ja.B3); revoked the 的-for-地 / 的-for-得 "not an error"
  exemptions in `zh.de_particle` per the 2026-09-27 user ruling (§1.2).

---

## 0. Conventions and common rules

### 0.1 Scope

In scope: one sentence (occasionally two short clauses joined by punctuation) that teaches one target word in
one locked sense at one tier (T1 ≈ vocabulary of a 4–5-year-old … T6 ≈ educated adult).

Out of scope, so never counted as an error of any type in this taxonomy:
- Spelling, typos, punctuation, spacing, full-width vs half-width characters. The only exceptions are three
  types that deliberately swap one correctly written real word or character for another: `zh.de_particle`,
  `ja.kanji_choice` and `en.lexical_form`.
- Whether the sentence is a good teaching sentence, is at the right tier, or is interesting. Tier fit is a
  separate judge. Register is covered here, but it is marked **stylistic, may be excluded**.
- Real-world facts that are merely unusual or false but not impossible or self-contradictory. "Beijing is
  hot in December" is a fact problem, not a language error.
- Cross-sentence discourse: a single sentence is judged on its own, with no preceding context.

### 0.2 The norm

"Wrong" means wrong for a standard, educated native speaker writing edited text for learners. It does not mean
wrong for a prescriptivist. Each language section defines its reference norm. Regional variants that are
standard somewhere (Taiwan Mandarin, British vs American English) are **not errors**.

### 0.3 Type classes

| Class | Meaning |
|---|---|
| G (grammar) | The sentence breaks a rule of form: morphology, function words, word order, construction. |
| S (semantic) | The sentence is grammatical but the meaning is wrong: sense, collocation, anomaly, contradiction. |
| T (target) | The target word is defective relative to the locked sense (rubric-mandated). |
| R (stylistic) | Register mismatch. It is a real defect for LinguaLoop, but excludable from a grammar benchmark. |

Each language has 15–17 core types (zh 15, en 15, ja 17 after the 2026-09-28 fold — see the changelog) plus
the three rubric-mandated target types (`target_absent`, `target_not_whole_word`, `target_in_idiom`). The
rubric's "wrong sense" check is a core semantic type (`wrong_sense`).

### 0.4 Subtlety levels

| Level | Definition |
|---|---|
| obvious | A learner at the sentence's own tier would probably notice. The sentence fails on first read. |
| moderate | Any native speaker notices immediately. An intermediate learner might not. |
| subtle | A native speaker notices on a careful read, but the sentence passes a skim. The surface stays fluent, the edit is one morpheme, character or word, and detecting it requires applying a specific rule or piece of knowledge. **Subtle is not the same as borderline.** If two native speakers could reasonably disagree about whether the sentence is wrong, the item is not subtle; it is invalid. |

### 0.5 Frequency ratings

"How often an LLM generator plausibly makes this error" is an **estimate**, not a measurement. No local file
records per-type verdicts from the live P1 judge. The general pattern the estimates follow: fluent LLM
generators rarely break core grammar in edited-register sentences. Their error mass sits in sense selection,
collocation, register drift, target-word handling, and (for zh/ja) calques from English. So the grammar buckets
will be exercised mostly on synthetic corruptions, where real-world prevalence is low. At low prevalence,
false positives dominate the error budget, and the classifier's precision (0.65–0.83 in §3.1) matters more
than its recall.

### 0.6 Lessons from the 2026-09-26 controlled set

Several §3.1 items that were labelled "broken" fall inside this document's "not an error" lists. That is label
noise in the first experiment, not only classifier failure:
- `朋友们没在群里发消息了` is acceptable colloquial Mandarin, meaning "they no longer post in the group" (没…了 as a
  change of state). jev scoring it as natural was arguably correct.
- `这个毛衣` uses 个 as a general classifier, which is acceptable in speech (the report already flags this).
- `更上一层天` / `更上一层楼层` break a fixed idiom but were labelled `wrong_sense`. Under this taxonomy, an idiom
  corruption is a collocation error, and neither item changes the target's sense.
- `只要用心，你也他的好品质可学到` was labelled subtle, but it is plainly garbled (obvious).

Every type below therefore carries an explicit "Not an error" list, and the verification rules make the reviewer
check candidate items against it.

### 0.7 Common corruption rules (apply to all three languages)

- **C1 Source.** Start only from a sentence a reviewer has confirmed fully correct: a live P1 sentence rated
  4–5 by the live judge **and** read by a fluent speaker. If the source is doubtful, skip it. Never "fix it
  first".
- **C2 One error.** Make exactly one edit at one locus: insert, delete, replace, or move one word, particle,
  morpheme or constituent. Relational types (`contradiction`, `wrong_sense`, `target_*`) may rewrite one
  phrase, but the rewrite must introduce one defect only.
- **C3 Keep the target.** Keep the target word, in the locked sense, whole and literal, unless the type is
  `wrong_sense` or a `target_*` type. The target may take whatever inflection the edit forces.
- **C4 Keep the shape.** Keep length within about ±20% (zh ±3 characters, ja ±4 characters, en ±2 words for
  short sentences), and keep topic and tier. Do not introduce vocabulary above the source's tier. Sense and
  target types may change the surrounding context, but must still keep length and tier.
- **C5 No typos.** No misspellings, non-words, dropped punctuation or random character deletions. Apart from
  the three named swap types (§0.1), every word in the broken sentence must be a correctly written real word.
- **C6 Plausible errors only.** Make the error one a fluent writer or an LLM could produce: a learner-corpus
  error, an English calque, a near-miss word, or a wrong paradigm form. Do not produce random scrambles.
- **C7 One type only.** The edit must not also trigger another type. For example, a wrong classifier that also
  makes the sentence absurd is out. If an edit hits two types, choose a different edit.
- **C8 Standalone reading.** The broken sentence must be wrong with no supporting context. If adding a
  plausible preceding sentence would make it correct (contrastive は, sequential 了 + 才, ironic "so"), the item
  is invalid.
- **C9 Make "subtle" subtle.** Change a small form, not a content word. Keep every collocate that makes the
  sentence look normal. Prefer errors that need a non-local rule (把 + potential complement; と + request;
  "look forward to" + base verb), or a near-miss from the same family (same classifier family, homophonous
  kanji, same word family). Do not change rhythm, length or script mix. Do not stack cues. Then check C8 again.
  Subtle edits are the most likely to become accidentally acceptable.
- **C10 Hard negatives.** For every bucket, also write acceptable variants taken from the member types' "Not an
  error" lists: minimal edits that look like errors but are fine. Label them `variant_ok`. They measure
  precision, which is jev's known weakness.
- **C11 Contested forms.** Forms marked **(contested — exclude)** in any list must not be used as positives or
  as hard negatives.
- **C12 Record.** For each item record: source sentence id, target, sense id, tier, declared register, type id,
  subtlety, a one-line description of the edit (what changed, and why it is wrong), and the author's
  confidence (sure / fairly sure).

### 0.8 Common verification rules (the second reviewer's checklist)

The reviewer is a different person or agent from the author, and must not have seen the authoring context.

1. **Blind read first.** Read the broken sentence with only the target, the locked definition, the tier and the
   declared register, without the claimed type or edit note. Write down whether there is an error, and where.
   Reject if the blind read finds no error, or finds a different one.
2. **Unambiguously wrong.** Would a standard native speaker correct this sentence in a learner's textbook? If
   the answer is "it's colloquial", "some people say that", "regional" or "old-fashioned but fine", reject, or
   move it to the `variant_ok` pool if it is fully acceptable.
3. **Exactly one error.** Apply the inverse of the claimed edit. The result must be the original sentence, or
   another fully correct one. Then scan for a second defect. Any second defect, including a register shift
   caused by the edit, means reject.
4. **Type fit.** The error matches the claimed type's definition and is not an adjacent type (collocation vs
   anomaly, aspect vs complement, and so on). It must not appear in that type's "Not an error" list. If it fits
   another type cleanly, relabel it rather than reject it.
5. **Standalone.** Try to build one plausible preceding context that makes the sentence correct. If one exists
   (contrast, irony, a narrative sequence, dialect), reject.
6. **Target integrity.** For non-target types, the target is present, whole, literal and in the locked sense.
   For `wrong_sense`, the new sense must be a different sense in the dictionary (`dim_word_senses` or a
   standard dictionary), not a nuance of the same sense. For `target_*` types, check the defect with the
   language's tokenizer (§1.5, §2.5, §3.5) as well as by eye.
7. **Invariants.** Length, topic and tier are within C4. There are no typos (C5). The script is unchanged
   (C9, ja/zh).
8. **Subtlety.** Re-rate subtlety independently. If the reviewer's rating differs by one level, relabel. If it
   differs by two levels (obvious vs subtle), send the item back to the author.
9. **Corpus sanity check, where a corpus is available.** For collocation, preposition and particle items, and
   every subtle item, look up the broken string in a large edited corpus (zh: BCC or CCL; ja: BCCWJ; en: COCA
   or BNC). If the "broken" form is well attested in edited registers, it is a variant, so reject.
10. **Hard negatives too.** For each `variant_ok` item, confirm it is fully acceptable. If there is any doubt,
    drop it. Do not relabel it as a positive.
11. **Disagreement.** If the author and reviewer disagree after one exchange, discard the item. Do not argue it
    in. A discard rate of 10–20% is healthy. Above 30% for one type means that type's definition or its
    examples need work, so flag it.

Record each outcome as `accept`, `reject:<reason>`, `relabel:<new type or subtlety>`.

### 0.9 Question polarity

All draft questions are phrased so that **yes = clean**, matching the §3.1 questions ("is this grammatical?").
Bucket B5 (sense) and B6 (target) are sense-conditional: the classifier's `state` must include the target, the
locked definition and, for B8, the declared register. The examples in parentheses in the draft questions are
there for the question author. Test the final wording with and without them.

### 0.10 Sizing the buckets (≥30 examples each)

Per bucket, aim for at least:
- **≥30 positives** (broken sentences), spread evenly across member types: about 10 per type in a 3-type
  bucket, 15 in a 2-type bucket, 30 in a 1-type bucket. Within each type, split roughly evenly across the three
  subtlety levels.
- **≥30 negatives**: the ≥15 untouched originals of those same positives (a paired design, so separation can be
  measured per pair) plus ≥15 `variant_ok` hard negatives.
- **Cross-bucket negatives.** Broken sentences from *other* buckets are scored by this bucket's question too.
  The correct answer there is "yes" (no error of this bucket's kind), and that measures specificity.

That comes to roughly 60 authored items per bucket, or about 420–480 per language for zh and en (8 buckets
each). Since the 2026-09-28 fold, ja has 9 buckets (B1–B9), so its total is about 480–540. Draw on at least
150 distinct source sentences per language (ja: correspondingly more), so no source is used more than about
3 times.

---

## 1. Chinese (zh)

**Reference norm:** Mainland 普通话 in edited written form (规范汉语), simplified characters, as described in
《现代汉语词典》 (7th ed.) and standard grammars. Taiwan and Hong Kong standard usages are not errors.

### 1.1 Type list

| id | Name | One-line definition | Class | LLM freq. | Why that frequency | Bucket |
|---|---|---|---|---|---|---|
| `zh.measure_word` | Classifier phrase | Wrong or missing classifier in a numeral/demonstrative + classifier + noun phrase, or 们 after a numeral. | G | medium | Defaults to 个 (usually acceptable); slips on less common pairings (幅, 盏, 匹, 枚, 顶). | B1 |
| `zh.aspect_negation` | Aspect & negation | Misuse of 了/过/着/正在, or 不 vs 没 selection that clashes with the aspect. | G | medium | English past tense pulls 了 onto habitual or stative verbs; the largest zh grammar risk in translated-feeling T1–T2 sentences. | B1 |
| `zh.de_particle` | 的 / 地 / 得 | Wrong structural particle before a complement or adverbial, or an obligatory 得 missing. | G | low | Edited training text; per the 2026-09-27 user ruling, all 的/地/得 misuse (including 的 for 地) now counts as an error. | B1 |
| `zh.complement` | Verb complements | Wrong form or position of a resultative, directional, potential or degree complement. | G | low | Native-like on common verbs; rare verbs and object placement slip occasionally. | B2 |
| `zh.ba_bei` | 把 / 被 constructions | 把 with a bare verb, an indefinite object, a non-disposal verb or a potential complement; negation misplaced inside 把. | G | low | LLMs mostly avoid 把 when unsure. | B2 |
| `zh.separable_verb` | Separable verbs (离合词) | An object or aspect marker placed after a separable verb instead of inside it or before it. | G | low–medium | Rises when the *target itself* is a 离合词 and the generator wants to give it an object. | B2 |
| `zh.word_order` | Word order | Adverbs, time/place phrases, prepositional phrases or 比-comparatives in the wrong position. | G | low | Low for scrambles; medium for English-calque order (PP after the verb). | B3 |
| `zh.coverb` | Prepositions / coverbs | Wrong coverb (对, 给, 跟, 向, 离, 从, 在) or a broken fixed frame (对…来说). | G | low–medium | Calques from English prepositions. | B3 |
| `zh.connective` | Paired connectives | Mismatched or misplaced paired connectives (虽然…但是, 只要…就, 只有…才, 不但…而且). | G | low | LLMs over-pair (stylistic) more than they mis-pair. | B3 |
| `zh.collocation` | Collocation | Words that fit grammatically but are not the conventional pairing; the event itself is possible. | S | medium–high | Where fluent-but-wrong output concentrates, especially translationese verb–noun pairs. | B4 |
| `zh.topic_comment` | Subject/topic slot (话题—主语结构) | The pre-verbal subject/topic slot is filled in an English way that Mandarin does not allow. Authored positives: a dummy 它 as the subject of a closed-list weather verb (下雨, 下雪, 刮风, 起风, 打雷). Other English-style fillers of that slot are routing-only. | G | low | LLM zh rarely calques expletive "it". The risk rises in translationese T1 weather sentences built from an English prompt frame ("It rained all night"). | B4 |
| `zh.wrong_sense` | Wrong sense | The target carries a different dictionary sense from the locked one. | S | high | Generators drift to the most frequent sense of polysemous words (打, 开, 走, 深, 意思). | B5 |
| `zh.target_in_idiom` | Target in idiom | The target is present but inside a 成语, 惯用语 or set phrase that shifts its meaning. | T | low–medium | Rises at T5–T6, where generators reach for 成语 to sound advanced. | B5 |
| `zh.target_absent` | Target absent | The target does not occur: replaced by a synonym or a near-form, or dropped. | T | low | Almost always included; medium in rewrite/repair loops that "smooth" wording. | B6 |
| `zh.target_not_whole_word` | Target as fragment | The target's characters occur only inside a longer word. | T | medium (monosyllabic targets) | "Contains 学" is satisfied by 学校 or 学生. | B6 |
| `zh.semantic_anomaly` | Semantic anomaly | Grammatical, but the event is impossible or absurd (a selectional or role violation). | S | low (obvious) / medium (subtle) | Fluent, but slot-filling can pick an object the verb cannot take. | B7 |
| `zh.contradiction` | Contradiction / logic | Grammatical, but the sentence contradicts itself: a time clash, a relational impossibility, or a world-knowledge clash within the sentence. | S | low | Occasional time-word clashes in templated T1 sentences. | B7 |
| `zh.register` | Register mismatch *(stylistic, may be excluded)* | Formality or style clashes with the declared register or tier (书面语 in a child sentence, 网络用语 in formal). | R | high | LLMs drift formal (进行, 对于, 于, 之) regardless of tier. | B8 |

**Collocation vs anomaly (all languages).** Collocation: the event is fine but the wording is not
conventional (穿帽子: people do wear hats, but the verb is wrong). Anomaly: the event described cannot happen
(切汤: soup cannot be cut).

### 1.2 Type details

#### `zh.measure_word`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 我买了三本书。 | 我买了三书。 | Classifier dropped between numeral and noun. |
| moderate | 墙上挂着一幅画。 | 墙上挂着一把画。 | 把 is for objects with handles; paintings take 幅 or 张. |
| subtle | 教室里有三个学生。 | 教室里有三个学生们。 | 们 cannot follow a numeral + classifier phrase. |

Not an error:
- 个 as a general classifier in ordinary speech, including nouns with a specific classifier (一个毛衣,
  一个椅子). **Never corrupt to 个.**
- Alternative standard classifiers: 一条狗 / 一只狗; 一头猪 / 一只猪; 一台电脑 / 一部电脑; 一本书 / 一部书
  (for a work); 一位老师 / 一个老师 (位 is only more polite).
- Dropping 一 before a classifier (买了本书, 这是个好主意).
- No classifier with a demonstrative in casual or written style (这书不错, 那人是谁).

#### `zh.aspect_negation`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 我去过北京。 | 我不去过北京。 | Experiential 过 is negated with 没, never 不. |
| moderate | 他每天早上都跑步。 | 他每天早上都跑了步。 | Perfective 了 on a habitual event marked by 每天…都. |
| subtle | 他正在吃饭。 | 他正在吃完饭。 | Progressive 正在 cannot take a completed resultative (完). |

Not an error:
- 没…了 / 不…了 as a change of state ("no longer"): 他没钱了, 我不去了, 朋友们没在群里发消息了.
- 了 omitted in narrative when completion is clear from context or a time word (昨天我去商店买东西).
- 了 in future or conditional sequences (明天我吃了饭就去).
- 不 for past habits or refusals (他以前不吃辣, 那天他就是不去).
- 在 without 正; 着 + 呢 (门开着呢).
- 了 + habitual when followed by a sequencing clause (每天都跑了步才去上班). This is why items must be read
  standalone (C8).

#### `zh.de_particle`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 他说汉语说得很好。 | 他说汉语说很好。 | The degree complement requires 得. |
| moderate | 她唱歌唱得很好听。 | 她唱歌唱地很好听。 | 地 (adverbial marker) used where the complement marker 得 is required. |
| subtle | 我们认真地讨论了这个问题。 | 我们认真得讨论了这个问题。 | 得 used for a pre-verbal adverbial, which needs 地. |

Not an error:
- 的 dropped with kinship terms, institutions or close attributes (我妈妈, 我们学校, 中国人, 红花).
- Monosyllabic adverbs and reduplicated adverbials without 地 (好好学习, 慢慢走, 快走).

**User decision (2026-09-27):** any misuse of 的/地/得 — 的 for 得, 的 for 地, 地 for 的, or an obligatory 得
missing — is a `zh.de_particle` error, never acceptable variation. This revokes the former 的-for-地 "not an
error" exemption above and the 的-for-得 contested/exclude status under §0.7 C11; both are now plain positives.

#### `zh.complement`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 我听不懂他的话。 | 我不听懂他的话。 | The potential/resultative complement must be negated with infixed 不 (听不懂). |
| moderate | 我看完这本书了。 | 我看这本书完了。 | Resultative 完 split from its verb by the object. |
| subtle | 他已经回家去了。 | 他已经回去家了。 | The place object must go between 回 and 去. |

Not an error:
- Both orders with directional complements and ordinary objects (带来了一本书 / 带了一本书来).
- 看见 / 看到, 听见 / 听到 used interchangeably.
- Potential complement vs 能 (我去不了 / 我不能去): a nuance difference only.
- The degree complement with or without 很 (跑得快 / 跑得很快).

#### `zh.ba_bei`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 我把作业写完了。 | 我把作业写。 | The verb after 把 cannot be bare; it needs a complement, 了, or similar. |
| moderate | 我把那本书买了。 | 我把一本书买了。 | The object of 把 must be definite or specific. |
| subtle | 我解决不了这个问题。 | 我把这个问题解决不了。 | 把 is incompatible with a potential complement. |

Not an error:
- 被 with neutral or positive outcomes (他被选为班长, 他被老师表扬了).
- Notional passives with no marker (作业写完了, 饭做好了).
- 叫, 让 or 给 as passive markers in speech.
- Emphatic 给 in 把/被 sentences (他把杯子给打破了).
- 把 sentences ending in a directional complement only (把书拿出来).
- 没 before 把 (我没把门关上) is correct. 把门没关上 **(contested — exclude)**: it occurs in northern colloquial
  speech.

#### `zh.separable_verb`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 我明天跟朋友见面。 | 我明天见面朋友。 | 见面 is intransitive; the person must be introduced with 跟 or 和. |
| moderate | 我帮了他很多忙。 | 我帮忙了他很多。 | 帮忙 cannot take an object; the object goes inside the compound (帮他的忙) or with 帮. |
| subtle | 他们俩见过一次面。 | 他们俩见面过一次。 | 过 and a frequency expression go inside the separable verb. |

Not an error:
- Split forms (见了面, 睡了一觉, 帮个忙, 洗个澡, 生他的气). **The target is still present and whole** (see
  `zh.target_not_whole_word`).
- Unsplit with sentence-final 了 (他们见面了).
- Duration after the unsplit compound (游泳了一个小时, 睡觉睡了八个小时) **(contested — exclude)**: widely
  accepted in speech.

#### `zh.word_order`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 公司今年赚了很多钱。 | 公司赚了今年很多钱。 | A time word wedged between verb and object. |
| moderate | 我对中国文化很感兴趣。 | 我很感兴趣对中国文化。 | Prepositional phrase moved after the predicate (an English calque). |
| subtle | 我比他更喜欢音乐。 | 我更比他喜欢音乐。 | 更 must follow the 比-phrase, directly before the predicate. |

Not an error:
- Topicalization (这本书我看过了, 饺子我最喜欢吃).
- Time word before or after the subject (明天我去 / 我明天去).
- Post-verbal 在/到 + place with placement or arrival verbs (住在北京, 放在桌子上, 走到门口).
- Afterthoughts in dialogue (走吧，我们).
- Adverb order variants of equal standing (他每天都七点起床 / 他每天七点就起床).

#### `zh.coverb`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 我家离学校很近。 | 我家从学校很近。 | Distance takes 离, not 从 (which marks a starting point). |
| moderate | 她对音乐很感兴趣。 | 她给音乐很感兴趣。 | 感兴趣 takes 对. |
| subtle | 这件事对我来说很重要。 | 这件事给我来说很重要。 | Fixed frame 对…来说 broken. |

Not an error:
- 跟 / 和 / 同 / 与 for "with" (they differ in register, not correctness).
- 对 / 向 in 表示感谢.
- 给他打电话 / 跟他打电话.
- 往 / 向 for direction.
- 住北京 without 在 (colloquial).
- 对于 overuse (stylistic, `zh.register` at most).

#### `zh.connective`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 虽然下雨了，但是我们还是去了公园。 | 虽然下雨了，所以我们还是去了公园。 | A concessive 虽然 paired with causal 所以. |
| moderate | 只要你努力，就能学好中文。 | 只要你努力，才能学好中文。 | 只要 (sufficient condition) pairs with 就; 才 belongs with 只有. |
| subtle | 他不但会唱歌，而且会跳舞。 | 不但他会唱歌，而且会跳舞。 | With a shared subject, 不但 must follow the subject. |

Not an error:
- Using only one half of a pair (因为下雨，我们没去; 下雨了，所以没去).
- 但是 / 可是 / 不过 interchanged.
- A postposed 虽然 clause (我们还是去了，虽然下雨了).
- 如果…的话 with or without 就.
- Over-pairing (因为…所以 in a short sentence). That is stylistic.

#### `zh.collocation`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 他每天骑自行车上班。 | 他每天开自行车上班。 | Bicycles are 骑, not 开. |
| moderate | 他戴着一顶帽子。 | 他穿着一顶帽子。 | Hats are 戴 (accessories), not 穿 (garments). |
| subtle | 我们要尊重别人的意见。 | 我们要尊敬别人的意见。 | 尊敬 takes people; opinions take 尊重. |

Not an error:
- Near-synonymous attested collocates (提高 / 改善 生活水平; 看书 / 读书; 做 / 干活; 打游戏 / 玩游戏;
  开车 / 驾驶汽车 with a register difference).
- All-purpose colloquial verbs (搞, 弄, 整) in casual register.
- Fixed idioms used intact.
- Older or Europeanized formal collocations attested in edited text (对…发生影响). Run the corpus check, V9.

#### `zh.topic_comment`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| moderate | 下雨了，我们快回家吧。 | 它下雨了，我们快回家吧。 | Dummy sentence-initial 它, a word-for-word match of English "It's raining"; 下雨 takes no subject. |
| moderate | 外面正在下雪。 | 外面它正在下雪。 | 它 inserted after the non-referential place topic 外面, which it cannot resume. |
| moderate | 因为昨天下了一夜的雪，路上很滑。 | 因为昨天它下了一夜的雪，路上很滑。 | Dummy 它 inside a subordinate clause, after a time word. |

**Single-level type (known limitation).** Every authored positive is `moderate`: a stray 它 is obvious to any
native reader, but an L1-English learner may not notice it. The §0.4 three-way subtlety split does not apply
to this type.

Not an error:
- Weather sentences with no subject, or with a place or time topic (下雨了, 外面下雨了, 山上下雪了,
  昨天刮了一天风).
- 天 as the subject (天下雨了, 天阴了).
- 它 with a real antecedent in the same sentence (那只猫很可爱，它每天都睡在沙发上).
- Topicalization and double subjects (这本书我看过了, 大象鼻子很长). Already covered under `zh.word_order`.
- Subject omission (pro-drop) in any register.
- Indefinite subjects introduced by 有 (有一本书在桌子上 / 桌子上有一本书).
- Dummy-**object** 它 (管它下不下雨, 由它下吧, 睡它一觉). This is correct; never use it as a source or positive.
- A resumptive 它 right after a fronted topic (那只猫它…), a preverbal indefinite subject of a locative
  predicate (一本书在桌子上), 关于/对于 introducing a fronted object topic, a 在-phrase as the subject of 是, and
  它 with time/temperature/distance predicates (它很冷, 它八点了): all **(contested — exclude)** and
  routing-only (a real occurrence in live output is labelled `zh.topic_comment`, but none of these is authored).

#### `zh.wrong_sense`
| Level | Target — locked sense | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | 打 — to hit, strike | 弟弟不小心打了我一下。 | 弟弟晚上给我打了个电话。 | 打 now means "make (a phone call)". |
| moderate | 意思 — meaning (of a word) | 这个词是什么意思？ | 这点小礼物，是我的一点意思。 | 意思 now means "a token of regard". |
| subtle | 深 — physically deep | 这条河很深，不能游泳。 | 这本书的内容很深，孩子看不懂。 | 深 now means "profound": a metaphorical extension listed as a separate sense. |

Not an error:
- A sentence where both senses are possible but the locked one is the natural reading.
- Sub-senses the dictionary does not separate. Check `dim_word_senses`: if the "other sense" is not a separate
  entry there, it is the same sense.
- The locked sense applied to a new but still physical referent (伤口很深, 雪很深 for 深 = physically deep).
- A figurative use that the dictionary does not list as a separate sense.

#### `zh.target_in_idiom`
| Level | Target — locked sense | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | 马 — horse | 草原上有很多马。 | 他做作业总是马马虎虎的。 | 马 is swallowed by 马马虎虎 ("careless"). |
| moderate | 醋 — vinegar | 吃饺子要蘸醋。 | 看到女朋友和别人说话，他吃醋了。 | 吃醋 = "be jealous": 醋 is a whole word but not vinegar. |
| subtle | 饭碗 — rice bowl | 桌子上放着一个饭碗。 | 他上个月丢了饭碗。 | 丢饭碗 = "lose one's job": no figurative cue on the surface. |

Not an error:
- The target in a fixed but **literal** collocation (吃饭, 喝水, 开门).
- An idiom whose meaning *is* the locked sense (if the locked sense of 吃醋 is "be jealous", it is correct).
- The target inside an idiom that keeps its literal sense (the target is present and literal). The whole-word
  check still applies.

#### `zh.target_absent`
| Level | Target | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | 高兴 | 看到你我很高兴。 | 看到你我很累。 | Target and its meaning gone. |
| moderate | 高兴 | 看到你我很高兴。 | 看到你我很开心。 | Synonym substituted. |
| subtle | 认识 | 你认识他吗？ | 你认得他吗？ | Near-form sharing a character (认得); the target is absent. |

Not an error:
- Reduplication (高高兴兴, 看看, 试一试).
- Split separable verbs (见了面).
- Infixed potential forms (看不见 for 看见).
- Attached aspect markers or 们/儿 (朋友们, 玩儿).

#### `zh.target_not_whole_word`
| Level | Target | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | 学 — to study | 我在学中文。 | 我在学校等你。 | 学 appears only inside 学校. |
| moderate | 车 — vehicle | 我的车坏了。 | 我去车站等你。 | 车 appears only inside 车站. |
| subtle | 人 — person | 他是个好人。 | 他是个好人才。 | Segmentation 好 / 人才: the string 好人 is visible, but 人 belongs to 人才. |

Not an error:
- Verb + complement where the target keeps its sense (学会, 看完, 写好 for targets 学, 看, 写).
- Split separable verbs.
- Reduplication.
- 儿化 and 们.

#### `zh.semantic_anomaly`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 我把苹果放进了冰箱里。 | 我把冰箱放进了苹果里。 | Roles swapped: impossible containment. |
| moderate | 我们在河里钓到了一条鱼。 | 我们在河里钓到了一只鸡。 | Fishing yields a chicken. |
| subtle | 他把肉切成了小块。 | 他把汤切成了小块。 | Soup cannot be cut into pieces; the frame 把…切成了小块 stays fluent. |

Not an error:
- Personification in children's-story register (小猫说："我饿了。", 太阳公公笑了). This is acceptable at T1–T2.
- Conventional metaphor (时间在流逝, 心都碎了).
- Hyperbole (饿死了, 累得要命).
- Figurative idioms (喝西北风).

#### `zh.contradiction`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 他从来没去过北京，明年想去看看。 | 他从来没去过北京，去年还在北京住了一个月。 | The second clause contradicts "never been". |
| moderate | 他比我大两岁，所以他是我哥哥。 | 他比我大两岁，所以我是他哥哥。 | Relational impossibility. |
| subtle | 秋天到了，树叶都黄了。 | 秋天到了，树叶都绿了。 | A within-sentence world-knowledge clash: autumn → leaves turn green. |

Not an error:
- Surprising concessions (他很累，但还是去了).
- Future perfect with 了 (明天这个时候他已经走了).
- Irony in dialogue.
- 虽然 + unexpected outcome.

#### `zh.register` *(stylistic, may be excluded)*
| Level | Declared | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | neutral, T1 | 小猫在沙发上睡觉。 | 小猫于沙发之上安寝。 | Classical written style in a toddler-tier sentence. |
| moderate | casual | 妈妈，我饿了，你给我做饭吧。 | 妈妈，我饿了，烦请您拨冗为我做饭。 | Formal-letter formula (烦请, 拨冗) addressed to a parent. |
| subtle | casual | 我们周末一起去公园玩吧。 | 我们周末一同前往公园玩吧。 | Written-register 一同, 前往 mixed with casual 玩吧. |

Not an error:
- 您 vs 你 chosen by relationship.
- 书面语 in T5–T6 sentences on formal topics when the declared register is formal.
- Modal particles (呢, 吧, 啊) in dialogue.
- 进行 + verb in news or formal register.

### 1.3 Question buckets (zh)

| Bucket | Name | Member types | Draft question (yes = clean) |
|---|---|---|---|
| zh.B1 | Measure words & particles | measure_word, aspect_negation, de_particle | "Are all the measure words, the particles 了 / 过 / 着 / 的 / 地 / 得, and the negation words 不 / 没 used correctly?" |
| zh.B2 | Verb constructions | complement, ba_bei, separable_verb | "Are the verb constructions correct: verb complements (看完, 听不懂, 回家去, 跑得快), 把 and 被 sentences, and separable verbs such as 见面 or 帮忙?" |
| zh.B3 | Word order & linking words | word_order, coverb, connective | "Are the words in a correct order, and are prepositions (对, 给, 离, 从, 跟) and linking words (虽然…但是, 只要…就) used correctly?" |
| zh.B4 | 搭配与主语习惯 (Collocation & subject slot) | collocation, topic_comment | 「句中的词语搭配和主语是否都符合汉语母语者的习惯？（省略主语、把话题放在句首都是正常的。）」 |
| zh.B5 | Target sense | wrong_sense, target_in_idiom | "Is 「{target}」 used here with the meaning '{definition}', literally, and not inside an idiom or set phrase that changes its meaning?" |
| zh.B6 | Target presence | target_absent, target_not_whole_word | "Does 「{target}」 appear in the sentence as a word in its own right: not missing, not replaced by another word, and not just a character inside a longer word?" |
| zh.B7 | Meaning & logic | semantic_anomaly, contradiction | "Does the sentence describe something that makes sense and could really happen, without contradicting itself?" |
| zh.B8 | Register *(optional)* | register | "Does the sentence's style (written/formal vs spoken/casual) match '{register}' and suit a learner at tier {tier}?" |

Notes:
- B1 follows the grouping suggested in the brief ("measure words and aspect particles"). It is the bucket where
  jev was weakest in §3.1, so give it the most `variant_ok` hard negatives (个 as a general classifier, 没…了,
  的 for 地).
- B6 can be checked more cheaply and exactly in code (a string match plus jieba segmentation). Keep it in the
  eval set to measure jev, but in production run the deterministic check first.
- zh.B4 (2026-09-28) now also covers the subject/topic slot (`zh.topic_comment`), authored only as a capped
  diagnostic slice of about 8 moderate positives; collocation keeps about 22. `zh.connective` subject-placement
  positives (不但他会唱歌…) and `zh.word_order` positives that move the subject are excluded from zh.B4's
  cross-bucket negative set and reported separately as a diagnostic, because 「主语」 invites a legitimate "no"
  on them. `zh.topic_comment` positives stay in zh.B1, zh.B3 and zh.B7's cross-bucket sets: the particles, word
  order and event described are all otherwise fine, so "yes" is correct there.

### 1.4 Corruption rules — zh additions

- Never corrupt *to* 个 (`zh.measure_word`). Never corrupt 地 → 的. Never use 没…了 or 不…了 as a positive.
- `zh.de_particle` positives use only three edits: 得 removed, 得 → 地, 地 → 得.
- `zh.aspect_negation` positives must be wrong without a following clause (C8); do not use 了 + habitual if the
  source continues with 才, 就 or a second event.
- If the target is a 离合词, a corruption of another type must leave the target's split or unsplit status
  unchanged.
- Keep full-width punctuation and simplified characters. Do not introduce traditional characters.
- Idiom corruptions (breaking a 成语 by swapping one character) are **`zh.collocation`**, not `wrong_sense`,
  and only if the target is not inside the idiom.
- `zh.topic_comment` positives insert 它 only as the subject of a closed-list weather verb (下雨, 下雪, 刮风,
  起风, 打雷); never as a dummy object. The source must not contain any noun 它 could pick up as an antecedent.
  Any topic before 它 must be non-referential (外面, or a time word), never a named or demonstrative place. Cap
  at about 8 positives, all moderate, each paired with a `variant_ok` item that has both a real-antecedent 它
  and a weather verb. If fewer than about 6 confirmed sources exist, treat `zh.topic_comment` as routing-only
  rather than relaxing C1.

### 1.5 Verification rules — zh additions

- Segment the broken sentence with jieba (or pkuseg) for every `target_*` item. Confirm the target is (absent)
  or is not (fragment) a standalone token. Segmentation errors from the tool are possible, so the final call is
  by eye.
- For every collocation, coverb and subtle item, search the broken string in BCC (BLCU) or CCL (PKU). If it
  appears as ordinary usage in news or literary text, reject it (V9).
- Check each item against the regional-variant list in §1.2. Anything standard in Taiwan usage is a reject.
- Where you can construct a "no longer" reading (没/不…了) or a sequence reading (V了…才), reject (V5).
- For `zh.topic_comment`, try a place-antecedent reading (e.g. "伦敦呢？——它下雨了"). If the reviewer finds it
  acceptable, reject the item (V5).

---

## 2. Japanese (ja)

**Reference norm:** 共通語 as used in edited writing (newspapers, NHK, textbooks). Politeness is judged against
the sentence's declared register (`plain` / `polite` / `honorific` / `humble` / `formal` / `casual`, the values
the live ja judge uses). Kana vs kanji spelling of a word is **never** an error unless the type is
`ja.kanji_choice`.

### 2.1 Type list

| id | Name | One-line definition | Class | LLM freq. | Why that frequency | Bucket |
|---|---|---|---|---|---|---|
| `ja.case_particle` | Case particles | Wrong case particle (が, を, に, で, へ, と, から) for the verb or predicate. | G | medium | Verbs whose English equivalent is transitive (乗る, 会う, 賛成する) pull を. | B1 |
| `ja.wa_ga` | は / が (structural only) | は where a structural rule requires が: question-word subject, inside a relative clause, subject of a subordinate clause that differs from the main subject. | G | low | Main-clause は/が is fluent. Structural slips are rare. | B1 |
| `ja.counter` | Counters (助数詞) | Wrong counter for the noun, including homophonous counters (軒/件). | G | low–medium | Common counters are fine; 本/冊/枚 and 軒/件 slip. | B1 |
| `ja.conjugation` | Conjugation | A wrong inflected form of a verb, i-adjective or na-adjective, including the wrong verb class (godan treated as ichidan). | G | low | Rare in LLM output, except with uncommon verbs. | B2 |
| `ja.transitivity_voice` | 自動詞/他動詞 & voice | The wrong member of a transitive/intransitive pair, or passive/causative mismatched with its particles. | G | medium | 自他 pairs are a classic confusion; English voice leaks in. | B2 |
| `ja.tam` | Tense, aspect, modality | Wrong tense for the time frame, wrong ている/てある/ておく, relative-tense errors in 前に/後で clauses, or the まだ + negative form. | G | medium | Relative tense in subordinate clauses and ている are where LLM Japanese slips. | B2 |
| `ja.modification` | Noun-modification form | Wrong connecting form before a noun (い/な/の), or a modifier that does not precede its head. | G | low | Rare; LLMs attach adjectives correctly. | B3 |
| `ja.clause_linkage` | Clause linkage | Wrong connector or conditional: から/ので/のに, と/たら/ば/なら with a request, ために vs ように. | G | medium–low | Conditional and purpose rules are usually but not always respected. | B3 |
| `ja.topic_comment` | 主題と述語の対応（主述のねじれ） | The は-topic is a closed-list noun that requires a nominal comment (夢・目標・希望・趣味・目的 → ～ことです; 理由・原因 → ～からです/～ためです), but the sentence ends in a finite verbal predicate instead. は/が themselves are never edited. | G | low | LLM Japanese usually produces 夢は～ことです correctly. The residual risk is a long 理由は-clause that ends in a plain past verb, and the English "My dream is (that) I want to…" calque. | B3 |
| `ja.collocation` | Collocation | Grammatical but not the conventional verb–noun pairing (薬を飲む, 風邪をひく). | S | medium | Calques of English verbs (take, catch, give). | B4 |
| `ja.kanji_choice` | Kanji choice (同音異義 / 異字同訓) | The wrong kanji among homophones: a real, correctly written word, but the wrong one. | S | low–medium | Mostly right; errors on 異字同訓 sets (計る/測る/量る, 変える/替える/換える, 暑い/熱い). | B4 |
| `ja.wrong_sense` | Wrong sense | The target carries a different dictionary sense from the locked one. | S | high | Kana-heavy and polysemous lemmas (かける, はかる, 甘い, 明るい) drift to the frequent sense. | B5 |
| `ja.target_in_idiom` | Target in idiom | The target is inside a 慣用句 that shifts its meaning (顔が広い, 腹が立つ, 猫の手も借りたい). | T | medium | Body-part and animal nouns (手, 顔, 腹, 気, 目, 猫) are idiom magnets. | B5 |
| `ja.target_absent` | Target absent | The target does not occur: a synonym, a suppletive keigo verb, or a different verb sharing the kanji. | T | low–medium | Suppletive honorific forms (召し上がる for 食べる) remove the target silently. | B6 |
| `ja.target_not_whole_word` | Target as fragment | The target occurs only inside a longer word or a lexical compound verb. | T | medium | Single-kanji targets (手, 車, 会) and 見る/見つける. | B6 |
| `ja.semantic_anomaly` | Semantic anomaly | Grammatical, but the event is impossible or absurd. | S | low | Fluent generator. | B7 |
| `ja.contradiction` | Contradiction / logic | Grammatical, but the sentence contradicts itself (time, kinship, cause–effect). | S | low | Occasional kinship and time slips. | B7 |
| `ja.keigo` | Keigo direction | Honorific (尊敬語) used for the speaker's in-group action, or humble (謙譲語) used for a superior's action. | G | medium–high | LLM Japanese mixes up keigo direction more than other grammar, and overuses させていただく. | B8 |
| `ja.register` | Register mismatch *(stylistic, may be excluded)* | Politeness level or written/spoken style clashes with the declared register (です/ます mixed with だ in the main clause, である in a casual sentence, slang in polite). | R | high | Declared register is often ignored; ため/しかしながら creep into casual sentences. | B8 |
| `ja.particle_other` | Focus, limit & listing particles (取り立て・限度・並列の助詞) | A focus, limit, comparison or listing particle that breaks its own rule. Authored positives cover three patterns: (P1) a negative-polarity particle — しか, comparative ほど (A は B ほど ～), も in 誰も/何も/どこも — with an affirmative predicate; (P2) a time-point noun + まで where a one-time action that must be finished by that time needs までに; (P3) non-exhaustive や/とか in a list closed by a count or totalising noun. | G | low–medium | LLM Japanese uses も/だけ fluently. The remaining slips come from English: "by Friday" and "until Friday" both come out as まで, and "and" comes out as や in a closed list. Negative-polarity breaks are rare. | B9 |

### 2.2 Type details

#### `ja.case_particle`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 毎朝電車に乗ります。 | 毎朝電車を乗ります。 | 乗る takes に for the vehicle. |
| moderate | 公園で子どもたちが遊んでいます。 | 公園に子どもたちが遊んでいます。 | The location of an activity takes で. |
| subtle | 机の上に本があります。 | 机の上で本があります。 | The location of existence (ある/いる) takes に; で is only for events (会議が会議室である). |

Not an error:
- が/を alternation with potential forms and ～たい (水が飲みたい / 水を飲みたい; 寿司が食べられる / 寿司を食べられる).
- を for a traversed path (道を歩く, 山を登る, 橋を渡る).
- に/へ for destination.
- 友達に会う / 友達と会う.
- 家を出る / 家から出る.
- 母に似ている / 母と似ている.
- 友達に借りる / 友達から借りる.
- Particle dropping in casual speech (ご飯食べた？).
- 気持ちを分かる **(contested — exclude)**.

#### `ja.wa_ga`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 誰が来ましたか。 | 誰は来ましたか。 | A question-word subject cannot be marked with は. |
| moderate | 私が作ったケーキを食べてください。 | 私は作ったケーキを食べてください。 | The subject inside a relative clause takes が (or の), not は. |
| subtle | 母が帰ってきたとき、私は寝ていました。 | 母は帰ってきたとき、私は寝ていました。 | The subject of a とき-clause that differs from the main-clause subject takes が. |

Not an error:
- **Almost every main-clause は/が choice.** Both are grammatical and differ only in topic, contrast or
  exhaustive focus. Only the three structural rules above are errors.
- も replacing は or が.
- Contrastive は in subordinate clauses when the contrast is overt (雨は降ったが、風は吹かなかった).
- Particle omission in casual speech.
- Never corrupt は ↔ が in a main clause.

#### `ja.counter`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 猫が二匹います。 | 猫が二枚います。 | 枚 is for flat objects. |
| moderate | 本を三冊買いました。 | 本を三本買いました。 | Books take 冊; 本 is for long, thin objects. |
| subtle | 通りに家が三軒並んでいます。 | 通りに家が三件並んでいます。 | Homophonous counter: 件 counts matters or cases, not buildings. |

Not an error:
- General つ for objects (りんごを三つ).
- 個 for many small objects (りんご3個, 消しゴム2個).
- 匹 / 頭 for mid-size animals where both occur.
- 人 / 名 (register only).
- Numbers without counters in lists or dates.
- 本 for bottles and pens.
- Arabic numerals vs kanji numerals.

#### `ja.conjugation`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 昨日、友達と映画を見ました。 | 昨日、友達と映画を見るました。 | ます attaches to the stem, not the dictionary form. |
| moderate | この部屋は静かじゃありません。 | この部屋は静かくないです。 | A na-adjective conjugated as an i-adjective. |
| subtle | 早く家に帰って休みたい。 | 早く家に帰て休みたい。 | 帰る is godan despite ending in -eru; its te-form is 帰って. This is a wrong-paradigm error, not a dropped kana. |

Not an error:
- ら抜き言葉 (見れる, 来れる, 食べれる): widespread and tolerated in speech.
- い-adjective + です (高いです).
- ～ません / ～ないです.
- Contracted forms in casual register (～ちゃう, ～てる, ～とく, ～なきゃ).
- さ入れ言葉 (書かさせる) and 違くて **(contested — exclude)**.

#### `ja.transitivity_voice`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 電気をつけてください。 | 電気をついてください。 | Intransitive つく cannot take を or a request. |
| moderate | ドアが閉まりました。 | ドアが閉めました。 | Transitive 閉める with the patient marked が and no agent. |
| subtle | 電気がつけてあります。 | 電気がついてあります。 | ～てある requires a transitive verb (resultative of a deliberate action). |

Not an error:
- ～てある with を (電気をつけてある).
- Verbs that are both transitive and intransitive (開く read ひらく, 増す, 終わる in 会議を終わる — the last is
  dated; prefer not to use it).
- Adversative passive of intransitives (雨に降られた).
- Non-adversative passive in written style.
- 始める / 始まる both used with 会議 (with the appropriate particle).

#### `ja.tam`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 昨日、図書館へ行きました。 | 昨日、図書館へ行きます。 | Non-past with a past time adverb. |
| moderate | まだ昼ご飯を食べていません。 | まだ昼ご飯を食べませんでした。 | "Not yet" requires まだ + ～ていない. |
| subtle | 寝る前に歯を磨きます。 | 寝た前に歯を磨きます。 | 前に requires the non-past form (and 後で the past). |

Not an error:
- Non-past for scheduled future events.
- た for discovery or recall (あ、ここにあった; 会議は何時でしたっけ).
- Historical present in narrative.
- ている for habitual or resultant states (結婚している, 毎朝走っている).
- ～ておく vs the plain verb.
- でしょう / だろう / と思う variation.

#### `ja.modification`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 大きい犬がいます。 | 大きいの犬がいます。 | An i-adjective attaches directly, with no の. |
| moderate | 静かな部屋で勉強します。 | 静かの部屋で勉強します。 | A na-adjective needs な before a noun. |
| subtle | 病気の友達のお見舞いに行きました。 | 病気な友達のお見舞いに行きました。 | 病気 is a noun (の), not a na-adjective. |

Not an error:
- Prenominal 大きな / 小さな.
- 同じ + noun without な.
- Scrambled argument order (寿司を私は食べた).
- 倒置 (inverted order) in casual speech (行こうよ、一緒に).
- Words that take both な and の (特別な / 特別の, 自由な).

#### `ja.clause_linkage`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 雨が降っているので、傘を持っていきます。 | 雨が降っているのに、傘を持っていきます。 | Concessive のに where the relation is causal. |
| moderate | 駅に着いたら、電話してください。 | 駅に着くと、電話してください。 | A と-conditional cannot take a request or volitional main clause. |
| subtle | 日本語が話せるように、毎日練習しています。 | 日本語が話せるために、毎日練習しています。 | ために needs a volitional verb; a potential or non-volitional verb takes ように. |

Not an error:
- から / ので interchanged.
- が / けど / けれども.
- たら where ば or と would also be fine for general truths.
- ～て for sequence or loose cause.
- Sentence-final のに expressing regret.
- ～ば with a request when the ば-clause is stative (時間があれば来てください).

#### `ja.topic_comment`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 私の趣味は本を読むことです。 | 私の趣味は本を読みます。 | 読むことです → 読みます. The topic 趣味 now has an action verb as its comment ("my hobby reads books"). |
| moderate | 私の夢は医者になることです。 | 私の夢は医者になりたいです。 | The classic ねじれ that 作文指導 corrects: a 夢 topic needs ～ことです, not ～たいです. |
| moderate | 昨日遅れた理由は電車が止まったからです。 | 昨日遅れた理由は電車が止まりました。 | からです → a finite past verb, same tense. A 理由 topic needs ～からです. Topic deletion leaves 電車が止まりました, which is correct. |

**Two-level type.** The sentence-final predicate complex (verb + auxiliaries + こと/から/ため + です) is edited
as one constituent (C2), so J1 items are never `subtle` (C9 requires a one-morpheme edit). Keep 私の in every
趣味 item, and prefer sources with no comma after 理由は/原因は.

**Decisive test (topic-deletion).** Delete the whole closed-list は-phrase (私の趣味は, 昨日遅れた理由は). The
item belongs to this type only if the broken sentence is wrong **and** what remains after deletion is a fully
correct sentence on its own (本を読みます, 医者になりたいです, 電車が止まりました). `ja.tam`, `ja.conjugation`,
`ja.keigo` and `ja.register` errors survive the deletion and fail this test.

Not an error:
- Noun comments (趣味は読書です, 夢は医者だ). ～ことだ vs ～ことです is register only.
- うなぎ文 and こんにゃく文 (僕はうなぎだ, こんにゃくは太らない).
- 象は鼻が長い-type double-subject sentences, and 象の鼻は長い.
- ～ということです, ～ことなんです, and 理由は～からだ / ～ためだ / ～ことだ. 原因は～ことです.
- 理由 or 夢 used as a plain subject rather than a topic–comment frame (理由が二つあります, 夢を見た).
- Topic heads outside the closed list (今日は, 私は).
- Subject omission.
- A て-form continuation that leaves the frame (趣味は本を読むことで、…).
- An expletive or doubled topic calqued from English (それは雨が降っています, 私は私の部屋を…): routing-only,
  never authored under any type, because inserting は falls outside `ja.wa_ga`'s three structural rules.
- An i-adjective comment without こと (この町のいいところは、公園が多いです), 理由は～んです / ～のです, and
  目的は～ためです: all **(contested — exclude)**.

#### `ja.collocation`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 毎日薬を飲みます。 | 毎日薬を食べます。 | Medicine is 飲む regardless of form. |
| moderate | 先週、風邪をひきました。 | 先週、風邪をとりました。 | 風邪 takes ひく (a calque of "catch" or "get"). |
| subtle | その本は私に大きな影響を与えました。 | その本は私に大きな影響をあげました。 | 影響 takes 与える; あげる is only for giving things. |

Not an error:
- 電話をかける / 電話する.
- シャワーを浴びる / シャワーする.
- 写真を撮る / 写真を写す.
- 眼鏡をかける / 眼鏡をする.
- 辞書を引く / 辞書で調べる.
- 決心する / 決心がつく.

#### `ja.kanji_choice`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 駅で友達に会いました。 | 駅で友達に合いました。 | 合う means "fit, match"; meeting a person is 会う. |
| moderate | 今日はとても暑いです。 | 今日はとても熱いです。 | 熱い is for objects and liquids; weather is 暑い. |
| subtle | 彼の努力に感心しました。 | 彼の努力に関心しました。 | 関心 (interest) is a noun that does not take する; 感心 (admiration) is the verb. |

Not an error:
- Kana instead of kanji (わかる / 分かる, ください / 下さい, こども / 子ども / 子供).
- Okurigana variants (行う / 行なう).
- Pairs where both kanji are standard for the context (聞く / 聴く for music, 早い / 速い in some uses).
- 当て字 in names.

#### `ja.wrong_sense`
| Level | Target — locked sense | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | かける — to hang (something) | 壁に絵をかけました。 | 友達に電話をかけました。 | かける now means "make (a call)". |
| moderate | 甘い — sweet (taste) | このケーキはとても甘い。 | 父は子どもにとても甘い。 | 甘い now means "lenient". |
| subtle | 明るい — bright, full of light | この部屋は窓が大きくて明るい。 | 彼女は性格がとても明るい。 | 明るい now means "cheerful": a metaphorical extension listed as a separate sense. |

Not an error:
- The same as `zh.wrong_sense`: dictionary-internal nuances are not different senses. Check the sense inventory.
- A kanji-disambiguated homograph that matches the locked sense (測る for "measure length"), even if another
  はかる exists.

#### `ja.target_in_idiom`
| Level | Target — locked sense | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | 猫 — cat | 猫がソファで寝ている。 | 年末は猫の手も借りたいほど忙しい。 | 猫 is inside 猫の手も借りたい ("extremely busy"). |
| moderate | 顔 — face | 毎朝顔を洗う。 | 彼は顔が広い。 | 顔が広い = "well-connected". |
| subtle | 腹 — belly | 食べすぎて腹が痛い。 | 彼の態度に腹が立った。 | 腹が立つ = "get angry"; it is so frequent it does not feel idiomatic. |

Not an error:
- Literal fixed collocations (手を洗う, 目を閉じる).
- An idiom whose meaning is the locked sense.
- Compound nouns that keep the target's meaning are not idioms (but see `ja.target_not_whole_word`).

#### `ja.target_absent`
| Level | Target | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | 食べる | 朝ご飯を食べました。 | 朝ご飯を作りました。 | Target and meaning gone. |
| moderate | 食べる | 先生、お昼はもう食べましたか。 | 先生、お昼はもう召し上がりましたか。 | The suppletive honorific 召し上がる is a different lexeme, so 食べる is absent. The sentence is otherwise better Japanese. |
| subtle | 見る | 窓から山を見ます。 | 窓から山が見えます。 | 見える is a separate verb sharing the kanji. |

Not an error:
- Any inflection, including passive, causative and potential (食べた, 食べられない, 食べさせる, 見られる).
- ら抜き potential.
- Kana or kanji spelling of the target, and okurigana variants.
- The polite prefix on a lexicalised form (お茶 for 茶).
- The *regular* honorific pattern of the target (お読みになる for 読む). The target stem is present, so this is
  not absent. Suppletive forms (召し上がる, いらっしゃる, おっしゃる, 申す, 参る) are absent.

#### `ja.target_not_whole_word`
| Level | Target | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | 手 — hand | 手が冷たいです。 | 歌が上手です。 | 手 appears only inside 上手. |
| moderate | 車 — car | 車で行きます。 | 電車で行きます。 | 車 appears only inside 電車. |
| subtle | 見る — to look at | 部屋で古い写真を見ました。 | 部屋で古い写真を見つけました。 | 見つける ("find") is a lexical compound verb, not an inflection of 見る. |

Not an error:
- Syntactic V–V compounds, where the target is still the event and the second verb is aspectual (見始める,
  食べ終わる, 読み続ける, 書き直す, 食べすぎる). Kageyama (1993) distinguishes these from lexical compounds
  (見つける, 飛び込む, 見合う).
- Auxiliary suffixes on the stem (食べたい, 降りそう, 読みやすい).
- Derived nouns in ～方 / ～物 (読み方, 食べ物) **(contested — exclude)**: the target's sense survives, but it no
  longer does its own grammatical job.

#### `ja.semantic_anomaly`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | オーブンでパンを焼きました。 | 冷蔵庫でパンを焼きました。 | You cannot bake in a refrigerator. |
| moderate | 猫が木に登っています。 | 魚が木に登っています。 | Fish do not climb trees (outside fantasy). |
| subtle | 氷が溶けて、水になりました。 | 氷が溶けて、固くなりました。 | Melting makes things soft or liquid, not hard. |

Not an error:
- Anthropomorphism in children's-story register (うさぎさんがケーキを焼きました).
- Conventional metaphor (時間が流れる).
- Hyperbole (死ぬほどお腹が空いた).
- Idioms.

#### `ja.contradiction`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 彼は一度も日本に行ったことがないので、来年行きたい。 | 彼は一度も日本に行ったことがないが、去年は東京に住んでいた。 | Contradicts "never been". |
| moderate | お腹がいっぱいなので、もう何も食べられません。 | お腹がいっぱいなので、もっと食べたいです。 | The stated cause contradicts the result. |
| subtle | 兄は私より三歳年上です。 | 兄は私より三歳年下です。 | An older brother (兄) cannot be younger. |

Not an error:
- Concessive のに or けど with surprising outcomes.
- Jokes marked as such (デザートは別腹).
- Future perfect expressed with ている / た.

#### `ja.keigo`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 先生がいらっしゃいました。 | 先生が参りました。 | Humble 参る used for a superior's action. |
| moderate | 私が先生の荷物をお持ちします。 | 私が先生の荷物をお持ちになります。 | Honorific お～になる used for the speaker's own action. |
| subtle | 社長はもうお帰りになりました。 | 社長はもうお帰りしました。 | Humble お～する used for a superior (very common even among natives, but wrong). |

Not an error:
- Established double honorifics listed as acceptable in 敬語の指針 (お召し上がりになる, お伺いする).
- Humble forms for in-group family members speaking to outsiders (母が申しておりました).
- 丁寧語 (です/ます) alone without 尊敬語 toward a superior in neutral-polite register.
- ～させていただく overuse (stylistic).
- おっしゃられる, ご覧になられる **(contested — exclude)**.

#### `ja.register` *(stylistic, may be excluded)*
| Level | Declared | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | polite | 明日は雨が降るでしょう。 | 明日は雨が降るっしょ。 | Slang contraction in a polite sentence. |
| moderate | plain, T1 | 猫がソファで寝ている。 | 猫がソファにて就寝している。 | Written/formal にて and 就寝 in a toddler-tier sentence. |
| subtle | polite, spoken | 雨が降ってきたので、帰りましょう。 | 雨が降ってきたため、帰りましょう。 | Written-register ため combined with a spoken invitation ましょう. |

Not an error:
- Plain forms in subordinate clauses of a polite sentence (雨が降ったので、…ました).
- である in T5–T6 expository sentences when the declared register is formal.
- です/ます in children's-register sentences.
- Mixed kana/kanji density.

#### `ja.particle_other`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | 冷蔵庫に卵が一つだけあります。 | 冷蔵庫に卵が一つしかあります。 | P1. だけ → しか. しか has negative polarity and requires a negative predicate (しかありません); with あります the sentence fails on first read. |
| moderate | 兄と姉の二人に手紙を書きました。 | 兄や姉の二人に手紙を書きました。 | P3. と → や, one slot. や marks a non-exhaustive list, which clashes with the exact total 二人; a counted, closed list needs と. |
| subtle | この本を金曜日までに返してください。 | この本を金曜日まで返してください。 | P2. までに → まで after a time noun. A single act (返す) completed before a deadline needs までに; まで marks continuation until the time. This is a calque of English "by / until". |

**Routing scope vs authored scope.** The particles routed to this type are も (including 誰も・何も・どこも),
だけ, しか, ばかり, さえ, こそ, でも (focus), まで, までに, より, ほど, や, とか, か (listing "or"), と (only in
noun listing, AとB), and は/も stacked after a retained が/を. **Authored positives use only P1–P3.** The other
particles, and stacking, are in scope for routing only: a real error on them found in live output is labelled
`ja.particle_other`, but none are authored, because no crisp rule is defined for them (or, for stacking, because
an LLM essentially never writes it). より is routed here rather than to `ja.case_particle`'s closed list (が, を,
に, で, へ, と, から): a jev convention that keeps the two types disjoint (DT v5 would file より under
`particle_case`).

Not an error:
- だけ + affirmative and しか + negative for the same fact (一つだけある / 一つしかない).
- と and や for an open list, with or without など (りんごやみかんを買った / りんごとみかんを買った /
  りんごとみかんなどを買った). A positive requires や/とか with an **exact** count or an explicitly closed set.
- まで with an action or state that continues until the time (五時まで待つ, 金曜日まで休みです). までに with a
  one-time action. What is never authored as a positive: までに with a continuing action.
- Spatial or range まで, including with one-time verbs (駅まで行く, 駅まで歩く, 東京から大阪まで送る, AからBまで).
- まで meaning "even" (子どもまで知っている).
- Clause + まで / までに (彼が来るまで待つ, 帰るまでに終わらせる), when otherwise correct.
- ほど in its affirmative uses: approximate quantity (一時間ほど待った, 三人ほど来た); ～ば～ほど
  (読めば読むほど面白い); clause + ほど of degree (涙が出るほど嬉しい); Xほど…はない (彼ほど親切な人はいない);
  set phrases (死ぬほど, 山ほど).
- より + affirmative and comparative ほど + negative (東京は大阪より大きい / 大阪は東京ほど大きくない).
- Case particle + は/も stacking where it is grammatical: に・で・へ・と・から + は/も (東京には, 学校でも,
  友達とも).
- も replacing は or が (already listed as not-an-error under `ja.wa_ga`).
- 誰もが, 何もかも, いつも, どれも with affirmative predicates. These are fixed forms, not negative-polarity も.
- Whether ね / よ / よね / none is used, and particle omission in casual speech.
- Colloquial listing とか, なんか, でも (お茶でも飲む？) in casual register.
- ～をも in written style, だけしか～ない (redundant but common), and ばかり vs だけ where both read naturally:
  all **(contested — exclude)**.

### 2.3 Question buckets (ja)

| Bucket | Name | Member types | Draft question (yes = clean) |
|---|---|---|---|
| ja.B1 | Particles & counters | case_particle, wa_ga, counter | "Are all the particles (が, を, に, で, へ, と, から, は) and counters used correctly for the words they attach to?" |
| ja.B2 | Verb forms | conjugation, transitivity_voice, tam | "Is every verb and adjective in a correct form: conjugation, the right transitive/intransitive verb, passive/causative, and tense/aspect (ている, てある) that fits the time?" |
| ja.B3 | 語・節・主題のつながり (Joining words, clauses & topic) | modification, clause_linkage, topic_comment | 「語と語、節と節、主題と述語のつながりは正しいですか。（例：名詞を修飾する形「大きい犬」「静かな部屋」「病気の友達」、「ので」「たら」「ように」などの接続、そして「～は」で示した主題と文末の述語がきちんと対応しているか。）」 |
| ja.B4 | Word choice | collocation, kanji_choice | "Is each word the one a native speaker would choose here: the natural verb for its noun, and the correct kanji for the meaning?" |
| ja.B5 | Target sense | wrong_sense, target_in_idiom | "Is 「{target}」 used here with the meaning '{definition}', literally, and not inside an idiom that changes its meaning?" |
| ja.B6 | Target presence | target_absent, target_not_whole_word | "Does 「{target}」 (in any conjugated form or spelling) appear as a word in its own right: not replaced by another word, and not just part of a longer word?" |
| ja.B7 | Meaning & logic | semantic_anomaly, contradiction | "Does the sentence describe something that makes sense and could really happen, without contradicting itself?" |
| ja.B8 | Politeness | keigo, register *(register part optional)* | "Are honorific and humble forms used for the right person, and does the politeness level match '{register}'?" |
| ja.B9 | 取り立て・並列の助詞 (Focus & listing particles) | particle_other | 「も・だけ・しか・まで／までに・より・ほど、並列の「や」「と」などの助詞は正しく使われていますか。（例：「しか」や比較の「ほど」、「誰も」「何も」を使った文の述語が否定形になっているか。期限を表すときに「までに」が使われているか。数が決まっている並べ方には「や」ではなく「と」が使われているか。）」 |

Notes:
- ja.B8 stays a core bucket even if register is excluded, because keigo direction is a grammatical error. If
  register is excluded, drop its clause from the question and author all 30 B8 positives as `ja.keigo`.
- ja.B6: a deterministic check with a lemmatiser (Sudachi or MeCab + UniDic) plus a suppletive-keigo table beats
  a classifier here. Keep it in the eval for measurement.
- ja.B1 carries the main hard-negative load: が/を with potentials, path を, the に/と variants, and main-clause
  は/が alternations. ja.B1 excludes ja.B9 positives from its cross-bucket negative set (a B9 positive like
  しかあります would legitimately answer "no" on B1's particle question) and reports them separately as a
  diagnostic.
- ja.B9 (2026-09-28) is a new, ja-only bucket for `particle_other` (30 positives: about 12 P1, 10 P2, 8 P3). It
  has no zh or en counterpart (§4).
- ja.B3 (2026-09-28) gains `topic_comment` (about 10 positives, split between obvious and moderate only). Its
  hardest neighbour, `clause_linkage`, is already in B3. `ja.wa_ga` and `ja.contradiction`/`ja.semantic_anomaly`
  positives with a は-topic are excluded from ja.B3's cross-bucket set when the question would legitimately
  answer "no" on them, and reported as diagnostics; `ja.topic_comment` positives stay in ja.B1, ja.B2, ja.B4 and
  ja.B8's cross-bucket sets but are excluded from ja.B7's.

### 2.4 Corruption rules — ja additions

- `ja.wa_ga` positives use only the three structural rules. Never swap は/が in a main clause.
- Keep the script mix: do not convert kanji to kana or kana to kanji, except as the edit in `ja.kanji_choice`.
- `ja.keigo` items must name the actor explicitly (先生, 社長, 私, お客様), so the direction is decidable from the
  single sentence.
- Conjugation errors must be real wrong-paradigm forms (a godan verb treated as ichidan, a na-adjective treated
  as an i-adjective), not a random missing kana. This is the §0.7 C5 no-typo rule applied to Japanese.
- Never use ら抜き, さ入れ, 二重敬語 or 違くて forms, as positives or as negatives.
- Keep the declared register fixed for every non-register type. A grammar corruption must not also change
  です/ます vs plain.
- `ja.particle_other` positives are particle swaps, insertions or deletions restricted to P1–P3 only. Never
  corrupt to or from は, が, or a case particle. No final-particle positives and no stacking positives.
- `ja.topic_comment` positives use only J1a (夢/目標/希望/趣味/目的 topics → ～ことです, or ～たいです for
  夢/目標/希望) and J1b (理由/原因 topics → ～からです/～ためです), replacing the sentence-final predicate
  complex as one constituent (C2). は/が are never edited. J1 items are always `obvious` or `moderate`, never
  `subtle` (C9 requires a one-morpheme edit).

### 2.5 Verification rules — ja additions

- Run Sudachi (mode C) or MeCab + UniDic on every `target_*` item. Compare lemmas, not surface strings, so
  conjugated forms count as present. Check suppletive keigo by hand.
- Separate syntactic from lexical compound verbs (see `ja.target_not_whole_word`). If unsure, look the compound up
  in a dictionary: if it has its own entry with its own meaning, it is lexical, so a fragment.
- For particle, collocation and kanji-choice items, and for every subtle item, check the broken string against
  BCCWJ (via 少納言 or 中納言). Attested usage in edited registers means reject.
- For `ja.wa_ga` and `ja.clause_linkage`, apply V5 rigorously: contrastive は and loose ～て readings rescue many
  apparent errors.
- Run the V9 corpus check (BCCWJ) on every `ja.particle_other` まで/までに and や item. For まで items, try an
  iterative or notice-style reading ("returns accepted up to Friday"); if the object is plural or number-neutral,
  or the verb can be read as repeated (出す, 送る), make the object singular and definite, or reject.
- For `ja.topic_comment`, apply the topic-deletion test (§2.2): delete the closed-list は-phrase; the item is
  valid only if what remains is a fully correct sentence on its own. Apply the ja.keigo precedent (V2): the
  argument "people say this in conversation" does not rescue a J1 item, but any other reading in which the
  sentence is correct still means reject.

---

## 3. English (en)

**Reference norm:** Standard written English, US or UK. Both are accepted, and mixing them within a sentence is
not an error. Non-standard dialect grammar ("she don't", "ain't") counts as an error against the norm, but avoid
it as a positive, because a reviewer may read it as register. Prescriptive shibboleths are **not** errors:
split infinitives, stranded prepositions, sentence-initial And/But, singular *they*, *who* as an object,
*hopefully*, *data is*.

### 3.1 Type list

| id | Name | One-line definition | Class | LLM freq. | Why that frequency | Bucket |
|---|---|---|---|---|---|---|
| `en.article_determiner` | Articles & determiners | A missing, extra or wrong article or determiner, or a countability clash (an advice, many information). | G | low | Native-level for en generators. | B1 |
| `en.preposition` | Prepositions | A wrong preposition for a verb, adjective or noun, or for a location or time. | G | low | Native-level; slips on dependent prepositions (married to, depend on). | B1 |
| `en.phrasal_verb` | Phrasal-verb particles | In an idiomatic phrasal verb (verb + particle whose combined meaning is not the verb's own meaning), or in a prepositional verb on a closed list (§3.2), the particle is wrong, missing, or placed wrongly relative to the object. | G | low | Native-level generators produce phrasal verbs fluently. Their phrasal-verb risk is sense (`en.target_in_idiom`), not form. The remaining slips are near-miss particles on the same verb, and pronoun objects placed after the particle. | B1 |
| `en.verb_form_tense` | Verb form & tense | A wrong tense or aspect for the time frame, or a wrong irregular or participle form. | G | low | Rare. | B2 |
| `en.complementation` | Verb patterns | A wrong complement type after a verb: to-infinitive, -ing, bare infinitive or that-clause. | G | low | Rare; "look forward to + base" style slips possible. | B2 |
| `en.agreement` | Agreement | Subject–verb disagreement, including attraction from an intervening noun. | G | low | Long subjects with plural attractors are the residual risk. | B3 |
| `en.word_order` | Word order | Wrong order in questions or embedded questions, adjective order, or adverb placement between verb and object. | G | low | Very rare. | B3 |
| `en.pronoun` | Pronouns | Wrong case, a reflexive without a local antecedent, *which* for a person, or a resumptive pronoun. | G | low | Rare. | B3 |
| `en.collocation` | Collocation | Grammatical but not the conventional word pairing (do a mistake, strong rain). | S | medium | Less than zh/ja, but the main residual en error besides sense. | B4 |
| `en.lexical_form` | Word-family form | The wrong member of the right word family (success/successful, economic/economical). | S | low | Rare for native-level generators. | B4 |
| `en.plural_number` | Noun number | A noun is in the wrong number for a fixed licensor: singular after a closed-list plural licensor (a numeral ≥2, both, several, a few, a couple of, many, or "one of"), or plural on a closed list of uncountable nouns (advice, information, furniture, luggage, homework, housework). The determiner and the verb are correct and unchanged. | G | low | Native-level en generators mark number reliably. The residual risks are "one of the + singular" inside long noun phrases, and translationese plurals of uncountables (informations, advices) when the prompt is built from a zh/ja source. | B4 |
| `en.wrong_sense` | Wrong sense | The target carries a different dictionary sense from the locked one. | S | high | Polysemy (bank, run, open, light) drifts to the most frequent sense. | B5 |
| `en.target_in_idiom` | Target in idiom | The target is inside an idiom or a phrasal verb that shifts its meaning. | T | medium | Phrasal verbs (give up, run into) and idioms are pervasive in fluent English. | B5 |
| `en.target_absent` | Target absent | The target does not occur: a synonym or a derived relative instead. | T | low | Almost always present. | B6 |
| `en.target_not_whole_word` | Target as fragment | The target occurs only inside a longer word or compound. | T | low–medium | Short targets (art, cat, light, book). | B6 |
| `en.semantic_anomaly` | Semantic anomaly | Grammatical, but the event is impossible or absurd. | S | low | Fluent generator. | B7 |
| `en.contradiction` | Contradiction / logic | Grammatical, but self-contradictory, or a connective asserts the wrong relation. | S | low | Occasional. | B7 |
| `en.register` | Register mismatch *(stylistic, may be excluded)* | Formality clashes with the declared register or tier (utilize, commence, reside in a T1 sentence; slang in formal). | R | high | LLM "elevated diction" is the most visible en defect. | B8 |

### 3.2 Type details

#### `en.article_determiner`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | She is a doctor. | She is doctor. | A singular count noun needs a determiner. |
| moderate | I need some advice. | I need an advice. | *Advice* is uncountable. |
| subtle | I had breakfast at seven. | I had a breakfast at seven. | Meal names take no article unless modified ("a big breakfast"). |

Not an error:
- *plays piano* / *plays the piano*.
- *go to hospital* / *university* (UK) vs *the hospital* (US).
- *in bed*, *at school*, *by car*.
- Generic *the tiger* / *tigers* / *a tiger*.
- Headline or label style.
- *a historic* / *an historic*.

#### `en.preposition`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | It depends on the weather. | It depends of the weather. | *Depend* takes *on*. |
| moderate | We arrived at the station at noon. | We arrived to the station at noon. | *Arrive* takes *at* or *in*, not *to*. |
| subtle | She is married to a doctor. | She is married with a doctor. | Spouse takes *to*; *married with* is only for "married with children". |

Not an error:
- *different from* / *than* / *to*.
- *on* / *at the weekend*.
- *bored of* / *with* / *by*.
- *in* / *on the street*.
- *meet* / *meet with*.
- *on accident* **(contested — exclude)**.

#### `en.phrasal_verb`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | We ran out of milk this morning. | We ran of milk this morning. | Particle *out* deleted from *run out of*; *run of* has no valid parse, so the sentence fails on first read. |
| moderate | I didn't know the word, so I looked it up. | I didn't know the word, so I looked up it. | *Look up* (= consult a reference) is idiomatic and separable. A pronoun object must sit between verb and particle; only a full noun phrase may follow the particle. |
| subtle | We have to put up with the noise from next door. | We have to put up to the noise from next door. | Same-verb near-miss particle: *put up with* = tolerate. *Put up to* exists only as *put someone up to something* (= incite), which needs a person object, so the frame has no valid parse here. The surface stays fluent. |

**The deciding criterion is idiomaticity**, not movement: a combination is in scope only if the verb does not
keep its own meaning (*look up* a word = consult; *turn out* = prove to be; *put up with* = tolerate; *run out
of* = exhaust). Whether the particle can follow the object is a secondary diagnostic only — it decides
placement errors on an already in-scope verb, and never brings a verb into scope. Literal verb + directional
particle (*give the pen back*, *carry the box in*, *pick up the cup* = lift) is **out of scope** for both
`en.phrasal_verb` and `en.preposition`; use it only as `variant_ok`.

Closed list of idiomatic, inseparable prepositional verbs that count as `en.phrasal_verb`: *look after, look
into, come across, take after, get over, run into* (= meet by chance), *go over* (= review), *put up with, run
out of, get along with, give in to, come up with, catch up on, look forward to*. Every other verb + preposition
pairing (*deal with, count on, care for, believe in, look at, consist of, depend on, listen to*, …) is
`en.preposition`. Separable or intransitive idiomatic verbs need no list; idiomaticity decides (*give in, run
out, look up* a word, *turn out, turn down* = reject, *put off* = postpone, *find out, call off, set off, break
down, bring up* a topic, *figure out, pick up* = learn or collect a person).

Positives use exactly one of: a particle swap that leaves no valid parse in that frame; a particle deletion that
removes the meaning; or, for an idiomatic separable verb, a pronoun object placed after the particle (or, for an
inseparable listed verb, split around its object) — capped at no more than 3 of about 10 positives.

Not an error:
- A separable idiomatic phrasal verb with a noun object in either position (*look up the word* / *look the word
  up*; *turn down the offer* / *turn the offer down*).
- US/UK particle variants of equal standing (*fill in* / *fill out* a form; *put back* (UK) = postpone; *check
  in* / *check into* a hotel; *meet* / *meet up* / *meet up with*; *wake* / *wake up*).
- An optional completive or intensifying particle where the bare verb is also standard (*eat* / *eat up*,
  *finish* / *finish up*, *clean* / *clean up*, *hurry* / *hurry up*, *find* / *find out* with a that-clause).
- A single-word verb chosen instead of a phrasal verb, or the reverse (*postpone* / *put off*, *tolerate* / *put
  up with*): `en.register` at most, never this type.
- Stacked particles used correctly (*put up with, get on with, catch up on, look forward to*).
- Literal verb + directional particle, in either order (*give back the pen* / *give the pen back*, *carry the
  box in*): out of scope (above); use it only as `variant_ok`.
- A long noun object placed between verb and particle (*turned the offer she had waited years for down*): awkward
  end-weight, not ungrammatical **(contested — exclude)**.
- *give up to* + noun as "yield to" (*gave up to pressure*): *give (oneself) up to* has a valid parse
  **(contested — exclude)**.
- *off of* (*get off of the bus*) **(contested — exclude)**.
- Regional particle uses outside US/UK standard (*cope up with, fill up a form, pick someone from the station*):
  dialect forms, never a positive and never `variant_ok`.

#### `en.verb_form_tense`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | She has gone to school. | She has went to school. | Past form used as a participle. |
| moderate | I saw him yesterday. | I have seen him yesterday. | Present perfect with a definite past time adverbial. |
| subtle | I have lived here since 2019. | I live here since 2019. | *Since* + a starting point requires the perfect. |

Not an error:
- *Did you eat yet?* (US).
- *learnt* / *learned*, *dreamt* / *dreamed*, *gotten* (US), *dove* / *dived*.
- Historic present.
- *If I was you* (informal).
- *will* / *going to*.
- Stative progressive in casual register (*I'm loving it*).
- *If I would have known* **(contested — exclude)**.

#### `en.complementation`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | I enjoy swimming. | I enjoy to swim. | *Enjoy* takes -ing. |
| moderate | She made him wait. | She made him to wait. | Causative *make* takes a bare infinitive in the active. |
| subtle | I look forward to seeing you. | I look forward to see you. | *To* here is a preposition, so it takes -ing. |

Not an error:
- *start* / *begin* / *like* / *love* + to-infinitive or -ing.
- *help (to) carry*.
- *try to* vs *try -ing* (a meaning difference, both grammatical).
- *suggest that he go* / *goes* / *should go*.
- *want for him to* **(contested — exclude)**.

#### `en.agreement`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | The children play in the park every day. | The children plays in the park every day. | Plural subject with a singular verb. |
| moderate | The news is good today. | The news are good today. | *News* is singular. |
| subtle | One of my friends lives in Paris. | One of my friends live in Paris. | Attraction to *friends*; the head is *one*. |

Not an error:
- Singular *they* (*Someone left their umbrella*).
- Collective nouns with plural verbs (*The team are winning*, UK).
- *There's* + plural in speech.
- *None of them are*, *A number of people are*, *data is* / *are*.
- *Each … have* **(contested — exclude)**.

#### `en.word_order`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | Where does she live? | Where she does live? | Auxiliary not inverted in a direct question. |
| moderate | I don't know where he is. | I don't know where is he. | Inversion inside an embedded question. |
| subtle | He bought a small red car. | He bought a red small car. | Size precedes colour in adjective order. |

Not an error:
- Split infinitives.
- Stranded prepositions.
- Flexible *only*.
- Fronting for emphasis (*This book I really like*).
- *often goes* / *goes often*.
- Adjective order reversed for contrastive stress in speech. Do not use as a positive unless the adjectives are
  plainly size and colour, or opinion and size.

#### `en.pronoun`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | She gave me the book. | She gave I the book. | Subject case in object position. |
| moderate | The woman who lives next door is a nurse. | The woman which lives next door is a nurse. | *Which* for a person. |
| subtle | Tom asked Anna to introduce herself. | Tom asked Anna to introduce himself. | A reflexive must be bound by the local subject (Anna). |

Not an error:
- Singular *they*.
- *It's me*.
- *that* for people.
- *who* as an object.
- *The company announced their plans* (UK).
- *me and my friend* in casual register (register at most).
- *between you and I*, *my wife and myself* **(contested — exclude)**.

#### `en.collocation`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | I made a mistake. | I did a mistake. | *Mistake* collocates with *make*. |
| moderate | There was heavy rain last night. | There was strong rain last night. | Rain intensity is *heavy*. |
| subtle | My uncle is a heavy smoker. | My uncle is a strong smoker. | The conventional intensifier for *smoker* is *heavy*. |

Not an error:
- *take* / *have a shower*.
- *make* / *take a decision*.
- *big* / *huge mistake*.
- *strong* / *black coffee*.
- *do* / *make a wish* **(contested — exclude)**.

#### `en.lexical_form`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | She is very successful. | She is very success. | A noun used for an adjective. |
| moderate | He spoke confidently. | He spoke confident. | An adjective used for an adverb (*confident* is not a flat adverb). |
| subtle | We want a more economical car. | We want a more economic car. | *Economic* = relating to the economy; *economical* = cheap to run. |

Not an error:
- Flat adverbs (*drive slow*, *come quick*, *think different*).
- *-ize* / *-ise*.
- Noun modifiers (*a beauty contest*).
- *historic* / *historical* where both are established.
- Homophone spellings (*affect/effect*, *its/it's*) are **out of scope** as spelling (C5).

#### `en.plural_number`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | I have two brothers and a sister. | I have two brother and a sister. | *-s* removed after the numeral *two* (N1). The object is not a subject, so no verb repair exists. |
| moderate | My teacher gave me some useful advice. | My teacher gave me some useful advices. | N3. *Advice* is on the uncountable list. *Some* is number-neutral, so the determiner is correct and the only repair is on the noun. |
| subtle | She is one of the best players on the team. | She is one of the best player on the team. | N2. *One of* requires a plural noun. The verb *is* agrees with *she*, so agreement is untouched. The long noun phrase lets the surface pass a skim. |

**Edit kinds (each a single-slot edit on the head noun only).** N1: missing plural after a closed-list plural
licensor (a cardinal numeral of two or more, *both, several, a few, a couple of, many*); with an irregular noun,
swap in its real singular form (*three children* → *three child*). N2: singular after *one of* + determiner +
(adjective) + noun. N3: a plural ending on a closed list of nouns uncountable in their ordinary sense (*advice,
information, furniture, luggage, homework, housework*), keeping a number-neutral determiner; the source must use
the noun in its ordinary sense, never a commercial or figurative one.

**Hard constraints.** The edited noun must never be the subject of a verb that shows number (a present-tense
verb, *was/were, has/have, does/do*) — that repair would be `en.agreement` (C7); existential *there* + *be* + an
N1 noun phrase is excluded for the same reason. The edited noun must never be the target. Never edit a numeral
word itself (*two hundreds*), produce an over-regularised non-word (*childs, mans, foots, sheeps, mouses* — C5),
or edit a noun used as a modifier (*a shoe shop* → *a shoes shop*).

Not an error:
- Uncountable nouns in the singular, and count use through a unit noun (*some advice*, *two pieces of advice*).
- Nouns that are countable and uncountable in different standard senses, used in their count sense (*two
  coffees*, *the papers*, *many experiences*, *his early works*, *tropical fruits*, *a few grey hairs*, *three
  times*). Only the N3 closed list may carry an N3 positive.
- Zero-plural nouns (*sheep, deer, fish, aircraft, series, species*) and plural-only nouns (*trousers, scissors,
  glasses, clothes*).
- Measure nouns used as modifiers, which are singular (*a five-year-old boy*, *a ten-minute walk*), and standard
  plural modifier nouns (*sports car, clothes shop, savings account, arms race*).
- *More than one* + singular, and *many a* + singular.
- *people* / *persons*. *data* / *media* with singular or plural agreement (`taxonomy.md` §3 norm).
- Generic singular vs plural (*The tiger is endangered* / *Tigers are endangered*).
- Collective nouns in the singular form; their verb agreement belongs to `en.agreement`.

Contested — exclude (C11):
- Distributive singular (*They raised their hand*); *these kind of things*.
- *a criteria*, *a phenomena*; *a scissor* / *a trouser* (attested as modifiers and in fashion usage).
- *fishes, feedbacks, researches, evidences, knowledges, equipments, baggages* (each attested in some edited
  register, or in a figurative sense).
- Zero or decimal quantities (*0 item(s)*, *1.5 hour(s)*); *a ten minutes' walk* (UK genitive of measure).
- Predicative measure phrases (*He is five year old*).

#### `en.wrong_sense`
| Level | Target — locked sense | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | bank — financial institution | I opened an account at the bank. | We had a picnic on the bank of the river. | Now "riverside". |
| moderate | run — manage, operate | She runs a small bakery. | She runs every morning before work. | Now "move fast on foot". |
| subtle | open — move so as to be not closed | Please open the window. | The new café opens at eight. | Now "start business": a closely related but separately listed sense. |

Not an error:
- Nuances within one dictionary sense. Check the sense inventory, as for `zh.wrong_sense`.

#### `en.target_in_idiom`
| Level | Target — locked sense | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | bucket — open container | She filled the bucket with water. | The old man finally kicked the bucket. | *Kick the bucket* = "die". |
| moderate | ice — frozen water | There is ice on the road this morning. | A joke helped break the ice at the meeting. | *Break the ice* = "ease tension". |
| subtle | give — hand over | She gave me a pen. | He gave up smoking last year. | The phrasal verb *give up* = "stop"; it has no idiomatic feel. |

Not an error:
- Literal phrasal combinations (*give back the pen*, *pick up the cup*) where the verb keeps its sense.
- Idioms whose meaning is the locked sense.

#### `en.target_absent`
| Level | Target | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | happy | She was happy with her gift. | She was busy with her gift. | Target and meaning gone. |
| moderate | happy | I'm happy to see you. | I'm glad to see you. | Synonym substituted. |
| subtle | happy | They look happy together. | They live happily together. | Derived adverb in place of the adjective: the target lexeme is absent. |

Not an error:
- Inflections, including suppletive inflection (*went* for *go*, *better* for *good*, *children* for *child*).
  These are one lexeme's paradigm, unlike the Japanese suppletive keigo verbs, which are separate lexemes.
- Contractions (*I'm* for *am*).

#### `en.target_not_whole_word`
| Level | Target | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | art — creative work | The art class starts at nine. | The party starts at nine. | *art* occurs only inside *party*. |
| moderate | book — printed work | Put the book on the shelf. | Put the notebook on the shelf. | Only inside the compound *notebook*. |
| subtle | light — not heavy | This bag is light. | This bag is lightweight. | Inside a compound that keeps a related meaning. |

Not an error:
- Inflectional suffixes (-s, -ed, -ing, comparative -er).
- Possessive *'s*.
- Hyphenated modifiers the reviewer judges transparent **(contested — exclude)**.

#### `en.semantic_anomaly`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | She put the milk in the fridge. | She put the fridge in the milk. | Roles swapped: impossible containment. |
| moderate | He listened to the radio. | He listened to the photograph. | A photograph cannot be listened to. |
| subtle | The ice cream melted in the sun. | The ice cream melted in the freezer. | A freezer prevents melting. |

Not an error:
- Personification (*The wind whispered*).
- Children's-story premises (*The rabbit baked a cake*).
- Hyperbole.
- Idioms.

#### `en.contradiction`
| Level | Correct | Broken | What changed |
|---|---|---|---|
| obvious | He has never been to Paris, but he wants to go next year. | He has never been to Paris, but he lived there last year. | Contradicts "never". |
| moderate | Because the shop was open, we bought some bread there. | Because the shop was closed, we bought some bread there. | The cause contradicts the result. |
| subtle | My older brother was born two years before me. | My older brother was born two years after me. | The kinship term contradicts the birth order. |

Not an error:
- Surprising concessions (*It was raining, but we went anyway*).
- Irony or jokes marked as such.
- Counterfactuals.

#### `en.register` *(stylistic, may be excluded)*
| Level | Declared | Correct | Broken | What changed |
|---|---|---|---|---|
| obvious | neutral, T1 | The dog is sleeping on the sofa. | The canine is reposing upon the sofa. | Elevated diction in a toddler-tier sentence. |
| moderate | formal | We regret to inform you that the meeting has been cancelled. | We regret to inform you that the meeting's been axed. | Slang in a formal notice. |
| subtle | formal | The children are playing outside. | The kids are playing outside. | Casual *kids* in a formal register. |

Not an error:
- Contractions in neutral register.
- *kids* in neutral or casual register.
- Latinate vocabulary in T5–T6 formal sentences.

### 3.3 Question buckets (en)

| Bucket | Name | Member types | Draft question (yes = clean) |
|---|---|---|---|
| en.B1 | Articles, prepositions & particles | article_determiner, preposition, phrasal_verb | "Are all articles (a, an, the), other determiners, prepositions and verb particles (as in *look it up*, *run out of*) correct and in the right place?" |
| en.B2 | Verb forms & patterns | verb_form_tense, complementation | "Is every verb in the correct form and tense for its time frame, and followed by the right pattern (to-infinitive, -ing, bare infinitive or that-clause)?" |
| en.B3 | Structure & agreement | agreement, word_order, pronoun | "Is the sentence put together correctly: subjects agreeing with their verbs, words in the right order, and pronouns in the right form and referring to the right person?" |
| en.B4 | Word choice & word form | collocation, lexical_form, plural_number | "Is each word the one a native speaker would choose, and in the right form: natural word combinations (*make a mistake*, *heavy rain*), the right member of a word family (*successful*, *confidently*), and each noun in the right singular or plural form (*two brothers*, *some advice*)?" |
| en.B5 | Target sense | wrong_sense, target_in_idiom | "Is '{target}' used here with the meaning '{definition}', literally, and not as part of an idiom or phrasal verb that changes its meaning?" |
| en.B6 | Target presence | target_absent, target_not_whole_word | "Does '{target}' (in any inflected form) appear in the sentence as a word in its own right: not replaced by another word, and not just part of a longer word?" |
| en.B7 | Meaning & logic | semantic_anomaly, contradiction | "Does the sentence describe something that makes sense and could really happen, without contradicting itself?" |
| en.B8 | Register *(optional)* | register | "Does the sentence's level of formality match '{register}' and suit a learner at tier {tier}?" |

Notes:
- en.B3 is the broadest question. If per-type recall in B3 comes out uneven, split it into B3a (agreement +
  pronoun: "do the forms agree?") and B3b (word order).
- Because en grammar errors are rare in real generator output, en.B1–B3 matter mostly as a regression guard.
  en.B5, en.B4 and en.B8 carry the real-world defect mass.
- en.B1 (2026-09-28) gains `phrasal_verb`; article_determiner and preposition drop from about 15 to about 10
  positives each. Placement positives (pronoun after the particle) are capped at ≤3 of about 10 phrasal_verb
  positives and are excluded from en.B3's cross-bucket negative set, reported separately as a diagnostic.
- en.B4 (2026-09-28) gains `plural_number`; the two existing members drop to about 10 positives each.
  plural_number's N1/N2 positives stay in en.B1 and en.B3's cross-bucket sets (the determiner and verb are
  correct by construction); its N3 positives are excluded from en.B1's set and reported as a diagnostic.
  en.article_determiner countability positives (*an advice*, *many information*) are excluded from en.B4's
  cross-bucket set for the same reason.

### 3.4 Corruption rules — en additions

- Never use a prescriptive shibboleth (§3 norm) as a positive. Never use a dialect form as a positive.
- Homophone spellings (*affect/effect*, *their/there*, *its/it's*) are typos under C5. Do not use them.
- Keep US vs UK spelling as in the source.
- `en.target_in_idiom`: phrasal verbs count only when the particle changes the verb's meaning (*give up*,
  *run into*, *look after*). Literal particles (*give back*, *pick up the cup*) do not.
- Short-sentence length rule: ±2 words.
- `en.phrasal_verb` positives use only particle swap, deletion or placement on in-scope verbs (§3.2); no verb
  substitution, no literal verb + particle, and no particle swap that yields a valid phrasal verb with a
  plausible meaning. Source sentences must contain an in-scope, non-target phrasal verb. No more than 3 of about
  10 positives may be placement items.
- `en.plural_number` positives use only N1–N3 with the hard constraints in §3.2: never edit a numeral word
  itself, never produce an over-regularised non-word, and never edit a noun used as a modifier.

### 3.5 Verification rules — en additions

- Lemmatise `target_*` items (spaCy, `en_core_web_sm` or larger) and compare lemmas. Suppletive inflections are
  present. Derived forms (*happily* for *happy*) are absent.
- For collocation, preposition and subtle items, check COCA or BNC frequency. The broken string should be rare
  or absent in edited registers relative to the correct one (V9).
- Apply the "would a copy editor for a learner textbook change this?" test. Reject anything a copy editor would
  leave alone.
- Run the V9 corpus check on every `en.phrasal_verb` item (search verb + particle + the next word, not the pair
  alone — particle swaps are where a "broken" form most often turns out attested under a different parse) and on
  every `en.plural_number` N3 item and every subtle plural_number item.

---

## 4. Cross-language bucket map

| Bucket id | Theme | zh | ja | en |
|---|---|---|---|---|
| B1 | Function words (closed-class grammar) | Measure words & particles — measure_word, aspect_negation, de_particle | Particles & counters — case_particle, wa_ga, counter | Articles, prepositions & particles — article_determiner, preposition, **phrasal_verb** |
| B2 | Verb forms & constructions | Verb constructions — complement, ba_bei, separable_verb | Verb forms — conjugation, transitivity_voice, tam | Verb forms & patterns — verb_form_tense, complementation |
| B3 | Structure & linking | Word order & linking words — word_order, coverb, connective | Joining words, clauses & topic — modification, clause_linkage, **topic_comment** | Structure & agreement — agreement, word_order, pronoun |
| B4 | Word choice | Collocation & subject slot — collocation, **topic_comment** | Word choice — collocation, kanji_choice | Word choice & word form — collocation, lexical_form, **plural_number** |
| B5 | Target sense *(sense-conditional)* | wrong_sense, target_in_idiom | wrong_sense, target_in_idiom | wrong_sense, target_in_idiom |
| B6 | Target presence *(prefer deterministic check)* | target_absent, target_not_whole_word | target_absent, target_not_whole_word | target_absent, target_not_whole_word |
| B7 | Meaning & logic | semantic_anomaly, contradiction | semantic_anomaly, contradiction | semantic_anomaly, contradiction |
| B8 | Politeness / register | register *(optional)* | keigo + register *(register part optional)* | register *(optional)* |
| B9 | Focus & listing particles | — | Focus & listing particles — **particle_other** | — |

Comparability notes:
- B5, B6 and B7 are structurally identical across languages, so per-language differences there reflect the
  classifier's language handling rather than differences in question scope.
- B1 is the best cross-language comparison for the §3.1 finding (particles and measure words weakest
  everywhere), but its member types are not equivalent: zh aspect sits in B1, while ja tense/aspect sits in B2.
  Since 2026-09-28, en B1 also covers verb particles (`en.phrasal_verb`), which has no zh or ja counterpart.
- B8 is not comparable across languages: in ja it contains a grammatical type (keigo) and is core. In zh and en
  it is purely stylistic and optional.
- B9 (2026-09-28) exists only for ja (`particle_other`) and has no cross-language comparison.
- zh and ja `topic_comment` (2026-09-28) sit in **different** buckets (zh B4, ja B3) and are not cross-language
  comparable, the same way zh aspect (B1) sits opposite ja tam (B2): zh's authored pattern adds an extra subject
  filler (expletive 它), ja's mis-joins the sentence-final predicate to its topic.

---

## 5. Sources

Background and internal sources:
- `wiki/evaluations/jev-judge-feasibility-2026-09-26.md` §3.1 — prior controlled-set results and failure cases.
- `data/eval/jev_2026-09-26/exp_a/controlled_set.py` — the 45 prior items. Some are reused as minimal pairs above
  (公司今年赚了很多钱); others are re-labelled in §0.6.
- `migrations/seed_ladder_judge_prompts.sql` (en/zh) and `migrations/ja_prompt_seeds.sql` §4 (ja) —
  `ladder_p1_sentence_judge`, the source of the target-word defect types and the ja register values.

Grammar references and learner-error corpora. These are cited from the author's knowledge of the works. Page
numbers were not checked and no web access was used in writing this document.

Chinese
- Li, Charles N. & Sandra A. Thompson (1981). *Mandarin Chinese: A Functional Reference Grammar*. University of
  California Press. Used for aspect (了/过/着), 把 constraints (definiteness, potential complements), resultative
  and potential complements, and coverbs.
- Ross, Claudia & Jing-heng Sheng Ma (2006). *Modern Mandarin Chinese Grammar: A Practical Guide*. Routledge.
  Used for classifiers, separable verbs, and 不 vs 没.
- 吕叔湘 主编 (1980; 增订本 1999).《现代汉语八百词》. 商务印书馆. Used for function-word usage and collocations
  (对…来说, 离/从).
- 刘月华、潘文娱、故韡 (2001).《实用现代汉语语法（增订本）》. 商务印书馆. Used for complements, paired connectives
  and the placement of 不但.
- 中国社会科学院语言研究所 (2016).《现代汉语词典》第7版. 商务印书馆. Used for the sense inventory and the
  的/地/得 norm.
- HSK动态作文语料库 (Beijing Language and Culture University). A learner-error corpus whose tagged categories
  include 量词, 了, 把字句 and 离合词 errors.
- CGED shared tasks, NLPTEA 2014–2020 (e.g. Yu, Lee & Chang 2014; Rao, Gong, Zhang & Xun 2018): Chinese
  grammatical error diagnosis with Redundant / Missing / Selection / Word-order error classes.
- AllSet Learning, *Chinese Grammar Wiki* (resources.allsetlearning.com), "common mistakes" pages.
- BCC (BLCU) and CCL (Peking University) corpora, recommended for verification (V9).

Japanese
- Makino, Seiichi & Michio Tsutsui (1986; 1995). *A Dictionary of Basic Japanese Grammar* / *…Intermediate
  Japanese Grammar*. The Japan Times. Used for particles, conditionals (と/たら/ば/なら) and ために/ように.
- 庵功雄・高梨信乃・中西久実子・山田敏弘 (2000).『初級を教える人のための日本語文法ハンドブック』スリーエーネットワーク.
  Used for 自他 pairs, ている/てある, and relative tense in 前に/後で.
- 野田尚史 (1996).『「は」と「が」』くろしお出版. The basis for restricting `ja.wa_ga` to structural rules.
- 影山太郎 (1993).『文法と語形成』ひつじ書房. The syntactic vs lexical compound-verb distinction used in
  `ja.target_not_whole_word`.
- 市川保子 (1997).『日本語誤用例文小辞典』凡人社. A learner-error dictionary covering particles, 自他 and tense.
- 文化審議会 (2007).『敬語の指針』. Used for the keigo categories and accepted vs non-accepted double honorifics.
- 国立国語研究所, I-JAS (多言語母語の日本語学習者横断コーパス), a learner corpus; and BCCWJ
  (現代日本語書き言葉均衡コーパス), recommended for verification.
- Mizumoto, Komachi, Nagata & Matsumoto (2011). "Mining Revision Log of Language Learning SNS for Automated
  Japanese Error Correction of Second Language Learners." IJCNLP. Lang-8 learner-error data.
- 文化庁「国語に関する世論調査」(various years). Used for the tolerance of ら抜き言葉.

English
- Huddleston, Rodney & Geoffrey K. Pullum (2002). *The Cambridge Grammar of the English Language*. Cambridge
  University Press. Used for agreement (attraction), singular *they*, binding of reflexives, and prescriptive
  myths.
- Swan, Michael (2016). *Practical English Usage*, 4th ed. Oxford University Press. Used for complementation,
  articles, dependent prepositions and US/UK variation.
- Nicholls, Diane (2003). "The Cambridge Learner Corpus: Error coding and analysis for lexicography and ELT."
  *Proceedings of Corpus Linguistics 2003*. Error categories: derivation, collocation, agreement, and others.
- Yannakoudakis, Helen, Ted Briscoe & Ben Medlock (2011). "A New Dataset and Method for Automatically Grading
  ESOL Texts." ACL. The FCE learner corpus.
- Bryant, Christopher, Mariano Felice & Ted Briscoe (2017). "Automatic Annotation and Evaluation of Error Types
  for Grammatical Error Correction." ACL. The ERRANT error-type scheme.
- Warstadt, Alex, Amanpreet Singh & Samuel R. Bowman (2019). "Neural Network Acceptability Judgments." TACL.
  CoLA; a reminder that acceptability, not prescription, is the target.
- COCA (Davies) and BNC, recommended for verification.
