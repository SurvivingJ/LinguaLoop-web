"""TASK-845: word_choice explanation_variant — deterministic resolver + v6 prompt surface.

Fake db only (no network, no writes). Covers each resolver branch: same lemma,
知道/认识-style shared L1 gloss, en-L2 skip (no zh/ja glosses), refuted model
calls, unresolvable lemmas, DB failure, and the ≤2-round-trip batching.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from services.dual_translation import prompts, word_choice_variant as wcv

ZH, EN, JA = 1, 2, 3


# ---------------------------------------------------------------------------
# Fake Supabase client: .table().select().eq().in_().execute() over in-memory rows
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table):
        self._db, self._table, self._filters = db, table, []

    def select(self, _cols):
        return self

    def eq(self, col, val):
        self._filters.append(lambda r: r.get(col) == val)
        return self

    def in_(self, col, vals):
        vals = list(vals)
        self._filters.append(lambda r: r.get(col) in vals)
        return self

    def execute(self):
        self._db.calls.append(self._table)
        if self._table in self._db.fail_tables:
            raise RuntimeError(f"boom: {self._table}")
        rows = self._db.rows.get(self._table, [])
        return _Resp([dict(r) for r in rows if all(f(r) for f in self._filters)])


class FakeDB:
    def __init__(self, rows, fail_tables=()):
        self.rows, self.fail_tables, self.calls = rows, set(fail_tables), []

    def table(self, name):
        return _Query(self, name)


VOCAB = [
    {"id": 10, "language_id": ZH, "lemma": "知道"},
    {"id": 11, "language_id": ZH, "lemma": "认识"},
    {"id": 12, "language_id": ZH, "lemma": "普通"},
    {"id": 13, "language_id": ZH, "lemma": "简单"},
    {"id": 14, "language_id": ZH, "lemma": "借"},
    {"id": 20, "language_id": EN, "lemma": "key"},
    {"id": 21, "language_id": EN, "lemma": "important"},
    {"id": 22, "language_id": EN, "lemma": "borrow"},
    {"id": 23, "language_id": EN, "lemma": "lend"},
]

SENSES = [
    # en glosses of zh words (definition_language_id = EN), both levels.
    {"vocab_id": 10, "definition_language_id": EN, "definition": "know"},
    {"vocab_id": 10, "definition_language_id": EN,
     "definition": "know; be aware of — knowing a fact, not a person"},
    {"vocab_id": 11, "definition_language_id": EN, "definition": "to know (a person); recognize"},
    {"vocab_id": 12, "definition_language_id": EN, "definition": "ordinary; common"},
    {"vocab_id": 13, "definition_language_id": EN, "definition": "simple; easy"},
    # Native zh definitions + a ja gloss sharing the key: must be ignored for L1=en.
    {"vocab_id": 12, "definition_language_id": ZH, "definition": "平常的；一般的"},
    {"vocab_id": 13, "definition_language_id": JA, "definition": "ordinary"},
    # en words' own (en) definitions — there are NO zh/ja glosses of en words.
    {"vocab_id": 22, "definition_language_id": EN, "definition": "take temporarily"},
    {"vocab_id": 23, "definition_language_id": EN, "definition": "give temporarily"},
]


def _db(**kw):
    return FakeDB({"dim_vocabulary": VOCAB, "dim_word_senses": SENSES}, **kw)


def _wc(learner, corrected, model=None):
    return {"subtype": "word_choice", "learner_form": learner,
            "corrected_form": corrected, "explanation_variant": model}


def _resolve_zh(db, errors):
    return wcv.resolve_variants(db, errors, l2_code="zh", l2_language_id=ZH, l1_language_id=EN)


# ---------------------------------------------------------------------------
# Gloss normalisation
# ---------------------------------------------------------------------------

def test_gloss_terms_split_normalise_and_drop_clarifier():
    assert wcv.gloss_terms("to know (a person); recognize") == {"know", "recognize"}
    assert wcv.gloss_terms("The Key, an important point / A Thing") == {"key", "important point", "thing"}
    assert wcv.gloss_terms("spirit; mind — no single English equivalent; covers mood") == {"spirit", "mind"}
    # zh/ja gloss format: full-width separators + parentheticals + —— clarifier.
    assert wcv.gloss_terms("紧张；不安（心理）、焦虑，担心／忧虑 —— 心里绷得很紧") == {
        "紧张", "不安", "焦虑", "担心", "忧虑"}
    assert wcv.gloss_terms("") == set()


def test_normalise_is_exact_not_fuzzy():
    assert wcv.normalise_gloss_term("to know") == wcv.normalise_gloss_term("Know")
    assert wcv.normalise_gloss_term("knows") != wcv.normalise_gloss_term("know")


# ---------------------------------------------------------------------------
# Resolver branches
# ---------------------------------------------------------------------------

def test_shared_l1_gloss_is_false_synonym():
    """知道 vs 认识 — both glossed "know" in the learner's L1 (en)."""
    db = _db()
    errs = [_wc("知道", "认识")]
    counts = _resolve_zh(db, errs)
    assert errs[0]["explanation_variant"] == "false_synonym"
    assert counts == {"same_lemma": 0, "shared_gloss": 1, "model": 0, "default": 0}


def test_shared_gloss_overrides_a_model_wrong_word():
    errs = [_wc("知道", "认识", model="wrong_word")]
    _resolve_zh(_db(), errs)
    assert errs[0]["explanation_variant"] == "false_synonym"


def test_same_lemma_is_wrong_sense_even_against_model():
    errs = [_wc("知道", "知道", model="false_synonym")]
    counts = _resolve_zh(_db(), errs)
    assert errs[0]["explanation_variant"] == "wrong_sense"
    assert counts["same_lemma"] == 1


def test_same_lemma_via_single_resolving_token():
    """知道了 is not a lemma; jieba gives 知道 + 了 and only 知道 resolves."""
    errs = [_wc("知道了", "知道")]
    _resolve_zh(_db(), errs)
    assert errs[0]["explanation_variant"] == "wrong_sense"


def test_two_resolving_tokens_is_unresolvable():
    """普通 + 简单 both resolve → ambiguous → deterministic steps skipped."""
    errs = [_wc("普通简单", "认识", model="false_synonym")]
    counts = _resolve_zh(_db(), errs)
    assert errs[0]["explanation_variant"] == "false_synonym"
    assert counts["model"] == 1


def test_disjoint_glosses_refute_model_false_synonym():
    errs = [_wc("普通", "简单", model="false_synonym")]
    counts = _resolve_zh(_db(), errs)
    assert errs[0]["explanation_variant"] == "wrong_word"
    assert counts["default"] == 1


def test_disjoint_glosses_keep_model_wrong_word():
    errs = [_wc("普通", "简单", model="wrong_word")]
    counts = _resolve_zh(_db(), errs)
    assert errs[0]["explanation_variant"] == "wrong_word"
    assert counts["model"] == 1


def test_model_wrong_sense_refuted_by_different_resolved_lemmas():
    """wrong_sense is narrow: two different dictionary words cannot be it."""
    errs = [_wc("普通", "简单", model="wrong_sense")]
    counts = _resolve_zh(_db(), errs)
    assert errs[0]["explanation_variant"] == "wrong_word"
    assert counts["default"] == 1


def test_missing_model_variant_defaults_to_wrong_word():
    errs = [_wc("普通", "简单")]
    counts = _resolve_zh(_db(), errs)
    assert errs[0]["explanation_variant"] == "wrong_word"
    assert counts["default"] == 1


def test_gloss_lookup_ignores_other_definition_languages():
    """普通 has a ja row "ordinary" on 简单 — only L1=en rows count."""
    errs = [_wc("普通", "简单", model="false_synonym")]
    _resolve_zh(_db(), errs)
    assert errs[0]["explanation_variant"] == "wrong_word"
    errs = [_wc("普通", "简单")]
    wcv.resolve_variants(_db(), errs, l2_code="zh", l2_language_id=ZH, l1_language_id=JA)
    # Under L1=ja only 简单 has a gloss → lookup unavailable → model's (none) → default.
    assert errs[0]["explanation_variant"] == "wrong_word"


def test_unresolvable_lemma_keeps_model_variant():
    errs = [_wc("搞定", "认识", model="false_synonym"), _wc("搞定", "认识", model="wrong_sense")]
    counts = _resolve_zh(_db(), errs)
    assert [e["explanation_variant"] for e in errs] == ["false_synonym", "wrong_sense"]
    assert counts["model"] == 2


@pytest.mark.parametrize("model, expected, basis", [
    ("false_synonym", "false_synonym", "model"),
    ("wrong_word", "wrong_word", "model"),
    (None, "wrong_word", "default"),
])
def test_en_l2_skips_gloss_lookup_and_uses_model(model, expected, basis):
    """en words have no zh/ja glosses → lookup unavailable → the model's call."""
    db = _db()
    errs = [{"subtype": "word_choice", "learner_form": "borrow", "corrected_form": "lend",
             "explanation_variant": model}]
    counts = wcv.resolve_variants(db, errs, l2_code="en", l2_language_id=EN, l1_language_id=ZH)
    assert errs[0]["explanation_variant"] == expected
    assert counts[basis] == 1
    assert db.calls == ["dim_vocabulary", "dim_word_senses"]


def test_en_lemma_resolution_skips_articles():
    errs = [{"subtype": "word_choice", "learner_form": "the key", "corrected_form": "key",
             "explanation_variant": None}]
    wcv.resolve_variants(_db(), errs, l2_code="en", l2_language_id=EN, l1_language_id=ZH)
    assert errs[0]["explanation_variant"] == "wrong_sense"


def test_non_word_choice_errors_get_none_and_are_not_counted():
    errs = [{"subtype": "tense_aspect", "learner_form": "a", "corrected_form": "b",
             "explanation_variant": "false_synonym"},
            {"subtype": "omission", "learner_form": "", "corrected_form": "b"}]
    db = _db()
    counts = _resolve_zh(db, errs)
    assert [e["explanation_variant"] for e in errs] == [None, None]
    assert sum(counts.values()) == 0
    assert db.calls == []


# ---------------------------------------------------------------------------
# Batching + DB failure
# ---------------------------------------------------------------------------

def test_batched_at_most_two_round_trips_per_submission():
    db = _db()
    errs = [_wc("知道", "认识"), _wc("普通", "简单"), _wc("知道", "知道"), _wc("搞定", "认识")]
    counts = _resolve_zh(db, errs)
    assert db.calls == ["dim_vocabulary", "dim_word_senses"]
    assert [e["explanation_variant"] for e in errs] == [
        "false_synonym", "wrong_word", "wrong_sense", "wrong_word"]
    assert counts == {"same_lemma": 1, "shared_gloss": 1, "model": 0, "default": 2}


def test_no_senses_query_when_nothing_needs_glosses():
    db = _db()
    _resolve_zh(db, [_wc("知道", "知道")])
    assert db.calls == ["dim_vocabulary"]


def test_vocabulary_failure_degrades_to_default_and_never_raises():
    db = _db(fail_tables={"dim_vocabulary"})
    errs = [_wc("知道", "认识", model="false_synonym"),
            {"subtype": "tense_aspect", "learner_form": "x", "corrected_form": "y"}]
    counts = _resolve_zh(db, errs)
    assert errs[0]["explanation_variant"] == "wrong_word"
    assert errs[1]["explanation_variant"] is None
    assert counts == {"same_lemma": 0, "shared_gloss": 0, "model": 0, "default": 1}


def test_senses_failure_keeps_same_lemma_and_defaults_the_rest():
    db = _db(fail_tables={"dim_word_senses"})
    errs = [_wc("知道", "知道"), _wc("知道", "认识", model="false_synonym")]
    counts = _resolve_zh(db, errs)
    assert [e["explanation_variant"] for e in errs] == ["wrong_sense", "wrong_word"]
    assert counts == {"same_lemma": 1, "shared_gloss": 0, "model": 0, "default": 1}


def test_db_none_is_a_db_failure_not_a_crash():
    errs = [_wc("知道", "认识", model="wrong_sense")]
    counts = _resolve_zh(None, errs)
    assert errs[0]["explanation_variant"] == "wrong_word"
    assert counts["default"] == 1


def test_resolve_variant_single_form():
    assert wcv.resolve_variant(
        _db(), learner_form="知道", corrected_form="认识", l2_code="zh",
        l1_language_id=EN, model_variant=None, l2_language_id=ZH,
    ) == ("false_synonym", "shared_gloss")
    assert wcv.resolve_variant(
        _db(), learner_form="borrow", corrected_form="lend", l2_code="en",
        l1_language_id=ZH, model_variant="false_synonym", l2_language_id=EN,
    ) == ("false_synonym", "model")


# ---------------------------------------------------------------------------
# Prompt surface (v6-gated; v5 byte-identity is pinned in test_dual_translation_prompts)
# ---------------------------------------------------------------------------

_MIGRATIONS = pathlib.Path(__file__).resolve().parent.parent / "migrations"


def _seed_taxonomy(name: str) -> dict:
    text = (_MIGRATIONS / name).read_text(encoding="utf-8")
    m = re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", text, re.S)
    assert m, f"no $taxonomy$ literal in {name}"
    return json.loads(m.group(1))


V5_TAX = _seed_taxonomy("dt_taxonomy_v5_seed.sql")
V6_TAX = _seed_taxonomy("dt_taxonomy_v6_seed.sql")
_RUBRIC = {"acceptable_variation": {}}
# String review 2026-10-07: en/zh now mark the field required under v6. ja review
# 2026-10-08 (TASK-840): ja follows ("必ず付け"), so its old "（任意" marker was
# replaced by the new opening phrase.
_VARIANT_MARKER = {"en": "explanation_variant (required", "zh": "explanation_variant（子类型为",
                   "ja": "explanation_variant（サブタイプ"}


def test_variant_enum_order_is_the_contract():
    assert prompts.VARIANT_ENUM == ("wrong_word", "wrong_sense", "false_synonym")


@pytest.mark.parametrize("l2", ["en", "zh", "ja"])
def test_v6_prompts_carry_variant_line_and_schema_field_once(l2):
    subtypes = V6_TAX["pairs"][l2]["subtypes"]
    assert prompts.variants_enabled(subtypes)
    det = prompts.build_detector_system_prompt(l2, _RUBRIC, subtypes)
    ver = prompts.build_verifier_system_prompt(l2, _RUBRIC, 3, subtypes)
    wc_ref = prompts._SUBTYPE_REF_FORMAT[l2].format(i=subtypes.index("word_choice"), label="word_choice")
    for prompt in (det, ver):
        assert prompt.count(_VARIANT_MARKER[l2]) == 1
        assert wc_ref in prompt
        assert prompt.count('"explanation_variant": 0') == 1  # errors[] / added_errors[] only


@pytest.mark.parametrize("l2", ["en", "zh", "ja"])
def test_v5_prompts_have_no_variant_surface(l2):
    subtypes = V5_TAX["pairs"][l2]["subtypes"]
    assert not prompts.variants_enabled(subtypes)
    det = prompts.build_detector_system_prompt(l2, _RUBRIC, subtypes)
    ver = prompts.build_verifier_system_prompt(l2, _RUBRIC, 3, subtypes)
    assert "explanation_variant" not in det and "explanation_variant" not in ver


@pytest.mark.parametrize("l2", ["zh", "ja"])
def test_zh_ja_variant_line_has_no_english_prose(l2):
    subtypes = V6_TAX["pairs"][l2]["subtypes"]
    block = prompts._variant_block(l2, subtypes, None)
    latin = re.findall(r"[A-Za-z_]{2,}", block.replace("explanation_variant", "").replace("word_choice", ""))
    assert latin == []
