"""L2-only prompt builders for the dual-translation grading cascade (TASK-606).

Per the repo override of the brief's §4.4 (see ADR-015 + the cascade doc): grading
prompts are **target-language (L2) only — no English** instructional text, and the
model must emit **numerical indices**, never prose. The three instructional template
strings below (EN/ZH/JA) are first drafts authored by an AI assistant, not a native
speaker of ZH/JA — they are functionally complete (the model only needs to follow the
JSON-shape instructions) but should get native-speaker linguistic review before this
ships to real users, same as any other ZH/JA content in this pipeline pending TASK-616.

JSON field names (`scores`, `errors`, `span_repro`, `category`, ...) stay in English in
every prompt regardless of L2 — they are protocol/schema tokens for the Python parser on
the other end, not natural-language content, so they don't violate the L2-only rule any
more than an XML tag name would.

Two prompt halves, matching `services.model_arena.llm_runner.call_model_with_usage`'s
`(prompt, system_prompt)` split:

  build_system_prompt(...)  — the cacheable prefix: rubric band descriptors for this
      age tier + the subtype/category/source/severity schema + JSON-shape instructions.
      Byte-stable for a given (tier, l2_code, age_tier, rubric config, subtypes) — the
      *content* varies only when dt_rubric_version/dt_taxonomy_version bump, never per
      submission. This is "the biggest lever" (prompt caching) from the cascade doc.
  build_user_prompt(...)    — the per-submission suffix: just the gold + reproduction
      text. Never cached, always tiny.

Deliberately excludes the learner's L1: tagging an error's `source` axis as numbered
indices and reading band descriptors needs only the L2 + age tier, so the same prefix
is shared across every learner studying that L2 regardless of L1 — maximizing cache
reuse today. Once TASK-616 seeds genuinely per-directed-pair subtype tables (interlingual
classification is L1-dependent per the taxonomy doc), `subtypes` will start varying by
L1 too and the cache will correctly narrow to per-(L1, L2) prefixes at that point — not a
regression, just the cache boundary tracking the data that's actually L1-specific.

Exception (taxonomy v6 only, string review 2026-10-07): the word_choice
explanation_variant line names the learner's L1 (`l1_code=` on the Detector/Verifier
builders), because its false_synonym variant ("a word the learner's L1 translates the
same way") cannot be judged without it. Under v6 the cached prefix is therefore
per-(L1, L2); every v5 prompt ignores `l1_code` and stays byte-identical.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

# Shared cross-linguistic schema (category/source/severity). These are NOT versioned
# taxonomy data — they are already hardcoded as CHECK constraints on the live
# `dt_error_instance` table (migrations/dual_translation_groundwork.sql, TASK-602), so
# fixing them as code constants here just mirrors a constraint the DB already enforces.
# Only `subtype` is the open-ended, per-pair axis that must come from dt_taxonomy_version.
CATEGORY_ENUM: tuple[str, ...] = ("grammatical", "lexical", "pragmatic_expressional")
SOURCE_ENUM: tuple[str, ...] = ("interlingual", "intralingual")
# TASK-625: MQM severity triad (new indices 0=minor / 1=major / 2=critical),
# replacing the 2-level global/local enum. Reader-impact tests live in
# _SEVERITY_TESTS below; the DB CHECK is migrations/dt_severity_triad.sql.
# _decode_error's range check widens automatically via len(SEVERITY_ENUM).
SEVERITY_ENUM: tuple[str, ...] = ("minor", "major", "critical")

# Which rubric dimensions each tier is responsible for scoring (dual-translation.tech.md
# "Rubric (Feature 1)" — primary grader tier column).
TIER_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "tier1": ("accuracy", "range"),
    "tier2": ("understandability", "fidelity", "naturalness"),
}

_REQUIRED_JSON_KEYS = ("confidence", "scores", "errors")
_REQUIRED_ERROR_KEYS = (
    "span_repro", "span_ref", "category", "source", "severity",
    "subtype", "learner_form", "corrected_form", "confidence",
)

# The band scale every prompt here asks for (_SCORE_INSTRUCTION's "1-4 scale",
# _example_schema's "<1-4>") and that validate_raw_response holds responses to.
# MAX_BAND mirrors tier0.MAX_BAND; the two are asserted equal in
# tests/test_dual_translation_grader_cascade.py rather than imported, so this
# module stays a dependency-free string builder.
MIN_BAND = 1
MAX_BAND = 4

# ---------------------------------------------------------------------------
# Per-language instructional text (the only thing that's hand-authored per L2)
# ---------------------------------------------------------------------------

_DIMENSION_NAMES: dict[str, dict[str, str]] = {
    "en": {
        "accuracy": "accuracy (grammatical correctness)",
        "range": "range (articulateness / sophistication)",
        "understandability": "understandability (would a native speaker grasp the meaning)",
        "fidelity": "fidelity (meaning and register preserved)",
        "naturalness": "naturalness (how native it sounds)",
    },
    "zh": {
        "accuracy": "准确性（语法正确性）",
        "range": "丰富度（表达的成熟度与多样性）",
        "understandability": "可理解性（母语者能否理解原意）",
        "fidelity": "忠实度（意义与语域是否保留）",
        "naturalness": "自然度（是否像母语者的表达）",
    },
    "ja": {
        "accuracy": "正確さ（文法的な正しさ）",
        "range": "表現の幅（表現の成熟度・多様性）",
        "understandability": "理解可能性（母語話者が意味を理解できるか）",
        "fidelity": "忠実度（意味と文体・敬語レベルが保たれているか）",
        "naturalness": "自然さ（母語話者らしい表現かどうか）",
    },
}

_INSTRUCTION_HEADER: dict[str, str] = {
    "en": (
        "You are a precise grading assistant for a language-learning app. You will be "
        "given a REFERENCE text and a LEARNER text that attempts to reproduce it. Compare "
        "them and find only errors relevant to the dimensions below. Output ONLY a single "
        "JSON object — no prose, no explanation, no text before or after it."
    ),
    "zh": (
        "你是一个语言学习应用程序中的精确评分助手。系统会给你一段【参考译文】和一段【学习者译文】"
        "（学习者尝试复现参考译文）。请比较两者，只查找与下列维度相关的错误。"
        "只输出一个JSON对象——不要任何说明、解释，JSON对象前后不要有任何文字。"
    ),
    "ja": (
        "あなたは語学学習アプリの厳密な採点アシスタントです。「参照文」と、それを再現しようとした"
        "「学習者文」が与えられます。両者を比較し、以下の観点に関係する誤りのみを見つけてください。"
        "出力は単一のJSONオブジェクトのみとし、説明文やJSON以外の文字を前後に含めないでください。"
    ),
}

_SCORE_INSTRUCTION: dict[str, str] = {
    "en": "Score the learner text on a 1-4 scale for each of these dimensions: {dims}.",
    "zh": "请按1到4分的等级，针对以下每个维度对学习者译文打分：{dims}。",
    "ja": "学習者文について、以下の各観点を1〜4の評価で採点してください：{dims}。",
}

_BAND_DESCRIPTOR_LABEL: dict[str, str] = {
    "en": "Band descriptors for this dimension at this learner's age tier",
    "zh": "该维度在此学习者年龄层级下的评分等级说明",
    "ja": "この学習者の年齢層におけるこの観点の評価基準",
}

_SUBTYPE_LIST_LABEL: dict[str, str] = {
    "en": "Error subtypes — when tagging an error, use its 0-based INDEX in this list, not its name:",
    "zh": "错误子类型——标注错误时请使用该子类型在下列列表中的索引（从0开始），而不是名称：",
    "ja": "誤りのサブタイプ——誤りに印を付ける際は、名前ではなく以下リストの0始まりのインデックスを使ってください：",
}

# Only category + source get a terse "0=x, 1=y" enum line here; severity is
# taught via the reader-impact _SEVERITY_TESTS block (TASK-624/625), so it has
# no entry in this dict and no gloss tuple.
_ENUM_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "category": "category (0={c0}, 1={c1}, 2={c2})",
        "source": "source (0={s0}, 1={s1})",
    },
    "zh": {
        "category": "类别 category（0={c0}，1={c1}，2={c2}）",
        "source": "来源 source（0={s0}，1={s1}）",
    },
    "ja": {
        "category": "種別 category（0={c0}、1={c1}、2={c2}）",
        "source": "起因 source（0={s0}、1={s1}）",
    },
}

# Glosses for the two fixed cross-linguistic enums shown as terse index lines
# (CATEGORY_ENUM/SOURCE_ENUM — 5 values total). These are finite and stable, so
# — unlike `subtype`, which is open-ended per-pair taxonomy data — they're
# authored here directly rather than sourced from dt_taxonomy_version. The
# English enum *value* (e.g. "grammatical") is a Python-side decode key only;
# the model never sees it in a ZH/JA prompt, only the gloss below. SEVERITY_ENUM
# has no gloss tuple: its reader-impact wording lives in _SEVERITY_TESTS.
_CATEGORY_GLOSS: dict[str, tuple[str, str, str]] = {
    "en": ("grammatical", "lexical", "pragmatic/expressional"),
    "zh": ("语法类", "词汇类", "语用/表达类"),
    "ja": ("文法的", "語彙的", "プラグマティック・表現的"),
}
_SOURCE_GLOSS: dict[str, tuple[str, str]] = {
    "en": ("interlingual (L1 transfer)", "intralingual (within-L2 overgeneralisation)"),
    "zh": ("语际迁移（受母语影响）", "语内泛化（目标语内部的过度泛化）"),
    "ja": ("言語間転移（母語の影響）", "言語内過剰一般化（目標言語内部での過剰一般化）"),
}

_JSON_SHAPE_INSTRUCTION: dict[str, str] = {
    "en": (
        "For every error found, report: span_repro [start,end] (character offsets into "
        "the LEARNER text), span_ref [start,end] (character offsets into the REFERENCE "
        "text), category, source, severity, subtype (the index described above), "
        "learner_form (exact substring the learner wrote), corrected_form (exact "
        "substring from the reference it should be), confidence (0.0-1.0), and "
        "is_mistake (true only if this looks like a self-corrected slip rather than a "
        "knowledge gap; false otherwise). Respond with exactly this JSON shape:\n{schema}"
    ),
    "zh": (
        "对每个找到的错误，请报告：span_repro [开始,结束]（在【学习者文本】中的字符偏移量）、"
        "span_ref [开始,结束]（在【参考文本】中的字符偏移量）、category、source、severity、"
        "subtype（上文所述的索引）、learner_form（学习者所写的确切片段）、corrected_form"
        "（参考文本中应替换为的确切片段）、confidence（0.0到1.0）、is_mistake（仅当这看起来是"
        "自我纠正的失误而非知识缺口时为true，否则为false）。请严格按以下JSON结构回复：\n{schema}"
    ),
    "ja": (
        "見つかった各誤りについて、span_repro [開始,終了]（「学習者文」内の文字オフセット）、"
        "span_ref [開始,終了]（「参照文」内の文字オフセット）、category、source、severity、"
        "subtype（上記のインデックス）、learner_form（学習者が書いた箇所の正確な文字列）、"
        "corrected_form（参照文中で置き換えるべき正確な文字列）、confidence（0.0〜1.0）、"
        "is_mistake（知識不足ではなく自己訂正可能な一時的なミスに見える場合のみtrue、それ以外は"
        "false）を報告してください。必ず以下のJSON形式で回答してください：\n{schema}"
    ),
}

_USER_PROMPT_LABELS: dict[str, tuple[str, str]] = {
    "en": ("REFERENCE", "LEARNER"),
    "zh": ("参考译文", "学习者译文"),
    "ja": ("参照文", "学習者文"),
}

# Label for the tier-0 candidate-regions block in the user prompt (TASK-624 §7b).
_REGION_LABEL: dict[str, str] = {
    "en": "CANDIDATE REGIONS",
    "zh": "候选区域",
    "ja": "候補領域",
}

# ---------------------------------------------------------------------------
# TASK-624 Phase-1 system-prompt blocks (false-positive-reduction levers).
# New module dicts, same pattern as _INSTRUCTION_HEADER: byte-stable, versioned
# in code (the *content* the model reads that varies per rubric/taxonomy lives
# in dt_rubric_version.config — acceptable_variation + exemplars). ZH/JA strings
# are AI-authored first drafts flagged for native review (same caveat as the
# module docstring). Authored to the wiki tech spec §7a; the accounted-for rule
# is the 2-way Phase-1 variant (no highlights — highlights ship in TASK-628).
# ---------------------------------------------------------------------------

# Accounted-for rule: every candidate region is either an error or acceptable
# variation. (Detector §7a, minus the highlights branch not present this phase.)
_ACCOUNTED_FOR: dict[str, str] = {
    "en": (
        "Every candidate region must be accounted for in exactly one way: (a) reported as an "
        "error, or (b) recognized as acceptable variation and left unreported. Candidate regions "
        "are hints from a character diff, not boundaries — merge adjacent regions that form one "
        "error, and still scan the rest of the text for errors the diff cannot expose."
    ),
    "zh": (
        "每个候选区域必须以且仅以下列一种方式处理：(a) 报告为错误；(b) 判定为可接受的变体并不予报告。"
        "候选区域只是字符级对比给出的提示，不是边界——相邻区域若构成同一个错误应合并处理，"
        "同时仍需检查全文，找出对比无法暴露的错误。"
    ),
    "ja": (
        "各候補領域は、必ず次のいずれか一つとして処理してください：(a) 誤りとして報告する、"
        "(b) 許容される言い換えと判断して報告しない。候補領域は文字単位の差分による手がかりにすぎず、"
        "境界ではありません——隣接する領域が一つの誤りを構成する場合は統合し、"
        "差分では検出できない誤りがないか全文も確認してください。"
    ),
}

# Acceptable-variation label; the per-L2 bullets come from rubric config
# (acceptable_variation[l2]) so they version with the rubric — the main FP lever.
_ACCEPTABLE_VARIATION_LABEL: dict[str, str] = {
    "en": "The following are NOT errors (acceptable variation) — never report them:",
    "zh": "以下情况不是错误（属于可接受的变体）——切勿报告：",
    "ja": "以下は誤りではありません（許容される言い換え）——決して報告しないでください：",
}

# Reader-impact severity tests — the MQM triad (SEVERITY_ENUM = ('minor','major',
# 'critical'); indices 0=minor / 1=major / 2=critical). TASK-625 restores the full
# 3-level §7a wording (TASK-624 shipped a 2-level global/local down-mapping while
# the DB CHECK was still global/local). Replaces the terse severity gloss line.
_SEVERITY_TESTS: dict[str, str] = {
    "en": (
        "Severity — apply this reader-impact test to each error: minor (0) = a native reader "
        "notices but reads on without hesitation; meaning fully intact. major (1) = a native "
        "reader hesitates or must reread; the form is plainly wrong but the intended meaning "
        "survives. critical (2) = the meaning is lost, changed or inverted (wrong actor, dropped "
        "negation, missing essential information), or the register failure would cause real "
        "offence."
    ),
    "zh": (
        "严重程度——对每个错误应用以下读者影响测试：轻微（0）＝母语读者会注意到，但不会停顿，"
        "意义完全保留；较重（1）＝母语读者会迟疑或需要重读，形式明显有误，但原意仍可理解；"
        "严重（2）＝意义丢失、改变或颠倒（如动作主体错误、否定丢失、关键信息缺失），"
        "或语域失误会造成真正的冒犯。"
    ),
    "ja": (
        "重大度——各誤りに次の読者影響テストを適用してください：軽微（0）＝母語話者は気づくが、"
        "止まらずに読み進められ、意味は完全に保たれる。重大（1）＝母語話者がつまずく、"
        "または読み返す必要があり、形は明らかに誤っているが意図された意味は伝わる。"
        "致命的（2）＝意味が失われる・変わる・逆転する（動作主の誤り、否定の欠落、"
        "必須情報の欠落など）、または敬語の失敗が実際に失礼にあたる。"
    ),
}

# Span discipline — the forms must be exact substrings at their spans, else the
# report is discarded (Detector §7a, verbatim).
_SPAN_DISCIPLINE: dict[str, str] = {
    "en": (
        "Spans are character offsets: span_repro into the LEARNER text, span_ref into the "
        "REFERENCE text. learner_form must be the exact substring of the LEARNER text at "
        "span_repro (copy it character-for-character); corrected_form must be the exact substring "
        "of the REFERENCE text at span_ref. Reports whose forms do not match their spans are "
        "discarded, so verify each one."
    ),
    "zh": (
        "跨度为字符偏移量：span_repro 指向【学习者译文】，span_ref 指向【参考译文】。"
        "learner_form 必须与学习者译文中 span_repro 处的子串逐字一致；"
        "corrected_form 必须与参考译文中 span_ref 处的子串逐字一致。"
        "形式与跨度不一致的报告将被丢弃，请逐一核对。"
    ),
    "ja": (
        "スパンは文字オフセットです：span_repro は「学習者文」内、span_ref は「参照文」内を指します。"
        "learner_form は学習者文の span_repro の位置の部分文字列と一字一句一致していなければなりません。"
        "corrected_form は参照文の span_ref の位置の部分文字列と一致していなければなりません。"
        "形式がスパンと一致しない報告は破棄されるため、必ず確認してください。"
    ),
}

# is_mistake, operationalized (Corder slip vs knowledge gap) — Detector §7a.
_IS_MISTAKE: dict[str, str] = {
    "en": (
        "is_mistake: true only if the same element is used correctly elsewhere in the learner "
        "text (a slip, not a knowledge gap); otherwise false."
    ),
    "zh": (
        "is_mistake：仅当同一语言点在学习者译文其他位置使用正确时（属于笔误而非知识缺口）为 true，"
        "否则为 false。"
    ),
    "ja": (
        "is_mistake：同じ言語項目が学習者文の他の箇所では正しく使われている場合のみ true"
        "（知識不足ではなく一時的なミス）。それ以外は false。"
    ),
}

# Label preceding the one worked exemplar (exemplar body comes from rubric config).
_EXEMPLAR_LABEL: dict[str, str] = {
    "en": "Worked example:",
    "zh": "示例：",
    "ja": "例：",
}


def build_system_prompt(
    tier: str,
    l2_code: str,
    rubric_cfg: dict,
    age_tier: int,
    subtypes: list[str],
    *,
    subtype_labels: list[str] = None,
    extra_dims: tuple[str, ...] = (),
) -> str:
    """Build the cacheable, L2-only instructional prefix for one cascade tier.

    Args:
        tier: 'tier1' or 'tier2' — selects TIER_DIMENSIONS' base dimension set.
        l2_code: ISO 639-1 of the language being graded ('zh'/'en'/'ja') — also
            the language this entire prompt is written in.
        rubric_cfg: the active dt_rubric_version.config (see
            wiki/algorithms/translation-grading-cascade.tech.md for the documented
            shape). Missing band-descriptor entries degrade gracefully (omitted,
            not a crash) — dt_rubric_version content (TASK-604) may not exist yet.
        age_tier: 1-6, selects which band descriptors to quote.
        subtypes: the resolved per-pair (or L2-baseline) subtype name list — the
            canonical English identifier slugs (dt_error_instance.subtype values).
            The model is told to report the 0-based index into this list; this
            exact list (by position) is what the caller decodes the index back
            against, regardless of what label text was shown for each entry.
        subtype_labels: what to actually show the model for each subtype, in
            l2_code (e.g. a dt_taxonomy_version `subtype_glosses` lookup) — must
            be the same length/order as `subtypes`. Defaults to `subtypes`
            itself (the bare English slug) when not given, which is a stopgap
            for ZH/JA prompts pre-TASK-616/604 content: it works, but the model
            is then reading a raw English identifier inside an otherwise L2-only
            prompt. grader_cascade.py resolves real glosses once they exist.
        extra_dims: additional dimensions to also grade in this call (the Tier 2
            escalation path also re-checks accuracy/range on low Tier 1
            confidence or a large Tier 0 diff — see grader_cascade.py).
    """
    if l2_code not in _INSTRUCTION_HEADER:
        raise ValueError(f"No instructional template authored for l2_code={l2_code!r}")
    if tier not in TIER_DIMENSIONS:
        raise ValueError(f"Unknown tier {tier!r}; expected one of {list(TIER_DIMENSIONS)}")

    dims = asked_dimensions(tier, extra_dims)
    names = _DIMENSION_NAMES[l2_code]
    dims_text = "; ".join(names.get(d, d) for d in dims)

    parts = [
        _INSTRUCTION_HEADER[l2_code],
        _SCORE_INSTRUCTION[l2_code].format(dims=dims_text),
        # TASK-624: accounted-for rule (references the user-prompt candidate regions).
        _ACCOUNTED_FOR[l2_code],
    ]

    # TASK-624: acceptable-variation block — the main FP lever. Bullets are
    # rubric-versioned (config), so the block is omitted (not crashed) until a
    # rubric carrying acceptable_variation for this L2 is active.
    variation_block = _acceptable_variation_text(rubric_cfg, l2_code)
    if variation_block:
        parts.append(variation_block)

    descriptor_block = _band_descriptors_text(rubric_cfg, dims, age_tier, l2_code)
    if descriptor_block:
        parts.append(f"{_BAND_DESCRIPTOR_LABEL[l2_code]}:\n{descriptor_block}")

    enum_lines = _ENUM_LABELS[l2_code]
    cat_gloss = _CATEGORY_GLOSS[l2_code]
    src_gloss = _SOURCE_GLOSS[l2_code]
    parts.append(enum_lines["category"].format(c0=cat_gloss[0], c1=cat_gloss[1], c2=cat_gloss[2]))
    parts.append(enum_lines["source"].format(s0=src_gloss[0], s1=src_gloss[1]))
    # TASK-624: reader-impact severity tests replace the terse severity gloss.
    parts.append(_SEVERITY_TESTS[l2_code])

    labels = subtype_labels if subtype_labels is not None else subtypes
    subtype_lines = "\n".join(f"{i}: {label}" for i, label in enumerate(labels))
    parts.append(f"{_SUBTYPE_LIST_LABEL[l2_code]}\n{subtype_lines}")

    # TASK-624: span discipline + operationalized is_mistake.
    parts.append(_SPAN_DISCIPLINE[l2_code])
    parts.append(_IS_MISTAKE[l2_code])

    schema = _example_schema(dims)
    parts.append(_JSON_SHAPE_INSTRUCTION[l2_code].format(schema=schema))

    # TASK-624: one worked exemplar per (L2, tier), from rubric config. Placed
    # after the schema; scores are projected to this call's dims. Omitted (not
    # crashed) until a rubric carrying exemplars for this L2 is active.
    exemplar_block = _exemplar_text(rubric_cfg, l2_code, dims, subtypes)
    if exemplar_block:
        parts.append(exemplar_block)

    return "\n\n".join(parts)


def build_user_prompt(
    l2_code: str,
    gold_l2: str,
    reproduction: str,
    regions: list[dict] | None = None,
) -> str:
    """Build the small, never-cached per-submission suffix.

    Args:
        regions: tier-0 non-equal diff opcodes as candidate regions (TASK-624
            §7b) — a list of ``{"op","ref","repro"}`` dicts, capped by the
            caller (grader_cascade). Rendered as a compact JSON list under the
            per-L2 CANDIDATE REGIONS label. ``None``/empty omits the line, so
            the user prompt is unchanged for callers that pass no regions.
    """
    ref_label, learner_label = _USER_PROMPT_LABELS.get(l2_code, _USER_PROMPT_LABELS["en"])
    lines = [f"{ref_label}: {gold_l2}", f"{learner_label}: {reproduction}"]
    if regions:
        region_label = _REGION_LABEL.get(l2_code, _REGION_LABEL["en"])
        lines.append(f"{region_label}: {json.dumps(regions, ensure_ascii=False)}")
    return "\n".join(lines)


def asked_dimensions(tier: str, extra_dims: tuple[str, ...] = ()) -> tuple[str, ...]:
    """The rubric dimensions this tier's prompt asks the model to score.

    Single source of truth for both halves of the contract: build_system_prompt
    renders the score instruction from this, and validate_raw_response holds the
    response to it. Sharing one definition is what keeps validation from drifting
    away from what was actually asked (TASK-635).
    """
    if tier not in TIER_DIMENSIONS:
        raise ValueError(f"Unknown tier {tier!r}; expected one of {list(TIER_DIMENSIONS)}")
    base = TIER_DIMENSIONS[tier]
    return tuple(base) + tuple(d for d in extra_dims if d not in base)


def validate_raw_response(payload: dict, required_dims: tuple[str, ...] = ()) -> bool:
    """Structural check on a parsed (already-json.loads'd) tier response.

    Checks the outer JSON shape, and — given `required_dims` (normally
    `asked_dimensions(tier, extra_dims)`) — that every dimension the tier was
    asked to score came back with a usable band. An incomplete `scores` object
    is a failed response, not a partial one: grader_cascade defaults any missing
    dimension to MAX_BAND, so accepting `scores: {}` alongside a high
    self-reported confidence silently awarded a perfect grade *and* suppressed
    the Tier-2 re-check, with fell_open=False and nothing in the trace. Failing
    here routes it down the same fall-open path as malformed JSON, which both
    records the reason and (via the 0.0 confidence default) forces the re-check
    — the scores-shaped half of the leniency hole TASK-623 closed for confidence
    (TASK-635).

    Still deliberately shallow about errors[]: per-error field validation (span
    bounds, enum range, non-empty learner_form/corrected_form) happens in
    grader_cascade._decode_error, where a single bad error can be dropped without
    discarding the whole response.
    """
    if not isinstance(payload, dict):
        return False
    if not all(k in payload for k in _REQUIRED_JSON_KEYS):
        return False
    if not isinstance(payload["scores"], dict) or not isinstance(payload["errors"], list):
        return False
    return not missing_score_dims(payload, required_dims)


def missing_score_dims(payload: dict, required_dims: tuple[str, ...]) -> list[str]:
    """Which of `required_dims` the response failed to score usably — missing
    entirely, non-numeric, or out of band range. Named separately from
    validate_raw_response so the caller can put the offending dimensions in the
    grader_trace reason rather than reporting a generic shape failure."""
    scores = payload.get("scores") if isinstance(payload, dict) else None
    if not isinstance(scores, dict):
        return list(required_dims)
    return [dim for dim in required_dims if not _is_valid_band(scores.get(dim))]


def error_has_required_keys(raw_error: dict) -> bool:
    return isinstance(raw_error, dict) and all(k in raw_error for k in _REQUIRED_ERROR_KEYS)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _is_valid_band(value) -> bool:
    """True iff `value` is a band the model could legitimately have scored: a
    number within [MIN_BAND, MAX_BAND].

    Non-integers (a 3.5 the prompt never asked for) are accepted and left to
    grader_cascade._clip_band to round, deliberately. Rejecting a dimension
    here makes it fall open to MAX_BAND, so being strict about a value that
    rounds to a real band would be *more* lenient than accepting it — the exact
    inversion this task exists to close. Only genuinely unusable values
    (missing, non-numeric, or outside the scale, all of which _clip_band would
    otherwise silently turn into a perfect band) fail.
    """
    if isinstance(value, bool):  # JSON true/false is not a band; float(True) == 1.0
        return False
    try:
        band = float(value)
    except (TypeError, ValueError):
        return False
    return MIN_BAND <= band <= MAX_BAND


def _band_descriptors_text(rubric_cfg: dict, dims: tuple[str, ...], age_tier: int, l2_code: str) -> str:
    """Quote whatever band-descriptor text dt_rubric_version has for these dims
    at this age tier. Returns '' (and the caller omits the section entirely) for
    any piece that's missing — TASK-604 content may be partial or not yet
    seeded; a missing descriptor degrades calibration quality, it must never
    crash the cascade."""
    descriptors = (rubric_cfg or {}).get("band_descriptors", {})
    tier_block = descriptors.get(str(age_tier), {})
    lines = []
    for dim in dims:
        per_lang = tier_block.get(dim, {})
        bands = per_lang.get(l2_code) if isinstance(per_lang, dict) else None
        if not bands:
            continue
        band_text = "; ".join(f"{band}={text}" for band, text in sorted(bands.items()))
        lines.append(f"- {dim}: {band_text}")
    return "\n".join(lines)


def _acceptable_variation_text(rubric_cfg: dict, l2_code: str) -> str:
    """Render the acceptable-variation block from rubric config
    (config['acceptable_variation'][l2_code] — a list of L2-authored bullets).
    Returns '' (block omitted) when the active rubric carries no list for this
    L2 — same graceful degradation as band descriptors (TASK-624)."""
    variation = (rubric_cfg or {}).get("acceptable_variation", {})
    bullets = variation.get(l2_code) if isinstance(variation, dict) else None
    if not bullets:
        return ""
    lines = "\n".join(f"- {b}" for b in bullets)
    return f"{_ACCEPTABLE_VARIATION_LABEL[l2_code]}\n{lines}"


def _slug_index(enum_values, slug) -> int | None:
    """Resolve a stored slug to its index in the live ordered list, or None.

    The inverse of ``grader_cascade._enum_lookup`` (index -> slug). It lives here
    rather than next to its twin because grader_cascade imports this module, not
    the reverse.

    Returns None — never a fallback index — when the slug is missing or absent
    from the list. Every index in this schema is a *legal* value, so guessing one
    doesn't fail, it silently relabels: index 0 of the JA subtype list is
    `omission`, so a missed `particle_wa_ga` taught every JA prompt that a HA/GA
    swap is an omission (TASK-637, ADR-020). Callers must skip, not substitute.
    """
    if not isinstance(slug, str):
        return None
    try:
        return list(enum_values).index(slug)
    except (ValueError, TypeError):
        return None


def _exemplar_text(rubric_cfg: dict, l2_code: str, dims: tuple[str, ...], subtypes: list[str]) -> str:
    """Render one worked exemplar from rubric config
    (config['exemplars'][l2_code]).

    The stored exemplar carries its error's subtype and severity as stable slugs
    (``subtype_slug`` / ``severity_slug``, not indices); this resolves them
    against the live ``subtypes`` list and ``SEVERITY_ENUM`` so the shown indices
    always match the lists the model is reading above — byte-stable for a given
    (l2, dims, taxonomy version). ``scores`` are projected to this call's
    ``dims``.

    Returns '' — the prompt simply omits the worked-example block — when the
    active rubric carries no exemplar for this L2 (TASK-624), *or* when either
    slug fails to resolve (TASK-637). A missing worked example is strictly better
    than a silently wrong one: the former costs the model a hint, the latter
    actively teaches it the wrong label. The skip is logged because an
    unresolvable slug means the rubric and taxonomy rows have drifted, which is a
    seeding bug, not a runtime condition."""
    exemplars = (rubric_cfg or {}).get("exemplars", {})
    exemplar = exemplars.get(l2_code) if isinstance(exemplars, dict) else None
    if not exemplar:
        return ""

    error = dict(exemplar.get("error", {}))
    subtype_slug = error.pop("subtype_slug", None)
    severity_slug = error.pop("severity_slug", None)
    subtype_index = _slug_index(subtypes, subtype_slug)
    severity_index = _slug_index(SEVERITY_ENUM, severity_slug)
    if subtype_index is None or severity_index is None:
        logger.warning(
            "dual_translation.prompts: dropping the %s exemplar from the prompt — "
            "subtype_slug=%r resolved to %r against the active taxonomy, severity_slug=%r "
            "resolved to %r against SEVERITY_ENUM. The rubric and taxonomy rows have "
            "drifted (ADR-020); re-apply migrations/dt_rubric_v4_seed.sql or check which "
            "dt_taxonomy_version row is active. Prompt is degraded, not wrong.",
            l2_code, subtype_slug, subtype_index, severity_slug, severity_index,
        )
        return ""
    error["subtype"] = subtype_index
    error["severity"] = severity_index

    exemplar_scores = exemplar.get("scores", {}) or {}
    scores = {d: exemplar_scores[d] for d in dims if d in exemplar_scores}
    obj = {
        "confidence": exemplar.get("confidence", error.get("confidence", 0.9)),
        "scores": scores,
        "errors": [error],
    }

    ref_label, learner_label = _USER_PROMPT_LABELS.get(l2_code, _USER_PROMPT_LABELS["en"])
    body = (
        f"{ref_label}: {exemplar.get('reference', '')}\n"
        f"{learner_label}: {exemplar.get('learner', '')}\n"
        f"→ {json.dumps(obj, ensure_ascii=False)}"
    )
    return f"{_EXEMPLAR_LABEL[l2_code]}\n{body}"


def _example_schema(dims: tuple[str, ...]) -> str:
    scores_example = {d: "<1-4>" for d in dims}
    schema = {
        "confidence": "<0.0-1.0>",
        "scores": scores_example,
        "errors": [
            {
                "span_repro": [0, 0],
                "span_ref": [0, 0],
                "category": 0,
                "source": 0,
                "severity": 0,
                "subtype": 0,
                "learner_form": "...",
                "corrected_form": "...",
                "confidence": "<0.0-1.0>",
                "is_mistake": False,
            }
        ],
    }
    return json.dumps(schema, ensure_ascii=False)


# ===========================================================================
# TASK-628 — Evidence-First Grading v2 (Detector / Verifier prompt builders).
#
# The v2 flow replaces the tier1/tier2 "band + detect" prompts with two roles:
#   Detector — exhaustive detection (errors + highlights), NO scores (§6a/§7a-b).
#   Verifier — verdicts (confirm/reject/adjust) on the detector's proposals,
#              added_errors it missed, and naturalness/range judgments with
#              mandatory evidence spans (§6b/§7c-d).
# Derived scoring (accuracy/fidelity/understandability) is computed in Python
# from the merged error list (services.dual_translation.scoring, TASK-627), so
# neither model call emits a `scores` object. These builders reuse the same
# cacheable-prefix architecture and every shared block above (acceptable
# variation, severity tests, enum/subtype lines, span discipline). ZH/JA strings
# are AI-authored first drafts flagged for native review, same as the v1 blocks.
# ===========================================================================

# Highlight reason enum (§6a/§7a highlights) and verdict enum (§6b/§7c). Fixed
# code constants, mirrored in the prompt wording; grader_cascade decodes indices
# back against these.
HIGHLIGHT_REASON_ENUM: tuple[str, ...] = ("grammar", "word_choice", "register_politeness", "structure")
VERDICT_ENUM: tuple[str, ...] = ("confirm", "reject", "adjust")

# TASK-845 (taxonomy v6, ADR-031 Decision A): the word_choice explanation_variant.
# Order is the index contract the model reports; the slugs match the
# dt_error_instance CHECK (migrations/dt_taxonomy_v6_columns.sql).
VARIANT_ENUM: tuple[str, ...] = ("wrong_word", "wrong_sense", "false_synonym")


def variants_enabled(subtypes) -> bool:
    """True only under a v6+ taxonomy (same `meaning_inversion` marker as the
    TASK-843 precedence gate) that has `word_choice`. False → no variant prompt
    text, no schema field, no decoded key: v5 grading stays byte-identical."""
    return "meaning_inversion" in subtypes and "word_choice" in subtypes

# The two model-judged dimensions the Verifier scores with evidence spans; the
# other three (accuracy/fidelity/understandability) are derived, not judged.
JUDGE_DIMENSIONS: tuple[str, ...] = ("naturalness", "range")

_REQUIRED_DETECTOR_KEYS = ("confidence", "errors", "highlights")
_REQUIRED_VERIFIER_KEYS = ("confidence", "verdicts", "added_errors", "judgments")

# --- Detector system-prompt blocks (§7a) ----------------------------------

_DETECTOR_HEADER: dict[str, str] = {
    "en": (
        "You are an expert examiner of learner writing for a language-learning app. You will "
        "receive a REFERENCE text (the correct version), a LEARNER text (an attempt to reproduce "
        "it), and CANDIDATE REGIONS where the two differ. Your only task in this call is to find, "
        "locate, classify and correct errors, and to credit genuinely well-handled difficult "
        "spots. You do NOT assign scores — scores are computed later from your error report, so "
        "completeness and precision are everything. Work through the learner text from start to "
        "finish. Output ONLY a single JSON object — no prose before or after."
    ),
    "zh": (
        "你是语言学习应用中的学习者写作评审专家。你将收到一段【参考译文】（正确版本）、一段"
        "【学习者译文】（学习者的复现尝试），以及两者存在差异的【候选区域】列表。本次调用你唯一的"
        "任务是：找出、定位、分类并改正错误，并对确实处理得好的难点给予标注。你不打分——分数将由你的"
        "错误报告计算得出，因此完整性和精确性至关重要。请从头到尾系统地检查学习者译文。"
        "只输出一个JSON对象，前后不得有任何其他文字。"
    ),
    "ja": (
        "あなたは語学学習アプリにおける学習者作文の専門審査員です。「参照文」（正しい版）、"
        "「学習者文」（その再現の試み）、および両者が異なる「候補領域」のリストが与えられます。"
        "この呼び出しでのあなたの唯一の任務は、誤りを発見・特定・分類・訂正し、難所を正しく処理"
        "できている箇所を評価することです。採点はしません——スコアはあなたの誤り報告から後で計算"
        "されるため、網羅性と正確性がすべてです。学習者文を最初から最後まで体系的に確認してください。"
        "出力は単一のJSONオブジェクトのみとし、前後に文章を含めないでください。"
    ),
}

# 3-way accounted-for rule (error | highlight | acceptable variation) — the
# full §7a version, extending the v1 2-way _ACCOUNTED_FOR with the highlight branch.
_ACCOUNTED_FOR_V2: dict[str, str] = {
    "en": (
        "Every candidate region must be accounted for in exactly one way: (a) reported as an "
        "error, (b) reported as a highlight, or (c) recognized as acceptable variation and "
        "silently ignored. Candidate regions are hints from a character diff, not boundaries — "
        "merge adjacent regions that form one error, and still scan the rest of the text for "
        "errors the diff cannot expose."
    ),
    "zh": (
        "每个候选区域必须以且仅以下列一种方式处理：(a) 报告为错误；(b) 报告为亮点；"
        "(c) 判定为可接受的变体并直接忽略。候选区域只是字符级对比给出的提示，不是边界——"
        "相邻区域若构成同一个错误应合并处理，同时仍需检查全文，找出对比无法暴露的错误。"
    ),
    "ja": (
        "各候補領域は、必ず次のいずれか一つとして処理してください：(a) 誤りとして報告する、"
        "(b) ハイライトとして報告する、(c) 許容される言い換えと判断して無視する。候補領域は"
        "文字単位の差分による手がかりにすぎず、境界ではありません——隣接する領域が一つの誤りを"
        "構成する場合は統合し、差分では検出できない誤りがないか全文も確認してください。"
    ),
}

# Highlights block (§7a) — positive evidence, capped at 3 (enforced in code).
_HIGHLIGHTS_BLOCK: dict[str, str] = {
    "en": (
        "highlights: up to 3 places where the learner correctly handled something genuinely "
        "difficult (a tricky grammar point, exact register, an idiomatic expression). Only "
        "non-obvious successes — an empty list is fine. reason: 0=grammar, 1=word choice, "
        "2=register/politeness, 3=structure."
    ),
    "zh": (
        "highlights：最多3处学习者正确处理了确实有难度的内容（棘手的语法点、准确的语域、地道的表达）。"
        "只报告并非显而易见的成功——空列表也可以。reason：0=语法，1=用词，2=语域/礼貌，3=结构。"
    ),
    "ja": (
        "highlights：学習者が本当に難しい点を正しく処理できた箇所を最大3つ（難しい文法項目、"
        "的確な敬語レベル、慣用的な表現など）。自明でない成功のみを報告してください——空リストでも"
        "構いません。reason：0=文法、1=語彙選択、2=敬語・文体、3=構文。"
    ),
}

# --- Verifier system-prompt blocks (§7c) ----------------------------------

# 4 paragraphs joined; the last carries {dims} (naturalness/range names in L2).
_VERIFIER_HEADER: dict[str, str] = {
    "en": (
        "You are a senior examiner reviewing a first-pass error report on a learner's "
        "reproduction of a reference text. You receive the REFERENCE, the LEARNER text, and a "
        "numbered list of PROPOSED ERRORS. Judge each proposed error strictly; then find what the "
        "first pass missed; then judge two dimensions with evidence. Output ONLY a single JSON "
        "object.\n\n"
        "For each proposed error output a verdict: 0 = confirm as reported; 1 = reject (not an "
        "error: acceptable variation, a wrong span, or the learner's version is actually correct); "
        "2 = adjust (a real error, but the severity, subtype or spans are wrong — supply the "
        "corrected fields). Rejecting false alarms is as important as confirming real errors.\n\n"
        "added_errors: errors the first pass missed, in the same shape as proposed errors. Look "
        "especially for meaning omitted or added relative to the reference, register or politeness "
        "mismatches, and unnatural phrasing that a diff-guided first pass cannot see.\n\n"
        "Finally, judge these dimensions of the learner text on the 1-4 bands described below: "
        "{dims}. For each, cite the 1-3 character spans of the learner text that most influenced "
        "your band. A band without evidence spans is invalid."
    ),
    "zh": (
        "你是一位资深评审，负责复核对学习者译文的第一轮错误报告。你将收到【参考译文】、"
        "【学习者译文】以及带编号的【待核错误】列表。请严格评判每个待核错误；然后找出第一轮遗漏的错误；"
        "最后依据证据对两个整体维度进行评级。只输出一个JSON对象。\n\n"
        "对每个待核错误给出裁定：0＝确认无误；1＝驳回（不是错误：属于可接受变体、跨度有误、"
        "或学习者的写法实际上正确）；2＝调整（确属错误，但严重程度、子类型或跨度有误——请提供修正后的字段）。"
        "驳回误报与确认真实错误同等重要。\n\n"
        "added_errors：第一轮遗漏的错误，格式与待核错误相同。请特别注意：相对参考译文的意义缺失或添加、"
        "语域/礼貌层级不匹配、以及依赖字符对比的第一轮无法察觉的不自然表达。\n\n"
        "最后，按下述1–4级描述对学习者译文的以下维度评级：{dims}。每个维度须引用对你的评级影响最大的"
        "学习者译文字符跨度（1–3个）。没有证据跨度的评级无效。"
    ),
    "ja": (
        "あなたは、学習者文に対する一次誤り報告を再審査する上級審査員です。「参照文」「学習者文」、"
        "および番号付きの「審査対象誤り」リストが与えられます。各審査対象誤りを厳密に判定し、"
        "次に一次審査の見落としを探し、最後に2つの観点を証拠に基づいて評定してください。"
        "出力は単一のJSONオブジェクトのみです。\n\n"
        "各審査対象誤りに判定を出してください：0＝報告どおり確認、1＝棄却（誤りではない："
        "許容される言い換え、スパンの誤り、または学習者の表現が実際には正しい）、2＝修正"
        "（誤りではあるが、重大度・サブタイプ・スパンが不適切——修正後のフィールドを提示）。"
        "誤報の棄却は、真の誤りの確認と同じく重要です。\n\n"
        "added_errors：一次審査が見落とした誤り（審査対象誤りと同じ形式）。特に注意すべき点："
        "参照文に対する意味の欠落・追加、敬語・文体レベルの不一致、文字差分に基づく一次審査では"
        "気づけない不自然な表現。\n\n"
        "最後に、以下の観点について、下記の1〜4の評価基準に従って学習者文を評定してください："
        "{dims}。各観点について、評定に最も影響した学習者文の文字スパン（1〜3個）を必ず示して"
        "ください。証拠スパンのない評定は無効です。"
    ),
}

# PROPOSED ERRORS label for the verifier user prompt (§7d).
_PROPOSED_LABEL: dict[str, str] = {
    "en": "PROPOSED ERRORS",
    "zh": "待核错误",
    "ja": "審査対象誤り",
}

# Shared "respond with exactly this JSON shape" tail (the schema-bearing line of
# _JSON_SHAPE_INSTRUCTION, reused verbatim for the v2 schemas that carry no scores).
_RESPOND_WITH_SHAPE: dict[str, str] = {
    "en": "Respond with exactly this JSON shape:\n{schema}",
    "zh": "请严格按以下JSON结构回复：\n{schema}",
    "ja": "必ず以下のJSON形式で回答してください：\n{schema}",
}

# --- TASK-843: meaning_inversion by-effect precedence (taxonomy v6, ADR-031) ---
#
# ADR-031 labels meaning_inversion BY EFFECT: any error whose effect reverses the
# reference's polarity/negation, direction, quantity/degree or agent/recipient is
# meaning_inversion (fidelity/critical), whatever its surface form; a pure content
# loss stays omission; contradiction is sentence-internal only.
#
# Version gate: the block renders only when the resolved subtype list contains
# `meaning_inversion` — i.e. only when the taxonomy row the grader resolved at
# runtime (active row, or a pinned version) is v6+. v5 has no such slug, so every
# v5 prompt stays byte-identical (tests/test_dual_translation_prompts.py pins
# pre-change hashes). Subtypes are referenced by the same "index (label)" the
# model reads in the subtype list above — it reports indices, and under glossed
# taxonomies it never sees the English slug. {mi}/{om}/{ad}/{co}/{surface} are
# filled by _precedence_block. ZH/JA are AI-authored drafts flagged for native
# review (TASK-839/840), same caveat as every other block in this module.
#
# String review 2026-10-07 (en item 1, applied to en + zh): each placeholder is
# used exactly once, "a clash with the reference" is narrowed to a reversal that
# only shows against the reference, {co} carries both limbs of its definition
# (self-contradiction OR an illogical clause link), and the "report it once, never
# also under its surface type" rule is explicit. References render as
# "index (short name)" — see _short_label.
# ja review 2026-10-08 (TASK-840, AI review — not a native-speaker review): the ja
# block follows the same structure. Its {co} keeps only the self-contradiction
# limb (time / relation / cause-effect), because a wrong ja connective (のに for
# ので) is clause_linkage, not contradiction.
_PRECEDENCE_V6: dict[str, str] = {
    "en": (
        "Meaning inversion — label by EFFECT, not by surface form. Use subtype {mi} for any error "
        "whose effect is to reverse the reference's polarity (negation), direction, quantity or "
        "degree (more → less, always → never), or who does what to whom — whatever its surface "
        "form: a preposition swap, a different word, or a dropped or added word. In particular, a "
        "negator (not, no, never …) that the learner dropped or added so that the polarity "
        "reverses belongs here, not under {om} or {ad}. Report such an error once, under this "
        "subtype only — never also under its surface-form type. Content that is lost without any "
        "reversal stays an omission, and a change of degree that does not reverse it "
        "(very → quite) is not an inversion. {co} is only for a sentence that contradicts itself "
        "or links its clauses illogically, visible from the learner text alone; a reversal that "
        "only shows when compared with the reference is a meaning inversion. A meaning inversion "
        "is always severity critical (2)."
    ),
    "zh": (
        "语义反转——按效果标注，而非按表面形式。若某个错误的效果是使学习者译文相对参考译文在极性（否定）、"
        "方向、数量或程度（多→少、总是→从不）、施事/受事（谁对谁做什么）上发生反转，无论其表面形式是"
        "介词替换、换了另一个词，还是漏掉或多加了某个词，一律标为子类型{mi}。特别是学习者漏掉或多加"
        "否定词（不、没、别、无等）导致极性反转的，属于此类，不标{om}或{ad}。这类错误只按此子类型"
        "报告一次，不要再按其表面形式的类型重复标注。只是丢失内容而没有发生反转的，仍属成分缺失；"
        "程度有变化但没有反转的（如“很”→“比较”）不算反转。{co}仅用于不看参考译文、仅凭学习者译文"
        "本身即可看出的句内自相矛盾或分句之间逻辑关系错误；只有与参考译文对照才能看出的反转，属于"
        "语义反转。语义反转的严重程度一律为严重（2）。"
    ),
    "ja": (
        "意味の反転——表面形式ではなく効果で判定してください。誤りの効果が、参照文と比べて極性（肯定／否定）、"
        "方向、数量・程度（多い→少ない、いつも→決して〜ない）、または動作主と受け手（誰が誰に何をするか）を"
        "反転させるものであれば、表面上は助詞の置き換え、別の語への置き換え、語の脱落・追加のいずれであっても、"
        "サブタイプ{mi}として報告してください。特に、学習者が否定（ない・ず・ません等）を落とした、または"
        "加えたことで極性が反転する場合は、{om}や{ad}ではなくこちらです。このような誤りはこのサブタイプで"
        "一度だけ報告し、表面形式の種類で重ねて報告しないでください。反転を伴わず内容が失われるだけの場合は"
        "欠落のままとし、程度が変わっても反転しない場合（「とても」→「かなり」など）は反転ではありません。"
        "{co}は、参照文を見なくても学習者文だけで分かる文内の自己矛盾（時間・関係・因果の食い違い）に限ります。"
        "参照文と比べて初めて分かる反転は意味の反転です。意味の反転の重大度は常に致命的（2）です。"
    ),
}

# Verifier-only addendum: re-type a Detector error whose effect is an inversion
# but whose subtype is a surface-form type.
_PRECEDENCE_V6_VERIFIER: dict[str, str] = {
    "en": (
        "If a proposed error's effect is such an inversion but it was typed as {surface}, adjust "
        "it (verdict 2) to subtype {mi} with severity critical (2)."
    ),
    "zh": (
        "若某个待核错误的效果属于上述反转，却被标为{surface}中的任一子类型，请裁定为调整（2），"
        "将子类型改为{mi}，严重程度改为严重（2）。"
    ),
    "ja": (
        "審査対象誤りの効果が上記の反転に当たるのに、{surface}のいずれかに分類されている場合は、修正（2）と"
        "判定し、サブタイプを{mi}に、重大度を致命的（2）に変更してください。"
    ),
}

# Surface-form subtypes an inversion is typically mis-filed under, per L2 (the
# v6 slug for the adposition type differs: en preposition / zh coverb / ja
# case_particle). Only those present in the resolved list are named.
_INVERSION_SURFACE_SUBTYPES: dict[str, tuple[str, ...]] = {
    "en": ("preposition", "word_choice", "omission", "addition"),
    "zh": ("coverb", "word_choice", "omission", "addition"),
    "ja": ("case_particle", "word_choice", "omission", "addition"),
}

# --- TASK-844: zh 的/地/得 rule (taxonomy v6, ADR-031 user ruling 2026-09-27) ---
#
# ANY 的/地/得 misuse (的-for-得, 的-for-地, attributive 地-for-的, ...) is a
# `de_particle` error at minor severity — never acceptable variation, never
# word_choice/orthography. zh only; rendered by _precedence_block under the same
# v6 gate as TASK-843 (and only when the resolved list has `de_particle`, a
# v6-only slug — v5 has `de_particles`), so v5 prompts stay byte-identical.
# {de}/{wc}/{orth} are filled with the live "index（label）" references. AI draft,
# in scope for the TASK-839/840 native review. String review 2026-10-07 (zh item
# 105): a MISSING obligatory 得 in a degree/state complement (跑快 → 跑得快) is
# also {de}, not complement — reviewer-proposed boundary pending user
# confirmation (ADR-031, 2026-10-07 note); the redundant "（含定语位置误用“地”）"
# was dropped (地-for-的 is attributive by definition).
_ZH_DE_RULE = (
    "结构助词“的、地、得”：三者之间的任何误用——包括用“的”代替“地”或“得”、用“地”代替“的”、"
    "用“得”代替“的”或“地”——以及缺少必需的“得”（如“跑快”应为“跑得快”），一律标为子类型{de}，"
    "严重程度为轻微（0）。这类误用不属于可接受的变体，不得因“意思不受影响”而忽略；不要标为{wc}或{orth}。"
)
_ZH_DE_RULE_VERIFIER = (
    "若待核错误是“的、地、得”误用，不得以可接受的变体为由驳回（1）；若被标为{wc}或{orth}，"
    "请裁定为调整（2），将子类型改为{de}，严重程度改为轻微（0）。"
)

_SUBTYPE_REF_FORMAT: dict[str, str] = {
    "en": "{i} ({label})",
    "zh": "{i}（{label}）",
    "ja": "{i}（{label}）",
}
_SUBTYPE_REF_SEP: dict[str, str] = {"en": " / ", "zh": "、", "ja": "、"}

# Name/definition separators used by the v6 glosses: en "name — definition",
# zh/ja "名称——定义". (A single "—" can sit inside a name, e.g. 话题—述题结构.)
_GLOSS_NAME_SEPARATORS: tuple[str, ...] = (" — ", "——")


def _short_label(label: str) -> str:
    """The gloss's short name — the text before its first name/definition
    separator — for inline "index (label)" references (string review
    2026-10-07, en item 84). The full gloss is already listed once in the
    subtype list above the block; repeating the whole definition at every
    reference made the rendered block unreadable. A label with no separator
    (bare slug, test labels) is returned unchanged."""
    cut = min((label.find(sep) for sep in _GLOSS_NAME_SEPARATORS if sep in label), default=-1)
    return label[:cut] if cut > 0 else label


def _precedence_block(
    l2_code: str, subtypes: list[str], subtype_labels, *, verifier: bool,
) -> str:
    """The TASK-843 meaning_inversion precedence block, or '' when the resolved
    subtype list has no `meaning_inversion` (every pre-v6 taxonomy) — the caller
    then appends nothing, keeping v5 prompts byte-identical."""
    if "meaning_inversion" not in subtypes:
        return ""
    labels = subtype_labels if subtype_labels is not None else subtypes
    ref_fmt = _SUBTYPE_REF_FORMAT[l2_code]

    def ref(slug: str) -> str:
        idx = _slug_index(subtypes, slug)
        if idx is None:
            return slug
        return ref_fmt.format(i=idx, label=_short_label(labels[idx]))

    fields = {
        "mi": ref("meaning_inversion"),
        "om": ref("omission"),
        "ad": ref("addition"),
        "co": ref("contradiction"),
    }
    text = _PRECEDENCE_V6[l2_code].format(**fields)
    if verifier:
        surface = _SUBTYPE_REF_SEP[l2_code].join(
            ref(s) for s in _INVERSION_SURFACE_SUBTYPES[l2_code] if s in subtypes
        )
        text += "\n" + _PRECEDENCE_V6_VERIFIER[l2_code].format(mi=fields["mi"], surface=surface)
    # TASK-844: zh 的/地/得 rule, same v6 gate (+ the v6-only de_particle slug).
    if l2_code == "zh" and "de_particle" in subtypes:
        de_fields = {"de": ref("de_particle"), "wc": ref("word_choice"), "orth": ref("orthography")}
        text += "\n" + _ZH_DE_RULE.format(**de_fields)
        if verifier:
            text += "\n" + _ZH_DE_RULE_VERIFIER.format(**de_fields)
    return text


# --- TASK-845: word_choice explanation_variant (taxonomy v6, ADR-031 A) ------
#
# One line per L2 defining the three VARIANT_ENUM indices. The model's call is
# only the residual: same-lemma (wrong_sense) and shared-L1-gloss (false_synonym)
# are re-decided in Python from the sense dictionary
# (services/dual_translation/word_choice_variant.py). `explanation_variant` is a
# machine-contract key and stays Latin in every L2. {wc} is the live
# "index (short name)" reference for word_choice. ZH/JA are AI-authored drafts, in
# scope for the TASK-839/840 native review.
#
# String review 2026-10-07 (en item 86, zh item 107): the field is REQUIRED on
# every word_choice error under v6 (merged_taxonomy marks it required; the
# decoder still tolerates its absence and falls back to the variant-less
# template), the variants are decided in ADR-031's precedence order (same lemma
# -> wrong_sense; else shared L1 translation -> false_synonym; else wrong_word),
# and the learner's L1 is named — the false_synonym question cannot be answered
# without it. {l1_sentence}/{l1_ref}/{example} come from _variant_l1_fields: with
# no l1_code they fall back to L1-neutral wording. ja review 2026-10-08 (TASK-840,
# AI review — not a native-speaker review): the ja line now has the same
# structure (required, decision order, L1 named via {l1_sentence}/{l1_ref}, per-L1
# {example}), replacing its old "任意" wording and {l1_paren} slot.
_VARIANT_BLOCK: dict[str, str] = {
    "en": (
        "explanation_variant (required on every error of subtype {wc}; omit it on all other "
        "errors).{l1_sentence} Decide in this order: 1 = wrong sense — the learner used the same "
        "word (same lemma) as the reference, but in a different one of its dictionary senses; "
        "otherwise 2 = false synonym — a different word that {l1_ref} would translate the same "
        "way as the reference word, but whose meaning or usage differs{example}; otherwise "
        "0 = wrong word — a different word that does not mean what the reference word means."
    ),
    "zh": (
        "explanation_variant（子类型为{wc}的每个错误都必须填写，其他错误不填）。{l1_sentence}"
        "请按以下顺序判断：1＝用错义项——学习者用的正是参考译文中的那个词（同一词条），但用成了它的"
        "另一个义项；否则，2＝假同义词——用了另一个词，它在{l1_ref}中与参考译文中的词译法相同，"
        "但意思或用法不同{example}；否则，0＝用错词——用了一个与参考译文中的词意思不同的词"
        "（不属于1或2的情况）。"
    ),
    "ja": (
        "explanation_variant（サブタイプ{wc}の誤りには必ず付け、それ以外の誤りには付けない）。{l1_sentence}"
        "次の順に判定してください：1＝誤った語義——学習者が参照文と同じ語（同じ見出し語）を使っているが、"
        "その語の辞書上の別の語義で使っている。そうでなければ、2＝偽の同義語——別の語で、{l1_ref}では"
        "参照文の語と同じ語に訳されるが、意味や用法が異なる{example}。そうでなければ、0＝誤った語——"
        "参照文の語と意味の異なる別の語（1にも2にも当たらない場合）。"
    ),
}

# The learner's L1, named in the L2 the prompt is written in.
_L1_NAME: dict[str, dict[str, str]] = {
    "en": {"en": "English", "zh": "Chinese", "ja": "Japanese"},
    "zh": {"en": "英语", "zh": "汉语", "ja": "日语"},
    "ja": {"en": "英語", "zh": "中国語", "ja": "日本語"},
}

# Per-(L2, L1) false_synonym example — a pair that THIS L1 translates with one
# word (borrow / lend is a false synonym for Chinese speakers, 借, but not for
# Japanese speakers, 借りる / 貸す). Absent pair -> the L1-neutral default below.
_VARIANT_EXAMPLE: dict[str, dict[str, str]] = {
    "en": {
        "zh": " (e.g. borrow / lend, both 借 in Chinese)",
        "ja": " (e.g. look / watch, both 見る in Japanese)",
    },
    "zh": {
        "en": "（如“知道”与“认识”，在英语中都译作同一个词）",
        "ja": "（如“知道”与“认识”，在日语中都译作「知っている」）",
    },
    # 着る / 履く is one verb in English (wear) and in Chinese (穿). The en example
    # avoids the Latin word so the ja block carries no English prose.
    "ja": {
        "en": "（例：「着る」と「履く」は英語ではどちらも同じ一語に訳される）",
        "zh": "（例：「着る」と「履く」は中国語ではどちらも「穿」）",
    },
}
_VARIANT_EXAMPLE_NEUTRAL: dict[str, str] = {
    "en": "",
    "zh": "（如“知道”与“认识”）",
    "ja": "（例：「着る」と「履く」）",
}


def _variant_l1_fields(l2_code: str, l1_code) -> dict[str, str]:
    """Fill the L1 slots of _VARIANT_BLOCK[l2_code]. A known L1 is named (and gets
    its own false_synonym example where one is authored); with no/unknown L1 the
    wording stays L1-neutral ("the learner's native language")."""
    name = _L1_NAME[l2_code].get(l1_code) if l1_code else None
    example = (_VARIANT_EXAMPLE.get(l2_code, {}).get(l1_code)
               or _VARIANT_EXAMPLE_NEUTRAL.get(l2_code, ""))
    if l2_code == "en":
        return {
            "l1_sentence": f" The learner's native language is {name}." if name else "",
            "l1_ref": name or "the learner's native language",
            "example": example,
        }
    if l2_code == "zh":
        return {
            "l1_sentence": f"学习者的母语是{name}。" if name else "",
            "l1_ref": name or "学习者母语",
            "example": example,
        }
    return {
        "l1_sentence": f"学習者の母語は{name}です。" if name else "",
        "l1_ref": name or "学習者の母語",
        "example": example,
    }


def _variant_block(l2_code: str, subtypes: list[str], subtype_labels, l1_code=None) -> str:
    """The TASK-845 explanation_variant line, or '' when variants are not enabled
    (every pre-v6 taxonomy) — the caller then appends nothing. `l1_code` (the
    learner's L1) is named in the line; None keeps it L1-neutral."""
    if not variants_enabled(subtypes):
        return ""
    labels = subtype_labels if subtype_labels is not None else subtypes
    idx = _slug_index(subtypes, "word_choice")
    wc = _SUBTYPE_REF_FORMAT[l2_code].format(i=idx, label=_short_label(labels[idx]))
    return _VARIANT_BLOCK[l2_code].format(wc=wc, **_variant_l1_fields(l2_code, l1_code))


def build_detector_system_prompt(
    l2_code: str,
    rubric_cfg: dict,
    subtypes: list[str],
    *,
    subtype_labels: list[str] = None,
    l1_code: str = None,
) -> str:
    """Build the cacheable Detector prefix (§7a). NO score instruction and NO
    band descriptors — the Detector only detects; scores are derived in Python.

    Byte-stable for a given (l2_code, rubric config, subtypes) — the prompt-cache
    lever is preserved. Reuses every shared block from the v1 builder above.
    """
    if l2_code not in _DETECTOR_HEADER:
        raise ValueError(f"No Detector template authored for l2_code={l2_code!r}")

    parts = [
        _DETECTOR_HEADER[l2_code],
        _ACCOUNTED_FOR_V2[l2_code],
    ]
    variation_block = _acceptable_variation_text(rubric_cfg, l2_code)
    if variation_block:
        parts.append(variation_block)
    parts.extend(_enum_and_subtype_blocks(l2_code, subtypes, subtype_labels))
    # TASK-843: v6-only (gated on meaning_inversion in the resolved list).
    precedence = _precedence_block(l2_code, subtypes, subtype_labels, verifier=False)
    if precedence:
        parts.append(precedence)
    # TASK-845: v6-only explanation_variant line + optional schema field.
    variants = variants_enabled(subtypes)
    if variants:
        parts.append(_variant_block(l2_code, subtypes, subtype_labels, l1_code))
    parts.append(_SPAN_DISCIPLINE[l2_code])
    parts.append(_IS_MISTAKE[l2_code])
    parts.append(_HIGHLIGHTS_BLOCK[l2_code])
    parts.append(_RESPOND_WITH_SHAPE[l2_code].format(schema=_detector_schema(variants=variants)))
    exemplar_block = _detector_exemplar_text(rubric_cfg, l2_code, subtypes)
    if exemplar_block:
        parts.append(exemplar_block)
    return "\n\n".join(parts)


def build_verifier_system_prompt(
    l2_code: str,
    rubric_cfg: dict,
    age_tier: int,
    subtypes: list[str],
    *,
    subtype_labels: list[str] = None,
    l1_code: str = None,
) -> str:
    """Build the cacheable Verifier prefix (§7c). Carries the naturalness/range
    band descriptors for this age tier (the only model-facing descriptors left)
    plus the shared detection blocks so its added_errors path can fully detect."""
    if l2_code not in _VERIFIER_HEADER:
        raise ValueError(f"No Verifier template authored for l2_code={l2_code!r}")

    names = _DIMENSION_NAMES[l2_code]
    dims_text = "; ".join(names.get(d, d) for d in JUDGE_DIMENSIONS)

    parts = [_VERIFIER_HEADER[l2_code].format(dims=dims_text)]
    variation_block = _acceptable_variation_text(rubric_cfg, l2_code)
    if variation_block:
        parts.append(variation_block)
    parts.extend(_enum_and_subtype_blocks(l2_code, subtypes, subtype_labels))
    # TASK-843: v6-only (gated on meaning_inversion in the resolved list).
    precedence = _precedence_block(l2_code, subtypes, subtype_labels, verifier=True)
    if precedence:
        parts.append(precedence)
    # TASK-845: v6-only explanation_variant line (applies to added_errors).
    variants = variants_enabled(subtypes)
    if variants:
        parts.append(_variant_block(l2_code, subtypes, subtype_labels, l1_code))
    parts.append(_SPAN_DISCIPLINE[l2_code])

    descriptor_block = _band_descriptors_text(rubric_cfg, JUDGE_DIMENSIONS, age_tier, l2_code)
    if descriptor_block:
        parts.append(f"{_BAND_DESCRIPTOR_LABEL[l2_code]}:\n{descriptor_block}")

    parts.append(_RESPOND_WITH_SHAPE[l2_code].format(schema=_verifier_schema(variants=variants)))
    exemplar_block = _verifier_exemplar_text(rubric_cfg, l2_code, subtypes)
    if exemplar_block:
        parts.append(exemplar_block)
    return "\n\n".join(parts)


def build_verifier_user_prompt(
    l2_code: str, gold_l2: str, reproduction: str, proposed: list[dict],
) -> str:
    """Small, never-cached Verifier suffix (§7d): reference + learner text + the
    compact numbered proposed-error list."""
    ref_label, learner_label = _USER_PROMPT_LABELS.get(l2_code, _USER_PROMPT_LABELS["en"])
    proposed_label = _PROPOSED_LABEL.get(l2_code, _PROPOSED_LABEL["en"])
    return "\n".join([
        f"{ref_label}: {gold_l2}",
        f"{learner_label}: {reproduction}",
        f"{proposed_label}: {json.dumps(proposed or [], ensure_ascii=False)}",
    ])


def validate_detector_response(payload) -> bool:
    """Structural check on a parsed Detector response (§6a): confidence present,
    errors and highlights are lists. Per-error/per-highlight field validation is
    grader_cascade's job (a single bad entry is dropped, not the whole response)."""
    if not isinstance(payload, dict):
        return False
    if not all(k in payload for k in _REQUIRED_DETECTOR_KEYS):
        return False
    return isinstance(payload["errors"], list) and isinstance(payload["highlights"], list)


def validate_verifier_response(payload) -> bool:
    """Structural check on a parsed Verifier response (§6b): verdicts and
    added_errors are lists, judgments is a dict. Per-item validation is deferred
    to grader_cascade's merge."""
    if not isinstance(payload, dict):
        return False
    if not all(k in payload for k in _REQUIRED_VERIFIER_KEYS):
        return False
    return (
        isinstance(payload["verdicts"], list)
        and isinstance(payload["added_errors"], list)
        and isinstance(payload["judgments"], dict)
    )


# --- v2 internals ----------------------------------------------------------

def _enum_and_subtype_blocks(l2_code: str, subtypes: list[str], subtype_labels) -> list[str]:
    """The category/source enum lines, reader-impact severity tests, and indexed
    subtype list — shared verbatim between the Detector and Verifier prefixes."""
    enum_lines = _ENUM_LABELS[l2_code]
    cat_gloss = _CATEGORY_GLOSS[l2_code]
    src_gloss = _SOURCE_GLOSS[l2_code]
    labels = subtype_labels if subtype_labels is not None else subtypes
    subtype_lines = "\n".join(f"{i}: {label}" for i, label in enumerate(labels))
    return [
        enum_lines["category"].format(c0=cat_gloss[0], c1=cat_gloss[1], c2=cat_gloss[2]),
        enum_lines["source"].format(s0=src_gloss[0], s1=src_gloss[1]),
        _SEVERITY_TESTS[l2_code],
        f"{_SUBTYPE_LIST_LABEL[l2_code]}\n{subtype_lines}",
    ]


def _error_schema_item(variants: bool) -> dict:
    """One error entry of the Detector `errors` / Verifier `added_errors` shape.
    TASK-845: under v6 (`variants`) it also shows the optional
    `explanation_variant` index; without it the dict — and so the serialized
    schema — is exactly the pre-v6 one."""
    item = {
        "span_repro": [0, 0],
        "span_ref": [0, 0],
        "category": 0,
        "source": 0,
        "severity": 0,
        "subtype": 0,
        "learner_form": "...",
        "corrected_form": "...",
        "confidence": "<0.0-1.0>",
        "is_mistake": False,
    }
    if variants:
        item["explanation_variant"] = 0
    return item


def _detector_schema(*, variants: bool = False) -> str:
    """The §6a Detector JSON shape: confidence + errors[] (no scores) + highlights[]."""
    schema = {
        "confidence": "<0.0-1.0>",
        "errors": [_error_schema_item(variants)],
        "highlights": [{"span_repro": [0, 0], "reason": 0}],
    }
    return json.dumps(schema, ensure_ascii=False)


def _verifier_schema(*, variants: bool = False) -> str:
    """The §6b Verifier JSON shape: confidence + verdicts[] + added_errors[] + judgments{}."""
    schema = {
        "confidence": "<0.0-1.0>",
        "verdicts": [
            {
                "error_index": 0,
                "verdict": 0,
                "severity": 0,
                "subtype": 0,
                "span_repro": [0, 0],
                "span_ref": [0, 0],
            }
        ],
        "added_errors": [_error_schema_item(variants)],
        "judgments": {
            "naturalness": {"band": "<1-4>", "evidence_spans": [[0, 0]]},
            "range": {"band": "<1-4>", "evidence_spans": [[0, 0]]},
        },
    }
    return json.dumps(schema, ensure_ascii=False)


def _resolve_exemplar_error(error: dict, subtypes: list[str]) -> dict | None:
    """Resolve a stored exemplar error's `subtype_slug`/`severity_slug` to live
    indices, returning the index-form error or None on drift (caller logs + skips).

    Shares the slug-resolution contract of the v1 `_exemplar_text` (a missing worked
    example beats a silently mislabelled one, TASK-637/ADR-020) but returns the
    resolved error so the Detector exemplar can reshape it (drop scores, add
    highlights) rather than duplicating the resolution."""
    error = dict(error)
    subtype_index = _slug_index(subtypes, error.pop("subtype_slug", None))
    severity_index = _slug_index(SEVERITY_ENUM, error.pop("severity_slug", None))
    if subtype_index is None or severity_index is None:
        return None
    error["subtype"] = subtype_index
    error["severity"] = severity_index
    return error


def _detector_exemplar_text(rubric_cfg: dict, l2_code: str, subtypes: list[str]) -> str:
    """Render one Detector-shaped worked exemplar (§7a). Prefers a v2-shape
    `exemplars.detector[l2]`; falls back to the already-seeded v4-shape
    `exemplars[l2]` single-error example reshaped to Detector output (drop scores,
    empty highlights). Returns '' — the block is omitted — when no exemplar is
    seeded or its slugs have drifted (logged; ADR-020 fail-safe)."""
    exemplars = (rubric_cfg or {}).get("exemplars", {})
    if not isinstance(exemplars, dict):
        return ""
    detector_map = exemplars.get("detector")
    entry = detector_map.get(l2_code) if isinstance(detector_map, dict) else None
    if not entry:
        entry = exemplars.get(l2_code)  # v4-shape single exemplar (already seeded)
    if not entry:
        return ""

    error = _resolve_exemplar_error(entry.get("error", {}), subtypes)
    if error is None:
        logger.warning(
            "dual_translation.prompts: dropping the %s Detector exemplar — its "
            "subtype_slug/severity_slug did not resolve against the active taxonomy/"
            "severity enums (rubric and taxonomy rows have drifted, ADR-020). Prompt "
            "is degraded, not wrong.", l2_code,
        )
        return ""

    obj = {
        "confidence": entry.get("confidence", error.get("confidence", 0.9)),
        "errors": [error],
        "highlights": entry.get("highlights", []),
    }
    ref_label, learner_label = _USER_PROMPT_LABELS.get(l2_code, _USER_PROMPT_LABELS["en"])
    body = (
        f"{ref_label}: {entry.get('reference', '')}\n"
        f"{learner_label}: {entry.get('learner', '')}\n"
        f"→ {json.dumps(obj, ensure_ascii=False)}"
    )
    return f"{_EXEMPLAR_LABEL[l2_code]}\n{body}"


# ===========================================================================
# TASK-630 — Explainer pass (Evidence-First Grading v2, tech spec §6c/§7e).
#
# The Explainer is the ONE prompt in this module written in the learner's **L1**,
# not the L2 (the module docstring's L2-only rule is a Detector/Verifier property —
# those tag numeric indices and read L2 band descriptors; the Explainer writes
# learner-facing prose, so it must speak the learner's native language). It takes
# the merged final errors — each already carrying its Rule-template explanation —
# and returns a per-error instance-specific *Application* layer that names the
# actual words in THIS sentence. Output is validated in services.dual_translation.
# explainer and falls back to Rule-only silently. JSON field names stay English
# protocol tokens; all natural language (header, subtype gloss, rule text) is L1.
# ZH/JA strings are the tech spec §7e drafts, flagged for native review like the
# rest of this module.
# ===========================================================================

# Explainer system prompt, written in the learner's L1 (§7e). One string per L1.
_EXPLAINER_HEADER: dict[str, str] = {
    "en": (
        "You write feedback for a language learner, in English (the learner's native "
        "language). You receive the reference sentence, the learner's sentence, and a "
        "numbered list of confirmed errors: each has the learner's form, the corrected "
        "form, the error type, and the general rule (already shown to the learner "
        "separately). For each error write 1-2 short sentences explaining why the "
        "correction is right in this specific sentence — name the actual words involved "
        "and the meaning difference they make. Do not restate the general rule; do not "
        "introduce new corrections; do not contradict the given correction; do not mention "
        "scores or how many errors there are; do not praise or console. Write at a level a "
        "motivated teenager understands. Output ONLY JSON: "
        '{"explanations":[{"error_index":0,"text":"..."}]}. If you cannot add anything '
        "specific beyond the general rule for an error, omit that index."
    ),
    "zh": (
        "你为语言学习者撰写反馈，使用中文（学习者的母语）。你将收到参考句、学习者的句子，"
        "以及带编号的已确认错误列表：每项包含学习者的写法、正确写法、错误类型和通用规则"
        "（已另行展示给学习者）。请为每个错误写1–2句话，解释为什么在这个具体句子中该改法是对的"
        "——点明涉及的具体词语及其造成的意义差别。不要复述通用规则；不要提出新的修改；"
        "不要与给定的改法矛盾；不要提及分数或错误数量；不要表扬或安慰。"
        "用积极上进的中学生能理解的语言书写。只输出JSON："
        '{"explanations":[{"error_index":0,"text":"..."}]}。'
        "若某个错误你无法给出比通用规则更具体的内容，则省略该编号。"
    ),
    "ja": (
        "あなたは語学学習者向けのフィードバックを、日本語（学習者の母語）で書きます。"
        "参照文、学習者の文、および番号付きの確定済み誤りリスト（各項目：学習者の表現、"
        "正しい表現、誤りの種類、一般規則——一般規則は別途学習者に表示済み）が与えられます。"
        "各誤りについて、この特定の文でなぜその訂正が正しいのかを1〜2文で説明してください"
        "——関係する実際の語句と、それが生む意味の違いを具体的に示すこと。一般規則の繰り返し、"
        "新たな訂正の提案、提示された訂正との矛盾、点数や誤り数への言及、称賛や慰めは禁止です。"
        "意欲的な中高生に伝わる言葉で書いてください。出力はJSONのみ："
        '{"explanations":[{"error_index":0,"text":"..."}]}。'
        "一般規則以上に具体的なことが書けない誤りは、その番号を省略してください。"
    ),
}

# Label preceding the numbered confirmed-error list in the Explainer user prompt (L1).
_EXPLAINER_ERRORS_LABEL: dict[str, str] = {
    "en": "CONFIRMED ERRORS",
    "zh": "已确认错误",
    "ja": "確定済み誤り",
}


# TASK-846 (taxonomy v6, ADR-031 Decision A): appended to the Explainer system
# prompt only when an error in the batch carries a word_choice `variant`. One
# sentence per variant, in the learner's L1; the slugs are protocol tokens (they
# appear verbatim in the error list) so they stay Latin. ZH/JA are AI drafts →
# native review with the rest of the v6 strings (TASK-839/840).
_EXPLAINER_VARIANT_GUIDANCE: dict[str, str] = {
    "en": (
        ' Some word-choice errors carry a "variant". wrong_word: the learner used a '
        "different word with a different meaning — say what each word means here. "
        "wrong_sense: it is the same word used in a sense this sentence does not need — "
        "say which sense the context calls for. false_synonym: the two words can share "
        "one English translation but are not interchangeable — contrast the two words "
        "and say how their usage differs."
    ),
    "zh": (
        "部分“词语选择”类错误带有“variant”字段。wrong_word：学习者用了意思不同的另一个词——说明两个词在这里各自的意思。"
        "wrong_sense：是同一个词，但用成了这个句子不需要的义项——说明语境需要的是哪个义项。"
        "false_synonym：两个词在中文里常常译成同一个词，但不能互换——对比这两个词，说明它们的用法有何不同。"
    ),
    "ja": (
        "一部の「語彙選択」の誤りには「variant」の項目が付いています。wrong_word：学習者が意味の異なる別の語を"
        "使った——ここでの各語の意味を説明すること。wrong_sense：同じ語だが、この文に合わない語義で使われている"
        "——文脈が求める語義を示すこと。false_synonym：二つの語は日本語では同じ訳語になり得るが置き換えはできない"
        "——二つの語を対比し、使い方の違いを説明すること。"
    ),
}


def build_explainer_system_prompt(l1_code: str, variants: bool = False) -> str:
    """The Explainer system prompt in the learner's L1 (§7e). Raises for an
    unauthored L1 — the caller (services.dual_translation.explainer) is fail-silent
    around this, so an unsupported L1 degrades to Rule-only rather than crashing.

    TASK-846: `variants=True` (some error carries a v6 word_choice variant) appends
    the per-variant guidance; the default returns the v5 header byte-identically."""
    if l1_code not in _EXPLAINER_HEADER:
        raise ValueError(f"No Explainer template authored for l1_code={l1_code!r}")
    if variants:
        return _EXPLAINER_HEADER[l1_code] + _EXPLAINER_VARIANT_GUIDANCE[l1_code]
    return _EXPLAINER_HEADER[l1_code]


def build_explainer_user_prompt(
    l1_code: str, reference: str, reproduction: str, errors: list[dict],
) -> str:
    """The small, never-cached Explainer suffix (§7e): reference + learner text +
    the numbered confirmed-error list. `errors` is the compact per-error shape the
    explainer builds — ``{i, learner_form, corrected_form, type, rule}`` — where
    `type` (the subtype gloss) and `rule` are already in the L1. TASK-846: a v6
    word_choice error also carries ``variant`` (its explanation_variant slug),
    serialized as-is with the rest of the item."""
    ref_label, learner_label = _USER_PROMPT_LABELS.get(l1_code, _USER_PROMPT_LABELS["en"])
    errors_label = _EXPLAINER_ERRORS_LABEL.get(l1_code, _EXPLAINER_ERRORS_LABEL["en"])
    return "\n".join([
        f"{ref_label}: {reference}",
        f"{learner_label}: {reproduction}",
        f"{errors_label}: {json.dumps(errors or [], ensure_ascii=False)}",
    ])


def validate_explainer_response(payload) -> bool:
    """Structural check on a parsed Explainer response (§6c): a dict whose
    `explanations` is a list. Per-item validation (length / mention / score-pattern /
    index bounds) is the explainer's job — a single bad item is dropped to Rule-only,
    never the whole response."""
    return isinstance(payload, dict) and isinstance(payload.get("explanations"), list)


def _verifier_exemplar_text(rubric_cfg: dict, l2_code: str, subtypes: list[str]) -> str:
    """Render one Verifier-shaped worked exemplar from `exemplars.verifier[l2]`
    (§7c), if seeded. The stored entry carries `reference`/`learner`/`proposed`
    and a fully-formed verifier `json` object (verdicts/added_errors/judgments).
    Returns '' — omitted — when no verifier exemplar is seeded (the v5 rubric does
    not carry one yet; authoring follow-up), matching the graceful-degradation
    pattern of every other rubric-config block."""
    exemplars = (rubric_cfg or {}).get("exemplars", {})
    verifier_map = exemplars.get("verifier") if isinstance(exemplars, dict) else None
    entry = verifier_map.get(l2_code) if isinstance(verifier_map, dict) else None
    if not entry:
        return ""
    obj = entry.get("json")
    if not isinstance(obj, dict):
        return ""
    ref_label, learner_label = _USER_PROMPT_LABELS.get(l2_code, _USER_PROMPT_LABELS["en"])
    proposed_label = _PROPOSED_LABEL.get(l2_code, _PROPOSED_LABEL["en"])
    body = (
        f"{ref_label}: {entry.get('reference', '')}\n"
        f"{learner_label}: {entry.get('learner', '')}\n"
        f"{proposed_label}: {json.dumps(entry.get('proposed', []), ensure_ascii=False)}\n"
        f"→ {json.dumps(obj, ensure_ascii=False)}"
    )
    return f"{_EXEMPLAR_LABEL[l2_code]}\n{body}"
