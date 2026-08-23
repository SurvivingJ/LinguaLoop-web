# L1 distractors, all three languages — a build-once phonetic trie

**Date:** 2026-08-23
**Follows:** [ja-l1-redesign-options.md](ja-l1-redesign-options.md) (Track B1/B2 in that
report are the ja-only ancestor of this design)
**Status:** plan only. No code, no dependencies, no DB changes made.

---

## 0. The one idea underneath all three languages

Every language's L1 problem is the same shape: given a target word's pronunciation, find
other real words whose pronunciation is *almost* the same. Today that search is delegated to
an LLM, which occasionally invents a word that isn't real rather than admitting it couldn't
find one. The fix is the same shape in all three languages too: **build a trie — a
prefix tree — out of a real, external, pronunciation-tagged dictionary, once, and then
answer "what's almost the same as this?" by walking the tree instead of asking a model.**
A trie makes this efficient specifically *because* the query is local: instead of comparing
the target against every other word in the dictionary, you walk down the tree along the
target's own pronunciation and, at each step, look sideways at the tree's other branches.
That's the whole mechanism — the three languages differ only in what the "unit" of a tree
step is (a mora, a syllable, a phoneme) and where the dictionary comes from.

Once this exists, the LLM's job in L1 shrinks from **"find and verify real, confusable
words"** (the job it keeps failing at in Japanese) to, at most, **"pick the best few from an
already-real, already-confusable shortlist, and describe why."** For a meaningful share of
cases even that last step can be templated with no model call at all, because the trie walk
already knows exactly *which* unit changed and *how*.

---

## 1. The shared data structure

```
Trie node:
  children: {unit_token -> child node}
  is_word_end: bool
  surface_forms: [orthographic spellings that end here]   # usually 1, sometimes many (homophones)
```

**Build:** for every (pronunciation, spelling) pair in a source dictionary, tokenize the
pronunciation into a sequence of units and insert it into the tree, appending the spelling
to the terminal node's `surface_forms`.

**Query — one-substitution neighbors of a target's unit sequence `[u0, u1, ..., un]`:**

```
for position i in 0..n:
    walk the trie along [u0, ..., u(i-1)]           # the shared prefix, unchanged
    at that node, for every child token v != u_i:    # every possible substitution at position i
        walk the remaining suffix [u(i+1), ..., un] from v
        if that walk reaches a node with is_word_end:
            every surface_form there is a one-substitution neighbor,
            tagged with (position i, u_i -> v) — this IS the explanation, for free
```

**Query — exact match (0-substitution, i.e. homophones):** walk the full sequence once;
`surface_forms` at the terminal node, minus the target's own spelling, are same-pronunciation
alternates.

Both queries cost O(word length × branching factor) — a handful of trie descents, not a scan
of the dictionary. For dictionaries in the 100k–200k word range (all three languages, see
§2–4) this is sub-millisecond and the whole tree fits in a few tens of MB of process memory,
so "build once" literally means build once and hold it in memory for the process lifetime —
no precomputed all-pairs table, no staleness relative to the ladder's own growing sense
pool, because the tree is built from a stable *external* dictionary, not from
`dim_vocabulary`.

**A structural guarantee this buys for free, in every language:** a fabricated candidate
cannot reach the output. The tree only ever returns `surface_forms` that were inserted from
the source dictionary — there is no path through this algorithm that invents a spelling.
Existence stops being something asked of a model and becomes something the data structure
cannot violate.

---

## 2. Japanese — mora trie

**Unit:** a mora — the beat-counting unit of Japanese phonology (what `L1_block` currently
asks the model to reason about by hand, badly, per TASK-735).

**Tokenizer** (deterministic, ~30 lines, no library needed beyond the reading string
itself):

| rule | example |
|---|---|
| one kana = one mora, by default | む・か・し |
| a small ゃ/ゅ/ょ (or katakana ャ/ュ/ョ) fuses with the preceding consonant kana into one mora | きゃ = 1 mora, not 2 |
| a chōon mark ー is its own mora (extends the vowel by one beat) | ビール = ビ・ー・ル, 3 morae |
| a small っ (sokuon) is its own mora (represents the geminate consonant beat) | ぶっか = ぶ・っ・か, 3 morae |

This is standard mora-counting, the same rule Japanese speakers use for haiku meter — not a
bespoke heuristic invented for this task.

**Lexicon source — the gap that has to be closed, and how.** Checked directly rather than
assumed: the two MeCab dictionaries already installed (`unidic-lite`, `ipadic`, both in
`requirements.txt`) ship only **compiled** `sys.dic` binaries — no raw CSV, and
`fugashi.Tagger` exposes no entry-enumeration API (`dictionary_info()` gives metadata only).
Confirmed by listing both packages' `dicdir` directly. So there is currently no free
"give me every headword and its reading" source in the repo. **Recommended: JMdict**
(EDRDG, Monash University — freely redistributable with attribution, ~180k+ entries, each
with explicit kanji spelling(s), kana reading(s), and part-of-speech tags) — it's the
resource actually designed for "reading → headword," not a tokenizer's internal trie
repurposed for a job it wasn't built for.

**Build:** parse JMdict once, mora-tokenize every `<reb>` (reading) field, insert
`(mora_sequence, kanji_spelling)` into the tree. POS tags from JMdict let the build exclude
non-lemma entries (bound morphemes, affixes) up front — closing, incidentally, part of the
"一/様/度 sort to the top of the sense pool" problem noted in prior review, though that's a
P1 sense-selection issue, not an L1 one.

**Tier:** JMdict doesn't carry frequency. Filter candidates post-lookup with
`wordfreq.zipf_frequency` against `TIER_GATE_PROFILES` — already live infrastructure
(`services/vocabulary_ladder/tier_gate.py`), already covers ja
(`TIER_GATE_LANG_CODES = {3: 'ja'}`). See prior report §5 for why vocabulary-band filtering,
not distance-scaling, is the right lever — that argument carries over unchanged.

**Worked example — 昔 (むかし):** mora sequence `[む, か, し]`. Position-2 substitution
(し→え) reaches む・か・え = 迎え (real, JMdict-attested) — exactly the neighbor TASK-735's
own generator found by hand. Position-0 substitution (む→ひ) reaches ひ・か・し = 皮脂? (not
real at that reading) → correctly absent, no fabrication risk, because absence in the tree
means absence, full stop.

**What this eliminates by construction:** the pitch-accent-only collision (機械/機会,
箸/橋). Both members of an accent-only pair have the *identical* reading — the
one-substitution query never proposes a target's own unchanged reading as a "neighbor,"
because a neighbor requires exactly one unit to differ. The judge's "reject accent-only
pairs" rule becomes unreachable dead code for anything that comes through this path, the
same conclusion the prior report reached for Track B1/B2, now confirmed to hold for the
mora-trie specifically (it was designed around this property, not discovered after the
fact).

---

## 3. Chinese — syllable (initial/final/tone) trie, with your stated two-tier priority

**Unit — this is where zh genuinely differs from a flat mora/phoneme trie, on purpose,
to implement the exact priority you described.** Decompose each syllable into three
components — `(initial, final, tone)` — rather than treating the whole syllable as one
opaque unit. Mandarin syllable structure is a solved, standard decomposition (an initial
consonant from a closed set of ~23 including the null/zero initial, a final from a closed
set of ~35, and a tone 1–4 or neutral/5) — not something invented for this task, and it's
exactly the structure `pypinyin` and CC-CEDICT already expose per-syllable.

A **word** is a sequence of these triples, one per hanzi (图书馆 → `[(t,u,2), (sh,u,1),
(g,u,an,3)]`).

**Two-tier candidate query, matching your stated priority exactly:**

1. **Tier 1 — same initial, same final, different tone.** Fix two of the three components,
   vary only tone. This is the trie's cheapest, most local query — for a single-character
   target this alone often produces the classic tonal minimal-pair set (妈/骂/马/麻 for
   ma1/ma2/ma3/ma4). Run this first; if it yields ≥3 real candidates, stop.
2. **Tier 2 — fallback, "similar spelling through patterns."** If Tier 1 is short, widen to
   a one-component substitution over `(initial, final)` while tone is free to vary too:
   same final + one-substitution initial (ba↔pa, a voicing-style contrast), or same initial
   + one-substitution final (ba↔bo). This is structurally the *same* one-substitution trie
   walk as the ja mora trie, just over 2 components instead of over morae — the "tree" you
   asked for is the same shape, decomposed one level deeper because Mandarin syllables carry
   an extra independent dimension (tone) that Japanese morae don't.

**Decided (2026-08-23): true homophones (same initial, same final, *same* tone, e.g. 是/事,
both shì) are rejected.** These give the listener genuinely zero disambiguating signal, the
same underlying problem as ja's pitch-accent collision — and in Mandarin, tone *is* reliably
rendered by TTS (unlike ja pitch accent, which many engines flatten), so treating these the
same as ja's forbidden case is the phonologically consistent choice: **exclude
same-(initial,final,tone) pairs from candidates, same as ja excludes same-reading pairs.**
This was raised as an open judgment call and confirmed by the user rather than decided
silently. Noting the asymmetry deliberately: the **English** design (§4) keeps the opposite
policy — the live en prompt permits true homophones (their/there/they're) as valid L1
distractors, and that's established, working project doctrine, untouched by this decision.
The three languages don't have to agree with each other here; each one's choice is now a
stated decision, not an accident of which query ran first.

**Lexicon source — already in the repo, no new dependency.** `scripts/import_cedict_classifiers.py`
already downloads and parses CC-CEDICT (`cedict_ts.u8`, MDBG, CC-BY-SA 3.0) on demand, with
a working regex for exactly the line format needed
(`simplified traditional [pin1 yin1] /defs/`). `pypinyin` is already a direct dependency
(`requirements.txt:69`) and `services/pinyin_service.py` already does tone-number extraction
and sandhi handling for the ladder's own sentence content. **Zh is the best-resourced
language of the three for this — the dictionary, the parser pattern, and the pinyin/tone
tooling all already exist in the repo.** Building the syllable decomposer (initial/final/tone
split from a `TONE3`-style string like `zhong1`) is the only genuinely new code, and it's a
small, standard lookup table.

**Tier:** same mechanism as ja — `wordfreq.zipf_frequency` against `TIER_GATE_PROFILES`,
already covers zh (`TIER_GATE_LANG_CODES = {1: 'zh'}`).

**Edge case to carry over, not solve fresh:** neutral-tone (tone 5) syllables are
context-dependent (sandhi) in a way `pinyin_service.py` already models. A target word ending
in a sandhi-affected tone should probably resolve candidates against its *base* tone, not a
sentence-specific sandhi tone — reuse `pinyin_service._parse_tone`'s convention (`ma5` for
neutral) rather than inventing a second one.

---

## 4. English — ARPAbet phoneme trie ("IPA-style tree")

**Unit:** an ARPAbet phoneme (CMUdict's representation — functionally the same idea as IPA,
ASCII-encoded, e.g. "ship" → `SH IH1 P`). Using ARPAbet rather than true IPA is a practical
substitution, not a downgrade: CMUdict is the standard, freely available (public domain),
zero-setup source for this in English, and its phonemes map 1:1 to IPA symbols if a display
form is ever needed.

**No custom tokenizer needed — this is the one language where that step is free.** Unlike
ja (had to define mora rules) and zh (had to define initial/final decomposition), CMUdict
ships pronunciations already segmented into a phoneme list per word. The "tree" is a direct
trie over that list.

**Lexicon source — a genuinely new, but minimal, dependency.** Checked: `requirements.txt`
has no `cmudict`/`pronouncing`/`nltk` today, and the DB itself can't substitute — I queried
`dim_word_senses.pronunciation`/`ipa_pronunciation` for `language_id=2` (English) and found
**10 populated rows out of 10,256** (0.1%). Track A/B's "read the pronunciation from the DB"
option that works for ja (100% populated) and zh (98%) simply isn't available for en — this
design has to key off the orthographic word directly against an external dictionary.
Recommend the `cmudict` PyPI package specifically (not `nltk`'s corpus-download mechanism):
it vendors the ~134k-entry dictionary as a plain Python resource inside the package, so
`pip install` is the entire setup step, with no runtime fetch to depend on for
reproducible builds.

**Stress-only collision — the same lesson from ja, applied by structural analogy, not
copied blindly.** CMUdict marks stress on vowel phonemes (`AH0`/`AH1`/`AH2`). Two different
words whose full phoneme sequence is identical *except* for stress placement are, for a
single isolated-word TTS rendering, the English analogue of ja's pitch-accent collision —
same underlying reason (no second utterance to compare against). **Design decision: strip
stress digits before comparing two candidates' base phoneme sequences; if they match, reject
the pair as stress-only, even though the raw (stress-included) trie walk would have called
it a valid one-substitution neighbor.** This needs an explicit post-filter rather than
falling out of the trie structure automatically, unlike ja's pitch-accent exclusion — noting
that difference plainly rather than overselling the parallel.

**True homophones — kept, matching live doctrine.** The 0-substitution exact-match query
(§1) returns every other spelling sharing the *exact* phoneme+stress sequence — their/there/
they're, know/no, etc. `prompt_templates` id 145 already treats this as the *preferred* L1
distractor category ("L1 is the only level where homophones/near-homophones of the target
are permitted"), and it's the one live row across all three languages that has never
fabricated. This design keeps that policy exactly, rather than "fixing" it to match the
zh/ja stricter default — see §3's flagged note.

**Tier:** same mechanism, `wordfreq.zipf_frequency` against `TIER_GATE_PROFILES`, already
covers en (`TIER_GATE_LANG_CODES = {2: 'en'}`).

**Priority, lowest of the three.** The live en row has never fabricated a word — TASK-735's
whole ja intervention doesn't have an en equivalent to fix. This design is worth building
for the LLM-call and cost reduction alone (§6), but it is not solving an open defect the way
the ja and zh versions are.

---

## 5. What's left for the LLM, if anything

Three shrinking options, in order of how far this goes:

1. **Full elimination for candidate generation and verification, all three languages.** The
   trie replaces the entire "propose distractors" LLM call. This is the part that matters
   most for "avoid hallucinations" — it isn't mitigated, it's structurally impossible,
   because nothing downstream of a dictionary lookup can return a spelling the dictionary
   doesn't contain.
2. **Explanation — templatable, no model call needed.** The trie walk already knows *which*
   unit changed and *how* (position, old unit, new unit) — that's precisely the content the
   current prompts ask the model to write by hand into each option's `"3"` (explanation)
   field. A template like `"「{surface}」は対象語と一モーラ差（{i}: {u_i}→{v}）"` (ja) or
   `"{surface} differs only in the {i}th sound: {u_i} → {v}"` (en) is deterministic and
   arguably *more* consistent than what the model currently writes case by case.
3. **The one thing that genuinely doesn't fall out of a dictionary lookup: synonymy.** A
   verified-real, correctly one-unit-different word can still mean nearly the same thing as
   the target — nothing about pronunciation checks meaning. This is real residual risk, but
   smaller than it sounds: true synonym pairs that also happen to be phonetically adjacent
   are rare in any language (semantic relatedness and phonological adjacency aren't
   correlated except by coincidence), so most candidates the trie proposes were never going
   to be synonyms in the first place. Three ways to close the residual gap, from cheapest to
   most thorough:
   - **Nothing, initially** — accept the residual risk, measure actual synonym-collision
     rate against real trie output before assuming it needs a fix (§7).
   - **A cheap heuristic where data already exists** — `dim_word_senses.embedding` exists for
     anything already in the ladder's own vocabulary; a cosine-similarity check against known
     senses catches the cases where the candidate is itself a taught word. Doesn't cover
     candidates the ladder has never taught (the more common case, since most trie
     candidates come from the external dictionary, not `dim_vocabulary`).
   - **A single, thin, batched LLM call**, only if the above two turn out to be
     insufficient — the draft already written for this in the prior report,
     [`data/eval/task736/b_rank_and_explain_ja.txt`](../../data/eval/task736/b_rank_and_explain_ja.txt),
     is exactly this shape (feed pre-verified candidates, ask only "drop synonyms / tier
     misfits, don't verify existence"). Even in the worst case where this call is kept
     permanently, it has already had the one job it could hallucinate at (existence) taken
     away from it.

**The realistic target state, across all three languages, is L1 generation at or near zero
LLM calls in steady state** — the trie for candidates, a template for explanations, and at
most a thin, optional, hallucination-incapable filtering pass. That is the strongest reading
of "build once, run forever" available here: the expensive, error-prone part is not
optimized, it's removed.

---

## 6. Storage, refresh, and where this plugs into the existing pipeline

**Storage: an in-process object, not a database table.** Earlier framing (prior report's
Track B2) proposed precomputing *every* neighbor pair into a DB table ahead of time. Having
now worked out the trie mechanics in detail, that's the wrong shape — the trie already *is*
the complete, compact answer space (node count ≈ dictionary size, not pairwise combinations),
and querying it live is sub-millisecond. Build once per language into a serialized artifact
(plain pickle or msgpack of a nested-dict trie — no compression library needed at these
dictionary sizes, tens of MB uncompressed), load it once per process via the same caching
pattern `furigana_service.py` already uses (`services.vocabulary.model_cache.model_cache`),
and query it live at generation time. No staleness relative to `dim_vocabulary` or
`dim_word_senses` growing over time, because the tree is built from the external dictionary,
which barely changes — a refresh is "re-run the build script against a newer JMdict/
CEDICT/CMUdict release," not something tied to the ladder's own content cadence.

**Proposed module layout** (new, mirrors the existing `scripts/build_classifier_dictionary.py`
/ `import_cedict_classifiers.py` convention already in the repo):

```
services/vocabulary_ladder/phonetic_trie/
  trie.py            # generic PhoneticTrie: build, exact-match, one-substitution query
  ja_mora.py         # mora tokenizer + JMdict parser
  zh_syllable.py     # initial/final/tone decomposer + CEDICT parser (reuses pypinyin)
  en_phoneme.py      # CMUdict loader (no tokenizer needed)

scripts/
  build_ja_mora_trie.py
  build_zh_syllable_trie.py
  build_en_phoneme_trie.py
```

**Integration point.** L1 comes out of the shared `vocab_prompt2_exercises` call entirely,
for whichever language has shipped its trie — that prompt's L1 block (and, per language, its
per-call cost) shrinks away; L3/L5/L6 keep generating through it unchanged. A new,
language-agnostic `l1_lookup.py` asset generator queries the appropriate trie, applies the
tier/zipf filter, optionally runs the thin ranking pass (§5.3), and writes the same
descriptive-key `level_1` shape (`options`, `explanations`, `correct_answer`) the renderer
already reads — `exercise_renderer.py`'s read side does not need to change.
`validators.OPTION_COUNTS[1]` can likely tighten back toward `(4, 4)` once a language's
lookup-miss rate is measured (a dictionary lookup with a defined fallback doesn't need the
same over-generation cushion an unreliable LLM does), but that's a follow-on change, not
part of the initial build.

---

## 7. Cost, effort, and sequencing

| | zh | ja | en |
|---|---|---|---|
| Lexicon already in repo? | **Yes** — CEDICT parser exists, `pypinyin`/`jieba` already deps | No — need JMdict | No — need `cmudict` (new dep) |
| Custom tokenizer to write | Initial/final/tone decomposer (small, standard table) | Mora tokenizer (small, standard rules) | **None** — CMUdict pre-segmented |
| Is the current LLM approach actually broken? | Not measured as broken, but never redesigned either | **Yes — this whole workstream exists because of it** | **No** — en has never fabricated |
| Build effort | **S** | M–L (JMdict acquisition + parsing + mora logic) | S–M (new dependency to vet + wire in) |
| LLM cost after ship | ~$0/sense (trie + template; optional thin call) | ~$0/sense (same) | ~$0/sense (same) |
| One-time build cost | Free (local parsing, no LLM) | Free (local parsing, no LLM) | Free (local parsing, no LLM) |

**Recommended order: zh → ja → en.**

- **zh first, deliberately, even though it isn't the fire.** It's the cheapest possible way
  to prove the whole pattern — trie build, tier filter, integration into
  `exercise_renderer` — end to end, using dependencies and parsers that already exist, before
  spending the JMdict-acquisition effort ja actually needs. Low cost, low risk, validates the
  architecture with a real measurement instead of a plan.
- **ja second**, applying the now-proven pattern to the language this entire workstream is
  actually about. Highest urgency, higher build cost (JMdict + a from-scratch mora
  tokenizer), but no longer a first attempt at the pattern by the time it's built.
- **en last.** Real value (cost reduction, one fewer LLM surface to maintain) but the lowest
  urgency of the three — nothing is broken there today, and it's a genuinely new dependency
  to bring in, which deserves the least rush of the three.

---

## 8. Risks and what's still unverified

- **JMdict/CMUdict coverage gaps.** Neither dictionary is exhaustive; a real, valid word a
  learner might know could be absent, producing a false "no neighbor found" rather than
  today's opposite failure (a false neighbor invented). Different error direction, still an
  error — needs measuring against real ladder targets before trusting either dictionary's
  coverage, not assumed from dictionary size alone.
- **The zh true-homophone exclusion (§3) is now a confirmed design decision (2026-08-23),
  not an unresolved judgment call** — still worth a native-reviewer pass at build time the
  same way the prior report flagged the ja doctrine and the invented A3 synonym example, but
  as a sanity check on execution, not because the direction is in doubt.
- **Tier-band filtering is inert until the `complexity_tier` prerequisite from the prior
  report (§0/§5 there) is fixed.** `dim_vocabulary.level_tag` is NULL for all three
  languages today; every proposal in this document that says "filter by tier" is filtering
  against a constant until that's fixed. Unchanged conclusion from the prior report, restated
  because it applies to all three languages here, not just ja.
- **I have not built or run any of this.** Every number in §7 is an estimate from reading
  the relevant code and dependency manifests, not a measurement. The natural next step,
  consistent with the prior report's budget instruction, is a small proof-of-concept build
  for zh (§7's recommended starting point) — cheap, no LLM spend, and would turn this
  section's estimates into real numbers before ja's larger build is committed to.
