"""Unit tests for the dual-translation cascade prompt builders (TASK-606).

Covers the two acceptance criteria that are specific to prompts.py: the
prompt is L2-only (no English instructional prose leaking into ZH/JA, modulo
the documented protocol-token exception), and the cacheable system-prompt
prefix is byte-stable for identical inputs (the cascade doc's "cached prefix
must be byte-stable" requirement).
"""

import copy
import logging
import re

import pytest

from services.dual_translation import prompts

_ASCII_WORD = re.compile(r"[A-Za-z]{2,}")

# Protocol/schema tokens that are deliberately inlined in every language's
# prompt (see prompts.py module docstring) — not a violation of "no English".
# These are exactly the JSON field names (and JSON boolean literals) the
# prose explains, split on underscores by the word regex (e.g. span_repro ->
# "span"+"repro", is_mistake -> "is"+"mistake").
_ALLOWED_PROTOCOL_TOKENS = {
    "category", "source", "severity", "json",
    "span", "repro", "ref", "learner", "corrected", "form",
    "confidence", "subtype", "is", "mistake", "true", "false",
}

RUBRIC_CFG = {}
SUBTYPES = ["article_omission", "preposition"]
SUBTYPE_LABELS_ZH = ["冠词缺失/误用", "介词错误"]
SUBTYPE_LABELS_JA = ["冠詞の脱落・誤用", "前置詞の誤り"]


def _prose_before_schema(prompt_text: str) -> str:
    return prompt_text.split('{"confidence"', 1)[0]


def test_build_system_prompt_zh_has_no_unexpected_english():
    prompt = prompts.build_system_prompt("tier1", "zh", RUBRIC_CFG, 3, SUBTYPES, subtype_labels=SUBTYPE_LABELS_ZH)
    prose = _prose_before_schema(prompt)
    leaked = {w.lower() for w in _ASCII_WORD.findall(prose)} - _ALLOWED_PROTOCOL_TOKENS
    assert not leaked, f"unexpected English tokens in zh prompt: {leaked}"


def test_build_system_prompt_ja_has_no_unexpected_english():
    prompt = prompts.build_system_prompt("tier1", "ja", RUBRIC_CFG, 3, SUBTYPES, subtype_labels=SUBTYPE_LABELS_JA)
    prose = _prose_before_schema(prompt)
    leaked = {w.lower() for w in _ASCII_WORD.findall(prose)} - _ALLOWED_PROTOCOL_TOKENS
    assert not leaked, f"unexpected English tokens in ja prompt: {leaked}"


def test_build_system_prompt_without_labels_falls_back_to_bare_subtype_names():
    """Documented stopgap: pre-616 content, no glosses available yet — the
    bare English subtype slug appears instead of crashing."""
    prompt = prompts.build_system_prompt("tier1", "zh", RUBRIC_CFG, 3, SUBTYPES)
    assert "article_omission" in prompt


def test_build_system_prompt_en_is_naturally_english():
    prompt = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG, 3, SUBTYPES)
    assert "accuracy" in prompt.lower()


def test_build_system_prompt_is_byte_stable_for_identical_inputs():
    """The cascade doc requires the cached prefix to be byte-stable across
    submissions; only a config/version change may alter it."""
    first = prompts.build_system_prompt("tier2", "ja", RUBRIC_CFG, 4, SUBTYPES)
    second = prompts.build_system_prompt("tier2", "ja", RUBRIC_CFG, 4, SUBTYPES)
    assert first == second


def test_build_system_prompt_changes_with_subtype_list():
    base = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG, 3, SUBTYPES)
    changed = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG, 3, SUBTYPES + ["tense_aspect"])
    assert base != changed


def test_build_system_prompt_unknown_language_raises():
    try:
        prompts.build_system_prompt("tier1", "fr", RUBRIC_CFG, 3, SUBTYPES)
        assert False, "expected ValueError for an unauthored language"
    except ValueError:
        pass


def test_build_user_prompt_includes_both_texts():
    prompt = prompts.build_user_prompt("en", "the gold text", "the learner text")
    assert "the gold text" in prompt
    assert "the learner text" in prompt


# ---------------------------------------------------------------------------
# TASK-624: candidate regions in the user prompt
# ---------------------------------------------------------------------------

def test_build_user_prompt_appends_candidate_regions_when_given():
    regions = [{"op": "replace", "ref": "has lived", "repro": "lives"}]
    prompt = prompts.build_user_prompt("en", "the gold text", "the learner text", regions=regions)
    assert "CANDIDATE REGIONS" in prompt
    assert '"op": "replace"' in prompt
    assert "has lived" in prompt and "lives" in prompt


def test_build_user_prompt_omits_regions_line_when_empty():
    # None and [] both leave the user prompt exactly as before (no label line).
    base = prompts.build_user_prompt("en", "g", "l")
    assert base == prompts.build_user_prompt("en", "g", "l", regions=None)
    assert base == prompts.build_user_prompt("en", "g", "l", regions=[])
    assert "CANDIDATE REGIONS" not in base


def test_build_user_prompt_region_label_is_localised():
    regions = [{"op": "delete", "ref": "了", "repro": ""}]
    zh = prompts.build_user_prompt("zh", "参考", "学习", regions=regions)
    ja = prompts.build_user_prompt("ja", "参照", "学習", regions=regions)
    assert "候选区域" in zh
    assert "候補領域" in ja


# ---------------------------------------------------------------------------
# TASK-624: new system-prompt blocks (accounted-for, acceptable-variation,
# reader-impact severity, span discipline, is_mistake, exemplar)
# ---------------------------------------------------------------------------

# A minimal v4-shaped rubric config (acceptable_variation + exemplars only).
RUBRIC_CFG_V4 = {
    "acceptable_variation": {
        "en": ["synonyms that preserve meaning and register", "optional commas"],
    },
    "exemplars": {
        "en": {
            "reference": "He learns about robotics.",
            "learner": "He learns on robotics.",
            "confidence": 0.9,
            "scores": {"accuracy": 3, "range": 4, "understandability": 4, "fidelity": 4, "naturalness": 4},
            "error": {
                "span_repro": [9, 20], "span_ref": [9, 23],
                "category": 0, "source": 1,
                "subtype_slug": "preposition", "severity_slug": "major",
                "learner_form": "on robotics", "corrected_form": "about robotics",
                "confidence": 0.9, "is_mistake": False,
            },
        },
    },
}


def test_new_blocks_present_in_en_prompt():
    prompt = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG, 3, SUBTYPES)
    # accounted-for rule, reader-impact severity, span discipline, is_mistake all
    # render unconditionally (no config needed).
    assert "accounted for" in prompt
    assert "reader-impact test" in prompt
    assert "character offsets" in prompt
    assert "is_mistake:" in prompt


def test_severity_block_is_the_three_level_triad():
    # TASK-625: the reader-impact severity block must carry all three MQM levels
    # (indices 0/1/2) and no longer mention the retired global/local vocabulary.
    prompt = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG, 3, SUBTYPES)
    assert "minor (0)" in prompt
    assert "major (1)" in prompt
    assert "critical (2)" in prompt
    assert "global" not in prompt.lower()
    # SEVERITY_ENUM itself is the triad, in order.
    assert prompts.SEVERITY_ENUM == ("minor", "major", "critical")


def test_acceptable_variation_block_renders_from_config():
    prompt = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG_V4, 3, SUBTYPES)
    assert "acceptable variation" in prompt.lower()
    assert "synonyms that preserve meaning and register" in prompt


def test_acceptable_variation_block_omitted_without_config():
    # Empty config → the block is silently omitted (graceful degradation).
    prompt = prompts.build_system_prompt("tier1", "en", {}, 3, SUBTYPES)
    assert "synonyms that preserve meaning and register" not in prompt


def test_exemplar_renders_and_resolves_subtype_slug_to_index():
    # subtype_slug 'preposition' -> index 1 in SUBTYPES; the shown index must
    # match the subtype list the model reads above it.
    prompt = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG_V4, 3, SUBTYPES)
    assert "Worked example:" in prompt
    assert '"subtype": 1' in prompt
    assert '"subtype_slug"' not in prompt  # slug is resolved away, not leaked
    assert "on robotics" in prompt


def test_exemplar_resolves_severity_slug_to_index():
    # severity_slug 'major' -> index 1 in SEVERITY_ENUM ("minor","major","critical").
    prompt = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG_V4, 3, SUBTYPES)
    assert '"severity": 1' in prompt
    assert '"severity_slug"' not in prompt  # slug is resolved away, not leaked


@pytest.mark.parametrize(
    "key, bad_value",
    [
        ("subtype_slug", "particle"),        # the exact TASK-637 regression: a retired slug
        ("subtype_slug", None),              # key absent entirely
        ("severity_slug", "catastrophic"),   # never in SEVERITY_ENUM
        ("severity_slug", None),
    ],
)
def test_exemplar_is_dropped_not_guessed_when_a_slug_fails_to_resolve(key, bad_value, caplog):
    """TASK-637 / ADR-020: an unresolvable slug must drop the worked example, NOT
    fall back to index 0.

    The old code did `except ValueError: error["subtype"] = 0`. Index 0 is a real
    subtype, so nothing raised and nothing logged — the exemplar simply taught the
    model the wrong label. Degrading the prompt is recoverable; corrupting it is not.
    """
    cfg = copy.deepcopy(RUBRIC_CFG_V4)
    if bad_value is None:
        cfg["exemplars"]["en"]["error"].pop(key)
    else:
        cfg["exemplars"]["en"]["error"][key] = bad_value

    with caplog.at_level(logging.WARNING):
        prompt = prompts.build_system_prompt("tier1", "en", cfg, 3, SUBTYPES)

    # The worked example is gone — no guessed index was substituted in its place.
    assert "Worked example:" not in prompt
    assert "on robotics" not in prompt
    # ...and the drift was announced rather than swallowed.
    assert caplog.records, "an unresolvable slug must log, not fail silently"
    assert "drifted" in caplog.text
    # The rest of the prompt still builds — this is degradation, not an outage.
    assert "accounted for" in prompt


def test_exemplar_still_renders_when_only_the_other_slug_is_fine():
    # Guard against an over-broad drop: a valid pair must survive.
    prompt = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG_V4, 3, SUBTYPES)
    assert "Worked example:" in prompt


def test_exemplar_scores_projected_to_tier_dims():
    # tier1 scores accuracy+range; the exemplar's scores block shows only those.
    t1 = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG_V4, 3, SUBTYPES)
    t1_exemplar = t1.split("Worked example:", 1)[1]
    assert '"accuracy"' in t1_exemplar and '"range"' in t1_exemplar
    assert '"understandability"' not in t1_exemplar


def test_new_blocks_keep_zh_ja_prompts_free_of_english():
    # The unconditional blocks are authored in ZH/JA; re-assert L2-purity now
    # that they render (config kept empty so exemplar/variation stay out).
    for l2, labels in (("zh", SUBTYPE_LABELS_ZH), ("ja", SUBTYPE_LABELS_JA)):
        prompt = prompts.build_system_prompt("tier2", l2, {}, 3, SUBTYPES, subtype_labels=labels)
        prose = _prose_before_schema(prompt)
        leaked = {w.lower() for w in _ASCII_WORD.findall(prose)} - _ALLOWED_PROTOCOL_TOKENS
        assert not leaked, f"unexpected English tokens in {l2} prompt: {leaked}"


def test_system_prompt_byte_stable_with_v4_config():
    first = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG_V4, 3, SUBTYPES)
    second = prompts.build_system_prompt("tier1", "en", RUBRIC_CFG_V4, 3, SUBTYPES)
    assert first == second


def test_validate_raw_response_accepts_well_shaped_payload():
    payload = {"confidence": 0.9, "scores": {"accuracy": 3}, "errors": []}
    assert prompts.validate_raw_response(payload) is True


def test_validate_raw_response_rejects_missing_keys():
    assert prompts.validate_raw_response({"scores": {}, "errors": []}) is False
    assert prompts.validate_raw_response({"confidence": 0.9, "scores": {}}) is False
    assert prompts.validate_raw_response("not a dict") is False


# ---------------------------------------------------------------------------
# TASK-635: scores must cover every dimension the tier was asked to score
# ---------------------------------------------------------------------------

TIER1_DIMS = ("accuracy", "range")


def test_validate_raw_response_rejects_empty_scores_despite_high_confidence():
    """The leniency hole: a well-formed payload that scores NOTHING used to pass,
    and its high self-reported confidence then suppressed the Tier-2 re-check
    while every dimension defaulted to a perfect band."""
    payload = {"confidence": 0.9, "scores": {}, "errors": []}
    assert prompts.validate_raw_response(payload, required_dims=TIER1_DIMS) is False


def test_validate_raw_response_rejects_one_missing_dimension():
    # Partial coverage is still incomplete — 'range' would default to MAX_BAND.
    payload = {"confidence": 0.9, "scores": {"accuracy": 3}, "errors": []}
    assert prompts.validate_raw_response(payload, required_dims=TIER1_DIMS) is False


def test_validate_raw_response_accepts_complete_scores():
    payload = {"confidence": 0.9, "scores": {"accuracy": 3, "range": 4}, "errors": []}
    assert prompts.validate_raw_response(payload, required_dims=TIER1_DIMS) is True


def test_validate_raw_response_accepts_extra_dimensions_beyond_those_asked():
    # Scoring more than asked is not a failure; only missing coverage is.
    payload = {"confidence": 0.9, "scores": {"accuracy": 3, "range": 4, "naturalness": 2}, "errors": []}
    assert prompts.validate_raw_response(payload, required_dims=TIER1_DIMS) is True


def test_validate_raw_response_rejects_unusable_band_values():
    # Each of these would otherwise be silently coerced to a perfect band by
    # grader_cascade._clip_band (out-of-range clips to 4; non-numeric returns 4).
    for bad in ("banana", None, 9, 0, -1, True, [3]):
        payload = {"confidence": 0.9, "scores": {"accuracy": bad, "range": 4}, "errors": []}
        assert prompts.validate_raw_response(payload, required_dims=TIER1_DIMS) is False, f"accepted band {bad!r}"


def test_validate_raw_response_accepts_numeric_string_and_float_bands():
    # Tolerated: they map onto a real band, and rejecting them would fall the
    # dimension open to MAX_BAND — more lenient than letting _clip_band round.
    for ok in (3, 3.0, "3", 2.5):
        payload = {"confidence": 0.9, "scores": {"accuracy": ok, "range": 4}, "errors": []}
        assert prompts.validate_raw_response(payload, required_dims=TIER1_DIMS) is True, f"rejected band {ok!r}"


def test_validate_raw_response_without_required_dims_only_checks_outer_shape():
    # The default keeps the pre-TASK-635 contract for callers that don't declare
    # the dimensions they asked for.
    assert prompts.validate_raw_response({"confidence": 0.9, "scores": {}, "errors": []}) is True


def test_missing_score_dims_names_the_offending_dimensions():
    payload = {"confidence": 0.9, "scores": {"accuracy": 3}, "errors": []}
    assert prompts.missing_score_dims(payload, TIER1_DIMS) == ["range"]
    assert prompts.missing_score_dims({"confidence": 0.9, "scores": {}, "errors": []}, TIER1_DIMS) == ["accuracy", "range"]
    # A payload whose scores aren't even a dict is missing all of them.
    assert prompts.missing_score_dims({"scores": "nope"}, TIER1_DIMS) == ["accuracy", "range"]


def test_asked_dimensions_matches_the_tier_and_extra_dims():
    assert prompts.asked_dimensions("tier1") == ("accuracy", "range")
    assert prompts.asked_dimensions("tier2") == ("understandability", "fidelity", "naturalness")
    # The Tier-2 re-check path adds accuracy/range; no duplicates when overlapping.
    assert prompts.asked_dimensions("tier2", ("accuracy", "range")) == (
        "understandability", "fidelity", "naturalness", "accuracy", "range",
    )
    assert prompts.asked_dimensions("tier1", ("accuracy",)) == ("accuracy", "range")


def test_asked_dimensions_rejects_unknown_tier():
    try:
        prompts.asked_dimensions("tier9")
        assert False, "expected ValueError for an unknown tier"
    except ValueError:
        pass


def test_error_has_required_keys():
    good = {
        "span_repro": [0, 1], "span_ref": [0, 1], "category": 0, "source": 0,
        "severity": 0, "subtype": 0, "learner_form": "a", "corrected_form": "b",
        "confidence": 0.5,
    }
    assert prompts.error_has_required_keys(good) is True
    assert prompts.error_has_required_keys({"span_repro": [0, 1]}) is False


# ---------------------------------------------------------------------------
# TASK-843: meaning_inversion by-effect precedence block (taxonomy v6, ADR-031)
# ---------------------------------------------------------------------------

import hashlib  # noqa: E402
import json  # noqa: E402
import pathlib  # noqa: E402

_MIGRATIONS = pathlib.Path(__file__).resolve().parent.parent / "migrations"


def _seed_taxonomy(name: str) -> dict:
    text = (_MIGRATIONS / name).read_text(encoding="utf-8")
    m = re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", text, re.S)
    assert m, f"no $taxonomy$ literal in {name}"
    return json.loads(m.group(1))


V5_TAX = _seed_taxonomy("dt_taxonomy_v5_seed.sql")
V6_TAX = _seed_taxonomy("dt_taxonomy_v6_seed.sql")

# Fixed rubric config for the byte-stability snapshot (acceptable variation +
# a verifier band descriptor), so the hashes cover those code paths too.
_SNAPSHOT_RUBRIC = {
    "acceptable_variation": {"en": ["synonyms that preserve meaning"], "zh": ["同义替换"], "ja": ["同義の言い換え"]},
    "band_descriptors": {"3": {"naturalness": {
        "en": {"1": "a", "4": "b"}, "zh": {"1": "甲", "4": "乙"}, "ja": {"1": "甲", "4": "乙"},
    }}},
}

# sha256 of the Detector / Verifier system prompts built from the v5 baseline
# subtype lists, captured BEFORE TASK-843 touched prompts.py. Keyed
# (l2, labels) -> (detector, verifier); labels "bare" = slug fallback,
# "glossed" = the v5 seed's subtype_glosses.
_V5_PRE_TASK843_SHA256 = {
    ("en", "bare"): ("94314baae349e9a4cde60a30acfca12948f0966d48ee5ba35a8203d45292104a",
                     "ec63540e167489d9f4c80b28eb3ce9f1af4a81fc8e480e6a0c884ee02c4f54a3"),
    ("en", "glossed"): ("f70120d280a09439111cdf1918043ade198b01c1ee0f617aa684f42bfda8d6ab",
                        "f08ecb6857d09caa140b02eeac7e7b08029e3e022041a7bff285400fdce1828d"),
    ("zh", "bare"): ("0edb61f89c0dcf900505cea77393230a6e8e0d93d0710380bab437622cafbb63",
                     "229f8fa85335edd64f7e84321326f669ff0f5828aa726432d895b5f8030ffae6"),
    ("zh", "glossed"): ("301904087ba9a7b66b640c7f84dfabeabce4c23bee2aee7ddb536b6e97b7a118",
                        "9fa775ae3bb6a3fd0f19886811c95920ff0012353851d7371af8a2eafd6aeb76"),
    ("ja", "bare"): ("e59e7964fb632d266d3bcc1f904fa6998d1f2a9a828d6a391c59d502d6db195b",
                     "9e95460755a5105900bc86f2327e3ef2515b923225c79ece9fd30b7173c4658b"),
    ("ja", "glossed"): ("562e16186a9de2192f68440a6562309fd12ae92c2f614e5cb968f47999d2d722",
                        "8e792093d0ed4505cc569e6b5502b74b7dd2edf6d6011b186e7b7232e722a587"),
}

# The opening phrase of each L2's precedence block, and of the Verifier addendum.
_PRECEDENCE_MARKER = {
    "en": "Meaning inversion — label by EFFECT",
    "zh": "语义反转——按效果标注",
    "ja": "意味の反転——表面形式ではなく効果で判定",
}
_RETYPE_MARKER = {
    "en": "If a proposed error's effect is such an inversion",
    "zh": "若某个待核错误的效果属于上述反转",
    "ja": "審査対象誤りの効果が上記の反転に当たる",
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _v5_labels(l2: str, kind: str):
    subtypes = V5_TAX["pairs"][l2]["subtypes"]
    if kind == "bare":
        return None
    return [V5_TAX["subtype_glosses"].get(s, {}).get(l2) or s for s in subtypes]


@pytest.mark.parametrize("l2", ["en", "zh", "ja"])
@pytest.mark.parametrize("kind", ["bare", "glossed"])
def test_v5_detector_and_verifier_prompts_are_byte_identical_to_pre_task843(l2, kind):
    """Gate proof: under the v5 taxonomy (no meaning_inversion) nothing changes."""
    subtypes = V5_TAX["pairs"][l2]["subtypes"]
    assert "meaning_inversion" not in subtypes
    labels = _v5_labels(l2, kind)
    det = prompts.build_detector_system_prompt(l2, _SNAPSHOT_RUBRIC, subtypes, subtype_labels=labels)
    ver = prompts.build_verifier_system_prompt(l2, _SNAPSHOT_RUBRIC, 3, subtypes, subtype_labels=labels)
    assert (_sha(det), _sha(ver)) == _V5_PRE_TASK843_SHA256[(l2, kind)]
    assert _PRECEDENCE_MARKER[l2] not in det and _PRECEDENCE_MARKER[l2] not in ver


@pytest.mark.parametrize("l2", ["en", "zh", "ja"])
def test_v6_detector_and_verifier_carry_the_precedence_block_once(l2):
    subtypes = V6_TAX["pairs"][l2]["subtypes"]
    assert "meaning_inversion" in subtypes
    det = prompts.build_detector_system_prompt(l2, _SNAPSHOT_RUBRIC, subtypes)
    ver = prompts.build_verifier_system_prompt(l2, _SNAPSHOT_RUBRIC, 3, subtypes)
    assert det.count(_PRECEDENCE_MARKER[l2]) == 1
    assert ver.count(_PRECEDENCE_MARKER[l2]) == 1
    # Re-type instruction is the Verifier's alone.
    assert _RETYPE_MARKER[l2] not in det
    assert ver.count(_RETYPE_MARKER[l2]) == 1
    # Placed right after the subtype list, before span discipline.
    for prompt in (det, ver):
        sub_at = prompt.index(prompts._SUBTYPE_LIST_LABEL[l2])
        block_at = prompt.index(_PRECEDENCE_MARKER[l2])
        span_at = prompt.index(prompts._SPAN_DISCIPLINE[l2])
        assert sub_at < block_at < span_at


@pytest.mark.parametrize("l2", ["en", "zh", "ja"])
def test_v6_precedence_block_references_live_indices_and_critical(l2):
    subtypes = V6_TAX["pairs"][l2]["subtypes"]
    labels = [f"L{i}" for i in range(len(subtypes))]
    block = prompts._precedence_block(l2, subtypes, labels, verifier=True)
    fmt = prompts._SUBTYPE_REF_FORMAT[l2]

    def ref(slug):
        i = subtypes.index(slug)
        return fmt.format(i=i, label=labels[i])

    # (1) by-effect rule -> meaning_inversion; (2)/(3) omission/addition named;
    # (4) contradiction scoped; verifier names the surface-form types.
    for slug in ("meaning_inversion", "omission", "addition", "contradiction", "word_choice"):
        assert ref(slug) in block, slug
    surface = {"en": "preposition", "zh": "coverb", "ja": "case_particle"}[l2]
    assert ref(surface) in block
    # (5) severity critical = index 2 of SEVERITY_ENUM.
    assert prompts.SEVERITY_ENUM.index("critical") == 2
    assert {"en": "critical (2)", "zh": "严重（2）", "ja": "致命的（2）"}[l2] in block


@pytest.mark.parametrize("l2", ["zh", "ja"])
def test_v6_precedence_block_has_no_english_prose(l2):
    subtypes = V6_TAX["pairs"][l2]["subtypes"]
    # With L2 labels: no ASCII word at all.
    cjk_labels = [f"类型{chr(0x4e00 + i)}" for i in range(len(subtypes))]
    for verifier in (False, True):
        block = prompts._precedence_block(l2, subtypes, cjk_labels, verifier=verifier)
        assert block
        assert not _ASCII_WORD.findall(block), _ASCII_WORD.findall(block)
    # With the bare-slug fallback (v6 seed has no glosses yet): only enum slugs.
    slug_tokens = {tok for s in subtypes for tok in s.split("_")}
    block = prompts._precedence_block(l2, subtypes, None, verifier=True)
    leaked = set(_ASCII_WORD.findall(block)) - slug_tokens
    assert not leaked, f"English prose in {l2} precedence block: {leaked}"


def test_precedence_gate_is_meaning_inversion_presence():
    v5_en = V5_TAX["pairs"]["en"]["subtypes"]
    assert prompts._precedence_block("en", v5_en, None, verifier=True) == ""
    assert prompts._precedence_block("en", v5_en + ["meaning_inversion"], None, verifier=False)


# ---------------------------------------------------------------------------
# TASK-844: zh 的/地/得 rule (ADR-031 user ruling: any misuse is de_particle)
# ---------------------------------------------------------------------------

_DE_RULE_MARKER = "结构助词“的、地、得”：三者之间的任何误用"
_DE_VERIFIER_MARKER = "若待核错误是“的、地、得”误用"


def test_de_rule_in_zh_v6_detector_and_verifier_exactly_once():
    subtypes = V6_TAX["pairs"]["zh"]["subtypes"]
    det = prompts.build_detector_system_prompt("zh", _SNAPSHOT_RUBRIC, subtypes)
    ver = prompts.build_verifier_system_prompt("zh", _SNAPSHOT_RUBRIC, 3, subtypes)
    assert det.count(_DE_RULE_MARKER) == 1
    assert ver.count(_DE_RULE_MARKER) == 1
    assert _DE_VERIFIER_MARKER not in det
    assert ver.count(_DE_VERIFIER_MARKER) == 1
    for prompt in (det, ver):
        assert prompt.index(prompts._SUBTYPE_LIST_LABEL["zh"]) < prompt.index(_DE_RULE_MARKER) \
            < prompt.index(prompts._SPAN_DISCIPLINE["zh"])


@pytest.mark.parametrize("l2", ["en", "ja"])
def test_de_rule_absent_from_en_and_ja_v6_prompts(l2):
    subtypes = V6_TAX["pairs"][l2]["subtypes"]
    det = prompts.build_detector_system_prompt(l2, _SNAPSHOT_RUBRIC, subtypes)
    ver = prompts.build_verifier_system_prompt(l2, _SNAPSHOT_RUBRIC, 3, subtypes)
    for prompt in (det, ver):
        assert _DE_RULE_MARKER not in prompt and _DE_VERIFIER_MARKER not in prompt
        assert "地、得" not in prompt


@pytest.mark.parametrize("kind", ["bare", "glossed"])
def test_de_rule_absent_from_zh_v5_prompts(kind):
    subtypes = V5_TAX["pairs"]["zh"]["subtypes"]
    assert "de_particle" not in subtypes  # v5 slug is de_particles
    labels = _v5_labels("zh", kind)
    det = prompts.build_detector_system_prompt("zh", _SNAPSHOT_RUBRIC, subtypes, subtype_labels=labels)
    ver = prompts.build_verifier_system_prompt("zh", _SNAPSHOT_RUBRIC, 3, subtypes, subtype_labels=labels)
    assert _DE_RULE_MARKER not in det and _DE_RULE_MARKER not in ver


def test_de_rule_references_live_indices_and_minor_severity():
    subtypes = V6_TAX["pairs"]["zh"]["subtypes"]
    labels = [f"L{i}" for i in range(len(subtypes))]
    fmt = prompts._SUBTYPE_REF_FORMAT["zh"]

    def ref(slug):
        i = subtypes.index(slug)
        return fmt.format(i=i, label=labels[i])

    det_block = prompts._precedence_block("zh", subtypes, labels, verifier=False)
    rule = det_block[det_block.index(_DE_RULE_MARKER):]
    for slug in ("de_particle", "word_choice", "orthography"):
        assert ref(slug) in rule, slug
    assert prompts.SEVERITY_ENUM.index("minor") == 0
    assert "轻微（0）" in rule
    # Every misuse direction the ruling names. String review 2026-10-07 (zh item
    # 105): the redundant "（含定语位置误用“地”）" was dropped (地-for-的 is
    # attributive by definition) and the missing-得 boundary (跑快 → 跑得快 is
    # de_particle, not complement; reviewer-proposed, pending user confirmation —
    # ADR-031) was added.
    for phrase in ("用“的”代替“地”或“得”", "用“地”代替“的”", "用“得”代替“的”或“地”",
                   "缺少必需的“得”（如“跑快”应为“跑得快”）", "不属于可接受的变体"):
        assert phrase in rule
    ver_block = prompts._precedence_block("zh", subtypes, labels, verifier=True)
    assert prompts.VERDICT_ENUM.index("reject") == 1 and prompts.VERDICT_ENUM.index("adjust") == 2
    tail = ver_block[ver_block.index(_DE_VERIFIER_MARKER):]
    assert "驳回（1）" in tail and "调整（2）" in tail and ref("de_particle") in tail


def test_de_rule_gate_needs_v6_and_de_particle():
    v6_zh = V6_TAX["pairs"]["zh"]["subtypes"]
    no_mi = [s for s in v6_zh if s != "meaning_inversion"]
    assert prompts._precedence_block("zh", no_mi, None, verifier=True) == ""
    no_de = [s for s in v6_zh if s != "de_particle"]
    assert _DE_RULE_MARKER not in prompts._precedence_block("zh", no_de, None, verifier=True)


def _seed_rubric(name: str) -> dict:
    text = (_MIGRATIONS / name).read_text(encoding="utf-8")
    m = re.search(r"\$rubric\$(.*?)\$rubric\$", text, re.S)
    assert m, f"no $rubric$ literal in {name}"
    return json.loads(m.group(1))


def test_de_rubric_v6_zh_acceptable_variation_cannot_cover_a_de_swap():
    """No zh acceptable-variation item may license a 的/地/得 swap: none names
    地 or 得, a structural/auxiliary particle (助词), or 的 as a quoted token."""
    items = _seed_rubric("dt_rubric_v6_seed.sql")["acceptable_variation"]["zh"]
    assert items
    for item in items:
        assert "地" not in item and "得" not in item, item
        assert "助词" not in item, item
        assert not re.search(r"[“\"'「]的", item), item
