"""The standalone test pages are shells around the session players.

Each page mounts an ES module that imports from static/js/session, so it needs
the import map (versioned URLs for the whole graph) ahead of any module, and
no script that would run before the deferred base scripts.
"""

import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODULE_PAGES = {
    'test.html': ('js/pages/test.js', "module_assets('js/session', 'players/reading_listening.js')"),
    'test_dictation.html': ('js/pages/test-dictation.js', "module_assets('js/session', 'players/dictation.js')"),
    'test_prestudy.html': ('js/pages/test-prestudy.js', "module_assets('js/session', 'players/intro_drill.js')"),
}
DEFERRED_PAGES = sorted(MODULE_PAGES) + ['test_preview.html']


def _template(name):
    with open(os.path.join(REPO, 'templates', name), encoding='utf-8') as fh:
        return fh.read()


@pytest.mark.parametrize('name', sorted(MODULE_PAGES))
def test_import_map_precedes_the_page_module(name):
    html = _template(name)
    entry, assets_call = MODULE_PAGES[name]
    assert assets_call in html
    assert html.index('type="importmap"') < html.index('rel="modulepreload"')
    assert html.index('rel="modulepreload"') < html.index('type="module"')
    assert f"<script type=\"module\" src=\"{{{{ url_for('static', filename='{entry}') }}}}\">" in html
    assert os.path.exists(os.path.join(REPO, 'static', entry))


@pytest.mark.parametrize('name', DEFERRED_PAGES)
def test_page_has_no_script_that_needs_the_base_scripts_synchronously(name):
    html = _template(name)
    assert '{% set defer_base_scripts = true %}' in html
    for attrs, body in re.findall(r'<script\b([^>]*)>(.*?)</script>', html, re.S):
        if 'importmap' in attrs:
            continue
        assert not body.strip(), f'{name}: inline script'
        assert 'defer' in attrs or 'type="module"' in attrs, f'{name}: blocking script {attrs}'
    assert not re.search(r'\son(click|change)=', html)
    assert '<style' not in html


def test_page_modules_only_import_session_modules_by_relative_path():
    for entry, _ in MODULE_PAGES.values():
        with open(os.path.join(REPO, 'static', entry), encoding='utf-8') as fh:
            source = fh.read()
        specs = re.findall(r"""from\s*['"]([^'"]+)['"]""", source)
        assert specs and all(s.startswith('../session/') for s in specs), entry
