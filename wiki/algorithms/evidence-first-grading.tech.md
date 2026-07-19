---
title: Evidence-First Grading (Dual Translation v2) — Technical Specification
type: algorithm-tech
status: complete
prose_page: ./evidence-first-grading.md
last_updated: 2026-07-19
dependencies:
  - "service: services.dual_translation.{tier0,prompts,grader_cascade,router} — v1 modules being revised"
  - "table: dt_error_instance (severity CHECK extension required), dt_rubric_version (config v3), dt_taxonomy_version (v5)"
  - "service: services.model_arena.llm_runner.call_model_with_usage"
  - "service: services.dictation.grader — Tier 0 diff, also supplies candidate regions + token counts"
breaking_change_risk: medium
---

# Evidence-First Grading (v2) — Technical Specification

> Supersedes-by-design the grading logic in [[algorithms/translation-grading-cascade.tech]]
> (v1, shipped). Tier 0, the router, prompt caching, budget guardrails, and the L2-only /
> numerical-index business rule all carry over unchanged unless stated here.

## 1. Summary of changes vs v1

| Aspect | v1 (shipped) | v2 (this spec) |
|---|---|---|
| Dimension scores | Model emits 1–4 gestalt bands | **Computed in Python** from severity-weighted error sums (MQM-style); only naturalness+range are model-judged, with mandatory span evidence |
| Call roles | Tier 1 (accuracy/range) + Tier 2 (rest), both band + detect | **Detector** (exhaustive detection, no scores) + **Verifier/Judge** (confirm/reject/adjust each error, find missed ones, judge naturalness/range) |
| Severity | `global` \| `local` | `minor` (1) \| `major` (5) \| `critical` (25) with operationalized reader-impact tests |
| Explanations | Rule template per (subtype, L1) only | 3 layers: Correction + Rule template + **model-generated instance Application** (Explainer call, L1) |
| Taxonomy | 9 subtypes/pair | ~15–17 subtypes/pair with per-subtype `dimension`/`default_severity`/`treatable`/`cloze_suitable` meta |
| Diff usage | Tier 0 gate only | Diff opcodes passed to Detector as **candidate regions** with an accounted-for rule |
| Positive evidence | none | `highlights[]` (≤3, enum-coded reasons) |
| Band descriptors | frequency-adverb boilerplate | Behaviorally anchored, tied to the computed thresholds |
| Few-shots | none | 1 worked exemplar per (L2, call) in the cached prefix, versioned in rubric config |
| Tier-0 near-exact | full marks at mismatch ≤ 5% | full marks **only if all diff ops are normalization-class**; otherwise always Detector |
| Fail-open | silent full marks (MAX_BAND) | **provisional grade** (`grader_trace.provisional=true`), renormalized weights; never silent full marks |
| Missing confidence | defaults 1.0 (never escalates) | defaults 0.0 (escalates) |
| Verification of quality | none | Gold-set eval harness: span F1, subtype acc, clean-passage FP rate, band QWK; gates every version bump |

## 2. Architecture / flow

```
POST /submit
  │
  ▼
Tier 0 (unchanged normalize/diff/cache)
  │  resolves ONLY if every non-equal opcode is normalization-class → full marks
  │  else: diff opcodes → candidate_regions (cap 20)
  ▼
DETECTOR  (cheap slug, was tier1; L2-only prompt, numerical output)
  │  errors[] + highlights[] — NO scores
  ▼
VERIFIER / JUDGE  (mid slug, was tier2; L2-only prompt, numerical output)
  │  verdicts[] (confirm/reject/adjust per error) + added_errors[]
  │  + judgments{naturalness, range} with evidence_spans
  ▼
MERGE (Python): final_errors = confirmed + adjusted + added
  ▼
DERIVED SCORING (Python, §4): accuracy/fidelity/understandability computed;
  naturalness/range from judgments; overall_band = weighted mean (weights unchanged)
  ▼
EXPLAINER  (cheap slug, L1 prose, only if final_errors non-empty; ADR-019)
  │  instance Application text per error; validated; falls back to Rule-only
  ▼
render 3-layer explanations → persist dt_grade + dt_error_instance[]
```

Escalation: Tier-3 arbiter (existing reserved slot) only when the verifier rejects ≥ 50% of
proposed errors OR verifier confidence < 0.5; re-adjudicates contested errors only. Default
OFF via config, as today.

**Failure modes (replaces v1 fail-open-to-full-marks):**
- Detector fails → Verifier runs with an empty proposed list; its `added_errors` path is a
  full detection pass (same prompt handles it). `grader_trace.provisional=true`.
- Verifier fails → Detector's errors are used unverified; naturalness/range have no judgment →
  those dimensions are **omitted from the weighted mean (weights renormalized)**, and
  `provisional=true`.
- Both fail → Tier-0 diff shown, no scores, `provisional=true`, UI invites retry. Never
  silent full marks.
- Explainer fails per-error or wholesale → Rule template only (log, non-blocking).

## 3. Severity model (MQM-aligned)

Enum (new indices, prompt + DB): `0=minor (weight 1)`, `1=major (weight 5)`, `2=critical (weight 25)`
([MQM scoring model](https://themqm.org/error-types-2/the-mqm-scoring-models/)).

Reader-impact tests (exact prompt wording in §7):
- **minor** — a native reader notices but reads on without hesitation; meaning fully intact.
- **major** — a native reader hesitates or must reread; plainly wrong form; meaning survives.
- **critical** — meaning lost/changed/inverted (wrong actor, dropped negation, missing
  essential information) or register failure causing real offence.

**Migration:** `dt_error_instance.severity` CHECK extended to
`('minor','major','critical','global','local')`; backfill `local→minor`, `global→major`;
old values dropped from the CHECK after backfill verification. `is_mistake` (Corder) is
unchanged but operationalized: *true only if the same element is used correctly elsewhere in
the same text*.

## 4. Derived scoring

Inputs: `final_errors` (post-merge), active `dt_taxonomy_version.taxonomy.subtype_meta`
(§5), active `dt_rubric_version.config` (v3, below).

```
SEVERITY_WEIGHTS = {minor: 1, major: 5, critical: 25}          # rubric config
UNDERSTANDABILITY_WEIGHTS = {minor: 0, major: 2, critical: 25}  # rubric config

penalty[d]   = Σ SEVERITY_WEIGHTS[e.severity]
               for e in final_errors if subtype_meta[e.subtype].dimension == d and not e.is_mistake
penalty[understandability] = Σ UNDERSTANDABILITY_WEIGHTS[e.severity] for ALL final_errors (not is_mistake)

band[d] = 4 if penalty[d] <= t4 else 3 if <= t3 else 2 if <= t2 else 1
```

Provisional default thresholds (rubric config v3; **to be calibrated in Phase 0** — flagged
in prose-page open questions). Absolute per-passage points are defensible because passages
are uniformly 2–4 sentences (length controlled at selection, ADR-018):

| dimension | t4 | t3 | t2 | intuition |
|---|---|---|---|---|
| accuracy, fidelity | 1 | 6 | 15 | 4 = at most one minor; 3 = one major or a few minors; 2 = two majors; 1 = worse |
| understandability | 2 | 6 | 25 | one major barely registers; one critical → band 2; two criticals → 1 |

`naturalness` and `range` come from the Verifier's `judgments` (clipped 1–4); a judgment
without ≥1 valid `evidence_spans` entry is discarded (treated as missing → renormalize).
Naturalness-mapped subtypes (collocation, topic_comment…) are still recorded as errors — they
feed remediation and the judge sees them — but their band comes from the judgment, with a
consistency check logged for eval when |judged − derived| ≥ 2.

`overall_band`: unchanged weighted mean (`compute_overall_band`), same weights as rubric v2
(`ja.fidelity` .30, `zh.accuracy` .40). `is_mistake` errors are displayed but never scored or
promoted (unchanged).

**Worked example (JA, 32-token reference).** Confirmed errors: ① `particle_wa_ga`, major
(accuracy +5); ② `word_choice`, minor (fidelity +1). → accuracy 5 → band 3; fidelity 1 →
band 4; understandability 2 → band 4; judge: naturalness 3, range 3.
Weighted (ja): (3×.3 + 4×.3 + 4×.3 + 3×.15 + 3×.1)/1.15 = 3.52 → **overall 4**, with
learner-facing lines: "Accuracy 3 — one major particle error" / "Fidelity 4 — one minor word choice".

**Re-scoring property:** bands are a pure function of (stored errors, rubric version) —
threshold/weight changes re-score historical grades in SQL/Python with **zero model calls**.

### `dt_rubric_version.config` v3 (synthetic example)

```json
{
  "weights": { "default": {"accuracy":0.3,"understandability":0.3,"fidelity":0.15,"range":0.15,"naturalness":0.1},
               "by_language": {"ja":{"fidelity":0.3},"zh":{"accuracy":0.4}} },
  "severity_weights": {"minor":1,"major":5,"critical":25},
  "understandability_weights": {"minor":0,"major":2,"critical":25},
  "band_thresholds": { "default": {"t4":1,"t3":6,"t2":15},
                       "by_dimension": {"understandability":{"t4":2,"t3":6,"t2":25}} },
  "acceptable_variation": { "<l2_code>": ["<L2-authored bullet shown verbatim in the prompt>", "..."] },
  "exemplars": { "detector": {"<l2_code>": {"reference":"...","learner":"...","json":{}}},
                 "verifier": {"<l2_code>": {"reference":"...","learner":"...","proposed":[],"json":{}}} },
  "band_descriptors": { "<age_tier>": {"<dimension>": {"<l2_code>": {"1":"...","2":"...","3":"...","4":"..."}}} }
}
```

Everything the prompts consume stays in the versioned config → the cached prefix remains
byte-stable per (L2, call type, versions), preserving v1's prompt-caching lever.

## 5. Taxonomy v5

New per-subtype meta (in `dt_taxonomy_version.taxonomy`):

```json
"subtype_meta": { "<subtype>": { "dimension": "accuracy|fidelity|naturalness",
                                  "default_severity": "minor|major",
                                  "treatable": true, "cloze_suitable": true } }
```

`dimension` drives §4. `treatable` (Ferris: rule-governed → drillable) and `cloze_suitable`
feed Feature 2's exercise chooser. `default_severity` is used only for gold-set seeding and
when a model omits severity — the model assigns per-instance severity via the reader tests.

**Shared core (all pairs, 8):** `omission`→fidelity/major · `addition`→fidelity/minor ·
`word_choice`→fidelity/minor · `collocation`→naturalness/minor · `word_order`→accuracy/major ·
`register`→fidelity/major · `orthography`→accuracy/minor · `cohesion_connective`→naturalness/minor

**EN target (+7):** `article`→accuracy/minor · `preposition`→accuracy/minor ·
`tense_aspect`→accuracy/major · `subject_verb_agreement`→accuracy/minor ·
`plural_number`→accuracy/minor · `phrasal_verb`→fidelity/minor · `pronoun_reference`→accuracy/major

**JA target (+9):** `particle_wa_ga`→accuracy/major · `particle_case` (を/に/で/へ)→accuracy/major ·
`particle_other`→accuracy/minor · `verb_conjugation` (て-form/potential/passive/causative)→accuracy/major ·
`tense_aspect_ja` (た/ている)→accuracy/major · `keigo_register`→fidelity/major ·
`counter_classifier`→accuracy/minor · `script_choice`→accuracy/minor · `topic_comment`→naturalness/minor

**ZH target (+9):** `classifier`→accuracy/minor · `aspect_marker` (了/过/着)→accuracy/major ·
`de_particles` (的/得/地)→accuracy/minor · `ba_construction`→accuracy/major ·
`bei_passive`→accuracy/major · `resultative_complement`→accuracy/major ·
`directional_complement`→accuracy/minor · `adverbial_order`→accuracy/major · `topic_comment`→naturalness/minor

Rationale: splits JA `particle` three ways (は/が discourse rule ≠ case-particle rule ≠ the
rest — different explanations, different drills); adds the highest-frequency learner-corpus
categories previously invisible (`de_particles`, `verb_conjugation`, `addition`, `collocation`,
`orthography`). Sizes (15/17/17) stay well under human-rater tagsets (CLC ~80, HSK 46) to
protect index-classification accuracy; exemplars + glosses mitigate. Every subtype needs
`subtype_glosses[subtype][l2]` and a Rule template per L1 (authoring task, same pattern as
TASK-616). `category`/`source` axes and per-pair resolution are unchanged.

## 6. Model-call contracts

All three calls: `temperature=0.0`, JSON-only output, `clean_json_response` + shape
validation; per-error validation (spans within bounds, `learner_form == reproduction[span]`
with a string-search repair fallback before dropping, enum indices in range) as v1's
`_decode_error`, extended with the exact-substring repair.

### 6a. Detector (cheap slug)

```json
{
  "confidence": 0.9,
  "errors": [ { "span_repro":[0,0], "span_ref":[0,0], "category":0, "source":0,
                "severity":1, "subtype":4, "learner_form":"...", "corrected_form":"...",
                "confidence":0.9, "is_mistake":false } ],
  "highlights": [ { "span_repro":[0,0], "reason":0 } ]
}
```
`severity` uses the NEW triad indices (§3). `highlights.reason`: 0=grammar, 1=word choice,
2=register/politeness, 3=structure. Max 3 highlights enforced in code.

### 6b. Verifier / Judge (mid slug)

```json
{
  "confidence": 0.9,
  "verdicts": [ { "error_index":0, "verdict":0,
                  "severity":1, "subtype":4, "span_repro":[0,0], "span_ref":[0,0] } ],
  "added_errors": [ { "...same shape as detector errors...": 0 } ],
  "judgments": { "naturalness": {"band":3, "evidence_spans":[[0,0]]},
                 "range":       {"band":3, "evidence_spans":[[0,0]]} }
}
```
`verdict`: 0=confirm, 1=reject, 2=adjust (adjust fields optional; only present when changed).
Verdict for an unknown `error_index` is dropped; a proposed error with **no verdict at all
defaults to confirm** (fail-safe toward showing the error, since the detector already passed
validation). Rejected errors are logged (`grader_trace.rejected_count`) for eval, never
persisted or shown.

### 6c. Explainer (cheap slug, learner's L1 — ADR-019)

Input: reference, learner text, numbered final errors (learner_form / corrected_form /
subtype gloss in L1 / the Rule-template text). Output:

```json
{ "explanations": [ { "error_index":0, "text":"<1-2 sentences in L1>" } ] }
```

Code validation per item: ≤ 240 chars, single paragraph, must contain `learner_form` or
`corrected_form` (≥2-char overlap), must not contain digits formatted like scores ("3/4").
Invalid or missing → Rule-only for that error. Persisted `dt_error_instance.explanation` =
`Rule + "\n" + Application` (concatenated — **no schema change needed**; UI already
escapes HTML). Contract additions: `errors[].explanation_parts = {rule, application|null}`.

`grader_trace` additions: `framework_version: 2`, `provisional: bool`,
`rejected_count: int`, `prompt_version: <rubric/taxonomy version pair>`.

## 7. Prompts (complete)

Same architecture as v1 `prompts.py`: a **cacheable system prefix** assembled from versioned
blocks (byte-stable per L2 + versions) and a **tiny per-submission user suffix**. JSON field
names stay English (protocol tokens); all natural language is in the L2 for Detector/Verifier
and in the **L1** for the Explainer. ZH/JA strings below are AI-authored first drafts flagged
for native review (open question).

### 7a. Detector — system prompt blocks

**Header:**
- EN: `You are an expert examiner of learner writing for a language-learning app. You will receive a REFERENCE text (the correct version), a LEARNER text (an attempt to reproduce it), and CANDIDATE REGIONS where the two differ. Your only task in this call is to find, locate, classify and correct errors, and to credit genuinely well-handled difficult spots. You do NOT assign scores — scores are computed later from your error report, so completeness and precision are everything. Work through the learner text from start to finish. Output ONLY a single JSON object — no prose before or after.`
- ZH: `你是语言学习应用中的学习者写作评审专家。你将收到一段【参考译文】（正确版本）、一段【学习者译文】（学习者的复现尝试），以及两者存在差异的【候选区域】列表。本次调用你唯一的任务是：找出、定位、分类并改正错误，并对确实处理得好的难点给予标注。你不打分——分数将由你的错误报告计算得出，因此完整性和精确性至关重要。请从头到尾系统地检查学习者译文。只输出一个JSON对象，前后不得有任何其他文字。`
- JA: `あなたは語学学習アプリにおける学習者作文の専門審査員です。「参照文」（正しい版）、「学習者文」（その再現の試み）、および両者が異なる「候補領域」のリストが与えられます。この呼び出しでのあなたの唯一の任務は、誤りを発見・特定・分類・訂正し、難所を正しく処理できている箇所を評価することです。採点はしません——スコアはあなたの誤り報告から後で計算されるため、網羅性と正確性がすべてです。学習者文を最初から最後まで体系的に確認してください。出力は単一のJSONオブジェクトのみとし、前後に文章を含めないでください。`

**Accounted-for rule:**
- EN: `Every candidate region must be accounted for in exactly one way: (a) reported as an error, (b) reported as a highlight, or (c) recognized as acceptable variation and silently ignored. Candidate regions are hints from a character diff, not boundaries — merge adjacent regions that form one error, and still scan the rest of the text for errors the diff cannot expose.`
- ZH: `每个候选区域必须以且仅以下列一种方式处理：(a) 报告为错误；(b) 报告为亮点；(c) 判定为可接受的变体并直接忽略。候选区域只是字符级对比给出的提示，不是边界——相邻区域若构成同一个错误应合并处理，同时仍需检查全文，找出对比无法暴露的错误。`
- JA: `各候補領域は、必ず次のいずれか一つとして処理してください：(a) 誤りとして報告する、(b) ハイライトとして報告する、(c) 許容される言い換えと判断して無視する。候補領域は文字単位の差分による手がかりにすぎず、境界ではありません——隣接する領域が一つの誤りを構成する場合は統合し、差分では検出できない誤りがないか全文も確認してください。`

**Acceptable variation (label + per-L2 bullets from rubric config `acceptable_variation`):**
- EN label: `The following are NOT errors (acceptable variation) — never report them:` — default bullets: synonyms preserving meaning and register · contractions where the register allows them · optional commas · equally natural clause order · consistent British/American spelling.
- ZH label: `以下情况不是错误（属于可接受的变体）——切勿报告：` — 语境清晰时省略主语或代词 · 意义与语域均保留的同义替换 · 两种说法同样自然的语序 · 标点全角/半角差异。
- JA label: `以下は誤りではありません（許容される言い換え）——決して報告しないでください：` — 文脈上明らかな主語・主題の省略 · 意味と敬語レベルを保つ同義の言い換え · どちらも標準的な仮名・漢字表記 · どちらも自然な「へ」と「に」の方向表現。

**Severity tests:**
- EN: `Severity — apply this reader-impact test to each error: minor (0) = a native reader notices but reads on without hesitation; meaning fully intact. major (1) = a native reader hesitates or must reread; the form is plainly wrong but the intended meaning survives. critical (2) = the meaning is lost, changed or inverted (wrong actor, dropped negation, missing essential information), or the register failure would cause real offence.`
- ZH: `严重程度——对每个错误应用以下读者影响测试：轻微（0）＝母语读者会注意到，但不会停顿，意义完全保留；较重（1）＝母语读者会迟疑或需要重读，形式明显有误，但原意仍可理解；严重（2）＝意义丢失、改变或颠倒（如动作主体错误、否定丢失、关键信息缺失），或语域失误会造成真正的冒犯。`
- JA: `重大度——各誤りに次の読者影響テストを適用してください：軽微（0）＝母語話者は気づくが、止まらずに読み進められ、意味は完全に保たれる。重大（1）＝母語話者がつまずく、または読み返す必要があり、形は明らかに誤っているが意図された意味は伝わる。致命的（2）＝意味が失われる・変わる・逆転する（動作主の誤り、否定の欠落、必須情報の欠落など）、または敬語の失敗が実際に失礼にあたる。`

**Category/source enums + indexed subtype list:** identical mechanism and glosses as v1
(`_ENUM_LABELS`, `subtype_glosses`), with the severity enum replaced by the triad above.

**Span discipline:**
- EN: `Spans are character offsets: span_repro into the LEARNER text, span_ref into the REFERENCE text. learner_form must be the exact substring of the LEARNER text at span_repro (copy it character-for-character); corrected_form must be the exact substring of the REFERENCE text at span_ref. Reports whose forms do not match their spans are discarded, so verify each one.`
- ZH: `跨度为字符偏移量：span_repro 指向【学习者译文】，span_ref 指向【参考译文】。learner_form 必须与学习者译文中 span_repro 处的子串逐字一致；corrected_form 必须与参考译文中 span_ref 处的子串逐字一致。形式与跨度不一致的报告将被丢弃，请逐一核对。`
- JA: `スパンは文字オフセットです：span_repro は「学習者文」内、span_ref は「参照文」内を指します。learner_form は学習者文の span_repro の位置の部分文字列と一字一句一致していなければなりません。corrected_form は参照文の span_ref の位置の部分文字列と一致していなければなりません。形式がスパンと一致しない報告は破棄されるため、必ず確認してください。`

**Mistake flag (Corder, operationalized):**
- EN: `is_mistake: true only if the same element is used correctly elsewhere in the learner text (a slip, not a knowledge gap); otherwise false.`
- ZH: `is_mistake：仅当同一语言点在学习者译文其他位置使用正确时（属于笔误而非知识缺口）为true，否则为false。`
- JA: `is_mistake：同じ言語項目が学習者文の他の箇所では正しく使われている場合のみtrue（知識不足ではなく一時的なミス）。それ以外はfalse。`

**Highlights:**
- EN: `highlights: up to 3 places where the learner correctly handled something genuinely difficult (a tricky grammar point, exact register, an idiomatic expression). Only non-obvious successes — an empty list is fine. reason: 0=grammar, 1=word choice, 2=register/politeness, 3=structure.`
- ZH: `highlights：最多3处学习者正确处理了确实有难度的内容（棘手的语法点、准确的语域、地道的表达）。只报告并非显而易见的成功——空列表也可以。reason：0=语法，1=用词，2=语域/礼貌，3=结构。`
- JA: `highlights：学習者が本当に難しい点を正しく処理できた箇所を最大3つ（難しい文法項目、的確な敬語レベル、慣用的な表現など）。自明でない成功のみを報告してください——空リストでも構いません。reason：0=文法、1=語彙選択、2=敬語・文体、3=構文。`

**JSON shape + exemplar:** the §6a schema (ensure_ascii=False), then one worked exemplar from
rubric config. EN exemplar (synthetic):

```
REFERENCE: She has lived in Osaka since 2019, but she still cannot speak Kansai dialect.
LEARNER:   She lives in Osaka since 2019, but she still cannot speak Kansai dialect.
→ {"confidence":0.95,
   "errors":[{"span_repro":[4,9],"span_ref":[4,13],"category":0,"source":1,"severity":1,
              "subtype":<tense_aspect idx>,"learner_form":"lives","corrected_form":"has lived",
              "confidence":0.95,"is_mistake":false}],
   "highlights":[]}
```

### 7b. Detector — user prompt

```
<REF label>: {gold_l2}
<LEARNER label>: {reproduction}
<REGIONS label>: [{"op":"replace","ref":[4,13],"repro":[4,9]}, ...]   ← tier0 non-equal opcodes, cap 20
```
Labels: EN `REFERENCE`/`LEARNER`/`CANDIDATE REGIONS` · ZH `参考译文`/`学习者译文`/`候选区域` ·
JA `参照文`/`学習者文`/`候補領域`.

### 7c. Verifier / Judge — system prompt blocks

**Header + verdicts + added_errors + judgments:**
- EN: `You are a senior examiner reviewing a first-pass error report on a learner's reproduction of a reference text. You receive the REFERENCE, the LEARNER text, and a numbered list of PROPOSED ERRORS. Judge each proposed error strictly; then find what the first pass missed; then judge two dimensions with evidence. Output ONLY a single JSON object.`
  `For each proposed error output a verdict: 0 = confirm as reported; 1 = reject (not an error: acceptable variation, a wrong span, or the learner's version is actually correct); 2 = adjust (a real error, but the severity, subtype or spans are wrong — supply the corrected fields). Rejecting false alarms is as important as confirming real errors.`
  `added_errors: errors the first pass missed, in the same shape as proposed errors. Look especially for meaning omitted or added relative to the reference, register or politeness mismatches, and unnatural phrasing that a diff-guided first pass cannot see.`
  `Finally, judge these dimensions of the learner text on the 1-4 bands described below: {dims}. For each, cite the 1-3 character spans of the learner text that most influenced your band. A band without evidence spans is invalid.`
- ZH: `你是一位资深评审，负责复核对学习者译文的第一轮错误报告。你将收到【参考译文】、【学习者译文】以及带编号的【待核错误】列表。请严格评判每个待核错误；然后找出第一轮遗漏的错误；最后依据证据对两个整体维度进行评级。只输出一个JSON对象。`
  `对每个待核错误给出裁定：0＝确认无误；1＝驳回（不是错误：属于可接受变体、跨度有误、或学习者的写法实际上正确）；2＝调整（确属错误，但严重程度、子类型或跨度有误——请提供修正后的字段）。驳回误报与确认真实错误同等重要。`
  `added_errors：第一轮遗漏的错误，格式与待核错误相同。请特别注意：相对参考译文的意义缺失或添加、语域/礼貌层级不匹配、以及依赖字符对比的第一轮无法察觉的不自然表达。`
  `最后，按下述1–4级描述对学习者译文的以下维度评级：{dims}。每个维度须引用对你的评级影响最大的学习者译文字符跨度（1–3个）。没有证据跨度的评级无效。`
- JA: `あなたは、学習者文に対する一次誤り報告を再審査する上級審査員です。「参照文」「学習者文」、および番号付きの「審査対象誤り」リストが与えられます。各審査対象誤りを厳密に判定し、次に一次審査の見落としを探し、最後に2つの観点を証拠に基づいて評定してください。出力は単一のJSONオブジェクトのみです。`
  `各審査対象誤りに判定を出してください：0＝報告どおり確認、1＝棄却（誤りではない：許容される言い換え、スパンの誤り、または学習者の表現が実際には正しい）、2＝修正（誤りではあるが、重大度・サブタイプ・スパンが不適切——修正後のフィールドを提示）。誤報の棄却は、真の誤りの確認と同じく重要です。`
  `added_errors：一次審査が見落とした誤り（審査対象誤りと同じ形式）。特に注意すべき点：参照文に対する意味の欠落・追加、敬語・文体レベルの不一致、文字差分に基づく一次審査では気づけない不自然な表現。`
  `最後に、以下の観点について、下記の1〜4の評価基準に従って学習者文を評定してください：{dims}。各観点について、評定に最も影響した学習者文の文字スパン（1〜3個）を必ず示してください。証拠スパンのない評定は無効です。`

Shared blocks reused verbatim from the Detector prefix: acceptable-variation list, severity
tests, enum labels, subtype list, span discipline. Then the naturalness/range **band
descriptors** for this age tier (rewritten per §8 — these are the only model-facing
descriptors left), the §6b JSON schema, and one verifier exemplar from rubric config.

### 7d. Verifier — user prompt

```
<REF label>: {gold_l2}
<LEARNER label>: {reproduction}
<PROPOSED label>: [{"i":0,"span_repro":[4,9],"span_ref":[4,13],"category":0,"source":1,
                    "severity":1,"subtype":6,"learner_form":"...","corrected_form":"..."}, ...]
```
Labels: EN `PROPOSED ERRORS` · ZH `待核错误` · JA `審査対象誤り`.

### 7e. Explainer — system prompt (written in the learner's **L1**)

- L1=EN: `You write feedback for a language learner, in English (the learner's native language). You receive the reference sentence, the learner's sentence, and a numbered list of confirmed errors: each has the learner's form, the corrected form, the error type, and the general rule (already shown to the learner separately). For each error write 1-2 short sentences explaining why the correction is right in this specific sentence — name the actual words involved and the meaning difference they make. Do not restate the general rule; do not introduce new corrections; do not contradict the given correction; do not mention scores or how many errors there are; do not praise or console. Write at a level a motivated teenager understands. Output ONLY JSON: {"explanations":[{"error_index":0,"text":"..."}]}. If you cannot add anything specific beyond the general rule for an error, omit that index.`
- L1=ZH: `你为语言学习者撰写反馈，使用中文（学习者的母语）。你将收到参考句、学习者的句子，以及带编号的已确认错误列表：每项包含学习者的写法、正确写法、错误类型和通用规则（已另行展示给学习者）。请为每个错误写1–2句话，解释为什么在这个具体句子中该改法是对的——点明涉及的具体词语及其造成的意义差别。不要复述通用规则；不要提出新的修改；不要与给定的改法矛盾；不要提及分数或错误数量；不要表扬或安慰。用积极上进的中学生能理解的语言书写。只输出JSON：{"explanations":[{"error_index":0,"text":"..."}]}。若某个错误你无法给出比通用规则更具体的内容，则省略该编号。`
- L1=JA: `あなたは語学学習者向けのフィードバックを、日本語（学習者の母語）で書きます。参照文、学習者の文、および番号付きの確定済み誤りリスト（各項目：学習者の表現、正しい表現、誤りの種類、一般規則——一般規則は別途学習者に表示済み）が与えられます。各誤りについて、この特定の文でなぜその訂正が正しいのかを1〜2文で説明してください——関係する実際の語句と、それが生む意味の違いを具体的に示すこと。一般規則の繰り返し、新たな訂正の提案、提示された訂正との矛盾、点数や誤り数への言及、称賛や慰めは禁止です。意欲的な中高生に伝わる言葉で書いてください。出力はJSONのみ：{"explanations":[{"error_index":0,"text":"..."}]}。一般規則以上に具体的なことが書けない誤りは、その番号を省略してください。`

**Explainer user prompt** (L1 labels): reference + learner text + numbered errors, each as
`{i, learner_form, corrected_form, subtype gloss in L1, rule template text}`.

## 8. Band descriptor authoring spec (v3 rewrite)

Pattern: **observable reader behaviour + typical error profile in parentheses**, so the words
match the §4 math. Distinct content per band; no frequency adverbs. Example (accuracy, EN,
tier 3):

- 1: `Multiple sentences break down grammatically; the reader must reconstruct what was meant. (Several major errors, or worse.)`
- 2: `Grammar errors force rereading in at least one place; a pattern (e.g. tense, agreement) is unreliable. (Roughly two major errors.)`
- 3: `One or two slips a native speaker would notice but read past without stopping. (One major or a few minor errors.)`
- 4: `Grammatically clean throughout; at most one trivial slip. (At most one minor error.)`

Under derived scoring, descriptors for accuracy/fidelity/understandability are **learner-facing
only** (feed-up + result explanation); only naturalness/range descriptors are still model-facing
(Verifier calibration). Full regeneration (6 tiers × 5 dims × 3 L2s × 4 bands, this pattern) is
an authoring task on the rubric v3 checklist.

## 9. Tier-0 precision fixes

1. Near-exact resolution requires **every** non-equal opcode to be normalization-class
   (punctuation/width/kana-only differences, checked against the same normalization tables) —
   `NEAR_EXACT_MISMATCH_RATIO` is retired. Any real lexical/grammatical diff → Detector (the
   result cache keeps repeat cost at zero).
2. `_safe_float(confidence, default=0.0)` on tier responses (v1 used 1.0 — a model that omits
   confidence should escalate, not sail through).
3. Tier-0 full-marks short-circuit is otherwise unchanged (exact match stays free).

**As-built (TASK-623, 2026-07-05).** The normalization-class gate keys on the diff **opcode
class** (`op != "equal"`), deliberately *not* on `grade_dictation`'s accuracy or per-token
`is_correct`. Rationale (the fuzzy-collapse gotcha): `grade_dictation._fuzzy_equal` marks a
≥4-char, Levenshtein-1 `replace` as correct and inflates `accuracy` to 1.0, but the opcode is
still emitted as `replace` — so gating on accuracy would let a real single-character edit
(e.g. `lazy`→`lazyy`) resolve at full marks. The op-class check is the **strict, non-fuzzy
diff** the gate needs: every non-`equal` op must fold to an identical string under
`_normalize_l2` + `services.dictation.tokenizer.normalize`, else escalate. Verified: a JA
は→が swap survives as a non-`equal` op (`normalize` folds が→か, ≠ は) and escalates.
*Known residual (out of scope, pre-existing in the reused dictation normalizer):* NFKD +
strip-Mn erases voiced-kana dakuten **before** the diff, so a は↔ば voicing swap collapses to
equal tokens and still resolves at Tier 0. Fixing that means a DT-specific normalizer (would
also alter dictation grading) — tracked separately, not part of TASK-623's ratio/confidence
scope.

## 10. Eval harness (Phase 0 — build BEFORE changing prompts)

- **Gold set per L2 (~30):** 10 clean passages (FP-rate measurement), 15 single-seeded-error
  (one per high-frequency subtype; seeded by scripted/LLM-assisted perturbation of real
  `dt_passage` golds, human-adjudicated), 5 natural multi-error (hand-written or captured
  real submissions, human-adjudicated error lists + bands).
- **Metrics:** span detection F1 (relaxed: ≥50% overlap counts), subtype accuracy, severity
  within-one agreement, clean-passage false-positive rate, per-dimension band QWK + exact/
  adjacent agreement, overall-band QWK.
- **Gate:** every dt_rubric/dt_taxonomy/prompt version bump runs the harness; results filed
  under `wiki/evaluations/dt-grading-<date>.md`; a regression blocks activation. Reuses
  model-arena's runner/pricing plumbing.

## 11. Rollout phases

- **Phase 0 — measure:** build gold sets + harness; baseline the shipped v1 grader. No product change.
- **Phase 1 — prompt upgrades, no schema change:** candidate regions + accounted-for rule,
  acceptable-variation block, reader-impact severity tests (still global/local at DB level),
  span discipline + substring repair, exemplars, is_mistake operationalization, confidence
  default fix, tier-0 near-exact tightening. Measure against baseline.

  **As-built (TASK-624, 2026-07-05).** Prompts upgraded **in place** on the existing tier1/tier2
  builders (roles NOT swapped — that is TASK-628): `prompts.py` gained the accounted-for,
  acceptable-variation, reader-impact-severity, span-discipline, is_mistake and exemplar blocks
  as module dicts (EN/ZH/JA; ZH/JA pending native review), plus a `regions` param on
  `build_user_prompt`; `grader_cascade` passes the tier-0 non-equal opcodes as candidate regions
  (`_diff_regions`, cap 20, text-shaped `{op,ref,repro}` — the tier-0 diff is token-level so
  exact char offsets aren't available, but the differing token text is a faithful hint) and
  threads the learner/reference texts into `_decode_error`, which now reconciles form↔span by
  substring search before dropping (`_reconcile_span_form`: repairs off-by-one spans, keeps
  empty-form omission/addition points, drops forms absent from the text — with a no-text
  fallback to structural validity for decode-only fixtures). The **accounted-for rule is the
  2-way Phase-1 variant** (error | acceptable-variation) — the highlights branch of §7a is
  deferred with highlights to TASK-628. The **severity reader-impact test replaces** the terse
  severity gloss and maps to the 2-level enum (0=global / 1=local); the MQM triad is TASK-625.
  Rubric config bumped **v2 → v4** (`migrations/dt_rubric_v4_seed.sql`): band descriptors +
  weights inherited byte-identical from v2 via jsonb `||`, adding only `acceptable_variation[l2]`
  (the FP lever) and `exemplars[l2]` (one worked example per L2; the error's subtype stored as a
  stable `subtype_slug` resolved to the live index at prompt-build time, so the exemplar stays
  correct across taxonomy reorderings). Version jumps to 4 to align rubric ↔ taxonomy (both v4);
  v3 skipped. Live single-active row verified (descriptors/weights identical to v2). Harness
  re-run: clean FP .30/.70/.40 → **.20/.00/.10** with span F1 + recall up on all three; the cost
  is a band-agreement (accuracy/overall) QWK give-back on EN/JA from variance compression — see
  [[evaluations/dt-grading-baseline-2026-07-05]] (TASK-624 update) for the full gate assessment.
- **Phase 2 — structural:** Detector/Verifier role split, severity-triad migration + backfill,
  taxonomy v5 (+ glosses/templates authoring), derived scoring + rubric config v3, provisional
  grades. Measure.

  **As-built (TASK-625, 2026-07-06) — severity triad only.** The vocabulary flip landed ahead of
  the role split / derived scoring (those stay TASK-627/628). `migrations/dt_severity_triad.sql`
  ran live as the two-step CHECK change of §3 (extend `dt_error_instance_severity_check` to the
  5-value union → backfill `local→minor` / `global→major` → `DO`-block verify zero old rows →
  tighten to `('minor','major','critical')`); 16 live rows migrated (14 minor / 2 major), 0
  critical. `prompts.SEVERITY_ENUM = ("minor","major","critical")`; `_SEVERITY_TESTS` restored to
  the full 3-level §7a reader-impact wording (EN/ZH/JA, ZH/JA pending native review); the dead
  2-level `_SEVERITY_GLOSS` and `_ENUM_LABELS["severity"]` (unused since TASK-624 replaced the
  terse gloss line with the reader-impact block) were **deleted**, not left stale.
  `_decode_error`'s range check widens to 3 automatically via `len(SEVERITY_ENUM)`. UI: three
  severity chips (`sev-global` high-impact styling now maps to critical+major; minor unstyled),
  i18n keys `dual_translation.severity.{minor,major,critical}` in all four locales incl. es.
  Harness: `run_dt_grading_eval::_exp_errors` now reads the fixtures' `severity_v2`, and the runner
  passes `em.SEVERITY_TRIAD_ORDER` so within-one severity agreement carries signal (trivial on the
  old 2-level scale). **Gotcha fixed:** the rubric v4 exemplar `severity` integers encoded the OLD
  index meaning (EN 1=local, ZH/JA 0=global); re-tagged in place on the live v4 row (no version
  bump, to avoid colliding with TASK-627's v5) to the triad meaning — EN 1→0 (minor, tense slip
  reads on), ZH/JA 0→1 (major, aspect/particle meaning change) — else the exemplars would teach the
  wrong severity the moment `SEVERITY_ENUM` flipped. Derived severity-weighted scoring stays
  unbuilt (TASK-627): this task changed only the vocabulary, not how bands are computed.

  **As-built (TASK-626, 2026-07-13) — taxonomy v5.** `migrations/dt_taxonomy_v5_seed.sql` ran live
  as the single active row (v4 deactivated). Per-L2 subtype sets grown to §5 sizes (EN 15 / JA 17 /
  ZH 17 = shared core 8 + per-target); new top-level **`subtype_meta`** carries per-subtype
  `{dimension, default_severity, treatable, cloze_suitable}` — `dimension` + `default_severity` are
  the §4 derived-scoring inputs (dimension straight from §5; `default_severity` speaks the TASK-625
  triad minor/major; `treatable`/`cloze_suitable` user-adjudicated, feed Feature-2's chooser). JA
  `particle` **split** into `particle_wa_ga` / `particle_case` (を・に・で・へ) / `particle_other` — a
  per-instance re-adjudication of the 8 JA particle gold items (は/が discourse ≠ case ≠ rest), not a
  bulk rename. `particle` kept in `subtype_meta` only (`historical_alias:true`, absent from every
  pairs list) so v1–v4 stored `dt_error_instance.subtype` rows still resolve under TASK-627; all other
  v4 subtypes survive verbatim (live rows use only word_choice/omission/word_order/aspect_marker). The
  15 new subtypes' ZH/JA glosses+templates are AI-drafted, flagged for native review in the migration
  header (ADR-019 pattern); the 17 carry-overs reuse v4 strings. Totality (every subtype → exactly one
  of accuracy/fidelity/naturalness) + no-slug-fallback (via the real `_resolve_subtypes` /
  `render_explanation`) + alias resolution guarded by `tests/test_dual_translation_taxonomy_v5.py` (28).
  Gold fixtures re-tagged to v5 names (harness measures subtype accuracy string-comparing fixture
  subtype ↔ live-taxonomy decode, so both sides are v5). **Harness hardened first** (§10): a bounded
  retry+backoff + `--resume` checkpoint in `run_dt_grading_eval.py` (`tests/test_dt_eval_harness_retry.py`)
  — behaviour-neutral when the network is fine, and it recovered the JA run from a mid-run
  `getaddrinfo` DNS failure (the exact TASK-625 orphaning cause). Rubric untouched (stays v4;
  taxonomy-only bump). Harness re-run + gate assessment in [[evaluations/dt-grading-baseline-2026-07-05]]
  (TASK-626 update): subtype accuracy up on EN/JA, a finer-tagset dip on ZH, detection (span F1) + clean
  FP held on all three, and the 625-deferred **JA floor re-confirmed**. Derived severity-weighted scoring
  stays TASK-627.
- **Phase 3 — feedback UX:** Explainer call + 3-layer explanations (ADR-019), highlights UI,
  per-dimension "because" lines, "next focus" feed-forward into Feature 2.

## 12. Security / cost considerations

- Explainer output is model prose rendered to the learner: length-capped, form-mention
  validated, HTML-escaped by the existing UI (`escapeHtml` in `dual_translation.js`), and
  carries no score authority. Prompt-injection surface is limited to the learner's own
  reproduction text — the Explainer can only affect its own explanation text.
- Cost: Verifier input grows by the proposed-error list (~50–150 tokens); Explainer adds ~300
  in / ~40×n out on error-bearing submissions only, on the cheap slug. Cached prefixes are
  unchanged in structure; exemplars grow them but stay byte-stable. Re-scoring on rubric bumps
  is now free (no model), replacing v1's "bulk re-score" batch cost.

## 13. Testing strategy

- Unit: derived-scoring pure functions (penalty sums, thresholds, renormalization on missing
  judgments); verdict merge (confirm/reject/adjust/default-confirm, unknown index); substring
  repair; explainer validation (length/mention/score-pattern).
- Contract: every persisted error has spans matching forms; provisional flag set on any tier
  failure; rejected errors never persisted.
- Prompt cache: prefix byte-stability per (L2, call, rubric+taxonomy versions).
- Harness: §10 is the integration test.

## Related Pages
- [[algorithms/evidence-first-grading]] — prose + research foundations
- [[algorithms/translation-grading-cascade.tech]] — v1 (shipped) spec this supersedes-by-design
- [[decisions/ADR-019-evidence-first-scoring]] — decision record
- [[features/dual-translation.tech]] · [[features/dual-translation-remediation.tech]]
- [[business-rules/translation-error-taxonomy]]
