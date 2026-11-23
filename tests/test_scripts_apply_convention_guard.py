"""Guard for the script write convention (TASK-1218): dry run unless --apply.

A script that can write gets its ``--apply`` / ``--dry-run`` flags from
``scripts/_common.base_parser`` (or ``add_apply_flags`` for one sub-command),
which makes the default a dry run, keeps ``--dry-run`` as an explicit alias and
rejects the two together (exit 2). This test fails when a script under
``scripts/`` or ``Corpuses/`` defines ``--dry-run`` itself, the shape the ~35
write-by-default scripts had, so the convention cannot quietly regress.

The allowlist names the scripts left as they are, each with its reason. An
entry that no longer defines ``--dry-run`` fails too, so the list stays exact.
"""

import ast
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = ('scripts', 'Corpuses')

ALLOWED = {
    # Long-running runners whose purpose is to write, left unchanged (TASK-1218).
    'scripts/dt_nightly_synthesis.py':
        'the in-process scheduler runs run_nightly_synthesis(dry_run=False); the CLI mirrors that job',
    'scripts/run_generation_batch.py':
        'ladder generation runner (LLM spend, resumable chunks); writing is the run itself',
    'scripts/run_test_generation_cli.py':
        'test generation runner; writing the generated tests is the run itself',
    'scripts/run_ladder_from_existing.py':
        'ladder runner over existing tests; also gated by an interactive --yes confirmation',
    'scripts/dt_rewrite_history_v6.py':
        'four-mode mutually exclusive group (dry run is the default; --rehearse/--apply/--restore); '
        'argparse already exits 2 on --apply --dry-run',
    # Retired: cannot write.
    'scripts/backfill_gloss_definitions.py':
        'retired: run() raises before any read or write (cross-language-glosses skill replaces it)',
    # Write only local files; --dry-run skips the file (and model calls).
    'scripts/build_distractor_gold_frame.py': 'writes only data/eval files; reads the database',
    'scripts/build_exercise_gen_reference_set.py': 'writes only the --out JSON; reads the database',
    'scripts/build_zh_pos_overrides.py': 'writes only data/lexicon/zh_pos_overrides.tsv',
    'scripts/merge_classifier_curation.py': 'writes only data/classifier_curation/approved_curation.json',
    'scripts/merge_counter_curation.py': 'writes only data/counter_curation/approved_curation.json',
}


def _script_files():
    for folder in DIRS:
        base = os.path.join(ROOT, folder)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if name.endswith('.py') and name != '_common.py':
                yield f'{folder}/{name}'


def _own_dry_run(path: str) -> list[int]:
    """Lines where the file defines --dry-run itself (add_argument or a raw sys.argv check)."""
    with open(os.path.join(ROOT, path), encoding='utf-8') as fh:
        tree = ast.parse(fh.read(), filename=path)
    lines = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'add_argument'
                and any(isinstance(a, ast.Constant) and a.value == '--dry-run' for a in node.args)):
            lines.append(node.lineno)
        if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Constant)
                and node.left.value == '--dry-run'
                and any(isinstance(op, ast.In) for op in node.ops)):
            lines.append(node.lineno)
    return lines


def test_no_script_defines_its_own_dry_run_flag():
    offenders = {path: lines for path in _script_files()
                 if path not in ALLOWED and (lines := _own_dry_run(path))}
    assert not offenders, (
        'These scripts define --dry-run themselves. A script that writes must be a dry '
        'run unless --apply: build the parser with scripts/_common.base_parser (or '
        'add_apply_flags for a sub-command) and drop the --dry-run argument, or add '
        f'the script to ALLOWED with its reason: {offenders}')


@pytest.mark.parametrize('path', sorted(ALLOWED))
def test_allowlist_entries_are_still_needed(path):
    assert os.path.exists(os.path.join(ROOT, path)), f'{path} is gone: drop it from ALLOWED'
    assert _own_dry_run(path), f'{path} no longer defines --dry-run: drop it from ALLOWED'


def test_the_guard_sees_both_shapes(tmp_path, monkeypatch):
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'scripts' / 'a.py').write_text(
        "import argparse, sys\np = argparse.ArgumentParser()\np.add_argument('--dry-run')\n"
        "x = '--dry-run' in sys.argv\n", encoding='utf-8')
    import sys
    monkeypatch.setattr(sys.modules[__name__], 'ROOT', str(tmp_path))
    assert _own_dry_run('scripts/a.py') == [3, 4]
