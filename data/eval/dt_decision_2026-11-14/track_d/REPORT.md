# Track D — DT feedback generation: quality vs cost (2026-11-14)

**Question.** Given an already-detected error (type, severity, learner span, reference fragment), what is the cheapest way to produce feedback a learner can learn from?

**Short answer.**

1. **Direct corrections and elicitation hints do not need an LLM.** Hand-written templates (G0, $0, 0 ms) match the LLMs on direct corrections (96% "good" vs 91–96%) and are within noise on hints (78% vs 64/80/91%), with zero answer leaks — while the LLM hints leak the answer 9–40% of the time.
2. **Explanations do need an LLM.** A static rule template is true but generic: G0 metalinguistic text scored 20% "good" (specificity 0.68/2), and the live v6 Rule template alone 55%. The live Explainer prompt run on `deepseek/deepseek-v4.1-flash` or `openai/gpt-6-luna` scored 94% / 91% with no upheld factual errors, at **$0.00005 / $0.00011 per error-bearing submission**.
3. **`qwen/qwen3.7-flash` is the cheapest ($0.00003) and the least safe**: 6 upheld wrong texts in 269 (2.2%), including an invented fix on a clean item and two false statements about Japanese grammar. Not recommended for learner-facing prose.
4. **"No-answer" styles are not reliably no-answer from any LLM.** The "must not reveal the correction" instruction was broken in 22–66% of metalinguistic texts. Any hint/meta text from an LLM needs a code-level leak filter with the template as fallback.
5. **Clean items: use a template.** The fixed clean message was rated 9/9 good; one of 9 qwen summaries invented a correction.
6. Cost is not the deciding factor. The whole feedback layer costs $0.00005–0.00012 per submission, i.e. 25–60% of the ~$0.0002 jev detection call. The mix should be chosen on risk and latency.

**Negative results, stated plainly.** Template metalinguistic explanations are not good enough for any error type. The two LLM judges barely agree on what is factually wrong (κ = 0.08), so the hallucination rates below rest on my manual adjudication of 39 flagged texts, not on the panel. Per-type conclusions rest on n = 1–7 errors per type. Nothing here was checked by a native speaker.

Spend: **$0.2164** of the $0.55 budget (657 paid calls; guard at $0.50 never triggered).

---

## 1. Setup

| | |
|---|---|
| Items | 45 from `tests/fixtures/dt_gold_v6/` — 15 per L2 (3 clean, 7 single, 5 multi), singles picked for subtype coverage. 56 gold errors, 26 v6 subtypes. |
| Input to every generator | Gold annotation only (learner_form, corrected_form, v6 subtype + gloss, severity, word_choice variant) plus the passage pair. Detection quality is held constant. |
| Learner L1 | zh-L2 and ja-L2 items → L1 English. en-L2 items → alternating L1 Chinese / Japanese (8 / 7 items). The gold set carries no L1, so this is an assignment, not data. |
| G0 | Templates written for this experiment: `g0_templates.py` → `templates.json`. All 40 v6 slugs in English; the 20 English-L2 slugs also in zh and ja. AI-drafted, not native-reviewed. |
| G0live | The live v6 Rule template (`dt_taxonomy_v6_seed.sql` → `templates` / `variant_templates`) — what production shows when the Explainer is silent. |
| G1 / G2 / G3 | `qwen/qwen3.7-flash` ($0.03/$0.13 per M), `deepseek/deepseek-v4.1-flash` ($0.051/$0.203), `openai/gpt-6-luna` ($0.10/$0.50). Temperature 0, reasoning disabled (0 reasoning tokens billed), one call per item per style. |
| Styles | **direct** ("X → Y"), **meta** (rule, ≤25 words, no answer), **hint** (elicitation question, no answer), **app** (the live Explainer prompt from `services/dual_translation/prompts.py`, verbatim — 1–2 sentences, answer allowed), **summary** (1–2 sentences per item: one strength + the most important fix). |
| Judges | J1 `anthropic/claude-haiku-5.5`, J2 `google/gemini-3.6-flash`. One call per item; every text for that item shown under an opaque id, order shuffled within each error, generator hidden, gold annotation and annotator note visible. Scales 0–2: correctness **c**, specificity, clarity, tone, usefulness; leak 0/1. |
| Code-side metrics | Length; over-limit flag; deterministic leak check (the corrected fragment, after stripping the prefix/suffix shared with the learner form, appears in the text). |
| Volume | 1,076 feedback texts (5 omitted by G2, see §6), 1,050 rated by both judges. |

"**good**" below = both judges gave c = 2, usefulness ≥ 1 and clarity ≥ 1.

## 2. Results by generator and style

| Generator / style | n | c (0–2) | specific | clear | useful | **good** | leak (J2 / code) | median length | over 25-word limit | $ per item | p50 / p90 latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G0 direct | 56 | 1.97 | 1.98 | 1.94 | 1.76 | **96%** | n/a | 5 | – | 0 | 0 |
| G1 direct | 56 | 1.96 | 1.97 | 2.00 | 1.75 | 91% | n/a | 9 | – | $0.000021 | 1.5 / 1.9 s |
| G2 direct | 56 | 1.98 | 1.98 | 1.98 | 1.78 | 96% | n/a | 8 | – | $0.000031 | 1.7 / 2.6 s |
| G3 direct | 56 | 1.98 | 1.98 | 1.99 | 1.79 | 96% | n/a | 5 | – | $0.000069 | 1.3 / 2.4 s |
| G0 meta | 56 | 1.38 | 0.68 | 1.76 | 0.89 | **20%** | 2% / 30%* | 24 | 16% | 0 | 0 |
| G1 meta | 56 | 1.78 | 1.84 | 1.98 | 1.46 | 51% | **66% / 65%** | 26 | 26% | $0.000025 | 1.7 / 2.4 s |
| G2 meta | 56 | 1.92 | 1.94 | 1.89 | 1.75 | 76% | 36% / 31% | 44 | **91%** | $0.000041 | 1.6 / 2.2 s |
| G3 meta | 56 | 1.91 | 1.89 | 1.97 | 1.79 | 82% | 22% / 29% | 27 | 40% | $0.000088 | 1.6 / 2.4 s |
| G0 hint | 56 | 1.87 | 1.86 | 1.94 | 1.78 | **78%** | **0% / 6%*** | 21 | 20% | 0 | 0 |
| G1 hint | 56 | 1.84 | 1.91 | 1.97 | 1.62 | 64% | 34% / 23% | 18 | 4% | $0.000023 | 1.7 / 2.2 s |
| G2 hint | 56 | 1.94 | 1.97 | 1.93 | 1.73 | 80% | 40% / 14% | 32 | 73% | $0.000037 | 1.7 / 2.4 s |
| G3 hint | 56 | 1.96 | 1.92 | 1.99 | 1.84 | **91%** | 9% / 4% | 16 | 6% | $0.000077 | 1.5 / 1.8 s |
| G0live rule (prod today) | 56 | 1.66 | 1.70 | 1.66 | 1.53 | 55% | n/a | 50 | – | 0 | 0 |
| G1 app | 56 | 1.93 | 1.99 | 1.93 | 1.94 | 89% | n/a | 39 | – | $0.000033 | 2.1 / 3.2 s |
| G2 app | 51 (+5 omitted) | 1.99 | 2.00 | 1.88 | 1.97 | **94%** | n/a | 43.5 | – | $0.000050 | 2.1 / 2.7 s |
| G3 app | 56 | 1.96 | 2.00 | 1.95 | 1.96 | **91%** | n/a | 31 | – | $0.000114 | 1.8 / 2.8 s |
| G0 summary | 45 | 1.77 | 1.76 | 1.88 | 1.64 | 68% | – | 20.5 | – | 0 | 0 |
| G1 summary | 45 | 1.71 | 1.78 | 1.93 | 1.67 | 61% | – | 19.5 | – | $0.000018 | 1.2 / 1.5 s |
| G2 summary | 45 | 1.85 | 1.98 | 1.94 | 1.88 | 77% | – | 33.5 | – | $0.000028 | 1.4 / 2.0 s |
| G3 summary | 45 | 1.84 | 1.91 | 1.96 | 1.83 | 80% | – | 23.5 | – | $0.000070 | 1.3 / 1.8 s |

Tone was 1.96–2.00 everywhere and does not discriminate. Length is in words for English output and characters for zh/ja output, so the median mixes the two; the over-limit column applies the right limit per language (25 words / 50 characters).

\* The code check over-counts leaks for templates on closed-class types: a rule that lists "的 / 地 / 得" or "a/an, the" necessarily contains the answer among the options. J2 is the better leak figure for meta. J1's leak ratings are unusable (it marked only 14–22% of `app` texts as containing the answer although 85–96% literally do) and are omitted.

**Reading the table.**

- **Direct:** all four are equivalent. The LLM adds 0–8 words ("Remove '过'", "use 得 before complement") that the judges did not value. Pay nothing.
- **Hint:** the template is as good as two of the three LLMs and is the only generator that never gives the answer away. G3 is better (91%), at $0.00008 and with a 9% leak rate.
- **Meta:** the template fails on specificity — it states the type's rule, which the learner could get from a grammar table. The LLMs are specific but break the no-answer constraint in 22–66% of cases, and G2 ignores the length limit (median 44 words; several run to 80+).
- **Explanation (`app`):** the live Explainer prompt is the best-performing style for every LLM (89–94%), and the only one where G2 and G3 had zero upheld errors. The live Rule template on its own is weak mainly on clarity (1.66): it is long (median 50 words) and lists every sub-rule of the type whether or not it applies.
- **Summary:** LLMs are better on error-bearing items (77% vs 60% good); the template is better on clean items (§4).

## 3. Wrong or hallucinated explanations

### 3.1 Judge panel (unreliable for this purpose)

| | G0 | G0live | G1 | G2 | G3 |
|---|---|---|---|---|---|
| Texts rated by both judges | 209 | 55 | 264 | 259 | 263 |
| c = 0 by **either** judge | 12 (5.7%) | 4 (7.3%) | 11 (4.2%) | 5 (1.9%) | 7 (2.7%) |
| c = 0 by **both** judges | 0 | 0 | 2 (0.8%) | 0 | 0 |

J1 flagged 26 texts, J2 flagged 15, and they agreed on 2. Cohen's κ on the "wrong" flag is **0.08**; exact agreement on c is 83% only because most texts get a 2. The panel cannot be used as a hallucination counter.

### 3.2 Manual adjudication (the numbers to use)

I read all 39 texts flagged by either judge and upheld 12. The 27 rejected flags were judge errors: J1 scoring vague-but-true template text as incorrect, J1 misreading the gold list on summaries (e.g. treating "one thing to fix" as contradicting gold when gold has exactly that one error), and J2 marking a true generic rule as a false claim. I also read every unflagged G1–G3 meta and app text for zh-L2 and ja-L2, and G1's for en-L2 (about 250 texts), and found no further false statements — only over-generalisations such as "after *some* the noun must be plural".

| Upheld wrong texts | G0 | G0live | G1 qwen | G2 deepseek | G3 gpt-6-luna |
|---|---|---|---|---|---|
| Total / texts produced | 2 / 213 (0.9%) | 1 / 56 (1.8%) | **6 / 269 (2.2%)** | 1 / 264 (0.4%) | 2 / 269 (0.7%) |
| en-L2 | 0 | 0 | 3 | 0 | 1 |
| zh-L2 | 0 | 1 | 0 | 0 | 0 |
| ja-L2 | 2 | 0 | 3 | 1 | 1 |
| By style | meta 1, hint 1 | rule 1 | meta 3, app 2, summary 1 | meta 1 | meta 1, hint 1 |

Japanese carries 7 of the 12, and one item — `ja_seed_10`, ら抜き言葉 (見つけれる → 見つけられる) — accounts for 4. All three LLMs got the *meta* text wrong on it; G2 and G3 got the *app* text right. Chinese-L2 output had no upheld LLM errors. With 12 events in total these per-cell rates are indicative only.

### 3.3 The bad examples

| Item | Gen / style | Text | What is wrong |
|---|---|---|---|
| `ja_seed_10` 見つけれる→見つけられる | G1 meta | "The verb "見つける" is a Group 1 (godan) verb. You cannot add "-reru" to it for the potential form. Use the correct godan potential conjugation instead." | 見つける is ichidan. Flagged by both judges. |
| same | G1 app | ""見つけれる" is grammatically incorrect because "見つける" is a godan verb, which requires the potential form "見つけられる"…" | Same false class, and the stated consequence does not follow. |
| same | G2 meta | "…見つける is an ichidan (ru-)verb, so its potential form keeps the full られ pattern. Dropping ら is fine, but swapping in れ for ら is not." | 見つけれる *is* the ら-dropped form. Self-contradictory. |
| same | G3 meta | "…The ら-dropping option applies to 見れる, but not to 見つけれる." | No such rule. |
| `ja_seed_07` シンプルなとても→とてもシンプルな | G1 app | "…the adverb "とても" (very) must come before the i-adjective "シンプルな"…" | シンプルな is a な-adjective. |
| `en_multi_01` learn on→learn about | G1 meta | "learn是及物动词，直接接宾语robotics。介词on多余，违反固定搭配规则。" | Tells the learner to delete the preposition; contradicts the confirmed correction. |
| `en_multi_02` the arm.→the arm move. | G1 meta | "make は他動詞なので目的語が必要です。arm の後に move を追加してください。" | False reason (the object is there; a verb is missing), and gives the answer in a no-answer style. |
| `en_clean_03` (clean) | G1 summary | "你的翻译非常准确，几乎与原文完全一致。唯一的小建议是将 'basic sticks' 改为 'simple sticks' 以更贴合原意。" | Invents a fix on a fully acceptable attempt. Flagged by both judges. |
| `en_seed_05` the Arduino to do→…what to do | G3 hint | "「tells the Arduino to do」のあとに、何をするのかを示す語が抜けていませんか？" | Points after "to do"; the missing word goes before it. |
| `ja_seed_11` 作ること、→作ることは、 | G0 meta + hint | "…building the sentence subject-first as in English sounds unnatural here." / "What is "作ること、単に" really about? Try putting that topic first…" | Template does not fit the instance: the topic is already first, only は is missing. `topic_comment` covers several different mistakes. |
| `zh_multi_02` 普通的图案→简单的图案 | G0live rule | "Easily confused words: "普通的图案" and "简单的图案" can both be translated by the same English word, but they are used differently…" | The `false_synonym` variant template asserts a fact about the learner's L1 that nothing verified, and it is doubtful here (ordinary vs simple). The gold variant is itself marked uncertain. |

Two patterns matter for design. First, the LLM errors cluster where the explanation needs a **lexical fact the prompt did not supply** (a verb's conjugation class, an adjective's class). Second, templates fail where a **type is heterogeneous** (`topic_comment`) or where the template **asserts a fact conditional on an upstream label** (`word_choice` variants).

### 3.4 Good examples (same error, all generators)

`zh_seed_03`, aspect_negation, 承载过很多 → 承载了很多, L1 English:

| | Text |
|---|---|
| G0 direct | Aspect / negation: "承载过很多" → "承载了很多" |
| G0 hint | In "承载过很多", is the action completed, experienced, ongoing or habitual? Which marker (or which negator) expresses that? |
| G0 meta | 了, 过 and 着 mark completed, experienced and ongoing actions; 不 negates habits and the future, 没 negates what did not happen. |
| G0live rule | Aspect/negation error: "承载过很多" should be "承载了很多". Chinese marks aspect, not tense: 了 = completed action, 过 = past experience, 着 / 正在 = ongoing state or action. Negate a past or completed action with 没, and habits, wishes or future actions with 不. |
| G3 hint | Check the aspect marker after "承载" here: is this describing an ongoing connection to memories or a past experience? |
| G3 meta | In "承载过很多," 过 marks an experience that happened before. Here, the sentence describes memories the shirt still holds, so this aspect marker does not fit. |
| G3 app | "承载了很多美好的回忆" presents the memories as part of what the T-shirt carries. "承载过" suggests it carried them at some earlier time, which makes the memories sound like they may no longer be connected to it. |
| G2 app | Here you're saying the T-shirt carries many good memories for you now, as an ongoing part of your feelings about it. 过 marks something you have experienced at least once in the past, which would suggest the memories are finished or distant, so 了 fits better with 承载 to show the memories are held and still matter. |
| G1 hint (leaks) | Does '过' imply the memories are in the past and no longer held? Try removing it to show the T-shirt still holds them now. |
| G2 hint (leaks) | You wrote 承载过很多美好的回忆. Does 过 suggest the memories are finished and no longer relevant? The reference uses 承载了很多 — which particle fits an ongoing feeling better? |

Hints in the learner's L1 for an English-L2 error (`en_multi_03`, pick on → pick up, L1 Chinese): G0 "“arm pick on small”里的动词没错——表达这个意思时，后面该接哪个小词（up、out、on、off等）？"; G3 "“pick”后面该用哪个小词，才能表示“拿起”？"; G1 "拿起东西用pick up还是pick on？请回想正确短语。" (gives the answer as one of two options).

Summaries (`en_multi_04`, meaning inversion + register, L1 Japanese): G0 "大部分は正確ですが、一か所で意味が変わっています。まず直したいのは「many things without it」の意味の反転です。"; G2 "DIYプロジェクトの説明は正確で、文の構成も自然です。ただし「without it」は意味が逆になるので「with it」に直しましょう。"

All 1,076 texts are in `feedback_samples.jsonl` for mock-ups.

## 4. Clean items — what to say when nothing is wrong

| Summary on 9 clean items | G0 template | G1 | G2 | G3 |
|---|---|---|---|---|
| good | 9 / 9 | 6 / 9 | 7 / 9 | 8 / 9 |
| Invented a fix | 0 | 1 | 0 | 0 |
| False "identical to the reference" claim | 0 | 1 | 1 | 0 |

The template text: "Your version says everything the original says — nothing needs fixing. Where your wording differs from the reference, it is an acceptable alternative." It is safe but identical every time. The best LLM clean summaries name the acceptable variant, which is what a learner who deviated from the reference wants to hear — G2: "这次翻译完全正确，用 enjoyable 替换 fun 也很自然，准确传达了原文意思。"; G3: "…This attempt is fully correct; 「つかむ」 is an acceptable variation of 「掴む」." That can be templated too if the grader returns the accepted-variation spans ("“{learner_variant}” for “{ref_fragment}” is fine").

LLM "strengths" on clean and error items are frequently filler ("natural flow of your sentence structure", "accurately copied the first two sentences" — the task is translation, not copying). The judges scored these as acceptable; a teacher probably would not.

## 5. Are templates good enough, and for which types?

By style, not by type:

| Style | Template verdict | Evidence |
|---|---|---|
| Direct correction | **Yes, all types.** | 96% good, equal to the best LLM. |
| Elicitation hint | **Yes for most types.** | 78% good overall, 0% leaks. Usefulness ≥ 1.75 on 17 of 25 rated types, including every particle, measure-word, agreement, article, preposition, phrasal-verb, word-order, register and word-choice item. |
| Hint — exceptions | Use an LLM hint (with leak filter) or skip the hint. | `topic_comment` (mismatch, §3.3), `conjugation` (1.0), `aspect_negation` (1.5, 1 of 3 good), `collocation` (1.5), `cohesion_connective` (1.5), `de_particle` (1.5), `omission` (1.6), `meaning_inversion` (1.7, 1 of 3 good). |
| Metalinguistic rule | **No, for any type.** | Usefulness 0.2–1.3 on every type; specificity 0.68. |
| Explanation | **No.** The live Rule template alone is 55% good; with the LLM application layer 89–94%. | |
| Summary, clean | **Yes.** | 9 / 9. |
| Summary, with errors | Marginal. | 60% vs 77% good. The template names the error by taxonomy label ("Aspect / negation at …"), which both judges called vague. |

Per-type n is 1–7 (17 of 26 types have n ≤ 2; `tam` has no two-judge rating because J1 returned nothing parsable for `ja_seed_05`). Treat the exception list as a set of hypotheses for the design team, not as findings. The full per-type table is `results.json → by_subtype`.

The exceptions share a property: they are types where the *slot* is not enough to guess the fix (open-class or structural errors), or where one slug covers several distinct mistakes. Closed-class types — where the learner must pick from a small set — are where a fixed question works.

## 6. Recommended mix and blended cost

| Layer | Source | When | Cost per submission |
|---|---|---|---|
| Direct correction | Template | Every error, rendered immediately | $0 |
| Hint | Template; suppressed for the §5 exception types | Every error, shown before the correction if the UI wants a try-again step | $0 |
| Explanation | One batched LLM call per error-bearing submission, live Explainer prompt, `deepseek/deepseek-v4.1-flash` (or `openai/gpt-6-luna`) | Loaded after the instant layers; Rule-only fallback as today | $0.000050 (G2) / $0.000114 (G3) |
| Summary, clean | Template (optionally filled with the accepted variant) | Clean submissions | $0 |
| Summary, errors | Same model, second call | Error-bearing submissions | $0.000028 (G2) / $0.000070 (G3) |

Blended, with G2 and with the share of error-bearing submissions at p: **p × $0.000077**. At the gold set's 67% that is **$0.00005 per submission** (G3: p × $0.000183 → $0.00012). Added to ~$0.0002 for jev detection the full pipeline is about $0.00025–0.00032 per submission. An all-LLM version of every style (G2: direct + hint + meta + app + summary) would cost $0.00019 per error-bearing item — 2.4× more, for no measured gain on direct and a leak problem on hint and meta.

G2 or G3? G2 is 2.3× cheaper, had the fewest upheld errors, and the highest app score, but it writes long (meta and hint over the limit 73–91% of the time; app median 43.5 words) and it omitted 5 of 56 explanations — which the live prompt permits ("omit that index") and which falls back to Rule-only. G3 is terse and obeys limits. Both are fine for `app`; the differences between them are within what 56 errors can resolve.

Latency: each call is 1.2–2.1 s p50 and under 3.2 s p90. Explanation and summary can run in parallel, so the LLM layer adds about 2 s after the template layers have rendered.

**Guards to add in code**, all cheap:
- Leak filter on any LLM hint or meta: reject if the minimal corrected fragment appears in the text and not in the learner form; fall back to the template hint. (This check agreed with J2 at κ = 0.74.)
- Length cap per style; the existing 240-character cap on the application layer already does this for `app`.
- For clean submissions, never call the LLM for a summary.
- Supply lexical facts the explanation depends on (verb/adjective class for `conjugation`, measure word for the noun) from the dictionary when available, since that is where all three models went wrong.

Not tested: merging explanation and summary into a single call (would cut the input cost roughly in half), and prompt variants. The prompts were written once and not tuned; the leak and length rates might improve with iteration.

## 7. What a grading result must carry for each style

| Field | direct | hint | meta | explanation | summary | Note |
|---|---|---|---|---|---|---|
| `subtype` (v6 slug) | label | selects template | selects template | gloss + rule | label of top error | Needs `taxonomy_version` beside it. |
| `learner_form` | yes | yes | yes | yes | yes (top error) | The only fragment the no-answer styles may show. |
| `corrected_form` | yes | **must be absent from the text**; needed by the leak filter | same | yes | LLM only | |
| `span_reproduction` [start, end] | to highlight | to anchor the question | to highlight | – | – | Without it the hint cannot point at the spot when the same string occurs twice. |
| `span_reference` [start, end] | to show the fragment in context | – | – | – | – | Must stay hidden while a hint is on screen. |
| `severity` (minor / major / critical) | chip | – | – | – | picks the top error and the wording | |
| `explanation_variant` (word_choice) | – | – | – | picks variant template + prompt guidance | – | Template asserts facts based on it (§3.3); carry `variant_uncertain` and fall back to the plain template when set. |
| `confidence` | hedge the wording below a threshold | hide hint below a threshold | – | skip LLM below a threshold | exclude low-confidence errors from "fix this first" | Not exercised here: gold errors have confidence 1. |
| Sentence pair (reference + reproduction) | – | – | – | required | required | LLM only. |
| Accepted-variation spans (clean items) | – | – | – | – | to fill the clean template | New field; the grader does not return it today. |
| `feedback_source` per text (template / model slug / fallback) | | | | | | For audit and for A/B reading later. |

The current contract (`errors[]{category, subtype, source, severity, learner_form, corrected_form, explanation, confidence, is_mistake, explanation_parts{rule, application}}` plus `highlights[]{span_reproduction, reason}`) already covers direct and explanation. Hints need `span_reproduction` on each error rather than only in `highlights`, and a place to put the text: `explanation_parts.hint` alongside `rule` and `application` would be the smallest change.

A practical gap for the jev track: the gold `learner_form` / `corrected_form` are short, aligned fragments. Every template and every leak check here assumes that. If the detector returns a type and a span but no reference fragment, direct corrections and the leak filter need an alignment step first.

## 8. Persistence for longitudinal error tracking

What exists (migrations `dual_translation_groundwork.sql`, `dt_taxonomy_v6_columns.sql`, `dt_error_profile.sql`): `dt_error_instance` already stores `submission_id`, both spans, `category`, `subtype`, `source`, `severity`, `learner_form`, `corrected_form`, `explanation`, `confidence`, `is_mistake`, `taxonomy_version`, `explanation_variant`, `remap_flag`, `created_at`. `dt_error_profile_entry` aggregates per (user, L1, L2, subtype): `count`, `severity_rank`, `trend`, `remediation_status`. `wiki/database/schema.tech.md` has no section for these tables; the spec lives in `wiki/features/dual-translation.tech.md`.

So the per-error record largely exists. What is missing for tracking *patterns* rather than type counts, and for learning which feedback works:

| Proposed addition to `dt_error_instance` | Type | Why |
|---|---|---|
| `target_key` | text, nullable | The specific thing that was wrong inside the type, normalised: the corrected minimal fragment for closed-class types (`を`, `件`, `了`, `about`, `an`), a lemma or sense id for word_choice. "Case-particle errors" is not actionable; "に for を with transitive verbs, 4 times" is. Deterministic from the two forms for closed-class types. |
| `learner_key` | text, nullable | The normalised wrong choice (`に`, `个`, `过`, `on`, ∅ for omissions). With `target_key` it gives the confusion pair. |
| `sentence_index` | smallint | Which sentence of the passage; lets a repeat attempt at the same passage be compared error by error. |
| `feedback_shown` | jsonb | Which styles were rendered and from what source: `{"direct":"template","hint":"template","explanation":"deepseek/deepseek-v4.1-flash"}`. Without it there is no way to tell later whether hints reduce recurrence. |
| `self_corrected` | boolean, nullable | Whether the learner fixed it after the hint and before seeing the answer. This is the error-vs-mistake signal the feature spec already wants for `is_mistake`, and it is only observable if a hint step exists. |

Minimal record, per error (existing columns unmarked, new ones marked +):

```
submission_id, sentence_index+, span_reproduction, span_reference,
taxonomy_version, subtype, explanation_variant, severity, confidence,
learner_form, corrected_form, learner_key+, target_key+,
is_mistake, self_corrected+, feedback_shown+, created_at
```

`explanation` text does not need to be kept for tracking; it is kept today because ADR-015 makes it eager and NOT NULL. `dt_error_profile_entry` would then need a finer grain — a child row or a jsonb of top `(learner_key → target_key)` pairs per subtype — which is a schema decision for the wiki owner, not something this track should fix.

## 9. Caveats

- **LLM judges.** κ = 0.08 on the "factually wrong" flag; 27 of 39 flags were judge errors on inspection. Usefulness and clarity scores are two models' opinion of what a teenager would learn from, with exact agreement of 67% on usefulness. No learner saw any of this text. J1 produced no parsable output for one item and J2 dropped one text.
- **Manual adjudication is mine**, not a native speaker's. I read all flagged texts and about a quarter of the unflagged ones; unflagged en-L2 output from G2 and G3 and all unflagged hint, direct and summary texts were not re-read. The true error rates could be somewhat higher than §3.2.
- **Small n.** 56 errors, 12 upheld wrong texts in total, 1–7 errors per type. Differences between G2 and G3 are not established. One item (`ja_seed_10`) drives a third of the errors.
- **Seeded errors.** Gold errors are scripted perturbations of a correct passage with clean, minimal spans, in three source texts (robot arm ×2, T-shirt). Real learner errors overlap, are longer, and come with imperfect spans and labels from the detector. Template feedback is exactly as wrong as the label it is given; this experiment never gave it a wrong label.
- **L1 was assigned**, and zh/ja L1 output was only produced for English-L2 items (15 items). Chinese- and Japanese-language feedback about Chinese or Japanese errors (ja-L1 learner of zh, zh-L1 learner of ja) was not tested.
- **Templates and prompts are first drafts.** G0 templates are AI-written and unreviewed; 16–20% exceed the 25-word limit they were supposed to respect. Generator prompts for direct/meta/hint/summary were written in English once and not tuned; only `app` uses the production prompt.
- **Costs** are from `usage.cost` on every call (no list-price fallback was needed), at one call per item per style. Batching styles into one call would be cheaper than the sum shown.

## 10. Files

| File | Content |
|---|---|
| `REPORT.md` | This report. |
| `results.json` | All aggregates, per-type table, judge agreement, cost/latency, flagged examples, manual adjudication. |
| `templates.json` / `g0_templates.py` | G0 templates (label, meta, hint per slug and L1; direct and summary patterns) and the renderer. |
| `feedback_samples.jsonl` | 1,076 rows: item, L2, L1, error, generator, model, style, text, call cost and latency. |
| `judged_rows.json` | The same rows with both judges' ratings and the code-side metrics. |
| `run.py`, `analyze.py` | Harness (cache, ledger, budget guard) and aggregation. |
| `costs.jsonl` | Ledger, one line per paid call. Total $0.21639: gemini-3.6-flash $0.1650, claude-haiku-5.5 $0.0243, gpt-6-luna $0.0157, deepseek-v4.1-flash $0.0070, qwen3.7-flash $0.0045. |
| `gen_raw.json`, `judge_raw.json`, `cache/` | Raw responses. |
| `taxonomy_v6_live.json`, `models.json` | Snapshot of the v6 taxonomy JSON extracted from the seed migration, and the OpenRouter model list used for selection. |
