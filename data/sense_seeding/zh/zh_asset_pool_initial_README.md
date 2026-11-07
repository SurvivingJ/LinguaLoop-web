# Pool report: zh senses with no word assets and no exercises

Source: `data/exercise_seeding/zh/pool/pool_senses.csv` (4108 data rows, 12 columns). Computed by a Python `csv` script; no database or API calls. Percentages are of total rows.

## 1. Headline counts

| Metric | Value |
|---|---|
| Total rows | 4108 |
| Distinct lemmas | 3813 |
| Rows with test_refs > 0 | 4067 (99.0%) |

## 2. Distributions

### semantic_class

| semantic_class | Count | % |
|---|---:|---:|
| action | 1438 | 35.0% |
| abstract | 1129 | 27.5% |
| concrete | 805 | 19.6% |
| property | 528 | 12.9% |
| function | 83 | 2.0% |
| (empty) | 65 | 1.6% |
| proper | 60 | 1.5% |

### part_of_speech (top 12 raw values)

| part_of_speech | Count | % |
|---|---:|---:|
| n | 1890 | 46.0% |
| v | 1050 | 25.6% |
| a | 182 | 4.4% |
| d | 160 | 3.9% |
| vn | 157 | 3.8% |
| l | 129 | 3.1% |
| noun | 97 | 2.4% |
| verb | 83 | 2.0% |
| nr | 82 | 2.0% |
| ns | 72 | 1.8% |
| i | 45 | 1.1% |
| nz | 37 | 0.9% |
| (all other values) | 124 | 3.0% |
| *distinct values total* | 31 | |

### zipf bands

| zipf band | Count | % |
|---|---:|---:|
| <3 | 327 | 8.0% |
| 3-4 | 1404 | 34.2% |
| 4-5 | 1439 | 35.0% |
| >=5 | 704 | 17.1% |
| null | 234 | 5.7% |

### test_refs buckets

| test_refs | Count | % |
|---|---:|---:|
| 0 | 41 | 1.0% |
| 1-2 | 3185 | 77.5% |
| 3-9 | 767 | 18.7% |
| 10+ | 115 | 2.8% |

### sense_rank

| sense_rank | Count | % |
|---|---:|---:|
| 1 | 3804 | 92.6% |
| 2 | 240 | 5.8% |
| 3 | 49 | 1.2% |
| 4 | 9 | 0.2% |
| 5 | 3 | 0.1% |
| 6 | 2 | 0.0% |
| 7 | 1 | 0.0% |

### is_validated

| is_validated | Count | % |
|---|---:|---:|
| True | 3883 | 94.5% |
| False | 225 | 5.5% |

## 3. Anomalies

| Check | Rows | Example sense_ids (up to 15) |
|---|---:|---|
| Empty lemma | 0 | none |
| Empty definition | 0 | none |
| Definition shorter than 6 characters (Python len, after strip) | 10 | 11413, 11059, 12574, 10419, 13471, 12320, 12510, 11688, 13042, 11980 |
| Lemma longer than 6 characters | 3 | 12518, 12840, 19937 |
| Duplicate (lemma, sense_rank) pairs: rows involved | 0 | none |

Duplicate (lemma, sense_rank) groups: 0 distinct pairs covering 0 rows.

| Proper noun / fragment candidates (part_of_speech in nr, ns, nz, nrt, nt OR semantic_class = proper) | 218 | 11635, 10606, 10705, 11828, 10682, 11123, 10609, 10074, 10824, 12086, 10384, 11353, 11483, 10766, 12894 |
| of which part_of_speech in nr/ns/nz/nrt/nt | 209 | 10606, 10705, 11828, 10682, 11123, 10609, 10074, 10824, 12086, 10384, 11353, 11483, 10766, 12894, 11339 |
| of which semantic_class = proper | 60 | 11635, 10430, 10261, 10900, 10920, 10919, 10345, 10902, 10496, 10205, 10344, 10966, 10202, 12518, 13193 |

Note: the examples below show that most nr/ns/nz/nrt/nt-tagged rows are ordinary common words (e.g. 伦理, 古老, 智慧), so the part_of_speech codes look unreliable for these rows; the proper-noun flag is best taken from semantic_class = proper.

### Examples: proper noun / fragment candidates (first 15)

| sense_id | lemma | part_of_speech | semantic_class | definition (first 40 chars) |
|---|---|---|---|---|
| 11635 | 地球 | n | proper | 太阳系八大行星之一，是人类已知唯一存在生命的天体。 |
| 10606 | 伦理 | ns | abstract | 伦理是指人与人之间相处时应遵循的道德原则和行为规范。 |
| 10705 | 文明 | nr | abstract | 指人类社会发展到较高阶段的状态，也指有礼貌、讲道理的行为。 |
| 11828 | 深度 | ns | abstract | 表示程度很大，多用于描述变化或影响的彻底性 |
| 10682 | 古老 | nr | property | 形容年代久远，存在时间很久。 |
| 11123 | 智慧 | nr | abstract | 指聪明、有见识，能正确判断和解决问题的能力。 |
| 10609 | 道德 | nr | abstract | 道德是社会生活中人们共同认可的行为准则和规范，用来判断是非善恶。 |
| 10074 | 普及 | ns | action | 普遍传播，使大众化。 |
| 10824 | 维度 | ns | abstract | 维度指事物或现象在某个方向上的特征或度量，如空间有长度、宽度、高度三个维度。 |
| 12086 | 东西 | ns | concrete | 指代前文提到的事物，尤其是自然现象或科学概念 |
| 10384 | 普通 | nz | property | 指一般的、平常的，没有特别之处。 |
| 11353 | 太阳 | ns | concrete | 太阳是太阳系的中心恒星，地球围绕它公转，为地球提供光和热。 |
| 11483 | 新鲜 | ns | property | 指食物、物品等没有变质、枯萎或失去原有状态，也指事物新颖、不陈旧。 |
| 10766 | 范畴 | nr | abstract | 指人的思维对客观事物普遍本质的概括和反映，或指类型、范围。 |
| 12894 | 二氧化碳 | nz | concrete | 无色无味的气体，由一个碳原子和两个氧原子组成，是常见的温室气体。 |

### Examples: short definitions (first 15)

| sense_id | lemma | definition |
|---|---|---|
| 11413 | 干 | 做，从事。 |
| 11059 | 观 | 看，观察。 |
| 12574 | 预示 | 预先显示。 |
| 10419 | 并存 | 同时存在 |
| 13471 | 来到 | 到达某处。 |
| 12320 | 提问 | 提出疑问。 |
| 12510 | 无需 | 不用，不必 |
| 11688 | 节能 | 节约能源。 |
| 13042 | 做饭 | 烹制饭菜。 |
| 11980 | 歼敌 | 消灭敌人。 |

### Examples: lemmas longer than 6 characters (first 15)

| sense_id | lemma | definition (first 40 chars) |
|---|---|---|
| 12518 | 联合国环境规划署 | 负责全球环境事务的国际组织 |
| 12840 | 联合国教科文组织 | 联合国教科文组织是联合国旗下专门负责教育、科学和文化事务的国际机构，简称教科文组 |
| 19937 | 美国联邦贸易委员会 | 美国负责保护消费者和促进市场竞争的政府机构 |

## 4. First 40 rows

Definition truncated to 40 characters.

| sense_id | lemma | part_of_speech | semantic_class | zipf | test_refs | definition |
|---|---|---|---|---:|---:|---|
| 10890 | 大家 | n | function | 5.6 | 30 | 指代包括说话人和听话人在内的所有人。 |
| 11449 | 环境 | n | abstract | 5.52 | 26 | 周围的自然条件，如空气、水、土地和生物 |
| 10564 | 可能 | 副词 | abstract | 6.01 | 25 | 表示事情也许是这样或发生。 |
| 10084 | 技术 | n | abstract | 5.72 | 25 | 人类在实践活动中积累的经验、知识和技能，以及相应的工具、设备等。 |
| 10382 | 不同 | a | property | 5.71 | 25 | 指事物之间没有共同点，有差别。 |
| 11697 | 保护 | v | action | 5.51 | 25 | 尽力照顾并使某人或某物不受损害。 |
| 10313 | 喜欢 | v | action | 5.73 | 24 | 指对人或事物有好感或感到兴趣。 |
| 11361 | 减少 | v | action | 5.17 | 23 | 使数量变少。 |
| 10624 | 发展 | 动词 | action | 6.03 | 22 | 某事物逐渐变得复杂或完善的过程 |
| 10134 | 系统 | n | abstract | 5.68 | 22 | 系统是指由相互联系、相互作用的若干部分组成的、具有一定结构和功能的整体。 |
| 10097 | 成为 | v | action | 5.93 | 21 | 变成某种状态或身份，强调变化的结果 |
| 10680 | 传统 | n | abstract | 5.43 | 21 | 指历史上流传下来的、具有特点的社会因素，如文化、思想、风俗、制度等。 |
| 10684 | 研究 | vn | action | 5.69 | 20 | 通过观察、实验或思考来探求事物的真相、性质或规律。 |
| 10370 | 全球 | n | concrete | 5.43 | 20 | 指整个地球或整个世界，包括所有国家、地区及其上的一切。 |
| 10633 | 简单 | a | property | 5.29 | 20 | 形容事情或问题不复杂，容易理解或处理。 |
| 10953 | 更好 | d | property | 4.96 | 20 | 指事物在程度上超过原来的状况，表示更加优秀或更令人满意。 |
| 10621 | 地方 | n | concrete | 5.82 | 19 | 某个区域或地理范围，常指有特定文化或人群的地方 |
| 10090 | 过程 | n | abstract | 5.5 | 19 | 指事物发展或进行所经过的程序、步骤或阶段。 |
| 11682 | 设计 | vn | action | 5.49 | 19 | 指在正式制作前，根据要求构思并制定出方法、方案或图样等。 |
| 10118 | 复杂 | a | property | 5 | 19 | 指事物或事情的结构、关系等繁多而难以理解或处理。 |
| 11150 | 空气 | n | concrete | 4.75 | 19 | 空气是由氮气、氧气等组成的混合气体，存在于地球周围，是生命必需的。 |
| 10604 | 持续 | vd | action | 5.25 | 18 | 延续不断，中间没有间断。 |
| 10931 | 问题 | 名词 | abstract | 6.19 | 17 | 某种情况中可能存在的缺点或令人质疑之处 |
| 10119 | 社会 | 名词 | abstract | 5.99 | 17 | 指由共同利益、文化或制度联系起来的人群整体。 |
| 10670 | 使用 | v | action | 5.87 | 17 | 利用；运用。指将某物或某种方式用于特定目的。 |
| 10226 | 影响 | vn | abstract | 5.74 | 17 | 事物对他事产生的作用或改变。 |
| 11635 | 地球 | n | proper | 5.01 | 17 | 太阳系八大行星之一，是人类已知唯一存在生命的天体。 |
| 11067 | 核心 | n | abstract | 4.99 | 17 | 指事物的中心或关键部分。 |
| 11853 | 需要 | v | action | 5.93 | 16 | 做某事不可缺少的条件或帮助 |
| 10745 | 提供 | v | action | 5.72 | 16 | 供给（所需的东西）。 |
| 10930 | 甚至 | d | function | 5.51 | 16 | 强调程度加深或范围扩大，常用于引出更进一步的情况。 |
| 10316 | 农业 | n | abstract | 5.26 | 16 | 指栽培农作物和饲养牲畜的生产活动。 |
| 10420 | 模式 | n | abstract | 5.2 | 16 | 某种事物的标准形式或可以照着做的样式。 |
| 10359 | 比如 | v | action | 5 | 16 | 用于举例说明。 |
| 10950 | 生活 | vn | action | 5.81 | 15 | 指人为了生存和发展而进行的各种活动。 |
| 10143 | 实现 | v | action | 5.39 | 15 | 使成为事实；完成目标或计划。 |
| 10255 | 形成 | v | action | 5.34 | 15 | 通过发展变化而成为具有某种特点的事物或出现某种情形。 |
| 12622 | 水 | n | concrete | 5.3 | 15 | 无色、无味、无臭的液体，是生命必需的物质。 |
| 10685 | 理解 | v | action | 5.18 | 15 | 明白事物的含义或道理，能够进行思考与分析。 |
| 11454 | 生态 | n | abstract | 4.92 | 15 | 生物与其环境之间相互作用的自然系统 |
