# Pairwise review pack 05

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


## sense 14024, level 3

#### Pack A
### Level 3 (sense 14024, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "My uncle came up with some ___ scheme to build a rocket ship in his backyard.",
  "original_sentence": "My uncle came up with some nutty scheme to build a rocket ship in his backyard.",
  "correct_answer": "nutty",
  "options": [
    "nutty",
    "expensive",
    "brief",
    "logical"
  ],
  "explanation": "Correct: fits the context of an eccentric or crazy scheme.",
  "distractor_tags": {},
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
}
```

#### Pack B
### Level 3 (sense 14024, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "My uncle came up with some ___ scheme to build a rocket ship in his garage.",
  "original_sentence": "My uncle came up with some nutty scheme to build a rocket ship in his garage.",
  "correct_answer": "nutty",
  "options": [
    "bureaucratic",
    "thick",
    "edible",
    "nutty"
  ],
  "explanation": "correct answer: fits the context of a crazy or eccentric plan.",
  "distractor_tags": {},
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "They were laughing about the ___ costumes people wore to the party.",
  "original_sentence": "They were laughing about the nutty costumes people wore to the party.",
  "correct_answer": "nutty",
  "options": [
    "sturdy",
    "fatuous",
    "delicious",
    "nutty"
  ],
  "explanation": "the correct target word meaning crazy or eccentric.",
  "distractor_tags": {},
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
}
```

---

## sense 14024, level 6

#### Pack A
### Level 6 (sense 14024, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He wrote a nutty resignation letter that was professional and polite.",
      "is_correct": false
    },
    {
      "text": "She followed the nutty traffic laws to ensure she arrived safely.",
      "is_correct": false
    },
    {
      "text": "The scientist presented a nutty formula for calculating the area of a circle.",
      "is_correct": false
    },
    {
      "text": "That sounds like a nutty scheme, but it actually worked out surprisingly well in the end.",
      "is_correct": true
    }
  ],
  "explanation": "Inappropriate: Mathematical formulas are precise and objective; 'nutty' implies irrationality or craziness, which clashes with scientific rigor. Inappropriate: Traffic laws are established regulations meant to be followed for safety; describing them as 'nutty' (crazy) contradicts the serious intent of compliance. Inappropriate: 'Nutty' implies eccentricity or insanity, which is mutually exclusive with being 'professional and polite'.",
  "target_word": "nutty"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "His behavior became increasingly nutty after he drank three cups of strong coffee.",
      "is_correct": true
    },
    {
      "text": "She felt nutty after running the marathon and needed some water.",
      "is_correct": false
    },
    {
      "text": "The nutty table was made of solid oak and lasted for generations.",
      "is_correct": false
    },
    {
      "text": "The nutty weather forecast predicted rain for the entire weekend.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic error: 'nutty' means crazy or eccentric when describing behavior or ideas, not the material composition of furniture. Semantic error: 'nutty' does not describe physical exhaustion or thirst; it describes mental state or eccentricity. Collocational/Semantic error: Weather forecasts are not described as 'nutty' (crazy/eccentric) in standard usage; they are accurate or inaccurate.",
  "target_word": "nutty"
}
```

#### Pack B
### Level 6 (sense 14024, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The accountant calculated the nutty taxes with extreme precision and strict adherence to the law.",
      "is_correct": false
    },
    {
      "text": "The sci-fi movie started normally before it got completely nutty.",
      "is_correct": true
    },
    {
      "text": "She wore a nutty dress to the formal gala because it was a highly conventional and elegant silk gown.",
      "is_correct": false
    },
    {
      "text": "The quiet library is a nutty environment where patrons read in complete silence.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic: 'nutty' means crazy or eccentric, which contradicts the context of strict, precise, and lawful tax calculation. semantic: 'nutty' means eccentric or crazy, which directly contradicts the description of the dress as conventional and elegant. pragmatic: a quiet, silent library is the opposite of a crazy, eccentric, or insane environment.",
  "target_word": "nutty"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She carefully folded the nutty piece of paper into a neat little airplane.",
      "is_correct": false
    },
    {
      "text": "The judge sentenced the criminal to ten years in prison for his nutty and highly calculated financial fraud.",
      "is_correct": false
    },
    {
      "text": "Why do you always come up with such nutty adventures?",
      "is_correct": true
    },
    {
      "text": "The solemn priest delivered a nutty and deeply moving eulogy that made everyone cry.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic: 'highly calculated' contradicts the eccentric or crazy meaning of 'nutty'. semantic: an inanimate object like paper cannot possess the human trait of being crazy or eccentric. pragmatic: the serious, emotional context of a 'deeply moving eulogy' clashes with the absurd or silly connotations of 'nutty'.",
  "target_word": "nutty"
}
```

---

## sense 14033, level 1

#### Pack A
### Level 1 (sense 14033, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "small",
  "pronunciation": "smawl",
  "ipa": "/smɔːl/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "small",
    "smell",
    "shall",
    "stall"
  ],
  "correct_answer": "small",
  "explanation": "Correct: matches the target word.",
  "distractor_explanations": {
    "smell": "Minimal pair: differs only in the final consonant /l/ vs /m/.",
    "shall": "Rhyme: shares the same vowel and final consonant /æl/, but starts with a different consonant cluster.",
    "stall": "Rhyme: shares the same vowel and final consonant /ɔːl/ (in some accents) or /æl/, creating auditory confusion."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14033, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "small",
  "pronunciation": "smawl",
  "ipa": "/smɔːl/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "smell",
    "small",
    "shawl",
    "smile"
  ],
  "correct_answer": "small",
  "explanation": "correct word: the exact target word heard in the audio.",
  "distractor_explanations": {
    "smell": "minimal pair: differs only in the vowel sound /ɔː/ vs /ɛ/.",
    "smile": "minimal pair: differs only in the vowel sound /ɔː/ vs /aɪ/.",
    "shawl": "rhyme: shares the same /ɔːl/ ending and syllable count but starts with a different consonant cluster /ʃ/ vs /sm/."
  },
  "distractor_source": "llm"
}
```

---

## sense 14033, level 3

#### Pack A
### Level 3 (sense 14033, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Every night, the ___child goes to bed early.",
  "original_sentence": "Every night, the small child goes to bed early.",
  "correct_answer": "small",
  "options": [
    "small",
    "fast",
    "loud",
    "heavy"
  ],
  "explanation": "Correct: 'small' correctly describes the size of the child, fitting the context of going to bed early.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "small "
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He had a ___wooden toy horse.",
  "original_sentence": "He had a small wooden toy horse.",
  "correct_answer": "small",
  "options": [
    "small",
    "colossal",
    "minuscule",
    "loud"
  ],
  "explanation": "correct word: fits the context of describing the physical size of a toy horse.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "small "
}
```

#### Pack B
### Level 3 (sense 14033, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Every night, the ___ child goes to bed early.",
  "original_sentence": "Every night, the small child goes to bed early.",
  "correct_answer": "small",
  "options": [
    "loud",
    "delicious",
    "ancient",
    "small"
  ],
  "explanation": "Correct: fits the context of a child's size relative to average.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "small"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He had a ___ wooden toy horse.",
  "original_sentence": "He had a small wooden toy horse.",
  "correct_answer": "small",
  "options": [
    "ancient",
    "small",
    "loud",
    "heavy"
  ],
  "explanation": "Correct: fits the context of a toy horse being diminutive in size.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "small"
}
```

---

## sense 14033, level 6

#### Pack A
### Level 6 (sense 14033, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The small ocean covered the entire horizon.",
      "is_correct": false
    },
    {
      "text": "They built small walls.",
      "is_correct": true
    },
    {
      "text": "The small sun provided heat to the solar system.",
      "is_correct": false
    },
    {
      "text": "He made a small decision to change his entire life path.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: Oceans are inherently vast; describing an ocean as 'small' contradicts general world knowledge unless used metaphorically, which is not supported by the literal sentence structure. Semantically inappropriate: Decisions that change life paths are significant/major; describing such a pivotal choice as 'small' creates a logical contradiction in magnitude. Factually inappropriate: The Sun is a massive star; describing it as 'small' is factually incorrect in an astronomical context.",
  "target_word": "small"
}
```

#### Pack B
### Level 6 (sense 14033, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The small ocean stretched out for thousands of miles.",
      "is_correct": false
    },
    {
      "text": "The small giant towered over the rest of the basketball team.",
      "is_correct": false
    },
    {
      "text": "Small animals can hide.",
      "is_correct": true
    },
    {
      "text": "The small elephant easily lifted the heavy car with its trunk.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: an elephant described as 'small' would not realistically possess the physical strength to lift a heavy car. Semantically inappropriate: an ocean is inherently massive; describing it as 'small' contradicts the fundamental definition of the word. Semantically inappropriate: 'small' and 'giant' are direct antonyms in the context of physical size, creating a logical contradiction.",
  "target_word": "Small "
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The small ocean covers more than seventy percent of the Earth's surface.",
      "is_correct": false
    },
    {
      "text": "The small skyscraper towered over the city at over a thousand feet tall.",
      "is_correct": false
    },
    {
      "text": "He ate a small feast consisting of fifty different dishes.",
      "is_correct": false
    },
    {
      "text": "They built small walls.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: an ocean is by definition a vast body of water, making 'small' semantically contradictory. pragmatic: a feast implies a large, abundant meal, which pragmatically contradicts the modifier 'small'. pragmatic: a skyscraper is inherently a very tall and large building, making 'small' pragmatically inappropriate.",
  "target_word": "small "
}
```

---

## sense 14100, level 3

#### Pack A
### Level 3 (sense 14100, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "correct_answer": "ascend",
  "options": [
    "remain",
    "vanish",
    "ascend",
    "descend"
  ],
  "explanation": "Correct: Fits the context of moving upward against gravity.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```

#### Pack B
### Level 3 (sense 14100, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "correct_answer": "ascend",
  "options": [
    "board",
    "ascend",
    "plummet",
    "hoist"
  ],
  "explanation": "Correct: fits the context of aerodynamic lift enabling upward movement.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She watched her team ___ to the top of the league standings.",
  "original_sentence": "She watched her team ascend to the top of the league standings.",
  "correct_answer": "ascend",
  "options": [
    "sprout",
    "fall",
    "ascend",
    "elevate"
  ],
  "explanation": "correct: appropriately describes moving upward in a competitive ranking",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```

---

## sense 14100, level 4

#### Pack A
### Level 4 (sense 14100, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "As an airplane ___, the air becomes less dense, meaning there are fewer air molecules.",
  "original_sentence": "As an airplane ascends, the air becomes less dense, meaning there are fewer air molecules.",
  "correct_answer": "ascends",
  "base_form": "ascend",
  "form_label": "third-person singular present",
  "options": [
    "ascend",
    "ascends",
    "ascending",
    "ascended"
  ],
  "explanation": "This third-person singular present form agrees with the singular subject 'airplane'.",
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascends"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Birds were seen ___ high above the trees as the storm approached.",
  "original_sentence": "Birds were seen ascending high above the trees as the storm approached.",
  "correct_answer": "ascending",
  "base_form": "ascend",
  "form_label": "present participle",
  "options": [
    "ascended",
    "ascending",
    "ascend",
    "ascends"
  ],
  "explanation": "present participle is required after the passive verb of perception to indicate ongoing active action",
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascending"
}
```

#### Pack B
### Level 4 (sense 14100, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "As an airplane ___, the air becomes less dense, meaning there are fewer air molecules.",
  "original_sentence": "As an airplane ascends, the air becomes less dense, meaning there are fewer air molecules.",
  "correct_answer": "ascends",
  "base_form": "ascend",
  "form_label": "third-person singular present",
  "options": [
    "ascend",
    "ascended",
    "ascending",
    "ascends"
  ],
  "explanation": "third-person singular present agrees with the singular subject 'airplane'",
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascends"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The brave knight started to ___ the winding stone stairs of the old tower.",
  "original_sentence": "The brave knight started to ascend the winding stone stairs of the old tower.",
  "correct_answer": "ascend",
  "base_form": "ascend",
  "form_label": "base form",
  "options": [
    "ascend",
    "ascended",
    "ascending",
    "ascends"
  ],
  "explanation": "bare infinitive is required after 'to'",
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```

---

## sense 14100, level 6

#### Pack A
### Level 6 (sense 14100, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The sun will ascend at midnight to provide light for the nocturnal animals.",
      "is_correct": false
    },
    {
      "text": "The heavy iron anvil will naturally ascend to the ceiling when dropped in a vacuum.",
      "is_correct": false
    },
    {
      "text": "We watched the hot air balloon slowly ascend into the morning sky.",
      "is_correct": true
    },
    {
      "text": "The submarine was designed to ascend deep into the ocean floor to explore the dark trenches.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: heavy objects fall due to gravity; they do not naturally move upward. semantic: ascending means moving upward, which contradicts moving down into the ocean floor. pragmatic: the sun does not rise at midnight, making this factually and contextually impossible.",
  "target_word": "ascend"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The small drone ascended quickly when he pushed the control stick forward.",
      "is_correct": true
    },
    {
      "text": "The liquid will ascend into a solid state when placed in the freezer.",
      "is_correct": false
    },
    {
      "text": "He tried to ascend the mathematical equation by adding more variables.",
      "is_correct": false
    },
    {
      "text": "The miners had to ascend deeper into the earth to find the rare minerals.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'ascend' refers to physical upward movement, not the phase change of a liquid to a solid semantic: 'ascend' cannot take an abstract concept like an 'equation' as a direct object for upward movement pragmatic: 'ascend' means to move upward, which directly contradicts the directional phrase 'deeper into the earth'",
  "target_word": "ascended"
}
```

#### Pack B
### Level 6 (sense 14100, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "We watched the hot air balloon slowly ascend into the bright morning sky.",
      "is_correct": true
    },
    {
      "text": "The temperature will ascend to 30 degrees by noon.",
      "is_correct": false
    },
    {
      "text": "The student tried to ascend the difficult math problem during the exam.",
      "is_correct": false
    },
    {
      "text": "She decided to ascend her new dress before the party.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic mismatch: 'Ascend' implies physical or hierarchical upward movement, not solving abstract intellectual problems. Valency error: 'Ascend' is intransitive or takes a path/location object, not a direct object like clothing to be worn. Register/Collocation error: While physically accurate, 'rise' is the standard lexical choice for temperature; 'ascend' is overly formal and unnatural here.",
  "target_word": "ascend"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "ascend",
  "relation": "antonym",
  "options": [
    "mount",
    "rise",
    "descend",
    "climb"
  ],
  "correct_answer": "descend",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To move upward or to a higher position.",
      "explanation": "antonym: to move downward or to a lower position"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The pilot prepared the jet to ascend above the thick layer of clouds.",
      "is_correct": true
    },
    {
      "text": "He decided to ascend his opinion during the heated debate.",
      "is_correct": false
    },
    {
      "text": "The water began to ascend the dry sponge rapidly.",
      "is_correct": false
    },
    {
      "text": "The student tried to ascend the complex mathematical equation to find the solution.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'ascend' refers to physical or metaphorical rising in rank/position, not solving or processing abstract logical structures. Collocationally incorrect: one does not 'ascend' an opinion; one might 'assert' or 'express' it. 'Ascend' requires a path, height, or rank as its object or direction. Semantically imprecise: while water moves up, the specific verb for liquid moving into a porous material is 'absorb' or 'wick'; 'ascend' implies self-propelled or aerodynamic upward movement.",
  "target_word": "ascend"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "ascend",
  "relation": "antonym",
  "options": [
    "soar",
    "climb",
    "rise",
    "descend"
  ],
  "correct_answer": "descend",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To move upward or to a higher position.",
      "explanation": "antonym: to move downward or to a lower position"
    }
  }
}
```

---

## sense 14189, level 4

#### Pack A
### Level 4 (sense 14189, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Our school is becoming ___ advanced by introducing new computers in every classroom this semester.",
  "original_sentence": "Our school is becoming technologically advanced by introducing new computers in every classroom this semester.",
  "correct_answer": "technologically",
  "base_form": "technologically",
  "form_label": "base form adverb",
  "options": [
    "technologically",
    "technological",
    "technologist",
    "technology"
  ],
  "explanation": "adverb modifying the adjective 'advanced'",
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "Our school is becoming ___ advanced by introducing new computers in every classroom this semester.",
  "original_sentence": "Our school is becoming technologically advanced by introducing new computers in every classroom this semester.",
  "required_pos": "adverb",
  "options": [
    "technologicity",
    "technologicalness",
    "technologically",
    "technologially"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the correct adverb modifying the adjective 'advanced'"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Some traditional crafts are changing ___ as artisans begin using digital tools.",
  "original_sentence": "Some traditional crafts are changing technologically as artisans begin using digital tools.",
  "correct_answer": "technologically",
  "base_form": "technological",
  "form_label": "adverb",
  "options": [
    "technological",
    "technology",
    "technologist",
    "technologically"
  ],
  "explanation": "adverb modifying the verb 'changing'",
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "Some traditional crafts are changing ___ as artisans begin using digital tools.",
  "original_sentence": "Some traditional crafts are changing technologically as artisans begin using digital tools.",
  "required_pos": "adverb",
  "options": [
    "technologially",
    "technologically",
    "technologicaly",
    "technologisticly"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverbial form modifying the verb"
    }
  }
}
```

#### Pack B
### Level 4 (sense 14189, difficulty None)
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "The museum created a ___ immersive experience that lets visitors explore ancient ruins in virtual reality.",
  "original_sentence": "The museum created a technologically immersive experience that lets visitors explore ancient ruins in virtual reality.",
  "required_pos": "adverb",
  "options": [
    "technologive",
    "technologation",
    "technologically",
    "technologer"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard adverbial derivation modifying the adjective"
    }
  }
}
```

---

## sense 14189, level 6

#### Pack A
### Level 6 (sense 14189, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The ancient philosopher argued that the human soul is technologically pure and cannot be corrupted by physical desires.",
      "is_correct": false
    },
    {
      "text": "She tasted the soup and realized it was technologically too salty for her liking.",
      "is_correct": false
    },
    {
      "text": "Our school library has become much more technologically equipped since they installed dozens of modern computers.",
      "is_correct": true
    },
    {
      "text": "The emotional support dog was technologically comforting to the patient after the tragic accident.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'technologically' relates to machines and equipment, which is pragmatically inappropriate for describing the spiritual purity of a soul semantic: 'technologically' cannot modify sensory perception or the physical taste of food pragmatic: 'technologically' implies the use of machines, which contradicts the organic and emotional nature of a support dog",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "manually",
    "scientifically",
    "mechanically",
    "digitally"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment",
      "explanation": "in a way done by hand rather than by machines, directly opposing the sense of using technology or equipment"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She baked the cake technologically by mixing flour, sugar, and eggs in a wooden bowl with a spoon.",
      "is_correct": false
    },
    {
      "text": "Although the region was isolated, it was surprisingly well-connected technologically thanks to satellite internet.",
      "is_correct": true
    },
    {
      "text": "The emotional healing process between the two friends progressed technologically as they shared their deepest feelings.",
      "is_correct": false
    },
    {
      "text": "The ancient oak tree grew technologically over the centuries, developing deep roots and a wide canopy.",
      "is_correct": false
    }
  ],
  "explanation": "technologically is semantically inappropriate here because trees grow through biological processes, not through the application of machines or equipment. technologically is pragmatically inappropriate because mixing ingredients in a wooden bowl by hand describes a manual, non-technological process, creating a direct contradiction. technologically is semantically mismatched because emotional healing and sharing feelings are interpersonal, psychological processes, not ones driven by machines or technical equipment.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "scientifically",
    "mechanically",
    "digitally",
    "primitively"
  ],
  "correct_answer": "primitively",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment",
      "explanation": "antonym of the target sense: in a primitive, non-technological manner"
    }
  }
}
```

#### Pack B
### Level 6 (sense 14189, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The baby slept technologically through the entire night without waking up.",
      "is_correct": false
    },
    {
      "text": "The ancient stone wall stood technologically firm against the wind for centuries.",
      "is_correct": false
    },
    {
      "text": "She felt technologically happy after receiving the good news from her friend.",
      "is_correct": false
    },
    {
      "text": "Many young people are becoming technologically skilled because they use smartphones every single day.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: sleeping is a biological function, not a process involving technology or machines. Semantically inappropriate: emotions like happiness are internal psychological states, not achieved through technological means. Semantically inappropriate: structural integrity of ancient masonry is a physical/engineering property, not a result of modern technology or digital equipment.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "digitally",
    "electronically",
    "automatically",
    "manually"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: done by hand rather than by machine or technology"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The baby slept technologically through the entire night without waking up.",
      "is_correct": false
    },
    {
      "text": "The library was upgraded technologically to help students access online books and archives.",
      "is_correct": true
    },
    {
      "text": "She felt technologically sad after hearing the bad news.",
      "is_correct": false
    },
    {
      "text": "The flower bloomed technologically in the early spring sunlight.",
      "is_correct": false
    }
  ],
  "explanation": "Inappropriate: Sleeping is a biological process and cannot be performed 'in a way that relates to technology'. Inappropriate: Emotions like sadness are internal psychological states and are not influenced by or related to the use of machines or equipment. Inappropriate: Natural botanical processes like blooming occur biologically, not through technological means or equipment.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "automatically",
    "manually",
    "electronically",
    "digitally"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: done by hand rather than by machine or technology"
    }
  }
}
```

---
