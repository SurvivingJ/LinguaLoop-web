"""Import map and modulepreload generation for ES-module graphs
(services/static_assets.py::module_assets), and its wiring into the
study-session page."""

import json
import os
import re

import pytest
from flask import Flask, render_template_string

from services.static_assets import (
    init_static_assets,
    module_assets,
    module_files,
    static_import_closure,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def module_app(tmp_path):
    mods = tmp_path / 'js' / 'mods'
    (mods / 'players').mkdir(parents=True)
    (mods / 'main.js').write_text(
        "import { a } from './a.js';\n"
        "import {\n  b,\n  c,\n} from './lib/b.js';\n"
        "import './side.js';\n"
        "export { z } from './z.js';\n"
        "// import { no } from './commented.js' is prose, but harmless\n"
        "const lazy = () => import('./players/lazy.js');\n"
    )
    (mods / 'a.js').write_text("import { d } from './lib/d.js';\nexport const a = 1;\n")
    (mods / 'lib').mkdir()
    (mods / 'lib' / 'b.js').write_text("import { d } from './d.js';\nexport const b = 1, c = 2;\n")
    (mods / 'lib' / 'd.js').write_text("export const d = 1;\n")
    (mods / 'side.js').write_text("window.x = 1;\n")
    (mods / 'z.js').write_text("export const z = 1;\n")
    (mods / 'players' / 'lazy.js').write_text("import { d } from '../lib/d.js';\nexport const l = d;\n")
    (mods / 'notes.txt').write_text('not a module')
    (tmp_path / 'js' / 'other.js').write_text('var classic = 1;')
    app = Flask(__name__, static_folder=str(tmp_path), static_url_path='/static')
    init_static_assets(app)

    @app.route('/page')
    def page():
        return render_template_string(
            "{% set m = module_assets('js/mods', 'main.js') %}"
            '<script type="importmap">{{ m.import_map|tojson }}</script>'
            '{% for href in m.preload %}<link rel="modulepreload" href="{{ href }}">{% endfor %}'
            '<script type="module" src="{{ m.entry }}"></script>'
        )

    return app


class TestModuleAssets:
    def test_lists_every_module_in_the_directory_only(self, module_app):
        assert module_files(module_app, 'js/mods') == [
            'js/mods/a.js',
            'js/mods/lib/b.js',
            'js/mods/lib/d.js',
            'js/mods/main.js',
            'js/mods/players/lazy.js',
            'js/mods/side.js',
            'js/mods/z.js',
        ]
        assert module_files(module_app, '../outside') == []
        assert module_files(module_app, 'js/missing') == []

    def test_import_map_maps_plain_urls_to_hashed_urls(self, module_app):
        with module_app.test_request_context():
            assets = module_assets(module_app, 'js/mods', 'main.js')
        imports = assets['import_map']['imports']
        assert len(imports) == 7
        for plain, versioned in imports.items():
            assert '?' not in plain and plain.startswith('/static/js/mods/')
            assert re.fullmatch(re.escape(plain) + r'\?v=[0-9a-f]{10}', versioned)
        # Lazily imported players are mapped too, so they are never revalidated.
        assert '/static/js/mods/players/lazy.js' in imports
        assert assets['entry'] == imports['/static/js/mods/main.js']

    def test_preload_is_the_static_import_closure_of_the_entry(self, module_app):
        assert static_import_closure(module_app, 'js/mods/main.js') == [
            'js/mods/main.js',
            'js/mods/a.js',
            'js/mods/lib/b.js',
            'js/mods/side.js',
            'js/mods/z.js',
            'js/mods/lib/d.js',
        ]
        with module_app.test_request_context():
            assets = module_assets(module_app, 'js/mods', 'main.js')
        imports = assets['import_map']['imports']
        assert assets['preload'][0] == assets['entry']
        assert set(assets['preload']) <= set(imports.values())
        # Dynamic imports are loaded on demand, not preloaded.
        assert imports['/static/js/mods/players/lazy.js'] not in assets['preload']

    def test_without_an_entry_there_is_only_the_map(self, module_app):
        with module_app.test_request_context():
            assets = module_assets(module_app, 'js/mods')
        assert assets['preload'] == [] and assets['entry'] is None
        assert len(assets['import_map']['imports']) == 7

    def test_a_changed_module_gets_a_new_url(self, module_app, tmp_path):
        with module_app.test_request_context():
            before = module_assets(module_app, 'js/mods')['import_map']['imports']
        (tmp_path / 'js' / 'mods' / 'lib' / 'd.js').write_text('export const d = 2;\n')
        with module_app.test_request_context():
            after = module_assets(module_app, 'js/mods')['import_map']['imports']
        changed = [k for k in before if before[k] != after[k]]
        assert changed == ['/static/js/mods/lib/d.js']

    def test_template_helper_renders_map_preloads_and_entry(self, module_app):
        client = module_app.test_client()
        html = client.get('/page').get_data(as_text=True)
        raw = re.search(r'<script type="importmap">(.*?)</script>', html).group(1)
        imports = json.loads(raw)['imports']
        assert imports['/static/js/mods/a.js'].startswith('/static/js/mods/a.js?v=')
        preloads = re.findall(r'<link rel="modulepreload" href="([^"]+)">', html)
        assert len(preloads) == 6
        # The import map comes before anything that fetches a module.
        assert html.index('importmap') < html.index('modulepreload') < html.index('type="module"')
        # A mapped URL is served with the one-year cache lifetime.
        r = client.get(imports['/static/js/mods/a.js'])
        assert r.status_code == 200
        assert 'max-age=31536000' in r.headers['Cache-Control']


class TestSessionModuleGraph:
    """The real static/js/session tree."""

    @pytest.fixture
    def repo_app(self):
        app = Flask(__name__, static_folder=os.path.join(REPO, 'static'), static_url_path='/static')
        init_static_assets(app)
        return app

    def test_every_session_module_is_mapped(self, repo_app):
        with repo_app.test_request_context():
            assets = module_assets(repo_app, 'js/session', 'controller.js')
        imports = assets['import_map']['imports']
        on_disk = []
        for folder, _dirs, names in os.walk(os.path.join(REPO, 'static', 'js', 'session')):
            on_disk += [n for n in names if n.endswith('.js')]
        assert len(imports) == len(on_disk)
        assert '/static/js/session/players/practice.js' in imports
        assert '/static/js/session/players/intro_drill.js' in imports
        assert '/static/js/session/lexicon.js' in imports

    def test_entry_graph_is_shallow_and_holds_no_player(self, repo_app):
        closure = static_import_closure(repo_app, 'js/session/controller.js')
        assert closure[0] == 'js/session/controller.js'
        # Players load on demand through the registry; a static import of one
        # from the controller would drag its whole subtree into first load.
        assert not [f for f in closure if '/players/' in f]
        assert set(closure) == {
            'js/session/controller.js',
            'js/session/player_registry.js',
            'js/session/save_queue.js',
            'js/session/dom.js',
            'js/session/tail.js',
        }

    def test_every_relative_import_resolves_to_a_mapped_module(self, repo_app):
        with repo_app.test_request_context():
            imports = module_assets(repo_app, 'js/session')['import_map']['imports']
        spec_re = re.compile(r"""(?:from\s*|import\s*\(\s*|^\s*import\s*)['"](\.{1,2}/[^'"]+)['"]""", re.MULTILINE)
        for plain in imports:
            path = os.path.join(REPO, plain.lstrip('/'))
            with open(path, encoding='utf-8') as fh:
                source = fh.read()
            for spec in spec_re.findall(source):
                target = os.path.normpath(os.path.join(os.path.dirname(plain), spec))
                assert target in imports, f'{plain} imports unmapped {spec}'

    def test_study_session_template_wires_it_in(self):
        with open(os.path.join(REPO, 'templates', 'study_session.html'), encoding='utf-8') as fh:
            html = fh.read()
        assert "module_assets('js/session', 'controller.js')" in html
        assert html.index('type="importmap"') < html.index('rel="modulepreload"')
        assert html.index('rel="modulepreload"') < html.index('type="module"')
        # The session request starts in the head, before the module graph.
        assert html.index('__ldSessionEarly') < html.index('type="module"')
        head, _, _ = html.partition('{% block content %}')
        assert 'type="importmap"' in head and "fetch(early.url" in head
