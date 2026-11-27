---
title: Which exercise types need explanations — survey and word-option pilot, 2026-11-27
type: evaluation
status: complete
last_updated: 2026-11-27
---

# Which exercise types need explanations — 2026-11-27

Owner: "Are there any other exercises that would benefit from explanations?", then "I think
particle choice, word form and synonym/antonym should be the ones we add explanations for. Can we
do it with Claude api?" Context: [[decisions/ADR-064-exercise-explanations-generated-once-and-cached]].

## Survey (40 random active items per type, content hydrated from Storage)

"NL" = Latin-script text an English speaker can read; "TL" = Japanese / Chinese text.

| Type | ja items / zh items | Shown after answering | Gap |
|---|---|---|---|
| fill the blank (`cloze_completion`) | 10,552 / 14,274 | one note on the key: ja 22 NL / 18 TL; zh 40 TL | wrong options never explained |
| particle (`particle_selection`) | 6,137 / — | one note: 17 NL / 23 TL (`error_tags` per wrong option, TL, not shown) | same |
| word form (`morphology_slot`) | 2,541 / — | one note: 19 NL / 21 TL | same |
| synonym / antonym | 1,377 / 1,453 | one note: ja 13 NL / 27 TL; zh 40 TL | same |
| listening (`phonetic_recognition`) | 3,266 / 1,681 | note on the key 40/40 TL; a note per wrong option exists (90/90 TL, templated) but is never rendered | no-model fix possible |
| typed fill-in (`cloze_typed`) | 11,259 / 13,996 | nothing | needs a model |
| word order (`jumbled_sentence`) | 1,332 / 624 | nothing | needs a model |
| script ↔ sound, tones, counters, definition match, flashcards, translation choice | ~9,850 ja / ~22,000 zh | the key | little to gain |

Also: the word's definition shown in fill-the-blank, word-form and synonym questions
(`word_definition` / `nl.en.definition`) was TL in 30/30 sampled per type; the English gloss rows
could replace it at serve time as for definition match (TASK-1250).

Real ja sittings, last 30 days: ~28 items each.

## Owner's choice

Particle, word form, synonym / antonym. Built 2026-11-27 (TASK-1242): the options become the units
of the shared explanation machinery, prompt `OPTION_PROMPT_VERSION = 1`, Storage files
`explanations/{lang}/{sense}.{nl}.o1.json` beside the `p2` ones. Fill the blank, typed fill-in,
word order and listening were not chosen (TASK-1249–1251).

## Pilot (Claude Sonnet 5.5, effort medium, Message Batches, owner's key)

18 random ja senses (7 per type, drawn by `md5(sense_id || 'pilot-o1')`), 52 items (23 particle,
18 word form, 11 synonym / antonym): **52 / 52 usable, 18 files written, $0.146** (33,669 in /
22,457 out tokens; $0.0028 an item batched). Ended within 2 minutes.

Read by hand (3 per type): correct grammar on every item; each wrong option gets what it marks or
what form it is, and why it does not fit (e.g. で for 国際法廷___裁かれる; まで after the
dictionary form 整う). One gloss slipped into Chinese ("negative连用 form"): the prompt now asks for
form names in English (prompt version unchanged — wording only, same output shape).

## Estimate for the rest

| Run | Items | Estimate |
|---|---|---|
| ja, all three types | 10,003 (10,055 less the pilot's 52) | **~$28** |
| zh synonym / antonym | 1,453 | ~$4 |

Storage: ~1.7 KB per item, ~17 MB for ja; database unchanged apart from one `storage.objects`
row (~0.5 KB) per file.
