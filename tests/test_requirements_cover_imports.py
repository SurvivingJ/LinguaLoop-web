"""Every third-party module the application imports must be pinned in requirements.txt.

Guards against a dependency being dropped from requirements.txt while an import
of it survives (the `import stripe` left in app.py after the token economy was
retired passed locally in an old virtualenv and broke every test in CI).

The check is static: it walks the application packages with ``ast``, collects
the top-level name of every absolute import, drops the standard library and
first-party names, and maps the rest to distributions with
``importlib.metadata.packages_distributions()``. Imports guarded by
``try/except ImportError`` and imports under ``if TYPE_CHECKING`` are optional
by construction and are skipped.
"""

import ast
import importlib.metadata
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_FILES = ['app.py', 'wsgi.py', 'config.py']
APP_PACKAGES = ['routes', 'services', 'web', 'utils', 'models', 'middleware']

# Import names whose distribution cannot be read from the installed metadata
# (packages_distributions() is empty for them) mapped to the requirement name.
ALIASES = {}


def _normalise(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def _requirement_names():
    names = set()
    with open(os.path.join(ROOT, 'requirements.txt'), encoding='utf-8') as fh:
        for line in fh:
            line = line.split('#', 1)[0].strip()
            if not line or line.startswith('-'):
                continue
            m = re.match(r'([A-Za-z0-9][A-Za-z0-9._-]*)', line)
            if m:
                names.add(_normalise(m.group(1)))
    return names


def _app_files():
    for f in APP_FILES:
        path = os.path.join(ROOT, f)
        if os.path.exists(path):
            yield path
    for pkg in APP_PACKAGES:
        for root, dirs, files in os.walk(os.path.join(ROOT, pkg)):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for f in files:
                if f.endswith('.py'):
                    yield os.path.join(root, f)


def _catches_import_error(handler):
    names = []
    t = handler.type
    if t is None:
        return True
    for node in (t.elts if isinstance(t, ast.Tuple) else [t]):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
    return bool({'ImportError', 'ModuleNotFoundError', 'Exception', 'BaseException'} & set(names))


def _is_type_checking(test):
    return (isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING') or (
        isinstance(test, ast.Attribute) and test.attr == 'TYPE_CHECKING')


def _imports(tree):
    """Yield (top-level name, lineno) for each unguarded module-level absolute import.

    Imports inside function bodies are deliberate lazy imports of heavy or
    tool-only dependencies (e.g. transformers in services/corpus/verifier.py,
    used only by the offline Corpuses/ tool) and do not run at import time.
    """
    def visit(node, guarded):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return
        if isinstance(node, ast.Try):
            body_guarded = guarded or any(_catches_import_error(h) for h in node.handlers)
            for child in node.body:
                yield from visit(child, body_guarded)
            for child in node.handlers + node.orelse + node.finalbody:
                yield from visit(child, guarded)
            return
        if isinstance(node, ast.If) and _is_type_checking(node.test):
            for child in node.orelse:
                yield from visit(child, guarded)
            return
        if not guarded:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    yield alias.name.split('.')[0], node.lineno
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                yield node.module.split('.')[0], node.lineno
        for child in ast.iter_child_nodes(node):
            yield from visit(child, guarded)

    yield from visit(tree, False)


def _first_party(name):
    return os.path.isdir(os.path.join(ROOT, name)) or os.path.exists(os.path.join(ROOT, name + '.py'))


def _uncovered():
    reqs = _requirement_names()
    dists = importlib.metadata.packages_distributions()
    problems = []
    for path in _app_files():
        with open(path, encoding='utf-8') as fh:
            tree = ast.parse(fh.read(), filename=path)
        here = os.path.dirname(path)
        for name, lineno in _imports(tree):
            if name in sys.stdlib_module_names or name == '__future__' or _first_party(name):
                continue
            if os.path.exists(os.path.join(here, name + '.py')):
                continue  # sibling module imported by a script-style path
            candidates = {_normalise(d) for d in dists.get(name, [])}
            if name in ALIASES:
                candidates.add(_normalise(ALIASES[name]))
            if not candidates:
                candidates.add(_normalise(name))
            if not candidates & reqs:
                rel = os.path.relpath(path, ROOT)
                problems.append(f'{rel}:{lineno} imports {name!r} '
                                f'(distribution {sorted(candidates)} not in requirements.txt)')
    return problems


def test_every_application_import_is_pinned_in_requirements():
    assert _uncovered() == []


def test_the_scan_sees_a_known_third_party_import():
    # Sanity check on the walker itself: app.py imports flask unguarded.
    with open(os.path.join(ROOT, 'app.py'), encoding='utf-8') as fh:
        names = {n for n, _ in _imports(ast.parse(fh.read()))}
    assert 'flask' in names


def test_guarded_imports_are_skipped():
    tree = ast.parse(
        'try:\n    import nothere_a\nexcept ImportError:\n    pass\n'
        'if TYPE_CHECKING:\n    import nothere_b\n'
        'def lazy():\n    import nothere_d\n'
        'import nothere_c\n')
    assert [n for n, _ in _imports(tree)] == ['nothere_c']


def test_app_imports_in_a_fresh_interpreter():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('SUPABASE', 'OPENROUTER', 'OPENAI', 'STRIPE'))}
    env['LINGUADOJO_SKIP_DOTENV'] = '1'
    out = subprocess.run([sys.executable, '-c', 'import app'], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
