# Recheck pack 03 — BLIND HALF

You are the second reviewer of references that scored low on tightness: a first
reviewer's blind back-translation landed far from the gold. Decide whether the
reference is loose (rewrite it) or the gold simply has several faithful
renderings (pass, with a note). Follow `.claude/skills/sentence-reference-review/SKILL.md`
for what to check (meaning, numbers and names, sentence identity, register,
leakage, tightness). The neighbours are context only; judge the TARGET.

Order (hard rule): write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/back/03.json` with your blind
back-translation of every TARGET into the studied language BEFORE opening
`recheck_03.gold.md`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "back": "<your L2 version>"}]}

Then open the gold file and write `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/verdicts/03.json`:

    {"reviewer_model": "<your model id>", "items": [{"key": "<key>", "verdict": "pass|rewritten|fail",
      "entailment_ok": true, "l1": "<final reference: unchanged for pass, your rewrite for rewritten>",
      "gold_seen_early": false, "notes": "<one line: why low, what you changed>"}]}

`fail` only for a gold that is itself broken (fragment, leaked preamble, mixed script).
A rewrite stays one sentence, keeps every number and name, adds nothing, and has
no L2 script, notes or parentheses. Never change the gold. Every key gets a verdict.


The gold half is `data/sentence_refs/full_2026-11-17/recheck-2026-11-17/sentence_refs/packs/recheck_03.gold.md`. Do not open it yet.


## 7e1103fb-2-en  (English reference -> back-translate into Japanese)

- context before: In the past, everyone got the same medicine.
- **TARGET:** Now it is medicine that suits each individual person's body.
- context after: The doctor examines the body and decides on the medicine.

## 7ea0010a-5-en  (English reference -> back-translate into Japanese)

- context before: In the eyes of the child who gazes at that sight dwells a sense of awe toward the fundamental toughness that life possesses.
- **TARGET:** The tiny workings that we adults so often overlook, he keeps recording innocently and solemnly.
- context after: Truly, that very attitude of conversing with the earth is surely nothing other than the nurturing of souls who will carry the future.

## b17d99de-0-en  (English reference -> back-translate into Japanese)

- **TARGET:** In apartments with limited space in the city, modern interior design greatly influences the impression of a space.
- context after: Based on the philosophy of minimalism, by keeping only the necessary elements, residents can lead a calmer daily life.

## b228d2e6-2-en  (English reference -> back-translate into Japanese)

- context before: This piece of clothing is my favourite.
- **TARGET:** I like the picture of a bear.
- context after: I wear this T-shirt every day.

## ba61a420-4-en  (English reference -> back-translate into Japanese)

- context before: At this point, the scientific backing that the film of fat functions as a barrier preventing the moisture of the jam from soaking in also cannot be ignored.
- **TARGET:** Next, layer jam, such as raspberry, onto the paired other half, or onto the same slice.
- context after: The contrasting harmony that sweetness and saltiness, smoothness and graininess weave in the mouth goes beyond the realm of mere nutritional intake, brings about recovery of cognitive function in a short time, and is completed as an act of eating in which rationality and aesthetics are fused.

## d112902b-2-en  (English reference -> back-translate into Japanese)

- context before: However, the eyes of my young child, standing by the window, were fixed on the yard covered in silver-white, and he was driven by an irrepressible impulse of life.
- **TARGET:** Paying no mind to the coldness of the harsh winter, he is purely and wholly absorbed in getting ready to play outside.
- context after: Though clumsily, he puts his arms through the sleeves of a thick coat, putting on armour to protect himself from the cold air.

## d1e30374-2-en  (English reference -> back-translate into Japanese)

- context before: What he values is feeding the chickens, which are animals.
- **TARGET:** The food given at this time of day is a mixture of fresh grain and vegetables harvested locally.
- context after: This is because the health of chickens that wake with the sunrise is precisely the condition for having them lay nutritious eggs.

## 03f1ba3e-9-en  (English reference -> back-translate into Chinese)

- context before: I remember that the first time I saw this T-shirt, I liked it very much.
- **TARGET:** At that time I saw it in a shop, and the kitten in the picture caught my attention at once.
- context after: I tried it on, and it felt just the right size, and also very comfortable.

## 03f1ba3e-20-en  (English reference -> back-translate into Chinese)

- context before: This kitten's expression is very relaxed, without the slightest worry.
- **TARGET:** The reason I like this T-shirt is, to a large extent, because of this picture.
- context after: It makes me feel calm and relaxed.

## 0899b72c-6-en  (English reference -> back-translate into Chinese)

- context before: The company must explain clearly how the software learns.
- **TARGET:** It must not tell lies.
- context after: When people use the software, it must be safe.

## 0adedab7-8-en  (English reference -> back-translate into Chinese)

- context before: When customers buy drinks, they pay a little extra, and after returning the empty bottle they can get the deposit back.
- **TARGET:** This method has greatly increased the recycling rate of plastic bottles.
- context after: Some cities in Asia, on the other hand, have strengthened waste sorting management, stipulating that residents must put plastic waste out separately, otherwise they will be fined.

## 18a77687-26-en  (English reference -> back-translate into Chinese)

- context before: It reminds me that sometimes simple is best.
- **TARGET:** This T-shirt has also given me more inspiration for putting outfits together.
- context after: I can pair it with jeans, and I can also pair it with casual trousers.

## 18a77687-27-en  (English reference -> back-translate into Chinese)

- context before: This T-shirt has also given me more inspiration for putting outfits together.
- **TARGET:** I can pair it with jeans, and I can also pair it with casual trousers.
- context after: It goes with everything; whatever the occasion, it can be worn.

## 18a77687-28-en  (English reference -> back-translate into Chinese)

- context before: I can pair it with jeans, and I can also pair it with casual trousers.
- **TARGET:** It goes with everything; whatever the occasion, it can be worn.
- context after: This makes me feel it is very convenient, and it also saves me a lot of trouble with matching outfits.

## 18a77687-30-en  (English reference -> back-translate into Chinese)

- context before: This makes me feel it is very convenient, and it also saves me a lot of trouble with matching outfits.
- **TARGET:** I once considered buying a new T-shirt with a more complicated design on it, or a more fashionable style.
- context after: But every time I see this white T-shirt, I give up that idea.

## 18a77687-33-en  (English reference -> back-translate into Chinese)

- context before: Because I know that what I really like is the feeling it brings, that simple, free, happy feeling.
- **TARGET:** This T-shirt has also taught me to value things more.
- context after: I know that many things, once lost, are very hard to get back.

## 1e6419a4-22-en  (English reference -> back-translate into Chinese)

- context before: Reputation in the virtual world is conferred by sustained behavioral output rather than by established status.
- **TARGET:** This meritocratic, performance-oriented culture gives rise to flat, self-organizing community structures.
- context after: Players spontaneously form guilds and clans, set internal rules, mediate conflicts, and even organize cross-border charity activities, turning virtual capital into real-world goodwill.

## 217b165d-2-en  (English reference -> back-translate into Chinese)

- context before: Washing hands is very important.
- **TARGET:** Soap and water can clean our hands.
- context after: Germs can make people sick.

## 21b994a8-1-en  (English reference -> back-translate into Chinese)

- context before: On a sunny morning, in the little girl Lili's room, a special toy was sitting on the desk.
- **TARGET:** It is a plush teddy bear named "Xiongxiong".
- context after: Xiongxiong looks very cute: its body is brown, its round eyes sparkle with a friendly light, and its nose is black and always tilts slightly upward, as if smiling.

## 2293ae13-6-en  (English reference -> back-translate into Chinese)

- context before: These countries export coffee beans to other countries.
- **TARGET:** Exporting means selling goods abroad.
- context after: Some countries without growing conditions, such as some European countries, need to import coffee beans from abroad.

## 2293ae13-8-en  (English reference -> back-translate into Chinese)

- context before: Some countries without growing conditions, such as some European countries, need to import coffee beans from abroad.
- **TARGET:** Importing is buying goods from other countries.
- context after: Through international trade, coffee beans are transported from the place of production to all parts of the world.

## 24739f58-0-en  (English reference -> back-translate into Chinese)

- **TARGET:** Many countries now do not allow plastic bags to be used.
- context after: This is to protect the environment.

## 24739f58-2-en  (English reference -> back-translate into Chinese)

- context before: This is to protect the environment.
- **TARGET:** Each country has different rules.
- context after: Some countries say that shops cannot give customers free plastic bags.

## 24cbee31-4-en  (English reference -> back-translate into Chinese)

- context before: Flowers have pollen, and bees take the pollen away.
- **TARGET:** This way, flowers can bear fruit.
- context after: A lot of food comes from fruit.

## 35742c67-1-en  (English reference -> back-translate into Chinese)

- context before: The Great Wall of China is a very old and huge structure.
- **TARGET:** In ancient times, people built the Great Wall for defence.
- context after: The Great Wall is in northern China, and it is very, very long.
