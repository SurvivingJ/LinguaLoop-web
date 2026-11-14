---
title: "DT Feedback — Option 3: Pattern Coach"
type: feature
status: planned
last_updated: 2026-11-14
open_questions:
  - "OPEN: per-language recall and type-accuracy figures come from 30 seeded gold items per language (jev-dt-tuning-2026-09-27). Every threshold below that depends on them is config, to be re-fitted on real submissions."
  - "OPEN: who tags reference sentences with the patterns they give a chance to use (deterministic rules vs one-off cheap LLM pass) — see §5."
  - "OPEN: does retrying one's own sentence transfer to new sentences, or only to that sentence? This is the main thing the A/B test in §7 must answer."
---

# DT Feedback — Option 3: Pattern Coach

One of three competing options for presenting and tracking Dual Translation (DT) feedback.
Mockup: `mockup.html` (same folder). Screens: `mobile.png`, `desktop.png` (montages of the 390px and 1280px renders).

## 0. The option in brief

Feedback on a single translation is deliberately short: each sentence is marked, the reference is shown, and a flagged sentence gets one error-type chip and a one-line templated rule. The product is what happens across translations. Every flag is logged by v6 type into a personal pattern profile. A pattern is shown only when there is enough evidence, is counted per chance to make the error, and is tracked through four states to "under control". The loop is closed by scheduling the learner's own previously wrong sentences for spaced re-translation, checked for free against the known correct form.

The option builds on what exists. `dt_error_instance`, `dt_error_profile_entry`, `dt_card` (`cloze`, `isolate_retranslate`), `dt_card_review`, FSRS-4 scheduling, the `/dual-translation/profile` page and the "N=3 in 30 days / 20 submissions" promotion rule are already specified or built ([[features/dual-translation-remediation.tech]], [[business-rules/translation-error-taxonomy]]). What this option changes is: a per-chance denominator, evidence thresholds that account for the cheap grader's noise, a "resolved" rule that does not rely on the absence of flags, a learner dispute path, and a per-item screen cut down to match.

### What the grader's limits force

| Grader fact ([[evaluations/jev-dt-tuning-2026-09-27]]) | Design consequence |
|---|---|
| Error present: precision ≈ 1.0 (en .95) | A flag can be shown plainly, with a one-tap "Not an error?" |
| Recall ≈ 50% zh/ja, 80% en; misses mostly minor | "No flag" is never shown as "correct". Only an exact match is a certain all-clear. "Resolved" needs evidence that does not depend on recall (§2.5) |
| Type top-1 right 69% ja, 75% zh, 95% en; top-3 92–100% | No pattern from fewer than 3 flags; type confidence gates logging; family-level fallback (§2.3) |
| Severity is the least reliable field (54–75%) | Severity is not shown as a label and does not rank patterns. The taxonomy's `default_severity` per type is used instead. One exception: `meaning_inversion`, which the grader caught 8 of 8 times |
| One type per sentence | The chip is attached to the sentence, not a span. Other differences in the sentence are marked neutrally |
| No free-text explanations | One-line rule from the existing per-subtype × per-L1 templates in `dt_taxonomy_version` ($0) |
| Naturalness and range not gradeable | Not shown. The five-band grid is removed from this screen when the cheap grader is the source |

---

## 1. In-the-moment feedback screen

Mockup view "Feedback". All five examples are real gold items (`zh_multi_01`, `ja_multi_01`, `en_multi_04`, `en_multi_02`, a clean zh item). The L1 reference text in the mockup is illustrative; the gold set stores only L2.

### 1.1 Layout, top to bottom

1. **Summary line.** "2 of 4 sentences match the reference · 2 points to notice", with one tally block per sentence (solid = match, hatched = point to notice). No band, no score, no percentage.
2. **One thing to take from this** (only when needed, §1.3).
3. **Sentence list.** One row per aligned sentence pair, in one of five states (§1.2).
4. **What happens next.** One or two lines of feed-forward: which sentence comes back and when, and whether a pattern changed state.
5. Actions: Next passage · See my patterns.

### 1.2 Sentence states

Each state has its own icon, text label, border style and colour, so colour is never the only signal.

| State | When | Shown | Logged to profile |
|---|---|---|---|
| **✓ Matches** | Sentence equals the reference after Tier 0 normalisation | Sentence in muted ink, single line | Clean chance, full weight (deterministic) |
| **● Type chip** (e.g. "Measure word · 量词") + "Likely" | `p_error ≥ τ_flag` and `p_type ≥ τ_type` | You / Reference with the differing parts marked, one-line rule, pattern note ("In your focus · 7 of your last 20 chances"), "Not an error?" | Error for that type |
| **● Family chip** ("Grammar") + "Possibly: particle" | `p_error ≥ τ_flag`, `p_type < τ_type` | Same, without a type rule | Error at family level only (§2.3) |
| **◌ Worth a second look** + "Checker unsure" | `τ_low ≤ p_error < τ_flag` | You / Reference, hedged sentence, "It is an error — count it" | Not logged unless the learner confirms |
| **≠ Different from the reference** | No flag, but the sentence is not an exact match | You / Reference with neutral marking, "your wording may be fine", "Save this to retry later" | Clean chance at reduced weight (§2.2); a learner save creates a self-reported error |
| **▲ Meaning may be reversed** | Type `meaning_inversion` (or the grader's narrow negation / quantity / agent checks fire) | As a flag, in the danger style, still worded as "seems to say the opposite" | Error, default severity critical |

Marked spans come from the free Tier 0 diff, not from the grader. A marked span means "this is where you differ from the reference", which is always true. The claim "this is an error of type X" is made once, at sentence level, where the grader actually made it.

### 1.3 The named states from the brief

- **Clean item.** All rows "Matches": "All 4 sentences match the reference. Word for word. Nothing to check." If a matched sentence was a chance to use a focus pattern, the row says so ("Measure word — one you have been working on"). This is the only positive feedback the data can fully support, so it is used.
- **Many errors.** At most one point is promoted to "One thing to take from this". Priority: a meaning reversal first, then a point in an in-focus pattern, then the type with the highest `default_severity`. The other flags stay in the sentence list in normal weight; nothing is hidden, but the learner is told which one to spend attention on. At six or more flagged sentences (rare with 2–4 sentence passages) rows after the third collapse behind "Show n more".
- **Low-confidence grader.** Per sentence: the "Worth a second look" state above. Per item: if grading failed or fell back, the existing provisional notice is kept ("Grading didn't finish"), sentences are shown with diff marking only, and nothing is logged.
- **Learner disputes a flag.** "Not an error?" opens three choices: "My version is also correct", "It's an error, but a different kind", "Not sure — check it again". On any choice the flag is struck through and leaves the learner's patterns immediately, with Undo. The dispute is queued for the live (expensive) grader, within a daily cap. If the stronger check agrees with the learner, nothing more is said. If it disagrees, the learner gets one hedged note on their next visit ("A second check still thinks 把 is needed here") with "Count it" / "Leave it out". The learner's choice is final for their own profile. All disputes feed grader QA (§6).

### 1.4 What is removed from the current result screen

The overall band, the five dimension tiles, the "because" lines, the per-error severity chips and the positive-evidence highlights are not shown when the cheap grader is the source. Accuracy, fidelity and understandability bands are still computed and stored (`dt_grade.scores`) for analytics and for the other options.

---

## 2. Tracking model

### 2.1 Units

- **Observation** = one graded sentence pair. This is the grader's own unit.
- **Chance** (opportunity) = an observation whose *reference* sentence uses the pattern. A reference sentence containing 一件衣服 is one chance for `measure_word`. Chances are a property of the corpus, tagged once per reference sentence (§5), not per learner.
- For translation-level types with no obligatory context (`omission`, `addition`, `word_choice`, `register`, `word_order`, `meaning_inversion`), every observation is a chance.
- **Pattern** = (user, L1→L2 pair, v6 subtype), the existing cluster key. A **family** is the taxonomy `class` plus `jev_bucket` grouping (e.g. ja particles: `wa_ga`, `case_particle`, `particle_other`).

Counting per chance is the SLA "obligatory context" method (Brown 1973; Pica 1983 target-like use; from memory, not re-verified). Raw counts would rank a pattern high just because its structure is common in the passages served.

### 2.2 Evidence weights

| Observation in a chance for type T | Counts as | Weight |
|---|---|---|
| Flagged, type T, `p_type ≥ τ_type` | error | 1 |
| Flagged, type T, `p_type < τ_type` | error for T's family only | 1 at family level |
| Flagged with another type | not a clean chance for T (the sentence was wrong somewhere; one type per sentence) | excluded |
| Exact match | clean | 1 |
| Not flagged, not exact | clean | `w_clean[lang]` = estimated recall (zh .5, ja .5, en .8) |
| "Worth a second look", unconfirmed | nothing | 0 |
| Disputed by learner | nothing | 0 |
| Learner-saved difference | error, `source = self_reported` | 1 |
| Retry (probe) result | kept separately; never mixed into the rate | — |

Defaults: `τ_flag` is the frozen per-language detection cutoff; `τ_low = τ_flag − 0.25`; `τ_type = 0.60`. All are config.

### 2.3 Aggregation rules

**Window and recency.** Rates use the last 20 chances for the pattern, with the 20 before as the comparison window. Recency is measured in chances, not calendar time. A learner who takes three weeks off has produced no evidence of improvement, and forgetting is more likely than gain, so a calendar decay would wrongly drift patterns toward "resolved".

**Rate and interval.** For k errors in n effective chances the profile stores the Jeffreys interval, Beta(k + ½, n − k + ½), 10th and 90th percentiles. (Standard recommendation for small-n binomial intervals: Brown, Cai & DasGupta 2001; from memory.) The interval drives states and the detail chart. It is never shown as a number in the list view.

**What the learner sees is a literal count**: "Flagged in 7 of your last 20 chances". A count is true as stated. A percentage or an "accuracy" figure would imply the unflagged chances were correct, which low recall does not support.

**Type noise.** If type labels were independent with top-1 accuracy *a*, the probability that at least 2 of 3 flags are truly this type is .77 (a = .69, ja), .84 (zh), .99 (en); at least 3 of 5 is .82, .90, 1.00. That is why 3 flags only earns "Maybe" and 5 are needed for focus. Label errors are not independent (confusable pairs exist), so:
- when a type has fewer than 5 confident flags but its family has 5 or more, the profile shows the family ("Particles") rather than a type;
- the detail view lists the learner's own sentences, so a mislabelled pattern is visible to the learner, who can move a sentence out ("Not this pattern?").

**Slips.** The existing `is_mistake` gate stays: self-corrected and one-off slips are logged, not drilled.

### 2.4 Pattern states

| State (DB) | Learner label | Entry rule | Shown as | Scheduling |
|---|---|---|---|---|
| `watching` | — | any evidence below the next row | not shown | each flagged sentence still gets one retry card |
| `emerging` | "Maybe" | ≥ 3 errors on ≥ 2 distinct days within the last 20 chances (the existing N = 3 rule, plus the day condition) | quiet list, "Still gathering evidence" | retries of own sentences only |
| `active` | "Active" | ≥ 5 errors and ≥ 10 chances, and the 10th-percentile rate ≥ 15% | focus card, if a focus slot is free | retries + cloze cards + passage routing (§2.6) |
| `improving` | "Improving" | was `active`; P(rate in last 20 < rate in previous 20) ≥ .80 from the two Beta posteriors; and ≥ 1 retry passed | focus card | unchanged |
| `resolved` | "Under control" | §2.5 | "Under control" list | check-in retry at 30 and 90 days |
| `paused` | "Paused" | learner action | collapsed | none |

Other rules:
- **At most three patterns in focus.** Further `active` patterns wait in a collapsed "Later" list, ordered by rate × `default_severity` weight × `treatable`. The learner can swap.
- **Relapse.** From `resolved`, a failed check-in or 2 errors in 10 chances returns the pattern to `active`. The copy treats this as expected ("it simply comes back into focus").
- **No downward path to hidden.** A pattern that stops producing errors without passing retries stays `active` or `improving`; it does not silently disappear.
- The existing `queued` / `drilling` values map onto `emerging` / `active`; a migration rewrites them.

### 2.5 "Under control" does not depend on the absence of flags

With 50% recall, a run of unflagged sentences is weak evidence. Two conditions, both required:

1. **Retries (recall-independent).** 3 consecutive passed retries for the pattern, on ≥ 3 distinct days, on ≥ 2 distinct source sentences, the last after a gap of ≥ 14 days. A retry is checked deterministically against the stored correct form (§2.6), so grader recall does not enter.
2. **New sentences (recall-adjusted).** A run of clean chances in fresh passages long enough that the upper 80% bound on the error rate, divided by the language's recall, is ≤ 10%. With zero errors that bound is about 1.64 / (2n + 1), which gives **n = 16 for zh/ja and n = 10 for en**. Exact matches count 1; unflagged non-exact sentences count `w_clean`, so a learner who paraphrases needs more of them.

Condition 1 guards against low recall. Condition 2 guards against memorising specific sentences. The learner sees both as two progress bars with the reason for the number ("Why 16? In Chinese the checker misses about half of small slips").

### 2.6 The re-practice loop

**Retry card** (existing `dt_card.card_type = 'isolate_retranslate'`).
- Prompt: the L1 sentence only. The pattern is **not** named before the answer; naming it turns retrieval into cued recognition. A "Give me a hint" button names the area and costs one FSRS grade.
- Check: Tier 0 normalise, then test whether the stored reference-side diff regions (`focus_ref`, e.g. `一只`) are present at the aligned position. Pass / fail is deterministic and free. The rest of the sentence is shown as a diff and explicitly not judged. If alignment fails (the learner rephrased the clause), one cheap-grader call on the sentence decides, or the card is marked `not_counted`.
- FSRS-4 grade: pass without hint = good, pass with hint = hard, fail = again. Reuses `services/vocabulary/fsrs.py`.
- Invariant kept from the current build: the card payload never contains `learner_form` as a target.

**Schedule.** First retry no sooner than the next day (never in the same session as the feedback), then FSRS intervals, typically about 1 → 4 → 10 → 30 days. Cap: 5 retry cards per day, at most 2 per pattern per session, types interleaved. A failed retry returns the next day.

**Other routes, for `active` patterns only.**
- Cloze cards for types marked `cloze_suitable` in the taxonomy (existing).
- Passage routing: `GET /api/dual-translation/next` prefers, among the learner's completed tests, passages with at least one chance for an in-focus pattern. This supplies the fresh chances that condition 2 needs and is the transfer test.
- Matching trainers where one exists: zh `measure_word` → [[features/measure-word-trainer]]. `word_choice` errors whose `corrected_form` resolves to a known sense can be offered to the vocabulary ladder ([[features/vocabulary-knowledge]]); this mapping is unverified and is a follow-up, not part of the first build.

**Where it surfaces.**
1. DT result screen — chips, pattern notes, "What happens next".
2. Daily session and DT queue — due retry and cloze cards interleaved through the existing `GET /next` interleaving and `window.DTErrorCard`.
3. Practice Engine sessions — same cards (existing design).
4. `/dual-translation/profile` — replaces the current list with the profile in the mockup.
5. Pattern detail — new, at `/dual-translation/profile/<subtype>`.
6. A state change (enters focus, improving, under control) is announced once, in "What happens next" on the result screen where it happened.

### 2.7 Profile view

Mockup view "My patterns". Order is by what the learner can do, not by size of problem:

1. **Retry call to action** — "4 of your own sentences are ready to retry · about 3 minutes".
2. **In focus** (≤ 3) — name in English and L2, state, literal count, a dot strip of the last 20 chances, a trend phrase, retries due.
3. **Still gathering evidence** — name and count only, "nothing is scheduled".
4. **Under control** — with next check-in date.
5. **Rarely flagged** — types with ≥ 20 chances and ≤ 1 flag, captioned "a good sign, not a guarantee".
6. **How this page decides what to show** — the thresholds, in plain words.

Empty state (fewer than 3 flags of any one type): "No patterns yet. They appear after the same kind of point comes up three times."

Pattern detail: the rule, the count and dot strip, a dot-and-range chart per block of 10 chances with a one-phrase verdict, the learner's own sentences with retry history, a habit line derived from the diffs ("In 5 of your 7 recent flags you wrote 个"), the two progress bars toward "under control", and actions (retry, trainer, pause).

### 2.8 Schema (additions; conventions as in `dual_translation_groundwork.sql`)

`bigint` identity PKs, `integer` language FKs, `real` for confidences, `timestamptz DEFAULT now()`, enums as CHECK constraints, prefix `dt_`.

**New: `dt_passage_sentence`** — reference sentences and the chances they offer (corpus-side, written once).

| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `passage_id` | bigint NOT NULL | FK → dt_passage ON DELETE CASCADE |
| `sentence_idx` | smallint NOT NULL | UNIQUE (passage_id, sentence_idx) |
| `l2_text` | text NOT NULL | |
| `affords` | text[] NOT NULL DEFAULT '{}' | v6 subtypes with an obligatory context in this sentence |
| `affords_source` | text NOT NULL | CHECK: `rules` \| `llm` \| `human` |
| `taxonomy_version_id` | bigint NOT NULL | FK → dt_taxonomy_version |
| `created_at` | timestamptz | |

**New: `dt_sentence_result`** — one row per graded sentence pair; the observation.

| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `submission_id` | bigint NOT NULL | FK → dt_submission ON DELETE CASCADE |
| `passage_sentence_id` | bigint NOT NULL | FK → dt_passage_sentence |
| `learner_text` | text NOT NULL | the aligned learner sentence |
| `match_kind` | text NOT NULL | CHECK: `exact` \| `graded` \| `ungraded` |
| `p_error` | real | NULL when `exact` or `ungraded` |
| `display_state` | text NOT NULL | CHECK: `match` \| `flag` \| `unsure` \| `diff_only` |
| `diff_regions` | jsonb | `[{ref:[s,e], repro:[s,e]}]` from Tier 0 |
| `grader_slug` | text | provenance |
| `created_at` | timestamptz | |

**Altered: `dt_error_instance`** — add:

| column | type | notes |
|---|---|---|
| `sentence_result_id` | bigint | FK → dt_sentence_result |
| `type_confidence` | real | `p_type` of the chosen subtype |
| `type_top3` | jsonb | `[{subtype, p}]` |
| `family` | text | taxonomy class / bucket key |
| `source_kind` | text NOT NULL DEFAULT 'grader' | CHECK: `grader` \| `self_reported` |
| `profile_status` | text NOT NULL DEFAULT 'counted' | CHECK: `counted` \| `family_only` \| `disputed` \| `overturned` \| `moved` |

`severity` stays as written by the grader but is no longer read by ranking. `explanation` is filled from the template.

**Altered: `dt_error_profile_entry`** — add: `chances_recent real`, `errors_recent real`, `chances_prev real`, `errors_prev real`, `rate_lo real`, `rate_hi real`, `p_improving real`, `probe_streak smallint`, `probe_last_gap_days smallint`, `clean_run real`, `in_focus boolean DEFAULT false`, `state_changed_at timestamptz`, `next_checkin date`. Widen the `remediation_status` CHECK to `watching | emerging | active | improving | resolved | paused`. `trend` jsonb holds the per-block series `[{from, to, errors, chances}]` for the chart. `count` and `severity_rank` are kept for compatibility.

**Altered: `dt_card`** — add `focus_ref jsonb` (reference-side strings and offsets the retry is checked against) and `sentence_result_id bigint`. **`dt_card_review`** — add `check_kind text CHECK (deterministic | grader | not_counted)`, `hint_used boolean`.

**New: `dt_error_dispute`**

| column | type | notes |
|---|---|---|
| `id` | bigint PK | |
| `error_instance_id` | bigint NOT NULL UNIQUE | FK → dt_error_instance |
| `user_id` | uuid NOT NULL | FK → users |
| `reason` | text NOT NULL | CHECK: `also_correct` \| `different_type` \| `unsure` |
| `status` | text NOT NULL DEFAULT 'open' | CHECK: `open` \| `upheld` \| `overturned` \| `unreviewed` |
| `adjudicator_slug` | text | live-grader slug, when run |
| `learner_final` | text | CHECK: `count` \| `exclude`; the learner's last word |
| `created_at`, `resolved_at` | timestamptz | |

RLS as for other `dt_*` tables: a learner reads and writes only their own rows; `dt_passage_sentence` is read-only to learners.

---

## 3. Pedagogy rationale

Citations marked **[verified]** were checked by web search in this session (title, authors, venue; findings from abstracts). **[from memory]** means the reference is standard and I am confident of it but did not re-check it. Anything shakier is marked **unverified**.

| Decision | Evidence | Honest caveat |
|---|---|---|
| Short per-item feedback, one promoted point, three patterns in focus | Bitchener & Knoch (2010), *The contribution of written corrective feedback to language development: a ten month investigation*, Applied Linguistics 31(2) **[verified]**: 52 ESL learners, feedback focused on two article functions, tracked over 10 months. Sheen (2007), TESOL Quarterly, focused feedback on articles **[from memory]** | The focused-feedback studies target one or two English features chosen by the researcher. A replication (Ekiert & di Gennaro, *Language Teaching*) only partly confirmed the result **[verified]**. Van Beuningen, De Jong & Kuiken (2012) found comprehensive feedback also works **[from memory]**. "Three" is a design choice, not an empirical optimum |
| Written correction is worth doing at all | Kang & Han (2015), *The efficacy of written corrective feedback in improving L2 written accuracy: a meta-analysis*, Modern Language Journal 99(1) **[verified]**: positive overall, moderated by proficiency, setting and genre | Truscott (1996), *The case against grammar correction in L2 writing classes*, Language Learning 46(2) **[verified]** argued it is useless or harmful, and the debate is not closed. Sources I found disagree on Kang & Han's pooled effect size, so I do not quote one |
| Feedback answers "where to next", and works at process and self-regulation level, not at the level of the self | Hattie & Timperley (2007), *The power of feedback*, Review of Educational Research 77(1) **[from memory]**: feed up / feed back / feed forward; task, process, self-regulation and self levels. The chip and rule are task/process level; the pattern note and "What happens next" are feed-forward; the profile is self-regulation level | A framework paper built on meta-analyses of mixed quality. Kluger & DeNisi (1996), Psychological Bulletin 119(2) **[from memory]** found about a third of feedback interventions lowered performance, mostly when attention moved to the self. That is the reason there is no score, rank or streak here |
| An error log the learner can read, judge and correct | Zimmerman (2002), *Becoming a self-regulated learner: an overview*, Theory Into Practice 41(2) **[from memory]**: self-monitoring and self-evaluation are core phases. The dispute, "save this", "not this pattern" and pause controls make the learner a participant in the record | Most evidence for self-monitoring is correlational or from classroom training, not from app dashboards |
| Dashboard leads with an action, not a chart | Jivet, Scheffel, Specht & Drachsler (2018), *License to evaluate: preparing learning analytics dashboards for educational practice*, LAK '18 **[verified]**; Jivet et al. (2017), *Awareness is not enough: pitfalls of learning analytics dashboards in the educational practice* **[verified title]**; Matcha, Uzir, Gašević & Pardo (2020), *A systematic review of empirical studies on learning analytics dashboards: a self-regulated learning perspective*, IEEE TLT 13(2) **[verified]**: dashboards are rarely grounded in learning theory and offer little on tactics; Bodily & Verbert (2017), IEEE TLT 10(4) **[verified]**: little experimental evidence of effect on behaviour or achievement | This literature shows that awareness-only dashboards lack evidence of benefit. It does not show that action-first dashboards work. That is a hypothesis this option must test (§7) |
| No peer comparison | Jivet et al. (2018) **[verified]**: comparison with peers is not received positively by all learners | — |
| Retry by producing, not re-reading the correction | Roediger & Karpicke (2006), *Test-enhanced learning*, Psychological Science 17(3) **[verified]**: repeated study wins at 5 minutes, testing wins at 2 days and 1 week | Prose recall by undergraduates, not L2 grammar. Transfer of the testing effect to rule-governed production is plausible, not demonstrated here |
| Retries spaced over days and weeks; none in the same session | Cepeda, Pashler, Vul, Wixted & Rohrer (2006), *Distributed practice in verbal recall tasks*, Psychological Bulletin 132(3) **[verified]**: 317 experiments; spacing helps, and the best gap grows with the retention interval | The evidence is verbal recall. For L2 grammar it is mixed: Suzuki & DeKeyser (2017) found a 1-day gap as good as a 7-day gap for accuracy, and better for speed **[verified]**. So the first interval is short (1 day) and the claim is "spaced beats massed", not "longer is better" |
| Interleave pattern types within a retry session | Nakata & Suzuki (2019), *Mixing grammar exercises facilitates long-term retention*, Modern Language Journal 103(3) **[verified]**: 115 learners, interleaving beat blocking on delayed tests | One study family, English grammar, Japanese learners |
| Criterion-based "under control" with check-ins | Bloom (1968), *Learning for mastery* **[from memory]**; Kulik, Kulik & Bangert-Drowns (1990), *Effectiveness of mastery learning programs: a meta-analysis*, Review of Educational Research 60(2) **[verified]**: 108 evaluations, positive effects | Mastery learning assumes a reliable mastery test. Ours is noisy, which is why the label is "under control", the criterion is two-part, and relapse is a normal path. I could not verify the commonly quoted ≈0.5 SD effect, so I do not rely on it |
| Only recurring errors become patterns | Corder (1967), *The significance of learners' errors*, IRAL 5 **[from memory]**: systematic errors vs one-off mistakes | The distinction is conceptual; our operational version (3 on 2 days) is a heuristic |
| Hierarchical error types, counted per obligatory context | Dagneaux, Denness & Granger (1998), *Computer-aided error analysis*, System 26 **[verified]**: hierarchical error tagging of a learner corpus. Per-context counting: Brown (1973), Pica (1983) **[from memory]** | Learner-corpus tagging is done by trained humans with adjudication. Ours is a cheap model, so we borrow the structure, not the reliability |
| Show the learner's own sentences | Noticing the gap between one's own output and the target: Schmidt (1990), *The role of consciousness in second language learning*, Applied Linguistics 11 **[from memory]**. Own sentences also let the learner audit the label | Noticing is argued to be necessary, not sufficient |
| Growth-oriented wording | Feedback aimed at the self is the least effective level (Hattie & Timperley). Wording describes the work ("flagged in 7 of 20"), never the learner | I make no claim from mindset interventions; large replications have found small effects (**unverified** in this session) |

---

## 4. Design rationale

**Chart choices.** Three forms only, each chosen for small, noisy counts.
- *Dot strip* (profile cards): one mark per chance, filled = flagged, hollow = not. It shows the raw observations, so there is no smoothing, no axis and nothing to misread as precision. Fill versus outline carries the meaning; colour is redundant.
- *Dot with range bar* (pattern detail): flagged share per block of 10 chances with the 80% interval. Y-axis labelled "none / half / all" rather than percentages. Blocks are equal numbers of chances, not equal time, so every dot rests on the same amount of evidence. Each dot is direct-labelled "4 of 10"; a table view is one tap away; hover gives the range.
- *Progress bars* (toward "under control"): the only place a target exists.
- Not used: line charts (imply continuity and a trend between sparse points), radar charts, a ranked bar chart of all error types (this is the "wall of weaknesses"), any composite score, percent-change figures ("down 40%" from 5 to 3 is noise).
- The verdict is a phrase chosen from the posterior: "Likely improving" (P ≥ .8), "No clear change yet", "Too few chances to see a trend". It is always next to the chart, so the learner does not have to read intervals.

**Visual hierarchy.** On the item screen the learner's own sentence is the largest text; the chip is small; the rule is secondary ink. On the profile the single primary-coloured block is the retry action; pattern cards are neutral surfaces with one small state pill. Warm apricot marks a flag, not red: red is reserved for a possible meaning reversal. "Under control" is blue-grey, not green with a trophy, because it is provisional.

**Colour is never the only signal (WCAG 2.2 SC 1.4.1).** Each sentence state has an icon (✓ ● ◌ ≠ ▲), a text label and a distinct border style (solid, dashed, dotted). Learner-side differences use a wavy underline plus tint; reference-side use a solid underline plus tint; a missing element shows a caret. Text and UI colours come from the app's existing tokens, whose comments record AA contrast (`--teal` 5.6:1, `--apricot-text`, `--warning-text`). Targets are at least 40px high; focus rings are visible; the retry result is an `aria-live` region; charts carry `role="img"` with a text equivalent.

**CJK typography.** Every L2 string carries `lang` (`zh-Hans`, `ja`), so the browser picks the right Han glyph forms and the app's per-language font stacks apply. L2 text is 1.2rem with line-height 1.8 and `line-break: strict` for Japanese. Emphasis inside CJK uses background and underline, never italics and never bold alone, which smears at this size. Uppercase letter-spaced labels are used only on Latin text. Marked spans are whole diff regions, so a mark never splits a character sequence the diff treated as one.

**Mobile.** Single column at 390px; You and Reference stack with labels above; the dot strip is at most 20 dots (282px) so it never scrolls; the chart is drawn at the container width so its labels stay at 11–12px rather than scaling down; the retry action goes full width. At ≥ 980px the profile uses two columns: things to do on the left, things that are fine on the right.

**Light and dark.** Tokens are copied from `:root` and `[data-theme='midnight']` in `static/css/styles.css`; dark values are chosen per token, not inverted. The mockup follows `prefers-color-scheme` and has a toggle.

**Tone.** Verbs describe the checker and the work: "flagged", "points to notice", "comes back tomorrow", "missing a retry is part of how this works". No "weakness", "mistake count", "failed", streaks or exclamation marks. Uncertainty is said in words ("Likely", "Checker unsure", "may be fine"), never as a percentage.

---

## 5. Data requirements and cost

**Needed from the grader, per sentence pair** (all of which the step-by-step jev grader already returns):

| Field | Used for |
|---|---|
| `p_error` (not only the yes/no) | flag / unsure / diff-only states |
| top-3 v6 types with probabilities | type gating, family fallback, "Also possible" line |
| narrow checks: negation, quantity, agent swap | the meaning-reversal state |
| sentence alignment (reference ↔ learner) | every row; chances |
| severity | stored, not displayed |

**Needed from elsewhere.**
- Tier 0 diff regions per sentence (exists; free).
- Explanation templates per subtype × L1 (exist in `dt_taxonomy_version`; free). Gap noted in the eval: zh `bei_passive` had no template in v4; v6 coverage must be checked.
- **Chance tags per reference sentence** (new). Many are rule-detectable (zh 数/这/那 + 量词, 把/被, 的/地/得, 了/过; ja は/が, case particles, です/ます; en articles, prepositions, 3rd-person verbs, plurals); the rest need one cheap LLM pass per reference sentence. This is corpus-side and paid once per sentence, not per submission.
- Per-language recall and type-accuracy estimates as config, re-fitted from dispute outcomes and a periodic audit sample.

**Cost per learner action.**

| Action | Cost |
|---|---|
| Grade a submission (cheap grader) | $0.00013–0.00023 per item (eval figure) |
| Explanation | $0 (template) |
| Retry check | $0 deterministic; one sentence-level grader call (well under $0.0001) when alignment fails |
| Profile aggregation | SQL only; update on write for the affected patterns plus the nightly synthesis job |
| Dispute adjudication by the live grader | about $0.025 (en) to $0.058 (zh/ja) each; cap 3 per learner per day; overflow stays `unreviewed` and the learner's choice stands |
| Chance tagging | one-off per reference sentence |

Not needed: free-text LLM explanations, naturalness or range scores, span-level error localisation from the grader, embeddings.

If chance tags are not ready at launch, fall back to "flags per 20 sentences" for every type and say "sentences", not "chances". Thresholds still apply; the per-chance rate is the upgrade.

---

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Mislabelled types pollute the profile** (top-1 69–75% in ja/zh) | 3 flags on 2 days before anything shows; 5 before focus; `τ_type` gate with family fallback; own sentences listed so the learner sees what the pattern is made of; "Not this pattern?" moves one sentence out; retrying one's own sentence is useful whatever the label was |
| **Low recall inflates "resolved"** | Two-part rule (§2.5): deterministic retries, plus a recall-scaled clean run; label is "under control"; check-ins at 30 and 90 days; relapse path |
| **Recall depends on severity**, so a learner whose errors become milder looks better than they are | Same two-part rule; the caption "counts are a floor"; learner self-report ("Save this to retry later") adds evidence the grader missed |
| **A correct sentence is told it is wrong** | Precision ≈ 1 on error presence; hedged wording for anything below `τ_flag`; diff marking claims only "differs"; one-tap dispute removes it at once |
| **Valid paraphrase punished** | Unflagged differences are neutral; paraphrase costs the learner only clean-run weight, never an error |
| **Retries train one sentence, not the rule** | Resolution requires ≥ 2 source sentences and fresh-passage chances; passage routing; A/B primary metric measures fresh chances (§7) |
| **Wall of weaknesses / demotivation** | Three in focus; nothing shown below threshold; "Rarely flagged" and "Under control" always present; literal counts, no scores; pause control |
| **Learners dispute everything** | It affects only their own profile; dispute rate per type is a grader-quality signal, and a type with a high upheld rate has `τ_type` raised or is demoted to family-only |
| **Sparse data** (rare structures such as 把) | "Too few chances to see a trend" is a first-class verdict; passage routing increases exposure |
| **Gold-set numbers do not hold on real learners** (30 seeded items per language) | All rates are config; run in shadow first (the eval's own recommendation); audit a weekly sample with the live grader and re-fit recall and type accuracy |
| **Retry load crowds out new work** | 5 per day, 2 per pattern per session; overflow waits |
| **Template rule does not fit the instance** | One-line rules are generic by design; the instance is carried by the You / Reference pair. Track "Not an error?" and "different kind" rates per template |
| **One type per sentence hides second errors** | "Also possible" line from top-3; neutral marking of every difference; stated on the screen in the several-errors case |

---

## 7. What to A/B test

**Primary test: does the loop reduce errors, beyond what display alone does?**
Three arms, randomised per learner, 8 weeks, all on the same short per-item screen:
- A — per-item feedback only (no profile, no retries).
- B — per-item feedback + profile (display only).
- C — per-item feedback + profile + scheduled retries and routing (this option).

**Primary metric:** flagged rate per chance on *fresh* passages for each learner's patterns that reached `active` in weeks 1–3, measured in weeks 6–8, relative to that learner's rate in weeks 1–3. Because recall is the same in every arm, the between-arm comparison is not biased by low recall, even though each absolute rate is. Analyse per language.

**Validation of the metric:** a random sample of week 6–8 submissions per arm graded by the live grader, to confirm the cheap-grader difference is real.

**Guardrails:** DT submissions per active week, 4-week retention, share of sessions where the retry prompt is dismissed, dispute rate, profile visits ending in a pause.

**Secondary tests.**
1. Pattern named before the retry versus after (cued versus free retrieval), measured on fresh-chance rate.
2. Focus cap of 3 versus no cap.
3. Literal counts and dot strips versus a percentage figure: retry starts per profile visit, and a one-question comprehension check ("has this got better?") against the true posterior.
4. First retry at 1 day versus 3 days (the L2 spacing evidence is mixed; test it rather than assume).

**Decision rule.** Ship C if C beats A on the primary metric with the live-grader sample agreeing in direction and no guardrail falls by more than a pre-set margin. If B does not beat A, that confirms the dashboard literature and the profile should stay only as the home of the retry loop.

---

## Related Pages
- [[features/dual-translation]] · [[features/dual-translation.tech]] · [[features/dual-translation-remediation.tech]]
- [[business-rules/translation-error-taxonomy]] · [[decisions/ADR-031-dt-taxonomy-v6-merge]]
- [[evaluations/jev-dt-tuning-2026-09-27]]
- [[features/flashcards.tech]] (FSRS-4) · [[features/measure-word-trainer]] · [[features/practice-engine]]
