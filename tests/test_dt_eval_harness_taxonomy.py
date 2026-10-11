"""Offline tests for the TASK-849 taxonomy-candidate path in scripts/run_dt_grading_eval.py.

Covers `--fixture-set` loading, `--taxonomy-file` parsing (the unapplied v6 seed), the
config-cache pre-seed that makes grader_cascade serve the candidate with no DB, the
exemplar-drop / no-template log counter, and an end-to-end record -> metrics -> report pass
driven by a STUBBED grader. No network, no DB, no model calls.
"""

import importlib.util
import logging
import pathlib

import pytest

from services.dual_translation import eval_metrics as em
from services.dual_translation import grader_cascade as gc

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_RUNNER_PATH = _ROOT / "scripts" / "run_dt_grading_eval.py"
_spec = importlib.util.spec_from_file_location("run_dt_grading_eval_tax", _RUNNER_PATH)
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)

V6_SEED = _ROOT / "migrations" / "dt_taxonomy_v6_seed.sql"
V5_SEED = _ROOT / "migrations" / "dt_taxonomy_v5_seed.sql"


@pytest.fixture(autouse=True)
def _clean_cache(monkeypatch):
    monkeypatch.delenv("DT_TAXONOMY_VERSION", raising=False)
    gc.clear_caches()
    yield
    gc.clear_caches()


# ---------------------------------------------------------------------------
# --fixture-set
# ---------------------------------------------------------------------------

def test_fixture_set_default_is_v5_dir():
    assert runner.FIXTURE_DIRS["v5"] == runner.FIXTURE_DIR
    assert runner._load_fixture("en") == runner._load_fixture("en", "v5")


@pytest.mark.parametrize("fixture_set", ["v5", "v6", "v6_silver"])
@pytest.mark.parametrize("l2", ["en", "zh", "ja"])
def test_every_fixture_set_loads(fixture_set, l2):
    items = runner._load_fixture(l2, fixture_set)
    assert items and all("expected_errors" in it and "expected_bands" in it for it in items)


def test_v6_fixtures_carry_variants_and_meaning_inversion():
    exp = [e for it in runner._load_fixture("en", "v6") for e in runner._exp_errors(it)]
    assert any(e["subtype"] == "meaning_inversion" for e in exp)
    assert any(e["explanation_variant"] for e in exp if e["subtype"] == "word_choice")
    v5 = [e for it in runner._load_fixture("en", "v5") for e in runner._exp_errors(it)]
    assert not any(e["explanation_variant"] for e in v5)


# ---------------------------------------------------------------------------
# --taxonomy-file parse + pre-seed
# ---------------------------------------------------------------------------

def test_load_candidate_taxonomy_v6_seed_offline():
    version, tax = runner._load_candidate_taxonomy(str(V6_SEED))
    assert version == 6
    for l1, l2 in (("zh", "en"), ("en", "zh"), ("en", "ja")):
        assert "meaning_inversion" in gc._resolve_subtypes(tax, l1, l2)
    assert tax.get("legacy_aliases")
    assert "baseline subtypes en=" in runner._taxonomy_summary(tax)


def test_load_candidate_taxonomy_v5_seed():
    version, tax = runner._load_candidate_taxonomy(str(V5_SEED))
    assert version == 5 and "meaning_inversion" not in gc._resolve_subtypes(tax, "zh", "en")


def test_load_candidate_taxonomy_rejects_non_taxonomy_sql(tmp_path):
    p = tmp_path / "x.sql"
    p.write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(SystemExit):
        runner._load_candidate_taxonomy(str(p))


def test_preseed_serves_candidate_without_db():
    version, tax = runner._load_candidate_taxonomy(str(V6_SEED))
    runner._preseed_candidate_taxonomy(version, tax)
    # db=None: any DB read would raise, so these prove the cache is what's served.
    assert gc.get_active_taxonomy(None) is tax
    assert gc.get_active_taxonomy_version(None) == 6
    subtypes = gc._resolve_subtypes(tax, "zh", "en")
    assert "meaning_inversion" in subtypes


def test_preseed_honours_matching_pin(monkeypatch):
    version, tax = runner._load_candidate_taxonomy(str(V6_SEED))
    runner._preseed_candidate_taxonomy(version, tax)
    monkeypatch.setenv("DT_TAXONOMY_VERSION", "6")
    assert gc.get_active_taxonomy(None) is tax
    assert gc.get_active_taxonomy_version(None) == 6


def test_preseed_rejects_conflicting_pin(monkeypatch):
    version, tax = runner._load_candidate_taxonomy(str(V6_SEED))
    monkeypatch.setenv("DT_TAXONOMY_VERSION", "5")
    with pytest.raises(SystemExit):
        runner._preseed_candidate_taxonomy(version, tax)
    assert "taxonomy" not in gc._cfg_cache


# ---------------------------------------------------------------------------
# Log counter
# ---------------------------------------------------------------------------

def test_log_counter_counts_and_restores_levels():
    cascade_log = logging.getLogger(runner._NO_TEMPLATE_LOGGER)
    prompts_log = logging.getLogger(runner._EXEMPLAR_DROP_LOGGER)
    before = cascade_log.level
    with runner._LogCounter() as lc:
        prompts_log.warning("dual_translation.prompts: dropping the en exemplar from the prompt")
        prompts_log.warning("dual_translation.prompts: dropping the zh Detector exemplar — x")
        prompts_log.warning("unrelated warning")
        cascade_log.info("dual_translation.grader_cascade: no explanation template for subtype=%r", "x")
        cascade_log.info("some other info line")
    assert lc.counts == {"exemplar_drop": 2, "no_explanation_template": 1}
    assert cascade_log.level == before
    assert lc not in cascade_log.filters and lc not in prompts_log.filters


# ---------------------------------------------------------------------------
# End-to-end with a stubbed grader
# ---------------------------------------------------------------------------

def _perfect_stub_grader(item):
    """Stands in for gc.grade_submission: asserts the candidate taxonomy is what the
    grader would load, then echoes the gold errors/bands (a perfect grader)."""
    tax = gc.get_active_taxonomy(None)
    assert "meaning_inversion" in gc._resolve_subtypes(tax, "zh", "en")
    errors = [{
        "span_reproduction": e["span_repro"],
        "subtype": e["subtype"],
        "severity": e["severity_v2"],
        "explanation_variant": e.get("explanation_variant"),
    } for e in item["expected_errors"]]
    bands = item["expected_bands"]
    return {
        "scores": bands,
        "overall_band": gc.compute_overall_band(bands, {}, "en"),
        "errors": errors,
        "grader_trace": {"variant_basis": {"model": sum(
            1 for e in errors if e["subtype"] == "word_choice")}},
    }


def test_stubbed_v6_run_scores_perfectly_and_renders_v6_section():
    version, tax = runner._load_candidate_taxonomy(str(V6_SEED))
    runner._preseed_candidate_taxonomy(version, tax)
    items = runner._load_fixture("en", "v6")
    records = [runner._build_record(it, _perfect_stub_grader(it), {}, "en") for it in items]

    metrics = em.aggregate_metrics(records, severity_order=em.SEVERITY_TRIAD_ORDER)
    metrics["v6"] = em.taxonomy_v6_metrics(records)
    assert metrics["span"]["f1"] == pytest.approx(1.0)
    assert metrics["subtype_accuracy"]["accuracy"] == pytest.approx(1.0)
    assert metrics["overall"]["exact"] == pytest.approx(1.0)
    mi = metrics["v6"]["meaning_inversion"]
    assert mi["n_expected"] >= 1 and mi["recall"] == pytest.approx(1.0)
    ev = metrics["v6"]["explanation_variant"]
    assert ev["total"] >= 1 and ev["accuracy"] == pytest.approx(1.0)
    assert ev["variant_basis"]["model"] >= ev["total"]

    meta = {"date": "2026-10-04", "l1": "zh", "slugs": [], "tokens_in": 0, "tokens_out": 0,
            "n_calls": 0, "cost": 0.0, "framework_v2": True, "fixture_set": "v6",
            "taxonomy_file": str(V6_SEED), "taxonomy_version": version,
            "log_counts": {"exemplar_drop": 0, "no_explanation_template": 0}}
    report = runner._render_report("en", metrics, meta)
    assert "## Taxonomy v6 metrics" in report
    assert "CANDIDATE v6" in report and "**Fixture set:** v6" in report
    assert "meaning_inversion confusion" in report


def test_dry_run_with_taxonomy_file_prints_plan_and_spends_nothing(monkeypatch, capsys, tmp_path):
    def _boom(*a, **k):  # any DB/client init on a dry run is a bug
        raise AssertionError("dry run touched Supabase")
    monkeypatch.setattr(runner.SupabaseFactory, "initialize", _boom)
    monkeypatch.setattr(runner, "get_supabase_admin", _boom)
    monkeypatch.setattr("sys.argv", [
        "run_dt_grading_eval.py", "--l2", "en", "--out", str(tmp_path / "r.md"),
        "--framework-v2", "--taxonomy-file", str(V6_SEED), "--fixture-set", "v6",
    ])
    assert runner.main() == 0
    out = capsys.readouterr().out
    assert "fixture-set=v6" in out and "[taxonomy] candidate v6 parsed" in out
    assert "[dry-run]" in out and "[warn]" not in out
    assert not (tmp_path / "r.md").exists()
