# Review pack 04 — zh -> en

Read `data/sentence_refs/pilot_2026-10-30/zh/aligned/sentence_refs/rules_review.md` first. Step 1 is blind: do not read below the marker until your back-translation file for that test is written.

## 61eb20cc-c8da-4dcc-9d7c-7e51aa463129

Write `back_translations/61eb20cc-c8da-4dcc-9d7c-7e51aa463129.en.json` from these English sentences:

- idx 0: In the precise system of modern aeronautical engineering, aircraft design is in essence an artistic application of physical laws, and aerodynamic principles in particular occupy a central position within it.
- idx 1: When an aircraft travels through the atmosphere, the interaction between its wings and the airflow determines the basic feasibility of flight.
- idx 2: The core of this process lies in the mechanism of lift generation: the airflow over the upper surface of the wing speeds up because of the greater curvature, causing the pressure to drop; by comparison, the airflow over the lower surface moves more slowly and the pressure is relatively higher.
- idx 3: This pressure difference is perpendicular to the direction of the airflow and forms an upward net force, namely lift.
- idx 4: According to Bernoulli's theorem, an increase in fluid velocity is necessarily accompanied by a decrease in static pressure, which provides a classical physical explanation for lift.
- idx 5: However, relying only on Bernoulli's principle is not enough to fully describe complex real flow phenomena, so modern aerodynamics tends more toward a combined analysis incorporating Newton's third law: the wing deflects the airflow downward through the angle of attack, and the airflow in turn pushes the wing upward with an equal and opposite force, thereby producing lift.
- idx 6: During flight, lift is not the only force acting on the aircraft.
- idx 7: Coexisting with it is drag, which is the opposing force that air exerts on the aircraft's forward motion, and which can be subdivided into several types, such as pressure drag, friction drag and induced drag.
- idx 8: Pressure drag arises from the pressure imbalance between the front and rear of the aircraft, and is especially pronounced where the fuselage cross-section changes sharply; friction drag comes from the viscous shear between air molecules and the aircraft surface, and is greatly affected by surface roughness and the Reynolds number; and induced drag is a by-product of lift, caused by the local downwash induced by wingtip vortices, and its strength increases as lift increases.
- idx 9: To achieve efficient cruising, aeronautical engineers must make fine trade-offs in the aerodynamic configuration in order to maximize the lift-to-drag ratio, that is, the lift that can be produced per unit of drag, which is a key indicator of flight efficiency.
- idx 10: From the perspective of engineering implementation, aircraft design is a multidisciplinary coupled optimization game.
- idx 11: Advances in materials science have allowed composite materials to be widely used, which has not only reduced structural weight but also enhanced fatigue durability; the development of computational fluid dynamics, CFD, in turn enables engineers to simulate aerodynamic performance under extreme conditions in a virtual wind tunnel, thereby completing multiple rounds of iteration before prototype manufacturing.
- idx 12: In addition, active flow control technologies, such as boundary layer suction or synthetic jets, are being explored for adjusting flow separation in real time, further extending the flight envelope.
- idx 13: Behind these cutting-edge technologies is the in-depth solution of the Navier-Stokes equations, whose nonlinear nature makes turbulence modeling to this day a problem that the physics community has not fully conquered.
- idx 14: It is worth noting that even in modern airliners highly integrated with autopilot and artificial intelligence, the basic physical laws of aerodynamics still cannot be violated.
- idx 15: All the control actions performed by pilots or flight control systems, whether pitch, roll or yaw, ultimately come down to the precise regulation of aerodynamic moments.
- idx 16: The aerodynamic challenges that an aircraft faces in different flight phases, such as takeoff, cruise and landing, differ, requiring the wing shape, such as the extension of flaps and slats, to adapt dynamically.
- idx 17: From this it can be seen that aeronautical engineering is not only a collection of technologies, but also an externalized expression of humanity's deep understanding of the laws of nature.
- idx 18: Every smooth takeoff and landing is the result of strict adherence to the laws of physics, and also demonstrates the outstanding ability of engineering wisdom to achieve controllability in complex systems.

--- GOLD BELOW, DO NOT READ YET ---

- idx 0 gold: 在现代航空工程的精密体系中，飞行器的设计本质上是物理法则的艺术化应用，尤其是空气动力学原理在其中占据了核心地位。
- idx 1 gold: 当一架飞机在大气层中穿行时，其机翼与气流之间的相互作用决定了飞行的基本可行性。
- idx 2 gold: 这一过程的核心在于升力的生成机制——机翼上表面的气流因曲率较大而流速加快，导致压力降低；相比之下，下表面的气流流速较慢，压力相对较高。
- idx 3 gold: 这种压力差垂直于气流方向，形成向上的净力，即升力。
- idx 4 gold: 根据伯努利定理，流体速度的增加必然伴随着静压的减小，这为升力提供了经典物理解释。
- idx 5 gold: 然而，仅依赖伯努利原理并不足以完全描述复杂的真实流动现象，因此现代空气动力学更倾向于结合牛顿第三定律进行综合分析：机翼通过攻角向下偏转气流，气流则以相等且反向的力推动机翼上升，从而产生升力。
- idx 6 gold: 飞行过程中，升力并非唯一作用于飞机的力。
- idx 7 gold: 与之同时存在的还有阻力，这是空气对飞机前进运动施加的反向力，可细分为压差阻力、摩擦阻力以及诱导阻力等多种类型。
- idx 8 gold: 压差阻力源于飞机前后方的压力不平衡，尤其在机身截面剧烈变化处尤为显著；摩擦阻力则来源于空气分子与飞机表面之间的黏性剪切作用，受表面粗糙度和雷诺数影响极大；而诱导阻力则是升力的副产品，由翼尖涡流引起局部下洗气流所致，其强度随升力增大而增强。
- idx 9 gold: 为了实现高效巡航，航空工程师必须在气动构型上进行精细权衡，以最大化升阻比——即单位阻力下所能产生的升力，这是衡量飞行效率的关键指标。
- idx 10 gold: 从工程实现的角度看，飞机的设计是一场多学科耦合的优化博弈。
- idx 11 gold: 材料科学的进步使得复合材料得以广泛应用，不仅减轻了结构重量，还增强了疲劳耐久性；计算流体动力学（CFD）的发展则使工程师能够在虚拟风洞中模拟极端工况下的气动性能，从而在原型制造前完成多轮迭代。
- idx 12 gold: 此外，主动流动控制技术，如边界层吸入或合成射流，正在被探索用于实时调节气流分离，进一步延展飞行包线。
- idx 13 gold: 这些前沿技术的背后，是对纳维-斯托克斯方程组的深入求解，其非线性特性使得湍流建模至今仍是物理学界未完全攻克的难题。
- idx 14 gold: 值得注意的是，即便在自动驾驶与人工智能高度集成的现代客机中，空气动力学的基本物理规律依然不可违背。
- idx 15 gold: 飞行员或飞控系统所执行的所有操纵动作——无论是俯仰、滚转还是偏航——最终都归结为对气动力矩的精确调控。
- idx 16 gold: 飞机在不同飞行阶段（如起飞、巡航、降落）所面临的气动挑战各异，要求机翼形态（如襟翼与缝翼的展开）能够动态适应。
- idx 17 gold: 由此观之，航空工程不仅是技术的集合体，更是人类对自然法则深刻理解的外化表现。
- idx 18 gold: 每一次平稳起降，都是对物理定律严谨遵循的结果，也彰显了工程智慧在复杂系统中实现可控性的卓越能力。

## 6ff700da-b34a-404e-a4f3-e0705401f821

Write `back_translations/6ff700da-b34a-404e-a4f3-e0705401f821.en.json` from these English sentences:

- idx 0: In the practical dimension of contemporary environmental ethics, the home composting system has become a microcosmic vehicle that makes the concept of urban sustainability concrete, not only reflecting individuals' active assumption of ecological responsibility, but also constituting an indispensable distributed node in the city's waste reduction strategy.
- idx 1: Through the localized cyclical conversion of organic waste, household-level resource reuse mechanisms effectively shorten the traditional waste treatment chain, thereby lowering the carbon footprint and strengthening ecological resilience at the community level.
- idx 2: This do-it-yourself ecological intervention is essentially a gentle reconstruction of the industrialized consumption model, and behind it lies a deep horticultural philosophy, namely that a non-predatory, symbiotic relationship should be established between humans and the land.
- idx 3: To achieve efficient and hygienic home composting, the first thing is to understand the biochemical balance between "green materials" and "brown materials".
- idx 4: Green materials are rich in nitrogen and include wet organic matter such as kitchen fruit peels, coffee grounds and fresh grass clippings; brown materials provide a carbon source and are dry residues such as dry leaves, shredded cardboard and sawdust.
- idx 5: The ideal ratio is about 1:2 by volume, and this carbon-to-nitrogen ratio can promote the succession from mesophilic to thermophilic microbial communities, so that the pile rises to 55–65°C within a few days, effectively inactivating pathogens and weed seeds.
- idx 6: Special attention must be paid to strictly excluding animal residues such as meat, fats and dairy products, because they easily cause anaerobic fermentation and breed odors and pests.
- idx 7: The choice of compost container must suit local conditions.
- idx 8: City apartments can use a sealed worm composting bin, using the gut microbes of red earthworms, Eisenia fetida, to efficiently break down finely chopped kitchen scraps, producing "black gold" rich in plant growth hormones, a concentrated humus liquid.
- idx 9: Those with a yard should build a tiered compost bin, using physical separation to achieve continuous processing of the different fermentation stages: the bottom layer is the primary decomposition zone, the middle layer is the maturation transition zone, and new material is continuously added to the top layer.
- idx 10: Regularly turning the pile to ensure oxygen penetration and prevent local anaerobic acidification is the key operation for maintaining the activity of the microbial community.
- idx 11: From the perspective of ecological engineering, home composting is in fact a low-entropy cycle model.
- idx 12: Traditional landfilling makes organic matter decompose under oxygen-free conditions, releasing methane, CH₄, a potent greenhouse gas, while aerobic composting converts it into stable humus and sequesters carbon within the soil matrix.
- idx 13: When this matured product is applied to a home gardening system, it not only improves soil aggregate structure and increases water and nutrient retention, but also rebuilds the positive feedback loop among plants, microorganisms and organic matter.
- idx 14: Studies show that in planting beds with long-term application of homemade compost, the microbial diversity index is more than 40% higher than in the control group, significantly enhancing plants' stress resistance.
- idx 15: Especially profound is that this daily practice contains a "cognitive transformation effect" in the sense of behavioral ecology.
- idx 16: When individuals personally experience the complete cycle of a banana peel turning into fertile soil, the boundary of their cognition of the concept of "waste" will undergo a fundamental shift: waste is no longer the end point of linear consumption, but an intermediary in circular metabolism.
- idx 17: This embodied cognition in turn catalyzes broader sustainable lifestyle choices, forming a chain reaction of behaviors from waste reduction to low-carbon travel and from organic consumption to energy saving.
- idx 18: Therefore, home composting is not only a technical operation, but also a ritual practice of constructing ecological subjectivity, reshaping the ethical contract between humans and nature within micro-level life politics.

--- GOLD BELOW, DO NOT READ YET ---

- idx 0 gold: 在当代环境伦理的实践维度中，家庭堆肥系统已成为都市可持续性（sustainability）理念具象化的微观载体，不仅体现个体对生态责任的主动承担，更构成城市减废（waste reduction）战略中不可或缺的分布式节点。
- idx 1 gold: 通过有机（organic）废弃物的本地化循环转化，家庭层面的资源再利用机制有效缩短了传统垃圾处理链条，从而降低碳足迹并增强社区层面的生态韧性。
- idx 2 gold: 这一自己动手（DIY）型生态干预，本质上是对工业化消费模式的温和重构，其背后潜藏着深层的园艺（horticulture）哲学——即人与土地之间应建立一种非掠夺性的共生关系。
- idx 3 gold: 要实现高效且卫生的家庭堆肥运作，首要在于理解“绿色材料”与“棕色材料”的生化平衡。
- idx 4 gold: 绿色材料富含氮元素，包括厨余果皮、咖啡渣、新鲜草屑等湿性有机物；棕色材料则提供碳源，如干树叶、碎纸板、木屑等干燥残余物。
- idx 5 gold: 理想配比约为1:2（体积比），此碳氮比可促进嗜温菌群向嗜热菌群的演替，使堆体在数日内升至55–65°C，有效灭活病原体与杂草种子。
- idx 6 gold: 须特别注意，动物性残余如肉类、油脂及乳制品应严格排除，因其易引致厌氧发酵，滋生异味与害虫。
- idx 7 gold: 堆肥容器的选择需因地制宜。
- idx 8 gold: 城市公寓可采用密闭式蠕虫堆肥箱（vermicomposter），利用红蚯蚓（Eisenia fetida）的肠道微生物高效降解细碎厨余，产出富含植物生长激素的“黑色金子”——腐殖质浓缩液。
- idx 9 gold: 而拥有庭院者则宜构建分层式堆肥仓，通过物理隔离实现不同发酵阶段的连续处理：底层为初级分解区，中层为熟化过渡带，顶层持续投入新料。
- idx 10 gold: 定期翻堆（aerobic turning）确保氧气渗透，防止局部厌氧酸化，是维持微生物群落活性的关键操作。
- idx 11 gold: 从生态工程学视角观之，家庭堆肥实为一种低熵循环模型。
- idx 12 gold: 传统填埋使有机质在无氧条件下分解，释放强效温室气体甲烷（CH₄），而好氧堆肥则将其转化为稳定腐殖质，封存碳素于土壤基质之中。
- idx 13 gold: 当此腐熟产物被施用于家庭园艺系统时，不仅改善土壤团粒结构，提升保水保肥能力，更重建了植物—微生物—有机质之间的正向反馈回路。
- idx 14 gold: 研究表明，长期施用自制堆肥的种植床，其微生物多样性指数较对照组提升逾40%，显著增强植物抗逆性。
- idx 15 gold: 尤为深远的是，这一日常实践蕴含行为生态学意义上的“认知转化效应”。
- idx 16 gold: 当个体亲历香蕉皮蜕变为沃土的完整周期，其对“废物”概念的认知边界将发生根本位移——废弃物不再是线性消费的终点，而是循环代谢的中介。
- idx 17 gold: 此种具身认知（embodied cognition）进而催化更广泛的可持续生活方式选择，形成从减废到低碳出行、从有机消费到能源节约的行为链式反应。
- idx 18 gold: 因此，家庭堆肥不仅是技术操作，更是生态主体性建构的仪式性实践，在微观生活政治中重塑人与自然的伦理契约。

## 8002d9fe-964a-433f-8ac2-467ef84cc6e9

Write `back_translations/8002d9fe-964a-433f-8ac2-467ef84cc6e9.en.json` from these English sentences:

- idx 0: A long time ago, people wrote slowly.
- idx 1: One person writing one book took many days.
- idx 2: Later, someone invented printing.
- idx 3: People could use wood or stone to make type, and then print it on paper.
- idx 4: This way, making a book was fast.
- idx 5: Books became more and more numerous, and many people could read.
- idx 6: Knowledge began to spread.
- idx 7: More people learned to write and to read.

--- GOLD BELOW, DO NOT READ YET ---

- idx 0 gold: 很久以前，人们写字很慢。
- idx 1 gold: 一个人写一本书，要用很多天。
- idx 2 gold: 后来，有人发明了印刷术。
- idx 3 gold: 人们可以用木头或石头做字模，然后印在纸上。
- idx 4 gold: 这样，做一本书很快。
- idx 5 gold: 书籍越来越多，很多人可以读书。
- idx 6 gold: 知识开始传播。
- idx 7 gold: 更多人学会了写字和看书。

## 8f0524f9-0920-4b91-ba00-c69a1d5dedb8

Write `back_translations/8f0524f9-0920-4b91-ba00-c69a1d5dedb8.en.json` from these English sentences:

- idx 0: People in different places see time differently.
- idx 1: Some people like to be on time.
- idx 2: For appointments or classes, they arrive early.
- idx 3: This is punctuality.
- idx 4: Some people take their time.
- idx 5: It is fine for ideas about time to be different.
- idx 6: Everyone has their own habits.
- idx 7: Some people write a schedule and look at it every day.
- idx 8: Some people remember things and do not write them down.
- idx 9: Now the world is connected together.
- idx 10: Globalization lets people from different cultures meet often.
- idx 11: Everyone needs to understand each other.
- idx 12: You are punctual, and I respect you.
- idx 13: I take my time, so please do not be angry.
- idx 14: This way, everyone is happy.

--- GOLD BELOW, DO NOT READ YET ---

- idx 0 gold: 不同地方的人看时间不一样。
- idx 1 gold: 有的人喜欢准时。
- idx 2 gold: 约会或上课，他们早早到。
- idx 3 gold: 这是守时性。
- idx 4 gold: 有的人慢慢来。
- idx 5 gold: 时间观念不一样，没关系。
- idx 6 gold: 每个人有习惯。
- idx 7 gold: 有些人写日程安排，每天看。
- idx 8 gold: 有些人记得事情，不写字。
- idx 9 gold: 现在世界连在一起了。
- idx 10 gold: 全球化让不同文化的人常见面。
- idx 11 gold: 大家要互相理解。
- idx 12 gold: 你守时，我尊重你。
- idx 13 gold: 我慢慢来，你别生气。
- idx 14 gold: 这样大家开心。

## 99dd6e29-c28d-41f5-b959-5d1c1041a3f1

Write `back_translations/99dd6e29-c28d-41f5-b959-5d1c1041a3f1.en.json` from these English sentences:

- idx 0: The evolution of musical notation systems profoundly reflects the historical process of humanity's understanding of the order of sound.
- idx 1: Since ancient times, different civilizations have tried to capture fleeting sounds with visual symbols, but early notation methods were mostly suggestive rather than precise.
- idx 2: Ancient Greece used letters to mark pitch, Byzantium used symbols to indicate the direction of the melody, and Chinese gongchepu used characters to record relative pitch positions; none of these systems specified rhythmic details, and their performance relied on the tradition of oral and personal transmission.
- idx 3: The truly revolutionary turning point began with the development of neume notation in Western Europe at the end of the Middle Ages, when monks added symbols above sacred texts to indicate the rise and fall of notes, which eventually evolved into the four-line staff, whose foundation was laid by Guido of Arezzo in the 11th century.
- idx 4: This system achieved a spatial representation of pitch through the clear correspondence between lines and spaces, and provided a necessary condition for the systematization of music theory.
- idx 5: By the Renaissance, the five-line staff was gradually established as the standard, and with the introduction of bar lines, key signatures and time signatures, notation became increasingly precise.
- idx 6: This technical evolution not only allowed the complex texture of polyphonic music to be conveyed accurately, but also profoundly influenced composers' ways of thinking.
- idx 7: Once sound could be completely recorded, composition was no longer confined to the realm of improvised performance, but became an intellectual activity that could be refined and revised on paper.
- idx 8: In the Baroque era, the popularity of figured bass notation further reflected the maturity of the concept of functional harmony; and from the Classical to the Romantic period, notation increasingly tended toward comprehensive control, with dynamics, tempo and expression markings appearing densely, reflecting the central position of individual emotional expression in music.
- idx 9: Since the 20th century, traditional notation has faced multiple challenges.
- idx 10: Schoenberg's twelve-tone system forced theorists to reconstruct the logic of pitch organization, and serialism brought parameters such as rhythm, duration and dynamics all under control, giving rise to a highly mathematical notational language.
- idx 11: At the same time, avant-garde composers such as John Cage questioned the authority of traditional notation, and developed graphic scores, text scores and even the open structures of chance music, emphasizing the performer's right to re-create.
- idx 12: The rise of electronic music brought an entirely new dimension: technical means such as spectral analysis, waveform diagrams and algorithmically generated scores allowed notation to go beyond the visual paradigm of the staff and enter the realm of data-based expression.
- idx 13: Today, the development of notation presents a pattern of diverse coexistence.
- idx 14: The traditional five-line staff is still the globally used technical language, supporting symphony orchestras, opera productions and academic composition teaching; while in the field of experimental music, mixed-media notation and real-time interactive notation, such as visual instructions in the Max/MSP environment, are constantly expanding the boundaries.
- idx 15: It is worth noting that after artificial intelligence became involved in music composition, machine-generated scores often combine symbolic logic with probabilistic models, prompting new discussions about "readability" and "playability".
- idx 16: Viewed from a historical dimension, notation is not only the evolution of a technical tool, but also a mirror of changes in the concept of the nature of music; it has both shaped composers' ways of imagining and reconstructed the cultural coding of auditory experience.
- idx 17: The development of notation is essentially humanity's eternal effort to capture infinite sonic possibilities with a limited system of symbols, and its trajectory of evolution is precisely a profound testimony to the interactive symbiosis of music theory and practice.

--- GOLD BELOW, DO NOT READ YET ---

- idx 0 gold: 记谱法体系的演变深刻反映了人类对声音秩序之理解的历史进程。
- idx 1 gold: 自远古时期起，不同文明便尝试以视觉符号捕捉稍纵即逝的音响，然而早期的记谱方式多具提示性而非精确性。
- idx 2 gold: 古希腊使用字母标记音高，拜占庭以符号指示旋律走向，而中国工尺谱则借字符记录相对音位——这些系统皆未规定节奏细节，其演奏依赖口传心授的传统。
- idx 3 gold: 真正革命性的转折始自中世纪末期西欧的纽姆谱发展，修士们在经文上方添加符号以指示音的升降，最终演化为四线谱，由圭多·达莱佐在11世纪奠定基础。
- idx 4 gold: 此一系统通过线与间的明确对应关系实现了音高的空间化表征，为音乐理论的系统化提供了必要条件。
- idx 5 gold: 至文艺复兴时期，五线谱逐渐确立为标准，配合小节线、调号与拍号的引入，记谱法日趋精密。
- idx 6 gold: 这一技术演进不仅使复调音乐的复杂织体得以准确传达，更深刻影响了作曲家的思维方式。
- idx 7 gold: 当声音可被完整记录，创作便不再局限于即兴表演的范畴，而是成为可在纸上推敲、修改的智力活动。
- idx 8 gold: 巴洛克时代，通奏低音记谱法的流行进一步体现了功能和声观念的成熟；而从古典到浪漫主义时期，记谱日益趋向全面控制，力度、速度、表情记号密集出现，反映出个体情感表达在音乐中的中心地位。
- idx 9 gold: 20世纪以降，传统记谱面临多重挑战。
- idx 10 gold: 勋伯格的十二音体系迫使理论家重构音高组织逻辑，序列主义将节奏、时值、力度等参数均纳入控制，催生出高度数学化的记谱语言。
- idx 11 gold: 与此同时，约翰·凯奇等先锋派作曲家质疑传统记谱的权威性，发展出图形谱、文字谱乃至机会音乐的开放式结构，强调演奏者的再创造权。
- idx 12 gold: 电子音乐的兴起更带来全新维度：频谱分析、波形图、算法生成乐谱等技术手段，使记谱超越五线谱的视觉范式，进入数据化表达领域。
- idx 13 gold: 今日，记谱法的发展呈现出多元并存格局。
- idx 14 gold: 传统五线谱仍是全球通行的技术语言，支撑着交响乐团、歌剧制作与学院派作曲教学；而在实验音乐领域，混合媒介记谱、实时交互记谱（如Max/MSP环境下的视觉指令）正不断拓展边界。
- idx 15 gold: 值得注意的是，人工智能介入音乐创作后，机器生成的乐谱常融合符号逻辑与概率模型，引发关于“可读性”与“可演性”的新讨论。
- idx 16 gold: 从历史维度审视，记谱不仅是技术工具的演进，更是音乐本体观念变迁的镜像——它既塑造了作曲家的想象方式，也重构了听觉经验的文化编码。
- idx 17 gold: 记谱法的发展，本质上是人类试图以有限符号系统捕捉无限音响可能性的永恒努力，其演变轨迹，正是音乐理论与实践互动共生的深层见证。

## 9f9e7cd7-4953-44f9-ab09-ebe232c15ca8

Write `back_translations/9f9e7cd7-4953-44f9-ab09-ebe232c15ca8.en.json` from these English sentences:

- idx 0: A long time ago, people did not know how to deal with garbage.
- idx 1: Later, someone drew three arrows that became a circle.
- idx 2: This design is very simple.
- idx 3: It tells people: garbage can become new things.
- idx 4: The three arrows look like they are dancing, and they also have symbolic meaning.
- idx 5: It represents everyone protecting the earth together.
- idx 6: Many countries use this symbol.
- idx 7: It appears on bottles and cartons.
- idx 8: On seeing it, people know to sort.
- idx 9: Good waste management makes cities cleaner.
- idx 10: Environmentalism is loving the earth.
- idx 11: This symbol has a very short history, but many people like it.
- idx 12: It makes recycling easy.

--- GOLD BELOW, DO NOT READ YET ---

- idx 0 gold: 很久以前，人们不知道怎么处理垃圾。
- idx 1 gold: 后来，有人画了三个箭头，变成一个圈。
- idx 2 gold: 这个设计很简单。
- idx 3 gold: 它告诉人们：垃圾可以变新东西。
- idx 4 gold: 三个箭头像在跳舞，也有象征意义。
- idx 5 gold: 它代表大家一起保护地球。
- idx 6 gold: 很多国家都用这个标志。
- idx 7 gold: 它出现在瓶子、纸盒上。
- idx 8 gold: 看到它，人们就知要分类。
- idx 9 gold: 好的废物管理让城市更干净。
- idx 10 gold: 环保主义就是爱地球。
- idx 11 gold: 这个标志的历史很短，但很多人喜欢。
- idx 12 gold: 它让回收变得容易。
