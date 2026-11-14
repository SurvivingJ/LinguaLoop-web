"""Sentence model and step planner (tech 3.1, 3.2)."""

import pytest

from services.dual_translation.repair import planner, sentences, settings

GOLD = "It's a great way to learn by doing. Arduino is great. You can make many things with it. This arm is one idea."
REPRO = "It's a sick way to learn by doing. Arduino is great. You can make many things without it. This arm is one idea."
SC = {"overall_band": 3, "scores": {"accuracy": 3, "fidelity": 2}, "grader_trace": {"tier": "single_call"}}


def err(eid, idx, form, *, subtype="register", severity="major", conf=0.9, source="exact",
        text=REPRO, corrected="x", correction="model_quote", span=None):
    if span is None:
        start = text.index(form)
        span = [start, start + len(form)]
    return {"id": eid, "sentence_index": idx, "span_reproduction": span, "span_reference": [0, 1],
            "subtype": subtype, "severity": severity, "confidence": conf, "span_source": source,
            "correction_source": correction, "learner_form": form, "corrected_form": corrected}


@pytest.fixture
def model():
    return sentences.sentence_model(GOLD, REPRO)


class TestSentences:
    def test_offsets_strip_whitespace(self):
        m = sentences.sentence_model("  A b.  C d. ", " A x.   C d.")
        assert [(p.repro_start, p.repro_end) for p in m] == [(1, 5), (8, 12)]
        assert [(p.ref_start, p.ref_end) for p in m] == [(2, 6), (8, 12)]

    def test_local_span_clamped(self):
        assert sentences.local_span([7, 11], 0, 34) == (7, 11)
        assert sentences.local_span([30, 40], 0, 34) == (30, 34)
        assert sentences.local_span([50, 60], 0, 34) is None

    def test_merged_pairs_join_l1(self, monkeypatch):
        gold = "A one. B two. C three."
        repro = "A one and B two. C three."
        m = sentences.sentence_model(gold, repro)
        gold_s = sentences.split_sentences(gold)
        prompts = sentences.positional_prompts(gold_s, ["甲。", "乙。", "丙。"], m, "zh")
        assert len(m) == 2 and prompts[0] == "甲。乙。" and prompts[1] == "丙。"

    def _db(self, sentences_rows, refs):
        class Q:
            def __init__(self, data): self.data = data
            def __getattr__(self, name): return lambda *a, **k: self
            def execute(self): return self
        class DB:
            def table(self, name):
                return Q(sentences_rows if name == "test_sentences" else refs)
        return DB()

    def test_rule1_range_passage(self):
        gold = "A one. B two."
        m = sentences.sentence_model(gold, gold)
        db = self._db([{"id": 1, "idx": 3}, {"id": 2, "idx": 4}],
                      [{"sentence_id": 1, "l1_text": "甲。", "review_verdict": "pass"},
                       {"sentence_id": 2, "l1_text": "乙。", "review_verdict": "rewritten"}])
        passage = {"sentence_start": 3, "sentence_end": 4, "source_ref_id": "t"}
        prompts, whole = sentences.l1_context(db, passage=passage, gold_l2=gold, l1_language_id=1,
                                              l1_code="zh", model=m, l1_passage_text=None)
        assert prompts == ["甲。", "乙。"] and whole == "甲。乙。"

    def test_rule2_passage_reference_split(self):
        gold = "A one. B two."
        m = sentences.sentence_model(gold, gold)
        prompts = sentences.l1_prompts(None, passage={}, gold_l2=gold, l1_language_id=1, l1_code="zh",
                                       model=m, l1_passage_text="甲。乙。")
        assert prompts == ["甲。", "乙。"]

    def test_rule3_count_mismatch_is_null(self):
        gold = "A one. B two."
        m = sentences.sentence_model(gold, gold)
        prompts, whole = sentences.l1_context(None, passage={}, gold_l2=gold, l1_language_id=1,
                                              l1_code="zh", model=m, l1_passage_text="甲乙。")
        assert prompts == [None, None] and whole == "甲乙。"


class TestEligibility:
    def test_clean(self, model):
        r = planner.plan(SC, [], model, 4)
        assert r["eligible"] and r["status"] == "finished" and r["steps"] == []

    def test_tier0_exact_is_eligible_but_v2_and_fallback_tier0_are_not(self, model):
        t0 = {**SC, "grader_trace": {"tier": "tier0", "deterministic_prefilter": True}}
        assert planner.plan(t0, [], model, 4)["status"] == "finished"
        for trace in ({"tier": "tier2"}, {"tier": "v2"}, {"tier": "tier0", "deterministic_prefilter": False}):
            assert not planner.plan({**SC, "grader_trace": trace}, [], model, 4)["eligible"]

    def test_unpersisted_grade(self, model):
        assert not planner.plan({**SC, "overall_band": None}, [], model, 4)["eligible"]

    def test_null_sentence_index(self, model):
        e = err(1, 0, "sick")
        e["sentence_index"] = None
        assert planner.plan(SC, [e], model, 4)["reason"] == "sentence_index_missing"

    def test_flag_off(self, model, monkeypatch):
        monkeypatch.setattr(settings, "DT_GUIDED_REPAIR", False)
        assert not planner.plan(SC, [], model, 4)["eligible"]


class TestBypass:
    def test_band_of_one(self, model):
        grade = {**SC, "scores": {"accuracy": 1, "fidelity": 3}}
        r = planner.plan(grade, [err(1, 0, "sick")], model, 4)
        assert r["status"] == "bypassed" and r["steps"] == []
        assert [d["step_kind"] for d in r["direct_items"]] == ["direct"]
        assert r["direct_items"][0]["step_order"] is None

    def test_five_flagged(self):
        gold = "A b. C d. E f. G h. I j."
        repro = "A x. C y. E z. G w. I v."
        m = sentences.sentence_model(gold, repro)
        errs = [err(i + 1, i, ch, text=repro) for i, ch in enumerate("xyzwv")]
        assert planner.plan(SC, errs, m, 4)["status"] == "bypassed"
        assert planner.plan(SC, errs[:4], m, 4)["status"] == "open"


class TestSteps:
    def test_primary_error_ordering(self, model):
        minor = err(1, 0, "sick", subtype="register", severity="minor")
        major = err(2, 0, "way", subtype="word_order", severity="major")
        meaning = err(3, 0, "learn", subtype="omission", severity="major")
        r = planner.plan(SC, [minor, major, meaning], model, 4)
        assert r["steps"][0]["error"]["id"] == 3  # major + meaning type wins

    def test_cap_by_severity_then_passage_order(self):
        gold = "A b. C d. E f. G h. K l."
        repro = "A x. C y. E z. G w. K l."
        m = sentences.sentence_model(gold, repro)
        errs = [err(1, 0, "x", severity="minor", text=repro), err(2, 1, "y", severity="major", text=repro),
                err(3, 2, "z", severity="critical", text=repro), err(4, 3, "w", severity="major", text=repro)]
        r = planner.plan(SC, errs, m, 4)
        assert [s["sentence_index"] for s in r["steps"]] == [0, 1, 2, 3]
        assert [s["step_kind"] for s in r["steps"]] == ["direct", "repair", "repair", "repair"]
        assert [s["step_order"] for s in r["steps"]] == [0, 1, 2, 3]

    def test_none_ladder_is_direct(self, model):
        r = planner.plan(SC, [err(1, 0, "sick", subtype="word_choice")], model, 4)
        assert r["steps"][0]["step_kind"] == "direct" and r["steps"][0]["rungs"] == []

    def test_unsure_only_when_every_error_below_threshold(self, model):
        low = err(1, 0, "sick", conf=0.3)
        assert planner.plan(SC, [low], model, 4)["steps"][0]["step_kind"] == "unsure"
        assert planner.plan(SC, [low, err(2, 0, "way", conf=0.6)], model, 4)["steps"][0]["step_kind"] == "repair"

    def test_age_tier_downgrade(self, model):
        assert planner.plan(SC, [err(1, 0, "sick")], model, 2)["steps"][0]["ladder"] == "short"
        assert planner.plan(SC, [err(1, 0, "sick")], model, 3)["steps"][0]["ladder"] == "full"

    def test_location_rules(self, model):
        sentence_level = err(1, 0, "sick", source="sentence")
        assert planner.plan(SC, [sentence_level], model, 4)["steps"][0]["rungs"] == [2, 3]
        wide = err(1, 0, "It's a sick way to learn")
        assert planner.plan(SC, [wide], model, 4)["steps"][0]["location_available"] is False
        point = err(1, 0, "", span=[7, 7])
        step = planner.plan(SC, [point], model, 4)["steps"][0]
        assert step["location_available"] and step["span"] == (7, 7) and step["rungs"] == [1, 2, 3]

    def test_short_rungs(self, model):
        r = planner.plan(SC, [err(1, 2, "without it", subtype="meaning_inversion", severity="critical")], model, 4)
        assert r["steps"][0]["ladder"] == "short" and r["steps"][0]["rungs"] == [1]
        r = planner.plan(SC, [err(1, 2, "without it", subtype="meaning_inversion", source="sentence")], model, 4)
        assert r["steps"][0]["rungs"] == []

    def test_active_is_local(self, model):
        r = planner.plan(SC, [err(1, 2, "without it", subtype="meaning_inversion")], model, 4)
        a = r["steps"][0]["active"]
        learner = REPRO[model[2].repro_start:model[2].repro_end]
        assert learner[a["start"]:a["end"]] == "without it"
