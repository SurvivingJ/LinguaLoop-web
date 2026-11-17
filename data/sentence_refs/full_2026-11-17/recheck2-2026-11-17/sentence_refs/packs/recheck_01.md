# Recheck pack 01 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/back/01.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_01.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/verdicts/01.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/packs/recheck_01.gold.md`. Do not open it yet.


## 103821c5-6-en  (English reference -> back-translate into Chinese)

- context before: If you encounter improper charges, deliberate detours or other inappropriate behavior, passengers must not swallow their anger, but should keep evidence such as recordings and screenshots, promptly file a complaint with the platform, and call the police when the situation is serious.
- **TARGET:** Only when the platform, the regulators and the passengers all make joint efforts can the line of defense for travel safety truly be built up.

## 21e244ae-1-en  (English reference -> back-translate into Chinese)

- context before: When a group meal breaks up, the bill is often more likely than the food to make people feel awkward.
- **TARGET:** Some people are used to rushing to treat everyone, seeing paying the bill as a way of expressing friendship; others advocate splitting the bill equally, believing that everyone paying for themselves is cleaner and more comfortable.
- context after: The former fear losing face, and the latter fear owing a favor; these two states of mind silently pull against each other at the cashier's counter.

## 21e244ae-4-en  (English reference -> back-translate into Chinese)

- context before: Nowadays WeChat Pay has given this difficulty a compromise: one person pays first, then starts a group payment request in the chat group, the system automatically calculates each person's share, and participants only need to tap to confirm, and the money quietly arrives.
- **TARGET:** The whole process requires no talking about money and no repeated polite refusals, which both preserves the dignity of the host and spares the guests any psychological burden.
- context after: Of course, technology can only resolve awkwardness in form, and the real sense of propriety still depends on the relationship between the people involved: with a close friend of many years, it is not worth worrying about who pays a little more; with someone you have just met, clear accounts are instead a form of respect.

## 21e244ae-5-en  (English reference -> back-translate into Chinese)

- context before: The whole process requires no talking about money and no repeated polite refusals, which both preserves the dignity of the host and spares the guests any psychological burden.
- **TARGET:** Of course, technology can only resolve awkwardness in form, and the real sense of propriety still depends on the relationship between the people involved: with a close friend of many years, it is not worth worrying about who pays a little more; with someone you have just met, clear accounts are instead a form of respect.

## 2335d747-1-en  (English reference -> back-translate into Chinese)

- context before: In the third week of my mother's hospital stay, I have almost figured out the routine of that ward: in the early morning the nurse comes to take her temperature, in the afternoon the sunlight crawls aslant up onto the bedside cabinet, and the evening is the hardest time of the day to get through.
- **TARGET:** Caring for a patient is not merely keeping watch; it is more like a long test of endurance: the folding bed is too narrow, the coughing at night is too frequent, and during the day I also have to deal with work and bills.
- context after: Relatives and friends who visit bring fruit and comforting words, saying things like "you'll be out of the hospital soon"; I accept them with a smile, but in my heart I know very well that recovery is never a straight line.

## 23e15ac8-6-en  (English reference -> back-translate into Chinese)

- context before: And at a deeper level, young people's fondness for Hanfu is in fact a conscious expression of cultural identity.
- **TARGET:** Through the sense of ritual in every stitch, they reconfirm where they come from.

## 250e8e7d-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** In recent years, a fitness craze has swept through urban white-collar workers.
- context after: After work, more and more young people are no longer content to stay at home, but walk into the gym and use sweat to fight the fatigue brought on by sitting for long periods.

## 2ff88667-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** Last autumn, I began renovating the old apartment I had lived in for twenty years.
- context after: The old house had aging pipes and peeling wall plaster, and I had originally thought that as long as I said hello to the neighbors in advance, we could get along without trouble.

## 2ff88667-2-en  (English reference -> back-translate into Chinese)

- context before: The old house had aging pipes and peeling wall plaster, and I had originally thought that as long as I said hello to the neighbors in advance, we could get along without trouble.
- **TARGET:** But things were far more difficult than I had imagined.
- context after: Downstairs lived a young couple who had just had a baby, the baby needed to sleep three hours during the day, and the noise from smashing walls and drilling happened to be concentrated in the morning.

## 2ff88667-5-en  (English reference -> back-translate into Chinese)

- context before: At first they only came to my door to remind me tactfully, but later, seeing the construction hours extended again and again, they complained directly to the property management.
- **TARGET:** For a while I felt wronged, thinking that renovation simply could not be done without noise.
- context after: But when I saw that mother pacing back and forth in the stairwell holding her crying child, my heart still softened.

## 345a7b83-2-en  (English reference -> back-translate into Chinese)

- context before: Top streamers are not in a hurry to list product specifications, but first create a sense of scarcity: the stock number on the screen drops rapidly, the flash-sale link opens for only thirty seconds, and the countdown and the assistant host's loud reminders are interwoven, so viewers have no time at all to think.
- **TARGET:** The spend-and-save rules are then repeatedly broken down into formulas that are easy to calculate in one's head, such as "50 off for every 300 spent", and once the amount is reached, not buying instead feels like a loss.
- context after: More subtle is the control of time: the best-value bundles are often scheduled to be launched late at night, when people's rational judgment is at its weakest, and impulse buying naturally happens.

## 3d9e9d38-6-en  (English reference -> back-translate into Chinese)

- context before: Yet after waiting nearly two weeks, the refund still had not arrived, and customer service's reply was always "under verification".
- **TARGET:** She finally gave a bad review, describing the whole course of the negotiation in detail in the review.
- context after: She frankly said that she did not mind about those few hundred yuan, and that what was truly disappointing was that rules in black and white were interpreted arbitrarily, and consumers' trust was also used up through one instance after another of passing the buck.

## 3f715450-3-en  (English reference -> back-translate into Chinese)

- context before: Numbers whose source is unclear or cannot be verified, even if they look precise, are hard to find convincing.
- **TARGET:** Second, one should note whether the definitions are consistent.
- context after: For example, even for the same "unemployment rate," some count only registered unemployed people, while others also include people who have voluntarily given up looking for work; with different definitions, the results naturally differ greatly, and if the two are compared directly, one will inevitably reach a misleading judgment.

## 3f715450-4-en  (English reference -> back-translate into Chinese)

- context before: Second, one should note whether the definitions are consistent.
- **TARGET:** For example, even for the same "unemployment rate," some count only registered unemployed people, while others also include people who have voluntarily given up looking for work; with different definitions, the results naturally differ greatly, and if the two are compared directly, one will inevitably reach a misleading judgment.
- context after: Third is sample size and sampling method.

## 3f715450-5-en  (English reference -> back-translate into Chinese)

- context before: For example, even for the same "unemployment rate," some count only registered unemployed people, while others also include people who have voluntarily given up looking for work; with different definitions, the results naturally differ greatly, and if the two are compared directly, one will inevitably reach a misleading judgment.
- **TARGET:** Third is sample size and sampling method.
- context after: Surveying only a few dozen people and then asserting that "most consumers are satisfied" is obviously taking a part for the whole; even if the sample size is large, if the subjects are concentrated in a certain age group, the conclusion is still biased.

## 3f715450-8-en  (English reference -> back-translate into Chinese)

- context before: Finally, one should also look at whether the report explains the survey method, the margin of error and the funding organization.
- **TARGET:** Only by weighing these aspects repeatedly will one not be led around by the nose by pretty numbers.

## 40f40f59-5-en  (English reference -> back-translate into Chinese)

- context before: Faced with massive records scattered across different systems, she writes query statements, extracts the required fields one by one, and removes duplicate and abnormal data.
- **TARGET:** The morning is almost entirely spent on this step, but she knows well that if the foundation is not solid, even the most beautiful charts are nothing but castles in the air.
- context after: In the afternoon, she moves on to the analysis stage, looking for the patterns hidden behind the numbers by comparing the behavioral differences between different user groups.

## 410d39b5-3-en  (English reference -> back-translate into Chinese)

- context before: For many of the "post-80s" and "post-90s", they grew up in an environment of enjoying all of their parents' love alone, and now have to learn to share toys, time and attention with younger brothers and sisters.
- **TARGET:** This change is not always easy.
- context after: When parents raise several children, it is inevitable that, because their energy is limited, they favour some more than others, and the older child often feels a certain degree of "favouritism", with disappointment and grievance rising in the heart.

## 410d39b5-4-en  (English reference -> back-translate into Chinese)

- context before: This change is not always easy.
- **TARGET:** When parents raise several children, it is inevitable that, because their energy is limited, they favour some more than others, and the older child often feels a certain degree of "favouritism", with disappointment and grievance rising in the heart.
- context after: However, sibling affection also quietly grows amid friction.

## 4328c306-2-en  (English reference -> back-translate into Chinese)

- context before: Although the collision was light, both parties still immediately turned on their hazard warning lights and placed warning triangles behind their cars to prevent a secondary accident.
- **TARGET:** After getting out, the drivers first checked whether anyone was injured, and then used their phones to photograph the positions of the vehicles, the points of impact and the road markings.
- context after: If the vehicles can move and no one is injured, both parties should move their cars as soon as possible to a place that does not obstruct traffic, to avoid causing congestion.

## 44d5ccb8-3-en  (English reference -> back-translate into Chinese)

- context before: Many elderly people's retirement money, saved over a lifetime, is transferred away in just a few minutes like this, leaving them with bitter regret.
- **TARGET:** In fact, any call from a stranger that demands secrecy, urges a transfer, or asks for a verification code is almost without exception a trap.
- context after: If children accompany and communicate with them more in daily life, and communities regularly hold anti-fraud talks, both can fill the gaps in the elderly's information to a great extent.

## 4d9a6e14-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** As the end of the year approaches, the atmosphere inside the company quietly changes.
- context after: What employees talk about most is none other than the amount of the year-end bonus.

## 4d9a6e14-5-en  (English reference -> back-translate into Chinese)

- context before: The annual party is usually scheduled for the weekend after pay is issued.
- **TARGET:** The venue is decorated brilliantly with lights, and the long tables are piled with fruit and drinks.
- context after: The prize draw is undoubtedly the part that stirs people the most; from practical electronic products to valuable travel vouchers, the prizes are revealed one after another, and cheers burst out from the audience from time to time.
