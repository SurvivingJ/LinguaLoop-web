# Italian profile: decisions a teacher would question

**Variety and learner.** Standard Italian of Italy; adult English speaker, A1 to B2. C1 only labels rare words.

**Text.** Only the straight apostrophe is allowed, and it is not punctuation: `l'amico` is one word and one tile. Accented letters are à è é ì ò ù and capitals only. Digits are forbidden; numbers are written as words.

**Pronunciation.** A `pronunciation` key was added (not in the template; the validator ignores it): IPA with stress mark and syllable dots, which `stress_position` needs.

**Open and closed e / o are not drilled**: standard speakers disagree by region. Stress position and double consonants are drilled instead.

**Six new types.**
- `stress_position` (deterministic, from the IPA): the analogue of tone identification.
- `article_match` (deterministic, `noun_gender`): definite, indefinite, plural article and preposition + article as four modes of one type. A reviewer may want the fused prepositions as their own type.
- `auxiliary_choice` and `conjugation_form` (deterministic, `verb_conjugation`). `conjugation_form` is a paradigm cell without a sentence; `morphology_slot` stays the authored in-sentence version. The overlap is deliberate.
- `government_match` (deterministic, `verb_government`) for prepositions fixed by a head word; `preposition_selection` (the only new authored block) for those fixed by the frame (in Italia / a Roma).

**Plural formation has no type of its own**; it goes to `morphology_slot`, checked against `noun_gender`.

**Collocation types and `word_family` are `adapt`, not `not_applicable`.** The `collocations` dictionary is the grounding list zh and ja lack, aimed at light-verb pairs (fare una domanda). Until it exists the types stay disabled. None of the three is in the first fat-seed slice.

**Translation types** are kept: nouns are answered with their article; false friends are forced in as distractors.

**cloze_typed counts a wrong or missing accent as an error**, reported as an accent error. Teachers who accept `perche` will disagree; e / è and da / dà decided it.

**Five dictionaries**: `noun_gender` (2000), `verb_conjugation` (600), `verb_government` (350), `collocations` (500), `false_friends` (200). Doubts:
- `verb_conjugation` stores only what cannot be computed. Passato remoto is left out (recognition only at these levels); impersonal verbs are excluded because `present` needs six forms. fare, dire, bere are classed by infinitive ending; `irregular_in` carries the rest.
- Cross-field rules (article against first sound; plural required unless `plural_type` is none) live in `author_notes`; the validator cannot check them. A build step should.
- `collocations.wrong_collocates` is the riskiest field: wrong must mean unacceptable, not rarer.
- `false_friends.kind` (full / partial) needs judgement; its `source_pos` is a list in one string.
- `verb_government` also takes adjectives and nouns, which the author adds beyond `source_pos`.

**Grammar, not ladder:** clitics, passato prossimo against imperfetto, subjunctive and hypotheticals, the agreement chain.

**pos_classes** use the app's semantic classes; each new row's note names the parts of speech.

**Not verified here.** TTS names it-IT-IsabellaNeural and it-IT-DiegoNeural are from memory, not checked against the live Azure list. spaCy is not installed in this environment, so the `nlp` notes on elision, fused prepositions and clitics describe `it_core_news_lg` from knowledge, not from a run.

## Review

Reviewed as a teacher and as the engineer of the `new` rows. `validate-profile it` ends with OK. Three real rows (one irregular) and one malformed row were run against every dictionary spec with the tool's own row checker.

**Changed in `profile.json`**

Ladder
- `phonetic_recognition`: stress pairs (ancora) removed from the distractor kinds. They are spelled like the headword, so they cannot be written options; the note now says every option must differ in spelling.
- `stress_position`: the "two-syllable words in a stress pair" clause removed (an unaccented two-syllable word is always stressed on the first). Homographs with two stresses are skipped, and a word whose written and IPA syllable counts differ is skipped, not guessed.
- `auxiliary_choice`: verbs marked `both` are now always skipped. The old rule made a deterministic generator read the free-text `auxiliary_note`. Added: feminine or plural subject for essere verbs, `si` for reflexives.
- `conjugation_form`: the note now says how the persons that are not stored are computed from the stored io forms (imperfect, future, conditional, present subjunctive), and that vai / va' are both correct.
- `government_match`: the prompt shows `en_pattern`, and a preposition that another row gives for the same head and complement is never a distractor (pensare a / di, chiedere a qualcuno / chiedere qualcosa). Without this the item had two right answers.
- `collocation_gap_fill`: distractors are the first three `wrong_collocates`.

Dictionaries
- `noun_gender`: `gender_cue` gains `suffix` with a closed list (feminine -zione, -sione, -gione, -tà, -tù, -trice, -tudine; masculine -ore, -iere), so la stazione and il colore get a rule in the explanation and are not lumped with il pane / la notte. Notes added: silent h (l'hotel), foreign j / w, il dio / gli dei, and plural-only nouns are left out (the row requires singular articles).
- `verb_conjugation`: `imperative_tu` is now optional (potere, dovere, piacere have none; the old spec forced an invented form) and holds the full form (vai, fai, dai, stai, di'); new optional `imperative_tu_short` (va', fa', da', sta'; the regex requires the apostrophe). Lemma regex simplified to `(are|ere|ire|rre|rsi)$` (same language as before). Notes: modals take avere with a note; succedere moved from the essere examples to the defective verbs that are left out; verbs with a fixed clitic other than si (andarsene, farcela) are left out.
- `verb_government`: `en_pattern` was free text; it is now a regex, lower case and ending in a closed placeholder (sb, sth, sb or sth, to do sth, do sth, doing sth), because the generator shows it. Notes state the `english_calque` rule and that prepositions outside the list (tra, contro) are left out.
- `collocations`: `wrong_collocates` minimum raised from 2 to 3. The gap fill has four options, and with two the generator would have had to invent the third, which is the ungrounded step the dictionary exists to remove.
- `false_friends`: lemma is the dictionary form (parente); camera removed from the examples of `full`.

Unique features
- Added `piacere_type_verbs` (mi piace / mi piacciono, mi manchi) and `formal_address` (tu / Lei with verb, pronoun and imperative forms), both delivered by grammar. Both are errors learners make visibly and for a long time, and neither had a home. piacere was removed from the `agreement_chain` text.

**Checked and left as it was**
- `text.allowed_regex`: accepts à è é ì ò ù and capitals, the straight apostrophe, straight double quotes, «», the dash and the hyphen. Curly quotes and the curly apostrophe are rejected on purpose (normalised first). No ó, î or foreign letters: no sentence in the level range needs them.
- All `reuse` and `not_applicable` decisions, and the six `new` types. Nothing listed in `unique_features` is something learners pick up without drilling.

**For the owner to decide**
1. `preposition_selection` is `new` although its shape is that of the Japanese `particle_selection`. It was kept `new` because the fat-seed shape check accepts extra blocks only from `new` llm rows; in the app it could be built as the particle renderer under another name.
2. `cloze_typed` marks a wrong accent (perchè for perché) as an error. Strict for A1; a softer option is to accept the wrong direction of the accent and reject only a missing one.
3. `jumbled_sentence` asks to accept every word order "a reviewer listed as valid", but no file in the pack stores such a list. Either add that field to the fat-seed document or limit the type to sentences with one possible order.
4. Plural-only nouns (gli occhiali, i pantaloni, le forbici, i soldi) are outside `noun_gender`. Taking them in needs optional singular articles, which loosens the spec for every other row.
5. Cross-field rules (article against first sound, plural required unless `plural_type` is none, `english_calque` only when `differs_from_english`, phrase contains node and collocate) are still only in `author_notes`; `validate-dict` cannot check them. A build step or the dictionary reviewer has to.
6. `collocations.wrong_collocates` now needs three clearly wrong partners. That is easy for light-verb pairs and hard for adjective + noun pairs; expect fewer than 500 rows, or mostly `verb_noun` rows.
7. Not verified by this review either: `proposed_language_id` 4 against `dim_languages`, the two Azure voice names, and the spaCy behaviour described in `nlp.notes`.
