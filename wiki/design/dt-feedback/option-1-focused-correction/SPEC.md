---
title: "DT Feedback — Option 1: Focused Correction"
type: feature
status: planned
last_updated: 2026-11-14
open_questions:
  - "OPEN: Can 'chances' (obligatory occasions) be detected deterministically from the reference for enough v6 types? Assumed yes for closed-class grammar types; untested."
  - "OPEN: This option makes the long explanation lazy (on tap). ADR-015 says explanations are eager. The one-line template is still eager; owner must accept the partial deviation."
  - "OPEN: All grader numbers come from seeded synthetic errors, n=30 per language. Thresholds below are starting values, not tuned."
---

# DT Feedback — Option 1: Focused Correction

One of three competing options. Mockup: `mockup.html` (same folder). Screenshots: `mobile.png`, `desktop.png`.

## Summary

After each Dual Translation submission the learner sees their own passage with **one** error promoted to a "Fix this first" card: their sentence, the original, a one-line reason in their L1, and an edit-and-check box. Everything else the checker found is collapsed behind one row. Across sessions the app tracks at most **three focus areas** (error types that recur), shown as a strip of the last ten chances to use that pattern, and retires each one when it stops recurring.

The option trades completeness for uptake. It shows less than the grader knows, on purpose, and it is built so that a wrong or unsure grader does little harm.

---

## (a) The feedback screen

### Layout, top to bottom

| Block | Content | Notes |
|---|---|---|
| 1. Outcome line | One sentence in words: "One part says the opposite of what you meant." / "We found nothing to fix." / "Nothing we are sure about. One spot is worth a second look." | Replaces the five-band wall. No overall band number. Bands stay in the data (see Deviations). |
| 2. Fix-first card | Pill "1 · Fix this first" (+ "Changes the meaning" when it applies). Three rows: **You wrote** (only this error marked), **Original** (corrected part marked), **Meaning** (L1 reference sentence). One-line reason. "Why?" link. **Next step**: the learner's sentence prefilled in an editable box + Check. "I think mine is right" link. | Exactly one per passage, or none. |
| 3. Your whole passage | Every sentence numbered, in the learner's own words. By default only the fix-first mark and "different, also fine" marks are drawn. Per sentence: "Show original", "I see a mistake here". | The noticing surface. The original is one tap away for every sentence, always. |
| 4. Collapsed row | "2 smaller things in this passage. Optional. They are saved either way. One is in your focus area を・に・が." | Expanding draws the thin marks and opens a short note for each. |
| 5. Next passage | Primary button. | Never blocked by the retype step. |
| 6. Focus areas | Side rail on desktop, below the button on phones. Up to three areas, each with status and the last-ten strip; this passage's result is ringed. | Links to the progress view. |

### Choosing the one fix-first error

Score every flagged error and take the highest. Only errors with detection confidence at or above the "confident" cutoff are eligible.

1. **Meaning-changing first.** `meaning_inversion`, or any error where a narrow check (negation reversed, quantity changed, who-does-what swapped) fires with high probability. This is the grader's most dependable severity signal: 8 of 8 inversions caught as critical in en.
2. **Then an error in an active focus area**, if its type confidence is high.
3. **Then a treatable type** (taxonomy `treatable = true`: rule-governed, so a one-line rule can help) over an untreatable one.
4. **Then by the taxonomy's default severity** for the type. The grader's own minor/major call is used only as a tiebreak, because it is the least reliable field (54–75% right, and human raters agreed only 62–85%).

Session cap: after three fix-first cards with a retype in one session, later passages still show a fix-first card but the retype box is offered as a link, not opened. (Starting value; test it.)

### What a mark means

Shape carries the meaning. Colour only reinforces it.

| Mark | Drawn as | Meaning | When |
|---|---|---|---|
| Fix first | 3px solid underline + tint + superscript **1** | The one thing to fix | Confident detection, top priority |
| Smaller | 1.5px solid underline + superscript **+** | Also found | Confident detection, shown on expand |
| Not sure | Dotted underline + superscript **?** | The checker is unsure | Detection or type confidence below cutoff |
| Different, also fine | Dashed underline + superscript **✓** | Differs from the original and is correct | Deterministic diff differs, no error detected |
| Missing word | Caret **⌃** + superscript | Something is absent here | Omission |
| Corrected form (original row) | 3px teal underline + tint | What the original has | Fix-first card and opened originals |

**Severity is not shown as a label**, except "Changes the meaning". There are no minor/major/critical chips. Severity drives ordering only.

**Confidence is shown as two states, never a number.** Confident: declarative copy ("You wrote X. The reference says Y."). Unsure: question copy ("yours may be fine here"), both forms shown side by side with no strike-through, and the next step is a choice ("Mine works too" / "I would change it"), not a correction. An unsure error is never the subject of a retype.

Mark spans are narrowed to the characters that actually differ inside the grader's span (簡単, not もっと簡単な), by a character diff between `learner_form` and `corrected_form`.

### States

| State | What the learner sees | Mockup tab |
|---|---|---|
| **Many errors** | One fix-first (the meaning-changing one), the rest collapsed, with a count. A focus-area error that is not the fix-first is still counted in tracking and named in the collapsed row. | Many errors · ja (`ja_multi_04`) |
| **One ordinary error / missing word** | Fix-first with a template reason; "Why?" loads the longer reason on tap. | Focus area · en / 中文 (`en_multi_02`) |
| **Clean item** | "We found nothing to fix." Never "Perfect" or "100%". Harmless differences are marked "different, also fine" with a reason. If a focus area had chances in the passage and all matched, say so. A standing line says the checker can miss small things and invites comparing with the original. | Clean item · ja (`ja_clean_02`) |
| **Checker unsure** | Card is titled "Worth a second look", blue-dotted, phrased as a question. The learner decides. "Mine works too" records nothing as an error. | Checker unsure · zh (`zh_seed_06`) |
| **Learner disputes a flag** | "I think mine is right" withdraws the card at once: "Removed. This will not count toward your focus areas, and a person will review it." Undo available. | Any fix-first card |
| **Learner reports a miss** | "I see a mistake here" on any sentence opens a one-field note ("What should it have been?"). Saved as a self-noticed error. | Any sentence |
| **Grading failed / budget exceeded** | Outcome line: "We could not check this one. Here is the original to compare." All originals open. Nothing recorded. | Not in mockup |
| **Exact match** | Clean state without the "can miss small things" line (a deterministic match is certain). | Not in mockup |

### Copy examples (learner's L1)

English L1:
- Outcome: "One part says the opposite of what you meant. Start there. The rest of your passage reads clearly."
- Reason (meaning): "You wrote 簡単 (simple). The reference says more **complex** robots: 複雑."
- Reason (rule, template): "The thing being moved takes を with 動かす."
- Unsure: "You wrote 轻松 where the original has 放松. These two are close in meaning, and yours may be fine here."
- Clean: "We found nothing to fix. Your meaning matches the original all the way through."
- Variant: "Same word, written in kana instead of kanji. Both are correct."
- Retype success / retry: "That matches the original now." / "Not yet. Look at the marked part once more."

Chinese L1 (as in the mockup's English-L2 scene):
- 结果：「有一句话少了一个词。先改这一处。其他地方意思都清楚。」
- 原因（模板）：「原文在 the arm 后面还有一个词：move。你的句子里没有。」
- 下一步：「改一改你的句子，让它和原文意思一致。」
- 异议：「我觉得我写的没错」→「已撤回。这一处不会计入你的重点项，我们会人工复核。」

Japanese L1 (not in mockup):
- 「まず、ここを直しましょう」「原文では "with" です。"without" だと意味が逆になります。」「見つかった間違いはありません。」「自分の文のほうも正しいと思う」

Tone rules: say what was written and what the original has; no "wrong", "error", "incorrect" in learner copy; no exclamation marks; no praise for the person, only statements about the text; unsure states use "may", "not sure", and hand over the decision.

---

## (b) Tracking model

### What is recorded

**Per flagged error** (extends `dt_error_instance`):

| Field | Purpose |
|---|---|
| `submission_id`, `sentence_index` | Location |
| `span_reproduction`, `span_reference`, `learner_form`, `corrected_form` | Marks, retype check, later cards |
| `subtype` (v6), `subtype_top3` with probabilities | Type, and family fallback when top-1 is weak |
| `p_error`, `narrow_checks{negation, quantity, agent, omitted, added}` | Confidence tier, meaning-change flag |
| `severity_default` (taxonomy), `severity_model` | Ordering only |
| `confidence_tier` | `confident` \| `unsure`, frozen at grading time with the cutoff version |
| `display_role` | `fix_first` \| `collapsed` \| `unsure` \| `variant` |
| `was_seen` | false if it stayed collapsed |
| `learner_response` | `none` \| `retyped_ok` \| `retyped_fail` \| `skipped` \| `disputed` \| `agreed_change` \| `kept_mine` |
| `explain_opened` | Was "Why?" tapped |
| `counts_toward_focus` | Derived: confident, not disputed, not `kept_mine` |

**Per chance** (new, `dt_opportunity`): one row each time a tracked pattern was *required by the reference sentence*, whether or not the learner got it right.

| Field | Purpose |
|---|---|
| `user_id`, `submission_id`, `sentence_index`, `subtype` (or family) | Key |
| `outcome` | `matched` (learner's text agrees with the reference at that point) \| `flagged` (confident error of that type there) \| `unsure` (differs, checker not confident) |
| `created_at` | Day spacing |

Chances are found without a model: closed-class patterns are located in the reference by rule (を/に/が after a noun, です/ます endings, 了/过 after verbs, 的/得/地, measure words, English articles, third-person -s, plural after quantifiers). `matched` comes from the existing token diff. This is the classic obligatory-occasion count. Open-class types (word choice, omission, collocation) have no detectable chance; for those the unit is the passage ("flagged in this passage or not").

**Per learner report**: `dt_self_report(submission_id, sentence_index, note_text, created_at)`.

**Per dispute**: `dt_dispute(error_instance_id, created_at, review_status)`. Feeds grader QA and the gold set.

### Becoming a focus area

- A type becomes a **candidate** when it has a confident, undisputed flag in **two different passages within 14 days**. Two is enough because precision is about 1.0; the risk is the label, not the detection.
- If top-1 type probability is below the type cutoff, the flag counts toward the type's **family** instead (ja particles; verb forms; zh aspect and complements; en determiners; word choice; meaning; register). A family can become a focus area under its family name when no single type inside it qualifies. This is how a 69–75% type label degrades without mislabelling.
- At most **three** active focus areas. If more qualify, rank by (meaning-changing > treatable > flags per chance). The rest wait in "Seen once or twice".
- Learners can pause an area, or pin one themselves.

### Status

| Status | Rule (starting values) | Learner-facing |
|---|---|---|
| Working on it | Active; fewer than 8 of the last 10 chances matched | Apricot pill |
| Fading | 8+ of the last 10 matched | Blue pill; says what is left ("2 more passages on different days") |
| Resolved | 8+ consecutive `matched` chances spread over 3+ different days, and at least one successful retype or card review for the type | Green pill with date; moves to Resolved |
| Reopened | 2 confident flags after resolution | Returns to Working, no alarm |

`unsure` chances are drawn but do not count either way. Maps onto the existing `dt_error_profile_entry.remediation_status` (`queued` → Working, `drilling` → Fading, `resolved` → Resolved); only the rules and the chance table are new.

### What the learner sees over days and weeks

- **The strip.** Up to ten marks per area, oldest left: filled circle = came out right, slashed square = flagged, dotted ring = checker unsure. No percentage. A caption in words ("6 of the last 10 chances came out right").
- **This-week line.** Passages done, fix-firsts corrected, areas resolved. Effort and outcomes the learner controls.
- **Resolved list**, with date and the evidence ("came out right 9 times across 4 days").
- **Seen once or twice**, collapsed. Includes the learner's own notes.
- A standing sentence: "The checker reliably catches the mistakes that matter but misses some small ones, so read these strips as a trend, not an exact count."

### Where it surfaces

1. **Before writing** (feed-up): the existing "What you'll be graded on" card gains one line, "While you write, watch for: を・に・が", naming one active focus area that has chances in this passage.
2. **Result screen**: focus-area pill on matching errors; the rail with this passage's result ringed.
3. **Progress view**: replaces "My Error Profile" at `/dual-translation/profile`.
4. **Practice queue**: `GET /api/dual-translation/next` already interleaves remediation cards; it should prefer cards from active focus areas.
5. **Study plan weekly summary**: one line when an area is resolved.

---

## (c) Pedagogy rationale

Verification key: **[V]** = bibliographic details and the stated finding were checked by web search for this spec (secondary summaries or abstracts, not full text). **[M]** = well-known source cited from memory; details not re-checked this session. Treat [M] items as unverified until someone opens the paper.

| Design decision | Evidence | How strong |
|---|---|---|
| **One error promoted, the rest collapsed** | Focused WCF produced durable accuracy gains in several controlled studies: Sheen (2007), "The effect of focused written corrective feedback and language aptitude on ESL learners' acquisition of articles", *TESOL Quarterly* 41(2) [V, bibliographic; finding M]; Bitchener & Knoch (2010), "Raising the linguistic accuracy level of advanced L2 writers with written corrective feedback", *J. Second Language Writing* 19(4) [V, bibliographic; finding M]; Sheen, Wright & Moldawa (2009), "Differential effects of focused and unfocused written correction…", *System* 37(4) [V, bibliographic; findings not retrieved]. Lee (2019), "Teacher written corrective feedback: Less is more", *Language Teaching* 52(4), argues the position directly [V]. | **Mixed, and this must be said.** Ellis, Sheen, Murakami & Takashima (2008), *System* 36(3), found **no difference** between focused and unfocused feedback [V]. Van Beuningen, De Jong & Kuiken (2012), "Evidence on the effectiveness of comprehensive error correction…", *Language Learning* 62(1), found comprehensive correction **works** [V]. Kang & Han's (2015) meta-analysis, *Modern Language Journal* 99(1), found WCF helps overall (small to moderate) and focused was higher than unfocused **but not significantly** [V]. Mao & Lee (2020), *Assessing Writing* 45, review the scope question and call it unresolved [V]. Most focused studies targeted one pre-chosen structure (English articles) for a whole class; this design chooses per learner, per passage, which those studies did not test. |
| **Collapse, do not delete** | Because the focused-vs-comprehensive evidence is mixed, the full set stays one tap away and is tracked either way. The claim being made is about attention and load at the moment of feedback, not that the other errors do not matter. | Design judgement. |
| **Low element count on screen** | Cognitive load theory: Sweller (1988), "Cognitive load during problem solving: Effects on learning", *Cognitive Science* 12 [M]. A learner reading feedback in L1 about L2 text, with CJK script, is already holding a lot. | The theory is established; its application to feedback layout is by analogy. |
| **Feedback can hurt, so less and more targeted** | Kluger & DeNisi (1996), *Psychological Bulletin* 119: feedback helped on average (d = .41) but over a third of interventions **lowered** performance [V]. Their account is that feedback which pulls attention to the self instead of the task is the kind that harms [M]. | Strong for "feedback is not automatically good". |
| **Outcome line, reason, next step** | Hattie & Timperley (2007), "The Power of Feedback", *Review of Educational Research* 77(1): effective feedback answers where am I going, how am I going, where to next, and works best at task and process level, worst when aimed at the self [V, bibliographic; model details M]. Feed-up = the "watch for" line; feed-back = the fix-first card; feed-forward = the retype and the focus area. No person-praise in copy. | Strong, general education. |
| **Learner's sentence next to the original, difference marked** | Noticing hypothesis: Schmidt (1990), "The role of consciousness in second language learning", *Applied Linguistics* 11(2) [M]. Learners must notice the gap between their output and the target. The paired rows are a noticing-the-gap device. | Influential; the strong form (no learning without noticing) is disputed. |
| **Show the correct form outright (direct), plus one line of reason** | Shintani, Ellis & Suzuki (2014), *Language Learning* 64(1): direct correction lasted longer than metalinguistic explanation, and **direct correction followed by revision was the most effective** condition; feedback helped the hypothetical conditional but **not** the indefinite article [V]. Ferris & Roberts (2001), *J. Second Language Writing* 10 [M], on how explicit feedback needs to be. In this app direct correction is also free: the reference is the correction. | Moderate. The article null result is a caution that some forms resist feedback. |
| **Edit-and-check as the next step** | Same Shintani et al. (2014) revision result [V]. Output hypothesis: Swain (1985, 1995) [M]. Also the existing A/B seam in `dual_translation.html` (`data-correction-style`) already anticipates testing this. | Moderate. |
| **Only rule-governed errors get a rule sentence** | Ferris (1999), "The case for grammar correction in L2 writing classes: A response to Truscott (1996)", *J. Second Language Writing* 8 [M]: treatable vs untreatable errors. The v6 taxonomy already carries `treatable`. | Widely used distinction; modest direct evidence. |
| **The Truscott objection** | Truscott (1996), "The case against grammar correction in L2 writing classes", *Language Learning* 46(2) [M]: correction is ineffective and can make learners avoid complex forms. Later controlled studies and Kang & Han (2015) answer the "ineffective" claim for accuracy on new writing; the **avoidance** worry is not answered by them. | Unresolved. Mitigations here: no score penalty on screen, "different, also fine" marks to reward risk, clean state that never says "perfect". Range cannot be measured by the grader, so avoidance cannot be detected by this design. |
| **Three focus areas, visible resolution, learner can pause/pin/dispute** | Self-regulated learning: Zimmerman (2002), "Becoming a self-regulated learner: An overview", *Theory Into Practice* 41(2) [M]: goal setting, self-monitoring, self-evaluation. | Strong general framework; no DT-specific evidence. |
| **Count chances, not just errors** | Obligatory-occasion analysis from morpheme-order research (Brown 1973; Pica 1983) [M]. An error count falls when a learner avoids a form; a per-chance count does not. | Standard method. |
| **Learner can report a miss** | Self-noticing is the target skill (Schmidt 1990 [M]). Also turns the grader's low recall into a learner activity. | Design judgement. |
| **Do not over-penalise non-native but clear output** | Munro & Derwing, already adopted in [[features/dual-translation]] [M]. | Consistent with existing wiki. |

---

## (d) Design rationale

**Hierarchy.** One card has a coloured border and it is the fix-first card. Everything else is the app's plain surface card. Reading order equals priority order: outcome, fix, whole passage, optional extras, next. The primary button is always "Next passage", so feedback is never a gate.

**Colour is never the only signal (WCAG 2.2 SC 1.4.1).** Every state differs by underline style (thick solid, thin solid, dotted, dashed), by a superscript character (1, +, ?, ✓), and by a text label in the legend and in `aria-label`. Progress marks differ by shape (circle, slashed square, dotted ring). Text colours use the app's AA-safe tokens (`--apricot-text` #a35417 on white, teal #0e7569 at 5.6:1) for SC 1.4.3. Red is not used: the app's danger colour would read as judgement, and red/green is the common colour-vision confusion pair. Marks are real `<button>`s with focus rings; touch targets on controls are 44px or more (SC 2.5.8 asks for 24px).

**CJK typography.**
- `lang` on every L2 run so the browser picks the right Han glyphs (ja and zh share code points with different shapes) and the app's per-language font stacks apply.
- Line height 2.0 for ja/zh L2 text (1.75 for en) so a 3px underline plus superscript never touches the next line.
- Underlines via `text-decoration` with `text-underline-offset`, not borders or boxes, so marks wrap correctly mid-phrase with `box-decoration-break: clone`. No italics (meaningless in CJK), no letter-spacing on CJK labels.
- `line-break: strict` to keep kinsoku rules (no line starting with 。、」).
- Marks cover one or two characters in CJK, so the thick underline and tint are needed for the fix-first mark to be findable; a thin underline under a single kana is easy to miss, which suits the collapsed tier.
- Superscript digits are set in the sans face at .62em so they do not read as ruby.
- The retype box is **prefilled** with the learner's sentence. Retyping a 60-character Japanese sentence through an IME on a phone is slow and error-prone, and would bury the one change in transcription effort.

**Mobile.** Single column at 390px; the three label rows of the fix card stack; the rail drops below the Next button. The fix-first card repeats one sentence that also appears in the passage list; this costs scroll on a phone and is accepted so the passage always reads whole.

**Themes.** Tokens follow the app's default and Midnight themes.

**Fit with the existing app.** Same 760px column, card radius, label style, teal primary, apricot accent, and the existing "Points to notice" / "next focus" ideas from TASK-631. Removed from the default view: overall band, five dimension tiles, severity chips.

---

## (e) Data needed from the grader, and cost

### Fields per sentence pair

| Field | Have it today (jev step-by-step)? | Used for |
|---|---|---|
| `p_error` | Yes | Confident / unsure tier |
| `subtype` top-3 with probabilities | Yes (pick-one with probabilities) | Type, family fallback |
| Five narrow checks with probabilities | Yes | "Changes the meaning", fix-first priority |
| `severity` | Yes, weak | Tiebreak only |
| Error span in learner text and reference | **No**: jev answers per sentence. Derive from the deterministic token diff inside that sentence. | Marks |
| `learner_form`, `corrected_form` | Derived from the diff | Card, retype check |
| Which diff hunk an error belongs to, when a sentence has several | **Gap.** jev gives one type per sentence. | Multi-error sentences |
| Chance detection per tracked type | **New, rule-based, no model** | Tracking |

**The multi-error gap matters.** `ja_multi_04` sentence 2 has two errors of different types; one call per sentence returns one type. Two ways to close it: (i) one extra jev call per additional diff hunk in a flagged sentence (cheap, same model), or (ii) show the sentence's one typed error and mark other hunks "not sure". The design works with (ii); (i) is better.

### Cost

Baseline from [[evaluations/jev-dt-tuning-2026-09-27]]: jev grading is $0.00013–0.00023 per item; the live grader is about $0.025–0.058.

| Tier | What it buys | Extra cost per item |
|---|---|---|
| **Template only** (this option's default) | One-line reason from per-type × per-L1 templates with `{learner_form}` / `{corrected_form}` slots. These templates already exist in `dt_taxonomy_version`. | $0 |
| **Per-hunk typing** for multi-error sentences | Correct type on each mark | About one more jev call per extra hunk: roughly +$0.00005 on items that need it (estimate) |
| **"Why?" on tap** | 1–2 sentence reason for *this* sentence, for the fix-first error only, generated when tapped and cached per (passage, learner_form, corrected_form) | One flash-class call of roughly 400 tokens in, 80 out. At typical flash pricing that is on the order of $0.0001 (estimate; depends on slug). Paid only on taps. |
| Eager LLM reason for every error (not this option) | What ADR-015 describes | About 2–3 such calls per erroneous item |

If a third of items have a fix-first and a third of those get a "Why?" tap, the blended extra is about $0.00001 per item. Even with "Why?" generated eagerly for every fix-first, the total stays near $0.0003 per item, around 100× below the live grader. These are estimates, not measurements.

Templates carry the load only for rule-governed types. For `word_choice`, `collocation`, `semantic_anomaly` and `meaning_inversion` the template can only state the two forms and their glosses; the gloss lookup needs the sense dictionary or the on-tap call.

### Deviations from current decisions (owner must accept)

- **ADR-015 (eager explanations):** the one-line reason stays eager; the longer reason becomes on-demand.
- **Bands:** still computed and stored; removed from the default screen. Naturalness and range are not shown at all, since the cheap grader cannot score them.
- **Promotion threshold:** two passages in 14 days, replacing "recurs ≥ N" with a concrete N.

---

## (f) Risks and how the design absorbs grader errors

| Failure | Likelihood | What the learner experiences | Mitigation |
|---|---|---|---|
| **False positive: a correct sentence is flagged** | Low (precision .95–1.0 on synthetic data; unknown on real learners) | A fix-first card for something that was fine | Only confident detections can be fix-first; the original is shown, so the learner can judge; "I think mine is right" withdraws it at once and it never counts; disputes go to review. Dispute rate per type is an alarm metric. |
| **Wrong error type** (5–31%) | Common in ja/zh | A rule sentence that does not fit | The card leads with the two forms, which are from the diff and always right; the rule line is secondary. Low type confidence drops to family naming or to no rule line. Focus areas need two passages. |
| **Wrong severity** | Common | Wrong thing promoted | Severity is not displayed. Priority rests on narrow checks and taxonomy defaults. Worst case: a real but lesser error is fixed first. |
| **Missed error (recall ~50% zh/ja)** | Very common for small errors | "Nothing to fix" on a passage with a slip | Copy never says perfect; standing honesty line; originals one tap away; "I see a mistake here"; tracking counts chances via the diff, so a missed error shows as "unsure", not as "came out right". |
| **Missed error makes an area look resolved** | Real risk | Premature "Resolved" | `matched` requires the learner's text to agree with the reference at the chance, which is deterministic. Resolution needs 3 different days. Reopening is quiet. |
| **Acceptable paraphrase differs from the reference** | Common | Could look like an error | Not flagged unless the model detects an error; shown as "different, also fine" or not at all. A paraphrase at a chance point is `unsure`, not `flagged`. |
| **Focusing hides errors the learner needed** | Inherent to the option | Slower fix of non-priority errors | They are tracked while collapsed and can become a focus area; the collapsed row names focus-area hits. |
| **Learners never expand, never open originals** | Likely for some | Shallow engagement | Acceptable by design; measured (see g). |
| **Prefilled retype becomes a copy exercise** | Likely | Low-effort fix | Delayed re-translation cards from the existing remediation pipeline carry the retrieval load; test prefilled vs blank. |
| **Avoidance (Truscott)** | Unknown | Learner writes safer sentences | Cannot be measured without a range signal. Track reproduction length and lexical variety as proxies. |
| **Three areas too few for advanced learners / too many for beginners** | Unknown | Stale or crowded list | Cap is a config value; pause and pin. |

---

## (g) What to A/B test

**Primary experiment: focused vs full.** Arm A: this option. Arm B: the current result screen (all errors listed, bands shown).

- **Primary metric: same-type recurrence per chance.** For each learner and each type flagged in weeks 1–2, the share of chances in weeks 3–6 that are `flagged`. Lower is better. Computed identically in both arms from the same grader, so grader bias cancels; chance-based, so avoidance does not flatter it.
- **Guardrails:** passages completed per week and 4-week retention (must not drop); mean reproduction length and type/token ratio (avoidance proxy; must not drop); dispute rate; share of learners with zero interactions on the result screen.
- **Secondary:** retype success rate; "Why?" tap rate (sizes the LLM cost); expand rate of the collapsed row; time on result screen.
- **Unit and size:** randomise by user. The effect in the literature is small to moderate (Kang & Han 2015), and scope effects are smaller than that, so expect to need hundreds of active learners per arm per language for six weeks. With fewer, report it as a pilot.

**Follow-up tests inside the option**, in order of value:
1. Retype box: prefilled-and-edit vs blank vs none (tests the revision effect against friction).
2. "Why?": on tap vs always shown (tests ADR-015's eager assumption directly).
3. Focus-area cap: 1 vs 3.
4. Pre-task "watch for" line: on vs off.

**Before any A/B:** run the cheap grader in shadow on real submissions (recommendation 1 of the jev report). Every threshold in this spec is set from synthetic errors.

---

## Related Pages
- [[features/dual-translation]], [[features/dual-translation.tech]], [[features/dual-translation-remediation.tech]]
- [[decisions/ADR-031-dt-taxonomy-v6-merge]], [[decisions/ADR-015-eager-error-explanations]]
- [[evaluations/jev-dt-tuning-2026-09-27]]
- Gold items used in the mockup: `tests/fixtures/dt_gold/` — `ja_multi_04`, `en_multi_02`, `ja_clean_02`, `zh_seed_06`. L1 lines, confidence tiers and learner history in the mockup are illustrative.
