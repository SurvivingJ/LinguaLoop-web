# Fat-seed EN authoring (v1, from the ja v7 structure)

Block shapes and plan values (anchor sentence, correct answer, `given`) are
fixed by the Block reference below; never choose them yourself. These six
sections are where documents lose points.

## 1. Core sentences: whole word, given sense, natural
- `definition` = the given definition. Exactly 10 sentences; mined ones first,
  byte-for-byte. pos / semantic_class / register / form labels: exactly the
  values the brief lists.
- The target is a free-standing whole word in THIS sense. Not inside another
  word: "new" is not in knew, renew or renewal; "art" is not in start or
  artist. Not another sense: teaching bank = a money institution excludes the
  river bank. `target_word` is the exact form and case in the sentence
  (decided, Decisions).
- Respect the tier.
  - Words per sentence: T1 ≤12, T2 ≤18, T3 ≤25, T4 ≤35, T5 ≤45.
  - Grammar: T1 simple present and past only; T2 adds future simple; T3 adds
    continuous and present perfect; T4 adds all perfects, passive and the
    1st/2nd conditional.
- Only ordinary collocations: make a decision (not do a decision), heavy rain
  (not strong rain), strong coffee (not powerful coffee), commit a crime (not
  make a crime). One register per document; no slang in a formal one.
- Each sentence has a context cue so the target is the only word that fits its
  slot when blanked.
- IPA broad with stress marks (/dɪˈsɪʒ.ən/). syllable_count counts the
  headword's syllables (decision = 3). Pronunciation as the brief describes.
- Forms: 3–5 real, contemporary forms of this lemma. No archaic or dialect
  forms.

## 2. level_1 (listening): sounds alike, not looks alike
- Correct = the headword. Distractors are real words a listener could mishear
  as it:
  - minimal pairs that differ by one phoneme: ship/sheep /ɪ/–/iː/,
    light/right /l/–/r/, bed/bad /e/–/æ/;
  - homophones: there/their, write/right;
  - same-stress rhymes with a different onset.
- Never: spelling-only lookalikes (tough/though, through/thorough), synonyms,
  or inflections of the target (run/ran).
- Explanation states the sound relation: "minimal pair: /ɪ/ in ship vs /iː/ in sheep".
- B uses different words from A. Decline `no_minimal_pairs` only for a variant
  with fewer than 3 real neighbours left. This happens mostly with long or
  technical words.

## 3. level_6 wrong sentences: grammatical, wrong only in what THIS word means
Each wrong sentence is grammatical English. A native speaker says "we don't
use that word like that", not "that's bad grammar". Build each with one move:
- **Move A, other sense:** a sentence natural for another sense of the same
  form. Teaching bank = money, use "We sat on the bank and watched the boats."
- **Move B, near-synonym swap:** write a natural sentence for a word learners
  confuse with the target, then put the target in its place.
  - fun ← funny: "The joke was so fun that everyone laughed."
  - watch ← notice: "I watched a mistake in your essay."
  - economic ← economical: "This small car is very economic on fuel."
  - sensible ← sensitive: "She cried because she is very sensible to criticism."
  - rob ← steal: "Someone robbed my bike last night."
- Never: a grammar slip (agreement, tense, article, preposition,
  countability: those belong to level_7). Also never: a sentence that is
  merely odd or false but uses the word correctly ("I ate my car"), an error
  on another word, or two problems at once.
- Explanation names the confusion: "This needs 'funny' (causing laughter);
  'fun' means enjoyable." Use different moves and partners across the three
  sentences; B uses none of A's.

## 4. level_7: one span, on the target
- A new sentence. Not a core sentence, and corrected_sentence equals no core
  sentence.
- The incorrect and corrected sentences differ in exactly ONE span: the
  target's form, its preposition or complement, or its collocate. Examples:
  - "Yesterday we goed to the park." → "Yesterday we went to the park."
  - "It depends of the weather." → "It depends on the weather."
  - "We discussed about the plan." → "We discussed the plan."
  - "She gave me a lot of informations." → "…a lot of information."
  - "He made a crime." → "He committed a crime." (target crime)
- error_description names the wrong form, the right form and why.

## 5. synonym_antonym_match: decline unless a thesaurus lists the pair
- Return `{"declined": "no_relation"}` unless a standard thesaurus lists the
  pair for THIS sense.
  - Valid pairs: big↔large, begin↔start, increase↔decrease, accept↔refuse.
  - Not pairs: table↔chair, coffee↔tea, Monday↔Friday.
  - Most concrete nouns have no antonym. A forced key is the worst defect.
- Distractors: same part of speech, in no relation to ANY sense of the word,
  never a form of the target (not "largely" for "large").

## 6. Explanations and distractors everywhere
- Every explanation is specific and true: what the option means and why it
  clashes here.
- level_3: start each distractor's explanation with its failure tag
  (semantic / collocational / aspectual / register / valency), then the
  reason, e.g. "collocational: we 'make', not 'do', a decision". The three
  distractors cover at least two tags.
- Never a generic line ("the meaning doesn't fit"). Never contradict the
  definition.
- level_3 distractors have the same part of speech and are grammatical in the
  slot, but must not fit when the sentence is read as plain English. Read each
  one in the blank. Run the substitution check: if a near-synonym of the target
  would make a distractor right, replace it. No homophones of the target in
  level_3.
- level_5 / level_8 collocation: distractors are close in meaning but
  unnatural with the target. Check British and American usage too: "take a
  decision" and "reach a decision" are valid, so never use them as distractors
  for "make". For level_8, error_collocate is one of the three distractors.
- level_4: distractors are real forms of the same lemma that clearly fail in
  the slot. "She has ___ three letters today." → written; not writes, wrote or
  writing.
- word_family:
  - The stem is the shortest base ("decide", not "decision").
  - Exactly one real derived form fits the slot's role (decision, noun).
  - The three distractors are INVENTED, well-formed non-words built with real
    suffixes: decidement, decidance, decisionhood.
  - Never a real word (decisive, decided). When unsure, do not use it.
  - Give each option its part_of_speech.
- A and B: B shares no distractor word, wrong sentence or error type with A.
