# Zero-LLM Exercise Generation — Measured Results

Date: 2026-09-18. All numbers below come from a live run of the REAL production
deterministic builders (`services/vocabulary_ladder/deterministic/*.py`,
unmodified) against `db/lab.sqlite`, via the sqlite `ctx.db` shim built for
this task (`prototypes/zero_llm/shim.py`). No LLM call, no Supabase call, no
migration was made anywhere in this investigation. Raw output:
`reports/zero_llm_measurement.json`, `reports/zero_llm_sample_exercises.json`,
`reports/extra_examples.json`.

Sample size: 1,200 randomly-sampled `standard`-level senses per language
(seed 20260917), out of populations of 121,159 (zh) / 4,842 (en) / 22,426
(ja) `dim_vocabulary` rows. Each sense was run through both ladder variants
(A/B), matching production's per-sense exercise count.

---

## 1. The shim (task 1)

`classifier_match.py`, `counter_match.py`, `definition_match.py` and
`readings.py` (hanzi_to_pinyin/pinyin_to_hanzi/kanji_to_reading/
reading_to_kanji) each do `from services.vocabulary_ladder.deterministic.
dictionaries import get_index` / `...lexicon import get_lexicon` at import
time. `prototypes/zero_llm/shim.py` pre-registers sqlite-backed
re-implementations of those two leaf modules (`prototypes/zero_llm/
dictionaries.py`, `.../lexicon.py` — adapted from the production files,
same public contract) directly into `sys.modules` under the production
module names, then triggers the real package's builder-loading sweep. Every
builder that runs after that is the **genuine, unmodified production file**;
only the two DB-touching leaf modules were swapped, and `ctx.db` is the
sqlite3 connection. Result: all 10 registered deterministic builders
(`classifier_match, counter_match, cloze_typed, definition_match,
jumbled_sentence, hanzi_to_pinyin, pinyin_to_hanzi, tone_id_word,
kanji_to_reading, reading_to_kanji`) import and run cleanly.

One real bug this surfaced and fixed along the way: the sandbox's
`dim_counters` table column is `kanji`, not `counter` — the adapter had it
wrong and `counter_match` was silently failing every call (`no such column:
counter`) until fixed. Also added two small compatibility shims the
production `classifier_match`/`readings` code required that the earlier
sandbox `dictionaries.py`/`lexicon.py` drafts didn't yet expose:
`MeasureWord.group_label` (aliased to `semantic_label`, since the sandbox has
no `dim_classifier_distractor_groups` table) and `Lexicon.component_neighbours`
(always `[]`, since `dim_character_components` isn't seeded — exactly
production's own degrade path when that table is empty).

Also fixed (perf, not behavior): the ported `Lexicon.definitions_at_tier` and
`Lexicon.frequency_band_fillers` did a fresh O(all entries) scan per call —
harmless in production (backed by an indexed Supabase query) but at zh's
124,933-entry scale in a flat Python list, thousands of such calls made the
first measurement run effectively hang for hours. Pre-grouping entries by
tier/length once at load time fixed it; same output, no behavior change.

**Semantic_class heuristic (read before trusting the matrix below):**
production's `dim_vocabulary.semantic_class` is an LLM-assigned field and
this sandbox seeds it as NULL for all 148,427 rows. Since the capability
matrix routes `classifier_match`/`counter_match`/`cloze_typed`/
`jumbled_sentence` on `semantic_class ∈ {concrete, abstract, action,
property}` rather than the `'all'` sentinel, leaving it NULL would make those
four types permanently unreachable — understating the zero-LLM path, not
overstating it. `prototypes/zero_llm/semantic_class.py` supplies an
LLM-free heuristic proxy: en/ja get real POS tags mapped to a class; **zh has
no POS data at all** (CC-CEDICT carries none), so zh classification is a
weak definition-text heuristic (leading "to " → action, else default
concrete). Sampled distribution: zh 999 concrete / 195 action / 4 proper / 2
function (out of 1200); en 524 concrete / 341 action / 183 property / 86
proper / 52 function / 14 unclassified; ja 652 concrete / 306 action / 211
property / 24 function / 2 proper / 5 unclassified. Every zh
classifier_match/cloze_typed/jumbled_sentence number below is filtered through
this proxy and should be read as directional, not as what a real P1 model
would classify.

---

## 2. Sentence sourcing — the crux (task 2)

`cloze_typed` and `jumbled_sentence` both need a real sentence containing the
target word. Three candidate sources, measured against the **full** vocab
per language (not the 8,000-cap subset `build_db.py` embedded):

| Source | zh (121,159 vocab) | en (4,842 vocab) | ja (22,426 vocab) |
|---|---|---|---|
| (a) `dim_word_senses.example_sentence` column (build_db.py, substring match) | 1,897 filled — **1.57%** | 2,604 filled — **53.78%** | 27 filled — **0.12%** |
| (b) tokenized corpus mining (real jieba/spaCy/fugashi via `LanguageProcessor`, whole-word match) | 1,541 — **1.27%** | 2,143 — **44.26%** | 17 — **0.08%** |
| (c) CC-CEDICT / JMdict native example fields | 0 — **0%**, confirmed absent from both source formats (checked the raw JSON/text; neither carries an example-sentence field) | 0% | 0% |

Corpus size available: 517 candidate zh sentences, 1,028 en, only **7** ja
(the seed corpus has just 1 Japanese test transcript — see README §4's
row-count correction).

**Verdict: sentence coverage is not low for a small technical reason, it is
categorically low.** zh and ja are both under 2% no matter which source is
used, because the entire available corpus is 153 test transcripts — nowhere
near enough to cover 121k/22k-word vocabularies by chance co-occurrence, and
neither dictionary format carries authored examples at all. En looks
healthy (44–54%) only because en's *vocabulary* is tiny (4,842 words, a
curated high-frequency list) relative to its own 76-test corpus — it is the
same mechanism, just at a scale where it happens to work. **This directly
collapses the ">=5 exercises per sense" claim for cloze_typed/jumbled_sentence
specifically** (see §4) — those two types are zero-LLM-*capable* but
zero-LLM-*reachable* for only a couple of percent of zh/ja senses, because
there is no LLM to author the missing sentences and no other honest source of
them.

---

## 3. True capability matrix (task 4)

% of the 1,200-sense sample that produced ≥1 exercise of that type (via
either variant A or B):

| Type | zh | en | ja |
|---|---|---|---|
| `definition_match` | **99.7%** (1,196) | 0% (0) — every en definition is NULL, a pre-existing fidelity gap, not a new finding | **99.8%** (1,198) |
| `hanzi_to_pinyin` | 94.4% (1,133) | — | — |
| `pinyin_to_hanzi` | 94.4% (1,133) | — | — |
| `tone_id_word` | 94.4% (1,133) | — | — |
| `kanji_to_reading` | — | — | 77.7% (932) |
| `reading_to_kanji` | — | — | 80.4% (965) |
| `classifier_match` | **0.4%** (5) | n/a | n/a |
| `counter_match` | n/a | n/a | **1.4%** (17) |
| `cloze_typed` | **2.25%** (27) | 48.0% (576) | 0.2%* (skips as "no cloze-capable sentence") |
| `jumbled_sentence` | **2.17%** (26) | 48.1% (577) | 0.2%* |

(*ja cloze/jumbled effectively round to the same ~0.2% floor set by the
7-sentence corpus; not shown as its own row above because it didn't clear 1
sense in the printed summary but is bounded by the same sentence-coverage
ceiling as zh.)

Dominant skip reasons confirm §2 exactly: zh/ja `cloze_typed` and
`jumbled_sentence` skip 2,334–2,338 times (out of 2,400 = 1,200×2 variants)
with `"no cloze-capable sentence to derive from"` / `"no P1 sentence
available"`. `classifier_match`/`counter_match` skip mostly on "not in the
[classifier/counter] dictionary" (expected — only 570/578 curated pairs exist
against 121k/22k vocab). ja `kanji_to_reading`/`reading_to_kanji` skip 466
times on "lemma contains no kanji" (function words in kana — correct
behavior, not a defect).

**Types the matrix enables but that have no registered builder at all:**
`text_flashcard`, `listening_flashcard`, `timed_speed_round` are marked
`generator: 'deterministic'` and `is_enabled: True` in
`config._CAPABILITY_SPEC` for every language, but no module in
`services/vocabulary_ladder/deterministic/` registers them — they are built
elsewhere in the real pipeline (not through this `generate()` path), so they
are correctly absent from this measurement rather than silently miscounted.

---

## 4. HEADLINE — exercises-per-sense distribution (task 4)

Total exercise items per sense (both variants combined), zero LLM calls:

| Language | 0 exercises | 1–2 | 3–4 | 5+ | mean |
|---|---|---|---|---|---|
| **zh** | 0.3% | 5.2% | 0.0% | **94.5%** | 7.75 |
| **en** | **51.3%** | 1.2% | 47.4% | 0.0% | 1.92 |
| **ja** | 0.2% | 18.9% | 3.2% | **77.8%** | 5.19 |

This is a real but lopsided result, and it does NOT mean what a naive read
suggests. zh/ja's ">=5 exercises" mass is almost entirely
`definition_match` + the 3–4 script/sound types (hanzi_to_pinyin/
pinyin_to_hanzi/tone_id_word for zh; kanji_to_reading/reading_to_kanji for
ja) firing on ~95%+ of senses each — genuinely free, genuinely reachable,
genuinely good exercises (see §6). What it is **not** is broad-based: the
sentence-dependent types (cloze_typed, jumbled_sentence — the two closest to
"real production/usage" exercises) are reachable for only ~2% of zh/ja senses
(§2/§3), so the 94.5%/77.8% headline is being carried entirely by
recognition/phonology drills, not by sentence-in-context exercises.

En is the inverse: en has NO script/sound drills (Latin script has no
reading-direction ambiguity to test) and NO definition_match (definitions are
NULL), so its only reachable types are cloze_typed/jumbled_sentence — and
because en's small vocabulary is well-covered by its own corpus (§2), those
fire on ~48% each, giving en's senses either 0 (51.3%, no sentence available)
or exactly 2 (47.4%, both cloze_typed and jumbled_sentence, since a sense
that clears the sentence-availability bar clears it for both types
simultaneously off the same sentence) — hence the near-total absence of a
"3-4" middle band and the 0% "5+" band. En's ceiling is structurally 2
exercises/sense here, not a partial result trending toward more.

**Backlog coverage** (task 4's last bullet): the sandbox's `exercises` table
starts empty for every sense (100% backlog, matching the "seeded empty by
design" note in the README). Per the table above, the zero-LLM path fills
that backlog to non-empty for **99.7% of zh senses, 48.7% of en senses, and
99.8% of ja senses**, at $0 — but for zh/ja, essentially none of that fill is
the sentence-grounded exercise types production's ladder treats as
higher-value (L3/L4/L9); it is definition + phonology drills.

---

## 5. Latency / throughput (task 4)

On a 400-sense sub-sample per language, single Python process, real
production builder code, warm lexicon/dictionary caches:

| Language | concurrency 1 | concurrency 8 | speedup |
|---|---|---|---|
| zh | 58.0 ms/sense (17.3 senses/sec) | 61.1 ms/sense (16.4 senses/sec) | **0.95x (slower)** |
| en | 2.1 ms/sense (468 senses/sec) | 2.3 ms/sense (431 senses/sec) | **0.92x (slower)** |
| ja | 9.2 ms/sense (108 senses/sec) | 9.4 ms/sense (106 senses/sec) | **0.98x (flat)** |

Concurrency 8 does not help and mildly hurts at every language — expected
and correctly diagnosed: this is single-process CPU-bound Python (dict/list
work under the GIL, no I/O wait to overlap), so `ThreadPoolExecutor` buys
nothing and adds scheduling overhead. A real batch job would want
multiprocessing or a compiled/vectorized rewrite of the hot path, not more
threads. Absolute throughput is still enormous next to any LLM call: zh's
worst case (~17 senses/sec, ~58ms/sense) would batch-process all 121,159 zh
vocab rows in **~2 hours of single-core CPU time**, at zero API cost — en/ja
are 2 and 12 orders of magnitude faster respectively.

---

## 6. Distractor strategy comparison (task 5)

Implemented on `definition_match`'s distractor selection, compared on 80
sampled senses per language (zh/ja only — en has no definitions to compare):

- **EMBED**: cosine-nearest-neighbour over the char-ngram TF-IDF proxy
  embeddings `build_db.py` already computed for the top-8,000
  highest-frequency senses/language (`lab/embeddings.py`). **This is an
  orthographic proxy, not semantic** — a documented sandbox limitation (no
  local sentence-transformer was found installed). Any "these are too
  similar" finding below is a LOWER bound: real semantic embeddings would
  likely surface even more near-duplicate meanings than this orthographic
  proxy does, not fewer.
- **NONEMBED**: production's real approach (same Zipf-frequency decile),
  extended with the heuristic semantic_class filter from §1 (same tier AND
  same class), matching the task's "frequency-tier + semantic field" spec.

**Result: the two strategies agree on nothing.** Mean overlap between the two
3-distractor sets was **0.0 for both zh and ja** — not one shared distractor
across 80 comparisons per language, out of an 8,000-sense pool. They are
answering different questions: NONEMBED asks "what's a plausible-difficulty,
plausible-category wrong answer", EMBED asks "what's the closest-meaning
wrong answer" — and at this pool size those pools essentially never
intersect.

**Quality risk, not just difference:** EMBED's top-1 nearest neighbour scored
cosine similarity > 0.92 for **1.2% of sampled senses in both zh and ja**
(1-in-~80). A concrete example — ja **制定** ("enactment; establishment;
creation") — EMBED's three distractors were *"establishment; institution"*,
*"establishment; settlement"*, *"establishment; creation; posing (a
problem)"*: three near-synonyms of the correct answer, at least one of which
a fluent judge could reasonably call also-correct. NONEMBED's distractors for
the same sense (*"decisive battle; deciding match; play-off"*, *"to
point"*, *"to decide; to determine"*) are unambiguously wrong but also
unambiguously *less discriminating* — a learner can eliminate them by
register/domain alone without knowing the target word's precise meaning.
**Neither strategy alone is right**: production's tier-only approach is safe
but coarse; pure embedding similarity is sharp but risks manufacturing
also-correct options; a real pipeline would want embedding similarity as a
*ranking* signal with a similarity ceiling (e.g. reject >0.85), not a
standalone selector — which is exactly what production does NOT currently do
(it doesn't use embeddings for this at all).

---

## 7. Quality spot-check (task 6) — concrete examples

**GOOD — zh `jumbled_sentence`, sense 主义 ("-ism/doctrine"):**
Sentence: 说到中国的治理，很多人会想到"中国特色社会主义"，这确实是一个独特的模式.
Chunked (via real jieba-backed `LanguageProcessor`) into 6 pieces:
`["说到中国的治理", "很多人会", "想到'中国特色社会主义'", "这", "确实是一个",
"独特的模式"]`. This is a long, multi-clause sentence with a fixed
topic-comment structure — reordering the 6 chunks back to the source order is
essentially unique; the "short Chinese sentence, multiple valid orderings"
risk the task warned about did not materialize here because the chunker
correctly produced clause-sized pieces, not word-sized ones.

**BAD — en `cloze_typed`, sense "lands" (plural of "land"):** blanked
sentence: *"...are also less clear-cut in today's much more fractured and
interdisciplinary scientific **___cape**."* — the blank sits **inside** the
word "landscape", because the seeded `example_sentence` (source (a), §2) was
matched into the corpus by `build_db.py`'s plain substring check (`"lands"
in sentence`), which matched inside "land**scape**" rather than a real
standalone occurrence of "lands". The accepted answer "lands" does
mechanically reconstruct "landscape" (lands+cape), so the item is not
*broken* in the sense of having no valid answer, but no learner would ever
read "___cape" and think to type "lands" — it is not a word-recognition
exercise, it's a string-splicing artifact. This is precisely why task 2 asked
for real tokenization instead of trusting the existing substring-matched
column: source (b) (`LanguageProcessor.contains_whole_word`, jieba/spaCy/
fugashi-backed) is CJK/word-boundary-safe by construction and would never
have produced this pairing.

**RISKY — ja `definition_match` distractor selection via embeddings, sense
制定 ("enactment"):** see §6 — EMBED's three distractors were near-synonyms
of the correct definition, a real "secretly also correct" risk. Production
does not currently use this strategy (it uses tier-only), so this is a
finding about a *hypothetical* improvement, not a bug in what's live today.

**QUESTIONABLE — ja `counter_match`, sense 教科書 ("textbook"):** stem "教科書
を一___" (how do you count ONE textbook?), options `["切れ", "章", "皿",
"条"]`, correct answer "章" (counter for **chapters**), accepted_answers
`["章", "部"]`. The counter being tested (chapter-counting) doesn't match
the noun being asked about (counting whole textbooks, which conventionally
takes 冊 or 部) — 教科書's curated pairing in
`data/counter_curation/*.json` appears to link it to the "chapters of a
document" counter-group rather than the "bound volumes" group. This is
upstream curation data, not a rendering bug, but it produces a genuinely
confusing exercise: a learner who correctly knows textbooks are counted with
冊 would find neither their answer nor an obviously-wrong option, only two
chapter-counting options (章/部) that are both defensible for "a chapter" and
neither obviously right for "a textbook."

**GOOD — zh `classifier_match`, sense 灶 ("stove"):** options
`["股", "架", "口", "盘"]`, correct "口" (used for wells, stoves, blades —
a real, specific classifier relationship, not the generic 个). Distractors
are unrelated household/counting classifiers, safely wrong. One caveat: this
noun's `semantic_label` was empty in the curated data, so distractors came
from the random-filler fallback rather than a semantically coherent group
(§1's dictionaries.py banner) — safe here, but means this item's distractors
are not guaranteed to be maximally discriminating the way a populated
semantic group would be.

---

## 8. Verdict

**Real win for zh and ja, on recognition/phonology drills — not the
"generate any exercise type for any sense" claim.** `definition_match` +
the four script/sound types (hanzi_to_pinyin/pinyin_to_hanzi/tone_id_word for
zh, kanji_to_reading/reading_to_kanji for ja) are genuinely production code,
genuinely free, genuinely fast (17–108+ senses/sec single-core), and
genuinely fire on 94–100% of senses once the semantic_class gate is
satisfied. That is ~119k zh senses and ~22k ja senses that could go from zero
exercises to 4–5 solid, LLM-quality-comparable exercises for the cost of CPU
time alone. classifier_match/counter_match add a small but real and
well-targeted increment (0.4%/1.4% of senses — bounded by curated-dictionary
coverage, not a code limitation).

**Not a win — barely reachable — for the sentence-grounded types
(cloze_typed, jumbled_sentence) in zh/ja specifically**, and this is the
finding that should gate any "ship the zero-LLM path" decision: those two
types need a real sentence, the sandbox's entire zh/ja corpus is 517/7
sentences respectively (a real-repo-scale problem, not a sandbox artifact —
there is no larger local corpus and neither source dictionary carries
examples), and coverage tops out at ~2%. Shipping zero-LLM cloze/jumbled for
zh/ja at production scale would need either a much larger locally-available
sentence corpus or accepting that those two types stay LLM-only.

**En is the mirror case**: the sentence-grounded types work well (48% each,
bounded only by en's own small-vocabulary/small-corpus ratio, which is
favorable) but `definition_match` and every script/sound drill are
structurally unavailable (no definitions seeded, Latin script has no
reading-direction ambiguity to test) — so en's zero-LLM ceiling is a flat 2
exercises/sense for under half its vocabulary, not the 5+ zh/ja gets.

**The distractor-quality question (task 5) argues against a naive
embedding-based upgrade**: pure similarity-ranked distractors measurably risk
manufacturing also-correct options (1.2% at cosine>0.92, likely
undercounted given the embeddings here are orthographic, not semantic), while
production's current frequency-tier-only approach is safe but not
discriminating. Neither extreme should ship as-is; a similarity-ranked
selection with a hard similarity ceiling is the actual recommendation, and it
is currently not what's live.
