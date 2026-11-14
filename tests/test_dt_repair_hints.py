"""Hint templates, ladders, rungs, rendering and the leak filter (tech 3.2, 5)."""

import json

import pytest

from services.dual_translation import single_call_prompts as sc_prompts
from services.dual_translation.repair import hints

ALL_V6 = sorted({slug for ids in sc_prompts.TYPE_IDS.values() for slug in ids})


def _file():
    with open(hints.TEMPLATE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class TestTemplateFile:
    def test_loads_and_validates(self):
        assert hints.available()
        assert hints.version() == "repair-hints/2026-11-14.1"

    def test_every_v6_slug_has_a_ladder(self):
        data = _file()
        assert len(ALL_V6) == 40
        assert set(data["subtypes"]) == set(ALL_V6)
        for slug in ALL_V6:
            assert data["subtypes"][slug]["ladder"] in hints.LADDERS

    def test_ladder_table(self):
        assert hints.ladder_for("register") == "full"
        assert hints.ladder_for("meaning_inversion") == "short"
        assert hints.ladder_for("topic_comment") == "short"
        assert hints.ladder_for("word_choice") == "none"
        assert hints.ladder_for("not_a_slug") == "short"

    def test_no_corrected_form_placeholder_anywhere(self):
        assert "{c}" not in json.dumps(_file(), ensure_ascii=False)

    def test_coverage(self):
        data = _file()
        for slug in ALL_V6:
            assert "en" in data["subtypes"][slug]["l1"]
        for slug in sc_prompts.TYPE_IDS["en"]:
            assert {"en", "zh", "ja"} <= set(data["subtypes"][slug]["l1"])

    def test_clue_length_limits(self):
        data = _file()
        for slug, entry in data["subtypes"].items():
            for code, t in entry["l1"].items():
                limit = 60 if code in ("zh", "ja") else 120
                assert len(t["clue"].replace("{l}", "xxxxxx")) <= limit, (slug, code)
                assert len(t["label"]) <= 48

    def test_invalid_file_disables_without_raising(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text('{"version": "x"}', encoding="utf-8")
        try:
            assert hints.load(str(bad)) is None
            assert not hints.available()
            bad.write_text(json.dumps({**_file(), "type_neutral": {"en": "x {c}"}}), encoding="utf-8")
            assert hints.load(str(bad)) is None
        finally:
            hints.load()
        assert hints.available()


class TestRungs:
    @pytest.mark.parametrize("ladder,loc,expected", [
        ("full", True, [1, 2, 3]), ("full", False, [2, 3]),
        ("short", True, [1]), ("short", False, []), ("none", True, []), ("none", False, []),
    ])
    def test_table(self, ladder, loc, expected):
        assert hints.rungs(ladder, loc) == expected

    def test_unsure_has_none(self):
        assert hints.rungs("full", True, unsure=True) == []


class TestRenderKind:
    def test_template(self):
        assert hints.render_kind("register", "zh") == ("语体不符", "zh", "template", "register.zh.kind")

    def test_gloss_fallback(self):
        tax = {"subtype_glosses": {"keigo": {"zh": "敬语 — 礼貌程度"}}}
        assert hints.render_kind("keigo", "zh", tax) == ("敬语", "zh", "taxonomy_gloss", "gloss.keigo.zh")

    def test_english_fallback(self):
        assert hints.render_kind("keigo", "zh", None) == ("Politeness level", "en", "template", "keigo.en.kind")

    def test_gloss_head(self):
        assert hints.gloss_head("Register — how formal") == "Register"
        assert hints.gloss_head("语域——正式程度") == "语域"


def _clue(slug, l1, learner, corrected, l2="en", text=None, **kw):
    return hints.render_clue(slug, l1, learner_form=learner, current_text=text or f"It is {learner} here.",
                             corrected_form=corrected, l2_code=l2, **kw)


class TestRenderClue:
    def test_template_with_learner_form(self):
        text, lang, source, tid, blocked = _clue("register", "en", "sick", "great")
        assert "“sick”" in text and "great" not in text
        assert (lang, source, tid, blocked) == ("en", "template", "register.en.clue", False)

    def test_missing_template_is_type_neutral(self):
        text, lang, source, tid, _ = _clue("keigo", "zh", "だ", "です", l2="ja", text="静かだ。")
        assert source == "type_neutral" and tid == "type_neutral.zh" and lang == "zh"

    def test_empty_learner_form_is_type_neutral(self):
        assert _clue("omission", "en", "", "the", text="I saw cat.")[2] == "type_neutral"

    def test_form_not_in_current_text_is_type_neutral(self):
        assert _clue("register", "en", "sick", "great", text="It is cool here.")[2] == "type_neutral"

    def test_unknown_l1_falls_back_to_english_neutral(self):
        text, lang, source, _, _ = _clue("keigo", "es", "x", "y")
        assert (lang, source) == ("en", "type_neutral")

    def test_leak_blocked(self):
        # phrasal_verb clues list "up, out, on, off": a correction to "give up" leaks.
        text, lang, source, tid, blocked = _clue("phrasal_verb", "en", "give", "give up",
                                                 text="I will not give now.")
        assert blocked and source == "type_neutral" and "up" not in text.split()


class TestLeaks:
    def test_plain_positive_and_negative(self):
        assert hints.leaks("Try “great” instead", "sick", "great", "en")
        assert not hints.leaks("Read “sick” again", "sick", "great", "en")

    def test_common_prefix_is_stripped(self):
        # fragment = "about"; "learn" is the learner's own word.
        assert not hints.leaks("Which word follows “learn on”?", "learn on", "learn about", "en")
        assert hints.leaks("Use about after learn", "learn on", "learn about", "en")

    def test_fragment_inside_learner_form_is_not_a_leak(self):
        assert not hints.leaks("Look at “cats” again", "cats", "cat", "en")

    def test_zh(self):
        assert hints.leaks("“没” 应该是 “不”", "没", "不", "zh")
        assert not hints.leaks("看看“我没去”里的否定词", "我没去", "我不去", "zh")

    def test_ja_width_and_kana_folded(self):
        assert hints.leaks("「です」を使いましょう", "だ", "デス", "ja")

    def test_reference_sentence_correction(self):
        text = "Compare it with: You can make many things with it."
        assert hints.leaks(text, "You can make lots without it.", "You can make many things with it.", "en")


# Fixture errors per L2, with corrected forms that are not in the learner's words.
# For every v6 subtype x learner L1 (L1 != L2: a learner's L1 is never the
# passage language) no rendered clue may contain the corrected fragment, and no
# kind label may contain the corrected form.
_FIXTURE_FORMS = {
    "en": [("sick", "great"), ("go to", "went to"), ("on", "about"), ("a apple", "an apple")],
    "zh": [("没", "不"), ("个", "本"), ("的", "得"), ("会", "能")],
    "ja": [("を", "に"), ("だ", "です"), ("食べる", "食べた"), ("本", "冊")],
}
_CLOSED_CLASS_LABELS = {"de_particle", "wa_ga", "ba_bei"}  # list the option set by design (tech 5.4)


@pytest.mark.parametrize("slug", ALL_V6)
@pytest.mark.parametrize("l1", ["en", "zh", "ja"])
def test_no_rendered_hint_contains_the_corrected_form(slug, l1):
    for l2, forms in _FIXTURE_FORMS.items():
        if l2 == l1:
            continue
        for learner, corrected in forms:
            current = f"X {learner} Y"
            text = hints.render_clue(slug, l1, learner_form=learner, current_text=current,
                                     corrected_form=corrected, l2_code=l2)[0]
            fragment = hints._strip_common(corrected, learner).strip()
            assert fragment not in text.replace(learner, ""), (slug, l1, learner, corrected, text)
            label = hints.render_kind(slug, l1)[0]
            if slug not in _CLOSED_CLASS_LABELS:
                assert corrected not in label, (slug, l1, corrected, label)
