"""Unit tests for the dual-translation cascade prompt builders (TASK-606).

Covers the two acceptance criteria that are specific to prompts.py: the
prompt is L2-only (no English instructional prose leaking into ZH/JA, modulo
the documented protocol-token exception), and the cacheable system-prompt
prefix is byte-stable for identical inputs (the cascade doc's "cached prefix
must be byte-stable" requirement).
"""

import re

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


def test_validate_raw_response_accepts_well_shaped_payload():
    payload = {"confidence": 0.9, "scores": {"accuracy": 3}, "errors": []}
    assert prompts.validate_raw_response(payload) is True


def test_validate_raw_response_rejects_missing_keys():
    assert prompts.validate_raw_response({"scores": {}, "errors": []}) is False
    assert prompts.validate_raw_response({"confidence": 0.9, "scores": {}}) is False
    assert prompts.validate_raw_response("not a dict") is False


def test_error_has_required_keys():
    good = {
        "span_repro": [0, 1], "span_ref": [0, 1], "category": 0, "source": 0,
        "severity": 0, "subtype": 0, "learner_form": "a", "corrected_form": "b",
        "confidence": 0.5,
    }
    assert prompts.error_has_required_keys(good) is True
    assert prompts.error_has_required_keys({"span_repro": [0, 1]}) is False
