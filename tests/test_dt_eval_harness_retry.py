"""Unit tests for the TASK-626 harness hardening in scripts/run_dt_grading_eval.py.

Covers the two additions that stop a single transient failure from orphaning a
whole L2 run (the TASK-625 failure mode): the bounded-retry wrapper
`_grade_with_retry` + its `_is_transient` classifier, and the resume checkpoint
round-trip (`_save_checkpoint` / `_load_checkpoint`). No network, no model calls —
`grade_fn` is a fake and `sleep` is injected, so the backoff is instant.
"""

import importlib.util
import json
import pathlib

import pytest

# scripts/ is not a package — load the runner module directly by path.
_RUNNER_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "run_dt_grading_eval.py"
_spec = importlib.util.spec_from_file_location("run_dt_grading_eval", _RUNNER_PATH)
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)


class _Flaky:
    """Callable that raises `exc` its first `fail_times` calls, then returns `result`."""

    def __init__(self, fail_times, exc, result="OK"):
        self.fail_times = fail_times
        self.exc = exc
        self.result = result
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.exc
        return self.result


class _RecordingSleep:
    def __init__(self):
        self.delays = []

    def __call__(self, d):
        self.delays.append(float(d))


@pytest.fixture
def recording_sleep(monkeypatch):
    """Patch tenacity's sleep hook on the module-level `_grade_once` retry object
    (`runner._grade_once.retry.sleep`) so the backoff is instant and observable —
    without patching time.sleep. Tenacity calls this per `DoSleep` with the computed
    wait, so `.delays` is the exact backoff envelope the @retry policy produced."""
    sleep = _RecordingSleep()
    monkeypatch.setattr(runner._grade_once.retry, "sleep", sleep)
    return sleep


# ---------------------------------------------------------------------------
# _is_transient classification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exc,expected", [
    (Exception("getaddrinfo failed"), True),          # the DNS blip that orphaned JA
    (Exception("HTTP 503 Service Unavailable"), True),
    (Exception("upstream is overloaded"), True),
    (TimeoutError("read timed out"), True),
    (ConnectionResetError("connection reset by peer"), True),
    (ValueError("No dim_languages row for l2_language_id=5"), False),
    (KeyError("span_reproduction"), False),
])
def test_is_transient_classifies_by_type_and_markers(exc, expected):
    assert runner._is_transient(exc) is expected


# ---------------------------------------------------------------------------
# _grade_with_retry (tenacity @retry, TASK-647)
#
# The retry envelope is now the project convention: stop_after_attempt(3) (3 total
# attempts, 2 backoff sleeps) with wait_exponential(multiplier=1, min=2, max=10),
# so both sleeps clamp to the 2s floor. Sleep is observed by patching tenacity's own
# sleep hook (the `recording_sleep` fixture), not time.sleep.
# ---------------------------------------------------------------------------

def test_succeeds_after_n_transient_failures(recording_sleep):
    flaky = _Flaky(fail_times=2, exc=Exception("getaddrinfo failed"))
    result, err = runner._grade_with_retry(flaky, "ja_seed_01")
    assert result == "OK"
    assert err is None
    assert flaky.calls == 3                      # 2 failures + 1 success (3rd attempt)
    assert recording_sleep.delays == [2.0, 2.0]  # wait_exponential floor between the 3 attempts


def test_gives_up_after_exhausting_retries_and_returns_none(recording_sleep):
    exc = Exception("503 upstream overloaded")
    flaky = _Flaky(fail_times=99, exc=exc)
    result, err = runner._grade_with_retry(flaky, "ja_seed_02")
    assert result is None                    # skip-and-log, never raise
    assert err is exc                        # reraise=True surfaces the ORIGINAL exception
    assert flaky.calls == 3                  # stop_after_attempt(3): 3 attempts, then give up
    assert len(recording_sleep.delays) == 2


def test_non_transient_error_is_not_retried(recording_sleep):
    exc = ValueError("No active dt_taxonomy_version row")
    flaky = _Flaky(fail_times=99, exc=exc)
    result, err = runner._grade_with_retry(flaky, "en_seed_03")
    assert result is None
    assert err is exc
    assert flaky.calls == 1                      # tried once, classified non-transient, gave up
    assert recording_sleep.delays == []          # no backoff sleep


def test_behaviour_neutral_when_call_succeeds_first_time(recording_sleep):
    flaky = _Flaky(fail_times=0, exc=Exception("unused"))
    result, err = runner._grade_with_retry(flaky, "zh_seed_04")
    assert (result, err) == ("OK", None)
    assert flaky.calls == 1
    assert recording_sleep.delays == []          # never sleeps on the happy path


# ---------------------------------------------------------------------------
# Resume checkpoint round-trip (TASK-644: append-only JSONL)
# ---------------------------------------------------------------------------

def test_checkpoint_missing_path_is_empty():
    assert runner._load_checkpoint(None) == {"records": [], "skipped": []}
    assert runner._load_checkpoint("nonexistent-file-xyz.json") == {"records": [], "skipped": []}


def test_checkpoint_none_path_and_no_entry_are_noops(tmp_path):
    # No path → nothing written (checkpointing disabled).
    runner._save_checkpoint(None, record={"id": "x"})
    # Path but neither record nor skipped → nothing written (defensive no-op).
    path = tmp_path / "resume.jsonl"
    runner._save_checkpoint(str(path))
    assert not path.exists()


def test_checkpoint_appends_one_jsonl_line_per_item(tmp_path):
    # The core TASK-644 property: each completed item appends exactly one line;
    # earlier lines are never rewritten (O(1) per item, not O(n) full rewrite).
    path = str(tmp_path / "resume.jsonl")
    runner._save_checkpoint(path, record={"id": "ja_seed_01", "kind": "single"})
    runner._save_checkpoint(path, skipped={"id": "ja_seed_02", "kind": "clean", "error": "503"})
    runner._save_checkpoint(path, record={"id": "ja_seed_03", "kind": "multi"})

    lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    envelopes = [json.loads(ln) for ln in lines]          # every line is a standalone JSON object
    assert [e["type"] for e in envelopes] == ["record", "skipped", "record"]
    assert envelopes[0]["data"]["id"] == "ja_seed_01"


def test_checkpoint_streaming_load_reconstructs_arrays(tmp_path):
    path = str(tmp_path / "resume.jsonl")
    r1 = {"id": "ja_seed_01", "kind": "single", "pred_overall": 4, "exp_overall": 3}
    r2 = {"id": "ja_seed_03", "kind": "multi", "pred_overall": 2, "exp_overall": 2}
    s1 = {"id": "ja_seed_02", "kind": "single", "error": "getaddrinfo failed"}
    runner._save_checkpoint(path, record=r1)
    runner._save_checkpoint(path, skipped=s1)
    runner._save_checkpoint(path, record=r2)

    loaded = runner._load_checkpoint(path)
    assert loaded["records"] == [r1, r2]     # order + partition preserved from the stream
    assert loaded["skipped"] == [s1]


def test_checkpoint_migrates_legacy_json_format(tmp_path):
    # A pre-TASK-644 whole-file sidecar must load once and be rewritten as JSONL,
    # so the rest of the run appends consistently instead of full-rewriting.
    path = tmp_path / "resume.json"
    records = [{"id": "ja_seed_01", "kind": "single", "pred_overall": 4, "exp_overall": 3}]
    skipped = [{"id": "ja_seed_02", "kind": "clean", "error": "503 overloaded"}]
    path.write_text(json.dumps({"records": records, "skipped": skipped}, indent=2), encoding="utf-8")

    loaded = runner._load_checkpoint(str(path))
    assert loaded["records"] == records
    assert loaded["skipped"] == skipped

    # File is now JSONL on disk (migrated in place): each line is an envelope, and
    # a whole-file JSON parse of it fails (multiple top-level objects).
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) == 2
    assert [json.loads(ln)["type"] for ln in lines] == ["record", "skipped"]
    with pytest.raises(json.JSONDecodeError):
        json.loads(text)

    # A subsequent append adds a third line and the reload sees all three items.
    runner._save_checkpoint(str(path), record={"id": "ja_seed_03", "kind": "multi"})
    reloaded = runner._load_checkpoint(str(path))
    assert [r["id"] for r in reloaded["records"]] == ["ja_seed_01", "ja_seed_03"]
    assert [s["id"] for s in reloaded["skipped"]] == ["ja_seed_02"]


def test_checkpoint_migrates_legacy_with_missing_key(tmp_path):
    # Legacy sidecar missing the "skipped" key still loads (backfilled to []).
    path = tmp_path / "partial.json"
    path.write_text(json.dumps({"records": [{"id": "x"}]}), encoding="utf-8")
    loaded = runner._load_checkpoint(str(path))
    assert loaded["records"] == [{"id": "x"}]
    assert loaded["skipped"] == []


def test_checkpoint_skips_partial_trailing_line(tmp_path):
    # Crash-safety: a torn final line (interrupted mid-append) is skipped, and the
    # completed lines before it are still recovered — no exception on load.
    path = tmp_path / "resume.jsonl"
    good = json.dumps({"type": "record", "data": {"id": "ja_seed_01", "kind": "single"}})
    torn = '{"type": "record", "data": {"id": "ja_seed_02"'   # truncated, no newline/close
    path.write_text(good + "\n" + torn, encoding="utf-8")

    loaded = runner._load_checkpoint(str(path))
    assert [r["id"] for r in loaded["records"]] == ["ja_seed_01"]
    assert loaded["skipped"] == []


def test_checkpoint_empty_file_is_empty(tmp_path):
    path = tmp_path / "resume.jsonl"
    path.write_text("", encoding="utf-8")
    assert runner._load_checkpoint(str(path)) == {"records": [], "skipped": []}


def test_checkpoint_append_after_torn_line_is_not_glued(tmp_path):
    # A crash can leave a final line with no trailing newline. The next append
    # must start a fresh line so it isn't concatenated onto (and lost with) the
    # torn tail — otherwise a resumed item would silently drop from the log.
    path = tmp_path / "resume.jsonl"
    good = json.dumps({"type": "record", "data": {"id": "ja_seed_01", "kind": "single"}})
    torn = '{"type": "record", "data": {"id": "ja_seed_02"'   # torn: no newline, unclosed
    path.write_text(good + "\n" + torn, encoding="utf-8")

    # Resume re-grades ja_seed_02 and appends its now-complete record.
    runner._save_checkpoint(str(path), record={"id": "ja_seed_02", "kind": "single", "pred_overall": 3})

    loaded = runner._load_checkpoint(str(path))
    assert [r["id"] for r in loaded["records"]] == ["ja_seed_01", "ja_seed_02"]  # both survive
    assert loaded["skipped"] == []
