# Recheck pack 08 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/back/08.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_08.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/verdicts/08.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/packs/recheck_08.gold.md`. Do not open it yet.


## e29bfa25-3-en  (English reference -> back-translate into Chinese)

- context before: The slope is very high.
- **TARGET:** When he lets go of the toy car, the toy car starts to roll.
- context after: It rolls very fast, and its speed gets faster and faster.

## e3d2be8e-7-en  (English reference -> back-translate into Chinese)

- context before: Every village and every country has its own way of narrative.
- **TARGET:** In some places they beat drums to tell stories, and in other places they dance to tell stories.
- context after: Stories can teach people to do what is right, and can also make people happy.

## e52f9e8d-3-en  (English reference -> back-translate into Chinese)

- context before: This spreading was very important for the Reformation.
- **TARGET:** The Reformation changed religion in Europe a great deal.
- context after: Printing let more people know about new religious ideas.

## ea4150b1-13-en  (English reference -> back-translate into Chinese)

- context before: Schools became more and more numerous, and people began to study science, history and medicine.
- **TARGET:** Although not everyone could read right away, the number of literate people slowly grew.
- context after: Bookstores and libraries appeared in cities.

## ea4150b1-17-en  (English reference -> back-translate into Chinese)

- context before: Gutenberg's printing press changed the world.
- **TARGET:** It made information easier for ordinary people to obtain.
- context after: Although we now have computers and mobile phones, books are still an important way to learn knowledge.

## eb41dd33-7-en  (English reference -> back-translate into Chinese)

- context before: Motors are like the robotic arm's "muscles"; they can make each part of the robotic arm turn.
- **TARGET:** Usually, we use servo motors, because they can precisely control the angle of rotation, which is very useful for grabbing small objects.
- context after: Next is the "hand".

## eb41dd33-9-en  (English reference -> back-translate into Chinese)

- context before: Next is the "hand".
- **TARGET:** This "hand" needs to be able to open and close so that it can grab objects.
- context after: We can design a simple clamp that uses two small arms to clamp objects.

## eb41dd33-14-en  (English reference -> back-translate into Chinese)

- context before: This "brain" is our programming part.
- **TARGET:** We can use a microcontroller, such as an Arduino or a Raspberry Pi.
- context after: You need to learn some basic programming languages, such as C++ or Python, to write the control code.

## eb41dd33-18-en  (English reference -> back-translate into Chinese)

- context before: The electronics part is also very important.
- **TARGET:** You need to connect the motors and the microcontroller, plus sensors if needed, for example to detect whether an object has been grabbed.
- context after: This requires some wires, batteries or a power adapter, and possibly some circuit boards.

## ecff6c81-4-en  (English reference -> back-translate into Chinese)

- context before: Although these things did not really happen, people like to tell them.
- **TARGET:** Narrative is not only for entertainment, but can also teach people how to be a good person.
- context after: In some places, elders sit by the fire at night and tell stories to the children.

## ecff6c81-13-en  (English reference -> back-translate into Chinese)

- context before: Listeners can also express their own views through questions and discussion.
- **TARGET:** In this way, everyone shares not only the stories, but also feelings and experiences.
- context after: Nowadays, although many people watch stories through television and mobile phones, there are still quite a few places that insist on telling them orally.

## f6fb78c3-2-en  (English reference -> back-translate into Chinese)

- context before: Between the tall buildings there are some small gardens.
- **TARGET:** Gardens make houses look nicer.
- context after: Many people want to buy nice-looking houses.

## f6fb78c3-3-en  (English reference -> back-translate into Chinese)

- context before: Gardens make houses look nicer.
- **TARGET:** Many people want to buy nice-looking houses.
- context after: When many people want to buy, houses become more expensive.

## f6fb78c3-5-en  (English reference -> back-translate into Chinese)

- context before: When many people want to buy, houses become more expensive.
- **TARGET:** With expensive houses, the owners can earn more money.
- context after: There are very few places to grow vegetables in the city.

## f871bc87-6-en  (English reference -> back-translate into Chinese)

- context before: This teddy bear is my good friend.
- **TARGET:** Every night, I hold it in my arms and sleep.
- context after: Its eyes are black, its nose is brown, and it always looks smiling, as if it is very happy to see me.

## f871bc87-16-en  (English reference -> back-translate into Chinese)

- context before: This bear is not just a toy; it also holds many of my memories.
- **TARGET:** When I am sad, I hold it and feel that it brings me comfort.
- context after: When I am happy, I also share my happiness with it.

## f871bc87-29-en  (English reference -> back-translate into Chinese)

- context before: It is an indispensable part of my childhood, and also a warm mark in my future memories.
- **TARGET:** Every time I see it, I feel a sense of security and happiness.
- context after: This bear is my little, fluffy, blue-sweater-wearing, one-of-a-kind friend.

## ffc9003e-12-en  (English reference -> back-translate into Chinese)

- context before: Yawning is not because of laziness; it is because the body needs it.
- **TARGET:** We should listen to our bodies.
- context after: When sleepy, yawn, and then go to sleep.
