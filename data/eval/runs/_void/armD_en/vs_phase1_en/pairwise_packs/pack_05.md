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
  "form_label": "present third-person singular",
  "options": [
    "ascends",
    "ascending",
    "ascended",
    "ascend"
  ],
  "explanation": "present third-person singular form agreeing with the singular subject 'airplane'",
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
  "required_pos": "noun",
  "options": [
    "ascendure",
    "ascent",
    "ascendal",
    "ascendage"
  ],
  "correct_answer": "ascent",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established nominalisation of ascend"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Birds can ___ effortlessly by riding warm currents of air.",
  "original_sentence": "Birds can ascend effortlessly by riding warm currents of air.",
  "correct_answer": "ascend",
  "base_form": "ascend",
  "form_label": "bare infinitive",
  "options": [
    "ascending",
    "ascends",
    "ascended",
    "ascend"
  ],
  "explanation": "bare infinitive required after the modal verb 'can'",
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "ascend",
  "sentence_with_blank": "Birds can ___ effortlessly by riding warm currents of air.",
  "original_sentence": "Birds can ascend effortlessly by riding warm currents of air.",
  "required_pos": "noun",
  "options": [
    "ascent",
    "ascendity",
    "ascendure",
    "ascendage"
  ],
  "correct_answer": "ascent",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established nominalisation for the physical act of moving upward"
    }
  }
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

---

## sense 14100, level 6

#### Pack A
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
      "text": "The chef will ascend the flour and sugar together to make the batter.",
      "is_correct": false
    },
    {
      "text": "She tried to ascend the liquid into a thick, solid block of ice.",
      "is_correct": false
    },
    {
      "text": "He used a hammer to ascend the nail into the wooden board.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'ascend' describes upward motion, not a phase-change transformation of a substance. Semantically inappropriate: 'ascend' means to move upward, not to mix or combine ingredients. Semantically inappropriate: 'ascend' cannot describe the action of driving a nail; the correct verb would be 'drive' or 'hammer.'",
  "target_word": "ascend"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He will ascend the math problem by using a new formula.",
      "is_correct": false
    },
    {
      "text": "They successfully ascended the stone steps leading to the ancient temple.",
      "is_correct": true
    },
    {
      "text": "The students had to ascend their textbooks to the top shelf in the library.",
      "is_correct": false
    },
    {
      "text": "The chef will ascend the soup by adding a pinch of salt.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: 'ascend' means to move oneself or an inanimate object upward, not to place an object on a shelf (which requires 'lift' or 'put'). Incorrect: 'ascend' refers to physical upward movement, not the mental process of solving or figuring out a problem. Incorrect: 'ascend' cannot be used to mean improving or enhancing the flavor of food; the correct verb would be 'season' or 'enhance'.",
  "target_word": "ascended"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "ascend",
  "relation": "antonym",
  "options": [
    "approach",
    "traverse",
    "descend",
    "proceed"
  ],
  "correct_answer": "descend",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To move upward or to a higher position.",
      "explanation": "antonym: to move downward is the direct opposite of moving upward"
    }
  }
}
```

#### Pack B
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
    "theologically",
    "biologically",
    "technologically",
    "chronologically"
  ],
  "correct_answer": "technologically",
  "explanation": "Correct: This is the exact target word.",
  "distractor_explanations": {
    "biologically": "Same-stress same-syllable-count rhyme: shares the '-logically' ending and stress pattern, but starts with a different syllable (/baɪ/ vs /tɛk/).",
    "chronologically": "Same-stress same-syllable-count rhyme: shares the '-logically' ending and stress pattern, but starts with a different consonant cluster (/krɒn/ vs /tɛk/).",
    "theologically": "Same-stress same-syllable-count rhyme: shares the '-logically' ending and stress pattern, but starts with a different initial sound (/θi/ vs /tɛk/)."
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
    "technologically",
    "psychologically",
    "geographically",
    "economically"
  ],
  "explanation": "Correct: The adverb 'technologically' correctly modifies the adjective 'advanced', describing the specific domain of the advancement.",
  "distractor_tags": {},
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The museum exhibition showed how homes have evolved ___ since the early twentieth century.",
  "original_sentence": "The museum exhibition showed how homes have evolved technologically since the early twentieth century.",
  "correct_answer": "technologically",
  "options": [
    "biologically",
    "technologically",
    "temporarily",
    "accidentally"
  ],
  "explanation": "Correct: 'Technologically' correctly modifies the verb 'evolved', describing the manner in which homes have changed over time.",
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
  "sentence_with_blank": "Our school is becoming ___ advanced by introducing tablets and interactive boards in every classroom this term.",
  "original_sentence": "Our school is becoming technologically advanced by introducing tablets and interactive boards in every classroom this term.",
  "correct_answer": "technologically",
  "base_form": "technologically",
  "form_label": "positive degree adverb",
  "options": [
    "technological",
    "technologist",
    "technology",
    "technologically"
  ],
  "explanation": "adverb required to modify the adjective 'advanced'",
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "Our school is becoming ___ advanced by introducing tablets and interactive boards in every classroom this term.",
  "original_sentence": "Our school is becoming technologically advanced by introducing tablets and interactive boards in every classroom this term.",
  "required_pos": "adverb",
  "options": [
    "technologiness",
    "technologicalment",
    "technologically",
    "technologistical"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverbial form required to modify the adjective 'advanced'"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Our science teacher explained how cars have grown ___ complex over the last decade.",
  "original_sentence": "Our science teacher explained how cars have grown technologically complex over the last decade.",
  "correct_answer": "technologically",
  "base_form": "technology",
  "form_label": "adverb",
  "options": [
    "technologically",
    "technology",
    "technologist",
    "technological"
  ],
  "explanation": "adverb required to modify the adjective 'complex'",
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "Our science teacher explained how cars have grown ___ complex over the last decade.",
  "original_sentence": "Our science teacher explained how cars have grown technologically complex over the last decade.",
  "required_pos": "adverb",
  "options": [
    "technologically",
    "technologitude",
    "technologiness",
    "technologify"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverbial form modifying the adjective 'complex'"
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
      "text": "She solved the math problem technologically by writing the correct answer on the chalkboard.",
      "is_correct": false
    },
    {
      "text": "The dog barked technologically at the mailman to warn him not to enter the yard.",
      "is_correct": false
    },
    {
      "text": "Students discussed how their local community was changing technologically over the past five years.",
      "is_correct": true
    },
    {
      "text": "The chef cooked the meal technologically to ensure it tasted delicious and had the right amount of salt.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: Cooking and seasoning are culinary skills, not actions performed 'in a way that relates to technology or machines'. Semantically inappropriate: Writing an answer on a chalkboard is a manual, low-tech action, not an action utilizing advanced machines or equipment. Pragmatically inappropriate: Animal behavior and vocalizations are natural instincts, not actions driven by or relating to human technology.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "industrially",
    "mechanically",
    "scientifically",
    "manually"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: done by hand rather than by machines or equipment"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She felt technologically sad because it was raining outside and she could not go to the park.",
      "is_correct": false
    },
    {
      "text": "The puppy learned to fetch the ball technologically after practicing in the backyard all afternoon.",
      "is_correct": false
    },
    {
      "text": "The chef cooked the meal technologically to ensure it tasted like a traditional family recipe.",
      "is_correct": false
    },
    {
      "text": "By upgrading their equipment, the team became technologically prepared for the upcoming robotics competition.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: Cooking a meal to taste like a traditional recipe relies on culinary skills and ingredients, not on the use of machines or advanced equipment. semantic: Emotions like sadness caused by weather are human psychological states and have no logical connection to the use of machines or equipment. semantic: A dog learning a physical trick like fetching a ball is a biological and behavioral process, not an action involving technology or machinery.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "industrially",
    "scientifically",
    "electronically",
    "manually"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: by hand without machines, contrasting with using machines and equipment"
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

## sense 14390, level 3

#### Pack A
### Level 3 (sense 14390, difficulty None)
**cloze_completion** variant `A`, tier `3`
```json
{
  "sentence_with_blank": "The way coffee is prepared and consumed varies ___ across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "original_sentence": "The way coffee is prepared and consumed varies enormously across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "correct_answer": "enormously",
  "options": [
    "enormously",
    "secretly",
    "slightly",
    "rarely"
  ],
  "explanation": "Correct: 'Enormously' is the target adverb meaning 'to a very great degree', which perfectly modifies the verb 'varies' to show the vast extent of the differences.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```
**cloze_completion** variant `B`, tier `3`
```json
{
  "sentence_with_blank": "Students benefited ___ from the extra tutoring sessions before the exam.",
  "original_sentence": "Students benefited enormously from the extra tutoring sessions before the exam.",
  "correct_answer": "enormously",
  "options": [
    "enormously",
    "continuously",
    "accidentally",
    "loudly"
  ],
  "explanation": "correct: fits the context of gaining a very great degree of benefit from extra tutoring.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```

#### Pack B
### Level 3 (sense 14390, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The way coffee is prepared and consumed varies ___ across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "original_sentence": "The way coffee is prepared and consumed varies enormously across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "correct_answer": "enormously",
  "options": [
    "loudly",
    "enormously",
    "slightly",
    "temporarily"
  ],
  "explanation": "Correct: Fits perfectly to modify the verb 'varies', indicating a very great degree of difference.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She has grown ___ as a musician since joining the local youth orchestra last year.",
  "original_sentence": "She has grown enormously as a musician since joining the local youth orchestra last year.",
  "correct_answer": "enormously",
  "options": [
    "enormously",
    "slightly",
    "permanently",
    "loudly"
  ],
  "explanation": "Correct: adverb meaning 'to a very great degree,' appropriately modifies 'grown' to indicate significant development as a musician",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```

---

## sense 14390, level 6

#### Pack A
### Level 6 (sense 14390, difficulty None)
**semantic_discrimination** variant `A`, tier `3`
```json
{
  "sentences": [
    {
      "text": "The enormously silent room was filled with loud music.",
      "is_correct": false
    },
    {
      "text": "Technology has changed our daily lives enormously since we were kids.",
      "is_correct": true
    },
    {
      "text": "He enormously forgot to buy milk at the grocery store yesterday.",
      "is_correct": false
    },
    {
      "text": "She enormously walked to the corner store to get some bread.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Enormously' modifies degree or extent, but 'forgetting' is a punctual, binary cognitive event that cannot logically be done to a 'great degree'. Semantically inappropriate: 'Enormously silent' is an oxymoron when immediately followed by 'filled with loud music', creating a direct logical contradiction in the same clause. Collocationally inappropriate: 'Walked' is a simple physical activity. While one can walk 'quickly' or 'far', one cannot walk 'enormously', as the adverb does not naturally collocate with the physical act of walking in this manner.",
  "target_word": "enormously"
}
```

#### Pack B
### Level 6 (sense 14390, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She enormously forgot her keys on the kitchen counter before leaving for work.",
      "is_correct": false
    },
    {
      "text": "He felt enormously proud when his team finally won the regional debate championship.",
      "is_correct": true
    },
    {
      "text": "The tiny ant carried the crumb enormously across the sidewalk.",
      "is_correct": false
    },
    {
      "text": "He was enormously the same height as his brother, so they had to buy identical suits.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Enormously' means to a very great degree, which contradicts 'the same' and makes no logical sense when describing exact equality. Semantically inappropriate: 'Enormously' modifies the degree or extent of an action, but forgetting is a binary event that cannot be done to a 'great extent'. Pragmatically inappropriate: 'Enormously' describes degree or extent, not physical size or the physical manner of carrying an object; 'carefully' or 'slowly' would be appropriate here.",
  "target_word": "enormously"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The city has expanded enormously since my grandparents moved there as young adults.",
      "is_correct": true
    },
    {
      "text": "The tiny ant carried the crumb enormously across the kitchen floor without stopping.",
      "is_correct": false
    },
    {
      "text": "She knew enormously that the answer was correct before checking her work.",
      "is_correct": false
    },
    {
      "text": "The whisper echoed enormously through the silent library, disturbing everyone's concentration.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'enormously' modifies manner of carrying, but ants carry things in a small, precise way; the adverb contradicts the physical reality of the subject Semantically inappropriate: 'knew' is a stative cognitive verb that does not accept degree modification by 'enormously'; one either knows or doesn't know Pragmatically contradictory: whispers are by definition quiet and cannot echo 'enormously'; the adverb directly conflicts with the noun it describes",
  "target_word": "enormously"
}
```

---

## sense 14390, level 7

#### Pack A
### Level 7 (sense 14390, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The way coffee is prepared and consumed varies enormously across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
      "is_correct": true
    },
    {
      "text": "The cost of living has increased enormously over the past few years, worrying many families.",
      "is_correct": true
    },
    {
      "text": "Her performance in the school play improved enormously after she practiced every single afternoon.",
      "is_correct": true
    },
    {
      "text": "The enormously crowd at the concert made it difficult to see the stage.",
      "is_correct": false,
      "error_description": "The word 'enormously' is an adverb and cannot be used to directly modify a noun such as 'crowd'. The adjective form 'enormous' must be used instead."
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She has grown enormously as a musician since joining the local youth orchestra last year.",
      "is_correct": true
    },
    {
      "text": "The weather changed enormously within minutes, turning from bright sunshine to heavy rain.",
      "is_correct": true
    },
    {
      "text": "The team was enormously success in completing the project ahead of schedule.",
      "is_correct": false,
      "error_description": "The adverb 'enormously' cannot directly modify a noun ('success'). It must modify an adjective, such as 'successful', or the noun must be changed to its adjective form."
    },
    {
      "text": "The city has expanded enormously since my grandparents moved there as young adults.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 14390, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `3`
```json
{
  "sentences": [
    {
      "text": "The weather can affect your mood enormously during the winter months.",
      "is_correct": true
    },
    {
      "text": "Our understanding of space has expanded enormously thanks to modern telescopes.",
      "is_correct": true
    },
    {
      "text": "Students benefited enormously from the extra tutoring sessions before the exam.",
      "is_correct": true
    },
    {
      "text": "The weather can affect enormously your mood during the winter months.",
      "is_correct": false,
      "error_description": "The adverb 'enormously' is incorrectly placed between the transitive verb 'affect' and its direct object 'your mood'. Adverbs should not separate a verb from its direct object."
    }
  ]
}
```

---

## sense 14473, level 3

#### Pack A
### Level 3 (sense 14473, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Over time, it got better.",
  "original_sentence": "Over time, it got better.",
  "correct_answer": "Over time",
  "options": [
    "Inside",
    "Over time",
    "Loudly",
    "Simultaneously"
  ],
  "explanation": "Correct adverbial phrase indicating gradual change, fitting the context of gradual improvement.",
  "distractor_tags": {},
  "word_definition": "Gradually, as time goes by.",
  "target_word": "over time"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The heavy rain eroded the soil ___.",
  "original_sentence": "The heavy rain eroded the soil over time.",
  "correct_answer": "over time",
  "options": [
    "over time",
    "upwards",
    "accidentally",
    "posthaste"
  ],
  "explanation": "Correct: fits the context of a gradual, long-term physical process.",
  "distractor_tags": {},
  "word_definition": "Gradually, as time goes by.",
  "target_word": "over time"
}
```

#### Pack B
### Level 3 (sense 14473, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "They realized their misunderstandings would clear up ___.",
  "original_sentence": "They realized their misunderstandings would clear up over time.",
  "correct_answer": "over time",
  "options": [
    "over time",
    "by accident",
    "suddenly",
    "in the room"
  ],
  "explanation": "Correct: Fits perfectly as an adverbial phrase meaning 'gradually' to describe the clearing up of misunderstandings.",
  "distractor_tags": {},
  "word_definition": "Gradually, as time goes by.",
  "target_word": "over time"
}
```

---
