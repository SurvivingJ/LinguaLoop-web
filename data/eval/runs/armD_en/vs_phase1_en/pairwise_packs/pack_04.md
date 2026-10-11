# Pairwise review pack 04

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


## sense 14024, level 6

#### Pack A
### Level 6 (sense 14024, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "That plan sounds completely nutty, but somehow it actually worked in the end.",
      "is_correct": true
    },
    {
      "text": "The chef prepared a nutty soup using only boiled water and plain crackers.",
      "is_correct": false
    },
    {
      "text": "She wore a very nutty dress to the formal gala that perfectly matched her elegant shoes.",
      "is_correct": false
    },
    {
      "text": "The math teacher gave a nutty explanation that was perfectly logical and easy for everyone to follow.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'nutty' implies a flavor of nuts or craziness, neither of which applies to a bland soup made of water and crackers. Semantically inappropriate: 'nutty' means crazy or eccentric, which clashes with the context of a 'formal gala' and an outfit that 'perfectly matched' elegant attire. Semantically inappropriate: 'nutty' means insane or irrational, which directly contradicts the description of the explanation being 'perfectly logical'.",
  "target_word": "nutty"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "After running the marathon, his legs felt completely nutty and exhausted.",
      "is_correct": false
    },
    {
      "text": "She wore a beautiful, nutty silk dress to the elegant formal gala.",
      "is_correct": false
    },
    {
      "text": "The chef added a nutty pinch of salt to the boiling water to make the pasta taste better.",
      "is_correct": false
    },
    {
      "text": "We spent the afternoon listening to her nutty theories about time travel.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: 'Nutty' means crazy or eccentric, not 'small' or 'measured', making it illogical for describing a pinch of salt. semantic: 'Nutty' refers to mental eccentricity or craziness, not physical fatigue or muscle soreness. semantic: 'Nutty' means insane or bizarre, which contradicts the context of wearing a 'beautiful' and 'elegant' dress.",
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

## sense 14033, level 3

#### Pack A
### Level 3 (sense 14033, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Every night, the ___ child goes to bed early.",
  "original_sentence": "Every night, the small child goes to bed early.",
  "correct_answer": "small",
  "options": [
    "final",
    "small",
    "ancient",
    "wooden"
  ],
  "explanation": "Correct: fits the context of describing a young child's physical size.",
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
    "small",
    "rapid",
    "fragile",
    "heavy"
  ],
  "explanation": "Correct: fits the context of describing the physical dimensions of a child's toy.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "small"
}
```

#### Pack B
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

---

## sense 14033, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 14033, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They built small walls.",
      "is_correct": true
    },
    {
      "text": "He felt very small because he was extremely arrogant.",
      "is_correct": false
    },
    {
      "text": "The small galaxy contained trillions of stars.",
      "is_correct": false
    },
    {
      "text": "The small ocean covered the entire planet.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: oceans are inherently massive bodies of water and cannot logically be described as small. Semantically inappropriate: arrogance typically correlates with feeling large or superior, not small; 'small' in this context usually implies humility or shame. Pragmatically inappropriate: galaxies are astronomically vast structures, making the adjective 'small' contextually and pragmatically jarring.",
  "target_word": "small"
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
    "ascend",
    "hover",
    "descend",
    "glide"
  ],
  "explanation": "Correct: 'ascend' correctly completes the sentence, meaning the machines move upward into the air.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The small drone ___ quickly to capture a wide aerial view of the park.",
  "original_sentence": "The small drone ascends quickly to capture a wide aerial view of the park.",
  "correct_answer": "ascends",
  "options": [
    "hovers",
    "ascends to",
    "ascends",
    "descends"
  ],
  "explanation": "Correct: third-person singular present tense matching the singular subject 'drone'.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascends"
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
  "explanation": "third-person singular present form is required for subject-verb agreement with the singular noun 'airplane'",
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascends"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "ascend",
  "sentence_with_blank": "As an airplane ___, the air becomes less dense, meaning there are fewer air molecules.",
  "original_sentence": "As an airplane ascends, the air becomes less dense, meaning there are fewer air molecules.",
  "required_pos": "verb",
  "options": [
    "ascendity",
    "ascendage",
    "ascendous",
    "ascends"
  ],
  "correct_answer": "ascends",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the required third-person singular present verb form"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She watched the elevator doors close as her friends ___ to the top floor.",
  "original_sentence": "She watched the elevator doors close as her friends ascended to the top floor.",
  "correct_answer": "ascended",
  "base_form": "ascend",
  "form_label": "past simple",
  "options": [
    "ascend",
    "ascending",
    "ascends",
    "ascended"
  ],
  "explanation": "past simple form required by the past-tense narrative context",
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascended"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "ascend",
  "sentence_with_blank": "She watched the elevator doors close as her friends ___ to the top floor.",
  "original_sentence": "She watched the elevator doors close as her friends ascended to the top floor.",
  "required_pos": "noun",
  "options": [
    "ascendal",
    "ascent",
    "ascendure",
    "ascendage"
  ],
  "correct_answer": "ascent",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established nominalisation meaning the act of moving upward"
    }
  }
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
      "text": "The heavy iron anchor began to ascend rapidly the moment it was thrown overboard into the sea.",
      "is_correct": false
    },
    {
      "text": "The diver watched her oxygen levels ascend as she swam deeper into the dark, crushing depths of the ocean.",
      "is_correct": false
    },
    {
      "text": "The hikers began to ascend the steep mountain trail as the morning sun broke through the clouds.",
      "is_correct": true
    },
    {
      "text": "He tried to ascend the liquid coffee into his mouth, but it just spilled all over his shirt.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: oxygen levels physically decrease, not ascend, as a diver goes deeper underwater. Semantically inappropriate: 'ascend' is not used to describe the physical act of drinking or consuming a liquid. Semantically inappropriate: a heavy iron anchor sinks (descends) when thrown into the sea; it defies physics for it to ascend.",
  "target_word": "ascend"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "ascend",
  "relation": "antonym",
  "options": [
    "advance",
    "proceed",
    "traverse",
    "descend"
  ],
  "correct_answer": "descend",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To move upward or to a higher position.",
      "explanation": "antonym: to move downward is the opposite of moving upward"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The river ascends through the valley, flowing gently toward the ocean.",
      "is_correct": false
    },
    {
      "text": "The path gradually ascends through the dense forest until you reach the rocky summit.",
      "is_correct": true
    },
    {
      "text": "He tried to ascend his knowledge of mathematics by reading the textbook once.",
      "is_correct": false
    },
    {
      "text": "The chef decided to ascend the soup by adding more salt and pepper to enhance its flavor.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'ascend' refers to physical upward movement, not improving or enhancing food. Semantically inappropriate: 'ascend' is not used for abstract improvement of knowledge; 'expand' or 'deepen' would be correct. Semantically inappropriate: rivers flow downward due to gravity; 'ascends' contradicts the natural direction of water flow and the phrase 'toward the ocean.'",
  "target_word": "ascends"
}
```

---

## sense 14189, level 1

#### Pack A
### Level 1 (sense 14189, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "pronunciation": "tek-nuh-loj-i-kuh-lee",
  "ipa": "/ˌtɛknəˈlɒdʒɪkəli/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "technologically",
    "theologically",
    "chronologically",
    "astrologically"
  ],
  "correct_answer": "technologically",
  "explanation": "Correct: the target word itself, matching the spoken audio.",
  "distractor_explanations": {
    "chronologically": "Phonetic distractor: same stress pattern and syllable count, differing only in the initial consonant cluster (/tɛk/ vs /krɒ/).",
    "theologically": "Phonetic distractor: same stress pattern and syllable count, differing only in the initial vowel and consonant sounds (/tɛk.nə/ vs /θiː.ə/).",
    "astrologically": "Phonetic distractor: same stress pattern and syllable count, differing only in the initial consonant cluster (/tɛk/ vs /æs/)."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14189, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "pronunciation": "tek-nuh-loj-i-kuh-lee",
  "ipa": "/ˌtɛknəˈlɒdʒɪkəli/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "technologically",
    "chronologically",
    "theologically",
    "mythologically"
  ],
  "correct_answer": "technologically",
  "explanation": "correct: this is the target word spoken aloud",
  "distractor_explanations": {
    "chronologically": "near-minimal pair: differs only in the initial consonant cluster /kr/ versus /t/ and the following vowel sound",
    "theologically": "same-stress same-syllable-count rhyme: shares the exact rhythm and final four syllables, differing only in the initial consonant",
    "mythologically": "same-stress same-syllable-count rhyme: shares the exact rhythm and final four syllables, differing only in the initial consonant"
  },
  "distractor_source": "llm"
}
```

---

## sense 14189, level 3

#### Pack A
### Level 3 (sense 14189, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "However, the industry is increasingly seeing a shift towards more consolidated and ___ advanced agricultural operations, especially in larger estates, aiming for increased efficiency and yield.",
  "original_sentence": "However, the industry is increasingly seeing a shift towards more consolidated and technologically advanced agricultural operations, especially in larger estates, aiming for increased efficiency and yield.",
  "correct_answer": "technologically",
  "options": [
    "technologically",
    "ecologically",
    "psychologically",
    "bureaucratically"
  ],
  "explanation": "correct: fits the context of using machines and equipment for increased agricultural efficiency",
  "distractor_tags": {},
  "word_definition": "in a way that relates to technology or using machines and equipment",
  "target_word": "technologically"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Some traditional industries have struggled because they have not evolved ___ over the past decade.",
  "original_sentence": "Some traditional industries have struggled because they have not evolved technologically over the past decade.",
  "correct_answer": "technologically",
  "options": [
    "technologically",
    "retroactively",
    "biologically",
    "chronologically"
  ],
  "explanation": "Correct: fits the context of industries advancing through the use of machines and equipment.",
  "distractor_tags": {},
  "word_definition": "in a way that relates to technology or using machines and equipment",
  "target_word": "technologically"
}
```

#### Pack B
### Level 3 (sense 14189, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "However, the industry is increasingly seeing a shift towards more consolidated and ___ advanced agricultural operations, especially in larger estates, aiming for increased efficiency and yield.",
  "original_sentence": "However, the industry is increasingly seeing a shift towards more consolidated and technologically advanced agricultural operations, especially in larger estates, aiming for increased efficiency and yield.",
  "correct_answer": "technologically",
  "options": [
    "bureaucratically",
    "technologically",
    "anarchically",
    "ecologically"
  ],
  "explanation": "Correct: fits the context of agricultural operations advancing through the use of modern machines and equipment.",
  "distractor_tags": {},
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She explained how the company grew ___ over the past decade by investing in research.",
  "original_sentence": "She explained how the company grew technologically over the past decade by investing in research.",
  "correct_answer": "technologically",
  "options": [
    "technique",
    "technological",
    "financially",
    "technologically"
  ],
  "explanation": "Correct: The adverb 'technologically' correctly modifies the verb 'grew', indicating the specific domain of the company's development.",
  "distractor_tags": {},
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```

---

## sense 14189, level 4

#### Pack A
### Level 4 (sense 14189, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The new factory is ___ equipped to produce twice as many items while using less energy.",
  "original_sentence": "The new factory is technologically equipped to produce twice as many items while using less energy.",
  "correct_answer": "technologically",
  "base_form": "technologically",
  "form_label": "adverb",
  "options": [
    "technologically",
    "technologists",
    "technology",
    "technological"
  ],
  "explanation": "adverb required to modify the participle 'equipped'",
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "The new factory is ___ equipped to produce twice as many items while using less energy.",
  "original_sentence": "The new factory is technologically equipped to produce twice as many items while using less energy.",
  "required_pos": "adverb",
  "options": [
    "technologement",
    "technologically",
    "technologive",
    "technologer"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverbial form modifying the participle 'equipped'"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The museum featured exhibits showing how societies evolved ___ from simple tools to computers.",
  "original_sentence": "The museum featured exhibits showing how societies evolved technologically from simple tools to computers.",
  "correct_answer": "technologically",
  "base_form": "technologically",
  "form_label": "adverb",
  "options": [
    "technologists",
    "technology",
    "technological",
    "technologically"
  ],
  "explanation": "adverb is required to modify the verb 'evolved'",
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "The museum featured exhibits showing how societies evolved ___ from simple tools to computers.",
  "original_sentence": "The museum featured exhibits showing how societies evolved technologically from simple tools to computers.",
  "required_pos": "adverb",
  "options": [
    "technologically",
    "technologicalment",
    "technologiness",
    "technologiment"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverbial form built from the adjective"
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
      "text": "She technologically felt a deep sense of sorrow when she heard the tragic news about her friend.",
      "is_correct": false
    },
    {
      "text": "The baker technologically kneaded the dough by hand, relying entirely on his grandmother's traditional recipes.",
      "is_correct": false
    },
    {
      "text": "The ancient ruins were technologically preserved by the local historians who refused to use any modern tools.",
      "is_correct": false
    },
    {
      "text": "They have updated their equipment to remain technologically competitive in a fast-moving market.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: preserving something by refusing modern tools contradicts the definition of doing something in a way that relates to technology. Semantically inappropriate: 'technologically' modifies machines and equipment, not internal human emotions or psychological states. Pragmatically inappropriate: kneading dough by hand using traditional recipes is the exact opposite of using machines and technological equipment.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "mechanically",
    "digitally",
    "scientifically",
    "manually"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: done by hand rather than using machines or equipment"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The ancient ruins were built technologically by hand using only simple stones and mud.",
      "is_correct": false
    },
    {
      "text": "The soup tasted technologically delicious because the chef used fresh, organic ingredients.",
      "is_correct": false
    },
    {
      "text": "He felt technologically sad after reading the emotional final chapter of the novel.",
      "is_correct": false
    },
    {
      "text": "Engineers are working hard to ensure the new vehicles are fully sound both mechanically and technologically.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Technologically' refers to machines and equipment, which does not logically explain the taste of fresh, organic food. Semantically inappropriate: 'Technologically' describes mechanical or digital processes, not human emotions or literary experiences. Semantically inappropriate: 'Technologically' implies the use of advanced machinery or modern equipment, which directly contradicts 'by hand' and 'simple stones'.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "electronically",
    "scientifically",
    "manually",
    "industrially"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: by hand rather than using machines or technology"
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

---
