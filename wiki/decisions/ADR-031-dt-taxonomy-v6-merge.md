---
title: "ADR-031: Dual Translation Taxonomy v6 — Merge with jev Grammar Taxonomy"
status: proposed
date: 2026-09-27
---

# ADR-031: Dual Translation Taxonomy v6 — Merge with jev Grammar Taxonomy

## Context
The live Dual Translation (DT) error taxonomy is **v5** ([[business-rules/translation-error-taxonomy]],
`migrations/dt_taxonomy_v5_seed.sql`): 15–17 subtypes per language, each carrying `dimension`
(accuracy/fidelity/naturalness — read by `services/dual_translation/scoring.py` to compute per-dimension
bands), `default_severity`, `treatable`, and `cloze_suitable`. Every subtype is also keyed into
per-user profiles (`dt_error_profile_entry`), remediation cards (`cards.py`), and the grading cascade
(`grader_cascade.py`, `explainer.py`).

Independently, a new single-sentence grammar taxonomy was built for the **jev** classifier
(`data/eval/jev_grammar_2026-09-26/taxonomy.md`, TASK-related to `typesafe/jev-1.13`). It defines
13–17 core types per language (zh/ja/en), each with a G/S/T/R class, a one-line definition, worked
examples at three subtlety levels, an explicit "not an error" list, and groups types into 8 yes/no
question buckets (B1–B8) for a cheap classifier. It is considerably finer-grained on grammar (e.g. it
splits zh's `de_particles` into a narrower rule, splits ja's `particle_wa_ga` down to three structural
cases, and adds types v5 never had: zh `separable_verb`/`coverb`/`connective`, ja `transitivity_voice`/
`modification`/`clause_linkage`/`kanji_choice`, en `complementation`/`lexical_form`). It also carries
three rubric-mandated `target_*` types (`target_absent`, `target_not_whole_word`, `target_in_idiom`)
that only make sense against a single **locked target word** in a P1 ladder sentence — DT grades whole
multi-sentence passages with no such locked target, so these do not transfer.

The two taxonomies currently disagree on where the line between "grammar error" and "not an error"
falls (e.g. jev explicitly says 的-for-地 and most main-clause は/が choices are **not** errors, while
v5's `de_particles`/`particle_wa_ga` cover them). Running DT scoring against v5 while grading sentences
against jev's stricter/narrower judgment would silently misclassify errors and mis-score submissions.

## Decision
Merge the two taxonomies into a single **v6** per-language type list:

1. **Keep** v5's 8 translation-level (non-grammar) types as-is: `omission`, `addition`, `word_choice`,
   `collocation`, `word_order`, `register`, `orthography`, `cohesion_connective`. `word_choice` also
   absorbs jev's `wrong_sense` (both describe "right word family, wrong sense/lexical item"); the
   explanation level splits it three ways via `explanation_variant` (`wrong_word` | `wrong_sense` |
   `shared_translation` — see Consequences).
2. **Replace** v5's coarse per-language grammar subtypes with jev's finer grammar types, 1:1 where a
   clean correspondence exists (renames), **merging** where jev collapses several v5 types into one
   (zh `ba_construction`+`bei_passive` → `ba_bei`; zh `resultative_complement`+`directional_complement`
   → `complement`; zh `adverbial_order` → folded into `word_order`), and flagging a **split** where
   jev's definition is strictly narrower than v5's (ja `particle_wa_ga`, en
   `pronoun_reference` — see mapping summary below). zh `de_particles` → `de_particle` is now a **1:1**
   mapping, not a split (user decision 2026-09-27 — see Consequences): any 的/地/得 misuse is an error
   under v6, so the narrowing jev originally proposed for 的-for-地 does not apply. Two v5 types have no jev equivalent and are
   **retained as legacy** (zh `topic_comment`, ja `topic_comment`/`particle_other`, en `plural_number`/
   `phrasal_verb`). One v5 type is **dropped** because jev explicitly classifies it as not an error
   (ja `script_choice`: kana/kanji spelling choice for the same word).
3. **Drop** jev's three ladder-only `target_*` types — no locked target word exists in a DT passage.
4. **Add** three new types per language: `semantic_anomaly`, `contradiction`, and `meaning_inversion`.
   `contradiction` is restored to jev's own scope — a sentence-internal logical/self-contradiction
   detectable from the translation text alone (time clash, relational impossibility, world-knowledge
   clash; en additionally keeps jev's "a connective asserts the wrong relation" clause) —
   `default_severity: major`. `meaning_inversion` is a new split-off type for the case the first draft
   had conflated into `contradiction`: the translation's core claim is the polarity/direction/quantity/
   agent reverse of the **reference** (a dropped/added negation, an antonym swap, a reversed direction,
   a flipped quantity, swapped agent/patient — e.g. "with" rendered as "without"), detected by comparing
   against the reference rather than self-evident from the translation alone. `meaning_inversion` keeps
   `default_severity: critical` — the first taxonomy use of the `critical` MQM tier that
   [[business-rules/translation-error-taxonomy]] defines but v5 never populated (this is exactly the
   "meaning breaks or inverts" reader-impact test for `critical`). All three are dimension `fidelity`
   except `semantic_anomaly` and `contradiction`'s `class` stays `S`; `meaning_inversion` also carries an
   explicit (not-yet-finalized) boundary-rule note against `omission`/`word_choice` in its definition.
   This split, and three other independent-reviewer-driven corrections (ja `kanji_choice` and en
   `lexical_form` moved `fidelity` → `accuracy`; zh `connective` moved `minor` → `major`), were applied
   after an author/reviewer exchange under jev taxonomy.md §0.8 — see
   [[../../data/eval/taxonomy_merge_2026-09-27/review/|review/]] (`{zh,ja,en}_review.json` +
   `author_response.json`) and the Open Questions below.
5. **Add** a first-class `jev_bucket` field (B1–B8, nullable) to every type, carrying over jev's
   bucket structure so a future jev-backed grader can reuse the yes/no bucket questions directly. Two
   of the "retained-legacy" v5 types with no original jev match — en `phrasal_verb`, ja `particle_other`
   — were subsequently **ported into jev's own taxonomy** (`taxonomy_addendum_2026-09-27.md`, user
   decision 2026-09-27) and now carry real buckets: `phrasal_verb` → jev B1, `particle_other` → a new
   jev **B9** bucket.
6. Every merged type carries: `id`, English name, native (zh/ja) name, `class` (G/S/R/D/F — grammar,
   semantic/lexical, register, discourse/naturalness, fidelity/completeness), `dimension`
   (accuracy/fidelity/naturalness, required by `scoring.py`), `default_severity`, `jev_bucket`,
   `treatable`, `cloze_suitable`, and a one-line definition.

## Per-language merged type counts

| Language | v5 count | v6 (merged) count | New (from jev) | New (not from jev) | Dropped | Retained-legacy (no jev match) | Ported to jev (§B9 note) |
|---|---|---|---|---|---|---|---|
| zh | 17 | 20 | `separable_verb`, `coverb`, `connective`, `semantic_anomaly`, `contradiction` (5) | `meaning_inversion` (1) | — (0) | `topic_comment` (1) | — |
| ja | 17 | 23 | `transitivity_voice`, `modification`, `clause_linkage`, `kanji_choice`, `semantic_anomaly`, `contradiction` (6) | `meaning_inversion` (1) | `script_choice` (1) | `topic_comment` (1) | `particle_other` → jev B9 |
| en | 15 | 20 | `complementation`, `lexical_form`, `semantic_anomaly`, `contradiction` (4) | `meaning_inversion` (1) | — (0) | `plural_number` (1) | `phrasal_verb` → jev B1 |

Full list per language, with all 8 required fields: [[../../data/eval/taxonomy_merge_2026-09-27/merged_taxonomy.json|data/eval/taxonomy_merge_2026-09-27/merged_taxonomy.json]].

### Compact type table (grammar-family changes only; translation-level types 1:1 as listed above)

| zh v5 → v6 | ja v5 → v6 | en v5 → v6 |
|---|---|---|
| classifier → `measure_word` (rename) | particle_wa_ga → `wa_ga` (**split**, narrower) | article → `article_determiner` (rename) |
| aspect_marker → `aspect_negation` (merge, +negation) | particle_case → `case_particle` (rename) | preposition → `preposition` (same) |
| de_particles → `de_particle` (**1:1**, revised 2026-09-27) | particle_other → `particle_other` (retained) | tense_aspect → `verb_form_tense` (rename) |
| ba_construction + bei_passive → `ba_bei` (merge) | verb_conjugation → `conjugation` (rename) | subject_verb_agreement → `agreement` (rename) |
| resultative_complement + directional_complement → `complement` (merge) | tense_aspect_ja → `tam` (merge, +modality) | plural_number → `plural_number` (retained) |
| adverbial_order → `word_order` (merge) | keigo_register → `keigo` (rename) | phrasal_verb → `phrasal_verb` (**ported to jev B1**, see below) |
| — (new) → `separable_verb`, `coverb`, `connective` | counter_classifier → `counter` (rename) | pronoun_reference → `pronoun` (**split**, narrower) |
| topic_comment → `topic_comment` (retained) | script_choice → **dropped** | — (new) → `complementation`, `lexical_form` |
| — (new, split off `contradiction`) → `meaning_inversion` | particle_other → `particle_other` (**ported to jev B9**, new bucket) | — (new, split off `contradiction`) → `meaning_inversion` |
| | topic_comment → `topic_comment` (retained) | |
| | — (new) → `transitivity_voice`, `modification`, `clause_linkage`, `kanji_choice` | |
| | — (new, split off `contradiction`) → `meaning_inversion` | |

Full row-by-row mapping (every v5 subtype and every jev type, with mapping kind and notes):
[[../../data/eval/taxonomy_merge_2026-09-27/v5_to_merged.csv|v5_to_merged.csv]],
[[../../data/eval/taxonomy_merge_2026-09-27/jev_grammar_to_merged.csv|jev_grammar_to_merged.csv]].

## Mapping summary + impact counts

Mapping kinds used across all three languages' v5 subtypes (32 rows total, incl. the ja historical
`particle` alias):
- **1:1** (rename or verbatim, deterministic): the large majority.
- **merge** (multiple v5 types collapse into one v6 type, still deterministic per instance): zh
  `aspect_marker`, `ba_construction`, `bei_passive`, `resultative_complement`, `directional_complement`,
  `adverbial_order`; ja `tense_aspect_ja`.
- **split** (v6's definition is strictly narrower or ambiguous — some historically-tagged instances no
  longer qualify as errors and need human relabelling): ja `particle_wa_ga`, ja
  `particle` (the pre-v5 historical alias — must be triaged by hand into `wa_ga`/`case_particle`/
  `particle_other`), en `pronoun_reference`. zh `de_particles` → `de_particle` is **no longer** a split
  (user decision 2026-09-27): any 的/地/得 misuse is an error under v6, so the mapping is 1:1.
- **dropped**: ja `script_choice` (jev explicitly rules it out as an error).

**Impact, counted over the gold + silver DT label sets** (`tests/fixtures/dt_gold/*.json` +
`data/eval/jev_dt_2026-09-26/silver/{zh_final3,ja_final3,en_final3}.json`, 174 labelled errors total —
counting script checked in at
[[../../data/eval/taxonomy_merge_2026-09-27/impact.py|impact.py]], output at
[[../../data/eval/taxonomy_merge_2026-09-27/impact.json|impact.json]] with the full per-subtype
breakdown):

| | zh | ja | en | **total** |
|---|---|---|---|---|
| Labelled errors | 59 | 56 | 59 | **174** |
| Maps unambiguously (1:1 / merge) | 59 | 53 | 56 | **168 (96.6%)** |
| Needs relabelling (split / dropped) | 0 (was 4, `de_particles`) | 3 (`particle_wa_ga`) | 3 (`pronoun_reference`) | **6 (3.4%)** |
| Unknown subtype (not seen in v5) | 0 | 0 | 0 | **0** |

**Recomputed 2026-09-27 (user decision):** zh `de_particles` moved from split to 1:1, so its 4 items
(`zh_seed_11`, `zh_multi_02`, `zh_silver_20`, `zh_silver_29`) no longer need relabelling — they all map
deterministically to `de_particle`/minor. Needs-relabelling total drops from 10 (5.7%) to 6 (3.4%);
unambiguous total rises from 164 (94.3%) to 168 (96.6%).

No gold/silver label used ja's `script_choice` or the historical `particle` alias, so the drop and the
alias-split cost nothing in the current label sets — but future ja labelling passes must not reintroduce
`script_choice`.

## Consequences
- **Gold/silver relabelling — ANSWERED (user decision 2026-09-27):** triaged by the same author/reviewer
  pairing jev taxonomy.md §0.8 uses, one exchange per item, and the 2 escalated zh items are now resolved
  by user ruling. Of the 10 items: `zh_seed_11` and `zh_multi_02` (both a 的-for-得 substitution) **stay
  `de_particle`/minor** — the user ruled that ANY 的/地/得 misuse is an error, never acceptable variation,
  settling the escalation in the reviewer's favour; `zh_silver_20` (的-for-地) **changes from `variant_ok`
  to `de_particle`/minor** under the same ruling — the zh `de_particle` "not an error" carve-out for
  的-for-地 is revoked; `zh_silver_29` → keep `de_particle`/minor, and the v6 definition is widened to
  "wrong 的/得/地 choice" to literally cover attributive 地-for-的 (bands are identical either way); the
  3 ja `particle_wa_ga` items keep `wa_ga`/major (all are genuine relative-clause-subject errors, rule 2);
  the 3 en `pronoun_reference` items retype to `word_choice`, and severity was itself a mid-exchange
  concession (reviewer conceded minor→major: a referent shift is a real propositional-content change, MQM
  major) — this also surfaces a gap the v5→v6 CSV had already flagged: v6 has no pronoun-antecedent-
  agreement type, so these three would move again if one is added. **0 items remain escalated** (both
  were resolved by the user decision above). Full record:
  [[../../data/eval/taxonomy_merge_2026-09-27/relabel/reconciled.json|relabel/reconciled.json]] (pre-dates
  the user ruling on the 2 escalated items — see this ADR for the final call). This was a small, bounded
  exercise — not a full re-label of the 174-item gold/silver corpus.
- **Profile history migration.** `dt_error_profile_entry` rows keyed on a v5 subtype must be re-keyed
  under v6 via the mapping table (1:1/merge rows rewrite deterministically; split rows need the same
  per-instance review as the gold set, or a one-time best-effort bulk remap with a flag for later
  correction).
- **Taxonomy version stamping.** `dt_taxonomy_version` gets a new active row (v6) exactly as v4→v5 did;
  `dt_error_instance`/profile rows must carry (or be joinable to) the taxonomy version they were graded
  under, since a v5 subtype slug is not always resolvable under v6 without the mapping table (this is
  the same historical-alias pattern v5 already uses for pre-v5 `particle`).
- **Prompt / explainer changes.** `grader_cascade.py`'s per-L2 prompt subtype lists, `subtype_glosses`,
  and `templates` (rendered explanations) need new entries for every added/renamed type in v6, and the
  9 new types (`separable_verb`, `coverb`, `connective`, `transitivity_voice`, `modification`,
  `clause_linkage`, `kanji_choice`, `complementation`, `lexical_form`) plus `semantic_anomaly`/
  `contradiction` per language need first-draft ZH/JA/EN glosses and templates authored (AI-drafted
  first pass, native review flagged — same process as v5's 15 new subtypes).
- **Scoring dimension map.** `scoring.py` reads `subtype_meta[subtype].dimension` verbatim, so v6's
  `subtype_meta` must ship with correct `dimension`/`default_severity` for every type before the cascade
  can grade under it — this proposal's `merged_taxonomy.json` is that data, but it still needs the same
  native-review pass v5's AI-drafted entries got.
- **First live use of `critical` severity.** After the review-driven split, `contradiction` itself
  defaults to `major` (see Open Questions), and it is `meaning_inversion`'s `default_severity: critical`
  that will be the first non-`particle`-alias row to exercise the MQM `critical` tier in
  `subtype_meta`/scoring. **ANSWERED:** `critical` is already wired in `dt_rubric_v6_seed.sql` —
  `severity_weights: {minor: 1, major: 5, critical: 25}` and `understandability_weights: {minor: 0,
  major: 2, critical: 25}` — so `compute_dimension_bands` (`services/dual_translation/scoring.py`) will
  price a `meaning_inversion` error correctly the moment v6's `subtype_meta` is seeded; no rubric-config
  change is required.
- **Independent review of the 15 new-type judgements.** Two independent Opus reviewers (one per
  non-English language plus one cross-checking English, per jev taxonomy.md §0.8's blind-then-compare
  protocol) checked every new type's `dimension`/`default_severity`. Four disagreements were conceded by
  the author after one exchange (ja `kanji_choice` and en `lexical_form`: `fidelity`→`accuracy`, both on
  a "right word, wrong form" consistency argument with `orthography`/`plural_number`; zh `connective`:
  `minor`→`major`, for cross-language consistency with ja `clause_linkage`; `contradiction`:
  `critical`→`major` plus the `meaning_inversion` split, above). The other 11 reviewed judgements
  (zh `separable_verb`/`coverb`; ja `transitivity_voice`/`modification`/`clause_linkage`; en
  `complementation`; `semantic_anomaly` in all three languages) were agreed with no changes. Full record:
  [[../../data/eval/taxonomy_merge_2026-09-27/review/|review/]] (`{zh,ja,en}_review.json` +
  `author_response.json`). **This was an AI (Opus) review, not a native-speaker one** — a human
  native-speaker check is still advisable for the zh/ja judgements specifically, per the existing
  native-review flag on all AI-drafted taxonomy entries (see Open Questions).
- **Legacy type porting.** Per user decision (2026-09-27), en `phrasal_verb` and ja `particle_other` —
  previously "retained-legacy, no jev match" — are being ported into jev's own grammar taxonomy via
  `data/eval/jev_grammar_2026-09-26/taxonomy_addendum_2026-09-27.md` (author/reviewer pass in progress).
  `phrasal_verb` takes jev bucket B1; `particle_other` takes a new jev bucket **B9** (jev's bucket
  structure previously topped out at B8). **ANSWERED (user decision 2026-09-27, second round):** en
  `plural_number` and zh/ja `topic_comment` are also being ported (author/reviewer pass in progress,
  addendum to be extended); until that lands, `merged_taxonomy.json` sets their `jev_bucket` to the
  string `"pending"` rather than `null`, to flag them as queued-for-porting rather than permanently
  legacy-only.
- **meaning_inversion precedence — ANSWERED (user decision 2026-09-27):** label **by effect**, not by
  surface form. Any error whose effect is to flip polarity/negation, direction, quantity/degree, or
  agent/recipient relative to the reference is tagged `meaning_inversion` (fidelity/critical), regardless
  of whether the edit that caused it reads as a preposition swap, a word-choice swap, or a dropped
  negator. Boundary rule, now finalized in each language's `meaning_inversion` definition in
  `merged_taxonomy.json`: a dropped 没/不/not (or equivalent) that flips the sentence's polarity is
  `meaning_inversion`, not `omission`; an omission that merely loses content without reversing polarity/
  direction/quantity/agent stays `omission`. This resolves the open boundary question against
  `en_seed_15` ("with" → "without"), which is `meaning_inversion`/critical, not `preposition`/critical.
  Gold/silver items currently tagged as a critical inversion under their old surface-form type (e.g.
  `en_seed_15`) get v6 overlay labels from a separate relabel job,
  `data/eval/taxonomy_merge_2026-09-27/v6_label_overlay.json` (not created by this ADR — referenced only).
- **word_choice / wrong_sense — ANSWERED (user decisions 2026-09-27; variant made 3-way in the second
  ruling, "Decision A"):** merge at scoring level (one `word_choice` id, one `subtype_meta` row, same
  dimension/severity per language — unchanged), split at explanation level. Every `word_choice` error
  carries an `explanation_variant` (field on the `word_choice` entry in `merged_taxonomy.json`, zh/ja/en):
  - `wrong_word` — a word that doesn't fit the idea (vocabulary gap).
  - `wrong_sense` (**narrow**) — the SAME word/lemma used in a different one of its own dictionary senses
    than the context needs (e.g. 意思 as "intention" where "meaning" is needed). A different lexeme never
    qualifies, however close.
  - `shared_translation` — a DIFFERENT word that shares a translation/gloss in the learner's L1 with the
    correct word (知道/认识 both "know"; 見る/会う both "see").
  Precedence: same lemma → `wrong_sense`; shared L1 gloss → `shared_translation`; else `wrong_word`.
  `shared_translation` is largely **deterministic**: if the learner's word and the correct word share an
  L1 gloss in the sense dictionary, it is `shared_translation`. Caveat: en words currently have no zh/ja
  glosses, so for en L2 this lookup is not yet available and the variant stays a grader judgement.
  Consequences: (1) `dt_error_instance` needs a new column or JSON detail field for the variant; (2) the
  grader needs a same-lemma check plus the gloss lookup (one jev yes/no question only for the residual
  `wrong_sense` vs `wrong_word` call); (3) `explainer.py` needs three rendered-explanation templates per
  language; (4) the per-user profile can aggregate `word_choice` by variant, `wrong_sense` instances can
  link to the sense dictionary, and `shared_translation` instances can drive contrastive pair drills.
- **v6 label overlay — FINAL (2026-09-27), status of this ADR still proposed.**
  `data/eval/taxonomy_merge_2026-09-27/v6_label_overlay.json` (built by `build_overlay.py`) labels all 174
  gold+silver errors; every entry is `"final": true`, and the 61 entries that went through the blind
  author/reviewer exchange (`overlay_reconciled.json`) carry a `resolution`: **46 agreed, 4
  reviewer_conceded** (`zh_silver_09` → `word_choice`/major, not an inversion; `ja_silver_20` → major;
  `ja_silver_24` → `word_choice`, not `collocation`; `ja_silver_27` → `cohesion_connective`/major),
  **0 author_conceded, 11 user_decision** (the 9 escalations plus `ja_multi_02` and `ja_multi_04#1`,
  re-classified from agreed `wrong_sense` under Decision A). Item escalations (Decision B, reviewer's
  call on all four): `zh_silver_18` → `omission`/**major** (content lost, nothing reversed; critical is
  for inversion-grade effects); `zh_silver_37` → `ba_bei`/major (把心情变好: 把 with a non-disposal verb,
  a construction error, not word choice); `ja_silver_19` → `addition`/**minor** (the added ない sits
  inside a "check whether" clause, 掴めないか確認 — not an inversion); `en_silver_17` → `word_choice`/
  **minor** (say/tell, meaning recoverable). Variant escalations all land on `shared_translation`
  (the author was right that a shared gloss drives them, the reviewer was right that a different lexeme
  is not `wrong_sense`): `zh_seed_06` 轻松/放松, `zh_multi_02#1` 普通/简单, `ja_seed_08` 持つ/掴む,
  `en_multi_03#0` key/important, `en_silver_17` say/tell, `en_silver_28` engine/motor. Final counts:
  **`meaning_inversion` 21** (was 22; `ja_silver_19` left); **`word_choice` 28** (`zh_silver_37` left)
  = **20 `wrong_word` / 0 `wrong_sense` / 8 `shared_translation`**, 3 flagged `variant_uncertain`
  (`zh_multi_02#1`, `ja_multi_04#1`, `en_multi_03#0` — see Open Questions). **Band changes vs
  `expected_bands`: 12 items** (was 8; the 4 new ones are exactly the Decision B items) —
  `overlay_band_changes.json`, recomputed with `scripts/dt_gold_seed_helper.derive_bands(offline=True)`
  under v6 dimensions via the same `V5_DIMENSION` swap shim. Gold fixtures and silver files are
  untouched; the overlay is the v6 label source until a v6 gold set is cut.

## Alternatives Considered
1. **Keep v5 as-is, ignore jev.** Simplest, zero migration cost, but leaves DT scoring and jev's
   sentence-level judge disagreeing about what counts as an error (的-for-地, main-clause は/が, etc.),
   which will surface as confusing/contradictory feedback if jev-derived tooling or judges ever touch
   DT-graded text. Rejected — the two systems need one shared ground truth.
2. **Adopt jev's grammar taxonomy wholesale, drop v5's translation-level types.** Loses `omission`,
   `addition`, `register`, `cohesion_connective` and other types that are core to what DT actually
   grades (jev's scope is single-sentence corruption detection for a classifier, not whole-passage
   translation quality) and loses the `target_*`-adjacent function of `word_choice` as a general lexical
   bucket. Rejected — jev's taxonomy was never designed to be a complete translation-error schema.
3. **Two-level type + subtype (keep v5's coarse type as a parent, jev's fine type as a child).** Would
   avoid renaming/merging visible subtype ids and ease profile-history migration (old subtype stays
   valid, mapped by parent), but doubles every consumer's lookup logic
   (`scoring.py`, `cards.py`, `grader_cascade.py`, `explainer.py`, profile aggregation) for a
   distinction only useful during the transition. Rejected in favour of a flat v6 list plus the mapping
   CSVs as the one-time migration aid; the CSVs already give reversibility without a permanent
   two-level schema.

## Open Questions
- **OPEN (narrowed by AI review, native check still needed):** independent Opus reviewers checked the
  `dimension`/`default_severity` of every new type against jev taxonomy.md §0.8's blind-then-compare
  protocol (see the new Consequences bullet above and
  [[../../data/eval/taxonomy_merge_2026-09-27/review/|review/]]); 4 disagreements were conceded and
  applied (ja `kanji_choice`, en `lexical_form`, zh `connective`, `contradiction`/`meaning_inversion`
  split), 11 judgements were agreed as drafted. **This was an AI review, not a native-speaker one** — a
  human native-speaker pass is still advisable for the zh/ja judgements specifically, following the same
  AI-drafted/native-review-pending pattern v5 already flags (see ADR-019 / the "NATIVE-REVIEW FLAG" note
  in `dt_taxonomy_v5_seed.sql`).
- **ANSWERED:** Is `critical` actually wired end-to-end in the live rubric config? Yes —
  `dt_rubric_v6_seed.sql` defines `severity_weights: {minor: 1, major: 5, critical: 25}` and
  `understandability_weights: {minor: 0, major: 2, critical: 25}`. `meaning_inversion`'s
  `default_severity: critical` will be priced correctly with no rubric-config change needed.
- **ANSWERED (user decision 2026-09-27):** en `phrasal_verb` and ja `particle_other` are being ported
  into jev's own taxonomy (`taxonomy_addendum_2026-09-27.md`, author/reviewer pass in progress) rather
  than staying DT-only legacy — see the new Consequences bullet above. **ANSWERED (second round, same
  date):** en `plural_number` and zh/ja `topic_comment` are also being ported to jev — the user extended
  the porting decision to these two types as well. `jev_bucket` is set to `"pending"` for all three
  (`plural_number`, zh `topic_comment`, ja `topic_comment`) in `merged_taxonomy.json` until the addendum
  author/reviewer pass assigns real buckets.
- **ANSWERED (user decision 2026-09-27):** the (now 10, corrected from an earlier "8") needs-relabel
  gold/silver items were triaged by the same author/reviewer pairing jev's own corruption-authoring
  process uses (§0.8) — see the updated Gold/silver relabelling bullet above and
  [[../../data/eval/taxonomy_merge_2026-09-27/relabel/reconciled.json|relabel/reconciled.json]]. This
  produced two new open questions below.
- **ANSWERED (user decision 2026-09-27):** `zh_seed_11` and `zh_multi_02` (both a
  的-for-得 substitution, e.g. 画得很细致 → 画的很细致) are errors, not acceptable variants: the user ruled
  that ANY 的/地/得 misuse is an error, never acceptable variation. Both items stay `de_particle`/minor
  (the reviewer's original position). This also settles `tests/fixtures/dt_gold/README.md`'s "clean
  items" provenance line, which claimed a "得/的 variant" was acceptable — that clause is now removed
  from the README (see `tests/fixtures/dt_gold/README.md` and the new addendum section
  "zh de_particle — user decision 2026-09-27" in `taxonomy_addendum_2026-09-27.md`). See
  `relabel/reconciled.json`'s `gold_readme_finding` for the pre-ruling analysis.
- **ANSWERED (user decision 2026-09-27):** the precedence when an error is both a plain grammar-form type
  and an inversion — e.g. `en_seed_15`, "with" mistranslated as "without", at once an
  `en.preposition`-shaped edit and a polarity inversion — is **label by effect**: any error whose effect
  is to flip polarity/negation, direction, quantity/degree, or agent/recipient relative to the reference
  is tagged `meaning_inversion` (fidelity/critical), regardless of surface form. `en_seed_15` is
  `meaning_inversion`/critical, not `preposition`/critical. The boundary rule is now finalized in each
  language's `meaning_inversion` definition in `merged_taxonomy.json`: a dropped negator that flips
  polarity is `meaning_inversion`, not `omission`; an omission that merely loses content is `omission`.
  Gold/silver critical-inversion relabelling (e.g. `en_seed_15`) is tracked separately in
  `data/eval/taxonomy_merge_2026-09-27/v6_label_overlay.json` (a separate relabel job, not created here).
- **ANSWERED (user decision 2026-09-27):** `word_choice` absorbing `wrong_sense` merges at the
  scoring/taxonomy level (one `word_choice` id, one `subtype_meta` row, one dimension/severity per
  language) but splits at the explanation level via a new `explanation_variant` field
  (`wrong_word` | `wrong_sense`) on the `word_choice` entry in `merged_taxonomy.json`. The grader records
  which kind it found (for jev: one extra yes/no bucket question — "is this a real word used in the wrong
  dictionary sense here?"), `dt_error_instance` gets a column/detail field for it, the per-user profile
  can aggregate by variant, and `wrong_sense` instances can link to the sense dictionary for drills.
  **Superseded in part by the next bullet** (the 2-way variant became 3-way).
- **ANSWERED (user decision 2026-09-27, Decision A): the `wrong_sense` definition.** The overlay review
  escalated 6 variant calls because author and reviewer read `wrong_sense` differently (author: a
  different word sharing an L1 gloss; reviewer: polysemy of the same lemma). Resolution: the variant is
  **three-way** — `wrong_word` | `wrong_sense` (**narrow**: the same lemma in a different one of its own
  senses) | `shared_translation` (a different word sharing an L1 gloss, detectable from the sense
  dictionary's L1 glosses; not yet for en L2, which has no zh/ja glosses). Scoring is unchanged.
  `explainer.py` needs three templates per language. All 6 escalations resolve to `shared_translation`
  (see the v6 label overlay bullet under Consequences).
- **OPEN:** no gold/silver `word_choice` error is narrow `wrong_sense` (0 of 28 — every pair in the set
  is two different lemmas), so the eval sets give that variant **no coverage**. A gold item with a
  genuine same-lemma sense error (e.g. 意思 intention/meaning) is needed before the variant's grader
  question can be measured.
- **OPEN:** 3 overlay variant calls are flagged `variant_uncertain` and should be re-checked by the
  deterministic L1-gloss lookup once it exists: `zh_multi_02#1` 普通/简单 ("plain" is not a core gloss
  of 普通 — may fall to `wrong_word`), `ja_multi_04#1` 仕事/役割 (JMdict shares no exact gloss — may fall
  to `wrong_word`), `en_multi_03#0` key/important (arguably an acceptable near-synonym; en has no zh/ja
  glosses to confirm).
- **RESOLVED (2026-09-28):** `en_silver_24`'s note described a meaning inversion (agent swap —
  "The Arduino writes instructions for you") but its `expected_errors` was empty, so it had no overlay
  entry and failed `derive_bands` under v5 (derived understandability 4 vs expected 2; it appeared in
  `overlay_band_changes.json` as a `v5_baseline_mismatch`). Root cause: the three silver raters agreed
  the error existed and was `critical` but split 3 ways on v5 subtype (draft=`pronoun_reference`,
  rater2=`word_choice`, rater3=`word_order`), so the merge found no subtype majority and demoted it to
  an `understandability_only_errors` entry in `en_merge_log.json` — a bucket that is recorded but never
  fed back into `expected_errors`/`expected_bands`. A fourth (blind) label of `word_choice`/`critical`
  agreed with rater2, forming a 2-of-4 majority; the item was rebuilt with
  `scripts/dt_gold_seed_helper.py` (`build_item`/`verify_item`/`derive_bands(offline=True)`) and
  replaced in `en_final3.json` (old version backed up as `en_final3.pre_fix.json`). New bands: accuracy
  4, fidelity 1, understandability 2, naturalness 4, range 4 — fidelity drops from the stale 4 because
  `word_choice` is a fidelity-dimension subtype at `critical` severity. `word_choice` →
  `meaning_inversion`/critical/`inversion_by_effect` was added to
  `data/eval/taxonomy_merge_2026-09-27/v6_label_overlay.json`, consistent with the other passage-14
  agent-swap siblings (`en_silver_20/21/22/23/25/27`).

## Related Pages
- [[../business-rules/translation-error-taxonomy]] — the taxonomy this ADR revises
- [[ADR-016-per-pair-error-taxonomy]] — per-directed-pair schema this taxonomy sits inside
- [[ADR-015-eager-error-explanations]] — explanation-template contract affected by new/renamed types
- [[ADR-019-evidence-first-scoring]] — native-review precedent for AI-drafted taxonomy entries
- [[ADR-025-semantic-distractor-selection]], [[ADR-029-jev-tier-assignment]] — other jev-related decisions
