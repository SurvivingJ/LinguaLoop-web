# Pairwise review pack 03

## Rubric

For each level shown, compare Pack A and Pack B for the SAME sense and level and
judge which set of exercises is better, or call it a tie. Score on:

1. **Correctness** -- is the correct answer actually correct for the sentence/prompt shown?
2. **Single defensible answer** -- is exactly one option defensible as correct, with no
   distractor that a reasonable native speaker could also accept?
3. **Distractor plausibility** -- are distractors plausible confusions (not random noise),
   and none of them *also correct* ("also-correct" is a major defect, not a style nit)?
4. **Naturalness** -- does the sentence/prompt read as something a native speaker would
   actually write or say?
5. **Target-word anchoring** -- does the exercise actually test the target word/sense, not
   some other word in the sentence? **Known defect class: the target word appears only
   inside a compound word**, so the exercise is really testing the compound, not the
   target sense. Flag this explicitly as a major defect when you see it.
6. **L1 (`phonetic_recognition`) validity, if shown** -- L1 is an audio-confusable-only,
   listening exercise: pitch-accent-only distractor pairs are NOT valid, because TTS only
   renders one form. A pitch-accent-only distractor is a major defect, not a style nit.

Return one JSON line per (sense_id, level) you evaluated:
`{"sense_id": ..., "level": ..., "preferred": "A" | "B" | "tie", "major_defects_A": [...], "major_defects_B": [...], "notes": "..."}`
`major_defects_A` / `major_defects_B` are short strings from the checklist above (e.g.
"also-correct distractor", "compound-word anchoring", "pitch-accent-only L1 pair"), empty
list if none found. Do not guess which side is the candidate or reference -- you are not
told, and should not try to infer it from formatting.


## sense 13931, level 6

#### Pack A
### Level 6 (sense 13931, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He brushed his teeth with green shoe polish.",
      "is_correct": false
    },
    {
      "text": "The green light told him to stop the car immediately.",
      "is_correct": false
    },
    {
      "text": "She wore a bright green jacket to the school party.",
      "is_correct": true
    },
    {
      "text": "The green blood pumped through his veins.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic: a green traffic light signals drivers to go, not to stop. pragmatic: shoe polish is a toxic substance meant for leather, completely inappropriate for oral hygiene. semantic: human and most animal blood is red, making green blood biologically inaccurate in a standard context.",
  "target_word": "green"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The snow on the mountain was bright green in the middle of winter.",
      "is_correct": false
    },
    {
      "text": "The blood from his cut was a vibrant shade of green.",
      "is_correct": false
    },
    {
      "text": "The sky is always green during a clear sunny day.",
      "is_correct": false
    },
    {
      "text": "The small frog sitting on the rock was dark green.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate because the sky is blue, not green, on a clear day. Semantically inappropriate because snow is naturally white, not green. Pragmatically inappropriate because human blood is red, not green.",
  "target_word": "green"
}
```

#### Pack B
### Level 6 (sense 13931, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The mathematical equation was green and difficult to solve.",
      "is_correct": false
    },
    {
      "text": "The silence in the room felt green and heavy.",
      "is_correct": false
    },
    {
      "text": "She painted her bedroom walls a bright green color.",
      "is_correct": true
    },
    {
      "text": "Her argument was very green during the debate.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: abstract concepts like equations do not have physical colors. Semantically inappropriate: while 'green' can mean inexperienced, it is not standard collocation for describing the quality or validity of an argument itself. Semantically inappropriate: silence is an auditory absence and cannot possess a visual color property.",
  "target_word": "green"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The angry manager gave his employee a green look when the report was late.",
      "is_correct": false
    },
    {
      "text": "He is a green lawyer with twenty years of experience in the court.",
      "is_correct": false
    },
    {
      "text": "She felt very green after hearing the sad news about her friend.",
      "is_correct": false
    },
    {
      "text": "They wore green shirts during the school sports event.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: 'green' is not idiomatically used to describe an angry or disapproving facial expression (unlike 'black' look or 'dirty' look). Semantically inappropriate: 'green' typically describes nausea or envy, not sadness or grief, making the emotional mapping incorrect. Semantically inappropriate: 'green' means inexperienced or novice, which directly contradicts the phrase 'twenty years of experience'.",
  "target_word": "green"
}
```

---

## sense 13946, level 6

#### Pack A
### Level 6 (sense 13946, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Do you ever dream about traveling to planets far away?",
      "is_correct": true
    },
    {
      "text": "The coffee in this cup tastes far away.",
      "is_correct": false
    },
    {
      "text": "She solved the math problem far away.",
      "is_correct": false
    },
    {
      "text": "He arrived at the meeting far away.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'far away' describes spatial distance or mental abstraction, not sensory qualities like taste. Semantically inappropriate: 'far away' does not describe the manner or success of solving a logical problem. Syntactically/Semantically awkward: while one can travel from far away, arriving 'far away' implies the destination itself is distant relative to an unstated point, which is confusing without context; usually we say he arrived 'late' or 'early'. In this specific isolated sentence, it fails to convey a clear meaning compared to standard adverbs of time or manner.",
  "target_word": "far away"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He wore a far away shirt to the party.",
      "is_correct": false
    },
    {
      "text": "The chef added far away salt to the soup.",
      "is_correct": false
    },
    {
      "text": "She solved the math problem far away.",
      "is_correct": false
    },
    {
      "text": "The sound of music echoed from somewhere far away.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Far away' describes spatial distance and cannot modify a concrete noun like 'salt' in a culinary context. Semantically inappropriate: 'Far away' refers to physical or metaphorical distance, not the manner or success of solving a logical problem. Semantically inappropriate: 'Far away' is an adverbial phrase of place/distance and cannot function as an adjective describing clothing.",
  "target_word": "far away"
}
```

#### Pack B
### Level 6 (sense 13946, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "elsewhere",
    "abroad",
    "nearby",
    "ahead"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "genuine antonym: at a short distance rather than a great one"
    }
  }
}
```

---

## sense 13981, level 3

#### Pack A
### Level 3 (sense 13981, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically ___ and crucial for the quality of the final product.",
  "original_sentence": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically demanding and crucial for the quality of the final product.",
  "correct_answer": "demanding",
  "options": [
    "fragile",
    "mandatory",
    "demanding",
    "stagnant"
  ],
  "explanation": "Correct: fits the context of a process requiring significant physical effort and attention.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Balancing schoolwork and sports can be extremely ___ for teenagers.",
  "original_sentence": "Balancing schoolwork and sports can be extremely demanding for teenagers.",
  "correct_answer": "demanding",
  "options": [
    "demanding",
    "heavy",
    "sudden",
    "relaxing"
  ],
  "explanation": "The correct adjective describing a task that requires a lot of effort and attention.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```

#### Pack B
### Level 3 (sense 13981, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically ___ and crucial for the quality of the final product.",
  "original_sentence": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically demanding and crucial for the quality of the final product.",
  "correct_answer": "demanding",
  "options": [
    "delightful",
    "optional",
    "demanding",
    "brief"
  ],
  "explanation": "Correct: Fits the context of a process requiring significant physical effort.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Is this university course as ___ as people have been saying on social media?",
  "original_sentence": "Is this university course as demanding as people have been saying on social media?",
  "correct_answer": "demanding",
  "options": [
    "demanding",
    "boring",
    "brief",
    "optional"
  ],
  "explanation": "Correct: Fits the context of a course requiring significant effort and attention.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```

---

## sense 13981, level 4

#### Pack A
### Level 4 (sense 13981, difficulty None)
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "Playing the piano at such a high level requires a ___ practice schedule every single day.",
  "original_sentence": "Playing the piano at such a high level requires a demanding practice schedule every single day.",
  "required_pos": "adjective",
  "options": [
    "demandation",
    "demandment",
    "demanding",
    "demandful"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established participial adjective meaning requiring great effort or skill"
    }
  }
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "The hiking trail grew increasingly ___ as they climbed higher into the mountains.",
  "original_sentence": "The hiking trail grew increasingly demanding as they climbed higher into the mountains.",
  "required_pos": "adjective",
  "options": [
    "demandive",
    "demandity",
    "demanding",
    "demandous"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established participial adjective meaning needing effort"
    }
  }
}
```

#### Pack B
### Level 4 (sense 13981, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She found her new job extremely ___ because it required working long hours and learning complex software quickly.",
  "original_sentence": "She found her new job extremely demanding because it required working long hours and learning complex software quickly.",
  "correct_answer": "demanding",
  "base_form": "demand",
  "form_label": "adjective",
  "options": [
    "demand",
    "demanding",
    "demands",
    "demanded"
  ],
  "explanation": "adjective form is required to describe the noun 'job'",
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "She found her new job extremely ___ because it required working long hours and learning complex software quickly.",
  "original_sentence": "She found her new job extremely demanding because it required working long hours and learning complex software quickly.",
  "required_pos": "adverb",
  "options": [
    "demandful",
    "demandingly",
    "demandous",
    "demandity"
  ],
  "correct_answer": "demandingly",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard adverbial form derived from the adjective"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Managing a busy restaurant schedule is a ___ task that leaves very little room for error.",
  "original_sentence": "Managing a busy restaurant schedule is a demanding task that leaves very little room for error.",
  "correct_answer": "demanding",
  "base_form": "demand",
  "form_label": "present participle",
  "options": [
    "demand",
    "demands",
    "demanding",
    "demanded"
  ],
  "explanation": "present participle functioning as an adjective to modify the noun 'task'",
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "Managing a busy restaurant schedule is a ___ task that leaves very little room for error.",
  "original_sentence": "Managing a busy restaurant schedule is a demanding task that leaves very little room for error.",
  "required_pos": "adverb",
  "options": [
    "demandment",
    "demandingly",
    "demandous",
    "demandity"
  ],
  "correct_answer": "demandingly",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverbial form derived from the adjective"
    }
  }
}
```

---

## sense 13981, level 6

#### Pack A
### Level 6 (sense 13981, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The demanding puppy slept quietly in its bed all day, requiring absolutely no attention from its owners.",
      "is_correct": false
    },
    {
      "text": "That teacher is known for having a demanding grading policy that challenges all her students.",
      "is_correct": true
    },
    {
      "text": "The wooden chair is extremely demanding, often asking the room to rearrange its furniture.",
      "is_correct": false
    },
    {
      "text": "She found the taste of plain water to be very demanding, so she added sugar to it.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: inanimate objects like chairs do not possess the agency to have expectations or make requests of others. Semantically inappropriate: 'demanding' describes tasks or people requiring effort and attention, not the flavor profile of a basic liquid. Pragmatically inappropriate: 'demanding' means expecting a lot of attention, which directly contradicts the subsequent clause about requiring no attention.",
  "target_word": "demanding"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Breathing air is a highly demanding process that takes up all of our daily energy.",
      "is_correct": false
    },
    {
      "text": "They faced a demanding situation when the project deadline was suddenly moved forward.",
      "is_correct": true
    },
    {
      "text": "The water in the pool was very demanding, requiring a lot of effort to stay wet.",
      "is_correct": false
    },
    {
      "text": "The hallway was extremely demanding, stretching for over five miles without any turns.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'demanding' applies to tasks or people requiring effort or attention, not the physical state of water. pragmatic: breathing is an automatic, effortless process for a healthy person, contradicting the definition of needing a lot of effort. semantic: 'demanding' describes the requirement of effort or attention, not the physical length or spatial dimensions of a location.",
  "target_word": "demanding"
}
```

#### Pack B
### Level 6 (sense 13981, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The water in the glass was demanding after sitting in the sun all day.",
      "is_correct": false
    },
    {
      "text": "He is a demanding teacher who expects every student to complete their assignments on time.",
      "is_correct": true
    },
    {
      "text": "The rock was very demanding when I kicked it by accident.",
      "is_correct": false
    },
    {
      "text": "She wore a demanding dress to the party that matched her shoes perfectly.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: Inanimate objects like water cannot have expectations or require effort from others; 'warm' or 'hot' would be appropriate. Semantically inappropriate: Clothing cannot be 'demanding' in the sense of requiring skill or attention from people; 'stylish' or 'elegant' fits better. Semantically inappropriate: A rock is an inanimate object and cannot expect anything from a person; 'hard' or 'painful' describes the physical sensation.",
  "target_word": "demanding"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Parents often feel exhausted when raising toddlers because the daily routine is so emotionally and physically demanding.",
      "is_correct": true
    },
    {
      "text": "He found the empty room demanding because there was nothing in it to look at.",
      "is_correct": false
    },
    {
      "text": "The lazy cat was very demanding because it slept for eighteen hours straight.",
      "is_correct": false
    },
    {
      "text": "The soft pillow was demanding on her neck after a long day.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Demanding' implies active effort or high expectations from others, which contradicts the passive behavior of sleeping. Semantically inappropriate: An empty room lacks the complexity or requirements that would make it 'demanding' of one's skill or attention. Collocationally/Semantically inappropriate: Soft pillows are typically described as 'comforting' or 'supportive'; they do not exert demands or require effort from the user.",
  "target_word": "demanding"
}
```

---

## sense 14001, level 1

#### Pack A
### Level 1 (sense 14001, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "system",
  "pronunciation": "SIS-tem",
  "ipa": "/ˈsɪstəm/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "system",
    "custom",
    "sister",
    "cistern"
  ],
  "correct_answer": "system",
  "explanation": "Correct: matches the target word pronunciation /ˈsɪstəm/.",
  "distractor_explanations": {
    "sister": "Phonetic distractor: shares initial /s/ and similar vowel/consonant structure, but differs in the medial cluster and final sound.",
    "custom": "Rhyme distractor: rhymes with the target (/ˈkʌstəm/ vs /ˈsɪstəm/) but starts with a different consonant cluster.",
    "cistern": "Minimal pair/Near-homophone: shares the initial /s/ sound and similar stress pattern, but differs in the vowel and final consonant."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14001, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "system",
  "pronunciation": "SIS-tuhm",
  "ipa": "/ˈsɪstəm/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "system",
    "sister",
    "systole",
    "sicken"
  ],
  "correct_answer": "system",
  "explanation": "Correct: This is the exact target word pronounced /ˈsɪstəm/.",
  "distractor_explanations": {
    "sister": "near-homophone: shares the /ˈsɪst/ onset but differs in the final syllable vowel (/ər/ vs /əm/).",
    "sicken": "minimal pair: differs only in the medial consonant cluster (/k/ vs /s/), keeping the same stress and syllable count.",
    "systole": "phonetic neighbor: shares the initial /ˈsɪst/ but adds an extra syllable and ends in a different vowel sound."
  },
  "distractor_source": "llm"
}
```

---

## sense 14001, level 3

#### Pack A
### Level 3 (sense 14001, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "These bugs talk to your body's defense ___, which is your immunity.",
  "original_sentence": "These bugs talk to your body's defense system, which is your immunity.",
  "correct_answer": "system",
  "options": [
    "routine",
    "strategy",
    "system",
    "machine"
  ],
  "explanation": "Correct: 'defense system' is the standard collocation for the body's immunity network.",
  "distractor_tags": {},
  "word_definition": "A set of connected parts that work together to form a complex whole.",
  "target_word": "system"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "A living plant is an open ___.",
  "original_sentence": "A living plant is an open system.",
  "correct_answer": "system",
  "options": [
    "machine",
    "mechanism",
    "system",
    "process"
  ],
  "explanation": "Correct: 'system' is the exact word from the base sentence, correctly identifying a plant as a set of connected parts.",
  "distractor_tags": {},
  "word_definition": "A set of connected parts that work together to form a complex whole.",
  "target_word": "system"
}
```

#### Pack B
### Level 3 (sense 14001, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "These bugs talk to your body's defense ___, which is your immunity.",
  "original_sentence": "These bugs talk to your body's defense system, which is your immunity.",
  "correct_answer": "system",
  "options": [
    "method",
    "system",
    "machine",
    "group"
  ],
  "explanation": "Correct: 'defense system' is the specific biological concept referring to immunity described in the sentence.",
  "distractor_tags": {},
  "word_definition": "A set of connected parts that form a complex whole.",
  "target_word": "system"
}
```

---

## sense 14001, level 4

#### Pack A
### Level 4 (sense 14001, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Sometimes, the defense ___ gets confused.",
  "original_sentence": "Sometimes, the defense system gets confused.",
  "correct_answer": "system",
  "base_form": "system",
  "form_label": "singular",
  "options": [
    "systems",
    "system",
    "system's",
    "systems'"
  ],
  "explanation": "the singular form is required to agree with the singular verb 'gets'",
  "word_definition": "A set of connected parts that work together to form a complex whole.",
  "target_word": "system"
}
```

#### Pack B
### Level 4 (sense 14001, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Sometimes, the defense ___ gets confused.",
  "original_sentence": "Sometimes, the defense system gets confused.",
  "correct_answer": "system",
  "base_form": "system",
  "form_label": "singular",
  "options": [
    "systems",
    "systems'",
    "system",
    "system's"
  ],
  "explanation": "singular noun required by the singular determiner 'the'",
  "word_definition": "A set of connected parts that form a complex whole.",
  "target_word": "system"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The weather ___ brought heavy rain and strong winds yesterday.",
  "original_sentence": "The weather system brought heavy rain and strong winds yesterday.",
  "correct_answer": "system",
  "base_form": "system",
  "form_label": "singular",
  "options": [
    "system",
    "systems'",
    "systems",
    "system's"
  ],
  "explanation": "singular noun required by the singular determiner 'The'",
  "word_definition": "A set of connected parts that form a complex whole.",
  "target_word": "system"
}
```

---

## sense 14001, level 6

#### Pack A
### Level 6 (sense 14001, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The system of the book was very heavy to carry in my backpack.",
      "is_correct": false
    },
    {
      "text": "The system was very loud and barked at the mailman.",
      "is_correct": false
    },
    {
      "text": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant.",
      "is_correct": true
    },
    {
      "text": "She baked a delicious system for the birthday party.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'system' refers to a set of connected parts, not a single physical object like a book. semantic: 'system' cannot refer to a baked good or food item. semantic: 'system' refers to an interconnected network of parts, not a living animal like a dog.",
  "target_word": "system"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The system was very tall and had green leaves.",
      "is_correct": false
    },
    {
      "text": "She poured a system of milk into her cereal bowl for breakfast.",
      "is_correct": false
    },
    {
      "text": "He felt a sharp pain in his system when he stubbed his toe.",
      "is_correct": false
    },
    {
      "text": "They designed a new computer system to help organize our homework files.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: 'system' refers to a complex whole of connected parts, not a physical liquid or a measurable quantity of food. semantic: A 'system' is an abstract or functional collection of parts, not a single physical organism that can grow leaves. collocational: While 'system' can refer to the body, we do not use it to describe a localized, specific physical injury like a stubbed toe; we use 'toe' or 'foot'.",
  "target_word": "system"
}
```

#### Pack B
### Level 6 (sense 14001, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The chef added a system of salt to the soup to enhance the flavor.",
      "is_correct": false
    },
    {
      "text": "She wore a beautiful system to the party last night.",
      "is_correct": false
    },
    {
      "text": "He read a system about ancient history from the library shelf.",
      "is_correct": false
    },
    {
      "text": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: 'system' implies a complex organized whole, whereas salt is a simple ingredient measured by amount (e.g., pinch, spoonful), not a structured entity. Semantically inappropriate: 'system' cannot refer to clothing or attire; the context requires a noun like 'dress' or 'outfit'. Semantically inappropriate: 'system' cannot refer to a literary work or publication; the context requires a noun like 'book' or 'text'.",
  "target_word": "system"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He kicked the soccer system into the goal.",
      "is_correct": false
    },
    {
      "text": "She wore a beautiful silk system to the party.",
      "is_correct": false
    },
    {
      "text": "Students tested the solar system model they built in science class.",
      "is_correct": true
    },
    {
      "text": "The chef added salt to the soup system to improve the flavor.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'System' implies a complex set of connected parts or rules, not a simple container or dish like a bowl or pot. Semantically inappropriate: 'System' cannot refer to clothing or fabric; the correct word would be 'dress' or 'gown'. Semantically inappropriate: 'System' cannot refer to a physical ball used in sports; the correct word is 'ball'.",
  "target_word": "system"
}
```

---

## sense 14001, level 7

#### Pack A
### Level 7 (sense 14001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "These bugs talk to your body's defense system, which is your immunity.",
      "is_correct": true
    },
    {
      "text": "Sometimes, the defense system gets confused.",
      "is_correct": true
    },
    {
      "text": "Furthermore, these systems often process vast amounts of sensitive data, raising valid concerns about privacy and security.",
      "is_correct": true
    },
    {
      "text": "The computer system are very slow today.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: The singular noun 'system' requires the singular verb 'is', not the plural verb 'are'."
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Students tested the solar system model they built in science class.",
      "is_correct": true
    },
    {
      "text": "The weather system brought heavy rain and strong winds yesterday.",
      "is_correct": true
    },
    {
      "text": "A living plant is an open system.",
      "is_correct": true
    },
    {
      "text": "The solar system are very large and contains many planets.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: The singular subject 'system' requires the singular verb 'is', not the plural verb 'are'."
    }
  ]
}
```

#### Pack B
### Level 7 (sense 14001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "These bugs talk to your body's defense system, which is your immunity.",
      "is_correct": true
    },
    {
      "text": "The engineers designed three new computer system for the office.",
      "is_correct": false,
      "error_description": "The noun 'system' is a countable noun and must be pluralized as 'systems' when referring to more than one, such as after the number 'three'."
    },
    {
      "text": "Furthermore, these systems often process vast amounts of sensitive data, raising valid concerns about privacy and security.",
      "is_correct": true
    },
    {
      "text": "Sometimes, the defense system gets confused.",
      "is_correct": true
    }
  ]
}
```

---
