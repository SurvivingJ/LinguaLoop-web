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
"""

from __future__ import annotations

import json

# Shared cross-linguistic schema (category/source/severity). These are NOT versioned
# taxonomy data — they are already hardcoded as CHECK constraints on the live
# `dt_error_instance` table (migrations/dual_translation_groundwork.sql, TASK-602), so
# fixing them as code constants here just mirrors a constraint the DB already enforces.
# Only `subtype` is the open-ended, per-pair axis that must come from dt_taxonomy_version.
CATEGORY_ENUM: tuple[str, ...] = ("grammatical", "lexical", "pragmatic_expressional")
SOURCE_ENUM: tuple[str, ...] = ("interlingual", "intralingual")
SEVERITY_ENUM: tuple[str, ...] = ("global", "local")

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

_ENUM_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "category": "category (0={c0}, 1={c1}, 2={c2})",
        "source": "source (0={s0}, 1={s1})",
        "severity": "severity (0={v0}, 1={v1})",
    },
    "zh": {
        "category": "类别 category（0={c0}，1={c1}，2={c2}）",
        "source": "来源 source（0={s0}，1={s1}）",
        "severity": "严重程度 severity（0={v0}，1={v1}）",
    },
    "ja": {
        "category": "種別 category（0={c0}、1={c1}、2={c2}）",
        "source": "起因 source（0={s0}、1={s1}）",
        "severity": "重大度 severity（0={v0}、1={v1}）",
    },
}

# Glosses for the three fixed cross-linguistic enums (CATEGORY_ENUM/SOURCE_ENUM/
# SEVERITY_ENUM). These are finite (7 values total) and stable, so — unlike
# `subtype`, which is open-ended per-pair taxonomy data — they're authored here
# directly rather than sourced from dt_taxonomy_version. The English enum
# *value* (e.g. "grammatical") is a Python-side decode key only; the model
# never sees it in a ZH/JA prompt, only the gloss below.
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
_SEVERITY_GLOSS: dict[str, tuple[str, str]] = {
    "en": ("global (impairs comprehension)", "local (noticeable but meaning survives)"),
    "zh": ("全局性（影响理解）", "局部性（可察觉但不影响理解）"),
    "ja": ("グローバル（理解を妨げる）", "ローカル（気づく程度で意味は保たれる）"),
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

    dims = tuple(TIER_DIMENSIONS[tier]) + tuple(d for d in extra_dims if d not in TIER_DIMENSIONS[tier])
    names = _DIMENSION_NAMES[l2_code]
    dims_text = "; ".join(names.get(d, d) for d in dims)

    parts = [
        _INSTRUCTION_HEADER[l2_code],
        _SCORE_INSTRUCTION[l2_code].format(dims=dims_text),
    ]

    descriptor_block = _band_descriptors_text(rubric_cfg, dims, age_tier, l2_code)
    if descriptor_block:
        parts.append(f"{_BAND_DESCRIPTOR_LABEL[l2_code]}:\n{descriptor_block}")

    enum_lines = _ENUM_LABELS[l2_code]
    cat_gloss = _CATEGORY_GLOSS[l2_code]
    src_gloss = _SOURCE_GLOSS[l2_code]
    sev_gloss = _SEVERITY_GLOSS[l2_code]
    parts.append(enum_lines["category"].format(c0=cat_gloss[0], c1=cat_gloss[1], c2=cat_gloss[2]))
    parts.append(enum_lines["source"].format(s0=src_gloss[0], s1=src_gloss[1]))
    parts.append(enum_lines["severity"].format(v0=sev_gloss[0], v1=sev_gloss[1]))

    labels = subtype_labels if subtype_labels is not None else subtypes
    subtype_lines = "\n".join(f"{i}: {label}" for i, label in enumerate(labels))
    parts.append(f"{_SUBTYPE_LIST_LABEL[l2_code]}\n{subtype_lines}")

    schema = _example_schema(dims)
    parts.append(_JSON_SHAPE_INSTRUCTION[l2_code].format(schema=schema))

    return "\n\n".join(parts)


def build_user_prompt(l2_code: str, gold_l2: str, reproduction: str) -> str:
    """Build the small, never-cached per-submission suffix: just the two texts."""
    ref_label, learner_label = _USER_PROMPT_LABELS.get(l2_code, _USER_PROMPT_LABELS["en"])
    return f"{ref_label}: {gold_l2}\n{learner_label}: {reproduction}"


def validate_raw_response(payload: dict) -> bool:
    """Shallow structural check on a parsed (already-json.loads'd) tier response.

    Deliberately shallow — per-error field validation (span bounds, enum range,
    non-empty learner_form/corrected_form) happens in grader_cascade._decode_error,
    where a single bad error can be dropped without discarding the whole response.
    """
    if not isinstance(payload, dict):
        return False
    if not all(k in payload for k in _REQUIRED_JSON_KEYS):
        return False
    if not isinstance(payload["scores"], dict) or not isinstance(payload["errors"], list):
        return False
    return True


def error_has_required_keys(raw_error: dict) -> bool:
    return isinstance(raw_error, dict) and all(k in raw_error for k in _REQUIRED_ERROR_KEYS)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

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
