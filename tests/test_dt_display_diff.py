"""Japanese display diff: kana/kanji spellings of the same word are a match
(services/dual_translation/display_diff.py). Display only — grading keeps
Tier 0's character diff."""

import pytest

pytest.importorskip("fugashi")

from services.dual_translation import display_diff as dd
from services.dual_translation import grader_cascade, tier0
from services.dimension_service import DimensionService

GOLD = "この服はわたしのお気に入りです。くまの絵がすきです。"
FALLBACK = [{"op": "replace", "correct": "x", "user": "y", "is_correct": False, "sense_id": None}]


def _changes(gold, user):
    return [(c["op"], c["correct"], c["user"])
            for c in dd.display_diff(gold, user, "ja", FALLBACK) if c["op"] != "equal"]


@pytest.mark.parametrize("gold,user", [
    (GOLD, "この服は私のお気に入りです。熊の絵が好きです。"),  # 私: dictionary reading わたくし
    (GOLD, GOLD),
    ("きょうはいい天気です。", "今日はいい天気です。"),
    ("パンをください。", "ぱんを下さい。"),                      # katakana / hiragana, 下さい
    ("わたしはがくせいです", "私は学生です"),                    # kana split がく+せい
    ("ねこをかいます。", "猫を飼います。"),                      # kana lemma guessed as 買う
    ("東京に行きます", "東京にいきます"),                        # kanji reference, kana answer
])
def test_script_variants_are_matches(gold, user):
    assert _changes(gold, user) == []


def test_matched_cells_keep_both_spellings():
    cells = dd.display_diff(GOLD, "この服は私のお気に入りです。熊の絵が好きです。", "ja", FALLBACK)
    assert {"op": "equal", "correct": "くま", "user": "熊", "is_correct": True, "sense_id": None} in cells
    assert all(c["is_correct"] for c in cells)


def test_real_differences_stay_changes():
    assert _changes(GOLD, "この服は私の一番好きで、熊の絵が好きです。") == [
        ("replace", "お", "一番"), ("replace", "気", "好き"), ("replace", "に", "で"),
        ("delete", "入り", None), ("delete", "です", None),
    ]
    assert _changes("ごはんをたべる。", "ご飯を食べた。") == [
        ("replace", "たべる", "食べ"), ("insert", None, "た")]  # same lemma, other form
    # A different kanji where the reference has kanji is a different word.
    assert _changes("猫を飼います。", "猫を買います。") == [("replace", "飼い", "買い")]


def test_other_languages_and_failures_keep_the_given_diff(monkeypatch):
    assert dd.display_diff("我喜欢猫", "我喜欢狗", "zh", FALLBACK) is FALLBACK

    def _broken():
        raise RuntimeError("no dictionary")
    monkeypatch.setattr(dd, "_get_tagger", _broken)
    assert dd.display_diff(GOLD, GOLD, "ja", FALLBACK) is FALLBACK


def test_grade_submission_shows_the_word_diff_but_grades_on_tier0(monkeypatch):
    """An exact kana answer resolves at Tier 0 as before; a kanji answer still
    goes to the model (grading unchanged) but its shown diff has no changes."""
    monkeypatch.setattr(DimensionService, "get_language_code",
                        classmethod(lambda cls, lid: {2: "en", 3: "ja"}.get(lid)))
    tier0.clear_cache()
    seen = {}

    def _cascade(db, **kw):
        t0 = tier0.grade_tier0(kw["passage_id"], kw["gold_l2"], kw["reproduction"], "ja")
        seen["tier0_changes"] = sum(1 for c in t0.diff if c["op"] != "equal")
        return {"overall_band": 4, "scores": {}, "errors": [], "diff": t0.diff, "grader_trace": {}}
    monkeypatch.setattr(grader_cascade, "_grade_cascade", _cascade)
    contract = grader_cascade.grade_submission(
        None, passage_id=98, gold_l2=GOLD, reproduction="この服は私のお気に入りです。熊の絵が好きです。",
        l2_language_id=3, l1_language_id=2, age_tier=1,
    )
    tier0.clear_cache()
    assert seen["tier0_changes"] > 0  # Tier 0 still sees the kanji as different
    assert [c for c in contract["diff"] if c["op"] != "equal"] == []
