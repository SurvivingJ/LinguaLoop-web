# Recheck pack 04 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/back/04.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_04.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/verdicts/04.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/packs/recheck_04.gold.md`. Do not open it yet.


## c1a2b59c-4-en  (English reference -> back-translate into Chinese)

- context before: Linguists point out that dialects carry unique vocabulary, intonation and local memory, and once the younger generation no longer speaks, many ways of expression disappear with it, and disappearance is often irreversible.
- **TARGET:** It is gratifying that in recent years some places have brought dialect nursery rhymes and local opera into schools, letting children come into contact with their native dialect again through games and chanting.
- context after: Protecting dialects does not mean opposing Mandarin; the two can perfectly well coexist: Mandarin broadens children's horizons, while dialect maintains their emotional ties with their homeland.

## c2e405c4-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** In the job market, age discrimination often appears in hidden forms.
- context after: Many positions superficially emphasize experience and stability, but in fact treat the "age-35 threshold" as a screening criterion.

## caf8cc2b-5-en  (English reference -> back-translate into Chinese)

- context before: They are willing to trade uncertainty for possibility, and high-intensity effort for faster returns.
- **TARGET:** In fact, there is no better or worse between stability and risk-taking.
- context after: What really needs to be asked is: what you want, is it a security you can rely on, or a way of life that lets you prove yourself?

## ccbad16e-2-en  (English reference -> back-translate into Chinese)

- context before: Suppose a hospital treats five hundred patients each with two therapies, A and B.
- **TARGET:** In the mild group, A's cure rate is 90% and B's is 85%; in the severe group, A's is 60% and B's is 50%.
- context after: So it can be seen that in either group, A is more effective.

## d3bb927b-5-en  (English reference -> back-translate into Chinese)

- context before: Slowly, he discovered that the street-stall economy is not just "small business", but the starting point for many people's ventures.
- **TARGET:** While keeping accounts, Xiao Lin studied customers' tastes, and also learned to use social media to announce his stall hours.
- context after: On weekends, he prepares the ingredients in advance so that customers do not have to wait too long.

## d4a82433-6-en  (English reference -> back-translate into Chinese)

- context before: However, a data lake lacking effective governance easily degenerates into a chaotic "data swamp".
- **TARGET:** Therefore, many companies simply use the two in combination, each taking its own strengths.

## d669a66d-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** Arranging to have hotpot with a few good friends on the weekend should have been something to look forward to, but once everyone's spice tolerance was laid on the table, the atmosphere turned subtle.
- context after: Some people cannot do without spice and claim that only the numbing, spicy kick that shoots straight up the nose counts as true flavour; others break out in a sweat on their foreheads at the mere smell of Sichuan pepper and only dare to order mild spice.

## d669a66d-3-en  (English reference -> back-translate into Chinese)

- context before: Fortunately, the restaurant brought out a yin-yang pot, with one half of red broth bubbling and the other half of clear broth calm, and the two completely different expectations each found their place.
- **TARGET:** The choices at the dipping-sauce counter are equally intriguing: those who love spice scoop on chilli and minced garlic layer upon layer, as if afraid the flavour would not be enough; those who prefer mild food add only a little sesame oil and spring onion, striving to preserve the original taste of the ingredients.
- context after: At the table there was the occasional good-natured teasing, saying that differences in taste have nothing to do with superiority, and are merely a matter of different taste-bud memories.

## d669a66d-4-en  (English reference -> back-translate into Chinese)

- context before: The choices at the dipping-sauce counter are equally intriguing: those who love spice scoop on chilli and minced garlic layer upon layer, as if afraid the flavour would not be enough; those who prefer mild food add only a little sesame oil and spring onion, striving to preserve the original taste of the ingredients.
- **TARGET:** At the table there was the occasional good-natured teasing, saying that differences in taste have nothing to do with superiority, and are merely a matter of different taste-bud memories.
- context after: Over the course of the meal, the broth in the pot simmered ever richer, and the people chatted ever closer.

## d669a66d-6-en  (English reference -> back-translate into Chinese)

- context before: Over the course of the meal, the broth in the pot simmered ever richer, and the people chatted ever closer.
- **TARGET:** What is called compatibility perhaps lies not in having completely identical tastes, but in being willing to leave room for half a pot of clear broth for each other.

## da2d90d6-1-en  (English reference -> back-translate into Chinese)

- context before: In recent years, the pace of life of city people has become ever tighter, and weekend nearby trips have quietly become a popular way of life.
- **TARGET:** Compared with being jostled by crowds at famous attractions, more and more people prefer to drive themselves to small towns two or three hours away by car, slowing their steps down.
- context after: During the short holiday, the traffic on the highways is an unbroken stream, while real enjoyment is often hidden on those nameless country lanes.

## dd22fa2e-5-en  (English reference -> back-translate into Chinese)

- context before: Once the line is determined, simply by entering the area of a new house one can roughly predict its reasonable price.
- **TARGET:** However, price is not determined by area alone; location, floor and building age are equally important, and a single line inevitably falls short by being too simplistic.
- context after: Therefore, in practical applications people often introduce multiple independent variables and interpret the results cautiously in combination with professional experience, rather than blindly relying on the model's numbers.

## e11b8c89-6-en  (English reference -> back-translate into Chinese)

- context before: It should be pointed out that medical insurance benefits have a waiting period, so it is best not to let contributions have a gap.
- **TARGET:** If you are temporarily unemployed, you can pay on your own as a flexibly employed person, so that your length of service and account balance do not develop a break.

## e3c26284-2-en  (English reference -> back-translate into Chinese)

- context before: Temple fairs mostly spread out in the streets and lanes around temples, with vendor next to vendor, and sugar paintings, paper cuttings, clay figurines, and old books and old records crowded together in one place, the sounds of hawking and of gongs and drums layered over one another.
- **TARGET:** After nightfall the lantern fair takes over the shift, and strings of lanterns spread all the way along the river embankment and the old street, their reflections breaking into shimmering gold on the water.
- context after: What people think about most is often guessing lantern riddles: the riddle slips hang beneath the lanterns, and those who guess right may take one down to exchange for a small prize, while onlookers chatter noisily and burst into laughter at a wrong guess, and that liveliness spreads from one person to the whole street.

## efcd3571-1-en  (English reference -> back-translate into Chinese)

- context before: The mean can only tell us the central position of a set of data, but cannot reveal the differences among them.
- **TARGET:** If two sets of scores have the same mean, with one set of scores concentrated near the mean and the other widely varying from high to low, then it is hard to tell which is better from the mean alone.
- context after: Variance is born precisely to make up for this shortcoming: it squares each data point's deviation from the mean and then averages them, thereby condensing the overall degree of dispersion into a single number.

## f6ddd4b3-2-en  (English reference -> back-translate into Chinese)

- context before: Before dawn, the queue outside the mountain gate has already wound for several li, and tourists clutch their phones and refresh the page repeatedly, fearing that the ticket reservation slots will be snatched up within a few minutes.
- **TARGET:** Once inside the scenic area, so-called sightseeing is more like being pushed forward by the crowd: the viewing platform is shoulder to shoulder, taking a single photo means queuing for half a day, a sea of people, every step difficult.
- context after: So quite a few people begin to reflect on their way of traveling.

## f6ddd4b3-4-en  (English reference -> back-translate into Chinese)

- context before: So quite a few people begin to reflect on their way of traveling.
- **TARGET:** Some split the holiday into two parts and go at off-peak times; some give up internet-famous attractions and turn to small towns and villages that are not very famous but have quiet, beautiful scenery.
- context after: Travel guides have been updated accordingly, no longer simply listing "must-visit check-in spots", but reminding readers to pay attention to crowd-limiting announcements and weather changes.

## fc7d1064-3-en  (English reference -> back-translate into Chinese)

- context before: By comparison, unstructured data has no uniform format; the comment text customers leave and the product pictures they upload both belong to this category.
- **TARGET:** For a comment like "beautifully packaged, but delivery is too slow", a person can read the praise and criticism at a glance, but a machine finds it hard to process directly.
- context after: To solve this problem, researchers often first ask dedicated people to annotate large numbers of comments, for example classifying sentences as "positive reviews" or "negative reviews", and then let algorithms learn patterns from them.

## fd1531c7-3-en  (English reference -> back-translate into Chinese)

- context before: In the north, a New Year's Eve dinner without dumplings is not considered complete; and for many people, making dumplings is itself the most concrete form of family reunion: several pairs of hands busy at the same chopping board, the conversation stretching from the gains and losses of the old year to the plans for the new one.
- **TARGET:** According to the old custom, Mother will quietly wrap a washed coin inside one of the dumplings.
- context after: Whoever bites into it is regarded as the most fortunate person in the coming year.

## fd1531c7-4-en  (English reference -> back-translate into Chinese)

- context before: According to the old custom, Mother will quietly wrap a washed coin inside one of the dumplings.
- **TARGET:** Whoever bites into it is regarded as the most fortunate person in the coming year.
- context after: This is naturally only a psychological comfort of courting good luck, and the coin itself has no magic; yet it is precisely this smiling expectation that gives an ordinary dinner a sense of ritual.
