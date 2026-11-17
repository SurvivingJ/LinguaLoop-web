# Recheck pack 02 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/back/02.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_02.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/verdicts/02.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/packs/recheck_02.gold.md`. Do not open it yet.


## 4d9a6e14-6-en  (English reference -> back-translate into Chinese)

- context before: The venue is decorated brilliantly with lights, and the long tables are piled with fruit and drinks.
- **TARGET:** The prize draw is undoubtedly the part that stirs people the most; from practical electronic products to valuable travel vouchers, the prizes are revealed one after another, and cheers burst out from the audience from time to time.
- context after: In sharp contrast to the excitement of the prize draw are the carefully rehearsed performances of the various departments: some people sing, some dance, and some adapt funny incidents from the office into skits, making everyone laugh until their sides ache.

## 4e4f6f61-7-en  (English reference -> back-translate into Chinese)

- context before: Parents not only bear the responsibility of supervising study, but also have to play the roles of recorder, coordinator, and even teaching assistant.
- **TARGET:** After a long time like this, the patience between parents and children is worn down, and the parents' own rest and emotions are also affected.
- context after: Home-school communication needs clearer boundaries, so that teachers, parents, and students can all take part within a reasonable range.

## 5006cdb0-1-en  (English reference -> back-translate into Chinese)

- context before: Every Spring Festival travel season, passenger flows on the national railways, highways and airlines surge sharply within a short time, putting enormous pressure on the transport authorities.
- **TARGET:** To make good arrangements for transport capacity in advance, scientific forecasting is indispensable.
- context after: Time series analysis is precisely a commonly used method for this: it takes historical passenger flow data recorded in chronological order as its object of study and extracts the underlying patterns from it.

## 5008130d-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** Squeezed between chain convenience stores and large supermarkets, the neighborhood shop can still take root, relying not on scale but on the web of personal relationships deeply embedded in the community.
- context after: Convenience stores excel at standardized goods and convenient service, and large supermarkets attract customers with a rich variety and price advantages, but neighborhood shops often run regular-customer relationships that are hard to quantify or replace.

## 5008130d-2-en  (English reference -> back-translate into Chinese)

- context before: Convenience stores excel at standardized goods and convenient service, and large supermarkets attract customers with a rich variety and price advantages, but neighborhood shops often run regular-customer relationships that are hard to quantify or replace.
- **TARGET:** The shop owner remembers residents' tastes, family circumstances and spending habits, and can offer flexibility in small details such as buying on credit, delivery and emergency help.
- context after: Especially for the elderly, students and busy office workers, the convenience of being reachable just by going downstairs and buying whenever you arrive is often more attractive than the "cheaper" of a grand shopping mall.

## 5019fe56-6-en  (English reference -> back-translate into Chinese)

- context before: So some people call those who live long-term carrying a loan "house slaves".
- **TARGET:** This label is not just a joke; it reminds people that a house can indeed bring a sense of security, but it may also squeeze the room for choices for many years to come.
- context after: Before buying a home, besides comparing interest rates and monthly installments, one should even more seriously assess one's own capacity to bear the burden, so as to avoid being deluded by a superficial feeling of ownership.

## 532d43c7-2-en  (English reference -> back-translate into Chinese)

- context before: A so-called school-district home refers to a residence zoned in the same district as a good designated school.
- **TARGET:** Parents believe that as long as they buy here, their child will be able to enroll smoothly and avoid the cruel competition of choosing a school.
- context after: So a thought-provoking scene appears in the trading market: the smaller and older the apartment, the higher the unit price instead.

## 532d43c7-5-en  (English reference -> back-translate into Chinese)

- context before: Many families spend all their savings, and even sell their spacious new homes, just to exchange them for an old place of a few dozen square meters, and they must also go to great trouble to move their household registration in.
- **TARGET:** For a single school place, the household registrations of several families may be crammed into the same apartment.
- context after: However, this anxiety is being slowly diluted by policy.

## 5a0843fc-4-en  (English reference -> back-translate into Chinese)

- context before: So I used this as an entry point to start bargaining, with a polite tone but a clear stance: I could come in person to pick it up that same day, saving the logistics fee and packaging costs, and I hoped the other party would take off 200 yuan.
- **TARGET:** The seller hesitated for a moment, and in the end agreed to lower the price by 150 yuan, and they arranged to hand it over at the entrance of the residential compound the next afternoon.
- context after: When we met, I carefully checked the condition and structure of the tabletop, and after confirming there were no cracks or woodworm, I transferred the money on the spot, then called a small van to carry the table home.

## 5a27ec54-1-en  (English reference -> back-translate into Chinese)

- context before: In the early morning, I set out from the city's long-distance bus station and took a long-distance bus back to my old home in the countryside.
- **TARGET:** The bus station was noisy with voices, the electronic screens kept announcing delays, and I clutched my ticket, afraid of missing this bus home.
- context after: After the bus drove out of the urban area, the buildings outside the window gradually became sparse, and fields and rivers unfolded one after another.

## 5a27ec54-4-en  (English reference -> back-translate into Chinese)

- context before: In order to get home before evening, I deliberately bought the earliest bus.
- **TARGET:** Along the way I also had to change buses in a small town, because there was only one direct bus to my old home each day.
- context after: When changing buses, I dragged my luggage through the crowded platform, with both weariness and anticipation in my heart.

## 5b71c55e-2-en  (English reference -> back-translate into Chinese)

- context before: On the other end of the screen, her mother, wearing an apron and holding a spatula in her hand, was about to teach her, step by step, the home-style dish she had eaten since childhood: tomato and egg stir-fry.
- **TARGET:** This dish seems simple, but actually hides some tricks.
- context after: Her mother stressed repeatedly that the heat is the key to success or failure: if the oil is too hot, the beaten egg will scorch in an instant; if the temperature is not enough, the egg will have difficulty becoming fluffy.

## 5b71c55e-3-en  (English reference -> back-translate into Chinese)

- context before: This dish seems simple, but actually hides some tricks.
- **TARGET:** Her mother stressed repeatedly that the heat is the key to success or failure: if the oil is too hot, the beaten egg will scorch in an instant; if the temperature is not enough, the egg will have difficulty becoming fluffy.
- context after: Lin Yue adjusted the heat as told, and only after seeing the edges of the beaten egg bubble slightly did she slowly push in the cut tomatoes.

## 5b71c55e-4-en  (English reference -> back-translate into Chinese)

- context before: Her mother stressed repeatedly that the heat is the key to success or failure: if the oil is too hot, the beaten egg will scorch in an instant; if the temperature is not enough, the egg will have difficulty becoming fluffy.
- **TARGET:** Lin Yue adjusted the heat as told, and only after seeing the edges of the beaten egg bubble slightly did she slowly push in the cut tomatoes.
- context after: As for seasoning, her mother only let her add a small pinch of sugar.

## 5b71c55e-7-en  (English reference -> back-translate into Chinese)

- context before: This seemingly superfluous act precisely neutralizes the sourness and astringency of the tomato, letting the savory flavor deepen layer by layer.
- **TARGET:** When the sweet and sour aroma spilled out of the screen, Lin Yue suddenly understood that the so-called taste of home has never been one particular recipe, but someone being willing, across a screen, to hand you the small details of proportion bit by bit.

## 5ca07cbc-2-en  (English reference -> back-translate into Chinese)

- context before: The groom's parents spoke first: the apartment had already been picked out, not far from the subway station, the down payment would be borne by them, and the remaining mortgage would be left to the young couple to pay off slowly themselves.
- **TARGET:** The bride's mother did not state a position right away, and only asked one thing: will our daughter's name be written on the property certificate?
- context after: The groom's father thought for a moment and said that writing both their names would be reassuring.

## 5e57f38d-3-en  (English reference -> back-translate into Chinese)

- context before: The parents' generation generally started families in their twenties and are used to regarding marriage as a necessary road in life, so they find it hard to understand why their children are so slow to settle down, and some elders even use a derogatory label like "leftover women" to describe unmarried women around thirty.
- **TARGET:** The children, however, often feel wronged: they are not refusing intimate relationships, but under the pressure of housing prices and career prospects, they want to keep the power of choice in their own hands.
- context after: So the festive atmosphere is mixed with silence and quarrels, and the "generation gap" between the two generations is fully revealed in a few questions.

## 67383c89-3-en  (English reference -> back-translate into Chinese)

- context before: If you want to compare the differences between categories, such as the quarterly sales of each department, a bar chart is the most intuitive, because the human eye is especially sensitive to differences in the height of bars.
- **TARGET:** If you want to present the trend of data changing over time, such as a city's temperature fluctuations over a year, a line chart is more suitable, and a continuous line can clearly show the direction of rises and falls.
- context after: As for the pie chart, it is suited to showing the proportion each part makes up of the whole, but once there are more than five or six categories, the slices will look crowded and readers will find it hard to tell them apart.

## 67504544-2-en  (English reference -> back-translate into Chinese)

- context before: Every day at noon, two completely different choices always appear in the office: one group of people pour into the company canteen, seeking convenience and liveliness; the other group insist on bringing their own meals, using the time left over from the night before to buy themselves some calm.
- **TARGET:** Looking at cost-effectiveness alone, the canteen seems to have the advantage: no shopping, no cooking, a meal settled by swiping a card, with the time cost compressed to the minimum.
- context after: However, people who rely on the canteen for a long time often complain that the flavours are monotonous and the food too oily and salty, and health risks accumulate without their noticing.

## 67504544-4-en  (English reference -> back-translate into Chinese)

- context before: However, people who rely on the canteen for a long time often complain that the flavours are monotonous and the food too oily and salty, and health risks accumulate without their noticing.
- **TARGET:** By contrast, the packed-lunch crowd can independently control the source and proportions of their ingredients, with little oil and salt and a balance of meat and vegetables, which both looks after the stomach and saves a considerable amount of expense each month.
- context after: Of course, bringing food is not without cost; the toil of getting up early to prepare a meal and the queuing in front of the microwave are both realities that must be accepted.

## 67809741-5-en  (English reference -> back-translate into Chinese)

- context before: The so-called inflection point refers to the turning moment when new cases change from rising continuously to falling continuously.
- **TARGET:** Its appearance often means that the prevention and control measures are beginning to show results, but it does not mean the risk has been eliminated.
- context after: If controls are relaxed too early, the reproduction number may rebound again, causing the earlier efforts to be wasted at the last step.

## 68799007-5-en  (English reference -> back-translate into Chinese)

- context before: What deserves vigilance is that when appearance is simplified into a set of quantifiable indicators, a person's worth is compressed along with it.
- **TARGET:** True confidence does not come from endlessly approaching the filter, but stems from accepting one's own uniqueness: acknowledging that one has imperfections, yet still being willing to face the camera calmly.

## 69a08a4a-6-en  (English reference -> back-translate into Chinese)

- context before: These rules seem tedious, but in fact they all express respect and consideration.
- **TARGET:** Only when I act accordingly do I feel at ease.
