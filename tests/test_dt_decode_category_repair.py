"""TASK-862 regression: `_decode_error` must not drop an error whose `category`
index is unusable when its subtype decodes.

qwen (the zh/ja Detector) sometimes copies the subtype index into `category`
(`category: 8, subtype: 8`). Before TASK-862 the whole error was discarded with an
"out-of-range enum index" WARNING; the TASK-850 gate lost zh 2 / ja 3 correct
detections this way (data/eval/dt_v6_gate_2026-10-08/*.log). The raw errors below
are copied verbatim from those logs; the passages are the gold items they were
graded on (tests/fixtures/dt_gold for the v5 arm A, dt_gold_v6 for arm B), inlined
so this test does not depend on fixture files that are still being edited.
"""

import json
import logging
import pathlib
import re

import pytest

from services.dual_translation import grader_cascade, prompts

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _extract_taxonomy(name: str) -> dict:
    text = (_ROOT / "migrations" / name).read_text(encoding="utf-8")
    m = re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", text, re.DOTALL)
    assert m, f"no $taxonomy$ literal in {name}"
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def tax_v5() -> dict:
    return _extract_taxonomy("dt_taxonomy_v5_seed.sql")


@pytest.fixture(scope="module")
def tax_v6() -> dict:
    return _extract_taxonomy("dt_taxonomy_v6_seed.sql")


# zh_multi_03 (v5 gold) — 一只→一个 classifier error.
ZH_MULTI_03_REF = "这件T恤最特别的地方是它的图案。在T恤的胸口位置，有一个小小的、很可爱的图画。这个图画是一只正在微笑的小猫，它好像在看着我，又好像在和我说话。小猫的眼睛是圆圆的，带着一点点好奇，它的嘴角微微向上翘起，看起来非常开心。"
ZH_MULTI_03_REPRO = "这件T恤最特别的地方是它的图案。在T恤的胸口位置，有一个小小的、很可爱的图画。这个图画是一个正在微笑的小猫，它好像在看着我，又好像在和我说话。小猫的眼睛是圆圆的，带着一点点好奇，它的嘴角微微向上翘起，看起来非常伤心。"

# zh_multi_01 (v6 gold) — 一件→一个 measure word + 洗了→洗 aspect omission.
ZH_MULTI_01_REF = "我最喜欢的T恤是一件非常特别的衣服。它不是那种很贵的牌子，也不是最新款式的，但它是我所有衣服里最喜欢的。这件T恤是蓝色的，颜色很正，洗了很多次也不会褪色。它的布料很舒服，穿在身上软软的，很透气，夏天穿也不会觉得热。"
ZH_MULTI_01_REPRO = "我最喜欢的T恤是一个非常特别的衣服。它不是那种很贵的牌子，也不是最新款式的，但它是我所有衣服里最喜欢的。这件T恤是蓝色的，颜色很正，洗很多次也不会褪色。它的布料很舒服，穿在身上软软的，很透气，夏天穿也不会觉得热。"

# ja_seed_04 (identical in v5 and v6 gold) — です→だ register downgrade.
JA_SEED_04_REF = "私たちが作るものは、小さな物を掴むことができる、とてもシンプルなロボットアームです。これは「電子工作」の楽しさを体験するのにぴったりで、完成した時の達成感は格別ですよ。どうやって作るの？このロボットアームを作るには、いくつかの部品が必要です。"
JA_SEED_04_REPRO = "私たちが作るものは、小さな物を掴むことができる、とてもシンプルなロボットアームです。これは「電子工作」の楽しさを体験するのにぴったりで、完成した時の達成感は格別ですよ。どうやって作るの？このロボットアームを作るには、いくつかの部品が必要だ。"

# ja_multi_03 (v6 gold) — 教え込みます→教え込む register downgrade.
JA_MULTI_03_REF = "プログラミング: ここが一番面白いところかもしれません。アームをどのように動かしたいか、例えば「左に動かす」「物を掴む」「右に動かす」といった指示を、コンピューターに分かりやすい言葉（プログラミング言語）で教え込みます。この「プログラミング」によって、ロボットアームは私たちの指示通りに動くようになるのです。テストする: 組み立てとプログラミングが終わったら、実際に動かしてテストしてみましょう。"
JA_MULTI_03_REPRO = "プログラミング: ここが一番難しいところかもしれません。アームをどのように動かしたいか、例えば「左に動かす」「物を掴む」「右に動かす」といった指示を、コンピューターに分かりやすい言葉（プログラミング言語）で教え込む。この「プログラミング」によって、ロボットアームは私たちの指示通りに動くようになるのです。テストする: 組み立てとプログラミングが終わったら、実際に動かしてテストしてみましょう。"


# (case id, taxonomy, l2, reference, reproduction, raw error, expected subtype,
#  expected category, expected learner_form, expected corrected_form)
DROPPED_CASES = [
    (
        "zh_A_zh_multi_03_classifier", "v5", "zh", ZH_MULTI_03_REF, ZH_MULTI_03_REPRO,
        {'span_repro': [44, 46], 'span_ref': [44, 46], 'category': 8, 'source': 1, 'severity': 1,
         'subtype': 8, 'learner_form': '一个', 'corrected_form': '一只', 'confidence': 0.95,
         'is_mistake': False},
        "classifier", "grammatical", "一个", "一只",
    ),
    (
        "zh_B_zh_multi_01_measure_word", "v6", "zh", ZH_MULTI_01_REF, ZH_MULTI_01_REPRO,
        {'span_repro': [8, 10], 'span_ref': [8, 10], 'category': 8, 'source': 0, 'severity': 0,
         'subtype': 8, 'learner_form': '一个', 'corrected_form': '一件', 'confidence': 0.95,
         'is_mistake': False},
        "measure_word", "grammatical", "一个", "一件",
    ),
    (
        "zh_B_zh_multi_01_missing_le", "v6", "zh", ZH_MULTI_01_REF, ZH_MULTI_01_REPRO,
        {'span_repro': [68, 68], 'span_ref': [68, 69], 'category': 9, 'source': 0, 'severity': 0,
         'subtype': 9, 'learner_form': '', 'corrected_form': '了', 'confidence': 0.9,
         'is_mistake': False},
        "aspect_negation", "grammatical", "", "了",
    ),
    (
        "ja_A_ja_seed_04_da_desu", "v5", "ja", JA_SEED_04_REF, JA_SEED_04_REPRO,
        {'span_repro': [117, 118], 'span_ref': [117, 119], 'category': 5, 'source': 1, 'severity': 1,
         'subtype': 5, 'learner_form': 'だ', 'corrected_form': 'です', 'confidence': 0.95,
         'is_mistake': True},
        "register", "pragmatic_expressional", "だ", "です",
    ),
    (
        "ja_B_ja_seed_04_da_desu", "v6", "ja", JA_SEED_04_REF, JA_SEED_04_REPRO,
        {'span_repro': [118, 119], 'span_ref': [118, 120], 'category': 5, 'source': 0, 'severity': 0,
         'subtype': 5, 'learner_form': 'だ', 'corrected_form': 'です', 'confidence': '0.95',
         'is_mistake': True, 'explanation_variant': 0},
        "register", "pragmatic_expressional", "だ", "です",
    ),
    (
        "ja_B_ja_multi_03_masu", "v6", "ja", JA_MULTI_03_REF, JA_MULTI_03_REPRO,
        {'span_repro': [109, 111], 'span_ref': [109, 111], 'category': 5, 'source': 1, 'severity': 1,
         'subtype': 5, 'learner_form': '', 'corrected_form': 'ます', 'confidence': 0.9,
         'is_mistake': False},
        "register", "pragmatic_expressional", "", "ます",
    ),
]


@pytest.mark.parametrize(
    "case_id, tax_name, l2, reference, reproduction, raw, exp_subtype, exp_category, exp_learner, exp_corrected",
    DROPPED_CASES,
    ids=[c[0] for c in DROPPED_CASES],
)
def test_gate_dropped_error_is_now_kept(
    request, caplog, case_id, tax_name, l2, reference, reproduction, raw,
    exp_subtype, exp_category, exp_learner, exp_corrected,
):
    tax = request.getfixturevalue(f"tax_{tax_name}")
    subtypes = grader_cascade._resolve_subtypes(tax, "en", l2)
    with caplog.at_level(logging.WARNING, logger=grader_cascade.logger.name):
        decoded = grader_cascade._decode_error(dict(raw), subtypes, tax, "en", reproduction, reference, l2)

    assert decoded is not None, f"{case_id} still dropped"
    assert decoded["subtype"] == exp_subtype
    assert decoded["category"] == exp_category
    assert decoded["category"] in prompts.CATEGORY_ENUM
    assert decoded["learner_form"] == exp_learner
    assert decoded["corrected_form"] == exp_corrected
    # span <-> form invariant (test_dt_error_span_invariant): a non-empty form
    # sits exactly at its span; an empty form only needs an in-bounds span.
    for text, span_key, form_key in (
        (reproduction, "span_reproduction", "learner_form"),
        (reference, "span_reference", "corrected_form"),
    ):
        s, e = decoded[span_key]
        assert 0 <= s <= e <= len(text)
        if decoded[form_key]:
            assert text[s:e] == decoded[form_key]
    # the repair is logged with the raw category value, and nothing says "dropping"
    repair = [r.getMessage() for r in caplog.records if "repaired invalid category" in r.getMessage()]
    assert len(repair) == 1 and repr(raw["category"]) in repair[0]
    assert not any("dropping error" in r.getMessage() for r in caplog.records)


def test_batch_decode_keeps_both_zh_b_errors(tax_v6):
    """zh_multi_01 lost BOTH gold errors in arm B; through `_decode_errors` both survive."""
    subtypes = grader_cascade._resolve_subtypes(tax_v6, "en", "zh")
    raws = [dict(c[5]) for c in DROPPED_CASES if c[0].startswith("zh_B_")]
    decoded = grader_cascade._decode_errors(raws, subtypes, tax_v6, "en", ZH_MULTI_01_REPRO, ZH_MULTI_01_REF, "zh")
    assert [d["subtype"] for d in decoded] == ["measure_word", "aspect_negation"]


def test_valid_category_is_not_overridden(tax_v5, caplog):
    """A usable model category is kept as-is (no derivation, no repair log)."""
    subtypes = grader_cascade._resolve_subtypes(tax_v5, "en", "zh")
    raw = dict(DROPPED_CASES[0][5], category=1)  # lexical, even though classifier derives grammatical
    with caplog.at_level(logging.WARNING, logger=grader_cascade.logger.name):
        decoded = grader_cascade._decode_error(raw, subtypes, tax_v5, "en", ZH_MULTI_03_REPRO, ZH_MULTI_03_REF, "zh")
    assert decoded["category"] == "lexical"
    assert not any("repaired invalid category" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("bad_category", [None, "lexical?", -1, 3, "x"])
def test_non_index_category_values_are_repaired(tax_v5, bad_category):
    subtypes = grader_cascade._resolve_subtypes(tax_v5, "en", "zh")
    raw = dict(DROPPED_CASES[0][5], category=bad_category)
    decoded = grader_cascade._decode_error(raw, subtypes, tax_v5, "en", ZH_MULTI_03_REPRO, ZH_MULTI_03_REF, "zh")
    assert decoded is not None and decoded["category"] == "grammatical"


@pytest.mark.parametrize("bad_subtype", [99, -1, None, "classifier"])
def test_undecodable_subtype_is_still_dropped(tax_v5, caplog, bad_subtype):
    """Only the subtype is load-bearing: if it can't be decoded the error goes."""
    subtypes = grader_cascade._resolve_subtypes(tax_v5, "en", "zh")
    raw = dict(DROPPED_CASES[0][5], category=bad_subtype if isinstance(bad_subtype, int) else 8, subtype=bad_subtype)
    with caplog.at_level(logging.WARNING, logger=grader_cascade.logger.name):
        decoded = grader_cascade._decode_error(raw, subtypes, tax_v5, "en", ZH_MULTI_03_REPRO, ZH_MULTI_03_REF, "zh")
    assert decoded is None
    assert any("dropping error with out-of-range enum index" in r.getMessage() for r in caplog.records)


def test_invalid_source_or_severity_still_drops(tax_v5):
    """TASK-862 relaxes `category` only; source/severity stay strict."""
    subtypes = grader_cascade._resolve_subtypes(tax_v5, "en", "zh")
    for field in ("source", "severity"):
        raw = dict(DROPPED_CASES[0][5], **{field: 9})
        assert grader_cascade._decode_error(raw, subtypes, tax_v5, "en", ZH_MULTI_03_REPRO, ZH_MULTI_03_REF, "zh") is None


def test_derive_category_every_pair_subtype_is_valid(tax_v5, tax_v6):
    """Totality: every subtype the model can be shown derives a CATEGORY_ENUM value."""
    for tax in (tax_v5, tax_v6):
        for l2 in ("en", "zh", "ja"):
            for slug in grader_cascade._resolve_subtypes(tax, "en" if l2 != "en" else "zh", l2):
                assert grader_cascade._derive_category(tax, slug) in prompts.CATEGORY_ENUM


def test_derive_category_precedence():
    tax = {"subtype_meta": {
        "explicit": {"category": "lexical", "class": "G", "dimension": "accuracy"},
        "by_class": {"class": "R", "dimension": "accuracy"},
        "register": {"dimension": "fidelity"},
        "by_dim": {"dimension": "naturalness"},
        "odd_class": {"class": {"en": "G"}, "dimension": "fidelity"},
    }}
    assert grader_cascade._derive_category(tax, "explicit") == "lexical"
    assert grader_cascade._derive_category(tax, "by_class") == "pragmatic_expressional"
    assert grader_cascade._derive_category(tax, "register") == "pragmatic_expressional"
    assert grader_cascade._derive_category(tax, "by_dim") == "pragmatic_expressional"
    assert grader_cascade._derive_category(tax, "odd_class") == "lexical"
    assert grader_cascade._derive_category(tax, "no_meta") == "grammatical"
    assert grader_cascade._derive_category({}, "anything") == "grammatical"
    assert grader_cascade._derive_category(None, "anything") == "grammatical"
