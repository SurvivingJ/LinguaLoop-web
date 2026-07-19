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
