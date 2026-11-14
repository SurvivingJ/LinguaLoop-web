"""Static-asset delivery: compression, content-hash URLs, long-lived caching.

Measured 2026-11-11 ([[evaluations/latency-2026-11-11]]): every page re-checked
every static file (Flask's default ``Cache-Control: no-cache``) and sent it
uncompressed — 82 KB of CSS, 60-130 KB of i18n JSON and up to 470 KB of JS on
the session page.

* ``url_for('static', filename=...)`` gains ``?v=<content hash>``. A versioned
  URL is served with a one-year ``Cache-Control``; when the file changes, its
  hash and so its URL change, and browsers fetch the new copy.
* A request WITHOUT ``v`` (ES-module imports resolved relative to a module,
  hand-written ``/static/...`` paths) keeps Flask's default revalidation, so
  nothing can ever be served stale.
* ES modules import each other by relative path, which no template can
  version. ``module_assets('js/session', 'controller.js')`` gives a page an
  import map from each module's plain URL to its ``?v=`` URL (so the whole
  graph is cached for a year and never revalidated) plus the URLs to
  ``modulepreload``.
* Flask-Compress gzips/brotlis HTML, CSS, JS and JSON responses.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Dict, List, Optional, Set, Tuple

from flask import Flask, request, url_for

logger = logging.getLogger(__name__)

ONE_YEAR = 365 * 24 * 3600

# filename -> (mtime_ns, size, short hash)
_hashes: Dict[str, Tuple[int, int, str]] = {}

I18N_LANGS = ('en', 'es', 'ja', 'zh')


def file_version(app: Flask, filename: str) -> Optional[str]:
    """Short content hash of a file under static/, or None if it is missing."""
    root = app.static_folder or ''
    path = os.path.normpath(os.path.join(root, filename))
    if not path.startswith(os.path.normpath(root) + os.sep):
        return None
    try:
        st = os.stat(path)
    except OSError:
        return None
    hit = _hashes.get(filename)
    if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
        return hit[2]
    with open(path, 'rb') as fh:
        digest = hashlib.sha1(fh.read()).hexdigest()[:10]
    _hashes[filename] = (st.st_mtime_ns, st.st_size, digest)
    return digest


_STATIC_IMPORT_RE = re.compile(
    r"""^\s*(?:import|export)\s[^'";]*?\sfrom\s*['"](\.{1,2}/[^'"]+)['"]"""
    r"""|^\s*import\s*['"](\.{1,2}/[^'"]+)['"]""",
    re.MULTILINE,
)


def module_files(app: Flask, directory: str) -> List[str]:
    """Every .js file under static/<directory>, as sorted static filenames."""
    root = os.path.normpath(app.static_folder or '')
    top = os.path.normpath(os.path.join(root, directory))
    if not top.startswith(root + os.sep):
        return []
    found = []
    for folder, _dirs, names in os.walk(top):
        for name in names:
            if name.endswith('.js'):
                rel = os.path.relpath(os.path.join(folder, name), root)
                found.append(rel.replace(os.sep, '/'))
    return sorted(found)


def static_import_closure(app: Flask, entry: str) -> List[str]:
    """`entry` plus every module it reaches through static relative imports.

    Dynamic ``import()`` calls are not followed: those modules load on demand.
    """
    root = app.static_folder or ''
    seen: Set[str] = set()
    order: List[str] = []
    todo = [entry]
    while todo:
        filename = todo.pop(0)
        if filename in seen:
            continue
        seen.add(filename)
        try:
            with open(os.path.join(root, filename), encoding='utf-8') as fh:
                source = fh.read()
        except OSError:
            continue
        order.append(filename)
        base = os.path.dirname(filename)
        for match in _STATIC_IMPORT_RE.finditer(source):
            spec = match.group(1) or match.group(2)
            todo.append(os.path.normpath(os.path.join(base, spec)).replace(os.sep, '/'))
    return order


def module_assets(app: Flask, directory: str, entry: Optional[str] = None) -> Dict[str, object]:
    """Import map and preload list for the ES modules under static/<directory>.

    Returns ``{'import_map': {'imports': {plain_url: versioned_url}},
    'preload': [versioned_url, ...], 'entry': versioned_url or None}``.
    ``preload`` is the entry module and everything it imports statically.
    Needs a request or application context (``url_for``).
    """
    imports: Dict[str, str] = {}
    for filename in module_files(app, directory):
        versioned = url_for('static', filename=filename)
        imports[versioned.split('?', 1)[0]] = versioned
    preload: List[str] = []
    entry_url = None
    if entry:
        entry_file = f'{directory}/{entry}'
        entry_url = url_for('static', filename=entry_file)
        preload = [
            url_for('static', filename=f) for f in static_import_closure(app, entry_file)
        ]
    return {'import_map': {'imports': imports}, 'preload': preload, 'entry': entry_url}


def init_static_assets(app: Flask) -> None:
    @app.url_defaults
    def _version_static_urls(endpoint, values):
        if endpoint == 'static' and 'filename' in values and 'v' not in values:
            v = file_version(app, values['filename'])
            if v:
                values['v'] = v

    default_max_age = app.get_send_file_max_age

    def _max_age(filename):
        # static/vendor/<lib>-<version>/... is versioned by its directory and
        # never edited in place (static/vendor/README.md), so it is immutable
        # even when requested without ?v= -- e.g. the webfonts a vendored CSS
        # file references with relative url()s.
        if request.args.get('v') or (filename or '').replace('\\', '/').startswith('vendor/'):
            return ONE_YEAR
        return default_max_age(filename)

    app.get_send_file_max_age = _max_age

    @app.context_processor
    def _asset_versions():
        # i18n JSON is fetched by JS, not via url_for: hand it the versions.
        return {
            'i18n_versions': {
                lang: file_version(app, f'i18n/{lang}.json') for lang in I18N_LANGS
            },
            # Called by the templates that load an ES-module graph.
            'module_assets': lambda directory, entry=None: module_assets(app, directory, entry),
        }

    try:
        from flask_compress import Compress
    except ImportError:  # pragma: no cover - dependency missing in some envs
        logger.warning('flask-compress not installed; responses are not compressed')
        return
    app.config.setdefault('COMPRESS_MIMETYPES', [
        'text/html', 'text/css', 'text/plain', 'text/javascript',
        'application/javascript', 'application/json', 'image/svg+xml',
    ])
    app.config.setdefault('COMPRESS_MIN_SIZE', 1024)
    # Brotli quality 4 / gzip 6: most of the size win for little CPU on a
    # small (hobby-tier) instance.
    app.config.setdefault('COMPRESS_BR_LEVEL', 4)
    app.config.setdefault('COMPRESS_LEVEL', 6)
    Compress(app)
