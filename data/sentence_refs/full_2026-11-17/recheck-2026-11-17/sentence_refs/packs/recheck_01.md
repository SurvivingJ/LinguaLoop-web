# Recheck pack 01 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/back/01.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_01.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/verdicts/01.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/packs/recheck_01.gold.md`. Do not open it yet.


## 0b39ed43-1-zh  (Chinese reference -> back-translate into English)

- context before: 大树和绿色公园对城市有好处。
- **TARGET:** 它们让城市看起来很漂亮。
- context after: 人们喜欢在绿色空间里散步。

## 0b39ed43-5-zh  (Chinese reference -> back-translate into English)

- context before: 当城市有更多绿色时，人们就想住在那里。
- **TARGET:** 住在那里的人更多，意味着房子价格更高。
- context after: 这对**房地产**有好处。

## 0bc3a55c-1-zh  (Chinese reference -> back-translate into English)

- context before: 麦克风架贴着玛雅颤抖的手掌，冰凉冰凉的。
- **TARGET:** 在后台，其他参赛者不安地踱步，他们的低语模糊成一片紧张不安的嘈杂。
- context after: 几个月来，这场独一无二的活动占据了她每一个清醒的时刻；每一节写下的诗节、每一行擦掉的诗句，以及她在卧室里每一次慌乱的排练，都通向了这场严峻的考验。

## 0bc3a55c-9-zh  (Chinese reference -> back-translate into English)

- context before: 她的第一句话迟疑地冒出来，几乎穿不透会场里弥漫的嗡嗡声。
- **TARGET:** 然而，随着节奏渐入佳境，她的羞怯消散了。
- context after: 她所创作的诗，记述了都市孤独与那些在不起眼的小瞬间里找到的安静韧性的并置。

## 0bc3a55c-11-zh  (Chinese reference -> back-translate into English)

- context before: 她所创作的诗，记述了都市孤独与那些在不起眼的小瞬间里找到的安静韧性的并置。
- **TARGET:** 她的声音渐渐高涨，在强烈的渐强与令人心悸、脆弱的低语之间转换。
- context after: 她运用刻意的停顿，让沉重的寂静为她隐喻的分量加上标点。

## 158a4f82-7-zh  (Chinese reference -> back-translate into English)

- context before: 它还穿过高高的石桥。
- **TARGET:** 水每天都在这些通道里流动。
- context after: 因为地面是倾斜的,水慢慢地向下流。

## 158a4f82-8-zh  (Chinese reference -> back-translate into English)

- context before: 水每天都在这些通道里流动。
- **TARGET:** 因为地面是倾斜的,水慢慢地向下流。
- context after: 没有使用任何水泵。

## 158a4f82-13-zh  (Chinese reference -> back-translate into English)

- context before: 干净的水直接来到了城镇。
- **TARGET:** 人们用它来喝、做饭和洗东西。
- context after: 这个聪明的设计让城市保持生机和健康。

## 16159b92-7-zh  (Chinese reference -> back-translate into English)

- context before: 箭头绕着转。
- **TARGET:** 这个图案代表好的事情。
- context after: 它的意思是不要把东西扔掉。

## 16159b92-10-zh  (Chinese reference -> back-translate into English)

- context before: 它的意思是把东西再次使用。
- **TARGET:** 人们看到了这个图案。
- context after: 他们喜欢它。

## 1f69565a-1-zh  (Chinese reference -> back-translate into English)

- context before: 可再生能源的历史是人类智慧的一段迷人旅程。
- **TARGET:** 几个世纪以来，人们一直在寻找利用自然力量满足自身需求的方法。
- context after: 这种对可持续发电的追求，一直是推动大量创新的动力。

## 1f69565a-19-zh  (Chinese reference -> back-translate into English)

- context before: 它们也变得更便宜了，使更多人能够用上清洁能源。
- **TARGET:** 这段历史表明，人们一直在持续努力改进我们获取发电的方式。
- context after: 风力涡轮机是风车的现代后代，是这个清洁能源故事的另一个关键部分。

## 1f69565a-23-zh  (Chinese reference -> back-translate into English)

- context before: 这些发电机随后产生电能。
- **TARGET:** 与旧式风车不同，现代涡轮机专门为发电而设计。
- context after: 它们的技术也取得了重大进步，使它们能够在各种风况下高效运行。

## 1f69565a-26-zh  (Chinese reference -> back-translate into English)

- context before: 从简单的风车到精密的太阳能电池板和风力涡轮机的演变，凸显了人类对更好技术的不懈追求。
- **TARGET:** 清洁能源领域这种持续的创新，对我们星球的未来至关重要。
- context after: 了解这段发电的历史，有助于我们体会已取得的进步，并设想可持续能源解决方案的下一步。

## 26c33b80-6-zh  (Chinese reference -> back-translate into English)

- context before: 把水弄到你的手上。
- **TARGET:** 拿起肥皂。
- context after: 把肥皂搓在你的手上。

## 26c33b80-9-zh  (Chinese reference -> back-translate into English)

- context before: 制造大量的泡泡。
- **TARGET:** 肥皂能杀死有害的细菌。
- context after: 现在，用水把肥皂冲掉。

## 26c33b80-11-zh  (Chinese reference -> back-translate into English)

- context before: 现在，用水把肥皂冲掉。
- **TARGET:** 用毛巾把手擦干。
- context after: 你的手现在干净了！

## 29c97a40-6-zh  (Chinese reference -> back-translate into English)

- context before: 然后,打印机以一种特别的方式工作。
- **TARGET:** 传统制造是把大块材料切小。
- context after: 但是3D打印是从底部向上构建东西。

## 29c97a40-10-zh  (Chinese reference -> back-translate into English)

- context before: 它把一层加在另一层的上面。
- **TARGET:** 塑料很快冷却下来并变硬。
- context after: 很快,一个新玩具或杯子就做好了!

## 4618c6fc-7-zh  (Chinese reference -> back-translate into English)

- context before: 开发者需要设计出在运行性能之外也优先考虑伦理因素的算法。
- **TARGET:** 没有严格的监督，在关键领域部署自我管理的技术可能会使民众面临不可接受的风险。
- context after: 最终，社会必须在自动化的技术益处与保护公众福祉、维持人类对关键基础设施的控制这一迫切需要之间取得平衡。

## 68b1b057-1-zh  (Chinese reference -> back-translate into English)

- context before: 利奥把他的蓝色自行车推出车库，为下午的出行做好了准备。
- **TARGET:** 出发之前，他把头盔戴稳，意识到无论何时骑车，安全始终是最重要的。
- context after: 他蹬离地面并开始朝社区公园骑去时，下午的阳光在街区的人行道上投下了长长的影子。

## 68b1b057-2-zh  (Chinese reference -> back-translate into English)

- context before: 出发之前，他把头盔戴稳，意识到无论何时骑车，安全始终是最重要的。
- **TARGET:** 他蹬离地面并开始朝社区公园骑去时，下午的阳光在街区的人行道上投下了长长的影子。
- context after: 走熟悉的路线需要专心掌控方向，尤其是在车辆经常经过的繁忙十字路口附近。

## 68b1b057-5-zh  (Chinese reference -> back-translate into English)

- context before: 利奥清楚地打了转弯信号，并在人行横道处停下，以确保道路完全畅通。
- **TARGET:** 他安全过了马路之后，便沿着通向公园入口的缓坡一路加速而下。
- context after: 到达后，他把自行车停在那棵大橡树旁，并把车架牢牢锁好。

## 7b9ece18-3-zh  (Chinese reference -> back-translate into English)

- context before: 他以熟练的精准度工作，揉捏着沉重的面团，直到它达到做出完美脆皮所需的确切弹性。
- **TARGET:** 面包发起来之后，就被推进巨大的石炉，在那里高温把它们烤成金黄色。
- context after: 早在太阳升到最高点之前，木质柜台上就摆满了一排排温热酥脆的面包。

## 7e5ce101-2-zh  (Chinese reference -> back-translate into English)

- context before: 这一现象的核心是升力的概念，升力是一种始终与重力对抗的力，使这些庞然大物得以升空并飞越遥远的距离。
- **TARGET:** 机翼是工程学上的奇迹，它具有特有的翼型形状，上表面弯曲，下表面较平，是产生这种关键升力的主要部件。
- context after: 当空气流过机翼上方和下方时，它所经过的路径不同。
