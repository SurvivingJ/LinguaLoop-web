# Recheck pack 07 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/back/07.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_07.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/verdicts/07.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/packs/recheck_07.gold.md`. Do not open it yet.


## a66437c6-16-en  (English reference -> back-translate into Chinese)

- context before: You can do it together with your family.
- **TARGET:** It is both fun and useful.

## a8c1c97b-2-en  (English reference -> back-translate into Chinese)

- context before: Computers need to learn many examples in order to do their work well.
- **TARGET:** These examples come from users.
- context after: The company must tell users: "We are using your data to help the computer learn."

## a8c1c97b-8-en  (English reference -> back-translate into Chinese)

- context before: Users have the right to know these things.
- **TARGET:** The company must write clear words and put them online.
- context after: Everyone can see them.

## a8c1c97b-9-en  (English reference -> back-translate into Chinese)

- context before: The company must write clear words and put them online.
- **TARGET:** Everyone can see them.
- context after: Only in this way will everyone trust this company.

## abf6c4ba-5-en  (English reference -> back-translate into Chinese)

- context before: If users do not understand the explanation, they cannot make the right choice.
- **TARGET:** Therefore, the wording must be simple and clear, avoiding words that are too technical.
- context after: In addition, how algorithms work should also have a certain degree of transparency.

## acf330bf-9-en  (English reference -> back-translate into Chinese)

- context before: The fabric of this T-shirt is also very soft, and it is comfortable to wear.
- **TARGET:** I often wear it on weekends, or when I go out to play with friends.
- context after: This T-shirt is a gift my mother gave me when it was my birthday.

## acf330bf-13-en  (English reference -> back-translate into Chinese)

- context before: I wash it carefully and put it away carefully, hoping it can be worn for a long time.
- **TARGET:** I think I will continue to like this T-shirt for a long time.
- context after: It is not just a piece of clothing, but even more a small happiness in my life.

## ade8e587-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** In very dry places, people have old methods of using water.
- context after: They use stones to build small channels, and rainwater flows into the fields.

## ade8e587-2-en  (English reference -> back-translate into Chinese)

- context before: They use stones to build small channels, and rainwater flows into the fields.
- **TARGET:** The fields are in low places, so the water does not run away.
- context after: In this way, the soil does not dry out, and vegetables and grain can be grown.

## ade8e587-8-en  (English reference -> back-translate into Chinese)

- context before: These practices are cultural heritage.
- **TARGET:** They help agriculture.
- context after: This is indigenous knowledge, and also a good example of resource management.

## afba2d39-8-en  (English reference -> back-translate into Chinese)

- context before: Children need to help the family do some simple housework, such as sweeping the courtyard or going to the market to buy things.
- **TARGET:** Even small children need to contribute their strength to the family.
- context after: Ancient Roman children also had time to play.

## b4c8cc94-2-en  (English reference -> back-translate into Chinese)

- context before: They like to fly to flowers.
- **TARGET:** Bees collect nectar from flowers, and pollen sticks to their bodies.
- context after: When it flies to another flower, the pollen falls off.

## baa11e11-6-en  (English reference -> back-translate into Chinese)

- context before: This can help solve the problem of food security.
- **TARGET:** The places where vegetables are grown also look very nice.
- context after: In places with green plants, the air is cleaner.

## baa11e11-14-en  (English reference -> back-translate into Chinese)

- context before: This is part of urban planning.
- **TARGET:** Doing this well is good for the future.
- context after: This is sustainability.

## c046897b-6-en  (English reference -> back-translate into Chinese)

- context before: For example, some communities collect rainwater during the rainy season and store it in underground cisterns.
- **TARGET:** When the drought comes, they then use this water to irrigate the farmland.
- context after: They also know which crops are drought-resistant, such as sorghum and millet.

## c2d263d5-16-en  (English reference -> back-translate into Chinese)

- context before: More thought-provoking is that some potent antipsychotic drugs, because they affect dopamine pathways, often have "pathological yawning" as a side effect, reaching dozens of times a day, which in turn provides a clinical window for studying its neural mechanisms.
- **TARGET:** In summary, yawning is far from a meaningless physiological reflex, but a multifunctional behavior that integrates temperature regulation, neural synchronization, and social communication.
- context after: It is both an outward manifestation of the brain's inner state and a way for humans to engage in emotional resonance unconsciously.

## c5e2e48b-6-en  (English reference -> back-translate into Chinese)

- context before: A bus can carry many people.
- **TARGET:** When many people take the bus, each person's carbon footprint is small.
- context after: When the carbon footprint is small, the earth is cleaner.

## c5e2e48b-9-en  (English reference -> back-translate into Chinese)

- context before: City planning makes bus routes convenient.
- **TARGET:** Everyone commuting by bus is a good environmentally friendly habit.

## cc7b0bb0-4-en  (English reference -> back-translate into Chinese)

- context before: This non-textual expression of history is embodied, in many indigenous societies, in cosmological narratives of the "Dreamtime" type, in which the actions of ancestors and the formation of natural landforms mirror each other, and time does not advance linearly, but restarts cyclically with mythic events as its nodes.
- **TARGET:** Within such a framework, telling a folktale is not merely recounting past events, but performing a cultural practice: the speaker activates sacred time and space through language, while the listener, in immersion, gains a reaffirmation of identity.
- context after: Narrative thus becomes an existence of the "kotodama" kind: language does not merely describe the world, but constructs reality.

## cc7b0bb0-8-en  (English reference -> back-translate into Chinese)

- context before: Unlike the fixity of written texts, each telling is a re-creation of the tradition, and the teller adds, deletes or reconstructs the plot according to the present context, the composition of the audience and social needs.
- **TARGET:** This mechanism of "persistence amid variation" allows the cultural core to maintain spiritual continuity through changes in form.
- context after: For example, in some tribes in Africa, the same hero legend is told in wartime with an emphasis on courage and sacrifice, and at harvest time highlights harmonious coexistence with nature; history thus becomes a resource of meaning that can be drawn upon, rather than a rigid archive of facts.

## cc7b0bb0-10-en  (English reference -> back-translate into Chinese)

- context before: For example, in some tribes in Africa, the same hero legend is told in wartime with an emphasis on courage and sacrifice, and at harvest time highlights harmonious coexistence with nature; history thus becomes a resource of meaning that can be drawn upon, rather than a rigid archive of facts.
- **TARGET:** In the contemporary era of globalization and digitization, although written records and visual media dominate the spread of information, oral narrative has not died out, but has returned in new forms: podcasts, oral history projects and movements to protect intangible cultural heritage can all be regarded as modern echoes of the original mode of communication.
- context after: These practices reaffirm the cognitive depth contained in bodily presence, vocal texture and improvised interaction; they cannot be fully translated into text or data.

## d4dcbfdf-2-en  (English reference -> back-translate into Chinese)

- context before: Before woodblock printing and movable-type technology appeared one after another, the preservation and spread of knowledge relied extremely heavily on handwritten copies, a process that was not only time-consuming and laborious but also prone to errors, causing books to become luxuries that only a small elite class could access.
- **TARGET:** As early as the Tang dynasty, China had already widely used woodblock printing, and in the Song dynasty Bi Sheng even first invented clay movable type, opening the precedent for reusable typesetting technology.
- context after: However, limited by the huge number of Chinese characters, the complexity of typesetting, and the constraints of social structure, this technology failed to trigger a large-scale wave of popularization of knowledge.

## d873cb80-12-en  (English reference -> back-translate into Chinese)

- context before: As time goes by, their language ability will also improve.
- **TARGET:** Although they have never met, in the virtual world they have become good partners.
- context after: Sometimes, the game is over and they are still chatting, sharing things from their lives.

## e0bac436-4-en  (English reference -> back-translate into Chinese)

- context before: The air above the wing flows fast, and the air below flows slowly.
- **TARGET:** This produces an upward force, which we call "lift."
- context after: Lift makes the airplane leave the ground and fly up into the sky.

## e0bac436-8-en  (English reference -> back-translate into Chinese)

- context before: This force that blocks the airplane is called "drag."
- **TARGET:** Drag makes the airplane slow down.
- context after: So the shape of the airplane must be made smooth, so that the air can flow past smoothly and drag is reduced.
