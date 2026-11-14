"""Re-check of one revised sentence through the single-call grader (tech 6.1).
The model boundary is single_call_grader.call_structured; no network."""

import json
import os
import re

import pytest

from config import Config
from services.dual_translation import single_call_grader as scg
from services.dual_translation import single_call_prompts as sc_prompts
from services.dual_translation.repair import recheck, settings

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_REPO, "migrations", "dt_taxonomy_v6_seed.sql"), encoding="utf-8") as fh:
    TAXONOMY_V6 = json.loads(re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", fh.read(), re.DOTALL).group(1))

REF = "It's a great way to learn by doing."
REV = "It's a cool way to learn by doing."


class FakeModel:
    def __init__(self, content=None, exc=None):
        self.content, self.exc, self.calls = content, exc, []

    def __call__(self, slug, system, user, *, schema, max_tokens, extra=None, timeout=30):
        self.calls.append({"slug": slug, "system": system, "user": user, "schema": schema,
                           "max_tokens": max_tokens, "extra": extra, "timeout": timeout})
        if self.exc:
            raise self.exc
        content = self.content if isinstance(self.content, str) else json.dumps(self.content)
        return {"content": content, "tokens_in": 2000, "tokens_out": 80, "cached_tokens": 1800,
                "reasoning_tokens": 0, "cost_usd": 0.00008, "latency_s": 1.234,
                "provider": "x", "finish_reason": "stop"}


def _payload(*errors):
    return {"errors": list(errors), "naturalness": {"band": 4, "evidence": "way"},
            "range": {"band": 4, "evidence": "way"}}


def _entry(lq="cool", rq="great", typ="register", conf="high", sev="major"):
    return {"sentence": 1, "learner_quote": lq, "reference_quote": rq, "type": typ, "severity": sev,
            "confidence": conf, "source": "intralingual", "explanation": "“cool” 太口语，应该用 “great”。"}


@pytest.fixture
def logged(monkeypatch):
    calls = []
    monkeypatch.setattr(recheck, "_log_failure", lambda res, *a: calls.append(res["status"]))
    return calls


def _run(monkeypatch, model, l2="en", l1="zh", ref=REF, rev=REV):
    monkeypatch.setattr(scg, "call_structured", model)
    return recheck.recheck_sentence(None, reference_sentence=ref, revised_sentence=rev, l2_code=l2,
                                    l1_code=l1, l2_language_id=2, l1_language_id=1, taxonomy=TAXONOMY_V6)


def test_one_call_one_pair_grading_prompt(monkeypatch, logged):
    model = FakeModel(_payload(_entry()))
    res = _run(monkeypatch, model)
    assert len(model.calls) == 1
    call = model.calls[0]
    assert call["slug"] == Config.DT_SINGLE_CALL_MODEL
    assert call["timeout"] == settings.DT_REPAIR_RECHECK_TIMEOUT_S
    assert call["max_tokens"] == sc_prompts.MAX_TOKENS
    assert call["extra"] == scg.REQUEST_EXTRAS.get(Config.DT_SINGLE_CALL_MODEL)
    assert call["system"] == sc_prompts.build_system_prompt("en", free_translation=False, band_descriptors="")
    assert "S1 REF: " + REF in call["user"] and "S1 LRN: " + REV in call["user"] and "S2" not in call["user"]
    assert res["status"] == "ok" and res["prompt_version"] == sc_prompts.PROMPT_VERSION
    (err,) = res["errors"]
    assert err["subtype"] == "register" and err["span"] == [7, 11] and err["learner_form"] == "cool"
    assert err["corrected_form"] == "great" and err["confidence_label"] == "high"
    assert res["tokens"] == {"in": 2000, "out": 80, "cached": 1800} and res["latency_ms"] == 1234
    assert res["cost_usd"] == 0.00008 and logged == []


def test_timeout(monkeypatch, logged):
    class APITimeoutError(Exception):
        pass
    res = _run(monkeypatch, FakeModel(exc=APITimeoutError("Request timed out.")))
    assert res["status"] == "timeout" and res["errors"] == [] and logged == ["timeout"]


def test_call_failed(monkeypatch, logged):
    res = _run(monkeypatch, FakeModel(exc=RuntimeError("502 bad gateway")))
    assert res["status"] == "call_failed" and logged == ["call_failed"]


def test_malformed(monkeypatch, logged):
    assert _run(monkeypatch, FakeModel("not json"))["status"] == "malformed"
    assert _run(monkeypatch, FakeModel({"nope": 1}))["status"] == "malformed"
    assert logged == ["malformed", "malformed"]


def test_low_confidence_withheld(monkeypatch, logged):
    monkeypatch.setattr(Config, "DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE", False)
    assert _run(monkeypatch, FakeModel(_payload(_entry(conf="low"))))["errors"] == []
    monkeypatch.setattr(Config, "DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE", True)
    assert len(_run(monkeypatch, FakeModel(_payload(_entry(conf="low"))))["errors"]) == 1


def test_clean_revision(monkeypatch, logged):
    res = _run(monkeypatch, FakeModel(_payload()), rev=REF)
    assert res["status"] == "ok" and res["errors"] == []


def test_unsupported_l2_makes_no_call(monkeypatch, logged):
    model = FakeModel(_payload())
    assert _run(monkeypatch, model, l2="es")["status"] == "unsupported"
    assert model.calls == []


def test_taxonomy_mismatch_makes_no_call(monkeypatch, logged):
    model = FakeModel(_payload())
    tax = json.loads(json.dumps(TAXONOMY_V6))
    tax["pairs"] = {"en": {"subtypes": ["omission"]}}
    monkeypatch.setattr(scg, "call_structured", model)
    res = recheck.recheck_sentence(None, reference_sentence=REF, revised_sentence=REV, l2_code="en",
                                   l1_code="zh", l2_language_id=2, l1_language_id=1, taxonomy=tax)
    assert res["status"] == "unsupported" and model.calls == []


def test_zh_sentence(monkeypatch, logged):
    entry = {"sentence": 1, "learner_quote": "没", "reference_quote": "不", "type": "aspect_negation",
             "severity": "major", "confidence": "high", "source": "interlingual",
             "explanation": "Use 不 for habits, not 没."}
    res = _run(monkeypatch, FakeModel(_payload(entry)), l2="zh", l1="en", ref="我不喝咖啡。", rev="我没喝咖啡。")
    assert res["status"] == "ok" and res["errors"][0]["span"] == [1, 2]
