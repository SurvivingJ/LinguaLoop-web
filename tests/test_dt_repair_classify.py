"""Re-check classification (tech 6.3)."""

from services.dual_translation.repair import classify

REF = "It's a great way to learn by doing."
ACTIVE = {"subtype": "register", "severity": "major", "form": "sick", "start": 7, "end": 11,
          "corrected_form": "great", "correction_source": "model_quote", "span_source": "exact"}


def e(subtype, severity, span, form="", corrected="", note=None, conf="high"):
    return {"subtype": subtype, "severity": severity, "span": span, "learner_form": form,
            "corrected_form": corrected, "correction_source": "model_quote", "span_source": "exact",
            "confidence_label": conf, "model_note": note}


def test_target_present_by_subtype():
    text = "It's a cool way to learn by doing."
    r = classify.classify(ACTIVE, text, REF, [e("register", "major", [7, 11], "cool", "great")], "en")
    assert r["result"] == "still_flagged" and r["reason"] == "target_present"
    assert r["active"]["form"] == "cool" and r["active"]["start"] == 7


def test_target_present_by_overlap_with_other_subtype():
    text = "It's a sick way to learn by doing."
    r = classify.classify(ACTIVE, text, REF, [e("word_choice", "minor", [7, 11], "sick")], "en")
    assert r["result"] == "still_flagged" and r["reason"] == "target_present"
    assert r["active"]["subtype"] == "word_choice"


def test_new_major_error_switches_active():
    text = "It's a great way for learn by doing."
    r = classify.classify(ACTIVE, text, REF, [e("preposition", "major", [17, 20], "for", "to", note="n")], "en")
    assert r["result"] == "still_flagged" and r["reason"] == "new_error"
    assert r["active"]["subtype"] == "preposition" and r["detail"]["x"] == "n"


def test_leftover_minor_is_fixed():
    text = "It's a great way to learn by doing"
    r = classify.classify(ACTIVE, text, REF, [e("orthography", "minor", [33, 34], "g")], "en")
    assert r["result"] == "fixed" and r["reason"] is None


def test_corrected_form_missing_is_no_issue_found():
    r = classify.classify(ACTIVE, "It's a fine way to learn by doing.", REF, [], "en")
    assert r["result"] == "no_issue_found"


def test_corrected_form_compare_is_normalised():
    r = classify.classify(ACTIVE, "It's a GREAT way to learn by doing.", REF, [], "en")
    assert r["result"] == "fixed"


def test_reference_sentence_correction():
    active = {**ACTIVE, "correction_source": "reference_sentence", "corrected_form": REF}
    assert classify.classify(active, REF, REF, [], "en")["result"] == "fixed"
    assert classify.classify(active, "It is a great way to learn by doing.", REF, [], "en")["result"] == "no_issue_found"


def test_zh_point_target():
    active = {"subtype": "measure_word", "severity": "minor", "form": "", "start": 2, "end": 2,
              "corrected_form": "本", "correction_source": "model_quote", "span_source": "diff_hunk"}
    r = classify.classify(active, "我有三本书。", "我有三本书。", [], "zh")
    assert r["result"] == "fixed"


def test_detail_is_compact():
    errs = [e("register", "minor", [i, i + 1]) for i in range(8)]
    r = classify.classify({**ACTIVE, "subtype": "x"}, "abcdefghij", REF, errs, "en")
    assert len(r["detail"]["e"]) == 5
    long = e("register", "major", [7, 11], "cool", note="y" * 400)
    assert len(classify.classify(ACTIVE, "It's a cool way.", REF, [long], "en")["detail"]["x"]) == 240


def test_where_for():
    assert classify.where_for(ACTIVE, "It's a sick way to learn by doing.") == {
        "start": 7, "end": 11, "text": "sick", "point": False}
    assert classify.where_for({**ACTIVE, "span_source": "sentence"}, "It's a sick way.") is None
    assert classify.where_for({**ACTIVE, "start": 3, "end": 3}, "abcdef")["point"] is True
