"""TASK-841: DT_TAXONOMY_VERSION pin + v5→v6 alias for rubric worked exemplars.

DB-free. The loaders are exercised against a tiny fake Supabase query chain that
records its filters; the exemplar alias is exercised against the real seeds on
disk (rubric v6 = live rubric, taxonomy v5 = live, taxonomy v6 = inactive seed),
so a drift in either seed shows up here.
"""

import json
import pathlib
import re

import pytest

from services.dimension_service import DimensionService
from services.dual_translation import grader_cascade, prompts, tier0

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIG = ROOT / "migrations"


def _literal(path: pathlib.Path, tag: str) -> dict:
    m = re.search(rf"\${tag}\$(.*?)\${tag}\$", path.read_text(encoding="utf-8"), re.DOTALL)
    assert m, f"no ${tag}$ literal in {path.name}"
    return json.loads(m.group(1))


RUBRIC = _literal(MIG / "dt_rubric_v6_seed.sql", "rubric")
TAX_V5 = _literal(MIG / "dt_taxonomy_v5_seed.sql", "taxonomy")
TAX_V6 = _literal(MIG / "dt_taxonomy_v6_seed.sql", "taxonomy")


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.delenv("DT_TAXONOMY_VERSION", raising=False)
    grader_cascade.clear_caches()
    yield
    grader_cascade.clear_caches()


# ---------------------------------------------------------------------------
# Fake Supabase: rows of dt_taxonomy_version; records every filter applied.
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, log):
        self._rows, self._log = list(rows), log
        self._col = None
        self._desc = False

    def select(self, col):
        self._col = col
        self._log.append(("select", col))
        return self

    def eq(self, col, val):
        self._log.append(("eq", col, val))
        self._rows = [r for r in self._rows if r[col] == val]
        return self

    def order(self, col, desc=False):
        self._log.append(("order", col, desc))
        self._rows.sort(key=lambda r: r[col], reverse=desc)
        return self

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    def execute(self):
        return _Resp([{self._col: r[self._col]} for r in self._rows])


class _FakeDB:
    def __init__(self, rows):
        self.rows, self.log = rows, []

    def table(self, name):
        assert name == "dt_taxonomy_version"
        return _Query(self.rows, self.log)


def _db():
    # Mirrors the live state before TASK-853: v5 active, v6 seeded inactive.
    return _FakeDB([
        {"version": 5, "is_active": True, "taxonomy": TAX_V5},
        {"version": 6, "is_active": False, "taxonomy": TAX_V6},
    ])


# ---------------------------------------------------------------------------
# The pin
# ---------------------------------------------------------------------------

def test_pin_unset_loads_highest_active_row_exactly_as_before():
    db = _db()
    assert grader_cascade.get_active_taxonomy(db) is TAX_V5
    assert grader_cascade.get_active_taxonomy_version(db) == 5
    assert ("eq", "is_active", True) in db.log
    assert not any(e[:2] == ("eq", "version") for e in db.log)


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_pin_is_unset(monkeypatch, blank):
    monkeypatch.setenv("DT_TAXONOMY_VERSION", blank)
    assert grader_cascade.taxonomy_version_pin() is None
    assert grader_cascade.get_active_taxonomy(_db()) is TAX_V5


def test_pin_6_loads_inactive_v6_and_reports_6(monkeypatch):
    monkeypatch.setenv("DT_TAXONOMY_VERSION", "6")
    db = _db()
    assert grader_cascade.get_active_taxonomy(db) is TAX_V6
    assert grader_cascade.get_active_taxonomy_version(db) == 6
    assert ("eq", "version", 6) in db.log
    assert ("eq", "is_active", True) not in db.log


def test_pin_is_read_at_call_time_and_cache_is_keyed_on_version(monkeypatch):
    db = _db()
    assert grader_cascade.get_active_taxonomy(db) is TAX_V5
    monkeypatch.setenv("DT_TAXONOMY_VERSION", "6")
    assert grader_cascade.get_active_taxonomy(db) is TAX_V6
    monkeypatch.delenv("DT_TAXONOMY_VERSION")
    assert grader_cascade.get_active_taxonomy(db) is TAX_V5
    assert grader_cascade.get_active_taxonomy_version(db) == 5


def test_activation_needs_clear_caches_before_v6_is_stamped():
    """TASK-853 runbook: the unpinned taxonomy / taxonomy_version caches live for
    the process, so a worker that graded under v5 keeps grading + stamping v5
    after v6 is activated until it is restarted or clear_caches() runs."""
    db = _db()
    assert grader_cascade.get_active_taxonomy_version(db) == 5
    assert "classifier" in grader_cascade._resolve_subtypes(grader_cascade.get_active_taxonomy(db), "en", "zh")
    # operator activates v6 (dt_taxonomy_v6_activate.sql)
    for row in db.rows:
        row["is_active"] = row["version"] == 6
    # not restarted: still v5 (the hazard the runbook step closes)
    assert grader_cascade.get_active_taxonomy(db) is TAX_V5
    assert grader_cascade.get_active_taxonomy_version(db) == 5
    grader_cascade.clear_caches()
    assert grader_cascade.get_active_taxonomy_version(db) == 6
    tax = grader_cascade.get_active_taxonomy(db)
    assert tax is TAX_V6
    subtypes = grader_cascade._resolve_subtypes(tax, "en", "zh")
    assert subtypes == grader_cascade._resolve_subtypes(TAX_V6, "en", "zh")
    assert "measure_word" in subtypes and "classifier" not in subtypes


def test_pin_to_unknown_version_raises(monkeypatch):
    monkeypatch.setenv("DT_TAXONOMY_VERSION", "99")
    with pytest.raises(RuntimeError, match="version=99"):
        grader_cascade.get_active_taxonomy(_db())


def test_non_integer_pin_raises(monkeypatch):
    monkeypatch.setenv("DT_TAXONOMY_VERSION", "v6")
    with pytest.raises(RuntimeError, match="not an integer"):
        grader_cascade.get_active_taxonomy(_db())


# ---------------------------------------------------------------------------
# Exemplar alias
# ---------------------------------------------------------------------------

def _subtypes(tax, l2):
    return grader_cascade._resolve_subtypes(tax, "en" if l2 != "en" else "zh", l2)


@pytest.mark.parametrize("l2", ["en", "zh", "ja"])
def test_v5_taxonomy_leaves_rubric_untouched(l2):
    subtypes = _subtypes(TAX_V5, l2)
    assert "legacy_aliases" not in TAX_V5
    assert grader_cascade.alias_rubric_exemplars(RUBRIC, TAX_V5, subtypes) is RUBRIC


@pytest.mark.parametrize("l2", ["en", "zh", "ja"])
def test_v5_prompts_byte_identical(l2):
    subtypes = _subtypes(TAX_V5, l2)
    aliased = grader_cascade.alias_rubric_exemplars(RUBRIC, TAX_V5, subtypes)
    assert (prompts.build_detector_system_prompt(l2, aliased, subtypes)
            == prompts.build_detector_system_prompt(l2, RUBRIC, subtypes))
    assert (prompts.build_verifier_system_prompt(l2, aliased, 3, subtypes)
            == prompts.build_verifier_system_prompt(l2, RUBRIC, 3, subtypes))
    assert (prompts.build_system_prompt("tier1", l2, aliased, 3, subtypes)
            == prompts.build_system_prompt("tier1", l2, RUBRIC, 3, subtypes))


@pytest.mark.parametrize("l2, v5_slug, v6_slug", [
    ("en", "tense_aspect", "verb_form_tense"),
    ("zh", "aspect_marker", "aspect_negation"),
])
def test_v6_maps_en_and_zh_exemplars(l2, v5_slug, v6_slug):
    subtypes = _subtypes(TAX_V6, l2)
    assert RUBRIC["exemplars"][l2]["error"]["subtype_slug"] == v5_slug
    assert v5_slug not in subtypes and v6_slug in subtypes

    # Without the alias the v6 Detector prompt has no worked exemplar at all.
    assert prompts._detector_exemplar_text(RUBRIC, l2, subtypes) == ""

    aliased = grader_cascade.alias_rubric_exemplars(RUBRIC, TAX_V6, subtypes)
    assert aliased["exemplars"][l2]["error"]["subtype_slug"] == v6_slug
    block = prompts._detector_exemplar_text(aliased, l2, subtypes)
    assert block, "exemplar should render under v6 once aliased"
    assert f'"subtype": {subtypes.index(v6_slug)}' in block
    assert prompts._exemplar_text(aliased, l2, prompts.TIER_DIMENSIONS["tier1"], subtypes)


def test_v6_ja_split_exemplar_is_still_dropped(caplog):
    subtypes = _subtypes(TAX_V6, "ja")
    assert TAX_V6["legacy_aliases"]["particle_wa_ga"]["kind"] == "split"
    aliased = grader_cascade.alias_rubric_exemplars(RUBRIC, TAX_V6, subtypes)
    assert aliased["exemplars"]["ja"] is RUBRIC["exemplars"]["ja"]
    with caplog.at_level("WARNING"):
        assert prompts._detector_exemplar_text(aliased, "ja", subtypes) == ""
    assert "dropping the ja Detector exemplar" in caplog.text


def test_alias_never_mutates_the_cached_rubric():
    before = json.dumps(RUBRIC, sort_keys=True, ensure_ascii=False)
    grader_cascade.alias_rubric_exemplars(RUBRIC, TAX_V6, _subtypes(TAX_V6, "en"))
    assert json.dumps(RUBRIC, sort_keys=True, ensure_ascii=False) == before


def test_alias_covers_detector_map_and_skips_split_and_dropped():
    tax = {"legacy_aliases": {
        "old_a": {"to": "new_a", "kind": "1:1"},
        "old_b": {"to": "new_b", "kind": "merge"},
        "old_c": {"to": "new_c", "kind": "split"},
        "old_d": {"to": None, "kind": "dropped"},
    }}
    rubric = {"exemplars": {
        "en": {"error": {"subtype_slug": "old_a"}},
        "zh": {"error": {"subtype_slug": "old_c"}},
        "ja": {"error": {"subtype_slug": "old_d"}},
        "detector": {"en": {"error": {"subtype_slug": "old_b"}}},
        "verifier": {"en": {"json": {"verdicts": []}}},
    }}
    subtypes = ["new_a", "new_b", "new_c"]
    out = grader_cascade.alias_rubric_exemplars(rubric, tax, subtypes)
    ex = out["exemplars"]
    assert ex["en"]["error"]["subtype_slug"] == "new_a"
    assert ex["detector"]["en"]["error"]["subtype_slug"] == "new_b"
    assert ex["zh"] is rubric["exemplars"]["zh"]
    assert ex["ja"] is rubric["exemplars"]["ja"]
    assert ex["verifier"] is rubric["exemplars"]["verifier"]
    # An alias whose target is not in this call's subtype list is not applied.
    assert grader_cascade.alias_rubric_exemplars(rubric, tax, ["new_c"]) is rubric


# ---------------------------------------------------------------------------
# Wiring: grade_submission hands the aliased rubric to the grading flow
# ---------------------------------------------------------------------------

def test_grade_submission_passes_aliased_rubric_under_pin(monkeypatch):
    monkeypatch.setenv("DT_TAXONOMY_VERSION", "6")
    monkeypatch.setattr(DimensionService, "get_language_code",
                        classmethod(lambda cls, lid: {1: "zh", 2: "en"}.get(lid)))
    monkeypatch.setattr(grader_cascade, "get_active_rubric", lambda db: RUBRIC)
    tier0.clear_cache()
    captured = {}

    def _fake_v2(db, **kw):
        captured.update(kw)
        return {"captured": True}

    monkeypatch.setattr(grader_cascade, "_grade_v2", _fake_v2)
    out = grader_cascade.grade_submission(
        _db(), passage_id=-841, gold_l2="She has lived in Osaka since 2019.",
        reproduction="She lives in Osaka since 2019.", l2_language_id=2,
        l1_language_id=1, age_tier=3, framework_v2=True,
    )
    tier0.clear_cache()
    assert out == {"captured": True}
    assert captured["taxonomy_cfg"] is TAX_V6
    assert "meaning_inversion" in captured["subtypes"]
    assert captured["rubric_cfg"]["exemplars"]["en"]["error"]["subtype_slug"] == "verb_form_tense"
