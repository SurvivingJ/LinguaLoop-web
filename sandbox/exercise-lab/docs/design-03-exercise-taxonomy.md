# Design 03 — Exercise Taxonomy

Evidence: `services/vocabulary_ladder/config.py` (`LADDER_LEVELS`,
`EXERCISE_TYPE_FAMILY`, `_CAPABILITY_SPEC`), `services/vocabulary_ladder/
deterministic/*.py` (all builders read directly), `recon-data-surface.md` §5-6
(grading paths), `recon-generation.md` §3 (type taxonomy).

Recognition vs. production classification follows the ladder's own
`EXERCISE_TYPE_FAMILY` mapping (`config.py:343-369`): `form_recognition` and
`meaning_recall` are recognition-side; `form_production`, `collocation`
(productive slot-fill), and `semantic_discrimination` (borderline — see note)
are production-side. `semantic_discrimination` and `spot_incorrect_sentence`
are flagged **recognition-with-a-production-flavor** below: the learner
selects from options, but must actively evaluate sentence-level meaning
rather than match a form — closer to recognition than production in answer
format, closer to production in cognitive demand. This ambiguity is called
out per-row rather than forced into one bucket.

## Full catalogue

| Type | Teaches | Recog/Prod | Answer format | Gen cost | Grading | Languages |
|---|---|---|---|---|---|---|
| `phonetic_recognition` (L1) | Audio-form discrimination | Recognition | MC, audio | ja: deterministic (mora trie, `l1_lookup.py`); zh/en: LLM (no trie built) | Client MC | zh, en, ja |
| `definition_match` (L2) | Word↔meaning mapping | Recognition | MC | Deterministic (`definition_match.py`) | Client MC | zh, en, ja |
| `cloze_completion` (L3) | Contextual meaning recall | Recognition (selects) | MC | LLM (sentence+distractors), or G1's embedding-band swap | Client MC | zh, en, ja |
| `morphology_slot` (L4) | Correct inflected/derived form | **Production knowledge, MC answer format** | MC | LLM (own prompt, TASK-520) | Client MC | en, ja (action/property); zh disabled (no inflection) |
| `collocation_gap_fill` (L5) | Fixed-collocation knowledge | Recognition (selects) | MC | LLM, PMI-grounded | Client MC | en only live (zh/ja disabled, no grounding source) |
| `semantic_discrimination` (L6) | Correct-usage judgment | Recognition-with-evaluation | MC (3 wrong sentences + 1 right) | LLM, or G1's embedding-neighbour "wrong" sentences | Client MC | zh, en, ja |
| `spot_incorrect_sentence` (L7) | Error detection + correction | Recognition-with-evaluation | MC + correction text | LLM, or G1's embedding-swap | Client MC | zh, en, ja |
| `collocation_repair` (L8) | Fixing a broken collocation | Production knowledge, MC format | MC | LLM (own prompt, TASK-520) | Client MC | en only live |
| `jumbled_sentence` (L9) | Syntax / word order production | **Production** | Ordering (drag chunks into place) | Deterministic (`jumbled.py`, chunked at build time) | Client, sequence match | zh, en, ja |
| `synonym_antonym_match` | Semantic relations | Recognition | MC | LLM, or G1's embedding nearest-neighbour | Client MC | zh, en, ja (abstract/action/property) |
| `word_family` | Derivational morphology | Recognition | MC | LLM, or G1's seed morphology_note | Client MC | en only |
| `particle_selection` | Grammatical function-word choice | **Production knowledge, MC format** | MC | LLM (no deterministic/embedding substitute proposed — see `design-01` Risks) | Client MC | ja only |
| `classifier_match` | Measure-word selection | **Production knowledge, MC format** | MC | Deterministic (`classifier_match.py`, curated dictionary) | Client MC | zh, concrete nouns |
| `counter_match` | Measure-word selection | Same as above | MC | Deterministic (`counter_match.py`, curated dictionary) | Client MC | ja, concrete nouns |
| `hanzi_to_pinyin` | Script→sound | Recognition | MC | Deterministic (`readings.py`, phonological confusion sets) | Client MC | zh |
| `pinyin_to_hanzi` | Sound→script | Recognition | MC | Deterministic (corpus homophone/component/frequency lookup) | Client MC | zh |
| `kanji_to_reading` | Script→sound | Recognition | MC | Deterministic | Client MC | ja (kanji lemmas only) |
| `reading_to_kanji` | Sound→script | Recognition | MC | Deterministic (corpus lookup) | Client MC | ja (kanji lemmas only) |
| `tone_id_word` | Tone-contour identification | Recognition | MC | Deterministic (`tone.py`) | Client MC | zh |
| `cloze_typed` | Productive lexical retrieval in context | **Production** | Free text | Deterministic — reuses L3's sentence, drops options (`cloze_typed.py`) | **Server**, exact-match post-normalization | zh, en, ja |
| Comprehension MC (`questions`) | Reading/listening comprehension | Recognition | MC | LLM (test-gen pipeline) | Server, literal string match | zh, en, ja |
| Dictation | Full transcription under audio | **Production** | Free text | N/A (uses existing test transcript) | Server, Levenshtein-tolerant token match | zh, en, ja |
| Pinyin / pitch-accent modes | Structured tap-sequence phonology | Recognition (structured) | Tap/click sequence | Deterministic (precomputed payload) | Server, structured match (not independently re-verified — recon flagged UNVERIFIED) | zh (pinyin), ja (pitch) |
| Dual Translation (DT) | Full free translation, meaning + register + naturalness | **Production** | Free text | N/A (learner-authored) | Server cascade: Tier0 deterministic exact/near-exact → Tier1 LLM (accuracy+range) → Tier2 LLM (understandability+fidelity+naturalness) | zh, en, ja |
| **`constrained_production` (NEW, proposed)** | Free sentence generation under a lexical+collocational constraint | **Production** | Free text | Deterministic (reuses seed's lemma+collocate; zero LLM at generation time) | **Server, near-deterministic** — see below | zh, en, ja |

## Legacy/frozen types (not generated, still served)

`tl_nl_translation`, `nl_tl_translation`, `text_flashcard`,
`listening_flashcard`, `odd_one_out`, `context_spectrum`,
`timed_speed_round`, `odd_collocation_out`, `verb_noun_match`,
`style_*` (4 variants) — frozen since TASK-512
(`recon-generation.md` §3b). Not modified by any design in this set; listed
for completeness only since they still occupy `exercises` rows and
`exercise_type` namespace.

---

## The new type: `constrained_production`

### Why one new type, and why this shape

`design-00` §3a commits to designing **at most one** genuinely new free-text
exercise with a fully deterministic or near-deterministic grading path. The
gap it fills: today's only productive types are `jumbled_sentence`
(reorders a *given* sentence — no lexical generation) and `cloze_typed`
(fills *one* blank in a *given* sentence — minimal generation). Neither asks
a learner to construct a sentence from scratch, which is the skill closest
to the stated product goal ("proficient use... in minimum time"). DT already
does full free production, but only at the passage-translation level (L1→L2
of a whole sentence/passage that already exists as a reference) and always
costs at least a Tier0 pass with conditional LLM escalation — it is not
designed as a per-word ladder drill. `constrained_production` sits between
`cloze_typed` and DT: **more generative than a cloze, cheaper to grade than
DT.**

### Design

**Prompt**: given the lemma and (where the seed has one) its primary
collocate, e.g. "Write a sentence using 咖啡 with 喝" (zh) / "Write a sentence
using 'coffee' with 'drink'" / "「機械」を使って、「動かす」を使った文を書いてください" (ja).
No reference sentence is shown — this is genuinely generative, not a
transformation of given material.

**Grading path — server-side, near-deterministic checklist, no LLM call in
the synchronous path**:

1. **Lemma presence** (deterministic, hard gate): does the submission contain
   the lemma or a recognized morphological variant? Reuses the exact
   machinery `cloze_typed` already has for this
   (`utils/answer_normalization.build_accepted`/`matches`,
   `services/vocabulary_ladder/tier_gate.morph_form_texts` for the variant
   set) — zero new normalization code.
2. **Collocate presence** (deterministic, soft gate — contributes to score,
   does not hard-fail): substring/lemma-match check for the required
   collocate, same mechanism as #1.
3. **Well-formedness band** (near-deterministic): embed the submitted
   sentence (same `text-embedding-3-small` pipeline already used for
   `dim_word_senses.embedding`) and check cosine similarity against the
   centroid of the seed's own stored example sentences for this
   semantic_class/tier is **above a floor** (catches empty/nonsense/wrong-
   language submissions) — this reuses G1's cosine-band mechanism
   (`design-01` §"G1", the semantic_distractors infrastructure) in a new
   role: not picking distractors, but bounding whether a free-form
   production is topically coherent at all. **This is a coarse filter, not a
   grammar checker** — it will not catch "coffee drink I" as ungrammatical
   English if the words are all correct and the embedding is CJK/English-
   agnostic-enough to still land in-band. That limitation is stated
   explicitly, not hidden.
4. **Length band** (deterministic): tier-appropriate min/max token count,
   reusing the existing tier-gate profiles (`config.py:240-247`,
   `TIER_GATE_PROFILES`) already built for exactly this kind of check.

**Score composition** (no LLM):
```
passed = lemma_present AND length_in_band AND embedding_above_floor
score  = 1.0 if passed and collocate_present
         0.7 if passed and not collocate_present
         0.0 if not passed
```

**What this deliberately does NOT check**: grammaticality, naturalness, or
whether the sentence *means* something sensible beyond the coherence floor.
This is the honest boundary of "near-deterministic" — a genuinely free
production task cannot be fully graded without either (a) a grammar-checking
NLP pass (some languages have `grammar_check_enabled` per
`dim_languages`, per `recon-data-surface.md` §1 — **UNVERIFIED** whether this
is wired to anything usable for scoring rather than just flagging) or (b) an
LLM call, which would reintroduce exactly the per-submission LLM cost this
document set is trying to minimize. **Recommendation**: ship the
deterministic score as the primary signal (fast, free, immediate feedback),
and route a random sample (or every `score < 1.0` case) to the same **offline
async audit sweep** `design-01`'s G1 already proposes for judge replacement —
consistent reuse of one audit mechanism across generation and grading,
rather than inventing a second one. This keeps the synchronous grading path
100% LLM-free while still surfacing quality signal for iteration.

### Pedagogical justification

This is the one type in the whole catalogue that asks for genuinely free
lexical retrieval plus syntactic assembly under a real-world-shaped
constraint (not just filling a pre-made slot) — the closest thing on this
list to Morris/Bransford/Franks's "transfer-appropriate processing": the
task (produce a sentence) matches the target skill (produce sentences) far
more closely than any MC type can, addressing the determinism-vs-pedagogy
tension named in `design-00` §3b directly rather than trading it away.

### Kill metric

`constrained_production_pass_rate` and, more importantly, `false_accept_rate`
— the fraction of `score=1.0` submissions that a human/LLM audit sample
judges as actually incoherent or wrong despite passing the deterministic
checklist. **Negative result**: if `false_accept_rate` exceeds a threshold
(no existing bar to reuse here — propose 10% as a starting gate, to be
tightened once measured) the embedding-coherence floor is too permissive and
needs either a tighter band or a cheap non-LLM grammaticality heuristic
(e.g. a small n-gram/perplexity model) before this type ships broadly rather
than as a flagged-for-review pilot.

---

## Cross-reference: MC-only rate by design

| Design | Types it adds/enables | MC fraction of those types |
|---|---|---|
| G1 (seed-and-render) | L1(zh/en pending trie), L3, L4, L6, L7, syn/ant | ~6/6 remain MC — G1 changes *how* distractors are generated, not the answer format |
| G2 (zero-LLM cold start) | definition_match + zh/ja script-sound types + syn/ant | 4-5/5 MC (`cloze_typed`/`jumbled_sentence` are the only productive types G2 can unlock, and only with a sentence) |
| New type | `constrained_production` | 0/1 — the only new type added by this whole document set that is not MC |

This table is the concrete evidence behind `design-00` §3b's warning: without
the one new type above, every generation design in `design-01` adds volume
almost entirely on the recognition side. `design-04`'s sequencing
recommendation treats `constrained_production` as a **required**, not
optional, companion to whichever generation design ships first — not a
someday nice-to-have.
