# Recheck pack 06 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/back/06.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_06.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/verdicts/06.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/packs/recheck_06.gold.md`. Do not open it yet.


## 8a47b6b8-15-en  (English reference -> back-translate into Chinese)

- context before: Its existence fills Xiaoming's life with warmth and color.
- **TARGET:** No matter where he goes, Xiaoming takes Lanlan with him.
- context after: This plush toy carries Xiaoming's most beautiful childhood memories.

## 8c96f996-4-en  (English reference -> back-translate into Chinese)

- context before: People think that being late to a meeting or an appointment is impolite.
- **TARGET:** They like to write out schedules very clearly, with what to do at what time all planned.
- context after: If things do not start on time, some people feel unhappy.

## 8c96f996-16-en  (English reference -> back-translate into Chinese)

- context before: Do not immediately judge others as "lazy" or "unprofessional"; perhaps their ways of life are just different.
- **TARGET:** Communicating the schedule in advance and understanding each other's habits are what make better cooperation possible.
- context after: Although punctuality is important, understanding and respecting cultural differences are equally important.

## 8f0524f9-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** People in different places see time differently.
- context after: Some people like to be on time.

## 8f0524f9-2-en  (English reference -> back-translate into Chinese)

- context before: Some people like to be on time.
- **TARGET:** For appointments or classes, they arrive early.
- context after: This is punctuality.

## 8f0524f9-4-en  (English reference -> back-translate into Chinese)

- context before: This is punctuality.
- **TARGET:** Some people take their time.
- context after: Different ideas about time are fine.

## 8f0524f9-5-en  (English reference -> back-translate into Chinese)

- context before: Some people take their time.
- **TARGET:** Different ideas about time are fine.
- context after: Everyone has their own habits.

## 8f0524f9-7-en  (English reference -> back-translate into Chinese)

- context before: Everyone has their own habits.
- **TARGET:** Some people write down a schedule and look at it every day.
- context after: Some people remember things and do not write them down.

## 8f0524f9-8-en  (English reference -> back-translate into Chinese)

- context before: Some people write down a schedule and look at it every day.
- **TARGET:** Some people remember things and do not write them down.
- context after: Now the world is connected.

## 8f0524f9-9-en  (English reference -> back-translate into Chinese)

- context before: Some people remember things and do not write them down.
- **TARGET:** Now the world is connected.
- context after: Globalization lets people from different cultures meet often.

## 8f0524f9-13-en  (English reference -> back-translate into Chinese)

- context before: You are punctual, and I respect you.
- **TARGET:** I take my time, so do not be angry with me.
- context after: This way, everyone is happy.

## 8f12ab21-13-en  (English reference -> back-translate into Chinese)

- context before: This is not because of being sleepy, but may be related to "mirror neurons" in the brain.
- **TARGET:** These neurons are activated when we imitate other people's behavior.
- context after: Psychologists have found that the closer the relationship between people, the more easily they pass yawns to each other.

## 8fd555ea-3-en  (English reference -> back-translate into Chinese)

- context before: City planners have found that buildings with green plants are more popular with people.
- **TARGET:** Because of this, real estate prices sometimes rise.
- context after: People living in the city can buy fresh vegetables more easily, which is also good for food security.

## 99dd6e29-1-en  (English reference -> back-translate into Chinese)

- context before: The evolution of the notation system profoundly reflects the historical course of humanity's understanding of the order of sound.
- **TARGET:** Since ancient times, different civilizations have tried to capture fleeting sounds with visual symbols, but early notation methods were mostly suggestive rather than precise.
- context after: Ancient Greece used letters to mark pitch, Byzantium used symbols to indicate the direction of the melody, and Chinese gongche notation used characters to record relative pitch positions; none of these systems specified rhythmic details, and their performance relied on the tradition of oral transmission.

## 9d6c005f-6-en  (English reference -> back-translate into Chinese)

- context before: The box should be put in the sun.
- **TARGET:** After a few weeks, the things turn black and become smaller.
- context after: This is organic fertilizer.

## 9e260157-9-en  (English reference -> back-translate into Chinese)

- context before: This shows that grassroots environmental protection practice is gradually evolving into an effective path for citizens to participate in social governance.
- **TARGET:** Viewed from an ecological perspective, the project places particular emphasis on the scientific nature of species configuration.
- context after: Abandoning the lesson of past large-scale planting of a single tree species, the team invited forestry experts to give guidance and built a multi-layered vegetation system containing trees, shrubs and herbaceous plants.

## a05ca20a-3-en  (English reference -> back-translate into Chinese)

- context before: Later, composers needed to write their music down so that more people could perform it.
- **TARGET:** So, different notation systems appeared.
- context after: In ancient times, some places used letters to represent pitch, and some used symbols.

## a05ca20a-7-en  (English reference -> back-translate into Chinese)

- context before: With the progress of music theory, notation became more refined.
- **TARGET:** An early form of staff notation appeared in medieval Europe.
- context after: At first there were only two lines, and later it became five lines, which could show the height of notes more clearly.

## a171a56b-2-en  (English reference -> back-translate into Chinese)

- context before: Since ancient times, agricultural communities in arid regions have developed a series of complex resource management systems, which are not only a response to natural constraints but also a deeper embodiment of the fusion of indigenous knowledge and ecological ethics.
- **TARGET:** Such traditional practices are often rooted in long-term environmental observation and intergenerational transmission, and their core lies in maximizing water use efficiency while maintaining the sustainability of the ecosystem.
- context after: For example, in the ancient oasis systems of Central Asia and North Africa, people channel alpine snowmelt water to lowland farmland through carefully designed irrigation networks, such as the qanat.

## a171a56b-7-en  (English reference -> back-translate into Chinese)

- context before: Water distribution is usually decided through collective village consultation and adjusted dynamically according to the season, crop type, and land area, reflecting a highly institutionalized logic of resource management.
- **TARGET:** In some regions, the right to use water is even passed down hereditarily, and its enforcement is supervised by specialized administrators, called "water officials", to ensure fairness and order.
- context after: This social regulation mechanism for water resources is essentially a non-market mode of governance, whose legitimacy derives from the cultural consensus within the community rather than from modern legal provisions.

## a1d5b73e-8-en  (English reference -> back-translate into Chinese)

- context before: Sometimes I am even in a better mood because of it.
- **TARGET:** I bought this T-shirt in a small shop.
- context after: At that time I was just browsing, and I didn't expect to find such a piece of clothing that I loved.

## a1d5b73e-9-en  (English reference -> back-translate into Chinese)

- context before: I bought this T-shirt in a small shop.
- **TARGET:** At that time I was just browsing, and I didn't expect to find such a piece of clothing that I loved.
- context after: The lady who owned the shop said this design was a limited edition and very hard to buy.

## a1d5b73e-15-en  (English reference -> back-translate into Chinese)

- context before: It is just like a good friend of mine, keeping me company.
- **TARGET:** The design on this T-shirt makes me feel happy.
- context after: The way the kitten looks wearing a hat can always make me laugh.

## a35d5c54-1-en  (English reference -> back-translate into Chinese)

- context before: Making compost by yourself is very simple.
- **TARGET:** Put the kitchen scraps in a box.
- context after: Vegetable leaves and fruit peels can all go in.

## a66437c6-13-en  (English reference -> back-translate into Chinese)

- context before: People without a garden can also give it a try.
- **TARGET:** Putting a small bin on the balcony is enough.
- context after: Making compost is not hard.
