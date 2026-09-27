# Adjudicated entailment gold — scoring

Labelled: A=300 B=297; both=297; tiebreak C=19.
Inter-labeller agreement A/B: 93.6%, Cohen kappa 0.887.
Final label = agreement, else majority of A/B/C, else `unclear`. **Adjudicators are models, not humans** (see task note).

## zh  (n=100; cutoffs (0.3, 0.6))

### live

| verdict \ adjudicated | yes | unclear | no |
|---|---|---|---|
| accept | 38 | 5 | 15 |
| flag | 0 | 0 | 23 |
| reject | 0 | 0 | 19 |

### jev

| verdict \ adjudicated | yes | unclear | no |
|---|---|---|---|
| accept | 37 | 1 | 0 |
| flag | 1 | 2 | 2 |
| reject | 0 | 2 | 55 |

- stratum A (n=57): false-accept live 0 / jev 0; false-reject live 0 / jev 0
- stratum D (n=43): false-accept live 15 / jev 0; false-reject live 0 / jev 0
- head-to-head on 43 disagreements: jev matches the adjudication on 36, live on 1 (rest: a flag or an `unclear` label)

## en  (n=100; cutoffs (0.3, 0.6))

### live

| verdict \ adjudicated | yes | unclear | no |
|---|---|---|---|
| accept | 57 | 3 | 2 |
| flag | 0 | 0 | 2 |
| reject | 1 | 2 | 33 |

### jev

| verdict \ adjudicated | yes | unclear | no |
|---|---|---|---|
| accept | 57 | 1 | 1 |
| flag | 1 | 4 | 4 |
| reject | 0 | 0 | 32 |

- stratum A (n=87): false-accept live 0 / jev 0; false-reject live 0 / jev 0
- stratum D (n=13): false-accept live 2 / jev 1; false-reject live 1 / jev 0
- head-to-head on 13 disagreements: jev matches the adjudication on 4, live on 5 (rest: a flag or an `unclear` label)

## ja  (n=100; cutoffs (0.3, 0.6))

### live

| verdict \ adjudicated | yes | unclear | no |
|---|---|---|---|
| accept | 46 | 9 | 7 |
| flag | 2 | 0 | 5 |
| reject | 2 | 2 | 27 |

### jev

| verdict \ adjudicated | yes | unclear | no |
|---|---|---|---|
| accept | 46 | 5 | 0 |
| flag | 4 | 6 | 9 |
| reject | 0 | 0 | 30 |

- stratum A (n=70): false-accept live 0 / jev 0; false-reject live 0 / jev 0
- stratum D (n=30): false-accept live 7 / jev 0; false-reject live 2 / jev 0
- head-to-head on 30 disagreements: jev matches the adjudication on 11, live on 8 (rest: a flag or an `unclear` label)

## Cutoff re-sweep (jev P(yes) vs adjudicated yes/no; `unclear` excluded)

**zh** (n=95, yes=38):

| reject < | accept ≥ | false-reject | false-accept | flagged |
|---|---|---|---|---|
| 0.2 | 0.5 | 0 | 1 | 4 |
| 0.2 | 0.6 | 0 | 0 | 6 |
| 0.2 | 0.7 | 0 | 0 | 6 |
| 0.3 | 0.5 | 0 | 1 | 1 |
| 0.3 | 0.6 | 0 | 0 | 3 |  ← current
| 0.3 | 0.7 | 0 | 0 | 3 |
| 0.4 | 0.5 | 0 | 1 | 1 |
| 0.4 | 0.6 | 0 | 0 | 3 |
| 0.4 | 0.7 | 0 | 0 | 3 |
| 0.5 | 0.5 | 0 | 1 | 0 |
| 0.5 | 0.6 | 0 | 0 | 2 |
| 0.5 | 0.7 | 0 | 0 | 2 |

**en** (n=95, yes=58):

| reject < | accept ≥ | false-reject | false-accept | flagged |
|---|---|---|---|---|
| 0.2 | 0.5 | 0 | 2 | 5 |
| 0.2 | 0.6 | 0 | 1 | 7 |
| 0.2 | 0.7 | 0 | 0 | 8 |
| 0.3 | 0.5 | 0 | 2 | 3 |
| 0.3 | 0.6 | 0 | 1 | 5 |  ← current
| 0.3 | 0.7 | 0 | 0 | 6 |
| 0.4 | 0.5 | 0 | 2 | 1 |
| 0.4 | 0.6 | 0 | 1 | 3 |
| 0.4 | 0.7 | 0 | 0 | 4 |
| 0.5 | 0.5 | 0 | 2 | 0 |
| 0.5 | 0.6 | 0 | 1 | 2 |
| 0.5 | 0.7 | 0 | 0 | 3 |

**ja** (n=89, yes=50):

| reject < | accept ≥ | false-reject | false-accept | flagged |
|---|---|---|---|---|
| 0.2 | 0.5 | 0 | 4 | 11 |
| 0.2 | 0.6 | 0 | 0 | 16 |
| 0.2 | 0.7 | 0 | 0 | 17 |
| 0.3 | 0.5 | 0 | 4 | 8 |
| 0.3 | 0.6 | 0 | 0 | 13 |  ← current
| 0.3 | 0.7 | 0 | 0 | 14 |
| 0.4 | 0.5 | 0 | 4 | 5 |
| 0.4 | 0.6 | 0 | 0 | 10 |
| 0.4 | 0.7 | 0 | 0 | 11 |
| 0.5 | 0.5 | 3 | 4 | 0 |
| 0.5 | 0.6 | 3 | 0 | 5 |
| 0.5 | 0.7 | 3 | 0 | 6 |

## Where each judge disagrees with the adjudication (text)

### jev: 1 confident errors

- [en/D/cal] jev=accept adj=no (majority) jev_p=0.62 live=reject structural=0
  - Q: What can the robot friend do on your own computer?
  - candidate: It can do what you want.

### live: 27 confident errors

- [ja/D/cal] live=reject adj=yes (agree) jev_p=0.88 live=reject structural=1
  - Q: 文中の「社会実装」の意味として最も適切なものを選んでください。
  - candidate: 技術やアイデアを現実の社会で実際に活用すること
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.02 live=accept structural=0
  - Q: 根据文中信息，可以合理推断出古罗马家庭在教育女孩方面与教育男孩相比，存在何种差异？
  - candidate: 女孩的学校教育比男孩的学校教育更为普遍和深入。
- [ja/D/cal] live=accept adj=no (majority) jev_p=0.53 live=accept structural=0
  - Q: 文中の「自らの肌で実感していく」の意味として最も適切なものを選んでください。
  - candidate: 自分の手で触れて確認していく
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.02 live=accept structural=0
  - Q: 根据文中信息，什么东西会让人生病？
  - candidate: 洗手
- [zh/D/win_main] live=accept adj=no (agree) jev_p=0.23 live=accept structural=None
  - Q: 根据上述材料，关于古罗马儿童的生活，最可能推出哪一项？
  - candidate: 古罗马儿童的个人价值主要通过为家庭做出贡献来体现。
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.29 live=accept structural=0
  - Q: 根据段落内容，可以推断出作者对这件T恤的看法与以下哪种说法最为接近？
  - candidate: 作者认为这件T恤的图案设计是其最突出的特点，远超其他方面。
- [ja/D/cal] live=accept adj=no (agree) jev_p=0.17 live=accept structural=0
  - Q: 文中の（結晶）の意味として最も適切なものを選んでください。
  - candidate: 移ろいやすい色彩を定着させた媒体
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.14 live=accept structural=0
  - Q: 作者在文章结尾强调合规可成为‘核心竞争力’和‘制度性优势’，其主要意图是什么？
  - candidate: 警告SaaS企业若忽视合规将面临淘汰
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.18 live=accept structural=0
  - Q: 根据文章内容，作者在感到压力大时，可能会采取哪种行动来缓解情绪？
  - candidate: 回忆与这件T恤相关的具体事件
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.09 live=accept structural=0
  - Q: 根据文中描述，可以推断出关于这只泰迪熊的哪些信息？
  - candidate: 泰迪熊的蓝色毛衣是它最先拥有的物品之一。
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.02 live=accept structural=0
  - Q: 根据文章描述，制作一个简易机械臂需要用到哪种类型的电机来精确控制转动角度？
  - candidate: 直流电机
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.20 live=accept structural=0
  - Q: 在文中，“假装自己在骑马”这个表达是什么意思？
  - candidate: 模仿马匹的动作
- [en/D/cal] live=accept adj=no (agree) jev_p=0.25 live=accept structural=0
  - Q: What does the term "conservation" mean in this passage?
  - candidate: The act of planting trees
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.51 live=accept structural=0
  - Q: 在文中，“闪闪发光”这个短语最贴切的意思是什么？
  - candidate: 发出微弱的光芒
- [en/D/cal] live=accept adj=no (agree) jev_p=0.27 live=accept structural=1
  - Q: What does the passage suggest is like 'showing how a child learns'?
  - candidate: Telling people what is in the data
- [ja/D/cal] live=accept adj=no (agree) jev_p=0.56 live=accept structural=0
  - Q: 文中の（冷徹に認識する）の意味として最も適切なものを選んでください。
  - candidate: 悲観的な見通しを持って警戒する
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.04 live=accept structural=0
  - Q: 根据文中信息，什么东西可以清洁我们的手？
  - candidate: 洗手
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.03 live=accept structural=0
  - Q: 在文中，“它就像我的家人一样”这句话中的“家人”是什么意思？
  - candidate: 指有共同兴趣的人
- [ja/D/cal] live=accept adj=no (agree) jev_p=0.05 live=accept structural=0
  - Q: この文章全体を通して最も強く伝えたいメッセージは何ですか？
  - candidate: 風車はかつて水をくみ上げるために使われていた
- [en/D/cal] live=reject adj=yes (agree) jev_p=0.80 live=reject structural=1
  - Q: What does the term "conservation" mean in this passage?
  - candidate: The protection of natural resources
- [ja/D/cal] live=reject adj=yes (agree) jev_p=0.91 live=reject structural=0
  - Q: 著者が最後の段落で『使い捨てプラスチックの規制は……試金石となっている』と述べた意図として、最も適切なものはどれか？
  - candidate: 環境問題が国家の制度設計能力を問う課題であると強調するため
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.45 live=accept structural=1
  - Q: 根据段落内容，可以推断出联合国环境规划署（UNEP）推动缔结全球协议的主要动因是什么？
  - candidate: 为了统一各国塑料禁令的执法标准并解决法规碎片化问题
- [ja/D/cal] live=accept adj=no (majority) jev_p=0.51 live=accept structural=0
  - Q: 文中の「形にした」の意味として最も適切なものを選んでください。
  - candidate: 見た目を変えて表現した
- [ja/D/cal] live=accept adj=no (majority) jev_p=0.35 live=accept structural=0
  - Q: 文中の「極致」の意味として最も適切なものを選んでください。
  - candidate: 限界を超えた先にある境地
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.02 live=accept structural=0
  - Q: 公司多久向老板提交一次报告？
  - candidate: 每天
- [ja/D/cal] live=accept adj=no (agree) jev_p=0.20 live=accept structural=0
  - Q: 文中の（無力化される）の意味として最も適切なものを選んでください。
  - candidate: 存在そのものが否定される
- [zh/D/cal] live=accept adj=no (agree) jev_p=0.16 live=accept structural=0
  - Q: 根据文中信息，可以合理推断出古罗马家庭在教育女孩方面与教育男孩相比，存在何种差异？
  - candidate: 古罗马家庭普遍认为女孩的教育不如男孩重要，因此很少进行教育。
