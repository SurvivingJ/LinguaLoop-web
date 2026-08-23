# ja L1 redesign — options report

**Date:** 2026-08-23
**Prior work:** [task735-ja-l1-fixes.md](task735-ja-l1-fixes.md) (TASK-735)
**Status:** exploration only. Nothing in this document has been applied. Drafts live in
[`data/eval/task736/`](../../data/eval/task736/).

---

## 0. Corrections to the handoff brief's "verified state"

Two things in the brief no longer match the live DB, and one thing the brief asked me to
check was worse than suspected. Stating these first so nothing below is read against stale
numbers.

**The row ids in the brief are the *original* rows, not the *live* ones.** TASK-735's
applier inserts a new row per version rather than updating in place (`apply()` in
`scripts/apply_task735_ja_l1_fixes.py:365`). The brief's ids 184 / 370 are the v1/v2
originals, now `is_active=false`. The rows actually serving traffic today:

| task_name | lang | live id | version | model |
|---|---|---|---|---|
| `vocab_prompt2_exercises` | ja | **376** | v4 | qwen/qwen3.7-plus |
| `ladder_l1_distractor_judge` | ja | **374** | v3 | qwen/qwen3.7-plus |
| `vocab_prompt2_exercises` | en | 145 | v4 | anthropic/claude-sonnet-5 |
| `ladder_l1_distractor_judge` | en | 173 | v1 | google/gemini-3.5-flash-lite |

Confirmed by querying `is_active` across every version of both task_names (see §9 for the
query). All four template bodies were read in full for this report, not summarized from
the brief.

**Confirmed: `{complexity_tier}` never appears in the ja L1 block.** It appears once, in
the shared header (`学習者レベル：{complexity_tier}`), and every occurrence of the word
"レベル" inside the L1 section of v4 refers to something else (地名・人名 checks, etc.) —
grepped the full body, zero hits of `complexity_tier` past the header. Confirmed as briefed.

**Worse than briefed: `complexity_tier` is not just unused by L1 — its value is the same
constant for every sense, in every language, today.** `prompt1_core.py:158` sources it as
`vocab.get('level_tag') or 'T3'`. I queried `dim_vocabulary.level_tag` across all three
languages:

```
language_id | level_tag | count
1 (zh)      | NULL      | 3957
2 (en)      | NULL      | 3964
3 (ja)      | NULL      | 2404
```

**Every row, every language, is NULL.** `complexity_tier` has been `'T3'` for every word
this pipeline has ever generated, regardless of the word's actual difficulty. This is not
a ja-specific gap and not new to this task — it's a standing defect in the whole vocabulary
ladder, and it means **no tier-conditioned L1 design does anything live until this is fixed
first**, independent of which proposal below is chosen. See §5.

The good news: a working, already-tested tier signal exists elsewhere in the same package
and is not wired in here. `services/vocabulary_ladder/tier_gate.py:tier_for_lemma(lemma,
language_id)` derives a tier from `wordfreq.zipf_frequency`, covers ja
(`TIER_GATE_LANG_CODES = {1: 'zh', 2: 'en', 3: 'ja'}`), and is already live in the P1
sentence-mining path (`asset_pipeline.py:662`). `prompt1_core.py:_load_word_data` could
call it as a fallback when `level_tag` is null — roughly five lines, zero new
infrastructure, fixes tier-awareness for every level in every language at once, not just
L1. **I did not apply this** (constraint: no live DB/code changes this pass) but it is the
highest-leverage single change in this report and every tier-conditioned proposal below
depends on it.

---

## 1. What a good ja L1 distractor is (restated, for anchoring every proposal below)

- A real word — a dictionary headword.
- Audio-confusable with the target — differs by exactly one mora (vowel/consonant minimal
  pair, voicing, vowel length, or gemination).
- Not a synonym.
- Not a spelling look-alike that sounds different.
- Not distinguishable only by pitch accent — TTS renders one reading; an accent-only pair
  (機械/機会, 箸/橋) gives the learner nothing to decide with. Stated explicitly per the
  brief, because it was got wrong twice already.

---

## Track A — prompt variants (same architecture: one generator call, one judge call)

All three keep the existing shape exactly: `vocab_prompt2_exercises` [ja] emits L1 among
L3/L5/L6 in one call; `ladder_l1_distractor_judge` [ja] filters the L1 distractors in a
second call. Only the L1 block of the generator prompt changes. Drafts:
[`data/eval/task736/a1_uncapped_enumeration_ja.txt`](../../data/eval/task736/a1_uncapped_enumeration_ja.txt),
[`a2_structured_retrieval_ja.txt`](../../data/eval/task736/a2_structured_retrieval_ja.txt),
[`a3_worked_negatives_ja.txt`](../../data/eval/task736/a3_worked_negatives_ja.txt).

All three also add two new placeholders, `{tier_display}` / `{tier_age_range}` — see §5
before assuming these do anything on their own.

### A1 — Remove the count quota (uncapped enumeration)

**Mechanism.** v4 already has an escape clause ("数は目標であって義務ではない") but still
states a range ("3 つ以上 5 つ以下") right next to it — the number is on the page even
though it's optional, and TASK-735's own measurement shows the model padding anyway on both
residual failures (向き, 可笑し on 昔). A1 deletes every digit from the instruction. The
procedure becomes "walk every mora position to the end, keep whatever is real, stop — that
count is the answer," with no number anywhere to anchor against. The renderer's own floor
(`options` list must be ≥4 before the judge even runs —
`exercise_renderer.py:483`) still means an item with fewer than 3 surviving candidates is
lost; A1 accepts that loss as correct behavior rather than a bug, same as v4's stated
principle, just applied without a visible target to drift back toward.

- **Files/rows:** `prompt_templates` id 376 → new version (ja only). No code change beyond
  the two tier placeholders shared by all of Track A (see §5).
- **Contract:** unchanged. Same `OPTION_KEY_MAP`, same 4–6-option shape, same judge call.
- **Failure modes:** a genuinely isolated word (few one-mora neighbors exist at all) now
  returns exactly what exists, which may be <3 and drop the item — this is the same
  all-or-nothing loss TASK-735 already lives with, not a new one. Risk this doesn't move
  the needle: the anchoring effect of a stated number may be weaker than TASK-735's own
  diagnosis suggests, in which case padding persists for other reasons (e.g. the model
  treating "give a complete-feeling answer" as a soft goal independent of any stated digit).
- **Cost/wall-clock:** unchanged — same call, same token budget. No new spend.
- **validators.py / renderer / applier:** no change needed.

**Plain English.** The current instructions tell the model "find 3 to 5 real near-matches,
but it's OK to stop early if you can't." The trouble is the number "3 to 5" is still sitting
right there, and a model under an implicit expectation to look complete tends to reach for
it anyway — even when the instructions say it doesn't have to. A1 strips the number out
entirely: the only instruction left is "check every position, keep what's real, stop." A
learner sees no difference if this works — the exercise looks identical. The catch: if the
model was padding for some other reason than "there's a number nearby," removing the number
won't fix it, and this is the cheapest and least certain of the three prompt rewrites to
test.

### A2 — Structured lexical retrieval (visible verification grid)

**Mechanism.** Force the model to emit a scratch, non-scored JSON field — a mora-by-mora
substitution grid (`{"position", "original_mora", "substituted_mora", "candidate_reading",
"is_real_word", "surface_form", "meaning"}` per attempt) — as a sibling top-level key to
`"1"`/`"3"`/`"5"`/`"6"`, before the L1 answer, and constrain the L1 answer to draw *only*
from rows the grid itself marked `is_real_word: true`. This is a self-consistency
constraint, not a request to "think harder": the model cannot use a word in its answer that
its own grid didn't first mark as verified, which makes free-associate-then-rationalize (the
mechanism TASK-735 diagnosed for 向こうし/無蚊地 — commit to a spelling, then justify it)
structurally harder to do without the contradiction being visible in the same response.

- **Files/rows:** same single row as A1.
- **Contract:** traced through the actual parsing code before drafting this, not assumed
  safe. `_remap_output` (`prompt2_exercises.py:169`) only reads `raw[level_key]` for
  `level_key in {'1','3','5','6'}` (whichever are active) — an extra top-level key like
  `"l1_grid"` is never read, never remapped, silently ignored. `remap_keys` itself
  (`config.py:1045`) preserves unmapped keys under their original name rather than dropping
  them, so even a stray key *inside* an option object would survive but sit unused by
  `validators.py` (which only reads `text`/`is_correct`/`explanation`). **Confirmed
  zero-risk to the JSON-key contract**, not merely plausible.
- **Failure modes:** token cost per call rises (the grid itself is verbose — for a
  short-reading word like 一 it's cheap; for a long reading with many mora positions ×
  candidate substitutions it could run to hundreds of extra tokens). A model that fills the
  grid honestly but then ignores its own `is_real_word: false` rows anyway defeats the whole
  point — this is a real risk with `response_format='json'` under weaker instruction
  adherence, and is exactly the kind of thing worth measuring rather than assuming.
- **Cost/wall-clock:** modestly higher per call than today (more output tokens for the
  grid); no new call. Order of magnitude: same call, maybe 20–40% more output tokens for
  words with many mora positions. Not a material line-item at 150 senses.
- **validators.py / renderer / applier:** no change. `check_row()` in the applier script
  would need `"l1_grid"` added nowhere — it isn't a `must_go`/`must_have` token, it's new
  content, and the existing placeholder-safety check (`placeholders()` /
  `CALLER_ARGS`) only inspects `{bare_identifier}` substitution tokens, which this doesn't
  add beyond the two tier placeholders.

**Plain English.** Right now the model is asked to search for real near-matches and then
just report what it found — there's no way to check its work. A2 makes it show its work: it
has to fill in a little table first (each attempted substitution, and whether that came out
to a real word or not), and then it's only allowed to use words from that table that it
marked "real." It's the difference between asking someone "did you check?" and making them
write the checklist down before they answer — a habitual liar can still lie on the
checklist, but it's a harder lie to tell consistently than a bare assertion. The catch: this
makes every L1 call a bit more expensive (the checklist itself costs tokens), and it doesn't
help at all if the model is willing to mark something "real" on the checklist that isn't —
in which case the extra structure is theater.

### A3 — Few-shot worked negatives

**Mechanism.** The en row (id 173) has never fabricated a word and is entirely rule-based —
no examples. So this isn't "copy what worked for en." It's the opposite hypothesis: en's
strictness comes from tight, closed rules over a small, well-understood phoneme inventory;
ja's failure modes (orthographic invention, classical-form leakage, accent confusion) are
more varied and better taught by concrete cases than by an eighth abstract bullet point. A3
adds four worked (target, rejected candidate, reason) examples, one per failure class
observed or plausible: **fabrication** (向こうし/無蚊地, the actual TASK-735 case),
**accent-only** (機会/機械, actual case), **register/rarity** (可笑し — real, but archaic,
flagged as tier-dependent), and **synonymy** (an illustrative, not-yet-observed case,
flagged as such — see below).

- **Files/rows:** same single row as A1/A2.
- **Contract:** unchanged, no new fields.
- **Failure modes:** few-shot examples can leak a *pattern* the model over-generalizes from
  rather than the *principle* behind it — e.g. if it learns "avoid 可笑し specifically"
  rather than "avoid archaic register," the fix doesn't generalize past that one word. This
  is a known risk with worked examples generally, and is exactly why the report calls out
  which example is illustrative-not-measured: the synonymy example is invented for this
  draft (I could not find a recorded case of the generator producing a same-mora-distance
  synonym; it is included because the failure mode is real in principle, not because it has
  been observed in ja generation).
- **Cost/wall-clock:** the four examples add roughly 400–500 characters to the prompt —
  cheap relative to the ~2,400-character live template, no material spend change.
- **validators.py / renderer / applier:** no change.

**Plain English.** Instead of telling the model rules in the abstract ("don't invent
words," "don't use accent-only pairs"), A3 shows it four worked examples: here is a target
word, here is a specific wrong answer that was actually generated for it, and here is
exactly why it's wrong. People (and models) often generalize better from "here's a mistake
and why it's a mistake" than from a rule stated in isolation — it's the difference between
"be careful with knives" and "here's someone who cut themselves reaching for the blade
first, and here's why." The catch: worked examples can teach the specific example instead
of the principle behind it — a model that avoids 可笑し by name without understanding *why*
(it's archaic) hasn't actually learned the register rule, and one of the four examples here
is a guess at a failure that hasn't actually happened yet in ja generation, so its
usefulness is unverified by construction.

---

## Track B — different architectures

Two designs, both centered on a fact I checked directly rather than assumed: the project
already depends on `fugashi` + `unidic-lite` (`requirements.txt:71-72`), used today by
`services/furigana_service.py` to tokenize text and pull each token's reading
(`feature.kana`/`feature.pron`) via `_extract_reading()`. That is a real, working,
already-tested Japanese lexical resource sitting one import away — but I want to be precise
about what it does and doesn't give for free, because my first framing of this
(over)promised more than the installed package actually delivers.

**What I checked before designing around it:** the installed `unidic-lite` package ships
only a *compiled* MeCab dictionary (`sys.dic`, ~187MB) — no source CSV, and fugashi's
`Tagger` exposes `dictionary_info()` (metadata) but no entry-enumeration API. I confirmed
this by listing the package's `dicdir` directly rather than assuming from its name.
**Consequence: there is no free "give me every word one mora away from むかし" query
available today.** What *is* free is the reverse operation the furigana service already
does: hand it a surface string, get back whether/how it tokenizes and what its reading is.
That distinction is why B1 and B2 below are shaped the way they are.

### B1 — Deterministic existence gate (verify, don't generate)

**Mechanism.** Keep LLM candidate generation exactly as today (any of A1/A2/A3, or even the
live v4 prompt unchanged) but insert a new, non-LLM, zero-latency check between generation
and the judge: tokenize each proposed distractor with the existing `fugashi.Tagger()` and
accept it only if (a) it comes back as **exactly one token** spanning the full string (a
fabricated compound like 向こうし splits into known sub-tokens — 向こう + し — under UniDic's
unknown-word handling, which is exactly the signal that it isn't a real headword) and (b)
that token's extracted reading (`_extract_reading()`, already written) matches the intended
one-mora-shifted reading. This is a hard gate a model cannot argue its way past — it is not
another prompt asking the model to be careful, it is code that either finds a matching
dictionary token or doesn't.

This also gets the pitch-accent problem for free, structurally, not by asking a judge to
notice it: a same-mora-distance candidate is generated by construction to have a *different*
reading from the target (that's what "one mora substituted" means), so a same-reading,
different-accent pair like 機械/機会 can never arise from this search process at all — there
is no step where the target's own reading is offered back as a candidate. The judge's
"reject accent-only pairs" rule becomes unreachable dead code for candidates that pass
through this gate, not a rule that has to keep working.

- **Files:** new `services/vocabulary_ladder/l1_lexicon_gate.py` — wraps
  `services.furigana_service._get_tagger()` (reuse the existing cached tagger, don't spin up
  a second one), exposes `verify_candidate(surface: str, expected_reading: str) ->
  bool`. Called from `exercise_renderer._render_phonetic` (`exercise_renderer.py:470`),
  before or alongside the existing `filter_l1_distractors` call — candidates failing the
  lexicon gate are dropped before the judge ever sees them (saves judge tokens on the
  fabrications specifically, which is a fraction of what's spent today ruling them out via
  an LLM call that has to reason "is 無蚊地 a real place name?").
- **Contract:** no change to `prompt_templates`, no new placeholders, no JSON-key change.
  The gate operates on the already-remapped `text` field of each option, after
  `_remap_options` — pure post-processing.
- **Age tiers:** does not touch tier at all — existence is a yes/no fact, not a
  tier-relative one. Tier-appropriateness of a *verified-real* word is still a judgment call
  (register, rarity) and stays with the judge (or a tier-aware prompt tweak per §5).
- **Failure modes:** UniDic tokenization false negatives — a real, valid word that
  unidic-lite's dictionary happens not to carry (it's a "lite" build, trimmed for size) would
  be wrongly dropped as if fabricated. This trades one error direction for the opposite one:
  today the risk is a fabrication slipping through as "real"; this risk is an actually-real
  word being discarded as if fake. Needs measurement against the existing recorded distractor
  sets (`word_assets` L1 content from the TASK-735 canary) before trusting it — cheap, no
  LLM spend, pure local code (see §7).
- **Cost/wall-clock:** strictly cheaper than today. Removes zero LLM calls by itself (the
  judge still runs on whatever survives) but shrinks the judge's job and removes its hardest
  failure mode. No added latency worth counting — a single tokenizer call is low-single-digit
  milliseconds, already paid by every ja furigana-bearing page.
- **validators.py / renderer / applier:** `exercise_renderer.py` gets a new gate call;
  `validators.py` unchanged (still validates the same option-count band).

### B2 — Precomputed phonetic-neighbor index

**Mechanism.** The "big" version of the same idea: build a reading→headword index *once*,
offline, so L1 generation becomes a table lookup instead of a live search — for every ja
target reading, the one-mora neighbor list is already known before the pipeline runs.

Two ways to source the index, both requiring real new engineering (not something already
sitting in the repo, and I want to be explicit that this is a bigger lift than B1):

1. **JMdict** (EDRDG, freely redistributable with attribution) — a purpose-built
   machine-readable dictionary with explicit (kanji, reading, sense) entries, ~180k+ words.
   The natural fit for "what does this reading correspond to as a headword," better suited
   to this than a tokenizer's internal trie.
2. **Re-derive the unidic-lite source CSV.** The compiled `sys.dic` installed locally came
   from a CSV during `pip install`; the CSV itself wasn't kept. Re-fetching and parsing it
   is possible but ties the index to whatever unidic-lite's upstream build source currently
   serves, which is a less stable dependency than a dictionary file checked into the repo.

I'd source from JMdict — it's the resource actually designed for this question, and its
license and format are well-trodden ground for exactly this kind of lookup table.

- **Files:** new one-time build script `scripts/build_ja_phonetic_index.py` (parses JMdict,
  computes mora segmentation per reading — needs a small deterministic mora-tokenizer for
  hiragana/katakana, handling small-tsu/yōon digraphs — and for every entry finds every
  other entry exactly one mora away); output stored as a new table, e.g.
  `ja_phonetic_neighbors(target_reading, candidate_surface, candidate_reading,
  contrast_type, zipf)` (zipf via the already-used `wordfreq.zipf_frequency`, for the tier
  filter in §5). At generation time, `_render_phonetic` (or a new
  `asset_generators/l1_lookup.py`) queries this table instead of calling the P2 generator
  for level 1 specifically — L1 is pulled **out of** the shared P2 call; L3/L5/L6 keep
  generating through `vocab_prompt2_exercises` unchanged.
- **Contract:** this is the one proposal that changes shape. `word_assets` content for L1
  would come from a different code path than L3/L5/L6, though the *stored* `level_1` dict
  can still be written in the same descriptive-key shape (`options`, `explanations`,
  `correct_answer`) so `exercise_renderer.py` doesn't need to change its read side. What
  disappears: the `vocab_prompt2_exercises` L1 block entirely (L1 is no longer part of that
  prompt or that call). What's needed instead: either templated explanations
  (`"「むかえ」は対象語と一モーラ差（し→え）"` built from `contrast_type`, no LLM at all) or
  a short LLM pass over the pre-verified candidates only for phrasing + synonym/tier
  filtering — draft in
  [`data/eval/task736/b_rank_and_explain_ja.txt`](../../data/eval/task736/b_rank_and_explain_ja.txt),
  proposed as a **new** `prompt_templates` row (`ladder_l1_candidate_ranker`), not a
  version bump of an existing one.
- **Age tiers:** this is where tier-as-vocabulary-band (§5) fits most naturally — the
  `zipf` column on each neighbor row means "give me candidates within tier T2's frequency
  band" is a `WHERE` clause, not a judgment call the model has to make freshly per item.
- **Failure modes:** the index goes stale as new senses are added or JMdict updates — needs
  a rebuild policy (e.g., rebuild on JMdict version bump, or when `dim_word_senses` grows by
  N). A bad build affects **every** ja sense until rebuilt, which is a materially larger
  blast radius than a bad prompt version (rollback there is one `is_active` flip; rollback
  here is "regenerate a multi-hour offline index or fall back to Track A/B1 for anything the
  index doesn't cover"). Coverage gaps (a target reading with no JMdict-attested neighbor)
  need a defined fallback — most plausibly, fall through to B1's live-verified path rather
  than silently losing the item.
- **Cost/wall-clock:** near-zero marginal cost per sense once built (`~$0`, a DB read) —
  the entire spend is the one-time build (JMdict parsing is free/local; if a QA sampling
  pass over the built index is added, budget a few dollars for a sample, not the whole
  table). This is the only proposal in this report where **the ongoing per-sense cost of
  L1 drops to roughly zero**, which matters if the 150-sense ja build isn't a one-time
  event but something re-run as new senses land.
- **validators.py / renderer / applier:** `OPTION_COUNTS[1]` can likely tighten back toward
  `(4, 4)` eventually (a lookup with a defined fallback shouldn't need the same over-generate
  cushion an LLM does) but I would NOT change it in the same pass that ships B2 — keep the
  cushion until the lookup's own miss rate is measured. New applier entry needed for the new
  `ladder_l1_candidate_ranker` row, following the existing `apply_task735_ja_l1_fixes.py`
  pattern (`must_go`/`must_have`, EOL detection, verify-after-write).

**Plain English (B1 and B2 together).** Right now, checking "is this a real word" is a job
we hand to an AI model, which occasionally makes something up and states it confidently. B1
and B2 both replace that specific check with a dictionary lookup — the same kind of thing a
spell-checker does, not a language model's opinion. B1 does this lookup live, on whatever
the AI proposes, right before the exercise is finalized — think of it as a fact-checker
standing between the writer and the printer, catching invented words with a real reference
book rather than by asking the writer "are you sure?" a second time. B2 goes further: it
builds, once, a complete reference table of "these words sound almost identical to these
other words" for the whole language, so that when a new lesson needs a listening exercise
for a word, the system just looks up its neighbors instead of having an AI search for them
from scratch each time. The honest catch for B1: it can occasionally throw out a real but
obscure word because the dictionary it's checking against happens to be missing that
particular entry — a different mistake than fabrication, but still a mistake, and it needs
to be measured before trusting it. The honest catch for B2: it's a genuinely bigger build
(a new reference dictionary has to be brought in and processed), and once it's built, a
mistake in that one build affects every single word in the language until someone notices
and rebuilds it — versus today, where a bad prompt only affects the words generated while
that prompt version was active.

### Considered and rejected: retrieval from `dim_vocabulary` alone

The brief explicitly raises this ("guaranteeing every distractor is a word the system
already knows and can gloss"). Checked and rejected as the *primary* candidate source: ja
`dim_vocabulary` has 2,404 rows. The words a target actually needs as one-mora neighbors are
overwhelmingly *not* curated ladder headwords — they're ordinary dictionary words (迎え,
向かい, 百足 for 昔) that have no reason to already be in a 2,400-word teaching pool. This is
effectively confirmed by the existing failure mode: the model already tries to draw on
general vocabulary knowledge and only fails when it runs out of *real* candidates near a
sparse word, not because it's ignorant of the ladder's own word list. Using `dim_vocabulary`
as the *sole* source would trade "the model sometimes fabricates" for "the model usually
finds nothing," which is a worse render rate, not a better one. It remains useful as a
secondary signal (a distractor already in `dim_vocabulary` is one the system can already
gloss and has already vetted), which is where B2's design keeps a hook for it (candidates
that also exist in the ladder's own pool could be preferred/ranked higher), but not as the
only source.

---

## 5. The tier question, argued

The brief asks directly: should phonetic distance scale with tier, or should tier govern the
vocabulary pool instead? Arguing for **vocabulary pool, not distance**:

1. **One-mora distance is the skill being trained, not a difficulty knob.** The brief's own
   framing is that L1 trains "the mapping from sound to orthography, which in Japanese is
   the hard part." A T1 four-year-old's ear does not become worse at discriminating one mora
   of difference because they're younger — if anything, loosening the distance to
   two-or-more morae for low tiers makes the item *easier to solve without careful
   listening*, which is the opposite of what the exercise is for. Scaling distance by tier
   risks quietly changing what the exercise measures at each tier, rather than just how hard
   it is.
2. **A single doctrine is what TASK-735 fought to establish, and it's fragile.** Project
   memory (`ja-l1-judge-and-generator-doctrine`) already flags that a closed enumeration in
   a judge prompt is an allow-list, and generate→judge pairs can contradict invisibly — this
   is exactly what happened with v2's four-contrast-type closed set and the
   generator/judge accent-only disagreement. Making the *distance rule itself* conditional
   on tier means the judge now needs six rule-sets instead of one, doubling the surface area
   for the two prompts to silently disagree again, in a language pair where that has already
   cost real debugging time twice.
3. **Vocabulary-band filtering reuses infrastructure that's already calibrated and tested.**
   `tier_gate.TIER_GATE_PROFILES` + `wordfreq.zipf_frequency` already define, per tier, what
   frequency band a *sentence's* vocabulary should sit in, and it's live in the P1 sentence
   path today. Applying the same profiles to *distractor* vocabulary is not a new
   calibration exercise — it's pointing an existing, tested mechanism at one more kind of
   text. This is the same reasoning A1–A3's "関門 5" clauses lean on, and it's what B2's
   `zipf` column is for directly.
4. **It matches the observed residual failure.** TASK-735's own writeup calls 可笑し
   ("archaic form") a bad distractor — not because it's more than one mora away (it isn't),
   but because it's the wrong *register* for a modern-day exercise. That's a vocabulary-band
   problem, not a distance problem, and the fix the data points to is the one this section
   argues for.

**This entire discussion is inert until §0's prerequisite is fixed.** `complexity_tier`
resolves to `'T3'` for every sense today. A vocabulary-band filter conditioned on tier, no
matter how well designed, filters against a constant — it cannot distinguish a T1 word from
a T6 word because the pipeline never tells it which one it's looking at.

---

## 6. Comparison across every proposal

Render rate and fabrication numbers below are **predictions**, not measurements — none of
these have been run live (budget instruction: ask before spending on generation runs; see
§8). The only measured numbers in this document are the ones carried over from TASK-735
(baseline 1/2 variants render, 0/7 fabrications after v4).

| Proposal | Fabrication risk | Expected render rate (vs. 1/2 baseline) | Cost / 150 senses | Build effort | Blast radius if wrong |
|---|---|---|---|---|---|
| A1 uncapped enumeration | Low–medium — same generator, still self-reported | Uncertain, could go either way | No change (~$3–6, same call as today) | XS — one prompt edit | Low — one `prompt_templates` row, rollback = flip `is_active` |
| A2 structured retrieval | Low — self-consistency constraint, but not enforced outside the model | Medium–high, if instruction-following holds | Slightly higher (+20–40% output tokens on long readings) | S — one prompt edit, verified contract-safe | Low — same as A1 |
| A3 worked negatives | Low–medium — generalizes from examples, may overfit to the named cases | Medium–high | Small increase (~500 extra chars/call) | S — one prompt edit | Low — same as A1 |
| B1 existence gate | Structurally eliminated for the fabrication class specifically | High, bounded by unidic-lite coverage gaps (opposite failure direction) | Lower than today (judge does less work) | M — one new module, wired into the renderer | Medium — new code path, needs a false-negative check against real TASK-735 words before trusting |
| B2 precomputed index | Structurally eliminated | High, bounded by JMdict coverage and index freshness | Lowest ongoing (~$0/sense after build; build cost is engineering time, not LLM spend) | L–XL — new dependency (JMdict), new table, new build script, L1 pulled out of the shared P2 call | High — a bad build affects every ja sense until rebuilt; needs a defined fallback for lookup misses |
| dim_vocabulary-only retrieval (rejected) | Structurally eliminated | Low — pool too small (2,404 rows) to cover most targets | N/A | N/A | N/A — not recommended |

Pitch-accent-only collision (箸/橋, 機械/機会) is structurally impossible in **both** B1 and
B2, for the same reason: the candidate-generation step only ever produces readings that
differ from the target by construction, so a same-reading pair can never reach the judge.
Track A proposals still rely on the judge's explicit rule for this, as today.

**What the judge would still be for, if B1/B2 make existence and pitch-accent moot** — the
brief asks this directly. Two things survive: **synonymy** (a verified-real, correctly
one-mora-different word can still mean nearly the same thing — nothing about dictionary
lookup checks meaning) and **register/tier fit** (a verified-real word can still be archaic,
overly technical, or otherwise wrong for the learner in front of it — §5). Both B1 and B2's
designs keep exactly this narrower judge role; the draft in
[`b_rank_and_explain_ja.txt`](../../data/eval/task736/b_rank_and_explain_ja.txt) is scoped
to precisely those two checks plus writing the explanation, nothing else.

---

## 7. Recommendation

**Ship B1 first, independent of everything else — it's the cheapest, lowest-risk, and
attacks the one failure mode that's actually cost real debugging time twice
(fabrication).** It needs no new prompt version, no new dependency, and no new table — it
reuses `furigana_service`'s already-cached tagger as a hard gate the judge doesn't have to
reason its way through. It can sit in front of *any* Track A prompt, including the unchanged
v4, so it isn't a competing proposal to A1–A3 so much as a foundation under them.

**Pair it with A2 (structured retrieval), not A1 or A3, if a prompt rewrite is wanted at
all.** A2 is the one Track A proposal I confirmed is contract-safe by tracing the actual
parsing code rather than by inspection of the prompt text alone, and its self-consistency
constraint is a genuinely different mechanism from v4's already-tried "state the rule more
forcefully" approach — A1 and A3 are both variations on "ask more clearly," which is the
category of fix TASK-735 already spent three rounds on. B1 makes the fabrication question
moot underneath A2 regardless of whether A2's own discipline holds, which is exactly the
belt-and-suspenders combination this task's framing ("rather than a fourth round of the same
tuning...") is asking for.

**Do not build B2 in this pass.** It is the correct end-state (near-zero marginal cost,
structurally sound) but it requires a new dependency (JMdict), a new table, a rebuild policy,
and pulling L1 out of the shared P2 call — real engineering, not a measurement-and-ship
task, and it should follow a B1 measurement that shows the deterministic-gate idea actually
works before investing in the full precomputed version of it. Building the expensive version
first, before confirming the cheap version's core assumption (that a hard existence check is
what's actually missing) holds up, is the wrong order.

**Fix the tier-signal prerequisite (§0) as its own small task, regardless of which L1
proposal ships.** It's five lines, reuses `tier_gate.tier_for_lemma`, and unblocks every
tier-aware idea in both tracks — including ones this report didn't need to invent, since the
mechanism to use already exists.

**What I would not do:** scale phonetic distance by tier (§5, argued against); use
`dim_vocabulary` as the sole candidate source (too sparse, §4); or ship a fourth round of
Track-A-only prompt tuning without B1 underneath it — the brief's own framing is that three
rounds of that already happened, and the residual failures are exactly the kind (existence
verification) a hard gate settles better than a fourth wording of the same rule.

---

## 8. Measurement plan

For the recommended pairing (B1 gate + A2 prompt), before touching the live DB:

1. **Widen the sense pool first.** `SENSES = (34997, 35001)` in
   `scripts/smoke_task735_ja_l1.py` is n=2 and openly flagged in TASK-735 as over-fit.
   Widen to ~10 senses spanning a range of neighbor-density (some words with many
   one-mora neighbors, some sparse) before drawing conclusions from any of this.
2. **B1 gate, free.** Run the existence-gate check (no LLM calls, pure local code) against
   every distractor already recorded in `word_assets` from the TASK-735 canary
   (`ja-20260822-232552`) plus the wider pool's existing content, if any. Compare its
   keep/reject calls against the two known-fabricated words (向こうし, 無蚊地 — must both be
   rejected) and every word the human-reviewed TASK-735 writeup already confirmed real (向き,
   迎え, 百足, 可笑し, 理解, 議会, 期待 — must all be kept). Zero LLM spend. This alone tells
   us the gate's false-negative rate on known-good words before it ever touches a live
   generation call.
3. **Then, and only with approval, a live `--gen` pass** over the widened pool: A2 draft as
   the generator prompt (new version, not applied — passed directly to
   `ExerciseAssetGenerator` the way the existing `--gen` smoke path already does), B1 gate
   applied to its output, existing judge (v3, id 374) on what survives. Estimated cost:
   the existing `--gen` path runs ~$0.02/sense/variant; ×10 senses ×2 variants ≈ **$0.40**,
   in the same range as TASK-735's own "$0.20 to widen to 10 senses" estimate.
4. **The number that counts: render rate over the ~10-sense pool** — how many of the
   (sense × variant) pairs produce ≥3 kept distractors, matching
   `exercise_renderer._render_phonetic`'s actual gate. Baseline is 1/2 (50%) on the n=2 pool
   today; **success is materially above that on the wider pool**, not a specific target
   number picked in advance, because n=2 is too small to have established what "normal" render
   rate even looks like for ja L1. Keep rate (distractors kept ÷ distractors proposed) is a
   diagnostic for *why* a variant did or didn't render, not the thing being optimized.

---

## 9. What I could not determine

- **Whether A1's "remove the number" actually changes model behavior** — this is a
  hypothesis about anchoring that only a live A/B run can confirm or refute; I have no way
  to test it without spending against the budget hold.
- **The true false-negative rate of unidic-lite (B1) or JMdict coverage (B2) against ja
  vocabulary at the tiers this ladder actually needs.** Both are estimable cheaply (§8 step
  2 for B1; a JMdict coverage check against the existing 2,404-word `dim_vocabulary` pool for
  B2) but neither has been run — both are local/free and worth doing before committing to
  either, but weren't run here because they weren't necessary to write this report and I
  wanted the measurement plan itself to be the next approved step, not something buried
  inside the exploration pass.
- **Whether `TIER_GATE_PROFILES`' existing frequency bands (calibrated for screening
  *sentences*) transfer cleanly to screening *single-word distractors*.** The mechanism is
  proven for one text genre; whether the same zipf thresholds feel right for an isolated
  word out of context (no surrounding sentence to support comprehension) is a genuine open
  question a native-speaker review would settle faster than more code-reading would.
- **The synonymy worked example in A3** is invented, not observed — flagged inline in §Track
  A / A3, repeated here because it's the one piece of this report's *content* (as opposed to
  its architecture) that should not be trusted without a native check before use.

---

## Next step

This report ends at a recommendation, per the brief. Section 8's measurement plan
(specifically step 2, which costs nothing) is the natural next action; step 3 (~$0.40) needs
explicit go-ahead before running, per the budget instruction this task was given.
