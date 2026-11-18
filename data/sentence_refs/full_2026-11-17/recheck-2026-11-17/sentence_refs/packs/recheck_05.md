# Recheck pack 05 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/back/05.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_05.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/verdicts/05.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/packs/recheck_05.gold.md`. Do not open it yet.


## 56d76dd3-12-en  (English reference -> back-translate into Chinese)

- context before: This reveals the gap between laboratory research and the real environment.
- **TARGET:** A deeper contradiction is that if bio-based plastics are promoted on a large scale, they may give rise to new ecological ethics problems, such as competition with food for land and water resource consumption.
- context after: Therefore, cutting-edge research is turning to synthetic biology approaches, designing programmable engineered bacterial strains that efficiently express polymer-cleaving enzymes when triggered by specific signals, achieving "precise biodegradation".

## 575bac7f-16-en  (English reference -> back-translate into Chinese)

- context before: The horizontal-axis structure of traditional windmills was retained, but the application of aerodynamic simulation and composite materials made blade length break through the hundred-metre level, and the swept area grew by geometric multiples.
- **TARGET:** The rise of offshore wind farms further moved power generation equipment to continental shelf areas where the wind is steadier and stronger.
- context after: Modern wind turbines have integrated intelligent control systems: lidar predicts wind speed changes and adjusts pitch angle in real time to optimize torque; digital twin technology builds virtual unit models to achieve predictive maintenance of faults.

## 5a475189-6-en  (English reference -> back-translate into Chinese)

- context before: It is a plush bear.
- **TARGET:** Every day, the little bear plays together with its owner.
- context after: The owner likes to hold it in their arms.

## 61cc1261-1-en  (English reference -> back-translate into Chinese)

- context before: In Japan, the way of drinking tea is an important ceremony.
- **TARGET:** It is a way of treating guests.
- context after: When drinking tea, people must be quiet and think good thoughts.

## 61cc1261-2-en  (English reference -> back-translate into Chinese)

- context before: It is a way of treating guests.
- **TARGET:** When drinking tea, people must be quiet and think good thoughts.
- context after: In this way, everyone will feel it is very harmonious.

## 61cc1261-3-en  (English reference -> back-translate into Chinese)

- context before: When drinking tea, people must be quiet and think good thoughts.
- **TARGET:** In this way, everyone will feel it is very harmonious.
- context after: This is an ancient tradition.

## 61eb20cc-6-en  (English reference -> back-translate into Chinese)

- context before: However, relying only on Bernoulli's principle is not enough to fully describe complex real flow phenomena, so modern aerodynamics tends to combine it with Newton's third law for comprehensive analysis: the wing deflects the airflow downward through the angle of attack, and the airflow in turn pushes the wing upward with an equal and opposite force, thereby producing lift.
- **TARGET:** During flight, lift is not the only force acting on the aircraft.
- context after: Coexisting with it is drag, which is the opposing force that air exerts on the forward motion of the aircraft, and which can be subdivided into many types such as pressure drag, friction drag and induced drag.

## 61eb20cc-16-en  (English reference -> back-translate into Chinese)

- context before: All the control actions performed by pilots or flight control systems, whether pitch, roll or yaw, ultimately come down to the precise regulation of aerodynamic moments.
- **TARGET:** The aerodynamic challenges that an aircraft faces in different flight phases, such as takeoff, cruising and landing, differ, requiring the wing shape, such as the deployment of flaps and slats, to adapt dynamically.
- context after: From this it can be seen that aeronautical engineering is not only a collection of technologies, but also an externalized manifestation of humanity's deep understanding of the laws of nature.

## 6ff700da-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** In the practical dimension of contemporary environmental ethics, the household composting system has become a micro-level carrier that embodies the concept of urban sustainability, not only reflecting an individual's active assumption of ecological responsibility, but also constituting an indispensable distributed node in the city's waste reduction strategy.
- context after: Through the localized cyclical conversion of organic waste, the household-level resource reuse mechanism effectively shortens the traditional waste treatment chain, thereby lowering the carbon footprint and strengthening community-level ecological resilience.

## 6ff700da-5-en  (English reference -> back-translate into Chinese)

- context before: Green materials are rich in nitrogen and include wet organic matter such as kitchen peelings, coffee grounds and fresh grass clippings; brown materials provide a carbon source, such as dry residues like dry leaves, shredded cardboard and sawdust.
- **TARGET:** The ideal ratio is about 1:2 by volume; this carbon-to-nitrogen ratio can promote the succession from mesophilic to thermophilic microbial communities, raising the pile to 55–65°C within a few days and effectively inactivating pathogens and weed seeds.
- context after: Special attention must be paid to strictly excluding animal-derived residues such as meat, fats and dairy products, because they easily cause anaerobic fermentation, breeding odors and pests.

## 6ff700da-6-en  (English reference -> back-translate into Chinese)

- context before: The ideal ratio is about 1:2 by volume; this carbon-to-nitrogen ratio can promote the succession from mesophilic to thermophilic microbial communities, raising the pile to 55–65°C within a few days and effectively inactivating pathogens and weed seeds.
- **TARGET:** Special attention must be paid to strictly excluding animal-derived residues such as meat, fats and dairy products, because they easily cause anaerobic fermentation, breeding odors and pests.
- context after: The choice of composting container must suit local conditions.

## 6ff700da-8-en  (English reference -> back-translate into Chinese)

- context before: The choice of composting container must suit local conditions.
- **TARGET:** City apartments can use a sealed vermicomposter, using the gut microbes of red earthworms, Eisenia fetida, to efficiently break down finely chopped kitchen waste, producing a humus concentrate rich in plant growth hormones, the "black gold".
- context after: Those with a yard should build a layered composting bin, using physical separation to achieve continuous processing of different fermentation stages: the bottom layer is the primary decomposition zone, the middle layer is the maturation transition zone, and the top layer continuously receives new material.

## 70dc83da-5-en  (English reference -> back-translate into Chinese)

- context before: The ingenuity of this design lies in its multi-layered symbolic meaning: the geometric structure itself is a global common language that needs no linguistic explanation, while the choice of green strengthens its association with nature and ecology.
- **TARGET:** Although this symbol originally served only a domestic American initiative, the high degree of abstraction in its form enabled it to cross national borders quickly.
- context after: After the 1972 Stockholm Conference on the Human Environment, the United Nations Environment Programme incorporated this kind of standardized symbol into its technical recommendations for global environmental governance.

## 7199de13-10-en  (English reference -> back-translate into Chinese)

- context before: Players can play together with friends.
- **TARGET:** They talk and plan their moves.
- context after: They help each other.

## 7199de13-11-en  (English reference -> back-translate into Chinese)

- context before: They talk and plan their moves.
- **TARGET:** They help each other.
- context after: In virtual worlds, people connect with each other using computers or phones.

## 73754e86-7-en  (English reference -> back-translate into Chinese)

- context before: In Mexico, time can be a little slower.
- **TARGET:** At a gathering of friends, arriving one hour late is also fine.
- context after: This is called time perception.

## 73754e86-8-en  (English reference -> back-translate into Chinese)

- context before: At a gathering of friends, arriving one hour late is also fine.
- **TARGET:** This is called time perception.
- context after: Because of cultural differences, the customs in each place are different.

## 73754e86-13-en  (English reference -> back-translate into Chinese)

- context before: Some people make plans first, and some people like to change their schedules at any time.
- **TARGET:** This is all fine.
- context after: What is important is mutual respect.

## 748c93f0-12-en  (English reference -> back-translate into Chinese)

- context before: The sweater was knitted by hand by the girl's mother.
- **TARGET:** She spent a long time before she finished knitting this sweater.
- context after: The stitches are very fine and close, and the colour is also very pretty.

## 7742bb7a-12-en  (English reference -> back-translate into Chinese)

- context before: I wore this blue T-shirt and, together with my friends, ran on the beach, built sandcastles, and also sang songs together.
- **TARGET:** At that time, I felt incredibly free and happy.
- context after: In that photo, I am wearing this T-shirt and smiling very happily; that is also my favourite photo.

## 7ac4f82a-5-en  (English reference -> back-translate into Chinese)

- context before: Teachers teach them new jobs.
- **TARGET:** Money should also be divided fairly.
- context after: Everyone should think of solutions together.

## 7ac4f82a-7-en  (English reference -> back-translate into Chinese)

- context before: Everyone should think of solutions together.
- **TARGET:** The world is changing, and we should be ready.

## 7dcd9417-3-en  (English reference -> back-translate into Chinese)

- context before: They drew three arrows on paper, forming a triangle.
- **TARGET:** This symbol means that things can be recycled and used again.
- context after: This design is very simple, and everyone can understand it.

## 7dcd9417-14-en  (English reference -> back-translate into Chinese)

- context before: The Earth is our common home.
- **TARGET:** We should cherish it.
- context after: When you see this symbol, put the recyclable things in the blue trash can.

## 83bf1379-7-en  (English reference -> back-translate into Chinese)

- context before: This sweater is for the bear.
- **TARGET:** The bear is very happy.
