# Recheck pack 02 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/back/02.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_02.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/verdicts/02.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/packs/recheck_02.gold.md`. Do not open it yet.


## 7e5ce101-5-zh  (Chinese reference -> back-translate into English)

- context before: 流经弯曲上表面的空气，必须在与机翼下方气流相同的时间内走过更长的距离。
- **TARGET:** 因此，上方的空气必须加速，导致其压强下降，这一现象由伯努利原理所描述。
- context after: 相反，机翼下方的空气走过的距离较短，速度较慢，从而产生较高的压强。

## 7e5ce101-18-zh  (Chinese reference -> back-translate into English)

- context before: 飞机要起飞，推力必须足以克服阻力，并把飞机加速到机翼产生的升力足以超过其重量的速度。
- **TARGET:** 巡航期间，这些力被精心地平衡，从而得以持续平飞。
- context after: 飞机的成功飞行是应用物理学与巧妙工程学的一曲交响乐。

## 7e5ce101-22-zh  (Chinese reference -> back-translate into English)

- context before: 虽然机翼上空气压差的基本原理至关重要，但其复杂性延伸到对副翼、升降舵和方向舵等操纵面的精细塑形，这些操纵面让飞行员能够操控气流，从而控制飞机的俯仰、横滚和偏航。
- **TARGET:** 这些操纵面偏转时，会改变气流模式，产生局部压强变化，从而引发所需的运动。
- context after: 例如，把一侧机翼上的副翼向上偏转，而把另一侧的向下偏转，会使两侧机翼之间产生升力差，从而使飞机横滚。

## 7f9c347a-4-zh  (Chinese reference -> back-translate into English)

- context before: 我们可以乘公共汽车。
- **TARGET:** 公共汽车很大。
- context after: 许多人乘坐公共汽车。

## 7f9c347a-9-zh  (Chinese reference -> back-translate into English)

- context before: 人们可以步行去各个地方。
- **TARGET:** 他们也可以骑自行车。
- context after: 这对地球有帮助。

## 8bd36dd0-16-zh  (Chinese reference -> back-translate into English)

- context before: 食物和叶子分解了。
- **TARGET:** 它们变成深色的泥土。
- context after: 这种泥土对花园有好处。

## 97f5efe0-6-zh  (Chinese reference -> back-translate into English)

- context before: 其他人不太担心时间。
- **TARGET:** 他们可以等一等再做事。
- context after: 他们可以迟到。

## ae1d02c2-12-zh  (Chinese reference -> back-translate into English)

- context before: 绿料太多会导致潮湿、发臭的一团糟，而褐料太多则会显著减慢分解过程。
- **TARGET:** 添加厨房残渣时，避免放入肉类、乳制品或油腻的食物，因为它们会吸引害虫并产生难闻的气味。
- context after: 草屑应该分成薄层添加，以防止它们结成团并变成厌氧状态。

## c008fc7a-0-zh  (Chinese reference -> back-translate into English)

- **TARGET:** 豆子长在植物上。
- context after: 这是一颗咖啡豆。

## c008fc7a-4-zh  (Chinese reference -> back-translate into English)

- context before: 他们把它们装进袋子里。
- **TARGET:** 这些袋子被放到大船上。
- context after: 船驶向远方。

## c873cef5-9-zh  (Chinese reference -> back-translate into English)

- context before: 这就是乐谱记法的开始。
- **TARGET:** 在历史的进程中,这个体系不断发展。
- context after: 它帮助作曲家写出更多的音乐。

## ddb8c17f-16-zh  (Chinese reference -> back-translate into English)

- context before: 他们可能不信任这个程序。
- **TARGET:** 公开是好的。
- context after: 它让程序感觉良好。

## ddb8c17f-17-zh  (Chinese reference -> back-translate into English)

- context before: 公开是好的。
- **TARGET:** 它让程序感觉良好。
- context after: 有了这个程序，每个人都可以感觉良好。

## fb2ceec5-1-zh  (Chinese reference -> back-translate into English)

- context before: 里奥每周都和朋友们踢足球。
- **TARGET:** 有时候,孩子们跑得很快时会摔倒,受一些小伤。
- context after: 为了帮忙,里奥有一个叫急救包的特别的红色盒子。

## 0d6a9b1b-4-en  (English reference -> back-translate into Japanese)

- context before: My younger brother attached the parts one by one while looking at the steps, and took two days to complete the robot.
- **TARGET:** Seeing the robot start moving, my younger brother said with shining eyes, "Next I want to make a robot that I design myself."

## 1ae5f89b-0-en  (English reference -> back-translate into Japanese)

- **TARGET:** Venture capital plays an important role in taking risks to raise funds for promising startups and supporting their growth.
- context after: Not stopping at mere investment, by providing management strategy and networks, it accelerates innovation that creates new value in the market.

## 20b503dc-1-en  (English reference -> back-translate into Japanese)

- context before: At my grandmother's house, she raises ten chickens.
- **TARGET:** Every morning, I help feed the chickens.
- context after: On cold days, my grandmother pays attention to the temperature of the coop.

## 293be6cb-4-en  (English reference -> back-translate into Japanese)

- context before: Next, the arrangement of feature points such as bifurcations and ridge endings is analysed precisely.
- **TARGET:** For the purpose of objective corroboration of the crime, it is only through this meticulous matching work that infallible identification is achieved.
- context after: A quiet and logical process for uncovering the truth: that, one could say, is the very essence of fingerprint analysis.

## 29dc5058-1-en  (English reference -> back-translate into Japanese)

- context before: High school students play sports at school.
- **TARGET:** Injuries occur.
- context after: They put a first aid kit in their bag.

## 29dc5058-2-en  (English reference -> back-translate into Japanese)

- context before: Injuries occur.
- **TARGET:** They put a first aid kit in their bag.
- context after: They also put in adhesive bandages.

## 29dc5058-3-en  (English reference -> back-translate into Japanese)

- context before: They put a first aid kit in their bag.
- **TARGET:** They also put in adhesive bandages.

## 3bc2a517-0-en  (English reference -> back-translate into Japanese)

- **TARGET:** The people of Rome build a tall bridge in a big city.
- context after: It is for carrying water.

## 3bc2a517-1-en  (English reference -> back-translate into Japanese)

- context before: The people of Rome build a tall bridge in a big city.
- **TARGET:** It is for carrying water.
- context after: They build it by stacking stones.

## 3bc2a517-2-en  (English reference -> back-translate into Japanese)

- context before: It is for carrying water.
- **TARGET:** They build it by stacking stones.

## 41123003-2-en  (English reference -> back-translate into Japanese)

- context before: Rather, in the complex adaptive systems woven by their interactions, nonlinear dynamics via positive and negative feedback bring about unpredictable macro-level order, that is, emergence.
- **TARGET:** This is precisely because, in the process of countless agents continually adapting on the basis of limited information, unintended innovations and systemic risks suddenly manifest.
- context after: It can be said that the true driving force of socioeconomic phenomena resides precisely beyond reductionist analysis, within the emergent properties of the network as a whole.
