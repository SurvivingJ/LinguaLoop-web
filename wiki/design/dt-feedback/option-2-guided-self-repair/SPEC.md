---
title: "DT Feedback — Option 2: Guided Self-Repair (hint ladder, retry before reveal)"
type: feature
status: planned
decision: "Chosen by the owner on 2026-11-14 over options 1 and 3. Not yet built."
last_updated: 2026-11-14
open_questions:
  - "ANSWERED 2026-11-14: The 'where' hint uses the span returned by the generative grader, not the diff (see Revision 2026-11-14)."
  - "OPEN: The chosen grader returns an error list with no probabilities. The 'unsure' state and the two-type fallback have no data source until a confidence field is added to the grader schema and tested."
  - "OPEN: Recall falls to .72 on heavily rephrased text and nothing has been run on real learner submissions; a shadow run comes first."
  - "OPEN: Daily-practice intervals, caps and the 'resolved' rule (section 8) are design defaults, not tuned values."
  - "OPEN: Which database size limit applies, and where grading results are stored at all (open since September)."
  - "OPEN: Thresholds (confidence bands, repair cap of 3, attempt cap of 4, credit weights) are design defaults, not tuned values."
  - "OPEN (Revision 2): zh and ja interface strings for the app-style flow are not written; real-device and keyboard behaviour is untested."
  - "OPEN: Hint templates need writing and native review for ~20 types x 3 L2s x 3 L1s."
---

# Option 2 — Guided Self-Repair

One of three competing options for presenting and tracking Dual Translation (DT) feedback.
Companion files (Revision 2): [`mockup.html`](./mockup.html) (working simulation), `mobile.png` and
`desktop.png` (contact sheets), `steps/` (one PNG per step, en flow), [`verify.cjs`](./verify.cjs)
(the no-scroll test). Superseded, kept for reference: `mockup-v1.html`, `mobile-v1.png`,
`desktop-v1.png`, `mobile-daily-v1.png`, `desktop-daily-v1.png`.
Context: [[features/dual-translation]], [[decisions/ADR-031-dt-taxonomy-v6-merge]],
[[evaluations/jev-dt-tuning-2026-09-27]].

## Revision 2 — 2026-11-14 (app-style flow)

**Why.** The owner rejected the first mockup: "the mockup is much too busy - imagine it needs to be
designed like an app. it just pops up, you get through one part and it opens the next - no scrolling."
Earlier: "it just needs to be clearer what the input box is." The first mockup put the whole passage
on one long page (4,152 px tall at 390 px wide for two flagged sentences) with every card, hint bar,
chip and counter visible at once.

This revision changes the **presentation only**. The ladder, the grader contract, the credit model and
the daily-practice rules (§1.2 outcomes, §2, §5, §8.1–8.4) are unchanged. Where an older section
describes layout, it is marked **Superseded by Revision 2**.

### R2.1 Interaction model

1. **It pops up.** After Submit, feedback opens as a modal sheet over the exercise: full screen on a
   phone, a centred 420 px card on wider screens with the exercise dimmed behind it.
2. **One step per screen.** Each screen has one sentence, one problem, one input and one primary
   button. The sheet has three fixed zones: header (close button, progress dots), content, and a
   bottom action area in thumb reach.
3. **No scrolling, ever** (acceptance criterion, R2.5).
4. **It advances by itself.** A successful check shows a short success moment and moves to the next
   sentence after about 1.6 s; a "Next" button is there for people who do not want to wait, and it is
   the only way forward when reduced motion is requested.
5. **Hints replace each other.** There is one hint slot under the field. A new hint, or a "still not
   quite" message, takes the place of what was there.
6. Steps change with a short slide and fade (off under `prefers-reduced-motion`).

### R2.2 Steps

| # | Screen | What is on it | Primary action | Quiet actions |
|---|---|---|---|---|
| 0 | Exercise (existing page) | Prompt, the learner's translation | Submit (shows "Checking…") | — |
| 1a | Result | A large number and "sentences to fix"; one line "The other N look fine." | Start | — |
| 1b | Result, clean | Tick, "No issues found", one line | Done | — |
| 2 | Fix | The L1 prompt sentence (quiet, two lines at most); the label "Fix your sentence"; the field, pre-filled with the learner's sentence | Check | "Need a hint?", "Mine is fine" |
| 3 | Fix + hint | Same screen. Hint 1 underlines the grader's span inside the field ("Look at the underlined part."); hint 2 names the type; hint 3 is the clue. Each replaces the last. The quiet button reads "Need a hint?" → "Another hint" → "Show answer". | Check | as above |
| 4 | Checking | Same screen; the button shows a spinner and "Checking…", the field is read-only, a second press is ignored (1–2 s) | — | — |
| 5a | Still not quite | Same screen; the slot says "Still not quite. Try again, or take a hint."; the field shakes once. Unchanged text: "That's the same sentence. Change something first." (no grader call) | Check | as above |
| 5b | Fixed | Tick, "Fixed", one line ("On your own" / "With 2 hints") | Next (auto after ~1.6 s) | — |
| 6 | Answer | "The original", the original sentence with the differing part marked, one line of explanation. Also used, with a different heading, for "No issue found. The original says:" and after a dispute ("Noted. The original says:"). Reached by "Show answer" or automatically after the 4th failed check (3rd in daily practice). | Next | — |
| 7 | Summary | "All done" and three counts: Fixed yourself / Needed help / Saved to practice | Done → existing result screen | — |

Progress is a row of dots in the header (the current one is longer, so shape as well as colour
carries it) with "Sentence 1 of 2" for screen readers. The close button ends the pass and goes to the
existing result screen; unfinished sentences are recorded as `skipped` and queued per §8.1. This
replaces the always-visible "Skip — show me everything" link.

**Uncertain flag** (needs a confidence field from the grader, still an open question): the same
single screen, phrased as a question. The label is "This part may need another look", the span has a
dotted underline from the start, there is no hint ladder, and the action area holds two buttons of
equal weight, "Mine is fine" and "Check". "Check" becomes the filled button only after the learner
changes the text. "Mine is fine" shows "Kept as written" and moves on.

**Daily practice** uses screen 2 unchanged, opened from the practice entry point, one item at a time,
with one extra line above the prompt: "From your translation on Tuesday". It opens with the span
already underlined (§8.3), so the first hint asked for is the type. The summary's third count reads
"Back in practice later".

**The field** (replaces the layout part of §1.2a; the behaviour there still holds). A real `<label>`
with a pencil icon, "Fix your sentence", sits directly on a large bordered field (2 px border, 20 px
text, the page's only white surface). It is pre-filled with the learner's sentence. It takes focus
automatically on pointer devices; on touch devices it waits for a tap so the keyboard does not cover
the screen before the learner has read it. Focus shows a 4 px ring and a coloured caret. The "where"
underline is drawn inside the field, under the learner's own words, and disappears once those words
are edited away. Enter submits; the field holds one sentence and no line breaks. The field stays in
the upper part of the screen. When the on-screen keyboard is open the screen keeps only the label,
the field, the hint and one row with "Check" and the hint button.

### R2.3 Removed from v1, and why

| Removed | Why |
|---|---|
| The whole passage on one page, clean sentences listed between flagged ones | The cause of the scrolling. Clean sentences are now one line on the result screen. |
| Demo tab bar inside the screen | Mock controls must not look like product UI. Language and scenario are two small controls on the mock start screen only. |
| "Take another look" / "Meaning differs" / severity chips, numbered sentence badges, "2 to look at · 2 with nothing flagged" counters | Several competing labels per card. The step label and the result number say the same thing once. |
| Four-segment "Hints used" bar (Where / What kind / Clue / Answer) | A legend for something the learner does not need to manage. Replaced by "Hint 2 of 3" on the hint itself. |
| Hints stacking above the field | Pushed the field down and off the screen. One slot, replaced in place. |
| "Your last checked version" panel above the field, and the instruction paragraph "Your sentence is already in the box…" | The field itself now carries the underline, and the label is enough. |
| "Check 1 of 4" counter | Pressure without information. The cap still applies. |
| Then-vs-now comparison and explanation after a self-fix | The success moment is a beat, not a reading task. The explanation is shown when the answer had to be given, and is on the existing result screen for every sentence. |
| "What gets recorded" disclosure, per-type progress panel, side panel with the full prompt | Developer or secondary content. Recording is specified in §2 and is not shown to the learner here. |
| Always-visible "Skip — show me everything" | Replaced by the close button. |

Kept deliberately: at most two quiet text buttons, and "Mine is fine" on every fix step, because the
grader can be wrong (§1.2).

### R2.4 Long sentences

The longest gold sentences were used as test items: en 69 characters (`en_clean_01`), zh 53
(`zh_seed_14`), ja 82 (`ja_seed_02`).

1. The field grows with its text. If it would not fit, the type steps down 20 → 18 → 16 → 15 px.
2. Past the smallest step the field scrolls inside itself; the page still does not. No gold sentence
   reaches this at the tested sizes.
3. The L1 prompt is clamped to two lines. If it is cut, tapping it opens the full prompt as an
   overlay on the same screen; tapping again closes it.
4. The answer screen uses the same type steps (24 → 20 → 17 → 15 px).
5. With the keyboard open on a short phone the prompt line is hidden, and below 400 px of visible
   height the label is hidden visually while a hint is showing (it stays available to screen readers).

Hint text is limited by rule: a clue is at most two short sentences (about 120 Latin characters or
60 CJK characters) and an explanation is one line (about 90 Latin or 45 CJK characters). Templates
longer than this fail review.

### R2.5 Acceptance criteria for implementation

- **No scroll.** On every step, in every state, `document.scrollingElement.scrollHeight <= window.innerHeight`
  and there is no horizontal overflow, at 390×844, 375×667 and 1280×800, in light and dark, and with
  the keyboard open (visible height 500 and 340 px). No element is clipped by, or hidden behind, the
  bottom action area. `verify.cjs` is the reference test; the implementation needs an equivalent.
- One primary button per screen (the uncertain step has two neutral ones). At most two quiet actions.
  At most three text elements above the field.
- Touch targets at least 44×44 px; WCAG 2.2 AA contrast; the underline, the dot shapes and the icons
  carry meaning without colour; CJK text uses the CJK font stacks and a line height of 1.65–1.7.
- No mock or debug control appears inside the flow.
- Every step event is still recorded (§2.1): hint level reached, each checked revision with its
  result and latency, time since the previous event, answer shown (asked or automatic), dispute,
  skip, and the episode outcome with total time. The mockup writes these to `window.__events`.

**Verified in the mockup** (2026-11-14, Chromium via Playwright, `node verify.cjs`): 766 step checks
passed, 0 failed. They cover en and zh flows (fix first try, all hints then answer, four failed
checks, no-issue-found, dispute, clean, uncertain, daily practice) and the three longest-sentence
items, at the three viewports and two keyboard-open sizes, in light and dark.

**Not verified:** real devices and real on-screen keyboards (the keyboard is simulated by a shorter
viewport); Safari and Firefox; screen readers; contrast was chosen from the app's tokens and not
measured by a tool; the Japanese and Chinese glyphs in the screenshots come from the test machine's
fallback font; UI copy is shown in English only, so the length of zh and ja interface strings is
untested; the mockup's ja item is reachable only by `?stress=ja`.

## Revision 2026-11-14 (post-experiment)

**Status.** The owner chose this option on 2026-11-14: "the guided process in mockup two is the way
to go - it just needs to be clearer what the input box is. We can then keep track of these errors and
include them in the daily practice having them fix the error in their translations." Frontmatter
`status` stays `planned` (nothing is built); the choice is recorded in `decision`.

The original spec assumed the September jev grader. [[evaluations/dt-decision-grading-2026-11-14]]
replaces that assumption. Sections below are corrected in place and marked **(rev. 2026-11-14)**.

| # | Was | Now | Where |
|---|---|---|---|
| 1 | Grader = jev decision model, one call per changed sentence, returns `p_error` and type probabilities | Grader = one generative call, `openai/gpt-6-luna`, structured output: a list of errors, each with subtype, severity, a span in the learner's text and a short explanation. Decision models are rejected (they flagged 31–76% of correct rephrased sentences). | §1.1, §5.1 |
| 2 | "Where" hint from the character diff | "Where" hint from the model's span. On heavily rephrased text the diff was a small local edit for only 12 of 40 errors; the model's span was on the error every time it flagged the right sentence (24 of 24 for GPT-6 Luna). | §1.2, §5.2 |
| 3 | Re-check in about 0.3 s | Re-check in about 1–2 s (p50 1.36 s). The UI needs a real checking state and a double-submit guard. | §1.2a |
| 4 | $0.0002 per call | About $0.00006 per call. Figures recomputed with arithmetic. | §5.4 |
| 5 | Explanation from the existing explainer | A short explanation arrives with the grade. Hint text for "what kind" and "clue" stays templated: model-written hints leaked the answer in 9–40% of texts, templates in 0%. Any model hint must pass a code-level leak filter. | §5.3 |
| 6 | Confidence bands from `p_error` | No probabilities exist. A sentence is flagged if the error list has an entry for it. The "unsure" state is kept in the design but has no data source yet. | §1.1, §1.3 |
| 7 | Input field described in one line | The field is specified as a component, pre-filled, with the decision recorded. | §1.2a |
| 8 | Unrepaired errors fed the existing remediation queue only | Errors not self-repaired at the first hint level return in daily practice as "fix your own sentence" items. | §8 |
| 9 | Event log sketched | Per-attempt record and storage budget specified. | §2.1, §8.5 |

Not changed: the ladder, the credit model, the pedagogy citations (§3; none added), the A/B design.

Caveats carried over from the experiment: every number is from seeded errors or model-written
paraphrases, none from real learners; n = 30 per language; the Track E checker is from the same model
family as GPT-6 Luna, which may flatter its false-alarm rate; hint templates and explanations have
had no native-speaker review.

## 0. The option in one paragraph

After the learner submits, the app does not show the correction. It marks which sentences have a
problem and lets the learner fix them. Help arrives one step at a time and only when asked for:
**where** the problem is, **what kind** it is, a **clue** about the rule, and finally the **answer**.
Every revision is re-checked by the cheap grader in about 1–2 s (rev. 2026-11-14; was 0.3 s). Every episode ends with the original
sentence on screen, whoever produced the fix. What gets tracked is how much help each error type
needed, which separates slips from gaps and shows a rule forming long before the error disappears.

The existing page already has a seam for this: `data-correction-style` in
`templates/dual_translation.html` (TASK-617) switches between `direct_metalinguistic` and
`flag_only`. This option is a third value, `guided_repair`, that runs **before** the existing result
screen (diff, bands, error cards), which stays as the final step.

## 1. In-the-moment flow

### 1.1 Sequence

> **Superseded by Revision 2 (layout only).** Step 3 is no longer a page of cards: one sentence per screen (R2.2). "Skip — show me everything" is the close button. Triage, cap and scoring are unchanged.

1. **Submit.** The passage is split into aligned sentence pairs. **(rev. 2026-11-14)** The whole
   item goes to the grader in one call, which returns a list of errors; each error names its
   sentence, subtype, severity, a span in the learner's text and a short explanation. A passage
   identical to the reference skips the call.
2. **Triage** (server, instant). Each graded sentence falls into one of four groups.
   **(rev. 2026-11-14)** The grader returns no probabilities, so read the table below as:
   *clean* = no error listed for the sentence; *repair target* / *shown directly* = an error is
   listed; *unsure* = not available until the grader schema carries a confidence field (untested;
   open question). The `p_error` thresholds are kept only as the original design intent.

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

> **Superseded by Revision 2 (layout only).** Hints no longer accumulate and there is no four-segment bar; one hint slot is replaced in place (R2.1, R2.2). Rungs, sources and re-check outcomes are unchanged.

The learner's own sentence is pre-filled in an editable field (§1.2a). They can edit and press
"Check" at any rung, or take the next hint.

| Rung | Button | What appears | Source | Cost |
|---|---|---|---|---|
| 0 | (none) | Sentence is marked "Take another look". No location, no type. | error listed for the sentence | 0 |
| 1 Where | "Hint: where?" | Underline on the suspect part of the learner's sentence. For meaning errors, the matching part of the L1 prompt is highlighted too. | grader span (§5.2; rev. 2026-11-14, was the diff) | 0 |
| 2 What kind | "Hint: what kind?" | v6 type name in the learner's L1, e.g. "Measure word (量词)" | grader subtype → taxonomy name template | 0 |
| 3 Clue | "Hint: give me a clue" | One or two sentences that state the rule or pose a question. Never contains the corrected form. | template per type x L1 | 0 |
| 4 Answer | "Show the answer" | Original sentence, differing part marked, explanation | reference + the explanation returned with the grade | 0 extra |

Hints accumulate on screen. A four-segment bar labelled Where / What kind / Clue / Answer shows how
far the learner has gone; taken rungs get a tick as well as a fill.

**Re-check outcomes.** Each check is one grader call on the revised sentence. **(rev. 2026-11-14)**
Without probabilities the rows collapse to three results: the flagged error is gone and the text
matches the reference there (**fixed**); no error is listed but the text differs from the reference
(**no issue found**); an error is still listed for the sentence (**still flagged**). The
`closed_unsure` row cannot occur until a confidence field exists.

| Result of re-check | Shown | Recorded outcome |
|---|---|---|
| Revised text matches the reference at the flagged part | "Fixed" + first try vs. now + explanation | `self_repaired` |
| Differs from reference, `p_error < 0.25` | "No issue found in your new version. Here is how the original puts it:" + both sentences | `repaired_alternative` |
| `0.25 ≤ p_error < 0.75` | Same screen as above, worded "We're not sure about this version" | `closed_unsure` (not counted) |
| `p_error ≥ 0.75` | "Still flagged. Try once more, or take the next hint." | stays open |
| Text unchanged | "That's the same sentence. Change something, or take a hint." | no call made |
| 4th failed check | Answer shown automatically: "This one's worth seeing rather than guessing." | `answer_shown` |

The wording follows what the grader can support. **(rev. 2026-11-14)** For GPT-6 Luna a flag is
usually real (precision .96 on near-copies, .91 on heavily rephrased text), so "still flagged" is
safe to say and the dispute link covers the rest. A pass is not proof (recall .88, falling to .72 on
heavily rephrased text), so the app says "no issue found", never "correct", and always puts the
original next to it.

### 1.2a The revision field (rev. 2026-11-14)

> **Superseded by Revision 2 (layout only).** The field's placement and surrounding panels are replaced by R2.2 "The field". Pre-filling, the checking state and the double-submit guard still apply.

**What was unclear in the first mockup** (screenshots at 390 px and 1280 px): the learner's sentence
appeared twice with nothing saying which copy was which; the editable copy had no label and looked
like a second read-only display; the hint-progress bar sat between the two, reading as a heading for
the box; nothing said whether to retype the whole sentence or only the fix; the button said "Check
again" before anything had been checked; the field border (`--border-strong` on white, about 1.7:1)
and the 25%-alpha focus ring were below the 3:1 that WCAG 1.4.11 asks for; and the re-check was
instant, so there was no checking state.

**Decision: pre-fill the field with the learner's own sentence, editable in place.** Not an empty box.

- The task is to repair a sentence, and repair is an edit. An empty box turns it into a second
  translation and invites new errors in parts that were fine, which the grader would then flag.
- Retyping 20–40 characters through an IME on a phone is the largest cost in the flow; pre-filling
  cuts the best case to a one- or two-character change.
- It answers "whole sentence or just the fix?" without words: the whole sentence is there, change
  the part that is wrong. The re-check needs the whole sentence anyway.
- Cost: the learner can press Check without changing anything. That case makes no grader call and
  shows "That's the same sentence".
- Cost: less retrieval effort than producing the sentence again. Accepted here; the daily-practice
  item (§8) is where the delayed attempt happens, and it is pre-filled for the same reasons.

**Component (same one in the repair pass and in daily practice).** One bordered panel contains, top
to bottom:

1. Caption "You wrote" (after a re-check: "Your last checked version") and the sentence read-only.
   The "where" underline lives here, because a textarea cannot carry marks. Having the read-only
   copy and the field in one panel is the visible link between the sentence and its input.
2. A real `<label for>`: pencil icon + **"Rewrite your sentence"**. Never placeholder text.
3. Helper text: "Your sentence is already in the box. Change only the part you think is wrong, then
   press Check." Wired with `aria-describedby`.
4. The textarea: white on the tinted panel, 2 px border in `--field-border` (#5e7375 on white, above
   4.5:1; #93a6a4 on the dark surface), inset shadow, at least two lines tall, 18 px text. Focus:
   border plus a solid 3 px outline in `--focus`, offset 2 px (WCAG 2.4.7 / 2.4.11; replaces the
   translucent ring everywhere in the mockup).
5. Primary button **"Check"** ("Check again" after the first check), full width on phones. On
   pointer devices 700 px and wider, a hint beside it: `Enter` to check · `Shift` + `Enter` for a
   new line. Enter is ignored while an IME composition is open (§4).
6. A status line (`role="status"`), hidden when empty.

The hint-progress bar moved below the panel, captioned "Hints used", next to the hint buttons.

**Checking state.** On Check: the button is disabled and shows a spinner and "Checking…"; the field
becomes read-only with a dashed border; the status line reads "Checking your sentence. This takes a
second or two."; hint, answer and dispute controls are disabled; a second Enter or tap is ignored.
The spinner stops under `prefers-reduced-motion` and the text carries the state. If the call takes
longer than 5 s or fails, re-enable everything, keep the learner's text, and say "Couldn't check
just now — try again" (not in the mockup). The mockup simulates 1.1–1.8 s.

**Result states** (each has its own icon, text and border, not colour alone):

| Result | What the learner sees |
|---|---|
| Fixed | Card turns green-bordered, chip "✓ Fixed …", first try vs. now, explanation |
| No issue found | Blue-bordered card, chip "○ No issue found in your new version", the learner's version beside the original. Deliberately not green and not a tick. |
| Still flagged | Amber box under the button: "↻ Still flagged. Try once more, or take the next hint." with "Check 1 of 4" at the right; focus returns to the field |
| Nothing changed | Neutral box: "That's the same sentence. Change something, or take a hint." No call made. |
| 4th failed check | Answer shown with "This one's worth seeing rather than guessing." |

In production the status line should be updated in place so screen readers announce it; the mockup
re-renders the card, which is not a reliable test of the live region.

### 1.3 Encoding severity and confidence

> **Superseded by Revision 2 (layout only).** Chips and card colours are removed (R2.3). Severity only orders the steps; low confidence changes the wording of the step (R2.2).

- **(rev. 2026-11-14)** The figures in this section (severity 54–75%, "all 8 meaning inversions")
  are from the September jev run. Severity accuracy for GPT-6 Luna is not in the summary report
  read for this revision; on gold the DeepSeek config flagged 6 of 6 inversions as critical, and it
  also typed 3 other errors as `meaning_inversion`. The design rule is unchanged: severity orders
  the cards and is not shown. The type-confidence rule at the end of this section needs a
  confidence field that the chosen grader does not return; until then rung 2 shows the single
  returned subtype (top-1 type was right 77–80% of the time for GPT-6 Luna on gold).
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

> **Superseded by Revision 2 (layout only).** The states are now the screens in R2.2.

| State | Behaviour |
|---|---|
| **Clean item** | Success card: "Nothing flagged. The checker can miss small things, so the original is below if you want to compare." Reference behind one tap. No repair pass. |
| **Many errors** | Only 3 targets get ladders. The status line reads "3 to look at now · 4 more in the full comparison". If 5 or more sentences are flagged or any dimension would band at 1, skip the repair pass entirely and go to direct feedback: the passage was too hard and repair would be a slog. |
| **Unsure flag** | Dotted card, two buttons: "Compare with the original" (shows both, differing word marked, "Both can work here; the original uses the highlighted word") and "Leave it". Never counted. |
| **Learner disputes** | "I think mine is right" is on every open card. One tap: the original is shown with "Fair enough. Yours may be just as good. We've sent this flag for review and left it out of your progress." The flag is logged for grader QA and, if budget allows, re-judged by the live grader offline. No argument, no penalty. |
| **Learner gives up** | "Show the answer" is one tap at any rung, same visual weight as the other links, no confirmation. Recorded as `answer_shown` at the rung reached. |
| **Location unknown** | **(rev. 2026-11-14)** If the grader returns no span, or a span that is not a substring of the learner's sentence, rung 1 is removed and the bar shows three segments. Every re-check returns a fresh span for the revised text, so the underline follows the learner's edits; if a re-check returns none, the hint says the location can no longer be pinpointed. |
| **Adaptive start** | If a type's last 3 episodes all needed rung 1 or more, the card opens at rung 1 with a one-line reason. If the last 3 all ended in `answer_shown`, the type switches to direct mode until a review drill succeeds (§2.4). |

### 1.6 Copy (learner's L1)

> **Superseded by Revision 2 (layout only).** Chip and skip strings are no longer used. Current strings are in R2.2; zh and ja versions of the new strings are not written yet.

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

**(rev. 2026-11-14)** Changes to the table above: `type_prob` and `p_error` are null for the
generative grader; add `error_instance_id` (the id of the flagged error, shared with daily practice,
§8), `span_start` / `span_end` (character offsets in `first_text`, from the grader) and
`span_source` (`grader` / `none`); `location_available` is false when the grader gave no usable span.

**`dt_repair_event`** — append-only, one row per action. This is the audit trail, the input to the
daily-practice queue and the dataset for tuning. **(rev. 2026-11-14)** Fields:

| Field | Notes |
|---|---|
| `episode_id`, `error_instance_id`, `sentence_idx` | which error, which sentence |
| `surface` | `repair_pass` / `daily_practice` |
| `ts`, `kind` | `hint_shown` / `revision_checked` / `answer_shown` / `disputed` / `skipped` |
| `hint_level` | level reached when the event happened (0–4) |
| `text` | on `revision_checked` only: the learner's revised sentence |
| `result` | on `revision_checked`: `fixed` / `no_issue_found` / `still_flagged`, plus the returned subtype, severity, span offsets and short explanation if an error is still listed |
| `latency_ms`, `since_prev_ms` | grader latency; time since the learner's previous event |
| `hint_source`, `hint_template_id` | on `hint_shown`: `grader_span` / `template` / `model`; template id and version. Hint text is stored only when the source is `model`. |

Whether the learner disputed the flag is the `disputed` event plus `outcome` on the episode.
Storage budget: §8.5.

~~The mockup's summary card has a "What gets recorded" disclosure that prints the episode rows live.~~ Superseded by Revision 2: nothing about recording is shown in the flow; the mockup writes the event rows to `window.__events`.

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

**(rev. 2026-11-14)** The table below describes the jev grader and is superseded. The chosen grader
(`openai/gpt-6-luna`, single call, "span + explanation" prompt variant, strict JSON schema,
temperature 0) returns per error:

| Field | Use |
|---|---|
| sentence index | card ↔ L1 sentence |
| `subtype` (v6 taxonomy) | rung 2 name, clue template lookup, tracking |
| `severity` | ordering only |
| `span` in the learner's text | rung 1 "where"; underline in daily practice |
| `explanation` (short; the tested variant capped it at 15 words) | shown with the answer and on a fix |
| `grader_version` (model + prompt version) | audit |

Not returned: any probability, top-3 types, the narrow meaning checks as separate signals (a
meaning error arrives as a subtype such as `meaning_inversion`). The red "meaning differs" card
therefore keys on subtype.

Superseded jev table, kept for history:

| Field | Have today? | Use |
|---|---|---|
| `p_error` | yes | triage, pass/fail on re-check |
| `types`: top-3 with probabilities | top-1 yes; top-3 needs the pick-one probabilities exposed | rung 2, two-type fallback |
| `severity` + probability | yes (unreliable) | ordering only |
| narrow checks: negation, quantity, agent swap, omission, addition | yes | red "meaning differs" state; short ladder |
| sentence alignment index | yes | card ↔ L1 sentence |
| `grader_version` | — | audit |

### 5.2 Span offsets — from the grader (rev. 2026-11-14)

**Corrected.** The "where" hint uses the span the grader returns with each error, on the first grade
and on every re-check. Evidence (Track E): the diff was a small local edit for 46 of 49 errors on
near-copies, 31 of 49 at moderate and 12 of 40 at heavy paraphrase; the model's span was on the
planted error whenever it flagged the right sentence (24 of 24 for GPT-6 Luna, 27 of 27 for
DeepSeek). The limit is recall, not location. Validate in code: the span must be a non-empty
substring of the learner's sentence and cover at most about 40% of it; otherwise
`location_available = false` and rung 1 is dropped. The diff is no longer used to locate errors.
The mockup fakes a fresh span per re-check.

The original diff procedure, superseded:

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
| Where | grader span (rev. 2026-11-14) | 0 extra |
| What kind | taxonomy `name` per L1 (exists in v6), looked up from the returned subtype | 0 |
| Clue | new template per type x L1, about 60 per L2 x L1 pair incl. tier variants | 0 at runtime; one-off authoring + native review |
| Answer | reference + the explanation returned with the grade | 0 extra |

**(rev. 2026-11-14)** Hint text comes from templates, and Track D supports that: template hints
never leaked the answer (0% by judge) and were rated good 78% of the time; model-written hints
leaked in 9–40% of texts, and model-written rule statements broke the no-answer instruction in
22–66%. Explanations are the opposite case: the model's were good 91–94% of the time against 55%
for the rule template alone, so the explanation comes from the grade. A longer explanation from the
live Explainer prompt is an optional extra call (about $0.000183 per error-bearing submission with
GPT-6 Luna).

If a model-written hint is ever used, it must pass a leak filter in code before display, with the
template as the fallback: reject the text if it contains the reference's wording for the flagged
part, or any token of that part that is absent from the learner's sentence (after the same
normalisation used for matching, e.g. readings for Japanese), and cap its length. Track D's code
check agreed with the better judge at κ = 0.74. Templates were weak for types that cover several
different mistakes (`topic_comment`) and are AI-drafted and unreviewed.

### 5.4 Cost

**(rev. 2026-11-14) Recomputed** at $0.00006 per call (GPT-6 Luna measured $0.000051–0.000057 per
item with provider prompt caching; a re-check sends one sentence, not the item, so this is on the
high side for re-checks) and 1–2 s per call.

| | Calls | Arithmetic | Cost per passage |
|---|---|---|---|
| First grade | 1 | 1 × $0.00006 | $0.00006 |
| Repair, expected | ≈ 2.4 | 1.5 targets × 1.6 checks × $0.00006 | ≈ $0.000144 |
| Repair, worst case | 12 | 3 targets × 4 checks × $0.00006 | $0.00072 |
| **Total, expected** | ≈ 3.4 | $0.00006 + $0.000144 | **≈ $0.0002** |
| **Total, worst case** | 13 | $0.00006 + $0.00072 | **$0.00078** |

At 1,000 passages a day the repair pass costs about $0.14 expected (1,000 × $0.000144) and $0.72
worst case (1,000 × $0.00072); with the first grade, about $0.20 and $0.78. The previous figures
were $0.50 and $2.40 for the repair pass alone.

Daily practice (§8) adds, per learner per day: expected 3 items × 1.5 checks × $0.00006 ≈ $0.00027;
worst case 3 items × 3 checks × $0.00006 = $0.00054.

Qualifiers: the 1.5 targets, 1.6 checks and 1.5 daily checks are my assumptions, not measurements.
At low or bursty traffic the cache misses and list price applies ($0.00008–0.00025 per item), so
the worst case at list price is 13 × $0.00025 ≈ $0.0033 per passage. The live grader costs
$0.025–0.05 per item.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Flag is wrong.** Rare for "error present", but the learner is then asked to fix a correct sentence. | Dispute button on every card, no penalty; "may be fine" wording below 0.75; nothing below 0.75 gets a ladder; dispute rate per type monitored. |
| **Type is wrong** (5–31% of the time). Rungs 2–3 then mislead. | Two-type wording under 0.6, skipped under 0.4; clues phrased as questions, not assertions; rung 1 does not depend on type; the answer and comparison are type-independent. |
| **Valid alternative.** The revision is fine but differs from the reference. | Pass is decided by the grader, not by string match; outcome `repaired_alternative`, full credit; reference shown as "how the original puts it". |
| **False pass.** The revision is still wrong but the grader misses it. | "No issue found", never "correct"; reference always shown beside it. |
| **Revision introduces a new error elsewhere.** | Still flagged, so the card stays open; after 2 failed checks the copy points to the next hint; hard stop at 4. |
| **Location unavailable or wrong.** | Rung dropped when the grader's span fails validation (§5.2); a fresh span comes with every re-check. |
| **Slow or failed re-check** (1–2 s typical). | Checking state, double-submit guard, 5 s timeout with the learner's text preserved (§1.2a). |
| **Missed errors on rephrased text** (recall .72 at heavy paraphrase). | Same as the recall row below; the "free translations are expected" prompt paragraph is a separate product decision. |
| **Practice queue nags or grows without bound.** | Daily cap of 3, 30-day expiry, retirement after 3 unsuccessful sittings, disputes remove the item (§8). |
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

## 8. Daily-practice loop: "fix your own sentence" (rev. 2026-11-14)

Reached from the "Daily practice" link on the mockup's start screen (Revision 2; was a tab). Screen layout: R2.2. All numbers here are design defaults.

### 8.1 What gets queued

One queue entry per **error instance** (one flagged error in one sentence of one attempt), decided
when its repair episode closes:

| Episode outcome | Queued? |
|---|---|
| Fixed at hint level 0 (second look) or 1 ("where") | No. Treated as a slip, as in §2.4. |
| Fixed at level 2 or 3 ("what kind", "clue") | Yes |
| Answer shown (asked for, automatic after the 4th check, or via "Skip — show me everything") | Yes |
| Shown directly (not hintable, or over the cap of 3) | Yes, the learner saw the answer without an attempt |
| No issue found in the revision (`repaired_alternative`) | By the level reached, as for a fix |
| Disputed, unsure, dismissed | No |

Each entry keeps the hint level reached, so the queue can order by it.

### 8.2 When it resurfaces

- First due the next calendar day, and not sooner than 20 hours after the episode.
- At most 3 such items per daily session; the rest wait. Order: meaning-changing errors, then
  highest hint level reached, then oldest.
- Not served while the learner is on the same passage.
- Entries expire unresolved after 30 days.

### 8.3 The item

The learner sees the L1 prompt sentence, their own earlier sentence with the grader's span
underlined (the item opens at the "where" level, since by definition that hint was not enough or
was never the issue), and the same revision field as §1.2a, pre-filled with their earlier sentence.
"What kind", "clue" and the answer are available as before; the check cap is 3. Only the sentence
index, span and the learner's text are needed; the L1 and reference sentences are read from the test.

### 8.4 What counts as resolved

| Result in daily practice | Consequence |
|---|---|
| Fixed, or no issue found, with no hint beyond the underline | **Resolved.** Removed from the queue. Acknowledged on the card: then vs. now, the explanation, "Resolved — removed from your practice list. Last time you needed the answer. Today you fixed it yourself." and the count for that pattern. |
| Fixed with "what kind" or "clue" | Not yet resolved. Returns once after 3 days; an unaided fix then resolves it. |
| Answer shown, or 3 failed checks | Returns after 2 days, then 4, then 7. After 3 such sittings it is retired and the type goes to direct mode and the existing drills (§2.4). |
| Disputed | Removed, sent for review, not counted. |

"Fixed" is decided by the grader on the revised sentence, as in the repair pass, so a valid
alternative resolves the item. A resolved item is evidence about that sentence only; the per-type
state (§2.3) still moves on new passages.

### 8.5 What is recorded, and how much space it takes

Every attempt, in the repair pass and in daily practice, writes `dt_repair_event` rows (§2.1). Per
attempt that covers: error instance id, sentence index, surface, hint level reached, each revision
text, each re-check result, grader latency and time between events, whether the learner disputed
the flag, and which hints were shown with their source and template id. The mockup's "What gets
recorded" disclosures print these live.

The owner asked to "save as much as possible while considering the size limit". Recommendation:

- **Store:** every revision text; the structured result of every check (subtype, severity, span
  offsets, the short explanation, since it is model output and cannot be regenerated identically);
  every hint event as level + source + template id and version; timings; dispute; grader and
  prompt version ids.
- **Do not store:** the prompt sent to the grader; the raw model response; the L1 or reference
  sentence (join on test id and sentence index); the text of template hints (the id and version
  reproduce it); a revision identical to the previous one (no call is made for it).

Rough size, UTF-8, including about 60 bytes of row and index overhead per row. These are estimates:

| Row | Arithmetic | Size |
|---|---|---|
| Check event | 32 B ids and numbers + revision text 90–150 B (30–50 CJK characters at 3 B, or 80–120 Latin characters) + result with explanation 60–100 B + 60 B overhead | ≈ 0.3 KB |
| Hint event | 32 B + 8 B template id + 60 B overhead | ≈ 0.1 KB |
| Episode row | 120 B fields + first text ≈ 120 B + 60 B overhead | ≈ 0.3 KB |

Per episode, expected: 0.3 + 1.6 checks × 0.3 + 1 hint × 0.1 ≈ 0.9 KB. Per passage at 1.5 targets:
≈ 1.3 KB. At 1,000 passages a day: ≈ 1.3 MB a day, under 0.5 GB a year. Worst case per passage:
3 × (0.3 + 4 × 0.3 + 3 × 0.1) = 5.4 KB. Storing the prompt and raw response for each call would be
several KB per call (estimate), roughly ten times the above, which is why they are left out. The
applicable database limit was not checked for this revision.

## Related Pages
- [[evaluations/dt-decision-grading-2026-11-14]] — the experiment behind the 2026-11-14 revision
- [[features/dual-translation]] · [[features/dual-translation.tech]]
- [[features/dual-translation-remediation.tech]]
- [[decisions/ADR-031-dt-taxonomy-v6-merge]]
- [[evaluations/jev-dt-tuning-2026-09-27]]
- [[business-rules/translation-error-taxonomy]]
