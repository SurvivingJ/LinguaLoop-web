# Recheck pack 04 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/back/04.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_04.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/verdicts/04.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/packs/recheck_04.gold.md`. Do not open it yet.


## 35742c67-2-en  (English reference -> back-translate into Chinese)

- context before: In ancient times, people built the Great Wall for defence.
- **TARGET:** The Great Wall is in northern China, and it is very, very long.
- context after: Building the Great Wall took a lot of manpower and many years of time.

## 3574dd04-5-en  (English reference -> back-translate into Chinese)

- context before: To encourage everyone to sort garbage, a designer drew this simple and easy-to-recognize pattern.
- **TARGET:** It quickly became popular and was used in many countries.
- context after: The three arrows of this symbol represent three steps of waste management: reduce use, reuse, and recycle.

## 36e75a96-9-en  (English reference -> back-translate into Chinese)

- context before: The longer the supply chain, the more water is used.
- **TARGET:** If we buy a little less clothing, we can save water.
- context after: When washing clothes, also don't waste water.

## 38096cf4-5-en  (English reference -> back-translate into Chinese)

- context before: Poke some small holes in the bottom and sides of the box.
- **TARGET:** Put the kitchen waste into the box.
- context after: Then add some soil and fallen leaves.

## 38096cf4-11-en  (English reference -> back-translate into Chinese)

- context before: They will smell bad.
- **TARGET:** After a few weeks, the kitchen waste will turn into dark soil.
- context after: This soil is very good.

## 38096cf4-15-en  (English reference -> back-translate into Chinese)

- context before: Making compost can reduce garbage.
- **TARGET:** It can also help plants grow.
- context after: Gardening has become easier.

## 3a07c050-5-en  (English reference -> back-translate into Chinese)

- context before: They could play with it at home, and they could also play with it outside.
- **TARGET:** The wooden horse made children's playtime more fun.
- context after: The children of ancient Rome liked this toy very much; they learned and grew through play.

## 3deb1f73-8-en  (English reference -> back-translate into Chinese)

- context before: Engineers invented the wind turbine.
- **TARGET:** It looks a little like a windmill, but its function is different.
- context after: Wind turbines can generate electricity.

## 4030db89-11-en  (English reference -> back-translate into Chinese)

- context before: Indigenous knowledge teaches people how to protect water.
- **TARGET:** Good resource management lets agriculture keep going all the time.
- context after: Traditional methods are simple, but very useful.

## 420128e8-9-en  (English reference -> back-translate into Chinese)

- context before: You can compete against them.
- **TARGET:** A match is competition.
- context after: Winning makes you very happy.

## 420128e8-12-en  (English reference -> back-translate into Chinese)

- context before: After losing, you can play again.
- **TARGET:** Playing games should be fun.

## 448826e8-3-en  (English reference -> back-translate into Chinese)

- context before: First, prepare a plastic box with a lid and put it on the balcony or in a corner of the yard.
- **TARGET:** A few small holes must be made in the box bottom, for drainage and air.
- context after: Next, in the box, first lay a layer of dry leaves or torn-up paper, and then add kitchen waste.

## 4980d9b2-1-en  (English reference -> back-translate into Chinese)

- context before: In the development landscape of contemporary metropolises, urban green spaces and vertical farms have gone beyond their purely ecological function and evolved into strategic elements reshaping the economic geography.
- **TARGET:** Parks, community gardens, and even the greening systems on building facades and rooftops, traditionally regarded as "non-productive spaces", are being deeply embedded in the urban capital cycle through multiple value chains.
- context after: The market premium mechanism of high-end real estate projects is significantly driven by landscape resources, and residential units adjacent to or integrating high-quality green space often achieve a value increase of more than 20%, a phenomenon especially prominent in the core areas of first-tier cities where land is scarce.

## 4980d9b2-6-en  (English reference -> back-translate into Chinese)

- context before: Through multi-layer hydroponics, aeroponics and artificial intelligence environmental control technology, such facilities can achieve, within a three-dimensional space of tens of thousands of square meters, an output efficiency equivalent to hundreds of hectares of traditional farmland, and supply fresh leafy vegetables and medicinal plants without interruption all year round.
- **TARGET:** Their characteristic of being located close to end consumers greatly reduces logistics losses and the carbon footprint, forming a resilient alternative to fragile global supply chains.
- context after: When frequent extreme weather causes fluctuations in staple grain producing areas, distributed urban food production networks show a significant risk-hedging capacity, leading local governments to include such projects in the emergency planning of critical infrastructure.

## 4980d9b2-9-en  (English reference -> back-translate into Chinese)

- context before: Viewed from the macro perspective of urban planning, sustainability has been transformed from a moral initiative into economic rationality.
- **TARGET:** Mixed-use development is being redefined: a commercial complex integrating a vertical farm is no longer merely a display of corporate social responsibility, but becomes a business strategy for attracting high-end tenants and increasing brand stickiness.
- context after: Through policy tools such as floor-area-ratio bonuses and tax reductions, the government guides private investment toward construction projects with ecological service functions, thereby lowering public finance's long-term spending on sewage treatment, heat island mitigation and air pollution control.

## 4bba338a-6-en  (English reference -> back-translate into Chinese)

- context before: When dirty water flows into rivers, fish will also die.
- **TARGET:** Shops keep selling new clothes, so people keep buying.
- context after: This is consumerism.

## 4bba338a-9-en  (English reference -> back-translate into Chinese)

- context before: The road from the factory to the shop is a road called the supply chain.
- **TARGET:** If we buy a little fewer clothes, we can save water and can also help the Earth.

## 5030b71f-15-en  (English reference -> back-translate into Chinese)

- context before: At the same time, there is also discussion suggesting that governments may need to collect more tax from enterprises that use artificial intelligence, and then use that money to help the affected workers.
- **TARGET:** However, there are still many problems.
- context after: Not everyone can learn new skills quickly.

## 53323621-16-en  (English reference -> back-translate into Chinese)

- context before: At the same time, developing biodegradable fibers and improving the recycling and reuse technology of discarded textiles are also important paths to relieve resource pressure.
- **TARGET:** However, technological innovation, without a simultaneous change in consumption concepts, will ultimately struggle to move forward.
- context after: Only by cultivating, through education and public policy guidance, a rational consumption culture of "less but better", and resisting the symbolic impulse of overconsumption, can space be created on the demand side to relieve the burden on resources.

## 53323621-21-en  (English reference -> back-translate into Chinese)

- context before: This is not only a renewal concerning clean technology, but also a deep dialogue involving ethics, economics and ecological philosophy: between the limits of growth and the transience of beauty, can humanity build a sustainable aesthetic that both respects the rhythms of nature and does not lose aesthetic dignity?
- **TARGET:** The answer perhaps lies in reflecting on the inertia of consumerism and in the persistent pursuit of supply chain justice.

## 5651b4c5-2-en  (English reference -> back-translate into Chinese)

- context before: They drew symbols to show how high or low sounds were.
- **TARGET:** This is musical notation.
- context after: Musical notation helps composers write songs.

## 5651b4c5-8-en  (English reference -> back-translate into Chinese)

- context before: Students practiced and remembered the meanings of the symbols.
- **TARGET:** Over a long time, musical notation became simpler.
- context after: Now, many people learn music.

## 568533a8-5-en  (English reference -> back-translate into Chinese)

- context before: Meetings start on time, transport timetables are calibrated in units of seconds, and personal planners are filled with inviolable blocks of time; this militarized management of time reflects a highly institutionalized and efficiency-oriented social logic.
- **TARGET:** However, in many Mediterranean, Middle Eastern and Latin American societies, time shows the characteristics of "polychronic time".
- context after: Time is not a container that is cut up, but a flowing fabric, and the completeness of interpersonal interaction takes priority over the markings of the clock.

## 568533a8-23-en  (English reference -> back-translate into Chinese)

- context before: True cross-cultural competence lies not in forcibly unifying the scale of time, but in cultivating "time sensitivity": understanding how different cultures weave their webs of temporal meaning, and negotiating a rhythm of flexible coexistence in a globalized context.
- **TARGET:** As the world becomes ever "faster", perhaps the deepest wisdom lies precisely in learning to ferry calmly through the differing currents of time.

## 56d76dd3-1-en  (English reference -> back-translate into Chinese)

- context before: In the frontier of contemporary materials science, research on biodegradable plastics has become one of the core topics in responding to global environmental impact.
- **TARGET:** Traditional plastics are made of long-chain polymers, which are extremely hard to break in the natural environment, leading to the accumulation of pollution that does not decay for hundreds of years.
- context after: In sharp contrast, the design philosophy of biodegradable plastics lies in the "controllable instability" of their molecular structure, that is, under specific ecological conditions, the polymer chains can be recognized by microorganisms in the environment as metabolizable organic substrates, thereby initiating the biodegradation process.
