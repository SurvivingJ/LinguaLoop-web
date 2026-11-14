---
title: "DT Feedback — Option 2: Guided Self-Repair (hint ladder, retry before reveal)"
type: feature
status: planned
last_updated: 2026-11-14
open_questions:
  - "OPEN: Where does the 'where' hint come from on real (non-seeded) submissions? The grader judges a sentence pair, not a span. This spec uses the existing deterministic diff and drops the rung when the diff is not a small local edit; how often that happens on real learner text is unmeasured."
  - "OPEN: Thresholds (confidence bands, repair cap of 3, attempt cap of 4, credit weights) are design defaults, not tuned values."
  - "OPEN: Hint templates need writing and native review for ~20 types x 3 L2s x 3 L1s."
---

# Option 2 — Guided Self-Repair

One of three competing options for presenting and tracking Dual Translation (DT) feedback.
Companion files: [`mockup.html`](./mockup.html) (working simulation), `mobile.png`, `desktop.png`.
Context: [[features/dual-translation]], [[decisions/ADR-031-dt-taxonomy-v6-merge]],
[[evaluations/jev-dt-tuning-2026-09-27]].

## 0. The option in one paragraph

After the learner submits, the app does not show the correction. It marks which sentences have a
problem and lets the learner fix them. Help arrives one step at a time and only when asked for:
**where** the problem is, **what kind** it is, a **clue** about the rule, and finally the **answer**.
Every revision is re-checked by the cheap grader in about 0.3 s. Every episode ends with the original
sentence on screen, whoever produced the fix. What gets tracked is how much help each error type
needed, which separates slips from gaps and shows a rule forming long before the error disappears.

The existing page already has a seam for this: `data-correction-style` in
`templates/dual_translation.html` (TASK-617) switches between `direct_metalinguistic` and
`flag_only`. This option is a third value, `guided_repair`, that runs **before** the existing result
screen (diff, bands, error cards), which stays as the final step.

## 1. In-the-moment flow

### 1.1 Sequence

1. **Submit.** The passage is split into aligned sentence pairs. Sentences identical to the reference
   are clean at no cost. Every other sentence gets one grader call.
2. **Triage** (server, instant). Each graded sentence falls into one of four groups:

   | Group | Rule (defaults) | What the learner gets |
   |---|---|---|
   | Clean | identical, or `p_error < 0.25` | "Nothing flagged" row |
   | Repair target | `p_error ≥ 0.75`, type is hintable (§1.4), within the cap | Hint ladder |
   | Shown directly | `p_error ≥ 0.75` but not hintable, or over the cap | Goes straight to the existing error card on the result screen |
   | Unsure | `0.25 ≤ p_error < 0.75` | "Possibly worth a look" card, no ladder |

   **Cap: at most 3 repair targets per passage.** Priority: meaning-changing errors first, then types
   the learner has not yet reached "on a second look" for (§2.3), then highest confidence.
3. **Repair pass.** One card per target, in passage order, first one focused. "Skip — show me
   everything" is always visible and ends the pass.
4. **Summary**, then the **existing result screen**. Bands are computed from the **first** submission;
   repairs never change the score.

### 1.2 The ladder

The learner's own sentence is pre-filled in an editable field. They can edit and press "Check again"
at any rung, or take the next hint.

| Rung | Button | What appears | Source | Cost |
|---|---|---|---|---|
| 0 | (none) | Sentence is marked "Take another look". No location, no type. | `p_error` | 0 |
| 1 Where | "Hint: where?" | Underline on the suspect part of the learner's sentence. For meaning errors, the matching part of the L1 prompt is highlighted too. | deterministic diff (§5.2) | 0 |
| 2 What kind | "Hint: what kind?" | v6 type name in the learner's L1, e.g. "Measure word (量词)" | grader top-1 type | 0 |
| 3 Clue | "Hint: give me a clue" | One or two sentences that state the rule or pose a question. Never contains the corrected form. | template per type x L1 | 0 |
| 4 Answer | "Show the answer" | Original sentence, differing part marked, explanation (the existing Rule + Application text) | reference + existing explainer | 0 extra |

Hints accumulate on screen. A four-segment bar labelled Where / What kind / Clue / Answer shows how
far the learner has gone; taken rungs get a tick as well as a fill.

**Re-check outcomes.** Each "Check again" is one grader call on the revised sentence.

| Result of re-check | Shown | Recorded outcome |
|---|---|---|
| Revised text matches the reference at the flagged part | "Fixed" + first try vs. now + explanation | `self_repaired` |
| Differs from reference, `p_error < 0.25` | "No issue found in your new version. Here is how the original puts it:" + both sentences | `repaired_alternative` |
| `0.25 ≤ p_error < 0.75` | Same screen as above, worded "We're not sure about this version" | `closed_unsure` (not counted) |
| `p_error ≥ 0.75` | "Still flagged. Try once more, or take the next hint." | stays open |
| Text unchanged | "That's the same sentence. Change something, or take a hint." | no call made |
| 4th failed check | Answer shown automatically: "This one's worth seeing rather than guessing." | `answer_shown` |

The wording follows what the grader can support. A flag is almost always real (precision ≈ 1.0), so
"still flagged" is safe to say. A pass is not proof (recall 50–95%), so the app says "no issue
found", never "correct", and always puts the original next to it.

### 1.3 Encoding severity and confidence

- **Severity is not shown as a label.** It is the least reliable field (54–75% accurate; human raters
  agree only 62–85%). It is used for ordering only. The one exception is the meaning check: all 8
  meaning inversions in the eval were caught, so sentences where the narrow checks fire get a distinct
  red-bordered card with "≠ Meaning differs from the prompt".
- **Confidence is shown in words and line style, never as a number.**

  | State | Border | Chip (icon + text) | Sentence under the chip |
  |---|---|---|---|
  | Repair target | solid amber | ↻ Take another look | "The checker is fairly sure something is off here." |
  | Meaning error | solid red | ≠ Meaning differs from the prompt | same |
  | Unsure | dotted blue, dashed outline | ? Possibly worth a look | "The checker isn't sure about this one. It may be fine." |
  | Clean | none | "Nothing flagged" | — |
  | Fixed | solid green | ✓ Fixed with N hints | — |
  | Answer shown / disputed | grey | → Answer shown / – You disagreed | — |

- **Type confidence.** If the top type's probability is under 0.6, rung 2 shows the two most likely
  types ("Probably word order or a particle"). Under 0.4 the rung is skipped and rung 3 uses a
  type-neutral clue ("Read your sentence against the prompt, clause by clause").

### 1.4 Which errors get a ladder

Hints only help when there is a rule to reach for. Types are marked `hintable` in the taxonomy config
(new field; maps closely onto the existing `treatable` flag).

- **Full ladder:** rule-governed grammar types (zh `measure_word`, `aspect_negation`, `de_particle`,
  `ba_bei`, `complement`; ja `wa_ga`, `case_particle`, `conjugation`, `tam`, `counter`,
  `transitivity_voice`; en `article_determiner`, `agreement`, `verb_form_tense`, `plural_number`,
  `preposition`), plus `word_order`, `register`, `omission`, `addition`.
- **Short ladder (Where → Answer):** `meaning_inversion`, `contradiction`, `semantic_anomaly`. The
  "where" hint with the L1 prompt highlighted is the whole clue.
- **No ladder, shown directly:** `word_choice`, `collocation`, `kanji_choice`, `lexical_form`,
  `phrasal_verb`. A learner who does not know the word cannot retrieve it from a hint.
- **Age tiers 1–2:** short ladder for everything, and clue templates avoid grammar terms.

### 1.5 States

| State | Behaviour |
|---|---|
| **Clean item** | Success card: "Nothing flagged. The checker can miss small things, so the original is below if you want to compare." Reference behind one tap. No repair pass. |
| **Many errors** | Only 3 targets get ladders. The status line reads "3 to look at now · 4 more in the full comparison". If 5 or more sentences are flagged or any dimension would band at 1, skip the repair pass entirely and go to direct feedback: the passage was too hard and repair would be a slog. |
| **Unsure flag** | Dotted card, two buttons: "Compare with the original" (shows both, differing word marked, "Both can work here; the original uses the highlighted word") and "Leave it". Never counted. |
| **Learner disputes** | "I think mine is right" is on every open card. One tap: the original is shown with "Fair enough. Yours may be just as good. We've sent this flag for review and left it out of your progress." The flag is logged for grader QA and, if budget allows, re-judged by the live grader offline. No argument, no penalty. |
| **Learner gives up** | "Show the answer" is one tap at any rung, same visual weight as the other links, no confirmation. Recorded as `answer_shown` at the rung reached. |
| **Location unknown** | If the diff is not a small local edit, rung 1 is removed and the bar shows three segments. If the learner's revision moves text so the marked part no longer exists, the underline moves to the part they changed, or the hint says the location can no longer be pinpointed. |
| **Adaptive start** | If a type's last 3 episodes all needed rung 1 or more, the card opens at rung 1 with a one-line reason. If the last 3 all ended in `answer_shown`, the type switches to direct mode until a review drill succeeds (§2.4). |

### 1.6 Copy (learner's L1)

| Key | English | 中文 | 日本語 |
|---|---|---|---|
| target chip | Take another look | 再看一眼 | もう一度見てみよう |
| meaning chip | Meaning differs from the prompt | 意思和原文不一样 | 元の文と意味が違います |
| unsure chip | Possibly worth a look | 可能值得再看看 | 念のため確認してもよい箇所 |
| unsure body | The checker isn't sure about this one. It may be fine. | 系统对这一句不太确定，也可能没有问题。 | この文は判定に自信がありません。問題ないかもしれません。 |
| clean row | Nothing flagged | 未发现问题 | 指摘なし |
| check | Check again | 再检查一次 | もう一度チェック |
| still | Still flagged. Try once more, or take the next hint. | 仍然有问题。再试一次，或者看下一个提示。 | まだ指摘があります。もう一度試すか、次のヒントを見てください。 |
| fixed, rung 0 | Fixed on your own, on a second look | 再看一眼后自己改对了 | 見直して自分で直せました |
| alternative | No issue found in your new version | 修改后的句子未发现问题 | 直した文に指摘はありません |
| give up | Show the answer | 看答案 | 答えを見る |
| dispute | I think mine is right | 我觉得我的没错 | 自分の文は正しいと思う |
| skip | Skip — show me everything | 跳过，直接看全部结果 | スキップして結果をすべて見る |

Clue examples used in the mockup (real gold items):

- zh `measure_word` (zh_multi_01, 一个 → 一件), L1 English: "衣服 doesn't take the all-purpose 个.
  Which measure word goes with clothes worn on the upper body?"
- ja `wa_ga` (ja_multi_05, 私たちは作るもの → 私たちが), L1 English: "私たち is the subject of a clause
  that describes もの. Inside a describing clause, the subject usually can't be marked as the topic."
- en `meaning_inversion` (en_multi_04, without it → with it), L1 中文: "再读一遍中文原句：'你可以用它
  做很多东西'。你的句子说的是'用它'，还是'不用它'？"

Tone rules: the checker is "the checker", never "you made a mistake". No exclamation marks, no
streaks, no red crosses. "Flagged" and "no issue found" are the only verdict words.

## 2. Tracking model

### 2.1 What is recorded

**`dt_repair_episode`** — one row per flagged sentence that reached the learner.

| Field | Type | Notes |
|---|---|---|
| `id`, `attempt_id`, `user_id`, `sentence_idx` | | links to the DT attempt |
| `error_type` | text | v6 type id (top-1 at first grade) |
| `type_prob`, `p_error` | numeric | from the first grade |
| `severity`, `meaning_check_fired` | text, bool | ordering and red-card state only |
| `group` | enum | `repair_target` / `shown_directly` / `unsure` |
| `ladder_kind` | enum | `full` / `short` / `none` |
| `location_available` | bool | false when the diff was not a local edit |
| `start_rung`, `max_rung` | smallint 0–4 | 4 = answer shown |
| `outcome` | enum | `self_repaired`, `repaired_alternative`, `closed_unsure`, `answer_shown`, `disputed`, `skipped`, `unsure_compared`, `unsure_dismissed` |
| `n_revisions`, `n_regrades` | smallint | |
| `time_ms`, `first_edit_latency_ms` | int | card focused → closed; focused → first keystroke |
| `first_text`, `final_text` | text | learner's sentence before and after |
| `counts_toward_mastery` | bool | false for `unsure`, `disputed`, `closed_unsure`, `skipped` |
| `grader_version`, `taxonomy_version` | | |

**`dt_repair_event`** — append-only, one row per action: `episode_id`, `ts`, `kind`
(`hint_shown` / `revision_checked` / `answer_shown` / `disputed` / `skipped`), `rung`, `text`,
`p_error_after`, `type_after`. This is the audit trail and the dataset for tuning thresholds.

The mockup's summary card has a "What gets recorded" disclosure that prints the episode rows live.

### 2.2 Per-episode credit

Following the "mediated score" idea from computerized dynamic assessment (§3.4):

| Outcome | Credit |
|---|---|
| Fixed at rung 0 | 1.00 |
| Fixed at rung 1 (where) | 0.75 |
| Fixed at rung 2 (what kind) | 0.50 |
| Fixed at rung 3 (clue) | 0.25 |
| Answer shown | 0.00 |

`repaired_alternative` earns the same credit as `self_repaired`. Three or more revisions in one
episode halves the credit (trial and error is not repair). Credit is internal and never shown.

### 2.3 Per-type state (what the learner sees)

For each (user, L2, error type): mean credit over the last 8 counted episodes within 60 days; shown
only once there are 3.

| Mean credit | Label |
|---|---|
| < 0.20 | Needs the answer |
| 0.20 – 0.55 | With a hint |
| 0.55 – 0.85 | When shown where |
| ≥ 0.85 | On a second look |
| no flag of this type in the last 6 passages | "Not flagged in your last 6 passages" |

The last line deliberately says "not flagged", not "mastered": with 50% recall on minor zh/ja errors,
absence of flags is weak evidence.

### 2.4 How it feeds the existing machinery

- **Error vs. slip.** [[features/dual-translation]] already says one-off slips are logged but not
  drilled. Hint level makes that operational. Toward the "recurs ≥ N" promotion threshold, an
  `answer_shown` episode counts 1, a rung 2–3 repair counts 0.5, a rung 0–1 repair counts 0.
- **Remediation queue.** Types in "Needs the answer" for 3 episodes running go into direct mode
  (answer shown at once, followed by the existing cloze and isolate-and-re-translate drills). They
  return to the ladder after one successful delayed drill.
- **Start rung.** The next episode of a type opens one rung below the median rung of its last 3
  successful repairs, never above rung 1.

### 2.5 Where it surfaces

1. **End of the repair pass** — summary card: one row per error type with the outcome and its
   consequence ("Fixed once you knew where · counted as a slip, no drill").
2. **My Error Profile** (`templates/dual_translation_profile.html`) — each pattern card gains a
   four-step track with the current position filled, a dashed marker for the position four weeks ago,
   a strip of the last 8 episodes (digit = hints used, A = answer shown), and one sentence of
   interpretation. Above the cards, four counts for the week: flagged, fixed yourself, needed the
   answer, disagreed.
3. **Weekly study plan** — one line per type that changed state ("了/过: now fixable with a clue").

No percentages, ranks or streaks, in line with the profile page's existing rule.

## 3. Pedagogy rationale

Citation status: **[V]** bibliographic details and the stated finding were confirmed by web search in
this session. **[B]** bibliographic details confirmed; the finding is stated from my knowledge of the
paper and was not re-confirmed. **[M]** from memory only, not checked this session. Treat [B] and [M]
findings as needing a check against the original before they are quoted elsewhere.

### 3.1 Prompts produce more learner repair than recasts

- Lyster & Ranta (1997), "Corrective feedback and learner uptake: Negotiation of form in
  communicative classrooms", *Studies in Second Language Acquisition* 19, 37–66. Recasts were 55% of
  teacher feedback and elicitation 14%; recasts led to repair in about 18% of cases **[V]**. My
  recollection that recast uptake was 31% and elicitation uptake 100% is **unverified**.
- Lyster & Saito (2010), "Oral feedback in classroom SLA: A meta-analysis", *SSLA* 32, 265–302:
  15 classroom studies, N = 827; effects were larger for prompts than for recasts **[V]**.

*Decision it drives:* withhold the correct form and push the learner to produce it (rungs 0–3).
*Limit:* both are about oral classroom feedback. Transfer to written, computer-delivered feedback is
an inference.

### 3.2 Pushed output and noticing

- Swain (1985), "Communicative competence: Some roles of comprehensible input and comprehensible
  output in its development"; Swain (1995), "Three functions of output in second language learning"
  **[M]**. Producing language, and being pushed to make it more accurate, makes learners notice gaps
  and test hypotheses.
- Schmidt (1990), "The role of consciousness in second language learning", *Applied Linguistics* 11
  **[M]**.

*Decision it drives:* the revision field is pre-filled and editable so that the response to feedback
is a new production, not a click. This matches the feature's stated purpose ("noticing of the gap").

### 3.3 Indirect vs. direct written corrective feedback — the evidence is mixed

- Ferris & Roberts (2001), "Error feedback in L2 writing classes: How explicit does it need to be?",
  *Journal of Second Language Writing* 10, 161–184 **[B]**. Coded and merely underlined errors both
  beat no feedback for self-editing, with little difference between them.
- Chandler (2003), "The efficacy of various kinds of error feedback…", *JSLW* 12, 267–296 **[M]**.
  Direct correction and plain underlining both outperformed describing the error type; direct was
  fastest and preferred, though students felt they learned more from self-correcting.
- Van Beuningen, De Jong & Kuiken (2012), "Evidence on the effectiveness of comprehensive error
  correction in second language writing", *Language Learning* 62, 1–41, N = 268 **[V]** for the study
  and its conclusion that comprehensive feedback improves accuracy. That direct feedback did better
  on grammatical errors and indirect on non-grammatical ones is **[B]**.
- Bitchener & Knoch (2010), "Raising the linguistic accuracy level of advanced L2 writers with
  written corrective feedback", *JSLW* 19, 207–217 **[M]**. Direct metalinguistic feedback held up
  over 10 weeks; indirect circling did not.
- Kang & Han (2015), "The efficacy of written corrective feedback in improving L2 written accuracy:
  A meta-analysis", *Modern Language Journal* 99, 1–18 **[V]**: small-to-moderate overall benefit,
  moderated by proficiency, setting and genre. Secondary sources disagree on whether it found direct
  feedback significantly better than indirect, so no claim is made here.
- Ferris (1999), "The case for grammar correction in L2 writing classes: A response to Truscott
  (1996)", *JSLW* 8 **[M]**: "treatable" (rule-governed) vs. "untreatable" (lexical, idiomatic)
  errors.
- Shintani & Ellis (2013), on direct feedback vs. metalinguistic explanation for the English
  indefinite article, *JSLW* 22 **[M]**: metalinguistic explanation helped explicit knowledge, but the
  gain was not durable.

*Honest reading:* this literature does **not** show that indirect feedback beats direct feedback.
Several well-run studies favour direct correction for grammar, and for lower-proficiency learners.
What it supports is narrower: indirect feedback works about as well when the learner already has the
knowledge to self-correct, and it does not work for errors with no rule behind them.

*Decisions it drives:* (a) every episode ends with the direct correction on screen — the ladder
changes when the answer arrives, not whether; (b) untreatable types skip the ladder (§1.4); (c) low
age tiers get the short ladder; (d) types that repeatedly end in `answer_shown` revert to direct
feedback (§2.4).

### 3.4 Graduated, contingent help

- Aljaafreh & Lantolf (1994), "Negative feedback as regulation and second language learning in the
  zone of proximal development", *MLJ* 78, 465–483. The regulatory scale, implicit to explicit, is on
  p. 471 **[V]**; that it has 13 levels (0–12) is **[M]**. Help should be graduated (no more explicit
  than needed) and contingent (withdrawn when not needed), and movement toward the implicit end of
  the scale is itself development.
- Nassaji & Swain (2000), "A Vygotskian perspective on corrective feedback in L2: The effect of random
  versus negotiated help…", *Language Awareness* 9 **[M]**. Graduated help beat random help — in a
  study of two learners, so weak evidence.
- Poehner, Zhang & Lu (2015), "Computerized dynamic assessment (C-DA): Diagnosing L2 development
  according to learner responsiveness to mediation", *Language Testing* 32(3), 337–357 **[V]**:
  reports both an actual score and a *mediated* score reflecting how much support was needed. Poehner
  & Lantolf (2013), "Bringing the ZPD into the equation", adds a learning-potential score **[V]**.

*Decisions it drives:* the ladder order, the adaptive start rung, and the whole tracking model. "How
much help was needed" is an established construct with a precedent in computerized testing, not a
novelty.

### 3.5 Retrieval, generation, desirable difficulty

- Bjork (1994), "Memory and metamemory considerations in the training of human beings" **[M]**.
- Slamecka & Graf (1978), "The generation effect: Delineation of a phenomenon" **[M]**.
- Roediger & Karpicke (2006), "Test-enhanced learning", *Psychological Science* 17 **[M]**.
- Kornell, Hays & Bjork (2009), "Unsuccessful retrieval attempts enhance subsequent learning" **[M]**.
- Pashler, Cepeda, Wixted & Rohrer (2005), "When does feedback facilitate learning of words?" **[M]**:
  after an error, being given the correct answer matters a great deal; right/wrong alone does little.
- Finn & Metcalfe (2010), "Scaffolding feedback to maximize long-term error correction", *Memory &
  Cognition* 38, 951–961 **[B]**. As I recall it, incremental hints that let learners generate the
  answer beat standard feedback on delayed tests. A later review found in this session says studies
  on hints "drew different conclusions", so this is contested.
- Kornell, Klein & Rawson (2015), "Retrieval attempts enhance learning, but retrieval success (versus
  failure) does not matter" **[M]**.
- A study titled "Effects of elaborate feedback during practice tests: Costs and benefits of retrieval
  prompts" (found via search; **authors unverified**) reports that hints shifted time from repetitions
  to feedback processing and were not preferable to showing the answer for vocabulary.

*Honest reading:* the robust finding is that **attempting** before seeing the answer helps, provided
the answer follows. Whether climbing several rungs adds anything beyond one attempt is unproven, and
for word-level knowledge the evidence leans against it.

*Decisions it drives:* rung 0 (one free attempt with no hint) is the highest-value step and is always
offered; the ladder is short; the attempt cap is 4; the answer always follows; vocabulary-type errors
get no ladder.

### 3.6 Hypercorrection

- Butterfield & Metcalfe (2001), "Errors committed with high confidence are hypercorrected" **[M]**;
  Metcalfe (2017), "Learning from errors", *Annual Review of Psychology* 68 **[B]**.

*Decision it drives:* the DT page already collects a self-rating before submission. A flagged
sentence in a passage the learner rated highly is a strong teaching moment, so the summary card
calls it out ("You were confident about this one"). Sentence-level confidence is not collected;
adding it would cost a tap per sentence and is not proposed.

### 3.7 CALL-specific evidence

- Heift (2004), "Corrective feedback and learner uptake in CALL", *ReCALL* 16, 416–431 **[V]**.
  Metalinguistic feedback plus highlighting produced the most uptake of three feedback types; a
  secondary summary says the difference was not statistically significant, and uptake there meant
  "attempted a correction", not durable learning.

### 3.8 Error vs. mistake

- Corder (1967), "The significance of learners' errors", *IRAL* 5 **[M]**. A learner who repairs
  unaided at rung 0 had the knowledge and slipped. One who needs the answer has a gap. Right/wrong
  scoring cannot tell these apart; hint level can.

## 4. Design rationale

**Interaction cost.** Best case for one target: read, edit, Enter — one extra action over reading a
correction. Worst case: 3 hint taps and 4 checks. My estimate, not measured: 15–40 s per target,
45–120 s added per passage at the cap. Mitigations: cap of 3, Enter submits, one-tap answer, skip
link, automatic bypass for badly failed passages, direct mode for types that hints do not help.

**Visual hierarchy.** The learner's own sentence is the largest text on each card (1.2 rem), then the
edit field, then the primary button. Hints sit between sentence and field so they stay visible when a
phone keyboard is open. Clean sentences collapse to one muted row so that flagged ones stand out
without red ink. On desktop the L1 prompt is a sticky left column with the current sentence tinted;
on phones it collapses and each card repeats its own L1 sentence.

**Colour is never the only signal (WCAG 1.4.1).** Every state has an icon and a text label as well as
a border colour; confidence uses solid vs. dotted borders; ladder progress uses ticks as well as fill;
the progress strip uses digits and a letter. Text colours use the app's AA-safe tokens
(`--warning-text`, `--apricot-text`). Status messages use `role="status"`/`aria-live="polite"`.
Controls are at least 44 px tall on phones. Motion is one 350 ms fade on a new hint, disabled under
`prefers-reduced-motion`.

**CJK and IME.**
- Enter triggers a re-check only when no composition is open (`!event.isComposing && keyCode !== 229`).
  In Chinese and Japanese input, Enter also confirms a candidate; submitting then would send
  half-typed text. The mockup implements this.
- No checking while typing. Re-checks happen on the explicit button or Enter only. Composition events
  fire per keystroke and intermediate strings are not the learner's text.
- Spans are character offsets, since zh/ja have no word spaces. The underline is a bottom border with
  a tint, which stays legible under dense glyphs where wavy underlines smear.
- `lang` is set on every L2 and L1 run so Han characters render with the right regional glyphs,
  following the `:lang()` font rule in `static/css/styles.css`.
- Input text is at least 16 px to prevent iOS zoom-on-focus; `autocapitalize`, `autocomplete` and
  `spellcheck` are off so the OS does not silently "fix" the learner's text.
- Japanese: kana-vs-kanji spelling of the same word is not an error under v6 (`script_choice` was
  dropped), so the "matches the reference" test normalises to readings before comparing.

**Mobile.** Single column; edit field and button stack full-width; the tab bar scrolls; no horizontal
page scroll at 390 px (checked with Playwright).

**Tone.** Matches the "Still Water" system's stated anti-gamification stance: calm, factual, the
checker is fallible and says so.

## 5. Data requirements

### 5.1 From the grader, per sentence pair (first grade and every re-grade)

| Field | Have today? | Use |
|---|---|---|
| `p_error` | yes | triage, pass/fail on re-check |
| `types`: top-3 with probabilities | top-1 yes; top-3 needs the pick-one probabilities exposed | rung 2, two-type fallback |
| `severity` + probability | yes (unreliable) | ordering only |
| narrow checks: negation, quantity, agent swap, omission, addition | yes | red "meaning differs" state; short ladder |
| sentence alignment index | yes | card ↔ L1 sentence |
| `grader_version` | — | audit |

### 5.2 Span offsets — not from the grader

The grader judges a sentence pair and returns no span. The "where" hint uses the existing
deterministic diff:

1. Take diff opcodes inside the flagged sentence.
2. If the changed text is one region covering ≤ 40% of the sentence, that is the span.
3. If there are two regions, optionally spend one extra classifier call ("which part contains the
   error: A or B?"); otherwise underline both.
4. Otherwise `location_available = false` and the ladder drops rung 1.

Caveat: in the gold set every reproduction is the reference with a planted edit, so the diff finds
the span perfectly. Real learners paraphrase. A learner whose sentence differs from the reference in
several legitimate ways will often land in case 4. The share of real submissions with a usable span
is unknown and should be measured from stored reproductions before build.

### 5.3 Hint content

| Rung | Source | Cost |
|---|---|---|
| Where | diff | 0 |
| What kind | taxonomy `name` per L1 (exists in v6) | 0 |
| Clue | new template per type x L1, about 60 per L2 x L1 pair incl. tier variants | 0 at runtime; one-off authoring + native review |
| Answer | reference + existing explainer text | 0 extra |

An LLM-written, sentence-specific clue is optional and not in the base design: it adds cost and
latency, and risks leaking the answer or asserting something false about a sentence the grader
mislabelled.

### 5.4 Cost

Taking the brief's $0.0002 and 0.3 s per call as upper bounds:

| | Calls | Cost |
|---|---|---|
| First grade, 4-sentence passage | ≤ 4 | ≤ $0.0008 |
| Repair, expected (≈ 1.5 targets x ≈ 1.6 checks) | ≈ 2.4 | ≈ $0.0005 |
| Repair, worst case (3 targets x 4 checks) | 12 | $0.0024 |

Worst case, repair triples the cheap grader's cost per passage and is still a small fraction of one
live-grader call (the eval puts the cheap grader at 200–400x cheaper). At 1,000 passages a day the
repair pass costs about $0.50 expected, $2.40 worst case. The expected figures rest on my assumptions
about flag and retry rates.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Flag is wrong.** Rare for "error present", but the learner is then asked to fix a correct sentence. | Dispute button on every card, no penalty; "may be fine" wording below 0.75; nothing below 0.75 gets a ladder; dispute rate per type monitored. |
| **Type is wrong** (5–31% of the time). Rungs 2–3 then mislead. | Two-type wording under 0.6, skipped under 0.4; clues phrased as questions, not assertions; rung 1 does not depend on type; the answer and comparison are type-independent. |
| **Valid alternative.** The revision is fine but differs from the reference. | Pass is decided by the grader, not by string match; outcome `repaired_alternative`, full credit; reference shown as "how the original puts it". |
| **False pass.** The revision is still wrong but the grader misses it. | "No issue found", never "correct"; reference always shown beside it. |
| **Revision introduces a new error elsewhere.** | Still flagged, so the card stays open; after 2 failed checks the copy points to the next hint; hard stop at 4. |
| **Location unavailable or wrong.** | Rung dropped when the diff is not local (§5.2); underline follows the learner's edits. |
| **Time and fatigue.** | Caps, skip, bypass for failed passages, direct mode; guardrail metrics in §7. |
| **Frustration at being made to guess.** | Rung 0 is an invitation, not a gate: the answer is one tap away from the first second. |
| **Trial-and-error gaming.** | Attempt cap; credit halved at 3+ revisions; unchanged text is not re-checked. |
| **Missed errors never get repaired** (recall 50% on zh/ja). | The existing result screen still shows the full diff afterwards. This option does not make recall worse; it does not fix it either. |
| **Tracking reads as mastery when it is absence of flags.** | "Not flagged in your last 6 passages" wording; minimum 3 episodes; disputed and unsure episodes excluded. |
| **Clue templates are generic or wrong for a sentence.** | Native review; templates state the rule and never describe the specific sentence. |
| **Eval basis is synthetic.** All grader numbers come from seeded errors on 10 passages per language. | Ship behind the A/B flag; log every event; re-tune thresholds on real data. |

## 7. A/B test

**Arms.** A: `direct_metalinguistic` (current default). B: `guided_repair`. The `flag_only` arm from
TASK-617 can run as a third arm to separate "withholding" from "laddered hints". Randomise by user.

**Primary metric: delayed unaided re-translation.** Seven days (± 2) after an error episode, the
learner is given the same L1 sentence through the existing isolate-and-re-translate drill, with no
hints. Success = the original error type is not flagged and the flagged part matches the reference or
passes the grader. Compared per episode, clustered by user. Both arms use the same grader, so its
misses affect them equally. Detecting a 10-point difference from a 50% baseline needs about 390
episodes per arm before the clustering adjustment.

**Secondary.** Same-type flags per 100 graded sentences on *new* passages over 28 days; share of
episodes fixed at rung 0–1 over time (arm B only).

**Guardrails.**

| Metric | Stop / rethink if |
|---|---|
| Median time per passage | more than +120 s vs. arm A |
| Passage completion rate | more than 3 points lower |
| DT passages per active week | more than 10% lower |
| "Skip — show me everything" rate | above 50% |
| Dispute rate | above 8% of repair targets |

**What would change the design.** If arm B wins only on rule-governed types, keep §1.4 as is. If
`flag_only` matches B, drop rungs 2–3 and keep "where → answer". If B loses or is flat with a clear
time cost, the ladder should not ship and only the tracking of first-attempt self-repair (rung 0) is
worth keeping.

## Related Pages
- [[features/dual-translation]] · [[features/dual-translation.tech]]
- [[features/dual-translation-remediation.tech]]
- [[decisions/ADR-031-dt-taxonomy-v6-merge]]
- [[evaluations/jev-dt-tuning-2026-09-27]]
- [[business-rules/translation-error-taxonomy]]
