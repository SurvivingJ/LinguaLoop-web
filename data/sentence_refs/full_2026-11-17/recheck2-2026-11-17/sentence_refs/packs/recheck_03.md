# Recheck pack 03 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/back/03.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_03.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/verdicts/03.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck2-2026-11-17/sentence_refs/packs/recheck_03.gold.md`. Do not open it yet.


## 6a7c9c62-3-en  (English reference -> back-translate into Chinese)

- context before: Many amateur runners join running clubs, train together on weekends, and learn how to control their pace, avoiding burning up their energy too fast right from the start.
- **TARGET:** For them, finishing a race is not only for getting a medal, but even more a confirmation of self-discipline and perseverance.
- context after: In a running club there are both experienced pace leaders and newcomers who have just started, and everyone reminds one another about refueling, warming up and recovery.

## 7961f3bf-2-en  (English reference -> back-translate into Chinese)

- context before: Take the recruitment screening system developed by a multinational company as an example: engineers trained the model with hiring records from the past ten years, and men account for the vast majority of these records.
- **TARGET:** As a result, the system gradually linked "male" with "excellent candidate" and automatically lowered the scores of résumés containing female-related experience.
- context after: This seemingly objective judgment has in fact entrenched and amplified historical discrimination.

## 7961f3bf-4-en  (English reference -> back-translate into Chinese)

- context before: This seemingly objective judgment has in fact entrenched and amplified historical discrimination.
- **TARGET:** What is more troublesome is that most algorithms are like a "black box", and users find it hard to know the basis of their decisions; the lack of transparency lets the problem go unnoticed for a long time.
- context after: To improve fairness, on the one hand it is necessary to take into account the representativeness of different groups when collecting training data, and on the other hand an independent review mechanism should be established, with evaluation standards made public, so that those affected have the right to question and appeal.

## 7fbfbde8-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** For many young people, obtaining a driver's license is almost regarded as a necessary rite of passage into adulthood.
- context after: However, only after actually entering driving school do people discover that this process is far longer than imagined.

## 7fd46cbe-6-en  (English reference -> back-translate into Chinese)

- context before: If they fail to get a ticket right away, passengers can also submit a waitlist order and wait for the system to automatically match returned tickets or newly added seats.
- **TARGET:** For most people, the Spring Festival travel rush is not only a journey but also an arrangement connected with family reunion, so what lies behind grabbing tickets is anticipation of home.

## 820230b1-3-en  (English reference -> back-translate into Chinese)

- context before: However, a statistician put forward the opposite view: this data came only from aircraft that had successfully returned, while aircraft that were hit in a vital spot and could not fly back had not entered the statistics at all.
- **TARGET:** In other words, the reason there are few bullet holes near the engines is not that those spots are hard to hit, but that most aircraft hit there crashed.
- context after: This phenomenon of reaching one-sided conclusions because of improper sample selection is called survivorship bias.

## 8364d584-3-en  (English reference -> back-translate into Chinese)

- context before: Nowadays, more and more parents are beginning to value quality education, hoping that their children will not only master one skill but also develop creativity, cooperation, and problem-solving abilities.
- **TARGET:** So coding summer camps are gradually becoming popular.
- context after: At camp, children learn graphical programming or simple algorithms, and use code to complete animations, games, and small projects.

## 83ce0bb4-2-en  (English reference -> back-translate into Chinese)

- context before: It seems to be just a light tap of the fingertip, yet it conceals a subtle sense of social propriety.
- **TARGET:** Those who send red envelopes often have to weigh the amount and the number of people, neither appearing perfunctory nor being so lavish that it makes others feel burdened; those who grab them need to judge the timing, since if the first person to open one says nothing, they will inevitably be seen as rude, and a fitting word of thanks or good wishes is often valued more than the red envelope itself.
- context after: As for the "luckiest draw", it is originally just an accidental result of the system's random allocation, but in the context of a group chat it is often given extra meaning: some people take the initiative to send another red envelope to "pass the baton", and some jokingly ask the lucky person to treat them to a meal later, and in the give and take, the distance between elders and juniors, colleagues and friends is quietly drawn closer.

## 840ca470-4-en  (English reference -> back-translate into Chinese)

- context before: Finally seated, we found the setting truly exquisite: warm yellow lighting, vintage wooden tables, nearly every corner seeming designed for the camera.
- **TARGET:** However, when the dessert arrived, our expectations quietly cooled: it looked beautiful, but the cream was too sweet and cloying, and the base was a little soggy.
- context after: We looked at each other in silence, both knowing in our hearts that this time we had probably stepped on a landmine.

## 840ca470-6-en  (English reference -> back-translate into Chinese)

- context before: We looked at each other in silence, both knowing in our hearts that this time we had probably stepped on a landmine.
- **TARGET:** On the way home, I pulled up the reviews on my phone and found that beneath the high scores there were also some complaints, with quite a few people complaining about "photos that lie" and poor value for money.
- context after: Perhaps what viral restaurants sell has never been just food, but an experience worth sharing.

## 840ca470-8-en  (English reference -> back-translate into Chinese)

- context before: Perhaps what viral restaurants sell has never been just food, but an experience worth sharing.
- **TARGET:** But once the time cost of queuing is counted into the bill as well, living up to one's name becomes something quite luxurious.

## 8b72a25f-2-en  (English reference -> back-translate into Chinese)

- context before: Millions of workers have bid farewell to fixed workstations and turned to making a living as gig workers: they drive ride-hailing cars through streets and alleys, deliver meals among office buildings, or wait in front of screens for work to be assigned.
- **TARGET:** This way of making a living does bring freedom of time and low entry barriers, but it also hands the risk of unstable income back to the individual: the number of orders depends entirely on the platform's algorithmic dispatch, and the peak season and the off season are often as different as heaven and earth.
- context after: What is thornier is the problem of social insurance.

## 9bfc841b-5-en  (English reference -> back-translate into Chinese)

- context before: After desensitization processing, these records can outline the movement trajectories of crowds between different time periods and different areas, thereby revealing the main travel directions during commuting peaks.
- **TARGET:** Using these analysis results, planning departments can discover which residential areas lack direct services to employment centers and which road sections are congested for long periods, and then add routes, adjust stops or shorten departure intervals in a targeted way.
- context after: Some bus routes that originally detoured too far have had their travel times shortened after optimization, and passengers' waiting experience has also clearly improved.

## a6302a5f-4-en  (English reference -> back-translate into Chinese)

- context before: For the elderly, leaving is not a mere spatial relocation but a stripping away of the sense of belonging: they know the dip in every threshold, and also remember whose children grew up under the tree.
- **TARGET:** Compensation and resettlement plans do indeed provide material accommodation, but they can hardly take on the feelings attached to specific places.
- context after: The new resettlement buildings are bright and tidy, and elevators replace the stairs that could never be finished climbing, but in the stairwell one can no longer hear greetings called through the windows.

## ab153bc8-1-en  (English reference -> back-translate into Chinese)

- context before: As urban dining consumption grows ever more active, food waste in restaurants has also gradually drawn attention.
- **TARGET:** Many customers care about keeping up appearances when ordering, often exceeding what they can actually eat, so that a lot of dishes are left over.
- context after: In fact, ordering a suitable amount and taking food as needed is a way of saving that everyone can practise.

## ba1a45c2-2-en  (English reference -> back-translate into Chinese)

- context before: Many young people jokingly call themselves "poop-shovel officers" and gain emotional comfort in the course of caring for cats and dogs, but they often overlook the boundaries that ought to exist between people and animals in an enclosed community.
- **TARGET:** The dog-walking hours in the early morning and at night are precisely when neighbor conflicts are most easily inflamed: barking penetrates thin walls, lapses with the leash let pets startle the elderly and children, and excrement left in stairwells is also a common sight.
- context after: Such neighbor disputes seem trivial but in fact reflect a lack of living ethics: pet owners both enjoy the pleasure of companionship and must bear the responsibility of restraint.

## ba1a45c2-3-en  (English reference -> back-translate into Chinese)

- context before: The dog-walking hours in the early morning and at night are precisely when neighbor conflicts are most easily inflamed: barking penetrates thin walls, lapses with the leash let pets startle the elderly and children, and excrement left in stairwells is also a common sight.
- **TARGET:** Such neighbor disputes seem trivial but in fact reflect a lack of living ethics: pet owners both enjoy the pleasure of companionship and must bear the responsibility of restraint.
- context after: Leashing, cleaning up, and actively giving way: these small acts make up the bottom line of civilized pet keeping.

## ba1a45c2-5-en  (English reference -> back-translate into Chinese)

- context before: Leashing, cleaning up, and actively giving way: these small acts make up the bottom line of civilized pet keeping.
- **TARGET:** If every owner could consider other people's expectations of quiet and cleanliness, people and pets could coexist peacefully under the same roof.

## bb4a2a5d-1-en  (English reference -> back-translate into Chinese)

- context before: On New Year's Eve, the whole family sits around the television, waiting for the Spring Festival Gala to begin.
- **TARGET:** Father, as usual, occupies the middle of the sofa, while Mother is busy setting melon seeds and tangerines on the coffee table.
- context after: Song and dance and crosstalk take the stage in turn, but what people look forward to most is still those few skits, which often take family trivia as material and exaggeratedly lay out the awkwardness and warmth of life, leaving a little aftertaste once the laughter is over.

## bb4a2a5d-3-en  (English reference -> back-translate into Chinese)

- context before: Song and dance and crosstalk take the stage in turn, but what people look forward to most is still those few skits, which often take family trivia as material and exaggeratedly lay out the awkwardness and warmth of life, leaving a little aftertaste once the laughter is over.
- **TARGET:** Interestingly, the family's reactions to the same program often differ greatly: Grandmother laughs until she keeps wiping away tears, while I find the lines slightly dated and cannot help grumbling in a low voice on my phone.
- context after: Online comments are more direct, with dense bullet comments flying past quickly on the video page, some sighing that "the New Year flavor has faded", and others retorting that liveliness need not be required to be perfect.

## c025ac1e-3-en  (English reference -> back-translate into Chinese)

- context before: So the mother quits her job and rents a place near the school to accompany the child while studying, and the father studies the admission cutoff scores and application strategies of various schools late at night, as if, so long as he calculates finely enough, he can pave a secure road for the child.
- **TARGET:** However, this meticulous care often turns, without anyone noticing, into heavy pressure: the child fears letting down the parents' sacrifice and also worries that their choices will be repeatedly discussed and revised, until in the end they can hardly even be sure what they like.
- context after: In fact, the gaokao is indeed important, but it is only one of the many crossroads in life.

## c025ac1e-5-en  (English reference -> back-translate into Chinese)

- context before: In fact, the gaokao is indeed important, but it is only one of the many crossroads in life.
- **TARGET:** Only when families learn to restore a score to being just a score, and hand the choice of application back to the child's interests, will that pressure truly loosen.

## c0f09fb2-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** In the field of business management, there has long been a contest between two orientations in decision-making.
- context after: One is "off-the-cuff" decision-making, in which managers rely on personal intuition or scattered impressions to make a quick call, which seems decisive and efficient, but in fact risks lurk within it.
