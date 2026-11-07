# zh wave_a — Definition Quality Audit

Scope: `data/sense_seeding/zh/wave_a/batch_001..133.senses.json` checked against the matching
`batch_NNN.json` and `AGENT_BRIEF.md`. File-only review; no DB or API calls. Audit date 2026-10-30.

## 1. Headline numbers

| Metric | Value |
|---|---|
| Files | 133 (all present; every file's vocab_ids match its batch exactly; lemmas match; no duplicate ids or lemmas) |
| Total entries | 6,625 |
| Defined | 6,180 (93.3%) |
| Skipped | 445 (6.7%) |
| Confidence >= 0.7 (validated) | 5,644 (91.3% of defined) |
| Confidence < 0.7 (stored unvalidated) | 536 (8.7% of defined) |
| Sample verdict (n=150, seed 7) | OK 129 (86.0%) / minor 19 (12.7%) / wrong 2 (1.3%) |

Confidence histogram (defined): 0.30:1, 0.40:7, 0.45:5, 0.50:38, 0.55:71, 0.58:1, 0.60:203, 0.62:6,
0.65:202, 0.68:2, 0.70:446, 0.72:12, 0.75:290, 0.78:27, 0.80:658, 0.82:107, 0.85:1227, 0.88:279,
0.90:1595, 0.92:91, 0.93:191, 0.95:621, 0.96:3, 0.97:62, 0.98:35.

Files where >= 20% of defined rows are below 0.7: 036 (12/48), 097 (15/50), 098 (14/47),
099 (16/49), 101 (15/50), 102 (13/45), 118 (10/48), 119 (10/48).

### POS distribution (defined rows)

| POS | Count | POS | Count |
|---|---|---|---|
| 1 noun | 2,890 | 7 conjunction | 94 |
| 2 verb | 1,875 | 9 measure_word | 71 |
| 3 adjective | 636 | 6 preposition | 43 |
| 4 adverb | 301 | 8 particle | 36 |
| 5 pronoun | 111 | 11 numeral | 7 |
| 0 other | 104 | 10 idiom | 3 |
| (missing) | 9 | | |

All present POS values are integers in 0-11; all confidences are in 0-1.

## 2. Automated checks

| Check | Hits | Notes |
|---|---|---|
| Missing `part_of_speech` | 9 | Allowed by the brief ("omit rather than guess"), see list |
| Example >= 60 chars | 0 | |
| Example does not contain lemma | 6 | 1 acceptable (separable verb 签了字), 5 genuine misses |
| Latin letters / digits in `simple` or `standard` | 0 | |
| Latin letters / digits in `example` | 2 | 等式 ("2加3等于5"), 变量 ("x") — violates "no English" spirit |
| `simple` > 60 chars | 0 | |
| `standard` < 6 chars | 151 | Mostly normal terse dictionary glosses (母亲。/ 各个国家。); a handful are circular, see below |
| `simple` identical to `standard` | 0 | |
| Half-width punctuation (, ; ? ! : ( )) in text | 219 rows | Confined to batches 013-018 (44/37/36/37/32/33 rows) — normalise to full-width |
| Repeated example sentences | 10 sentences | e.g. 小鸟在树上唱歌。 x3; harmless but low variety |

**Missing POS (9):** 25376 之一, 25480 所谓, 25686 现, 25706 为时, 25734 没有什么, 25811 不得,
25833 今, 27360 第二次, 31554 在我看. Most are reasonably assignable (今/现 noun, 不得 verb,
所谓 adjective, 之一 noun/0); consider filling before exercise use.

**Example lacks lemma (6):**
- 25766 运用 — "他把学到的字用在作文里了。" uses 用, not 运用. Rewrite.
- 30019 低能 — example says 智力较低, never 低能. Rewrite (also sensitive/pejorative word, conf 0.6).
- 30435 签字 — "签了字": separable verb, acceptable.
- 31428 大数 — example uses 很大的数, not 大数. Rewrite.
- 31543 前意识 — example never mentions the word. Rewrite (technical term, consider skipping).
- 31633 职业教育 — example uses 职业学校. Rewrite.

**Short `standard` worth fixing (circular or POS-mismatched):** 30152 增设 "增加设置。"
(simple "多放一个新的，来做事" is also vague), 30173 找机会 "寻找机会。", 28580 开吃 "开始吃。",
28550 新增 (simple "多出来的新的" reads as an adjective though POS=2), 27610 大声 (POS 4 but gloss
"声音响亮" is adjectival), 30133 任人 "听凭别人。". The other ~145 short glosses are fine.

## 3. Skipped lemmas by reason keyword

Reasons were free text (271 distinct strings, mixed English/Chinese); grouped here by keyword.

- **fragment / non-word** (243): 要有、张得、乌斯、法比、莫比、了了、有了、么、中的、我人、有年、这不、中人、人中、中中、这就、和会、为上、说中、对上、年上、不月、在后、是日、说上、我等、会要、大我、不很、上个、日中、人从、看在、不着、一说、我去、要着、亚、地和、年过、斯、要看、那是、他用、对地、尔、到现在、得中、到得、在前、好去、或将、小的、日新、了当、日没、这些个、过从、大过、得可以、一更、做大、小我、大用、儿、得着、才不、义、出月、不第、去得、得看、至人、做小、等比、万有、奥、给事、长多、三小、做生活、维、游戏说、自要、太上、点大、内内、出号、新钱、不图、中分、走时、带过、要图、多站、就道、然、里带、正人、资、便人、日至、开地、分时、对本、站地、三无、上达、可吃、好道、正日、分地、起小、分所、呢呢、国小、把总、政治关系、岁出、无已、约出、中女、即由、正时、听事、起号、另用、正用、老中、用间、分当、四大、女大、自高、着处、高起、一作、问事、拿人、次后、老等、该应、以次、后感觉、社会民主、县地、要路、这么点、长开、先有、下网、作下、再发、别有、学人、希、后制、网下、行好、拿大、更次、使成、分则、什、分点、小受、莱、认识不能、么么、点见、其外、分系统、普、对版、开站、高名、不期、他性、即如、大心、应点、间使、并条、地书、委、指到、称钱、诸、点发、其先、女高、市钱、干话、与共、曼、玩话、起种、娜、带种、性地、丹、务、卡拉、制钱、问市、会车、正正、市分、应名、所生、未成、全向、打网、做手、天次、手用、男大、门对、因如此、本经、干手机、国际级、多放、作马、可加、二进、非直接、同位、要子、变分、非处、管他、马占、真版、非独立、小转、我这个人、最后一天、拍点、那提、原道、倒把、入月
- **proper noun** (69): 欧洲、伏尔泰、南美洲、安第斯、达莱佐、东京、雅加达、伯努利、斯德哥尔摩、亚洲、非洲大陆、东非、中国、德意志、拉丁美洲、牛顿、联合国环境规划署、斯托克斯、美国联邦贸易委员会、古罗马、长城、李、陈、罗、人大、苏、巴、华、欧、俄、尼、刘、中区、鲁、赵、天和、里约、京、马克、吗哪、唐、贾、以军、范、卫、朱、金沙、上水、第一国际、苏丹、郭、乔、薇、曹、楚、泰、菲、明朝、杜、迪、麦克、徐、卢、波音、澳、小黄、回回、月城、韦
- **phrase (free combination)** (37): 上一个、月中、第一次、得要、要得、应该的、做自己、再不、可看、做工作、出问题、跟人、有一些、有影响、经济问题、听会、两个中国、成说、分说、家去、不在了、要说、次一个、同上、无两、可作、未可、对心、成话、无成、有水、受死、被旅游、几乎完全、没水平、转关系、具体到
- **numeral** (36): 一、三、万、两、二、亿、四、五、第二、六、三不、一句、七、九、〸、十、八、零、岁时、百万、千、三两、十五、十八、第五、十九、十二、二十、十三、十一、十四、万名、三五、二指、十六、三十
- **variant** (26): 於、麽、卽、乾、榦、剋、经济人、脩、昇、蔘、却才、菸、至当、作人、长至、徵、寀、吃吃、干号、亦或、摺、没有法、向性、痠、大系、夥
- **obscene/vulgar** (19): 操、爱爱、他妈的、不是东西、小电影、强奸、发生关系、色情、做爱、作爱、骚、鸡巴、老子、性爱、我靠、性事、性服务、屁、屎
- **other** (14): 阿、自杀、英、上第、比为、她经济、中企业、来事、书会、写死、另开、行号、性向、性工作
- **symbol** (1): ○
Reasons classified as **other** (verbatim):
  - 阿: prefix / transliteration character, no independent meaning
  - 自杀: sensitive topic unsuitable for a child-register definition
  - 英: 单字，是"英国"等词的简称或别的词的一部分，本身不单独成词
  - 上第: 不成词的片段，多半是"及第""上第几"等词的错误切分
  - 比为: 不成词的片段，多是"比值为""比率为"等词的省写
  - 她经济: 不成词的片段，是"她经济"这类临时搭配
  - 中企业: 不成词的片段，是"中小企业"等词的错误切分
  - 来事: 方言或固定搭配（如"会来事"）的片段，没有独立的单一义项
  - 书会: rare historical term (Song-era storytellers' guild), no everyday sense
  - 写死: ambiguous compound, no clear independent sense
  - 另开: 透明复合词（另+开），无独立义项
  - 行号: 多义且无单一常用义
  - 性向: technical term with no everyday primary sense
  - 性工作: sensitive/adult-related term
**Questionable skips (should probably be defined):**
- 第一次 skipped as a phrase while 27360 第二次 was defined — inconsistent; define both or skip both.
- 有了, 这不, 回回 ("每次"), 下网, 干手机, 分系统, 国际级, 干号, 管他 — real, lexicalised everyday words/expressions.
- 屁, 屎 — everyday words children use; "obscene" is too strong. 老子 also has neutral senses (父亲; 老子 the philosopher).
- 自杀, 强奸, 性工作, 性服务, 发生关系 — skipped as sensitive, which the brief does not list as a skip reason; this is a policy call for the owner, not a writer call.
- 岁时 tagged "numeral" (it means 季节/一年中的时节); 一句 / 万名 tagged numeral but are phrases — skip is fine, reason is wrong.

## 4. Sample review (150 defined entries, `random.seed(7)`; `random.sample(defined, 150)`)

Reviewed by hand for: primary everyday sense in `standard`, child-safe accuracy of `simple`,
POS, and whether `example` uses the word in the defined sense.

| Verdict | Count | % |
|---|---|---|
| OK | 129 | 86.0 |
| Minor issue | 19 | 12.7 |
| Wrong | 2 | 1.3 |

### Wrong (2)
- 25864 加上 (batch 016) — simple "把另一个放到这一个上面" and standard "把一个再放到另一个上面" describe physically placing on top; the primary sense is "add; plus; in addition". Would mislead a child (the example 三加上二是五 contradicts the definition).
- 30097 自然历史 (batch 101) — simple "讲一个东西从头到现在怎么变过来" describes history in general and never mentions nature/living things; misleading.

### Minor (19)
- 25534 狗 — simple calls a dog "一种小动物"; dogs are not necessarily small.
- 28965 拍卖 — example "在拍卖会上被拍卖了" is redundant.
- 25723 有限公司 — simple "是一种公司的名字" is misleading-ish (it is a company type, not a name).
- 27235 愚蠢 — example "把钥匙丢了，这样做太愚蠢了": losing keys is not a 做法; awkward.
- 29897 中级 — POS 1; 中级 is a distinguishing word, better 3.
- 30152 增设 — simple "多放一个新的，来做事" vague; standard circular; example "新增设" redundant.
- 27840 笔者 — example "笔者在书中写了很多故事" reads as third-person "the writer", blurring the self-reference sense.
- 26711 搭 — standard lists four senses (支起；架设；连接；乘坐), breaking the one-sense rule.
- 30243 仪 — two unrelated senses jammed together (仪表 / 仪器); bound morpheme, conf 0.6.
- 30156 多目的 — example "这个房间是多目的的" unnatural.
- 25966 节 — example "春节是个快乐的节" unnatural; 节 as measure word (一节课) is arguably the more frequent sense.
- 31234 全书 — example "这本故事书的全书都读完了" ungrammatical.
- 30173 找机会 — free phrase; standard circular ("寻找机会").
- 25714 在地 — likely segmentation artefact (坐在地上); "本地的" sense is Taiwan usage; conf 0.65.
- 31501 责 — example "老师没有责我" is not natural modern usage (责备/批评).
- 27627 监 — example only uses the compound 监考, not 监 alone.
- 27037 创 — example "创一家小店" unnatural (开/创办).
- 27651 医药 — example "医院里有很多医药" unnatural (医药 is not a count noun; 药).
- 26263 府 — example "住在大府里" unnatural.

Observations: function words, measure words and particles in the sample (块, 篇, 遍, 耶, 几, 有些) are
handled well. Most minor issues are unnatural example sentences rather than wrong definitions;
standard definitions were accurate in 147/150 cases. Extrapolated to 6,180 rows: roughly 80 wrong
(95% CI about 0-200) and roughly 780 with minor issues.

## 5. Recommendation

1. **Ready to use:** the bulk of wave_a. Structure is clean (ids, lemmas, types, lengths all pass) and the
   sampled wrong rate is low (~1%).
2. **Fix before exercises (targeted rows):**
   - The 2 wrong sample rows (25864 加上, 30097 自然历史) and the 5 examples that omit the lemma
     (25766 运用, 30019 低能, 31428 大数, 31543 前意识, 31633 职业教育).
   - The 2 examples with digits/Latin (30195 等式, 30325 变量) if exercises forbid them.
   - Circular / mismatched short glosses: 30152 增设, 30173 找机会, 28580 开吃, 28550 新增, 27610 大声, 30133 任人.
   - Fill the 9 missing POS values.
3. **Normalise punctuation** in batches 013-018 (219 rows with half-width , ; ? ! :).
4. **Re-review low-confidence clusters:** batches 036, 097, 098, 099, 101, 102, 118, 119 (>= 20% below
   0.7). These rows are stored unvalidated anyway; exclude conf < 0.7 rows (536) from exercise
   generation until a second pass, or re-review them in a fresh context.
5. **Example naturalness pass:** because most minor issues are stilted examples, a quick native-speaker pass on
   examples (not definitions) for single-character lemmas (节, 责, 创, 府, 监, 仪 ...) is the best value.
6. **Skips:** revisit the questionable skips in section 3 (第一次 vs 第二次, 有了, 屁/屎, 回回, etc.) and get an
   owner decision on sensitive-but-standard words (自杀, 强奸, 性工作 ...) instead of leaving it to writers.
   Normalise the free-text reasons to a fixed set of codes.
7. **Upload status note:** at audit time `uploaded.txt` listed 33 batches already uploaded (001-013, 019-029,
   109-113, 127-130), and `upload_log.md` shows embed-on-create failing (no OpenAI key). Fixes to rows in
   those batches (e.g. 31428 大数, 31501 责, 25686 现, half-width punctuation in 013) must be applied as
   updates in the database, not only in these files; the uploaded rows also still need embedding.
