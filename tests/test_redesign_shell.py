"""The 2026-11 redesign app shell in templates/base.html (see FOUNDATION hand-off)."""


def test_app_pages_carry_tabs_and_viewport_fit(client):
    html = client.get('/tests').get_data(as_text=True)
    assert 'viewport-fit=cover' in html
    assert 'id="ldTabbar"' in html
    assert 'ld-has-tabs' in html
    # the Tests tab is the current one on /tests
    assert 'class="ld-tab is-active" href="/tests' in html
    for area in ('auth', 'session', 'tests', 'prestudy', 'translation', 'trainers', 'settings'):
        assert f'/static/css/redesign/{area}.css' in html
    # everything the old navbar offered stays reachable
    for hook in ('id="logout-btn"', 'id="themeSwitcherMenu"', 'id="langSwitcherMenu"',
                 'data-lang-gate="zh"', 'data-lang-gate="ja"', 'data-bs-target="#reportModal"',
                 '/study-plan', '/word-list', '/calibration'):
        assert hook in html, hook


def test_redesign_stylesheets_are_versioned_and_long_cached(client):
    """The seven area stylesheets go through url_for('static'), so they carry a
    content hash (?v=) and are served with the one-year Cache-Control like every
    other static asset (services/static_assets.py)."""
    import re
    html = client.get('/tests').get_data(as_text=True)
    for area in ('auth', 'session', 'tests', 'prestudy', 'translation', 'trainers', 'settings'):
        m = re.search(rf'/static/css/redesign/{area}\.css\?v=([0-9a-f]{{10}})', html)
        assert m, area
        resp = client.get(f'/static/css/redesign/{area}.css?v={m.group(1)}')
        assert resp.status_code == 200
        assert 'max-age=31536000' in resp.headers.get('Cache-Control', ''), area


def test_bare_pages_have_no_tabs(client):
    html = client.get('/login').get_data(as_text=True)
    assert 'id="ldTabbar"' not in html
    assert 'ld-bare' in html


def test_task_mode_blocks_render(app):
    from flask import render_template_string
    tpl = ('{% extends "base.html" %}{% set task_mode = true %}'
           '{% block task_title %}Quiz{% endblock %}{% block task_back_href %}/tests{% endblock %}'
           '{% block content %}<div class="ld-stage">Q</div>{% endblock %}'
           '{% block dock %}<button class="ld-btn">Check</button>{% endblock %}')
    with app.test_request_context('/tests'):
        html = render_template_string(tpl)
    assert 'ld-body ld-task' in html
    assert 'class="ld-main ld-main--task"' in html
    assert '<div class="ld-dock ld-dock--page" id="ldDock"><button class="ld-btn">Check</button></div>' in html
    assert 'id="ldBack" href="/tests"' in html
    assert '<b id="ldTaskTitle">Quiz</b>' in html


def test_no_empty_dock_without_block(app):
    from flask import render_template_string
    with app.test_request_context('/tests'):
        html = render_template_string('{% extends "base.html" %}{% block content %}x{% endblock %}')
    assert 'id="ldDock"' not in html
