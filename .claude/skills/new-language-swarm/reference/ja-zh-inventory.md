# What Japanese and Chinese have (surveyed 2026-11-28)

This is the map the team works from. Counts are from the live database on
2026-11-28 (451 MB of a 500 MB plan; the stop line is 480 MB). A new language
needs each row of the first table answered: built, adapted, or declared not
applicable with a reason.

## 1. Content, by type

| content | zh (id 1) | ja (id 3) | how it was made | per-language part |
|---|---|---|---|---|
| vocabulary (`dim_vocabulary`) | 12,809 | 6,974 | test-text extraction plus curated lists (CC-CEDICT + Zipf for zh; JLPT lists and a 5k agent list for ja) | tokeniser, frequency source, level scheme |
| senses (`dim_word_senses`) | 41,581 | 40,716 | `batch-sense-generation`: simple (child register) + standard definition in the word's own language, example; JLPT levels through headless `claude -p` write + review | register rules, POS legend |
| cross-language glosses | en for 3,914 words | en + zh | `cross-language-glosses`: single best equivalent + equivalent set | none beyond the language pair |
| ladder assets (`word_assets`) | 54,481 | 42,406 | `fat-seed-authoring`: one JSON per sense (core + variants A/B), Sonnet core, Haiku audits and variants, separate review | **cheat sheet** `cheatsheets/<lang>.md`, block set |
| rendered exercises | ~101,000 | ~81,000 | renderer + judges from the assets | capability rows |
| per-option explanations | Storage files | Storage files | Message Batches, Sonnet (ADR-064) | none |
| grammar drills | 10,209 items, 39 topics, 39 guides, 22 generators | none (particle drills planned, nothing in the repo) | Claude subagents: guide agent per topic; per batch one author and one reviewer in a fresh context (blind solve, compare, fix) | **everything**: topic plan, guides, items |
| lookup dictionaries | measure words: 146 classifiers, 2,664 noun pairs | counters: 54 counters, 837 noun pairs | curation files per entry, reviewed, merged, built | **everything** |
| reading aids | pinyin payloads, tone inventory, character components | furigana, pitch accent, mora trie | deterministic libraries | **everything** |
| comprehension tests | 276 | 185 | topic + prose + question agents (hosted models), 98 prompt rows per language | prompt rows, tier thresholds |
| sentence references | yes | yes | `sentence-reference-authoring` / `-review` | L1/L2 branches |
| collocation grounding | 40 corpus rows | none | corpus PMI (zh), curated list (en) | a list or a corpus |
| placement / calibration | anchor pool, distractor cache, tone mode | anchor pool, distractor cache, reading mode | SQL refresh + cache build after senses and embeddings exist | pronunciation mode |
| TTS voices | 2 Azure voices | 2 Azure voices | `dim_languages.tts_voice_ids` | voice ids |

## 2. Exercise types and who has them

The live matrix is `dim_exercise_capabilities` (mirror: `_CAPABILITY_SPEC` in
`services/vocabulary_ladder/config.py`). Ladder level in brackets.

| scope | types |
|---|---|
| every language | `phonetic_recognition` (1), `definition_match` (2), `cloze_completion` (3), `cloze_typed` (4), `semantic_discrimination` (6), `spot_incorrect_sentence` (7), `jumbled_sentence` (9), `synonym_antonym_match` (6), `text_flashcard`, `listening_flashcard`, `timed_speed_round` |
| zh and ja | `tl_nl_translation`, `nl_tl_translation` (3) |
| **zh only** | `hanzi_to_pinyin`, `pinyin_to_hanzi`, `tone_id_word` (1, deterministic from the reading); `classifier_match` (4, deterministic from the measure-word dictionary) |
| **ja only** | `kanji_to_reading`, `reading_to_kanji` (1, deterministic); `particle_selection` (4, authored; needs tokenised particles); `counter_match` (4, deterministic from the counter dictionary); `morphology_slot` (4) for inflecting words only |
| **en only** | `word_family` (4); `collocation_gap_fill` (5) and `collocation_repair` (8), which need a collocation list; `morphology_slot` (4) |
| disabled for zh and ja | `collocation_gap_fill`, `collocation_repair` (no grounding source); `morphology_slot` for zh |

The pattern behind the unique types, which is what the profiler must reproduce
for the new language:

1. **Script-to-sound** exercises generated from a reading (pinyin, kana). An
   alphabetic language has no script barrier; its analogue is whatever the
   spelling hides (stress, vowel quality, double consonants, silent letters).
2. **A closed-class word chosen by the noun or the frame**, generated from a
   reviewed dictionary (measure words, counters) or authored per sentence
   (particles). Analogues: gender and articles, case, prepositions, auxiliaries.
3. **Inflection**: `morphology_slot` where the language inflects; a paradigm
   table makes most of it deterministic.
4. **Grammar drilled to reflex**: Chinese got 39 topics chosen from what
   learners get wrong (了/过/着, 的/得/地, 把/被, complements, word order,
   confusable pairs), not from a textbook's table of contents.

## 3. What is not content: the wiring a language needs before anything is live

There is no language registry. `{1: 'zh', 2: 'en', 3: 'ja'}` is copied into
about 60 places; most fail loudly on an unknown id. The full list is in
`wiring-checklist.md`. The parts that decide what the team can and cannot do
before wiring:

- `prompt_templates` lookups for the ladder are strict (no cross-language
  fallback), so `scripts/fat_seed_runner.py` and the `nt_*` pipeline cannot run
  for a language with no prompt rows. Until then fat-seed documents are checked
  for shape only (`language_pack.py validate-fatseed`).
- Three NLP registries (vocabulary pipeline, exercise generation, corpus) each
  need a processor for the language.
- `scripts/grammar_drills.py` and the drill page are Chinese-only (`LANG = 'zh'`,
  pinyin checks, `zh` / `py` fields). `scripts/language_pack.py` checks and
  builds drills for any language from its `profile.json`.
- The database has room for about 28 MB. One language's dictionary and assets
  are roughly 30 KB per sense. **Everything the team writes is files**; nothing
  is uploaded.

## 4. How the existing content was produced: rules that held up

- Author and reviewer are different agents, and the reviewer starts with a
  fresh context. For drills the reviewer first solves a blind copy; the
  comparison finds the ambiguous items an author cannot see in their own work.
- Scripts validate, models write. Every file an agent writes has a command
  that says OK or lists the problems, and the agent runs it until clean.
- A pilot before the fan-out (了 and word order before the other 37 topics;
  100-sense gold sets before the fat-seed queue).
- Short, example-led instructions. The Japanese cheat sheet is ~5 KB; every
  longer rule list scored worse (`data/exercise_seeding/ja/opt/REPORT.md`).
- Explanations in English, quoting target-language words.
- Known gaps to not repeat: no native-speaker check on the Chinese drills;
  Chinese English glosses cover a third of the words; definitions that join two
  senses were the main cause of rejected cores.
