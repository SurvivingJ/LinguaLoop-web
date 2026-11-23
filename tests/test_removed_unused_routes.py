# tests/test_removed_unused_routes.py
"""API routes removed because nothing in the repository calls them (TASK-1221).

The owner confirmed no other tool or app calls the API, so a route with no
caller in static/, templates/, the session players, scripts or the skills was
dropped together with the code only it used. Each removed path now answers
with the app's JSON error envelope, and the routes next to them on the same
blueprints still resolve.
"""

import json

import pytest
from werkzeug.exceptions import HTTPException

# (method, path, expected status). A removed path answers 404; the one that
# lies under a kept ``/api/tests/<slug>`` GET rule answers 405 instead, with
# POST absent from the methods it allows.
REMOVED = [
    ('GET', '/api/config', 404),
    ('POST', '/api/vocabulary/extract', 404),
    ('POST', '/api/errors/log', 404),
    ('POST', '/api/tests/moderate', 405),
    ('GET', '/api/users/profile', 404),
    ('GET', '/api/calibration/ability', 404),
    ('GET', '/api/flashcards/page', 404),
    ('GET', '/api/flashcards/stats', 404),
    ('POST', '/api/flashcards/skip', 404),
    ('GET', '/api/dual-translation/cards/due', 404),
    ('POST', '/api/dual-translation/passage-from-sentences', 404),
    ('POST', '/api/corpus/ingest', 404),
    ('POST', '/api/corpus/style-analyze', 404),
    ('GET', '/api/corpus/style-profile/1', 404),
    ('POST', '/api/admin/vocab/upload-words', 404),
    ('POST', '/api/admin/vocab/generate-assets', 404),
    ('POST', '/api/admin/vocab/render-exercises', 404),
    ('GET', '/api/admin/vocab/words', 404),
    ('POST', '/api/admin/vocab/word/1/wipe', 404),
    ('DELETE', '/api/admin/vocab/word/1/level/2', 404),
]

# Neighbours on the same blueprints that have callers and must still resolve.
KEPT = [
    ('GET', '/api/health'),
    ('GET', '/api/metadata'),
    ('POST', '/api/vocabulary/word-quiz'),
    ('GET', '/api/tests/'),
    ('GET', '/api/tests/random'),
    ('GET', '/api/tests/some-slug'),
    ('GET', '/api/users/elo'),
    ('GET', '/api/users/preferences'),
    ('PATCH', '/api/users/preferences'),
    ('GET', '/api/users/native-language'),
    ('POST', '/api/calibration/start'),
    ('GET', '/api/calibration/next'),
    ('POST', '/api/calibration/answer'),
    ('POST', '/api/calibration/end'),
    ('GET', '/api/calibration/placement/result'),
    ('GET', '/api/flashcards/due'),
    ('POST', '/api/flashcards/review'),
    ('GET', '/api/dual-translation/next'),
    ('POST', '/api/dual-translation/7/submit'),
    ('POST', '/api/dual-translation/7/skip'),
    ('POST', '/api/dual-translation/cards/7/review'),
    ('GET', '/api/dual-translation/profile'),
    ('GET', '/api/dual-translation/test-available'),
    ('GET', '/api/admin/vocab/word/1/preview'),
]


@pytest.mark.parametrize('method,path,status', REMOVED)
def test_removed_route_answers_json_error(client, auth_headers, method, path, status):
    resp = client.open(path, method=method, json={}, headers=auth_headers)
    assert resp.status_code == status
    body = json.loads(resp.data)
    assert body['status'] == 'error'
    assert body['error_code'] == {404: 'NOT_FOUND', 405: 'METHOD_NOT_ALLOWED'}[status]
    if status == 405:
        assert method not in resp.headers.get('Allow', '')


@pytest.mark.parametrize('method,path,status', REMOVED)
def test_removed_route_has_no_rule(app, method, path, status):
    adapter = app.url_map.bind('localhost')
    try:
        adapter.match(path, method=method)
    except HTTPException as exc:
        assert exc.code == status
    else:
        pytest.fail(f'{method} {path} still resolves to a route')


@pytest.mark.parametrize('method,path', KEPT)
def test_kept_neighbour_still_resolves(app, method, path):
    endpoint, _ = app.url_map.bind('localhost').match(path, method=method)
    assert endpoint in app.view_functions


def test_corpus_blueprint_is_gone(app):
    assert 'corpus' not in app.blueprints
    assert not [r for r in app.url_map.iter_rules() if r.rule.startswith('/api/corpus')]


def test_vocab_admin_keeps_only_preview(app):
    rules = sorted(r.rule for r in app.url_map.iter_rules()
                   if r.rule.startswith('/api/admin/vocab'))
    assert rules == ['/api/admin/vocab/word/<int:sense_id>/preview']
